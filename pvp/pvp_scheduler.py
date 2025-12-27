# pvp/pvp_scheduler.py

import logging
import datetime
from telegram.ext import ContextTypes

# Imports dos módulos
from modules.player.core import players_collection 
from modules import player_manager, game_data
from pvp.pvp_config import MONTHLY_RANKING_REWARDS

logger = logging.getLogger(__name__)

async def executar_reset_pvp(context_bot, force_run=False):
    """
    Função Mestra que zera os pontos e entrega prêmios.
    Deve ser chamada pelo jobs.py ou main.py no dia 1º do mês.
    """
    agora = datetime.datetime.now()
    mes_atual_str = f"{agora.year}-{agora.month}"
    
    # --- VERIFICAÇÃO DE SEGURANÇA ---
    # Se não for forçado, verifica se é dia 1 e se já rodou neste mês
    if not force_run:
        if agora.day != 1:
            return
        # Verifica se a chave existe e é igual ao mês atual (evita reset duplo)
        if game_data.SYSTEM_DATA.get("pvp_last_reset_month") == mes_atual_str:
            logger.info(f"ℹ️ [PvP] Reset mensal já foi realizado em: {mes_atual_str}")
            return

    logger.info(f"🔄 [PvP] INICIANDO RESET! (Forçado: {force_run})")

    if players_collection is None:
        logger.error("❌ [PvP] Erro: Sem conexão com o banco de dados.")
        return

    # =================================================================
    # FASE 1: PREMIAR OS CAMPEÕES (Antes de zerar)
    # =================================================================
    try:
        # Busca jogadores com pontos > 0
        cursor = players_collection.find({"pvp_points": {"$gt": 0}}).sort("pvp_points", -1).limit(5)
        top_players = list(cursor)

        for i, player in enumerate(top_players):
            rank = i + 1
            reward = MONTHLY_RANKING_REWARDS.get(rank, 0)
            user_id = player["_id"]
            
            if reward > 0:
                # Entrega Gemas
                players_collection.update_one({"_id": user_id}, {"$inc": {"gems": reward}})
                
                # Avisa o jogador (se possível)
                try:
                    await context_bot.send_message(
                        chat_id=user_id,
                        text=f"🏆 <b>Recompensa da Temporada PvP!</b>\n"
                             f"Você ficou no <b>Rank #{rank}</b> e ganhou 💎 <b>{reward} Gemas</b>!"
                    )
                except Exception: pass
                
        logger.info(f"✅ [PvP] Prêmios entregues para {len(top_players)} jogadores.")

    except Exception as e:
        logger.error(f"⚠️ [PvP] Erro ao entregar prêmios: {e}")

    # =================================================================
    # FASE 2: ZERAR OS PONTOS (O Código que você procurava)
    # =================================================================
    try:
        # O comando update_many com filtro vazio {} afeta TODOS os jogadores
        resultado = players_collection.update_many(
            {}, 
            {"$set": {"pvp_points": 0}}
        )
        logger.info(f"🧹 [PvP] Pontos zerados! Jogadores afetados: {resultado.modified_count}")
        
        # Limpa cache do bot para evitar dados antigos na memória
        if hasattr(player_manager, "PLAYER_CACHE"):
            player_manager.PLAYER_CACHE.clear()

    except Exception as e:
        logger.critical(f"❌ [PvP] ERRO CRÍTICO AO ZERAR PONTOS: {e}")
        return # Se falhar aqui, não salva o status de concluído

    # =================================================================
    # FASE 3: REGISTRAR QUE O RESET FOI FEITO
    # =================================================================
    try:
        game_data.SYSTEM_DATA["pvp_last_reset_month"] = mes_atual_str
        
        # Salva dados do sistema (se houver função de save)
        # game_data.save_system_data() # Descomente se tiver essa função
        
        logger.info(f"💾 [PvP] Reset concluído com sucesso: {mes_atual_str}")

    except Exception as e:
        logger.error(f"⚠️ [PvP] Erro ao salvar flag de reset: {e}")