# handlers/profile_handler.py (VERSÃO FINALÍSSIMA CORRIGIDA)

import logging
import unicodedata
import re
import json
import html
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler
from telegram.error import BadRequest
from modules.player.premium import PremiumManager
from modules import player_manager, game_data
from modules import file_ids
from modules.game_data.skins import SKIN_CATALOG
from modules.game_data import skills as skills_data
from modules.player import stats as player_stats
from modules.player import stats as player_stats
from modules.game_data.class_evolution import can_player_use_skill

logger = logging.getLogger(__name__)

MAX_EQUIPPED_SKILLS = 6

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
    # (Função original mantida - sem alterações)
    raw_cls = (player_data.get("class") or player_data.get("class_tag") or "").strip()
    cls = _slugify(raw_cls)
    purpose = (purpose or "").strip().lower()
    candidates = []
    equipped_skin_id = player_data.get("equipped_skin")
    if equipped_skin_id and equipped_skin_id in SKIN_CATALOG:
        skin_info = SKIN_CATALOG[equipped_skin_id]
        if skin_info.get('class') == raw_cls or skin_info.get('class') == cls:
            candidates.append(skin_info['media_key'])
    classes_data = getattr(game_data, "CLASSES_DATA", {}) or {}
    cls_cfg = classes_data.get(raw_cls) or classes_data.get(cls) or {}
    for k in ("profile_file_id_key", "profile_media_key", "file_id_name", "status_file_id_key", "file_id_key"):
        if cls_cfg and cls_cfg.get(k):
            candidates.append(cls_cfg[k])
    if cls:
        candidates += [
            f"classe_{cls}_media", f"class_{cls}_media", f"{cls}_media",
            f"perfil_video_{cls}", f"personagem_video_{cls}", f"profile_video_{cls}",
            f"{purpose}_video_{cls}", f"{purpose}_{cls}",
            f"{cls}_{purpose}_video", f"{cls}_{purpose}",
        ]
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

async def show_skills_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await _safe_edit_or_send(query, context, chat_id, "Erro: Personagem não encontrado.")
        return
    
    # --- !!! 2. CORREÇÃO DA CLASSE !!! ---
    # Pega a classe normalizada (ex: "arcanista")
    player_class_key = player_stats._get_class_key_normalized(player_data)
    
    player_skill_ids = player_data.get("skills", [])
    if not player_skill_ids:
        text = "📚 <b>Suas Habilidades</b>\n\nVocê ainda não aprendeu nenhuma habilidade."
        kb = [[InlineKeyboardButton("⬅️ Voltar ao Perfil", callback_data="profile")]]
        await _safe_edit_or_send(query, context, chat_id, text, InlineKeyboardMarkup(kb))
        return

    active_skills_lines = []
    passive_skills_lines = []
    
    for skill_id in player_skill_ids:
        skill_info = skills_data.SKILL_DATA.get(skill_id)
        if not skill_info:
            logger.warning(f"Skill ID '{skill_id}' encontrado em {user_id} mas não existe em SKILL_DATA.")
            continue
            
        # --- !!! 3. CORREÇÃO DA VERIFICAÇÃO !!! ---
        # Verifica se a classe atual (ou a base) pode usar esta skill
        allowed_classes = skill_info.get("allowed_classes", [])
        if not can_player_use_skill(player_class_key, allowed_classes):
            continue # Pula esta skill, o jogador não pode mais usá-la
            
        name = skill_info.get("display_name", skill_id)
        desc = skill_info.get("description", "Sem descrição.")
        mana_cost = skill_info.get("mana_cost")
        skill_type = skill_info.get("type", "unknown")
        line = f"• <b>{name}</b>"
        if mana_cost is not None:
            line += f" ({mana_cost} MP)"
        line += f": <i>{html.escape(desc)}</i>"
        if skill_type == "active" or skill_type.startswith("support"):
            active_skills_lines.append(line)
        elif skill_type == "passive":
            passive_skills_lines.append(line)
            
    text_parts = ["📚 <b>Suas Habilidades</b>\n"]
    if active_skills_lines:
        text_parts.append("✨ <b><u>Habilidades Ativas</u></b> ✨")
        text_parts.extend(active_skills_lines)
        text_parts.append("(Você pode equipar até 4 skills ativas para usar em combate)")
        text_parts.append("")
    if passive_skills_lines:
        text_parts.append("🛡️ <b><u>Habilidades Passivas</u></b> 🛡️")
        text_parts.extend(passive_skills_lines)
        text_parts.append("")
        
    # Se ambas as listas estiverem vazias (ex: só tinha skills de mago e evoluiu)
    if not active_skills_lines and not passive_skills_lines:
        text_parts.append("<i>Você não possui nenhuma habilidade que sua classe atual possa usar.</i>")

    kb = [[InlineKeyboardButton("⬅️ Voltar ao Perfil", callback_data="profile")]]
    if active_skills_lines:
        kb.insert(0, [InlineKeyboardButton("⚙️ Equipar Skills Ativas", callback_data="skills_equip_menu")])
    
    final_text = "\n".join(text_parts)
    reply_markup = InlineKeyboardMarkup(kb)
    await _safe_edit_or_send(query, context, chat_id, final_text, reply_markup)

async def show_equip_skills_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await _safe_edit_or_send(query, context, chat_id, "Erro: Personagem não encontrado.")
        return

    # --- !!! 4. CORREÇÃO DA CLASSE !!! ---
    # Pega a classe normalizada (ex: "arcanista")
    player_class_key = player_stats._get_class_key_normalized(player_data)
    # --- FIM DA CORREÇÃO ---

    all_skill_ids = player_data.get("skills", [])
    equipped_ids = player_data.get("equipped_skills", [])
    if not isinstance(equipped_ids, list):
        equipped_ids = []
        player_data["equipped_skills"] = equipped_ids

    active_skill_ids = []
    # Filtra as skills ativas que o jogador APRENDEU
    for skill_id in all_skill_ids:
        skill_type = skills_data.SKILL_DATA.get(skill_id, {}).get("type", "unknown")
        if skill_type == "active" or skill_type.startswith("support"):
            active_skill_ids.append(skill_id)

    if not active_skill_ids:
        text = "⚙️ Equipar Skills Ativas\n\nVocê não possui nenhuma skill ativa para equipar."
        kb = [[InlineKeyboardButton("⬅️ Voltar (Habilidades)", callback_data="skills_menu_open")]]
        await _safe_edit_or_send(query, context, chat_id, text, InlineKeyboardMarkup(kb))
        return
    
    text_parts = [f"⚙️ <b>Equipar Skills Ativas</b> (Limite: {len(equipped_ids)}/{MAX_EQUIPPED_SKILLS})\n"]
    kb_rows = []
    text_parts.append("✅ <b><u>Equipadas Atualmente</u></b> ✅")
    
    if not equipped_ids:
        text_parts.append("<i>Nenhuma skill ativa equipada.</i>")
    else:
        for skill_id in equipped_ids:
            skill_info = skills_data.SKILL_DATA.get(skill_id)
            if not skill_info: continue
            
            # --- !!! 5. CORREÇÃO DA VERIFICAÇÃO !!! ---
            # Adiciona uma verificação para o caso de uma skill equipada se tornar inválida
            allowed_classes = skill_info.get("allowed_classes", [])
            if not can_player_use_skill(player_class_key, allowed_classes):
                # A skill está equipada mas não devia! (Não mostra, mas oferece desequipar)
                name = skill_info.get("display_name", skill_id)
                text_parts.append(f"• <s><b>{name}</b> (Classe Inválida)</s>")
            else:
                name = skill_info.get("display_name", skill_id)
                mana_cost = skill_info.get("mana_cost")
                line = f"• <b>{name}</b>"
                if mana_cost is not None: line += f" ({mana_cost} MP)"
                text_parts.append(line)
            
            kb_rows.append([InlineKeyboardButton(f"➖ Desequipar {name}", callback_data=f"unequip_skill:{skill_id}")])

    text_parts.append("\n" + ("─" * 20) + "\n")
    text_parts.append("➕ <b><u>Disponíveis para Equipar</u></b> ➕")
    
    slots_free = MAX_EQUIPPED_SKILLS - len(equipped_ids)
    available_to_equip_found = False

    for skill_id in active_skill_ids:
        if skill_id not in equipped_ids:
            skill_info = skills_data.SKILL_DATA.get(skill_id)
            if not skill_info: continue

            # --- !!! 6. CORREÇÃO DA VERIFICAÇÃO !!! ---
            allowed_classes = skill_info.get("allowed_classes", [])
            if not can_player_use_skill(player_class_key, allowed_classes):
                continue # ...pula esta skill, nem mostra o botão.
            # --- FIM DA CORREÇÃO ---

            available_to_equip_found = True
            name = skill_info.get("display_name", skill_id)
            mana_cost = skill_info.get("mana_cost")
            line = f"• <b>{name}</b>"
            if mana_cost is not None: line += f" ({mana_cost} MP)"
            text_parts.append(line)
            
            if slots_free > 0:
                kb_rows.append([InlineKeyboardButton(f"➕ Equipar {name}", callback_data=f"equip_skill:{skill_id}")])
            else:
                kb_rows.append([InlineKeyboardButton(f"🚫 Limite Atingido", callback_data="noop")])

    if not available_to_equip_found:
        text_parts.append("<i>Não há outras skills ativas disponíveis (ou que a sua classe possa usar).</i>")
    
    kb_rows.append([InlineKeyboardButton("⬅️ Voltar (Habilidades)", callback_data="skills_menu_open")])
    final_text = "\n".join(text_parts)
    reply_markup = InlineKeyboardMarkup(kb_rows)
    await _safe_edit_or_send(query, context, chat_id, final_text, reply_markup)

async def equip_skill_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try:
        skill_id = query.data.split(":", 1)[1]
    except IndexError:
        logger.error(f"Callback equip_skill inválido: {query.data}")
        await query.answer("Erro ao processar a ação.", show_alert=True)
        return

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await query.answer("Erro: Personagem não encontrado.", show_alert=True)
        return

    skill_info = skills_data.SKILL_DATA.get(skill_id)
    if not skill_info:
        await query.answer("Erro: Skill não encontrada nos dados do jogo.", show_alert=True)
        return

    # --- !!! 7. CORREÇÃO DA VERIFICAÇÃO !!! ---
    # Pega a classe normalizada (ex: "arcanista")
    player_class_key = player_stats._get_class_key_normalized(player_data)
    allowed_classes = skill_info.get("allowed_classes", [])
    
    if not can_player_use_skill(player_class_key, allowed_classes):
        await query.answer("Sua classe (ou classe base) não pode equipar esta habilidade!", show_alert=True)
        await show_equip_skills_menu(update, context) # Recarrega o menu
        return
    # --- FIM DA CORREÇÃO ---

    equipped_skills = player_data.setdefault("equipped_skills", [])
    if not isinstance(equipped_skills, list):
        equipped_skills = []
        player_data["equipped_skills"] = equipped_skills
    
    if skill_id in equipped_skills:
        await query.answer("Essa skill já está equipada.", show_alert=True)
        await show_equip_skills_menu(update, context)
        return
    
    if len(equipped_skills) >= MAX_EQUIPPED_SKILLS:
        await query.answer(f"Limite de {MAX_EQUIPPED_SKILLS} skills equipadas atingido!", show_alert=True)
        await show_equip_skills_menu(update, context)
        return
    
    equipped_skills.append(skill_id)
    await player_manager.save_player_data(user_id, player_data)
    
    await show_equip_skills_menu(update, context)

async def unequip_skill_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    try:
        skill_id = query.data.split(":", 1)[1]
    except IndexError:
        logger.error(f"Callback unequip_skill inválido: {query.data}")
        await query.answer("Erro ao processar a ação.", show_alert=True)
        return
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await query.answer("Erro: Personagem não encontrado.", show_alert=True)
        return
    equipped_skills = player_data.get("equipped_skills", [])
    if not isinstance(equipped_skills, list):
        equipped_skills = []
        player_data["equipped_skills"] = equipped_skills
    if skill_id in equipped_skills:
        equipped_skills.remove(skill_id)
        await player_manager.save_player_data(user_id, player_data)
    else:
        await query.answer("Essa skill não estava equipada.", show_alert=True)
    await show_equip_skills_menu(update, context)

async def noop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Limite de skills equipadas atingido!")

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except Exception:
        pass
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except Exception:
        pass
    try:
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        logger.error(f"Falha ao enviar mensagem em _safe_edit_or_send: {e}")

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
    """
    Função unificada para lidar com /personagem (comando) e 'profile' (botão).
    """
    query = update.callback_query
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if query:
        await query.answer()

    player_data = await player_manager.get_player_data(user_id)

    if not player_data:
        text = "Erro: Personagem não encontrado. Use /start para começar."
        if query:
            await _safe_edit_or_send(query, context, chat_id, text)
        else:
            await context.bot.send_message(chat_id, text)
        return
    
    # ===== totais (base + equipamentos) =====

    totals = await player_manager.get_player_total_stats(player_data)
    
    total_hp_max = int(totals.get('max_hp', 50))
    total_atk = int(totals.get('attack', 0))
    total_def = int(totals.get('defense', 0))
    total_ini = int(totals.get('initiative', 0))
    total_luck = int(totals.get('luck', 0))
    # --- ADICIONADO MANA ---
    total_mp_max = int(totals.get('max_mana', 10)) # Puxa o Mana Máximo

    current_hp = max(0, min(int(player_data.get('current_hp', total_hp_max)), total_hp_max))
    # --- ADICIONADO MANA ---
    current_mp = max(0, min(int(player_data.get('current_mp', total_mp_max)), total_mp_max))
    
    # <<< CORREÇÃO 1: Adiciona await AQUI >>>
    chance_esquiva = int((await player_manager.get_player_dodge_chance(player_data)) * 100)
    # <<< CORREÇÃO 2: Adiciona await AQUI >>>
    chance_ataque_duplo = int((await player_manager.get_player_double_attack_chance(player_data)) * 100)

    location_key = player_data.get('current_location', 'reino_eldora')
    location_name = (game_data.REGIONS_DATA or {}).get(location_key, {}).get('display_name', 'Lugar Desconhecido')

    # ===== BLOCO PREMIUM =====
    premium_line = ""
    premium = PremiumManager(player_data)
    if premium.is_premium():
        tier_name = premium.tier.capitalize() if premium.tier else "Premium"
        exp_date = premium.expiration_date
        premium_line = f"\n👑 <b>Status Premium:</b> {tier_name}"
        if exp_date:
            premium_line += f"\n(Expira em: {exp_date.strftime('%d/%m/%Y')})"
        else:
            premium_line += " (Permanente)"
    
    # ===== XP, Profissão, Classe =====
    # <<< CORREÇÃO 3: Remove await AQUI >>>
    max_energy  = int(player_manager.get_player_max_energy(player_data))
    combat_level = int(player_data.get('level', 1))
    combat_xp = int(player_data.get('xp', 0))
    try:
        combat_next = int(game_data.get_xp_for_next_combat_level(combat_level))
    except Exception:
        combat_next = 0
    combat_bar = _bar(combat_xp, combat_next)

    prof_line = "" 
    prof_norm = _normalize_profession(player_data.get('profession'))
    if prof_norm:
        prof_key, prof_level, prof_xp = prof_norm
        prof_name = (game_data.PROFESSIONS_DATA or {}).get(prof_key, {}).get('display_name', prof_key)
        try:
            prof_next = int(game_data.get_xp_for_next_collection_level(prof_level))
        except Exception:
            prof_next = 0
        prof_bar = _bar(prof_xp, prof_next, blocks=10, filled_char='🟨', empty_char='⬜️')
        prof_line = f"\n💼 <b>Profissão:</b> {prof_name} — Nível {prof_level}\n<code>[{prof_bar}]</code> {prof_xp}/{prof_next} XP"
    
    class_banner = ""
    if player_manager.needs_class_choice(player_data):
        class_banner = "\n\n✨ <b>Escolha sua Classe!</b>"

    current_class_key = (player_data.get("class") or "no_class").lower()
    class_config = (game_data.CLASSES_DATA or {}).get(current_class_key, {})
    class_name = class_config.get("display_name", current_class_key.title())
    class_emoji = class_config.get("emoji", "👤")

    # ===== texto do perfil =====
    char_name = player_data.get('character_name','Aventureiro(a)')
    available_points = int(player_data.get("stat_points", 0) or 0)

    lines = [
        f"👤 <b>Pᴇʀғɪʟ ᴅᴇ {char_name}</b>{premium_line}",
        f"{class_emoji} <b>Classe:</b> {class_name}", 
        f"📍 <b>𝑳𝒐𝒄𝒂𝒍𝒊𝒛𝒂𝒄̧𝒂̃𝒐 𝑨𝒕𝒖𝒂𝒍:</b> {location_name}",
        "",
        f"❤️ <b>𝐇𝐏:</b> {current_hp} / {total_hp_max}",
        f"💙 <b>𝐌𝐚𝐧𝐚:</b> {current_mp} / {total_mp_max}",
        f"⚡️ <b>𝐄𝐧𝐞𝐫𝐠𝐢𝐚:</b> {int(player_data.get('energy', 0))} / {max_energy}",
        "",
        f"🧡 <b>𝐇𝐏 𝐌𝐚́𝐱𝐢𝐦𝐨:</b> {total_hp_max}",
        f"⚔️ <b>𝐀𝐭𝐚𝐪𝐮𝐞:</b> {total_atk}",
        f"🛡️ <b>𝐃𝐞𝐟𝐞𝐬𝐚:</b> {total_def}",
        f"🏃 <b>𝐈𝐧𝐢𝐜𝐢𝐚𝐭𝐢𝐯𝐚:</b> {total_ini}",
        f"🍀 <b>𝐒𝐨𝐫𝐭𝐞:</b> {total_luck}",
        f"⚡️ <b>Chance de Esquiva:</b> {chance_esquiva}%",
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
    if player_manager.needs_class_choice(player_data):
        keyboard.append([InlineKeyboardButton("✨ 𝐄𝐬𝐜𝐨𝐥𝐡𝐞𝐫 𝐂𝐥𝐚𝐬𝐬𝐞", callback_data='class_open')])
    if not prof_norm:
        keyboard.append([InlineKeyboardButton("💼 𝐄𝐬𝐜𝐨𝐥𝐡𝐞𝐫 𝐏𝐫𝐨𝐟𝐢𝐬𝐬𝐚̃𝐨", callback_data='job_menu')])

    keyboard.extend([
        [InlineKeyboardButton("🔰⚜️𝐂𝐋𝐀𝐍⚜️🔰", callback_data='clan_menu:profile')],
        [InlineKeyboardButton("📊 𝐒𝐭𝐚𝐭𝐮𝐬 & 𝐀𝐭𝐫𝐢𝐛𝐮𝐭𝐨𝐬 📊", callback_data='status_open')],
        [InlineKeyboardButton("🧰 𝐄𝐪𝐮𝐢𝐩𝐚𝐦𝐞𝐧𝐭𝐨𝐬 🧰", callback_data='equipment_menu')],
        [InlineKeyboardButton("🎒 𝐕𝐞𝐫 𝐈𝐧𝐯𝐞𝐧𝐭𝐚́𝐫𝐢𝐨 𝐂𝐨𝐦𝐩𝐥𝐞𝐭𝐨 🎒", callback_data='inventory_CAT_equipamento_PAGE_1')],
        [InlineKeyboardButton("🧪 𝐔𝐬𝐚𝐫 𝐂𝐨𝐧𝐬𝐮𝐦𝐢́𝐯𝐞𝐥 🧪", callback_data='inventory_CAT_consumivel_PAGE_1')],
        [InlineKeyboardButton("📚 𝐇𝐚𝐛𝐢𝐥𝐢𝐝𝐚𝐝𝐞𝐬 📚", callback_data='skills_menu_open')],
        [InlineKeyboardButton("🎨 𝐌𝐮𝐝𝐚𝐫 𝐀𝐩𝐚𝐫𝐞̂𝐧𝐜𝐢𝐚 🎨", callback_data='skin_menu')],
        [InlineKeyboardButton("🔄 𝐂𝐨𝐧𝐯𝐞𝐫𝐭𝐞𝐫 𝐑𝐞𝐜𝐨𝐦𝐩𝐞𝐧𝐬𝐚𝐬 🔄", callback_data='conv:main')],
        [InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫 ⬅️", callback_data='continue_after_action')],
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)

    # ===== mídia da classe =====
    media = _get_class_media(player_data, "personagem")
    if media and media.get("id"):
        try:
            if query:
                await query.delete_message()
            fid  = media["id"]
            ftyp = (media.get("type") or "photo").lower()
            if ftyp == "video":
                await context.bot.send_video(chat_id=chat_id, video=fid, caption=profile_text, reply_markup=reply_markup, parse_mode="HTML")
            else:
                await context.bot.send_photo(chat_id=chat_id, photo=fid, caption=profile_text, reply_markup=reply_markup, parse_mode="HTML")
            return 
        except Exception as e:
            logger.error(f"Falha ao enviar mídia do perfil para user {user_id}: {e}")

    # Fallback: sem mídia
    if query:
        await _safe_edit_or_send(query, context, chat_id, profile_text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        # Se veio de um comando (/personagem), envia uma nova mensagem
        await context.bot.send_message(chat_id=chat_id, text=profile_text, reply_markup=reply_markup, parse_mode="HTML")

# ====================================================================
# <<< INÍCIO DAS EXPORTAÇÕES DE HANDLER (O QUE FALTAVA) >>>
# ====================================================================

# O handler para o comando /personagem
character_command_handler = CommandHandler("personagem", profile_callback)

# O handler para o botão 'profile' (ex: "Voltar ao Perfil")
profile_handler = CallbackQueryHandler(profile_callback, pattern=r'^(?:profile|personagem)$')

# Handlers para os sub-menus de skills (que estão neste ficheiro)
skills_menu_handler = CallbackQueryHandler(show_skills_menu, pattern=r'^skills_menu_open$')
skills_equip_menu_handler = CallbackQueryHandler(show_equip_skills_menu, pattern=r'^skills_equip_menu$')
equip_skill_handler = CallbackQueryHandler(equip_skill_callback, pattern=r'^equip_skill:')
unequip_skill_handler = CallbackQueryHandler(unequip_skill_callback, pattern=r'^unequip_skill:')
noop_handler = CallbackQueryHandler(noop_callback, pattern=r'^noop$')