# modules/crafting_registry.py
# ===================================================
# Registro central de receitas de forja/refino
# ===================================================

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Registry em memória
# -------------------------------------------------------------------
_RECIPES: Dict[str, Dict[str, Any]] = {}

# -------------------------------------------------------------------
# Suporte a raridades (com normalização)
# -------------------------------------------------------------------
RARITY_ORDER = ("comum", "bom", "raro", "epico", "lendario")

# Defaults (ajuste livremente se quiser outros números)
DEFAULT_RARITY_T1 = {
    "comum": 0.78,
    "bom": 0.20,
    "raro": 0.02,
    "epico": 0.00,
    "lendario": 0.00,
}
DEFAULT_RARITY_T2 = {
    "comum": 0.74,
    "bom": 0.23,
    "raro": 0.02,
    "epico": 0.01,
    "lendario": 0.00,
}

def _guess_tier_from_level(level_req: int | None) -> int:
    """Heurística simples: <= 12 -> T1, senão T2."""
    if level_req is None:
        return 1
    return 1 if level_req <= 12 else 2

def _ensure_rarity_block(rarity: dict | None, *, tier: int) -> dict:
    """
    Garante as 5 chaves (comum/bom/raro/epico/lendario) e normaliza para somar 1.0.
    Se nada vier, aplica o default por tier.
    """
    base = DEFAULT_RARITY_T1 if tier == 1 else DEFAULT_RARITY_T2
    data = dict(base if not isinstance(rarity, dict) else rarity)

    # garante chaves e remove negativos
    for k in RARITY_ORDER:
        data[k] = float(max(0.0, data.get(k, 0.0)))

    total = sum(data.values())
    if total <= 0.0:
        data = dict(base)
        total = sum(data.values())

    # normaliza
    data = {k: (v / total) for k, v in data.items()}
    return data

# -------------------------------------------------------------------
# API
# -------------------------------------------------------------------
def register_recipe(recipe_id: str, recipe_data: Dict[str, Any]) -> None:
    """Registra ou sobrescreve uma receita no registry."""
    if not recipe_id or not isinstance(recipe_data, dict):
        logger.warning("[crafting_registry] register_recipe ignorado: parâmetros inválidos.")
        return

    data = dict(recipe_data)

    # normalização de raridades
    tier = _guess_tier_from_level(data.get("level_req"))
    data["rarity_chances"] = _ensure_rarity_block(data.get("rarity_chances"), tier=tier)

    _RECIPES[recipe_id] = data
    logger.debug(f"[crafting_registry] Receita registrada: {recipe_id}")

def get_recipe(recipe_id: str) -> Dict[str, Any] | None:
    """Retorna os dados de uma receita pelo ID."""
    return _RECIPES.get(recipe_id)

def all_recipes() -> Dict[str, Dict[str, Any]]:
    """Retorna todas as receitas registradas (cópia rasa)."""
    return dict(_RECIPES)

# -------------------------------------------------------------------
# Receitas embutidas (exemplo mínimo)
# -------------------------------------------------------------------
CRAFTING_RECIPES: Dict[str, Dict[str, Any]] = {
    "work_espada_ferro_guerreiro": {
        "display_name": "Espada de Ferro do Guerreiro",
        "emoji": "🗡️",
        "profession": "armeiro",
        "level_req": 5,
        "time_seconds": 480,
        "xp_gain": 25,
        # 🔧 CORRIGIDO: 'barra_ferro' -> 'barra_de_ferro' (igual ao inventário dos jogadores)
        "inputs": {"barra_de_ferro": 8, "couro_curtido": 2, "nucleo_forja_fraco": 1},
        "result_base_id": "espada_ferro_guerreiro",
        "unique": True,
        "class_req": ["guerreiro"],
        # Pode omitir ou definir incompleto; a normalização garante as 5 chaves e soma 1.0
        "rarity_chances": {
            "comum": 0.80,
            "bom": 0.18,
            "raro": 0.02
            # epico/lendario serão incluídos como 0.0 e tudo será normalizado
        },
        "affix_pools_to_use": ["guerreiro", "geral"],
        "damage_info": {"type": "cortante", "min_damage": 12, "max_damage": 18},
    },
}

# Adicione esta função ao seu ficheiro modules/crafting_registry.py

def get_recipe_by_item_id(item_base_id: str) -> Dict[str, Any] | None:
    """Procura e retorna a receita que produz um item com um determinado base_id."""
    for recipe_data in _RECIPES.values():
        if recipe_data.get("result_base_id") == item_base_id:
            return recipe_data
    return None

def load_builtin_recipes() -> None:
    """Carrega as receitas definidas em CRAFTING_RECIPES para o registry central."""
    for rid, data in CRAFTING_RECIPES.items():
        register_recipe(rid, data)
    logger.info("[crafting_registry] %d receitas embutidas carregadas.", len(CRAFTING_RECIPES))

# Carrega automaticamente as receitas embutidas ao importar o módulo
load_builtin_recipes()
