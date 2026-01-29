# modules/recovery_manager.py

import logging
from datetime import datetime, timezone
from telegram.ext import Application
from modules import player_manager

# Engines & Handlers
from modules import auto_hunt_engine
from handlers import job_handler, forge_handler, refining_handler

logger = logging.getLogger(__name__)


def _parse_finish_time(finish_time_str: str) -> datetime | None:
    if not finish_time_str:
        return None
    try:
        # aceita "...Z"
        dt = datetime.fromisoformat(str(finish_time_str).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _resolve_chat_id(pdata: dict, details: dict) -> int | None:
    """
    Resolve chat_id de forma resiliente:
    - prioriza collect_chat_id / action-specific
    - fallback last_chat_id
    """
    for k in ("collect_chat_id", "chat_id"):
        try:
            v = details.get(k)
            if v is None:
                continue
            v = int(v)
            if v:
                return v
        except Exception:
            pass

    try:
        v = pdata.get("last_chat_id")
        if v is None:
            return None
        v = int(v)
        return v or None
    except Exception:
        return None


def _remove_jobs_by_prefix(app: Application, prefix: str, user_id: str) -> None:
    """
    Remove jobs antigos para idempotência no recovery.
    Os seus jobs atuais seguem o padrão: f"{prefix}_{user_id}"
    """
    try:
        name = f"{prefix}_{user_id}"
        for j in app.job_queue.get_jobs_by_name(name):
            j.schedule_removal()
    except Exception:
        pass


async def recover_active_hunts(app: Application):
    """
    Varre o banco de dados ao iniciar o bot para recuperar ações interrompidas.
    """
    logger.info("🔄 [RECOVERY] Iniciando varredura de ações interrompidas...")

    count_recovered = 0
    count_errors = 0

    try:
        all_user_ids = list(player_manager.iter_player_ids())
    except Exception as e:
        logger.error(f"[RECOVERY] Falha ao listar jogadores: {e}")
        return

    SUPPORTED_ACTIONS = {"auto_hunting", "collecting", "crafting", "refining", "dismantling"}

    for user_id in all_user_ids:
        try:
            pdata = await player_manager.get_player_data(user_id)
            if not pdata:
                continue

            state = pdata.get("player_state", {}) or {}
            action = state.get("action")

            if not action or action == "idle":
                continue

            if action not in SUPPORTED_ACTIONS:
                continue

            details = state.get("details", {}) or {}
            finish_time_str = state.get("finish_time")

            finish_time = _parse_finish_time(finish_time_str)
            if not finish_time:
                # estado inválido -> destrava
                pdata["player_state"] = {"action": "idle"}
                await player_manager.save_player_data(user_id, pdata)
                continue

            now = datetime.now(timezone.utc)
            time_diff = (finish_time - now).total_seconds()
            is_expired = time_diff <= 0

            chat_id = _resolve_chat_id(pdata, details)

            # ====================================================
            # 1) AUTO HUNT
            # ====================================================
            if action == "auto_hunting":
                hunt_count = details.get("hunt_count", 1)
                region_key = details.get("region_key")

                if not chat_id:
                    pdata["player_state"] = {"action": "idle"}
                    await player_manager.save_player_data(user_id, pdata)
                    continue

                _remove_jobs_by_prefix(app, "autohunt", str(user_id))

                if is_expired or time_diff < 1:
                    logger.info(f"[RECOVERY] ⚔️ Finalizando CAÇA pendente para {user_id}")
                    await auto_hunt_engine.execute_hunt_completion(
                        user_id=user_id,
                        chat_id=chat_id,
                        hunt_count=hunt_count,
                        region_key=region_key,
                        context=app,
                        message_id=None,
                    )
                else:
                    logger.info(f"[RECOVERY] ⏱️ Reagendando CAÇA para {user_id} ({int(time_diff)}s)")
                    app.job_queue.run_once(
                        auto_hunt_engine.finish_auto_hunt_job,
                        when=time_diff,
                        data={
                            "user_id": user_id,
                            "chat_id": chat_id,
                            "hunt_count": hunt_count,
                            "region_key": region_key,
                            "message_id": None,
                        },
                        name=f"autohunt_{user_id}",
                    )

                count_recovered += 1
                continue

            # ====================================================
            # 2) COLETA
            # ====================================================
            if action == "collecting":
                resource_id = details.get("resource_id")
                item_id = details.get("item_id_yielded")
                qty = details.get("quantity", 1)
                msg_id = details.get("collect_message_id")

                if not chat_id:
                    pdata["player_state"] = {"action": "idle"}
                    await player_manager.save_player_data(user_id, pdata)
                    continue

                if not resource_id:
                    pdata["player_state"] = {"action": "idle"}
                    await player_manager.save_player_data(user_id, pdata)
                    continue

                _remove_jobs_by_prefix(app, "collect", str(user_id))

                if is_expired or time_diff < 1:
                    logger.info(f"[RECOVERY] ⛏️ Finalizando COLETA para {user_id}")
                    await job_handler.execute_collection_logic(
                        user_id=user_id,
                        chat_id=chat_id,
                        resource_id=resource_id,
                        item_id_yielded=item_id,
                        quantity_base=qty,
                        context=app,
                        message_id_to_delete=msg_id,
                    )
                else:
                    logger.info(f"[RECOVERY] ⏱️ Reagendando COLETA para {user_id} ({int(time_diff)}s)")
                    if hasattr(job_handler, "finish_collection_job"):
                        app.job_queue.run_once(
                            job_handler.finish_collection_job,
                            when=time_diff,
                            data={
                                "user_id": user_id,
                                "chat_id": chat_id,
                                "resource_id": resource_id,
                                "item_id_yielded": item_id,
                                "quantity": qty,
                                "message_id": msg_id,
                            },
                            name=f"collect_{user_id}",
                        )
                    else:
                        logger.warning("[RECOVERY] finish_collection_job não encontrado; mantendo estado para finalizar via fallback.")

                count_recovered += 1
                continue

            # ====================================================
            # 3) FORJA (CRAFTING)
            # ====================================================
            if action == "crafting":
                recipe_id = details.get("recipe_id")
                msg_id = details.get("message_id_notificacao")

                if not chat_id:
                    pdata["player_state"] = {"action": "idle"}
                    await player_manager.save_player_data(user_id, pdata)
                    continue

                _remove_jobs_by_prefix(app, "craft", str(user_id))

                if is_expired or time_diff < 1:
                    logger.info(f"[RECOVERY] 🔨 Finalizando FORJA para {user_id}")
                    await forge_handler.execute_craft_logic(
                        user_id=user_id,
                        chat_id=chat_id,
                        recipe_id=recipe_id,
                        context=app,
                        message_id_to_delete=msg_id,
                    )
                else:
                    logger.info(f"[RECOVERY] ⏱️ Reagendando FORJA para {user_id} ({int(time_diff)}s)")
                    app.job_queue.run_once(
                        forge_handler.finish_craft_notification_job,
                        when=time_diff,
                        data={
                            "user_id": user_id,
                            "chat_id": chat_id,
                            "recipe_id": recipe_id,
                            "message_id_notificacao": msg_id,
                        },
                        name=f"craft_{user_id}",
                    )

                count_recovered += 1
                continue

            # ====================================================
            # 4) REFINO (REFINING)
            # ====================================================
            if action == "refining":
                msg_id = details.get("message_id_to_delete")

                if not chat_id:
                    pdata["player_state"] = {"action": "idle"}
                    await player_manager.save_player_data(user_id, pdata)
                    continue

                _remove_jobs_by_prefix(app, "refine", str(user_id))

                if is_expired or time_diff < 1:
                    logger.info(f"[RECOVERY] 🔧 Finalizando REFINO para {user_id}")
                    await refining_handler.execute_refine_logic(
                        user_id=user_id,
                        chat_id=chat_id,
                        context=app,
                        message_id_to_delete=msg_id,
                    )
                else:
                    logger.info(f"[RECOVERY] ⏱️ Reagendando REFINO para {user_id} ({int(time_diff)}s)")
                    app.job_queue.run_once(
                        refining_handler.finish_refine_job,
                        when=time_diff,
                        data={
                            "user_id": user_id,
                            "chat_id": chat_id,
                            "message_id_to_delete": msg_id,
                        },
                        name=f"refine_{user_id}",
                    )

                count_recovered += 1
                continue

            # ====================================================
            # 5) DESMONTE (DISMANTLING)
            # ====================================================
            if action == "dismantling":
                msg_id = details.get("message_id_to_delete")

                if not chat_id:
                    pdata["player_state"] = {"action": "idle"}
                    await player_manager.save_player_data(user_id, pdata)
                    continue

                _remove_jobs_by_prefix(app, "dismantle", str(user_id))

                if is_expired or time_diff < 1:
                    logger.info(f"[RECOVERY] ♻️ Finalizando DESMONTE para {user_id}")
                    await refining_handler.execute_dismantle_logic(
                        user_id=user_id,
                        chat_id=chat_id,
                        context=app,
                        job_details=details,
                        message_id_to_delete=msg_id,
                    )
                else:
                    logger.info(f"[RECOVERY] ⏱️ Reagendando DESMONTE para {user_id} ({int(time_diff)}s)")

                    d = dict(details or {})
                    d["user_id"] = user_id
                    d["chat_id"] = chat_id
                    if msg_id is not None:
                        d["message_id_to_delete"] = msg_id

                    app.job_queue.run_once(
                        refining_handler.finish_dismantle_job,
                        when=time_diff,
                        data=d,
                        name=f"dismantle_{user_id}",
                    )

                count_recovered += 1
                continue

        except Exception as e:
            logger.error(f"[RECOVERY] Erro ao processar user_id {user_id}: {e}", exc_info=True)
            count_errors += 1
            continue

    logger.info(f"✅ [RECOVERY] Sistema restaurado. {count_recovered} ações recuperadas. {count_errors} erros.")
