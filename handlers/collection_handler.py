# handlers/collection_handler.py

from __future__ import annotations

from typing import Any
import logging
import random
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

# Módulos do Jogo
from modules import player_manager, game_data
from modules import file_ids as file_id_manager
from modules.player.actions import _collect_duration_seconds, _gather_cost, _gather_xp_mult
from modules.player.premium import PremiumManager
from handlers.utils_timed import schedule_or_replace_job

# Adiciona importações de Missão/Guilda de forma segura (embora não sejam usadas)
try: from modules import clan_manager, mission_manager
except ImportError: clan_manager = None; mission_manager = None

logger = logging.getLogger(__name__)


# =============================================================================
# Helpers
# =============================================================================
def _humanize(seconds: int) -> str:
    seconds = int(seconds)
    if seconds >= 60:
        m = round(seconds / 60)
        return f"{m} min"
    return f"{seconds} s"

def _get_media_key_for_item(item_id: str) -> str:
    if not item_id: return ""
    items_data = getattr(game_data, "ITEMS_DATA", {}) or {}
    item_info = items_data.get(item_id)
    if item_info and (media_key := item_info.get("media_key")):
        return media_key
    return item_id

def _int(v: Any, default: int = 0) -> int:
    try: return int(v)
    except Exception: return int(default)

async def finish_collection_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Finaliza a coleta. Missões e Guilda foram REMOVIDAS. Inclui deleção da mensagem anterior.
    """
    job = context.job
    if not job: return
    user_id = job.user_id
    chat_id = job.chat_id
    
    # Pré-carrega os dados do jogador (o job.data tem o resource_id, mas precisamos do player_data)
    player_data = None
    try:
        player_data = await player_manager.get_player_data(user_id)
        if not player_data: return

        # === DELEÇÃO DA MENSAGEM ANTERIOR (DEVE ESTAR AQUI) ===
        if player_data.get("player_state", {}).get("details", {}).get("collect_message_id"):
            message_id_to_delete = player_data["player_state"]["details"]["collect_message_id"]
            # Tenta deletar. Se falhar (msg muito antiga ou já deletada), ignora.
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
        # =======================================================

        state = player_data.get("player_state") or {}
        if state.get("action") != "collecting":
            return

        details = state.get("details", {})
        resource_key = details.get("resource_id")
        
        if not resource_key:
            await context.bot.send_message(chat_id=chat_id, text="❌ Erro: ID do recurso não encontrado no estado.")
            player_data["player_state"] = {"action": "idle"}
            await player_manager.save_player_data(user_id, player_data)
            return

        resource_info = (game_data.ITEMS_DATA or {}).get(resource_key)
        if not resource_info:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Erro: Item '{resource_key}' não existe em game_data.ITEMS_DATA.")
            player_data["player_state"] = {"action": "idle"}
            await player_manager.save_player_data(user_id, player_data)
            return

        # ========================= 1. Cálculos (Seguro) =========================
        profession_data = player_data.get("profession", {}) or {}
        profession_lvl = _int(profession_data.get("level", 1))
        
        # Stats
        try:
            total_stats = player_manager.get_player_total_stats(player_data)
            luck_stat = _int(total_stats.get("luck", 5))
        except Exception:
            luck_stat = 5

        # Quantidade (Multiplicador de 1.0)
        base_qty = _int(resource_info.get("base_quantity", 1))
        level_multiplier = 1.0 
        quantity_bonus = int(profession_lvl * level_multiplier)
        
        luck_bonus = 0
        if luck_stat >= 20:
            luck_bonus = random.randint(0, int(luck_stat / 50))

        amount_collected = base_qty + quantity_bonus + luck_bonus

        # XP
        base_xp = _int(resource_info.get("base_xp", 5))
        xp_level_bonus = (profession_lvl - 1) * 0.5
        try: xp_mult_perks = _gather_xp_mult(player_data)
        except: xp_mult_perks = 1.0
        xp_gain = int(round((base_xp + xp_level_bonus) * xp_mult_perks))
        
        # Crítico
        critical_chance = 0.05 + (luck_stat / 200.0)
        is_critical = random.random() < critical_chance
        critical_message = ""
        if is_critical:
            amount_collected *= 2
            xp_gain = int(xp_gain * 1.5)
            critical_message = "✨ <b>𝑪𝒐𝒍𝒆𝒕𝒂 𝑪𝒓𝒊́𝒕𝒊𝒄𝒂!</b> Dobrou os ganhos!\n"


        # ========================= 2. Entrega de Itens (Essencial) =========================
        player_manager.add_item_to_inventory(player_data, resource_key, amount_collected)
        
        # ========================= 3. Recurso Raro (Isolado) =========================
        rare_find_message = ""
        try:
            region_info = (game_data.REGIONS_DATA or {}).get(player_data.get('current_location', ''), {})
            rare_cfg = region_info.get("rare_resource")
            if isinstance(rare_cfg, dict) and rare_cfg.get("key"):
                rare_chance = 0.10 + (luck_stat / 150.0)
                if random.random() < rare_chance:
                    rare_key = rare_cfg["key"]
                    rare_item_info = game_data.ITEMS_DATA.get(rare_key, {})
                    rare_name = rare_item_info.get("display_name", rare_key)
                    player_manager.add_item_to_inventory(player_data, rare_key, 1)
                    rare_find_message = f"💎 Sorte! Encontrou 1x {rare_name}!\n"
        except Exception as e_rare:
            logger.error(f"Erro calculo raro user {user_id}: {e_rare}")

        # ========================= 4. Level Up Profissão (Isolado) =========================
        level_up_message = ""
        current_prof_level = profession_lvl
        try:
            profession_data["xp"] = _int(profession_data.get("xp", 0)) + xp_gain
            if hasattr(game_data, 'get_xp_for_next_collection_level'):
                xp_needed = _int(game_data.get_xp_for_next_collection_level(current_prof_level))
                while xp_needed > 0 and profession_data["xp"] >= xp_needed:
                    current_prof_level += 1
                    profession_data["level"] = current_prof_level
                    profession_data["xp"] -= xp_needed
                    prof_type = profession_data.get("type", "")
                    prof_name = (game_data.PROFESSIONS_DATA or {}).get(prof_type, {}).get("display_name", "Profissão")
                    level_up_message += f"\n🎉 Sua profissão de {prof_name} subiu para o nível {current_prof_level}!"
                    xp_needed = _int(game_data.get_xp_for_next_collection_level(current_prof_level))
        except Exception as e_lvl:
            logger.error(f"Erro level up profissão {user_id}: {e_lvl}")

        # ========================= 5. SALVAR E FINALIZAR =========================
        profession_data["level"] = current_prof_level
        player_data["profession"] = profession_data
        player_data["player_state"] = {"action": "idle"}
        
        await player_manager.save_player_data(user_id, player_data)

        # Mensagem
        raw_display_name = resource_info.get("display_name")
        # --- CORREÇÃO FINAL ROBUSTA (Nome do Item) ---
        if raw_display_name:
            res_name = str(raw_display_name)
        else:
            res_name = str(resource_key or "ITEM_SEM_NOME")
        # ---------------------------------------------

        region_info = (game_data.REGIONS_DATA or {}).get(player_data.get('current_location', ''), {})
        region_display_name = region_info.get('display_name', 'Local')
        
        caption = (
            f"{critical_message}{rare_find_message}"
            f"✅ <b>Coleta finalizada!</b>\n"
            f"Obteve <b>{amount_collected}x {res_name}</b> (+<b>{xp_gain}</b> XP)"
            f"{level_up_message}\n\n"
            f"Você está em <b>{region_display_name}</b>."
        )

        keyboard = [
            [InlineKeyboardButton("🖐️ Coletar novamente", callback_data=f"collect_{resource_key}")],
            [InlineKeyboardButton("🗺️ Voltar ao Mapa", callback_data="travel")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Envio Mídia
        image_key = _get_media_key_for_item(resource_key)
        file_data = file_id_manager.get_file_data(image_key)
        try:
            if file_data and file_data.get("id"):
                fid = file_data["id"]
                ftyp = (file_data.get("type") or "photo").lower()
                if ftyp == "video":
                    await context.bot.send_video(chat_id=chat_id, video=fid, caption=caption, reply_markup=reply_markup, parse_mode="HTML")
                else:
                    await context.bot.send_photo(chat_id=chat_id, photo=fid, caption=caption, reply_markup=reply_markup, parse_mode="HTML")
            else:
                await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML")
        except Exception:
            await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML")

    except Exception as e_fatal:
        error_msg = f"⚠️ ERRO DE CÓDIGO: {str(e_fatal)}"
        logger.exception(f"Erro Fatal Coleta {user_id}: {e_fatal}")
        try:
            if player_data: # Tenta resetar estado se os dados existirem
                player_data['player_state'] = {'action': 'idle'}
                await player_manager.save_player_data(user_id, player_data)
            await context.bot.send_message(chat_id=chat_id, text=error_msg)
        except: pass

async def collection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Inicia coleta com bloqueio visual. Salva o ID da mensagem para deleção.
    """
    query = update.callback_query
    if not query or not query.message: return
    await query.answer()

    user_id = query.from_user.id
    chat_id = query.message.chat_id

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        try: await query.edit_message_text("Erro: Personagem não carregou.")
        except: pass
        return

    data = (query.data or "")
    target_key = data.replace("collect_", "", 1)

    # ========================= RECUPERAÇÃO DE ESTADO TRAVADO =========================
    state = player_data.get("player_state") or {"action": "idle"}
    
    if state.get("action") == "collecting":
        finish_time_str = state.get("finish_time")
        if finish_time_str:
            try:
                ft = datetime.fromisoformat(finish_time_str)
                if datetime.now(timezone.utc) > ft:
                    await query.answer("Recuperando coleta perdida...")
                    
                    # Cria um objeto job simulado para rodar a finalização
                    job_simulated = type('SimulatedJob', (object,), {
                        'user_id': user_id,
                        'chat_id': chat_id,
                        'data': state.get('details', {}) # Usar .get para evitar KeyError
                    })()
                    
                    original_job = context.job
                    context.job = job_simulated
                    
                    await finish_collection_job(context)
                    
                    context.job = original_job
                    return 
                
            except Exception as e_recovery:
                logger.error(f"Erro na recuperação de estado travado {user_id}: {e_recovery}")
                player_data["player_state"] = {"action": "idle"}
                await player_manager.save_player_data(user_id, player_data)
                await query.answer("Aviso: Erro na recuperação. Personagem liberado.")
                return 

    if state.get("action") not in (None, "idle"):
        await query.answer(f"Ocupado: {state.get('action')}", show_alert=True)
        return
    # ==================================================================================

    # --- INÍCIO DA NOVA COLETA ---
    # 1. Busca recurso
    resource_key = target_key
    resource_info = (game_data.ITEMS_DATA or {}).get(resource_key)

    # 2. Se não achou, tenta via região
    if not resource_info:
        region_check = (game_data.REGIONS_DATA or {}).get(target_key)
        if region_check and "resource" in region_check:
            resource_key = region_check["resource"]
            resource_info = (game_data.ITEMS_DATA or {}).get(resource_key)

    if not resource_info:
        await query.answer(f"Erro: Item/Recurso '{target_key}' não encontrado no banco de dados.", show_alert=True)
        return

    # Validação Local
    current_location = player_data.get('current_location')
    region_info = (game_data.REGIONS_DATA or {}).get(current_location, {})
    if region_info.get("resource") != resource_key:
         expected_res = region_info.get("resource", "nada")
         if expected_res != resource_key:
             await query.answer(f"Você não pode coletar esse recurso aqui.", show_alert=True)
             return

    # Validação Profissão (Restante do código...)
    req_prof = game_data.get_profession_for_resource(resource_key)
    cur_prof = (player_data.get("profession") or {}).get("type")
    if req_prof and cur_prof != req_prof:
        req_name = (game_data.PROFESSIONS_DATA or {}).get(req_prof, {}).get("display_name", "???")
        await query.answer(f"Precisa ser {req_name}.", show_alert=True)
        return

    # Custo
    cost = _gather_cost(player_data)
    duration_seconds = _collect_duration_seconds(player_data)
    try:
        premium_temp = PremiumManager(player_data)
        speed_mult = float(premium_temp.get_perk_value("gather_speed_multiplier", 1.0))
    except: speed_mult = 1.0

    # Energia
    if cost > 0:
        current_energy = _int(player_data.get('energy', 0))
        if current_energy < cost:
            await query.answer("Sem energia!", show_alert=True)
            return
        player_data['energy'] = current_energy - cost

    # Salva estado inicial (sem ID da mensagem ainda)
    player_manager.ensure_timed_state(
        pdata=player_data, action="collecting", seconds=duration_seconds,
        details={"region_key": current_location, "resource_id": resource_key, "energy_cost": cost, "speed_mult": speed_mult, "collect_message_id": None }, # Limpa ID antigo
        chat_id=chat_id,
    )
    # A primeira chamada de save_player_data é feita APÓS o envio da mensagem!
    # await player_manager.save_player_data(user_id, player_data) # REMOVIDO DAQUI

    # Agenda
    job_data_for_finish = {"resource_id": resource_key, "region_key": current_location}
    schedule_or_replace_job(
        context=context, job_id=f"collect:{user_id}", when=duration_seconds,
        callback=finish_collection_job,
        data=job_data_for_finish,
        chat_id=chat_id, user_id=user_id,
    )

    # Visual
    human = _humanize(duration_seconds)
    cost_txt = "grátis" if cost == 0 else f"-{cost} ⚡️"
    
    caption = (
        f"⛏️ <b>Coletando...</b>\n"
        f"⏳ Tempo: {human}\n"
        f"⚡ Custo: {cost_txt}\n\n"
        f"⚠️ <i>Você está ocupado e não pode realizar outras ações até terminar.</i>"
    )

    collect_key = f"coleta_{current_location}"
    file_data = file_id_manager.get_file_data(collect_key)

    kb_list = [[InlineKeyboardButton("⏳ Trabalhando...", callback_data="chk_status_busy")]]
    kb = InlineKeyboardMarkup(kb_list)

    try: await query.delete_message()
    except: pass

    msg = None
    try:
        # Envio de Mídia/Mensagem
        if file_data and file_data.get("id"):
            fid = file_data["id"]
            ftyp = (file_data.get("type") or "photo").lower()
            if ftyp == "video":
                msg = await context.bot.send_video(chat_id=chat_id, video=fid, caption=caption, reply_markup=kb, parse_mode="HTML")
            else:
                msg = await context.bot.send_photo(chat_id=chat_id, photo=fid, caption=caption, reply_markup=kb, parse_mode="HTML")
        else:
            msg = await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=kb, parse_mode="HTML")
    except Exception as e_send_start:
        logger.error(f"Falha ao enviar msg 'Coletando...' {chat_id}: {e_send_start}")
        await query.answer("Erro interface coleta.", show_alert=True)
        return

    # >>> AÇÃO CRÍTICA: SALVA O ID DA MENSAGEM PARA DELETAR DEPOIS <<<
    # Esta é a ÚNICA forma de garantir que o ID é salvo e associado à coleta
    if msg and hasattr(msg, 'message_id'):
        message_id = msg.message_id
        
        # Garante que o dict 'details' existe (já foi criado antes, mas segurança extra)
        player_data["player_state"].setdefault("details", {})
        player_data["player_state"]["details"]["collect_message_id"] = message_id
        
        # IMPORTANTE: Salvar AGORA o player data com o ID da mensagem.
        await player_manager.save_player_data(user_id, player_data)
    else:
        logger.warning(f"Falha ao obter message_id para user {user_id}. A mensagem não será deletada.")

# =============================================================================
# Exports
# =============================================================================
collection_handler = CallbackQueryHandler(collection_callback, pattern=r"^collect_[A-Za-z0-9_]+$")