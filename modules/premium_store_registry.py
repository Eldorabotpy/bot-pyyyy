# ============================================================
# 💎 MUNDO DE ELDORA - CATÁLOGO DA LOJA PREMIUM
# ============================================================

from copy import deepcopy


# ============================================================
# 💎 PACOTES DE GEMAS
# ============================================================
#
# IMPORTANTE:
#
# - "gemas" é a quantidade REAL entregue ao jogador.
# - "valor_centavos" evita trabalhar com float em dinheiro.
#
# Exemplo:
#
# 500 = R$ 5,00
# 1000 = R$ 10,00
#
# Os valores abaixo são INICIAIS e podem ser alterados
# posteriormente sem precisar mexer no frontend.
# ============================================================

PACOTES_GEMAS = {

    "gemas_100": {
        "id": "gemas_100",

        "nome": "Punhado de Gemas",

        "gemas": 100,

        "valor_centavos": 500,

        "icone": "💎",

        "descricao": (
            "Um pequeno suprimento de gemas "
            "para sua jornada em Eldora."
        ),

        "destaque": False,

        "ativo": True,

        "ordem": 10,
    },


    "gemas_250": {
        "id": "gemas_250",

        "nome": "Bolsa de Gemas",

        "gemas": 250,

        "valor_centavos": 1000,

        "icone": "💎",

        "descricao": (
            "Uma boa reserva para serviços "
            "e recursos especiais."
        ),

        "destaque": False,

        "ativo": True,

        "ordem": 20,
    },


    "gemas_550": {
        "id": "gemas_550",

        "nome": "Baú de Gemas",

        "gemas": 550,

        "valor_centavos": 2000,

        "icone": "💎",

        "descricao": (
            "Mais gemas por compra para "
            "aventureiros frequentes."
        ),

        "destaque": True,

        "ativo": True,

        "ordem": 30,
    },


    "gemas_1200": {
        "id": "gemas_1200",

        "nome": "Cofre Real de Gemas",

        "gemas": 1200,

        "valor_centavos": 4000,

        "icone": "💎",

        "descricao": (
            "Uma grande reserva de gemas "
            "para os heróis mais dedicados."
        ),

        "destaque": False,

        "ativo": True,

        "ordem": 40,
    },
        "gemas_2000": {
        "id": "gemas_2000",

        "nome": "Cofre Nobre",

        "gemas": 2000,

        "valor_centavos": 6000,

        "icone": "💎",

        "descricao": (
            "Uma reserva generosa de gemas "
            "para aventureiros experientes."
        ),

        "destaque": False,

        "ativo": True,

        "ordem": 50,
    },


    "gemas_3500": {
        "id": "gemas_3500",

        "nome": "Tesouro Épico",

        "gemas": 3500,

        "valor_centavos": 10000,

        "icone": "💎",

        "descricao": (
            "Um grande tesouro para quem "
            "vive grandes aventuras em Eldora."
        ),

        "destaque": False,

        "ativo": True,

        "ordem": 60,
    },


    "gemas_6000": {
        "id": "gemas_6000",

        "nome": "Tesouro Lendário",

        "gemas": 6000,

        "valor_centavos": 16000,

        "icone": "💎",

        "descricao": (
            "Uma enorme reserva de gemas "
            "destinada aos grandes heróis."
        ),

        "destaque": False,

        "ativo": True,

        "ordem": 70,
    },


    "gemas_10000": {
        "id": "gemas_10000",

        "nome": "Tesouro de Eldora",

        "gemas": 10000,

        "valor_centavos": 25000,

        "icone": "💎",

        "descricao": (
            "O maior tesouro disponível, "
            "digno das lendas de Eldora."
        ),

        "destaque": False,

        "ativo": True,

        "ordem": 80,
    },
}


# ============================================================
# 📦 LISTAR PACOTES ATIVOS
# ============================================================

def listar_pacotes_gemas():
    pacotes = []


    for pacote in PACOTES_GEMAS.values():

        if not pacote.get(
            "ativo",
            False,
        ):
            continue


        pacotes.append(
            deepcopy(
                pacote
            )
        )


    pacotes.sort(
        key=lambda pacote: int(
            pacote.get(
                "ordem",
                999,
            )
        )
    )


    return pacotes


# ============================================================
# 🔎 OBTER PACOTE
# ============================================================

def obter_pacote_gemas(
    pacote_id,
):
    pacote_id = str(
        pacote_id or ""
    ).strip()


    if not pacote_id:
        return None


    pacote = PACOTES_GEMAS.get(
        pacote_id
    )


    if not pacote:
        return None


    if not pacote.get(
        "ativo",
        False,
    ):
        return None


    return deepcopy(
        pacote
    )


# ============================================================
# 💵 FORMATAR VALOR
# ============================================================

def formatar_valor_reais(
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
        centavos = 0


    reais = centavos / 100


    return (
        f"R$ {reais:,.2f}"
        .replace(
            ",",
            "X",
        )
        .replace(
            ".",
            ",",
        )
        .replace(
            "X",
            ".",
        )
    )