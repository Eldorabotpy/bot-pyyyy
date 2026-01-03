# handlers/job_handler.py
# (VERSÃO BLINDADA: Garante o Destravamento com TRY/FINALLY)

import random
import logging
import traceback
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
# 1. A LÓGICA PURA (BLINDADA COM TRY/FINALLY)
# ==============================================================================
async def execute_collection_logic(
    user_id: str, 
    chat_id: int,
    resource_id: str,
    item_id_yielded: str,
    quantity_base: int,
    context: ContextTypes.DEFAULT_TYPE,
    message_id_to_delete: int = None
):
    # --- AUTO-CORREÇÃO DE IDs (Compatibilidade Legado) ---
    FIX_IDS = {
        "minerio_ferro": "minerio_de_ferro",
        "iron_ore": "minerio_de_ferro",
        "pedra_ferro": "minerio_de_ferro",
        "minerio_estanho": "minerio_de_estanho",
        "tin_ore": "minerio_de_estanho",
        "madeira_rara_bruta": "madeira_rara"
    }
    
    if resource_id in FIX_IDS: resource_id = FIX_IDS[resource_id]
    if item_id_yielded in FIX_IDS: item_id_yielded = FIX_IDS[item_id_yielded]
        
    """
    Executa a matemática da coleta, entrega itens e notifica.
    USANDO ESTRUTURA BLINDADA PARA EVITAR TRAVAMENTOS.
    """
    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return

    # 1. Tenta deletar mensagem antiga de "Coletando..." (Cosmético)
    if message_id_to_delete:
        try: await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
        except: pass

    if not resource_id: 
        # Se não tem recurso, destrava e sai
        player_data['player_state'] = {'action': 'idle'}
        await player_manager.save_player_data(user_id, player_data)
        return

    # Variáveis para controle de erro
    sucesso_operacao = False
    
    try:
        # ==========================================================
        # 🔓 DESTRAVAMENTO NA MEMÓRIA (Obrigatório)
        # ==========================================================
        # Definimos como idle aqui, mas só será salvo no 'finally'
        player_data['player_state'] = {'action': 'idle'}
        
        # ==========================================================
        # 🛑 TRAVA DE PROFISSÃO
        # ==========================================================
        prof = player_data.get('profession', {}) or {}
        user_prof_key = prof.get('key') or prof.get('type')
        required_profession = game_data.get_profession_for_resource(resource_id)
        
        if required_profession and user_prof_key != required_profession:
            prof_info = game_data.PROFESSIONS_DATA.get(required_profession, {})
            prof_name_display = prof_info.get('display_name', required_profession.capitalize())
            
            msg_erro = (
                f"❌ <b>Falha na Coleta!</b>\n\n"
                f"Você tentou coletar este recurso, mas não tem o conhecimento necessário.\n"
                f"⚠️ Requisito: Ser um <b>{prof_name_display}</b>."
            )
            current_loc = player_data.get('current_location', 'reino_eldora')
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data=f"open_region:{current_loc}")]])
            await context.bot.send_message(chat_id, msg_erro, reply_markup=kb, parse_mode='HTML')
            return # Sai da função, mas o FINALLY vai rodar e salvar o estado IDLE

        # ==========================================================
        # 🧮 CÁLCULOS E RECOMPENSAS
        # ==========================================================
        prof_level = _int(prof.get('level', 1), 1)
        total_stats = await player_manager.get_player_total_stats(player_data)
        luck_stat = _int(total_stats.get("luck", 5))

        # Quantidade
        quantidade_final = quantity_base + prof_level 
        
        # Crítico
        is_crit = False
        chance_critica = 3.0 + (prof_level * 0.1) + (luck_stat * 0.05)
        if random.uniform(0, 100) < chance_critica:
            is_crit = True
            quantidade_final *= 2
        
        # Entrega Item
        final_item_id = item_id_yielded or resource_id
        player_manager.add_item_to_inventory(player_data, final_item_id, quantidade_final)

        # Atualiza Missões (Protegido)
        try:
            if mission_manager:
                await mission_manager.update_mission_progress(user_id, 'collect', final_item_id, quantidade_final)
        except Exception: pass

        # XP Profissão
        xp_base_unit = 3
        base_calc = (1 + prof_level) * xp_base_unit
        premium = PremiumManager(player_data)
        xp_mult = _clamp_float(premium.get_perk_value('gather_xp_multiplier', 1.0), 1.0, 5.0, 1.0)
        
        xp_ganho = int(base_calc * xp_mult)
        if is_crit: xp_ganho *= 2
        
        prof['xp'] = _int(prof.get('xp', 0)) + xp_ganho
        
        # Level Up Loop
        cur_level = prof_level
        level_up_text = ""
        while True:
            try: xp_need = int(game_data.get_xp_for_next_collection_level(cur_level))
            except: xp_need = int(100 * (cur_level ** 1.5))
            
            if xp_need <= 0 or prof['xp'] < xp_need: break
                
            prof['xp'] -= xp_need
            cur_level += 1
            prof['level'] = cur_level
            level_up_text += f"\n🆙 Profissão subiu para nível {cur_level}!"
            
        player_data['profession'] = prof

        # Item Raro (Sorte)
        rare_msg = ""
        try:
            current_loc = player_data.get('current_location', 'reino_eldora')
            region_info = (game_data.REGIONS_DATA or {}).get(current_loc, {})
            rare_cfg = region_info.get("rare_resource")
            
            if isinstance(rare_cfg, dict) and rare_cfg.get("key"):
                chance = 0.01 + (luck_stat / 2000.0)
                if random.random() < chance:
                    rare_key = rare_cfg["key"]
                    r_info = (game_data.ITEMS_DATA.get(rare_key, {}))
                    r_name = r_info.get("display_name", rare_key)
                    player_manager.add_item_to_inventory(player_data, rare_key, 1)
                    rare_msg = f"\n💎 <b>Achado Raro!</b> +1 {r_name}"
        except Exception: pass

        # Prepara Mensagem de Sucesso
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
            logger.warning(f"[Collection] Usuário {user_id} bloqueou o bot.")
        except Exception:
            await context.bot.send_message(chat_id, msg_text, reply_markup=kb, parse_mode='HTML')

        sucesso_operacao = True

    except Exception as e:
        logger.error(f"❌ [Collection] ERRO CRÍTICO usuário {user_id}: {e}")
        traceback.print_exc()
        try:
            await context.bot.send_message(chat_id, "⚠️ Ocorreu um erro na coleta, mas você foi destravado.")
        except: pass
        
    finally:
        # ==========================================================
        # 🔓 O SALVAMENTO FINAL OBRIGATÓRIO (BLINDAGEM)
        # ==========================================================
        # Isso garante que, independente do erro acima, o jogador
        # seja salvo como 'idle' e seus itens sejam persistidos.
        try:
            await player_manager.save_player_data(user_id, player_data)
        except Exception as e:
            logger.critical(f"❌ [Collection] FALHA AO SALVAR DADOS DE {user_id}: {e}")

# ==============================================================================
# 2. O WRAPPER DO TELEGRAM (MANTIDO E PROTEGIDO)
# ==============================================================================
async def finish_collection_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Job chamado pelo scheduler.
    """
    job = context.job
    if not job: return

    job_data = job.data or {}
    
    # --- RECUPERAÇÃO SEGURA DO ID ---
    raw_uid = job_data.get('user_id') or job.user_id
    user_id = str(raw_uid) # Garante String para Auth
    
    chat_id = job_data.get('chat_id') or job.chat_id
    
    # Injeção de Sessão
    if context.user_data is not None:
        context.user_data['logged_player_id'] = user_id
    
    msg_id = job_data.get('message_id')
    if not msg_id:
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