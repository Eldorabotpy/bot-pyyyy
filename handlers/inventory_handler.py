# handlers/inventory_handler.py
# (VERSÃO CORRIGIDA - PASSO 5A: LÓGICA DE FUSÃO DE SKILL)

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
from modules import file_ids  # ✅ gerenciador de mídia (JSON)
from modules.game_data.skins import SKIN_CATALOG
from modules.game_data import skills as skills_data
from modules.player import actions as player_actions # Para HP, Energia, etc.
from modules.player import stats as player_stats
from modules.game_data.class_evolution import can_player_use_skill

logger = logging.getLogger(__name__)

# ---- Gancho opcional p/ destravar estados pós-restart ----
try:
    from handlers.utils_timed import auto_finalize_if_due  # se existir
except Exception:
    async def auto_finalize_if_due(*args, **kwargs):
        return

async def _auto_finalize_safe(user_id, context):
    """Wrapper silencioso para tentar finalizar ações vencidas sem quebrar a UI."""
    try:
        await auto_finalize_if_due(user_id, context, player_manager)
    except Exception:
        pass
# -----------------------------------------------------------

ITEMS_PER_PAGE = 5  # Itens por página

# Abas de exibição
CATEGORIES = {
    "consumivel": "🧪 𝑪𝒐𝒏𝒔𝒖𝒎.",
    "coletavel":  "✋ 𝐂𝐨𝐥𝐞𝐭𝐚",
    "cacada":     "🐺 𝐂𝐚𝐜̧𝐚",
    "especial":   "✨ 𝐄𝐬𝐩𝐞𝐄𝐜.",
}

# Aliases aceitos no callback (ex.: botões antigos chamando 'equipamento')
CATEGORY_ALIASES = {
    "equipamento":  "especial",
    "equipamentos": "especial",
    "consumível":   "consumivel",
    "consumiveis":  "consumivel",
    "consumables":  "consumivel",
    "materials":    "coletavel",
    "material":     "coletavel",
    "keys":         "especial",
    "chaves":       "especial",
}

# Mapa canônico type/category -> aba
ITEM_CAT_TO_TAB = {
    # consumíveis
    "consumivel": "consumivel",
    "consumível": "consumivel",
    "consumiveis": "consumivel",
    "consumíveis": "consumivel",

    # materiais/recursos => coletável
    "material": "coletavel",
    "materiais": "coletavel",
    "material_bruto": "coletavel",
    "material_refinado": "coletavel",
    "recurso": "coletavel",
    "recursos": "coletavel",
    "coletavel": "coletavel",
    "coletável": "coletavel",

    # caça
    "caca": "cacada",
    "caça": "cacada",
    "cacada": "cacada",
    "hunt": "cacada",
    "hunting": "cacada",
    "material_monstro": "cacada",

    # especiais / chaves / equipamentos
    "especial": "especial",
    "chave": "especial",
    "chaves": "especial",
    "equipamento": "especial",
    "equipamentos": "especial",
    "event_ticket": "especial",
}

# ---- Heurísticas por NOME de chave (quando não há dados no ITEMS_DATA) ----
_HUNT_NAME_HINTS = (
    "couro", "ectoplasma", "esporo", "joia", "presa", "dente", "asa",
    "escama", "sangue", "pena", "seiva", "carapaca", "carapaça",
    "olho", "glandula", "glândula", "garras", "garra",
    "oss", "femur", "fêmur", "chifre",
    "palha", "ent",
)

_COLLECT_NAME_HINTS = (
    "barra", "madeira", "tabua", "tábua", "ferro", "linho",
    "pano", "pedra", "rolo", "minerio", "minério", "gema_bruta",
    "nucleo_forja", "núcleo_forja",
)

_SPECIAL_NAME_HINTS = (
    "pergaminho", "pedra_do_aprimoramento", "chave", "cristal", "mapa", "ticket",
)

def _first_category_key() -> str:
    return next(iter(CATEGORIES))
def _sanitize_category(cat: str) -> str:
    cat = (cat or "").strip().lower()
    cat = CATEGORY_ALIASES.get(cat, cat)
    return cat if cat in CATEGORIES else _first_category_key()
def _info_for(key: str) -> dict:
    if not key: return {}
    data = getattr(game_data, "ITEMS_DATA", {}).get(key, {}) or {}
    base = getattr(game_data, "ITEM_BASES", {}).get(key, {}) or {}
    info = {}
    info.update(base)
    info.update(data)
    return info
def _humanize_key(key: str) -> str:
    if not key: return ""
    words = key.replace("_", " ").strip().split()
    if not words: return key
    titled = [w.capitalize() for w in words]
    for i, w in enumerate(titled):
        if w.lower() in {"de", "da", "do", "das", "dos"} and i != 0:
            titled[i] = w.lower()
    return " ".join(titled)
def _name_for_key(item_key: str) -> str:
    info = _info_for(item_key)
    return info.get("display_name") or _humanize_key(item_key)
def _display_name_for_instance(uid: str, inst: dict) -> str:
    base_id = inst.get("base_id")
    if inst.get("custom_name"):
        return str(inst["custom_name"])
    info = _info_for(base_id)
    return info.get("display_name") or _humanize_key(base_id or uid)
def _render_item_line_safe(inst: dict) -> str:
    try:
        return display_utils.formatar_item_para_exibicao(inst)
    except Exception:
        return _display_name_for_instance("", inst)
def _extract_raw_category(item_info: dict) -> str:
    keys_in_order = ["category", "type", "tipo", "group", "grupo", "origin", "origem", "item_category"]
    for k in keys_in_order:
        v = (item_info.get(k) or "")
        if isinstance(v, str) and v.strip():
            return v.strip().lower()
    tags = item_info.get("tags") or item_info.get("etiquetas") or []
    if isinstance(tags, (list, tuple)):
        lowered = [str(t).strip().lower() for t in tags]
        for needle in ("cacada", "caça", "hunt", "hunting"):
            if needle in lowered: return "cacada"
        for needle in ("consumivel", "consumível", "potion"):
            if needle in lowered: return "consumivel"
        for needle in ("material", "material_refinado", "recurso", "coletavel", "coletável"):
            if needle in lowered: return "coletavel"
        for needle in ("chave", "especial", "equipamento", "event_ticket"):
            if needle in lowered: return "especial"
    return ""

def _guess_tab_by_key(item_key: str) -> str:
    k = (item_key or "").lower()
    if any(h in k for h in _HUNT_NAME_HINTS): return "cacada"
    if any(h in k for h in _SPECIAL_NAME_HINTS): return "especial"
    if any(h in k for h in _COLLECT_NAME_HINTS): return "coletavel"
    return "coletavel"  
def _item_tab_for(item_info: dict, item_key: str, item_value) -> str:
    raw = _extract_raw_category(item_info)
    if raw:
        mapped = ITEM_CAT_TO_TAB.get(raw)
        if mapped in CATEGORIES:
            return mapped
    hint = _guess_tab_by_key(item_key)
    if hint in CATEGORIES:
        return hint
    t = (item_info.get("type") or item_info.get("tipo") or "").lower()
    if t in ("material", "material_bruto", "material_refinado", "recurso", "coletavel", "coletável"):
        return "coletavel"
    return "especial" if isinstance(item_value, dict) else "coletavel"
async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except Exception as e:
        if "message is not modified" in str(e).lower(): return 
        pass
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except Exception as e:
        if "message is not modified" in str(e).lower(): return 
        pass
    try:
        await query.delete_message()
    except Exception:
        pass
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
def _get_diamonds_amount(player_data: dict) -> int:
    for fn_name in ("get_diamonds", "get_gems"):
        if hasattr(player_manager, fn_name):
            try:
                val = getattr(player_manager, fn_name)(player_data)
                return int(val or 0)
            except Exception: pass
    for k in ("diamonds", "gems", "gemas", "dimas", "diamantes"):
        try:
            if k in player_data: return int(player_data.get(k, 0) or 0)
        except Exception: continue
    return 0
def _merge_legacy_crystals_view(inventory: dict, player_data: dict) -> dict:
    inv = dict(inventory or {})
    legacy_keys = ("cristal_de_abertura", "cristal_abertura")
    for k in legacy_keys:
        try:
            legacy_val = int(player_data.get(k, 0) or 0)
        except Exception: legacy_val = 0
        if legacy_val > 0 and k not in inv:
            inv[k] = legacy_val
    return inv

async def inventory_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    await _auto_finalize_safe(user_id, context)
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await _safe_edit_or_send(query, context, chat_id, "Não encontrei seus dados. Use /start para começar.")
        return

    m = re.match(r"^inventory_CAT_([A-Za-z0-9_]+)_PAGE_([0-9]+)$", (query.data or ""))
    if not m:
        await query.answer("Requisição inválida.", show_alert=True); return

    category_key = _sanitize_category(m.group(1))
    current_page = max(1, int(m.group(2) or 1))

    # --- Pega a classe normalizada (ex: "arcanista") ---
    player_class_key = player_stats._get_class_key_normalized(player_data)

    raw_inventory = player_data.get("inventory", {}) or {}
    inventory = _merge_legacy_crystals_view(raw_inventory, player_data)
    equipped_uids = {v for v in (player_data.get("equipment", {}) or {}).values() if isinstance(v, str) and v}

    filtered_items = []
    for item_key, item_value in inventory.items():
        if item_key in {"ouro", "gold"}: continue
        if isinstance(item_value, dict):
            if item_key in equipped_uids: continue
            base_id = item_value.get("base_id")
            item_info = _info_for(base_id)
            tab = _item_tab_for(item_info, base_id or item_key, item_value)
            key_for_name = base_id or item_key
        else:
            item_info = _info_for(item_key)
            tab = _item_tab_for(item_info, item_key, item_value)
            key_for_name = item_key
        if tab == category_key:
            filtered_items.append((key_for_name, item_value, item_info)) 

    def _display_name(pair):
        k, v, _info = pair
        return _display_name_for_instance(k, v) if isinstance(v, dict) else _name_for_key(k)
    filtered_items.sort(key=_display_name)

    total_pages = max(1, math.ceil(len(filtered_items) / ITEMS_PER_PAGE))
    current_page = min(current_page, total_pages)
    start = (current_page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    items_on_page = filtered_items[start:end]

    gold_amt = player_manager.get_gold(player_data)
    diamonds_amt = _get_diamonds_amount(player_data)
    label = CATEGORIES.get(category_key, "Inventário")
    header = (
        f"🎒 𝐈𝐧𝐯𝐞𝐧𝐭𝐚́𝐫𝐢𝐨 — {label} (Página {current_page}/{total_pages})\n"
        f"🪙 𝐎𝐮𝐫𝐨: {gold_amt:,}   💎 𝐃𝐢𝐚𝐦𝐚𝐧𝐭𝐞𝐬: {diamonds_amt}\n\n"
    )

    body_text_lines = []
    item_buttons = [] 

    if not items_on_page:
        body_text_lines.append("Nenhum item nesta categoria.")
    else:
        for item_key, item_value, item_info in items_on_page:
            if isinstance(item_value, dict):
                body_text_lines.append(f"{_render_item_line_safe(item_value)}")
            else:
                qty = int(item_value)
                emoji = item_info.get("emoji", "")
                item_name = item_info.get("display_name") or _humanize_key(item_key)
                body_text_lines.append(f"• {emoji + ' ' if emoji else ''}{item_name}: <b>{qty}</b>")
                
                # --- (LÓGICA DE BOTÃO "USAR" COM FILTRO DE CLASSE) ---
                if category_key == "consumivel":
                    on_use_data = item_info.get("on_use", {}) or {}
                    effects_data = item_info.get("effects", {}) or {}
                    
                    if "effect" in on_use_data:
                        effect_data_to_check = on_use_data
                    else:
                        effect_data_to_check = effects_data
                    
                    if effect_data_to_check: # Garante que há dados de efeito
                        can_use = True # Começa como verdadeiro
                        effect = effect_data_to_check.get("effect")
                        skill_id = effect_data_to_check.get("skill_id")
                        skin_id = effect_data_to_check.get("skin_id")

                        if effect == "grant_skill" and skill_id:
                            skill_info = skills_data.SKILL_DATA.get(skill_id, {})
                            allowed_classes = skill_info.get("allowed_classes", [])
                            
                            # Verifica a classe base
                            if not can_player_use_skill(player_class_key, allowed_classes):
                                can_use = False # Bloqueia o botão

                        elif effect == "grant_skin" and skin_id:
                            skin_info = SKIN_CATALOG.get(skin_id, {})
                            allowed_class = skin_info.get("class")
                            
                            if allowed_class and player_class_key != allowed_class:
                                can_use = False # Bloqueia o botão
                        
                        if can_use:
                            item_buttons.append([
                                InlineKeyboardButton(f"🧪 Usar {item_name}", callback_data=f"inv_use_item:{item_key}")
                            ])
                        else:
                            # Mostra o item, mas o botão está desativado
                            item_buttons.append([
                                InlineKeyboardButton(f"🚫 {item_name} (Outra Classe)", callback_data=f"noop_inventory:Outra Classe")
                            ])
                # --- Fim da lógica do botão ---

    inventory_text = header + "\n".join(body_text_lines)

    keyboard = []
    keyboard.extend(item_buttons)
    
    row_tabs = [InlineKeyboardButton(f"✅ {lbl}" if key == category_key else lbl, callback_data=f"inventory_CAT_{key}_PAGE_1") for key, lbl in CATEGORIES.items()]
    keyboard.append(row_tabs)
    
    pag_buttons = []
    if current_page > 1: pag_buttons.append(InlineKeyboardButton("◀️", callback_data=f"inventory_CAT_{category_key}_PAGE_{current_page - 1}"))
    pag_buttons.append(InlineKeyboardButton(f"- {current_page} -", callback_data="noop_inventory:Página"))
    if current_page < total_pages: pag_buttons.append(InlineKeyboardButton("▶️", callback_data=f"inventory_CAT_{category_key}_PAGE_{current_page + 1}"))
    if pag_buttons: keyboard.append(pag_buttons)

    keyboard.append([InlineKeyboardButton("🧰 𝐄𝐪𝐮𝐢𝐩𝐚𝐦𝐞𝐧𝐭𝐨𝐬", callback_data="equipment_menu")])
    keyboard.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="profile")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    # (Lógica de Envio de Mídia permanece igual)
    fd = (
        file_ids.get_file_data("img_inventario")
        or file_ids.get_file_data("inventario_img")
        or file_ids.get_file_data("inventory_img")
    )
    media_id = fd.get("id") if fd else None
    if media_id:
        try:
            media_type = (fd.get("type") or "photo").lower()
            media_input = InputMediaVideo(media=media_id, caption=inventory_text, parse_mode="HTML") if media_type == "video" else InputMediaPhoto(media=media_id, caption=inventory_text, parse_mode="HTML")
            await query.edit_message_media(media=media_input, reply_markup=reply_markup)
            return
        except Exception:
            pass 
    try:
        await query.delete_message()
    except Exception:
        pass
    if media_id:
        try:
            media_type = (fd.get("type") or "photo").lower()
            if media_type == "video":
                await context.bot.send_video(chat_id=chat_id, video=media_id, caption=inventory_text, reply_markup=reply_markup, parse_mode="HTML")
            else:
                await context.bot.send_photo(chat_id=chat_id, photo=media_id, caption=inventory_text, reply_markup=reply_markup, parse_mode="HTML")
            return
        except Exception as e:
            logger.warning(f"Falha ao enviar mídia do inventário (ID: {media_id}). Erro: {e}. Usando fallback de texto.")
    await context.bot.send_message(chat_id=chat_id, text=inventory_text, reply_markup=reply_markup, parse_mode="HTML")

# =========================================================================
# ================== INÍCIO DA FUNÇÃO CORRIGIDA (PASSO 5A) ==================
# =========================================================================

# handlers/inventory_handler.py

# ... (todo o código anterior, como inventory_callback, etc.) ...

# =========================================================================
# ================== INÍCIO DA FUNÇÃO CORRIGIDA (Contador + effect_id) ==================
# =========================================================================

async def use_item_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    (ATUALIZADO COM CONTADOR 6/12 e CORREÇÃO effect_id)
    Processa o clique no botão [Usar] do inventário.
    """
    query = update.callback_query
    user_id = query.from_user.id
    
    try:
        item_id = query.data.split(":", 1)[1]
    except IndexError:
        await query.answer("Erro: Callback de item inválido.", show_alert=True)
        return

    await query.answer(f"Tentando usar {item_id}...")
    
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await query.answer("Erro: Personagem não encontrado.", show_alert=True)
        return

    item_info = _info_for(item_id) # Pega info do game_data
    item_name = item_info.get("display_name", item_id)
    
    player_class_key = player_stats._get_class_key_normalized(player_data)
    
    effects_data = item_info.get("effects", {}) or {}
    on_use_data = item_info.get("on_use", {}) or {}
    
    if "effect" in on_use_data:
        effect_data_to_use = on_use_data
    else:
        effect_data_to_use = effects_data

    if not effect_data_to_use:
        await query.answer(f"O item '{item_name}' não tem um efeito utilizável.", show_alert=True)
        return

    # 1. Tenta consumir o item PRIMEIRO
    if not player_manager.remove_item_from_inventory(player_data, item_id, 1):
        await query.answer(f"Você não tem mais '{item_name}'!", show_alert=True)
        await inventory_callback(update, context) 
        return

    # 2. Aplica os efeitos
    feedback_msg = f"Você usou {item_name}!"
    item_foi_devolvido = False
    
    effect = effect_data_to_use.get("effect") 
    
    # --- !!! AQUI ESTÁ A CORREÇÃO !!! ---
    effect_id = effect_data_to_use.get("effect_id") # Esta linha estava faltando
    # --- FIM DA CORREÇÃO ---
    
    skill_id = effect_data_to_use.get("skill_id")
    skin_id = effect_data_to_use.get("skin_id")
    
    try:
        # --- Lógica de SKILL (MODIFICADA COM CONTADOR) ---
        if effect == "grant_skill" and skill_id:
            skill_info = skills_data.SKILL_DATA.get(skill_id, {})
            skill_name = skill_info.get("display_name", skill_id)
            allowed_classes = skill_info.get("allowed_classes", [])
            
            if not player_class_key:
                feedback_msg = "🚫 Você precisa escolher uma classe antes de aprender uma habilidade."
                player_manager.add_item_to_inventory(player_data, item_id, 1); item_foi_devolvido = True
            
            elif not can_player_use_skill(player_class_key, allowed_classes):
                feedback_msg = f"🚫 Sua classe ({player_class_key.capitalize()}) não pode aprender esta habilidade."
                player_manager.add_item_to_inventory(player_data, item_id, 1); item_foi_devolvido = True
                
            else:
                skills = player_data.setdefault("skills", {})
                if not isinstance(skills, dict):
                    logger.warning(f"use_item_callback: Migrando 'skills' (era lista) para {user_id}...")
                    new_skills_dict = {sid: {"rarity": "comum", "progress": 0} for sid in skills if sid}
                    player_data["skills"] = new_skills_dict
                    skills = new_skills_dict

                # --- LÓGICA DE FUSÃO/APRENDIZADO COM CONTADOR ---
                if skill_id not in skills:
                    # 1. APRENDER (Skill Nova)
                    skills[skill_id] = {"rarity": "comum", "progress": 0}
                    feedback_msg = f"📚 Você aprendeu a habilidade: {skill_name} (Comum)!"
                else:
                    # 2. MELHORAR (Fusão de Skill Existente)
                    current_rarity = skills[skill_id].get("rarity", "comum")
                    current_progress = skills[skill_id].get("progress", 0)
                    
                    if current_rarity == "lendaria":
                        feedback_msg = f"Você já maximizou a skill [{skill_name}] (Lendária)."
                        player_manager.add_item_to_inventory(player_data, item_id, 1); item_foi_devolvido = True
                    else:
                        cap = 0
                        next_rarity = ""
                        if current_rarity == "comum":
                            cap = 6
                            next_rarity = "epica"
                        elif current_rarity == "epica":
                            cap = 12
                            next_rarity = "lendaria"
                        
                        if cap == 0:
                            feedback_msg = f"Você já conhece esta skill ({current_rarity.capitalize()})."
                            player_manager.add_item_to_inventory(player_data, item_id, 1); item_foi_devolvido = True
                        else:
                            # Adiciona progresso
                            current_progress += 1
                            skills[skill_id]["progress"] = current_progress
                            
                            if current_progress >= cap:
                                # APRIMOROU!
                                skills[skill_id]["rarity"] = next_rarity
                                skills[skill_id]["progress"] = 0
                                feedback_msg = f"🌟 Habilidade Aprimorada! Sua skill [{skill_name}] agora é {next_rarity.capitalize()}!"
                            else:
                                # Apenas ganhou progresso
                                feedback_msg = f"✨ Progresso da Skill [{skill_name}] aumentou! ({current_progress}/{cap})"

        # --- Lógica de SKIN (Sem alteração) ---
        elif effect == "grant_skin" and skin_id:
            skin_info = SKIN_CATALOG.get(skin_id, {})
            allowed_class = skin_info.get("class") 

            if not player_class_key:
                feedback_msg = "🚫 Você precisa escolher uma classe antes de desbloquear uma aparência."
                player_manager.add_item_to_inventory(player_data, item_id, 1); item_foi_devolvido = True
            elif allowed_class and player_class_key != allowed_class:
                feedback_msg = f"🚫 Sua classe ({player_class_key.capitalize()}) não pode usar esta aparência."
                player_manager.add_item_to_inventory(player_data, item_id, 1); item_foi_devolvido = True
            else:
                skins = player_data.setdefault("unlocked_skins", [])
                if skin_id not in skins:
                    skins.append(skin_id)
                    skin_name = skin_info.get("display_name", skin_id)
                    feedback_msg = f"🎨 Você desbloqueou a aparência: {skin_name}!"
                else:
                    feedback_msg = "Você já possui esta aparência."
                    player_manager.add_item_to_inventory(player_data, item_id, 1); item_foi_devolvido = True

        # --- (Restante da função 'use_item_callback' mantida igual) ---
        elif effect == "add_pvp_entries":
            value = effect_data_to_use.get("value", 1)
            player_manager.add_pvp_entries(player_data, int(value))
            feedback_msg = f"🎟️ Você ganhou {value} entrada(s) para a Arena!"
        
        elif effect_id == "buff_hp_flat": # <--- AGORA FUNCIONA
            feedback_msg = "Este item (buff) ainda não pode ser usado fora de combate."
            player_manager.add_item_to_inventory(player_data, item_id, 1); item_foi_devolvido = True
        
        elif 'heal' in effect_data_to_use:
            heal_amount = int(effect_data_to_use['heal'])
            await player_actions.heal_player(player_data, heal_amount)
            feedback_msg = f"❤️ Você recuperou {heal_amount} HP!"
        elif 'add_energy' in effect_data_to_use:
            energy_amount = int(effect_data_to_use['add_energy'])
            player_actions.add_energy(player_data, energy_amount)
            feedback_msg = f"⚡️ Você recuperou {energy_amount} de Energia!"
        elif 'add_mana' in effect_data_to_use: 
            mana_amount = int(effect_data_to_use['add_mana'])
            await player_actions.add_mana(player_data, mana_amount)
            feedback_msg = f"💙 Você recuperou {mana_amount} de Mana!"
        elif 'add_xp' in effect_data_to_use:
            xp_amount = int(effect_data_to_use['add_xp'])
            player_data['xp'] = player_data.get('xp', 0) + xp_amount
            _n, _p, level_up_msg = player_manager.check_and_apply_level_up(player_data)
            feedback_msg = f"🧠 Você ganhou {xp_amount} XP!"
            if level_up_msg: feedback_msg += f"\n\n{level_up_msg}"
        else:
            feedback_msg = f"O item '{item_name}' não tem um efeito utilizável fora de combate."
            if not item_foi_devolvido:
                player_manager.add_item_to_inventory(player_data, item_id, 1) # Devolve

    except Exception as e:
        logger.error(f"Erro ao aplicar on_use_effect para {item_id} (user {user_id}): {e}", exc_info=True)
        feedback_msg = f"Ocorreu um erro ao usar o item: {e}"
        if not item_foi_devolvido:
            player_manager.add_item_to_inventory(player_data, item_id, 1) # Devolve
    
    # 3. Salva os dados
    await player_manager.save_player_data(user_id, player_data)
    await query.answer(feedback_msg, show_alert=True)
    
    # 4. Recarrega o menu do inventário (para mostrar a nova quantidade)
    await inventory_callback(update, context)


# =========================================================================
# ================== FIM DA FUNÇÃO CORRIGIDA ===================
# =========================================================================

async def noop_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        reason = query.data.split(":", 1)[1]
        if reason == "Outra Classe":
            await query.answer("🚫 Você não pode usar este item (outra classe).", show_alert=True)
        else:
            await query.answer() 
    except IndexError:
        await query.answer() 
        
noop_inventory_handler = CallbackQueryHandler(noop_inventory, pattern=r'^noop_inventory') 
inventory_handler = CallbackQueryHandler(inventory_callback, pattern=r'^inventory_CAT_[A-Za-z0-9_]+_PAGE_[0-9]+$')
use_item_handler = CallbackQueryHandler(use_item_callback, pattern=r'^inv_use_item:')