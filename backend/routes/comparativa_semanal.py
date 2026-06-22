"""Comparativa semanal: planeado (programa de obra) vs real (avances semanales del dron).

Devuelve una lista de tarjetas — una por cada semana del programa — con:
  • Cantidades planeadas por fase (excavación m³, pilas, anclas, muros m²)
  • Cantidades reales acumuladas hasta el final de esa semana (del avance del dron)
  • Presupuesto planeado y presupuesto real ejecutado en esa ventana
  • Porcentaje de cumplimiento global y por fase
"""
import logging
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends

from core.config import get_db, get_current_user

logger = logging.getLogger(__name__)
db = get_db()
router = APIRouter(prefix="/api")


def _calcular_ejecutado(real: float, planeado: float) -> float:
    if planeado <= 0:
        return 0.0
    return round(min(real / planeado * 100, 999.9), 1)


def _calcular_presupuesto_ejecutado(real_acumulado: Dict[str, float], categorias: Dict[str, Any]) -> float:
    """Aplica los porcentajes reales por categoría al presupuesto de la categoría."""
    total = 0.0
    for nombre, cat in (categorias or {}).items():
        nombre_lower = (nombre or "").lower()
        importe_cat = float(cat.get("total", 0) or 0)
        if "excav" in nombre_lower:
            pct = real_acumulado.get("excavacion_pct", 0)
        elif "ancla" in nombre_lower:
            pct = real_acumulado.get("anclas_pct", 0)
        elif "muro" in nombre_lower:
            pct = real_acumulado.get("muros_pct", 0)
        elif ("reforz" in nombre_lower and "colindanc" not in nombre_lower) or ("perfil" in nombre_lower and "cimentaci" not in nombre_lower):
            pct = real_acumulado.get("perfiles_pct", 0)
        elif "cimen" in nombre_lower or "pila" in nombre_lower:
            pct = real_acumulado.get("pilas_pct", 0)
        else:
            pct = real_acumulado.get("general_pct", 0)
        total += importe_cat * (pct / 100)
    return round(total, 2)


@router.get("/proyectos/{proyecto_id}/comparativa-semanal")
async def comparativa_semanal(proyecto_id: str, current_user: dict = Depends(get_current_user)):
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    if current_user.get("rol") == "client":
        if current_user.get("id") not in (proyecto.get("clientes_asignados") or []):
            raise HTTPException(status_code=403, detail="Sin acceso")

    programa = proyecto.get("programa_semanal") or []
    if not programa:
        return {
            "tiene_programa": False,
            "mensaje": "Este proyecto no tiene programa semanal. Reimporta el cronograma para activarlo.",
            "semanas": [],
        }

    # Avances reales (registros del dron) — agrupar por número de semana
    avances = await db.avances_semanales.find(
        {"proyecto_id": proyecto_id}, {"_id": 0}
    ).sort("semana", 1).to_list(500)

    # Construir mapeo semana → avance real
    avances_por_semana = {int(a.get("semana", 0)): a for a in avances}

    # Acumuladores planeados (acumulado hasta semana N)
    plan_acum = {"excavacion": 0.0, "pilas": 0.0, "anclas": 0.0, "muros": 0.0, "perfiles": 0.0, "presupuesto": 0.0}
    # Acumuladores reales
    real_acum = {"excavacion": 0.0, "pilas": 0.0, "anclas": 0.0, "muros": 0.0, "perfiles": 0.0}

    # Totales del proyecto (para pct)
    plan_total = {
        "excavacion": float(proyecto.get("volumen_total_planeado") or 0),
        "pilas": float(proyecto.get("pilas_planeadas") or 0),
        "anclas": float(proyecto.get("anclas_planeadas") or 0),
        "muros": float(proyecto.get("muros_planeados") or 0),
        "perfiles": float(proyecto.get("perfiles_planeados") or 0),
    }
    presupuesto_total = float((proyecto.get("presupuesto") or {}).get("total") or 0)
    if not presupuesto_total:
        presupuesto_total = float((proyecto.get("presupuesto") or {}).get("total_general") or 0)
    presupuesto_cats = (proyecto.get("presupuesto") or {}).get("categorias") or {}

    # Mapeo nombre categoría → fase del proyecto
    def _cat_a_fase(nombre_cat: str) -> str:
        n = (nombre_cat or "").lower()
        if "excav" in n:
            return "excavacion"
        if "ancla" in n:
            return "anclas"
        if "muro" in n:
            return "muros"
        # "reforzamiento" alone (sin "colindancia") = perfiles
        if "reforz" in n and "colindanc" not in n:
            return "perfiles"
        if "perfil" in n and "cimentaci" not in n:
            return "perfiles"
        if "cimen" in n or "pila" in n:
            return "pilas"
        return "otros"

    # Calcular importe TOTAL por fase a partir del presupuesto del proyecto (APU u otro)
    importe_total_fase = {"excavacion": 0.0, "pilas": 0.0, "anclas": 0.0, "muros": 0.0, "perfiles": 0.0, "otros": 0.0}
    for nombre_cat, info in presupuesto_cats.items():
        fase = _cat_a_fase(nombre_cat)
        importe_total_fase[fase] = importe_total_fase.get(fase, 0.0) + float(info.get("total") or 0)

    # Contar cuántas semanas tienen actividad planeada por fase
    sem_activas_fase = {"excavacion": 0, "pilas": 0, "anclas": 0, "muros": 0, "perfiles": 0}
    for sem in programa:
        if float(sem.get("excavacion_m3") or 0) > 0:
            sem_activas_fase["excavacion"] += 1
        if float(sem.get("pilas") or 0) > 0:
            sem_activas_fase["pilas"] += 1
        if float(sem.get("anclas") or 0) > 0:
            sem_activas_fase["anclas"] += 1
        if float(sem.get("muros_m2") or 0) > 0:
            sem_activas_fase["muros"] += 1
        if float(sem.get("perfiles") or 0) > 0:
            sem_activas_fase["perfiles"] += 1

    # Importe promedio por semana de cada fase activa
    importe_promedio_semana = {
        f: (importe_total_fase[f] / sem_activas_fase[f]) if sem_activas_fase[f] > 0 else 0.0
        for f in ("excavacion", "pilas", "anclas", "muros", "perfiles")
    }
    # Generales/Otros se prorratea linealmente por todas las semanas
    total_semanas_programa = max(len(programa), 1)
    importe_generales_por_semana = importe_total_fase["otros"] / total_semanas_programa

    semanas_out = []
    for sem in programa:
        n = int(sem.get("semana") or 0)
        plan_exc = float(sem.get("excavacion_m3") or 0)
        plan_pil = float(sem.get("pilas") or 0)
        plan_anc = float(sem.get("anclas") or 0)
        plan_mur = float(sem.get("muros_m2") or 0)
        plan_perf = float(sem.get("perfiles") or 0)
        plan_pres_excel = float(sem.get("presupuesto") or 0)

        # Presupuesto de la semana: si el archivo de programa de obra ya traía
        # importes, los usamos; si no, distribuimos el presupuesto promedio por
        # semana de cada fase activa en esa semana.
        if plan_pres_excel > 0:
            plan_pres = plan_pres_excel
        else:
            plan_pres = importe_generales_por_semana
            if plan_exc > 0:
                plan_pres += importe_promedio_semana["excavacion"]
            if plan_pil > 0:
                plan_pres += importe_promedio_semana["pilas"]
            if plan_anc > 0:
                plan_pres += importe_promedio_semana["anclas"]
            if plan_mur > 0:
                plan_pres += importe_promedio_semana["muros"]
            if plan_perf > 0:
                plan_pres += importe_promedio_semana["perfiles"]

        # Acumular planeado
        plan_acum["excavacion"] += plan_exc
        plan_acum["pilas"] += plan_pil
        plan_acum["anclas"] += plan_anc
        plan_acum["muros"] += plan_mur
        plan_acum["perfiles"] += plan_perf
        plan_acum["presupuesto"] += plan_pres

        # Avance real de esta semana (los modelos del dron son acumulativos por evento)
        avance = avances_por_semana.get(n) or {}
        # Las cantidades en cada avance representan lo nuevo de la semana
        real_exc_sem = float(avance.get("volumen_excavacion") or 0)
        real_pil_sem = float(avance.get("pilas_completadas") or 0)
        real_anc_sem = float(avance.get("anclas_instaladas") or 0)
        real_mur_sem = float(avance.get("muros_completados") or 0)
        real_perf_sem = float(avance.get("perfiles_completados") or 0)

        real_acum["excavacion"] += real_exc_sem
        real_acum["pilas"] += real_pil_sem
        real_acum["anclas"] += real_anc_sem
        real_acum["muros"] += real_mur_sem
        real_acum["perfiles"] += real_perf_sem

        # Porcentajes (real vs planeado de la semana)
        pct_sem = {
            "excavacion": _calcular_ejecutado(real_exc_sem, plan_exc),
            "pilas": _calcular_ejecutado(real_pil_sem, plan_pil),
            "anclas": _calcular_ejecutado(real_anc_sem, plan_anc),
            "muros": _calcular_ejecutado(real_mur_sem, plan_mur),
            "perfiles": _calcular_ejecutado(real_perf_sem, plan_perf),
        }

        # Porcentaje global de la semana (promedio ponderado de las fases activas)
        fases_activas = []
        if plan_exc > 0:
            fases_activas.append(pct_sem["excavacion"])
        if plan_pil > 0:
            fases_activas.append(pct_sem["pilas"])
        if plan_anc > 0:
            fases_activas.append(pct_sem["anclas"])
        if plan_mur > 0:
            fases_activas.append(pct_sem["muros"])
        if plan_perf > 0:
            fases_activas.append(pct_sem["perfiles"])
        pct_global_sem = round(sum(fases_activas) / len(fases_activas), 1) if fases_activas else 0.0

        # Presupuesto real acumulado a esta semana (% de cada categoría aplicado a su importe)
        real_acumulado_pct = {
            "excavacion_pct": (real_acum["excavacion"] / plan_total["excavacion"] * 100) if plan_total["excavacion"] else 0,
            "pilas_pct": (real_acum["pilas"] / plan_total["pilas"] * 100) if plan_total["pilas"] else 0,
            "anclas_pct": (real_acum["anclas"] / plan_total["anclas"] * 100) if plan_total["anclas"] else 0,
            "muros_pct": (real_acum["muros"] / plan_total["muros"] * 100) if plan_total["muros"] else 0,
            "perfiles_pct": (real_acum["perfiles"] / plan_total["perfiles"] * 100) if plan_total["perfiles"] else 0,
            "general_pct": 0,
        }
        ejecutado_acum = _calcular_presupuesto_ejecutado(real_acumulado_pct, presupuesto_cats)
        pct_presupuesto = (ejecutado_acum / plan_acum["presupuesto"] * 100) if plan_acum["presupuesto"] > 0 else 0

        # Determinar estado (verde/ámbar/rojo) por umbral.
        # Consideramos que hay avance real solo si alguna métrica > 0
        tiene_avance = any([
            float(avance.get("volumen_excavacion") or 0) > 0,
            float(avance.get("pilas_completadas") or 0) > 0,
            float(avance.get("anclas_instaladas") or 0) > 0,
            float(avance.get("muros_completados") or 0) > 0,
            float(avance.get("perfiles_completados") or 0) > 0,
        ])
        if not tiene_avance:
            estado = "pendiente"  # aún no hay avance registrado
        elif pct_global_sem >= 90:
            estado = "ok"
        elif pct_global_sem >= 70:
            estado = "atraso"
        else:
            estado = "critico"

        semanas_out.append({
            "semana": n,
            "fecha_inicio": sem.get("fecha_inicio"),
            "fecha_fin": sem.get("fecha_fin"),
            "estado": estado,
            "tiene_avance": tiene_avance,
            "avance_id": avance.get("id") if avance else None,
            "actividades_planeadas": sem.get("actividades") or [],
            "planeado": {
                "excavacion_m3": round(plan_exc, 2),
                "pilas": round(plan_pil, 2),
                "anclas": round(plan_anc, 2),
                "muros_m2": round(plan_mur, 2),
                "perfiles": round(plan_perf, 2),
                "presupuesto": round(plan_pres, 2),
            },
            "real": {
                "excavacion_m3": round(real_exc_sem, 2),
                "pilas": round(real_pil_sem, 2),
                "anclas": round(real_anc_sem, 2),
                "muros_m2": round(real_mur_sem, 2),
                "perfiles": round(real_perf_sem, 2),
            },
            "pct": {
                **pct_sem,
                "global": pct_global_sem,
            },
            "acumulado": {
                "planeado": {
                    "excavacion_m3": round(plan_acum["excavacion"], 2),
                    "pilas": round(plan_acum["pilas"], 2),
                    "anclas": round(plan_acum["anclas"], 2),
                    "muros_m2": round(plan_acum["muros"], 2),
                    "perfiles": round(plan_acum["perfiles"], 2),
                    "presupuesto": round(plan_acum["presupuesto"], 2),
                },
                "real": {
                    "excavacion_m3": round(real_acum["excavacion"], 2),
                    "pilas": round(real_acum["pilas"], 2),
                    "anclas": round(real_acum["anclas"], 2),
                    "muros_m2": round(real_acum["muros"], 2),
                    "perfiles": round(real_acum["perfiles"], 2),
                    "presupuesto": ejecutado_acum,
                },
                "pct_presupuesto": round(min(pct_presupuesto, 999.9), 1),
            },
        })

    return {
        "tiene_programa": True,
        "total_semanas": len(programa),
        "presupuesto_total_contrato": presupuesto_total,
        "semanas": semanas_out,
    }
