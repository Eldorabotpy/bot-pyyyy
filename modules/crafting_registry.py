# modules/crafting_registry.py
# ===================================================
# Registro central de receitas de forja/refino
# ===================================================

import logging
import pkgutil
import importlib
from typing import Dict, Any, List

# Importamos o pacote de receitas para que o código possa encontrá-lo
from modules import recipes as recipes_package

logger = logging.getLogger(__name__)

_RECIPES: Dict[str, Dict[str, Any]] = {} 

# ... (Toda a sua lógica de raridade pode continuar aqui, ela está correta)
RARITY_ORDER = ("comum", "bom", "raro", "epico", "lendario")
DEFAULT_RARITY_T1 = {
    "comum": 0.90,      # 90%
    "bom": 0.09,        # 9%
    "raro": 0.009,      # 0.9%
    "epico": 0.0009,    # 0.09%
    "lendario": 0.0001  # 0.01%
}
DEFAULT_RARITY_T2 = {
    "comum": 0.90,
    "bom": 0.09,
    "raro": 0.009,
    "epico": 0.0009,
    "lendario": 0.0001
}

def _guess_tier_from_level(level_req: int | None) -> int:
    if level_req is None: return 1
    return 1 if level_req <= 12 else 2

def _ensure_rarity_block(rarity: dict | None, *, tier: int) -> dict:
    base = DEFAULT_RARITY_T1 if tier == 1 else DEFAULT_RARITY_T2
    data = dict(base if not isinstance(rarity, dict) else rarity)
    for k in RARITY_ORDER: data[k] = float(max(0.0, data.get(k, 0.0)))
    total = sum(data.values())
    if total <= 0.0:
        data = dict(base)
        total = sum(data.values())
    return {k: (v / total) for k, v in data.items()}

# =====================================================
# API do Registro (Funções que gerenciam as receitas)
# =====================================================

def register_recipe(recipe_id: str, recipe_data: Dict[str, Any]) -> None:
    """Registra ou sobrescreve uma receita, normalizando os dados necessários."""
    if not recipe_id or not isinstance(recipe_data, dict):
        logger.warning("[crafting_registry] Tentativa de registrar receita inválida ignorada.")
        return

    data = dict(recipe_data)
    tier = _guess_tier_from_level(data.get("level_req"))
    data["rarity_chances"] = _ensure_rarity_block(data.get("rarity_chances"), tier=tier)
    
    _RECIPES[recipe_id] = data
    logger.debug(f"[crafting_registry] Receita registrada: {recipe_id}")

def get_recipe(recipe_id: str) -> Dict[str, Any] | None:
    """Retorna os dados de uma receita pelo ID."""
    return _RECIPES.get(recipe_id)

def all_recipes() -> Dict[str, Dict[str, Any]]:
    """Retorna um dicionário com todas as receitas registradas."""
    return dict(_RECIPES)

def get_recipe_by_item_id(item_base_id: str) -> Dict[str, Any] | None:
    """Procura e retorna a receita que produz um item com um determinado base_id."""
    for recipe_data in _RECIPES.values():
        if recipe_data.get("result_base_id") == item_base_id:
            return recipe_data
    return None

# =====================================================
# <<< NOVO BLOCO: CARREGADOR AUTOMÁTICO DE RECEITAS >>>
# =====================================================

def load_recipes_from_package(package) -> int:
    """
    Descobre e carrega automaticamente todas as receitas de arquivos .py
    dentro de um pacote (uma pasta com um __init__.py).
    
    Procura por um dicionário chamado 'RECIPES' em cada arquivo.
    """
    count = 0
    logger.info(f"Procurando por receitas na pasta '{package.__name__}'...")
    
    # Itera sobre todos os módulos dentro da pasta 'recipes'
    for _, module_name, _ in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
        try:
            # Importa o módulo (o arquivo .py)
            module = importlib.import_module(module_name)
            
            # Procura pelo dicionário 'RECIPES' dentro do arquivo
            recipes_dict = getattr(module, 'RECIPES', None)
            
            if isinstance(recipes_dict, dict):
                logger.info(f"  -> Encontradas {len(recipes_dict)} receitas em '{module_name}'")
                for recipe_id, recipe_data in recipes_dict.items():
                    register_recipe(recipe_id, recipe_data)
                    count += 1
            else:
                logger.warning(f"  -> Arquivo '{module_name}' não contém um dicionário 'RECIPES'.")

        except Exception as e:
            logger.exception(f"Erro ao carregar receitas do arquivo '{module_name}': {e}")
            
    return count

# =====================================================
# Inicialização do Registro
# =====================================================

def _initialize_registry():
    """Função central que carrega todas as receitas quando o bot inicia."""
    
    # Limpa o registro para evitar duplicações se o bot for recarregado
    _RECIPES.clear()
    
    # Carrega as receitas da pasta modules/recipes/
    loaded_count = load_recipes_from_package(recipes_package)
    
    logger.info(f"[crafting_registry] Carregamento finalizado. Total de {loaded_count} receitas registradas dinamicamente.")

# Executa a inicialização assim que este arquivo é importado pela primeira vez.
_initialize_registry()