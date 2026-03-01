# handlers/profile_handler.py
# (VERSÃO FINAL: AUTH UNIFICADA + ID SEGURO)

import logging
import unicodedata
import re
import html
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler
from modules.player.premium import PremiumManager
from modules import player_manager, game_data
from modules import file_ids
from modules.game_data.skins import SKIN_CATALOG
from modules.game_data import skills as skills_data
from modules.player import stats as player_stats
from modules.game_data.class_evolution import can_player_use_skill
from modules.auth_utils import get_current_player_id  # <--- ÚNICA FONTE DE VERDADE

# Import para correção de energia
from modules.player import actions as player_actions

logger = logging.getLogger(__name__)

MAX_EQUIPPED_SKILLS = 6

# ===== util =====
def _slugify(text: str) -> str:
    if not text: return ""
    norm = unicodedata.normalize("NFKD", text)
    norm = norm.encode("ascii", "ignore").decode("ascii")
    norm = re.sub(r"\s+", "_", norm.strip().lower())
    norm = re.sub(r"[^a-z0-9_]", "", norm)
    return norm

def _get_class_media(player_data: dict, purpose: str = "personagem"):
    raw_cls = (player_data.get("class") or player_data.get("class_tag") or "").strip()
    cls = _slugify(raw_cls)
    try:
        player_base_class = player_stats._get_class_key_normalized(player_data)
    except Exception:
        player_base_class = cls

    purpose = (purpose or "").strip().lower()
    candidates = []
    equipped_skin_id = player_data.get("equipped_skin")

    if equipped_skin_id and equipped_skin_id in SKIN_CATALOG:
        skin_info = SKIN_CATALOG[equipped_skin_id]
        if skin_info.get('class') == player_base_class:
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
    
    for key in [k for k in candidates if k and "abertura" not in k.lower()]:
        fd = file_ids.get_file_data(key)
        if fd and fd.get("id"):
            return fd
    return None

def _bar(current: int, total: int, blocks: int = 10, filled_char: str = '🟧', empty_char: str = '⬜️') -> str:
    if total <= 0: filled = blocks
    else:
        ratio = max(0.0, min(1.0, float(current) / float(total)))
        filled = int(round(ratio * blocks))
    return filled_char * filled + empty_char * (blocks - filled)

def _normalize_profession(raw):
    if not raw: return None
    if isinstance(raw, str): return (raw, 1, 0)
    if isinstance(raw, dict):
        if 'type' in raw: return (raw.get('type'), int(raw.get('level', 1)), int(raw.get('xp', 0)))
        for k, v in raw.items():
            if isinstance(v, dict): return (k, int(v.get('level', 1)), int(v.get('xp', 0)))
            return (k, 1, 0)
    return None

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except Exception: pass
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except Exception: pass
    try:
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e: logger.error(f"Falha ao enviar mensagem: {e}")

# ====================================================================
# MENUS DE SKILLS
# ====================================================================
async def show_skills_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # 🔒 SEGURANÇA: ID via Auth Central
    user_id = get_current_player_id(update, context)
    chat_id = query.message.chat.id
    
    if not user_id:
        await _safe_edit_or_send(query, context, chat_id, "Sessão inválida. Use /start.")
        return

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await _safe_edit_or_send(query, context, chat_id, "Erro: Personagem não encontrado.")
        return
    
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
        if not skill_info: continue
        allowed_classes = skill_info.get("allowed_classes", [])
        if not can_player_use_skill(player_class_key, allowed_classes): continue 
            
        name = skill_info.get("display_name", skill_id)
        desc = skill_info.get("description", "Sem descrição.")
        mana_cost = skill_info.get("mana_cost")
        skill_type = skill_info.get("type", "unknown")
        line = f"• <b>{name}</b>"
        if mana_cost is not None: line += f" ({mana_cost} MP)"
        line += f": <i>{html.escape(desc)}</i>"
        
        if skill_type == "active" or skill_type.startswith("support"):
            active_skills_lines.append(line)
        elif skill_type == "passive":
            passive_skills_lines.append(line)
            
    text_parts = ["📚 <b>GRIMOIRE DE HABILIDADES</b>\n"]
    if active_skills_lines:
        text_parts.append("✨ <b><u>Ativas & Suporte</u></b>")
        text_parts.extend(active_skills_lines)
        text_parts.append("")
    if passive_skills_lines:
        text_parts.append("🛡️ <b><u>Passivas</u></b>")
        text_parts.extend(passive_skills_lines)
        text_parts.append("")
        
    kb = [[InlineKeyboardButton("⬅️ Voltar ao Perfil", callback_data="profile")]]
    if active_skills_lines:
        kb.insert(0, [InlineKeyboardButton("⚙️ Equipar Skills Ativas", callback_data="skills_equip_menu")])
    
    final_text = "\n".join(text_parts)
    await _safe_edit_or_send(query, context, chat_id, final_text, InlineKeyboardMarkup(kb))

async def show_equip_skills_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # 🔒 SEGURANÇA: ID via Auth Central
    user_id = get_current_player_id(update, context)
    chat_id = query.message.chat.id
    
    if not user_id:
        await _safe_edit_or_send(query, context, chat_id, "Sessão inválida.")
        return

    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return

    player_class_key = player_stats._get_class_key_normalized(player_data)
    all_skill_ids = player_data.get("skills", [])
    equipped_ids = player_data.get("equipped_skills", [])
    if not isinstance(equipped_ids, list):
        equipped_ids = []
        player_data["equipped_skills"] = equipped_ids

    active_skill_ids = []
    for skill_id in all_skill_ids:
        skill_type = skills_data.SKILL_DATA.get(skill_id, {}).get("type", "unknown")
        if skill_type == "active" or skill_type.startswith("support"):
            active_skill_ids.append(skill_id)

    if not active_skill_ids:
        text = "⚙️ Equipar Skills\n\nVocê não possui skills ativas."
        kb = [[InlineKeyboardButton("⬅️ Voltar", callback_data="skills_menu_open")]]
        await _safe_edit_or_send(query, context, chat_id, text, InlineKeyboardMarkup(kb))
        return
    
    text_parts = [f"⚙️ <b>EQUIPAR SKILLS</b> (Slots: {len(equipped_ids)}/{MAX_EQUIPPED_SKILLS})\n"]
    kb_rows = []
    
    # Equipadas
    text_parts.append("✅ <b><u>Em Uso</u></b>")
    if not equipped_ids:
        text_parts.append("<i>Nenhuma.</i>")
    else:
        for skill_id in equipped_ids:
            skill_info = skills_data.SKILL_DATA.get(skill_id)
            if not skill_info: continue
            name = skill_info.get("display_name", skill_id)
            kb_rows.append([InlineKeyboardButton(f"➖ Remover {name}", callback_data=f"unequip_skill:{skill_id}")])
            text_parts.append(f"• <b>{name}</b>")

    text_parts.append("\n➕ <b><u>Disponíveis</u></b>")
    slots_free = MAX_EQUIPPED_SKILLS - len(equipped_ids)
    
    for skill_id in active_skill_ids:
        if skill_id not in equipped_ids:
            skill_info = skills_data.SKILL_DATA.get(skill_id)
            if not skill_info: continue
            allowed_classes = skill_info.get("allowed_classes", [])
            if not can_player_use_skill(player_class_key, allowed_classes): continue 

            name = skill_info.get("display_name", skill_id)
            text_parts.append(f"• {name}")
            if slots_free > 0:
                kb_rows.append([InlineKeyboardButton(f"➕ Equipar {name}", callback_data=f"equip_skill:{skill_id}")])
            else:
                kb_rows.append([InlineKeyboardButton(f"🚫 {name} (Slot Cheio)", callback_data="noop")])

    kb_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="skills_menu_open")])
    await _safe_edit_or_send(query, context, chat_id, "\n".join(text_parts), InlineKeyboardMarkup(kb_rows))

async def equip_skill_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # 🔒 SEGURANÇA
    user_id = get_current_player_id(update, context)
    if not user_id:
        return

    try: skill_id = query.data.split(":", 1)[1]
    except IndexError: return

    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return

    equipped = player_data.setdefault("equipped_skills", [])
    if len(equipped) >= MAX_EQUIPPED_SKILLS:
        await query.answer("Limite de skills atingido!", show_alert=True)
        return
    
    if skill_id not in equipped:
        equipped.append(skill_id)
        await player_manager.save_player_data(user_id, player_data)
    
    await show_equip_skills_menu(update, context)

async def unequip_skill_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # 🔒 SEGURANÇA
    user_id = get_current_player_id(update, context)
    if not user_id:
        return

    try: skill_id = query.data.split(":", 1)[1]
    except IndexError: return
    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return
    equipped = player_data.setdefault("equipped_skills", [])
    if skill_id in equipped:
        equipped.remove(skill_id)
        await player_manager.save_player_data(user_id, player_data)
    await show_equip_skills_menu(update, context)

async def noop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Ação indisponível.", show_alert=True)

# ====================================================================
# PERFIL PRINCIPAL (AQUI ESTÁ A MUDANÇA)
# ====================================================================
async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # 🔒 SEGURANÇA: ID via Auth Central
    user_id = get_current_player_id(update, context)
    chat_id = update.effective_chat.id
    
    if query: await query.answer()

    if not user_id:
        # Fallback se não identificar
        text = "Sessão inválida. Digite /start."
        if query: await _safe_edit_or_send(query, context, chat_id, text)
        else: await context.bot.send_message(chat_id, text)
        return

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        text = "Erro: Personagem não encontrado. Use /start para começar."
        if query: await _safe_edit_or_send(query, context, chat_id, text)
        else: await context.bot.send_message(chat_id, text)
        return
    
    # Atualiza energia visual
    try: player_actions._apply_energy_autoregen_inplace(player_data)
    except: pass
    
    # Stats Totais
    totals = await player_manager.get_player_total_stats(player_data)
    
    max_hp = int(totals.get('max_hp', 50))
    max_mp = int(totals.get('max_mana', 10))
    atk = int(totals.get('attack', 0))
    defense = int(totals.get('defense', 0))
    ini = int(totals.get('initiative', 0))
    luck = int(totals.get('luck', 0))
    
    cur_hp = max(0, min(int(player_data.get('current_hp', max_hp)), max_hp))
    cur_mp = max(0, min(int(player_data.get('current_mp', max_mp)), max_mp))
    cur_energy = int(player_data.get('energy', 0))
    max_energy = int(player_manager.get_player_max_energy(player_data))

    dodge = int((await player_manager.get_player_dodge_chance(player_data)) * 100)
    double_atk = int((await player_manager.get_player_double_attack_chance(player_data)) * 100)

    # Info Básica
    # Info Básica - Correção: Garantir que char_name nunca é None
    char_name = (
        player_data.get("character_name") or 
        player_data.get("name") or 
        (update.effective_user.first_name if update and update.effective_user else "Aventureiro")
    )
    loc_key = player_data.get('current_location', 'reino_eldora')
    loc_name = (game_data.REGIONS_DATA or {}).get(loc_key, {}).get('display_name', 'Desconhecido')
    
    cls_key = (player_data.get("class") or "no_class").lower()
    cls_cfg = (game_data.CLASSES_DATA or {}).get(cls_key, {})
    cls_name = cls_cfg.get("display_name", cls_key.title())
    cls_emoji = cls_cfg.get("emoji", "👤")

    # --- MUDANÇA DE NOME: PREMIUM -> BÊNÇÃO ---
    premium_txt = ""
    raw_tier = player_data.get("premium_tier")
    
    # Verifica se existe tier e se não é "free"
    if raw_tier and str(raw_tier).lower() not in ("free", "none"):
        exp = player_data.get("premium_expires_at")
        date_str = "Permanente"
        
        # Tenta formatar a data se ela existir
        if exp:
            try:
                # Suporta formato ISO com ou sem timezone
                dt = datetime.fromisoformat(str(exp))
                date_str = dt.strftime('%d/%m/%Y')
                
                # Opcional: Avisar se venceu
                if dt.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
                     date_str = f"{date_str} (Vencido)"
            except Exception: 
                pass
                
        # Monta o texto
        premium_txt = f"\n✨ <b>Bênção:</b> {raw_tier.upper()} <code>({date_str})</code>"
        
    # Progressão (Nível e Profissão)
    lvl = int(player_data.get('level', 1))
    xp = int(player_data.get('xp', 0))
    try: next_xp = int(game_data.get_xp_for_next_combat_level(lvl))
    except: next_xp = 0
    xp_bar = _bar(xp, next_xp)

    prof_block = ""
    prof_norm = _normalize_profession(player_data.get('profession'))
    if prof_norm:
        p_key, p_lvl, p_xp = prof_norm
        p_name = (game_data.PROFESSIONS_DATA or {}).get(p_key, {}).get('display_name', p_key)
        try: p_next = int(game_data.get_xp_for_next_collection_level(p_lvl))
        except: p_next = 0
        p_bar = _bar(p_xp, p_next, blocks=8, filled_char='🟨', empty_char='⬜️')
        prof_block = (
            f"\n💼 <b>Profissão:</b> {p_name} <code>Nv.{p_lvl}</code>\n"
            f" ╰┈➤ <code>[{p_bar}]</code> {p_xp}/{p_next}"
        )

    pts = int(player_data.get("stat_points", 0) or 0)
    
    # MONTAGEM DO LAYOUT (ESTILO HUD MODERNO + SETAS)
    text = (
        f"👤 <b>PERFIL DE {char_name.upper()}</b>{premium_txt}\n"
        f"──────────────────────\n"
        f"🛡 <b>Classe:</b> {cls_emoji} {cls_name}\n"
        f"📍 <b>Local:</b> {loc_name}\n\n"
        
        f"📊 <b>BARRAS VITAIS</b>\n"
        f"├─ ❤️ <b>HP.....</b> <code>{cur_hp}/{max_hp}</code>\n"
        f"├─ 💙 <b>MP.....</b> <code>{cur_mp}/{max_mp}</code>\n"
        f"└─ ⚡️ <b>ENE....</b> <code>{cur_energy}/{max_energy}</code>\n\n"

        f"⚔️ <b>ATRIBUTOS DE COMBATE</b>\n"
        f"├─ ⚔️ <b>ATK....</b> <code>{atk}</code>\n"
        f"├─ 🛡 <b>DEF....</b> <code>{defense}</code>\n"
        f"├─ 🏃 <b>INI....</b> <code>{ini}</code>\n"
        f"└─ 🍀 <b>LUK....</b> <code>{luck}</code>\n\n"
        
        f"🎲 <b>CHANCES SECUNDÁRIAS</b>\n"
        f" ╰┈➤ 💨 Esquiva: <code>{dodge}%</code>\n"
        f" ╰┈➤ ⚔️ Atk Duplo: <code>{double_atk}%</code>\n\n"
        
        f"🎖 <b>PROGRESSÃO</b>\n"
        f" ╰┈➤ 🎯 Pontos Livres: <code>{pts}</code>\n"
        f" ╰┈➤ ⚔️ Nível {lvl} <code>\n"
        f" ╰┈➤[{xp_bar}]</code> {xp}/{next_xp}"
        f"{prof_block}"
    )
    
    if player_manager.needs_class_choice(player_data):
        text += "\n\n⚠️ <b>AÇÃO NECESSÁRIA:</b> Escolha sua classe!"

    # --- TECLADO ---
    keyboard = []
    if player_manager.needs_class_choice(player_data):
        keyboard.append([InlineKeyboardButton("✨ 𝐄𝐬𝐜𝐨𝐥𝐡𝐞𝐫 𝐂𝐥𝐚𝐬𝐬𝐞", callback_data='class_open')])
    if not prof_norm:
        keyboard.append([InlineKeyboardButton("💼 𝐄𝐬𝐜𝐨𝐥𝐡𝐞𝐫 𝐏𝐫𝐨𝐟𝐢𝐬𝐬𝐚̃𝐨", callback_data='job_menu')])

    back_cb = "back_to_kingdom" if loc_key == "reino_eldora" else f"open_region:{loc_key}"

    keyboard.extend([
        [InlineKeyboardButton("🏰 𝐆𝐮𝐢𝐥𝐝𝐚", callback_data='adventurer_guild_main')],
        [InlineKeyboardButton("📊 𝐒𝐭𝐚𝐭𝐮𝐬", callback_data='status_open'), InlineKeyboardButton("🧰 𝐄𝐪𝐮𝐢𝐩𝐬", callback_data='equipment_menu')],
        [InlineKeyboardButton("🎒 𝐈𝐧𝐯𝐞𝐧𝐭𝐚́𝐫𝐢𝐨", callback_data='inventory_menu'), InlineKeyboardButton("📚 𝐒𝐤𝐢𝐥𝐥𝐬", callback_data='skills_menu_open')],
        [InlineKeyboardButton("💼 𝐏𝐫𝐨𝐟𝐢𝐬𝐬𝐚̃𝐨", callback_data="job_menu"), InlineKeyboardButton("🎨 𝐒𝐤𝐢𝐧𝐬", callback_data='skin_menu')],
        [InlineKeyboardButton("🔄 𝐂𝐨𝐧𝐯𝐞𝐫𝐭𝐞𝐫 𝐑𝐞𝐜𝐨𝐦𝐩𝐞𝐧𝐬𝐚𝐬 🔄", callback_data='conv:main')],
        [InlineKeyboardButton("❌ SAIR DA CONTA", callback_data="logout_btn"), InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data=back_cb)],
        
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    media = _get_class_media(player_data, "personagem")

    if query:
        try: await query.delete_message()
        except: pass

    if media and media.get("id"):
        try:
            fid = media["id"]
            ftyp = (media.get("type") or "photo").lower()
            send_func = context.bot.send_video if ftyp == "video" else context.bot.send_photo
            kw = {"video": fid} if ftyp == "video" else {"photo": fid}
            await send_func(chat_id=chat_id, caption=text, reply_markup=reply_markup, parse_mode="HTML", **kw)
            return
        except Exception as e:
            logger.error(f"Erro mídia perfil: {e}")

    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="HTML")

# ====================================================================
# EXPORTAÇÕES
# ====================================================================
character_command_handler = CommandHandler("personagem", profile_callback)
profile_handler = CallbackQueryHandler(profile_callback, pattern=r'^(?:profile|personagem)$')
skills_menu_handler = CallbackQueryHandler(show_skills_menu, pattern=r'^skills_menu_open$')
skills_equip_menu_handler = CallbackQueryHandler(show_equip_skills_menu, pattern=r'^skills_equip_menu$')
equip_skill_handler = CallbackQueryHandler(equip_skill_callback, pattern=r'^equip_skill:')
unequip_skill_handler = CallbackQueryHandler(unequip_skill_callback, pattern=r'^unequip_skill:')
noop_handler = CallbackQueryHandler(noop_callback, pattern=r'^noop$')