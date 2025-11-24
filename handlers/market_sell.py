from __future__ import annotations
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from modules import player_manager, game_data

# Tenta importar display_utils, se não existir, usa fallback interno
try:
    from modules import display_utils
except Exception:
    display_utils = None

__all__ = ["open_sell_menu"]

# ==============================
#  CONFIG: Itens Bloqueados
# ==============================
EVOLUTION_ITEMS: set[str] = {
    "emblema_guerreiro", "essencia_guardia", "essencia_furia", "selo_sagrado", "essencia_luz",
    "emblema_berserker", "totem_ancestral", "emblema_cacador", "essencia_precisao",
    "marca_predador", "essencia_fera", "emblema_monge", "reliquia_mistica", "essencia_ki",
    "emblema_mago", "essencia_arcana", "essencia_elemental", "grimorio_arcano",
    "emblema_bardo", "essencia_harmonia", "essencia_encanto", "batuta_maestria",
    "emblema_assassino", "essencia_sombra", "essencia_letal", "manto_eterno",
    "emblema_samurai", "essencia_corte", "essencia_disciplina", "lamina_sagrada",
}

# ==============================
#  Helpers de Exibição
# ==============================
RARITY_LABEL = {"comum": "Comum", "bom": "Boa", "raro": "Rara", "epico": "Épica", "lendario": "Lendária"}

def _player_class_key(pdata: dict, fallback: str = "guerreiro") -> str:
    for c in [(pdata.get("class") or pdata.get("classe")), pdata.get("class_type"), pdata.get("classe")]:
        if isinstance(c, str): return c.strip().lower()
        if isinstance(c, dict) and "type" in c: return c["type"].strip().lower()
    return fallback

def _cut_middle(s: str, maxlen: int = 56) -> str:
    s = (s or "").strip()
    return s if len(s) <= maxlen else s[:maxlen//2 - 1] + "… " + s[-maxlen//2:]

def _get_item_info(base_id: str) -> dict:
    try:
        info = game_data.get_item_info(base_id)
        if info: return dict(info)
    except Exception: pass
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

def _render_unique_line_safe(inst: dict, pclass: str) -> str:
    """Renderiza item único (tenta usar display_utils, senão usa fallback)."""
    # 1. Tenta usar o display_utils global do projeto
    if display_utils and hasattr(display_utils, "formatar_item_para_exibicao"):
        try:
            return display_utils.formatar_item_para_exibicao(inst)
        except Exception:
            pass

    # 2. Fallback local (simplificado, mas bonito)
    base_id = inst.get("base_id") or inst.get("tpl") or "item"
    info = _get_item_info(base_id)
    name = inst.get("display_name") or info.get("display_name") or base_id
    emoji = inst.get("emoji") or info.get("emoji") or "⚔️"
    
    tier = inst.get("tier", 1)
    rarity = inst.get("rarity", "comum").lower()
    r_label = RARITY_LABEL.get(rarity, rarity.capitalize())
    
    # Renderiza stats principais se existirem
    stats = []
    ench = inst.get("enchantments") or {}
    if isinstance(ench, dict):
        for k, v in ench.items():
            if isinstance(v, dict) and "value" in v:
                val = v["value"]
                stats.append(f"{k} +{val}")
    
    stats_str = ", ".join(stats[:2]) # Mostra só os 2 primeiros pra não poluir
    stats_display = f": {stats_str}" if stats_str else ""

    return f"{emoji} {name} [T{tier}] [{r_label}]{stats_display}"

# ==============================
#  Menu: Vender Item (Com Paginação)
# ==============================
async def open_sell_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Lista inventário com paginação e filtro de itens proibidos.
    Callback esperado: market_sell ou market_sell:PAGE
    """
    query = update.callback_query
    if query:
        await query.answer()
        user_id = query.from_user.id
        data = query.data
    else:
        # Fallback se for chamado via comando direto (improvável para este menu)
        user_id = update.effective_user.id
        data = "market_sell:1"

    # Define a página atual
    try:
        page = int(data.split(':')[1])
    except (IndexError, ValueError):
        page = 1
    
    ITEMS_PER_PAGE = 8
    pdata = await player_manager.get_player_data(user_id) or {}
    pclass = _player_class_key(pdata)
    inv = pdata.get("inventory", {}) or {}

    # 1. Coletar e Filtrar Itens Vendáveis
    sellable_items = []

    # > Itens Únicos
    for uid, inst in inv.items():
        if isinstance(inst, dict):
            base_id = inst.get("base_id") or inst.get("tpl") or inst.get("id")
            # BLOQUEIO DE EVOLUÇÃO
            if base_id in EVOLUTION_ITEMS:
                continue
            sellable_items.append({"type": "unique", "uid": uid, "inst": inst, "sort_name": base_id})

    # > Stacks
    for base_id, qty in inv.items():
        if isinstance(qty, (int, float)) and int(qty) > 0:
            # BLOQUEIO DE EVOLUÇÃO
            if base_id in EVOLUTION_ITEMS:
                continue
            sellable_items.append({"type": "stack", "base_id": base_id, "qty": int(qty), "sort_name": base_id})

    # Ordena para ficar organizado
    sellable_items.sort(key=lambda x: x["sort_name"])

    # 2. Lógica de Paginação
    total_items = len(sellable_items)
    start_index = (page - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    items_for_page = sellable_items[start_index:end_index]

    caption = f"➕ <b>Vender Item</b> (Página {page})\nSelecione um item para anunciar:\n"
    rows = []

    if not sellable_items:
        caption = "🎒 Seu inventário está vazio ou não possui itens vendáveis."
        rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")])
    elif not items_for_page:
        # Caso a página esteja vazia (ex: vendeu o último item da pág 2)
        caption = "Página vazia. Volte para a anterior."
        rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data=f"market_sell:{max(1, page-1)}")])
    else:
        # 3. Gerar Botões
        for item in items_for_page:
            if item["type"] == "unique":
                full_line = _render_unique_line_safe(item["inst"], pclass)
                cb = f"market_pick_unique_{item['uid']}"
                rows.append([InlineKeyboardButton(_cut_middle(full_line, 56), callback_data=cb)])
            else:
                # Stack
                b_id = item["base_id"]
                info = _get_item_info(b_id)
                name = info.get("display_name") or info.get("nome_exibicao") or b_id
                label = f"📦 {name} (x{item['qty']})"
                cb = f"market_pick_stack_{b_id}"
                rows.append([InlineKeyboardButton(label, callback_data=cb)])

        # Botões de Navegação (Anterior / Próxima)
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"market_sell:{page - 1}"))
        if end_index < total_items:
            nav_row.append(InlineKeyboardButton("Próxima ➡️", callback_data=f"market_sell:{page + 1}"))
        
        if nav_row:
            rows.append(nav_row)
        
        rows.append([InlineKeyboardButton("⬅️ Voltar ao Mercado", callback_data="market_adventurer")])

    # 4. Envio Seguro (Edita se possível, senão envia novo)
    reply_markup = InlineKeyboardMarkup(rows)
    
    if query:
        try:
            await query.edit_message_text(text=caption, reply_markup=reply_markup, parse_mode="HTML")
        except Exception:
            # Se falhar a edição (ex: mensagem muito antiga ou sem mudança), manda nova
            await query.message.reply_text(text=caption, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await update.message.reply_text(text=caption, reply_markup=reply_markup, parse_mode="HTML")