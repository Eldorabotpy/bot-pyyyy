# Em handlers/daily_jobs.py

import logging
from datetime import datetime, timezone
from telegram.ext import ContextTypes
from modules import player_manager

logger = logging.getLogger(__name__)

def _today_iso() -> str:
    """Retorna a data atual no formato YYYY-MM-DD."""
    return datetime.now(timezone.utc).date().isoformat()

async def daily_pvp_entry_reset_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Job que roda uma vez por dia para resetar as 10 entradas de PvP de todos os jogadores.
    """
    today = _today_iso()
    reset_count = 0
    
    # Itera por todos os arquivos de jogador
    for user_id, p_data in player_manager.iter_players():
        try:
            # Só reseta se o último reset foi em um dia anterior
            if p_data.get("last_pvp_entry_reset") != today:
                p_data["pvp_entries_left"] = 10
                p_data["last_pvp_entry_reset"] = today
                player_manager.save_player_data(user_id, p_data)
                reset_count += 1
        except Exception as e:
            logger.error(f"Falha ao resetar entradas de PvP para {user_id}: {e}")
            
    logger.info(f"[JOB DIÁRIO] Entradas de PvP resetadas para {reset_count} jogadores.")