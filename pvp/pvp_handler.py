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
from modules.auth_utils import get_current_player_id

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

    # Variável para usar em caso de erro visual no início
    original_message_is_media = bool(query.message.photo or query.message.video or query.message.animation)
        
    await query.answer("🔍 Buscando oponente na rede...")
    user_id = query.from_user.id
    
    # 1. Carrega dados do Jogador
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await query.answer("Erro ao carregar dados.", show_alert=True)
        return

    # 2. Verifica se tem Ticket (MAS NÃO GASTA AINDA)
    item_id_entrada = "ticket_arena" 
    if not player_manager.has_item(player_data, item_id_entrada, quantity=1):
        current_tickets = player_data.get('inventory', {}).get(item_id_entrada, 0)
        item_name = game_data.ITEMS_DATA.get(item_id_entrada, {}).get('display_name', item_id_entrada)
        await context.bot.answer_callback_query(query.id, f"Você não tem {item_name} suficiente! ({current_tickets} restantes)", show_alert=True)
        return

    # 3. Busca Oponentes (LÓGICA OTIMIZADA MONGODB)
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
            
            # Listas de prioridade
            match_perfeito = []   # +/- 300 pontos
            match_aceitavel = []  # +/- 1000 pontos
            match_qualquer = []   # Resto
            
            for opp in potential_opponents:
                try:
                    opp_points = opp.get("pvp_points", 0)
                    diff = abs(my_points - opp_points)
                    opp_id = opp["_id"]
                    
                    if diff <= 300:
                        match_perfeito.append(opp_id)
                    elif diff <= 1000:
                        match_aceitavel.append(opp_id)
                    else:
                        match_qualquer.append(opp_id)
                except Exception: continue
            
            # Escolhe a melhor lista disponível
            if match_perfeito:
                opponents_found = match_perfeito
            elif match_aceitavel:
                opponents_found = match_aceitavel
            else:
                opponents_found = match_qualquer
                
        else:
            # --- FALLBACK (Caso DB falhe, usa o iterador antigo) ---
            async for opponent_id, opp_data in player_manager.iter_players():
                if opponent_id == user_id: continue
                opponents_found.append(opponent_id)

    except Exception as e_search:
        logger.error(f"Erro na busca PvP: {e_search}")
        await query.answer("Erro técnico na busca.", show_alert=True)
        return

    # 4. Decisão Final e Combate
    if opponents_found:
        final_opponent_id = random.choice(opponents_found)
        
        # AGORA SIM: Consome o Ticket
        if not player_manager.remove_item_from_inventory(player_data, item_id_entrada, quantity=1):
            await query.answer("Erro ao consumir ticket.", show_alert=True)
            return
        
        # Salva o inventário atualizado
        await player_manager.save_player_data(user_id, player_data)

        # Prepara dados do oponente
        opponent_data = await player_manager.get_player_data(final_opponent_id)
        if not opponent_data:
            await query.answer("Oponente inválido.", show_alert=True)
            return
            
        # Configura Modificadores do Dia
        today_weekday = datetime.datetime.now().weekday()
        modifier = ARENA_MODIFIERS.get(today_weekday)
        current_effect = modifier.get("effect") if modifier else None

        caption_batalha = "⚔️ <b>Oponente encontrado!</b> Simulando batalha..."

        # --- Limpeza e Envio da Mídia (Visual) ---
        try: await query.delete_message()
        except Exception: pass

        sent_msg = None
        try:
            # Tenta pegar a Mídia da Classe do Oponente
            raw_class = opponent_data.get("class_key") or opponent_data.get("class") or "guerreiro"
            class_slug = raw_class.lower().strip()
            video_key = f"classe_{class_slug}_media"
            
            media_data = file_ids.get_file_data(video_key) 

            # LÓGICA DE VÍDEO CORRIGIDA
            if media_data and media_data.get("id"):
                file_id = media_data["id"]
                # Verifica explicitamente se é vídeo
                if media_data.get("type") == "video":
                    sent_msg = await context.bot.send_video(
                        chat_id=query.message.chat_id, 
                        video=file_id, 
                        caption=caption_batalha, 
                        parse_mode=ParseMode.HTML
                    )
                else:
                    # Se não for vídeo, manda foto
                    sent_msg = await context.bot.send_photo(
                        chat_id=query.message.chat_id, 
                        photo=file_id, 
                        caption=caption_batalha, 
                        parse_mode=ParseMode.HTML
                    )
            else:
                # Fallback se não tiver mídia da classe
                sent_msg = await context.bot.send_message(
                    chat_id=query.message.chat_id, 
                    text=caption_batalha, 
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            logger.error(f"Erro visual ao enviar mídia: {e}")
            sent_msg = await context.bot.send_message(chat_id=query.message.chat_id, text="⚔️ Batalha Iniciada!")

        # --- SIMULAÇÃO DA BATALHA ---
        vencedor_id, log_completo = await pvp_battle.simular_batalha_completa(user_id, final_opponent_id, modifier_effect=current_effect)
        
        # Definição de Ganhos/Perdas
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
        
        # --- SALVA RESULTADOS (Seguro) ---
        if vencedor_id == user_id:
            await aplicar_resultado_pvp_seguro(user_id, elo_ganho, OURO_FINAL_RECOMPENSA)
            await aplicar_resultado_pvp_seguro(final_opponent_id, -elo_perdido, 0)
            log_final.append(f"\n🏆 Você ganhou <b>+{elo_ganho}</b> pontos de Elo!")
            log_final.append(f"💰 Você recebeu <b>{OURO_FINAL_RECOMPENSA}</b> de ouro!")

        elif vencedor_id == final_opponent_id:
            await aplicar_resultado_pvp_seguro(user_id, -elo_perdido, 0)
            await aplicar_resultado_pvp_seguro(final_opponent_id, elo_ganho, 0)
            log_final.append(f"\n❌ Você perdeu <b>-{elo_perdido}</b> pontos de Elo.")

        # --- ANIMAÇÃO DO LOG (Loop Janela Deslizante) ---
        reply_markup_final = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]])
        
        if sent_msg:
            dest_chat_id = sent_msg.chat_id
            dest_msg_id = sent_msg.message_id
            is_media = bool(sent_msg.photo or sent_msg.video)
            
            header = log_final[0] # Cabeçalho
            corpo_log = log_final[1:] # Ação
                
            passo = 4 
            tamanho_janela = 10 

            for i in range(0, len(corpo_log), passo):
                is_last_frame = (i + passo) >= len(corpo_log)
                markup = reply_markup_final if is_last_frame else None
                    
                # CÁLCULO DA JANELA
                fim_slice = i + passo
                inicio_slice = max(0, fim_slice - tamanho_janela)
                
                chunk_atual = corpo_log[inicio_slice : fim_slice]
                    
                if is_last_frame:
                    # No final, garante mostrar o resultado (últimas 12 linhas)
                    chunk_atual = corpo_log[max(0, len(corpo_log) - 12):]
                    texto_combate = "\n".join(chunk_atual)
                    texto_frame = f"{header}\n\n📜 <b>Histórico Recente:</b>\n{texto_combate}"
                else:
                    texto_combate = "\n".join(chunk_atual)
                    rodape = "\n\n⚔️ <i>A batalha continua...</i>"
                    texto_frame = f"{header}\n\n{texto_combate}{rodape}"
                
                # Proteção de limite de caracteres
                if len(texto_frame) > 1000: 
                    texto_frame = texto_frame[:990] + "..."

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
                    
                if not is_last_frame:
                    await asyncio.sleep(2.5)
        else:
            # Fallback se a mensagem sumiu
            await context.bot.send_message(chat_id=query.message.chat_id, text="\n".join(log_final[-10:]), reply_markup=reply_markup_final)

    else: 
        # 5. CASO NÃO ACHE NINGUÉM
        no_opp_msg = "🛡️ <b>Arena Vazia!</b>\nNão encontramos oponentes neste momento.\n<i>Seu ticket foi preservado.</i>"
        keyboard = [[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            if original_message_is_media: await query.edit_message_caption(caption=no_opp_msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
            else: await query.edit_message_text(text=no_opp_msg, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        except Exception: pass


async def ranking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # Avisa o telegram para parar o "reloginho" de carregamento
    try: 
        await query.answer("Carregando Ranking...") 
    except: 
        pass
        
    user_id = query.from_user.id

    try:
        if players_collection is None:
            await query.edit_message_text("❌ Erro: Banco de dados desconectado.")
            return

        # --- BUSCA OTIMIZADA NO MONGODB ---
        # 1. Filtra > 0 pontos
        # 2. Ordena Decrescente (-1)
        # 3. Limita aos Top 15
        cursor = players_collection.find({"pvp_points": {"$gt": 0}})\
                                   .sort("pvp_points", -1)\
                                   .limit(15)
        
        top_players = list(cursor)

        # Monta o Texto
        ranking_text_lines = ["🏆 <b>Ranking da Arena de Eldora</b> 🏆\n"]
        
        if not top_players:
            ranking_text_lines.append("<i>Ainda não há guerreiros classificados nesta temporada.</i>")
        else:
            player_rank = -1
            
            for i, p_data in enumerate(top_players):
                rank = i + 1
                points = p_data.get("pvp_points", 0)
                # Pega nome ou usa fallback
                name = p_data.get("character_name", p_data.get("username", "Guerreiro"))
                
                # Trata caracteres especiais no nome para não quebrar o HTML
                safe_name = html.escape(name)
                
                # Pega o Elo e o Emoji
                _, elo_display = pvp_utils.get_player_elo_details(points)
                
                # Destaca se for o usuário atual
                if p_data["_id"] == user_id:
                    player_rank = rank
                    line = f"👉 <b>{rank}º</b> {elo_display} - {safe_name} <b>({points})</b>"
                else:
                    line = f"<b>{rank}º</b> {elo_display} - {safe_name} <b>({points})</b>"
                
                ranking_text_lines.append(line)

            # Se o jogador não apareceu no TOP 15, busca a posição dele separada
            if player_rank == -1:
                my_data = await player_manager.get_player_data(user_id)
                if my_data:
                    my_points = my_data.get("pvp_points", 0)
                    if my_points > 0:
                        # Conta quantos jogadores têm mais pontos que ele
                        position = players_collection.count_documents({"pvp_points": {"$gt": my_points}}) + 1
                        _, my_elo = pvp_utils.get_player_elo_details(my_points)
                        ranking_text_lines.append("\n...")
                        ranking_text_lines.append(f"👉 <b>{position}º</b> {my_elo} - Você <b>({my_points})</b>")

        # Adiciona informações de recompensa
        ranking_text_lines.append("\n💎 <b>Recompensas Mensais (Top 5):</b>")
        for rank, reward in sorted(MONTHLY_RANKING_REWARDS.items()):
            ranking_text_lines.append(f"   {rank}º Lugar: {reward} Gemas")
            
        ranking_text_lines.append(f"\n<i>Total de competidores: {len(top_players)}</i>")
        
        final_text = "\n".join(ranking_text_lines)
        
        keyboard = [[InlineKeyboardButton("⬅️ Voltar para a Arena", callback_data="pvp_arena")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # --- LÓGICA BLINDADA DE EDIÇÃO ---
        # Verifica se a mensagem original tem Mídia (Foto/Vídeo)
        if query.message.photo or query.message.video:
            await query.edit_message_caption(
                caption=final_text[:1024], # Limite do Telegram para legendas
                reply_markup=reply_markup, 
                parse_mode=ParseMode.HTML
            )
        else:
            await query.edit_message_text(
                text=final_text[:4096], # Limite do Telegram para texto
                reply_markup=reply_markup, 
                parse_mode=ParseMode.HTML
            )

    except Exception as e:
        logger.error(f"Erro no Ranking: {e}")
        # Tenta avisar o usuário com um alerta se a edição falhar
        try: 
            await query.answer("❌ Erro ao exibir ranking.", show_alert=True)
        except: 
            pass

async def historico_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Função 'Histórico' ainda em construção!", show_alert=True)

async def pvp_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_current_player_id(update, context)
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