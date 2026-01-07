# handlers/status_handler.py
# (VERSÃO CORRIGIDA: Salva em 'invested' para compatibilidade com stats.py)

import logging
import re
import unicodedata
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.error import BadRequest
from modules.auth_utils import get_current_player_id 
from modules import player_manager, game_data, file_ids

# --- IMPORTS ESSENCIAIS DO STATS.PY ---
from modules.player.stats import (
    _get_point_gains_for_class, 
    _get_class_key_normalized,
    get_player_total_stats,
    _compute_class_baseline_for_level,
    PROFILE_KEYS,
)

logger = logging.getLogger(__name__)

# ==============================================================================
# FUNÇÕES AUXILIARES DE MÍDIA
# ==============================================================================
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
    
    classes_data = getattr(game_data, "CLASSES_DATA", {}) or {}
    cls_cfg = classes_data.get(raw_cls) or classes_data.get(base_cls_key) or {}
    
    candidates = []
    if cls_cfg.get("file_id_name"): candidates.append(cls_cfg.get("file_id_name"))
    if cls_cfg.get("status_file_id_key"): candidates.append(cls_cfg["status_file_id_key"])
    if cls_slug:
        candidates.extend([
            f"status_video_{cls_slug}", f"status_{cls_slug}",
            f"class_{cls_slug}_status", f"classe_{cls_slug}_media"
        ])
    candidates.append("status_video")
    
    unique_candidates = list(filter(None, dict.fromkeys(candidates)))
    
    for key in unique_candidates:
        try:
            fd = file_ids.get_file_data(key)
            if fd and fd.get("id"):
                return fd
        except Exception:
            pass
    return None

# ==============================================================================
# GERAÇÃO DE CONTEÚDO DO MENU
# ==============================================================================
async def _get_status_content(player_data: dict) -> tuple[str, InlineKeyboardMarkup]:
    """
    Gera o texto e o teclado do menu de status.
    Usa get_player_total_stats para mostrar os valores REAIS.
    """
    # Calcula status totais (Base + Investido + Equipamentos + Buffs)
    total_stats = await get_player_total_stats(player_data)
    
    char_name = player_data.get('character_name', 'Aventureiro(a)')
    status_text = f"👤 <b>Status de {char_name}</b>\n\n"
    
    emoji_map = {'max_hp': '❤️', 'attack': '⚔️', 'defense': '🛡️', 'initiative': '🏃', 'luck': '🍀'}
    name_map = {'max_hp': 'HP Máximo', 'attack': 'Ataque', 'defense': 'Defesa', 'initiative': 'Iniciativa', 'luck': 'Sorte'}

    # Exibe os valores finais calculados
    for stat in PROFILE_KEYS:
        raw_val = total_stats.get(stat, 0)
        val_str = str(int(raw_val))
        status_text += f"{emoji_map.get(stat, '')} <b>{name_map.get(stat, stat.title())}:</b> {val_str}\n"

    available_points = int(player_data.get('stat_points', 0) or 0)
    status_text += f"\n✨ <b>Pontos disponíveis:</b> {available_points}"

    # Monta o teclado de distribuição de pontos
    keyboard_rows = []
    if available_points > 0:
        ckey = _get_class_key_normalized(player_data)
        # Pega quanto cada ponto vale para essa classe
        gains = _get_point_gains_for_class(ckey)

        # Linha 1: HP e Ataque
        row1 = [InlineKeyboardButton(f"➕ ❤️‍🩹 𝐇𝐏 (+{gains.get('max_hp', 1)})", callback_data='upgrade_max_hp')]
        if 'attack' in PROFILE_KEYS: 
            row1.append(InlineKeyboardButton(f"➕ ⚔️ 𝐀𝐓𝐊 (+{gains.get('attack', 1)})", callback_data='upgrade_attack'))
        keyboard_rows.append(row1)

        # Linha 2: Defesa e Iniciativa
        row2 = []
        if 'defense' in PROFILE_KEYS: 
            row2.append(InlineKeyboardButton(f"➕ 🛡 𝐃𝐄𝐅 (+{gains.get('defense', 1)})", callback_data='upgrade_defense'))
        if 'initiative' in PROFILE_KEYS: 
            row2.append(InlineKeyboardButton(f"➕ 🏃‍♂️ 𝐈𝐍𝐈 (+{gains.get('initiative', 1)})", callback_data='upgrade_initiative'))
        if row2: keyboard_rows.append(row2)

        # Linha 3: Sorte
        if 'luck' in PROFILE_KEYS:
            keyboard_rows.append([InlineKeyboardButton(f"➕ 🍀 𝐒𝐎𝐑𝐓𝐄 (+{gains.get('luck', 1)})", callback_data='upgrade_luck')])

    keyboard_rows.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data='profile')]) 

    return status_text, InlineKeyboardMarkup(keyboard_rows)

# ==============================================================================
# HANDLERS PRINCIPAIS
# ==============================================================================

async def show_status_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_current_player_id(update, context)
    chat_id = update.effective_chat.id 
    player_data = await player_manager.get_player_data(user_id) 

    if not player_data:
        text = "Você precisa criar um personagem. Use /start."
        if update.callback_query:
            await update.callback_query.answer(text, show_alert=True)
        elif update.message:
            await update.message.reply_text(text)
        return

    status_text, reply_markup = await _get_status_content(player_data)

    if update.callback_query:
        query = update.callback_query
        try:
            await query.edit_message_caption(caption=status_text, reply_markup=reply_markup, parse_mode='HTML')
        except Exception:
            try:
                await query.edit_message_text(text=status_text, reply_markup=reply_markup, parse_mode='HTML')
            except Exception:
                try: await query.delete_message() 
                except: pass
                await _send_fresh_status_message(context, chat_id, player_data, status_text, reply_markup)
    else:
        await _send_fresh_status_message(context, chat_id, player_data, status_text, reply_markup)

async def _send_fresh_status_message(context, chat_id, player_data, text, markup):
    """Helper para enviar a mensagem com mídia correta."""
    media = _get_class_media(player_data, "status")
    if media and media.get("id"):
        try:
            if media.get("type") == "video":
                await context.bot.send_video(chat_id, video=media["id"], caption=text, reply_markup=markup, parse_mode='HTML')
            else:
                await context.bot.send_photo(chat_id, photo=media["id"], caption=text, reply_markup=markup, parse_mode='HTML')
        except:
            await context.bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')
    else:
        await context.bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')


async def upgrade_stat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = get_current_player_id(update, context)

    player_data = await player_manager.get_player_data(user_id) 
    if not player_data:
        await query.answer("Erro ao carregar dados.", show_alert=True)
        return

    # 1. Verifica pontos disponíveis
    pool = int(player_data.get("stat_points", 0) or 0)
    if pool <= 0:
        await query.answer("Sem pontos disponíveis!", show_alert=True)
        return

    # 2. Identifica o atributo vindo do botão
    profile_stat = query.data.replace('upgrade_', '')
    if profile_stat not in PROFILE_KEYS:
        await query.answer("Atributo inválido.", show_alert=True)
        return

    # 3. Mapeia para a chave interna (Canônica)
    stat_mapping = {
        'max_hp': 'max_hp',
        'attack': 'attack',
        'defense': 'defense',
        'initiative': 'initiative',
        'luck': 'luck'
    }
    internal_key = stat_mapping.get(profile_stat, profile_stat)

    # 4. CORREÇÃO: Salva em "invested" (que é onde o stats.py lê os pontos extras)
    if "invested" not in player_data or not isinstance(player_data["invested"], dict):
        player_data["invested"] = {}

    current_clicks = player_data["invested"].get(internal_key, 0)
    player_data["invested"][internal_key] = current_clicks + 1

    # Desconta o ponto
    player_data["stat_points"] = pool - 1

    # Recalcula para atualizar HP atual se necessário e mostrar valores corretos no menu
    new_totals = await get_player_total_stats(player_data)
    
    # (Opcional) Atualiza valores visuais no dict local para feedback imediato no menu
    for stat in PROFILE_KEYS:
        player_data[stat] = new_totals.get(stat, 0)

    # Se aumentou Max HP, cura o valor ganho para não ficar com barra vazia
    if internal_key == 'max_hp':
        ckey = _get_class_key_normalized(player_data)
        gains = _get_point_gains_for_class(ckey)
        hp_increment = gains.get('max_hp', 1) 
        player_data["current_hp"] = int(player_data.get("current_hp", 0)) + hp_increment

    await player_manager.save_player_data(user_id, player_data)
    
    stat_display_name = profile_stat.replace('max_', '').title()
    if profile_stat == 'max_hp': stat_display_name = "HP"
    await query.answer(f"Subiu {stat_display_name}!")

    # Atualiza o menu
    status_text, reply_markup = await _get_status_content(player_data)
    try:
        await query.edit_message_caption(caption=status_text, reply_markup=reply_markup, parse_mode='HTML')
    except Exception:
        try:
            await query.edit_message_text(text=status_text, reply_markup=reply_markup, parse_mode='HTML')
        except:
            pass 
        
async def close_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try: await query.delete_message()
    except: pass

# ==============================================================================
# EXPORTS
# ==============================================================================
status_command_handler = CommandHandler("status", show_status_menu)
status_open_handler = CallbackQueryHandler(show_status_menu, pattern=r'^status_open$')
status_callback_handler = CallbackQueryHandler(upgrade_stat_callback, pattern=r'^upgrade_')
close_status_handler = CallbackQueryHandler(close_status_callback, pattern=r'^close_status$')