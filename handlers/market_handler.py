# handlers/market_handler.py
import logging
from typing import List, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler, MessageHandler, filters
# modules importados
from modules import player_manager, game_data, file_id_manager, market_manager, clan_manager
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
#  UTILS BÁSICOS
# ==============================
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
#  MERCADO (MENU PRINCIPAL)
# ==============================
async def market_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o menu principal do Mercado."""
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id

    caption = "🛒 <b>Mercado</b>\nEscolha uma opção:"
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎒 𝐌𝐞𝐫𝐜𝐚𝐝𝐨 𝐝𝐨 𝐀𝐯𝐞𝐧𝐭𝐮𝐫𝐞𝐢𝐫𝐨", callback_data="market_adventurer")],
        [InlineKeyboardButton(" 🏛️ 𝐂𝐨𝐦𝐞́𝐫𝐜𝐢𝐨 𝐝𝐞 𝐑𝐞𝐥𝐢́𝐪𝐮𝐢𝐚𝐬 💎 ", callback_data="gem_market_main")],
        [InlineKeyboardButton("🏰 𝐋𝐨𝐣𝐚 𝐝𝐨 𝐑𝐞𝐢𝐧𝐨", callback_data="market_kingdom")],
        [InlineKeyboardButton("💎 𝐋𝐨𝐣𝐚 𝐝𝐞 𝐆𝐞𝐦𝐚𝐬", callback_data="gem_shop")],
        [InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="continue_after_action")],
    ])

    try: await q.delete_message()
    except Exception: pass 
    media_keys = ["market", "mercado_principal", "img_mercado"] 
    await _send_with_media(chat_id, context, caption, kb, media_keys)

# ==============================
#  MERCADO DO AVENTUREIRO (P2P)
# ==============================
async def market_adventurer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id

    text = "🎒 <b>Mercado do Aventureiro</b>\nCompre e venda itens com outros jogadores."
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Listagens", callback_data="market_list")],
        [InlineKeyboardButton("➕ Vender Item", callback_data="market_sell:1")],
        [InlineKeyboardButton("👤 Minhas Listagens", callback_data="market_my")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market")],
    ])

    keys = ["mercado_aventureiro", "img_mercado_aventureiro", "market_adventurer", "market_aventurer_img"]
    try: await q.delete_message()
    except Exception: pass
    await _send_with_media(chat_id, context, text, kb, keys)

async def market_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    user_id = q.from_user.id
    
    viewer_pdata = await player_manager.get_player_data(user_id) or {}
    is_premium_viewer = player_manager.has_premium_plan(viewer_pdata)

    # list_active é síncrono no seu manager atual
    listings = market_manager.list_active(
        viewer_id=user_id, # Importante para ver itens privados
        page=1,
        page_size=20
    )
    
    if not listings:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]])
        await _safe_edit_or_send(q, context, chat_id, "Não há listagens ativas no momento.", kb)
        return

    lines = ["📦 <b>Listagens ativas</b>\n"]
    if not is_premium_viewer:
        lines.append("<i>Apenas Apoiadores (Premium) podem comprar itens.</i>\n")
        
    kb_rows = []
    for l in listings[:30]:
        # Renderiza a linha com suporte a visualização de privado
        lines.append("• " + _mm_render_listing_line(l, viewer_player_data=viewer_pdata, show_price_per_unit=True))
        
        # Botão de compra
        if is_premium_viewer and int(l.get("seller_id", 0)) != user_id:
            # Mostra cadeado no botão se for privado
            btn_txt = f"🔒 Comprar #{l['id']}" if l.get("target_buyer_id") else f"Comprar #{l['id']}"
            kb_rows.append([InlineKeyboardButton(btn_txt, callback_data=f"market_buy_{l['id']}")])

    kb_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")])
    await _safe_edit_or_send(q, context, chat_id, "\n".join(lines), InlineKeyboardMarkup(kb_rows))

async def market_my(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id
    viewer_pdata = await player_manager.get_player_data(user_id) or {}

    my = market_manager.list_by_seller(user_id)
    if not my:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]])
        await _safe_edit_or_send(q, context, chat_id, "Você não tem listagens ativas.", kb)
        return

    lines = ["👤 <b>Minhas listagens</b>\n"]
    kb_rows = []
    for l in my:
        lines.append("• " + _mm_render_listing_line(l, viewer_player_data=viewer_pdata, show_price_per_unit=True))
        kb_rows.append([InlineKeyboardButton(f"Cancelar #{l['id']}", callback_data=f"market_cancel_{l['id']}")])

    kb_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")])
    await _safe_edit_or_send(q, context, chat_id, "\n".join(lines), InlineKeyboardMarkup(kb_rows))

async def market_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id
    lid = int(q.data.replace("market_cancel_", ""))

    listing = market_manager.get_listing(lid)
    if not listing or not listing.get("active"):
        await q.answer("Listagem inválida.", show_alert=True); return
    
    if int(listing["seller_id"]) != int(user_id):
        await q.answer("Você não pode cancelar de outro jogador.", show_alert=True); return

    pdata = await player_manager.get_player_data(user_id)
    it = listing["item"]
    
    # Devolução do item
    if it["type"] == "stack":
        base_id = it["base_id"]
        pack_qty = int(it.get("qty", 1))
        lots_left = int(listing.get("quantity", 0))
        total_return = pack_qty * max(0, lots_left)
        if total_return > 0:
            player_manager.add_item_to_inventory(pdata, base_id, total_return)
    else:
        # Unique
        uid = it["uid"]
        inst = it["item"]
        inv = pdata.get("inventory", {}) or {}
        new_uid = uid if uid not in inv else f"{uid}_ret"
        inv[new_uid] = inst
        pdata["inventory"] = inv

    await player_manager.save_player_data(user_id, pdata)
    market_manager.delete_listing(lid)

    await _safe_edit_or_send(q, context, chat_id, f"❌ Listagem #{lid} cancelada e itens devolvidos.", InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market_my")]
    ]))

async def market_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    buyer_id = q.from_user.id
    chat_id = update.effective_chat.id
    lid = int(q.data.replace("market_buy_", ""))

    try:
        buyer_data = await player_manager.get_player_data(buyer_id)
        if not player_manager.has_premium_plan(buyer_data):
            await q.answer("Apenas Apoiadores (Premium) podem comprar itens.", show_alert=True)
            return

        updated_listing, total_price = await market_manager.purchase_listing(
            buyer_id=buyer_id, 
            listing_id=lid, 
            quantity=1,
            context=context
        )
        
        remaining = int(updated_listing.get("quantity", 0)) if updated_listing.get("active") else 0
        suffix = f" Restam {remaining} lote(s)." if remaining > 0 else " Não restam lotes."
        
        await _safe_edit_or_send(q, context, chat_id, f"✅ Compra concluída (#{lid}). {total_price} 🪙 transferidos.{suffix}", InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Voltar", callback_data="market_list")]
        ]))

    except Exception as e:
        await q.answer(f"Erro: {e}", show_alert=True)

# ==============================
#  LÓGICA DE VENDA (SPINNERS E FLUXO)
# ==============================
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
        [InlineKeyboardButton("✅ Confirmar Preço", callback_data="mktp_confirm")],
        [InlineKeyboardButton("❌ Cancelar",  callback_data="market_cancel_new")]
    ])

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
    prefix = "Defina o <b>preço</b>:"
    await _safe_edit_or_send(q, context, chat_id, f"{prefix} <b>{cur} 🪙</b>", kb)

# --- (AQUI ESTÁ A CORREÇÃO PRINCIPAL) ---
async def market_price_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chamado quando clica em Confirmar Preço. Mostra os botões Público/Privado."""
    q = update.callback_query
    await q.answer()
    
    price = max(1, int(context.user_data.get("market_price", 1)))
    
    # MOSTRA O NOVO MENU DE TIPO DE VENDA
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 Venda Pública (Todos)", callback_data="mkt_type_public")],
        [InlineKeyboardButton("🔒 Venda Privada (VIP)", callback_data="mkt_type_private")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="market_cancel_new")]
    ])
    
    await _safe_edit_or_send(q, context, update.effective_chat.id, 
        f"💰 Preço definido: <b>{price} 🪙</b>\n\nComo deseja anunciar este item?", 
        kb
    )

# --- OPÇÃO 1: VENDA PÚBLICA ---
async def market_type_public(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    # Limpa dados de privado
    context.user_data.pop("market_target_id", None)
    context.user_data.pop("market_target_name", None)
    
    price = context.user_data.get("market_price", 1)
    await market_finalize_listing(update, context, price)

# --- OPÇÃO 2: VENDA PRIVADA ---
async def market_type_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    
    # Verifica VIP
    pdata = await player_manager.get_player_data(user_id)
    if not player_manager.has_premium_plan(pdata):
        await q.answer("🔒 Apenas VIPs podem fazer vendas privadas!", show_alert=True)
        return
        
    await q.answer()
    
    # ATIVA O ESTADO DE ESPERA
    context.user_data["awaiting_market_name"] = True
    
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="market_cancel_new")]])
    await _safe_edit_or_send(q, context, update.effective_chat.id,
        (
            "🔒 <b>VENDA PRIVADA</b>\n\n"
            "Por favor, <b>digite no chat o nome exato</b> do personagem para quem você quer vender.\n\n"
            "<i>Aguardando resposta...</i>"
        ),
        kb
    )

# --- CAPTURADOR DE TEXTO (MAGIA) ---
async def market_catch_input_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Se não estiver esperando nome, ignora
    if not context.user_data.get("awaiting_market_name"):
        return 

    context.user_data.pop("awaiting_market_name", None) # Limpa estado
    target_name = update.message.text.strip()
    
    found = await player_manager.find_player_by_name(target_name)
    if not found:
        await update.message.reply_text(f"❌ Jogador <b>{target_name}</b> não encontrado. Venda cancelada.", parse_mode="HTML")
        return

    target_id, target_pdata = found
    real_name = target_pdata.get("character_name", target_name)

    if target_id == user_id:
        await update.message.reply_text("❌ Você não pode vender para si mesmo.")
        return

    # Salva dados para o finalizador
    context.user_data["market_target_id"] = target_id
    context.user_data["market_target_name"] = real_name
    
    price = context.user_data.get("market_price", 1)
    await market_finalize_listing(update, context, price)

# --- FINALIZADOR (CRIA O ANÚNCIO) ---
async def market_finalize_listing(update: Update, context: ContextTypes.DEFAULT_TYPE, price: int):
    # Detecta de onde veio (callback ou mensagem)
    if update.callback_query:
        user_id = update.callback_query.from_user.id
        chat_id = update.effective_chat.id
    else:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

    pending = context.user_data.get("market_pending")
    if not pending:
        await context.bot.send_message(chat_id=chat_id, text="Erro: Nenhuma venda pendente.")
        return

    # Recupera dados privados
    target_id = context.user_data.get("market_target_id")
    target_name = context.user_data.get("market_target_name")

    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {}) or {}

    try:
        # Lógica de criação (igual anterior, mas com target_id)
        if pending["type"] == "unique":
            item_payload = {"type": "unique", "uid": pending["uid"], "item": pending["item"]}
            
            listing = market_manager.create_listing(
                seller_id=user_id, item_payload=item_payload, unit_price=price, quantity=1,
                target_buyer_id=target_id, target_buyer_name=target_name
            )
        else: # stack
            base_id = pending["base_id"]
            pack_qty = int(pending.get("qty", 1))
            
            # Remove do inv
            have = int(inv.get(base_id, 0))
            if have < pack_qty: raise ValueError("Sem qtd suficiente")
            inv[base_id] = have - pack_qty
            if inv[base_id] <= 0: del inv[base_id]
            pdata["inventory"] = inv
            await player_manager.save_player_data(user_id, pdata)

            item_payload = {"type": "stack", "base_id": base_id, "qty": pack_qty}
            
            listing = market_manager.create_listing(
                seller_id=user_id, item_payload=item_payload, unit_price=price, quantity=1,
                target_buyer_id=target_id, target_buyer_name=target_name
            )

        # Limpa tudo
        context.user_data.pop("market_pending", None)
        context.user_data.pop("market_price", None)
        context.user_data.pop("market_target_id", None)
        context.user_data.pop("market_target_name", None)

        # Feedback
        if target_name:
            text = f"✅ <b>Venda Privada Criada!</b>\n📦 Listagem #{listing['id']}\n🔒 Reservado para: <b>{target_name}</b>"
        else:
            text = f"✅ Listagem #{listing['id']} criada com sucesso!"

        kb = InlineKeyboardMarkup([[InlineKeyboardButton("👤 Minhas Listagens", callback_data="market_my")]])
        
        if update.callback_query:
            try: await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode='HTML')
            except: await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=kb, parse_mode='HTML')
        else:
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=kb, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Erro ao criar listing: {e}")
        await context.bot.send_message(chat_id=chat_id, text="Erro ao criar listagem.")

async def market_cancel_new(update, context):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    
    # Devolve item se cancelar no meio
    pending = context.user_data.pop("market_pending", None)
    if pending and pending.get("type") == "unique":
        pdata = await player_manager.get_player_data(user_id)
        inv = pdata.get("inventory", {}) or {}
        uid = pending["uid"]
        new_uid = uid if uid not in inv else f"{uid}_back"
        inv[new_uid] = pending["item"]
        pdata["inventory"] = inv
        await player_manager.save_player_data(user_id, pdata)

    context.user_data.pop("market_price", None)
    context.user_data.pop("awaiting_market_name", None)
    
    await q.edit_message_text("❌ Operação cancelada.", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar ao Mercado", callback_data="market_adventurer")]
    ]))

# ==============================
#  HANDLERS DE SELEÇÃO DE ITEM (Unique/Stack)
# ==============================
async def market_pick_unique(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    uid = q.data.replace("market_pick_unique_", "")

    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {}) or {}
    inst = inv.get(uid)
    if not isinstance(inst, dict): return

    base_id = inst.get("base_id") or inst.get("tpl") or inst.get("id")
    if base_id in EVOLUTION_ITEMS:
        await q.answer(EVOL_BLOCK_MSG, show_alert=True); return

    context.user_data["market_pending"] = {"type": "unique", "uid": uid, "item": inst}
    del inv[uid]
    pdata["inventory"] = inv
    await player_manager.save_player_data(user_id, pdata)

    context.user_data["market_price"] = 50
    await _render_price_spinner(50) # só inicializa
    await market_price_spin(update, context) # chama o spinner

async def market_pick_stack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    base_id = q.data.replace("market_pick_stack_", "")

    if base_id in EVOLUTION_ITEMS:
        await q.answer(EVOL_BLOCK_MSG, show_alert=True); return

    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {}) or {}
    qty_have = int(inv.get(base_id, 0))
    
    context.user_data["market_pending"] = {"type": "stack", "base_id": base_id, "qty_have": qty_have}
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("×1", callback_data="market_qty_1"),
         InlineKeyboardButton(f"×{qty_have}", callback_data="market_qty_all")],
        [InlineKeyboardButton("⬅️ Cancelar", callback_data="market_cancel_new")]
    ])
    await _safe_edit_or_send(q, context, update.effective_chat.id, f"Quantos deseja vender? (Você tem {qty_have})", kb)

async def market_choose_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    pending = context.user_data.get("market_pending")
    
    qty_have = int(pending.get("qty_have", 0))
    data = q.data
    qty = qty_have if data == "market_qty_all" else int(data.replace("market_qty_", ""))
    
    pending["qty"] = qty
    context.user_data["market_pending"] = pending
    context.user_data["market_price"] = 10
    await market_price_spin(update, context)


# ==============================
#  EXPORTS
# ==============================
market_open_handler = CallbackQueryHandler(market_open, pattern=r'^market$')
market_adventurer_handler = CallbackQueryHandler(market_adventurer, pattern=r'^market_adventurer$')

market_list_handler = CallbackQueryHandler(market_list, pattern=r'^market_list$')
market_my_handler = CallbackQueryHandler(market_my, pattern=r'^market_my$')
market_buy_handler = CallbackQueryHandler(market_buy, pattern=r'^market_buy_\d+$')
market_cancel_handler = CallbackQueryHandler(market_cancel, pattern=r'^market_cancel_\d+$')

market_pick_unique_handler= CallbackQueryHandler(market_pick_unique, pattern=r'^market_pick_unique_')
market_pick_stack_handler = CallbackQueryHandler(market_pick_stack,  pattern=r'^market_pick_stack_')
market_qty_handler        = CallbackQueryHandler(market_choose_qty,  pattern=r'^market_qty_')

market_price_spin_handler    = CallbackQueryHandler(market_price_spin,    pattern=r'^mktp_(inc|dec)_[0-9]+$')
market_price_confirm_handler = CallbackQueryHandler(market_price_confirm, pattern=r'^mktp_confirm$')
market_cancel_new_handler = CallbackQueryHandler(market_cancel_new, pattern=r'^market_cancel_new$')


from handlers.market_sell import open_sell_menu
market_sell_handler = CallbackQueryHandler(open_sell_menu, pattern=r'^market_sell(:(\d+))?$')
