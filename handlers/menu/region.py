# handlers/menu/region.py

import time
import logging
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, game_data

# 🔎 Mídias (mapa/regiões). Suporta tanto file_id_manager quanto file_ids.
try:
    from modules import file_id_manager as media_ids
except Exception:
    try:
        from modules import file_ids as media_ids
    except Exception:
        media_ids = None  # fallback mudo

# Menu principal do reino (fallback)
try:
    from handlers.menu.kingdom import show_kingdom_menu
except Exception:
    show_kingdom_menu = None  # será checado antes de usar

# Botão utilitário do calabouço (se o runtime existir)
try:
    from modules.dungeons.runtime import build_region_dungeon_button
except Exception:
    build_region_dungeon_button = None  # fallback: usaremos InlineKeyboardButton

logger = logging.getLogger(__name__)


def _humanize_duration(seconds: int) -> str:
    seconds = int(seconds)
    if seconds >= 60:
        mins = round(seconds / 60)
        return f"{mins} min"
    return f"{seconds} s"


def _get_travel_time_seconds(cur_key: str, dest_key: str, player: dict) -> int:
    """
    Regra:
      - Premium → 0s (instantâneo)
      - Free    → 600s (10min)
    """
    try:
        if player_manager.is_player_premium(player):
            return 0
    except Exception:
        pass
    return 600


async def _auto_finalize_travel_if_due(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """
    Se o player estiver em 'travel' e o tempo já passou (pós-restart),
    finaliza silenciosamente e retorna True.
    """
    player = player_manager.get_player_data(user_id) or {}
    state = player.get("player_state") or {}
    if state.get("action") == "travel":
        finish_ts = float(state.get("travel_finish_ts") or 0)
        if finish_ts > 0 and time.time() >= finish_ts:
            dest = state.get("travel_dest")
            if dest and dest in (game_data.REGIONS_DATA or {}):
                player["current_location"] = dest
            player["player_state"] = {"action": "idle"}
            player_manager.save_player_data(user_id, player)
            return True
    return False


# =============================================================================
# Mostra o menu de VIAGEM (o "Ver Mapa")
# =============================================================================
async def show_travel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    chat_id = query.message.chat_id

    # Finaliza viagem vencida (segurança pós-restart)
    await _auto_finalize_travel_if_due(context, user_id)

    player_data = player_manager.get_player_data(user_id) or {}
    current_location = player_data.get("current_location", "reino_eldora")
    region_info = (game_data.REGIONS_DATA or {}).get(current_location) or {}
    possible_destinations = (game_data.WORLD_MAP or {}).get(current_location, [])

    caption = (
        f"𝑽𝒐𝒄𝒆̂ 𝒆𝒔𝒕𝒂́ 𝒆𝒎 <b>{region_info.get('display_name','Desconhecido')}</b>.\n"
        f"𝑷𝒂𝒓𝒂 𝒐𝒏𝒅𝒆 𝒅𝒆𝒔𝒆𝒋𝒂 𝒗𝒊𝒂𝒋𝒂𝒓?"
    )

    keyboard = []
    for dest_key in possible_destinations:
        dest_info = (game_data.REGIONS_DATA or {}).get(dest_key, {}) or {}
        button = InlineKeyboardButton(
            f"{dest_info.get('emoji', '')} {dest_info.get('display_name', dest_key)}",
            callback_data=f"region_{dest_key}",
        )
        keyboard.append([button])

    keyboard.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="continue_after_action")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await query.delete_message()
    except Exception:
        pass

    fd = media_ids.get_file_data("mapa_mundo") if media_ids and hasattr(media_ids, "get_file_data") else None
    if fd and fd.get("id"):
        try:
            if (fd.get("type") or "photo").lower() == "video":
                await context.bot.send_video(
                    chat_id=chat_id, video=fd["id"],
                    caption=caption, reply_markup=reply_markup, parse_mode="HTML"
                )
            else:
                await context.bot.send_photo(
                    chat_id=chat_id, photo=fd["id"],
                    caption=caption, reply_markup=reply_markup, parse_mode="HTML"
                )
            return
        except Exception as e:
            logger.debug("Falha ao enviar mídia do mapa (%s): %s", fd, e)

    await context.bot.send_message(
        chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML"
    )


# =============================================================================
# Constrói e envia o menu da REGIÃO (pós-viagem/teleporte).
# =============================================================================
# Em handlers/menu/region.py
# SUBSTITUA a sua função send_region_menu por esta:

async def open_region_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    
    try:
        region_key = query.data.split(':')[1]
    except IndexError:
        region_key = 'reino_eldora'

    player_data = player_manager.get_player_data(user_id)
    if player_data:
        player_data['current_location'] = region_key
        player_manager.save_player_data(user_id, player_data)

    try: await query.delete_message()
    except Exception: pass

    await send_region_menu(context, user_id, chat_id)

async def send_region_menu(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int):
    print(">>> RASTREAMENTO: Entrou em send_region_menu")
    player_data = player_manager.get_player_data(user_id) or {}
    region_key = player_data.get("current_location", "reino_eldora")
    region_info = (game_data.REGIONS_DATA or {}).get(region_key)

    if not region_info or region_key == "reino_eldora":
        if show_kingdom_menu:
            fake_update = Update(
                update_id=0,
                message=type("Message", (), {
                    "from_user": type("User", (), {"id": user_id})(),
                    "chat": type("Chat", (), {"id": chat_id})()
                })()
            )
            await show_kingdom_menu(fake_update, context)
        else:
            await context.bot.send_message(chat_id=chat_id, text="Você está no Reino de Eldora.", parse_mode="HTML")
        return

    total_stats = player_manager.get_player_total_stats(player_data)
    current_hp = int(player_data.get("current_hp", 0))
    max_hp = int(total_stats.get("max_hp", 0))
    current_energy = int(player_data.get("energy", 0))
    max_energy = int(player_manager.get_player_max_energy(player_data))

    status_footer = (
        f"\n\n═════════════ ◆◈◆ ══════════════\n"
        f"❤️ 𝐇𝐏: {current_hp}/{max_hp}   "
        f"⚡️ 𝐄𝐧𝐞𝐫𝐠𝐢𝐚: {current_energy}/{max_energy}"
    )

    caption = (
        f"Você está em <b>{region_info.get('display_name', 'Região Desconhecida')}</b>.\n"
        f"O que deseja fazer?{status_footer}"
    )

    keyboard = []
    keyboard.append([InlineKeyboardButton("⚔️ 𝐂𝐚𝐜̧𝐚𝐫 𝐌𝐨𝐧𝐬𝐭𝐫𝐨𝐬 ⚔️", callback_data=f"hunt_{region_key}")])

    if build_region_dungeon_button:
        keyboard.append([build_region_dungeon_button(region_key)])
    else:
        keyboard.append([InlineKeyboardButton("🏰 𝐂𝐚𝐥𝐚𝐛𝐨𝐮𝐜̧𝐨 🏰", callback_data=f"dungeon_open:{region_key}")])

    keyboard.append([InlineKeyboardButton("👤 𝐏𝐞𝐫𝐬𝐨𝐧𝐚𝐠𝐞𝐦 👤", callback_data="profile")])
    keyboard.append([InlineKeyboardButton("📜 𝐑𝐞𝐬𝐭𝐚𝐮𝐫𝐚𝐫 𝐃𝐮𝐫𝐚𝐛𝐢𝐥𝐢𝐝𝐚𝐝𝐞 📜", callback_data="restore_durability_menu")])

    # --- INÍCIO DA CORREÇÃO ---
    # Usar a chave da região como a única fonte de verdade para o ID do recurso.
    resource_id = region_key
    # --- FIM DA CORREÇÃO ---
    
    if resource_id:
        required_profession = game_data.get_profession_for_resource(resource_id)
        prof_data = player_data.get("profession", {}) or {}
        player_prof = prof_data.get("type")

        if required_profession and required_profession == player_prof:
            item_info = (game_data.ITEMS_DATA or {}).get(resource_id, {}) or {}
            # Para o nome do item no botão, usamos o item que será dado, não o recurso
            profession_resources = (game_data.PROFESSIONS_DATA.get(required_profession, {}) or {}).get('resources', {})
            item_id_yielded = profession_resources.get(resource_id, resource_id)
            item_yielded_info = (game_data.ITEMS_DATA or {}).get(item_id_yielded, {}) or {}
            item_name = item_yielded_info.get("display_name", item_id_yielded.capitalize())
            
            profession_info = (game_data.PROFESSIONS_DATA or {}).get(required_profession, {}) or {}
            profession_emoji = profession_info.get("emoji", "✋")
            
            base_secs = int(getattr(game_data, "COLLECTION_TIME_MINUTES", 1) * 60)
            try:
                speed_mult = float(player_manager.get_player_perk_value(player_data, "gather_speed_multiplier", 1.0))
            except Exception:
                speed_mult = 1.0
            speed_mult = max(0.25, min(4.0, speed_mult))
            duration_seconds = max(1, int(base_secs / speed_mult))
            human_time = _humanize_duration(duration_seconds)

            energy_cost = int(player_manager.get_player_perk_value(player_data, "gather_energy_cost", 1))
            cost_txt = "grátis" if energy_cost == 0 else f"-{energy_cost} ⚡️"

            keyboard.append([InlineKeyboardButton(
                f"{profession_emoji} Coletar {item_name} (~{human_time}, {cost_txt})",
                callback_data=f"collect_{region_key}"
            )])

    keyboard.append([InlineKeyboardButton("🗺️ 𝕍𝕖𝕣 𝕄𝕒𝕡𝕒 🗺️", callback_data="travel")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    file_id_key = f"regiao_{region_key}"
    fd = media_ids.get_file_data(file_id_key) if media_ids and hasattr(media_ids, "get_file_data") else None
    if fd and fd.get("id"):
        try:
            if (fd.get("type") or "photo").lower() == "video":
                await context.bot.send_video(
                    chat_id=chat_id, video=fd["id"],
                    caption=caption, reply_markup=reply_markup, parse_mode="HTML"
                )
            else:
                await context.bot.send_photo(
                    chat_id=chat_id, photo=fd["id"],
                    caption=caption, reply_markup=reply_markup, parse_mode="HTML"
                )
            return
        except Exception as e:
            logger.debug("Falha ao enviar mídia da região (%s): %s", fd, e)

    await context.bot.send_message(
        chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML"
    )

# =============================================================================
# Validação da viagem e início do cronômetro
# =============================================================================
def _is_neighbor(world_map: dict, cur: str, dest: str) -> bool:
    if cur == dest:
        return True
    neigh = (world_map or {}).get(cur, []) or []
    if dest in neigh:
        return True
    cur_info = (game_data.REGIONS_DATA or {}).get(cur, {}) or {}
    if dest in (cur_info.get("neighbors") or []):
        return True
    return False


# Em handlers/menu/region.py

async def region_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback 'region_<id>': valida e inicia a viagem temporizada.
    Se o tempo for 0 (premium), teleporta na hora.
    """
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
    chat_id = q.message.chat.id

    # Esta função agora não é mais necessária aqui, pois a watchdog em jobs.py lida com isso.
    # await _auto_finalize_travel_if_due(context, user_id)

    data = (q.data or "")
    if not data.startswith("region_"):
        await q.answer("Destino inválido.", show_alert=True)
        return
    dest_key = data.replace("region_", "", 1)

    player = player_manager.get_player_data(user_id) or {}
    cur = player.get("current_location", "reino_eldora")

    if dest_key not in (game_data.REGIONS_DATA or {}):
        await q.answer("Região desconhecida.", show_alert=True)
        return

    if not _is_neighbor(getattr(game_data, "WORLD_MAP", {}), cur, dest_key):
        await q.answer("Você não pode viajar direto para lá.", show_alert=True)
        return

    # custo de energia
    travel_cost = int(((game_data.REGIONS_DATA or {}).get(dest_key, {}) or {}).get("travel_cost", 0))
    energy = int(player.get("energy", 0))
    if travel_cost > 0 and energy < travel_cost:
        await q.answer("Energia insuficiente para viajar.", show_alert=True)
        return

    secs = _get_travel_time_seconds(cur, dest_key, player)

    # debita energia
    if travel_cost > 0:
        player["energy"] = max(0, energy - travel_cost)

    if secs <= 0:
        # teleporte instantâneo
        player["current_location"] = dest_key
        player["player_state"] = {"action": "idle"}
        player_manager.save_player_data(user_id, player)
        try:
            await q.delete_message()
        except Exception:
            pass
        await send_region_menu(context, user_id, chat_id)
        return

    # =========================================================
    # 👇 INÍCIO DA CORREÇÃO PARA O BUG DA VIAGEM 👇
    # =========================================================
    # Agora salvamos o estado no formato que a watchdog entende.
    finish_time = datetime.now(timezone.utc) + timedelta(seconds=secs)
    player["player_state"] = {
        "action": "travel",
        "finish_time": finish_time.isoformat(),
        "details": {
            "destination": dest_key
        }
    }
    player_manager.save_player_data(user_id, player)
    # =========================================================
    # 👆 FIM DA CORREÇÃO 👆
    # =========================================================

    try:
        await q.delete_message()
    except Exception:
        pass

    dest_disp = (game_data.REGIONS_DATA or {}).get(dest_key, {}).get("display_name", dest_key)
    human = _humanize_duration(secs)
    caption = f"🧭 Viajando para <b>{dest_disp}</b>… (~{human})"

    banner = media_ids.get_file_data("mapa_mundo") if media_ids and hasattr(media_ids, "get_file_data") else None
    if banner and banner.get("id"):
        try:
            if (banner.get("type") or "photo").lower() == "video":
                await context.bot.send_video(chat_id=chat_id, video=banner["id"], caption=caption, parse_mode="HTML")
            else:
                await context.bot.send_photo(chat_id=chat_id, photo=banner["id"], caption=caption, parse_mode="HTML")
        except Exception as e:
            logger.debug("Falha ao enviar mídia de viagem (%s): %s. Usando texto.", banner, e)
            await context.bot.send_message(chat_id=chat_id, text=caption, parse_mode="HTML")
    else:
        await context.bot.send_message(chat_id=chat_id, text=caption, parse_mode="HTML")

    # agenda a finalização da viagem
    context.job_queue.run_once(
        finish_travel_job,
        when=secs,
        user_id=user_id,
        chat_id=chat_id,
        data={"dest": dest_key},
        name=f"finish_travel_{user_id}",
    )

# =============================================================================
# Job: finaliza a viagem e abre o menu da região


async def finish_travel_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Job: finaliza a viagem, atualiza a localização do jogador e abre o menu da nova região.
    """
    job = context.job
    user_id = job.user_id
    chat_id = job.chat_id
    dest = (job.data or {}).get("dest")

    player = player_manager.get_player_data(user_id) or {}
    state = player.get("player_state", {})

    # Verificação de segurança: A tarefa só deve ser executada se o jogador
    # ainda estiver no estado 'travel'. Isto previne execuções duplicadas.
    if state.get("action") != "travel":
        return

    # A tarefa é nossa! Reivindicamos a tarefa mudando o estado primeiro.
    player["current_location"] = dest
    player["player_state"] = {"action": "idle"}
    player_manager.save_player_data(user_id, player)

    # Agora, com a certeza de que somos os únicos a processar, enviamos o menu.
    # A sua função `send_region_menu` já foi corrigida para usar a `current_location`
    # que acabámos de salvar, então não precisamos de passar o `dest` aqui.
    await send_region_menu(context, user_id, chat_id)

async def collect_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
    chat_id = q.message.chat_id

    data = (q.data or "")
    if not data.startswith("collect_"):
        await q.answer("Ação inválida.", show_alert=True)
        return
    region_key = data.replace("collect_", "", 1)

    # --- INÍCIO DA CORREÇÃO ---
    # O ID do recurso é o próprio ID da região.
    resource_id = region_key
    # --- FIM DA CORREÇÃO ---

    if resource_id not in (game_data.REGIONS_DATA or {}):
        await q.answer("Região desconhecida.", show_alert=True)
        return

    player = player_manager.get_player_data(user_id) or {}
    cur_loc = player.get("current_location", "reino_eldora")
    if cur_loc != region_key:
        await q.answer("Você precisa estar nesta região para coletar.", show_alert=True)
        return

    required_profession = game_data.get_profession_for_resource(resource_id)
    prof_data = player.get("profession", {}) or {}
    player_prof = prof_data.get("type")
    if not required_profession or required_profession != player_prof:
        await q.answer("Sua profissão não permite coletar aqui.", show_alert=True)
        return

    try:
        energy_cost = int(player_manager.get_player_perk_value(player, "gather_energy_cost", 1))
    except Exception:
        energy_cost = 1
    cur_energy = int(player.get("energy", 0))
    if energy_cost > 0 and cur_energy < energy_cost:
        await q.answer("Energia insuficiente para coletar.", show_alert=True)
        return

    base_secs = int(getattr(game_data, "COLLECTION_TIME_MINUTES", 1) * 60)
    try:
        speed_mult = float(player_manager.get_player_perk_value(player, "gather_speed_multiplier", 1.0))
    except Exception:
        speed_mult = 1.0
    speed_mult = max(0.25, min(4.0, speed_mult))
    duration_seconds = max(1, int(base_secs / speed_mult))

    if energy_cost > 0:
        player["energy"] = max(0, cur_energy - energy_cost)
    
    # Descobre o item a ser dado para guardar no player_state
    profession_resources = (game_data.PROFESSIONS_DATA.get(required_profession, {}) or {}).get('resources', {})
    item_id_yielded = profession_resources.get(resource_id, resource_id)

    now = datetime.now(timezone.utc).replace(microsecond=0)
    finish_time = now + timedelta(seconds=duration_seconds)
    player_state = {
        "action": "collecting",
        "finish_time": finish_time.isoformat(),
        "details": {
            "resource_id": resource_id,
            "item_id_yielded": item_id_yielded,
            "energy_cost": energy_cost,
            "speed_mult": speed_mult,
        }
    }
    player["player_state"] = player_state
    player["last_chat_id"] = chat_id
    player_manager.save_player_data(user_id, player)

    item_yielded_info = (game_data.ITEMS_DATA or {}).get(item_id_yielded, {}) or {}
    item_name = item_yielded_info.get("display_name", item_id_yielded)

    human = _humanize_duration(duration_seconds)
    caption = f"⛏️ 𝚅𝚘𝚌𝚎̂ 𝚌𝚘𝚖𝚎𝚌̧𝚘𝚞 𝚊 𝚌𝚘𝚕𝚎𝚝𝚊𝚛 <b>{item_name}</b> (~{human}). Volto quando terminar."

    banner = media_ids.get_file_data("mapa_mundo") if media_ids and hasattr(media_ids, "get_file_data") else None
    try:
        await q.delete_message()
    except Exception:
        pass

    if banner and banner.get("id"):
        try:
            if (banner.get("type") or "photo").lower() == "video":
                await context.bot.send_video(chat_id=chat_id, video=banner["id"], caption=caption, parse_mode="HTML")
            else:
                await context.bot.send_photo(chat_id=chat_id, photo=banner["id"], caption=caption, parse_mode="HTML")
        except Exception as e:
            logger.debug("Falha ao enviar mídia de coleta (%s): %s. Usando texto.", banner, e)
            await context.bot.send_message(chat_id=chat_id, text=caption, parse_mode="HTML")
    else:
        await context.bot.send_message(chat_id=chat_id, text=caption, parse_mode="HTML")

    try:
        from handlers.job_handler import finish_collection_job
        context.job_queue.run_once(
            finish_collection_job,
            when=duration_seconds,
            user_id=user_id,
            chat_id=chat_id,
            data={
                "resource_id": resource_id,
                "item_id_yielded": item_id_yielded,
                "energy_cost": energy_cost,
                "charged": True,
                "speed_mult": speed_mult,
            },
            name=f"finish_collect_{user_id}",
        )
    except Exception as e:
        logger.warning("Falha ao agendar finish_collection_job: %s", e)

# =============================================================================
# Wrapper: abrir o menu da região atual (usado por /start e outros)
# =============================================================================
async def show_region_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(">>> RASTREAMENTO: Entrou em show_region_menu (wrapper)")
    query = getattr(update, "callback_query", None)
    if query:
        await query.answer()
        try:
            await query.delete_message()
        except Exception:
            pass
        user_id = query.from_user.id
        chat_id = query.message.chat_id
    else:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

    await _auto_finalize_travel_if_due(context, user_id)

    # se tiver helper no player_manager para finalizar outras ações, chame aqui
    try:
        player_manager.try_finalize_timed_action_for_user(user_id)
    except Exception:
        pass

    await send_region_menu(context, user_id, chat_id)


# =============================================================================
# 👉 Menu local de RESTAURAR DURABILIDADE (somente itens equipados)
# =============================================================================
def _dur_tuple(raw) -> tuple[int, int]:
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
    cur = max(0, min(cur, mx))
    mx = max(1, mx)
    return cur, mx


async def show_restore_durability_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
    chat_id = q.message.chat_id
    pdata = player_manager.get_player_data(user_id) or {}
    inv = pdata.get("inventory", {}) or {}
    equip = pdata.get("equipment", {}) or {}

    lines = ["<b>📜 Restaurar Durabilidade</b>\nEscolha um item <u>equipado</u> para restaurar:\n"]
    kb_rows = []
    any_repairable = False

    for slot, uid in (equip.items() if isinstance(equip, dict) else []):
        inst = inv.get(uid)
        if not (isinstance(inst, dict) and inst.get("base_id")):
            continue
        cur, mx = _dur_tuple(inst.get("durability"))
        # mostra apenas quem precisa de reparo
        if cur < mx:
            any_repairable = True
            base = (game_data.ITEMS_DATA or {}).get(inst["base_id"], {}) or {}
            name = base.get("display_name", inst["base_id"])
            lines.append(f"• {name} — <b>{cur}/{mx}</b>")
            kb_rows.append([InlineKeyboardButton(f"Restaurar {name}", callback_data=f"rd_fix_{uid}")])

    if not any_repairable:
        lines.append("<i>Nenhum equipamento equipado precisa de reparo.</i>")

    kb_rows.append([InlineKeyboardButton("⬅️ 𝕍𝕠𝕝𝕥𝕒𝕣", callback_data="continue_after_action")])

    try:
        await q.edit_message_caption(caption="\n".join(lines), reply_markup=InlineKeyboardMarkup(kb_rows), parse_mode="HTML")
    except Exception:
        await q.edit_message_text(text="\n".join(lines), reply_markup=InlineKeyboardMarkup(kb_rows), parse_mode="HTML")


async def fix_item_durability(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
    pdata = player_manager.get_player_data(user_id) or {}
    uid = q.data.replace("rd_fix_", "", 1)

    # usamos o engine oficial para reparar (consome pergaminho)
    from modules.profession_engine import restore_durability as restore_durability_engine

    res = restore_durability_engine(pdata, uid)
    if isinstance(res, dict) and res.get("error"):
        await q.answer(res["error"], show_alert=True)
        # volta/atualiza a listagem
        await show_restore_durability_menu(update, context)
        return

    player_manager.save_player_data(user_id, pdata)

    # feedback leve e atualiza a lista
    await q.answer("Durabilidade restaurada!", show_alert=True)
    await show_restore_durability_menu(update, context)


# =============================================================================
# Exports (registre no main)
# =============================================================================
region_handler  = CallbackQueryHandler(region_callback, pattern=r"^region_[A-Za-z0-9_]+$")
travel_handler  = CallbackQueryHandler(show_travel_menu, pattern=r"^travel$")
collect_handler = CallbackQueryHandler(collect_callback, pattern=r"^collect_[A-Za-z0-9_]+$")
open_region_handler = CallbackQueryHandler(open_region_callback, pattern=r"^open_region:")

# Atalhos locais de durabilidade
restore_durability_menu_handler = CallbackQueryHandler(show_restore_durability_menu, pattern=r"^restore_durability_menu$")
restore_durability_fix_handler  = CallbackQueryHandler(fix_item_durability, pattern=r"^rd_fix_.+$")
