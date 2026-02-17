"""
Rutas de Vuelos - DrON Topografía
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from typing import List, Optional
import uuid

from core.config import get_db
from models.schemas import Vuelo, VueloCreate, VueloUpdate

router = APIRouter(prefix="/vuelos", tags=["Vuelos"])


@router.post("", response_model=Vuelo)
async def crear_vuelo(vuelo: VueloCreate):
    """Crea un nuevo vuelo"""
    db = get_db()
    vuelo_dict = vuelo.model_dump()
    vuelo_dict["id"] = str(uuid.uuid4())
    vuelo_dict["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.vuelos.insert_one(vuelo_dict)
    vuelo_dict.pop("_id", None)
    return vuelo_dict


@router.get("", response_model=List[Vuelo])
async def listar_vuelos(proyecto_id: Optional[str] = None):
    """Lista todos los vuelos, opcionalmente filtrados por proyecto"""
    db = get_db()
    query = {"proyecto_id": proyecto_id} if proyecto_id else {}
    vuelos = await db.vuelos.find(query, {"_id": 0}).to_list(100)
    return vuelos


@router.get("/{vuelo_id}", response_model=Vuelo)
async def obtener_vuelo(vuelo_id: str):
    """Obtiene un vuelo por su ID"""
    db = get_db()
    vuelo = await db.vuelos.find_one({"id": vuelo_id}, {"_id": 0})
    if not vuelo:
        raise HTTPException(status_code=404, detail="Vuelo no encontrado")
    return vuelo


@router.put("/{vuelo_id}", response_model=Vuelo)
async def actualizar_vuelo(vuelo_id: str, vuelo_update: VueloUpdate):
    """Actualiza un vuelo existente"""
    db = get_db()
    
    vuelo_actual = await db.vuelos.find_one({"id": vuelo_id}, {"_id": 0})
    if not vuelo_actual:
        raise HTTPException(status_code=404, detail="Vuelo no encontrado")
    
    update_data = {k: v for k, v in vuelo_update.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.vuelos.update_one(
        {"id": vuelo_id},
        {"$set": update_data}
    )
    
    vuelo_actualizado = await db.vuelos.find_one({"id": vuelo_id}, {"_id": 0})
    return vuelo_actualizado


@router.delete("/{vuelo_id}")
async def eliminar_vuelo(vuelo_id: str):
    """Elimina un vuelo"""
    db = get_db()
    result = await db.vuelos.delete_one({"id": vuelo_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Vuelo no encontrado")
    return {"message": "Vuelo eliminado"}
