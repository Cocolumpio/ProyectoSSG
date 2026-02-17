"""
Funciones auxiliares compartidas para DrON Topografía
"""
import logging
from datetime import datetime
from urllib.parse import quote
from typing import Optional

from core.config import get_db

logger = logging.getLogger(__name__)


async def recalcular_avance_proyecto(proyecto_id: str) -> float:
    """
    Recalcula el porcentaje de avance de un proyecto como PROMEDIO de todas las fases activas:
    - Excavación: volumen total planeado vs excavado
    - Cimentación: (pilas + anclas) / 2 si ambas tienen metas
    - Edificación: muros planeados vs completados
    
    El avance TOTAL es el promedio de todas las fases que tengan metas configuradas.
    
    Returns:
        El nuevo porcentaje de avance calculado
    """
    db = get_db()
    
    # Obtener el proyecto
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        return 0
    
    tipos = proyecto.get('actividades_tipo', [])
    
    # Obtener todos los avances semanales
    avances = await db.avances_semanales.find(
        {"proyecto_id": proyecto_id}
    ).to_list(1000)
    
    # Calcular totales ejecutados
    volumen_excavado = sum((a.get('volumen_excavacion', 0) or 0) for a in avances)
    pilas_completadas = sum((a.get('pilas_completadas', 0) or 0) for a in avances)
    anclas_instaladas = sum((a.get('anclas_instaladas', 0) or 0) for a in avances)
    muros_completados = sum((a.get('muros_completados', 0) or 0) for a in avances)
    
    # Obtener metas
    volumen_planeado = proyecto.get('volumen_total_planeado', 0) or 0
    pilas_planeadas = proyecto.get('pilas_planeadas', 0) or 0
    anclas_planeadas = proyecto.get('anclas_planeadas', 0) or 0
    muros_planeados = proyecto.get('muros_planeados', 0) or 0
    
    # Calcular porcentajes por fase
    porcentajes = []
    
    # Excavación
    if 'excavacion' in tipos or volumen_planeado > 0:
        if volumen_planeado > 0:
            pct_excavacion = min((volumen_excavado / volumen_planeado) * 100, 100)
            porcentajes.append(pct_excavacion)
    
    # Cimentación (pilas + anclas)
    if 'pilas' in tipos or 'anclas' in tipos or pilas_planeadas > 0 or anclas_planeadas > 0:
        pct_cimentacion_parts = []
        if pilas_planeadas > 0:
            pct_cimentacion_parts.append(min((pilas_completadas / pilas_planeadas) * 100, 100))
        if anclas_planeadas > 0:
            pct_cimentacion_parts.append(min((anclas_instaladas / anclas_planeadas) * 100, 100))
        if pct_cimentacion_parts:
            porcentajes.append(sum(pct_cimentacion_parts) / len(pct_cimentacion_parts))
    
    # Edificación (muros)
    if 'muros' in tipos or muros_planeados > 0:
        if muros_planeados > 0:
            pct_edificacion = min((muros_completados / muros_planeados) * 100, 100)
            porcentajes.append(pct_edificacion)
    
    # Avance total = promedio de todas las fases
    nuevo_avance = 0
    if porcentajes:
        nuevo_avance = sum(porcentajes) / len(porcentajes)
    
    nuevo_avance = round(nuevo_avance, 2)
    
    # Actualizar el proyecto con todos los totales ejecutados
    await db.proyectos.update_one(
        {"id": proyecto_id},
        {"$set": {
            "avance_actual": nuevo_avance,
            "volumen_ejecutado": volumen_excavado,
            "pilas_ejecutadas": pilas_completadas,
            "anclas_ejecutadas": anclas_instaladas,
            "muros_ejecutados": muros_completados
        }}
    )
    
    logger.info(f"Proyecto {proyecto_id} actualizado: avance={nuevo_avance:.2f}%")
    return nuevo_avance


def generar_google_calendar_link(
    titulo: str,
    fecha: str,
    hora: Optional[str],
    descripcion: str,
    ubicacion: str = ""
) -> str:
    """Genera un link para agregar evento a Google Calendar"""
    # Formatear fecha y hora para Google Calendar
    fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
    
    if hora:
        try:
            hora_dt = datetime.strptime(hora, "%H:%M")
            fecha_inicio = fecha_dt.replace(hour=hora_dt.hour, minute=hora_dt.minute)
            fecha_fin = fecha_dt.replace(hour=hora_dt.hour + 2)  # 2 horas de duración
        except ValueError:
            fecha_inicio = fecha_dt.replace(hour=9, minute=0)
            fecha_fin = fecha_dt.replace(hour=11, minute=0)
    else:
        fecha_inicio = fecha_dt.replace(hour=9, minute=0)
        fecha_fin = fecha_dt.replace(hour=11, minute=0)
    
    # Formato para Google Calendar: YYYYMMDDTHHmmSS
    fecha_inicio_str = fecha_inicio.strftime("%Y%m%dT%H%M%S")
    fecha_fin_str = fecha_fin.strftime("%Y%m%dT%H%M%S")
    
    # Construir URL
    base_url = "https://calendar.google.com/calendar/render"
    params = {
        "action": "TEMPLATE",
        "text": titulo,
        "dates": f"{fecha_inicio_str}/{fecha_fin_str}",
        "details": descripcion,
        "location": ubicacion
    }
    
    query_string = "&".join([f"{k}={quote(str(v))}" for k, v in params.items()])
    return f"{base_url}?{query_string}"


async def obtener_metricas_proyecto(proyecto_id: str) -> dict:
    """
    Obtiene todas las métricas acumuladas de un proyecto.
    """
    db = get_db()
    
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        return {}
    
    avances = await db.avances_semanales.find(
        {"proyecto_id": proyecto_id}, {"_id": 0}
    ).to_list(100)
    
    volumen_excavado = sum((a.get('volumen_excavacion', 0) or 0) for a in avances)
    pilas_completadas = sum((a.get('pilas_completadas', 0) or 0) for a in avances)
    anclas_instaladas = sum((a.get('anclas_instaladas', 0) or 0) for a in avances)
    muros_completados = sum((a.get('muros_completados', 0) or 0) for a in avances)
    
    # Obtener metas del proyecto
    volumen_total_planeado = proyecto.get('volumen_total_planeado', 0) or 0
    pilas_planeadas = proyecto.get('pilas_planeadas', 0) or 0
    anclas_planeadas = proyecto.get('anclas_planeadas', 0) or 0
    muros_planeados = proyecto.get('muros_planeados', 0) or 0
    
    # Calcular porcentajes
    avance_excavacion = (volumen_excavado / volumen_total_planeado * 100) if volumen_total_planeado > 0 else 0
    avance_pilas = (pilas_completadas / pilas_planeadas * 100) if pilas_planeadas > 0 else 0
    avance_anclas = (anclas_instaladas / anclas_planeadas * 100) if anclas_planeadas > 0 else 0
    avance_muros = (muros_completados / muros_planeados * 100) if muros_planeados > 0 else 0
    
    return {
        "volumen_excavado": volumen_excavado,
        "volumen_planeado": volumen_total_planeado,
        "avance_excavacion_pct": round(avance_excavacion, 2),
        "pilas_completadas": pilas_completadas,
        "pilas_planeadas": pilas_planeadas,
        "avance_pilas_pct": round(avance_pilas, 2),
        "anclas_instaladas": anclas_instaladas,
        "anclas_planeadas": anclas_planeadas,
        "avance_anclas_pct": round(avance_anclas, 2),
        "muros_completados": muros_completados,
        "muros_planeados": muros_planeados,
        "avance_muros_pct": round(avance_muros, 2),
        "semanas_registradas": len(avances)
    }
