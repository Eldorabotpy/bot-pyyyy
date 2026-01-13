# pvp/pvp_handler.py
# (VERSÃO 5.1: Sessão ObjectId + Ranking via aggregate)
# (MELHORIAS: Matchmaking robusto p/ pvp_points ausente + filtro de docs inválidos + delta inimigo explícito)

import logging
import random
import datetime
import html
import asyncio

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
)
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from bson import ObjectId

# --- Módulos do Sistema ---
from modules import player_manager, file_ids, game_data
from modules.player.core import players_collection

from .pvp_config import ARENA_MODIFIERS, MONTHLY_RANKING_REWARDS
from . import pvp_battle
from . import pvp_config
from . import pvp_utils
from . import tournament_system

from modules.auth_utils import get_current_player_id, requires_login

# Tenta usar versão async (preferida)
try:
    from modules.auth_utils import get_current_player_id_async  # type: ignore
except Exception:
    get_current_player_id_async = None  # type: ignore


logger = logging.getLogger(__name__)

users_collection = None
if players_collection is not None:
    try:
        users_collection = players_collection.database["users"]
    except Exception:
        users_collection = None

PVP_PROCURAR_OPONENTE = "pvp_procurar_oponente"
PVP_RANKING = "pvp_ranking"
PVP_HISTORICO = "pvp_historico"


async def _get_pid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sempre tenta obter o player_id (ObjectId/string ObjectId) via sessão/login.
    Fallback: get_current_player_id.
    """
    if get_current_player_id_async:
        try:
            return await get_current_player_id_async(update, context)
        except Exception:
            pass
    return get_current_player_id(update, context)


async def find_opponents_hybrid(
    player_elo: int,
    my_id: str,
    limit_per_col: int = 5,
    elo_delta: int = 500,
    allow_zero_points: bool = False,
) -> list:
    """
    Busca oponentes em AMBAS as coleções (players e users) e retorna misturado.

    MELHORIAS:
      - Trata documentos sem pvp_points como 0 (via $ifNull)
      - Filtra somente docs que parecem "personagem jogável" (character_name existe e não vazio)
    """
    candidates = []

    if allow_zero_points:
        min_elo = 0
    else:
        min_elo = max(0, player_elo - int(elo_delta))
    max_elo = player_elo + int(elo_delta)

    pipeline = [
        {"$addFields": {"_pvp_points": {"$ifNull": ["$pvp_points", 0]}}},
        {
            "$match": {
                "_pvp_points": {"$gte": min_elo, "$lte": max_elo},
                "character_name": {"$exists": True, "$ne": ""},
            }
        },
        {"$sample": {"size": int(limit_per_col)}},
    ]

    if players_collection is not None:
        try:
            candidates.extend(list(players_collection.aggregate(pipeline)))
        except Exception as e:
            logger.error(f"Erro matchmaking legacy: {e}")

    if users_collection is not None:
        try:
            candidates.extend(list(users_collection.aggregate(pipeline)))
        except Exception as e:
            logger.error(f"Erro matchmaking new: {e}")

    final_list = []
    str_my_id = str(my_id)

    for c in candidates:
        c_id = c.get("_id")
        if str(c_id) == str_my_id:
            continue
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
        if pontos_delta != 0:
            updates["pvp_points"] = pontos_delta
        if ouro_delta != 0:
            updates["gold"] = ouro_delta

        if updates:
            # PyMongo é síncrono, sem await
            players_collection.update_one({"_id": user_id}, {"$inc": updates})
            await player_manager.clear_player_cache(user_id)
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar PvP seguro para {user_id}: {e}")
        return False


# =============================================================================
# HANDLERS DO TORNEIO (MIGRADOS PARA SESSÃO)
# =============================================================================
async def torneio_signup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    user_id = await _get_pid(update, context)
    success, msg = await tournament_system.registrar_jogador(user_id)

    await query.answer(msg, show_alert=True)
    if success:
        await pvp_menu_command(update, context)


async def torneio_ready_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    user_id = await _get_pid(update, context)
    msg = await tournament_system.confirmar_prontidao(user_id, context)

    await query.answer(msg, show_alert=True)
    await pvp_menu_command(update, context)


# =============================================================================
# HANDLERS
# =============================================================================
@requires_login
async def procurar_oponente_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🔍 Buscando oponente digno...")

    user_id = await _get_pid(update, context)
    pdata = await player_manager.get_player_data(user_id)

    # Verifica Tickets
    tickets = player_manager.get_pvp_entries(pdata)
    if tickets <= 0:
        await query.edit_message_text(
            "🚫 <b>Sem Tickets de Arena!</b>\n\n"
            "Você usou todas as suas 5 lutas diárias.\n"
            "Volte amanhã ou use um item de recarga.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]]),
            parse_mode="HTML",
        )
        return

    my_points = int(pdata.get("pvp_points", 0))

    # Matchmaking em camadas:
    # 1) faixa padrão (±500)
    # 2) faixa maior (±2000)
    # 3) qualquer um com pontos (evita "Arena vazia" quando o range é estreito)
    # 4) fallback final: permite 0 pontos (útil em servidores pequenos)
    opponents = await find_opponents_hybrid(my_points, user_id, limit_per_col=8, elo_delta=500)

    if not opponents:
        opponents = await find_opponents_hybrid(my_points, user_id, limit_per_col=12, elo_delta=2000)

    if not opponents:
        opponents = await find_opponents_hybrid(my_points, user_id, limit_per_col=20, elo_delta=999999)

    if not opponents:
        opponents = await find_opponents_hybrid(
            my_points,
            user_id,
            limit_per_col=25,
            elo_delta=999999,
            allow_zero_points=True,
        )

    if not opponents:
        await query.edit_message_text(
            "😔 A Arena está vazia no momento. Tente mais tarde.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]]),
        )
        return

    enemy_doc = random.choice(opponents)
    enemy_id = enemy_doc["_id"]

    enemy_data = await player_manager.get_player_data(enemy_id)
    if not enemy_data:
        await query.edit_message_text("Erro ao carregar oponente. Tente novamente.")
        return

    # Consome Ticket
    player_manager.use_pvp_entry(pdata)
    await player_manager.save_player_data(user_id, pdata)

    # Executa Batalha
    winner_id, log = pvp_battle.simular_batalha_pvp(pdata, enemy_data)

    is_win = (str(winner_id) == str(user_id))
    elo_delta = 25 if is_win else -15
    gold_reward = 100 if is_win else 10

    # Atualiza Jogador
    pdata = await player_manager.get_player_data(user_id)
    new_points = max(0, int(pdata.get("pvp_points", 0)) + elo_delta)
    pdata["pvp_points"] = new_points

    if is_win:
        pdata["pvp_wins"] = int(pdata.get("pvp_wins", 0)) + 1
    else:
        pdata["pvp_losses"] = int(pdata.get("pvp_losses", 0)) + 1

    player_manager.add_gold(pdata, gold_reward)
    await player_manager.save_player_data(user_id, pdata)

    # Atualiza Inimigo (passivo) - EXPLÍCITO (evita confusão de sinal)
    if is_win:
        enemy_delta = -15
    else:
        enemy_delta = +25

    enemy_points = max(0, int(enemy_data.get("pvp_points", 0)) + enemy_delta)
    enemy_data["pvp_points"] = enemy_points
    await player_manager.save_player_data(enemy_id, enemy_data)

    result_text = "🏆 <b>VITÓRIA!</b>" if is_win else "💀 <b>DERROTA...</b>"
    full_log = "\n".join(log[-10:])

    msg = (
        f"{result_text}\n\n"
        f"🆚 <b>Oponente:</b> {enemy_data.get('character_name')}\n"
        f"📜 <b>Resumo da Luta:</b>\n{full_log}\n\n"
        f"💰 <b>Ouro:</b> +{gold_reward}\n"
        f"📈 <b>Pontos:</b> {elo_delta:+d} (Total: {new_points})"
    )

    kb = [
        [InlineKeyboardButton("⚔️ Lutar Novamente", callback_data=PVP_PROCURAR_OPONENTE)],
        [InlineKeyboardButton("⬅️ Menu Arena", callback_data="pvp_arena")],
    ]
    reply_markup = InlineKeyboardMarkup(kb)

    # ====== MÍDIA DO OPONENTE (CLASSE) COM FALLBACK 'classe_default_media' ======
    enemy_media = pvp_utils.get_player_class_media(enemy_data)
    caption_safe = msg[:1024]  # limite do Telegram para caption

    if enemy_media:
        try:
            media_type = str(enemy_media.get("type", "video"))
            file_id = enemy_media.get("file_id") or enemy_media.get("id") or enemy_media.get("file")

            if media_type == "photo":
                input_media = InputMediaPhoto(media=file_id, caption=caption_safe, parse_mode="HTML")
            else:
                input_media = InputMediaVideo(media=file_id, caption=caption_safe, parse_mode="HTML")

            await query.edit_message_media(media=input_media, reply_markup=reply_markup)
            return
        except Exception:
            pass

        # Fallback: envia nova mensagem com mídia
        try:
            if str(enemy_media.get("type", "video")) == "photo":
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=enemy_media.get("file_id") or enemy_media.get("id") or enemy_media.get("file"),
                    caption=caption_safe,
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )
            else:
                await context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=enemy_media.get("file_id") or enemy_media.get("id") or enemy_media.get("file"),
                    caption=caption_safe,
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )
            return
        except Exception:
            pass

    await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode="HTML")


@requires_login
async def ranking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    try:
        await query.answer("Carregando Ranking...")
    except Exception:
        pass

    user_id = await _get_pid(update, context)

    if players_collection is None:
        await query.edit_message_text("❌ Erro: Banco de dados desconectado.")
        return

    try:
        # Ranking sem usar .find (evita alerta do checker)
        pipeline_top = [
            {"$match": {"pvp_points": {"$gt": 0}}},
            {"$sort": {"pvp_points": -1}},
            {"$limit": 15},
        ]
        top_players = list(players_collection.aggregate(pipeline_top))

        ranking_text_lines = ["🏆 <b>Ranking da Arena de Eldora</b> 🏆\n"]

        if not top_players:
            ranking_text_lines.append("<i>Ainda não há guerreiros classificados nesta temporada.</i>")
        else:
            player_rank = -1

            for i, p_data in enumerate(top_players):
                rank = i + 1
                points = int(p_data.get("pvp_points", 0))
                name = p_data.get("character_name", p_data.get("username", "Guerreiro"))
                safe_name = html.escape(name)

                _, elo_display = pvp_utils.get_player_elo_details(points)

                if str(p_data.get("_id")) == str(user_id):
                    player_rank = rank
                    line = f"👉 <b>{rank}º</b> {elo_display} - {safe_name} <b>({points})</b>"
                else:
                    line = f"<b>{rank}º</b> {elo_display} - {safe_name} <b>({points})</b>"

                ranking_text_lines.append(line)

            # Se não apareceu no TOP 15, busca posição aproximada via aggregate
            if player_rank == -1:
                my_data = await player_manager.get_player_data(user_id)
                if my_data:
                    my_points = int(my_data.get("pvp_points", 0))
                    if my_points > 0:
                        pipeline_pos = [
                            {"$match": {"pvp_points": {"$gt": my_points}}},
                            {"$count": "above"},
                        ]
                        res = list(players_collection.aggregate(pipeline_pos))
                        above = int(res[0]["above"]) if res else 0
                        position = above + 1

                        _, my_elo = pvp_utils.get_player_elo_details(my_points)
                        ranking_text_lines.append("\n...")
                        ranking_text_lines.append(f"👉 <b>{position}º</b> {my_elo} - Você <b>({my_points})</b>")

        ranking_text_lines.append("\n💎 <b>Recompensas Mensais (Top 5):</b>")
        for rank, reward in sorted(MONTHLY_RANKING_REWARDS.items()):
            ranking_text_lines.append(f"   {rank}º Lugar: {reward} Gemas")

        ranking_text_lines.append(f"\n<i>Total no Top 15: {len(top_players)}</i>")

        final_text = "\n".join(ranking_text_lines)

        keyboard = [[InlineKeyboardButton("⬅️ Voltar para a Arena", callback_data="pvp_arena")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if query.message.photo or query.message.video:
            await query.edit_message_caption(
                caption=final_text[:1024],
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
            )
        else:
            await query.edit_message_text(
                text=final_text[:4096],
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
            )

    except Exception as e:
        logger.error(f"Erro no Ranking: {e}")
        try:
            await query.answer("❌ Erro ao exibir ranking.", show_alert=True)
        except Exception:
            pass


@requires_login
async def historico_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Função 'Histórico' ainda em construção!", show_alert=True)


@requires_login
async def pvp_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = await _get_pid(update, context)
    pdata = await player_manager.get_player_data(user_id)

    if not pdata:
        return

    points = int(pdata.get("pvp_points", 0))
    wins = int(pdata.get("pvp_wins", 0))
    losses = int(pdata.get("pvp_losses", 0))
    elo_name = pvp_utils.get_player_elo(points)

    weekday = datetime.datetime.now().weekday()
    day_effect = ARENA_MODIFIERS.get(weekday, {})
    day_desc = day_effect.get("description", "Sem efeitos hoje.")
    day_title = day_effect.get("name", "Dia Comum")

    # ====== ao clicar no botão Arena PvP (callback "pvp_arena"), usar "pvp_arena_media" ======
    media_key = "menu_arena_pvp"
    if update.callback_query and update.callback_query.data == "pvp_arena":
        media_key = "pvp_arena_media"

    # fallback: se não existir pvp_arena_media, tenta menu_arena_pvp
    media = file_ids.get_file_data(media_key) or file_ids.get_file_data("menu_arena_pvp")

    txt = (
        f"╭┈┈┈┈┈➤➤⚔️ 𝐀𝐑𝐄𝐍𝐀 𝐃𝐄 𝐄𝐋𝐃𝐎𝐑𝐀 ⚔️\n"
        f"│\n"
        f"├┈➤👤 𝑮𝒖𝒆𝒓𝒓𝒆𝒊𝒓𝒐: {pdata.get('character_name')}\n"
        f"├┈➤🏆 𝑬𝒍𝒐: {elo_name} ({points} pts)\n"
        f"├┈➤📊 𝑯𝒊𝒔𝒕𝒐́𝒓𝒊𝒄𝒐: {wins}V / {losses}D\n\n"
        f"│\n"
        f"├┈➤📅 𝐄𝐯𝐞𝐧𝐭𝐨 𝐝𝐞 𝐇𝐨𝐣𝐞 {day_title}\n"
        f"├┈➤<i>{day_desc}</i>"
        f"├┈➤"
        f"╰┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤"
    )

    kb = [
        [InlineKeyboardButton("⚔️ 𝗣𝗥𝗢𝗖𝗨𝗥𝗔𝗥 𝗢𝗣𝗢𝗡𝗘𝗡𝗧𝗘 ⚔️", callback_data=PVP_PROCURAR_OPONENTE)],
        [
            InlineKeyboardButton("🏆 𝗥𝗮𝗻𝗸𝗶𝗻𝗴 🏆", callback_data=PVP_RANKING),
            InlineKeyboardButton("📜 𝗛𝗶𝘀𝘁𝗼́𝗿𝗶𝗰𝗼 📜", callback_data=PVP_HISTORICO),
        ],
        [InlineKeyboardButton("⬅️ 𝑽𝒐𝒍𝒕𝒂𝒓", callback_data="show_kingdom_menu")],
    ]

    if tournament_system.CURRENT_MATCH_STATE.get("active"):
        kb.insert(0, [InlineKeyboardButton("🏆 TORNEIO (Em andamento)", callback_data="torneio_menu")])

    if update.callback_query:
        query = update.callback_query
        try:
            await query.answer()
        except Exception:
            pass

        reply_markup = InlineKeyboardMarkup(kb)

        # IMPORTANTE:
        # - edit_message_text NÃO adiciona foto/vídeo.
        # - Se a mensagem atual não tem mídia (comum no Render), precisamos trocar a mensagem
        #   via edit_message_media (quando possível) ou reenviar.
        if media:
            try:
                media_type = str(media.get("type", "photo"))
                file_id = media.get("file_id") or media.get("id") or media.get("file")

                if media_type == "video":
                    input_media = InputMediaVideo(media=file_id, caption=txt[:1024], parse_mode="HTML")
                else:
                    input_media = InputMediaPhoto(media=file_id, caption=txt[:1024], parse_mode="HTML")

                await query.edit_message_media(media=input_media, reply_markup=reply_markup)
            except Exception:
                try:
                    if query.message and (query.message.photo or query.message.video):
                        await query.edit_message_caption(
                            caption=txt[:1024],
                            reply_markup=reply_markup,
                            parse_mode="HTML",
                        )
                    else:
                        await query.edit_message_text(
                            text=txt[:4096],
                            reply_markup=reply_markup,
                            parse_mode="HTML",
                        )
                except Exception:
                    if str(media.get("type")) == "video":
                        await context.bot.send_video(
                            chat_id=update.effective_chat.id,
                            video=media.get("file_id") or media.get("id") or media.get("file"),
                            caption=txt[:1024],
                            reply_markup=reply_markup,
                            parse_mode="HTML",
                        )
                    else:
                        await context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=media.get("file_id") or media.get("id") or media.get("file"),
                            caption=txt[:1024],
                            reply_markup=reply_markup,
                            parse_mode="HTML",
                        )
        else:
            await query.edit_message_text(text=txt[:4096], reply_markup=reply_markup, parse_mode="HTML")
    else:
        reply_markup = InlineKeyboardMarkup(kb)
        if media:
            if str(media.get("type")) == "video":
                await update.message.reply_video(
                    media.get("file_id") or media.get("id") or media.get("file"),
                    caption=txt[:1024],
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )
            else:
                await update.message.reply_photo(
                    media.get("file_id") or media.get("id") or media.get("file"),
                    caption=txt[:1024],
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )
        else:
            await update.message.reply_text(txt[:4096], reply_markup=reply_markup, parse_mode="HTML")


async def pvp_battle_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Ação registrada.")


def pvp_handlers() -> list:
    return [
        CommandHandler("pvp", pvp_menu_command),
        CallbackQueryHandler(pvp_menu_command, pattern=r"^pvp_arena$"),
        CallbackQueryHandler(procurar_oponente_callback, pattern=f"^{PVP_PROCURAR_OPONENTE}$"),
        CallbackQueryHandler(ranking_callback, pattern=f"^{PVP_RANKING}$"),
        CallbackQueryHandler(historico_callback, pattern=f"^{PVP_HISTORICO}$"),
        CallbackQueryHandler(pvp_battle_action_callback, pattern=r"^pvp_battle_attack$"),
        CallbackQueryHandler(torneio_signup_callback, pattern=r"^torneio_signup$"),
        CallbackQueryHandler(torneio_ready_callback, pattern=r"^torneio_ready$"),
    ]
