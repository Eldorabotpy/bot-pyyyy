# modules/items_api.py
from __future__ import annotations
import uuid
import random
from typing import Dict, Any, List

from modules import game_data  # assume que já existe

# -----------------------------------------------------------
# Helpers
# -----------------------------------------------------------

_AFFIX_BUDGET = {
    "comum": 0,
    "bom": 1,
    "raro": 2,
    "epico": 3,
    "lendario": 4,
}

def _safe_item_info(base_id: str) -> Dict[str, Any]:
    info = game_data.get_item_info(base_id) or {}
    info.setdefault("display_name", base_id)
    info.setdefault("emoji", "✨")
    info.setdefault("slot", None)
    return info

def _roll_primary_stat(slot: str | None, rarity: str) -> Dict[str, int]:
    """
    Usa ITEM_SLOTS + BASE_STATS_BY_RARITY do seu game_data.
    Se não houver dados para o slot, retorna {}.
    """
    if not slot:
        return {}

    slot_meta = (game_data.ITEM_SLOTS or {}).get(slot)
    if not slot_meta:
        return {}

    stat_name = slot_meta.get("primary_stat")
    if not stat_name:
        return {}

    rar_map = (
        (game_data.BASE_STATS_BY_RARITY or {})
        .get(slot, {})
        .get(stat_name, {})
    )
    rng = rar_map.get(rarity) or rar_map.get("comum") or [1, 1]
    try:
        low, high = int(rng[0]), int(rng[1])
    except Exception:
        low, high = 1, 1

    val = random.randint(low, high)
    return {stat_name: val}

def _pick_affixes(rarity: str, pools: List[str], exclude: List[str]) -> Dict[str, int]:
    """
    Sorteia afixos de acordo com o budget da raridade, a partir das POOLS pedidas.
    Evita duplicar o atributo primário.
    """
    budget = _AFFIX_BUDGET.get(rarity, 0)
    if budget <= 0:
        return {}

    # junta pools
    combined: List[str] = []
    for pool in pools:
        combined.extend((game_data.AFFIX_POOLS or {}).get(pool, []))

    # lista única e limpa excluídos
    uniq = list({name for name in combined if name})
    uniq = [a for a in uniq if a not in exclude]

    random.shuffle(uniq)
    chosen = uniq[:budget]

    out: Dict[str, int] = {}
    for name in chosen:
        info = (game_data.AFFIXES or {}).get(name)
        if not info:
            continue
        rng = (info.get("values") or {}).get(rarity) or (info.get("values") or {}).get("comum") or [1, 1]
        try:
            low, high = int(rng[0]), int(rng[1])
        except Exception:
            low, high = 1, 1
        out[name] = random.randint(low, high)
    return out

# -----------------------------------------------------------
# API pública (compatível com o admin antigo)
# -----------------------------------------------------------

def generate_item_instance(
    base_id: str,
    rarity: str = "comum",
    seed: int | None = None,
    affix_pools: List[str] | None = None,
) -> Dict[str, Any]:
    """
    Gera uma instância única de item, **sem depender do sistema de forja**.
    - Usa o atributo primário por slot (se definido em game_data).
    - Usa afixos de pools informadas (padrão: ["geral"]).
    - Não consome inventário nem player_data.
    """
    if seed is not None:
        random.seed(seed)

    info = _safe_item_info(base_id)
    slot = info.get("slot")

    item: Dict[str, Any] = {
        "uuid": str(uuid.uuid4()),
        "base_id": base_id,
        "rarity": rarity,
        "upgrade_level": 1,
        "durability": [20, 20],
        "attributes": {},
        # campos auxiliares úteis
        "_display_name": info["display_name"],
        "_emoji": info["emoji"],
        "_slot": slot,
    }

    # atributo primário por slot
    prim = _roll_primary_stat(slot, rarity)
    item["attributes"].update(prim)

    # afixos (por padrão, apenas da pool "geral")
    pools = affix_pools or ["geral"]
    exclude = list(prim.keys())
    sec = _pick_affixes(rarity, pools, exclude)
    item["attributes"].update(sec)

    return item

def render_item_line(item: Dict[str, Any]) -> str:
    """
    Converte o dicionário do item numa linha amigável para Telegram.
    """
    emoji = item.get("_emoji") or "✨"
    name = item.get("_display_name") or item.get("base_id", "Item")
    rarity = item.get("rarity", "comum")

    attrs = item.get("attributes") or {}
    if attrs:
        parts = []
        # ordem estável/bonita
        for k in sorted(attrs.keys()):
            v = attrs[k]
            try:
                parts.append(f"{k} +{int(v)}")
            except Exception:
                parts.append(f"{k}: {v}")
        attrs_txt = " – " + ", ".join(parts)
    else:
        attrs_txt = ""

    return f"{emoji} {name} ({rarity}){attrs_txt}"
