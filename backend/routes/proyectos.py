"""
Rutas de Proyectos - DrON Topografía
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from typing import List, Optional
import uuid

from core.config import get_db, logger
from models.schemas import Proyecto, ProyectoCreate, ProyectoUpdate

router = APIRouter(prefix="/proyectos", tags=["Proyectos"])


async def recalcular_avance_proyecto(proyecto_id: str):
    """
    Recalcula el avance total del proyecto basado en todas las métricas.
    El avance total es el promedio de las fases activas.
    """
    db = get_db()
    
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        return
    
    # Obtener todos los avances semanales
    avances = await db.avances_semanales.find(
        {"proyecto_id": proyecto_id}, {"_id": 0}
    ).to_list(100)
    
    # Calcular totales acumulados
    volumen_excavado = sum((a.get('volumen_excavacion', 0) or 0) for a in avances)
    pilas_completadas = sum((a.get('pilas_completadas', 0) or 0) for a in avances)
    anclas_instaladas = sum((a.get('anclas_instaladas', 0) or 0) for a in avances)
    muros_completados = sum((a.get('muros_completados', 0) or 0) for a in avances)
    
    # Obtener metas del proyecto
    volumen_total = proyecto.get('volumen_total_planeado', 0) or 0
    pilas_planeadas = proyecto.get('pilas_planeadas', 0) or 0
    anclas_planeadas = proyecto.get('anclas_planeadas', 0) or 0
    muros_planeados = proyecto.get('muros_planeados', 0) or 0
    
    tipos_actividades = proyecto.get('tipos_actividades', [])
    
    # Calcular avances por fase
    avances_fases = []
    
    # Excavación
    if 'excavacion' in tipos_actividades and volumen_total > 0:
        avance_excavacion = (volumen_excavado / volumen_total) * 100
        avances_fases.append(min(avance_excavacion, 100))
    
    # Cimentación (promedio de pilas y anclas)
    if 'cimentacion' in tipos_actividades:
        avances_cimentacion = []
        if pilas_planeadas > 0:
            avances_cimentacion.append((pilas_completadas / pilas_planeadas) * 100)
        if anclas_planeadas > 0:
            avances_cimentacion.append((anclas_instaladas / anclas_planeadas) * 100)
        if avances_cimentacion:
            avances_fases.append(min(sum(avances_cimentacion) / len(avances_cimentacion), 100))
    
    # Edificación
    if 'edificacion' in tipos_actividades and muros_planeados > 0:
        avance_edificacion = (muros_completados / muros_planeados) * 100
        avances_fases.append(min(avance_edificacion, 100))
    
    # Calcular avance total como promedio de fases activas
    avance_total = sum(avances_fases) / len(avances_fases) if avances_fases else 0
    
    # Actualizar proyecto
    await db.proyectos.update_one(
        {"id": proyecto_id},
        {"$set": {
            "avance_actual": round(avance_total, 2),
            "volumen_excavado_total": volumen_excavado,
            "pilas_completadas_total": pilas_completadas,
            "anclas_instaladas_total": anclas_instaladas,
            "muros_completados_total": muros_completados,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    logger.info(f"Proyecto {proyecto_id} actualizado: avance={avance_total:.2f}%")


@router.post("", response_model=Proyecto)
async def crear_proyecto(proyecto: ProyectoCreate):
    """Crea un nuevo proyecto"""
    db = get_db()
    proyecto_dict = proyecto.model_dump()
    proyecto_dict["id"] = str(uuid.uuid4())
    proyecto_dict["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.proyectos.insert_one(proyecto_dict)
    proyecto_dict.pop("_id", None)
    return proyecto_dict


@router.get("", response_model=List[Proyecto])
async def listar_proyectos(cliente_id: Optional[str] = None):
    """Lista todos los proyectos, opcionalmente filtrados por cliente"""
    db = get_db()
    
    if cliente_id:
        # Buscar proyectos donde el cliente está asignado
        proyectos = await db.proyectos.find(
            {"clientes_asignados": cliente_id}, 
            {"_id": 0}
        ).to_list(100)
    else:
        proyectos = await db.proyectos.find({}, {"_id": 0}).to_list(100)
    
    # Ordenar por fecha de creación descendente
    proyectos.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return proyectos


@router.get("/{proyecto_id}", response_model=Proyecto)
async def obtener_proyecto(proyecto_id: str):
    """Obtiene un proyecto por su ID"""
    db = get_db()
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return proyecto


@router.put("/{proyecto_id}/avance")
async def actualizar_avance(proyecto_id: str, avance: float):
    """Actualiza el avance de un proyecto"""
    db = get_db()
    result = await db.proyectos.update_one(
        {"id": proyecto_id},
        {"$set": {"avance_actual": avance, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return {"id": proyecto_id, "avance_actual": avance}


@router.put("/{proyecto_id}", response_model=Proyecto)
async def actualizar_proyecto(proyecto_id: str, proyecto_update: ProyectoUpdate):
    """Actualiza un proyecto existente"""
    db = get_db()
    
    # Obtener proyecto actual
    proyecto_actual = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto_actual:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Preparar datos de actualización
    update_data = {k: v for k, v in proyecto_update.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    # Manejar coordenadas si están presentes
    if "coordenadas" in update_data and update_data["coordenadas"]:
        update_data["coordenadas"] = update_data["coordenadas"].model_dump()
    
    await db.proyectos.update_one(
        {"id": proyecto_id},
        {"$set": update_data}
    )
    
    # Recalcular avance si se actualizaron métricas
    await recalcular_avance_proyecto(proyecto_id)
    
    proyecto_actualizado = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    return proyecto_actualizado


@router.post("/{proyecto_id}/asignar-clientes")
async def asignar_clientes_proyecto(proyecto_id: str, cliente_ids: List[str]):
    """Asigna clientes a un proyecto"""
    db = get_db()
    
    proyecto = await db.proyectos.find_one({"id": proyecto_id})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Verificar que los clientes existen
    for cliente_id in cliente_ids:
        cliente = await db.users.find_one({"id": cliente_id, "rol": "client"})
        if not cliente:
            raise HTTPException(status_code=404, detail=f"Cliente {cliente_id} no encontrado")
    
    await db.proyectos.update_one(
        {"id": proyecto_id},
        {"$set": {"clientes_asignados": cliente_ids}}
    )
    
    return {"message": f"Clientes asignados al proyecto {proyecto_id}", "clientes": cliente_ids}


@router.get("/{proyecto_id}/clientes-asignados")
async def obtener_clientes_asignados(proyecto_id: str):
    """Obtiene los clientes asignados a un proyecto"""
    db = get_db()
    
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    cliente_ids = proyecto.get("clientes_asignados", [])
    
    clientes = await db.users.find(
        {"id": {"$in": cliente_ids}, "rol": "client"},
        {"_id": 0, "password": 0}
    ).to_list(100)
    
    return clientes


@router.delete("/{proyecto_id}")
async def eliminar_proyecto(proyecto_id: str):
    """Elimina un proyecto"""
    db = get_db()
    result = await db.proyectos.delete_one({"id": proyecto_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # También eliminar avances semanales asociados
    await db.avances_semanales.delete_many({"proyecto_id": proyecto_id})
    
    return {"message": "Proyecto eliminado"}
