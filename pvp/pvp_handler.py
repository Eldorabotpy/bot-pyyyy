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
from modules.auth_utils import get_current_player_id, requires_login

logger = logging.getLogger(__name__)

users_collection = None
if players_collection is not None:
    try: users_collection = players_collection.database["users"]
    except: pass

PVP_PROCURAR_OPONENTE = "pvp_procurar_oponente"
PVP_RANKING = "pvp_ranking"
PVP_HISTORICO = "pvp_historico"

async def find_opponents_hybrid(player_elo: int, my_id: str, limit_per_col=5) -> list:
    """
    Busca oponentes em AMBAS as coleções (players e users) e retorna misturado.
    """
    candidates = []
    
    # Faixa de Elo aceitável (+/- 500 pontos)
    min_elo = max(0, player_elo - 500)
    max_elo = player_elo + 500
    
    query = {
        "pvp_points": {"$gte": min_elo, "$lte": max_elo}
    }

    # 1. Busca no Legado (Players)
    if players_collection is not None:
        try:
            pipeline = [{"$match": query}, {"$sample": {"size": limit_per_col}}]
            candidates.extend(list(players_collection.aggregate(pipeline)))
        except Exception as e:
            logger.error(f"Erro matchmaking legacy: {e}")

    # 2. Busca no Novo (Users)
    if users_collection is not None:
        try:
            pipeline = [{"$match": query}, {"$sample": {"size": limit_per_col}}]
            candidates.extend(list(users_collection.aggregate(pipeline)))
        except Exception as e:
            logger.error(f"Erro matchmaking new: {e}")

    # 3. Filtra a si mesmo
    final_list = []
    str_my_id = str(my_id)
    
    for c in candidates:
        c_id = c.get("_id")
        if str(c_id) == str_my_id: continue
        c["_id"] = c_id 
        final_list.append(c)

    return final_list

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

@requires_login
async def procurar_oponente_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🔍 Buscando oponente digno...")
    
    user_id = get_current_player_id(update, context)
    pdata = await player_manager.get_player_data(user_id)
    
    # Verifica Tickets
    tickets = player_manager.get_pvp_entries(pdata)
    if tickets <= 0:
        await query.edit_message_text(
            "🚫 <b>Sem Tickets de Arena!</b>\n\n"
            "Você usou todas as suas 5 lutas diárias.\n"
            "Volte amanhã ou use um item de recarga.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]])
        , parse_mode="HTML")
        return

    # Matchmaking
    my_points = pdata.get("pvp_points", 0)
    opponents = await find_opponents_hybrid(my_points, user_id)
    
    if not opponents:
        # Se não achou ninguém perto, pega qualquer um aleatório
        opponents = await find_opponents_hybrid(my_points, user_id, limit_per_col=10) # range maior implícito na lógica se quiser, ou só retry
        
        if not opponents:
            await query.edit_message_text("😔 A Arena está vazia no momento. Tente mais tarde.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]]))
            return

    enemy_doc = random.choice(opponents)
    enemy_id = enemy_doc["_id"]
    
    # Carrega dados completos do inimigo via player_manager (garante cálculo de stats)
    # Note que enemy_id pode ser int ou ObjectId, o manager lida com isso.
    enemy_data = await player_manager.get_player_data(enemy_id)
    
    if not enemy_data:
        await query.edit_message_text("Erro ao carregar oponente. Tente novamente.")
        return

    # Consome Ticket
    player_manager.use_pvp_entry(pdata)
    await player_manager.save_player_data(user_id, pdata)

    # Executa Batalha
    winner_id, log = pvp_battle.simular_batalha_pvp(pdata, enemy_data)
    
    # Processa Resultado
    is_win = (str(winner_id) == str(user_id))
    
    # Cálculos de recompensa...
    elo_delta = 25 if is_win else -15
    gold_reward = 100 if is_win else 10
    
    # Aplica no Jogador
    pdata = await player_manager.get_player_data(user_id) # Recarrega pra garantir
    new_points = max(0, pdata.get("pvp_points", 0) + elo_delta)
    pdata["pvp_points"] = new_points
    
    if is_win: 
        pdata["pvp_wins"] = pdata.get("pvp_wins", 0) + 1
        player_manager.add_gold(pdata, gold_reward)
    else:
        pdata["pvp_losses"] = pdata.get("pvp_losses", 0) + 1
        player_manager.add_gold(pdata, gold_reward)
        
    await player_manager.save_player_data(user_id, pdata)
    
    # Aplica no Inimigo (Passivo)
    # Inimigos só perdem/ganham pontos, não gold/wins passivas (decisão de design comum)
    enemy_points = max(0, enemy_data.get("pvp_points", 0) - (15 if is_win else -25))
    enemy_data["pvp_points"] = enemy_points
    await player_manager.save_player_data(enemy_id, enemy_data)

    # Renderiza Log
    result_text = "🏆 <b>VITÓRIA!</b>" if is_win else "💀 <b>DERROTA...</b>"
    full_log = "\n".join(log[-10:]) # Últimas 10 linhas para não floodar
    
    msg = (
        f"{result_text}\n\n"
        f"🆚 <b>Oponente:</b> {enemy_data.get('character_name')}\n"
        f"📜 <b>Resumo da Luta:</b>\n{full_log}\n\n"
        f"💰 <b>Ouro:</b> +{gold_reward}\n"
        f"📈 <b>Pontos:</b> {elo_delta:+d} (Total: {new_points})"
    )
    
    kb = [[InlineKeyboardButton("⚔️ Lutar Novamente", callback_data=PVP_PROCURAR_OPONENTE)],
          [InlineKeyboardButton("⬅️ Menu Arena", callback_data="pvp_arena")]]
          
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")


@requires_login
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

@requires_login
async def historico_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Função 'Histórico' ainda em construção!", show_alert=True)

@requires_login
async def pvp_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_current_player_id(update, context)
    pdata = await player_manager.get_player_data(user_id)
    
    if not pdata: return

    # Dados do Jogador
    points = pdata.get("pvp_points", 0)
    wins = pdata.get("pvp_wins", 0)
    losses = pdata.get("pvp_losses", 0)
    elo_name = pvp_utils.get_player_elo(points)
    
    # Efeito do Dia
    weekday = datetime.datetime.now().weekday()
    day_effect = ARENA_MODIFIERS.get(weekday, {})
    day_desc = day_effect.get("description", "Sem efeitos hoje.")
    day_title = day_effect.get("name", "Dia Comum")

    # Mídia
    media = file_ids.get_file_data("menu_arena_pvp")
    
    txt = (
        f"⚔️ <b>ARENA DE ELDORA</b> ⚔️\n\n"
        f"👤 <b>Guerreiro:</b> {pdata.get('character_name')}\n"
        f"🏆 <b>Elo:</b> {elo_name} ({points} pts)\n"
        f"📊 <b>Histórico:</b> {wins}V / {losses}D\n\n"
        f"📅 <b>Evento de Hoje:</b> {day_title}\n"
        f"<i>{day_desc}</i>"
    )

    kb = [
        [InlineKeyboardButton("⚔️ PROCURAR OPONENTE", callback_data=PVP_PROCURAR_OPONENTE)],
        [InlineKeyboardButton("🏆 Ranking", callback_data=PVP_RANKING), 
         InlineKeyboardButton("📜 Histórico", callback_data=PVP_HISTORICO)],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="show_kingdom_menu")]
    ]

    # Torneio Ativo?
    if tournament_system.CURRENT_MATCH_STATE["active"]:
        kb.insert(0, [InlineKeyboardButton("🏆 TORNEIO (Em andamento)", callback_data="torneio_menu")])

    if update.callback_query:
        await update.callback_query.answer()
        # Lógica de envio de mídia segura (igual ao seu padrão)
        if media:
            try:
                if media["type"] == "video":
                    await update.callback_query.edit_message_caption(caption=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
                else:
                    await update.callback_query.edit_message_text(text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
            except:
                # Fallback se não der pra editar
                await context.bot.send_message(update.effective_chat.id, txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        else:
            await update.callback_query.edit_message_text(text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    else:
        await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

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