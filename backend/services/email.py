"""
Servicio de Email para DrON Topografía
Usa Resend para enviar notificaciones y alertas
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional
import resend

from core.config import RESEND_API_KEY, ADMIN_EMAIL

# Configure Resend
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

logger = logging.getLogger(__name__)


async def enviar_alerta_discrepancia(
    proyecto_nombre: str,
    proyecto_id: str,
    discrepancias: list,
    resumen_ia: str,
    pdf_nombre: str
) -> bool:
    """
    Envía una alerta por email cuando se detectan discrepancias críticas (>15%)
    entre los datos del dron y el reporte del residente.
    """
    if not ADMIN_EMAIL or not RESEND_API_KEY:
        logger.warning("No se puede enviar alerta: ADMIN_EMAIL o RESEND_API_KEY no configurados")
        return False
    
    # Construir tabla de discrepancias
    discrepancias_html = ""
    for d in discrepancias:
        color = "#dc2626"
        discrepancias_html += f"""
        <tr style="background-color: #fef2f2;">
            <td style="padding: 12px; border-bottom: 1px solid #fecaca;">{d.get('nombre', 'N/A')}</td>
            <td style="padding: 12px; border-bottom: 1px solid #fecaca; text-align: right;">{d.get('valor_dron', 0):,.2f} {d.get('unidad', '')}</td>
            <td style="padding: 12px; border-bottom: 1px solid #fecaca; text-align: right;">{d.get('valor_residente', 0):,.2f} {d.get('unidad', '')}</td>
            <td style="padding: 12px; border-bottom: 1px solid #fecaca; text-align: right; color: {color}; font-weight: bold;">
                {d.get('diferencia_porcentaje', 0):+.1f}%
            </td>
        </tr>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #994B49 0%, #B85C5A 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 24px;">⚠️ Alerta de Discrepancia</h1>
            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">DrON Topografía - Sistema de Monitoreo</p>
        </div>
        
        <div style="background: #fff; padding: 30px; border: 1px solid #e5e5e5; border-top: none; border-radius: 0 0 10px 10px;">
            <div style="background: #fef2f2; border-left: 4px solid #dc2626; padding: 15px; margin-bottom: 20px; border-radius: 4px;">
                <strong style="color: #dc2626;">Se detectaron discrepancias críticas (&gt;15%)</strong>
                <p style="margin: 5px 0 0 0; color: #7f1d1d;">
                    El análisis del reporte del residente muestra diferencias significativas con los datos del dron.
                </p>
            </div>
            
            <h2 style="color: #994B49; border-bottom: 2px solid #994B49; padding-bottom: 10px; margin-top: 0;">
                📋 Proyecto: {proyecto_nombre}
            </h2>
            
            <p><strong>Archivo analizado:</strong> {pdf_nombre}</p>
            <p><strong>Fecha:</strong> {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC</p>
            
            <h3 style="color: #dc2626; margin-top: 25px;">🔴 Discrepancias Detectadas</h3>
            
            <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                <thead>
                    <tr style="background: #f3f4f6;">
                        <th style="padding: 12px; text-align: left; border-bottom: 2px solid #e5e5e5;">Métrica</th>
                        <th style="padding: 12px; text-align: right; border-bottom: 2px solid #e5e5e5;">Dron</th>
                        <th style="padding: 12px; text-align: right; border-bottom: 2px solid #e5e5e5;">Residente</th>
                        <th style="padding: 12px; text-align: right; border-bottom: 2px solid #e5e5e5;">Diferencia</th>
                    </tr>
                </thead>
                <tbody>
                    {discrepancias_html}
                </tbody>
            </table>
            
            <h3 style="color: #994B49; margin-top: 25px;">🤖 Análisis de IA</h3>
            <div style="background: #f9fafb; padding: 15px; border-radius: 8px; border: 1px solid #e5e5e5;">
                <p style="margin: 0; white-space: pre-wrap;">{resumen_ia[:800]}{'...' if len(resumen_ia) > 800 else ''}</p>
            </div>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e5e5;">
                <p style="color: #6b7280; font-size: 12px; margin: 0;">
                    Esta alerta se generó automáticamente al detectar diferencias mayores al 15% entre los datos del sistema de drones y el reporte del residente de obra. 
                    Se recomienda revisar ambas fuentes para identificar la causa de la discrepancia.
                </p>
            </div>
        </div>
        
        <div style="text-align: center; padding: 20px; color: #6b7280; font-size: 12px;">
            <p>DrON Topografía © 2025</p>
        </div>
    </body>
    </html>
    """
    
    try:
        params = {
            "from": "DrON Topografía <onboarding@resend.dev>",
            "to": [ADMIN_EMAIL],
            "subject": f"⚠️ Alerta: Discrepancias críticas en {proyecto_nombre}",
            "html": html_content
        }
        
        await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Alerta de discrepancia enviada a {ADMIN_EMAIL} para proyecto {proyecto_nombre}")
        return True
    except Exception as e:
        logger.error(f"Error enviando alerta de discrepancia: {e}")
        return False


async def enviar_notificacion_solicitud_vuelo(
    solicitud_data: dict,
    google_calendar_link: str
) -> bool:
    """
    Envía notificación de nueva solicitud de vuelo al admin.
    """
    if not ADMIN_EMAIL or not RESEND_API_KEY:
        logger.warning("No se puede enviar notificación: ADMIN_EMAIL o RESEND_API_KEY no configurados")
        return False
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8f9fa;">
        <div style="background-color: #994B49; color: white; padding: 20px; border-radius: 10px 10px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 24px;">🚁 Nueva Solicitud de Vuelo</h1>
            <p style="margin: 5px 0 0 0; opacity: 0.9;">DrON Topografía</p>
        </div>
        
        <div style="background-color: white; padding: 25px; border: 1px solid #e5e7eb; border-top: none;">
            <h2 style="color: #994B49; margin-top: 0;">Detalles del Proyecto</h2>
            
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; color: #6b7280; width: 40%;">Nombre del Proyecto:</td>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; font-weight: bold;">{solicitud_data.get('nombre_proyecto', 'N/A')}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; color: #6b7280;">Fecha Inicio:</td>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{solicitud_data.get('fecha_inicio_proyecto', 'N/A')}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; color: #6b7280;">Fecha Fin:</td>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{solicitud_data.get('fecha_fin_proyecto', 'N/A')}</td>
                </tr>
            </table>
            
            <h2 style="color: #994B49;">📅 Fecha Solicitada para el Vuelo</h2>
            
            <div style="background-color: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 15px; margin-bottom: 20px;">
                <p style="margin: 0; font-size: 18px; font-weight: bold; color: #92400e;">
                    {solicitud_data.get('fecha_vuelo_deseada', 'N/A')}
                    {f" a las {solicitud_data.get('hora_preferencia')}" if solicitud_data.get('hora_preferencia') else ''}
                </p>
            </div>
            
            {f'''
            <h3 style="color: #374151;">📝 Notas del Cliente:</h3>
            <div style="background-color: #f3f4f6; border-radius: 8px; padding: 15px; margin-bottom: 20px;">
                <p style="margin: 0; color: #4b5563;">{solicitud_data.get("notas")}</p>
            </div>
            ''' if solicitud_data.get('notas') else ''}
            
            <div style="text-align: center; margin-top: 25px;">
                <a href="{google_calendar_link}" 
                   style="display: inline-block; background-color: #994B49; color: white; padding: 15px 30px; 
                          text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">
                    📅 Agregar a Google Calendar
                </a>
            </div>
            
            <p style="color: #9ca3af; font-size: 12px; text-align: center; margin-top: 25px;">
                Este correo fue generado automáticamente desde DrON Topografía.
            </p>
        </div>
        
        <div style="background-color: #994B49; color: white; padding: 15px; border-radius: 0 0 10px 10px; text-align: center;">
            <p style="margin: 0; font-size: 12px; opacity: 0.8;">
                © {datetime.now().year} DrON Topografía - Gestión de Construcción con Drones
            </p>
        </div>
    </body>
    </html>
    """
    
    try:
        params = {
            "from": "DrON Topografía <onboarding@resend.dev>",
            "to": [ADMIN_EMAIL],
            "subject": f"🚁 Nueva Solicitud de Vuelo - {solicitud_data.get('nombre_proyecto', 'Proyecto')}",
            "html": html_content
        }
        
        await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Email de solicitud enviado: {solicitud_data.get('nombre_proyecto')}")
        return True
    except Exception as e:
        logger.error(f"Error enviando email: {e}")
        return False


async def enviar_actualizacion_solicitud(
    solicitud: dict,
    nuevo_estado: str,
    comentario_admin: Optional[str] = None
) -> bool:
    """
    Envía notificación al cliente cuando se actualiza el estado de su solicitud.
    """
    cliente_email = solicitud.get("cliente_email")
    if not cliente_email or not RESEND_API_KEY:
        return False
    
    if nuevo_estado not in ["confirmado", "cancelado"]:
        return False
    
    estado_texto = "CONFIRMADO ✅" if nuevo_estado == "confirmado" else "CANCELADO ❌"
    estado_color = "#059669" if nuevo_estado == "confirmado" else "#DC2626"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8f9fa;">
        <div style="background-color: #994B49; color: white; padding: 20px; border-radius: 10px 10px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 24px;">🚁 Actualización de Solicitud</h1>
            <p style="margin: 5px 0 0 0; opacity: 0.9;">DrON Topografía</p>
        </div>
        
        <div style="background-color: white; padding: 25px; border: 1px solid #e5e7eb; border-top: none;">
            <h2 style="color: {estado_color}; margin-top: 0; text-align: center;">{estado_texto}</h2>
            
            <p>Hola <strong>{solicitud.get('cliente_nombre', 'Cliente')}</strong>,</p>
            
            <p>Tu solicitud de vuelo para el proyecto <strong>{solicitud.get('nombre_proyecto')}</strong> ha sido <strong style="color: {estado_color};">{nuevo_estado}</strong>.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; color: #6b7280;">Fecha solicitada:</td>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; font-weight: bold;">{solicitud.get('fecha_vuelo_deseada')}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; color: #6b7280;">Hora preferida:</td>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{solicitud.get('hora_preferencia', 'Sin preferencia')}</td>
                </tr>
            </table>
            
            {f'<div style="background-color: #f3f4f6; border-radius: 8px; padding: 15px; margin: 20px 0;"><strong>Comentario del administrador:</strong><p style="margin: 10px 0 0 0;">{comentario_admin}</p></div>' if comentario_admin else ''}
            
            <p style="color: #6b7280; font-size: 14px; margin-top: 20px;">
                Si tienes alguna pregunta, no dudes en contactarnos.
            </p>
        </div>
        
        <div style="background-color: #994B49; color: white; padding: 15px; border-radius: 0 0 10px 10px; text-align: center;">
            <p style="margin: 0; font-size: 12px; opacity: 0.8;">© {datetime.now().year} DrON Topografía</p>
        </div>
    </body>
    </html>
    """
    
    try:
        params = {
            "from": "DrON Topografía <onboarding@resend.dev>",
            "to": [cliente_email],
            "subject": f"🚁 Tu solicitud ha sido {nuevo_estado} - {solicitud.get('nombre_proyecto')}",
            "html": html_content
        }
        
        await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Email de notificación enviado a {cliente_email}")
        return True
    except Exception as e:
        logger.error(f"Error enviando email de notificación: {e}")
        return False


async def enviar_alerta_desviacion_cronograma(
    proyecto_nombre: str,
    proyecto_id: str,
    desviaciones: list,
    resumen: str,
    fecha_analisis: str
) -> bool:
    """
    Envía una alerta por email cuando el progreso real se desvía significativamente
    del cronograma planificado (>20% de retraso).
    """
    if not ADMIN_EMAIL or not RESEND_API_KEY:
        logger.warning("No se puede enviar alerta: ADMIN_EMAIL o RESEND_API_KEY no configurados")
        return False
    
    # Construir tabla de desviaciones
    desviaciones_html = ""
    for d in desviaciones:
        porcentaje = d.get('desviacion_porcentaje', 0)
        if porcentaje < -10:
            color = "#dc2626"  # Rojo - retraso crítico
            estado = "⚠️ Retraso"
        elif porcentaje > 10:
            color = "#059669"  # Verde - adelantado
            estado = "✅ Adelanto"
        else:
            color = "#f59e0b"  # Amarillo - ligera desviación
            estado = "⏳ En rango"
        
        desviaciones_html += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #e5e5e5;">{d.get('fase', 'N/A')}</td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e5e5; text-align: right;">{d.get('planeado', 0):.1f}%</td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e5e5; text-align: right;">{d.get('real', 0):.1f}%</td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e5e5; text-align: right; color: {color}; font-weight: bold;">
                {porcentaje:+.1f}%
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e5e5; text-align: center;">{estado}</td>
        </tr>
        """
    
    # Calcular si hay retrasos críticos
    hay_retrasos_criticos = any(d.get('desviacion_porcentaje', 0) < -20 for d in desviaciones)
    alerta_nivel = "CRÍTICA" if hay_retrasos_criticos else "MODERADA"
    alerta_color = "#dc2626" if hay_retrasos_criticos else "#f59e0b"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 650px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #994B49 0%, #B85C5A 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 24px;">📊 Alerta de Desviación del Cronograma</h1>
            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">DrON Topografía - Monitoreo de Progreso</p>
        </div>
        
        <div style="background: #fff; padding: 30px; border: 1px solid #e5e5e5; border-top: none; border-radius: 0 0 10px 10px;">
            <div style="background: {'#fef2f2' if hay_retrasos_criticos else '#fef3c7'}; border-left: 4px solid {alerta_color}; padding: 15px; margin-bottom: 20px; border-radius: 4px;">
                <strong style="color: {alerta_color};">Alerta {alerta_nivel}</strong>
                <p style="margin: 5px 0 0 0; color: #374151;">
                    Se detectaron desviaciones significativas entre el progreso real y el cronograma planificado.
                </p>
            </div>
            
            <h2 style="color: #994B49; border-bottom: 2px solid #994B49; padding-bottom: 10px; margin-top: 0;">
                📋 Proyecto: {proyecto_nombre}
            </h2>
            
            <p><strong>Fecha del análisis:</strong> {fecha_analisis}</p>
            
            <h3 style="color: #374151; margin-top: 25px;">📈 Resumen de Desviaciones</h3>
            
            <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                <thead>
                    <tr style="background: #f3f4f6;">
                        <th style="padding: 12px; text-align: left; border-bottom: 2px solid #e5e5e5;">Fase</th>
                        <th style="padding: 12px; text-align: right; border-bottom: 2px solid #e5e5e5;">Planeado</th>
                        <th style="padding: 12px; text-align: right; border-bottom: 2px solid #e5e5e5;">Real</th>
                        <th style="padding: 12px; text-align: right; border-bottom: 2px solid #e5e5e5;">Desviación</th>
                        <th style="padding: 12px; text-align: center; border-bottom: 2px solid #e5e5e5;">Estado</th>
                    </tr>
                </thead>
                <tbody>
                    {desviaciones_html}
                </tbody>
            </table>
            
            <h3 style="color: #994B49; margin-top: 25px;">💡 Análisis y Recomendaciones</h3>
            <div style="background: #f9fafb; padding: 15px; border-radius: 8px; border: 1px solid #e5e5e5;">
                <p style="margin: 0; white-space: pre-wrap;">{resumen}</p>
            </div>
            
            <div style="margin-top: 25px; padding: 15px; background: #eff6ff; border-radius: 8px; border: 1px solid #bfdbfe;">
                <h4 style="margin: 0 0 10px 0; color: #1e40af;">🎯 Acciones Recomendadas</h4>
                <ul style="margin: 0; padding-left: 20px; color: #1e40af;">
                    <li>Revisar el avance de las actividades con retraso</li>
                    <li>Verificar disponibilidad de recursos y maquinaria</li>
                    <li>Considerar ajustes al cronograma si es necesario</li>
                    <li>Programar reunión de seguimiento con el equipo</li>
                </ul>
            </div>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e5e5;">
                <p style="color: #6b7280; font-size: 12px; margin: 0;">
                    Esta alerta se generó automáticamente al detectar diferencias mayores al 20% entre el progreso real 
                    y el cronograma planificado. El sistema monitorea continuamente el avance del proyecto.
                </p>
            </div>
        </div>
        
        <div style="text-align: center; padding: 20px; color: #6b7280; font-size: 12px;">
            <p>DrON Topografía © {datetime.now().year}</p>
        </div>
    </body>
    </html>
    """
    
    try:
        params = {
            "from": "DrON Topografía <onboarding@resend.dev>",
            "to": [ADMIN_EMAIL],
            "subject": f"📊 Alerta de Desviación - {proyecto_nombre} ({alerta_nivel})",
            "html": html_content
        }
        
        await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Alerta de desviación enviada a {ADMIN_EMAIL} para proyecto {proyecto_nombre}")
        return True
    except Exception as e:
        logger.error(f"Error enviando alerta de desviación: {e}")
        return False
