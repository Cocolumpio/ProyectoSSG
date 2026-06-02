"""Rutas para gestión de la matriz de Pilas/Anclas dividida en 4 caras de excavación.

Modelo de datos guardado en proyecto.caras_excavacion (List[CaraExcavacion]):
    [
        {
            "nombre": "Norte",
            "pilas": 12,
            "anclas": 8,
            "pilas_estados": [True, False, ...],   # length == pilas
            "anclas_estados": [False, False, ...], # length == anclas
        },
        ...  # exactamente 4 caras
    ]
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from core.config import get_db, get_current_admin, get_current_user

logger = logging.getLogger(__name__)
db = get_db()
router = APIRouter(prefix="/api")


# ---------------- Models ----------------

class CaraExcavacionInput(BaseModel):
    nombre: str = ""
    pilas: int = 0
    anclas: int = 0
    pilas_estados: Optional[List[bool]] = None  # opcional al definir, se inicializa con False
    anclas_estados: Optional[List[bool]] = None


class CarasUpdate(BaseModel):
    caras: List[CaraExcavacionInput] = Field(..., min_length=4, max_length=4)


# ---------------- Helpers ----------------

def _normalizar_estados(cara: dict) -> dict:
    """Asegura que pilas_estados / anclas_estados tengan longitud correcta."""
    pilas = max(int(cara.get("pilas", 0) or 0), 0)
    anclas = max(int(cara.get("anclas", 0) or 0), 0)

    pilas_estados = list(cara.get("pilas_estados") or [])
    anclas_estados = list(cara.get("anclas_estados") or [])

    # Ajustar longitudes (preservando estados existentes si reducimos/crecemos)
    if len(pilas_estados) < pilas:
        pilas_estados = pilas_estados + [False] * (pilas - len(pilas_estados))
    elif len(pilas_estados) > pilas:
        pilas_estados = pilas_estados[:pilas]

    if len(anclas_estados) < anclas:
        anclas_estados = anclas_estados + [False] * (anclas - len(anclas_estados))
    elif len(anclas_estados) > anclas:
        anclas_estados = anclas_estados[:anclas]

    return {
        "nombre": (cara.get("nombre") or "").strip(),
        "pilas": pilas,
        "anclas": anclas,
        "pilas_estados": [bool(x) for x in pilas_estados],
        "anclas_estados": [bool(x) for x in anclas_estados],
    }


async def _recalcular_totales_proyecto(proyecto_id: str):
    """Recalcula pilas/anclas planeadas y ejecutadas a partir de las caras."""
    from services.helpers import recalcular_avance_proyecto
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        return
    caras = proyecto.get("caras_excavacion") or []
    if not caras:
        return

    pilas_plan = sum(int(c.get("pilas", 0) or 0) for c in caras)
    anclas_plan = sum(int(c.get("anclas", 0) or 0) for c in caras)
    pilas_exec = sum(sum(1 for s in (c.get("pilas_estados") or []) if s) for c in caras)
    anclas_exec = sum(sum(1 for s in (c.get("anclas_estados") or []) if s) for c in caras)

    await db.proyectos.update_one(
        {"id": proyecto_id},
        {"$set": {
            "pilas_planeadas": pilas_plan,
            "anclas_planeadas": anclas_plan,
            "pilas_ejecutadas": pilas_exec,
            "anclas_ejecutadas": anclas_exec,
        }}
    )
    await recalcular_avance_proyecto(proyecto_id)


# ---------------- Endpoints ----------------

@router.get("/proyectos/{proyecto_id}/caras-excavacion")
async def obtener_caras(proyecto_id: str, current_user: dict = Depends(get_current_user)):
    """Obtiene la configuración de matriz por cara (pilas + anclas)."""
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    # Si es cliente, validar que el proyecto le pertenece
    if current_user.get("rol") == "client":
        if current_user.get("id") not in (proyecto.get("clientes_asignados") or []):
            raise HTTPException(status_code=403, detail="Sin acceso a este proyecto")

    caras = proyecto.get("caras_excavacion") or []
    return {
        "configurado": len(caras) == 4,
        "caras": caras,
    }


@router.put("/proyectos/{proyecto_id}/caras-excavacion")
async def configurar_caras(
    proyecto_id: str,
    payload: CarasUpdate,
    current_user: dict = Depends(get_current_admin),
):
    """Crea o reemplaza la configuración de las 4 caras (admin)."""
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    existentes = proyecto.get("caras_excavacion") or []

    nuevas_caras = []
    for idx, cara_in in enumerate(payload.caras):
        cara_dict = cara_in.model_dump()
        # Conservar estados previos si la cantidad coincide o se redimensiona
        if idx < len(existentes) and cara_dict.get("pilas_estados") is None:
            cara_dict["pilas_estados"] = existentes[idx].get("pilas_estados", [])
        if idx < len(existentes) and cara_dict.get("anclas_estados") is None:
            cara_dict["anclas_estados"] = existentes[idx].get("anclas_estados", [])
        nuevas_caras.append(_normalizar_estados(cara_dict))

    await db.proyectos.update_one(
        {"id": proyecto_id},
        {"$set": {"caras_excavacion": nuevas_caras}},
    )

    await _recalcular_totales_proyecto(proyecto_id)

    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    return {"caras": proyecto.get("caras_excavacion") or []}


@router.put("/proyectos/{proyecto_id}/caras-excavacion/{cara_idx}/{tipo}/{cell_idx}")
async def toggle_celda(
    proyecto_id: str,
    cara_idx: int,
    tipo: str,
    cell_idx: int,
    estado: Optional[bool] = None,
    current_user: dict = Depends(get_current_admin),
):
    """Marca/desmarca una celda. tipo = 'pilas' | 'anclas'."""
    if tipo not in ("pilas", "anclas"):
        raise HTTPException(status_code=400, detail="tipo inválido")
    if cara_idx < 0 or cara_idx > 3:
        raise HTTPException(status_code=400, detail="cara_idx fuera de rango (0-3)")

    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    caras = list(proyecto.get("caras_excavacion") or [])
    if len(caras) != 4:
        raise HTTPException(status_code=400, detail="Las caras no han sido configuradas")

    cara = caras[cara_idx]
    campo_estados = "pilas_estados" if tipo == "pilas" else "anclas_estados"
    total = cara.get("pilas" if tipo == "pilas" else "anclas", 0)

    estados = list(cara.get(campo_estados) or [])
    # Garantizar longitud
    if len(estados) < total:
        estados = estados + [False] * (total - len(estados))

    if cell_idx < 0 or cell_idx >= total:
        raise HTTPException(status_code=400, detail="cell_idx fuera de rango")

    estados[cell_idx] = bool(estado) if estado is not None else (not estados[cell_idx])
    cara[campo_estados] = estados
    caras[cara_idx] = cara

    await db.proyectos.update_one(
        {"id": proyecto_id},
        {"$set": {"caras_excavacion": caras}},
    )

    await _recalcular_totales_proyecto(proyecto_id)

    return {
        "cara_idx": cara_idx,
        "tipo": tipo,
        "cell_idx": cell_idx,
        "estado": estados[cell_idx],
    }


@router.get("/proyectos/{proyecto_id}/caras-excavacion/resumen")
async def resumen_caras(proyecto_id: str, current_user: dict = Depends(get_current_user)):
    """Resumen agregado por cara: completadas / total para pilas y anclas."""
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    if current_user.get("rol") == "client":
        if current_user.get("id") not in (proyecto.get("clientes_asignados") or []):
            raise HTTPException(status_code=403, detail="Sin acceso a este proyecto")

    caras = proyecto.get("caras_excavacion") or []
    resumen = []
    tot_p = tot_pc = tot_a = tot_ac = 0
    for c in caras:
        p = int(c.get("pilas", 0) or 0)
        a = int(c.get("anclas", 0) or 0)
        pc = sum(1 for s in (c.get("pilas_estados") or []) if s)
        ac = sum(1 for s in (c.get("anclas_estados") or []) if s)
        resumen.append({
            "nombre": c.get("nombre", ""),
            "pilas_total": p,
            "pilas_completadas": pc,
            "pilas_pct": round((pc / p * 100) if p else 0, 1),
            "anclas_total": a,
            "anclas_completadas": ac,
            "anclas_pct": round((ac / a * 100) if a else 0, 1),
        })
        tot_p += p
        tot_pc += pc
        tot_a += a
        tot_ac += ac

    return {
        "caras": resumen,
        "totales": {
            "pilas_total": tot_p,
            "pilas_completadas": tot_pc,
            "pilas_pct": round((tot_pc / tot_p * 100) if tot_p else 0, 1),
            "anclas_total": tot_a,
            "anclas_completadas": tot_ac,
            "anclas_pct": round((tot_ac / tot_a * 100) if tot_a else 0, 1),
        },
    }
