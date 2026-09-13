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

        "beneficios": {
            "tesouraria_dias": 30,

            "limites_loja": {
                "pocao_cura_media": 10,
                "pocao_mana_media": 10,
                "pedra_de_aprimoramento": 5,
                "nucleo_de_forja": 5,
                "pergaminho_de_reparo": 3,
                "sigilo_de_protecao": 2,
            },
        },
    },

    2: {
        "capacidade": 15,
        "xp_evolucao": 5_000,
        "ouro_evolucao": 25_000,

        "beneficios": {
            "tesouraria_dias": 30,

            "limites_loja": {
                "pocao_cura_media": 12,
                "pocao_mana_media": 12,
                "pedra_de_aprimoramento": 5,
                "nucleo_de_forja": 5,
                "pergaminho_de_reparo": 3,
                "sigilo_de_protecao": 2,
            },
        },
    },

    3: {
        "capacidade": 20,
        "xp_evolucao": 10_000,
        "ouro_evolucao": 50_000,

        "beneficios": {
            "tesouraria_dias": 35,

            "limites_loja": {
                "pocao_cura_media": 12,
                "pocao_mana_media": 12,
                "pedra_de_aprimoramento": 6,
                "nucleo_de_forja": 6,
                "pergaminho_de_reparo": 3,
                "sigilo_de_protecao": 2,
            },
        },
    },

    4: {
        "capacidade": 25,
        "xp_evolucao": 18_000,
        "ouro_evolucao": 90_000,

        "beneficios": {
            "tesouraria_dias": 35,

            "limites_loja": {
                "pocao_cura_media": 14,
                "pocao_mana_media": 14,
                "pedra_de_aprimoramento": 6,
                "nucleo_de_forja": 6,
                "pergaminho_de_reparo": 3,
                "sigilo_de_protecao": 2,
            },
        },
    },

    5: {
        "capacidade": 30,
        "xp_evolucao": 30_000,
        "ouro_evolucao": 150_000,

        "beneficios": {
            "tesouraria_dias": 40,

            "limites_loja": {
                "pocao_cura_media": 14,
                "pocao_mana_media": 14,
                "pedra_de_aprimoramento": 7,
                "nucleo_de_forja": 7,
                "pergaminho_de_reparo": 4,
                "sigilo_de_protecao": 2,
            },
        },
    },

    6: {
        "capacidade": 35,
        "xp_evolucao": 45_000,
        "ouro_evolucao": 240_000,

        "beneficios": {
            "tesouraria_dias": 40,

            "limites_loja": {
                "pocao_cura_media": 16,
                "pocao_mana_media": 16,
                "pedra_de_aprimoramento": 7,
                "nucleo_de_forja": 7,
                "pergaminho_de_reparo": 4,
                "sigilo_de_protecao": 2,
            },
        },
    },

    7: {
        "capacidade": 40,
        "xp_evolucao": 65_000,
        "ouro_evolucao": 360_000,

        "beneficios": {
            "tesouraria_dias": 45,

            "limites_loja": {
                "pocao_cura_media": 16,
                "pocao_mana_media": 16,
                "pedra_de_aprimoramento": 8,
                "nucleo_de_forja": 8,
                "pergaminho_de_reparo": 4,
                "sigilo_de_protecao": 3,
            },
        },
    },

    8: {
        "capacidade": 45,
        "xp_evolucao": 90_000,
        "ouro_evolucao": 500_000,

        "beneficios": {
            "tesouraria_dias": 45,

            "limites_loja": {
                "pocao_cura_media": 18,
                "pocao_mana_media": 18,
                "pedra_de_aprimoramento": 8,
                "nucleo_de_forja": 8,
                "pergaminho_de_reparo": 5,
                "sigilo_de_protecao": 3,
            },
        },
    },

    9: {
        "capacidade": 50,
        "xp_evolucao": None,
        "ouro_evolucao": None,

        "beneficios": {
            "tesouraria_dias": 60,

            "limites_loja": {
                "pocao_cura_media": 20,
                "pocao_mana_media": 20,
                "pedra_de_aprimoramento": 10,
                "nucleo_de_forja": 10,
                "pergaminho_de_reparo": 5,
                "sigilo_de_protecao": 4,
            },
        },
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

def obter_beneficios_nivel(
    nivel,
):
    """
    Retorna os benefícios efetivos do nível
    informado.

    Sempre devolve uma cópia independente
    para impedir alterações acidentais no
    registro global.
    """

    config = obter_config_nivel(
        nivel
    )

    beneficios = config.get(
        "beneficios",
        {},
    ) or {}


    limites_loja = beneficios.get(
        "limites_loja",
        {},
    ) or {}


    return {
        "tesouraria_dias": int(
            beneficios.get(
                "tesouraria_dias",
                30,
            )
            or 30
        ),

        "limites_loja": deepcopy(
            limites_loja
        ),
    }


def obter_limite_loja_cla(
    nivel,
    item_id,
    limite_padrao=0,
):
    """
    Retorna o limite semanal oficial de um
    item da Loja do Clã para determinado nível.
    """

    item_id = str(
        item_id or ""
    ).strip()


    beneficios = obter_beneficios_nivel(
        nivel
    )


    limites = beneficios.get(
        "limites_loja",
        {},
    ) or {}


    try:
        return int(
            limites.get(
                item_id,
                limite_padrao,
            )
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):
        return int(
            limite_padrao
            or 0
        )


def obter_dias_tesouraria(
    nivel,
):
    """
    Retorna a duração oficial da licença da
    Tesouraria para o nível do clã.
    """

    beneficios = obter_beneficios_nivel(
        nivel
    )

    return int(
        beneficios.get(
            "tesouraria_dias",
            30,
        )
        or 30
    )

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
