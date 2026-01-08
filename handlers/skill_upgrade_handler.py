# handlers/skill_upgrade_handler.py
# (NOVO ARQUIVO: Gerencia o Menu de Skills e Upgrades fora de combate)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager
from modules import class_evolution_service
# Importamos a função de cálculo de custo para exibir no botão antes de clicar
from modules.class_evolution_service import _get_skill_upgrade_cost 
from modules.game_data.skills import get_skill_data_with_rarity
# Tenta importar helper de nome de item, com fallback caso falhe
try:
    from modules.game_data.items import get_display_name
except ImportError:
    def get_display_name(iid): return iid.replace("_", " ").title()

logger = logging.getLogger(__name__)

async def menu_skills_main_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Lista todas as habilidades aprendidas pelo jogador para visualização/upgrade.
    """
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    pdata = await player_manager.get_player_data(user_id)
    
    if not pdata:
        return

    skills_dict = pdata.get("skills", {})
    if not skills_dict:
        # Se não tiver skills, avisa e dá botão de voltar
        await query.edit_message_caption(
            caption="⚠️ **Você ainda não aprendeu nenhuma habilidade.**\n"
                    "Avance de nível ou evolua sua classe para aprender.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="start_menu")]]),
            parse_mode="Markdown"
        )
        return

    # Monta os botões
    keyboard = []
    row = []
    
    # Ordena skills por nome para ficar organizado
    sorted_skills = sorted(skills_dict.keys())

    for skill_id in sorted_skills:
        skill_entry = skills_dict[skill_id]
        
        # Pega dados visuais (Nome, Raridade)
        full_data = get_skill_data_with_rarity(pdata, skill_id)
        if not full_data: continue

        name = full_data.get("display_name", skill_id.replace("_", " ").title())
        level = skill_entry.get("level", 1)
        rarity = skill_entry.get("rarity", "comum")
        
        # Emoji de raridade para enfeitar
        rarity_emoji = {
            "comum": "⚪", "incomum": "🟢", "rara": "🔵", 
            "epica": "🟣", "lendaria": "🟠"
        }.get(rarity.lower(), "⚪")

        btn_text = f"{rarity_emoji} {name} (Lv.{level})"
        
        # Callback leva para o menu de detalhe daquela skill
        row.append(InlineKeyboardButton(btn_text, callback_data=f"skill_detail:{skill_id}"))
        
        if len(row) == 1: # 1 skill por linha para caber o nome
            keyboard.append(row)
            row = []
            
    if row: keyboard.append(row)
    
    # Botão de Voltar (ajustado para voltar ao menu de ascensão se veio de lá, ou região)
    # Por padrão, mandamos para o menu de evolução se for o fluxo comum
    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data="open_evolution_menu")])

    text = (
        "📚 **GRIMOIRE DE HABILIDADES**\n\n"
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
        # Fallback se a mensagem original não tiver caption (ex: era texto puro)
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )


async def skill_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Mostra detalhes da skill e o botão de Upar com o preço calculado.
    """
    query = update.callback_query
    await query.answer()
    
    try:
        _, skill_id = query.data.split(":", 1)
    except ValueError:
        return

    user_id = query.from_user.id
    pdata = await player_manager.get_player_data(user_id)
    
    if not pdata or "skills" not in pdata or skill_id not in pdata["skills"]:
        await query.edit_message_caption("⚠️ Habilidade não encontrada.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Voltar", callback_data="menu_skills_main")]]))
        return

    skill_entry = pdata["skills"][skill_id]
    current_level = skill_entry.get("level", 1)
    rarity = skill_entry.get("rarity", "comum")
    
    # Busca dados completos (Dano, CD, Descrição)
    full_data = get_skill_data_with_rarity(pdata, skill_id)
    
    name = full_data.get("display_name", skill_id)
    desc = full_data.get("description", "Sem descrição.")
    mana = full_data.get("mana_cost", 0)
    cooldown = full_data.get("effects", {}).get("cooldown_turns", 0)
    skill_type = full_data.get("type", "active").title()

    # --- CÁLCULO DO PREÇO (Usando a função do service) ---
    costs = _get_skill_upgrade_cost(current_level, rarity, skill_id)
    cost_gold = costs["gold"]
    cost_items = costs["items"] # Ex: {'tomo_skill_x': 1}
    
    # Formata texto do item necessário
    item_req_text = ""
    for iid, qty in cost_items.items():
        iname = get_display_name(iid)
        item_req_text += f"\n- {qty}x {iname}"

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

    # Botão de Upar
    btn_upgrade = InlineKeyboardButton(
        f"⬆️ Upar ({cost_gold}g)", 
        callback_data=f"skill_upgrade_do:{skill_id}"
    )
    
    btn_back = InlineKeyboardButton("⬅️ Voltar", callback_data="menu_skills_main")
    
    # Se nível for máximo (ex: 10), remove botão de upar
    keyboard = []
    if current_level < 10:
        keyboard.append([btn_upgrade])
    else:
        text += "\n\n🌟 **NÍVEL MÁXIMO ALCANÇADO!**"
        
    keyboard.append([btn_back])

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


async def skill_upgrade_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Executa a transação de upgrade chamando o Service.
    """
    query = update.callback_query
    
    try:
        _, skill_id = query.data.split(":", 1)
    except ValueError:
        return

    user_id = query.from_user.id
    
    # CHAMA O SERVICE QUE CRIAMOS ANTES
    # Ele verifica itens, ouro, consome e salva.
    success, message, new_data = await class_evolution_service.process_skill_upgrade(user_id, skill_id)

    if success:
        await query.answer("🎉 Sucesso!", show_alert=False)
        # Atualiza a tela com os dados do novo nível
        await skill_detail_callback(update, context)
        
        # Opcional: Mandar msg de confirmação
        # await context.bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")
    else:
        await query.answer(f"❌ {message}", show_alert=True)