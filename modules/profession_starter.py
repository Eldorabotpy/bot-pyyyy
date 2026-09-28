"""Prepare a profession tool without overwriting existing equipment."""
from copy import deepcopy
from uuid import uuid4


def prepare_profession_tool(player, profession):
    from modules.game_data.items_tools import TOOLS_DATA

    inventory = deepcopy(player.get('inventory') or {})
    equipment = dict(player.get('equipment_tools') or {})
    candidates = []
    for uid, item in inventory.items():
        base = item.get('base_id', uid) if isinstance(item, dict) else uid
        meta = TOOLS_DATA.get(base, {})
        if meta.get('tool_type') == profession:
            candidates.append((uid, meta))
    equipped = equipment.get(profession)
    if any(uid == equipped for uid, _ in candidates):
        return inventory, equipment
    if candidates:
        uid, _ = max(candidates, key=lambda entry: int(entry[1].get('tier', 1)))
    else:
        starters = [(key, meta) for key, meta in TOOLS_DATA.items()
                    if meta.get('tool_type') == profession and meta.get('tier') == 1]
        if not starters:
            raise ValueError('Ferramenta inicial deste ofício não encontrada.')
        base, meta = starters[0]
        uid = str(uuid4())
        inventory[uid] = {
            'base_id': base, 'quantity': 1, 'rarity': meta.get('rarity', 'comum'),
            'upgrade_level': 0, 'durability': deepcopy(meta['durability']),
            'crafter': 'Mestre de ofício',
        }
    equipment[profession] = uid
    return inventory, equipment
