# handlers/skill_upgrade_handler.py
# (Gerencia o Menu de Skills e Upgrades fora de combate — ObjectId SAFE)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager
from modules import class_evolution_service
from modules.class_evolution_service import _get_skill_upgrade_cost
from modules.game_data.skills import get_skill_data_with_rarity
from modules.auth_utils import get_current_player_id_async

# Tenta importar helper de nome de item, com fallback
try:
    from modules.game_data.items import get_display_name
except ImportError:
    def get_display_name(iid): return iid.replace("_", " ").title()

logger = logging.getLogger(__name__)


# =============================================================================
# MENU PRINCIPAL DE SKILLS
# =============================================================================
async def menu_skills_main_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    player_id = await get_current_player_id_async(update, context)
    if not player_id:
        return

    pdata = await player_manager.get_player_data(player_id)
    if not pdata:
        return

    skills_dict = pdata.get("skills", {})
    if not skills_dict:
        await query.edit_message_caption(
            caption="⚠️ **Você ainda não aprendeu nenhuma habilidade.**\n"
                    "Avance de nível ou evolua sua classe para aprender.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="start_menu")]]),
            parse_mode="Markdown"
        )
        return

    keyboard = []
    row = []

    for skill_id in sorted(skills_dict.keys()):
        skill_entry = skills_dict[skill_id]
        full_data = get_skill_data_with_rarity(pdata, skill_id)
        if not full_data:
            continue

        name = full_data.get("display_name", skill_id.replace("_", " ").title())
        level = skill_entry.get("level", 1)
        rarity = skill_entry.get("rarity", "comum")

        rarity_emoji = {
            "comum": "⚪", "incomum": "🟢", "rara": "🔵",
            "epica": "🟣", "lendaria": "🟠"
        }.get(rarity.lower(), "⚪")

        btn_text = f"{rarity_emoji} {name} (Lv.{level})"
        row.append(InlineKeyboardButton(btn_text, callback_data=f"skill_detail:{skill_id}"))

        if len(row) == 1:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data="open_evolution_menu")])

    text = (
        "📚 **GRIMÓRIO DE HABILIDADES**\n\n"
        "Selecione uma habilidade para ver detalhes e realizar **Upgrades**.\n"
        "Para evoluir, você precisará de Ouro e Tomos da habilidade."
    )

    try:
        await query.edit_message_caption(
            caption=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except Exception:
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )


# =============================================================================
# DETALHE DA SKILL
# =============================================================================
async def skill_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        _, skill_id = query.data.split(":", 1)
    except ValueError:
        return

    player_id = await get_current_player_id_async(update, context)
    if not player_id:
        return

    pdata = await player_manager.get_player_data(player_id)
    if not pdata or skill_id not in pdata.get("skills", {}):
        await query.edit_message_caption(
            "⚠️ Habilidade não encontrada.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="menu_skills_main")]])
        )
        return

    skill_entry = pdata["skills"][skill_id]
    current_level = skill_entry.get("level", 1)
    rarity = skill_entry.get("rarity", "comum")

    full_data = get_skill_data_with_rarity(pdata, skill_id)
    name = full_data.get("display_name", skill_id)
    desc = full_data.get("description", "Sem descrição.")
    mana = full_data.get("mana_cost", 0)
    cooldown = full_data.get("effects", {}).get("cooldown_turns", 0)
    skill_type = full_data.get("type", "active").title()

    costs = _get_skill_upgrade_cost(current_level, rarity, skill_id)
    cost_gold = costs["gold"]
    cost_items = costs["items"]

    item_req_text = ""
    for iid, qty in cost_items.items():
        item_req_text += f"\n- {qty}x {get_display_name(iid)}"

    text = (
        f"📖 **{name}** (Nível {current_level})\n"
        f"_{rarity.title()} | {skill_type}_\n\n"
        f"📝 {desc}\n\n"
        f"💧 **Mana:** {mana} | ⏳ **Recarga:** {cooldown}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⬆️ **PRÓXIMO NÍVEL:**\n"
        f"💰 Custo: {cost_gold} Ouro"
        f"{item_req_text}"
    )

    keyboard = []
    if current_level < 10:
        keyboard.append([
            InlineKeyboardButton(f"⬆️ Upar ({cost_gold}g)", callback_data=f"skill_upgrade_do:{skill_id}")
        ])
    else:
        text += "\n\n🌟 **NÍVEL MÁXIMO ALCANÇADO!**"

    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data="menu_skills_main")])

    try:
        await query.edit_message_caption(
            caption=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except Exception:
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )


# =============================================================================
# EXECUÇÃO DO UPGRADE
# =============================================================================
async def skill_upgrade_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        _, skill_id = query.data.split(":", 1)
    except ValueError:
        return

    player_id = await get_current_player_id_async(update, context)
    if not player_id:
        return

    success, message, _ = await class_evolution_service.process_skill_upgrade(player_id, skill_id)

    if success:
        await query.answer("🎉 Sucesso!", show_alert=False)
        await skill_detail_callback(update, context)
    else:
        await query.answer(f"❌ {message}", show_alert=True)
