# handlers/admin_handler.py
# (VERSÃO FINAL: Blindado contra imports legados de jobs e event_manager)

from __future__ import annotations
import io
import logging
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional, Union

# --- Imports do Telegram ---
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler
)
from telegram.constants import ParseMode
from modules.auth_utils import get_current_player_id

# --- Imports de Banco e Utils ---
from bson import ObjectId
from modules.auth_utils import get_current_player_id
from handlers.admin.utils import ensure_admin, ADMIN_LIST, parse_hybrid_id

# --- Imports de Funcionalidades Administrativas ---
from handlers.admin.grant_item import grant_item_conv_handler
from handlers.admin.generate_equip import generate_equip_conv_handler
from handlers.admin.file_id_conv import file_id_conv_handler
from handlers.admin.premium_panel import premium_panel_handler
from handlers.admin.reset_panel import reset_panel_conversation_handler
from handlers.admin.grant_skill import grant_skill_conv_handler
from handlers.admin.grant_skin import grant_skin_conv_handler
from handlers.admin.player_management_handler import player_management_conv_handler
from handlers.admin.debug_skill import debug_skill_handler

from modules.player.core import (
    get_player_data,
    save_player_data,
    clear_player_cache,
    clear_all_player_cache,
    users_collection,
    _player_cache
)
from modules.player.queries import (
    find_player_by_name,
    iter_players,
    delete_player
)
from modules.player.inventory import add_item_to_inventory
from modules.player.stats import (
    allowed_points_for_level,
    compute_spent_status_points,
    reset_stats_and_refund_points
)

from modules import game_data
from ui.ui_renderer import render_menu, notify
from ui.ui_renderer import render_text

# ----------------------------------------------------------------------
# ✅ BLINDAGEM: imports legados do handlers.jobs (evita ImportError)
# ----------------------------------------------------------------------
from handlers.jobs import reset_pvp_season

try:
    from handlers.jobs import distribute_kingdom_defense_ticket_job
except Exception:
    distribute_kingdom_defense_ticket_job = None

try:
    from handlers.jobs import force_grant_daily_crystals
except Exception:
    force_grant_daily_crystals = None

# ----------------------------------------------------------------------
# ✅ BLINDAGEM: event_manager pode não existir em ambientes sem o módulo
# ----------------------------------------------------------------------
try:
    from kingdom_defense.engine import event_manager
except Exception:
    event_manager = None

logger = logging.getLogger(__name__)
HTML = ParseMode.HTML

# --- CONSTANTES DE ESTADO ---
(SELECT_CACHE_ACTION, ASK_USER_FOR_CACHE_CLEAR) = range(2)
(SELECT_TEST_ACTION, ASK_WAVE_NUMBER) = range(2, 4)
(ASK_DELETE_ID, CONFIRM_DELETE_ACTION) = range(4, 6)
ASK_GHOST_CLAN_ID = 6
(ASK_OLD_ID_CHANGE, ASK_NEW_ID_CHANGE, CONFIRM_ID_CHANGE) = range(7, 10)

# =========================================================
# HELPERS
# =========================================================

async def _safe_answer(update: Update):
    if q := update.callback_query:
        try:
            await q.answer()
        except:
            pass

async def _safe_edit_text(update, context, text, reply_markup=None):
    # "scope" do admin: tudo do painel admin fica no mesmo fluxo (uma tela só)
    await render_text(
        update,
        context,
        text,
        reply_markup=reply_markup,
        scope="admin",
        parse_mode=HTML,
        delete_previous_on_send=True,
        allow_edit=True,
    )


# =========================================================
# UI CLEAN HELPERS (1 mensagem por fluxo)
# =========================================================

async def _ui_try_delete(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int) -> None:
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

def _ui_get_chat_and_msg(update: Update):
    if update.callback_query and update.callback_query.message:
        return update.callback_query.message.chat_id, update.callback_query.message
    return update.effective_chat.id, None

async def ui_render_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup=None) -> None:
    """
    Regra:
    - Callback: tenta editar a mensagem do menu.
      Se falhar (BadRequest etc.), deleta e envia uma nova.
    - Comando/mensagem: apaga o último menu do bot (se existir) e envia um novo.
    Salva o menu atual em context.user_data["last_menu_msg_id"].
    """
    chat_id, msg = _ui_get_chat_and_msg(update)

    # Responde callback para tirar "loading..."
    if update.callback_query:
        try:
            await update.callback_query.answer()
        except Exception:
            pass

    # Caso callback: tenta editar primeiro
    if msg is not None:
        try:
            await msg.edit_text(text=text, parse_mode=HTML, reply_markup=reply_markup, disable_web_page_preview=True)
            context.user_data["last_menu_msg_id"] = msg.message_id
            return
        except Exception:
            # se não der para editar: apaga e manda novo
            await _ui_try_delete(context, chat_id, msg.message_id)

    # Não-callback ou fallback: apaga menu anterior do bot
    last_id = context.user_data.get("last_menu_msg_id")
    if last_id:
        await _ui_try_delete(context, chat_id, last_id)

    sent = await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=HTML, reply_markup=reply_markup, disable_web_page_preview=True)
    context.user_data["last_menu_msg_id"] = sent.message_id

async def _send_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await render_text(
        update,
        context,
        "🎛️ <b>Painel do Admin</b>\nEscolha uma opção:",
        reply_markup=_admin_menu_kb(),
        scope="admin",
        parse_mode=HTML,
        delete_previous_on_send=True,
        allow_edit=True
    )



# =========================================================
# MENUS
# =========================================================

def _admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 𝔼𝕟𝕥𝕣𝕖𝕘𝕒𝕣 𝕀𝕥𝕖𝕟𝕤", callback_data="admin_grant_item")],
        [InlineKeyboardButton("🛠️ 𝔾𝕖𝕣𝕒𝕣 𝔼𝕢𝕦𝕚𝕡𝕒𝕞𝕖𝕟𝕥𝕠", callback_data="admin_generate_equip")],
        [InlineKeyboardButton("📚 𝔼𝕟𝕤𝕚𝕟𝕒𝕣 𝕊𝕜𝕚𝕝𝕝", callback_data="admin_grant_skill")],
        [InlineKeyboardButton("🎨 𝔼𝕟𝕥𝕣𝕖𝕘𝕒𝕣 𝕊𝕜𝕚𝕟", callback_data="admin_grant_skin")],
        [InlineKeyboardButton("✏️ 𝐄𝐝𝐢𝐭𝐚𝐫 𝐉𝐨𝐠𝐚𝐝𝐨𝐫", callback_data="admin_edit_player")],
        [InlineKeyboardButton("👥 𝔾𝕖𝕣𝕖𝕟𝕔𝕚𝕒𝕣 𝕁𝕠𝕘𝕒𝕕𝕠𝕣𝕖𝕤", callback_data="admin_pmanage_main")],
        [InlineKeyboardButton("🚀 𝐌𝐈𝐆𝐑𝐀𝐑/CLONAR 𝐈𝐃", callback_data="admin_change_id_start")],
        [InlineKeyboardButton("🏚️ Limpar Clã Fantasma", callback_data="admin_fix_clan_start")],
        [InlineKeyboardButton("💀 𝐃𝐄𝐋𝐄𝐓𝐀𝐑 𝐂𝐎𝐍𝐓𝐀", callback_data="admin_delete_start")],
        [InlineKeyboardButton("🔁 𝔽𝕠𝕣ç𝕒𝕣 𝔻𝕚á𝕣𝕚𝕠𝕤", callback_data="admin_force_daily")],
        [InlineKeyboardButton("💎 𝐕𝐞𝐧𝐝𝐞𝐫 𝐆𝐞𝐦𝐚𝐬", callback_data="admin_sell_gems"),
         InlineKeyboardButton("🔥 Remover Gemas", callback_data="admin_remove_gems")],
        [InlineKeyboardButton("👑 ℙ𝕣𝕖𝕞𝕚𝕦𝕞", callback_data="admin_premium")],
        [InlineKeyboardButton("🎉 𝔾𝕖𝕣𝕖𝕟𝕔𝕚𝕒𝕣 𝔼𝕧𝕖𝕟𝕥𝕠𝕤", callback_data="admin_event_menu")],
        [InlineKeyboardButton("🔬 𝕋𝕖𝕤𝕥𝕖𝕤 𝕕𝕖 𝔼𝕧𝕖𝕟𝕥𝕠", callback_data="admin_test_menu")],
        [InlineKeyboardButton("📁 𝔾𝕖𝕣𝕖𝕟𝕔𝕚𝕒𝕣 𝔽𝕚𝕝𝕖 𝕀𝔻𝕤", callback_data="admin_file_ids")],
        [InlineKeyboardButton("🧹 ℝ𝕖𝕤𝕖𝕥/ℝ𝕖𝕤𝕡𝕖𝕔", callback_data="admin_reset_menu")],
        [InlineKeyboardButton("🧽 𝕃𝕚𝕞𝕡𝕒𝕣 ℂ𝕒𝕔𝕙𝕖", callback_data="admin_clear_cache")],
        [InlineKeyboardButton("ℹ️ 𝐀𝐣𝐮𝐝𝐚", callback_data="admin_help")]
    ])

def _admin_event_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎟️ Entregar Ticket", callback_data="admin_event_force_ticket")],
        [InlineKeyboardButton("📨 FORÇAR JOB TICKETS", callback_data="admin_force_ticket_job")],
        [InlineKeyboardButton("▶️ Iniciar Evento", callback_data="admin_event_force_start")],
        [InlineKeyboardButton("⏹️ Finalizar Evento", callback_data="admin_event_force_end")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin_main")],
    ])

def _admin_test_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Iniciar Wave X", callback_data="test_start_at_wave")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin_main")],
    ])

async def ui_render(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup=None, media: dict | None = None) -> None:
    """
    media esperado:
      {"file_id": "...", "file_type": "photo"|"video"|"animation"|"document"}
    Se não houver media ou for inválida, envia texto normalmente.
    Para callback, tenta editar texto/caption; se falhar, deleta e reenvia.
    """
    chat_id, msg = _ui_get_chat_and_msg(update)

    if update.callback_query:
        try:
            await update.callback_query.answer()
        except Exception:
            pass

    # Se não tem media válida, cai no texto puro
    file_id = (media or {}).get("file_id")
    ftype = ((media or {}).get("file_type") or "").lower()

    if not file_id or ftype not in ("photo", "video", "animation", "document"):
        return await ui_render_text(update, context, text, reply_markup=reply_markup)

    # Callback: tenta editar caption (quando existir)
    if msg is not None:
        try:
            await msg.edit_caption(caption=text, parse_mode=HTML, reply_markup=reply_markup)
            context.user_data["last_menu_msg_id"] = msg.message_id
            return
        except Exception:
            await _ui_try_delete(context, chat_id, msg.message_id)

    # Apaga menu anterior
    last_id = context.user_data.get("last_menu_msg_id")
    if last_id:
        await _ui_try_delete(context, chat_id, last_id)

    try:
        if ftype == "photo":
            sent = await context.bot.send_photo(chat_id=chat_id, photo=file_id, caption=text, parse_mode=HTML, reply_markup=reply_markup)
        elif ftype == "video":
            sent = await context.bot.send_video(chat_id=chat_id, video=file_id, caption=text, parse_mode=HTML, reply_markup=reply_markup)
        elif ftype == "animation":
            sent = await context.bot.send_animation(chat_id=chat_id, animation=file_id, caption=text, parse_mode=HTML, reply_markup=reply_markup)
        else:
            sent = await context.bot.send_document(chat_id=chat_id, document=file_id, caption=text, parse_mode=HTML, reply_markup=reply_markup)

        context.user_data["last_menu_msg_id"] = sent.message_id
        return
    except Exception:
        # fallback absoluto: texto
        return await ui_render_text(update, context, text, reply_markup=reply_markup)

# =========================================================
# HANDLERS GERAIS
# =========================================================

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): 
        return
    await update.message.reply_text(
        "🎛️ <b>Painel do Admin</b>\nEscolha uma opção:",
        reply_markup=_admin_menu_kb(),
        parse_mode=HTML,
    )

async def _handle_admin_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): 
        return
    if update.callback_query:
        await update.callback_query.answer()

    text = "🎛️ <b>Painel do Admin</b>\nEscolha uma opção:"
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=_admin_menu_kb(), parse_mode=HTML)
    else:
        await update.message.reply_text(text, reply_markup=_admin_menu_kb(), parse_mode=HTML)

async def get_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    game_id = get_current_player_id(update, context)
    text = (
        f"<b>🕵️ INFO DO JOGADOR</b>\n"
        f"--------------------------\n"
        f"🎮 <b>ID do Jogo:</b> <code>{game_id}</code>\n"
        f"🏠 <b>Chat ID:</b> <code>{chat_id}</code>"
    )
    await update.message.reply_text(text, parse_mode=HTML)

async def _handle_admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): 
        return
    await _safe_answer(update)
    help_text = "ℹ️ <b>Ajuda</b>\n/fixme - Reseta seus status\n/mydata - Baixa JSON\n/find_player <nome> - Busca ID\n/delete_player <id> - Deleta conta"
    await _safe_edit_text(update, context, help_text,
                          InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_main")]]))

# =========================================================
# EVENTOS
# =========================================================

async def _handle_admin_event_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): 
        return
    await _safe_answer(update)
    await _safe_edit_text(update, context, "🎉 <b>Gerenciamento de Eventos</b>", _admin_event_menu_kb())

async def _handle_force_start_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): 
        return
    if event_manager is None:
        await update.callback_query.answer("event_manager indisponível.", show_alert=True)
        return

    await update.callback_query.answer("Iniciando...")
    result = await event_manager.start_event()
    msg = result.get("success") or result.get("error") or "Erro desconhecido"

    await ui_render_text(
        update, context,
        f"✅ <b>Event Start</b>\n{msg}",
        reply_markup=_admin_event_menu_kb()
    )


async def _handle_force_end_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): 
        return
    if event_manager is None:
        await update.callback_query.answer("event_manager indisponível.", show_alert=True)
        return

    query = update.callback_query
    await query.answer("Finalizando...")
    result = await event_manager.end_event(context)
    msg = result.get("success") or result.get("error") or "Erro desconhecido"
    await query.message.reply_text(f"Event End: {msg}")

async def _handle_force_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): 
        return
    query = update.callback_query
    uid = get_current_player_id(update, context)
    pdata = await get_player_data(uid)
    if pdata:
        add_item_to_inventory(pdata, 'ticket_defesa_reino', 1)
        await save_player_data(uid, pdata)
        await query.answer("Ticket entregue!", show_alert=True)

async def _handle_force_ticket_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): 
        return
    query = update.callback_query
    await query.answer("Executando job...")

    if distribute_kingdom_defense_ticket_job is None:
        await query.message.reply_text("⚠️ Job legado de tickets não existe mais (foi substituído por claim diário).")
        return

    # Cria um objeto Job fake para compatibilidade com a função (caso ela exista)
    context.job = type('Job', (object,), {'data': {"event_time": "FORCE"}, 'name': 'admin_force'})
    await distribute_kingdom_defense_ticket_job(context)
    await query.message.reply_text("Tickets distribuídos.")

async def _handle_admin_force_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): 
        return
    await _safe_answer(update)

    if force_grant_daily_crystals is None:
        await _safe_edit_text(
            update, context,
            "⚠️ O comando legado de 'forçar cristais diários' foi removido.\n"
            "Agora as entradas/eventos são via CLAIM diário no menu Eventos.",
            InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_main")]])
        )
        return

    await force_grant_daily_crystals(context)
    await _safe_edit_text(
        update, context,
        "✅ Cristais diários entregues.",
        InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admin_main")]])
    )

async def force_daily_crystals_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): 
        return

    if force_grant_daily_crystals is None:
        await update.message.reply_text("⚠️ Função legada removida. Use o claim diário no menu Eventos.")
        return

    await force_grant_daily_crystals(context)
    await update.message.reply_text("Cristais entregues.")

async def _reset_pvp_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): 
        return
    await reset_pvp_season(context)
    await update.message.reply_text("PvP resetado.")

# =========================================================
# DEBUG E PLAYER FIX
# =========================================================

async def fix_my_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): 
        return
    user_id = get_current_player_id(update, context)
    player_data = await get_player_data(user_id)
    if not player_data: 
        return

    try:
        player_data['xp'] = 0
        allowed = allowed_points_for_level(player_data)
        spent = compute_spent_status_points(player_data)
        player_data['stat_points'] = max(0, allowed - spent)
        await save_player_data(user_id, player_data)
        await update.message.reply_text("✅ Status corrigidos!")
    except Exception as e:
        await update.message.reply_text(f"Erro: {e}")

async def my_data_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): 
        return
    user_id = get_current_player_id(update, context)
    player_data = await get_player_data(user_id)
    if not player_data: 
        return

    pdata_copy = player_data.copy()
    if '_id' in pdata_copy:
        pdata_copy['_id'] = str(pdata_copy['_id'])

    try:
        data_str = json.dumps(pdata_copy, indent=2, ensure_ascii=False)
        input_file = io.BytesIO(data_str.encode('utf-8'))
        await update.message.reply_document(document=input_file, filename=f"dados_{user_id}.json")
    except Exception as e:
        await update.message.reply_text(f"Erro: {e}")

async def inspect_item_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): 
        return
    if not context.args: 
        return
    item_id = context.args[0]
    info = (game_data.ITEMS_DATA or {}).get(item_id)
    await update.message.reply_text(f"INFO {item_id}: {info}")

async def debug_player_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): 
        return
    try:
        uid = parse_hybrid_id(context.args[0])
    except:
        return

    in_cache = str(uid) in _player_cache
    in_new = False

    if users_collection is not None:
        try:
            search_id = ObjectId(uid) if ObjectId.is_valid(uid) else uid
            in_new = await asyncio.to_thread(users_collection.find_one, {"_id": search_id}) is not None
        except:
            pass

    await update.message.reply_text(
        f"🔍 <b>Debug Info</b>\n🆔 ID: <code>{uid}</code>\n💾 Cache: {'✅' if in_cache else '❌'}\n☁️ DB Users: {'✅' if in_new else '❌'}",
        parse_mode=HTML
    )

async def find_player_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): 
        return
    if not context.args: 
        return
    name = " ".join(context.args)
    found = await find_player_by_name(name)
    if found:
        await update.message.reply_text(
            f"Encontrado: {found[1].get('character_name')}\nID: <code>{found[0]}</code>",
            parse_mode=HTML
        )
    else:
        await update.message.reply_text("Não encontrado.")

async def hard_respec_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): 
        return
    msg = await update.message.reply_text("⏳ Iniciando Reset Total...")
    count = 0
    async for uid, _ in iter_players():
        pdata = await get_player_data(uid)
        if pdata:
            await reset_stats_and_refund_points(pdata)
            await save_player_data(uid, pdata)
            count += 1
            if count % 50 == 0:
                await asyncio.sleep(0.1)
    clear_all_player_cache()
    await msg.edit_text(f"✅ Reset Concluído! {count} jogadores.")

async def admin_clean_market_names(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Funcionalidade temporariamente desativada na migração.")

async def clean_clan_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): 
        return
    if not context.args: 
        return
    uid = parse_hybrid_id(context.args[0])
    pdata = await get_player_data(uid)
    if pdata:
        pdata['clan_id'] = None
        await save_player_data(uid, pdata)
        await clear_player_cache(uid)
        await update.message.reply_text("Clã limpo.")

async def fix_deleted_clan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): 
        return
    clan_id = context.args[0]
    count = 0
    async for uid, pdata in iter_players():
        if pdata.get('clan_id') == clan_id:
            pdata['clan_id'] = None
            await save_player_data(uid, pdata)
            count += 1
    await update.message.reply_text(f"Clã fantasma removido de {count} jogadores.")

# === 🛠️ DEFINIÇÃO DA FUNÇÃO QUE FALTAVA ===
async def fix_premium_dates_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Varre todos os jogadores e corrige o formato da data de expiração do VIP.
    Converte objetos datetime do MongoDB para strings ISO compatíveis com JSON.
    """
    if not await ensure_admin(update): 
        return

    msg = await update.message.reply_text("⏳ Verificando e corrigindo datas VIP...")
    count = 0
    fixed = 0

    async for uid, pdata in iter_players():
        count += 1

        raw_date = pdata.get("premium_expires_at")
        tier = pdata.get("premium_tier", "free")

        if not raw_date:
            continue

        new_date_str = None
        needs_fix = False

        if isinstance(raw_date, datetime):
            needs_fix = True
            if raw_date.tzinfo is None:
                raw_date = raw_date.replace(tzinfo=timezone.utc)
            new_date_str = raw_date.isoformat()

        elif isinstance(raw_date, str):
            try:
                datetime.fromisoformat(raw_date)
            except ValueError:
                needs_fix = True
                new_date_str = None
                if tier != "free":
                    pass

        if needs_fix:
            pdata["premium_expires_at"] = new_date_str
            await save_player_data(uid, pdata)
            fixed += 1

        if count % 50 == 0:
            await asyncio.sleep(0.01)

    await msg.edit_text(f"✅ Concluído!\n👥 Verificados: {count}\n🔧 Corrigidos: {fixed}")

async def _delete_player_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update): 
        return
    uid = parse_hybrid_id(context.args[0])
    if await delete_player(uid):
        await update.message.reply_text("Deletado.")
    else:
        await update.message.reply_text("Não encontrado.")

# =========================================================
# CONVERSATIONS (CACHE, DELETE, CLONE, TEST)
# =========================================================

# --- Cache ---
async def _cache_entry_point(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update): 
        return ConversationHandler.END
    await _safe_edit_text(update, context, "Opções de Cache:", InlineKeyboardMarkup([
        [InlineKeyboardButton("Limpar UM", callback_data="cache_clear_one")],
        [InlineKeyboardButton("Limpar TUDO", callback_data="cache_clear_all_confirm")],
        [InlineKeyboardButton("Cancelar", callback_data="admin_main")]
    ]))
    return SELECT_CACHE_ACTION

async def _cache_ask_for_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _safe_edit_text(update, context, "Envie o ID:")
    return ASK_USER_FOR_CACHE_CLEAR

async def _cache_clear_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = parse_hybrid_id(update.message.text)
    if uid:
        await clear_player_cache(uid)
    await update.message.reply_text("Cache limpo.")
    await _send_admin_menu(update, context)
    return ConversationHandler.END

async def _cache_confirm_clear_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _safe_edit_text(update, context, "Confirmar limpar TUDO?", InlineKeyboardMarkup([
        [InlineKeyboardButton("Sim", callback_data="cache_do_clear_all")],
        [InlineKeyboardButton("Não", callback_data="admin_main")]
    ]))
    return SELECT_CACHE_ACTION

async def _cache_do_clear_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    clear_all_player_cache()
    await _safe_edit_text(update, context, "Cache global limpo.")
    await _send_admin_menu(update.effective_chat.id, context)
    return ConversationHandler.END

async def _cache_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _send_admin_menu(update, context)
    return ConversationHandler.END

clear_cache_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(_cache_entry_point, pattern=r"^admin_clear_cache$")],
    states={
        SELECT_CACHE_ACTION: [
            CallbackQueryHandler(_cache_ask_for_user, pattern="^cache_clear_one$"),
            CallbackQueryHandler(_cache_confirm_clear_all, pattern="^cache_clear_all_confirm$"),
            CallbackQueryHandler(_cache_do_clear_all, pattern="^cache_do_clear_all$"),
            CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$"),
        ],
        ASK_USER_FOR_CACHE_CLEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_LIST), _cache_clear_user)],
    },
    fallbacks=[
        CommandHandler("cancelar", _cache_cancel, filters=filters.User(ADMIN_LIST)),
        CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$")
    ],
    per_message=False
)

# --- Test Event ---
async def _handle_admin_test_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update): 
        return ConversationHandler.END
    await _safe_edit_text(update, context, "Painel de Teste", _admin_test_menu_kb())
    return SELECT_TEST_ACTION

async def _test_ask_wave(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _safe_edit_text(update, context, "Digite a Wave:")
    return ASK_WAVE_NUMBER

async def _test_start_wave(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        wave = int(update.message.text)
    except:
        wave = 1

    if event_manager is None:
        await update.message.reply_text("event_manager indisponível.")
        return ConversationHandler.END

    event_manager.start_event_at_wave(wave)
    await update.message.reply_text(f"Iniciado na wave {wave}")
    return ConversationHandler.END

async def _test_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _send_admin_menu(update.effective_chat.id, context)
    return ConversationHandler.END

test_event_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(_handle_admin_test_menu, pattern=r"^admin_test_menu$")],
    states={
        SELECT_TEST_ACTION: [
            CallbackQueryHandler(_test_ask_wave, pattern="^test_start_at_wave$"),
            CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$")
        ],
        ASK_WAVE_NUMBER: [MessageHandler(filters.TEXT & filters.User(ADMIN_LIST), _test_start_wave)],
    },
    fallbacks=[
        CommandHandler("cancelar", _test_cancel),
        CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$")
    ],
    per_message=False
)

# --- Delete Player ---
async def _delete_entry_point(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update): 
        return ConversationHandler.END
    await _safe_edit_text(update, context, "Envie ID para DELETAR:")
    return ASK_DELETE_ID

async def _delete_resolve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = parse_hybrid_id(update.message.text)
    if not uid:
        return ConversationHandler.END
    context.user_data['del_id'] = uid
    await update.message.reply_text(
        f"Confirmar deletar {uid}?",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("SIM", callback_data="confirm_delete_yes")]])
    )
    return CONFIRM_DELETE_ACTION

async def _delete_perform_btn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = context.user_data.get('del_id')
    await delete_player(uid)
    await _safe_edit_text(update, context, "Deletado.")
    return ConversationHandler.END

async def _delete_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _send_admin_menu(update, context)
    return ConversationHandler.END

delete_player_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(_delete_entry_point, pattern=r"^admin_delete_start$")],
    states={
        ASK_DELETE_ID: [MessageHandler(filters.TEXT & filters.User(ADMIN_LIST), _delete_resolve)],
        CONFIRM_DELETE_ACTION: [
            CallbackQueryHandler(_delete_perform_btn, pattern="^confirm_delete_yes$"),
            CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$")
        ]
    },
    fallbacks=[
        CommandHandler("cancelar", _delete_cancel),
        CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$")
    ]
)

# --- Fix Clan ---
async def _fix_clan_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update): 
        return ConversationHandler.END
    await _safe_edit_text(update, context, "Digite o ID do Clã:")
    return ASK_GHOST_CLAN_ID

async def _fix_clan_perform(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    clan_id = update.message.text
    count = 0
    async for uid, pdata in iter_players():
        if pdata.get('clan_id') == clan_id:
            pdata['clan_id'] = None
            await save_player_data(uid, pdata)
            count += 1
    await update.message.reply_text(f"Limpo de {count} jogadores.")
    return ConversationHandler.END

fix_clan_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(_fix_clan_entry, pattern=r"^admin_fix_clan_start$")],
    states={ASK_GHOST_CLAN_ID: [MessageHandler(filters.TEXT & filters.User(ADMIN_LIST), _fix_clan_perform)]},
    fallbacks=[CommandHandler("cancelar", _delete_cancel), CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$")]
)

# --- Change ID ---
async def _change_id_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await ensure_admin(update): 
        return ConversationHandler.END
    await _safe_edit_text(update, context, "Digite ID ORIGEM (User ID):")
    return ASK_OLD_ID_CHANGE

async def _change_id_ask_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['old_id'] = parse_hybrid_id(update.message.text)
    await update.message.reply_text("Digite ID DESTINO (Novo User ID):")
    return ASK_NEW_ID_CHANGE

async def _change_id_confirm_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['new_id'] = parse_hybrid_id(update.message.text)
    await update.message.reply_text(
        "Confirmar clonagem/migração?",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("SIM", callback_data="do_change_id_yes")]])
    )
    return CONFIRM_ID_CHANGE

async def _change_id_perform(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    old = context.user_data['old_id']
    new = context.user_data['new_id']

    pdata = None
    if users_collection is not None:
        try:
            oid = ObjectId(old) if ObjectId.is_valid(old) else old
            pdata = await asyncio.to_thread(users_collection.find_one, {"_id": oid})
        except:
            pass

    if pdata:
        try:
            if users_collection is not None:
                final_oid = ObjectId(new) if ObjectId.is_valid(new) else new
                pdata['_id'] = final_oid

                await asyncio.to_thread(users_collection.replace_one, {"_id": final_oid}, pdata, upsert=True)

                old_oid = ObjectId(old) if ObjectId.is_valid(old) else old
                await asyncio.to_thread(users_collection.delete_one, {"_id": old_oid})

            await _safe_edit_text(update, context, "✅ ID Trocado (Sistema Novo).")
        except Exception as e:
            await _safe_edit_text(update, context, f"❌ Erro ao gravar: {e}")
    else:
        await _safe_edit_text(update, context, "Erro: Conta original não encontrada no sistema novo.")
    return ConversationHandler.END

change_id_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(_change_id_entry, pattern=r"^admin_change_id_start$")],
    states={
        ASK_OLD_ID_CHANGE: [MessageHandler(filters.TEXT & filters.User(ADMIN_LIST), _change_id_ask_new)],
        ASK_NEW_ID_CHANGE: [MessageHandler(filters.TEXT & filters.User(ADMIN_LIST), _change_id_confirm_step)],
        CONFIRM_ID_CHANGE: [
            CallbackQueryHandler(_change_id_perform, pattern="^do_change_id_yes$"),
            CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$")
        ]
    },
    fallbacks=[CommandHandler("cancelar", _delete_cancel)]
)

# =========================================================
# REGISTRO
# =========================================================

admin_command_handler = CommandHandler("admin", admin_command, filters=filters.User(ADMIN_LIST))
delete_player_handler = CommandHandler("delete_player", _delete_player_command, filters=filters.User(ADMIN_LIST))
inspect_item_handler = CommandHandler("inspect_item", inspect_item_command, filters=filters.User(ADMIN_LIST))
force_daily_handler = CommandHandler("forcar_cristais", force_daily_crystals_cmd, filters=filters.User(ADMIN_LIST))
my_data_handler = CommandHandler("mydata", my_data_command, filters=filters.User(ADMIN_LIST))
reset_pvp_now_handler = CommandHandler("resetpvpnow", _reset_pvp_now_command, filters=filters.User(ADMIN_LIST))
find_player_handler = CommandHandler("find_player", find_player_command, filters=filters.User(ADMIN_LIST))
debug_player_handler = CommandHandler("debug_player", debug_player_data, filters=filters.User(ADMIN_LIST))
get_id_command_handler = CommandHandler("get_id", get_id_command)
fixme_handler = CommandHandler("fixme", fix_my_character, filters=filters.User(ADMIN_LIST))
hard_respec_all_handler = CommandHandler("hard_respec_all", hard_respec_all_command, filters=filters.User(ADMIN_LIST))
clean_market_handler = CommandHandler("limpar_mercado", admin_clean_market_names, filters=filters.User(ADMIN_LIST))
clean_clan_handler = CommandHandler("limpar_cla", clean_clan_status_command, filters=filters.User(ADMIN_LIST))
fix_ghost_clan_handler = CommandHandler("fix_cla_fantasma", fix_deleted_clan_command, filters=filters.User(ADMIN_LIST))
fix_premium_handler = CommandHandler("fix_premium", fix_premium_dates_command, filters=filters.User(ADMIN_LIST))

admin_main_handler = CallbackQueryHandler(_handle_admin_main, pattern="^admin_main$")
admin_force_daily_callback_handler = CallbackQueryHandler(_handle_admin_force_daily, pattern="^admin_force_daily$")
admin_event_menu_handler = CallbackQueryHandler(_handle_admin_event_menu, pattern="^admin_event_menu$")
admin_force_start_handler = CallbackQueryHandler(_handle_force_start_event, pattern="^admin_event_force_start$")
admin_force_end_handler = CallbackQueryHandler(_handle_force_end_event, pattern="^admin_event_force_end$")
admin_force_ticket_handler = CallbackQueryHandler(_handle_force_ticket, pattern="^admin_event_force_ticket$")
admin_force_ticket_job_handler = CallbackQueryHandler(_handle_force_ticket_job, pattern="^admin_force_ticket_job$")
admin_help_handler = CallbackQueryHandler(_handle_admin_help, pattern="^admin_help$")

all_admin_handlers = [
    admin_command_handler,
    delete_player_handler,
    inspect_item_handler,
    force_daily_handler,
    find_player_handler,
    debug_player_handler,
    get_id_command_handler,
    fixme_handler,
    admin_main_handler,

    admin_force_daily_callback_handler,
    admin_event_menu_handler,
    admin_force_start_handler,
    admin_force_end_handler,
    admin_force_ticket_handler,
    admin_force_ticket_job_handler,
    clear_cache_conv_handler,
    test_event_conv_handler,
    grant_item_conv_handler,
    my_data_handler,
    reset_pvp_now_handler,
    generate_equip_conv_handler,
    file_id_conv_handler,
    premium_panel_handler,
    reset_panel_conversation_handler,
    grant_skill_conv_handler,
    grant_skin_conv_handler,
    player_management_conv_handler,
    admin_help_handler,
    delete_player_conv_handler,
    hard_respec_all_handler,
    clean_clan_handler,
    change_id_conv_handler,
    fix_ghost_clan_handler,
    fix_clan_conv_handler,
    debug_skill_handler,
    clean_market_handler,
    fix_premium_handler
]
