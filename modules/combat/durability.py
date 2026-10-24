# modules/player/durability.py (ou modules/combat/durability.py dependendo da sua pasta)
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
    """Lê a durabilidade e retorna (atual, maxima)."""
    cur, mx = 20, 20
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        try:
            cur, mx = int(raw[0]), int(raw[1])
        except Exception: pass
    elif isinstance(raw, dict):
        try:
            cur, mx = int(raw.get("current", 20)), int(raw.get("max", 20))
        except Exception: pass
    # Tratamento caso venha apenas um inteiro (ex: legado)
    elif isinstance(raw, (int, float)):
        cur = int(raw)
        
    cur = max(0, min(cur, mx))
    mx = max(1, mx)
    return cur, mx

# --- NOVA FUNÇÃO IMPORTANTE ---
def is_item_broken(item_inst: dict) -> bool:
    """Retorna True se o item estiver com durabilidade 0."""
    if not item_inst: 
        return False
    dur_data = item_inst.get("durability")
    # Se não tiver durabilidade definida, assumimos que é indestrutível (False)
    if dur_data is None:
        return False
        
    cur, _ = _dur_tuple(dur_data)
    return cur <= 0
# ------------------------------

def consume_durability(player_data: dict, uid: str, amount: int = 1) -> tuple[int, int, bool]:
    inv = player_data.get("inventory", {}) or {}
    inst = inv.get(uid)
    if not isinstance(inst, dict): return (0, 0, False)

    raw_durability = inst.get("durability")
    if raw_durability is None:
        return (0, 0, False)

    cur, mx = _dur_tuple(raw_durability)
    if mx <= 0:
        return (0, 0, False)
    if cur <= 0: return (0, mx, False)

    cur = max(0, cur - max(1, int(amount or 1)))
    inst["durability"] = [cur, mx]
    return (cur, mx, cur == 0)

def is_weapon_broken(player_data: dict) -> tuple[bool, str | None, tuple[int, int]]:
    w_uid = _get_equipped_uid(player_data, _WEAPON_SLOTS)
    if not w_uid: return (False, None, (0, 0))
    inst = _get_unique_inst(player_data, w_uid)
    if not inst: return (False, None, (0, 0))
    
    if is_item_broken(inst):
        cur, mx = _dur_tuple(inst.get("durability"))
        return (True, w_uid, (cur, mx))
        
    return (False, None, (0, 0))

def apply_equipment_combat_wear(player_data: dict, amount: int = 1, log: list[str] | None = None) -> dict:
    """Aplica uma única cobrança de desgaste a cada equipamento equipado."""
    processed_uids = set()
    inventory = player_data.get("inventory", {}) or {}
    amount = max(1, int(amount or 1))
    result = {"alterados": [], "quebrados": [], "mensagens": []}
    log = log if isinstance(log, list) else []

    def gastar_equipamento(uid: str, slot: str):
        if not uid or uid in processed_uids:
            return

        item_inst = inventory.get(uid)
        if not isinstance(item_inst, dict) or item_inst.get("durability") is None:
            return

        cur, mx = _dur_tuple(item_inst.get("durability"))
        if mx <= 0 or cur <= 0:
            return

        processed_uids.add(uid)
        cur, mx, broke_now = consume_durability(player_data, uid, amount)
        nome = (
            item_inst.get("display_name")
            or item_inst.get("nome")
            or str(item_inst.get("base_id") or uid).replace("_", " ").title()
        )
        result["alterados"].append({
            "slot": slot,
            "uid": uid,
            "nome": nome,
            "durability": item_inst.get("durability"),
        })

        if broke_now:
            item_quebrado = {"slot": slot, "uid": uid, "nome": nome}
            result["quebrados"].append(item_quebrado)
            mensagem = f"⚠️ {nome} quebrou ({cur}/{mx})."
            result["mensagens"].append(mensagem)
            log.append(mensagem)
    
    # --- Desgaste da Arma ---
    w_uid = _get_equipped_uid(player_data, _WEAPON_SLOTS)
    gastar_equipamento(w_uid, "arma")

    # --- Desgaste da Armadura ---
    for slot in _ARMOR_SLOTS:
        uid_to_damage = _get_equipped_uid(player_data, [slot])
        gastar_equipamento(uid_to_damage, slot)

    player_data["inventory"] = inventory
    return result


def apply_combat_end_wear_once(
    player_data: dict,
    combat_state: dict,
    participant_id: str,
    amount: int = 1,
) -> dict:
    """Aplica o desgaste de encerramento uma vez por participante e encontro."""
    applied_players = combat_state.setdefault("_durability_wear_applied_players", [])
    participant_key = str(participant_id)
    if participant_key in applied_players:
        return {"alterados": [], "quebrados": [], "mensagens": [], "ja_aplicado": True}

    result = apply_equipment_combat_wear(player_data, amount=amount)
    applied_players.append(participant_key)
    result["ja_aplicado"] = False
    return result


def apply_end_of_battle_wear(player_data: dict, combat_details: dict, log: list[str]) -> bool:
    """Compatibilidade com chamadas antigas que só precisam saber se houve desgaste."""
    result = apply_equipment_combat_wear(player_data, amount=1, log=log)
    return bool(result["alterados"])
