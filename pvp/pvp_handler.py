# pvp/pvp_handler.py
# (VERSÃO 5.3: Corrige ID int->ObjectId e usa simular_batalha_completa)

import logging
import random
import datetime
import html

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
from modules import player_manager, file_ids  # game_data não é necessário aqui
from modules.player.core import players_collection  # usamos para obter database

from .pvp_config import ARENA_MODIFIERS, MONTHLY_RANKING_REWARDS
from . import pvp_battle
from . import pvp_utils
from . import tournament_system

from modules.auth_utils import get_current_player_id, requires_login

try:
    from modules.auth_utils import get_current_player_id_async  # type: ignore
except Exception:
    get_current_player_id_async = None  # type: ignore

logger = logging.getLogger(__name__)

# ==============================
# COLLECTION CORRETA: users
# ==============================
users_collection = None
if players_collection is not None:
    try:
        users_collection = players_collection.database["users"]
    except Exception:
        users_collection = None

PVP_PROCURAR_OPONENTE = "pvp_procurar_oponente"
PVP_RANKING = "pvp_ranking"
PVP_HISTORICO = "pvp_historico"


def _safe_str(x) -> str:
    try:
        return str(x)
    except Exception:
        return "<err>"


def _try_objectid(x):
    if isinstance(x, ObjectId):
        return x
    if isinstance(x, str):
        s = x.strip()
        # tenta converter string hex de ObjectId
        try:
            return ObjectId(s)
        except Exception:
            return x  # pode ser string id interno do projeto
    return x


async def _resolve_player_id(update: Update, context: ContextTypes.DEFAULT_TYPE, raw_id):
    """
    Normaliza o ID para o formato que o player_manager aceita (ObjectId/str).
    Se vier int (telegram id), tenta resolver para _id real na collection users.
    """
    # 1) Se já é ObjectId ou str válida, retorna
    if isinstance(raw_id, (ObjectId, str)):
        return _try_objectid(raw_id)

    # 2) Se vier int (Telegram ID), tenta resolver pelo session/context.user_data
    if isinstance(raw_id, int):
        # Sessão comum em bots: salva o id real em user_data
        for key in ("player_id", "user_id", "mongo_id", "account_id"):
            v = context.user_data.get(key) if context and hasattr(context, "user_data") else None
            if isinstance(v, (str, ObjectId)) and v:
                return _try_objectid(v)

        # 3) Resolver via Mongo (users) procurando campos comuns de telegram
        if users_collection is not None:
            tg = raw_id
            queries = [
                {"telegram_id": tg},
                {"telegram_user_id": tg},
                {"telegram_id_owner": tg},
                {"tg_id": tg},
                {"telegramId": tg},
            ]
            for q in queries:
                try:
                    doc = users_collection.find_one(q, {"_id": 1})
                    if doc and doc.get("_id"):
                        return doc["_id"]
                except Exception:
                    pass

        # 4) Último fallback: retorna str(int) para evitar crash,
        # mas isso provavelmente NÃO encontrará o player no seu banco.
        return str(raw_id)

    # 5) Outro tipo inesperado
    return raw_id


async def _get_pid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obtém player_id preferindo sessão/login. Normaliza para ObjectId/str.
    """
    pid = None
    if get_current_player_id_async:
        try:
            pid = await get_current_player_id_async(update, context)
        except Exception:
            pid = None

    if pid is None:
        pid = get_current_player_id(update, context)

    pid = await _resolve_player_id(update, context, pid)

    # log útil
    if isinstance(pid, int):
        logger.warning(f"[PvP] ID ainda é int após resolve: {pid}")

    return pid


async def find_opponents(
    player_elo: int,
    my_id,
    limit: int = 10,
    elo_delta: int = 500,
    allow_zero_points: bool = False,
) -> list:
    """
    Matchmaking na collection users.
    Converte pvp_points para int e filtra docs com character_name.
    """
    if users_collection is None:
        return []

    min_elo = 0 if allow_zero_points else max(0, int(player_elo) - int(elo_delta))
    max_elo = int(player_elo) + int(elo_delta)

    pipeline = [
        {
            "$addFields": {
                "_pvp_points": {
                    "$convert": {
                        "input": "$pvp_points",
                        "to": "int",
                        "onError": 0,
                        "onNull": 0,
                    }
                }
            }
        },
        {
            "$match": {
                "_pvp_points": {"$gte": min_elo, "$lte": max_elo},
                "character_name": {"$exists": True, "$ne": ""},
            }
        },
        {"$sample": {"size": int(limit)}},
    ]

    try:
        candidates = list(users_collection.aggregate(pipeline))
    except Exception as e:
        logger.error(f"Erro matchmaking (users): {e}")
        return []

    my_str = str(my_id)
    return [c for c in candidates if c.get("_id") and str(c.get("_id")) != my_str]


@requires_login
async def procurar_oponente_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🔍 Buscando oponente digno...")

    user_id = await _get_pid(update, context)

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        await query.edit_message_text(
            "❌ Não consegui carregar seu personagem. (ID inválido ou sessão não resolvida)\n"
            f"ID atual: {_safe_str(user_id)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]]),
        )
        return

    # Tickets
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

    # Matchmaking em camadas
    opponents = await find_opponents(my_points, user_id, limit=10, elo_delta=500)
    if not opponents:
        opponents = await find_opponents(my_points, user_id, limit=15, elo_delta=2000)
    if not opponents:
        opponents = await find_opponents(my_points, user_id, limit=25, elo_delta=999999)
    if not opponents:
        opponents = await find_opponents(my_points, user_id, limit=35, elo_delta=999999, allow_zero_points=True)

    # fallback bruto
    if not opponents and users_collection is not None:
        try:
            pipeline_any = [
                {"$match": {"character_name": {"$exists": True, "$ne": ""}}},
                {"$sample": {"size": 60}},
            ]
            opponents = list(users_collection.aggregate(pipeline_any))
            opponents = [o for o in opponents if o.get("_id") and str(o.get("_id")) != str(user_id)]
        except Exception:
            opponents = []

    if not opponents:
        await query.edit_message_text(
            "😔 A Arena está vazia no momento (nenhum personagem válido encontrado).",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]]),
        )
        return

    # Seleção segura: carrega do player_manager para garantir consistência do schema
    random.shuffle(opponents)
    enemy_id = None
    enemy_data = None

    for enemy_doc in opponents:
        _id = enemy_doc.get("_id")
        if not _id or str(_id) == str(user_id):
            continue
        data = await player_manager.get_player_data(_id)
        if data and (data.get("character_name") or data.get("username") or data.get("name")):
            enemy_id = _id
            enemy_data = data
            break

    if not enemy_data or not enemy_id:
        await query.edit_message_text(
            "😔 Não encontrei nenhum personagem válido para lutar agora.\n"
            "Isso indica inconsistência entre a collection e o loader de player_data.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="pvp_arena")]]),
        )
        return

    # Consome Ticket
    player_manager.use_pvp_entry(pdata)
    await player_manager.save_player_data(user_id, pdata)

    # Modificador do dia (para a simulação completa)
    weekday = datetime.datetime.now().weekday()
    day_effect = ARENA_MODIFIERS.get(weekday, {})
    modifier_effect = day_effect.get("effect")

    # ✅ CHAMADA CORRETA: pvp_battle.py tem simular_batalha_completa (async)
    winner_id, log = await pvp_battle.simular_batalha_completa(
        user_id,
        enemy_id,
        modifier_effect=modifier_effect,
        nivel_padrao=None,  # PvP normal
    )

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

    # Atualiza Inimigo (passivo)
    enemy_delta = -15 if is_win else +25
    enemy_points = max(0, int(enemy_data.get("pvp_points", 0)) + enemy_delta)
    enemy_data["pvp_points"] = enemy_points
    await player_manager.save_player_data(enemy_id, enemy_data)

    # Mensagem
    result_text = "🏆 <b>VITÓRIA!</b>" if is_win else "💀 <b>DERROTA...</b>"
    # log pode ser grande; pega últimas linhas
    try:
        full_log = "\n".join(log[-10:])
    except Exception:
        full_log = str(log)

    msg = (
        f"{result_text}\n\n"
        f"🆚 <b>Oponente:</b> {html.escape(enemy_data.get('character_name', 'Desconhecido'))}\n"
        f"📜 <b>Resumo da Luta:</b>\n{full_log}\n\n"
        f"💰 <b>Ouro:</b> +{gold_reward}\n"
        f"📈 <b>Pontos:</b> {elo_delta:+d} (Total: {new_points})"
    )

    kb = [
        [InlineKeyboardButton("⚔️ Lutar Novamente", callback_data=PVP_PROCURAR_OPONENTE)],
        [InlineKeyboardButton("⬅️ Menu Arena", callback_data="pvp_arena")],
    ]
    reply_markup = InlineKeyboardMarkup(kb)

    # Mídia do oponente (classe) com fallback classe_default_media
    enemy_media = pvp_utils.get_player_class_media(enemy_data)
    caption_safe = msg[:1024]

    if enemy_media:
        file_id = enemy_media.get("file_id") or enemy_media.get("id") or enemy_media.get("file")
        media_type = str(enemy_media.get("type", "video")).lower()

        # tenta editar mídia
        try:
            if media_type == "photo":
                input_media = InputMediaPhoto(media=file_id, caption=caption_safe, parse_mode="HTML")
            else:
                input_media = InputMediaVideo(media=file_id, caption=caption_safe, parse_mode="HTML")

            await query.edit_message_media(media=input_media, reply_markup=reply_markup)
            return
        except Exception:
            pass

        # fallback: envia nova msg com mídia
        try:
            if media_type == "photo":
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=file_id,
                    caption=caption_safe,
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )
            else:
                await context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=file_id,
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

    if users_collection is None:
        await query.edit_message_text("❌ Erro: Banco de dados desconectado (users).")
        return

    try:
        pipeline_top = [
            {"$match": {"pvp_points": {"$gt": 0}, "character_name": {"$exists": True, "$ne": ""}}},
            {"$sort": {"pvp_points": -1}},
            {"$limit": 15},
        ]
        top_players = list(users_collection.aggregate(pipeline_top))

        lines = ["🏆 <b>Ranking da Arena de Eldora</b> 🏆\n"]
        if not top_players:
            lines.append("<i>Ainda não há guerreiros classificados nesta temporada.</i>")
        else:
            for i, p in enumerate(top_players, start=1):
                pts = int(p.get("pvp_points", 0))
                name = html.escape(p.get("character_name", p.get("username", "Guerreiro")))
                _, elo_display = pvp_utils.get_player_elo_details(pts)

                if str(p.get("_id")) == str(user_id):
                    lines.append(f"👉 <b>{i}º</b> {elo_display} - {name} <b>({pts})</b>")
                else:
                    lines.append(f"<b>{i}º</b> {elo_display} - {name} <b>({pts})</b>")

        lines.append("\n💎 <b>Recompensas Mensais (Top 5):</b>")
        for rank, reward in sorted(MONTHLY_RANKING_REWARDS.items()):
            lines.append(f"   {rank}º Lugar: {reward} Gemas")

        final_text = "\n".join(lines)

        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Voltar para a Arena", callback_data="pvp_arena")]]
        )

        if query.message.photo or query.message.video:
            await query.edit_message_caption(caption=final_text[:1024], reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        else:
            await query.edit_message_text(text=final_text[:4096], reply_markup=reply_markup, parse_mode=ParseMode.HTML)

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
        # Mostra erro claro quando ID está errado
        if update.callback_query:
            await update.callback_query.edit_message_text(
                f"❌ Não consegui carregar seu personagem.\nID: {_safe_str(user_id)}"
            )
        return

    points = int(pdata.get("pvp_points", 0))
    wins = int(pdata.get("pvp_wins", 0))
    losses = int(pdata.get("pvp_losses", 0))
    elo_name = pvp_utils.get_player_elo(points)

    weekday = datetime.datetime.now().weekday()
    day_effect = ARENA_MODIFIERS.get(weekday, {})
    day_desc = day_effect.get("description", "Sem efeitos hoje.")
    day_title = day_effect.get("name", "Dia Comum")

    media_key = "menu_arena_pvp"
    if update.callback_query and update.callback_query.data == "pvp_arena":
        media_key = "pvp_arena_media"
    media = file_ids.get_file_data(media_key) or file_ids.get_file_data("menu_arena_pvp")

    txt = (
        f"⚔️ <b>ARENA DE ELDORA</b> ⚔️\n\n"
        f"👤 <b>Guerreiro:</b> {html.escape(pdata.get('character_name', ''))}\n"
        f"🏆 <b>Elo:</b> {elo_name} ({points} pts)\n"
        f"📊 <b>Histórico:</b> {wins}V / {losses}D\n\n"
        f"📅 <b>Evento de Hoje:</b> {html.escape(day_title)}\n"
        f"<i>{html.escape(day_desc)}</i>"
    )

    kb = [
        [InlineKeyboardButton("⚔️ PROCURAR OPONENTE", callback_data=PVP_PROCURAR_OPONENTE)],
        [
            InlineKeyboardButton("🏆 Ranking", callback_data=PVP_RANKING),
            InlineKeyboardButton("📜 Histórico", callback_data=PVP_HISTORICO),
        ],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="show_kingdom_menu")],
    ]

    if tournament_system.CURRENT_MATCH_STATE.get("active"):
        kb.insert(0, [InlineKeyboardButton("🏆 TORNEIO (Em andamento)", callback_data="torneio_menu")])

    reply_markup = InlineKeyboardMarkup(kb)

    if update.callback_query:
        query = update.callback_query
        try:
            await query.answer()
        except Exception:
            pass

        if media:
            file_id = media.get("file_id") or media.get("id") or media.get("file")
            media_type = str(media.get("type", "photo")).lower()
            try:
                if media_type == "video":
                    input_media = InputMediaVideo(media=file_id, caption=txt[:1024], parse_mode="HTML")
                else:
                    input_media = InputMediaPhoto(media=file_id, caption=txt[:1024], parse_mode="HTML")
                await query.edit_message_media(media=input_media, reply_markup=reply_markup)
                return
            except Exception:
                # se não der pra editar mídia, edita texto/caption
                try:
                    if query.message and (query.message.photo or query.message.video):
                        await query.edit_message_caption(caption=txt[:1024], reply_markup=reply_markup, parse_mode="HTML")
                    else:
                        await query.edit_message_text(text=txt[:4096], reply_markup=reply_markup, parse_mode="HTML")
                    return
                except Exception:
                    pass

        await query.edit_message_text(text=txt[:4096], reply_markup=reply_markup, parse_mode="HTML")
    else:
        if media:
            file_id = media.get("file_id") or media.get("id") or media.get("file")
            media_type = str(media.get("type", "photo")).lower()
            if media_type == "video":
                await update.message.reply_video(file_id, caption=txt[:1024], reply_markup=reply_markup, parse_mode="HTML")
            else:
                await update.message.reply_photo(file_id, caption=txt[:1024], reply_markup=reply_markup, parse_mode="HTML")
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


# ====== torneio callbacks (mantidos) ======
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
