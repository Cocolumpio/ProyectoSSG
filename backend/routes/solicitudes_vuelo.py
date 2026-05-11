"""Rutas de Solicitudes de Vuelo - DrON Topografía"""
import os
import asyncio
import logging
from typing import Optional, List
from datetime import datetime, timezone

import resend
import uuid
from jose import jwt
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from core.config import get_db, ADMIN_EMAIL, SECRET_KEY, ALGORITHM, get_current_admin
from models.schemas import SolicitudVuelo, SolicitudVueloCreate, SolicitudVueloUpdate
from services.helpers import generar_google_calendar_link
from services.email import enviar_notificacion_solicitud_vuelo, enviar_actualizacion_solicitud
from services.notifications import crear_notificacion_sistema

db = get_db()
router = APIRouter(prefix="/api")

# --- Solicitudes de Vuelo ---
@router.post("/solicitudes-vuelo", response_model=dict)
async def crear_solicitud_vuelo(solicitud: SolicitudVueloCreate, credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    """Crear una solicitud de vuelo y enviar notificación por email"""
    
    # Obtener info del cliente si está autenticado
    cliente_id = None
    cliente_email = None
    cliente_nombre = None
    
    if credentials:
        try:
            token = credentials.credentials
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                user = await db.usuarios.find_one({"id": user_id}, {"_id": 0})
                if user:
                    cliente_id = user["id"]
                    cliente_email = user["email"]
                    cliente_nombre = user["nombre"]
        except Exception:
            pass  # Si hay error con el token, continuar sin datos de cliente
    
    # Crear la solicitud
    nueva_solicitud = SolicitudVuelo(
        nombre_proyecto=solicitud.nombre_proyecto,
        fecha_inicio_proyecto=solicitud.fecha_inicio_proyecto,
        fecha_fin_proyecto=solicitud.fecha_fin_proyecto,
        fecha_vuelo_deseada=solicitud.fecha_vuelo_deseada,
        hora_preferencia=solicitud.hora_preferencia,
        notas=solicitud.notas,
        cliente_id=cliente_id,
        cliente_email=cliente_email,
        cliente_nombre=cliente_nombre
    )
    
    solicitud_dict = nueva_solicitud.model_dump()
    solicitud_dict['created_at'] = solicitud_dict['created_at'].isoformat()
    
    # Guardar en base de datos
    await db.solicitudes_vuelo.insert_one(solicitud_dict)
    
    # Generar link de Google Calendar
    titulo_evento = f"🚁 Vuelo DrON - {solicitud.nombre_proyecto}"
    descripcion_evento = f"""Solicitud de vuelo de dron

Proyecto: {solicitud.nombre_proyecto}
Fecha del proyecto: {solicitud.fecha_inicio_proyecto} al {solicitud.fecha_fin_proyecto}
Fecha solicitada: {solicitud.fecha_vuelo_deseada}
Hora preferida: {solicitud.hora_preferencia or 'Sin preferencia'}

Notas del cliente:
{solicitud.notas or 'Sin notas adicionales'}
"""
    
    google_calendar_link = generar_google_calendar_link(
        titulo=titulo_evento,
        fecha=solicitud.fecha_vuelo_deseada,
        hora=solicitud.hora_preferencia,
        descripcion=descripcion_evento
    )
    
    # Construir email HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
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
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; font-weight: bold;">{solicitud.nombre_proyecto}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; color: #6b7280;">Fecha Inicio:</td>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{solicitud.fecha_inicio_proyecto}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; color: #6b7280;">Fecha Fin:</td>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{solicitud.fecha_fin_proyecto}</td>
                </tr>
            </table>
            
            <h2 style="color: #994B49;">📅 Fecha Solicitada para el Vuelo</h2>
            
            <div style="background-color: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 15px; margin-bottom: 20px;">
                <p style="margin: 0; font-size: 18px; font-weight: bold; color: #92400e;">
                    {solicitud.fecha_vuelo_deseada}
                    {f' a las {solicitud.hora_preferencia}' if solicitud.hora_preferencia else ''}
                </p>
            </div>
            
            {f'''
            <h3 style="color: #374151;">📝 Notas del Cliente:</h3>
            <div style="background-color: #f3f4f6; border-radius: 8px; padding: 15px; margin-bottom: 20px;">
                <p style="margin: 0; color: #4b5563;">{solicitud.notas}</p>
            </div>
            ''' if solicitud.notas else ''}
            
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
    
    # Enviar email
    try:
        params = {
            "from": "DrON Topografía <onboarding@resend.dev>",
            "to": [ADMIN_EMAIL],
            "subject": f"🚁 Nueva Solicitud de Vuelo - {solicitud.nombre_proyecto}",
            "html": html_content
        }
        
        email_result = await asyncio.to_thread(resend.Emails.send, params)
        logging.info(f"Email enviado: {email_result}")
        
        return {
            "status": "success",
            "message": "Solicitud de vuelo creada y notificación enviada",
            "solicitud_id": nueva_solicitud.id,
            "email_sent": True
        }
    except Exception as e:
        logging.error(f"Error enviando email: {e}")
        # Aún así guardamos la solicitud
        return {
            "status": "partial",
            "message": "Solicitud creada pero hubo un error al enviar el email",
            "solicitud_id": nueva_solicitud.id,
            "email_sent": False,
            "error": str(e)
        }

@router.get("/solicitudes-vuelo")
async def listar_solicitudes_vuelo(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    """Listar solicitudes de vuelo - Admin ve todas, Cliente ve solo las suyas"""
    user = None
    if credentials:
        try:
            token = credentials.credentials
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                user = await db.usuarios.find_one({"id": user_id}, {"_id": 0})
        except Exception:
            pass
    
    # Si es admin o no hay usuario, mostrar todas
    if not user or user.get("rol") == "admin":
        solicitudes = await db.solicitudes_vuelo.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    else:
        # Cliente solo ve sus solicitudes
        solicitudes = await db.solicitudes_vuelo.find(
            {"cliente_id": user["id"]}, 
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
    
    return solicitudes

@router.put("/solicitudes-vuelo/{solicitud_id}/estado")
async def actualizar_estado_solicitud(solicitud_id: str, update_data: SolicitudVueloUpdate, current_user: dict = Depends(get_current_admin)):
    """Actualizar el estado de una solicitud de vuelo (solo admin) y notificar al cliente"""
    estados_validos = ["pendiente", "confirmado", "completado", "cancelado"]
    if update_data.estado not in estados_validos:
        raise HTTPException(status_code=400, detail=f"Estado inválido. Debe ser uno de: {estados_validos}")
    
    # Obtener la solicitud actual
    solicitud = await db.solicitudes_vuelo.find_one({"id": solicitud_id}, {"_id": 0})
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
    # Actualizar estado y comentario
    update_fields = {
        "estado": update_data.estado,
        "fecha_respuesta": datetime.now(timezone.utc).isoformat()
    }
    if update_data.comentario_admin:
        update_fields["comentario_admin"] = update_data.comentario_admin
    
    await db.solicitudes_vuelo.update_one(
        {"id": solicitud_id},
        {"$set": update_fields}
    )
    
    # Enviar notificación por email al cliente si tiene email
    cliente_email = solicitud.get("cliente_email")
    if cliente_email and update_data.estado in ["confirmado", "cancelado"]:
        try:
            estado_texto = "CONFIRMADO ✅" if update_data.estado == "confirmado" else "CANCELADO ❌"
            estado_color = "#059669" if update_data.estado == "confirmado" else "#DC2626"
            
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
                    
                    <p>Tu solicitud de vuelo para el proyecto <strong>{solicitud.get('nombre_proyecto')}</strong> ha sido <strong style="color: {estado_color};">{update_data.estado}</strong>.</p>
                    
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
                    
                    {f'<div style="background-color: #f3f4f6; border-radius: 8px; padding: 15px; margin: 20px 0;"><strong>Comentario del administrador:</strong><p style="margin: 10px 0 0 0;">{update_data.comentario_admin}</p></div>' if update_data.comentario_admin else ''}
                    
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
            
            params = {
                "from": "DrON Topografía <onboarding@resend.dev>",
                "to": [cliente_email],
                "subject": f"🚁 Tu solicitud ha sido {update_data.estado} - {solicitud.get('nombre_proyecto')}",
                "html": html_content
            }
            
            await asyncio.to_thread(resend.Emails.send, params)
            logging.info(f"Email de notificación enviado a {cliente_email}")
        except Exception as e:
            logging.error(f"Error enviando email de notificación: {e}")
    
    return {"message": "Estado actualizado", "estado": update_data.estado, "notificacion_enviada": bool(cliente_email)}

