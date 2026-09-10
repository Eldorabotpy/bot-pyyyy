# ============================================================
# 📲 MUNDO DE ELDORA - NOTIFICAÇÕES DA LOJA NO TELEGRAM
# ============================================================

import os
import json
import html
import threading

from urllib.parse import urlencode
from urllib.request import Request, urlopen

from config import TELEGRAM_TOKEN


TELEGRAM_ADMIN_CHAT_ID = str(
    os.getenv(
        "TELEGRAM_ADMIN_CHAT_ID",
        ""
    )
).strip()


ADMIN_PANEL_URL = str(
    os.getenv(
        "ADMIN_PANEL_URL",
        ""
    )
).strip()


# ============================================================
# 📤 ENVIO INTERNO
# ============================================================

def _enviar_mensagem_sync(
    texto,
):
    try:

        if not TELEGRAM_TOKEN:
            print(
                "⚠️ [PREMIUM TELEGRAM] "
                "TELEGRAM_TOKEN não configurado."
            )

            return False


        if not TELEGRAM_ADMIN_CHAT_ID:
            print(
                "⚠️ [PREMIUM TELEGRAM] "
                "TELEGRAM_ADMIN_CHAT_ID "
                "não configurado."
            )

            return False


        dados = {
            "chat_id":
                TELEGRAM_ADMIN_CHAT_ID,

            "text":
                texto,

            "parse_mode":
                "HTML",

            "disable_web_page_preview":
                "true",
        }


        # Se você configurar a URL do
        # Painel GM, aparece um botão
        # diretamente na mensagem.
        if ADMIN_PANEL_URL:

            dados["reply_markup"] = (
                json.dumps({
                    "inline_keyboard": [
                        [
                            {
                                "text":
                                    "👑 Abrir Painel GM",

                                "url":
                                    ADMIN_PANEL_URL,
                            }
                        ]
                    ]
                })
            )


        corpo = urlencode(
            dados
        ).encode(
            "utf-8"
        )


        url = (
            "https://api.telegram.org/bot"
            f"{TELEGRAM_TOKEN}"
            "/sendMessage"
        )


        requisicao = Request(
            url,
            data=corpo,
            method="POST",
        )


        with urlopen(
            requisicao,
            timeout=10,
        ) as resposta:

            sucesso = (
                200
                <= resposta.status
                < 300
            )


        if sucesso:
            print(
                "📲 [PREMIUM TELEGRAM] "
                "Notificação enviada."
            )


        return sucesso


    except Exception as erro:

        print(
            "⚠️ [PREMIUM TELEGRAM] "
            "Falha ao enviar notificação: "
            f"{erro}"
        )

        return False


# ============================================================
# 🧵 ENVIA SEM TRAVAR A LOJA
# ============================================================

def _enviar_async(
    texto,
):

    thread = threading.Thread(
        target=
            _enviar_mensagem_sync,

        args=(
            texto,
        ),

        daemon=True,
    )

    thread.start()


# ============================================================
# 💎 NOVO PEDIDO
# ============================================================

def notificar_novo_pedido(
    codigo,
    personagem,
    gemas,
    valor_formatado,
):

    codigo = html.escape(
        str(
            codigo or ""
        )
    )

    personagem = html.escape(
        str(
            personagem
            or "Aventureiro"
        )
    )

    gemas = int(
        gemas or 0
    )

    valor_formatado = html.escape(
        str(
            valor_formatado or ""
        )
    )


    texto = (
        "💎 <b>NOVO PEDIDO NA LOJA DE ELDORA</b>\n\n"

        f"📜 Pedido: <code>{codigo}</code>\n"
        f"👤 Jogador: <b>{personagem}</b>\n"
        f"💎 Pacote: <b>{gemas} Gemas</b>\n"
        f"💵 Valor: <b>{valor_formatado}</b>\n\n"

        "⏳ Status: Aguardando pagamento."
    )


    _enviar_async(
        texto
    )


# ============================================================
# 🚨 COMPROVANTE RECEBIDO
# ============================================================

def notificar_comprovante_recebido(
    codigo,
    personagem,
    gemas,
    valor_formatado,
):

    codigo = html.escape(
        str(
            codigo or ""
        )
    )

    personagem = html.escape(
        str(
            personagem
            or "Aventureiro"
        )
    )

    gemas = int(
        gemas or 0
    )

    valor_formatado = html.escape(
        str(
            valor_formatado or ""
        )
    )


    texto = (
        "🚨 <b>COMPROVANTE PIX RECEBIDO</b>\n\n"

        f"📜 Pedido: <code>{codigo}</code>\n"
        f"👤 Jogador: <b>{personagem}</b>\n"
        f"💎 Gemas: <b>{gemas}</b>\n"
        f"💵 Valor: <b>{valor_formatado}</b>\n\n"

        "🔎 Status: <b>EM ANÁLISE</b>\n\n"

        "👑 Abra o Painel GM para conferir "
        "o comprovante e aprovar ou recusar."
    )


    _enviar_async(
        texto
    )