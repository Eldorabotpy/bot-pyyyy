# modules/recovery_manager.py

import logging
from datetime import datetime, timezone
from telegram.ext import Application
from modules import player_manager

# Engines & Handlers
from modules import auto_hunt_engine 
from handlers import job_handler, forge_handler, refining_handler

logger = logging.getLogger(__name__)

async def recover_active_hunts(app: Application):
    """
    Varre o banco de dados ao iniciar o bot para recuperar ações.
    """
    logger.info("🔄 [RECOVERY] Iniciando varredura de ações interrompidas...")
    
    count_recovered = 0
    count_errors = 0
    
    # CORREÇÃO: Pega a lista de IDs primeiro (síncrono) e depois processa (assíncrono)
    # Isso evita o erro de 'async for' em gerador síncrono
    try:
        # Tenta pegar todos os IDs numa lista para não travar o cursor
        all_user_ids = list(player_manager.iter_player_ids())
    except Exception as e:
        logger.error(f"[RECOVERY] Falha ao listar jogadores: {e}")
        return

    # Agora iteramos sobre a lista normalmente
    for user_id in all_user_ids:
        try:
            # Carrega dados (Isso é async, então precisa de await)
            pdata = await player_manager.get_player_data(user_id)
            if not pdata: continue

            state = pdata.get('player_state', {})
            action = state.get('action')
            
            # Se não estiver fazendo nada importante, pula
            if not action or action == 'idle': 
                continue

            # Lista de ações suportadas
            SUPPORTED_ACTIONS = ['auto_hunting', 'collecting', 'crafting', 'refining', 'dismantling']
            if action not in SUPPORTED_ACTIONS:
                continue

            details = state.get('details', {})
            finish_time_str = state.get('finish_time')
            chat_id = pdata.get('last_chat_id')

            # --- Validação de Integridade ---
            if not finish_time_str or not chat_id:
                pdata['player_state'] = {'action': 'idle'}
                await player_manager.save_player_data(user_id, pdata)
                continue

            try:
                finish_time = datetime.fromisoformat(finish_time_str)
                if finish_time.tzinfo is None:
                    finish_time = finish_time.replace(tzinfo=timezone.utc)
            except ValueError:
                pdata['player_state'] = {'action': 'idle'}
                await player_manager.save_player_data(user_id, pdata)
                continue
                
            now = datetime.now(timezone.utc)
            time_diff = (finish_time - now).total_seconds()
            is_expired = time_diff <= 0
            
            # ====================================================
            # 1. AUTO HUNT
            # ====================================================
            if action == 'auto_hunting':
                hunt_count = details.get('hunt_count', 1)
                region_key = details.get('region_key')
                
                if is_expired:
                    logger.info(f"[RECOVERY] ⚔️ Finalizando CAÇA pendente para {user_id}")
                    await auto_hunt_engine.execute_hunt_completion(
                        user_id=user_id, chat_id=chat_id,
                        hunt_count=hunt_count, region_key=region_key,
                        context=app, message_id=None
                    )
                else:
                    logger.info(f"[RECOVERY] ⏱️ Reagendando CAÇA para {user_id}")
                    app.job_queue.run_once(
                        auto_hunt_engine.finish_auto_hunt_job,
                        when=time_diff,
                        data={
                            'user_id': user_id, 'chat_id': chat_id, 
                            'hunt_count': hunt_count, 'region_key': region_key, 
                            'message_id': None
                        },
                        name=f"autohunt_{user_id}"
                    )
                count_recovered += 1

            # ====================================================
            # 2. COLETA
            # ====================================================
            elif action == 'collecting':
                resource_id = details.get('resource_id')
                item_id = details.get('item_id_yielded')
                qty = details.get('quantity', 1)
                msg_id = details.get('collect_message_id')

                if is_expired:
                    logger.info(f"[RECOVERY] ⛏️ Finalizando COLETA para {user_id}")
                    await job_handler.execute_collection_logic(
                        user_id=user_id,
                        chat_id=chat_id,
                        resource_id=resource_id,
                        item_id_yielded=item_id,
                        quantity_base=qty,
                        context=app, 
                        message_id_to_delete=msg_id
                    )
                else:
                    logger.info(f"[RECOVERY] ⏱️ Reagendando COLETA para {user_id}")
                    app.job_queue.run_once(
                        job_handler.finish_collection_job,
                        when=time_diff,
                        data={
                            'user_id': user_id, 'chat_id': chat_id,
                            'resource_id': resource_id, 'item_id_yielded': item_id,
                            'quantity': qty, 'message_id': msg_id
                        },
                        name=f"collect_{user_id}"
                    )
                count_recovered += 1

            # ====================================================
            # 3. FORJA (CRAFTING)
            # ====================================================
            elif action == 'crafting':
                recipe_id = details.get("recipe_id")
                msg_id = details.get("message_id_notificacao")

                if is_expired:
                    logger.info(f"[RECOVERY] 🔨 Finalizando FORJA para {user_id}")
                    await forge_handler.execute_craft_logic(
                        user_id=user_id,
                        chat_id=chat_id,
                        recipe_id=recipe_id,
                        context=app,
                        message_id_to_delete=msg_id
                    )
                else:
                    logger.info(f"[RECOVERY] ⏱️ Reagendando FORJA para {user_id}")
                    app.job_queue.run_once(
                        forge_handler.finish_craft_notification_job,
                        when=time_diff,
                        chat_id=chat_id, user_id=user_id,
                        data={"recipe_id": recipe_id, "message_id_notificacao": msg_id},
                        name=f"craft_{user_id}"
                    )
                count_recovered += 1

            # ====================================================
            # 4. REFINO (REFINING)
            # ====================================================
            elif action == 'refining':
                msg_id = details.get("message_id_to_delete")

                if is_expired:
                    logger.info(f"[RECOVERY] 🔧 Finalizando REFINO para {user_id}")
                    await refining_handler.execute_refine_logic(
                        user_id=user_id,
                        chat_id=chat_id,
                        context=app,
                        message_id_to_delete=msg_id
                    )
                else:
                    logger.info(f"[RECOVERY] ⏱️ Reagendando REFINO para {user_id}")
                    app.job_queue.run_once(
                        refining_handler.finish_refine_job,
                        when=time_diff,
                        user_id=user_id, chat_id=chat_id,
                        data={"message_id_to_delete": msg_id},
                        name=f"refine_{user_id}"
                    )
                count_recovered += 1

            # ====================================================
            # 5. DESMONTE (DISMANTLING)
            # ====================================================
            elif action == 'dismantling':
                msg_id = details.get("message_id_to_delete")

                if is_expired:
                    logger.info(f"[RECOVERY] ♻️ Finalizando DESMONTE para {user_id}")
                    await refining_handler.execute_dismantle_logic(
                        user_id=user_id,
                        chat_id=chat_id,
                        context=app,
                        job_details=details,
                        message_id_to_delete=msg_id
                    )
                else:
                    logger.info(f"[RECOVERY] ⏱️ Reagendando DESMONTE para {user_id}")
                    app.job_queue.run_once(
                        refining_handler.finish_dismantle_job,
                        when=time_diff,
                        user_id=user_id, chat_id=chat_id,
                        data=details,
                        name=f"dismantle_{user_id}"
                    )
                count_recovered += 1

        except Exception as e:
            logger.error(f"[RECOVERY] Erro ao processar user_id {user_id}: {e}", exc_info=True)
            count_errors += 1
            continue

    logger.info(f"✅ [RECOVERY] Sistema restaurado. {count_recovered} ações recuperadas. {count_errors} erros.")