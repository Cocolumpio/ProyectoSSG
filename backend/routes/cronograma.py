"""Rutas de Cronograma y Frentes - DrON Topografía"""
import os
import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse

from core.config import get_db, UPLOAD_DIR
from services import cronograma_ai
from services.notifications import crear_notificacion_sistema

db = get_db()
router = APIRouter(prefix="/api")

# --- Cronograma y Frentes ---
@router.post("/proyectos/importar-cronograma")
async def importar_cronograma(file: UploadFile = File(...)):
    """
    Importa un archivo Excel con el cronograma del proyecto.
    Parsea automáticamente los frentes y actividades.
    """
    from services.cronograma_ai import parse_excel_cronograma
    
    # Verificar extensión
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="El archivo debe ser Excel (.xlsx o .xls)")
    
    # Leer contenido
    content = await file.read()
    
    # Parsear cronograma
    resultado = parse_excel_cronograma(content)
    
    if not resultado.get("success"):
        raise HTTPException(status_code=400, detail=resultado.get("error", "Error parseando archivo"))
    
    return resultado


@router.get("/plantilla-cronograma")
async def descargar_plantilla_cronograma():
    """Descarga la plantilla de Excel para cronogramas"""
    plantilla_path = UPLOAD_DIR / "plantilla_cronograma.xlsx"
    if not plantilla_path.exists():
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    
    return FileResponse(
        plantilla_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="plantilla_cronograma_dron.xlsx"
    )


@router.post("/proyectos/crear-desde-cronograma")
async def crear_proyecto_desde_cronograma(data: dict):
    """
    Crea un proyecto completo a partir de datos de cronograma parseados.
    """
    try:
        # Crear proyecto
        proyecto_id = str(uuid.uuid4())
        resumen = data.get("resumen", {})
        
        proyecto = {
            "id": proyecto_id,
            "nombre": data.get("nombre", resumen.get("nombre_proyecto") or "Nuevo Proyecto"),
            "ubicacion": data.get("ubicacion", ""),
            "direccion": data.get("direccion", ""),
            "coordenadas": data.get("coordenadas", {"lat": 0, "lng": 0}),
            "fecha_inicio": resumen.get("fecha_inicio", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
            "fecha_fin_planeada": resumen.get("fecha_fin", ""),
            "avance_actual": 0.0,
            # Tipos de actividades detectadas
            "actividades_tipo": resumen.get("tipos_actividades", ["pilas"]),
            # Métricas planeadas
            "volumen_total_planeado": resumen.get("total_excavacion", 0),
            "pilas_planeadas": resumen.get("total_pilas", 0),
            "muros_planeados": resumen.get("total_muros", 0),
            "anclas_planeadas": resumen.get("total_anclas", 0),
            # Métricas ejecutadas (inician en 0)
            "volumen_ejecutado": 0,
            "pilas_ejecutadas": 0,
            "muros_ejecutados": 0,
            "anclas_ejecutadas": 0,
            # Cronograma
            "semanas_planeadas": resumen.get("semanas_estimadas", 0),
            "semanas_excavacion": resumen.get("semanas_excavacion", 0),
            "semanas_pilas": resumen.get("semanas_pilas", 0),
            "semanas_muros": resumen.get("semanas_muros", 0),
            "descripcion": data.get("descripcion", ""),
            "capacidad_camion": 25.0,
            "costo_m3": 150.0,
            "clientes_asignados": [],
            "created_at": datetime.now(timezone.utc)
        }

        # Si el parser V2 incluyó presupuesto, persistirlo en el proyecto
        presupuesto_data = data.get("presupuesto")
        if presupuesto_data and isinstance(presupuesto_data, dict) and presupuesto_data.get("total"):
            proyecto["presupuesto"] = {
                **presupuesto_data,
                "version": presupuesto_data.get("version") or datetime.now(timezone.utc).strftime("v%Y%m%d-%H%M"),
                "fecha_carga": datetime.now(timezone.utc).isoformat(),
            }

        # Persistir el programa semanal (cards de comparativa por semana)
        programa_semanal = data.get("programa_semanal")
        if isinstance(programa_semanal, list) and programa_semanal:
            proyecto["programa_semanal"] = programa_semanal
        
        await db.proyectos.insert_one(proyecto)
        
        # Crear frentes
        frentes_data = data.get("frentes", [])
        for idx, frente_data in enumerate(frentes_data):
            frente = {
                "id": str(uuid.uuid4()),
                "proyecto_id": proyecto_id,
                "nombre": frente_data.get("nombre", f"Frente {idx + 1}"),
                "descripcion": frente_data.get("descripcion", ""),
                "actividades": frente_data.get("actividades", []),
                "orden": idx + 1,
                "created_at": datetime.now(timezone.utc)
            }
            await db.frentes.insert_one(frente)
        
        # Crear avances semanales vacíos para cada semana planeada
        semanas = resumen.get("semanas_estimadas", 12)
        fecha_inicio = datetime.strptime(resumen.get("fecha_inicio", datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d")
        
        for semana in range(1, semanas + 1):
            fecha_semana = fecha_inicio + timedelta(weeks=semana - 1)
            avance = {
                "id": str(uuid.uuid4()),
                "proyecto_id": proyecto_id,
                "semana": semana,
                "fecha": fecha_semana.strftime("%Y-%m-%d"),
                "descripcion": f"Semana {semana}",
                "volumen_excavacion": 0,
                "pilas_planeadas": 0,
                "pilas_completadas": 0,
                "anclas_planeadas": 0,
                "anclas_instaladas": 0,
                "imagenes": [],
                "created_at": datetime.now(timezone.utc)
            }
            await db.avances_semanales.insert_one(avance)
        
        return {
            "success": True,
            "proyecto_id": proyecto_id,
            "mensaje": f"Proyecto creado con {len(frentes_data)} frentes y {semanas} semanas de avance"
        }
        
    except Exception as e:
        logging.error(f"Error creando proyecto desde cronograma: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/proyectos/{proyecto_id}/actualizar-cronograma")
async def actualizar_cronograma_proyecto(proyecto_id: str, file: UploadFile = File(...)):
    """
    Actualiza el cronograma de un proyecto existente desde un archivo Excel.
    Permite subir o actualizar el programa de obra.
    """
    from services.cronograma_ai import parse_excel_cronograma
    
    # Verificar que el proyecto existe
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Validar tipo de archivo
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos Excel (.xlsx, .xls)")
    
    try:
        content = await file.read()
        
        # Parsear cronograma
        resultado = parse_excel_cronograma(content)
        
        if resultado.get("error"):
            raise HTTPException(status_code=400, detail=resultado["error"])
        
        resumen = resultado.get("resumen", {})
        frentes_data = resultado.get("frentes", [])
        
        # Actualizar datos del proyecto con el nuevo cronograma
        update_data = {
            "cronograma_archivo": file.filename,
            "cronograma_fecha_carga": datetime.now(timezone.utc).isoformat(),
            "actividades_tipo": resumen.get("tipos_actividades", proyecto.get("actividades_tipo", [])),
            "semanas_planeadas": resumen.get("semanas_estimadas", proyecto.get("semanas_planeadas", 0)),
            "semanas_excavacion": resumen.get("semanas_excavacion", 0),
            "semanas_pilas": resumen.get("semanas_pilas", 0),
            "semanas_muros": resumen.get("semanas_muros", 0),
            "cronograma_resumen": resumen,
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Actualizar métricas planeadas si vienen en el cronograma
        if resumen.get("total_pilas", 0) > 0:
            update_data["pilas_planeadas"] = resumen["total_pilas"]
        if resumen.get("total_anclas", 0) > 0:
            update_data["anclas_planeadas"] = resumen["total_anclas"]
        if resumen.get("total_muros", 0) > 0:
            update_data["muros_planeados"] = resumen["total_muros"]
        if resumen.get("total_excavacion", 0) > 0:
            update_data["volumen_total_planeado"] = resumen["total_excavacion"]
        
        # Actualizar fechas si vienen en el cronograma y tienen sentido
        if resumen.get("fecha_inicio"):
            update_data["fecha_inicio"] = resumen["fecha_inicio"]
        if resumen.get("fecha_fin"):
            update_data["fecha_fin_planeada"] = resumen["fecha_fin"]

        # Si el parser V2 incluyó presupuesto, persistirlo en el proyecto
        presupuesto_data = resultado.get("presupuesto")
        if presupuesto_data and isinstance(presupuesto_data, dict) and presupuesto_data.get("total"):
            update_data["presupuesto"] = {
                **presupuesto_data,
                "version": presupuesto_data.get("version") or datetime.now(timezone.utc).strftime("v%Y%m%d-%H%M"),
                "fecha_carga": datetime.now(timezone.utc).isoformat(),
            }

        # Persistir el programa semanal
        programa_semanal = resultado.get("programa_semanal")
        if isinstance(programa_semanal, list) and programa_semanal:
            update_data["programa_semanal"] = programa_semanal
        
        await db.proyectos.update_one({"id": proyecto_id}, {"$set": update_data})
        
        # Eliminar frentes anteriores y crear nuevos
        await db.frentes.delete_many({"proyecto_id": proyecto_id})
        
        for idx, frente_data in enumerate(frentes_data):
            frente = {
                "id": str(uuid.uuid4()),
                "proyecto_id": proyecto_id,
                "nombre": frente_data.get("nombre", f"Frente {idx + 1}"),
                "descripcion": frente_data.get("descripcion", ""),
                "actividades": frente_data.get("actividades", []),
                "orden": idx + 1,
                "created_at": datetime.now(timezone.utc)
            }
            await db.frentes.insert_one(frente)
        
        return {
            "success": True,
            "mensaje": f"Cronograma actualizado: {len(frentes_data)} frentes, {resumen.get('semanas_estimadas', 0)} semanas",
            "resumen": resumen,
            "frentes_creados": len(frentes_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error actualizando cronograma: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error procesando archivo: {str(e)}")


@router.get("/proyectos/{proyecto_id}/cronograma")
async def obtener_cronograma_proyecto(proyecto_id: str):
    """Obtiene información del cronograma cargado para un proyecto"""
    proyecto = await db.proyectos.find_one(
        {"id": proyecto_id}, 
        {"_id": 0, "cronograma_archivo": 1, "cronograma_fecha_carga": 1, "cronograma_resumen": 1, 
         "semanas_planeadas": 1, "fecha_inicio": 1, "fecha_fin_planeada": 1, "nombre": 1}
    )
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Obtener frentes del proyecto
    frentes = await db.frentes.find({"proyecto_id": proyecto_id}, {"_id": 0}).to_list(100)
    frentes = sorted(frentes, key=lambda x: x.get("orden", 0))
    
    return {
        "proyecto_nombre": proyecto.get("nombre", ""),
        "tiene_cronograma": bool(proyecto.get("cronograma_archivo")),
        "cronograma_archivo": proyecto.get("cronograma_archivo"),
        "cronograma_fecha_carga": proyecto.get("cronograma_fecha_carga"),
        "cronograma_resumen": proyecto.get("cronograma_resumen"),
        "semanas_planeadas": proyecto.get("semanas_planeadas", 0),
        "fecha_inicio": proyecto.get("fecha_inicio"),
        "fecha_fin_planeada": proyecto.get("fecha_fin_planeada"),
        "frentes": frentes
    }


@router.post("/proyectos/{proyecto_id}/analizar-desviacion")
async def analizar_desviacion_cronograma(proyecto_id: str):
    """
    Analiza la desviación entre el progreso real y el cronograma planificado.
    Envía alerta por email si la desviación es significativa (>20%).
    """
    from services.email import enviar_alerta_desviacion_cronograma
    
    # Obtener proyecto
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Verificar que tiene cronograma
    if not proyecto.get("cronograma_resumen"):
        raise HTTPException(status_code=400, detail="El proyecto no tiene cronograma cargado")
    
    cronograma = proyecto.get("cronograma_resumen", {})
    fecha_inicio_str = proyecto.get("fecha_inicio")
    
    if not fecha_inicio_str:
        raise HTTPException(status_code=400, detail="El proyecto no tiene fecha de inicio definida")
    
    # Calcular semana actual del proyecto
    try:
        fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d")
        dias_transcurridos = (datetime.now() - fecha_inicio).days
        semana_actual = max(1, dias_transcurridos // 7 + 1)
    except:
        semana_actual = 1
    
    semanas_planeadas = proyecto.get("semanas_planeadas", 12)
    progreso_esperado = min(100, (semana_actual / semanas_planeadas) * 100) if semanas_planeadas > 0 else 0
    
    # Obtener progreso real por tipo de actividad
    desviaciones = []
    
    # Excavación
    vol_planeado = proyecto.get("volumen_total_planeado", 0)
    vol_real = proyecto.get("volumen_ejecutado", 0)
    if vol_planeado > 0:
        progreso_real_exc = (vol_real / vol_planeado) * 100
        desviacion_exc = progreso_real_exc - progreso_esperado
        desviaciones.append({
            "fase": "Excavación",
            "planeado": progreso_esperado,
            "real": progreso_real_exc,
            "desviacion_porcentaje": desviacion_exc,
            "unidades": f"{vol_real:,.0f} / {vol_planeado:,.0f} m³"
        })
    
    # Pilas
    pilas_planeadas = proyecto.get("pilas_planeadas", 0)
    pilas_real = proyecto.get("pilas_ejecutadas", 0)
    if pilas_planeadas > 0:
        progreso_real_pilas = (pilas_real / pilas_planeadas) * 100
        desviacion_pilas = progreso_real_pilas - progreso_esperado
        desviaciones.append({
            "fase": "Pilas / Cimentación",
            "planeado": progreso_esperado,
            "real": progreso_real_pilas,
            "desviacion_porcentaje": desviacion_pilas,
            "unidades": f"{pilas_real} / {pilas_planeadas} pilas"
        })
    
    # Anclas
    anclas_planeadas = proyecto.get("anclas_planeadas", 0)
    anclas_real = proyecto.get("anclas_ejecutadas", 0)
    if anclas_planeadas > 0:
        progreso_real_anclas = (anclas_real / anclas_planeadas) * 100
        desviacion_anclas = progreso_real_anclas - progreso_esperado
        desviaciones.append({
            "fase": "Anclas",
            "planeado": progreso_esperado,
            "real": progreso_real_anclas,
            "desviacion_porcentaje": desviacion_anclas,
            "unidades": f"{anclas_real} / {anclas_planeadas} anclas"
        })
    
    # Muros
    muros_planeados = proyecto.get("muros_planeados", 0)
    muros_real = proyecto.get("muros_ejecutados", 0)
    if muros_planeados > 0:
        progreso_real_muros = (muros_real / muros_planeados) * 100
        desviacion_muros = progreso_real_muros - progreso_esperado
        desviaciones.append({
            "fase": "Muros / Estructura",
            "planeado": progreso_esperado,
            "real": progreso_real_muros,
            "desviacion_porcentaje": desviacion_muros,
            "unidades": f"{muros_real} / {muros_planeados} muros"
        })
    
    # Determinar si hay desviaciones críticas (>20% de retraso)
    hay_desviacion_critica = any(d["desviacion_porcentaje"] < -20 for d in desviaciones)
    hay_desviacion_moderada = any(d["desviacion_porcentaje"] < -10 for d in desviaciones)
    
    # Generar resumen
    if hay_desviacion_critica:
        resumen = f"""⚠️ ALERTA CRÍTICA: El proyecto muestra retrasos significativos.

Situación actual:
- Semana {semana_actual} de {semanas_planeadas} planeadas
- Progreso esperado según cronograma: {progreso_esperado:.1f}%
- Se detectaron fases con retraso mayor al 20%

Recomendaciones inmediatas:
1. Convocar reunión de emergencia con el equipo de obra
2. Revisar disponibilidad de maquinaria y recursos
3. Evaluar posibles causas del retraso (clima, suministros, etc.)
4. Considerar ajustes al cronograma o recursos adicionales"""
    elif hay_desviacion_moderada:
        resumen = f"""📊 ALERTA MODERADA: Algunas fases muestran desviaciones.

Situación actual:
- Semana {semana_actual} de {semanas_planeadas} planeadas
- Progreso esperado según cronograma: {progreso_esperado:.1f}%
- Se detectaron desviaciones entre 10-20%

Recomendaciones:
1. Monitorear de cerca las actividades con retraso
2. Verificar si hay obstáculos que resolver
3. Mantener comunicación con el equipo de obra"""
    else:
        resumen = f"""✅ El proyecto avanza dentro de los parámetros esperados.

Situación actual:
- Semana {semana_actual} de {semanas_planeadas} planeadas
- Progreso esperado según cronograma: {progreso_esperado:.1f}%
- Las desviaciones están dentro del rango aceptable (±10%)"""
    
    # Enviar alerta por email si hay desviación significativa
    email_enviado = False
    if hay_desviacion_critica or hay_desviacion_moderada:
        email_enviado = await enviar_alerta_desviacion_cronograma(
            proyecto_nombre=proyecto.get("nombre", "Sin nombre"),
            proyecto_id=proyecto_id,
            desviaciones=desviaciones,
            resumen=resumen,
            fecha_analisis=datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
        )
        
        # Crear notificación en el sistema
        tipo_notif = "error" if hay_desviacion_critica else "warning"
        titulo_notif = "Alerta Crítica de Desviación" if hay_desviacion_critica else "Desviación Detectada"
        await crear_notificacion_sistema(
            tipo=tipo_notif,
            titulo=titulo_notif,
            mensaje=f"Semana {semana_actual}/{semanas_planeadas} - Progreso esperado: {progreso_esperado:.1f}%",
            proyecto_id=proyecto_id,
            proyecto_nombre=proyecto.get("nombre"),
            link=f"/proyectos?id={proyecto_id}",
            metadata={
                "semana_actual": semana_actual,
                "progreso_esperado": progreso_esperado,
                "hay_desviacion_critica": hay_desviacion_critica,
                "desviaciones_count": len(desviaciones)
            }
        )
    
    # Guardar el análisis en el proyecto
    await db.proyectos.update_one(
        {"id": proyecto_id},
        {"$set": {
            "ultimo_analisis_desviacion": {
                "fecha": datetime.now(timezone.utc).isoformat(),
                "semana_actual": semana_actual,
                "progreso_esperado": progreso_esperado,
                "desviaciones": desviaciones,
                "hay_desviacion_critica": hay_desviacion_critica,
                "hay_desviacion_moderada": hay_desviacion_moderada,
                "email_enviado": email_enviado
            }
        }}
    )
    
    return {
        "success": True,
        "proyecto": proyecto.get("nombre"),
        "semana_actual": semana_actual,
        "semanas_planeadas": semanas_planeadas,
        "progreso_esperado": round(progreso_esperado, 1),
        "desviaciones": desviaciones,
        "hay_desviacion_critica": hay_desviacion_critica,
        "hay_desviacion_moderada": hay_desviacion_moderada,
        "resumen": resumen,
        "alerta_enviada": email_enviado
    }


@router.get("/proyectos/{proyecto_id}/frentes")
async def obtener_frentes(proyecto_id: str):
    """Obtiene todos los frentes de un proyecto"""
    frentes = await db.frentes.find({"proyecto_id": proyecto_id}, {"_id": 0}).to_list(100)
    return sorted(frentes, key=lambda x: x.get("orden", 0))


@router.post("/proyectos/{proyecto_id}/frentes")
async def crear_frente(proyecto_id: str, frente: dict):
    """Crea un nuevo frente para el proyecto"""
    frente_data = {
        "id": str(uuid.uuid4()),
        "proyecto_id": proyecto_id,
        "nombre": frente.get("nombre", "Nuevo Frente"),
        "descripcion": frente.get("descripcion", ""),
        "actividades": frente.get("actividades", []),
        "orden": frente.get("orden", 1),
        "created_at": datetime.now(timezone.utc)
    }
    await db.frentes.insert_one(frente_data)
    frente_data.pop("_id", None)
    return frente_data

