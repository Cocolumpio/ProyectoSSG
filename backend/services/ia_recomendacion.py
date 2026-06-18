"""Servicio IA para generar recomendaciones de plan de recuperación ante desviación."""
import logging
import os
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")


async def generar_recomendacion(
    proyecto_nombre: str,
    avance_real_pct: float,
    avance_esperado_pct: float,
    desviacion_pct: float,
    semana_actual: int,
    fases_desviadas: List[Dict],
    ubicacion: str = "",
) -> str:
    """Genera una recomendación con Claude Sonnet 4.5 vía emergentintegrations.

    Args:
        fases_desviadas: lista [{nombre, planeado, real, unidad, desviacion_pct}]

    Returns:
        Texto plano con recomendaciones estructuradas.
    """
    if not EMERGENT_LLM_KEY:
        return _fallback_recomendacion(fases_desviadas, desviacion_pct)

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"alerta-{proyecto_nombre[:20]}-{datetime.now().isoformat()}",
            system_message=(
                "Eres un experto Gerente de Proyectos de Construcción Civil en México con 20 años "
                "de experiencia en obras de excavación, anclajes, pilas de cimentación y muros "
                "Milán. Tu rol es identificar la raíz de las desviaciones y proponer planes de "
                "recuperación CONCRETOS y ACCIONABLES. Habla directo y profesional, en español."
            ),
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")

        fases_texto = "\n".join(
            f"  • {f['nombre']}: planeado {f['planeado']} {f['unidad']} — "
            f"real {f['real']} {f['unidad']} ({f['desviacion_pct']:+.1f}%)"
            for f in fases_desviadas
        )

        prompt = f"""Analiza esta desviación de obra y proporciona un PLAN DE RECUPERACIÓN concreto.

📍 PROYECTO: {proyecto_nombre}
{f'📍 UBICACIÓN: {ubicacion}' if ubicacion else ''}
📊 AVANCE REAL: {avance_real_pct:.1f}%
🎯 AVANCE ESPERADO: {avance_esperado_pct:.1f}%
⚠️ DESVIACIÓN: {desviacion_pct:+.1f}%
📅 SEMANA EVALUADA: {semana_actual}

🔍 FASES DESVIADAS:
{fases_texto}

Estructura tu respuesta así, sin Markdown (texto plano para WhatsApp):

🎯 DIAGNÓSTICO PROBABLE
(1-2 oraciones sobre la causa más probable según la fase desviada)

❓ PREGUNTAS CLAVE PARA EL RESIDENTE/COORDINADOR
(3-4 preguntas específicas y técnicas — no genéricas — que el director debe hacer hoy mismo)

🛠️ ACCIONES INMEDIATAS (esta semana)
(2-3 acciones concretas, ej: revisar rendimiento de maquinaria específica, contratar segundo turno, validar suministro de material X)

📋 REVISAR EN EL PROGRAMA DE OBRA
(¿hay algo en la planeación original que pudiera estar mal calculado? Sé específico — ej: rendimiento de excavación m³/día asumido, tiempos de fraguado, ventana climática)

💡 PLAN DE RECUPERACIÓN
(propuesta concreta para recuperar el atraso — ej: trabajar sábado, paralelizar X con Y)

Sé directo, técnico y específico. No uses lenguaje genérico. Mantén toda la respuesta bajo 1200 caracteres."""

        msg = UserMessage(text=prompt)
        response = await chat.send_message(msg)
        return str(response).strip()

    except Exception as e:
        logger.exception(f"Error generando recomendación IA: {e}")
        return _fallback_recomendacion(fases_desviadas, desviacion_pct)


def _fallback_recomendacion(fases_desviadas: List[Dict], desviacion_pct: float) -> str:
    """Recomendación de fallback si la IA falla — basada en reglas heurísticas."""
    lineas = ["🎯 DIAGNÓSTICO PROBABLE"]

    diagnosticos = []
    preguntas = []
    acciones = []

    for f in fases_desviadas:
        nombre = (f.get("nombre") or "").lower()
        if "excav" in nombre:
            diagnosticos.append("Rendimiento bajo de excavación — posible avería o falta de maquinaria")
            preguntas.append("¿Cuántas horas-máquina reales tuvimos esta semana vs lo planeado?")
            preguntas.append("¿La retroexcavadora tuvo paros por mantenimiento o combustible?")
            acciones.append("Verificar bitácora de operador y rendimiento m³/hora")
            acciones.append("Validar si hay material no clasificado (roca) que requiera otra máquina")
        elif "ancla" in nombre:
            diagnosticos.append("Instalación de anclajes detrás del programa")
            preguntas.append("¿Hubo problemas de tensado o pruebas de carga?")
            preguntas.append("¿La perforadora opera en horario completo?")
            acciones.append("Revisar disponibilidad de toron y lechada")
        elif "pila" in nombre or "cimen" in nombre:
            diagnosticos.append("Cimentación con rezago — pilas/perforaciones")
            preguntas.append("¿Está disponible el equipo piloteador todos los días?")
            acciones.append("Coordinar entrega de acero/concreto y verificar permisos")
        elif "muro" in nombre:
            diagnosticos.append("Avance de muros menor a lo programado")
            preguntas.append("¿Hubo retrasos en cimbra, armado o colado?")
            acciones.append("Revisar suministro de concreto premezclado")

    lineas.append((" — ".join(diagnosticos) or "Atraso generalizado en obra") + ".")
    lineas.append("")
    lineas.append("❓ PREGUNTAS CLAVE")
    lineas.extend(f"  • {p}" for p in (preguntas or [
        "¿Cuál es el porcentaje real de jornada laboral aprovechada?",
        "¿Hubo factores climáticos, de suministro o de personal que justifiquen el atraso?",
        "¿La planeación original es realista o requiere ajuste?",
    ])[:4])
    lineas.append("")
    lineas.append("🛠️ ACCIONES INMEDIATAS")
    lineas.extend(f"  • {a}" for a in (acciones or [
        "Reunión técnica con residente y coordinador esta semana",
        "Revisar bitácora diaria de los últimos 7 días",
    ])[:3])
    lineas.append("")
    lineas.append("📋 REVISAR PROGRAMA DE OBRA")
    lineas.append("Validar que los rendimientos asumidos (m³/día, pzas/día) sean reales y no teóricos.")
    if abs(desviacion_pct) > 20:
        lineas.append("Considerar re-baselinear el cronograma si la desviación supera el 20%.")
    lineas.append("")
    lineas.append("💡 PLAN DE RECUPERACIÓN")
    lineas.append("Evaluar segundo turno o trabajo sabatino en la fase crítica para recuperar el atraso.")

    return "\n".join(lineas)
