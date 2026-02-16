"""
Servicio de análisis de cronogramas con IA y detección de avance en fotos
"""
import os
import logging
import base64
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from io import BytesIO

from dotenv import load_dotenv
load_dotenv()

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")


def excel_date_to_string(excel_date: int) -> str:
    """Convierte fecha serial de Excel a string YYYY-MM-DD"""
    try:
        if isinstance(excel_date, (int, float)) and excel_date > 40000:
            # Excel serial date (days since 1899-12-30)
            base_date = datetime(1899, 12, 30)
            result_date = base_date + timedelta(days=int(excel_date))
            return result_date.strftime("%Y-%m-%d")
        return str(excel_date)
    except Exception:
        return str(excel_date)


def parse_excel_cronograma(file_content: bytes) -> Dict[str, Any]:
    """
    Parsea un archivo Excel de cronograma y extrae la información de frentes y actividades.
    Retorna estructura lista para crear proyecto.
    """
    try:
        # Leer Excel
        df = pd.read_excel(BytesIO(file_content), header=None)
        
        frentes = []
        current_frente = None
        total_pilas = 0
        fecha_inicio_proyecto = None
        fecha_fin_proyecto = None
        total_dias = 0
        
        for idx, row in df.iterrows():
            # Detectar encabezado de frente
            first_cell = str(row.iloc[0]).strip().upper() if pd.notna(row.iloc[0]) else ""
            
            if first_cell.startswith("FRENTE"):
                # Nuevo frente encontrado
                if current_frente:
                    frentes.append(current_frente)
                
                current_frente = {
                    "nombre": first_cell,
                    "actividades": []
                }
            elif current_frente and first_cell and not first_cell.startswith("#") and "PILAS" not in first_cell:
                # Es una actividad del frente actual
                try:
                    actividad = {
                        "descripcion": str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else "",
                        "num_pilas": int(row.iloc[1]) if pd.notna(row.iloc[1]) else 0,
                        "fecha_inicio": excel_date_to_string(row.iloc[2]) if pd.notna(row.iloc[2]) else "",
                        "fecha_fin": excel_date_to_string(row.iloc[3]) if pd.notna(row.iloc[3]) else "",
                        "fecha_descabece": excel_date_to_string(row.iloc[4]) if pd.notna(row.iloc[4]) else "",
                        "dias": int(row.iloc[5]) if pd.notna(row.iloc[5]) else 0
                    }
                    
                    if actividad["descripcion"] and actividad["num_pilas"] > 0:
                        current_frente["actividades"].append(actividad)
                        total_pilas += actividad["num_pilas"]
                        total_dias += actividad["dias"]
                        
                        # Actualizar fechas del proyecto
                        if actividad["fecha_inicio"]:
                            act_inicio = actividad["fecha_inicio"]
                            if not fecha_inicio_proyecto or act_inicio < fecha_inicio_proyecto:
                                fecha_inicio_proyecto = act_inicio
                        
                        if actividad["fecha_descabece"]:
                            act_fin = actividad["fecha_descabece"]
                            if not fecha_fin_proyecto or act_fin > fecha_fin_proyecto:
                                fecha_fin_proyecto = act_fin
                except Exception as e:
                    logging.warning(f"Error parseando fila {idx}: {e}")
                    continue
        
        # Agregar último frente
        if current_frente:
            frentes.append(current_frente)
        
        # Calcular semanas
        semanas_estimadas = max(1, total_dias // 7) if total_dias > 0 else len(frentes) * 4
        
        return {
            "success": True,
            "frentes": frentes,
            "resumen": {
                "total_frentes": len(frentes),
                "total_pilas": total_pilas,
                "total_dias": total_dias,
                "semanas_estimadas": semanas_estimadas,
                "fecha_inicio": fecha_inicio_proyecto,
                "fecha_fin": fecha_fin_proyecto
            }
        }
        
    except Exception as e:
        logging.error(f"Error parseando Excel: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def analizar_foto_avance(
    imagen_base64: str,
    imagen_anterior_base64: Optional[str] = None,
    pilas_planeadas: int = 0,
    anclas_planeadas: int = 0,
    semana_actual: int = 1
) -> Dict[str, Any]:
    """
    Analiza una foto de avance de obra usando Gemini Vision para detectar:
    - Número de pilas visibles
    - Número de anclas instaladas
    - Comparación con semana anterior
    - Pronóstico de avance
    """
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
        
        if not EMERGENT_LLM_KEY:
            return {"success": False, "error": "EMERGENT_LLM_KEY no configurada"}
        
        # Crear chat con Gemini Vision
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"analisis-avance-{datetime.now().isoformat()}",
            system_message="""Eres un experto en análisis de imágenes de construcción civil, especializado en:
- Detección de pilas de cimentación (columnas circulares de concreto que salen del suelo)
- Detección de anclas de acero (barras de refuerzo que sobresalen de las pilas)
- Análisis de progreso de obra

Tu trabajo es analizar fotos aéreas de dron de sitios de construcción y proporcionar:
1. Conteo preciso de elementos visibles
2. Comparación con fotos anteriores si se proporcionan
3. Evaluación del progreso vs lo planeado

Responde SIEMPRE en formato JSON estructurado."""
        ).with_model("gemini", "gemini-2.5-flash")
        
        # Preparar contenido de imagen
        image_content = ImageContent(image_base64=imagen_base64)
        
        # Construir prompt
        prompt = f"""Analiza esta imagen aérea de una obra de construcción.

CONTEXTO:
- Semana actual del proyecto: {semana_actual}
- Pilas planeadas hasta esta semana: {pilas_planeadas}
- Anclas planeadas hasta esta semana: {anclas_planeadas}

INSTRUCCIONES:
1. Cuenta el número de PILAS visibles (columnas circulares de concreto que emergen del suelo)
2. Cuenta el número de ANCLAS visibles (barras de acero que sobresalen de las pilas)
3. Evalúa si el avance visual corresponde con lo planeado

Responde EXACTAMENTE en este formato JSON:
{{
    "pilas_detectadas": <número>,
    "anclas_detectadas": <número>,
    "pilas_en_proceso": <número de pilas que parecen estar en construcción>,
    "porcentaje_avance_estimado": <porcentaje 0-100>,
    "estado_proyecto": "<EN_TIEMPO | ADELANTADO | RETRASADO>",
    "confianza_deteccion": "<ALTA | MEDIA | BAJA>",
    "observaciones": "<descripción breve de lo que se observa>",
    "recomendaciones": "<sugerencias si hay retraso>"
}}"""
        
        # Si hay imagen anterior, agregar comparación
        if imagen_anterior_base64:
            prompt += """

COMPARACIÓN CON SEMANA ANTERIOR:
También se proporciona la imagen de la semana anterior. Compara ambas y agrega:
- pilas_nuevas: número de pilas nuevas desde la semana anterior
- anclas_nuevas: número de anclas nuevas desde la semana anterior
- cambio_observado: descripción del progreso visible"""
        
        # Enviar mensaje con imagen
        user_message = UserMessage(
            text=prompt,
            image_contents=[image_content]
        )
        
        response = await chat.send_message(user_message)
        
        # Parsear respuesta JSON
        import json
        import re
        
        # Extraer JSON de la respuesta
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            result = json.loads(json_match.group())
            result["success"] = True
            result["raw_response"] = response
            return result
        else:
            return {
                "success": True,
                "raw_response": response,
                "pilas_detectadas": 0,
                "anclas_detectadas": 0,
                "observaciones": response,
                "confianza_deteccion": "BAJA"
            }
            
    except Exception as e:
        logging.error(f"Error analizando imagen: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


async def generar_reporte_progreso(
    proyecto_nombre: str,
    semana_actual: int,
    pilas_planeadas: int,
    pilas_detectadas: int,
    anclas_planeadas: int,
    anclas_detectadas: int,
    historial_semanas: List[Dict] = None
) -> Dict[str, Any]:
    """
    Genera un reporte de progreso usando IA
    """
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        if not EMERGENT_LLM_KEY:
            return {"success": False, "error": "EMERGENT_LLM_KEY no configurada"}
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"reporte-{datetime.now().isoformat()}",
            system_message="Eres un experto en gestión de proyectos de construcción."
        ).with_model("gemini", "gemini-2.5-flash")
        
        historial_texto = ""
        if historial_semanas:
            historial_texto = "\nHistorial de semanas anteriores:\n"
            for h in historial_semanas:
                historial_texto += f"- Semana {h.get('semana')}: {h.get('pilas_detectadas', 0)} pilas, {h.get('anclas_detectadas', 0)} anclas\n"
        
        prompt = f"""Genera un breve reporte de progreso para el proyecto "{proyecto_nombre}":

Semana actual: {semana_actual}
Pilas planeadas: {pilas_planeadas}
Pilas detectadas: {pilas_detectadas}
Anclas planeadas: {anclas_planeadas}
Anclas detectadas: {anclas_detectadas}
{historial_texto}

Responde en JSON con:
{{
    "resumen_ejecutivo": "<2-3 oraciones>",
    "porcentaje_pilas": <número>,
    "porcentaje_anclas": <número>,
    "estado": "<EN_TIEMPO | ADELANTADO | RETRASADO>",
    "dias_diferencia": <positivo si adelantado, negativo si retrasado>,
    "fecha_estimada_termino": "<si hay retraso, nueva fecha estimada>",
    "acciones_recomendadas": ["<acción 1>", "<acción 2>"]
}}"""
        
        response = await chat.send_message(UserMessage(text=prompt))
        
        import json
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            result = json.loads(json_match.group())
            result["success"] = True
            return result
        
        return {"success": True, "resumen_ejecutivo": response}
        
    except Exception as e:
        logging.error(f"Error generando reporte: {e}")
        return {"success": False, "error": str(e)}
