# modules/skills/skill_canonical_adapter.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, List


CANON_VERSION = 1


def _as_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _as_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _pick(d: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    for k in keys:
        if k in d:
            return d[k]
    return default


def _ensure_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _normalize_damage_effects(effects: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converte chaves de dano legadas -> canônicas.
    Retorna dict "damage" canônico (ou {} se não houver).
    """
    dmg_mult = _pick(effects, "damage_multiplier", "damage_mult", default=None)
    dmg_scale = _pick(effects, "damage_scale", default=None)

    # Alguns usos seus: damage_scale (ex.: 2.5x) é equivalente ao mult
    mult = None
    if dmg_mult is not None:
        mult = _as_float(dmg_mult, 1.0)
    elif dmg_scale is not None:
        mult = _as_float(dmg_scale, 1.0)

    # type
    dmg_type = _pick(effects, "damage_type", default="physical")
    dmg_type = dmg_type if dmg_type in ("physical", "magic", "true") else "physical"

    # penetração
    armor_pen = _pick(effects, "defense_penetration", "armor_penetration", default=0.0)
    armor_pen = _clamp01(_as_float(armor_pen, 0.0))

    # hit garantido / cannot dodge
    cannot_dodge = bool(_pick(effects, "guaranteed_hit", "cannot_be_dodged", default=False))

    # bônus de crit neste golpe (legado: bonus_crit_chance)
    bonus_crit = _pick(effects, "bonus_crit_chance", default=None)
    bonus_crit = _clamp01(_as_float(bonus_crit, 0.0)) if bonus_crit is not None else 0.0

    if mult is None and (armor_pen == 0.0 and not cannot_dodge and bonus_crit == 0.0):
        return {}

    return {
        "mult": _as_float(mult, 1.0) if mult is not None else 1.0,
        "type": dmg_type,
        "armor_pen": armor_pen,
        "cannot_dodge": cannot_dodge,
        "bonus_crit": bonus_crit,
    }


def _normalize_multi_hit(effects: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converte multi-hit legado -> canônico.
    """
    mh_min = _pick(effects, "multi_hit_min", default=None)
    mh_max = _pick(effects, "multi_hit_max", default=None)
    if mh_min is None or mh_max is None:
        return {}

    per_hit_mult = _pick(effects, "per_hit_mult", "damage_multiplier", "damage_mult", default=1.0)

    out = {
        "min": _as_int(mh_min, 1),
        "max": _as_int(mh_max, 1),
        "per_hit_mult": _as_float(per_hit_mult, 1.0),
        "on_hit": [],  # lista de efeitos por hit (canônico)
    }

    # Alguns de seus multi-hit lendários têm chance_on_hit (ex.: bleed)
    coh = _ensure_dict(effects.get("chance_on_hit"))
    if coh:
        dot = _normalize_chance_on_hit_to_on_hit(coh)
        if dot:
            out["on_hit"].append(dot)

    return out


def _normalize_chance_on_hit_to_on_hit(coh: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converte chance_on_hit legado (dot) -> item canônico em multi_hit.on_hit
    ou em passiva on_hit (quando multi-hit não existe).
    """
    if coh.get("effect") != "dot":
        return {}

    chance = _clamp01(_as_float(coh.get("chance", 0.0), 0.0))
    duration = _as_int(coh.get("duration_turns", 3), 3)

    # scale/value como você usa: scale="attack", value=0.10 => 10% ATK por turno
    scale = coh.get("scale", "attack")
    value = _as_float(coh.get("value", 0.0), 0.0)

    stacks = _as_int(coh.get("stack", 1), 1)
    stacks = max(1, stacks)

    # Se você não especificar, por padrão assume poison; mas para Dança das Mil Lâminas
    # você quer bleed (a gente decide pelo skill_id fora, se quiser).
    dot_id = coh.get("dot_id")  # opcional, se você quiser colocar explicitamente
    if not dot_id:
        dot_id = "poison"

    out = {
        "kind": "dot",
        "id": dot_id,
        "chance": chance,
        "duration_turns": duration,
        "stacks": stacks,
        "params": {
            "scale": scale,
            "pct": value,
            "damage_type": coh.get("damage_type", "physical"),
        },
    }

    # Debuff adicional (ex.: -DEF por X turnos)
    deb = _ensure_dict(coh.get("debuff"))
    if deb:
        out["extra_apply"] = [{
            "kind": "debuff",
            "id": "stat_debuff",
            "duration_turns": _as_int(deb.get("duration_turns", duration), duration),
            "params": {
                "stat": deb.get("stat"),
                "mult": _as_float(deb.get("value", 0.0), 0.0),
            }
        }]

    return out


def _normalize_execute(effects: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converte bônus por alvo low HP -> canônico execute.
    """
    a = _ensure_dict(effects.get("bonus_damage_if_low_hp_target"))
    b = _ensure_dict(effects.get("bonus_damage_vs_low_hp"))
    src = a if a else b
    if not src:
        return {}

    hp_lt = src.get("threshold", src.get("hp_threshold", None))
    bonus = src.get("bonus", src.get("bonus_mult", None))

    if hp_lt is None or bonus is None:
        return {}

    reset_on_kill = _as_float(effects.get("cooldown_reduction_on_kill", 0.0), 0.0) >= 1.0

    return {
        "hp_lt": _clamp01(_as_float(hp_lt, 0.0)),
        "bonus_mult": _as_float(bonus, 0.0),
        "reset_cd_on_kill": bool(reset_on_kill),
    }


def _normalize_passives(effects: Dict[str, Any], *, skill_id: str) -> List[Dict[str, Any]]:
    """
    Converte passivas legadas do Assassino -> lista canônica de regras.
    """
    rules: List[Dict[str, Any]] = []

    # 1) first_hit_bonus (Emboscada)
    fh = _ensure_dict(effects.get("first_hit_bonus"))
    if fh:
        rules.append({
            "trigger": "first_hit",
            "apply": [{
                "kind": "buff",
                "id": "first_hit_bonus",
                "duration_turns": 9999,  # consumível via flag no combate
                "params": {
                    "damage_mult": _as_float(fh.get("damage_mult", 0.0), 0.0),
                    "crit_chance_flat": _clamp01(_as_float(fh.get("crit_chance_flat", 0.0), 0.0)),
                    "armor_pen": _clamp01(_as_float(fh.get("armor_penetration", 0.0), 0.0)),
                }
            }]
        })

    # 2) stat_add_mult (Foco)
    sa = _ensure_dict(effects.get("stat_add_mult"))
    if sa:
        rules.append({
            "trigger": "always",
            "apply": [{
                "kind": "buff",
                "id": "stat_add_mult",
                "duration_turns": 9999,
                "params": {
                    "crit_chance_flat": _clamp01(_as_float(sa.get("crit_chance_flat", 0.0), 0.0)),
                    "crit_damage_mult": _as_float(sa.get("crit_damage_mult", 0.0), 0.0),
                }
            }]
        })

    # 3) on_crit_buff (Foco épico/lendário)
    oc = _ensure_dict(effects.get("on_crit_buff"))
    if oc:
        # você usa: {"effect":"armor_penetration","value":0.15,"cannot_be_dodged":True}
        rules.append({
            "trigger": "on_crit",
            "apply": [{
                "kind": "buff",
                "id": "on_crit_buff",
                "duration_turns": 1,
                "params": {
                    "effect": oc.get("effect"),
                    "value": _as_float(oc.get("value", 0.0), 0.0),
                    "cannot_dodge": bool(oc.get("cannot_be_dodged", False)),
                }
            }]
        })

    # 4) on_kill_buff (Aspecto da Noite)
    ok = _ensure_dict(effects.get("on_kill_buff"))
    if ok:
        # invisibility + on_exit_buff
        invis = ok.get("effect", "invisibility")
        dur = _as_int(ok.get("duration_turns", 1), 1)
        rule = {
            "trigger": "on_kill",
            "apply": [{
                "kind": "state",
                "id": invis,
                "duration_turns": dur,
                "params": {}
            }]
        }
        on_exit = _ensure_dict(ok.get("on_exit_buff"))
        if on_exit:
            # guaranteed_crit ou multi_stat_buff
            rule["on_exit_apply"] = [{
                "kind": "buff" if on_exit.get("effect") != "guaranteed_crit" else "state",
                "id": on_exit.get("effect"),
                "duration_turns": _as_int(on_exit.get("duration_turns", 1), 1),
                "params": {
                    "buffs": _ensure_dict(on_exit.get("buffs")),
                }
            }]
        rules.append(rule)

    # 5) chance_on_hit (toxinas / bleed por hit)
    coh = _ensure_dict(effects.get("chance_on_hit"))
    if coh and coh.get("effect") == "dot":
        dot = _normalize_chance_on_hit_to_on_hit(coh)
        if dot:
            # definir dot_id por skill quando não vier explícito
            # - dança das mil lâminas lendária: bleed
            # - toxinas/ninja: poison
            if skill_id == "assassino_active_dance_of_a_thousand_cuts":
                dot["id"] = "bleed"
            else:
                dot["id"] = "poison"

            rules.append({
                "trigger": "on_hit",
                "chance": dot.get("chance", 0.0),
                "apply": [dot],
            })

    return rules


def adapt_skill_to_canon(
    *,
    skills_db: Dict[str, Any],
    skill_id: str,
    rarity: str,
) -> Dict[str, Any]:
    """
    Converte a skill do formato atual (skills.py) para um formato canônico.
    Não altera nada no banco; é só transformação em memória.
    """
    s = _ensure_dict(skills_db.get(skill_id))
    if not s:
        return {"_canon_v": CANON_VERSION, "id": skill_id, "missing": True}

    rarity = rarity or "comum"
    reffs = _ensure_dict(s.get("rarity_effects", {}))
    rr = _ensure_dict(reffs.get(rarity)) or _ensure_dict(reffs.get("comum"))
    effects = _ensure_dict(rr.get("effects", {}))

    out: Dict[str, Any] = {
        "_canon_v": CANON_VERSION,
        "id": skill_id,
        "display_name": s.get("display_name", skill_id),
        "type": s.get("type", "active"),
        "allowed_classes": s.get("allowed_classes", []),
        "mana_cost": _as_int(rr.get("mana_cost", 0), 0),
        "cooldown_turns": _as_int(effects.get("cooldown_turns", 0), 0),
        "effects": {
            # canônicos
            "damage": _normalize_damage_effects(effects),
            "multi_hit": _normalize_multi_hit(effects),
            "execute": _normalize_execute(effects),
            "passives": _normalize_passives(effects, skill_id=skill_id),
        },
        # manter legado para debug/auditoria
        "_legacy": {
            "rarity": rarity,
            "raw_effects": effects,
        }
    }

    # Limpeza: se multi_hit vazio, remove
    if not out["effects"]["multi_hit"]:
        out["effects"].pop("multi_hit", None)
    # Limpeza: se damage vazio, remove
    if not out["effects"]["damage"]:
        out["effects"].pop("damage", None)
    # Limpeza: se execute vazio, remove
    if not out["effects"]["execute"]:
        out["effects"].pop("execute", None)
    # Limpeza: se passives vazio, remove
    if not out["effects"]["passives"]:
        out["effects"].pop("passives", None)

    return out
