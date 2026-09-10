# ============================================================
# 🛡️ MUNDO DE ELDORA - REGRAS DOS CLÃS
# ============================================================

from copy import deepcopy

CLAN_NIVEL_INICIAL = 1
CLAN_NIVEL_MAXIMO = 9


# Valores iniciais de balanceamento.
# Depois podemos alterar tudo somente neste arquivo.
CLAN_NIVEIS = {
    1: {
        "capacidade": 10,
        "xp_evolucao": 2_000,
        "ouro_evolucao": 10_000,
    },
    2: {
        "capacidade": 15,
        "xp_evolucao": 5_000,
        "ouro_evolucao": 25_000,
    },
    3: {
        "capacidade": 20,
        "xp_evolucao": 10_000,
        "ouro_evolucao": 50_000,
    },
    4: {
        "capacidade": 25,
        "xp_evolucao": 18_000,
        "ouro_evolucao": 90_000,
    },
    5: {
        "capacidade": 30,
        "xp_evolucao": 30_000,
        "ouro_evolucao": 150_000,
    },
    6: {
        "capacidade": 35,
        "xp_evolucao": 45_000,
        "ouro_evolucao": 240_000,
    },
    7: {
        "capacidade": 40,
        "xp_evolucao": 65_000,
        "ouro_evolucao": 360_000,
    },
    8: {
        "capacidade": 45,
        "xp_evolucao": 90_000,
        "ouro_evolucao": 500_000,
    },
    9: {
        "capacidade": 50,
        "xp_evolucao": None,
        "ouro_evolucao": None,
    },

}

# ============================================================
# 🎖️ CARGOS PERSONALIZADOS POR NÍVEL
# ============================================================

# Quantidade máxima de cargos criados pelo próprio clã.
#
# Os cargos do sistema:
# líder / vice-líder / oficial / membro
# NÃO entram neste limite.

CARGOS_PERSONALIZADOS_POR_NIVEL = {
    1: 2,
    2: 3,
    3: 4,
    4: 5,
    5: 6,
    6: 7,
    7: 8,
    8: 9,
    9: 10,
}

# ============================================================
# 👑 CARGOS
# ============================================================

CARGO_LIDER = "lider"
CARGO_VICE_LIDER = "vice_lider"
CARGO_OFICIAL = "oficial"
CARGO_MEMBRO = "membro"

# ============================================================
# 🔐 PERMISSÕES DOS CARGOS
# ============================================================

PERMISSAO_CONVIDAR = "convidar"

PERMISSAO_ACEITAR_SOLICITACOES = (
    "aceitar_solicitacoes"
)

PERMISSAO_EXPULSAR = "expulsar"

PERMISSAO_GERENCIAR_MISSOES = (
    "gerenciar_missoes"
)

PERMISSAO_GERENCIAR_CARGOS = (
    "gerenciar_cargos"
)

PERMISSAO_EDITAR_CLA = (
    "editar_cla"
)

PERMISSAO_ALTERAR_BRASAO = (
    "alterar_brasao"
)

PERMISSAO_MELHORAR_CLA = (
    "melhorar_cla"
)

PERMISSAO_GERENCIAR_TESOURO = (
    "gerenciar_tesouro"
)


PERMISSOES_CARGO_VALIDAS = {
    PERMISSAO_CONVIDAR,
    PERMISSAO_ACEITAR_SOLICITACOES,
    PERMISSAO_EXPULSAR,
    PERMISSAO_GERENCIAR_MISSOES,
    PERMISSAO_GERENCIAR_CARGOS,
    PERMISSAO_EDITAR_CLA,
    PERMISSAO_ALTERAR_BRASAO,
    PERMISSAO_MELHORAR_CLA,
    PERMISSAO_GERENCIAR_TESOURO,
}


PERMISSOES_CARGO_NOMES = {

    PERMISSAO_CONVIDAR:
        "Convidar jogadores",

    PERMISSAO_ACEITAR_SOLICITACOES:
        "Aceitar solicitações",

    PERMISSAO_EXPULSAR:
        "Expulsar membros",

    PERMISSAO_GERENCIAR_MISSOES:
        "Administrar missões",

    PERMISSAO_GERENCIAR_CARGOS:
        "Administrar cargos",

    PERMISSAO_EDITAR_CLA:
        "Editar informações do clã",

    PERMISSAO_ALTERAR_BRASAO:
        "Alterar brasão",

    PERMISSAO_MELHORAR_CLA:
        "Melhorar o clã",

    PERMISSAO_GERENCIAR_TESOURO:
        "Administrar tesouro",
}


# ============================================================
# 👑 CONFIGURAÇÃO DOS CARGOS PADRÃO
# ============================================================
#
# IMPORTANTE:
#
# Esses valores reproduzem as permissões
# que o sistema possui HOJE.
#
# Portanto esta mudança ainda não altera
# o comportamento dos jogadores.
# ============================================================

CARGOS_PADRAO = {

    CARGO_LIDER: {

        "nome":
            "Líder",

        "ordem":
            100,

        "sistema":
            True,

        "protegido":
            True,

        "permissoes": {

            PERMISSAO_CONVIDAR:
                True,

            PERMISSAO_ACEITAR_SOLICITACOES:
                True,

            PERMISSAO_EXPULSAR:
                True,

            PERMISSAO_GERENCIAR_MISSOES:
                True,

            PERMISSAO_GERENCIAR_CARGOS:
                True,

            PERMISSAO_EDITAR_CLA:
                True,

            PERMISSAO_ALTERAR_BRASAO:
                True,

            PERMISSAO_MELHORAR_CLA:
                True,

            PERMISSAO_GERENCIAR_TESOURO:
                True,
        },
    },


    CARGO_VICE_LIDER: {

        "nome":
            "Vice-líder",

        "ordem":
            90,

        "sistema":
            True,

        "protegido":
            True,

        "permissoes": {

            PERMISSAO_CONVIDAR:
                True,

            PERMISSAO_ACEITAR_SOLICITACOES:
                True,

            PERMISSAO_EXPULSAR:
                True,

            PERMISSAO_GERENCIAR_MISSOES:
                True,

            PERMISSAO_GERENCIAR_CARGOS:
                False,

            PERMISSAO_EDITAR_CLA:
                False,

            PERMISSAO_ALTERAR_BRASAO:
                False,

            PERMISSAO_MELHORAR_CLA:
                False,

            PERMISSAO_GERENCIAR_TESOURO:
                False,
        },
    },


    CARGO_OFICIAL: {

        "nome":
            "Oficial",

        "ordem":
            70,

        "sistema":
            True,

        "protegido":
            True,

        "permissoes": {

            PERMISSAO_CONVIDAR:
                True,

            PERMISSAO_ACEITAR_SOLICITACOES:
                False,

            PERMISSAO_EXPULSAR:
                False,

            PERMISSAO_GERENCIAR_MISSOES:
                True,

            PERMISSAO_GERENCIAR_CARGOS:
                False,

            PERMISSAO_EDITAR_CLA:
                False,

            PERMISSAO_ALTERAR_BRASAO:
                False,

            PERMISSAO_MELHORAR_CLA:
                False,

            PERMISSAO_GERENCIAR_TESOURO:
                False,
        },
    },


    CARGO_MEMBRO: {

        "nome":
            "Membro",

        "ordem":
            10,

        "sistema":
            True,

        "protegido":
            True,

        "permissoes": {

            PERMISSAO_CONVIDAR:
                False,

            PERMISSAO_ACEITAR_SOLICITACOES:
                False,

            PERMISSAO_EXPULSAR:
                False,

            PERMISSAO_GERENCIAR_MISSOES:
                False,

            PERMISSAO_GERENCIAR_CARGOS:
                False,

            PERMISSAO_EDITAR_CLA:
                False,

            PERMISSAO_ALTERAR_BRASAO:
                False,

            PERMISSAO_MELHORAR_CLA:
                False,

            PERMISSAO_GERENCIAR_TESOURO:
                False,
        },
    },
}

CARGOS_VALIDOS = {
    CARGO_LIDER,
    CARGO_VICE_LIDER,
    CARGO_OFICIAL,
    CARGO_MEMBRO,
}


HIERARQUIA_CARGOS = {
    CARGO_MEMBRO: 1,
    CARGO_OFICIAL: 2,
    CARGO_VICE_LIDER: 3,
    CARGO_LIDER: 4,
}


CARGOS_PODEM_CONVIDAR = {
    CARGO_LIDER,
    CARGO_VICE_LIDER,
    CARGO_OFICIAL,
}


CARGOS_PODEM_EXPULSAR = {
    CARGO_LIDER,
    CARGO_VICE_LIDER,
}

# ============================================================
# 🏰 MISSÕES COLETIVAS DO CLÃ
# ============================================================

CARGOS_PODEM_GERENCIAR_MISSOES = {
    CARGO_LIDER,
    CARGO_VICE_LIDER,
    CARGO_OFICIAL,
}

CARGOS_PROMOVIVEIS = {
    CARGO_MEMBRO,
    CARGO_OFICIAL,
    CARGO_VICE_LIDER,
}


# ============================================================
# 🛠️ FUNÇÕES
# ============================================================

def obter_config_nivel(nivel):
    try:
        nivel = int(nivel)
    except (TypeError, ValueError):
        nivel = CLAN_NIVEL_INICIAL

    return CLAN_NIVEIS.get(
        nivel,
        CLAN_NIVEIS[CLAN_NIVEL_INICIAL],
    )


def obter_capacidade(nivel):
    return int(
        obter_config_nivel(nivel)["capacidade"]
    )


def obter_proximo_nivel(nivel):
    try:
        nivel = int(nivel)
    except (TypeError, ValueError):
        return None

    if nivel >= CLAN_NIVEL_MAXIMO:
        return None

    return nivel + 1


def obter_custo_evolucao(nivel):
    config = obter_config_nivel(nivel)

    return {
        "xp": config.get("xp_evolucao"),
        "ouro": config.get("ouro_evolucao"),
    }


def pode_evoluir_cla(nivel):
    return obter_proximo_nivel(nivel) is not None


def cargo_valido(cargo):
    return cargo in CARGOS_VALIDOS


def obter_hierarquia(cargo):
    return int(HIERARQUIA_CARGOS.get(cargo, 0))


def cargo_superior(cargo_a, cargo_b):
    return (
        obter_hierarquia(cargo_a)
        > obter_hierarquia(cargo_b)
    )


def pode_convidar(cargo):
    return cargo in CARGOS_PODEM_CONVIDAR


def pode_expulsar(cargo):
    return cargo in CARGOS_PODEM_EXPULSAR

def pode_gerenciar_missoes(cargo):
    """
    Líder, vice-líder e oficial podem
    aceitar e entregar contratos coletivos.

    Membros comuns apenas contribuem.
    """

    return (
        cargo
        in CARGOS_PODEM_GERENCIAR_MISSOES
    )

# ============================================================
# 🎖️ NOVO SISTEMA DE CARGOS
# ============================================================

def obter_limite_cargos_personalizados(
    nivel,
):
    """
    Retorna quantos cargos personalizados
    um clã pode possuir naquele nível.
    """

    try:
        nivel = int(nivel)

    except (TypeError, ValueError):
        nivel = CLAN_NIVEL_INICIAL


    nivel = max(
        CLAN_NIVEL_INICIAL,
        min(
            nivel,
            CLAN_NIVEL_MAXIMO,
        ),
    )


    return int(
        CARGOS_PERSONALIZADOS_POR_NIVEL.get(
            nivel,
            2,
        )
    )


def obter_cargos_padrao():
    """
    Retorna uma cópia independente dos
    cargos padrão.

    Isso evita que um clã altere o catálogo
    global de outro clã.
    """

    return deepcopy(
        CARGOS_PADRAO
    )


def obter_config_cargo_padrao(
    cargo,
):
    """
    Retorna a configuração de um cargo
    padrão do sistema.
    """

    cargo = str(
        cargo or ""
    ).strip()


    dados = CARGOS_PADRAO.get(
        cargo
    )


    if not dados:
        return None


    return deepcopy(
        dados
    )


def normalizar_permissoes_cargo(
    permissoes,
):
    """
    Garante que somente permissões conhecidas
    sejam salvas no cargo.

    Todas são convertidas para True/False.
    """

    permissoes = (
        permissoes
        if isinstance(
            permissoes,
            dict
        )
        else {}
    )


    resultado = {}


    for permissao in (
        PERMISSOES_CARGO_VALIDAS
    ):

        resultado[
            permissao
        ] = bool(
            permissoes.get(
                permissao,
                False,
            )
        )


    return resultado


def listar_permissoes_cargo():
    """
    Lista as permissões para a interface
    de criação/edição de cargos.
    """

    resultado = []


    for permissao in sorted(
        PERMISSOES_CARGO_VALIDAS
    ):

        resultado.append({

            "id":
                permissao,

            "nome":
                PERMISSOES_CARGO_NOMES.get(
                    permissao,
                    permissao,
                ),
        })


    return resultado


def cargo_padrao_tem_permissao(
    cargo,
    permissao,
):
    """
    Consulta uma permissão de um cargo
    padrão do sistema.
    """

    cargo = str(
        cargo or ""
    ).strip()

    permissao = str(
        permissao or ""
    ).strip()


    if (
        permissao
        not in PERMISSOES_CARGO_VALIDAS
    ):
        return False


    dados = CARGOS_PADRAO.get(
        cargo,
        {}
    )


    permissoes = (
        dados.get(
            "permissoes",
            {}
        )
        or {}
    )


    return bool(
        permissoes.get(
            permissao,
            False,
        )
    )
