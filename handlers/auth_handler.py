# handlers/auth_handler.py
# (VERSÃO FINAL SANITIZADA: Auth Segura + Migração Unidirecional)

import logging
import hashlib
import asyncio 
from datetime import datetime
from bson import ObjectId

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

# --- MÓDULOS SANITIZADOS ---
from modules.auth_utils import get_current_player_id
from modules.player.core import clear_player_cache, users_collection, get_legacy_data_by_telegram_id
from modules.player.queries import check_migration_status, create_new_player
from modules.sessions import save_persistent_session, get_persistent_session, clear_persistent_session

# Tenta importar start_command opcionalmente
try:
    from handlers.start_handler import start_command
except ImportError:
    start_command = None

logger = logging.getLogger(__name__)

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
    # 1. Verifica memória RAM ou ID inválido
    session_id = get_current_player_id(update, context)
    tg_id = update.effective_user.id

    # 2. Se não tem na RAM, busca no Banco (Persistência)
    if not session_id:
        saved_id = await get_persistent_session(tg_id)
        if saved_id:
            # Verifica se esse ID existe na collection NOVA
            if users_collection is not None:
                try:
                    user_exists = await asyncio.to_thread(users_collection.find_one, {"_id": ObjectId(saved_id)})
                    if user_exists:
                        # Restaura sessão
                        context.user_data['logged_player_id'] = saved_id
                        session_id = saved_id
                        logger.info(f"🔄 Auto-Login: {tg_id} -> {saved_id}")
                    else:
                        await clear_persistent_session(tg_id)
                except:
                    await clear_persistent_session(tg_id)

    # 3. Se logou, manda pro jogo
    if session_id:
        if start_command: 
            await start_command(update, context)
        else: 
            await update.message.reply_text("✅ Você já está logado!")
        return ConversationHandler.END

    # --- MODO DESLOGADO: ANÁLISE DE MIGRAÇÃO ---
    context.user_data.clear()
    
    # Usa a nova query sanitizada para verificar status
    has_legacy, already_migrated, _ = await check_migration_status(tg_id)

    keyboard = []
    
    # Se tem conta antiga E ainda não migrou -> Força o fluxo de migração visualmente
    if has_legacy and not already_migrated:
        current_img = IMG_MIGRA
        caption_text = (
            "⚠️ <b>ATENÇÃO! CONTA ANTIGA DETECTADA</b>\n\n"
            "Detectamos um personagem vinculado ao seu Telegram no sistema antigo.\n"
            "Para continuar jogando com ele, você precisa criar um Login e Senha.\n\n"
            "👇 <b>Clique abaixo para Migrar e Salvar seu Progresso!</b>"
        )
        keyboard.append([InlineKeyboardButton("🔄 RESGATAR CONTA ANTIGA", callback_data='btn_migrate')])
        # Opção de criar do zero caso a pessoa queira abandonar a antiga
        keyboard.append([InlineKeyboardButton("🆕 Criar Nova do Zero (Perder Antiga)", callback_data='btn_register')])
    
    else:
        # Usuário novo ou já migrado
        current_img = IMG_NOVO
        caption_text = (
            "⚔️ <b>BEM-VINDO A ELDORA</b>\n\n"
            "Sua jornada começa aqui.\n"
            "Faça login ou crie sua conta para jogar."
        )
        keyboard.append([InlineKeyboardButton("🔐 ENTRAR", callback_data='btn_login')])
        keyboard.append([InlineKeyboardButton("📝 CRIAR CONTA", callback_data='btn_register')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.answer()
        try: await update.callback_query.delete_message()
        except: pass
            
    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=current_img, caption=caption_text, reply_markup=reply_markup, parse_mode="HTML")
    return CHOOSING_ACTION

# ==============================================================================
# 2. LOGIN (Collection USERS)
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
    try: await update.message.delete() # Apaga senha
    except: pass
    
    if users_collection is None:
        await update.message.reply_text("❌ Erro no banco de dados.")
        return ConversationHandler.END

    username = context.user_data.get('auth_temp_user')
    password_hash = hash_password(password)
    
    # Busca APENAS na collection 'users'
    user_doc = await asyncio.to_thread(users_collection.find_one, {"username": username, "password": password_hash})

    if user_doc:
        new_player_id = str(user_doc['_id'])
        
        # Limpa cache e seta sessão
        await clear_player_cache(new_player_id)
        context.user_data.clear()
        context.user_data['logged_player_id'] = new_player_id
        
        # Salva persistência
        await save_persistent_session(update.effective_user.id, new_player_id)
        
        await update.message.reply_photo(photo=IMG_LOGIN, caption=f"🔓 <b>Bem-vindo, {user_doc.get('character_name', username)}!</b>\n<i>Sessão iniciada.</i>", parse_mode="HTML")
        if start_command: await start_command(update, context)
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ <b>Dados incorretos.</b>\nSe você tinha conta antiga, use a opção 'Resgatar Conta' no /start.", parse_mode="HTML")
        return ConversationHandler.END

# ==============================================================================
# 3. REGISTRO (Collection USERS)
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
        await update.message.reply_text("❌ Erro DB.")
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
    
    new_player_doc = {
        "username": username,
        "password": hash_password(password),
        "telegram_id_owner": owner_id,
        "created_at": now_iso,
        "last_seen": now_iso,
        "character_name": username.capitalize(),
        "level": 1, "xp": 0, "gold": 100, "class": None,
        "max_hp": 50, "current_hp": 50, "energy": 20, "max_energy": 20, "energy_last_ts": now_iso,
        "inventory": {}, "equipment": {},
        "base_stats": {"max_hp": 50, "attack": 5, "defense": 3, "initiative": 5, "luck": 5},
        "premium_tier": "free", "gems": 0
    }
    
    # Insert direto
    result = await asyncio.to_thread(users_collection.insert_one, new_player_doc)
    new_player_id = str(result.inserted_id)
    
    context.user_data['logged_player_id'] = new_player_id
    await save_persistent_session(owner_id, new_player_id)

    await update.message.reply_photo(photo=IMG_NOVO, caption="🎉 <b>Conta Criada!</b>", parse_mode="HTML")
    if start_command: await start_command(update, context)
    return ConversationHandler.END

# ==============================================================================
# 4. MIGRAÇÃO (Leitura LEGACY -> Escrita USERS)
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
    
    if users_collection is None:
        await update.message.reply_text("❌ Erro DB.")
        return ConversationHandler.END

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
    
    # 1. Busca dados antigos EXPLICITAMENTE do Legado
    old_data = await get_legacy_data_by_telegram_id(tg_id)
    
    if not old_data:
        await update.message.reply_text("❌ Não encontramos dados antigos para este Telegram. Use a opção 'Criar Conta'.")
        return ConversationHandler.END
    
    # 2. Clona e Limpa os dados
    new_data = dict(old_data)
    
    # REMOVE O ID ANTIGO (Numérico) - Isso é crucial!
    if "_id" in new_data: del new_data["_id"] 
    
    # Atualiza com as credenciais do novo sistema
    new_data.update({
        "username": username,
        "password": hash_password(password),
        "telegram_id_owner": tg_id, # Vínculo para segurança futura
        "migrated_at": datetime.now().isoformat(),
        "is_migrated": True,
        # Garante que premium antigo não quebre o sistema novo
        "premium_tier": "free" if not new_data.get("premium_tier") else new_data.get("premium_tier"), 
        "premium_expires_at": None # Remove datas inválidas antigas
    })
    
    # 3. Insere na collection NOVA ('users')
    try:
        result = await asyncio.to_thread(users_collection.insert_one, new_data)
        new_player_id = str(result.inserted_id)
        
        # 4. Login imediato
        await clear_player_cache(new_player_id)
        context.user_data.clear()
        context.user_data['logged_player_id'] = new_player_id
        await save_persistent_session(tg_id, new_player_id)
        
        await update.message.reply_photo(photo=IMG_MIGRA, caption=f"✅ <b>MIGRAÇÃO SUCESSO!</b>\n\nPersonagem: <b>{new_data.get('character_name')}</b>\nNível: {new_data.get('level')}\n\n<i>Seus itens e atributos foram transferidos.</i>", parse_mode="HTML")
        if start_command: await start_command(update, context)
        
    except Exception as e:
        logger.error(f"Erro na migração do user {tg_id}: {e}")
        await update.message.reply_text("❌ Ocorreu um erro ao migrar seus dados. Contate o suporte.")

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
    await update.message.reply_text("🔒 <b>Você saiu.</b>", parse_mode="HTML")

async def logout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await clear_persistent_session(update.effective_user.id)
    context.user_data.clear()
    try: await q.delete_message()
    except: pass
    
    # Retorna ao menu inicial
    await start_auth(update, context)
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