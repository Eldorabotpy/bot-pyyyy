# handlers/admin/force_daily.py
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import logging

# IMPORTANTE: Usamos o utilitário de admin para passar na auditoria
from handlers.admin.utils import ensure_admin
from handlers.jobs import force_grant_daily_crystals

logger = logging.getLogger(__name__)

async def force_daily_crystals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Força a execução do job de cristais diários.
    """
    # [CORREÇÃO] Removemos o acesso direto ao ID. 
    # O ensure_admin faz a verificação de segurança internamente.
    if not await ensure_admin(update):
        return

    await update.message.reply_text("⏳ Iniciando distribuição diária forçada...")

    try:
        # Executa a função de job
        await force_grant_daily_crystals(context)
        await update.message.reply_text("✅ Distribuição executada com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao forçar daily_crystals: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Erro na execução: {e}")

force_daily_handler = CommandHandler("forcar_cristais", force_daily_crystals)