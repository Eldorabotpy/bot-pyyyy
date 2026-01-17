# handlers/jobs.py

from __future__ import annotations

import logging
import datetime
import asyncio
import certifi
from zoneinfo import ZoneInfo
from typing import Any, List, Dict, Optional
from config import ADMIN_ID

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from telegram.error import BadRequest, Forbidden

from pymongo import MongoClient
from bson import ObjectId

from modules import game_data, player_manager
from modules.player.premium import PremiumManager
from modules.auth_utils import get_current_player_id
from modules.player_manager import save_player_data

from config import JOB_TIMEZONE, ANNOUNCEMENT_CHAT_ID, ANNOUNCEMENT_THREAD_ID, EVENT_TIMES

from pvp.pvp_scheduler import executar_reset_pvp
from modules.world_boss.engine import (
    world_boss_manager,
    broadcast_boss_announcement,
    distribute_loot_and_announce
)

try:
    from kingdom_defense.engine import event_manager
except ImportError:
    event_manager = None

from pvp.pvp_config import MONTHLY_RANKING_REWARDS

# --- NOVO: Guerra de Clãs (sistema único) ---
from modules.game_data import regions as game_data_regions
from modules.guild_war.war_event import (
    start_week_prep,
    force_active,
    finalize_campaign,
    tick_weekly_campaign,
    WarScoreRepo,
)
from modules.guild_war.campaign import ensure_weekly_campaign
from modules.guild_war.region import get_region_meta

logger = logging.getLogger(__name__)

# ==============================================================================
# CONFIGURAÇÃO DO MONGODB
# ==============================================================================
MONGO_STR = "mongodb+srv://eldora-cluster:pb060987@cluster0.4iqgjaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
players_col = None
users_col = None
try:
    client = MongoClient(MONGO_STR, tlsCAFile=certifi.where())
    db = client["eldora_db"]
    players_col = db["players"]
    users_col = db["users"]
    logger.info("✅ [JOBS] Conexão MongoDB Híbrida OK.")
except Exception as e:
    logger.critical(f"❌ [JOBS] FALHA CRÍTICA NA CONEXÃO MONGODB: {e}")
    players_col = None
    users_col = None


async def safe_send_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int | str, text: str):
    """Envia mensagem de forma segura (ignora usuário deletado ou bloqueio)."""
    try:
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
        await asyncio.sleep(0.05)
    except (BadRequest, Forbidden):
        pass
    except Exception as e:
        logger.warning(f"Erro ao notificar {chat_id}: {e}")


def get_col_and_id(user_id):
    """
    Retorna a coleção correta e o formato do ID para query.
    BLINDADA contra erro de boolean do PyMongo.
    """
    if isinstance(user_id, ObjectId):
        if users_col is not None:
            return users_col, user_id
        return None, None

    if isinstance(user_id, int):
        if players_col is not None:
            return players_col, user_id
        return None, None

    elif isinstance(user_id, str):
        if users_col is not None and ObjectId.is_valid(user_id):
            return users_col, ObjectId(user_id)
        if user_id.isdigit():
            if players_col is not None:
                return players_col, int(user_id)

    return None, None

def _today_str(tzname: str = JOB_TIMEZONE) -> str:
    try:
        tz = ZoneInfo(tzname)
        now = datetime.datetime.now(tz)
    except Exception:
        now = datetime.datetime.now()
    return now.date().isoformat()



# ==============================================================================
# ✅ NOVO SISTEMA: RESET DIÁRIO (MEIA-NOITE) PARA NÃO ACUMULAR
# ==============================================================================
DAILY_EVENT_ITEMS = {
    "ticket_arena": 10,
    "ticket_defesa_reino": 4,
    "cristal_de_abertura": 4,
}

async def daily_reset_event_entries_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Meia-noite:
      - Zera os itens diários (para NÃO acumular).
      - Remove o flag de claim do dia (libera para o novo dia).
    Aplica em users_col e players_col (híbrido).
    """
    update = {
        "$set": {
            "inventory.ticket_arena": 0,
            "inventory.ticket_defesa_reino": 0,
            "inventory.cristal_de_abertura": 0,
        },
        "$unset": {
            "daily_claims.event_entries_claim_date": "",
            "daily_awards.last_arena_ticket_date": "",
            "daily_awards.last_kingdom_ticket_date": "",
            "daily_awards.last_crystal_date": "",
            "last_pvp_entry_reset": "",
        }
    }

    try:
        if users_col is not None:
            users_col.update_many({}, update)
        if players_col is not None:
            players_col.update_many({}, update)
        logger.info("[JOB] Reset diário de entradas/eventos executado (sem acúmulo).")
    except Exception as e:
        logger.error(f"[JOB] Erro no reset diário de entradas/eventos: {e}")

# ==============================================================================
# ⚔️ GUERRA DE CLÃS — SISTEMA ÚNICO (guild_war)
# ==============================================================================

async def guild_war_finalize_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Rodar no domingo à noite (ex.: 23:55 no timezone do JOB_TIMEZONE).
    - Finaliza a campanha semanal (ENDED + ranking top5)
    - Opcionalmente anuncia no grupo (se ANNOUNCEMENT_CHAT_ID estiver setado)
    """
    try:
        # garante que a fase do dia também foi aplicada (boa prática)
        await tick_weekly_campaign(game_data_regions_module=game_data_regions)

        campaign = await finalize_campaign(game_data_regions_module=game_data_regions, top_n=5)
        cid = str(campaign.get("campaign_id") or "")
        target_region_id = str(campaign.get("target_region_id") or "")
        region_meta = get_region_meta(game_data_regions, target_region_id) if target_region_id else {}

        result = campaign.get("result") or {}
        winner = result.get("winner")
        top = result.get("top") or []

        if ANNOUNCEMENT_CHAT_ID:
            lines: List[str] = []
            for i, row in enumerate(top, start=1):
                lines.append(
                    f"{i}. <code>{row.get('clan_id')}</code> — "
                    f"<b>{row.get('total', 0)}</b> (PvE {row.get('pve', 0)} | PvP {row.get('pvp', 0)})"
                )
            ranking_txt = "\n".join(lines) if lines else "<i>Ninguém pontuou nesta rodada.</i>"

            winner_txt = (
                f"🏆 Vencedor: <code>{winner.get('clan_id')}</code> — <b>{winner.get('total')}</b>"
                if winner else "🏆 Vencedor: <i>sem vencedor</i>"
            )

            msg = (
                "⚔️ <b>Guerra de Clãs — Encerrada!</b>\n\n"
                f"Rodada: <b>{cid}</b>\n"
                f"{region_meta.get('emoji','📍')} Região Alvo: <b>{region_meta.get('display_name', target_region_id)}</b>\n\n"
                f"{winner_txt}\n\n"
                f"<b>Top 5:</b>\n{ranking_txt}"
            )

            try:
                await context.bot.send_message(
                    chat_id=ANNOUNCEMENT_CHAT_ID,
                    message_thread_id=ANNOUNCEMENT_THREAD_ID,
                    text=msg,
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"[GUILD_WAR] Falha ao anunciar ranking: {e}")

        logger.info(f"[GUILD_WAR] Finalização concluída (campaign={cid}).")

    except Exception as e:
        logger.error(f"[GUILD_WAR] guild_war_finalize_job falhou: {e}")

def _is_admin_id(user_id: Any) -> bool:
    return str(user_id) == str(ADMIN_ID)

async def _admin_reply(update: Update, text: str):
    if update.effective_message:
        await update.effective_message.reply_text(text, parse_mode="HTML")

async def cmd_war_week_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = get_current_player_id(update, context)
    if not _is_admin_id(uid):
        return
    campaign = await start_week_prep(game_data_regions_module=game_data_regions)
    cid = str(campaign.get("campaign_id"))
    target = str(campaign.get("target_region_id") or "")
    meta = get_region_meta(game_data_regions, target) if target else {}
    await _admin_reply(
        update,
        (
            "✅ <b>Semana iniciada (PREP)</b>\n\n"
            f"Rodada: <b>{cid}</b>\n"
            f"{meta.get('emoji','📍')} Alvo: <b>{meta.get('display_name', target)}</b>\n"
            "Inscrição: <b>ABERTA</b>\n"
            "Placar: <b>ZERADO</b>"
        )
    )

async def cmd_war_force_active(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = get_current_player_id(update, context)
    if not _is_admin_id(uid):
        return
    campaign = await force_active(game_data_regions_module=game_data_regions)
    cid = str(campaign.get("campaign_id"))
    await _admin_reply(update, f"✅ <b>ACTIVE forçado</b>\nRodada: <b>{cid}</b>\nInscrição: <b>FECHADA</b>")


async def cmd_war_finalize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = get_current_player_id(update, context)
    if not _is_admin_id(uid):
        return
    campaign = await finalize_campaign(game_data_regions_module=game_data_regions, top_n=5)
    cid = str(campaign.get("campaign_id"))
    result = campaign.get("result") or {}
    winner = result.get("winner")
    await _admin_reply(
        update,
        (
            f"✅ <b>Campanha finalizada</b>\nRodada: <b>{cid}</b>\n"
            f"Vencedor: <code>{(winner or {}).get('clan_id','—')}</code>"
        )
    )

async def cmd_war_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = get_current_player_id(update, context)
    if not _is_admin_id(uid):
        return

    campaign = await ensure_weekly_campaign(game_data_regions_module=game_data_regions)
    cid = str(campaign.get("campaign_id") or "")
    phase = str(campaign.get("phase") or "PREP")
    signup_open = bool(campaign.get("signup_open", True))
    target = str(campaign.get("target_region_id") or "")
    meta = get_region_meta(game_data_regions, target) if target else {}

    # mostra top 5 atual (debug)
    top = await WarScoreRepo().top_clans(cid, limit=5)
    lines = []
    for i, row in enumerate(top, start=1):
        lines.append(
            f"{i}. <code>{row.get('clan_id')}</code> — <b>{row.get('total', 0)}</b> "
            f"(PvE {row.get('pve', 0)} | PvP {row.get('pvp', 0)})"
        )
    ranking_txt = "\n".join(lines) if lines else "<i>Sem pontuação ainda.</i>"

    await _admin_reply(
        update,
        (
            "📌 <b>Status Guerra de Clãs</b>\n\n"
            f"Rodada: <b>{cid}</b>\n"
            f"Fase: <b>{phase}</b>\n"
            f"Inscrição: <b>{'ABERTA' if signup_open else 'FECHADA'}</b>\n"
            f"{meta.get('emoji','📍')} Alvo: <b>{meta.get('display_name', target)}</b>\n\n"
            f"<b>Top 5 (parcial):</b>\n{ranking_txt}"
        )
    )
# ==============================================================================
# 🛡️ KINGDOM DEFENSE (EVENTO) — SEM DAR TICKETS AUTOMATICAMENTE
# ==============================================================================
async def start_kingdom_defense_event(context: ContextTypes.DEFAULT_TYPE):
    if not event_manager:
        return

    job_data = context.job.data or {}
    duration_minutes = job_data.get("event_duration_minutes", 30)
    location_name = "🏰 Portões do Reino"

    try:
        result = await event_manager.start_event()
        if result and "error" in result:
            logger.warning(f"[KD] Evento já ativo ou erro: {result['error']}")
            return

        # ❌ Removido: não distribui ticket automaticamente.
        # O jogador pega no menu Eventos (claim diário).

        group_msg = (
            "🔥 <b>INVASÃO EM ANDAMENTO!</b> 🔥\n\n"
            "‼️ <b>ATENÇÃO HERÓIS DE ELDORA!</b>\n"
            f"Monstros estão atacando os <b>{location_name}</b>!\n\n"
            f"⏳ <b>Tempo Restante:</b> {duration_minutes} minutos\n"
            "🎟️ <i>Use seus tickets diários no menu 'Eventos'.</i>\n"
            "👉 <b>CORRAM PARA O MENU 'DEFESA DO REINO'!</b>"
        )

        if ANNOUNCEMENT_CHAT_ID:
            try:
                thread_id = ANNOUNCEMENT_THREAD_ID if ANNOUNCEMENT_THREAD_ID else None
                await context.bot.send_message(
                    chat_id=ANNOUNCEMENT_CHAT_ID,
                    message_thread_id=thread_id,
                    text=group_msg,
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"❌ ERRO NOTIFICAR GRUPO: {e}")

        context.job_queue.run_once(
            end_kingdom_defense_event,
            when=duration_minutes * 60,
            name="auto_end_kingdom_defense"
        )
        logger.info("🛡️ Defesa Iniciada com sucesso.")

    except Exception as e:
        logger.error(f"Erro ao iniciar Kingdom Defense: {e}")


async def end_kingdom_defense_event(context: ContextTypes.DEFAULT_TYPE):
    if not event_manager:
        return
    if not getattr(event_manager, "is_active", False):
        return

    try:
        await event_manager.end_event()

        end_msg = (
            "🏁 <b>FIM DA INVASÃO!</b> 🏁\n\n"
            "As poeiras da batalha baixaram.\n"
            "Obrigado a todos os defensores!\n\n"
            "🏆 <i>Verifique o Ranking no menu do evento para ver os maiores danos!</i>"
        )

        if ANNOUNCEMENT_CHAT_ID:
            try:
                thread_id = ANNOUNCEMENT_THREAD_ID if ANNOUNCEMENT_THREAD_ID else None
                await context.bot.send_message(
                    chat_id=ANNOUNCEMENT_CHAT_ID,
                    message_thread_id=thread_id,
                    text=end_msg,
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"❌ ERRO NOTIFICAR GRUPO (KD END): {e}")

    except Exception as e:
        logger.error(f"Erro ao finalizar Kingdom Defense: {e}")


# ==============================================================================
# 👹 WORLD BOSS (mantido)
# ==============================================================================
async def start_world_boss_job(context: ContextTypes.DEFAULT_TYPE):
    if world_boss_manager is None:
        return
    if world_boss_manager.is_active:
        return

    logger.info("👹 [JOB] Iniciando World Boss...")
    result = world_boss_manager.start_event()

    if result.get("success"):
        location_key = result.get('location', 'desconhecido')
        region_info = (game_data.REGIONS_DATA.get(location_key) or {})
        location_display = region_info.get("display_name", location_key.replace("_", " ").title())

        if ANNOUNCEMENT_CHAT_ID:
            try:
                msg_text = (
                    f"👹 𝕎𝕆ℝ𝕃𝔻 𝔹𝕆𝕊𝕊 𝕊𝕌ℝ𝔾𝕀𝕌!\n"
                    f"📍 𝕃𝕠𝕔𝕒𝕝: {location_display}\n"
                    f"O monstro despertou! Ataquem!"
                )
                await context.bot.send_message(
                    chat_id=ANNOUNCEMENT_CHAT_ID,
                    message_thread_id=ANNOUNCEMENT_THREAD_ID,
                    text=msg_text,
                    parse_mode="HTML"
                )
            except Exception:
                pass

        try:
            await broadcast_boss_announcement(context.application, location_key)
        except Exception:
            pass


async def end_world_boss_job(context: ContextTypes.DEFAULT_TYPE):
    if not world_boss_manager or not world_boss_manager.is_active:
        return
    logger.info("👹 [JOB] Boss Time Out.")
    battle_results = world_boss_manager.end_event(reason="Tempo esgotado")
    await distribute_loot_and_announce(context, battle_results)


# ==============================================================================
# ⚔️ PVP / TEMPORADA (mantido)
# ==============================================================================
async def job_pvp_monthly_reset(context: ContextTypes.DEFAULT_TYPE):
    try:
        tz = ZoneInfo(JOB_TIMEZONE)
    except Exception:
        tz = datetime.timezone.utc

    now = datetime.datetime.now(tz)
    if now.day != 1:
        return

    # 1) Entrega recompensas (com base nos pontos atuais)
    await distribute_pvp_rewards(context)

    # 2) Zera a temporada (pontos voltam a 0)
    await reset_pvp_season(context)

    # 3) Se você ainda quiser chamar o seu engine legado/atual, chame após o reset.
    #    (ou remova se o engine faz reset e conflita)
    try:
        await executar_reset_pvp(context.bot, force_run=True)
    except Exception:
        pass



async def distribute_pvp_rewards(context: ContextTypes.DEFAULT_TYPE):
    """
    Distribui recompensas mensais do ranking PvP.
    Corrigido para:
      - suportar user_id como ObjectId/string (não é chat_id do Telegram)
      - creditar gemas no DB de forma segura (sync ou async collection)
      - notificar usando last_chat_id/telegram_id_owner/telegram_id quando existir
      - pagar apenas ranks definidos em MONTHLY_RANKING_REWARDS
    """
    # Sem tabela de recompensas, não faz nada
    if not MONTHLY_RANKING_REWARDS:
        return

    # ranks que realmente pagam
    paying_ranks = sorted(int(r) for r in MONTHLY_RANKING_REWARDS.keys())
    max_rank = max(paying_ranks)

    all_players_ranked = []
    try:
        async for user_id, p_data in player_manager.iter_players():
            try:
                pts = player_manager.get_pvp_points(p_data)
                if pts and pts > 0:
                    all_players_ranked.append({"user_id": user_id, "points": int(pts)})
            except Exception:
                pass
    except Exception:
        return

    if not all_players_ranked:
        # ainda assim pode anunciar
        if ANNOUNCEMENT_CHAT_ID:
            try:
                await context.bot.send_message(
                    chat_id=ANNOUNCEMENT_CHAT_ID,
                    message_thread_id=ANNOUNCEMENT_THREAD_ID,
                    text="🏆 <b>Ranking PvP Finalizado!</b>\n\nNinguém pontuou nesta temporada.",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        return

    all_players_ranked.sort(key=lambda p: p["points"], reverse=True)

    # Paga apenas até o maior rank premiado
    winners = all_players_ranked[:max_rank]

    paid_count = 0
    total_gems = 0

    for i, player in enumerate(winners):
        rank = i + 1
        reward_amount = MONTHLY_RANKING_REWARDS.get(rank)
        if not reward_amount:
            continue

        user_id = player["user_id"]
        col, query_id = get_col_and_id(user_id)

        if col is None:
            continue

        # --- Credita gemas (compatível com collection sync/async) ---
        try:
            upd = col.update_one({"_id": query_id}, {"$inc": {"gems": int(reward_amount)}})
            # se for coroutine (motor/async), aguarda
            if hasattr(upd, "__await__"):
                await upd
        except Exception:
            continue

        paid_count += 1
        total_gems += int(reward_amount)

        # --- Notificação (não usar user_id como chat_id!) ---
        target_chat_id = None
        try:
            pdata = await player_manager.get_player_data(user_id)
            if pdata:
                target_chat_id = (
                    pdata.get("last_chat_id")
                    or pdata.get("telegram_id_owner")
                    or pdata.get("telegram_id")
                )
        except Exception:
            target_chat_id = None

        if target_chat_id:
            try:
                await context.bot.send_message(
                    chat_id=target_chat_id,
                    text=f"🏆 Você terminou em <b>#{rank}</b> na Arena PvP e recebeu <b>{reward_amount}</b> gemas!",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    # --- Anúncio no chat definido ---
    if ANNOUNCEMENT_CHAT_ID:
        try:
            top_preview = []
            for i, p in enumerate(winners[:min(5, len(winners))]):
                r = i + 1
                if r in MONTHLY_RANKING_REWARDS:
                    top_preview.append(f"#{r} — <code>{p['user_id']}</code> ({p['points']} pts)")

            preview_txt = "\n".join(top_preview) if top_preview else "Sem top 5."
            await context.bot.send_message(
                chat_id=ANNOUNCEMENT_CHAT_ID,
                message_thread_id=ANNOUNCEMENT_THREAD_ID,
                text=(
                    "🏆 <b>Ranking PvP Finalizado!</b>\n\n"
                    f"Premiados: <b>{paid_count}</b>\n"
                    f"Gemas distribuídas: <b>{total_gems}</b>\n\n"
                    f"<b>Top:</b>\n{preview_txt}"
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass



async def reset_pvp_season(context: ContextTypes.DEFAULT_TYPE):
    if players_col is not None:
        players_col.update_many({}, {"$set": {"pvp_points": 0}})

    if users_col is not None:
        users_col.update_many({}, {"$set": {"pvp_points": 0}})

    if ANNOUNCEMENT_CHAT_ID:
        msg_season = (
            "╭────── [ 🏆 <b>NOVA TEMPORADA</b> ] ──────➤\n"
            "│\n"
            "│ ⚔️ <b>A ARENA FOI REINICIADA!</b>\n"
            "│ <i>Os deuses da guerra limparam o sangue</i>\n"
            "│ <i>da areia. A glória aguarda novos heróis!</i>\n"
            "│\n"
            "│ 🔄 <b>Status:</b> Pontos Resetados\n"
            "│ 💎 <b>Prêmios:</b> Entregues aos Top Rankings\n"
            "│\n"
            "╰──────────────────────────────➤\n"
            "🔥 <i>Vá à Arena e conquiste seu lugar na história!</i>"
        )

        try:
            await context.bot.send_message(
                chat_id=ANNOUNCEMENT_CHAT_ID,
                message_thread_id=ANNOUNCEMENT_THREAD_ID,
                text=msg_season,
                parse_mode="HTML"
            )
        except Exception:
            pass


# ==============================================================================
# ⚡ ENERGIA (mantido)
# ==============================================================================
_non_premium_tick: Dict[str, int] = {"count": 0}

async def regenerate_energy_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    _non_premium_tick["count"] = (_non_premium_tick["count"] + 1) % 2
    regenerate_non_premium = (_non_premium_tick["count"] == 0)

    try:
        async for user_id, pdata in player_manager.iter_players():
            try:
                max_e = int(player_manager.get_player_max_energy(pdata))
                cur_e = int(pdata.get("energy", 0))
                if cur_e >= max_e:
                    continue

                is_premium = player_manager.has_premium_plan(pdata)

                if is_premium or regenerate_non_premium:
                    col, query_id = get_col_and_id(user_id)
                    if col is not None:
                        col.update_one({"_id": query_id}, {"$inc": {"energy": 1}})
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Erro regenerate_energy_job: {e}")


# ==============================================================================
# 💎 PREMIUM WATCHDOG (mantido)
# ==============================================================================
async def check_premium_expiry_job(context: ContextTypes.DEFAULT_TYPE):
    count_downgraded = 0
    now = datetime.datetime.now(datetime.timezone.utc)

    async for user_id, pdata in player_manager.iter_players():
        try:
            current_tier = pdata.get("premium_tier")
            if not current_tier or current_tier == "free":
                continue

            pm = PremiumManager(pdata)
            if not pm.is_premium():
                exp_date = pm.expiration_date
                should_remove = (exp_date is None) or (exp_date < now)

                if should_remove:
                    logger.info(f"[PREMIUM] Expirou para user {user_id}. Resetando...")

                    pm.revoke()
                    col, query_id = get_col_and_id(user_id)

                    if col is not None:
                        col.update_one(
                            {"_id": query_id},
                            {"$set": {"premium_tier": "free", "premium_expires_at": None}}
                        )

                    if users_col is not None and col != users_col:
                        try:
                            users_col.update_one(
                                {"telegram_id_owner": int(str(user_id))},
                                {"$set": {"premium_tier": "free", "premium_expires_at": None}}
                            )
                        except Exception:
                            pass

                    target_chat_id = pdata.get("last_chat_id") or pdata.get("telegram_id_owner") or user_id
                    if target_chat_id:
                        msg = (
                            "⚠️ <b>ASSINATURA EXPIRADA</b>\n\n"
                            f"O seu plano <b>{str(current_tier).title()}</b> chegou ao fim.\n"
                            "Sua conta retornou para o status <b>Aventureiro Comum</b>."
                        )
                        await safe_send_message(context, target_chat_id, msg)

                    count_downgraded += 1

        except Exception as e:
            logger.error(f"Erro check_premium_expiry_job user {user_id}: {e}")
            continue

    if count_downgraded > 0:
        logger.info(f"[JOB PREMIUM] {count_downgraded} assinaturas vencidas processadas.")


# ==============================================================================
# 🔧 COMANDO ADMIN (mantido)
# ==============================================================================
async def cmd_force_pvp_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from config import ADMIN_ID
    user_id = get_current_player_id(update, context)
    if str(user_id) != str(ADMIN_ID):
        return

    await update.message.reply_text("🔄 DEBUG: Iniciando reset PvP...")
    await job_pvp_monthly_reset(context)
    await update.message.reply_text("✅ DEBUG: Concluído.")


admin_force_pvp_reset_handler = CommandHandler("force_pvp_reset", cmd_force_pvp_reset)
war_week_start_handler = CommandHandler("war_week_start", cmd_war_week_start)
war_force_active_handler = CommandHandler("war_force_active", cmd_war_force_active)
war_finalize_handler = CommandHandler("war_finalize", cmd_war_finalize)
war_status_handler = CommandHandler("war_status", cmd_war_status)
