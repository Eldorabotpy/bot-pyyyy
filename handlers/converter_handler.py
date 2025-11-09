# handlers/converter_handler.py
# (VERSÃO CORRIGIDA - COM IMPORTS)

import logging  # <-- (NOVO) 1. Importa o 'logging'
import math     # <-- (NOVO) 2. Importa o 'math'
from typing import List, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, game_data
from modules.game_data.skins import SKIN_CATALOG
from modules.game_data import skills as skills_data

try:
    from handlers.gem_market_handler import SKILL_BOOK_ITEMS, SKIN_BOX_ITEMS
except ImportError:
    # (logging ainda não está definido, vamos usar print)
    print("AVISO: Falha ao importar listas de itens do gem_market_handler. O Conversor não funcionará.")
    SKILL_BOOK_ITEMS = set()
    SKIN_BOX_ITEMS = set()

logger = logging.getLogger(__name__) # <-- Esta linha agora funciona

# --- Funções Auxiliares ---

# (NOVO) 3. Função _get_item_info (estava em falta)
def _get_item_info(base_id: str) -> dict:
    """Pega os dados de um item da game_data."""
    try:
        info = game_data.get_item_info(base_id)
        if info:
            return dict(info)
    except Exception:
        pass
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None):
    """Função segura para editar ou enviar mensagem."""
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        try:
            await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="HTML")
        except Exception:
            try:
                await query.delete_message()
            except Exception:
                pass
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="HTML")

def _get_skill_name(skill_id):
    """Pega o nome de exibição de uma skill."""
    return skills_data.SKILL_DATA.get(skill_id, {}).get("display_name", skill_id)

def _get_skin_name(skin_id):
    """Pega o nome de exibição de uma skin."""
    return SKIN_CATALOG.get(skin_id, {}).get("display_name", skin_id)

# --- Menu Principal do Conversor ---

async def converter_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o menu principal do conversor (Skills ou Skins)."""
    query = update.callback_query
    await query.answer()
    
    text = (
        "🔄 <b>Conversor de Recompensas</b>\n\n"
        "Este utilitário permite-te converter Skills ou Skins que já *aprendeste* "
        "de volta em **Itens Consumíveis** (Tomos/Caixas).\n\n"
        "Isto permite que vendas as tuas recompensas na 🏛️ Casa de Leilões.\n\n"
        "<b>Atenção:</b> Converter uma recompensa fará com que a 'esqueças'. "
        "Terás de usar o item para a aprenderes de novo."
    )
    keyboard = [
        [InlineKeyboardButton("📚 Converter Skills", callback_data="conv:list:skill:1")],
        [InlineKeyboardButton("🎨 Converter Skins", callback_data="conv:list:skin:1")],
        [InlineKeyboardButton("⬅️ Voltar ao Perfil", callback_data="profile")],
    ]
    await _safe_edit_or_send(query, context, query.message.chat_id, text, InlineKeyboardMarkup(keyboard))

# --- Listagem de Itens Conversíveis ---

async def converter_list_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a lista paginada de Skills ou Skins que o jogador pode converter."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    try:
        # Ex: "conv:list:skill:1"
        parts = query.data.split(":")
        item_type = parts[2] # 'skill' or 'skin'
        page = int(parts[3])
    except (IndexError, ValueError):
        await query.answer("Erro de callback.", show_alert=True); return

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        await query.answer("Erro: Personagem não encontrado.", show_alert=True); return

    convertible_items = []
    
    if item_type == "skill":
        title = "📚 Converter Skills"
        learned_skills = pdata.get("skills", [])
        for skill_id in learned_skills:
            item_id = f"tomo_{skill_id}"
            # Verifica se este item de skill é um dos que podem ser vendidos (da nossa lista)
            if item_id in SKILL_BOOK_ITEMS:
                convertible_items.append((skill_id, _get_skill_name(skill_id)))
                
    else: # item_type == "skin"
        title = "🎨 Converter Skins"
        unlocked_skins = pdata.get("unlocked_skins", [])
        for skin_id in unlocked_skins:
            item_id = f"caixa_{skin_id}"
            # Verifica se este item de skin é um dos que podem ser vendidos
            if item_id in SKIN_BOX_ITEMS:
                convertible_items.append((skin_id, _get_skin_name(skin_id)))

    convertible_items.sort(key=lambda x: x[1]) # Ordena por nome

    # Paginação
    ITEMS_PER_PAGE = 5
    start_index = (page - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    items_on_page = convertible_items[start_index:end_index]
    total_pages = max(1, math.ceil(len(convertible_items) / ITEMS_PER_PAGE))
    page = min(page, total_pages)
    
    text = f"{title} (Pág. {page}/{total_pages})\n\nSelecione a recompensa que deseja 'engarrafar':"
    keyboard_rows = []

    if not items_on_page and page == 1:
        text += "\n\n<i>Você não possui recompensas (Skills/Skins) aprendidas que possam ser convertidas em itens.</i>"
    
    for item_id, item_name in items_on_page:
        # O callback de confirmação precisa saber o tipo E o ID
        callback_data = f"conv:confirm:{item_type}:{item_id}"
        keyboard_rows.append([InlineKeyboardButton(f"🔄 {item_name}", callback_data=callback_data)])
        
    # Navegação
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"conv:list:{item_type}:{page - 1}"))
    
    nav_buttons.append(InlineKeyboardButton("⬅️ Voltar", callback_data="conv:main"))
    
    if end_index < len(convertible_items):
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"conv:list:{item_type}:{page + 1}"))
        
    keyboard_rows.append(nav_buttons)
    await _safe_edit_or_send(query, context, query.message.chat_id, text, InlineKeyboardMarkup(keyboard_rows))

# --- Confirmação e Execução ---

async def converter_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pede ao jogador a confirmação final para 'esquecer' a recompensa."""
    query = update.callback_query
    await query.answer()
    
    try:
        # Ex: "conv:confirm:skill:active_whirlwind"
        parts = query.data.split(":")
        item_type = parts[2]
        item_id = parts[3] # ID da skill/skin (ex: "active_whirlwind")
    except (IndexError, ValueError):
        await query.answer("Erro de callback.", show_alert=True); return
        
    if item_type == "skill":
        item_name = _get_skill_name(item_id)
        item_consumable_id = f"tomo_{item_id}"
        item_consumable_name = _get_item_info(item_consumable_id).get("display_name", f"Tomo: {item_name}")
        text = (
            f"⚠️ <b>Confirmar Conversão</b> ⚠️\n\n"
            f"Tens a certeza que queres 'esquecer' a skill:\n<b>{item_name}</b>?\n\n"
            f"Ela será removida da tua lista de skills (e desequipada) e vais receber o item "
            f"<b>{item_consumable_name}</b> no teu inventário."
        )
    else: # skin
        item_name = _get_skin_name(item_id)
        item_consumable_id = f"caixa_{item_id}"
        item_consumable_name = _get_item_info(item_consumable_id).get("display_name", f"Caixa: {item_name}")
        text = (
            f"⚠️ <b>Confirmar Conversão</b> ⚠️\n\n"
            f"Tens a certeza que queres 'guardar' a aparência:\n<b>{item_name}</b>?\n\n"
            f"Ela será removida da tua lista de skins (e desequipada) e vais receber o item "
            f"<b>{item_consumable_name}</b> no teu inventário."
        )
        
    keyboard = [
        [InlineKeyboardButton(f"✅ Sim, converter", callback_data=f"conv:exec:{item_type}:{item_id}")],
        [InlineKeyboardButton(f"❌ Não, voltar", callback_data=f"conv:list:{item_type}:1")]
    ]
    await _safe_edit_or_send(query, context, query.message.chat_id, text, InlineKeyboardMarkup(keyboard))

async def converter_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Executa a conversão: Remove a skill/skin e adiciona o item."""
    query = update.callback_query
    await query.answer("A converter...")
    user_id = query.from_user.id
    
    try:
        parts = query.data.split(":")
        item_type = parts[2]
        item_id = parts[3] # ID da skill/skin (ex: "active_whirlwind")
    except (IndexError, ValueError):
        await query.answer("Erro de callback.", show_alert=True); return

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        await query.answer("Erro: Personagem não encontrado.", show_alert=True); return
        
    item_foi_removido = False
    item_consumable_id = ""
    item_consumable_name = ""

    if item_type == "skill":
        item_consumable_id = f"tomo_{item_id}"
        item_consumable_name = _get_item_info(item_consumable_id).get("display_name", f"Tomo: {_get_skill_name(item_id)}")
        
        # Remove da lista de skills aprendidas
        if item_id in pdata.get("skills", []):
            pdata["skills"].remove(item_id)
            item_foi_removido = True
        
        # Remove da lista de skills equipadas
        if item_id in pdata.get("equipped_skills", []):
            pdata["equipped_skills"].remove(item_id)
            
    else: # skin
        item_consumable_id = f"caixa_{item_id}"
        item_consumable_name = _get_item_info(item_consumable_id).get("display_name", f"Caixa: {_get_skin_name(item_id)}")
        
        # Remove da lista de skins desbloqueadas
        if item_id in pdata.get("unlocked_skins", []):
            pdata["unlocked_skins"].remove(item_id)
            item_foi_removido = True
            
        # Desequipa a skin se estiver em uso
        if pdata.get("equipped_skin") == item_id:
            pdata["equipped_skin"] = None

    if not item_foi_removido:
        await query.answer(f"Erro: Já não tinhas essa recompensa.", show_alert=True)
        await converter_main_menu(update, context)
        return

    # Adiciona o item ao inventário
    player_manager.add_item_to_inventory(pdata, item_consumable_id, 1)
    await player_manager.save_player_data(user_id, pdata)

    text = f"✅ Conversão Concluída!\n\nRecebeste 1x <b>{item_consumable_name}</b> no teu inventário."
    keyboard = [
        [InlineKeyboardButton("⬅️ Voltar ao Conversor", callback_data="conv:main")]
    ]
    await _safe_edit_or_send(query, context, query.message.chat_id, text, InlineKeyboardMarkup(keyboard))

# ==============================
#  Handlers (Exports)
# ==============================

converter_main_handler = CallbackQueryHandler(converter_main_menu, pattern=r'^conv:main$')
converter_list_handler = CallbackQueryHandler(converter_list_items, pattern=r'^conv:list:(skill|skin):(\d+)$')
converter_confirm_handler = CallbackQueryHandler(converter_confirm, pattern=r'^conv:confirm:(skill|skin):')
converter_execute_handler = CallbackQueryHandler(converter_execute, pattern=r'^conv:exec:(skill|skin):')