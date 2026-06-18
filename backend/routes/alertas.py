"""Alertas de desviación: detecta atraso ≥10% vs programa y envía WhatsApp + IA."""
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.config import get_current_admin, get_current_user, get_db
from services import whatsapp as wa_service
from services import ia_recomendacion as ia_service

logger = logging.getLogger(__name__)
db = get_db()
router = APIRouter(prefix="/api")

UMBRAL_DESVIACION = -10.0  # ≤ -10% dispara alerta


async def _calcular_desviacion(proyecto_id: str) -> Optional[dict]:
    """Calcula avance real vs esperado en la última semana con avance.

    Devuelve dict con: avance_real_pct, avance_esperado_pct, desviacion_pct,
    semana_actual, fases_desviadas, proyecto_doc; o None si no aplica.
    """
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto or not proyecto.get("programa_semanal"):
        return None

    programa = proyecto["programa_semanal"]
    avances = await db.avances_semanales.find(
        {"proyecto_id": proyecto_id}, {"_id": 0}
    ).sort("semana", 1).to_list(500)
    avances_por_sem = {int(a.get("semana", 0)): a for a in avances}

    # Encontrar la última semana con métricas reales > 0
    ultima_con_avance = None
    for sem in programa:
        n = int(sem.get("semana") or 0)
        av = avances_por_sem.get(n) or {}
        if any(float(av.get(k, 0) or 0) > 0 for k in
               ("volumen_excavacion", "pilas_completadas", "anclas_instaladas", "muros_completados")):
            ultima_con_avance = sem
    if not ultima_con_avance:
        return None
    n_eval = int(ultima_con_avance["semana"])

    # Calcular acumulado planeado y real hasta n_eval
    plan_acum = {"excavacion": 0.0, "pilas": 0.0, "anclas": 0.0, "muros": 0.0}
    real_acum = {"excavacion": 0.0, "pilas": 0.0, "anclas": 0.0, "muros": 0.0}
    for sem in programa:
        if int(sem.get("semana") or 0) > n_eval:
            break
        plan_acum["excavacion"] += float(sem.get("excavacion_m3") or 0)
        plan_acum["pilas"] += float(sem.get("pilas") or 0)
        plan_acum["anclas"] += float(sem.get("anclas") or 0)
        plan_acum["muros"] += float(sem.get("muros_m2") or 0)
        av = avances_por_sem.get(int(sem.get("semana") or 0)) or {}
        real_acum["excavacion"] += float(av.get("volumen_excavacion") or 0)
        real_acum["pilas"] += float(av.get("pilas_completadas") or 0)
        real_acum["anclas"] += float(av.get("anclas_instaladas") or 0)
        real_acum["muros"] += float(av.get("muros_completados") or 0)

    tot = {
        "excavacion": float(proyecto.get("volumen_total_planeado") or 0),
        "pilas": float(proyecto.get("pilas_planeadas") or 0),
        "anclas": float(proyecto.get("anclas_planeadas") or 0),
        "muros": float(proyecto.get("muros_planeados") or 0),
    }

    pcts_esperado, pcts_real = [], []
    fases_desviadas: List[dict] = []
    mapping = {
        "excavacion": ("Excavación", "m³"),
        "pilas": ("Pilas", "pzs"),
        "anclas": ("Anclas", "pzs"),
        "muros": ("Muros", "m²"),
    }
    for key, (label, unidad) in mapping.items():
        if tot[key] <= 0 or plan_acum[key] <= 0:
            continue
        esp = min(plan_acum[key] / tot[key] * 100, 100)
        rl = min(real_acum[key] / tot[key] * 100, 100)
        pcts_esperado.append(esp)
        pcts_real.append(rl)
        desv = rl - esp
        if desv <= -5:
            fases_desviadas.append({
                "nombre": label,
                "planeado": round(plan_acum[key], 2),
                "real": round(real_acum[key], 2),
                "unidad": unidad,
                "desviacion_pct": round(desv, 1),
            })

    if not pcts_esperado:
        return None

    avance_real_pct = sum(pcts_real) / len(pcts_real)
    avance_esperado_pct = sum(pcts_esperado) / len(pcts_esperado)
    desviacion_pct = avance_real_pct - avance_esperado_pct

    return {
        "proyecto": proyecto,
        "avance_real_pct": round(avance_real_pct, 1),
        "avance_esperado_pct": round(avance_esperado_pct, 1),
        "desviacion_pct": round(desviacion_pct, 1),
        "semana_evaluada": n_eval,
        "fases_desviadas": fases_desviadas,
    }


def _build_whatsapp_body(info: dict, recomendacion: str) -> str:
    proyecto = info["proyecto"]
    nombre = proyecto.get("nombre", "Proyecto")
    ubicacion = proyecto.get("ubicacion") or proyecto.get("direccion") or ""
    desv = info["desviacion_pct"]

    fases_txt = "\n".join(
        f"  • {f['nombre']}: {f['real']} de {f['planeado']} {f['unidad']} ({f['desviacion_pct']:+.1f}%)"
        for f in info["fases_desviadas"]
    ) or "  (Sin fases específicas identificadas)"

    return (
        f"🚨 *Alerta de Desviación* — DrON Topografía\n\n"
        f"🏗️ *{nombre}*\n"
        f"{f'📍 {ubicacion}' if ubicacion else ''}\n"
        f"📅 Semana evaluada: {info['semana_evaluada']}\n\n"
        f"📉 *Desviación:* {desv:+.1f}%\n"
        f"Avance real: {info['avance_real_pct']:.1f}%  |  Esperado: {info['avance_esperado_pct']:.1f}%\n\n"
        f"*Conceptos desviados:*\n{fases_txt}\n\n"
        f"────────────────\n"
        f"{recomendacion}\n"
        f"────────────────\n"
        f"_Mensaje generado automáticamente._"
    )


@router.post("/proyectos/{proyecto_id}/alerta-desviacion")
async def disparar_alerta(
    proyecto_id: str,
    forzar: bool = False,
    current_user: dict = Depends(get_current_admin),
):
    """Calcula desviación; si supera umbral, envía WhatsApp a directores activos
    con recomendación de IA. Idempotente (1 alerta por semana evaluada salvo forzar=true).
    """
    info = await _calcular_desviacion(proyecto_id)
    if not info:
        raise HTTPException(400, "El proyecto no tiene programa o no hay avances reales todavía")

    if info["desviacion_pct"] > UMBRAL_DESVIACION and not forzar:
        return {
            "alerta_enviada": False,
            "razon": f"Desviación de {info['desviacion_pct']:.1f}% no supera umbral ({UMBRAL_DESVIACION}%)",
            **info,
        }

    # Idempotencia: ya alertado en esta semana?
    key = f"{proyecto_id}:{info['semana_evaluada']}"
    if not forzar:
        existente = await db.alertas_enviadas.find_one({"key": key})
        if existente:
            return {
                "alerta_enviada": False,
                "razon": "Ya se envió alerta para esta semana del proyecto. Usa forzar=true.",
                **info,
            }

    # Generar recomendación IA
    recomendacion = await ia_service.generar_recomendacion(
        proyecto_nombre=info["proyecto"].get("nombre", ""),
        avance_real_pct=info["avance_real_pct"],
        avance_esperado_pct=info["avance_esperado_pct"],
        desviacion_pct=info["desviacion_pct"],
        semana_actual=info["semana_evaluada"],
        fases_desviadas=info["fases_desviadas"],
        ubicacion=info["proyecto"].get("ubicacion") or "",
    )

    # Obtener directores activos
    directores = await db.directores.find(
        {"activo": True}, {"_id": 0}
    ).to_list(100)
    if not directores:
        return {
            "alerta_enviada": False,
            "razon": "No hay directores activos configurados",
            **info,
        }

    body = _build_whatsapp_body(info, recomendacion)
    resultados = wa_service.enviar_a_lista(directores, body)
    exitosos = sum(1 for r in resultados if r.get("success"))

    # Registrar en historial
    await db.alertas_enviadas.insert_one({
        "key": key,
        "proyecto_id": proyecto_id,
        "proyecto_nombre": info["proyecto"].get("nombre"),
        "semana_evaluada": info["semana_evaluada"],
        "desviacion_pct": info["desviacion_pct"],
        "destinatarios": len(directores),
        "exitosos": exitosos,
        "resultados": resultados,
        "recomendacion": recomendacion,
        "enviado_at": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "alerta_enviada": True,
        "destinatarios_total": len(directores),
        "destinatarios_exitosos": exitosos,
        "recomendacion": recomendacion,
        "resultados": resultados,
        **info,
    }


@router.get("/proyectos/{proyecto_id}/alertas-historial")
async def historial_alertas(
    proyecto_id: str,
    current_user: dict = Depends(get_current_user),
):
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(404, "Proyecto no encontrado")
    if current_user.get("rol") == "client":
        if current_user["id"] not in (proyecto.get("clientes_asignados") or []):
            raise HTTPException(403, "Sin acceso")

    docs = await db.alertas_enviadas.find(
        {"proyecto_id": proyecto_id}, {"_id": 0}
    ).sort("enviado_at", -1).to_list(100)
    return {"alertas": docs}


# ----------- AUTO-TRIGGER: hook para invocar después de subir avance -----------

async def evaluar_y_disparar_si_aplica(proyecto_id: str) -> Optional[dict]:
    """Helper para ser llamado desde el flujo de upload de avance semanal.

    Evalúa la desviación; si supera umbral y no se ha enviado antes, dispara WhatsApp.
    Nunca lanza excepción.
    """
    try:
        info = await _calcular_desviacion(proyecto_id)
        if not info or info["desviacion_pct"] > UMBRAL_DESVIACION:
            return None
        key = f"{proyecto_id}:{info['semana_evaluada']}"
        if await db.alertas_enviadas.find_one({"key": key}):
            return None

        recomendacion = await ia_service.generar_recomendacion(
            proyecto_nombre=info["proyecto"].get("nombre", ""),
            avance_real_pct=info["avance_real_pct"],
            avance_esperado_pct=info["avance_esperado_pct"],
            desviacion_pct=info["desviacion_pct"],
            semana_actual=info["semana_evaluada"],
            fases_desviadas=info["fases_desviadas"],
            ubicacion=info["proyecto"].get("ubicacion") or "",
        )
        directores = await db.directores.find({"activo": True}, {"_id": 0}).to_list(100)
        if not directores:
            return None
        body = _build_whatsapp_body(info, recomendacion)
        resultados = wa_service.enviar_a_lista(directores, body)
        exitosos = sum(1 for r in resultados if r.get("success"))
        await db.alertas_enviadas.insert_one({
            "key": key,
            "proyecto_id": proyecto_id,
            "proyecto_nombre": info["proyecto"].get("nombre"),
            "semana_evaluada": info["semana_evaluada"],
            "desviacion_pct": info["desviacion_pct"],
            "destinatarios": len(directores),
            "exitosos": exitosos,
            "resultados": resultados,
            "recomendacion": recomendacion,
            "trigger": "auto",
            "enviado_at": datetime.now(timezone.utc).isoformat(),
        })
        return {"alerta_enviada": True, "destinatarios": len(directores), "exitosos": exitosos}
    except Exception as e:
        logger.exception(f"Error en alerta automática: {e}")
        return None


# ----------- COMENTARIOS POR SEMANA -----------

class ComentarioSemana(BaseModel):
    texto: str


@router.put("/proyectos/{proyecto_id}/comentario-semana/{semana}")
async def actualizar_comentario(
    proyecto_id: str,
    semana: int,
    payload: ComentarioSemana,
    current_user: dict = Depends(get_current_admin),
):
    """Crea o actualiza el comentario único de admin para esa semana."""
    doc = {
        "proyecto_id": proyecto_id,
        "semana": semana,
        "texto": (payload.texto or "").strip()[:2000],
        "autor_id": current_user["id"],
        "autor_nombre": current_user.get("nombre") or current_user.get("email"),
        "actualizado_en": datetime.now(timezone.utc).isoformat(),
    }
    await db.comentarios_semana.update_one(
        {"proyecto_id": proyecto_id, "semana": semana},
        {"$set": doc},
        upsert=True,
    )
    return doc


@router.get("/proyectos/{proyecto_id}/comentarios-semana")
async def listar_comentarios(
    proyecto_id: str,
    current_user: dict = Depends(get_current_user),
):
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(404, "Proyecto no encontrado")
    if current_user.get("rol") == "client":
        if current_user["id"] not in (proyecto.get("clientes_asignados") or []):
            raise HTTPException(403, "Sin acceso")

    docs = await db.comentarios_semana.find(
        {"proyecto_id": proyecto_id}, {"_id": 0}
    ).sort("semana", 1).to_list(500)
    return {"comentarios": docs}


@router.delete("/proyectos/{proyecto_id}/comentario-semana/{semana}")
async def borrar_comentario(
    proyecto_id: str,
    semana: int,
    current_user: dict = Depends(get_current_admin),
):
    await db.comentarios_semana.delete_one({"proyecto_id": proyecto_id, "semana": semana})
    return {"deleted": True}
