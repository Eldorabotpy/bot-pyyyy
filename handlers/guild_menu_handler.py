# handlers/guild_menu_handler.py
# (VERSÃO FINAL: Botão de CANCELAR adicionado ao Mural)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules import player_manager, guild_system, clan_manager, file_ids

async def _smart_media_edit(query, text, markup, media_key, context):
    """
    Tenta editar a mensagem existente para evitar 'piscar'.
    Só apaga e reenvia se for absolutamente necessário (ex: troca de Foto para Vídeo).
    """
    # 1. Pega o ID da mídia
    try: media_fid = file_ids.get_file_id(media_key)
    except: media_fid = None

    # Se não tiver mídia configurada, usa texto simples (fallback)
    if not media_fid:
        try: await query.edit_message_text(text=text, reply_markup=markup, parse_mode="HTML")
        except: 
            try: await query.delete_message()
            except: pass
            await context.bot.send_message(query.message.chat.id, text, reply_markup=markup, parse_mode="HTML")
        return

    # 2. Tenta EDITAR a Mídia (Transição Suave)
    # Assumimos que a guilda usa FOTO por padrão. Se usar GIF, troque para InputMediaAnimation
    try:
        await query.edit_message_media(
            media=InputMediaPhoto(media=media_fid, caption=text, parse_mode="HTML"),
            reply_markup=markup
        )
    except Exception:
        # Se falhar (ex: mensagem anterior era texto puro ou vídeo incompatível), deleta e envia novo
        try: await query.delete_message()
        except: pass
        await context.bot.send_photo(
            chat_id=query.message.chat.id,
            photo=media_fid,
            caption=text,
            reply_markup=markup,
            parse_mode="HTML"
        )

# --- HELPERS ---

def _bar(current, total, blocks=8):
    if total <= 0: return "🟩" * blocks
    ratio = min(1.0, max(0.0, current / total))
    filled = int(ratio * blocks)
    return "🟩" * filled + "⬜" * (blocks - filled)

async def _safe_edit(query, text, markup):
    try:
        await query.edit_message_text(text=text, reply_markup=markup, parse_mode="HTML")
    except Exception:
        try:
            await query.edit_message_caption(caption=text, reply_markup=markup, parse_mode="HTML")
        except Exception:
            try: await query.delete_message()
            except: pass
            await query.message.reply_text(text, reply_markup=markup, parse_mode="HTML")

# --- HANDLERS PRINCIPAIS ---

async def adventurer_guild_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except: pass
    
    user_id = query.from_user.id
    
    # --- Dados ---
    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return

    gdata = pdata.get("adventurer_guild", {})
    missions = guild_system.generate_daily_missions(pdata)
    await player_manager.save_player_data(user_id, pdata)

    rank_letra = gdata.get("rank", "F")
    points = gdata.get("points", 0)
    rank_info = guild_system.get_rank_info(rank_letra)
    next_pts = rank_info.get("req_points", 9999)
    prog_bar = _bar(points, next_pts) if next_pts > 0 else "🌟🌟🌟🌟🌟🌟🌟🌟"
    prog_text = f"{points}/{next_pts}" if next_pts > 0 else "MÁXIMO"

    text = (
        f"🏰 <b>GUILDA DE AVENTUREIROS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎫 <b>CARTEIRA DE MEMBRO</b>\n"
        f"👤 <b>Nome:</b> {pdata.get('character_name')}\n"
        f"🎖️ <b>Rank:</b> {rank_info.get('emoji', '🔰')} <b>{rank_letra}</b> - {rank_info.get('title', 'Aventureiro')}\n"
        f"💠 <b>Prestígio:</b> <code>[{prog_bar}]</code> ({prog_text})\n\n"
        f"📋 <b>QUADRO DE AVISOS DIÁRIO:</b>\n"
    )

    keyboard = []
    
    # Listagem de Missões
    for idx, m in enumerate(missions):
        if str(m.get('type', '')).upper() == 'COLLECT': continue
        status_icon = "✅" if m.get('status') in ['completed', 'claimed'] else "⬜"
        if m.get('status') == 'completed': status_icon = "🎁"
        name = m.get('title') or m.get('name') or "Missão"
        rewards = m.get('rewards', {})
        pts = rewards.get('prestige_points', m.get('reward_points', 0))
        prog = m.get('progress', 0)
        target = m.get('target_count', m.get('qty', 1))
        
        btn_txt = f"{status_icon} {name} ({prog}/{target}) [+ {pts} pts]"
        keyboard.append([InlineKeyboardButton(btn_txt, callback_data=f"gld_mission_view_{idx}")])

    if pdata.get("clan_id"):
        keyboard.append([InlineKeyboardButton("🛡️ Acessar Meu Clã", callback_data="clan_menu")])
    else:
        keyboard.append([InlineKeyboardButton("🛡️ Criar ou Buscar Clã", callback_data="guild_menu")])

    keyboard.append([InlineKeyboardButton("🔙 Voltar", callback_data="profile")])
    markup = InlineKeyboardMarkup(keyboard)

    # --- AQUI ESTÁ A MÁGICA ---
    # Usa a função inteligente com a imagem do NPC
    await _smart_media_edit(query, text, markup, "img_guild_npc", context)

async def view_mission_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe os detalhes de uma missão pessoal."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    try: idx = int(query.data.split("_")[-1])
    except: return

    pdata = await player_manager.get_player_data(user_id)
    missions = pdata.get("adventurer_guild", {}).get("active_missions", [])
    if idx >= len(missions): return
        
    m = missions[idx]

    if str(m.get('type', '')).upper() == 'COLLECT':
        await query.answer("Esta missão foi removida.", show_alert=True)
        await adventurer_guild_menu(update, context)
        return
    
    title = m.get('title') or m.get('name') or "Missão"
    desc = m.get('description') or m.get('desc') or "Sem descrição."
    status = m.get('status', 'active')
    
    rewards = m.get('rewards', {})
    xp = rewards.get('xp', m.get('xp', 0))
    gold = rewards.get('gold', m.get('reward_gold', 0))
    pts = rewards.get('prestige_points', m.get('reward_points', 0))
    
    prog = m.get('progress', 0)
    target = m.get('target_count', m.get('qty', 1))
    
    text = (
        f"📜 <b>{title}</b>\n"
        f"<i>{desc}</i>\n\n"
        f"📊 <b>Progresso:</b> {prog}/{target}\n"
        f"💰 <b>Recompensas:</b> {gold} Ouro, {xp} XP, {pts} Prestígio\n\n"
    )
    
    kb = []
    if status == 'completed':
        text += "\n✅ <b>Concluída!</b> Toque abaixo para receber."
        kb.append([InlineKeyboardButton("🎁 RESGATAR RECOMPENSA", callback_data=f"gld_mission_claim_{idx}")])
    elif status == 'claimed':
        text += "\n📦 <b>Recompensa já coletada.</b>"
    
    kb.append([InlineKeyboardButton("🔙 Voltar", callback_data="adventurer_guild_main")])
    
    await _safe_edit(query, text, InlineKeyboardMarkup(kb))

async def claim_mission_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resgata recompensa pessoal."""
    query = update.callback_query
    user_id = query.from_user.id
    
    try: idx = int(query.data.split("_")[-1])
    except: return

    from modules import mission_manager
    result = await mission_manager.claim_personal_reward(user_id, idx)
    
    if not result:
        await query.answer("Erro: Já coletada ou inválida.", show_alert=True)
        await adventurer_guild_menu(update, context)
        return
    
    await query.answer(f"🎉 Sucesso! +{result['gold']} Ouro, +{result['xp']} XP!", show_alert=True)
    
    if result.get("rank_up"):
        await context.bot.send_message(chat_id=query.message.chat.id, text=f"🎉 <b>PARABÉNS!</b>\nSubiu para Rank {result['rank_up']['title']}!", parse_mode="HTML")
    
    await adventurer_guild_menu(update, context)

# ==========================================================
# MENU DE MISSÕES DE CLÃ (CORRIGIDO COM CANCELAR)
# ==========================================================
async def clan_mission_board(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except: pass
    
    user_id = query.from_user.id
    pdata = await player_manager.get_player_data(user_id)
    
    if not pdata.get("clan_id"):
        await query.answer("Você precisa estar em um Clã!", show_alert=True)
        return

    try: clan_data = await clan_manager.get_clan(pdata["clan_id"])
    except: clan_data = {}

    if not clan_data:
        await query.answer("Clã não encontrado.", show_alert=True)
        return

    clan_lvl = clan_data.get('level', 1)
    clan_name = clan_data.get('name', 'Seu Clã')
    leader_id = int(clan_data.get('leader_id', 0))
    is_leader = (user_id == leader_id)
    active_m = clan_data.get('active_mission')
    
    text = (
        f"🛡️ <b>MISSÕES DE EXPANSÃO DO CLÃ</b>\n"
        f"Clã: <b>{clan_name}</b> | Nível: {clan_lvl}\n\n"
    )
    
    keyboard = []

    # Ignora coleta antiga visualmente, mas se o objeto existe, mostra opção de cancelar
    if active_m and str(active_m.get('type', '')).upper() == 'COLLECT':
        # Truque: não setamos active_m como None, mas avisamos
        text += "⚠️ <i>Missão antiga detectada. Líder deve cancelar.</i>\n\n"

    if active_m:
        title = active_m.get('title', 'Missão')
        prog = active_m.get('current_progress', 0)
        targ = active_m.get('target_count', 1)
        desc = active_m.get('description', '')
        
        target_raw = active_m.get('target_monster_id') or active_m.get('target_item_id') or "Alvo"
        target_pretty = str(target_raw).replace("_", " ").title()
        
        percent = (prog / targ) * 100 if targ > 0 else 0
        
        text += (
            f"⚔️ <b>MISSÃO ATIVA:</b>\n"
            f"📜 <b>{title}</b>\n"
            f"<i>\"{desc}\"</i>\n\n"
            f"🎯 <b>Objetivo:</b> Derrotar {targ}x <b>{target_pretty}</b>\n"
            f"📊 <b>Progresso:</b> {prog}/{targ} ({percent:.1f}%)\n"
            f"<code>[{_bar(prog, targ, 10)}]</code>\n"
        )
        
        if prog >= targ:
            text += "\n✅ <b>CONCLUÍDA! O líder deve finalizar.</b>"
            if is_leader:
                keyboard.append([InlineKeyboardButton("🏆 Finalizar Missão", callback_data="gld_mission_finish")])
        else:
            # [CORREÇÃO] Se não está completa e é Líder, mostra Cancelar
            if is_leader:
                 keyboard.append([InlineKeyboardButton("❌ Cancelar Missão (Líder)", callback_data="gld_mission_cancel")])

    else:
        text += "💤 <i>Nenhuma missão ativa no momento.</i>\n\n"
        if is_leader:
            text += "👑 <b>Você é o Líder!</b> Inicie uma missão para seu clã."
            keyboard.append([InlineKeyboardButton("📜 Iniciar Nova Missão", callback_data="gld_mission_select_menu")])
        else:
            text += "<i>Peça ao seu Líder para iniciar uma missão.</i>"
    
    keyboard.append([InlineKeyboardButton("🔙 Voltar à Guilda", callback_data="adventurer_guild_main")])
    
    await _safe_edit(query, text, InlineKeyboardMarkup(keyboard))

# Exports
adventurer_guild_handler = CallbackQueryHandler(adventurer_guild_menu, pattern=r'^adventurer_guild_main$')
clan_board_handler = CallbackQueryHandler(clan_mission_board, pattern=r'^gld_clan_board$')
mission_view_handler = CallbackQueryHandler(view_mission_details, pattern=r'^gld_mission_view_')
mission_claim_handler = CallbackQueryHandler(claim_mission_reward, pattern=r'^gld_mission_claim_')