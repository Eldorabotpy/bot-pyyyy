# handlers/inventory_handler.py
# (VERSÃO FINAL: COMPATÍVEL COM VIEW DE DETALHES + LAYOUT SOLICITADO)

import math
import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
)
from telegram.ext import ContextTypes, CallbackQueryHandler

# AUTH: Apenas o novo sistema
from modules.auth_utils import get_current_player_id
from modules import player_manager, game_data, file_ids
from modules.game_data import skills as skills_data
from modules.game_data.skins import SKIN_CATALOG
from modules.player import stats as player_stats
from modules.game_data.class_evolution import can_player_use_skill
from modules.player import actions as player_actions

logger = logging.getLogger(__name__)

# Configurações Visuais
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
# Helpers Locais
# -----------------------------------------------------------

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

def _determine_tab(item_key: str, item_value) -> str:
    if isinstance(item_value, dict): return "equipamento"
    info = _info_for(item_key)
    tipo = (info.get("type") or "").lower()
    cat = (info.get("category") or "").lower()
    
    if "tomo_" in item_key or "caixa_" in item_key or "livro" in item_key: return "aprendizado"
    effects = info.get("effects") or info.get("on_use") or {}
    if effects.get("effect") in ("grant_skill", "grant_skin") or "learn_skill" in effects: return "aprendizado"
    if cat == "evento" or tipo == "event_ticket" or "ticket" in item_key or "fragmento" in item_key: return "evento"
    if tipo == "equipamento" or info.get("slot"): return "equipamento"
    if tipo == "material_monstro" or cat == "cacada": return "cacada"
    if cat == "evolucao" or info.get("evolution_item") is True: return "especial"
    if tipo in ("material_bruto", "material_refinado", "sucata") or cat == "coletavel": return "refino"
    
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

async def _force_fix_inventory_items(user_id, player_data):
    inventory = player_data.get("inventory", {})
    if not inventory: return False
    mudou = False
    
    correcoes = {
        "ferro": "minerio_de_ferro", "minerio_ferro": "minerio_de_ferro", "iron_ore": "minerio_de_ferro",
        "pedra_ferro": "minerio_de_ferro", "minerio_bruto": "minerio_de_ferro", "minerio_de_ferro_bruto": "minerio_de_ferro",
        "minerio_estanho": "minerio_de_estanho", "tin_ore": "minerio_de_estanho",
        "minerio_prata": "minerio_de_prata", "silver_ore": "minerio_de_prata",
        "madeira_rara_bruta": "madeira_rara", "wood_rare": "madeira_rara",
        "carvao_mineral": "carvao", "coal": "carvao"
    }

    for velho, novo in correcoes.items():
        if velho in inventory:
            if velho == novo: continue
            dado_velho = inventory[velho]
            qtd_velha = int(dado_velho.get("quantity", 1)) if isinstance(dado_velho, dict) else int(dado_velho)
            
            if qtd_velha > 0:
                if novo not in inventory: inventory[novo] = 0
                if isinstance(inventory[novo], dict):
                    inventory[novo]["quantity"] = int(inventory[novo].get("quantity", 0)) + qtd_velha
                else:
                    inventory[novo] = int(inventory[novo]) + qtd_velha
                mudou = True
            
            del inventory[velho]
            mudou = True
            
    if mudou:
        await player_manager.save_player_data(user_id, player_data)
    return mudou

# -----------------------------------------------------------
# 1. MENU PRINCIPAL
# -----------------------------------------------------------

async def inventory_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    user_id = get_current_player_id(update, context)
    if not user_id:
        if query: await query.answer("Sessão inválida. Use /start", show_alert=True)
        return
    
    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return

    try: await _force_fix_inventory_items(user_id, player_data)
    except Exception as e: logger.error(f"Erro fix inventory: {e}")

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
            buttons.append(row); row = []
    if row: buttons.append(row)
    
    buttons.append([
        InlineKeyboardButton("🔥 Minhas Skills", callback_data="skills_menu_open"),
        InlineKeyboardButton("🎭 Minhas Skins", callback_data="skin_menu")
    ])
    buttons.append([InlineKeyboardButton("🔙 Voltar ao Perfil", callback_data="profile")])
    
    chat_id = update.effective_chat.id
    if query:
        await _safe_edit_or_send(query, context, chat_id, text, InlineKeyboardMarkup(buttons))
    else:
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")

# -----------------------------------------------------------
# 2. LISTA DE ITENS (CATÁLOGO)
# -----------------------------------------------------------

async def inventory_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, manual_data=None):
    query = update.callback_query
    if not manual_data: await query.answer()
    
    target_data = manual_data if manual_data else query.data
    try:
        _, _, cat_key, page_str = target_data.split("_")
        page = int(page_str)
    except:
        await inventory_menu_callback(update, context)
        return

    user_id = get_current_player_id(update, context)
    if not user_id: return
    
    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return
    
    inventory = player_data.get("inventory", {})
    
    items_in_cat = []
    for k, v in inventory.items():
        if k in ("ouro", "gold", "gems"): continue
        
        # Filtro de categoria
        if _determine_tab(k, v) == cat_key:
            if isinstance(v, dict): 
                # Item Único (Equipamento/Custom)
                name = _display_name_for_instance(k, v)
                base_id_debug = v.get("base_id", "item")
                items_in_cat.append({"name": name, "id": k, "qty": 1, "type": "unique", "base_id": base_id_debug})
            else:
                # Item Stack (Consumível/Material)
                info = _info_for(k)
                name = info.get("display_name") or k.replace("_", " ").title()
                emoji = info.get("emoji", "")
                full_name = f"{emoji} {name}".strip()
                items_in_cat.append({"name": full_name, "id": k, "qty": v, "type": "stack", "base_id": k})

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
            
            # AGORA O CLICK VAI PARA A VIEW (DETALHES), NÃO PARA O USO DIRETO
            cb_data = f"inv_view:{item['id']}"
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
# 3. DETALHES DO ITEM (NOVO MENU SOLICITADO)
# -----------------------------------------------------------

async def inventory_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = get_current_player_id(update, context)
    if not user_id: return

    try: item_id = query.data.split(":", 1)[1]
    except: return

    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return

    item_val = player_data.get("inventory", {}).get(item_id)
    if not item_val:
        await query.answer("Item não encontrado ou removido.", show_alert=True)
        await inventory_menu_callback(update, context)
        return

    # Determina Base ID e Tipo
    is_unique = isinstance(item_val, dict)
    base_id = item_val.get("base_id") if is_unique else item_id
    qty = 1 if is_unique else item_val
    
    # Carrega Info
    info = _info_for(base_id)
    name = info.get("display_name") or base_id.replace("_", " ").title()
    emoji = info.get("emoji", "")
    full_name = f"{emoji} {name}".strip()
    desc = info.get("description", "Sem descrição.")
    tipo = (info.get("type") or "Item").replace("_", " ").title()
    cat_key = _determine_tab(base_id, item_val)
    cat_label = CATEGORIES.get(cat_key, {}).get("label", "Outros")
    
    # Validações de Uso
    player_class_key = player_stats._get_class_key_normalized(player_data)
    can_use = True
    lock_reason = ""

    # Verifica se é equipamento (Redireciona para menu de equip)
    is_equip = is_unique or info.get("type") == "equipamento"
    
    if not is_equip:
        # Verifica efeitos para saber se é "usável"
        effects = info.get("on_use") or info.get("effects") or {}
        if not effects:
            can_use = False # Apenas material, não tem botão usar
        
        # Verifica Classe
        class_req = info.get("class_req")
        if class_req and not can_player_use_skill(player_class_key, class_req):
            can_use = False
            lock_reason = f"(Req: {class_req[0].title()})"

    # --- MONTAGEM DO TEXTO (LAYOUT SOLICITADO) ---
    text = (
        f"📊 <b>{full_name}</b>\n"
        f"├┈➤ {desc}\n"
        f"├┈➤ <b>Categoria:</b> {cat_label}\n"
        f"├┈➤ <b>Tipo:</b> {tipo}\n"
        f"╰┈➤ <b>Quantidade:</b> {qty}"
    )
    if lock_reason:
        text += f"\n\n🔒 <b>Bloqueado:</b> {lock_reason}"

    # --- MONTAGEM DOS BOTÕES ---
    buttons = []
    
    # Botão de Ação
    if is_equip:
        # Se for equip, botão manda para menu de equipamentos
        buttons.append([InlineKeyboardButton("⚙️ Gerenciar Equipamento", callback_data="equipment_menu")])
    elif can_use:
        # Se for consumível e puder usar
        buttons.append([InlineKeyboardButton("✅ Usar Item", callback_data=f"inv_use_item:{item_id}")])
    
    # Botão Voltar (Calcula a aba correta para não perder o lugar)
    back_data = f"inv_open_{cat_key}_1"
    buttons.append([InlineKeyboardButton("🔙 Voltar ao Menu Anterior", callback_data=back_data)])

    # Usa a função segura com a media_key do item (se tiver imagem específica) ou padrão
    media_k = info.get("media_key", "img_inventario")
    await _safe_edit_or_send(query, context, query.message.chat.id, text, InlineKeyboardMarkup(buttons), media_key=media_k)


# -----------------------------------------------------------
# 4. USO DE ITENS (LÓGICA)
# -----------------------------------------------------------

async def use_item_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    user_id = get_current_player_id(update, context)
    if not user_id: return

    try: item_id = query.data.split(":", 1)[1]
    except: return

    # Feedback imediato no botão para parecer responsivo
    # await query.answer("Usando...") 

    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return

    item_val = player_data.get("inventory", {}).get(item_id)
    if not item_val:
        await query.answer("Você não tem mais este item.", show_alert=True)
        # Tenta voltar para a lista
        await inventory_menu_callback(update, context)
        return

    # Info Básica
    is_unique = isinstance(item_val, dict)
    base_id = item_val.get("base_id") if is_unique else item_id
    item_info = _info_for(base_id)
    item_name = item_info.get("display_name", base_id)

    # Extrai Efeitos
    on_use_data = item_info.get("on_use", {}) or {}
    effects_data = item_info.get("effects", {}) or {}
    effect_data_to_use = {**on_use_data, **effects_data}

    if not effect_data_to_use:
        await query.answer(f"O item '{item_name}' não pode ser usado.", show_alert=True)
        return

    # Consome 1 unidade
    if not player_manager.remove_item_from_inventory(player_data, item_id, 1):
        await query.answer("Erro ao consumir item.", show_alert=True)
        return

    # Aplica Efeitos
    feedback_msg = f"Você usou {item_name}!"
    effect = effect_data_to_use.get("effect")
    skill_id = effect_data_to_use.get("skill_id") or effect_data_to_use.get("learn_skill")
    skin_id = effect_data_to_use.get("skin_id")
    
    try:
        if (effect == "grant_skill" or "learn_skill" in effect_data_to_use) and skill_id:
            if skill_id not in skills_data.SKILL_DATA:
                player_manager.add_item_to_inventory(player_data, item_id, 1)
                raise ValueError(f"Skill ID {skill_id} inválida.")

            if "skills" not in player_data: player_data["skills"] = {}
            if "equipped_skills" not in player_data: player_data["equipped_skills"] = []

            if skill_id in player_data["skills"]:
                await query.answer("Você já conhece esta habilidade!", show_alert=True)
                player_manager.add_item_to_inventory(player_data, item_id, 1)
                return

            player_data["skills"][skill_id] = {"rarity": "comum", "progress": 0}
            if skill_id not in player_data["equipped_skills"]:
                player_data["equipped_skills"].append(skill_id)

            skill_name_display = skills_data.SKILL_DATA[skill_id].get("display_name", skill_id)
            feedback_msg = f"📚 Você aprendeu: {skill_name_display}!"
            
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
        feedback_msg = "Erro ao usar item. Devolvido."

    await player_manager.save_player_data(user_id, player_data)
    await query.answer(feedback_msg, show_alert=True)

    # Após usar, REABRE A VIEW DO ITEM (para mostrar a qtd atualizada)
    # Se a quantidade for 0, o inventory_view_callback vai tratar e jogar pro menu
    query.data = f"inv_view:{item_id}" 
    await inventory_view_callback(update, context)

async def noop_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        data_parts = query.data.split(":", 1)
        msg = data_parts[1] if len(data_parts) > 1 else "Ação inválida"
        if "Página" in msg: await query.answer() 
        else: await query.answer(f"🚫 {msg}", show_alert=True)
    except Exception:
        await query.answer()

# -----------------------------------------------------------
# DEFINIÇÃO DOS HANDLERS (EXPORTS CRÍTICOS)
# -----------------------------------------------------------

inventory_menu_handler = CallbackQueryHandler(inventory_menu_callback, pattern=r'^inventory_menu$')
inventory_cat_handler = CallbackQueryHandler(inventory_category_callback, pattern=r'^inv_open_')

# Novo Handler para a View de Detalhes
inventory_view_handler = CallbackQueryHandler(inventory_view_callback, pattern=r'^inv_view:')

# Handler de Uso (Ação)
inventory_use_handler = CallbackQueryHandler(use_item_callback, pattern=r'^inv_use_item:')

noop_inventory_handler = CallbackQueryHandler(noop_inventory, pattern=r'^noop_inventory')

# ALIASES para compatibilidade com registries/character.py
inventory_list_handler = inventory_cat_handler