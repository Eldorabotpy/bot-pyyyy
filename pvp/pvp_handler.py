# Em pvp/pvp_handler.py

import logging
import random
import datetime
from modules import clan_manager
from .pvp_config import ARENA_MODIFIERS
from . import pvp_battle
from . import pvp_config
from . import pvp_utils
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from modules import player_manager, file_ids

logger = logging.getLogger(__name__)

# --- Constantes dos Botões ---
# (Usar constantes torna o código mais fácil de manter)
PVP_PROCURAR_OPONENTE = "pvp_procurar_oponente"
PVP_RANKING = "pvp_ranking"
PVP_HISTORICO = "pvp_historico"

# --- Funções dos Botões (Placeholders) ---

# Em pvp/pvp_handler.py

# Em pvp/pvp_handler.py

# Em pvp/pvp_handler.py

# (Garanta que 'random' está importado no topo do arquivo)
import random

# Em pvp/pvp_handler.py

async def procurar_oponente_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Procurando um oponente digno...")
    user_id = query.from_user.id
    player_data = player_manager.get_player_data(user_id)
    
    # 1. Lógica do Sistema de Entradas (Tickets)
    if not player_manager.use_pvp_entry(player_data):
        remaining_entries = player_manager.get_pvp_entries(player_data)
        # <<< NOTA: A resposta aqui deve ser editada na mensagem, não no "answer" que some. >>>
        await context.bot.answer_callback_query(query.id, f"Você não tem mais entradas de PvP hoje! ({remaining_entries}/10)", show_alert=True)
        return
    
    player_manager.save_player_data(user_id, player_data)

    # 2. Lógica de Matchmaking Flexível
    my_points = player_manager.get_pvp_points(player_data)
    my_elo = pvp_utils.get_player_elo(my_points)
    
    same_elo_opponents = []
    lower_elo_opponents = []

    # Este iterador pode ser lento. Para um jogo maior, considere uma base de dados.
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
        await query.edit_message_caption(caption=f"⚔️ Oponente encontrado! Simulando batalha...")
        
        # CHAMA O SIMULADOR DE BATALHA
        vencedor_id, log_completo = pvp_battle.simular_batalha_completa(user_id, final_opponent_id)
        
        elo_ganho = 25
        elo_perdido = 15
        
        log_final = list(log_completo)
        
        opponent_data = player_manager.get_player_data(final_opponent_id)

        if vencedor_id == user_id:
            # Recompensas para o jogador que iniciou
            player_manager.add_pvp_points(player_data, elo_ganho)
            player_manager.add_pvp_points(opponent_data, -elo_perdido) # O oponente perde pontos
            log_final.append(f"\n🏆 Você ganhou <b>+{elo_ganho}</b> pontos de Elo!")

            # =========================================================
            # 👇 INTEGRAÇÃO COM MISSÕES DE GUILDA (PVP_WIN) 👇
            # =========================================================
            clan_id = player_data.get("clan_id")
            if clan_id:
                clan_manager.update_guild_mission_progress(
                    clan_id=clan_id,
                    mission_type='PVP_WIN',
                    details={'count': 1}
                )
            # =========================================================

        elif vencedor_id == final_opponent_id:
            # Penalidades para o jogador que iniciou
            player_manager.add_pvp_points(player_data, -elo_perdido)
            player_manager.add_pvp_points(opponent_data, elo_ganho) # O oponente ganha pontos
            log_final.append(f"\n❌ Você perdeu <b>-{elo_perdido}</b> pontos de Elo.")
        
        # Salva os dados de ambos os jogadores
        player_manager.save_player_data(user_id, player_data)
        player_manager.save_player_data(final_opponent_id, opponent_data)

        # Formata e exibe o resultado final
        resultado_final = "\n".join(log_final)
        keyboard = [[InlineKeyboardButton("⬅️ Voltar para a Arena", callback_data="pvp_arena")]]
        await query.edit_message_caption(caption=resultado_final, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        
    else:
        await query.edit_message_caption(caption=f"🛡️ Nenhum oponente encontrado no momento. Tente novamente mais tarde.")
        player_manager.add_pvp_entries(player_data, 1) # Devolve a entrada
        player_manager.save_player_data(user_id, player_data)

async def ranking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Função 'Ranking' ainda em construção!", show_alert=True)

async def historico_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Função 'Histórico' ainda em construção!", show_alert=True)


# --- Função Principal do Menu da Arena ---

# Em pvp/pvp_handler.py

async def pvp_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde ao comando /pvp ou a um botão para abrir o menu da arena."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if not player_manager.get_player_data(user_id):
        await context.bot.send_message(chat_id, "Você precisa criar um personagem primeiro com /start.")
        return

    # --- NOVA LÓGICA DO MODIFICADOR DIÁRIO ---
    # Pega o dia da semana atual (Segunda = 0, Terça = 1, ...)
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

# Em pvp/pvp_handler.py

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