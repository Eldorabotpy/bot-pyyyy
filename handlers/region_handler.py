# handlers/region_handler.py

import logging
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules import player_manager, game_data
from modules import file_ids as file_id_manager
from handlers.menu.kingdom import show_kingdom_menu
from modules.dungeons.registry import get_dungeon_for_region
from modules.player.premium import PremiumManager
from world_boss.engine import world_boss_manager, BOSS_STATS

logger = logging.getLogger(__name__)

def _humanize_duration(seconds: int) -> str:
    seconds = int(seconds)
    if seconds >= 60:
        mins = round(seconds / 60)
        return f"{mins} min"
    return f"{seconds} s"


def _default_travel_seconds() -> int:
    return int(getattr(game_data, "TRAVEL_DEFAULT_SECONDS", 30))


def _get_travel_time_seconds(cur_key: str, dest_key: str, player: dict) -> int:
    dest_info = (game_data.REGIONS_DATA or {}).get(dest_key, {}) or {}
    base = int(dest_info.get("travel_time_seconds", _default_travel_seconds()))
    
    premium = PremiumManager(player)
    mult = float(premium.get_perk_value("travel_time_multiplier", 1.0))

    secs = max(0, int(round(base * mult)))
    return secs

async def _auto_finalize_travel_if_due(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """
    Se o player estiver viajando e o tempo já passou, finaliza silenciosamente.
    Cobre estados legados e novos via player_manager.try_finalize_timed_action_for_user.
    """
    progressed = False

    # 1) Finalizador robusto (novo)
    if player_manager.try_finalize_timed_action_for_user(user_id):
        progressed = True

    # 2) Complemento: checa legacy travel_finish_ts aqui também
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
            progressed = True

    return progressed


# =============================================================================
# Mostra o menu de VIAGEM (o "Ver Mapa")
# =============================================================================
async def show_travel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    chat_id = query.message.chat_id

    # Finaliza viagem se estiver vencida (segurança pós-restart)
    await _auto_finalize_travel_if_due(context, user_id)

    player_data = player_manager.get_player_data(user_id) or {}
    current_location = player_data.get('current_location', 'reino_eldora')
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
            callback_data=f"region_{dest_key}"
        )
        keyboard.append([button])

    keyboard.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data='continue_after_action')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await query.delete_message()
    except Exception:
        pass

    file_data = file_id_manager.get_file_data('mapa_mundo')
    if file_data and file_data.get("id"):
        await context.bot.send_photo(
            chat_id=chat_id, photo=file_data["id"],
            caption=caption, reply_markup=reply_markup, parse_mode='HTML'
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode='HTML'
        )


# =============================================================================
# Constrói e envia o menu da REGIÃO (pós-viagem/teleporte).
# =============================================================================
# Em handlers/menu/region.py

async def send_region_menu(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int):
    # Sempre tenta destravar antes de mostrar a região
    await _auto_finalize_travel_if_due(context, user_id)

    player_data = player_manager.get_player_data(user_id) or {}
    region_key = player_data.get('current_location', 'reino_eldora')
    region_info = (game_data.REGIONS_DATA or {}).get(region_key)

    if not region_info or region_key == 'reino_eldora':
        # fallback para o menu do reino (código original inalterado)
        fake_update = Update(
            update_id=0,
            message=type('Message', (), {
                'from_user': type('User', (), {'id': user_id})(),
                'chat': type('Chat', (), {'id': chat_id})()
            })()
        )
        await show_kingdom_menu(fake_update, context)
        return

    # --- NOVO: LÓGICA DO WORLD BOSS ---
    is_boss_active = world_boss_manager.is_active
    boss_location = world_boss_manager.boss_location

    # Se o boss está ativo NESTA região, mostra o menu especial
    if is_boss_active and region_key == boss_location:
        caption = (
            f"‼️ **PERIGO IMINENTE** ‼️\n\n"
            f"O **Demônio Dimensional** está nesta região!\n\n"
            f"{world_boss_manager.get_status_text()}"
        )
        keyboard = [
            [InlineKeyboardButton("⚔️ ATACAR O DEMÔNIO ⚔️", callback_data='wb_attack')],
            [InlineKeyboardButton("👤 Personagem", callback_data='profile')],
            [InlineKeyboardButton("🗺️ Ver Mapa", callback_data='travel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Tenta obter a media do boss; se não houver, usa a da região como fallback
        file_data = file_id_manager.get_file_data(BOSS_STATS.get("media_key"))
        if not file_data or not file_data.get("id"):
            file_data = file_id_manager.get_file_data(f"regiao_{region_key}")

    # --- SENÃO, mostra o menu normal da região ---
    else:
        total_stats = player_manager.get_player_total_stats(player_data)
        current_hp = int(player_data.get('current_hp', 0))
        max_hp = int(total_stats.get('max_hp', 0))
        current_energy = int(player_data.get('energy', 0))
        max_energy = int(player_manager.get_player_max_energy(player_data))
        status_bar = f"\n\n❤️ HP: {current_hp}/{max_hp}   ⚡️ Energia: {current_energy}/{max_energy}"
        caption = (
            f"Você está em <b>{region_info.get('display_name', 'Região Desconhecida')}</b>.\n"
            f"O que deseja fazer?{status_bar}"
        )

        keyboard = []
        # Botão de Caça Normal
        keyboard.append([InlineKeyboardButton("⚔️ Caçar Monstros", callback_data=f'hunt_{region_key}')])

        # Botão de Coleta (com correção de bug)
        resource_id = region_info.get('resource')
        if resource_id:
            required_profession = game_data.get_profession_for_resource(resource_id)
            player_prof = (player_data.get('profession', {}) or {}).get('type')
            
            if required_profession and required_profession == player_prof:
                item_info = (game_data.ITEMS_DATA or {}).get(resource_id, {}) or {}
                item_name = item_info.get('display_name', resource_id.capitalize())
                profession_info = (game_data.PROFESSIONS_DATA or {}).get(required_profession, {}) or {}
                profession_emoji = profession_info.get('emoji', '✋')
                
                # --- CORREÇÃO DE BUG: Usa PremiumManager para perks de coleta ---
                premium = PremiumManager(player_data)
                base_secs = int(getattr(game_data, "COLLECTION_TIME_MINUTES", 1) * 60)
                speed_mult = float(premium.get_perk_value('gather_speed_multiplier', 1.0))
                duration_seconds = max(1, int(base_secs / max(0.25, speed_mult)))
                human_time = _humanize_duration(duration_seconds)

                energy_cost = int(premium.get_perk_value('gather_energy_cost', 1))
                cost_txt = "grátis" if energy_cost == 0 else f"-{energy_cost}⚡️"

                keyboard.append([InlineKeyboardButton(
                    f"{profession_emoji} Coletar {item_name} (~{human_time}, {cost_txt})",
                    callback_data=f"collect_{region_key}"
                )])
        
        keyboard.append([InlineKeyboardButton("👤 Personagem", callback_data='profile')])
        keyboard.append([InlineKeyboardButton("🗺️ Ver Mapa", callback_data='travel')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        file_data = file_id_manager.get_file_data(f"regiao_{region_key}")

    # --- Lógica de envio da mensagem (comum para ambos os menus) ---
    try:
        if file_data and file_data.get("id"):
            await context.bot.send_photo(
                chat_id=chat_id, photo=file_data["id"],
                caption=caption, reply_markup=reply_markup, parse_mode='HTML'
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode='HTML'
            )
    except Exception as e:
        # Fallback final se o envio com foto falhar por algum motivo
        logger.warning(f"Falha ao enviar menu da região '{region_key}'. Erro: {e}. Usando fallback de texto.")
        await context.bot.send_message(
            chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode='HTML'
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


async def region_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback 'region_<id>': valida e inicia a viagem temporizada."""
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
    chat_id = q.message.chat_id

    # finalize viagens vencidas antes de iniciar nova
    await _auto_finalize_travel_if_due(context, user_id)

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

    travel_cost = int(((game_data.REGIONS_DATA or {}).get(dest_key, {}) or {}).get("travel_cost", 0))
    energy = int(player.get("energy", 0))
    if travel_cost > 0 and energy < travel_cost:
        await q.answer("Energia insuficiente para viajar.", show_alert=True)
        return

    secs = _get_travel_time_seconds(cur, dest_key, player)

    if travel_cost > 0:
        player["energy"] = max(0, energy - travel_cost)

    if secs <= 0:
        player["current_location"] = dest_key
        player["player_state"] = {"action": "idle"}
        player_manager.save_player_data(user_id, player)
        try:
            await q.delete_message()
        except Exception:
            pass
        await send_region_menu(context, user_id, chat_id)
        return

    finish_ts = time.time() + secs
    player_state = (player.get("player_state") or {})
    player_state["action"] = "travel"
    player_state["travel_dest"] = dest_key
    player_state["travel_finish_ts"] = finish_ts
    player["player_state"] = player_state
    player_manager.save_player_data(user_id, player)

    dest_disp = (game_data.REGIONS_DATA or {}).get(dest_key, {}).get("display_name", dest_key)
    human = _humanize_duration(secs)

    try:
        await q.delete_message()
    except Exception:
        pass

    banner = file_id_manager.get_file_data('mapa_mundo')
    caption = f"🧭 𝑽𝒊𝒂𝒋𝒂𝒏𝒅𝒐 𝒑𝒂𝒓𝒂 <b>{dest_disp}</b>… (~{human})"
    if banner and banner.get("id"):
        await context.bot.send_photo(chat_id=chat_id, photo=banner["id"], caption=caption, parse_mode="HTML")
    else:
        await context.bot.send_message(chat_id=chat_id, text=caption, parse_mode="HTML")

    context.job_queue.run_once(
        finish_travel_job,
        when=secs,
        user_id=user_id,
        chat_id=chat_id,
        data={"dest": dest_key},
        name=f"finish_travel_{user_id}"
    )


# =============================================================================
# Job: finaliza a viagem e abre o menu da região
# =============================================================================
async def finish_travel_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id = job.user_id
    chat_id = job.chat_id
    dest = (job.data or {}).get("dest")

    # Antes de aplicar, tente destravar pelo finalizador robusto
    player_manager.try_finalize_timed_action_for_user(user_id)

    player = player_manager.get_player_data(user_id) or {}
    state = (player.get("player_state") or {})
    if state.get("action") == "travel" and dest and state.get("travel_dest") == dest:
        player["current_location"] = dest
        player["player_state"] = {"action": "idle"}
        player_manager.save_player_data(user_id, player)

    await send_region_menu(context, user_id, chat_id)


# =============================================================================
# Wrapper: abrir o menu da região atual (usado por /start e outros)
# =============================================================================
async def show_region_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    # garanta destrave antes de mostrar
    await _auto_finalize_travel_if_due(context, user_id)
    await send_region_menu(context, user_id, chat_id)


# =============================================================================
# Exports (registre no main)
# =============================================================================
region_handler  = CallbackQueryHandler(region_callback, pattern=r'^region_[A-Za-z0-9_]+$')
travel_handler  = CallbackQueryHandler(show_travel_menu, pattern=r'^travel$')
