# handlers/refining_handler.py
import logging 
import math
import telegram
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
)
from telegram.ext import ContextTypes, CallbackQueryHandler

# Engines e dados
# REMOVIDO: mission_manager, clan_manager (para evitar erros)
from modules import game_data, player_manager, file_ids
from modules.refining_engine import preview_refine, start_refine, finish_refine
from modules import crafting_registry
from modules import dismantle_engine
from modules import display_utils

ITEMS_PER_PAGE = 5
logger = logging.getLogger(__name__)

# =========================
# Helpers de UI e utilitários
# =========================
async def _safe_send_with_media(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    caption: str,
    reply_markup=None,
    media_key: str | None = None,
    fallback_key: str = "refino_universal",
):
    keys_to_try = []
    if media_key:
        keys_to_try.append(media_key)
    if fallback_key:
        keys_to_try.append(fallback_key)

    media_sent = False
    sent_message = None

    for key in keys_to_try:
        fd = file_ids.get_file_data(key)
        if not fd or not fd.get("id"):
            continue 

        media_id = fd["id"]
        ftype = (fd.get("type") or "photo").lower()

        try:
            if ftype == "video":
                sent_message = await context.bot.send_video(
                    chat_id=chat_id, video=media_id, caption=caption, 
                    reply_markup=reply_markup, parse_mode="HTML"
                )
            else:
                sent_message = await context.bot.send_photo(
                    chat_id=chat_id, photo=media_id, caption=caption, 
                    reply_markup=reply_markup, parse_mode="HTML"
                )
            media_sent = True
            break 
        except telegram.error.BadRequest as e:
            if "Wrong file identifier" in str(e):
                continue 
            else:
                logger.exception(f"Erro de mídia (ignorado): {e}")
    
    if not media_sent:
        sent_message = await context.bot.send_message(
            chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML"
        )

    return sent_message


async def _safe_edit_or_send_with_media(
    query: CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    caption: str,
    reply_markup=None,
    media_key: str = "refino_universal"
):
    try:
       await query.delete_message()
    except Exception:
        pass

    sent_message = await _safe_send_with_media(
        context,
        chat_id,
        caption,
        reply_markup,
        media_key=media_key,
        fallback_key="refino_universal"
    )
    return sent_message

def _fmt_minutes_or_seconds(seconds: int) -> str:
    return f"{round(seconds/60)} min" if seconds >= 60 else f"{int(seconds)}s"

def _fmt_item_line(item_id: str, qty: int) -> str:
    info = (game_data.ITEMS_DATA or {}).get(item_id) or {}
    display = (
        info.get("display_name")
        or getattr(game_data, "item_display_name", lambda x: None)(item_id)
        or item_id.replace("_", " ").title()
    )
    emoji = info.get("emoji", "")
    prefix = f"{emoji} " if emoji else ""
    return f"{prefix}<b>{display}</b> x{int(qty)}"

# =========================
# Handlers Principais
# =========================

async def refining_main_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = q.message.chat.id

    RECIPES_PER_PAGE = 8
    current_page = 1 
    
    if q.data and "_PAGE_" in q.data:
        try:
            current_page = int(q.data.split('_PAGE_')[-1])
        except ValueError:
            current_page = 1

    pdata = await player_manager.get_player_data(user_id) or {}

    all_available_recipes = []
    for rid, rec in game_data.REFINING_RECIPES.items():
        prev = preview_refine(rid, pdata)
        if prev and rec.get("display_name"):
             mins = _fmt_minutes_or_seconds(int(prev.get("duration_seconds", 0)))
             all_available_recipes.append({
                 "id": rid, 
                 "data": rec, 
                 "preview": prev,
                 "duration_fmt": mins
             }) 

    total_recipes = len(all_available_recipes)
    total_pages = max(1, math.ceil(total_recipes / RECIPES_PER_PAGE))
    current_page = max(1, min(current_page, total_pages))
    
    start = (current_page - 1) * RECIPES_PER_PAGE
    end = start + RECIPES_PER_PAGE
    recipes_on_page = all_available_recipes[start:end]

    lines = ["🛠️ <b>Refino & Desmontagem</b>\n"]
    lines.append(f"🧾 <b>Receitas:</b> (Pág. {current_page}/{total_pages})")
    
    kb: list[list[InlineKeyboardButton]] = []
    kb.append([InlineKeyboardButton("♻️ Desmontar Equipamento", callback_data="ref_dismantle_list")])
    
    if not recipes_on_page:
        lines.append("\nNenhuma receita disponível nesta página.")
    
    for recipe in recipes_on_page:
        rid, rec, prev, mins = recipe["id"], recipe["data"], recipe["preview"], recipe["duration_fmt"]
        tag = "✅" if prev.get("can_refine") else "⛔"
        lines.append(f"{tag} {rec.get('display_name', rid)} | ⏳ {mins}") 
        kb.append([
            InlineKeyboardButton(
                text=rec.get("display_name", rid),
                callback_data=f"ref_sel_{rid}",
            )
        ])
    
    pag_kb = []
    if current_page > 1:
        pag_kb.append(InlineKeyboardButton("◀️ Anterior", callback_data=f"ref_main_PAGE_{current_page - 1}"))
    
    pag_kb.append(InlineKeyboardButton(f"- {current_page} / {total_pages} -", callback_data="noop_ref_page"))
    
    if current_page < total_pages:
        pag_kb.append(InlineKeyboardButton("Próximo ▶️", callback_data=f"ref_main_PAGE_{current_page + 1}"))
        
    if pag_kb: kb.append(pag_kb)
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="continue_after_action")])
    
    caption = "\n".join(lines)
    await _safe_edit_or_send_with_media(q, context, chat_id, caption, InlineKeyboardMarkup(kb))

async def show_dismantle_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = q.message.chat.id

    player_data = await player_manager.get_player_data(user_id) or {}

    page = 0
    if q.data and ':page:' in q.data:
        try:
            page = int(q.data.split(':page:')[1])
        except (ValueError, IndexError):
            page = 0

    inventory = player_data.get("inventory", {})
    equipped_uids = {v for k, v in player_data.get("equipment", {}).items()}

    all_dismantleable_items = []
    for item_uid, item_data in inventory.items():
        if isinstance(item_data, dict) and item_uid not in equipped_uids:
            base_id = item_data.get("base_id")
            if base_id and crafting_registry.get_recipe_by_item_id(base_id):
                all_dismantleable_items.append((item_uid, item_data))

    all_dismantleable_items.sort(key=lambda x: x[1].get("display_name", ""))

    start_index = page * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    items_on_page = all_dismantleable_items[start_index:end_index]
    total_pages = (len(all_dismantleable_items) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    caption = (
        "♻️ <b>Desmontar Equipamento</b>\n\n"
        "Selecione um item do seu inventário para desmontar. Itens equipados não são mostrados."
    )

    keyboard = []
    if not items_on_page:
        if page == 0:
             caption += "\n\nVocê não possui nenhum equipamento desmontável no seu inventário."
        else:
             caption += "\n\nNão há mais itens para mostrar nesta página."
    else:
        for item_uid, item_data in items_on_page:
            item_name = item_data.get("display_name", "Item Desconhecido")
            keyboard.append([
                InlineKeyboardButton(
                    f"🔩 {item_name}",
                    callback_data=f"ref_dismantle_preview:{item_uid}"
                )
            ])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"ref_dismantle_list:page:{page - 1}"))
    if end_index < len(all_dismantleable_items):
        nav_buttons.append(InlineKeyboardButton("Próxima ➡️", callback_data=f"ref_dismantle_list:page:{page + 1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data="ref_main")])

    if total_pages > 1:
        caption += f"\n\n<i>Página {page + 1} de {total_pages}</i>"

    await _safe_edit_or_send_with_media(q, context, chat_id, caption, InlineKeyboardMarkup(keyboard), media_key='desmontagem_menu_image')

async def show_dismantle_preview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = q.message.chat.id

    unique_item_id = q.data.split(':')[1]

    player_data = await player_manager.get_player_data(user_id) or {}
    inventory = player_data.get("inventory", {})
    item_to_dismantle = inventory.get(unique_item_id)

    if not item_to_dismantle:
        await q.answer("O item já não se encontra no seu inventário.", show_alert=True)
        await show_dismantle_list_callback(update, context)
        return

    base_id = item_to_dismantle.get("base_id")
    original_recipe = crafting_registry.get_recipe_by_item_id(base_id)

    if not original_recipe:
        await _safe_edit_or_send_with_media(q, context, chat_id, "Este item não pode ser desmontado (não foi encontrada a receita original).")
        return

    # Imagem
    item_media_key = None
    item_info = (game_data.ITEMS_DATA or {}).get(base_id, {})
    if item_info and item_info.get("media_key"):
        item_media_key = item_info["media_key"]
    final_media_key = item_media_key or 'desmontagem_menu_image'

    ITENS_NAO_RETORNAVEIS = {"nucleo_forja_fraco"}
    returned_materials = {}
    original_inputs = original_recipe.get("inputs", {})
    for material_id, needed_qty in original_inputs.items():
        if material_id in ITENS_NAO_RETORNAVEIS: continue
        return_qty = needed_qty // 2
        if return_qty == 0 and needed_qty > 0: return_qty = 1
        if return_qty > 0: returned_materials[material_id] = return_qty

    full_item_text = display_utils.formatar_item_para_exibicao(item_to_dismantle)
    caption_lines = [
        f"♻️ <b>Confirmar Desmontagem</b> ♻️",
        f"\nVocê está prestes a destruir o item:",
        full_item_text,
        "\n<b>Materiais a Receber (aproximadamente):</b>"
    ]
    if not returned_materials:
        caption_lines.append(" - Nenhum material será recuperado.")
    else:
        for mat_id, mat_qty in returned_materials.items():
            caption_lines.append(f"• {_fmt_item_line(mat_id, mat_qty)}")
    caption_lines.append("\n⚠️ <b>Esta ação é irreversível!</b>")

    caption = "\n".join(caption_lines)
    keyboard = [
        [InlineKeyboardButton("✅ Confirmar Desmontagem", callback_data=f"ref_dismantle_confirm:{unique_item_id}")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="ref_dismantle_list")]
    ]

    await _safe_edit_or_send_with_media(q, context, chat_id, caption, InlineKeyboardMarkup(keyboard), media_key=final_media_key)

async def confirm_dismantle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = q.message.chat.id
    unique_item_id = q.data.split(':')[1]

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
         await q.answer("Erro ao carregar dados do jogador!", show_alert=True)
         return

    result = await dismantle_engine.start_dismantle(pdata, unique_item_id)
    
    if isinstance(result, str):
        await context.bot.answer_callback_query(q.id, result, show_alert=True)
        return

    duration = result.get("duration_seconds", 60)
    item_name = result.get("item_name", "item")
    base_id = result.get("base_id")

    mins = _fmt_minutes_or_seconds(duration)
    sent_in_progress_message = await _safe_edit_or_send_with_media(
        q, context, chat_id,
        f"♻️ A desmontar <b>{item_name}</b>... O processo levará ~{mins}."
    )
    
    message_id_to_delete = None
    if sent_in_progress_message: 
        message_id_to_delete = sent_in_progress_message.message_id

    context.job_queue.run_once(
        finish_dismantle_job,
        when=duration,
        chat_id=chat_id,
        user_id=user_id,
        data={
            "unique_item_id": unique_item_id, 
            "item_name": item_name,
            "base_id": base_id,
            "message_id_to_delete": message_id_to_delete
        },
        name=f"dismantle_{user_id}"
    )

async def finish_dismantle_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id, chat_id = job.user_id, job.chat_id
    job_details = job.data
    
    # Tenta apagar a mensagem de "processando" se houver ID (Melhoria visual)
    message_id_to_delete = job_details.get("message_id_to_delete")
    if message_id_to_delete:
        try:
            await context.bot.delete_message(chat_id, message_id_to_delete)
        except Exception:
            pass

    # 1. Carrega dados do jogador
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        return

    # 2. Chama a engine (agora async) para processar a lógica
    # A engine retorna uma string em caso de erro, ou uma tupla (nome, materiais) em caso de sucesso
    result = await dismantle_engine.finish_dismantle(player_data, job_details)

    if isinstance(result, str):
        await context.bot.send_message(chat_id=chat_id, text=f"❗ Erro ao finalizar desmontagem: {result}")
        return

    # 3. Sucesso: Desempacota os dados
    item_name, returned_materials = result

    # 4. Salvamento de segurança (Garante que o estado 'idle' e inventário fiquem salvos)
    if player_data:
        await player_manager.save_player_data(user_id, player_data)

    # 5. Monta a mensagem de resposta
    caption_lines = [f"♻️ <b>{item_name}</b> foi desmontado com sucesso!", "\nVocê recuperou:"]
    
    if not returned_materials:
        caption_lines.append(" - Nenhum material foi recuperado.")
    else:
        for mat_id, mat_qty in returned_materials.items():
            # _fmt_item_line é uma função auxiliar interna do refining_handler.py
            caption_lines.append(f"• {_fmt_item_line(mat_id, mat_qty)}")

    keyboard = [
        [InlineKeyboardButton("⬅️ Voltar para Refino/Desmontagem", callback_data="ref_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=chat_id,
        text="\n".join(caption_lines),
        parse_mode="HTML",
        reply_markup=reply_markup
    )

async def ref_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = q.message.chat.id

    rid = q.data.replace("ref_sel_", "", 1)
    pdata = await player_manager.get_player_data(user_id) or {}
    prev = preview_refine(rid, pdata)

    if not prev:
        await q.answer("Receita inválida.", show_alert=True)
        return

    ins = "\n".join(_fmt_item_line(k, v) for k, v in (prev.get("inputs") or {}).items()) or "—"
    outs = "\n".join(_fmt_item_line(k, v) for k, v in (prev.get("outputs") or {}).items()) or "—"
    mins = _fmt_minutes_or_seconds(int(prev.get("duration_seconds", 0)))
    title = game_data.REFINING_RECIPES.get(rid, {}).get("display_name", rid)

    txt = (
        f"🛠️ <b>{title}</b>\n"
        f"⏳ <b>Tempo:</b> ~{mins}\n\n"
        f"📥 <b>Entrada:</b>\n{ins}\n\n"
        f"📦 <b>Saída:</b>\n{outs}"
    )

    kb: list[list[InlineKeyboardButton]] = []
    if prev.get("can_refine"):
        kb.append([InlineKeyboardButton("✅ Refinar", callback_data=f"ref_confirm_{rid}")])
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="ref_main")])

    await _safe_edit_or_send_with_media(q, context, chat_id, txt, InlineKeyboardMarkup(kb))

async def ref_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = q.message.chat.id

    rid = q.data.replace("ref_confirm_", "", 1)
    
    pdata = await player_manager.get_player_data(user_id) or {}
    state = pdata.get("player_state", {})

    if state.get("action") not in (None, "idle"):
        await q.answer("Você já está ocupado com outra ação!", show_alert=True)
        return

    res = await start_refine(pdata, rid)

    if isinstance(res, str):
        await q.answer(res, show_alert=True)
        return

    secs = int(res.get("duration_seconds", 0))
    mins = _fmt_minutes_or_seconds(secs)
    title = game_data.REFINING_RECIPES.get(rid, {}).get("display_name", rid)

    sent_in_progress_message = await _safe_edit_or_send_with_media(
        q, context, chat_id,
        f"🔧 Refinando <b>{title}</b>... (~{mins})"
    )

    message_id_to_delete = None
    if sent_in_progress_message:
        message_id_to_delete = sent_in_progress_message.message_id

    context.job_queue.run_once(
        finish_refine_job,
        when=secs,
        user_id=user_id,
        chat_id=chat_id,
        data={
            "rid": rid, 
            "message_id_to_delete": message_id_to_delete 
        }, 
        name=f"refining:{user_id}" 
    )

async def finish_refine_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id, chat_id = job.user_id, job.chat_id
    job_data = job.data
    
    message_id_to_delete = job_data.get("message_id_to_delete")
    if message_id_to_delete:
        try:
            await context.bot.delete_message(chat_id, message_id_to_delete)
        except Exception:
            pass

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        return

    res = await finish_refine(pdata)
    
    if isinstance(res, str):
        await context.bot.send_message(chat_id=chat_id, text=f"❗ {res}")
        return
    if not res:
        logger.warning(f"finish_refine_job para user {user_id}: finish_refine retornou {res}.")
        return

    outs = res.get("outputs") or {}
    xp_gained = res.get("xp_gained", 0)

    # --- SALVAMENTO (Sem Missões) ---
    await player_manager.save_player_data(user_id, pdata)
    
    lines = ["✅ <b>Refino concluído!</b>", "Você obteve:"]
    for k, v in outs.items():
        lines.append(f"• {_fmt_item_line(k, v)}")
        
    if xp_gained > 0:
        lines.append(f"✨ <b>+{xp_gained} XP</b> de Profissão")
        
    caption = "\n".join(lines)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫 à𝐬 𝐫𝐞𝐜𝐞𝐢𝐭𝐚𝐬", callback_data="ref_main")]
    ])

    specific_media_key = None
    if outs and len(outs) > 0:
        item_id_para_imagem = list(outs.keys())[0]
        item_info = (game_data.ITEMS_DATA or {}).get(item_id_para_imagem, {})
        specific_media_key = item_info.get("media_key")
    
    await _safe_send_with_media(
        context,
        chat_id,
        caption,
        kb,
        media_key=specific_media_key
    )

# =========================
# Definição dos Handlers
# =========================
async def noop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()

refining_main_handler = CallbackQueryHandler(
    refining_main_callback, 
    pattern=r"^(refining_main|ref_main|ref_main_PAGE_\d+)$"
)

noop_handler = CallbackQueryHandler(noop_callback, pattern=r"^noop_ref_page$")

ref_select_handler  = CallbackQueryHandler(ref_select_callback,  pattern=r"^ref_sel_[A-Za-z0-9_]+$")
ref_confirm_handler = CallbackQueryHandler(ref_confirm_callback,  pattern=r"^ref_confirm_[A-Za-z0-9_]+$")
dismantle_list_handler = CallbackQueryHandler(show_dismantle_list_callback, pattern=r"^ref_dismantle_list(:page:\d+)?$")
dismantle_preview_handler = CallbackQueryHandler(show_dismantle_preview_callback, pattern=r"^ref_dismantle_preview:[a-f0-9-]+$")
dismantle_confirm_handler = CallbackQueryHandler(confirm_dismantle_callback, pattern=r"^ref_dismantle_confirm:[a-f0-9-]+$")