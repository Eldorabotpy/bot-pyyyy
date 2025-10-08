# handlers/profile_handler.py

import logging
import unicodedata
import re
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules.player.premium import PremiumManager
from modules import player_manager, game_data
from modules import file_ids

logger = logging.getLogger(__name__)

# ===== util =====
def _slugify(text: str) -> str:
    if not text:
        return ""
    norm = unicodedata.normalize("NFKD", text)
    norm = norm.encode("ascii", "ignore").decode("ascii")
    norm = re.sub(r"\s+", "_", norm.strip().lower())
    norm = re.sub(r"[^a-z0-9_]", "", norm)
    return norm

def _get_class_media(player_data: dict, purpose: str = "personagem"):
    """
    Encontra mídia no file_ids.json para a classe do jogador.
    Prioriza 'classe_<slug>_media'. Evita chaves com 'abertura'.
    Retorna {'id': str, 'type': 'photo'|'video'} ou None.
    """
    raw_cls = (player_data.get("class") or player_data.get("class_tag") or "").strip()
    cls = _slugify(raw_cls)
    purpose = (purpose or "").strip().lower()

    candidates = []

    # 1) chaves vindas de CLASSES_DATA (se existir)
    classes_data = getattr(game_data, "CLASSES_DATA", {}) or {}
    cls_cfg = classes_data.get(raw_cls) or classes_data.get(cls) or {}
    for k in ("profile_file_id_key", "profile_media_key", "file_id_name", "status_file_id_key", "file_id_key"):
        if cls_cfg and cls_cfg.get(k):
            candidates.append(cls_cfg[k])

    # 2) padrões por classe
    if cls:
        candidates += [
            f"classe_{cls}_media",   # ✅ padrão preferido
            f"class_{cls}_media",
            f"{cls}_media",
            f"perfil_video_{cls}",
            f"personagem_video_{cls}",
            f"profile_video_{cls}",
            f"{purpose}_video_{cls}",
            f"{purpose}_{cls}",
            f"{cls}_{purpose}_video",
            f"{cls}_{purpose}",
        ]

    # 3) fallbacks genéricos
    candidates += ["perfil_video", "personagem_video", "profile_video", "perfil_foto", "profile_photo"]

    tried = []
    for key in [k for k in candidates if k and "abertura" not in k.lower()]:
        tried.append(key)
        fd = file_ids.get_file_data(key)
        if fd and fd.get("id"):
            logger.info("[PROFILE_MEDIA] purpose=%s class=%s slug=%s chosen=%s", purpose, raw_cls, cls, key)
            return fd

    logger.info("[PROFILE_MEDIA] purpose=%s class=%s slug=%s chosen=None tried=%s", purpose, raw_cls, cls, tried)
    return None

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except Exception:
        pass
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except Exception:
        pass
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

def _bar(current: int, total: int, blocks: int = 10, filled_char: str = '🟧', empty_char: str = '⬜️') -> str:
    if total <= 0:
        filled = blocks
    else:
        ratio = max(0.0, min(1.0, float(current) / float(total)))
        filled = int(round(ratio * blocks))
    return filled_char * filled + empty_char * (blocks - filled)

def _normalize_profession(raw):
    if not raw:
        return None
    if isinstance(raw, str):
        return (raw, 1, 0)
    if isinstance(raw, dict) and ('type' in raw):
        t = raw.get('type') or None
        if not t: return None
        return (t, int(raw.get('level', 1)), int(raw.get('xp', 0)))
    if isinstance(raw, dict):
        for k, v in raw.items():
            if isinstance(v, dict):
                return (k, int(v.get('level', 1)), int(v.get('xp', 0)))
            return (k, 1, 0)
    return None

def _class_key_from_player(player_data: dict) -> str:
    if player_data.get("class_key"):
        return str(player_data["class_key"])
    raw = (player_data.get("class") or "").strip()
    return _slugify(raw) or "_default"

async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ao clicar em Personagem/Profile: envia o VÍDEO/FOTO da classe (se houver) já com o perfil."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    chat_id = query.message.chat_id
    player_data = player_manager.get_player_data(user_id)

    if not player_data:
        await _safe_edit_or_send(query, context, chat_id, "Erro: Personagem não encontrado. Use /start para começar.")
        return

    # ===== totais (base + equipamentos) =====
    totals = player_manager.get_player_total_stats(player_data)
    total_hp_max = int(totals.get('max_hp', 50))
    total_atk    = int(totals.get('attack', 0))
    total_def    = int(totals.get('defense', 0))
    total_ini    = int(totals.get('initiative', 0))
    total_luck   = int(totals.get('luck', 0))

    current_hp = max(0, min(int(player_data.get('current_hp', total_hp_max)), total_hp_max))
    chance_esquiva = int(player_manager.get_player_dodge_chance(player_data) * 100)
    chance_ataque_duplo = int(player_manager.get_player_double_attack_chance(player_data) * 100)

    location_key  = player_data.get('current_location', 'reino_eldora')
    location_name = (game_data.REGIONS_DATA or {}).get(location_key, {}).get('display_name', 'Lugar Desconhecido')

    # =================================================================
    # ===== BLOCO PREMIUM TOTALMENTE CORRIGIDO E MELHORADO =====
    # =================================================================
    premium_line = ""
    # Usamos a nova função correta: has_premium_plan(user_id)
    if player_manager.has_premium_plan(user_id):
        premium = PremiumManager(player_data)
        tier_name = premium.tier.capitalize() if premium.tier else "Premium"
        exp_date = premium.expiration_date
        
        premium_line = f"\n👑 <b>Status Premium:</b> {tier_name}"
        if exp_date:
            premium_line += f"\n(Expira em: {exp_date.strftime('%d/%m/%Y')})"
        else:
            premium_line += " (Permanente)"
    
    max_energy   = int(player_manager.get_player_max_energy(player_data))
    combat_level = int(player_data.get('level', 1))
    combat_xp    = int(player_data.get('xp', 0))
    try:
        combat_next = int(game_data.get_xp_for_next_combat_level(combat_level))
    except Exception:
        combat_next = 0
    combat_bar = _bar(combat_xp, combat_next)

    prof_norm = _normalize_profession(player_data.get('profession'))
    prof_line = None
    if prof_norm:
        prof_key, prof_level, prof_xp = prof_norm
        prof_name = (game_data.PROFESSIONS_DATA or {}).get(prof_key, {}).get('display_name', prof_key)
    try:
        prof_next = int(game_data.get_xp_for_next_collection_level(prof_level))
    except Exception:
        prof_next = 0
    
    prof_bar = _bar(prof_xp, prof_next, blocks=10, filled_char='🟨', empty_char='⬜️')
    prof_line = f"💼 <b>Profissão:</b> {prof_name} — Nível {prof_level}\n<code>[{prof_bar}]</code> {prof_xp}/{prof_next} XP"

    
    class_banner = ""
    if player_manager.needs_class_choice(player_data):
        class_banner = "\n\n✨ <b>Escolha sua Classe!</b>"

    # ===== texto do perfil =====
    char_name        = player_data.get('character_name','Aventureiro(a)')
    available_points = int(player_data.get("stat_points", 0) or 0)

    lines = [
        f"👤 <b>Pᴇʀғɪʟ ᴅᴇ {char_name}</b>{premium_line}",
        f"📍 <b>𝑳𝒐𝒄𝒂𝒍𝒊𝒛𝒂𝒄̧𝒂̃𝒐 𝑨𝒕𝒖𝒂𝒍:</b> {location_name}",
        "",
        f"❤️ <b>𝐇𝐏:</b> {current_hp} / {total_hp_max}",
        f"⚡️ <b>𝐄𝐧𝐞𝐫𝐠𝐢𝐚:</b> {int(player_data.get('energy', 0))} / {max_energy}",
        "",
        f"🧡 <b>𝐇𝐏 𝐌𝐚́𝐱𝐢𝐦𝐨:</b> {total_hp_max}",
        f"⚔️ <b>𝐀𝐭𝐚𝐪𝐮𝐞:</b> {total_atk}",
        f"🛡️ <b>𝐃𝐞𝐟𝐞𝐬𝐚:</b> {total_def}",
        f"🏃 <b>𝐈𝐧𝐢𝐜𝐢𝐚𝐭𝐢𝐯𝐚:</b> {total_ini}",
        f"🍀 <b>𝐒𝐨𝐫𝐭𝐞:</b> {total_luck}",
        f"⚡️ <b>Chance de Esquiva:</b> {chance_esquiva}%",          # <-- NOVA LINHA
        f"⚔️ <b>Chance de Ataque Duplo:</b> {chance_ataque_duplo}%",
        "",
        f"🎯 <b>𝑷𝒐𝒏𝒕𝒐𝒔 𝒅𝒆 𝑨𝒕𝒓𝒊𝒃𝒖𝒕𝒐 𝒅𝒊𝒔𝒑𝒐𝒏𝒊́𝒗𝒆𝒊𝒔:</b> {available_points}",
        f"🎖️ <b>𝑵𝒊́𝒗𝒆𝒍 𝒅𝒆 𝑪𝒐𝒎𝒃𝒂𝒕𝒆:</b> {combat_level}\n<code>[{combat_bar}]</code> {combat_xp}/{combat_next} 𝐗𝐏",
    ]
    if prof_line:
        lines.append(prof_line)
    if class_banner:
        lines.append(class_banner)

    profile_text = "\n".join(lines)

    # ===== teclado =====
    keyboard = []

    # Se precisa escolher classe, põe o botão no topo
    if player_manager.needs_class_choice(player_data):
        keyboard.append([InlineKeyboardButton("✨ 𝐄𝐬𝐜𝐨𝐥𝐡𝐞𝐫 𝐂𝐥𝐚𝐬𝐬𝐞", callback_data='class_open')])

    if not prof_norm:
        keyboard.append([InlineKeyboardButton("💼 𝐄𝐬𝐜𝐨𝐥𝐡𝐞𝐫 𝐏𝐫𝐨𝐟𝐢𝐬𝐬𝐚̃𝐨", callback_data='job_menu')])

    keyboard.extend([
        # DEPOIS (versão corrigida)
        [InlineKeyboardButton("꧁𓊈𒆜🅲🅻🅰🅽𒆜𓊉꧂", callback_data='clan_menu:profile')],
        [InlineKeyboardButton("📊 𝐒𝐭𝐚𝐭𝐮𝐬 & 𝐀𝐭𝐫𝐢𝐛𝐮𝐭𝐨𝐬", callback_data='status_open')],
        [InlineKeyboardButton("🧰 𝐄𝐪𝐮𝐢𝐩𝐚𝐦𝐞𝐧𝐭𝐨𝐬", callback_data='equipment_menu')],
        [InlineKeyboardButton("🎒 𝐕𝐞𝐫 𝐈𝐧𝐯𝐞𝐧𝐭𝐚́𝐫𝐢𝐨 𝐂𝐨𝐦𝐩𝐥𝐞𝐭𝐨", callback_data='inventory_CAT_equipamento_PAGE_1')],
        [InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data='continue_after_action')],
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)

    # ===== mídia da classe (se existir) =====
# Em handlers/profile_handler.py

    # ===== mídia da classe (se existir) =====
    media = _get_class_media(player_data, "personagem")
    if media and media.get("id"):
        try:
            # Tenta deletar a mensagem antiga e enviar a nova com mídia
            await query.delete_message()

            fid  = media["id"]
            ftyp = (media.get("type") or "photo").lower()
            if ftyp == "video":
                await context.bot.send_video(chat_id=chat_id, video=fid, caption=profile_text, reply_markup=reply_markup, parse_mode="HTML")
            else:
                await context.bot.send_photo(chat_id=chat_id, photo=fid, caption=profile_text, reply_markup=reply_markup, parse_mode="HTML")
            return # Se tudo deu certo, encerra a função aqui

        except Exception as e:
            # Se qualquer coisa acima falhar, loga o erro e continua
            logger.error(f"Falha ao enviar mídia do perfil para user {user_id}: {e}")
            # A função NÃO vai parar. Ela continuará para o envio de texto abaixo.

    # Fallback: sem mídia (ou se a mídia falhou) -> edita/envia texto
    await _safe_edit_or_send(query, context, chat_id, profile_text, reply_markup=reply_markup, parse_mode='HTML')
profile_handler = CallbackQueryHandler(profile_callback, pattern=r'^(?:profile|personagem)$')
