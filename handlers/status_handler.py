# handlers/status_handler.py (VERSÃO FINAL E CORRIGIDA)

import logging
import re
import unicodedata
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.error import BadRequest

from modules import player_manager, game_data, file_ids

logger = logging.getLogger(__name__)

PROFILE_KEYS = ['max_hp', 'attack', 'defense', 'initiative', 'luck']

def _slugify(text: str) -> str:
    if not text: return ""
    # Normaliza, remove acentos, converte para minúsculas, substitui espaços, remove caracteres inválidos
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    norm = re.sub(r"[^\w\s-]", "", norm).strip().lower() # Permite hífens também
    norm = re.sub(r"[-\s]+", "_", norm) # Substitui hífens e espaços por underscore
    return norm

def _get_class_media(player_data: dict, purpose: str = "status"):
    """Busca a mídia (video/foto) associada à classe do jogador."""
    raw_cls = (player_data.get("class") or "").strip()
    base_cls_key = raw_cls.lower() # Ex: 'ronin'
    cls_slug = _slugify(base_cls_key) # Ex: 'ronin'
    logger.debug(f"[_get_class_media] Raw Class: '{raw_cls}', Base Key: '{base_cls_key}', Slug: '{cls_slug}'")

    classes_data = getattr(game_data, "CLASSES_DATA", {}) or {}
    # Obtém a configuração da classe atual (ex: dados do Ronin)
    cls_cfg = classes_data.get(raw_cls) or classes_data.get(base_cls_key) or {}

    candidates = []

    # =========================================================
    # <<< INÍCIO DA CORREÇÃO >>>
    # =========================================================
    # 1. Tenta a chave definida em 'file_id_name' PRIMEIRO
    file_id_name_from_class = cls_cfg.get("file_id_name")
    if file_id_name_from_class:
        candidates.append(file_id_name_from_class) # Ex: 'classe_samurai_media'
    # =========================================================
    # <<< FIM DA CORREÇÃO >>>
    # =========================================================

    # 2. Tenta a chave específica para status definida na config da classe
    if cls_cfg.get("status_file_id_key"):
         candidates.append(cls_cfg["status_file_id_key"])

    # 3. Tenta nomes padronizados baseados no slug da classe ATUAL ('ronin')
    if cls_slug:
        candidates.extend([
            f"status_video_{cls_slug}", # status_video_ronin
            f"status_{cls_slug}",      # status_ronin
            f"class_{cls_slug}_status", # class_ronin_status
            f"classe_{cls_slug}_media" # classe_ronin_media
        ])
    # 4. Fallback genérico
    candidates.append("status_video")

    # Remove duplicates e None values
    unique_candidates = list(filter(None, dict.fromkeys(candidates)))
    logger.debug(f"[_get_class_media] Candidate Keys (Order: file_id_name -> specific -> slugged -> fallback): {unique_candidates}")

    for key in unique_candidates:
        logger.debug(f"[_get_class_media] Trying key: '{key}'")
        try:
            fd = file_ids.get_file_data(key)
            if fd and fd.get("id"):
                logger.info(f"[_get_class_media] Success! Found media for class '{raw_cls}' using key: '{key}' -> ID: {fd.get('id')}")
                return fd
            else:
                 logger.debug(f"[_get_class_media] Key '{key}' found, but data is invalid or missing 'id'. Data: {fd}")
        except Exception as e:
             logger.error(f"[_get_class_media] Error looking up key '{key}': {e}", exc_info=False) # exc_info=False para logs menos verbosos no caso normal

    logger.warning(f"[_get_class_media] No valid media found for class '{raw_cls}' after trying all keys.")
    return None

async def _get_status_content(player_data: dict) -> tuple[str, InlineKeyboardMarkup]:
    """Gera o texto e o teclado do menu de status."""
    
    # --- CORREÇÃO 1: Adiciona 'await' aqui ---
    # Esta função provavelmente é assíncrona, como vimos no profile_handler
    total_stats = await player_manager.get_player_total_stats(player_data)
    
    char_name = player_data.get('character_name', 'Aventureiro(a)')
    status_text = f"👤 <b>Status de {char_name}</b>\n\n"
    emoji_map = {'max_hp': '❤️', 'attack': '⚔️', 'defense': '🛡️', 'initiative': '🏃', 'luck': '🍀'}
    name_map = {'max_hp': 'HP Máximo', 'attack': 'Ataque', 'defense': 'Defesa', 'initiative': 'Iniciativa', 'luck': 'Sorte'}

    for stat in PROFILE_KEYS:
        raw_val = total_stats.get(stat, 0)
        
        # --- CORREÇÃO 2: Lógica para mostrar decimais (float) ---
        if stat == 'luck':
            # Formata a Sorte para 1 casa decimal (ex: 77.0 ou 77.5)
            val_str = f"{raw_val:.1f}"
        else:
            # Formata os outros como inteiros (ex: 362)
            val_str = str(int(raw_val))
        # --- Fim da Correção 2 ---
            
        status_text += f"{emoji_map[stat]} <b>{name_map[stat]}:</b> {val_str}\n" # Usa val_str

    available_points = int(player_data.get('stat_points', 0) or 0)
    status_text += f"\n✨ <b>Pontos disponíveis:</b> {available_points}"

    keyboard_rows = []
    if available_points > 0:
        # Botões de upgrade (duas colunas)
        row1 = [InlineKeyboardButton("➕ HP (+3)", callback_data='upgrade_max_hp')]
        if 'attack' in PROFILE_KEYS: row1.append(InlineKeyboardButton("➕ ATK (+1)", callback_data='upgrade_attack'))
        keyboard_rows.append(row1)

        row2 = []
        if 'defense' in PROFILE_KEYS: row2.append(InlineKeyboardButton("➕ DEF (+1)", callback_data='upgrade_defense'))
        if 'initiative' in PROFILE_KEYS: row2.append(InlineKeyboardButton("➕ INI (+1)", callback_data='upgrade_initiative'))
        if row2: keyboard_rows.append(row2) # Adiciona linha 2 se tiver botões

        if 'luck' in PROFILE_KEYS:
            keyboard_rows.append([InlineKeyboardButton("➕ SORTE (+1)", callback_data='upgrade_luck')]) # Sorte em linha própria

    # Botões de Ação
    keyboard_rows.append([InlineKeyboardButton("🎐 𝐄𝐯𝐨𝐥𝐮çã𝐨 𝐝𝐞 𝐂𝐥𝐚𝐬𝐬𝐞", callback_data="status_evolution_open")])
    keyboard_rows.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data='profile')]) # Assume que 'profile' volta ao menu principal

    return status_text, InlineKeyboardMarkup(keyboard_rows)

async def show_status_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Mostra a tela de status, funcionando para comando /status e botão.
    (Agora assíncrono para buscar dados)
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id # Pega o chat_id

    # <<< CORREÇÃO 1: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id) 

    if not player_data:
        text = "Você precisa criar um personagem. Use /start."
        if update.callback_query:
            await update.callback_query.answer()
            try:
                await update.callback_query.edit_message_text(text)
            except BadRequest:
                if chat_id: await context.bot.send_message(chat_id, text)
        else:
            if update.message: await update.message.reply_text(text)
        return

    # --- CORREÇÃO APLICADA AQUI ---
    # Como _get_status_content agora é 'async', precisa de 'await'
    status_text, reply_markup = await _get_status_content(player_data)
    # --- FIM DA CORREÇÃO ---

    # --- Lógica para CallbackQuery (Botão) ---
    if update.callback_query:
        query = update.callback_query
        await query.answer() # Já estava correto

        try:
            await query.delete_message()
        except Exception as e_del:
            logger.debug(f"Não foi possível apagar mensagem anterior em show_status_menu: {e_del}")

        # _get_class_media é síncrono
        media = _get_class_media(player_data, "status")

        try:
            if media and media.get("id") and chat_id:
                media_id = media["id"]
                media_type = (media.get("type") or "photo").lower()
                if media_type == "video":
                    await context.bot.send_video(chat_id=chat_id, video=media_id, caption=status_text, reply_markup=reply_markup, parse_mode='HTML')
                else:
                    await context.bot.send_photo(chat_id=chat_id, photo=media_id, caption=status_text, reply_markup=reply_markup, parse_mode='HTML')
            elif chat_id: # Fallback se não houver mídia
                await context.bot.send_message(chat_id=chat_id, text=status_text, reply_markup=reply_markup, parse_mode='HTML')
            else:
                 logger.error("show_status_menu (callback): chat_id inválido.")
        except Exception as e_send:
            logger.error(f"Erro ao enviar menu de status (callback) para {user_id}: {e_send}", exc_info=True)
            if chat_id: await context.bot.send_message(chat_id, "Ocorreu um erro ao exibir o menu de status.")

    # --- Lógica para Comando /status ---
    else:
        if update.message and chat_id: # Garante que temos uma mensagem e chat_id
            await update.message.reply_text(text=status_text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            logger.error("show_status_menu (comando): update.message ou chat_id inválido.")

async def upgrade_stat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aplica o upgrade de stat, salva, e edita a mensagem usando os dados locais."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # --- 1. Carrega os dados ---
    player_data = await player_manager.get_player_data(user_id) 
    if not player_data:
        try: await query.answer("Erro: Não foi possível carregar seus dados.", show_alert=True)
        except Exception: pass
        return

    # Lógica síncrona de verificação
    pool = int(player_data.get("stat_points", 0) or 0)
    if pool <= 0:
        await query.answer("Você não tem pontos de atributo para gastar!", show_alert=True)
        return

    profile_stat = query.data.replace('upgrade_', '')
    if profile_stat not in PROFILE_KEYS:
        logger.warning(f"Callback de upgrade inválido recebido: {query.data}")
        try: await query.answer("Atributo inválido.", show_alert=True)
        except Exception: pass
        return

    # --- 2. Aplica o upgrade (Modifica o 'player_data' localmente) ---
    player_data["stat_points"] = pool - 1
    
    player_class = player_data.get('class')
    modifiers = game_data.CLASSES_DATA.get(player_class, {}).get(
        'stat_modifiers', {'attack': 1, 'defense': 1, 'initiative': 1, 'luck': 0.5}
    )

    if profile_stat == 'attack':
        player_data['attack'] = int(player_data.get('attack', 0) + (1 * modifiers.get('attack', 1)))
    
    elif profile_stat == 'defense':
        player_data['defense'] = int(player_data.get('defense', 0) + (1 * modifiers.get('defense', 1)))
    
    elif profile_stat == 'initiative':
        player_data['initiative'] = int(player_data.get('initiative', 0) + (1 * modifiers.get('initiative', 1)))
    
    elif profile_stat == 'luck':
        player_data['luck'] = player_data.get('luck', 0) + (1 * modifiers.get('luck', 0.5))
    
    elif profile_stat == 'max_hp':
        inc = 3
        current_hp = int(player_data.get("current_hp", 0))
        player_data['max_hp'] = int(player_data.get('max_hp', 0)) + inc
        new_max_hp = player_data['max_hp']
        if current_hp < new_max_hp:
            player_data["current_hp"] = min(current_hp + inc, new_max_hp)


    # --- 3. Salva os dados modificados ---
    try:
        await player_manager.save_player_data(user_id, player_data)
    except Exception as e_save:
        logger.error(f"Falha ao salvar dados após upgrade de stat para {user_id}: {e_save}", exc_info=True)
        await query.answer("Erro ao salvar o upgrade.", show_alert=True)
        # Reverte a mudança de pontos localmente se o save falhar
        player_data["stat_points"] = pool 
        return

    # --- 4. Gera o conteúdo COM os dados que acabámos de modificar ---
    # <<< CORREÇÃO PRINCIPAL: NÃO RECARREGAMOS MAIS OS DADOS >>>
    # Usamos o 'player_data' que já está correto na memória.
    try:
        status_text, reply_markup = await _get_status_content(player_data) 
    except Exception as e_get_content:
        logger.error(f"Falha ao gerar _get_status_content para {user_id}: {e_get_content}", exc_info=True)
        await query.answer("Erro ao redesenhar o menu.", show_alert=True)
        return

    # --- 5. Tenta editar a mensagem ---
    try:
        await query.edit_message_caption(caption=status_text, reply_markup=reply_markup, parse_mode='HTML')
    except BadRequest as e_caption:
        error_str = str(e_caption).lower()
        if "message has no caption" in error_str or "there is no caption" in error_str or \
           "message can't be edited" in error_str or "message to edit not found" in error_str:
            try:
                await query.edit_message_text(text=status_text, reply_markup=reply_markup, parse_mode='HTML')
            except BadRequest as e_text:
                if "message is not modified" not in str(e_text).lower():
                    logger.error(f"Falha ao editar menu de status (texto) após fallback: {e_text}")
            except Exception as e_generic_text:
                logger.error(f"Erro genérico ao editar menu de status (texto) após fallback: {e_generic_text}", exc_info=True)
        elif "message is not modified" not in error_str:
            logger.error(f"Falha ao editar menu de status (caption): {e_caption}")
    except Exception as e_generic_caption:
        logger.error(f"Erro genérico ao editar menu de status (caption): {e_generic_caption}", exc_info=True)

async def close_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fecha (apaga) a mensagem de status."""
    query = update.callback_query
    await query.answer()
    try:
        await query.delete_message()
    except BadRequest as e:
         if "message to delete not found" not in str(e).lower():
              logger.warning(f"Erro ao tentar fechar status: {e}")
    except Exception as e_del:
        logger.warning(f"Erro genérico ao fechar status: {e_del}")
        
# ==== EXPORTS ====
status_command_handler = CommandHandler("status", show_status_menu)
status_open_handler = CallbackQueryHandler(show_status_menu, pattern=r'^status_open$')
status_callback_handler = CallbackQueryHandler(upgrade_stat_callback, pattern=r'^upgrade_')
close_status_handler = CallbackQueryHandler(close_status_callback, pattern=r'^close_status$') # Assume que você tem um botão para fechar