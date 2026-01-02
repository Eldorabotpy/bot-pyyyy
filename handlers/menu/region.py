# handlers/menu/region.py
# (VERSÃO FINAL: AUTH UNIFICADA + FIX VIAGEM VIP)

import time
import logging
from datetime import datetime, timezone, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

# --- IMPORTS DE MÓDULOS ---
from modules import player_manager, game_data
from modules import file_ids as file_id_manager
from modules.player.premium import PremiumManager
from modules.player import actions as player_actions
from modules.game_data import monsters as monsters_data
from modules.game_data.worldmap import WORLD_MAP
from modules.dungeons.registry import get_dungeon_for_region
from modules.auth_utils import get_current_player_id, requires_login

# --- IMPORTS DE HANDLERS ESPECÍFICOS ---
from modules.world_boss.engine import world_boss_manager
from handlers.christmas_shop import is_event_active
from modules.player.stats import can_see_evolution_menu

logger = logging.getLogger(__name__)

# Fallbacks de Importação Segura
try:
    from modules import file_id_manager as media_ids
except Exception:
    media_ids = file_id_manager

try:
    from handlers.menu.kingdom import show_kingdom_menu
except Exception:
    show_kingdom_menu = None 

try:
    from modules.dungeons.runtime import build_region_dungeon_button
except Exception:
    build_region_dungeon_button = None

# =============================================================================
# Helpers
# =============================================================================

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    """Edita a mensagem se possível, senão envia uma nova (evita erros de mídia)."""
    if query:
        try:
            await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
            return
        except Exception:
            pass
        try:
            await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
            return
        except Exception:
            try: await query.delete_message()
            except Exception: pass
    
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

def _humanize_duration(seconds: int) -> str:
    seconds = int(seconds)
    if seconds >= 60:
        mins = round(seconds / 60)
        return f"{mins} min"
    return f"{seconds} s"

def _get_travel_time_seconds(player_data: dict, dest_key: str) -> int:
    base = 360 
    try:
        premium = PremiumManager(player_data)
        mult = float(premium.get_perk_value("travel_time_multiplier", 1.0))
    except Exception:
        mult = 1.0 
    return max(0, int(round(base * mult)))

async def _auto_finalize_travel_if_due(context: ContextTypes.DEFAULT_TYPE, user_id) -> bool:
    """Finaliza viagem silenciosamente se o tempo já passou."""
    player = await player_manager.get_player_data(user_id) or {}
    state = player.get("player_state") or {}
    if state.get("action") == "travel":
        finish_iso = state.get("finish_time")
        if finish_iso:
            try:
                finish_dt = datetime.fromisoformat(finish_iso)
                if datetime.now(timezone.utc) >= finish_dt:
                    dest = (state.get("details") or {}).get("destination")
                    if dest and dest in (game_data.REGIONS_DATA or {}):
                        player["current_location"] = dest
                    player["player_state"] = {"action": "idle"}
                    await player_manager.save_player_data(user_id, player) 
                    return True
            except Exception: pass 
    return False

# =============================================================================
# Menus de Navegação (Mapa e Info)
# =============================================================================

@requires_login
async def show_travel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # 🔒 SEGURANÇA: ID via Auth Central
    user_id = get_current_player_id(update, context)
    chat_id = query.message.chat_id
    
    player_data = await player_manager.get_player_data(user_id) or {} 
    current_location = player_data.get("current_location", "reino_eldora")
    region_info = (game_data.REGIONS_DATA or {}).get(current_location) or {}
    
    # --- LÓGICA VIP CORRIGIDA ---
    is_vip = False
    try:
        pm = PremiumManager(player_data)
        if pm.is_premium():
            is_vip = True
        else:
            # Fallback para dados legados (Tier existe mas data é None)
            tier = pm.tier
            if tier and tier != 'free' and pm.expiration_date is None:
                # É VIP Permanente Legado? Considera True por enquanto
                is_vip = True
    except: pass

    if is_vip:
        # Ordem personalizada do mapa múndi
        REGION_ORDER = [
            "reino_eldora", "pradaria_inicial", "floresta_sombria", 
            "campos_linho", "pedreira_granito", "mina_ferro", 
            "pantano_maldito", "pico_grifo", "forja_abandonada", 
            "picos_gelados", "deserto_ancestral"
        ]
        all_regions = list((game_data.REGIONS_DATA or {}).keys())
        all_regions.sort(key=lambda k: REGION_ORDER.index(k) if k in REGION_ORDER else 999)
        possible_destinations = [r for r in all_regions if r != current_location]
        caption = f"🗺 🄼🄰🄿🄰 🄼🅄🄽🄳🄸\n📍 Local: {region_info.get('display_name','Unknown')}\n✨ <i>Teletransporte ativo.</i>"
    else:
        possible_destinations = WORLD_MAP.get(current_location, [])
        caption = f"🧭 <b>ＰＬＡＮＯ ＤＥ ＶＩＡＧＥＭ</b>\n📍 Local: {region_info.get('display_name','Unknown')}"

    keyboard = []
    row = []
    for dest_key in possible_destinations:
        dest_info = (game_data.REGIONS_DATA or {}).get(dest_key, {})
        if not dest_info: continue
        d_name = dest_info.get('display_name', dest_key)
        d_emoji = dest_info.get('emoji', '📍')
        row.append(InlineKeyboardButton(f"{d_emoji} {d_name}", callback_data=f"region_{dest_key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row: keyboard.append(row)

    keyboard.append([InlineKeyboardButton("⬅️ 𝐂𝐚𝐧𝐜𝐞𝐥𝐚𝐫", callback_data=f'open_region:{current_location}')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    try: await query.delete_message()
    except: pass

    fd = media_ids.get_file_data("mapa_mundo")
    if fd and fd.get("id"):
        try:
            if (fd.get("type") or "photo").lower() == "video":
                await context.bot.send_video(chat_id=chat_id, video=fd["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
            else:
                await context.bot.send_photo(chat_id=chat_id, photo=fd["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
            return
        except: pass

    await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML")

@requires_login
async def open_region_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = get_current_player_id(update, context)
    chat_id = query.message.chat_id
    
    try: region_key = query.data.split(':')[1]
    except IndexError: region_key = 'reino_eldora'

    player_data = await player_manager.get_player_data(user_id)
    if player_data:
        player_data['current_location'] = region_key
        await player_manager.save_player_data(user_id, player_data) 

    try: await query.delete_message()
    except: pass

    await send_region_menu(context, user_id, chat_id)

@requires_login
async def region_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try: region_key = query.data.split(':')[1]
    except IndexError: return
        
    region_info = game_data.REGIONS_DATA.get(region_key, {})
    info_parts = [f"ℹ️ <b>{region_info.get('display_name', region_key)}</b>", f"<i>{region_info.get('description', '')}</i>\n"]
    
    if region_key == 'reino_eldora':
        info_parts.extend([" 🏇 - 𝐕𝐢𝐚𝐣𝐚𝐫 ", " 🔰 - 𝐆𝐮𝐢𝐥𝐝𝐚", " 🛒 - 𝐌𝐞𝐫𝐜𝐚𝐝𝐨", " ⚒️ - 𝐅𝐨𝐫𝐣𝐚"])
    else:
        if region_info.get('resource'): info_parts.append("- Coleta disponível")
        if monsters_data.MONSTERS_DATA.get(region_key): info_parts.append("- Caça disponível")
        if get_dungeon_for_region(region_key): info_parts.append("- Calabouço")
    
    info_parts.append("\n<b>Criaturas:</b>")
    mons = monsters_data.MONSTERS_DATA.get(region_key, [])
    if not mons: info_parts.append("- <i>Nenhuma.</i>")
    else:
        for m in mons: info_parts.append(f"- {m.get('name', '???')}")
            
    text = "\n".join(info_parts)
    back_cb = 'continue_after_action' if region_key == 'reino_eldora' else f"open_region:{region_key}"
    keyboard = [[InlineKeyboardButton("⬅️ 𝐕𝐎𝐋𝐓𝐀𝐑", callback_data=back_cb)]]
    await _safe_edit_or_send(query, context, query.message.chat_id, text, InlineKeyboardMarkup(keyboard))

# =============================================================================
# Menu Principal da Região
# =============================================================================

async def send_region_menu(context: ContextTypes.DEFAULT_TYPE, user_id, chat_id: int, region_key: str | None = None, player_data: dict | None = None):
    if player_data is None:
        player_data = await player_manager.get_player_data(user_id) or {}
    
    # Sincronia de energia
    if player_actions._apply_energy_autoregen_inplace(player_data):
        await player_manager.save_player_data(user_id, player_data)

    final_region_key = region_key or player_data.get("current_location", "reino_eldora")
    player_data['current_location'] = final_region_key
    region_info = (game_data.REGIONS_DATA or {}).get(final_region_key)

    if not region_info or final_region_key == "reino_eldora":
        if show_kingdom_menu:
            fake_update = Update(update_id=0) 
            await show_kingdom_menu(fake_update, context, player_data=player_data, chat_id=chat_id)
        else:
            await context.bot.send_message(chat_id=chat_id, text="Bem-vindo ao Reino.", parse_mode="HTML")
        return 

    # World Boss
    if world_boss_manager.state["is_active"] and final_region_key == world_boss_manager.state["location"]:
        hud_text = await world_boss_manager.get_battle_hud()
        caption = (f"‼️ **PERIGO IMINENTE** ‼️\nO **Demônio Dimensional** está aqui!\n\n{hud_text}")
        keyboard = [[InlineKeyboardButton("⚔️ ENTRAR NA RAID ⚔️", callback_data='wb_menu')], [InlineKeyboardButton("🗺️ Fugir", callback_data='travel')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            fd = media_ids.get_file_data("boss_raid")
            if fd: await context.bot.send_photo(chat_id, fd["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
            else: await context.bot.send_message(chat_id, caption, reply_markup=reply_markup, parse_mode="HTML")
        except: await context.bot.send_message(chat_id, caption, reply_markup=reply_markup, parse_mode="HTML")
        return

    # Menu Normal
    premium = PremiumManager(player_data)
    stats = await player_manager.get_player_total_stats(player_data)
    
    char_name = player_data.get("character_name", "Aventureiro")
    prof = (player_data.get("profession", {}) or {}).get("type", "adventurer").capitalize()
    
    p_hp, max_hp = int(player_data.get('current_hp', 0)), int(stats.get('max_hp', 1))
    p_mp, max_mp = int(player_data.get('current_mp', 0)), int(stats.get('max_mana', 1))
    p_en, max_en = int(player_data.get('energy', 0)), int(player_manager.get_player_max_energy(player_data))
    p_gold, p_gems = player_manager.get_gold(player_data), player_manager.get_gems(player_data)

    status_hud = (
        f"\n╭─────── [ 𝐏𝐄𝐑𝐅𝐈𝐋 ] ─────➤\n"
        f"│ ╭┈➤ 👤 {char_name}\n"
        f"│ ├┈➤ 🛠 {prof} (Nv. {player_data.get('level',1)})\n"
        f"│ ├┈➤ ❤️ HP: {p_hp}/{max_hp}  💙 MP: {p_mp}/{max_mp}\n"
        f"│ ├┈➤ ⚡ ENERGIA: 🪫{p_en}/🔋{max_en}\n"
        f"│ ╰┈➤ 💰 {p_gold:,}  💎 {p_gems:,}\n"
        f"╰───────────────────────➤"
    )
    
    caption = f"🗺️ Você está em <b>{region_info.get('display_name', 'Região')}</b>.\n╰┈➤ <i>O que deseja fazer?</i>\n{status_hud}"
    keyboard = []
    
    # Botões Especiais
    if final_region_key == 'floresta_sombria': keyboard.append([InlineKeyboardButton("⛺ 𝐀𝐥𝐪𝐮𝐢𝐦𝐢𝐬𝐭𝐚", callback_data='npc_trade:alquimista_floresta')])
    if final_region_key == 'deserto_ancestral':
         row = [InlineKeyboardButton("🧙‍♂️ 𝐌𝐢́𝐬𝐭𝐢𝐜𝐨", callback_data='rune_npc:main')]
         if can_see_evolution_menu(player_data): row.append(InlineKeyboardButton("⛩️ 𝐀𝐬𝐜𝐞𝐧𝐬𝐚̃𝐨", callback_data='open_evolution_menu'))
         keyboard.append(row)
    if final_region_key == 'picos_gelados' and is_event_active(): keyboard.append([InlineKeyboardButton("🎅 𝐍𝐨𝐞𝐥", callback_data="christmas_shop_open")])

    # Combate
    combat = [InlineKeyboardButton("⚔️ 𝐂𝐚𝐜̧𝐚𝐫", callback_data=f"hunt_{final_region_key}")]
    if build_region_dungeon_button: 
        btn = build_region_dungeon_button(final_region_key)
        if btn: combat.append(btn)
    elif get_dungeon_for_region(final_region_key):
        combat.append(InlineKeyboardButton("🏰 𝐂𝐚𝐥𝐚𝐛𝐨𝐮𝐜̧𝐨", callback_data=f"dungeon_open:{final_region_key}"))
    keyboard.append(combat)

    if premium.is_premium():
        keyboard.append([
            InlineKeyboardButton("⏱ 10x", callback_data=f"autohunt_start_10_{final_region_key}"),
            InlineKeyboardButton("⏱ 25x", callback_data=f"autohunt_start_25_{final_region_key}"),
            InlineKeyboardButton("⏱ 35x", callback_data=f"autohunt_start_35_{final_region_key}"),
        ])

    # Coleta
    res_id = region_info.get("resource")
    if res_id:
        req_prof = game_data.get_profession_for_resource(res_id)
        p_prof_data = player_data.get("profession", {})
        my_prof = p_prof_data.get("key") or p_prof_data.get("type")

        if not req_prof or (my_prof and my_prof == req_prof):
            item_info = (game_data.ITEMS_DATA or {}).get(res_id, {})
            item_name = item_info.get("display_name", res_id.replace("_", " ").title())
            keyboard.append([InlineKeyboardButton(f"⛏️ Coletar {item_name}", callback_data=f"collect_{res_id}")])

    keyboard.append([InlineKeyboardButton("🗺️ 𝐌𝐚𝐩𝐚", callback_data="travel"), InlineKeyboardButton("👤 𝐏𝐞𝐫𝐟𝐢𝐥", callback_data="profile")])
    keyboard.append([InlineKeyboardButton("📜 𝐑𝐞𝐩𝐚𝐫𝐚𝐫", callback_data="restore_durability_menu"), InlineKeyboardButton("ℹ️ 𝐈𝐧𝐟𝐨", callback_data=f"region_info:{final_region_key}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        fd = media_ids.get_file_data(f"regiao_{final_region_key}")
        if fd: await context.bot.send_photo(chat_id, fd["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
        else: await context.bot.send_message(chat_id, caption, reply_markup=reply_markup, parse_mode="HTML")
    except: await context.bot.send_message(chat_id, caption, reply_markup=reply_markup, parse_mode="HTML")

async def show_region_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, region_key: str | None = None, player_data: dict | None = None):
    # Lógica limpa para recuperar o ID
    q = getattr(update, "callback_query", None)
    
    uid = get_current_player_id(update, context)
    
    if q:
        await q.answer()
        try: await q.delete_message()
        except Exception: pass
        cid = q.message.chat_id
    else:
        cid = update.effective_chat.id

    if not uid: return

    await _auto_finalize_travel_if_due(context, uid)
    try: await player_manager.try_finalize_timed_action_for_user(uid)
    except: pass
    
    await send_region_menu(context, uid, cid, region_key=region_key, player_data=player_data)
    
# =============================================================================
# Handlers de Ação: Viagem e Coleta
# =============================================================================

@requires_login
async def region_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = get_current_player_id(update, context)
    cid = q.message.chat_id
    
    await _auto_finalize_travel_if_due(context, uid)

    dest = q.data.replace("region_", "", 1)
    pdata = await player_manager.get_player_data(uid)
    if not pdata: return

    cur = pdata.get("current_location", "reino_eldora")
    
    # --- VERIFICAÇÃO VIP CONSISTENTE ---
    is_vip = False
    try:
        pm = PremiumManager(pdata)
        if pm.is_premium():
            is_vip = True
        else:
            tier = pm.tier
            if tier and tier != 'free' and pm.expiration_date is None:
                is_vip = True
    except Exception:
        pass

    is_neighbor = dest in WORLD_MAP.get(cur, []) or cur == dest
    if not is_vip and not is_neighbor:
        await q.answer("Muito longe para viajar a pé.", show_alert=True)
        return

    # Calcula custo de viagem
    cost = int(((game_data.REGIONS_DATA or {}).get(dest, {}) or {}).get("travel_cost", 0))
    
    current_energy = int(pdata.get("energy", 0))
    if cost > 0 and current_energy < cost:
        await q.answer(f"Energia insuficiente. Precisa de {cost}⚡.", show_alert=True)
        return

    if cost > 0:
        player_manager.spend_energy(pdata, cost)

    secs = _get_travel_time_seconds(pdata, dest)

    # Viagem Instantânea
    if secs <= 0:
        pdata["current_location"] = dest
        pdata["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(uid, pdata)
        
        try: await q.delete_message()
        except: pass
        
        await send_region_menu(context, uid, cid)
        return

    # Viagem com Tempo
    finish = datetime.now(timezone.utc) + timedelta(seconds=secs)
    pdata["player_state"] = {
        "action": "travel", 
        "finish_time": finish.isoformat(), 
        "details": {"destination": dest}
    }
    await player_manager.save_player_data(uid, pdata)

    try: await q.delete_message()
    except: pass
    
    human = _humanize_duration(secs)
    dest_name = (game_data.REGIONS_DATA or {}).get(dest, {}).get("display_name", dest)
    txt = f"🧭 Viajando para <b>{dest_name}</b>… (~{human})"
    
    await context.bot.send_message(chat_id=cid, text=txt, parse_mode="HTML")
    context.job_queue.run_once(finish_travel_job, when=secs, data={"player_id": str(uid), "dest": dest}, chat_id=cid, name=f"finish_travel_{uid}")
    
async def finish_travel_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    # Garante que pegamos o ID corretamente (seja int antigo ou string novo)
    job_data = job.data or {}
    uid = job_data.get("player_id") or str(job.user_id)
    cid = job.chat_id
    dest = job_data.get("dest")

    pdata = await player_manager.get_player_data(uid)
    if pdata and pdata.get("player_state", {}).get("action") == "travel":
        pdata["current_location"] = dest
        pdata["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(uid, pdata)
    
    # Injeta sessão manual se necessário (Hack de JobQueue)
    if context.user_data is not None:
        context.user_data['logged_player_id'] = str(uid)
        
    await send_region_menu(context, uid, cid)
    
# --- START COLLECTION LOGIC ---
@requires_login
async def collect_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    from handlers.job_handler import finish_collection_job 
    await q.answer()
    
    uid = get_current_player_id(update, context)
    cid = q.message.chat_id
    res_id = (q.data or "").replace("collect_", "", 1)
    
    pdata = await player_manager.get_player_data(uid)
    if not pdata: return

    prem = PremiumManager(pdata)
    cost = int(prem.get_perk_value("gather_energy_cost", 1))
    if int(pdata.get("energy", 0)) < cost:
        await q.answer(f"Sem energia ({cost}⚡).", show_alert=True); return

    player_manager.spend_energy(pdata, cost)
    
    req_prof = game_data.get_profession_for_resource(res_id)
    p_res = (game_data.PROFESSIONS_DATA.get(req_prof, {}) or {}).get('resources', {})
    item_yielded = p_res.get(res_id, res_id)

    base_secs = int(getattr(game_data, "COLLECTION_TIME_MINUTES", 1) * 60)
    spd = float(prem.get_perk_value("gather_speed_multiplier", 1.0))
    dur = max(1, int(base_secs / max(0.25, spd)))
    
    finish = datetime.now(timezone.utc) + timedelta(seconds=dur)
    pdata['player_state'] = {
        'action': 'collecting',
        'finish_time': finish.isoformat(), 
        'details': {'resource_id': res_id, 'item_id_yielded': item_yielded, 'quantity': 1}
    }
    player_manager.set_last_chat_id(pdata, cid)
    
    human = _humanize_duration(dur)
    cap = f"⛏️ <b>Coletando...</b>\n⏳ Tempo: {human}"
    try: await q.delete_message()
    except: pass
    msg = await context.bot.send_message(cid, cap, parse_mode="HTML")
    
    if msg: pdata['player_state']['details']['collect_message_id'] = msg.message_id
    await player_manager.save_player_data(uid, pdata)

    context.job_queue.run_once(
        finish_collection_job,
        when=dur,
        data={'user_id': uid, 'chat_id': cid, 'resource_id': res_id, 'item_id_yielded': item_yielded, 'quantity': 1, 'message_id': msg.message_id},
        name=f"collect_{uid}"
    )

# =============================================================================
# Durabilidade e Registro
# =============================================================================

@requires_login
async def show_restore_durability_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = get_current_player_id(update, context)
    pdata = await player_manager.get_player_data(uid) or {}
    
    lines = ["<b>📜 Restaurar Durabilidade</b>\n"]
    lines.append("<i>Restaura TODOS os itens equipados consumindo apenas 1 Pergaminho.</i>\n")

    inv, equip = pdata.get("inventory", {}), pdata.get("equipment", {})
    def _d(raw): 
        try: return int(raw[0]), int(raw[1])
        except: return 20, 20

    items_broken_count = 0
    for slot, uid_item in equip.items():
        if not uid_item: continue
        inst = inv.get(uid_item)
        if isinstance(inst, dict):
            cur, mx = _d(inst.get("durability"))
            if cur < mx:
                items_broken_count += 1
                nm = (game_data.ITEMS_DATA or {}).get(inst.get("base_id"), {}).get("display_name", "Item")
                lines.append(f"• {nm} <b>({cur}/{mx})</b>")
    
    kb = []
    if items_broken_count > 0:
        kb.append([InlineKeyboardButton(f"✨ REPARAR TUDO (Gasta 1x 📜)", callback_data="rd_fix_all")])
    else:
        lines.append("✅ <i>Todos os equipamentos estão perfeitos.</i>")
    
    loc = pdata.get("current_location", "reino_eldora")
    back = 'continue_after_action' if loc == 'reino_eldora' else f"open_region:{loc}"
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data=back)])
    
    await _safe_edit_or_send(q, context, q.message.chat_id, "\n".join(lines), InlineKeyboardMarkup(kb))

@requires_login
async def fix_item_durability(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = get_current_player_id(update, context)
    
    target = q.data.replace("rd_fix_", "", 1)
    if target != "all":
        await q.answer("Opção antiga inválida. Use 'Reparar Tudo'.", show_alert=True)
        await show_restore_durability_menu(update, context)
        return

    pdata = await player_manager.get_player_data(uid)
    from modules.profession_engine import restore_all_equipped_durability
    res = await restore_all_equipped_durability(pdata)
    
    if isinstance(res, dict) and res.get("error"):
        await q.answer(res["error"], show_alert=True)
    else:
        count = res.get("count", 0)
        await player_manager.save_player_data(uid, pdata)
        await q.answer(f"✨ Sucesso! {count} itens reparados!", show_alert=True)
    
    await show_restore_durability_menu(update, context)

# REGISTRO DOS HANDLERS
region_handler = CallbackQueryHandler(region_callback, pattern=r"^region_[A-Za-z0-9_]+$")
travel_handler = CallbackQueryHandler(show_travel_menu, pattern=r"^travel$")
collect_handler = CallbackQueryHandler(collect_callback, pattern=r"^collect_[A-Za-z0-9_]+$")
open_region_handler = CallbackQueryHandler(open_region_callback, pattern=r"^open_region:")
restore_durability_menu_handler = CallbackQueryHandler(show_restore_durability_menu, pattern=r"^restore_durability_menu$")
restore_durability_fix_handler = CallbackQueryHandler(fix_item_durability, pattern=r"^rd_fix_all$")
region_info_handler = CallbackQueryHandler(region_info_callback, pattern=r"^region_info:.*$")