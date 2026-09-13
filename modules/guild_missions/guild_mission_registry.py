# ============================================================
# 📜 MUNDO DE ELDORA - REGISTRO DE MISSÕES DA GUILDA
# ============================================================
#
# IMPORTANTE:
# Este sistema NÃO usa player["quests"].
#
# quests = história / evolução / classes
#
# guild_missions = Guilda dos Aventureiros
#
# ============================================================

from copy import deepcopy

from modules.game_data.monsters import MONSTERS_DATA


# ============================================================
# CONSTANTES
# ============================================================

# ============================================================
# 👤 TIPO
# ============================================================

TIPO_PESSOAL = "pessoal"
TIPO_CLA = "cla"


# ============================================================
# 🎯 ESCOPO
# ============================================================

# Missão pertence ao personagem.
ESCOPO_INDIVIDUAL = "individual"

# Missão pertence ao clã inteiro.
ESCOPO_COLETIVO = "coletivo"


# ============================================================
# ⚔️ MODO
# ============================================================

MODO_SOLO = "solo"
MODO_GRUPO = "grupo"

# Aceita abate solo OU em grupo.
MODO_QUALQUER = "qualquer"


# ============================================================
# ⏰ FREQUÊNCIA
# ============================================================

# Só pode ser concluída uma vez.
FREQUENCIA_UNICA = "unica"

# Pode ser realizada uma vez por dia.
FREQUENCIA_DIARIA = "diaria"

# Pode ser realizada uma vez por semana.
FREQUENCIA_SEMANAL = "semanal"


# ============================================================
# 🎯 OBJETIVOS
# ============================================================

OBJETIVO_MATAR_MOB = "matar_mob"


TIPOS_VALIDOS = {
    TIPO_PESSOAL,
    TIPO_CLA,
}


ESCOPOS_VALIDOS = {
    ESCOPO_INDIVIDUAL,
    ESCOPO_COLETIVO,
}


MODOS_VALIDOS = {
    MODO_SOLO,
    MODO_GRUPO,
    MODO_QUALQUER,
}


FREQUENCIAS_VALIDAS = {
    FREQUENCIA_UNICA,
    FREQUENCIA_DIARIA,
    FREQUENCIA_SEMANAL,
}

# ============================================================
# 🏅 RANKS DA GUILDA DOS AVENTUREIROS
# ============================================================
#
# A reputação total do personagem nunca diminui.
#
# pontos_total
#     -> determina o Rank da Guilda
#
# pontos
#     -> será o saldo gastável na Loja da Guilda
#
# ============================================================

GUILD_RANKS = (

    {
        "id": "novato",
        "nome": "Novato",
        "reputacao_minima": 0,
    },

    {
        "id": "ferro",
        "nome": "Ferro",
        "reputacao_minima": 50,
    },

    {
        "id": "bronze",
        "nome": "Bronze",
        "reputacao_minima": 150,
    },

    {
        "id": "prata",
        "nome": "Prata",
        "reputacao_minima": 350,
    },

    {
        "id": "ouro",
        "nome": "Ouro",
        "reputacao_minima": 700,
    },

    {
        "id": "platina",
        "nome": "Platina",
        "reputacao_minima": 1200,
    },

    {
        "id": "mestre",
        "nome": "Mestre",
        "reputacao_minima": 2000,
    },

    {
        "id": "lendario",
        "nome": "Lendário",
        "reputacao_minima": 3500,
    },
)

def obter_rank_guilda(
    pontos_total,
):
    """
    Retorna o Rank oficial da Guilda
    a partir da reputação histórica.

    Esta função NÃO usa o saldo gastável.
    """

    try:
        pontos_total = max(
            0,
            int(
                pontos_total
                or 0
            ),
        )

    except (
        TypeError,
        ValueError,
    ):
        pontos_total = 0


    rank_atual = (
        GUILD_RANKS[0]
    )

    proximo_rank = None


    for indice, rank in enumerate(
        GUILD_RANKS
    ):

        minimo = int(
            rank.get(
                "reputacao_minima",
                0,
            )
            or 0
        )


        if pontos_total >= minimo:

            rank_atual = rank

            if (
                indice + 1
                <
                len(
                    GUILD_RANKS
                )
            ):
                proximo_rank = (
                    GUILD_RANKS[
                        indice + 1
                    ]
                )

            else:
                proximo_rank = None

            continue


        break


    minimo_atual = int(
        rank_atual.get(
            "reputacao_minima",
            0,
        )
        or 0
    )


    if proximo_rank:

        minimo_proximo = int(
            proximo_rank.get(
                "reputacao_minima",
                0,
            )
            or 0
        )


        faltante = max(
            0,
            minimo_proximo
            -
            pontos_total,
        )


        tamanho_faixa = max(
            1,
            minimo_proximo
            -
            minimo_atual,
        )


        progresso_faixa = max(
            0,
            pontos_total
            -
            minimo_atual,
        )


        progresso_percentual = min(
            100,
            max(
                0,
                round(
                    (
                        progresso_faixa
                        /
                        tamanho_faixa
                    )
                    *
                    100
                ),
            ),
        )


        proximo_dados = {
            "id":
                proximo_rank["id"],

            "nome":
                proximo_rank["nome"],

            "reputacao_minima":
                minimo_proximo,
        }


    else:

        minimo_proximo = None

        faltante = 0

        progresso_percentual = 100

        proximo_dados = None


    return {

        "id":
            rank_atual["id"],

        "nome":
            rank_atual["nome"],

        "reputacao_minima":
            minimo_atual,

        "reputacao_total":
            pontos_total,

        "proximo_rank":
            proximo_dados,

        "reputacao_proximo_rank":
            minimo_proximo,

        "reputacao_faltante":
            faltante,

        "progresso_percentual":
            progresso_percentual,

        "nivel_maximo":
            proximo_rank is None,
    }

# ============================================================
# NOMES DAS REGIÕES
# ============================================================

REGIOES_GUILDA = {

    "capital_eldora": "Capital de Eldora",

    "pradaria_inicial": "Pradaria Inicial",

    "floresta_sombria": "Floresta Sombria",

    "pedreira_granito": "Pedreira de Granito",

    "campos_linho": "Campos de Linho",

    "pico_grifo": "Pico do Grifo",

    "mina_ferro": "Mina de Ferro",

    "forja_abandonada": "Forja Abandonada",

    "pantano_maldito": "Pântano Maldito",

    "picos_gelados": "Picos Gelados",

    "deserto_ancestral": "Deserto Ancestral",
}


# ============================================================
# 📜 CATÁLOGO DE MISSÕES
# ============================================================
#
# tipo:
#   pessoal = contrato do personagem
#   cla     = contrato relacionado ao clã
#
# escopo:
#   individual = progresso pertence ao personagem
#   coletivo   = progresso pertence ao clã inteiro
#
# modo:
#   solo  = abate só conta fora de grupo
#   grupo = abate só conta quando realmente estiver em grupo
#
# ============================================================
# ============================================================
# 👹 HELPERS DE MOBS DAS REGIÕES
# ============================================================

def ids_mobs_regiao(
    regiao,
    incluir_bosses=True,
):
    """
    Retorna automaticamente todos os IDs
    de monstros existentes em uma região.

    Assim missões do tipo:
    "Derrote criaturas da Floresta"
    não precisam manter uma lista manual.
    """

    resultado = []

    for mob in MONSTERS_DATA.get(
        str(regiao),
        [],
    ):

        mob_id = mob.get("id")

        if not mob_id:
            continue

        if (
            not incluir_bosses
            and mob.get("is_boss")
        ):
            continue

        resultado.append(
            str(mob_id)
        )

    return resultado

GUILD_MISSIONS = {

    # ========================================================
    # 👤 PESSOAL + SOLO
    # ========================================================

    "guild_pessoal_solo_001": {

        "id": "guild_pessoal_solo_001",

        "nome": "Limpeza da Pradaria",

        "descricao": (
            "A população de slimes cresceu demais. "
            "A Guilda precisa de aventureiros para controlá-la."
        ),

        "tipo": TIPO_PESSOAL,

        "modo": MODO_SOLO,

        "nivel_minimo": 1,

        "ativa": True,

        "objetivo": {

            "tipo": OBJETIVO_MATAR_MOB,

            "regiao": "pradaria_inicial",

            "mob_ids":
                ids_mobs_regiao(
                    "pradaria_inicial"
                ),

            "quantidade": 10,

            "texto": (
                "Derrote 10 Slimes na Pradaria Inicial."
            ),
        },

        "recompensas": {

            "xp": 80,

            "gold": 120,

            # NÃO É stat_points.
            # São pontos pessoais da Guilda.
            "pontos_guilda": 5,

            "xp_cla": 0,

            "itens": [
                {
                    "item_id": "pocao_cura_leve",
                    "quantidade": 2,
                }
            ],
        },

        "repetivel": False,
    },


    # ========================================================
    # 👥 PESSOAL + GRUPO
    # ========================================================

    "guild_pessoal_grupo_001": {

        "id": "guild_pessoal_grupo_001",

        "nome": "Caçada em Companhia",

        "descricao": (
            "Algumas criaturas da Floresta Sombria são "
            "mais seguras quando enfrentadas ao lado de aliados."
        ),

        "tipo": TIPO_PESSOAL,

        "modo": MODO_GRUPO,

        "nivel_minimo": 5,

        "ativa": True,

        "objetivo": {

            "tipo": OBJETIVO_MATAR_MOB,

            "regiao": "floresta_sombria",

            "mob_ids":
                ids_mobs_regiao(
                    "floresta_sombria"
                ),

            "quantidade": 15,

            "texto": (
                "Derrote 15 criaturas da Floresta Sombria "
                "participando de um grupo."
            ),
        },

        "recompensas": {

            "xp": 180,

            "gold": 250,

            "pontos_guilda": 10,

            "xp_cla": 0,

            "itens": [
                {
                    "item_id": "pedra_de_aprimoramento",
                    "quantidade": 1,
                }
            ],
        },

        "repetivel": False,
    },


    # ========================================================
    # 🛡️ CLÃ + SOLO
    # ========================================================

    "guild_cla_solo_001": {

        "id": "guild_cla_solo_001",

        "nome": "Serviço ao Estandarte",

        "descricao": (
            "A Guilda oferece contratos especiais aos membros "
            "de clãs. Complete a tarefa e fortaleça seu clã."
        ),

        "tipo": TIPO_CLA,

        "modo": MODO_SOLO,

        "nivel_minimo": 15,

        "ativa": True,

        "objetivo": {

            "tipo": OBJETIVO_MATAR_MOB,

            "regiao": "pedreira_granito",

            "mob_ids":
                ids_mobs_regiao(
                    "pedreira_granito"
                ),

            "quantidade": 12,

            "texto": (
                "Derrote 12 criaturas da Pedreira de Granito "
                "sem estar em grupo."
            ),
        },

        "recompensas": {

            "xp": 250,

            "gold": 300,

            "pontos_guilda": 12,

            # Somente entregue quando voltar à Guilda.
            "xp_cla": 100,

            "medalhas_cla": 6,

            "itens": [
                {
                    "item_id": "nucleo_de_forja",
                    "quantidade": 1,
                }
            ],
        },

        "repetivel": False,
    },


    # ========================================================
    # ⚔️ CLÃ + GRUPO
    # ========================================================

    "guild_cla_grupo_001": {

        "id": "guild_cla_grupo_001",

        "nome": "Expedição da Pedreira",

        "descricao": (
            "Aventureiros organizados em grupo devem reduzir "
            "a ameaça das criaturas mais perigosas da Pedreira."
        ),

        "tipo": TIPO_CLA,

        "modo": MODO_GRUPO,

        "nivel_minimo": 15,

        "ativa": True,

        "objetivo": {

            "tipo": OBJETIVO_MATAR_MOB,

            "regiao": "pedreira_granito",

            "mob_ids":
                ids_mobs_regiao(
                    "pedreira_granito"
                ),

            "quantidade": 20,

            "texto": (
                "Derrote 20 criaturas da Pedreira de Granito "
                "participando de um grupo."
            ),
        },

        "recompensas": {

            "xp": 450,

            "gold": 550,

            "pontos_guilda": 20,

            "xp_cla": 250,

            "medalhas_cla": 10,

            "itens": [
                {
                    "item_id": "pergaminho_de_reparo",
                    "quantidade": 1,
                }
            ],
        },

        "repetivel": False,
    },

    # ========================================================
    # 👤 PESSOAL + SOLO 002
    # ========================================================

    "guild_pessoal_solo_002": {

        "id": "guild_pessoal_solo_002",

        "nome": "Sombras Entre as Árvores",

        "descricao": (
            "Viajantes desapareceram nas trilhas da "
            "Floresta Sombria. A Guilda precisa reduzir "
            "a presença das criaturas na região."
        ),

        "tipo": TIPO_PESSOAL,

        "modo": MODO_SOLO,

        "nivel_minimo": 5,

        "ativa": True,

        "objetivo": {

            "tipo": OBJETIVO_MATAR_MOB,

            "regiao": "floresta_sombria",

            "mob_ids":
                ids_mobs_regiao(
                    "floresta_sombria"
                ),

            "quantidade": 12,

            "texto": (
                "Derrote 12 criaturas da "
                "Floresta Sombria sem estar em grupo."
            ),
        },

        "recompensas": {

            "xp": 160,

            "gold": 220,

            "pontos_guilda": 8,

            "xp_cla": 0,

            "itens": [
                {
                    "item_id": "pocao_mana_leve",
                    "quantidade": 2,
                }
            ],
        },

        "repetivel": False,
    },


    # ========================================================
    # 👥 PESSOAL + GRUPO 002
    # ========================================================

    "guild_pessoal_grupo_002": {

        "id": "guild_pessoal_grupo_002",

        "nome": "Patrulha dos Novatos",

        "descricao": (
            "Aventureiros ainda pouco experientes podem "
            "aprender muito lutando lado a lado."
        ),

        "tipo": TIPO_PESSOAL,

        "modo": MODO_GRUPO,

        "nivel_minimo": 3,

        "ativa": True,

        "objetivo": {

            "tipo": OBJETIVO_MATAR_MOB,

            "regiao": "pradaria_inicial",

            "mob_ids":
                ids_mobs_regiao(
                    "pradaria_inicial"
                ),

            "quantidade": 12,

            "texto": (
                "Derrote 12 criaturas da Pradaria Inicial "
                "participando de um grupo."
            ),
        },

        "recompensas": {

            "xp": 120,

            "gold": 180,

            "pontos_guilda": 7,

            "xp_cla": 0,

            "itens": [
                {
                    "item_id": "pocao_cura_leve",
                    "quantidade": 2,
                }
            ],
        },

        "repetivel": False,
    },


    # ========================================================
    # 👤 PESSOAL + SOLO 003
    # ========================================================

    "guild_pessoal_solo_003": {

        "id": "guild_pessoal_solo_003",

        "nome": "Pedra e Sangue",

        "descricao": (
            "Os caminhos da Pedreira estão cada vez "
            "mais perigosos para mineradores e comerciantes."
        ),

        "tipo": TIPO_PESSOAL,

        "modo": MODO_SOLO,

        "nivel_minimo": 15,

        "ativa": True,

        "objetivo": {

            "tipo": OBJETIVO_MATAR_MOB,

            "regiao": "pedreira_granito",

            "mob_ids":
                ids_mobs_regiao(
                    "pedreira_granito"
                ),

            "quantidade": 15,

            "texto": (
                "Derrote 15 criaturas da Pedreira "
                "de Granito sem estar em grupo."
            ),
        },

        "recompensas": {

            "xp": 300,

            "gold": 380,

            "pontos_guilda": 14,

            "xp_cla": 0,

            "itens": [
                {
                    "item_id":
                        "pedra_de_aprimoramento",

                    "quantidade": 1,
                }
            ],
        },

        "repetivel": False,
    },


    # ========================================================
    # 👥 PESSOAL + GRUPO 003
    # ========================================================

    "guild_pessoal_grupo_003": {

        "id": "guild_pessoal_grupo_003",

        "nome": "Linha de Frente da Pedreira",

        "descricao": (
            "Algumas áreas da Pedreira exigem uma "
            "companhia inteira de aventureiros."
        ),

        "tipo": TIPO_PESSOAL,

        "modo": MODO_GRUPO,

        "nivel_minimo": 15,

        "ativa": True,

        "objetivo": {

            "tipo": OBJETIVO_MATAR_MOB,

            "regiao": "pedreira_granito",

            "mob_ids":
                ids_mobs_regiao(
                    "pedreira_granito"
                ),

            "quantidade": 20,

            "texto": (
                "Derrote 20 criaturas da Pedreira "
                "de Granito participando de um grupo."
            ),
        },

        "recompensas": {

            "xp": 420,

            "gold": 500,

            "pontos_guilda": 18,

            "xp_cla": 0,

            "itens": [
                {
                    "item_id":
                        "nucleo_de_forja",

                    "quantidade": 1,
                }
            ],
        },

        "repetivel": False,
    },


    # ========================================================
    # 🛡️ CLÃ + SOLO 002
    # ========================================================

    "guild_cla_solo_002": {

        "id": "guild_cla_solo_002",

        "nome": "Honra na Floresta",

        "descricao": (
            "Cada aventureiro carrega sozinho a honra "
            "do estandarte de seu clã."
        ),

        "tipo": TIPO_CLA,

        "modo": MODO_SOLO,

        "nivel_minimo": 10,

        "ativa": True,

        "objetivo": {

            "tipo": OBJETIVO_MATAR_MOB,

            "regiao": "floresta_sombria",

            "mob_ids":
                ids_mobs_regiao(
                    "floresta_sombria"
                ),

            "quantidade": 15,

            "texto": (
                "Derrote 15 criaturas da Floresta Sombria "
                "sem estar em grupo."
            ),
        },

        "recompensas": {

            "xp": 220,

            "gold": 280,

            "pontos_guilda": 10,

            "xp_cla": 120,

            "medalhas_cla": 5,

            "itens": [
                {
                    "item_id":
                        "pocao_cura_media",

                    "quantidade": 1,
                }
            ],
        },

        "repetivel": False,
    },


    # ========================================================
    # 🛡️ CLÃ + GRUPO 002
    # ========================================================

    "guild_cla_grupo_002": {

        "id": "guild_cla_grupo_002",

        "nome": "Matilha do Estandarte",

        "descricao": (
            "A Guilda recompensa clãs capazes de lutar "
            "como uma única unidade dentro da floresta."
        ),

        "tipo": TIPO_CLA,

        "modo": MODO_GRUPO,

        "nivel_minimo": 10,

        "ativa": True,

        "objetivo": {

            "tipo": OBJETIVO_MATAR_MOB,

            "regiao": "floresta_sombria",

            "mob_ids":
                ids_mobs_regiao(
                    "floresta_sombria"
                ),

            "quantidade": 20,

            "texto": (
                "Derrote 20 criaturas da Floresta Sombria "
                "participando de um grupo."
            ),
        },

        "recompensas": {

            "xp": 320,

            "gold": 400,

            "pontos_guilda": 15,

            "xp_cla": 200,

            "medalhas_cla": 8,

            "itens": [
                {
                    "item_id":
                        "pedra_de_aprimoramento",

                    "quantidade": 1,
                }
            ],
        },

        "repetivel": False,
    },    

    # ========================================================
    # 🏰 CLÃ COLETIVO + SEMANAL 001
    # ========================================================

    "guild_cla_coletiva_semanal_001": {

        "id":
            "guild_cla_coletiva_semanal_001",

        "nome":
            "A Grande Patrulha",

        "descricao": (
            "A Guilda convoca todos os membros "
            "do clã para proteger as rotas da "
            "Floresta Sombria durante esta semana."
        ),

        "tipo":
            TIPO_CLA,

        "escopo":
            ESCOPO_COLETIVO,

        "frequencia":
            FREQUENCIA_SEMANAL,

        # Solo OU grupo contam.
        "modo":
            MODO_QUALQUER,

        # Aqui é nível do CLÃ.
        "nivel_cla_minimo":
            1,

        "ativa":
            True,

        "objetivo": {

            "tipo":
                OBJETIVO_MATAR_MOB,

            "regiao":
                "floresta_sombria",

            "mob_ids":
                ids_mobs_regiao(
                    "floresta_sombria"
                ),

            "quantidade":
                100,

            "texto": (
                "O clã deve derrotar 100 criaturas "
                "da Floresta Sombria."
            ),
        },

        "recompensas": {

            "xp_cla":
                500,

            "ouro_cla":
                300,

            "pontos_cla":
                10,

            "medalhas_cla_participante":
                6,

            "min_contribuicao_medalhas":
                10,
        },
    }, 
    # ========================================================
    # ☀️ CLÃ COLETIVO + DIÁRIA 001
    # ========================================================

    "guild_cla_coletiva_diaria_001": {

        "id":
            "guild_cla_coletiva_diaria_001",

        "nome":
            "Ronda da Pradaria",

        "descricao": (
            "A Guilda solicita uma patrulha diária "
            "para manter seguras as rotas próximas "
            "à Capital de Eldora."
        ),

        "tipo":
            TIPO_CLA,

        "escopo":
            ESCOPO_COLETIVO,

        "frequencia":
            FREQUENCIA_DIARIA,

        "modo":
            MODO_QUALQUER,

        "nivel_cla_minimo":
            1,

        "ativa":
            True,

        "objetivo": {

            "tipo":
                OBJETIVO_MATAR_MOB,

            "regiao":
                "pradaria_inicial",

            "mob_ids":
                ids_mobs_regiao(
                    "pradaria_inicial"
                ),

            "quantidade":
                20,

            "texto": (
                "O clã deve derrotar 20 criaturas "
                "da Pradaria Inicial."
            ),
        },

        "recompensas": {

            "xp_cla":
                100,

            "ouro_cla":
                75,

            "pontos_cla":
                3,

            "medalhas_cla_participante":
                1,

            "min_contribuicao_medalhas":
                3,
        },
    },


    # ========================================================
    # ☀️ CLÃ COLETIVO + DIÁRIA 002
    # ========================================================

    "guild_cla_coletiva_diaria_002": {

        "id":
            "guild_cla_coletiva_diaria_002",

        "nome":
            "Vigília das Sombras",

        "descricao": (
            "Criaturas continuam rondando as trilhas "
            "da Floresta Sombria. A Guilda pede que "
            "os clãs mantenham vigilância diária."
        ),

        "tipo":
            TIPO_CLA,

        "escopo":
            ESCOPO_COLETIVO,

        "frequencia":
            FREQUENCIA_DIARIA,

        "modo":
            MODO_QUALQUER,

        "nivel_cla_minimo":
            1,

        "ativa":
            True,

        "objetivo": {

            "tipo":
                OBJETIVO_MATAR_MOB,

            "regiao":
                "floresta_sombria",

            "mob_ids":
                ids_mobs_regiao(
                    "floresta_sombria"
                ),

            "quantidade":
                25,

            "texto": (
                "O clã deve derrotar 25 criaturas "
                "da Floresta Sombria."
            ),
        },

        "recompensas": {

            "xp_cla":
                150,

            "ouro_cla":
                100,

            "pontos_cla":
                4,

            "medalhas_cla_participante":
                2,

            "min_contribuicao_medalhas":
                4,
        },
    },


    # ========================================================
    # ☀️ CLÃ COLETIVO + DIÁRIA 003
    # ========================================================

    "guild_cla_coletiva_diaria_003": {

        "id":
            "guild_cla_coletiva_diaria_003",

        "nome":
            "Turno dos Mineiros",

        "descricao": (
            "Mineradores pediram proteção para continuar "
            "trabalhando na Pedreira de Granito. "
            "A Guilda convocou os clãs da região."
        ),

        "tipo":
            TIPO_CLA,

        "escopo":
            ESCOPO_COLETIVO,

        "frequencia":
            FREQUENCIA_DIARIA,

        "modo":
            MODO_QUALQUER,

        "nivel_cla_minimo":
            2,

        "ativa":
            True,

        "objetivo": {

            "tipo":
                OBJETIVO_MATAR_MOB,

            "regiao":
                "pedreira_granito",

            "mob_ids":
                ids_mobs_regiao(
                    "pedreira_granito"
                ),

            "quantidade":
                25,

            "texto": (
                "O clã deve derrotar 25 criaturas "
                "da Pedreira de Granito."
            ),
        },

        "recompensas": {

            "xp_cla":
                200,

            "ouro_cla":
                140,

            "pontos_cla":
                5,

            "medalhas_cla_participante":
                2,

            "min_contribuicao_medalhas":
                4,
        },
    },


    # ========================================================
    # 🌙 CLÃ COLETIVO + SEMANAL 002
    # ========================================================

    "guild_cla_coletiva_semanal_002": {

        "id":
            "guild_cla_coletiva_semanal_002",

        "nome":
            "Cerco à Pedreira",

        "descricao": (
            "As rotas de minério precisam permanecer abertas. "
            "Durante esta semana, a Guilda recompensa os clãs "
            "que mantiverem a Pedreira sob controle."
        ),

        "tipo":
            TIPO_CLA,

        "escopo":
            ESCOPO_COLETIVO,

        "frequencia":
            FREQUENCIA_SEMANAL,

        "modo":
            MODO_QUALQUER,

        "nivel_cla_minimo":
            2,

        "ativa":
            True,

        "objetivo": {

            "tipo":
                OBJETIVO_MATAR_MOB,

            "regiao":
                "pedreira_granito",

            "mob_ids":
                ids_mobs_regiao(
                    "pedreira_granito"
                ),

            "quantidade":
                150,

            "texto": (
                "O clã deve derrotar 150 criaturas "
                "da Pedreira de Granito durante a semana."
            ),
        },

        "recompensas": {

            "xp_cla":
                750,

            "ouro_cla":
                500,

            "pontos_cla":
                15,

            "medalhas_cla_participante":
                8,

            "min_contribuicao_medalhas":
                15,
        },
    },


    # ========================================================
    # 🌙 CLÃ COLETIVO + SEMANAL 003
    # ========================================================

    "guild_cla_coletiva_semanal_003": {

        "id":
            "guild_cla_coletiva_semanal_003",

        "nome":
            "Companhia do Estandarte",

        "descricao": (
            "A Guilda quer ver os clãs lutando como uma "
            "verdadeira companhia de guerra. Nesta missão, "
            "somente abates realizados em grupo contam."
        ),

        "tipo":
            TIPO_CLA,

        "escopo":
            ESCOPO_COLETIVO,

        "frequencia":
            FREQUENCIA_SEMANAL,

        "modo":
            MODO_GRUPO,

        "nivel_cla_minimo":
            1,

        "ativa":
            True,

        "objetivo": {

            "tipo":
                OBJETIVO_MATAR_MOB,

            "regiao":
                "floresta_sombria",

            "mob_ids":
                ids_mobs_regiao(
                    "floresta_sombria"
                ),

            "quantidade":
                80,

            "texto": (
                "O clã deve derrotar 80 criaturas "
                "da Floresta Sombria em combates de grupo."
            ),
        },

        "recompensas": {

            "xp_cla":
                650,

            "ouro_cla":
                450,

            "pontos_cla":
                14,

            "medalhas_cla_participante":
                10,

            "min_contribuicao_medalhas":
                10,
        },
    },       
}


# ============================================================
# 🔎 CONSULTAS
# ============================================================
def _normalizar_missao(missao):
    """
    Garante compatibilidade com contratos antigos.

    Missões que ainda não possuem os novos campos
    são consideradas:

    escopo = individual
    frequencia = unica
    """

    if not isinstance(missao, dict):
        return None

    dados = deepcopy(missao)

    dados.setdefault(
        "escopo",
        ESCOPO_INDIVIDUAL,
    )

    dados.setdefault(
        "frequencia",
        FREQUENCIA_UNICA,
    )

    return dados

def obter_missao(missao_id):
    """
    Retorna uma cópia normalizada da missão.

    Contratos antigos recebem automaticamente:
    escopo = individual
    frequencia = unica
    """

    missao = GUILD_MISSIONS.get(
        str(missao_id or "")
    )

    if not missao:
        return None

    return _normalizar_missao(
        missao
    )

def listar_missoes_ativas(
    escopo=None,
):
    """
    Lista contratos atualmente liberados.

    Se escopo for informado:
        individual
        coletivo

    devolve somente aquele tipo.
    """

    resultado = []

    for missao_original in (
        GUILD_MISSIONS.values()
    ):

        missao = _normalizar_missao(
            missao_original
        )

        if not missao:
            continue

        if not missao.get(
            "ativa",
            True,
        ):
            continue

        if (
            escopo is not None
            and
            missao.get("escopo")
            != escopo
        ):
            continue

        resultado.append(
            missao
        )

    return resultado

# ============================================================
# 👹 VALIDAÇÃO DE MOBS
# ============================================================

def mob_existe_na_regiao(
    regiao,
    mob_id,
):
    """
    Confirma se um mob realmente existe naquela região
    dentro do MONSTERS_DATA.
    """

    mobs = MONSTERS_DATA.get(
        str(regiao or ""),
        [],
    )

    for mob in mobs:

        if str(mob.get("id")) == str(mob_id):
            return True

    return False


def validar_catalogo_missoes():
    """
    Detecta erro de digitação ao cadastrar uma missão.

    Exemplo:
    kobold_escavador -> existe
    kobold_escavdor  -> erro
    """

    erros = []

    for missao_id, missao in GUILD_MISSIONS.items():
        missao = _normalizar_missao(
            missao
        )        

        if missao.get("tipo") not in TIPOS_VALIDOS:

            erros.append(
                f"{missao_id}: tipo inválido."
            )

        if (
            missao.get("escopo")
            not in ESCOPOS_VALIDOS
        ):

            erros.append(
                f"{missao_id}: escopo inválido."
            )


        if (
            missao.get("frequencia")
            not in FREQUENCIAS_VALIDAS
        ):

            erros.append(
                f"{missao_id}: frequência inválida."
            )

        if missao.get("modo") not in MODOS_VALIDOS:

            erros.append(
                f"{missao_id}: modo inválido."
            )

        objetivo = (
            missao.get("objetivo", {})
            or {}
        )

        regiao = objetivo.get("regiao")

        if regiao not in REGIOES_GUILDA:

            erros.append(
                f"{missao_id}: região inválida "
                f"({regiao})."
            )

            continue

        for mob_id in objetivo.get(
            "mob_ids",
            [],
        ):

            if not mob_existe_na_regiao(
                regiao,
                mob_id,
            ):

                erros.append(
                    f"{missao_id}: mob "
                    f"'{mob_id}' não existe em "
                    f"'{regiao}'."
                )

    return erros