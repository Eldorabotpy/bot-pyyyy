# modules/dungeons/registry.py
from __future__ import annotations
from typing import Dict, List, Any
from dataclasses import asdict

from modules import game_data
from .regions import REGIONAL_DUNGEONS, MobDef

# --------- helpers de stat ----------

def _as_int(d: dict, k: str, default: int) -> int:
    try:
        return int(d.get(k, default))
    except Exception:
        return default

def _mobdef_to_floor(m: MobDef) -> dict:
    """
    Converte o MobDef (com 'max_hp') para o formato do runtime:
    hp, attack, defense, initiative, luck + metadados.
    """
    base = m.stats_base or {}
    floor = {
        "id": m.key,
        "name": m.display,
        "emoji": m.emoji or "",
        "file_id_name": m.media_key,  # usado pela UI
        # map max_hp -> hp
        "hp": _as_int(base, "max_hp", 10),
        "attack": _as_int(base, "attack", 5),
        "defense": _as_int(base, "defense", 2),
        "initiative": _as_int(base, "initiative", 5),
        "luck": _as_int(base, "luck", 5),
        # recompensas base do monstro (pode customizar por mob)
        "xp_reward": 12,
        "gold_drop": 7,
        # loot por andar (pode variar — exemplo simples)
        "loot_table": [
            # Exemplo: 8% fragmento de evolução (ajuste itens/IDs conforme seu ITEMS_DATA)
            {"item_id": "fragmento_evolucao_generico", "drop_chance": 8},
            # Exemplo: 20% de Essência
            {"item_id": "essencia_mistica", "drop_chance": 20},
        ],
        "is_boss": "(BOSS)" in (m.display or "").upper() or "BOSS" in (m.display or ""),
    }
    return floor

# Se você tiver uma base de mobs global (ex.: game_data.MONSTERS),
# aqui dá pra puxar por ID ao invés de usar m.stats_base:
def _from_global_monsters(mob_id: str) -> dict | None:
    MONS = getattr(game_data, "MONSTERS", None)
    if not isinstance(MONS, dict):
        return None
    src = MONS.get(mob_id)
    if not isinstance(src, dict):
        return None
    return {
        "id": mob_id,
        "name": src.get("display_name") or src.get("name") or mob_id,
        "emoji": src.get("emoji", ""),
        "file_id_name": src.get("file_id_name"),
        "hp": _as_int(src, "max_hp", _as_int(src, "hp", 10)),
        "attack": _as_int(src, "attack", 5),
        "defense": _as_int(src, "defense", 2),
        "initiative": _as_int(src, "initiative", 5),
        "luck": _as_int(src, "luck", 5),
        "xp_reward": _as_int(src, "xp_reward", 12),
        "gold_drop": _as_int(src, "gold_drop", 7),
        "loot_table": list(src.get("loot_table") or []),
        "is_boss": bool(src.get("is_boss")),
    }

# --------- fábrica de dungeon ---------

def _build_dungeon(region_key: str, cfg: Dict[str, Any]) -> dict:
    """
    Transforma a entrada do REGIONAL_DUNGEONS em dungeon no formato do runtime.
    """
    floors: List[dict] = []
    for entry in (cfg.get("floors") or []):
        if isinstance(entry, MobDef):
            floors.append(_mobdef_to_floor(entry))
        elif isinstance(entry, dict) and entry.get("ref"):  # modo referência à base global
            ref_id = str(entry["ref"])
            base = _from_global_monsters(ref_id)
            if base:
                # permite overrides pontuais no regions.py, tipo loot extra
                override = dict(entry)
                override.pop("ref", None)
                base.update(override)
                floors.append(base)

    # Config padrão com opções que o runtime lê:
    dungeon = {
        "display_name": f"{cfg.get('emoji','')} {cfg.get('label', region_key)}".strip(),
        # opcional: requisito de chave para entrar
        "key_item": cfg.get("key_item", "cristal_de_abertura"),
        # escala por dificuldade
        "difficulty_scale": cfg.get("difficulty_scale", {
            "facil": 0.9,
            "normal": 1.0,
            "infernal": 1.25,
        }),
        # ouro final por dificuldade (pode usar gold_base como base)
        "final_gold": cfg.get("final_gold") or {
            "facil": int((cfg.get("gold_base", 600)) * 0.7),
            "normal": int(cfg.get("gold_base", 600)),
            "infernal": int((cfg.get("gold_base", 600)) * 1.3),
        },
        "floors": floors,
    }
    return dungeon

# --------- API esperada pelo runtime ---------

def get_dungeon_for_region(region_key: str) -> dict | None:
    cfg = REGIONAL_DUNGEONS.get(region_key)
    if not cfg:
        return None
    return _build_dungeon(region_key, cfg)
