# modules/items.py
# (VERSÃO FINAL: Geração Automática de Tomos com a Chave 'effects' Correta)

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
    # Materiais são essenciais, mantemos o raise se falhar
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
    # CORREÇÃO: Não trava o bot se não tiver runas ainda
    print(f"⚠️ Aviso: items_runes não encontrado ou com erro ({e}). Ignorando.")
    RUNE_ITEMS_DATA = {}

# ==============================================================================
# 2. FUSÃO DOS DADOS
# ==============================================================================

# Dicionários Principais
ITEMS_DATA = {}
MARKET_ITEMS = {} 

ITEMS_DATA.update(MATERIALS_DATA)
ITEMS_DATA.update(CONSUMABLES_DATA)
ITEMS_DATA.update(EQUIPMENTS_DATA)
ITEMS_DATA.update(EVOLUTION_ITEMS_DATA)
ITEMS_DATA.update(RUNE_ITEMS_DATA)

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
            
            # Se o item não existe (não foi criado manualmente), cria agora
            if tomo_id not in ITEMS_DATA:
                
                # Define emoji baseado na classe (Visual)
                classes = info.get("allowed_classes", [])
                emoji = "📘"
                if "guerreiro" in classes or "berserker" in classes: emoji = "📕"
                elif "cacador" in classes or "assassino" in classes: emoji = "📗"
                elif "monge" in classes or "samurai" in classes: emoji = "📙"

                ITEMS_DATA[tomo_id] = {
                    "display_name": f"Tomo: {skill_name}",
                    "emoji": emoji,
                    "type": "skill_book",     # Tipo para filtros de inventário
                    "category": "aprendizado", 
                    "description": f"Ensina a habilidade: {skill_name}.",
                    "stackable": True, 
                    "tradable": True, 
                    "market_currency": "gems",
                    "price": 100, 
                    # ✅ CORREÇÃO CRÍTICA AQUI:
                    # Usamos 'effects' em vez de 'on_use' para bater com o sistema de consumo
                    "effects": {
                        "learn_skill": skill_id
                    }
                }
                generated += 1
                
            # Cria um alias reverso se necessário (opcional, para segurança)
            if skill_id not in ITEMS_DATA:
                ITEMS_DATA[skill_id] = ITEMS_DATA[tomo_id].copy()
                ITEMS_DATA[skill_id]["display_name"] += " (Item)"
                
    except ImportError: pass
    except Exception as e: logger.error(f"Auto-Items Skill Error: {e}")

    # --- AUTOMATIZAÇÃO DE CAIXAS DE SKIN ---
    try:
        from modules.game_data.skins import SKIN_CATALOG
        for skin_id, info in SKIN_CATALOG.items():
            caixa_id = f"caixa_{skin_id}"
            skin_name = info.get('display_name', skin_id)
            item_def = {
                "display_name": f"Cx. Skin: {skin_name}",
                "emoji": "👘", 
                "type": "consumable",
                "category": "aprendizado",
                "description": f"Desbloqueia a aparência: {skin_name}.",
                "stackable": True, 
                "tradable": True, 
                "market_currency": "gems",
                "price": 200,
                # Skins geralmente usam logicas diferentes, mas padronizando 'effects' é seguro
                "on_use": {"effect": "grant_skin", "skin_id": skin_id}
            }
            if caixa_id not in ITEMS_DATA:
                ITEMS_DATA[caixa_id] = item_def
                generated += 1
            if skin_id not in ITEMS_DATA:
                ITEMS_DATA[skin_id] = item_def.copy()
                ITEMS_DATA[skin_id]["display_name"] = f"Skin: {skin_name} (Item)"
    except ImportError: pass
    except Exception as e: logger.error(f"Auto-Items Skin Error: {e}")
        
    print(f">>> ITEMS: {generated} itens automáticos gerados.")

# Executa a geração
_generate_auto_items()

# ==============================================================================
# 6. INDEXAÇÃO DO MERCADO (PREÇO AUTOMÁTICO)
# ==============================================================================

def _calculate_auto_price(item_data: dict) -> int:
    """Calcula um preço base se o item não tiver preço definido."""
    rarity = str(item_data.get("rarity", "comum")).lower()
    itype = str(item_data.get("type", "misc")).lower()
    
    # Preço base por tipo
    base = 10
    if itype in ("material", "resource"): base = 5
    elif itype == "consumable": base = 25
    elif itype == "equipamento": base = 100
    elif itype == "rune": base = 150
    elif itype == "skill_book": base = 500 # Valoriza os livros
    
    # Multiplicador por raridade
    mult = 1
    if rarity == "incomum" or rarity == "bom": mult = 3
    elif rarity == "raro": mult = 10
    elif rarity == "epico": mult = 50
    elif rarity == "lendario": mult = 200
    
    return base * mult

def _rebuild_market_index():
    """
    Indexa todos os itens no mercado. Se não tiver preço, gera um automático.
    """
    global MARKET_ITEMS
    count = 0
    for item_id, data in ITEMS_DATA.items():
        # Ignora itens marcados como não trocáveis
        if data.get("tradable") is False or data.get("tradeable") is False:
            continue

        # Verifica se tem preço manual
        price = data.get("value") or data.get("price")
        
        # Se não tiver, calcula automático
        if not price:
            price = _calculate_auto_price(data)
            # Salva no dicionário para uso futuro
            data["value"] = price
        
        # Adiciona ao mercado se tiver preço válido
        if int(price) > 0:
            MARKET_ITEMS[item_id] = {
                "price": int(price),
                "currency": data.get("market_currency", "gold"),
                "tradeable": True
            }
            count += 1
    
    print(f">>> MARKET: {count} itens indexados automaticamente no mercado.")

_rebuild_market_index()