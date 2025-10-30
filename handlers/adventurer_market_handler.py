# handlers/adventurer_market_handler.py

import logging
from typing import List, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules import mission_manager, player_manager, game_data, file_id_manager, market_manager, clan_manager
from modules.market_manager import render_listing_line as _mm_render_listing_line

# --- DISPLAY UTILS opcional (fallback consistente) ---
try:
    from modules import display_utils  # deve ter: formatar_item_para_exibicao(dict) -> str
except Exception:
    class _DisplayFallback:
        @staticmethod
        def formatar_item_para_exibicao(item_criado: dict) -> str:
            emoji = item_criado.get("emoji", "🛠")
            name = item_criado.get("display_name", item_criado.get("name", "Item"))
            rarity = item_criado.get("rarity", "")
            if rarity:
                name = f"{name} [{rarity}]"
            return f"{emoji} {name}"
    display_utils = _DisplayFallback()

logger = logging.getLogger(__name__)

# ==============================
#  BLOQUEIO: Itens de evolução de classe
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

EVOL_BLOCK_MSG = (
    "🚫 Este é um <b>item de evolução de classe</b> e não pode ser vendido no "
    "<b>Mercado do Aventureiro</b> por ouro.\n"
    "Use a <b>Loja de Gemas</b> (moeda premium) para negociar esse tipo de item."
)

# ==============================
#  Utils básicos
# ==============================
def _gold(pdata: dict) -> int:
    return int(pdata.get("gold", 0))

def _set_gold(pdata: dict, value: int):
    pdata["gold"] = max(0, int(value))

def _item_label_from_base(base_id: str) -> str:
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}).get("display_name", base_id)

def _get_item_info(base_id: str) -> dict:
    try:
        info = game_data.get_item_info(base_id)
        if info:
            return dict(info)
    except Exception:
        pass
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

def _player_class_key(pdata: dict, fallback="guerreiro") -> str:
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
    s = (s or "").strip()
    return s if len(s) <= maxlen else s[:maxlen//2 - 1] + "… " + s[-maxlen//2:]

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except Exception:
        pass
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except Exception:
        pass
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

async def _send_with_media(chat_id: int, context: ContextTypes.DEFAULT_TYPE, caption: str, kb: InlineKeyboardMarkup, media_keys: List[str]):
    for key in media_keys:
        fd = file_id_manager.get_file_data(key)
        if fd and fd.get("id"):
            fid, ftype = fd["id"], fd.get("type")
            try:
                if ftype == "video":
                    await context.bot.send_video(chat_id=chat_id, video=fid, caption=caption, reply_markup=kb, parse_mode="HTML")
                else:
                    await context.bot.send_photo(chat_id=chat_id, photo=fid, caption=caption, reply_markup=kb, parse_mode="HTML")
                return
            except Exception:
                continue
    await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=kb, parse_mode="HTML")

# ==============================
#  Emojis/rotulagem (usa mapa oficial + fallback)
# ==============================
RARITY_LABEL: Dict[str, str] = {
    "comum": "Comum", "bom": "Boa", "raro": "Rara",
    "epico": "Épica", "lendario": "Lendária",
}

_CLASS_DMG_EMOJI_FALLBACK = {
    "guerreiro": "⚔️", "berserker": "🪓", "cacador": "🏹", "caçador": "🏹",
    "assassino": "🗡", "bardo": "🎵", "monge": "🙏", "mago": "✨", "samurai": "🗡",
}
_STAT_EMOJI_FALLBACK = {
    "dmg": "🗡", "hp": "❤️‍🩹", "vida": "❤️‍🩹", "defense": "🛡️", "defesa": "🛡️",
    "initiative": "🏃", "agilidade": "🏃", "luck": "🍀", "sorte": "🍀",
    "forca": "💪", "força": "💪", "foco": "🧘", "carisma": "😎", "bushido": "🥷",
    "inteligencia": "🧠", "inteligência": "🧠", "precisao": "🎯", "precisão": "🎯",
    "letalidade": "☠️", "furia": "🔥", "fúria": "🔥",
}

def _class_dmg_emoji(pclass: str) -> str:
    try:
        return getattr(game_data, "CLASS_DMG_EMOJI", {}).get((pclass or "").lower(), _CLASS_DMG_EMOJI_FALLBACK.get((pclass or "").lower(), "🗡"))
    except Exception:
        return _CLASS_DMG_EMOJI_FALLBACK.get((pclass or "").lower(), "🗡")

def _stat_emoji(stat: str, pclass: str) -> str:
    s = (stat or "").lower()
    try:
        attr_mod = getattr(game_data, "attributes", None)
        if attr_mod and hasattr(attr_mod, "ATTRIBUTE_ICONS"):
            em = attr_mod.ATTRIBUTE_ICONS.get(s)
            if em:
                return _class_dmg_emoji(pclass) if s == "dmg" else em
    except Exception:
        pass
    if s == "dmg":
        return _class_dmg_emoji(pclass)
    return _STAT_EMOJI_FALLBACK.get(s, "❔")

def _stack_inv_display(base_id: str, qty: int) -> str:
    info = _get_item_info(base_id)
    name = info.get("display_name") or info.get("nome_exibicao") or base_id
    emoji = info.get("emoji", "")
    return f"{emoji}{name} ×{qty}" if emoji else f"{name} ×{qty}"

def _render_unique_line_safe(inst: dict, pclass: str) -> str:
    try:
        return display_utils.formatar_item_para_exibicao(inst)
    except Exception:
        pass

    base_id = inst.get("base_id") or inst.get("tpl") or inst.get("id") or "item"
    info = _get_item_info(base_id)
    name = inst.get("display_name") or info.get("display_name") or info.get("nome_exibicao") or base_id
    item_emoji = inst.get("emoji") or info.get("emoji") or _class_dmg_emoji(pclass)
    try:
        cur_d, max_d = inst.get("durability", [20, 20]); cur_d, max_d = int(cur_d), int(max_d)
    except Exception:
        cur_d, max_d = 20, 20
    try:
        tier = int(inst.get("tier", 1))
    except Exception:
        tier = 1
    rarity = str(inst.get("rarity", "comum")).lower()
    rarity_label = RARITY_LABEL.get(rarity, rarity.capitalize())
    ench = inst.get("enchantments") or {}
    parts = []
    primary_key, primary_val = None, 0
    if isinstance(ench, dict):
        for k, v in ench.items():
            if k == "dmg" or not isinstance(v, dict): continue
            if str(v.get("source", "")).startswith("primary"):
                primary_key = k
                try: primary_val = int(v.get("value", 0) or 0)
                except Exception: primary_val = 0
                break
        if primary_key is None:
            best = None
            for k, v in ench.items():
                if k == "dmg" or not isinstance(v, dict): continue
                try: val = int(v.get("value", 0) or 0)
                except Exception: val = 0
                if best is None or val > best[1]: best = (k, val)
            if best: primary_key, primary_val = best
    if primary_key:
        parts.append(f"{_stat_emoji(primary_key, pclass)}+{int(primary_val)}")
    if isinstance(ench, dict):
        afx = []
        for k, v in ench.items():
            if k in ("dmg", primary_key) or not isinstance(v, dict): continue
            if str(v.get("source")) != "affix": continue
            try: val = int(v.get("value", 0) or 0)
            except Exception: val = 0
            afx.append((k, val))
        afx.sort(key=lambda t: (t[0], -t[1]))
        for k, val in afx:
            parts.append(f"{_stat_emoji(k, pclass)}+{int(val)}")
    stats_str = ", ".join(parts) if parts else "—"
    return f"『[{cur_d}/{max_d}] {item_emoji}{name} [ {tier} ] [ {rarity_label} ]: {stats_str}』"


async def market_adventurer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ponto de entrada para o Mercado do Aventureiro.
    (Agora permite que TODOS os jogadores entrem)
    """
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id

    # --- VERIFICAÇÃO PREMIUM REMOVIDA DESTA FUNÇÃO ---
    # Todos os jogadores podem aceder a este menu.

    text = (
        "🎒 <b>Mercado do Aventureiro</b>\n"
        "Compre e venda itens com outros jogadores."
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Listagens (Ver Itens)", callback_data="market_list")],
        [InlineKeyboardButton("➕ Vender Item", callback_data="market_sell:1")],
        [InlineKeyboardButton("👤 Minhas Listagens", callback_data="market_my")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market")],
    ])

    keys = ["mercado_aventureiro", "img_mercado_aventureiro", "market_adventurer", "market_aventurer_img"]
    try:
        await q.delete_message()
    except Exception:
        pass
    await _send_with_media(chat_id, context, text, kb, keys)

async def market_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    user_id = q.from_user.id
    
    # Carrega dados do jogador que está a ver a lista
    viewer_pdata = await player_manager.get_player_data(user_id) or {}

    # <<< CORREÇÃO APLICADA AQUI >>>
    # Verifica se o JOGADOR QUE ESTÁ A VER é premium
    is_premium_viewer = player_manager.has_premium_plan(viewer_pdata) 

    listings = market_manager.list_active() # Síncrono (corrigido antes)
    logger.info("[market_list] ativos=%d", len(listings))

    if not listings:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]])
        await _safe_edit_or_send(q, context, chat_id, "Não há listagens ativas no momento.", kb)
        return

    lines = ["📦 <b>Listagens ativas</b>\n"]
    
    # Adiciona um aviso se o jogador não for premium
    if not is_premium_viewer:
        lines.append("<i>Apenas Apoiadores (Premium) podem comprar itens.</i>\n")
        
    kb_rows = []
    for l in listings[:30]: 
        lines.append("• " + _mm_render_listing_line(l, viewer_player_data=viewer_pdata, show_price_per_unit=True))
        
        # <<< CORREÇÃO APLICADA AQUI >>>
        # Só mostra o botão "Comprar" se:
        # 1. O visualizador for premium
        # 2. O visualizador não for o vendedor do item
        if is_premium_viewer and int(l.get("seller_id", 0)) != user_id:
            kb_rows.append([InlineKeyboardButton(f"Comprar #{l['id']}", callback_data=f"market_buy_{l['id']}")])

    kb_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")])
    await _safe_edit_or_send(q, context, chat_id, "\n".join(lines), InlineKeyboardMarkup(kb_rows))

async def market_my(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id
    
    # Carrega dados do jogador (correto)
    viewer_pdata = await player_manager.get_player_data(user_id) or {}

    # <<< CORREÇÃO APLICADA AQUI: REMOVIDO 'await' >>>
    # list_by_seller é SÍNCRONO
    my = market_manager.list_by_seller(user_id) 

    # Se não houver listagens
    if not my:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]])
        await _safe_edit_or_send(q, context, chat_id, "Você não tem listagens ativas.", kb)
        return

    # Monta a lista e botões
    lines = ["👤 <b>Minhas listagens</b>\n"]
    kb_rows = []
    for l in my:
        # Renderiza linha (síncrono)
        lines.append("• " + _mm_render_listing_line(l, viewer_player_data=viewer_pdata, show_price_per_unit=True))
        # Adiciona botão de cancelar
        kb_rows.append([InlineKeyboardButton(f"Cancelar #{l['id']}", callback_data=f"market_cancel_{l['id']}")])

    # Adiciona botão de voltar
    kb_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")])
    
    # Envia mensagem
    await _safe_edit_or_send(q, context, chat_id, "\n".join(lines), InlineKeyboardMarkup(kb_rows))

async def market_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id
    
    try:
        lid = int(q.data.replace("market_cancel_", ""))
    except (ValueError, AttributeError):
        await q.answer("ID de listagem inválido.", show_alert=True)
        return

    # <<< CORREÇÃO 1: REMOVIDO 'await' >>>
    listing = market_manager.get_listing(lid) 

    if not listing or not listing.get("active"):
        await q.answer("Listagem inválida ou já cancelada.", show_alert=True)
        await market_my(update, context) 
        return
    if int(listing.get("seller_id", 0)) != int(user_id):
        await q.answer("Você não pode cancelar a listagem de outro jogador.", show_alert=True)
        return

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        await q.answer("Erro ao carregar seus dados.", show_alert=True)
        return
        
    # Devolve o item
    it = listing.get("item") 
    if isinstance(it, dict): 
        item_type = it.get("type")
        if item_type == "stack": 
            base_id = it.get("base_id")
            pack_qty = int(it.get("qty", 1))
            lots_left = int(listing.get("quantity", 0))
            total_return = pack_qty * max(0, lots_left)
            if total_return > 0 and base_id:
                player_manager.add_item_to_inventory(pdata, base_id, total_return)
        elif item_type == "unique": 
            uid = it.get("uid")
            inst = it.get("item")
            if uid and inst: 
                 inv = pdata.get("inventory", {}) or {}
                 new_uid = uid 
                 count = 0
                 while new_uid in inv: 
                     count += 1
                     new_uid = f"{uid}_ret_{count}"
                     if count > 5: break 
                 
                 if new_uid not in inv:
                     inv[new_uid] = inst
                     pdata["inventory"] = inv
                 else:
                      logger.error(f"Não foi possível devolver o item único {uid} ao cancelar listagem {lid} (conflito UID).")
                      await context.bot.send_message(chat_id, f"⚠️ Erro ao devolver o item da listagem #{lid}. Contacte um admin.")
        else:
             logger.error(f"Tipo de item desconhecido ou inválido ao cancelar listagem {lid}: {item_type}")
             await context.bot.send_message(chat_id, f"⚠️ Erro ao processar o item da listagem #{lid}. Contacte um admin.")
    else: 
         logger.error(f"Estrutura de item inválida na listagem {lid} ao cancelar: {repr(it)}")
         await context.bot.send_message(chat_id, f"⚠️ Erro crítico ao ler o item da listagem #{lid}. Contacte um admin.")

    await player_manager.save_player_data(user_id, pdata)
    
    # <<< CORREÇÃO 2: REMOVIDO 'await' >>>
    market_manager.delete_listing(lid) 

    await _safe_edit_or_send(q, context, chat_id, f"❌ Listagem #{lid} cancelada e itens devolvidos.", InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market_my")]
    ]))

async def market_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    buyer_id = q.from_user.id
    chat_id = update.effective_chat.id
    
    try:
        lid = int(q.data.replace("market_buy_", ""))
    except (ValueError, AttributeError):
        await q.answer("ID de listagem inválido.", show_alert=True)
        return

    listing = market_manager.get_listing(lid) # Síncrono (corrigido antes)

    if not listing or not listing.get("active"):
        await q.answer("Listagem não está mais ativa.", show_alert=True)
        return
    if int(listing.get("seller_id", 0)) == int(buyer_id):
        await q.answer("Você não pode comprar sua própria listagem.", show_alert=True)
        return

    # Carrega dados do comprador
    buyer = await player_manager.get_player_data(buyer_id)
    
    # <<< CORREÇÃO DE SEGURANÇA APLICADA AQUI >>>
    # Verifica se o comprador é premium ANTES de carregar o vendedor ou processar
    if not player_manager.has_premium_plan(buyer):
         await q.answer("Apenas Apoiadores Premium podem comprar itens.", show_alert=True)
         return # Para a execução
         
    # Se chegou aqui, o comprador É premium. Continua a lógica normal.
    seller_id = listing.get("seller_id")
    seller = None
    if seller_id:
         seller = await player_manager.get_player_data(seller_id)

    if not buyer or not seller:
        if not seller and seller_id:
             logger.error(f"Erro crítico: Vendedor {seller_id} da listagem {lid} não encontrado no DB.")
        await q.answer("Erro ao carregar dados do comprador ou vendedor.", show_alert=True)
        return

    try:
        # Chama a compra (síncrona)
        updated_listing, total_price = market_manager.purchase_listing(
            buyer_id=buyer_id, listing_id=lid, quantity=1 
        )
    except market_manager.MarketError as e:
        await q.answer(str(e), show_alert=True) 
        return
    except Exception as e: 
         logger.error(f"Erro inesperado durante purchase_listing para L{lid} B{buyer_id}: {e}", exc_info=True)
         await q.answer("Ocorreu um erro ao processar a compra.", show_alert=True)
         return

    # Recarrega os dados APÓS a compra
    buyer_after = await player_manager.get_player_data(buyer_id)
    seller_after = await player_manager.get_player_data(seller_id)
    if not buyer_after or not seller_after:
         logger.error(f"Falha ao recarregar dados de B{buyer_id} ou S{seller_id} após compra de L{lid}")
         await _safe_edit_or_send(q, context, chat_id, f"✅ Compra concluída (#{lid}), mas ocorreu um erro ao atualizar os dados locais. Verifique seu inventário/ouro.", InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_list")]]))
         return

    # Entrega o item ao comprador
    it = listing.get("item") 
    if isinstance(it, dict):
         item_type = it.get("type")
         if item_type == "stack":
             base_id = it.get("base_id")
             pack_qty = int(it.get("qty", 1))
             if base_id:
                 player_manager.add_item_to_inventory(buyer_after, base_id, pack_qty)
         elif item_type == "unique":
             uid = it.get("uid")
             inst = it.get("item")
             if uid and inst:
                 inv = buyer_after.get("inventory", {}) or {}
                 new_uid = uid 
                 count = 0
                 while new_uid in inv: 
                     count += 1
                     new_uid = f"{uid}_buy_{count}"
                     if count > 5: break
                 
                 if new_uid not in inv:
                      inv[new_uid] = inst
                      buyer_after["inventory"] = inv
                 else:
                      logger.error(f"Não foi possível entregar o item único {uid} da L{lid} (conflito UID).")
                      await context.bot.send_message(chat_id, f"⚠️ Erro CRÍTICO ao entregar o item da compra #{lid}! Contacte um admin.")
    else: 
        logger.error(f"Estrutura de item inválida na listagem {lid} durante a compra: {repr(it)}")
        await context.bot.send_message(chat_id, f"⚠️ Erro CRÍTICO ao processar o item da compra #{lid}! Contacte um admin.")

    # Atualiza Missões (para 'seller_after')
    seller_after["user_id"] = seller_id 
    await mission_manager.update_mission_progress(
        seller_after,
        event_type="MARKET_SELL",
        details={ "item_id": it.get("base_id") if isinstance(it, dict) else None, "quantity": 1 } 
    )
    clan_id = seller_after.get("clan_id")
    if clan_id:
        try:
             await clan_manager.update_guild_mission_progress(
                 clan_id=clan_id,
                 mission_type='MARKET_SELL',
                 details={
                     "item_id": it.get("base_id") if isinstance(it, dict) else None, 
                     "quantity": 1, "gold_value": total_price
                 },
                 context=context 
             )
        except Exception as e_clan_mission:
             logger.error(f"Erro ao atualizar missão de guilda MARKET_SELL para clã {clan_id}: {e_clan_mission}")

    # Salva dados
    await player_manager.save_player_data(buyer_id, buyer_after)
    await player_manager.save_player_data(seller_id, seller_after)

    # Confirmação
    remaining_lots = int(updated_listing.get("quantity", 0)) if updated_listing.get("active") else 0
    suffix = f" Restam {remaining_lots} lote(s)." if remaining_lots > 0 else " Não restam lotes."
    await _safe_edit_or_send(q, context, chat_id, f"✅ Compra concluída (#{lid}). {total_price} 🪙 transferidos.{suffix}", InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market_list")]
    ]))

async def market_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = update.effective_chat.id

    # <<< CORREÇÃO 18: Adiciona await >>>
    pdata = await player_manager.get_player_data(user_id) or {}

    try:
        page = int(query.data.split(':')[1])
    except (IndexError, ValueError):
        page = 1

    ITEMS_PER_PAGE = 8
    inv = pdata.get("inventory", {}) or {}
    pclass = _player_class_key(pdata) # Síncrono

    sellable_items = []
    # Loop síncrono sobre o inventário
    for uid, inst in inv.items():
        if isinstance(inst, dict):
            base_id = inst.get("base_id") or inst.get("tpl") or inst.get("id")
            if base_id and base_id not in EVOLUTION_ITEMS:
                sellable_items.append({"type": "unique", "uid": uid, "inst": inst})
    for base_id, qty in inv.items():
        if isinstance(qty, (int, float)) and int(qty) > 0:
            if base_id not in EVOLUTION_ITEMS:
                sellable_items.append({"type": "stack", "base_id": base_id, "qty": int(qty)})

    sellable_items.sort(key=lambda x: x.get('uid', x.get('base_id')))

    start_index = (page - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    items_for_page = sellable_items[start_index:end_index]

    caption = f"➕ <b>Vender Item</b> (Página {page})\nSelecione um item do seu inventário:\n"
    keyboard_rows = []

    if not sellable_items:
        caption = "Você não tem itens vendáveis no seu inventário."
        keyboard_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")])
    elif not items_for_page:
        caption = "Não há mais itens para mostrar."
        keyboard_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")])
    else:
        for item in items_for_page:
            if item["type"] == "unique":
                full_line = _render_unique_line_safe(item["inst"], pclass) # Síncrono
                callback_data = f"market_pick_unique_{item['uid']}"
                keyboard_rows.append([InlineKeyboardButton(_cut_middle(full_line, 56), callback_data=callback_data)]) # Síncrono
            else:
                label = f"📦 {_item_label_from_base(item['base_id'])} ({item['qty']}x)" # Síncrono
                callback_data = f"market_pick_stack_{item['base_id']}"
                keyboard_rows.append([InlineKeyboardButton(label, callback_data=callback_data)])

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"market_sell:{page - 1}"))
    if end_index < len(sellable_items):
        nav_buttons.append(InlineKeyboardButton("Próxima ➡️", callback_data=f"market_sell:{page + 1}"))

    if nav_buttons:
        keyboard_rows.append(nav_buttons)

    keyboard_rows.append([InlineKeyboardButton("⬅️ Voltar ao Mercado", callback_data="market_adventurer")])
    await _safe_edit_or_send(query, context, chat_id, caption, InlineKeyboardMarkup(keyboard_rows))

def _render_price_spinner(price: int) -> InlineKeyboardMarkup:
    price = max(1, int(price))
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("−100", callback_data="mktp_dec_100"),
            InlineKeyboardButton("−10",  callback_data="mktp_dec_10"),
            InlineKeyboardButton("−1",   callback_data="mktp_dec_1"),
            InlineKeyboardButton(f"💰 {price} 🪙", callback_data="noop"),
            InlineKeyboardButton("+1",   callback_data="mktp_inc_1"),
            InlineKeyboardButton("+10",  callback_data="mktp_inc_10"),
            InlineKeyboardButton("+100", callback_data="mktp_inc_100"),
        ],
        [InlineKeyboardButton("✅ Confirmar", callback_data="mktp_confirm")],
        [InlineKeyboardButton("❌ Cancelar",  callback_data="market_cancel_new")]
    ])

async def _show_price_spinner(q, context, chat_id: int, caption_prefix: str = "Defina o preço:"):
    price = max(1, int(context.user_data.get("market_price", 50)))
    kb = _render_price_spinner(price)
    await _safe_edit_or_send(q, context, chat_id, f"{caption_prefix} <b>{price} 🪙</b>", kb)

async def market_price_spin(update, context):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id

    cur = max(1, int(context.user_data.get("market_price", 50)))
    action = q.data
    if action.startswith("mktp_inc_"):
        step = int(action.split("_")[-1]); cur += step
    elif action.startswith("mktp_dec_"):
        step = int(action.split("_")[-1]); cur = max(1, cur - step)
    context.user_data["market_price"] = cur

    kb = _render_price_spinner(cur)
    await _safe_edit_or_send(q, context, chat_id, f"Defina o preço: <b>{cur} 🪙</b>", kb)

async def market_price_confirm(update, context):
    q = update.callback_query
    await q.answer()
    price = max(1, int(context.user_data.get("market_price", 1)))
    await market_finalize_listing(update, context, price)

async def market_pick_unique(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id
    uid = q.data.replace("market_pick_unique_", "")

    # <<< CORREÇÃO 19: Adiciona await >>>
    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {}) or {}
    inst = inv.get(uid)
    if not isinstance(inst, dict):
        await q.answer("Item não encontrado.", show_alert=True); return

    base_id = inst.get("base_id") or inst.get("tpl") or inst.get("id")
    if base_id in EVOLUTION_ITEMS:
        # Usar answer com show_alert=True para mensagens de erro importantes
        await q.answer("Itens de evolução não podem ser vendidos aqui.", show_alert=True)
        # Considerar retornar ao menu anterior em vez de só dar answer
        # await market_sell(update, context) # Exemplo: recarrega a lista
        return

    context.user_data["market_pending"] = {"type": "unique", "uid": uid, "item": inst}
    
    # Remove o item do inventário ANTES de mostrar o preço
    if uid in inv:
      del inv[uid]
      pdata["inventory"] = inv
      # <<< CORREÇÃO 20: Adiciona await >>>
      await player_manager.save_player_data(user_id, pdata)
    else:
       # Se o item já não estava no inventário (talvez removido em outra aba?), avisa erro.
       await q.answer("Erro: Item não encontrado no inventário.", show_alert=True)
       # Limpa o estado pendente e retorna ao menu de venda
       context.user_data.pop("market_pending", None)
       await market_sell(update, context)
       return

    context.user_data["market_price"] = 50 # Preço inicial
    # <<< CORREÇÃO 21: Adiciona await >>>
    await _show_price_spinner(q, context, chat_id, "Defina o <b>preço</b> deste item único:")

async def market_pick_stack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id
    base_id = q.data.replace("market_pick_stack_", "")

    if base_id in EVOLUTION_ITEMS:
        await q.answer("Itens de evolução não podem ser vendidos aqui.", show_alert=True)
        return

    # <<< CORREÇÃO 22: Adiciona await >>>
    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {}) or {}
    qty_have = int(inv.get(base_id, 0))
    if qty_have <= 0: # Simplificado: verifica se tem algum
        await q.answer("Quantidade insuficiente.", show_alert=True); return

    context.user_data["market_pending"] = {"type": "stack", "base_id": base_id, "qty_have": qty_have}

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("×1", callback_data="market_qty_1"),
         InlineKeyboardButton("×5", callback_data="market_qty_5"),
         InlineKeyboardButton("×10", callback_data="market_qty_10"),
         InlineKeyboardButton(f"×{qty_have} (Tudo)", callback_data="market_qty_all")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data=f"market_sell:{context.user_data.get('market_sell_page', 1)}")] # Volta para a página atual
    ])
    
    # <<< CORREÇÃO 23: Adiciona await >>>
    await _safe_edit_or_send(
        q, context, chat_id,
        f"Quanto deseja colocar por <b>lote</b> em <b>{_item_label_from_base(base_id)}</b>? Você possui {qty_have}.",
        kb
    )

async def market_choose_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    pending = context.user_data.get("market_pending") or {}
    if pending.get("type") != "stack":
        # Se o estado pendente for inválido, cancela a operação
        await market_cancel_new(update, context)
        return

    qty_have = int(pending.get("qty_have", 0))
    data = q.data
    if data == "market_qty_all":
        qty = qty_have
    else:
        try: # Adiciona try-except para o int()
            qty = int(data.replace("market_qty_", ""))
            if qty <= 0 or qty > qty_have:
                 await q.answer("Quantidade inválida.", show_alert=True); return
        except ValueError:
             await q.answer("Quantidade inválida.", show_alert=True); return


    pending["qty"] = qty
    context.user_data["market_pending"] = pending
    context.user_data["market_price"] = 10 # Preço inicial por lote
    
    # <<< CORREÇÃO 24: Adiciona await >>>
    await _show_price_spinner(q, context, chat_id, "Defina o <b>preço por lote</b>:")

async def market_cancel_new(update, context):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id

    pending = context.user_data.pop("market_pending", None)
    if pending and pending.get("type") == "unique":
        # <<< CORREÇÃO 25: Adiciona await >>>
        pdata = await player_manager.get_player_data(user_id)
        inv = pdata.get("inventory", {}) or {}
        uid = pending["uid"]
        new_uid = uid if uid not in inv else f"{uid}_back"
        inv[new_uid] = pending["item"]
        pdata["inventory"] = inv
        # <<< CORREÇÃO 26: Adiciona await >>>
        await player_manager.save_player_data(user_id, pdata)

    context.user_data.pop("market_price", None)
    # <<< CORREÇÃO 27: Adiciona await >>>
    await _safe_edit_or_send(q, context, chat_id, "Criação de listagem cancelada.", InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]
    ]))

async def market_finalize_listing(update: Update, context: ContextTypes.DEFAULT_TYPE, price: int):
    logger.info("[market_finalize_listing] start price=%s has_cb=%s",
                price, bool(update.callback_query))

    query_obj = None # Inicializa query_obj
    if update.callback_query:
        user_id = update.callback_query.from_user.id
        chat_id = update.effective_chat.id # Usa effective_chat para garantir
        query_obj = update.callback_query # Guarda a query para _safe_edit_or_send
    else:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

    pending = context.user_data.get("market_pending")
    if not pending:
        logger.warning("[market_finalize_listing] NADA pendente em user_data")
        # Envia mensagem diretamente pois pode não haver query
        await context.bot.send_message(chat_id=chat_id, text="Nada pendente para vender. Volte e selecione o item novamente.")
        return

    # Carrega pdata UMA VEZ
    pdata = await player_manager.get_player_data(user_id)
    # Se pdata não for carregado, não podemos continuar
    if not pdata:
         await context.bot.send_message(chat_id=chat_id, text="Erro ao carregar dados do jogador.")
         context.user_data.pop("market_pending", None) # Limpa estado
         context.user_data.pop("market_price", None)
         return

    inv = pdata.get("inventory", {}) or {} # Garante que é um dict

    try:
        if pending["type"] == "unique":
            # Verifica item de evolução ANTES de criar
            base_id = (pending["item"] or {}).get("base_id") # Pega base_id
            if base_id in EVOLUTION_ITEMS:
                await context.bot.send_message(chat_id=chat_id, text=EVOL_BLOCK_MSG, parse_mode="HTML")
                # Devolve o item único que foi removido prematuramente
                inv = pdata.get("inventory", {}) or {} # Recarrega inv caso tenha mudado
                uid = pending["uid"]
                new_uid = uid if uid not in inv else f"{uid}_back_evol"
                inv[new_uid] = pending["item"]
                pdata["inventory"] = inv
                await player_manager.save_player_data(user_id, pdata) # Salva devolução
                context.user_data.pop("market_pending", None)
                context.user_data.pop("market_price", None)
                return # Interrompe a função

            item_payload = {"type": "unique", "uid": pending["uid"], "item": pending["item"]}
            
            # <<< CORREÇÃO APLICADA AQUI: REMOVIDO 'await' >>>
            listing = market_manager.create_listing(seller_id=user_id, item_payload=item_payload, unit_price=price, quantity=1)
        
        else: # type == "stack"
            base_id = pending["base_id"]
            # Verifica item de evolução ANTES de modificar inventário
            if base_id in EVOLUTION_ITEMS:
                await context.bot.send_message(chat_id=chat_id, text=EVOL_BLOCK_MSG, parse_mode="HTML")
                context.user_data.pop("market_pending", None)
                context.user_data.pop("market_price", None)
                return # Interrompe a função

            pack_qty = int(pending.get("qty", 0))
            # Usa 'pdata' já carregado para verificar quantidade
            have = int((pdata.get("inventory", {}) or {}).get(base_id, 0)) # Verifica no pdata atual
            
            if pack_qty <= 0 or have < pack_qty:
                logger.warning("[market_finalize_listing] qty inválida: pack=%s have=%s", pack_qty, have)
                await context.bot.send_message(chat_id=chat_id, text="Quantidade inválida ou insuficiente.")
                context.user_data.pop("market_pending", None)
                context.user_data.pop("market_price", None)
                return

            # Remove do inventário (modifica 'pdata' em memória)
            inv = pdata.get("inventory", {}) or {} # Pega o inventário novamente para garantir
            inv[base_id] = have - pack_qty
            if inv[base_id] <= 0:
                 del inv[base_id]
            pdata["inventory"] = inv # Atualiza pdata em memória
            
            # Salva pdata AGORA, APÓS remover o item
            await player_manager.save_player_data(user_id, pdata)

            item_payload = {"type": "stack", "base_id": base_id, "qty": pack_qty}
            
            # <<< CORREÇÃO APLICADA AQUI: REMOVIDO 'await' >>>
            listing = market_manager.create_listing(seller_id=user_id, item_payload=item_payload, unit_price=price, quantity=1)

        # Limpa o estado pendente APÓS a criação bem-sucedida
        context.user_data.pop("market_pending", None)
        context.user_data.pop("market_price", None)

        text = f"✅ Listagem #{listing['id']} criada."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("👤 Minhas Listagens", callback_data="market_my")],
                                   [InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]])

        # Envia a confirmação (edita se possível, senão envia nova)
        if query_obj:
            await _safe_edit_or_send(query_obj, context, chat_id, text, kb)
        else:
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=kb, parse_mode='HTML')

        logger.info("[market_finalize_listing] OK -> #%s", listing["id"])

    except Exception as e:
        logger.exception("[market_finalize_listing] erro: %s", e)
        # Tenta enviar mensagem de erro
        try:
             await context.bot.send_message(chat_id=chat_id, text="Falha ao criar a listagem. Tente novamente.")
        except Exception:
             pass # Ignora se até o envio da msg de erro falhar

        # Tenta devolver o item único se a criação falhou E se era um item único
        if pending and pending.get("type") == "unique":
            try:
                # Recarrega pdata para garantir que temos o estado mais recente
                pdata_reloaded = await player_manager.get_player_data(user_id)
                inv_reloaded = (pdata_reloaded or {}).get("inventory", {}) or {}
                uid = pending["uid"]
                # Adiciona de volta apenas se não existir já (evita duplicar se save falhou antes)
                if uid not in inv_reloaded:
                     new_uid = uid # Tenta usar o UID original primeiro
                     # Se já existir algo com UID original (improvável), usa um sufixo
                     count = 0
                     while new_uid in inv_reloaded:
                         count += 1
                         new_uid = f"{uid}_fail_ret_{count}"
                         if count > 5: break # Limite para evitar loop infinito
                     
                     if new_uid not in inv_reloaded:
                         inv_reloaded[new_uid] = pending["item"]
                         pdata_reloaded["inventory"] = inv_reloaded
                         await player_manager.save_player_data(user_id, pdata_reloaded)
                         logger.info(f"Item único {uid} (como {new_uid}) devolvido após falha ao criar listagem.")
                     else:
                          logger.error(f"Não foi possível devolver o item único {uid} após falha (conflito de UID mesmo com sufixo).")
                else:
                     logger.warning(f"Item único {uid} já estava no inventário ao tentar devolver após falha.")
                     
            except Exception as e_ret:
                logger.error(f"Erro CRÍTICO ao tentar devolver item único {pending.get('uid')} após falha: {e_ret}")
        
        # Limpa o estado pendente de qualquer forma em caso de erro
        context.user_data.pop("market_pending", None) 
        context.user_data.pop("market_price", None)        
# ==============================
#  Handlers (exports para este arquivo)
# ==============================
market_adventurer_handler = CallbackQueryHandler(market_adventurer, pattern=r'^market_adventurer$')
market_list_handler       = CallbackQueryHandler(market_list, pattern=r'^market_list$')
market_my_handler         = CallbackQueryHandler(market_my, pattern=r'^market_my$')
market_sell_handler       = CallbackQueryHandler(market_sell, pattern=r'^market_sell(:(\d+))?$')
market_buy_handler        = CallbackQueryHandler(market_buy, pattern=r'^market_buy_\d+$')
market_cancel_handler     = CallbackQueryHandler(market_cancel, pattern=r'^market_cancel_\d+$')
market_pick_unique_handler= CallbackQueryHandler(market_pick_unique, pattern=r'^market_pick_unique_')
market_pick_stack_handler = CallbackQueryHandler(market_pick_stack,  pattern=r'^market_pick_stack_')
market_qty_handler        = CallbackQueryHandler(market_choose_qty,  pattern=r'^market_qty_')
market_price_spin_handler    = CallbackQueryHandler(market_price_spin,    pattern=r'^mktp_(inc|dec)_[0-9]+$')
market_price_confirm_handler = CallbackQueryHandler(market_price_confirm, pattern=r'^mktp_confirm$')
market_cancel_new_handler = CallbackQueryHandler(market_cancel_new, pattern=r'^market_cancel_new$')