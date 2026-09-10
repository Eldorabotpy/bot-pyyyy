# ============================================================
# 📜 MUNDO DE ELDORA - MOTOR DE MISSÕES DA GUILDA
# ============================================================
#
# SISTEMA TOTALMENTE SEPARADO DAS QUESTS DE HISTÓRIA.
#
# player["quests"]
#     -> história / classe / evolução
#
# player["guild_missions"]
#     -> Guilda dos Aventureiros
#
# ============================================================

from __future__ import annotations

import asyncio
import inspect

from datetime import datetime, timezone

from bson import ObjectId

from modules.player.core import (
    users_collection,
    clear_player_cache,
)

from modules import player_manager

from modules.player.stats import (
    check_and_apply_level_up,
)

from modules.game_data import items as items_data

from modules.clan import clan_manager

from .guild_mission_registry import (
    GUILD_MISSIONS,
    REGIOES_GUILDA,

    TIPO_CLA,
    TIPO_PESSOAL,

    ESCOPO_INDIVIDUAL,
    ESCOPO_COLETIVO,

    MODO_SOLO,
    MODO_GRUPO,
    MODO_QUALQUER,

    FREQUENCIA_UNICA,
    FREQUENCIA_DIARIA,
    FREQUENCIA_SEMANAL,

    OBJETIVO_MATAR_MOB,

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
# 🔧 HELPERS
# ============================================================

def _agora():
    return datetime.now(timezone.utc)


def _object_id(valor):
    if isinstance(valor, ObjectId):
        return valor

    if valor is None:
        return None

    texto = str(valor).strip()

    if not ObjectId.is_valid(texto):
        return None

    return ObjectId(texto)


def _limpar_cache(player_id):
    """
    Limpa o cache do personagem sem quebrar
    caso clear_player_cache seja async.
    """

    if not player_id:
        return

    for valor in (
        player_id,
        str(player_id),
    ):
        try:
            resultado = clear_player_cache(valor)

            if not inspect.isawaitable(resultado):
                continue

            try:
                loop = asyncio.get_running_loop()

            except RuntimeError:
                asyncio.run(resultado)

            else:
                loop.create_task(resultado)

        except Exception as erro:
            print(
                "⚠️ [GUILD MISSIONS CACHE] "
                f"Falha ao limpar cache {valor}: {erro}"
            )


def _serializar(valor):
    """
    Converte ObjectId e datetime antes de mandar
    os dados para o frontend.
    """

    if isinstance(valor, ObjectId):
        return str(valor)

    if isinstance(valor, datetime):
        return valor.isoformat()

    if isinstance(valor, dict):
        return {
            chave: _serializar(item)
            for chave, item in valor.items()
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


def _obter_estado(jogador):
    estado = jogador.get(
        "guild_missions"
    )

    if not isinstance(estado, dict):
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
            estado.get("pontos", 0) or 0
        )
    except Exception:
        estado["pontos"] = 0

    return estado


def _formatar_missao(
    missao,
    estado_missao=None,
):
    dados = dict(missao)

    objetivo = dict(
        dados.get("objetivo", {})
        or {}
    )

    recompensas = dict(
        dados.get("recompensas", {})
        or {}
    )

    estado_missao = (
        estado_missao
        if isinstance(estado_missao, dict)
        else {}
    )

    progresso = int(
        estado_missao.get(
            "progresso",
            0,
        ) or 0
    )

    total = int(
        objetivo.get(
            "quantidade",
            1,
        ) or 1
    )

    dados["objetivo"] = objetivo
    dados["recompensas"] = recompensas

    dados["regiao_nome"] = (
        REGIOES_GUILDA.get(
            objetivo.get("regiao"),
            objetivo.get("regiao"),
        )
    )

    dados["progresso"] = progresso
    dados["progresso_total"] = total

    dados["status"] = estado_missao.get(
        "status"
    )

    dados["aceita_em"] = estado_missao.get(
        "aceita_em"
    )

    dados["concluida_em"] = estado_missao.get(
        "concluida_em"
    )

    return _serializar(dados)


# ============================================================
# 📖 LISTAR MISSÕES PARA O JOGADOR
# ============================================================

def listar_missoes_jogador(user_id):

    player_id = _object_id(user_id)

    if not player_id:
        return {
            "success": False,
            "error": "ID do jogador inválido.",
        }

    jogador = users_collection.find_one({
        "_id": player_id
    })

    if not jogador:
        return {
            "success": False,
            "error": "Herói não encontrado.",
        }

    estado = _obter_estado(jogador)

    nivel = int(
        jogador.get("level", 1) or 1
    )

    cla_atual = (
        clan_manager
        .obter_cla_do_jogador(
            player_id
        )
    )

    ativas = []
    disponiveis = []
    concluidas = []

    # ========================================================
    # MISSÕES ATIVAS
    # ========================================================

    for missao_id, estado_missao in (
        estado["ativas"].items()
    ):

        missao = obter_missao(
            missao_id
        )

        if not missao:
            continue

        ativas.append(
            _formatar_missao(
                missao,
                estado_missao,
            )
        )

    # ========================================================
    # CATÁLOGO DA ATENDENTE
    # ========================================================

    for missao in listar_missoes_ativas(
        ESCOPO_INDIVIDUAL
    ):

        missao_id = missao["id"]

        if missao_id in estado["ativas"]:
            continue

        historico = (
            estado["concluidas"]
            .get(missao_id)
        )

        if (
            historico
            and
            not missao.get(
                "repetivel",
                False,
            )
        ):
            continue

        bloqueio = None

        nivel_minimo = int(
            missao.get(
                "nivel_minimo",
                1,
            ) or 1
        )

        if nivel < nivel_minimo:

            bloqueio = (
                f"Requer nível "
                f"{nivel_minimo}."
            )

        elif (
            missao.get("tipo")
            == TIPO_CLA
            and
            not cla_atual
        ):

            bloqueio = (
                "Você precisa pertencer "
                "a um clã."
            )

        dados = _formatar_missao(
            missao
        )

        dados["disponivel"] = (
            bloqueio is None
        )

        dados["bloqueio"] = bloqueio

        disponiveis.append(dados)

    # ========================================================
    # HISTÓRICO
    # ========================================================

    for missao_id, info in (
        estado["concluidas"].items()
    ):

        missao = obter_missao(
            missao_id
        )

        if not missao:
            continue

        dados = _formatar_missao(
            missao
        )

        dados["historico"] = (
            _serializar(info)
        )

        concluidas.append(dados)

    return {
        "success": True,

        "pontos_guilda": int(
            estado.get("pontos", 0)
            or 0
        ),

        "ativas": ativas,

        "disponiveis": disponiveis,

        "concluidas": concluidas,
    }


# ============================================================
# 📜 ACEITAR MISSÃO
# ============================================================

def aceitar_missao(
    user_id,
    missao_id,
):

    player_id = _object_id(user_id)

    if not player_id:
        return {
            "success": False,
            "error": "ID do jogador inválido.",
        }

    missao = obter_missao(
        missao_id
    )

    if not missao:
        return {
            "success": False,
            "error": "Missão inexistente.",
        }
    # ========================================================
    # 🛡️ ESTE MANAGER É SOMENTE INDIVIDUAL
    # ========================================================

    if (
        missao.get("escopo")
        != ESCOPO_INDIVIDUAL
    ):

        return {
            "success": False,
            "error": (
                "Este contrato pertence "
                "ao clã inteiro."
            ),
        }
    
    if not missao.get(
        "ativa",
        True,
    ):
        return {
            "success": False,
            "error": (
                "Este contrato não está "
                "disponível."
            ),
        }

    jogador = users_collection.find_one({
        "_id": player_id
    })

    if not jogador:
        return {
            "success": False,
            "error": "Herói não encontrado.",
        }

    nivel = int(
        jogador.get("level", 1)
        or 1
    )

    nivel_minimo = int(
        missao.get(
            "nivel_minimo",
            1,
        ) or 1
    )

    if nivel < nivel_minimo:

        return {
            "success": False,
            "error": (
                f"Você precisa alcançar "
                f"o nível {nivel_minimo}."
            ),
        }

    estado = _obter_estado(jogador)

    if missao_id in estado["ativas"]:

        return {
            "success": False,
            "error": (
                "Você já aceitou "
                "esta missão."
            ),
        }

    ja_concluiu = (
        estado["concluidas"]
        .get(missao_id)
    )

    if (
        ja_concluiu
        and
        not missao.get(
            "repetivel",
            False,
        )
    ):

        return {
            "success": False,
            "error": (
                "Esta missão já foi "
                "concluída."
            ),
        }

    clan_id_aceite = None

    # ========================================================
    # MISSÃO DE CLÃ
    # ========================================================

    if missao.get("tipo") == TIPO_CLA:

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
                    "Você precisa pertencer "
                    "a um clã para aceitar "
                    "este contrato."
                ),
            }

        clan_id_aceite = str(
            cla["_id"]
        )

    agora = _agora()

    novo_estado = {
        "missao_id": missao_id,

        "status": STATUS_ATIVA,

        "progresso": 0,

        "aceita_em": agora,

        "concluida_em": None,

        "tipo": missao.get("tipo"),

        "modo": missao.get("modo"),

        # Importante:
        # missão de clã fica vinculada ao clã
        # no qual ela foi aceita.
        "clan_id_aceite":
            clan_id_aceite,
    }

    campo = (
        f"guild_missions."
        f"ativas.{missao_id}"
    )

    resultado = (
        users_collection
        .update_one(
            {
                "_id": player_id,
                campo: {
                    "$exists": False
                },
            },
            {
                "$set": {
                    campo: novo_estado
                },

                "$setOnInsert": {
                    "guild_missions.pontos": 0
                },
            },
        )
    )

    if resultado.matched_count != 1:

        return {
            "success": False,
            "error": (
                "Não foi possível aceitar "
                "a missão."
            ),
        }

    _limpar_cache(player_id)

    print(
        "📜 [GUILDA] "
        f"{jogador.get('character_name', player_id)} "
        f"aceitou {missao_id}"
    )

    return {
        "success": True,

        "message": (
            f"Missão '{missao['nome']}' "
            f"aceita!"
        ),

        "missao": _formatar_missao(
            missao,
            novo_estado,
        ),
    }


# ============================================================
# ⚔️ REGISTRAR ABATE
# ============================================================

def registrar_abate(
    user_id,
    monster_id,
    regiao,
    em_grupo=False,
    quantidade=1,
):
    """
    Esta função será chamada PELO BACKEND
    quando o monstro realmente morrer.

    Nunca pelo JavaScript.

    Assim o jogador não pode mandar
    falsos abates pelo navegador.
    """

    player_id = _object_id(user_id)

    if not player_id:
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
            int(quantidade),
        )

    except Exception:
        quantidade = 1

    jogador = users_collection.find_one(
        {
            "_id": player_id
        },
        {
            "guild_missions": 1,
            "clan_id": 1,
            "character_name": 1,
        },
    )

    if not jogador:
        return []

    estado = _obter_estado(
        jogador
    )

    if not estado["ativas"]:
        return []

    cla_atual = None
    clan_id_atual = None

    alteradas = []

    for missao_id, estado_missao in list(
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
        
        # Este motor registra somente
        # progresso individual.
        if (
            missao.get("escopo")
            != ESCOPO_INDIVIDUAL
        ):
            continue

        objetivo = (
            missao.get(
                "objetivo",
                {},
            )
            or {}
        )

        # Somente abate de mob
        if (
            objetivo.get("tipo")
            != OBJETIVO_MATAR_MOB
        ):
            continue

        # Região precisa ser exatamente
        # a região da missão.
        if (
            str(objetivo.get("regiao"))
            != regiao
        ):
            continue

        mobs_validos = [
            str(m)
            for m in objetivo.get(
                "mob_ids",
                [],
            )
        ]

        if monster_id not in mobs_validos:
            continue

        # ====================================================
        # VALIDA MODO SOLO / GRUPO
        # ====================================================

        modo = missao.get("modo")

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

        # ====================================================
        # MISSÃO DE CLÃ
        # ====================================================

        if missao.get("tipo") == TIPO_CLA:

            if cla_atual is None:

                cla_atual = (
                    clan_manager
                    .obter_cla_do_jogador(
                        player_id
                    )
                )

                if cla_atual:
                    clan_id_atual = str(
                        cla_atual["_id"]
                    )

            clan_id_aceite = str(
                estado_missao.get(
                    "clan_id_aceite"
                )
                or ""
            )

            # Se saiu do clã ou trocou de clã,
            # este contrato não progride.
            if (
                not clan_id_atual
                or
                clan_id_atual
                != clan_id_aceite
            ):
                continue

        total = int(
            objetivo.get(
                "quantidade",
                1,
            ) or 1
        )

        campo = (
            f"guild_missions."
            f"ativas.{missao_id}"
        )

        # ====================================================
        # INCREMENTO ATÔMICO
        # ====================================================

        resultado = (
            users_collection
            .update_one(
                {
                    "_id": player_id,

                    f"{campo}.status":
                        STATUS_ATIVA,

                    f"{campo}.progresso": {
                        "$lt": total
                    },
                },
                {
                    "$inc": {
                        f"{campo}.progresso":
                            quantidade
                    }
                },
            )
        )

        if resultado.modified_count != 1:
            continue

        jogador_novo = (
            users_collection
            .find_one(
                {
                    "_id": player_id
                },
                {
                    campo: 1
                },
            )
        )

        # Pela projeção aninhada do Mongo,
        # é mais seguro buscar o estado completo
        # quando precisarmos confirmar conclusão.
        jogador_novo = (
            users_collection
            .find_one(
                {
                    "_id": player_id
                },
                {
                    "guild_missions": 1
                },
            )
        )

        estado_novo = _obter_estado(
            jogador_novo or {}
        )

        atual = (
            estado_novo["ativas"]
            .get(
                missao_id,
                {},
            )
        )

        progresso = min(
            total,
            int(
                atual.get(
                    "progresso",
                    0,
                ) or 0
            ),
        )

        # Nunca deixa passar do total visualmente.
        users_collection.update_one(
            {
                "_id": player_id
            },
            {
                "$set": {
                    f"{campo}.progresso":
                        progresso
                }
            },
        )

        pronta = (
            progresso >= total
        )

        if pronta:

            concluida_em = _agora()

            users_collection.update_one(
                {
                    "_id": player_id,

                    f"{campo}.status":
                        STATUS_ATIVA,
                },
                {
                    "$set": {
                        f"{campo}.status":
                            STATUS_PRONTA_ENTREGA,

                        f"{campo}.progresso":
                            total,

                        f"{campo}.concluida_em":
                            concluida_em,
                    }
                },
            )

            status_final = (
                STATUS_PRONTA_ENTREGA
            )

            print(
                "✅ [GUILDA] "
                f"Missão pronta para entrega: "
                f"{missao_id} / jogador={player_id}"
            )

        else:
            status_final = STATUS_ATIVA

        alteradas.append({
            "missao_id": missao_id,
            "nome": missao.get(
                "nome",
                missao_id,
            ),
            "progresso": progresso,
            "total": total,
            "status": status_final,
        })

    if alteradas:
        _limpar_cache(player_id)

    return alteradas


# ============================================================
# 🎁 VALIDA RECOMPENSAS
# ============================================================

def _validar_itens_recompensa(
    recompensas,
):
    erros = []

    for item in (
        recompensas.get(
            "itens",
            [],
        )
        or []
    ):

        item_id = str(
            item.get(
                "item_id",
                "",
            )
        ).strip()

        try:
            quantidade = int(
                item.get(
                    "quantidade",
                    1,
                )
                or 1
            )

        except Exception:
            quantidade = 0

        if not item_id:
            erros.append(
                "Recompensa possui item vazio."
            )

            continue

        if quantidade <= 0:
            erros.append(
                f"{item_id}: quantidade inválida."
            )

        if (
            item_id
            not in items_data.ITEMS_DATA
        ):
            erros.append(
                f"Item inexistente: {item_id}."
            )

    return erros


# ============================================================
# 🎁 ENTREGAR RECOMPENSA
# ============================================================

def resgatar_recompensa(
    user_id,
    missao_id,
):

    player_id = _object_id(user_id)

    if not player_id:

        return {
            "success": False,
            "error": "ID do jogador inválido.",
        }

    missao = obter_missao(
        missao_id
    )

    if not missao:

        return {
            "success": False,
            "error": "Missão inexistente.",
        }

    recompensas = (
        missao.get(
            "recompensas",
            {},
        )
        or {}
    )

    # ========================================================
    # VALIDA ITENS ANTES DE TRAVAR ENTREGA
    # ========================================================

    erros_itens = (
        _validar_itens_recompensa(
            recompensas
        )
    )

    if erros_itens:

        return {
            "success": False,
            "error": (
                "Erro no catálogo da missão: "
                + " | ".join(erros_itens)
            ),
        }

    campo = (
        f"guild_missions."
        f"ativas.{missao_id}"
    )

    # ========================================================
    # 🔒 TRAVA CONTRA DUPLO CLIQUE
    # ========================================================

    trava = (
        users_collection
        .update_one(
            {
                "_id": player_id,

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

    if trava.modified_count != 1:

        jogador_teste = (
            users_collection
            .find_one(
                {
                    "_id": player_id
                },
                {
                    "guild_missions": 1
                },
            )
        )

        if not jogador_teste:

            return {
                "success": False,
                "error": "Herói não encontrado.",
            }

        return {
            "success": False,
            "error": (
                "A missão ainda não está "
                "pronta para entrega ou "
                "a recompensa já foi recebida."
            ),
        }

    jogador = users_collection.find_one({
        "_id": player_id
    })

    if not jogador:

        return {
            "success": False,
            "error": "Herói não encontrado.",
        }

    estado = _obter_estado(
        jogador
    )

    estado_ativo = (
        estado["ativas"]
        .get(missao_id)
    )

    if not estado_ativo:

        return {
            "success": False,
            "error": (
                "Estado da missão "
                "não encontrado."
            ),
        }

    # ========================================================
    # 🛡️ REVALIDA CLÃ
    # ========================================================

    cla_atual = None

    if missao.get("tipo") == TIPO_CLA:

        cla_atual = (
            clan_manager
            .obter_cla_do_jogador(
                player_id
            )
        )

        clan_id_aceite = str(
            estado_ativo.get(
                "clan_id_aceite"
            )
            or ""
        )

        if (
            not cla_atual
            or
            str(cla_atual["_id"])
            != clan_id_aceite
        ):

            # Destrava novamente
            users_collection.update_one(
                {
                    "_id": player_id
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
                    "Você não pertence mais "
                    "ao clã no qual aceitou "
                    "esta missão."
                ),
            }

    # ========================================================
    # VALORES DA RECOMPENSA
    # ========================================================

    xp = int(
        recompensas.get(
            "xp",
            0,
        ) or 0
    )

    gold = int(
        recompensas.get(
            "gold",
            0,
        ) or 0
    )

    pontos = int(
        recompensas.get(
            "pontos_guilda",
            0,
        ) or 0
    )

    xp_cla = int(
        recompensas.get(
            "xp_cla",
            0,
        ) or 0
    )

    # ========================================================
    # 💰 OURO
    # ========================================================

    if gold > 0:
        player_manager.add_gold(
            jogador,
            gold,
        )

    # ========================================================
    # ⭐ XP DO PERSONAGEM
    # ========================================================

    if xp > 0:
        jogador["xp"] = int(
            jogador.get(
                "xp",
                0,
            ) or 0
        ) + xp

    levels_gained = 0
    pontos_level = 0
    mensagem_level = ""

    if xp > 0:

        (
            levels_gained,
            pontos_level,
            mensagem_level,
        ) = check_and_apply_level_up(
            jogador
        )

    # ========================================================
    # 🎒 ITENS
    # ========================================================

    itens_entregues = []

    for item in (
        recompensas.get(
            "itens",
            [],
        )
        or []
    ):

        item_id = str(
            item.get("item_id")
        )

        quantidade_item = int(
            item.get(
                "quantidade",
                1,
            )
            or 1
        )

        player_manager.add_item_to_inventory(
            jogador,
            item_id,
            quantidade_item,
        )

        info_item = (
            items_data.ITEMS_DATA.get(
                item_id,
                {},
            )
            or {}
        )

        itens_entregues.append({
            "item_id": item_id,

            "nome": info_item.get(
                "display_name",
                item_id
                .replace("_", " ")
                .title(),
            ),

            "emoji": info_item.get(
                "emoji",
                "📦",
            ),

            "quantidade":
                quantidade_item,
        })

    # ========================================================
    # 🏅 PONTOS PESSOAIS DA GUILDA
    # ========================================================

    estado["pontos"] = int(
        estado.get(
            "pontos",
            0,
        ) or 0
    ) + pontos

    agora = _agora()

    # ========================================================
    # 📜 MOVE ATIVA -> CONCLUÍDA
    # ========================================================

    historico_anterior = (
        estado["concluidas"]
        .get(
            missao_id,
            {},
        )
        or {}
    )

    vezes = int(
        historico_anterior.get(
            "vezes",
            0,
        ) or 0
    ) + 1

    estado["concluidas"][
        missao_id
    ] = {

        "vezes": vezes,

        "entregue_em": agora,

        "ultima_entrega_em": agora,

        "xp_cla_previsto":
            xp_cla,

        "xp_cla_entregue":
            False,
    }

    estado["ativas"].pop(
        missao_id,
        None,
    )

    jogador[
        "guild_missions"
    ] = estado

    # ========================================================
    # 💾 SALVA RECOMPENSA PESSOAL
    # ========================================================

    atualizacao = {

        "gold": int(
            jogador.get(
                "gold",
                0,
            ) or 0
        ),

        "xp": int(
            jogador.get(
                "xp",
                0,
            ) or 0
        ),

        "level": int(
            jogador.get(
                "level",
                1,
            ) or 1
        ),

        "stat_points": int(
            jogador.get(
                "stat_points",
                0,
            ) or 0
        ),

        "current_hp": int(
            jogador.get(
                "current_hp",
                1,
            ) or 1
        ),

        "inventory": (
            jogador.get(
                "inventory",
                {},
            )
            or {}
        ),

        "guild_missions":
            estado,
    }

    salvo = (
        users_collection
        .update_one(
            {
                "_id": player_id,

                f"{campo}.status":
                    STATUS_ENTREGANDO,
            },
            {
                "$set":
                    atualizacao
            },
        )
    )

    if salvo.modified_count != 1:

        # Como tudo estava somente na memória,
        # nenhuma recompensa foi salva.
        users_collection.update_one(
            {
                "_id": player_id
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
                "a recompensa."
            ),
        }

    # ========================================================
    # 🛡️ XP DO CLÃ
    # ========================================================

    xp_cla_entregue = 0

    if (
        missao.get("tipo") == TIPO_CLA
        and
        xp_cla > 0
    ):

        try:

            sucesso_cla = (
                clan_manager
                .adicionar_xp_cla(
                    user_id=player_id,
                    quantidade=xp_cla,
                )
            )

            if sucesso_cla:

                xp_cla_entregue = xp_cla

                users_collection.update_one(
                    {
                        "_id": player_id
                    },
                    {
                        "$set": {
                            (
                                "guild_missions."
                                "concluidas."
                                f"{missao_id}."
                                "xp_cla_entregue"
                            ): True
                        }
                    },
                )

        except Exception as erro:

            print(
                "⚠️ [GUILDA XP CLÃ] "
                f"Falha: {erro}"
            )

    _limpar_cache(
        player_id
    )

    print(
        "🎁 [GUILDA] "
        f"Recompensa entregue "
        f"{missao_id} para {player_id}"
    )

    return {

        "success": True,

        "message": (
            f"Recompensa de "
            f"'{missao['nome']}' recebida!"
        ),

        "recompensas": {

            "xp": xp,

            "gold": gold,

            "pontos_guilda":
                pontos,

            "xp_cla":
                xp_cla_entregue,

            "itens":
                itens_entregues,
        },

        "level_up": {

            "subiu":
                levels_gained > 0,

            "niveis_ganhos":
                levels_gained,

            "novo_level": int(
                jogador.get(
                    "level",
                    1,
                )
            ),

            "pontos_atributo":
                pontos_level,

            "mensagem":
                mensagem_level,
        },

        "pontos_guilda_total":
            estado["pontos"],
    }