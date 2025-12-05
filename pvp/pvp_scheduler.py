# pvp/pvp_scheduler.py
import logging
import datetime
from telegram.ext import ContextTypes

# Importa a conexão do banco de dados existente
from modules.database import players_col
from modules import player_manager, game_data
from pvp.pvp_config import MONTHLY_RANKING_REWARDS

logger = logging.getLogger(__name__)

async def executar_reset_pvp(context_bot, force_run=False):
    """
    Função central que executa a lógica do reset.
    Pode ser chamada pelo Job automático ou manualmente.
    """
    agora = datetime.datetime.now()
    mes_atual_str = f"{agora.year}-{agora.month}"
    
    # Se NÃO for forçado, verifica se já rodou hoje ou se é dia 1
    if not force_run:
        if agora.day != 1:
            return
        
        # Verifica se já rodou este mês para evitar duplicidade
        ultimo_reset = game_data.SYSTEM_DATA.get("pvp_last_reset_month")
        if ultimo_reset == mes_atual_str:
            return

    logger.info(f"🔄 [PvP] INICIANDO RESET DE TEMPORADA! (Mês: {mes_atual_str}, Forçado: {force_run})")

    if players_col is None:
        logger.error("❌ [PvP] Cancelando reset: 'players_col' é None. Verifique a conexão com o banco.")
        return

    # --- FASE 1: PREMIAR OS VENCEDORES (Top 5) ---
    try:
        # Busca apenas os top 5 jogadores com pontos > 0
        cursor = players_col.find({"pvp_points": {"$gt": 0}}).sort("pvp_points", -1).limit(5)
        top_players = list(cursor) # Converte cursor para lista (síncrono/pymongo padrão) ou await se for motor
        # Nota: Se estiver usando Motor (Async), seria: await cursor.to_list(length=5)
        # Assumindo PyMongo padrão pelo seu core.py:
        
        msg_recompensa = "🏆 <b>Nova Temporada PvP Iniciada!</b>\nParabéns! Você ficou entre os melhores da temporada passada:"

        for i, p_data in enumerate(top_players):
            user_id = p_data.get("_id") # MongoDB usa _id
            rank = i + 1
            reward_gems = MONTHLY_RANKING_REWARDS.get(rank, 0)

            if reward_gems > 0:
                # Adiciona Gemas usando seu player_manager (Safe)
                # Precisamos garantir que player_manager tenha add_gems ou similar
                # Se add_gems for async, use await. Se for sync, chame direto.
                # Assumindo async baseada no contexto:
                try:
                    p_data_loaded = await player_manager.get_player_data(user_id)
                    player_manager.add_gems(p_data_loaded, reward_gems)
                    await player_manager.save_player_data(user_id, p_data_loaded)
                    
                    # Notifica
                    await context_bot.send_message(
                        chat_id=user_id, 
                        text=f"{msg_recompensa}\n💎 <b>+{reward_gems} Gemas</b> (Rank #{rank})"
                    )
                    logger.info(f"✅ [PvP] Prêmio entregue para Rank #{rank} (ID: {user_id})")
                except Exception as e_reward:
                    logger.error(f"⚠️ Erro ao premiar ID {user_id}: {e_reward}")

    except Exception as e:
        logger.error(f"⚠️ [PvP] Erro ao processar ranking: {e}")

    # --- FASE 2: O RESET TOTAL (Bulk Update) ---
    # Isso é instantâneo e não trava o bot
    try:
        result = players_col.update_many(
            {"pvp_points": {"$gt": 0}},  # Filtro: Quem tem pontos positivos
            {"$set": {"pvp_points": 0}}  # Ação: Zera
        )
        logger.info(f"✅ [PvP] Pontos zerados com sucesso via MongoDB. Jogadores afetados: {result.modified_count}")
        
    except Exception as e:
        logger.error(f"❌ [PvP] Erro Crítico ao zerar pontos no banco: {e}")
        return

    # --- FASE 3: MARCAR COMO FEITO ---
    game_data.SYSTEM_DATA["pvp_last_reset_month"] = mes_atual_str
    # Salvar system data se necessário (depende da sua implementação de game_data)
    
    # Aviso para o Admin
    from config import ADMIN_ID
    if ADMIN_ID:
        try:
            await context_bot.send_message(chat_id=ADMIN_ID, text=f"✅ <b>PvP Resetado com Sucesso!</b>\nJogadores zerados: {result.modified_count}")
        except: pass

async def job_pvp_monthly_reset(context: ContextTypes.DEFAULT_TYPE):
    """Job automático (roda todo dia)."""
    await executar_reset_pvp(context.bot, force_run=False)