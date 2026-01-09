# handlers/autohunt_handler.py
# (VERSÃO LIMPA: Roteador para o Engine Central)

import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

# ✅ IMPORTAÇÃO CRÍTICA: Traz a lógica do Engine (Fonte da Verdade)
# Não reescrevemos a função aqui, apenas a importamos.
# Isso garante compatibilidade total com o sistema de recuperação (Watchdog).
from modules.auto_hunt_engine import start_auto_hunt

logger = logging.getLogger(__name__)

# ==============================================================================
# 🧩 HANDLER DE BOTÃO (PARSER INTELIGENTE)
# ==============================================================================
async def _autohunt_button_parser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Recebe o clique no botão, extrai os dados e chama o Engine.
    Formato esperado: autohunt_start_{quantidade}_{regiao}
    Ex: autohunt_start_10_floresta_sombria
    """
    query = update.callback_query
    data = query.data
    
    try:
        # Remove o prefixo
        content = data.replace("autohunt_start_", "")
        
        # Divide apenas no primeiro underscore 
        # (Isso permite que regiões tenham underline no nome, ex: floresta_negra)
        parts = content.split("_", 1)
        
        if len(parts) < 2:
            await query.answer("❌ Dados do botão inválidos.", show_alert=True)
            return

        # Converte os dados
        hunt_count = int(parts[0])
        region_key = parts[1]

        # 🚀 CHAMA O ENGINE
        # O Engine cuidará de:
        # 1. Verificar Auth (get_current_player_id)
        # 2. Verificar VIP/Energia
        # 3. Salvar no Banco (compatível com Watchdog)
        # 4. Agendar o Job
        await start_auto_hunt(update, context, hunt_count, region_key)
        
    except ValueError:
        await query.answer("❌ Erro de formato (número inválido).", show_alert=True)
    except Exception as e:
        logger.error(f"Erro no parser do autohunt: {e}")
        await query.answer("❌ Erro ao iniciar caçada.", show_alert=True)

# ==============================================================================
# 📦 EXPORTAÇÃO PARA O REGISTRO
# ==============================================================================
# O __init__.py ou regions.py deve importar esta lista
all_autohunt_handlers = [
    CallbackQueryHandler(_autohunt_button_parser, pattern="^autohunt_start_")
]