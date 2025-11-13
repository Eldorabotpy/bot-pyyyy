# modules/combat/durability.py
from typing import Any, Tuple
from modules import player_manager
import logging

logger = logging.getLogger(__name__)

_WEAPON_SLOTS = ("weapon", "primary_weapon", "arma")
_ARMOR_SLOTS  = ("elmo", "armadura", "calca", "luvas", "botas", "anel", "colar", "brinco")


def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _get_equipped_uid(player_data: dict, slot_names) -> str | None:
    """
    Retorna o uid do item atualmente equipado em qualquer um dos `slot_names`.
    player_data['equipment'] é esperado como dict {slot_name: uid}.
    """
    equip = (player_data or {}).get("equipment", {}) or {}
    for s in slot_names:
        uid = equip.get(s)
        if isinstance(uid, str) and uid:
            return uid
    return None


def _get_unique_inst(player_data: dict, uid: str) -> dict | None:
    """
    Retorna a instância única do inventário (dict) para o uid, ou None.
    Espera-se que player_data['inventory'] seja um dict {uid: instance_dict}.
    """
    if not uid:
        return None
    inv = (player_data or {}).get("inventory", {}) or {}
    inst = inv.get(uid)
    if not isinstance(inst, dict):
        return None
    # verifique se tem base_id para garantir que é item único
    if not inst.get("base_id"):
        return None
    return inst


def _dur_tuple(raw: Any) -> Tuple[int, int]:
    """
    Normaliza diferentes formatos de durabilidade e retorna (current, max).
    Aceita:
      - lista/tuple [current, max]
      - dict {"current": x, "max": y}
      - qualquer outro -> retorna (20, 20) por padrão
    Garante: max >= 1, 0 <= current <= max
    """
    cur, mx = 20, 20

    # extrai mx primeiro para evitar cur > mx depois do clamp
    if isinstance(raw, dict):
        try:
            mx = _to_int(raw.get("max", 20), 20)
            cur = _to_int(raw.get("current", 20), 20)
        except Exception:
            cur, mx = 20, 20
    elif isinstance(raw, (list, tuple)) and len(raw) >= 2:
        try:
            mx = _to_int(raw[1], 20)
            cur = _to_int(raw[0], 20)
        except Exception:
            cur, mx = 20, 20
    else:
        # raw pode ser None ou formato inesperado
        cur, mx = 20, 20

    mx = max(1, mx)
    cur = max(0, min(cur, mx))
    return cur, mx


def consume_durability(player_data: dict, uid: str, amount: int = 1) -> Tuple[int, int, bool]:
    """
    Consome `amount` de durabilidade do item uid no player_data (mutação in-place).
    Retorna (current, max, broke_now).
    - Se o item não existir ou não tiver durabilidade, retorna (0, 0, False).
    - amount é normalizado (int, >=0). Se amount == 0, não altera nada.
    IMPORTANTE: essa função altera player_data['inventory'][uid]['durability'] mas não salva o player.
    O chamador DEVE salvar player_data após as alterações se necessário.
    """
    try:
        amount = max(0, int(amount))
    except Exception:
        amount = 1

    inv = (player_data or {}).get("inventory", {}) or {}
    inst = inv.get(uid)
    if not isinstance(inst, dict):
        return (0, 0, False)

    raw = inst.get("durability")
    cur, mx = _dur_tuple(raw)

    if amount == 0:
        # sem alteração
        return (cur, mx, cur == 0)

    if cur <= 0:
        # já quebrado
        return (0, mx, False)

    new_cur = max(0, cur - amount)
    inst["durability"] = [new_cur, mx]
    broke_now = (cur > 0 and new_cur == 0)
    return (new_cur, mx, broke_now)


def is_weapon_broken(player_data: dict) -> Tuple[bool, str | None, Tuple[int, int]]:
    """
    Retorna (broken?, weapon_uid_or_none, (cur, max))
    """
    w_uid = _get_equipped_uid(player_data, _WEAPON_SLOTS)
    if not w_uid:
        return (False, None, (0, 0))
    inst = _get_unique_inst(player_data, w_uid)
    if not inst:
        return (False, w_uid, (0, 0))
    cur, mx = _dur_tuple(inst.get("durability"))
    return (cur <= 0, w_uid, (cur, mx))


def apply_end_of_battle_wear(player_data: dict, combat_details: dict, log: list) -> bool:
    """
    Aplica 1 ponto de desgaste a TODOS os itens equipados (arma + armadura)
    no final de uma batalha (vitória, derrota ou fuga).

    Retorna True se alguma durabilidade foi alterada (ou item quebrou agora), False caso contrário.

    Observações:
    - Modifica player_data in-place; quem chama deve persistir (save) o player_data.
    - `log` deve ser uma lista; se não for, tentamos transformá-lo em lista ou ignoramos.
    """
    if not isinstance(log, list):
        # não queremos tentar append em algo que não é lista; tentar adaptar/avisar
        try:
            log = list(log)
        except Exception:
            log = []

    changed = False

    # --- Desgaste da Arma ---
    w_uid = _get_equipped_uid(player_data, _WEAPON_SLOTS)
    if w_uid:
        cur, mx, broke_now = consume_durability(player_data, w_uid, 1)
        if cur != mx or broke_now:
            # se cur diminuiu (cur != mx) ou quebrou agora -> houve mudança
            changed = True
        if broke_now:
            log.append(f"⚠️ 𝑺𝒖𝒂 𝒂𝒓𝒎𝒂 quebrou ({cur}/{mx}).")

    # --- Desgaste da Armadura ---
    for slot in _ARMOR_SLOTS:
        uid_to_damage = _get_equipped_uid(player_data, [slot])
        if not uid_to_damage:
            continue
        prev_inst = _get_unique_inst(player_data, uid_to_damage)
        prev_cur, prev_mx = (0, 0)
        if prev_inst:
            prev_cur, prev_mx = _dur_tuple(prev_inst.get("durability"))

        cur, mx, broke_now = consume_durability(player_data, uid_to_damage, 1)
        # Se a inst nao existia, consume_durability retorna (0,0,False) e nao mudou nada.
        # Verifica se houve diminuição real comparando prev_cur -> cur
        if prev_inst and cur != prev_cur:
            changed = True

        if broke_now:
            item_inst = _get_unique_inst(player_data, uid_to_damage)
            item_name = (item_inst or {}).get("display_name", "Seu equipamento")
            log.append(f"⚠️ {item_name} quebrou ({cur}/{mx}).")

    return changed
