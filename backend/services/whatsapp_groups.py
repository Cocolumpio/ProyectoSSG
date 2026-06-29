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

    Implementa paginación real con `idMessage` como offset (más histórico).
    """
    if not is_configured() or not chat_id:
        return []
    mensajes_filtrados = []
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            count_por_lote = 100
            total_pedidos = 0
            ultimo_id = None
            while total_pedidos < max_count:
                payload = {"chatId": chat_id, "count": count_por_lote}
                if ultimo_id:
                    payload["idMessage"] = ultimo_id  # paginar hacia mensajes más viejos
                r = client.post(_url("getChatHistory"), json=payload)
                if r.status_code != 200:
                    logger.error(f"getChatHistory {r.status_code}: {r.text[:200]}")
                    break
                lote = r.json() or []
                if not lote:
                    break
                # Filtra dentro del rango
                for m in lote:
                    ts = m.get("timestamp", 0)
                    if desde_ts <= ts <= hasta_ts:
                        mensajes_filtrados.append(m)
                # Si todos los del lote son más viejos que el rango, paramos
                mas_viejo = lote[-1].get("timestamp", 0)
                total_pedidos += len(lote)
                ultimo_id = lote[-1].get("idMessage")
                if not ultimo_id:
                    break
                if mas_viejo and mas_viejo < desde_ts:
                    break
                if len(lote) < count_por_lote:
                    break
        mensajes_filtrados.sort(key=lambda m: m.get("timestamp", 0))
        return mensajes_filtrados
    except Exception as e:
        logger.exception(f"Error obteniendo mensajes del grupo {chat_id}: {e}")
        return []


def obtener_mensajes_grupo_diagnostico(chat_id: str, desde_ts: int, hasta_ts: int) -> dict:
    """Versión con diagnóstico: regresa info de qué devolvió Green API."""
    if not is_configured() or not chat_id:
        return {"filtrados": [], "total_obtenidos": 0, "mas_nuevo_ts": None, "mas_viejo_ts": None, "error": "Sin chat_id o no configurado"}
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.post(_url("getChatHistory"), json={"chatId": chat_id, "count": 100})
            if r.status_code != 200:
                return {"filtrados": [], "total_obtenidos": 0, "mas_nuevo_ts": None, "mas_viejo_ts": None,
                        "error": f"HTTP {r.status_code}: {r.text[:150]}"}
            lote = r.json() or []
            filtrados = [m for m in lote if desde_ts <= m.get("timestamp", 0) <= hasta_ts]
            ts_list = [m.get("timestamp", 0) for m in lote if m.get("timestamp")]
            return {
                "filtrados": sorted(filtrados, key=lambda m: m.get("timestamp", 0)),
                "total_obtenidos": len(lote),
                "mas_nuevo_ts": max(ts_list) if ts_list else None,
                "mas_viejo_ts": min(ts_list) if ts_list else None,
                "error": None,
            }
    except Exception as e:
        return {"filtrados": [], "total_obtenidos": 0, "mas_nuevo_ts": None, "mas_viejo_ts": None, "error": str(e)}


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
