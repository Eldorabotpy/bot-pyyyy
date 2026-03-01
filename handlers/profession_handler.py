# handlers/profession_handler.py
# (VERSÃO FINAL: Importação correta de game_data.items + Fix de Lista de Receitas)

import math
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, game_data, crafting_registry
from modules.game_data.refining import REFINING_RECIPES
from modules.auth_utils import get_current_player_id

# ✅ 1. IMPORTAÇÃO CORRETA DAS PROFISSÕES
try:
    from modules.game_data.professions import PROFESSIONS_DATA
except ImportError:
    PROFESSIONS_DATA = {}

# ✅ 2. IMPORTAÇÃO CORRETA DOS ITENS (Sem modules.items)
# O arquivo correto é modules/game_data/items.py
try:
    from modules.game_data.items import ITEMS_DATA
except ImportError:
    ITEMS_DATA = {} 

logger = logging.getLogger(__name__)

RECIPES_PER_PAGE = 6

# ==================================================================
# HELPERS
# ==================================================================
def _get_prof_display_name(key):
    return PROFESSIONS_DATA.get(key, {}).get('display_name', key.capitalize())

async def _safe_edit(query, text, reply_markup):
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='HTML')
    except:
        await query.message.reply_text(text=text, reply_markup=reply_markup, parse_mode='HTML')

# ==================================================================
# 1. MENU PRINCIPAL
# ==================================================================
async def job_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = get_current_player_id(update, context)
    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return

    prof_data = player_data.get("profession") or {}
    current_prof_key = prof_data.get("type") or prof_data.get("key")

    # --- CENÁRIO A: JOGADOR JÁ TEM PROFISSÃO ---
    if current_prof_key and current_prof_key in PROFESSIONS_DATA:
        prof_info = PROFESSIONS_DATA[current_prof_key]
        prof_name = prof_info.get('display_name', current_prof_key.capitalize())
        prof_cat = prof_info.get('category', 'crafting') # gathering ou crafting
        
        lvl = prof_data.get("level", 1)
        xp = prof_data.get("xp", 0)
        
        text = (
            f"🛠 <b>PROFISSÃO: {prof_name.upper()}</b>\n"
            f"Nível: {lvl} | XP: {xp}\n"
        )
        
        kb = []
        
        # --- MENU PARA COLETORES (Gathering) ---
        if prof_cat == 'gathering':
            text += f"\n🌲 <i>Sua função é explorar o mundo e extrair recursos naturais.</i>\n\n"
            text += "💡 <b>Como upar?</b>\nViaje para regiões que tenham recursos e use a opção <b>⛏️ Coletar</b>."
            
            resources = prof_info.get('resources', {})
            if resources:
                text += "\n\n<b>Seus Alvos:</b>\n"
                for res_key, _ in resources.items():
                    r_name = ITEMS_DATA.get(res_key, {}).get('display_name', res_key)
                    text += f"• {r_name}\n"

            kb.append([InlineKeyboardButton("🗺️ Abrir Mapa", callback_data="travel")])

        # --- MENU PARA ARTESÃOS (Crafting) ---
        else:
            text += f"<i>Você transforma materiais brutos em equipamentos poderosos.</i>"
            kb.append([InlineKeyboardButton(f"⚒️ Refinar / Processar", callback_data=f"job_list_refine_1")])
            kb.append([InlineKeyboardButton(f"📜 Criar Itens ({prof_name})", callback_data=f"job_list_craft_1")])
        
        kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="show_kingdom_menu")])
        
        await _safe_edit(query, text, InlineKeyboardMarkup(kb))
        return

    # --- CENÁRIO B: JOGADOR SEM PROFISSÃO ---
    text = (
        "🔨 <b>GUILDA DOS ARTESÃOS</b>\n\n"
        "Você precisa se especializar em um ofício.\n"
        "⚠️ <b>Atenção:</b> Escolha com sabedoria, pois você só poderá exercer UMA profissão!\n\n"
        "Escolha seu caminho:"
    )
    
    kb = []
    row = []
    for key, info in PROFESSIONS_DATA.items():
        name = info.get('display_name', key.title())
        cat_emoji = "🌲" if info.get('category') == 'gathering' else "⚒️"
        
        row.append(InlineKeyboardButton(f"{cat_emoji} {name}", callback_data=f"job_pick_{key}"))
        if len(row) == 2:
            kb.append(row); row = []
    if row: kb.append(row)
    
    kb.append([InlineKeyboardButton("⬅️ Sair", callback_data="show_kingdom_menu")])
    
    await _safe_edit(query, text, InlineKeyboardMarkup(kb))

# ==================================================================
# 2. ESCOLHER PROFISSÃO
# ==================================================================
async def pick_profession_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    user_id = get_current_player_id(update, context)
    player_data = await player_manager.get_player_data(user_id)
    
    prof_data = player_data.get("profession") or {}
    if prof_data.get("type") or prof_data.get("key"):
        await query.answer("Você já tem uma profissão!", show_alert=True)
        await job_menu_callback(update, context)
        return

    target_prof = query.data.replace("job_pick_", "")
    if target_prof not in PROFESSIONS_DATA:
        await query.answer("Profissão inválida.", show_alert=True)
        return

    player_data["profession"] = {
        "type": target_prof, 
        "level": 1,
        "xp": 0
    }
    await player_manager.save_player_data(user_id, player_data)
    
    p_name = _get_prof_display_name(target_prof)
    await query.answer(f"Você se tornou um {p_name}!", show_alert=True)
    await job_menu_callback(update, context)

# ==================================================================
# 3. LISTAR RECEITAS (CORRIGIDO: SUPORTE A LISTA DE REQUISITOS)
# ==================================================================
async def job_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = get_current_player_id(update, context)
    player_data = await player_manager.get_player_data(user_id)
    
    prof_data = player_data.get("profession") or {}
    my_prof_key = prof_data.get("type") or prof_data.get("key")
    
    if not my_prof_key:
        await query.answer("Escolha uma profissão primeiro!", show_alert=True)
        await job_menu_callback(update, context)
        return

    try:
        parts = query.data.split("_")
        mode = parts[2] # 'refine' ou 'craft'
        page = int(parts[3])
    except:
        mode = "craft"; page = 1

    recipes = []
    
    if mode == "refine":
        # Lista receitas de refino
        for k, v in REFINING_RECIPES.items():
            temp = v.copy(); temp['id'] = k
            recipes.append(temp)
            
    elif mode == "craft":
        all_recipes = crafting_registry.all_recipes()
        for k, v in all_recipes.items():
            # CORREÇÃO: Verifica se o requisito é uma lista OU string
            req = v.get("profession_req")
            
            allowed = False
            if isinstance(req, list):
                if my_prof_key in req: allowed = True
            elif req == my_prof_key:
                allowed = True
            elif req is None:
                allowed = True # Receitas sem requisito

            if allowed:
                temp = v.copy(); temp['id'] = k
                recipes.append(temp)

    total_items = len(recipes)
    total_pages = math.ceil(total_items / RECIPES_PER_PAGE) or 1
    page = max(1, min(page, total_pages))
    
    start = (page - 1) * RECIPES_PER_PAGE
    end = start + RECIPES_PER_PAGE
    current_list = recipes[start:end]
    
    prof_display = _get_prof_display_name(my_prof_key)
    mode_display = "Refino" if mode == "refine" else "Criação"
    
    text = f"⚒️ <b>{mode_display} ({prof_display})</b> - Pág {page}/{total_pages}\n\n"
    
    kb = []
    if not current_list:
        text += "<i>Nenhuma receita disponível.</i>"
    else:
        for rec in current_list:
            rid = rec['id']
            
            # --- BUSCA INTELIGENTE DE NOME ---
            final_item_id = None
            if "result_id" in rec: final_item_id = rec["result_id"]
            elif "result_base_id" in rec: final_item_id = rec["result_base_id"]
            elif "outputs" in rec and isinstance(rec["outputs"], dict):
                keys = list(rec["outputs"].keys())
                if keys: final_item_id = keys[0]

            name = rec.get("result_name") 
            if final_item_id:
                item_db_info = ITEMS_DATA.get(final_item_id, {})
                if not name: name = item_db_info.get("display_name")
                if not name: name = final_item_id.replace("_", " ").title()
            
            if not name: name = "Item Misterioso"

            lvl_req = rec.get("level_req", 1)
            
            # Botão de Criar
            kb.append([InlineKeyboardButton(f"🔨 {name} (Nv.{lvl_req})", callback_data=f"job_do_{mode}_{rid}")])
            
            # Texto de custo
            mats = rec.get("materials") or rec.get("inputs") or {}
            mats_str = ", ".join([f"{qty}x {mid}" for mid, qty in mats.items()])
            text += f"🔹 <b>{name}</b>: {mats_str}\n"

    nav = []
    if page > 1: nav.append(InlineKeyboardButton("⬅️", callback_data=f"job_list_{mode}_{page-1}"))
    nav.append(InlineKeyboardButton("🔙 Menu", callback_data="job_menu"))
    if page < total_pages: nav.append(InlineKeyboardButton("➡️", callback_data=f"job_list_{mode}_{page+1}"))
    kb.append(nav)
    
    await _safe_edit(query, text, InlineKeyboardMarkup(kb))

# ==================================================================
# EXECUTOR
# ==================================================================
async def job_do_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    user_id = get_current_player_id(update, context)
    player_data = await player_manager.get_player_data(user_id)
    
    try:
        _, _, mode, recipe_id = query.data.split("_", 3)
    except: return

    from modules import profession_engine
    
    if mode == "refine":
        result = await profession_engine.try_refine(user_id, player_data, recipe_id)
    else:
        result = await profession_engine.try_craft(user_id, player_data, recipe_id)
        
    if result.get("success"):
        await query.answer("✅ Sucesso!", show_alert=False)
        await context.bot.send_message(query.message.chat.id, result["message"])
    else:
        await query.answer(result.get("error", "Erro."), show_alert=True)

# HANDLERS
job_menu_handler = CallbackQueryHandler(job_menu_callback, pattern=r'^job_menu$')
job_pick_handler = CallbackQueryHandler(pick_profession_callback, pattern=r'^job_pick_')
job_list_handler = CallbackQueryHandler(job_list_callback, pattern=r'^job_list_')
job_do_handler = CallbackQueryHandler(job_do_callback, pattern=r'^job_do_')