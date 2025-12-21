# handlers/job_handler.py
# (VERSÃO REFATORADA: Compatível com JobQueue E Recovery System)

import random
import logging
import math
from typing import Any
from telegram.error import Forbidden
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Módulos do Jogo
from modules import player_manager, game_data, mission_manager, file_ids
from modules.player.premium import PremiumManager

logger = logging.getLogger(__name__)

# --- Helpers ---
def _int(v: Any, default: int = 0) -> int:
    try: return int(v)
    except Exception: return int(default)

def _clamp_float(v: Any, lo: float, hi: float, default: float) -> float:
    try: f = float(v)
    except Exception: f = default
    return max(lo, min(hi, f))

# ==============================================================================
# 1. A LÓGICA PURA (Pode ser chamada pelo Job ou pelo Recovery)
# ==============================================================================
async def execute_collection_logic(
    user_id: int,
    chat_id: int,
    resource_id: str,
    item_id_yielded: str,
    quantity_base: int,
    context: ContextTypes.DEFAULT_TYPE,
    message_id_to_delete: int = None
):
    # --- [INÍCIO DA CORREÇÃO] ADICIONE ISTO AQUI ---
    # Mapa de correção forçada (ID Antigo -> ID Novo)
    FIX_IDS = {
        "minerio_ferro": "minerio_de_ferro",  # Converte o antigo pro novo
        "iron_ore": "minerio_de_ferro",       # Caso tenha sobrado algo em inglês
        # Adicione outros se precisar
    }
    
    # Se o ID que chegou for um dos antigos, trocamos pelo novo imediatamente
    if resource_id in FIX_IDS: 
        resource_id = FIX_IDS[resource_id]
    
    if item_id_yielded in FIX_IDS: 
        item_id_yielded = FIX_IDS[item_id_yielded]
        
    """
    Executa a matemática da coleta, entrega itens e notifica.
    Independente de contexto de Job.
    """
    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return

    # 1. Limpeza de Estado
    state = player_data.get('player_state') or {}
    if state.get('action') == 'collecting':
        player_data['player_state'] = {'action': 'idle'}

    # 2. Tenta deletar mensagem antiga de "Coletando..."
    if message_id_to_delete:
        try: await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
        except: pass

    # 3. Validações de Dados
    if not resource_id:
        return # Dados inválidos, aborta silenciosamente para não spammar erro

    # --- CÁLCULOS (Mantendo sua lógica original) ---
    prof = player_data.get('profession', {}) or {}
    prof_level = _int(prof.get('level', 1), 1)
    
    total_stats = await player_manager.get_player_total_stats(player_data)
    luck_stat = _int(total_stats.get("luck", 5))

    # Quantidade: Base + Nível Profissão
    quantidade_final = quantity_base + prof_level 
    
    # Crítico (Base 3% + Bônus Nível + Bônus Sorte)
    is_crit = False
    chance_critica = 3.0 + (prof_level * 0.1) + (luck_stat * 0.05)
    
    if random.uniform(0, 100) < chance_critica:
        is_crit = True
        quantidade_final *= 2
    
    # --- ENTREGA DO ITEM ---
    final_item_id = item_id_yielded or resource_id
    player_manager.add_item_to_inventory(player_data, final_item_id, quantidade_final)

    # --- ATUALIZA MISSÕES ---
    try:
        # Tenta atualizar missões de coleta
        if mission_manager:
            await mission_manager.update_mission_progress(user_id, 'collect', final_item_id, quantidade_final)
            # Mantendo suporte ao seu formato antigo 'GATHER' se necessário
            # mission_manager.update_mission_progress(player_data, 'GATHER', details={'item_id': final_item_id, 'quantity': quantidade_final})
    except Exception: pass

    # --- XP DE PROFISSÃO ---
    xp_ganho = 0
    level_up_text = ""
    required_profession = game_data.get_profession_for_resource(resource_id)
    
    # Só ganha XP se tiver a profissão certa
    if prof.get('type') == required_profession:
        # XP Base: 3 * Quantidade (sem critico na base, mas a sua lógica multiplicava a base)
        # Sua lógica: xp_base = quantidade_base * 3. Se critico, xp * 2.
        
        # Vamos replicar exato:
        xp_base_unit = 3
        base_calc = (1 + prof_level) * xp_base_unit # Base sem o critico de quantidade
        
        premium = PremiumManager(player_data)
        xp_mult = _clamp_float(premium.get_perk_value('gather_xp_multiplier', 1.0), 1.0, 5.0, 1.0)
        
        xp_ganho = int(base_calc * xp_mult)
        
        if is_crit: 
            xp_ganho *= 2 # Dobra XP no critico também
        
        # Aplica XP
        prof['xp'] = _int(prof.get('xp', 0)) + xp_ganho
        
        # Level Up Loop
        cur_level = prof_level
        while True:
            try: 
                xp_need = int(game_data.get_xp_for_next_collection_level(cur_level))
            except: 
                # Fallback de segurança se game_data falhar
                xp_need = int(100 * (cur_level ** 1.5))
            
            if xp_need <= 0 or prof['xp'] < xp_need: 
                break
                
            prof['xp'] -= xp_need
            cur_level += 1
            prof['level'] = cur_level
            level_up_text += f"\n🆙 Profissão subiu para nível {cur_level}!"
            
        player_data['profession'] = prof

    # --- ITEM RARO (Sorte) ---
    rare_msg = ""
    try:
        current_loc = player_data.get('current_location', 'reino_eldora')
        region_info = (game_data.REGIONS_DATA or {}).get(current_loc, {})
        rare_cfg = region_info.get("rare_resource")
        
        if isinstance(rare_cfg, dict) and rare_cfg.get("key"):
            # Chance: 1% base + Sorte/2000
            chance = 0.01 + (luck_stat / 2000.0)
            if random.random() < chance:
                rare_key = rare_cfg["key"]
                r_info = (game_data.ITEMS_DATA.get(rare_key, {}))
                r_name = r_info.get("display_name", rare_key)
                player_manager.add_item_to_inventory(player_data, rare_key, 1)
                rare_msg = f"\n💎 <b>Achado Raro!</b> +1 {r_name}"
    except Exception: pass

    # --- SALVAR NO BANCO ---
    await player_manager.save_player_data(user_id, player_data)

    # --- NOTIFICAÇÃO ---
    item_info = (game_data.ITEMS_DATA.get(final_item_id, {}))
    item_name = item_info.get("display_name", final_item_id)
    
    crit_msg = "✨ <b>Sorte!</b> Coleta Crítica!\n" if is_crit else ""
    xp_txt = f" (+{xp_ganho} XP)" if xp_ganho > 0 else ""
    
    msg_text = (
        f"{crit_msg}{rare_msg}"
        f"✅ <b>Coleta Finalizada!</b>\n"
        f"Recebeu: <b>{quantidade_final}x {item_name}</b>{xp_txt}"
        f"{level_up_text}"
    )

    # Mídia
    media_key = item_info.get("media_key") or "coleta_sucesso"
    file_data = file_ids.get_file_data(media_key)
    
    current_loc = player_data.get('current_location', 'reino_eldora')
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data=f"open_region:{current_loc}")]])

    try:
        if file_data and file_data.get("id"):
            ftyp = file_data.get("type", "photo")
            if ftyp == "video":
                await context.bot.send_video(chat_id, file_data["id"], caption=msg_text, reply_markup=kb, parse_mode='HTML')
            else:
                await context.bot.send_photo(chat_id, file_data["id"], caption=msg_text, reply_markup=kb, parse_mode='HTML')
        else:
            await context.bot.send_message(chat_id, msg_text, reply_markup=kb, parse_mode='HTML')
            
    except Forbidden:
        logger.warning(f"[Collection] Usuário {user_id} bloqueou o bot. Item entregue.")
    except Exception as e:
        logger.warning(f"Erro ao enviar msg final coleta {user_id}: {e}")


# ==============================================================================
# 2. O WRAPPER DO TELEGRAM (Mantém compatibilidade com JobQueue)
# ==============================================================================
async def finish_collection_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Job chamado pelo scheduler. Extrai dados e chama a lógica.
    """
    job = context.job
    if not job: return

    job_data = job.data or {}
    
    # Extrai dados do job
    user_id = job_data.get('user_id') or job.user_id
    chat_id = job_data.get('chat_id') or job.chat_id
    
    # Busca message_id para apagar a msg de "Trabalhando..." se existir
    msg_id = job_data.get('message_id')
    if not msg_id:
        # Tenta buscar do player_data se não vier no job (fallback)
        try:
            pdata = await player_manager.get_player_data(user_id)
            if pdata:
                msg_id = pdata.get('player_state', {}).get('details', {}).get('collect_message_id')
        except: pass

    await execute_collection_logic(
        user_id=user_id,
        chat_id=chat_id,
        resource_id=job_data.get('resource_id'),
        item_id_yielded=job_data.get('item_id_yielded'),
        quantity_base=job_data.get('quantity', 1),
        context=context,
        message_id_to_delete=msg_id
    )