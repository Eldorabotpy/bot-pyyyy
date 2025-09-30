# modules/dungeon_loot.py
import random
from modules import player_manager, game_data

def _roll_rarity(weights: dict[str, int]) -> str:
    total = sum(int(w) for w in weights.values()) or 1
    r = random.randint(1, total)
    acc = 0
    for k, w in weights.items():
        acc += int(w)
        if r <= acc:
            return k
    return "comum"

def _choose_set_base(pdata: dict, dcfg: dict) -> str:
    sp = dcfg.get("set_piece", {})
    cls = (pdata.get("class") or "").lower()
    mage_classes = [c.lower() for c in sp.get("mage_classes", [])]
    return sp.get("mage") if cls in mage_classes else sp.get("default")

def _hp_for_rarity(dcfg: dict, rarity: str) -> int:
    sp = dcfg.get("set_piece", {})
    table = sp.get("hp_by_rarity", {})
    return int(table.get(rarity, 10))

def create_set_piece_instance(base_id: str, rarity: str, hp_value: int) -> dict:
    return {
        "base_id": base_id,
        "rarity": rarity,
        "enchantments": {"hp": {"value": int(hp_value)}},
    }

def award_dungeon_rewards(pdata: dict, dungeon_key: str, diff_key: str):
    dcfg = game_data.DUNGEONS[dungeon_key]
    diff = dcfg["difficulties"][diff_key]

    # Ouro garantido
    player_manager.add_gold(pdata, int(diff["gold_reward"]))

    # Outros drops (por chance)
    for entry in diff.get("other_drops", []):
        if random.random() <= float(entry.get("chance", 0)):
            qty = random.randint(int(entry["min"]), int(entry["max"]))
            player_manager.add_item_to_inventory(pdata, entry["item_id"], qty)

    # Peça do set (chance)
    if random.random() <= float(diff.get("set_piece_drop_chance", 0)):
        base_id = _choose_set_base(pdata, dcfg)
        rarity = _roll_rarity(diff["rarity_weights"])
        hp_val = _hp_for_rarity(dcfg, rarity)
        inst = create_set_piece_instance(base_id, rarity, hp_val)
        player_manager.add_unique_item(pdata, inst)

    return pdata
