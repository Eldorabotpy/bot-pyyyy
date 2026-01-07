# handlers/refining_handler.py
# (VERSÃO FINAL: AUTH UNIFICADA + ID SEGURO)

import logging 
import math
import telegram
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
)
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules.auth_utils import get_current_player_id
from modules.game_data import attributes
from modules import game_data, player_manager, file_ids
from modules.refining_engine import preview_refine, start_refine, finish_refine, start_batch_refine, get_max_refine_quantity
from modules import crafting_registry, dismantle_engine, display_utils

ITEMS_PER_PAGE = 5

SLOT_FANCY_TEXT = {
    "arma": "𝐀𝐫𝐦𝐚",
    "armadura": "𝐀𝐫𝐦𝐚𝐝𝐮𝐫𝐚",
    "elmo": "𝐄𝐥𝐦𝐨",
    "calca": "𝐂𝐚𝐥𝐜̧𝐚",
    "luvas": "𝐋𝐮𝐯𝐚𝐬",
    "botas": "𝐁𝐨𝐭𝐚𝐬",
    "anel": "𝐀𝐧𝐞𝐥",
    "colar": "𝐂𝐨𝐥𝐚𝐫",
    "brinco": "𝐁𝐫𝐢𝐧𝐜𝐨"
}

SLOT_EMOJI_MAP = {
    "arma": "⚔️", "elmo": "🪖", "armadura": "👕", "calca": "👖",
    "luvas": "🧤", "botas": "🥾", "colar": "📿", "anel": "💍", "brinco": "🧿",
}
logger = logging.getLogger(__name__)

# =========================
# HELPER DE VISUAL (NOVO)
# =========================
def _get_profession_header(pdata: dict) -> str:
    prof = pdata.get("profession", {})
    p_type = str(prof.get("type", "Aprendiz")).upper()
    lvl = int(prof.get("level", 1))
    # Correção visual de nível 0
    if lvl < 1 and p_type: lvl = 1
    
    xp = int(prof.get("xp", 0))
    return (
        f"⚒️ <b>OFICINA DE REFINO</b>\n"
        f"👷 <b>Profissão:</b> {p_type} <code>[Lv. {lvl}]</code>\n"
        f"🎓 <b>XP Atual:</b> <code>{xp}</code>\n"
        f"──────────────────────"
    )
# =====================================================
# 1. CORE LOGIC - REFINO
# =====================================================
async def execute_refine_logic(
    user_id: str, 
    chat_id: int, 
    context: ContextTypes.DEFAULT_TYPE, 
    message_id_to_delete: int = None
):
    """Finaliza o refino e mostra o loot com estilo."""
    # 1. Tenta apagar a mensagem de progresso (Refinando...)
    if message_id_to_delete:
        try: 
            await context.bot.delete_message(chat_id, message_id_to_delete)
        except Exception: 
            pass # Se já foi apagada ou não existe, ignora

    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return

    res = await finish_refine(pdata)
    
    if isinstance(res, str):
        await context.bot.send_message(chat_id, f"❗ {res}")
        return
    if not res: return

    outs = res.get("outputs") or {}
    xp = res.get("xp_gained", 0)
    
    # Visual de Sucesso
    lines = [
        "✅ <b>PROCESSO CONCLUÍDO!</b>",
        "──────────────────────",
        "<i>Os itens foram adicionados ao seu inventário.</i>\n",
        "🎒 <b>VOCÊ RECEBEU:</b>"
    ]
    
    for k, v in outs.items():
        lines.append(f" ╰┈➤ {_fmt_item_line(k, v)}")
    
    if xp > 0:
        lines.append(f" ╰┈➤ ✨ <b>XP Profissão:</b> <code>+{xp}</code>")
        
    lines.append("\n────────────────────────")
    
    caption = "\n".join(lines)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Refino", callback_data="ref_main")]])

    mkey = None
    if outs:
        iid = list(outs.keys())[0]
        mkey = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(iid, {}).get("media_key")

    # Envia a NOVA mensagem de resultado
    await _safe_send_with_media(context, chat_id, caption, kb, media_key=mkey)

# =====================================================
# 2. CORE LOGIC - DESMONTE (SINGLE)
# =====================================================
async def execute_dismantle_logic(
    user_id: str,
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    job_details: dict,
    message_id_to_delete: int = None
):
    """Finaliza o desmonte único."""
    # 1. Apaga a mensagem de progresso
    if message_id_to_delete:
        try: 
            await context.bot.delete_message(chat_id, message_id_to_delete)
        except Exception: 
            pass

    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return

    result = await dismantle_engine.finish_dismantle(pdata, job_details)

    if isinstance(result, str):
        await context.bot.send_message(chat_id, f"❗ Erro desmonte: {result}")
        return

    item_name, returned_materials = result
    
    lines = [f"♻️ <b>{item_name}</b> desmontado!", "\n📉 <b>Recuperado:</b>"]
    if not returned_materials: lines.append(" ╰┈➤ <i>Nada (Item sem receita?)</i>")
    else:
        for k, v in returned_materials.items():
            lines.append(f" ╰┈➤ {_fmt_item_line(k, v)}")

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="ref_main")]])
    
    # Envia NOVA mensagem
    await context.bot.send_message(chat_id, "\n".join(lines), parse_mode="HTML", reply_markup=kb)


# =====================================================
# 3. CORE LOGIC - DESMONTE EM MASSA (BULK)
# =====================================================
async def execute_bulk_dismantle_logic(
    user_id: str,
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    job_details: dict,
    message_id_to_delete: int = None
):
    """
    Finaliza o desmonte em massa.
    """
    # 1. Apaga a mensagem de progresso
    if message_id_to_delete:
        try: 
            await context.bot.delete_message(chat_id, message_id_to_delete)
        except Exception: 
            pass

    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return
    
    result = await dismantle_engine.finish_dismantle_batch(pdata, job_details)
    
    if isinstance(result, str):
        await context.bot.send_message(chat_id, f"❗ Erro no desmonte: {result}")
        return

    item_name, rewards = result 

    # Monta a mensagem visual
    count = job_details.get("qty_dismantling", 1)
    
    lines = [f"♻️ <b>Desmonte em Massa Concluído!</b>", f"Foram destruídos {count}x <b>{item_name}</b>.", "\n📉 <b>Total Recuperado:</b>"]
    
    if not rewards: 
        lines.append(" ╰┈➤ <i>Nada.</i>")
    else:
        for k, v in rewards.items():
            lines.append(f" ╰┈➤ {_fmt_item_line(k, v)}")

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="ref_main")]])
    
    # Envia NOVA mensagem
    await context.bot.send_message(chat_id, "\n".join(lines), parse_mode="HTML", reply_markup=kb)


# =====================================================
# 4. JOB WRAPPERS
# =====================================================
async def finish_refine_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Executado quando o tempo de refino acaba.
    RECUPERA O ID DO USUÁRIO DO BANCO 'USERS' VIA JOB.DATA.
    """
    job = context.job
    if not job: return

    # --- CORREÇÃO CRÍTICA DE ID ---
    # O job.user_id nativo do Telegram é um INT. 
    # O nosso sistema novo usa STRING (ObjectId).
    # Portanto, devemos pegar o ID que salvamos explicitamente no 'data'.
    user_id = job.data.get("user_id")
    chat_id = job.chat_id
    mid = job.data.get("message_id_to_delete")

    # Validação de Segurança
    if not user_id:
        logger.error(f"❌ [Refino] Job {job.name} executado sem 'user_id' no data!")
        return

    # 1. Tenta apagar a mensagem de progresso (barra de carregamento)
    if mid:
        try: 
            await context.bot.delete_message(chat_id, mid)
        except Exception: 
            pass # Ignora se a mensagem já foi apagada ou não existe mais

    # 2. Busca os dados do jogador no banco novo (usando o ID String)
    pdata = await player_manager.get_player_data(user_id)
    if not pdata: 
        return

    # 3. Executa a finalização lógica (Engine)
    # Isso calcula recompensas, entrega itens e dá XP
    res = await finish_refine(pdata)
    
    # Tratamento de erro da engine
    if isinstance(res, str):
        await context.bot.send_message(chat_id, f"❗ Ocorreu um erro no refino: {res}")
        return
    if not res: 
        return

    # 4. Monta a Mensagem de Sucesso
    outs = res.get("outputs") or {}
    xp = res.get("xp_gained", 0)
    
    lines = [
        "✅ <b>PROCESSO CONCLUÍDO!</b>",
        "──────────────────────",
        "🎒 <b>VOCÊ RECEBEU:</b>"
    ]
    
    # Lista os itens recebidos
    for item_id, qty in outs.items():
        # Usa o helper _fmt_item_line que deve existir no arquivo
        lines.append(f" ╰┈➤ {_fmt_item_line(item_id, qty)}")
    
    # Mostra XP se houver
    if xp > 0:
        lines.append(f" ╰┈➤ ✨ <b>XP Profissão:</b> <code>+{xp}</code>")
        
    # Adiciona botão para voltar
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Refino", callback_data="ref_main")]])
    
    # Envia a mensagem final
    await context.bot.send_message(chat_id, "\n".join(lines), parse_mode="HTML", reply_markup=kb)

async def finish_dismantle_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    if not job: return
    
    user_id = str(job.data.get("user_id") or job.user_id)
    
    await execute_dismantle_logic(
        user_id=user_id,
        chat_id=job.chat_id,
        context=context,
        job_details=job.data,
        message_id_to_delete=job.data.get("message_id_to_delete")
    )

async def finish_bulk_dismantle_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    if not job: return
    
    user_id = job.data.get("user_id") 
    if not user_id: return
    
    await execute_bulk_dismantle_logic(
        user_id=user_id,
        chat_id=job.chat_id,
        context=context,
        job_details=job.data,
        message_id_to_delete=job.data.get("message_id_to_delete")
    )


# =========================
# Helpers UI
# =========================
def _fmt_minutes_or_seconds(seconds: int) -> str:
    if seconds < 60: return f"{int(seconds)}s"
    mins = seconds // 60
    secs = seconds % 60
    if secs > 0: return f"{mins}m {secs}s"
    return f"{mins} min"

def _fmt_item_line(item_id: str, qty: int) -> str:
    info = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(item_id) or {}
    display = info.get("display_name") or item_id.replace("_", " ").title()
    emoji = info.get("emoji", "📦")
    return f"{emoji} <b>{display}</b> x<code>{int(qty)}</code>"
    
def _fmt_item_details_styled(item_data: dict) -> str:
    """Formata o item com visual rico."""
    cur_dur = item_data.get("durability")
    max_dur = item_data.get("max_durability")
    dur_str = f"[{cur_dur}/{max_dur}] " if (cur_dur is not None and max_dur) else ""

    class_req = item_data.get("class_req")
    class_emoji = ""
    if class_req:
        c_name = (class_req[0] if isinstance(class_req, list) else str(class_req)).lower()
        c_emojis = {
            "guerreiro": "⚔️", "berserker": "🪓", "cacador": "🏹",
            "monge": "🧘", "mago": "🧙", "bardo": "🎶",
            "assassino": "🔪", "samurai": "🥷", "curandeiro": "🩹"
        }
        if c_name in c_emojis:
            class_emoji = f"{c_emojis[c_name]} "

    name = item_data.get("display_name", "Item")
    item_emoji = item_data.get("emoji", "") 
    rarity = (item_data.get("rarity") or "comum").title()
    lvl = item_data.get("enhancement", item_data.get("level", 0))
    lvl_str = f" [+ {lvl}]" if lvl > 0 else ""

    stat_icons = {
        "vida": "❤️", "hp": "❤️", "max_hp": "❤️", "health": "❤️", "vitalidade": "❤️", "vit": "❤️",
        "mana": "💧", "max_mana": "💧", "mp": "💧", "max_mp": "💧", "inteligencia": "🧠", "intelligence": "🧠", "int": "🧠",
        "ataque": "⚔️", "attack": "⚔️", "atk": "⚔️", "dano": "⚔️", "damage": "⚔️",
        "forca": "💪", "strength": "💪", "str": "💪", "fisico": "💪",
        "defesa": "🛡️", "defense": "🛡️", "def": "🛡️", "armadura": "🛡️", "armor": "🛡️",
        "resistencia": "🛡️", "resistance": "🛡️", "res": "🛡️", "block": "🛡️",
        "agilidade": "🏃", "agility": "🏃", "agi": "🏃",
        "iniciativa": "⚡", "initiative": "⚡", "ini": "⚡", "velocidade": "⚡",
        "sorte": "🍀", "luck": "🍀", "lucky": "🍀", "luk": "🍀",
        "critico": "💥", "crit": "💥", "crit_chance": "💥", "crit_chance_flat": "💥",
        "dano_critico": "🩸", "crit_damage": "🩸", "crit_damage_mult": "🩸",
        "furia": "💢", "rage": "💢",
        "precisao": "🎯", "mira": "🎯", "precision": "🎯", "accuracy": "🎯",
        "fe": "🙏", "faith": "🙏",
        "carisma": "👄", "charisma": "👄",
        "bushido": "👹", "honra": "👹",
        "foco": "🧿", "focus": "🧿", "chi": "☯️",
        "letalidade": "☠️", "lethality": "☠️", "morte": "☠️",
        "cura": "❤️‍🩹", "heal": "❤️‍🩹", "heal_potency": "❤️‍🩹",
        "magia": "🔮", "magic": "🔮", "magic_attack": "🔮", "poder_magico": "🔮",
        "esquiva": "💨", "dodge": "💨",
        "penetracao": "🔩", "penetration": "🔩", "armor_penetration": "🔩",
        "roubo_vida": "🧛", "lifesteal": "🧛", "vampirismo": "🧛",
        "tenacidade": "🏰", "tenacity": "🏰"
    }

    stats_str_list = []
    stats = dict(item_data.get("stats") or {})
    ench = item_data.get("enchantments", {})
    
    for k, v in ench.items():
        val = v["value"] if isinstance(v, dict) and "value" in v else (v if isinstance(v, (int, float)) else 0)
        if val > 0: stats[k] = stats.get(k, 0) + val

    ignored_keys = {"durability", "max_durability", "level", "enhancement"}
    
    for key, val in stats.items():
        k_clean = str(key).lower().strip().replace(" ", "_")
        if k_clean in ignored_keys or not isinstance(val, (int, float)) or val == 0: continue
        
        icon = stat_icons.get(k_clean, "🔹")
        if icon == "🔹": 
            k_display = str(key).replace("_", " ").title()
            stats_str_list.append(f"{icon} {k_display} +{val}")
        else:
            stats_str_list.append(f"{icon} +{val}")

    stats_display = ", ".join(stats_str_list)
    if not stats_display: stats_display = "Sem atributos"
    total_slots = item_data.get("slots", 0) 
    slots_visual = f" ({'⚪️' * int(total_slots)})" if total_slots > 0 else ""

    return f"『{dur_str}{class_emoji}{item_emoji} {name}{lvl_str}[{rarity}]: {stats_display} 』{slots_visual}"

async def _safe_send_with_media(context, chat_id, caption, reply_markup=None, media_key=None, fallback_key="refino_universal"):
    keys = [k for k in [media_key, fallback_key] if k]
    for key in keys:
        fd = file_ids.get_file_data(key)
        if fd and fd.get("id"):
            try:
                if fd.get("type") == "video":
                    return await context.bot.send_video(chat_id, fd["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
                else:
                    return await context.bot.send_photo(chat_id, fd["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
            except: pass
    return await context.bot.send_message(chat_id, caption, reply_markup=reply_markup, parse_mode="HTML")

async def _safe_edit_or_send_with_media(query, context, caption, reply_markup=None, media_key="refino_universal"):
    try: await query.message.delete()
    except: pass
    
    # Busca file_id
    fd = file_ids.get_file_data(media_key)
    chat_id = query.message.chat_id
    
    if fd and fd.get("id"):
        try:
            if fd.get("type") == "video":
                return await context.bot.send_video(chat_id, fd["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
            else:
                return await context.bot.send_photo(chat_id, fd["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
        except: pass
    return await context.bot.send_message(chat_id, caption, reply_markup=reply_markup, parse_mode="HTML")

# =========================
# HANDLERS CALLBACKS
# =========================

async def refining_main_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    # 🔒 SEGURANÇA TOTAL: Obtém o ID da sessão do banco de dados (String/ObjectId)
    # Se o user não tiver logado, isso retorna None e barra o acesso.
    uid = get_current_player_id(update, context)
    if not uid:
        await q.answer("⚠️ Sessão expirada. Digite /login ou /start.", show_alert=True)
        return
    
    # Correção preventiva de inventário
    await player_manager.corrigir_inventario_automatico(uid)

    pdata = await player_manager.get_player_data(uid)
    if not pdata:
        await q.answer("Erro ao carregar perfil.", show_alert=True)
        return

    # Lógica de Paginação e Exibição (Mantida igual, mas usando dados seguros)
    page = 1
    if "_PAGE_" in q.data: 
        try: page = int(q.data.split('_PAGE_')[-1])
        except: page = 1

    recipes = []
    refining_recipes = getattr(game_data, "REFINING_RECIPES", {}) or {}
    
    for rid, rec in refining_recipes.items():
        prev = preview_refine(rid, pdata)
        if prev:
            sec = int(prev.get("duration_seconds", 0))
            t_fmt = f"{sec//60:02d}:{sec%60:02d}m"
            recipes.append({
                "id": rid, 
                "name": rec.get("display_name"),
                "prev": prev, 
                "time": t_fmt,
                "req_lvl": rec.get("level_req", 1)
            })

    total_p = max(1, math.ceil(len(recipes) / ITEMS_PER_PAGE))
    page = max(1, min(page, total_p))
    current = recipes[(page-1)*ITEMS_PER_PAGE : page*ITEMS_PER_PAGE]

    prof = pdata.get("profession", {})
    p_type = str(prof.get("type", "Aprendiz")).upper()
    lvl = int(prof.get("level", 1))

    lines = [
        f"⚒️ <b>OFICINA DE REFINO</b>",
        f"👷 <b>Profissão:</b> {p_type} <code>[Lv. {lvl}]</code>",
        f"──────────────────────"
    ]
    
    kb = []
    # Botão de Desmonte no Topo
    kb.append([InlineKeyboardButton("♻️ MODO DE DESMONTAGEM ♻️", callback_data="ref_dismantle_list")])

    for r in current:
        can = r["prev"].get("can_refine")
        icon = "🟢" if can else "🔴"
        status_txt = "Pronto" if can else "Falta Material/Nível"
        
        lines.append(f"\n{icon} <b>{r['name']}</b>")
        lines.append(f"   └─ ⏳ {r['time']} | {status_txt}")
        
        kb.append([InlineKeyboardButton(f"🔨 FORJAR: {r['name']}", callback_data=f"ref_sel_{r['id']}")])

    lines.append(f"\n📄 <b>Página {page}/{total_p}</b>")

    nav = []
    if page > 1: nav.append(InlineKeyboardButton("◀️", callback_data=f"ref_main_PAGE_{page-1}"))
    nav.append(InlineKeyboardButton("🔄", callback_data="noop_ref_page"))
    if page < total_p: nav.append(InlineKeyboardButton("▶️", callback_data=f"ref_main_PAGE_{page+1}"))
    if nav: kb.append(nav)
    
    kb.append([InlineKeyboardButton("🔙 Fechar", callback_data="continue_after_action")])

    await _safe_edit_or_send_with_media(q, context, "\n".join(lines), InlineKeyboardMarkup(kb))
    
async def ref_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    
    # 1. Apaga o menu de seleção anterior
    try: await q.delete_message()
    except: pass
    
    # 2. 🔒 SEGURANÇA: Obtém o ID da sessão (String/ObjectId)
    # Se não tiver sessão ativa, barra o acesso.
    uid = get_current_player_id(update, context)
    if not uid:
        await q.answer("Sessão inválida. Digite /start.", show_alert=True)
        return

    # 3. Identifica a receita
    rid = q.data.replace("ref_confirm_", "", 1)
    
    # 4. Carrega dados do jogador
    pdata = await player_manager.get_player_data(uid)
    
    # 5. Verifica se já está ocupado
    if pdata.get("player_state", {}).get("action") not in (None, "idle"):
        await context.bot.send_message(
            q.message.chat_id, 
            "⚠️ <b>Ocupado!</b> Você já está fazendo outra coisa.", 
            parse_mode="HTML"
        )
        return

    # 6. Inicia o refino na Engine
    res = await start_refine(pdata, rid)
    
    # Se retornar string, é mensagem de erro
    if isinstance(res, str):
        await context.bot.send_message(q.message.chat_id, f"❌ {res}", parse_mode="HTML")
        return

    # 7. Prepara o visual de progresso
    secs = int(res.get("duration_seconds", 60))
    t = _fmt_minutes_or_seconds(secs)
    
    # Busca nome bonito do item
    recipe_info = (getattr(game_data, "REFINING_RECIPES", {}) or {}).get(rid, {})
    title = recipe_info.get("display_name", rid)
    
    # Barra de progresso inicial (vazia)
    bar = "▒▒▒▒▒▒▒▒▒▒"
    
    txt = (
        f"🔨 <b>FORJA INICIADA:</b>\n"
        f"<b>{title.upper()}</b>\n"
        f"──────────────────────\n"
        f" ╰┈➤⏳ <b>Tempo Estimado:</b> <code>{t}</code>\n"
        f" ╰┈➤🔋 <b>Estado:</b> <code>Aquecendo fornalha...</code>\n\n"
        f" ╰┈➤[{bar}] 0%\n"
        f"<i>Você pode fechar esta janela, o bot avisará quando terminar.</i>"
    )
    
    # 8. Envia a mensagem com mídia (se houver)
    sent = await _safe_send_with_media(context, q.message.chat_id, txt)
    mid = sent.message_id if sent else None
    
    # 9. Agenda o Job de finalização
    # IMPORTANTE: Não passamos 'user_id=uid' como argumento direto pois ele é String.
    # Passamos apenas dentro de 'data' para evitar conflito de tipo na lib.
    context.job_queue.run_once(
        finish_refine_job, 
        secs, 
        chat_id=q.message.chat_id,
        data={
            "rid": rid, 
            "message_id_to_delete": mid, 
            "user_id": uid  # <--- O ID seguro vai aqui dentro
        }, 
        name=f"refining:{uid}"
    )

async def ref_batch_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o menu para escolher a quantidade do lote com visual melhorado."""
    q = update.callback_query
    # Apaga menu anterior
    try: await q.delete_message()
    except: pass
    
    rid = q.data.replace("ref_batch_menu_", "")
    
    # 🔒 SEGURANÇA: ID via Auth Central
    uid = get_current_player_id(update, context)
    if not uid:
        return

    pdata = await player_manager.get_player_data(uid)
    rec = game_data.REFINING_RECIPES.get(rid)
    
    max_qty = get_max_refine_quantity(pdata, rec)
    rec_name = rec.get("display_name", "Item").upper()
    
    txt = (
        f"📚 <b>LOTE: {rec_name}</b>\n"
        f"──────────────────────\n"
        f" ╰┈➤ 📦 <b>Limite Atual:</b> <code>{max_qty}</code> un.\n"
        f" ╰┈➤ ⏳ <b>Tempo:</b> <code>Acumulativo</code>\n"
        f" ╰┈➤ ⚖️ <b>XP:</b> <code>-50%</code> (Penalidade)\n"
        f"──────────────────────\n\n"
        f"<i>Quantas unidades deseja produzir?</i>"
    )
    
    kb = []
    options = []
    if max_qty >= 2: options.append(2)
    if max_qty >= 5: options.append(5)
    if max_qty >= 10: options.append(10)
    
    unique_options = sorted(list(set(options + [max_qty])))
    
    row = []
    for val in unique_options:
        label = f"⚡ {val}x (MÁX)" if val == max_qty else f"{val}x"
        row.append(InlineKeyboardButton(label, callback_data=f"ref_batch_go_{rid}_{val}"))
        
        if len(row) >= 3:
            kb.append(row); row = []
            
    if row: kb.append(row)
    
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data=f"ref_sel_{rid}")])
    
    mkey = rec.get("media_key")
    await _safe_send_with_media(context, q.message.chat_id, txt, InlineKeyboardMarkup(kb), media_key=mkey)

async def ref_batch_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try: await q.delete_message()
    except Exception: pass
    
    payload = q.data.replace("ref_batch_go_", "")
    try:
        rid, qty_str = payload.rsplit("_", 1)
        qty = int(qty_str)
    except ValueError:
        await context.bot.send_message(q.message.chat_id, "❌ Erro interno: Receita inválida.")
        return

    uid = get_current_player_id(update, context)
    if not uid:
        await q.answer("Sessão inválida.", show_alert=True)
        return

    pdata = await player_manager.get_player_data(uid)
    
    if pdata.get("player_state", {}).get("action") not in (None, "idle"):
        await context.bot.send_message(q.message.chat_id, "⚠️ Você já está ocupado!")
        return

    res = await start_batch_refine(pdata, rid, qty)
    
    if isinstance(res, str): 
        await context.bot.send_message(q.message.chat_id, f"❌ {res}")
        return

    seconds = int(res["duration_seconds"])
    xp = res["xp_reward"]
    rec = game_data.REFINING_RECIPES.get(rid, {})
    name = rec.get("display_name") or rid.replace("_", " ").title()
    
    txt = (
        f"⚙️ <b>LOTE INICIADO\n"
        f" ╰┈➤{qty}x {name}</b>\n"
        f"──────────────────────\n"
        f" ╰┈➤ ⏳ <b>Tempo Total:</b> <code>{_fmt_minutes_or_seconds(seconds)}</code>\n"
        f" ╰┈➤ ✨ <b>XP Previsto:</b> <code>{xp}</code>\n"
        f" ╰┈➤ ⏲️ <i>Produção em massa iniciada...</i>"
    )
    
    sent = await _safe_send_with_media(context, q.message.chat_id, txt)
    mid = sent.message_id if sent else None
    
    # CORREÇÃO: 'user_id': uid no data
    context.job_queue.run_once(
        finish_refine_job, 
        seconds, 
        chat_id=q.message.chat_id,
        data={
            "rid": rid, 
            "message_id_to_delete": mid, 
            "user_id": uid # <--- CRÍTICO
        }, 
        name=f"refining:{uid}"
    )

async def ref_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe detalhes da receita e opção de refino."""
    q = update.callback_query
    # Apaga o menu anterior
    try: await q.delete_message()
    except: pass

    rid = q.data.replace("ref_sel_", "", 1)
    
    # 🔒 SEGURANÇA: ID via Auth Central
    uid = get_current_player_id(update, context)
    if not uid: return

    pdata = await player_manager.get_player_data(uid)
    
    prev = preview_refine(rid, pdata)
    if not prev: return
    
    rec = game_data.REFINING_RECIPES.get(rid) or {}
    
    raw_prof = rec.get("profession", "Geral")
    if isinstance(raw_prof, list):
        prof_display = str(raw_prof[0]).title() if raw_prof else "Geral"
    else:
        prof_display = str(raw_prof).title()

    t_fmt = _fmt_minutes_or_seconds(int(prev.get("duration_seconds", 0)))
    req_lvl = rec.get("level_req", 1)
    
    p_prof = pdata.get("profession", {})
    cur_lvl = int(p_prof.get("level", 1))
    
    valid_prof = False
    if isinstance(raw_prof, list): valid_prof = p_prof.get("type") in raw_prof
    else: valid_prof = p_prof.get("type") == raw_prof
    
    if not valid_prof: cur_lvl = 0

    lvl_icon = "✅" if cur_lvl >= req_lvl else "❌"
    
    txt = (
        f"⚒️ <b>FORJA: {rec.get('display_name', rid).upper()}</b>\n"
        f"──────────────────────\n"
        f" ╰┈➤ ⏳ <b>Tempo:</b> <code>{t_fmt}</code>\n"
        f" ╰┈➤ 📚 <b>{prof_display}:</b> <code>Nv. {cur_lvl}/{req_lvl}</code> {lvl_icon}\n"
        f"──────────────────────\n"
    )
    
    txt += "📥 <b>INGREDIENTES:</b>\n"
    inputs = prev.get("inputs") or {}
    for k, qty in inputs.items():
        inv_item = pdata.get("inventory", {}).get(k)
        has = int(inv_item.get("quantity", 0)) if isinstance(inv_item, dict) else int(inv_item or 0)
        check = "✅" if has >= qty else "❌"
        txt += f" ╰┈➤ {_fmt_item_line(k, qty)}  <code>({has})</code> {check}\n"

    txt += "\n📦 <b>RESULTADO:</b>\n"
    for k, qty in (prev.get("outputs") or {}).items():
        txt += f" ╰┈➤ {_fmt_item_line(k, qty)}\n"

    kb = []
    if prev.get("can_refine"):
        kb.append([InlineKeyboardButton("✅ CONFIRMAR REFINO", callback_data=f"ref_confirm_{rid}")])
        max_qty = get_max_refine_quantity(pdata, rec)
        if max_qty > 1:
            kb.append([InlineKeyboardButton(f"📚 Refinar em Lote (Max: {max_qty})", callback_data=f"ref_batch_menu_{rid}")])
    else:
        kb.append([InlineKeyboardButton("🔒 Requisitos não atendidos", callback_data="noop")])

    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="ref_main")])
    
    mkey = rec.get("media_key")
    await _safe_send_with_media(context, q.message.chat_id, txt, InlineKeyboardMarkup(kb), media_key=mkey)

async def show_dismantle_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    # 🔒 SEGURANÇA: ID via Auth Central
    uid = get_current_player_id(update, context)
    if not uid: return

    pdata = await player_manager.get_player_data(uid)
    
    page = 0
    if ":page:" in q.data: page = int(q.data.split(':page:')[1])
    
    inv = pdata.get("inventory", {})
    equip = set(pdata.get("equipment", {}).values())
    
    items = []
    for uid_item, d in inv.items():
        if isinstance(d, dict) and uid_item not in equip:
            if crafting_registry.get_recipe_by_item_id(d.get("base_id")):
                items.append((uid_item, d))
    
    items.sort(key=lambda x: x[1].get("display_name", ""))
    
    total_items = len(items)
    total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    cur_items = items[page*ITEMS_PER_PAGE : (page+1)*ITEMS_PER_PAGE]
    
    kb = []
    for iuid, idata in cur_items:
        plus = idata.get("enhancement", idata.get("level", 0))
        plus_txt = f" +{plus}" if plus > 0 else ""
        
        base_id = idata.get("base_id")
        static_data = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {})
        emoji = idata.get("emoji") or static_data.get("emoji", "📦")
        rarity = (idata.get("rarity") or "comum").upper()
        
        btn_text = f"{emoji} {idata.get('display_name')}{plus_txt} [{rarity}]"
        kb.append([InlineKeyboardButton(btn_text, callback_data=f"ref_dismantle_preview:{iuid}")])
        
    nav_row = []
    if page > 0: 
        nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"ref_dismantle_list:page:{page-1}"))
    nav_row.append(InlineKeyboardButton("🔙 Voltar", callback_data="ref_main"))
    if (page+1)*ITEMS_PER_PAGE < total_items: 
        nav_row.append(InlineKeyboardButton("➡️", callback_data=f"ref_dismantle_list:page:{page+1}"))
    
    kb.append(nav_row)
    
    msg = f"♻️ <b>Desmontar</b> (Pág {page+1}/{max(1, total_pages)})\nEscolha um item do inventário para reciclar materiais:"
    if not items: msg += "\n\n<i>(Nenhum equipamento desmontável encontrado no inventário)</i>"
    
    # Usa a função que deleta e envia nova
    await _safe_edit_or_send_with_media(q, context, msg, InlineKeyboardMarkup(kb), media_key='desmontagem_menu_image')

async def show_dismantle_preview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    # 🔒 SEGURANÇA: ID via Auth Central
    uid = get_current_player_id(update, context)
    if not uid: return

    try: iuid = q.data.split(':')[1]
    except: return
    
    pdata = await player_manager.get_player_data(uid)
    item = pdata.get("inventory", {}).get(iuid)
    if not item: return await show_dismantle_list_callback(update, context)

    base_id = item.get("base_id")
    static_data = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {})
    slot_raw = (item.get("slot") or static_data.get("slot") or "outros").lower()
    
    slot_fancy = SLOT_FANCY_TEXT.get(slot_raw, slot_raw.title())
    slot_emoji = SLOT_EMOJI_MAP.get(slot_raw, "🎒")

    target_rarity = item.get("rarity", "comum")
    count_dupes = 0
    inv = pdata.get("inventory", {})
    equip = set(pdata.get("equipment", {}).values())
    
    for u, d in inv.items():
        if isinstance(d, dict) and u not in equip:
            if d.get("base_id") == base_id and d.get("rarity", "comum") == target_rarity:
                count_dupes += 1

    item_line = _fmt_item_details_styled(item)
    txt = (f"<b>CONFIRMAÇÃO DE DESMONTE</b>\n\n"
           f"[ {slot_emoji} {slot_fancy} ] ──────────────\n"
           f" ╰┈➤ {item_line}\n\n"
           f"📉 <b>MATERIAIS RECUPERADOS (Por Unidade)</b>\n")
    
    kb = []
    kb.append([InlineKeyboardButton("✅ 𝐂𝐨𝐧𝐟𝐢𝐫𝐦𝐚𝐫 (1 Unid)", callback_data=f"ref_dismantle_confirm:{iuid}")])
    
    if count_dupes > 1:
        kb.append([InlineKeyboardButton(f"♻️ 𝐃𝐞𝐬𝐦𝐨𝐧𝐭𝐚𝐫 𝐓𝐨𝐝𝐨𝐬 ({count_dupes}x)", 
                                        callback_data=f"ref_dismantle_bulk:{base_id}:{target_rarity}")])

    kb.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="ref_dismantle_list")])
    
    mkey = static_data.get("media_key")
    # Deleta e envia nova
    await _safe_edit_or_send_with_media(q, context, txt, InlineKeyboardMarkup(kb), media_key=mkey)

async def confirm_dismantle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try: await q.delete_message()
    except: pass
    
    uid = get_current_player_id(update, context)
    if not uid:
        await q.answer("Sessão inválida.", show_alert=True)
        return

    iuid = q.data.split(':')[1]
    pdata = await player_manager.get_player_data(uid)
    
    res = await dismantle_engine.start_dismantle(pdata, iuid)
    if isinstance(res, str):
        await context.bot.send_message(q.message.chat_id, res)
        return
        
    dur = res.get("duration_seconds", 60)
    sent = await _safe_send_with_media(context, q.message.chat_id, f"♻️ Desmontando... (~{_fmt_minutes_or_seconds(dur)})")
    
    mid = sent.message_id if sent else None
    
    # Prepara dados do Job com ID seguro
    job_data = {
        "unique_item_id": iuid, 
        "item_name": res.get("item_name"),
        "base_id": res.get("base_id"),
        "rarity": pdata.get("player_state", {}).get("details", {}).get("rarity"), 
        "message_id_to_delete": mid,
        "user_id": uid # <--- CRÍTICO
    }
    
    # Atualiza o state também, por garantia, mas o Job usa o job_data acima
    if "details" in pdata.get("player_state", {}):
        pdata["player_state"]["details"]["message_id_to_delete"] = mid
    await player_manager.save_player_data(uid, pdata)

    context.job_queue.run_once(finish_dismantle_job, dur, chat_id=q.message.chat_id,
                               data=job_data, name=f"dismantle_{uid}")
    
async def confirm_bulk_dismantle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try: await q.delete_message()
    except: pass
    
    uid = get_current_player_id(update, context)
    if not uid:
        await q.answer("Sessão inválida.", show_alert=True)
        return
    
    parts = q.data.split(':') 
    base_id = parts[1]
    rarity_filter = parts[2] if len(parts) > 2 else "comum"
    
    pdata = await player_manager.get_player_data(uid)
    if pdata.get("player_state", {}).get("action") not in (None, "idle"):
        await context.bot.send_message(q.message.chat_id, "Ocupado!")
        return

    inv = pdata.get("inventory", {})
    equip = set(pdata.get("equipment", {}).values())
    
    count_available = 0
    for uniq, data in inv.items():
        if uniq not in equip and isinstance(data, dict):
            if data.get("base_id") == base_id and data.get("rarity", "comum") == rarity_filter:
                count_available += 1
    
    if count_available < 2:
        await context.bot.send_message(q.message.chat_id, "Quantidade insuficiente.")
        return

    res = await dismantle_engine.start_batch_dismantle(pdata, base_id, rarity_filter, count_available)
    if isinstance(res, str):
        await context.bot.send_message(q.message.chat_id, res)
        return

    qty = res.get("qty")
    name = res.get("item_name")
    dur = res.get("duration_seconds", 60)
    
    txt = f"♻️ Desmontando {qty}x <b>{name} [{rarity_filter.title()}]</b>... (~{_fmt_minutes_or_seconds(dur)})"
    sent = await _safe_send_with_media(context, q.message.chat_id, txt)
    
    mid = sent.message_id if sent else None
    
    # Recupera detalhes do state que a engine salvou e adiciona os dados de controle do job
    details = pdata.get("player_state", {}).get("details", {})
    details["message_id_to_delete"] = mid
    details["user_id"] = uid # <--- CRÍTICO
        
    # Salva novamente só para garantir que o message_id fique no banco se o bot reiniciar
    # (Opcional, mas boa prática)
    pdata["player_state"]["details"] = details
    await player_manager.save_player_data(uid, pdata)

    context.job_queue.run_once(finish_bulk_dismantle_job, dur, chat_id=q.message.chat_id,
                               data=details, name=f"dismantle_bulk_{uid}")
                               
async def noop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

# =========================
# REGISTROS
# =========================
refining_main_handler = CallbackQueryHandler(refining_main_callback, pattern=r"^(refining_main|ref_main|ref_main_PAGE_\d+)$")
noop_handler = CallbackQueryHandler(noop_callback, pattern=r"^noop_ref_page$")
ref_select_handler  = CallbackQueryHandler(ref_select_callback,  pattern=r"^ref_sel_[A-Za-z0-9_]+$")
ref_confirm_handler = CallbackQueryHandler(ref_confirm_callback,  pattern=r"^ref_confirm_[A-Za-z0-9_]+$")

ref_batch_menu_handler = CallbackQueryHandler(ref_batch_menu_callback, pattern=r"^ref_batch_menu_")
ref_batch_go_handler = CallbackQueryHandler(ref_batch_confirm_callback, pattern=r"^ref_batch_go_")

dismantle_list_handler = CallbackQueryHandler(show_dismantle_list_callback, pattern=r"^ref_dismantle_list(:page:\d+)?$")
dismantle_preview_handler = CallbackQueryHandler(show_dismantle_preview_callback, pattern=r"^ref_dismantle_preview:[a-f0-9-]+$")
dismantle_confirm_handler = CallbackQueryHandler(confirm_dismantle_callback, pattern=r"^ref_dismantle_confirm:[a-f0-9-]+$")
dismantle_bulk_handler = CallbackQueryHandler(confirm_bulk_dismantle_callback, pattern=r"^ref_dismantle_bulk:.+$")