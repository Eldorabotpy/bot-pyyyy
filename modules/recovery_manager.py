# modules/recovery_manager.py
# (VERSÃO CORRIGIDA: Usa job_handler em vez de collection_engine)

import logging
from datetime import datetime, timezone
from telegram.ext import Application
from modules import player_manager

# Importa os Engines
from modules import auto_hunt_engine 
# CORREÇÃO: Importa o job_handler em vez do collection_engine inexistente
from handlers import job_handler 

logger = logging.getLogger(__name__)

async def recover_active_hunts(app: Application):
    """
    Varre o banco de dados ao iniciar o bot para:
    1. Finalizar ações que acabaram enquanto o bot estava desligado.
    2. Reagendar ações que ainda não acabaram.
    """
    logger.info("🔄 [RECOVERY] Iniciando varredura de ações interrompidas...")
    
    count_recovered = 0
    count_errors = 0
    
    # Itera de forma segura sobre os IDs
    async for user_id in player_manager.iter_player_ids():
        try:
            # Carrega dados
            pdata = await player_manager.get_player_data(user_id)
            if not pdata: continue

            state = pdata.get('player_state', {})
            action = state.get('action')
            
            # Se não estiver fazendo nada importante, pula
            if not action or action == 'idle': 
                continue

            # Apenas nos interessa Auto-Hunt e Coleta
            if action not in ['auto_hunting', 'collecting']:
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
            # 1. RECUPERAÇÃO DE AUTO HUNT
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
                    logger.info(f"[RECOVERY] ⏱️ Reagendando CAÇA para {user_id} (Faltam {time_diff:.1f}s)")
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
            # 2. RECUPERAÇÃO DE COLETA (CORRIGIDO)
            # ====================================================
            elif action == 'collecting':
                resource_id = details.get('resource_id')
                item_id = details.get('item_id_yielded')
                qty = details.get('quantity', 1)
                msg_id = details.get('collect_message_id')

                if is_expired:
                    logger.info(f"[RECOVERY] ⛏️ Finalizando COLETA para {user_id}")
                    # CORREÇÃO: Chama job_handler.execute_collection_logic
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
                    logger.info(f"[RECOVERY] ⏱️ Reagendando COLETA para {user_id} (Faltam {time_diff:.1f}s)")
                    # CORREÇÃO: Chama job_handler.finish_collection_job
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

        except Exception as e:
            logger.error(f"[RECOVERY] Erro ao processar user_id {user_id}: {e}", exc_info=True)
            count_errors += 1
            continue

    logger.info(f"✅ [RECOVERY] Sistema restaurado. {count_recovered} ações recuperadas.")