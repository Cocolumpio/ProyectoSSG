"""CRUD de directores que reciben alertas de WhatsApp por desviación de obra."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.config import get_current_admin, get_db

logger = logging.getLogger(__name__)
db = get_db()
router = APIRouter(prefix="/api")


class DirectorCreate(BaseModel):
    nombre: str
    whatsapp: str  # E.164 o 10 dígitos (se normaliza al enviar)
    cargo: str = "Director"
    activo: bool = True


class DirectorUpdate(BaseModel):
    nombre: Optional[str] = None
    whatsapp: Optional[str] = None
    cargo: Optional[str] = None
    activo: Optional[bool] = None


@router.get("/directores")
async def listar_directores(current_user: dict = Depends(get_current_admin)):
    docs = await db.directores.find({}, {"_id": 0}).sort("nombre", 1).to_list(500)
    return {"directores": docs}


@router.post("/directores")
async def crear_director(payload: DirectorCreate, current_user: dict = Depends(get_current_admin)):
    if not payload.nombre.strip():
        raise HTTPException(400, "nombre requerido")
    if not payload.whatsapp.strip():
        raise HTTPException(400, "whatsapp requerido")
    doc = {
        "id": str(uuid.uuid4()),
        "nombre": payload.nombre.strip(),
        "whatsapp": payload.whatsapp.strip(),
        "cargo": payload.cargo.strip() or "Director",
        "activo": payload.activo,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.directores.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.put("/directores/{director_id}")
async def actualizar_director(
    director_id: str,
    payload: DirectorUpdate,
    current_user: dict = Depends(get_current_admin),
):
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "Sin cambios")
    result = await db.directores.update_one({"id": director_id}, {"$set": updates})
    if not result.matched_count:
        raise HTTPException(404, "Director no encontrado")
    doc = await db.directores.find_one({"id": director_id}, {"_id": 0})
    return doc


@router.delete("/directores/{director_id}")
async def eliminar_director(director_id: str, current_user: dict = Depends(get_current_admin)):
    result = await db.directores.delete_one({"id": director_id})
    if not result.deleted_count:
        raise HTTPException(404, "Director no encontrado")
    return {"deleted": True}
