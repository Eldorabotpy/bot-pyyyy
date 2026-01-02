# handlers/work_handler.py
# (VERSÃO FINAL: AUTH UNIFICADA + ID SEGURO)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from datetime import timedelta
from modules import player_manager, game_data
from modules.profession_engine import WORK_RECIPES, preview_work, start_work, finish_work
from modules.auth_utils import get_current_player_id  # <--- ÚNICA FONTE DE VERDADE

logger = logging.getLogger(__name__)

def _humanize(seconds: int) -> str:
    if seconds >= 60:
        m = round(seconds/60)
        return f"{m} min"
    return f"{int(seconds)} s"

async def show_work_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # 🔒 SEGURANÇA: ID via Auth Central
    user_id = get_current_player_id(update, context)
    
    if not user_id:
        await query.answer("Sessão inválida. Use /start.", show_alert=True)
        return

    # <<< CORREÇÃO 1: Adiciona await >>>
    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
         # Adiciona um fallback se os dados do jogador não forem encontrados
         try: await query.edit_message_text("Erro ao carregar dados. Tente /start.")
         except: pass
         return

    # Lógica síncrona
    prof = pdata.get('profession', {}) or {}
    prof_type = prof.get('type')
    if not prof_type or prof_type not in game_data.PROFESSIONS_DATA or game_data.PROFESSIONS_DATA[prof_type]['category'] != 'crafting':
        await query.answer("Você não tem uma profissão de produção/forja.", show_alert=True)
        return

    text = f"<b>Trabalhos de {game_data.PROFESSIONS_DATA[prof_type]['display_name']} (Nível {prof.get('level',1)})</b>\nSelecione:"
    kb = []

    # Loop síncrono
    for rid, rec in WORK_RECIPES.items():
        if rec.get('profession') != prof_type:
            continue
        prev = preview_work(rid, pdata) # Assumindo preview_work síncrono
        mark = "✅" if prev['can_work'] else "❌"
        t = _humanize(prev['duration_seconds'])
        kb.append([InlineKeyboardButton(f"{mark} {rec['display_name']} (Nvl {rec['level_req']}, ~{t})", callback_data=f"work_start_{rid}")])

    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="continue_after_action")])
    rm = InlineKeyboardMarkup(kb)

    try:
        await query.edit_message_text(text=text, reply_markup=rm, parse_mode='HTML')
    except Exception:
        await context.bot.send_message(chat_id=query.message.chat_id, text=text, reply_markup=rm, parse_mode='HTML')

async def start_work_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # 🔒 SEGURANÇA: ID via Auth Central
    user_id = get_current_player_id(update, context)
    chat_id = query.message.chat_id
    
    if not user_id:
        await query.answer("Sessão inválida.", show_alert=True)
        return

    rid = query.data.replace("work_start_", "")

    # <<< CORREÇÃO 2: Adiciona await e carrega pdata >>>
    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
         await query.answer("Erro ao carregar dados do jogador!", show_alert=True)
         return
         
    # Adiciona verificação de estado (movida de finish_work)
    state = pdata.get("player_state", {})
    if state.get("action") not in (None, "idle"):
         await query.answer("Você já está ocupado com outra ação!", show_alert=True)
         return

    # <<< CORREÇÃO 3: Adiciona await e passa pdata >>>
    res = await start_work(pdata, rid) # Assumindo que start_work é async e espera pdata
    
    if isinstance(res, dict) and res.get("error"):
        await query.answer(res["error"], show_alert=True); return
        
    # Salva o pdata modificado pelo start_work (que define o estado 'working')
    # <<< CORREÇÃO 4: Adiciona await >>>
    await player_manager.save_player_data(user_id, pdata)

    duration = int(res["duration_seconds"])
    
    # Agendamento do Job com ID Seguro
    job_data = {
        "recipe_id": rid,
        "user_id": user_id  # String ID
    }
    
    context.job_queue.run_once(
        _finish_work_job, 
        when=duration, 
        chat_id=chat_id,
        user_id=int(user_id) if str(user_id).isdigit() else None, # Opcional para legado
        data=job_data,
        name=f"work_{user_id}"
    )

    try:
        await query.edit_message_text(text=f"🛠️ Trabalho iniciado! Conclusão em ~{_humanize(duration)}.", parse_mode='HTML')
    except Exception:
        await context.bot.send_message(chat_id=chat_id, text=f"🛠️ Trabalho iniciado! Conclusão em ~{_humanize(duration)}.", parse_mode='HTML')

async def _finish_work_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    if not job: return
    
    # Recupera ID seguro (String)
    data = job.data or {}
    raw_uid = data.get("user_id") or job.user_id
    user_id = str(raw_uid)
    chat_id = job.chat_id
    recipe_id = data.get("recipe_id")

    # <<< CORREÇÃO 5: Adiciona await e carrega pdata >>>
    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
         logger.error(f"_finish_work_job: pdata não encontrado para {user_id}")
         try: await context.bot.send_message(chat_id=chat_id, text="Erro ao finalizar trabalho: jogador não encontrado.")
         except: pass
         return

    # <<< CORREÇÃO 6: Adiciona await e passa pdata >>>
    out = await finish_work(pdata) # Assumindo que finish_work é async e espera pdata

    # O pdata foi modificado pelo finish_work (itens adicionados, estado = idle)
    # Agora precisamos salvar essas alterações.
    
    # <<< CORREÇÃO 7: Adiciona await >>>
    await player_manager.save_player_data(user_id, pdata)

    # Envia a notificação de sucesso ou falha
    if out.get("status") == "success":
        name = game_data.ITEMS_DATA.get(out["result_base_id"], {}).get("display_name", out["result_base_id"])
        await context.bot.send_message(chat_id=chat_id, text=f"✅ Trabalho concluído! Você produziu: {name}.")
    else:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Trabalho não foi concluído: {out.get('error','erro desconhecido')}")

work_main_handler = CallbackQueryHandler(show_work_list, pattern=r'^(forge|work_show_list)$')
work_start_handler = CallbackQueryHandler(start_work_callback, pattern=r'^work_start_')