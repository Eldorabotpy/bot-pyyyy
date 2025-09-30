import logging
from typing import List, Tuple

from telegram import Update, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, InputMediaPhoto
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.helpers import escape_markdown

from modules import mission_manager
# Motores e dados
from modules import player_manager, game_data, crafting_engine, crafting_registry
from modules import file_ids
from modules import clan_manager

logger = logging.getLogger(__name__)

# --- DISPLAY UTILS (sem alterações) ---
try:
    from modules import display_utils
except Exception:
    class _DisplayFallback:
        @staticmethod
        def formatar_item_para_exibicao(item_criado: dict) -> str:
            emoji = item_criado.get("emoji", "🛠")
            name = item_criado.get("display_name", item_criado.get("name", "Item"))
            rarity = item_criado.get("rarity", "")
            extra = []
            for k, v in item_criado.items():
                if k in {"emoji", "display_name", "name", "rarity"}:
                    continue
                extra.append(f"{k}={v}")
            extra_str = ", ".join(extra) if extra else ""
            if rarity:
                name = f"{name} [{rarity}]"
            return f"{emoji} *{name}*{(' — ' + extra_str) if extra_str else ''}"
    display_utils = _DisplayFallback()

# =====================================================
# Helpers
# =====================================================

def _get_media_key_for_item(item_id: str) -> str:
    """
    Busca a 'media_key' nos dados de um item.
    Se não encontrar, retorna o próprio item_id como fallback.
    """
    if not item_id:
        return ""
    
    items_data = getattr(game_data, "ITEMS_DATA", {}) or {}
    item_info = items_data.get(item_id)
    
    if item_info and (media_key := item_info.get("media_key")):
        return media_key
    
    return item_id


def _get_image_source(item_key: str) -> str:
    if not item_key: return getattr(game_data, "ITEM_IMAGES", {}).get("fallback", "")
    registered_id = file_ids.get_file_id(item_key)
    if registered_id:
        return registered_id
    fallback_source = getattr(game_data, "ITEM_IMAGES", {}).get(item_key)
    if fallback_source:
        return fallback_source
    return getattr(game_data, "ITEM_IMAGES", {}).get("fallback", "")


def _md_escape_v1(text: str) -> str:
    return escape_markdown(text, version=1)

async def _send_or_edit_photo(
    query: CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
    photo_source: str,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None
):
    try:
        photo_input = InputFile(photo_source) if isinstance(photo_source, str) and photo_source.startswith(('assets/', './')) else photo_source
        if query.message.photo:
            await query.edit_message_media(media=InputMediaPhoto(media=photo_input), reply_markup=reply_markup)
            await query.edit_message_caption(caption=caption, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await query.message.delete()
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=photo_input,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error("Falha ao enviar/editar foto: %s. Usando fallback de texto.", e)
        try:
            await query.edit_message_text(text=caption, reply_markup=reply_markup, parse_mode="Markdown")
        except Exception as inner_e:
            logger.warning("Falha no fallback de texto: %s", inner_e)
            if query.message:
                 await query.message.reply_text(text=caption, reply_markup=reply_markup, parse_mode="Markdown")

def _pretty_item_name(item_id: str) -> str:
    info = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(item_id) or {}
    name = (info.get("display_name") or getattr(game_data, "item_display_name", lambda x: None)(item_id) or item_id.replace("_", " ").title())
    emoji = info.get("emoji", "")
    full = f"{emoji} {name}" if emoji else name
    return _md_escape_v1(full)

def _fmt_need_line(item_id: str, have: int, need: int) -> str:
    mark = "✅" if have >= need else "❌"
    return f"{mark} `{have}/{need}` {_pretty_item_name(item_id)}"

# =====================================================
# UI — Menus
# =====================================================

async def show_forge_professions_menu(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    # (Esta função não precisa de alterações)
    user_id = query.from_user.id
    player_data = player_manager.get_player_data(user_id)
    profession_info = "Você ainda não escolheu uma profissão de criação."
    player_prof = player_data.get("profession")
    if player_prof and (prof_id := player_prof.get("type")):
        prof_data = (getattr(game_data, "PROFESSIONS_DATA", {}) or {}).get(prof_id, {})
        if prof_data.get("category") == "crafting":
            prof_level = player_prof.get("level", 1)
            prof_display_name = prof_data.get("display_name", prof_id.capitalize())
            safe_display_name = _md_escape_v1(prof_display_name)
            profession_info = f"Sua Profissão Ativa: *{safe_display_name} (Nível {prof_level})*"
    keyboard = [[InlineKeyboardButton("🛠️ 𝐀𝐩𝐫𝐢𝐦𝐨𝐫𝐚𝐫 & 𝐃𝐮𝐫𝐚𝐛𝐢𝐥𝐢𝐝𝐚𝐝𝐞", callback_data="enhance_menu")]]
    row = []
    for prof_id, prof_data in (getattr(game_data, "PROFESSIONS_DATA", {}) or {}).items():
        if prof_data.get("category") == "crafting":
            display_name = prof_data.get("display_name", prof_id.capitalize())
            row.append(InlineKeyboardButton(display_name, callback_data=f"forge:prof:{prof_id}:1"))
            if len(row) == 2:
                keyboard.append(row); row = []
    if row: keyboard.append(row)
    keyboard.append([InlineKeyboardButton("↩️ 𝐕𝐨𝐥𝐭𝐚𝐫 𝐚𝐨 𝐑𝐞𝐢𝐧𝐨", callback_data="show_kingdom_menu")])
    text = (f"{profession_info}\n\n" "🔥 *Forja de Eldora*\nEscolha uma opção:")
    photo_source = _get_image_source("menu_forja_principal")
    await _send_or_edit_photo(query, context, photo_source, text, InlineKeyboardMarkup(keyboard))

async def show_profession_recipes_menu(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, profession_id: str, page: int):
    # (Esta função não precisa de alterações)
    user_id = query.from_user.id
    player_data = player_manager.get_player_data(user_id)
    player_prof = (player_data or {}).get("profession", {}) or {}
    player_prof_type = player_prof.get("type")
    player_prof_level = int(player_prof.get("level", 1))
    available = []
    if player_prof_type == profession_id:
        for recipe_id, recipe_data in crafting_registry.all_recipes().items():
            if (recipe_data.get("profession") == profession_id and player_prof_level >= int(recipe_data.get("level_req", 1))):
                available.append((recipe_id, recipe_data))
    available.sort(key=lambda it: it[1].get("level_req", 1))
    items_per_page = 5
    start, end = (page - 1) * items_per_page, page * items_per_page
    slice_recipes = available[start:end]
    keyboard = []
    for recipe_id, recipe_data in slice_recipes:
        emoji = recipe_data.get("emoji", "🔧")
        display_name = recipe_data.get("display_name", "Receita")
        keyboard.append([InlineKeyboardButton(f"{emoji} {display_name}", callback_data=f"forge:recipe:{recipe_id}")])
    nav = []
    if page > 1: nav.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"forge:prof:{profession_id}:{page-1}"))
    nav.append(InlineKeyboardButton("↩️ Voltar", callback_data="forge:main"))
    if end < len(available): nav.append(InlineKeyboardButton("Próxima ➡️", callback_data=f"forge:prof:{profession_id}:{page+1}"))
    if nav: keyboard.append(nav)
    profession_name = (getattr(game_data, "PROFESSIONS_DATA", {}) or {}).get(profession_id, {}).get("display_name", "Desconhecida")
    safe_profession_name = _md_escape_v1(profession_name)
    if not available:
        text = (f"🔥 *Forja — Receitas de {safe_profession_name}*\n\n"
                "Você ainda não aprendeu receitas desta profissão, "
                "sua profissão ativa é outra, ou seu nível é insuficiente.")
        keyboard = [[InlineKeyboardButton("↩️ Voltar", callback_data="forge:main")]]
    else:
        text = f"🔥 *Forja — Receitas de {safe_profession_name} (Pág. {page})*\n\nEscolha um item para forjar:"
    try:
        await query.edit_message_caption(caption=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception:
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def show_recipe_preview(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, recipe_id: str):
    user_id = query.from_user.id
    player_data = player_manager.get_player_data(user_id)
    recipe_data = crafting_registry.get_recipe(recipe_id)
    if not recipe_data:
        await query.answer("Receita não encontrada.", show_alert=True); return
    preview = crafting_engine.preview_craft(recipe_id, player_data)
    if not preview:
        await query.answer("Erro ao pré-visualizar a receita.", show_alert=True); return
    display_name = _md_escape_v1(preview.get("display_name", "Item"))
    minutes = int(preview.get("duration_seconds", 0)) // 60
    lines = [f"🔥 *Forja - Confirmar Criação*", "",
             f"Item: *{preview.get('emoji','🛠')} {display_name}*",
             f"Tempo: *{minutes} minutos*", "",
             "Materiais Necessários:"]
    inv = player_data.get("inventory", {}) or {}
    inputs = preview.get("inputs") or {}
    for item_id, need in inputs.items():
        have = inv.get(item_id, {}).get("quantity", 0) if isinstance(inv.get(item_id), dict) else inv.get(item_id, 0)
        lines.append(_fmt_need_line(item_id, int(have), int(need)))
    text = "\n".join(lines)
    keyboard = []
    back_btn = InlineKeyboardButton("↩️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data=f"forge:prof:{recipe_data.get('profession')}:{1}")
    if preview.get("can_craft"):
        keyboard.append([back_btn, InlineKeyboardButton("🔨 𝐅𝐨𝐫𝐣𝐚𝐫 𝐈𝐭𝐞𝐦", callback_data=f"forge:confirm:{recipe_id}")])
    else:
        keyboard.append([back_btn])
        text += "\n\n*Você não possui os materiais ou a profissão/nível necessários.*"
    
    # ## CORREÇÃO: Aplicando a lógica da media_key que você sugeriu.
    output_item_id = recipe_data.get("output_item_id") or recipe_data.get("result_base_id") or recipe_id
    image_key = _get_media_key_for_item(output_item_id)
    photo_source = _get_image_source(image_key)
    
    await _send_or_edit_photo(query, context, photo_source, text, InlineKeyboardMarkup(keyboard))

# =====================================================
# Craft — início e término
# =====================================================

async def confirm_craft_start(query: CallbackQuery, recipe_id: str, context: ContextTypes.DEFAULT_TYPE):
    # (Esta função não precisa de alterações)
    user_id = query.from_user.id
    result = crafting_engine.start_craft(user_id, recipe_id)
    if isinstance(result, str):
        await query.answer(result, show_alert=True); return
    duration = int(result.get("duration_seconds", 0))
    context.job_queue.run_once(finish_craft_notification_job, duration, chat_id=query.message.chat.id, user_id=user_id, name=f"craft_{user_id}_{recipe_id}")
    recipe_name = crafting_registry.get_recipe(recipe_id).get("display_name", "item")
    text = (f"🔥 *Forja Iniciada!*\n\n"
            f"Seu(sua) *{_md_escape_v1(recipe_name)}* está sendo forjado.\n"
            f"Ele ficará pronto em *{duration // 60} minutos*.")
    try:
        await query.edit_message_caption(caption=text, reply_markup=None, parse_mode="Markdown")
    except Exception:
        await query.edit_message_text(text=text, reply_markup=None, parse_mode="Markdown")

async def finish_craft_notification_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job; user_id = job.user_id; chat_id = job.chat_id
    result = crafting_engine.finish_craft(user_id)
    
    if not isinstance(result, dict):
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Erro ao finalizar forja: {getattr(result,'error', result)}"); return
    
    item_criado = result.get("item_criado")
    if not isinstance(item_criado, dict):
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Forja finalizada, mas item inválido."); return
    
    player_data = player_manager.get_player_data(user_id)
    if player_data and (base_id := item_criado.get("base_id")):
        player_data["user_id"] = user_id
        
        # Atualiza a missão pessoal (código que você já tinha)
        mission_manager.update_mission_progress(player_data, event_type="CRAFT", details={"item_id": base_id, "quantity": 1})
        
        # ==========================================================
        # ## INÍCIO DA CORREÇÃO: AVISAR O CLÃ SOBRE O ITEM CRIADO ##
        # ==========================================================
        clan_id = player_data.get("clan_id")
        if clan_id:
            mission_details = {
                "item_id": base_id, 
                "quantity": 1, 
                "recipe_id": result.get("recipe_id") # Passa também o ID da receita
            }
            clan_manager.update_guild_mission_progress(clan_id=clan_id, mission_type='CRAFT', details=mission_details)
        # ==========================================================
        # ## FIM DA CORREÇÃO ##
        # ==========================================================

        player_manager.save_player_data(user_id, player_data)
    
    item_txt = display_utils.formatar_item_para_exibicao(item_criado)
    text = f"✨ *Forja Concluída!*\n\nVocê obteve:\n{item_txt}"
    
    base_id = item_criado.get("base_id")
    image_key = _get_media_key_for_item(base_id)
    photo_source = _get_image_source(image_key)
    
    back_to_forge_button = InlineKeyboardButton(
        "↩️ Voltar para a Forja", 
        callback_data="forge:main"
    )
    reply_markup = InlineKeyboardMarkup([[back_to_forge_button]])

    try:
        photo_input = InputFile(photo_source) if isinstance(photo_source, str) and photo_source.startswith(('assets/', './')) else photo_source
        await context.bot.send_photo(
            chat_id=chat_id, 
            photo=photo_input, 
            caption=text, 
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error("Falha ao enviar foto de item criado: %s. Enviando texto.", e)
        await context.bot.send_message(
            chat_id=chat_id, 
            text=text, 
            parse_mode="Markdown",
            reply_markup=reply_markup
        )        
# =====================================================
# Roteador principal
# =====================================================

async def forge_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # (Esta função não precisa de alterações)
    query = update.callback_query
    await query.answer()
    data = (query.data or "").strip()
    parts = data.split(":")
    action = parts[1] if len(parts) > 1 else None
    if not action or (action in {"prof", "recipe", "confirm"} and len(parts) < 3):
        try:
            await query.edit_message_text("❌ Ação ou ID da forja ausente.")
        except: pass
        return
    try:
        if action == "main":
            await show_forge_professions_menu(query, context)
        elif action == "prof":
            prof_id = parts[2]
            page = int(parts[3]) if len(parts) > 3 else 1
            await show_profession_recipes_menu(query, context, prof_id, page)
        elif action == "recipe":
            recipe_id = parts[2]
            await show_recipe_preview(query, context, recipe_id)
        elif action == "confirm":
            recipe_id = parts[2]
            await confirm_craft_start(query, recipe_id, context)
        else:
            await query.edit_message_text("❌ Ação da forja desconhecida.")
    except Exception as e:
        logger.error("Erro no roteador da forja: %s", e, exc_info=True)
        try:
            await query.edit_message_text("❌ Ocorreu um erro na forja.")
        except Exception as inner_e:
            logger.warning("Falha ao editar mensagem de erro no roteador: %s", inner_e)

# =====================================================
# Registro do handler
# =====================================================
forge_handler = CallbackQueryHandler(forge_callback_router, pattern=r"^forge:")