"""Compatibilidade com chamadas antigas do reset mensal da Arena.

As temporadas e seus prêmios agora são administrados pelo agendador do Coliseu
em ``main.py`` e persistidos pelo serviço ``coliseum_rewards``. Este módulo
mantém os nomes públicos antigos sem permitir um segundo reset mensal.
"""
import logging

logger = logging.getLogger(__name__)


async def entregar_premios_ranking(context_bot=None):
    logger.info("Premiações PvP são processadas pelo ciclo de temporada de 35 dias do Coliseu.")
    return 0


async def executar_reset_pvp(context_bot=None, force_run=False):
    logger.info("Reset mensal ignorado; o Coliseu controla Elo e prêmios a cada 35 dias.")
    return False
