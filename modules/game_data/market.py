# modules/game_data/market.py

"""
Catálogo do Mercado do Reino: define itens vendáveis, preços e estoque.
- Se "stock" for None -> estoque infinito.
- IDs devem existir em modules/game_data/items.py (ITEMS_DATA) OU
  em modules/game_data/equipment.py (ITEM_DATABASE).
"""

from __future__ import annotations

from .items import ITEMS_DATA
from .equipment import ITEM_DATABASE

# -----------------------------------------------------------------------------
# Tabela do Mercado
# -----------------------------------------------------------------------------
MARKET_ITEMS = {
    # Consumíveis / catalisadores
    "pedra_do_aprimoramento": {"price": 300, "stock": None},   # estoque infinito
    "pergaminho_durabilidade": {"price": 150, "stock": None},

    # Núcleos de forja (progressão PvE)
    "nucleo_forja_fraco": {"price": 500, "stock": None},
    "nucleo_forja_comum": {"price": 1000, "stock": None},
}


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
    Retorna uma lista pronta para o UI do mercado:
    [
      {"id": "pedra_do_aprimoramento", "name": "Pedra do Aprimoramento", "price": 300, "stock": None},
      ...
    ]
    Itens inexistentes são ignorados (após validação dificilmente haverá).
    """
    out: list[dict] = []
    for iid, cfg in MARKET_ITEMS.items():
        if not item_exists(iid):
            # ignora itens inválidos silenciosamente aqui;
            # a validação já vai logar no startup
            continue
        out.append({
            "id": iid,
            "name": get_display_name(iid),
            "price": int(cfg.get("price", 0)),
            "stock": cfg.get("stock", None),
        })
    return out


# -----------------------------------------------------------------------------
# Validação (chame no startup)
# -----------------------------------------------------------------------------
def validate_market_items() -> None:
    """
    Valida todos os IDs de MARKET_ITEMS.
    - Loga/printa erro para IDs inexistentes.
    - Faz warnings para preços inválidos (<= 0).
    """
    any_error = False
    for iid, cfg in MARKET_ITEMS.items():
        if not item_exists(iid):
            print(f"[ERRO][MARKET] Item '{iid}' não existe em items.py nem equipment.py")
            any_error = True
            continue

        # Preço deve ser inteiro positivo
        try:
            price = int(cfg.get("price", 0))
        except Exception:
            price = 0
        if price <= 0:
            print(f"[AVISO][MARKET] Preço inválido para '{iid}': {cfg.get('price')}. Ajuste para > 0.")

        # Stock: None (infinito) ou inteiro >= 0
        stock = cfg.get("stock", None)
        if stock is not None:
            try:
                s = int(stock)
                if s < 0:
                    print(f"[AVISO][MARKET] Stock negativo para '{iid}': {stock}. Use None (infinito) ou >= 0.")
            except Exception:
                print(f"[AVISO][MARKET] Stock inválido para '{iid}': {stock}. Use None (infinito) ou inteiro.")

    if not any_error:
        print("[MARKET] Validação concluída: todos os itens do mercado existem e foram checados.")
