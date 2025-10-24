# handlers/admin/premium_panel.py

from __future__ import annotations
import os
import logging
from datetime import datetime, timezone
from typing import Tuple, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)
from modules import player_manager, game_data # game_data importado caso precise dos tiers
from handlers.admin.utils import ensure_admin
from modules.player.premium import PremiumManager # Importa a classe correta

logger = logging.getLogger(__name__)

# ---- States da conversa ----
(ASK_NAME,) = range(1) # Simplificado, só precisamos de um estado principal
ADMIN_ID = int(os.getenv("ADMIN_ID"))
# ---------------------------------------------------------
# Utilidades
# ---------------------------------------------------------
def _fmt_date(iso: Optional[str]) -> str:
    # ... (código existente) ...
    if not iso: return "Permanente" # Ou "—" se preferir
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    except Exception: return iso

def _capfirst(s: Optional[str]) -> str:
    # ... (código existente) ...
     if not s: return "—"
     s = str(s)
     return s[0:1].upper() + s[1:]


def _get_user_target(context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    # ... (código existente) ...
    return context.user_data.get("premium_target_uid")

def _set_user_target(context: ContextTypes.DEFAULT_TYPE, uid: int, name: str) -> None:
    # Armazena também o nome para referência
    context.user_data["premium_target_uid"] = int(uid)
    context.user_data["premium_target_name"] = name

def _panel_text(user_id: int, pdata: dict) -> str:
    name = pdata.get("character_name") or f"Jogador {user_id}"
    
    # Usa o PremiumManager para obter informações consistentes
    premium = PremiumManager(pdata)
    tier = premium.tier
    tier_disp = game_data.PREMIUM_TIERS.get(tier, {}).get("display_name", "Free") if tier else "Free"
    exp_date = premium.expiration_date
    exp_disp = _fmt_date(exp_date.isoformat()) if exp_date else "Permanente"

    return (
        "🔥 <b>Painel Premium</b>\n\n"
        f"<b>Usuário:</b> {name} <code>({user_id})</code>\n"
        f"<b>Tier Atual:</b> {tier_disp}\n"
        f"<b>Expira em:</b> {exp_disp}\n\n"
        "Selecione uma ação:"
    )

def _panel_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [ # Linha para definir/mudar o tier
            InlineKeyboardButton("🆓 Free", callback_data="prem_tier:free"),
            InlineKeyboardButton("⭐ Premium", callback_data="prem_tier:premium"),
            InlineKeyboardButton("💎 VIP", callback_data="prem_tier:vip"),
            InlineKeyboardButton("👑 Lenda", callback_data="prem_tier:lenda"),
        ],
        [ # Linha para adicionar dias (mantendo o tier atual)
            InlineKeyboardButton("➕ 1 Dia", callback_data="prem_add:1"),
            InlineKeyboardButton("➕ 7 Dias", callback_data="prem_add:7"),
            InlineKeyboardButton("➕ 30 Dias", callback_data="prem_add:30"),
        ],
        [ # Ação de remover completamente
             InlineKeyboardButton("🚫 Remover Premium", callback_data="prem_clear"),
        ],
        [ # Navegação da conversa
            InlineKeyboardButton("🔎 Trocar Usuário", callback_data="prem_change_user"),
            InlineKeyboardButton("❌ Fechar Painel", callback_data="prem_close"),
        ],
    ]
    return InlineKeyboardMarkup(rows)

# ---------------------------------------------------------
# Entrada e Gestão da Conversa
# ---------------------------------------------------------
async def _entry_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia a conversa pedindo o nome do jogador."""
    if not await ensure_admin(update): return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    prompt = (
        "🔥 <b>Painel Premium</b>\n\n"
        "Envie o <b>User ID</b> ou o <b>nome exato do personagem</b>.\n"
        "Use /cancelar para sair."
    )
    keyboard = [[InlineKeyboardButton("❌ Fechar", callback_data="prem_close")]] # Botão fechar inicial
    try:
        await query.edit_message_text(prompt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception: # Fallback se a edição falhar (ex: msg deletada)
        if query.message: # Tenta enviar nova msg se a original existir
             await context.bot.send_message(chat_id=query.message.chat.id, text=prompt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    # Limpa dados de alvo anterior, se houver
    context.user_data.pop("premium_target_uid", None)
    context.user_data.pop("premium_target_name", None)
    return ASK_NAME # Estado para esperar ID ou nome

async def _receive_name_or_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe ID ou Nome, encontra o jogador e mostra o painel."""
    if not await ensure_admin(update): return ConversationHandler.END

    target_input = (update.message.text or "").strip()
    user_id, pdata = None, None

    # Tenta encontrar por ID primeiro
    try:
        user_id_int = int(target_input)
        pdata_found = player_manager.get_player_data(user_id_int)
        if pdata_found:
            user_id = user_id_int
            pdata = pdata_found
    except ValueError:
        # Se não for ID, tenta por nome
        found_by_name = player_manager.find_player_by_name(target_input)
        if found_by_name:
            user_id, pdata = found_by_name

    if not pdata:
        await update.message.reply_text(
            "❌ Jogador não encontrado. Tente novamente com o <b>User ID</b> ou o <b>nome exato</b>.\n"
            "Use /cancelar para sair.", parse_mode="HTML"
        )
        return ASK_NAME # Continua esperando input

    # Encontrou! Guarda o alvo e mostra o painel
    player_name = pdata.get("character_name", f"ID: {user_id}")
    _set_user_target(context, user_id, player_name)

    text = _panel_text(user_id, pdata)
    await update.message.reply_text(text, reply_markup=_panel_keyboard(), parse_mode="HTML")

    return ASK_NAME # Permanece no estado principal para receber ações dos botões

# ---------------------------------------------------------
# Ações do painel (Callbacks)
# ---------------------------------------------------------
async def _action_set_tier(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Define ou altera o tier do jogador alvo."""
    if not await ensure_admin(update): return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    target_uid = _get_user_target(context)
    if not target_uid:
        await query.answer("Erro: Alvo não definido. Use 'Trocar Usuário'.", show_alert=True)
        return ASK_NAME

    new_tier = (query.data or "prem_tier:free").split(":", 1)[1]

    try:
        pdata = player_manager.get_player_data(target_uid)
        if not pdata: raise ValueError("Dados do jogador não encontrados.")

        premium = PremiumManager(pdata)
        premium.set_tier(new_tier) # Usa o método set_tier

        player_manager.save_player_data(target_uid, premium.player_data)

        # Recarrega dados para exibir painel atualizado
        updated_pdata = player_manager.get_player_data(target_uid) or pdata
        text = _panel_text(target_uid, updated_pdata)
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=_panel_keyboard())

    except Exception as e:
         logger.error(f"Erro ao definir tier premium para {target_uid}: {e}", exc_info=True)
         await query.answer(f"❌ Erro ao definir tier: {e}", show_alert=True)

    return ASK_NAME

async def _action_add_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Adiciona dias à assinatura premium do jogador alvo."""
    if not await ensure_admin(update): return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    target_uid = _get_user_target(context)
    if not target_uid:
        await query.answer("Erro: Alvo não definido. Use 'Trocar Usuário'.", show_alert=True)
        return ASK_NAME

    try:
        days_str = (query.data or "prem_add:1").split(":", 1)[1]
        days = int(days_str)
        if days <= 0: raise ValueError("Dias devem ser positivos")
    except (ValueError, IndexError):
        await query.answer("Valor de dias inválido.", show_alert=True)
        return ASK_NAME

    await query.answer(f"Adicionando {days} dias...")

    try:
        pdata = player_manager.get_player_data(target_uid)
        if not pdata: raise ValueError("Dados do jogador não encontrados.")

        current_tier = pdata.get("premium_tier") or "premium"
        if current_tier == "free": current_tier = "premium"

        premium = PremiumManager(pdata)
        premium.grant_days(tier=current_tier, days=days) # Usa grant_days

        player_manager.save_player_data(target_uid, premium.player_data)

        updated_pdata = player_manager.get_player_data(target_uid) or pdata
        text = _panel_text(target_uid, updated_pdata)
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=_panel_keyboard())

    except Exception as e:
         logger.error(f"Erro ao adicionar dias premium para {target_uid}: {e}", exc_info=True)
         # Tenta editar a msg com erro, fallback para answer
         try: await query.edit_message_text(f"❌ Ocorreu um erro ao adicionar dias: {e}")
         except Exception: await query.answer(f"❌ Erro ao adicionar dias: {e}", show_alert=True)

    return ASK_NAME

async def _action_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Revoga o status premium do jogador alvo."""
    if not await ensure_admin(update): return ConversationHandler.END
    query = update.callback_query
    target_uid = _get_user_target(context)
    target_name = context.user_data.get("premium_target_name", f"ID {target_uid}") # Pega nome do context
    if not target_uid:
        await query.answer("Erro: Alvo não definido. Use 'Trocar Usuário'.", show_alert=True)
        return ASK_NAME

    await query.answer(f"Revogando premium de {target_name}...")

    try:
        pdata = player_manager.get_player_data(target_uid)
        if not pdata: raise ValueError("Dados do jogador não encontrados.")

        premium = PremiumManager(pdata)
        premium.revoke() # Chama o método revoke()

        player_manager.save_player_data(target_uid, premium.player_data)

        # Recarrega dados para exibir painel atualizado
        updated_pdata = player_manager.get_player_data(target_uid) or pdata
        text = _panel_text(target_uid, updated_pdata)
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=_panel_keyboard())

    except Exception as e:
         logger.error(f"Erro ao revogar premium para {target_uid}: {e}", exc_info=True)
         try: await query.edit_message_text(f"❌ Ocorreu um erro ao revogar o premium: {e}")
         except Exception: await query.answer(f"❌ Erro ao revogar: {e}", show_alert=True)

    # Não limpa user_data aqui, permite continuar gerenciando o mesmo user
    return ASK_NAME

async def _action_change_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Volta para a etapa de pedir nome/ID."""
    if not await ensure_admin(update): return ConversationHandler.END
    # Reutiliza a função de entrada para pedir o nome novamente
    return await _entry_from_callback(update, context)

async def _action_close(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Fecha o painel deletando a mensagem."""
    query = update.callback_query
    await query.answer()
    try:
        await query.delete_message()
    except Exception: pass # Ignora se não conseguir deletar
    context.user_data.clear() # Limpa dados da conversa
    return ConversationHandler.END

async def _cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Fallback para comando /cancel."""
    await update.message.reply_text("Operação do Painel Premium cancelada.")
    context.user_data.clear()
    return ConversationHandler.END

# ---------------------------------------------------------
# /premium_user <user_id> (opcional – atalho)
# ---------------------------------------------------------
async def _premium_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Atalho para abrir o painel direto num user ID."""
    if not await ensure_admin(update): return
    if not context.args:
        await update.message.reply_text("Uso: /premium_user <user_id>")
        return
    try: uid = int(context.args[0])
    except Exception:
        await update.message.reply_text("ID inválido.")
        return

    pdata = player_manager.get_player_data(uid)
    if not pdata:
        await update.message.reply_text("Jogador não encontrado.")
        return

    player_name = pdata.get("character_name", f"ID: {uid}")
    _set_user_target(context, uid, player_name) # Define o alvo
    await update.message.reply_text(_panel_text(uid, pdata), parse_mode="HTML", reply_markup=_panel_keyboard())
    # NOTA: Isto NÃO inicia a ConversationHandler. As ações podem não funcionar.
    # É melhor guiar o admin para usar o /admin e o painel.

# ---------------------------------------------------------
# Exports
# ---------------------------------------------------------
premium_panel_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(_entry_from_callback, pattern=r'^admin_premium$'),
    ],
    states={
        ASK_NAME: [ # Estado principal onde esperamos nome ou ação de botão
            MessageHandler(filters.TEXT & ~filters.COMMAND, _receive_name_or_id),
            CallbackQueryHandler(_action_set_tier, pattern=r"^prem_tier:(free|premium|vip|lenda)$"),
            CallbackQueryHandler(_action_add_days, pattern=r"^prem_add:(\d+)$"),
            CallbackQueryHandler(_action_clear, pattern=r"^prem_clear$"),
            CallbackQueryHandler(_action_change_user, pattern=r"^prem_change_user$"),
            CallbackQueryHandler(_action_close, pattern=r"^prem_close$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancelar", _cmd_cancel), # Comando /cancelar
        CallbackQueryHandler(_action_close, pattern=r"^prem_close$"), # Botão fechar como fallback também
    ],
    name="premium_panel_conv",
    persistent=False,
    # block=False # Descomentar se precisar interagir com outros handlers durante a conversa
)

# Comando de atalho (mantido, mas com a ressalva de não iniciar a conversa)
premium_command_handler = CommandHandler("premium_user", _premium_user_cmd, filters=filters.User(ADMIN_ID))