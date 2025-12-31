# pvp/tournament_admin.py

import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from . import tournament_system
from modules.auth_utils import get_current_player_id
# Configure seus IDs de admin aqui (ou importe do seu config.py)
ADMIN_IDS = [
    7262799478, # Seu ID
    
]

logger = logging.getLogger(__name__)

async def check_admin(update: Update) -> bool:
    """Verificação de segurança simples."""
    user_id = get_current_player_id(update, 
                                    )
    if user_id not in ADMIN_IDS:
        # Opcional: Avisar que não tem permissão ou apenas ignorar
        # await update.message.reply_text("⛔ Apenas o Rei pode convocar torneios.")
        return False
    return True

async def cmd_abrir_torneio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando: /torneio_abrir"""
    if not await check_admin(update): return
    
    chat_id = update.effective_chat.id
    # Chama a função de abrir inscrições do sistema
    await tournament_system.abrir_inscricoes(context, chat_id)
    
    # Opcional: Apagar o comando do admin pra ficar limpo
    try: await update.message.delete()
    except: pass

async def cmd_gerar_chave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando: /torneio_gerar"""
    if not await check_admin(update): return
    
    chat_id = update.effective_chat.id
    # Fecha inscrições e mostra quem luta com quem
    await tournament_system.fechar_inscricoes_e_gerar_chave(context, chat_id)

async def cmd_proxima_luta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando: /torneio_proxima"""
    if not await check_admin(update): return
    
    chat_id = update.effective_chat.id
    # Chama os próximos lutadores
    await tournament_system.chamar_proxima_luta(context, chat_id)

async def cmd_reset_torneio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de Emergência: /torneio_reset"""
    if not await check_admin(update): return
    
    # Força o status para idle e limpa tudo (caso bugue)
    data = tournament_system.get_tournament_data()
    data["status"] = "idle"
    data["bracket"] = []
    data["participants"] = []
    data["round_winners"] = []
    tournament_system.save_tournament_data(data)
    
    # Cancela timer se houver
    if tournament_system.CURRENT_MATCH_STATE["task"]:
        tournament_system.CURRENT_MATCH_STATE["task"].cancel()
    
    tournament_system.CURRENT_MATCH_STATE["active"] = False
    
    await update.message.reply_text("⚠️ **Torneio resetado forçadamente!**", parse_mode="Markdown")

# Função para exportar os handlers prontos para o main.py
def get_tournament_admin_handlers():
    return [
        CommandHandler("torneio_abrir", cmd_abrir_torneio),
        CommandHandler("torneio_gerar", cmd_gerar_chave),
        CommandHandler("torneio_proxima", cmd_proxima_luta),
        CommandHandler("torneio_reset", cmd_reset_torneio),
    ]