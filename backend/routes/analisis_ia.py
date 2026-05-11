"""Rutas de Análisis IA de Fotos y Reportes - DrON Topografía"""
import os
import io
import json
import uuid
import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from core.config import get_db, EMERGENT_LLM_KEY
from services import cronograma_ai

db = get_db()
router = APIRouter(prefix="/api")

@router.post("/analisis/foto-avance")
async def analizar_foto_para_avance(imagen: UploadFile = File(...), proyecto_info: str = Form("{}")):
    """
    Analiza una foto de obra para detectar avances antes de crear el registro.
    Retorna las cantidades detectadas para pre-rellenar el formulario.
    """
    from emergentintegrations.llm.gemini import GeminiChat
    
    try:
        # Parsear info del proyecto
        info = json.loads(proyecto_info)
        tiene_excavacion = info.get("tiene_excavacion", True)
        tiene_cimentacion = info.get("tiene_cimentacion", False)
        tiene_edificacion = info.get("tiene_edificacion", False)
        pilas_planeadas = info.get("pilas_planeadas", 0)
        anclas_planeadas = info.get("anclas_planeadas", 0)
        muros_planeados = info.get("muros_planeados", 0)
        
        # Leer y convertir imagen a base64
        content = await imagen.read()
        import base64
        imagen_base64 = base64.b64encode(content).decode('utf-8')
        
        # Crear prompt para análisis
        prompt = f"""Analiza esta foto de una obra de construcción y detecta los elementos visibles.

El proyecto tiene las siguientes fases activas:
{"- EXCAVACIÓN: Detecta si hay trabajo de excavación visible y estima el volumen" if tiene_excavacion else ""}
{f"- CIMENTACIÓN: Detecta pilas (meta: {pilas_planeadas}) y anclas (meta: {anclas_planeadas})" if tiene_cimentacion else ""}
{f"- EDIFICACIÓN: Detecta muros completados (meta: {muros_planeados})" if tiene_edificacion else ""}

Responde SOLO en formato JSON con esta estructura exacta:
{{
    "volumen_excavacion": <número estimado de m³ excavados, 0 si no aplica o no visible>,
    "pilas_detectadas": <número de pilas completadas visibles, 0 si no aplica>,
    "anclas_detectadas": <número de anclas instaladas visibles, 0 si no aplica>,
    "muros_detectados": <número de muros completados visibles, 0 si no aplica>,
    "descripcion_ia": "<descripción breve del estado de la obra en 1-2 oraciones>",
    "confianza": "<ALTA|MEDIA|BAJA - qué tan seguro estás de los números>"
}}

IMPORTANTE:
- Si no puedes ver claramente algo, pon 0
- Sé conservador en las estimaciones
- La descripción debe ser concisa y profesional
"""

        chat = GeminiChat(gemini_key=EMERGENT_LLM_KEY)
        
        response = await asyncio.to_thread(
            chat.send_message_with_image,
            prompt,
            imagen_base64,
            image_type="image/jpeg"
        )
        
        # Parsear respuesta JSON
        response_text = response.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        
        resultado = json.loads(response_text)
        
        return {
            "success": True,
            "resultado": {
                "volumen_excavacion": resultado.get("volumen_excavacion", 0),
                "pilas_detectadas": resultado.get("pilas_detectadas", 0),
                "anclas_detectadas": resultado.get("anclas_detectadas", 0),
                "muros_detectados": resultado.get("muros_detectados", 0),
                "descripcion_ia": resultado.get("descripcion_ia", ""),
                "confianza": resultado.get("confianza", "MEDIA")
            }
        }
        
    except json.JSONDecodeError as e:
        logging.error(f"Error parseando respuesta IA: {e}")
        return {
            "success": False,
            "error": "La IA no pudo analizar correctamente la imagen",
            "resultado": {
                "volumen_excavacion": 0,
                "pilas_detectadas": 0,
                "anclas_detectadas": 0,
                "muros_detectados": 0,
                "descripcion_ia": "",
                "confianza": "BAJA"
            }
        }
    except Exception as e:
        logging.error(f"Error analizando foto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/avances/{avance_id}/analizar-foto")
async def analizar_foto_avance(avance_id: str, data: dict):
    """
    Analiza una foto de avance usando IA para detectar pilas y anclas.
    """
    from services.cronograma_ai import analizar_foto_avance as analizar_ia
    
    avance = await db.avances_semanales.find_one({"id": avance_id})
    if not avance:
        raise HTTPException(status_code=404, detail="Avance no encontrado")
    
    imagen_base64 = data.get("imagen_base64")
    if not imagen_base64:
        raise HTTPException(status_code=400, detail="Se requiere imagen en base64")
    
    # Obtener imagen de semana anterior para comparación
    imagen_anterior = None
    if avance.get("semana", 1) > 1:
        avance_anterior = await db.avances_semanales.find_one({
            "proyecto_id": avance["proyecto_id"],
            "semana": avance["semana"] - 1
        })
        if avance_anterior and avance_anterior.get("imagenes"):
            # Podríamos cargar la imagen anterior aquí
            pass
    
    # Obtener proyecto para pilas planeadas
    proyecto = await db.proyectos.find_one({"id": avance["proyecto_id"]})
    pilas_planeadas = proyecto.get("total_pilas_planeadas", 0) if proyecto else 0
    
    # Analizar con IA
    resultado = await analizar_ia(
        imagen_base64=imagen_base64,
        imagen_anterior_base64=imagen_anterior,
        pilas_planeadas=pilas_planeadas,
        semana_actual=avance.get("semana", 1)
    )
    
    if resultado.get("success"):
        # Guardar análisis
        analisis = {
            "id": str(uuid.uuid4()),
            "proyecto_id": avance["proyecto_id"],
            "avance_id": avance_id,
            "semana": avance.get("semana", 1),
            "fecha_analisis": datetime.now(timezone.utc),
            "pilas_detectadas": resultado.get("pilas_detectadas", 0),
            "anclas_detectadas": resultado.get("anclas_detectadas", 0),
            "pilas_en_proceso": resultado.get("pilas_en_proceso", 0),
            "porcentaje_avance_estimado": resultado.get("porcentaje_avance_estimado", 0),
            "estado_proyecto": resultado.get("estado_proyecto", "EN_TIEMPO"),
            "confianza_deteccion": resultado.get("confianza_deteccion", "MEDIA"),
            "observaciones": resultado.get("observaciones", ""),
            "recomendaciones": resultado.get("recomendaciones", "")
        }
        await db.analisis_fotos.insert_one(analisis)
        
        # Actualizar avance con datos detectados
        await db.avances_semanales.update_one(
            {"id": avance_id},
            {"$set": {
                "pilas_detectadas_ia": resultado.get("pilas_detectadas", 0),
                "anclas_detectadas_ia": resultado.get("anclas_detectadas", 0),
                "estado_ia": resultado.get("estado_proyecto", "EN_TIEMPO")
            }}
        )
    
    return resultado


@router.get("/proyectos/{proyecto_id}/analisis-ia")
async def obtener_analisis_ia(proyecto_id: str):
    """Obtiene todos los análisis de IA de un proyecto"""
    analisis = await db.analisis_fotos.find(
        {"proyecto_id": proyecto_id}, 
        {"_id": 0}
    ).sort("semana", 1).to_list(100)
    return analisis


@router.post("/proyectos/{proyecto_id}/generar-reporte-ia")
async def generar_reporte_ia(proyecto_id: str):
    """Genera un reporte de progreso usando IA"""
    from services.cronograma_ai import generar_reporte_progreso
    
    proyecto = await db.proyectos.find_one({"id": proyecto_id})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Obtener último análisis
    ultimo_analisis = await db.analisis_fotos.find_one(
        {"proyecto_id": proyecto_id},
        sort=[("semana", -1)]
    )
    
    # Obtener historial
    historial = await db.analisis_fotos.find(
        {"proyecto_id": proyecto_id},
        {"_id": 0, "semana": 1, "pilas_detectadas": 1, "anclas_detectadas": 1}
    ).sort("semana", 1).to_list(100)
    
    resultado = await generar_reporte_progreso(
        proyecto_nombre=proyecto.get("nombre", "Proyecto"),
        semana_actual=ultimo_analisis.get("semana", 1) if ultimo_analisis else 1,
        pilas_planeadas=proyecto.get("total_pilas_planeadas", 0),
        pilas_detectadas=ultimo_analisis.get("pilas_detectadas", 0) if ultimo_analisis else 0,
        anclas_planeadas=proyecto.get("total_anclas_planeadas", 0),
        anclas_detectadas=ultimo_analisis.get("anclas_detectadas", 0) if ultimo_analisis else 0,
        historial_semanas=historial
    )
    
    return resultado


# Include the router in the main app
