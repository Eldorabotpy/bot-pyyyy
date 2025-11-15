# handlers/status_handler.py (VERSÃO COM LÓGICA DE UPGRADE CORRIGIDA)

import logging
import re
import unicodedata
import certifi
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.error import BadRequest
from pymongo.errors import ConnectionFailure, ConfigurationError
from modules.player.stats import _compute_class_baseline_for_level


from modules import player_manager, game_data, file_ids

# <<< [MUDANÇA] Importa as funções de stats necessárias >>>
from modules.player.stats import (
    _get_point_gains_for_class, 
    _get_class_key_normalized,
    get_player_total_stats # Precisamos desta para a cura do HP
)

logger = logging.getLogger(__name__)

PROFILE_KEYS = ['max_hp', 'attack', 'defense', 'initiative', 'luck']

# ... (Funções _slugify e _get_class_media estão corretas) ...
def _slugify(text: str) -> str:
    if not text: return ""
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    norm = re.sub(r"[^\w\s-]", "", norm).strip().lower()
    norm = re.sub(r"[-\s]+", "_", norm)
    return norm

def _get_class_media(player_data: dict, purpose: str = "status"):
    raw_cls = (player_data.get("class") or "").strip()
    base_cls_key = raw_cls.lower()
    cls_slug = _slugify(base_cls_key)
    logger.debug(f"[_get_class_media] Raw Class: '{raw_cls}', Base Key: '{base_cls_key}', Slug: '{cls_slug}'")
    classes_data = getattr(game_data, "CLASSES_DATA", {}) or {}
    cls_cfg = classes_data.get(raw_cls) or classes_data.get(base_cls_key) or {}
    candidates = []
    file_id_name_from_class = cls_cfg.get("file_id_name")
    if file_id_name_from_class:
        candidates.append(file_id_name_from_class)
    if cls_cfg.get("status_file_id_key"):
        candidates.append(cls_cfg["status_file_id_key"])
    if cls_slug:
        candidates.extend([
            f"status_video_{cls_slug}", f"status_{cls_slug}",
            f"class_{cls_slug}_status", f"classe_{cls_slug}_media"
        ])
    candidates.append("status_video")
    unique_candidates = list(filter(None, dict.fromkeys(candidates)))
    logger.debug(f"[_get_class_media] Candidate Keys: {unique_candidates}")
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
            logger.error(f"[_get_class_media] Error looking up key '{key}': {e}", exc_info=False)
    logger.warning(f"[_get_class_media] No valid media found for class '{raw_cls}' after trying all keys.")
    return None

async def _get_status_content(player_data: dict) -> tuple[str, InlineKeyboardMarkup]:
    """Gera o texto e o teclado do menu de status."""
    
    total_stats = await get_player_total_stats(player_data)
    
    char_name = player_data.get('character_name', 'Aventureiro(a)')
    status_text = f"👤 <b>Status de {char_name}</b>\n\n"
    emoji_map = {'max_hp': '❤️', 'attack': '⚔️', 'defense': '🛡️', 'initiative': '🏃', 'luck': '🍀'}
    name_map = {'max_hp': 'HP Máximo', 'attack': 'Ataque', 'defense': 'Defesa', 'initiative': 'Iniciativa', 'luck': 'Sorte'}

    for stat in PROFILE_KEYS:
        raw_val = total_stats.get(stat, 0)
        # Formata tudo como inteiro
        val_str = str(int(raw_val))
        status_text += f"{emoji_map[stat]} <b>{name_map[stat]}:</b> {val_str}\n"

    available_points = int(player_data.get('stat_points', 0) or 0)
    status_text += f"\n✨ <b>Pontos disponíveis:</b> {available_points}"

    keyboard_rows = []
    if available_points > 0:
        ckey = _get_class_key_normalized(player_data)
        gains = _get_point_gains_for_class(ckey)

        row1 = [InlineKeyboardButton(f"➕ ❤️‍🩹 𝐇𝐏 (+{gains['max_hp']})", callback_data='upgrade_max_hp')]
        if 'attack' in PROFILE_KEYS: 
            row1.append(InlineKeyboardButton(f"➕ ⚔️ 𝐀𝐓𝐊 (+{gains['attack']})", callback_data='upgrade_attack'))
        keyboard_rows.append(row1)

        row2 = []
        if 'defense' in PROFILE_KEYS: 
            row2.append(InlineKeyboardButton(f"➕ 🛡 𝐃𝐄𝐅 (+{gains['defense']})", callback_data='upgrade_defense'))
        if 'initiative' in PROFILE_KEYS: 
            row2.append(InlineKeyboardButton(f"➕ 🏃‍♂️ 𝐈𝐍𝐈 (+{gains['initiative']})", callback_data='upgrade_initiative'))
        if row2: keyboard_rows.append(row2)

        if 'luck' in PROFILE_KEYS:
            keyboard_rows.append([InlineKeyboardButton(f"➕ 🍀 𝐒𝐎𝐑𝐓𝐄 (+{gains['luck']})", callback_data='upgrade_luck')])

    keyboard_rows.append([InlineKeyboardButton("⛩️ 𝐀𝐬𝐜𝐞𝐧𝐬𝐚̃𝐨", callback_data="open_evolution_menu")])
    keyboard_rows.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data='profile')]) 

    return status_text, InlineKeyboardMarkup(keyboard_rows)

async def show_status_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id 
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

    status_text, reply_markup = await _get_status_content(player_data)

    if update.callback_query:
        query = update.callback_query
        await query.answer() 
        try:
            await query.delete_message()
        except Exception as e_del:
            logger.debug(f"Não foi possível apagar mensagem anterior em show_status_menu: {e_del}")
        media = _get_class_media(player_data, "status")
        try:
            if media and media.get("id") and chat_id:
                media_id = media["id"]
                media_type = (media.get("type") or "photo").lower()
                if media_type == "video":
                    await context.bot.send_video(chat_id=chat_id, video=media_id, caption=status_text, reply_markup=reply_markup, parse_mode='HTML')
                else:
                    await context.bot.send_photo(chat_id=chat_id, photo=media_id, caption=status_text, reply_markup=reply_markup, parse_mode='HTML')
            elif chat_id:
                await context.bot.send_message(chat_id=chat_id, text=status_text, reply_markup=reply_markup, parse_mode='HTML')
            else:
                logger.error("show_status_menu (callback): chat_id inválido.")
        except Exception as e_send:
            logger.error(f"Erro ao enviar menu de status (callback) para {user_id}: {e_send}", exc_info=True)
            if chat_id: await context.bot.send_message(chat_id, "Ocorreu um erro ao exibir o menu de status.")
    else:
        if update.message and chat_id:
            await update.message.reply_text(text=status_text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            logger.error("show_status_menu (comando): update.message ou chat_id inválido.")


# <<< [MUDANÇA] Lógica de upgrade_stat_callback CORRIGIDA (V6) >>>
async def upgrade_stat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Aplica o ganho de stat correto (ex: +2, +3) ao stat base.
    (VERSÃO CORRIGIDA FINAL)
    """
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # --- 1. Carrega os dados ---
    player_data = await player_manager.get_player_data(user_id) 
    if not player_data:
        try: await query.answer("Erro: Não foi possível carregar seus dados.", show_alert=True)
        except Exception: pass
        return

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

    # --- 2. Aplica o upgrade (LÓGICA CORRIGIDA) ---
    player_data["stat_points"] = pool - 1
    
    ckey = _get_class_key_normalized(player_data)
    gains = _get_point_gains_for_class(ckey) 
    increment = gains.get(profile_stat, 1)

    # <<< [ESTA É A CORREÇÃO PRINCIPAL] >>>
    
    # 1. Calcula o HP base do Nível (ex: 122)
    #    (A CORREÇÃO DO BUG ESTÁ AQUI)
    lvl = int(player_data.get("level", 1)) # <-- USA , 1 DENTRO do get()
    
    class_baseline_stats = _compute_class_baseline_for_level(ckey, lvl)
    
    # 2. Pega o valor que o jogador tem *agora* (que pode já ter sido investido)
    #    ou a baseline se for a primeira vez.
    current_value = int(player_data.get(profile_stat, class_baseline_stats.get(profile_stat, 0)))

    # 3. Adiciona o novo incremento
    player_data[profile_stat] = current_value + int(increment)
    
    # <<< [FIM DA CORREÇÃO PRINCIPAL] >>>
    
    # Lógica especial para HP (curar o jogador)
    if profile_stat == 'max_hp':
        current_hp = int(player_data.get("current_hp", 0))
        
        player_data_copy = player_data.copy()
        total_stats = await get_player_total_stats(player_data_copy)
        new_max_hp = int(total_stats.get('max_hp'))
        
        if current_hp < new_max_hp:
            player_data["current_hp"] = min(current_hp + int(increment), new_max_hp)

    # --- 3. Salva os dados modificados ---
    try:
        await player_manager.save_player_data(user_id, player_data)
    except Exception as e_save:
        logger.error(f"Falha ao salvar dados após upgrade de stat para {user_id}: {e_save}", exc_info=True)
        await query.answer("Erro ao salvar o upgrade.", show_alert=True)
        player_data["stat_points"] = pool # Devolve o ponto se falhar
        return

    # --- 4. Gera o conteúdo COM os dados atualizados ---
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
            # Ignora o erro "message is not modified"
            pass
    except Exception as e_generic_caption:
        logger.error(f"Erro genérico ao editar menu de status (caption): {e_generic_caption}", exc_info=True)
        
# ... (close_status_callback está correto) ...
async def close_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
close_status_handler = CallbackQueryHandler(close_status_callback, pattern=r'^close_status$')