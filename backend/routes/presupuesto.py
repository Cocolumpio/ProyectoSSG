"""Rutas de Presupuesto del Proyecto (Excel + IA Gemini) - DrON Topografía"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel

from core.config import get_db, get_current_admin
from services import presupuesto as presupuesto_service

db = get_db()
router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


# ============================================================
# 1. LISTAR HOJAS DE UN EXCEL (para que usuario elija versión)
# ============================================================
@router.post("/presupuesto/listar-hojas")
async def listar_hojas(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_admin),
):
    """Sube un Excel y devuelve la lista de hojas detectadas con metadatos.
    El frontend lo usa para mostrar un selector si hay múltiples hojas."""
    if not file.filename.lower().endswith((".xlsx", ".xlsm", ".xls")):
        raise HTTPException(status_code=400, detail="Sube un archivo .xlsx o .xlsm")
    
    contents = await file.read()
    if len(contents) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="El archivo excede 20 MB")
    
    try:
        hojas = presupuesto_service.listar_hojas(contents)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    presupuesto_hojas = [h for h in hojas if h["es_presupuesto"]]
    
    return {
        "filename": file.filename,
        "hojas": hojas,
        "hojas_con_presupuesto": [h["nombre"] for h in presupuesto_hojas],
        "tiene_multiples_versiones": len(presupuesto_hojas) > 1,
        "version_recomendada": _seleccionar_version_recomendada(presupuesto_hojas),
    }


def _seleccionar_version_recomendada(hojas_pres: list) -> Optional[str]:
    """Heurística: prefiere la versión más reciente (R4 > R3 > R2 > ...)."""
    versiones = [h for h in hojas_pres if (h.get("posible_version") or "").startswith("R")]
    if versiones:
        # Ordenar por número R
        def get_num(h):
            try:
                return int(h["posible_version"].replace("R", ""))
            except Exception:
                return 0
        versiones.sort(key=get_num, reverse=True)
        return versiones[0]["nombre"]
    if hojas_pres:
        return hojas_pres[0]["nombre"]
    return None


# ============================================================
# 2. ANALIZAR Y GUARDAR PRESUPUESTO
# ============================================================
@router.post("/proyectos/{proyecto_id}/presupuesto/analizar")
async def analizar_presupuesto(
    proyecto_id: str,
    file: UploadFile = File(...),
    sheet_name: str = Form(...),
    version: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_admin),
):
    """Analiza una hoja específica del Excel con IA y guarda el presupuesto en el proyecto."""
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    if not file.filename.lower().endswith((".xlsx", ".xlsm", ".xls")):
        raise HTTPException(status_code=400, detail="Sube un archivo .xlsx o .xlsm")
    
    contents = await file.read()
    
    try:
        resultado = await presupuesto_service.extraer_presupuesto_con_ia(
            contents, sheet_name, version=version
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error procesando presupuesto")
        raise HTTPException(status_code=500, detail=f"Error: {type(e).__name__}: {e}")

    # Guardar en proyecto
    presupuesto_doc = {
        "filename": file.filename,
        "sheet_name": sheet_name,
        "version": version or resultado.get("version"),
        "categorias": resultado["categorias"],
        "total_general": resultado["total_general"],
        "num_conceptos": resultado["num_conceptos"],
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "uploaded_by": current_user.get("id"),
    }
    
    await db.proyectos.update_one(
        {"id": proyecto_id},
        {"$set": {"presupuesto": presupuesto_doc}}
    )
    
    return presupuesto_doc


# ============================================================
# 3. OBTENER PRESUPUESTO DE UN PROYECTO
# ============================================================
@router.get("/proyectos/{proyecto_id}/presupuesto")
async def obtener_presupuesto(proyecto_id: str):
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0, "presupuesto": 1})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return proyecto.get("presupuesto") or {"empty": True}


# ============================================================
# 4. ELIMINAR PRESUPUESTO
# ============================================================
@router.delete("/proyectos/{proyecto_id}/presupuesto")
async def eliminar_presupuesto(
    proyecto_id: str,
    current_user: dict = Depends(get_current_admin),
):
    result = await db.proyectos.update_one(
        {"id": proyecto_id},
        {"$unset": {"presupuesto": ""}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return {"message": "Presupuesto eliminado"}


# ============================================================
# 5. ACTUALIZAR UN CONCEPTO MANUALMENTE
# ============================================================
class ConceptoUpdate(BaseModel):
    categoria_origen: str
    categoria_destino: str
    indice_concepto: int  # Índice dentro de la categoría origen


@router.put("/proyectos/{proyecto_id}/presupuesto/reclasificar")
async def reclasificar_concepto(
    proyecto_id: str,
    body: ConceptoUpdate,
    current_user: dict = Depends(get_current_admin),
):
    """Mueve un concepto de una categoría a otra (si la IA lo clasificó mal)."""
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto or "presupuesto" not in proyecto:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    
    pres = proyecto["presupuesto"]
    categorias = pres["categorias"]
    if body.categoria_origen not in categorias:
        raise HTTPException(status_code=400, detail="Categoría origen no existe")
    
    conceptos_origen = categorias[body.categoria_origen]["conceptos"]
    if body.indice_concepto >= len(conceptos_origen):
        raise HTTPException(status_code=400, detail="Índice de concepto inválido")
    
    # Mover
    concepto = conceptos_origen.pop(body.indice_concepto)
    categorias[body.categoria_origen]["total"] = round(
        sum(c["importe"] for c in conceptos_origen), 2
    )
    if not conceptos_origen:
        del categorias[body.categoria_origen]
    
    if body.categoria_destino not in categorias:
        categorias[body.categoria_destino] = {"total": 0.0, "conceptos": []}
    categorias[body.categoria_destino]["conceptos"].append(concepto)
    categorias[body.categoria_destino]["total"] = round(
        sum(c["importe"] for c in categorias[body.categoria_destino]["conceptos"]), 2
    )
    
    await db.proyectos.update_one(
        {"id": proyecto_id},
        {"$set": {"presupuesto.categorias": categorias}}
    )
    return {"message": "Concepto reclasificado", "categorias": categorias}
