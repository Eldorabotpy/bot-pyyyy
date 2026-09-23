# modules/dungeon_event_service.py

from __future__ import annotations

import random
import threading
import uuid

from copy import deepcopy

from bson import ObjectId

from modules.player.core import users_collection

from modules.game_data.monsters import (
    MONSTERS_DATA
)

from modules.game_data.dungeon_events import (
    get_dungeon_event_config
)

from modules.game_data.dungeon_chests import (
    DUNGEON_CHEST_REWARDS
)


# ============================================================
# 🔒 LOCK
# ============================================================

_EVENT_LOCK = threading.RLock()


# ============================================================
# 📦 LOCAL DO ESTADO NO PERSONAGEM
# ============================================================

STATE_ROOT = "dungeon_events"
# ==============================================================================
# 🔮 IDENTIDADE DAS PEDRAS DO ENIGMA
# ==============================================================================

DUNGEON_RUNE_NAMES = {
    1: {
        "nome": "Lua",
        "emoji": "🌙",
    },
    2: {
        "nome": "Mar",
        "emoji": "🌊",
    },
    3: {
        "nome": "Gelo",
        "emoji": "❄️",
    },
    4: {
        "nome": "Sol",
        "emoji": "☀️",
    },
    5: {
        "nome": "Ouro",
        "emoji": "👑",
    },
    6: {
        "nome": "Chama",
        "emoji": "🔥",
    },
}


def _gerar_charada_sequencia(
    sequence: list[int],
) -> str:

    pistas = {
        1: "a senhora que reina quando o sol se cala",
        2: "o caminho que nunca descansa e beija todas as margens",
        3: "o sopro que aprisiona a água em cristal",
        4: "o soberano que desperta o mundo a cada manhã",
        5: "aquilo que reis desejam e homens traem para possuir",
        6: "a fome que dança, ilumina e devora sem ter boca",
    }

    enigmas = []

    for indice in sequence:

        pista = pistas.get(
            int(indice),
            "o símbolo esquecido pelos antigos"
        )

        enigmas.append(
            pista
        )

    if len(enigmas) < 3:
        return (
            "As inscrições permanecem silenciosas..."
        )

    return (
        "As inscrições do baú despertam:\n\n"
        f"“Meu selo começa com {enigmas[0]}.\n"
        f"Em seguida, procure {enigmas[1]}.\n"
        f"Somente então desperte {enigmas[2]}.”"
    )

# ============================================================
# ❌ ERRO DO SISTEMA
# ============================================================

class DungeonEventError(Exception):
    pass


# ============================================================
# 👤 OBJECT ID
# ============================================================

def _oid(user_id: str) -> ObjectId:

    if (
        not user_id
        or not ObjectId.is_valid(
            str(user_id)
        )
    ):
        raise DungeonEventError(
            "Jogador inválido."
        )

    return ObjectId(
        str(user_id)
    )


# ============================================================
# 👤 BUSCA PLAYER
# ============================================================

def _get_player(
    user_id: str
) -> dict:

    player = users_collection.find_one({
        "_id": _oid(user_id)
    })

    if not player:
        raise DungeonEventError(
            "Herói não encontrado."
        )

    return player


# ============================================================
# 🗝️ CONSUMIR CHAVE DE MASMORRA
# ============================================================

def consumir_chave_masmorra(
    *,
    user_id: str,
    dungeon_id: str
) -> dict:

    """
    Verifica e consome 1 Chave de Masmorra.

    Esta função deve ser chamada somente
    quando o jogador confirma uma NOVA
    entrada em uma dungeon.

    Recarregar o jogo já estando dentro
    da dungeon não deve chamar esta função.
    """

    with _EVENT_LOCK:

        # ====================================================
        # 🏰 VALIDAR DUNGEON
        # ====================================================

        dungeon_id = str(
            dungeon_id
            or ""
        ).strip()

        if not dungeon_id:

            raise DungeonEventError(
                "Dungeon inválida."
            )


        # ====================================================
        # 👤 BUSCAR JOGADOR
        # ====================================================

        player = _get_player(
            user_id
        )


        # ====================================================
        # 📦 INVENTÁRIO
        # ====================================================

        inventory = (
            player.get(
                "inventory",
                {}
            )
            or {}
        )

        if not isinstance(
            inventory,
            dict
        ):

            inventory = {}


        item_id = (
            "chave_masmorra"
        )

        item = inventory.get(
            item_id
        )


        # ====================================================
        # 🔎 QUANTIDADE ATUAL
        # ====================================================

        quantidade = 0


        if isinstance(
            item,
            dict
        ):

            try:

                quantidade = int(
                    item.get(
                        "quantity",
                        0
                    )
                    or 0
                )

            except (
                TypeError,
                ValueError
            ):

                quantidade = 0


        elif isinstance(
            item,
            int
        ):

            quantidade = max(
                0,
                int(item)
            )


        # ====================================================
        # 🔒 SEM CHAVE
        # ====================================================

        if quantidade <= 0:

            return {

                "success":
                    False,

                "autorizado":
                    False,

                "acao":
                    "sem_chave",

                "dungeon_id":
                    dungeon_id,

                "item_id":
                    item_id,

                "quantidade":
                    0,

                "mensagem":
                    (
                        "Você precisa de 1 "
                        "Chave de Masmorra "
                        "para entrar."
                    ),
            }


        nova_quantidade = (
            quantidade - 1
        )


        # ====================================================
        # 🗝️ CONSUMIR FORMATO NOVO
        # ====================================================
        #
        # inventory:
        #
        # "chave_masmorra": {
        #     "base_id": "chave_masmorra",
        #     "quantity": 3
        # }
        # ====================================================

        if isinstance(
            item,
            dict
        ):

            filtro = {

                "_id":
                    player["_id"],

                (
                    "inventory."
                    "chave_masmorra."
                    "quantity"
                ):
                    quantidade,
            }


            if nova_quantidade <= 0:

                atualizacao = {

                    "$unset": {

                        (
                            "inventory."
                            "chave_masmorra"
                        ):
                            ""
                    }
                }

            else:

                atualizacao = {

                    "$inc": {

                        (
                            "inventory."
                            "chave_masmorra."
                            "quantity"
                        ):
                            -1
                    }
                }


        # ====================================================
        # 🗝️ CONSUMIR FORMATO ANTIGO
        # ====================================================
        #
        # inventory:
        #
        # "chave_masmorra": 3
        # ====================================================

        else:

            filtro = {

                "_id":
                    player["_id"],

                (
                    "inventory."
                    "chave_masmorra"
                ):
                    quantidade,
            }


            if nova_quantidade <= 0:

                atualizacao = {

                    "$unset": {

                        (
                            "inventory."
                            "chave_masmorra"
                        ):
                            ""
                    }
                }

            else:

                atualizacao = {

                    "$inc": {

                        (
                            "inventory."
                            "chave_masmorra"
                        ):
                            -1
                    }
                }


        # ====================================================
        # 💾 ATUALIZAÇÃO ATÔMICA
        # ====================================================

        resultado = (
            users_collection.update_one(
                filtro,
                atualizacao
            )
        )


        # Se a quantidade mudou entre a leitura
        # e a atualização, não autoriza a entrada.
        if (
            resultado.modified_count
            != 1
        ):

            return {

                "success":
                    False,

                "autorizado":
                    False,

                "acao":
                    "inventario_alterado",

                "dungeon_id":
                    dungeon_id,

                "item_id":
                    item_id,

                "quantidade":
                    quantidade,

                "mensagem":
                    (
                        "O inventário foi alterado. "
                        "Tente entrar novamente."
                    ),
            }


        # ====================================================
        # ✅ ENTRADA AUTORIZADA
        # ====================================================

        return {

            "success":
                True,

            "autorizado":
                True,

            "acao":
                "entrada_autorizada",

            "dungeon_id":
                dungeon_id,

            "item_id":
                item_id,

            "consumido":
                1,

            "quantidade":
                nova_quantidade,

            "mensagem":
                (
                    "1 Chave de Masmorra "
                    "foi consumida."
                ),
        }


# ============================================================
# 📦 CAMINHO DO ESTADO
# ============================================================

def _state_path(
    dungeon_id: str,
    puzzle_id: str
) -> str:

    return (
        f"{STATE_ROOT}."
        f"{dungeon_id}."
        f"{puzzle_id}"
    )


# ============================================================
# 📖 PEGAR ESTADO
# ============================================================

def _get_nested_state(
    player: dict,
    dungeon_id: str,
    puzzle_id: str
):

    root = player.get(
        STATE_ROOT,
        {}
    )

    if not isinstance(root, dict):
        return None

    dungeon = root.get(
        str(dungeon_id),
        {}
    )

    if not isinstance(dungeon, dict):
        return None

    state = dungeon.get(
        str(puzzle_id)
    )

    if isinstance(state, dict):
        return deepcopy(state)

    return None


# ============================================================
# 💾 SALVAR ESTADO
# ============================================================

def _save_state(
    user_id: str,
    dungeon_id: str,
    puzzle_id: str,
    state: dict
):

    state = deepcopy(state)

    state["revision"] = (
        int(
            state.get(
                "revision",
                0
            )
        )
        + 1
    )

    users_collection.update_one(

        {
            "_id": _oid(user_id)
        },

        {
            "$set": {
                _state_path(
                    dungeon_id,
                    puzzle_id
                ): state
            }
        }

    )


# ============================================================
# 🎲 GERAR SEQUÊNCIA
# ============================================================

def _new_sequence(
    config: dict
) -> list[int]:

    lights = [

        int(x)

        for x in config.get(
            "available_lights",
            [1, 2, 3, 4, 5, 6]
        )

    ]

    size = int(
        config.get(
            "sequence_length",
            3
        )
    )

    if (
        size <= 0
        or size > len(lights)
    ):
        raise DungeonEventError(
            "Configuração inválida da sequência."
        )

    # Sem repetição.
    #
    # Exemplo:
    # [2, 6, 4]

    return random.sample(
        lights,
        size
    )


# ============================================================
# 🆕 ESTADO NOVO
# ============================================================

def _fresh_state(
    config: dict
) -> dict:

    return {

        "version": int(
            config.get(
                "state_version",
                1
            )
        ),

        # SEGREDO.
        # Nunca enviar isto ao frontend.
        "sequence": _new_sequence(
            config
        ),

        # Pedras já acertadas.
        "progress": [],

        "resolved": False,

        "chest_open": False,

        "mimic_active": False,

        "mimic_spawn_id": None,

        "attempts": 0,

        "mimics_defeated": 0,

        "last_mimic_result": None,

        "revision": 0,
    }


# ============================================================
# ✅ GARANTE ESTADO
# ============================================================

def _ensure_state(
    user_id: str,
    dungeon_id: str,
    puzzle_id: str
):

    config = get_dungeon_event_config(
        dungeon_id,
        puzzle_id
    )

    if not config:
        raise DungeonEventError(
            "Evento de dungeon não encontrado."
        )

    player = _get_player(
        user_id
    )

    state = _get_nested_state(
        player,
        dungeon_id,
        puzzle_id
    )

    expected_version = int(
        config.get(
            "state_version",
            1
        )
    )

    if (
        not state
        or int(
            state.get(
                "version",
                -1
            )
        ) != expected_version
    ):

        state = _fresh_state(
            config
        )

        _save_state(
            user_id,
            dungeon_id,
            puzzle_id,
            state
        )

        state["revision"] = (
            int(
                state.get(
                    "revision",
                    0
                )
            )
            + 1
        )

    return (
        player,
        config,
        state
    )


# ============================================================
# 🌐 ESTADO QUE PODE IR AO FRONTEND
# ============================================================

def _public_state(
    state: dict
) -> dict:

    # IMPORTANTE:
    #
    # NÃO enviar:
    #
    # sequence
    #
    # porque essa é a resposta do puzzle.

    return {

        "luzes_ativas": [

            int(x)

            for x in state.get(
                "progress",
                []
            )

        ],

        "resolvido": bool(
            state.get(
                "resolved"
            )
        ),

        "bau_aberto": bool(
            state.get(
                "chest_open"
            )
        ),

        "mimico_ativo": bool(
            state.get(
                "mimic_active"
            )
        ),

        "mimico_spawn_id":
            state.get(
                "mimic_spawn_id"
            ),

        "tentativas": int(
            state.get(
                "attempts",
                0
            )
        ),

        "mimicos_derrotados": int(
            state.get(
                "mimics_defeated",
                0
            )
        ),

        "revision": int(
            state.get(
                "revision",
                0
            )
        ),
    }


# ============================================================
# 👹 BUSCAR TEMPLATE DO MONSTRO
# ============================================================

def _find_monster_template(
    monster_id: str
) -> dict:

    for categoria, mobs in (
        MONSTERS_DATA.items()
    ):

        if str(
            categoria
        ).startswith("_"):
            continue

        for monster in mobs:

            if (
                monster.get("id")
                == monster_id
            ):

                return deepcopy(
                    monster
                )

    raise DungeonEventError(
        f"Monstro de evento não encontrado: "
        f"{monster_id}"
    )


# ============================================================
# 👹 VERIFICA SE SPAWN EXISTE
# ============================================================

def _spawn_exists(
    sistema_cacada,
    dungeon_id: str,
    spawn_id
) -> bool:

    if (
        not spawn_id
        or sistema_cacada is None
    ):
        return False

    region = getattr(
        sistema_cacada,
        "mobs_vivos",
        {}
    ).get(
        str(dungeon_id),
        {}
    )

    return (
        str(spawn_id)
        in region
    )


# ============================================================
# 👹 CRIAR MÍMICO
# ============================================================

def _create_mimic_spawn(
    *,
    user_id: str,
    dungeon_id: str,
    puzzle_id: str,
    config: dict,
    state: dict,
    sistema_cacada
) -> str:

    if sistema_cacada is None:

        raise DungeonEventError(
            "Motor de caçada não está disponível."
        )

    old_spawn = state.get(
        "mimic_spawn_id"
    )

    # Se já existe um Mímico ativo,
    # reutiliza o mesmo.

    if (
        state.get("mimic_active")
        and _spawn_exists(
            sistema_cacada,
            dungeon_id,
            old_spawn
        )
    ):
        return str(
            old_spawn
        )

    monster_id = str(
        config["monster_id"]
    )

    template = _find_monster_template(
        monster_id
    )

    # Spawn único e privado.

    spawn_id = (
        f"dungeonevt_"
        f"{str(user_id)}_"
        f"{str(puzzle_id)}_"
        f"{uuid.uuid4().hex[:10]}"
    )

    hp = int(
        template.get(
            "hp",
            1
        )
        or 1
    )

    level_min = int(
        template.get(
            "min_level",
            1
        )
        or 1
    )

    mob = {

        "id": spawn_id,

        "spawn_id": spawn_id,

        "monster_id":
            monster_id,

        "level":
            level_min,

        "hp":
            hp,

        "hp_atual":
            hp,

        "hp_max":
            hp,

        "attack": int(
            template.get(
                "attack",
                1
            )
            or 1
        ),

        "defense": int(
            template.get(
                "defense",
                0
            )
            or 0
        ),

        "initiative": int(
            template.get(
                "initiative",
                0
            )
            or 0
        ),

        "luck": int(
            template.get(
                "luck",
                0
            )
            or 0
        ),

        # O Mímico do puzzle
        # não dá recompensa normal.
        "xp_reward": 0,

        "gold_drop": 0,

        "respawn_segundos": 0,

        # Flags para o resto do jogo
        # saber que NÃO é mob normal.

        "event_only": True,

        "evento": True,

        "evento_dungeon": True,

        "tipo_evento":
            "dungeon_event",

        "origem":
            "dungeon_event",

        # Segurança:
        # este Mímico pertence apenas
        # ao jogador que ativou o evento.

        "event_owner_id":
            str(user_id),

        "event_id":
            str(puzzle_id),

        "dungeon_id":
            str(dungeon_id),

        "puzzle_id":
            str(puzzle_id),
    }

    mobs_vivos = getattr(
        sistema_cacada,
        "mobs_vivos",
        None
    )

    if mobs_vivos is None:

        raise DungeonEventError(
            "Motor de caçada sem mobs_vivos."
        )

    mobs_vivos.setdefault(
        str(dungeon_id),
        {}
    )[spawn_id] = mob

    state[
        "mimic_active"
    ] = True

    state[
        "mimic_spawn_id"
    ] = spawn_id

    return spawn_id


# ============================================================
# 🧹 REMOVER SPAWN DO EVENTO
# ============================================================

def _remove_event_spawn(
    sistema_cacada,
    dungeon_id: str,
    spawn_id
):

    if (
        not sistema_cacada
        or not spawn_id
    ):
        return

    try:

        region = getattr(
            sistema_cacada,
            "mobs_vivos",
            {}
        ).get(
            str(dungeon_id),
            {}
        )

        region.pop(
            str(spawn_id),
            None
        )

    except Exception:
        pass


# ============================================================
# 📖 STATUS DO EVENTO
# ============================================================

def obter_estado_evento(
    *,
    user_id: str,
    dungeon_id: str,
    puzzle_id: str,
    sistema_cacada=None
):

    with _EVENT_LOCK:

        (
            _player,
            config,
            state
        ) = _ensure_state(
            user_id,
            dungeon_id,
            puzzle_id
        )

        # Se o servidor reiniciou,
        # o banco pode lembrar de um Mímico
        # que já sumiu da RAM.

        if state.get(
            "mimic_active"
        ):

            spawn_id = state.get(
                "mimic_spawn_id"
            )

            if (
                sistema_cacada is not None
                and not _spawn_exists(
                    sistema_cacada,
                    dungeon_id,
                    spawn_id
                )
            ):

                state[
                    "mimic_active"
                ] = False

                state[
                    "mimic_spawn_id"
                ] = None

                state[
                    "progress"
                ] = []

                _save_state(
                    user_id,
                    dungeon_id,
                    puzzle_id,
                    state
                )

                state["revision"] = (
                    int(
                        state.get(
                            "revision",
                            0
                        )
                    )
                    + 1
                )

        return {

            "success": True,

            "acao":
                "estado",

            "dungeon_id":
                str(dungeon_id),

            "puzzle_id":
                str(puzzle_id),

            "estado":
                _public_state(
                    state
                ),
        }


# ============================================================
# 💡 INTERAGIR COM PEDRA
# ============================================================

def interagir_luz(
    *,
    user_id: str,
    dungeon_id: str,
    puzzle_id: str,
    indice: int,
    sistema_cacada
):

    with _EVENT_LOCK:

        (
            _player,
            config,
            state
        ) = _ensure_state(
            user_id,
            dungeon_id,
            puzzle_id
        )

        try:
            indice = int(
                indice
            )

        except (
            TypeError,
            ValueError
        ):

            raise DungeonEventError(
                "Índice da pedra inválido."
            )

        available = [

            int(x)

            for x in config.get(
                "available_lights",
                []
            )

        ]

        if indice not in available:

            raise DungeonEventError(
                "Essa pedra não pertence ao puzzle."
            )

        # ====================================================
        # EVENTO JÁ CONCLUÍDO
        # ====================================================

        if state.get(
            "chest_open"
        ):

            return {

                "success": True,

                "acao":
                    "evento_concluido",

                "mensagem":
                    "Este baú já foi aberto.",

                "estado":
                    _public_state(
                        state
                    ),
            }

        # ====================================================
        # PUZZLE JÁ RESOLVIDO
        # ====================================================

        if state.get(
            "resolved"
        ):

            return {

                "success": True,

                "acao":
                    "puzzle_ja_resolvido",

                "mensagem":
                    "A combinação já foi descoberta.",

                "estado":
                    _public_state(
                        state
                    ),
            }

        # ====================================================
        # MÍMICO ATIVO
        # ====================================================

        if state.get(
            "mimic_active"
        ):

            return {

                "success": True,

                "acao":
                    "mimico_em_andamento",

                "invocar_mimico":
                    False,

                "mensagem":
                    "O Mímico já despertou.",

                "estado":
                    _public_state(
                        state
                    ),
            }

        # ====================================================
        # SEQUÊNCIA
        # ====================================================

        sequence = [

            int(x)

            for x in state.get(
                "sequence",
                []
            )

        ]

        progress = [

            int(x)

            for x in state.get(
                "progress",
                []
            )

        ]

        if not sequence:

            raise DungeonEventError(
                "Sequência do puzzle inválida."
            )

        # ====================================================
        # CLICOU NOVAMENTE EM UMA PEDRA ACESA
        # ====================================================
        #
        # Funciona como interruptor:
        #
        # OFF → ON
        # ON  → OFF
        # ====================================================

        if indice in progress:

            progress.remove(
                indice
            )

            state[
                "progress"
            ] = progress

            _save_state(
                user_id,
                dungeon_id,
                puzzle_id,
                state
            )

            state[
                "revision"
            ] += 1

            return {

                "success":
                    True,

                "acao":
                    "luz_desativada",

                "mensagem":
                    "A pedra voltou a ficar apagada.",

                "estado":
                    _public_state(
                        state
                    ),
            }

        # ====================================================
        # AS 3 PEDRAS JÁ FORAM ESCOLHIDAS
        # ====================================================
        #
        # Se tentar acender uma QUARTA pedra,
        # precisa primeiro apagar uma das três.
        # ====================================================

        if (
            len(progress)
            >= len(sequence)
        ):

            return {

                "success":
                    True,

                "acao":
                    "sequencia_pronta",

                "mensagem":
                    (
                        "Três runas já estão acesas. "
                        "Apague uma delas ou volte ao baú."
                    ),

                "estado":
                    _public_state(
                        state
                    ),
            }
        # ====================================================
        # ACENDE A PEDRA
        # ====================================================

        progress.append(
            indice
        )

        state[
            "progress"
        ] = progress

        _save_state(
            user_id,
            dungeon_id,
            puzzle_id,
            state
        )

        state[
            "revision"
        ] += 1

        # ====================================================
        # TERCEIRA PEDRA
        # ====================================================
        #
        # Continua acesa.
        # Ainda NÃO verifica se está certa.
        # ====================================================

        if (
            len(progress)
            == len(sequence)
        ):

            return {

                "success":
                    True,

                "acao":
                    "sequencia_pronta",

                "mensagem":
                    (
                        "As três runas foram escolhidas. "
                        "Agora volte ao baú."
                    ),

                "estado":
                    _public_state(
                        state
                    ),
            }

        # ====================================================
        # PRIMEIRA / SEGUNDA PEDRA
        # ====================================================

        return {

            "success":
                True,

            "acao":
                "luz_selecionada",

            "mensagem":
                (
                    f"Pedra ativada "
                    f"({len(progress)}/"
                    f"{len(sequence)})."
                ),

            "estado":
                _public_state(
                    state
                ),
        }
# ============================================================
# 🎁 ENTREGAR RECOMPENSA
# ============================================================

def _grant_chest_reward(
    player: dict,
    loot_id: str
):

    reward = (
        DUNGEON_CHEST_REWARDS.get(
            str(loot_id)
        )
    )

    if (
        not reward
        or not reward.get(
            "configured"
        )
    ):

        return (
            False,
            {},
            (
                f"A recompensa '{loot_id}' "
                "ainda não foi configurada. "
                "O baú continuará fechado."
            )
        )

    # ========================================================
    # 📦 INVENTÁRIO
    # ========================================================

    inventory = (
        player.get(
            "inventory",
            {}
        )
        or {}
    )

    if not isinstance(
        inventory,
        dict
    ):
        inventory = {}

    delivered_items = []

    # ========================================================
    # 🏷️ CATÁLOGO DE ITENS
    # ========================================================

    try:

        from modules.game_data.items import (
            ITEMS_DATA,
            get_display_name,
        )

    except Exception:

        ITEMS_DATA = {}

        def get_display_name(
            item_id
        ):
            return str(
                item_id
            ).replace(
                "_",
                " "
            ).title()

    # ========================================================
    # 📥 ADICIONAR ITEM
    # ========================================================

    def adicionar_item(
        item_id,
        quantidade
    ):

        item_id = str(
            item_id
            or ""
        )

        quantidade = max(
            0,
            int(
                quantidade
                or 0
            )
        )

        if (
            not item_id
            or quantidade <= 0
        ):
            return

        # Se o catálogo estiver disponível,
        # não permite ID inexistente.
        if (
            ITEMS_DATA
            and item_id
            not in ITEMS_DATA
        ):

            print(
                "[DUNGEON CHEST] Item inválido ignorado:",
                item_id
            )

            return

        current = inventory.get(
            item_id
        )

        if isinstance(
            current,
            dict
        ):

            current = dict(
                current
            )

            current[
                "quantity"
            ] = (
                int(
                    current.get(
                        "quantity",
                        0
                    )
                    or 0
                )
                + quantidade
            )

            current.setdefault(
                "base_id",
                item_id
            )

            inventory[
                item_id
            ] = current

        elif isinstance(
            current,
            int
        ):

            inventory[
                item_id
            ] = (
                current
                + quantidade
            )

        else:

            inventory[
                item_id
            ] = {

                "base_id":
                    item_id,

                "quantity":
                    quantidade,

            }

        delivered_items.append({

            "item_id":
                item_id,

            "nome":
                get_display_name(
                    item_id
                ),

            "quantity":
                quantidade,

        })

    # ========================================================
    # 💰 SORTEAR OURO
    # ========================================================

    gold_config = reward.get(
        "gold",
        0
    )

    if isinstance(
        gold_config,
        dict
    ):

        gold_min = max(
            0,
            int(
                gold_config.get(
                    "min",
                    0
                )
                or 0
            )
        )

        gold_max = max(
            gold_min,
            int(
                gold_config.get(
                    "max",
                    gold_min
                )
                or gold_min
            )
        )

        gold = random.randint(
            gold_min,
            gold_max
        )

    else:

        gold = max(
            0,
            int(
                gold_config
                or 0
            )
        )

    # ========================================================
    # 📦 DROPS NORMAIS
    # ========================================================

    drops = (
        reward.get(
            "drops",
            []
        )
        or []
    )

    for drop in drops:

        if not isinstance(
            drop,
            dict
        ):
            continue

        item_id = str(
            drop.get(
                "item_id",
                ""
            )
        )

        try:

            chance = float(
                drop.get(
                    "chance",
                    0
                )
                or 0
            )

        except (
            TypeError,
            ValueError
        ):

            chance = 0.0

        chance = max(
            0.0,
            min(
                1.0,
                chance
            )
        )

        if random.random() > chance:
            continue

        quantidade_min = max(
            1,
            int(
                drop.get(
                    "min",
                    1
                )
                or 1
            )
        )

        quantidade_max = max(
            quantidade_min,
            int(
                drop.get(
                    "max",
                    quantidade_min
                )
                or quantidade_min
            )
        )

        quantidade = random.randint(
            quantidade_min,
            quantidade_max
        )

        adicionar_item(
            item_id,
            quantidade
        )

    # ========================================================
    # 🔮 ROLL ESPECIAL DE RUNA
    # ========================================================

    rune_config = (
        reward.get(
            "rune_roll",
            {}
        )
        or {}
    )

    if isinstance(
        rune_config,
        dict
    ):

        pool = [

            str(item_id)

            for item_id
            in (
                rune_config.get(
                    "pool",
                    []
                )
                or []
            )

            if item_id

        ]

        try:

            rune_chance = float(
                rune_config.get(
                    "chance",
                    0
                )
                or 0
            )

        except (
            TypeError,
            ValueError
        ):

            rune_chance = 0.0

        rune_chance = max(
            0.0,
            min(
                1.0,
                rune_chance
            )
        )

        if (
            pool
            and random.random()
            <= rune_chance
        ):

            rune_id = random.choice(
                pool
            )

            rune_quantity = max(
                1,
                int(
                    rune_config.get(
                        "quantity",
                        1
                    )
                    or 1
                )
            )

            adicionar_item(
                rune_id,
                rune_quantity
            )

    # ========================================================
    # 💾 SALVAR
    # ========================================================

    users_collection.update_one(

        {
            "_id":
                player["_id"]
        },

        {
            "$set": {

                "inventory":
                    inventory

            },

            "$inc": {

                "gold":
                    gold

            }

        }

    )

    # ========================================================
    # ✅ RESULTADO
    # ========================================================

    return (

        True,

        {

            "gold":
                gold,

            "items":
                delivered_items,

        },

        None

    )


# ============================================================
# 📦 INTERAGIR COM BAÚ
# ============================================================

def interagir_bau(
    *,
    user_id: str,
    dungeon_id: str,
    puzzle_id: str,
    sistema_cacada
):

    with _EVENT_LOCK:

        (
            player,
            config,
            state
        ) = _ensure_state(
            user_id,
            dungeon_id,
            puzzle_id
        )

        # ====================================================
        # JÁ ABERTO
        # ====================================================

        if state.get(
            "chest_open"
        ):

            return {

                "success":
                    True,

                "acao":
                    "bau_ja_aberto",

                "mensagem":
                    "O baú já foi aberto.",

                "estado":
                    _public_state(
                        state
                    ),
            }

        # ====================================================
        # MÍMICO JÁ ATIVO
        # ====================================================

        if state.get(
            "mimic_active"
        ):

            return {

                "success":
                    True,

                "acao":
                    "mimico_em_andamento",

                "invocar_mimico":
                    False,

                "mensagem":
                    "O Mímico já despertou.",

                "estado":
                    _public_state(
                        state
                    ),
            }

        sequence = [

            int(x)

            for x in state.get(
                "sequence",
                []
            )

        ]

        progress = [

            int(x)

            for x in state.get(
                "progress",
                []
            )

        ]

        if not sequence:

            raise DungeonEventError(
                "Sequência do puzzle inválida."
            )

        # ====================================================
        # AINDA NÃO ESCOLHEU AS 3 PEDRAS
        # ====================================================
        #
        # O BAÚ REVELA A CHARADA.
        # ====================================================

        if (
            not state.get("resolved")
            and
            len(progress)
            < len(sequence)
        ):

            charada = (
                _gerar_charada_sequencia(
                    sequence
                )
            )

            return {

                "success":
                    True,

                "acao":
                    "bau_charada",

                "invocar_mimico":
                    False,

                "mensagem":
                    (
                        "Runas antigas brilham sobre o baú..."
                    ),

                "charada":
                    charada,

                "estado":
                    _public_state(
                        state
                    ),
            }

        # ====================================================
        # JOGADOR ESCOLHEU AS 3
        # ====================================================
        #
        # SOMENTE AO CLICAR NO BAÚ
        # verificamos a combinação.
        # ====================================================

        if not state.get(
            "resolved"
        ):

            # ================================================
            # ✅ COMBINAÇÃO CORRETA
            # ================================================

            if progress == sequence:

                state[
                    "resolved"
                ] = True

                _save_state(
                    user_id,
                    dungeon_id,
                    puzzle_id,
                    state
                )

                state[
                    "revision"
                ] += 1

            # ================================================
            # ❌ COMBINAÇÃO ERRADA
            # ================================================

            else:

                state[
                    "attempts"
                ] = (
                    int(
                        state.get(
                            "attempts",
                            0
                        )
                    )
                    + 1
                )

                # As pedras apagam
                # quando o baú vira Mímico.
                state[
                    "progress"
                ] = []

                spawn_id = (
                    _create_mimic_spawn(

                        user_id=
                            user_id,

                        dungeon_id=
                            dungeon_id,

                        puzzle_id=
                            puzzle_id,

                        config=
                            config,

                        state=
                            state,

                        sistema_cacada=
                            sistema_cacada,
                    )
                )

                _save_state(
                    user_id,
                    dungeon_id,
                    puzzle_id,
                    state
                )

                state[
                    "revision"
                ] += 1

                return {

                    "success":
                        True,

                    "acao":
                        "sequencia_errada",

                    "invocar_mimico":
                        True,

                    "spawn_id":
                        spawn_id,

                    "monster_id":
                        config.get(
                            "monster_id"
                        ),

                    "mensagem":
                        (
                            "As runas rejeitam a combinação... "
                            "algo se move dentro do baú!"
                        ),

                    "estado":
                        _public_state(
                            state
                        ),
                }

        # ====================================================
        # ✅ CORRETO — ABRIR O BAÚ
        # ====================================================

        loot_id = str(
            config.get(
                "loot_id",
                ""
            )
        )

        (
            delivered,
            rewards,
            error
        ) = _grant_chest_reward(
            player,
            loot_id
        )

        if not delivered:

            return {

                "success":
                    False,

                "acao":
                    "loot_nao_configurado",

                "mensagem":
                    error,

                "loot_id":
                    loot_id,

                "estado":
                    _public_state(
                        state
                    ),
            }

        state[
            "chest_open"
        ] = True

        _save_state(
            user_id,
            dungeon_id,
            puzzle_id,
            state
        )

        state[
            "revision"
        ] += 1

        return {

            "success":
                True,

            "acao":
                "bau_aberto",

            "mensagem":
                (
                    "O selo se rompeu. "
                    "Você recebeu o tesouro!"
                ),

            "loot_id":
                loot_id,

            "recompensas":
                rewards,

            "estado":
                _public_state(
                    state
                ),
        }
    
# ============================================================
# ⚔️ FINALIZAR COMBATE DO MÍMICO
# ============================================================

def finalizar_combate_mimico(
    *,
    user_id: str,
    spawn_id: str,
    sistema_cacada,
    resultado: str
):

    with _EVENT_LOCK:

        if not spawn_id:

            return {
                "success": False,
                "error":
                    "Spawn de evento ausente."
            }

        event_mob = None
        event_region = None

        mobs_vivos = (

            getattr(
                sistema_cacada,
                "mobs_vivos",
                {}
            )

            if sistema_cacada
            else {}

        )

        for (
            region,
            mobs
        ) in mobs_vivos.items():

            mob = (
                mobs
                or {}
            ).get(
                str(spawn_id)
            )

            if mob:

                event_mob = mob

                event_region = str(
                    region
                )

                break

        if (
            not event_mob
            or not event_mob.get(
                "evento_dungeon"
            )
        ):

            return {

                "success":
                    False,

                "error":
                    "Esse combate não pertence a um evento de dungeon.",
            }

        owner_id = str(
            event_mob.get(
                "event_owner_id",
                ""
            )
        )

        if (
            owner_id
            and owner_id
            != str(user_id)
        ):

            return {

                "success":
                    False,

                "error":
                    "Esse Mímico pertence a outro jogador.",
            }

        dungeon_id = str(

            event_mob.get(
                "dungeon_id"
            )

            or event_region

            or ""

        )

        puzzle_id = str(

            event_mob.get(
                "puzzle_id"
            )

            or event_mob.get(
                "event_id"
            )

            or ""

        )

        (
            _player,
            _config,
            state
        ) = _ensure_state(
            user_id,
            dungeon_id,
            puzzle_id
        )

        # Remove o Mímico da RAM.
        # Não usa respawn normal.

        _remove_event_spawn(
            sistema_cacada,
            dungeon_id,
            spawn_id
        )

        state[
            "mimic_active"
        ] = False

        state[
            "mimic_spawn_id"
        ] = None

        # Depois do Mímico,
        # precisa tentar a sequência
        # desde o começo.

        state[
            "progress"
        ] = []

        state[
            "last_mimic_result"
        ] = str(
            resultado
        )

        if (
            str(resultado)
            == "vitoria"
        ):

            state[
                "mimics_defeated"
            ] = (

                int(
                    state.get(
                        "mimics_defeated",
                        0
                    )
                )

                + 1
            )

        _save_state(
            user_id,
            dungeon_id,
            puzzle_id,
            state
        )

        state[
            "revision"
        ] += 1

        return {

            "success":
                True,

            "dungeon_id":
                dungeon_id,

            "puzzle_id":
                puzzle_id,

            "resultado":
                str(
                    resultado
                ),

            "estado":
                _public_state(
                    state
                ),
        }


# ============================================================
# 🔎 É MOB DE EVENTO?
# ============================================================

def is_dungeon_event_mob(
    mob
) -> bool:

    return bool(

        isinstance(
            mob,
            dict
        )

        and (

            mob.get(
                "evento_dungeon"
            )

            or mob.get(
                "tipo_evento"
            ) == "dungeon_event"

            or mob.get(
                "origem"
            ) == "dungeon_event"

        )

    )


# ============================================================
# 🔒 VALIDAR DONO DO MÍMICO
# ============================================================

def validate_event_mob_owner(
    mob,
    user_id: str
) -> bool:

    if not is_dungeon_event_mob(
        mob
    ):
        return True

    owner = str(
        (
            mob
            or {}
        ).get(
            "event_owner_id",
            ""
        )
    )

    return (
        not owner
        or owner
        == str(user_id)
    )