"""Google Calendar OAuth + integración para programación automática de vuelos.

Funcionalidad:
  • OAuth 2.0 — connect/disconnect cuenta Google del admin
  • Tokens guardados por usuario en MongoDB (collection google_tokens)
  • Generación automática de eventos a partir del programa_semanal del proyecto
"""
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

import requests
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from core.config import get_current_admin, get_current_user, get_db

logger = logging.getLogger(__name__)
db = get_db()
router = APIRouter(prefix="/api")

CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
SCOPES = ["https://www.googleapis.com/auth/calendar.events", "openid", "email", "profile"]

BACKEND_BASE_URL = (
    os.environ.get("BACKEND_BASE_URL")
    or os.environ.get("REACT_APP_BACKEND_URL")
    or ""
)


def _redirect_uri() -> str:
    if not BACKEND_BASE_URL:
        # fallback al hostname del request — más adelante
        return ""
    return BACKEND_BASE_URL.rstrip("/") + "/api/oauth/calendar/callback"


# --------------------------------------------------------------------------
# OAuth Flow
# --------------------------------------------------------------------------

@router.get("/oauth/calendar/login")
async def oauth_login(
    base_url: str = Query(..., description="Base URL del backend para redirect_uri"),
    current_user: dict = Depends(get_current_admin),
):
    """Devuelve URL de autorización Google. El frontend redirige al usuario allí."""
    if not CLIENT_ID or not CLIENT_SECRET:
        raise HTTPException(500, "Google OAuth no está configurado en el servidor")
    redirect_uri = base_url.rstrip("/") + "/api/oauth/calendar/callback"
    flow = Flow.from_client_config({
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }, scopes=SCOPES, redirect_uri=redirect_uri)
    # State = user_id del admin para vincular el callback con el usuario
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=current_user["id"],
        include_granted_scopes="true",
    )
    return {"authorization_url": auth_url}


@router.get("/oauth/calendar/callback")
async def oauth_callback(request: Request, code: str, state: str = ""):
    """Google redirige aquí tras login. Intercambiamos code → tokens."""
    if not CLIENT_ID or not CLIENT_SECRET:
        raise HTTPException(500, "Google OAuth no está configurado")
    if not state:
        raise HTTPException(400, "state (user_id) faltante")

    # Construir el redirect_uri exactamente como Google lo recibió: a partir del
    # request actual. Importante: si el frontend está detrás de un proxy/ingress
    # debemos respetar X-Forwarded-Proto y X-Forwarded-Host.
    forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    redirect_uri = f"{forwarded_proto}://{forwarded_host}/api/oauth/calendar/callback"

    token_resp = requests.post("https://oauth2.googleapis.com/token", data={
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }, timeout=15).json()

    if "access_token" not in token_resp:
        logger.error(f"Error en intercambio de token (redirect_uri={redirect_uri}): {token_resp}")
        raise HTTPException(400, f"OAuth error: {token_resp.get('error_description') or token_resp.get('error') or 'unknown'}")

    # Obtener email del usuario de Google
    user_info = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {token_resp['access_token']}"},
        timeout=10,
    ).json()
    google_email = user_info.get("email") or ""

    # Guardar tokens en collection google_tokens, vinculados al user_id (state)
    await db.google_tokens.update_one(
        {"user_id": state},
        {"$set": {
            "user_id": state,
            "google_email": google_email,
            "access_token": token_resp.get("access_token"),
            "refresh_token": token_resp.get("refresh_token"),
            "expires_in": token_resp.get("expires_in"),
            "scope": token_resp.get("scope"),
            "token_type": token_resp.get("token_type"),
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )

    # Redirigir al frontend con un flag de éxito (mismo host del request)
    frontend_base = f"{forwarded_proto}://{forwarded_host}"
    return RedirectResponse(f"{frontend_base}/app?google_calendar=connected")


@router.get("/oauth/calendar/status")
async def oauth_status(current_user: dict = Depends(get_current_user)):
    """Devuelve si el usuario tiene Google Calendar conectado."""
    doc = await db.google_tokens.find_one({"user_id": current_user["id"]}, {"_id": 0})
    if not doc or not doc.get("refresh_token"):
        return {"connected": False}
    return {
        "connected": True,
        "google_email": doc.get("google_email"),
        "connected_at": doc.get("connected_at"),
    }


@router.delete("/oauth/calendar/disconnect")
async def oauth_disconnect(current_user: dict = Depends(get_current_admin)):
    """Revoca el token y borra del DB."""
    doc = await db.google_tokens.find_one({"user_id": current_user["id"]})
    if doc and doc.get("access_token"):
        try:
            requests.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": doc["access_token"]},
                timeout=8,
            )
        except Exception as e:
            logger.warning(f"Error revocando token: {e}")
    await db.google_tokens.delete_one({"user_id": current_user["id"]})
    return {"disconnected": True}


# --------------------------------------------------------------------------
# Helper para obtener Credentials válidas
# --------------------------------------------------------------------------

async def _get_user_credentials(user_id: str):
    """Carga tokens de la DB, refresca si vencidos, devuelve Credentials de Google."""
    doc = await db.google_tokens.find_one({"user_id": user_id})
    if not doc or not doc.get("refresh_token"):
        return None

    creds = Credentials(
        token=doc.get("access_token"),
        refresh_token=doc["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=SCOPES,
    )

    if not creds.valid:
        try:
            creds.refresh(GoogleRequest())
            await db.google_tokens.update_one(
                {"user_id": user_id},
                {"$set": {"access_token": creds.token}},
            )
        except Exception as e:
            logger.error(f"Error refrescando token Google: {e}")
            return None

    return creds


# --------------------------------------------------------------------------
# Generación automática de vuelos
# --------------------------------------------------------------------------

def _build_event_body(proyecto: dict, sem: dict, fecha_inicio_obj: datetime, fecha_vuelo: datetime) -> Dict[str, Any]:
    """Construye el body del evento de Google Calendar para un vuelo."""
    proyecto_nombre = proyecto.get("nombre", "Proyecto")
    ubicacion = proyecto.get("direccion") or proyecto.get("ubicacion") or ""
    coords = proyecto.get("coordenadas") or {}

    # Fases activas planeadas esa semana
    fases = []
    if (sem.get("excavacion_m3") or 0) > 0:
        fases.append(f"Excavación: {sem['excavacion_m3']} m³")
    if (sem.get("pilas") or 0) > 0:
        fases.append(f"Pilas: {int(sem['pilas']) if float(sem['pilas']).is_integer() else sem['pilas']}")
    if (sem.get("anclas") or 0) > 0:
        fases.append(f"Anclas: {int(sem['anclas']) if float(sem['anclas']).is_integer() else sem['anclas']}")
    if (sem.get("muros_m2") or 0) > 0:
        fases.append(f"Muros: {sem['muros_m2']} m²")

    actividades = sem.get("actividades") or []
    actividades_txt = "\n".join(f"  • {a.get('descripcion', '')[:120]}" for a in actividades[:6])

    descripcion = (
        f"Vuelo programado para Semana {sem['semana']} del proyecto {proyecto_nombre}.\n\n"
        f"📅 Inicio de la semana: {sem.get('fecha_inicio')}\n"
        f"🏗️ Actividades planeadas:\n  {chr(10).join('• ' + f for f in fases)}\n\n"
        f"📋 Detalle:\n{actividades_txt}\n\n"
        f"🌐 Captura el avance al inicio de esta semana para comparar contra el programa de obra.\n"
        f"— Generado automáticamente por DrON Topografía"
    )

    body: Dict[str, Any] = {
        "summary": f"🚁 Vuelo DrON · {proyecto_nombre} · Sem {sem['semana']}",
        "description": descripcion,
        "location": ubicacion or (f"{coords.get('lat')},{coords.get('lng')}" if coords else ""),
        # Evento de 1 hora a las 10:00 AM (hora local CDMX/GDL)
        "start": {
            "dateTime": fecha_vuelo.replace(hour=10, minute=0, second=0).isoformat(),
            "timeZone": "America/Mexico_City",
        },
        "end": {
            "dateTime": fecha_vuelo.replace(hour=11, minute=0, second=0).isoformat(),
            "timeZone": "America/Mexico_City",
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 60 * 24},   # 1 día antes
                {"method": "popup", "minutes": 60},        # 1 hora antes
            ],
        },
    }
    return body


def _hoy_local() -> datetime:
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-6)))


@router.post("/proyectos/{proyecto_id}/vuelos/generar")
async def generar_vuelos_calendario(
    proyecto_id: str,
    current_user: dict = Depends(get_current_admin),
):
    """Genera eventos de Google Calendar (vuelos) para CADA semana del programa.

    Regla del usuario:
      • Fecha del vuelo = fecha_inicio de la tarjeta semanal (lunes de esa semana)
      • Evento creado en el calendario "ahora", con la fecha del vuelo programada
      • Se generan TODAS las semanas del programa (incluso pasadas, para historial)
      • Si ya existe un evento para esa semana, se actualiza (no duplica)
    """
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(404, "Proyecto no encontrado")

    programa = proyecto.get("programa_semanal") or []
    if not programa:
        raise HTTPException(400, "Este proyecto no tiene programa semanal cargado")

    creds = await _get_user_credentials(current_user["id"])
    if not creds:
        raise HTTPException(400, "Google Calendar no conectado. Conéctalo primero.")

    service = build("calendar", "v3", credentials=creds, cache_discovery=False)

    # Cargar eventos ya creados para este proyecto (mapping semana → google_event_id)
    existentes = await db.vuelos_calendario.find(
        {"proyecto_id": proyecto_id, "user_id": current_user["id"]},
        {"_id": 0},
    ).to_list(500)
    map_existentes = {e["semana"]: e for e in existentes}

    creados = 0
    actualizados = 0
    saltados = 0
    eventos_resultantes: List[Dict[str, Any]] = []

    for sem in programa:
        if not sem.get("fecha_inicio"):
            saltados += 1
            continue
        try:
            fecha_inicio_obj = datetime.fromisoformat(sem["fecha_inicio"])
        except Exception:
            saltados += 1
            continue

        # El vuelo se programa en la fecha_inicio de la tarjeta
        fecha_vuelo = fecha_inicio_obj

        body = _build_event_body(proyecto, sem, fecha_inicio_obj, fecha_vuelo)
        num_sem = int(sem["semana"])

        try:
            if num_sem in map_existentes and map_existentes[num_sem].get("google_event_id"):
                event_id = map_existentes[num_sem]["google_event_id"]
                ev = service.events().update(
                    calendarId="primary", eventId=event_id, body=body
                ).execute()
                actualizados += 1
            else:
                ev = service.events().insert(calendarId="primary", body=body).execute()
                creados += 1

            await db.vuelos_calendario.update_one(
                {"proyecto_id": proyecto_id, "user_id": current_user["id"], "semana": num_sem},
                {"$set": {
                    "proyecto_id": proyecto_id,
                    "user_id": current_user["id"],
                    "semana": num_sem,
                    "google_event_id": ev.get("id"),
                    "html_link": ev.get("htmlLink"),
                    "fecha_vuelo": fecha_vuelo.date().isoformat(),
                    "actualizado_en": datetime.now(timezone.utc).isoformat(),
                }},
                upsert=True,
            )
            eventos_resultantes.append({
                "semana": num_sem,
                "fecha_vuelo": fecha_vuelo.date().isoformat(),
                "event_id": ev.get("id"),
                "html_link": ev.get("htmlLink"),
            })
        except Exception as e:
            logger.error(f"Error creando evento semana {num_sem}: {e}")
            saltados += 1

    return {
        "proyecto_id": proyecto_id,
        "total_semanas": len(programa),
        "creados": creados,
        "actualizados": actualizados,
        "saltados": saltados,
        "eventos": eventos_resultantes,
    }


@router.get("/proyectos/{proyecto_id}/vuelos/programados")
async def listar_vuelos_programados(
    proyecto_id: str,
    current_user: dict = Depends(get_current_user),
):
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(404, "Proyecto no encontrado")

    # Cliente solo ve los suyos
    if current_user.get("rol") == "client":
        if current_user["id"] not in (proyecto.get("clientes_asignados") or []):
            raise HTTPException(403, "Sin acceso")

    docs = await db.vuelos_calendario.find(
        {"proyecto_id": proyecto_id}, {"_id": 0}
    ).sort("semana", 1).to_list(500)
    return {"vuelos": docs}


@router.delete("/proyectos/{proyecto_id}/vuelos/{semana}")
async def eliminar_vuelo(
    proyecto_id: str,
    semana: int,
    current_user: dict = Depends(get_current_admin),
):
    """Borra un evento específico del calendario."""
    doc = await db.vuelos_calendario.find_one(
        {"proyecto_id": proyecto_id, "user_id": current_user["id"], "semana": semana}
    )
    if not doc:
        raise HTTPException(404, "Vuelo no encontrado")

    creds = await _get_user_credentials(current_user["id"])
    if creds and doc.get("google_event_id"):
        try:
            service = build("calendar", "v3", credentials=creds, cache_discovery=False)
            service.events().delete(
                calendarId="primary", eventId=doc["google_event_id"]
            ).execute()
        except Exception as e:
            logger.warning(f"Error borrando evento de Google: {e}")

    await db.vuelos_calendario.delete_one(
        {"proyecto_id": proyecto_id, "user_id": current_user["id"], "semana": semana}
    )
    return {"deleted": True}
