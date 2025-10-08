# handlers/admin/generate_equip.py (Versão Final e Completa)

import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    CommandHandler,
)
from modules import player_manager, game_data, item_factory
from handlers.admin.utils import ensure_admin

# --- Estados da Conversa ---
(SELECT_BASE, SELECT_RARITY, ASK_ATTRIBUTES, ASK_TIER, ASK_DURABILITY, ASK_PLAYER, CONFIRM) = range(7)
ITEMS_PER_PAGE = 10

# --- Funções da Conversa ---

async def start_generation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Passo 1: Mostra a lista de equipamentos base."""
    if not await ensure_admin(update): return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    page = 1
    if ":" in query.data:
        try: page = int(query.data.split(":")[1])
        except (ValueError, IndexError): page = 1
    base_equips = item_factory.available_item_bases()
    start_index = (page - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    items_on_page = base_equips[start_index:end_index]
    keyboard = []
    for item_id, display_name in items_on_page:
        keyboard.append([InlineKeyboardButton(display_name, callback_data=f"gen_base:{item_id}")])
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"admin_generate_equip:{page-1}"))
    total_pages = (len(base_equips) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Próximo ➡️", callback_data=f"admin_generate_equip:{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="gen_cancel")])
    text = f"🛠️ **Reconstrutor de Itens** (Pág {page}/{total_pages})\n\n[Passo 1/7] Escolha um item base:"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return SELECT_BASE

async def receive_base_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Passo 2: Recebe o item base e pede a raridade."""
    query = update.callback_query
    await query.answer()
    base_id = query.data.split(":")[1]
    context.user_data['gen_item'] = {"base_id": base_id}
    rarities = item_factory.available_rarities()
    keyboard = []
    row = []
    for rarity in rarities:
        row.append(InlineKeyboardButton(rarity.capitalize(), callback_data=f"gen_rarity:{rarity}"))
        if len(row) == 3:
            keyboard.append(row); row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("↩️ Voltar", callback_data="admin_generate_equip")])
    await query.edit_message_text("[Passo 2/7] Escolha a **raridade**:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return SELECT_RARITY

async def receive_rarity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Passo 3: Recebe a raridade e pede os atributos."""
    query = update.callback_query
    await query.answer()
    rarity = query.data.split(":")[1]
    context.user_data['gen_item']['rarity'] = rarity
    text = (
        f"[Passo 3/7] Envie os **atributos (bónus)** do item.\n\n"
        f"**Formato:** `nome:valor, nome:valor`\n"
        f"**Exemplo:** `dmg:10, hp:25, luck:5`\n\n"
        f"Nomes válidos: `dmg`, `hp`, `defense`, `initiative`, `luck`.\n"
        f"Se o item não tiver bónus, envie a palavra `nenhum`."
    )
    await query.edit_message_text(text, parse_mode="HTML")
    return ASK_ATTRIBUTES

async def receive_attributes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Passo 4: Recebe os atributos, soma os duplicados e pede o Tier."""
    text = update.message.text.lower()
    enchants = {}
    
    if text != 'nenhum':
        try:
            parts = [p.strip() for p in text.split(',')]
            for part in parts:
                stat, value_str = part.split(':')
                stat = stat.strip()
                value = int(value_str)
                
                if stat not in ['dmg', 'hp', 'defense', 'initiative', 'luck']:
                    raise ValueError(f"Atributo '{stat}' inválido.")
                
                # ✅ LÓGICA CORRIGIDA: Soma os valores se o atributo for repetido
                if stat in enchants:
                    enchants[stat]["value"] += value
                else:
                    enchants[stat] = {"value": value}

        except Exception as e:
            await update.message.reply_text(f"❌ Formato inválido. Tente novamente.\nExemplo: `dmg:10, hp:25`\nErro: {e}")
            return ASK_ATTRIBUTES
            
    context.user_data['gen_item']['enchantments'] = enchants
    await update.message.reply_text("[Passo 4/7] Qual o **Tier** do item? (Envie um número, ex: `3`)")
    return ASK_TIER

async def receive_tier(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Passo 5: Recebe o Tier e pede a Durabilidade."""
    try:
        tier = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Tier inválido. Envie apenas um número.")
        return ASK_TIER
        
    context.user_data['gen_item']['tier'] = tier
    await update.message.reply_text("[Passo 5/7] Qual a **Durabilidade** do item?\nFormato: `atual/maxima` (ex: `80/100`)")
    return ASK_DURABILITY

async def receive_durability(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Passo 6: Recebe a durabilidade e pede o jogador."""
    try:
        current, maximum = map(int, update.message.text.split('/'))
    except Exception:
        await update.message.reply_text("❌ Formato inválido. Use `atual/maxima`, ex: `80/100`.")
        return ASK_DURABILITY
        
    context.user_data['gen_item']['durability'] = [current, maximum]
    await update.message.reply_text("[Passo 6/7] Para qual jogador devemos entregar este item?\nEnvie o **User ID** ou o **nome exato do personagem**.")
    return ASK_PLAYER

async def receive_player_and_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Passo 7: Recebe o jogador e mostra a confirmação final com o emoji correto."""
    target_input = update.message.text.strip()
    
    try:
        user_id = int(target_input)
        pdata = player_manager.get_player_data(user_id)
    except ValueError:
        found = player_manager.find_player_by_name(target_input)
        if found:
            user_id, pdata = found
        else:
            user_id, pdata = None, None

    if not pdata:
        await update.message.reply_text("❌ Jogador não encontrado. Tente novamente.")
        return ASK_PLAYER
    
    context.user_data['gen_target_id'] = user_id
    
    item_instance = context.user_data['gen_item']
    base_id = item_instance.get("base_id")

    # ✅ CORREÇÃO: Encontra a classe do ITEM, não do jogador.
    base_item_info = game_data.ITEMS_DATA.get(base_id, {})
    # Pega na primeira classe da lista de requisitos (ex: ["cacador"])
    item_class_req = (base_item_info.get("class_req") or [None])[0]
    
    # Usa a classe do ITEM para "desenhar" a pré-visualização.
    preview_line = item_factory.render_item_line(item_instance, item_class_req)
    
    summary_text = (
        f"<b>Confirmação Final:</b>\n\n"
        f"Gerar e entregar este item para <b>{pdata.get('character_name')}</b>?\n\n"
        f"<code>{preview_line}</code>"
    )
    
    keyboard = [[
        InlineKeyboardButton("✅ Sim, gerar e entregar", callback_data="gen_confirm_yes"),
        InlineKeyboardButton("❌ Não, cancelar", callback_data="gen_cancel")
    ]]
    
    await update.message.reply_text(summary_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    
    return CONFIRM

async def dispatch_generation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Executa a entrega do item construído manualmente."""
    query = update.callback_query
    await query.answer()

    user_id = context.user_data['gen_target_id']
    item_to_give = context.user_data['gen_item']
    
    try:
        pdata = player_manager.get_player_data(user_id)
        if not pdata:
            raise ValueError("Jogador alvo não encontrado.")

        player_manager.add_unique_item(pdata, item_to_give)
        player_manager.save_player_data(user_id, pdata)
        
        # ✅ CORREÇÃO: Usa a classe do ITEM para a mensagem final.
        base_id = item_to_give.get("base_id")
        base_item_info = game_data.ITEMS_DATA.get(base_id, {})
        item_class_req = (base_item_info.get("class_req") or [None])[0]
        
        rendered_line = item_factory.render_item_line(item_to_give, item_class_req)
        player_name = pdata.get("character_name")
        
        await query.edit_message_text(f"✅ Item reconstruído e entregue com sucesso para {player_name}!\n\n<code>{rendered_line}</code>", parse_mode="HTML")
    except Exception as e:
        await query.edit_message_text(f"❌ Ocorreu um erro: {e}")

    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a conversa."""
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Operação cancelada.")
    else:
        await update.message.reply_text("Operação cancelada.")
        
    context.user_data.clear()
    return ConversationHandler.END
    
# --- O Handler da Conversa ---
generate_equip_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_generation, pattern=r"^admin_generate_equip(:.*)?$")],
    states={
        SELECT_BASE: [
            CallbackQueryHandler(receive_base_item, pattern=r"^gen_base:.*"),
            CallbackQueryHandler(start_generation, pattern=r"^admin_generate_equip:.*")
        ],
        SELECT_RARITY: [
            CallbackQueryHandler(receive_rarity, pattern=r"^gen_rarity:.*"),
            CallbackQueryHandler(start_generation, pattern=r"^admin_generate_equip")
        ],
        ASK_ATTRIBUTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_attributes)],
        ASK_TIER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_tier)],
        ASK_DURABILITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_durability)],
        ASK_PLAYER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_player_and_confirm)],
        CONFIRM: [
            CallbackQueryHandler(dispatch_generation, pattern=r"^gen_confirm_yes$"),
            CallbackQueryHandler(cancel, pattern=r"^gen_confirm_no$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancelar", cancel),
        CallbackQueryHandler(cancel, pattern=r"^gen_cancel$")
    ],
)