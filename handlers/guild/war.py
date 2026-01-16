# handlers/guild/war.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules import clan_war_engine, game_data

WAR_REGIONS = [
    "floresta_sombria",
    "pedreira_granito",
    "mina_ferro",
    "pantano_maldito",
    "pico_grifo"
]

async def _safe_edit(query, text: str, reply_markup: InlineKeyboardMarkup):
    """
    Edita TEXT se a mensagem for texto puro.
    Edita CAPTION se a mensagem tiver mídia (foto/video/animação).
    """
    try:
        has_media = bool(query.message.photo or query.message.video or query.message.animation)
    except Exception:
        has_media = False

    if has_media:
        try:
            await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="HTML")
            return
        except Exception:
            pass

    # fallback: tenta editar texto normal
    try:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        # fallback final
        try:
            await query.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")
        except Exception:
            pass


async def show_war_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

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

    keyboard.append([InlineKeyboardButton("🔙 Voltar", callback_data="gld_menu")])

    await _safe_edit(query, text, InlineKeyboardMarkup(keyboard))


async def show_region_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        region_key = query.data.split(":")[1]
    except Exception:
        await query.answer("Região inválida.", show_alert=True)
        return

    reg_info = (getattr(game_data, "REGIONS_DATA", None) or {}).get(region_key, {})
    reg_name = reg_info.get("display_name", region_key.replace("_", " ").title())

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

    keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data="war_menu")]]
    await _safe_edit(query, text, InlineKeyboardMarkup(keyboard))


# ✅ NÃO usar mais clan_war_menu aqui (para não colidir com menu do clã)
war_menu_handler = CallbackQueryHandler(show_war_menu, pattern=r"^war_menu$")
war_ranking_handler = CallbackQueryHandler(show_region_ranking, pattern=r"^war_view:")
