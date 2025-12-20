# handlers/class_evolution_handler.py
# (VERSÃO CORRIGIDA - Botão Voltar leva para a Região Atual)

import logging
from typing import Dict, Tuple, Optional, List, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

from modules import player_manager
from modules import class_evolution_service as evo_service
from modules.game_data import class_evolution as evo_data
from modules.game_data.skills import SKILL_DATA
from modules.player import stats as player_stats

# Importamos o novo módulo de batalha para iniciar a apresentação visual
from modules import evolution_battle

logger = logging.getLogger(__name__)

# --- Funções Auxiliares de Formatação ---

def _format_cost_lines(cost: dict) -> str:
    """Formata o custo (itens/gold) para exibição."""
    lines = []
    if not cost:
        return "<i>Sem custo</i>"
        
    if "gold" in cost:
        lines.append(f"  • {cost['gold']:,} 🪙 Ouro")
    
    try:
        from modules.game_data.items import ITEMS_DATA
    except ImportError:
        ITEMS_DATA = {}
    
    for item_id, qty in cost.items():
        if item_id == "gold": continue
        item_info = ITEMS_DATA.get(item_id, {})
        item_name = item_info.get("display_name", item_id)
        item_emoji = item_info.get("emoji", "💠")
        lines.append(f"  • {item_emoji} {item_name} x{qty}")
        
    return "\n".join(lines)

def _get_player_class_name(pdata: dict) -> str:
    class_key = (pdata.get("class") or "N/A").lower()
    if class_key in evo_data.EVOLUTIONS: return class_key.title()
    try:
        evo_def = evo_data.find_evolution_by_target(class_key)
        if evo_def: return evo_def.get("to", class_key).title()
    except AttributeError:
        pass
    return class_key.title()

# ================================================
# HANDLER PRINCIPAL (MENU DA ÁRVORE)
# ================================================

async def open_evolution_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return

    status_info = evo_service.get_player_evolution_status(pdata)
    current_class_name = _get_player_class_name(pdata)
    level = pdata.get("level", 1)
    
    # Recupera a localização atual para o botão de voltar
    current_location = pdata.get("current_location", "reino_eldora")
    
    caption_lines = [
        f"⛩️ <b>Caminho da Ascensão</b> ⛩️",
        f"Classe: {current_class_name} (Nível {level})",
        "---"
    ]
    keyboard = []

    if status_info["status"] == "max_tier":
        caption_lines.append("Você atingiu o auge da sua classe.")
    elif status_info["status"] == "locked":
        evo_opt = status_info["option"]
        caption_lines.append(f"Próxima: <b>{evo_opt['to'].title()}</b>")
        caption_lines.append(f"🔒 {status_info['message']}")
    elif status_info["status"] == "path_available":
        evo_opt = status_info["option"]
        target_class = evo_opt['to']
        caption_lines.append(f"Próxima: <b>{target_class.title()}</b>")
        caption_lines.append(f"<i>{evo_opt['desc']}</i>\n")
        
        for node in status_info.get("path_nodes", []):
            if node["status"] == "complete":
                caption_lines.append(f"  ✅ <s>{node['desc']}</s>")
            elif node["status"] == "available":
                caption_lines.append(f"  🔘 <b>{node['desc']}</b>")
                keyboard.append([InlineKeyboardButton(f"Ver: {node['desc']}", callback_data=f"evo_node_info:{node['id']}")])
            elif node["status"] == "locked":
                caption_lines.append(f"  🔒 <i>{node['desc']}</i>")

        if status_info.get("all_nodes_complete", False):
            caption_lines.append("\n<b>Caminho completo!</b> O Teste Final aguarda.")
            keyboard.append([InlineKeyboardButton(f"⚔️ Iniciar Teste: {target_class.title()}", callback_data=f"evo_start_trial_confirm:{target_class}")])
    
    # Botão de Skills
    keyboard.append([InlineKeyboardButton("💎 Aprimorar Skills de Evolução", callback_data="evo_skill_ascend_menu")])
    
    # [CORREÇÃO] Botão Voltar agora aponta para a região atual
    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Mapa", callback_data=f"open_region:{current_location}")])
    
    try: await query.edit_message_text("\n".join(caption_lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    except BadRequest: pass

# ================================================
# LÓGICA DE CUSTO DE SKILL
# ================================================

RARITY_UPGRADE_PATH_EVO = {
    "comum": {"cap": 10, "next": "epica"},
    "epica": {"cap": 10, "next": "lendaria"},
    "lendaria": None
}

def _get_skill_upgrade_cost(pdata: dict, skill_id: str, current_rarity: str) -> Optional[dict]:
    """Calcula o custo para aprimorar uma skill."""
    skill_data = SKILL_DATA.get(skill_id)
    if not skill_data: return None

    base_class = player_stats._get_class_key_normalized(pdata)
    
    # 1. Tenta descobrir o Tier da Skill
    target_tier = 1 
    for evo in evo_data.EVOLUTIONS.get(base_class, []):
        if skill_id in evo.get("unlocks_skills", []):
            target_tier = evo.get("tier_num")
            break
            
    # 2. Define o Tier do material de custo (Sempre Tier + 1)
    cost_tier = target_tier + 1
    if target_tier >= 6: cost_tier = 6

    # 3. Encontra a evolução que contém o material de custo
    cost_evolution = None
    for evo in evo_data.EVOLUTIONS.get(base_class, []):
        if evo.get("tier_num") == cost_tier:
            cost_evolution = evo
            break
            
    if not cost_evolution:
        if current_rarity == "lendaria": return None
        return {"gold": 50000} 

    # 4. Extrai o ID do material
    material_id = None
    asc_path = cost_evolution.get("ascension_path", [])
    if asc_path:
        first_node_cost = asc_path[0].get("cost", {})
        for item in first_node_cost:
            if item != "gold":
                material_id = item
                break
    
    if not material_id: return {"gold": 50000}

    # 5. Define quantidades
    cost = {}
    if current_rarity == "comum":
        cost[material_id] = 10
        cost["gold"] = 5000
    elif current_rarity == "epica":
        cost[material_id] = 20
        cost["gold"] = 10000
    else:
        return None

    return cost

# ================================================
# MENUS DE SKILL E OUTROS HANDLERS
# ================================================

async def show_node_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try: node_id = query.data.split(":", 1)[1]
    except: return

    user_id = query.from_user.id
    pdata = await player_manager.get_player_data(user_id)
    status_info = evo_service.get_player_evolution_status(pdata)

    node = next((n for n in status_info.get("path_nodes", []) if n["id"] == node_id), None)
    if not node:
        await query.answer("Tarefa indisponível.", show_alert=True)
        await open_evolution_menu(update, context)
        return

    cost_str = _format_cost_lines(node.get("cost", {}))
    text = f"🔘 <b>Tarefa: {node['desc']}</b>\n\nCusto:\n{cost_str}"
    kb = [[InlineKeyboardButton("✅ Completar", callback_data=f"evo_complete_node:{node_id}")],
          [InlineKeyboardButton("⬅️ Voltar", callback_data="open_evolution_menu")]]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def complete_node(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: node_id = query.data.split(":", 1)[1]
    except: return
    
    success, msg = await evo_service.attempt_ascension_node(query.from_user.id, node_id)
    await query.answer(msg, show_alert=True)
    await open_evolution_menu(update, context)

async def start_trial_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: target = query.data.split(":", 1)[1]
    except: return
    
    text = f"⚔️ <b>Teste: {target.title()}</b>\nDeseja iniciar a batalha pela sua evolução?"
    kb = [[InlineKeyboardButton("⚔️ Lutar!", callback_data=f"evo_start_trial_execute:{target}")],
          [InlineKeyboardButton("Cancelar", callback_data="open_evolution_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def start_trial_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    try: target = query.data.split(":", 1)[1]
    except: return

    # 1. Verifica se pode iniciar (service)
    result = await evo_service.start_evolution_trial(user_id, target)
    if not result.get("success"):
        await query.answer(result.get("message"), show_alert=True)
        return

    # 2. Inicia a apresentação visual (agora usando o NOVO módulo)
    await evolution_battle.start_evolution_presentation(update, context, user_id, target)

# --- SKILL ASCENSION HANDLERS ---

async def show_skill_ascension_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pdata = await player_manager.get_player_data(query.from_user.id)
    skills = pdata.get("skills", {})
    
    text = "💎 <b>Aprimorar Skills</b> 💎\nSelecione uma skill para evoluir sua raridade.\n"
    kb = []
    
    valid_skills = []
    for sid, sdata in skills.items():
        if isinstance(sdata, dict) and sid in SKILL_DATA:
            valid_skills.append(sid)
            
    if not valid_skills:
        text += "\n<i>Nenhuma skill aprimorável encontrada.</i>"
    
    for sid in valid_skills:
        sdata = skills[sid]
        info = SKILL_DATA[sid]
        rarity = sdata.get("rarity", "comum")
        prog = sdata.get("progress", 0)
        path = RARITY_UPGRADE_PATH_EVO.get(rarity)
        
        if path:
            btn_txt = f"{info['display_name']} ({rarity.title()} {prog}/{path['cap']})"
            kb.append([InlineKeyboardButton(btn_txt, callback_data=f"evo_skill_ascend_info:{sid}")])
        else:
            kb.append([InlineKeyboardButton(f"🌟 {info['display_name']} (MÁX)", callback_data="noop")])

    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="open_evolution_menu")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def show_skill_ascension_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try: sid = query.data.split(":", 1)[1]
    except: return
    
    pdata = await player_manager.get_player_data(query.from_user.id)
    sdata = pdata["skills"].get(sid)
    info = SKILL_DATA.get(sid)
    
    rarity = sdata.get("rarity", "comum")
    cost = _get_skill_upgrade_cost(pdata, sid, rarity)
    
    text = f"💎 <b>{info['display_name']}</b>\n"
    text += f"Raridade: {rarity.title()}\n"
    text += f"Progresso: {sdata.get('progress', 0)}/{RARITY_UPGRADE_PATH_EVO[rarity]['cap']}\n\n"
    
    kb = []
    if cost:
        text += "<b>Custo para melhorar:</b>\n" + _format_cost_lines(cost)
        kb.append([InlineKeyboardButton("✅ Melhorar", callback_data=f"evo_skill_ascend_confirm:{sid}")])
    else:
        text += "<i>Não é possível melhorar mais.</i>"
        
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="evo_skill_ascend_menu")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def confirm_skill_ascension(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: sid = query.data.split(":", 1)[1]
    except: return
    
    user_id = query.from_user.id
    pdata = await player_manager.get_player_data(user_id)
    sdata = pdata["skills"].get(sid)
    
    cost = _get_skill_upgrade_cost(pdata, sid, sdata.get("rarity", "comum"))
    if not cost: 
        await query.answer("Erro no custo.", show_alert=True)
        return

    if not evo_service._consume_gold(pdata, cost.get("gold", 0)):
        await query.answer("Ouro insuficiente!", show_alert=True)
        return
        
    items_only = {k:v for k,v in cost.items() if k!="gold"}
    if not evo_service._consume_items(pdata, items_only):
        player_manager.add_gold(pdata, cost.get("gold", 0))
        await query.answer("Itens insuficientes!", show_alert=True)
        return
        
    sdata["progress"] = sdata.get("progress", 0) + 1
    path = RARITY_UPGRADE_PATH_EVO.get(sdata["rarity"])
    
    msg = "✨ Skill aprimorada!"
    if sdata["progress"] >= path["cap"]:
        sdata["rarity"] = path["next"]
        sdata["progress"] = 0
        msg = f"🌟 A skill evoluiu para {sdata['rarity'].title()}!"
        
    await player_manager.save_player_data(user_id, pdata)
    await query.answer(msg, show_alert=True)
    await show_skill_ascension_info(update, context)

# ================================================
# EXPORTS
# ================================================
status_evolution_open_handler = CallbackQueryHandler(open_evolution_menu, pattern=r'^open_evolution_menu$')
show_node_info_handler = CallbackQueryHandler(show_node_info, pattern=r'^evo_node_info:')
complete_node_handler = CallbackQueryHandler(complete_node, pattern=r'^evo_complete_node:')
start_trial_confirmation_handler = CallbackQueryHandler(start_trial_confirmation, pattern=r'^evo_start_trial_confirm:')
start_trial_execute_handler = CallbackQueryHandler(start_trial_execute, pattern=r'^evo_start_trial_execute:')
skill_ascension_menu_handler = CallbackQueryHandler(show_skill_ascension_menu, pattern=r'^evo_skill_ascend_menu$')
skill_ascension_info_handler = CallbackQueryHandler(show_skill_ascension_info, pattern=r'^evo_skill_ascend_info:')
skill_ascension_confirm_handler = CallbackQueryHandler(confirm_skill_ascension, pattern=r'^evo_skill_ascend_confirm:')