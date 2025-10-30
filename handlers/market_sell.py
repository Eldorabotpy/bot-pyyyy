# handlers/market_sell.py
from __future__ import annotations
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from modules import player_manager, game_data
from modules.item_factory import render_item_line

__all__ = ["open_sell_menu"]

# -----------------------
# Helpers
# -----------------------
def _player_class_key(pdata: dict, fallback: str = "guerreiro") -> str:
    for c in [
        (pdata.get("class") or pdata.get("classe")),
        pdata.get("class_type"), pdata.get("classe_tipo"),
        pdata.get("class_key"), pdata.get("classe"),
    ]:
        if isinstance(c, dict):
            t = c.get("type")
            if isinstance(t, str) and t.strip():
                return t.strip().lower()
        if isinstance(c, str) and c.strip():
            return c.strip().lower()
    return fallback

def _cut_middle(s: str, maxlen: int = 56) -> str:
    """Corta no meio para caber no botão sem perder começo/fim."""
    s = (s or "").strip()
    return s if len(s) <= maxlen else s[:maxlen//2 - 1] + "… " + s[-maxlen//2:]

def _get_item_info(base_id: str) -> dict:
    """Busca metadados compatíveis (novo game_data ou ITEMS_DATA legado)."""
    try:
        info = game_data.get_item_info(base_id)
        if info:
            return dict(info)
    except Exception:
        pass
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

def _stack_inv_display(base_id: str, qty: int) -> str:
    """Linha estilo inventário para stacks (emoji + nome ×qty)."""
    info = _get_item_info(base_id)
    name = info.get("display_name") or info.get("nome_exibicao") or base_id
    emoji = info.get("emoji", "")
    return f"{emoji}{name} ×{qty}" if emoji else f"{name} ×{qty}"

# -----------------------
# Menu: vender item
# -----------------------
async def open_sell_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Abre o menu de seleção de itens para venda.
    - Itens únicos: render com render_item_line (mesma linha do inventário).
    - Stacks: emoji + nome ×quantidade.
    - Gera callback_data compatível: market_pick_unique_{uid} / market_pick_stack_{base_id}
    """
    user_id = update.effective_user.id
    pdata = await player_manager.get_player_data(user_id) or {}
    pclass = _player_class_key(pdata)

    inv = pdata.get("inventory", {}) or {}
    lines = ["➕ Vender Item\nSelecione um item do seu inventário:\n"]
    rows: list[list[InlineKeyboardButton]] = []

    # ► Itens ÚNICOS
    for uid, inst in inv.items():
        if not isinstance(inst, dict):
            continue
        try:
            full_line = render_item_line(inst, pclass)  # 『[20/20] ⚔️Espada …』
        except Exception:
            # fallback muito simples
            base_id = inst.get("base_id") or inst.get("tpl") or inst.get("id") or "Item"
            name = game_data.ITEM_BASES.get(base_id, {}).get("display_name") or \
                   game_data.ITEMS_DATA.get(base_id, {}).get("display_name", base_id)
            full_line = f"{name} (único)"

        lines.append(f"• {full_line}")
        rows.append([InlineKeyboardButton(_cut_middle(full_line, 56),
                                          callback_data=f"market_pick_unique_{uid}")])

    # ► Itens EMPILHÁVEIS
    for base_id, qty in inv.items():
        if isinstance(qty, (int, float)) and int(qty) > 0:
            label = _stack_inv_display(base_id, int(qty))
            lines.append(f"• {label}")
            # no botão, mantemos compacto e claro
            disp_name = _get_item_info(base_id).get("display_name", base_id)
            rows.append([InlineKeyboardButton(f"📦 {disp_name} ({int(qty)}x)",
                                              callback_data=f"market_pick_stack_{base_id}")])

    if not rows:
        await update.effective_message.reply_text(
            "Você não tem itens à venda.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]])
        )
        return

    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")])

    await update.effective_message.reply_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(rows),
        parse_mode=None  # sem HTML; a linha já é autoexplicativa
    )
# Renderização igual ao inventário/forja
try:
    from modules import display_utils  # tem formatar_item_para_exibicao(item: dict) -> str
except Exception:
    display_utils = None  # usamos fallback local quando None
