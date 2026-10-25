"""Select learnable tomes for event and dungeon rewards."""
from hashlib import sha256


CLASS_SKILL_TOME_MARKER = "tomo_habilidade_classe"


def resolve_class_skill_tome(player, stable_key=""):
    """Prefer an unlearned tome for another class, making event drops tradable."""
    if not isinstance(player, dict):
        return None

    from modules.game_data.items import ITEMS_DATA
    from modules.game_data.skills import SKILL_DATA
    from modules.skill_progression import (
        is_skill_tome_learnable,
        player_has_skill,
        skill_is_available_to_class,
    )

    player_class = str(
        player.get("class") or player.get("class_key") or player.get("classe") or ""
    ).strip()
    candidates = []
    other_class_candidates = []
    for item_id, meta in ITEMS_DATA.items():
        if not item_id.startswith("tomo_") or meta.get("type") != "skill_book":
            continue
        skill_id = str((meta.get("effects") or {}).get("learn_skill") or "")
        if (
            not skill_id
            or skill_id not in SKILL_DATA
            or player_has_skill(player, skill_id)
            or not is_skill_tome_learnable(skill_id)
            or meta.get("skill_tome_purpose", "learn") != "learn"
        ):
            continue
        allowed = meta.get("class_req") or SKILL_DATA[skill_id].get("allowed_classes") or []
        if isinstance(allowed, str):
            allowed = [allowed]
        candidates.append(item_id)
        if player_class and not skill_is_available_to_class(player_class, skill_id, allowed):
            other_class_candidates.append(item_id)

    # Prefer a tome the character cannot learn. If those are exhausted, fall
    # back to any unlearned ordinary tome so an event reward is not wasted.
    if other_class_candidates:
        candidates = other_class_candidates
    if not candidates:
        return None
    candidates.sort()
    identity = str(player.get("_id") or player.get("user_id") or "")
    digest = sha256(f"{stable_key}:{identity}".encode("utf-8")).digest()
    return candidates[int.from_bytes(digest[:8], "big") % len(candidates)]
