# handlers/evolution_handler.py
from __future__ import annotations
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from modules.player_manager import get_player_data
from modules.game_data.classes import CLASSES_DATA 
from modules.game_data.class_evolution import get_evolution_options
# --- IMPORT NOVO ---
from modules.auth_utils import get_current_player_id 

async def open_class_evolution_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Abre o menu de Evolução de Classe com suporte a Login Híbrido."""
    q = update.callback_query
    await q.answer()

    # --- ALTERAÇÃO AQUI ---
    user_id = get_current_player_id(update, context)
    # ----------------------

    pdata = await get_player_data(user_id) or {}

    # Dados do jogador
    pclass = (pdata.get("class") or "guerreiro").lower()
    plevel = int(pdata.get("level") or 1)

    # Info da classe ATUAL
    cinfo = CLASSES_DATA.get(pclass, {})
    cname = f"{cinfo.get('emoji','')} {cinfo.get('display_name', pclass.title())}"

    # Busca próxima evolução
    evo_options = get_evolution_options(pclass, plevel, show_locked=True)
    
    if evo_options:
        next_evo = evo_options[0]
        raw_to = next_evo.get("to", "???")
        pretty_name = next_evo.get("display_name", raw_to.replace("_", " ").title())
        min_lvl = next_evo.get("min_level", 0)
        desc = next_evo.get("desc", "Sem descrição.")
        
        next_evo_text = (
            f"🔮 <b>Próxima Evolução:</b> {pretty_name}\n"
            f"📝 <i>{desc}</i>\n"
            f"📏 Requisito: Nível {min_lvl}"
        )
        
        if plevel >= min_lvl:
            action_btn = [InlineKeyboardButton("✅ Iniciar Ascensão", callback_data=f"evo_start_{raw_to}")]
        else:
            action_btn = [InlineKeyboardButton(f"🔒 Requer Nível {min_lvl}", callback_data="noop")]
            
    else:
        next_evo_text = "<i>Você atingiu o ápice da sua classe atual ou não há evoluções disponíveis.</i>"
        action_btn = []

    text = (
        f"🧬 <b>ARVORE DE EVOLUÇÃO</b>\n\n"
        f"👤 <b>Atual:</b> {cname}\n"
        f"📊 <b>Nível:</b> {plevel}\n"
        f"──────────────────\n"
        f"{next_evo_text}\n"
    )

    kb = []
    if action_btn: kb.append(action_btn)
    kb.append([InlineKeyboardButton("🔄 Atualizar", callback_data="char_evolution")])
    kb.append([InlineKeyboardButton("⬅️ Voltar ao Personagem", callback_data="status_open")])

    try:
        await q.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
    except Exception:
        await q.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

evolution_open_handler = CallbackQueryHandler(open_class_evolution_menu, pattern=r"^char_evolution$")