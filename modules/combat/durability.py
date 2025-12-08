# modules/player/durability.py (CORRIGIDO E ADICIONADO REPARO)
from modules import player_manager

_WEAPON_SLOTS = ("weapon", "primary_weapon", "arma")
_ARMOR_SLOTS  = ("elmo", "armadura", "calca", "luvas", "botas", "anel", "colar", "brinco")

# --- NOVO: ID do Pergaminho de Reparo ---
REPAIR_SCROLL_ID = "pergaminho_reparo"
# ----------------------------------------

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

# --- FUNÇÃO DE REPARO CENTRAL (USADA PELA FORJA E PELO PERGAMINHO) ---
def _restore_item_durability_to_max(item_inst: dict) -> bool:
    """Restaura a durabilidade de uma instância de item equipada para o máximo."""
    if not item_inst or item_inst.get("durability") is None:
        return False

    cur, mx = _dur_tuple(item_inst.get("durability"))
    
    if cur < mx:
        item_inst["durability"] = [mx, mx]
        return True
        
    return False

# --- FUNÇÃO DE VERIFICAÇÃO (MANTIDA) ---
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

# --- FUNÇÃO DE REPARO TOTAL (USO DO PERGAMINHO) ---
async def repair_all_equipped_with_scroll(player_data: dict) -> str:
    """
    Restaura a durabilidade de todos os equipamentos equipados, consumindo 1 Pergaminho de Reparo.
    """
    scroll_quantity = 1
    
    # 1. VERIFICA E CONSUME O PERGAMINHO
    current_scrolls = player_data.get("inventory", {}).get(REPAIR_SCROLL_ID, 0)
    if current_scrolls < scroll_quantity:
        return f"Você precisa de {scroll_quantity}x Pergaminho de Reparo para consertar seus equipamentos!"
        
    if not player_manager.remove_item_from_inventory(player_data, REPAIR_SCROLL_ID, scroll_quantity):
        return "⚠️ Erro ao consumir o pergaminho. Tente novamente."

    # 2. APLICA O REPARO EM TODOS OS ITENS EQUIPADOS
    repaired_count = 0
    all_slots = list(_WEAPON_SLOTS) + list(_ARMOR_SLOTS)

    for slot in all_slots:
        w_uid = _get_equipped_uid(player_data, [slot])
        inst = _get_unique_inst(player_data, w_uid)
        
        if _restore_item_durability_to_max(inst):
            repaired_count += 1
            
    # 3. SALVA E RETORNA
    user_id = player_data.get('user_id')
    if user_id:
        await player_manager.save_player_data(user_id, player_data)
        
    if repaired_count > 0:
        return f"✨ Durabilidade de {repaired_count} item(s) restaurada para 100% com 1 Pergaminho de Reparo!"
    else:
        # Se consumiu o pergaminho, mas não havia nada para reparar.
        return "Nenhum item equipado precisava de reparo. O pergaminho foi consumido."
# ----------------------------------------
    
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
    
    if is_item_broken(inst):
        cur, mx = _dur_tuple(inst.get("durability"))
        return (True, w_uid, (cur, mx))
        
    return (False, None, (0, 0))

def apply_end_of_battle_wear(player_data: dict, combat_details: dict, log: list[str]) -> bool:
    changed = False
    
    # --- Desgaste da Arma ---
    w_uid = _get_equipped_uid(player_data, _WEAPON_SLOTS)
    if w_uid:
        cur, mx, broke_now = consume_durability(player_data, w_uid, 1)
        changed = True
        if broke_now:
            log.append(f"⚠️ 𝑺𝒖𝒂 𝒂𝒓𝒎𝒂 𝒒𝒖𝒆𝒃𝒓𝒐𝒖 ({cur}/{mx}).")

    # --- Desgaste da Armadura ---
    for slot in _ARMOR_SLOTS:
        uid_to_damage = _get_equipped_uid(player_data, [slot])
        if uid_to_damage:
            cur, mx, broke_now = consume_durability(player_data, uid_to_damage, 1)
            changed = True
            if broke_now:
                item_inst = _get_unique_inst(player_data, uid_to_damage)
                item_name = (item_inst or {}).get("display_name", "Seu equipamento")
                log.append(f"⚠️ {item_name} 𝒒𝒖𝒆𝒃𝒓𝒐𝒖 ({cur}/{mx}).")

    return changed