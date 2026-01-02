# handlers/converter_handler.py
# (VERSÃO FINAL: SEGURA - IDS BLINDADOS)

import logging
import math
from typing import List, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, game_data, file_ids
from modules.game_data.skins import SKIN_CATALOG
from modules.game_data import skills as skills_data
from modules.auth_utils import get_current_player_id
# Tenta importar as listas de itens permitidos para venda
try:
    from handlers.gem_market_handler import SKILL_BOOK_ITEMS, SKIN_BOX_ITEMS
except ImportError:
    SKILL_BOOK_ITEMS = set()
    SKIN_BOX_ITEMS = set()

logger = logging.getLogger(__name__)

# --- Funções Auxiliares ---

def _get_item_info(base_id: str) -> dict:
    """Pega os dados de um item da game_data de forma segura."""
    try:
        # Tenta o novo método se existir
        if hasattr(game_data, "get_item_info"):
            info = game_data.get_item_info(base_id)
            if info: return dict(info)
            
        # Fallback para o dicionário direto
        return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}
    except Exception:
        return {}

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None):
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        try:
            await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="HTML")
        except Exception:
            try: await query.delete_message()
            except: pass
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="HTML")

def _get_skill_name(skill_id):
    return skills_data.SKILL_DATA.get(skill_id, {}).get("display_name", skill_id)

def _get_skin_name(skin_id):
    return SKIN_CATALOG.get(skin_id, {}).get("display_name", skin_id)

# --- Menu Principal do Conversor ---

async def converter_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # 🔒 BLINDAGEM: Verifica sessão, embora não precise de dados neste menu
    user_id = get_current_player_id(update, context)
    if not user_id:
        await _safe_edit_or_send(query, context, query.message.chat_id, "Sessão inválida. Use /start.", None)
        return
    
    text = (
        "🔄 <b>Conversor de Recompensas</b>\n\n"
        "Converta Skills ou Skins aprendidas de volta em <b>Itens</b> (Tomos/Caixas) para vender ou trocar.\n\n"
        "⚠️ <b>Aviso:</b> Você perderá o acesso à skill/skin até usar o item novamente."
    )
    keyboard = [
        [InlineKeyboardButton("📚 Converter Skills", callback_data="conv:list:skill:1")],
        [InlineKeyboardButton("🎨 Converter Skins", callback_data="conv:list:skin:1")],
        [InlineKeyboardButton("⬅️ Voltar ao Perfil", callback_data="profile")],
    ]
    await _safe_edit_or_send(query, context, query.message.chat_id, text, InlineKeyboardMarkup(keyboard))

# --- Listagem de Itens Conversíveis ---

async def converter_list_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # 🔒 BLINDAGEM: ID seguro
    user_id = get_current_player_id(update, context)
    
    if not user_id:
        await _safe_edit_or_send(query, context, query.message.chat_id, "Sessão inválida.", None)
        return
    
    try:
        parts = query.data.split(":")
        item_type = parts[2]
        page = int(parts[3])
    except:
        await converter_main_menu(update, context)
        return

    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return

    convertible_items = []
    
    if item_type == "skill":
        title = "📚 Converter Skills"
        learned_skills = pdata.get("skills", [])
        # Suporte a lista ou dict (novo formato)
        if isinstance(learned_skills, dict):
            learned_skills = list(learned_skills.keys())
            
        for skill_id in learned_skills:
            if isinstance(skill_id, str) and skill_id in skills_data.SKILL_DATA:
                convertible_items.append((skill_id, _get_skill_name(skill_id)))
            
    else: # skin
        title = "🎨 Converter Skins"
        unlocked_skins = pdata.get("unlocked_skins", [])
        for skin_id in unlocked_skins:
            if isinstance(skin_id, str) and skin_id in SKIN_CATALOG:
                convertible_items.append((skin_id, _get_skin_name(skin_id)))

    convertible_items.sort(key=lambda x: x[1])

    # Paginação
    per_page = 5
    start = (page - 1) * per_page
    end = start + per_page
    items_page = convertible_items[start:end]
    total_pages = max(1, math.ceil(len(convertible_items) / per_page))
    
    text = f"{title} (Pág. {page}/{total_pages})\n\nEscolha para converter em item:"
    rows = []

    if not items_page:
        text += "\n\n<i>Nenhum item conversível encontrado.</i>"
    
    for iid, name in items_page:
        rows.append([InlineKeyboardButton(f"🔄 {name}", callback_data=f"conv:confirm:{item_type}:{iid}")])
        
    nav = []
    if page > 1: nav.append(InlineKeyboardButton("⬅️", callback_data=f"conv:list:{item_type}:{page - 1}"))
    nav.append(InlineKeyboardButton("🔙 Voltar", callback_data="conv:main"))
    if page < total_pages: nav.append(InlineKeyboardButton("➡️", callback_data=f"conv:list:{item_type}:{page + 1}"))
    rows.append(nav)
    
    await _safe_edit_or_send(query, context, query.message.chat_id, text, InlineKeyboardMarkup(rows))

# --- Confirmação e Execução ---

async def converter_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # 🔒 BLINDAGEM: Verifica sessão
    user_id = get_current_player_id(update, context)
    if not user_id:
        return
    
    try:
        parts = query.data.split(":")
        item_type = parts[2]
        item_id = parts[3]
    except: return
        
    if item_type == "skill":
        name = _get_skill_name(item_id)
        item_name = f"Tomo: {name}"
    else:
        name = _get_skin_name(item_id)
        item_name = f"Caixa: {name}"
        
    text = (
        f"⚠️ <b>Confirmar Conversão</b>\n\n"
        f"Você vai esquecer: <b>{name}</b>\n"
        f"E receberá: <b>{item_name}</b>\n\n"
        f"Deseja continuar?"
    )
        
    kb = [
        [InlineKeyboardButton("✅ Sim, Converter", callback_data=f"conv:exec:{item_type}:{item_id}")],
        [InlineKeyboardButton("❌ Cancelar", callback_data=f"conv:list:{item_type}:1")]
    ]
    await _safe_edit_or_send(query, context, query.message.chat_id, text, InlineKeyboardMarkup(kb))

async def converter_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # 🔒 BLINDAGEM: ID Seguro
    user_id = get_current_player_id(update, context)
    
    if not user_id:
        await query.answer("Sessão inválida.", show_alert=True)
        return
    
    try:
        parts = query.data.split(":")
        item_type = parts[2]
        item_id = parts[3]
    except: return

    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return
        
    removed = False
    item_give_id = ""

    if item_type == "skill":
        item_give_id = f"tomo_{item_id}"
        skills = pdata.get("skills", {})
        
        # Suporte a lista ou dict
        if isinstance(skills, list) and item_id in skills:
            skills.remove(item_id)
            removed = True
        elif isinstance(skills, dict) and item_id in skills:
            del skills[item_id]
            removed = True
            
        # Remove dos equipados
        equipped = pdata.get("equipped_skills", [])
        if item_id in equipped:
            equipped.remove(item_id)
            
    else: # skin
        item_give_id = f"caixa_{item_id}"
        skins = pdata.get("unlocked_skins", [])
        if item_id in skins:
            skins.remove(item_id)
            removed = True
            
        if pdata.get("equipped_skin") == item_id:
            pdata["equipped_skin"] = None

    if not removed:
        await query.answer("Erro: Você não possui mais isso.", show_alert=True)
        await converter_main_menu(update, context)
        return

    # Entrega o item
    player_manager.add_item_to_inventory(pdata, item_give_id, 1)
    await player_manager.save_player_data(user_id, pdata)

    text = "✅ <b>Sucesso!</b> Item adicionado ao seu inventário."
    kb = [[InlineKeyboardButton("⬅️ Voltar", callback_data="conv:main")]]
    await _safe_edit_or_send(query, context, query.message.chat_id, text, InlineKeyboardMarkup(kb))

# ==============================
#  Handlers
# ==============================
converter_main_handler = CallbackQueryHandler(converter_main_menu, pattern=r'^conv:main$')
converter_list_handler = CallbackQueryHandler(converter_list_items, pattern=r'^conv:list:')
converter_confirm_handler = CallbackQueryHandler(converter_confirm, pattern=r'^conv:confirm:')
converter_execute_handler = CallbackQueryHandler(converter_execute, pattern=r'^conv:exec:')