# Arquivo: handlers/jobs.py

from __future__ import annotations

import logging
import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Optional
from telegram.ext import ContextTypes

# Módulos do player
from modules.player_manager import (
    iter_players,
    add_energy,
    save_player_data,
    is_player_premium,
    get_player_max_energy,
    add_item_to_inventory,
)

from handlers.refining_handler import finish_dismantle_job

# NOTA: As importações de finalização de jobs foram REMOVIDAS daqui
# para resolver o erro de ciclo de importação.

logger = logging.getLogger(__name__)

# --- CONSTANTES ---
DAILY_CRYSTAL_ITEM_ID = "cristal_de_abertura"
DAILY_CRYSTAL_QTY = 4
DAILY_TZ = "America/Fortaleza"
DAILY_NOTIFY_USERS = True
DAILY_NOTIFY_TEXT = f"🎁 Você recebeu {DAILY_CRYSTAL_QTY}× Cristal de Abertura (recompensa diária)."
_non_premium_tick: Dict[str, int] = {"count": 0}


# --- HELPERS ---
def _today_str(tzname: str = DAILY_TZ) -> str:
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
            premium = bool(is_player_premium(pdata))
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
            _safe_add_stack(pdata, DAILY_CRYSTAL_ITEM_ID, DAILY_CRYSTAL_QTY)
            daily["last_crystal_date"] = today
            pdata["daily_awards"] = daily
            save_player_data(user_id, pdata)
            granted += 1
            if DAILY_NOTIFY_USERS:
                try: await context.bot.send_message(chat_id=user_id, text=DAILY_NOTIFY_TEXT)
                except Exception: pass
        except Exception as e:
            logger.warning("[DAILY] Falha ao conceder cristais para %s: %s", user_id, e)
    logger.info("[DAILY] Rotina normal: %s jogadores receberam cristais.", granted)
    return granted


async def force_grant_daily_crystals(context: ContextTypes.DEFAULT_TYPE) -> int:
    granted = 0
    for user_id, pdata in iter_players():
        try:
            _safe_add_stack(pdata, DAILY_CRYSTAL_ITEM_ID, DAILY_CRYSTAL_QTY)
            daily = pdata.get("daily_awards") or {}
            daily["last_crystal_date"] = _today_str()
            pdata["daily_awards"] = daily
            save_player_data(user_id, pdata)
            granted += 1
            if DAILY_NOTIFY_USERS:
                try: await context.bot.send_message(chat_id=user_id, text=DAILY_NOTIFY_TEXT)
                except Exception: pass
        except Exception as e:
            logger.warning("[ADMIN_FORCE_DAILY] Falha ao forçar cristais para %s: %s", user_id, e)
    logger.info("[ADMIN_FORCE_DAILY] Cristais concedidos forçadamente para %s jogadores.", granted)
    return granted


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