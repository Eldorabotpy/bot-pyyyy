# pvp/pvp_handler.py
# (VERSÃO 5.0: Animação Obrigatória + Correções de Banco)

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
# ✅ IMPORTAÇÃO DO SISTEMA DE TORNEIO
from . import tournament_system
# import do terneio
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
            # PyMongo é síncrono, sem await
            players_collection.update_one({"_id": user_id}, {"$inc": updates})
            await player_manager.clear_player_cache(user_id) 
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar PvP seguro para {user_id}: {e}")
        return False

# =============================================================================
# HANDLERS DO TORNEIO (NOVOS)
# =============================================================================

async def torneio_signup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botão de inscrição no torneio."""
    query = update.callback_query
    success, msg = await tournament_system.registrar_jogador(query.from_user.id)
    await query.answer(msg, show_alert=True)
    
    # Recarrega o menu para atualizar o botão para "Inscrito"
    if success:
        await pvp_menu_command(update, context)

async def torneio_ready_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botão de 'Estou Pronto' na hora da luta."""
    query = update.callback_query
    msg = await tournament_system.confirmar_prontidao(query.from_user.id, context)
    await query.answer(msg, show_alert=True)
    # Recarrega menu
    await pvp_menu_command(update, context)

# =============================================================================
# HANDLERS
# =============================================================================

async def procurar_oponente_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query.message:
        return

    # Variável para usar em caso de erro no início
    original_message_is_media = bool(query.message.photo or query.message.video or query.message.animation)
        
    await query.answer("Procurando um oponente digno...")
    user_id = query.from_user.id
    
    # 1. Carrega dados e verifica Tickets
    player_data = await player_manager.get_player_data(user_id)
    item_id_entrada = "ticket_arena" 

    if not player_manager.has_item(player_data, item_id_entrada, quantity=1):
        current_tickets = player_data.get('inventory', {}).get(item_id_entrada, 0)
        item_name = game_data.ITEMS_DATA.get(item_id_entrada, {}).get('display_name', item_id_entrada)
        await context.bot.answer_callback_query(query.id, f"Você não tem {item_name} suficiente! ({current_tickets} restantes)", show_alert=True)
        return

    if not player_manager.remove_item_from_inventory(player_data, item_id_entrada, quantity=1):
        item_name = game_data.ITEMS_DATA.get(item_id_entrada, {}).get('display_name', item_id_entrada)
        await context.bot.answer_callback_query(query.id, f"Erro ao tentar usar o {item_name}. Tente novamente.", show_alert=True)
        return

    await player_manager.save_player_data(user_id, player_data) 
    
    # 2. Configura Modificadores e Busca
    today_weekday = datetime.datetime.now().weekday()
    modifier = ARENA_MODIFIERS.get(today_weekday)
    current_effect = None
    if modifier: current_effect = modifier.get("effect")

    my_points = player_manager.get_pvp_points(player_data)
    my_elo = pvp_utils.get_player_elo(my_points)
    
    same_elo_opponents = []
    lower_elo_opponents = []
    
    try:
        async for opponent_id, opp_data in player_manager.iter_players():
            if opponent_id == user_id: continue
            try:
                opp_points = player_manager.get_pvp_points(opp_data)
                opp_elo = pvp_utils.get_player_elo(opp_points)
            except Exception: continue

            if my_elo == opp_elo:
                same_elo_opponents.append(opponent_id)
            elif opp_points < my_points:
                lower_elo_opponents.append(opponent_id)
                
    except Exception as e_iter:
        logger.error(f"Erro durante busca pvp: {e_iter}")
        error_message = "🛡️ Erro ao buscar oponentes."
        keyboard = [[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            if original_message_is_media: await query.edit_message_caption(caption=error_message, reply_markup=reply_markup)
            else: await query.edit_message_text(text=error_message, reply_markup=reply_markup)
        except: pass
        return

    final_opponent_id = None
    if same_elo_opponents: final_opponent_id = random.choice(same_elo_opponents)
    elif lower_elo_opponents: final_opponent_id = random.choice(lower_elo_opponents)

    # 3. Oponente Encontrado
    if final_opponent_id:
        opponent_data = await player_manager.get_player_data(final_opponent_id)
        if not opponent_data: 
            await query.edit_message_text("Erro ao carregar oponente.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]]))
            return
            
        caption_batalha = "⚔️ <b>Oponente encontrado!</b> Simulando batalha..."

        # --- PREPARAÇÃO DA MENSAGEM (Limpeza) ---
        try:
            await query.delete_message()
        except Exception: pass

        sent_msg = None
        try:
            opponent_class_key = (opponent_data.get("class_key") or opponent_data.get("class") or "default")
            video_key = f"classe_{opponent_class_key.lower()}_media"
            media_data = file_ids.get_file_data(video_key) 

            if media_data and media_data.get("id"):
                if media_data.get("type") == "video":
                    sent_msg = await context.bot.send_video(
                        chat_id=query.message.chat_id, 
                        video=media_data["id"], 
                        caption=caption_batalha, 
                        parse_mode=ParseMode.HTML
                    )
                else:
                    sent_msg = await context.bot.send_photo(
                        chat_id=query.message.chat_id, 
                        photo=media_data["id"], 
                        caption=caption_batalha, 
                        parse_mode=ParseMode.HTML
                    )
            else:
                sent_msg = await context.bot.send_message(
                    chat_id=query.message.chat_id, 
                    text=caption_batalha, 
                    parse_mode=ParseMode.HTML
                )
            
        except Exception as e_visual:
            logger.error(f"Erro visual ao iniciar batalha: {e_visual}")
            sent_msg = await context.bot.send_message(chat_id=query.message.chat_id, text="⚔️ Batalha Iniciada!")

        # --- SIMULAÇÃO ---
        try:
            vencedor_id, log_completo = await pvp_battle.simular_batalha_completa( user_id, final_opponent_id, modifier_effect=current_effect )
            
            elo_ganho_base = 25; elo_perdido_base = 15; log_final = list(log_completo)
            OURO_BASE_RECOMPENSA = 50
            OURO_FINAL_RECOMPENSA = OURO_BASE_RECOMPENSA
            
            if current_effect == "prestige_day": 
                elo_ganho = int(elo_ganho_base * 1.5); elo_perdido = int(elo_perdido_base * 1.5)
                log_final.append("\n🏆 <b>Dia do Prestígio!</b> Pontos de Elo aumentados!")
            else: 
                elo_ganho = elo_ganho_base; elo_perdido = elo_perdido_base
            
            if current_effect == "greed_day": 
                OURO_FINAL_RECOMPENSA *= 2
                log_final.append("💰 <b>Dia da Ganância!</b> Ouro dobrado!")
            
            # --- SALVAMENTO ---
            if vencedor_id == user_id:
                await aplicar_resultado_pvp_seguro(user_id, elo_ganho, OURO_FINAL_RECOMPENSA)
                await aplicar_resultado_pvp_seguro(final_opponent_id, -elo_perdido, 0)
                log_final.append(f"\n🏆 Você ganhou <b>+{elo_ganho}</b> pontos de Elo!")
                log_final.append(f"💰 Você recebeu <b>{OURO_FINAL_RECOMPENSA}</b> de ouro pela vitória!")

            elif vencedor_id == final_opponent_id:
                await aplicar_resultado_pvp_seguro(user_id, -elo_perdido, 0)
                await aplicar_resultado_pvp_seguro(final_opponent_id, elo_ganho, 0)
                log_final.append(f"\n❌ Você perdeu <b>-{elo_perdido}</b> pontos de Elo.")

            # --- ANIMAÇÃO (LOOP) ---
            reply_markup_final = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]])
            
            if sent_msg:
                dest_chat_id = sent_msg.chat_id
                dest_msg_id = sent_msg.message_id
                is_media = bool(sent_msg.photo or sent_msg.video)

                header = log_final[0] 
                corpo_log = log_final[1:]
                
                # Passo de 4 linhas é um bom equilíbrio para batalhas
                passo = 4 
                
                for i in range(0, len(corpo_log), passo):
                    
                    # Verifica se estamos no último frame
                    is_last_frame = (i + passo) >= len(corpo_log)
                    markup = reply_markup_final if is_last_frame else None
                    
                    # LOGICA DE EXIBIÇÃO:
                    if is_last_frame:
                        # --- FIX DO FINAL ---
                        # Se for o fim, pega as últimas 8 linhas do log TOTAL.
                        # Isso garante contexto: (Golpe Final + Barra Vazia + Vitoria + Recompensas)
                        qtd_linhas_contexto = 8
                        # Pega do fim para trás, cuidado para não pegar indice negativo inválido
                        inicio_corte = max(0, len(corpo_log) - qtd_linhas_contexto)
                        bloco_final = corpo_log[inicio_corte:]
                        
                        texto_frame = f"{header}\n...\n" + "\n".join(bloco_final)
                    
                    else:
                        # --- FRAMES INTERMEDIARIOS (Imersivo) ---
                        # Mostra apenas o 'chunk' atual, limpando o anterior.
                        chunk = corpo_log[i : i + passo]
                        texto_do_turno = "\n".join(chunk)
                        rodape = "\n\n⏳ <i>Lutando...</i>"
                        texto_frame = f"{header}\n\n{texto_do_turno}{rodape}"
                    
                    # Proteção de limite de caracteres
                    limite_char = 1000 if is_media else 4000
                    if len(texto_frame) > limite_char:
                        texto_frame = f"{header}\n...\n" + "\n".join(corpo_log[-5:]) # Fallback seguro

                    try:
                        if is_media:
                            await context.bot.edit_message_caption(
                                chat_id=dest_chat_id,
                                message_id=dest_msg_id,
                                caption=texto_frame,
                                reply_markup=markup,
                                parse_mode=ParseMode.HTML
                            )
                        else:
                            await context.bot.edit_message_text(
                                chat_id=dest_chat_id,
                                message_id=dest_msg_id,
                                text=texto_frame,
                                reply_markup=markup,
                                parse_mode=ParseMode.HTML
                            )
                    except Exception:
                        pass 
                    
                    # Pausa para leitura (exceto no último frame)
                    if not is_last_frame:
                        await asyncio.sleep(1.5) 

            else:
                # Fallback se a mensagem original sumiu
                await context.bot.send_message(chat_id=query.message.chat_id, text="\n".join(log_final[-10:]), reply_markup=reply_markup_final)

        except Exception as e_battle: 
            logger.error(f"Erro CRÍTICO durante batalha: {e_battle}", exc_info=True)
            try:
                await context.bot.send_message(chat_id=query.message.chat_id, text="🛡️ Erro crítico na batalha. Entrada consumida.")
            except: pass

    else: # Se não achou oponente
        no_opp_msg = "🛡️ Nenhum oponente encontrado com Elo compatível. Tente novamente."
        keyboard = [[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]]; reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            if original_message_is_media: await query.edit_message_caption(caption=no_opp_msg, reply_markup=reply_markup)
            else: await query.edit_message_text(text=no_opp_msg, reply_markup=reply_markup)
        except Exception: pass


async def ranking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Calculando o ranking...")
    user_id = query.from_user.id

    all_players_ranked = []
    try:
        async for p_id, p_data in player_manager.iter_players():
            try: 
                pvp_points = player_manager.get_pvp_points(p_data) 
                if pvp_points > 0:
                    all_players_ranked.append({
                        "user_id": p_id,
                        "name": p_data.get("character_name", f"ID: {p_id}"),
                        "points": pvp_points
                    })
            except Exception: continue
                
    except Exception:
        try: await query.edit_message_text("❌ Erro ao buscar dados do ranking.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]]))
        except: pass
        return

    all_players_ranked.sort(key=lambda p: p["points"], reverse=True)
    ranking_text_lines = ["🏆 **Ranking da Arena de Eldora** 🏆\n"]; top_n = 10; player_rank = -1
    if not all_players_ranked: ranking_text_lines.append("Ainda não há jogadores classificados...")
    else:
        for i, player in enumerate(all_players_ranked):
            rank = i + 1; elo_name, elo_display = pvp_utils.get_player_elo_details(player["points"])
            line = f"{rank}. {elo_display} - {html.escape(player['name'])} ({player['points']} Pts)" 
            if rank <= top_n: ranking_text_lines.append(line)
            if player["user_id"] == user_id: player_rank = rank
        if player_rank > top_n:
            ranking_text_lines.append("\n...")
            my_player_data = next((p for p in all_players_ranked if p["user_id"] == user_id), None)
            if my_player_data: _, my_elo_display = pvp_utils.get_player_elo_details(my_player_data["points"]); ranking_text_lines.append(f"{player_rank}. {my_elo_display} - {html.escape(my_player_data['name'])} ({my_player_data['points']} Pts) (Você)")

    ranking_text_lines.append("\n\n💎 **Recompensas Mensais (Top 5):**") 
    for rank, reward in sorted(MONTHLY_RANKING_REWARDS.items()): ranking_text_lines.append(f"   {rank}º Lugar: {reward} Gemas (Dimas)")
    ranking_text_lines.append("_(Próximo reset em ~30 dias)_")
    ranking_text_lines.append(f"\nTotal de jogadores no ranking: {len(all_players_ranked)}")
    final_text = "\n".join(ranking_text_lines)
    keyboard = [[InlineKeyboardButton("⬅️ Voltar para a Arena", callback_data="pvp_arena")]]; reply_markup = InlineKeyboardMarkup(keyboard)

    try: await query.delete_message()
    except: pass
    
    await context.bot.send_message(chat_id=query.message.chat_id, text=final_text[:4090], reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def historico_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Função 'Histórico' ainda em construção!", show_alert=True)

async def pvp_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    try: await pvp_utils.verificar_reset_temporada(context.bot)
    except: pass

    try:
        player_data = await player_manager.get_player_data(user_id)
        if not player_data:
            await context.bot.send_message(chat_id, "Você precisa criar um personagem primeiro com /start.")
            return
        
        item_id_entrada = "ticket_arena"
        current_tickets = player_data.get('inventory', {}).get(item_id_entrada, 0)
        
        today_weekday = datetime.datetime.now().weekday()
        modifier = ARENA_MODIFIERS.get(today_weekday)
        modifier_text = ""
        if modifier:
            modifier_text = (f"\n🔥 <b>Modificador de Hoje: {modifier['name']}</b>\n<i>{modifier['description']}</i>\n")
        
        caption = (
            "⚔️ 𝐀𝐫𝐞𝐧𝐚 𝐝𝐞 𝐄𝐥𝐝𝐨𝐫𝐚 ⚔️\n"
            f"🎟️ <b>Tickets Disponíveis: {current_tickets}x</b>\n"
            f"{modifier_text}\n"
            "Escolha seu caminho, campeão:"
        )

        # --- BOTÕES PADRÃO ---
        keyboard = [
            [InlineKeyboardButton("⚔️ Procurar Oponente (Ranqueado)", callback_data=PVP_PROCURAR_OPONENTE)],
            [InlineKeyboardButton("🏆 Ranking", callback_data=PVP_RANKING),
             InlineKeyboardButton("📜 Histórico", callback_data=PVP_HISTORICO)],
            [InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data="show_kingdom_menu")],
        ]

        # ====================================================
        # 👇 INTEGRAÇÃO COM O TORNEIO (CÓDIGO NOVO) 👇
        # ====================================================
        try:
            t_data = tournament_system.get_tournament_data()
            status = t_data.get("status")
            
            # 1. Fase de Inscrição
            if status == "registration":
                # Verifica se já está inscrito
                participantes = t_data.get("participants", [])
                if user_id in participantes:
                    # Botão informativo (sem ação)
                    keyboard.insert(0, [InlineKeyboardButton("✅ Inscrito no Torneio", callback_data="noop")])
                else:
                    # Botão de ação
                    keyboard.insert(0, [InlineKeyboardButton("✍️ Inscrever-se no Torneio", callback_data="torneio_signup")])
            
            # 2. Fase de Luta Ativa (Botão de Pronto)
            elif status == "active":
                match_state = tournament_system.CURRENT_MATCH_STATE
                # Só mostra o botão se houver luta ativa E o usuário for um dos lutadores
                if match_state["active"] and user_id in [match_state["p1"], match_state["p2"]]:
                    keyboard.insert(0, [InlineKeyboardButton("🔥 ⚔️ ESTOU PRONTO! ⚔️ 🔥", callback_data="torneio_ready")])
        except Exception as e:
            logger.error(f"Erro ao integrar torneio no menu: {e}")
        # ====================================================

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            try: await update.callback_query.delete_message()
            except: pass

        media_data = file_ids.get_file_data("pvp_arena_media")
        if media_data and media_data.get("id"):
            try:
                await context.bot.send_photo(chat_id=chat_id, photo=media_data["id"], caption=caption, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
                return
            except Exception: pass

        await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    except Exception as e_geral:
        logger.error(f"Erro pvp_menu: {e_geral}")

async def torneio_signup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    success, msg = await tournament_system.registrar_jogador(query.from_user.id)
    await query.answer(msg, show_alert=True)
    if success:
        # Atualiza o menu para mostrar "Inscrito"
        await pvp_menu_command(update, context)

async def torneio_ready_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    msg = await tournament_system.confirmar_prontidao(query.from_user.id, context)
    await query.answer(msg, show_alert=True)
    # Atualiza o menu
    await pvp_menu_command(update, context)

async def pvp_battle_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Ação registrada.")

def pvp_handlers() -> list:
    return [
        CommandHandler("pvp", pvp_menu_command),
        CallbackQueryHandler(pvp_menu_command, pattern=r'^pvp_arena$'), 
        CallbackQueryHandler(procurar_oponente_callback, pattern=f'^{PVP_PROCURAR_OPONENTE}$'),
        CallbackQueryHandler(ranking_callback, pattern=f'^{PVP_RANKING}$'),
        CallbackQueryHandler(historico_callback, pattern=f'^{PVP_HISTORICO}$'),
        CallbackQueryHandler(pvp_battle_action_callback, pattern=r'^pvp_battle_attack$'),
        # ✅ Handlers do Torneio (Novos)
        CallbackQueryHandler(torneio_signup_callback, pattern=r'^torneio_signup$'),
        CallbackQueryHandler(torneio_ready_callback, pattern=r'^torneio_ready$'),
    ]