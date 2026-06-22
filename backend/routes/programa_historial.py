"""Historial de cambios en el programa de obra de un proyecto.

Cada vez que se actualiza el programa (subida de Excel o edición manual de
métricas clave), se guarda una versión snapshot con los totales planeados y
las deltas vs la versión anterior. Esto permite detectar y graficar cambios
"de maquillaje" (residentes/coordinadores ajustando metas para encubrir atrasos).
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from core.config import get_current_admin, get_current_user, get_db
from services import whatsapp_groups as wa_groups
from services import resumen_chat_ia

logger = logging.getLogger(__name__)
db = get_db()
router = APIRouter(prefix="/api")


_FIELDS_NUM = ("volumen_total_planeado", "pilas_planeadas", "anclas_planeadas",
               "muros_planeados", "perfiles_planeados", "semanas_planeadas")


def _extraer_totales(proyecto: dict) -> dict:
    """Extrae métricas-clave de un documento proyecto."""
    programa = proyecto.get("programa_semanal") or []
    return {
        "volumen_total_planeado": float(proyecto.get("volumen_total_planeado") or 0),
        "pilas_planeadas": float(proyecto.get("pilas_planeadas") or 0),
        "anclas_planeadas": float(proyecto.get("anclas_planeadas") or 0),
        "muros_planeados": float(proyecto.get("muros_planeados") or 0),
        "perfiles_planeados": float(proyecto.get("perfiles_planeados") or 0),
        "semanas_planeadas": int(proyecto.get("semanas_planeadas") or len(programa) or 0),
        "semanas_en_programa": len(programa),
    }


def _calcular_delta(prev: Optional[dict], curr: dict) -> dict:
    """Calcula delta absoluto y porcentual entre dos snapshots de totales."""
    if not prev:
        return {}
    delta = {}
    for k, v in curr.items():
        anterior = float(prev.get(k) or 0)
        abs_delta = v - anterior
        pct = (abs_delta / anterior * 100) if anterior else (100.0 if abs_delta else 0.0)
        delta[k] = {"anterior": anterior, "actual": v, "abs": round(abs_delta, 2), "pct": round(pct, 2)}
    return delta


async def guardar_snapshot(
    proyecto_id: str,
    user: dict,
    fuente: str = "manual",
    motivo: Optional[str] = None,
) -> Optional[dict]:
    """Persiste una versión del programa de obra para auditoría.

    fuente: 'excel' | 'manual' | 'sistema'
    motivo: texto libre opcional (puede inferirse luego desde WhatsApp).
    """
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        return None
    totales = _extraer_totales(proyecto)

    # Última versión previa
    prev = await db.programa_obra_historial.find_one(
        {"proyecto_id": proyecto_id},
        sort=[("created_at", -1)],
        projection={"_id": 0, "totales": 1},
    )
    if prev:
        # Si los totales son idénticos a la última versión, no guardamos otra.
        if all(prev["totales"].get(k) == totales.get(k) for k in totales):
            return None

    delta = _calcular_delta(prev.get("totales") if prev else None, totales)

    # Versión incremental
    count = await db.programa_obra_historial.count_documents({"proyecto_id": proyecto_id})
    version = count + 1

    doc = {
        "id": f"hist-{proyecto_id}-{version}",
        "proyecto_id": proyecto_id,
        "version": version,
        "fuente": fuente,
        "totales": totales,
        "delta_vs_anterior": delta,
        "motivo": motivo or "",
        "autor_id": (user or {}).get("id") or "system",
        "autor_nombre": (user or {}).get("nombre") or (user or {}).get("email") or "Sistema",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.programa_obra_historial.insert_one(doc)
    # Sin _id
    doc.pop("_id", None)
    logger.info(f"📝 Snapshot programa v{version} guardado para {proyecto.get('nombre')} ({fuente})")
    return doc


@router.get("/proyectos/{proyecto_id}/programa-historial")
async def listar_historial(
    proyecto_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Lista todas las versiones del programa de obra del proyecto."""
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(404, "Proyecto no encontrado")
    if current_user.get("rol") == "client":
        if current_user["id"] not in (proyecto.get("clientes_asignados") or []):
            raise HTTPException(403, "Sin acceso")

    docs = await db.programa_obra_historial.find(
        {"proyecto_id": proyecto_id}, {"_id": 0}
    ).sort("version", 1).to_list(500)

    return {
        "proyecto_id": proyecto_id,
        "proyecto_nombre": proyecto.get("nombre"),
        "total_versiones": len(docs),
        "versiones": docs,
    }


@router.post("/proyectos/{proyecto_id}/programa-historial/{version}/inferir-motivo")
async def inferir_motivo_desde_whatsapp(
    proyecto_id: str,
    version: int,
    current_user: dict = Depends(get_current_admin),
):
    """Busca en el grupo de WhatsApp del proyecto los mensajes ±48 h alrededor
    del cambio del programa y pide a la IA un resumen del motivo probable.
    """
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(404, "Proyecto no encontrado")
    chat_id = proyecto.get("wa_grupo_chat_id")
    if not chat_id:
        raise HTTPException(400, "Este proyecto no tiene grupo de WhatsApp vinculado")

    doc = await db.programa_obra_historial.find_one(
        {"proyecto_id": proyecto_id, "version": version}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Versión no encontrada")

    # Ventana de 48 h alrededor del cambio (24h antes y 24h después)
    try:
        cambio_dt = datetime.fromisoformat(doc["created_at"].replace("Z", "+00:00"))
    except Exception:
        cambio_dt = datetime.now(timezone.utc)
    desde_ts = int((cambio_dt - timedelta(hours=24)).timestamp())
    hasta_ts = int((cambio_dt + timedelta(hours=24)).timestamp())
    mensajes = wa_groups.obtener_mensajes_grupo(chat_id, desde_ts, hasta_ts)
    transcript = wa_groups.formatear_mensajes_para_ia(mensajes)

    if not transcript.strip():
        motivo = "Sin mensajes en el grupo en las 48 h alrededor del cambio."
    else:
        # Resumimos pidiendo enfoque en cambios de programa / metas
        prompt_ctx = (
            f"Cambios detectados en este snapshot (v{version}):\n"
            + "\n".join(
                f"  • {k}: {d['anterior']} → {d['actual']} ({d['pct']:+.1f}%)"
                for k, d in (doc.get("delta_vs_anterior") or {}).items()
                if d.get("abs")
            )
            + "\n\nAnaliza el chat y dime EN MÁXIMO 4 LÍNEAS cuál es el motivo "
              "probable de estos cambios. Si no hay justificación clara, dilo."
        )
        motivo = await resumen_chat_ia.resumir_chat_semanal(
            proyecto_nombre=proyecto["nombre"],
            semana=version,
            fecha_inicio=(cambio_dt - timedelta(hours=24)).strftime("%d/%m/%Y"),
            fecha_fin=(cambio_dt + timedelta(hours=24)).strftime("%d/%m/%Y"),
            transcript=transcript + "\n\n" + prompt_ctx,
        )

    await db.programa_obra_historial.update_one(
        {"proyecto_id": proyecto_id, "version": version},
        {"$set": {"motivo": motivo[:3000], "motivo_fuente": "whatsapp_ia"}},
    )
    return {"ok": True, "motivo": motivo, "mensajes_analizados": len(mensajes)}


def detectar_cambio_metricas(antes: dict, despues: dict) -> bool:
    """Devuelve True si algún campo relevante cambió."""
    for f in _FIELDS_NUM:
        a = float(antes.get(f) or 0)
        b = float(despues.get(f) or 0)
        if a != b:
            return True
    # programa_semanal: hash por longitud + suma total
    pa = antes.get("programa_semanal") or []
    pb = despues.get("programa_semanal") or []
    if len(pa) != len(pb):
        return True
    return False
