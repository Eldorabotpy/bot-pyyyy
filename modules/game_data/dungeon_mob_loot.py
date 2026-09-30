"""Loot das Catacumbas: chances percentuais por abate, não por participante."""

from .items_evolution import EVOLUTION_ITEMS_DATA
from .runes_data import RUNES_DB


def _pool(group, item_ids, chance):
    ids = sorted(item_ids)
    return [
        {"item_id": item_id, "drop_chance": chance / len(ids), "loot_group": group}
        for item_id in ids
    ]


def catacumbas_loot(*, elite=False, boss=False):
    # Materiais básicos e emblemas, sem antecipar almas/divinos de tiers finais.
    evolution = [
        item_id for item_id, item in EVOLUTION_ITEMS_DATA.items()
        if item_id.startswith("emblema_") or item.get("type") == "material_especial"
    ]
    loot = _pool("evolucao", evolution, 100 if boss else 20 if elite else 12)
    loot.append({
        "item_id": "fragmento_runa_ancestral",
        "drop_chance": 100 if boss else 10 if elite else 5,
    })
    if boss:
        # Um único sorteio: exatamente uma runa, 90% Maior / 10% Ancestral.
        for tier, chance in ((2, 90), (3, 10)):
            loot.extend(_pool("runa", [rid for rid, rune in RUNES_DB.items()
                                       if rune["tier"] == tier], chance))
    else:
        loot.extend(_pool("runa", [rid for rid, rune in RUNES_DB.items()
                                   if rune["tier"] == 1], 5 if elite else 2))
    return loot
