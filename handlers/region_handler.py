# handlers/region_handler.py
# (VERSÃO FINAL: AUTH UNIFICADA + ID SEGURO + CORREÇÃO DE JOBS)

import logging
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules import player_manager, game_data
from modules import file_ids as file_id_manager
from handlers.menu.kingdom import show_kingdom_menu
from modules.dungeons.registry import get_dungeon_for_region
from modules.player.premium import PremiumManager
from modules.world_boss.engine import world_boss_manager, BOSS_STATS
from datetime import datetime, timezone, timedelta
from modules.auth_utils import get_current_player_id # <--- ÚNICA FONTE DE VERDADE

logger = logging.getLogger(__name__)

def _humanize_duration(seconds: int) -> str:
    seconds = int(seconds)
    if seconds >= 60:
        mins = round(seconds / 60)
        return f"{mins} min"
    return f"{seconds} s"


def _default_travel_seconds() -> int:
    return int(getattr(game_data, "TRAVEL_DEFAULT_SECONDS", 360))


# Em: handlers/menu/region.py

def _get_travel_time_seconds(player_data: dict, dest_key: str) -> int:
    """
    Calcula o tempo de viagem. 
    FORÇADO PARA 6 MINUTOS (360 segundos) BASE.
    """
    # --- VALOR BASE FIXO: 6 MINUTOS ---
    base = 360 
    
    # Aplica multiplicadores de perks (Premium), se houver
    try:
        premium = PremiumManager(player_data)
        mult = float(premium.get_perk_value("travel_time_multiplier", 1.0))
    except Exception:
        mult = 1.0 # Fallback se o PremiumManager falhar

    final_seconds = max(0, int(round(base * mult)))
    
    # Debug para o terminal (para você ter certeza que funcionou)
    # print(f"DEBUG VIAGEM: Base=360s, Mult={mult}, Final={final_seconds}s")
    
    return final_seconds

async def _auto_finalize_travel_if_due(context: ContextTypes.DEFAULT_TYPE, user_id: str) -> bool:
    """
    Se o player estiver viajando e o tempo já passou, finaliza silenciosamente.
    Args:
        user_id (str): ID do jogador (ObjectId string).
    """
    progressed = False

    # 1) Finalizador robusto (novo) - Assumindo que esta função é SÍNCRONA
    try:
        if player_manager.try_finalize_timed_action_for_user(user_id):
            progressed = True
    except Exception as e_finalize:
         logger.error(f"Erro ao tentar _auto_finalize_travel_if_due (novo) para {user_id}: {e_finalize}")

    # 2) Complemento: checa legacy travel_finish_ts
    player = await player_manager.get_player_data(user_id) or {}
    state = player.get("player_state") or {}

    if state.get("action") == "travel":
        # Verifica o novo formato (finish_time ISO string)
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
             except Exception:
                  pass 

        # Verifica o formato legado (travel_finish_ts float)
        finish_ts = float(state.get("travel_finish_ts") or 0)
        if finish_ts > 0 and time.time() >= finish_ts:
            dest = state.get("travel_dest")
            if dest and dest in (game_data.REGIONS_DATA or {}):
                player["current_location"] = dest
            player["player_state"] = {"action": "idle"}
            await player_manager.save_player_data(user_id, player)
            progressed = True

    return progressed

# =============================================================================
# Mostra o menu de VIAGEM (o "Ver Mapa")
# =============================================================================
async def show_travel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # 🔒 SEGURANÇA: ID via Auth Central
    user_id = get_current_player_id(update, context)
    chat_id = query.message.chat_id

    if not user_id:
        await query.answer("Sessão inválida.", show_alert=True)
        return

    await _auto_finalize_travel_if_due(context, user_id)

    player_data = await player_manager.get_player_data(user_id) or {}
    
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
async def send_region_menu(context: ContextTypes.DEFAULT_TYPE, user_id: str, chat_id: int):
    """
    Envia o menu da região atual para o jogador.
    Args:
        user_id (str): ID do jogador (String).
        chat_id (int): Chat ID para envio da mensagem.
    """
    await _auto_finalize_travel_if_due(context, user_id)

    player_data = await player_manager.get_player_data(user_id) or {}
    region_key = player_data.get('current_location', 'reino_eldora')
    region_info = (game_data.REGIONS_DATA or {}).get(region_key)

    if not region_info or region_key == 'reino_eldora':
        # Cria um fake update seguro para chamar o menu do reino
        # Usamos um chat_id numérico válido no objeto Mock
        fake_update = Update(0, message=None) 
        fake_update.effective_chat = type("Chat", (), {"id": chat_id})()
        
        # Injeta o ID na sessão para que o show_kingdom_menu consiga ler (hack de compatibilidade)
        if context.user_data is not None:
            context.user_data["logged_player_id"] = user_id
            
        await show_kingdom_menu(fake_update, context)
        return

    # --- LÓGICA DO WORLD BOSS ---
    is_boss_active = world_boss_manager.is_active
    boss_location = world_boss_manager.boss_location

    if is_boss_active and region_key == boss_location:
        caption = (f"‼️ **PERIGO IMINENTE** ‼️\n\n"
                   f"O **Demônio Dimensional** está nesta região!\n\n"
                   f"{world_boss_manager.get_status_text()}")
        keyboard = [
            [InlineKeyboardButton("⚔️ ATACAR O DEMÔNIO ⚔️", callback_data='wb_attack')],
            [InlineKeyboardButton("👤 Personagem", callback_data='profile')],
            [InlineKeyboardButton("🗺️ Ver Mapa", callback_data='travel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        file_data = file_id_manager.get_file_data(BOSS_STATS.get("media_key"))
        if not file_data or not file_data.get("id"):
            file_data = file_id_manager.get_file_data(f"regiao_{region_key}")

    else:
        # --- Menu normal da região ---
        total_stats = await player_manager.get_player_total_stats(player_data) # Async
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
        keyboard.append([InlineKeyboardButton("⚔️ Caçar Monstros", callback_data=f'hunt_{region_key}')])
        
        resource_id = region_info.get('resource')
        if resource_id:
            required_profession = game_data.get_profession_for_resource(resource_id)
            player_prof = (player_data.get('profession', {}) or {}).get('type')
            
            if required_profession and required_profession == player_prof:
                item_info = (game_data.ITEMS_DATA or {}).get(resource_id, {}) or {}
                item_name = item_info.get('display_name', resource_id.capitalize())
                profession_info = (game_data.PROFESSIONS_DATA or {}).get(required_profession, {}) or {}
                profession_emoji = profession_info.get('emoji', '✋')
                
                premium = PremiumManager(player_data)
                base_secs = int(getattr(game_data, "COLLECTION_TIME_MINUTES", 1) * 60)
                speed_mult = float(premium.get_perk_value('gather_speed_multiplier', 1.0))
                duration_seconds = max(1, int(base_secs / max(0.25, speed_mult)))
                human_time = _humanize_duration(duration_seconds)
                energy_cost = int(premium.get_perk_value('gather_energy_cost', 1))
                cost_txt = "grátis" if energy_cost == 0 else f"-{energy_cost}⚡️"

                keyboard.append([InlineKeyboardButton(
                    f"{profession_emoji} Coletar {item_name} (~{human_time}, {cost_txt})",
                    callback_data=f"collect_{resource_id}"
                )])
        
        keyboard.append([InlineKeyboardButton("👤 Personagem", callback_data='profile')])
        keyboard.append([InlineKeyboardButton("🗺️ Ver Mapa", callback_data='travel')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        file_data = file_id_manager.get_file_data(f"regiao_{region_key}")

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

    # 🔒 SEGURANÇA: ID via Auth Central
    user_id = get_current_player_id(update, context)
    chat_id = q.message.chat_id

    if not user_id:
        await q.answer("Sessão inválida. Use /start.", show_alert=True)
        return

    await _auto_finalize_travel_if_due(context, user_id)

    data = (q.data or "")
    if not data.startswith("region_"):
        await q.answer("Destino inválido.", show_alert=True)
        return
    dest_key = data.replace("region_", "", 1)

    player = await player_manager.get_player_data(user_id) or {}
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

    # Correção: Passa apenas 2 argumentos (player_data e dest_key)
    secs = _get_travel_time_seconds(player, dest_key)

    if travel_cost > 0:
        player["energy"] = max(0, energy - travel_cost)

    if secs <= 0: # Teleporte instantâneo
        player["current_location"] = dest_key
        player["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(user_id, player)
        try: await q.delete_message()
        except Exception: pass
        await send_region_menu(context, user_id, chat_id)
        return

    # Iniciar viagem temporizada
    finish_ts = time.time() + secs
    player_state = (player.get("player_state") or {})
    player_state["action"] = "travel"
    player_state["travel_dest"] = dest_key
    player_state["travel_finish_ts"] = finish_ts
    
    # Novo formato ISO para compatibilidade futura
    player_state["finish_time"] = (datetime.now(timezone.utc) + timedelta(seconds=secs)).isoformat()
    player_state["details"] = {"destination": dest_key}
    
    player["player_state"] = player_state
    await player_manager.save_player_data(user_id, player)

    dest_disp = (game_data.REGIONS_DATA or {}).get(dest_key, {}).get("display_name", dest_key)
    human = _humanize_duration(secs)

    try: await q.delete_message()
    except Exception: pass

    banner = file_id_manager.get_file_data('mapa_mundo')
    caption = f"🧭 𝑽𝒊𝒂𝒋𝒂𝒏𝒅𝒐 𝒑𝒂𝒓𝒂 <b>{dest_disp}</b>… (~{human})"
    if banner and banner.get("id"):
        await context.bot.send_photo(chat_id=chat_id, photo=banner["id"], caption=caption, parse_mode="HTML")
    else:
        await context.bot.send_message(chat_id=chat_id, text=caption, parse_mode="HTML")

    # Agendamento - Passa o ID na DATA para recuperar como string
    context.job_queue.run_once(
        finish_travel_job, 
        when=secs,
        # chat_id é seguro passar como int
        chat_id=chat_id,
        # user_id string vai no data
        data={"dest": dest_key, "user_id": user_id},
        name=f"finish_travel_{user_id}"
    )


# =============================================================================
# Job: finaliza a viagem e abre o menu da região
# =============================================================================
async def finish_travel_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    # Recupera ID string do payload
    user_id = str(job.data.get("user_id") or job.user_id) 
    chat_id = job.chat_id
    dest = (job.data or {}).get("dest")

    # Finaliza (pode ser síncrono ou async dependendo da implementação)
    # Aqui assumimos que try_finalize... é robusto ou que _auto_finalize... resolve
    await _auto_finalize_travel_if_due(context, user_id)

    # Abre o menu
    await send_region_menu(context, user_id, chat_id)

# =============================================================================
# Wrapper: abrir o menu da região atual (usado por /start e outros)
# =============================================================================
async def show_region_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = getattr(update, "callback_query", None)
    
    # 🔒 SEGURANÇA
    user_id = get_current_player_id(update, context)
    chat_id = update.effective_chat.id
    
    if query:
        await query.answer()
        try: await query.delete_message()
        except Exception: pass
        chat_id = query.message.chat_id

    if not user_id:
        return

    await _auto_finalize_travel_if_due(context, user_id)
    await send_region_menu(context, user_id, chat_id)

# =============================================================================
# Exports (registre no main)
# =============================================================================
region_handler  = CallbackQueryHandler(region_callback, pattern=r'^region_[A-Za-z0-9_]+$')
travel_handler  = CallbackQueryHandler(show_travel_menu, pattern=r'^travel$')