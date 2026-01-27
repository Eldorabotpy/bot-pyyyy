# modules/profession_engine.py
# (VERSÃO CORRIGIDA: Lógica Original Restaurada + Funções de Reparo Incluídas)

from __future__ import annotations
from typing import Dict, Tuple, Any
import random
from modules import player_manager, game_data, crafting_registry
from modules.game_data.refining import REFINING_RECIPES

# ==================================================================
# 1. FUNÇÕES PARA O SISTEMA DE MENUS (CRAFT E REFINO)
# ==================================================================

async def try_refine(user_id: str, player_data: dict, recipe_id: str) -> dict:
    recipe = REFINING_RECIPES.get(recipe_id)
    if not recipe: return {"success": False, "error": "Receita inexistente."}

    inv = player_data.get("inventory", {})
    # Verifica materiais
    for mat_id, qty in recipe.get("materials", {}).items():
        have = int(inv.get(mat_id, 0)) if isinstance(inv.get(mat_id), (int, float, str)) else 0
        if have < int(qty):
             return {"success": False, "error": f"Falta material: {mat_id}"}

    # Consome
    for mat_id, qty in recipe.get("materials", {}).items():
        player_manager.remove_item_from_inventory(player_data, mat_id, qty)

    # Entrega
    res_id, qty_res = recipe["result_id"], recipe.get("result_qty", 1)
    player_manager.add_item_to_inventory(player_data, res_id, qty_res)
    
    _add_xp(player_data, 1)
    await player_manager.save_player_data(user_id, player_data)
    
    return {"success": True, "message": f"Refinado: {qty_res}x {res_id}"}

async def try_craft(user_id: str, player_data: dict, recipe_id: str) -> dict:
    recipe = crafting_registry.get_recipe(recipe_id)
    if not recipe: return {"success": False, "error": "Receita não encontrada."}

    # Trava de Profissão
    my_prof_data = player_data.get("profession", {})
    my_prof = my_prof_data.get("key") or my_prof_data.get("type")
    req_prof = recipe.get("profession_req")
    
    if req_prof and req_prof != my_prof:
        return {"success": False, "error": f"Requer profissão: {req_prof.capitalize()}"}

    inv = player_data.get("inventory", {})
    mats = recipe.get("materials", {})
    for mat_id, qty in mats.items():
        have = int(inv.get(mat_id, 0)) if isinstance(inv.get(mat_id), (int, float, str)) else 0
        if have < int(qty):
            return {"success": False, "error": f"Falta: {mat_id}"}

    for mat_id, qty in mats.items():
        player_manager.remove_item_from_inventory(player_data, mat_id, qty)

    base_id = recipe["result_base_id"]
    new_item = {
        "base_id": base_id, "rarity": "comum", "upgrade_level": 1, 
        "durability": [20, 20], "crafter": player_data.get("character_name", "Alguém")
    }
    
    # Sorte no craft
    r = random.random()
    if r < 0.05: new_item["rarity"] = "lendario"
    elif r < 0.15: new_item["rarity"] = "epico"
    elif r < 0.35: new_item["rarity"] = "raro"
    
    # Aplica a lógica de atributos da sua engine original
    _sync_attrs_to_upgrade(new_item)

    await player_manager.add_unique_item_to_player(user_id, new_item)
    _add_xp(player_data, recipe.get("xp_gain", 10))
    await player_manager.save_player_data(user_id, player_data)

    return {"success": True, "message": f"Criado: {base_id} ({new_item['rarity']})!"}

# ==================================================================
# 2. SUA ENGINE ORIGINAL (Enhance, Atributos, Failstacks, Tabelas)
# ==================================================================

# Fallbacks caso não estejam definidos nas tabelas
RARITY_CAPS_FALLBACK = {
    "comum": 5, "bom": 7, "raro": 9, "epico": 11, "lendario": 13,
}

# Itens de aprimoramento
JOIA_FORJA_ID    = "joia_da_forja"
SIGILO_ID        = "sigilo_protecao"
PARCHMENT_ID     = "pergaminho_durabilidade"

# Regras de chance (ajustadas)
BASE_SUCCESS_BY_TARGET = {
    1: 1.00, 2: 1.00, 3: 1.00, 4: 1.00, 5: 1.00,
    6: 1.00, 7: 0.98, 8: 0.97, 9: 0.60, 10: 0.45,
    11: 0.30, 12: 0.36, 13: 0.20, 14: 0.22, 15: 0.15,
    16: 0.10, 17: 0.08, 18: 0.05, 19: 0.02, 20: 0.01
}

RARITY_SUCCESS_MOD = {
    "comum": +0.10, "bom": +0.05, "raro": 0.00, "epico": -0.05, "lendario": -0.10,
}

FAILSTACK_STEP = 0.03
FAILSTACK_MAX  = 0.30
MIN_CHANCE = 0.05
MAX_CHANCE = 0.95

# =========================
# Inventário util
# =========================
def _inv_qty(pdata: dict, item_id: str) -> int:
    inv = (pdata or {}).get("inventory", {}) or {}
    val = inv.get(item_id, 0)
    if isinstance(val, dict): return 0
    try: return int(val)
    except Exception: return 0

def _consume_costs(pdata: dict, costs: Dict[str, int]) -> None:
    for k, need in (costs or {}).items():
        player_manager.remove_item_from_inventory(pdata, k, int(need))

# =========================
# Tabelas e Metadados
# =========================
def _get_caps_table() -> Dict[str, int]:
    try:
        from modules.game_data import rarity as rarity_tables
        for attr in ("UPGRADE_CAP_BY_RARITY", "MAX_UPGRADE_BY_RARITY"):
            tb = getattr(rarity_tables, attr, None)
            if isinstance(tb, dict) and tb:
                return {str(k).lower(): int(v) for k, v in tb.items()}
    except Exception: pass
    return dict(RARITY_CAPS_FALLBACK)

def _get_item_info(base_id: str) -> dict:
    try:
        info = game_data.get_item_info(base_id)
        if info: return dict(info)
    except Exception: pass
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

# =========================
# Ferramentas de Coleta
# =========================
def _get_equipped_tool(player_data: dict) -> tuple[str | None, dict | None, dict | None]:
    """
    Retorna (unique_id, instância, item_base) da ferramenta equipada.
    """
    equip = player_data.get("equipment", {}) or {}
    inv = player_data.get("inventory", {}) or {}

    uid = equip.get("tool")
    if not uid:
        return None, None, None

    inst = inv.get(uid)
    if not isinstance(inst, dict):
        return None, None, None

    base_id = inst.get("base_id")
    info = _get_item_info(base_id)
    if not info:
        return None, None, None

    return uid, inst, info


def _consume_tool_durability(tool_inst: dict, amount: int = 1) -> bool:
    """
    Consome durabilidade da ferramenta.
    Retorna False se quebrar.
    """
    cur, mx = _dur_tuple(tool_inst.get("durability"))
    cur -= amount
    if cur <= 0:
        _set_dur(tool_inst, 0, mx)
        return False

    _set_dur(tool_inst, cur, mx)
    return True

def validate_and_prepare_gather(player_data: dict) -> dict:
    """
    Valida se o jogador pode coletar:
    - tem profissão
    - tem ferramenta equipada
    - ferramenta é compatível
    - tem durabilidade
    """
    prof = player_data.get("profession", {}) or {}
    prof_key = prof.get("key") or prof.get("type")

    if not prof_key:
        return {"ok": False, "error": "Você não possui uma profissão ativa."}

    uid, tool_inst, tool_info = _get_equipped_tool(player_data)
    if not tool_inst:
        return {"ok": False, "error": "Você precisa equipar uma ferramenta de coleta."}

    tool_type = tool_info.get("tool_type")
    if tool_type != prof_key:
        return {
            "ok": False,
            "error": f"Ferramenta incompatível com a profissão ({prof_key})."
        }

    cur, _ = _dur_tuple(tool_inst.get("durability"))
    if cur <= 0:
        return {"ok": False, "error": "Sua ferramenta está quebrada."}

    return {
        "ok": True,
        "tool_uid": uid,
        "tool_inst": tool_inst,
        "tool_info": tool_info,
        "profession": prof_key
    }

def _is_weapon(item_inst: dict) -> bool:
    base_id = (item_inst or {}).get("base_id")
    info = _get_item_info(base_id)
    slot = (info.get("slot") or "").lower()
    return slot in {"arma", "weapon", "weap", "primary_weapon"}

def _sync_attrs_to_upgrade(item_inst: dict) -> None:
    """Sincroniza atributos com o nível de upgrade."""
    if not isinstance(item_inst, dict): return
    
    ench = item_inst.setdefault("enchantments", {}) or {}
    up = int(item_inst.get("upgrade_level", 1)) 
    primary_key_found = None

    for k, v in list(ench.items()):
        if not isinstance(v, dict): continue
        source = str(v.get("source", ""))
        if source == "primary_mirror": continue
        v["value"] = up
        ench[k] = v
        if source == "primary": primary_key_found = k

    if _is_weapon(item_inst):
        if primary_key_found and primary_key_found != "dmg":
            ench["dmg"] = {"value": up, "source": "primary_mirror"}

# =========================
# Custos baseados na receita original
# =========================
def _resolve_recipe_for_inst(inst: dict) -> dict | None:
    if not isinstance(inst, dict): return None
    rid = inst.get("crafted_recipe_id")
    if rid:
        rec = crafting_registry.get_recipe(rid)
        if rec: return rec
    base_id = inst.get("base_id")
    if not base_id: return None
    try:
        all_rec = crafting_registry.all_recipes()
        for _, rec in (all_rec.items() if isinstance(all_rec, dict) else []):
            if rec.get("result_base_id") == base_id: return rec
    except Exception: pass
    return None

def _compute_costs_from_recipe(item_inst: dict, include_protection: bool) -> Dict[str, int]:
    rec = _resolve_recipe_for_inst(item_inst)
    if not rec: return {} 
    costs = {k: int(v) for k, v in (rec.get("inputs") or {}).items()}
    costs[JOIA_FORJA_ID] = costs.get(JOIA_FORJA_ID, 0) + 1
    if include_protection:
        costs[SIGILO_ID] = costs.get(SIGILO_ID, 0) + 1
    return costs

def _can_pay_costs(pdata: dict, costs: Dict[str, int]) -> bool:
    return all(_inv_qty(pdata, k) >= int(v) for k, v in (costs or {}).items())

# =========================
# APRIMORAMENTO (ENHANCE)
# =========================
async def enhance_item(user_id: str, player_data: dict, unique_id: str, use_joia: bool = False) -> dict:
    inv = player_data.get('inventory', {}) or {}
    item = inv.get(unique_id)
    
    if not isinstance(item, dict) or not item.get('base_id'):
        return {"success": False, "error": "Item inválido."}

    rarity = str(item.get("rarity", "comum")).lower()
    up = int(item.get("upgrade_level", 1))
    caps = _get_caps_table()
    cap = int(caps.get(rarity, RARITY_CAPS_FALLBACK.get(rarity, 5)))

    if up >= cap:
        return {"success": False, "error": f"Item no limite (+{cap}) para {rarity}."}

    costs = _compute_costs_from_recipe(item, include_protection=use_joia)
    if not costs:
        costs = {JOIA_FORJA_ID: 1}
        if use_joia: costs[SIGILO_ID] = 1

    if not _can_pay_costs(player_data, costs):
        return {"success": False, "error": "Materiais insuficientes."}

    _consume_costs(player_data, costs)

    # Lógica de Chance
    target = up + 1
    if target <= 2: 
        new_level = target
        item['upgrade_level'] = new_level
        item['enh_failstacks'] = 0.0
        _sync_attrs_to_upgrade(item)
        await player_manager.save_player_data(user_id, player_data)
        return {"success": True, "new_level": new_level, "message": f"Sucesso garantido! +{new_level}"}

    base = BASE_SUCCESS_BY_TARGET.get(target, 0.10)
    base += RARITY_SUCCESS_MOD.get(rarity, 0.0)

    fs = float(item.get("enh_failstacks", 0.0) or 0.0)
    fs_bonus = min(FAILSTACK_MAX, fs * FAILSTACK_STEP)
    
    total_stats = await player_manager.get_player_total_stats(player_data)
    luck = int(total_stats.get('luck', 5))
    prof_lvl = int(player_data.get('profession', {}).get('level', 1))
    perk_bonus = (luck + prof_lvl) * 0.001

    chance = max(MIN_CHANCE, min(MAX_CHANCE, base + fs_bonus + perk_bonus))
    success = random.random() <= chance

    # Durabilidade na falha
    cur_d, max_d = _dur_tuple(item.get("durability"))
    if not success:
        cur_d = max(0, cur_d - 1)
    _set_dur(item, cur_d, max_d)

    msg = ""
    if success:
        new_level = up + 1
        item['upgrade_level'] = new_level
        item['enh_failstacks'] = 0.0
        _sync_attrs_to_upgrade(item)
        msg = f"✨ <b>SUCESSO!</b> Agora é +{new_level}!"
    else:
        protected = False
        if use_joia and costs.get(SIGILO_ID, 0) > 0:
            protected = True
            msg = "❌ Falhou! (Protegido pelo Sigilo)"
        else:
            if up >= 3:
                item['upgrade_level'] = max(1, up - 1)
                msg = f"❌ Falhou! Caiu para +{item['upgrade_level']}."
            else:
                msg = "❌ Falhou! (Nível mantido)."
        
        item['enh_failstacks'] = min(10.0, float(item.get('enh_failstacks', 0.0) or 0.0) + 1.0)
        _sync_attrs_to_upgrade(item)

    await player_manager.save_player_data(user_id, player_data)
    return {"success": success, "new_level": item.get("upgrade_level"), "message": msg}

# =========================
# Helpers Durabilidade (Seu código original)
# =========================
def _dur_tuple(raw) -> Tuple[int, int]:
    cur, mx = 20, 20
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        try: cur = int(raw[0]); mx = int(raw[1])
        except: pass
    elif isinstance(raw, dict):
        try: cur = int(raw.get("current", 20)); mx = int(raw.get("max", 20))
        except: pass
    return max(0, min(cur, mx)), max(1, mx)

def _set_dur(item: dict, cur: int, mx: int) -> None:
    item["durability"] = [int(max(0, min(cur, mx))), int(mx)]

# ==================================================================
# 3. REPARO E REPARO EM MASSA (As funções que faltavam!)
# ==================================================================

async def restore_durability(player_data: dict, unique_id: str) -> dict:
    inv = player_data.get('inventory', {}) or {}
    item = inv.get(unique_id)
    if not isinstance(item, dict) or not item.get('base_id'):
        return {"error": "Item inválido para restaurar."}
    if _inv_qty(player_data, PARCHMENT_ID) <= 0:
        return {"error": "Você precisa de 1x Pergaminho de Durabilidade."}

    # Consome 1 pergaminho e restaura totalmente (20/20)
    player_manager.remove_item_from_inventory(player_data, PARCHMENT_ID, 1)
    
    # Pega durabilidade máxima real
    info = _get_item_info(item.get("base_id"))
    max_d = 20
    raw_dur = info.get("durability")
    if isinstance(raw_dur, list): max_d = raw_dur[1]
    elif isinstance(raw_dur, int): max_d = raw_dur

    _set_dur(item, max_d, max_d)
    
    # O handler que chama isso vai salvar o player_data, mas por segurança salvamos aqui se tivermos user_id?
    # Como a função antiga não recebia user_id, assumimos que quem chama (handler) salva.
    # Mas se precisar salvar aqui, precisaríamos passar user_id. 
    # Mantendo compatibilidade com chamada antiga: Retorna status.
    return {"status": "ok", "durability": item['durability']}

async def restore_all_equipped_durability(player_data: dict) -> dict:
    """
    Restaura TODOS os itens equipados consumindo APENAS 1 Pergaminho.
    """
    inv = player_data.get('inventory', {}) or {}
    equip = player_data.get('equipment', {}) or {}
    
    if _inv_qty(player_data, PARCHMENT_ID) <= 0:
        return {"error": "Você precisa de 1x Pergaminho de Durabilidade."}

    items_to_repair = []
    # Pega valores únicos (IDs dos itens)
    for uid in set(equip.values()):
        if uid and uid in inv:
            items_to_repair.append(uid)

    if not items_to_repair:
        return {"error": "Nenhum equipamento equipado para restaurar."}

    player_manager.remove_item_from_inventory(player_data, PARCHMENT_ID, 1)

    count = 0
    for uid in items_to_repair:
        item = inv[uid]
        base_id = item.get("base_id")
        info = _get_item_info(base_id)
        
        real_max = 20
        raw_dur = info.get("durability")
        if isinstance(raw_dur, list) and len(raw_dur) > 1: real_max = int(raw_dur[1])
        elif isinstance(raw_dur, int): real_max = raw_dur
            
        _set_dur(item, real_max, real_max)
        count += 1

    return {"success": True, "count": count, "message": f"Reparados {count} itens!"}

# =========================
# Util XP
# =========================
def _add_xp(player_data, amount):
    p = player_data.setdefault("profession", {})
    if "level" not in p: p["level"] = 1
    if "xp" not in p: p["xp"] = 0
    p["xp"] += amount
    req = p["level"] * 100
    if p["xp"] >= req:
        p["xp"] -= req
        p["level"] += 1