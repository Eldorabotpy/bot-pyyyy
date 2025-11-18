# modules/game_data/market.py

"""
Catálogo do Mercado do Reino: define itens vendáveis, preços e estoque.
- Se "stock" for None -> estoque infinito.
- IDs devem existir em modules/game_data/items.py (ITEMS_DATA) OU
  em modules/game_data/equipment.py (ITEM_DATABASE).
"""

from __future__ import annotations

# Importa os dados e também a lista dinâmica gerada lá (Evolution Gems, etc)
from .items import ITEMS_DATA, MARKET_ITEMS as DYNAMIC_MARKET
from .equipment import ITEM_DATABASE

# -----------------------------------------------------------------------------
# 1. Itens Manuais (Definidos aqui fixos)
# -----------------------------------------------------------------------------
STATIC_MARKET_ITEMS = {
    # Consumíveis / catalisadores
    "pedra_do_aprimoramento": {"price": 300, "stock": None},   # estoque infinito
    "pergaminho_durabilidade": {"price": 150, "stock": None},

    # Núcleos de forja (progressão PvE)
    "nucleo_forja_fraco": {"price": 500, "stock": None},
    "nucleo_forja_comum": {"price": 1000, "stock": None},
    
    # Exemplo de item manual extra se quiser adicionar:
    # "pocao_cura_media": {"price": 50, "stock": None},
}

# -----------------------------------------------------------------------------
# 2. Fusão: Manual + Dinâmico (do items.py)
# -----------------------------------------------------------------------------
MARKET_ITEMS = {}

# Adiciona os estáticos primeiro
MARKET_ITEMS.update(STATIC_MARKET_ITEMS)

# Adiciona os dinâmicos (Emblemas, Essências, Tomos se tiverem preço) vindo do items.py
if DYNAMIC_MARKET:
    # O items.py pode retornar uma lista (sistema antigo) ou dict (sistema novo)
    if isinstance(DYNAMIC_MARKET, dict):
        # Se for dict, faz update direto (respeitando configurações de preço de lá)
        for iid, data in DYNAMIC_MARKET.items():
            # Só adiciona se tiver preço definido e não estiver na lista estática (para não sobrescrever manuais)
            if iid not in MARKET_ITEMS and data.get("price", 0) > 0:
                MARKET_ITEMS[iid] = {
                    "price": data["price"],
                    "stock": None, # Itens do sistema geralmente são estoque infinito
                    "currency": data.get("currency", "gold") # Suporte a gemas se necessário
                }
    elif isinstance(DYNAMIC_MARKET, list):
        # Fallback para sistema antigo (apenas lista de IDs)
        for iid in DYNAMIC_MARKET:
            if iid not in MARKET_ITEMS:
                # Preço padrão caso não definido (fallback)
                MARKET_ITEMS[iid] = {"price": 100, "stock": None}

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def item_exists(item_id: str) -> bool:
    """True se o item existe em ITEMS_DATA (consumíveis/mats) ou ITEM_DATABASE (equipáveis)."""
    return item_id in ITEMS_DATA or item_id in ITEM_DATABASE


def get_display_name(item_id: str) -> str:
    """
    Nome de exibição amigável:
    - Se for item de inventário (ITEMS_DATA): usa 'display_name'
    - Se for equipável (ITEM_DATABASE): usa 'nome_exibicao'
    - Fallback: retorna o próprio item_id
    """
    if item_id in ITEMS_DATA:
        return ITEMS_DATA[item_id].get("display_name", item_id)
    if item_id in ITEM_DATABASE:
        return ITEM_DATABASE[item_id].get("nome_exibicao", item_id)
    return item_id


def get_market_entry(item_id: str) -> dict | None:
    """Retorna o dict do item no mercado (price/stock) ou None."""
    return MARKET_ITEMS.get(item_id)


def list_market_catalog() -> list[dict]:
    """
    Retorna uma lista pronta para o UI do mercado.
    Filtra apenas itens válidos.
    """
    out: list[dict] = []
    for iid, cfg in MARKET_ITEMS.items():
        if not item_exists(iid):
            continue
            
        # Verifica moeda (Gold é padrão, mas items.py pode definir Gems)
        currency = cfg.get("currency", "gold")
        
        out.append({
            "id": iid,
            "name": get_display_name(iid),
            "price": int(cfg.get("price", 0)),
            "stock": cfg.get("stock", None),
            "currency": currency
        })
        
    # Ordena por preço para ficar bonito
    out.sort(key=lambda x: x["price"])
    return out


# -----------------------------------------------------------------------------
# Validação (chame no startup)
# -----------------------------------------------------------------------------
def validate_market_items() -> None:
    """
    Valida todos os IDs de MARKET_ITEMS.
    """
    any_error = False
    print(f"[MARKET] Carregando catálogo... Total de itens: {len(MARKET_ITEMS)}")
    
    for iid, cfg in MARKET_ITEMS.items():
        if not item_exists(iid):
            print(f"[ERRO][MARKET] Item '{iid}' não existe em items.py nem equipment.py")
            any_error = True
            continue

        try:
            price = int(cfg.get("price", 0))
        except Exception:
            price = 0
            
        if price <= 0:
            # Alguns itens podem ser apenas visualização ou troca, warning apenas
            pass 

    if not any_error:
        print("[MARKET] Validação concluída com sucesso.")