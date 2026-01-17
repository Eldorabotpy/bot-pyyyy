# modules/guild_war/region.py
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone

UTC = timezone.utc


# =============================================================================
# Sistema único (campanha semanal)
# =============================================================================

class CampaignPhase(str, Enum):
    PREP = "PREP"
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"


# =============================================================================
# Compat (legado interno do guild_war anterior) — mantido, mas NÃO é fonte de verdade
# =============================================================================

class WarDay(str, Enum):
    THURSDAY = "thursday"
    SUNDAY = "sunday"


class WarPhase(str, Enum):
    PEACE = "peace"
    SIGNUP_OPEN = "signup_open"
    ACTIVE = "active"
    LOCKED = "locked"


class ActionType(str, Enum):
    PVE_KILL = "pve_kill"
    PVP_WIN = "pvp_win"
    PVP_LOSS = "pvp_loss"


DEFAULT_LEVEL_BRACKETS: List[Tuple[int, int]] = [
    (1, 10),
    (11, 20),
    (21, 30),
    (31, 40),
    (41, 50),
    (51, 60),
    (61, 999),
]


@dataclass
class WarWindow:
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
        # Robustez: se vier algo inesperado, cai para UTC now/now
        try:
            day = WarDay(str(data.get("day")))
        except Exception:
            day = WarDay.THURSDAY
        try:
            sa = datetime.fromisoformat(str(data.get("starts_at"))).astimezone(UTC)
            ea = datetime.fromisoformat(str(data.get("ends_at"))).astimezone(UTC)
        except Exception:
            now = datetime.now(UTC)
            sa, ea = now, now
        return WarWindow(day=day, starts_at=sa, ends_at=ea)


@dataclass
class RegionOwnership:
    owner_clan_id: Optional[str] = None
    last_changed_at: Optional[str] = None


@dataclass
class RegionWarState:
    phase: WarPhase = WarPhase.PEACE
    current_window: Optional[WarWindow] = None
    participants: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    influence: Dict[str, int] = field(default_factory=dict)
    last_event_log: List[Dict[str, Any]] = field(default_factory=list)
    thursday_result: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegionWarDocument:
    region_id: str
    ownership: RegionOwnership = field(default_factory=RegionOwnership)
    war: RegionWarState = field(default_factory=RegionWarState)
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


# =============================================================================
# Metadados da região
# =============================================================================

def get_region_meta(game_data_module, region_id: str) -> Dict[str, Any]:
    """
    Resolve metadados da região via REGIONS_DATA (fonte única do "nome bonito").
    """
    regions = getattr(game_data_module, "REGIONS_DATA", {}) or {}
    meta = regions.get(str(region_id)) or {}

    level_range = meta.get("level_range") or (1, 999)
    try:
        level_range = (int(level_range[0]), int(level_range[1]))
    except Exception:
        level_range = (1, 999)

    return {
        "region_id": str(region_id),
        "display_name": meta.get("display_name", str(region_id)),
        "emoji": meta.get("emoji", "📍"),
        "level_range": level_range,
        "resource": meta.get("resource"),
        "file_id_name": meta.get("file_id_name"),
        "description": meta.get("description", ""),
    }


# =============================================================================
# Elegibilidade
# =============================================================================

def compute_level_bracket(level: int, brackets: Optional[List[Tuple[int, int]]] = None) -> Tuple[int, int]:
    level = int(level or 1)
    brackets = brackets or DEFAULT_LEVEL_BRACKETS
    for lo, hi in brackets:
        if lo <= level <= hi:
            return (lo, hi)
    return brackets[-1]


def can_participate_in_region_war(player_level: int, region_level_range: Tuple[int, int]) -> bool:
    lo, hi = region_level_range
    lvl = int(player_level or 1)
    return (lo - 5) <= lvl <= (hi + 10)


# =============================================================================
# Serialização robusta (para evitar "unexpected keyword argument")
# =============================================================================

def to_mongo(doc: RegionWarDocument) -> Dict[str, Any]:
    payload = asdict(doc)
    ww = doc.war.current_window
    payload["war"]["current_window"] = ww.to_dict() if ww else None
    return payload


def from_mongo(data: Dict[str, Any]) -> RegionWarDocument:
    """
    Robusto: ignora chaves desconhecidas e tolera formatos antigos.
    """
    data = data or {}
    region_id = str(data.get("region_id") or data.get("_id") or "")
    doc = RegionWarDocument(region_id=region_id)

    ownership = data.get("ownership") or {}
    doc.ownership.owner_clan_id = ownership.get("owner_clan_id")
    doc.ownership.last_changed_at = ownership.get("last_changed_at")

    war = data.get("war") or {}
    try:
        doc.war.phase = WarPhase(str(war.get("phase") or WarPhase.PEACE.value))
    except Exception:
        doc.war.phase = WarPhase.PEACE

    doc.war.participants = war.get("participants") or {}
    doc.war.influence = {str(k): int(v) for k, v in (war.get("influence") or {}).items()}
    doc.war.last_event_log = war.get("last_event_log") or []
    doc.war.thursday_result = war.get("thursday_result") or {}

    cw = war.get("current_window")
    if cw:
        try:
            doc.war.current_window = WarWindow.from_dict(cw)
        except Exception:
            doc.war.current_window = None

    doc.updated_at = str(data.get("updated_at") or datetime.now(UTC).isoformat())
    return doc
