"""Servicio de WhatsApp vía Green API para alertas de desviación de obra.

Green API envía mensajes desde el número de WhatsApp del usuario (vinculado por QR)
hacia los contactos destinatarios. No requiere sandbox; el remitente es el usuario.

Docs: https://greenapi.com/en/docs/api/sending/SendMessage/
"""
import logging
import os
from typing import List

import httpx

logger = logging.getLogger(__name__)

GREEN_HOST = (os.environ.get("GREEN_API_HOST") or "").rstrip("/")
GREEN_INSTANCE = os.environ.get("GREEN_API_INSTANCE_ID", "")
GREEN_TOKEN = os.environ.get("GREEN_API_TOKEN", "")

_TIMEOUT = 20.0  # segundos


def is_configured() -> bool:
    return bool(GREEN_HOST and GREEN_INSTANCE and GREEN_TOKEN)


def _chat_id(number: str) -> str:
    """Convierte un número (E.164 o local mexicano) al formato chatId de WhatsApp.

    - "+5213319906249" → "5213319906249@c.us"
    - "3319906249"     → "5213319906249@c.us" (default +52 MX)
    - "+1415..."       → "1415...@c.us"
    """
    n = (number or "").strip()
    if not n:
        return ""
    if n.endswith("@c.us") or n.endswith("@g.us"):
        return n
    digits = "".join(ch for ch in n if ch.isdigit())
    if not digits:
        return ""
    # Si tiene 10 dígitos y no comienza con código de país, asumimos México (+52)
    if len(digits) == 10:
        digits = f"52{digits}"
    return f"{digits}@c.us"


def _check_url() -> str:
    return f"{GREEN_HOST}/waInstance{GREEN_INSTANCE}/checkWhatsapp/{GREEN_TOKEN}"


def _resolve_mx_chat_id(digits: str) -> str:
    """Para números mexicanos prueba ambos formatos vía checkWhatsapp:
    - 52XXXXXXXXXX (formato nuevo)
    - 521XXXXXXXXXX (formato viejo, con el "1" de celular)
    Devuelve el primero que exista en WhatsApp, o "" si ninguno.
    """
    candidatos = []
    if digits.startswith("521") and len(digits) == 13:
        candidatos = [digits, f"52{digits[3:]}"]
    elif digits.startswith("52") and len(digits) == 12:
        candidatos = [digits, f"521{digits[2:]}"]
    else:
        return ""
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            for cand in candidatos:
                r = client.post(_check_url(), json={"phoneNumber": int(cand)})
                if r.status_code == 200:
                    data = r.json() or {}
                    if data.get("existsWhatsapp"):
                        return f"{cand}@c.us"
    except Exception as e:
        logger.warning(f"checkWhatsapp falló: {e}")
    return ""


def _send_message_url() -> str:
    return f"{GREEN_HOST}/waInstance{GREEN_INSTANCE}/sendMessage/{GREEN_TOKEN}"


def _state_url() -> str:
    return f"{GREEN_HOST}/waInstance{GREEN_INSTANCE}/getStateInstance/{GREEN_TOKEN}"


def enviar_whatsapp(to: str, body: str) -> dict:
    """Envía un mensaje individual vía Green API.

    Para números mexicanos resuelve automáticamente el formato correcto
    (52XXX vs 521XXX) usando checkWhatsapp.

    Returns: {success, message_id, error}
    """
    if not is_configured():
        return {"success": False, "error": "Green API no está configurado"}
    chat = _chat_id(to)
    if not chat:
        return {"success": False, "error": "Número destino inválido"}

    # Para MX: confirmar/corregir formato (521 vs 52) usando checkWhatsapp
    digits_only = chat.split("@")[0]
    if digits_only.startswith("52") and len(digits_only) in (12, 13):
        resolved = _resolve_mx_chat_id(digits_only)
        if resolved:
            chat = resolved
        elif resolved == "":
            # checkWhatsapp explícitamente dijo que no existe en ninguna variante
            # Intentamos enviar con lo que tenemos, pero advertimos en logs.
            logger.warning(f"checkWhatsapp: número {digits_only} no parece estar en WhatsApp")

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.post(
                _send_message_url(),
                json={"chatId": chat, "message": body[:4000]},
            )
            data = {}
            try:
                data = r.json()
            except Exception:
                data = {"raw": r.text}
            if r.status_code == 200 and data.get("idMessage"):
                return {"success": True, "message_id": data["idMessage"], "chat_id": chat}
            return {
                "success": False,
                "error": f"HTTP {r.status_code} {data}",
                "status_code": r.status_code,
                "chat_id": chat,
            }
    except httpx.HTTPError as e:
        logger.error(f"Green API HTTP error enviando a {to}: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Error enviando WhatsApp via Green API: {e}")
        return {"success": False, "error": str(e)}


def enviar_a_lista(destinatarios: List[dict], body: str) -> List[dict]:
    """Envía el mismo mensaje a una lista de directores [{nombre, whatsapp}].

    Personaliza el saludo con el primer nombre del director.
    """
    resultados = []
    for d in destinatarios:
        numero = d.get("whatsapp") or d.get("telefono")
        nombre = d.get("nombre", "")
        if not numero:
            continue
        cuerpo = f"Hola {nombre.split()[0]},\n\n{body}" if nombre else body
        res = enviar_whatsapp(numero, cuerpo)
        res["destinatario"] = nombre
        res["numero"] = numero
        resultados.append(res)
    return resultados


def get_state_instance() -> dict:
    """Consulta el estado de la instancia (authorized / notAuthorized / ...)."""
    if not is_configured():
        return {"configured": False, "state": "not_configured"}
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.get(_state_url())
            if r.status_code == 200:
                data = r.json() or {}
                return {
                    "configured": True,
                    "state": data.get("stateInstance", "unknown"),
                    "raw": data,
                }
            return {
                "configured": True,
                "state": "error",
                "error": f"HTTP {r.status_code}",
                "raw": r.text[:300],
            }
    except Exception as e:
        return {"configured": True, "state": "error", "error": str(e)}
