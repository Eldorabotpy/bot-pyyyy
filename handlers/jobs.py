# Arquivo: handlers/jobs.py

from __future__ import annotations

import logging
import datetime
import asyncio
from zoneinfo import ZoneInfo
from typing import Dict, Optional
from telegram.ext import ContextTypes
from telegram.error import Forbidden

# Módulos do player
from modules.player_manager import (
    iter_players,
    add_energy,
    save_player_data,
    has_premium_plan,
    get_perk_value,
    get_player_max_energy,
    add_item_to_inventory,
)
from config import EVENT_TIMES, JOB_TIMEZONE

from handlers.refining_handler import finish_dismantle_job

logger = logging.getLogger(__name__)

# --- CONSTANTES ---
DAILY_CRYSTAL_ITEM_ID = "cristal_de_abertura"
DAILY_CRYSTAL_BASE_QTY = 4
#DAILY_TZ = "America/Sao_Paulo"
DAILY_NOTIFY_USERS = True
#DAILY_NOTIFY_TEXT = f"🎁 Você recebeu {DAILY_CRYSTAL_BASE_QTY}× Cristal de Abertura (recompensa diária)."
_non_premium_tick: Dict[str, int] = {"count": 0}


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

# --- WATCHDOG ---
# NOTA: O dicionário ACTION_FINISHERS foi REMOVIDO daqui.

async def timed_actions_watchdog(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Verifica todos os jogadores e finaliza ações cronometradas que já
    deveriam ter terminado (especialmente útil após um reinício do bot).
    """
    # Passo 1: As importações são feitas aqui dentro para quebrar os ciclos.
    from handlers.job_handler import finish_collection_job
    from handlers.menu.region import finish_travel_job
    from handlers.forge_handler import finish_craft_notification_job as finish_crafting_job
    from handlers.refining_handler import finish_refine_job as finish_refining_job

    # Passo 2: O dicionário é definido aqui dentro, usando as funções que acabámos de importar.
    ACTION_FINISHERS = {
        "collecting": {
            "fn": finish_collection_job,
            "data_builder": lambda st: {
                'resource_id': (st.get("details") or {}).get("resource_id"),
                'item_id_yielded': (st.get("details") or {}).get("item_id_yielded"),
                'energy_cost': (st.get("details") or {}).get("energy_cost", 1),
                'speed_mult': (st.get("details") or {}).get("speed_mult", 1.0)
            }
        },
        "travel": {
            "fn": finish_travel_job,
            "data_builder": lambda st: {"dest": (st.get("details") or {}).get("destination")}
        },
        "crafting": {
            "fn": finish_crafting_job,
            "data_builder": lambda st: {"recipe_id": (st.get("details") or {}).get("recipe_id")}
        },
        "refining": {
            "fn": finish_refining_job,
            "data_builder": lambda st: {"recipe_id": (st.get("details") or {}).get("recipe_id")}
        },
        "dismantling": {
            "fn": finish_dismantle_job,
        },    
    }

    now = datetime.datetime.now(datetime.timezone.utc)
    fired = 0
    for user_id, pdata in iter_players():
        try:
            st = pdata.get("player_state") or {}
            action = st.get("action")
            if not action or action not in ACTION_FINISHERS:
                continue
            
            ft = _parse_iso_utc(st.get("finish_time"))
            if not ft or ft > now:
                continue
            
            config = ACTION_FINISHERS[action]
            finalizer_fn = config.get("fn")
            if not finalizer_fn:
                continue
            
            job_data = config["data_builder"](st) if config.get("data_builder") else {}
            chat_id = pdata.get("last_chat_id", user_id)

            # Reagenda a finalização para ser executada imediatamente
            context.job_queue.run_once(
                finalizer_fn, when=0, chat_id=chat_id, user_id=user_id,
                data=job_data, name=f"{action}:{user_id}",
            )
            fired += 1
            logger.info("[WATCHDOG] Finalização da ação '%s' para user %s foi reagendada.", action, user_id)
        except Exception as e:
            logger.warning("[WATCHDOG] Erro ao verificar jogador %s: %s", user_id, e)
    
    if fired:
        logger.info("[WATCHDOG] Disparadas %s finalizações de ações vencidas.", fired)

