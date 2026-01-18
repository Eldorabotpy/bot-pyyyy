# handlers/guild_menu_handler.py
# (VERSÃO ATUALIZADA: UI RENDERER + GUILDAS)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from datetime import datetime, timedelta, timezone

from modules import player_manager, guild_system, clan_manager, file_ids
from modules.auth_utils import get_current_player_id
from modules.clan_war_engine import get_war_status

# --- IMPORT VISUAL ---
from ui.ui_renderer import render_photo_or_text

# ==============================================================================
# HELPERS
# ==============================================================================

def _bar(current, total, blocks=8):
    if total <= 0: return "🟩" * blocks
    ratio = min(1.0, max(0.0, current / total))
    filled = int(ratio * blocks)
    return "🟩" * filled + "⬜" * (blocks - filled)

def _mini_bar(current, total):
    blocks = 5
    if total <= 0: return "▪️" * blocks
    ratio = min(1.0, max(0.0, current / total))
    filled = int(ratio * blocks)
    return "▪️" * filled + "▫️" * (blocks - filled)

def _get_time_until_reset():
    now = datetime.now(timezone.utc)
    next_reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    diff = next_reset - now
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours}h {minutes}m"

async def _render_guild_screen(update, context, text, keyboard, media_key=None, scope="adventurer_guild"):
    """Wrapper para renderizar telas da guilda de aventureiros."""
    media_fid = None
    if media_key:
        try:
            media_fid = file_ids.get_file_id(media_key)
        except: pass
    
    # Fallback visual
    if not media_fid:
        try:
            media_fid = file_ids.get_file_id("img_guild_npc")
        except: pass

    await render_photo_or_text(
        update,
        context,
        text=text,
        photo_file_id=media_fid,
        reply_markup=InlineKeyboardMarkup(keyboard),
        scope=scope,
        parse_mode="HTML",
        allow_edit=True
    )

# ==============================================================================
# HANDLERS PRINCIPAIS
# ==============================================================================

async def adventurer_guild_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()

    user_id = get_current_player_id(update, context)
    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return

    # Atualiza missões diárias
    gdata = pdata.get("adventurer_guild", {})
    missions = guild_system.generate_daily_missions(pdata)
    await player_manager.save_player_data(user_id, pdata)

    rank_letra = gdata.get("rank", "F")
    points = gdata.get("points", 0)
    rank_info = guild_system.get_rank_info(rank_letra)
    next_pts = rank_info.get("req_points", 9999)
    prog_bar = _bar(points, next_pts) if next_pts > 0 else "🌟🌟🌟🌟🌟🌟🌟🌟"
    prog_text = f"{points}/{next_pts}" if next_pts > 0 else "MÁXIMO"
    timer_str = _get_time_until_reset()

    text = (
        f"🏰 <b>GUILDA DE AVENTUREIROS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎫 <b>CARTEIRA DE MEMBRO</b>\n"
        f"👤 <b>Nome:</b> {pdata.get('character_name')}\n"
        f"🎖️ <b>Rank:</b> {rank_info.get('emoji', '🔰')} <b>{rank_letra}</b> - {rank_info.get('title', 'Aventureiro')}\n"
        f"💠 <b>Prestígio:</b> <code>[{prog_bar}]</code> ({prog_text})\n\n"
        f"📋 <b>QUADRO DE AVISOS DIÁRIO</b>\n"
        f"🕒 <i>Novos contratos em: {timer_str}</i>"
    )

    keyboard = []
    for idx, m in enumerate(missions):
        if str(m.get("type", "")).upper() == "COLLECT":
            continue

        status = m.get("status", "active")
        name = m.get("title") or m.get("name") or "Missão"
        prog = m.get("progress", 0)
        target = m.get("target_count", m.get("qty", 1))

        if status == "claimed":
            btn_txt = f"✅ {name} (Concluído)"
        elif status == "completed":
            btn_txt = f"🎁 {name} (RECEBER)"
        else:
            mini_b = _mini_bar(prog, target)
            btn_txt = f"▫️ {name} [{mini_b}] {prog}/{target}"

        keyboard.append([InlineKeyboardButton(btn_txt, callback_data=f"gld_mission_view_{idx}")])

    if pdata.get("clan_id"):
        keyboard.append([InlineKeyboardButton("🛡️ Acessar Meu Clã", callback_data="clan_menu")])
        keyboard.append([InlineKeyboardButton("⚔️ Guerra de Clãs (Evento)", callback_data="gld_war_status")])
    else:
        keyboard.append([InlineKeyboardButton("🛡️ Criar ou Buscar Clã", callback_data="clan_create_menu_start")])

    keyboard.append([InlineKeyboardButton("🔙 Voltar", callback_data="profile")])
    
    # Renderiza
    await _render_guild_screen(update, context, text, keyboard, media_key="img_guild_npc")


async def guild_war_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra status resumido da Guerra (atalho no menu pessoal)."""
    query = update.callback_query
    if query: await query.answer()

    user_id = get_current_player_id(update, context)
    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return

    ws = await get_war_status()
    season = ws.get("season", {}) or {}

    war_id = season.get("season_id") or season.get("campaign_id") or "-"
    phase = str(season.get("phase") or "PREP").upper()
    signup_open = bool(season.get("signup_open", season.get("registration_open", False)))
    target_region_id = str(season.get("target_region_id") or "")

    region_name = target_region_id or "—"
    region_emoji = "📍"
    try:
        from modules.game_data import regions as game_data_regions
        from modules.guild_war.region import get_region_meta
        meta = get_region_meta(game_data_regions, target_region_id) if target_region_id else {}
        region_name = meta.get("display_name", region_name)
        region_emoji = meta.get("emoji", region_emoji)
    except: pass

    txt = (
        f"⚔️ <b>GUERRA DE CLÃS (Evento Global)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 <b>Rodada:</b> <code>{war_id}</code>\n"
        f"⏳ <b>Fase Atual:</b> <b>{phase}</b>\n"
        f"📝 <b>Inscrições:</b> {'🟢 ABERTA' if signup_open else '🔴 FECHADA'}\n"
        f"{region_emoji} <b>Região Alvo:</b> <b>{region_name}</b>\n\n"
    )

    if phase == "PREP" or phase == "PREPARAÇÃO":
        txt += (
            "✅ <b>Modo PREPARAÇÃO</b>\n"
            "Os líderes de clã devem inscrever suas guildas agora.\n"
            "Se você tem clã, verifique o painel dele para entrar na lista de batalha.\n"
        )
    elif phase == "ACTIVE":
        txt += (
            "🔥 <b>GUERRA ATIVA!</b>\n"
            "O combate começou! Apenas membros inscritos pontuam.\n"
            "Vá para a região alvo e derrote inimigos para ajudar seu clã.\n"
        )
    else:
        txt += "🏁 <b>Rodada Encerrada.</b> Aguardando próxima temporada.\n"

    kb = []
    if pdata.get("clan_id"):
        kb.append([InlineKeyboardButton("🛡️ Painel do Meu Clã", callback_data="clan_menu")])
    else:
        kb.append([InlineKeyboardButton("🛡️ Buscar Clã", callback_data="clan_create_menu_start")])

    kb.append([InlineKeyboardButton("🔙 Voltar", callback_data="adventurer_guild_main")])
    
    await _render_guild_screen(update, context, txt, kb, media_key="img_war_default")


async def view_mission_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = get_current_player_id(update, context)
    try:
        idx = int(query.data.split("_")[-1])
    except: return

    pdata = await player_manager.get_player_data(user_id)
    missions = pdata.get("adventurer_guild", {}).get("active_missions", [])
    if idx >= len(missions): return

    m = missions[idx]

    if str(m.get("type", "")).upper() == "COLLECT":
        await query.answer("Missão antiga removida.", show_alert=True)
        await adventurer_guild_menu(update, context)
        return

    title = m.get("title") or m.get("name") or "Missão"
    desc = m.get("description") or m.get("desc") or "Sem descrição."
    status = m.get("status", "active")
    rewards = m.get("rewards", {})
    
    xp = rewards.get("xp", m.get("xp", 0))
    gold = rewards.get("gold", m.get("reward_gold", 0))
    pts = rewards.get("prestige_points", m.get("reward_points", 0))
    
    prog = m.get("progress", 0)
    target = m.get("target_count", m.get("qty", 1))

    text = (
        f"📜 <b>DETALHES DO CONTRATO</b>\n\n"
        f"📌 <b>{title}</b>\n"
        f"<i>\"{desc}\"</i>\n\n"
        f"📊 <b>Progresso:</b> {prog}/{target}\n"
        f"💰 <b>Recompensas:</b>\n"
        f"   • {gold} Ouro\n"
        f"   • {xp} XP\n"
        f"   • {pts} pts de Prestígio\n\n"
    )

    kb = []
    if status == "completed":
        text += "✅ <b>Concluída!</b> Resgate sua recompensa abaixo."
        kb.append([InlineKeyboardButton("🎁 RESGATAR AGORA", callback_data=f"gld_mission_claim_{idx}")])
    elif status == "claimed":
        text += "📦 <b>Recompensa já coletada.</b>"

    kb.append([InlineKeyboardButton("🔙 Voltar", callback_data="adventurer_guild_main")])
    
    await _render_guild_screen(update, context, text, kb, media_key="img_mission_scroll")


async def claim_mission_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = get_current_player_id(update, context)
    try:
        idx = int(query.data.split("_")[-1])
    except: return

    from modules import mission_manager
    result = await mission_manager.claim_personal_reward(user_id, idx)
    
    if not result:
        await query.answer("Erro ao coletar ou já coletada.", show_alert=True)
    else:
        msg = f"🎉 +{result['gold']} Ouro"
        if result.get("xp"): msg += f", +{result['xp']} XP"
        if result.get("rank_up"):
            msg += f"\n🏆 NOVO RANK: {result['rank_up']['title']}!"
        await query.answer(msg, show_alert=True)

    await adventurer_guild_menu(update, context)


async def clan_mission_board(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Visualização alternativa do quadro de missões do clã via menu da Guilda de Aventureiros.
    Redireciona para o handler oficial do clã para consistência.
    """
    query = update.callback_query
    await query.answer()
    
    # Importação tardia para evitar ciclo
    from handlers.guild.missions import show_guild_mission_details
    await show_guild_mission_details(update, context)

# --- CONFIGURAÇÃO ---
adventurer_guild_handler = CallbackQueryHandler(adventurer_guild_menu, pattern=r"^adventurer_guild_main$")
clan_board_handler = CallbackQueryHandler(clan_mission_board, pattern=r"^gld_clan_board$")
war_status_handler = CallbackQueryHandler(guild_war_status, pattern=r"^gld_war_status$")
mission_view_handler = CallbackQueryHandler(view_mission_details, pattern=r"^gld_mission_view_")
mission_claim_handler = CallbackQueryHandler(claim_mission_reward, pattern=r"^gld_mission_claim_")