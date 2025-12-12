# handlers/menu/region.py
# (VERSÃO FINAL LIMPA: Sem duplicações e Sem Erro de Import)

import time
import logging
from datetime import datetime, timezone, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

# --- IMPORTS DE MÓDULOS ---
from modules import player_manager, game_data
from modules import file_ids as file_id_manager
from modules.player.premium import PremiumManager
from modules.game_data import monsters as monsters_data
from modules.game_data.worldmap import WORLD_MAP
from modules.dungeons.registry import get_dungeon_for_region

# --- IMPORTS DE HANDLERS ESPECÍFICOS ---
from handlers.world_boss.engine import world_boss_manager, BOSS_STATS
from handlers.christmas_shop import is_event_active

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

async def _auto_finalize_travel_if_due(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
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

async def show_travel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    player_data = await player_manager.get_player_data(user_id) or {} 
    current_location = player_data.get("current_location", "reino_eldora")
    region_info = (game_data.REGIONS_DATA or {}).get(current_location) or {}
    
    is_vip = False
    try: is_vip = PremiumManager(player_data).is_premium()
    except Exception: pass

    if is_vip:
        REGION_ORDER = [
            "reino_eldora", "pradaria_inicial", "floresta_sombria", "campos_linho",
            "pedreira_granito", "mina_ferro", "pantano_maldito", "pico_grifo",
            "forja_abandonada", "picos_gelados", "deserto_ancestral"
        ]
        all_regions = list((game_data.REGIONS_DATA or {}).keys())
        all_regions.sort(key=lambda k: REGION_ORDER.index(k) if k in REGION_ORDER else 999)
        possible_destinations = [r for r in all_regions if r != current_location]
        
        caption = (
            f"🗺 <b>🄼🄰🄿🄰 🄼🅄🄽🄳🄸 (VIP)</b> 🗺\n"
            f"Você está em <b>{region_info.get('display_name','Desconhecido')}</b>.\n\n"
            f"Como viajante de elite, a <b>Pedra Dimensional</b> permite viajar para qualquer destino!"
        )
    else:
        possible_destinations = WORLD_MAP.get(current_location, [])
        caption = (
            f"Você está em <b>{region_info.get('display_name','Desconhecido')}</b>.\n"
            f"Para onde deseja viajar?"
        )

    keyboard = []
    for dest_key in possible_destinations:
        dest_info = (game_data.REGIONS_DATA or {}).get(dest_key, {})
        if not dest_info: continue
        button = InlineKeyboardButton(
            f"{dest_info.get('emoji', '')} {dest_info.get('display_name', dest_key)}",
            callback_data=f"region_{dest_key}",
        )
        keyboard.append([button])

    keyboard.append([InlineKeyboardButton("⬅️ 𝐕𝐎𝐋𝐓𝐀𝐑", callback_data=f'open_region:{current_location}')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    try: await query.delete_message()
    except Exception: pass

    fd = media_ids.get_file_data("mapa_mundo")
    if fd and fd.get("id"):
        try:
            if (fd.get("type") or "photo").lower() == "video":
                await context.bot.send_video(chat_id=chat_id, video=fd["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
            else:
                await context.bot.send_photo(chat_id=chat_id, photo=fd["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
            return
        except Exception: pass

    await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML")

async def open_region_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    
    try: region_key = query.data.split(':')[1]
    except IndexError: region_key = 'reino_eldora'

    player_data = await player_manager.get_player_data(user_id)
    if player_data:
        player_data['current_location'] = region_key
        await player_manager.save_player_data(user_id, player_data) 

    try: await query.delete_message()
    except Exception: pass

    await send_region_menu(context, user_id, chat_id)

async def region_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try: region_key = query.data.split(':')[1]
    except IndexError: return
        
    region_info = game_data.REGIONS_DATA.get(region_key, {})
    
    info_parts = [
        f"ℹ️ <b>Sobre: {region_info.get('display_name', region_key)}</b>",
        f"<i>{region_info.get('description', 'Nenhuma descrição.')}</i>\n",
        "<b>Ações Possíveis:</b>"
    ]
    
    if region_key == 'reino_eldora':
        info_parts.extend([" 🏇 - 𝐕𝐢𝐚𝐣𝐚𝐫 ", " 🔰 - 𝐆𝐮𝐢𝐥𝐝𝐚", " 🛒 - 𝐌𝐞𝐫𝐜𝐚𝐝𝐨", " ⚒️ - 𝐅𝐨𝐫𝐣𝐚", " 👤 - 𝐏𝐞𝐫𝐟𝐢𝐥"])
    else:
        if region_info.get('resource'): info_parts.append("- Coletar recursos")
        if monsters_data.MONSTERS_DATA.get(region_key): info_parts.append("- Caçar monstros")
        if get_dungeon_for_region(region_key): info_parts.append("- Entrar em Calabouço")
    
    info_parts.append("\n<b>Criaturas:</b>")
    mons = monsters_data.MONSTERS_DATA.get(region_key, [])
    if not mons: info_parts.append("- <i>Nenhuma criatura catalogada.</i>")
    else:
        for m in mons: info_parts.append(f"- {m.get('name', '???')}")
            
    text = "\n".join(info_parts)
    back_cb = 'continue_after_action' if region_key == 'reino_eldora' else f"open_region:{region_key}"
    keyboard = [[InlineKeyboardButton("⬅️ 𝐕𝐎𝐋𝐓𝐀𝐑", callback_data=back_cb)]]
    
    await _safe_edit_or_send(query, context, query.message.chat_id, text, InlineKeyboardMarkup(keyboard))

# =============================================================================
# Menu Principal da Região
# =============================================================================

async def send_region_menu(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, region_key: str | None = None, player_data: dict | None = None):
    if player_data is None:
        player_data = await player_manager.get_player_data(user_id) or {}
    
    final_region_key = region_key or player_data.get("current_location", "reino_eldora")
    player_data['current_location'] = final_region_key
    
    region_info = (game_data.REGIONS_DATA or {}).get(final_region_key)

    if not region_info or final_region_key == "reino_eldora":
        if show_kingdom_menu:
            fake_update = Update(update_id=0) 
            await show_kingdom_menu(fake_update, context, player_data=player_data)
        else:
            await context.bot.send_message(chat_id=chat_id, text="Bem-vindo ao Reino de Eldora.", parse_mode="HTML")
        return 

    # --- LÓGICA DO WORLD BOSS ---
    if world_boss_manager.is_active and final_region_key == world_boss_manager.boss_location:
        caption = (f"‼️ **PERIGO IMINENTE** ‼️\nO **Demônio Dimensional** está aqui!\n\n{world_boss_manager.get_status_text()}")
        keyboard = [
            [InlineKeyboardButton("⚔️ ATACAR BOSS ⚔️", callback_data='wb_attack')],
            [InlineKeyboardButton("👤 Perfil", callback_data='profile')],
            [InlineKeyboardButton("🗺️ Fugir", callback_data='travel')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        file_data = media_ids.get_file_data(BOSS_STATS.get("media_key"))
    else:
        # --- MENU NORMAL ---
        premium = PremiumManager(player_data)
        stats = await player_manager.get_player_total_stats(player_data)
        
        status_footer = (
            f"\n\n═════════════ ◆◈◆ ══════════════\n"
            f"💰 𝐎𝐮𝐫𝐨: {player_manager.get_gold(player_data):,}   💎 𝐆𝐞𝐦𝐚𝐬: {player_manager.get_gems(player_data):,}\n"
            f"❤️ 𝐇𝐏: {int(player_data.get('current_hp',0))}/{int(stats.get('max_hp',0))}   "
            f"💙 𝐌𝐚𝐧𝐚: {int(player_data.get('current_mp',0))}/{int(stats.get('max_mana',0))}\n"
            f"⚡️ 𝐄𝐧𝐞𝐫𝐠𝐢𝐚: {int(player_data.get('energy',0))}/{int(player_manager.get_player_max_energy(player_data))}"
        )
        caption = f"Você está em <b>{region_info.get('display_name', 'Região')}</b>.\nO que deseja fazer?{status_footer}"

        keyboard = []
        if final_region_key == 'floresta_sombria':
            keyboard.append([InlineKeyboardButton("⛺ Tenda do Alquimista", callback_data='npc_trade:alquimista_floresta')])
        if final_region_key == 'deserto_ancestral':
            keyboard.append([InlineKeyboardButton("🧙‍♂️ Cabana do Místico", callback_data='rune_npc:main')])
        if final_region_key == 'picos_gelados' and is_event_active():
             keyboard.append([InlineKeyboardButton("🎅 Cabana do Noel", callback_data="christmas_shop_open")])
                 
        keyboard.append([InlineKeyboardButton("⚔️ Caçar Monstro", callback_data=f"hunt_{final_region_key}")])

        if premium.is_premium():
            keyboard.append([
                InlineKeyboardButton("⏱ 10x", callback_data=f"autohunt_start_10_{final_region_key}"),
                InlineKeyboardButton("⏱ 25x", callback_data=f"autohunt_start_25_{final_region_key}"),
                InlineKeyboardButton("⏱ 35x", callback_data=f"autohunt_start_35_{final_region_key}"),
            ])

        if build_region_dungeon_button:
            if btn := build_region_dungeon_button(final_region_key): keyboard.append([btn])
        elif get_dungeon_for_region(final_region_key):
            keyboard.append([InlineKeyboardButton("🏰 Calabouço", callback_data=f"dungeon_open:{final_region_key}")])

        keyboard.append([InlineKeyboardButton("👤 Personagem", callback_data="profile")])
        keyboard.append([InlineKeyboardButton("📜 Restaurar Durabilidade", callback_data="restore_durability_menu")])
        keyboard.append([InlineKeyboardButton("ℹ️ Info Região", callback_data=f"region_info:{final_region_key}")])
        
        # --- BOTÃO DE COLETA ---
        res_id = region_info.get("resource")
        if res_id:
            req_prof = game_data.get_profession_for_resource(res_id)
            cur_prof = (player_data.get("profession", {}) or {}).get("type")
            if req_prof and req_prof == cur_prof:
                p_res = (game_data.PROFESSIONS_DATA.get(req_prof, {}) or {}).get('resources', {})
                item_yielded = p_res.get(res_id, res_id)
                i_name = (game_data.ITEMS_DATA or {}).get(item_yielded, {}).get("display_name", res_id).capitalize()
                
                # Visual
                base_secs = int(getattr(game_data, "COLLECTION_TIME_MINUTES", 1) * 60)
                spd = float(premium.get_perk_value("gather_speed_multiplier", 1.0))
                dur = max(1, int(base_secs / max(0.25, spd)))
                hum_tm = _humanize_duration(dur)
                cost = int(premium.get_perk_value("gather_energy_cost", 1))
                c_txt = "grátis" if cost == 0 else f"-{cost}⚡"

                keyboard.append([InlineKeyboardButton(f"✋ Coletar {i_name} ({hum_tm}, {c_txt})", callback_data=f"collect_{res_id}")])

        keyboard.append([InlineKeyboardButton("🗺️ Ver Mapa", callback_data="travel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        file_data = media_ids.get_file_data(f"regiao_{final_region_key}")

    try:
        if file_data and file_data.get("id"):
            mtype = (file_data.get("type") or "photo").lower()
            if mtype == "video":
                await context.bot.send_video(chat_id=chat_id, video=file_data["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
            else:
                await context.bot.send_photo(chat_id=chat_id, photo=file_data["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
        else:
            await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML")

async def show_region_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, region_key: str | None = None, player_data: dict | None = None):
    # Wrapper para compatibilidade
    q = getattr(update, "callback_query", None)
    if q:
        await q.answer()
        try: await q.delete_message()
        except Exception: pass
        uid, cid = q.from_user.id, q.message.chat_id
    else:
        uid, cid = update.effective_user.id, update.effective_chat.id

    await _auto_finalize_travel_if_due(context, uid)
    try: await player_manager.try_finalize_timed_action_for_user(uid)
    except: pass
    
    await send_region_menu(context, uid, cid, region_key=region_key, player_data=player_data)

# =============================================================================
# Handlers de Ação: Viagem e Coleta
# =============================================================================

async def region_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid, cid = q.from_user.id, q.message.chat_id
    await _auto_finalize_travel_if_due(context, uid)

    dest = q.data.replace("region_", "", 1)
    if dest not in (game_data.REGIONS_DATA or {}):
        await q.answer("Região inválida.", show_alert=True); return

    pdata = await player_manager.get_player_data(uid)
    cur = pdata.get("current_location", "reino_eldora")
    
    vip = PremiumManager(pdata).is_premium()
    # Verifica vizinho (import local para evitar ciclo se WORLD_MAP tiver deps, mas aqui é safe)
    is_neighbor = dest in WORLD_MAP.get(cur, []) or cur == dest
    if not vip and not is_neighbor:
        await q.answer("Muito longe para viajar a pé.", show_alert=True); return

    cost = int(((game_data.REGIONS_DATA or {}).get(dest, {}) or {}).get("travel_cost", 0))
    if cost > 0 and int(pdata.get("energy", 0)) < cost:
        await q.answer("Energia insuficiente.", show_alert=True); return

    # Inicia Viagem
    if cost > 0: pdata["energy"] = int(pdata.get("energy", 0)) - cost
    secs = _get_travel_time_seconds(pdata, dest)

    if secs <= 0: # Instantâneo
        pdata["current_location"] = dest
        pdata["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(uid, pdata)
        try: await q.delete_message()
        except: pass
        await send_region_menu(context, uid, cid)
        return

    finish = datetime.now(timezone.utc) + timedelta(seconds=secs)
    pdata["player_state"] = {"action": "travel", "finish_time": finish.isoformat(), "details": {"destination": dest}}
    await player_manager.save_player_data(uid, pdata)

    try: await q.delete_message()
    except: pass
    
    human = _humanize_duration(secs)
    dest_name = (game_data.REGIONS_DATA or {}).get(dest, {}).get("display_name", dest)
    txt = f"🧭 Viajando para <b>{dest_name}</b>… (~{human})"
    
    await context.bot.send_message(chat_id=cid, text=txt, parse_mode="HTML")
    context.job_queue.run_once(finish_travel_job, when=secs, user_id=uid, chat_id=cid, data={"dest": dest}, name=f"finish_travel_{uid}")

async def finish_travel_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    uid, cid, dest = job.user_id, job.chat_id, (job.data or {}).get("dest")
    pdata = await player_manager.get_player_data(uid)
    if pdata.get("player_state", {}).get("action") == "travel":
        pdata["current_location"] = dest
        pdata["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(uid, pdata)
        await send_region_menu(context, uid, cid)

# --- START COLLECTION LOGIC (LÓGICA LOCAL) ---
async def collect_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Inicia coleta diretamente aqui, agendando o job no final.
    """
    q = update.callback_query
    # IMPORTANTE: Import local para evitar ciclo
    from handlers.job_handler import finish_collection_job 

    await q.answer()
    uid, cid = q.from_user.id, q.message.chat_id
    
    res_id = (q.data or "").replace("collect_", "", 1)
    
    # 1. Carrega dados
    pdata = await player_manager.get_player_data(uid)
    if not pdata: return

    # 2. Validações (Região e Profissão)
    cur_loc = pdata.get("current_location", "reino_eldora")
    reg_info = (game_data.REGIONS_DATA or {}).get(cur_loc, {})
    if reg_info.get("resource") != res_id:
        await q.answer("Recurso não disponível aqui.", show_alert=True); return

    req_prof = game_data.get_profession_for_resource(res_id)
    cur_prof = (pdata.get("profession", {}) or {}).get("type")
    if req_prof and req_prof != cur_prof:
        pn = (game_data.PROFESSIONS_DATA or {}).get(req_prof, {}).get("display_name", req_prof)
        await q.answer(f"Precisa ser {pn}.", show_alert=True); return

    # 3. Custo e Tempo
    prem = PremiumManager(pdata)
    cost = int(prem.get_perk_value("gather_energy_cost", 1))
    
    if int(pdata.get("energy", 0)) < cost:
        await q.answer(f"Sem energia ({cost}⚡).", show_alert=True); return

    # 4. Aplica Custo
    player_manager.spend_energy(pdata, cost)

    # 5. Configura Item Resultante
    p_res = (game_data.PROFESSIONS_DATA.get(req_prof, {}) or {}).get('resources', {})
    item_yielded = p_res.get(res_id, res_id)

    # 6. Salva Estado
    base_secs = int(getattr(game_data, "COLLECTION_TIME_MINUTES", 1) * 60)
    spd = float(prem.get_perk_value("gather_speed_multiplier", 1.0))
    dur = max(1, int(base_secs / max(0.25, spd)))
    
    finish = datetime.now(timezone.utc) + timedelta(seconds=dur)
    
    pdata['player_state'] = {
        'action': 'collecting',
        'finish_time': finish.isoformat(),
        'details': {
            'resource_id': res_id, 'item_id_yielded': item_yielded,
            'quantity': 1, 'energy_cost': cost
        }
    }
    player_manager.set_last_chat_id(pdata, cid)
    
    # Envio da mensagem visual
    i_name = (game_data.ITEMS_DATA or {}).get(item_yielded, {}).get("display_name", item_yielded)
    human = _humanize_duration(dur)
    c_txt = "Grátis" if cost == 0 else f"-{cost}⚡"
    cap = f"⛏️ <b>Coletando {i_name}...</b>\n⏳ Tempo: {human}\n⚡ Custo: {c_txt}"
    
    try: await q.delete_message()
    except: pass
    
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⏳ Trabalhando...", callback_data="noop")]])
    
    # Envia mídia da região como feedback
    m_key = reg_info.get("media_key") or f"regiao_{cur_loc}"
    fd = media_ids.get_file_data(m_key)
    msg = None
    try:
        if fd and fd.get("id"):
            typ = (fd.get("type") or "photo").lower()
            if typ == "video": msg = await context.bot.send_video(cid, fd["id"], caption=cap, reply_markup=kb, parse_mode="HTML")
            else: msg = await context.bot.send_photo(cid, fd["id"], caption=cap, reply_markup=kb, parse_mode="HTML")
        else:
            msg = await context.bot.send_message(cid, cap, reply_markup=kb, parse_mode="HTML")
    except:
        msg = await context.bot.send_message(cid, cap, reply_markup=kb, parse_mode="HTML")

    # Atualiza ID da mensagem para delete futuro
    if msg:
        pdata['player_state']['details']['collect_message_id'] = msg.message_id
        
    await player_manager.save_player_data(uid, pdata)

    # 7. Agendamento (Usando função importada localmente)
    context.job_queue.run_once(
        finish_collection_job,
        when=dur,
        data={
            'user_id': uid, 'chat_id': cid,
            'resource_id': res_id, 'item_id_yielded': item_yielded,
            'quantity': 1, 'message_id': msg.message_id if msg else None
        },
        name=f"collect_{uid}"
    )

# =============================================================================
# Durabilidade e Registro
# =============================================================================

async def show_restore_durability_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    pdata = await player_manager.get_player_data(uid) or {}
    
    lines = ["<b>📜 Restaurar Durabilidade</b>\n"]
    kb = []
    inv, equip = pdata.get("inventory", {}), pdata.get("equipment", {})
    
    def _d(raw): 
        try: return int(raw[0]), int(raw[1])
        except: return 20, 20

    has_fix = False
    for slot, uid_item in equip.items():
        inst = inv.get(uid_item)
        if isinstance(inst, dict):
            cur, mx = _d(inst.get("durability"))
            if cur < mx:
                has_fix = True
                nm = (game_data.ITEMS_DATA or {}).get(inst.get("base_id"), {}).get("display_name", "Item")
                lines.append(f"• {nm} ({cur}/{mx})")
                kb.append([InlineKeyboardButton(f"Reparar {nm}", callback_data=f"rd_fix_{uid_item}")])
    
    if not has_fix: lines.append("<i>Tudo 100%.</i>")
    
    loc = pdata.get("current_location", "reino_eldora")
    back = 'continue_after_action' if loc == 'reino_eldora' else f"open_region:{loc}"
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data=back)])
    
    await _safe_edit_or_send(q, context, q.message.chat_id, "\n".join(lines), InlineKeyboardMarkup(kb))

async def fix_item_durability(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    pdata = await player_manager.get_player_data(uid)
    item_uid = q.data.replace("rd_fix_", "", 1)

    from modules.profession_engine import restore_durability
    res = restore_durability(pdata, item_uid)
    
    if isinstance(res, dict) and res.get("error"):
        await q.answer(res["error"], show_alert=True)
    else:
        await player_manager.save_player_data(uid, pdata)
        await q.answer("Reparado!", show_alert=True)
    
    await show_restore_durability_menu(update, context)

# REGISTRO
region_handler = CallbackQueryHandler(region_callback, pattern=r"^region_[A-Za-z0-9_]+$")
travel_handler = CallbackQueryHandler(show_travel_menu, pattern=r"^travel$")
collect_handler = CallbackQueryHandler(collect_callback, pattern=r"^collect_[A-Za-z0-9_]+$")
open_region_handler = CallbackQueryHandler(open_region_callback, pattern=r"^open_region:")
restore_durability_menu_handler = CallbackQueryHandler(show_restore_durability_menu, pattern=r"^restore_durability_menu$")
restore_durability_fix_handler = CallbackQueryHandler(fix_item_durability, pattern=r"^rd_fix_.+$")
region_info_handler = CallbackQueryHandler(region_info_callback, pattern=r"^region_info:.*$")