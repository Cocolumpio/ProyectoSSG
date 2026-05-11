"""
Helper para crear notificaciones del sistema desde cualquier módulo.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from core.config import get_db


async def crear_notificacion_sistema(
    tipo: str,
    titulo: str,
    mensaje: str,
    proyecto_id: Optional[str] = None,
    proyecto_nombre: Optional[str] = None,
    usuario_id: Optional[str] = None,
    link: Optional[str] = None,
    metadata: Optional[dict] = None,
):
    """Crea una notificación en la BD y la devuelve."""
    db = get_db()
    notif_data = {
        "id": str(uuid.uuid4()),
        "tipo": tipo,
        "titulo": titulo,
        "mensaje": mensaje,
        "proyecto_id": proyecto_id,
        "proyecto_nombre": proyecto_nombre,
        "usuario_id": usuario_id,
        "leida": False,
        "fecha": datetime.now(timezone.utc).isoformat(),
        "link": link,
        "metadata": metadata,
    }
    try:
        await db.notificaciones.insert_one(notif_data)
    except Exception as e:
        logging.error(f"Error creando notificación: {e}")
    notif_data.pop("_id", None)
    return notif_data
