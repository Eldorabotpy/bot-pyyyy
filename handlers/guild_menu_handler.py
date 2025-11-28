# handlers/guild_menu_handler.py
# (VERSÃO FINAL CORRIGIDA: ERRO DE CHAVE 'PTS' RESOLVIDO)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules import player_manager, guild_system, clan_manager, file_ids

# Helper de Barra
def _bar(current, total, blocks=8):
    if total <= 0: return "🟩" * blocks
    ratio = min(1.0, max(0.0, current / total))
    filled = int(ratio * blocks)
    return "🟩" * filled + "⬜" * (blocks - filled)

async def adventurer_guild_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu Principal da Instituição (NPC)."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return

    # Dados
    gdata = pdata.get("adventurer_guild", {})
    rank_letra = gdata.get("rank", "F")
    points = gdata.get("points", 0)
    rank_info = guild_system.get_rank_info(rank_letra)
    
    # Gera Missões (se necessário)
    missions = guild_system.generate_daily_missions(pdata)
    await player_manager.save_player_data(user_id, pdata)

    # Barra de Progresso do Rank
    next_rank_pts = rank_info["req_points"]
    if next_rank_pts > 0:
        prog_bar = _bar(points, next_rank_pts)
        prog_text = f"{points}/{next_rank_pts}"
    else:
        prog_bar = "🌟🌟🌟🌟🌟🌟🌟🌟"
        prog_text = "MÁXIMO"

    text = (
        f"🏰 <b>GUILDA DE AVENTUREIROS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎫 <b>CARTEIRA DE MEMBRO</b>\n"
        f"👤 <b>Nome:</b> {pdata.get('character_name')}\n"
        f"🎖️ <b>Rank:</b> {rank_info['emoji']} <b>{rank_letra}</b> - {rank_info['title']}\n"
        f"💠 <b>Prestígio:</b> <code>[{prog_bar}]</code> ({prog_text})\n\n"
        f"📋 <b>QUADRO DE AVISOS DIÁRIO:</b>\n"
    )

    keyboard = []
    
    # Lista Missões Pessoais
    for m in missions:
        status = "✅" if m.get('status') == 'completed' else "⬜"
        
        # --- CORREÇÃO AQUI ---
        # Tenta pegar 'reward_points', se não tiver tenta 'pts', se não tiver usa 0
        pts_val = m.get('reward_points', m.get('pts', 0))
        
        btn_txt = f"{status} {m['name']} (+{pts_val} pts)"
        keyboard.append([InlineKeyboardButton(btn_txt, callback_data="noop")])

    # Botão para acessar o Clã
    if pdata.get("clan_id"):
        keyboard.append([InlineKeyboardButton("🛡️ Acessar Meu Clã", callback_data="clan_menu")])
    else:
        keyboard.append([InlineKeyboardButton("🛡️ Criar ou Buscar Clã", callback_data="guild_menu")])

    keyboard.append([InlineKeyboardButton("🔙 Voltar", callback_data="profile")])

    # Envio com imagem (opcional)
    media_id = file_ids.get_file_id("img_guild_npc") 
    
    if media_id:
        try:
            if query.message.photo:
                 await query.edit_message_media(
                    media=InputMediaPhoto(media_id, caption=text, parse_mode="HTML"),
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.delete_message()
                await context.bot.send_photo(
                    chat_id=query.message.chat.id, 
                    photo=media_id, 
                    caption=text, 
                    reply_markup=InlineKeyboardMarkup(keyboard), 
                    parse_mode="HTML"
                )
            return
        except:
            pass
    
    # Texto puro (Fallback)
    try:
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    except:
        await context.bot.send_message(chat_id=query.message.chat.id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def clan_mission_board(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Quadro de Missões Globais do Clã.
    """
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    
    if not clan_id:
        await query.answer("Você precisa estar em um Clã!", show_alert=True)
        return

    # Busca dados do clã
    try:
        clan_data = await clan_manager.get_clan(clan_id)
    except:
        clan_data = {}

    if not clan_data:
        await query.answer("Erro ao carregar dados do Clã.", show_alert=True)
        return

    clan_lvl = clan_data.get('level', 1) if isinstance(clan_data.get('level'), int) else 1
    clan_name = clan_data.get('name', 'Seu Clã')

    text = (
        f"🛡️ <b>MISSÕES DE EXPANSÃO DO CLÃ</b>\n"
        f"Clã: <b>{clan_name}</b> | Nível: {clan_lvl}\n\n"
        f"Complete estas tarefas em grupo para ganhar XP de Clã e aumentar o limite de membros!\n"
    )
    
    # Exemplo de missões estáticas
    keyboard = [
        [InlineKeyboardButton("💀 Raid: Rei Goblin (500 XP)", callback_data="noop")],
        [InlineKeyboardButton("💰 Doação: 5.000 Ouro (100 XP)", callback_data="noop")],
        [InlineKeyboardButton("🔙 Voltar à Guilda", callback_data="adventurer_guild_main")]
    ]
    
    try:
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    except:
        await context.bot.send_message(chat_id=query.message.chat.id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# --- EXPORTAÇÃO DOS HANDLERS ---

adventurer_guild_handler = CallbackQueryHandler(adventurer_guild_menu, pattern=r'^adventurer_guild_main$')
clan_board_handler = CallbackQueryHandler(clan_mission_board, pattern=r'^gld_clan_board$')