# ============================================================
# 🏰 MUNDO DE ELDORA
# MOTOR DE MISSÕES COLETIVAS DO CLÃ
# ============================================================

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from bson import ObjectId

from modules.clan import clan_manager

from modules.clan.clan_registry import (
    PERMISSAO_GERENCIAR_MISSOES,
)

from .guild_mission_registry import (
    TIPO_CLA,

    ESCOPO_COLETIVO,

    MODO_SOLO,
    MODO_GRUPO,
    MODO_QUALQUER,

    FREQUENCIA_UNICA,
    FREQUENCIA_DIARIA,
    FREQUENCIA_SEMANAL,

    OBJETIVO_MATAR_MOB,

    REGIOES_GUILDA,

    obter_missao,
    listar_missoes_ativas,
)


# ============================================================
# 📌 STATUS
# ============================================================

STATUS_ATIVA = "ativa"
STATUS_PRONTA_ENTREGA = "pronta_entrega"
STATUS_ENTREGANDO = "entregando"


# ============================================================
# 🕐 FUSO DO JOGO
# ============================================================

FUSO_GUILDA = ZoneInfo(
    "America/Fortaleza"
)


# ============================================================
# 🔧 HELPERS
# ============================================================

def _agora():
    return datetime.now(
        FUSO_GUILDA
    )


def _object_id(valor):

    if isinstance(valor, ObjectId):
        return valor

    if valor is None:
        return None

    texto = str(valor).strip()

    if not ObjectId.is_valid(texto):
        return None

    return ObjectId(texto)


def _serializar(valor):

    if isinstance(valor, ObjectId):
        return str(valor)

    if isinstance(valor, datetime):
        return valor.isoformat()

    if isinstance(valor, dict):
        return {
            chave: _serializar(item)
            for chave, item
            in valor.items()
        }

    if isinstance(valor, list):
        return [
            _serializar(item)
            for item in valor
        ]

    return valor


def _estado_padrao():
    return {
        "pontos": 0,
        "ativas": {},
        "concluidas": {},
    }


def _obter_estado_cla(cla):

    estado = cla.get(
        "guild_missions"
    )

    if not isinstance(
        estado,
        dict
    ):
        estado = _estado_padrao()

    if not isinstance(
        estado.get("ativas"),
        dict
    ):
        estado["ativas"] = {}

    if not isinstance(
        estado.get("concluidas"),
        dict
    ):
        estado["concluidas"] = {}

    try:
        estado["pontos"] = int(
            estado.get(
                "pontos",
                0
            ) or 0
        )

    except Exception:
        estado["pontos"] = 0

    return estado


def _cargo_membro(
    cla,
    player_id,
):

    player_id = _object_id(
        player_id
    )

    if not player_id:
        return None

    for membro in (
        cla.get("membros", [])
        or []
    ):

        if (
            membro.get("user_id")
            == player_id
        ):
            return membro.get(
                "cargo"
            )

    return None


def _nome_membro(
    cla,
    player_id,
):

    player_id = _object_id(
        player_id
    )

    for membro in (
        cla.get("membros", [])
        or []
    ):

        if (
            membro.get("user_id")
            == player_id
        ):

            return membro.get(
                "nome",
                "Aventureiro"
            )

    return "Aventureiro"


def _pode_gerenciar(
    cla,
    cargo,
):
    """
    Verifica se o cargo possui permissão
    para administrar missões coletivas.
    """

    return (
        clan_manager
        .tem_permissao_cla(
            cla,
            cargo,
            PERMISSAO_GERENCIAR_MISSOES,
        )
    )


# ============================================================
# ⏰ PERÍODO DA MISSÃO
# ============================================================

def obter_periodo_missao(
    missao,
    agora=None,
):

    agora = (
        agora
        if isinstance(
            agora,
            datetime
        )
        else _agora()
    )

    frequencia = missao.get(
        "frequencia",
        FREQUENCIA_UNICA,
    )

    # ========================================================
    # MISSÃO ÚNICA
    # ========================================================

    if (
        frequencia
        == FREQUENCIA_UNICA
    ):
        return "unica"


    # ========================================================
    # MISSÃO DIÁRIA
    # ========================================================

    if (
        frequencia
        == FREQUENCIA_DIARIA
    ):

        return agora.strftime(
            "%Y-%m-%d"
        )


    # ========================================================
    # MISSÃO SEMANAL
    # ========================================================

    if (
        frequencia
        == FREQUENCIA_SEMANAL
    ):

        iso = agora.isocalendar()

        return (
            f"{iso.year}-W"
            f"{iso.week:02d}"
        )


    return "unica"


# ============================================================
# 🧹 REMOVE ATIVAS DE PERÍODO ANTIGO
# ============================================================

def _limpar_ativas_expiradas(
    cla,
):

    if not cla:
        return False

    estado = _obter_estado_cla(
        cla
    )

    removidas = []

    for missao_id, estado_missao in list(
        estado["ativas"].items()
    ):

        missao = obter_missao(
            missao_id
        )

        if not missao:
            continue

        frequencia = missao.get(
            "frequencia",
            FREQUENCIA_UNICA,
        )

        # Única não expira.
        if (
            frequencia
            == FREQUENCIA_UNICA
        ):
            continue

        periodo_salvo = str(
            estado_missao.get(
                "periodo",
                ""
            )
        )

        periodo_atual = (
            obter_periodo_missao(
                missao
            )
        )

        if (
            periodo_salvo
            == periodo_atual
        ):
            continue

        removidas.append(
            missao_id
        )


    if not removidas:
        return False


    unset = {}

    for missao_id in removidas:

        unset[
            (
                "guild_missions."
                "ativas."
                f"{missao_id}"
            )
        ] = ""


    clan_manager.clans_collection.update_one(
        {
            "_id": cla["_id"]
        },
        {
            "$unset": unset,

            "$set": {
                "atualizado_em":
                    _agora()
            },
        },
    )

    print(
        "🧹 [GUILDA CLÃ] "
        f"Contratos expirados removidos "
        f"do clã {cla['_id']}: "
        f"{removidas}"
    )

    return True


# ============================================================
# 🎨 FORMATA MISSÃO
# ============================================================

def _formatar_missao(
    missao,
    estado_missao=None,
):

    estado_missao = (
        estado_missao
        if isinstance(
            estado_missao,
            dict
        )
        else {}
    )

    dados = dict(
        missao
    )

    objetivo = dict(
        missao.get(
            "objetivo",
            {}
        )
        or {}
    )

    recompensas = dict(
        missao.get(
            "recompensas",
            {}
        )
        or {}
    )

    progresso = int(
        estado_missao.get(
            "progresso",
            0
        ) or 0
    )

    total = int(
        objetivo.get(
            "quantidade",
            1
        ) or 1
    )

    contribuicoes = (
        estado_missao.get(
            "contribuicoes",
            {}
        )
        or {}
    )

    ranking = []

    if isinstance(
        contribuicoes,
        dict
    ):

        for membro_id, info in (
            contribuicoes.items()
        ):

            if isinstance(
                info,
                dict
            ):

                quantidade = int(
                    info.get(
                        "quantidade",
                        0
                    ) or 0
                )

                nome = info.get(
                    "nome",
                    "Aventureiro"
                )

            else:

                quantidade = int(
                    info or 0
                )

                nome = "Aventureiro"

            ranking.append({
                "user_id":
                    str(membro_id),

                "nome":
                    str(nome),

                "quantidade":
                    quantidade,
            })


    ranking.sort(
        key=lambda item:
            item["quantidade"],
        reverse=True,
    )


    dados["objetivo"] = objetivo
    dados["recompensas"] = recompensas

    dados["regiao_nome"] = (
        REGIOES_GUILDA.get(
            objetivo.get(
                "regiao"
            ),
            objetivo.get(
                "regiao"
            ),
        )
    )

    dados["progresso"] = min(
        progresso,
        total
    )

    dados["progresso_total"] = total

    dados["status"] = (
        estado_missao.get(
            "status"
        )
    )

    dados["periodo"] = (
        estado_missao.get(
            "periodo"
        )
    )

    dados["aceita_em"] = (
        estado_missao.get(
            "aceita_em"
        )
    )

    dados["aceita_por"] = (
        estado_missao.get(
            "aceita_por"
        )
    )

    dados["concluida_em"] = (
        estado_missao.get(
            "concluida_em"
        )
    )

    dados["ranking"] = ranking

    return _serializar(
        dados
    )


# ============================================================
# 📖 LISTAR MISSÕES COLETIVAS DO CLÃ
# ============================================================

def listar_missoes_cla(
    user_id,
):

    player_id = _object_id(
        user_id
    )

    if not player_id:

        return {
            "success": False,
            "error":
                "ID do jogador inválido.",
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


    # Remove diariamente/semanalmente
    # contratos de períodos antigos.
    if _limpar_ativas_expiradas(
        cla
    ):

        cla = (
            clan_manager
            .obter_cla_por_id(
                cla["_id"]
            )
        )


    estado = _obter_estado_cla(
        cla
    )

    cargo = _cargo_membro(
        cla,
        player_id
    )

    nivel_cla = int(
        cla.get(
            "nivel",
            1
        ) or 1
    )

    ativas = []
    disponiveis = []
    concluidas = []


    # ========================================================
    # ATIVAS
    # ========================================================

    for (
        missao_id,
        estado_missao
    ) in estado[
        "ativas"
    ].items():

        missao = obter_missao(
            missao_id
        )

        if not missao:
            continue

        if (
            missao.get("escopo")
            != ESCOPO_COLETIVO
        ):
            continue

        ativas.append(
            _formatar_missao(
                missao,
                estado_missao,
            )
        )


    # ========================================================
    # DISPONÍVEIS
    # ========================================================

    for missao in (
        listar_missoes_ativas(
            ESCOPO_COLETIVO
        )
    ):

        if (
            missao.get("tipo")
            != TIPO_CLA
        ):
            continue


        missao_id = missao["id"]


        if (
            missao_id
            in estado["ativas"]
        ):
            continue


        periodo_atual = (
            obter_periodo_missao(
                missao
            )
        )

        historico = (
            estado["concluidas"]
            .get(
                missao_id,
                {}
            )
            or {}
        )

        ultimo_periodo = str(
            historico.get(
                "ultimo_periodo",
                ""
            )
        )


        # ====================================================
        # MISSÃO ÚNICA JÁ CONCLUÍDA
        # ====================================================

        if (
            missao.get("frequencia")
            == FREQUENCIA_UNICA
            and
            historico
        ):
            continue


        # ====================================================
        # DIÁRIA/SEMANAL JÁ FEITA NESTE PERÍODO
        # ====================================================

        if (
            historico
            and
            ultimo_periodo
            == periodo_atual
        ):
            continue


        bloqueio = None

        nivel_minimo = int(
            missao.get(
                "nivel_cla_minimo",
                1
            ) or 1
        )


        if (
            nivel_cla
            < nivel_minimo
        ):

            bloqueio = (
                f"Requer clã nível "
                f"{nivel_minimo}."
            )


        dados = _formatar_missao(
            missao
        )

        dados["periodo"] = (
            periodo_atual
        )

        dados["disponivel"] = (
            bloqueio is None
        )

        dados["bloqueio"] = (
            bloqueio
        )

        disponiveis.append(
            dados
        )


    # ========================================================
    # HISTÓRICO
    # ========================================================

    for (
        missao_id,
        info
    ) in estado[
        "concluidas"
    ].items():

        missao = obter_missao(
            missao_id
        )

        if not missao:
            continue

        if (
            missao.get("escopo")
            != ESCOPO_COLETIVO
        ):
            continue

        dados = _formatar_missao(
            missao
        )

        dados["historico"] = (
            _serializar(
                info
            )
        )

        concluidas.append(
            dados
        )


    return {
        "success": True,

        "clan": {
            "id":
                str(cla["_id"]),

            "nome":
                cla.get("nome"),

            "tag":
                cla.get("tag"),

            "nivel":
                nivel_cla,
        },

        "cargo":
            cargo,

        "pode_gerenciar":
            _pode_gerenciar(
                cla,
                cargo,
            ),

        "pontos_cla":
            int(
                estado.get(
                    "pontos",
                    0
                ) or 0
            ),

        "ativas":
            ativas,

        "disponiveis":
            disponiveis,

        "concluidas":
            concluidas,
    }


# ============================================================
# 📜 ACEITAR MISSÃO COLETIVA
# ============================================================

def aceitar_missao_cla(
    user_id,
    missao_id,
):

    player_id = _object_id(
        user_id
    )

    if not player_id:

        return {
            "success": False,
            "error":
                "ID inválido.",
        }


    missao = obter_missao(
        missao_id
    )

    if not missao:

        return {
            "success": False,
            "error":
                "Missão inexistente.",
        }


    if (
        missao.get("tipo")
        != TIPO_CLA
        or
        missao.get("escopo")
        != ESCOPO_COLETIVO
    ):

        return {
            "success": False,
            "error": (
                "Este contrato não é "
                "uma missão coletiva de clã."
            ),
        }


    if not missao.get(
        "ativa",
        True
    ):

        return {
            "success": False,
            "error":
                "Contrato indisponível.",
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


    _limpar_ativas_expiradas(
        cla
    )

    cla = (
        clan_manager
        .obter_cla_por_id(
            cla["_id"]
        )
    )


    cargo = _cargo_membro(
        cla,
        player_id
    )


    if not _pode_gerenciar(
        cla,
        cargo,
    ):

        return {
            "success": False,
            "error": (
                "Seu cargo não permite "
                "aceitar missões do clã."
            ),
        }


    nivel_cla = int(
        cla.get(
            "nivel",
            1
        ) or 1
    )

    nivel_minimo = int(
        missao.get(
            "nivel_cla_minimo",
            1
        ) or 1
    )


    if (
        nivel_cla
        < nivel_minimo
    ):

        return {
            "success": False,
            "error": (
                f"O clã precisa alcançar "
                f"o nível {nivel_minimo}."
            ),
        }


    estado = _obter_estado_cla(
        cla
    )


    if (
        missao_id
        in estado["ativas"]
    ):

        return {
            "success": False,
            "error":
                "Este contrato já está ativo.",
        }


    periodo = (
        obter_periodo_missao(
            missao
        )
    )

    historico = (
        estado["concluidas"]
        .get(
            missao_id,
            {}
        )
        or {}
    )


    if (
        missao.get("frequencia")
        == FREQUENCIA_UNICA
        and
        historico
    ):

        return {
            "success": False,
            "error":
                "Este contrato já foi concluído.",
        }


    if (
        historico
        and
        str(
            historico.get(
                "ultimo_periodo",
                ""
            )
        ) == periodo
    ):

        return {
            "success": False,
            "error": (
                "Este contrato já foi "
                "concluído neste período."
            ),
        }


    agora = _agora()

    novo_estado = {

        "missao_id":
            missao_id,

        "status":
            STATUS_ATIVA,

        "periodo":
            periodo,

        "progresso":
            0,

        "aceita_em":
            agora,

        "aceita_por":
            player_id,

        "aceita_por_nome":
            _nome_membro(
                cla,
                player_id
            ),

        "concluida_em":
            None,

        "contribuicoes":
            {},
    }


    campo = (
        "guild_missions."
        "ativas."
        f"{missao_id}"
    )


    resultado = (
        clan_manager
        .clans_collection
        .update_one(
            {
                "_id":
                    cla["_id"],

                "status":
                    "ativo",

                campo: {
                    "$exists":
                        False
                },
            },
            {
                "$set": {
                    campo:
                        novo_estado,

                    "atualizado_em":
                        agora,
                },
            },
        )
    )


    if (
        resultado.modified_count
        != 1
    ):

        return {
            "success": False,
            "error": (
                "Não foi possível aceitar "
                "o contrato."
            ),
        }


    try:
        clan_manager._registrar_atividade(
            clan_id=cla["_id"],

            tipo="missao_cla",

            mensagem=(
                f"{_nome_membro(cla, player_id)} "
                f"aceitou a missão coletiva "
                f"'{missao['nome']}'."
            ),

            autor_id=
                player_id,

            autor_nome=
                _nome_membro(
                    cla,
                    player_id
                ),

            dados={
                "missao_id":
                    missao_id,

                "periodo":
                    periodo,
            },
        )

    except Exception:
        pass


    return {
        "success": True,

        "message": (
            f"Missão coletiva "
            f"'{missao['nome']}' aceita!"
        ),

        "missao":
            _formatar_missao(
                missao,
                novo_estado
            ),
    }


# ============================================================
# ⚔️ REGISTRAR ABATE COLETIVO
# ============================================================

def registrar_abate_cla(
    user_id,
    monster_id,
    regiao,
    em_grupo=False,
    quantidade=1,
):

    player_id = _object_id(
        user_id
    )

    if not player_id:
        return []


    cla = (
        clan_manager
        .obter_cla_do_jogador(
            player_id
        )
    )

    if not cla:
        return []


    _limpar_ativas_expiradas(
        cla
    )


    cla = (
        clan_manager
        .obter_cla_por_id(
            cla["_id"]
        )
    )

    if not cla:
        return []


    estado = _obter_estado_cla(
        cla
    )

    if not estado["ativas"]:
        return []


    monster_id = str(
        monster_id or ""
    ).strip()

    regiao = str(
        regiao or ""
    ).strip()


    try:
        quantidade = max(
            1,
            int(quantidade)
        )

    except Exception:
        quantidade = 1


    nome_membro = (
        _nome_membro(
            cla,
            player_id
        )
    )


    alteradas = []


    for (
        missao_id,
        estado_missao
    ) in list(
        estado["ativas"].items()
    ):


        if (
            estado_missao.get("status")
            != STATUS_ATIVA
        ):
            continue


        missao = obter_missao(
            missao_id
        )

        if not missao:
            continue


        if (
            missao.get("tipo")
            != TIPO_CLA
            or
            missao.get("escopo")
            != ESCOPO_COLETIVO
        ):
            continue


        # ====================================================
        # PERÍODO
        # ====================================================

        periodo_atual = (
            obter_periodo_missao(
                missao
            )
        )

        if (
            str(
                estado_missao.get(
                    "periodo",
                    ""
                )
            )
            != periodo_atual
        ):
            continue


        objetivo = (
            missao.get(
                "objetivo",
                {}
            )
            or {}
        )


        if (
            objetivo.get("tipo")
            != OBJETIVO_MATAR_MOB
        ):
            continue


        if (
            str(
                objetivo.get(
                    "regiao"
                )
            )
            != regiao
        ):
            continue


        mobs_validos = [
            str(mob_id)

            for mob_id in (
                objetivo.get(
                    "mob_ids",
                    []
                )
                or []
            )
        ]


        if (
            monster_id
            not in mobs_validos
        ):
            continue


        # ====================================================
        # SOLO / GRUPO / QUALQUER
        # ====================================================

        modo = missao.get(
            "modo",
            MODO_QUALQUER
        )


        if (
            modo == MODO_SOLO
            and
            em_grupo
        ):
            continue


        if (
            modo == MODO_GRUPO
            and
            not em_grupo
        ):
            continue


        total = int(
            objetivo.get(
                "quantidade",
                1
            ) or 1
        )


        campo = (
            "guild_missions."
            "ativas."
            f"{missao_id}"
        )


        membro_chave = str(
            player_id
        )


        # ====================================================
        # INCREMENTO ATÔMICO
        # ====================================================

        resultado = (
            clan_manager
            .clans_collection
            .update_one(
                {
                    "_id":
                        cla["_id"],

                    f"{campo}.status":
                        STATUS_ATIVA,

                    f"{campo}.periodo":
                        periodo_atual,

                    f"{campo}.progresso": {
                        "$lt":
                            total
                    },

                    "membros.user_id":
                        player_id,
                },
                {
                    "$inc": {

                        f"{campo}.progresso":
                            quantidade,

                        (
                            f"{campo}."
                            "contribuicoes."
                            f"{membro_chave}."
                            "quantidade"
                        ):
                            quantidade,
                    },

                    "$set": {

                        (
                            f"{campo}."
                            "contribuicoes."
                            f"{membro_chave}."
                            "nome"
                        ):
                            nome_membro,

                        "atualizado_em":
                            _agora(),
                    },
                },
            )
        )


        if (
            resultado.modified_count
            != 1
        ):
            continue


        cla_novo = (
            clan_manager
            .obter_cla_por_id(
                cla["_id"]
            )
        )


        estado_novo = (
            _obter_estado_cla(
                cla_novo or {}
            )
        )


        atual = (
            estado_novo[
                "ativas"
            ].get(
                missao_id,
                {}
            )
        )


        progresso = min(
            total,
            int(
                atual.get(
                    "progresso",
                    0
                ) or 0
            )
        )


        # ====================================================
        # CONCLUSÃO
        # ====================================================

        if (
            progresso >= total
        ):

            concluida_em = (
                _agora()
            )


            clan_manager.clans_collection.update_one(
                {
                    "_id":
                        cla["_id"],

                    f"{campo}.status":
                        STATUS_ATIVA,

                    f"{campo}.periodo":
                        periodo_atual,
                },
                {
                    "$set": {

                        f"{campo}.status":
                            STATUS_PRONTA_ENTREGA,

                        f"{campo}.progresso":
                            total,

                        f"{campo}.concluida_em":
                            concluida_em,

                        "atualizado_em":
                            concluida_em,
                    }
                },
            )


            status_final = (
                STATUS_PRONTA_ENTREGA
            )


            print(
                "✅ [GUILDA CLÃ] "
                f"Missão coletiva pronta: "
                f"{missao_id} | "
                f"clã={cla['_id']}"
            )

        else:

            status_final = (
                STATUS_ATIVA
            )


        alteradas.append({

            "missao_id":
                missao_id,

            "nome":
                missao.get(
                    "nome",
                    missao_id
                ),

            "progresso":
                progresso,

            "total":
                total,

            "status":
                status_final,

            "contribuicao_membro":
                quantidade,
        })


        print(
            "🏰 [GUILDA CLÃ] "
            f"{nome_membro} +{quantidade} | "
            f"{missao_id} | "
            f"{progresso}/{total}"
        )


    return alteradas


# ============================================================
# 🎁 RESGATAR RECOMPENSA COLETIVA
# ============================================================

def resgatar_recompensa_cla(
    user_id,
    missao_id,
):

    player_id = _object_id(
        user_id
    )

    if not player_id:

        return {
            "success": False,
            "error":
                "ID inválido.",
        }


    missao = obter_missao(
        missao_id
    )

    if not missao:

        return {
            "success": False,
            "error":
                "Missão inexistente.",
        }


    if (
        missao.get("tipo")
        != TIPO_CLA
        or
        missao.get("escopo")
        != ESCOPO_COLETIVO
    ):

        return {
            "success": False,
            "error":
                "Este contrato não é coletivo.",
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


    cargo = _cargo_membro(
        cla,
        player_id
    )


    if not _pode_gerenciar(
        cla,
        cargo,
    ):

        return {
            "success": False,
            "error": (
                "Seu cargo não permite "
                "entregar missões do clã."
            ),
        }


    campo = (
        "guild_missions."
        "ativas."
        f"{missao_id}"
    )


    # ========================================================
    # 🔒 TRAVA
    # ========================================================

    trava = (
        clan_manager
        .clans_collection
        .update_one(
            {
                "_id":
                    cla["_id"],

                f"{campo}.status":
                    STATUS_PRONTA_ENTREGA,
            },
            {
                "$set": {
                    f"{campo}.status":
                        STATUS_ENTREGANDO
                }
            },
        )
    )


    if (
        trava.modified_count
        != 1
    ):

        return {
            "success": False,
            "error": (
                "A missão ainda não está "
                "pronta ou já foi entregue."
            ),
        }


    cla = (
        clan_manager
        .obter_cla_por_id(
            cla["_id"]
        )
    )


    estado = _obter_estado_cla(
        cla
    )


    estado_ativo = (
        estado["ativas"]
        .get(
            missao_id
        )
    )


    if not estado_ativo:

        return {
            "success": False,
            "error": (
                "Estado da missão "
                "não encontrado."
            ),
        }


    recompensas = (
        missao.get(
            "recompensas",
            {}
        )
        or {}
    )


    xp_cla = int(
        recompensas.get(
            "xp_cla",
            0
        ) or 0
    )


    ouro_cla = int(
        recompensas.get(
            "ouro_cla",
            0
        ) or 0
    )


    pontos_cla = int(
        recompensas.get(
            "pontos_cla",
            0
        ) or 0
    )


    agora = _agora()


    historico_anterior = (
        estado[
            "concluidas"
        ].get(
            missao_id,
            {}
        )
        or {}
    )


    vezes = int(
        historico_anterior.get(
            "vezes",
            0
        ) or 0
    ) + 1


    historico_novo = {

        "vezes":
            vezes,

        "ultimo_periodo":
            estado_ativo.get(
                "periodo"
            ),

        "ultima_entrega_em":
            agora,

        "entregue_por":
            player_id,

        "entregue_por_nome":
            _nome_membro(
                cla,
                player_id
            ),

        "progresso_final":
            estado_ativo.get(
                "progresso",
                0
            ),

        "contribuicoes":
            estado_ativo.get(
                "contribuicoes",
                {}
            ),

        "xp_cla":
            xp_cla,

        "ouro_cla":
            ouro_cla,

        "pontos_cla":
            pontos_cla,
    }


    update_inc = {}


    if xp_cla > 0:
        update_inc[
            "xp"
        ] = xp_cla


    if ouro_cla > 0:
        update_inc[
            "tesouro.ouro"
        ] = ouro_cla


    if pontos_cla > 0:
        update_inc[
            "guild_missions.pontos"
        ] = pontos_cla


    atualizacao = {

        "$set": {

            (
                "guild_missions."
                "concluidas."
                f"{missao_id}"
            ):
                historico_novo,

            "atualizado_em":
                agora,
        },

        "$unset": {
            campo: ""
        },
    }


    if update_inc:

        atualizacao[
            "$inc"
        ] = update_inc


    salvo = (
        clan_manager
        .clans_collection
        .update_one(
            {
                "_id":
                    cla["_id"],

                f"{campo}.status":
                    STATUS_ENTREGANDO,
            },
            atualizacao,
        )
    )


    if (
        salvo.modified_count
        != 1
    ):

        # Destrava.
        clan_manager.clans_collection.update_one(
            {
                "_id":
                    cla["_id"]
            },
            {
                "$set": {
                    f"{campo}.status":
                        STATUS_PRONTA_ENTREGA
                }
            },
        )

        return {
            "success": False,
            "error": (
                "Não foi possível salvar "
                "a recompensa do clã."
            ),
        }


    try:
        clan_manager._registrar_atividade(
            clan_id=cla["_id"],

            tipo="missao_cla",

            mensagem=(
                f"O clã concluiu a missão "
                f"'{missao['nome']}'."
            ),

            autor_id=
                player_id,

            autor_nome=
                _nome_membro(
                    cla,
                    player_id
                ),

            dados={
                "missao_id":
                    missao_id,

                "xp_cla":
                    xp_cla,

                "ouro_cla":
                    ouro_cla,

                "pontos_cla":
                    pontos_cla,
            },
        )

    except Exception:
        pass


    print(
        "🎁 [GUILDA CLÃ] "
        f"{missao_id} entregue | "
        f"clã={cla['_id']} | "
        f"XP={xp_cla} | "
        f"ouro={ouro_cla}"
    )


    return {
        "success": True,

        "message": (
            f"Missão coletiva "
            f"'{missao['nome']}' concluída!"
        ),

        "recompensas": {

            "xp_cla":
                xp_cla,

            "ouro_cla":
                ouro_cla,

            "pontos_cla":
                pontos_cla,
        },
    }