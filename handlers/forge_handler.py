# handlers/forge_handler.py
"""
Este módulo contém toda a lógica para o sistema de forja do bot.
Ele lida com a exibição de profissões, listas de receitas, pré-visualização de itens,
confirmação de criação e notificações de conclusão.

O fluxo é gerenciado por um roteador principal (forge_callback_router) que
interpreta os dados de callback que começam com "forge:".
"""

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
    clan_manager,
    mission_manager,
    file_ids,
)

print("!!! O ARQUIVO forge_handler.py FOI CARREGADO COM SUCESSO !!!")

logger = logging.getLogger(__name__)

# --- Fallback de Display Utils ---
# Tenta importar a função de formatação. Se não encontrar, cria uma alternativa básica.
try:
    from modules.display_utils import formatar_item_para_exibicao
except (ImportError, AttributeError):
    def formatar_item_para_exibicao(item_criado: dict) -> str:
        """Fallback para formatar a exibição de um item."""
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
    """Busca a 'media_key' nos dados do item. Retorna item_id como fallback."""
    if not item_id:
        return ""
    item_info = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(item_id, {})
    return item_info.get("media_key", item_id)

def _get_image_source(item_key: str) -> str:
    """Obtém o ID ou URL da imagem para um item, com fallbacks."""
    if not item_key:
        return getattr(game_data, "ITEM_IMAGES", {}).get("fallback", "")
    
    # Prioridade 1: ID de arquivo registrado
    if registered_id := file_ids.get_file_id(item_key):
        return registered_id
        
    # Prioridade 2: URL/caminho de fallback definido em game_data
    if fallback_source := getattr(game_data, "ITEM_IMAGES", {}).get(item_key):
        return fallback_source
        
    # Prioridade 3: Fallback global
    return getattr(game_data, "ITEM_IMAGES", {}).get("fallback", "")

def _md_escape(text: str) -> str:
    """Escapa caracteres especiais para o modo MarkdownV2 (mais seguro)."""
    return escape_markdown(str(text))

async def _send_or_edit_photo(
    query: CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
    photo_source: str,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
):
    """
    Tenta editar a mídia e o texto de uma mensagem. Se falhar, tenta editar
    apenas o texto. Se tudo falhar, envia uma nova mensagem.
    """
    try:
        # Tenta editar a mídia primeiro se a mensagem já tiver uma foto
        if query.message.photo and photo_source:
            photo_input = InputFile(photo_source) if photo_source.startswith(('assets/', './')) else photo_source
            await query.edit_message_media(media=InputMediaPhoto(media=photo_input), reply_markup=reply_markup)
            # A legenda precisa ser editada em uma chamada separada após a mídia
            await query.edit_message_caption(caption=caption, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            # Fallback: se não havia foto ou a edição de mídia falhou, edita o texto
            await query.edit_message_text(text=caption, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Falha ao editar a mensagem ({e}), enviando uma nova.")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=caption,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

def _pretty_item_name(item_id: str) -> str:
    """Formata o nome de um item para exibição, com emoji."""
    info = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(item_id, {})
    name = info.get("display_name", item_id.replace("_", " ").title())
    emoji = info.get("emoji", "")
    full_name = f"{emoji} {name}" if emoji else name
    return _md_escape(full_name)

def _fmt_need_line(item_id: str, have: int, need: int) -> str:
    """Formata uma linha de "materiais necessários"."""
    mark = "✅" if have >= need else "❌"
    return f"{mark} `{have}/{need}` {_pretty_item_name(item_id)}"

# =====================================================
# Funções de Interface (Menus da Forja)
# =====================================================

async def show_forge_professions_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Exibe o menu principal da forja com as profissões de criação.
    Esta é a função de entrada para o fluxo de forja.
    """
    query = update.callback_query
    user_id = query.from_user.id
    # <<< CORREÇÃO 1: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)

    profession_info = "Você ainda não tem uma profissão de criação."
    # Lógica síncrona para verificar a profissão
    if player_prof := (player_data or {}).get("profession"):
        if prof_id := player_prof.get("type"):
            prof_data = (getattr(game_data, "PROFESSIONS_DATA", {}) or {}).get(prof_id, {})
            if prof_data.get("category") == "crafting":
                prof_level = player_prof.get("level", 1)
                prof_display_name = prof_data.get("display_name", prof_id.capitalize())
                profession_info = f"Sua Profissão: *{_md_escape(prof_display_name)} (Nível {prof_level})*"

    # Construção síncrona do teclado
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
    photo_source = _get_image_source("menu_forja_principal") # Síncrono

    # <<< CORREÇÃO 2: Adiciona await >>>
    await _send_or_edit_photo(query, context, photo_source, text, InlineKeyboardMarkup(keyboard)) # Chama função async

async def show_profession_recipes_menu(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, profession_id: str, page: int):
    """
    Exibe a lista paginada de receitas para uma profissão.
    (VERSÃO COM LOGS DE DEBUG)
    """
    logger.info(f"--- INICIANDO DEBUG: FORJA PARA PROFISSÃO '{profession_id}' ---")

    user_id = query.from_user.id
    # <<< CORREÇÃO 3: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)

    # Lógica síncrona
    player_prof = (player_data or {}).get("profession", {})
    player_prof_type = player_prof.get("type")
    player_prof_level = int(player_prof.get("level", 1))

    logger.info(f"DADOS DO JOGADOR: Profissão Ativa='{player_prof_type}', Nível={player_prof_level}")
    logger.info(f"DADOS DO MENU: Profissão Requisitada='{profession_id}'")

    available_recipes = []
    if player_prof_type != profession_id:
        logger.warning(f"FALHA NA VERIFICAÇÃO DE PROFISSÃO: Ativa ('{player_prof_type}') != Requisitada ('{profession_id}')")

    # Lógica síncrona
    if player_prof_type == profession_id:
        all_recipes = crafting_registry.all_recipes()
        logger.info(f"REGISTRO DE RECEITAS: {len(all_recipes)} receitas encontradas no total.")
        recipes_for_this_prof = 0
        for recipe_id, recipe_data in all_recipes.items():
            if recipe_data.get("profession") == profession_id:
                recipes_for_this_prof += 1
                if player_prof_level >= recipe_data.get("level_req", 1):
                    available_recipes.append((recipe_id, recipe_data))
        logger.info(f"FILTRO DE RECEITAS: Encontradas {recipes_for_this_prof} receitas para '{profession_id}'.")
        logger.info(f"FILTRO DE NÍVEL: {len(available_recipes)} receitas passaram no filtro de nível (Nível do Jogador: {player_prof_level}).")

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

    photo_source = _get_image_source(f"profissao_{profession_id}_menu") or _get_image_source("menu_forja_principal") # Síncrono

    # <<< CORREÇÃO 4: Adiciona await >>>
    await _send_or_edit_photo(query, context, photo_source, text, InlineKeyboardMarkup(keyboard)) # Chama função async
    logger.info("--- FIM DO DEBUG: FORJA ---")

async def show_recipe_preview(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, recipe_id: str):
    """Mostra os detalhes de uma receita, materiais e o botão de confirmação."""
    user_id = query.from_user.id
    # <<< CORREÇÃO 5: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)

    # Assumindo síncrono
    recipe_data = crafting_registry.get_recipe(recipe_id)
    if not recipe_data:
        await query.answer("Receita não encontrada.", show_alert=True)
        return

    # Assumindo síncrono
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

    # Montagem síncrona dos botões
    keyboard = []
    back_button = InlineKeyboardButton("↩️ Voltar", callback_data=f"forge:prof:{recipe_data.get('profession')}:1")
    if preview.get("can_craft"):
        keyboard.append([back_button, InlineKeyboardButton("🔨 Forjar Item", callback_data=f"forge:confirm:{recipe_id}")])
    else:
        keyboard.append([back_button])
        text += "\n\n*Você não possui os materiais ou o nível/profissão necessários.*"

    output_item_id = recipe_data.get("output_item_id", recipe_id)
    image_key = _get_media_key_for_item(output_item_id) # Síncrono
    photo_source = _get_image_source(image_key) # Síncrono

    # <<< CORREÇÃO 6: Adiciona await >>>
    await _send_or_edit_photo(query, context, photo_source, text, InlineKeyboardMarkup(keyboard)) # Chama função async

# =====================================================
# Lógica de Início e Término da Forja
# =====================================================

async def confirm_craft_start(query: CallbackQuery, recipe_id: str, context: ContextTypes.DEFAULT_TYPE):
    """Inicia o processo de forja e agenda a notificação de conclusão."""
    user_id = query.from_user.id
    # Assumindo start_craft síncrono
    result = await crafting_engine.start_craft(user_id, recipe_id)

    if isinstance(result, str):
        await query.answer(result, show_alert=True)
        return

    # Lógica síncrona
    duration = result.get("duration_seconds", 0)
    job_name = f"craft_{user_id}_{recipe_id}"
    context.job_queue.run_once(
        finish_craft_notification_job, # Nome da função async
        duration,
        chat_id=query.message.chat_id,
        user_id=user_id,
        name=job_name,
        # Passa recipe_id para o job poder atualizar missões
        data={"recipe_id": recipe_id}
    )

    recipe_name = (crafting_registry.get_recipe(recipe_id) or {}).get("display_name", "item")
    text = (f"🔥 *Forja Iniciada!*\n\n"
            f"Seu(sua) *{_md_escape(recipe_name)}* está sendo forjado.\n"
            f"Ele ficará pronto em *{duration // 60} minutos*.")

    # <<< CORREÇÃO 7: Adiciona await >>>
    # Passa photo_source vazio para garantir que a foto é removida ou texto é editado
    await _send_or_edit_photo(query, context, photo_source="", caption=text, reply_markup=None) # Chama função async

# <<< CORREÇÃO 8: Adiciona async def >>>
async def finish_craft_notification_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Job que é executado quando a forja termina. Entrega o item ao jogador
    e envia uma notificação.
    """
    job = context.job
    user_id = job.user_id
    chat_id = job.chat_id
    recipe_id = (job.data or {}).get("recipe_id") # Pega recipe_id do job.data

    # Assumindo finish_craft síncrono
    result = await crafting_engine.finish_craft(user_id)
    if not isinstance(result, dict) or "item_criado" not in result:
        error_msg = f"⚠️ Erro ao finalizar a forja: {result}"
        logger.error(error_msg)
        await context.bot.send_message(chat_id=chat_id, text=error_msg)
        return

    item_criado = result["item_criado"]
    # <<< CORREÇÃO 9: Adiciona await >>>
    player_data = await player_manager.get_player_data(user_id)

    # Atualiza missões (síncrono localmente, async para clã)
    if player_data and (base_id := item_criado.get("base_id")):
        mission_manager.update_mission_progress(player_data, "CRAFT", {"item_id": base_id, "quantity": 1}) # Síncrono

        if clan_id := player_data.get("clan_id"):
             try: # Adiciona try/except para missão de clã
                # <<< CORREÇÃO 10: Adiciona await >>>
                await clan_manager.update_guild_mission_progress(
                    clan_id=clan_id,
                    mission_type='CRAFT',
                    # Passa recipe_id se a missão precisar dele
                    details={"item_id": base_id, "quantity": 1, "recipe_id": recipe_id},
                    context=context
                )
             except Exception as e_clan_craft:
                  logger.error(f"Erro ao atualizar missão de guilda CRAFT para clã {clan_id}: {e_clan_craft}")


        # <<< CORREÇÃO 11: Adiciona await >>>
        await player_manager.save_player_data(user_id, player_data)

    # Formatação e envio (síncrono + async)
    item_txt = formatar_item_para_exibicao(item_criado) # Síncrono
    text = f"✨ *Forja Concluída!*\n\nVocê obteve:\n{item_txt}"

    base_id = item_criado.get("base_id")
    image_key = _get_media_key_for_item(base_id) # Síncrono
    photo_source = _get_image_source(image_key) # Síncrono

    reply_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("↩️ Voltar para a Forja", callback_data="forge:main")
    ]])

    try:
        if photo_source:
            # <<< CORREÇÃO 12: Adiciona await >>>
            await context.bot.send_photo(
                chat_id=chat_id, photo=photo_source, caption=text,
                parse_mode="Markdown", reply_markup=reply_markup,
            )
        else:
            raise ValueError("Fonte da foto não encontrada")
    except Exception as e:
        logger.error(f"Falha ao enviar foto do item criado ({e}). Enviando como texto.")
        # <<< CORREÇÃO 13: Adiciona await >>>
        await context.bot.send_message(
            chat_id=chat_id, text=text,
            parse_mode="Markdown", reply_markup=reply_markup,
        )
        
# =====================================================
# Roteador Principal de Callbacks da Forja
# =====================================================

async def forge_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Captura e roteia todos os callbacks que começam com 'forge:'.
    """
    query = update.callback_query
    await query.answer()

    data = query.data
    parts = data.split(":")
    logger.info(f"Roteador da Forja recebeu callback: {data}")

    try:
        action = parts[1]

        if action == "main":
            # <<< CORREÇÃO 14: Adiciona await >>>
            await show_forge_professions_menu(update, context)

        elif action == "prof":
            profession_id = parts[2]
            page = int(parts[3])
            # <<< CORREÇÃO 15: Adiciona await >>>
            await show_profession_recipes_menu(query, context, profession_id, page)

        elif action == "recipe":
            recipe_id = parts[2]
            # <<< CORREÇÃO 16: Adiciona await >>>
            await show_recipe_preview(query, context, recipe_id)

        elif action == "confirm":
            recipe_id = parts[2]
            # <<< CORREÇÃO 17: Adiciona await >>>
            await confirm_craft_start(query, recipe_id, context)

        else:
            logger.warning(f"Ação desconhecida no roteador da forja: {action}")
            # <<< CORREÇÃO 18: Adiciona await >>>
            await query.edit_message_text("❌ Ação da forja desconhecida.")

    except (IndexError, ValueError) as e:
        logger.error(f"Erro de formato no callback da forja: '{data}'. Erro: {e}")
        # <<< CORREÇÃO 19: Adiciona await >>>
        await query.edit_message_text("❌ Callback com formato inválido.")
    except Exception as e:
        logger.exception(f"Erro fatal ao processar callback da forja '{data}':")
        # <<< CORREÇÃO 20: Adiciona await >>>
        await query.edit_message_text("❌ Ocorreu um erro interno na forja. Tente novamente.")
        
# =====================================================
# Registro do Handler
# =====================================================

# Este handler único captura todos os callbacks relacionados à forja.
forge_handler = CallbackQueryHandler(forge_callback_router, pattern=r"^forge:")