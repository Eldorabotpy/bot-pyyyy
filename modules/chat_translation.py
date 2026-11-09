"""Helpers for optional MyMemory translations in the global game chat."""

from datetime import date
from functools import lru_cache
from html import unescape
import json
import logging
import re
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

_MARCADORES_IDIOMA = {
    "pt": {
        "não": 4, "nao": 4, "você": 4, "vocês": 4, "oi": 4,
        "olá": 4, "obrigado": 4, "obrigada": 4, "valeu": 4,
        "tá": 3, "pra": 3, "também": 3, "muito": 3, "muita": 3,
        "estou": 3, "estamos": 3, "bom": 2, "boa": 2, "dia": 2,
        "noite": 2, "tudo": 2, "bem": 2, "agora": 2, "depois": 2,
        "sim": 2, "jogo": 2, "amigo": 1, "amiga": 1,
    },
    "es": {
        "hola": 4, "gracias": 4, "adiós": 4, "adios": 4, "tú": 4,
        "ustedes": 4, "vosotros": 4, "vosotras": 4, "estoy": 3,
        "estás": 3, "estamos": 3, "muy": 3, "pero": 3, "también": 3,
        "qué": 3, "cómo": 3, "dónde": 3, "buenos": 3, "buenas": 3,
        "sí": 3, "ahora": 2, "juego": 2, "amigo": 1, "amiga": 1,
    },
    "en": {
        "you": 5, "you're": 5, "your": 4, "the": 4, "and": 4,
        "hello": 4, "thanks": 4, "thank": 4, "please": 4,
        "what": 3, "where": 3, "when": 3, "why": 3, "how": 3,
        "is": 2, "are": 2, "am": 2, "was": 2, "were": 2,
        "have": 2, "has": 2, "with": 2, "good": 2, "morning": 3,
        "night": 3, "this": 2, "that": 2, "game": 2, "yes": 2,
        "no": 1, "hi": 2, "hey": 2, "i": 1, "me": 1, "my": 1,
    },
}


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


def detectar_idioma_mensagem(texto, idioma_selecionado="pt"):
    """Detect common PT/ES/EN chat text; use the preference for ambiguous text."""
    idioma_padrao = normalizar_idioma_chat(idioma_selecionado)
    texto_normalizado = str(texto or "").lower()
    palavras = re.findall(r"[a-záéíóúüñãõâêôç]+", texto_normalizado)
    if not palavras:
        return idioma_padrao

    pontuacoes = {idioma: 0 for idioma in IDIOMAS_CHAT}
    for palavra in palavras:
        for idioma, marcadores in _MARCADORES_IDIOMA.items():
            pontuacoes[idioma] += marcadores.get(palavra, 0)

    if any(caractere in texto_normalizado for caractere in ("ñ", "¿", "¡")):
        pontuacoes["es"] += 4
    if any(caractere in texto_normalizado for caractere in ("ã", "õ", "ç")):
        pontuacoes["pt"] += 4

    maior = max(pontuacoes.values())
    vencedores = [idioma for idioma, pontos in pontuacoes.items() if pontos == maior]
    if maior < 3 or len(vencedores) != 1:
        return idioma_padrao
    segundo_maior = sorted(pontuacoes.values(), reverse=True)[1]
    if maior - segundo_maior < 2:
        return idioma_padrao
    return vencedores[0]


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
