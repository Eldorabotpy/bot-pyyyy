"""Helpers for optional, self-hosted translations in the global game chat."""

from functools import lru_cache
import json
import logging
import os
from queue import Full, Queue
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


IDIOMAS_CHAT = {"pt": "Português (Brasil)", "es": "Español", "en": "English"}
LIMITE_CARACTERES_TRADUCAO = 500
_FILA_TRADUCAO = Queue(maxsize=12)
_TRAVA_TRADUTOR = Lock()
_TRADUTOR_ATIVO = False
_LOGGER = logging.getLogger(__name__)


def normalizar_idioma_chat(valor):
    idioma = str(valor or "pt").strip().lower().replace("_", "-")
    if idioma in {"pt-br", "pt-pt", "pb"}:
        return "pt"
    return idioma if idioma in IDIOMAS_CHAT else "pt"


def obter_url_tradutor():
    return str(os.getenv("ELDORA_CHAT_TRANSLATOR_URL", "")).strip()


def tradutor_chat_disponivel():
    return bool(obter_url_tradutor())


def texto_pode_ser_traduzido(texto):
    return isinstance(texto, str) and 0 < len(texto) <= LIMITE_CARACTERES_TRADUCAO


@lru_cache(maxsize=512)
def _traduzir_em_cache(url, texto, idioma_destino):
    if not texto or len(texto) > LIMITE_CARACTERES_TRADUCAO:
        return None

    payload = json.dumps({
        "q": texto,
        "source": "auto",
        "target": idioma_destino,
        "format": "text",
    }).encode("utf-8")
    request = Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=4) as response:
            resultado = json.loads(response.read().decode("utf-8"))
        if not isinstance(resultado, dict):
            return None
        traduzido = resultado.get("translatedText")
        if not isinstance(traduzido, str) or not traduzido.strip():
            return None
        return traduzido.strip()
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, TypeError):
        return None


def _processar_fila_traducao(socketio):
    while True:
        id_mensagem, texto, destinatarios_por_idioma = _FILA_TRADUCAO.get()
        url = obter_url_tradutor()
        try:
            for idioma_destino, destinatarios in destinatarios_por_idioma.items():
                texto_traduzido = _traduzir_em_cache(url, texto, idioma_destino)
                evento = "chatTraducaoPronta" if texto_traduzido is not None else "chatTraducaoFalhou"
                pacote = {"id": str(id_mensagem), "idioma": idioma_destino}
                if texto_traduzido is not None:
                    pacote["texto"] = texto_traduzido
                for sid in destinatarios:
                    socketio.emit(evento, pacote, to=sid)
        except Exception:
            _LOGGER.exception("Falha ao distribuir tradução do chat")
            for idioma_destino, destinatarios in destinatarios_por_idioma.items():
                for sid in destinatarios:
                    try:
                        socketio.emit(
                            "chatTraducaoFalhou",
                            {"id": str(id_mensagem), "idioma": idioma_destino},
                            to=sid,
                        )
                    except Exception:
                        pass
        finally:
            _FILA_TRADUCAO.task_done()


def enfileirar_traducao(socketio, id_mensagem, texto, destinatarios_por_idioma):
    """Queue translations so bursts never start many model requests at once."""
    global _TRADUTOR_ATIVO
    if not obter_url_tradutor():
        return False

    try:
        _FILA_TRADUCAO.put_nowait((str(id_mensagem), texto, destinatarios_por_idioma))
    except Full:
        for idioma, destinatarios in destinatarios_por_idioma.items():
            for sid in destinatarios:
                socketio.emit(
                    "chatTraducaoFalhou",
                    {"id": str(id_mensagem), "idioma": idioma},
                    to=sid,
                )
        return False

    with _TRAVA_TRADUTOR:
        if not _TRADUTOR_ATIVO:
            _TRADUTOR_ATIVO = True
            socketio.start_background_task(_processar_fila_traducao, socketio)
    return True
