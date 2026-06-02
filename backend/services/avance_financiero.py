"""
Avance Financiero Service — calcula comparativa Presupuestado vs Ejecutado
cruzando el presupuesto del proyecto contra los avances reales medidos con dron.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Mapeo categoría del presupuesto → fuente de datos reales
CATEGORIA_FUENTE = {
    "Excavación": ("volumen_excavacion", "volumen_total_planeado", "m³"),
    "Cimentación": ("pilas_completadas", "pilas_planeadas", "pilas"),
    "Anclas": ("anclas_instaladas", "anclas_planeadas", "anclas"),
    "Muros": ("muros_completados", "muros_planeados", "m²"),
}


def calcular_avance_financiero(proyecto: dict, avances: list) -> Dict[str, Any]:
    """
    Devuelve la comparativa por categoría:
    {
        "categorias": [
            {"nombre": "Excavación", "presupuestado": 2060000, "ejecutado": 250000,
             "pct_avance": 12.5, "unidad": "m³",
             "real": 1624.7, "planeado": 13000.0, "color": "#F59E0B"},
            ...
        ],
        "totales": {"presupuestado": X, "ejecutado": Y, "pct": Z},
        "tiene_presupuesto": bool,
    }
    """
    presupuesto = proyecto.get("presupuesto")
    if not presupuesto or not presupuesto.get("categorias"):
        return {
            "tiene_presupuesto": False,
            "categorias": [],
            "totales": {"presupuestado": 0, "ejecutado": 0, "pct": 0},
        }

    # Sumar reales desde avances semanales
    reales = {
        "volumen_excavacion": sum((a.get("volumen_excavacion") or 0) for a in avances),
        "pilas_completadas": sum((a.get("pilas_completadas") or 0) for a in avances),
        "anclas_instaladas": sum((a.get("anclas_instaladas") or 0) for a in avances),
        "muros_completados": sum((a.get("muros_completados") or 0) for a in avances),
    }

    # Planeados desde proyecto
    planeados = {
        "volumen_excavacion": proyecto.get("volumen_total_planeado") or 0,
        "pilas_completadas": proyecto.get("pilas_planeadas") or 0,
        "anclas_instaladas": proyecto.get("anclas_planeadas") or 0,
        "muros_completados": proyecto.get("muros_planeados") or 0,
    }

    # Si hay matriz de caras, sobrescribir pilas/anclas con celdas marcadas
    caras = proyecto.get("caras_excavacion") or []
    if len(caras) == 4 and any((c.get("pilas") or c.get("anclas")) for c in caras):
        reales["pilas_completadas"] = sum(
            sum(1 for s in (c.get("pilas_estados") or []) if s) for c in caras
        )
        reales["anclas_instaladas"] = sum(
            sum(1 for s in (c.get("anclas_estados") or []) if s) for c in caras
        )
        planeados["pilas_completadas"] = sum(int(c.get("pilas") or 0) for c in caras)
        planeados["anclas_instaladas"] = sum(int(c.get("anclas") or 0) for c in caras)

    color_map = {
        "Generales": "#94A3B8",
        "Excavación": "#F59E0B",
        "Cimentación": "#3B82F6",
        "Anclas": "#14B8A6",
        "Muros": "#A855F7",
        "Edificación": "#EC4899",
        "Otros": "#71717A",
    }

    categorias_out = []
    total_presupuestado = 0.0
    total_ejecutado = 0.0

    for cat_nombre, info in presupuesto["categorias"].items():
        presup_cat = float(info.get("total") or 0)
        total_presupuestado += presup_cat

        if cat_nombre in CATEGORIA_FUENTE:
            campo_real, campo_planeado, unidad = CATEGORIA_FUENTE[cat_nombre]
            real_val = float(reales.get(campo_real) or 0)
            plan_val = float(planeados.get(campo_real) or 0)
            if plan_val > 0:
                pct = min(real_val / plan_val * 100, 100.0)
            elif real_val > 0:
                # Hay datos reales pero falta meta planeada: usar avance ponderado
                pct = float(proyecto.get("avance_total") or 0)
            else:
                pct = 0.0
            ejecutado = presup_cat * (pct / 100.0)
        else:
            # Categorías sin fuente directa (Generales, Edificación, Otros)
            # se asumen prorrateadas con el avance ponderado del proyecto
            real_val = None
            plan_val = None
            unidad = ""
            pct = float(proyecto.get("avance_total") or 0)
            ejecutado = presup_cat * (pct / 100.0)

        total_ejecutado += ejecutado

        categorias_out.append({
            "nombre": cat_nombre,
            "presupuestado": round(presup_cat, 2),
            "ejecutado": round(ejecutado, 2),
            "pendiente": round(presup_cat - ejecutado, 2),
            "pct_avance": round(pct, 2),
            "real": round(real_val, 2) if real_val is not None else None,
            "planeado": round(plan_val, 2) if plan_val is not None else None,
            "unidad": unidad,
            "color": color_map.get(cat_nombre, "#94A3B8"),
            "fuente_real": cat_nombre in CATEGORIA_FUENTE,
        })

    # Ordenar por mayor presupuesto
    categorias_out.sort(key=lambda x: x["presupuestado"], reverse=True)

    pct_total = (total_ejecutado / total_presupuestado * 100) if total_presupuestado > 0 else 0

    return {
        "tiene_presupuesto": True,
        "categorias": categorias_out,
        "totales": {
            "presupuestado": round(total_presupuestado, 2),
            "ejecutado": round(total_ejecutado, 2),
            "pendiente": round(total_presupuestado - total_ejecutado, 2),
            "pct": round(pct_total, 2),
        },
        "version": presupuesto.get("version"),
        "filename": presupuesto.get("filename"),
    }
