# modules/game_data/__init__.py

import logging
from telegram.ext import Application
from .premium import PREMIUM_TIERS, PREMIUM_PLANS_FOR_SALE
# --- Constantes globais ---
TRAVEL_TIME_MINUTES = 15
COLLECTION_TIME_MINUTES = 10


def get_xp_for_next_collection_level(level: int) -> int:
    return 10 * (level ** 2) + 40

def get_xp_for_next_combat_level(level: int) -> int:
    return 20 * (level ** 2) + 80

def _safe_import(modpath, names: dict, defaults: dict):
    try:
        m = __import__(modpath, fromlist=list(names.values()))
        out = {}
        for alias, real in names.items():
            out[alias] = getattr(m, real)
        return out
    except Exception as e:
        print(f"[game_data] Aviso: falha ao importar {modpath}: {e}")
        return defaults

# --- Itens / Mercado ---
_vals = _safe_import(
    "modules.game_data.items",
    names={"ITEMS_DATA": "ITEMS_DATA", "ITEM_BASES": "ITEM_BASES", "MARKET_ITEMS": "MARKET_ITEMS"},
    defaults={"ITEMS_DATA": {}, "ITEM_BASES": {}, "MARKET_ITEMS": {}}
)
ITEMS_DATA = _vals["ITEMS_DATA"]
ITEM_BASES = _vals["ITEM_BASES"]
MARKET_ITEMS = _vals["MARKET_ITEMS"]

# ✅ --- Classes ---
# Adicionada uma nova secção para importar tudo de classes.py
_classes = _safe_import(
    "modules.game_data.classes",
    names={
        "CLASSES_DATA": "CLASSES_DATA",
        "CLASS_PRIMARY_DAMAGE": "CLASS_PRIMARY_DAMAGE",
        "CLASS_DMG_EMOJI": "CLASS_DMG_EMOJI",
        "get_primary_damage_profile": "get_primary_damage_profile",
        "get_stat_modifiers": "get_stat_modifiers",
    },
    defaults={
        "CLASSES_DATA": {},
        "CLASS_PRIMARY_DAMAGE": {},
        "CLASS_DMG_EMOJI": {},
        "get_primary_damage_profile": lambda *_: {},
        "get_stat_modifiers": lambda *_: {},
    }
)
CLASSES_DATA = _classes["CLASSES_DATA"]
CLASS_PRIMARY_DAMAGE = _classes["CLASS_PRIMARY_DAMAGE"]
CLASS_DMG_EMOJI = _classes["CLASS_DMG_EMOJI"]
get_primary_damage_profile = _classes["get_primary_damage_profile"]
get_stat_modifiers = _classes["get_stat_modifiers"]

# ✅ --- Atributos / Afixos ---
# Adicionamos esta nova secção para carregar os dados de attributes.py
_attrs = _safe_import(
    "modules.game_data.attributes",
    names={
        "STAT_EMOJI": "ATTRIBUTE_ICONS", # Renomeia ATTRIBUTE_ICONS para STAT_EMOJI
        "AFFIX_POOLS": "AFFIX_POOLS",
        "AFFIXES": "AFFIXES",
    },
    defaults={"STAT_EMOJI": {}, "AFFIX_POOLS": {}, "AFFIXES": {}}
)
STAT_EMOJI = _attrs["STAT_EMOJI"]
AFFIX_POOLS = _attrs["AFFIX_POOLS"]
AFFIXES = _attrs["AFFIXES"]


# --- Premium ---
PREMIUM_TIERS = _safe_import(
    "modules.game_data.premium",
    names={"PREMIUM_TIERS": "PREMIUM_TIERS"},
    defaults={"PREMIUM_TIERS": {}}
)["PREMIUM_TIERS"]

# --- Profissões ---
_vals_prof = _safe_import(
    "modules.game_data.professions",
    names={"PROFESSIONS_DATA": "PROFESSIONS_DATA", "get_profession_for_resource": "get_profession_for_resource"},
    defaults={"PROFESSIONS_DATA": {}, "get_profession_for_resource": lambda *_: None}
)
PROFESSIONS_DATA = _vals_prof["PROFESSIONS_DATA"]
get_profession_for_resource = _vals_prof["get_profession_for_resource"]

# --- Mundo / Regiões ---
WORLD_MAP = _safe_import(
    "modules.game_data.worldmap",
    names={"WORLD_MAP": "WORLD_MAP"},
    defaults={"WORLD_MAP": {}}
)["WORLD_MAP"]

_vals = _safe_import(
    "modules.game_data.regions",
    names={
        "REGIONS_DATA": "REGIONS_DATA",
        "REGION_TARGET_POWER": "REGION_TARGET_POWER",
        "REGION_SCALING_ENABLED": "REGION_SCALING_ENABLED",
    },
    defaults={"REGIONS_DATA": {}, "REGION_TARGET_POWER": {}, "REGION_SCALING_ENABLED": {}}
)
REGIONS_DATA = _vals["REGIONS_DATA"]
REGION_TARGET_POWER = _vals["REGION_TARGET_POWER"]
REGION_SCALING_ENABLED = _vals["REGION_SCALING_ENABLED"]

# --- Monstros ---
MONSTERS_DATA = _safe_import(
    "modules.game_data.monsters",
    names={"MONSTERS_DATA": "MONSTERS_DATA"},
    defaults={"MONSTERS_DATA": {}}
)["MONSTERS_DATA"]

# --- Refino ---
REFINING_RECIPES = _safe_import(
    "modules.game_data.refining",
    names={"REFINING_RECIPES": "REFINING_RECIPES"},
    defaults={"REFINING_RECIPES": {}}
)["REFINING_RECIPES"]

# --- Utils (LEGADO) ---
_utils = _safe_import(
    "modules.game_data.utils",
    names={
        "SLOT_EMOJI": "SLOT_EMOJI",
        "SLOT_ORDER": "SLOT_ORDER",
        "item_display_name": "item_display_name",
        "get_item_info": "get_item_info",
    },
    defaults={
        "SLOT_EMOJI": {
            "elmo": "🪖", "armadura": "👕", "calca": "👖", "luvas": "🧤",
            "botas": "🥾", "colar": "📿", "anel": "💍", "brinco": "🧿", "arma": "⚔️",
        },
        "SLOT_ORDER": ["arma","elmo","armadura","calca","luvas","botas","colar","anel","brinco"],
        "item_display_name": lambda base_id: (ITEMS_DATA.get(base_id) or {}).get("display_name", base_id),
        "get_item_info": lambda base_id: (ITEMS_DATA.get(base_id) or {}),
    }
)

# --- Equipamentos NOVOS (equipment.py) ---
_eq = _safe_import(
    "modules.game_data.equipment",
    names={
        "EQ_SLOT_EMOJI": "SLOT_EMOJI",
        "EQ_SLOT_ORDER": "SLOT_ORDER",
        "ITEM_SLOTS": "ITEM_SLOTS",
        "ITEM_DATABASE": "ITEM_DATABASE",
        "equip_get_item_info": "get_item_info",
    },
    defaults={
        "EQ_SLOT_EMOJI": _utils["SLOT_EMOJI"],
        "EQ_SLOT_ORDER": _utils["SLOT_ORDER"],
        "ITEM_SLOTS": {},
        "ITEM_DATABASE": {},
        "equip_get_item_info": None,
    }
)

# Preferir definições do sistema novo (se existir DB novo), senão usar as legadas
SLOT_EMOJI = _eq["EQ_SLOT_EMOJI"]
SLOT_ORDER = _eq["EQ_SLOT_ORDER"]
ITEM_SLOTS = _eq["ITEM_SLOTS"]
ITEM_DATABASE = _eq["ITEM_DATABASE"]

# get_item_info: prioriza o banco novo
if _eq["equip_get_item_info"]:
    get_item_info = _eq["equip_get_item_info"]
else:
    get_item_info = _utils["get_item_info"]

def item_display_name(base_id: str) -> str:
    info_new = ITEM_DATABASE.get(base_id) if isinstance(ITEM_DATABASE, dict) else None
    if info_new:
        return info_new.get("nome_exibicao", base_id)
    return (_utils["item_display_name"])(base_id)

# === Fallback de SLOTS e atributo primário por classe (essenciais para a forja) ===
if not ITEM_SLOTS:
    ITEM_SLOTS = {
        "arma":      {"primary_stat_type": "class_attribute"},
        "elmo":      {"primary_stat": "defesa"},
        "armadura":  {"primary_stat": "defesa"},
        "calca":     {"primary_stat": "defesa"},
        "botas":     {"primary_stat": "iniciativa"},
        "luvas":     {"primary_stat": "dmg"},
        "anel":      {"primary_stat": "sorte"},
        "colar":     {"primary_stat": "hp"},
        "brinco":    {"primary_stat": "hp"},
    }

try:
    CLASS_PRIMARY_ATTRIBUTE  # type: ignore[name-defined]
except NameError:
    CLASS_PRIMARY_ATTRIBUTE = {
        "guerreiro": "forca",
        "mago": "inteligencia",
        "berserker": "furia",
        "cacador": "precisao",
        "assassino": "letalidade",
        "bardo": "carisma",
        "monge": "foco",
        "samurai": "bushido",
    }

# --- Raridade / Escalas ---
_rar = _safe_import(
    "modules.game_data.rarity",
    names={"BASE_STATS_BY_RARITY": "BASE_STATS_BY_RARITY", "RARITY_DATA": "RARITY_DATA"},
    defaults={
        "BASE_STATS_BY_RARITY": {
            "elmo":     {"defense":   {"comum":[1,2], "bom":[2,3], "raro":[3,5],  "epico":[5,7],   "lendario":[7,9]}},
            "armadura": {"defense":   {"comum":[2,3], "bom":[3,5], "raro":[5,7],  "epico":[7,10],  "lendario":[10,14]}},
            "calca":    {"defense":   {"comum":[1,2], "bom":[2,3], "raro":[3,4],  "epico":[4,6],   "lendario":[6,8]}},
            "botas":    {"initiative":{"comum":[1,2], "bom":[2,3], "raro":[3,4],  "epico":[4,6],   "lendario":[6,8]}},
            "luvas":    {"dmg":       {"comum":[1,2], "bom":[2,3], "raro":[3,4],  "epico":[4,6],   "lendario":[6,8]}},
            "colar":    {"hp":        {"comum":[3,6], "bom":[6,9], "raro":[9,12], "epico":[12,16], "lendario":[16,20]}},
            "brinco":   {"hp":        {"comum":[2,4], "bom":[4,6], "raro":[6,9],  "epico":[9,12],  "lendario":[12,14]}},
            "arma":     {"__class_primary__": {"comum":[2,4], "bom":[4,6], "raro":[6,9], "epico":[9,12], "lendario":[12,16]}},
            "anel":     {"luck":      {"comum":[1,1], "bom":[1,2], "raro":[2,3],  "epico":[3,4],   "lendario":[4,5]}},
        },
        "RARITY_DATA": {
            "comum":    {"name":"Comum","emoji":"⚪","tier":1,"bonus_stats":0},
            "bom":      {"name":"Bom","emoji":"🟢","tier":1,"bonus_stats":1},
            "raro":     {"name":"Raro","emoji":"🔵","tier":1,"bonus_stats":2},
            "epico":    {"name":"Épico","emoji":"🟣","tier":1,"bonus_stats":3},
            "lendario": {"name":"Lendário","emoji":"🟡","tier":1,"bonus_stats":4},
        },
    }
)
BASE_STATS_BY_RARITY = _rar["BASE_STATS_BY_RARITY"]
RARITY_DATA = _rar["RARITY_DATA"]

# --- AFFIXES / POOLS ---
_vals_aff = _safe_import(
    "modules.game_data.attributes",
    names={"AFFIX_POOLS": "AFFIX_POOLS", "AFFIXES": "AFFIXES"},
    defaults={"AFFIX_POOLS": {"geral": []}, "AFFIXES": {}}
)
AFFIX_POOLS = _vals_aff["AFFIX_POOLS"]
AFFIXES = _vals_aff["AFFIXES"]

# --- Compatibilidade: segundos ---
try:
    TRAVEL_DEFAULT_SECONDS  # type: ignore[name-defined]
except NameError:
    TRAVEL_DEFAULT_SECONDS = TRAVEL_TIME_MINUTES * 60

__all__ = [
    "TRAVEL_TIME_MINUTES", "COLLECTION_TIME_MINUTES",
    "get_xp_for_next_collection_level", "get_xp_for_next_combat_level",
    "TRAVEL_DEFAULT_SECONDS",
    "ITEMS_DATA", "ITEM_BASES", "MARKET_ITEMS",
    # Novas variáveis de classes
    "CLASSES_DATA", "CLASS_PRIMARY_DAMAGE", "CLASS_DMG_EMOJI",
    "get_primary_damage_profile", "get_stat_modifiers",
    # Resto da lista
    "PREMIUM_TIERS",
    "PROFESSIONS_DATA", "get_profession_for_resource",
    "WORLD_MAP", "REGIONS_DATA", "REGION_TARGET_POWER", "REGION_SCALING_ENABLED",
    "MONSTERS_DATA",
    "REFINING_RECIPES",
    "SLOT_EMOJI", "SLOT_ORDER", "ITEM_SLOTS", "ITEM_DATABASE",
    "item_display_name", "get_item_info",
    "BASE_STATS_BY_RARITY", "RARITY_DATA", "AFFIX_POOLS", "AFFIXES",
    "CLASS_PRIMARY_ATTRIBUTE",
    "CLAN_CONFIG", "CLAN_PRESTIGE_LEVELS" # Adicionado para garantir que é exportado
    "STAT_EMOJI",
    "AFFIX_POOLS", 
    "AFFIXES",
]

from .clans import CLAN_CONFIG, CLAN_PRESTIGE_LEVELS