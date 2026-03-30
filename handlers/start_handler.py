import logging
from datetime import datetime, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.constants import ParseMode

from handlers.menu.kingdom import show_kingdom_menu
from handlers.menu.region import show_region_menu

from modules.player.queries import get_or_create_player 
from modules import player_manager
from modules.auth_utils import requires_login
from modules.player.account_lock import check_account_lock

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    session_id = context.user_data.get("logged_player_id")
    tg_id = update.effective_user.id
    
    # 1. BLOQUEIO DE SEGURANÇA: Se não estiver logado, pede para logar
    if not session_id:
        await update.message.reply_text(
            "🔒 <b>Acesso Restrito</b>\nVocê precisa entrar na sua conta para jogar.\n\nPor favor, use o comando /login para se identificar ou se registrar.", 
            parse_mode="HTML"
        )
        return
    
    # 2. Verifica os dados do jogador com a função CORRETA
    player_data = await player_manager.get_player_data(session_id)

    # =======================================================
    # 3. TRIAGEM: É NOVATO OU VETERANO?
    # =======================================================
    if player_data:
        # 👇 CORREÇÃO AQUI: Checa se tem Nível > 1 ou se já ganhou algum XP!
        is_veteran = player_data.get("level", 1) > 1 or player_data.get("xp", 0) > 0
        
        # Se NÃO TEM gênero, precisamos agir:
        if not player_data.get("gender"):
            if is_veteran:
                # Se for veterano, salva como masculino por padrão e deixa passar!
                player_data["gender"] = "masculino"
                await player_manager.save_player_data(session_id, player_data)
            else:
                # Se for novato de verdade (0 XP e lvl 1), mostra os botões!
                keyboard = [
                    [
                        InlineKeyboardButton("Masculino ♂️", callback_data="set_gender_masculino"),
                        InlineKeyboardButton("Feminino ♀️", callback_data="set_gender_feminino")
                    ],
                    [InlineKeyboardButton("Não-binário ⚧️", callback_data="set_gender_nao_binario")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "✨ *Bem-vindo ao Mundo de Eldora!*\n\n"
                    "Sua jornada está prestes a começar, mas antes, como você se identifica?",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
                return

    # 4. SE O JOGADOR EXISTE E JÁ TEM GÊNERO: Segue com a lógica original de reparo e login
    try:
        user_name = update.effective_user.first_name or "Aventureiro"
        tg_username = update.effective_user.username or ""

        # Auto-reparo de campos essenciais
        needs_repair = False
        if not player_data.get("telegram_id"):
            player_data["telegram_id"] = tg_id
            player_data["username"] = tg_username
            needs_repair = True
            
        missing_keys = {
            "inventory": {}, "equipment": {}, "equipped_items": {}, 
            "skills": [], "equipped_skills": [], "invested": {},
            "profession": {}, "guild": None
        }
        
        for key, default_value in missing_keys.items():
            if key not in player_data:
                player_data[key] = default_value
                needs_repair = True
                
        if needs_repair:
            await player_manager.save_player_data(session_id, player_data)

    except Exception as e:
        logger.error(f"Erro ao processar dados em /start: {e}")
        await update.message.reply_text("❌ Erro interno ao acessar os dados da conta.")
        return

    # Verificação de bloqueio
    locked, lock_msg = check_account_lock(player_data)
    if locked:
        await update.message.reply_text(lock_msg, parse_mode=ParseMode.HTML)
        return

    # Carrega a tela do jogo!
    await resume_game_state(update, context, player_data)
    
async def gender_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manipula o clique no botão de gênero."""
    query = update.callback_query
    await query.answer()
    
    gender = query.data.replace("set_gender_", "")
    context.user_data["temp_gender"] = gender
    context.user_data["awaiting_name"] = True
    
    await query.edit_message_text(
        "Ótima escolha! Agora, por qual **nome** você deseja ser conhecido em Eldora?\n"
        "_(Digite o nome aqui no chat)_",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o nome digitado e finalmente cria a conta."""
    if not context.user_data.get("awaiting_name"):
        return

    chosen_name = update.message.text
    gender = context.user_data.get("temp_gender", "não informado")
    session_id = context.user_data.get("logged_player_id")
    
    # Cria o player com os dados escolhidos
    player_data = await get_or_create_player(
        user_id=session_id, 
        default_name=chosen_name,
        username=update.effective_user.username or "",
        telegram_id=update.effective_user.id
    )
    
    # Adiciona o gênero ao documento do player
    player_data["gender"] = gender
    await player_manager.save_player_data(player_data["_id"], player_data)
    
    # Limpa estados temporários
    context.user_data["awaiting_name"] = False
    
    await update.message.reply_text(f"✅ Personagem **{chosen_name}** criado com sucesso!")
    await resume_game_state(update, context, player_data)

async def resume_game_state(update: Update, context: ContextTypes.DEFAULT_TYPE, player_data: dict):
    try:
        current_location = player_data.get("current_location", "reino_eldora")
        if current_location == "reino_eldora":
            await show_kingdom_menu(update, context, player_data=player_data)
        else:
            await show_region_menu(update, context, region_key=current_location)
    except Exception as e:
        logger.error(f"[START] Erro ao retomar estado: {e}")
        await update.message.reply_text("Erro ao carregar o menu. Tente /menu.")

# Handlers para registrar no seu main.py:
start_command_handler = CommandHandler(['start', 'menu'], start_command)
gender_handler = CallbackQueryHandler(gender_callback, pattern=r"^set_gender_")
name_input_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_input)