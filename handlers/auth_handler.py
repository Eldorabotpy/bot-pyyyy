# handlers/auth_handler.py
# (VERSÃO ATUALIZADA: Com Logout via Botão)

import logging
import hashlib
from datetime import datetime
from bson import ObjectId

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

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

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================
def hash_password(password: str) -> str:
    salt = "eldora_secure_v1"
    return hashlib.sha256((password + salt).encode()).hexdigest()

def get_session_id(context):
    return context.user_data.get("logged_player_id")

# ==============================================================================
# 1. MENU INICIAL E COMANDO /START
# ==============================================================================
async def start_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Se for em grupo, ignora
    if update.effective_chat.type != 'private':
        return ConversationHandler.END

    # 1. DEEP LINK (CRIAR CONTA)
    if context.args and context.args[0] == 'criar_conta':
        await update.message.reply_text("👋 Bem-vindo ao Registro!\nVamos criar sua conta.")
        return await start_register_flow(update, context)

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
            if start_command:
                await start_command(update, context)
            else:
                await update.message.reply_text(
                    f"✅ Você já está logado como **{user_doc.get('username')}**!\n"
                    "Use /menu para jogar."
                )
            return ConversationHandler.END

    # 3. CHECK DE CONTA ANTIGA / MIGRAÇÃO
    old_account = players_col.find_one({"_id": user.id})
    already_migrated = USERS_COLLECTION.find_one({"telegram_id_owner": user.id})

    # --- DEFINIÇÃO DAS IMAGENS (Coloque seus IDs ou URLs aqui) ---
    IMG_LOGIN = "AgACAgEAAxkBAAEEhz9pUum4yP5jywLvsM-XaIHeG2-rfwACJAxrG_tYmUZ14kXfrtMVigEAAwIAA3kAAzYE"    # Imagem para quem já tem conta (Entrar)
    IMG_MIGRACAO = "AgACAgEAAxkBAAEEhzZpUulnSfDAylISvmAqV6y4Zn7fogACIwxrG_tYmUaQ3V-IybVsVwEAAwIAA3kAAzYE" # Imagem para quem precisa Migrar
    IMG_NOVO = "AgACAgEAAxkBAAEEhzZpUulnSfDAylISvmAqV6y4Zn7fogACIwxrG_tYmUaQ3V-IybVsVwEAAwIAA3kAAzYE"     # Imagem para novos jogadores (Criar)

    # Variáveis que serão preenchidas nos IFs abaixo
    current_img = None
    caption_text = ""
    keyboard = []

    # --- LÓGICA DE SELEÇÃO DE MENU ---
    
    # CASO 1: Já tem conta no sistema novo -> Login/Criar Outra
    if already_migrated:
        current_img = IMG_LOGIN
        caption_text = f"🛡️ **Bem-vindo de volta, {user.first_name}!**\nDetectamos sua conta Eldora."
        keyboard.append([InlineKeyboardButton("🔐 𝔼ℕ𝕋ℝ𝔸ℝ", callback_data='btn_login')])
        keyboard.append([InlineKeyboardButton("📝 𝕀𝕟𝕚𝕔𝕚𝕒𝕣 ℕ𝕠𝕧𝕒 𝕁𝕠𝕣𝕟𝕒𝕕𝕒", callback_data='btn_register')])
    
    # CASO 2: Tem conta antiga -> Migração
    elif old_account:
        current_img = IMG_MIGRACAO
        nome_heroi = old_account.get('character_name', 'Aventureiro')
        caption_text = (
            "📜 𝐎 𝐆𝐑𝐈𝐌𝐎́𝐑𝐈𝐎 𝐅𝐎𝐈 𝐀𝐓𝐔𝐀𝐋𝐈𝐙𝐀𝐃𝐎!\n\n"
            f"Saudações, nobre {nome_heroi}!\n\n"
            "𝘖𝘴 𝘮𝘢𝘨𝘰𝘴 𝘥𝘰 𝘳𝘦𝘪𝘯𝘰 𝘳𝘦𝘯𝘰𝘷𝘢𝘳𝘢𝘮 𝘰𝘴 𝘢𝘯𝘵𝘪𝘨𝘰𝘴 𝘳𝘦𝘨𝘪𝘴𝘵𝘳𝘰𝘴 𝘥𝘦 𝘌𝘭𝘥𝘰𝘳𝘢. "
            "𝘗𝘢𝘳𝘢 𝘨𝘢𝘳𝘢𝘯𝘵𝘪𝘳 𝘲𝘶𝘦 𝘴𝘶𝘢𝘴 𝘭𝘦𝘯𝘥𝘢𝘴, 𝘰𝘶𝘳𝘰𝘴 𝘦 𝘤𝘰𝘯𝘲𝘶𝘪𝘴𝘵𝘢𝘴 𝘯𝘢̃𝘰 𝘴𝘦 𝘱𝘦𝘳𝘤𝘢𝘮 𝘯𝘢𝘴 𝘢𝘳𝘦𝘪𝘢𝘴 𝘥𝘰 𝘵𝘦𝘮𝘱𝘰, "
            "𝘦́ 𝘯𝘦𝘤𝘦𝘴𝘴𝘢́𝘳𝘪𝘰 𝐯𝐢𝐧𝐜𝐮𝐥𝐚𝐫 𝐬𝐮𝐚 𝐚𝐥𝐦𝐚 𝘢 𝘶𝘮 𝘯𝘰𝘷𝘰 𝘙𝘦𝘨𝘪𝘴𝘵𝘳𝘰 𝘔𝘢́𝘨𝘪𝘤𝘰.\n\n"
            "𝘕𝘢̃𝘰 𝘵𝘦𝘮𝘢! 𝘛𝘰𝘥𝘰 𝘰 𝘴𝘦𝘶 𝘱𝘰𝘥𝘦𝘳 𝘦 𝘪𝘯𝘷𝘦𝘯𝘵𝘢́𝘳𝘪𝘰 𝘴𝘦𝘳𝘢̃𝘰 𝘱𝘳𝘦𝘴𝘦𝘳𝘷𝘢𝘥𝘰𝘴 𝘥𝘶𝘳𝘢𝘯𝘵𝘦 𝘰 𝘳𝘪𝘵𝘶𝘢𝘭."
        )
        keyboard.append([InlineKeyboardButton("✨ RESGATAR MEU LEGADO", callback_data='btn_migrate')])
        keyboard.append([InlineKeyboardButton("🆕 Iniciar Nova Jornada", callback_data='btn_register')])
    
    # CASO 3: Novo Jogador -> Criar/Entrar
    else:
        current_img = IMG_NOVO
        caption_text = "⚔️ 𝗕𝗲𝗺-𝘃𝗶𝗻𝗱𝗼 𝗮𝗼 𝗠𝘂𝗻𝗱𝗼 𝗱𝗲 𝗘𝗹𝗱𝗼𝗿𝗮!\n\n𝗣𝗮𝗿𝗮 𝗷𝗼𝗴𝗮𝗿, 𝗲𝗻𝘁𝗿𝗲 𝗼𝘂 𝗰𝗿𝗶𝗲 𝘂𝗺𝗮 𝗰𝗼𝗻𝘁𝗮."
        keyboard.append([InlineKeyboardButton("📝 CRIAR CONTA", callback_data='btn_register')])
        keyboard.append([InlineKeyboardButton("🔐 Já tenho conta", callback_data='btn_login')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # --- ENVIO DA IMAGEM ---
    
    # Se veio de um clique de botão (Callback), deletamos a anterior para mandar a nova foto limpa
    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.delete_message()
        except Exception:
            pass # Ignora se não der pra deletar
            
    # Envia a foto com a legenda (Caption)
    try:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=current_img,
            caption=caption_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        # Fallback de segurança: Se a imagem falhar (ID errado), envia só texto
        print(f"Erro ao enviar imagem de auth: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=caption_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    return CHOOSING_ACTION

# ==============================================================================
# 2. FLUXO DE LOGIN
# ==============================================================================
async def btn_login_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # CORREÇÃO: Deleta a imagem
    try:
        await query.delete_message()
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="👤 Digite seu 𝗨𝗦𝗨𝗔𝗥𝗜𝗢:",
        parse_mode="Markdown"
    )
    return TYPING_USER_LOGIN

async def receive_user_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['auth_temp_user'] = update.message.text.strip().lower()
    await update.message.reply_text("🔑 Agora digite sua 𝐒𝐄𝐍𝐇𝐀:")
    return TYPING_PASS_LOGIN

async def receive_pass_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    username = context.user_data.get('auth_temp_user')
    password_hash = hash_password(password)

    user_doc = USERS_COLLECTION.find_one({"username": username, "password": password_hash})

    if user_doc:
        context.user_data['logged_player_id'] = str(user_doc['_id'])
        context.user_data['logged_username'] = username
        
        await update.message.reply_text(
            f"🔓 𝕃𝕠𝕘𝕚𝕟 𝕣𝕖𝕒𝕝𝕚𝕫𝕒𝕕𝕠!\nBem-vindo, {user_doc.get('character_name', username)}!",
            reply_markup=ReplyKeyboardRemove()
        )
        
        if start_command:
            await start_command(update, context)
            
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ Usuário ou senha incorretos.\nUse /start para tentar novamente.")
        return ConversationHandler.END

# ==============================================================================
# 3. FLUXO DE REGISTRO
# ==============================================================================
async def start_register_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🆕 **Nova Conta**\n\nEscolha um 𝗡𝗢𝗠𝗘 𝗗𝗘 𝗨𝗦𝗨𝗔𝗥𝗜𝗢  único:"
    
    if update.callback_query:
        await update.callback_query.answer()
        # CORREÇÃO: Deleta a imagem se veio de botão
        try:
            await update.callback_query.delete_message()
        except Exception:
            pass
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(text, parse_mode="Markdown")
        
    return TYPING_USER_REG

async def receive_user_reg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip().lower()
    
    if len(username) < 4:
        await update.message.reply_text("⚠️ O usuário deve ter pelo menos 4 letras. Tente outro:")
        return TYPING_USER_REG

    if USERS_COLLECTION.find_one({"username": username}):
        await update.message.reply_text("⚠️ Este usuário já existe. Escolha outro:")
        return TYPING_USER_REG
        
    context.user_data['reg_temp_user'] = username
    await update.message.reply_text(f"✅ Usuário '{username}' disponível!\n\nAgora escolha uma **SENHA**:")
    return TYPING_PASS_REG

async def receive_pass_reg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
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
        "base_stats": {"max_hp": 50, "attack": 5, "defense": 3, "initiative": 5, "luck": 5}
    }
    
    result = USERS_COLLECTION.insert_one(new_player_doc)
    context.user_data['logged_player_id'] = str(result.inserted_id)
    
    await update.message.reply_text("🎉 **Conta Criada!**\nAbrindo menu...")
    
    if start_command:
        await start_command(update, context)
        
    return ConversationHandler.END

# ==============================================================================
# 4. FLUXO DE MIGRAÇÃO
# ==============================================================================
async def btn_migrate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # CORREÇÃO: Deleta a imagem antes de mandar o texto
    try:
        await query.delete_message()
    except Exception:
        pass # Se não der pra deletar, ignora
        
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🔄 **MIGRAÇÃO DE CONTA**\n\n1️⃣ Digite o **USUÁRIO** que você quer usar:",
        parse_mode="Markdown"
    )
    return TYPING_USER_MIGRATE

async def receive_user_migrate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip().lower()
    if USERS_COLLECTION.find_one({"username": username}):
        await update.message.reply_text("⚠️ Usuário em uso. Tente outro:")
        return TYPING_USER_MIGRATE
    
    context.user_data['mig_temp_user'] = username
    await update.message.reply_text("2️⃣ Agora escolha uma **SENHA** segura:")
    return TYPING_PASS_MIGRATE

async def receive_pass_migrate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    username = context.user_data['mig_temp_user']
    telegram_id = update.effective_user.id
    
    old_data = players_col.find_one({"_id": telegram_id})
    
    if not old_data:
        await update.message.reply_text("❌ Erro crítico: Conta antiga não encontrada.")
        return ConversationHandler.END
        
    new_data = dict(old_data)
    if "_id" in new_data: del new_data["_id"]
        
    new_data.update({
        "username": username,
        "password": hash_password(password),
        "telegram_id_owner": telegram_id,
        "migrated_at": datetime.now().isoformat(),
        "is_migrated": True
    })
    
    result = USERS_COLLECTION.insert_one(new_data)
    
    context.user_data['logged_player_id'] = str(result.inserted_id)
    context.user_data['logged_username'] = username
    
    await update.message.reply_text("✅ **Migração Concluída!**\nAbrindo menu...")
    
    if start_command:
        await start_command(update, context)
        
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operação cancelada.")
    return ConversationHandler.END

async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("🔒 Você saiu da sua conta.")

# --- NOVA FUNÇÃO DE LOGOUT PARA O BOTÃO ---
# Em handlers/auth_handler.py

async def logout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Realiza o logout, limpa a sessão e ENCERRA qualquer conversa ativa.
    """
    query = update.callback_query
    
    # 1. Feedback visual rápido
    try: await query.answer("👋 Saindo...")
    except: pass
    
    # 2. Tenta apagar a mensagem do menu anterior (opcional, mas limpa a tela)
    try: await query.delete_message()
    except: pass
    
    # 3. Limpa os dados da sessão
    context.user_data.clear()
    
    # 4. Chama a tela de Login novamente
    # Nota: Não usamos 'await start_auth' direto aqui porque queremos que o handler
    # de autenticação capture o 'estado' limpo na próxima interação.
    # Em vez disso, mandamos a mensagem inicial manualmente.
    
    # Vamos usar a mesma lógica do start_auth para mostrar a imagem correta
    # (Copie aqui as suas variáveis de imagem que estão lá em cima no arquivo)
    IMG_LOGIN = "AgACAgEAAxkBAAEEhz9pUum4yP5jywLvsM-XaIHeG2-rfwACJAxrG_tYmUZ14kXfrtMVigEAAwIAA3kAAzYE"
    
    kb = [
        [InlineKeyboardButton("🔐 𝔼ℕ𝕋ℝ𝔸ℝ", callback_data='btn_login')],
        [InlineKeyboardButton("📝 𝕀𝕟𝕚𝕔𝕚𝕒𝕣 ℕ𝕠𝕧𝕒 𝕁𝕠𝕣𝕟𝕒𝕕𝕒", callback_data='btn_register')]
    ]
    
    try:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=IMG_LOGIN,
            caption="🔒 <b>Você desconectou.</b>\n\nPara voltar a Eldora, entre novamente.",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="HTML"
        )
    except Exception:
        # Fallback se der erro na foto
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🔒 <b>Você desconectou.</b>\n\nUse /start para entrar novamente.",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="HTML"
        )

    # 5. O PASSO MAIS IMPORTANTE:
    # Retorna END para dizer ao ConversationHandler do Jogo que acabou!
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
    ],
    states={
        CHOOSING_ACTION: [
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
        # Adicione esta linha para o botão funcionar mesmo se o jogador estiver digitando senha:
        CallbackQueryHandler(logout_callback, pattern='^logout_btn$')
    ]
)
