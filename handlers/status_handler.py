# handlers/status_handler.py
# (VERSÃO CORRIGIDA: Exibição dinâmica de Ataque vs Inteligência)

import logging
import re
import unicodedata
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from modules.auth_utils import get_current_player_id 
from modules import player_manager, game_data, file_ids

# --- IMPORTS DO STATS.PY ---
from modules.player.stats import (
    _get_point_gains_for_class, 
    _get_class_key_normalized,
    get_player_total_stats,
    PROFILE_KEYS,
)

logger = logging.getLogger(__name__)

# Lista de classes mágicas para verificação visual
VISUAL_MAGIC_CLASSES = {
    "mago", "arquimago", "feiticeiro", "bruxo", "necromante", 
    "curandeiro", "sacerdote", "clerigo", "druida", "xama",
    "bardo", "mistico", "elementalista"
}

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
# GERAÇÃO DE CONTEÚDO DO MENU (LÓGICA VISUAL AJUSTADA)
# ==============================================================================
async def _get_status_content(player_data: dict) -> tuple[str, InlineKeyboardMarkup]:
    # Calcula status totais
    total_stats = await get_player_total_stats(player_data)
    
    char_name = player_data.get('character_name', 'Aventureiro(a)')
    ckey = _get_class_key_normalized(player_data)
    raw_class = (player_data.get("class") or "").lower()

    # Verifica se é mágico visualmente
    is_magic = False
    if ckey in VISUAL_MAGIC_CLASSES: is_magic = True
    elif any(m in raw_class for m in VISUAL_MAGIC_CLASSES): is_magic = True

    status_text = f"👤 <b>Status de {char_name}</b>\n\n"
    
    # Mapeamento de Nomes e Emojis
    # NOTA: Magos veem "Inteligência", Guerreiros veem "Ataque"
    display_map = {
        'max_hp':       ('❤️', 'HP Máximo'),
        'attack':       ('⚔️', 'Ataque'),
        'magic_attack': ('🔮', 'Inteligência'), # Tradução corrigida
        'defense':      ('🛡️', 'Defesa'),
        'initiative':   ('🏃', 'Iniciativa'),
        'luck':         ('🍀', 'Sorte')
    }

    # Loop de Exibição Filtrado
    for stat in PROFILE_KEYS:
        # REGRA 1: Se for Mago, esconde o "Attack" físico e mostra apenas Magic Attack
        if is_magic and stat == 'attack': continue
        
        # REGRA 2: Se for Físico, esconde "Magic Attack"
        if not is_magic and stat == 'magic_attack': continue

        # Pega o valor
        raw_val = total_stats.get(stat, 0)
        val_str = str(int(raw_val))
        
        # Formata a linha
        if stat in display_map:
            emoji, label = display_map[stat]
            status_text += f"{emoji} <b>{label}:</b> {val_str}\n"

    available_points = int(player_data.get('stat_points', 0) or 0)
    status_text += f"\n✨ <b>Pontos disponíveis:</b> {available_points}"

    # Monta o teclado de distribuição
    keyboard_rows = []
    if available_points > 0:
        gains = _get_point_gains_for_class(ckey)

        # Botão Linha 1: HP e (Ataque OU Inteligência)
        # O callback continua sendo 'upgrade_attack' pois usamos o mesmo "balde" de pontos
        # mas o rótulo muda para o jogador entender.
        
        hp_btn = InlineKeyboardButton(f"➕ ❤️‍🩹 𝐇𝐏 (+{gains.get('max_hp', 1)})", callback_data='upgrade_max_hp')
        
        if is_magic:
            # Botão para Magos: Mostra INT ou MAGIA
            atk_label = f"➕ 🔮 𝐈𝐍𝐓 (+{gains.get('magic_attack', gains.get('attack', 1))})"
            # Dica: Magos usam o mesmo stat base de 'attack' para upar magia no nosso sistema híbrido
            atk_btn = InlineKeyboardButton(atk_label, callback_data='upgrade_attack')
        else:
            # Botão para Físicos
            atk_label = f"➕ ⚔️ 𝐀𝐓𝐊 (+{gains.get('attack', 1)})"
            atk_btn = InlineKeyboardButton(atk_label, callback_data='upgrade_attack')

        keyboard_rows.append([hp_btn, atk_btn])

        # Linha 2: Defesa e Iniciativa
        row2 = []
        if 'defense' in PROFILE_KEYS: 
            row2.append(InlineKeyboardButton(f"➕ 🛡 𝐃𝐄𝐅 (+{gains.get('defense', 1)})", callback_data='upgrade_defense'))
        if 'initiative' in PROFILE_KEYS: 
            row2.append(InlineKeyboardButton(f"➕ 🏃 𝐈𝐍𝐈 (+{gains.get('initiative', 1)})", callback_data='upgrade_initiative'))
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

    if not player_data: return

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
    if not player_data: return

    pool = int(player_data.get("stat_points", 0) or 0)
    if pool <= 0:
        await query.answer("Sem pontos disponíveis!", show_alert=True)
        return

    profile_stat = query.data.replace('upgrade_', '')
    
    # Mapeamento interno simples
    internal_key = profile_stat
    if profile_stat == 'magic_attack': internal_key = 'attack' # Redireciona upgrade de magia para bucket de atk

    if "invested" not in player_data or not isinstance(player_data["invested"], dict):
        player_data["invested"] = {}

    current_clicks = player_data["invested"].get(internal_key, 0)
    player_data["invested"][internal_key] = current_clicks + 1
    player_data["stat_points"] = pool - 1

    # Atualiza visual instantâneo (opcional, pois get_player_total_stats recalcula tudo)
    # Apenas salva e recarrega a tela
    await player_manager.save_player_data(user_id, player_data)
    
    display_name = profile_stat.upper()
    if profile_stat == 'attack': 
        # Feedback inteligente
        ckey = _get_class_key_normalized(player_data)
        if ckey in VISUAL_MAGIC_CLASSES: display_name = "INTELIGÊNCIA"
        else: display_name = "ATAQUE"

    await query.answer(f"Subiu {display_name}!")

    status_text, reply_markup = await _get_status_content(player_data)
    try:
        await query.edit_message_caption(caption=status_text, reply_markup=reply_markup, parse_mode='HTML')
    except:
        try: await query.edit_message_text(text=status_text, reply_markup=reply_markup, parse_mode='HTML')
        except: pass

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