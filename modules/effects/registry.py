# modules/effects/registry.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal

# O engine vai interpretar esse registry.
EffectKind = Literal["buff", "debuff"]

# Chaves de modificadores padronizadas (o engine soma e aplica)
# Sugestão: multipliers sempre em float (ex.: 0.30 = +30% / -30%)
MOD_DAMAGE_DEALT_MULT = "damage_dealt_mult"
MOD_DAMAGE_TAKEN_MULT = "damage_taken_mult"
MOD_HEAL_RECEIVED_MULT = "heal_received_mult"
MOD_CANNOT_ACT = "cannot_act"
MOD_SHIELD_FLAT = "shield_flat"  # absorção em HP (flat)

# Para DOT/HOT (tick por turno)
TICK_DAMAGE = "tick_damage"
TICK_HEAL = "tick_heal"


@dataclass
class EffectTemplate:
    """
    Template declarativo de um efeito.
    O EffectEngine decide como aplicar stacks/duração, e como processar eventos.
    """
    effect_id: str
    name: str
    kind: EffectKind

    tags: List[str] = field(default_factory=list)

    # Stack rules
    max_stacks: int = 1
    stack_mode: str = "refresh_duration"  # refresh_duration | add_duration | increase_potency | none
    priority: int = 100                   # menor roda primeiro

    dispellable: bool = True
    exclusive_group: Optional[str] = None  # ex.: "stance", "aura"

    # Modifiers: aplicado como "sempre ativo" enquanto o efeito existe
    modifiers: Dict[str, Any] = field(default_factory=dict)

    # Tick behavior: aplicado em eventos (ex.: turno start/end)
    # Ex.: {"tick_damage": {"at": "on_turn_start", "type": "bleed"}}
    tick: Dict[str, Any] = field(default_factory=dict)

    # Observações/descrição (UI)
    desc: str = ""


# =============================================================================
# REGISTRY PRINCIPAL
# =============================================================================

EFFECTS: Dict[str, EffectTemplate] = {
    # 1) BLEED (DOT físico por turno)
    "bleed": EffectTemplate(
        effect_id="bleed",
        name="Sangramento",
        kind="debuff",
        tags=["dot", "bleed", "physical"],
        max_stacks=5,
        stack_mode="increase_potency",
        priority=50,
        dispellable=True,
        tick={
            TICK_DAMAGE: {
                "at": "on_turn_start",     # quando aplicar o tick
                "damage_type": "bleed",    # tipo do dano
                # fórmula base: engine vai calcular: base + (potency * stacks)
                # você pode calibrar no engine
                "base": 0,
                "per_stack": 1,
            }
        },
        desc="Recebe dano físico por turno. Stack aumenta o dano.",
    ),

    # 2) POISON (DOT por turno)
    "poison": EffectTemplate(
        effect_id="poison",
        name="Veneno",
        kind="debuff",
        tags=["dot", "poison"],
        max_stacks=10,
        stack_mode="increase_potency",
        priority=60,
        dispellable=True,
        tick={
            TICK_DAMAGE: {
                "at": "on_turn_start",
                "damage_type": "poison",
                "base": 0,
                "per_stack": 1,
            }
        },
        desc="Recebe dano por turno. Stack aumenta o dano.",
    ),

    # 3) REGEN (HOT por turno)
    "regen": EffectTemplate(
        effect_id="regen",
        name="Regeneração",
        kind="buff",
        tags=["hot", "regen"],
        max_stacks=3,
        stack_mode="refresh_duration",
        priority=80,
        dispellable=True,
        tick={
            TICK_HEAL: {
                "at": "on_turn_start",
                "base": 1,
                "per_stack": 1,
            }
        },
        desc="Recupera vida por turno.",
    ),

    # 4) STUN (bloqueia ação)
    "stun": EffectTemplate(
        effect_id="stun",
        name="Atordoamento",
        kind="debuff",
        tags=["control", "stun"],
        max_stacks=1,
        stack_mode="refresh_duration",
        priority=10,  # roda cedo para travar ação
        dispellable=True,
        modifiers={
            MOD_CANNOT_ACT: True
        },
        desc="Não pode agir enquanto durar.",
    ),

    # 5) SHIELD (absorve dano)
    "shield": EffectTemplate(
        effect_id="shield",
        name="Escudo",
        kind="buff",
        tags=["shield"],
        max_stacks=1,
        stack_mode="refresh_duration",
        priority=20,
        dispellable=True,
        modifiers={
            # O valor real do escudo virá do potency (ex.: 25 = 25 de escudo)
            MOD_SHIELD_FLAT: True
        },
        desc="Absorve dano antes de reduzir HP.",
    ),

    # 6) HEAL REDUCTION (reduz cura recebida)
    "heal_reduction": EffectTemplate(
        effect_id="heal_reduction",
        name="Ferida Profunda",
        kind="debuff",
        tags=["antiheal", "wound"],
        max_stacks=1,
        stack_mode="refresh_duration",
        priority=30,
        dispellable=True,
        modifiers={
            # potency será interpretado como redução (ex.: 0.30 = -30%)
            MOD_HEAL_RECEIVED_MULT: -0.30
        },
        desc="Reduz a cura recebida.",
    ),
}


def get_effect_template(effect_id: str) -> Optional[EffectTemplate]:
    return EFFECTS.get(effect_id)
