# Em pvp/pvp_handler.py

import logging
import random
import datetime
from modules import clan_manager
from .pvp_config import ARENA_MODIFIERS
from . import pvp_battle
from . import pvp_config
from . import pvp_utils
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaVideo
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from modules import player_manager, file_ids

logger = logging.getLogger(__name__)


PVP_PROCURAR_OPONENTE = "pvp_procurar_oponente"
PVP_RANKING = "pvp_ranking"
PVP_HISTORICO = "pvp_historico"

async def procurar_oponente_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Procurando um oponente digno...")
    user_id = query.from_user.id
    player_data = player_manager.get_player_data(user_id)
    
    # 1. Lógica do Sistema de Entradas (Tickets)
    if not player_manager.use_pvp_entry(player_data):
        remaining_entries = player_manager.get_pvp_entries(player_data)
        await context.bot.answer_callback_query(query.id, f"Você não tem mais entradas de PvP hoje! ({remaining_entries}/10)", show_alert=True)
        return
    
    player_manager.save_player_data(user_id, player_data)

    # Lógica do Modificador do Dia
    today_weekday = datetime.datetime.now().weekday()
    modifier = ARENA_MODIFIERS.get(today_weekday)
    current_effect = None
    if modifier:
        current_effect = modifier.get("effect")

    # 2. Lógica de Matchmaking Flexível
    my_points = player_manager.get_pvp_points(player_data)
    my_elo = pvp_utils.get_player_elo(my_points)
    
    same_elo_opponents = []
    lower_elo_opponents = []

    for opponent_id, opp_data in player_manager.iter_players():
        if opponent_id == user_id: continue
        
        opp_points = player_manager.get_pvp_points(opp_data)
        opp_elo = pvp_utils.get_player_elo(opp_points)
        
        if my_elo == opp_elo:
            same_elo_opponents.append(opponent_id)
        elif opp_points < my_points:
            lower_elo_opponents.append(opponent_id)

    # 3. Escolhe o oponente com prioridade
    final_opponent_id = None
    if same_elo_opponents:
        final_opponent_id = random.choice(same_elo_opponents)
    elif lower_elo_opponents:
        final_opponent_id = random.choice(lower_elo_opponents)

    # 4. Inicia a Batalha ou Informa que não encontrou
    if final_opponent_id:
        
        opponent_data = player_manager.get_player_data(final_opponent_id)
        
        caption_batalha = "⚔️ Oponente encontrado! Simulando batalha..."
        
        # Bloco de Lógica para editar a mensagem ANTES da batalha
        try:
            opponent_class_key = (
                opponent_data.get("class_key") or
                opponent_data.get("class") or
                opponent_data.get("classe") or
                opponent_data.get("class_type") or
                "default"
            )
            
            video_key = f"classe_{opponent_class_key.lower()}_media"
            media_data = file_ids.get_file_data(video_key)

            if media_data and media_data.get("id"):
                new_media = InputMediaVideo(
                    media=media_data["id"],
                    caption=caption_batalha,
                    parse_mode="HTML"
                )
                await query.edit_message_media(media=new_media)
            else:
                logger.warning(f"Vídeo/Mídia '{video_key}' não encontrado. Usando edit_caption.")
                await query.edit_message_caption(caption=caption_batalha, parse_mode="HTML")
        
        except Exception as e:
            # Lógica de Fallback melhorada
            logger.error(f"Falha ao trocar mídia/caption: {e}")
            try:
                await query.edit_message_caption(caption=caption_batalha, parse_mode="HTML")
            except Exception as e2:
                logger.error(f"Falha ao editar caption como fallback: {e2}")
                try:
                    await query.edit_message_text(text=caption_batalha, parse_mode="HTML")
                except Exception as e3:
                     logger.error(f"Falha ao editar texto como fallback final: {e3}")
        
        # Bloco de Segurança da Batalha (try...except e_battle)
        try:
            vencedor_id, log_completo = pvp_battle.simular_batalha_completa(
                user_id, 
                final_opponent_id,
                modifier_effect=current_effect
            )
            
            # ... (Lógica de Elo base) ...
            elo_ganho_base = 25
            elo_perdido_base = 15
            log_final = list(log_completo)
            
            # ... (Lógica do Modificador de Prestígio) ...
            if current_effect == "prestige_day":
                elo_ganho = int(elo_ganho_base * 1.5)
                elo_perdido = int(elo_perdido_base * 1.5)
                log_final.append("\n🏆 <b>Dia do Prestígio!</b> Pontos de Elo ganhos/perdidos aumentados em 50%!")
            else:
                elo_ganho = elo_ganho_base
                elo_perdido = elo_perdido_base
            
            # Lógica de Vitória/Derrota
            if vencedor_id == user_id:
                player_manager.add_pvp_points(player_data, elo_ganho)
                player_manager.add_pvp_points(opponent_data, -elo_perdido)
                log_final.append(f"\n🏆 Você ganhou <b>+{elo_ganho}</b> pontos de Elo!")
                
                if current_effect == "greed_day":
                    log_final.append("💰 <b>Dia da Ganância!</b> Recompensas em Ouro da vitória são dobradas!")

                clan_id = player_data.get("clan_id")
                if clan_id:
                    clan_manager.update_guild_mission_progress(
                        clan_id=clan_id,
                        mission_type='PVP_WIN',
                        details={'count': 1},
                        context=context
                    )

            elif vencedor_id == final_opponent_id:
                player_manager.add_pvp_points(player_data, -elo_perdido)
                player_manager.add_pvp_points(opponent_data, elo_ganho)
                log_final.append(f"\n❌ Você perdeu <b>-{elo_perdido}</b> pontos de Elo.")
            
            # Salva os dados
            player_manager.save_player_data(user_id, player_data)
            player_manager.save_player_data(final_opponent_id, opponent_data)

            # Formata e exibe o resultado final
            resultado_final = "\n".join(log_final)
            keyboard = [[InlineKeyboardButton("⬅️ Voltar para a Arena", callback_data="pvp_arena")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # =========================================================
            # 👇 [CORREÇÃO] Lógica para Logs de Batalha Longos 👇
            # =========================================================
            
            # Limite de segurança do Telegram para legendas é 1024
            if len(resultado_final) > 1020:
                # Se o log for muito longo, não podemos usar edit_caption.
                # A melhor solução é apagar a mídia e enviar um novo texto.
                logger.warning("Log de batalha muito longo (>1024). Enviando como nova mensagem.")
                try:
                    await query.delete_message()
                except Exception as del_e:
                    logger.error(f"Falha ao deletar mídia antes de enviar log longo: {del_e}")
                
                # Envia o resultado como uma nova mensagem de texto (limite 4096)
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=resultado_final[:4090], # Trunca por segurança
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            else:
                # Se o log for curto, usa a lógica antiga (robusta)
                try:
                    await query.edit_message_caption(caption=resultado_final, reply_markup=reply_markup, parse_mode="HTML")
                except Exception:
                    await query.edit_message_text(
                        text=resultado_final, 
                        reply_markup=reply_markup, 
                        parse_mode="HTML"
                    )
            # =========================================================
            # 👆 [FIM DA CORREÇÃO] 👆
            # =========================================================
        
        except Exception as e_battle:
            # Bloco de Captura de Erro da Batalha (mantido)
            logger.error(f"Erro CRÍTICO durante a simulação da batalha: {e_battle}", exc_info=True)
            player_manager.add_pvp_entries(player_data, 1) 
            player_manager.save_player_data(user_id, player_data)
            error_message = (
                "🛡️ **Falha na Batalha** 🛡️\n\n"
                "Ocorreu um erro inesperado ao simular a batalha.\n"
                "Sua entrada de PvP foi devolvida. Tente novamente."
            )
            keyboard = [[InlineKeyboardButton("⬅️ Voltar para a Arena", callback_data="pvp_arena")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await query.edit_message_caption(caption=error_message, reply_markup=reply_markup, parse_mode="HTML")
            except Exception:
                await query.edit_message_text(text=error_message, reply_markup=reply_markup, parse_mode="HTML")
        
    else:
        # Se não achou oponente (mantido)
        try:
            await query.edit_message_caption(caption=f"🛡️ Nenhum oponente encontrado no momento. Tente novamente mais tarde.")
        except Exception:
            await query.edit_message_text(text=f"🛡️ Nenhum oponente encontrado no momento. Tente novamente mais tarde.")
            
        player_manager.add_pvp_entries(player_data, 1) 
        player_manager.save_player_data(user_id, player_data)
        
async def ranking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Função 'Ranking' ainda em construção!", show_alert=True)

async def historico_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Função 'Histórico' ainda em construção!", show_alert=True)

async def pvp_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde ao comando /pvp ou a um botão para abrir o menu da arena."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if not player_manager.get_player_data(user_id):
        await context.bot.send_message(chat_id, "Você precisa criar um personagem primeiro com /start.")
        return
    
    today_weekday = datetime.datetime.now().weekday()
    modifier = ARENA_MODIFIERS.get(today_weekday)

    modifier_text = ""
    if modifier:
        modifier_text = (
            f"\n🔥 <b>Modificador de Hoje: {modifier['name']}</b>\n"
            f"<i>{modifier['description']}</i>\n"
        )
    # --- FIM DA NOVA LÓGICA ---

    caption = (
        "⚔️ **Arena de Eldora** ⚔️\n"
        f"{modifier_text}\n"  # Adiciona o texto do modificador à mensagem
        "Escolha seu caminho, campeão:"
    )

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
            await update.callback_query.delete_message()
        except Exception: pass

    # Tenta enviar com a imagem de fundo da arena
    media_data = file_ids.get_file_data("pvp_arena_media")
    if media_data and media_data.get("id"):
        try:
            await context.bot.send_photo(
                chat_id=chat_id, photo=media_data["id"],
                caption=caption, reply_markup=reply_markup, parse_mode="HTML"
            )
            return
        except Exception as e:
            logger.error(f"Falha ao enviar pvp_arena_media: {e}")

    # Fallback: se não conseguir enviar a foto, envia só o texto
    await context.bot.send_message(
        chat_id=chat_id, text=caption,
        reply_markup=reply_markup, parse_mode="HTML"
    )



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