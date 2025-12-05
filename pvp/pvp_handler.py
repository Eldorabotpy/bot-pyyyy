# Em pvp/pvp_handler.py

import logging
import random
import datetime
import html
import asyncio
from .pvp_config import ARENA_MODIFIERS, MONTHLY_RANKING_REWARDS
from . import pvp_battle
from . import pvp_config
from . import pvp_utils
from handlers.utils import format_pvp_result
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaVideo
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from modules import player_manager, file_ids, game_data
from modules.player.core import players_collection

logger = logging.getLogger(__name__)


PVP_PROCURAR_OPONENTE = "pvp_procurar_oponente"
PVP_RANKING = "pvp_ranking"
PVP_HISTORICO = "pvp_historico"

async def aplicar_resultado_pvp_seguro(user_id, pontos_delta, ouro_delta=0):
    """
    Usa o MongoDB direto para somar/subtrair pontos e ouro.
    Isso é 'Atomic Update': Não depende de carregar o perfil e evita perda de dados.
    """
    if not players_collection:
        return False
        
    try:
        # Prepara o comando de atualização ($inc = increment/add)
        updates = {}
        if pontos_delta != 0:
            updates["pvp_points"] = pontos_delta
        if ouro_delta != 0:
            updates["gold"] = ouro_delta # Assumindo que o ouro fica na raiz 'gold'
            
        if not updates:
            return True

        # Envia direto pro banco (Milissegundos)
        await players_collection.update_one(
            {"_id": user_id},
            {"$inc": updates}
        )
        
        # Opcional: Atualiza o cache local para o bot não ficar com dados velhos na memória
        # Isso é só visual, o banco já está salvo e seguro.
        await player_manager.clear_player_cache(user_id)
        
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar resultado PvP atômico para {user_id}: {e}")
        return False
    
async def procurar_oponente_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query.message:
        await query.answer("Esta ação expirou.", show_alert=True)
        return
        
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
            if opponent_id == user_id: 
                continue
            
            try:
                opp_points = player_manager.get_pvp_points(opp_data)
                opp_elo = pvp_utils.get_player_elo(opp_points)
            except Exception as e_opp_stats:
                logger.error(f"Erro ao obter stats PvP do oponente {opponent_id}: {e_opp_stats}")
                continue

            if my_elo == opp_elo:
                same_elo_opponents.append(opponent_id)
            elif opp_points < my_points:
                lower_elo_opponents.append(opponent_id)
                
    except Exception as e_iter:
        logger.error(f"Erro CRÍTICO durante player_manager.iter_players(): {e_iter}", exc_info=True)
        error_message = ("🛡️ Falha na Busca 🛡️\n\nOcorreu um erro ao procurar oponentes.")
        keyboard = [[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]]; reply_markup = InlineKeyboardMarkup(keyboard)
        original_message_is_media = bool(query.message.photo or query.message.video or query.message.animation)
        try:
            if original_message_is_media: await query.edit_message_caption(caption=error_message, reply_markup=reply_markup, parse_mode="HTML")
            else: await query.edit_message_text(text=error_message, reply_markup=reply_markup, parse_mode="HTML")
        except Exception: pass
        return

    final_opponent_id = None
    if same_elo_opponents: final_opponent_id = random.choice(same_elo_opponents)
    elif lower_elo_opponents: final_opponent_id = random.choice(lower_elo_opponents)

    original_message_is_media = bool(query.message.photo or query.message.video or query.message.animation)

    # 3. Oponente Encontrado
    if final_opponent_id:
        opponent_data = await player_manager.get_player_data(final_opponent_id)
        if not opponent_data: 
            await query.edit_message_text("Erro ao carregar oponente. Tente novamente.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]]))
            return
            
        caption_batalha = "⚔️ Oponente encontrado! Simulando batalha..."

        # Tenta mostrar a mídia da classe do oponente
        try:
            opponent_class_key = (opponent_data.get("class_key") or opponent_data.get("class") or opponent_data.get("classe") or opponent_data.get("class_type") or "default")
            video_key = f"classe_{opponent_class_key.lower()}_media"
            media_data = file_ids.get_file_data(video_key) 

            if media_data and media_data.get("id") and original_message_is_media:
                new_media = InputMediaVideo(media=media_data["id"], caption=caption_batalha, parse_mode="HTML")
                await query.edit_message_media(media=new_media)
            elif original_message_is_media:
                await query.edit_message_caption(caption=caption_batalha, parse_mode="HTML")
            else:
                await query.edit_message_text(text=caption_batalha, parse_mode="HTML")
        except Exception as e_edit_initial:
            logger.error(f"Falha ao editar msg ANTES da batalha: {e_edit_initial}. Tentando fallback final.")
            try:
                await query.edit_message_text(text=caption_batalha, parse_mode="HTML")
            except Exception as e_fallback_text:
                logger.error(f"Falha no fallback final de texto: {e_fallback_text}")

        # --- LÓGICA DE BATALHA E RECOMPENSAS ---
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
            
            if vencedor_id == user_id:
                # === VOCÊ VENCEU (ATUALIZAÇÃO SEGURA) ===
                # Salva: Seus Pontos (+), Seu Ouro (+), Pontos Oponente (-)
                await aplicar_resultado_pvp_seguro(user_id, elo_ganho, OURO_FINAL_RECOMPENSA)
                await aplicar_resultado_pvp_seguro(final_opponent_id, -elo_perdido, 0)
                
                log_final.append(f"\n🏆 Você ganhou <b>+{elo_ganho}</b> pontos de Elo!")
                log_final.append(f"💰 Você recebeu <b>{OURO_FINAL_RECOMPENSA}</b> de ouro pela vitória!")

            elif vencedor_id == final_opponent_id:
                # === VOCÊ PERDEU (ATUALIZAÇÃO SEGURA) ===
                # Salva: Seus Pontos (-), Pontos Oponente (+)
                await aplicar_resultado_pvp_seguro(user_id, -elo_perdido, 0)
                await aplicar_resultado_pvp_seguro(final_opponent_id, elo_ganho, 0)
                
                log_final.append(f"\n❌ Você perdeu <b>-{elo_perdido}</b> pontos de Elo.")

            # =========================================================================
            # 👇 ANIMAÇÃO DE SUBSTITUIÇÃO (ESTILO FILME) 👇
            # =========================================================================
            
            reply_markup_final = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]])
            
            # log_final[0] é o cabeçalho com os status (VS). Ele é fixo.
            header = log_final[0] 
            # O resto são os turnos e o resultado final.
            corpo_log = log_final[1:]
            
            # Configura método de edição
            if original_message_is_media:
                metodo_edit = query.edit_message_caption
                param_key = 'caption'
            else:
                metodo_edit = query.edit_message_text
                param_key = 'text'

            # Define quantos blocos de texto mostrar por vez.
            passo = 5 
            
            for i in range(0, len(corpo_log), passo):
                chunk = corpo_log[i : i + passo]
                texto_do_turno = "\n".join(chunk)
                
                is_last_frame = (i + passo) >= len(corpo_log)
                
                # Monta o frame: Cabeçalho + Apenas o pedaço atual
                # Se for o último frame, mostra o botão de voltar.
                markup = reply_markup_final if is_last_frame else None
                
                # Rodapé de status
                rodape = "\n\n⚔️ <i>Batalha em andamento...</i>" if not is_last_frame else ""
                
                # O TEXTO FINAL DO FRAME:
                texto_frame = f"{header}\n{texto_do_turno}{rodape}"
                
                # Verificação de segurança de tamanho (raramente necessário neste modo, mas bom ter)
                if len(texto_frame) > 1024 and original_message_is_media:
                    texto_frame = texto_frame[:1000] + "\n[...]"

                try:
                    await metodo_edit(**{param_key: texto_frame}, reply_markup=markup, parse_mode="HTML")
                    
                    if not is_last_frame:
                        await asyncio.sleep(1.5) # Pausa dramática entre os turnos
                        
                except Exception as e_anim:
                    # Se der erro (ex: mensagem não modificada), ignora e tenta o próximo
                    continue

        except Exception as e_battle: # Captura de Erro da Batalha
            logger.error(f"Erro CRÍTICO durante a simulação da batalha: {e_battle}", exc_info=True)
            error_message = ("🛡️ Falha na Batalha 🛡️\n\nOcorreu um erro crítico.\nSua entrada foi consumida.")
            keyboard = [[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]]; reply_markup = InlineKeyboardMarkup(keyboard)
            try: 
                if original_message_is_media: await query.edit_message_caption(caption=error_message, reply_markup=reply_markup, parse_mode="HTML")
                else: await query.edit_message_text(text=error_message, reply_markup=reply_markup, parse_mode="HTML")
            except Exception: pass

    else: # Se não achou oponente
        no_opp_msg = "🛡️ Nenhum oponente encontrado com Elo compatível. Tente novamente."
        keyboard = [[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]]; reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            if original_message_is_media: await query.edit_message_caption(caption=no_opp_msg, reply_markup=reply_markup)
            else: await query.edit_message_text(text=no_opp_msg, reply_markup=reply_markup)
        except Exception: pass

async def ranking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe o ranking PvP dos melhores jogadores e os prémios mensais."""
    query = update.callback_query
    await query.answer("Calculando o ranking...")
    user_id = query.from_user.id

    all_players_ranked = []
    try:
        # <<< CORREÇÃO 9: Adiciona 'async for' >>>
        async for p_id, p_data in player_manager.iter_players():
            try: 
                pvp_points = player_manager.get_pvp_points(p_data) 
                if pvp_points > 0:
                    all_players_ranked.append({
                        "user_id": p_id,
                        "name": p_data.get("character_name", f"ID: {p_id}"),
                        "points": pvp_points
                    })
            except Exception as e_player:
                logger.error(f"Erro ao processar ranking para jogador {p_id}: {e_player}")
                
    except Exception as e:
        logger.error(f"Erro ao iterar jogadores para ranking: {e}", exc_info=True)
        try: await query.edit_message_caption("❌ Erro ao buscar dados do ranking.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]]))
        except Exception: await query.edit_message_text("❌ Erro ao buscar dados do ranking.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]]))
        return

    # Lógica síncrona de ordenação e formatação (Mantida)
    all_players_ranked.sort(key=lambda p: p["points"], reverse=True)
    ranking_text_lines = ["🏆 𝐑𝐚𝐧𝐤𝐢𝐧𝐠 𝐝𝐚 𝐀𝐫𝐞𝐧𝐚 𝐝𝐞 𝐄𝐥𝐝𝐨𝐫𝐚 🏆\n"]; top_n = 10; player_rank = -1
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

    ranking_text_lines.append("\n\n💎 𝗥𝗲𝗰𝗼𝗺𝗽𝗲𝗻𝘀𝗮𝘀 𝗠𝗲𝗻𝘀𝗮𝗶𝘀 (𝗧𝗼𝗽 𝟱):") 
    for rank, reward in sorted(MONTHLY_RANKING_REWARDS.items()): ranking_text_lines.append(f"   {rank}º Lugar: {reward} Gemas (Dimas)")
    ranking_text_lines.append("_(Próximo reset em ~30 dias)_")
    ranking_text_lines.append(f"\nTotal de jogadores no ranking: {len(all_players_ranked)}")
    final_text = "\n".join(ranking_text_lines)
    keyboard = [[InlineKeyboardButton("⬅️ Voltar para a Arena", callback_data="pvp_arena")]]; reply_markup = InlineKeyboardMarkup(keyboard)

    # Lógica de edição (já usava await)
    original_message_is_media = bool(query.message.photo or query.message.video or query.message.animation)
    try:
        if original_message_is_media and len(final_text) > 1020:
            logger.warning("Mensagem de ranking longa, enviando como texto.")
            await query.delete_message()
            await context.bot.send_message(chat_id=query.message.chat_id, text=final_text[:4090], reply_markup=reply_markup, parse_mode="HTML")
        elif original_message_is_media:
            await query.edit_message_caption(caption=final_text, reply_markup=reply_markup, parse_mode="HTML")
        else:
            await query.edit_message_text(text=final_text[:4090], reply_markup=reply_markup, parse_mode="HTML")
    except Exception as e_edit:
        logger.error(f"Falha ao editar mensagem do ranking: {e_edit}")
        try: await context.bot.send_message(chat_id=query.message.chat_id, text=final_text[:4090], reply_markup=reply_markup, parse_mode="HTML")
        except Exception as e_send: logger.error(f"Falha CRÍTICA ao enviar mensagem do ranking: {e_send}")

async def historico_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Função 'Histórico' ainda em construção!", show_alert=True)

async def pvp_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde ao comando /pvp ou a um botão para abrir o menu da arena."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    try:
        # 1. Carrega dados e verifica se existe
        player_data = await player_manager.get_player_data(user_id)
        if not player_data:
            await context.bot.send_message(chat_id, "Você precisa criar um personagem primeiro com /start.")
            return
        
        # 2. Obtém o número de tickets e o modificador
        item_id_entrada = "ticket_arena"
        current_tickets = player_data.get('inventory', {}).get(item_id_entrada, 0)
        
        today_weekday = datetime.datetime.now().weekday()
        modifier = ARENA_MODIFIERS.get(today_weekday)

        modifier_text = ""
        if modifier:
            modifier_text = (
                f"\n🔥 <b>Modificador de Hoje: {modifier['name']}</b>\n"
                f"<i>{modifier['description']}</i>\n"
            )
        
        # 3. Monta o Caption com o Indicador de Tickets
        caption = (
            "⚔️ 𝐀𝐫𝐞𝐧𝐚 𝐝𝐞 𝐄𝐥𝐝𝐨𝐫𝐚 ⚔️\n"
            f"🎟️ <b>Tickets Disponíveis: {current_tickets}x</b>\n"
            f"{modifier_text}\n"
            "Escolha seu caminho, campeão:"
        )

        keyboard = [
            [InlineKeyboardButton("⚔️ 𝐏𝐫𝐨𝐜𝐮𝐫𝐚𝐫 𝐎𝐩𝐨𝐧𝐞𝐧𝐭𝐞 (Ranqueado)", callback_data=PVP_PROCURAR_OPONENTE)],
            [InlineKeyboardButton("🏆 𝐑𝐚𝐧𝐤𝐢𝐧𝐠", callback_data=PVP_RANKING),
             InlineKeyboardButton("📜 𝐇𝐢𝐬𝐭𝐨́𝐫𝐢𝐜𝐨", callback_data=PVP_HISTORICO)],
            [InlineKeyboardButton("⬅️ 𝑽𝒐𝒍𝒕𝒂𝒓 𝒂𝒐 𝑹𝒆𝒊𝒏𝒐", callback_data="show_kingdom_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # 4. Deleta a mensagem anterior (se for callback)
        if update.callback_query:
            try:
                await update.callback_query.delete_message()
            except Exception:
                pass

        # 5. Envia a mensagem com mídia ou texto
        media_data = file_ids.get_file_data("pvp_arena_media")
        
        if media_data and media_data.get("id"):
            try:
                await context.bot.send_photo(
                    chat_id=chat_id, photo=media_data["id"],
                    caption=caption, reply_markup=reply_markup, parse_mode="HTML"
                )
                return
            except Exception as e_photo:
                logger.error(f"Falha ao enviar pvp_arena_media: {e_photo}")

        # Fallback
        await context.bot.send_message(
            chat_id=chat_id, text=caption,
            reply_markup=reply_markup, parse_mode="HTML"
        )

    except Exception as e_geral:
        logger.error(f"Erro inesperado em pvp_menu_command: {e_geral}", exc_info=True)
        try:
            await context.bot.send_message(chat_id, "Ocorreu um erro ao abrir o menu PvP. Tente novamente.")
        except Exception:
            pass

async def pvp_battle_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # <<< CORREÇÃO 11: Adiciona await >>>
    new_state, log_do_turno = await pvp_battle.processar_turno_ataque(user_id)
    
    if not new_state:
        await query.edit_message_text("Esta batalha não está mais ativa.")
        return

    # <<< CORREÇÃO 12: Adiciona await >>>
    texto_atualizado = await pvp_battle.formatar_mensagem_batalha(new_state)
    texto_atualizado += "\n\n--- Últimas Ações ---\n" + "\n".join(log_do_turno)
    
    p1_id = new_state["player1"]["id"]
    p2_id = new_state["player2"]["id"]
    p1_msg_id = new_state["messages"].get(p1_id)
    p2_msg_id = new_state["messages"].get(p2_id)
    
    keyboard = [[
        InlineKeyboardButton("⚔️ Atacar", callback_data="pvp_battle_attack"),
        InlineKeyboardButton("🏃 Fugir", callback_data="pvp_battle_flee"), 
    ]]
    
    if new_state.get("turn"): # Se a batalha não acabou
        reply_markup_p1 = InlineKeyboardMarkup(keyboard) if new_state["turn"] == p1_id else None
        reply_markup_p2 = InlineKeyboardMarkup(keyboard) if new_state["turn"] == p2_id else None
    else: # Batalha terminada
        reply_markup_p1 = None
        reply_markup_p2 = None

    if p1_msg_id:
        await context.bot.edit_message_text(
            chat_id=p1_id, message_id=p1_msg_id, 
            text=texto_atualizado, reply_markup=reply_markup_p1, parse_mode="HTML"
        )
    if p2_msg_id:
        await context.bot.edit_message_text(
            chat_id=p2_id, message_id=p2_msg_id, 
            text=texto_atualizado, reply_markup=reply_markup_p2, parse_mode="HTML"
        )

def pvp_handlers() -> list:
    return [
        CommandHandler("pvp", pvp_menu_command),
        CallbackQueryHandler(pvp_menu_command, pattern=r'^pvp_arena$'), 
        CallbackQueryHandler(procurar_oponente_callback, pattern=f'^{PVP_PROCURAR_OPONENTE}$'),
        CallbackQueryHandler(ranking_callback, pattern=f'^{PVP_RANKING}$'),
        CallbackQueryHandler(historico_callback, pattern=f'^{PVP_HISTORICO}$'),
        CallbackQueryHandler(pvp_battle_action_callback, pattern=r'^pvp_battle_attack$'),
    ]