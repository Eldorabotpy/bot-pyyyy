import logging

# Configuração de log
logger = logging.getLogger(__name__)

print(">>> INICIANDO CARREGAMENTO DE ITENS...")

# --- 1. IMPORTAÇÕES DOS MÓDULOS DE DADOS (SEM BLINDAGEM) ---
# Removemos o try/except. Se o arquivo tiver erro, o jogo DEVE parar e avisar.
# Isso corrige o problema de "itens sumindo" silenciosamente.

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
    print(f"❌ ERRO FATAL em items_runes: {e}")
    raise e

# -------------------------------------------------------

# Dicionários Principais
ITEMS_DATA = {}
MARKET_ITEMS = {} 

# --- 2. FUSÃO DOS DADOS (O Grande "Update") ---
# Aqui juntamos todos os arquivos menores no dicionário mestre.
ITEMS_DATA.update(MATERIALS_DATA)
ITEMS_DATA.update(CONSUMABLES_DATA)
ITEMS_DATA.update(EQUIPMENTS_DATA)
ITEMS_DATA.update(EVOLUTION_ITEMS_DATA)
ITEMS_DATA.update(RUNE_ITEMS_DATA)

print(f"📦 TOTAL DE ITENS NO SISTEMA: {len(ITEMS_DATA)}")

# --- 3. ALIAS E HELPERS (Compatibilidade) ---
# Para garantir que códigos antigos que buscam "ferro" em vez de "minerio_de_ferro" funcionem
if "minerio_de_ferro" in ITEMS_DATA:
    ITEMS_DATA["ferro"] = ITEMS_DATA["minerio_de_ferro"]

# Apelidos globais para outros módulos usarem
ITEM_BASES = ITEMS_DATA
ITEMS = ITEMS_DATA

# --- 4. FUNÇÕES DE SUPORTE (Getters) ---

def get_item(item_id: str):
    """Retorna os dados do item ou None."""
    return ITEMS_DATA.get(item_id)

def get_item_info(item_id: str):
    """Retorna os dados do item ou dict vazio (seguro)."""
    return ITEMS_DATA.get(item_id, {})

def is_stackable(item_id: str) -> bool:
    """Verifica se o item pode ser empilhado."""
    meta = ITEMS_DATA.get(item_id) or {}
    return bool(meta.get("stackable", True))

def get_display_name(item_id: str) -> str:
    """
    Retorna o nome bonito do item.
    Se não achar, transforma 'pano_simples' em 'Pano Simples'.
    """
    if not item_id:
        return "Item Desconhecido"
        
    # Tenta pegar do dicionário mestre
    meta = ITEMS_DATA.get(item_id)
    
    # Se achou e tem display_name, retorna ele
    if meta and "display_name" in meta:
        return meta["display_name"]
    
    # Se não achou, formata o ID para ficar legível (Fallback)
    return item_id.replace("_", " ").title()

def _register_item_safe(item_id: str, data: dict, market_price: int | None = None):
    """
    Função utilitária para registrar itens dinamicamente (ex: em scripts).
    """
    global ITEMS_DATA, MARKET_ITEMS
    
    if item_id not in ITEMS_DATA:
        ITEMS_DATA[item_id] = data

    # Se tiver preço, adiciona ao mercado
    if market_price is not None:
        if isinstance(MARKET_ITEMS, dict):
            MARKET_ITEMS[item_id] = {
                "price": int(market_price), 
                "currency": data.get("market_currency", "gold"), 
                "tradeable": bool(data.get("tradable", True))
            }

# --- 5. GERAÇÃO AUTOMÁTICA (Skills e Skins) ---
def _generate_auto_items():
    """
    Lê Skills e Skins e cria os itens 'Tomo' e 'Caixa' automaticamente.
    Importante: Fazemos o import DENTRO da função para evitar Ciclo de Importação.
    """
    generated = 0
    
    # A. GERAÇÃO DE TOMOS DE SKILL
    try:
        # Import local para evitar erro circular (items -> skills -> items)
        # Se der erro aqui, queremos ver no console
        from modules.game_data.skills import SKILL_DATA
        
        for skill_id, info in SKILL_DATA.items():
            tomo_id = f"tomo_{skill_id}"
            skill_name = info.get('display_name', skill_id)
            
            # Cria o Tomo se não existir manualmente
            if tomo_id not in ITEMS_DATA:
                ITEMS_DATA[tomo_id] = {
                    "display_name": f"Tomo: {skill_name}",
                    "emoji": "📚",
                    "type": "consumable",
                    "category": "aprendizado", 
                    "description": f"Ensina a habilidade: {skill_name}.",
                    "stackable": True, 
                    "tradable": True, 
                    "market_currency": "gems",
                    # AQUI ESTÁ A MÁGICA PARA O INVENTORY_HANDLER:
                    "on_use": {
                        "effect": "grant_skill", 
                        "skill_id": skill_id
                    }
                }
                generated += 1
            
            # Legado: Item com ID da skill (caso o jogador tenha itens antigos)
            if skill_id not in ITEMS_DATA:
                ITEMS_DATA[skill_id] = ITEMS_DATA[tomo_id].copy()
                ITEMS_DATA[skill_id]["display_name"] += " (Item)"

    except ImportError:
        # Se skills.py não existir ou tiver erro, apenas avisamos, não crashamos tudo
        print("⚠️ Aviso: SKILL_DATA não encontrado. Tomos não gerados.")
    except Exception as e:
        logger.error(f"Auto-Items Skill Error: {e}")

    # B. GERAÇÃO DE CAIXAS DE SKIN
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
                "on_use": {
                    "effect": "grant_skin", 
                    "skin_id": skin_id
                }
            }

            if caixa_id not in ITEMS_DATA:
                ITEMS_DATA[caixa_id] = item_def
                generated += 1
            
            # Legado
            if skin_id not in ITEMS_DATA:
                ITEMS_DATA[skin_id] = item_def.copy()
                ITEMS_DATA[skin_id]["display_name"] = f"Skin: {skin_name} (Item)"

    except ImportError:
         print("⚠️ Aviso: SKIN_CATALOG não encontrado. Caixas de Skin não geradas.")
    except Exception as e:
        logger.error(f"Auto-Items Skin Error: {e}")
        
    print(f">>> ITEMS: {generated} itens automáticos (Skills/Skins) gerados.")

# Executa geração dinâmica
_generate_auto_items()

# --- 6. INDEXAÇÃO DO MERCADO ---
def _rebuild_market_index():
    """
    Varre todos os itens carregados. Se tiverem 'value' ou 'price',
    adiciona automaticamente ao dicionário MARKET_ITEMS.
    """
    global MARKET_ITEMS
    count = 0
    for item_id, data in ITEMS_DATA.items():
        # Verifica se tem preço definido no dado do item
        price = data.get("value") or data.get("price")
        
        # Só adiciona se tiver preço e não estiver no mercado ainda
        if price and int(price) > 0:
            if item_id not in MARKET_ITEMS:
                MARKET_ITEMS[item_id] = {
                    "price": int(price),
                    "currency": data.get("market_currency", "gold"),
                    "tradeable": bool(data.get("tradable", True))
                }
                count += 1
    
    print(f">>> MARKET: {count} itens indexados automaticamente no mercado.")

# Executa indexação final
_rebuild_market_index()