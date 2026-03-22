# handlers/auth_handler.py
# (VERSÃO BLINDADA E PADRONIZADA PARA telegram_id)

import logging
import hashlib
import asyncio 
import certifi 
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient 

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
from telegram.constants import ChatType

# --- MÓDULOS INTERNOS ---
from modules.auth_utils import get_current_player_id
from modules.player.core import clear_player_cache, get_player_data
# Importa o gerenciador de sessões
from modules.sessions import save_persistent_session, get_persistent_session, clear_persistent_session

try:
    from handlers.start_handler import start_command
except ImportError:
    start_command = None

logger = logging.getLogger(__name__)

# ==============================================================================
# CONEXÃO MONGODB (Local para garantir funcionamento)
# ==============================================================================
MONGO_STR = "mongodb+srv://eldora-cluster:pb060987@cluster0.4iqgjaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

users_collection = None

try:
    client = MongoClient(MONGO_STR, tlsCAFile=certifi.where())
    db = client["eldora_db"]
    users_collection = db["users"] 
    logger.info("✅ [AUTH] Conexão MongoDB estabelecida.")
except Exception as e:
    logger.error(f"❌ [AUTH] FALHA CONEXÃO: {e}")
    users_collection = None

# ==============================================================================
# ESTADOS DA CONVERSA
# ==============================================================================
CHOOSING_ACTION = 1
TYPING_USER_LOGIN = 2
TYPING_PASS_LOGIN = 3
TYPING_USER_REG = 4
TYPING_PASS_REG = 5
TYPING_USER_MIGRATE = 6
TYPING_PASS_MIGRATE = 7
TYPING_USER_FORGOT = 8
TYPING_PASS_FORGOT = 9

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
# 1. MENU INICIAL / AUTO-LOGIN
# ==============================================================================
async def start_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != ChatType.PRIVATE:
        return ConversationHandler.END

    # --- LÓGICA DE AUTO-LOGIN ---
    session_id = get_current_player_id(update, context)
    tg_id = update.effective_user.id

    if not session_id:
        saved_id = await get_persistent_session(tg_id)
        if saved_id:
            if users_collection is not None:
                try:
                    user_exists = await asyncio.to_thread(users_collection.find_one, {"_id": ObjectId(saved_id)})
                    if user_exists:
                        context.user_data['logged_player_id'] = saved_id
                        session_id = saved_id
                        logger.info(f"🔄 Auto-Login: {tg_id} -> {saved_id}")
                    else:
                        await clear_persistent_session(tg_id)
                except: pass

    if session_id:
        if start_command: 
            await start_command(update, context)
        else: 
            await update.message.reply_text("✅ Você já está logado!")
        return ConversationHandler.END

    # --- MODO DESLOGADO: MOSTRA MENU ---
    context.user_data.clear()
    
    has_legacy = False
    try:
        legacy_data = await get_player_data(tg_id)
        if legacy_data:
            already_migrated = False
            if users_collection is not None:
                # CORREÇÃO: Busca por telegram_id padronizado
                doc = await asyncio.to_thread(users_collection.find_one, {"telegram_id": tg_id})
                if doc: already_migrated = True
            
            if not already_migrated:
                has_legacy = True
    except Exception as e:
        logger.error(f"Erro ao verificar legado: {e}")

    keyboard = []
    if has_legacy:
        current_img = IMG_MIGRA
        caption_text = (
            "⚠️ <b>ATENÇÃO! CONTA ANTIGA DETECTADA</b>\n\n"
            "O sistema mudou para Login/Senha.\n"
            "Você possui itens/níveis antigos para resgatar.\n\n"
            "👇 <b>Use 'Resgatar Conta' para não perder nada!</b>"
        )
        keyboard.append([InlineKeyboardButton("🔄 RESGATAR CONTA ANTIGA", callback_data='btn_migrate')])
        keyboard.append([InlineKeyboardButton("🆕 Criar Nova do Zero", callback_data='btn_register')])
    else:
        current_img = IMG_NOVO
        caption_text = (
            "⚔️ <b>BEM-VINDO A ELDORA</b>\n\n"
            "Sua jornada começa aqui.\n"
            "Faça login ou crie sua conta para jogar."
        )
        keyboard.append([InlineKeyboardButton("🔐 ENTRAR", callback_data='btn_login')])
        keyboard.append([InlineKeyboardButton("📝 CRIAR CONTA", callback_data='btn_register')])
        keyboard.append([InlineKeyboardButton("🆘 Esqueci a Senha", callback_data='btn_forgot')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.answer()
        try: await update.callback_query.delete_message()
        except: pass
            
    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=current_img, caption=caption_text, reply_markup=reply_markup, parse_mode="HTML")
    return CHOOSING_ACTION

# ==============================================================================
# 2. LOGIN
# ==============================================================================
async def btn_login_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_private(update): return ConversationHandler.END
    query = update.callback_query; await query.answer()
    try: await query.delete_message()
    except: pass
    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=IMG_LOGIN, caption="👤 <b>LOGIN</b>\nDigite seu <b>USUÁRIO</b>:", parse_mode="HTML")
    return TYPING_USER_LOGIN

async def receive_user_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['auth_temp_user'] = update.message.text.strip().lower()
    await update.message.reply_text("🔑 Digite sua <b>SENHA</b>:", parse_mode="HTML")
    return TYPING_PASS_LOGIN

async def receive_pass_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    try: await update.message.delete()
    except: pass
    
    username = context.user_data.get('auth_temp_user')
    password_hash = hash_password(password)
    
    if users_collection is None:
        await update.message.reply_text("❌ Erro de conexão com banco de dados.")
        return ConversationHandler.END

    user_doc = await asyncio.to_thread(users_collection.find_one, {"username": username, "password": password_hash})

    if user_doc:
        new_player_id = str(user_doc['_id'])
        await clear_player_cache(new_player_id)
        context.user_data.clear()
        context.user_data['logged_player_id'] = new_player_id
        await save_persistent_session(update.effective_user.id, new_player_id)
        
        await update.message.reply_photo(photo=IMG_LOGIN, caption=f"🔓 <b>Bem-vindo, {user_doc.get('character_name', username)}!</b>\n<i>Sessão salva.</i>", parse_mode="HTML")
        if start_command: await start_command(update, context)
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ <b>Dados incorretos.</b> Tente novamente (/start).", parse_mode="HTML")
        return ConversationHandler.END

# --- FLUXO DE ESQUECI A SENHA ---

async def btn_forgot_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_private(update): return ConversationHandler.END
    q = update.callback_query; await q.answer()
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🆘 <b>RECUPERAÇÃO DE SENHA</b>\n\nDigite o <b>USUÁRIO</b> da conta que deseja recuperar:",
        parse_mode="HTML"
    )
    return TYPING_USER_FORGOT

async def receive_user_forgot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip().lower()
    tg_id = update.effective_user.id
    
    if users_collection is None:
        await update.message.reply_text("❌ Erro de conexão.")
        return ConversationHandler.END

    user_doc = await asyncio.to_thread(users_collection.find_one, {"username": username})
    
    if not user_doc:
        await update.message.reply_text("❌ Usuário não encontrado.")
        return ConversationHandler.END
        
    # CORREÇÃO: Lê prioritariamente o telegram_id correto
    owner_id = user_doc.get("telegram_id") or user_doc.get("telegram_id_owner")
    
    if str(owner_id) != str(tg_id):
        await update.message.reply_text("⛔ <b>Acesso Negado.</b>\nEssa conta não está vinculada ao seu Telegram.", parse_mode="HTML")
        return ConversationHandler.END

    context.user_data['forgot_temp_user'] = username
    await update.message.reply_text(f"✅ Conta <b>{username}</b> verificada!\n\nDigite sua <b>NOVA SENHA</b>:", parse_mode="HTML")
    return TYPING_PASS_FORGOT

async def receive_pass_forgot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_password = update.message.text.strip()
    username = context.user_data.get('forgot_temp_user')
    new_hash = hash_password(new_password)
    
    if users_collection is not None:
        await asyncio.to_thread(
            users_collection.update_one,
            {"username": username},
            {"$set": {"password": new_hash}}
        )
        
    await update.message.reply_text(f"🔄 <b>Senha Alterada!</b>\nAgora você pode fazer login com a nova senha.", parse_mode="HTML")
    return await start_auth(update, context)

# ==============================================================================
# 3. REGISTRO
# ==============================================================================
async def start_register_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_private(update): return ConversationHandler.END
    q = update.callback_query; await q.answer()
    try: await q.delete_message()
    except: pass
    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=IMG_NOVO, caption="🆕 <b>REGISTRO</b>\nEscolha seu <b>USUÁRIO</b> (min 4 letras):", parse_mode="HTML")
    return TYPING_USER_REG

async def receive_user_reg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip().lower()
    if len(username) < 4: 
        await update.message.reply_text("⚠️ Muito curto. Tente outro:")
        return TYPING_USER_REG
    
    if users_collection is None:
         await update.message.reply_text("❌ Erro no banco de dados. Tente mais tarde.")
         return ConversationHandler.END

    exists = await asyncio.to_thread(users_collection.find_one, {"username": username})
    if exists: 
        await update.message.reply_text("⚠️ Em uso. Tente outro:")
        return TYPING_USER_REG
        
    context.user_data['reg_temp_user'] = username
    await update.message.reply_text(f"✅ Usuário <b>{username}</b> disponível!\nAgora escolha uma <b>SENHA</b>:", parse_mode="HTML")
    return TYPING_PASS_REG

async def receive_pass_reg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    try: await update.message.delete()
    except: pass

    username = context.user_data['reg_temp_user']
    owner_id = update.effective_user.id
    now_iso = datetime.now().isoformat()
    char_name_display = username.capitalize()

    new_player_doc = {
        "username": username,
        "password": hash_password(password),
        "telegram_id": owner_id, # CORREÇÃO: Apenas telegram_id
        "created_at": now_iso,
        "last_seen": now_iso,
        "name": char_name_display,
        "character_name": char_name_display,
        "name_normalized": char_name_display.lower(),
        "class": "aventureiro",
        "class_key": "aventureiro",
        "current_location": "reino_eldora",
        "level": 1, "xp": 0, "gold": 100, "gems": 0,
        "premium_tier": "free", "premium_expires_at": None,
        "hp": 50, "max_hp": 50, "current_hp": 50,
        "mana": 50, "max_mana": 50, "current_mp": 50, "mp": 50,
        "energy": 20, "max_energy": 20, "energy_last_ts": now_iso,
        "stats": {"hp": 50, "attack": 5, "defense": 3, "initiative": 5, "luck": 5, "mana": 50},
        "base_stats": {"max_hp": 50, "attack": 5, "defense": 3, "initiative": 5, "luck": 5},
        "inventory": {}, "equipment": {}, "equipped_items": {},
        "skills": [], "equipped_skills": [], "invested": {},
        "profession": None, "guild": None
    }

    if users_collection is not None:
        result = await asyncio.to_thread(users_collection.insert_one, new_player_doc)
        new_player_id = str(result.inserted_id)
        context.user_data['logged_player_id'] = new_player_id
        await save_persistent_session(owner_id, new_player_id)

        await update.message.reply_photo(
            photo=IMG_NOVO,
            caption=f"🎉 <b>Conta Criada!</b>\nBem-vindo a Eldora, {char_name_display}.\nVocê já está logado.",
            parse_mode="HTML"
        )
        if start_command: await start_command(update, context)
    else:
        await update.message.reply_text("❌ Erro de conexão.")
    return ConversationHandler.END

# ==============================================================================
# 4. MIGRAÇÃO
# ==============================================================================
async def btn_migrate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_private(update): return ConversationHandler.END
    q = update.callback_query; await q.answer()
    try: await q.delete_message()
    except: pass
    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=IMG_MIGRA, caption="🔄 <b>MIGRAÇÃO</b>\nPara salvar seu progresso antigo, crie um <b>NOVO USUÁRIO</b>:", parse_mode="HTML")
    return TYPING_USER_MIGRATE

async def receive_user_migrate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip().lower()
    if users_collection is not None:
        exists = await asyncio.to_thread(users_collection.find_one, {"username": username})
        if exists:
            await update.message.reply_text("⚠️ Em uso. Tente outro:")
            return TYPING_USER_MIGRATE
        
    context.user_data['mig_temp_user'] = username
    await update.message.reply_text("2️⃣ Escolha uma <b>SENHA</b>:", parse_mode="HTML")
    return TYPING_PASS_MIGRATE

async def receive_pass_migrate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    try: await update.message.delete()
    except: pass
    
    username = context.user_data['mig_temp_user']
    tg_id = update.effective_user.id
    old_data = await get_player_data(tg_id)
    
    if not old_data:
        new_data = {
            "username": username, "password": hash_password(password),
            "telegram_id": tg_id, "migrated_at": datetime.now().isoformat(),
            "character_name": username.capitalize(), "level": 1, "gold": 100
        }
    else:
        new_data = dict(old_data)
        if "_id" in new_data: del new_data["_id"]
        # CORREÇÃO: Salva apenas telegram_id
        new_data.update({
            "username": username, "password": hash_password(password),
            "telegram_id": tg_id, "migrated_at": datetime.now().isoformat(), "is_migrated": True
        })
    
    if users_collection is not None:
        result = await asyncio.to_thread(users_collection.insert_one, new_data)
        new_player_id = str(result.inserted_id)
        await clear_player_cache(tg_id)
        context.user_data.clear()
        context.user_data['logged_player_id'] = new_player_id
        await save_persistent_session(tg_id, new_player_id)
    
    await update.message.reply_photo(photo=IMG_MIGRA, caption="✅ <b>Migração Concluída!</b>\nSeus itens e nível foram salvos.", parse_mode="HTML")
    if start_command: await start_command(update, context)
    return ConversationHandler.END

# ==============================================================================
# LOGOUT / CANCEL
# ==============================================================================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operação cancelada.")
    return ConversationHandler.END

async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = get_current_player_id(update, context)
    if uid: await clear_player_cache(uid)
    await clear_persistent_session(update.effective_user.id)
    context.user_data.clear()
    await update.message.reply_text("🔒 <b>Você saiu.</b>\nSeu auto-login foi removido.", parse_mode="HTML")

async def logout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try:
        await q.answer("Saindo...")
    except:
        pass

    await clear_persistent_session(update.effective_user.id)
    context.user_data.clear()
    if context.chat_data:
        context.chat_data.clear()

    try:
        await q.delete_message()
    except:
        pass

    keyboard = [
        [InlineKeyboardButton("🔐 ENTRAR", callback_data='btn_login')],
        [InlineKeyboardButton("📝 CRIAR CONTA", callback_data='btn_register')]
    ]

    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=IMG_NOVO,
        caption="🔒 <b>Desconectado.</b>\nEntre novamente para jogar:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

auth_handler = ConversationHandler(
    entry_points=[
        CommandHandler('start', start_auth, filters=filters.ChatType.PRIVATE),
        CallbackQueryHandler(btn_login_callback, pattern='^btn_login$'),
        CallbackQueryHandler(start_register_flow, pattern='^btn_register$'),
        CallbackQueryHandler(btn_migrate_callback, pattern='^btn_migrate$'),
        CallbackQueryHandler(btn_forgot_callback, pattern='^btn_forgot$'),
    ],
    states={
        CHOOSING_ACTION: [
            CommandHandler('start', start_auth),
            CallbackQueryHandler(btn_login_callback, pattern='^btn_login$'),
            CallbackQueryHandler(start_register_flow, pattern='^btn_register$'),
            CallbackQueryHandler(btn_migrate_callback, pattern='^btn_migrate$'),
            CallbackQueryHandler(btn_forgot_callback, pattern='^btn_forgot$'),
        ],
        TYPING_USER_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_user_login)],
        TYPING_PASS_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_pass_login)],
        TYPING_USER_REG: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_user_reg)],
        TYPING_PASS_REG: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_pass_reg)],
        TYPING_USER_MIGRATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_user_migrate)],
        TYPING_PASS_MIGRATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_pass_migrate)],
        TYPING_USER_FORGOT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_user_forgot)],
        TYPING_PASS_FORGOT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_pass_forgot)],
    },
    fallbacks=[
        CommandHandler('cancel', cancel),
        CommandHandler('logout', logout_command),
        CallbackQueryHandler(logout_callback, pattern='^logout_btn$')
    ],
    allow_reentry=True
)