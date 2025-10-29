# handlers/profile_handler.py

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

logger = logging.getLogger(__name__)

MAX_EQUIPPED_SKILLS = 4

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
    Encontra mídia para a classe do jogador, dando prioridade à skin equipada.
    """
    raw_cls = (player_data.get("class") or player_data.get("class_tag") or "").strip()
    cls = _slugify(raw_cls)
    purpose = (purpose or "").strip().lower()

    candidates = []
    
    # --- LÓGICA DE SKIN ---
    # 1. Primeiro, tenta encontrar a media_key da skin equipada
    equipped_skin_id = player_data.get("equipped_skin")
    if equipped_skin_id and equipped_skin_id in SKIN_CATALOG:
        skin_info = SKIN_CATALOG[equipped_skin_id]
        # Garante que a skin pertence à classe do jogador
        if skin_info.get('class') == raw_cls or skin_info.get('class') == cls:
             candidates.append(skin_info['media_key'])
    # --- FIM DA LÓGICA DE SKIN ---
            
    # 2) Se não encontrar skin, continua com a lógica original de procurar a mídia padrão
    classes_data = getattr(game_data, "CLASSES_DATA", {}) or {}
    cls_cfg = classes_data.get(raw_cls) or classes_data.get(cls) or {}
    for k in ("profile_file_id_key", "profile_media_key", "file_id_name", "status_file_id_key", "file_id_key"):
        if cls_cfg and cls_cfg.get(k):
            candidates.append(cls_cfg[k])

    # 3) Padrões por classe
    if cls:
        candidates += [
            f"classe_{cls}_media",
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

    # 4) Fallbacks genéricos
    candidates += ["perfil_video", "personagem_video", "profile_video", "perfil_foto", "profile_photo"]

    # 5) Procura pelo primeiro file_id válido na lista de candidatos
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
    """Mostra a lista de habilidades ativas e passivas do jogador."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await _safe_edit_or_send(query, context, chat_id, "Erro: Personagem não encontrado.")
        return

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
            logger.warning(f"Skill ID '{skill_id}' encontrado nos dados do jogador {user_id} mas não existe em SKILL_DATA.")
            continue

        name = skill_info.get("display_name", skill_id)
        desc = skill_info.get("description", "Sem descrição.")
        mana_cost = skill_info.get("mana_cost")
        skill_type = skill_info.get("type", "unknown")

        line = f"• <b>{name}</b>"
        if mana_cost is not None:
            line += f" ({mana_cost} MP)"
        line += f": <i>{html.escape(desc)}</i>" # Usa html.escape

        if skill_type == "active" or skill_type.startswith("support"):
            active_skills_lines.append(line)
        elif skill_type == "passive":
            passive_skills_lines.append(line)

    # Monta o texto final
    text_parts = ["📚 <b>Suas Habilidades</b>\n"]

    if active_skills_lines:
        text_parts.append("✨ <b><u>Habilidades Ativas</u></b> ✨")
        text_parts.extend(active_skills_lines)
        text_parts.append("(Você pode equipar até 4 skills ativas para usar em combate)") # Informa o limite
        text_parts.append("")

    if passive_skills_lines:
        text_parts.append("🛡️ <b><u>Habilidades Passivas</u></b> 🛡️")
        text_parts.extend(passive_skills_lines)
        text_parts.append("")

    # --- INÍCIO DA MUDANÇA NO TECLADO ---
    # Teclado inicial apenas com botão de voltar ao perfil
    kb = [[InlineKeyboardButton("⬅️ Voltar ao Perfil", callback_data="profile")]]

    # Adiciona o botão "Equipar Skills" APENAS se houver skills ativas para equipar
    if active_skills_lines:
        kb.insert(0, [InlineKeyboardButton("⚙️ Equipar Skills Ativas", callback_data="skills_equip_menu")])
    # --- FIM DA MUDANÇA NO TECLADO ---

    final_text = "\n".join(text_parts)
    reply_markup = InlineKeyboardMarkup(kb)

    # Usa a função segura para editar (idealmente) ou enviar a nova mensagem
    await _safe_edit_or_send(query, context, chat_id, final_text, reply_markup)

async def show_equip_skills_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o menu para equipar/desequipar skills ativas."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await _safe_edit_or_send(query, context, chat_id, "Erro: Personagem não encontrado.")
        return

    all_skill_ids = player_data.get("skills", [])
    # Garante que equipped_skills existe e é uma lista
    equipped_ids = player_data.get("equipped_skills", [])
    if not isinstance(equipped_ids, list):
        equipped_ids = []
        player_data["equipped_skills"] = equipped_ids # Corrige se não for lista

    # Filtra apenas skills ativas/suporte
    active_skill_ids = [
        skill_id for skill_id in all_skill_ids
        if skills_data.SKILL_DATA.get(skill_id, {}).get("type") == "active" or
           skills_data.SKILL_DATA.get(skill_id, {}).get("type", "").startswith("support")
    ]

    if not active_skill_ids:
        text = "⚙️ Equipar Skills Ativas\n\nVocê não possui nenhuma skill ativa para equipar."
        kb = [[InlineKeyboardButton("⬅️ Voltar (Habilidades)", callback_data="skills_menu_open")]]
        await _safe_edit_or_send(query, context, chat_id, text, InlineKeyboardMarkup(kb))
        return

    text_parts = [f"⚙️ <b>Equipar Skills Ativas</b> (Limite: {len(equipped_ids)}/{MAX_EQUIPPED_SKILLS})\n"]
    kb_rows = []

    # --- Secção: Skills Equipadas ---
    text_parts.append("✅ <b><u>Equipadas Atualmente</u></b> ✅")
    if not equipped_ids:
        text_parts.append("<i>Nenhuma skill ativa equipada.</i>")
    else:
        for skill_id in equipped_ids:
            skill_info = skills_data.SKILL_DATA.get(skill_id)
            if not skill_info: continue # Segurança
            name = skill_info.get("display_name", skill_id)
            mana_cost = skill_info.get("mana_cost")
            line = f"• <b>{name}</b>"
            if mana_cost is not None: line += f" ({mana_cost} MP)"
            text_parts.append(line)
            # Botão para desequipar
            kb_rows.append([InlineKeyboardButton(f"➖ Desequipar {name}", callback_data=f"unequip_skill:{skill_id}")])

    text_parts.append("\n" + ("─" * 20) + "\n") # Separador

    # --- Secção: Skills Disponíveis ---
    text_parts.append("➕ <b><u>Disponíveis para Equipar</u></b> ➕")
    slots_free = MAX_EQUIPPED_SKILLS - len(equipped_ids)
    available_to_equip_found = False

    for skill_id in active_skill_ids:
        # Mostra apenas as skills ativas que NÃO estão equipadas
        if skill_id not in equipped_ids:
            available_to_equip_found = True
            skill_info = skills_data.SKILL_DATA.get(skill_id)
            if not skill_info: continue
            name = skill_info.get("display_name", skill_id)
            mana_cost = skill_info.get("mana_cost")
            line = f"• <b>{name}</b>"
            if mana_cost is not None: line += f" ({mana_cost} MP)"
            text_parts.append(line)

            # Botão para equipar (se houver espaço)
            if slots_free > 0:
                kb_rows.append([InlineKeyboardButton(f"➕ Equipar {name}", callback_data=f"equip_skill:{skill_id}")])
            else:
                # Botão "desativado" (não faz nada ao clicar) se o limite foi atingido
                kb_rows.append([InlineKeyboardButton(f"🚫 Limite Atingido", callback_data="noop")]) # 'noop' = no operation

    if not available_to_equip_found:
         text_parts.append("<i>Não há outras skills ativas disponíveis ou todas já estão equipadas.</i>")

    # Botão para voltar ao menu anterior de skills
    kb_rows.append([InlineKeyboardButton("⬅️ Voltar (Habilidades)", callback_data="skills_menu_open")])

    final_text = "\n".join(text_parts)
    reply_markup = InlineKeyboardMarkup(kb_rows)

    await _safe_edit_or_send(query, context, chat_id, final_text, reply_markup)

async def equip_skill_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Equipa uma skill ativa se houver espaço."""
    query = update.callback_query
    # Responde imediatamente para o Telegram saber que recebemos o clique
    await query.answer()
    user_id = query.from_user.id

    try:
        # Extrai o ID da skill do callback_data (formato: "equip_skill:skill_id")
        skill_id = query.data.split(":", 1)[1]
    except IndexError:
        logger.error(f"Callback equip_skill inválido: {query.data}")
        await query.answer("Erro ao processar a ação.", show_alert=True)
        return

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        # Não edita a mensagem aqui, apenas avisa
        await query.answer("Erro: Personagem não encontrado.", show_alert=True)
        return

    # Garante que a lista existe e obtém a lista atual
    equipped_skills = player_data.setdefault("equipped_skills", [])
    if not isinstance(equipped_skills, list): # Segurança extra
        equipped_skills = []
        player_data["equipped_skills"] = equipped_skills

    # Verifica se a skill já está equipada (segurança)
    if skill_id in equipped_skills:
        await query.answer("Essa skill já está equipada.", show_alert=True)
        # Atualiza o menu caso haja inconsistência
        await show_equip_skills_menu(update, context)
        return

    # Verifica o limite
    if len(equipped_skills) >= MAX_EQUIPPED_SKILLS:
        await query.answer(f"Limite de {MAX_EQUIPPED_SKILLS} skills equipadas atingido!", show_alert=True)
        # Atualiza o menu para mostrar o botão de limite
        await show_equip_skills_menu(update, context)
        return

    # Equipa a skill
    equipped_skills.append(skill_id)
    await player_manager.save_player_data(user_id, player_data)

    # logger.info(f"Jogador {user_id} equipou a skill: {skill_id}") # Log opcional
    # Atualiza a mensagem mostrando o novo estado
    await show_equip_skills_menu(update, context)


async def unequip_skill_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Desequipa uma skill ativa."""
    query = update.callback_query
    await query.answer() # Responde ao clique
    user_id = query.from_user.id

    try:
        # Extrai o ID da skill do callback_data (formato: "unequip_skill:skill_id")
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
    if not isinstance(equipped_skills, list): # Segurança
        equipped_skills = []
        player_data["equipped_skills"] = equipped_skills


    # Verifica se a skill está realmente equipada antes de remover
    if skill_id in equipped_skills:
        equipped_skills.remove(skill_id)
        await player_manager.save_player_data(user_id, player_data)
        # logger.info(f"Jogador {user_id} desequipou a skill: {skill_id}") # Log opcional
    else:
        await query.answer("Essa skill não estava equipada.", show_alert=True)


    # Atualiza a mensagem mostrando o novo estado
    await show_equip_skills_menu(update, context)

async def noop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback que não faz nada, usado para botões desativados como 'Limite Atingido'."""
    query = update.callback_query
    # Apenas responde ao clique para o Telegram saber que foi recebido
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

def _durability_tuple(raw) -> tuple[int, int]:
    """Converte a durabilidade (lista, ditado ou None) para uma tupla (atual, max)."""
    cur, mx = 20, 20
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        try:
            cur = int(raw[0]); mx = int(raw[1])
        except Exception:
            cur, mx = 20, 20
    elif isinstance(raw, dict):
        try:
            cur = int(raw.get("current", 20)); mx = int(raw.get("max", 20))
        except Exception:
            cur, mx = 20, 20
    # Garante que os valores são válidos
    mx = max(1, mx) # Max não pode ser 0
    cur = max(0, min(cur, mx)) # Atual não pode ser negativo ou maior que o max
    return cur, mx

async def show_restore_durability_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
    chat_id = q.message.chat_id
    pdata = await player_manager.get_player_data(user_id) or {}
    inv = pdata.get("inventory", {}) or {}
    equip = pdata.get("equipment", {}) or {}

    lines = ["<b>📜 Restaurar Durabilidade</b>\nEscolha um item <u>equipado</u> para restaurar:\n"]
    kb_rows = []
    any_repairable = False

    for slot, uid in (equip.items() if isinstance(equip, dict) else []):
        inst = inv.get(uid)
        if not (isinstance(inst, dict) and inst.get("base_id")):
            continue
        cur, mx = _durability_tuple(inst.get("durability")) # <-- Agora _durability_tuple existe
        if cur < mx:
            any_repairable = True
            base = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(inst["base_id"], {}) or {}
            name = base.get("display_name", inst["base_id"])
            lines.append(f"• {name} — <b>{cur}/{mx}</b>")
            kb_rows.append([InlineKeyboardButton(f"Restaurar {name}", callback_data=f"rd_fix_{uid}")])

    if not any_repairable:
        lines.append("<i>Nenhum equipamento equipado precisa de reparo.</i>")

    kb_rows.append([InlineKeyboardButton("⬅️ 𝕍𝕠𝕝𝕥𝕒𝕣", callback_data="profile")])

    try:
        await q.edit_message_caption(caption="\n".join(lines), reply_markup=InlineKeyboardMarkup(kb_rows), parse_mode="HTML")
    except Exception:
        try:
             await q.edit_message_text(text="\n".join(lines), reply_markup=InlineKeyboardMarkup(kb_rows), parse_mode="HTML")
        except Exception as e:
             logger.warning(f"Falha ao editar menu de durabilidade: {e}")
             await context.bot.send_message(chat_id=chat_id, text="\n".join(lines), reply_markup=InlineKeyboardMarkup(kb_rows), parse_mode="HTML")

async def fix_item_durability(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
    pdata = await player_manager.get_player_data(user_id) or {} 
    uid = q.data.replace("rd_fix_", "", 1)

    from modules.profession_engine import restore_durability as restore_durability_engine

    res = restore_durability_engine(pdata, uid)
    if isinstance(res, dict) and res.get("error"):
        await q.answer(res["error"], show_alert=True)
        await show_restore_durability_menu(update, context) # <-- Agora show_restore_durability_menu existe
        return

    await player_manager.save_player_data(user_id, pdata)

    await q.answer("Durabilidade restaurada!", show_alert=True)
    await show_restore_durability_menu(update, context) # <-- Agora show_restore_durability_menu existe

async def fix_item_durability(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
    # <<< CORREÇÃO 3: Adiciona await >>>
    pdata = await player_manager.get_player_data(user_id) or {} 
    uid = q.data.replace("rd_fix_", "", 1)

    # usamos o engine oficial para reparar (consome pergaminho)
    from modules.profession_engine import restore_durability as restore_durability_engine

    res = restore_durability_engine(pdata, uid) # Síncrono
    if isinstance(res, dict) and res.get("error"):
        await q.answer(res["error"], show_alert=True)
        # volta/atualiza a listagem
        # <<< CORREÇÃO 4: Adiciona await >>>
        await show_restore_durability_menu(update, context) # Chama função async
        return

    # <<< CORREÇÃO 5: Adiciona await >>>
    await player_manager.save_player_data(user_id, pdata)

    # feedback leve e atualiza a lista
    await q.answer("Durabilidade restaurada!", show_alert=True)
    # <<< CORREÇÃO 6: Adiciona await >>>
    await show_restore_durability_menu(update, context) # Chama função async
    
#
# >>> COLE ESTA FUNÇÃO COMPLETA NO LUGAR DA SUA "profile_callback" ANTIGA <<<
# (handlers/profile_handler.py)
#

async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # --- NOVA CORREÇÃO (Início) ---
    # Lógica para lidar com COMANDO ou BOTÃO
    query = update.callback_query
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if not chat_id:
         logger.warning("profile_callback não conseguiu determinar o chat_id.")
         return

    if query:
        await query.answer()
    # --- NOVA CORREÇÃO (Fim) ---
        
    # Carrega os dados do jogador (Já estava correto com await)
    player_data = await player_manager.get_player_data(user_id)

    if not player_data:
        # --- NOVA CORREÇÃO: Usa o 'update' e não o 'query' para o _safe_edit_or_send ---
        await _safe_edit_or_send_v2(update, context, chat_id, "Erro: Personagem não encontrado. Use /start para começar.")
        return
    
    # ===== totais (base + equipamentos) =====
    
    # <<< CORREÇÃO 1: Adiciona await AQUI >>>
    totals = await player_manager.get_player_total_stats(player_data)
    
    # Agora 'totals' é um dicionário e .get() vai funcionar
    total_hp_max = int(totals.get('max_hp', 50))
    total_atk = int(totals.get('attack', 0))
    total_def = int(totals.get('defense', 0))
    total_ini = int(totals.get('initiative', 0))
    total_luck = int(totals.get('luck', 0))

    current_hp = max(0, min(int(player_data.get('current_hp', total_hp_max)), total_hp_max))
    
    # <<< CORREÇÃO 2 & 3: Adiciona await AQUI TAMBÉM >>>
    chance_esquiva = int((await player_manager.get_player_dodge_chance(player_data)) * 100)
    chance_ataque_duplo = int((await player_manager.get_player_double_attack_chance(player_data)) * 100)

    location_key = player_data.get('current_location', 'reino_eldora')
    location_name = (game_data.REGIONS_DATA or {}).get(location_key, {}).get('display_name', 'Lugar Desconhecido')

    # =================================================================
    # ===== BLOCO PREMIUM (Já estava correto) =====
    # =================================================================
    premium_line = ""
    premium = PremiumManager(player_data) # Instancia o manager
    if premium.is_premium(): # Usa o método correto para verificar
        tier_name = premium.tier.capitalize() if premium.tier else "Premium"
        exp_date = premium.expiration_date
        
        premium_line = f"\n👑 <b>Status Premium:</b> {tier_name}"
        if exp_date:
            premium_line += f"\n(Expira em: {exp_date.strftime('%d/%m/%Y')})"
        else:
            premium_line += " (Permanente)"
    
    # (Resto da lógica de XP, Profissão, Classe - mantida igual)
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

    # ===== teclado (Mantido igual) =====
    keyboard = []
    if player_manager.needs_class_choice(player_data):
        keyboard.append([InlineKeyboardButton("✨ 𝐄𝐬𝐜𝐨𝐥𝐡𝐞𝐫 𝐂𝐥𝐚𝐬𝐬𝐞", callback_data='class_open')])
    if not prof_norm:
        keyboard.append([InlineKeyboardButton("💼 𝐄𝐬𝐜𝐨𝐥𝐡𝐞𝐫 𝐏𝐫𝐨𝐟𝐢𝐬𝐬𝐚̃𝐨", callback_data='job_menu')])

    keyboard.extend([
        [InlineKeyboardButton("🔰  𝐂𝐥𝐚n  🔰", callback_data='clan_menu:profile')],
        [InlineKeyboardButton("📊 𝐒𝐭𝐚𝐭𝐮𝐬 & 𝐀𝐭𝐫𝐢𝐛𝐮𝐭𝐨𝐬", callback_data='status_open')],
        [InlineKeyboardButton("🧰 𝐄𝐪𝐮𝐢𝐩𝐚𝐦𝐞𝐧𝐭𝐨𝐬", callback_data='equipment_menu')],
        [InlineKeyboardButton("🎒 𝐕𝐞𝐫 𝐈𝐧𝐯𝐞𝐧𝐭𝐚́𝐫𝐢𝐨 𝐂𝐨𝐦𝐩𝐥𝐞to", callback_data='inventory_CAT_equipamento_PAGE_1')],
        [InlineKeyboardButton("🧪 𝐔𝐬𝐚𝐫 𝐂𝐨𝐧𝐬𝐮𝐦𝐢́𝐯𝐞𝐥", callback_data='potion_menu')],
        [InlineKeyboardButton("📚 𝐇𝐚𝐛𝐢𝐥𝐢𝐝𝐚𝐝𝐞𝐬", callback_data='skills_menu_open')],
        [InlineKeyboardButton("🎨 𝐌𝐮𝐝𝐚𝐫 𝐀𝐩𝐚𝐫𝐞̂𝐧𝐜𝐢𝐚", callback_data='skin_menu')],
        [InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data='continue_after_action')],
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)

    # ===== mídia da classe (Mantido igual) =====
    media = _get_class_media(player_data, "personagem")
    if media and media.get("id"):
        try:
            # --- NOVA CORREÇÃO: Apenas apaga se for um botão ---
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

    # Fallback: sem mídia (Mantido igual)
    # --- NOVA CORREÇÃO: Passa 'update' em vez de 'query' ---
    await _safe_edit_or_send_v2(update, context, chat_id, profile_text, reply_markup=reply_markup, parse_mode='HTML')


# --- NOVA FUNÇÃO HELPER (Necessária para a correção) ---
# (Pode apagar a sua `_safe_edit_or_send` antiga e usar esta)
async def _safe_edit_or_send_v2(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str, reply_markup=None, parse_mode='HTML'):
    """
    Tenta editar a mensagem se for um CallbackQuery.
    Se falhar, ou se for um Comando, envia uma nova mensagem.
    """
    query = update.callback_query
    if query:
        try:
            await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
            return
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                pass # Tenta editar como texto
        except Exception:
            pass # Tenta editar como texto
        
        try:
            await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
            return
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                logger.debug(f"_safe_edit_or_send_v2: Falha ao editar texto: {e}")
        except Exception as e:
            logger.debug(f"_safe_edit_or_send_v2: Falha ao editar texto: {e}")

    # Fallback: Se for comando ou se a edição falhar
    try:
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        logger.error(f"_safe_edit_or_send_v2: Falha ao enviar nova mensagem: {e}")

profile_handler = CallbackQueryHandler(profile_callback, pattern=r'^(?:profile|personagem|char_sheet_main)$') # Callback para botões como "Voltar ao Perfil"
character_command_handler = CommandHandler("personagem", profile_callback)



# Handlers de Skills
skills_menu_handler = CallbackQueryHandler(show_skills_menu, pattern=r"^skills_menu_open$")
skills_equip_menu_handler = CallbackQueryHandler(show_equip_skills_menu, pattern=r"^skills_equip_menu$")
equip_skill_handler = CallbackQueryHandler(equip_skill_callback, pattern=r"^equip_skill:")
unequip_skill_handler = CallbackQueryHandler(unequip_skill_callback, pattern=r"^unequip_skill:")
noop_handler = CallbackQueryHandler(noop_callback, pattern=r"^noop$")

