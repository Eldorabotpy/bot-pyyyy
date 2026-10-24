"""Sorteio de drops independentes e grupos de alternativas exclusivas."""

import random


def roll_loot(loot_table, luck_bonus=0, player_data=None):
    from modules.skill_tome_rewards import CLASS_SKILL_TOME_MARKER, resolve_class_skill_tome

    items = []
    groups = {}
    for entry in loot_table if isinstance(loot_table, list) else []:
        if not isinstance(entry, dict) or not entry.get("item_id"):
            continue
        group = entry.get("loot_group")
        if group:
            groups.setdefault(group, []).append(entry)
            continue
        chance = float(entry.get("drop_chance", 0)) + luck_bonus
        if random.random() * 100 < min(100, max(0, chance)):
            item_id = entry["item_id"]
            if item_id == CLASS_SKILL_TOME_MARKER:
                item_id = resolve_class_skill_tome(player_data, f"dungeon:{random.random()}")
            if item_id:
                items.append(item_id)

    # Grupos usam chances fixas: sorte não multiplica a chance por alternativa.
    for entries in groups.values():
        weights = [max(0, float(entry.get("drop_chance", 0))) for entry in entries]
        total = sum(weights)
        if total <= 0:
            continue
        roll = random.random() * max(100, total)
        cumulative = 0
        for entry, weight in zip(entries, weights):
            cumulative += weight
            if roll < cumulative:
                item_id = entry["item_id"]
                if item_id == CLASS_SKILL_TOME_MARKER:
                    item_id = resolve_class_skill_tome(player_data, f"dungeon:{random.random()}")
                if item_id:
                    items.append(item_id)
                break
    return items
