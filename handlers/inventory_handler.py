# handlers/inventory_handler.py

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
    """Une ITEMS_DATA e ITEM_BASES (fallback)."""
    if not key:
        return {}
    data = getattr(game_data, "ITEMS_DATA", {}).get(key, {}) or {}
    base = getattr(game_data, "ITEM_BASES", {}).get(key, {}) or {}
    info = {}
    info.update(base)
    info.update(data)
    return info

def _humanize_key(key: str) -> str:
    """barra_de_ferro -> Barra de Ferro (com preposições minúsculas)."""
    if not key:
        return ""
    words = key.replace("_", " ").strip().split()
    if not words:
        return key
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
    """Usa o formatter novo universal da UI de itens."""
    try:
        return display_utils.formatar_item_para_exibicao(inst)
    except Exception:
        return _display_name_for_instance("", inst)

def _extract_raw_category(item_info: dict) -> str:
    """Extrai categoria crua de vários campos comuns nos dados."""
    keys_in_order = ["category", "type", "tipo", "group", "grupo", "origin", "origem", "item_category"]
    for k in keys_in_order:
        v = (item_info.get(k) or "")
        if isinstance(v, str) and v.strip():
            return v.strip().lower()

    tags = item_info.get("tags") or item_info.get("etiquetas") or []
    if isinstance(tags, (list, tuple)):
        lowered = [str(t).strip().lower() for t in tags]
        for needle in ("cacada", "caça", "hunt", "hunting"):
            if needle in lowered:
                return "cacada"
        for needle in ("consumivel", "consumível", "potion"):
            if needle in lowered:
                return "consumivel"
        for needle in ("material", "material_refinado", "recurso", "coletavel", "coletável"):
            if needle in lowered:
                return "coletavel"
        for needle in ("chave", "especial", "equipamento", "event_ticket"):
            if needle in lowered:
                return "especial"
    return ""

def _guess_tab_by_key(item_key: str) -> str:
    k = (item_key or "").lower()
    if any(h in k for h in _HUNT_NAME_HINTS):
        return "cacada"
    if any(h in k for h in _SPECIAL_NAME_HINTS):
        return "especial"
    if any(h in k for h in _COLLECT_NAME_HINTS):
        return "coletavel"
    return "coletavel"  

def _item_tab_for(item_info: dict, item_key: str, item_value) -> str:
    raw = _extract_raw_category(item_info)
    
    # Mapeamento direto
    if raw:
        mapped = ITEM_CAT_TO_TAB.get(raw)
        if mapped in CATEGORIES:
            return mapped

    # Heurística por nome de chave (quando não há dados)
    hint = _guess_tab_by_key(item_key)
    if hint in CATEGORIES:
        return hint

    # Heurística por 'type'
    t = (item_info.get("type") or item_info.get("tipo") or "").lower()
    if t in ("material", "material_bruto", "material_refinado", "recurso", "coletavel", "coletável"):
        return "coletavel"

    # Fallback final
    return "especial" if isinstance(item_value, dict) else "coletavel"

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except Exception as e:
        if "message is not modified" in str(e).lower(): return # (NOVO) Ignora erro "não modificado"
        pass
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except Exception as e:
        if "message is not modified" in str(e).lower(): return # (NOVO) Ignora erro "não modificado"
        pass
    try:
        await query.delete_message()
    except Exception:
        pass
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

# ---- Compat helpers (diamantes + cristais legados) -------------------------

def _get_diamonds_amount(player_data: dict) -> int:
    for fn_name in ("get_diamonds", "get_gems"):
        if hasattr(player_manager, fn_name):
            try:
                val = getattr(player_manager, fn_name)(player_data)
                return int(val or 0)
            except Exception:
                pass
    for k in ("diamonds", "gems", "gemas", "dimas", "diamantes"):
        try:
            if k in player_data:
                return int(player_data.get(k, 0) or 0)
        except Exception:
            continue
    return 0

def _merge_legacy_crystals_view(inventory: dict, player_data: dict) -> dict:
    inv = dict(inventory or {})
    legacy_keys = ("cristal_de_abertura", "cristal_abertura")
    for k in legacy_keys:
        try:
            legacy_val = int(player_data.get(k, 0) or 0)
        except Exception:
            legacy_val = 0
        if legacy_val > 0 and k not in inv:
            inv[k] = legacy_val
    return inv

async def inventory_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    (ATUALIZADO) Inventário com abas + paginação E botões de "Usar".
    """
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    chat_id = query.message.chat.id

    await _auto_finalize_safe(user_id, context)

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        try:
            await query.edit_message_text("Não encontrei seus dados. Use /start para começar.")
        except Exception:
            await context.bot.send_message(chat_id=chat_id, text="Não encontrei seus dados. Use /start para começar.")
        return

    m = re.match(r"^inventory_CAT_([A-Za-z0-9_]+)_PAGE_([0-9]+)$", (query.data or ""))
    if not m:
        await query.answer("Requisição inválida.", show_alert=True)
        return

    category_key = _sanitize_category(m.group(1))
    current_page = max(1, int(m.group(2) or 1))

    raw_inventory = player_data.get("inventory", {}) or {}
    inventory = _merge_legacy_crystals_view(raw_inventory, player_data)
    equipped_uids = {v for v in (player_data.get("equipment", {}) or {}).values() if isinstance(v, str) and v}

    # 1) Filtra por aba
    filtered_items = []
    for item_key, item_value in inventory.items():
        if item_key in {"ouro", "gold"}:
            continue

        if isinstance(item_value, dict):
            if item_key in equipped_uids:
                continue
            base_id = item_value.get("base_id")
            item_info = _info_for(base_id)
            tab = _item_tab_for(item_info, base_id or item_key, item_value)
            key_for_name = base_id or item_key
        else:
            item_info = _info_for(item_key)
            tab = _item_tab_for(item_info, item_key, item_value)
            key_for_name = item_key

        if tab == category_key:
            filtered_items.append((key_for_name, item_value, item_info)) # (NOVO) Adiciona info

    # Ordena por nome de exibição
    def _display_name(pair):
        k, v, _info = pair
        return _display_name_for_instance(k, v) if isinstance(v, dict) else _name_for_key(k)
    filtered_items.sort(key=_display_name)

    # 2) Paginação
    total_pages = max(1, math.ceil(len(filtered_items) / ITEMS_PER_PAGE))
    current_page = min(current_page, total_pages)
    start = (current_page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    items_on_page = filtered_items[start:end]

    # 3) Texto (header)
    gold_amt = player_manager.get_gold(player_data)
    diamonds_amt = _get_diamonds_amount(player_data)
    label = CATEGORIES.get(category_key, "Inventário")
    header = (
        f"🎒 𝐈𝐧𝐯𝐞𝐧𝐭𝐚́𝐫𝐢𝐨 — {label} (Página {current_page}/{total_pages})\n"
        f"🪙 𝐎𝐮𝐫𝐨: {gold_amt:,}   💎 𝐃𝐢𝐚𝐦𝐚𝐧𝐭𝐞𝐬: {diamonds_amt}\n\n"
    )

    # 4) (NOVO) Corpo do texto E Botões de Itens
    body_text_lines = []
    item_buttons = [] # Lista para os botões [Usar]

    if not items_on_page:
        body_text_lines.append("Nenhum item nesta categoria.")
    else:
        for item_key, item_value, item_info in items_on_page:
            if isinstance(item_value, dict):
                # Item único (equipamento)
                body_text_lines.append(f"{_render_item_line_safe(item_value)}")
            else:
                # Item empilhável
                qty = int(item_value)
                emoji = item_info.get("emoji", "")
                item_name = item_info.get("display_name") or _humanize_key(item_key)
                body_text_lines.append(f"• {emoji + ' ' if emoji else ''}{item_name}: <b>{qty}</b>")
                
                # --- (LÓGICA DO BOTÃO "USAR") ---
                # Verifica se o item é consumível (pela aba) E se tem um efeito
                on_use_data = item_info.get("on_use")
                effects_data = item_info.get("effects") # Para poções antigas
                
                if category_key == "consumivel" and (on_use_data or effects_data):
                    item_buttons.append([
                        InlineKeyboardButton(f"🧪 Usar {item_name}", callback_data=f"inv_use_item:{item_key}")
                    ])
                # --- Fim da lógica do botão ---

    inventory_text = header + "\n".join(body_text_lines)

    # 5) Teclado (Combinado)
    keyboard = []
    
    # Adiciona os botões de [Usar] primeiro
    keyboard.extend(item_buttons)
    
    # Abas
    row_tabs = [InlineKeyboardButton(f"✅ {lbl}" if key == category_key else lbl, callback_data=f"inventory_CAT_{key}_PAGE_1") for key, lbl in CATEGORIES.items()]
    keyboard.append(row_tabs)
    
    # Paginação
    pag_buttons = []
    if current_page > 1: pag_buttons.append(InlineKeyboardButton("◀️", callback_data=f"inventory_CAT_{category_key}_PAGE_{current_page - 1}"))
    pag_buttons.append(InlineKeyboardButton(f"- {current_page} -", callback_data="noop_inventory"))
    if current_page < total_pages: pag_buttons.append(InlineKeyboardButton("▶️", callback_data=f"inventory_CAT_{category_key}_PAGE_{current_page + 1}"))
    if pag_buttons: keyboard.append(pag_buttons)

    keyboard.append([InlineKeyboardButton("🧰 𝐄𝐪𝐮𝐢𝐩𝐚𝐦𝐞𝐧𝐭𝐨𝐬", callback_data="equipment_menu")])
    keyboard.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="profile")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    # =========================================================
    # LÓGICA DE ENVIO ROBUSTA (PLANO A, B e C)
    # =========================================================
    fd = (
        file_ids.get_file_data("img_inventario")
        or file_ids.get_file_data("inventario_img")
        or file_ids.get_file_data("inventory_img")
    )
    media_id = fd.get("id") if fd else None

    # --- PLANO A: Tentar editar a mídia (se a mensagem já for uma mídia) ---
    if media_id:
        try:
            media_type = (fd.get("type") or "photo").lower()
            media_input = InputMediaVideo(media=media_id, caption=inventory_text, parse_mode="HTML") if media_type == "video" else InputMediaPhoto(media=media_id, caption=inventory_text, parse_mode="HTML")
            await query.edit_message_media(media=media_input, reply_markup=reply_markup)
            return  # Sucesso!
        except Exception:
            pass  # Se falhar, tentará o Plano B.

    # --- PLANO B: Apagar a mensagem antiga e enviar uma nova ---
    try:
        await query.delete_message()
    except Exception:
        pass
    
    # PLANO B.1: Tentar enviar nova mensagem COM mídia
    if media_id:
        try:
            media_type = (fd.get("type") or "photo").lower()
            if media_type == "video":
                await context.bot.send_video(chat_id=chat_id, video=media_id, caption=inventory_text, reply_markup=reply_markup, parse_mode="HTML")
            else:
                await context.bot.send_photo(chat_id=chat_id, photo=media_id, caption=inventory_text, reply_markup=reply_markup, parse_mode="HTML")
            return # Sucesso!
        except Exception as e:
            logger.warning(f"Falha ao enviar mídia do inventário (ID: {media_id}). Erro: {e}. Usando fallback de texto.")
            # Se falhar, continua para o Plano C.

    # --- PLANO C: Fallback final para mensagem de texto simples ---
    # Só executa se não houver mídia ou se todos os planos anteriores falharem.
    await context.bot.send_message(chat_id=chat_id, text=inventory_text, reply_markup=reply_markup, parse_mode="HTML")    # Ordena por nome de exibição
    def _display_name(pair):
        k, v = pair
        if isinstance(v, dict):
            return _display_name_for_instance(k, v)
        return _name_for_key(k)

    filtered_items.sort(key=_display_name)

    # 2) Paginação
    total_pages = max(1, math.ceil(len(filtered_items) / ITEMS_PER_PAGE))
    current_page = min(current_page, total_pages)
    start = (current_page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    items_on_page = filtered_items[start:end]

    # 3) Texto (inclui ouro + diamantes)
    gold_amt = player_manager.get_gold(player_data) if hasattr(player_manager, "get_gold") \
               else int(player_data.get("gold", 0))
    diamonds_amt = _get_diamonds_amount(player_data)

    label = CATEGORIES.get(category_key, "Inventário")
    header = (
        f"🎒 𝐈𝐧𝐯𝐞𝐧𝐭𝐚́𝐫𝐢𝐨 — {label} "
        f"(Página {current_page}/{total_pages})\n"
        f"🪙 𝐎𝐮𝐫𝐨: {gold_amt}    💎 𝐃𝐢𝐚𝐦𝐚𝐧𝐭𝐞𝐬: {diamonds_amt}\n\n"
    )

    # 4) Corpo da lista
    body_text = ""
    if not items_on_page:
        body_text = "Nenhum item nesta categoria."
    else:
        for item_key, item_value in items_on_page:
            if isinstance(item_value, dict):
                # Instância única (render bonito)
                body_text += f"{_render_item_line_safe(item_value)}\n"
            else:
                # Empilhável
                qty = int(item_value)
                info = _info_for(item_key)
                emoji = info.get("emoji", "")
                item_name = info.get("display_name") or _humanize_key(item_key)
                body_text += f"• {emoji + ' ' if emoji else ''}{item_name}: <b>{qty}</b>\n"

    inventory_text = header + body_text

    # 5) Teclado
    keyboard = []

    # Abas
    row = []
    for key, tab_label in CATEGORIES.items():
        text = f"✅ {tab_label}" if key == category_key else tab_label
        row.append(InlineKeyboardButton(text, callback_data=f"inventory_CAT_{key}_PAGE_1"))
    keyboard.append(row)

    # Paginação
    pag = []
    if current_page > 1:
        pag.append(InlineKeyboardButton("◀️", callback_data=f"inventory_CAT_{category_key}_PAGE_{current_page - 1}"))
    pag.append(InlineKeyboardButton(f"- {current_page} -", callback_data="noop_inventory"))
    if current_page < total_pages:
        pag.append(InlineKeyboardButton("▶️", callback_data=f"inventory_CAT_{category_key}_PAGE_{current_page + 1}"))
    keyboard.append(pag)

    # atalhos
    keyboard.append([InlineKeyboardButton("🧰 𝐄𝐪𝐮𝐢𝐩𝐚𝐦𝐞𝐧𝐭𝐨𝐬", callback_data="equipment_menu")])
    keyboard.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="profile")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # 6) Mídia do inventário
    fd = (
        file_ids.get_file_data("img_inventario")
        or file_ids.get_file_data("inventario_img")
        or file_ids.get_file_data("inventory_img")
    )

    if fd and fd.get("id"):
        media_id = fd["id"]
        media_type = (fd.get("type") or "photo").lower()
        try:
            if media_type == "video":
                await query.edit_message_media(
                    media=InputMediaVideo(media=media_id, caption=inventory_text, parse_mode="HTML"),
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_media(
                    media=InputMediaPhoto(media=media_id, caption=inventory_text, parse_mode="HTML"),
                    reply_markup=reply_markup
                )
            return
        except Exception:
            try:
                await query.delete_message()
            except Exception:
                pass

            if media_type == "video":
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=media_id,
                    caption=inventory_text,
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )
            else:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=media_id,
                    caption=inventory_text,
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )
            return

    # 7) Fallback (sem mídia)
    await _safe_edit_or_send(query, context, chat_id, inventory_text, reply_markup=reply_markup, parse_mode="HTML")

async def use_item_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Processa o clique no botão [Usar] do inventário.
    Lê o 'on_use' ou 'effects' do game_data/items.py e aplica o efeito.
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
    
    # Combina os dois tipos de blocos de efeito (on_use e effects)
    effects_data = item_info.get("effects", {}) or {}
    on_use_data = item_info.get("on_use", {}) or {}
    
    # Se 'on_use' tiver um 'effect' (ex: grant_skill), usa ele.
    # Se não, usa o 'effects' (ex: heal).
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
        await inventory_callback(update, context) # Recarrega o inventário
        return

    # 2. Aplica os efeitos
    feedback_msg = f"Você usou {item_name}!" # Mensagem padrão
    item_foi_devolvido = False
    
    # Pega os efeitos de dentro do bloco
    effect = effect_data_to_use.get("effect") # Para grant_skill, etc.
    effect_id = effect_data_to_use.get("effect_id") # Para seiva_escura
    
    skill_id = effect_data_to_use.get("skill_id")
    skin_id = effect_data_to_use.get("skin_id")
    
    try:
        # --- Lógica de SKILL (NOVO) ---
        if effect == "grant_skill" and skill_id:
            skills = player_data.setdefault("skills", [])
            if skill_id not in skills:
                skills.append(skill_id)
                skill_name = skills_data.SKILL_DATA.get(skill_id, {}).get("display_name", skill_id)
                feedback_msg = f"📚 Você aprendeu a habilidade: {skill_name}!"
            else:
                feedback_msg = "Você já conhece esta habilidade."
                player_manager.add_item_to_inventory(player_data, item_id, 1) # Devolve o item
                item_foi_devolvido = True

        # --- Lógica de SKIN (NOVO) ---
        elif effect == "grant_skin" and skin_id:
            skins = player_data.setdefault("unlocked_skins", [])
            if skin_id not in skins:
                skins.append(skin_id)
                skin_name = SKIN_CATALOG.get(skin_id, {}).get("display_name", skin_id)
                feedback_msg = f"🎨 Você desbloqueou a aparência: {skin_name}!"
            else:
                feedback_msg = "Você já possui esta aparência."
                player_manager.add_item_to_inventory(player_data, item_id, 1) # Devolve o item
                item_foi_devolvido = True

        # --- Lógica de TICKET DE ARENA (do items.py) ---
        elif effect == "add_pvp_entries":
            value = effect_data_to_use.get("value", 1)
            player_manager.add_pvp_entries(player_data, int(value))
            feedback_msg = f"🎟️ Você ganhou {value} entrada(s) para a Arena!"
        
        # --- Lógica de BUFF (do items.py) ---
        elif effect_id == "buff_hp_flat":
            # (Esta lógica de buff é simples, se for complexa, precisa do player_actions)
            feedback_msg = "Este item (buff) ainda não pode ser usado fora de combate."
            player_manager.add_item_to_inventory(player_data, item_id, 1) # Devolve
            item_foi_devolvido = True

        # --- Lógica de POÇÕES (Copiada do combat_handler) ---
        elif 'heal' in effect_data_to_use:
            heal_amount = int(effect_data_to_use['heal'])
            await player_actions.heal_player(player_data, heal_amount)
            feedback_msg = f"❤️ Você recuperou {heal_amount} HP!"
        
        elif 'add_energy' in effect_data_to_use:
             energy_amount = int(effect_data_to_use['add_energy'])
             player_actions.add_energy(player_data, energy_amount)
             feedback_msg = f"⚡️ Você recuperou {energy_amount} de Energia!"
        
        elif 'add_mana' in effect_data_to_use: # (Adicionado para poções de mana)
             mana_amount = int(effect_data_to_use['add_mana'])
             await player_actions.add_mana(player_data, mana_amount)
             feedback_msg = f"💙 Você recuperou {mana_amount} de Mana!"

        elif 'add_xp' in effect_data_to_use:
             xp_amount = int(effect_data_to_use['add_xp'])
             player_data['xp'] = player_data.get('xp', 0) + xp_amount
             _n, _p, level_up_msg = player_manager.check_and_apply_level_up(player_data)
             feedback_msg = f"🧠 Você ganhou {xp_amount} XP!"
             if level_up_msg: feedback_msg += f"\n\n{level_up_msg}"
        
        # --- Fallback ---
        else:
            feedback_msg = f"O item '{item_name}' não tem um efeito utilizável fora de combate."
            if not item_foi_devolvido: # Evita devolver duas vezes
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

# ---------------------------------------------------------------------------


# Handler principal
inventory_handler = CallbackQueryHandler(inventory_callback, pattern=r'^inventory_CAT_[A-Za-z0-9_]+_PAGE_[0-9]+$')

# No-op para o botão central
async def noop_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()