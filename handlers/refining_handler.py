# handlers/refining_handler.py
import logging 
import telegram
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
)
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules import mission_manager
# Engines e dados
from modules import game_data, player_manager, file_ids
from modules.refining_engine import preview_refine, start_refine, finish_refine
from modules import player_manager, game_data, clan_manager, mission_manager
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
    media_key: str | None = None, # <-- Argumento opcional para a imagem
    fallback_key: str = "refino_universal", # <-- Imagem padrão se a 1ª falhar
):
    """
    Tenta enviar uma mídia com uma chave específica (media_key).
    Se falhar, tenta enviar com uma chave de fallback (fallback_key).
    Se tudo falhar, envia como texto simples.
    """
    keys_to_try = []
    if media_key:
        keys_to_try.append(media_key)
    if fallback_key:
        keys_to_try.append(fallback_key)

    media_sent = False
    for key in keys_to_try:
        fd = file_ids.get_file_data(key)
        if not fd or not fd.get("id"):
            continue # Pula para a próxima chave se esta não tiver ID

        media_id = fd["id"]
        ftype = (fd.get("type") or "photo").lower()
        
        try:
            if ftype == "video":
                await context.bot.send_video(
                    chat_id=chat_id, video=media_id, caption=caption, 
                    reply_markup=reply_markup, parse_mode="HTML"
                )
            else:
                await context.bot.send_photo(
                    chat_id=chat_id, photo=media_id, caption=caption, 
                    reply_markup=reply_markup, parse_mode="HTML"
                )
            media_sent = True
            break # Sucesso! Para o loop.
        except telegram.error.BadRequest as e:
            if "Wrong file identifier" in str(e):
                logger.warning(f"ID inválido para a chave '{key}'. Tentando a próxima.")
                continue # O ID é inválido, tenta a próxima chave
            else:
                logger.exception(f"BadRequest inesperado ao enviar mídia com chave '{key}'.")
                raise e # Erro inesperado, é melhor quebrar e investigar
    
    # Se, depois de todas as tentativas, nenhuma mídia foi enviada...
    if not media_sent:
        logger.info("Nenhuma mídia válida encontrada. Enviando como texto.")
        await context.bot.send_message(
            chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML"
        )

async def _try_edit_media(query, caption: str, reply_markup=None, media_key: str = "refino_universal") -> bool:
    """
    Tenta TROCAR a mídia da mensagem atual.
    AGORA aceita uma 'media_key' para usar mídias diferentes.
    """
    # Se nenhuma media_key for fornecida, ele usa a de refino como padrão.
    fd = file_ids.get_file_data(media_key)
    if not fd or not fd.get("id"):
        # Se a chave de mídia for inválida, tentamos editar só o texto e o teclado
        try:
            await query.edit_message_caption(caption=caption, reply_markup=reply_markup, parse_mode="HTML")
            return True
        except Exception:
            return False # Falhou, deixa a função principal reenviar

    media_id = fd["id"]
    ftype = (fd.get("type") or "photo").lower()
    try:
        if ftype == "video":
            await query.edit_message_media(
                media=InputMediaVideo(media=media_id, caption=caption, parse_mode="HTML"),
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_media(
                media=InputMediaPhoto(media=media_id, caption=caption, parse_mode="HTML"),
                reply_markup=reply_markup
            )
        return True
    except Exception as e:
        logger.debug("[_try_edit_media] Falhou: %s", e)
        return False


async def _safe_edit_or_send_with_media(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    caption: str,
    reply_markup=None,
    media_key: str = "refino_universal" # A chave de mídia que a função recebe
):
    """
    Tenta editar uma mensagem. Se falhar, apaga a antiga e envia uma nova
    usando a nossa função centralizada e robusta _safe_send_with_media.
    """
    # Tenta editar a mensagem atual com a nova mídia
    if await _try_edit_media(query, caption, reply_markup, media_key=media_key):
        return

    # Se a edição falhar, apaga a mensagem antiga
    try:
        await query.delete_message()
    except Exception:
        pass
    
    # 👇 AQUI ESTÁ A CORREÇÃO 👇
    # Em vez de chamar a função antiga, chamamos a nova, passando o media_key
    await _safe_send_with_media(
        context,
        chat_id,
        caption,
        reply_markup,
        media_key=media_key
    )

def _fmt_minutes_or_seconds(seconds: int) -> str:
    """Formata segundos para 'X min' ou 'Ys'."""
    return f"{round(seconds/60)} min" if seconds >= 60 else f"{int(seconds)}s"


def _fmt_item_line(item_id: str, qty: int) -> str:
    """
    Formata uma linha de item com emoji + nome + quantidade.
    Cai para um nome "bonito" mesmo sem ITEMS_DATA (robusto).
    """
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
# Handlers
# =========================

async def refining_main_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("\n>>> DENTRO DO refining_main_callback! O BOTÃO DE REFINO FOI ATIVADO! <<<\n", flush=True)
    """
    Lista TODAS as receitas de refino e agora também o botão para Desmontar.
    """
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = q.message.chat.id

    pdata = player_manager.get_player_data(user_id) or {}

    # Título atualizado para incluir a nova funcionalidade
    lines = ["🛠️ <b>Refino & Desmontagem</b>\n"]
    kb: list[list[InlineKeyboardButton]] = []

    # =========================================================
    # 👇 ADIÇÃO DO NOVO BOTÃO NO TOPO DO MENU 👇
    # =========================================================
    kb.append([InlineKeyboardButton("♻️ Desmontar Equipamento", callback_data="ref_dismantle_list")])
    # =========================================================

    any_recipe = False
    for rid, rec in game_data.REFINING_RECIPES.items():
        prev = preview_refine(rid, pdata)
        if not prev:
            continue
        any_recipe = True
        mins = _fmt_minutes_or_seconds(int(prev.get("duration_seconds", 0)))
        tag = "✅" if prev.get("can_refine") else "⛔"
        lines.append(f"{tag} <b>{rec.get('display_name', rid)}</b> • ⏳ ~{mins}")
        kb.append([
            InlineKeyboardButton(
                text=rec.get("display_name", rid),
                callback_data=f"ref_sel_{rid}",
            )
        ])

    if not any_recipe:
        lines.append("\nAinda não há receitas de refino cadastradas.")

    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="continue_after_action")])
    caption = "\n".join(lines)

    await _safe_edit_or_send_with_media(q, context, chat_id, caption, InlineKeyboardMarkup(kb))

# Em handlers/refining_handler.py

async def show_dismantle_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Mostra a lista paginada de itens que podem ser desmontados.
    """
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = q.message.chat.id

    player_data = player_manager.get_player_data(user_id) or {}

    # --- Lógica de Paginação ---
    page = 0
    # Verifica se o clique veio de um botão de página (ex: "ref_dismantle_list:page:1")
    if q.data and ':page:' in q.data:
        try:
            page = int(q.data.split(':page:')[1])
        except (ValueError, IndexError):
            page = 0

    # 1. Busca e filtra todos os itens desmontáveis (sua lógica original está ótima)
    inventory = player_data.get("inventory", {})
    equipped_uids = {v for k, v in player_data.get("equipment", {}).items()}
    
    all_dismantleable_items = []
    for item_uid, item_data in inventory.items():
        if isinstance(item_data, dict) and item_uid not in equipped_uids:
            base_id = item_data.get("base_id")
            if base_id and crafting_registry.get_recipe_by_item_id(base_id):
                all_dismantleable_items.append((item_uid, item_data))
    
    # Ordena alfabeticamente para uma exibição consistente
    all_dismantleable_items.sort(key=lambda x: x[1].get("display_name", ""))

    # 2. Calcula os itens para a página atual
    start_index = page * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    items_on_page = all_dismantleable_items[start_index:end_index]
    total_pages = (len(all_dismantleable_items) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    # 3. Monta a legenda (caption) - agora muito mais curta e limpa!
    caption = (
        "♻️ <b>Desmontar Equipamento</b>\n\n"
        "Selecione um item do seu inventário para desmontar. Itens equipados não são mostrados."
    )

    keyboard = []
    if not items_on_page:
        caption += "\n\nVocê não possui nenhum equipamento desmontável no seu inventário."
    else:
        # Cria um botão para cada item NA PÁGINA ATUAL
        for item_uid, item_data in items_on_page:
            item_name = item_data.get("display_name", "Item Desconhecido")
            keyboard.append([
                InlineKeyboardButton(
                    f"🔩 {item_name}",
                    callback_data=f"ref_dismantle_preview:{item_uid}"
                )
            ])

    # 4. Monta os botões de navegação da página
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

    # Envia a mensagem com a sua função segura
    await _safe_edit_or_send_with_media(q, context, chat_id, caption, InlineKeyboardMarkup(keyboard), media_key='desmontagem_menu_image')


# Em handlers/refining_handler.py

# Em handlers/refining_handler.py
# SUBSTITUA a sua função antiga por esta versão completa:

# Em handlers/refining_handler.py
# SUBSTITUA a sua função antiga por esta nova versão dinâmica:

async def show_dismantle_preview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Mostra os materiais recuperados e pede confirmação, AGORA usando a
    imagem específica do item a ser desmontado.
    """
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = q.message.chat.id

    unique_item_id = q.data.split(':')[1]

    player_data = player_manager.get_player_data(user_id) or {}
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

    # --- LÓGICA PARA OBTER A IMAGEM DO ITEM ---
    item_media_key = None
    # Primeiro, tentamos obter a chave da mídia a partir da informação base do item
    item_info = (game_data.ITEMS_DATA or {}).get(base_id, {})
    if item_info and item_info.get("media_key"):
        item_media_key = item_info["media_key"]
    
    # Se não encontrarmos uma imagem específica para o item, usamos a imagem padrão de desmontagem
    final_media_key = item_media_key or 'desmontagem_menu_image'
    # --- FIM DA LÓGICA DA IMAGEM ---

    # (O resto da lógica para calcular materiais continua igual)
    ITENS_NAO_RETORNAVEIS = {
        "nucleo_forja_fraco", 
        # Adicione aqui outros IDs se necessário, por exemplo: "martelo_de_ferreiro"
    }

    returned_materials = {}
    original_inputs = original_recipe.get("inputs", {})
    for material_id, needed_qty in original_inputs.items():
        # >>> A MÁGICA ACONTECE AQUI <<<
        # Se o material estiver na nossa lista negra, nós simplesmente o ignoramos.
        if material_id in ITENS_NAO_RETORNAVEIS:
            continue # Pula para o próximo item do loop

        return_qty = needed_qty // 2
        if return_qty == 0 and needed_qty > 0:
            return_qty = 1
        if return_qty > 0:
            returned_materials[material_id] = return_qty
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

    # A chamada final agora usa a nossa chave de mídia dinâmica
    await _safe_edit_or_send_with_media(q, context, chat_id, caption, InlineKeyboardMarkup(keyboard), media_key=final_media_key)

async def confirm_dismantle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    É chamada pelo botão 'Confirmar Desmontagem'.
    Inicia a desmontagem e agenda a sua finalização.
    """
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = q.message.chat.id
    unique_item_id = q.data.split(':')[1]

    # Chama a nova função de INÍCIO do nosso motor de desmontagem
    result = dismantle_engine.start_dismantle(user_id, unique_item_id)
    
    if isinstance(result, str):
        # Se o resultado for uma string, é uma mensagem de erro
        await context.bot.answer_callback_query(q.id, result, show_alert=True)
        return

    # Se o início foi bem-sucedido, o resultado é um dicionário com os detalhes do job
    duration = result.get("duration_seconds", 60)
    item_name = result.get("item_name", "item")
    base_id = result.get("base_id")
    
    # Agenda a execução da função de finalização para quando o tempo acabar
    context.job_queue.run_once(
        finish_dismantle_job,
        when=duration,
        chat_id=chat_id,
        user_id=user_id,
        # AQUI ESTÁ A CORREÇÃO: Adicionamos o base_id aos dados do job.
        data={
            "unique_item_id": unique_item_id, 
            "item_name": item_name,
            "base_id": base_id
        },
        name=f"dismantle_{user_id}"
    )
    
    # Envia uma mensagem a informar que o processo começou
    mins = _fmt_minutes_or_seconds(duration)
    await _safe_edit_or_send_with_media(
        q, context, chat_id,
        f"♻️ A desmontar <b>{item_name}</b>... O processo levará ~{mins}."
    )

    # Adicione esta nova função ao handlers/refining_handler.py

# VERSÃO CORRIGIDA
async def finish_dismantle_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id, chat_id = job.user_id, job.chat_id
    
    # AQUI ESTÁ A CORREÇÃO: Usamos job.data em vez de ler o player_state.
    # 'job.data' contém a informação "congelada" do momento em que a ação começou.
    job_details = job.data
    
    result = dismantle_engine.finish_dismantle(user_id, job_details)
    
    if isinstance(result, str):
        await context.bot.send_message(chat_id=chat_id, text=f"❗ Erro ao finalizar desmontagem: {result}")
        return
        
    item_name, returned_materials = result
    
    # Integração com Missões
    player_data = player_manager.get_player_data(user_id)
    if player_data:
        mission_manager.update_mission_progress(player_data, 'DISMANTLE', details={'count': 1})
        clan_id = player_data.get("clan_id")
        if clan_id:
            # Precisamos de passar o 'context' para a função de missão de clã
            await clan_manager.update_guild_mission_progress(
                clan_id=clan_id,
                mission_type='DISMANTLE',
                details={'count': 1},
                context=context
            )
        player_manager.save_player_data(user_id, player_data)

    # Mensagem de Sucesso
    caption_lines = [f"♻️ <b>{item_name}</b> foi desmontado com sucesso!", "\nVocê recuperou:"]
    if not returned_materials:
        caption_lines.append(" - Nenhum material foi recuperado.")
    else:
        for mat_id, mat_qty in returned_materials.items():
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
    """
    Mostra o detalhe da receita selecionada + botão de confirmar.
    """
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = q.message.chat.id

    rid = q.data.replace("ref_sel_", "", 1)
    pdata = player_manager.get_player_data(user_id) or {}
    prev = preview_refine(rid, pdata)

    if not prev:
        await q.answer("Receita inválida.", show_alert=True)
        return

    # Entradas com emoji/nomes bonitos
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
    """
    Confirma o refino e agenda a finalização.
    """
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = q.message.chat.id

    rid = q.data.replace("ref_confirm_", "", 1)
    pdata = player_manager.get_player_data(user_id) or {}
    state = pdata.get("player_state", {})

    if state.get("action") not in (None, "idle"):
        await q.answer("Você já está ocupado com outra ação!", show_alert=True)
        return

    res = start_refine(user_id, rid)
    if isinstance(res, str):
        await q.answer(res, show_alert=True)
        return

    secs = int(res.get("duration_seconds", 0))
    mins = _fmt_minutes_or_seconds(secs)
    title = game_data.REFINING_RECIPES.get(rid, {}).get("display_name", rid)

    await _safe_edit_or_send_with_media(
        q, context, chat_id,
        f"🔧 Refinando <b>{title}</b>... (~{mins})"
    )

    # Agenda a finalização
    context.job_queue.run_once(
        finish_refine_job,
        when=secs,
        user_id=user_id,
        chat_id=chat_id,
        data={"rid": rid},
    )



async def finish_refine_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id, chat_id = job.user_id, job.chat_id

    # --- Bloco 1: Lógica do Jogo (permanece igual) ---
    res = finish_refine(user_id)
    if isinstance(res, str):
        await context.bot.send_message(chat_id=chat_id, text=f"❗ {res}")
        return
    if not res:
        return

    outs = res.get("outputs") or {}
    player_data = player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")

    if player_data and outs:
        for item_id, quantity in outs.items():
            mission_manager.update_mission_progress(
                player_data, 'REFINE', details={'item_id': item_id, 'quantity': quantity}
            )
            if clan_id:
                await clan_manager.update_guild_mission_progress(
                    clan_id=clan_id, mission_type='REFINE',
                    details={'item_id': item_id, 'count': quantity}, context=context
                )
        player_manager.save_player_data(user_id, player_data)
    
    # --- Bloco 2: Preparação da Mensagem (permanece igual) ---
    lines = ["✅ <b>Refino concluído!</b>", "Você obteve:"]
    for k, v in outs.items():
        lines.append(f"• {_fmt_item_line(k, v)}")
    
    caption = "\n".join(lines)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫 à𝐬 𝐫𝐞𝐜𝐞𝐢𝐭𝐚𝐬", callback_data="ref_main")]
    ])

    # --- Bloco 3: Lógica de Envio de Mídia (AGORA SUPER SIMPLES) ---
    specific_media_key = None
    if outs:
        item_id_para_imagem = list(outs.keys())[0]
        item_info = (game_data.ITEMS_DATA or {}).get(item_id_para_imagem, {})
        specific_media_key = item_info.get("media_key") # Pode ser None se não houver
    
    # Fazemos uma única chamada para a nossa função robusta!
    await _safe_send_with_media(
        context,
        chat_id,
        caption,
        kb,
        media_key=specific_media_key # Tenta esta chave primeiro
        # Se specific_media_key for None ou inválida, a função usará 'refino_universal'
    )
        # =========================
refining_main_handler = CallbackQueryHandler(refining_main_callback, pattern=r"^(refining_main|ref_main)$")
ref_select_handler    = CallbackQueryHandler(ref_select_callback,   pattern=r"^ref_sel_[A-Za-z0-9_]+$")
ref_confirm_handler   = CallbackQueryHandler(ref_confirm_callback,  pattern=r"^ref_confirm_[A-Za-z0-9_]+$")
dismantle_list_handler = CallbackQueryHandler(show_dismantle_list_callback, pattern=r"^ref_dismantle_list(:page:\d+)?$")
dismantle_preview_handler = CallbackQueryHandler(show_dismantle_preview_callback, pattern=r"^ref_dismantle_preview:[a-f0-9-]+$")
dismantle_confirm_handler = CallbackQueryHandler(confirm_dismantle_callback, pattern=r"^ref_dismantle_confirm:[a-f0-9-]+$")