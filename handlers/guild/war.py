# handlers/guild/war.py
# (VERSÃO FINAL: Menu Visual da Guerra de Clãs)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules import clan_war_engine, game_data, player_manager

# Lista de regiões disputáveis (certifique-se que estas chaves existem no seu game_data)
WAR_REGIONS = [
    "floresta_sombria", 
    "pedreira_granito", 
    "mina_ferro", 
    "pantano_maldito", 
    "pico_grifo"
]

async def show_war_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o menu principal da guerra com o modo do dia."""
    query = update.callback_query
    await query.answer()
    
    # Verifica o modo atual (PvE ou PvP)
    mode = clan_war_engine.get_current_war_mode()
    
    if mode == "PVP":
        header = "🔥 <b>HOJE: GUERRA DE SANGUE (PvP)</b> 🔥\n<i>Ataque jogadores de clãs rivais para pontuar!</i>"
    else:
        header = "🌲 <b>HOJE: DOMINAÇÃO (PvE)</b> 🌲\n<i>Cace monstros nas regiões para pontuar!</i>"

    text = (
        f"{header}\n\n"
        f"<b>Territórios em Disputa:</b>\n"
        f"<i>Escolha uma região para ver o ranking:</i>"
    )
    
    keyboard = []
    row = []
    for reg_key in WAR_REGIONS:
        # Tenta pegar o nome bonito da região
        reg_info = (game_data.REGIONS_DATA or {}).get(reg_key, {})
        name = reg_info.get("display_name", reg_key.replace("_", " ").title())
        
        # Botão para ver ranking daquela região
        row.append(InlineKeyboardButton(name, callback_data=f"war_view:{reg_key}"))
        
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row: keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 Voltar ao Clã", callback_data="clan_menu")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def show_region_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o Top 10 Clãs daquela região."""
    query = update.callback_query
    await query.answer()
    
    try:
        region_key = query.data.split(":")[1]
    except:
        await query.answer("Região inválida.")
        return

    reg_info = (game_data.REGIONS_DATA or {}).get(region_key, {})
    reg_name = reg_info.get("display_name", region_key.replace("_", " ").title())
    
    # Busca os dados do banco
    leaderboard = await clan_war_engine.get_region_leaderboard(region_key)
    
    text = f"🚩 <b>Domínio: {reg_name}</b>\n\n"
    
    if not leaderboard:
        text += "<i>Nenhum clã conquistou pontos aqui ainda. Seja o primeiro!</i>"
    else:
        medals = ["🥇", "🥈", "🥉"]
        for idx, entry in enumerate(leaderboard):
            # Formatação: 🥇 Nome do Clã: 1500 pts
            icon = medals[idx] if idx < 3 else f"{idx+1}."
            c_name = entry['clan_name']
            pts = entry['points']
            text += f"{icon} <b>{c_name}</b>: {pts} pts\n"
            
    text += "\n<i>Pontue derrotando inimigos nesta região!</i>"
    
    keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data="clan_war_menu")]]
    
    # Edição segura (evita erro se não tiver mudado nada ou se era foto)
    try: 
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    except: 
        try:
            await query.edit_message_caption(caption=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        except:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# --- HANDLERS PARA EXPORTAR ---
war_menu_handler = CallbackQueryHandler(show_war_menu, pattern="^clan_war_menu$")
war_ranking_handler = CallbackQueryHandler(show_region_ranking, pattern="^war_view:")