# handlers/admin/respec.py
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import os
from modules import player_manager

ADMIN_ID = int(os.getenv("ADMIN_ID"))
HELP_TEXT = (
    "Uso:\n"
    "/respec_user <user_id>  — reseta e devolve pontos do jogador pelo ID\n"
    "/respec_user <nome>     — reseta pelo nome exato do personagem\n"
)

async def respec_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or user.id != ADMIN_ID:
        await update.effective_message.reply_text("⛔ Apenas admin pode usar este comando.")
        return

    if not context.args:
        await update.effective_message.reply_text(HELP_TEXT)
        return

    arg = " ".join(context.args).strip()

    # tenta por ID
    target_id = None
    try:
        target_id = int(arg)
    except Exception:
        target_id = None

    pdata = None
    uid = None

    if target_id is not None:
        pdata = player_manager.get_player_data(target_id)
        uid = target_id
    else:
        # tenta por nome
        found = player_manager.find_player_by_name(arg)
        if found:
            uid, pdata = found

    if not pdata or uid is None:
        await update.effective_message.reply_text("❓ Jogador não encontrado. Use ID ou nome exato.")
        return

    # garante baseline, reseta e reembolsa
    player_manager._ensure_base_stats_block(pdata)
    refunded = player_manager.reset_stats_and_refund_points(pdata)

    # persiste (no teu save precisa do user_id)
    player_manager.save_player_data(uid, pdata)

    char_name = pdata.get("character_name") or str(uid)
    await update.effective_message.reply_text(
        f"✅ RESPEC concluído para **{char_name}** (ID: {uid}).\n"
        f"• Pontos devolvidos: {refunded}\n"
        f"• Stats base restaurados ao baseline."
    )

# handler exportável
respec_user_handler = CommandHandler("respec_user", respec_user_cmd)
