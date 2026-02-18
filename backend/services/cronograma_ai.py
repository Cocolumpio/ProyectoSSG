"""
Servicio de análisis de cronogramas con IA y detección de avance en fotos
"""
import os
import logging
import base64
import pandas as pd
import re
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


def detectar_tipo_actividad(descripcion: str) -> Dict[str, Any]:
    """
    Detecta el tipo de actividad basado en palabras clave en la descripción.
    Retorna el tipo y si aplica anclas.
    """
    desc_lower = descripcion.lower()
    
    # Patrones para detectar tipos
    if any(word in desc_lower for word in ['pila', 'pilas', 'pilote', 'pilotes']):
        return {"tipo": "pilas", "tiene_anclas": True}
    elif any(word in desc_lower for word in ['muro', 'muros', 'muro milan', 'pantalla']):
        return {"tipo": "muros", "tiene_anclas": True}
    elif any(word in desc_lower for word in ['excavac', 'excavar', 'terraceria', 'desmonte', 'despalme']):
        return {"tipo": "excavacion", "tiene_anclas": False}
    elif any(word in desc_lower for word in ['ciment', 'zapata', 'losa', 'dado']):
        return {"tipo": "cimentacion", "tiene_anclas": False}
    elif any(word in desc_lower for word in ['ancla', 'anclas', 'anclaje']):
        return {"tipo": "anclas", "tiene_anclas": True}
    else:
        return {"tipo": "otro", "tiene_anclas": False}


def parse_excel_cronograma(file_content: bytes) -> Dict[str, Any]:
    """
    Parsea un archivo Excel de cronograma y extrae la información de frentes y actividades.
    Detecta automáticamente los tipos de actividades (excavación, pilas, muros, anclas).
    Retorna estructura lista para crear proyecto.
    """
    try:
        # Leer Excel
        df = pd.read_excel(BytesIO(file_content), header=None)
        
        frentes = []
        current_frente = None
        # Contadores totales
        total_pilas = 0
        total_muros = 0
        total_anclas = 0
        total_excavacion = 0
        # Fechas
        fecha_inicio_proyecto = None
        fecha_fin_proyecto = None
        total_dias = 0
        # Tipos de actividades detectadas
        tipos_actividades = set()
        # Semanas por tipo
        semanas_por_tipo = {"excavacion": 0, "pilas": 0, "muros": 0, "anclas": 0}
        
        for idx, row in df.iterrows():
            # Detectar encabezado de frente (primera columna contiene "FRENTE")
            first_cell = str(row.iloc[0]).strip().upper() if pd.notna(row.iloc[0]) else ""
            second_cell = str(row.iloc[1]).strip().upper() if len(row) > 1 and pd.notna(row.iloc[1]) else ""
            
            # Si es header de frente
            is_frente_header = first_cell.startswith("FRENTE") and (
                "#PILAS" in second_cell or "PILAS" in second_cell or 
                "#" in second_cell or "CANTIDAD" in second_cell
            )
            
            if is_frente_header:
                # Guardar frente anterior si existe
                if current_frente:
                    frentes.append(current_frente)
                
                current_frente = {
                    "nombre": first_cell,
                    "actividades": [],
                    "tipo_principal": None
                }
                continue
            
            # Si tenemos un frente activo y la segunda columna tiene un número (cantidad)
            if current_frente:
                try:
                    cantidad_val = row.iloc[1] if len(row) > 1 else None
                    if pd.notna(cantidad_val) and isinstance(cantidad_val, (int, float)) and cantidad_val > 0:
                        # Es una actividad válida
                        descripcion = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
                        
                        # Detectar tipo de actividad
                        tipo_info = detectar_tipo_actividad(descripcion)
                        tipo = tipo_info["tipo"]
                        tiene_anclas = tipo_info["tiene_anclas"]
                        
                        # Parsear fechas
                        fecha_inicio_raw = row.iloc[2] if len(row) > 2 else None
                        fecha_fin_raw = row.iloc[3] if len(row) > 3 else None
                        fecha_descabece_raw = row.iloc[4] if len(row) > 4 else None
                        dias_raw = row.iloc[5] if len(row) > 5 else 0
                        
                        # Convertir fechas
                        def parse_fecha(val):
                            if pd.isna(val):
                                return ""
                            if isinstance(val, datetime):
                                return val.strftime("%Y-%m-%d")
                            return excel_date_to_string(val)
                        
                        cantidad = int(cantidad_val)
                        dias = int(dias_raw) if pd.notna(dias_raw) and isinstance(dias_raw, (int, float)) else 0
                        
                        actividad = {
                            "descripcion": descripcion,
                            "cantidad": cantidad,
                            "tipo": tipo,
                            "tiene_anclas": tiene_anclas,
                            "fecha_inicio": parse_fecha(fecha_inicio_raw),
                            "fecha_fin": parse_fecha(fecha_fin_raw),
                            "fecha_descabece": parse_fecha(fecha_descabece_raw),
                            "dias": dias
                        }
                        
                        current_frente["actividades"].append(actividad)
                        
                        # Actualizar contadores según tipo
                        if tipo == "pilas" or "pila" in descripcion.lower():
                            total_pilas += cantidad
                            tipos_actividades.add("pilas")
                            semanas_por_tipo["pilas"] += max(1, dias // 7)
                        elif tipo == "muros":
                            total_muros += cantidad
                            tipos_actividades.add("muros")
                            semanas_por_tipo["muros"] += max(1, dias // 7)
                        elif tipo == "excavacion":
                            total_excavacion += cantidad
                            tipos_actividades.add("excavacion")
                            semanas_por_tipo["excavacion"] += max(1, dias // 7)
                        elif tipo == "anclas":
                            total_anclas += cantidad
                            tipos_actividades.add("anclas")
                            semanas_por_tipo["anclas"] += max(1, dias // 7)
                        else:
                            # Por defecto, si tiene número y parece ser pilas
                            total_pilas += cantidad
                            tipos_actividades.add("pilas")
                        
                        # Si tiene anclas, estimar cantidad
                        if tiene_anclas:
                            total_anclas += cantidad  # Una ancla por pila/muro
                            tipos_actividades.add("anclas")
                        
                        total_dias += dias
                        
                        # Actualizar fechas del proyecto
                        if actividad["fecha_inicio"]:
                            if not fecha_inicio_proyecto or actividad["fecha_inicio"] < fecha_inicio_proyecto:
                                fecha_inicio_proyecto = actividad["fecha_inicio"]
                        
                        if actividad["fecha_descabece"]:
                            if not fecha_fin_proyecto or actividad["fecha_descabece"] > fecha_fin_proyecto:
                                fecha_fin_proyecto = actividad["fecha_descabece"]
                        elif actividad["fecha_fin"]:
                            if not fecha_fin_proyecto or actividad["fecha_fin"] > fecha_fin_proyecto:
                                fecha_fin_proyecto = actividad["fecha_fin"]
                                
                except Exception as e:
                    logging.warning(f"Error parseando fila {idx}: {e}")
                    continue
        
        # Agregar último frente
        if current_frente:
            frentes.append(current_frente)
        
        # Calcular semanas basado en el rango de fechas
        semanas_estimadas = 1
        if fecha_inicio_proyecto and fecha_fin_proyecto:
            try:
                inicio = datetime.strptime(fecha_inicio_proyecto, "%Y-%m-%d")
                fin = datetime.strptime(fecha_fin_proyecto, "%Y-%m-%d")
                dias_totales = (fin - inicio).days
                semanas_estimadas = max(1, (dias_totales + 6) // 7)  # Redondear hacia arriba
            except:
                semanas_estimadas = max(1, total_dias // 7) if total_dias > 0 else len(frentes) * 4
        
        return {
            "success": True,
            "frentes": frentes,
            "resumen": {
                "total_frentes": len(frentes),
                "total_actividades": sum(len(f["actividades"]) for f in frentes),
                "total_dias": total_dias,
                "semanas_estimadas": semanas_estimadas,
                "fecha_inicio": fecha_inicio_proyecto,
                "fecha_fin": fecha_fin_proyecto,
                # Métricas por tipo
                "total_pilas": total_pilas,
                "total_muros": total_muros,
                "total_anclas": total_anclas,
                "total_excavacion": total_excavacion,
                # Tipos de actividades detectadas
                "tipos_actividades": list(tipos_actividades),
                # Semanas por tipo
                "semanas_excavacion": semanas_por_tipo["excavacion"],
                "semanas_pilas": semanas_por_tipo["pilas"],
                "semanas_muros": semanas_por_tipo["muros"],
                "semanas_anclas": semanas_por_tipo["anclas"]
            }
        }
        
    except Exception as e:
        logging.error(f"Error parseando Excel: {e}")
        import traceback
        traceback.print_exc()
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
    import tempfile
    import os
    
    try:
        from emergentintegrations.llm.chat import LlmChat, FileContentWithMimeType
        
        if not EMERGENT_LLM_KEY:
            return {"success": False, "error": "EMERGENT_LLM_KEY no configurada"}
        
        # Guardar imagen temporalmente
        import base64
        image_data = base64.b64decode(imagen_base64)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_file.write(image_data)
            temp_path = tmp_file.name
        
        try:
            # Construir prompt detallado
            prompt = f"""Analiza esta imagen aérea de una obra de construcción de cimentaciones profundas.

CONTEXTO:
- Semana actual del proyecto: {semana_actual}
- Pilas planeadas hasta esta semana: {pilas_planeadas}
- Anclas planeadas hasta esta semana: {anclas_planeadas}

QUÉ BUSCAR:
1. PILAS DE CIMENTACIÓN: Son columnas circulares de concreto que emergen del suelo, típicamente de 60cm a 120cm de diámetro. Se ven como círculos o cilindros grises desde arriba.

2. ANCLAS/ANCLAJES: Son barras de acero (varillas) que sobresalen de las pilas ya construidas. Se ven como puntos oscuros o pequeñas estructuras metálicas encima de las pilas terminadas.

3. PILAS EN PROCESO: Áreas donde se está excavando (agujeros en el suelo) o donde hay maquinaria de perforación trabajando.

4. EXCAVACIÓN: Áreas donde se ha removido tierra, taludes, rampas de acceso.

INSTRUCCIONES:
- Cuenta TODOS los elementos que puedas identificar claramente
- Si hay duda, incluye el elemento pero indica confianza media/baja
- Describe qué ves en la imagen

Responde EXACTAMENTE en este formato JSON:
{{
    "pilas_detectadas": <número de pilas terminadas visibles>,
    "anclas_detectadas": <número de anclas/anclajes visibles>,
    "pilas_en_proceso": <número de pilas en construcción>,
    "excavaciones_activas": <número de puntos de excavación>,
    "porcentaje_avance_estimado": <porcentaje 0-100 basado en lo visible>,
    "estado_proyecto": "<EN_TIEMPO | ADELANTADO | RETRASADO | NO_DETERMINABLE>",
    "confianza_deteccion": "<ALTA | MEDIA | BAJA>",
    "elementos_identificados": "<lista de lo que se puede ver claramente>",
    "observaciones": "<descripción detallada de lo que se observa en la imagen>",
    "condiciones_terreno": "<estado del terreno, clima visible, etc>",
    "maquinaria_visible": "<descripción de equipos visibles>",
    "recomendaciones": "<sugerencias basadas en lo observado>"
}}"""
            
            # Crear chat con Gemini Vision
            llm = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"analisis-foto-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                system_message="Eres un experto en análisis de imágenes de construcción civil."
            ).with_model("gemini", "gemini-2.0-flash")
            
            # Preparar imagen como FileContentWithMimeType usando la ruta del archivo temporal
            image_file = FileContentWithMimeType(
                mime_type="image/jpeg",
                file_path=temp_path
            )
            
            # Crear mensaje con texto e imagen
            from emergentintegrations.llm.chat import UserMessage
            user_message = UserMessage(
                text=prompt,
                file_contents=[image_file]
            )
            
            # Enviar mensaje
            response = await llm.send_message(user_message)
            
            # Parsear respuesta JSON
            import json
            import re
            
            # Limpiar respuesta
            response_text = response.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            # Extraer JSON de la respuesta
            json_match = re.search(r'\{[\s\S]*\}', response_text)
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
        finally:
            # Limpiar archivo temporal
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            
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
