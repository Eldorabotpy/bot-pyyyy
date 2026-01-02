# handlers/admin/sell_gems.py
# (VERSÃO BLINDADA: Sistema Novo + Busca Async Otimizada)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, ConversationHandler, 
    MessageHandler, filters, CommandHandler
)
from bson import ObjectId

# [CORREÇÃO] Removemos players_collection. Usamos apenas abstrações seguras.
from modules.player.core import get_player_data, save_player_data
from modules.player.inventory import add_gems
from modules.player.queries import find_player_by_name
from handlers.admin.utils import ensure_admin

logger = logging.getLogger(__name__)

(ASK_TARGET_PLAYER, ASK_QUANTITY, CONFIRM_GRANT) = range(3)

# [NOVA FUNÇÃO] Substitui _blocking_search por uma busca async segura
async def smart_search_player(term: str):
    """
    Busca inteligente que aceita ID (Int/ObjectId) ou Nome.
    Usa o sistema híbrido (Users > Players) sem acessar collections diretamente.
    """
    term = str(term).strip()
    
    # 1. Tenta buscar por ID (ObjectId ou Int)
    if ObjectId.is_valid(term) or term.isdigit():
        # get_player_data já lida com o roteamento (Users vs Players)
        # Se for dígito, ele trata como int legado. Se ObjectId, trata como novo.
        uid_arg = ObjectId(term) if ObjectId.is_valid(term) else int(term)
        pdata = await get_player_data(uid_arg)
        if pdata:
            # Retorna o ID real do documento encontrado
            return pdata.get("_id")

    # 2. Tenta buscar por Nome (Usa a query otimizada do módulo queries)
    # Retorna tupla (uid, pdata) ou None
    found = await find_player_by_name(term)
    if found:
        return found[0] # Retorna o UID

    return None

async def start_sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update): return ConversationHandler.END
    await update.callback_query.answer()
    
    # Limpa dados anteriores
    context.user_data.clear()
    
    await update.callback_query.edit_message_text(
        "💎 <b>Gerenciador de Gemas (Sistema Novo)</b>\n\n"
        "Mande o <b>NOME</b> ou <b>ID</b> do jogador.\n"
        "<i>O sistema buscará automaticamente na base nova e antiga.</i>",
        parse_mode="HTML"
    )
    return ASK_TARGET_PLAYER

async def receive_target_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Captura texto enviado
    if update.message and update.message.text:
        txt = update.message.text
    else:
        await update.message.reply_text("Por favor, envie apenas texto.")
        return ASK_TARGET_PLAYER

    status = await update.message.reply_text(f"🔍 Buscando: {txt}...")
    
    try:
        # [CORREÇÃO] Chamada async direta (sem threads, pois usamos motor/asyncio nativo nas queries)
        uid = await smart_search_player(txt)

        if not uid:
            await status.edit_text(f"❌ Jogador '{txt}' não encontrado.")
            return ASK_TARGET_PLAYER

        pdata = await get_player_data(uid)
        if not pdata:
            await status.edit_text("❌ Erro ao carregar dados do jogador (Dados corrompidos?).")
            return ASK_TARGET_PLAYER

        context.user_data['gem_target_id'] = uid
        context.user_data['gem_target_name'] = pdata.get('character_name', str(uid))

        # Formata o ID para exibição (se for ObjectId, converte para str)
        display_id = str(uid)
        
        await status.edit_text(
            f"✅ ALVO ENCONTRADO:\n"
            f"👤 <b>Nome:</b> {context.user_data['gem_target_name']}\n"
            f"🆔 <b>ID:</b> <code>{display_id}</code>\n\n"
            "Digite a <b>QUANTIDADE</b> de gemas a enviar:",
            parse_mode="HTML"
        )
        return ASK_QUANTITY

    except Exception as e:
        logger.error("Erro crítico em sell_gems", exc_info=True)
        await status.edit_text(f"ERRO INTERNO: {e}")
        return ConversationHandler.END

async def receive_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        qty = int(update.message.text.strip())
        if qty <= 0: raise ValueError
        context.user_data['gem_quantity'] = qty
        
        name = context.user_data['gem_target_name']
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ CONFIRMAR ENVIO", callback_data="gem_confirm_yes")],
            [InlineKeyboardButton("❌ CANCELAR", callback_data="gem_confirm_no")]
        ])
        await update.message.reply_text(
            f"💎 <b>Confirmação de Transferência</b>\n\n"
            f"Enviar <b>{qty}</b> gemas para <b>{name}</b>?",
            reply_markup=kb,
            parse_mode="HTML"
        )
        return CONFIRM_GRANT
    except:
        await update.message.reply_text("⚠️ Número inválido. Digite um valor maior que zero.")
        return ASK_QUANTITY

async def dispatch_grant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    if query.data == "gem_confirm_no":
        await query.edit_message_text("❌ Operação cancelada.")
        context.user_data.clear()
        return ConversationHandler.END

    uid = context.user_data['gem_target_id']
    qty = context.user_data['gem_quantity']
    name = context.user_data['gem_target_name']
    
    pdata = await get_player_data(uid)
    if pdata:
        # Adiciona Gemas
        add_gems(pdata, qty)
        await save_player_data(uid, pdata)
        
        # Feedback para o Admin
        await query.edit_message_text(
            f"✅ <b>SUCESSO!</b>\n"
            f"<code>{qty}</code> gemas foram creditadas para <b>{name}</b>.", 
            parse_mode="HTML"
        )
        
        # --- NOTIFICAÇÃO RPG PARA O JOGADOR ---
        try:
            msg_rpg = (
                "👑 ⚜️ <b>𝐃𝐄𝐂𝐑𝐄𝐓𝐎 𝐃𝐄 𝐄𝐋𝐃𝐎𝐑𝐀</b> ⚜️ 👑\n"
                "═════════════════════════\n"
                "<i>Por ordem superior, recursos especiais\n"
                "foram alocados para sua jornada.</i>\n\n"
                f"💎 <b>𝐐𝐮𝐚𝐧𝐭𝐢𝐝𝐚𝐝𝐞:</b> <code>{qty}</code> Gemas\n"
                "📦 <b>𝐒𝐭𝐚𝐭𝐮𝐬:</b> Entregue com Sucesso\n\n"
                "<i>Faça bom uso destas riquezas.</i>\n"
                "═════════════════════════"
            )
            
            # Garante que UID seja compatível com send_message (int ou str)
            target_chat_id = uid
            # Se for ID legado (int), usa direto. Se for ObjectId, precisamos do chat_id ou torcer para o ID ser igual (não é).
            # No sistema novo, 'user_id' pode ser ObjectId. Precisamos do 'last_chat_id' ou 'telegram_id_owner' se disponível.
            
            # Tentativa de notificação inteligente
            if isinstance(uid, ObjectId) or (isinstance(uid, str) and not uid.isdigit()):
                # Tenta pegar o ID do telegram do dono se disponível
                target_chat_id = pdata.get("telegram_id_owner") or pdata.get("last_chat_id")
            
            if target_chat_id:
                await context.bot.send_message(target_chat_id, msg_rpg, parse_mode="HTML")
            else:
                logger.warning(f"Não foi possível notificar {name}: Sem Chat ID.")
                
        except Exception as e:
            logger.warning(f"Falha na notificação do jogador {uid}: {e}")
        # --------------------------------------
        
    else:
        await query.edit_message_text("❌ Erro crítico: Falha ao salvar dados no banco.")
    
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelado.")
    context.user_data.clear()
    return ConversationHandler.END

sell_gems_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_sell, pattern=r"^admin_sell_gems$")],
    states={
        # USANDO FILTERS.ALL para garantir que pegue TUDO
        ASK_TARGET_PLAYER: [MessageHandler(filters.ALL & ~filters.COMMAND, receive_target_player)],
        ASK_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_quantity)],
        CONFIRM_GRANT: [
            CallbackQueryHandler(dispatch_grant, pattern=r"^gem_confirm_yes$"),
            CallbackQueryHandler(dispatch_grant, pattern=r"^gem_confirm_no$"), 
        ],
    },
    fallbacks=[CommandHandler("cancelar", cancel)],
    per_message=False 
)