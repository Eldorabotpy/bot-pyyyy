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
from modules.game_data import attributes
from modules import game_data, player_manager, file_ids
from modules.refining_engine import preview_refine, start_refine, finish_refine
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

# =====================================================
# 1. CORE LOGIC - REFINO
# =====================================================
async def execute_refine_logic(
    user_id: int, 
    chat_id: int, 
    context: ContextTypes.DEFAULT_TYPE, 
    message_id_to_delete: int = None
):
    """Finaliza o refino: dá os itens e notifica."""
    if message_id_to_delete:
        try: await context.bot.delete_message(chat_id, message_id_to_delete)
        except: pass

    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return

    res = await finish_refine(pdata)
    
    if isinstance(res, str):
        await context.bot.send_message(chat_id, f"❗ {res}")
        return
    if not res: return

    outs = res.get("outputs") or {}
    lines = ["✅ <b>Refino concluído!</b>", "Você obteve:"]
    for k, v in outs.items():
        lines.append(f"• {_fmt_item_line(k, v)}")
    
    caption = "\n".join(lines)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="ref_main")]])

    mkey = None
    if outs:
        iid = list(outs.keys())[0]
        mkey = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(iid, {}).get("media_key")

    await _safe_send_with_media(context, chat_id, caption, kb, media_key=mkey)


# =====================================================
# 2. CORE LOGIC - DESMONTE (SINGLE)
# =====================================================
async def execute_dismantle_logic(
    user_id: int,
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    job_details: dict,
    message_id_to_delete: int = None
):
    """Finaliza o desmonte único."""
    if message_id_to_delete:
        try: await context.bot.delete_message(chat_id, message_id_to_delete)
        except: pass

    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return

    result = await dismantle_engine.finish_dismantle(pdata, job_details)

    if isinstance(result, str):
        await context.bot.send_message(chat_id, f"❗ Erro desmonte: {result}")
        return

    item_name, returned_materials = result
    
    # Nota: O engine já salva os dados, mas garantimos aqui se necessário
    # await player_manager.save_player_data(user_id, pdata)

    lines = [f"♻️ <b>{item_name}</b> desmontado!", "\n📉 <b>Recuperado:</b>"]
    if not returned_materials: lines.append(" ╰┈➤ <i>Nada (Item sem receita?)</i>")
    else:
        for k, v in returned_materials.items():
            lines.append(f" ╰┈➤ {_fmt_item_line(k, v)}")

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="ref_main")]])
    await context.bot.send_message(chat_id, "\n".join(lines), parse_mode="HTML", reply_markup=kb)


# =====================================================
# 3. CORE LOGIC - DESMONTE EM MASSA (BULK)
# =====================================================
async def execute_bulk_dismantle_logic(
    user_id: int,
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    job_details: dict,
    message_id_to_delete: int = None
):
    """
    Finaliza o desmonte em massa USANDO O ENGINE NOVO.
    """
    if message_id_to_delete:
        try: await context.bot.delete_message(chat_id, message_id_to_delete)
        except: pass

    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return
    
    # CHAMA O MOTOR NOVO (Isso garante que a matemática seja a mesma do single)
    result = await dismantle_engine.finish_dismantle_batch(pdata, job_details)
    
    if isinstance(result, str):
        await context.bot.send_message(chat_id, f"❗ Erro no desmonte: {result}")
        return

    item_name, rewards = result # O engine já salvou e entregou os itens

    # Monta a mensagem visual
    count = job_details.get("qty_dismantling", 1)
    
    lines = [f"♻️ <b>Desmonte em Massa Concluído!</b>", f"Foram destruídos {count}x <b>{item_name}</b>.", "\n📉 <b>Total Recuperado:</b>"]
    
    if not rewards: 
        lines.append(" ╰┈➤ <i>Nada.</i>")
    else:
        for k, v in rewards.items():
            lines.append(f" ╰┈➤ {_fmt_item_line(k, v)}")

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="ref_main")]])
    await context.bot.send_message(chat_id, "\n".join(lines), parse_mode="HTML", reply_markup=kb)


# =====================================================
# 4. JOB WRAPPERS
# =====================================================
async def finish_refine_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    if not job: return
    await execute_refine_logic(
        user_id=job.user_id,
        chat_id=job.chat_id,
        context=context,
        message_id_to_delete=job.data.get("message_id_to_delete")
    )

async def finish_dismantle_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    if not job: return
    await execute_dismantle_logic(
        user_id=job.user_id,
        chat_id=job.chat_id,
        context=context,
        job_details=job.data,
        message_id_to_delete=job.data.get("message_id_to_delete")
    )

async def finish_bulk_dismantle_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    if not job: return
    await execute_bulk_dismantle_logic(
        user_id=job.user_id,
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
    """
    Formata o item com visual rico e mapeamento COMPLETO de atributos.
    Ex: 『[19/20] 🔪 Adaga Sorrateira [12][Lendario]: ☠️ +12, 🍀 +1 』
    """
    # 1. Durabilidade
    cur_dur = item_data.get("durability")
    max_dur = item_data.get("max_durability")
    dur_str = f"[{cur_dur}/{max_dur}] " if (cur_dur is not None and max_dur) else ""

    # 2. Classe (Emoji)
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

    # 3. Dados Básicos
    name = item_data.get("display_name", "Item")
    item_emoji = item_data.get("emoji", "") 
    
    # 4. Raridade e Nível
    rarity = (item_data.get("rarity") or "comum").title()
    lvl = item_data.get("enhancement", item_data.get("level", 0))
    lvl_str = f" [+ {lvl}]" if lvl > 0 else ""

    # 5. Atributos - O GRANDE DICIONÁRIO DE ÍCONES
    # Mapeia Inglês, Português e variações para o mesmo emoji
    stat_icons = {
        # --- HP / VIDA ---
        "vida": "❤️", "hp": "❤️", "max_hp": "❤️", "health": "❤️", "vitalidade": "❤️", "vit": "❤️",
        
        # --- MANA / MP ---
        "mana": "💧", "max_mana": "💧", "mp": "💧", "max_mp": "💧", "inteligencia": "🧠", "intelligence": "🧠", "int": "🧠",

        # --- ATAQUE / FORÇA ---
        "ataque": "⚔️", "attack": "⚔️", "atk": "⚔️", "dano": "⚔️", "damage": "⚔️",
        "forca": "💪", "strength": "💪", "str": "💪", "fisico": "💪",

        # --- DEFESA / RESISTÊNCIA ---
        "defesa": "🛡️", "defense": "🛡️", "def": "🛡️", "armadura": "🛡️", "armor": "🛡️",
        "resistencia": "🛡️", "resistance": "🛡️", "res": "🛡️", "block": "🛡️",

        # --- VELOCIDADE / AGILIDADE ---
        "agilidade": "🏃", "agility": "🏃", "agi": "🏃",
        "iniciativa": "⚡", "initiative": "⚡", "ini": "⚡", "velocidade": "⚡",

        # --- SORTE / CRITICO ---
        "sorte": "🍀", "luck": "🍀", "lucky": "🍀", "luk": "🍀",
        "critico": "💥", "crit": "💥", "crit_chance": "💥", "crit_chance_flat": "💥",
        "dano_critico": "🩸", "crit_damage": "🩸", "crit_damage_mult": "🩸",

        # --- ESPECIAIS DE CLASSE ---
        "furia": "💢", "rage": "💢",
        "precisao": "🎯", "mira": "🎯", "precision": "🎯", "accuracy": "🎯",
        "fe": "🙏", "faith": "🙏",
        "carisma": "👄", "charisma": "👄",
        "bushido": "👹", "honra": "👹",
        "foco": "🧿", "focus": "🧿", "chi": "☯️",
        "letalidade": "☠️", "lethality": "☠️", "morte": "☠️",
        "cura": "❤️‍🩹", "heal": "❤️‍🩹", "heal_potency": "❤️‍🩹",
        "magia": "🔮", "magic": "🔮", "magic_attack": "🔮", "poder_magico": "🔮",

        # --- OUTROS / SECUNDÁRIOS ---
        "esquiva": "💨", "dodge": "💨",
        "penetracao": "🔩", "penetration": "🔩", "armor_penetration": "🔩",
        "roubo_vida": "🧛", "lifesteal": "🧛", "vampirismo": "🧛",
        "tenacidade": "🏰", "tenacity": "🏰"
    }

    stats_str_list = []
    
    # Combina Stats Base + Encantamentos
    stats = dict(item_data.get("stats") or {})
    ench = item_data.get("enchantments", {})
    
    for k, v in ench.items():
        val = v["value"] if isinstance(v, dict) and "value" in v else (v if isinstance(v, (int, float)) else 0)
        if val > 0: stats[k] = stats.get(k, 0) + val

    ignored_keys = {"durability", "max_durability", "level", "enhancement"}
    
    for key, val in stats.items():
        # Normaliza a chave: remove espaços, tudo minúsculo
        k_clean = str(key).lower().strip().replace(" ", "_")
        
        if k_clean in ignored_keys or not isinstance(val, (int, float)) or val == 0: continue
        
        # Busca o ícone
        icon = stat_icons.get(k_clean, "🔹")
        
        if icon == "🔹": 
            # Se não achou ícone, mostra o nome original (ex: "Luck") para debug visual, mas mantém o layout
            k_display = str(key).replace("_", " ").title()
            stats_str_list.append(f"{icon} {k_display} +{val}")
        else:
            # Se achou o ícone, mostra só o ícone + valor (Layout Limpo)
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
                    await context.bot.send_video(chat_id, fd["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
                else:
                    await context.bot.send_photo(chat_id, fd["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
                return
            except: pass
    await context.bot.send_message(chat_id, caption, reply_markup=reply_markup, parse_mode="HTML")

async def _safe_edit_or_send_with_media(query, context, caption, reply_markup=None, media_key="refino_universal"):
    try: await query.delete_message()
    except: pass
    return await _safe_send_with_media(context, query.message.chat_id, caption, reply_markup, media_key=media_key)


# =========================
# HANDLERS CALLBACKS
# =========================

async def refining_main_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    
    page = 1
    if "_PAGE_" in q.data: page = int(q.data.split('_PAGE_')[-1])

    pdata = await player_manager.get_player_data(uid)
    recipes = []
    refining_recipes = getattr(game_data, "REFINING_RECIPES", {}) or {}
    
    for rid, rec in refining_recipes.items():
        prev = preview_refine(rid, pdata)
        if prev:
            t = _fmt_minutes_or_seconds(int(prev.get("duration_seconds", 0)))
            recipes.append({"id": rid, "data": rec, "prev": prev, "time": t})

    total_p = max(1, math.ceil(len(recipes) / 8))
    page = max(1, min(page, total_p))
    current = recipes[(page-1)*8 : page*8]

    lines = ["🛠️ <b>Refino & Desmontagem</b>\n", f"Pág {page}/{total_p}"]
    kb = [[InlineKeyboardButton("♻️ Desmontar Equipamento", callback_data="ref_dismantle_list")]]
    
    for r in current:
        tag = "✅" if r["prev"].get("can_refine") else "⛔"
        lines.append(f"{tag} {r['data'].get('display_name')} | ⏳ {r['time']}")
        kb.append([InlineKeyboardButton(r['data'].get('display_name'), callback_data=f"ref_sel_{r['id']}")])

    nav = []
    if page > 1: nav.append(InlineKeyboardButton("◀️", callback_data=f"ref_main_PAGE_{page-1}"))
    nav.append(InlineKeyboardButton("⟳", callback_data="noop_ref_page"))
    if page < total_p: nav.append(InlineKeyboardButton("▶️", callback_data=f"ref_main_PAGE_{page+1}"))
    if nav: kb.append(nav)
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="continue_after_action")])

    await _safe_edit_or_send_with_media(q, context, "\n".join(lines), InlineKeyboardMarkup(kb))

async def ref_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    rid = q.data.replace("ref_sel_", "", 1)
    pdata = await player_manager.get_player_data(q.from_user.id)
    prev = preview_refine(rid, pdata)
    
    if not prev: return
    
    ins = "\n".join(_fmt_item_line(k, v) for k, v in (prev.get("inputs") or {}).items())
    outs = "\n".join(_fmt_item_line(k, v) for k, v in (prev.get("outputs") or {}).items())
    t = _fmt_minutes_or_seconds(int(prev.get("duration_seconds", 0)))
    
    recipe_name = (getattr(game_data, "REFINING_RECIPES", {}).get(rid,{}) or {}).get('display_name', rid)
    txt = f"🛠️ <b>{recipe_name}</b>\n⏳ {t}\n\n📥 <b>Entrada:</b>\n{ins}\n\n📦 <b>Saída:</b>\n{outs}"
    
    kb = []
    if prev.get("can_refine"): kb.append([InlineKeyboardButton("✅ Refinar", callback_data=f"ref_confirm_{rid}")])
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="ref_main")])
    
    await _safe_edit_or_send_with_media(q, context, txt, InlineKeyboardMarkup(kb))

async def ref_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    rid = q.data.replace("ref_confirm_", "", 1)
    
    pdata = await player_manager.get_player_data(uid)
    if pdata.get("player_state", {}).get("action") not in (None, "idle"):
        await q.answer("Ocupado!", show_alert=True); return

    res = await start_refine(pdata, rid)
    if isinstance(res, str):
        await q.answer(res, show_alert=True); return

    secs = int(res.get("duration_seconds", 60))
    t = _fmt_minutes_or_seconds(secs)
    title = (getattr(game_data, "REFINING_RECIPES", {}).get(rid, {}) or {}).get("display_name", rid)
    
    sent = await _safe_edit_or_send_with_media(q, context, f"🔧 Refinando <b>{title}</b>... (~{t})")
    mid = sent.message_id if sent else None
    
    context.job_queue.run_once(finish_refine_job, secs, user_id=uid, chat_id=q.message.chat_id,
                               data={"rid": rid, "message_id_to_delete": mid}, name=f"refining:{uid}")
    await q.answer()

async def show_dismantle_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    pdata = await player_manager.get_player_data(uid)
    
    page = 0
    if ":page:" in q.data: page = int(q.data.split(':page:')[1])
    
    inv = pdata.get("inventory", {})
    equip = set(pdata.get("equipment", {}).values())
    
    items = []
    for uid_item, d in inv.items():
        if isinstance(d, dict) and uid_item not in equip:
            # Só lista itens que tem receita de desmonte
            if crafting_registry.get_recipe_by_item_id(d.get("base_id")):
                items.append((uid_item, d))
    
    # Ordena por Nome
    items.sort(key=lambda x: x[1].get("display_name", ""))
    
    # Paginação
    total_items = len(items)
    total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    cur_items = items[page*ITEMS_PER_PAGE : (page+1)*ITEMS_PER_PAGE]
    
    kb = []
    for iuid, idata in cur_items:
        plus = idata.get("enhancement", idata.get("level", 0))
        plus_txt = f" +{plus}" if plus > 0 else ""
        
        # Emoji e Raridade
        base_id = idata.get("base_id")
        static_data = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {})
        emoji = idata.get("emoji") or static_data.get("emoji", "📦")
        rarity = (idata.get("rarity") or "comum").upper()
        
        btn_text = f"{emoji} {idata.get('display_name')}{plus_txt} [{rarity}]"
        kb.append([InlineKeyboardButton(btn_text, callback_data=f"ref_dismantle_preview:{iuid}")])
        
    # --- BARRA DE NAVEGAÇÃO UNIFICADA ---
    nav_row = []
    
    # 1. Botão Anterior (⬅️)
    if page > 0: 
        nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"ref_dismantle_list:page:{page-1}"))
    
    # 2. Botão Voltar ao Menu (🔙 Voltar) - Fica no meio
    nav_row.append(InlineKeyboardButton("🔙 Voltar", callback_data="ref_main"))
    
    # 3. Botão Próximo (➡️)
    if (page+1)*ITEMS_PER_PAGE < total_items: 
        nav_row.append(InlineKeyboardButton("➡️", callback_data=f"ref_dismantle_list:page:{page+1}"))
    
    # Adiciona a linha de navegação ao teclado
    kb.append(nav_row)
    
    msg = f"♻️ <b>Desmontar</b> (Pág {page+1}/{max(1, total_pages)})\nEscolha um item do inventário para reciclar materiais:"
    if not items: msg += "\n\n<i>(Nenhum equipamento desmontável encontrado no inventário)</i>"
    
    await _safe_edit_or_send_with_media(q, context, msg, InlineKeyboardMarkup(kb), media_key='desmontagem_menu_image')

async def show_dismantle_preview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    try: uid, iuid = q.from_user.id, q.data.split(':')[1]
    except: return
    
    pdata = await player_manager.get_player_data(uid)
    item = pdata.get("inventory", {}).get(iuid)
    if not item: return await show_dismantle_list_callback(update, context)

    # --- LÓGICA VISUAL (CABEÇALHO) ---
    base_id = item.get("base_id")
    # Busca slot no item ou no game_data
    static_data = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {})
    slot_raw = (item.get("slot") or static_data.get("slot") or "outros").lower()
    
    slot_fancy = SLOT_FANCY_TEXT.get(slot_raw, slot_raw.title()) # Usa seu dict de fontes
    slot_emoji = SLOT_EMOJI_MAP.get(slot_raw, "🎒")

    # --- LÓGICA DE DUPLICATAS COM RARIDADE ---
    target_rarity = item.get("rarity", "comum")
    count_dupes = 0
    inv = pdata.get("inventory", {})
    equip = set(pdata.get("equipment", {}).values())
    
    for u, d in inv.items():
        if isinstance(d, dict) and u not in equip:
            # SÓ CONTA SE ID E RARIDADE FOREM IGUAIS
            if d.get("base_id") == base_id and d.get("rarity", "comum") == target_rarity:
                count_dupes += 1

    # --- MONTAGEM DO TEXTO ---
    item_line = _fmt_item_details_styled(item)
    txt = (f"<b>CONFIRMAÇÃO DE DESMONTE</b>\n\n"
           f"[ {slot_emoji} {slot_fancy} ] ──────────────\n"
           f" ╰┈➤ {item_line}\n\n"
           f"📉 <b>MATERIAIS RECUPERADOS (Por Unidade)</b>\n")
    
    # (Adicione sua lógica de materials/recipe aqui...)
    rec = crafting_registry.get_recipe_by_item_id(base_id)
    # ... se não tiver receita, use calculate_rarity_fallback(target_rarity)
    
    # --- BOTÕES ---
    kb = []
    kb.append([InlineKeyboardButton("✅ 𝐂𝐨𝐧𝐟𝐢𝐫𝐦𝐚𝐫 (1 Unid)", callback_data=f"ref_dismantle_confirm:{iuid}")])
    
    if count_dupes > 1:
        # PASSANDO RARIDADE NO CALLBACK
        kb.append([InlineKeyboardButton(f"♻️ 𝐃𝐞𝐬𝐦𝐨𝐧𝐭𝐚𝐫 𝐓𝐨𝐝𝐨𝐬 ({count_dupes}x)", 
                                        callback_data=f"ref_dismantle_bulk:{base_id}:{target_rarity}")])

    kb.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="ref_dismantle_list")])
    
    mkey = static_data.get("media_key")
    await _safe_edit_or_send_with_media(q, context, txt, InlineKeyboardMarkup(kb), media_key=mkey)

async def confirm_dismantle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid, iuid = q.from_user.id, q.data.split(':')[1]
    pdata = await player_manager.get_player_data(uid)
    
    res = await dismantle_engine.start_dismantle(pdata, iuid)
    if isinstance(res, str):
        await q.answer(res, show_alert=True); return
        
    dur = res.get("duration_seconds", 60)
    sent = await _safe_edit_or_send_with_media(q, context, f"♻️ Desmontando... (~{_fmt_minutes_or_seconds(dur)})")
    
    mid = sent.message_id if sent else None
    
    job_data = {
        "unique_item_id": iuid, 
        "item_name": res.get("item_name"),
        "base_id": res.get("base_id"),
        "rarity": pdata.get("player_state", {}).get("details", {}).get("rarity"), # Garante raridade
        "message_id_to_delete": mid
    }
    
    # Atualiza details com message_id
    if "details" in pdata["player_state"]:
        pdata["player_state"]["details"]["message_id_to_delete"] = mid
    await player_manager.save_player_data(uid, pdata)

    context.job_queue.run_once(finish_dismantle_job, dur, user_id=uid, chat_id=q.message.chat_id,
                               data=job_data, name=f"dismantle_{uid}")
    await q.answer()

async def confirm_bulk_dismantle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    
    # Lê ID e RARIDADE do botão
    parts = q.data.split(':') # ref_dismantle_bulk : ID : RARIDADE
    base_id = parts[1]
    rarity_filter = parts[2] if len(parts) > 2 else "comum"
    
    pdata = await player_manager.get_player_data(uid)
    if pdata.get("player_state", {}).get("action") not in (None, "idle"):
        await q.answer("Ocupado!", show_alert=True); return

    # Conta novamente (Segurança)
    inv = pdata.get("inventory", {})
    equip = set(pdata.get("equipment", {}).values())
    count_available = 0
    for uniq, data in inv.items():
        if uniq not in equip and isinstance(data, dict):
            if data.get("base_id") == base_id and data.get("rarity", "comum") == rarity_filter:
                count_available += 1
    
    if count_available < 2:
        await q.answer("Quantidade insuficiente.", show_alert=True); return

    # CHAMA O ENGINE COM A RARIDADE
    res = await dismantle_engine.start_batch_dismantle(pdata, base_id, rarity_filter, count_available)
    
    if isinstance(res, str):
        await q.answer(res, show_alert=True); return

    # Notificação final
    qty = res.get("qty")
    name = res.get("item_name")
    dur = res.get("duration_seconds", 60)
    
    txt = f"♻️ Desmontando {qty}x <b>{name} [{rarity_filter.title()}]</b>... (~{_fmt_minutes_or_seconds(dur)})"
    sent = await _safe_edit_or_send_with_media(q, context, txt)
    
    mid = sent.message_id if sent else None
    pdata["player_state"]["details"]["message_id_to_delete"] = mid
    await player_manager.save_player_data(uid, pdata)

    context.job_queue.run_once(finish_bulk_dismantle_job, dur, user_id=uid, chat_id=q.message.chat_id,
                               data=pdata["player_state"]["details"], name=f"dismantle_bulk_{uid}")
    await q.answer()

async def noop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

# Registros
refining_main_handler = CallbackQueryHandler(refining_main_callback, pattern=r"^(refining_main|ref_main|ref_main_PAGE_\d+)$")
noop_handler = CallbackQueryHandler(noop_callback, pattern=r"^noop_ref_page$")
ref_select_handler  = CallbackQueryHandler(ref_select_callback,  pattern=r"^ref_sel_[A-Za-z0-9_]+$")
ref_confirm_handler = CallbackQueryHandler(ref_confirm_callback,  pattern=r"^ref_confirm_[A-Za-z0-9_]+$")
dismantle_list_handler = CallbackQueryHandler(show_dismantle_list_callback, pattern=r"^ref_dismantle_list(:page:\d+)?$")
dismantle_preview_handler = CallbackQueryHandler(show_dismantle_preview_callback, pattern=r"^ref_dismantle_preview:[a-f0-9-]+$")
dismantle_confirm_handler = CallbackQueryHandler(confirm_dismantle_callback, pattern=r"^ref_dismantle_confirm:[a-f0-9-]+$")
# Alteramos o regex para ".+" (qualquer coisa), aceitando hifens e maiúsculas
dismantle_bulk_handler = CallbackQueryHandler(confirm_bulk_dismantle_callback, pattern=r"^ref_dismantle_bulk:.+$")