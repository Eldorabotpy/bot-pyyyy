# pvp/pvp_scheduler.py
# (VERSÃO CORRIGIDA: Reset em Duas Tabelas)

import logging
import datetime
from telegram.ext import ContextTypes

# Imports
from modules.player.core import players_collection 
from modules import player_manager, game_data
from pvp.pvp_config import MONTHLY_RANKING_REWARDS

logger = logging.getLogger(__name__)

# Tenta pegar users_collection
users_collection = None
if players_collection is not None:
    try: users_collection = players_collection.database["users"]
    except: pass

async def entregar_premios_ranking(context_bot):
    """Entrega prêmios usando o iterador híbrido."""
    all_players = []
    
    # Itera de forma inteligente (pula duplicados de migração)
    async for user_id, pdata in player_manager.iter_players():
        pts = int(pdata.get("pvp_points", 0))
        if pts > 0:
            all_players.append({
                "user_id": user_id,
                "points": pts,
                "pdata": pdata
            })

    all_players.sort(key=lambda x: x["points"], reverse=True)
    
    count_premiados = 0
    for i, player in enumerate(all_players):
        rank = i + 1
        rewards = MONTHLY_RANKING_REWARDS.get(rank)
        
        if rewards:
            uid = player["user_id"]
            pdata = player["pdata"]
            
            # Entrega Itens
            if "ouro" in rewards: player_manager.add_gold(pdata, rewards["ouro"])
            if "gems" in rewards: player_manager.add_gems(pdata, rewards["gems"])
            if "cristal_de_abertura" in rewards:
                player_manager.add_item_to_inventory(pdata, "cristal_de_abertura", rewards["cristal_de_abertura"])

            await player_manager.save_player_data(uid, pdata)
            
            # Notifica
            try:
                await context_bot.send_message(
                    chat_id=uid, 
                    text=f"🏆 <b>PARABÉNS!</b>\nTerminou em <b>#{rank}</b> no PvP!\nPrémios entregues.",
                    parse_mode="HTML"
                )
            except: pass
            
            count_premiados += 1

    logger.info(f"🎁 [PvP] Prêmios entregues: {count_premiados}")

async def executar_reset_pvp(context_bot, force_run=False):
    """Função Mestra que zera pontos em AMBAS as coleções."""
    agora = datetime.datetime.now()
    mes_atual_str = f"{agora.year}-{agora.month}"
    
    if not force_run:
        if agora.day != 1: return
        if game_data.SYSTEM_DATA.get("pvp_last_reset_month") == mes_atual_str:
            logger.info(f"ℹ️ [PvP] Reset já feito em {mes_atual_str}")
            return

    logger.info(f"🔄 [PvP] RESET INICIADO! (Force: {force_run})")

    # 1. Entrega Prêmios
    await entregar_premios_ranking(context_bot)

    # 2. Zera Pontos (HÍBRIDO)
    count = 0
    
    # Limpa Legado
    if players_collection is not None:
        try:
            res = players_collection.update_many({}, {"$set": {"pvp_points": 0}})
            count += res.modified_count
        except Exception as e: logger.error(f"Erro reset legacy: {e}")

    # Limpa Novo (ESSA PARTE FALTAVA NO SEU ARQUIVO)
    if users_collection is not None:
        try:
            res = users_collection.update_many({}, {"$set": {"pvp_points": 0}})
            count += res.modified_count
        except Exception as e: logger.error(f"Erro reset new: {e}")

    logger.info(f"🧹 [PvP] Pontos zerados! {count} docs afetados.")
    
    player_manager.clear_all_player_cache()
    game_data.SYSTEM_DATA["pvp_last_reset_month"] = mes_atual_str