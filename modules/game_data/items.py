# modules/items.py
# Catálogo unificado: tomos são negociáveis por gemas; skins mantêm suas regras próprias.

import logging

# Configuração de log
logger = logging.getLogger(__name__)

print(">>> INICIANDO CARREGAMENTO DE ITENS...")

# ==============================================================================
# 1. IMPORTAÇÕES DOS MÓDULOS DE DADOS
# ==============================================================================
try:
    from modules.game_data.items_materials import MATERIALS_DATA
    print(f"✅ Materiais carregados: {len(MATERIALS_DATA)}")
except ImportError as e:
    print(f"❌ ERRO FATAL em items_materials: {e}")
    raise e

try:
    from modules.game_data.items_consumables import CONSUMABLES_DATA
    print(f"✅ Consumíveis carregados: {len(CONSUMABLES_DATA)}")
except ImportError as e:
    print(f"❌ ERRO FATAL em items_consumables: {e}")
    raise e

try:
    from modules.game_data.items_equipments import EQUIPMENTS_DATA
    print(f"✅ Equipamentos carregados: {len(EQUIPMENTS_DATA)}")
except ImportError as e:
    print(f"❌ ERRO FATAL em items_equipments: {e}")
    raise e

try:
    from modules.game_data.items_evolution import EVOLUTION_ITEMS_DATA
    print(f"✅ Itens Evolução carregados: {len(EVOLUTION_ITEMS_DATA)}")
except ImportError as e:
    print(f"❌ ERRO FATAL em items_evolution: {e}")
    raise e

try:
    from modules.game_data.items_runes import RUNE_ITEMS_DATA
    print(f"✅ Runas carregadas: {len(RUNE_ITEMS_DATA)}")
except ImportError as e:
    print(f"⚠️ Aviso: items_runes não encontrado ou com erro ({e}). Ignorando.")
    RUNE_ITEMS_DATA = {}

try:
    from modules.game_data.items_tools import TOOLS_DATA
    print(f"✅ Ferramentas carregadas: {len(TOOLS_DATA)}")
except ImportError as e:
    print(f"⚠️ Aviso: items_tools não encontrado ({e}). Ignorando.")
    TOOLS_DATA = {}

# ==============================================================================
# 2. FUSÃO DOS DADOS
# ==============================================================================

ITEMS_DATA = {}
MARKET_ITEMS = {} 

for _item_data in EVOLUTION_ITEMS_DATA.values():
    _item_data.setdefault("tradable", True)
    _item_data.setdefault("market_currency", "gems")
    _item_data.setdefault("market_min_price", 30)

for _rune_data in RUNE_ITEMS_DATA.values():
    _rune_data["market_currency"] = "gems"
    _rune_data["market_min_price"] = 30

ITEMS_DATA.update(MATERIALS_DATA)
ITEMS_DATA.update(CONSUMABLES_DATA)
ITEMS_DATA.update(EQUIPMENTS_DATA)
ITEMS_DATA.update(EVOLUTION_ITEMS_DATA)
ITEMS_DATA.update(RUNE_ITEMS_DATA)
ITEMS_DATA.update(TOOLS_DATA)
print(f"📦 TOTAL DE ITENS NO SISTEMA: {len(ITEMS_DATA)}")

# --- 3. ALIAS E HELPERS ---
if "minerio_de_ferro" in ITEMS_DATA:
    ITEMS_DATA["ferro"] = ITEMS_DATA["minerio_de_ferro"]

ITEM_BASES = ITEMS_DATA
ITEMS = ITEMS_DATA

# --- 4. FUNÇÕES DE SUPORTE ---

def get_item(item_id: str):
    return ITEMS_DATA.get(item_id)

def get_item_info(item_id: str):
    return ITEMS_DATA.get(item_id, {})

def is_stackable(item_id: str) -> bool:
    meta = ITEMS_DATA.get(item_id) or {}
    return bool(meta.get("stackable", True))

def get_display_name(item_id: str) -> str:
    if not item_id:
        return "Item Desconhecido"
    meta = ITEMS_DATA.get(item_id)
    if meta and "display_name" in meta:
        return meta["display_name"]
    return item_id.replace("_", " ").title()

# ==============================================================================
# 5. GERAÇÃO AUTOMÁTICA (Skills e Skins)
# ==============================================================================
def _generate_auto_items():
    generated = 0
    
    # --- AUTOMATIZAÇÃO DE TOMOS DE SKILL ---
    try:
        from modules.game_data.skills import SKILL_DATA
        for skill_id, info in SKILL_DATA.items():
            tomo_id = f"tomo_{skill_id}"
            skill_name = info.get('display_name', skill_id)
            
            if tomo_id not in ITEMS_DATA:
                
                # Pega as classes permitidas da skill
                classes = info.get("allowed_classes", [])
                
                # Define emoji visual
                emoji = "📘"
                if "guerreiro" in classes or "berserker" in classes: emoji = "📕"
                elif "cacador" in classes or "assassino" in classes: emoji = "📗"
                elif "monge" in classes or "samurai" in classes: emoji = "📙"

                ITEMS_DATA[tomo_id] = {
                    "display_name": f"Tomo: {skill_name}",
                    "emoji": emoji,
                    "type": "skill_book",
                    "category": "aprendizado", 
                    "description": f"Ensina a habilidade: {skill_name}.",
                    "stackable": True, 
                    
                    "tradable": True,
                    "market_currency": "gems",
                    "market_min_price": 30,
                    "price": 100, 
                    "class_req": classes,
                    "effects": {
                        "learn_skill": skill_id
                    }
                }
                generated += 1
                
            if skill_id not in ITEMS_DATA:
                ITEMS_DATA[skill_id] = ITEMS_DATA[tomo_id].copy()
                ITEMS_DATA[skill_id]["display_name"] += " (Item)"
                
    except ImportError: pass
    except Exception as e: logger.error(f"Auto-Items Skill Error: {e}")

    print(f">>> ITEMS: {generated} itens automáticos gerados.")

_generate_auto_items()

# Marcador interno usado apenas na configuração e seleção de recompensas por classe.
# O fluxo de drop/evento sempre o troca por um tomo real antes de entregar ao jogador.
ITEMS_DATA["tomo_habilidade_classe"] = {
    "display_name": "Tomo de Habilidade da sua Classe",
    "emoji": "📘",
    "type": "event_skill_tome",
    "category": "aprendizado",
    "description": "Recompensa especial: ensina uma habilidade compatível com sua classe.",
    "stackable": True,
    "tradable": False,
    "price": 0,
}

# ==============================================================================
# 6. INDEXAÇÃO DO MERCADO
# ==============================================================================

def _calculate_auto_price(item_data: dict) -> int:
    rarity = str(item_data.get("rarity", "comum")).lower()
    itype = str(item_data.get("type", "misc")).lower()
    
    base = 10
    if itype in ("material", "resource"): base = 5
    elif itype == "consumable": base = 25
    elif itype == "equipamento": base = 100
    elif itype == "rune": base = 150
    elif itype == "skill_book": base = 500
    
    mult = 1
    if rarity == "incomum" or rarity == "bom": mult = 3
    elif rarity == "raro": mult = 10
    elif rarity == "epico": mult = 50
    elif rarity == "lendario": mult = 200
    
    return base * mult

def _rebuild_market_index():
    global MARKET_ITEMS
    count = 0
    for item_id, data in ITEMS_DATA.items():
        # Se for explicitamente False, pula
        if data.get("tradable") is False or data.get("tradeable") is False:
            continue

        price = data.get("value") or data.get("price")
        if not price:
            price = _calculate_auto_price(data)
            data["value"] = price
        
        if int(price) > 0:
            MARKET_ITEMS[item_id] = {
                "price": int(price),
                "currency": data.get("market_currency", "gold"),
                "tradeable": True
            }
            count += 1
    
    print(f">>> MARKET: {count} itens indexados automaticamente no mercado.")

_rebuild_market_index()
