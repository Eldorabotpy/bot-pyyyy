"""Helpers for optional Azure Translator translations in the global game chat."""

from functools import lru_cache
import json
import logging
import os
from queue import Full, Queue
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlencode


IDIOMAS_CHAT = {"pt": "Português (Brasil)", "es": "Español", "en": "English"}
LIMITE_CARACTERES_TRADUCAO = 500
_FILA_TRADUCAO = Queue(maxsize=12)
_TRAVA_TRADUTOR = Lock()
_TRADUTOR_ATIVO = False
_LOGGER = logging.getLogger(__name__)
AZURE_TRANSLATOR_ENDPOINT = "https://api.cognitive.microsofttranslator.com/translate"


def normalizar_idioma_chat(valor):
    idioma = str(valor or "pt").strip().lower().replace("_", "-")
    if idioma in {"pt-br", "pt-pt", "pb"}:
        return "pt"
    return idioma if idioma in IDIOMAS_CHAT else "pt"


def obter_configuracao_tradutor():
    chave = str(os.getenv("ELDORA_AZURE_TRANSLATOR_KEY", "")).strip()
    regiao = str(os.getenv("ELDORA_AZURE_TRANSLATOR_REGION", "")).strip()
    return chave, regiao


def tradutor_chat_disponivel():
    chave, _regiao = obter_configuracao_tradutor()
    return bool(chave)


def texto_pode_ser_traduzido(texto):
    return isinstance(texto, str) and 0 < len(texto) <= LIMITE_CARACTERES_TRADUCAO


@lru_cache(maxsize=512)
def _traduzir_em_cache(chave, regiao, texto, idioma_destino):
    if not texto or len(texto) > LIMITE_CARACTERES_TRADUCAO:
        return None

    query = urlencode({"api-version": "3.0", "to": idioma_destino})
    payload = json.dumps([{"Text": texto}]).encode("utf-8")
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Ocp-Apim-Subscription-Key": chave,
    }
    if regiao:
        headers["Ocp-Apim-Subscription-Region"] = regiao
    request = Request(
        f"{AZURE_TRANSLATOR_ENDPOINT}?{query}",
        data=payload,
        headers=headers,
        method="POST",
    )

    try:
        with urlopen(request, timeout=4) as response:
            resultado = json.loads(response.read().decode("utf-8"))
        if not isinstance(resultado, list) or not resultado:
            return None
        traducoes = resultado[0].get("translations")
        if not isinstance(traducoes, list) or not traducoes:
            return None
        traduzido = traducoes[0].get("text")
        if not isinstance(traduzido, str) or not traduzido.strip():
            return None
        return traduzido.strip()
    except HTTPError as exc:
        _LOGGER.warning("Azure Translator respondeu HTTP %s", exc.code)
        return None
    except (URLError, TimeoutError, OSError, ValueError, TypeError):
        return None


def _processar_fila_traducao(socketio):
    while True:
        id_mensagem, texto, destinatarios_por_idioma = _FILA_TRADUCAO.get()
        chave, regiao = obter_configuracao_tradutor()
        try:
            for idioma_destino, destinatarios in destinatarios_por_idioma.items():
                texto_traduzido = _traduzir_em_cache(
                    chave,
                    regiao,
                    texto,
                    idioma_destino,
                )
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
    if not tradutor_chat_disponivel():
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
