# ============================================================
# ⚔️ MUNDO DE ELDORA - REGRAS DA GUERRA DE CLÃS
# ============================================================
#
# Este arquivo contém somente regras/configurações.
#
# NÃO acessa MongoDB.
# NÃO executa combate.
# NÃO entrega recompensas.
#
# O clan_war_manager.py utilizará estas regras.
# ============================================================

from copy import deepcopy

from modules.clan.clan_registry import (
    CLAN_NIVEL_INICIAL,
    CLAN_NIVEL_MAXIMO,
)


# ============================================================
# 🧱 VERSÃO
# ============================================================

CLAN_WAR_SCHEMA_VERSION = 1


# ============================================================
# ⚔️ TIPOS DE GUERRA
# ============================================================

GUERRA_TIPO_OFICIAL = "oficial"
GUERRA_TIPO_AMISTOSA = "amistosa"

TIPOS_GUERRA_VALIDOS = {
    GUERRA_TIPO_OFICIAL,
    GUERRA_TIPO_AMISTOSA,
}


# ============================================================
# 🚦 STATUS
# ============================================================

GUERRA_STATUS_INSCRICOES = (
    "inscricoes"
)

GUERRA_STATUS_ESCALACAO = (
    "escalacao"
)

GUERRA_STATUS_PAREAMENTO = (
    "pareamento"
)

GUERRA_STATUS_AGENDADA = (
    "agendada"
)

GUERRA_STATUS_EM_ANDAMENTO = (
    "em_andamento"
)

GUERRA_STATUS_FINALIZADA = (
    "finalizada"
)

GUERRA_STATUS_CANCELADA = (
    "cancelada"
)


STATUS_GUERRA_VALIDOS = {
    GUERRA_STATUS_INSCRICOES,
    GUERRA_STATUS_ESCALACAO,
    GUERRA_STATUS_PAREAMENTO,
    GUERRA_STATUS_AGENDADA,
    GUERRA_STATUS_EM_ANDAMENTO,
    GUERRA_STATUS_FINALIZADA,
    GUERRA_STATUS_CANCELADA,
}


STATUS_GUERRA_FINAIS = {
    GUERRA_STATUS_FINALIZADA,
    GUERRA_STATUS_CANCELADA,
}


# ============================================================
# 🔄 TRANSIÇÕES PERMITIDAS
# ============================================================
#
# Impede uma guerra de pular fases.
#
# Exemplo:
#
# inscrições
#     ↓
# escalação
#     ↓
# pareamento
#     ↓
# agendada
#     ↓
# em andamento
#     ↓
# finalizada
# ============================================================

TRANSICOES_STATUS_GUERRA = {

    GUERRA_STATUS_INSCRICOES: {
        GUERRA_STATUS_ESCALACAO,
        GUERRA_STATUS_CANCELADA,
    },

    GUERRA_STATUS_ESCALACAO: {
        GUERRA_STATUS_PAREAMENTO,
        GUERRA_STATUS_CANCELADA,
    },

    GUERRA_STATUS_PAREAMENTO: {
        GUERRA_STATUS_AGENDADA,
        GUERRA_STATUS_CANCELADA,
    },

    GUERRA_STATUS_AGENDADA: {
        GUERRA_STATUS_EM_ANDAMENTO,
        GUERRA_STATUS_CANCELADA,
    },

    GUERRA_STATUS_EM_ANDAMENTO: {
        GUERRA_STATUS_FINALIZADA,
        GUERRA_STATUS_CANCELADA,
    },

    GUERRA_STATUS_FINALIZADA:
        set(),

    GUERRA_STATUS_CANCELADA:
        set(),
}


# ============================================================
# 👥 ESTRUTURA DAS BATALHAS
# ============================================================

JOGADORES_POR_FRENTE = 5

GUERRA_MINIMO_JOGADORES_POR_CLA = 5
GUERRA_MAXIMO_JOGADORES_POR_CLA = 25


# ============================================================
# ⚔️ CATEGORIAS
# ============================================================
#
# Nunca teremos uma batalha gigante de 25x25.
#
# Cada guerra será dividida em frentes 5x5.
#
# 5x5   = 1 frente
# 10x10 = 2 frentes
# 15x15 = 3 frentes
# 20x20 = 4 frentes
# 25x25 = 5 frentes
# ============================================================

CATEGORIAS_GUERRA = {

    5: {
        "id":
            "5x5",

        "nome":
            "5 x 5",

        "jogadores_por_cla":
            5,

        "frentes":
            1,

        "jogadores_por_frente":
            JOGADORES_POR_FRENTE,
    },


    10: {
        "id":
            "10x10",

        "nome":
            "10 x 10",

        "jogadores_por_cla":
            10,

        "frentes":
            2,

        "jogadores_por_frente":
            JOGADORES_POR_FRENTE,
    },


    15: {
        "id":
            "15x15",

        "nome":
            "15 x 15",

        "jogadores_por_cla":
            15,

        "frentes":
            3,

        "jogadores_por_frente":
            JOGADORES_POR_FRENTE,
    },


    20: {
        "id":
            "20x20",

        "nome":
            "20 x 20",

        "jogadores_por_cla":
            20,

        "frentes":
            4,

        "jogadores_por_frente":
            JOGADORES_POR_FRENTE,
    },


    25: {
        "id":
            "25x25",

        "nome":
            "25 x 25",

        "jogadores_por_cla":
            25,

        "frentes":
            5,

        "jogadores_por_frente":
            JOGADORES_POR_FRENTE,
    },
}


# ============================================================
# 🏰 CATEGORIA MÁXIMA POR NÍVEL DO CLÃ
# ============================================================
#
# O nível define somente o LIMITE.
#
# Ele não obriga o clã a lutar nessa categoria.
#
# Exemplo:
#
# Clã nível 7:
# pode participar até 20x20.
#
# Mas se somente 12 jogadores se inscreverem,
# participa naquela semana como 10x10.
# ============================================================

CATEGORIA_MAXIMA_POR_NIVEL_CLA = {

    1: 5,
    2: 5,

    3: 10,
    4: 10,

    5: 15,
    6: 15,

    7: 20,
    8: 20,

    9: 25,
}


# ============================================================
# 📅 CALENDÁRIO SEMANAL
# ============================================================
#
# dia_semana:
#
# 0 = segunda
# 1 = terça
# 2 = quarta
# 3 = quinta
# 4 = sexta
# 5 = sábado
# 6 = domingo
#
#
# PRIMEIRA CONFIGURAÇÃO:
#
# Segunda 00:00
# → inscrições abrem
#
# Quinta 23:59
# → inscrições dos membros fecham
#
# Sexta 18:00
# → escalações travadas
#
# Sexta 19:00
# → matchmaking
#
# Sábado 10:00
# → guerra abre
#
# Domingo 22:00
# → guerra encerra
#
# Podemos alterar depois somente aqui.
# ============================================================

GUERRA_SEMANAL_TIMEZONE = (
    "America/Sao_Paulo"
)


CALENDARIO_GUERRA_SEMANAL = {

    "inscricoes_abrem": {
        "dia_semana": 0,
        "hora": 0,
        "minuto": 0,
    },

    "inscricoes_fecham": {
        "dia_semana": 3,
        "hora": 23,
        "minuto": 59,
    },

    "escalacoes_travam": {
        "dia_semana": 4,
        "hora": 18,
        "minuto": 0,
    },

    "pareamento": {
        "dia_semana": 4,
        "hora": 19,
        "minuto": 0,
    },

    "guerra_abre": {
        "dia_semana": 5,
        "hora": 10,
        "minuto": 0,
    },

    "guerra_fecha": {
        "dia_semana": 6,
        "hora": 22,
        "minuto": 0,
    },
}


# ============================================================
# 🏆 CRITÉRIOS DE DESEMPATE
# ============================================================
#
# Importante para:
#
# 10x10 = 2 frentes
# 20x20 = 4 frentes
#
# Ordem:
#
# 1. frentes vencidas
# 2. sobreviventes
# 3. % total de HP restante
# 4. dano total causado
#
# Só conectaremos isso ao combate quando analisarmos
# o motor de combate em grupo.
# ============================================================

CRITERIOS_DESEMPATE_GUERRA = (

    "frentes_vencidas",

    "sobreviventes",

    "hp_percentual_restante",

    "dano_total",
)


# ============================================================
# 📈 RATING
# ============================================================
#
# Rating será utilizado pelo matchmaking.
#
# NÃO é a mesma coisa que Pontos de Guerra.
# ============================================================

GUERRA_RATING_INICIAL = 1000


# ============================================================
# 🛠️ HELPERS
# ============================================================

def _inteiro(
    valor,
    padrao=0,
):
    try:
        return int(
            valor
        )

    except (
        TypeError,
        ValueError,
    ):
        return int(
            padrao
        )


# ============================================================
# 🚦 STATUS
# ============================================================

def status_guerra_valido(
    status,
):
    return (
        str(
            status or ""
        ).strip()
        in STATUS_GUERRA_VALIDOS
    )


def status_guerra_final(
    status,
):
    return (
        str(
            status or ""
        ).strip()
        in STATUS_GUERRA_FINAIS
    )


def pode_transicionar_status(
    status_atual,
    novo_status,
):
    status_atual = str(
        status_atual or ""
    ).strip()

    novo_status = str(
        novo_status or ""
    ).strip()


    if (
        status_atual
        not in STATUS_GUERRA_VALIDOS
    ):
        return False


    if (
        novo_status
        not in STATUS_GUERRA_VALIDOS
    ):
        return False


    return (
        novo_status
        in TRANSICOES_STATUS_GUERRA.get(
            status_atual,
            set(),
        )
    )


# ============================================================
# 🏰 LIMITE POR NÍVEL
# ============================================================

def obter_categoria_maxima_por_nivel(
    nivel_cla,
):
    nivel = _inteiro(
        nivel_cla,
        CLAN_NIVEL_INICIAL,
    )


    nivel = max(
        CLAN_NIVEL_INICIAL,
        min(
            nivel,
            CLAN_NIVEL_MAXIMO,
        ),
    )


    return int(
        CATEGORIA_MAXIMA_POR_NIVEL_CLA.get(
            nivel,
            5,
        )
    )


# ============================================================
# ⚔️ CONFIGURAÇÃO DA CATEGORIA
# ============================================================

def obter_config_categoria(
    jogadores_por_cla,
):
    tamanho = _inteiro(
        jogadores_por_cla,
        0,
    )


    config = (
        CATEGORIAS_GUERRA.get(
            tamanho
        )
    )


    if not config:
        return None


    return deepcopy(
        config
    )


def listar_categorias_guerra():
    return [

        deepcopy(
            CATEGORIAS_GUERRA[
                tamanho
            ]
        )

        for tamanho
        in sorted(
            CATEGORIAS_GUERRA
        )
    ]


def listar_categorias_liberadas(
    nivel_cla,
):
    maximo = (
        obter_categoria_maxima_por_nivel(
            nivel_cla
        )
    )


    return [

        deepcopy(
            config
        )

        for (
            tamanho,
            config
        )
        in sorted(
            CATEGORIAS_GUERRA.items()
        )

        if tamanho <= maximo
    ]


# ============================================================
# 👥 CATEGORIA EFETIVA DA SEMANA
# ============================================================

def obter_tamanho_categoria_efetiva(
    nivel_cla,
    inscritos,
):
    """
    Calcula o tamanho real da guerra.

    Exemplo:

    Clã liberado até 20x20.
    Inscritos = 13.

    Resultado:
    10x10.

    Retorna None se houver menos de 5.
    """

    inscritos = max(
        0,
        _inteiro(
            inscritos,
            0,
        ),
    )


    maximo_nivel = (
        obter_categoria_maxima_por_nivel(
            nivel_cla
        )
    )


    limite_real = min(
        inscritos,
        maximo_nivel,
        GUERRA_MAXIMO_JOGADORES_POR_CLA,
    )


    categorias = [

        tamanho

        for tamanho
        in CATEGORIAS_GUERRA

        if tamanho <= limite_real
    ]


    if not categorias:
        return None


    return max(
        categorias
    )


def obter_categoria_efetiva(
    nivel_cla,
    inscritos,
):
    tamanho = (
        obter_tamanho_categoria_efetiva(
            nivel_cla,
            inscritos,
        )
    )


    if tamanho is None:
        return None


    return obter_config_categoria(
        tamanho
    )


# ============================================================
# ⚔️ QUANTIDADE DE FRENTES
# ============================================================

def obter_quantidade_frentes(
    jogadores_por_cla,
):
    config = (
        obter_config_categoria(
            jogadores_por_cla
        )
    )


    if not config:
        return 0


    return int(
        config.get(
            "frentes",
            0,
        )
        or 0
    )


# ============================================================
# 📅 CALENDÁRIO
# ============================================================

def obter_calendario_guerra_semanal():
    return deepcopy(
        CALENDARIO_GUERRA_SEMANAL
    )