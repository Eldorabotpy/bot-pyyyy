# modules/skills/skill_effects_adapter.py

from typing import Dict, Any, List

from modules.effects.engine import apply_effect
from modules.effects.models import EVENT_ON_HEAL, CombatContext
from modules.effects.engine import dispatch
from modules.game_data.skills import get_skill_data_with_rarity


def apply_skill_effects(
    *,
    skill_id: str,
    skill_info: Dict[str, Any],
    player_id: int,
    player_stats: Dict[str, Any],
    battle_cache: Dict[str, Any],
    monster_stats: Dict[str, Any],
    log: List[str],
    combat_result: Dict[str, Any] | None = None,
):

    """
    Converte skill_info["effects"] em efeitos universais (buff/debuff).
    NÃO calcula dano base — isso continua no combat_engine.
    """

    effects = skill_info.get("effects", {})
    if not effects:
        return

    # =========================
    # DEBUFFS NO MONSTRO
    # =========================

    if "apply_bleed" in effects:
        cfg = effects["apply_bleed"]
        apply_effect(
            monster_stats,
            "bleed",
            source_id=str(player_id),
            source_type="skill",
            duration_turns=cfg.get("duration", 3),
            stacks=cfg.get("stacks", 1),
            potency=cfg.get("potency", 1.0),
        )
        log.append("🩸 O inimigo está sangrando!")

    if "apply_poison" in effects:
        cfg = effects["apply_poison"]
        apply_effect(
            monster_stats,
            "poison",
            source_id=str(player_id),
            source_type="skill",
            duration_turns=cfg.get("duration", 3),
            stacks=cfg.get("stacks", 1),
            potency=cfg.get("potency", 1.0),
        )
        log.append("☠️ O inimigo foi envenenado!")

    if "apply_stun" in effects:
        cfg = effects["apply_stun"]
        apply_effect(
            monster_stats,
            "stun",
            source_id=str(player_id),
            source_type="skill",
            duration_turns=cfg.get("duration", 1),
        )
        log.append("💫 O inimigo ficou atordoado!")

    if "apply_heal_reduction" in effects:
        cfg = effects["apply_heal_reduction"]
        apply_effect(
            monster_stats,
            "heal_reduction",
            source_id=str(player_id),
            source_type="skill",
            duration_turns=cfg.get("duration", 2),
            potency=cfg.get("potency", 1.0),
        )
        log.append("🩹 Ferida profunda aplicada!")

    # =========================
    # BUFFS NO JOGADOR
    # =========================

    if "grant_shield" in effects:
        cfg = effects["grant_shield"]
        shield_value = int(
            cfg.get("value", 0)
            or player_stats.get("max_hp", 100) * cfg.get("percent_max_hp", 0)
        )

        apply_effect(
            battle_cache,
            "shield",
            source_id=str(player_id),
            source_type="skill",
            duration_turns=cfg.get("duration", 2),
            potency=shield_value,
        )
        log.append(f"🛡️ Escudo ativo ({shield_value})!")

    if "apply_regen" in effects:
        cfg = effects["apply_regen"]
        apply_effect(
            battle_cache,
            "regen",
            source_id=str(player_id),
            source_type="skill",
            duration_turns=cfg.get("duration", 3),
            stacks=cfg.get("stacks", 1),
            potency=cfg.get("potency", 1.0),
        )
        log.append("🌱 Regeneração ativada!")

        # =========================
    # PROC ON HIT (Assassino: veneno/sangramento)
    # =========================
    if "chance_on_hit" in effects:
        cfg = effects["chance_on_hit"] or {}
        chance = float(cfg.get("chance", 0.0))
        duration = int(cfg.get("duration_turns", 3))
        stacks = int(cfg.get("stack", 1) or 1)
        value = float(cfg.get("value", 0.0))  # ex.: 0.10 = 10% ATK

        # Quantidade de "tentativas" = hits (se combat_engine informar), senão 1
        hits = 1
        if combat_result and isinstance(combat_result, dict):
            hits = int(combat_result.get("num_hits", 1) or 1)


        # Determinar qual DOT aplicar:
        # - Assassino "toxinas" / "artes venenosas" => poison
        # - Dança das Mil Lâminas (lendária) => bleed
        dot_id = str(cfg.get("dot_id", "poison"))

        # Dano por tick: % do ATK do jogador
        atk = int(player_stats.get("attack", 0))
        dot_tick = max(1, int(atk * value)) if value > 0 else 1

        import random
        procs = 0
        for _ in range(max(1, hits)):
            if random.random() < chance:
                procs += 1

        if procs > 0:
            apply_effect(
                monster_stats,
                dot_id,
                source_id=str(player_id),
                source_type="skill",
                duration_turns=duration,
                stacks=min(stacks, procs) if stacks > 1 else 1,
                potency=1.0,
                meta={"dot_tick": dot_tick},
            )
            if dot_id == "poison":
                log.append("☠️ O inimigo foi envenenado!")
            else:
                log.append("🩸 O inimigo está sangrando!")

def apply_on_hit_passives(
    *,
    player_data: Dict[str, Any],
    player_stats: Dict[str, Any],
    battle_cache: Dict[str, Any],
    monster_stats: Dict[str, Any],
    log: List[str],
    combat_result: Dict[str, Any] | None = None,
) -> None:
    """
    Aplica SOMENTE passivas com effects["chance_on_hit"].
    Não aplica skills ativas.
    """
    skills = (player_data.get("skills") or {})
    if not skills:
        return

    for sid in list(skills.keys()):
        try:
            s_info = get_skill_data_with_rarity(player_data, sid)
        except Exception:
            s_info = None

        if not s_info:
            continue
        if s_info.get("type") != "passive":
            continue

        eff = (s_info.get("effects") or {})
        if "chance_on_hit" not in eff:
            continue

        # Reaproveita o pipeline existente
        apply_skill_effects(
            skill_id=sid,
            skill_info=s_info,
            player_id=int(player_data.get("player_id", 0) or 0),
            player_stats=player_stats,
            battle_cache=battle_cache,
            monster_stats=monster_stats,
            log=log,
            combat_result=combat_result,
        )
