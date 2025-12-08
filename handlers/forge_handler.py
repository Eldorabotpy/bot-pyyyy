# handlers/forge_handler.py
# (VERSÃO FINAL 3.0: Suporte total a VÍDEO MP4 e FOTO na forja)

import logging
from telegram import (
    Update,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
)
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.helpers import escape_markdown
from telegram.error import BadRequest
from telegram.error import Forbidden
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

def _get_media_data(key: str) -> dict:
    """
    Busca os dados completos da mídia (ID e TIPO).
    Retorna: {'id': '...', 'type': 'video'/'photo'} ou None
    """
    if not key: return None
    
    # 1. Busca no gerenciador de arquivos (Prioridade)
    if hasattr(file_ids, "get_file_data"):
        data = file_ids.get_file_data(key)
        if data and data.get("id"):
            return data
            
    # 2. Fallback para apenas ID (assume foto se não tiver tipo)
    if hasattr(file_ids, "get_file_id"):
        fid = file_ids.get_file_id(key)
        if fid:
            return {"id": fid, "type": "photo"}
            
    return None

def _md_escape(text: str) -> str:
    return escape_markdown(str(text))

async def _send_or_edit_media(
    query: CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
    media_data: dict,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
):
    """
    Função inteligente que envia Foto ou Vídeo e limpa o chat.
    """
    chat_id = query.message.chat_id

    # 1. Limpa a mensagem anterior (Menu)
    try:
        await query.delete_message()
    except Exception:
        pass

    # 2. Prepara o envio
    media_id = media_data.get("id")
    media_type = media_data.get("type", "photo").lower()

    try:
        if not media_id:
            raise ValueError("ID de mídia vazio")

        # Verifica se é link (URL) -> Trata como Vídeo ou Foto URL
        if isinstance(media_id, str) and media_id.startswith("http"):
            if media_type == "video" or media_id.endswith(".mp4"):
                 await context.bot.send_video(
                    chat_id=chat_id, video=media_id, caption=caption, 
                    reply_markup=reply_markup, parse_mode="Markdown"
                )
            else:
                # Tenta como animação (GIF) se for URL genérica
                try:
                    await context.bot.send_animation(
                        chat_id=chat_id, animation=media_id, caption=caption, 
                        reply_markup=reply_markup, parse_mode="Markdown"
                    )
                except:
                    # Se falhar, tenta foto
                    await context.bot.send_photo(
                        chat_id=chat_id, photo=media_id, caption=caption,
                        reply_markup=reply_markup, parse_mode="Markdown"
                    )
        
        # Se for File ID do Telegram
        else:
            if media_type == "video":
                await context.bot.send_video(
                    chat_id=chat_id, video=media_id, caption=caption, 
                    reply_markup=reply_markup, parse_mode="Markdown"
                )
            else:
                # Padrão é foto
                await context.bot.send_photo(
                    chat_id=chat_id, photo=media_id, caption=caption, 
                    reply_markup=reply_markup, parse_mode="Markdown"
                )

    except Exception as e:
        logger.error(f"Falha ao enviar mídia ({media_type}): {e}. Enviando texto.")
        await context.bot.send_message(
            chat_id=chat_id, text=caption, 
            reply_markup=reply_markup, parse_mode="Markdown"
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
    
    # Busca dados da mídia
    media_data = _get_media_data("menu_forja_principal")
    # Fallback
    if not media_data:
        media_data = {"id": "https://i.pinimg.com/originals/a8/2f/30/a82f3073995eb879d74709d437033527.gif", "type": "photo"}

    await _send_or_edit_media(query, context, media_data, text, InlineKeyboardMarkup(keyboard))

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

    media_data = _get_media_data(f"profissao_{profession_id}_menu")
    if not media_data:
        media_data = {"id": "https://i.pinimg.com/originals/a8/2f/30/a82f3073995eb879d74709d437033527.gif", "type": "photo"}

    await _send_or_edit_media(query, context, media_data, text, InlineKeyboardMarkup(keyboard))

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
    # Tenta pegar imagem do item
    media_data = _get_media_data(f"item_{output_item_id}")
    if not media_data:
        # Fallback genérico
        media_data = {"id": "https://media.tenor.com/J1y9Y_5y4B0AAAAC/blacksmith-forge.gif", "type": "video"}

    await _send_or_edit_media(query, context, media_data, text, InlineKeyboardMarkup(keyboard))

# =====================================================
# Lógica de Início e Término da Forja (AGORA COM VIDEO)
# =====================================================

async def confirm_craft_start(query: CallbackQuery, recipe_id: str, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    
    result = await crafting_engine.start_craft(user_id, recipe_id)

    if isinstance(result, str):
        await query.answer(result, show_alert=True)
        return

    duration = result.get("duration_seconds", 0)
    job_name = f"craft_{user_id}_{recipe_id}"
    
    context.job_queue.run_once(
        finish_craft_notification_job,
        duration,
        chat_id=query.message.chat_id,
        user_id=user_id,
        name=job_name,
        data={"recipe_id": recipe_id}
    )

    recipe_name = (crafting_registry.get_recipe(recipe_id) or {}).get("display_name", "item")
    
    text = (f"🔥 *Forja Iniciada!*\n\n"
            f"O item *{_md_escape(recipe_name)}* está sendo moldado.\n"
            f"⏳ Tempo estimado: *{duration // 60} minutos*.\n\n"
            f"_Você será notificado quando estiver pronto._")

    # --- CORREÇÃO PRINCIPAL ---
    # Busca a mídia. Se você cadastrou "forge_working_gif" como type="video" no file_ids.py,
    # ele vai retornar {'id': '...', 'type': 'video'} e a função _send_or_edit_media vai usar send_video.
    media_data = _get_media_data("forge_working_gif") 
    
    # Fallback se não tiver no banco
    if not media_data:
        media_data = {"id": "https://media.tenor.com/J1y9Y_5y4B0AAAAC/blacksmith-forge.gif", "type": "video"}

    kb = InlineKeyboardMarkup([])

    # Envia a Mídia (Video ou Foto) e apaga o anterior
    await _send_or_edit_media(query, context, media_data, caption=text, reply_markup=kb)

async def finish_craft_notification_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id = job.user_id
    chat_id = job.chat_id
    
    # 1. Tenta pegar o ID da mensagem de notificação anterior para apagar
    message_id_antiga = job.data.get("message_id_notificacao") # Assume que o ID foi salvo aqui
    
    # 2. Finaliza a lógica do jogo (adiciona item, XP, etc.)
    result = await crafting_engine.finish_craft(user_id)
    if not isinstance(result, dict) or "item_criado" not in result:
        # Se a forja falhou ou já estava 'idle', apenas retorna
        return

    # 3. Apaga a notificação anterior ("Forja Iniciada!")
    if message_id_antiga:
        try:
            # Chama a função para apagar a mensagem anterior
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id_antiga)
        except Exception as e:
            # Ignora erros se a mensagem já foi apagada ou o bot não tem permissão
            logger.warning(f"Falha ao apagar notificação {message_id_antiga} no chat {chat_id}: {e}")
            pass

    # 4. Prepara e Envia a notificação de item obtido
    item_criado = result["item_criado"]
    item_txt = formatar_item_para_exibicao(item_criado)
    
    text = f"✨ *Forja Concluída!*\n\nVocê obteve:\n{item_txt}"

    base_id = item_criado.get("base_id")
    
    # Busca a imagem do item criado
    media_data = _get_media_data(f"item_{base_id}")
    
    if not media_data:
        # Fallback se item criado não tem foto (GIF Tenor)
        media_data = {"id": "https://media.tenor.com/images/157d605055627255953059275727c62d/tenor.gif", "type": "video"}

    reply_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("🎒 Inventário", callback_data="inventory_menu"),
        InlineKeyboardButton("↩️ Voltar para a Forja", callback_data="forge:main")
    ]])

    # --- NOVO BLOCO TRY/EXCEPT PARA TRATAR ERROS DE COMUNICAÇÃO ---
    try:
        # Tenta enviar a mensagem de item obtido (pode falhar com Forbidden)
        if media_data.get("type") == "video" or str(media_data.get("id")).endswith(".mp4"):
            await context.bot.send_video(chat_id=chat_id, video=media_data["id"], caption=text, parse_mode="Markdown", reply_markup=reply_markup)
        else:
            await context.bot.send_photo(chat_id=chat_id, photo=media_data["id"], caption=text, parse_mode="Markdown", reply_markup=reply_markup)
            
    except Forbidden:
        # Erro de bloqueio: o bot não pode enviar a mensagem, mas a lógica do jogo está correta.
        logger.warning(f"Usuário {user_id} bloqueou o bot. Notificação de forja falhou.")
        return # Sai sem tentar o fallback de texto
        
    except Exception as e:
        # Trata outros erros de envio de mídia
        logger.error(f"Falha ao enviar mídia final ({e}). Enviando texto como fallback.")
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown", reply_markup=reply_markup)
               
# =====================================================
# Roteador
# =====================================================

async def forge_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except BadRequest:
        pass

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
            await query.edit_message_text("❌ Ação da forja desconhecida.")

    except Exception as e:
        logger.exception(f"Erro fatal ao processar callback da forja '{data}':")
        await query.edit_message_text("❌ Ocorreu um erro interno na forja.")
        
forge_handler = CallbackQueryHandler(forge_callback_router, pattern=r"^forge:")