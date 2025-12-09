# handlers/menu/region.py
# (VERSÃO CORRIGIDA: Lida corretamente com edição de mensagens com mídia no menu de durabilidade)

import time
import logging
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest
from modules import player_manager, game_data
from modules.player.premium import PremiumManager
from handlers.world_boss.engine import world_boss_manager, BOSS_STATS
from modules.game_data.worldmap import WORLD_MAP
from modules import file_ids as file_id_manager
from handlers.menu.kingdom import show_kingdom_menu
from modules.dungeons.registry import get_dungeon_for_region
from modules.game_data.worldmap import WORLD_MAP
from modules.game_data import monsters as monsters_data
from handlers.christmas_shop import is_event_active

logger = logging.getLogger(__name__)

try:
    from modules import file_id_manager as media_ids
except Exception:
    try:
        from modules import file_ids as media_ids
    except Exception:
        media_ids = None

# Menu principal do reino (fallback)
try:
    from handlers.menu.kingdom import show_kingdom_menu
except Exception:
    show_kingdom_menu = None 

# Botão Dungeon
try:
    from modules.dungeons.runtime import build_region_dungeon_button
except Exception:
    build_region_dungeon_button = None

# --- Função Auxiliar para Edição Segura ---
async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    """
    Tenta editar a legenda ou texto da mensagem. Se falhar (ex: conflito mídia/texto),
    apaga a mensagem antiga e envia uma nova.
    """
    if query:
        try:
            # Tenta editar legenda (se for foto/vídeo)
            await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
            return
        except Exception:
            pass
        try:
            # Tenta editar texto (se for mensagem de texto puro)
            await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
            return
        except Exception:
            # Se falhar a edição (ex: mudar de foto para texto), tenta apagar
            try:
                await query.delete_message()
            except Exception:
                pass
    
    # Se não foi possível editar ou se a mensagem foi apagada, envia uma nova
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)


def _humanize_duration(seconds: int) -> str:
    seconds = int(seconds)
    if seconds >= 60:
        mins = round(seconds / 60)
        return f"{mins} min"
    return f"{seconds} s"

def _default_travel_seconds() -> int:
    return int(getattr(game_data, "TRAVEL_DEFAULT_SECONDS", 360))

def _get_travel_time_seconds(player_data: dict, dest_key: str) -> int:
    base = 360 
    try:
        premium = PremiumManager(player_data)
        mult = float(premium.get_perk_value("travel_time_multiplier", 1.0))
    except Exception:
        mult = 1.0 
    return max(0, int(round(base * mult)))

async def _auto_finalize_travel_if_due(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """
    Se o player estiver em 'travel' e o tempo já passou (pós-restart),
    finaliza silenciosamente e retorna True.
    """
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
            except Exception:
                pass 
                
        # Fallback para o formato antigo (timestamp float)
        finish_ts = float(state.get("travel_finish_ts") or 0)
        if finish_ts > 0 and time.time() >= finish_ts:
            dest = state.get("travel_dest")
            if dest and dest in (game_data.REGIONS_DATA or {}):
                player["current_location"] = dest
            player["player_state"] = {"action": "idle"}
            await player_manager.save_player_data(user_id, player)
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
    player_data = await player_manager.get_player_data(user_id) or {} 
    current_location = player_data.get("current_location", "reino_eldora")
    region_info = (game_data.REGIONS_DATA or {}).get(current_location) or {}
    
    # --- LÓGICA VIP ---
    is_vip = False
    try:
        is_vip = PremiumManager(player_data).is_premium()
    except Exception:
        pass

    if is_vip:
        # --- 👇 DEFINA A SUA ORDEM AQUI 👇 ---
        REGION_ORDER = [
            "reino_eldora",
            "pradaria_inicial",
            "floresta_sombria",
            "campos_linho",
            "pedreira_granito",
            "mina_ferro",
            "pantano_maldito",
            "pico_grifo",
            "forja_abandonada",
            "picos_gelados",
            "deserto_ancestral"
        ]
        # ------------------------------------

        # Pega todas as regiões que existem no jogo
        all_regions = list((game_data.REGIONS_DATA or {}).keys())
        
        # Ordena a lista com base na sua REGION_ORDER
        all_regions.sort(key=lambda k: REGION_ORDER.index(k) if k in REGION_ORDER else 999)

        # Remove a localização atual da lista de destinos
        possible_destinations = [r for r in all_regions if r != current_location]
        
        caption = (
            f"🗺 <b>🄼🄰🄿🄰 🄼🅄🄽🄳🄸 (VIP)</b> 🗺\n"
            f"𝑽𝒐𝒄𝒆̂ 𝒆𝒔𝒕𝒂́ 𝒆𝒎 <b>{region_info.get('display_name','Desconhecido')}</b>.\n\n"
            f"𝑪𝒐𝒎𝒐 𝒗𝒊𝒂𝒋𝒂𝒏𝒕𝒆 𝒅𝒆 𝒆𝒍𝒊𝒕𝒆, 𝒗𝒐𝒄𝒆̂ 𝒑𝒐𝒔𝒔𝒖𝒊 𝒂 <b>𝐏𝐞𝐝𝐫𝐚 𝐃𝐢𝐦𝐞𝐧𝐬𝐢𝐨𝐧𝐚𝐥</b>. "
            f"𝑬𝒍𝒂 𝒑𝒆𝒓𝒎𝒊𝒕𝒆 𝒒𝒖𝒆 𝒗𝒐𝒄𝒆̂ 𝒂𝒕𝒊𝒗𝒆 𝒐𝒔 𝒑𝒐𝒓𝒕𝒂𝒊𝒔 𝒅𝒆 𝒗𝒊𝒂𝒈𝒆𝒎 𝒆𝒎 𝒒𝒖𝒂𝒍𝒒𝒖𝒆𝒓 𝒓𝒆𝒈𝒊𝒂̃𝒐,"
            f"𝒗𝒊𝒂𝒋𝒂𝒏𝒅𝒐 𝒑𝒂𝒓𝒂 𝒒𝒖𝒂𝒍𝒒𝒖𝒆𝒓 𝒅𝒆𝒔𝒕𝒊𝒏𝒐 𝒔𝒆𝒎 𝒓𝒆𝒔𝒕𝒓𝒊𝒄̧𝒐̃𝒆𝒔!"
        )
    else:
        # Jogador normal vê apenas vizinhos (como definido no WORLD_MAP)
        possible_destinations = WORLD_MAP.get(current_location, [])
        caption = (
            f"𝑽𝒐𝒄𝒆̂ 𝒆𝒔𝒕𝒂́ 𝒆𝒎 <b>{region_info.get('display_name','Desconhecido')}</b>.\n"
            f"𝑷𝒂𝒓𝒂 𝒐𝒏𝒅𝒆 𝒅𝒆𝒔𝒆𝒋𝒂 𝒗𝒊𝒂𝒋𝒂𝒓?"
        )
    # ------------------

    keyboard = []
    for dest_key in possible_destinations:
        dest_info = (game_data.REGIONS_DATA or {}).get(dest_key, {})
        # Garante que não cria botões para regiões que não existem no REGIONS_DATA
        if not dest_info: continue
        
        button = InlineKeyboardButton(
            f"{dest_info.get('emoji', '')} {dest_info.get('display_name', dest_key)}",
            callback_data=f"region_{dest_key}",
        )
        keyboard.append([button])

    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data=f'open_region:{current_location}')])
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

async def open_region_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    
    try:
        region_key = query.data.split(':')[1]
    except IndexError:
        region_key = 'reino_eldora'

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
    
    try:
        region_key = query.data.split(':')[1]
    except IndexError:
        await query.answer("Região não especificada.", show_alert=True)
        return
        
    region_info = game_data.REGIONS_DATA.get(region_key, {})
    if not region_info:
        await query.answer("Informação da região não encontrada.", show_alert=True)
        return
        
    # --- Monta a Mensagem de Informação ---
    info_parts = [
        f"ℹ️ <b>Sobre: {region_info.get('display_name', region_key)}</b>",
        f"<i>{region_info.get('description', 'Nenhuma descrição disponível.')}</i>\n"
    ]
    
    info_parts.append("<b>Ações Possíveis:</b>")
    
    # --- LÓGICA INTELIGENTE ---
    if region_key == 'reino_eldora':
        info_parts.append(" 🏇 - Viajar para outras regiões")
        info_parts.append(" 🔰 - Aceder à Guilda")
        info_parts.append(" 🛒 - Visitar o Mercados")
        info_parts.append(" ⚒️ - Refino e Forja")
        info_parts.append(" 👤 - Gerir o teu Personagem")
        info_parts.append(" 🧧 - Participar em Eventos")
    else:
        monsters_in_region = monsters_data.MONSTERS_DATA.get(region_key, [])
        
        if region_info.get('resource'):
            info_parts.append("- Coletar recursos")
        
        if monsters_in_region:
            info_parts.append("- Caçar monstros")
            
        if get_dungeon_for_region(region_key):
            info_parts.append("- Entrar em Calabouço")
            
        if region_key == 'floresta_sombria':
            info_parts.append("- Visitar a Tenda do Alquimista")
    
    info_parts.append("")

    if region_key != 'reino_eldora':
        info_parts.append("<b>Criaturas na Região:</b>")
        monsters_in_region = monsters_data.MONSTERS_DATA.get(region_key, [])
        if not monsters_in_region:
            info_parts.append("- <i>Nenhuma criatura catalogada.</i>")
        else:
            for monster in monsters_in_region:
                info_parts.append(f"- {monster.get('name', 'Criatura Desconhecida')}")
            
    text = "\n".join(info_parts)
    
    back_callback = 'continue_after_action' if region_key == 'reino_eldora' else f"open_region:{region_key}"
    keyboard = [[InlineKeyboardButton("⬅️ Voltar", callback_data=back_callback)]]
    
    # Usa a função segura para editar
    await _safe_edit_or_send(query, context, query.message.chat_id, text, InlineKeyboardMarkup(keyboard))

async def send_region_menu(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, region_key: str | None = None, player_data: dict | None = None):
    """
    Envia a mensagem com a mídia e os botões da região especificada.
    (VERSÃO ATUALIZADA COM BOTÕES DE AUTO-HUNT E STATUS COMPLETO)
    """
    print(">>> RASTREAMENTO: Entrou em send_region_menu")
    
    if player_data is None:
        player_data = await player_manager.get_player_data(user_id) or {}
    
    final_region_key = region_key or player_data.get("current_location", "reino_eldora")
    player_data['current_location'] = final_region_key
    
    region_info = (game_data.REGIONS_DATA or {}).get(final_region_key)

    if not region_info or final_region_key == "reino_eldora":
        if show_kingdom_menu:
            try:
                # Gambiarra para chamar o show_kingdom_menu sem update real se necessário
                # Mas o ideal é que o show_kingdom_menu suporte chamadas diretas.
                # Aqui simplificamos:
                user_obj = type("User", (), {"id": user_id})()
                chat_obj = type("Chat", (), {"id": chat_id})()
                msg_obj = type("Message", (), {"from_user": user_obj, "chat": chat_obj})()
                fake_update = Update(update_id=0, message=msg_obj)
                await show_kingdom_menu(fake_update, context, player_data=player_data)
            except Exception as e_fake:
                logger.error(f"Falha ao criar fake_update para show_kingdom_menu: {e_fake}")
                await context.bot.send_message(chat_id=chat_id, text="Você está no Reino de Eldora.", parse_mode="HTML")
        else:
            await context.bot.send_message(chat_id=chat_id, text="Você está no Reino de Eldora.", parse_mode="HTML")
        return 

    # --- LÓGICA DO WORLD BOSS ---
    is_boss_active = world_boss_manager.is_active
    boss_location = world_boss_manager.boss_location

    if is_boss_active and final_region_key == boss_location:
        
        caption = (
            f"‼️ **PERIGO IMINENTE** ‼️\n\n"
            f"O **Demônio Dimensional** está nesta região!\n\n"
            f"{world_boss_manager.get_status_text()}"
        )
        keyboard = [
            [InlineKeyboardButton("⚔️ ATACAR O DEMÔNIO ⚔️", callback_data='wb_attack')],
            [InlineKeyboardButton("👤 Personagem", callback_data='profile')],
            [InlineKeyboardButton("🗺️ Ver Mapa", callback_data='travel')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        file_data = media_ids.get_file_data(BOSS_STATS.get("media_key"))
        if not file_data or not file_data.get("id"):
            file_data = media_ids.get_file_data(f"regiao_{final_region_key}")

    else:
        # --- SENÃO, mostra o menu normal da região ---
        premium = PremiumManager(player_data)
        
        total_stats = await player_manager.get_player_total_stats(player_data)
        
        current_hp = int(player_data.get("current_hp", 0))
        max_hp = int(total_stats.get("max_hp", 0)) 
        current_mp = int(player_data.get("current_mp", 0))
        max_mp = int(total_stats.get("max_mana", 0))
        current_energy = int(player_data.get("energy", 0))
        max_energy = int(player_manager.get_player_max_energy(player_data))
        p_gold = player_manager.get_gold(player_data)
        p_gems = player_manager.get_gems(player_data)
        
        status_footer = (
            f"\n\n═════════════ ◆◈◆ ══════════════\n"
            f"💰 𝐎𝐮𝐫𝐨: {p_gold:,}   💎 𝐆𝐞𝐦𝐚𝐬: {p_gems:,}\n"
            f"❤️ 𝐇𝐏: {current_hp}/{max_hp}   💙 𝐌𝐚𝐧𝐚: {current_mp}/{max_mp}\n"
            f"⚡️ 𝐄𝐧𝐞𝐫𝐠𝐢𝐚: {current_energy}/{max_energy}"
        )
        caption = (
            f"Você está em <b>{region_info.get('display_name', 'Região Desconhecida')}</b>.\n"
            f"O que deseja fazer?{status_footer}"
        )

        keyboard = []

        if final_region_key == 'floresta_sombria':
            keyboard.append([InlineKeyboardButton("⛺ Visitar Tenda do Alquimista", callback_data='npc_trade:alquimista_floresta')])
        
        if final_region_key == 'deserto_ancestral':
            keyboard.append([InlineKeyboardButton("🧙‍♂️ Cabana do Místico (Runas)", callback_data='rune_npc:main')])

        if final_region_key == 'picos_gelados' and is_event_active():
             keyboard.append([InlineKeyboardButton("🎅 Cabana do Noel", callback_data="christmas_shop_open")])
                 
        keyboard.append([InlineKeyboardButton("⚔️ Caçar Monstro ", callback_data=f"hunt_{final_region_key}")])

        if premium.is_premium():
            keyboard.append([
                InlineKeyboardButton("⏱ 10x", callback_data=f"autohunt_start_10_{final_region_key}"),
                InlineKeyboardButton("⏱ 25x", callback_data=f"autohunt_start_25_{final_region_key}"),
                InlineKeyboardButton("⏱ 35x", callback_data=f"autohunt_start_35_{final_region_key}"),
            ])

        if build_region_dungeon_button:
            try:
                dungeon_button = build_region_dungeon_button(final_region_key)
                if dungeon_button:
                        keyboard.append([dungeon_button])
            except Exception:
                pass 
        else:
             if get_dungeon_for_region(final_region_key):
                keyboard.append([InlineKeyboardButton("🏰 Calabouço", callback_data=f"dungeon_open:{final_region_key}")])

        keyboard.append([InlineKeyboardButton("👤 Personagem", callback_data="profile")])
        keyboard.append([InlineKeyboardButton("📜 Restaurar Durabilidade", callback_data="restore_durability_menu")])
        keyboard.append([InlineKeyboardButton("ℹ️ Sobre a Região", callback_data=f"region_info:{final_region_key}")])
        
        resource_id = region_info.get("resource")
        if resource_id:
            required_profession = game_data.get_profession_for_resource(resource_id)
            player_prof = (player_data.get("profession", {}) or {}).get("type")
            
            if required_profession and required_profession == player_prof:
                profession_resources = (game_data.PROFESSIONS_DATA.get(required_profession, {}) or {}).get('resources', {})
                item_id_yielded = profession_resources.get(resource_id, resource_id)
                item_yielded_info = (game_data.ITEMS_DATA or {}).get(item_id_yielded, {}) or {}
                item_name = item_yielded_info.get("display_name", item_id_yielded.capitalize())
                profession_info = (game_data.PROFESSIONS_DATA or {}).get(required_profession, {}) or {}
                profession_emoji = profession_info.get("emoji", "✋")
                
                base_secs = int(getattr(game_data, "COLLECTION_TIME_MINUTES", 1) * 60)
                speed_mult = float(premium.get_perk_value("gather_speed_multiplier", 1.0))
                duration_seconds = max(1, int(base_secs / max(0.25, speed_mult)))
                human_time = _humanize_duration(duration_seconds)
                energy_cost = int(premium.get_perk_value("gather_energy_cost", 1))
                cost_txt = "grátis" if energy_cost == 0 else f"-{energy_cost} ⚡️"

                keyboard.append([InlineKeyboardButton(
                    f"{profession_emoji} Coletar {item_name} (~{human_time}, {cost_txt})",
                    callback_data=f"collect_{resource_id}"
                )])

        keyboard.append([InlineKeyboardButton("🗺️ Ver Mapa", callback_data="travel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        file_data = media_ids.get_file_data(f"regiao_{final_region_key}")

    try:
        if file_data and file_data.get("id"):
            media_type = (file_data.get("type") or "photo").lower()
            if media_type == "video":
                await context.bot.send_video(chat_id=chat_id, video=file_data["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
            else:
                await context.bot.send_photo(chat_id=chat_id, photo=file_data["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
        else:
            raise ValueError("No valid media found, falling back to text.")
    except Exception as e:
        logger.warning(f"Falha ao enviar menu da região '{final_region_key}'. Erro: {e}. Usando fallback de texto.")
        await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML")

# =============================================================================
# Validação da viagem e início do cronômetro
# =============================================================================
def _is_neighbor(world_map: dict, cur: str, dest: str) -> bool:
    if cur == dest: return True
    neighbors_of_current_location = (world_map or {}).get(cur, [])
    return dest in neighbors_of_current_location

async def region_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
    chat_id = q.message.chat_id

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

    is_vip = PremiumManager(player).is_premium()
    if not is_vip and not _is_neighbor(WORLD_MAP, cur, dest_key):
        await q.answer("Você não pode viajar direto para lá.", show_alert=True)
        return

    travel_cost = int(((game_data.REGIONS_DATA or {}).get(dest_key, {}) or {}).get("travel_cost", 0))
    energy = int(player.get("energy", 0))
    if travel_cost > 0 and energy < travel_cost:
        await q.answer("Energia insuficiente para viajar.", show_alert=True)
        return

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

    finish_time = datetime.now(timezone.utc) + timedelta(seconds=secs)
    player["player_state"] = {
        "action": "travel",
        "finish_time": finish_time.isoformat(),
        "details": {
            "destination": dest_key
        }
    }
    await player_manager.save_player_data(user_id, player)

    try: await q.delete_message()
    except Exception: pass

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

    context.job_queue.run_once(
        finish_travel_job,
        when=secs,
        user_id=user_id,
        chat_id=chat_id,
        data={"dest": dest_key},
        name=f"finish_travel_{user_id}"
    )

async def finish_travel_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id = job.user_id
    chat_id = job.chat_id
    dest = (job.data or {}).get("dest")

    player = await player_manager.get_player_data(user_id) or {}
    state = player.get("player_state", {})

    if state.get("action") != "travel":
        return

    player["current_location"] = dest
    player["player_state"] = {"action": "idle"}
    await player_manager.save_player_data(user_id, player)
    
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

    resource_id = data.replace("collect_", "", 1)
    
    if resource_id not in (game_data.ITEMS_DATA or {}):
        await q.answer("Recurso desconhecido.", show_alert=True)
        return

    player = await player_manager.get_player_data(user_id) or {}
    cur_loc = player.get("current_location", "reino_eldora")
    
    current_region_info = (game_data.REGIONS_DATA or {}).get(cur_loc, {})
    if current_region_info.get("resource") != resource_id:
        await q.answer("Você não pode coletar este recurso nesta região.", show_alert=True)
        return

    required_profession = game_data.get_profession_for_resource(resource_id)
    prof_data = player.get("profession", {}) or {}
    player_prof = prof_data.get("type")
    if not required_profession or required_profession != player_prof:
        await q.answer("Sua profissão não permite coletar aqui.", show_alert=True)
        return

    try:
        premium = PremiumManager(player)
        energy_cost = int(premium.get_perk_value("gather_energy_cost", 1))
        speed_mult = float(premium.get_perk_value("gather_speed_multiplier", 1.0))
    except Exception:
        try:
            energy_cost = int(player_manager.get_player_perk_value(player, "gather_energy_cost", 1))
        except Exception:
            energy_cost = 1
        try:
            speed_mult = float(player_manager.get_player_perk_value(player, "gather_speed_multiplier", 1.0))
        except Exception:
            speed_mult = 1.0

    cur_energy = int(player.get("energy", 0))
    if energy_cost > 0 and cur_energy < energy_cost:
        await q.answer("Energia insuficiente para coletar.", show_alert=True)
        return

    base_secs = int(getattr(game_data, "COLLECTION_TIME_MINUTES", 1) * 60)
    speed_mult = max(0.25, min(4.0, speed_mult))
    duration_seconds = max(1, int(base_secs / speed_mult))

    if energy_cost > 0:
        player["energy"] = max(0, cur_energy - energy_cost)
    
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
    await player_manager.save_player_data(user_id, player)

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


async def show_region_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, region_key: str | None = None, player_data: dict | None = None):
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
    try:
        await player_manager.try_finalize_timed_action_for_user(user_id)
    except Exception as e_finalize:
        logger.warning(f"Falha ao tentar finalizar ação em show_region_menu: {e_finalize}")

    final_region_key = region_key
   
    if not final_region_key:
       if player_data is None: 
            player_data = await player_manager.get_player_data(user_id)
            final_region_key = (player_data or {}).get("current_location", "reino_eldora")

    await send_region_menu(context, user_id, chat_id, region_key=final_region_key, player_data=player_data)

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
    uid = q.from_user.id
    pdata = await player_manager.get_player_data(uid) or {}
    
    lines = ["<b>📜 Restaurar Durabilidade</b>\nEscolha um item:\n"]
    kb = []
    
    inv, equip = pdata.get("inventory", {}), pdata.get("equipment", {})
    any_rep = False
    
    for slot, uid_item in equip.items():
        inst = inv.get(uid_item)
        if isinstance(inst, dict):
            cur, mx = _dur_tuple(inst.get("durability"))
            if cur < mx:
                any_rep = True
                nm = (game_data.ITEMS_DATA or {}).get(inst.get("base_id"), {}).get("display_name", "Item")
                lines.append(f"• {nm} ({cur}/{mx})")
                kb.append([InlineKeyboardButton(f"Reparar {nm}", callback_data=f"rd_fix_{uid_item}")])
    
    if not any_rep: lines.append("<i>Nenhum item precisa de reparo.</i>")
    
    loc = pdata.get("current_location", "reino_eldora")
    
    if loc == 'reino_eldora':
        back_callback = 'continue_after_action'
    else:
        back_callback = f"open_region:{loc}"
        
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data=back_callback)])
    
    # CORREÇÃO APLICADA AQUI: USA _safe_edit_or_send
    await _safe_edit_or_send(q, context, q.message.chat_id, "\n".join(lines), InlineKeyboardMarkup(kb))


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
        await show_restore_durability_menu(update, context)
        return

    await player_manager.save_player_data(user_id, pdata)

    await q.answer("Durabilidade restaurada!", show_alert=True)
    await show_restore_durability_menu(update, context)


# =============================================================================
# Exports (registre no main)
# =============================================================================
region_handler = CallbackQueryHandler(region_callback, pattern=r"^region_[A-Za-z0-9_]+$")
travel_handler = CallbackQueryHandler(show_travel_menu, pattern=r"^travel$")
collect_handler = CallbackQueryHandler(collect_callback, pattern=r"^collect_[A-Za-z0-9_]+$")
open_region_handler = CallbackQueryHandler(open_region_callback, pattern=r"^open_region:")

# Atalhos locais de durabilidade
restore_durability_menu_handler = CallbackQueryHandler(show_restore_durability_menu, pattern=r"^restore_durability_menu$")
restore_durability_fix_handler = CallbackQueryHandler(fix_item_durability, pattern=r"^rd_fix_.+$")

region_info_handler = CallbackQueryHandler(region_info_callback, pattern=r"^region_info:.*$")