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
        # BAÚ JÁ ABERTO
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
                    "As pedras já revelaram o segredo do baú.",

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

            spawn_id = (
                _create_mimic_spawn(

                    user_id=user_id,

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
                    "mimico_ativo",

                "invocar_mimico":
                    True,

                "spawn_id":
                    spawn_id,

                "monster_id":
                    config[
                        "monster_id"
                    ],

                "mensagem":
                    "O Mímico ainda está à espreita!",

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

        if (
            len(progress)
            >= len(sequence)
        ):

            state[
                "resolved"
            ] = True

            _save_state(
                user_id,
                dungeon_id,
                puzzle_id,
                state
            )

            state["revision"] += 1

            return {

                "success": True,

                "acao":
                    "puzzle_resolvido",

                "mensagem":
                    "As três pedras responderam. O baú foi destravado!",

                "estado":
                    _public_state(
                        state
                    ),
            }

        expected = sequence[
            len(progress)
        ]

        # ====================================================
        # ✅ ACERTO
        # ====================================================

        if indice == expected:

            progress.append(
                indice
            )

            state[
                "progress"
            ] = progress

            # Última pedra.

            if (
                len(progress)
                == len(sequence)
            ):

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

                return {

                    "success":
                        True,

                    "acao":
                        "puzzle_resolvido",

                    "mensagem":
                        "As três pedras responderam. O baú foi destravado!",

                    "estado":
                        _public_state(
                            state
                        ),
                }

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
                    "luz_correta",

                "mensagem":
                    "A pedra começou a brilhar.",

                "estado":
                    _public_state(
                        state
                    ),
            }

        # ====================================================
        # ❌ ERROU
        # ====================================================

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

        # Apaga todas as pedras.
        state[
            "progress"
        ] = []

        spawn_id = None

        if config.get(
            "trigger_mimic_on_wrong",
            True
        ):

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
                bool(
                    spawn_id
                ),

            "spawn_id":
                spawn_id,

            "monster_id":
                (
                    config.get(
                        "monster_id"
                    )
                    if spawn_id
                    else None
                ),

            "mensagem":
                "A sequência falhou... o baú revelou sua verdadeira natureza!",

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

    gold = max(
        0,
        int(
            reward.get(
                "gold",
                0
            )
            or 0
        )
    )

    items = (
        reward.get(
            "items",
            {}
        )
        or {}
    )

    delivered_items = []

    for (
        item_id,
        qty
    ) in items.items():

        qty = max(
            0,
            int(
                qty
                or 0
            )
        )

        if qty <= 0:
            continue

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
                + qty
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
                + qty
            )

        else:

            inventory[
                item_id
            ] = {

                "base_id":
                    item_id,

                "quantity":
                    qty,
            }

        delivered_items.append({

            "item_id":
                item_id,

            "quantity":
                qty,
        })

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
        # MÍMICO JÁ ACORDADO
        # ====================================================

        if state.get(
            "mimic_active"
        ):

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
                    "mimico_ativo",

                "invocar_mimico":
                    True,

                "spawn_id":
                    spawn_id,

                "monster_id":
                    config[
                        "monster_id"
                    ],

                "mensagem":
                    "O baú se contorce e mostra os dentes!",

                "estado":
                    _public_state(
                        state
                    ),
            }

        # ====================================================
        # TENTOU ABRIR ANTES DE RESOLVER
        # ====================================================

        if not state.get(
            "resolved"
        ):

            state[
                "progress"
            ] = []

            spawn_id = None

            if config.get(
                "trigger_mimic_on_early_chest",
                True
            ):

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
                    "bau_armadilha",

                "invocar_mimico":
                    bool(
                        spawn_id
                    ),

                "spawn_id":
                    spawn_id,

                "monster_id":
                    (
                        config.get(
                            "monster_id"
                        )
                        if spawn_id
                        else None
                    ),

                "mensagem":
                    "O baú era uma armadilha. Um Mímico desperta!",

                "estado":
                    _public_state(
                        state
                    ),
            }

        # ====================================================
        # PUZZLE RESOLVIDO
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
                "O selo se rompeu. Você recebeu o tesouro!",

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