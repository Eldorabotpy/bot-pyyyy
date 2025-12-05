# handlers/forge_handler.py
# (VERSÃO FINAL: Com animação de forja e limpeza de chat)

import logging
from typing import List, Tuple

from telegram import (
    Update,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
    InputMediaPhoto,
)
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.helpers import escape_markdown

# --- Módulos do Jogo ---
from modules import (
    player_manager,
    game_data,
    crafting_engine,
    crafting_registry,
    file_ids,
)

logger = logging.getLogger(__name__)

# --- Fallback de Display Utils ---
try:
    from modules.display_utils import formatar_item_para_exibicao
except (ImportError, AttributeError):
    def formatar_item_para_exibicao(item_criado: dict) -> str:
        emoji = item_criado.get("emoji", "🛠")
        name = item_criado.get("display_name", item_criado.get("name", "Item"))
        rarity = item_criado.get("rarity", "")
        if rarity:
            name = f"{name} [{rarity}]"
        return f"{emoji} *{name}*"

# =====================================================
# Funções Auxiliares (Helpers)
# =====================================================

def _get_media_key_for_item(item_id: str) -> str:
    if not item_id: return ""
    item_info = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(item_id, {})
    return item_info.get("media_key", item_id)

def _get_image_source(item_key: str) -> str:
    if not item_key:
        return getattr(game_data, "ITEM_IMAGES", {}).get("fallback", "")
    
    # 1. Tenta pegar ID de arquivo registrado (mais rápido)
    if registered_id := file_ids.get_file_id(item_key):
        return registered_id
        
    # 2. Tenta pegar configuração no game_data
    if fallback_source := getattr(game_data, "ITEM_IMAGES", {}).get(item_key):
        return fallback_source
    
    # 3. Fallback genérico
    return getattr(game_data, "ITEM_IMAGES", {}).get("fallback", "")

def _md_escape(text: str) -> str:
    return escape_markdown(str(text))

async def _send_or_edit_photo(
    query: CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
    photo_source: str,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
):
    """
    Função central para manipular a mensagem.
    Tenta APAGAR a anterior e ENVIAR uma nova com foto.
    """
    # 1. Tenta apagar a mensagem anterior (Menu de Receitas)
    try:
        await query.delete_message()
    except Exception as e:
        # É normal falhar se a mensagem for muito velha, apenas loga debug
        logger.debug(f"Não foi possível apagar mensagem anterior: {e}")

    # 2. Tenta enviar a nova mensagem com Foto
    try:
        if photo_source:
            # Verifica se é um caminho local ou ID do Telegram
            photo_input = InputFile(photo_source) if isinstance(photo_source, str) and photo_source.startswith(('assets/', './')) else photo_source
            
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=photo_input,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            raise ValueError("photo_source vazio")
            
    except Exception as e_photo:
        logger.error(f"Falha ao enviar foto ({photo_source}): {e_photo}. Usando fallback de texto.")
        # Se a foto falhar (ID inválido), envia texto para não travar o jogo
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=caption,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

def _pretty_item_name(item_id: str) -> str:
    info = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(item_id, {})
    name = info.get("display_name", item_id.replace("_", " ").title())
    emoji = info.get("emoji", "")
    full_name = f"{emoji} {name}" if emoji else name
    return _md_escape(full_name)

def _fmt_need_line(item_id: str, have: int, need: int) -> str:
    mark = "✅" if have >= need else "❌"
    return f"{mark} `{have}/{need}` {_pretty_item_name(item_id)}"

# =====================================================
# Funções de Interface (Menus da Forja)
# =====================================================

async def show_forge_professions_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    player_data = await player_manager.get_player_data(user_id)

    profession_info = "Você ainda não tem uma profissão de criação."
    if player_prof := (player_data or {}).get("profession"):
        if prof_id := player_prof.get("type"):
            prof_data = (getattr(game_data, "PROFESSIONS_DATA", {}) or {}).get(prof_id, {})
            if prof_data.get("category") == "crafting":
                prof_level = player_prof.get("level", 1)
                prof_display_name = prof_data.get("display_name", prof_id.capitalize())
                profession_info = f"Sua Profissão: *{_md_escape(prof_display_name)} (Nível {prof_level})*"

    keyboard = [[InlineKeyboardButton("🛠️ Aprimorar & Durabilidade", callback_data="enhance_menu")]]
    row = []
    all_professions = getattr(game_data, "PROFESSIONS_DATA", {}) or {}
    for prof_id, prof_data in all_professions.items():
        if prof_data.get("category") == "crafting":
            display_name = prof_data.get("display_name", prof_id.capitalize())
            row.append(InlineKeyboardButton(display_name, callback_data=f"forge:prof:{prof_id}:1"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("↩️ Voltar ao Reino", callback_data="show_kingdom_menu")])

    text = f"{profession_info}\n\n🔥 *Forja de Eldora*\nEscolha uma profissão para ver as receitas:"
    photo_source = _get_image_source("menu_forja_principal")

    await _send_or_edit_photo(query, context, photo_source, text, InlineKeyboardMarkup(keyboard))

async def show_profession_recipes_menu(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, profession_id: str, page: int):
    user_id = query.from_user.id
    player_data = await player_manager.get_player_data(user_id)

    player_prof = (player_data or {}).get("profession", {})
    player_prof_type = player_prof.get("type")
    player_prof_level = int(player_prof.get("level", 1))

    available_recipes = []
    if player_prof_type == profession_id:
        all_recipes = crafting_registry.all_recipes()
        for recipe_id, recipe_data in all_recipes.items():
            if recipe_data.get("profession") == profession_id:
                if player_prof_level >= recipe_data.get("level_req", 1):
                    available_recipes.append((recipe_id, recipe_data))

    available_recipes.sort(key=lambda r: r[1].get("level_req", 1))

    items_per_page = 5
    start_index = (page - 1) * items_per_page
    end_index = page * items_per_page
    paginated_recipes = available_recipes[start_index:end_index]

    keyboard = []
    for recipe_id, recipe_data in paginated_recipes:
        emoji = recipe_data.get("emoji", "🔧")
        display_name = recipe_data.get("display_name", "Receita")
        keyboard.append([InlineKeyboardButton(f"{emoji} {display_name}", callback_data=f"forge:recipe:{recipe_id}")])

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"forge:prof:{profession_id}:{page - 1}"))
    nav_row.append(InlineKeyboardButton("↩️ Voltar", callback_data="forge:main"))
    if end_index < len(available_recipes):
        nav_row.append(InlineKeyboardButton("Próxima ➡️", callback_data=f"forge:prof:{profession_id}:{page + 1}"))
    if nav_row:
        keyboard.append(nav_row)

    prof_name = (getattr(game_data, "PROFESSIONS_DATA", {}) or {}).get(profession_id, {}).get("display_name", "Desconhecida")

    if not available_recipes:
        text = (f"🔥 *Forja — {prof_name}*\n\n"
                "Você não tem o nível necessário para nenhuma receita, ou esta não é sua profissão ativa.")
        keyboard = [[InlineKeyboardButton("↩️ Voltar", callback_data="forge:main")]]
    else:
        text = f"🔥 *Forja — Receitas de {_md_escape(prof_name)} (Pág. {page})*\n\nEscolha um item para forjar:"

    photo_source = _get_image_source(f"profissao_{profession_id}_menu") or _get_image_source("menu_forja_principal")

    await _send_or_edit_photo(query, context, photo_source, text, InlineKeyboardMarkup(keyboard))

async def show_recipe_preview(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, recipe_id: str):
    user_id = query.from_user.id
    player_data = await player_manager.get_player_data(user_id)

    recipe_data = crafting_registry.get_recipe(recipe_id)
    if not recipe_data:
        await query.answer("Receita não encontrada.", show_alert=True)
        return

    preview = await crafting_engine.preview_craft(recipe_id, player_data)
    if not preview:
        await query.answer("Erro ao pré-visualizar a receita.", show_alert=True)
        return

    display_name = _md_escape(preview.get("display_name", "Item"))
    minutes = preview.get("duration_seconds", 0) // 60
    lines = [
        "🔥 *Forja - Confirmar Criação*", "",
        f"Item: *{preview.get('emoji','🛠')} {display_name}*",
        f"Tempo: *{minutes} minutos*", "",
        "Materiais Necessários:"
    ]
    inventory = (player_data or {}).get("inventory", {})
    inputs = preview.get("inputs") or {}
    for item_id, need in inputs.items():
        item_in_inventory = inventory.get(item_id)
        have = 0
        if isinstance(item_in_inventory, dict): have = item_in_inventory.get("quantity", 0)
        elif isinstance(item_in_inventory, int): have = item_in_inventory
        lines.append(_fmt_need_line(item_id, have, need))
    text = "\n".join(lines)

    keyboard = []
    back_button = InlineKeyboardButton("↩️ Voltar", callback_data=f"forge:prof:{recipe_data.get('profession')}:1")
    if preview.get("can_craft"):
        keyboard.append([back_button, InlineKeyboardButton("🔨 Forjar Item", callback_data=f"forge:confirm:{recipe_id}")])
    else:
        keyboard.append([back_button])
        text += "\n\n*Você não possui os materiais ou o nível/profissão necessários.*"

    output_item_id = recipe_data.get("output_item_id", recipe_id)
    image_key = _get_media_key_for_item(output_item_id)
    photo_source = _get_image_source(image_key)

    await _send_or_edit_photo(query, context, photo_source, text, InlineKeyboardMarkup(keyboard))

# =====================================================
# Lógica de Início e Término da Forja (CORRIGIDO)
# =====================================================

async def confirm_craft_start(query: CallbackQuery, recipe_id: str, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    
    # Inicia a lógica no motor
    result = await crafting_engine.start_craft(user_id, recipe_id)

    if isinstance(result, str):
        await query.answer(result, show_alert=True)
        return

    duration = result.get("duration_seconds", 0)
    job_name = f"craft_{user_id}_{recipe_id}"
    
    # Agenda a finalização
    context.job_queue.run_once(
        finish_craft_notification_job,
        duration,
        chat_id=query.message.chat_id,
        user_id=user_id,
        name=job_name,
        data={"recipe_id": recipe_id}
    )

    recipe_name = (crafting_registry.get_recipe(recipe_id) or {}).get("display_name", "item")
    
    # Texto de confirmação
    text = (f"🔥 *Forja Iniciada!*\n\n"
            f"O item *{_md_escape(recipe_name)}* está sendo moldado.\n"
            f"⏳ Tempo estimado: *{duration // 60} minutos*.\n\n"
            f"_Você será notificado quando estiver pronto._")

    # --- CORREÇÃO: Tenta pegar uma imagem de "trabalhando" ---
    # Se não tiver, usa a imagem do menu principal, mas NUNCA vazio.
    photo_source = _get_image_source("forge_working_gif") 
    if not photo_source:
        photo_source = _get_image_source("menu_forja_principal")

    # Adiciona botão para não travar o jogador na tela
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Voltar ao Menu", callback_data="forge:main")]])

    # Envia usando a função que apaga a anterior
    await _send_or_edit_photo(query, context, photo_source, caption=text, reply_markup=kb)

async def finish_craft_notification_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id = job.user_id
    chat_id = job.chat_id
    
    # O job.data pode vir vazio se foi reagendado pelo watchdog
    job_data = job.data or {}
    
    result = await crafting_engine.finish_craft(user_id)
    if not isinstance(result, dict) or "item_criado" not in result:
        # Silencia erros comuns de race condition
        # error_msg = f"⚠️ Status da forja: {result}"
        # logger.warning(error_msg)
        return

    item_criado = result["item_criado"]
    item_txt = formatar_item_para_exibicao(item_criado)
    
    text = f"✨ *Forja Concluída!*\n\nVocê obteve:\n{item_txt}"

    base_id = item_criado.get("base_id")
    image_key = _get_media_key_for_item(base_id)
    photo_source = _get_image_source(image_key)
    
    # Fallback de imagem de sucesso se o item não tiver imagem
    if not photo_source:
        photo_source = _get_image_source("forge_success_img")

    reply_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("🎒 Inventário", callback_data="inventory_menu"),
        InlineKeyboardButton("↩️ Voltar para a Forja", callback_data="forge:main")
    ]])

    try:
        if photo_source:
            await context.bot.send_photo(
                chat_id=chat_id, photo=photo_source, caption=text,
                parse_mode="Markdown", reply_markup=reply_markup,
            )
        else:
            raise ValueError("Fonte da foto não encontrada")
    except Exception as e:
        logger.error(f"Falha ao enviar foto do item criado ({e}). Enviando como texto.")
        await context.bot.send_message(
            chat_id=chat_id, text=text,
            parse_mode="Markdown", reply_markup=reply_markup,
        )
        
# =====================================================
# Roteador Principal de Callbacks da Forja
# =====================================================

async def forge_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data
    parts = data.split(":")
    logger.info(f"Roteador da Forja recebeu callback: {data}")

    try:
        action = parts[1]

        if action == "main":
            await show_forge_professions_menu(update, context)

        elif action == "prof":
            profession_id = parts[2]
            page = int(parts[3])
            await show_profession_recipes_menu(query, context, profession_id, page)

        elif action == "recipe":
            recipe_id = parts[2]
            await show_recipe_preview(query, context, recipe_id)

        elif action == "confirm":
            recipe_id = parts[2]
            await confirm_craft_start(query, recipe_id, context)

        else:
            logger.warning(f"Ação desconhecida no roteador da forja: {action}")
            await query.edit_message_text("❌ Ação da forja desconhecida.")

    except (IndexError, ValueError) as e:
        logger.error(f"Erro de formato no callback da forja: '{data}'. Erro: {e}")
        await query.edit_message_text("❌ Callback com formato inválido.")
    except Exception as e:
        logger.exception(f"Erro fatal ao processar callback da forja '{data}':")
        await query.edit_message_text("❌ Ocorreu um erro interno na forja. Tente novamente.")
        
# =====================================================
# Registro do Handler
# =====================================================

forge_handler = CallbackQueryHandler(forge_callback_router, pattern=r"^forge:")