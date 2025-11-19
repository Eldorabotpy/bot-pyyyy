# modules/crafting_engine.py

from __future__ import annotations
from datetime import datetime, timezone, timedelta
import uuid
import random
from typing import Any, Dict, Tuple, List
from modules import player_manager, game_data
from modules.crafting_registry import get_recipe, all_recipes  # noqa: F401
from modules.game_data.classes import get_primary_damage_profile
from modules.game_data import rarity as rarity_tables  # ATTR_COUNT_BY_RARITY, BASE_STATS_BY_RARITY etc.
from modules import clan_manager

# =========================
#    Utilitários básicos 
# =========================

def _as_dict(obj: Any, default: Dict | None = None) -> Dict:
    if isinstance(obj, dict):
        return obj
    return {} if default is None else default

def _as_tuple_2(val: Any, fallback: Tuple[int, int] = (1, 1)) -> Tuple[int, int]:
    """
    Compat: converte ([a,b], {'min':a,'max':b}, {'raro':[a,b]}, etc.) para (min,max).
    Aqui é usado apenas para metadados (ex.: bloco "damage" do item), não para o valor dos atributos.
    """
    try:
        if isinstance(val, (list, tuple)) and len(val) >= 2:
            return int(val[0]), int(val[1])
        if isinstance(val, dict):
            if "min" in val and "max" in val:
                return int(val["min"]), int(val["max"])
            for k in ("lendario", "epico", "raro", "bom", "comum"):
                v = val.get(k)
                if isinstance(v, (list, tuple)) and len(v) >= 2:
                    return int(v[0]), int(v[1])
    except Exception:
        pass
    return fallback

# Em modules/crafting_engine.py

async def _seconds_with_perks(player_data: dict, base_seconds: int) -> int:
    # user_id = player_data['user_id']  <-- Correto, não precisamos disto

    # Passa 'player_data' (Corrigido)
    craft_mult_raw = player_manager.get_perk_value(player_data, "craft_speed_multiplier", None)

    if craft_mult_raw is None:
    # Passa 'player_data' (Corrigido)
        mult = float(player_manager.get_perk_value(player_data, "refine_speed_multiplier", 1.0))
    else:
        mult = float(craft_mult_raw)

    clan_id = player_data.get("clan_id")
    if clan_id:
        # <<< [ESTA É A CORREÇÃO] >>>
        # Remove 'await'. Esta função é síncrona (def) e não async.
        clan_buffs = clan_manager.get_clan_buffs(clan_id) 
        speed_bonus_percent = clan_buffs.get("crafting_speed_percent", 0)
        if speed_bonus_percent > 0:
            mult += (speed_bonus_percent / 100.0)

    mult = max(0.25, min(4.0, mult)) # Síncrono
 
    return max(1, int(base_seconds / mult)) # Síncrono

def _has_materials(player_data: dict, inputs: dict) -> bool:
    inv = _as_dict(player_data.get("inventory"))
    for k, v in _as_dict(inputs).items():
        have = inv.get(k, 0)
        if isinstance(have, dict):
            have = int(have.get("quantity", 0))
        if int(have) < int(v):
            return False
    return True

def _consume_materials(player_data: dict, inputs: dict) -> None:
    for item_id, qty in _as_dict(inputs).items():
        player_manager.remove_item_from_inventory(player_data, item_id, int(qty))

def _gd_attr(slot: str, key: str, default: Any = None):
    """
    Busca ranges em modules/game_data/rarity.py
    Esperado: BASE_STATS_BY_RARITY[slot][key] -> {rarity: [min,max]}
    (Hoje serve só para meta/compat; não define valores de atributo.)
    """
    try:
        table = getattr(rarity_tables, "BASE_STATS_BY_RARITY", {}) or {}
        out = _as_dict(_as_dict(table.get(slot)).get(key), default={})
        return out
    except Exception:
        return {}

def _get_item_info(base_id: str) -> dict:
    """
    Tenta pegar metadados da versão nova (equipment via game_data.get_item_info),
    e cai para ITEMS_DATA se preciso.
    """
    try:
        info = game_data.get_item_info(base_id)
        if info:
            return dict(info)
    except Exception:
        pass
    return _as_dict(getattr(game_data, "ITEMS_DATA", {})).get(base_id, {}) or {}

def _get_player_class_key(player_data: dict) -> str | None:
    candidates = [
        _as_dict(player_data.get("class")).get("type"),
        _as_dict(player_data.get("classe")).get("type"),
        player_data.get("class_type"),
        player_data.get("classe_tipo"),
        player_data.get("class_key"),
        player_data.get("classe"),
        player_data.get("class"),
    ]
    for c in candidates:
        if isinstance(c, str) and c.strip():
            return c.strip().lower()
    return None

def _is_weapon_slot(slot: str | None) -> bool:
    s = (slot or "").lower()
    return s in {"arma", "weapon", "weap", "primary_weapon"}


# =========================
# Preview / Start
# =========================

# <<< CORREÇÃO 5: Adiciona async def >>>
async def preview_craft(recipe_id: str, player_data: dict) -> dict | None:
    rec = get_recipe(recipe_id) # Síncrono
    if not rec:
        return None

    rec = dict(rec)
    inputs = _as_dict(rec.get("inputs")) # Síncrono
    prof = _as_dict(player_data.get("profession")) # Síncrono
    ok_prof = (prof.get("type") == rec.get("profession")) and \
              (int(prof.get("level", 1)) >= int(rec.get("level_req", 1))) # Síncrono

    # <<< CORREÇÃO 6: Adiciona await >>>
    duration = await _seconds_with_perks(player_data, int(rec.get("time_seconds", 60))) # Chama função async

    return {
        "can_craft": bool(ok_prof and _has_materials(player_data, inputs)), # Síncrono
        "duration_seconds": duration,
        "inputs": dict(inputs),
        "result_base_id": rec.get("result_base_id"),
        "display_name": rec.get("display_name", recipe_id),
        "emoji": rec.get("emoji", ""),
    }

# <<< CORREÇÃO 7: Adiciona async def >>>
async def start_craft(user_id: int, recipe_id: str):
    # <<< CORREÇÃO 8: Adiciona await >>>
    pdata = await player_manager.get_player_data(user_id)
    rec = get_recipe(recipe_id) # Síncrono
    if not pdata or not rec:
        return "Receita de forja inválida."

    rec = dict(rec)
    prof = _as_dict(pdata.get("profession")) # Síncrono
    if prof.get("type") != rec.get("profession") or int(prof.get("level", 1)) < int(rec.get("level_req", 1)):
        return "Nível ou tipo de profissão insuficiente para esta receita."

    inputs = _as_dict(rec.get("inputs")) # Síncrono
    if not _has_materials(pdata, inputs): # Síncrono
        return "Materiais insuficientes."

    # <<< CORREÇÃO 9: Adiciona await >>>
    duration = await _seconds_with_perks(pdata, int(rec.get("time_seconds", 60))) # Chama função async
    _consume_materials(pdata, inputs) # Síncrono

    # Lógica síncrona de estado
    finish = datetime.now(timezone.utc) + timedelta(seconds=duration)
    pdata["player_state"] = {
        "action": "crafting",
        "finish_time": finish.isoformat(),
        "details": {"recipe_id": recipe_id}
    }
    # <<< CORREÇÃO 10: Adiciona await >>>
    await player_manager.save_player_data(user_id, pdata)
    return {"duration_seconds": duration, "finish_time": finish.isoformat()}

# =========================
# Mapeamento/seleção de atributos
# =========================

def _attr_to_enchant_key(attr_name: str) -> str:
    """Normaliza nomes para as chaves usadas em 'enchantments'."""
    a = str(attr_name or "").lower()
    
    # --- Mapeamentos CRÍTICOS para Magia/Foco/Recursos ---
    if a in {"inteligencia", "magia", "poder_magico", "dano_magico"}:
        return "magic_attack" # Chave usada para dano de feitiços
    if a in {"mana", "mp", "mana_max", "max_mana"}:
        return "max_mana"
    if a in {"foco", "disciplina", "tenacidade", "tenacity"}:
        return "tenacity" # Exemplo de atributo secundário
    # ----------------------------------------------------

    if a in {"forca", "força", "ataque", "attack", "dano", "damage", "dmg", "poder", "ofensivo"}:
        return "dmg"
    if a in {"vida", "hp", "saude", "saúde", "health"}:
        return "hp"
    if a in {"defesa", "defense"}:
        return "defense"
    if a in {"iniciativa", "initiative", "velocidade", "agilidade"}:
        return "initiative"
    if a in {"sorte", "luck"}:
        return "luck"
        
    # Atributos de classe (bushido, carisma, letalidade, etc.)
    return a

def _class_primary_attr(player_class: str | None) -> str:
    """
    Retorna o atributo PRIMÁRIO 'visível' da classe (ex.: 'bushido' pro Samurai).
    O 'dmg' é apenas espelho para cálculo.
    """
    profile = get_primary_damage_profile((player_class or "").lower()) or {}
    key = profile.get("stat_key") or "dmg"
    return key

def _rarity_target_attr_count(rarity: str) -> int:
    # Fallback seguro se a tabela não existir
    default_map = {"comum": 1, "bom": 2, "raro": 3, "epico": 4, "lendario": 5}
    table = getattr(rarity_tables, "ATTR_COUNT_BY_RARITY", None)
    if isinstance(table, dict) and table:
        return int(table.get((rarity or "").lower(), default_map.get((rarity or "").lower(), 1)))
    return int(default_map.get((rarity or "").lower(), 1))

def _secondary_attr_pool(recipe: dict, player_class: str | None) -> List[str]:
    """
    Monta a pool de candidatos (sem primário): pools da receita + 'geral' + pool da classe.
    """
    AFFIX_POOLS = getattr(game_data, "AFFIX_POOLS", {}) or {}
    combined: List[str] = []

    for pool_name in (recipe.get("affix_pools_to_use") or []):
        pool = AFFIX_POOLS.get(pool_name) or []
        for entry in pool:
            if isinstance(entry, dict):
                stat_name = entry.get("stat") or entry.get("name") or entry.get("attr")
                if stat_name:
                    combined.append(str(stat_name))
            elif isinstance(entry, str):
                combined.append(entry)

    combined += (AFFIX_POOLS.get("geral") or [])
    if player_class:
        combined += (AFFIX_POOLS.get(player_class) or [])

    # normaliza, remove vazios e 'dmg'
    out: List[str] = []
    seen = {"dmg"}
    for a in combined:
        a = (a or "").strip().lower()
        if not a or a in seen:
            continue
        seen.add(a)
        out.append(a)
    return out

def _pick_attribute_keys_for_item(rarity: str, primary_key: str, recipe: dict, player_class: str | None) -> List[str]:
    """
    Define a LISTA FINAL de atributos do item.
    - Sempre inclui 'primary_key' como primeiro.
    - Completa com candidatos da pool até atingir ATTR_COUNT_BY_RARITY[rarity].
    - Sem duplicatas, sem 'dmg' visível.
    """
    target = max(1, _rarity_target_attr_count(rarity))
    if target == 1:
        return [primary_key]

    candidates = _secondary_attr_pool(recipe, player_class)
    random.shuffle(candidates)

    out = [primary_key]
    seen = {primary_key, "dmg"}
    for c in candidates:
        ck = _attr_to_enchant_key(c)
        if ck in seen:
            continue
        seen.add(ck)
        out.append(ck)
        if len(out) >= target:
            break
    return out[:target]


# =========================
# Raridade / meta de dano
# =========================

def _roll_rarity(player_data: dict, recipe: dict) -> str:
    """
    Roll probabilístico (com pequeno bônus por nível de profissão acima do requisito).
    """
    prof = _as_dict(player_data.get("profession"))
    prof_level = int(prof.get("level", 1))
    level_req = int(recipe.get("level_req", 1))
    level_diff = max(0, prof_level - level_req)

    base_chances = dict(recipe.get("rarity_chances", {"comum": 1.0}))
    bonus_per_level = 0.01  # +1% por nível acima em 'bom'+

    def _add_bonus(k: str, v: float) -> float:
        return max(0.0, v + (level_diff * bonus_per_level)) if k in ("bom", "raro", "epico", "lendario") else max(0.0, v)

    adjusted = {k: _add_bonus(k, float(v)) for k, v in base_chances.items()}
    total = sum(adjusted.values()) or 1.0
    norm = {k: v / total for k, v in adjusted.items()}

    order = ["lendario", "epico", "raro", "bom", "comum"]
    roll = random.random()
    acc = 0.0
    for r in order:
        acc += norm.get(r, 0.0)
        if roll < acc:
            return r
    return "comum"


# =========================
# Aplicação de atributos (= upgrade_level)
# =========================

def _apply_attr_with_upgrade(item: dict, attr_key: str, upgrade_level: int, source: str) -> None:
    """
    Escreve 'enchantments[attr_key].value = upgrade_level'.
    'source' pode ser 'primary' (primeiro atributo) ou 'affix' (demais).
    """
    ench = item.setdefault("enchantments", {})
    ench[attr_key] = {"value": int(upgrade_level), "source": source}


# =========================
# Criação do item (nova lógica)
# =========================

def _create_dynamic_unique_item(player_data: dict, recipe: dict) -> dict:
    final_rarity = _roll_rarity(player_data, recipe)
    base_id = recipe["result_base_id"]

    # <<< CORREÇÃO (Parte 1): Buscamos o slot ANTES de criar o item >>>
    info = _get_item_info(base_id)
    slot = (info.get("slot") or "").lower()
    
    new_item = {
        "uuid": str(uuid.uuid4()),
        "base_id": base_id,
        "rarity": final_rarity,
        "slot": slot,  # <<< CORREÇÃO (Parte 2): O slot agora é salvo no item >>>
        "upgrade_level": 1,          # nasce no +1
        "durability": [20, 20],      # [cur/max]
        "enchantments": {},
    }

    # ===== Classe-alvo: usa class_req da receita se existir; senão, cai para a classe do jogador =====
    if isinstance(recipe.get("class_req"), (list, tuple)) and recipe["class_req"]:
        target_class = str(recipe["class_req"][0]).strip().lower()
    else:
        target_class = _get_player_class_key(player_data)

    # Mapa de atributo primário VISÍVEL por classe (para exibição + ícones)
    CLASS_VISIBLE_PRIMARY_ATTR = {
        "guerreiro": "forca",
        "berserker": "furia",
        "cacador":   "precisao",
        "assassino": "letalidade",
        "bardo":     "carisma",
        "monge":     "foco",
        "mago":      "inteligencia",
        "samurai":   "bushido",
    }

    # 1) escolher o primário "visível"
    if _is_weapon_slot(slot):
        primary_attr = CLASS_VISIBLE_PRIMARY_ATTR.get((target_class or ""), "forca")
        mirror_dmg = True

        # Metadados descritivos de dano (tooltip). Não afetam os valores dos atributos.
        dmg_info = _as_dict(recipe.get("damage_info"))
        dmin, dmax = _as_tuple_2(dmg_info, (10, 20))
        # se não vier 'scales_with' na receita, usa o perfil da classe-alvo
        class_profile = get_primary_damage_profile(target_class or "")
        scales_with = str(dmg_info.get("scales_with", class_profile.get("scales_with", "for")))
        new_item["damage"] = {
            "type": str(dmg_info.get("type", class_profile.get("type", "fisico"))),
            "min": int(dmg_info.get("min_damage", dmin)),
            "max": int(dmg_info.get("max_damage", dmax)),
            "scales_with": scales_with,
        }
    else:
        # Primário padrão de não-armas: vida (hp).
        # Se quiser por slot (elmo/armadura/…): trocar por uma função que leia BASE_STATS_BY_RARITY.
        primary_attr = "hp"
        mirror_dmg = False

    # 2) lista final de atributos pela raridade (inclui primário + secundários)
    attr_keys = _pick_attribute_keys_for_item(final_rarity, primary_attr, recipe, target_class)

    # 3) aplica TODOS com valor = upgrade_level
    upg = int(new_item["upgrade_level"])
    for idx, ak in enumerate(attr_keys):
        source = "primary" if idx == 0 else "affix"
        _apply_attr_with_upgrade(new_item, _attr_to_enchant_key(ak), upg, source)

    # 4) espelho em 'dmg' só se for arma (para os cálculos)
    if mirror_dmg and attr_keys:
        first_key = _attr_to_enchant_key(attr_keys[0])
        if first_key != "dmg":
            new_item["enchantments"]["dmg"] = {"value": upg, "source": "primary_mirror"}

    # 5) metadados amigáveis
    dn = info.get("display_name") or info.get("nome_exibicao") or info.get("name") or base_id.replace("_", " ").title()
    if dn:
        new_item["display_name"] = str(dn)
    if info.get("emoji"):
        new_item["emoji"] = info["emoji"]

    # 6) requisito de classe (se a receita definir)
    class_req = recipe.get("class_req")
    if isinstance(class_req, (list, tuple)):
        new_item["class_req"] = [str(x).strip().lower() for x in class_req if str(x).strip()]
    elif isinstance(class_req, str) and class_req.strip():
        new_item["class_req"] = [class_req.strip().lower()]

    return new_item

# =========================
# Finish / XP
# =========================

# <<< CORREÇÃO 11: Adiciona async def >>>
async def finish_craft(user_id: int):
    # <<< CORREÇÃO 12: Adiciona await >>>
    pdata = await player_manager.get_player_data(user_id)
    pstate = _as_dict(pdata.get("player_state")) if pdata else {} # Síncrono
    if not pdata or pstate.get("action") != "crafting":
        return "Nenhuma forja em andamento."

    rid = _as_dict(pstate.get("details")).get("recipe_id") # Síncrono
    rec = get_recipe(rid) # Síncrono
    if not rec:
        pdata["player_state"] = {"action": "idle"}
        # <<< CORREÇÃO 13: Adiciona await >>>
        await player_manager.save_player_data(user_id, pdata)
        return "Receita não encontrada ao concluir."

    rec = dict(rec)

    # Lógica síncrona
    novo_item_criado = _create_dynamic_unique_item(pdata, rec)
    player_manager.add_unique_item(pdata, novo_item_criado)

    # XP de profissão (síncrono)
    prof = _as_dict(pdata.get("profession"))
    if prof.get("type") == rec.get("profession"):
        prof["xp"] = int(prof.get("xp", 0)) + int(rec.get("xp_gain", 1))
        cur = int(prof.get("level", 1))
        while True:
            try: need = int(game_data.get_xp_for_next_collection_level(cur))
            except Exception: need = 0
            if need <= 0 or prof["xp"] < need: break
            prof["xp"] -= need; cur += 1; prof["level"] = cur
        pdata["profession"] = prof

    pdata["player_state"] = {"action": "idle"}
    # <<< CORREÇÃO 14: Adiciona await >>>
    await player_manager.save_player_data(user_id, pdata)

    return {"status": "success", "item_criado": novo_item_criado}
