# handlers/inventory_handler.py
# (VERSÃO CORRIGIDA: Compatível com "learn_skill" e Trava de Classe)

import math
import re
import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
)
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, game_data, display_utils
from modules import file_ids
from modules.game_data.skins import SKIN_CATALOG
from modules.game_data import skills as skills_data
from modules.player import stats as player_stats
from modules.game_data.class_evolution import can_player_use_skill
from modules.player import actions as player_actions

logger = logging.getLogger(__name__)

# Configurações
ITEMS_PER_PAGE = 5

# --- DEFINIÇÃO DAS CATEGORIAS ---
CATEGORIES = {
    "consumivel":  {"label": "🎒 Consumíveis", "emoji": "🎒"},
    "equipamento": {"label": "⚔️ Equipamentos", "emoji": "⚔️"},
    "cacada":      {"label": "🐺 Caça/Drops",   "emoji": "🐺"},
    "refino":      {"label": "⚒️ Refino/Mat.",  "emoji": "⚒️"},
    "especial":    {"label": "💎 Especiais",    "emoji": "💎"},
    "evento":      {"label": "🎉 Eventos",      "emoji": "🎉"},
    "aprendizado": {"label": "📚 Aprendizado",  "emoji": "📚"},
}

# -----------------------------------------------------------
# Helpers e Ganchos
# -----------------------------------------------------------
try:
    from handlers.utils_timed import auto_finalize_if_due 
except Exception:
    async def auto_finalize_if_due(*args, **kwargs): return

async def _auto_finalize_safe(user_id, context):
    try: await auto_finalize_if_due(user_id, context, player_manager)
    except Exception: pass

def _info_for(key: str) -> dict:
    if not key: return {}
    data = getattr(game_data, "ITEMS_DATA", {}).get(key, {}) or {}
    base = getattr(game_data, "ITEM_BASES", {}).get(key, {}) or {}
    info = {}
    info.update(base)
    info.update(data)
    return info

def _display_name_for_instance(uid: str, inst: dict) -> str:
    base_id = inst.get("base_id")
    info = _info_for(base_id)
    name = inst.get("custom_name") or info.get("display_name") or base_id
    emoji = info.get("emoji", "")
    return f"{emoji} {name}".strip()

def _determine_tab(item_key: str, item_value: dict|int) -> str:
    """Lógica de separação de categorias."""
    if isinstance(item_value, dict): return "equipamento"

    info = _info_for(item_key)
    tipo = (info.get("type") or "").lower()
    cat = (info.get("category") or "").lower()
    
    if "tomo_" in item_key or "caixa_" in item_key or "livro" in item_key: 
        return "aprendizado"
        
    effects = info.get("effects") or info.get("on_use") or {}
    # CORREÇÃO: Detecta learn_skill também
    if effects.get("effect") in ("grant_skill", "grant_skin") or "learn_skill" in effects: 
        return "aprendizado"

    if cat == "evento" or tipo == "event_ticket" or "ticket" in item_key or "fragmento" in item_key: return "evento"
    if tipo == "equipamento" or info.get("slot"): return "equipamento"
    if tipo == "material_monstro" or cat == "cacada": return "cacada"
    
    if tipo in ("material_bruto", "material_refinado", "sucata") or cat == "coletavel":
        if cat == "evolucao": return "especial"
        return "refino"

    itens_melhoria = ("pedra_do_aprimoramento", "nucleo_forja_comum", "nucleo_forja_fraco", "pergaminho_durabilidade", "cristal_de_abertura", "nucleo_de_energia_instavel", "essencia_draconica_pura")
    if item_key in itens_melhoria: return "especial"
    if cat in ("especial", "evolucao") or "chave" in item_key or "gem" in item_key: return "especial"
    if tipo == "material_magico": return "especial"

    return "consumivel"

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML', media_key="img_inventario"):
    fd = file_ids.get_file_data(media_key) or file_ids.get_file_data("inventario_img")
    media_id = fd.get("id") if fd else None
    media_type = (fd.get("type") or "photo").lower()

    if query.message:
        try:
            if media_id:
                media = InputMediaVideo(media_id, caption=text, parse_mode=parse_mode) if media_type == "video" else InputMediaPhoto(media_id, caption=text, parse_mode=parse_mode)
                await query.edit_message_media(media=media, reply_markup=reply_markup)
            else:
                await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
            return
        except Exception: pass 

    try: await query.delete_message()
    except: pass
    
    if media_id:
        try:
            if media_type == "video": await context.bot.send_video(chat_id=chat_id, video=media_id, caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
            else: await context.bot.send_photo(chat_id=chat_id, photo=media_id, caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
            return
        except Exception: pass
        
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

# -----------------------------------------------------------
# 1. MENU PRINCIPAL
# -----------------------------------------------------------

async def inventory_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return

    gold = player_manager.get_gold(player_data)
    gems = player_manager.get_gems(player_data)
    
    text = (
        f"🎒 <b>SEU INVENTÁRIO</b>\n"
        f"💰 <b>Ouro:</b> {gold:,} | 💎 <b>Gemas:</b> {gems}\n\n"
        f"Selecione uma categoria para ver seus itens:"
    )
    
    buttons = []
    row = []
    for key, data in CATEGORIES.items():
        row.append(InlineKeyboardButton(data["label"], callback_data=f"inv_open_{key}_1"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row: buttons.append(row)
    
    buttons.append([
        InlineKeyboardButton("🔥 Minhas Skills", callback_data="skills_menu_open"),
        InlineKeyboardButton("🎭 Minhas Skins", callback_data="skin_menu")
    ])
    
    buttons.append([InlineKeyboardButton("🔙 Voltar ao Perfil", callback_data="profile")])
    
    await _safe_edit_or_send(query, context, query.message.chat.id, text, InlineKeyboardMarkup(buttons))

# -----------------------------------------------------------
# 2. LISTA DE ITENS (COM TRAVA DE CLASSE)
# -----------------------------------------------------------

async def inventory_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, manual_data=None):
    query = update.callback_query
    if not manual_data:
        await query.answer()
    
    target_data = manual_data if manual_data else query.data

    try:
        _, _, cat_key, page_str = target_data.split("_")
        page = int(page_str)
    except:
        await inventory_menu_callback(update, context)
        return

    user_id = query.from_user.id
    player_data = await player_manager.get_player_data(user_id)
    inventory = player_data.get("inventory", {})
    player_class_key = player_stats._get_class_key_normalized(player_data)

    items_in_cat = []
    for k, v in inventory.items():
        if k in ("ouro", "gold", "gems"): continue
        
        if _determine_tab(k, v) == cat_key:
            if isinstance(v, dict): 
                name = _display_name_for_instance(k, v)
                items_in_cat.append({"name": name, "id": k, "qty": 1, "type": "unique"})
            else:
                info = _info_for(k)
                name = info.get("display_name") or k.replace("_", " ").title()
                emoji = info.get("emoji", "")
                full_name = f"{emoji} {name}".strip()
                items_in_cat.append({"name": full_name, "id": k, "qty": v, "type": "stack"})

    total_items = len(items_in_cat)
    total_pages = math.ceil(total_items / ITEMS_PER_PAGE) or 1
    page = max(1, min(page, total_pages))
    
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    current_items = items_in_cat[start:end]
    
    cat_info = CATEGORIES.get(cat_key, {})
    cat_label = cat_info.get("label", "Itens")
    
    text = f"<b>{cat_label}</b> (Pág {page}/{total_pages})\n\n"
    
    item_buttons = []
    if not current_items:
        text += "<i>Nenhum item nesta categoria.</i>"
    else:
        for item in current_items:
            display = f"{item['name']}"
            if item['qty'] > 1: display += f" (x{item['qty']})"
            
            # --- LÓGICA DE TRAVA VISUAL ATUALIZADA ---
            is_locked = False
            req_class_label = ""
            
            item_info = _info_for(item['id'])
            effects = item_info.get("on_use") or item_info.get("effects") or {}
            eff_type = effects.get("effect")
            
            # 1. Verifica Class_Req explícito no Item (Prioridade)
            class_req = item_info.get("class_req")
            if class_req and not can_player_use_skill(player_class_key, class_req):
                is_locked = True
                req_class_label = class_req[0].capitalize()

            # 2. Verifica Skill ID (Formato Antigo e Novo)
            if not is_locked:
                # Tenta pegar ID de skill de ambos os formatos
                sid = effects.get("skill_id") or effects.get("learn_skill")
                
                if sid:
                    skill = skills_data.SKILL_DATA.get(sid, {})
                    allowed = skill.get("allowed_classes", [])
                    if allowed and not can_player_use_skill(player_class_key, allowed):
                        is_locked = True
                        req_class_label = allowed[0].capitalize()
            
            # 3. Verifica Skin
            if not is_locked and eff_type == "grant_skin":
                sid = effects.get("skin_id")
                if sid:
                    skin = SKIN_CATALOG.get(sid, {})
                    cls = skin.get("class")
                    if cls and player_class_key != cls:
                        is_locked = True
                        req_class_label = cls.capitalize()

            if is_locked:
                display_locked = f"🔒 {display} ({req_class_label})"
                cb_data = f"noop_inventory:{req_class_label}"
                item_buttons.append([InlineKeyboardButton(display_locked, callback_data=cb_data)])
            else:
                cb_data = f"inv_use_item:{item['id']}"
                item_buttons.append([InlineKeyboardButton(display, callback_data=cb_data)])

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("⬅️ Ant.", callback_data=f"inv_open_{cat_key}_{page-1}"))
    nav_row.append(InlineKeyboardButton("🔙 Categorias", callback_data="inventory_menu")) 
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("Prox. ➡️", callback_data=f"inv_open_{cat_key}_{page+1}"))
    
    item_buttons.append(nav_row)
    
    await _safe_edit_or_send(query, context, query.message.chat.id, text, InlineKeyboardMarkup(item_buttons))

# -----------------------------------------------------------
# 3. USO DE ITENS
# -----------------------------------------------------------

async def use_item_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    try: item_id = query.data.split(":", 1)[1]
    except: return

    await query.answer("Verificando...")
    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return

    item_val = player_data.get("inventory", {}).get(item_id)
    is_unique = isinstance(item_val, dict)
    base_id = item_val.get("base_id") if is_unique else item_id
    item_info = _info_for(base_id)
    item_name = item_info.get("display_name", base_id)

    if is_unique or item_info.get("type") == "equipamento":
        await query.answer("⚔️ Use o menu 'Equipamentos' para gerenciar.", show_alert=True)
        return

    on_use_data = item_info.get("on_use", {}) or {}
    effects_data = item_info.get("effects", {}) or {}
    # Mescla para garantir que lemos tudo
    effect_data_to_use = {**on_use_data, **effects_data}

    if not effect_data_to_use:
        await query.answer(f"O item '{item_name}' não tem uso direto.", show_alert=True)
        return

    # Tenta remover o item
    if not player_manager.remove_item_from_inventory(player_data, item_id, 1):
        await query.answer("Item não encontrado.", show_alert=True)
        query.data = f"inv_open_{_determine_tab(base_id, 1)}_1"
        await inventory_category_callback(update, context)
        return

    feedback_msg = f"Você usou {item_name}!"
    effect = effect_data_to_use.get("effect")
    
    # --- CORREÇÃO: Tenta ler ID de skill de ambos os formatos ---
    skill_id = effect_data_to_use.get("skill_id") or effect_data_to_use.get("learn_skill")
    skin_id = effect_data_to_use.get("skin_id")
    
    try:
        # === SKILL: Verifica Formato Antigo ("grant_skill") OU Novo ("learn_skill" existe) ===
        if (effect == "grant_skill" or "learn_skill" in effect_data_to_use) and skill_id:
            
            if skill_id not in skills_data.SKILL_DATA:
                # Devolve se skill não existir
                player_manager.add_item_to_inventory(player_data, item_id, 1)
                raise ValueError(f"Skill ID {skill_id} inválida.")

            if "skills" not in player_data or not isinstance(player_data["skills"], dict):
                player_data["skills"] = {}
            if "equipped_skills" not in player_data:
                player_data["equipped_skills"] = []

            if skill_id in player_data["skills"]:
                await query.answer("Você já conhece esta habilidade!", show_alert=True)
                player_manager.add_item_to_inventory(player_data, item_id, 1)
                return

            player_data["skills"][skill_id] = {"rarity": "comum", "progress": 0}

            if skill_id not in player_data["equipped_skills"]:
                player_data["equipped_skills"].append(skill_id)

            skill_name_display = skills_data.SKILL_DATA[skill_id].get("display_name", skill_id)
            feedback_msg = f"📚 Você aprendeu a habilidade: <b>{skill_name_display}</b>!\nEla foi equipada automaticamente."
            
        elif effect == "grant_skin" and skin_id:
            skins = player_data.setdefault("unlocked_skins", [])
            if skin_id not in skins:
                skins.append(skin_id)
                feedback_msg = f"🎨 Aparência desbloqueada!"
            else:
                feedback_msg = "Você já possui essa aparência."
            
        elif effect == "add_pvp_entries":
            val = effect_data_to_use.get("value", 1)
            player_manager.add_pvp_entries(player_data, int(val))
            feedback_msg = f"🎟️ +{val} Entrada(s) na Arena!"

        elif "heal" in effect_data_to_use:
            amt = int(effect_data_to_use["heal"])
            await player_actions.heal_player(player_data, amt)
            feedback_msg = f"❤️ +{amt} HP!"

        elif "add_energy" in effect_data_to_use:
            amt = int(effect_data_to_use["add_energy"])
            player_actions.add_energy(player_data, amt)
            feedback_msg = f"⚡ +{amt} Energia!"
            
        elif "add_xp" in effect_data_to_use:
            amt = int(effect_data_to_use["add_xp"])
            player_data['xp'] = player_data.get('xp', 0) + amt
            player_manager.check_and_apply_level_up(player_data)
            feedback_msg = f"🧠 +{amt} XP!"

        elif "add_mana" in effect_data_to_use:
            amt = int(effect_data_to_use["add_mana"])
            await player_actions.add_mana(player_data, amt)
            feedback_msg = f"💙 +{amt} Mana!"

    except Exception as e:
        logger.error(f"Erro usando item {item_id}: {e}")
        player_manager.add_item_to_inventory(player_data, item_id, 1) 
        feedback_msg = "Erro interno ao usar item. Ele foi devolvido."

    await player_manager.save_player_data(user_id, player_data)
    await query.answer(feedback_msg, show_alert=True)

    tab = _determine_tab(base_id, 1)
    target_data_str = f"inv_open_{tab}_1"
    await inventory_category_callback(update, context, manual_data=target_data_str)

async def noop_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        data_parts = query.data.split(":", 1)
        msg = data_parts[1] if len(data_parts) > 1 else "Ação inválida"
        if "Página" in msg: await query.answer() 
        else: await query.answer(f"🚫 Este item é exclusivo para: {msg}!", show_alert=True)
    except Exception:
        await query.answer()

inventory_menu_handler = CallbackQueryHandler(inventory_menu_callback, pattern=r'^inventory_menu$')
inventory_cat_handler = CallbackQueryHandler(inventory_category_callback, pattern=r'^inv_open_')
use_item_handler = CallbackQueryHandler(use_item_callback, pattern=r'^inv_use_item:')
noop_inventory_handler = CallbackQueryHandler(noop_inventory, pattern=r'^noop_inventory')