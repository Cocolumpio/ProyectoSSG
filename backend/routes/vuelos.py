"""
Rutas de vuelos para DrON Topografía
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import datetime

from models import Vuelo, VueloCreate, VueloUpdate, Volumetria
from services import db

router = APIRouter(prefix="/vuelos", tags=["Vuelos"])


@router.post("", response_model=Vuelo)
async def crear_vuelo(vuelo: VueloCreate):
    """Crear un nuevo vuelo"""
    proyecto = await db.proyectos.find_one({"id": vuelo.proyecto_id})
    if not proyecto:
        raise HTTPException(status_code=400, detail="Proyecto no encontrado")
    
    vuelo_data = vuelo.model_dump()
    if vuelo_data.get('volumetria') is None:
        vuelo_data['volumetria'] = Volumetria().model_dump()
    
    vuelo_obj = Vuelo(**vuelo_data)
    doc = vuelo_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.vuelos.insert_one(doc)
    return vuelo_obj


@router.get("", response_model=List[Vuelo])
async def listar_vuelos(proyecto_id: Optional[str] = None):
    """Listar vuelos, opcionalmente filtrados por proyecto"""
    query = {}
    if proyecto_id:
        query["proyecto_id"] = proyecto_id
    
    vuelos = await db.vuelos.find(query, {"_id": 0}).sort("fecha_vuelo", -1).to_list(1000)
    for v in vuelos:
        if isinstance(v.get('created_at'), str):
            v['created_at'] = datetime.fromisoformat(v['created_at'])
    return vuelos


@router.get("/{vuelo_id}", response_model=Vuelo)
async def obtener_vuelo(vuelo_id: str):
    """Obtener un vuelo por ID"""
    vuelo = await db.vuelos.find_one({"id": vuelo_id}, {"_id": 0})
    if not vuelo:
        raise HTTPException(status_code=404, detail="Vuelo no encontrado")
    if isinstance(vuelo.get('created_at'), str):
        vuelo['created_at'] = datetime.fromisoformat(vuelo['created_at'])
    return vuelo


@router.put("/{vuelo_id}", response_model=Vuelo)
async def actualizar_vuelo(vuelo_id: str, vuelo_update: VueloUpdate):
    """Actualizar un vuelo existente"""
    update_data = {k: v for k, v in vuelo_update.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No se proporcionaron campos para actualizar")
    
    result = await db.vuelos.update_one(
        {"id": vuelo_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Vuelo no encontrado")
    
    vuelo = await db.vuelos.find_one({"id": vuelo_id}, {"_id": 0})
    if isinstance(vuelo.get('created_at'), str):
        vuelo['created_at'] = datetime.fromisoformat(vuelo['created_at'])
    return vuelo


@router.delete("/{vuelo_id}")
async def eliminar_vuelo(vuelo_id: str):
    """Eliminar un vuelo"""
    result = await db.vuelos.delete_one({"id": vuelo_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Vuelo no encontrado")
    return {"message": "Vuelo eliminado"}
