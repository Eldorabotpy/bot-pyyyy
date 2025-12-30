# pvp/pvp_handler.py
# (VERSÃO 6.0: Híbrido - Usa Entradas Diárias ou Tickets)

import logging
import random
import datetime
import html
import asyncio

# --- Imports Necessários ---
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaVideo
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

# --- Módulos do Sistema ---
from modules import player_manager, file_ids, game_data
from modules.player.core import players_collection 

from .pvp_config import ARENA_MODIFIERS, MONTHLY_RANKING_REWARDS
from . import pvp_battle
from . import pvp_config
from . import pvp_utils
from . import tournament_system

logger = logging.getLogger(__name__)

PVP_PROCURAR_OPONENTE = "pvp_procurar_oponente"
PVP_RANKING = "pvp_ranking"
PVP_HISTORICO = "pvp_historico"

# =============================================================================
# FUNÇÃO AUXILIAR SEGURA
# =============================================================================
async def aplicar_resultado_pvp_seguro(user_id, pontos_delta, ouro_delta=0):
    """
    Salva pontos e ouro diretamente no MongoDB (Atomic Update).
    """
    if players_collection is None: 
        return False
        
    try:
        updates = {}
        if pontos_delta != 0: updates["pvp_points"] = pontos_delta
        if ouro_delta != 0: updates["gold"] = ouro_delta 
        
        if updates:
            players_collection.update_one({"_id": user_id}, {"$inc": updates})
            await player_manager.clear_player_cache(user_id) 
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar PvP seguro para {user_id}: {e}")
        return False

# =============================================================================
# HANDLERS DO TORNEIO
# =============================================================================
async def torneio_signup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    success, msg = await tournament_system.registrar_jogador(query.from_user.id)
    await query.answer(msg, show_alert=True)
    if success: await pvp_menu_command(update, context)

async def torneio_ready_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    msg = await tournament_system.confirmar_prontidao(query.from_user.id, context)
    await query.answer(msg, show_alert=True)
    await pvp_menu_command(update, context)

# =============================================================================
# HANDLERS PRINCIPAIS
# =============================================================================

async def procurar_oponente_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query.message:
        return

    original_message_is_media = bool(query.message.photo or query.message.video or query.message.animation)
        
    await query.answer("🔍 Analisando seus recursos de batalha...")
    user_id = query.from_user.id
    
    # 1. Carrega dados
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await query.answer("Erro ao carregar dados.", show_alert=True)
        return

    # 2. SISTEMA HÍBRIDO DE ENTRADA (CORREÇÃO AQUI)
    # Verifica primeiro as entradas diárias (resetam todo dia)
    # Se não tiver, verifica tickets (item de inventário)
    
    pvp_entries = player_data.get("pvp_entries_left", 0)
    ticket_id = "ticket_arena"
    
    usar_entrada_diaria = False
    
    if pvp_entries > 0:
        usar_entrada_diaria = True
    elif player_manager.has_item(player_data, ticket_id, quantity=1):
        usar_entrada_diaria = False
    else:
        # Se não tiver nenhum dos dois
        current_tickets = player_data.get('inventory', {}).get(ticket_id, 0)
        item_name = game_data.ITEMS_DATA.get(ticket_id, {}).get('display_name', "Ticket de Arena")
        
        await context.bot.answer_callback_query(
            query.id, 
            f"⛔ Você está sem energia!\n\nEntradas Diárias: 0\n{item_name}: {current_tickets}\n\nAguarde o reset diário ou use um Ticket.", 
            show_alert=True
        )
        return

    # 3. Busca Oponentes (LÓGICA OTIMIZADA)
    # Salva dados (necessário se tiver alterações pendentes, mas o consumo vem depois)
    await player_manager.save_player_data(user_id, player_data) 
    
    today_weekday = datetime.datetime.now().weekday()
    modifier = ARENA_MODIFIERS.get(today_weekday)
    current_effect = modifier.get("effect") if modifier else None

    my_points = player_manager.get_pvp_points(player_data)
    opponents_found = []
    
    try:
        if players_collection is not None:
            pipeline = [
                {"$match": {"_id": {"$ne": user_id}}},
                {"$match": {"level": {"$gte": 1}}},
                {"$sample": {"size": 30}}
            ]
            cursor = players_collection.aggregate(pipeline)
            potential_opponents = list(cursor)
            
            match_perfeito = []   # +/- 300 pontos
            match_aceitavel = []  # +/- 1000 pontos
            match_qualquer = []   # Resto
            
            for opp in potential_opponents:
                try:
                    opp_points = opp.get("pvp_points", 0)
                    diff = abs(my_points - opp_points)
                    opp_id = opp["_id"]
                    
                    if diff <= 300: match_perfeito.append(opp_id)
                    elif diff <= 1000: match_aceitavel.append(opp_id)
                    else: match_qualquer.append(opp_id)
                except Exception: continue
            
            if match_perfeito: opponents_found = match_perfeito
            elif match_aceitavel: opponents_found = match_aceitavel
            else: opponents_found = match_qualquer
        else:
            async for opponent_id, opp_data in player_manager.iter_players():
                if opponent_id == user_id: continue
                opponents_found.append(opponent_id)

    except Exception:
        await query.answer("Erro técnico na busca.", show_alert=True)
        return

    # 4. Decisão Final e Combate
    if opponents_found:
        final_opponent_id = random.choice(opponents_found)
        
        # --- CONSUMO DO RECURSO (AGORA SIM) ---
        if usar_entrada_diaria:
            # Desconta Entrada Diária
            new_entries = pvp_entries - 1
            player_data["pvp_entries_left"] = new_entries
            # Atualiza no banco para garantir
            if players_collection:
                players_collection.update_one({"_id": user_id}, {"$set": {"pvp_entries_left": new_entries}})
        else:
            # Desconta Ticket
            if not player_manager.remove_item_from_inventory(player_data, ticket_id, quantity=1):
                await query.answer("Erro ao consumir ticket.", show_alert=True)
                return
        
        await player_manager.save_player_data(user_id, player_data)

        # Prepara dados do oponente
        opponent_data = await player_manager.get_player_data(final_opponent_id)
        if not opponent_data:
            await query.answer("Oponente inválido.", show_alert=True)
            return
            
        caption_batalha = "⚔️ <b>Oponente encontrado!</b> Simulando batalha..."

        # Visual (Mídia)
        try: await query.delete_message()
        except Exception: pass

        sent_msg = None
        try:
            raw_class = opponent_data.get("class_key") or opponent_data.get("class") or "guerreiro"
            class_slug = raw_class.lower().strip()
            video_key = f"classe_{class_slug}_media"
            media_data = file_ids.get_file_data(video_key) 

            if media_data and media_data.get("id"):
                file_id = media_data["id"]
                if media_data.get("type") == "video":
                    sent_msg = await context.bot.send_video(chat_id=query.message.chat_id, video=file_id, caption=caption_batalha, parse_mode=ParseMode.HTML)
                else:
                    sent_msg = await context.bot.send_photo(chat_id=query.message.chat_id, photo=file_id, caption=caption_batalha, parse_mode=ParseMode.HTML)
            else:
                sent_msg = await context.bot.send_message(chat_id=query.message.chat_id, text=caption_batalha, parse_mode=ParseMode.HTML)
        except Exception:
            sent_msg = await context.bot.send_message(chat_id=query.message.chat_id, text="⚔️ Batalha Iniciada!")

        # Simulação
        vencedor_id, log_completo = await pvp_battle.simular_batalha_completa(user_id, final_opponent_id, modifier_effect=current_effect)
        
        elo_ganho_base = 25; elo_perdido_base = 15; log_final = list(log_completo)
        OURO_FINAL = 50
        
        if current_effect == "prestige_day": 
            elo_ganho = int(elo_ganho_base * 1.5); elo_perdido = int(elo_perdido_base * 1.5)
            log_final.append("\n🏆 <b>Dia do Prestígio!</b> Pontos de Elo aumentados!")
        else: 
            elo_ganho = elo_ganho_base; elo_perdido = elo_perdido_base
        
        if current_effect == "greed_day": 
            OURO_FINAL *= 2
            log_final.append("💰 <b>Dia da Ganância!</b> Ouro dobrado!")
        
        # Resultados
        if vencedor_id == user_id:
            await aplicar_resultado_pvp_seguro(user_id, elo_ganho, OURO_FINAL)
            await aplicar_resultado_pvp_seguro(final_opponent_id, -elo_perdido, 0)
            log_final.append(f"\n🏆 Você ganhou <b>+{elo_ganho}</b> Elo e <b>{OURO_FINAL}</b> Ouro!")
        elif vencedor_id == final_opponent_id:
            await aplicar_resultado_pvp_seguro(user_id, -elo_perdido, 0)
            await aplicar_resultado_pvp_seguro(final_opponent_id, elo_ganho, 0)
            log_final.append(f"\n❌ Você perdeu <b>-{elo_perdido}</b> Elo.")

        # Animação Janela Deslizante
        reply_markup_final = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]])
        
        if sent_msg:
            dest_chat_id = sent_msg.chat_id; dest_msg_id = sent_msg.message_id
            is_media = bool(sent_msg.photo or sent_msg.video)
            header = log_final[0]; corpo_log = log_final[1:]
            passo = 4; tamanho_janela = 10 

            for i in range(0, len(corpo_log), passo):
                is_last_frame = (i + passo) >= len(corpo_log)
                markup = reply_markup_final if is_last_frame else None
                
                fim_slice = i + passo
                inicio_slice = max(0, fim_slice - tamanho_janela)
                chunk_atual = corpo_log[inicio_slice : fim_slice]
                
                if is_last_frame:
                    chunk_atual = corpo_log[max(0, len(corpo_log) - 12):] # Mostra final
                    texto_frame = f"{header}\n\n📜 <b>Resultado Final:</b>\n" + "\n".join(chunk_atual)
                else:
                    texto_frame = f"{header}\n\n" + "\n".join(chunk_atual) + "\n\n⚔️ <i>Lutando...</i>"
                
                if len(texto_frame) > 1000: texto_frame = texto_frame[:990] + "..."

                try:
                    if is_media: await context.bot.edit_message_caption(chat_id=dest_chat_id, message_id=dest_msg_id, caption=texto_frame, reply_markup=markup, parse_mode=ParseMode.HTML)
                    else: await context.bot.edit_message_text(chat_id=dest_chat_id, message_id=dest_msg_id, text=texto_frame, reply_markup=markup, parse_mode=ParseMode.HTML)
                except Exception: pass
                
                if not is_last_frame: await asyncio.sleep(2.5)
        else:
            await context.bot.send_message(chat_id=query.message.chat_id, text="\n".join(log_final[-10:]), reply_markup=reply_markup_final)

    else: 
        # Sem oponentes (Não consome nada)
        no_opp_msg = "🛡️ <b>Arena Vazia!</b>\nNão encontramos oponentes neste momento.\n<i>Seus recursos foram preservados.</i>"
        kb = [[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]]
        try:
            if original_message_is_media: await query.edit_message_caption(caption=no_opp_msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
            else: await query.edit_message_text(text=no_opp_msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        except Exception: pass

async def ranking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer("Carregando Ranking...") 
    except: pass
    user_id = query.from_user.id

    try:
        if players_collection is None:
            await query.edit_message_text("❌ Erro: Banco de dados desconectado.")
            return

        cursor = players_collection.find({"pvp_points": {"$gt": 0}}).sort("pvp_points", -1).limit(15)
        top_players = list(cursor)

        lines = ["🏆 <b>Ranking da Arena de Eldora</b> 🏆\n"]
        if not top_players: lines.append("<i>Ainda não há guerreiros classificados.</i>")
        else:
            found_me = False
            for i, p in enumerate(top_players):
                rank = i + 1; pts = p.get("pvp_points", 0)
                name = html.escape(p.get("character_name", "Guerreiro"))
                _, elo = pvp_utils.get_player_elo_details(pts)
                
                if p["_id"] == user_id:
                    found_me = True
                    lines.append(f"👉 <b>{rank}º</b> {elo} - {name} <b>({pts})</b>")
                else:
                    lines.append(f"<b>{rank}º</b> {elo} - {name} <b>({pts})</b>")

            if not found_me:
                my_data = await player_manager.get_player_data(user_id)
                if my_data and my_data.get("pvp_points", 0) > 0:
                    pos = players_collection.count_documents({"pvp_points": {"$gt": my_data["pvp_points"]}}) + 1
                    _, my_elo = pvp_utils.get_player_elo_details(my_data["pvp_points"])
                    lines.append("\n..."); lines.append(f"👉 <b>{pos}º</b> {my_elo} - Você <b>({my_data['pvp_points']})</b>")

        lines.append("\n💎 <b>Top 5 Ganham Gemas Mensalmente!</b>")
        final_text = "\n".join(lines)
        
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]])
        if query.message.photo or query.message.video:
            await query.edit_message_caption(caption=final_text[:1024], reply_markup=kb, parse_mode=ParseMode.HTML)
        else:
            await query.edit_message_text(text=final_text[:4096], reply_markup=kb, parse_mode=ParseMode.HTML)

    except Exception: await query.answer("Erro ao exibir ranking.", show_alert=True)

async def historico_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Função 'Histórico' em construção!", show_alert=True)

async def pvp_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    player_data = await player_manager.get_player_data(user_id)
    if not player_data: return

    # MOSTRA OS DOIS RECURSOS NO MENU
    current_tickets = player_data.get('inventory', {}).get("ticket_arena", 0)
    daily_entries = player_data.get("pvp_entries_left", 0)

    today_weekday = datetime.datetime.now().weekday()
    modifier = ARENA_MODIFIERS.get(today_weekday)
    mod_text = f"\n🔥 <b>{modifier['name']}</b>: {modifier['description']}\n" if modifier else ""

    caption = (
        "⚔️ 𝐀𝐫𝐞𝐧𝐚 𝐝𝐞 𝐄𝐥𝐝𝐨𝐫𝐚 ⚔️\n\n"
        f"🗡️ <b>Entradas Diárias:</b> {daily_entries}/10\n"
        f"🎟️ <b>Tickets Extras:</b> {current_tickets}\n"
        f"{mod_text}\n"
        "<i>Prove seu valor e suba no ranking!</i>"
    )

    kb = [
        [InlineKeyboardButton("⚔️ Lutar (Ranqueado)", callback_data=PVP_PROCURAR_OPONENTE)],
        [InlineKeyboardButton("🏆 Ranking", callback_data=PVP_RANKING), InlineKeyboardButton("📜 Histórico", callback_data=PVP_HISTORICO)],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="show_kingdom_menu")]
    ]
    
    # Adiciona botões do Torneio se necessário (mantendo integração)
    try:
        t_data = tournament_system.get_tournament_data()
        if t_data.get("status") == "registration":
            if user_id not in t_data.get("participants", []):
                kb.insert(0, [InlineKeyboardButton("✍️ Inscrever-se no Torneio", callback_data="torneio_signup")])
            else:
                kb.insert(0, [InlineKeyboardButton("✅ Inscrito no Torneio", callback_data="noop")])
        elif t_data.get("status") == "active":
            ms = tournament_system.CURRENT_MATCH_STATE
            if ms["active"] and user_id in [ms["p1"], ms["p2"]]:
                kb.insert(0, [InlineKeyboardButton("🔥 ⚔️ ESTOU PRONTO! ⚔️ 🔥", callback_data="torneio_ready")])
    except: pass

    markup = InlineKeyboardMarkup(kb)
    
    if update.callback_query:
        try: await update.callback_query.delete_message()
        except: pass

    media = file_ids.get_file_data("pvp_arena_media")
    if media and media.get("id"):
        try: await context.bot.send_photo(chat_id=chat_id, photo=media["id"], caption=caption, reply_markup=markup, parse_mode=ParseMode.HTML)
        except: await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=markup, parse_mode=ParseMode.HTML)
    else:
        await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=markup, parse_mode=ParseMode.HTML)

async def pvp_battle_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Ação registrada.")

def pvp_handlers() -> list:
    return [
        CommandHandler("pvp", pvp_menu_command),
        CallbackQueryHandler(pvp_menu_command, pattern=r'^pvp_arena$'), 
        CallbackQueryHandler(procurar_oponente_callback, pattern=f'^{PVP_PROCURAR_OPONENTE}$'),
        CallbackQueryHandler(ranking_callback, pattern=f'^{PVP_RANKING}$'),
        CallbackQueryHandler(historico_callback, pattern=f'^{PVP_HISTORICO}$'),
        CallbackQueryHandler(pvp_battle_action_callback, pattern=r'^pvp_battle_attack$'),
        CallbackQueryHandler(torneio_signup_callback, pattern=r'^torneio_signup$'),
        CallbackQueryHandler(torneio_ready_callback, pattern=r'^torneio_ready$'),
    ]