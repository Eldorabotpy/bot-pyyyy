# Em pvp/pvp_handler.py

import logging
import random
import datetime
from modules import clan_manager
from .pvp_config import ARENA_MODIFIERS, MONTHLY_RANKING_REWARDS
from . import pvp_battle
from . import pvp_config
from . import pvp_utils
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaVideo
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from modules import player_manager, file_ids, game_data

logger = logging.getLogger(__name__)


PVP_PROCURAR_OPONENTE = "pvp_procurar_oponente"
PVP_RANKING = "pvp_ranking"
PVP_HISTORICO = "pvp_historico"

async def procurar_oponente_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # Verifica se a mensagem original ainda existe
    if not query.message:
        await query.answer("Esta ação expirou.", show_alert=True)
        return
        
    await query.answer("Procurando um oponente digno...")
    user_id = query.from_user.id
    player_data = player_manager.get_player_data(user_id)
    print(f"\n>>> DEBUG: [PvP Match] User {user_id} iniciando busca.") # <-- NOVO
    
    # Lógica de Entradas via Item
    item_id_entrada = "ticket_arena" # Define o ID do item de entrada

    # 1. Verifica se o jogador TEM o item
    if not player_manager.has_item(player_data, item_id_entrada, quantity=1):
        # Obtém a quantidade atual para a mensagem (opcional)
        current_tickets = player_data.get('inventory', {}).get(item_id_entrada, 0)
        item_name = game_data.ITEMS_DATA.get(item_id_entrada, {}).get('display_name', item_id_entrada) # Para nome bonito

        await context.bot.answer_callback_query(
            query.id, 
            f"Você não tem {item_name} suficiente! ({current_tickets} restantes)", 
            show_alert=True
        )
        print(f">>> DEBUG: [PvP Match] User {user_id} sem item '{item_id_entrada}'.") # Debug
        return # Impede a continuação

    # 2. Se tem, CONSOME o item
    # Presume que remove_item_from_inventory retorna True/False
    item_consumido_com_sucesso = player_manager.remove_item_from_inventory(player_data, item_id_entrada, quantity=1)

    # 3. Verifica se o consumo correu bem (importante!)
    if not item_consumido_com_sucesso:
        item_name = game_data.ITEMS_DATA.get(item_id_entrada, {}).get('display_name', item_id_entrada) # Pega nome de novo
        await context.bot.answer_callback_query(
            query.id, 
            f"Erro ao tentar usar o {item_name}. Tente novamente.", 
            show_alert=True
        )
        print(f">>> DEBUG: [PvP Match] User {user_id} - Falha ao REMOVER '{item_id_entrada}'.") # Debug
        # Não salva os dados aqui, pois a remoção falhou
        return

    # 4. Salva os dados APÓS consumir o item com sucesso
    player_manager.save_player_data(user_id, player_data) 
    print(f">>> DEBUG: [PvP Match] Item '{item_id_entrada}' consumido e dados salvos para {user_id}.") # Debug
    
    # Lógica do Modificador do Dia
    today_weekday = datetime.datetime.now().weekday()
    modifier = ARENA_MODIFIERS.get(today_weekday)
    current_effect = None
    if modifier:
        current_effect = modifier.get("effect")
    print(f">>> DEBUG: [PvP Match] Modificador do dia: {current_effect or 'Nenhum'}") # <-- NOVO

    # Lógica de Matchmaking
    my_points = player_manager.get_pvp_points(player_data)
    my_elo = pvp_utils.get_player_elo(my_points)
    print(f">>> DEBUG: [PvP Match] User {user_id} tem {my_points} pontos (Elo: {my_elo})") # <-- NOVO
    
    same_elo_opponents = []
    lower_elo_opponents = []
    
    print(">>> DEBUG: [PvP Match] Iniciando loop de oponentes...") # <-- NOVO
    opponent_count = 0 # <-- NOVO
    try: # <-- NOVO TRY/EXCEPT
        for opponent_id, opp_data in player_manager.iter_players():
            opponent_count += 1 # <-- NOVO
            # print(f">>> DEBUG: [PvP Match] Verificando oponente {opponent_count}: ID {opponent_id}") # <-- DEBUG MUITO VERBOSO (descomentar se necessário)
            if opponent_id == user_id: 
                # print(f">>> DEBUG: [PvP Match] Oponente {opponent_id} é o próprio user. Pulando.") # <-- DEBUG MUITO VERBOSO
                continue
            
            # Tenta obter pontos e elo do oponente DENTRO de um try/except
            try:
                opp_points = player_manager.get_pvp_points(opp_data)
                opp_elo = pvp_utils.get_player_elo(opp_points)
            except Exception as e_opp_stats:
                logger.error(f"Erro ao obter stats PvP do oponente {opponent_id}: {e_opp_stats}")
                print(f">>> DEBUG: [PvP Match] ERRO ao obter stats PvP do oponente {opponent_id}: {e_opp_stats}. Pulando.") # <-- NOVO
                continue # Pula este oponente se houver erro

            # print(f">>> DEBUG: [PvP Match] Oponente {opponent_id} tem {opp_points} pontos (Elo: {opp_elo})") # <-- DEBUG MUITO VERBOSO

            if my_elo == opp_elo:
                same_elo_opponents.append(opponent_id)
            elif opp_points < my_points:
                lower_elo_opponents.append(opponent_id)
                
    except Exception as e_iter:
         # Se o PRÓPRIO iter_players() falhar
         logger.error(f"Erro CRÍTICO durante player_manager.iter_players(): {e_iter}", exc_info=True)
         print(f">>> DEBUG: [PvP Match] ERRO CRÍTICO no loop iter_players: {e_iter}") # <-- NOVO
         # Não devolve a entrada aqui, pois já foi consumida e salva
         error_message = ("🛡️ **Falha na Busca** 🛡️\n\nOcorreu um erro ao procurar oponentes.")
         keyboard = [[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]]; reply_markup = InlineKeyboardMarkup(keyboard)
         original_message_is_media = bool(query.message.photo or query.message.video or query.message.animation)
         try:
             if original_message_is_media: await query.edit_message_caption(caption=error_message, reply_markup=reply_markup, parse_mode="HTML")
             else: await query.edit_message_text(text=error_message, reply_markup=reply_markup, parse_mode="HTML")
         except Exception: pass
         return # Termina a função aqui

    print(f">>> DEBUG: [PvP Match] Loop de oponentes concluído. Verificados {opponent_count} jogadores.") # <-- NOVO
    print(f">>> DEBUG: [PvP Match] Oponentes mesmo Elo: {len(same_elo_opponents)}") # <-- NOVO
    print(f">>> DEBUG: [PvP Match] Oponentes Elo inferior: {len(lower_elo_opponents)}") # <-- NOVO

    # Escolhe o oponente
    final_opponent_id = None
    if same_elo_opponents:
        final_opponent_id = random.choice(same_elo_opponents)
        print(f">>> DEBUG: [PvP Match] Oponente escolhido (mesmo Elo): {final_opponent_id}") # <-- NOVO
    elif lower_elo_opponents:
        final_opponent_id = random.choice(lower_elo_opponents)
        print(f">>> DEBUG: [PvP Match] Oponente escolhido (Elo inferior): {final_opponent_id}") # <-- NOVO
    else:
         print(f">>> DEBUG: [PvP Match] Nenhum oponente elegível encontrado.") # <-- NOVO

    # Determina o tipo da mensagem original (já estava aqui)
    original_message_is_media = bool(query.message.photo or query.message.video or query.message.animation)

    if final_opponent_id:
        opponent_data = player_manager.get_player_data(final_opponent_id)
        caption_batalha = "⚔️ Oponente encontrado! Simulando batalha..."
        print(f">>> DEBUG: [PvP Match] Preparando para editar msg para '{caption_batalha}'") # <-- NOVO

        # Edita a mensagem ANTES da batalha
        try:
            # === DEBUG PRINTS ADICIONADOS ===
            print("\n--- DEBUG Mídia Classe ---")
            print(f"Opponent Data (parcial): class='{opponent_data.get('class')}', classe='{opponent_data.get('classe')}', class_key='{opponent_data.get('class_key')}'")
            # === FIM DEBUG PRINTS ===

            opponent_class_key = (opponent_data.get("class_key") or opponent_data.get("class") or opponent_data.get("classe") or opponent_data.get("class_type") or "default")
            video_key = f"classe_{opponent_class_key.lower()}_media"
            media_data = file_ids.get_file_data(video_key)

            # === DEBUG PRINTS ADICIONADOS ===
            print(f"Classe Resolvida: '{opponent_class_key}'")
            print(f"Chave de Mídia Procurada: '{video_key}'")
            print(f"Dados da Mídia Encontrados: {media_data}")
            print("--- FIM DEBUG Mídia Classe ---\n")
            # === FIM DEBUG PRINTS ===

            if media_data and media_data.get("id") and original_message_is_media:
                new_media = InputMediaVideo(media=media_data["id"], caption=caption_batalha, parse_mode="HTML")
                await query.edit_message_media(media=new_media)
                print(f">>> DEBUG: [PvP Match] edit_message_media SUCESSO.") # <-- NOVO
            elif original_message_is_media:
                logger.warning(f"Vídeo/Mídia '{video_key}' não encontrado ou msg é mídia. Usando edit_caption.")
                await query.edit_message_caption(caption=caption_batalha, parse_mode="HTML")
                print(f">>> DEBUG: [PvP Match] edit_message_caption (fallback video) SUCESSO.") # <-- NOVO
            else:
                await query.edit_message_text(text=caption_batalha, parse_mode="HTML")
                print(f">>> DEBUG: [PvP Match] edit_message_text (fallback mídia) SUCESSO.") # <-- NOVO
        except Exception as e_edit_initial:
            logger.error(f"Falha ao editar msg ANTES da batalha: {e_edit_initial}. Tentando fallback final.")
            print(f">>> DEBUG: [PvP Match] ERRO ao editar msg antes da batalha: {e_edit_initial}") # <-- NOVO
            try:
                await query.edit_message_text(text=caption_batalha, parse_mode="HTML")
                print(f">>> DEBUG: [PvP Match] edit_message_text (fallback final) SUCESSO.") # <-- NOVO
            except Exception as e_fallback_text:
                 logger.error(f"Falha no fallback final de texto: {e_fallback_text}")
                 print(f">>> DEBUG: [PvP Match] ERRO no fallback final de texto: {e_fallback_text}") # <-- NOVO

        # Bloco de Segurança da Batalha
        try:
            print(f">>> DEBUG: [PvP Match] CHAMANDO simular_batalha_completa...") # <-- NOVO
            vencedor_id, log_completo = pvp_battle.simular_batalha_completa( user_id, final_opponent_id, modifier_effect=current_effect )
            print(f">>> DEBUG: [PvP Match] simular_batalha_completa RETORNOU. Vencedor: {vencedor_id}") # <-- NOVO
            
            # Lógica de Elo e Recompensas
            elo_ganho_base = 25
            elo_perdido_base = 15
            log_final = list(log_completo)
            if current_effect == "prestige_day":
                elo_ganho = int(elo_ganho_base * 1.5); elo_perdido = int(elo_perdido_base * 1.5)
                log_final.append("\n🏆 <b>Dia do Prestígio!</b> Pontos de Elo aumentados!")
            else:
                elo_ganho = elo_ganho_base; elo_perdido = elo_perdido_base
            
            if vencedor_id == user_id:
                player_manager.add_pvp_points(player_data, elo_ganho)
                player_manager.add_pvp_points(opponent_data, -elo_perdido)
                log_final.append(f"\n🏆 Você ganhou <b>+{elo_ganho}</b> pontos de Elo!")
                if current_effect == "greed_day": log_final.append("💰 <b>Dia da Ganância!</b> Ouro dobrado!")
                clan_id = player_data.get("clan_id")
                if clan_id: clan_manager.update_guild_mission_progress(clan_id=clan_id, mission_type='PVP_WIN', details={'count': 1}, context=context)
            elif vencedor_id == final_opponent_id:
                player_manager.add_pvp_points(player_data, -elo_perdido)
                player_manager.add_pvp_points(opponent_data, elo_ganho)
                log_final.append(f"\n❌ Você perdeu <b>-{elo_perdido}</b> pontos de Elo.")
            
            # Salvar dados
            player_manager.save_player_data(user_id, player_data)
            player_manager.save_player_data(final_opponent_id, opponent_data)
            print(f">>> DEBUG: [PvP Match] Dados salvos para user {user_id} e oponente {final_opponent_id}") # <-- NOVO

            # Exibe o resultado final
            resultado_final = "\n".join(log_final)
            keyboard = [[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]]; reply_markup = InlineKeyboardMarkup(keyboard)
            print(f">>> DEBUG: [PvP Match] Preparando para exibir resultado final (len={len(resultado_final)})...") # <-- NOVO

            # Lógica para Logs Longos e Fallback
            if len(resultado_final) > 1020:
                logger.warning("Log de batalha >1024. Enviando como nova mensagem.")
                print(f">>> DEBUG: [PvP Match] Log longo ({len(resultado_final)} chars), enviando nova mensagem.") # <-- NOVO
                try: 
                    await query.delete_message()
                    print(f">>> DEBUG: [PvP Match] Mensagem de mídia deletada.") # <-- NOVO
                except Exception as e_del_long: 
                    logger.error(f"Falha ao deletar msg antes de enviar log longo: {e_del_long}")
                    print(f">>> DEBUG: [PvP Match] Falha ao deletar msg antes de log longo: {e_del_long}") # <-- NOVO
                    pass
                await context.bot.send_message(
                    chat_id=query.message.chat_id, text=resultado_final[:4090],
                    reply_markup=reply_markup, parse_mode="HTML"
                )
                print(f">>> DEBUG: [PvP Match] Nova mensagem (log longo) enviada.") # <-- NOVO
            else:
                 # Log curto: Tenta editar (prioriza o tipo original da msg)
                 print(f">>> DEBUG: [PvP Match] Log curto ({len(resultado_final)} chars), tentando editar.") # <-- NOVO
                 try:
                     if original_message_is_media:
                         await query.edit_message_caption(caption=resultado_final, reply_markup=reply_markup, parse_mode="HTML")
                         print(f">>> DEBUG: [PvP Match] edit_message_caption (resultado) SUCESSO.") # <-- NOVO
                     else:
                         await query.edit_message_text(text=resultado_final, reply_markup=reply_markup, parse_mode="HTML")
                         print(f">>> DEBUG: [PvP Match] edit_message_text (resultado) SUCESSO.") # <-- NOVO
                 except Exception as e_edit_final:
                     # Se a primeira tentativa falhar (raro, mas possível), tenta o outro método
                     logger.warning(f"Falha ao editar resultado ({e_edit_final}), tentando método alternativo.")
                     print(f">>> DEBUG: [PvP Match] ERRO ao editar resultado ({e_edit_final}), tentando fallback.") # <-- NOVO
                     try:
                         if original_message_is_media: # Falhou caption, tenta texto (improvável)
                            await query.edit_message_text(text=resultado_final, reply_markup=reply_markup, parse_mode="HTML")
                            print(f">>> DEBUG: [PvP Match] edit_message_text (fallback resultado) SUCESSO.") # <-- NOVO
                         else: # Falhou texto, tenta caption (improvável)
                            await query.edit_message_caption(caption=resultado_final, reply_markup=reply_markup, parse_mode="HTML")
                            print(f">>> DEBUG: [PvP Match] edit_message_caption (fallback resultado) SUCESSO.") # <-- NOVO
                     except Exception as e_edit_final_fallback:
                          logger.error(f"Falha CRÍTICA ao exibir resultado final: {e_edit_final_fallback}")
                          print(f">>> DEBUG: [PvP Match] ERRO CRÍTICO ao exibir resultado final: {e_edit_final_fallback}") # <-- NOVO

        except Exception as e_battle:
            # Captura de Erro da Batalha
            logger.error(f"Erro CRÍTICO durante a simulação da batalha: {e_battle}", exc_info=True)
            print(f">>> DEBUG: [PvP Match] ERRO CRÍTICO no bloco try da batalha: {e_battle}") # <-- NOVO
            # Não devolve a entrada aqui pois já foi gasta E salva
            error_message = ("🛡️ **Falha na Batalha** 🛡️\n\nOcorreu um erro.\nSua entrada foi consumida.") # Mensagem ajustada
            keyboard = [[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]]; reply_markup = InlineKeyboardMarkup(keyboard)
            try: # Tenta editar (prioriza tipo original)
                if original_message_is_media: await query.edit_message_caption(caption=error_message, reply_markup=reply_markup, parse_mode="HTML")
                else: await query.edit_message_text(text=error_message, reply_markup=reply_markup, parse_mode="HTML")
            except Exception: pass # Falha silenciosa se não conseguir avisar

    else: # Se não achou oponente
        print(f">>> DEBUG: [PvP Match] NENHUM OPONENTE ENCONTRADO. Editando mensagem.") # <-- NOVO
        no_opp_msg = "🛡️ Nenhum oponente encontrado. Tente novamente."
        # Não devolve a entrada aqui pois já foi gasta E salva
        try:
            if original_message_is_media: await query.edit_message_caption(caption=no_opp_msg)
            else: await query.edit_message_text(text=no_opp_msg)
            print(f">>> DEBUG: [PvP Match] Mensagem 'Nenhum Oponente' editada.") # <-- NOVO
        except Exception as e_no_opp: 
             print(f">>> DEBUG: [PvP Match] Falha ao editar msg 'Nenhum Oponente': {e_no_opp}") # <-- NOVO
             pass
        
async def ranking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe o ranking PvP dos melhores jogadores e os prémios mensais."""
    query = update.callback_query
    await query.answer("Calculando o ranking...")
    user_id = query.from_user.id

    # 1. Buscar todos os jogadores com pontos PvP
    all_players_ranked = []
    try:
        player_iterator = player_manager.iter_players()
        if isinstance(player_iterator, dict): player_iterator = player_iterator.items()

        for p_id, p_data in player_iterator:
            pvp_points = player_manager.get_pvp_points(p_data)
            # Alterado para incluir apenas > 0 pontos
            if pvp_points > 0:
               all_players_ranked.append({
                   "user_id": p_id,
                   "name": p_data.get("character_name", f"ID: {p_id}"),
                   "points": pvp_points
               })
    except Exception as e:
         logger.error(f"Erro ao iterar jogadores para ranking: {e}", exc_info=True)
         # Tenta editar a mensagem existente com erro
         try: await query.edit_message_caption("❌ Erro ao buscar dados do ranking.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]]))
         except Exception: await query.edit_message_text("❌ Erro ao buscar dados do ranking.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]]))
         return

    # 2. Ordenar por pontos
    all_players_ranked.sort(key=lambda p: p["points"], reverse=True)

    # 3. Construir a mensagem do Ranking (Top 10)
    ranking_text_lines = ["🏆 **Ranking da Arena de Eldora** 🏆\n"]
    top_n = 10
    player_rank = -1

    if not all_players_ranked:
        ranking_text_lines.append("Ainda não há jogadores classificados nesta temporada.")
    else:
        for i, player in enumerate(all_players_ranked):
            rank = i + 1
            elo_name, elo_display = pvp_utils.get_player_elo_details(player["points"])
            line = f"{rank}. {elo_display} - {player['name']} ({player['points']} Pts)"

            if rank <= top_n:
                ranking_text_lines.append(line)
            if player["user_id"] == user_id:
                player_rank = rank

        # 4. Adiciona a posição do jogador atual (se não estiver no Top N)
        if player_rank > top_n:
            ranking_text_lines.append("\n...")
            my_player_data = next((p for p in all_players_ranked if p["user_id"] == user_id), None)
            if my_player_data:
                 _, my_elo_display = pvp_utils.get_player_elo_details(my_player_data["points"])
                 ranking_text_lines.append(f"{player_rank}. {my_elo_display} - {my_player_data['name']} ({my_player_data['points']} Pts) (Você)")

    # =========================================================
    # 👇 [MELHORIA] Adicionar Secção de Prémios Mensais 👇
    # =========================================================
    ranking_text_lines.append("\n\n💎 **Recompensas Mensais (Top 3):**")
    for rank, reward in sorted(MONTHLY_RANKING_REWARDS.items()):
        ranking_text_lines.append(f"  {rank}º Lugar: {reward} Gemas (Dimas)")
    ranking_text_lines.append("_(Próximo reset em ~30 dias)_") # Ou 28
    # =========================================================

    # 5. Adiciona informações adicionais
    ranking_text_lines.append(f"\nTotal de jogadores no ranking: {len(all_players_ranked)}")

    # 6. Monta a mensagem final e o teclado
    final_text = "\n".join(ranking_text_lines)
    keyboard = [[InlineKeyboardButton("⬅️ Voltar para a Arena", callback_data="pvp_arena")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # 7. Edita a mensagem (lógica robusta mantida)
    original_message_is_media = bool(query.message.photo or query.message.video or query.message.animation)
    try:
        # Verifica o comprimento ANTES de tentar editar legenda
        if original_message_is_media and len(final_text) > 1020:
             logger.warning("Mensagem de ranking muito longa para legenda. Enviando como texto.")
             # Apaga a mídia e envia como texto
             await query.delete_message()
             await context.bot.send_message(chat_id=query.message.chat_id, text=final_text[:4090], reply_markup=reply_markup, parse_mode="HTML")
        elif original_message_is_media:
            await query.edit_message_caption(caption=final_text, reply_markup=reply_markup, parse_mode="HTML")
        else: # Mensagem original era texto
            await query.edit_message_text(text=final_text[:4090], reply_markup=reply_markup, parse_mode="HTML") # Adiciona limite aqui também por segurança
    except Exception as e_edit:
        logger.error(f"Falha ao editar mensagem do ranking: {e_edit}")
        # Fallback final: Envia como nova mensagem
        try:
            await context.bot.send_message(chat_id=query.message.chat_id, text=final_text[:4090], reply_markup=reply_markup, parse_mode="HTML")
        except Exception as e_send:
             logger.error(f"Falha CRÍTICA ao enviar mensagem do ranking: {e_send}")

async def historico_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Função 'Histórico' ainda em construção!", show_alert=True)

async def pvp_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde ao comando /pvp ou a um botão para abrir o menu da arena."""
    print("\n>>> DEBUG: 1. Entrou em pvp_menu_command") # <-- ADICIONADO
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    print(f">>> DEBUG: 2. User ID: {user_id}, Chat ID: {chat_id}") # <-- ADICIONADO

    try: # Adiciona um try/except geral para capturar erros inesperados
        if not player_manager.get_player_data(user_id):
            print(">>> DEBUG: 3a. Jogador NÃO encontrado. Enviando mensagem de erro.") # <-- ADICIONADO
            await context.bot.send_message(chat_id, "Você precisa criar um personagem primeiro com /start.")
            print(">>> DEBUG: 3b. Mensagem de erro (jogador não encontrado) enviada.") # <-- ADICIONADO
            return
        
        print(">>> DEBUG: 4. Jogador encontrado. Buscando modificador...") # <-- ADICIONADO
        today_weekday = datetime.datetime.now().weekday()
        modifier = ARENA_MODIFIERS.get(today_weekday)
        print(f">>> DEBUG: 5. Modificador encontrado: {modifier.get('name') if modifier else 'Nenhum'}") # <-- ADICIONADO

        modifier_text = ""
        if modifier:
            modifier_text = (
                f"\n🔥 <b>Modificador de Hoje: {modifier['name']}</b>\n"
                f"<i>{modifier['description']}</i>\n"
            )
        
        caption = (
            "⚔️ **Arena de Eldora** ⚔️\n"
            f"{modifier_text}\n"
            "Escolha seu caminho, campeão:"
        )
        print(">>> DEBUG: 6. Caption e Keyboard preparados.") # <-- ADICIONADO

        keyboard = [
            [InlineKeyboardButton("⚔️ Procurar Oponente (Ranqueado)", callback_data=PVP_PROCURAR_OPONENTE)],
            [
                InlineKeyboardButton("🏆 Ranking", callback_data=PVP_RANKING),
                InlineKeyboardButton("📜 Histórico", callback_data=PVP_HISTORICO),
            ],
            [InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data="show_kingdom_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Deleta a mensagem anterior se veio de um botão
        if update.callback_query:
            try:
                print(">>> DEBUG: 7a. Tentando deletar mensagem anterior (callback)...") # <-- ADICIONADO
                await update.callback_query.delete_message()
                print(">>> DEBUG: 7b. Mensagem anterior deletada.") # <-- ADICIONADO
            except Exception as e_del:
                 print(f">>> DEBUG: 7c. Falha ao deletar mensagem anterior: {e_del}") # <-- ADICIONADO
                 pass # Ignora se não conseguir deletar

        print(">>> DEBUG: 8. Preparando para enviar mensagem/foto...") # <-- ADICIONADO
        # Tenta enviar com a imagem de fundo da arena
        media_data = file_ids.get_file_data("pvp_arena_media")
        
        # <<< ADICIONADO DEBUG EXTRA AQUI >>>
        print(f">>> DEBUG: 9. Media data para 'pvp_arena_media': {media_data}") 
        
        if media_data and media_data.get("id"):
            try:
                print(">>> DEBUG: 10a. Tentando enviar FOTO...") # <-- ADICIONADO
                await context.bot.send_photo(
                    chat_id=chat_id, photo=media_data["id"],
                    caption=caption, reply_markup=reply_markup, parse_mode="HTML"
                )
                print(">>> DEBUG: 10b. FOTO enviada com sucesso.") # <-- ADICIONADO
                return
            except Exception as e_photo:
                logger.error(f"Falha ao enviar pvp_arena_media: {e_photo}")
                print(f">>> DEBUG: 10c. ERRO ao enviar foto: {e_photo}") # <-- ADICIONADO
                # Continua para o fallback de texto

        # Fallback: se não conseguir enviar a foto, envia só o texto
        try:
            print(">>> DEBUG: 11a. Tentando enviar TEXTO (fallback)...") # <-- ADICIONADO
            await context.bot.send_message(
                chat_id=chat_id, text=caption,
                reply_markup=reply_markup, parse_mode="HTML"
            )
            print(">>> DEBUG: 11b. TEXTO enviado com sucesso.") # <-- ADICIONADO
        except Exception as e_text:
             print(f">>> DEBUG: 11c. ERRO CRÍTICO ao enviar texto fallback: {e_text}") # <-- ADICIONADO
             logger.error(f"Falha crítica ao enviar fallback de texto no pvp_menu: {e_text}", exc_info=True)

    except Exception as e_geral:
        # Captura qualquer outro erro inesperado na função
        print(f">>> DEBUG: ERRO GERAL INESPERADO em pvp_menu_command: {e_geral}") # <-- ADICIONADO
        logger.error(f"Erro inesperado em pvp_menu_command: {e_geral}", exc_info=True)
        # Tenta enviar uma mensagem de erro simples para o usuário
        try:
            await context.bot.send_message(chat_id, "Ocorreu um erro ao abrir o menu PvP. Tente novamente.")
        except Exception:
            pass # Ignora se nem a msg de erro puder ser enviada


async def pvp_battle_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    new_state, log_do_turno = pvp_battle.processar_turno_ataque(user_id)
    
    if not new_state:
        await query.edit_message_text("Esta batalha não está mais ativa.")
        return

    # Junta o log do turno ao texto principal da batalha
    texto_atualizado = pvp_battle.formatar_mensagem_batalha(new_state)
    texto_atualizado += "\n\n--- Últimas Ações ---\n" + "\n".join(log_do_turno)
    
    p1_id = new_state["player1"]["id"]
    p2_id = new_state["player2"]["id"]
    p1_msg_id = new_state["messages"].get(p1_id)
    p2_msg_id = new_state["messages"].get(p2_id)
    
    # Teclado de ações
    keyboard = [[
        InlineKeyboardButton("⚔️ Atacar", callback_data="pvp_battle_attack"),
        InlineKeyboardButton("🏃 Fugir", callback_data="pvp_battle_flee"),
    ]]
    
    # Define quem verá os botões
    if new_state.get("turn"): # Se a batalha não acabou
        reply_markup_p1 = InlineKeyboardMarkup(keyboard) if new_state["turn"] == p1_id else None
        reply_markup_p2 = InlineKeyboardMarkup(keyboard) if new_state["turn"] == p2_id else None
    else: # Batalha terminada
        reply_markup_p1 = None
        reply_markup_p2 = None

    # EDITA a mensagem de batalha para ambos os jogadores
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

# --- Agrupador de Handlers ---
# (Uma função que retorna todos os handlers deste arquivo, para manter o main.py limpo)
def pvp_handlers() -> list:
    return [
        CommandHandler("pvp", pvp_menu_command),
        CallbackQueryHandler(pvp_menu_command, pattern=r'^pvp_arena$'), # Botão do menu do Reino
        CallbackQueryHandler(procurar_oponente_callback, pattern=f'^{PVP_PROCURAR_OPONENTE}$'),
        CallbackQueryHandler(ranking_callback, pattern=f'^{PVP_RANKING}$'),
        CallbackQueryHandler(historico_callback, pattern=f'^{PVP_HISTORICO}$'),
        CallbackQueryHandler(pvp_battle_action_callback, pattern=r'^pvp_battle_attack$'),

    ]