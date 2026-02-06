"""
Rutas de proyectos para DrON Topografía
"""
from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime

from models import Proyecto, ProyectoCreate, ProyectoUpdate
from services import db

router = APIRouter(prefix="/proyectos", tags=["Proyectos"])


@router.post("", response_model=Proyecto)
async def crear_proyecto(proyecto: ProyectoCreate):
    """Crear un nuevo proyecto"""
    proyecto_obj = Proyecto(**proyecto.model_dump())
    doc = proyecto_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    if doc.get('volumetria'):
        doc['volumetria'] = doc['volumetria'] if isinstance(doc['volumetria'], dict) else doc['volumetria']
    await db.proyectos.insert_one(doc)
    return proyecto_obj


@router.get("", response_model=List[Proyecto])
async def listar_proyectos():
    """Listar todos los proyectos"""
    proyectos = await db.proyectos.find({}, {"_id": 0}).to_list(1000)
    for p in proyectos:
        if isinstance(p.get('created_at'), str):
            p['created_at'] = datetime.fromisoformat(p['created_at'])
    return proyectos


@router.get("/{proyecto_id}", response_model=Proyecto)
async def obtener_proyecto(proyecto_id: str):
    """Obtener un proyecto por ID"""
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    if isinstance(proyecto.get('created_at'), str):
        proyecto['created_at'] = datetime.fromisoformat(proyecto['created_at'])
    return proyecto


@router.put("/{proyecto_id}", response_model=Proyecto)
async def actualizar_proyecto(proyecto_id: str, proyecto_update: ProyectoUpdate):
    """Actualizar un proyecto existente"""
    update_data = {k: v for k, v in proyecto_update.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No se proporcionaron campos para actualizar")
    
    if 'volumetria' in update_data and update_data['volumetria']:
        update_data['volumetria'] = update_data['volumetria'] if isinstance(update_data['volumetria'], dict) else update_data['volumetria']
    
    result = await db.proyectos.update_one(
        {"id": proyecto_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if isinstance(proyecto.get('created_at'), str):
        proyecto['created_at'] = datetime.fromisoformat(proyecto['created_at'])
    return proyecto


@router.delete("/{proyecto_id}")
async def eliminar_proyecto(proyecto_id: str):
    """Eliminar un proyecto y sus datos asociados"""
    result = await db.proyectos.delete_one({"id": proyecto_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    await db.vuelos.delete_many({"proyecto_id": proyecto_id})
    await db.avances_semanales.delete_many({"proyecto_id": proyecto_id})
    
    return {"message": "Proyecto eliminado"}
