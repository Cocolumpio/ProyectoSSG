"""Rutas de Volumetría DEM (TIFF) - DrON Topografía"""
import io
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.config import get_db, get_current_admin
from services import dem_volumetry
from services.storage import get_storage

db = get_db()
router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


async def _read_gridfs(file_id: str) -> bytes:
    """Helper: lee bytes desde GridFS."""
    storage = get_storage(db)
    data, _meta = await storage.get_file(file_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Archivo GridFS {file_id} no encontrado")
    return data


# ============================================================
# 1. SUBIR DEM (TIFF) A UN AVANCE SEMANAL
# ============================================================
@router.post("/proyectos/{proyecto_id}/avances-semanales/{avance_id}/dem")
async def subir_dem_avance(
    proyecto_id: str,
    avance_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_admin),
):
    """Sube un DEM (GeoTIFF) a un avance semanal específico."""
    if not file.filename.lower().endswith((".tif", ".tiff")):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .tif/.tiff")

    avance = await db.avances_semanales.find_one(
        {"id": avance_id, "proyecto_id": proyecto_id},
        {"_id": 0}
    )
    if not avance:
        raise HTTPException(status_code=404, detail="Avance no encontrado")

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="El archivo está vacío")
    if len(contents) > 500 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="El archivo excede 500 MB")

    # Extraer metadata antes de guardar
    metadata = dem_volumetry.extraer_metadata_dem(contents)
    if "error" in metadata:
        raise HTTPException(status_code=400, detail=f"El TIFF no es un DEM válido: {metadata['error']}")

    # Guardar en GridFS
    storage = get_storage(db)
    file_id = await storage.save_file(
        contents,
        filename=file.filename,
        content_type="image/tiff",
        metadata={
            "type": "dem",
            "proyecto_id": proyecto_id,
            "avance_id": avance_id,
            "uploaded_by": current_user.get("id"),
        }
    )

    # Eliminar DEM previo si existía
    if avance.get("dem_gridfs_id"):
        try:
            await storage.delete_file(avance["dem_gridfs_id"])
        except Exception as e:
            logger.warning(f"No se pudo eliminar DEM previo: {e}")

    now_iso = datetime.now(timezone.utc).isoformat()
    await db.avances_semanales.update_one(
        {"id": avance_id, "proyecto_id": proyecto_id},
        {"$set": {
            "dem_gridfs_id": file_id,
            "dem_filename": file.filename,
            "dem_uploaded_at": now_iso,
            "dem_metadata": metadata,
        }}
    )

    return {
        "message": "DEM subido correctamente",
        "dem_gridfs_id": file_id,
        "dem_filename": file.filename,
        "metadata": metadata,
    }


# ============================================================
# 2. ELIMINAR DEM DE UN AVANCE
# ============================================================
@router.delete("/proyectos/{proyecto_id}/avances-semanales/{avance_id}/dem")
async def eliminar_dem_avance(
    proyecto_id: str,
    avance_id: str,
    current_user: dict = Depends(get_current_admin),
):
    avance = await db.avances_semanales.find_one(
        {"id": avance_id, "proyecto_id": proyecto_id},
        {"_id": 0}
    )
    if not avance:
        raise HTTPException(status_code=404, detail="Avance no encontrado")
    if not avance.get("dem_gridfs_id"):
        raise HTTPException(status_code=404, detail="Este avance no tiene DEM")

    storage = get_storage(db)
    try:
        await storage.delete_file(avance["dem_gridfs_id"])
    except Exception as e:
        logger.warning(f"Error eliminando DEM en GridFS: {e}")

    await db.avances_semanales.update_one(
        {"id": avance_id, "proyecto_id": proyecto_id},
        {"$unset": {
            "dem_gridfs_id": "",
            "dem_filename": "",
            "dem_uploaded_at": "",
            "dem_metadata": "",
        }}
    )
    return {"message": "DEM eliminado correctamente"}


# ============================================================
# 3. CALCULAR VOLUMETRÍA ENTRE DOS DEMs
# ============================================================
class VolumetriaRequest(BaseModel):
    avance_anterior_id: str  # Puede ser "terreno_original" para el DEM base del proyecto
    avance_actual_id: str
    threshold_m: Optional[float] = 0.05
    interpretar_ia: Optional[bool] = False


@router.post("/proyectos/{proyecto_id}/volumetria-dem")
async def calcular_volumetria(
    proyecto_id: str,
    body: VolumetriaRequest,
    current_user: dict = Depends(get_current_admin),
):
    """Calcula volumetría retiro/relleno entre dos DEMs del proyecto."""
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    storage = get_storage(db)

    # ---- Obtener DEM anterior ----
    if body.avance_anterior_id == "terreno_original":
        dem_anterior_id = proyecto.get("dem_terreno_original_gridfs_id")
        dem_anterior_label = "Terreno original"
        if not dem_anterior_id:
            raise HTTPException(
                status_code=400,
                detail="El proyecto no tiene DEM de terreno original cargado"
            )
    else:
        ant = await db.avances_semanales.find_one(
            {"id": body.avance_anterior_id, "proyecto_id": proyecto_id},
            {"_id": 0}
        )
        if not ant:
            raise HTTPException(status_code=404, detail="Avance anterior no encontrado")
        dem_anterior_id = ant.get("dem_gridfs_id")
        dem_anterior_label = f"Semana {ant.get('semana', '?')} ({ant.get('fecha', '')})"
        if not dem_anterior_id:
            raise HTTPException(status_code=400, detail="El avance anterior no tiene DEM cargado")

    # ---- Obtener DEM actual ----
    act = await db.avances_semanales.find_one(
        {"id": body.avance_actual_id, "proyecto_id": proyecto_id},
        {"_id": 0}
    )
    if not act:
        raise HTTPException(status_code=404, detail="Avance actual no encontrado")
    dem_actual_id = act.get("dem_gridfs_id")
    if not dem_actual_id:
        raise HTTPException(status_code=400, detail="El avance actual no tiene DEM cargado")
    dem_actual_label = f"Semana {act.get('semana', '?')} ({act.get('fecha', '')})"

    # ---- Descargar bytes ----
    try:
        prev_bytes = await _read_gridfs(dem_anterior_id)
        actual_bytes = await _read_gridfs(dem_actual_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error leyendo DEMs: {e}")

    # ---- Calcular volumetría ----
    try:
        resultado = dem_volumetry.calcular_volumetria_dem(
            prev_bytes, actual_bytes, threshold_m=body.threshold_m or 0.05
        )
    except MemoryError:
        logger.exception("OOM en cálculo de volumetría")
        raise HTTPException(
            status_code=507,
            detail="DEMs demasiado grandes para procesar. Considera bajar la resolución de los TIFFs o exportarlos con compresión."
        )
    except Exception as e:
        logger.exception("Error calculando volumetría")
        raise HTTPException(status_code=500, detail=f"Error en cálculo: {type(e).__name__}: {e}")

    # ---- Guardar heatmap PNG en GridFS ----
    heatmap_id = await storage.save_file(
        resultado.pop("heatmap_png"),
        filename=f"heatmap_{proyecto_id}_{body.avance_actual_id}.png",
        content_type="image/png",
        metadata={"type": "dem_heatmap", "proyecto_id": proyecto_id}
    )
    heatmap_url = f"/api/dem-heatmap/{heatmap_id}"

    # ---- Persistir comparación ----
    comparacion_id = str(uuid.uuid4())
    comparacion_doc = {
        "id": comparacion_id,
        "proyecto_id": proyecto_id,
        "avance_anterior_id": body.avance_anterior_id,
        "avance_anterior_label": dem_anterior_label,
        "avance_actual_id": body.avance_actual_id,
        "avance_actual_label": dem_actual_label,
        "resultado": resultado,
        "heatmap_gridfs_id": heatmap_id,
        "heatmap_url": heatmap_url,
        "threshold_m": body.threshold_m or 0.05,
        "creado_por": current_user.get("id"),
        "fecha": datetime.now(timezone.utc).isoformat(),
        "interpretacion_ia": None,
    }
    await db.comparaciones_dem.insert_one(comparacion_doc)

    # ---- Interpretación IA opcional ----
    if body.interpretar_ia:
        try:
            contexto = {
                "proyecto_nombre": proyecto.get("nombre"),
                "semana_actual": act.get("semana"),
                "semana_anterior": ant.get("semana") if body.avance_anterior_id != "terreno_original" else None,
                "volumen_planeado_total": proyecto.get("volumen_total_planeado", 0),
            }
            interpretacion = await dem_volumetry.interpretar_volumetria_con_ia(resultado, contexto)
            await db.comparaciones_dem.update_one(
                {"id": comparacion_id},
                {"$set": {"interpretacion_ia": interpretacion}}
            )
            comparacion_doc["interpretacion_ia"] = interpretacion
        except Exception as e:
            logger.error(f"Error en interpretación IA: {e}")
            comparacion_doc["interpretacion_ia"] = f"Error generando IA: {e}"

    # Quitar _id residual si fuera el caso
    comparacion_doc.pop("_id", None)
    return comparacion_doc


# ============================================================
# 4. LISTAR COMPARACIONES DE UN PROYECTO
# ============================================================
@router.get("/proyectos/{proyecto_id}/volumetria-dem")
async def listar_comparaciones_dem(proyecto_id: str):
    cursor = db.comparaciones_dem.find(
        {"proyecto_id": proyecto_id},
        {"_id": 0}
    ).sort("fecha", -1)
    return await cursor.to_list(length=200)


# ============================================================
# 5. SERVIR HEATMAP PNG
# ============================================================
@router.get("/dem-heatmap/{file_id}")
async def descargar_heatmap(file_id: str):
    try:
        data = await _read_gridfs(file_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Heatmap no encontrado")
    return StreamingResponse(io.BytesIO(data), media_type="image/png")


# ============================================================
# 6. ELIMINAR UNA COMPARACIÓN
# ============================================================
@router.delete("/volumetria-dem/{comparacion_id}")
async def eliminar_comparacion(
    comparacion_id: str,
    current_user: dict = Depends(get_current_admin),
):
    comp = await db.comparaciones_dem.find_one({"id": comparacion_id}, {"_id": 0})
    if not comp:
        raise HTTPException(status_code=404, detail="Comparación no encontrada")
    storage = get_storage(db)
    if comp.get("heatmap_gridfs_id"):
        try:
            await storage.delete_file(comp["heatmap_gridfs_id"])
        except Exception:
            pass
    await db.comparaciones_dem.delete_one({"id": comparacion_id})
    return {"message": "Comparación eliminada"}


# ============================================================
# 7. INTERPRETAR CON IA UNA COMPARACIÓN EXISTENTE
# ============================================================
@router.post("/volumetria-dem/{comparacion_id}/interpretar")
async def interpretar_comparacion(
    comparacion_id: str,
    current_user: dict = Depends(get_current_admin),
):
    comp = await db.comparaciones_dem.find_one({"id": comparacion_id}, {"_id": 0})
    if not comp:
        raise HTTPException(status_code=404, detail="Comparación no encontrada")

    proyecto = await db.proyectos.find_one({"id": comp["proyecto_id"]}, {"_id": 0})
    contexto = {
        "proyecto_nombre": proyecto.get("nombre") if proyecto else None,
        "volumen_planeado_total": proyecto.get("volumen_total_planeado", 0) if proyecto else 0,
    }
    interpretacion = await dem_volumetry.interpretar_volumetria_con_ia(comp["resultado"], contexto)
    await db.comparaciones_dem.update_one(
        {"id": comparacion_id},
        {"$set": {"interpretacion_ia": interpretacion}}
    )
    return {"interpretacion_ia": interpretacion}


# ============================================================
# 8. SUBIR DEM DE TERRENO ORIGINAL AL PROYECTO
# ============================================================
@router.post("/proyectos/{proyecto_id}/dem-terreno-original")
async def subir_dem_terreno_original(
    proyecto_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_admin),
):
    if not file.filename.lower().endswith((".tif", ".tiff")):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .tif/.tiff")

    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    contents = await file.read()
    if len(contents) > 500 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="El archivo excede 500 MB")

    metadata = dem_volumetry.extraer_metadata_dem(contents)
    if "error" in metadata:
        raise HTTPException(status_code=400, detail=f"TIFF inválido: {metadata['error']}")

    storage = get_storage(db)
    file_id = await storage.save_file(
        contents,
        filename=file.filename,
        content_type="image/tiff",
        metadata={"type": "dem_terreno_original", "proyecto_id": proyecto_id}
    )

    if proyecto.get("dem_terreno_original_gridfs_id"):
        try:
            await storage.delete_file(proyecto["dem_terreno_original_gridfs_id"])
        except Exception:
            pass

    await db.proyectos.update_one(
        {"id": proyecto_id},
        {"$set": {
            "dem_terreno_original_gridfs_id": file_id,
            "dem_terreno_original_filename": file.filename,
            "dem_terreno_original_metadata": metadata,
            "dem_terreno_original_uploaded_at": datetime.now(timezone.utc).isoformat(),
        }}
    )
    return {
        "message": "DEM de terreno original cargado",
        "filename": file.filename,
        "metadata": metadata,
    }
