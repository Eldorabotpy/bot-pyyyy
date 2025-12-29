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
from telegram.error import BadRequest, Forbidden
from modules.auth_utils import get_current_player_id
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
    if not key: return None
    if hasattr(file_ids, "get_file_data"):
        data = file_ids.get_file_data(key)
        if data and data.get("id"): return data
    if hasattr(file_ids, "get_file_id"):
        fid = file_ids.get_file_id(key)
        if fid: return {"id": fid, "type": "photo"}
    return None

def _md_escape(text: str) -> str:
    return escape_markdown(str(text))

async def _send_or_edit_media(query, context, media_data, caption, reply_markup=None):
    chat_id = query.message.chat_id
    try: await query.delete_message()
    except Exception: pass
    media_id = media_data.get("id")
    media_type = media_data.get("type", "photo").lower()
    try:
        if media_type == "video": await context.bot.send_video(chat_id=chat_id, video=media_id, caption=caption, reply_markup=reply_markup, parse_mode="Markdown")
        else: await context.bot.send_photo(chat_id=chat_id, photo=media_id, caption=caption, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Erro ao enviar mídia na forja: {e}")
        await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode="Markdown")

def _pretty_item_name(item_id: str) -> str:
    info = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(item_id, {})
    name = info.get("display_name", item_id.replace("_", " ").title())
    emoji = info.get("emoji", "")
    full_name = f"{emoji} {name}" if emoji else name
    return _md_escape(full_name)

def _fmt_need_line(item_id: str, have: int, need: int) -> str:
    mark = "✅" if have >= need else "❌"
    info = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(item_id, {})
    name = info.get("display_name", item_id.replace("_", " ").title())
    return f"{mark} `{have}/{need}` {_md_escape(name)}"

# =====================================================
# 1. LÓGICA DE EXECUÇÃO (Recovery Safe)
# =====================================================
# É AQUI QUE ENTRA A NOVA FUNÇÃO QUE VOCÊ PERGUNTOU
async def execute_craft_logic(
    user_id: int, 
    chat_id: int, 
    recipe_id: str, 
    context: ContextTypes.DEFAULT_TYPE, 
    message_id_to_delete: int = None
):
    """
    Finaliza a forja: entrega o item, calcula XP e notifica.
    Pode ser chamado pelo Job (normal) ou Recovery (reboot).
    """
    # 1. Apaga mensagem de progresso (se existir)
    if message_id_to_delete:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
        except Exception: pass

    # 2. Executa a lógica de finalização (Banco de Dados + Inventário)
    # O crafting_engine.finish_craft já cuida de verificar se está 'crafting' e dar o item
    result = await crafting_engine.finish_craft(user_id)
    
    if not isinstance(result, dict) or "item_criado" not in result:
        # Se retornou erro ou não tinha nada pra finalizar, paramos.
        # Mas garantimos que o player seja destravado se for um erro de estado.
        pdata = await player_manager.get_player_data(user_id)
        if pdata and pdata.get('player_state', {}).get('action') == 'crafting':
             pdata['player_state'] = {'action': 'idle'}
             await player_manager.save_player_data(user_id, pdata)
        return

    # 3. Notificação Visual
    item_criado = result["item_criado"]
    item_txt = formatar_item_para_exibicao(item_criado)
    
    text = f"✨ *Forja Concluída!*\n\nVocê obteve:\n{item_txt}"

    # Mídia
    base_id = item_criado.get("base_id")
    media_data = _get_media_data(f"item_{base_id}")
    
    if not media_data:
        media_data = {"id": "BAACAgEAAxkBAAEEcHBpUX9JS1KW8xJPX8HhLgkhiWQo_gACZgYAAlOKkEYoa0mljmtqoDYE", "type": "video"}

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🎒 Inventário", callback_data="inventory_menu"),
        InlineKeyboardButton("↩️ Voltar para a Forja", callback_data="forge:main")
    ]])

    try:
        if media_data.get("type") == "video" or str(media_data.get("id")).endswith(".mp4"):
            await context.bot.send_video(chat_id=chat_id, video=media_data["id"], caption=text, parse_mode="Markdown", reply_markup=kb)
        else:
            await context.bot.send_photo(chat_id=chat_id, photo=media_data["id"], caption=text, parse_mode="Markdown", reply_markup=kb)
            
    except Forbidden:
        logger.warning(f"Bot bloqueado pelo usuário {user_id} na forja.")
    except Exception as e:
        logger.error(f"Erro envio forja {user_id}: {e}")
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown", reply_markup=kb)
# =====================================================
# Funções de Interface (Menus da Forja)
# =====================================================

async def show_forge_professions_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = get_current_player_id(update, context)
    
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
        media_data = {"id": "https://i.ibb.co/d4sdS1qs/photo-2025-12-11-21-55-55.jpg", "type": "photo"}

    await _send_or_edit_media(query, context, media_data, text, InlineKeyboardMarkup(keyboard))

async def show_profession_recipes_menu(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, profession_id: str, page: int):
    user_id = context.user_data.get("logged_player_id") or query.from_user.id
    player_data = await player_manager.get_player_data(user_id)

    player_prof = (player_data or {}).get("profession", {})
    player_prof_type = player_prof.get("type")
    
    available_recipes = []
    # Mostra receitas apenas se for a profissão do jogador (opcional, ajustável)
    if player_prof_type == profession_id:
        all_recipes = crafting_registry.all_recipes()
        for recipe_id, recipe_data in all_recipes.items():
            if recipe_data.get("profession") == profession_id:
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
    if nav_row: keyboard.append(nav_row)

    prof_name = (getattr(game_data, "PROFESSIONS_DATA", {}) or {}).get(profession_id, {}).get("display_name", "Desconhecida")
    text = f"🔥 *Forja — Receitas de {_md_escape(prof_name)} (Pág. {page})*\n\nEscolha um item para forjar:"
    
    if not available_recipes:
        text = f"🔥 *Forja — {prof_name}*\n\nVocê não tem receitas disponíveis ou esta não é sua profissão ativa."
        keyboard = [[InlineKeyboardButton("↩️ Voltar", callback_data="forge:main")]]

    media_data = _get_media_data(f"profissao_{profession_id}_menu") or {"id": "https://media.tenor.com/images/a82f3073995eb879d74709d437033527/tenor.gif", "type": "photo"}
    await _send_or_edit_media(query, context, media_data, text, InlineKeyboardMarkup(keyboard))

async def show_recipe_preview(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, recipe_id: str):
    user_id = context.user_data.get("logged_player_id") or query.from_user.id
    player_data = await player_manager.get_player_data(user_id)

    recipe_data = crafting_registry.get_recipe(recipe_id)
    if not recipe_data:
        await query.answer("Receita não encontrada.", show_alert=True); return

    preview = await crafting_engine.preview_craft(recipe_id, player_data)
    if not preview:
        await query.answer("Erro ao pré-visualizar.", show_alert=True); return

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
        have = inventory.get(item_id, 0)
        if isinstance(have, dict): have = have.get("quantity", 0)
        lines.append(_fmt_need_line(item_id, have, need))
    text = "\n".join(lines)

    keyboard = []
    back_btn = InlineKeyboardButton("↩️ Voltar", callback_data=f"forge:prof:{recipe_data.get('profession')}:1")
    if preview.get("can_craft"):
        keyboard.append([back_btn, InlineKeyboardButton("🔨 Forjar Item", callback_data=f"forge:confirm:{recipe_id}")])
    else:
        keyboard.append([back_btn])
        text += "\n\n*Materiais insuficientes.*"

    media_data = _get_media_data(f"item_{recipe_data.get('output_item_id')}") or {"id": "BAACAgEAAxkBAAEEcHBpUX9JS1KW8xJPX8HhLgkhiWQo_gACZgYAAlOKkEYoa0mljmtqoDYE", "type": "video"}
    await _send_or_edit_media(query, context, media_data, text, InlineKeyboardMarkup(keyboard))

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
    if row: keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("↩️ Voltar ao Reino", callback_data="show_kingdom_menu")])

    text = f"{profession_info}\n\n🔥 *Forja de Eldora*\nEscolha uma profissão para ver as receitas:"
    media_data = _get_media_data("menu_forja_principal") or {"id": "https://media.tenor.com/images/a82f3073995eb879d74709d437033527/tenor.gif", "type": "photo"}

    await _send_or_edit_media(query, context, media_data, text, InlineKeyboardMarkup(keyboard))

# =====================================================
# Lógica de Início e Término da Forja (AGORA COM VIDEO)
# =====================================================

async def confirm_craft_start(query: CallbackQuery, recipe_id: str, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data.get("logged_player_id") or query.from_user.id
    chat_id = query.message.chat_id
    message_id_antiga = query.message.message_id
    
    result = await crafting_engine.start_craft(user_id, recipe_id)

    if isinstance(result, str):
        await query.answer(result, show_alert=True)
        return

    duration = result.get("duration_seconds", 0)
    job_name = f"craft_{user_id}_{recipe_id}"
    
    # Salva o ID da mensagem para apagar depois
    job_data = {"recipe_id": recipe_id, "message_id_notificacao": message_id_antiga}
    
    context.job_queue.run_once(
        finish_craft_notification_job,
        duration,
        chat_id=chat_id,
        user_id=user_id,
        name=job_name,
        data=job_data
    )

    recipe_name = (crafting_registry.get_recipe(recipe_id) or {}).get("display_name", "item")
    text = (f"🔥 *Forja Iniciada!*\n\n"
              f"Item: *{_md_escape(recipe_name)}*\n"
              f"⏳ Tempo: *{duration // 60} minutos*.\n\n"
              f"_Você será notificado._")

    kb = InlineKeyboardMarkup([]) 
    media_data = _get_media_data("forge_working_gif") or {"id": "AgACAgEAAxkBAAECtXNpNkGsTyrOVt3x3r-rtQ_JkqM2UAACIgtrG5_1mEWdopXF6XTxrAEAAwIAA3kAAzYE", "type": "video"}

    try:
        await query.edit_message_caption(caption=text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await _send_or_edit_media(query, context, media_data, caption=text, reply_markup=kb)

async def finish_craft_notification_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Função chamada pelo JobQueue. Apenas repassa os dados para a lógica principal.
    """
    job = context.job
    if not job: return
    
    await execute_craft_logic(
        user_id=job.user_id,
        chat_id=job.chat_id,
        recipe_id=job.data.get("recipe_id"),
        context=context,
        message_id_to_delete=job.data.get("message_id_notificacao")
    )
# =====================================================
# Roteador
# =====================================================

async def forge_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except BadRequest: pass

    data = query.data
    parts = data.split(":")
    
    try:
        action = parts[1]
        if action == "main": await show_forge_professions_menu(update, context)
        elif action == "prof": await show_profession_recipes_menu(query, context, parts[2], int(parts[3]))
        elif action == "recipe": await show_recipe_preview(query, context, parts[2])
        elif action == "confirm": await confirm_craft_start(query, parts[2], context)
    except Exception as e:
        logger.error(f"Erro forja callback {data}: {e}")
        await query.edit_message_text("❌ Erro interno.")
        
forge_handler = CallbackQueryHandler(forge_callback_router, pattern=r"^forge:")
