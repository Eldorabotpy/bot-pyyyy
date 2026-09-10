# modules/player/combat_stats.py

from __future__ import annotations

import asyncio
import threading
from typing import Any, Dict

from bson import ObjectId

COMBAT_INT_STAT_KEYS = (
    "max_hp",
    "max_mana",
    "attack",
    "defense",
    "initiative",
    "luck",
    "magic_attack",
)


COMBAT_FLOAT_STAT_KEYS = (
    "armor_penetration",
    "accuracy_flat",
    "crit_chance_flat",
    "crit_damage_mult",
    "double_attack_chance_flat",
    "dodge_chance_flat",
)


COMBAT_STAT_KEYS = (
    COMBAT_INT_STAT_KEYS
    +
    COMBAT_FLOAT_STAT_KEYS
)


def _int_safe(valor: Any, default: int = 0) -> int:
    try:
        return int(round(float(valor)))
    except Exception:
        return int(default)

def _float_safe(
    valor: Any,
    default: float = 0.0,
) -> float:
    try:

        return float(
            valor
        )

    except Exception:

        return float(
            default
        )
    
def _run_async_sync(coro):
    """
    Executa coroutine em contexto síncrono.
    Funciona em Flask/thread normal e também quando já existe event loop ativo.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    resultado = {}
    erro = {}

    def runner():
        try:
            resultado["valor"] = asyncio.run(coro)
        except Exception as e:
            erro["erro"] = e

    t = threading.Thread(target=runner, daemon=True)
    t.start()
    t.join()

    if erro.get("erro"):
        raise erro["erro"]

    return resultado.get("valor")


def _normalizar_oid(user_id):
    if isinstance(user_id, ObjectId):
        return user_id

    sid = str(user_id or "").strip()
    if ObjectId.is_valid(sid):
        return ObjectId(sid)

    return None


def _calcular_base_stats_seguro(player_data: dict) -> dict:
    try:
        from modules.player.stats import _get_class_key_normalized, _compute_class_baseline_for_level

        lvl = int(player_data.get("level", 1) or 1)
        ckey = _get_class_key_normalized(player_data)
        return _compute_class_baseline_for_level(ckey, lvl)
    except Exception:
        return player_data.get("base_stats", {}) or {}


async def get_combat_stats(player_data: dict) -> Dict[str, int]:
    """
    Fonte única de status de combate.

    Regra:
    1. get_player_total_stats(player_data) é a fonte oficial.
    2. player_data["stats"] é cache/fallback.
    3. campos da raiz são fallback legado.

    Combate não deve usar player.get("attack") direto.
    """
    from modules.player.stats import get_player_total_stats

    player_data = player_data or {}

    try:
        calculado = await get_player_total_stats(player_data)
    except Exception as e:
        print(f"⚠️ [COMBAT STATS] Falha no get_player_total_stats: {e}")
        calculado = {}

    cache_stats = player_data.get("stats", {}) or {}
    if not isinstance(cache_stats, dict):
        cache_stats = {}

    def pegar(chave: str, default: int = 0) -> int:
        for fonte in (calculado, cache_stats, player_data):
            if isinstance(fonte, dict) and fonte.get(chave) is not None:
                return _int_safe(fonte.get(chave), default)
        return int(default)

    def pegar_float(
        chave: str,
        default: float = 0.0,
    ) -> float:

        for fonte in (
            calculado,
            cache_stats,
            player_data,
        ):

            if (
                isinstance(
                    fonte,
                    dict,
                )
                and
                fonte.get(
                    chave
                )
                is not None
            ):

                return _float_safe(
                    fonte.get(
                        chave
                    ),
                    default,
                )


        return float(
            default
        )
    
    max_hp = max(1, pegar("max_hp", 100))
    max_mana = max(10, pegar("max_mana", 50))

    current_hp = _int_safe(player_data.get("current_hp", max_hp), max_hp)
    current_mp = _int_safe(player_data.get("current_mp", max_mana), max_mana)

    return {
        "max_hp":
            max_hp,

        "max_mana":
            max_mana,

        "attack":
            max(
                0,
                pegar(
                    "attack",
                    5,
                ),
            ),

        "defense":
            max(
                0,
                pegar(
                    "defense",
                    0,
                ),
            ),

        "initiative":
            max(
                0,
                pegar(
                    "initiative",
                    5,
                ),
            ),

        "luck":
            max(
                0,
                pegar(
                    "luck",
                    0,
                ),
            ),

        "magic_attack":
            max(
                0,
                pegar(
                    "magic_attack",
                    0,
                ),
            ),


        # ====================================================
        # ⚔️ ATRIBUTOS ESPECIAIS
        # ====================================================

        "armor_penetration":
            max(
                0.0,
                pegar_float(
                    "armor_penetration",
                ),
            ),

        "accuracy_flat":
            max(
                0.0,
                pegar_float(
                    "accuracy_flat",
                ),
            ),

        "crit_chance_flat":
            max(
                0.0,
                pegar_float(
                    "crit_chance_flat",
                ),
            ),

        "crit_damage_mult":
            max(
                0.0,
                pegar_float(
                    "crit_damage_mult",
                ),
            ),

        "double_attack_chance_flat":
            max(
                0.0,
                pegar_float(
                    "double_attack_chance_flat",
                ),
            ),

        "dodge_chance_flat":
            max(
                0.0,
                pegar_float(
                    "dodge_chance_flat",
                ),
            ),


        "current_hp":
            max(
                0,
                min(
                    current_hp,
                    max_hp,
                ),
            ),

        "current_mp":
            max(
                0,
                min(
                    current_mp,
                    max_mana,
                ),
            ),
    }


def get_combat_stats_sync(player_data: dict) -> Dict[str, int]:
    return _run_async_sync(get_combat_stats(player_data))


def aplicar_combat_stats_no_player(player_data: dict, stats: dict | None = None) -> dict:
    """
    Normaliza o dict do jogador para qualquer motor de combate.
    Atualiza raiz e player_data["stats"] com os mesmos valores oficiais.
    """
    player_data = player_data or {}

    if stats is None:
        stats = get_combat_stats_sync(player_data)

    if not isinstance(player_data.get("stats"), dict):
        player_data["stats"] = {}

    for chave in COMBAT_STAT_KEYS:

        if (
            chave
            in
            COMBAT_FLOAT_STAT_KEYS
        ):

            valor = _float_safe(
                stats.get(
                    chave,
                    0.0
                ),
                0.0,
            )


        else:

            valor = _int_safe(
                stats.get(
                    chave,
                    0
                ),
                0,
            )


        player_data[
            chave
        ] = valor


        player_data[
            "stats"
        ][
            chave
        ] = valor

    player_data["current_hp"] = int(stats.get("current_hp", stats.get("max_hp", 1)) or 1)
    player_data["current_mp"] = int(stats.get("current_mp", stats.get("max_mana", 10)) or 10)
    player_data["base_stats"] = _calcular_base_stats_seguro(player_data)

    return player_data


async def sync_combat_stats_to_db(user_id: str, player_data: dict) -> dict:
    """
    Recalcula e grava no Mongo:
    - stats final
    - espelho da raiz
    - base_stats
    - current_hp/current_mp limitados ao máximo real

    Use depois de equipar, desequipar, refinar, encantar, distribuir ponto,
    subir level ou qualquer mudança que afete atributo.
    """
    from modules.player.core import users_collection, clear_player_cache

    oid = _normalizar_oid(user_id or player_data.get("_id"))
    if not oid:
        raise ValueError(f"ID inválido para sync_combat_stats_to_db: {user_id}")

    stats = await get_combat_stats(player_data)
    player_data = aplicar_combat_stats_no_player(player_data, stats)

    update_set = {
        "stats": player_data.get("stats", {}),
        "base_stats": player_data.get("base_stats", {}),
        "max_hp": int(player_data.get("max_hp", stats["max_hp"])),
        "max_mana": int(player_data.get("max_mana", stats["max_mana"])),
        "attack": int(player_data.get("attack", stats["attack"])),
        "defense": int(player_data.get("defense", stats["defense"])),
        "initiative": int(player_data.get("initiative", stats["initiative"])),
        "luck": int(player_data.get("luck", stats["luck"])),
        "magic_attack": int(player_data.get("magic_attack", stats["magic_attack"])),
        "armor_penetration":
            _float_safe(
                player_data.get(
                    "armor_penetration",
                    stats.get(
                        "armor_penetration",
                        0.0,
                    ),
                ),
            ),

        "accuracy_flat":
            _float_safe(
                player_data.get(
                    "accuracy_flat",
                    stats.get(
                        "accuracy_flat",
                        0.0,
                    ),
                ),
            ),

        "crit_chance_flat":
            _float_safe(
                player_data.get(
                    "crit_chance_flat",
                    stats.get(
                        "crit_chance_flat",
                        0.0,
                    ),
                ),
            ),

        "crit_damage_mult":
            _float_safe(
                player_data.get(
                    "crit_damage_mult",
                    stats.get(
                        "crit_damage_mult",
                        0.0,
                    ),
                ),
            ),

        "double_attack_chance_flat":
            _float_safe(
                player_data.get(
                    "double_attack_chance_flat",
                    stats.get(
                        "double_attack_chance_flat",
                        0.0,
                    ),
                ),
            ),

        "dodge_chance_flat":
            _float_safe(
                player_data.get(
                    "dodge_chance_flat",
                    stats.get(
                        "dodge_chance_flat",
                        0.0,
                    ),
                ),
            ),
            
        "current_hp": int(player_data.get("current_hp", stats["current_hp"])),
        "current_mp": int(player_data.get("current_mp", stats["current_mp"])),
    }

    users_collection.update_one({"_id": oid}, {"$set": update_set})

    try:
        await clear_player_cache(oid)
        await clear_player_cache(str(oid))
    except Exception:
        pass

    return stats
