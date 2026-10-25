"""Shared rules for class skills, tomes, and evolution unlocks."""

from __future__ import annotations


Q6_INITIAL_SKILLS_BY_CLASS = {
    "guerreiro": "guerreiro_corte_perfurante",
    "mago": "mago_bola_de_fogo",
    "cacador": "cacador_flecha_precisa",
    "assassino": "assassino_ataque_furtivo",
    "monge": "monge_rajada_de_punhos",
    "samurai": "samurai_corte_iaijutsu",
    "berserker": "berserker_golpe_selvagem",
    "curandeiro": "curandeiro_chama_sagrada",
    "bardo": "bardo_nota_cortante",
    "necromante": "necromante_levantar_esqueletos",
}

Q6_INITIAL_SKILLS = frozenset(Q6_INITIAL_SKILLS_BY_CLASS.values())


def evolution_skill_targets() -> dict[str, str]:
    """Map each evolution-granted skill to the class that unlocks it."""
    from modules.game_data.class_evolution import EVOLUTIONS

    targets = {}
    for evolution_path in EVOLUTIONS.values():
        for option in evolution_path:
            target_class = str(option.get("to") or "").strip().lower()
            for skill_id in option.get("unlocks_skills", []) or []:
                if skill_id and target_class:
                    targets[str(skill_id)] = target_class
    return targets


def get_evolution_skill_target(skill_id: str) -> str | None:
    return evolution_skill_targets().get(str(skill_id or ""))


def is_evolution_skill(skill_id: str) -> bool:
    # The prefix is a fail-closed guard if a future evo skill is accidentally
    # omitted from the evolution tree's unlock list.
    return str(skill_id or "").startswith("evo_") or get_evolution_skill_target(skill_id) is not None


def is_q6_initial_skill(skill_id: str) -> bool:
    return str(skill_id or "") in Q6_INITIAL_SKILLS


def is_skill_tome_learnable(skill_id: str) -> bool:
    """Only ordinary class tomes teach skills; Q6 and evo skills have gates."""
    return bool(skill_id) and not is_evolution_skill(skill_id) and not is_q6_initial_skill(skill_id)


def skill_is_available_to_class(player_class: str, skill_id: str, allowed_classes=None) -> bool:
    """Check class ancestry and, for evo skills, the exact evolution tier."""
    from modules.game_data.class_evolution import can_player_use_skill, get_class_ancestry

    player_class = str(player_class or "").strip().lower()
    target_class = get_evolution_skill_target(skill_id)
    if is_evolution_skill(skill_id):
        if not target_class or target_class not in get_class_ancestry(player_class):
            return False

    if allowed_classes is None:
        from modules.game_data.skills import SKILL_DATA
        allowed_classes = (SKILL_DATA.get(skill_id) or {}).get("allowed_classes") or []
    return can_player_use_skill(player_class, allowed_classes)


def player_has_skill(player: dict, skill_id: str) -> bool:
    for field in ("skills", "skills_desbloqueadas"):
        skills = player.get(field)
        if isinstance(skills, dict) and skill_id in skills:
            return True
        if isinstance(skills, list) and any(
            (str(item.get("skill_id") or item.get("id") or "") if isinstance(item, dict) else str(item)) == skill_id
            for item in skills
        ):
            return True
    return False
