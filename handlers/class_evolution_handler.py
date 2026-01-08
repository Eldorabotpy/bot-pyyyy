# handlers/class_evolution_handler.py
# (VERSÃO LIMPA: Apenas Árvore de Ascensão + Link para Novo Menu de Skills)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

from modules.auth_utils import get_current_player_id
from modules import player_manager
from modules import class_evolution_service as evo_service
from modules.game_data import class_evolution as evo_data
from modules.game_data.monsters import MONSTERS_DATA
from modules import evolution_battle

logger = logging.getLogger(__name__)

# ================================================
# FUNÇÕES AUXILIARES VISUAIS
# ================================================

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
    """Retorna o nome da classe formatado corretamente."""
    raw_class = (pdata.get("class") or "N/A").lower()
    # Normaliza caracteres especiais
    class_key = raw_class.replace("ç", "c").replace("ã", "a")
    
    if class_key in evo_data.EVOLUTIONS: return class_key.title()
    try:
        evo_def = evo_data.find_evolution_by_target(class_key)
        if evo_def: return evo_def.get("to", class_key).title()
    except AttributeError:
        pass
    
    return raw_class.title()

# ================================================
# MENU PRINCIPAL (ÁRVORE DE ASCENSÃO)
# ================================================

async def open_evolution_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = get_current_player_id(update, context)
    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return

    # Normaliza a classe para consulta no service
    pdata_for_eval = pdata.copy()
    if pdata_for_eval.get("class"):
        pdata_for_eval["class"] = pdata_for_eval["class"].lower().replace("ç", "c").replace("ã", "a")
    
    status_info = evo_service.get_player_evolution_status(pdata_for_eval)

    current_class_name = _get_player_class_name(pdata)
    level = pdata.get("level", 1)
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
        
        # Renderiza os nós da árvore
        for node in status_info.get("path_nodes", []):
            if node["status"] == "complete":
                caption_lines.append(f"  ✅ <s>{node['desc']}</s>")
            elif node["status"] == "available":
                caption_lines.append(f"  🔘 <b>{node['desc']}</b>")
                keyboard.append([InlineKeyboardButton(f"Ver: {node['desc']}", callback_data=f"evo_node_info:{node['id']}")])
            elif node["status"] == "locked":
                caption_lines.append(f"  🔒 <i>{node['desc']}</i>")

        # Se tudo estiver completo, libera o teste
        if status_info.get("all_nodes_complete", False):
            caption_lines.append("\n<b>Caminho completo!</b> O Teste Final aguarda.")
            keyboard.append([InlineKeyboardButton(f"⚔️ Iniciar Teste: {target_class.title()}", callback_data=f"evo_start_trial_confirm:{target_class}")])
    
    # --- BOTÃO NOVO DE SKILLS ---
    # Redireciona para o handler 'skill_upgrade_handler.py'
    keyboard.append([InlineKeyboardButton("📘 Aprimorar Habilidades", callback_data="menu_skills_main")])
    
    # Voltar para a região (Hub)
    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Mapa", callback_data=f"open_region:{current_location}")])
    
    try: 
        await query.edit_message_text("\n".join(caption_lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    except BadRequest: 
        pass

# ================================================
# HANDLERS DA ÁRVORE (Nós e Tarefas)
# ================================================

async def show_node_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try: node_id = query.data.split(":", 1)[1]
    except: return

    user_id = get_current_player_id(update, context)
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
    
    user_id = get_current_player_id(update, context)
    
    # Chama o service para validar e gastar recursos
    success, msg = await evo_service.attempt_ascension_node(user_id, node_id)
    
    await query.answer(msg, show_alert=True)
    await open_evolution_menu(update, context)

# ================================================
# BATALHA DE PROVAÇÃO (TRIAL)
# ================================================

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
    user_id = get_current_player_id(update, context)
    
    try: 
        target = query.data.split(":", 1)[1]
    except: 
        return

    # 1. Verifica requisitos (service)
    result = await evo_service.start_evolution_trial(user_id, target)
    if not result.get("success"):
        await query.answer(result.get("message"), show_alert=True)
        return

    # 2. Busca o monstro do teste
    evo_def = evo_data.find_evolution_by_target(target)
    if not evo_def:
        await query.answer("Erro: Evolução não encontrada.", show_alert=True)
        return
        
    monster_id = evo_def.get("trial_monster_id")
    monster_data = None
    
    # Busca na lista especial de trials
    trials_list = MONSTERS_DATA.get("_evolution_trials", [])
    for mob in trials_list:
        if mob["id"] == monster_id:
            monster_data = mob.copy() 
            break
            
    # Fallback: Busca geral
    if not monster_data:
        for region_list in MONSTERS_DATA.values():
            if isinstance(region_list, list):
                for mob in region_list:
                    if mob.get("id") == monster_id:
                        monster_data = mob.copy()
                        break
            if monster_data: break

    if not monster_data:
        await query.answer(f"Erro: Monstro '{monster_id}' não encontrado.", show_alert=True)
        return

    # 3. Configura o combate
    pdata = await player_manager.get_player_data(user_id)
    
    combat_details = monster_data.copy()
    combat_details['is_evolution_trial'] = True
    combat_details['target_class_reward'] = target
    combat_details['monster_hp'] = combat_details.get('hp')
    combat_details['monster_max_hp'] = combat_details.get('hp')
    combat_details['monster_name'] = combat_details.get('name')
    
    pdata['player_state'] = {
        'action': 'evolution_combat', 
        'details': combat_details
    }
    
    await player_manager.save_player_data(user_id, pdata)
    
    if 'battle_cache' in context.user_data:
        del context.user_data['battle_cache']

    # 4. Inicia a apresentação visual
    await evolution_battle.start_evolution_presentation(update, context, user_id, target)

# ================================================
# EXPORTS (REGISTRO NO MAIN)
# ================================================

status_evolution_open_handler = CallbackQueryHandler(open_evolution_menu, pattern=r'^open_evolution_menu$')
show_node_info_handler = CallbackQueryHandler(show_node_info, pattern=r'^evo_node_info:')
complete_node_handler = CallbackQueryHandler(complete_node, pattern=r'^evo_complete_node:')
start_trial_confirmation_handler = CallbackQueryHandler(start_trial_confirmation, pattern=r'^evo_start_trial_confirm:')
start_trial_execute_handler = CallbackQueryHandler(start_trial_execute, pattern=r'^evo_start_trial_execute:')
evo_battle_start_handler = CallbackQueryHandler(evolution_battle.start_evo_combat_callback, pattern=r'^start_evo_combat$')