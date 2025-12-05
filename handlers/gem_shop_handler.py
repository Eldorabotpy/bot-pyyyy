# handlers/gem_shop_handler.py
# (VERSÃO FINAL 3.0: Com Notificação de Hype no Grupo)

import logging
from typing import Dict, List
from datetime import datetime, timedelta, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler
from modules.player.core import clear_player_cache
from modules import player_manager, game_data
from modules import file_id_manager

logger = logging.getLogger(__name__)

# CONFIGURAÇÃO DE LOG / NOTIFICAÇÃO
LOG_GROUP_ID = -1002881364171
LOG_TOPIC_ID = 24475

# ----------------------------------------------------------------------
# Helpers e Configurações Gerais
# ----------------------------------------------------------------------

def _get_gems(pdata: dict) -> int:
    return int(pdata.get("gems", 0))

def _set_gems(pdata: dict, value: int):
    pdata["gems"] = max(0, int(value))

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    if query:
        try:
            await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
            return
        except Exception:
            try:
                await query.delete_message()
            except Exception:
                pass
    
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

async def _send_with_media(chat_id: int, context: ContextTypes.DEFAULT_TYPE, caption: str, kb: InlineKeyboardMarkup, media_keys: List[str]):
    media_sent = False
    for key in media_keys:
        fd = file_id_manager.get_file_data(key) 
        
        if fd and fd.get("id"):
            fid, ftype = fd["id"], fd.get("type", "photo").lower() 
            try:
                if ftype in ("video", "animation"): 
                    await context.bot.send_animation(chat_id=chat_id, animation=fid, caption=caption, reply_markup=kb, parse_mode="HTML")
                else: 
                    await context.bot.send_photo(chat_id=chat_id, photo=fid, caption=caption, reply_markup=kb, parse_mode="HTML")
                media_sent = True 
                break 
            except Exception as e:
                continue 
    
    if not media_sent:
        await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=kb, parse_mode="HTML")

async def gem_shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    
    if q:
        await q.answer()
        user_id = q.from_user.id
        chat_id = q.message.chat.id 
        try:
            await q.delete_message()
        except Exception: pass 
    else: 
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id 

    pdata = await player_manager.get_player_data(user_id)
    current_gems = _get_gems(pdata) 

    caption = (
        "💎 <b>Loja de Gemas</b>\n\n"
        "Bem-vindo, aventureiro! Use suas gemas com sabedoria.\n\n"
        f"Seu saldo: <b>{current_gems}</b> 💎\n\n"
        "O que você deseja ver?"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Comprar Itens de Evolução", callback_data="gem_shop_items")],
        [InlineKeyboardButton("⭐ Comprar Planos Premium", callback_data="gem_shop_premium")],
        [InlineKeyboardButton("⬅️ Voltar ao Mercado", callback_data="market")] 
    ])

    media_keys = ["loja_gemas", "gem_store", "premium_shop_img", "market"] 
    await _send_with_media(chat_id, context, caption, kb, media_keys)

# -- Configuração dos Itens --
EVOLUTION_ITEMS = [
    "cristal_de_abertura", "emblema_guerreiro", "essencia_guardia", "essencia_furia",
    "selo_sagrado", "essencia_luz", "emblema_berserker", "totem_ancestral",
    "emblema_cacador", "essencia_precisao", "marca_predador", "essencia_fera",
    "emblema_monge", "reliquia_mistica", "essencia_ki", "emblema_mago",
    "essencia_arcana", "essencia_elemental", "grimorio_arcano", "emblema_bardo",
    "essencia_harmonia", "essencia_encanto", "batuta_maestria", "emblema_assassino",
    "essencia_sombra", "essencia_letal", "manto_eterno", "emblema_samurai",
    "essencia_corte", "essencia_disciplina", "lamina_sagrada",
]
DEFAULT_GEM_PRICE = 10
GEM_SHOP_PRICES: Dict[str, int] = { }

def _item_label_for(base_id: str) -> str:
    info = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}
    name = info.get("display_name", base_id)
    emoji = info.get("emoji", "")
    return f"{emoji}{name}" if emoji else name

def _item_price_for(base_id: str) -> int:
    return int(GEM_SHOP_PRICES.get(base_id, DEFAULT_GEM_PRICE))

def _item_state(context: ContextTypes.DEFAULT_TYPE) -> dict:
    st = context.user_data.get("gemshop_item", {})
    if not st:
        st = {"base_id": EVOLUTION_ITEMS[0], "qty": 1}
        context.user_data["gemshop_item"] = st
    return st

# -- Handlers da Loja de Itens --
async def gem_shop_items_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = q.message.chat.id

    st = _item_state(context) 
    base_id, qty = st["base_id"], st["qty"]
    
    pdata = await player_manager.get_player_data(user_id)
    gems_now = _get_gems(pdata) 

    text = (f"💎 <b>Loja de Itens</b>\n\n"
            f"Gemas: <b>{gems_now}</b> 💎\n\n"
            f"Selecionado: <b>{_item_label_for(base_id)}</b> — {_item_price_for(base_id)} 💎/un") 

    row: List[InlineKeyboardButton] = []
    item_buttons: List[List[InlineKeyboardButton]] = []
    for i, item_id in enumerate(EVOLUTION_ITEMS, 1):
        prefix = "✅ " if item_id == base_id else ""
        row.append(InlineKeyboardButton(f"{prefix}{_item_label_for(item_id)}", callback_data=f"gem_item_pick_{item_id}"))
        if i % 2 == 0:
            item_buttons.append(row); row = []
    if row: item_buttons.append(row)

    qty_row = [
        InlineKeyboardButton("➖", callback_data="gem_item_qty_minus"),
        InlineKeyboardButton(f"Qtd: {qty}", callback_data="noop"), 
        InlineKeyboardButton("➕", callback_data="gem_item_qty_plus"),
    ]
    actions = [
        [InlineKeyboardButton("🛒 Comprar", callback_data="gem_item_buy")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="gem_shop")]
    ]
    kb = InlineKeyboardMarkup(item_buttons + [qty_row] + actions)
    await _safe_edit_or_send(q, context, chat_id, text, kb) 

async def gem_item_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    st = _item_state(context)
    st["base_id"] = q.data.replace("gem_item_pick_", "")
    context.user_data["gemshop_item"] = st
    await gem_shop_items_menu(update, context)

async def gem_item_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    st = _item_state(context)
    qty = st.get("qty", 1)
    if q.data == "gem_item_qty_minus": st["qty"] = max(1, qty - 1)
    elif q.data == "gem_item_qty_plus": st["qty"] = qty + 1
    context.user_data["gemshop_item"] = st
    await gem_shop_items_menu(update, context)
    
async def gem_item_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = q.message.chat.id

    st = _item_state(context) 
    base_id, qty = st["base_id"], st["qty"]
    total_price = _item_price_for(base_id) * qty 

    pdata = await player_manager.get_player_data(user_id)

    if _get_gems(pdata) < total_price:
        await q.answer("Gemas insuficientes.", show_alert=True); return

    _set_gems(pdata, _get_gems(pdata) - total_price)
    player_manager.add_item_to_inventory(pdata, base_id, qty)

    await player_manager.save_player_data(user_id, pdata)

    await _safe_edit_or_send(
        q, context, chat_id,
        f"✅ Você comprou {qty}× {_item_label_for(base_id)} por {total_price} 💎.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="gem_shop_items")]])
    )

# ----------------------------------------------------------------------
# --- SEÇÃO 2: COMPRA DE PLANOS PREMIUM ---
# ----------------------------------------------------------------------

async def gem_shop_premium_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = q.message.chat.id

    pdata = await player_manager.get_player_data(user_id)
    current_gems = _get_gems(pdata) 

    text = (f"⭐ <b>Loja de Planos Premium</b>\n\n"
            f"Seu saldo: <b>{current_gems}</b> 💎\n\n"
            "Selecione um plano para comprar:")

    kb_rows = []
    for plan_id, plan in game_data.PREMIUM_PLANS_FOR_SALE.items():
        btn_text = f"{plan['name']} - {plan['price']} 💎"
        kb_rows.append([InlineKeyboardButton(btn_text, callback_data=f"gem_prem_confirm:{plan_id}")])

    kb_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="gem_shop")])
    await _safe_edit_or_send(q, context, chat_id, text, InlineKeyboardMarkup(kb_rows)) 

async def gem_shop_premium_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = q.message.chat.id
    plan_id = q.data.split(":")[1]
    plan = game_data.PREMIUM_PLANS_FOR_SALE.get(plan_id)
    if not plan: return

    text = (f"Confirmar a compra de:\n\n<b>{plan['name']}</b>\n"
            f"<i>{plan['description']}</i>\n\nCusto: <b>{plan['price']} 💎</b>")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirmar", callback_data=f"gem_prem_execute:{plan_id}")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="gem_shop_premium")]
    ])
    await _safe_edit_or_send(q, context, chat_id, text, kb)

async def gem_shop_premium_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Executa a compra do plano e NOTIFICA O GRUPO."""
    q = update.callback_query
    user_id = q.from_user.id
    chat_id = q.message.chat.id
    plan_id = q.data.split(":")[1]
    plan = game_data.PREMIUM_PLANS_FOR_SALE.get(plan_id) 
    if not plan:
        await q.answer("Plano inválido.", show_alert=True) 
        return

    pdata = await player_manager.get_player_data(user_id)

    if _get_gems(pdata) < plan['price']:
        await q.answer("Gemas insuficientes.", show_alert=True); return

    await q.answer("Processando...") 

    # 1. Desconta Gemas
    _set_gems(pdata, _get_gems(pdata) - plan['price'])

    # 2. Lógica Manual de Premium
    now = datetime.now(timezone.utc)
    current_tier = pdata.get("premium_tier", "free")
    current_exp_str = pdata.get("premium_expiration")
    
    new_tier = plan['tier']
    days_to_add = int(plan['days'])

    start_date = now
    if current_exp_str and current_tier != "free":
        try:
            current_exp = datetime.fromisoformat(current_exp_str)
            if current_exp > now:
                start_date = current_exp
        except ValueError:
            pass

    new_expiration = start_date + timedelta(days=days_to_add)

    pdata["premium_tier"] = new_tier
    pdata["premium_expiration"] = new_expiration.isoformat()

    # 3. Salva no Banco de Dados
    await player_manager.save_player_data(user_id, pdata) 
    clear_player_cache(user_id) 

    # 4. Mensagem para o Jogador (Privado)
    fmt_date = new_expiration.strftime('%d/%m/%Y')
    await _safe_edit_or_send(q, context, chat_id, 
        f"✅ Compra concluída!\n\n"
        f"👑 <b>Novo Plano:</b> {plan['name']}\n"
        f"📅 <b>Válido até:</b> {fmt_date}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="gem_shop_premium")]])
    )

    # 5. NOTIFICAÇÃO DE HYPE NO GRUPO (NOVA PARTE)
    try:
        char_name = pdata.get("character_name", q.from_user.first_name)
        
        hype_msg = (
            "🎉 <b>UM NOVO MEMBRO DE ELITE SURGIU!</b> 🎉\n\n"
            f"O aventureiro <b>{char_name}</b> acaba de adquirir o plano:\n"
            f"🌟 <b>{plan['name']}</b> 🌟\n\n"
            f"<i>Agora ele possui bônus de XP, Drop e Vantagens Exclusivas!</i>\n\n"
            "💎 Quer se tornar VIP também? Digite /gemas ou vá ao Mercado!"
        )

        await context.bot.send_message(
            chat_id=LOG_GROUP_ID,
            message_thread_id=LOG_TOPIC_ID,
            text=hype_msg,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"Falha ao enviar notificação de VIP no grupo: {e}")

# ----------------------------------------------------------------------
# --- EXPORTS DE HANDLERS ---
# ----------------------------------------------------------------------
gem_shop_command_handler = CommandHandler("gemas", gem_shop_menu)

gem_shop_menu_handler = CallbackQueryHandler(gem_shop_menu, pattern=r'^gem_shop$')

gem_shop_items_handler = CallbackQueryHandler(gem_shop_items_menu, pattern=r'^gem_shop_items$')
gem_item_pick_handler = CallbackQueryHandler(gem_item_pick, pattern=r'^gem_item_pick_')
gem_item_qty_handler = CallbackQueryHandler(gem_item_qty, pattern=r'^(gem_item_qty_minus|gem_item_qty_plus)$')
gem_item_buy_handler = CallbackQueryHandler(gem_item_buy, pattern=r'^gem_item_buy$')

gem_shop_premium_handler = CallbackQueryHandler(gem_shop_premium_menu, pattern=r'^gem_shop_premium$')
gem_prem_confirm_handler = CallbackQueryHandler(gem_shop_premium_confirm, pattern=r'^gem_prem_confirm:')
gem_prem_execute_handler = CallbackQueryHandler(gem_shop_premium_execute, pattern=r'^gem_prem_execute:')