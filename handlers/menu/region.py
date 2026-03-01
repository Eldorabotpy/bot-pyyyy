# handlers/menu/region.py
# (VERSÃO FINAL CORRIGIDA + GUERRA DE CLÃS: Botão Atacar/Conquistar só p/ registrados)

import time
import logging
import html

from datetime import datetime, timezone, timedelta

from pvp import pvp_battle
from pvp import pvp_utils
from bson import ObjectId
from modules.player.core import players_collection  # para acessar database

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

# --- IMPORTS DE MÓDULOS ---
from modules import player_manager, game_data
from modules import file_ids as file_id_manager
from modules import file_ids
from ui.ui_renderer import render_media_or_text
from modules.player.premium import PremiumManager
from modules.player import actions as player_actions
from modules.game_data import monsters as monsters_data
from modules.game_data.worldmap import WORLD_MAP
from modules.dungeons.registry import get_dungeon_for_region
from modules.auth_utils import get_current_player_id, requires_login
from modules.guild_war.combat_integration import process_war_pvp_result # <--- Importante!
from pvp import pvp_battle, pvp_utils
from modules.game_data import regions as game_data_regions
from modules.guild_war.campaign import ensure_weekly_campaign
from modules.guild_war.region import CampaignPhase
from handlers.job_handler import _dur_tuple

# --- GUERRA DE CLÃS ---
# Usa seu engine central (gate oficial para mostrar botões e bloquear callbacks)
try:
    from modules import clan_war_engine
except Exception:
    clan_war_engine = None
WAR_PRESENCE_COL = None
try:
    if players_collection is not None:
        WAR_PRESENCE_COL = players_collection.database["clan_war_presence"]
except Exception:
    WAR_PRESENCE_COL = None

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

# Importa DIRETAMENTE do seu arquivo premium.py
from modules.game_data.premium import PREMIUM_TIERS

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
            try:
                await query.delete_message()
            except Exception:
                pass

    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)


def _humanize_duration(seconds: int) -> str:
    seconds = int(seconds)
    if seconds >= 60:
        mins = round(seconds / 60)
        return f"{mins} min"
    return f"{seconds} s"


def _get_travel_time_seconds(player_data: dict, dest_key: str) -> int:
    """Calcula o tempo de viagem (VIP = 0)."""
    tier = str(player_data.get("premium_tier", "free")).lower().strip()
    if tier in ["lenda", "vip", "admin", "premium"]:
        return 0

    base = 360
    try:
        pm = PremiumManager(player_data)
        mult = float(pm.get_perk_value("travel_time_multiplier", 1.0))
        if mult <= 0.01:
            return 0
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
            except Exception:
                pass
    return False


def _get_player_clan_id_fallback(pdata: dict):
    """
    Fallback local para extrair clan_id sem depender do engine.
    Compatível com variações de schema (clan_id / guild_id / clan._id / guild._id).
    """
    if not isinstance(pdata, dict):
        return None

    cid = pdata.get("clan_id") or pdata.get("guild_id")
    if cid:
        return cid

    obj = pdata.get("clan") or pdata.get("guild")
    if isinstance(obj, dict):
        return obj.get("_id") or obj.get("id")

    return None


# =============================================================================
# Menus de Navegação (Mapa e Info)
# =============================================================================

@requires_login
async def show_travel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = get_current_player_id(update, context)
    chat_id = query.message.chat_id

    player_data = await player_manager.get_player_data(user_id) or {}
    current_location = player_data.get("current_location", "reino_eldora")
    region_info = (game_data.REGIONS_DATA or {}).get(current_location) or {}

    # --- CHECK VIP ---
    is_vip = False
    try:
        tier = str(player_data.get("premium_tier", "free")).lower().strip()
        if tier in ["lenda", "vip", "premium", "admin"]:
            is_vip = True
    except Exception:
        pass

    if is_vip:
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
        if not dest_info:
            continue
        d_name = dest_info.get('display_name', dest_key)
        d_emoji = dest_info.get('emoji', '📍')
        row.append(InlineKeyboardButton(f"{d_emoji} {d_name}", callback_data=f"region_{dest_key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("⬅️ 𝐂𝐚𝐧𝐜𝐞𝐥𝐚𝐫", callback_data=f'open_region:{current_location}')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await query.delete_message()
    except Exception:
        pass

    fd = media_ids.get_file_data("mapa_mundo")
    if fd and fd.get("id"):
        try:
            if (fd.get("type") or "photo").lower() == "video":
                await context.bot.send_video(chat_id=chat_id, video=fd["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
            else:
                await context.bot.send_photo(chat_id=chat_id, photo=fd["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
            return
        except Exception:
            pass

    await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML")

@requires_login
async def open_region_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.message:
        return

    try:
        await query.answer()
    except Exception:
        pass

    user_id = get_current_player_id(update, context)
    if not user_id:
        return

    chat_id = getattr(query.message, "chat_id", None) or (update.effective_chat.id if update.effective_chat else None)
    if not chat_id:
        return

    # region_key
    data = query.data or ""
    try:
        region_key = data.split(":", 1)[1]
    except Exception:
        region_key = "reino_eldora"

    # carrega player
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        return

    # salva local
    player_data["current_location"] = region_key
    await player_manager.save_player_data(user_id, player_data)

    # limpa mensagem anterior (opcional)
    try:
        await query.delete_message()
    except Exception:
        pass

    # abre menu da região
    await send_region_menu(context, user_id, chat_id)

@requires_login
async def region_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        region_key = query.data.split(':')[1]
    except IndexError:
        return

    region_info = game_data.REGIONS_DATA.get(region_key, {})
    info_parts = [f"ℹ️ <b>{region_info.get('display_name', region_key)}</b>", f"<i>{region_info.get('description', '')}</i>\n"]

    if region_key == 'reino_eldora':
        info_parts.extend([" 🏇 - 𝐕𝐢𝐚𝐣𝐚𝐫 ", " 🔰 - 𝐆𝐮𝐢𝐥𝐝𝐚", " 🛒 - 𝐌𝐞𝐫𝐜𝐚𝐝𝐨", " ⚒️ - 𝐅𝐨𝐫𝐣𝐚"])
    else:
        if region_info.get('resource'):
            info_parts.append("- Coleta disponível")
        if monsters_data.MONSTERS_DATA.get(region_key):
            info_parts.append("- Caça disponível")
        if get_dungeon_for_region(region_key):
            info_parts.append("- Calabouço")

    info_parts.append("\n<b>Criaturas:</b>")
    mons = monsters_data.MONSTERS_DATA.get(region_key, [])
    if not mons:
        info_parts.append("- <i>Nenhuma.</i>")
    else:
        for m in mons:
            info_parts.append(f"- {m.get('name', '???')}")

    text = "\n".join(info_parts)
    back_cb = 'continue_after_action' if region_key == 'reino_eldora' else f"open_region:{region_key}"
    keyboard = [[InlineKeyboardButton("⬅️ 𝐕𝐎𝐋𝐓𝐀𝐑", callback_data=back_cb)]]
    await _safe_edit_or_send(query, context, query.message.chat_id, text, InlineKeyboardMarkup(keyboard))


# =============================================================================
# Menu Principal da Região
# =============================================================================

@requires_login
async def continue_after_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler usado como "Voltar" genérico (muito usado no Reino).
    """
    query = update.callback_query
    await query.answer()

    user_id = get_current_player_id(update, context)
    chat_id = query.message.chat_id

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await context.bot.send_message(chat_id, "Sessão inválida.")
        return

    loc = player_data.get("current_location", "reino_eldora")

    try:
        await query.delete_message()
    except Exception:
        pass

    if loc == "reino_eldora":
        if show_kingdom_menu:
            # mantém compatível com seu padrão atual
            await show_kingdom_menu(None, context, player_data=player_data, chat_id=chat_id)
        else:
            await context.bot.send_message(chat_id, "🏰 Reino de Eldora")
    else:
        await send_region_menu(context, user_id, chat_id)

@requires_login
async def war_pvp_fight_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Executa a luta PvP da Guerra de Clãs.
    """
    query = update.callback_query
    # Responde rápido ao clique para parar o "reloginho" do botão
    try:
        await query.answer()
    except:
        pass
    
    # 1. Identifica os lutadores
    user_id = get_current_player_id(update, context)
    
    try:
        # Formato esperado: "pvp_fight_start:ID_DO_INIMIGO"
        enemy_id = query.data.split(":")[1]
    except IndexError:
        await query.answer("❌ Erro ao identificar oponente.", show_alert=True)
        return

    # Verifica se não é você mesmo (bug de radar/cache)
    if str(user_id) == str(enemy_id):
        await query.answer("Você não pode lutar contra si mesmo!", show_alert=True)
        return

    # 2. Carrega dados para validar e exibir
    pdata = await player_manager.get_player_data(user_id)
    enemy_data = await player_manager.get_player_data(enemy_id)
    
    if not enemy_data:
        await query.edit_message_text("❌ Oponente não encontrado (pode ter deslogado ou mudado de região).")
        return

    # 3. EXECUTA A BATALHA (Simulação)
    # A função simular_batalha_completa calcula o vencedor baseada nos stats reais,
    # mas sem gastar tickets da Arena comum.
    try:
        winner_id, log = await pvp_battle.simular_batalha_completa(
            user_id,
            enemy_id,
            modifier_effect=None, 
            nivel_padrao=None
        )
    except Exception as e:
        logger.error(f"Erro na simulação PvP Guerra: {e}")
        await query.answer("Erro ao simular combate. Tente novamente.", show_alert=True)
        return
    
    # Define quem ganhou e quem perdeu
    is_win = (str(winner_id) == str(user_id))
    loser_id = enemy_id if is_win else user_id

    # 4. APLICA AS REGRAS DA GUERRA (Pontos, Ban, Cooldown)
    # process_war_pvp_result aplica:
    # - Vitória: Cooldown de ataque (5 min) + Pontos pro Clã
    # - Derrota: Ban de PvE (30 min) + Perda de Pontos
    try:
        from modules.game_data import regions as game_data_regions
        await process_war_pvp_result(
            winner_id=str(winner_id), 
            loser_id=str(loser_id), 
            game_data_regions_module=game_data_regions
        )
    except Exception as e:
        logger.error(f"Erro ao processar resultado PvP Guerra (DB): {e}")

    # 5. GERAR O RELATÓRIO VISUAL (Log da Luta)
    my_name = html.escape(pdata.get("character_name", "Você"))
    enemy_name = html.escape(enemy_data.get("character_name", "Inimigo"))
    
    # Pega as últimas 8 linhas do log para não poluir a tela
    try:
        summary_log = "\n".join(log[-8:])
    except:
        summary_log = "Detalhes do combate indisponíveis."

    # Cabeçalho muda se ganhou ou perdeu
    if is_win:
        header = f"🏆 <b>VITÓRIA NA GUERRA!</b>\n<i>Você derrotou {enemy_name}!</i>"
        status_txt = (
            "✅ <b>Inimigo neutralizado!</b> (Ban PvE 30m)\n"
            "📈 <b>+Pontos</b> garantidos para seu Clã.\n"
            "⏳ Você entrou em cooldown de ataque."
        )
    else:
        header = f"💀 <b>VOCÊ FOI DERROTADO!</b>\n<i>{enemy_name} te venceu...</i>"
        status_txt = (
            "🚫 <b>Você está ferido!</b> (30m sem caçar)\n"
            "📉 Seu clã perdeu pontos de influência.\n"
            "Recupere-se antes de tentar novamente."
        )

    msg_text = (
        f"{header}\n\n"
        f"⚔️ <b>Log de Combate:</b>\n"
        f"<blockquote expandable>{summary_log}</blockquote>\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{status_txt}"
    )

    # Botões de Navegação
    # Garante que temos a região para o botão de voltar
    current_region = pdata.get("current_location", "floresta_sombria")
    
    kb = [
        # CORREÇÃO: callback deve ser 'pvp_search_targets' para reabrir o radar
        [InlineKeyboardButton("🔭 Buscar Outro Alvo", callback_data="pvp_search_targets")],
        [InlineKeyboardButton("⬅️ Voltar para Região", callback_data=f"open_region:{current_region}")]
    ]
    reply_markup = InlineKeyboardMarkup(kb)

    # 6. ENVIAR COM FOTO/VÍDEO (Do Oponente)
    # Tenta limpar a mensagem anterior (radar) para focar no resultado
    try:
        await query.delete_message()
    except Exception:
        pass # Se falhar (msg muito antiga), ignora

    # Busca a mídia da classe do inimigo para ilustrar
    enemy_media = pvp_utils.get_player_class_media(enemy_data)
    
    if enemy_media:
        file_id = enemy_media.get("file_id") or enemy_media.get("id")
        media_type = str(enemy_media.get("type", "photo")).lower()
        
        try:
            if media_type == "video":
                await context.bot.send_video(
                    chat_id=query.message.chat_id,
                    video=file_id,
                    caption=msg_text,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            else:
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=file_id,
                    caption=msg_text,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            return # Enviado com sucesso
        except Exception as e:
            logger.warning(f"Falha ao enviar mídia no PvP ({e}), enviando texto puro.")
            # Se der erro na mídia, cai para o envio de texto abaixo

    # Fallback: Envia apenas texto se não tiver mídia ou der erro
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=msg_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def send_region_menu(
    context: ContextTypes.DEFAULT_TYPE,
    user_id,
    chat_id: int,
    region_key: str | None = None,
    player_data: dict | None = None
):
    if player_data is None:
        player_data = await player_manager.get_player_data(user_id) or {}

    # Sincronia de energia
    if player_actions._apply_energy_autoregen_inplace(player_data):
        await player_manager.save_player_data(user_id, player_data)

    final_region_key = region_key or player_data.get("current_location", "reino_eldora")
    try:
        if clan_war_engine:
            # user_id no seu projeto é ObjectId/str; normaliza para ObjectId (strict)
            # player_manager já trabalha com ObjectId; aqui precisamos do ObjectId real no presence
            from bson import ObjectId as _OID
            pid = user_id if isinstance(user_id, _OID) else (_OID(str(user_id)) if _OID.is_valid(str(user_id)) else None)
            if pid:
                await clan_war_engine.update_presence(pid, player_data, final_region_key, chat_id=chat_id)
    except Exception:
        pass
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
        caption = (f"‼️ 𝐏𝐄𝐑𝐈𝐆𝐎 𝐈𝐌𝐈𝐍𝐄𝐍𝐓𝐄 ‼️\nO 𝕯𝖊𝖒𝖔̂𝖓𝖎𝖔 𝕯𝖎𝖒𝖊𝖓𝖘𝖎𝖔𝖓𝖆𝖑 está aqui!\n\n{hud_text}")
        keyboard = [
            [InlineKeyboardButton("🛡⚔️ 𝐄𝐍𝐓𝐑𝐀𝐑 𝐍𝐀 𝐑𝐀𝐈𝐃 ⚔️🛡", callback_data='wb_menu')],
            [InlineKeyboardButton("🗺️ 𝐅𝐮𝐠𝐢𝐫", callback_data='travel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            fd = media_ids.get_file_data("boss_raid")
            if fd:
                await context.bot.send_photo(chat_id, fd["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
            else:
                await context.bot.send_message(chat_id, caption, reply_markup=reply_markup, parse_mode="HTML")
        except Exception:
            await context.bot.send_message(chat_id, caption, reply_markup=reply_markup, parse_mode="HTML")
        return

    # --- CÁLCULOS DO HUD ---
    # --- CÁLCULOS DO HUD (BLINDADO) ---
    try:
        stats = await player_manager.get_player_total_stats(player_data)
    except Exception:
        stats = {}

    # 1. Correção do Nome (Fim do "None")
    char_name = (
        player_data.get("character_name") or 
        player_data.get("name") or 
        "Aventureiro"
    )
    char_lvl = player_data.get("level", 1)

    prof_data = player_data.get("profession", {}) or {}
    prof_name = prof_data.get("type", "adventurer").capitalize()
    prof_lvl = int(prof_data.get("level", 1))

    tier_key = str(player_data.get("premium_tier", "free")).lower()
    tier_info = PREMIUM_TIERS.get(tier_key, {})
    tier_display = tier_info.get("display_name", tier_key.capitalize())
    if tier_key == "free":
        tier_display = "Comum"

    # 2. Correção do HP e MP (Fim do 0/45)
    p_hp = int(player_data.get('current_hp') or player_data.get('hp') or 0)
    max_hp = int(stats.get('max_hp') or player_data.get('max_hp') or 50)
    
    p_mp = int(player_data.get('current_mp') or player_data.get('mana') or player_data.get('mp') or 0)
    max_mp = int(stats.get('max_mana') or player_data.get('max_mana') or 50)
    
    # 3. Energia e Economia
    try:
        max_en = int(player_manager.get_player_max_energy(player_data))
    except Exception:
        max_en = 20
        
    p_en = int(player_data.get('energy', 0))
    p_gold = int(player_data.get("gold", 0))
    p_gems = int(player_data.get("gems", 0))

    status_hud = (
        f"\n╭┈┈┈┈┈┈┈ [ 𝐏𝐄𝐑𝐅𝐈𝐋 ] ┈┈┈┈┈┈┈┈┈➤\n"
        f"│ ╭┈➤ 👤 {char_name} (𝐍𝐯. {char_lvl})\n"
        f"│ ├┈➤ 🎖️ 𝐏𝐥𝐚𝐧𝐨: <b>{tier_display}</b>\n"
        f"│ ├┈➤ 🛠 {prof_name} [𝐏𝐫𝐨𝐟.nv {prof_lvl}]\n"
        f"│ ├┈➤ ❤️ 𝐇𝐏: {p_hp}/{max_hp}  💙 𝐌𝐏: {p_mp}/{max_mp}\n"
        f"│ ├┈➤ ⚡ 𝐄𝐍𝐄𝐑𝐆𝐈𝐀: 🪫{p_en} /🔋{max_en} \n"
        f"│ ╰┈➤ 💰 {p_gold:,}  💎 {p_gems:,}\n"
        f"╰┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤"
    )

    caption = f"🗺️ Você está em <b>{region_info.get('display_name', 'Região')}</b>.\n╰┈➤ <i>O que deseja fazer?</i>\n{status_hud}"
    keyboard = []

        # =========================================================
    # GUERRA DE CLÃS — BOTÕES CONDICIONAIS (DOMÍNIO + PvP REGIÃO)
    # =========================================================
    try:
        if clan_war_engine:
            # status da guerra
            status = await clan_war_engine.get_war_status()
            season = status.get("season", {}) if isinstance(status, dict) else {}
            is_war_active = bool(season.get("active", False))
            target_region = str(season.get("target_region_id") or "")

            # jogador apto (inscrito/pronto)
            if is_war_active and target_region and final_region_key == target_region:
                keyboard.insert(0, [
                    InlineKeyboardButton("⚔️ Procurar na Região", callback_data="war_pvp_refresh")
                ])

                # 1) Botões de domínio (só faz sentido quando a guerra está ativa)
                state = await clan_war_engine.get_region_control_state(final_region_key)
                owner = state.get("owner_clan_id") if isinstance(state, dict) else None
                my_clan_id = _get_player_clan_id_fallback(player_data)

                if not owner:
                    keyboard.append([
                        InlineKeyboardButton("🛡️ Conquistar Região", callback_data=f"war_claim:{final_region_key}")
                    ])
                elif my_clan_id and str(owner) != str(my_clan_id):
                    keyboard.append([
                        InlineKeyboardButton("🏰 Atacar o Castelo", callback_data=f"war_attack:{final_region_key}")
                    ])

                # 2) PvP de Guerra: aparece NO TOPO apenas na região alvo (e se horário permitir)
                if target_region and final_region_key == target_region:
                    # Se você NÃO quiser limitar por horário, remova esse if e insira direto.
                    keyboard.insert(0, [InlineKeyboardButton("⚔️ Procurar na Região", callback_data="war_pvp_refresh")])


    except Exception as e:
        print(f"Erro menu guerra: {e}")
        pass

    # Botões Especiais (NPCs, Eventos)
    if final_region_key == 'floresta_sombria':
        keyboard.append([InlineKeyboardButton("⛺ 𝐀𝐥𝐪𝐮𝐢𝐦𝐢𝐬𝐭𝐚", callback_data='npc_trade:alquimista_floresta')])

    if final_region_key == 'deserto_ancestral':
        row = [InlineKeyboardButton("🧙‍♂️ 𝐌𝐢́𝐬𝐭𝐢𝐜𝐨", callback_data='rune_npc:main')]
        if can_see_evolution_menu(player_data):
            row.append(InlineKeyboardButton("⛩️ 𝐀𝐬𝐜𝐞𝐧𝐬𝐚̃𝐨", callback_data='open_evolution_menu'))
        keyboard.append(row)

    #if final_region_key == 'picos_gelados' and is_event_active():
        #keyboard.append([InlineKeyboardButton("🎅 𝐍𝐨𝐞𝐥", callback_data="christmas_shop_open")])

    # --- LÓGICA BLINDADA SUPREMA (CHECK VIP) ---
    is_vip_visual = False
    if tier_key in ["premium", "vip", "lenda", "admin"]:
        is_vip_visual = True
    elif max_en > 20:
        is_vip_visual = True  # Fallback

    # --- LINHA DE COMBATE ---
    combat = [InlineKeyboardButton("⚔️ 𝐂𝐚𝐜̧𝐚𝐫", callback_data=f"hunt_{final_region_key}")]

    # Auto Hunt bloqueado se free
    if not is_vip_visual:
        combat.append(InlineKeyboardButton("🤖 𝐀𝐮𝐭𝐨 𝐂𝐚𝐜̧𝐚 (🔒)", callback_data="premium_info"))

    if build_region_dungeon_button:
        btn = build_region_dungeon_button(final_region_key)
        if btn:
            combat.append(btn)
    elif get_dungeon_for_region(final_region_key):
        combat.append(InlineKeyboardButton("🏰 𝐂𝐚𝐥𝐚𝐛𝐨𝐮𝐜̧𝐨", callback_data=f"dungeon_open:{final_region_key}"))

    keyboard.append(combat)

    # --- LINHA VIP: Auto Hunt Rápido ---
    if is_vip_visual:
        keyboard.append([
            InlineKeyboardButton("⏱ 𝟙𝟘𝕩", callback_data=f"autohunt_start_10_{final_region_key}"),
            InlineKeyboardButton("⏱ 𝟚𝟝𝕩", callback_data=f"autohunt_start_25_{final_region_key}"),
            InlineKeyboardButton("⏱ 𝟛𝟝𝕩", callback_data=f"autohunt_start_35_{final_region_key}"),
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
            keyboard.append([InlineKeyboardButton(f"⛏️ 𝐂𝐨𝐥𝐞𝐭𝐚𝐫 {item_name}", callback_data=f"collect_{res_id}")])

    keyboard.append([
        InlineKeyboardButton("🗺️ 𝐌𝐚𝐩𝐚", callback_data="travel"),
        InlineKeyboardButton("👤 𝐏𝐞𝐫𝐟𝐢𝐥", callback_data="profile")
    ])
    keyboard.append([
        InlineKeyboardButton("📜 𝐑𝐞𝐩𝐚𝐫𝐚𝐫", callback_data="restore_durability_menu"),
        InlineKeyboardButton("ℹ️ 𝐈𝐧𝐟𝐨", callback_data=f"region_info:{final_region_key}")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        fd = media_ids.get_file_data(f"regiao_{final_region_key}")
        if fd:
            await context.bot.send_photo(chat_id, fd["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
        else:
            await context.bot.send_message(chat_id, caption, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        await context.bot.send_message(chat_id, caption, reply_markup=reply_markup, parse_mode="HTML")


async def show_region_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, region_key: str | None = None, player_data: dict | None = None):
    q = getattr(update, "callback_query", None)
    uid = get_current_player_id(update, context)

    if q:
        await q.answer()
        try:
            await q.delete_message()
        except Exception:
            pass
        cid = q.message.chat_id
    else:
        cid = update.effective_chat.id

    if not uid:
        return

    await _auto_finalize_travel_if_due(context, uid)
    try:
        await player_manager.try_finalize_timed_action_for_user(uid)
    except Exception:
        pass

    await send_region_menu(context, uid, cid, region_key=region_key, player_data=player_data)


# =============================================================================
# Handlers de Guerra de Clãs (callbacks)
# =============================================================================

@requires_login
async def war_claim_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = get_current_player_id(update, context)
    pdata = await player_manager.get_player_data(uid) or {}
    if not pdata:
        await q.answer("Sessão inválida.", show_alert=True)
        return

    # BLOQUEIO HARD: só registrado e ACTIVE
    if not clan_war_engine:
        await q.answer("Guerra indisponível.", show_alert=True)
        return

    ok, reason = await clan_war_engine.can_player_participate_in_war(pdata)
    if not ok:
        await q.answer(reason or "⛔ Você não pode participar da guerra.", show_alert=True)
        return

    try:
        region_key = (q.data or "").split(":", 1)[1]
    except Exception:
        region_key = pdata.get("current_location", "reino_eldora")

    # Nesta etapa: apenas confirma.
    await q.answer("🛡️ Pedido de conquista enviado!", show_alert=True)

    try:
        await q.delete_message()
    except Exception:
        pass
    await send_region_menu(context, uid, q.message.chat_id, region_key=region_key, player_data=pdata)


@requires_login
async def war_attack_callback(update, context):
    q = update.callback_query
    await q.answer()

    uid = get_current_player_id(update, context)
    pdata = await player_manager.get_player_data(uid) or {}
    if not pdata:
        await q.answer("Sessão inválida.", show_alert=True)
        return

    # ✅ Gate da guerra (inscrito + ACTIVE)
    player_id_str = str(uid)
    ok, reason = await clan_war_engine.can_player_participate_in_war(pdata)
    if not ok:
        await q.answer(f"⛔ {reason}", show_alert=True)
        return

    # região alvo
    try:
        region_key = (q.data or "").split(":", 1)[1]
    except Exception:
        region_key = pdata.get("current_location", "reino_eldora")

    # encontra um inimigo elegível na mesma região
    enemy_id, enemy_data = await _find_enemy_for_region_war(uid, pdata, region_key)
    if not enemy_id or not enemy_data:
        await q.answer("😔 Nenhum inimigo registrado encontrado nesta região agora.", show_alert=True)
        return

    # ✅ SIMULA PvP (IMPORTANTE: sem ticket / sem arena ranking)
    winner_id, log = await pvp_battle.simular_batalha_completa(
        uid,
        enemy_id,
        modifier_effect=None,   # guerra não usa modificador da arena (a não ser que você queira)
        nivel_padrao=None
    )

    is_win = (str(winner_id) == str(uid))

    # ✅ Pontua GUERRA (não Arena)
    my_clan_id = (pdata or {}).get("clan_id")
    if my_clan_id:
        await clan_war_engine.register_battle(
            clan_id=str(my_clan_id),
            region_id=str(region_key),
            outcome=("win" if is_win else "loss"),
        )

    # Mensagem de resultado (com mídia do oponente, fallback)
    my_name = html.escape(pdata.get("character_name", "Você"))
    enemy_name = html.escape(enemy_data.get("character_name", "Inimigo"))

    try:
        summary = "\n".join(log[-10:])
    except Exception:
        summary = str(log)

    header = "🏆 <b>VITÓRIA TERRITORIAL!</b>" if is_win else "💀 <b>DERROTA TERRITORIAL...</b>"
    msg = (
        f"{header}\n\n"
        f"🗺️ <b>Região:</b> {html.escape(str(region_key))}\n"
        f"🆚 <b>{my_name}</b> vs <b>{enemy_name}</b>\n\n"
        f"📜 <b>Resumo:</b>\n{summary}"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Atacar Novamente", callback_data=f"war_attack:{region_key}")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data=f"open_region:{region_key}")],
    ])

    enemy_media = pvp_utils.get_player_class_media(enemy_data)

    try:
        if enemy_media:
            file_id = enemy_media.get("file_id") or enemy_media.get("id") or enemy_media.get("file")
            media_type = str(enemy_media.get("type", "video")).lower()
            caption = msg[:1024]

            if media_type == "photo":
                await context.bot.send_photo(
                    chat_id=q.message.chat_id,
                    photo=file_id,
                    caption=caption,
                    reply_markup=kb,
                    parse_mode="HTML",
                )
            else:
                await context.bot.send_video(
                    chat_id=q.message.chat_id,
                    video=file_id,
                    caption=caption,
                    reply_markup=kb,
                    parse_mode="HTML",
                )
        else:
            await context.bot.send_message(
                chat_id=q.message.chat_id,
                text=msg[:4096],
                reply_markup=kb,
                parse_mode="HTML",
            )
    except Exception:
        await context.bot.send_message(
            chat_id=q.message.chat_id,
            text=msg[:4096],
            reply_markup=kb,
            parse_mode="HTML",
        )

async def _find_enemy_for_region_war(my_id, my_data: dict, region_key: str):
    """
    Encontra um inimigo elegível para guerra territorial:
    - ambos registrados na guerra (registered_players do get_war_status)
    - fase ACTIVE
    - na mesma região (presence)
    - clã diferente
    - last_seen dentro do TTL
    """
    try:
        # 1) Preciso ter clã
        my_clan_id = (my_data or {}).get("clan_id")
        if not my_clan_id:
            return None, None

        # Normaliza meu_id para ObjectId
        if not isinstance(my_id, ObjectId):
            if ObjectId.is_valid(str(my_id)):
                my_oid = ObjectId(str(my_id))
            else:
                return None, None
        else:
            my_oid = my_id

        # 2) War status (fase + lista de registrados)
        ws = await clan_war_engine.get_war_status()
        state = (ws or {}).get("state", {}) or {}
        phase = str(state.get("phase", "idle")).lower()

        if phase != "active":
            return None, None

        registered_players = state.get("registered_players", {}) or {}
        if not isinstance(registered_players, dict):
            return None, None

        # Eu preciso estar registrado e o clã precisa bater
        my_reg_clan = registered_players.get(str(my_oid))
        if not my_reg_clan or str(my_reg_clan) != str(my_clan_id):
            return None, None

        # 3) Presence collection precisa existir
        if WAR_PRESENCE_COL is None:
            return None, None

        # 4) Atualiza minha presença AGORA (para eu ser encontrado também)
        now = datetime.now(timezone.utc)
        WAR_PRESENCE_COL.update_one(
            {"player_id": my_oid},
            {"$set": {
                "player_id": my_oid,
                "clan_id": str(my_clan_id),
                "region_key": str(region_key),
                "last_seen": now,
            }},
            upsert=True
        )

        # 5) Busca inimigos na mesma região, registrados e online no TTL
        ttl_seconds = 180
        cutoff = now - timedelta(seconds=ttl_seconds)

        # Pega candidatos na região dentro do TTL
        candidates = list(WAR_PRESENCE_COL.find({
            "region_key": str(region_key),
            "last_seen": {"$gte": cutoff},
            "player_id": {"$ne": my_oid},
            "clan_id": {"$ne": str(my_clan_id)},
        }).limit(30))

        if not candidates:
            return None, None

        # 6) Filtra por "registrado na guerra"
        # registered_players guarda player_id como string de ObjectId
        for c in candidates:
            enemy_oid = c.get("player_id")
            if not enemy_oid:
                continue

            enemy_pid_str = str(enemy_oid)

            # precisa estar registrado e o registro dele deve apontar para o clã dele
            enemy_reg_clan = registered_players.get(enemy_pid_str)
            if not enemy_reg_clan:
                continue

            # Confere consistência: clan_id do presence bate com registered_players
            if str(enemy_reg_clan) != str(c.get("clan_id")):
                continue

            # Carrega dados reais do inimigo
            enemy_data = await player_manager.get_player_data(enemy_oid)
            if not enemy_data:
                continue

            # Confere também o clan_id do inimigo no profile (evita “presence fraud”)
            if str(enemy_data.get("clan_id")) != str(enemy_reg_clan):
                continue

            return enemy_oid, enemy_data

        return None, None

    except Exception:
        return None, None



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
    if not pdata:
        return

    cur = pdata.get("current_location", "reino_eldora")

    # --- VERIFICAÇÃO VIP CONSISTENTE ---
    is_vip = False
    try:
        tier = str(pdata.get("premium_tier", "free")).lower().strip()
        if tier in ["lenda", "vip", "premium", "admin"]:
            is_vip = True
        else:
            pm = PremiumManager(pdata)
            if pm.is_premium():
                is_vip = True
    except Exception:
        pass

    is_neighbor = dest in WORLD_MAP.get(cur, []) or cur == dest
    if not is_vip and not is_neighbor:
        await q.answer("𝑴𝒖𝒊𝒕𝒐 𝒍𝒐𝒏𝒈𝒆 𝒑𝒂𝒓𝒂 𝒗𝒊𝒂𝒋𝒂𝒓 𝒂 𝒑𝒆́.", show_alert=True)
        return

    # Calcula custo de viagem
    cost = int(((game_data.REGIONS_DATA or {}).get(dest, {}) or {}).get("travel_cost", 0))
    current_energy = int(pdata.get("energy", 0))
    if cost > 0 and current_energy < cost:
        await q.answer(f"𝑬𝒏𝒆𝒓𝒈𝒊𝒂 𝒊𝒏𝒔𝒖𝒇𝒊𝒄𝒊𝒆𝒏𝒕𝒆. 𝑷𝒓𝒆𝒄𝒊𝒔𝒂 𝒅𝒆 {cost}⚡.", show_alert=True)
        return

    if cost > 0:
        player_manager.spend_energy(pdata, cost)

    secs = _get_travel_time_seconds(pdata, dest)

    if secs <= 0:
        pdata["current_location"] = dest
        pdata["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(uid, pdata)
        try:
            await q.delete_message()
        except Exception:
            pass
        await send_region_menu(context, uid, cid)
        return

    finish = datetime.now(timezone.utc) + timedelta(seconds=secs)
    pdata["player_state"] = {
        "action": "travel",
        "finish_time": finish.isoformat(),
        "details": {"destination": dest}
    }
    await player_manager.save_player_data(uid, pdata)

    try:
        await q.delete_message()
    except Exception:
        pass

    human = _humanize_duration(secs)
    dest_name = (game_data.REGIONS_DATA or {}).get(dest, {}).get("display_name", dest)
    txt = f"🧭 𝑽𝒊𝒂𝒋𝒂𝒏𝒅𝒐 𝒑𝒂𝒓𝒂 <b>>>>┈➤ {dest_name}</b>… (~{human})"

    await context.bot.send_message(chat_id=cid, text=txt, parse_mode="HTML")
    context.job_queue.run_once(
        finish_travel_job,
        when=secs,
        data={"player_id": str(uid), "dest": dest},
        chat_id=cid,
        name=f"finish_travel_{uid}"
    )


async def finish_travel_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    job_data = job.data or {}
    uid = job_data.get("player_id") or str(job.user_id)
    cid = job.chat_id
    dest = job_data.get("dest")

    pdata = await player_manager.get_player_data(uid)
    if pdata and pdata.get("player_state", {}).get("action") == "travel":
        pdata["current_location"] = dest
        pdata["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(uid, pdata)

    if context.user_data is not None:
        context.user_data['logged_player_id'] = str(uid)

    await send_region_menu(context, uid, cid)


@requires_login
async def collect_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    from handlers.job_handler import finish_collection_job

    if not q or not q.message:
        return

    uid = get_current_player_id(update, context)
    cid = q.message.chat_id

    # ==========================================================
    # ✅ Notificação robusta (alert + fallback no chat)
    # - NÃO damos ACK vazio no começo (isso "come" o show_alert em muitos clients)
    # ==========================================================
    async def _notify(text: str, alert: bool = True) -> None:
        try:
            await q.answer(text, show_alert=alert)
            return
        except Exception:
            pass
        # fallback garantido (usuário sempre vê algo)
        try:
            await context.bot.send_message(chat_id=cid, text=text, parse_mode="HTML")
        except Exception:
            pass

    res_id = (q.data or "").replace("collect_", "", 1).strip()
    if not res_id:
        await _notify("❌ Recurso inválido.", alert=True)
        return

    pdata = await player_manager.get_player_data(uid)
    if not pdata:
        await _notify("❌ Personagem não encontrado.", alert=True)
        return

    # ==========================================================
    # 🧷 Anti-dupe (melhorado)
    # - se estiver coletando e já venceu, tenta finalizar e não trava
    # ==========================================================
    state = pdata.get("player_state") or {}
    if state.get("action") == "collecting":
        finish_iso = state.get("finish_time")
        if finish_iso:
            try:
                finish_dt = datetime.fromisoformat(str(finish_iso).replace("Z", "+00:00"))
                if datetime.now(timezone.utc) >= finish_dt:
                    try:
                        await player_manager.try_finalize_timed_action_for_user(uid)
                    except Exception:
                        pass

                    pdata = await player_manager.get_player_data(uid) or pdata
                    state = pdata.get("player_state") or {}
                    if state.get("action") == "collecting":
                        await _notify("⏳ Você ainda está coletando.", alert=True)
                        return
                else:
                    await _notify("⏳ Você já está coletando algo.", alert=True)
                    return
            except Exception:
                # estado corrompido -> destrava pra não bricar
                pdata["player_state"] = {"action": "idle"}
                try:
                    await player_manager.save_player_data(uid, pdata)
                except Exception:
                    pass
        else:
            await _notify("⏳ Você já está coletando algo.", alert=True)
            return

    # ==========================================================
    # 🧨 Remove jobs antigos ANTES de criar novo
    # ==========================================================
    try:
        for j in context.job_queue.get_jobs_by_name(f"collect_{uid}"):
            j.schedule_removal()
    except Exception:
        pass

    equip = pdata.setdefault("equipment", {}) or {}
    inv = pdata.setdefault("inventory", {}) or {}

    tool_uid = equip.get("tool")
    if not tool_uid or tool_uid not in inv or not isinstance(inv.get(tool_uid), dict):
        await _notify("❌ Você precisa equipar uma ferramenta para coletar.", alert=True)
        return

    tool_inst = inv.get(tool_uid) or {}
    tool_base_id = tool_inst.get("base_id")
    if not tool_base_id:
        await _notify("❌ Ferramenta inválida (sem base_id).", alert=True)
        return

    tool_info = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(tool_base_id) or {}
    if tool_info.get("type") != "tool":
        await _notify("❌ O item equipado não é uma ferramenta válida.", alert=True)
        return

    tool_name = tool_info.get("display_name", tool_base_id.replace("_", " ").title())

    # Durabilidade
    try:
        cur_d, mx_d = _dur_tuple(tool_inst.get("durability"))
    except Exception:
        cur_d, mx_d = 0, 0

    if cur_d <= 0:
        await _notify("❌ Sua ferramenta está quebrada. Repare ou equipe outra.", alert=True)
        return

    # ==========================================================
    # 🧑‍🏭 Profissão (Mongo: profession.type)
    # ==========================================================
    prof = pdata.get("profession", {}) or {}
    user_prof_key = (prof.get("type") or prof.get("key") or "").strip().lower()

    # padroniza caso tenha vindo legado
    if user_prof_key and not prof.get("type"):
        prof["type"] = user_prof_key
        pdata["profession"] = prof

    # se ainda estiver vazio, evita key "collecting_"
    if not user_prof_key:
        user_prof_key = "generic"

    req_prof = game_data.get_profession_for_resource(res_id)
    if req_prof and user_prof_key != req_prof:
        await _notify("❌ Profissão incompatível.", alert=True)
        return

    tool_type = (tool_info.get("tool_type") or "").strip().lower()
    if req_prof and tool_type != req_prof:
        await _notify("❌ Ferramenta incompatível com este recurso.", alert=True)
        return

    # ==========================================================
    # ⚡ Energia + tempo por tier (centralizado)
    # ==========================================================
    from modules.player.premium import PremiumManager, get_collection_duration_seconds

    prem = PremiumManager(pdata)
    cost = int(prem.get_perk_value("gather_energy_cost", 1))

    if int(pdata.get("energy", 0)) < cost:
        await _notify(f"Sem energia ({cost}⚡).", alert=True)
        return

    player_manager.spend_energy(pdata, cost)
    dur = int(get_collection_duration_seconds(pdata))

    # item_yielded
    if req_prof:
        p_res = (game_data.PROFESSIONS_DATA.get(req_prof, {}) or {}).get("resources", {}) or {}
        item_yielded = p_res.get(res_id, res_id)
    else:
        item_yielded = res_id

    now = datetime.now(timezone.utc)
    finish = now + timedelta(seconds=dur)

    pdata["player_state"] = {
        "action": "collecting",
        "finish_time": finish.isoformat(),
        "details": {
            "resource_id": res_id,
            "item_id_yielded": item_yielded,
            "quantity": 1,
            "started_at": now.isoformat(),
            # ✅ persistência p/ pós-restart e p/ deletar "Coletando"
            "collect_chat_id": cid,
        },
    }
    player_manager.set_last_chat_id(pdata, cid)

    # ✅ ACK de sucesso (agora sim)
    try:
        await q.answer("⛏️ Coleta iniciada!", show_alert=False)
    except Exception:
        pass

    # Texto
    human = _humanize_duration(dur)
    item_info = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(item_yielded, {}) or {}
    item_name = item_info.get("display_name", item_yielded.replace("_", " ").title())
    item_emoji = item_info.get("emoji", "📦")

    cap = (
        f"╭┈┈┈┈┈➤➤⛏️ ℂ𝕠𝕝𝕖𝕥𝕒𝕟𝕕𝕠 ┈┈┈➤➤\n"
        f"│\n"
        f"├┈➤{item_emoji} <b>{item_name}</b>\n"
        f"├┈➤🛠️ {tool_name} ({cur_d}/{mx_d})\n"
        f"├┈➤⚡ Custo: {cost}\n"
        f"├┈➤⏳ Tempo: {human}\n"
        f"╰┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤➤"
    )

    try:
        await q.delete_message()
    except Exception:
        pass

    # ✅ Mídia por PROFISSÃO (collecting_{prof})
    media_key = f"collecting_{user_prof_key}"
    media = file_ids.get_file_data(media_key) or file_ids.get_file_data("collecting_generic") or {}
    media_id = media.get("id")
    media_type = (media.get("type") or "photo").strip().lower()

    sent = None
    try:
        if media_id and media_type == "video":
            sent = await context.bot.send_video(cid, media_id, caption=cap, parse_mode="HTML")
        elif media_id:
            sent = await context.bot.send_photo(cid, media_id, caption=cap, parse_mode="HTML")
        else:
            sent = await context.bot.send_message(cid, cap, parse_mode="HTML")
    except Exception:
        sent = await context.bot.send_message(cid, cap, parse_mode="HTML")

    # ✅ salva message_id para o job deletar depois + persistência no state
    if sent:
        pdata["player_state"]["details"]["collect_message_id"] = sent.message_id
        pdata["player_state"]["details"]["collect_chat_id"] = cid

    await player_manager.save_player_data(uid, pdata)

    context.job_queue.run_once(
        finish_collection_job,
        when=dur,
        data={
            "user_id": str(uid),
            "chat_id": cid,
            "resource_id": res_id,
            "item_id_yielded": item_yielded,
            "quantity": 1,
            "message_id": sent.message_id if sent else None,
        },
        name=f"collect_{uid}",
    )


# =============================================================================
# Durabilidade e Registro
# =============================================================================

@requires_login
async def show_restore_durability_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q or not q.message:
        return

    try:
        await q.answer()
    except Exception:
        pass

    uid = get_current_player_id(update, context)
    pdata = await player_manager.get_player_data(uid) or {}

    lines = ["<b>📜 Restaurar Durabilidade</b>\n"]
    lines.append("<i>Restaura TODOS os itens equipados consumindo apenas 1 Pergaminho.</i>\n")

    inv = pdata.get("inventory", {}) or {}
    equip = pdata.get("equipment", {}) or {}

    def _dur_from_base(inst: dict, fallback_max: int) -> int:
        base_id = (inst or {}).get("base_id")
        base = (game_data.ITEMS_DATA or {}).get(base_id, {}) or {}
        bd = base.get("durability")
        if isinstance(bd, (list, tuple)) and len(bd) >= 2:
            try:
                return int(bd[1])
            except Exception:
                return int(fallback_max or 0)
        return int(fallback_max or 0)

    def _d(inst: dict):
        """
        Retorna (cur, max) saneado.
        Aceita durability como:
          - [cur, max]
          - {"current": cur, "max": max}
          - None/invalid -> tenta pegar max do ITEMS_DATA
        """
        raw = (inst or {}).get("durability")
        cur, mx = 0, 0

        if isinstance(raw, (list, tuple)) and len(raw) >= 2:
            try:
                cur, mx = int(raw[0]), int(raw[1])
            except Exception:
                cur, mx = 0, 0
        elif isinstance(raw, dict):
            try:
                cur, mx = int(raw.get("current", 0)), int(raw.get("max", 0))
            except Exception:
                cur, mx = 0, 0

        # se max não veio, tenta puxar do item base
        mx = _dur_from_base(inst, mx)

        mx = max(0, mx)
        cur = max(0, min(cur, mx)) if mx > 0 else max(0, cur)

        return cur, mx

    items_broken_count = 0
    for slot, uid_item in (equip or {}).items():
        if not uid_item:
            continue

        inst = inv.get(uid_item)
        if not isinstance(inst, dict):
            continue

        cur, mx = _d(inst)
        if mx > 0 and cur < mx:
            items_broken_count += 1
            base_id = inst.get("base_id")
            nm = (game_data.ITEMS_DATA or {}).get(base_id, {}).get("display_name", "Item")
            lines.append(f"• {nm} <b>({cur}/{mx})</b>")

    kb = []
    if items_broken_count > 0:
        kb.append([InlineKeyboardButton("✨ REPARAR TUDO (Gasta 1x 📜)", callback_data="rd_fix_all")])
    else:
        lines.append("✅ <i>Todos os equipamentos estão perfeitos.</i>")

    loc = pdata.get("current_location", "reino_eldora")
    back = "continue_after_action" if loc == "reino_eldora" else f"open_region:{loc}"
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data=back)])

    await _safe_edit_or_send(
        q,
        context,
        q.message.chat_id,
        "\n".join(lines),
        InlineKeyboardMarkup(kb)
    )

@requires_login
async def noop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("✅", show_alert=False)

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

@requires_login
async def war_search_targets_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Mostra a lista de inimigos (Radar) na região atual.
    """
    query = update.callback_query
    # Avisa ao Telegram que o clique foi recebido
    await query.answer("🔭 Escaneando a área...")

    user_id = update.effective_user.id
    pdata = await player_manager.get_player_data(user_id)
    
    # --- CORREÇÃO AQUI ---
    # 1. Identifica onde o jogador está. Se falhar, joga para um local seguro (ex: floresta).
    current_region = pdata.get("current_location", "floresta_sombria")
    
    # Formatação visual do nome da região
    region_display_name = current_region.replace("_", " ").title()
    # ---------------------

    # 2. Busca alvos no Engine (filtrando pela região atual)
    targets = await clan_war_engine.get_war_targets_in_region(str(user_id), current_region)
    
    kb = []

    if not targets:
        text = (
            f"🔭 <b>RADAR DE GUERRA: {region_display_name}</b>\n\n"
            f"<i>Nenhum inimigo rival encontrado rondando por aqui no momento.</i>\n"
            "Tente novamente em instantes."
        )
        # Botão apenas para atualizar
        kb.append([InlineKeyboardButton("🔄 Buscar Novamente", callback_data="pvp_search_targets")])
    
    else:
        text = (
            f"🔭 <b>RADAR DE GUERRA: {region_display_name}</b>\n"
            f"<i>{len(targets)} inimigos detectados na área. Ataque para pontuar!</i>"
        )
        
        # 3. Lista os alvos encontrados
        for t in targets:
            # Botão de ataque: Espada + Nome + Nível
            # Callback leva o ID do alvo para o handler de luta
            btn_text = f"⚔️ {t['name']} (Nv.{t['lvl']})"
            kb.append([InlineKeyboardButton(btn_text, callback_data=f"pvp_fight_start:{t['user_id']}")])
        
        # Botão de atualizar lista
        kb.append([InlineKeyboardButton("🔄 Atualizar Radar", callback_data="pvp_search_targets")])
    
    # --- BOTÃO VOLTAR CORRIGIDO ---
    # Agora a variável 'current_region' existe e ele voltará para o mapa certo
    kb.append([InlineKeyboardButton("⬅️ Voltar para Região", callback_data=f"open_region:{current_region}")])
    
    # Renderiza o menu
    await query.edit_message_text(
        text=text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    
# =============================================================================
# REGISTRO DOS HANDLERS
# =============================================================================

region_handler = CallbackQueryHandler(region_callback, pattern=r"^region_[A-Za-z0-9_]+$")
travel_handler = CallbackQueryHandler(show_travel_menu, pattern=r"^travel$")
collect_handler = CallbackQueryHandler(collect_callback, pattern=r"^collect_[A-Za-z0-9_]+$")
open_region_handler = CallbackQueryHandler(open_region_callback, pattern=r"^open_region:")
restore_durability_menu_handler = CallbackQueryHandler(show_restore_durability_menu, pattern=r"^restore_durability_menu$")
restore_durability_fix_handler = CallbackQueryHandler(fix_item_durability, pattern=r"^rd_fix_all$")
region_info_handler = CallbackQueryHandler(region_info_callback, pattern=r"^region_info:.*$")

# ✅ Corrigido: handler que existia, mas não estava registrado
continue_after_action_handler = CallbackQueryHandler(continue_after_action, pattern=r"^continue_after_action$")

# ✅ Guerra de Clãs
war_claim_handler = CallbackQueryHandler(war_claim_callback, pattern=r"^war_claim:")
war_attack_handler = CallbackQueryHandler(war_attack_callback, pattern=r"^war_attack:")

# ✅ No-op (botões informativos)
noop_handler = CallbackQueryHandler(noop_callback, pattern=r"^noop$")

war_search_handler = CallbackQueryHandler(war_search_targets_callback, pattern=r"^pvp_search_targets$")
war_pvp_fight_handler = CallbackQueryHandler(war_pvp_fight_callback, pattern=r"^pvp_fight_start:")
