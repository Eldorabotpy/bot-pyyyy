# handlers/auth_handler.py
# (VERSÃO 4.1: Com suporte ao botão de Reconexão)

import logging
import hashlib
from datetime import datetime
from bson import ObjectId
# No topo do arquivo, junto com os outros imports
from modules.player.core import clear_player_cache
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
from modules.auth_utils import get_current_player_id

# Tenta importar as coleções
try:
    from modules.database import players_col, db
except ImportError:
    from modules.player.core import players_collection as players_col
    db = players_col.database 

# Tenta importar o menu para redirecionar quem já está logado
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

# --- CONSTANTES ---
USERS_COLLECTION = db["users"] 

# --- IMAGENS (IDs do Telegram) ---
IMG_LOGIN = "https://i.ibb.co/Fb8VkHjw/photo-2025-12-30-21-56-50.jpg"
IMG_MIGRACAO = "https://i.ibb.co/m5NxQwGw/photo-2025-12-30-21-56-46.jpg"
IMG_NOVO = "https://i.ibb.co/7JyxJfpn/photo-2025-12-30-21-56-42.jpg" 

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================
def hash_password(password: str) -> str:
    salt = "eldora_secure_v1"
    return hashlib.sha256((password + salt).encode()).hexdigest()

def get_session_id(context):
    return context.user_data.get("logged_player_id")

async def _check_private(update: Update) -> bool:
    """Retorna True se for privado, False se for grupo (e avisa)."""
    if update.effective_chat.type != ChatType.PRIVATE:
        if update.callback_query:
            await update.callback_query.answer("⚠️ Por segurança, faça isso no PRIVADO do bot!", show_alert=True)
        return False
    return True

# ==============================================================================
# 1. MENU INICIAL E COMANDO /START
# ==============================================================================
async def start_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Se for em grupo, ignora
    if update.effective_chat.type != ChatType.PRIVATE:
        return ConversationHandler.END

    # Lazy Import para evitar ciclo
    try:
        from handlers.start_handler import start_command
    except ImportError:
        start_command = None

    user = update.effective_user
    
    # 1. DEEP LINK (CRIAR CONTA)
    if context.args and context.args[0] == 'criar_conta':
        await start_register_flow(update, context)
        return TYPING_USER_REG

    # 2. CHECK SE JÁ ESTÁ LOGADO
    session_id = get_session_id(context)
    if session_id:
        try:
            oid = ObjectId(session_id)
            user_doc = USERS_COLLECTION.find_one({"_id": oid})
        except Exception:
            user_doc = None

        if not user_doc:
             context.user_data.clear()
        else:
            # Se já está logado, chama o menu principal
            if start_command:
                await start_command(update, context)
            else:
                await update.message.reply_text("⚠️ Você já está logado.")
            return ConversationHandler.END

    # 3. CHECK DE CONTA ANTIGA / MIGRAÇÃO
    old_account = players_col.find_one({"_id": user.id})
    already_migrated = USERS_COLLECTION.find_one({"telegram_id_owner": user.id})

    current_img = None
    caption_text = ""
    keyboard = []

    if already_migrated:
        current_img = IMG_LOGIN
        caption_text = f"🛡️ <b>Bem-vindo de volta, {user.first_name}!</b>\nDetectamos sua conta Eldora."
        keyboard.append([InlineKeyboardButton("🔐 𝔼ℕ𝕋ℝ𝔸ℝ", callback_data='btn_login')])
        keyboard.append([InlineKeyboardButton("📝 𝕀𝕟𝕚𝕔𝕚𝕒𝕣 ℕ𝕠𝕧𝕒 𝕁𝕠𝕣𝕟𝕒𝕕𝕒", callback_data='btn_register')])
    elif old_account:
        current_img = IMG_MIGRACAO
        nome_heroi = old_account.get('character_name', 'Aventureiro')
        caption_text = (
            "📜 <b>O GRIMÓRIO FOI ATUALIZADO!</b>\n\n"
            f"Saudações, nobre {nome_heroi}!\n\n"
            "Os magos do reino renovaram os antigos registros de Eldora. "
            "Para garantir que suas lendas não se percam, vincule sua alma a um novo Registro Mágico.\n\n"
            "<i>Todo o seu poder e inventário serão preservados.</i>"
        )
        keyboard.append([InlineKeyboardButton("✨ RESGATAR MEU LEGADO", callback_data='btn_migrate')])
        keyboard.append([InlineKeyboardButton("🆕 Iniciar Nova Jornada", callback_data='btn_register')])
    else:
        current_img = IMG_NOVO
        caption_text = "⚔️ <b>Bem-vindo ao Mundo de Eldora!</b>\n\nPara jogar, entre ou crie uma conta."
        keyboard.append([InlineKeyboardButton("📝 CRIAR CONTA", callback_data='btn_register')])
        keyboard.append([InlineKeyboardButton("🔐 Já tenho conta", callback_data='btn_login')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.answer()
        # Tenta deletar a mensagem anterior (ex: a msg de "Sessão Expirada") para limpar a tela
        try: await update.callback_query.delete_message()
        except Exception: pass
            
    try:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=current_img,
            caption=caption_text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    except Exception:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=caption_text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )

    return CHOOSING_ACTION

# ==============================================================================
# 2. FLUXO DE LOGIN
# ==============================================================================
async def btn_login_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_private(update): return ConversationHandler.END

    query = update.callback_query
    await query.answer()
    try: await query.delete_message()
    except Exception: pass

    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=IMG_LOGIN,
        caption="👤 <b>LOGIN:</b> Digite seu <b>USUÁRIO</b>:",
        parse_mode="HTML"
    )
    return TYPING_USER_LOGIN

async def receive_user_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != ChatType.PRIVATE: return ConversationHandler.END
    
    context.user_data['auth_temp_user'] = update.message.text.strip().lower()
    
    await update.message.reply_photo(
        photo=IMG_LOGIN,
        caption="🔑 <b>LOGIN:</b> Agora digite sua <b>SENHA</b>:",
        parse_mode="HTML"
    )
    return TYPING_PASS_LOGIN

async def receive_pass_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != ChatType.PRIVATE: return ConversationHandler.END

    password = update.message.text.strip()
    try: await update.message.delete()
    except Exception: pass
    
    username = context.user_data.get('auth_temp_user')
    password_hash = hash_password(password)

    user_doc = USERS_COLLECTION.find_one({"username": username, "password": password_hash})

    if user_doc:
        # Limpeza completa de sessão anterior
        context.user_data.clear()
        
        new_player_id = str(user_doc['_id'])
        await clear_player_cache(new_player_id)
        await clear_player_cache(update.effective_user.id)

        context.user_data['logged_player_id'] = new_player_id
        context.user_data['logged_username'] = username
        
        await update.message.reply_photo(
            photo=IMG_LOGIN,
            caption=f"🔓 <b>Login realizado!</b>\nBem-vindo, {user_doc.get('character_name', username)}!",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )
        
        if start_command:
            await start_command(update, context)
            
        return ConversationHandler.END
    else:
        await update.message.reply_photo(
            photo=IMG_LOGIN,
            caption="❌ <b>Usuário ou senha incorretos.</b>\nUse /start para tentar novamente.",
            parse_mode="HTML"
        )
        return ConversationHandler.END
 

# ==============================================================================
# 3. FLUXO DE REGISTRO
# ==============================================================================
async def start_register_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message if update.message else update.callback_query.message
    if not await _check_private(update): return ConversationHandler.END

    if update.callback_query:
        await update.callback_query.answer()
        try: await update.callback_query.delete_message()
        except Exception: pass
        
        await context.bot.send_photo(
            chat_id=msg.chat_id, 
            photo=IMG_NOVO,
            caption="🆕 <b>NOVA CONTA</b>\n\nEscolha um <b>NOME DE USUÁRIO</b> único:",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_photo(
            photo=IMG_NOVO,
            caption="🆕 <b>NOVA CONTA</b>\n\nEscolha um <b>NOME DE USUÁRIO</b> único:",
            parse_mode="HTML"
        )
        
    return TYPING_USER_REG

async def receive_user_reg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != ChatType.PRIVATE: return ConversationHandler.END

    username = update.message.text.strip().lower()
    
    if len(username) < 4:
        await update.message.reply_photo(
            photo=IMG_NOVO,
            caption="⚠️ O usuário deve ter pelo menos 4 letras. Tente outro:",
            parse_mode="HTML"
        )
        return TYPING_USER_REG

    if USERS_COLLECTION.find_one({"username": username}):
        await update.message.reply_photo(
            photo=IMG_NOVO,
            caption="⚠️ Este usuário já existe. Escolha outro:",
            parse_mode="HTML"
        )
        return TYPING_USER_REG
        
    context.user_data['reg_temp_user'] = username
    
    await update.message.reply_photo(
        photo=IMG_NOVO,
        caption=f"✅ Usuário <b>{username}</b> disponível!\n\nAgora escolha uma <b>SENHA</b>:",
        parse_mode="HTML"
    )
    return TYPING_PASS_REG

async def receive_pass_reg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != ChatType.PRIVATE: return ConversationHandler.END

    password = update.message.text.strip()
    try: await update.message.delete()
    except Exception: pass
    
    username = context.user_data['reg_temp_user']
    now_iso = datetime.now().isoformat()
    
    new_player_doc = {
        "username": username,
        "password": hash_password(password),
        "telegram_id_owner": update.effective_user.id,
        "created_at": now_iso,
        "last_seen": now_iso,
        "character_name": username.capitalize(),
        "level": 1, "xp": 0, "gold": 100, "class": None,
        "max_hp": 50, "current_hp": 50,
        "energy": 20, "max_energy": 20, "energy_last_ts": now_iso,
        "inventory": {}, "equipment": {},
        "base_stats": {"max_hp": 50, "attack": 5, "defense": 3, "initiative": 5, "luck": 5},
        "premium_tier": "free",
        "premium_expires_at": None,
        "gems": 0
    }
    
    result = USERS_COLLECTION.insert_one(new_player_doc)
    await clear_player_cache(update.effective_user.id)

    context.user_data['logged_player_id'] = str(result.inserted_id)
    
    await update.message.reply_photo(
        photo=IMG_NOVO,
        caption="🎉 <b>Conta Criada com Sucesso!</b>\nAbrindo menu principal...",
        parse_mode="HTML"
    )
    
    if start_command:
        await start_command(update, context)
        
    return ConversationHandler.END

# ==============================================================================
# 4. FLUXO DE MIGRAÇÃO
# ==============================================================================
async def btn_migrate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_private(update): return ConversationHandler.END

    query = update.callback_query
    await query.answer()
    try: await query.delete_message()
    except Exception: pass
        
    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=IMG_MIGRACAO,
        caption="🔄 <b>MIGRAÇÃO</b>\n\n1️⃣ Digite o <b>USUÁRIO</b> que você quer usar na nova conta:",
        parse_mode="HTML"
    )
    return TYPING_USER_MIGRATE

async def receive_user_migrate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != ChatType.PRIVATE: return ConversationHandler.END

    username = update.message.text.strip().lower()
    if USERS_COLLECTION.find_one({"username": username}):
        await update.message.reply_photo(
            photo=IMG_MIGRACAO,
            caption="⚠️ Usuário em uso. Tente outro:",
            parse_mode="HTML"
        )
        return TYPING_USER_MIGRATE
    
    context.user_data['mig_temp_user'] = username
    
    await update.message.reply_photo(
        photo=IMG_MIGRACAO,
        caption="2️⃣ Agora escolha uma <b>SENHA</b> segura:",
        parse_mode="HTML"
    )
    return TYPING_PASS_MIGRATE

async def receive_pass_migrate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != ChatType.PRIVATE: return ConversationHandler.END

    password = update.message.text.strip()
    try: await update.message.delete()
    except Exception: pass
    
    username = context.user_data['mig_temp_user']
    telegram_id = update.effective_user.id
    
    old_data = players_col.find_one({"_id": telegram_id})
    if not old_data:
        await update.message.reply_text("❌ Erro crítico: Conta antiga não encontrada.")
        return ConversationHandler.END
        
    new_data = dict(old_data)
    if "_id" in new_data: del new_data["_id"]
    new_data.pop("premium_tier", None)
    new_data.pop("premium_expires_at", None)
    
    new_data.update({
        "username": username,
        "password": hash_password(password),
        "telegram_id_owner": telegram_id,
        "migrated_at": datetime.now().isoformat(),
        "is_migrated": True,
        "premium_tier": "free",
        "premium_expires_at": None
    })
    
    result = USERS_COLLECTION.insert_one(new_data)
    
    await clear_player_cache(telegram_id)
    context.user_data.clear()

    context.user_data['logged_player_id'] = str(result.inserted_id)
    context.user_data['logged_username'] = username
    
    await update.message.reply_photo(
        photo=IMG_MIGRACAO,
        caption="✅ <b>Migração Concluída!</b>",
        parse_mode="HTML"
    )
    
    if start_command:
        await start_command(update, context)
        
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operação cancelada.")
    return ConversationHandler.END

async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logged_id = context.user_data.get("logged_player_id")
    if logged_id:
        await clear_player_cache(logged_id)
    await clear_player_cache(update.effective_user.id)
    context.user_data.clear()
    await update.message.reply_text("🔒 Você saiu da sua conta.")

async def logout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer("👋 Saindo...")
    except: pass
    try: await query.delete_message()
    except: pass
    
    logged_id = context.user_data.get("logged_player_id")
    if logged_id:
        await clear_player_cache(logged_id)
    await clear_player_cache(update.effective_user.id)
    
    context.user_data.clear()
    
    kb = [
        [InlineKeyboardButton("🔐 𝔼ℕ𝕋ℝ𝔸ℝ", callback_data='btn_login')],
        [InlineKeyboardButton("📝 𝕀𝕟𝕚𝕔𝕚𝕒𝕣 ℕ𝕠𝕧𝕒 𝕁𝕠𝕣𝕟𝕒𝕕𝕒", callback_data='btn_register')]
    ]
    
    if update.effective_chat.type == ChatType.PRIVATE:
        try:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id, 
                photo=IMG_LOGIN, 
                caption="🔒 <b>Você desconectou.</b>", 
                reply_markup=InlineKeyboardMarkup(kb), 
                parse_mode="HTML"
            )
        except:
            pass
    return ConversationHandler.END

# ==============================================================================
# CONFIGURAÇÃO DO HANDLER
# ==============================================================================
auth_handler = ConversationHandler(
    entry_points=[
        CommandHandler('start', start_auth, filters=filters.ChatType.PRIVATE),
        CallbackQueryHandler(btn_login_callback, pattern='^btn_login$'),
        CallbackQueryHandler(start_register_flow, pattern='^btn_register$'),
        CallbackQueryHandler(btn_migrate_callback, pattern='^btn_migrate$'),
        
        # ✅ ADICIONADO AQUI: O ponto de entrada para o botão de Reconectar
        CallbackQueryHandler(start_auth, pattern='^start_login_flow$'),
    ],
    states={
        CHOOSING_ACTION: [
            CommandHandler('start', start_auth, filters=filters.ChatType.PRIVATE),
            CallbackQueryHandler(btn_login_callback, pattern='^btn_login$'),
            CallbackQueryHandler(start_register_flow, pattern='^btn_register$'),
            CallbackQueryHandler(btn_migrate_callback, pattern='^btn_migrate$'),
            CallbackQueryHandler(start_auth, pattern='^start_login_flow$'),
        ],
        TYPING_USER_LOGIN: [
             CommandHandler('start', start_auth), 
             MessageHandler(filters.TEXT & ~filters.COMMAND, receive_user_login)
        ],
        TYPING_PASS_LOGIN: [
             CommandHandler('start', start_auth),
             MessageHandler(filters.TEXT & ~filters.COMMAND, receive_pass_login)
        ],
        TYPING_USER_REG: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_user_reg)],
        TYPING_PASS_REG: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_pass_reg)],
        TYPING_USER_MIGRATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_user_migrate)],
        TYPING_PASS_MIGRATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_pass_migrate)],
    },
    fallbacks=[
        CommandHandler('cancel', cancel),
        CommandHandler('logout', logout_command),
        CallbackQueryHandler(logout_callback, pattern='^logout_btn$'),
        CommandHandler('start', start_auth, filters=filters.ChatType.PRIVATE)
    ],
    allow_reentry=True
)