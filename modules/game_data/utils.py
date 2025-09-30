# modules/game_data/utils.py
from .items import ITEMS_DATA

SLOT_EMOJI = {
    "elmo": "🪖", "armadura": "👕", "calca": "👖", "luvas": "🧤",
    "botas": "🥾", "colar": "📿", "anel": "💍", "brinco": "🧿", "arma": "⚔️",
}
SLOT_ORDER = ["arma","elmo","armadura","calca","luvas","botas","colar","anel","brinco"]

def get_item_info(base_id: str) -> dict:
    """Retorna info estática conhecida para um item base (fallback simples)."""
    return ITEMS_DATA.get(base_id, {})

def item_display_name(base_id: str) -> str:
    """Nome para exibição (usa ITEMS_DATA como base)."""
    return ITEMS_DATA.get(base_id, {}).get("display_name", base_id)
