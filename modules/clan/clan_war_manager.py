# ============================================================
# ⚔️ MUNDO DE ELDORA - GERENCIADOR DA GUERRA DE CLÃS
# ============================================================

from __future__ import annotations

from datetime import (
    datetime,
    timezone,
    timedelta,
)

from zoneinfo import ZoneInfo

from bson import ObjectId

from pymongo import (
    ReturnDocument,
)

from pymongo.errors import (
    DuplicateKeyError,
    PyMongoError,
)

from modules.player.core import (
    db,
    users_collection,
)

from modules.clan import (
    clan_manager,
)

from .clan_war_registry import (

    CLAN_WAR_SCHEMA_VERSION,

    GUERRA_TIPO_OFICIAL,

    GUERRA_STATUS_INSCRICOES,
    GUERRA_STATUS_ESCALACAO,
    GUERRA_STATUS_PAREAMENTO,
    GUERRA_STATUS_AGENDADA,
    GUERRA_STATUS_EM_ANDAMENTO,
    GUERRA_STATUS_FINALIZADA,
    GUERRA_STATUS_CANCELADA,
    GUERRA_SEMANAL_TIMEZONE,
    CALENDARIO_GUERRA_SEMANAL,
    GUERRA_MINIMO_JOGADORES_POR_CLA,

    GUERRA_PONTOS_VITORIA,
    GUERRA_PONTOS_EMPATE,
    GUERRA_PONTOS_DERROTA,

    GUERRA_RATING_INICIAL,

    obter_categoria_efetiva,
    obter_categoria_maxima_por_nivel,
    obter_config_categoria,
)


# ============================================================
# 🗄️ COLEÇÃO
# ============================================================

clan_wars_collection = db[
    "clan_wars"
]

# ============================================================
# 🧪 CONTROLE GM DA GUERRA
# ============================================================

clan_war_admin_collection = db[
    "clan_war_admin"
]


CLAN_WAR_ADMIN_DOC_ID = (
    "guerra_oficial_controle"
)

# ============================================================
# 📄 TIPOS DE DOCUMENTO
# ============================================================
#
# Usaremos uma única coleção:
#
# clan_wars
#
# mas ela poderá armazenar:
#
# inscricao = clã inscrito naquela semana
# guerra    = confronto já formado
#
# Nesta primeira etapa criamos apenas
# documentos "inscricao".
# ============================================================

WAR_DOC_INSCRICAO = (
    "inscricao"
)

WAR_DOC_GUERRA = (
    "guerra"
)

# ============================================================
# 👥 QUÓRUM DA GUERRA
# ============================================================

QUORUM_STATUS_EM_FORMACAO = (
    "em_formacao"
)

QUORUM_STATUS_APROVADO = (
    "aprovado"
)

QUORUM_STATUS_SEM_QUORUM = (
    "sem_quorum"
)

QUORUM_STATUS_CANCELADO = (
    "cancelado"
)

# ============================================================
# 🧪 MODO DE TESTE DA GUERRA
# ============================================================
#
# True:
# permite inscrever clã e guerreiros
# mesmo fora do período oficial.
#
# Antes de liberar o sistema:
# trocar para False.
# ============================================================

GUERRA_MODO_TESTE = False

# ============================================================
# 🔧 HELPERS
# ============================================================

def _agora():
    return datetime.now(
        timezone.utc
    )


def _object_id(
    valor,
):
    if isinstance(
        valor,
        ObjectId,
    ):
        return valor


    if valor is None:
        return None


    texto = str(
        valor
    ).strip()


    if not ObjectId.is_valid(
        texto
    ):
        return None


    return ObjectId(
        texto
    )


def _json_seguro(
    valor,
):
    if isinstance(
        valor,
        ObjectId,
    ):
        return str(
            valor
        )


    if isinstance(
        valor,
        datetime,
    ):
        return valor.isoformat()


    if isinstance(
        valor,
        dict,
    ):
        return {

            chave:
                _json_seguro(
                    item
                )

            for (
                chave,
                item
            )
            in valor.items()
        }


    if isinstance(
        valor,
        list,
    ):
        return [

            _json_seguro(
                item
            )

            for item
            in valor
        ]


    return valor

# ============================================================
# 🧪 CONTROLE DE TESTE GM
# ============================================================

FASES_TESTE_GUERRA = {
    GUERRA_STATUS_INSCRICOES,
    GUERRA_STATUS_ESCALACAO,
    GUERRA_STATUS_PAREAMENTO,
    GUERRA_STATUS_AGENDADA,
    GUERRA_STATUS_EM_ANDAMENTO,
    GUERRA_STATUS_FINALIZADA,
}


def obter_controle_teste_guerra():
    """
    Retorna o controle administrativo
    da Guerra de Clãs.

    Se não existir, significa que o
    calendário real está ativo.
    """

    controle = (
        clan_war_admin_collection
        .find_one({
            "_id":
                CLAN_WAR_ADMIN_DOC_ID
        })
    )


    if not controle:

        return {
            "modo_teste":
                False,

            "fase_forcada":
                None,

            "alterado_em":
                None,

            "alterado_por":
                None,
        }


    return {
        "modo_teste":
            bool(
                controle.get(
                    "modo_teste"
                )
            ),

        "fase_forcada":
            controle.get(
                "fase_forcada"
            ),

        "alterado_em":
            controle.get(
                "alterado_em"
            ),

        "alterado_por":
            controle.get(
                "alterado_por"
            ),
    }


def definir_fase_teste_guerra(
    fase,
    alterado_por="GM",
):
    """
    Força temporariamente uma fase
    da Guerra Semanal.

    O calendário oficial não é alterado.
    """

    fase = str(
        fase or ""
    ).strip()


    if (
        fase
        not in
        FASES_TESTE_GUERRA
    ):

        return {
            "success":
                False,

            "error":
                "Fase de teste inválida.",
        }


    agora = _agora()


    clan_war_admin_collection.update_one(
        {
            "_id":
                CLAN_WAR_ADMIN_DOC_ID
        },

        {
            "$set": {
                "modo_teste":
                    True,

                "fase_forcada":
                    fase,

                "alterado_em":
                    agora,

                "alterado_por":
                    str(
                        alterado_por
                        or
                        "GM"
                    ),
            }
        },

        upsert=True,
    )


    return {
        "success":
            True,

        "modo_teste":
            True,

        "fase_forcada":
            fase,

        "message":
            (
                "Fase da Guerra alterada "
                f"para '{fase}'."
            ),
    }


def desativar_teste_guerra(
    alterado_por="GM",
):
    """
    Remove a fase forçada e devolve
    a Guerra ao calendário real.
    """

    agora = _agora()


    clan_war_admin_collection.update_one(
        {
            "_id":
                CLAN_WAR_ADMIN_DOC_ID
        },

        {
            "$set": {
                "modo_teste":
                    False,

                "fase_forcada":
                    None,

                "alterado_em":
                    agora,

                "alterado_por":
                    str(
                        alterado_por
                        or
                        "GM"
                    ),
            }
        },

        upsert=True,
    )


    return {
        "success":
            True,

        "modo_teste":
            False,

        "fase_forcada":
            None,

        "message":
            (
                "A Guerra voltou ao "
                "calendário oficial."
            ),
    }

# ============================================================
# ⚔️ SINCRONIZAR STATUS REAL DAS GUERRAS
# ============================================================

def sincronizar_status_guerras_semana(
    calendario=None,
):
    """
    Mantém o documento WAR_DOC_GUERRA
    alinhado com a fase operacional
    do calendário.

    Não finaliza a guerra automaticamente.
    A finalização precisa vir do resultado
    das frentes.
    """

    calendario = (
        calendario
        or
        obter_estado_calendario()
    )


    semana_id = str(
        calendario.get(
            "semana_id",
            ""
        )
    ).strip()


    fase = str(
        calendario.get(
            "fase",
            ""
        )
    ).strip()


    if not semana_id:

        return {
            "success":
                False,

            "alteradas":
                0,
        }


    if fase not in {
        GUERRA_STATUS_AGENDADA,
        GUERRA_STATUS_EM_ANDAMENTO,
    }:

        return {
            "success":
                True,

            "alteradas":
                0,

            "fase":
                fase,
        }


    agora = _agora()


    resultado = (
        clan_wars_collection
        .update_many(

            {
                "tipo_documento":
                    WAR_DOC_GUERRA,

                "semana_id":
                    semana_id,

                "status": {
                    "$nin": [
                        GUERRA_STATUS_FINALIZADA,
                        GUERRA_STATUS_CANCELADA,
                    ]
                },
            },

            {
                "$set": {
                    "status":
                        fase,

                    "atualizado_em":
                        agora,
                }
            },
        )
    )


    clan_wars_collection.update_many(

        {
            "tipo_documento":
                WAR_DOC_INSCRICAO,

            "semana_id":
                semana_id,

            "matchmaking.processado":
                True,

            "status": {
                "$nin": [
                    GUERRA_STATUS_FINALIZADA,
                    GUERRA_STATUS_CANCELADA,
                ]
            },
        },

        {
            "$set": {
                "status":
                    fase,

                "atualizado_em":
                    agora,
            }
        },
    )


    return {
        "success":
            True,

        "alteradas":
            resultado.modified_count,

        "status":
            fase,
    }
    
# ============================================================
# 🌎 FUSO HORÁRIO
# ============================================================

def _timezone_guerra():
    return ZoneInfo(
        GUERRA_SEMANAL_TIMEZONE
    )


def _agora_local(
    agora=None,
):
    tz = (
        _timezone_guerra()
    )


    if agora is None:

        return (
            _agora()
            .astimezone(
                tz
            )
        )


    if not isinstance(
        agora,
        datetime,
    ):
        return (
            _agora()
            .astimezone(
                tz
            )
        )


    if agora.tzinfo is None:

        agora = agora.replace(
            tzinfo=timezone.utc
        )


    return agora.astimezone(
        tz
    )


# ============================================================
# 📅 SEMANA DA GUERRA
# ============================================================

def obter_semana_id(
    agora=None,
):
    """
    Exemplo:

    2026-W34
    """

    local = (
        _agora_local(
            agora
        )
    )


    calendario_iso = (
        local.isocalendar()
    )


    return (
        f"{calendario_iso.year}"
        f"-W"
        f"{calendario_iso.week:02d}"
    )


def _inicio_semana_local(
    agora=None,
):
    local = (
        _agora_local(
            agora
        )
    )


    segunda = (
        local
        -
        timedelta(
            days=local.weekday()
        )
    )


    return segunda.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )


def _momento_calendario(
    chave,
    agora=None,
):
    config = (
        CALENDARIO_GUERRA_SEMANAL
        .get(
            chave,
            {}
        )
        or {}
    )


    segunda = (
        _inicio_semana_local(
            agora
        )
    )


    dia = int(
        config.get(
            "dia_semana",
            0,
        )
        or 0
    )


    hora = int(
        config.get(
            "hora",
            0,
        )
        or 0
    )


    minuto = int(
        config.get(
            "minuto",
            0,
        )
        or 0
    )


    momento = (
        segunda
        +
        timedelta(
            days=dia
        )
    )


    return momento.replace(
        hour=hora,
        minute=minuto,
        second=0,
        microsecond=0,
    )


# ============================================================
# 📅 ESTADO DA SEMANA
# ============================================================

def obter_estado_calendario(
    agora=None,
):
    """
    Calcula automaticamente a fase
    atual da Guerra Semanal.
    """

    local = (
        _agora_local(
            agora
        )
    )


    inscricoes_abrem = (
        _momento_calendario(
            "inscricoes_abrem",
            local,
        )
    )


    inscricoes_fecham = (
        _momento_calendario(
            "inscricoes_fecham",
            local,
        )
    )


    escalacoes_travam = (
        _momento_calendario(
            "escalacoes_travam",
            local,
        )
    )


    pareamento = (
        _momento_calendario(
            "pareamento",
            local,
        )
    )


    guerra_abre = (
        _momento_calendario(
            "guerra_abre",
            local,
        )
    )


    guerra_fecha = (
        _momento_calendario(
            "guerra_fecha",
            local,
        )
    )


    # ========================================================
    # FASE
    # ========================================================

    if (
        local
        <
        inscricoes_abrem
    ):

        fase = (
            GUERRA_STATUS_FINALIZADA
        )


    # ========================================================
    # 📝 INSCRIÇÕES
    # ========================================================

    elif (
        local
        <
        inscricoes_fecham
    ):

        fase = (
            GUERRA_STATUS_INSCRICOES
        )


    # ========================================================
    # 🔒 ESCALAÇÃO
    #
    # Depois que as inscrições fecham,
    # o clã entra na fase de escalação.
    #
    # A escalação permanece disponível
    # até o início do pareamento.
    # ========================================================

    elif (
        local
        <
        pareamento
    ):

        fase = (
            GUERRA_STATUS_ESCALACAO
        )


    # ========================================================
    # ⚖️ PAREAMENTO CONCLUÍDO / GUERRA AGENDADA
    # ========================================================

    elif (
        local
        <
        guerra_abre
    ):

        fase = (
            GUERRA_STATUS_AGENDADA
        )


    # ========================================================
    # ⚔️ GUERRA EM ANDAMENTO
    # ========================================================

    elif (
        local
        <
        guerra_fecha
    ):

        fase = (
            GUERRA_STATUS_EM_ANDAMENTO
        )


    # ========================================================
    # 🏆 GUERRA ENCERRADA
    # ========================================================

    else:

        fase = (
            GUERRA_STATUS_FINALIZADA
        )

    # ========================================================
    # 🧪 SOBRESCRITA GM
    # ========================================================

    fase_real = fase


    controle_teste = (
        obter_controle_teste_guerra()
    )


    modo_teste = bool(
        controle_teste.get(
            "modo_teste"
        )
    )


    fase_forcada = (
        controle_teste.get(
            "fase_forcada"
        )
    )


    if (
        modo_teste
        and
        fase_forcada
        in
        FASES_TESTE_GUERRA
    ):

        fase = (
            fase_forcada
        )

    return {

        "semana_id":
            obter_semana_id(
                local
            ),

        "timezone":
            GUERRA_SEMANAL_TIMEZONE,

        "fase":
            fase,

        "fase_real":
            fase_real,

        "modo_teste":
            modo_teste,

        "fase_forcada":
            (
                fase_forcada
                if modo_teste
                else None
            ),

        "inscricoes_abertas":
            (
                fase
                ==
                GUERRA_STATUS_INSCRICOES
            ),

        "escalacao_aberta":
            (
                fase
                ==
                GUERRA_STATUS_ESCALACAO
            ),

        "agora":
            local,

        "inscricoes_abrem":
            inscricoes_abrem,

        "inscricoes_fecham":
            inscricoes_fecham,

        "escalacoes_travam":
            escalacoes_travam,

        "pareamento":
            pareamento,

        "guerra_abre":
            guerra_abre,

        "guerra_fecha":
            guerra_fecha,
    }

# ============================================================
# 🔓 GM — DESTRAVAR ESCALAÇÕES DA SEMANA
# ============================================================

def gm_destravar_escalacoes(
    semana_id=None,
):
    """
    Destrava as escalações da semana,
    preservando os participantes inscritos.

    Usado exclusivamente para testes.
    """

    semana_id = str(
        semana_id
        or
        obter_semana_id()
    ).strip()


    agora = _agora()


    resultado = (
        clan_wars_collection
        .update_many(

            {
                "tipo_documento":
                    WAR_DOC_INSCRICAO,

                "semana_id":
                    semana_id,
            },

            {
                "$set": {

                    "escalacao.travada":
                        False,

                    "escalacao.travada_em":
                        None,

                    "escalacao.confirmada_por":
                        None,

                    "escalacao.categoria":
                        None,

                    "escalacao.categoria_nome":
                        None,

                    "escalacao.titulares_total":
                        0,

                    "escalacao.reservas_total":
                        0,

                    "escalacao.jogadores":
                        [],

                    "escalacao.reservas":
                        [],

                    "matchmaking.processado":
                        False,

                    "matchmaking.processado_em":
                        None,

                    "matchmaking.guerra_id":
                        None,

                    "atualizado_em":
                        agora,
                },

                "$push": {

                    "historico": {

                        "tipo":
                            "gm_escalacao_destravada",

                        "mensagem":
                            (
                                "A escalação foi "
                                "destravada pelo GM "
                                "para testes."
                            ),

                        "autor_id":
                            None,

                        "criado_em":
                            agora,
                    }
                },
            },
        )
    )


    return {
        "success":
            True,

        "semana_id":
            semana_id,

        "clans_afetados":
            resultado.modified_count,

        "message":
            (
                f"{resultado.modified_count} "
                "escalações foram destravadas."
            ),
    }

# ============================================================
# 🔄 GM — REINICIAR BATALHA DE UMA FRENTE
# ============================================================

def gm_reiniciar_batalha_frente(
    user_id,
    semana_id=None,
    alterado_por="GM",
):
    """
    Reinicia SOMENTE a batalha da frente
    onde o jogador titular está escalado.

    Preserva:
    - guerra;
    - pareamento;
    - titulares;
    - reservas;
    - lobby;
    - presentes;
    - jogadores PRONTOS.

    Reinicia:
    - HP;
    - MP;
    - cooldowns;
    - rodada;
    - turnos;
    - log;
    - vencedor da batalha.
    """

    player_id = _object_id(
        user_id
    )


    if not player_id:

        return {
            "success": False,
            "error":
                "Jogador inválido.",
        }


    # ========================================================
    # 🏰 CLÃ ATUAL
    # ========================================================

    cla = (
        clan_manager
        .obter_cla_do_jogador(
            player_id
        )
    )


    if not cla:

        return {
            "success": False,
            "error":
                "O jogador não pertence a um clã.",
        }


    clan_id = cla["_id"]


    # ========================================================
    # 📅 SEMANA
    # ========================================================

    semana_id = str(
        semana_id
        or
        obter_semana_id()
    ).strip()


    # ========================================================
    # ⚔️ GUERRA DO CLÃ
    # ========================================================

    guerra = (
        obter_guerra_cla(
            clan_id=
                clan_id,

            semana_id=
                semana_id,
        )
    )


    if not guerra:

        return {
            "success": False,
            "error":
                "Nenhuma Guerra foi encontrada "
                "para este jogador nesta semana.",
        }


    status_guerra = str(
        guerra.get(
            "status",
            ""
        )
        or ""
    ).strip()


    if status_guerra not in {
        GUERRA_STATUS_EM_ANDAMENTO,
        GUERRA_STATUS_FINALIZADA,
    }:

        return {
            "success": False,

            "error":
                (
                    "A Guerra precisa estar "
                    "em andamento ou finalizada "
                    "para reiniciar uma batalha "
                    "de teste."
                ),

            "status":
                status_guerra,
        }


    # ========================================================
    # 🛡️ FRENTE DO JOGADOR
    # ========================================================

    frente = (
        _localizar_frente_jogador(
            guerra=
                guerra,

            clan_id=
                clan_id,

            player_id=
                player_id,
        )
    )


    if not frente:

        return {
            "success": False,

            "error":
                (
                    "O jogador informado não é "
                    "titular de nenhuma frente "
                    "desta Guerra."
                ),
        }


    try:

        numero_frente = int(
            frente.get(
                "numero",
                0
            )
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):

        numero_frente = 0


    if numero_frente <= 0:

        return {
            "success": False,
            "error":
                "Número da frente inválido.",
        }


    # ========================================================
    # ✅ LOBBY PRECISA CONTINUAR PRONTO
    # ========================================================

    lobby = (
        frente.get(
            "lobby",
            {}
        )
        or {}
    )


    if (
        lobby.get(
            "estado"
        )
        !=
        "pronta_para_combate"
    ):

        return {
            "success": False,

            "error":
                (
                    "Esta frente ainda não possui "
                    "os jogadores PRONTOS para "
                    "recriar a batalha."
                ),
        }


    agora = _agora()


    # ========================================================
    # 🗑️ REMOVE SOMENTE A BATALHA ANTIGA
    # ========================================================

    resultado_reset = (
        clan_wars_collection
        .update_one(

            {
                "_id":
                    guerra["_id"],

                "frentes.numero":
                    numero_frente,
            },

            {
                "$unset": {

                    "frentes.$.batalha":
                        "",
                },

                "$set": {

                    # ========================================
                    # ⚔️ REABRE A GUERRA PARA TESTE
                    # ========================================

                    "status":
                        GUERRA_STATUS_EM_ANDAMENTO,

                    "resultado.vencedor_clan_id":
                        None,

                    "resultado.perdedor_clan_id":
                        None,

                    "resultado.empate":
                        False,

                    "resultado.frentes_clan_a":
                        0,

                    "resultado.frentes_clan_b":
                        0,

                    "resultado.finalizada_em":
                        None,

                    # ========================================
                    # 🔄 REINICIA SOMENTE ESTA FRENTE
                    # ========================================

                    "frentes.$.status":
                        GUERRA_STATUS_EM_ANDAMENTO,

                    "frentes.$.resultado.vencedor_clan_id":
                        None,

                    "frentes.$.resultado.finalizada_em":
                        None,

                    "atualizado_em":
                        agora,
                },

                "$push": {

                    "historico": {

                        "tipo":
                            "gm_batalha_frente_reiniciada",

                        "mensagem":
                            (
                                f"A batalha da Frente "
                                f"{numero_frente} foi "
                                "reiniciada pelo GM "
                                "para testes."
                            ),

                        "autor":
                            str(
                                alterado_por
                                or
                                "GM"
                            ),

                        "criado_em":
                            agora,
                    }
                },
            },
        )
    )


    if (
        resultado_reset.matched_count
        != 1
    ):

        return {
            "success": False,

            "error":
                (
                    "Não foi possível localizar "
                    "a frente para reiniciar."
                ),
        }

    # ========================================================
    # 📄 REABRE AS INSCRIÇÕES PARA O TESTE
    # ========================================================

    clan_wars_collection.update_many(

        {
            "tipo_documento":
                WAR_DOC_INSCRICAO,

            "semana_id":
                semana_id,

            "matchmaking.guerra_id":
                guerra["_id"],

            "status": {
                "$ne":
                    GUERRA_STATUS_CANCELADA
            },
        },

        {
            "$set": {

                "status":
                    GUERRA_STATUS_EM_ANDAMENTO,

                "atualizado_em":
                    agora,
            }
        },
    )

    # ========================================================
    # ⚔️ CRIA NOVAMENTE A BATALHA
    # ========================================================

    from modules.clan import (
        clan_war_battle_engine,
    )


    resultado_batalha = (
        clan_war_battle_engine
        .garantir_batalha_inicial(

            guerra_id=
                guerra["_id"],

            numero_frente=
                numero_frente,
        )
    )


    if not resultado_batalha.get(
        "success"
    ):

        return {
            "success": False,

            "error":
                (
                    "A batalha antiga foi removida, "
                    "mas a nova batalha não pôde "
                    "ser criada: "
                    +
                    str(
                        resultado_batalha.get(
                            "error",
                            "erro desconhecido",
                        )
                    )
                ),
        }

    # ========================================================
    # 📊 RECALCULA O PLACAR DAS OUTRAS FRENTES
    # ========================================================

    resultado_geral = (
        consolidar_resultado_guerra(
            guerra["_id"]
        )
    )


    if not resultado_geral.get(
        "success"
    ):

        return {
            "success": False,

            "error":
                (
                    "A batalha foi reiniciada, "
                    "mas o placar geral não pôde "
                    "ser recalculado: "
                    +
                    str(
                        resultado_geral.get(
                            "error",
                            "erro desconhecido",
                        )
                    )
                ),
        }
    
    return {
        "success": True,

        "guerra_id":
            str(
                guerra["_id"]
            ),

        "frente_numero":
            numero_frente,

        "message":
            (
                f"Frente {numero_frente} "
                "reiniciada com sucesso! "
                "A batalha está novamente pronta."
            ),
    }

# ============================================================
# 🗃️ ÍNDICES
# ============================================================

def garantir_indices():
    """
    Cria os índices necessários.

    Uma falha aqui não deve derrubar
    todo o servidor.
    """

    try:

        # Um mesmo clã só pode ter
        # uma inscrição oficial
        # naquela semana.
        clan_wars_collection.create_index(
            [
                (
                    "tipo_documento",
                    1,
                ),
                (
                    "semana_id",
                    1,
                ),
                (
                    "clan_id",
                    1,
                ),
            ],

            unique=True,

            partialFilterExpression={
                "tipo_documento":
                    WAR_DOC_INSCRICAO,
            },

            name=(
                "clan_war_inscricao_"
                "semanal_unica"
            ),
        )


        clan_wars_collection.create_index(
            [
                (
                    "tipo_documento",
                    1,
                ),
                (
                    "semana_id",
                    1,
                ),
                (
                    "status",
                    1,
                ),
            ],

            name=(
                "clan_war_semana_status"
            ),
        )


        clan_wars_collection.create_index(
            [
                (
                    "clan_id",
                    1,
                ),
                (
                    "criado_em",
                    -1,
                ),
            ],

            name=(
                "clan_war_historico_cla"
            ),
        )

        # Um jogador só pode representar
        # um único clã por semana.
        clan_wars_collection.create_index(
            [
                (
                    "semana_id",
                    1,
                ),
                (
                    "participantes.user_id",
                    1,
                ),
            ],

            unique=True,

            partialFilterExpression={
                "tipo_documento":
                    WAR_DOC_INSCRICAO,

                "participantes.user_id": {
                    "$exists": True,
                },
            },

            name=(
                "clan_war_participante_"
                "semanal_unico"
            ),
        )        

        # ====================================================
        # ⚔️ UM CLÃ SÓ PODE TER UMA GUERRA POR SEMANA
        # ====================================================

        clan_wars_collection.create_index(
            [
                (
                    "tipo_documento",
                    1,
                ),
                (
                    "semana_id",
                    1,
                ),
                (
                    "clans_ids",
                    1,
                ),
            ],

            unique=True,

            partialFilterExpression={
                "tipo_documento":
                    WAR_DOC_GUERRA,

                "clans_ids": {
                    "$exists": True,
                },
            },

            name=(
                "clan_war_guerra_"
                "clan_semanal_unico"
            ),
        )

    except Exception as erro:

        print(
            "⚠️ [GUERRA DE CLÃS] "
            "Não foi possível garantir "
            f"os índices: {erro}"
        )


# ============================================================
# 🔎 INSCRIÇÃO DA SEMANA
# ============================================================

def obter_inscricao_cla(
    clan_id,
    semana_id=None,
):
    clan_id = (
        _object_id(
            clan_id
        )
    )


    if not clan_id:
        return None


    semana_id = str(
        semana_id
        or
        obter_semana_id()
    ).strip()


    return (
        clan_wars_collection
        .find_one({
            "tipo_documento":
                WAR_DOC_INSCRICAO,

            "semana_id":
                semana_id,

            "clan_id":
                clan_id,
        })
    )

# ============================================================
# ⚔️ GUERRA FORMADA DO CLÃ
# ============================================================

def obter_guerra_cla(
    clan_id,
    semana_id=None,
):
    clan_id = (
        _object_id(
            clan_id
        )
    )


    if not clan_id:
        return None


    semana_id = str(
        semana_id
        or
        obter_semana_id()
    ).strip()


    return (
        clan_wars_collection
        .find_one({
            "tipo_documento":
                WAR_DOC_GUERRA,

            "semana_id":
                semana_id,

            "clans_ids":
                clan_id,
        })
    )


def _obter_adversario_guerra(
    guerra,
    clan_id,
):
    if not guerra:
        return None


    clan_id = (
        _object_id(
            clan_id
        )
    )


    for lado in (
        guerra.get(
            "clans",
            []
        )
        or []
    ):

        if (
            _object_id(
                lado.get(
                    "clan_id"
                )
            )
            !=
            clan_id
        ):

            return lado


    return None

# ============================================================
# 🏰 LADO DO CLÃ NA GUERRA
# ============================================================

def _obter_lado_cla_guerra(
    guerra,
    clan_id,
):
    if not guerra:
        return None


    clan_id = _object_id(
        clan_id
    )


    if not clan_id:
        return None


    for lado in (
        guerra.get(
            "clans",
            []
        )
        or []
    ):

        if (
            _object_id(
                lado.get(
                    "clan_id"
                )
            )
            ==
            clan_id
        ):

            return lado


    return None


# ============================================================
# ⚔️ LOCALIZAR FRENTE DO JOGADOR
# ============================================================

def _localizar_frente_jogador(
    guerra,
    clan_id,
    player_id,
):
    if not guerra:
        return None


    clan_id = _object_id(
        clan_id
    )


    player_id = _object_id(
        player_id
    )


    if (
        not clan_id
        or
        not player_id
    ):

        return None


    for frente in (
        guerra.get(
            "frentes",
            []
        )
        or []
    ):

        for chave_lado in (
            "clan_a",
            "clan_b",
        ):

            lado = (
                frente.get(
                    chave_lado,
                    {}
                )
                or {}
            )


            if (
                _object_id(
                    lado.get(
                        "clan_id"
                    )
                )
                !=
                clan_id
            ):

                continue


            jogadores = (
                lado.get(
                    "jogadores",
                    []
                )
                or []
            )


            for jogador in jogadores:

                if (
                    _object_id(
                        jogador.get(
                            "user_id"
                        )
                    )
                    ==
                    player_id
                ):

                    return frente


    return None

# ============================================================
# 🚪 ENTRAR NO LOBBY DA FRENTE
# ============================================================

def entrar_lobby_frente_guerra(
    user_id,
):
    """
    Registra um titular como presente
    no lobby da sua própria frente.

    O servidor valida novamente:
    - jogador;
    - clã;
    - guerra;
    - fase;
    - titularidade;
    - frente correta;
    - frente não finalizada.

    O frontend não informa qual frente
    o jogador deseja entrar.
    O backend descobre sozinho.
    """

    # ========================================================
    # 👤 JOGADOR
    # ========================================================

    player_id = _object_id(
        user_id
    )


    if not player_id:

        return {
            "success": False,
            "error": "ID de jogador inválido.",
        }


    # ========================================================
    # 🏰 CLÃ ATUAL
    # ========================================================

    cla = (
        clan_manager
        .obter_cla_do_jogador(
            player_id
        )
    )


    if not cla:

        return {
            "success": False,
            "error": (
                "Você não pertence "
                "a um clã."
            ),
        }


    clan_id = cla[
        "_id"
    ]


    # ========================================================
    # 📅 FASE OFICIAL UTILIZADA
    # ========================================================

    calendario = (
        obter_estado_calendario()
    )


    sincronizar_status_guerras_semana(
        calendario
    )


    if (
        calendario.get(
            "fase"
        )
        !=
        GUERRA_STATUS_EM_ANDAMENTO
    ):

        return {
            "success": False,
            "error": (
                "A Guerra de Clãs não está "
                "em andamento neste momento."
            ),
        }


    # ========================================================
    # ⚔️ GUERRA DO CLÃ
    # ========================================================

    guerra = (
        obter_guerra_cla(
            clan_id=
                clan_id,

            semana_id=
                calendario.get(
                    "semana_id"
                ),
        )
    )


    if not guerra:

        return {
            "success": False,
            "error": (
                "Nenhum confronto foi "
                "encontrado para seu clã."
            ),
        }


    if (
        guerra.get(
            "status"
        )
        !=
        GUERRA_STATUS_EM_ANDAMENTO
    ):

        return {
            "success": False,
            "error": (
                "Este confronto ainda não "
                "está liberado para entrada."
            ),
        }


    # ========================================================
    # 🛡️ FRENTE DO PRÓPRIO JOGADOR
    # ========================================================

    frente = (
        _localizar_frente_jogador(
            guerra=
                guerra,

            clan_id=
                clan_id,

            player_id=
                player_id,
        )
    )

    #Apenas titulares aparecem dentro
    #de clan_a.jogadores / clan_b.jogadores
    #das frentes.

    if not frente:

        return {
            "success": False,
            "error": (
                "Somente jogadores titulares "
                "podem entrar nas frentes "
                "desta guerra."
            ),
        }


    if (
        frente.get(
            "status"
        )
        ==
        GUERRA_STATUS_FINALIZADA
    ):

        return {
            "success": False,
            "error": (
                "Esta frente já foi finalizada."
            ),
        }


    try:

        numero_frente = int(
            frente.get(
                "numero"
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        return {
            "success": False,
            "error": (
                "A frente do jogador "
                "possui identificação inválida."
            ),
        }


    # ========================================================
    # 👥 VERIFICA SE JÁ ESTAVA PRESENTE
    # ========================================================

    lobby_atual = (
        frente.get(
            "lobby",
            {}
        )
        or {}
    )


    presentes_antes = {
        _object_id(
            valor
        )

        for valor
        in (
            lobby_atual.get(
                "presentes_ids",
                []
            )
            or []
        )

        if _object_id(
            valor
        )
    }


    ja_estava_presente = (
        player_id
        in
        presentes_antes
    )


    # ========================================================
    # 🚪 REGISTRA PRESENÇA
    #
    # $addToSet impede duplicação caso
    # o jogador clique novamente.
    # ========================================================

    agora = _agora()


    resultado = (
        clan_wars_collection
        .update_one(

            {
                "_id":
                    guerra["_id"],

                "frentes": {
                    "$elemMatch": {

                        "numero":
                            numero_frente,

                        "status": {
                            "$ne":
                                GUERRA_STATUS_FINALIZADA
                        },
                    }
                },
            },

            {
                "$addToSet": {

                    "frentes.$.lobby.presentes_ids":
                        player_id,
                },

                "$set": {

                    "frentes.$.lobby.atualizado_em":
                        agora,

                    "atualizado_em":
                        agora,
                },
            },
        )
    )


    if (
        resultado.matched_count
        == 0
    ):

        return {
            "success": False,
            "error": (
                "Não foi possível entrar "
                "nesta frente."
            ),
        }


    # ========================================================
    # 🔄 LÊ NOVAMENTE O ESTADO REAL
    # ========================================================

    guerra_atualizada = (
        clan_wars_collection
        .find_one({
            "_id":
                guerra["_id"]
        })
        or {}
    )


    frente_atualizada = next(
        (
            item

            for item
            in (
                guerra_atualizada.get(
                    "frentes",
                    []
                )
                or []
            )

            if int(
                item.get(
                    "numero",
                    0
                )
                or 0
            )
            ==
            numero_frente
        ),

        None,
    )


    if not frente_atualizada:

        return {
            "success": False,
            "error": (
                "A frente não foi encontrada "
                "após registrar a entrada."
            ),
        }


    lobby = (
        frente_atualizada.get(
            "lobby",
            {}
        )
        or {}
    )


    presentes_ids = (
        lobby.get(
            "presentes_ids",
            []
        )
        or []
    )


    jogadores_total = (
        len(
            (
                frente_atualizada
                .get(
                    "clan_a",
                    {}
                )
                .get(
                    "jogadores",
                    []
                )
                or []
            )
        )
        +
        len(
            (
                frente_atualizada
                .get(
                    "clan_b",
                    {}
                )
                .get(
                    "jogadores",
                    []
                )
                or []
            )
        )
    )


    return {
        "success": True,

        "message":
            (
                "Você entrou no lobby "
                f"da Frente {numero_frente}."
            ),

        "guerra_id":
            str(
                guerra["_id"]
            ),

        "frente_numero":
            numero_frente,

        "ja_estava_presente":
            ja_estava_presente,

        "presentes_total":
            len(
                presentes_ids
            ),

        "jogadores_total":
            jogadores_total,
    }

# ============================================================
# ✅ MARCAR JOGADOR PRONTO NA FRENTE
# ============================================================

def marcar_pronto_lobby_frente_guerra(
    user_id,
):
    """
    Marca um titular como PRONTO
    dentro do lobby da própria frente.

    Regras:
    - precisa ser titular;
    - precisa possuir frente;
    - guerra precisa estar em andamento;
    - precisa ter entrado no lobby antes;
    - não duplica PRONTO;
    - não inicia combate nesta etapa.
    """

    player_id = _object_id(
        user_id
    )


    if not player_id:

        return {
            "success": False,
            "error": "ID de jogador inválido.",
        }


    # ========================================================
    # 🔎 USA O ESTADO OFICIAL JÁ VALIDADO
    # ========================================================

    estado = (
        obter_estado_guerra_jogador(
            player_id
        )
    )


    if not estado.get(
        "success"
    ):

        return {
            "success": False,
            "error":
                estado.get(
                    "error",
                    "Não foi possível consultar a guerra."
                ),
        }


    frente = (
        estado.get(
            "minha_frente"
        )
        or {}
    )


    guerra = (
        estado.get(
            "guerra"
        )
        or {}
    )


    if (
        not estado.get(
            "sou_titular_guerra"
        )
        or
        not frente
    ):

        return {
            "success": False,
            "error": (
                "Somente titulares podem "
                "marcar PRONTO nesta frente."
            ),
        }


    if not estado.get(
        "pode_entrar_guerra"
    ):

        return {
            "success": False,
            "error": (
                "Esta frente não está disponível "
                "para preparação neste momento."
            ),
        }


    guerra_id = _object_id(
        guerra.get(
            "_id"
        )
    )


    if not guerra_id:

        return {
            "success": False,
            "error": "Guerra inválida.",
        }


    try:

        numero_frente = int(
            frente.get(
                "numero"
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        return {
            "success": False,
            "error": "Frente inválida.",
        }


    # ========================================================
    # 🚪 PRECISA ESTAR PRESENTE NO LOBBY
    # ========================================================

    lobby = (
        frente.get(
            "lobby",
            {}
        )
        or {}
    )


    presentes_ids = {

        _object_id(
            valor
        )

        for valor
        in (
            lobby.get(
                "presentes_ids",
                []
            )
            or []
        )

        if _object_id(
            valor
        )
    }


    if (
        player_id
        not in
        presentes_ids
    ):

        return {
            "success": False,
            "error": (
                "Entre no lobby da sua frente "
                "antes de marcar PRONTO."
            ),
        }


    prontos_antes = {

        _object_id(
            valor
        )

        for valor
        in (
            lobby.get(
                "prontos_ids",
                []
            )
            or []
        )

        if _object_id(
            valor
        )
    }


    ja_estava_pronto = (
        player_id
        in
        prontos_antes
    )


    agora = _agora()


    # ========================================================
    # ✅ REGISTRA PRONTO
    #
    # $addToSet garante idempotência.
    # ========================================================

    guerra_atualizada = (
        clan_wars_collection
        .find_one_and_update(

            {
                "_id":
                    guerra_id,

                "frentes": {
                    "$elemMatch": {

                        "numero":
                            numero_frente,

                        "status": {
                            "$ne":
                                GUERRA_STATUS_FINALIZADA
                        },

                        "lobby.presentes_ids":
                            player_id,
                    }
                },
            },

            {
                "$addToSet": {

                    "frentes.$.lobby.prontos_ids":
                        player_id,
                },

                "$set": {

                    "frentes.$.lobby.atualizado_em":
                        agora,

                    "atualizado_em":
                        agora,
                },
            },

            return_document=
                ReturnDocument.AFTER,
        )
    )


    if not guerra_atualizada:

        return {
            "success": False,
            "error": (
                "Não foi possível marcar "
                "o jogador como PRONTO."
            ),
        }


    # ========================================================
    # 🔄 RECUPERA A FRENTE ATUALIZADA
    # ========================================================

    frente_atualizada = next(
        (
            item

            for item
            in (
                guerra_atualizada.get(
                    "frentes",
                    []
                )
                or []
            )

            if int(
                item.get(
                    "numero",
                    0
                )
                or 0
            )
            ==
            numero_frente
        ),

        None,
    )


    if not frente_atualizada:

        return {
            "success": False,
            "error": (
                "A frente não foi encontrada "
                "após marcar PRONTO."
            ),
        }


    lobby_atualizado = (
        frente_atualizada.get(
            "lobby",
            {}
        )
        or {}
    )


    # ========================================================
    # 👥 JOGADORES VÁLIDOS DA FRENTE
    # ========================================================

    jogadores_ids = set()


    for chave_lado in (
        "clan_a",
        "clan_b",
    ):

        for jogador in (
            frente_atualizada
            .get(
                chave_lado,
                {}
            )
            .get(
                "jogadores",
                []
            )
            or []
        ):

            jogador_id = _object_id(
                jogador.get(
                    "user_id"
                )
            )


            if jogador_id:

                jogadores_ids.add(
                    jogador_id
                )


    prontos_ids = {

        _object_id(
            valor
        )

        for valor
        in (
            lobby_atualizado.get(
                "prontos_ids",
                []
            )
            or []
        )

        if _object_id(
            valor
        )
    }


    prontos_validos = (
        prontos_ids
        &
        jogadores_ids
    )


    jogadores_total = len(
        jogadores_ids
    )


    prontos_total = len(
        prontos_validos
    )


    todos_prontos = bool(
        jogadores_total > 0
        and
        prontos_total
        ==
        jogadores_total
    )


    # ========================================================
    # ⚔️ FRENTE PRONTA PARA COMBATE
    #
    # IMPORTANTE:
    # Isto NÃO inicia o combate.
    #
    # Apenas registra oficialmente no MongoDB
    # que todos os jogadores daquela frente
    # confirmaram PRONTO.
    #
    # A gravação é idempotente:
    # preparada_em só é definida uma vez.
    # ========================================================

    preparada_agora = False


    if todos_prontos:

        agora_preparo = _agora()


        resultado_preparo = (
            clan_wars_collection
            .update_one(

                {
                    "_id":
                        guerra_id,

                    "frentes": {
                        "$elemMatch": {

                            "numero":
                                numero_frente,

                            "status": {
                                "$ne":
                                    GUERRA_STATUS_FINALIZADA
                            },

                            "lobby.preparada_em":
                                None,
                        }
                    },
                },

                {
                    "$set": {

                        "frentes.$.lobby.todos_prontos":
                            True,

                        "frentes.$.lobby.estado":
                            "pronta_para_combate",

                        "frentes.$.lobby.prontos_total":
                            prontos_total,

                        "frentes.$.lobby.jogadores_total":
                            jogadores_total,

                        "frentes.$.lobby.preparada_em":
                            agora_preparo,

                        "atualizado_em":
                            agora_preparo,
                    }
                },
            )
        )


        preparada_agora = bool(
            resultado_preparo.modified_count
            == 1
        )


        if preparada_agora:

            print(
                "⚔️ [GUERRA DE CLÃS] "
                f"Frente {numero_frente} "
                "pronta para combate "
                f"({prontos_total}/"
                f"{jogadores_total})."
            )


    return {
        "success": True,

        "message":
            (
                "Você está PRONTO "
                f"na Frente {numero_frente}."
            ),

        "frente_numero":
            numero_frente,

        "ja_estava_pronto":
            ja_estava_pronto,

        "prontos_total":
            prontos_total,

        "jogadores_total":
            jogadores_total,

        "todos_prontos":
            todos_prontos,

        "frente_preparada":
            todos_prontos,

        "preparada_agora":
            preparada_agora,

        # Continua False.
        # O motor de batalha ainda não existe.
        "combate_iniciado":
            False,
    }

# ============================================================
# 📈 RATING DO CLÃ PARA MATCHMAKING
# ============================================================

def _obter_rating_guerra_cla(
    clan_id,
):
    clan_id = (
        _object_id(
            clan_id
        )
    )


    if not clan_id:
        return int(
            GUERRA_RATING_INICIAL
        )


    cla = (
        db["clans"]
        .find_one(
            {
                "_id":
                    clan_id
            },

            {
                "war_rating":
                    1,

                "guerra.rating":
                    1,
            },
        )
        or {}
    )


    guerra = (
        cla.get(
            "guerra",
            {}
        )
        or {}
    )


    rating = (
        guerra.get(
            "rating"
        )
        or
        cla.get(
            "war_rating"
        )
        or
        GUERRA_RATING_INICIAL
    )


    try:
        return int(
            rating
        )

    except (
        TypeError,
        ValueError,
    ):
        return int(
            GUERRA_RATING_INICIAL
        )

# ============================================================
# 🏆 RANKING DA GUERRA DE CLÃS
# ============================================================

def obter_ranking_guerra(
    semana_id=None,
    limite=100,
):
    """
    Calcula o ranking diretamente das
    Guerras oficiais já finalizadas.

    semana_id:
    - None = ranking geral;
    - "2026-W37" = somente aquela semana.

    Não grava pontos no documento do clã.
    Portanto uma Guerra nunca é pontuada
    duas vezes por chamadas repetidas.
    """

    try:
        limite = int(
            limite
        )

    except (
        TypeError,
        ValueError,
    ):
        limite = 100


    limite = max(
        1,
        min(
            limite,
            200,
        ),
    )


    filtro = {

        "tipo_documento":
            WAR_DOC_GUERRA,

        "tipo_guerra":
            GUERRA_TIPO_OFICIAL,

        "status":
            GUERRA_STATUS_FINALIZADA,

        "resultado.finalizada_em": {
            "$ne":
                None,
        },
    }


    semana_filtro = None


    if semana_id is not None:

        semana_filtro = str(
            semana_id
        ).strip()


        if not semana_filtro:

            return {
                "success": False,
                "error":
                    "Semana inválida.",
            }


        filtro[
            "semana_id"
        ] = semana_filtro


    guerras = list(
        clan_wars_collection.find(
            filtro,
            {
                "semana_id": 1,
                "clans": 1,
                "resultado": 1,
            },
        )
    )


    ranking_por_clan = {}

    guerras_consideradas = 0
    guerras_ignoradas = 0


    def garantir_clan(
        lado,
    ):
        clan_id = _object_id(
            lado.get(
                "clan_id"
            )
        )


        if not clan_id:
            return None


        chave = str(
            clan_id
        )


        if chave not in ranking_por_clan:

            ranking_por_clan[
                chave
            ] = {

                "clan_id":
                    clan_id,

                "nome":
                    str(
                        lado.get(
                            "nome",
                            "Clã",
                        )
                    ),

                "tag":
                    str(
                        lado.get(
                            "tag",
                            "",
                        )
                    ),

                "logo_url":
                    str(
                        lado.get(
                            "logo_url"
                        )
                        or ""
                    ),

                "jogos":
                    0,

                "vitorias":
                    0,

                "empates":
                    0,

                "derrotas":
                    0,

                "frentes_vencidas":
                    0,

                "frentes_perdidas":
                    0,

                "saldo_frentes":
                    0,

                "pontos":
                    0,

                "rating":
                    GUERRA_RATING_INICIAL,
            }


        return ranking_por_clan[
            chave
        ]


    for guerra in guerras:

        clans = (
            guerra.get(
                "clans",
                []
            )
            or []
        )


        lado_a = next(
            (
                item

                for item
                in clans

                if str(
                    item.get(
                        "lado",
                        ""
                    )
                ).lower()
                ==
                "a"
            ),

            None,
        )


        lado_b = next(
            (
                item

                for item
                in clans

                if str(
                    item.get(
                        "lado",
                        ""
                    )
                ).lower()
                ==
                "b"
            ),

            None,
        )


        if (
            not lado_a
            or
            not lado_b
        ):

            guerras_ignoradas += 1
            continue


        clan_a_id = _object_id(
            lado_a.get(
                "clan_id"
            )
        )


        clan_b_id = _object_id(
            lado_b.get(
                "clan_id"
            )
        )


        if (
            not clan_a_id
            or
            not clan_b_id
            or
            clan_a_id
            ==
            clan_b_id
        ):

            guerras_ignoradas += 1
            continue


        resultado = (
            guerra.get(
                "resultado",
                {}
            )
            or {}
        )


        try:

            frentes_a = int(
                resultado.get(
                    "frentes_clan_a",
                    0,
                )
                or 0
            )


            frentes_b = int(
                resultado.get(
                    "frentes_clan_b",
                    0,
                )
                or 0
            )

        except (
            TypeError,
            ValueError,
        ):

            guerras_ignoradas += 1
            continue


        empate = bool(
            resultado.get(
                "empate",
                False,
            )
        )


        vencedor_id = _object_id(
            resultado.get(
                "vencedor_clan_id"
            )
        )


        if not empate:

            if vencedor_id not in {
                clan_a_id,
                clan_b_id,
            }:

                guerras_ignoradas += 1
                continue


        dados_a = garantir_clan(
            lado_a
        )


        dados_b = garantir_clan(
            lado_b
        )


        if (
            not dados_a
            or
            not dados_b
        ):

            guerras_ignoradas += 1
            continue


        dados_a[
            "jogos"
        ] += 1


        dados_b[
            "jogos"
        ] += 1


        dados_a[
            "frentes_vencidas"
        ] += frentes_a


        dados_a[
            "frentes_perdidas"
        ] += frentes_b


        dados_b[
            "frentes_vencidas"
        ] += frentes_b


        dados_b[
            "frentes_perdidas"
        ] += frentes_a


        if empate:

            dados_a[
                "empates"
            ] += 1


            dados_b[
                "empates"
            ] += 1


            dados_a[
                "pontos"
            ] += GUERRA_PONTOS_EMPATE


            dados_b[
                "pontos"
            ] += GUERRA_PONTOS_EMPATE


        elif (
            vencedor_id
            ==
            clan_a_id
        ):

            dados_a[
                "vitorias"
            ] += 1


            dados_b[
                "derrotas"
            ] += 1


            dados_a[
                "pontos"
            ] += GUERRA_PONTOS_VITORIA


            dados_b[
                "pontos"
            ] += GUERRA_PONTOS_DERROTA


        else:

            dados_b[
                "vitorias"
            ] += 1


            dados_a[
                "derrotas"
            ] += 1


            dados_b[
                "pontos"
            ] += GUERRA_PONTOS_VITORIA


            dados_a[
                "pontos"
            ] += GUERRA_PONTOS_DERROTA


        guerras_consideradas += 1


    ranking = list(
        ranking_por_clan.values()
    )


    for item in ranking:

        item[
            "saldo_frentes"
        ] = (
            item[
                "frentes_vencidas"
            ]
            -
            item[
                "frentes_perdidas"
            ]
        )


        item[
            "rating"
        ] = (
            _obter_rating_guerra_cla(
                item[
                    "clan_id"
                ]
            )
        )

        # ====================================================
        # 🛡️ BRASÃO ATUAL DO CLÃ
        #
        # O documento da guerra preserva a logo histórica,
        # mas o ranking deve exibir a identidade visual
        # atual escolhida pelo clã.
        # ====================================================

        cla_atual = (
            db["clans"]
            .find_one({
                "_id":
                    item[
                        "clan_id"
                    ]
            })
            or {}
        )


        cla_serializado = (
            clan_manager
            .serializar_cla(
                cla_atual
            )
            or {}
        )


        item[
            "logo_url"
        ] = str(
            cla_serializado.get(
                "logo_url"
            )
            or
            item.get(
                "logo_url"
            )
            or
            ""
        )

    ranking.sort(
        key=lambda item: (

            -int(
                item.get(
                    "pontos",
                    0,
                )
            ),

            -int(
                item.get(
                    "frentes_vencidas",
                    0,
                )
            ),

            -int(
                item.get(
                    "saldo_frentes",
                    0,
                )
            ),

            -int(
                item.get(
                    "rating",
                    GUERRA_RATING_INICIAL,
                )
            ),

            str(
                item.get(
                    "nome",
                    ""
                )
            ).casefold(),
        )
    )


    ranking = ranking[
        :limite
    ]


    for indice, item in enumerate(
        ranking,
        start=1,
    ):

        item[
            "posicao"
        ] = indice


        item[
            "clan_id"
        ] = str(
            item[
                "clan_id"
            ]
        )


    return {
        "success":
            True,

        "semana_id":
            semana_filtro,

        "guerras_consideradas":
            guerras_consideradas,

        "guerras_ignoradas":
            guerras_ignoradas,

        "total_clans":
            len(
                ranking
            ),

        "ranking":
            ranking,
    }

# ============================================================
# ⚔️ CRIAR FRENTES DA GUERRA
# ============================================================

def _criar_frentes_guerra(
    inscricao_a,
    inscricao_b,
    categoria,
):
    escalacao_a = (
        inscricao_a.get(
            "escalacao",
            {}
        )
        or {}
    )


    escalacao_b = (
        inscricao_b.get(
            "escalacao",
            {}
        )
        or {}
    )


    titulares_a = list(
        escalacao_a.get(
            "jogadores",
            []
        )
        or []
    )


    titulares_b = list(
        escalacao_b.get(
            "jogadores",
            []
        )
        or []
    )


    categoria = int(
        categoria
    )


    quantidade_frentes = (
        categoria // 5
    )


    frentes = []


    for indice in range(
        quantidade_frentes
    ):

        inicio = (
            indice * 5
        )

        fim = (
            inicio + 5
        )


        jogadores_a = (
            titulares_a[
                inicio:fim
            ]
        )


        jogadores_b = (
            titulares_b[
                inicio:fim
            ]
        )


        frentes.append({

            "numero":
                indice + 1,

            "status":
                GUERRA_STATUS_AGENDADA,

            "clan_a": {

                "clan_id":
                    inscricao_a[
                        "clan_id"
                    ],

                "jogadores":
                    jogadores_a,
            },

            "clan_b": {

                "clan_id":
                    inscricao_b[
                        "clan_id"
                    ],

                "jogadores":
                    jogadores_b,
            },

            "resultado": {

                "vencedor_clan_id":
                    None,

                "finalizada_em":
                    None,
            },
        })


    return frentes

# ============================================================
# 🏆 CONSOLIDAR RESULTADO GERAL DA GUERRA
# ============================================================

def consolidar_resultado_guerra(
    guerra_id,
):
    """
    Recalcula o placar geral da Guerra
    usando SOMENTE os resultados oficiais
    já persistidos em cada frente.

    Regras:
    - atualiza o placar parcial;
    - não encerra enquanto existir frente pendente;
    - finaliza somente quando todas as frentes
      possuem vencedor oficial;
    - suporta empate;
    - é idempotente.
    """

    guerra_id = _object_id(
        guerra_id
    )


    if not guerra_id:

        return {
            "success": False,
            "error":
                "ID de Guerra inválido.",
        }


    # ========================================================
    # ⚔️ ESTADO MAIS RECENTE DA GUERRA
    # ========================================================

    guerra = (
        clan_wars_collection
        .find_one({
            "_id":
                guerra_id,

            "tipo_documento":
                WAR_DOC_GUERRA,
        })
    )


    if not guerra:

        return {
            "success": False,
            "error":
                "Guerra não encontrada.",
        }


    if (
        guerra.get(
            "status"
        )
        ==
        GUERRA_STATUS_CANCELADA
    ):

        return {
            "success": False,
            "error":
                "Esta Guerra foi cancelada.",
        }


    # ========================================================
    # 🏰 IDENTIFICA CLÃ A E CLÃ B
    # ========================================================

    clans = (
        guerra.get(
            "clans",
            []
        )
        or []
    )


    lado_a = next(
        (
            item

            for item
            in clans

            if str(
                item.get(
                    "lado",
                    ""
                )
            ).lower()
            ==
            "a"
        ),
        None,
    )


    lado_b = next(
        (
            item

            for item
            in clans

            if str(
                item.get(
                    "lado",
                    ""
                )
            ).lower()
            ==
            "b"
        ),
        None,
    )


    if (
        not lado_a
        or
        not lado_b
    ):

        return {
            "success": False,
            "error":
                "Os lados da Guerra são inválidos.",
        }


    clan_a_id = _object_id(
        lado_a.get(
            "clan_id"
        )
    )


    clan_b_id = _object_id(
        lado_b.get(
            "clan_id"
        )
    )


    if (
        not clan_a_id
        or
        not clan_b_id
    ):

        return {
            "success": False,
            "error":
                "Os IDs dos clãs são inválidos.",
        }


    # ========================================================
    # ⚔️ FRENTES OFICIAIS
    # ========================================================

    frentes = list(
        guerra.get(
            "frentes",
            []
        )
        or []
    )


    try:

        frentes_total = int(
            guerra.get(
                "frentes_total",
                len(
                    frentes
                )
            )
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):

        frentes_total = 0


    if (
        frentes_total <= 0
        or
        len(
            frentes
        )
        !=
        frentes_total
    ):

        return {
            "success": False,

            "error":
                (
                    "A quantidade de frentes "
                    "da Guerra é inconsistente."
                ),
        }


    # ========================================================
    # 🧮 CONTA SOMENTE RESULTADOS OFICIAIS
    # ========================================================

    frentes_clan_a = 0
    frentes_clan_b = 0
    frentes_finalizadas = 0


    for frente in frentes:

        if (
            frente.get(
                "status"
            )
            !=
            GUERRA_STATUS_FINALIZADA
        ):

            continue


        resultado_frente = (
            frente.get(
                "resultado",
                {}
            )
            or {}
        )


        vencedor_frente = _object_id(
            resultado_frente.get(
                "vencedor_clan_id"
            )
        )


        if (
            vencedor_frente
            ==
            clan_a_id
        ):

            frentes_clan_a += 1
            frentes_finalizadas += 1


        elif (
            vencedor_frente
            ==
            clan_b_id
        ):

            frentes_clan_b += 1
            frentes_finalizadas += 1


        else:

            return {
                "success": False,

                "error":
                    (
                        "Existe uma frente finalizada "
                        "sem vencedor oficial válido."
                    ),

                "frente_numero":
                    frente.get(
                        "numero"
                    ),
            }


    agora = _agora()


    # ========================================================
    # 📊 PLACAR PARCIAL
    #
    # Uma chamada antiga nunca pode sobrescrever
    # uma Guerra que já foi oficialmente finalizada.
    # ========================================================

    clan_wars_collection.update_one(

        {
            "_id":
                guerra_id,

            "status": {
                "$nin": [
                    GUERRA_STATUS_FINALIZADA,
                    GUERRA_STATUS_CANCELADA,
                ]
            },
        },

        {
            "$set": {

                "resultado.frentes_clan_a":
                    frentes_clan_a,

                "resultado.frentes_clan_b":
                    frentes_clan_b,

                "atualizado_em":
                    agora,
            }
        },
    )


    # ========================================================
    # ⏳ AINDA EXISTEM FRENTES ABERTAS
    # ========================================================

    if (
        frentes_finalizadas
        <
        frentes_total
    ):

        return {
            "success": True,

            "finalizada":
                False,

            "frentes_total":
                frentes_total,

            "frentes_finalizadas":
                frentes_finalizadas,

            "frentes_clan_a":
                frentes_clan_a,

            "frentes_clan_b":
                frentes_clan_b,
        }


    # ========================================================
    # 🏆 RESULTADO DEFINITIVO
    # ========================================================

    empate = (
        frentes_clan_a
        ==
        frentes_clan_b
    )


    if empate:

        vencedor_clan_id = None
        perdedor_clan_id = None


    elif (
        frentes_clan_a
        >
        frentes_clan_b
    ):

        vencedor_clan_id = (
            clan_a_id
        )

        perdedor_clan_id = (
            clan_b_id
        )


    else:

        vencedor_clan_id = (
            clan_b_id
        )

        perdedor_clan_id = (
            clan_a_id
        )


    nome_a = str(
        lado_a.get(
            "nome",
            "Clã A"
        )
    )


    nome_b = str(
        lado_b.get(
            "nome",
            "Clã B"
        )
    )


    # ========================================================
    # 🔒 FINALIZAÇÃO ATÔMICA / IDPOTENTE
    #
    # Apenas uma chamada consegue mudar:
    # em_andamento -> finalizada.
    # ========================================================

    resultado_finalizacao = (
        clan_wars_collection
        .update_one(

            {
                "_id":
                    guerra_id,

                "tipo_documento":
                    WAR_DOC_GUERRA,

                "status": {
                    "$nin": [
                        GUERRA_STATUS_FINALIZADA,
                        GUERRA_STATUS_CANCELADA,
                    ]
                },
            },

            {
                "$set": {

                    "status":
                        GUERRA_STATUS_FINALIZADA,

                    "resultado.vencedor_clan_id":
                        vencedor_clan_id,

                    "resultado.perdedor_clan_id":
                        perdedor_clan_id,

                    "resultado.empate":
                        empate,

                    "resultado.frentes_clan_a":
                        frentes_clan_a,

                    "resultado.frentes_clan_b":
                        frentes_clan_b,

                    "resultado.finalizada_em":
                        agora,

                    "atualizado_em":
                        agora,
                },

                "$push": {

                    "historico": {

                        "tipo":
                            "guerra_finalizada",

                        "mensagem":
                            (
                                f"Guerra finalizada: "
                                f"{nome_a} "
                                f"{frentes_clan_a} x "
                                f"{frentes_clan_b} "
                                f"{nome_b}."
                            ),

                        "autor":
                            "sistema",

                        "criado_em":
                            agora,
                    }
                },
            },
        )
    )


    # ========================================================
    # 📄 FINALIZA TAMBÉM AS DUAS INSCRIÇÕES
    #
    # Isso impede que a sincronização operacional
    # volte a exibir as inscrições como em andamento.
    # ========================================================

    clan_wars_collection.update_many(

        {
            "tipo_documento":
                WAR_DOC_INSCRICAO,

            "semana_id":
                guerra.get(
                    "semana_id"
                ),

            "matchmaking.guerra_id":
                guerra_id,

            "status": {
                "$ne":
                    GUERRA_STATUS_CANCELADA
            },
        },

        {
            "$set": {

                "status":
                    GUERRA_STATUS_FINALIZADA,

                "atualizado_em":
                    agora,
            }
        },
    )


    return {
        "success": True,

        "finalizada":
            True,

        "finalizada_agora":
            (
                resultado_finalizacao
                .modified_count
                ==
                1
            ),

        "empate":
            empate,

        "vencedor_clan_id":
            (
                str(
                    vencedor_clan_id
                )
                if vencedor_clan_id
                else None
            ),

        "perdedor_clan_id":
            (
                str(
                    perdedor_clan_id
                )
                if perdedor_clan_id
                else None
            ),

        "frentes_total":
            frentes_total,

        "frentes_finalizadas":
            frentes_finalizadas,

        "frentes_clan_a":
            frentes_clan_a,

        "frentes_clan_b":
            frentes_clan_b,
    }

# ============================================================
# 👤 PARTICIPAÇÃO DO JOGADOR NA SEMANA
# ============================================================

def obter_inscricao_participante(
    user_id,
    semana_id=None,
):
    player_id = (
        _object_id(
            user_id
        )
    )


    if not player_id:
        return None


    semana_id = str(
        semana_id
        or
        obter_semana_id()
    ).strip()


    return (
        clan_wars_collection
        .find_one({
            "tipo_documento":
                WAR_DOC_INSCRICAO,

            "semana_id":
                semana_id,

            "participantes.user_id":
                player_id,
        })
    )

# ============================================================
# 👤 SNAPSHOT DO GUERREIRO
# ============================================================

def _criar_snapshot_participante(
    player_id,
):
    jogador = (
        users_collection
        .find_one({
            "_id":
                player_id
        })
        or {}
    )


    nome = (
        jogador.get(
            "character_name"
        )
        or
        jogador.get(
            "nome"
        )
        or
        jogador.get(
            "username"
        )
        or
        "Aventureiro"
    )


    nivel = (
        jogador.get(
            "level"
        )
        or
        jogador.get(
            "nivel"
        )
        or
        1
    )


    classe = (
        jogador.get(
            "class"
        )
        or
        jogador.get(
            "classe"
        )
        or
        "aventureiro"
    )


    try:
        nivel = int(
            nivel
        )

    except (
        TypeError,
        ValueError,
    ):
        nivel = 1


    return {
        "user_id":
            player_id,

        "nome":
            str(
                nome
            ),

        "nivel":
            nivel,

        "classe":
            str(
                classe
            ),

        "inscrito_em":
            _agora(),
    }

# ============================================================
# ⚔️ RECALCULAR CATEGORIA DA INSCRIÇÃO
# ============================================================

def _recalcular_categoria_inscricao(
    inscricao,
):
    if not inscricao:
        return None


    participantes = (
        inscricao.get(
            "participantes",
            []
        )
        or []
    )


    total = len(
        participantes
    )


    nivel_cla = int(
        (
            inscricao
            .get(
                "clan_snapshot",
                {}
            )
            .get(
                "nivel",
                1,
            )
        )
        or 1
    )


    categoria = (
        obter_categoria_efetiva(
            nivel_cla,
            total,
        )
    )


    atualizacao = {
        "participantes_total":
            total,

        "atualizado_em":
            _agora(),
    }


    if categoria:

        atualizacao.update({
            "categoria_efetiva":
                categoria.get(
                    "jogadores_por_cla"
                ),

            "categoria_efetiva_nome":
                categoria.get(
                    "nome"
                ),

            "frentes_efetivas":
                categoria.get(
                    "frentes",
                    0,
                ),
        })

    else:

        atualizacao.update({
            "categoria_efetiva":
                None,

            "categoria_efetiva_nome":
                None,

            "frentes_efetivas":
                0,
        })


    clan_wars_collection.update_one(
        {
            "_id":
                inscricao["_id"]
        },

        {
            "$set":
                atualizacao
        },
    )


    inscricao.update(
        atualizacao
    )


    return inscricao

# ============================================================
# 👥 AVALIAR QUÓRUM DA INSCRIÇÃO
# ============================================================

def _avaliar_quorum_inscricao(
    inscricao,
    calendario=None,
):
    """
    Avalia se o clã atingiu o mínimo
    necessário para permanecer na Guerra.

    Durante as inscrições:
    apenas acompanha o progresso.

    Após o fechamento:
    define oficialmente se o clã está
    aprovado ou sem quórum.
    """

    if not inscricao:
        return None


    calendario = (
        calendario
        or
        obter_estado_calendario()
    )


    participantes = (
        inscricao.get(
            "participantes",
            []
        )
        or []
    )


    total = len(
        participantes
    )


    minimo = int(
        GUERRA_MINIMO_JOGADORES_POR_CLA
    )


    faltam = max(
        0,
        minimo - total,
    )


    inscricoes_abertas = bool(
        calendario.get(
            "inscricoes_abertas"
        )
    )


    status_documento = str(
        inscricao.get(
            "status",
            ""
        )
    ).strip()


    # ========================================================
    # CANCELADA
    # ========================================================

    if (
        status_documento
        ==
        GUERRA_STATUS_CANCELADA
    ):

        status_quorum = (
            QUORUM_STATUS_CANCELADO
        )

        atingido = False
        encerrado = True
        elegivel_matchmaking = False


    # ========================================================
    # INSCRIÇÕES AINDA ABERTAS
    # ========================================================

    elif inscricoes_abertas:

        status_quorum = (
            QUORUM_STATUS_EM_FORMACAO
        )

        atingido = (
            total >= minimo
        )

        encerrado = False

        # Ainda não entra no matchmaking
        # enquanto as inscrições estiverem abertas.
        elegivel_matchmaking = False


    # ========================================================
    # INSCRIÇÕES ENCERRADAS
    # ========================================================

    else:

        encerrado = True

        atingido = (
            total >= minimo
        )


        if atingido:

            status_quorum = (
                QUORUM_STATUS_APROVADO
            )

            elegivel_matchmaking = True

        else:

            status_quorum = (
                QUORUM_STATUS_SEM_QUORUM
            )

            elegivel_matchmaking = False


    novo_quorum = {

        "status":
            status_quorum,

        "minimo":
            minimo,

        "participantes_total":
            total,

        "faltam":
            faltam,

        "atingido":
            atingido,

        "encerrado":
            encerrado,

        "elegivel_matchmaking":
            elegivel_matchmaking,
    }


    quorum_atual = (
        inscricao.get(
            "quorum",
            {}
        )
        or {}
    )


    mudou = any(

        quorum_atual.get(
            chave
        )
        != valor

        for (
            chave,
            valor
        )
        in novo_quorum.items()
    )


    if mudou:

        agora = _agora()


        novo_quorum[
            "atualizado_em"
        ] = agora


        novo_quorum[
            "avaliado_em"
        ] = (
            agora
            if encerrado
            else None
        )


        clan_wars_collection.update_one(
            {
                "_id":
                    inscricao["_id"]
            },
            {
                "$set": {
                    "quorum":
                        novo_quorum,

                    "atualizado_em":
                        agora,
                }
            },
        )


    else:

        novo_quorum[
            "atualizado_em"
        ] = quorum_atual.get(
            "atualizado_em"
        )


        novo_quorum[
            "avaliado_em"
        ] = quorum_atual.get(
            "avaliado_em"
        )


    inscricao[
        "quorum"
    ] = novo_quorum


    return novo_quorum

# ============================================================
# 🚪 REMOÇÃO FORÇADA DE PARTICIPAÇÃO
# ============================================================

def remover_participacao_forcada(
    user_id,
    clan_id=None,
    semana_id=None,
    motivo="saida_cla",
):
    """
    Remove um jogador da inscrição da Guerra
    independentemente da fase ou trava.

    Usado quando:
    - sai do clã;
    - é expulso;
    - vínculo antigo fica órfão;
    - troca de clã.
    """

    player_id = _object_id(
        user_id
    )


    if not player_id:

        return {
            "success": False,
            "error":
                "ID de jogador inválido.",
        }


    clan_id = (
        _object_id(
            clan_id
        )
        if clan_id
        else None
    )


    semana_id = str(
        semana_id
        or
        obter_semana_id()
    ).strip()


    filtro = {
        "tipo_documento":
            WAR_DOC_INSCRICAO,

        "semana_id":
            semana_id,

        "participantes.user_id":
            player_id,
    }


    if clan_id:

        filtro[
            "clan_id"
        ] = clan_id


    inscricoes = list(
        clan_wars_collection.find(
            filtro
        )
    )


    if not inscricoes:

        return {
            "success": True,
            "removido": False,
            "total_removido": 0,
        }


    mensagens = {

        "saida_cla":
            (
                "foi removido da Guerra "
                "porque saiu do clã."
            ),

        "expulsao_cla":
            (
                "foi removido da Guerra "
                "porque foi expulso do clã."
            ),

        "vinculo_cla_alterado":
            (
                "foi removido da Guerra "
                "porque seu vínculo de clã mudou."
            ),

        "dissolucao_cla":
            (
                "foi removido da Guerra "
                "porque o clã foi dissolvido."
            ),
    }


    descricao = (
        mensagens.get(
            motivo
        )
        or
        "foi removido da Guerra."
    )


    total_removido = 0


    for inscricao in inscricoes:

        participante = next(
            (
                item

                for item
                in (
                    inscricao.get(
                        "participantes",
                        []
                    )
                    or []
                )

                if item.get(
                    "user_id"
                )
                ==
                player_id
            ),
            None,
        )


        nome = (
            participante.get(
                "nome"
            )
            if participante
            else None
        ) or "Aventureiro"


        agora = _agora()


        atualizada = (
            clan_wars_collection
            .find_one_and_update(

                {
                    "_id":
                        inscricao["_id"],

                    "participantes.user_id":
                        player_id,
                },

                {
                    "$pull": {

                        "participantes": {
                            "user_id":
                                player_id,
                        },

                        "escalacao.jogadores": {
                            "user_id":
                                player_id,
                        },

                        "escalacao.reservas": {
                            "user_id":
                                player_id,
                        },
                    },

                    "$push": {
                        "historico": {

                            "tipo":
                                motivo,

                            "mensagem":
                                (
                                    f"{nome} "
                                    f"{descricao}"
                                ),

                            "autor_id":
                                player_id,

                            "criado_em":
                                agora,
                        },
                    },

                    "$set": {
                        "atualizado_em":
                            agora,
                    },
                },

                return_document=
                    ReturnDocument.AFTER,
            )
        )


        if not atualizada:
            continue


        atualizada = (
            _recalcular_categoria_inscricao(
                atualizada
            )
        )


        _avaliar_quorum_inscricao(
            atualizada
        )

        total_removido += 1


    return {
        "success": True,

        "removido":
            total_removido > 0,

        "total_removido":
            total_removido,
    }

# ============================================================
# 🩹 REPARAR PARTICIPAÇÃO ÓRFÃ
# ============================================================

def _reparar_participacao_orfa(
    player_id,
    clan_id_atual,
    semana_id,
):
    """
    Verifica se o jogador ainda representa
    o mesmo clã em que está atualmente.

    Caso contrário, remove automaticamente
    a inscrição antiga.
    """

    player_id = _object_id(
        player_id
    )


    clan_id_atual = (
        _object_id(
            clan_id_atual
        )
        if clan_id_atual
        else None
    )


    if not player_id:
        return None


    participacao = (
        obter_inscricao_participante(
            player_id,
            semana_id,
        )
    )


    if not participacao:
        return None


    clan_id_participacao = (
        _object_id(
            participacao.get(
                "clan_id"
            )
        )
    )


    # Está tudo certo.
    if (
        clan_id_atual
        and
        clan_id_participacao
        ==
        clan_id_atual
    ):
        return participacao


    # Não pertence mais àquele clã.
    remover_participacao_forcada(

        user_id=
            player_id,

        clan_id=
            clan_id_participacao,

        semana_id=
            semana_id,

        motivo=
            "vinculo_cla_alterado",
    )


    return None

# ============================================================
# 💀 CLÃ DISSOLVIDO — CANCELAR INSCRIÇÃO
# ============================================================

def cancelar_inscricao_cla_dissolvido(
    clan_id,
    semana_id=None,
):
    """
    Cancela a inscrição semanal quando
    o clã é dissolvido.

    Também libera todos os jogadores
    registrados para que possam participar
    por outro clã naquela semana.
    """

    clan_id = _object_id(
        clan_id
    )


    if not clan_id:

        return {
            "success": False,
            "error":
                "ID de clã inválido.",
        }


    semana_id = str(
        semana_id
        or
        obter_semana_id()
    ).strip()


    inscricao = (
        obter_inscricao_cla(
            clan_id,
            semana_id,
        )
    )


    if not inscricao:

        return {
            "success": True,
            "cancelada": False,
            "message":
                (
                    "O clã não possuía "
                    "inscrição nesta semana."
                ),
        }


    status_atual = str(
        inscricao.get(
            "status",
            ""
        )
    ).strip()


    # ========================================================
    # ✅ JÁ ESTÁ CANCELADA
    # ========================================================

    if (
        status_atual
        ==
        GUERRA_STATUS_CANCELADA
    ):

        return {
            "success": True,
            "cancelada": True,
            "ja_cancelada": True,
        }


    # ========================================================
    # 🏆 GUERRA JÁ FINALIZADA
    # ========================================================
    #
    # Não alteramos histórico de uma guerra
    # que já terminou.
    # ========================================================

    if (
        status_atual
        ==
        GUERRA_STATUS_FINALIZADA
    ):

        return {
            "success": True,
            "cancelada": False,
            "finalizada": True,
        }


    agora = _agora()


    # ========================================================
    # 📜 PRESERVA QUEM ESTAVA INSCRITO
    # ========================================================

    participantes_anteriores = (
        inscricao.get(
            "participantes",
            []
        )
        or []
    )


    escalacao_anterior = (
        inscricao.get(
            "escalacao",
            {}
        )
        or {}
    )


    # ========================================================
    # 💾 CANCELAMENTO
    # ========================================================

    resultado = (
        clan_wars_collection
        .update_one(

            {
                "_id":
                    inscricao["_id"],

                "status": {
                    "$ne":
                        GUERRA_STATUS_FINALIZADA,
                },
            },

            {
                "$set": {

                    "status":
                        GUERRA_STATUS_CANCELADA,

                    # Preserva para histórico.
                    "cancelamento.participantes":
                        participantes_anteriores,

                    "cancelamento.escalacao":
                        escalacao_anterior,

                    "cancelamento.motivo":
                        "clan_dissolvido",

                    "cancelamento.criado_em":
                        agora,

                    # Libera os jogadores.
                    "participantes":
                        [],

                    "participantes_total":
                        0,

                    "categoria_efetiva":
                        None,

                    "categoria_efetiva_nome":
                        None,

                    "frentes_efetivas":
                        0,

                    "escalacao.travada":
                        True,

                    "escalacao.travada_em":
                        agora,

                    "escalacao.jogadores":
                        [],

                    "escalacao.reservas":
                        [],

                    "atualizado_em":
                        agora,
                },

                "$push": {

                    "historico": {

                        "tipo":
                            "clan_dissolvido",

                        "mensagem":
                            (
                                "A inscrição na Guerra "
                                "foi cancelada porque "
                                "o clã foi dissolvido."
                            ),

                        "autor_id":
                            None,

                        "criado_em":
                            agora,
                    },
                },
            },
        )
    )


    return {
        "success": True,

        "cancelada":
            resultado.modified_count
            == 1,

        "participantes_liberados":
            len(
                participantes_anteriores
            ),
    }

# ============================================================
# 📦 SERIALIZAÇÃO
# ============================================================

def serializar_inscricao(
    inscricao,
):
    if not inscricao:
        return None


    return _json_seguro(
        inscricao
    )


def serializar_calendario(
    calendario=None,
):
    calendario = (
        calendario
        or
        obter_estado_calendario()
    )


    return _json_seguro(
        calendario
    )


# ============================================================
# 👤 ESTADO DA GUERRA PARA O JOGADOR
# ============================================================

def obter_estado_guerra_jogador(
    user_id,
):
    player_id = (
        _object_id(
            user_id
        )
    )


    if not player_id:

        return {
            "success": False,
            "error": (
                "ID de jogador inválido."
            ),
        }


    calendario = (
        obter_estado_calendario()
    )

    # ========================================================
    # ⚔️ SINCRONIZA A FASE OPERACIONAL DA GUERRA
    # ========================================================

    sincronizar_status_guerras_semana(
        calendario
    )


    cla = (
        clan_manager
        .obter_cla_do_jogador(
            player_id
        )
    )

    # ========================================================
    # 🩹 LIMPA PARTICIPAÇÃO ANTIGA/ÓRFÃ
    # ========================================================

    clan_id_atual = (
        cla.get(
            "_id"
        )
        if cla
        else None
    )


    _reparar_participacao_orfa(
        player_id=
            player_id,

        clan_id_atual=
            clan_id_atual,

        semana_id=
            calendario[
                "semana_id"
            ],
    )    

    # ========================================================
    # JOGADOR SEM CLÃ
    # ========================================================

    if not cla:

        return {
            "success": True,

            "possui_clan":
                False,

            "sou_lider":
                False,

            "pode_inscrever_clan":
                False,

            "calendario":
                serializar_calendario(
                    calendario
                ),

            "inscricao":
                None,
        }


    clan_id = (
        cla["_id"]
    )


    sou_lider = (
        cla.get(
            "lider_id"
        )
        ==
        player_id
    )


    nivel = int(
        cla.get(
            "nivel",
            1,
        )
        or 1
    )


    categoria_maxima = (
        obter_categoria_maxima_por_nivel(
            nivel
        )
    )


    categoria_config = (
        obter_config_categoria(
            categoria_maxima
        )
        or {}
    )


    inscricao = (
        obter_inscricao_cla(
            clan_id=
                clan_id,

            semana_id=
                calendario[
                    "semana_id"
                ],
        )
    )

    # ========================================================
    # ⚔️ CONFRONTO FORMADO
    # ========================================================

    guerra = (
        obter_guerra_cla(
            clan_id=
                clan_id,

            semana_id=
                calendario[
                    "semana_id"
                ],
        )
    )


    adversario = (
        _obter_adversario_guerra(
            guerra,
            clan_id,
        )
    )

    # ========================================================
    # ⚔️ PAPEL DO JOGADOR NO CONFRONTO
    # ========================================================

    meu_lado_guerra = (
        _obter_lado_cla_guerra(
            guerra,
            clan_id,
        )
    )


    minha_frente = (
        _localizar_frente_jogador(
            guerra,
            clan_id,
            player_id,
        )
    )

    # ========================================================
    # ⚔️ GARANTE ESTADO DA FRENTE PRONTA
    # ========================================================

    if (
        guerra
        and
        minha_frente
    ):

        lobby_frente = (
            minha_frente.get(
                "lobby",
                {}
            )
            or {}
        )


        jogadores_frente_ids = set()


        for chave_lado in (
            "clan_a",
            "clan_b",
        ):

            for jogador in (
                minha_frente
                .get(
                    chave_lado,
                    {}
                )
                .get(
                    "jogadores",
                    []
                )
                or []
            ):

                jogador_id = _object_id(
                    jogador.get(
                        "user_id"
                    )
                )


                if jogador_id:

                    jogadores_frente_ids.add(
                        jogador_id
                    )


        prontos_frente_ids = {

            _object_id(
                valor
            )

            for valor
            in (
                lobby_frente.get(
                    "prontos_ids",
                    []
                )
                or []
            )

            if _object_id(
                valor
            )
        }


        prontos_validos = (
            prontos_frente_ids
            &
            jogadores_frente_ids
        )


        todos_prontos_frente = bool(

            jogadores_frente_ids

            and
            len(
                prontos_validos
            )
            ==
            len(
                jogadores_frente_ids
            )
        )


        if (
            todos_prontos_frente
            and
            lobby_frente.get(
                "estado"
            )
            !=
            "pronta_para_combate"
        ):

            agora_preparo = _agora()


            try:

                numero_frente = int(
                    minha_frente.get(
                        "numero"
                    )
                )

            except (
                TypeError,
                ValueError,
            ):

                numero_frente = 0


            if numero_frente:

                resultado_preparo = (
                    clan_wars_collection
                    .update_one(

                        {
                            "_id":
                                guerra["_id"],

                            "frentes": {
                                "$elemMatch": {

                                    "numero":
                                        numero_frente,

                                    "status": {
                                        "$ne":
                                            GUERRA_STATUS_FINALIZADA
                                    },
                                }
                            },
                        },

                        {
                            "$set": {

                                "frentes.$.lobby.todos_prontos":
                                    True,

                                "frentes.$.lobby.estado":
                                    "pronta_para_combate",

                                "frentes.$.lobby.prontos_total":
                                    len(
                                        prontos_validos
                                    ),

                                "frentes.$.lobby.jogadores_total":
                                    len(
                                        jogadores_frente_ids
                                    ),

                                "frentes.$.lobby.preparada_em":
                                    agora_preparo,

                                "atualizado_em":
                                    agora_preparo,
                            }
                        },
                    )
                )


                if (
                    resultado_preparo.modified_count
                    == 1
                ):

                    guerra = (
                        obter_guerra_cla(
                            clan_id=
                                clan_id,

                            semana_id=
                                calendario[
                                    "semana_id"
                                ],
                        )
                    )


                    minha_frente = (
                        _localizar_frente_jogador(
                            guerra,
                            clan_id,
                            player_id,
                        )
                    )


                    print(
                        "⚔️ [GUERRA DE CLÃS] "
                        f"Frente {numero_frente} "
                        "confirmada como pronta "
                        "para combate."
                    )

    # ========================================================
    # ⚔️ PREPARAR ESTADO INICIAL DA BATALHA 5x5
    # ========================================================

    if (
        guerra
        and
        minha_frente
        and
        (
            minha_frente.get(
                "lobby",
                {}
            )
            or {}
        ).get(
            "estado"
        )
        ==
        "pronta_para_combate"
    ):

        from modules.clan import (
            clan_war_battle_engine,
        )


        resultado_batalha = (
            clan_war_battle_engine
            .garantir_batalha_inicial(

                guerra_id=
                    guerra[
                        "_id"
                    ],

                numero_frente=
                    minha_frente.get(
                        "numero"
                    ),
            )
        )


        if resultado_batalha.get(
            "success"
        ):

            # Recarrega para que a mesma
            # resposta da API já contenha
            # frente.batalha.
            guerra = (
                obter_guerra_cla(
                    clan_id=
                        clan_id,

                    semana_id=
                        calendario[
                            "semana_id"
                        ],
                )
            )


            minha_frente = (
                _localizar_frente_jogador(
                    guerra,
                    clan_id,
                    player_id,
                )
            )                    
    escalacao_guerra = (
        (
            meu_lado_guerra
            or {}
        ).get(
            "escalacao",
            {}
        )
        or {}
    )


    titulares_guerra = (
        escalacao_guerra.get(
            "jogadores",
            []
        )
        or []
    )


    reservas_guerra = (
        escalacao_guerra.get(
            "reservas",
            []
        )
        or []
    )


    sou_titular_guerra = any(

        _object_id(
            jogador.get(
                "user_id"
            )
        )
        ==
        player_id

        for jogador
        in titulares_guerra
    )


    sou_reserva_guerra = any(

        _object_id(
            jogador.get(
                "user_id"
            )
        )
        ==
        player_id

        for jogador
        in reservas_guerra
    )


    pode_entrar_guerra = bool(

        guerra

        and sou_titular_guerra

        and minha_frente

        and calendario.get(
            "fase"
        )
        ==
        GUERRA_STATUS_EM_ANDAMENTO

        and guerra.get(
            "status"
        )
        ==
        GUERRA_STATUS_EM_ANDAMENTO

        and minha_frente.get(
            "status"
        )
        !=
        GUERRA_STATUS_FINALIZADA
    )

    participantes = (
        inscricao.get(
            "participantes",
            []
        )
        if inscricao
        else []
    ) or []


    minha_participacao = next(
        (
            participante

            for participante
            in participantes

            if participante.get(
                "user_id"
            )
            ==
            player_id
        ),

        None,
    )


    participantes_total = len(
        participantes
    )

    quorum = (
        _avaliar_quorum_inscricao(
            inscricao,
            calendario,
        )
        if inscricao
        else None
    )

    categoria_efetiva = (
        obter_categoria_efetiva(
            nivel,
            participantes_total,
        )
        if inscricao
        else None
    )


    faltam_para_minimo = (
        max(
            0,

            GUERRA_MINIMO_JOGADORES_POR_CLA
            -
            participantes_total,
        )
        if inscricao
        else GUERRA_MINIMO_JOGADORES_POR_CLA
    )


    pode_participar = bool(
        inscricao
        and
        (
            calendario.get(
                "inscricoes_abertas"
            )
            or
            GUERRA_MODO_TESTE
        )
        
        and
        not minha_participacao
        and
        not (
            inscricao
            .get(
                "escalacao",
                {}
            )
            .get(
                "travada"
            )
        )
    )


    pode_sair_participacao = bool(
        inscricao
        and
        minha_participacao
        and
        (
            calendario.get(
                "inscricoes_abertas"
            )
            or
            GUERRA_MODO_TESTE
        )

        and
        not (
            inscricao
            .get(
                "escalacao",
                {}
            )
            .get(
                "travada"
            )
        )
    )

    escalacao = (
        inscricao.get(
            "escalacao",
            {}
        )
        if inscricao
        else {}
    ) or {}


    escalacao_travada = bool(
        escalacao.get(
            "travada"
        )
    )


    pode_gerenciar_escalacao = bool(

        sou_lider

        and inscricao

        and quorum

        and quorum.get(
            "status"
        )
        ==
        QUORUM_STATUS_APROVADO

        and calendario.get(
            "fase"
        )
        ==
        GUERRA_STATUS_ESCALACAO

        and not escalacao_travada
    )

    pode_inscrever = bool(
        sou_lider
        and
        (
            calendario.get(
                "inscricoes_abertas"
            )
            or
            GUERRA_MODO_TESTE
        )
        and
        not inscricao
    )


    motivo_bloqueio = None


    if not sou_lider:

        motivo_bloqueio = (
            "Somente o líder pode "
            "inscrever o clã."
        )


    elif inscricao:

        motivo_bloqueio = (
            "Seu clã já está inscrito "
            "nesta semana."
        )


    elif not calendario.get(
        "inscricoes_abertas"
    ):

        motivo_bloqueio = (
            "As inscrições não estão "
            "abertas neste momento."
        )


    return {
        "success": True,

        "possui_clan":
            True,

        "sou_lider":
            sou_lider,

        "pode_inscrever_clan":
            pode_inscrever,

        "motivo_bloqueio":
            motivo_bloqueio,

        "clan": {
            "id":
                str(
                    clan_id
                ),

            "nome":
                cla.get(
                    "nome",
                    "",
                ),

            "tag":
                cla.get(
                    "tag",
                    "",
                ),

            "nivel":
                nivel,

            "membros_total":
                int(
                    cla.get(
                        "membros_total",
                        0,
                    )
                    or 0
                ),

            "categoria_maxima":
                categoria_maxima,

            "categoria_nome":
                categoria_config.get(
                    "nome"
                ),
        },

        "calendario":
            serializar_calendario(
                calendario
            ),

        "minha_participacao":
            _json_seguro(
                minha_participacao
            ),

        "estou_inscrito":
            bool(
                minha_participacao
            ),

        "pode_participar":
            pode_participar,

        "pode_sair_participacao":
            pode_sair_participacao,

        "participantes_total":
            participantes_total,

        "faltam_para_minimo":
            faltam_para_minimo,

        "quorum":
            _json_seguro(
                quorum
            ),

        "participantes":
            _json_seguro(
                participantes
            ),

        "escalacao":
            _json_seguro(
                escalacao
            ),

        "escalacao_travada":
            escalacao_travada,

        "pode_gerenciar_escalacao":
            pode_gerenciar_escalacao,

        "categoria_efetiva":
            (
                categoria_efetiva.get(
                    "jogadores_por_cla"
                )
                if categoria_efetiva
                else None
            ),

        "categoria_efetiva_nome":
            (
                categoria_efetiva.get(
                    "nome"
                )
                if categoria_efetiva
                else None
            ),

        "inscricao":
            serializar_inscricao(
                inscricao
            ),

        "guerra":
            _json_seguro(
                guerra
            ),

        "adversario":
            _json_seguro(
                adversario
            ),

        "sou_titular_guerra":
            sou_titular_guerra,

        "sou_reserva_guerra":
            sou_reserva_guerra,

        "minha_frente":
            _json_seguro(
                minha_frente
            ),

        "pode_entrar_guerra":
            pode_entrar_guerra,
    }


# ============================================================
# ⚔️ INSCREVER CLÃ NA GUERRA SEMANAL
# ============================================================

def inscrever_cla_na_guerra(
    user_id,
):
    player_id = (
        _object_id(
            user_id
        )
    )


    if not player_id:

        return {
            "success": False,
            "error": (
                "ID de jogador inválido."
            ),
        }


    # ========================================================
    # 🏰 LOCALIZA CLÃ
    # ========================================================

    cla = (
        clan_manager
        .obter_cla_do_jogador(
            player_id
        )
    )


    if not cla:

        return {
            "success": False,
            "error": (
                "Você não pertence "
                "a um clã."
            ),
        }


    clan_id = (
        cla["_id"]
    )


    # ========================================================
    # 👑 SOMENTE O LÍDER
    # ========================================================

    if (
        cla.get(
            "lider_id"
        )
        !=
        player_id
    ):

        return {
            "success": False,

            "error": (
                "Somente o líder do clã "
                "pode realizar a inscrição "
                "na Guerra Semanal."
            ),
        }


    # ========================================================
    # 📅 FASE DA SEMANA
    # ========================================================

    calendario = (
        obter_estado_calendario()
    )


    if (
        not calendario.get(
            "inscricoes_abertas"
        )
        and
        not GUERRA_MODO_TESTE
    ):

        return {
            "success": False,

            "error": (
                "As inscrições da Guerra "
                "de Clãs não estão abertas."
            ),

            "fase":
                calendario.get(
                    "fase"
                ),

            "calendario":
                serializar_calendario(
                    calendario
                ),
        }


    semana_id = (
        calendario[
            "semana_id"
        ]
    )


    # ========================================================
    # 🔁 IDEMPOTÊNCIA
    # ========================================================
    #
    # Se o botão for tocado duas vezes,
    # não cria duas inscrições.
    # ========================================================

    existente = (
        obter_inscricao_cla(
            clan_id=
                clan_id,

            semana_id=
                semana_id,
        )
    )


    if existente:

        return {
            "success": True,

            "ja_inscrito":
                True,

            "message": (
                "Seu clã já está inscrito "
                "na Guerra desta semana."
            ),

            "inscricao":
                serializar_inscricao(
                    existente
                ),
        }


    # ========================================================
    # ⚔️ CATEGORIA MÁXIMA
    # ========================================================

    nivel = int(
        cla.get(
            "nivel",
            1,
        )
        or 1
    )


    categoria_maxima = (
        obter_categoria_maxima_por_nivel(
            nivel
        )
    )


    categoria_config = (
        obter_config_categoria(
            categoria_maxima
        )
        or {}
    )


    # ========================================================
    # 🛡️ SNAPSHOT DO CLÃ
    # ========================================================
    #
    # Guardamos a identidade do clã no
    # momento da inscrição.
    #
    # Isso é importante para histórico.
    # ========================================================

    cla_serializado = (
        clan_manager.serializar_cla(
            cla
        )
        or {}
    )


    agora = (
        _agora()
    )


    nova_inscricao = {

        "schema_version":
            CLAN_WAR_SCHEMA_VERSION,

        "tipo_documento":
            WAR_DOC_INSCRICAO,

        "tipo_guerra":
            GUERRA_TIPO_OFICIAL,

        "semana_id":
            semana_id,

        "status":
            GUERRA_STATUS_INSCRICOES,

        # ====================================================
        # 🏰 CLÃ
        # ====================================================

        "clan_id":
            clan_id,

        "clan_snapshot": {

            "nome":
                cla.get(
                    "nome",
                    "",
                ),

            "tag":
                cla.get(
                    "tag",
                    "",
                ),

            "logo_id":
                cla_serializado.get(
                    "logo_id"
                ),

            "logo_url":
                cla_serializado.get(
                    "logo_url"
                ),

            "nivel":
                nivel,

            "membros_total":
                int(
                    cla.get(
                        "membros_total",
                        0,
                    )
                    or 0
                ),
        },

        # ====================================================
        # 👑 QUEM INSCREVEU
        # ====================================================

        "inscrito_por":
            player_id,

        # ====================================================
        # ⚔️ CATEGORIA
        # ====================================================

        "categoria_maxima":
            categoria_maxima,

        "categoria_maxima_nome":
            categoria_config.get(
                "nome"
            ),

        # A categoria efetiva só será
        # descoberta após as inscrições
        # individuais dos membros.

        "categoria_efetiva":
            None,

        # ====================================================
        # 👥 PARTICIPANTES
        # ====================================================

        "participantes":
            [],

        "participantes_total":
            0,

        # ====================================================
        # 👥 QUÓRUM
        # ====================================================

        "quorum": {

            "status":
                QUORUM_STATUS_EM_FORMACAO,

            "minimo":
                GUERRA_MINIMO_JOGADORES_POR_CLA,

            "participantes_total":
                0,

            "faltam":
                GUERRA_MINIMO_JOGADORES_POR_CLA,

            "atingido":
                False,

            "encerrado":
                False,

            "elegivel_matchmaking":
                False,

            "avaliado_em":
                None,

            "atualizado_em":
                agora,
        },

        # ====================================================
        # 🔒 ESCALAÇÃO
        # ====================================================

        "escalacao": {
            "travada":
                False,

            "travada_em":
                None,

            "confirmada_por":
                None,

            "categoria":
                None,

            "categoria_nome":
                None,

            "titulares_total":
                0,

            "reservas_total":
                0,

            "jogadores":
                [],

            "reservas":
                [],
        },

        # ====================================================
        # ⚖️ MATCHMAKING
        # ====================================================

        "matchmaking": {
            "processado":
                False,

            "processado_em":
                None,

            "guerra_id":
                None,
        },

        # ====================================================
        # 📅 CALENDÁRIO DAQUELA SEMANA
        # ====================================================

        "calendario": {

            "timezone":
                GUERRA_SEMANAL_TIMEZONE,

            "inscricoes_abrem":
                calendario[
                    "inscricoes_abrem"
                ].astimezone(
                    timezone.utc
                ),

            "inscricoes_fecham":
                calendario[
                    "inscricoes_fecham"
                ].astimezone(
                    timezone.utc
                ),

            "escalacoes_travam":
                calendario[
                    "escalacoes_travam"
                ].astimezone(
                    timezone.utc
                ),

            "pareamento":
                calendario[
                    "pareamento"
                ].astimezone(
                    timezone.utc
                ),

            "guerra_abre":
                calendario[
                    "guerra_abre"
                ].astimezone(
                    timezone.utc
                ),

            "guerra_fecha":
                calendario[
                    "guerra_fecha"
                ].astimezone(
                    timezone.utc
                ),
        },

        # ====================================================
        # 📜 HISTÓRICO
        # ====================================================

        "historico": [
            {
                "tipo":
                    "inscricao_clan",

                "mensagem":
                    (
                        "Clã inscrito na "
                        "Guerra Semanal."
                    ),

                "autor_id":
                    player_id,

                "criado_em":
                    agora,
            }
        ],

        "criado_em":
            agora,

        "atualizado_em":
            agora,
    }


    # ========================================================
    # 💾 SALVAR
    # ========================================================

    try:

        resultado = (
            clan_wars_collection
            .insert_one(
                nova_inscricao
            )
        )


        nova_inscricao[
            "_id"
        ] = (
            resultado.inserted_id
        )


    except DuplicateKeyError:

        # Segurança contra dois pedidos
        # simultâneos do mesmo botão.

        existente = (
            obter_inscricao_cla(
                clan_id=
                    clan_id,

                semana_id=
                    semana_id,
            )
        )


        if existente:

            return {
                "success": True,

                "ja_inscrito":
                    True,

                "message": (
                    "Seu clã já está "
                    "inscrito nesta semana."
                ),

                "inscricao":
                    serializar_inscricao(
                        existente
                    ),
            }


        return {
            "success": False,

            "error": (
                "Não foi possível confirmar "
                "a inscrição do clã."
            ),
        }


    except PyMongoError as erro:

        print(
            "❌ [GUERRA DE CLÃS] "
            "Erro ao inscrever clã: "
            f"{erro}"
        )


        return {
            "success": False,

            "error": (
                "Não foi possível acessar "
                "os registros da Guerra "
                "de Clãs."
            ),
        }


    # ========================================================
    # ✅ RESULTADO
    # ========================================================

    return {
        "success": True,

        "ja_inscrito":
            False,

        "message": (
            f"O clã {cla.get('nome', '')} "
            "foi inscrito na Guerra "
            "Semanal!"
        ),

        "inscricao":
            serializar_inscricao(
                nova_inscricao
            ),
    }

# ============================================================
# ⚔️ MEMBRO — PARTICIPAR DA GUERRA
# ============================================================

def inscrever_jogador_na_guerra(
    user_id,
):
    player_id = (
        _object_id(
            user_id
        )
    )


    if not player_id:

        return {
            "success": False,
            "error":
                "ID de jogador inválido.",
        }


    # ========================================================
    # 🛡️ CLÃ ATUAL
    # ========================================================

    cla = (
        clan_manager
        .obter_cla_do_jogador(
            player_id
        )
    )


    if not cla:

        return {
            "success": False,
            "error":
                "Você não pertence a um clã.",
        }


    clan_id = (
        cla["_id"]
    )


    # ========================================================
    # 📅 FASE
    # ========================================================

    calendario = (
        obter_estado_calendario()
    )


    if (
        not calendario.get(
            "inscricoes_abertas"
        )
        and
        not GUERRA_MODO_TESTE
    ):

        return {
            "success": False,

            "error":
                (
                    "As inscrições dos "
                    "guerreiros estão fechadas."
                ),

            "fase":
                calendario.get(
                    "fase"
                ),
        }


    semana_id = (
        calendario[
            "semana_id"
        ]
    )

    # ========================================================
    # 🩹 LIMPA INSCRIÇÃO DE CLÃ ANTERIOR
    # ========================================================

    _reparar_participacao_orfa(

        player_id=
            player_id,

        clan_id_atual=
            clan_id,

        semana_id=
            semana_id,
    )

    # ========================================================
    # ⚔️ CLÃ PRECISA ESTAR INSCRITO
    # ========================================================

    inscricao = (
        obter_inscricao_cla(
            clan_id,
            semana_id,
        )
    )


    if not inscricao:

        return {
            "success": False,

            "error":
                (
                    "Seu clã ainda não foi "
                    "inscrito na Guerra Semanal."
                ),
        }


    # ========================================================
    # 🔒 ESCALAÇÃO NÃO PODE ESTAR TRAVADA
    # ========================================================

    if (
        inscricao
        .get(
            "escalacao",
            {}
        )
        .get(
            "travada"
        )
    ):

        return {
            "success": False,

            "error":
                (
                    "A escalação deste clã "
                    "já foi travada."
                ),
        }


    # ========================================================
    # 🔎 JÁ PARTICIPA DE ALGUM CLÃ NESTA SEMANA?
    # ========================================================

    participacao_existente = (
        obter_inscricao_participante(
            player_id,
            semana_id,
        )
    )


    if participacao_existente:

        mesmo_cla = (
            participacao_existente.get(
                "clan_id"
            )
            ==
            clan_id
        )


        if mesmo_cla:

            return {
                "success": True,

                "ja_inscrito":
                    True,

                "message":
                    (
                        "Você já está inscrito "
                        "para representar seu clã."
                    ),

                "inscricao":
                    serializar_inscricao(
                        participacao_existente
                    ),
            }


        return {
            "success": False,

            "error":
                (
                    "Você já está registrado "
                    "por outro clã nesta "
                    "Guerra Semanal."
                ),
        }


    participante = (
        _criar_snapshot_participante(
            player_id
        )
    )


    # ========================================================
    # 💾 INSCRIÇÃO ATÔMICA
    # ========================================================

    try:

        inscricao_atualizada = (
            clan_wars_collection
            .find_one_and_update(

                {
                    "_id":
                        inscricao["_id"],

                    "participantes.user_id": {
                        "$ne":
                            player_id
                    },

                    "escalacao.travada": {
                        "$ne":
                            True
                    },
                },

                {

                    "$push": {
                        "participantes":
                            participante,

                        "historico": {
                            "tipo":
                                "jogador_inscrito",

                            "mensagem":
                                (
                                    f"{participante['nome']} "
                                    "se inscreveu para lutar."
                                ),

                            "autor_id":
                                player_id,

                            "criado_em":
                                _agora(),
                        },
                    },
                },

                return_document=
                    ReturnDocument.AFTER,
            )
        )


    except DuplicateKeyError:

        return {
            "success": False,

            "error":
                (
                    "Você já está registrado "
                    "em outra inscrição desta "
                    "Guerra Semanal."
                ),
        }


    except PyMongoError as erro:

        print(
            "❌ [GUERRA DE CLÃS] "
            "Erro ao registrar jogador: "
            f"{erro}"
        )


        return {
            "success": False,

            "error":
                (
                    "Não foi possível registrar "
                    "sua participação."
                ),
        }


    if not inscricao_atualizada:

        return {
            "success": False,

            "error":
                (
                    "Sua inscrição não pôde "
                    "ser confirmada."
                ),
        }


    inscricao_atualizada = (
        _recalcular_categoria_inscricao(
            inscricao_atualizada
        )
    )

    _avaliar_quorum_inscricao(
        inscricao_atualizada,
        calendario,
    )

    total = len(
        inscricao_atualizada.get(
            "participantes",
            []
        )
        or []
    )


    faltam = max(
        0,

        GUERRA_MINIMO_JOGADORES_POR_CLA
        -
        total,
    )


    return {
        "success": True,

        "ja_inscrito":
            False,

        "message":
            (
                "Você se inscreveu para "
                "representar seu clã!"
            ),

        "participantes_total":
            total,

        "faltam_para_minimo":
            faltam,

        "categoria_efetiva":
            inscricao_atualizada.get(
                "categoria_efetiva"
            ),

        "categoria_efetiva_nome":
            inscricao_atualizada.get(
                "categoria_efetiva_nome"
            ),
    }

# ============================================================
# 👑 LÍDER — CONFIRMAR ESCALAÇÃO
# ============================================================

def confirmar_escalacao_cla(
    user_id,
    titulares_ids,
):
    """
    Confirma e trava a escalação oficial
    do clã para a Guerra da semana.

    A quantidade de titulares precisa ser
    exatamente igual à categoria efetiva.

    Todos os inscritos não selecionados
    tornam-se reservas automaticamente.
    """

    player_id = _object_id(
        user_id
    )


    if not player_id:

        return {
            "success": False,
            "error":
                "ID de jogador inválido.",
        }


    # ========================================================
    # 🏰 LOCALIZA O CLÃ
    # ========================================================

    cla = (
        clan_manager
        .obter_cla_do_jogador(
            player_id
        )
    )


    if not cla:

        return {
            "success": False,
            "error":
                "Você não pertence a um clã.",
        }


    clan_id = cla["_id"]


    # ========================================================
    # 👑 SOMENTE O LÍDER
    # ========================================================

    if (
        cla.get(
            "lider_id"
        )
        !=
        player_id
    ):

        return {
            "success": False,

            "error":
                (
                    "Somente o líder do clã "
                    "pode confirmar a escalação."
                ),
        }


    # ========================================================
    # 📅 FASE ATUAL
    # ========================================================

    calendario = (
        obter_estado_calendario()
    )


    fase = str(
        calendario.get(
            "fase",
            ""
        )
    ).strip()


    if (
        fase
        !=
        GUERRA_STATUS_ESCALACAO
    ):

        return {
            "success": False,

            "error":
                (
                    "A escalação só pode ser "
                    "confirmada durante a fase "
                    "de escalação."
                ),

            "fase":
                fase,
        }


    semana_id = (
        calendario[
            "semana_id"
        ]
    )


    # ========================================================
    # ⚔️ INSCRIÇÃO DO CLÃ
    # ========================================================

    inscricao = (
        obter_inscricao_cla(
            clan_id,
            semana_id,
        )
    )


    if not inscricao:

        return {
            "success": False,

            "error":
                (
                    "Seu clã não possui inscrição "
                    "na Guerra desta semana."
                ),
        }


    # ========================================================
    # 👥 QUÓRUM
    # ========================================================

    quorum = (
        _avaliar_quorum_inscricao(
            inscricao,
            calendario,
        )
        or {}
    )


    if (
        quorum.get(
            "status"
        )
        !=
        QUORUM_STATUS_APROVADO
    ):

        return {
            "success": False,

            "error":
                (
                    "O clã não possui quórum "
                    "aprovado para formar "
                    "uma escalação."
                ),
        }


    # ========================================================
    # 🔒 JÁ CONFIRMADA
    # ========================================================

    escalacao_atual = (
        inscricao.get(
            "escalacao",
            {}
        )
        or {}
    )


    if escalacao_atual.get(
        "travada"
    ):

        return {
            "success": True,

            "ja_confirmada":
                True,

            "message":
                (
                    "A escalação deste clã "
                    "já está confirmada."
                ),

            "escalacao":
                _json_seguro(
                    escalacao_atual
                ),
        }


    # ========================================================
    # 👥 PARTICIPANTES INSCRITOS
    # ========================================================

    participantes = (
        inscricao.get(
            "participantes",
            []
        )
        or []
    )


    if not participantes:

        return {
            "success": False,

            "error":
                "Não existem guerreiros inscritos.",
        }


    # ========================================================
    # ⚔️ CATEGORIA EFETIVA
    # ========================================================

    inscricao = (
        _recalcular_categoria_inscricao(
            inscricao
        )
    )


    categoria_tamanho = (
        inscricao.get(
            "categoria_efetiva"
        )
    )


    categoria_nome = (
        inscricao.get(
            "categoria_efetiva_nome"
        )
    )


    if not categoria_tamanho:

        return {
            "success": False,

            "error":
                (
                    "Não foi possível determinar "
                    "a categoria da Guerra."
                ),
        }


    categoria_tamanho = int(
        categoria_tamanho
    )


    # ========================================================
    # 📥 NORMALIZA LISTA ENVIADA
    # ========================================================

    if not isinstance(
        titulares_ids,
        list,
    ):

        return {
            "success": False,

            "error":
                (
                    "A lista de titulares "
                    "é inválida."
                ),
        }


    titulares_normalizados = []


    for valor in titulares_ids:

        jogador_id = (
            _object_id(
                valor
            )
        )


        if not jogador_id:

            return {
                "success": False,

                "error":
                    (
                        "Existe um jogador inválido "
                        "na escalação."
                    ),
            }


        if (
            jogador_id
            not in
            titulares_normalizados
        ):

            titulares_normalizados.append(
                jogador_id
            )


    # ========================================================
    # 🔢 QUANTIDADE EXATA
    # ========================================================

    if (
        len(
            titulares_normalizados
        )
        !=
        categoria_tamanho
    ):

        return {
            "success": False,

            "error":
                (
                    "A escalação precisa possuir "
                    f"exatamente {categoria_tamanho} "
                    "titulares."
                ),

            "necessarios":
                categoria_tamanho,

            "selecionados":
                len(
                    titulares_normalizados
                ),
        }


    # ========================================================
    # 🔎 MAPA DOS INSCRITOS
    # ========================================================

    participantes_por_id = {}


    for participante in participantes:

        participante_id = (
            _object_id(
                participante.get(
                    "user_id"
                )
            )
        )


        if participante_id:

            participantes_por_id[
                participante_id
            ] = participante


    # ========================================================
    # 🛡️ TODOS PRECISAM ESTAR INSCRITOS
    # ========================================================

    for jogador_id in (
        titulares_normalizados
    ):

        if (
            jogador_id
            not in
            participantes_por_id
        ):

            return {
                "success": False,

                "error":
                    (
                        "Um dos jogadores escolhidos "
                        "não está inscrito pelo clã."
                    ),
            }


    # ========================================================
    # ✅ TITULARES
    # ========================================================

    titulares = []


    for jogador_id in (
        titulares_normalizados
    ):

        participante = dict(
            participantes_por_id[
                jogador_id
            ]
        )


        participante[
            "funcao_guerra"
        ] = "titular"


        titulares.append(
            participante
        )


    # ========================================================
    # 🪑 RESERVAS AUTOMÁTICAS
    # ========================================================

    reservas = []


    titulares_set = set(
        titulares_normalizados
    )


    for participante in participantes:

        participante_id = (
            _object_id(
                participante.get(
                    "user_id"
                )
            )
        )


        if (
            not participante_id
            or
            participante_id
            in titulares_set
        ):

            continue


        reserva = dict(
            participante
        )


        reserva[
            "funcao_guerra"
        ] = "reserva"


        reservas.append(
            reserva
        )


    agora = _agora()


    nova_escalacao = {

        "travada":
            True,

        "travada_em":
            agora,

        "confirmada_por":
            player_id,

        "categoria":
            categoria_tamanho,

        "categoria_nome":
            categoria_nome,

        "titulares_total":
            len(
                titulares
            ),

        "reservas_total":
            len(
                reservas
            ),

        "jogadores":
            titulares,

        "reservas":
            reservas,
    }


    # ========================================================
    # 💾 TRAVA ATÔMICA
    # ========================================================

    atualizada = (
        clan_wars_collection
        .find_one_and_update(

            {
                "_id":
                    inscricao["_id"],

                "escalacao.travada": {
                    "$ne":
                        True
                },
            },

            {
                "$set": {

                    "escalacao":
                        nova_escalacao,

                    "status":
                        GUERRA_STATUS_ESCALACAO,

                    "atualizado_em":
                        agora,
                },

                "$push": {

                    "historico": {

                        "tipo":
                            "escalacao_confirmada",

                        "mensagem":
                            (
                                "O líder confirmou "
                                "a escalação oficial "
                                f"de {categoria_nome}."
                            ),

                        "autor_id":
                            player_id,

                        "criado_em":
                            agora,
                    },
                },
            },

            return_document=
                ReturnDocument.AFTER,
        )
    )


    if not atualizada:

        existente = (
            obter_inscricao_cla(
                clan_id,
                semana_id,
            )
        )


        if (
            existente
            and
            (
                existente
                .get(
                    "escalacao",
                    {}
                )
                .get(
                    "travada"
                )
            )
        ):

            return {
                "success": True,

                "ja_confirmada":
                    True,

                "message":
                    (
                        "A escalação já havia "
                        "sido confirmada."
                    ),

                "escalacao":
                    _json_seguro(
                        existente.get(
                            "escalacao",
                            {}
                        )
                    ),
            }


        return {
            "success": False,

            "error":
                (
                    "Não foi possível confirmar "
                    "a escalação."
                ),
        }


    return {
        "success": True,

        "ja_confirmada":
            False,

        "message":
            (
                "Escalação confirmada "
                "com sucesso!"
            ),

        "categoria":
            categoria_tamanho,

        "categoria_nome":
            categoria_nome,

        "titulares_total":
            len(
                titulares
            ),

        "reservas_total":
            len(
                reservas
            ),

        "escalacao":
            _json_seguro(
                nova_escalacao
            ),
    }

# ============================================================
# 🚪 MEMBRO — SAIR DA INSCRIÇÃO
# ============================================================

def remover_jogador_da_guerra(
    user_id,
):
    player_id = (
        _object_id(
            user_id
        )
    )


    if not player_id:

        return {
            "success": False,
            "error":
                "ID de jogador inválido.",
        }


    calendario = (
        obter_estado_calendario()
    )


    if (
        not calendario.get(
            "inscricoes_abertas"
        )
        and
        not GUERRA_MODO_TESTE
    ):

        return {
            "success": False,

            "error":
                (
                    "O período de inscrições "
                    "já foi encerrado."
                ),
        }


    cla = (
        clan_manager
        .obter_cla_do_jogador(
            player_id
        )
    )


    if not cla:

        return {
            "success": False,
            "error":
                "Você não pertence a um clã.",
        }


    inscricao = (
        obter_inscricao_cla(
            cla["_id"],
            calendario[
                "semana_id"
            ],
        )
    )


    if not inscricao:

        return {
            "success": False,

            "error":
                (
                    "Seu clã não possui uma "
                    "inscrição ativa."
                ),
        }


    if (
        inscricao
        .get(
            "escalacao",
            {}
        )
        .get(
            "travada"
        )
    ):

        return {
            "success": False,

            "error":
                (
                    "A escalação já foi "
                    "travada e não pode mais "
                    "ser alterada."
                ),
        }


    participante = next(
        (
            item

            for item
            in (
                inscricao.get(
                    "participantes",
                    []
                )
                or []
            )

            if item.get(
                "user_id"
            )
            ==
            player_id
        ),

        None,
    )


    if not participante:

        return {
            "success": True,

            "nao_inscrito":
                True,

            "message":
                (
                    "Você não estava inscrito "
                    "nesta guerra."
                ),
        }


    nome = (
        participante.get(
            "nome"
        )
        or
        "Aventureiro"
    )


    inscricao_atualizada = (
        clan_wars_collection
        .find_one_and_update(

            {
                "_id":
                    inscricao["_id"],

                "participantes.user_id":
                    player_id,

                "escalacao.travada": {
                    "$ne":
                        True
                },
            },

            {
                "$pull": {

                    "participantes": {
                        "user_id":
                            player_id,
                    },

                    "escalacao.jogadores": {
                        "user_id":
                            player_id,
                    },

                    "escalacao.reservas": {
                        "user_id":
                            player_id,
                    },
                },

                "$inc": {
                    "participantes_total":
                        -1,
                },

                "$push": {
                    "historico": {
                        "tipo":
                            "jogador_saiu",

                        "mensagem":
                            (
                                f"{nome} retirou "
                                "sua inscrição."
                            ),

                        "autor_id":
                            player_id,

                        "criado_em":
                            _agora(),
                    },
                },

                "$set": {
                    "atualizado_em":
                        _agora(),
                },
            },

            return_document=
                ReturnDocument.AFTER,
        )
    )


    if not inscricao_atualizada:

        return {
            "success": False,

            "error":
                (
                    "Não foi possível retirar "
                    "sua inscrição."
                ),
        }


    inscricao_atualizada = (
        _recalcular_categoria_inscricao(
            inscricao_atualizada
        )
    )

    _avaliar_quorum_inscricao(
        inscricao_atualizada,
        calendario,
    )

    total = len(
        inscricao_atualizada.get(
            "participantes",
            []
        )
        or []
    )


    return {
        "success": True,

        "message":
            (
                "Você saiu da inscrição "
                "da Guerra de Clãs."
            ),

        "participantes_total":
            total,

        "faltam_para_minimo":
            max(
                0,

                GUERRA_MINIMO_JOGADORES_POR_CLA
                -
                total,
            ),

        "categoria_efetiva":
            inscricao_atualizada.get(
                "categoria_efetiva"
            ),

        "categoria_efetiva_nome":
            inscricao_atualizada.get(
                "categoria_efetiva_nome"
            ),
    }

# ============================================================
# ⚖️ EXECUTAR PAREAMENTO DA SEMANA
# ============================================================

def executar_pareamento_semana(
    semana_id=None,
    executado_por="sistema",
):
    calendario = (
        obter_estado_calendario()
    )


    fase = str(
        calendario.get(
            "fase",
            ""
        )
    ).strip()


    # No modo real, após 19h o calendário
    # já entra em AGENDADA.
    #
    # No GM temos a fase PAREAMENTO.
    if fase not in {
        GUERRA_STATUS_PAREAMENTO,
        GUERRA_STATUS_AGENDADA,
    }:

        return {
            "success":
                False,

            "error":
                (
                    "O pareamento só pode ser "
                    "executado durante a fase "
                    "de Pareamento."
                ),

            "fase":
                fase,
        }


    semana_id = str(
        semana_id
        or
        calendario.get(
            "semana_id"
        )
        or
        obter_semana_id()
    ).strip()


    agora = (
        _agora()
    )


    # ========================================================
    # ⚔️ ESCALAÇÕES CANDIDATAS
    # ========================================================

    inscricoes = list(
        clan_wars_collection.find({

            "tipo_documento":
                WAR_DOC_INSCRICAO,

            "semana_id":
                semana_id,

            "status": {
                "$ne":
                    GUERRA_STATUS_CANCELADA
            },

            "escalacao.travada":
                True,
        })
    )


    candidatos_por_categoria = {}


    ignorados = []


    for inscricao in inscricoes:

        # Se já existe guerra para esse clã,
        # ele não pode ser pareado novamente.
        guerra_existente = (
            obter_guerra_cla(
                inscricao.get(
                    "clan_id"
                ),
                semana_id,
            )
        )


        if guerra_existente:
            continue


        quorum = (
            _avaliar_quorum_inscricao(
                inscricao,
                calendario,
            )
            or {}
        )


        if (
            quorum.get(
                "status"
            )
            !=
            QUORUM_STATUS_APROVADO
        ):

            ignorados.append({
                "clan_id":
                    str(
                        inscricao.get(
                            "clan_id"
                        )
                    ),

                "motivo":
                    "quorum_nao_aprovado",
            })

            continue


        escalacao = (
            inscricao.get(
                "escalacao",
                {}
            )
            or {}
        )


        categoria = (
            escalacao.get(
                "categoria"
            )
            or
            inscricao.get(
                "categoria_efetiva"
            )
        )


        try:
            categoria = int(
                categoria
            )

        except (
            TypeError,
            ValueError,
        ):
            categoria = 0


        titulares = (
            escalacao.get(
                "jogadores",
                []
            )
            or []
        )


        if (
            not categoria
            or
            len(
                titulares
            )
            !=
            categoria
        ):

            ignorados.append({
                "clan_id":
                    str(
                        inscricao.get(
                            "clan_id"
                        )
                    ),

                "motivo":
                    "escalacao_invalida",
            })

            continue


        rating = (
            _obter_rating_guerra_cla(
                inscricao.get(
                    "clan_id"
                )
            )
        )


        candidatos_por_categoria.setdefault(
            categoria,
            []
        ).append({

            "inscricao":
                inscricao,

            "rating":
                rating,
        })


    guerras_criadas = []


    aguardando = []


    # ========================================================
    # ⚖️ PAREIA SOMENTE CLÃS DA MESMA CATEGORIA
    # ========================================================

    for (
        categoria,
        candidatos
    ) in candidatos_por_categoria.items():

        candidatos.sort(
            key=lambda item: (
                -int(
                    item.get(
                        "rating",
                        GUERRA_RATING_INICIAL,
                    )
                ),

                str(
                    item[
                        "inscricao"
                    ].get(
                        "clan_id"
                    )
                ),
            )
        )


        indice = 0


        while (
            indice + 1
            <
            len(
                candidatos
            )
        ):

            item_a = (
                candidatos[
                    indice
                ]
            )


            item_b = (
                candidatos[
                    indice + 1
                ]
            )


            inscricao_a = (
                item_a[
                    "inscricao"
                ]
            )


            inscricao_b = (
                item_b[
                    "inscricao"
                ]
            )


            clan_a_id = (
                inscricao_a[
                    "clan_id"
                ]
            )


            clan_b_id = (
                inscricao_b[
                    "clan_id"
                ]
            )


            snapshot_a = (
                inscricao_a.get(
                    "clan_snapshot",
                    {}
                )
                or {}
            )


            snapshot_b = (
                inscricao_b.get(
                    "clan_snapshot",
                    {}
                )
                or {}
            )


            config_categoria = (
                obter_config_categoria(
                    categoria
                )
                or {}
            )


            frentes = (
                _criar_frentes_guerra(
                    inscricao_a,
                    inscricao_b,
                    categoria,
                )
            )


            nova_guerra = {

                "schema_version":
                    CLAN_WAR_SCHEMA_VERSION,

                "tipo_documento":
                    WAR_DOC_GUERRA,

                "tipo_guerra":
                    GUERRA_TIPO_OFICIAL,

                "semana_id":
                    semana_id,

                "status":
                    GUERRA_STATUS_AGENDADA,

                "categoria":
                    categoria,

                "categoria_nome":
                    config_categoria.get(
                        "nome"
                    )
                    or
                    f"{categoria} x {categoria}",

                "frentes_total":
                    len(
                        frentes
                    ),

                "clans_ids": [
                    clan_a_id,
                    clan_b_id,
                ],

                "clans": [

                    {
                        "lado":
                            "a",

                        "clan_id":
                            clan_a_id,

                        "nome":
                            snapshot_a.get(
                                "nome",
                                "Clã A",
                            ),

                        "tag":
                            snapshot_a.get(
                                "tag",
                                "",
                            ),

                        "logo_url":
                            snapshot_a.get(
                                "logo_url"
                            ),

                        "nivel":
                            snapshot_a.get(
                                "nivel",
                                1,
                            ),

                        "rating":
                            item_a.get(
                                "rating",
                                GUERRA_RATING_INICIAL,
                            ),

                        "escalacao":
                            inscricao_a.get(
                                "escalacao",
                                {},
                            ),
                    },

                    {
                        "lado":
                            "b",

                        "clan_id":
                            clan_b_id,

                        "nome":
                            snapshot_b.get(
                                "nome",
                                "Clã B",
                            ),

                        "tag":
                            snapshot_b.get(
                                "tag",
                                "",
                            ),

                        "logo_url":
                            snapshot_b.get(
                                "logo_url"
                            ),

                        "nivel":
                            snapshot_b.get(
                                "nivel",
                                1,
                            ),

                        "rating":
                            item_b.get(
                                "rating",
                                GUERRA_RATING_INICIAL,
                            ),

                        "escalacao":
                            inscricao_b.get(
                                "escalacao",
                                {},
                            ),
                    },
                ],

                "frentes":
                    frentes,

                "resultado": {

                    "vencedor_clan_id":
                        None,

                    "perdedor_clan_id":
                        None,

                    "empate":
                        False,

                    "frentes_clan_a":
                        0,

                    "frentes_clan_b":
                        0,

                    "finalizada_em":
                        None,
                },

                "historico": [

                    {
                        "tipo":
                            "pareamento_criado",

                        "mensagem":
                            (
                                f"{snapshot_a.get('nome', 'Clã A')} "
                                "foi pareado contra "
                                f"{snapshot_b.get('nome', 'Clã B')}."
                            ),

                        "autor":
                            str(
                                executado_por
                                or
                                "sistema"
                            ),

                        "criado_em":
                            agora,
                    }
                ],

                "criado_em":
                    agora,

                "atualizado_em":
                    agora,
            }


            try:

                resultado_insert = (
                    clan_wars_collection
                    .insert_one(
                        nova_guerra
                    )
                )


                guerra_id = (
                    resultado_insert
                    .inserted_id
                )


                nova_guerra[
                    "_id"
                ] = guerra_id


            except DuplicateKeyError:

                # Segurança/idempotência.
                existente = (
                    clan_wars_collection
                    .find_one({

                        "tipo_documento":
                            WAR_DOC_GUERRA,

                        "semana_id":
                            semana_id,

                        "clans_ids": {
                            "$all": [
                                clan_a_id,
                                clan_b_id,
                            ]
                        },
                    })
                )


                if not existente:

                    indice += 2
                    continue


                nova_guerra = (
                    existente
                )


                guerra_id = (
                    existente[
                        "_id"
                    ]
                )


            # ====================================================
            # 💾 MARCA AS DUAS INSCRIÇÕES
            # ====================================================

            clan_wars_collection.update_many(

                {
                    "_id": {
                        "$in": [
                            inscricao_a[
                                "_id"
                            ],
                            inscricao_b[
                                "_id"
                            ],
                        ]
                    }
                },

                {
                    "$set": {

                        "status":
                            GUERRA_STATUS_AGENDADA,

                        "matchmaking.processado":
                            True,

                        "matchmaking.processado_em":
                            agora,

                        "matchmaking.guerra_id":
                            guerra_id,

                        "atualizado_em":
                            agora,
                    }
                },
            )


            # Adversário A
            clan_wars_collection.update_one(
                {
                    "_id":
                        inscricao_a[
                            "_id"
                        ]
                },
                {
                    "$set": {
                        "matchmaking.adversario_clan_id":
                            clan_b_id
                    }
                },
            )


            # Adversário B
            clan_wars_collection.update_one(
                {
                    "_id":
                        inscricao_b[
                            "_id"
                        ]
                },
                {
                    "$set": {
                        "matchmaking.adversario_clan_id":
                            clan_a_id
                    }
                },
            )


            guerras_criadas.append({

                "guerra_id":
                    str(
                        guerra_id
                    ),

                "categoria":
                    categoria,

                "clan_a":
                    snapshot_a.get(
                        "nome",
                        "Clã A",
                    ),

                "clan_b":
                    snapshot_b.get(
                        "nome",
                        "Clã B",
                    ),

                "frentes":
                    len(
                        frentes
                    ),
            })


            indice += 2


        # ====================================================
        # 🕐 SOBROU UM CLÃ SEM ADVERSÁRIO
        # ====================================================

        if (
            indice
            <
            len(
                candidatos
            )
        ):

            sobra = (
                candidatos[
                    indice
                ][
                    "inscricao"
                ]
            )


            clan_wars_collection.update_one(
                {
                    "_id":
                        sobra[
                            "_id"
                        ]
                },
                {
                    "$set": {

                        "matchmaking.processado":
                            False,

                        "matchmaking.estado":
                            "aguardando_adversario",

                        "atualizado_em":
                            agora,
                    }
                },
            )


            aguardando.append({

                "clan_id":
                    str(
                        sobra.get(
                            "clan_id"
                        )
                    ),

                "nome":
                    (
                        sobra.get(
                            "clan_snapshot",
                            {}
                        )
                        or {}
                    ).get(
                        "nome",
                        "Clã",
                    ),

                "categoria":
                    categoria,
            })


    return {
        "success":
            True,

        "semana_id":
            semana_id,

        "guerras_criadas_total":
            len(
                guerras_criadas
            ),

        "guerras":
            guerras_criadas,

        "aguardando_adversario":
            aguardando,

        "ignorados":
            ignorados,

        "message":
            (
                f"{len(guerras_criadas)} "
                "confronto(s) processado(s)."
            ),
    }


# ============================================================
# 🚀 PREPARAÇÃO DO MÓDULO
# ============================================================

garantir_indices()