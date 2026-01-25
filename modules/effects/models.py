# modules/effects/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal
from uuid import uuid4

# -----------------------------
# Tipos base
# -----------------------------
EffectKind = Literal["buff", "debuff"]
DurationKind = Literal["turns", "seconds"]  # no MVP, use "turns" no combate

# Eventos padrão do engine (você pode expandir depois)
EVENT_ON_APPLY = "on_apply"
EVENT_ON_REFRESH = "on_refresh"
EVENT_ON_EXPIRE = "on_expire"
EVENT_ON_TURN_START = "on_turn_start"
EVENT_ON_TURN_END = "on_turn_end"
EVENT_ON_BEFORE_ATTACK = "on_before_attack"
EVENT_ON_AFTER_ATTACK = "on_after_attack"
EVENT_ON_BEFORE_DAMAGE = "on_before_damage"
EVENT_ON_AFTER_DAMAGE = "on_after_damage"
EVENT_ON_HEAL = "on_heal"
EVENT_ON_DISPEL = "on_dispel"
EVENT_ON_DEATH = "on_death"

ALL_EVENTS: List[str] = [
    EVENT_ON_APPLY, EVENT_ON_REFRESH, EVENT_ON_EXPIRE,
    EVENT_ON_TURN_START, EVENT_ON_TURN_END,
    EVENT_ON_BEFORE_ATTACK, EVENT_ON_AFTER_ATTACK,
    EVENT_ON_BEFORE_DAMAGE, EVENT_ON_AFTER_DAMAGE,
    EVENT_ON_HEAL, EVENT_ON_DISPEL, EVENT_ON_DEATH
]

DamageType = Literal[
    "physical", "magic", "true",
    "bleed", "poison", "fire", "ice", "arcane"
]

# Flags de combate comuns
@dataclass
class CombatFlags:
    is_crit: bool = False
    was_dodged: bool = False
    was_blocked: bool = False
    is_skill: bool = False
    is_support: bool = False


# -----------------------------
# Contexto de combate
# -----------------------------
@dataclass
class CombatContext:
    """
    Contexto que circula nos eventos do EffectEngine.
    O combate cria isso e chama engine.dispatch(event, ctx).
    Effects podem ler e alterar campos (ex.: ctx.damage, ctx.heal).
    """
    event: str
    source: Dict[str, Any]                 # entidade atacante/curador (dict)
    target: Dict[str, Any]                 # entidade alvo (dict)
    battle: Dict[str, Any]                 # battle_cache ou ctx do combate
    skill_id: Optional[str] = None

    damage: int = 0
    heal: int = 0
    damage_type: DamageType = "physical"

    flags: CombatFlags = field(default_factory=CombatFlags)

    # espaço para qualquer dado extra (andar da torre, dificuldade, etc.)
    meta: Dict[str, Any] = field(default_factory=dict)


# -----------------------------
# Instância de efeito ativo
# -----------------------------
@dataclass
class EffectInstance:
    """
    Um efeito ativo em uma entidade (jogador/monstro).
    - effect_id aponta para o template no registry.
    - uid identifica essa instância (para remover/atualizar com precisão).
    """
    effect_id: str
    kind: EffectKind

    uid: str = field(default_factory=lambda: uuid4().hex)

    source_id: Optional[str] = None        # player_id / monster_id / skill_id etc.
    source_type: Optional[str] = None      # "skill" | "rune" | "class" | "tower" | "mob" etc.

    duration_kind: DurationKind = "turns"
    remaining: int = 0                     # turnos restantes (0 = expira)
    permanent: bool = False                # se True, ignora remaining

    stacks: int = 1
    potency: float = 1.0                   # intensidade (ex.: 0.3 = -30% cura)
    dispellable: bool = True

    tags: List[str] = field(default_factory=list)

    # regras úteis (stack, refresh, exclusive group etc.)
    rules: Dict[str, Any] = field(default_factory=dict)

    # metadata livre (floor, seed, rarity etc.)
    meta: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        if self.permanent:
            return False
        return self.remaining <= 0

    def tick(self) -> None:
        """
        Decrementa duração por turno (MVP).
        """
        if self.permanent:
            return
        if self.duration_kind == "turns":
            self.remaining -= 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "effect_id": self.effect_id,
            "kind": self.kind,
            "uid": self.uid,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "duration_kind": self.duration_kind,
            "remaining": self.remaining,
            "permanent": self.permanent,
            "stacks": self.stacks,
            "potency": self.potency,
            "dispellable": self.dispellable,
            "tags": list(self.tags),
            "rules": dict(self.rules),
            "meta": dict(self.meta),
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "EffectInstance":
        return EffectInstance(
            effect_id=str(d.get("effect_id", "")),
            kind=d.get("kind", "buff"),
            uid=str(d.get("uid") or uuid4().hex),
            source_id=d.get("source_id"),
            source_type=d.get("source_type"),
            duration_kind=d.get("duration_kind", "turns"),
            remaining=int(d.get("remaining", 0)),
            permanent=bool(d.get("permanent", False)),
            stacks=int(d.get("stacks", 1)),
            potency=float(d.get("potency", 1.0)),
            dispellable=bool(d.get("dispellable", True)),
            tags=list(d.get("tags", []) or []),
            rules=dict(d.get("rules", {}) or {}),
            meta=dict(d.get("meta", {}) or {}),
        )
