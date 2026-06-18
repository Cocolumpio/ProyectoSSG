"""Servicio de WhatsApp vía Twilio para alertas de desviación de obra."""
import logging
import os
from typing import List

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)

TWILIO_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "")


def is_configured() -> bool:
    return bool(TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM)


def _client() -> Client:
    return Client(TWILIO_SID, TWILIO_TOKEN)


def _format_to(number: str) -> str:
    """Asegura el formato whatsapp:+E.164."""
    n = (number or "").strip()
    if not n:
        return ""
    if n.startswith("whatsapp:"):
        return n
    if not n.startswith("+"):
        # Si viene sin +, asumimos México y agregamos +52 si tiene 10 dígitos
        digits = "".join(ch for ch in n if ch.isdigit())
        if len(digits) == 10:
            n = f"+52{digits}"
        elif not digits.startswith("52") and len(digits) > 10:
            n = f"+{digits}"
        else:
            n = f"+{digits}"
    return f"whatsapp:{n}"


def enviar_whatsapp(to: str, body: str) -> dict:
    """Envía un único mensaje. Devuelve {success, sid, error}."""
    if not is_configured():
        return {"success": False, "error": "Twilio no está configurado"}
    if not to:
        return {"success": False, "error": "Número destino vacío"}
    try:
        client = _client()
        msg = client.messages.create(
            from_=TWILIO_FROM,
            to=_format_to(to),
            body=body[:1500],
        )
        return {"success": True, "sid": msg.sid, "status": msg.status}
    except TwilioRestException as e:
        logger.error(f"Twilio error enviando a {to}: {e}")
        return {"success": False, "error": str(e), "code": getattr(e, "code", None)}
    except Exception as e:
        logger.error(f"Error enviando WhatsApp: {e}")
        return {"success": False, "error": str(e)}


def enviar_a_lista(destinatarios: List[dict], body: str) -> List[dict]:
    """Envía el mismo mensaje a una lista de directores [{nombre, whatsapp}].

    Personaliza el saludo con el nombre del director.
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
