# handlers/profession_handler.py

import math
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, game_data, file_ids, crafting_registry
from modules.game_data.refining import REFINING_RECIPES

logger = logging.getLogger(__name__)

# Itens por página nas listas
RECIPES_PER_PAGE = 6

# ==================================================================
# HELPERS
# ==================================================================

def _bar(current: int, total: int, blocks: int = 10, filled_char: str = '🟧', empty_char: str = '⬜️') -> str:
    if total <= 0: filled = blocks
    else:
        ratio = max(0.0, min(1.0, float(current) / float(total)))
        filled = int(round(ratio * blocks))
    return filled_char * filled + empty_char * (blocks - filled)

def _get_profession_info(player_data: dict):
    """Extrai dados normalizados da profissão."""
    prof_data = player_data.get("profession")
    key, level, xp = None, 1, 0
    if isinstance(prof_data, dict):
        key = prof_data.get("type")
        level = int(prof_data.get("level", 1))
        xp = int(prof_data.get("xp", 0))
    elif isinstance(prof_data, str):
        key = prof_data
    return key, level, xp

def _prof_label(key: str, data: dict) -> str:
    return f"{data.get('emoji','💼')} {data.get('display_name', key.capitalize())}"

def _get_recipes_for_profession(prof_key: str, category: str) -> list:
    filtered = []
    craft_recipes = crafting_registry.all_recipes() or {}
    refine_recipes = REFINING_RECIPES or {}
    all_pool = {}
    all_pool.update(craft_recipes)
    all_pool.update(refine_recipes)

    for item_result_id, recipe_data in all_pool.items():
        req_prof = recipe_data.get("profession")
        # Verifica se a profissão bate (suporta string ou lista)
        if isinstance(req_prof, list):
            if prof_key not in req_prof: continue
        elif req_prof != prof_key: continue
            
        item_info = game_data.ITEMS_DATA.get(item_result_id, {})
        if not item_info:
            item_info = {"display_name": recipe_data.get("display_name", item_result_id), "emoji": "🔸"}

        item_type = (item_info.get("type") or "").lower()
        item_cat = (item_info.get("category") or "").lower()
        
        is_refining = item_result_id in refine_recipes
        if not is_refining:
            if item_type in ("material_refinado", "material", "ingrediente", "reagent") or item_cat == "coletavel":
                is_refining = True
            
        if category == "refino" and is_refining:
            filtered.append((item_result_id, recipe_data, item_info))
        elif category == "craft" and not is_refining:
            filtered.append((item_result_id, recipe_data, item_info))
            
    filtered.sort(key=lambda x: int(x[1].get("level_req", 1)))
    return filtered

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML', media_key="img_profissao"):
    """
    Função Inteligente de Envio:
    1. Procura imagem específica > pai > genérica.
    2. Se achar imagem: Tenta editar a mídia ou envia nova foto.
    3. Se NÃO achar imagem (None): Edita apenas o texto ou envia nova mensagem de texto.
    """
    fd = None
    
    # 1. Tenta chave específica (ex: img_prof_armeiro_craft)
    if media_key:
        fd = file_ids.get_file_data(media_key)
    
    # 2. Tenta chave pai (ex: img_prof_armeiro)
    if not fd and media_key and "_" in media_key:
        parent_key = media_key.rsplit("_", 1)[0]
        fd = file_ids.get_file_data(parent_key)
        
    # 3. Tenta genérica (img_profissao)
    if not fd:
        fd = file_ids.get_file_data("img_profissao")

    media_id = fd.get("id") if fd else None
    media_type = (fd.get("type") or "photo").lower() if fd else "photo"

    # --- TENTATIVA DE EDIÇÃO ---
    if query and query.message:
        try:
            if media_id:
                # Tem imagem nova para mostrar
                media = InputMediaVideo(media_id, caption=text, parse_mode=parse_mode) if media_type == "video" else InputMediaPhoto(media_id, caption=text, parse_mode=parse_mode)
                await query.edit_message_media(media=media, reply_markup=reply_markup)
            else:
                # Não tem imagem (ou não achou no banco): Edita só o texto
                await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
            return
        except Exception:
            pass # Falha na edição, tenta reenvio limpo

    # --- REENVIO LIMPO (Fallback) ---
    if query and query.message:
        try: await query.delete_message()
        except: pass
    
    if media_id:
        try:
            if media_type == "video":
                await context.bot.send_video(chat_id=chat_id, video=media_id, caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
            else:
                await context.bot.send_photo(chat_id=chat_id, photo=media_id, caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
            return
        except: pass 
        
    # Último recurso: Apenas texto
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

# ==================================================================
# 1. LÓGICA DE ESCOLHA DE PROFISSÃO (Se não tiver)
# ==================================================================

async def show_profession_choose_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, player_data: dict):
    """Mostra o menu de escolha se o jogador não tiver profissão."""
    q = update.callback_query
    chat_id = q.message.chat_id

    # Diagnóstico: Verifica se existem profissões carregadas
    all_profs = game_data.PROFESSIONS_DATA or {}
    if not all_profs:
        await _safe_edit_or_send(q, context, chat_id, "⚠️ Nenhuma profissão foi configurada no sistema ainda.", InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="profile")]]))
        return

    title = "💼 <b>Escolher Profissão</b>\nSelecione uma profissão para desbloquear coletas, refino e criação de itens.\n"
    kb = []
    
    for key, data in all_profs.items():
        # O callback data usa o ID da profissão
        kb.append([InlineKeyboardButton(_prof_label(key, data), callback_data=f"job_pick_{key}")])
        
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="profile")])

    await _safe_edit_or_send(q, context, chat_id, title, InlineKeyboardMarkup(kb))

async def pick_profession_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Define a profissão selecionada."""
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = q.message.chat_id

    pdata = await player_manager.get_player_data(user_id)
    if not pdata: return

    # Verifica novamente
    if (pdata.get('profession') or {}).get('type'):
        await q.answer("Você já possui uma profissão.", show_alert=True)
        return

    prefix = "job_pick_"
    data = q.data or ""
    if not data.startswith(prefix): return
    prof_key = data[len(prefix):]

    all_profs = game_data.PROFESSIONS_DATA or {}
    if prof_key not in all_profs:
        await q.answer(f"Profissão '{prof_key}' inválida.", show_alert=True)
        return

    # Define a profissão
    pdata['profession'] = {"type": prof_key, "level": 1, "xp": 0}
    await player_manager.save_player_data(user_id, pdata)

    # Redireciona para o menu da profissão recém-adquirida
    await job_menu_callback(update, context)

# ==================================================================
# 2. MENU PRINCIPAL DA PROFISSÃO (Se já tiver)
# ==================================================================

async def job_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return

    prof_key, prof_level, prof_xp = _get_profession_info(player_data)
    
    # SE NÃO TIVER PROFISSÃO: Mostra o menu de escolha
    if not prof_key:
        if query:
            await show_profession_choose_menu(update, context, player_data)
        return

    prof_info = (game_data.PROFESSIONS_DATA or {}).get(prof_key, {})
    display_name = prof_info.get("display_name", prof_key.title())
    emoji = prof_info.get("emoji", "⚒️")
    desc = prof_info.get("description", "Um mestre em seu ofício.")

    try: xp_next = int(game_data.get_xp_for_next_collection_level(prof_level))
    except: xp_next = prof_level * 1000 
    
    bar = _bar(prof_xp, xp_next)
    
    text = (
        f"{emoji} <b>GUIA DA PROFISSÃO: {display_name.upper()}</b>\n\n"
        f"<i>{desc}</i>\n\n"
        f"🎖️ <b>Nível:</b> {prof_level}\n"
        f"💠 <b>Progresso:</b> <code>[{bar}]</code> ({prof_xp}/{xp_next} XP)\n\n"
        f"Selecione uma categoria para ver as receitas disponíveis:"
    )

    keyboard = [
        [
            InlineKeyboardButton("🔨 Criação (Equips)", callback_data=f"job_list_craft_1"),
            InlineKeyboardButton("🔥 Refino (Materiais)", callback_data=f"job_list_refino_1")
        ],
        [InlineKeyboardButton("🔙 Voltar ao Perfil", callback_data="profile")]
    ]
    
    img_key = f"img_prof_{prof_key}"
    await _safe_edit_or_send(query, context, chat_id, text, InlineKeyboardMarkup(keyboard), media_key=img_key)

# ==================================================================
# 3. LISTA DE RECEITAS (Paginada e Separada)
# ==================================================================

async def job_recipes_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        # Formato esperado: job_list_MODO_PAGINA
        _, _, mode, page_str = query.data.split("_")
        page = int(page_str)
    except:
        await job_menu_callback(update, context)
        return

    user_id = query.from_user.id
    player_data = await player_manager.get_player_data(user_id)
    prof_key, prof_level, _ = _get_profession_info(player_data)

    recipes_list = _get_recipes_for_profession(prof_key, mode)
    
    if mode == "craft":
        title = "🔨 RECEITAS DE CRIAÇÃO"
        empty_msg = "Nenhuma receita de equipamento encontrada para esta profissão."
    else:
        title = "🔥 RECEITAS DE REFINO"
        empty_msg = "Nenhuma receita de refino encontrada para esta profissão."

    total_items = len(recipes_list)
    total_pages = math.ceil(total_items / RECIPES_PER_PAGE) or 1
    page = max(1, min(page, total_pages))
    
    start = (page - 1) * RECIPES_PER_PAGE
    end = start + RECIPES_PER_PAGE
    current_items = recipes_list[start:end]

    text = f"<b>{title}</b> (Pág {page}/{total_pages})\n\n"
    
    if not current_items:
        text += f"<i>{empty_msg}</i>"
    else:
        for item_id, recipe_data, item_info in current_items:
            base_name = item_info.get("display_name", item_id) or recipe_data.get("display_name") or item_id
            name = base_name.replace("_", " ").title()
            emoji = item_info.get("emoji", "🔸")
            lvl_req = recipe_data.get("level_req", 1)
            
            status_icon = "✅" if prof_level >= lvl_req else "🔒"
            
            mats = recipe_data.get("inputs") or recipe_data.get("materials") or {}
            mats_str_list = []
            for mat_id, qty in mats.items():
                mat_info = game_data.ITEMS_DATA.get(mat_id, {})
                mat_name = mat_info.get("display_name", mat_id)
                mats_str_list.append(f"{qty}x {mat_name}")
            mats_str = ", ".join(mats_str_list)
            
            text += f"{status_icon} <b>[Nv. {lvl_req}] {emoji} {name}</b>\n"
            text += f"   └ ⚒️ <i>{mats_str}</i>\n\n"

    keyboard = []
    nav_row = []
    if page > 1: nav_row.append(InlineKeyboardButton("⬅️ Ant.", callback_data=f"job_list_{mode}_{page-1}"))
    nav_row.append(InlineKeyboardButton("🔙 Menu Profissão", callback_data="job_menu"))
    if page < total_pages: nav_row.append(InlineKeyboardButton("Prox. ➡️", callback_data=f"job_list_{mode}_{page+1}"))
    if nav_row: keyboard.append(nav_row)
    
    img_key = f"img_prof_{prof_key}_{mode}"
    await _safe_edit_or_send(query, context, query.message.chat.id, text, InlineKeyboardMarkup(keyboard), media_key=img_key)

# ==================================================================
# GANCHOS (HANDLERS)
# ==================================================================
job_menu_handler = CallbackQueryHandler(job_menu_callback, pattern=r'^job_menu$')
job_pick_handler = CallbackQueryHandler(pick_profession_callback, pattern=r'^job_pick_.+$')
job_view_handler = CallbackQueryHandler(job_recipes_callback, pattern=r'^job_list_')

async def _noop(u, c): 
    if u.callback_query: await u.callback_query.answer("Em desenvolvimento.")
job_confirm_handler = CallbackQueryHandler(_noop, pattern=r'^job_confirm')
job_guide_handler = CallbackQueryHandler(_noop, pattern=r'^job_guide')