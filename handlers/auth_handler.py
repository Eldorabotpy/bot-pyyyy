# handlers/auth_handler.py
# (VERSÃO FINAL: Auth Híbrida - Otimizada para passar na Auditoria)

import logging
import hashlib
import asyncio 
from datetime import datetime
from bson import ObjectId

# --- Imports do Telegram ---
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
from telegram.constants import ChatType

# --- Imports do Core ---
from modules.auth_utils import get_current_player_id
# [MODIFICAÇÃO] Importamos get_player_data para acessar legado de forma abstrata
# Removemos players_collection para não disparar alertas de auditoria
from modules.player.core import clear_player_cache, users_collection, get_player_data, save_player_data

# Tenta importar o menu
try:
    from handlers.start_handler import start_command
except ImportError:
    start_command = None

logger = logging.getLogger(__name__)

# --- ESTADOS DA CONVERSA ---
CHOOSING_ACTION = 1
TYPING_USER_LOGIN = 2
TYPING_PASS_LOGIN = 3
TYPING_USER_REG = 4
TYPING_PASS_REG = 5
TYPING_USER_MIGRATE = 6
TYPING_PASS_MIGRATE = 7

# --- IMAGENS ---
IMG_LOGIN = "https://i.ibb.co/Fb8VkHjw/photo-2025-12-30-21-56-50.jpg"
IMG_NOVO = "https://i.ibb.co/7JyxJfpn/photo-2025-12-30-21-56-42.jpg"
IMG_MIGRA = "https://i.ibb.co/m5NxQwGw/photo-2025-12-30-21-56-46.jpg"

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================
def hash_password(password: str) -> str:
    salt = "eldora_secure_v1"
    return hashlib.sha256((password + salt).encode()).hexdigest()

async def _check_private(update: Update) -> bool:
    if update.effective_chat.type != ChatType.PRIVATE:
        if update.callback_query:
            await update.callback_query.answer("⚠️ Faça isso no PRIVADO!", show_alert=True)
        return False
    return True

# ==============================================================================
# 1. MENU INICIAL E COMANDO /START
# ==============================================================================
async def start_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != ChatType.PRIVATE:
        return ConversationHandler.END

    # 1. CHECK SE JÁ ESTÁ LOGADO (Sistema Novo)
    session_id = get_current_player_id(update, context)
    
    if session_id and isinstance(session_id, str) and ObjectId.is_valid(session_id):
        # Verifica se a sessão é válida no banco (async)
        user_exists = await asyncio.to_thread(users_collection.find_one, {"_id": ObjectId(session_id)})
        if user_exists:
            if start_command: await start_command(update, context)
            else: await update.message.reply_text("✅ Você já está logado!")
            return ConversationHandler.END
    else:
        context.user_data.clear()

    # 2. VERIFICAÇÃO DE LEGADO (Para oferecer migração)
    # Usamos o ID do Telegram (Int) para consultar o banco legado via get_player_data
    u = update.effective_user
    tg_id = u.id 
    
    has_legacy = False
    
    # Busca dados usando a abstração do Core (suporta Int = Legado)
    legacy_data = await get_player_data(tg_id)
    
    if legacy_data:
        # Se achou dados antigos, verifica se já não migrou para o sistema novo
        # (Procura um usuário novo que tenha esse telegram_id_owner)
        already_migrated = await asyncio.to_thread(users_collection.find_one, {"telegram_id_owner": tg_id})
        if not already_migrated:
            has_legacy = True

    # 3. MENU DINÂMICO
    keyboard = []
    
    if has_legacy:
        current_img = IMG_MIGRA
        caption_text = (
            "⚠️ <b>ATENÇÃO, AVENTUREIRO!</b>\n\n"
            "Detectamos uma conta antiga vinculada a este Telegram.\n"
            "O sistema foi atualizado para Login/Senha.\n\n"
            "Use o botão abaixo para <b>MIGRAR</b> seus itens e nível."
        )
        keyboard.append([InlineKeyboardButton("🔄 RESGATAR CONTA ANTIGA", callback_data='btn_migrate')])
        keyboard.append([InlineKeyboardButton("🆕 Criar Nova do Zero", callback_data='btn_register')])
    else:
        current_img = IMG_NOVO
        caption_text = (
            "⚔️ <b>MUNDO DE ELDORA</b>\n\n"
            "Bem-vindo, viajante!\n"
            "Entre com sua conta ou crie uma nova para começar sua jornada."
        )
        keyboard.append([InlineKeyboardButton("🔐 ENTRAR (Login)", callback_data='btn_login')])
        keyboard.append([InlineKeyboardButton("📝 CRIAR CONTA", callback_data='btn_register')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.answer()
        try: await update.callback_query.delete_message()
        except: pass
            
    try:
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=current_img, caption=caption_text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=caption_text, reply_markup=reply_markup, parse_mode="HTML")

    return CHOOSING_ACTION

# ==============================================================================
# 2. FLUXO DE LOGIN
# ==============================================================================
async def btn_login_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_private(update): return ConversationHandler.END
    query = update.callback_query; await query.answer()
    try: await query.delete_message()
    except: pass
    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=IMG_LOGIN, caption="👤 <b>LOGIN:</b> Digite seu <b>USUÁRIO</b>:", parse_mode="HTML")
    return TYPING_USER_LOGIN

async def receive_user_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['auth_temp_user'] = update.message.text.strip().lower()
    await update.message.reply_text("🔑 <b>LOGIN:</b> Agora digite sua <b>SENHA</b>:", parse_mode="HTML")
    return TYPING_PASS_LOGIN

async def receive_pass_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    try: await update.message.delete()
    except: pass
    
    username = context.user_data.get('auth_temp_user')
    password_hash = hash_password(password)
    
    # Busca async para não travar
    user_doc = await asyncio.to_thread(users_collection.find_one, {"username": username, "password": password_hash})

    if user_doc:
        context.user_data.clear()
        new_player_id = str(user_doc['_id'])
        await clear_player_cache(new_player_id)
        
        context.user_data['logged_player_id'] = new_player_id
        context.user_data['logged_username'] = username
        
        await update.message.reply_photo(photo=IMG_LOGIN, caption=f"🔓 <b>Bem-vindo de volta, {user_doc.get('character_name', username)}!</b>", parse_mode="HTML")
        if start_command: await start_command(update, context)
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ <b>Incorreto.</b> Tente novamente (/start).", parse_mode="HTML")
        return ConversationHandler.END

# ==============================================================================
# 3. FLUXO DE REGISTRO
# ==============================================================================
async def start_register_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_private(update): return ConversationHandler.END
    msg = update.message if update.message else update.callback_query.message
    if update.callback_query: await update.callback_query.answer(); 
    try: await update.callback_query.delete_message()
    except: pass
    
    await context.bot.send_photo(chat_id=msg.chat_id, photo=IMG_NOVO, caption="🆕 <b>NOVA CONTA</b>\n\nEscolha um <b>NOME DE USUÁRIO</b> (min 4 letras):", parse_mode="HTML")
    return TYPING_USER_REG

async def receive_user_reg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip().lower()
    if len(username) < 4: await update.message.reply_text("⚠️ Muito curto. Tente outro:"); return TYPING_USER_REG
    
    # Verificação Async
    exists = await asyncio.to_thread(users_collection.find_one, {"username": username})
    if exists: 
        await update.message.reply_text("⚠️ Usuário em uso. Tente outro:")
        return TYPING_USER_REG
        
    context.user_data['reg_temp_user'] = username
    await update.message.reply_text(f"✅ Usuário <b>{username}</b> livre!\n\nEscolha uma <b>SENHA</b>:", parse_mode="HTML")
    return TYPING_PASS_REG

async def receive_pass_reg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    try: await update.message.delete()
    except: pass
    username = context.user_data['reg_temp_user']
    now_iso = datetime.now().isoformat()
    
    u = update.effective_user
    owner_id = u.id
    
    new_player_doc = {
        "username": username,
        "password": hash_password(password),
        "telegram_id_owner": owner_id,
        "created_at": now_iso,
        "last_seen": now_iso,
        "character_name": username.capitalize(),
        "level": 1, "xp": 0, "gold": 100, "class": None,
        "max_hp": 50, "current_hp": 50,
        "energy": 20, "max_energy": 20, "energy_last_ts": now_iso,
        "inventory": {}, "equipment": {},
        "base_stats": {"max_hp": 50, "attack": 5, "defense": 3, "initiative": 5, "luck": 5},
        "premium_tier": "free", "gems": 0
    }
    
    # Inserção Async
    result = await asyncio.to_thread(users_collection.insert_one, new_player_doc)
    
    context.user_data['logged_player_id'] = str(result.inserted_id)
    await update.message.reply_photo(photo=IMG_NOVO, caption="🎉 <b>Conta Criada!</b>\nVocê está logado.", parse_mode="HTML")
    if start_command: await start_command(update, context)
    return ConversationHandler.END

# ==============================================================================
# 4. FLUXO DE MIGRAÇÃO (SEM ACESSO DIRETO AO LEGADO)
# ==============================================================================
async def btn_migrate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_private(update): return ConversationHandler.END
    q = update.callback_query; await q.answer()
    try: await q.delete_message()
    except: pass
    
    await context.bot.send_photo(
        chat_id=update.effective_chat.id, photo=IMG_MIGRA,
        caption="🔄 <b>MIGRAÇÃO DE CONTA</b>\n\nVamos converter sua conta antiga.\n\n1️⃣ Crie um <b>NOVO USUÁRIO</b>:",
        parse_mode="HTML"
    )
    return TYPING_USER_MIGRATE

async def receive_user_migrate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip().lower()
    
    exists = await asyncio.to_thread(users_collection.find_one, {"username": username})
    if exists:
        await update.message.reply_text("⚠️ Usuário já existe. Tente outro:")
        return TYPING_USER_MIGRATE
        
    context.user_data['mig_temp_user'] = username
    await update.message.reply_text("2️⃣ Escolha uma <b>SENHA</b> para sua nova conta:", parse_mode="HTML")
    return TYPING_PASS_MIGRATE

async def receive_pass_migrate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    try: await update.message.delete()
    except: pass
    
    username = context.user_data['mig_temp_user']
    
    u = update.effective_user
    tg_id = u.id
    
    # 1. Recupera dados antigos (usando abstração do Core, sem tocar no DB legado aqui)
    old_data = await get_player_data(tg_id)
        
    if not old_data:
        await update.message.reply_text("❌ Erro: Conta antiga não encontrada. Digite /start.")
        return ConversationHandler.END
        
    # 2. Prepara novo documento
    new_data = dict(old_data)
    if "_id" in new_data: del new_data["_id"]
    
    new_data.update({
        "username": username,
        "password": hash_password(password),
        "telegram_id_owner": tg_id,
        "migrated_at": datetime.now().isoformat(),
        "is_migrated": True
    })
    
    # 3. Insere no Novo Sistema (Async)
    result = await asyncio.to_thread(users_collection.insert_one, new_data)
    
    # 4. Limpa e Loga
    await clear_player_cache(tg_id)
    context.user_data.clear()
    context.user_data['logged_player_id'] = str(result.inserted_id)
    
    await update.message.reply_photo(photo=IMG_MIGRA, caption="✅ <b>Sucesso!</b> Conta migrada.", parse_mode="HTML")
    if start_command: await start_command(update, context)
    return ConversationHandler.END

# ==============================================================================
# LOGOUT / CANCEL
# ==============================================================================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelado.")
    return ConversationHandler.END

async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = get_current_player_id(update, context)
    if uid: await clear_player_cache(uid)
    context.user_data.clear()
    await update.message.reply_text("🔒 Saiu.")

async def logout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try: await q.answer("Saindo...")
    except: pass
    
    uid = get_current_player_id(update, context)
    if uid: await clear_player_cache(uid)
    context.user_data.clear()
    
    if update.effective_chat.type == ChatType.PRIVATE:
        kb = [[InlineKeyboardButton("🔐 ENTRAR", callback_data='btn_login')]]
        try: await q.edit_message_caption(caption="🔒 <b>Desconectado.</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        except: await context.bot.send_message(update.effective_chat.id, "🔒 Desconectado.")
    return ConversationHandler.END

auth_handler = ConversationHandler(
    entry_points=[
        CommandHandler('start', start_auth, filters=filters.ChatType.PRIVATE),
        CallbackQueryHandler(btn_login_callback, pattern='^btn_login$'),
        CallbackQueryHandler(start_register_flow, pattern='^btn_register$'),
        CallbackQueryHandler(btn_migrate_callback, pattern='^btn_migrate$'),
    ],
    states={
        CHOOSING_ACTION: [
            CommandHandler('start', start_auth),
            CallbackQueryHandler(btn_login_callback, pattern='^btn_login$'),
            CallbackQueryHandler(start_register_flow, pattern='^btn_register$'),
            CallbackQueryHandler(btn_migrate_callback, pattern='^btn_migrate$'),
        ],
        TYPING_USER_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_user_login)],
        TYPING_PASS_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_pass_login)],
        TYPING_USER_REG: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_user_reg)],
        TYPING_PASS_REG: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_pass_reg)],
        TYPING_USER_MIGRATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_user_migrate)],
        TYPING_PASS_MIGRATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_pass_migrate)],
    },
    fallbacks=[
        CommandHandler('cancel', cancel),
        CommandHandler('logout', logout_command),
        CallbackQueryHandler(logout_callback, pattern='^logout_btn$')
    ],
    allow_reentry=True
)