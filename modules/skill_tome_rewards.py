"""Select a learnable tome for class-based event and dungeon rewards."""
from hashlib import sha256


CLASS_SKILL_TOME_MARKER = "tomo_habilidade_classe"


def resolve_class_skill_tome(player, stable_key=""):
    """Return a deterministic, unlearned class tome, or None when unavailable."""
    if not isinstance(player, dict):
        return None

    from modules.game_data.class_evolution import can_player_use_skill
    from modules.game_data.items import ITEMS_DATA
    from modules.game_data.skills import SKILL_DATA

    player_class = str(
        player.get("class") or player.get("class_key") or player.get("classe") or ""
    ).strip()
    if not player_class:
        return None

    learned_ids = set()
    for learned in (player.get("skills"), player.get("skills_desbloqueadas")):
        if isinstance(learned, dict):
            learned_ids.update(str(skill_id) for skill_id in learned)
        elif isinstance(learned, list):
            learned_ids.update(
                str(skill.get("skill_id") or skill.get("id"))
                if isinstance(skill, dict) else str(skill)
                for skill in learned if skill
            )

    candidates = []
    for item_id, meta in ITEMS_DATA.items():
        if not item_id.startswith("tomo_") or meta.get("type") != "skill_book":
            continue
        skill_id = str((meta.get("effects") or {}).get("learn_skill") or "")
        if not skill_id or skill_id in learned_ids or skill_id not in SKILL_DATA:
            continue
        allowed = meta.get("class_req") or SKILL_DATA[skill_id].get("allowed_classes") or []
        if isinstance(allowed, str):
            allowed = [allowed]
        if can_player_use_skill(player_class, allowed):
            candidates.append(item_id)

    if not candidates:
        return None
    candidates.sort()
    identity = str(player.get("_id") or player.get("user_id") or "")
    digest = sha256(f"{stable_key}:{identity}".encode("utf-8")).digest()
    return candidates[int.from_bytes(digest[:8], "big") % len(candidates)]
