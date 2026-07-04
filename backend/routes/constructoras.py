"""CRUD de constructoras (clientes) con logo PNG para mostrar en la landing pública."""
import io
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from core.config import get_current_admin, get_db
from services.storage import get_storage

logger = logging.getLogger(__name__)
db = get_db()
router = APIRouter(prefix="/api")

ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp", "image/svg+xml"}
ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
MAX_LOGO_BYTES = 3 * 1024 * 1024  # 3 MB


def _to_public_dict(doc: dict) -> dict:
    """Prepara el documento para respuesta pública/admin (sin _id)."""
    doc.pop("_id", None)
    if doc.get("logo_gridfs_id"):
        doc["logo_url"] = f"/api/constructoras/{doc['id']}/logo"
    return doc


# ---------- Endpoint público (para landing) ----------
@router.get("/public/constructoras")
async def listar_constructoras_publicas():
    """Devuelve las constructoras activas con logo para mostrar en la landing."""
    docs = await db.constructoras.find(
        {"activo": True, "logo_gridfs_id": {"$ne": None}},
        {"_id": 0, "id": 1, "nombre": 1, "logo_gridfs_id": 1, "orden": 1},
    ).sort("orden", 1).to_list(200)
    resultado = []
    for d in docs:
        resultado.append({
            "id": d["id"],
            "nombre": d.get("nombre"),
            "logo_url": f"/api/constructoras/{d['id']}/logo",
        })
    return {"constructoras": resultado}


# ---------- Endpoint público del logo ----------
@router.get("/constructoras/{constructora_id}/logo")
async def obtener_logo(constructora_id: str):
    doc = await db.constructoras.find_one({"id": constructora_id}, {"_id": 0})
    if not doc or not doc.get("logo_gridfs_id"):
        raise HTTPException(404, "Logo no encontrado")
    storage = get_storage(db)
    content, meta = await storage.get_file(doc["logo_gridfs_id"])
    if not content:
        raise HTTPException(404, "Logo no encontrado")
    content_type = (meta or {}).get("contentType") or doc.get("logo_content_type") or "image/png"
    return StreamingResponse(
        io.BytesIO(content),
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )


# ---------- CRUD Admin ----------
@router.get("/constructoras")
async def listar_constructoras(current_user: dict = Depends(get_current_admin)):
    docs = await db.constructoras.find({}, {"_id": 0}).sort([("orden", 1), ("nombre", 1)]).to_list(500)
    return {"constructoras": [_to_public_dict(d) for d in docs]}


@router.post("/constructoras")
async def crear_constructora(
    nombre: str = Form(...),
    activo: bool = Form(True),
    orden: int = Form(0),
    logo: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_admin),
):
    nombre_clean = (nombre or "").strip()
    if not nombre_clean:
        raise HTTPException(400, "El nombre es requerido")

    logo_gridfs_id = None
    logo_content_type = None
    logo_filename = None
    if logo:
        content = await logo.read()
        if len(content) > MAX_LOGO_BYTES:
            raise HTTPException(400, f"Logo demasiado grande (>{MAX_LOGO_BYTES // (1024 * 1024)}MB)")
        ext = ("." + logo.filename.rsplit(".", 1)[-1].lower()) if "." in (logo.filename or "") else ""
        if logo.content_type not in ALLOWED_MIME and ext not in ALLOWED_EXT:
            raise HTTPException(400, "Formato de logo no permitido (PNG, JPG, WEBP o SVG)")
        storage = get_storage(db)
        logo_gridfs_id = await storage.save_file(
            content=content,
            filename=f"constructora_{uuid.uuid4()}{ext or '.png'}",
            content_type=logo.content_type or "image/png",
            metadata={"tipo": "logo_constructora"},
        )
        logo_content_type = logo.content_type or "image/png"
        logo_filename = logo.filename

    doc = {
        "id": str(uuid.uuid4()),
        "nombre": nombre_clean,
        "activo": bool(activo),
        "orden": int(orden),
        "logo_gridfs_id": logo_gridfs_id,
        "logo_content_type": logo_content_type,
        "logo_filename": logo_filename,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.constructoras.insert_one(doc)
    return _to_public_dict(doc)


@router.put("/constructoras/{constructora_id}")
async def actualizar_constructora(
    constructora_id: str,
    nombre: Optional[str] = Form(None),
    activo: Optional[bool] = Form(None),
    orden: Optional[int] = Form(None),
    logo: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_admin),
):
    doc = await db.constructoras.find_one({"id": constructora_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Constructora no encontrada")

    updates = {}
    if nombre is not None and nombre.strip():
        updates["nombre"] = nombre.strip()
    if activo is not None:
        updates["activo"] = bool(activo)
    if orden is not None:
        updates["orden"] = int(orden)

    if logo:
        content = await logo.read()
        if len(content) > MAX_LOGO_BYTES:
            raise HTTPException(400, f"Logo demasiado grande (>{MAX_LOGO_BYTES // (1024 * 1024)}MB)")
        ext = ("." + logo.filename.rsplit(".", 1)[-1].lower()) if "." in (logo.filename or "") else ""
        if logo.content_type not in ALLOWED_MIME and ext not in ALLOWED_EXT:
            raise HTTPException(400, "Formato de logo no permitido (PNG, JPG, WEBP o SVG)")
        storage = get_storage(db)
        # Reemplazar logo previo
        if doc.get("logo_gridfs_id"):
            try:
                await storage.delete_file(doc["logo_gridfs_id"])
            except Exception as e:
                logger.warning(f"No se pudo borrar logo previo: {e}")
        new_id = await storage.save_file(
            content=content,
            filename=f"constructora_{uuid.uuid4()}{ext or '.png'}",
            content_type=logo.content_type or "image/png",
            metadata={"tipo": "logo_constructora"},
        )
        updates["logo_gridfs_id"] = new_id
        updates["logo_content_type"] = logo.content_type or "image/png"
        updates["logo_filename"] = logo.filename

    if not updates:
        raise HTTPException(400, "Sin cambios")

    await db.constructoras.update_one({"id": constructora_id}, {"$set": updates})
    doc = await db.constructoras.find_one({"id": constructora_id}, {"_id": 0})
    return _to_public_dict(doc)


@router.delete("/constructoras/{constructora_id}")
async def eliminar_constructora(constructora_id: str, current_user: dict = Depends(get_current_admin)):
    doc = await db.constructoras.find_one({"id": constructora_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Constructora no encontrada")
    if doc.get("logo_gridfs_id"):
        try:
            storage = get_storage(db)
            await storage.delete_file(doc["logo_gridfs_id"])
        except Exception as e:
            logger.warning(f"Error borrando logo de GridFS: {e}")
    await db.constructoras.delete_one({"id": constructora_id})
    # Desasignar la constructora de cualquier proyecto vinculado
    await db.proyectos.update_many(
        {"constructora_id": constructora_id},
        {"$set": {"constructora_id": None}},
    )
    return {"deleted": True}
