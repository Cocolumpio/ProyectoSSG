"""Endpoints para resumir el chat semanal de un grupo de WhatsApp asociado a un proyecto."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.config import get_current_admin, get_db
from services import whatsapp_groups as wa_groups
from services import resumen_chat_ia

logger = logging.getLogger(__name__)
db = get_db()
router = APIRouter(prefix="/api")

# CDMX (UTC-6 sin DST)
TZ_CDMX_OFFSET_HOURS = -6


class VincularGrupo(BaseModel):
    chat_id: Optional[str] = None
    nombre: Optional[str] = None  # opcional, para mostrarlo en UI


@router.get("/whatsapp/grupos")
async def listar_grupos_endpoint(current_user: dict = Depends(get_current_admin)):
    """Lista todos los grupos de WhatsApp donde está el bot."""
    grupos = wa_groups.listar_grupos()
    return {"grupos": grupos, "total": len(grupos)}


@router.get("/whatsapp/grupos/auto-match/{proyecto_id}")
async def auto_match_grupo(
    proyecto_id: str,
    current_user: dict = Depends(get_current_admin),
):
    """Sugiere automáticamente un grupo para un proyecto basado en el nombre (flexible)."""
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(404, "Proyecto no encontrado")
    grupos = wa_groups.listar_grupos()
    encontrado = wa_groups.buscar_grupo_para_proyecto(proyecto["nombre"], grupos)
    return {
        "proyecto_nombre": proyecto["nombre"],
        "grupo_sugerido": encontrado,
        "total_grupos": len(grupos),
    }


@router.put("/proyectos/{proyecto_id}/whatsapp-grupo")
async def vincular_grupo(
    proyecto_id: str,
    payload: VincularGrupo,
    current_user: dict = Depends(get_current_admin),
):
    """Vincula o desvincula manualmente un grupo de WhatsApp a un proyecto."""
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(404, "Proyecto no encontrado")
    update = {
        "wa_grupo_chat_id": payload.chat_id or None,
        "wa_grupo_nombre": payload.nombre or None,
    }
    await db.proyectos.update_one({"id": proyecto_id}, {"$set": update})
    return {"ok": True, **update}


def _calcular_rango_semana(
    fecha_inicio_proyecto: str,
    semana: int,
) -> tuple[int, int, str, str]:
    """Calcula el rango Unix timestamp (lunes 00:00 → domingo 23:59:59 CDMX) de la semana N.

    Asume que la semana 1 inicia el lunes de la semana de `fecha_inicio_proyecto`.
    Returns: (desde_ts, hasta_ts, fecha_inicio_iso, fecha_fin_iso)
    """
    try:
        d0 = datetime.fromisoformat(fecha_inicio_proyecto.split("T")[0])
    except Exception:
        d0 = datetime.now(timezone.utc)
    # Lunes de la semana de d0
    lunes_s1 = d0 - timedelta(days=d0.weekday())
    lunes_n = lunes_s1 + timedelta(weeks=max(0, semana - 1))
    domingo_n = lunes_n + timedelta(days=6, hours=23, minutes=59, seconds=59)

    # Convertir a UTC asumiendo CDMX (UTC-6)
    desde_utc = lunes_n.replace(hour=0, minute=0, second=0, tzinfo=timezone.utc) - timedelta(hours=TZ_CDMX_OFFSET_HOURS)
    hasta_utc = domingo_n.replace(tzinfo=timezone.utc) - timedelta(hours=TZ_CDMX_OFFSET_HOURS)

    return (
        int(desde_utc.timestamp()),
        int(hasta_utc.timestamp()),
        lunes_n.strftime("%d/%m/%Y"),
        domingo_n.strftime("%d/%m/%Y"),
    )


async def _generar_y_guardar_resumen(
    proyecto: dict,
    semana: int,
    autor_id: str = "system",
    autor_nombre: str = "Resumen WhatsApp · IA",
) -> dict:
    """Lógica compartida entre endpoint manual y cron dominical."""
    chat_id = proyecto.get("wa_grupo_chat_id")
    if not chat_id:
        # Intentar auto-match
        grupos = wa_groups.listar_grupos()
        sug = wa_groups.buscar_grupo_para_proyecto(proyecto["nombre"], grupos)
        if not sug:
            return {"ok": False, "razon": "Sin grupo de WhatsApp vinculado y no se encontró auto-match"}
        chat_id = sug["chat_id"]

    desde_ts, hasta_ts, fini, ffin = _calcular_rango_semana(
        proyecto.get("fecha_inicio") or proyecto.get("fecha_fin_planeada") or "",
        semana,
    )
    diag = wa_groups.obtener_mensajes_grupo_diagnostico(chat_id, desde_ts, hasta_ts)
    mensajes = diag["filtrados"]
    transcript = wa_groups.formatear_mensajes_para_ia(mensajes)

    # Buscar avance real/esperado de esa semana para dar contexto a la IA
    avance_real_pct = None
    avance_esperado_pct = None
    try:
        from routes.alertas import _calcular_desviacion  # reuse helper
        info = await _calcular_desviacion(proyecto["id"])
        if info and info.get("semana_evaluada") == semana:
            avance_real_pct = info["avance_real_pct"]
            avance_esperado_pct = info["avance_esperado_pct"]
    except Exception:
        pass

    resumen = await resumen_chat_ia.resumir_chat_semanal(
        proyecto_nombre=proyecto["nombre"],
        semana=semana,
        fecha_inicio=fini,
        fecha_fin=ffin,
        transcript=transcript,
        avance_real_pct=avance_real_pct,
        avance_esperado_pct=avance_esperado_pct,
    )

    # Si no hubo mensajes en el rango, anexar diagnóstico para el usuario
    if not mensajes:
        from datetime import datetime as _dt
        info_diag_lines = [f"\n\n_📋 Diagnóstico Green API:_"]
        info_diag_lines.append(f"_• Mensajes obtenidos del grupo: {diag['total_obtenidos']}_")
        if diag.get("mas_nuevo_ts"):
            info_diag_lines.append(
                f"_• Mensaje más reciente: {_dt.fromtimestamp(diag['mas_nuevo_ts']).strftime('%d/%m/%Y %H:%M')}_"
            )
            info_diag_lines.append(
                f"_• Mensaje más antiguo: {_dt.fromtimestamp(diag['mas_viejo_ts']).strftime('%d/%m/%Y %H:%M')}_"
            )
        if diag.get("error"):
            info_diag_lines.append(f"_• Error: {diag['error']}_")
        if diag["total_obtenidos"] == 0:
            info_diag_lines.append(
                "_• Posible causa: el bot fue agregado recientemente al grupo; Green API solo guarda historial DESPUÉS de habilitar `enableMessagesHistory`. Asegúrate de que la configuración esté activa en console.green-api.com → Settings → 'Enable saving messages history'._"
            )
        elif diag["total_obtenidos"] > 0:
            info_diag_lines.append(
                f"_• Esos {diag['total_obtenidos']} mensajes están fuera del rango {fini} – {ffin}. Probablemente son anteriores._"
            )
        resumen += "\n".join(info_diag_lines)

    doc = {
        "proyecto_id": proyecto["id"],
        "semana": semana,
        "texto": resumen[:5000],
        "autor_id": autor_id,
        "autor_nombre": autor_nombre,
        "fuente": "whatsapp_ia",
        "wa_chat_id": chat_id,
        "mensajes_analizados": len(mensajes),
        "diagnostico_wa": {
            "total_obtenidos": diag["total_obtenidos"],
            "mas_nuevo_ts": diag.get("mas_nuevo_ts"),
            "mas_viejo_ts": diag.get("mas_viejo_ts"),
            "error": diag.get("error"),
        },
        "actualizado_en": datetime.now(timezone.utc).isoformat(),
    }
    await db.comentarios_semana.update_one(
        {"proyecto_id": proyecto["id"], "semana": semana},
        {"$set": doc},
        upsert=True,
    )
    return {
        "ok": True,
        "mensajes_analizados": len(mensajes),
        "mensajes_totales_obtenidos": diag["total_obtenidos"],
        "diagnostico_wa": doc["diagnostico_wa"],
        "fecha_inicio": fini,
        "fecha_fin": ffin,
        "resumen": resumen,
    }


@router.post("/proyectos/{proyecto_id}/resumen-whatsapp-semana/{semana}")
async def generar_resumen_manual(
    proyecto_id: str,
    semana: int,
    current_user: dict = Depends(get_current_admin),
):
    """Dispara manualmente el resumen del chat para una semana específica."""
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(404, "Proyecto no encontrado")
    res = await _generar_y_guardar_resumen(
        proyecto,
        semana,
        autor_id=current_user["id"],
        autor_nombre=f"Resumen WhatsApp · IA (manual por {current_user.get('nombre') or current_user.get('email')})",
    )
    if not res.get("ok"):
        raise HTTPException(400, res.get("razon", "Error desconocido"))
    return res


async def cron_resumen_semanal_dominical():
    """Cron: cada domingo 22:00 CDMX, genera el resumen de la semana actual
    para todos los proyectos activos.

    Calcula qué semana del proyecto corresponde a HOY y dispara el resumen.
    """
    logger.info("🗓️  Cron dominical: iniciando resumen WhatsApp semanal")
    try:
        proyectos = await db.proyectos.find({}, {"_id": 0}).to_list(500)
        ahora = datetime.now(timezone.utc)
        total_ok = 0
        for p in proyectos:
            try:
                fini_str = p.get("fecha_inicio")
                if not fini_str:
                    continue
                try:
                    fini = datetime.fromisoformat(fini_str.split("T")[0]).replace(tzinfo=timezone.utc)
                except Exception:
                    continue
                # Saltar si la fecha de inicio es futura
                if ahora < fini:
                    continue
                # Calcular semana actual (1-based)
                lunes_s1 = fini - timedelta(days=fini.weekday())
                dias = (ahora - lunes_s1).days
                semana_actual = max(1, (dias // 7) + 1)
                # Si el proyecto tiene semanas planeadas y ya pasaron, saltar
                if p.get("semanas_planeadas") and semana_actual > int(p["semanas_planeadas"]) + 1:
                    continue
                res = await _generar_y_guardar_resumen(
                    p,
                    semana_actual,
                    autor_id="system",
                    autor_nombre="Resumen WhatsApp · IA (automático dominical)",
                )
                if res.get("ok"):
                    total_ok += 1
                    logger.info(
                        f"  ✓ {p['nombre']} sem {semana_actual}: "
                        f"{res['mensajes_analizados']} mensajes resumidos"
                    )
                else:
                    logger.info(f"  · {p['nombre']} saltado: {res.get('razon')}")
            except Exception as e:
                logger.exception(f"Error procesando {p.get('nombre')}: {e}")
        logger.info(f"🗓️  Cron dominical OK: {total_ok}/{len(proyectos)} proyectos resumidos")
    except Exception as e:
        logger.exception(f"Error en cron dominical: {e}")
