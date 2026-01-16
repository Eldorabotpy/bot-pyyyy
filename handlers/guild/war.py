# handlers/guild/war.py
# (VERSÃO CORRIGIDA: Menu Visual da Guerra de Clãs + ranking por região)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules import clan_war_engine, game_data

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

    # ✅ Compat: engine pode não ter o modo; fallback PVE
    try:
        mode = clan_war_engine.get_current_war_mode()
    except Exception:
        mode = "PVE"

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
        reg_info = (getattr(game_data, "REGIONS_DATA", None) or {}).get(reg_key, {})
        name = reg_info.get("display_name", reg_key.replace("_", " ").title())

        row.append(InlineKeyboardButton(name, callback_data=f"war_view:{reg_key}"))

        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🔙 Voltar ao Clã", callback_data="clan_menu")])

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def show_region_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o Top 10 Clãs daquela região."""
    query = update.callback_query
    await query.answer()

    try:
        region_key = query.data.split(":")[1]
    except Exception:
        await query.answer("Região inválida.", show_alert=True)
        return

    reg_info = (getattr(game_data, "REGIONS_DATA", None) or {}).get(region_key, {})
    reg_name = reg_info.get("display_name", region_key.replace("_", " ").title())

    # ✅ Compat: se engine não tiver, retorna vazio
    try:
        leaderboard = await clan_war_engine.get_region_leaderboard(region_key)
    except Exception:
        leaderboard = []

    text = f"🚩 <b>Domínio: {reg_name}</b>\n\n"

    if not leaderboard:
        text += "<i>Nenhum clã conquistou pontos aqui ainda. Seja o primeiro!</i>"
    else:
        medals = ["🥇", "🥈", "🥉"]
        for idx, entry in enumerate(leaderboard[:10]):
            icon = medals[idx] if idx < 3 else f"{idx+1}."
            c_name = entry.get("clan_name", "Clã")
            pts = entry.get("points", 0)
            text += f"{icon} <b>{c_name}</b>: {pts} pts\n"

    text += "\n<i>Pontue derrotando inimigos nesta região!</i>"

    keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data="clan_war_menu")]]

    # Edição segura (texto vs caption)
    try:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    except Exception:
        try:
            await query.edit_message_caption(caption=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


# --- HANDLERS PARA EXPORTAR ---
# ✅ Mantém: 'clan_war_menu' abre este menu visual (ranking por região)
war_menu_handler = CallbackQueryHandler(show_war_menu, pattern=r"^clan_war_menu$")
war_ranking_handler = CallbackQueryHandler(show_region_ranking, pattern=r"^war_view:")
