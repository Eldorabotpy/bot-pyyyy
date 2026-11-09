"""Helpers for optional MyMemory translations in the global game chat."""

from datetime import date
from functools import lru_cache
from html import unescape
import json
import logging
from queue import Full, Queue
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


IDIOMAS_CHAT = {"pt": "Português (Brasil)", "es": "Español", "en": "English"}
LIMITE_CARACTERES_TRADUCAO = 500
LIMITE_DIARIO_CARACTERES = 4500
MYMEMORY_ENDPOINT = "https://api.mymemory.translated.net/get"
_FILA_TRADUCAO = Queue(maxsize=12)
_TRAVA_TRADUTOR = Lock()
_TRAVA_COTA_DIARIA = Lock()
_TRADUTOR_ATIVO = False
_DIA_COTA = None
_USO_COTA_DIARIA = 0
_LOGGER = logging.getLogger(__name__)


def normalizar_idioma_chat(valor):
    idioma = str(valor or "pt").strip().lower().replace("_", "-")
    if idioma in {"pt-br", "pt-pt", "pb"}:
        return "pt"
    return idioma if idioma in IDIOMAS_CHAT else "pt"


def tradutor_chat_disponivel():
    return True


def texto_pode_ser_traduzido(texto):
    return (
        isinstance(texto, str)
        and 0 < len(texto) <= LIMITE_CARACTERES_TRADUCAO
        and len(texto.encode("utf-8")) <= LIMITE_CARACTERES_TRADUCAO
    )


def _reservar_cota_diaria(texto, dia):
    global _DIA_COTA, _USO_COTA_DIARIA
    with _TRAVA_COTA_DIARIA:
        if _DIA_COTA != dia:
            _DIA_COTA = dia
            _USO_COTA_DIARIA = 0
        tamanho = len(texto)
        if _USO_COTA_DIARIA + tamanho > LIMITE_DIARIO_CARACTERES:
            return False
        _USO_COTA_DIARIA += tamanho
        return True


@lru_cache(maxsize=512)
def _traduzir_em_cache(texto, idioma_origem, idioma_destino, dia):
    if not texto_pode_ser_traduzido(texto):
        return None
    if idioma_origem == idioma_destino:
        return texto
    if not _reservar_cota_diaria(texto, dia):
        return None

    query = urlencode({
        "q": texto,
        "langpair": f"{idioma_origem}|{idioma_destino}",
        "mt": "1",
    })
    request = Request(
        f"{MYMEMORY_ENDPOINT}?{query}",
        headers={"User-Agent": "EldoraChat/1.0"},
    )

    try:
        with urlopen(request, timeout=4) as response:
            resultado = json.loads(response.read().decode("utf-8"))
        if not isinstance(resultado, dict) or resultado.get("responseStatus") != 200:
            return None
        dados_traducao = resultado.get("responseData")
        if not isinstance(dados_traducao, dict):
            return None
        traduzido = dados_traducao.get("translatedText")
        if not isinstance(traduzido, str) or not traduzido.strip():
            return None
        return unescape(traduzido.strip())
    except HTTPError as exc:
        _LOGGER.warning("MyMemory respondeu HTTP %s", exc.code)
        return None
    except (URLError, TimeoutError, OSError, ValueError, TypeError):
        return None


def _processar_fila_traducao(socketio):
    while True:
        (
            id_mensagem,
            texto,
            idioma_origem,
            destinatarios_por_idioma,
        ) = _FILA_TRADUCAO.get()
        dia = date.today().isoformat()
        try:
            for idioma_destino, destinatarios in destinatarios_por_idioma.items():
                texto_traduzido = _traduzir_em_cache(
                    texto,
                    idioma_origem,
                    idioma_destino,
                    dia,
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


def enfileirar_traducao(
    socketio,
    id_mensagem,
    texto,
    idioma_origem,
    destinatarios_por_idioma,
):
    """Queue translations so bursts never start many API requests at once."""
    global _TRADUTOR_ATIVO
    if not tradutor_chat_disponivel() or not texto_pode_ser_traduzido(texto):
        return False

    try:
        _FILA_TRADUCAO.put_nowait((
            str(id_mensagem),
            texto,
            normalizar_idioma_chat(idioma_origem),
            dict(destinatarios_por_idioma or {}),
        ))
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
