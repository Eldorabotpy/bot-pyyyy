import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from typing import List

from modules import player_manager, clan_manager, file_id_manager
from modules.game_data.clans import CLAN_PRESTIGE_LEVELS

# Importações das outras funcionalidades (mantidas)
from handlers.guild.missions import show_guild_mission_details
from handlers.guild.bank import show_clan_bank_menu
from handlers.guild.management import show_clan_management_menu

logger = logging.getLogger(__name__)

# --- Função Auxiliar de Mídia (ADICIONADA) ---

async def _send_with_media(chat_id: int, context: ContextTypes.DEFAULT_TYPE, caption: str, kb: InlineKeyboardMarkup, media_keys: List[str]):
    """
    Tenta enviar uma mensagem com mídia usando uma lista de chaves.
    Se falhar, envia como texto simples.
    """
    media_sent = False
    for key in media_keys:
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
                logger.warning(f"Falha ao enviar mídia da Guilda com chave '{key}'. Erro: {e}.")
                continue 
    
    if not media_sent:
        logger.info(f"Nenhuma mídia válida encontrada para Guilda (chaves: {media_keys}). Enviando como texto.")
        await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=kb, parse_mode="HTML")

# --- Funções de Exibição (CORRIGIDAS) ---

async def show_clan_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE, came_from: str = "kingdom"):
    """Mostra o painel principal do clã (AGORA COM MÍDIA)."""
    query = update.callback_query
    user_id = update.effective_user.id
    chat_id = query.message.chat_id # Pega o chat_id aqui
    
    player_data = await player_manager.get_player_data(user_id) # Correto (await)
    if not player_data:
         await query.answer("Erro ao carregar dados do jogador.", show_alert=True)
         return
         
    clan_id = player_data.get("clan_id")
    
    # <<< CORREÇÃO 1: Removido 'await' >>>
    clan_data = clan_manager.get_clan(clan_id) # síncrono

    if not clan_data:
        await query.answer("Você não está em um clã.", show_alert=True)
        return

    # --- Construção da Mensagem (Legenda) ---
    clan_name = clan_data.get('display_name', 'Nome do Clã')
    level = clan_data.get('prestige_level', 1)
    members_count = len(clan_data.get('members', []))
    level_info = CLAN_PRESTIGE_LEVELS.get(level, {})
    max_members = level_info.get('max_members', 5)
    
    mission = await clan_manager.get_active_guild_mission(clan_id) # Correto (await)
    mission_line = "Nenhuma missão ativa."
    if mission:
        progress = mission.get('current_progress', 0)
        target = mission.get('target_count', 1)
        mission_title = mission.get('title', 'Missão')
        mission_line = f"▫️ {mission_title}: [{progress}/{target}]"
        
    members_list_str = ""
    # Limita a exibição (ex: 10 membros) para não estourar a mensagem
    members_to_show = clan_data.get("members", [])[:10] 
    
    for member_id in members_to_show:
        member_data = await player_manager.get_player_data(member_id) # Correto (await)
        if member_data:
            member_name = member_data.get("character_name", f"ID:{member_id}")
            # Adiciona indicador de líder
            if member_id == clan_data.get("leader_id"):
                 members_list_str += f"   - 👑 {member_name} (Líder)\n"
            else:
                 members_list_str += f"   - 👤 {member_name}\n"
    
    if len(clan_data.get("members", [])) > len(members_to_show):
         members_list_str += f"   ... e mais {len(clan_data.get('members', [])) - len(members_to_show)}."

    text = (
        f"⚜️ <b>Painel do Clã: {clan_name}</b> ⚜️\n\n"
        f"<b>Nível:</b> {level}\n"
        f"<b>Membros:</b> {members_count}/{max_members}\n\n"
        f"<b>Missão do Clã Ativa:</b>\n{mission_line}\n\n"
        f"<b>Membros do Clã:</b>\n"
        f"{members_list_str}"
    )

    # --- Teclado (Keyboard) ---
    if came_from == 'profile':
        back_callback = 'profile' # Botão "Voltar" leva ao Perfil
    else:
        # 'continue_after_action' é geralmente usado para voltar ao menu principal (Reino)
        back_callback = 'continue_after_action' 

    keyboard = [
        [InlineKeyboardButton("📜 Ver Detalhes da Missão", callback_data="clan_mission_details")],
        [InlineKeyboardButton("🏦 Banco do Clã", callback_data="clan_bank_menu")],
        [InlineKeyboardButton("👑 Gerir Clã", callback_data="clan_manage_menu")],
        [InlineKeyboardButton("🚪 Sair do Clã", callback_data="clan_leave_confirm")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data=back_callback)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # --- Lógica de Envio de Mídia (ADICIONADA) ---
    try:
        await query.delete_message()
    except Exception as e:
        logger.debug(f"Não foi possível apagar a mensagem anterior: {e}")
    
    # Define as chaves de mídia a tentar
    media_keys = [
        clan_data.get("logo_media_key"), # 1. Chave personalizada do clã (se tiverem)
        f"clan_logo_{clan_id}",         # 2. Logo específico (ex: clan_logo_draconicos)
        "guild_dashboard_media",       # 3. Mídia genérica do painel de guildas
        "clan_menu_media",             # 4. Outra chave genérica
        "regiao_reino_eldora"          # 5. Fallback: imagem do reino
    ]
    
    await _send_with_media(chat_id, context, text, reply_markup, media_keys)


async def show_leave_clan_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    text = "Tem a certeza que deseja sair do seu clã? Esta ação não pode ser desfeita."
    keyboard = [[
        InlineKeyboardButton("✅ Sim, desejo sair", callback_data="clan_leave_do"),
        InlineKeyboardButton("❌ Não, quero ficar", callback_data="clan_menu") # 'clan_menu' vai chamar o router
    ]]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

async def do_leave_clan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    
    player_data = await player_manager.get_player_data(user_id) # Correto (await)
    clan_id = player_data.get("clan_id")

    if not clan_id:
        await query.edit_message_text("Você já não está em um clã.")
        return
        
    try:
        # <<< CORREÇÃO 2: Removido 'await' >>>
        clan_data = clan_manager.get_clan(clan_id) # síncrono
        clan_name = (clan_data or {}).get("display_name", "do clã") # Adiciona fallback
        
        # <<< CORREÇÃO 3: Removido 'await' >>>
        clan_manager.remove_member(clan_id, user_id, kicked_by_leader=False) # síncrono
        
        player_data["clan_id"] = None
        
        await player_manager.save_player_data(user_id, player_data) # Correto (await)
        
        # Envia texto simples de confirmação
        await query.edit_message_text(f"Você saiu do clã '{clan_name}'.")
        
        # (Opcional: Poderia chamar show_kingdom_menu aqui para voltar ao reino)
        # await show_kingdom_menu(update, context) 

    except ValueError as e:
        await context.bot.answer_callback_query(query.id, str(e), show_alert=True)
        # Se falhar (ex: líder a tentar sair), volta ao dashboard
        await show_clan_dashboard(update, context) # Correto (await)

# --- FUNÇÃO ROUTER FINAL (Mantida) ---
# Esta função recebe o callback 'clan_menu' e chama show_clan_dashboard
async def clan_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe todos os callbacks que começam com 'clan_' e direciona para a função correta."""
    query = update.callback_query
    await query.answer() # Responde à query aqui

    action = query.data
    # Extrai o 'came_from' se existir (ex: 'clan_menu:profile')
    came_from = "kingdom" # Padrão
    if ":" in action:
         try:
             action, came_from = action.split(":", 1)
         except ValueError:
             action = action.split(":", 1)[0] # Pega só a ação
             
    if action == 'clan_menu':
        # Passa o 'came_from' para o dashboard
        await show_clan_dashboard(update, context, came_from=came_from) 
    elif action == 'clan_leave_confirm':
        await show_leave_clan_confirm(update, context)
    elif action == 'clan_leave_do':
        await do_leave_clan_callback(update, context)
    elif action == 'clan_back_to_kingdom':
        # Esta ação específica força o retorno ao reino
        pass # (Ainda não temos a função show_kingdom_menu importada)
        # Se/quando importares 'show_kingdom_menu', descomenta a linha abaixo:
        # await show_kingdom_menu(update, context)
        # Por agora, envia uma mensagem simples:
        await query.edit_message_text("Retornando ao reino...", reply_markup=None)

    elif action == 'clan_mission_details':
        await show_guild_mission_details(update, context)
    elif action == 'clan_bank_menu':
        await show_clan_bank_menu(update, context)
    elif action == 'clan_manage_menu':
        await show_clan_management_menu(update, context)
    # (Adiciona outros 'elif' aqui se necessário)
    
# --- UM ÚNICO HANDLER EFICIENTE ---
# Este handler captura 'clan_menu' e 'clan_menu:profile'
clan_handler = CallbackQueryHandler(clan_router, pattern=r'^clan_')