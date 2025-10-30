# Em handlers/admin/reset_panel.py

from __future__ import annotations
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CommandHandler,
)

from modules import player_manager

logger = logging.getLogger(__name__)
ADMIN_ID = int(os.getenv("ADMIN_ID"))
# --- Estados da Conversa ---
MAIN_MENU, ASKING_PLAYER_RESPEC, ASKING_PLAYER_IDLE, CONFIRM_ALL, CONFIRM_IDLE = range(5)

# --- Funções Auxiliares (Lógica de Reset) ---
def _reset_points_one(p: dict) -> int:
    try:
        refunded = player_manager.reset_stats_and_refund_points(p)
        totals = player_manager.get_player_total_stats(p)
        max_hp = int(totals.get("max_hp", p.get("max_hp", 50)))
        p["current_hp"] = max(1, min(int(p.get("current_hp", max_hp)), max_hp))
        return int(refunded)
    except Exception as e:
        logger.warning("[ADM RESET] Falha no reset de pontos: %s", e)
        return 0

def _reset_class_one(p: dict) -> None:
    for k in ("class", "class_key", "class_tag"):
        if k in p: p[k] = None

def _reset_prof_one(p: dict) -> None:
    p["profession"] = {}

async def _resolve_user_id(text: str) -> int | None:
    text = (text or "").strip()
    if text.isdigit(): return int(text)
    uid, _ = await player_manager.find_player_by_name_norm(text) or (None, None)
    return uid

# --- Funções da Conversa ---

# Ponto de Entrada: Mostra o menu principal de reset
async def _entry_point(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
    text = (
        "🔧 <b>Painel de Reset (ADM)</b>\n\n"
        "Selecione uma ferramenta de reset. Use com cuidado."
    )
    keyboard = [
        [InlineKeyboardButton("🔄 Resetar Estado (Destravar)", callback_data="reset_action_idle")],
        [InlineKeyboardButton("🎯 Zerar Pontos (por jogador)", callback_data="reset_action_points")],
        [InlineKeyboardButton("✨ Zerar Classe (por jogador)", callback_data="reset_action_class")],
        [InlineKeyboardButton("🛠️ Zerar Profissão (por jogador)", callback_data="reset_action_prof")],
        [InlineKeyboardButton("🧹 Zerar Pontos (TODOS)", callback_data="reset_action_points_all")],
        [InlineKeyboardButton("⬅️ Voltar ao Menu Admin", callback_data="admin_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Se veio de um botão, edita a mensagem.
    if query:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")
    # Se veio de uma mensagem de texto (update.message existe), envia uma nova.
    elif update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")
        
    return MAIN_MENU

# Pede o ID do jogador para resetar STATS/CLASSE/PROF
async def _ask_player_for_respec(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    action = query.data.split('_')[-1] # 'points', 'class', 'prof'
    context.user_data['reset_action'] = action
    
    await query.edit_message_text(
        "Envie o <b>ID, @username ou nome exato</b> do personagem para zerar sua/seus " + action.upper(),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="reset_back_to_main")]])
    )
    return ASKING_PLAYER_RESPEC

# Pede o ID do jogador para destravar (RESET DE ESTADO)
async def _ask_player_for_idle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Envie o <b>ID, @username ou nome exato</b> do personagem para destravar (resetar estado para 'livre').",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="reset_back_to_main")]])
    )
    return ASKING_PLAYER_IDLE

# Recebe o texto, encontra o jogador e executa o RESPEC
async def _receive_player_for_respec(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    target_id = await _resolve_user_id(update.message.text)
    action = context.user_data.get('reset_action')

    if not target_id or not action:
        await update.message.reply_text("❌ Jogador não encontrado ou ação inválida. Tente novamente.")
        return ASKING_PLAYER_RESPEC

    pdata = await player_manager.get_player_data(target_id)
    if not pdata:
        await update.message.reply_text("❌ Jogador não encontrado.")
        return ASKING_PLAYER_RESPEC

    summary = []
    if action == 'points':
        rec = _reset_points_one(pdata)
        summary.append(f"pontos (recuperados: {rec})")
    elif action == 'class':
        _reset_class_one(pdata)
        summary.append("classe")
    elif action == 'prof':
        _reset_prof_one(pdata)
        summary.append("profissão")

    await player_manager.save_player_data(target_id, pdata)
    await update.message.reply_text(f"✅ Reset de `{', '.join(summary)}` aplicado para o jogador `{target_id}`.")
    
    context.user_data.pop('reset_action', None)
    # Volta para o menu principal de reset
    await _entry_point(update, context)
    return MAIN_MENU

# Recebe o texto, encontra o jogador e pede CONFIRMAÇÃO para destravar
async def _receive_player_for_idle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    target_id = await _resolve_user_id(update.message.text)
    if not target_id:
        await update.message.reply_text("❌ Jogador não encontrado. Tente novamente.")
        return ASKING_PLAYER_IDLE

    pdata = await player_manager.get_player_data(target_id)
    if not pdata:
        await update.message.reply_text("❌ Jogador não encontrado.")
        return ASKING_PLAYER_IDLE
        
    context.user_data['reset_target_id'] = target_id
    char_name = pdata.get("character_name", "N/A")
    current_action = (pdata.get("player_state") or {}).get("action", "livre")

    text = (f"❓ Confirmação\n\n<b>Jogador:</b> {char_name} ({target_id})\n<b>Estado Atual:</b> <code>{current_action}</code>\n\n"
            "Deseja forçar o estado para <b>'livre' (idle)</b>?")
    keyboard = [
        [InlineKeyboardButton("✅ Sim, destravar", callback_data="reset_confirm_idle")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="reset_back_to_main")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return CONFIRM_IDLE

# Executa o reset de estado para 'idle'
async def _execute_idle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    target_id = context.user_data.get('reset_target_id')
    if not target_id:
        await query.edit_message_text("❌ Erro: Alvo perdido. Comece novamente.")
        return ConversationHandler.END

    pdata = await player_manager.get_player_data(target_id)
    pdata["player_state"] = {"action": "idle"}
    await player_manager.save_player_data(target_id, pdata)
    
    await query.edit_message_text(f"✅ Estado do jogador <code>{target_id}</code> foi resetado para 'livre'.")
    context.user_data.pop('reset_target_id', None)
    
    # Notifica o jogador, se possível
    try: await context.bot.send_message(chat_id=target_id, text="ℹ️ Um administrador destravou seu personagem.")
    except Exception: pass
    
    return ConversationHandler.END

# Lógica para resetar pontos de TODOS
async def _reset_all_points_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    text = ("⚠️ **CONFIRMAÇÃO FINAL** ⚠️\n\nVocê tem certeza que quer resetar os pontos de "
            "<b>TODOS OS JOGADORES</b> do bot? Esta ação não pode ser desfeita.")
    keyboard = [
        [InlineKeyboardButton("🔴 SIM, TENHO CERTEZA", callback_data="reset_execute_points_all")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="reset_back_to_main")]
    ]
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRM_ALL

async def _reset_all_points_execute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("Processando... Isso pode levar um tempo.", show_alert=True)
    
    changed = 0
    total_recovered = 0
    for uid, pdata in player_manager.iter_players():
        total_recovered += _reset_points_one(pdata)
        await player_manager.save_player_data(uid, pdata)
        changed += 1
    
    await query.edit_message_text(f"✅ Pontos de <b>{changed}</b> jogadores foram resetados. Total recuperado: {total_recovered} pontos.")
    return ConversationHandler.END


# --- Montagem do ConversationHandler ---
reset_panel_conversation_handler = ConversationHandler(
    entry_points=[
        # Pega o clique do botão "Reset/Respec" no menu admin principal
        CallbackQueryHandler(_entry_point, pattern=r'^admin_reset_menu$')
    ],
    states={
        MAIN_MENU: [
            CallbackQueryHandler(_ask_player_for_idle_reset, pattern=r'^reset_action_idle$'),
            CallbackQueryHandler(_ask_player_for_respec, pattern=r'^(reset_action_points|reset_action_class|reset_action_prof)$'),
            CallbackQueryHandler(_reset_all_points_confirm, pattern=r'^reset_action_points_all$'),
        ],
        ASKING_PLAYER_RESPEC: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, _receive_player_for_respec),
            CallbackQueryHandler(_entry_point, pattern=r'^reset_back_to_main$'),
        ],
        ASKING_PLAYER_IDLE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, _receive_player_for_idle_reset),
            CallbackQueryHandler(_entry_point, pattern=r'^reset_back_to_main$'),
        ],
        CONFIRM_ALL: [
            CallbackQueryHandler(_reset_all_points_execute, pattern=r'^reset_execute_points_all$'),
            CallbackQueryHandler(_entry_point, pattern=r'^reset_back_to_main$'),
        ],
        CONFIRM_IDLE: [
            CallbackQueryHandler(_execute_idle_reset, pattern=r'^reset_confirm_idle$'),
            CallbackQueryHandler(_entry_point, pattern=r'^reset_back_to_main$'),
        ]
    },
    fallbacks=[
        # O botão "Voltar ao Menu Admin" encerra esta conversa e o admin_handler assume
        CallbackQueryHandler(ConversationHandler.END, pattern=r'^admin_main$'),
        CommandHandler("cancelar", ConversationHandler.END)
    ],
    name="admin_reset_panel_conv",
    persistent=False,
)