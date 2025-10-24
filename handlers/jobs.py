# Arquivo: handlers/jobs.py

from __future__ import annotations

import logging
import datetime
import asyncio
from zoneinfo import ZoneInfo
from typing import Dict, Optional
from telegram.ext import ContextTypes
from telegram.error import Forbidden

from modules import player_manager
# Módulos do player
from modules.player_manager import (
    iter_players,
    add_energy,
    save_player_data,
    has_premium_plan,
    get_perk_value,
    get_player_max_energy,
    add_item_to_inventory,
    get_pvp_points,
    add_gems,
)
from config import EVENT_TIMES, JOB_TIMEZONE

from handlers.refining_handler import finish_dismantle_job
from pvp.pvp_config import MONTHLY_RANKING_REWARDS
logger = logging.getLogger(__name__)

# --- CONSTANTES ---
DAILY_CRYSTAL_ITEM_ID = "cristal_de_abertura"
DAILY_CRYSTAL_BASE_QTY = 4
DAILY_NOTIFY_USERS = True
_non_premium_tick: Dict[str, int] = {"count": 0}

# <<< IDs PARA ANÚNCIOS >>>
ANNOUNCEMENT_CHAT_ID = -1002881364171 # ID do Grupo/Canal
ANNOUNCEMENT_THREAD_ID = 24         # ID do Tópico

# --- HELPERS ---
def _today_str(tzname: str = JOB_TIMEZONE) -> str:
    try:
        tz = ZoneInfo(tzname)
        now = datetime.datetime.now(tz)
    except Exception:
        now = datetime.datetime.now()
    return now.date().isoformat()

def _parse_iso_utc(s: Optional[str]) -> Optional[datetime.datetime]:
    if not s: return None
    try:
        s_norm = s.strip().removesuffix("Z") + "+00:00" if s.strip().endswith("Z") else s.strip()
        dt = datetime.datetime.fromisoformat(s_norm)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc)
    except Exception: return None

def _safe_add_stack(pdata: dict, item_id: str, qty: int) -> None:
    try:
        add_item_to_inventory(pdata, item_id, qty)
    except Exception as e:
        logger.debug("[_safe_add_stack] add_item_to_inventory falhou (%s). Usando fallback.", e)
        inv = pdata.setdefault("inventory", {})
        inv[item_id] = int(inv.get(item_id, 0)) + int(qty)

# --- JOBS PRINCIPAIS ---

async def regenerate_energy_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    _non_premium_tick["count"] = (_non_premium_tick["count"] + 1) % 2
    regenerate_non_premium = (_non_premium_tick["count"] == 0)
    touched = 0
    for user_id, pdata in iter_players():
        try:
            max_e, cur_e = int(get_player_max_energy(pdata)), int(pdata.get("energy", 0))
            if cur_e >= max_e: continue
            
            premium = has_premium_plan(user_id)
            
            if premium or regenerate_non_premium:
                add_energy(pdata, 1)
                save_player_data(user_id, pdata)
                touched += 1
        except Exception as e:
            logger.warning("[ENERGY] Falha ao processar jogador %s: %s", user_id, e)
    if touched:
        logger.info("[ENERGY] Regeneração aplicada a %s jogadores.", touched)


async def daily_crystal_grant_job(context: ContextTypes.DEFAULT_TYPE) -> int:
    today = _today_str()
    granted = 0
    for user_id, pdata in iter_players():
        try:
            daily = pdata.get("daily_awards") or {}
            if daily.get("last_crystal_date") == today: continue

            # =================================================================
            # --- 3. MELHORIA COM O SISTEMA DE PERKS ---
            # =================================================================
            bonus_qty = get_perk_value(user_id, "daily_crystal_bonus", 0)
            total_qty = DAILY_CRYSTAL_BASE_QTY + bonus_qty
            
            _safe_add_stack(pdata, DAILY_CRYSTAL_ITEM_ID, total_qty)
            
            daily["last_crystal_date"] = today
            pdata["daily_awards"] = daily
            save_player_data(user_id, pdata)
            granted += 1
            
            if DAILY_NOTIFY_USERS:
                notify_text = f"🎁 Você recebeu {total_qty}× Cristal de Abertura (recompensa diária)."
                if bonus_qty > 0:
                    notify_text += f"\n✨ Bônus de apoiador: +{bonus_qty} cristais!"
                try: await context.bot.send_message(chat_id=user_id, text=notify_text)
                except Exception: pass
        except Exception as e:
            logger.warning("[DAILY] Falha ao conceder cristais para %s: %s", user_id, e)
    logger.info("[DAILY] Rotina normal: %s jogadores receberam cristais.", granted)
    return granted

async def force_grant_daily_crystals(context: ContextTypes.DEFAULT_TYPE) -> int:
    """Força a entrega dos cristais diários (apenas a quantidade base)."""
    granted = 0
    for user_id, pdata in iter_players():
        try:
            # ✅ CORREÇÃO 2: Usando a nova constante DAILY_CRYSTAL_BASE_QTY
            _safe_add_stack(pdata, DAILY_CRYSTAL_ITEM_ID, DAILY_CRYSTAL_BASE_QTY)
            
            daily = pdata.get("daily_awards") or {}
            daily["last_crystal_date"] = _today_str()
            pdata["daily_awards"] = daily
            save_player_data(user_id, pdata)
            granted += 1

            # A notificação agora também usa a constante correta
            notify_text = f"🎁 Você recebeu {DAILY_CRYSTAL_BASE_QTY}× Cristal de Abertura (entrega forçada pelo admin)."
            try: await context.bot.send_message(chat_id=user_id, text=notify_text)
            except Exception: pass
        except Exception as e:
            logger.warning("[ADMIN_FORCE_DAILY] Falha ao forçar cristais para %s: %s", user_id, e)
    logger.info("[ADMIN_FORCE_DAILY] Cristais concedidos forçadamente para %s jogadores.", granted)
    return granted

async def daily_event_ticket_job(context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entrega o ticket do evento e anuncia os horários do dia."""
    horarios_str = " e ".join([f"{start_h:02d}:{start_m:02d}" for start_h, start_m, _, _ in EVENT_TIMES])
    notify_text = (
        f"🎟️ **Um Ticket de Defesa do Reino foi entregue a você!**\n\n"
        f"📢 Hoje, as hordas atacarão Eldora nos seguintes horários:\n"
        f"  - **{horarios_str}**\n\n"
        f"Esteja no reino e prepare-se para a batalha!"
    )
    delivered = 0
    for user_id, pdata in iter_players():
        try:
            # Entrega 1 ticket para cada jogador
            _safe_add_stack(pdata, 'ticket_defesa_reino', 1)
            save_player_data(user_id, pdata)
            delivered += 1
            
            # Tenta notificar o jogador
            try:
                await context.bot.send_message(chat_id=user_id, text=notify_text, parse_mode='HTML')
                await asyncio.sleep(0.1) # Delay para não sobrecarregar a API
            except Forbidden:
                pass # Ignora se o bot foi bloqueado
        except Exception as e:
            logger.warning("[JOB_TICKET] Falha ao entregar ticket para %s: %s", user_id, e)
    
    logger.info("[JOB_TICKET] Tickets de evento entregues para %s jogadores.", delivered)
    return delivered


async def afternoon_event_reminder_job(context: ContextTypes.DEFAULT_TYPE) -> int:
    """Envia uma notificação de lembrete para o segundo evento do dia."""
    notify_text = "🔔 **LEMBRETE DE EVENTO** 🔔\n\nA segunda horda de monstros se aproxima! O ataque ao reino começará em breve, às 14:00. Não se esqueça de participar!"
    
    notified = 0
    for user_id, _ in iter_players():
        try:
            await context.bot.send_message(chat_id=user_id, text=notify_text, parse_mode='HTML')
            await asyncio.sleep(0.1)
            notified += 1
        except Exception:
            pass # Ignora erros
            
    logger.info("[JOB_LEMBRETE] Lembrete de evento enviado para %s jogadores.", notified)
    return notified

async def timed_actions_watchdog(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Verifica ações terminadas e reagenda a finalização."""
    # Importações das funções finalizadoras (movidas para o topo da função)
    from modules import player_manager
    # <<< CORREÇÃO: Importa _parse_iso (nome correto) de actions.py >>>
    from modules.player.actions import _parse_iso
    from handlers.job_handler import finish_collection_job
    from handlers.menu.region import finish_travel_job
    from handlers.forge_handler import finish_craft_notification_job as finish_crafting_job
    from handlers.refining_handler import finish_refine_job as finish_refining_job
    from handlers.refining_handler import finish_dismantle_job

    ACTION_FINISHERS = {
         "collecting": {"fn": finish_collection_job, "data_builder": lambda st: {'resource_id': (st.get("details") or {}).get("resource_id"),'item_id_yielded': (st.get("details") or {}).get("item_id_yielded"),'energy_cost': (st.get("details") or {}).get("energy_cost", 1),'speed_mult': (st.get("details") or {}).get("speed_mult", 1.0)}},
         "travel": {"fn": finish_travel_job, "data_builder": lambda st: {"dest": (st.get("details") or {}).get("destination")}},
         "crafting": {"fn": finish_crafting_job, "data_builder": lambda st: {"recipe_id": (st.get("details") or {}).get("recipe_id")}},
         "refining": {"fn": finish_refining_job, "data_builder": lambda st: {"recipe_id": (st.get("details") or {}).get("recipe_id")}},
         "dismantling": {"fn": finish_dismantle_job, "data_builder": lambda st: {}},
    }

    # print("\n>>> DEBUG WATCHDOG: Iniciando verificação...") # DEBUG Removido
    now = datetime.datetime.now(datetime.timezone.utc)
    # print(f">>> DEBUG WATCHDOG: Hora Atual (UTC): {now.isoformat()}") # DEBUG Removido

    fired = 0
    checked_players = 0

    try:
        player_iterator = player_manager.iter_players()
        if isinstance(player_iterator, dict): player_iterator = player_iterator.items()

        for user_id, pdata in player_iterator:
            checked_players += 1
            try:
                st = pdata.get("player_state") or {}
                action = st.get("action")

                if not action or action not in ACTION_FINISHERS:
                    continue

                ft_str = st.get("finish_time")
                # <<< CORREÇÃO: Usa a função importada _parse_iso >>>
                ft = _parse_iso(ft_str)

                # <<< Verificação de fuso horário (importante!) >>>
                # A função _parse_iso já adiciona UTC se não houver fuso.
                # Garantimos que 'now' também está em UTC.

                # Compara as horas
                if not ft or ft > now:
                    continue

                # --- Se chegou aqui, a ação foi encontrada e TERMINOU ---
                # print(f">>> DEBUG WATCHDOG: Ação '{action}' TERMINADA encontrada para User {user_id} (Finish: {ft_str})") # DEBUG Removido

                config = ACTION_FINISHERS[action]
                finalizer_fn = config.get("fn")
                if not finalizer_fn:
                    # print(f">>> DEBUG WATCHDOG: ERRO - Finalizer 'fn' não encontrado para action '{action}'!") # DEBUG Removido
                    continue

                job_data = {}
                if "data_builder" in config and callable(config["data_builder"]):
                     job_data = config["data_builder"](st)

                chat_id = pdata.get("last_chat_id", user_id)
                job_name = f"{action}:{user_id}"

                # Reagenda a finalização
                context.job_queue.run_once(
                    finalizer_fn, when=0, chat_id=chat_id, user_id=user_id,
                    data=job_data, name=job_name,
                )
                fired += 1
                # print(f">>> DEBUG WATCHDOG: Job '{job_name}' agendado para execução imediata.") # DEBUG Removido

            except Exception as e_player:
                logger.warning("[WATCHDOG] Erro ao verificar jogador %s: %s", user_id, e_player)
                # print(f">>> DEBUG WATCHDOG: ERRO ao processar jogador {user_id}: {e_player}") # DEBUG Removido

    except Exception as e_loop:
         logger.error(f"[WATCHDOG] Erro CRÍTICO durante o loop: {e_loop}", exc_info=True)
         # print(f">>> DEBUG WATCHDOG: ERRO CRÍTICO no loop principal: {e_loop}") # DEBUG Removido

    # Log final da execução (mantido)
    if fired > 0:
        logger.info("[WATCHDOG] Disparadas %s finalizações de ações vencidas.", fired)
    # print(f">>> DEBUG WATCHDOG: Verificação concluída. {checked_players} jogadores verificados, {fired} finalizações agendadas.") # DEBUG Removido

async def distribute_pvp_rewards(context: ContextTypes.DEFAULT_TYPE):
    """Distribui recompensas de Gemas (Dimas) para o Top N do ranking PvP,
       usando as configurações de MONTHLY_RANKING_REWARDS."""
    logger.info("Iniciando distribuição de recompensas PvP...")
    print(">>> JOB: Iniciando distribuição de recompensas PvP...") # Para debug

    # 1. Buscar todos os jogadores com pontos PvP > 0
    all_players_ranked = []
    try:
        # Usa .items() se iter_players retorna um dict, ou apenas o iterador se for direto
        player_iterator = player_manager.iter_players()
        if isinstance(player_iterator, dict):
            player_iterator = player_iterator.items()

        for p_id, p_data in player_iterator:
            pvp_points = player_manager.get_pvp_points(p_data)
            if pvp_points > 0: # Apenas quem tem pontos positivos
               all_players_ranked.append({
                   "user_id": p_id,
                   "name": p_data.get("character_name", f"ID: {p_id}"),
                   "points": pvp_points,
                   # Guarda p_data para adicionar gemas diretamente (precisa copiar?)
                   # Fazer cópia profunda pode ser mais seguro se p_data for modificado em outro lugar
                   "_pdata": p_data.copy() # Faz uma cópia para segurança
               })
    except Exception as e:
         logger.error(f"Erro ao buscar jogadores para recompensas PvP: {e}", exc_info=True)
         print(f">>> JOB ERROR: Erro ao buscar jogadores para recompensas PvP: {e}")
         return # Aborta a tarefa se houver erro

    # 2. Ordenar por pontos
    all_players_ranked.sort(key=lambda p: p["points"], reverse=True)

    # =========================================================
    # 👇 [CORREÇÃO] Usando MONTHLY_RANKING_REWARDS importado 👇
    # =========================================================

    # 3. Distribuir recompensas com base no dicionário importado
    winners_info = [] # Para log ou anúncio
    if not MONTHLY_RANKING_REWARDS:
         logger.warning("MONTHLY_RANKING_REWARDS não está definido ou está vazio em pvp_config. Nenhuma recompensa distribuída.")
         print(">>> JOB WARNING: MONTHLY_RANKING_REWARDS vazio. Nenhuma recompensa.")
    else:
        # Itera sobre os jogadores já ordenados
        for i, player in enumerate(all_players_ranked):
            rank = i + 1
            # Pega a recompensa do dicionário importado. Retorna None se o rank não tiver prémio.
            reward_amount = MONTHLY_RANKING_REWARDS.get(rank)

            if reward_amount:
                user_id = player["user_id"]
                # IMPORTANTE: Busca os dados MAIS RECENTES antes de modificar e salvar
                p_data_current = player_manager.get_player_data(user_id)
                if not p_data_current:
                     logger.error(f"Não foi possível obter dados atuais para o vencedor PvP Rank {rank} ({user_id})")
                     print(f">>> JOB ERROR: Não achou p_data para vencedor {user_id}")
                     continue # Pula este jogador

                player_name = p_data_current.get("character_name", f"ID: {user_id}") # Usa nome atual

                try:
                    # Adiciona as gemas aos dados atuais
                    player_manager.add_gems(p_data_current, reward_amount)
                    # Salva os dados atualizados
                    player_manager.save_player_data(user_id, p_data_current)

                    log_msg = f"Recompensa PvP Rank {rank}: {reward_amount} Gemas para {player_name} ({user_id})."
                    logger.info(log_msg)
                    print(f">>> JOB: {log_msg}") # Debug
                    winners_info.append(f"{rank}º: {player_name} (+{reward_amount}💎)")

                    # Opcional: Notificar o jogador diretamente
                    try:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=f"Parabéns! Você terminou em {rank}º lugar no ranking PvP mensal e recebeu {reward_amount} Gemas (Dimas) como recompensa!"
                        )
                    except Forbidden:
                        logger.warning(f"Bot bloqueado pelo vencedor PvP {user_id}, não notificado.")
                    except Exception as e_notify:
                         logger.warning(f"Falha ao notificar vencedor PvP {user_id}: {e_notify}")

                except Exception as e_grant:
                     err_msg = f"Erro ao conceder recompensa PvP Rank {rank} para {player_name} ({user_id}): {e_grant}"
                     logger.error(err_msg, exc_info=True)
                     print(f">>> JOB ERROR: {err_msg}")
            else:
                 # Otimização: Se chegámos a um rank sem prémio e os ranks são sequenciais (1, 2, 3...),
                 # podemos parar o loop mais cedo.
                 if rank > max(MONTHLY_RANKING_REWARDS.keys(), default=0):
                      break
    
    
    # =========================================================
    # 👆 [FIM DA CORREÇÃO] 👆
    # =========================================================

    # 5. Opcional: Anunciar os vencedores num canal/grupo
    if winners_info:
         announcement = "🏆 **Recompensas do Ranking PvP Mensal Distribuídas!** 🏆\n\nParabéns aos melhores combatentes deste ciclo:\n" + "\n".join(winners_info)
         try:
             await context.bot.send_message(
                 chat_id=ANNOUNCEMENT_CHAT_ID,
                 message_thread_id=ANNOUNCEMENT_THREAD_ID, # Envia para o tópico
                 text=announcement,
                 parse_mode="HTML"
             )
             logger.info(f"Anúncio dos vencedores PvP enviado para o tópico {ANNOUNCEMENT_THREAD_ID} no chat {ANNOUNCEMENT_CHAT_ID}.")
             print(f">>> JOB: Anúncio dos vencedores enviado para Tópico ID {ANNOUNCEMENT_THREAD_ID}.")
         except Exception as e_announce:
               print(">>> JOB: Anúncio dos vencedores (simulado):")
               print(announcement) # Debug

    logger.info("Distribuição de recompensas PvP concluída.")
    print(">>> JOB: Distribuição de recompensas PvP concluída.") # Debug

async def reset_pvp_season(context: ContextTypes.DEFAULT_TYPE):
    """Reseta os pontos PvP de todos os jogadores, iniciando uma nova temporada."""
    logger.info("Iniciando reset da temporada PvP...")
    print(">>> JOB: Iniciando reset da temporada PvP...") # Para debug

    reset_count = 0
    try:
        # Itera sobre todos os jogadores
        player_iterator = player_manager.iter_players()
        if isinstance(player_iterator, dict):
            player_iterator = player_iterator.items()

        for user_id, p_data in player_iterator:
            if "pvp_points" in p_data and p_data["pvp_points"] != 0:
                try:
                    # Opcional: Guardar histórico aqui antes de zerar, se desejado
                    previous_points = p_data.get("pvp_points", 0)
                    p_data.setdefault("pvp_history", []).append({"date": datetime.datetime.now(datetime.timezone.utc).isoformat(), "points": previous_points})

                    # Reseta os pontos para 0 (ou outro valor base, se preferir)
                    p_data["pvp_points"] = 0

                    # Salva os dados atualizados
                    player_manager.save_player_data(user_id, p_data)
                    reset_count += 1

                    # Opcional: Notificar o jogador sobre o reset
                    try:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text="⚔️ Uma nova temporada PvP começou! Seus pontos de Elo foram resetados. Boa sorte na arena!"
                        )
                        await asyncio.sleep(0.1) # Pequeno delay
                    except Exception:
                        pass # Ignora se não puder notificar

                except Exception as e_player_reset:
                     logger.error(f"Erro ao resetar PvP para jogador {user_id}: {e_player_reset}", exc_info=True)
                     print(f">>> JOB ERROR: Erro ao resetar PvP para {user_id}: {e_player_reset}")

    except Exception as e_iter:
         logger.error(f"Erro CRÍTICO durante a iteração para reset PvP: {e_iter}", exc_info=True)
         print(f">>> JOB ERROR: Erro CRÍTICO durante a iteração para reset PvP: {e_iter}")
         # A tarefa falhou, mas tentará novamente no próximo ciclo

    logger.info(f"Reset da temporada PvP concluído. Pontos de {reset_count} jogadores foram resetados.")
    print(f">>> JOB: Reset da temporada PvP concluído. {reset_count} jogadores resetados.") # Debug

    announcement = "⚔️ **Nova Temporada PvP Iniciada!** ⚔️\n\nTodos os pontos de Elo foram resetados. Que comecem as batalhas pela glória na Arena!"
    try:
        await context.bot.send_message(
            chat_id=ANNOUNCEMENT_CHAT_ID,
            message_thread_id=ANNOUNCEMENT_THREAD_ID, # Envia para o tópico
            text=announcement,
            parse_mode="HTML"
        )
        logger.info(f"Anúncio de nova temporada PvP enviado para o tópico {ANNOUNCEMENT_THREAD_ID} no chat {ANNOUNCEMENT_CHAT_ID}.")
        print(f">>> JOB: Anúncio de nova temporada enviado para Tópico ID {ANNOUNCEMENT_THREAD_ID}.")
    except Exception as e_announce:
         logger.error(f"Falha ao anunciar nova temporada PvP no tópico {ANNOUNCEMENT_THREAD_ID}: {e_announce}")
         print(f">>> JOB ERROR: Falha ao anunciar nova temporada PvP: {e_announce}")
         