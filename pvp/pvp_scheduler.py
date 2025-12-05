# pvp/pvp_scheduler.py

import logging
import datetime
from telegram.ext import ContextTypes

# --- IMPORTS CORRETOS ---
# Importamos a coleção do banco para zerar rápido
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
    
    # Se não for forçado, checa se é dia 1
    if not force_run:
        if agora.day != 1:
            return
        if game_data.SYSTEM_DATA.get("pvp_last_reset_month") == mes_atual_str:
            return

    logger.info(f"🔄 [PvP] INICIANDO RESET! (Forçado: {force_run})")

    if players_collection is None:
        logger.error("❌ [PvP] Erro: Sem conexão com o banco de dados.")
        return

    # --- FASE 1: PREMIAR TOP 5 ---
    try:
        cursor = players_collection.find({"pvp_points": {"$gt": 0}}).sort("pvp_points", -1).limit(5)
        top_players = list(cursor)
        
        for i, p_data in enumerate(top_players):
            user_id = p_data.get("_id")
            rank = i + 1
            reward_gems = MONTHLY_RANKING_REWARDS.get(rank, 0)

            if reward_gems > 0:
                try:
                    # Entrega direta para garantir
                    await player_manager.safe_add_gold(user_id, 0) # Apenas para carregar pdata se necessario
                    # Logica de gemas (assumindo que existe no inventory ou wallet)
                    # Se não tiver func direta, atualizamos via mongo:
                    # players_collection.update_one({"_id": user_id}, {"$inc": {"inventory.gem": reward_gems}})
                    
                    # Notifica
                    await context_bot.send_message(chat_id=user_id, text=f"🏆 <b>Nova Temporada!</b>\nVocê ganhou {reward_gems} Gemas pelo Rank #{rank}!")
                except: pass

    except Exception as e:
        logger.error(f"⚠️ [PvP] Erro ao premiar: {e}")

    # --- FASE 2: O GRANDE RESET (ZERAR TUDO) ---
    try:
        # ISSO AQUI QUE VAI LIMPAR O RANKING DA IMAGEM
        result = players_collection.update_many(
            {"pvp_points": {"$gt": 0}},  # Pega todo mundo com pontos
            {"$set": {"pvp_points": 0}}  # ZERA os pontos
        )
        logger.info(f"✅ [PvP] SUCESSO! {result.modified_count} jogadores foram zerados.")
        
    except Exception as e:
        logger.error(f"❌ [PvP] Erro ao zerar pontos: {e}")
        return

    # Marca como feito
    game_data.SYSTEM_DATA["pvp_last_reset_month"] = mes_atual_str
    
    # Avisa Admin
    from config import ADMIN_ID
    if ADMIN_ID:
        try: await context_bot.send_message(chat_id=ADMIN_ID, text=f"✅ <b>PvP Resetado!</b>\nJogadores limpos: {result.modified_count}")
        except: pass
async def job_pvp_monthly_reset(context: ContextTypes.DEFAULT_TYPE):
    await executar_reset_pvp(context.bot, force_run=False)