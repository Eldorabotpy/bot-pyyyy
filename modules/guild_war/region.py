# modules/guild_war/region.py
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone


# =============================================================================
# Enums / Constantes
# =============================================================================

UTC = timezone.utc


class WarDay(str, Enum):
    THURSDAY = "thursday"
    SUNDAY = "sunday"


class WarPhase(str, Enum):
    # Região fora da guerra (sem janela ativa)
    PEACE = "peace"

    # Inscrições abertas para a próxima janela
    SIGNUP_OPEN = "signup_open"

    # Guerra em andamento (durante a janela)
    ACTIVE = "active"

    # Guerra encerrada, aguardando resolução/fechamento (apuração)
    LOCKED = "locked"


class ActionType(str, Enum):
    PVE_KILL = "pve_kill"
    PVP_WIN = "pvp_win"
    PVP_LOSS = "pvp_loss"


# Sugestão de faixas (você pode ajustar depois ou calcular dinamicamente)
DEFAULT_LEVEL_BRACKETS: List[Tuple[int, int]] = [
    (1, 10),
    (11, 20),
    (21, 30),
    (31, 40),
    (41, 50),
    (51, 60),
    (61, 999),
]


# =============================================================================
# Models (estado)
# =============================================================================

@dataclass
class WarWindow:
    """
    Representa a janela de guerra: início/fim em UTC.

    Observação:
    - Internamente mantenha UTC; UI pode mostrar local.
    """
    day: WarDay
    starts_at: datetime
    ends_at: datetime

    def is_open(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.now(UTC)
        return self.starts_at <= now < self.ends_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "day": self.day.value,
            "starts_at": self.starts_at.astimezone(UTC).isoformat(),
            "ends_at": self.ends_at.astimezone(UTC).isoformat(),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "WarWindow":
        return WarWindow(
            day=WarDay(str(data.get("day"))),
            starts_at=datetime.fromisoformat(str(data.get("starts_at"))).astimezone(UTC),
            ends_at=datetime.fromisoformat(str(data.get("ends_at"))).astimezone(UTC),
        )


@dataclass
class RegionOwnership:
    owner_clan_id: Optional[str] = None   # ObjectId string do clã dominante
    last_changed_at: Optional[str] = None # ISO string


@dataclass
class RegionWarState:
    phase: WarPhase = WarPhase.PEACE
    current_window: Optional[WarWindow] = None

    # inscritos do evento atual (somente durante signup/active/locked)
    # player_id -> payload (clan_id, level, joined_at, bracket...)
    participants: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # influência acumulada na janela atual (clan_id -> pontos)
    influence: Dict[str, int] = field(default_factory=dict)

    # auditoria simples (opcional)
    last_event_log: List[Dict[str, Any]] = field(default_factory=list)

    # vantagem do domingo baseada na quinta (se você quiser usar no war_event)
    thursday_result: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegionWarDocument:
    """
    Documento de guerra por região (o que vai para o DB).
    Sugestão: 1 doc por region_id em uma collection: region_war_state
    """
    region_id: str
    ownership: RegionOwnership = field(default_factory=RegionOwnership)
    war: RegionWarState = field(default_factory=RegionWarState)
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


# =============================================================================
# Metadados da região (ponte com modules.game_data.regions)
# =============================================================================

def get_region_meta(game_data_module, region_id: str) -> Dict[str, Any]:
    """
    Lê metadados da região já existentes em game_data.REGIONS_DATA.
    Não duplique mapa aqui.
    """
    regions = getattr(game_data_module, "REGIONS_DATA", {}) or {}
    meta = regions.get(region_id) or {}

    level_range = meta.get("level_range") or (1, 999)
    try:
        level_range = (int(level_range[0]), int(level_range[1]))
    except Exception:
        level_range = (1, 999)

    return {
        "region_id": region_id,
        "display_name": meta.get("display_name", region_id),
        "emoji": meta.get("emoji", "📍"),
        "level_range": level_range,
        "resource": meta.get("resource"),
        "file_id_name": meta.get("file_id_name"),
        "description": meta.get("description", ""),
    }


# =============================================================================
# Regras de inscrição / elegibilidade
# =============================================================================

def compute_level_bracket(level: int, brackets: Optional[List[Tuple[int, int]]] = None) -> Tuple[int, int]:
    level = int(level or 1)
    brackets = brackets or DEFAULT_LEVEL_BRACKETS
    for lo, hi in brackets:
        if lo <= level <= hi:
            return (lo, hi)
    return brackets[-1]


def can_participate_in_region_war(player_level: int, region_level_range: Tuple[int, int]) -> bool:
    """
    Regra simples:
    - permite entrar se o jogador estiver dentro da faixa ou “próximo”.
    """
    lo, hi = region_level_range
    lvl = int(player_level or 1)
    return (lo - 5) <= lvl <= (hi + 10)


def is_participant(doc: RegionWarDocument, player_id: str) -> bool:
    return str(player_id) in (doc.war.participants or {})


def get_participant(doc: RegionWarDocument, player_id: str) -> Optional[Dict[str, Any]]:
    return (doc.war.participants or {}).get(str(player_id))


def register_participant(doc: RegionWarDocument, player_id: str, clan_id: str, level: int) -> None:
    """
    Registra um jogador como participante oficial da janela.
    """
    pid = str(player_id)
    cid = str(clan_id)

    doc.war.participants[pid] = {
        "player_id": pid,
        "clan_id": cid,
        "level": int(level or 1),
        "bracket": compute_level_bracket(level),
        "joined_at": datetime.now(UTC).isoformat(),
    }
    doc.updated_at = datetime.now(UTC).isoformat()


def unregister_participant(doc: RegionWarDocument, player_id: str) -> None:
    doc.war.participants.pop(str(player_id), None)
    doc.updated_at = datetime.now(UTC).isoformat()


# =============================================================================
# Influência (PvE / PvP) + logs
# =============================================================================

def _push_log(doc: RegionWarDocument, entry: Dict[str, Any], max_items: int = 30) -> None:
    doc.war.last_event_log.append(entry)
    if len(doc.war.last_event_log) > max_items:
        doc.war.last_event_log = doc.war.last_event_log[-max_items:]


def add_influence(
    doc: RegionWarDocument,
    clan_id: str,
    points: int,
    reason: ActionType,
    player_id: Optional[str] = None,
    enemy_player_id: Optional[str] = None,
) -> None:
    """
    Adiciona (ou remove) influência para um clã.
    points pode ser negativo.
    """
    cid = str(clan_id)
    delta = int(points)

    doc.war.influence[cid] = int(doc.war.influence.get(cid, 0)) + delta

    _push_log(doc, {
        "ts": datetime.now(UTC).isoformat(),
        "reason": reason.value,
        "clan_id": cid,
        "points": delta,
        "player_id": str(player_id) if player_id else None,
        "enemy_player_id": str(enemy_player_id) if enemy_player_id else None,
    })
    doc.updated_at = datetime.now(UTC).isoformat()


def award_pve_kill(doc: RegionWarDocument, player_id: str, clan_id: str, base_points: int = 3) -> None:
    """
    Chamado quando o jogador mata mob (durante ACTIVE).
    """
    add_influence(
        doc,
        clan_id=clan_id,
        points=int(base_points),
        reason=ActionType.PVE_KILL,
        player_id=player_id
    )


def award_pvp_result(
    doc: RegionWarDocument,
    winner_player_id: str,
    winner_clan_id: str,
    loser_player_id: str,
    loser_clan_id: str,
    base_points: int = 12,
    steal_ratio: float = 0.50,
) -> None:
    """
    PvP durante ACTIVE:
    - vencedor ganha pontos
    - perdedor perde uma fração (roubo / negação)
    """
    win_pts = int(base_points)
    lose_pts = -int(round(base_points * float(steal_ratio)))

    add_influence(
        doc,
        clan_id=winner_clan_id,
        points=win_pts,
        reason=ActionType.PVP_WIN,
        player_id=winner_player_id,
        enemy_player_id=loser_player_id
    )

    add_influence(
        doc,
        clan_id=loser_clan_id,
        points=lose_pts,
        reason=ActionType.PVP_LOSS,
        player_id=loser_player_id,
        enemy_player_id=winner_player_id
    )


# =============================================================================
# Estado da Guerra: abrir inscrições / iniciar / encerrar / resolver
# =============================================================================

def open_signup(doc: RegionWarDocument, window: WarWindow) -> None:
    """
    PEACE -> SIGNUP_OPEN (limpa estado da janela anterior)
    """
    doc.war.phase = WarPhase.SIGNUP_OPEN
    doc.war.current_window = window
    doc.war.participants = {}
    doc.war.influence = {}
    doc.war.last_event_log = []
    doc.updated_at = datetime.now(UTC).isoformat()


def start_war(doc: RegionWarDocument) -> None:
    """
    SIGNUP_OPEN -> ACTIVE
    """
    doc.war.phase = WarPhase.ACTIVE
    doc.updated_at = datetime.now(UTC).isoformat()


def lock_war(doc: RegionWarDocument) -> None:
    """
    ACTIVE -> LOCKED (fim da janela).
    """
    doc.war.phase = WarPhase.LOCKED
    doc.updated_at = datetime.now(UTC).isoformat()


def resolve_war(doc: RegionWarDocument, day: WarDay) -> Dict[str, Any]:
    """
    Resolve o resultado do evento.
    - Quinta: salva “vantagem” (não troca dono)
    - Domingo: troca dono pela maior influência
    """
    ranked = sorted(doc.war.influence.items(), key=lambda kv: int(kv[1]), reverse=True)
    winner_clan_id = ranked[0][0] if ranked else None
    winner_points = ranked[0][1] if ranked else 0

    result = {
        "day": day.value,
        "winner_clan_id": winner_clan_id,
        "winner_points": int(winner_points),
        "ranked": [{"clan_id": cid, "points": int(pts)} for cid, pts in ranked[:10]],
        "resolved_at": datetime.now(UTC).isoformat(),
    }

    if day == WarDay.THURSDAY:
        doc.war.thursday_result = result

    elif day == WarDay.SUNDAY:
        if winner_clan_id:
            doc.ownership.owner_clan_id = winner_clan_id
            doc.ownership.last_changed_at = datetime.now(UTC).isoformat()

    # encerra a janela e volta ao PEACE (limpeza)
    doc.war.phase = WarPhase.PEACE
    doc.war.current_window = None
    doc.updated_at = datetime.now(UTC).isoformat()
    return result


# =============================================================================
# Serialização / helpers
# =============================================================================

def to_mongo(doc: RegionWarDocument) -> Dict[str, Any]:
    """
    Converte para dict para salvar no Mongo.
    """
    payload = asdict(doc)

    ww = doc.war.current_window
    if ww:
        payload["war"]["current_window"] = ww.to_dict()
    else:
        payload["war"]["current_window"] = None

    return payload


def from_mongo(data: Dict[str, Any]) -> RegionWarDocument:
    """
    Monta o objeto a partir do dict do Mongo.
    """
    region_id = str(data.get("region_id") or data.get("_id") or "")
    doc = RegionWarDocument(region_id=region_id)

    ownership = data.get("ownership") or {}
    doc.ownership.owner_clan_id = ownership.get("owner_clan_id")
    doc.ownership.last_changed_at = ownership.get("last_changed_at")

    war = data.get("war") or {}
    doc.war.phase = WarPhase(str(war.get("phase") or WarPhase.PEACE.value))
    doc.war.participants = war.get("participants") or {}
    doc.war.influence = {str(k): int(v) for k, v in (war.get("influence") or {}).items()}
    doc.war.last_event_log = war.get("last_event_log") or []
    doc.war.thursday_result = war.get("thursday_result") or {}

    cw = war.get("current_window")
    if cw:
        doc.war.current_window = WarWindow.from_dict(cw)

    doc.updated_at = str(data.get("updated_at") or datetime.now(UTC).isoformat())
    return doc
