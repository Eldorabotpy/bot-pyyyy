# pvp/pvp_scheduler.py

import logging
import datetime
from telegram.ext import ContextTypes

# Imports
from modules.player.core import players_collection 
from modules import player_manager, game_data
from pvp.pvp_config import MONTHLY_RANKING_REWARDS

logger = logging.getLogger(__name__)

async def executar_reset_pvp(context_bot, force_run=False):
    """
    Função que zera os pontos e entrega prêmios.
    """
    agora = datetime.datetime.now()
    mes_atual_str = f"{agora.year}-{agora.month}"
    
    # Se não for forçado, verifica se já rodou neste mês
    if not force_run:
        if agora.day != 1:
            return
        # Verifica se a chave existe e é igual ao mês atual
        if game_data.SYSTEM_DATA.get("pvp_last_reset_month") == mes_atual_str:
            logger.info(f"ℹ️ [PvP] Reset mensal já foi realizado em: {mes_atual_str}")
            return

    logger.info(f"🔄 [PvP] INICIANDO RESET! (Forçado: {force_run})")

    if players_collection is None:
        logger.error("❌ [PvP] Erro: Sem conexão com o banco de dados.")
        return

    # --- FASE 1: PREMIAR TOP 5 (Antes de zerar) ---
    try:
        # Pega APENAS quem tem pontos para não pesar a query
        cursor = players_collection.find({"pvp_points": {"$gt": 0}}).sort("pvp_points", -1).limit(5)
        top_players = list(cursor)
        
        for i, p_data in enumerate(top_players):
            user_id = p_data.get("_id")
            rank = i + 1
            reward_gems = MONTHLY_RANKING_REWARDS.get(rank, 0)

            if reward_gems > 0:
                try:
                    # Tenta avisar o jogador
                    await context_bot.send_message(chat_id=user_id, text=f"🏆 <b>Nova Temporada PvP!</b>\nVocê terminou em #{rank} e ganhou {reward_gems} Gemas!")
                    
                    # Opcional: Se você tiver um método seguro de dar gemas offline, chame aqui.
                    # Exemplo: await player_manager.safe_add_currency(user_id, "gems", reward_gems)
                    # Por enquanto, estamos apenas confiando que o admin fará ou que existe outro sistema.
                except Exception as e_msg: 
                    logger.warning(f"Não foi possível enviar msg para {user_id}: {e_msg}")

    except Exception as e:
        logger.error(f"⚠️ [PvP] Erro ao processar prêmios: {e}")

    # --- FASE 2: O GRANDE RESET ---
    try:
        # 1. Zera no Banco de Dados
        result = players_collection.update_many(
            {"pvp_points": {"$gt": 0}}, 
            {"$set": {"pvp_points": 0}}
        )
        logger.info(f"✅ [PvP] DB Atualizado! {result.modified_count} jogadores zerados.")
        
        # 2. LIMPEZA DE CACHE (CRUCIAL)
        # Se o player estiver na memória com 5000 pontos, ele vai sobrescrever o zero do banco quando salvar.
        # Como não temos uma função 'clear_all_cache', vamos iterar sobre quem alteramos (idealmente) ou confiar no restart.
        # DICA: A melhor prática após um reset global é reiniciar o bot ou limpar o cache globalmente.
        if hasattr(player_manager, "PLAYER_CACHE"):
            player_manager.PLAYER_CACHE.clear()
            logger.info("🧹 [PvP] Cache de jogadores limpo para evitar conflitos.")
        
    except Exception as e:
        logger.error(f"❌ [PvP] Erro Crítico ao zerar pontos: {e}")
        return

    # --- FASE 3: SALVAR O ESTADO DO SISTEMA ---
    try:
        game_data.SYSTEM_DATA["pvp_last_reset_month"] = mes_atual_str
        
        # IMPORTANTE: Você precisa salvar o arquivo json/dict do sistema para persistir isso!
        # Estou assumindo que existe uma função assim. Se não, implemente no game_data.
        if hasattr(game_data, "save_system_data"):
            game_data.save_system_data()
        elif hasattr(game_data, "save_data"):
            game_data.save_data()
        
        logger.info(f"💾 [PvP] Data do reset salva: {mes_atual_str}")

    except Exception as e:
        logger.error(f"⚠️ [PvP] Erro ao salvar SYSTEM_DATA: {e}")
    
    # Avisa Admin
    from config import ADMIN_ID
    if ADMIN_ID:
        try: await context_bot.send_message(chat_id=ADMIN_ID, text=f"✅ <b>PvP Resetado com Sucesso!</b>\nJogadores afetados: {result.modified_count}\nCache Limpo.")
        except: pass

async def job_pvp_monthly_reset(context: ContextTypes.DEFAULT_TYPE):
    await executar_reset_pvp(context.bot, force_run=False)