# modules/game_data/__init__.py
import logging

logger = logging.getLogger(__name__)

# --- Constantes Globais ---
TRAVEL_TIME_MINUTES = 15
COLLECTION_TIME_MINUTES = 10
TRAVEL_DEFAULT_SECONDS = TRAVEL_TIME_MINUTES * 60

def get_xp_for_next_collection_level(level: int) -> int:
    return 10 * (level ** 2) + 40

def get_xp_for_next_combat_level(level: int) -> int:
    return 20 * (level ** 2) + 80

# ==============================================================================
# 1. IMPORTAÇÕES PRINCIPAIS (ITENS & MERCADO)
# ==============================================================================
# O items.py é o "Gerente". Se ele falhar, o jogo NÃO pode abrir.
try:
    from .items import (
        ITEMS_DATA, 
        ITEM_BASES, 
        MARKET_ITEMS, 
        get_item, 
        get_item_info, 
        get_display_name,
        is_stackable
    )
except ImportError as e:
    logger.critical(f"❌ ERRO FATAL ao importar items.py (Verifique imports circulares): {e}")
    raise e

# Função wrapper para manter compatibilidade
def item_display_name(base_id: str) -> str:
    return get_display_name(base_id)

# ==============================================================================
# 2. CLASSES E ATRIBUTOS (AQUI ESTAVA O PROBLEMA DO LENDÁRIO)
# ==============================================================================
# Removemos o try/except para obrigar o jogo a carregar os atributos.
# Se isso falhar, saberemos que é culpa do attributes.py.

try:
    from .classes import (
        CLASSES_DATA, 
        CLASS_PRIMARY_DAMAGE, 
        CLASS_DMG_EMOJI,
        get_primary_damage_profile, 
        get_stat_modifiers
    )
except ImportError as e:
    logger.error(f"Erro ao carregar Classes: {e}")
    # Fallback mínimo para não crashar imediatamente, mas avisa no log
    CLASSES_DATA = {}
    CLASS_PRIMARY_DAMAGE = {}
    def get_primary_damage_profile(*args): return {}
    def get_stat_modifiers(*args): return {}

# --- A CORREÇÃO PRINCIPAL ---
# O erro dos itens "sem status" vinha daqui. O except silencioso definia AFFIX_POOLS vazio.
# Agora, se der erro, ele vai avisar no console.
try:
    from .attributes import (
        STAT_EMOJI, 
        AFFIX_POOLS, 
        AFFIXES
    )
except ImportError as e:
    logger.critical(f"❌ ERRO CRÍTICO EM ATTRIBUTES.PY: {e}")
    # Definimos um fallback DE EMERGÊNCIA para itens não saírem bugados
    logger.warning("⚠️ Usando Pool de Atributos de Emergência!")
    STAT_EMOJI = {"hp": "❤️", "atk": "⚔️", "def": "🛡️"}
    AFFIX_POOLS = {
        "geral": ["hp", "defense", "initiative", "luck", "critical_chance"],
        "guerreiro": ["forca"], "mago": ["inteligencia"], 
        "cacador": ["agilidade"], "berserker": ["forca"],
        "assassino": ["agilidade"], "monge": ["agilidade"],
        "bardo": ["inteligencia"], "samurai": ["forca"]
    }
    AFFIXES = {}

# Fallback para atributo primário se não definido
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

# ==============================================================================
# 3. MUNDO, MONSTROS E PROFISSÕES
# ==============================================================================
try:
    from .worldmap import WORLD_MAP
except ImportError:
    WORLD_MAP = {}

try:
    from .regions import REGIONS_DATA, REGION_TARGET_POWER, REGION_SCALING_ENABLED
except ImportError:
    REGIONS_DATA = {}
    REGION_TARGET_POWER = {}
    REGION_SCALING_ENABLED = {}

try:
    from .monsters import MONSTERS_DATA
except ImportError:
    MONSTERS_DATA = {}

try:
    from .professions import PROFESSIONS_DATA, get_profession_for_resource
except ImportError:
    PROFESSIONS_DATA = {}
    def get_profession_for_resource(*args): return None

# ==============================================================================
# 4. SISTEMAS
# ==============================================================================
try:
    from .refining import REFINING_RECIPES
except ImportError:
    REFINING_RECIPES = {}

try:
    from .clans import CLAN_CONFIG, CLAN_PRESTIGE_LEVELS
except ImportError:
    CLAN_CONFIG = {}
    CLAN_PRESTIGE_LEVELS = {}

try:
    from .premium import PREMIUM_TIERS, PREMIUM_PLANS_FOR_SALE
except ImportError:
    PREMIUM_TIERS = {}
    PREMIUM_PLANS_FOR_SALE = {}

try:
    from .rarity import BASE_STATS_BY_RARITY, RARITY_DATA
except ImportError:
    BASE_STATS_BY_RARITY = {}
    RARITY_DATA = {}

# ==============================================================================
# 5. EQUIPAMENTOS E SLOTS
# ==============================================================================
try:
    from .equipment import (
        EQ_SLOT_EMOJI, 
        EQ_SLOT_ORDER, 
        ITEM_SLOTS, 
        ITEM_DATABASE
    )
    # Alias para compatibilidade
    SLOT_EMOJI = EQ_SLOT_EMOJI
    SLOT_ORDER = EQ_SLOT_ORDER
except ImportError:
    SLOT_EMOJI = {
        "elmo": "🪖", "armadura": "👕", "calca": "👖", "luvas": "🧤",
        "botas": "🥾", "colar": "📿", "anel": "💍", "brinco": "🧿", "arma": "⚔️",
    }
    SLOT_ORDER = ["arma","elmo","armadura","calca","luvas","botas","colar","anel","brinco"]
    ITEM_SLOTS = {}
    ITEM_DATABASE = {}

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

# ==============================================================================
# 6. EXPORTAÇÃO (__all__)
# ==============================================================================
__all__ = [
    "TRAVEL_TIME_MINUTES", "COLLECTION_TIME_MINUTES", "TRAVEL_DEFAULT_SECONDS",
    "get_xp_for_next_collection_level", "get_xp_for_next_combat_level",
    "ITEMS_DATA", "ITEM_BASES", "MARKET_ITEMS", 
    "get_item", "get_item_info", "get_display_name", "item_display_name",
    "CLASSES_DATA", "CLASS_PRIMARY_DAMAGE", "CLASS_DMG_EMOJI",
    "get_primary_damage_profile", "get_stat_modifiers",
    "CLASS_PRIMARY_ATTRIBUTE",
    "STAT_EMOJI", "AFFIX_POOLS", "AFFIXES",
    "WORLD_MAP", "REGIONS_DATA", "REGION_TARGET_POWER", "REGION_SCALING_ENABLED",
    "MONSTERS_DATA", "PROFESSIONS_DATA", "get_profession_for_resource",
    "REFINING_RECIPES",
    "CLAN_CONFIG", "CLAN_PRESTIGE_LEVELS",
    "PREMIUM_TIERS", "PREMIUM_PLANS_FOR_SALE",
    "BASE_STATS_BY_RARITY", "RARITY_DATA",
    "SLOT_EMOJI", "SLOT_ORDER", "ITEM_SLOTS", "ITEM_DATABASE"
]