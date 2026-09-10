# ============================================================
# 💎 MUNDO DE ELDORA - PIX DA LOJA PREMIUM
# ============================================================

from __future__ import annotations

import os
import re
import unicodedata
from decimal import Decimal


# ============================================================
# ⚙️ CONFIGURAÇÃO
# ============================================================

PIX_CHAVE = str(
    os.getenv(
        "PIX_CHAVE",
        "",
    )
).strip()


PIX_NOME = str(
    os.getenv(
        "PIX_NOME",
        "",
    )
).strip()


PIX_CIDADE = str(
    os.getenv(
        "PIX_CIDADE",
        "",
    )
).strip()


GUI_PIX = "br.gov.bcb.pix"


# ============================================================
# 🔧 NORMALIZAÇÃO
# ============================================================

def _remover_acentos(
    texto,
):
    texto = str(
        texto or ""
    )


    normalizado = unicodedata.normalize(
        "NFKD",
        texto,
    )


    return "".join(
        caractere
        for caractere in normalizado
        if not unicodedata.combining(
            caractere
        )
    )


def _normalizar_texto_emv(
    texto,
    limite,
):
    texto = _remover_acentos(
        texto
    )


    texto = texto.upper()


    texto = re.sub(
        r"[^A-Z0-9 .\-]",
        "",
        texto,
    )


    texto = re.sub(
        r"\s+",
        " ",
        texto,
    ).strip()


    return texto[
        :int(limite)
    ]


# ============================================================
# 🧾 TXID
# ============================================================

def normalizar_txid(
    codigo_pedido,
):
    txid = str(
        codigo_pedido or ""
    )


    # Pix permite apenas:
    # A-Z
    # a-z
    # 0-9

    txid = re.sub(
        r"[^A-Za-z0-9]",
        "",
        txid,
    )


    txid = txid[:25]


    if not txid:
        return "***"


    return txid


# ============================================================
# 🧱 CAMPO TLV
# ============================================================

def _tlv(
    identificador,
    valor,
):
    valor = str(
        valor
    )


    tamanho = len(
        valor.encode(
            "utf-8"
        )
    )


    if tamanho > 99:
        raise ValueError(
            "Campo Pix excedeu "
            "o tamanho permitido."
        )


    return (
        f"{identificador}"
        f"{tamanho:02d}"
        f"{valor}"
    )


# ============================================================
# 🔐 CRC16
# ============================================================

def _crc16(
    payload,
):
    crc = 0xFFFF


    for byte in payload.encode(
        "utf-8"
    ):

        crc ^= (
            byte << 8
        )


        for _ in range(8):

            if crc & 0x8000:

                crc = (
                    (crc << 1)
                    ^ 0x1021
                ) & 0xFFFF

            else:

                crc = (
                    crc << 1
                ) & 0xFFFF


    return f"{crc:04X}"


# ============================================================
# ✅ VALIDAR CONFIGURAÇÃO
# ============================================================

def validar_configuracao_pix():

    if not PIX_CHAVE:

        return {
            "success": False,
            "error": (
                "PIX_CHAVE não foi "
                "configurada no servidor."
            ),
        }


    if len(
        PIX_CHAVE
    ) > 77:

        return {
            "success": False,
            "error": (
                "A chave Pix configurada "
                "excede o limite permitido."
            ),
        }


    if not PIX_NOME:

        return {
            "success": False,
            "error": (
                "PIX_NOME não foi "
                "configurado no servidor."
            ),
        }


    if not PIX_CIDADE:

        return {
            "success": False,
            "error": (
                "PIX_CIDADE não foi "
                "configurada no servidor."
            ),
        }


    return {
        "success": True,
    }


# ============================================================
# 💰 FORMATAR VALOR
# ============================================================

def _valor_pix(
    valor_centavos,
):
    try:

        centavos = int(
            valor_centavos
        )

    except (
        TypeError,
        ValueError,
    ):

        raise ValueError(
            "Valor do Pix inválido."
        )


    if centavos <= 0:

        raise ValueError(
            "O valor do Pix precisa "
            "ser maior que zero."
        )


    valor = (
        Decimal(
            centavos
        )
        / Decimal(
            100
        )
    )


    return f"{valor:.2f}"


# ============================================================
# 💠 GERAR PIX COPIA E COLA
# ============================================================

def gerar_pix_copia_cola(
    valor_centavos,
    codigo_pedido,
):
    configuracao = (
        validar_configuracao_pix()
    )


    if not configuracao.get(
        "success"
    ):

        return configuracao


    try:

        valor = _valor_pix(
            valor_centavos
        )


        txid = normalizar_txid(
            codigo_pedido
        )


        nome = (
            _normalizar_texto_emv(
                PIX_NOME,
                25,
            )
        )


        cidade = (
            _normalizar_texto_emv(
                PIX_CIDADE,
                15,
            )
        )


        if not nome:

            return {
                "success": False,
                "error": (
                    "Nome Pix inválido."
                ),
            }


        if not cidade:

            return {
                "success": False,
                "error": (
                    "Cidade Pix inválida."
                ),
            }


        # ----------------------------------------------------
        # MERCHANT ACCOUNT INFORMATION
        # ----------------------------------------------------

        conta_pix = (
            _tlv(
                "00",
                GUI_PIX,
            )
            +
            _tlv(
                "01",
                PIX_CHAVE,
            )
        )


        # ----------------------------------------------------
        # ADDITIONAL DATA / TXID
        # ----------------------------------------------------

        dados_adicionais = (
            _tlv(
                "05",
                txid,
            )
        )


        # ----------------------------------------------------
        # PAYLOAD BR CODE
        # ----------------------------------------------------

        payload = ""


        # Payload Format Indicator
        payload += _tlv(
            "00",
            "01",
        )


        # Merchant Account Information
        payload += _tlv(
            "26",
            conta_pix,
        )


        # Merchant Category Code
        payload += _tlv(
            "52",
            "0000",
        )


        # BRL
        payload += _tlv(
            "53",
            "986",
        )


        # Valor da compra
        payload += _tlv(
            "54",
            valor,
        )


        # País
        payload += _tlv(
            "58",
            "BR",
        )


        # Recebedor
        payload += _tlv(
            "59",
            nome,
        )


        # Cidade
        payload += _tlv(
            "60",
            cidade,
        )


        # TXID
        payload += _tlv(
            "62",
            dados_adicionais,
        )


        # Campo CRC
        payload_crc = (
            payload
            + "6304"
        )


        crc = _crc16(
            payload_crc
        )


        payload_final = (
            payload_crc
            + crc
        )


        return {
            "success": True,

            "codigo_pix":
                payload_final,

            "txid":
                txid,

            "codigo_pedido":
                str(
                    codigo_pedido
                ),

            "valor":
                valor,

            "valor_centavos":
                int(
                    valor_centavos
                ),
        }


    except Exception as erro:

        return {
            "success": False,
            "error": (
                "Erro ao gerar Pix: "
                f"{str(erro)}"
            ),
        }