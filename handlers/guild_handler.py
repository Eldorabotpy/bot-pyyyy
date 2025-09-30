# Em handlers/guild_handler.py
import logging
import random
from telegram.error import BadRequest
from telegram.ext import ConversationHandler, MessageHandler, filters, CommandHandler
from modules.game_data.clans import CLAN_CONFIG
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules import player_manager, game_data # Iremos adicionar clan_manager depois
from modules.game_data.clans import CLAN_PRESTIGE_LEVELS, CLAN_CONFIG
from modules import clan_manager
from modules import mission_manager
from modules.game_data.missions import MISSION_CATALOG
from modules.game_data.guild_missions import GUILD_MISSIONS_CATALOG
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from modules import file_ids

logger = logging.getLogger(__name__)

ASKING_NAME = 1
ASKING_INVITEE = 1
ASKING_SEARCH_NAME, SHOWING_SEARCH_RESULT = range(2, 4) # Usamos 2 e 3 para não colidir com a outra conversa
ASKING_LEADER_TARGET, CONFIRM_LEADER_TRANSFER = range(4, 6)
ASKING_DEPOSIT_AMOUNT, ASKING_WITHDRAW_AMOUNT = range(10, 12) # Usamos números altos para não colidir
ASKING_CLAN_LOGO = range(20, 21)

# --- Handler principal do menu da Guilda ---
async def start_clan_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    player_data = player_manager.get_player_data(user_id)
    
    # Extrai o método de pagamento do botão (gold ou dimas)
    payment_method = query.data.split(':')[1]
    
    # Verifica o custo
    cost = CLAN_CONFIG["creation_cost"][payment_method]
    
    # Verifica se o jogador tem os recursos
    if payment_method == "gold":
        if player_data.get("gold", 0) < cost:
            await context.bot.answer_callback_query(query.id, f"Você não tem {cost:,} de ouro para fundar um clã.", show_alert=True)
            return ConversationHandler.END # Termina a conversa
    elif payment_method == "dimas":
        if player_data.get("dimas", 0) < cost: # Assumindo que você tem um campo 'dimas'
            await context.bot.answer_callback_query(query.id, f"Você não tem {cost} dimas para fundar um clã.", show_alert=True)
            return ConversationHandler.END

    # Se tiver recursos, guarda o método de pagamento para o próximo passo
    context.user_data['clan_payment_method'] = payment_method
    
    # Pede o nome ao jogador
    await query.edit_message_caption(caption="Excelente! Para fundar o seu clã, por favor, envie agora o nome que deseja para ele. (Use /cancelar para desistir)")
    
    # Avança para o próximo estado: esperar pelo nome
    return ASKING_NAME

async def start_transfer_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_caption(
        caption="👑 Para quem você deseja transferir a liderança do clã? Por favor, envie o nome exato do personagem. (Use /cancelar para desistir)"
    )
    return ASKING_LEADER_TARGET

async def receive_transfer_target_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    leader_id = update.effective_user.id
    target_name = update.message.text
    
    # Precisamos da função que busca um jogador pelo nome do personagem
    target_info = player_manager.find_player_by_character_name(target_name)
    
    if not target_info:
        await update.message.reply_text(f"Nenhum personagem com o nome '{target_name}' foi encontrado. Tente novamente ou use /cancelar.")
        return ASKING_LEADER_TARGET

    target_id = target_info['user_id']
    clan_id = player_manager.get_player_data(leader_id).get("clan_id")
    clan_data = clan_manager.get_clan(clan_id)

    # Validações
    if target_id not in clan_data.get("members", []):
        await update.message.reply_text(f"'{target_name}' é um jogador válido, mas não é membro do seu clã. Tente novamente ou use /cancelar.")
        return ASKING_LEADER_TARGET
        
    if target_id == leader_id:
        await update.message.reply_text("Você não pode transferir a liderança para si mesmo. Tente novamente ou use /cancelar.")
        return ASKING_LEADER_TARGET

    # Guarda o ID do alvo para o passo de confirmação
    context.user_data['transfer_target_id'] = target_id
    
    # Mostra o menu de confirmação
    caption = (
        f"Você tem a certeza que quer transferir a liderança para <b>{target_name}</b>?\n\n"
        f"⚠️ <b>ESTA AÇÃO É IRREVERSÍVEL!</b> ⚠️\n\n"
        f"Você perderá todos os privilégios de líder."
    )
    keyboard = [[
        InlineKeyboardButton("✅ Sim, transferir", callback_data="clan_transfer_do"),
        InlineKeyboardButton("❌ Não, cancelar", callback_data="clan_manage_menu")
    ]]
    
    await update.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    return CONFIRM_LEADER_TRANSFER

# 4. Função final que executa a transferência
async def do_transfer_leadership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    leader_id = update.effective_user.id
    clan_id = player_manager.get_player_data(leader_id).get("clan_id")
    target_id = context.user_data.get('transfer_target_id')

    try:
        clan_manager.transfer_leadership(clan_id, leader_id, target_id)
        
        clan_name = clan_manager.get_clan(clan_id).get("display_name")
        target_name = player_manager.get_player_data(target_id).get("character_name")
        
        await query.edit_message_text(f"A liderança do clã '{clan_name}' foi transferida com sucesso para {target_name}.")
        
        # Notifica o novo líder
        try:
            await context.bot.send_message(chat_id=target_id, text=f"👑 Você é o novo líder do clã '{clan_name}'!")
        except Exception: pass
        
    except ValueError as e:
        await context.bot.answer_callback_query(query.id, f"Erro: {e}", show_alert=True)
    
    # Limpa os dados e termina a conversa
    context.user_data.pop('transfer_target_id', None)
    return ConversationHandler.END

async def cancel_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a conversa de transferência de liderança."""
    user_id = update.effective_user.id
    
    # Limpa os dados específicos desta conversa ('transfer_target_id')
    context.user_data.pop('transfer_target_id', None)
    
    await update.message.reply_text("Transferência de liderança cancelada.")
    
    # Para voltar ao menu de gestão, precisamos de simular um 'update' de callback
    # pois esta função vem de um comando de texto (/cancelar)
    fake_query = type('Query', (), {'data': 'clan_manage_menu', 'answer': lambda: None})()
    fake_update = type('Update', (), {'callback_query': fake_query, 'effective_user': update.effective_user})()
    await show_clan_management_menu(fake_update, context)

    return ConversationHandler.END

async def receive_clan_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    clan_name = update.message.text
    
    # Validação do nome
    if not clan_name or len(clan_name) < 3 or len(clan_name) > 20:
        await context.bot.send_message(chat_id, "Nome inválido. Por favor, escolha um nome entre 3 e 20 caracteres. (Use /cancelar para desistir)")
        return ASKING_NAME # Continua no mesmo estado, a pedir um nome válido
        
    # Recupera o método de pagamento que guardámos
    payment_method = context.user_data.get('clan_payment_method')
    
    # 4. Chama a função do clan_manager para criar o clã
    try:
        clan_id = clan_manager.create_clan(leader_id=user_id, clan_name=clan_name, payment_method=payment_method)
        
        # Atualiza os dados do jogador
        player_data = player_manager.get_player_data(user_id)
        player_data["clan_id"] = clan_id
        player_manager.save_player_data(user_id, player_data)
        
        await context.bot.send_message(chat_id, f"Parabéns! O clã '{clan_name}' foi fundado com sucesso!")

    except ValueError as e: # Trata erros, como nome de clã já existente
        await context.bot.send_message(chat_id, f"Erro: {e}")

    # Limpa os dados da conversa
    context.user_data.pop('clan_payment_method', None)
    
    # Termina a conversa
    return ConversationHandler.END

# Em handlers/guild_handler.py
async def confirm_mission_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    clan_id = player_manager.get_player_data(user_id).get("clan_id")
    mission_id = query.data.split(':')[1]

    try:
        # Chama a nossa nova função de backend
        clan_manager.assign_mission_to_clan(clan_id, mission_id, user_id)
        
        mission_title = GUILD_MISSIONS_CATALOG[mission_id]['title']
        await context.bot.answer_callback_query(query.id, f"Missão '{mission_title}' iniciada!", show_alert=True)

        # Opcional: Notificar todos os membros do clã
        clan_data = clan_manager.get_clan(clan_id)
        for member_id in clan_data.get("members", []):
            if member_id != user_id:
                try:
                    await context.bot.send_message(chat_id=member_id, text=f"🎯 O líder iniciou uma nova missão de guilda: {mission_title}!")
                except Exception:
                    pass # Ignora se o membro bloqueou o bot

    except ValueError as e:
        await context.bot.answer_callback_query(query.id, str(e), show_alert=True)

    # No final, atualiza e volta ao painel principal do clã
    await show_clan_dashboard(update, context)

async def cancel_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id
    context.user_data.pop('clan_payment_method', None)
    await context.bot.send_message(chat_id, "Criação de clã cancelada.")
    # Aqui, poderíamos chamar a função para mostrar o menu do reino de novo
    return ConversationHandler.END

# 6. Montagem final do ConversationHandler
clan_creation_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_clan_creation, pattern=r'^clan_create_start:(gold|dimas)$')],
    states={
        ASKING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_clan_name)],
    },
    fallbacks=[CommandHandler('cancelar', cancel_creation)],
)

# Em handlers/guild_handler.py
# Substitua a sua guild_menu_callback (versão de debug) por esta versão final

async def guild_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    player_data = player_manager.get_player_data(user_id)
    
    # 1. Determina qual mídia mostrar
    media_to_show = None
    clan_id = player_data.get("clan_id")
    if clan_id:
        clan_data = clan_manager.get_clan(clan_id)
        if clan_data:
            # Tenta pegar a logo customizada do clã
            media_to_show = clan_data.get("logo_media")

    # Se não encontrou uma logo customizada, usa a genérica
    if not media_to_show:
        media_to_show = file_ids.get_file_data("menu_guilda_generico")

    # 2. Monta a mensagem e os botões
    caption = "Você está nos portões da Guilda dos Aventureiros. O que deseja fazer?"
    keyboard = [
        [InlineKeyboardButton("꧁𓊈𒆜🅲🅻🅰🅽𒆜𓊉꧂", callback_data='clan_menu:guild_menu')],
        [InlineKeyboardButton("📜 𝐌𝐢𝐧𝐡𝐚𝐬 𝐌𝐢𝐬𝐬õ𝐞𝐬 𝐃𝐢á𝐫𝐢𝐚𝐬 📜", callback_data='guild_missions')],
        [InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫 𝐚 𝐀𝐯𝐞𝐧𝐭𝐮𝐫𝐚 ⬅️", callback_data='continue_after_action')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # 3. Envia a mensagem com a mídia
    try:
        if media_to_show and media_to_show.get("id"):
            file_id = media_to_show["id"]
            media_type = media_to_show.get("type", "photo")
            
            if media_type == "video":
                media_input = InputMediaVideo(media=file_id, caption=caption)
            else:
                media_input = InputMediaPhoto(media=file_id, caption=caption)
            
            await query.edit_message_media(media=media_input, reply_markup=reply_markup)
        else:
            # Fallback se não houver mídia definida
            await query.edit_message_caption(caption=caption, reply_markup=reply_markup)
            
    except Exception as e:
        logger.error(f"Erro ao exibir mídia da guilda: {e}")
        # Fallback de segurança para apenas editar o texto
        await query.edit_message_caption(caption=caption, reply_markup=reply_markup)

# --- Handler do menu do Clã (com a lógica de verificação) ---
async def clan_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    player_data = player_manager.get_player_data(user_id)

    origem = 'guild_menu'
    if ':' in query.data:
        try:
            origem = query.data.split(':')[1]
        except IndexError:
            pass
            
    if player_data.get("clan_id"):
        await show_clan_dashboard(update, context, came_from=origem)
    else:
        await show_create_clan_menu(update, context, came_from=origem)

# --- Função que mostra o menu de criação ---
# Em handlers/guild_handler.py

async def show_create_clan_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, came_from: str = 'guild_menu'):
    query = update.callback_query
    
    # Lendo os custos do arquivo de configuração (mais profissional)
    custo_ouro = game_data.CLAN_CONFIG['creation_cost']['gold']
    custo_dimas = game_data.CLAN_CONFIG['creation_cost']['dimas']

    caption = (
        "Você ainda não faz parte de um clã.\n\n"
        "Criar um novo clã une aventureiros sob um mesmo estandarte, "
        "permitindo o acesso a benefícios e missões exclusivas.\n\n"
        f"<b>Custo para fundar um clã:</b>\n"
        f"- 🪙 {custo_ouro:,} Ouro\n"
        f"- 💎 {custo_dimas} Diamantes" # Corrigido para "Diamantes"
    )

    keyboard = [
        [InlineKeyboardButton("🔎 Procurar Clã", callback_data='clan_search_start')],
        [InlineKeyboardButton(f"🪙 Fundar com Ouro", callback_data='clan_create_start:gold')],
        [InlineKeyboardButton(f"💎 Fundar com Diamantes", callback_data='clan_create_start:dimas')],
        # O botão "Voltar" agora usa a variável 'came_from' para saber para onde voltar
        [InlineKeyboardButton("⬅️ Voltar", callback_data=came_from)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_caption(caption=caption, reply_markup=reply_markup, parse_mode='HTML')
    
async def show_clan_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE, came_from: str = 'guild_menu'):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    player_data = player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")
    
    if not clan_id:
        await show_create_clan_menu(update, context, came_from=came_from)
        return
        
    clan_data = clan_manager.get_clan(clan_id)
    if not clan_data:
        player_data["clan_id"] = None
        player_manager.save_player_data(user_id, player_data)
        await query.edit_message_caption(caption="Erro: O clã ao qual você pertencia não foi encontrado.")
        return

    # --- Lógica de obter dados do clã (sem alterações) ---
    clan_name = clan_data.get("display_name", "Clã Sem Nome")
    clan_level = clan_data.get("prestige_level", 1)
    clan_points = clan_data.get("prestige_points", 0)
    member_ids = clan_data.get("members", [])
    leader_id = clan_data.get("leader_id")
    level_info = CLAN_PRESTIGE_LEVELS.get(clan_level, {})
    level_title = level_info.get("title", "")
    max_members = level_info.get("max_members", 5)
    points_needed = level_info.get("points_to_next_level", 'MAX')

    # --- CONSTRUÇÃO DA MENSAGEM ---
    caption = f"⚜️ <b>Painel do Clã: {clan_name}</b> ⚜️\n\n"
    caption += f"<b>Nível:</b> {clan_level} ({level_title})\n"
    caption += f"<b>Membros:</b> {len(member_ids)} / {max_members}\n"
    
    if points_needed != 'MAX':
        progress_bar = _create_progress_bar(clan_points, points_needed)
        caption += f"<b>Prestígio:</b> {progress_bar} {clan_points}/{points_needed}\n"
    else:
        caption += "<b>Prestígio:</b> Nível Máximo!\n"
        
    # ===============================================
    # ## INÍCIO DA CORREÇÃO: MOSTRAR BUFFS ATIVOS ##
    # ===============================================
    clan_buffs = clan_manager.get_clan_buffs(clan_id)
    if clan_buffs:
        caption += "\n<b>Buffs Ativos do Clã:</b>\n"
        caption += _format_buffs_text(clan_buffs)
    # ===============================================
    # ## FIM DA CORREÇÃO ##
    # ===============================================
        
    caption += "\n<b>Missão do Clã Ativa:</b>\n"
    active_mission = clan_manager.get_active_guild_mission(clan_id)
    
    if active_mission:
        progress = active_mission.get("current_progress", 0)
        target = active_mission.get("target_count", 1)
        mission_bar = _create_progress_bar(progress, target)
        caption += f"📜 {active_mission.get('title', '...')}\n"
        caption += f"🎯 {mission_bar} {progress}/{target}\n"
    else:
        caption += "💤 Nenhuma missão ativa no momento.\n"
        
    caption += "\n<b>Membros do Clã:</b>\n"
    for member_id in member_ids:
        member_data = player_manager.get_player_data(member_id)
        member_name = member_data.get("character_name", "Desconhecido")
        is_leader_icon = "👑" if member_id == leader_id else ""
        caption += f"- {member_name} {is_leader_icon}\n"
        
    # --- CONSTRUÇÃO DOS BOTÕES (sem alterações) ---
    keyboard = []
    if active_mission:
        keyboard.append([InlineKeyboardButton("📜 Ver Detalhes da Missão", callback_data='clan_guild_mission_details')])
        keyboard.append([InlineKeyboardButton("🏦 Banco do Clã", callback_data='clan_bank_menu')])

    if user_id == leader_id:
        if len(member_ids) < max_members:
            keyboard.append([InlineKeyboardButton("➕ Convidar Jogador", callback_data='clan_invite_start')])
        
        pending_count = len(clan_data.get("pending_applications", []))
        if pending_count > 0:
            button_text = f"📩 Gerir Candidaturas ({pending_count})"
            keyboard.append([InlineKeyboardButton(button_text, callback_data='clan_manage_apps')])

        keyboard.append([InlineKeyboardButton("✏️ Gerir Clã", callback_data='clan_manage_menu')])

    keyboard.append([InlineKeyboardButton("🚪 Sair do Clã", callback_data='clan_leave_confirm')])
    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data=came_from)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    media_to_show = clan_data.get("logo_media")
    if not media_to_show:
        media_to_show = file_ids.get_file_data("menu_guilda_generico")

    try:
        # Apaga a mensagem anterior para evitar conflitos de edição
        await query.delete_message()
    except Exception:
        pass # Ignora se a mensagem já foi apagada

    # Envia uma nova mensagem com a mídia correta
    try:
        if media_to_show and media_to_show.get("file_id"):
            file_id = media_to_show["file_id"]
            media_type = media_to_show.get("type", "photo")
            
            if media_type == "video":
                await context.bot.send_video(chat_id=query.message.chat_id, video=file_id, caption=caption, reply_markup=reply_markup, parse_mode='HTML')
            else:
                await context.bot.send_photo(chat_id=query.message.chat_id, photo=file_id, caption=caption, reply_markup=reply_markup, parse_mode='HTML')
        else:
            # Fallback final se nenhuma mídia for encontrada
            await context.bot.send_message(chat_id=query.message.chat_id, text=caption, reply_markup=reply_markup, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Erro ao enviar mídia do painel do clã: {e}")
        # Fallback de segurança se o file_id for inválido
        await context.bot.send_message(chat_id=query.message.chat_id, text=caption, reply_markup=reply_markup, parse_mode='HTML')

def _format_buffs_text(buffs_dict: dict) -> str:
    """Formata um dicionário de buffs numa string legível."""
    if not buffs_dict:
        return "  - Nenhum\n"
    
    text = ""
    if buffs_dict.get("xp_bonus_percent"):
        text += f"  - Bónus de XP: +{buffs_dict['xp_bonus_percent']}%\n"
    if buffs_dict.get("gold_bonus_percent"):
        text += f"  - Bónus de Ouro: +{buffs_dict['gold_bonus_percent']}%\n"
    if buffs_dict.get("all_stats_percent"):
        text += f"  - Bónus de Atributos: +{buffs_dict['all_stats_percent']}%\n"
    if buffs_dict.get("crafting_speed_percent"):
        text += f"  - Velocidade de Produção: +{buffs_dict['crafting_speed_percent']}%\n"
    # Adicione outros buffs que você criar aqui
    
    return text if text else "  - Nenhum\n"

def _create_progress_bar(current: int, required: int, length: int = 10) -> str:
    """Cria uma barra de progresso em texto. Ex: [█████-----]"""
    if required == 0: return "[----------]"
    progress = min(1.0, current / required)
    filled_length = int(progress * length)
    bar = '⬛️' * filled_length + '◻️' * (length - filled_length)
    return f"[{bar}]"

# Adicione esta NOVA função ao seu handlers/guild_handler.py

async def show_guild_mission_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra os detalhes da missão de guilda ativa."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    clan_id = player_manager.get_player_data(user_id).get("clan_id")

    active_mission = clan_manager.get_active_guild_mission(clan_id)
    
    if not active_mission:
        await query.edit_message_caption(
            caption="O seu clã não tem uma missão ativa no momento.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="clan_menu")]])
        )
        return

    # Formata os detalhes da missão
    progress = active_mission.get("current_progress", 0)
    target = active_mission.get("target_count", 1)
    mission_bar = _create_progress_bar(progress, target)
    
    caption = f"📜 <b>Detalhes da Missão: {active_mission.get('title')}</b>\n\n"
    caption += f"<i>{active_mission.get('description')}</i>\n\n"
    caption += f"<b>Progresso:</b> {mission_bar} {progress}/{target}\n"
    
    # Formata as recompensas para exibição
    rewards = active_mission.get("rewards", {})
    if rewards:
        caption += "\n<b>Recompensas pela Conclusão:</b>\n"
        if "guild_xp" in rewards:
            caption += f"- Prestígio para o Clã: {rewards['guild_xp']} ✨\n"
        if "gold_per_member" in rewards:
            caption += f"- Ouro para cada membro: {rewards['gold_per_member']} 🪙\n"
        # Adicione aqui a formatação para outras recompensas, como itens.

    keyboard = [[InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="clan_menu")]]
    
    await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def show_clan_upgrade_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    player_data = player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")
    if not clan_id:
        await query.edit_message_caption(caption="Você não está em um clã.")
        return
        
    clan_data = clan_manager.get_clan(clan_id)
    
    # 1. Verificação de Liderança
    if clan_data.get("leader_id") != user_id:
        await context.bot.answer_callback_query(query.id, "Apenas o líder do clã pode aceder a este menu.", show_alert=True)
        return
        
    # 2. Obter dados do nível atual e do próximo
    current_level = clan_data.get("prestige_level", 1)
    current_points = clan_data.get("prestige_points", 0)
    
    current_level_info = CLAN_PRESTIGE_LEVELS.get(current_level, {})
    next_level_info = CLAN_PRESTIGE_LEVELS.get(current_level + 1) # Será None se for o nível máximo

    # 3. Construir a mensagem
    caption = f"⚜️ <b>Aprimorar Clã: {clan_data.get('display_name')}</b> ⚜️\n\n"
    caption += f"<b>Nível de Prestígio Atual:</b> {current_level} ({current_level_info.get('title', '')})\n"
    
    # Buffs Atuais
    caption += "<b>Buffs Ativos:</b>\n"
    caption += _format_buffs_text(current_level_info.get("buffs", {}))
    
    keyboard = []
    
    # Se não for o nível máximo, mostra o progresso e os próximos buffs
    if next_level_info:
        points_needed = current_level_info.get("points_to_next_level", 9999)
        progress_bar = _create_progress_bar(current_points, points_needed)
        
        caption += f"\n<b>Progresso para o Nível {current_level + 1}:</b>\n"
        caption += f"Prestigio: {progress_bar} {current_points}/{points_needed}\n"
        
        caption += "\n<b>Benefícios do Próximo Nível:</b>\n"
        caption += f"  - Membros: {next_level_info.get('max_members', 0)}\n"
        caption += _format_buffs_text(next_level_info.get("buffs", {}))

        upgrade_cost = next_level_info.get("upgrade_cost", {})
        cost_gold = upgrade_cost.get("gold", 0)
        cost_dimas = upgrade_cost.get("dimas", 0)
        
        caption += f"\n<b>Custo do Aprimoramento:</b>\n"
        caption += f"  - 🪙 {cost_gold:,} Ouro\n"
        caption += f"  - 💎 {cost_dimas} Dimas\n"
        
        # 4. Adicionar botões de aprimoramento apenas se tiver pontos suficientes
        if current_points >= points_needed:
            caption += "\n<b>Você tem prestígio suficiente para aprimorar!</b>"
            keyboard.append([
                InlineKeyboardButton(f"🪙 Aprimorar com Ouro", callback_data=f'clan_upgrade_confirm:gold'),
                InlineKeyboardButton(f"💎 Aprimorar com Dimas", callback_data=f'clan_upgrade_confirm:dimas'),
            ])
    else:
        caption += "\n<b>O seu clã já atingiu o nível máximo de prestígio!</b>"

    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Clã", callback_data='clan_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_caption(caption=caption, reply_markup=reply_markup, parse_mode='HTML')

async def show_clan_bank_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o menu principal do banco do clã, com saldo e opções."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    player_data = player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")
    if not clan_id:
        # Medida de segurança, caso o jogador seja expulso enquanto navega
        await query.edit_message_caption(caption="Você não está mais em um clã.")
        return
        
    clan_data = clan_manager.get_clan(clan_id)
    
    # Pega o saldo de ouro do banco
    bank_gold = clan_data.get("bank", {}).get("gold", 0)
    
    caption = (
        f"🏦 <b>Banco do Clã: {clan_data.get('display_name')}</b>\n\n"
        f"Bem-vindo ao cofre do clã. Todas as transações são finais.\n\n"
        f"<b>Saldo Atual:</b>\n"
        f"🪙 {bank_gold:,} Ouro"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📥 Depositar Ouro", callback_data="clan_bank_deposit_start"),
            # O botão de levantar só aparece para o líder
            InlineKeyboardButton("📤 Levantar Ouro", callback_data="clan_bank_withdraw_start")
        ],
        [InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="clan_menu")]
    ]
    
    # Regra de permissão: apenas o líder vê o botão de levantar
    if clan_data.get("leader_id") != user_id:
        # Remove o botão "Levantar Ouro" se o jogador não for o líder
        keyboard[0].pop(1)

    await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')


async def start_clan_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_caption(caption="Qual o nome do clã que você procura? (Use /cancelar para desistir)")
    return ASKING_SEARCH_NAME

async def show_applications_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    clan_id = player_manager.get_player_data(user_id).get("clan_id")
    clan_data = clan_manager.get_clan(clan_id)

    # Segurança: só o líder pode ver
    if not clan_data or clan_data.get("leader_id") != user_id:
        return

    applications = clan_data.get("pending_applications", [])
    caption = "<b>📩 Candidaturas Pendentes</b>\n\n"
    keyboard = []

    if not applications:
        caption += "Não há nenhuma candidatura pendente no momento."
    else:
        for applicant_id in applications:
            applicant_data = player_manager.get_player_data(applicant_id)
            applicant_name = applicant_data.get("character_name", f"ID: {applicant_id}")
            
            # Adiciona uma linha para cada candidato com botões
            keyboard.append([
                InlineKeyboardButton(f"{applicant_name}", callback_data="noop"), # Botão não clicável com o nome
                InlineKeyboardButton("✅ Aceitar", callback_data=f'clan_app_accept:{applicant_id}'),
                InlineKeyboardButton("❌ Recusar", callback_data=f'clan_app_decline:{applicant_id}'),
            ])

    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data='clan_menu')])
    await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def accept_application_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    leader_id = update.effective_user.id
    clan_id = player_manager.get_player_data(leader_id).get("clan_id")
    applicant_id = int(query.data.split(':')[1])

    try:
        clan_manager.accept_application(clan_id, applicant_id)
        
        # Atualiza os dados do novo membro
        applicant_data = player_manager.get_player_data(applicant_id)
        applicant_data["clan_id"] = clan_id
        player_manager.save_player_data(applicant_id, applicant_data)

        # Notifica o candidato
        clan_name = clan_manager.get_clan(clan_id).get("display_name")
        await context.bot.send_message(chat_id=applicant_id, text=f"🎉 Parabéns! A sua candidatura ao clã '{clan_name}' foi aceite!")
        
    except ValueError as e:
        await context.bot.answer_callback_query(query.id, f"Erro: {e}", show_alert=True)
    
    # Atualiza o menu de candidaturas
    await show_applications_menu(update, context)

async def decline_application_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    leader_id = update.effective_user.id
    clan_id = player_manager.get_player_data(leader_id).get("clan_id")
    applicant_id = int(query.data.split(':')[1])

    clan_manager.decline_application(clan_id, applicant_id)
    
    # Notifica o candidato (opcional)
    clan_name = clan_manager.get_clan(clan_id).get("display_name")
    await context.bot.send_message(chat_id=applicant_id, text=f"A sua candidatura ao clã '{clan_name}' foi recusada.")

    # Atualiza o menu
    await show_applications_menu(update, context)


async def receive_clan_search_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id
    clan_name_searched = update.message.text
    
    clan_data = clan_manager.find_clan_by_display_name(clan_name_searched)
    
    if not clan_data:
        await update.message.reply_text(f"Nenhum clã com o nome '{clan_name_searched}' foi encontrado. Tente novamente ou use /cancelar.")
        return ASKING_SEARCH_NAME

    # Mostra as informações do clã encontrado
    clan_id = clan_data.get("id")
    clan_name = clan_data.get("display_name")
    leader_data = player_manager.get_player_data(clan_data.get("leader_id"))
    leader_name = leader_data.get("character_name", "Desconhecido")
    member_count = len(clan_data.get("members", []))
    
    caption = (
        f"<b>Clã Encontrado:</b> {clan_name}\n"
        f"<b>Líder:</b> {leader_name}\n"
        f"<b>Membros:</b> {member_count}\n\n"
        f"Deseja enviar um pedido para se juntar a este clã?"
    )
    
    keyboard = [[
        InlineKeyboardButton("✅ Sim, enviar pedido", callback_data=f'clan_apply:{clan_id}'),
        InlineKeyboardButton("⬅️ Voltar", callback_data='guild_menu'),
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(caption, reply_markup=reply_markup, parse_mode='HTML')
    return ConversationHandler.END

# 4. Função para o clique no botão "Aplicar para Entrar" (handler separado)
async def apply_to_clan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    clan_id_to_join = query.data.split(':')[1]
    
    try:
        clan_manager.add_application(clan_id_to_join, user_id)
        await query.edit_message_text("Seu pedido foi enviado ao líder do clã. Você será notificado se for aceite.")
        # Opcional: notificar o líder do clã sobre a nova candidatura
    except ValueError as e:
        await context.bot.answer_callback_query(query.id, f"Erro: {e}", show_alert=True)

# 5. O ConversationHandler de busca
clan_search_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_clan_search, pattern=r'^clan_search_start$')],
    states={
        ASKING_SEARCH_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_clan_search_name)],
    },
    fallbacks=[CommandHandler('cancelar', cancel_creation)], # Reutiliza a função de cancelar
)

async def show_leave_clan_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    caption = "Tem a certeza que deseja sair do seu clã? Esta ação não pode ser desfeita."
    keyboard = [[
        InlineKeyboardButton("✅ 𝐒𝐢𝐦, 𝐝𝐞𝐬𝐞𝐣𝐨 𝐬𝐚𝐢𝐫", callback_data="clan_leave_do"),
        InlineKeyboardButton("❌ 𝐍ã𝐨, 𝐪𝐮𝐞𝐫𝐨 𝐟𝐢𝐜𝐚𝐫", callback_data="clan_menu") # Volta ao painel
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_caption(caption=caption, reply_markup=reply_markup)

# Em handlers/guild_handler.py

async def show_clan_management_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    caption = "✏️ <b>Gestão do Clã</b>\n\nSelecione uma opção:"
    keyboard = [
        # =======================================================
        # ## O BOTÃO DEVE ESTAR AQUI ##
        # =======================================================
        [InlineKeyboardButton("🖼️ Alterar Logo do Clã", callback_data='clan_logo_start')],
        # =======================================================
        
        [InlineKeyboardButton("🎯 Iniciar Missão de Guilda", callback_data='clan_mission_start')],
        [InlineKeyboardButton("👟 Expulsar Membro", callback_data='clan_kick_menu')],
        [InlineKeyboardButton("👑 Transferir Liderança", callback_data='clan_transfer_leader_start')],
        [InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data='clan_menu')]
    ]
    await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def show_mission_selection_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    clan_id = player_manager.get_player_data(user_id).get("clan_id")
    clan_data = clan_manager.get_clan(clan_id)

    # Validações (apenas líder, sem missão ativa)
    if not clan_data or clan_data.get("leader_id") != user_id: return
    if "active_mission" in clan_data and clan_data.get("active_mission"):
        await context.bot.answer_callback_query(query.id, "O seu clã já tem uma missão ativa.", show_alert=True)
        return

    # Pega 3 missões aleatórias do catálogo
    mission_ids = list(GUILD_MISSIONS_CATALOG.keys())
    # Garante que não tentamos pegar mais missões do que as que existem
    sample_size = min(3, len(mission_ids))
    random_mission_ids = random.sample(mission_ids, sample_size)
    
    caption = "🎯 <b>Escolha a Próxima Missão</b>\n\nSelecione uma das missões abaixo para a sua guilda:"
    keyboard = []
    for mission_id in random_mission_ids:
        mission = GUILD_MISSIONS_CATALOG[mission_id]
        button_text = f"📜 {mission['title']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"clan_mission_confirm:{mission_id}")])

    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data='clan_manage_menu')])
    await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# 2. Mostra a lista de membros para expulsar
async def show_kick_member_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    clan_id = player_manager.get_player_data(user_id).get("clan_id")
    clan_data = clan_manager.get_clan(clan_id)

    caption = "👟 <b>Expulsar Membro</b>\n\nSelecione o membro que deseja remover do clã:"
    keyboard = []
    
    # Lista todos os membros, exceto o próprio líder
    for member_id in clan_data.get("members", []):
        if member_id != user_id: # O líder não pode expulsar-se a si mesmo
            member_data = player_manager.get_player_data(member_id)
            member_name = member_data.get("character_name", f"ID: {member_id}")
            keyboard.append([InlineKeyboardButton(f"❌ {member_name}", callback_data=f'clan_kick_confirm:{member_id}')])

    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data='clan_manage_menu')])
    await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# 3. Mostra a confirmação final
async def show_kick_confirm_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    member_id_to_kick = int(query.data.split(':')[1])
    member_data = player_manager.get_player_data(member_id_to_kick)
    member_name = member_data.get("character_name", "este membro")

    caption = f"Tem a certeza que deseja expulsar <b>{member_name}</b> do clã? Esta ação é irreversível."
    keyboard = [
        [InlineKeyboardButton("✅ 𝐒𝐢𝐦, 𝐞𝐱𝐩𝐮𝐥𝐬𝐚𝐫", callback_data=f'clan_kick_do:{member_id_to_kick}'),
         InlineKeyboardButton("❌ 𝐍ã𝐨", callback_data='clan_kick_menu')]
    ]
    await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def do_kick_member_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    leader_id = update.effective_user.id
    clan_id = player_manager.get_player_data(leader_id).get("clan_id")
    clan_data = clan_manager.get_clan(clan_id)
    
    # Segurança extra: só o líder pode executar esta ação
    if clan_data.get("leader_id") != leader_id:
        return

    member_id_to_kick = int(query.data.split(':')[1])
    member_data = player_manager.get_player_data(member_id_to_kick)
    member_name = member_data.get("character_name", "O jogador")

    try:
        # Reutilizamos a função que já tínhamos!
        clan_manager.remove_member(clan_id, member_id_to_kick)

        # Limpa o ID do clã dos dados do jogador expulso
        member_data["clan_id"] = None
        player_manager.save_player_data(member_id_to_kick, member_data)
        
        await context.bot.answer_callback_query(query.id, f"{member_name} foi expulso do clã.")

        # Notifica o jogador expulso
        clan_name = clan_data.get("display_name")
        try:
            await context.bot.send_message(chat_id=member_id_to_kick, text=f"Você foi expulso do clã '{clan_name}' pelo líder.")
        except Exception:
            pass # Ignora se o jogador bloqueou o bot

    except ValueError as e:
        await context.bot.answer_callback_query(query.id, f"Erro: {e}", show_alert=True)
    
    # Atualiza a lista de membros a expulsar
    await show_kick_member_menu(update, context)

# 2. Processa a saída após a confirmação
async def do_leave_clan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    player_data = player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")

    if not clan_id:
        await query.edit_message_caption(caption="Você não está em um clã.")
        return
        
    try:
        # A nossa nova função clan_manager já tem a regra que impede o líder de sair
        clan_manager.remove_member(clan_id, user_id)
        
        # Limpa o ID do clã dos dados do jogador
        player_data["clan_id"] = None
        player_manager.save_player_data(user_id, player_data)
        
        clan_name = clan_manager.get_clan(clan_id).get("display_name")
        await query.edit_message_text(f"Você saiu do clã '{clan_name}'.")

        # Notifica o líder que um membro saiu (opcional)
        leader_id = clan_manager.get_clan(clan_id).get("leader_id")
        if leader_id:
            member_name = player_data.get("character_name", "Um membro")
            try:
                await context.bot.send_message(chat_id=leader_id, text=f"O jogador {member_name} saiu do seu clã.")
            except Exception:
                pass # Ignora se o líder bloqueou o bot
                
    except ValueError as e:
        await context.bot.answer_callback_query(query.id, str(e), show_alert=True)
        # Se deu erro (líder a tentar sair), volta ao painel do clã
        await show_clan_dashboard(update, context)

async def confirm_clan_upgrade_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    clan_id = player_manager.get_player_data(user_id).get("clan_id")
    
    # Extrai o método de pagamento do botão (gold ou dimas)
    payment_method = query.data.split(':')[1]
    
    try:
        # Chama a função do manager que faz todo o trabalho pesado
        clan_manager.level_up_clan(clan_id, user_id, payment_method)
        
        clan_data = clan_manager.get_clan(clan_id)
        clan_name = clan_data.get("display_name")
        new_level = clan_data.get("prestige_level")

        # Notifica o líder
        await context.bot.answer_callback_query(query.id, f"Parabéns! O clã {clan_name} subiu para o nível de prestígio {new_level}!", show_alert=True)
        
        # Notifica todos os membros (opcional, mas muito bom!)
        for member_id in clan_data.get("members", []):
            if member_id != user_id: # Não notifica o líder duas vezes
                try:
                    await context.bot.send_message(chat_id=member_id, text=f"🎉 Boas notícias! O seu clã, {clan_name}, subiu para o nível de prestígio {new_level}!")
                except Exception:
                    pass # Ignora se o membro bloqueou o bot

    except ValueError as e:
        # Mostra o erro se alguma verificação falhar (ex: sem dinheiro)
        await context.bot.answer_callback_query(query.id, str(e), show_alert=True)
        
    # Atualiza o menu do painel do clã
    await show_clan_dashboard(update, context)


async def show_missions_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    missions_data = mission_manager.get_player_missions(user_id)
    active_missions = missions_data.get("active_missions", [])
    rerolls_left = missions_data.get("daily_rerolls_left", 0)
    
    # Esta função agora simplesmente monta e exibe a lista atual de missões.
    caption = f"📜 <b>Missões Diárias</b>\n"
    caption += f"🔄 Você pode atualizar {rerolls_left} missões hoje.\n\n"
    
    keyboard = []
    
    if not active_missions:
        caption += "Um novo dia, novas missões! Boa sorte."
    
    for i, mission_state in enumerate(active_missions):
        template = next((m for m in MISSION_CATALOG if m["id"] == mission_state["mission_id"]), None)
        if not template: continue

        progress = mission_state.get("progress", 0)
        target = template.get("target_count", 1)
        
        status_icon = ""
        progress_text = ""
        buttons = []

        if mission_state.get("is_claimed"):
            # Este estado agora será muito raro, pois a missão é substituída
            status_icon = "🏅"
            progress_text = "(Reclamada)"
        elif mission_state.get("is_complete"):
            status_icon = "✅"
            progress_text = "<b>(Completa!)</b>"
            buttons.append(InlineKeyboardButton("🏆 Reclamar Recompensa", callback_data=f"mission_claim:{i}"))
        else:
            status_icon = "⏳"
            progress_text = f"({progress}/{target})"
            if rerolls_left > 0:
                buttons.append(InlineKeyboardButton("🔄 𝐀𝐭𝐮𝐚𝐥𝐢𝐳𝐚𝐫", callback_data=f"mission_reroll:{i}"))
        
        caption += f"<b>{status_icon} {template['title']}</b>: {template['description']} {progress_text}\n"
        
        if buttons:
            keyboard.append(buttons)

    keyboard.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data='guild_menu')])
    await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# Em handlers/guild_handler.py
# Substitua a sua função claim_reward_callback inteira por esta:

async def claim_reward_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Processa o clique no botão de reclamar recompensa, envia uma notificação
    detalhada e atualiza o menu de missões.
    """
    query = update.callback_query
    await query.answer() # Responde ao clique imediatamente
    
    user_id = update.effective_user.id
    mission_index = int(query.data.split(':')[1])
    
    player_data = player_manager.get_player_data(user_id)
    if not player_data:
        await query.answer("Erro: Não foi possível encontrar os dados do seu personagem.", show_alert=True)
        return

    # A função claim_reward modifica o player_data e retorna o dicionário de recompensas
    rewards = mission_manager.claim_reward(player_data, mission_index)
    
    if rewards:
        # Salva os dados do jogador com a nova missão já no lugar
        player_manager.save_player_data(user_id, player_data)
        
        # --- NOVA LÓGICA DE NOTIFICAÇÃO ---
        rewards_text = "<b>Recompensas Recebidas:</b>\n"
        if "xp" in rewards:
            rewards_text += f"- {rewards['xp']} XP ✨\n"
        if "gold" in rewards:
            rewards_text += f"- {rewards['gold']} Ouro 🪙\n"
        if "prestige_points" in rewards:
             rewards_text += f"- {rewards['prestige_points']} Pontos de Prestígio ⚜️\n"
        # Adicione aqui outros tipos de recompensa que você tiver

        # Envia a mensagem de recompensa e apaga a mensagem antiga do menu
        try:
            await query.delete_message()
        except Exception:
            pass
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ <b>Missão Concluída!</b>\n\n{rewards_text}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📜 Ver Novas Missões", callback_data="guild_missions")]]),
            parse_mode='HTML'
        )
        # ------------------------------------
        
    else:
        # Se, por algum motivo, não houver recompensas, apenas atualiza o menu
        await context.bot.answer_callback_query(query.id, "Recompensa reclamada!", show_alert=True)
        await show_missions_menu(update, context)
        
async def reroll_mission_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    mission_index = int(query.data.split(':')[1])
    success = mission_manager.reroll_mission(update.effective_user.id, mission_index)
    
    if success:
        await context.bot.answer_callback_query(query.id, "Missão atualizada!")
    else:
        await context.bot.answer_callback_query(query.id, "Não foi possível atualizar a missão.", show_alert=True)

    await show_missions_menu(update, context) # Atualiza o menu

# Adicione estas 3 funções ao handlers/guild_handler.py

async def start_deposit_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia a conversa para depositar ouro."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_caption(
        caption="📥 Quanto ouro você deseja depositar no banco do clã? Por favor, envie um número. (Use /cancelar para desistir)"
    )
    return ASKING_DEPOSIT_AMOUNT

# Adicione estas 2 funções ao handlers/guild_handler.py

async def start_withdraw_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia a conversa para levantar ouro."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_caption(
        caption="📤 Quanto ouro você deseja levantar do banco do clã? Por favor, envie um número. (Use /cancelar para desistir)"
    )
    return ASKING_WITHDRAW_AMOUNT

async def receive_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe a quantia de ouro a levantar e processa a transação."""
    user_id = update.effective_user.id
    clan_id = player_manager.get_player_data(user_id).get("clan_id")
    
    try:
        amount = int(update.message.text)
        if amount <= 0:
            await update.message.reply_text("Por favor, envie um número positivo.")
            return ASKING_WITHDRAW_AMOUNT

        # Chama a função do backend que já tem a regra de permissão do líder
        clan_manager.withdraw_gold_from_bank(clan_id, user_id, amount)
        
        await update.message.reply_text(f"✅ Você levantou {amount:,} de ouro com sucesso!")

    except ValueError as e:
        await update.message.reply_text(f"❌ Erro: {e}")
    except Exception:
        await update.message.reply_text("❌ Quantia inválida. Por favor, envie apenas números.")
        return ASKING_WITHDRAW_AMOUNT

    await show_clan_dashboard(update, context)
    return ConversationHandler.END

# Em handlers/guild_handler.py
# SUBSTITUA a função receive_clan_logo por esta:

async def start_logo_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia a conversa para o líder enviar a logo do clã."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_caption(
        caption="🖼️ Por favor, envie a foto ou o vídeo que você deseja usar como logo para o seu clã. (Use /cancelar para desistir)"
    )
    return ASKING_CLAN_LOGO

async def receive_clan_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe uma foto ou vídeo, guarda os seus dados e termina a conversa."""
    user_id = update.effective_user.id
    clan_id = player_manager.get_player_data(user_id).get("clan_id")
    
    media_data = {}
    if update.message and update.message.photo:
        # Se for uma foto, pega o ID e o tipo
        media_data["file_id"] = update.message.photo[-1].file_id
        media_data["type"] = "photo"
    elif update.message and update.message.video:
        # Se for um vídeo, pega o ID e o tipo
        media_data["file_id"] = update.message.video.file_id
        media_data["type"] = "video"
    else:
        await update.message.reply_text("Arquivo inválido. Por favor, envie uma foto ou um vídeo.")
        return ASKING_CLAN_LOGO

    try:
        # Chama a função do backend para salvar os dados da mídia
        clan_manager.set_clan_media(clan_id, user_id, media_data)
        await update.message.reply_text("✅ Logo do clã atualizada com sucesso!")
        
    except ValueError as e:
        await update.message.reply_text(f"❌ Erro: {e}")

    # Volta ao menu de gestão do clã
    await show_clan_management_menu(update, context)
    return ConversationHandler.END

async def cancel_logo_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela o processo de upload da logo."""
    await update.message.reply_text("Upload da logo cancelado.")
    await show_clan_management_menu(update, context)
    return ConversationHandler.END

# Definição do ConversationHandler atualizado
clan_logo_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_logo_upload, pattern=r'^clan_logo_start$')],
    states={
        # O filtro agora aceita FOTO OU VÍDEO, e chama a nova função
        ASKING_CLAN_LOGO: [MessageHandler(filters.PHOTO | filters.VIDEO & ~filters.COMMAND, receive_clan_media)],
    },
    fallbacks=[CommandHandler('cancelar', cancel_logo_upload)],
)

async def handle_clan_mission_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Esta função é um "roteador". Ela é chamada quando o líder clica em
    "Iniciar Missão de Guilda" e decide qual menu mostrar.
    """
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    clan_id = player_manager.get_player_data(user_id).get("clan_id")
    clan_data = clan_manager.get_clan(clan_id)

    # Verifica se o clã já comprou o quadro de missões
    if clan_data.get("has_mission_board"):
        # Se sim, vai para o menu de seleção de missões que já existia
        await show_mission_selection_menu(update, context)
    else:
        # Se não, vai para o novo menu de compra
        await show_purchase_board_menu(update, context)

async def show_purchase_board_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o menu para o líder comprar o quadro de missões."""
    query = update.callback_query
    # Não precisa de query.answer() aqui pois já foi dado no roteador
    
    cost = CLAN_CONFIG.get("mission_board_cost", {}).get("gold", 0)
    
    caption = (
        "<b>Quadro de Missões da Guilda</b>\n\n"
        "Para que o seu clã possa realizar missões, o líder precisa de adquirir um Quadro de Missões.\n\n"
        "Esta é uma compra única para o clã e permitirá o acesso permanente às missões de guilda.\n\n"
        f"<b>Custo:</b> {cost:,} 🪙 Ouro (será debitado do Banco do Clã)"
    )
    
    keyboard = [
        [InlineKeyboardButton("🪙 Comprar Quadro de Missões", callback_data="clan_board_purchase")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="clan_manage_menu")]
    ]
    
    await query.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def handle_board_purchase_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa a tentativa de compra do quadro de missões."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    clan_id = player_manager.get_player_data(user_id).get("clan_id")

    try:
        # Chama a função do backend que faz o trabalho pesado
        clan_manager.purchase_mission_board(clan_id, user_id)
        
        await context.bot.answer_callback_query(
            query.id,
            "Quadro de Missões comprado com sucesso!",
            show_alert=True
        )
        # Após a compra, leva o líder direto para a seleção de missões
        await show_mission_selection_menu(update, context)

    except ValueError as e:
        # Mostra qualquer erro que o backend tenha retornado (ex: sem ouro, não é o líder)
        await context.bot.answer_callback_query(query.id, str(e), show_alert=True)

async def receive_deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe a quantia de ouro a depositar e processa a transação."""
    user_id = update.effective_user.id
    clan_id = player_manager.get_player_data(user_id).get("clan_id")
    
    try:
        amount = int(update.message.text)
        if amount <= 0:
            await update.message.reply_text("Por favor, envie um número positivo.")
            return ASKING_DEPOSIT_AMOUNT # Continua a pedir um número

        # Chama a função do backend que faz o trabalho pesado
        clan_manager.deposit_gold_to_bank(clan_id, user_id, amount)
        
        await update.message.reply_text(f"✅ Você depositou {amount:,} de ouro com sucesso!")

    except ValueError as e:
        # Trata erros, como falta de ouro ou número inválido
        await update.message.reply_text(f"❌ Erro: {e}")
    except Exception:
        # Erro genérico, como texto em vez de número
        await update.message.reply_text("❌ Quantia inválida. Por favor, envie apenas números.")
        return ASKING_DEPOSIT_AMOUNT

    # Após a transação, volta ao menu do clã
    await show_clan_dashboard(update, context)
    return ConversationHandler.END # Termina a conversa

async def cancel_bank_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a conversa do banco e volta ao menu do clã."""
    await update.message.reply_text("Operação no banco cancelada.")
    await show_clan_dashboard(update, context)
    return ConversationHandler.END

# Handlers para exportar

async def start_invite_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    player_data = player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")
    clan_data = clan_manager.get_clan(clan_id)

    # Verificações de segurança
    if not clan_data or clan_data.get("leader_id") != user_id:
        await context.bot.answer_callback_query(query.id, "Apenas o líder pode convidar.", show_alert=True)
        return ConversationHandler.END

    clan_level = clan_data.get("prestige_level", 1)
    level_info = CLAN_PRESTIGE_LEVELS.get(clan_level, {})
    max_members = level_info.get("max_members", 5)

    if len(clan_data.get("members", [])) >= max_members:
        await context.bot.answer_callback_query(query.id, "O seu clã já atingiu o número máximo de membros para este nível.", show_alert=True)
        return ConversationHandler.END
        
    await query.edit_message_caption(caption="Por favor, envie o `@username` do jogador que você deseja convidar. (Use /cancelar para desistir)")
    
    return ASKING_INVITEE

clan_transfer_leader_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_transfer_conversation, pattern=r'^clan_transfer_leader_start$')],
    states={
        ASKING_LEADER_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_transfer_target_name)],
        CONFIRM_LEADER_TRANSFER: [CallbackQueryHandler(do_transfer_leadership, pattern=r'^clan_transfer_do$')],
    },
    fallbacks=[
        CommandHandler('cancelar', cancel_transfer), # <-- CORRIGIDO para usar a nova função
        
        # Se o utilizador clicar em "Não", volta ao menu de gestão
        CallbackQueryHandler(show_clan_management_menu, pattern=r'^clan_manage_menu$')
    ],
)

# --- Handlers para registar no main.py ---
guild_menu_handler = CallbackQueryHandler(guild_menu_callback, pattern=r'^guild_menu$')
clan_menu_handler = CallbackQueryHandler(clan_menu_callback, pattern=r"^clan_menu(:.*)?$")
clan_upgrade_menu_handler = CallbackQueryHandler(show_clan_upgrade_menu, pattern=r'^clan_upgrade_menu$')
clan_apply_handler = CallbackQueryHandler(apply_to_clan_callback, pattern=r'^clan_apply:[a-z0-9_]+$')
clan_manage_apps_handler = CallbackQueryHandler(show_applications_menu, pattern=r'^clan_manage_apps$')
clan_app_accept_handler = CallbackQueryHandler(accept_application_callback, pattern=r'^clan_app_accept:\d+$')
clan_app_decline_handler = CallbackQueryHandler(decline_application_callback, pattern=r'^clan_app_decline:\d+$')
noop_handler = CallbackQueryHandler(lambda u, c: c.bot.answer_callback_query(u.callback_query.id), pattern=r'^noop$')
clan_upgrade_confirm_handler = CallbackQueryHandler(confirm_clan_upgrade_callback, pattern=r'^clan_upgrade_confirm:(gold|dimas)$')
clan_leave_confirm_handler = CallbackQueryHandler(show_leave_clan_confirm, pattern=r'^clan_leave_confirm$')
clan_leave_do_handler = CallbackQueryHandler(do_leave_clan_callback, pattern=r'^clan_leave_do$')
clan_manage_menu_handler = CallbackQueryHandler(show_clan_management_menu, pattern=r'^clan_manage_menu$')
clan_kick_menu_handler = CallbackQueryHandler(show_kick_member_menu, pattern=r'^clan_kick_menu$')
clan_kick_confirm_handler = CallbackQueryHandler(show_kick_confirm_menu, pattern=r'^clan_kick_confirm:\d+$')
clan_kick_do_handler = CallbackQueryHandler(do_kick_member_callback, pattern=r'^clan_kick_do:\d+$')
missions_menu_handler = CallbackQueryHandler(show_missions_menu, pattern=r'^guild_missions$')
mission_claim_handler = CallbackQueryHandler(claim_reward_callback, pattern=r'^mission_claim:\d+$')
mission_reroll_handler = CallbackQueryHandler(reroll_mission_callback, pattern=r'^mission_reroll:\d+$')
clan_mission_start_handler =  CallbackQueryHandler(show_mission_selection_menu, pattern=r'^clan_mission_start$')
clan_mission_confirm_handler = CallbackQueryHandler(confirm_mission_selection_callback, pattern=r'^clan_mission_confirm:[a-zA-Z0-9_]+$')
clan_board_purchase_handler = CallbackQueryHandler(handle_board_purchase_callback, pattern=r'^clan_board_purchase$')
clan_guild_mission_details_handler = CallbackQueryHandler(show_guild_mission_details, pattern=r'^clan_guild_mission_details$')

# Adicione esta linha no final de handlers/guild_handler.py
clan_bank_menu_handler = CallbackQueryHandler(show_clan_bank_menu, pattern=r'^clan_bank_menu$')
# Adicione estas duas variáveis no final de handlers/guild_handler.py

clan_deposit_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_deposit_conversation, pattern=r'^clan_bank_deposit_start$')],
    states={
        ASKING_DEPOSIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_deposit_amount)],
    },
    fallbacks=[CommandHandler('cancelar', cancel_bank_conversation)],
)

clan_withdraw_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_withdraw_conversation, pattern=r'^clan_bank_withdraw_start$')],
    states={
        ASKING_WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_withdraw_amount)],
    },
    fallbacks=[CommandHandler('cancelar', cancel_bank_conversation)],
)
