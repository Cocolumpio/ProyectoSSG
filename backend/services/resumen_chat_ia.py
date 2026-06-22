"""Servicio IA para resumir el chat semanal de un grupo de WhatsApp de obra.

Enfatiza justificaciones de atraso, decisiones técnicas y riesgos.
Usa Claude Sonnet 4.5 vía emergentintegrations.
"""
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")

MAX_TRANSCRIPT_CHARS = 25000  # ~6000 tokens, deja margen para prompt + respuesta


async def resumir_chat_semanal(
    proyecto_nombre: str,
    semana: int,
    fecha_inicio: str,
    fecha_fin: str,
    transcript: str,
    avance_real_pct: float = None,
    avance_esperado_pct: float = None,
) -> str:
    """Genera un resumen ejecutivo del chat de la semana enfocado en justificaciones de atraso.

    Args:
        transcript: texto plano con líneas `[fecha hora] Autor: mensaje`.
        avance_real_pct, avance_esperado_pct: contexto opcional para que la IA correlacione.

    Returns: texto plano con el resumen.
    """
    if not transcript.strip():
        return f"📱 Sin actividad registrada en el grupo de WhatsApp del {fecha_inicio} al {fecha_fin}."

    # Truncar si es muy largo (preferir mensajes más recientes)
    if len(transcript) > MAX_TRANSCRIPT_CHARS:
        transcript = "[...inicio truncado...]\n" + transcript[-MAX_TRANSCRIPT_CHARS:]

    if not EMERGENT_LLM_KEY:
        return _fallback_resumen(transcript, fecha_inicio, fecha_fin)

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        contexto_avance = ""
        if avance_real_pct is not None and avance_esperado_pct is not None:
            desv = avance_real_pct - avance_esperado_pct
            contexto_avance = (
                f"\n\n📊 CONTEXTO DE AVANCE ESTA SEMANA:\n"
                f"  • Avance real: {avance_real_pct:.1f}%\n"
                f"  • Avance esperado: {avance_esperado_pct:.1f}%\n"
                f"  • Desviación: {desv:+.1f}%"
            )

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"resumen-wa-{proyecto_nombre[:20]}-s{semana}-{datetime.now().isoformat()[:10]}",
            system_message=(
                "Eres un analista experto en obras de construcción civil en México. "
                "Tu tarea es leer un chat de WhatsApp del equipo de obra y extraer "
                "lo verdaderamente importante para el control de avance, especialmente "
                "JUSTIFICACIONES DE ATRASO, decisiones técnicas y riesgos. "
                "Ignora bromas, saludos, mensajes irrelevantes. Escribe en español, "
                "tono profesional pero directo. No inventes datos que no estén en el chat."
            ),
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")

        prompt = f"""Resume el chat de la semana del equipo de obra del proyecto "{proyecto_nombre}".

📅 Periodo: SEMANA {semana} · {fecha_inicio} al {fecha_fin}{contexto_avance}

💬 TRANSCRIPCIÓN DEL CHAT (orden cronológico):
{transcript}

Genera el resumen con esta estructura (texto plano, sin Markdown):

🎯 RESUMEN EJECUTIVO
(2-3 oraciones clave sobre lo más importante de la semana)

⚠️ JUSTIFICACIONES DE ATRASO Y BLOQUEOS
(Lista los motivos reportados por el equipo: lluvia, falta de material, paro de maquinaria, falta de personal, retrasos de proveedor, decisiones técnicas que pararon avance, etc. Incluye fechas/días específicos si los mencionaron. Si no hay justificaciones, escribe "Sin justificaciones reportadas".)

🛠️ ACTIVIDADES REALIZADAS REPORTADAS
(Trabajos que el equipo dijo haber ejecutado esta semana)

📌 DECISIONES TÉCNICAS / CAMBIOS
(Modificaciones al plan, decisiones de campo relevantes)

🚨 RIESGOS Y ALERTAS
(Cualquier riesgo identificado o tema que requiera atención del director)

👥 PARTICIPANTES PRINCIPALES
(Quiénes intervinieron más, brevemente — útil para saber a quién consultar)

Si la información para alguna sección no aparece en el chat, escribe "Sin información reportada en el chat." en esa sección. Sé directo y específico — cita brevemente partes del chat cuando aporten valor. Mantén el resumen total bajo 1800 caracteres."""

        msg = UserMessage(text=prompt)
        response = await chat.send_message(msg)
        return str(response).strip()
    except Exception as e:
        logger.exception(f"Error generando resumen IA del chat: {e}")
        return _fallback_resumen(transcript, fecha_inicio, fecha_fin)


def _fallback_resumen(transcript: str, fecha_inicio: str, fecha_fin: str) -> str:
    """Resumen heurístico si la IA falla — extrae primeras líneas con keywords de atraso."""
    keywords = [
        "lluvia", "lluvi", "llovi", "agua", "clima",
        "atraso", "atras", "retraso", "retras",
        "no llego", "no llegó", "falta", "faltó", "sin",
        "paro", "paró", "averia", "avería", "descompuso",
        "mañana", "lunes", "martes", "miercoles", "jueves", "viernes",
    ]
    lineas = transcript.split("\n")
    relevantes = [l for l in lineas if any(k in l.lower() for k in keywords)]
    cuerpo = (
        "\n".join(relevantes[:10])
        if relevantes
        else "Sin mensajes con keywords de atraso/paro detectados."
    )
    return (
        f"📱 Resumen del grupo WhatsApp · {fecha_inicio} al {fecha_fin}\n\n"
        f"⚠️ POSIBLES JUSTIFICACIONES (extracto heurístico):\n{cuerpo}\n\n"
        f"_Resumen generado sin IA (servicio Claude no disponible)._"
    )
