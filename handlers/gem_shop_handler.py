# handlers/gem_shop_handler.py

import logging
from typing import Dict, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler
from modules.player.core import clear_player_cache
# Importe tudo que é necessário
from modules import player_manager, game_data
from modules.player.premium import PremiumManager
from modules import file_id_manager

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Helpers e Configurações Gerais
# ----------------------------------------------------------------------

def _get_gems(pdata: dict) -> int:
    return int(pdata.get("gems", 0))

def _set_gems(pdata: dict, value: int):
    pdata["gems"] = max(0, int(value))

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except Exception: pass
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

async def _send_with_media(chat_id: int, context: ContextTypes.DEFAULT_TYPE, caption: str, kb: InlineKeyboardMarkup, media_keys: List[str]):
    """
    Tenta enviar uma mensagem com mídia usando uma lista de chaves.
    Se falhar, envia como texto simples.
    """
    media_sent = False
    for key in media_keys:
        # Tenta obter dados da mídia usando a chave
        # <<< VERIFICA se 'file_id_manager' é o nome correto que importaste >>>
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
                logger.warning(f"Falha ao enviar mídia com chave '{key}' (ID: {fid}, Tipo: {ftype}). Erro: {e}. Tentando a próxima chave.")
                continue 
    
    if not media_sent:
        logger.info(f"Nenhuma mídia válida encontrada para as chaves {media_keys}. Enviando como texto.")
        await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=kb, parse_mode="HTML")

async def gem_shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe o menu principal da Loja de Gemas com as categorias (AGORA COM MÍDIA)."""
    q = update.callback_query
    
    if q:
        await q.answer()
        user_id = q.from_user.id
        chat_id = q.message.chat.id # Pega chat_id da mensagem original da query
        try:
            # Tenta apagar a mensagem anterior se veio de um botão
            await q.delete_message()
        except Exception:
            pass # Ignora se falhar
    else: # Se chamado via /gemas (não tem query)
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id # Pega chat_id do update da mensagem

    # Carrega dados do jogador (Já estava correto com await)
    pdata = await player_manager.get_player_data(user_id)
    current_gems = _get_gems(pdata) 

    # Texto da legenda (caption)
    caption = (
        "💎 <b>Loja de Gemas</b>\n\n"
        "Bem-vindo, aventureiro! Use suas gemas com sabedoria.\n\n"
        f"Seu saldo: <b>{current_gems}</b> 💎\n\n"
        "O que você deseja ver?"
    )

    # Teclado (keyboard)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Comprar Itens de Evolução", callback_data="gem_shop_items")],
        [InlineKeyboardButton("⭐ Comprar Planos Premium", callback_data="gem_shop_premium")],
        [InlineKeyboardButton("⬅️ Voltar ao Mercado", callback_data="market")] 
    ])

    # <<< NOVA LÓGICA DE MÍDIA AQUI >>>
    # Define as chaves de mídia a tentar, por ordem de preferência
    media_keys = ["loja_gemas", "gem_store", "premium_shop_img", "market"] 
    
    # Chama a função _send_with_media para enviar a mensagem com a mídia
    await _send_with_media(chat_id, context, caption, kb, media_keys)

#
# >>> FIM DO CÓDIGO MODIFICADO (gem_shop_menu) <<<
#
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

# -- Funções Auxiliares de Itens --
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
    """Mostra a interface de compra de itens."""
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id

    st = _item_state(context) # Síncrono
    base_id, qty = st["base_id"], st["qty"]
    # <<< CORREÇÃO 2: Adiciona await >>>
    pdata = await player_manager.get_player_data(user_id)
    gems_now = _get_gems(pdata) # Síncrono

    text = (f"💎 <b>Loja de Itens</b>\n\n"
            f"Gemas: <b>{gems_now}</b> 💎\n\n"
            f"Selecionado: <b>{_item_label_for(base_id)}</b> — {_item_price_for(base_id)} 💎/un") # Síncrono

    # Construção do teclado (síncrona)
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
        InlineKeyboardButton(f"Qtd: {qty}", callback_data="noop"), # 'noop' assumido como callback que não faz nada
        InlineKeyboardButton("➕", callback_data="gem_item_qty_plus"),
    ]
    actions = [
        [InlineKeyboardButton("🛒 Comprar", callback_data="gem_item_buy")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="gem_shop")]
    ]
    kb = InlineKeyboardMarkup(item_buttons + [qty_row] + actions)
    await _safe_edit_or_send(q, context, q.message.chat_id, text, kb) # Já usa await

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

    st = _item_state(context) # Síncrono
    base_id, qty = st["base_id"], st["qty"]
    total_price = _item_price_for(base_id) * qty # Síncrono

    # <<< CORREÇÃO 3: Adiciona await >>>
    pdata = await player_manager.get_player_data(user_id)

    # Verificação síncrona
    if _get_gems(pdata) < total_price:
        await q.answer("Gemas insuficientes.", show_alert=True); return

    # Modificações síncronas no pdata
    _set_gems(pdata, _get_gems(pdata) - total_price)
    player_manager.add_item_to_inventory(pdata, base_id, qty)

    # <<< CORREÇÃO 4: Adiciona await >>>
    await player_manager.save_player_data(user_id, pdata)

    # Usa edit_message_text diretamente pois sabemos que veio de um callback
    await q.edit_message_text(
        f"✅ Você comprou {qty}× {_item_label_for(base_id)} por {total_price} 💎.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="gem_shop_items")]])
    )

# ----------------------------------------------------------------------
# --- SEÇÃO 2: COMPRA DE PLANOS PREMIUM (Nosso código anterior) ---
# ----------------------------------------------------------------------

async def gem_shop_premium_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a interface de compra de planos premium."""
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id

    # <<< CORREÇÃO 5: Adiciona await >>>
    pdata = await player_manager.get_player_data(user_id)
    current_gems = _get_gems(pdata) # Síncrono

    text = (f"⭐ <b>Loja de Planos Premium</b>\n\n"
            f"Seu saldo: <b>{current_gems}</b> 💎\n\n"
            "Selecione um plano para comprar:")

    # Construção síncrona do teclado
    kb_rows = []
    # Assumindo que PREMIUM_PLANS_FOR_SALE é carregado sincronamente
    for plan_id, plan in game_data.PREMIUM_PLANS_FOR_SALE.items():
        btn_text = f"{plan['name']} - {plan['price']} 💎"
        kb_rows.append([InlineKeyboardButton(btn_text, callback_data=f"gem_prem_confirm:{plan_id}")])

    kb_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="gem_shop")])
    await _safe_edit_or_send(q, context, q.message.chat_id, text, InlineKeyboardMarkup(kb_rows)) # Já usa await

async def gem_shop_premium_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tela de confirmação para compra de plano."""
    q = update.callback_query
    await q.answer()
    plan_id = q.data.split(":")[1]
    plan = game_data.PREMIUM_PLANS_FOR_SALE.get(plan_id)
    if not plan: return

    text = (f"Confirmar a compra de:\n\n<b>{plan['name']}</b>\n"
            f"<i>{plan['description']}</i>\n\nCusto: <b>{plan['price']} 💎</b>")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirmar", callback_data=f"gem_prem_execute:{plan_id}")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="gem_shop_premium")]
    ])
    await _safe_edit_or_send(q, context, q.message.chat_id, text, kb)

async def gem_shop_premium_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Executa a compra do plano."""
    q = update.callback_query
    user_id = q.from_user.id
    plan_id = q.data.split(":")[1]
    plan = game_data.PREMIUM_PLANS_FOR_SALE.get(plan_id) # Síncrono
    if not plan:
        await q.answer("Plano inválido.", show_alert=True) # Adiciona feedback
        return

    # <<< CORREÇÃO 6: Adiciona await >>>
    pdata = await player_manager.get_player_data(user_id)

    # Verificação síncrona
    if _get_gems(pdata) < plan['price']:
        await q.answer("Gemas insuficientes.", show_alert=True); return

    await q.answer("Processando...") # Já usa await

    # Modificações síncronas no pdata
    _set_gems(pdata, _get_gems(pdata) - plan['price'])
    premium = PremiumManager(pdata) # Síncrono
    premium.grant_days(tier=plan['tier'], days=plan['days']) # Síncrono

    # <<< CORREÇÃO 7: Adiciona await >>>
    await player_manager.save_player_data(user_id, premium.player_data) # Usa pdata modificado

    clear_player_cache(user_id) # Assumindo síncrono

    await _safe_edit_or_send(q, context, q.message.chat_id, # Já usa await
        f"✅ Compra concluída!\n\nVocê adquiriu o <b>{plan['name']}</b>.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="gem_shop_premium")]])
    )
# ----------------------------------------------------------------------
# --- EXPORTS DE HANDLERS (TODOS JUNTOS) ---
# ----------------------------------------------------------------------
gem_shop_command_handler = CommandHandler("gemas", gem_shop_menu)

# Menu Principal
gem_shop_menu_handler = CallbackQueryHandler(gem_shop_menu, pattern=r'^gem_shop$')

# Handlers da Loja de Itens
gem_shop_items_handler = CallbackQueryHandler(gem_shop_items_menu, pattern=r'^gem_shop_items$')
gem_item_pick_handler = CallbackQueryHandler(gem_item_pick, pattern=r'^gem_item_pick_')
gem_item_qty_handler = CallbackQueryHandler(gem_item_qty, pattern=r'^(gem_item_qty_minus|gem_item_qty_plus)$')
gem_item_buy_handler = CallbackQueryHandler(gem_item_buy, pattern=r'^gem_item_buy$')

# Handlers da Loja de Planos Premium
gem_shop_premium_handler = CallbackQueryHandler(gem_shop_premium_menu, pattern=r'^gem_shop_premium$')
gem_prem_confirm_handler = CallbackQueryHandler(gem_shop_premium_confirm, pattern=r'^gem_prem_confirm:')
gem_prem_execute_handler = CallbackQueryHandler(gem_shop_premium_execute, pattern=r'^gem_prem_execute:')