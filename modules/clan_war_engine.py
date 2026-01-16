# modules/clan_war_engine.py
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta, time as dt_time
from typing import Dict, Optional, Tuple, Any, List

from bson import ObjectId
from modules.player.core import players_collection

logger = logging.getLogger(__name__)

# ============================================================
# DATABASE
# ============================================================

def _get_db():
    try:
        return players_collection.database
    except Exception:
        return None

def _col(name: str):
    db = _get_db()
    if db is None:
        return None
    return db[name]


SYSTEM_COL = _col("system_data")
REGISTRATION_COL = _col("clan_war_registrations")
REGION_COL = _col("clan_war_regions")
PRESENCE_COL = _col("clan_war_presence")

# ============================================================
# CONSTANTES
# ============================================================

SEASON_DOC_ID = "clan_war_season_v1"
STATE_DOC_ID = "clan_war_state_v1"

# Placares semanais (doc único no system_data)
WEEKLY_DOC_ID = "clan_war_weekly_v1"

PHASE_PREP = "PREP"
PHASE_ACTIVE = "ACTIVE"
PHASE_ENDED = "ENDED"

DEFAULT_PRESENCE_TTL_SECONDS = 180

# Pontos padrão (ajuste quando quiser)
PVP_WIN_POINTS = 1
PVP_LOSS_POINTS = 0

PVE_HUNT_POINTS = 1
PVE_COLLECT_POINTS = 1
PVE_DUNGEON_POINTS = 3

# ============================================================
# HELPERS
# ============================================================

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def current_week_id(now: datetime | None = None) -> str:
    """
    Retorna o identificador da semana da Guerra de Clãs.
    Formato: YYYY-WW (ISO week).
    """
    if now is None:
        now = datetime.now(timezone.utc)

    year, week, _ = now.isocalendar()
    return f"{year}-W{week:02d}"

def _oid(x: Any) -> Optional[ObjectId]:
    if isinstance(x, ObjectId):
        return x
    if isinstance(x, str) and ObjectId.is_valid(x):
        return ObjectId(x)
    return None

def get_player_clan_id(pdata: dict) -> Optional[ObjectId]:
    for k in ("clan_id", "guild_id"):
        cid = _oid(pdata.get(k))
        if cid:
            return cid
    clan = pdata.get("clan") or pdata.get("guild")
    if isinstance(clan, dict):
        return _oid(clan.get("_id") or clan.get("id"))
    return None

def _safe_str(x: Any) -> str:
    try:
        return str(x)
    except Exception:
        return ""

def _get_local_tz():
    """
    Usa JOB_TIMEZONE do config quando possível; fallback UTC.
    """
    try:
        from zoneinfo import ZoneInfo
        from config import JOB_TIMEZONE
        return ZoneInfo(JOB_TIMEZONE)
    except Exception:
        return timezone.utc

def _week_id(dt: datetime) -> str:
    """
    Identificador estável por semana ISO.
    Ex.: '2026-W03'
    """
    iso = dt.isocalendar()
    return f"{iso.year}-W{int(iso.week):02d}"

def _ensure_system_doc(_id: str, default_doc: dict) -> dict:
    # ❗ PyMongo: Collection não pode ser avaliada como bool()
    if SYSTEM_COL is None:
        return dict(default_doc)

    doc = SYSTEM_COL.find_one({"_id": _id})
    if not doc:
        SYSTEM_COL.insert_one({"_id": _id, **default_doc})
        doc = SYSTEM_COL.find_one({"_id": _id}) or {"_id": _id, **default_doc}
    return doc

# ============================================================
# MODELOS
# ============================================================

@dataclass
class WarSeason:
    season_id: Optional[str] = None
    active: bool = False
    phase: str = PHASE_PREP
    registration_open: bool = False


@dataclass
class WarState:
    season_id: Optional[str] = None
    phase: str = PHASE_PREP
    # Mantém compatibilidade com seu legado (pode ser usado depois)
    registered_clans: Dict[str, str] = field(default_factory=dict)
    last_tick: Optional[str] = None

# ============================================================
# SEASON / STATE
# ============================================================

def get_season() -> WarSeason:
    if SYSTEM_COL is None:
        return WarSeason()

    doc = SYSTEM_COL.find_one({"_id": SEASON_DOC_ID})
    if not doc:
        season = WarSeason(
            season_id=current_week_id(),
            active=True,
            phase=PHASE_PREP,
            registration_open=False
        )
        SYSTEM_COL.insert_one({
            "_id": SEASON_DOC_ID,
            **asdict(season)
        })
        return season

    doc.pop("_id", None)

    # 🔒 blindagem retrocompat
    doc.setdefault("active", True)
    doc.setdefault("registration_open", False)

    return WarSeason(**doc)

def load_state() -> WarState:
    # ❗ PyMongo: Collection não pode ser avaliada como bool()
    if SYSTEM_COL is None:
        return WarState()

    doc = SYSTEM_COL.find_one({"_id": STATE_DOC_ID})
    if not doc:
        state = WarState()
        SYSTEM_COL.insert_one({"_id": STATE_DOC_ID, **asdict(state)})
        return state

    doc.pop("_id", None)
    return WarState(**doc)

def save_state(state: WarState):
    # ❗ PyMongo: Collection não pode ser avaliada como bool()
    if SYSTEM_COL is not None:
        SYSTEM_COL.update_one({"_id": STATE_DOC_ID}, {"$set": asdict(state)}, upsert=True)

# ============================================================
# WEEKLY SCOREBOARD
# ============================================================

def _load_weekly_doc(now_local: datetime) -> dict:
    """
    Retorna doc do placar semanal, garantindo week_id atual.
    Se week_id mudou (virou a semana), reinicia automaticamente.
    """
    wid = _week_id(now_local)

    default = {
        "week_id": wid,
        "created_at": now_local.isoformat(),
        "scores": {},   # clan_id -> {"total": int, "pvp": int, "pve": int}
        "logs": []      # lista curta (rotacionada) de eventos
    }
    doc = _ensure_system_doc(WEEKLY_DOC_ID, default)

    # Se trocou a semana, reseta doc
    if doc.get("week_id") != wid:
        doc = {"_id": WEEKLY_DOC_ID, **default}
        if SYSTEM_COL is not None:
            SYSTEM_COL.update_one({"_id": WEEKLY_DOC_ID}, {"$set": default}, upsert=True)

    return doc

def _save_weekly_doc(doc: dict):
    if SYSTEM_COL is None:
        return
    # remove _id duplicado no $set se vier
    d = dict(doc)
    d.pop("_id", None)
    SYSTEM_COL.update_one({"_id": WEEKLY_DOC_ID}, {"$set": d}, upsert=True)

async def add_war_points(
    clan_id,
    region_key: str,
    points: int,
    reason: str,
    player_id=None,
):
    """
    Soma pontos no placar semanal da guerra.
    - Não reseta diariamente
    - Separado do PvP normal
    - Seguro contra dados inválidos
    """
    if SYSTEM_COL is None:
        return

    # Sanitização
    try:
        pts = int(points)
    except Exception:
        pts = 0
    if pts <= 0:
        return

    cid = _oid(clan_id) or clan_id
    if not cid:
        return
    clan_key = _safe_str(cid)

    tz = _get_local_tz()
    now_local = datetime.now(tz)

    doc = _load_weekly_doc(now_local)
    scores = doc.get("scores") or {}
    entry = scores.get(clan_key) or {"total": 0, "pvp": 0, "pve": 0}

    # bucket por motivo
    r = (reason or "").lower().strip()
    is_pvp = r.startswith("pvp") or r in ("war_pvp", "pvp_win", "pvp_loss", "territory_pvp")
    is_pve = not is_pvp

    entry["total"] = int(entry.get("total", 0)) + pts
    if is_pvp:
        entry["pvp"] = int(entry.get("pvp", 0)) + pts
    else:
        entry["pve"] = int(entry.get("pve", 0)) + pts

    scores[clan_key] = entry
    doc["scores"] = scores

    # log (mantém tamanho controlado)
    logs: List[dict] = doc.get("logs") or []
    logs.append({
        "ts": now_local.isoformat(),
        "clan_id": clan_key,
        "region_key": _safe_str(region_key),
        "points": pts,
        "reason": reason,
        "player_id": _safe_str(player_id) if player_id else None
    })
    # limita logs para não estourar doc
    if len(logs) > 500:
        logs = logs[-500:]
    doc["logs"] = logs

    _save_weekly_doc(doc)

# ============================================================
# API USADA PELO REGION.PY
# ============================================================

async def get_war_status() -> dict:
    season = get_season()

    registered_players: Dict[str, str] = {}
    try:
        if PRESENCE_COL is not None:
            cutoff = _now_utc() - timedelta(seconds=DEFAULT_PRESENCE_TTL_SECONDS)
            for p in PRESENCE_COL.find(
                {"last_seen": {"$gte": cutoff}},
                {"player_id": 1, "clan_id": 1}
            ):
                if p.get("player_id") and p.get("clan_id"):
                    registered_players[str(p["player_id"])] = str(p["clan_id"])
    except Exception:
        pass

    # 🔑 AQUI ESTAVA O PROBLEMA
    registration_open = False
    try:
        if SYSTEM_COL is not None:
            doc = SYSTEM_COL.find_one({"_id": SEASON_DOC_ID})
            registration_open = bool(doc.get("registration_open")) if doc else False
    except Exception:
        pass

    return {
        "season": {
            **asdict(season),
            "registration_open": registration_open
        },
        "state": {
            "phase": season.phase,
            "registered_players": registered_players,
            "registrations_by_clan": {}
        }
    }


# ============================================================
# ELEGIBILIDADE
# ============================================================

async def can_player_participate_in_war(pdata: dict) -> Tuple[bool, str]:
    season = get_season()
    if not season.active or season.phase != PHASE_ACTIVE:
        return False, "⛔ Guerra não ativa."

    clan_id = get_player_clan_id(pdata)
    if not clan_id:
        return False, "⛔ Você não possui clã."

    if REGISTRATION_COL is None:
        return False, "⛔ Registro indisponível."

    if not REGISTRATION_COL.find_one({
        "season_id": season.season_id,
        "clan_id": clan_id,
        "active": True
    }):
        return False, "⛔ Seu clã não está registrado."

    return True, ""

# ============================================================
# PRESENÇA / MATCH
# ============================================================

async def update_presence(player_id: ObjectId, pdata: dict, region_key: str, chat_id: Optional[int] = None):
    if PRESENCE_COL is None:
        return

    ok, _ = await can_player_participate_in_war(pdata)
    if not ok:
        return

    PRESENCE_COL.update_one(
        {"player_id": player_id},
        {"$set": {
            "player_id": player_id,
            "clan_id": get_player_clan_id(pdata),
            "region_key": region_key,
            "last_seen": _now_utc(),
            "chat_id": chat_id
        }},
        upsert=True
    )

async def find_enemy_in_region(my_player_id: ObjectId, my_clan_id: ObjectId, region_key: str):
    if PRESENCE_COL is None:
        return None

    cutoff = _now_utc() - timedelta(seconds=DEFAULT_PRESENCE_TTL_SECONDS)
    candidates = list(PRESENCE_COL.find({
        "region_key": region_key,
        "clan_id": {"$ne": my_clan_id},
        "player_id": {"$ne": my_player_id},
        "last_seen": {"$gte": cutoff}
    }))
    return random.choice(candidates) if candidates else None

# ============================================================
# BATALHA / PONTUAÇÃO
# ============================================================

async def register_battle(clan_id: ObjectId, region_key: str, outcome: str):
    """
    Mantém pontos por região (controle local) + adiciona pontos semanais globais.
    """
    if REGION_COL is None:
        return

    # ---- (A) Controle local por região (mantido) ----
    doc = REGION_COL.find_one({"region_key": region_key}) or {
        "region_key": region_key,
        "points": {}
    }

    pts = int((doc.get("points") or {}).get(str(clan_id), 0))
    if outcome == "win":
        pts += 1
    doc.setdefault("points", {})
    doc["points"][str(clan_id)] = pts

    REGION_COL.update_one(
        {"region_key": region_key},
        {"$set": doc},
        upsert=True
    )

    # ---- (B) Placar semanal global (novo) ----
    if outcome == "win":
        await add_war_points(clan_id=clan_id, region_key=region_key, points=PVP_WIN_POINTS, reason="pvp_win")
    else:
        if PVP_LOSS_POINTS > 0:
            await add_war_points(clan_id=clan_id, region_key=region_key, points=PVP_LOSS_POINTS, reason="pvp_loss")

# ============================================================
# FINALIZAÇÃO SEMANAL + ANÚNCIO
# ============================================================

async def weekly_finalize_and_announce(application):
    """
    Executa no domingo:
    - calcula vencedor global (por pontos semanais)
    - anuncia em ANNOUNCEMENT_CHAT_ID (e thread, se houver)
    - zera placar semanal
    - (opcional) marca temporada como ENDED e volta para PREP
    """
    if SYSTEM_COL is None:
        return

    tz = _get_local_tz()
    now_local = datetime.now(tz)

    # Carrega placar
    doc = _load_weekly_doc(now_local)
    scores = doc.get("scores") or {}

    # Se não houve pontuação, ainda assim anuncia (opcional)
    ranking = []
    for clan_key, data in scores.items():
        try:
            total = int((data or {}).get("total", 0))
            pvp = int((data or {}).get("pvp", 0))
            pve = int((data or {}).get("pve", 0))
        except Exception:
            total, pvp, pve = 0, 0, 0
        ranking.append((clan_key, total, pvp, pve))
    ranking.sort(key=lambda x: x[1], reverse=True)

    winner = ranking[0] if ranking else None

    # Monta mensagem
    title = "🏁 <b>GUERRA DE CLÃS — RESULTADO SEMANAL</b>"
    when_txt = now_local.strftime("%d/%m/%Y %H:%M")
    lines = [title, f"🗓️ <i>Encerramento:</i> {when_txt}", ""]

    if not winner or winner[1] <= 0:
        lines.append("⚠️ <b>Sem pontuações registradas nesta semana.</b>")
    else:
        lines.append(f"👑 <b>Vencedor:</b> <code>{winner[0]}</code>")
        lines.append(f"⭐ <b>Pontos:</b> {winner[1]} (PvP {winner[2]} | PvE {winner[3]})")

    # Top 5
    if ranking:
        lines.append("")
        lines.append("🏆 <b>Top 5 Clãs</b>")
        topn = ranking[:5]
        for i, (cid, total, pvp, pve) in enumerate(topn, start=1):
            lines.append(f"{i}. <code>{cid}</code> — {total} (PvP {pvp} | PvE {pve})")

    text = "\n".join(lines)

    # Envia anúncio
    try:
        from config import ANNOUNCEMENT_CHAT_ID, ANNOUNCEMENT_THREAD_ID
        chat_id = ANNOUNCEMENT_CHAT_ID
        thread_id = ANNOUNCEMENT_THREAD_ID
    except Exception:
        chat_id = None
        thread_id = None

    if application and chat_id:
        try:
            kwargs = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
            # Thread (tópicos)
            if thread_id:
                kwargs["message_thread_id"] = int(thread_id)
            await application.bot.send_message(**kwargs)
        except Exception as e:
            logger.warning(f"[WAR] Falha ao anunciar resultado semanal: {e}")

    # Marca como ENDED (estado macro) e reseta placar
    try:
        season = get_season()
        if season.active:
            season.phase = PHASE_ENDED
            if SYSTEM_COL is not None:
                SYSTEM_COL.update_one({"_id": SEASON_DOC_ID}, {"$set": asdict(season)}, upsert=True)
    except Exception:
        pass

    # Zera placar para a próxima semana (sem esperar virada ISO)
    try:
        new_week = _week_id(now_local + timedelta(days=1))
        reset_doc = {
            "week_id": new_week,
            "created_at": now_local.isoformat(),
            "scores": {},
            "logs": []
        }
        if SYSTEM_COL is not None:
            SYSTEM_COL.update_one({"_id": WEEKLY_DOC_ID}, {"$set": reset_doc}, upsert=True)
    except Exception:
        pass

    # Volta para PREP (para começar nova semana)
    try:
        season = get_season()
        season.phase = PHASE_PREP
        season.active = True if season.season_id else season.active  # mantém como está se não houver season_id
        if SYSTEM_COL is not None:
            SYSTEM_COL.update_one({"_id": SEASON_DOC_ID}, {"$set": asdict(season)}, upsert=True)
    except Exception:
        pass

# ============================================================
# SCHEDULER
# ============================================================

async def war_tick(context=None):
    """
    Tick leve (telemetria/heartbeat). Mantido.
    """
    state = load_state()
    state.last_tick = _now_utc().isoformat()
    save_state(state)

async def _weekly_finalize_job(context):
    """
    JobQueue callback (precisa ser async e receber context).
    Evita lambda retornando coroutine sem await.
    """
    try:
        application = context.application
    except Exception:
        application = None
    await weekly_finalize_and_announce(application)

def register_war_jobs(application):
    """
    Registra:
    - tick repetitivo (leve)
    - finalização semanal no domingo (anúncio + reset)
    - opcional: job “quarta” pode ser adicionado depois (escaramuça)
    """
    jq = application.job_queue

    jq.run_repeating(
        war_tick,
        interval=60,
        first=10,
        name="clan_war_tick"
    )

    # Finalização semanal (domingo)
    try:
        tz = _get_local_tz()
        # Domingo às 23:55 (ajustável)
        finalize_time = dt_time(hour=23, minute=55, tzinfo=tz)
        jq.run_daily(
            _weekly_finalize_job,
            time=finalize_time,
            days=(6,),  # 0=seg ... 6=dom
            name="clan_war_weekly_finalize"
        )
    except Exception as e:
        logger.warning(f"[WAR] Falha ao agendar finalize semanal: {e}")

# ============================================================
# COMPAT: Funções legadas usadas por handlers/guild/dashboard.py
# ============================================================

async def open_clan_registration():
    """
    Compat: abre período de inscrição.
    No modelo semanal, isso significa:
    - garantir season_id
    - marcar guerra ativa em PREP (pré-guerra/inscrição aberta)
    """
    if SYSTEM_COL is None:
        return False

    tz = _get_local_tz()
    now_local = datetime.now(tz)
    season = get_season()

    if not season.season_id:
        season.season_id = _week_id(now_local)

    season.active = True
    season.phase = PHASE_PREP

    try:
        SYSTEM_COL.update_one(
            {"_id": SEASON_DOC_ID},
            {"$set": {**asdict(season), "registration_open": True}},
            upsert=True
        )
    except Exception:
        SYSTEM_COL.update_one({"_id": SEASON_DOC_ID}, {"$set": asdict(season)}, upsert=True)

    return True

async def close_clan_registration():
    """
    Compat: fecha período de inscrição.
    Mantemos a guerra em PREP, mas com flag registration_open False.
    """
    if SYSTEM_COL is None:
        return False

    season = get_season()
    if not season.season_id:
        season.season_id = _week_id(datetime.now(_get_local_tz()))

    season.active = True
    season.phase = PHASE_PREP

    try:
        SYSTEM_COL.update_one(
            {"_id": SEASON_DOC_ID},
            {"$set": {**asdict(season), "registration_open": False}},
            upsert=True
        )
    except Exception:
        SYSTEM_COL.update_one({"_id": SEASON_DOC_ID}, {"$set": asdict(season)}, upsert=True)

    return True

async def start_clan_war():
    """
    Compat: inicia guerra (fase ACTIVE).
    """
    if SYSTEM_COL is None:
        return False

    season = get_season()
    if not season.season_id:
        season.season_id = _week_id(datetime.now(_get_local_tz()))

    season.active = True
    season.phase = PHASE_ACTIVE

    SYSTEM_COL.update_one({"_id": SEASON_DOC_ID}, {"$set": asdict(season)}, upsert=True)
    return True

async def end_clan_war(application=None):
    """
    Compat: encerra guerra (fase ENDED).
    Se application for passado, dispara o fechamento semanal + anúncio.
    """
    if SYSTEM_COL is None:
        return False

    season = get_season()
    season.active = True
    season.phase = PHASE_ENDED
    SYSTEM_COL.update_one({"_id": SEASON_DOC_ID}, {"$set": asdict(season)}, upsert=True)

    if application is not None:
        try:
            await weekly_finalize_and_announce(application)
        except Exception as e:
            logger.warning(f"[WAR] end_clan_war finalize falhou: {e}")

    return True

async def register_clan_for_war(clan_id):
    """
    Compat: registra um clã na guerra atual.
    (Seu sistema já usa REGISTRATION_COL; isso é só um wrapper.)
    """
    if REGISTRATION_COL is None:
        return False

    season = get_season()
    if not season.season_id:
        season.season_id = _week_id(datetime.now(_get_local_tz()))
        season.active = True
        season.phase = PHASE_PREP
        if SYSTEM_COL is not None:
            SYSTEM_COL.update_one({"_id": SEASON_DOC_ID}, {"$set": asdict(season)}, upsert=True)

    cid = _oid(clan_id) or clan_id
    if not cid:
        return False

    REGISTRATION_COL.update_one(
        {"season_id": season.season_id, "clan_id": cid},
        {"$set": {
            "season_id": season.season_id,
            "clan_id": cid,
            "active": True,
            "updated_at": _now_utc()
        }},
        upsert=True
    )
    return True

async def join_war_as_member(player_id, player_data: dict, region_key: str = None, chat_id: int | None = None):
    """
    Compat: 'inscrever membro na guerra'.
    Participar do PvP territorial depende de PRESENCE_COL (TTL), então:
      -> atualizar presença do jogador (update_presence)
    """
    try:
        pid = _oid(player_id) or player_id
        if not pid:
            return False, "ID de jogador inválido."

        if not isinstance(player_data, dict):
            return False, "Dados do jogador inválidos."

        ok, reason = await can_player_participate_in_war(player_data)
        if not ok:
            return False, reason or "⛔ Você não pode participar da guerra."

        rk = region_key or player_data.get("current_location") or "reino_eldora"

        try:
            await update_presence(pid, player_data, rk, chat_id=chat_id)
        except Exception:
            pass

        try:
            if SYSTEM_COL is not None:
                SYSTEM_COL.update_one(
                    {"_id": STATE_DOC_ID},
                    {"$set": {"last_member_join_at": _now_utc().isoformat()}},
                    upsert=True
                )
        except Exception:
            pass

        return True, "✅ Você entrou na Guerra de Clãs!"

    except Exception as e:
        return False, f"Erro ao entrar na guerra: {e}"

async def leave_war_as_member(player_id, player_data: dict | None = None):
    """
    Compat: 'sair da guerra como membro'.
    Sair = remover presença.
    """
    try:
        pid = _oid(player_id) or player_id
        if not pid:
            return False, "ID de jogador inválido."

        if PRESENCE_COL is None:
            return False, "Sistema de presença indisponível."

        PRESENCE_COL.delete_one({"player_id": pid})

        try:
            if SYSTEM_COL is not None:
                SYSTEM_COL.update_one(
                    {"_id": STATE_DOC_ID},
                    {"$set": {"last_member_leave_at": _now_utc().isoformat()}},
                    upsert=True
                )
        except Exception:
            pass

        return True, "✅ Você saiu da Guerra de Clãs."

    except Exception as e:
        return False, f"Erro ao sair da guerra: {e}"

# ============================================================
# COMPAT para handlers/guild/war.py
# ============================================================

def get_current_war_mode() -> str:
    """
    Compat: retorna "PVE" ou "PVP".
    """
    try:
        tz = _get_local_tz()
        wd = datetime.now(tz).weekday()  # 0 seg ... 6 dom
        if wd in (2, 6):  # quarta e domingo
            return "PVP"
        return "PVE"
    except Exception:
        return "PVE"

async def get_region_leaderboard(region_key: str, limit: int = 10):
    """
    Compat: Top clãs por pontos naquela região.
    """
    if REGION_COL is None:
        return []

    doc = REGION_COL.find_one({"region_key": region_key}) or {}
    points_map = doc.get("points") or {}
    if not isinstance(points_map, dict) or not points_map:
        return []

    ranking = []
    for clan_id_str, pts in points_map.items():
        try:
            p = int(pts)
        except Exception:
            p = 0
        ranking.append((clan_id_str, p))
    ranking.sort(key=lambda x: x[1], reverse=True)
    ranking = ranking[: max(1, int(limit))]

    out = []
    CLANS_COL = _col("clans") or _col("guilds")
    for clan_id_str, p in ranking:
        clan_name = clan_id_str
        try:
            if CLANS_COL is not None:
                cid = _oid(clan_id_str) or clan_id_str
                clan_doc = CLANS_COL.find_one({"_id": cid}, {"display_name": 1, "name": 1})
                if clan_doc:
                    clan_name = clan_doc.get("display_name") or clan_doc.get("name") or clan_name
        except Exception:
            pass
        out.append({"clan_name": clan_name, "points": p})

    return out
