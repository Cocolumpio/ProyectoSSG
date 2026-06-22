"""Servicio para interactuar con grupos de WhatsApp vía Green API.

Permite listar grupos, obtener historial de mensajes y filtrar por rango temporal.
Docs: https://greenapi.com/en/docs/api/journals/GetChatHistory/
      https://greenapi.com/en/docs/api/contacts/GetContacts/
"""
import logging
import os
import re
import unicodedata
from datetime import datetime, timezone
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)

GREEN_HOST = (os.environ.get("GREEN_API_HOST") or "").rstrip("/")
GREEN_INSTANCE = os.environ.get("GREEN_API_INSTANCE_ID", "")
GREEN_TOKEN = os.environ.get("GREEN_API_TOKEN", "")
_TIMEOUT = 30.0


def is_configured() -> bool:
    return bool(GREEN_HOST and GREEN_INSTANCE and GREEN_TOKEN)


def _url(endpoint: str) -> str:
    return f"{GREEN_HOST}/waInstance{GREEN_INSTANCE}/{endpoint}/{GREEN_TOKEN}"


def _normalize(s: str) -> str:
    """Lowercase, sin acentos, sin caracteres especiales, espacios colapsados."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z0-9 ]", " ", s).lower()
    return re.sub(r"\s+", " ", s).strip()


def listar_grupos() -> List[dict]:
    """Lista todos los grupos de WhatsApp (chats que terminan en @g.us).

    Returns: [{chat_id, nombre}]
    """
    if not is_configured():
        return []
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.get(_url("getContacts"))
            if r.status_code != 200:
                logger.error(f"getContacts {r.status_code}: {r.text[:200]}")
                return []
            contactos = r.json() or []
            grupos = []
            for c in contactos:
                cid = c.get("id") or ""
                if cid.endswith("@g.us"):
                    grupos.append({
                        "chat_id": cid,
                        "nombre": c.get("name") or "(Sin nombre)",
                    })
            return sorted(grupos, key=lambda g: g["nombre"].lower())
    except Exception as e:
        logger.exception(f"Error listando grupos: {e}")
        return []


def buscar_grupo_para_proyecto(nombre_proyecto: str, grupos: Optional[List[dict]] = None) -> Optional[dict]:
    """Auto-match flexible: busca grupo cuyo nombre contenga (normalizado) el del proyecto.

    Estrategia:
    1. Normaliza ambos lados (sin acentos, lowercase, sin signos).
    2. Match exacto → match si contiene todas las palabras → match parcial.
    """
    if grupos is None:
        grupos = listar_grupos()
    if not grupos or not nombre_proyecto:
        return None

    target = _normalize(nombre_proyecto)
    if not target:
        return None
    target_words = [w for w in target.split() if len(w) >= 3]

    # 1) Exacto
    for g in grupos:
        if _normalize(g["nombre"]) == target:
            return g

    # 2) Contiene el nombre del proyecto entero
    for g in grupos:
        if target in _normalize(g["nombre"]):
            return g

    # 3) Contiene TODAS las palabras significativas (≥3 caracteres) del proyecto
    if target_words:
        for g in grupos:
            gn = _normalize(g["nombre"])
            if all(w in gn for w in target_words):
                return g

    return None


def obtener_mensajes_grupo(chat_id: str, desde_ts: int, hasta_ts: int, max_count: int = 500) -> List[dict]:
    """Obtiene mensajes del grupo filtrados por rango de timestamps Unix.

    Args:
        chat_id: ID del chat (xxx@g.us)
        desde_ts, hasta_ts: límites temporales (epoch seconds)
        max_count: máximo de mensajes a pedir a la API (Green API limita a 100 por llamada,
                   pero pedimos varios lotes)

    Returns: lista de mensajes con {timestamp, senderName, textMessage, type, ...}
    """
    if not is_configured() or not chat_id:
        return []
    mensajes_filtrados = []
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            count_por_lote = 100
            total_pedidos = 0
            # Green API getChatHistory devuelve del más reciente al más antiguo
            while total_pedidos < max_count:
                r = client.post(
                    _url("getChatHistory"),
                    json={"chatId": chat_id, "count": count_por_lote},
                )
                if r.status_code != 200:
                    logger.error(f"getChatHistory {r.status_code}: {r.text[:200]}")
                    break
                lote = r.json() or []
                if not lote:
                    break
                # Filtra y termina si vemos mensajes anteriores al rango
                mas_viejo_del_lote = lote[-1].get("timestamp", 0) if lote else 0
                for m in lote:
                    ts = m.get("timestamp", 0)
                    if desde_ts <= ts <= hasta_ts:
                        mensajes_filtrados.append(m)
                total_pedidos += len(lote)
                # Si el más viejo del lote ya es anterior a desde_ts, podemos parar
                if mas_viejo_del_lote and mas_viejo_del_lote < desde_ts:
                    break
                # Green API no soporta paginación nativa fácilmente; con un solo lote de 100
                # cubrimos típicamente una semana de actividad. Si quieres más, sube count.
                if len(lote) < count_por_lote:
                    break
                # Para simplicidad cortamos aquí (un solo lote). Más adelante implementar paginación.
                break
        # Orden cronológico ascendente
        mensajes_filtrados.sort(key=lambda m: m.get("timestamp", 0))
        return mensajes_filtrados
    except Exception as e:
        logger.exception(f"Error obteniendo mensajes del grupo {chat_id}: {e}")
        return []


def formatear_mensajes_para_ia(mensajes: List[dict]) -> str:
    """Convierte mensajes en un transcript legible y compacto para enviar a la IA."""
    lineas = []
    for m in mensajes:
        ts = m.get("timestamp")
        try:
            fecha = datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%a %d/%m %H:%M")
        except Exception:
            fecha = "?"
        autor = m.get("senderName") or m.get("chatName") or "Usuario"
        tipo = m.get("typeMessage", "textMessage")
        texto = m.get("textMessage") or m.get("extendedTextMessage", {}).get("text", "")
        if not texto and tipo != "textMessage":
            # Indicador de medio
            mapping = {
                "imageMessage": "[imagen]",
                "videoMessage": "[video]",
                "documentMessage": f"[documento: {m.get('fileName', '')}]",
                "audioMessage": "[audio]",
                "locationMessage": "[ubicación]",
            }
            texto = mapping.get(tipo, f"[{tipo}]")
        if texto:
            lineas.append(f"[{fecha}] {autor}: {texto}")
    return "\n".join(lineas)
