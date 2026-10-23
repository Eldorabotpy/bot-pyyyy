# Regras compartilhadas: equipamento, Forja, perfil e mercado.
SOCKETS_BY_RARITY = {"comum": 0, "bom": 0, "incomum": 0, "raro": 1, "epico": 2, "lendario": 3}
EXTRACTION_GEMS = 5
EVOLUTION_COSTS = {1: {"gold": 500, "po_runico": 5}, 2: {"gold": 1500, "po_runico": 15, "fragmento_runa_ancestral": 1}}
EVOLUTION_SUCCESS_CHANCE = {1: 70, 2: 50}
DUST_YIELD = {1: 2, 2: 6, 3: 18}

RUNE_NAME_PREFIXES = {
    "crueldade": "da Crueldade", "precisao": "da Precisão", "vampiro": "do Vampiro",
    "rocha": "da Rocha", "mente": "da Mente", "eco": "do Eco", "midas": "de Midas", "sabio": "do Sábio",
}

# Completa os níveis das famílias existentes, mantendo os valores já publicados.
FAMILIES = {
    "crueldade": ("Crueldade", "crit_damage_mult", [5, 10, 20], "Dano crítico", "%", "#e98484"),
    "precisao": ("Precisão", "crit_chance_flat", [2, 4, 6], "Chance crítica", "%", "#edb37c"),
    "vampiro": ("Vampiro", "lifesteal", [1, 3, 5], "Roubo de vida", "%", "#cf83ab"),
    "rocha": ("Rocha", "defesa_fisica", [3, 6, 10], "Defesa", "", "#a8be92"),
    "mente": ("Mente", "max_mana", [10, 20, 40], "Mana máxima", "", "#82c6eb"),
    "eco": ("Eco", "magic_attack", [2, 4, 8], "Poder mágico", "", "#b49ae9"),
    "midas": ("Midas", "gold_multiplier", [5, 10, 15], "Ouro em caçadas", "%", "#dfbd6e"),
    "sabio": ("Sábio", "xp_multiplier", [3, 6, 9], "XP em caçadas", "%", "#afcfdb"),
}

RUNE_NAME_PREFIXES = {
    "crueldade": "da Crueldade",
    "precisao": "da Precisão",
    "vampiro": "do Vampiro",
    "rocha": "da Rocha",
    "mente": "da Mente",
    "eco": "do Eco",
    "midas": "de Midas",
    "sabio": "do Sábio",
}

def complete_catalog(runes):
    for family, (name, stat, values, label, unit, color) in FAMILIES.items():
        for tier, suffix in enumerate(("menor", "maior", "ancestral"), 1):
            rid = f"runa_{family}_{suffix}"
            row = runes.setdefault(rid, {"name": f"Runa {RUNE_NAME_PREFIXES[family]} {suffix.title()}", "stat_key": stat, "value": values[tier-1], "type": "percent" if unit else "flat", "tier": tier, "desc": f"+{values[tier-1]}{unit} {label}"})
            icon_url = f"https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/runas/{rid}.png"
            row.update({"family": family, "family_name": name, "color": color, "icon": icon_url, "icon_url": icon_url})
            row["next_id"] = f"runa_{family}_{('maior' if tier == 1 else 'ancestral')}" if tier < 3 else None
