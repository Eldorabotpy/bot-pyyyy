#==>handlers/daily_jobs.py


import asyncio
import logging
from telegram.error import Forbidden
from datetime import datetime, timezone
from telegram.ext import ContextTypes
from modules import player_manager # Garante que player_manager está importado

logger = logging.getLogger(__name__)

def _today_iso() -> str:
    """Retorna a data atual no formato YYYY-MM-DD."""
    # Usa UTC para consistência com timestamps salvos
    return datetime.now(timezone.utc).date().isoformat()

async def daily_pvp_entry_reset_job(context: ContextTypes.DEFAULT_TYPE, force_run: bool = False): # <<< 1. ADICIONA force_run
    """
    Job que roda uma vez por dia para resetar as 10 entradas de PvP.
    Se force_run=True, ignora a verificação de data.
    """
    today = _today_iso()
    reset_count = 0
    processed_count = 0
    
    notify_text = "⚔️ Suas 10 entradas diárias da Arena PvP foram resetadas! Boa sorte!"
    
    if force_run:
         logger.info("[JOB DIÁRIO - PvP Reset] Iniciando o reset de entradas... (MODO FORÇADO)")
    else:
         logger.info("[JOB DIÁRIO - PvP Reset] Iniciando o reset de entradas...")
    
    try:
        async for user_id, p_data in player_manager.iter_players():
            processed_count += 1
            try:
                if not isinstance(p_data, dict):
                    logger.warning(f"[JOB DIÁRIO - PvP Reset] Dados inválidos para {user_id}. Ignorando.")
                    continue

                # <<< 2. ALTERA A CONDIÇÃO >>>
                # Agora só executa se (for forçado) OU (ainda não tiver sido feito hoje)
                if force_run or p_data.get("last_pvp_entry_reset") != today:
                    
                    p_data["pvp_entries_left"] = 10 
                    p_data["last_pvp_entry_reset"] = today 
                    
                    await player_manager.save_player_data(user_id, p_data)
                    reset_count += 1

                    # Só notifica se for forçado (para não spamar se o job automático correr)
                    if force_run: 
                        try:
                            await context.bot.send_message(chat_id=user_id, text=notify_text)
                            await asyncio.sleep(0.1) 
                        except Exception:
                            pass # Ignora erros de notificação no modo forçado
            
            except Exception as e_player:
                logger.error(f"[JOB DIÁRIO - PvP Reset] Falha CRÍTICA ao processar reset para {user_id}: {e_player}", exc_info=True)

    except Exception as e_iter:
        logger.error(f"[JOB DIÁRIO - PvP Reset] Erro CRÍTICO durante a iteração: {e_iter}", exc_info=True)
            
    logger.info(f"[JOB DIÁRIO - PvP Reset] Concluído. Jogadores processados: {processed_count}. Entradas resetadas para: {reset_count} jogadores.")


async def daily_arena_ticket_job(context: ContextTypes.DEFAULT_TYPE, force_run: bool = False): # <<< 1. ADICIONA force_run
    """
    Job diário que entrega 1 'ticket_arena' a todos os jogadores.
    Se force_run=True, ignora a verificação de data.
    """
    today = _today_iso()
    item_id_to_give = "ticket_arena"
    item_qty = 10
    delivered_count = 0
    processed_count = 0
    
    notify_text = f"🎫 Você recebeu seu {item_qty}x Ticket de Arena diário! (Entrega Forçada)" if force_run else f"🎫 Você recebeu seu {item_qty}x Ticket de Arena diário!"
    
    if force_run:
         logger.info(f"[JOB DIÁRIO - Arena Ticket] Iniciando a entrega de '{item_id_to_give}'... (MODO FORÇADO)")
    else:
         logger.info(f"[JOB DIÁRIO - Arena Ticket] Iniciando a entrega de '{item_id_to_give}'...")
    
    try:
        async for user_id, p_data in player_manager.iter_players():
            processed_count += 1
            try:
                if not isinstance(p_data, dict):
                    logger.warning(f"[JOB DIÁRIO - Arena Ticket] Dados inválidos para {user_id}. Ignorando.")
                    continue

                daily_awards = p_data.get("daily_awards", {})
                if not isinstance(daily_awards, dict): 
                     daily_awards = {}
                
                # <<< 2. ALTERA A CONDIÇÃO >>>
                # Agora só executa se (for forçado) OU (ainda não tiver sido feito hoje)
                if force_run or daily_awards.get("last_arena_ticket_date") != today:
                    
                    player_manager.add_item_to_inventory(p_data, item_id_to_give, item_qty)
                    
                    daily_awards["last_arena_ticket_date"] = today
                    p_data["daily_awards"] = daily_awards
                    
                    await player_manager.save_player_data(user_id, p_data)
                    delivered_count += 1

                    # Tenta notificar (com delay)
                    try:
                        await context.bot.send_message(chat_id=user_id, text=notify_text)
                        await asyncio.sleep(0.1) 
                    except Forbidden:
                        logger.warning(f"[JOB DIÁRIO - Arena Ticket] Não foi possível notificar {user_id}: Bot bloqueado.")
                    except Exception as e_notify:
                        logger.warning(f"[JOB DIÁRIO - Arena Ticket] Falha ao notificar {user_id}: {type(e_notify).__name__}")
            
            except Exception as e_player:
                logger.error(f"[JOB DIÁRIO - Arena Ticket] Falha CRÍTICA ao processar {user_id}: {e_player}", exc_info=True)

    except Exception as e_iter:
        logger.error(f"[JOB DIÁRIO - Arena Ticket] Erro CRÍTICO durante a iteração: {e_iter}", exc_info=True)
            
    logger.info(f"[JOB DIÁRIO - Arena Ticket] Concluído. Jogadores processados: {processed_count}. Tickets entregues a: {delivered_count} jogadores.")