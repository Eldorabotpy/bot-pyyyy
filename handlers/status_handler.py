# handlers/status_handler.py

import logging
import re
import unicodedata
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from modules import player_manager, game_data
from modules import file_ids  # ✅ gerenciador de mídia baseado no JSON

logger = logging.getLogger(__name__)

# Atributos que mostramos/permitimos upar
PROFILE_KEYS = ['max_hp', 'attack', 'defense', 'initiative', 'luck']


def _slugify(text: str) -> str:
    """
    Normaliza 'Caçador Arcano' -> 'cacador_arcano'
    """
    if not text:
        return ""
    norm = unicodedata.normalize("NFKD", text)
    norm = norm.encode("ascii", "ignore").decode("ascii")
    norm = re.sub(r"\s+", "_", norm.strip().lower())
    norm = re.sub(r"[^a-z0-9_]", "", norm)
    return norm


def _get_class_media(player_data: dict, purpose: str = "status"):
    """
    Escolhe mídia cadastrada no file_ids.json com base na classe.
    Evita chaves contendo 'abertura'.
    Retorna {'id': '<file_id>', 'type': 'photo'|'video'} ou None.
    """
    raw_cls = (player_data.get("class") or player_data.get("class_tag") or "").strip()
    cls = _slugify(raw_cls)
    purpose = (purpose or "").strip().lower()

    candidates = []
    if cls:
        candidates += [
            f"classe_{cls}_media",
            f"class_{cls}_media",
            f"{cls}_media",
            f"{purpose}_video_{cls}",
            f"{purpose}_{cls}",
            f"{cls}_{purpose}_video",
            f"{cls}_{purpose}",
            (f"status_video_{cls}" if purpose == "status" else f"profile_video_{cls}"),
            (f"status_{cls}" if purpose == "status" else f"perfil_video_{cls}"),
            f"class_{cls}_{purpose}",
        ]

    # Fallbacks genéricos
    if purpose == "status":
        candidates += ["status_video", "status_photo", "status_media"]
    else:
        candidates += ["perfil_video", "personagem_video", "profile_video", "perfil_foto", "profile_photo"]

    # Também olha CLASSES_DATA, se houver
    classes_data = getattr(game_data, "CLASSES_DATA", {}) or {}
    cls_cfg = classes_data.get(raw_cls) or classes_data.get(cls) or {}
    for k in ("status_file_id_key", "profile_file_id_key", "profile_media_key", "file_id_name", "file_id_key"):
        if cls_cfg and cls_cfg.get(k):
            candidates.insert(0, cls_cfg[k])

    tried = []
    for key in [k for k in candidates if k and "abertura" not in k.lower()]:
        tried.append(key)
        fd = file_ids.get_file_data(key)
        if fd and fd.get("id"):
            logger.info("[STATUS_MEDIA] purpose=%s class=%s slug=%s chosen_key=%s", purpose, raw_cls, cls, key)
            return fd

    logger.info("[STATUS_MEDIA] purpose=%s class=%s slug=%s chosen=None tried=%s", purpose, raw_cls, cls, tried)
    return None


async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except Exception:
        pass
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except Exception:
        pass
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)


def _build_upgrade_keyboard(available_points: int) -> InlineKeyboardMarkup:
    """
    Teclado de upgrades:
      - HP: +3
      - ATK/DEF/INI/SORTE: +1
      + botão de Evolução de Classe
    """
    rows = []
    if available_points > 0:
        rows.append([
            InlineKeyboardButton("➕ HP (+3)", callback_data='upgrade_max_hp'),
            InlineKeyboardButton("➕ ATK (+1)", callback_data='upgrade_attack'),
        ])
        rows.append([
            InlineKeyboardButton("➕ DEF (+1)", callback_data='upgrade_defense'),
            InlineKeyboardButton("➕ INI (+1)", callback_data='upgrade_initiative'),
        ])
        rows.append([
            InlineKeyboardButton("➕ SORTE (+1)", callback_data='upgrade_luck'),
        ])

    # ✅ Botão permanente de Evolução de Classe
    #    Usamos um callback_data padronizado que o class_evolution_handler escuta.
    rows.append([InlineKeyboardButton("🎐 𝐄𝐯𝐨𝐥𝐮çã𝐨 𝐝𝐞 𝐂𝐥𝐚𝐬𝐬𝐞", callback_data="status_evolution_open")])

    # Botão de voltar ao perfil/personagem
    rows.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data='profile')])
    return InlineKeyboardMarkup(rows)


async def show_status_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a tela de status do jogador com upgrades; tenta usar a mídia da classe."""
    user_id = (update.effective_user.id if update.effective_user else None)
    if not user_id:
        if update.callback_query:
            await update.callback_query.answer("Não foi possível identificar o jogador.", show_alert=True)
        return

    player_data = player_manager.get_player_data(user_id)
    if not player_data:
        if update.callback_query:
            await update.callback_query.edit_message_text("Você precisa criar um personagem. Use /start.")
        else:
            await update.message.reply_text("Você precisa criar um personagem. Use /start.")
        return

    # Totais com equipamentos (apenas para exibir)
    total_stats = player_manager.get_player_total_stats(player_data)

    char_name = player_data.get('character_name', 'Aventureiro(a)')
    status_text = f"👤 <b>Status de {char_name}</b>\n\n"

    emoji_map = {'max_hp': '❤️', 'attack': '⚔️', 'defense': '🛡️', 'initiative': '🏃', 'luck': '🍀'}
    name_map  = {'max_hp': 'HP Máximo', 'attack': 'Ataque', 'defesa': 'Defesa', 'defense': 'Defesa', 'initiative': 'Iniciativa', 'luck': 'Sorte'}

    for stat in PROFILE_KEYS:
        label_key = 'defesa' if stat == 'defense' else stat
        val = int(total_stats.get(stat, 0))
        status_text += f"{emoji_map[stat]} <b>{name_map[label_key]}:</b> {val}\n"

    available_points = int(player_data.get('stat_points', 0) or 0)
    status_text += f"\n✨ <b>Pontos disponíveis:</b> {available_points}"

    reply_markup = _build_upgrade_keyboard(available_points)

    if update.callback_query:
        q = update.callback_query
        await q.answer()
        chat_id = update.effective_chat.id

        if q.data == 'status_open':
            media = _get_class_media(player_data, "status")
            if media and media.get("id"):
                try:
                    await q.delete_message()
                except Exception:
                    pass

                if (media.get("type") or "photo").lower() == "video":
                    await context.bot.send_video(
                        chat_id=chat_id, video=media["id"],
                        caption=status_text, reply_markup=reply_markup, parse_mode='HTML'
                    )
                else:
                    await context.bot.send_photo(
                        chat_id=chat_id, photo=media["id"],
                        caption=status_text, reply_markup=reply_markup, parse_mode='HTML'
                    )
                return

        await _safe_edit_or_send(q, context, chat_id, status_text, reply_markup, parse_mode='HTML')
        return

    await update.message.reply_text(text=status_text, reply_markup=reply_markup, parse_mode='HTML')


async def upgrade_stat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Aplica upgrade com custo fixo de 1 ponto:
      - max_hp: +3 (e current_hp sobe +3 com clamp ao novo máximo)
      - attack/defense/initiative/luck: +1
    Respeita o teto: 1 ponto por nível (level-1) OU a regra por classe se seu player_manager usar progressão avançada.
    """
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    player_data = player_manager.get_player_data(user_id)
    if not player_data:
        await query.answer("Crie um personagem com /start.", show_alert=True)
        return

    # qual stat
    profile_stat = query.data.replace('upgrade_', '')
    if profile_stat not in PROFILE_KEYS:
        await query.answer("Atributo desconhecido.", show_alert=True)
        return

    # Teto: allowed = level-1 ; spent = quanto já foi aplicado nos atributos base acima do baseline
    allowed = player_manager.allowed_points_for_level(player_data)
    spent = player_manager.compute_spent_status_points(player_data)
    pool = int(player_data.get("stat_points", 0) or 0)

    # Se já atingiu o teto ou não tem pontos, não permite
    if pool <= 0 or spent >= allowed:
        await query.answer("Você não tem pontos para gastar!", show_alert=True)
        await show_status_menu(update, context)
        return

    # Gasta 1 do pool
    player_data["stat_points"] = max(0, pool - 1)

    # Aplica incremento no atributo base do SAVE
    if profile_stat == "max_hp":
        inc = 3
        new_max = int(player_data.get("max_hp", 0)) + inc
        player_data["max_hp"] = new_max
        cur = int(player_data.get("current_hp", 0)) + inc
        player_data["current_hp"] = min(cur, new_max)
    else:
        inc = 1
        player_data[profile_stat] = int(player_data.get(profile_stat, 0)) + inc

    # Persiste
    player_manager.save_player_data(user_id, player_data)

    # Volta ao menu de status
    await show_status_menu(update, context)


async def close_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        await query.delete_message()
    except Exception:
        pass


# ==== EXPORTS ====
status_command_handler  = CommandHandler("status", show_status_menu)
status_open_handler     = CallbackQueryHandler(show_status_menu, pattern=r'^status_open$')
status_callback_handler = CallbackQueryHandler(upgrade_stat_callback, pattern=r'^upgrade_')
close_status_handler    = CallbackQueryHandler(close_status_callback, pattern=r'^close_status$')
