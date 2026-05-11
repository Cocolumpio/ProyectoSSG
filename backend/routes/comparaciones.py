"""Rutas de Comparación de Avances con Residente - DrON Topografía"""
import os
import json
import uuid
import shutil
import logging
from pathlib import Path
from datetime import datetime, timezone

import resend
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse

from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType

from core.config import get_db, UPLOAD_DIR, ADMIN_EMAIL, EMERGENT_LLM_KEY
from services.email import enviar_alerta_discrepancia

db = get_db()
router = APIRouter(prefix="/api")

# --- Comparación de Avances con IA ---


@router.post("/proyectos/{proyecto_id}/comparar-avance")
async def comparar_avance_con_residente(
    proyecto_id: str,
    file: UploadFile = File(...)
):
    """
    Sube un PDF del reporte del residente de obra y lo compara con los datos del dron.
    Usa Gemini Vision para extraer las métricas del PDF y genera un análisis comparativo.
    """
    # Verificar que el proyecto existe
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Verificar que es un PDF
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")
    
    # Guardar el PDF
    pdfs_dir = UPLOAD_DIR / "reportes_residente" / proyecto_id
    pdfs_dir.mkdir(parents=True, exist_ok=True)
    
    unique_id = str(uuid.uuid4())
    pdf_filename = f"{unique_id}_{file.filename}"
    pdf_path = pdfs_dir / pdf_filename
    
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    pdf_url = f"/api/reportes-residente/{proyecto_id}/{pdf_filename}"
    
    # Obtener datos acumulados del dron (sistema)
    avances = await db.avances_semanales.find(
        {"proyecto_id": proyecto_id}, 
        {"_id": 0}
    ).to_list(100)
    
    # Calcular totales acumulados del sistema
    volumen_excavado_dron = sum((a.get('volumen_excavacion', 0) or 0) for a in avances)
    pilas_completadas_dron = sum((a.get('pilas_completadas', 0) or 0) for a in avances)
    anclas_instaladas_dron = sum((a.get('anclas_instaladas', 0) or 0) for a in avances)
    muros_completados_dron = sum((a.get('muros_completados', 0) or 0) for a in avances)
    
    # Obtener metas del proyecto
    volumen_total_planeado = proyecto.get('volumen_total_planeado', 0) or 0
    pilas_planeadas = proyecto.get('pilas_planeadas', 0) or 0
    anclas_planeadas = proyecto.get('anclas_planeadas', 0) or 0
    muros_planeados = proyecto.get('muros_planeados', 0) or 0
    
    # Calcular porcentajes de avance del dron
    avance_excavacion_dron = (volumen_excavado_dron / volumen_total_planeado * 100) if volumen_total_planeado > 0 else 0
    avance_pilas_dron = (pilas_completadas_dron / pilas_planeadas * 100) if pilas_planeadas > 0 else 0
    avance_anclas_dron = (anclas_instaladas_dron / anclas_planeadas * 100) if anclas_planeadas > 0 else 0
    avance_muros_dron = (muros_completados_dron / muros_planeados * 100) if muros_planeados > 0 else 0
    
    metricas_dron = {
        "volumen_excavado": volumen_excavado_dron,
        "volumen_planeado": volumen_total_planeado,
        "avance_excavacion_pct": round(avance_excavacion_dron, 2),
        "pilas_completadas": pilas_completadas_dron,
        "pilas_planeadas": pilas_planeadas,
        "avance_pilas_pct": round(avance_pilas_dron, 2),
        "anclas_instaladas": anclas_instaladas_dron,
        "anclas_planeadas": anclas_planeadas,
        "avance_anclas_pct": round(avance_anclas_dron, 2),
        "muros_completados": muros_completados_dron,
        "muros_planeados": muros_planeados,
        "avance_muros_pct": round(avance_muros_dron, 2),
        "semanas_registradas": len(avances)
    }
    
    # Analizar el PDF con Gemini
    try:
        emergent_key = os.environ.get('EMERGENT_LLM_KEY')
        if not emergent_key:
            raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY no configurada")
        
        chat = LlmChat(
            api_key=emergent_key,
            session_id=f"comparacion-{proyecto_id}-{unique_id}",
            system_message="""Eres un experto en análisis de reportes de avance de construcción.
Tu tarea es extraer las métricas de avance del PDF del residente de obra y compararlas con los datos del dron.

IMPORTANTE: Debes responder ÚNICAMENTE en formato JSON válido, sin texto adicional.
El JSON debe tener esta estructura exacta:
{
    "metricas_extraidas": {
        "excavacion_m3": número o null,
        "excavacion_porcentaje": número o null,
        "pilas_perforadas": número o null,
        "pilas_porcentaje": número o null,
        "anclas_tensadas": número o null,
        "anclas_porcentaje": número o null,
        "muros_m2": número o null,
        "muros_porcentaje": número o null,
        "avance_general_porcentaje": número o null
    },
    "discrepancias": ["lista de discrepancias encontradas"],
    "analisis": "análisis detallado de la comparación",
    "recomendaciones": ["lista de recomendaciones"],
    "confianza": "ALTA" | "MEDIA" | "BAJA"
}"""
        ).with_model("gemini", "gemini-2.5-flash")
        
        pdf_file = FileContentWithMimeType(
            file_path=str(pdf_path),
            mime_type="application/pdf"
        )
        
        prompt = f"""Analiza el PDF adjunto que es un reporte de avance de obra del residente.

DATOS DEL SISTEMA DE DRONES (referencia para comparar):
- Excavación: {volumen_excavado_dron:,.2f} m³ ejecutados de {volumen_total_planeado:,.2f} m³ planeados ({avance_excavacion_dron:.1f}%)
- Pilas: {pilas_completadas_dron} ejecutadas de {pilas_planeadas} planeadas ({avance_pilas_dron:.1f}%)
- Anclas: {anclas_instaladas_dron} instaladas de {anclas_planeadas} planeadas ({avance_anclas_dron:.1f}%)
- Muros: {muros_completados_dron} completados de {muros_planeados} planeados ({avance_muros_dron:.1f}%)

Extrae las métricas del PDF y compáralas con los datos del dron.
Identifica discrepancias significativas (diferencias > 5%) y explica posibles razones.
Responde SOLO con el JSON especificado, sin texto adicional."""
        
        user_message = UserMessage(
            text=prompt,
            file_contents=[pdf_file]
        )
        
        response = await chat.send_message(user_message)
        
        # Parsear respuesta JSON
        import json
        # Limpiar la respuesta (quitar posibles marcadores de código)
        response_clean = response.strip()
        if response_clean.startswith("```json"):
            response_clean = response_clean[7:]
        if response_clean.startswith("```"):
            response_clean = response_clean[3:]
        if response_clean.endswith("```"):
            response_clean = response_clean[:-3]
        response_clean = response_clean.strip()
        
        analisis_ia = json.loads(response_clean)
        
        metricas_residente = analisis_ia.get("metricas_extraidas", {})
        
        # Crear comparaciones detalladas
        comparaciones = []
        
        # Excavación
        if metricas_residente.get("excavacion_m3") is not None:
            diff = metricas_residente["excavacion_m3"] - volumen_excavado_dron
            diff_pct = (diff / volumen_excavado_dron * 100) if volumen_excavado_dron > 0 else 0
            estado = "coincide" if abs(diff_pct) < 5 else ("discrepancia_menor" if abs(diff_pct) < 15 else "discrepancia_mayor")
            comparaciones.append({
                "nombre": "Excavación",
                "unidad": "m³",
                "valor_dron": volumen_excavado_dron,
                "valor_residente": metricas_residente["excavacion_m3"],
                "diferencia": round(diff, 2),
                "diferencia_porcentaje": round(diff_pct, 2),
                "estado": estado
            })
        
        # Pilas
        if metricas_residente.get("pilas_perforadas") is not None:
            diff = metricas_residente["pilas_perforadas"] - pilas_completadas_dron
            diff_pct = (diff / pilas_completadas_dron * 100) if pilas_completadas_dron > 0 else 0
            estado = "coincide" if abs(diff_pct) < 5 else ("discrepancia_menor" if abs(diff_pct) < 15 else "discrepancia_mayor")
            comparaciones.append({
                "nombre": "Pilas Perforadas",
                "unidad": "pzas",
                "valor_dron": pilas_completadas_dron,
                "valor_residente": metricas_residente["pilas_perforadas"],
                "diferencia": round(diff, 2),
                "diferencia_porcentaje": round(diff_pct, 2),
                "estado": estado
            })
        
        # Anclas
        if metricas_residente.get("anclas_tensadas") is not None:
            diff = metricas_residente["anclas_tensadas"] - anclas_instaladas_dron
            diff_pct = (diff / anclas_instaladas_dron * 100) if anclas_instaladas_dron > 0 else 0
            estado = "coincide" if abs(diff_pct) < 5 else ("discrepancia_menor" if abs(diff_pct) < 15 else "discrepancia_mayor")
            comparaciones.append({
                "nombre": "Anclas Tensadas",
                "unidad": "pzas",
                "valor_dron": anclas_instaladas_dron,
                "valor_residente": metricas_residente["anclas_tensadas"],
                "diferencia": round(diff, 2),
                "diferencia_porcentaje": round(diff_pct, 2),
                "estado": estado
            })
        
        # Muros
        if metricas_residente.get("muros_m2") is not None:
            diff = metricas_residente["muros_m2"] - muros_completados_dron
            diff_pct = (diff / muros_completados_dron * 100) if muros_completados_dron > 0 else 0
            estado = "coincide" if abs(diff_pct) < 5 else ("discrepancia_menor" if abs(diff_pct) < 15 else "discrepancia_mayor")
            comparaciones.append({
                "nombre": "Muros/Lanzado",
                "unidad": "m²",
                "valor_dron": muros_completados_dron,
                "valor_residente": metricas_residente["muros_m2"],
                "diferencia": round(diff, 2),
                "diferencia_porcentaje": round(diff_pct, 2),
                "estado": estado
            })
        
        # Crear registro de comparación
        comparacion = {
            "id": unique_id,
            "proyecto_id": proyecto_id,
            "semana": len(avances),
            "fecha_comparacion": datetime.now(timezone.utc).isoformat(),
            "pdf_url": pdf_url,
            "pdf_nombre": file.filename,
            "metricas_residente": metricas_residente,
            "metricas_dron": metricas_dron,
            "comparaciones": comparaciones,
            "resumen_ia": analisis_ia.get("analisis", ""),
            "discrepancias_detectadas": analisis_ia.get("discrepancias", []),
            "recomendaciones": analisis_ia.get("recomendaciones", []),
            "estado_comparacion": "analizado",
            "avance_general_residente": metricas_residente.get("avance_general_porcentaje", 0) or 0,
            "avance_general_dron": proyecto.get('avance_actual', 0) or 0,
            "confianza": analisis_ia.get("confianza", "MEDIA")
        }
        
        # Guardar en la base de datos
        await db.comparaciones_avance.insert_one(comparacion)
        
        # Eliminar _id de MongoDB para la respuesta
        comparacion.pop('_id', None)
        
        # Verificar si hay discrepancias críticas (>15%) y enviar alerta
        discrepancias_criticas = [c for c in comparaciones if c.get("estado") == "discrepancia_mayor"]
        if discrepancias_criticas and ADMIN_EMAIL and resend.api_key:
            try:
                await enviar_alerta_discrepancia(
                    proyecto_nombre=proyecto.get("nombre", "Proyecto"),
                    proyecto_id=proyecto_id,
                    discrepancias=discrepancias_criticas,
                    resumen_ia=analisis_ia.get("analisis", ""),
                    pdf_nombre=file.filename
                )
                comparacion["alerta_enviada"] = True
                logging.info(f"Alerta de discrepancia enviada para proyecto {proyecto_id}")
            except Exception as email_err:
                logging.error(f"Error enviando alerta de discrepancia: {email_err}")
                comparacion["alerta_enviada"] = False
        
        return comparacion
        
    except json.JSONDecodeError as e:
        logging.error(f"Error parseando respuesta de IA: {e}")
        logging.error(f"Respuesta recibida: {response}")
        raise HTTPException(status_code=500, detail=f"Error procesando respuesta de IA: {str(e)}")
    except Exception as e:
        logging.error(f"Error en análisis de PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Error analizando PDF: {str(e)}")


@router.get("/proyectos/{proyecto_id}/comparaciones")
async def obtener_comparaciones(proyecto_id: str):
    """Obtener historial de comparaciones de un proyecto"""
    comparaciones = await db.comparaciones_avance.find(
        {"proyecto_id": proyecto_id},
        {"_id": 0}
    ).sort("fecha_comparacion", -1).to_list(50)
    
    return comparaciones


@router.get("/reportes-residente/{proyecto_id}/{filename}")
async def obtener_reporte_residente(proyecto_id: str, filename: str):
    """Obtener un PDF de reporte del residente"""
    file_path = UPLOAD_DIR / "reportes_residente" / proyecto_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    return FileResponse(
        file_path,
        media_type="application/pdf",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Content-Disposition": f"inline; filename={filename}"
        }
    )


@router.delete("/proyectos/{proyecto_id}/comparaciones/{comparacion_id}")
async def eliminar_comparacion(proyecto_id: str, comparacion_id: str):
    """Eliminar una comparación de avance"""
    # Obtener la comparación para eliminar el PDF
    comparacion = await db.comparaciones_avance.find_one({
        "id": comparacion_id,
        "proyecto_id": proyecto_id
    })
    
    if not comparacion:
        raise HTTPException(status_code=404, detail="Comparación no encontrada")
    
    # Eliminar el PDF si existe
    pdf_url = comparacion.get("pdf_url", "")
    if pdf_url:
        try:
            filename = pdf_url.split("/")[-1]
            file_path = UPLOAD_DIR / "reportes_residente" / proyecto_id / filename
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logging.error(f"Error eliminando PDF: {e}")
    
    # Eliminar de la base de datos
    await db.comparaciones_avance.delete_one({
        "id": comparacion_id,
        "proyecto_id": proyecto_id
    })
    
    return {"message": "Comparación eliminada"}

