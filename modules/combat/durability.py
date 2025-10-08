# modules/combat/durability.py
from modules import player_manager

_WEAPON_SLOTS = ("weapon", "primary_weapon", "arma")
_ARMOR_SLOTS  = ("elmo", "armadura", "calca", "luvas", "botas", "anel", "colar", "brinco")

def _get_equipped_uid(player_data: dict, slot_names) -> str | None:
    equip = (player_data or {}).get("equipment", {}) or {}
    for s in slot_names:
        uid = equip.get(s)
        if isinstance(uid, str) and uid:
            return uid
    return None

def _get_unique_inst(player_data: dict, uid: str) -> dict | None:
    if not uid: return None
    inv = (player_data or {}).get("inventory", {}) or {}
    inst = inv.get(uid)
    return inst if isinstance(inst, dict) and inst.get("base_id") else None

def _dur_tuple(raw) -> tuple[int, int]:
    cur, mx = 20, 20
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        try:
            cur, mx = int(raw[0]), int(raw[1])
        except Exception: pass
    elif isinstance(raw, dict):
        try:
            cur, mx = int(raw.get("current", 20)), int(raw.get("max", 20))
        except Exception: pass
    cur = max(0, min(cur, mx))
    mx = max(1, mx)
    return cur, mx

def consume_durability(player_data: dict, uid: str, amount: int = 1) -> tuple[int, int, bool]:
    inv = player_data.get("inventory", {}) or {}
    inst = inv.get(uid)
    if not isinstance(inst, dict): return (0, 0, False)

    cur, mx = _dur_tuple(inst.get("durability"))
    if cur <= 0: return (0, mx, False)

    cur = max(0, cur - int(amount))
    inst["durability"] = [cur, mx]
    return (cur, mx, cur == 0)

def is_weapon_broken(player_data: dict) -> tuple[bool, str | None, tuple[int, int]]:
    w_uid = _get_equipped_uid(player_data, _WEAPON_SLOTS)
    if not w_uid: return (False, None, (0, 0))
    inst = _get_unique_inst(player_data, w_uid)
    if not inst: return (False, None, (0, 0))
    cur, mx = _dur_tuple(inst.get("durability"))
    return (cur <= 0, w_uid, (cur, mx))

def apply_end_of_battle_wear(player_data: dict, combat_details: dict, log: list[str]) -> bool:
    changed = False
    if bool(combat_details.get("used_weapon")):
        w_uid = _get_equipped_uid(player_data, _WEAPON_SLOTS)
        if w_uid:
            cur, mx, broke_now = consume_durability(player_data, w_uid, 1)
            changed = True
            if broke_now:
                log.append(f"⚠️ 𝑺𝒖𝒂 𝒂𝒓𝒎𝒂 𝒒𝒖𝒆𝒃𝒓𝒐𝒖 ({cur}/{mx}).")

    if bool(combat_details.get("took_damage")):
        for slot in _ARMOR_SLOTS:
            uid_to_damage = _get_equipped_uid(player_data, [slot])
            if uid_to_damage:
                cur, mx, broke_now = consume_durability(player_data, uid_to_damage, 1)
                changed = True
                if broke_now:
                    item_inst = _get_unique_inst(player_data, uid_to_damage)
                    item_name = (item_inst or {}).get("display_name", "Sua armadura")
                    log.append(f"⚠️ {item_name} 𝒒𝒖𝒆𝒃𝒓𝒐𝒖 ({cur}/{mx}).")
    
    return changed