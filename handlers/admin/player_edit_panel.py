# handlers/admin/player_edit_panel.py
# (VERSÃO ATUALIZADA COM BOTÃO DE MUDAR CLASSE)

import logging
import os
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, 
    ConversationHandler, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    filters
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
from modules.player_manager import find_player_by_name
from modules import player_manager, game_data
try:
    from config import ADMIN_LIST
except ImportError:
    logger = logging.getLogger(__name__) # Define logger aqui se precisar
    logger.warning("ADMIN_LIST não encontrada em config.py no player_edit_panel, usando ADMIN_ID.")
    try:
        # Tenta pegar ADMIN_ID do ambiente se ADMIN_LIST falhou
        ADMIN_ID = int(os.getenv("ADMIN_ID"))
        ADMIN_LIST = [ADMIN_ID]
    except (TypeError, ValueError):
        logger.error("ADMIN_ID não definido nas variáveis de ambiente! Painel de edição pode não funcionar.")
        ADMIN_LIST = []
        
logger = logging.getLogger(__name__)

# Definição dos estados da conversa
(
    STATE_GET_USER_ID, 
    STATE_SHOW_MENU, 
    STATE_AWAIT_PROFESSION, 
    STATE_AWAIT_PROF_LEVEL, 
    STATE_AWAIT_CHAR_LEVEL,
    STATE_AWAIT_CLASS  # <<< 1. ESTADO ADICIONADO
) = range(6) # <<< 2. ALTERADO DE 5 PARA 6

# --- Funções Auxiliares (Helpers) ---

def _get_player_info_text(pdata: dict) -> str:
    """Monta o texto de status atual do jogador."""
    try:
        char_level = int(pdata.get('level', 1))
        prof_type = (pdata.get('profession', {}) or {}).get('type', 'Nenhuma')
        prof_level = int((pdata.get('profession', {}) or {}).get('level', 1))
        char_name = pdata.get('character_name', 'Sem Nome')
        user_id = pdata.get('user_id', '???') # Garante que user_id está nos dados

        # --- ADICIONADO PARA MOSTRAR A CLASSE ---
        class_key = pdata.get('class_key') or pdata.get('class', 'Nenhuma')
        class_info = (game_data.CLASSES_DATA.get(class_key) or {})
        class_display = class_info.get('display_name', class_key)
        # --- FIM DA ADIÇÃO ---

        # Busca o nome de exibição da profissão
        prof_display = (game_data.PROFESSIONS_DATA.get(prof_type) or {}).get('display_name', prof_type)

        return (
            f"👤 <b>Editando Jogador:</b> {char_name} (ID: <code>{user_id}</code>)\n"
            "----------------------------------\n"
            f"👑 <b>Classe:</b> {class_display}\n" # <<< LINHA ADICIONADA
            f"🎖️ <b>Nível de Personagem:</b> {char_level}\n"
            f"⚒️ <b>Profissão:</b> {prof_display}\n"
            f"📊 <b>Nível de Profissão:</b> {prof_level}\n"
            "----------------------------------\n"
            "O que você deseja alterar?"
        )
    except Exception as e:
        logger.error(f"Erro ao montar _get_player_info_text: {e}")
        return "Erro ao carregar dados. O que deseja alterar?"

def create_admin_edit_player_handler() -> ConversationHandler: # <<< VERIFIQUE ESTE NOME
    """Cria o ConversationHandler para o painel de edição de jogador."""

    admin_filter = filters.User(ADMIN_LIST)

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("editplayer", admin_edit_player_start, filters=admin_filter),
            CallbackQueryHandler(admin_edit_player_start, pattern=r"^admin_edit_player$")
        ],
        states={
            STATE_GET_USER_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter, admin_get_user_id)
            ],
            STATE_SHOW_MENU: [
                # <<< 3. ADICIONADO 'char_class' AO PATTERN >>>
                CallbackQueryHandler(admin_choose_action, pattern=r"^edit_(prof_type|prof_lvl|char_lvl|cancel|char_class)$"),
                CallbackQueryHandler(admin_edit_player_start, pattern=r"^admin_edit_player$")
            ],
            STATE_AWAIT_PROFESSION: [
                CallbackQueryHandler(admin_set_profession_type, pattern=r"^set_prof:"),
                CallbackQueryHandler(admin_show_menu_dispatch, pattern=r"^edit_back_menu$")
            ],
            STATE_AWAIT_CHAR_LEVEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter, admin_set_char_level)
            ],
            STATE_AWAIT_PROF_LEVEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter, admin_set_prof_level)
            ],
            # <<< 4. ADICIONADO NOVO ESTADO PARA MUDAR CLASSE >>>
            STATE_AWAIT_CLASS: [
                CallbackQueryHandler(admin_set_class, pattern=r"^set_class:"),
                CallbackQueryHandler(admin_show_menu_dispatch, pattern=r"^edit_back_menu$")
            ],
        },
        fallbacks=[
            CallbackQueryHandler(admin_edit_cancel, pattern=r"^edit_cancel$"),
            CommandHandler("cancel", admin_edit_cancel, filters=admin_filter)
        ],
        per_message=False
    )
    return conv_handler
    
async def _send_or_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Envia ou edita a mensagem principal do menu de edição."""
    kb = InlineKeyboardMarkup([
        # <<< 5. BOTÃO ADICIONADO >>>
        [InlineKeyboardButton("👑 Alterar Classe", callback_data="edit_char_class")],
        [InlineKeyboardButton("⚒️ Alterar Profissão", callback_data="edit_prof_type")],
        [InlineKeyboardButton("📊 Definir Nível de Profissão", callback_data="edit_prof_lvl")],
        [InlineKeyboardButton("🎖️ Definir Nível de Personagem", callback_data="edit_char_lvl")],
        [InlineKeyboardButton("❌ Cancelar Edição", callback_data="edit_cancel")]
    ])

    query = update.callback_query
    message = query.message if query else update.message # Obtém a mensagem correta

    # Tenta editar primeiro
    if query:
        try:
            await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
            return
        except Exception:
            # Fallback se a mensagem não puder ser editada
            pass

    # Fallback para enviar nova mensagem ou responder
    if message:
        try:
            # Tenta responder à mensagem original para manter o contexto
            await message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
        except Exception:
            # Fallback final se responder falhar (ex: msg deletada)
            await context.bot.send_message(message.chat_id, text, reply_markup=kb, parse_mode=ParseMode.HTML)
    else:
        # Se não houver mensagem original (raro, mas possível)
        await context.bot.send_message(update.effective_chat.id, text, reply_markup=kb, parse_mode=ParseMode.HTML)

async def admin_edit_player_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Inicia a conversa para editar um jogador.
    Pede ID ou Nome do Personagem.
    (Versão com fallback robusto para edição)
    """
    text = "Insira o <b>ID do usuário</b> ou o <b>Nome exato do personagem</b> que você deseja editar:"

    query = update.callback_query
    if query:
        await query.answer() # Responde ao clique primeiro

        # --- CORREÇÃO: Tenta editar caption OU texto ---
        message_to_edit = query.message
        edited = False
        if message_to_edit:
            try:
                # Tenta editar caption primeiro (se a msg tiver mídia)
                await message_to_edit.edit_caption(caption=text, parse_mode=ParseMode.HTML)
                edited = True
            except BadRequest as e_caption:
                if "message is not modified" in str(e_caption).lower():
                        edited = True # Considera editado se for a mesma msg
                elif "message to edit not found" in str(e_caption).lower():
                        pass # Mensagem foi deletada, não podemos editar
                elif "message can't be edited" in str(e_caption).lower():
                        pass # Mensagem muito antiga ou outro erro, não podemos editar
                else:
                    # Se não for caption, tenta editar texto
                    try:
                        await message_to_edit.edit_text(text, parse_mode=ParseMode.HTML)
                        edited = True
                    except BadRequest as e_text:
                        if "message is not modified" in str(e_text).lower():
                                edited = True
                        elif "message to edit not found" in str(e_text).lower():
                                pass
                        elif "message can't be edited" in str(e_text).lower():
                                pass
                        else:
                                # Se ambos falharam por outros motivos, loga
                                logger.warning(f"Falha ao editar msg (caption/texto) em admin_edit_player_start: {e_caption} / {e_text}")
                    except Exception as e_generic_text:
                        logger.warning(f"Erro genérico ao editar texto em admin_edit_player_start: {e_generic_text}")
            except Exception as e_generic_caption:
                logger.warning(f"Erro genérico ao editar caption em admin_edit_player_start: {e_generic_caption}")

        # --- Fallback: Envia nova mensagem se a edição falhou ---
        if not edited:
            chat_id = update.effective_chat.id
            if chat_id:
                try:
                    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
                except Exception as e_send:
                        logger.error(f"Falha CRÍTICA ao enviar msg fallback em admin_edit_player_start: {e_send}")
            else:
                logger.error("Não foi possível enviar msg fallback em admin_edit_player_start: chat_id desconhecido.")

    # Se veio de um comando /editplayer (sem query)
    else:
        if update.message: # Garante que message existe
            await update.message.reply_text(text, parse_mode=ParseMode.HTML)

    return STATE_GET_USER_ID

async def admin_get_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Recebe o ID ou Nome, encontra o jogador e mostra o menu de edição.
    (Com logs de temporização)
    """
    start_time = time.time() # <<< DEBUG TEMPORIZAÇÃO

    user_input = update.message.text
    target_user_id = None
    pdata = None
    found_by = "ID/Nome"

    # 1. Tenta encontrar por ID
    try:
        target_user_id = int(user_input)
        # <<< CORREÇÃO 1: Adiciona await >>>
        pdata = await player_manager.get_player_data(target_user_id)
        found_by = "ID"
        if pdata:
            pdata['user_id'] = target_user_id
    except ValueError:
        # 2. Se não for ID, tenta encontrar por Nome
        try:
            # <<< CORREÇÃO 2: Adiciona await >>>
            found = await find_player_by_name(user_input)
            if found:
                target_user_id, pdata = found
                found_by = "Nome"
                if pdata:
                    pdata['user_id'] = target_user_id
        except Exception as e:
            logger.error(f"Erro ao buscar jogador por nome '{user_input}': {e}")
            await update.message.reply_text("Ocorreu um erro ao buscar pelo nome. Tente novamente ou use o ID.")
            return STATE_GET_USER_ID

    end_time = time.time() # <<< DEBUG TEMPORIZAÇÃO
    elapsed = end_time - start_time
    logger.info(f"[DEBUG_TEMP] Buscando jogador '{user_input}' levou {elapsed:.3f} segundos.") # <<< DEBUG TEMPORIZAÇÃO

    # 3. Verifica se encontrou
    if not pdata or not target_user_id:
        await update.message.reply_text(
            f"Jogador não encontrado pelo {found_by} <code>{user_input}</code>. Verifique se digitou corretamente e tente novamente:",
            parse_mode=ParseMode.HTML
        )
        return STATE_GET_USER_ID

    # 4. Salva o ID encontrado e mostra o menu
    context.user_data['edit_target_id'] = target_user_id

    info_text = _get_player_info_text(pdata)
    await _send_or_edit_menu(update, context, info_text)

    return STATE_SHOW_MENU

async def admin_show_menu_dispatch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mostra o menu principal (usado para retornar ao menu)."""
    query = update.callback_query
    if query:
        await query.answer()

    target_user_id = context.user_data.get('edit_target_id')
    if not target_user_id:
        await query.edit_message_text("Erro: ID do jogador alvo perdido. Encerrando.")
        return ConversationHandler.END

    # <<< CORREÇÃO 3: Adiciona await >>>
    pdata = await player_manager.get_player_data(target_user_id)
    info_text = _get_player_info_text(pdata)
    await _send_or_edit_menu(update, context, info_text)
    
    return STATE_SHOW_MENU

async def admin_choose_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa o botão de ação escolhido pelo admin."""
    query = update.callback_query
    await query.answer()
    
    action = query.data

    # --- !!! 6. BLOCO ADICIONADO !!! ---
    if action == "edit_char_class":
        # Monta o teclado com todas as classes disponíveis
        kb_rows = []
        # Assumindo que game_data.CLASSES_DATA está disponível
        if hasattr(game_data, 'CLASSES_DATA'):
            for class_id, class_data in game_data.CLASSES_DATA.items():
                kb_rows.append([InlineKeyboardButton(
                    f"{class_data.get('emoji', '👤')} {class_data.get('display_name', class_id)}",
                    callback_data=f"set_class:{class_id}"
                )])
        else:
            logger.warning("game_data.CLASSES_DATA não encontrado!")
            # Adiciona fallback manual se necessário, ou apenas o botão de voltar
            
        kb_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="edit_back_menu")])
        
        await query.edit_message_text(
            "Escolha a <b>nova classe</b> para o jogador:",
            reply_markup=InlineKeyboardMarkup(kb_rows),
            parse_mode=ParseMode.HTML
        )
        return STATE_AWAIT_CLASS
    # --- FIM DO NOVO BLOCO ---

    elif action == "edit_prof_type":
        # Monta o teclado com todas as profissões disponíveis
        kb_rows = []
        for prof_id, prof_data in game_data.PROFESSIONS_DATA.items():
            kb_rows.append([InlineKeyboardButton(
                f"{prof_data.get('display_name', prof_id)} ({prof_data.get('category', 'N/A')})",
                callback_data=f"set_prof:{prof_id}"
            )])
        kb_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="edit_back_menu")])
        
        await query.edit_message_text(
            "Escolha a <b>nova profissão</b> para o jogador:",
            reply_markup=InlineKeyboardMarkup(kb_rows),
            parse_mode=ParseMode.HTML
        )
        return STATE_AWAIT_PROFESSION

    elif action == "edit_prof_lvl":
        await query.edit_message_text("Digite o <b>novo Nível de Profissão</b> (ex: 10):", parse_mode=ParseMode.HTML)
        return STATE_AWAIT_PROF_LEVEL
        
    elif action == "edit_char_lvl":
        await query.edit_message_text("Digite o <b>novo Nível de Personagem</b> (ex: 50):", parse_mode=ParseMode.HTML)
        return STATE_AWAIT_CHAR_LEVEL
        
    elif action == "edit_cancel":
        await query.edit_message_text("Edição cancelada.")
        context.user_data.pop('edit_target_id', None)
        return ConversationHandler.END

    return STATE_SHOW_MENU

# --- !!! 7. FUNÇÃO INTEIRA ADICIONADA !!! ---
async def admin_set_class(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Define a nova classe do jogador."""
    query = update.callback_query
    await query.answer()
    
    target_user_id = context.user_data.get('edit_target_id')
    if not target_user_id:
        await query.edit_message_text("Erro: ID do jogador alvo perdido. Encerrando.")
        return ConversationHandler.END

    new_class_id = query.data.replace("set_class:", "")
    class_info = game_data.CLASSES_DATA.get(new_class_id)
    
    if not class_info:
        await query.answer("Classe inválida.", show_alert=True)
        return STATE_AWAIT_CLASS # Permanece no estado de escolha

    pdata = await player_manager.get_player_data(target_user_id)
    if not pdata:
        await query.edit_message_text("Erro: Não foi possível carregar os dados do jogador alvo. Encerrando.")
        return ConversationHandler.END
    
    # Define a classe (ambos os campos, 'class' e 'class_key')
    new_class_name = class_info.get('display_name', new_class_id)
    pdata['class'] = new_class_name
    pdata['class_key'] = new_class_id
    
    await player_manager.save_player_data(target_user_id, pdata)
    
    await query.answer(f"Classe alterada para {new_class_name}!")
    
    # Volta ao menu principal
    info_text = _get_player_info_text(pdata)
    await _send_or_edit_menu(update, context, info_text)
    return STATE_SHOW_MENU
# --- FIM DA NOVA FUNÇÃO ---

async def admin_set_profession_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Define a nova profissão do jogador."""
    query = update.callback_query
    await query.answer()
    
    target_user_id = context.user_data.get('edit_target_id')
    if not target_user_id:
        await query.edit_message_text("Erro: ID do jogador alvo perdido. Encerrando.")
        return ConversationHandler.END

    new_prof_id = query.data.replace("set_prof:", "")
    if new_prof_id not in game_data.PROFESSIONS_DATA:
        await query.answer("Profissão inválida.", show_alert=True)
        return STATE_AWAIT_PROFESSION

    # <<< CORREÇÃO 4: Adiciona await >>>
    pdata = await player_manager.get_player_data(target_user_id)
    
    # Define a profissão, resetando nível e XP
    pdata.setdefault('profession', {})
    pdata['profession']['type'] = new_prof_id
    pdata['profession']['level'] = 1
    pdata['profession']['xp'] = 0
    
    # <<< CORREÇÃO 5: Adiciona await >>>
    await player_manager.save_player_data(target_user_id, pdata)
    
    await query.answer("Profissão alterada!")
    
    # Volta ao menu principal
    info_text = _get_player_info_text(pdata)
    await _send_or_edit_menu(update, context, info_text)
    return STATE_SHOW_MENU

async def admin_set_char_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Define o novo nível de personagem."""
    try:
        new_level = int(update.message.text)
        if new_level <= 0:
            raise ValueError("Nível deve ser positivo")
    except ValueError:
        await update.message.reply_text("Valor inválido. Digite um número (ex: 50).")
        return STATE_AWAIT_CHAR_LEVEL

    target_user_id = context.user_data.get('edit_target_id')
    if not target_user_id:
        await update.message.reply_text("Erro: ID do jogador alvo perdido. Encerrando.")
        return ConversationHandler.END

    # <<< CORREÇÃO 6: Adiciona await >>>
    pdata = await player_manager.get_player_data(target_user_id)
    
    # Define o nível e reseta o XP
    pdata['level'] = new_level
    pdata['xp'] = 0
    
    # <<< CORREÇÃO 7: Adiciona await >>>
    await player_manager.save_player_data(target_user_id, pdata)
    
    info_text = _get_player_info_text(pdata)
    await update.message.reply_text(f"✅ Nível de personagem atualizado para <b>{new_level}</b>.", parse_mode=ParseMode.HTML)
    await _send_or_edit_menu(update, context, info_text)
    return STATE_SHOW_MENU

async def admin_set_prof_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Define o novo nível de profissão."""
    try:
        new_level = int(update.message.text)
        if new_level <= 0:
            raise ValueError("Nível deve ser positivo")
    except ValueError:
        await update.message.reply_text("Valor inválido. Digite um número (ex: 10).")
        return STATE_AWAIT_PROF_LEVEL

    target_user_id = context.user_data.get('edit_target_id')
    if not target_user_id:
        await update.message.reply_text("Erro: ID do jogador alvo perdido. Encerrando.")
        return ConversationHandler.END

    # <<< CORREÇÃO 8: Adiciona await >>>
    pdata = await player_manager.get_player_data(target_user_id)
    
    # Define o nível e reseta o XP da profissão
    pdata.setdefault('profession', {})
    if not pdata['profession'].get('type'):
        await update.message.reply_text("Erro: O jogador não tem uma profissão definida. Altere a profissão primeiro.")
    else:
        pdata['profession']['level'] = new_level
        pdata['profession']['xp'] = 0
        
        # <<< CORREÇÃO 9: Adiciona await >>>
        await player_manager.save_player_data(target_user_id, pdata)
        await update.message.reply_text(f"✅ Nível de profissão atualizado para <b>{new_level}</b>.", parse_mode=ParseMode.HTML)

    info_text = _get_player_info_text(pdata)
    await _send_or_edit_menu(update, context, info_text)
    return STATE_SHOW_MENU

async def admin_edit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a conversa."""
    query = update.callback_query
    if query:
        await query.edit_message_text("Edição cancelada.")
    else:
        await update.message.reply_text("Edição cancelada.")
        
    context.user_data.pop('edit_target_id', None)
    return ConversationHandler.END