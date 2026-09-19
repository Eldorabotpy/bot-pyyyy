# modules/player/stats.py
# (VERSÃO DEFINITIVA: Balanceamento Ativo + Correção de Mago)

from __future__ import annotations
import random
from bson import ObjectId
import logging
from typing import Dict, Optional, Tuple, Any, List, Union

# --- IMPORTS ---
from modules.game_data.skills import SKILL_DATA
from modules.game_data.classes import CLASSES_DATA, get_stat_modifiers
from modules import game_data
from modules.game_data.class_evolution import get_evolution_options, get_class_ancestry
from modules.player.core import users_collection, save_player_data
# Tenta importar o módulo de balanceamento
try:
    from modules import balance
except ImportError:
    balance = None  # Fallback se o arquivo não existir

try:
    from modules.combat.durability import is_item_broken
except ImportError:
    def is_item_broken(x): return False

logger = logging.getLogger(__name__)

# ========================================
# 🛡️ XP DE CLÃ POR COMBATE
# ========================================

PERCENTUAL_XP_CLA_COMBATE = 0.10


def _adicionar_xp_cla_combate(
    user_id,
    xp_recebido,
):
    """
    Entrega ao clã 10% do XP realmente recebido
    pelo jogador no combate.

    Uma falha no sistema de clã nunca deve
    impedir a recompensa normal do jogador.
    """

    try:
        xp_recebido = int(
            xp_recebido or 0
        )
    except (TypeError, ValueError):
        xp_recebido = 0

    if xp_recebido <= 0:
        return 0

    xp_cla = max(
        1,
        int(
            xp_recebido *
            PERCENTUAL_XP_CLA_COMBATE
        ),
    )

    try:
        # Importação local para evitar
        # dependências circulares.
        from modules.clan.clan_manager import (
            adicionar_xp_cla,
        )

        sucesso = adicionar_xp_cla(
            user_id=user_id,
            quantidade=xp_cla,
        )

        if sucesso:
            return xp_cla

    except Exception as erro:
        print(
            "⚠️ [XP CLÃ] Falha ao entregar "
            f"XP do clã para {user_id}: {erro}"
        )

    return 0

# ========================================
# 1. CONSTANTES E LISTAS DE CLASSES
# ========================================

MAGIC_CLASSES = {
    "mago", "arquimago", "feiticeiro", "bruxo", "necromante", 
    "curandeiro", "sacerdote", "clerigo", "druida", "xama",
    "bardo", "mistico", "elementalista", "hierofante", "oraculo_celestial"
}

AGILITY_CLASSES = {
    "cacador", "arqueiro", "patrulheiro", "franco_atirador",
    "assassino", "ninja", "ladino", "ladrao", "ladrao_de_sombras", "ceifador",
    "monge", "samurai", "ronin", "kenshi", "mestre_das_laminas"
}

# TABELA DE PROGRESSÃO (STATUS BASE)
CLASS_PROGRESSIONS = {
    "guerreiro":   { "BASE": {"max_hp": 60, "attack": 6, "defense": 5, "initiative": 4, "luck": 3}, "PER_LVL": {"max_hp": 8, "attack": 2, "defense": 2, "initiative": 0, "luck": 0}, "mana_stat": "luck" },
    "berserker":   { "BASE": {"max_hp": 65, "attack": 8, "defense": 3, "initiative": 5, "luck": 3}, "PER_LVL": {"max_hp": 9, "attack": 3, "defense": 0, "initiative": 1, "luck": 0}, "mana_stat": "luck" },
    "cacador":     { "BASE": {"max_hp": 50, "attack": 7, "defense": 3, "initiative": 7, "luck": 4}, "PER_LVL": {"max_hp": 6, "attack": 2, "defense": 1, "initiative": 2, "luck": 1}, "mana_stat": "initiative" },
    "monge":       { "BASE": {"max_hp": 55, "attack": 6, "defense": 4, "initiative": 6, "luck": 3}, "PER_LVL": {"max_hp": 7, "attack": 2, "defense": 2, "initiative": 2, "luck": 0}, "mana_stat": "initiative" },
    "mago":        { "BASE": {"max_hp": 45, "attack": 8, "defense": 2, "initiative": 5, "luck": 4}, "PER_LVL": {"max_hp": 5, "attack": 1, "defense": 0, "initiative": 1, "luck": 1}, "mana_stat": "magic_attack" },
    "bardo":       { "BASE": {"max_hp": 48, "attack": 5, "defense": 3, "initiative": 5, "luck": 7}, "PER_LVL": {"max_hp": 6, "attack": 1, "defense": 1, "initiative": 1, "luck": 3}, "mana_stat": "luck" },
    "assassino":   { "BASE": {"max_hp": 48, "attack": 8, "defense": 2, "initiative": 8, "luck": 5}, "PER_LVL": {"max_hp": 5, "attack": 3, "defense": 0, "initiative": 3, "luck": 1}, "mana_stat": "initiative" },
    "samurai":     { "BASE": {"max_hp": 55, "attack": 7, "defense": 4, "initiative": 6, "luck": 4}, "PER_LVL": {"max_hp": 7, "attack": 3, "defense": 1, "initiative": 2, "luck": 0}, "mana_stat": "defense" },
    "curandeiro":  { "BASE": {"max_hp": 50, "attack": 4, "defense": 4, "initiative": 5, "luck": 5}, "PER_LVL": {"max_hp": 6, "attack": 1, "defense": 2, "initiative": 1, "luck": 2}, "mana_stat": "luck" },
    
    "_default":    { "BASE": {"max_hp": 50, "attack": 5, "defense": 3, "initiative": 5, "luck": 5}, "PER_LVL": {"max_hp": 7, "attack": 1, "defense": 1, "initiative": 1, "luck": 1}, "mana_stat": "luck" },
}

# Usado apenas para referência visual no menu (se balance.py estiver ativo, o ganho real varia)
CLASS_POINT_GAINS = {
    "_default":  {"max_hp": 3, "attack": 1, "defense": 1, "initiative": 1, "luck": 1},
    "guerreiro": {"max_hp": 4, "defense": 2}, 
    "berserker": {"max_hp": 3, "attack": 2},  
    "cacador":   {"attack": 2, "initiative": 2}, 
    "monge":     {"defense": 2, "initiative": 2}, 
    "mago":      {"max_hp": 2, "attack": 2, "luck": 2}, 
    "bardo":     {"max_hp": 3, "luck": 2}, 
    "assassino": {"attack": 2, "initiative": 2, "luck": 2}, 
    "samurai":   {"attack": 2, "defense": 2},
    "curandeiro":{"max_hp": 4, "defense": 2}, 
}

PROFILE_KEYS = ("max_hp", "attack", "defense", "initiative", "luck", "magic_attack")
_BASELINE_KEYS = ("max_hp", "attack", "defense", "initiative", "luck")

# ============================================================
# ⚔️ ATRIBUTOS ESPECIAIS DE COMBATE
#
# Estes atributos precisam manter casas decimais.
# Não podem passar por _ival(), pois 0.15 viraria 0.
# ============================================================

SPECIAL_COMBAT_FLOAT_KEYS = {
    "armor_penetration",
    "accuracy_flat",
    "crit_chance_flat",
    "crit_damage_mult",
    "double_attack_chance_flat",
    "dodge_chance_flat",
    "crit_resistance_flat",
    "hp_regen_percent",
    "mp_regen_percent",
    "lifesteal",
    "lifesteal_flat",
}

# ========================================
# 2. HELPER FUNCTIONS
# ========================================

def _ival(x: Any, default: int = 0) -> int:
    try: return int(round(float(x)))
    except: return int(default) if default else 0

def _get_class_key_normalized(pdata: dict) -> str:
    raw_class = pdata.get("class_key") or pdata.get("class") or pdata.get("classe")
    if not raw_class: return "_default"
    
    norm = str(raw_class).strip().lower().replace("_", " ") 
    raw_clean = str(raw_class).strip().lower()
    
    if raw_clean in CLASS_PROGRESSIONS: return raw_clean
    if norm in CLASS_PROGRESSIONS: return norm

    aliases = {
        "ladrao de sombras": "assassino", "ninja": "assassino",
        "cavaleiro": "guerreiro", "templario": "guerreiro",
        "barbaro": "berserker", "selvagem": "berserker",
        "patrulheiro": "cacador", "franco atirador": "cacador",
        "arquimago": "mago", "feiticeiro": "mago",
        "clerigo": "curandeiro", "sacerdote": "curandeiro",
        "ronin": "samurai", "kenshi": "samurai",
        "menestrel": "bardo", "trovador": "bardo"
    }
    if norm in aliases: return aliases[norm]

    try:
        ancestry = get_class_ancestry(raw_clean)
        for ancestor in ancestry:
            if ancestor.lower() in CLASS_PROGRESSIONS:
                return ancestor.lower()
    except Exception:
        pass
    
    return "_default"

def _map_stat_name(raw_key: str) -> str | None:
    if not raw_key:
        return None

    raw = str(
        raw_key
    ).lower().strip()


    # ========================================================
    # ⚔️ ATRIBUTOS ESPECIAIS
    #
    # Precisamos testar ANTES de remover "_",
    # porque os nomes canônicos possuem underscore.
    # ========================================================

    if raw in SPECIAL_COMBAT_FLOAT_KEYS:
        return raw


    k = (
        raw
        .replace("_", "")
        .replace(" ", "")
    )

    if k in ("ataque", "attack", "atk", "str", "forca", "strength", "dano", "fisico", "furia", "bushido", "foco", "precisao", "letalidade", "physatk"): return "attack"
    if k in ("inteligencia", "int", "matk", "magia", "magic", "magicattack", "fe", "faith", "carisma", "charisma", "arcano"): return "magic_attack"
    if k in ("defesa", "defense", "def", "armadura", "armor", "resistencia", "res", "vitality"): return "defense"
    if k in ("hp", "vida", "health", "maxhp", "vitalidade", "vit", "hpmax", "points_hp"): return "max_hp"
    if k in ("iniciativa", "initiative", "agi", "agilidade", "velocidade", "speed", "dex", "destreza"): return "initiative"
    if k in ("sorte", "luck", "luk", "critico", "crt", "chance"): return "luck"
    return None

def _base_enchant_stat_key(raw_key: str) -> str:
    """
    Remove sufixo numérico de atributo repetido.

    Ex:
    forca    -> forca
    forca_2  -> forca
    sorte_3  -> sorte
    crit_chance_flat -> crit_chance_flat
    """
    key = str(raw_key or "").strip().lower()

    if "_" in key:
        base, suffix = key.rsplit("_", 1)
        if suffix.isdigit():
            return base

    return key


def _real_enchantment_stat(entry_key: str, entry_data: dict) -> str:
    """
    Descobre o atributo real de uma entrada de enchantments.

    Novo formato:
    "forca_2": {
        "stat": "forca",
        "value": 1
    }

    Formato antigo:
    "forca": {
        "value": 1
    }
    """
    if isinstance(entry_data, dict) and entry_data.get("stat"):
        return _base_enchant_stat_key(entry_data.get("stat"))

    return _base_enchant_stat_key(entry_key)

# ========================================
# 3. CÁLCULO TOTAL DE STATUS (CORE ENGINE)
# ========================================

async def get_player_total_stats(player_data: dict, ally_user_ids: list = None) -> dict:
    from modules import player_manager
    from modules.player.premium import PremiumManager 

    # 🛡️ PROTEÇÃO INICIAL (Se o DB enviar nulo, retorna status base seguro)
    if not player_data or not isinstance(player_data, dict):
        return {"max_hp": 50, "max_mana": 20, "attack": 5, "defense": 3, "initiative": 5, "luck": 5, "magic_attack": 5}

    lvl = _ival(player_data.get("level"), 1)

    # ====================================================
    # 👇 NOVA TRAVA DE SEGURANÇA: AUTO-CORREÇÃO DE CLASSE
    # ====================================================
    classe_exibicao = str(player_data.get("class", "")).lower().strip()
    classe_chave = str(player_data.get("class_key", "")).lower().strip()

    # Se a classe de exibição não for vazia/básica e estiver diferente da chave, forçamos a cura do banco de dados na memória.
    if classe_exibicao and classe_exibicao != classe_chave and classe_exibicao not in ["", "none", "aventureiro", "aprendiz"]:
        player_data["class_key"] = classe_exibicao
        ckey = classe_exibicao
    else:
        ckey = _get_class_key_normalized(player_data)
    
    # real_class_key: Classe Real/Evoluída (usada para Balanceamento e Modificadores)
    real_class_key = str(player_data.get("class_key") or player_data.get("class") or ckey).lower()
    
    # ----------------------------------------------------
    # PASSO 1: BASE DA CLASSE (FIXO DA TABELA)
    # ----------------------------------------------------
    class_baseline = _compute_class_baseline_for_level(ckey, lvl)
    total: Dict[str, Any] = {} 
    
    for k in _BASELINE_KEYS:
        total[k] = class_baseline.get(k, 0)
    total['magic_attack'] = class_baseline.get('magic_attack', 0)

    # ----------------------------------------------------
    # PASSO 2: ESCALONAMENTO DE EVOLUÇÃO (BASE)
    # ----------------------------------------------------
    if real_class_key and real_class_key != ckey and real_class_key != "_default":
        current_mods = get_stat_modifiers(real_class_key)
        base_mods = get_stat_modifiers(ckey)
        
        if current_mods and base_mods:
            for stat_k in list(total.keys()):
                mod_k = "hp" if stat_k == "max_hp" else stat_k
                if stat_k == "magic_attack": mod_k = "inteligencia"

                mod_curr = float(current_mods.get(mod_k, 1.0))
                if stat_k == "magic_attack" and mod_curr == 1.0:
                    mod_curr = float(current_mods.get("attack", 1.0))

                mod_base = float(base_mods.get(mod_k, 1.0))
                if stat_k == "magic_attack" and mod_base == 1.0:
                    mod_base = float(base_mods.get("attack", 1.0))

                if mod_base > 0:
                    ratio = mod_curr / mod_base
                    total[stat_k] = int(total[stat_k] * ratio)

    # ----------------------------------------------------
    # PASSO 3: PONTOS INVESTIDOS (COM BALANCE.PY)
    # ----------------------------------------------------
    invested_clicks = player_data.get("invested", {})
    if not isinstance(invested_clicks, dict): invested_clicks = {}

    if balance:
        for k, clicks in invested_clicks.items():
            n_clicks = _ival(clicks, 0)
            if n_clicks <= 0: continue

            target_key = _map_stat_name(k) or k
            balance_key = "hp" if target_key == "max_hp" else target_key
            if target_key == "magic_attack": balance_key = "attack"

            if balance_key not in balance.STAT_RULES:
                gains = _get_point_gains_for_class(ckey)
                gain_per_click = gains.get(target_key, 1)
                if target_key not in total: total[target_key] = 0
                total[target_key] += (n_clicks * gain_per_click)
            else:
                added_val = balance.effect_from_points(balance_key, n_clicks, real_class_key)
                if target_key not in total: total[target_key] = 0
                total[target_key] += int(added_val)
    else:
        gains = _get_point_gains_for_class(ckey)
        for k, clicks in invested_clicks.items():
            target_key = _map_stat_name(k) or k
            if target_key == "magic_attack":
                gain = gains.get("magic_attack", gains.get("attack", 1))
                total["magic_attack"] += (_ival(clicks, 0) * gain)
            elif target_key in total or target_key in _BASELINE_KEYS:
                if target_key not in total: total[target_key] = 0
                gain_per_click = gains.get(target_key, 1)
                total[target_key] += (_ival(clicks, 0) * gain_per_click)

    # ----------------------------------------------------
    # PASSO 4: EQUIPAMENTOS E CONJUNTOS (SETS) - 🛡️ BLINDADO
    # ----------------------------------------------------
    inventory = player_data.get('inventory', {})
    equipped = player_data.get('equipment', {})
    
    # Proteção caso venham como None ou String
    if not isinstance(inventory, dict): inventory = {}
    if not isinstance(equipped, dict): equipped = {}
    
    equipped_sets = {} 

    for slot, unique_id in equipped.items():
        if not unique_id: continue
        
        # 🛡️ Verifica se o item ainda existe fisicamente no inventário
        inst = inventory.get(unique_id)
        if not isinstance(inst, dict) or is_item_broken(inst): 
            continue 
        
        def add_item_stat(
            r_stat,
            r_val,
        ):
            s_key = _map_stat_name(
                r_stat
            )


            if not s_key:
                return


            # =================================================
            # ⚔️ ATRIBUTOS ESPECIAIS
            #
            # Mantêm decimal:
            # 0.15 = 15% penetração
            # 0.05 = 5% precisão/esquiva
            # etc.
            # =================================================

            if (
                s_key
                in
                SPECIAL_COMBAT_FLOAT_KEYS
            ):

                try:
                    valor = float(
                        r_val or 0
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    valor = 0.0


                if valor <= 0:
                    return


                total[s_key] = (
                    float(
                        total.get(
                            s_key,
                            0.0
                        )
                        or 0.0
                    )
                    +
                    valor
                )


                return


            # =================================================
            # 📊 ATRIBUTOS NORMAIS
            # =================================================

            valor = _ival(
                r_val,
                0
            )


            if valor <= 0:
                return


            if s_key not in total:
                total[s_key] = 0


            total[s_key] += valor

        # 🛡️ Puxa os status com .get() de forma segura
        base_stats = inst.get('stats') or inst.get('attributes') or {}
        if isinstance(base_stats, dict):
            for k, v in base_stats.items(): add_item_stat(k, v)

        ench = inst.get('enchantments', {}) or {}
        if isinstance(ench, dict):
            for k, data in ench.items():
                if isinstance(data, dict):
                    stat_real = _real_enchantment_stat(k, data)
                    add_item_stat(stat_real, data.get('value', 0))

        # --- CONTA PEÇAS DE CONJUNTO ---
        try:
            base_id = inst.get("base_id") or inst.get("id")
            if base_id:
                from modules.game_data import equipment as equip_data
                item_info = equip_data.ITEM_DATABASE.get(base_id, {})
                set_id = item_info.get("set_id")
                
                if set_id:
                    equipped_sets[set_id] = equipped_sets.get(set_id, 0) + 1
        except Exception as e:
            logger.error(f"Erro ao contar Sets: {e}")

    # --- APLICA BÓNUS DE CONJUNTO ---
    if equipped_sets:
        try:
            from modules.game_data import equipment as equip_data
            for set_id, count in equipped_sets.items():
                set_info = equip_data.SETS_DATABASE.get(set_id)
                
                if set_info and isinstance(set_info, dict) and count >= set_info.get("pecas_necessarias", 99):
                    buffs = set_info.get("buffs", {})
                    if not isinstance(buffs, dict): continue
                    
                    if "max_hp_mult" in buffs:
                        total["max_hp"] += int(total.get("max_hp", 0) * float(buffs["max_hp_mult"]))
                        
                    if "defense_add" in buffs:
                        total["defense"] += int(buffs["defense_add"])
                        
                    if "attack_mult" in buffs:
                        total["attack"] += int(total.get("attack", 0) * float(buffs["attack_mult"]))
                        
        except Exception as e:
            logger.error(f"Erro ao aplicar Bónus de Set: {e}")

    # ----------------------------------------------------
    # PASSO 5: BÔNUS EXTERNOS (CLÃ, PREMIUM, BUFFS)
    # ----------------------------------------------------

    try:
        premium = PremiumManager(player_data)
        if premium.is_premium():
            vip_percent = float(premium.get_perk_value("all_stats_percent", 0))
            if vip_percent > 0:
                mult_vip = 1 + (vip_percent / 100.0)
                for st in ['max_hp', 'attack', 'defense', 'initiative', 'luck', 'magic_attack']:
                    if st in total: total[st] = int(total.get(st, 0) * mult_vip)
            vip_luck = int(premium.get_perk_value("bonus_luck", 0))
            if vip_luck > 0: total['luck'] += vip_luck
    except: pass

    try:
        _apply_passive_skill_bonuses(player_data, total)
        _apply_party_aura_bonuses(player_data, total)
        if ally_user_ids:
            my_id_str = str(player_data.get("user_id") or player_data.get("_id") or "")
            for ally_id in ally_user_ids:
                if str(ally_id) == my_id_str: continue
                ally_data = await player_manager.get_player_data(ally_id)
                if ally_data: _apply_party_aura_bonuses(ally_data, total)
        
        rune_bonuses = player_manager.get_rune_bonuses(player_data)
        total["runa_roubo_vida_ativa"] = float(rune_bonuses.get("lifesteal", 0) or 0) > 0
        for stat, value in rune_bonuses.items():
            k_rune = _map_stat_name(stat) or stat
            if k_rune == "crit_damage_mult":
                total[k_rune] = total.get(k_rune, 0.0) + float(value) / 100.0
            elif k_rune in SPECIAL_COMBAT_FLOAT_KEYS:
                total[k_rune] = total.get(k_rune, 0.0) + float(value)
            elif k_rune in total:
                total[k_rune] += int(value)
            elif stat == "defesa_fisica":
                total["defense"] += int(value)
    except: pass

    # ----------------------------------------------------
    # PASSO 6: TRADUTOR DE ATRIBUTOS (IDENTIDADE DE CLASSE)
    # ----------------------------------------------------
    is_magic = False
    if real_class_key in MAGIC_CLASSES: is_magic = True
    else:
        try:
            ancestry = get_class_ancestry(real_class_key)
            if any(c in MAGIC_CLASSES for c in ancestry): is_magic = True
        except: pass

    if is_magic:
        raw_attack = total.get("attack", 0)
        
        # 1. A Magia continua absorvendo 100% da força do painel
        total["magic_attack"] = total.get("magic_attack", 0) + raw_attack
        
        # 2. Regula o Ataque Normal: Deixa com 40% da força.
        # Assim não tira apenas 8 de dano, mas também não dá 58 de dano físico igual um Guerreiro!
        total["attack"] = max(1, int(raw_attack * 0.4))
        
    is_agility = False
    if real_class_key in AGILITY_CLASSES: is_agility = True
    else:
        try:
            ancestry = get_class_ancestry(real_class_key)
            if any(c in AGILITY_CLASSES for c in ancestry): is_agility = True
        except: pass

    if is_agility:
        # O ASSASSINO BRILHA AQUI: Como ele distribui pontos em "Agilidade" (Iniciativa),
        # nós fazemos a Agilidade se transformar diretamente em Dano Letal!
        # Transforma 80% de toda a Agilidade em Poder de Ataque extra.
        agilidade_total = total.get('initiative', 0)
        total['attack'] += int(agilidade_total * 0.8)
    
    _calculate_mana(player_data, total, ckey_fallback=ckey)
    
    for k in total:

        if (
            k
            in
            SPECIAL_COMBAT_FLOAT_KEYS
        ):

            try:

                total[k] = max(
                    0.0,
                    float(
                        total.get(
                            k,
                            0.0
                        )
                        or 0.0
                    ),
                )

            except (
                TypeError,
                ValueError,
            ):

                total[k] = 0.0


        elif k != "resistance":

            total[k] = max(
                0,
                _ival(
                    total.get(
                        k
                    ),
                    0
                ),
            )
    
    total['max_hp'] = max(1, total.get('max_hp', 1))
    total['max_mana'] = max(10, total.get('max_mana', 10))
    
    return total

async def sync_player_stats_to_db(user_id: str, player_data: dict) -> None:
    """
    Recalcula todos os atributos totais do jogador (HP, MP, Attack, etc)
    e os salva de volta no banco de dados para evitar dessincronização.
    Chame isso sempre após um Level Up ou mudança de equipamento.
    """
    # 1. Puxa os cálculos completos e blindados da engine
    total_stats = await get_player_total_stats(player_data)
    
    # 2. Copia os resultados para a raiz do documento
    for stat_key, value in total_stats.items():
        player_data[stat_key] = value
        
    # Garante que as cópias na chave "stats" também fiquem iguais
    if "stats" not in player_data:
        player_data["stats"] = {}
    
    for stat_key, value in total_stats.items():
        player_data["stats"][stat_key] = value

    # Atualiza base_stats com a matemática correta do nível
    lvl = player_data.get("level", 1)
    ckey = _get_class_key_normalized(player_data)
    baseline = _compute_class_baseline_for_level(ckey, lvl)
    player_data["base_stats"] = baseline

    # 3. Salva os dados atualizados no MongoDB usando a função blindada do core.py
    await save_player_data(user_id, player_data)
    
async def get_player_dodge_chance(player_data: dict, ally_user_ids: list = None) -> float:
    total_stats = await get_player_total_stats(player_data, ally_user_ids)
    initiative = total_stats.get('initiative', 0)
    dodge_chance = min(0.25, (initiative * 0.25) / 100.0)
    dodge_chance += total_stats.get('dodge_chance_flat', 0)
    return min(dodge_chance, 0.75)

async def get_player_double_attack_chance(player_data: dict, ally_user_ids: list = None) -> float:
    total_stats = await get_player_total_stats(player_data, ally_user_ids)
    initiative = total_stats.get('initiative', 0)
    double_attack_chance = (initiative * 0.25 + total_stats.get("double_attack_chance_flat", 0)) / 100.0
    return min(double_attack_chance, 0.50)

# ========================================
# 4. FUNÇÕES DE SUPORTE
# ========================================

def _calculate_mana(pdata: dict, total_stats: dict, ckey_fallback: str | None):
    ckey = _get_class_key_normalized(pdata) or ckey_fallback
    prog = CLASS_PROGRESSIONS.get(ckey) or CLASS_PROGRESSIONS["_default"]
    mana_stat = prog.get("mana_stat", "luck")
    
    # Se for magic_attack, agora o sistema encontrará o valor correto
    if mana_stat == "magic_attack":
        mana_val = total_stats.get("magic_attack", 0)
        multiplier = 3
    else:
        mana_val = total_stats.get(mana_stat, 0)
        multiplier = 5
        
    # Calcula a mana natural gerada pelos atributos da classe
    mana_base_calculada = 20 + (mana_val * multiplier)
    
    # Soma a mana natural com a mana bónus que já estava acumulada dos equipamentos
    total_stats['max_mana'] = total_stats.get('max_mana', 0) + mana_base_calculada
    
def allowed_points_for_level(pdata: dict) -> int:
    lvl = _ival(pdata.get("level"), 1)
    return max(0, lvl - 1)

async def reset_stats_and_refund_points(pdata: dict) -> int:
    lvl = _ival(pdata.get("level"), 1)
    ckey = _get_class_key_normalized(pdata)
    
    class_baseline = _compute_class_baseline_for_level(ckey, lvl)
    
    for k in _BASELINE_KEYS:
        pdata[k] = class_baseline.get(k, 0)
    pdata["base_stats"] = class_baseline.copy()

    should_have_points = allowed_points_for_level(pdata)
    pdata["stat_points"] = should_have_points
    pdata["invested"] = {}
    
    pdata["current_hp"] = max(1, pdata.get("max_hp", 100))
    pdata["current_mp"] = max(10, pdata.get("max_mana", 10))

    return should_have_points

def _compute_class_baseline_for_level(class_key: str, level: int) -> dict:
    lvl = max(1, int(level or 1))
    ckey = (class_key or "").lower()
    
    prog = CLASS_PROGRESSIONS.get(ckey)
    if not prog:
        try:
            ancestry = get_class_ancestry(ckey) 
            if ancestry:
                for ancestor in reversed(ancestry):
                    if ancestor.lower() in CLASS_PROGRESSIONS:
                        prog = CLASS_PROGRESSIONS[ancestor.lower()]
                        break
        except: pass
        
    if not prog: prog = CLASS_PROGRESSIONS["_default"]
    
    base = dict(prog["BASE"])
    per = dict(prog["PER_LVL"])
    
    levels_up = lvl - 1
    out: Dict[str, int] = {}
    for k in _BASELINE_KEYS:
        out[k] = _ival(base.get(k)) + (_ival(per.get(k)) * levels_up)
    return out

def check_and_apply_level_up(player_data: dict) -> tuple[int, int, str]:
    levels_gained, points_gained = 0, 0
    current_xp = int(player_data.get('xp', 0))
    ckey = _get_class_key_normalized(player_data)

    while True:
        current_level = int(player_data.get('level', 1))
        xp_needed = int(game_data.get_xp_for_next_combat_level(current_level))
        if xp_needed <= 0 or current_xp < xp_needed: break
        
        current_xp -= xp_needed
        # Baseline update apenas para HP
        old_baseline = _compute_class_baseline_for_level(ckey, current_level)
        new_baseline = _compute_class_baseline_for_level(ckey, current_level + 1)
        hp_increase = max(0, new_baseline.get("max_hp", 0) - old_baseline.get("max_hp", 0))

        player_data['level'] = current_level + 1
        player_data["current_hp"] = int(player_data.get("current_hp", 1) + hp_increase)
        
        levels_gained += 1
        points_gained += 1 

    if levels_gained > 0:
        player_data['xp'] = current_xp
        current_balance = int(player_data.get('stat_points', 0))
        player_data['stat_points'] = current_balance + points_gained

    level_up_message = ""
    if levels_gained > 0:
        nivel_txt = "nível" if levels_gained == 1 else "níveis"
        ponto_txt = "ponto" if points_gained == 1 else "pontos"
        level_up_message = (
            f"\n\n✨ <b>Parabéns!</b> Você subiu {levels_gained} {nivel_txt} "
            f"(agora Nv. {player_data['level']}) e ganhou {points_gained} {ponto_txt} de atributo."
        )
    return levels_gained, points_gained, level_up_message

def needs_class_choice(player_data: dict) -> bool:
    lvl = _ival(player_data.get("level"), 1)
    
    # Pega a classe atual (se não tiver, fica vazio)
    current_class = str(player_data.get("class", "")).lower().strip()
    
    # Considera que o jogador JÁ TEM classe apenas se a classe for diferente de vazio, aventureiro ou aprendiz
    already_has_class = current_class not in ["", "none", "aventureiro", "aprendiz"]
    
    already_offered = bool(player_data.get("class_choice_offered"))
    
    return (lvl >= 5) and (not already_has_class) and (not already_offered)

async def mark_class_choice_offered(user_id: Union[str, int]):
    from .core import get_player_data, save_player_data
    uid = str(user_id) if isinstance(user_id, int) else user_id
    pdata = await get_player_data(uid)
    if not pdata: return
    pdata["class_choice_offered"] = True
    await save_player_data(uid, pdata)

def _get_point_gains_for_class(ckey: str) -> dict:
    norm_key = (ckey or "").lower()
    gains = CLASS_POINT_GAINS.get(norm_key)
    if gains is None and norm_key != "_default":
        try:
            ancestry = get_class_ancestry(norm_key)
            if ancestry:
                base_class = ancestry[-1]
                gains = CLASS_POINT_GAINS.get(base_class.lower())
        except: pass
    if gains is None: gains = CLASS_POINT_GAINS["_default"]
    return gains

def compute_spent_status_points(pdata: dict) -> int:
    inv = pdata.get("invested")
    if isinstance(inv, dict):
        return sum(int(v) for v in inv.values())
    return 0

def has_completed_dungeon(player_data: dict, dungeon_id: str, difficulty: str) -> bool:
    completions = player_data.get("dungeon_completions", {})
    return difficulty in completions.get(dungeon_id, [])

def can_see_evolution_menu(player_data: dict) -> bool:
    current_class = player_data.get("class")
    if not current_class: return False
    player_level = player_data.get("level", 1)
    all_options = get_evolution_options(current_class, player_level, show_locked=True)
    return bool(all_options)

def mark_dungeon_as_completed(player_data: dict, dungeon_id: str, difficulty: str):
    if "dungeon_completions" not in player_data: player_data["dungeon_completions"] = {}
    if dungeon_id not in player_data["dungeon_completions"]: player_data["dungeon_completions"][dungeon_id] = []
    if difficulty not in player_data["dungeon_completions"][dungeon_id]: player_data["dungeon_completions"][dungeon_id].append(difficulty)

async def apply_class_change_and_recalculate(player_data: dict, new_class_key: str):
    lvl = _ival(player_data.get("level"), 1)
    player_data["class"] = new_class_key
    player_data["class_key"] = new_class_key
    if "class_tag" in player_data: del player_data["class_tag"]
    await reset_stats_and_refund_points(player_data)
    player_data["class_choice_offered"] = True
    return player_data

def add_xp(player_data: dict, amount: int):
    if not player_data: return
    current_xp = player_data.get("xp", 0)
    try:
        amount = int(amount)
        current_xp = int(current_xp)
    except: amount = 0
    player_data["xp"] = current_xp + amount

def _apply_passive_skill_bonuses(pdata: dict, total_stats: dict):
    player_skills_dict = pdata.get("skills", {})
    if not isinstance(player_skills_dict, dict): return
    for skill_id, skill_info in player_skills_dict.items():
        if not isinstance(skill_info, dict): continue 
        skill_data = SKILL_DATA.get(skill_id)
        if not skill_data or skill_data.get("type") != "passive": continue 
        rarity = skill_info.get("rarity", "comum")
        rarity_effects_data = skill_data.get("rarity_effects", {}).get(rarity)
        if not rarity_effects_data: continue
        effects = rarity_effects_data.get("effects", {})
        if not effects: continue

        stat_bonuses = effects.get("stat_add_mult", {})
        if stat_bonuses:
            for stat, multiplier in stat_bonuses.items():
                target = _map_stat_name(stat) or stat
                if target in SPECIAL_COMBAT_FLOAT_KEYS:
                    amount = float(multiplier)
                    if target == "crit_chance_flat" and 0 < amount <= 1:
                        amount *= 100.0
                    total_stats[target] = total_stats.get(target, 0.0) + amount
                elif target in total_stats:
                    bonus_valor = total_stats[target] * float(multiplier)
                    total_stats[target] += int(bonus_valor)
                elif target == "magic_attack": 
                    if "magic_attack" not in total_stats: total_stats["magic_attack"] = total_stats.get("attack", 0)
                    total_stats["magic_attack"] += int(total_stats.get("magic_attack", 0) * float(multiplier))

        for key in ("crit_resistance_flat", "double_attack_chance_flat", "hp_regen_percent", "mp_regen_percent", "lifesteal_flat"):
            total_stats[key] = total_stats.get(key, 0.0) + float(effects.get(key, 0.0) or 0.0)
        if effects.get("cannot_be_dodged"):
            total_stats["cannot_be_dodged"] = True

        res_bonuses = effects.get("resistance_mult", {})
        if res_bonuses:
            if "resistance" not in total_stats: total_stats["resistance"] = {}
            for res_type, value in res_bonuses.items():
                total_stats["resistance"][res_type] = total_stats["resistance"].get(res_type, 0.0) + float(value)
        if effects.get("crit_immune", False): total_stats["crit_immune"] = True 

        scaling = effects.get("stat_scaling")
        if scaling:
            try:
                src = _map_stat_name(scaling["source_stat"]) or scaling["source_stat"]
                tgt = _map_stat_name(scaling["target_stat"]) or scaling["target_stat"]
                val = total_stats.get(src, 0)
                bonus = val * float(scaling["ratio"])
                if tgt in total_stats: total_stats[tgt] += int(bonus)
                else: total_stats[tgt] = total_stats.get(tgt, 0.0) + bonus
            except: pass

def _apply_party_aura_bonuses(ally_data: dict, target_stats: dict):
    ally_skills_dict = ally_data.get("skills", {})
    if not isinstance(ally_skills_dict, dict): return
    for skill_id, skill_info in ally_skills_dict.items():
        if not isinstance(skill_info, dict): continue
        skill_data = SKILL_DATA.get(skill_id)
        if not skill_data or skill_data.get("type") != "passive": continue
        rarity = skill_info.get("rarity", "comum")
        rarity_effects_data = skill_data.get("rarity_effects", {}).get(rarity)
        if not rarity_effects_data: continue
        effects = rarity_effects_data.get("effects", {})
        aura_bonuses = effects.get("party_aura", {})
        if not aura_bonuses: continue 
        stat_bonuses = aura_bonuses.get("stat_add_mult", {})
        if stat_bonuses:
            for stat, multiplier in stat_bonuses.items():
                target = _map_stat_name(stat) or stat
                if target in SPECIAL_COMBAT_FLOAT_KEYS:
                    amount = float(multiplier)
                    if target == "crit_chance_flat" and 0 < amount <= 1:
                        amount *= 100.0
                    target_stats[target] = target_stats.get(target, 0.0) + amount
                elif target in target_stats:
                    bonus_valor = target_stats[target] * float(multiplier)
                    target_stats[target] += int(bonus_valor)
                else:
                    target_stats[target] = target_stats.get(target, 0.0) + float(multiplier)
        for kind, amount in aura_bonuses.get("resistance_mult", {}).items():
            resistances = target_stats.setdefault("resistance", {})
            resistances[kind] = resistances.get(kind, 0.0) + float(amount)
        if aura_bonuses.get("cannot_be_dodged", False): target_stats["cannot_be_dodged"] = True
        if "hp_regen_percent" in aura_bonuses:
             target_stats["hp_regen_percent"] = target_stats.get("hp_regen_percent", 0.0) + float(aura_bonuses["hp_regen_percent"])
        if "mp_regen_percent" in aura_bonuses:
             target_stats["mp_regen_percent"] = target_stats.get("mp_regen_percent", 0.0) + float(aura_bonuses["mp_regen_percent"])



def _recuperar_recursos_combate(stats, hp, mp, dano_real=0, regenerar=False):
    """Regenera por turno ou rouba vida do dano efetivo, sem ressuscitar."""
    if hp <= 0:
        return hp, mp
    max_hp = int(stats.get("max_hp", hp))
    max_mp = int(stats.get("max_mana", mp))
    taxa = min(1.0, max(0.0, float(stats.get("lifesteal", 0)) / 100.0 + float(stats.get("lifesteal_flat", 0))))
    cura = int(max(0, dano_real) * taxa)
    mana = 0
    if regenerar:
        cura += int(max_hp * min(1.0, max(0.0, float(stats.get("hp_regen_percent", 0)))))
        mana = int(max_mp * min(1.0, max(0.0, float(stats.get("mp_regen_percent", 0)))))
    return hp + min(max(0, max_hp - hp), cura), mp + min(max(0, max_mp - mp), mana)


def _aplicar_golpes_combate(resultado, stats, hp, mp, mob_hp):
    """Aplica dano e roubo de vida por golpe, na ordem apresentada ao jogador."""
    logs = []
    hits = resultado.get("hits", [])
    por_log = {hit["log_index"]: hit for hit in hits}
    for index, texto in enumerate(resultado.get("log_messages", [])):
        hit = por_log.get(index)
        if hit is None:
            logs.append({"autor": "player", "texto": texto, "dano": 0})
            continue
        if mob_hp <= 0:
            break
        dano = min(mob_hp, max(0, int(hit["damage"])))
        hp_antes = hp
        hp, mp = _recuperar_recursos_combate(stats, hp, mp, dano)
        mob_hp -= dano
        cura = hp - hp_antes
        numero = hit["hit_number"]
        mostrar_roubo = bool(stats.get("runa_roubo_vida_ativa")) and cura > 0
        mensagem = f"Ataque {numero}: {dano} de dano."
        if mostrar_roubo:
            mensagem += f" Roubou {cura} de vida."
        if hit.get("critical"):
            mensagem = f"Crítico! {mensagem}"
        logs.append({
            "autor": "player", "texto": mensagem, "dano": dano,
            "golpe": numero, "critico": bool(hit.get("critical")),
            "roubo_vida": cura, "mostrar_roubo_vida": mostrar_roubo, "player_hp_apos_golpe": hp,
            "mob_hp_apos_golpe": mob_hp,
            "anim_effect": resultado.get("anim_effect", ""),
            "tipo_skill": resultado.get("tipo_skill", ""),
        })
    return hp, mp, mob_hp, logs


def _get_skill_data_mesclada(pdata: dict, skill_id: str) -> dict | None:
    """Retorna a skill já mesclada com os dados da raridade do jogador."""
    if not skill_id:
        return None

    base_skill = SKILL_DATA.get(skill_id)
    if not base_skill:
        return None

    merged = base_skill.copy()

    rarity = "comum"
    player_skills = pdata.get("skills", {})
    if isinstance(player_skills, dict):
        inst = player_skills.get(skill_id)
        if isinstance(inst, dict):
            rarity = inst.get("rarity", "comum") or "comum"

    rarity_data = (base_skill.get("rarity_effects", {}) or {}).get(
        rarity,
        (base_skill.get("rarity_effects", {}) or {}).get("comum", {})
    ) or {}

    merged.update(rarity_data)
    return merged


def _get_skill_rarity(pdata: dict, skill_id: str) -> str:
    player_skills = pdata.get("skills", {})
    if isinstance(player_skills, dict):
        inst = player_skills.get(skill_id)
        if isinstance(inst, dict):
            return inst.get("rarity", "comum") or "comum"
    return "comum"


def _is_skill_suporte(skill_data: dict | None) -> bool:
    """Detecta skills que curam/buffam aliados, sem capturar debuffs ofensivos."""
    if not skill_data:
        return False

    effects = skill_data.get("effects", {}) or {}

    if effects.get("target") in ["ally", "party", "grupo"]:
        return True

    chaves_suporte = {
        "party_heal",
        "party_mana",
        "party_buff",
        "self_heal_percent",
        "heal_type",
        "heal_scale",
        "on_heal_buff",
        "on_heal_low_hp_buff",
    }

    return any(chave in effects for chave in chaves_suporte)


def _calcular_cura_suporte(cura_def: dict, caster_stats: dict, alvo_stats: dict) -> int:
    """Calcula cura para party_heal, cura em alvo único e curas percentuais."""
    if not isinstance(cura_def, dict):
        return 0

    max_hp_alvo = int(alvo_stats.get("max_hp", alvo_stats.get("hp_max", 1)) or 1)

    if "amount_flat" in cura_def:
        return max(0, int(cura_def.get("amount_flat", 0) or 0))

    if "amount_percent_max_hp" in cura_def:
        pct = float(cura_def.get("amount_percent_max_hp", 0) or 0)
        return max(0, int(max_hp_alvo * pct))

    if "amount_based_on_def" in cura_def:
        escala = float(cura_def.get("amount_based_on_def", 0) or 0)
        return max(0, int(int(caster_stats.get("defense", 0) or 0) * escala))

    heal_type = cura_def.get("heal_type")
    heal_scale = float(cura_def.get("heal_scale", 0) or 0)

    if heal_type == "magic_attack":
        base = int(caster_stats.get("magic_attack", 0) or 0)
        if base <= 0:
            # fallback para classes híbridas/suporte que ainda não têm magic_attack alto
            base = int(caster_stats.get("attack", 0) or 0)
        return max(0, int(base * heal_scale))

    if heal_type == "percent_max_hp":
        return max(0, int(max_hp_alvo * heal_scale))

    if heal_type == "max_hp":
        return max(0, int(int(caster_stats.get("max_hp", 0) or 0) * heal_scale))

    return 0


def _calcular_mana_suporte(mana_def: dict, alvo_stats: dict) -> int:
    if not isinstance(mana_def, dict):
        return 0

    if "amount_flat" in mana_def:
        return max(0, int(mana_def.get("amount_flat", 0) or 0))

    if "amount_percent_max_mp" in mana_def:
        max_mp = int(alvo_stats.get("max_mana", alvo_stats.get("max_mp", 0)) or 0)
        pct = float(mana_def.get("amount_percent_max_mp", 0) or 0)
        return max(0, int(max_mp * pct))

    return 0


def _nome_buff_suporte(buff_def: dict) -> str:
    if not isinstance(buff_def, dict):
        return "Bênção de suporte"

    if buff_def.get("buff_name"):
        valor = buff_def.get("buff_value")
        duracao = buff_def.get("duration") or buff_def.get("duration_turns")
        partes = [str(buff_def.get("buff_name"))]
        if valor:
            partes.append(str(valor))
        if duracao:
            partes.append(f"({duracao})")
        return " - ".join(partes)

    efeito = buff_def.get("effect") or buff_def.get("stat") or "buff"
    duracao = buff_def.get("duration") or buff_def.get("duration_turns")
    if duracao:
        return f"{efeito} ({duracao} turnos)"
    return str(efeito)

def _dur_tuple_combate(raw) -> tuple[int, int]:
    cur, mx = 0, 0

    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        try:
            cur = int(raw[0])
            mx = int(raw[1])
        except Exception:
            cur, mx = 0, 0

    elif isinstance(raw, dict):
        try:
            cur = int(raw.get("current", raw.get("cur", 0)))
            mx = int(raw.get("max", raw.get("mx", 0)))
        except Exception:
            cur, mx = 0, 0

    mx = max(0, mx)
    cur = max(0, min(cur, mx)) if mx > 0 else max(0, cur)

    return cur, mx


def _set_dur_combate(item: dict, cur: int, mx: int) -> None:
    item["durability"] = [int(max(0, min(cur, mx))), int(max(0, mx))]


def _nome_item_combate(item: dict, uid: str = "") -> str:
    if not isinstance(item, dict):
        return str(uid or "Item")

    if item.get("display_name"):
        return str(item.get("display_name"))

    if item.get("nome"):
        return str(item.get("nome"))

    base_id = item.get("base_id") or uid or "item"
    return str(base_id).replace("_", " ").title()


def _gastar_durabilidade_equipamentos_combate(
    player_data: dict,
    *,
    gastar_arma: bool = False,
    gastar_defesa: bool = False,
    custo_arma: int = 1,
    custo_defesa: int = 1,
    chance_arma: float = 0.30,
    chance_defesa: float = 0.30
) -> dict:
    """
    Gasta durabilidade dos equipamentos de combate.

    Regras:
    - 30% de chance da arma gastar quando causa dano.
    - 30% de chance de UMA peça defensiva gastar quando recebe dano.
    - ferramentas de profissão em equipment_tools NÃO gastam em combate.
    """
    import random

    inventory = player_data.get("inventory", {}) or {}
    equipment = player_data.get("equipment", {}) or {}

    if not isinstance(inventory, dict):
        inventory = {}

    if not isinstance(equipment, dict):
        equipment = {}

    alterados = []
    quebrados = []

    def gastar_slot(slot: str, custo: int):
        uid = equipment.get(slot)

        if not uid:
            return

        item = inventory.get(uid)

        if not isinstance(item, dict):
            return

        cur, mx = _dur_tuple_combate(item.get("durability"))

        # Item sem durabilidade não é afetado.
        if mx <= 0:
            return

        # Já quebrado, não reduz mais.
        if cur <= 0:
            return

        novo_cur = max(0, cur - int(max(1, custo)))
        _set_dur_combate(item, novo_cur, mx)

        inventory[uid] = item

        alterados.append({
            "slot": slot,
            "uid": uid,
            "nome": _nome_item_combate(item, uid),
            "durability": item.get("durability")
        })

        if novo_cur <= 0:
            quebrados.append({
                "slot": slot,
                "uid": uid,
                "nome": _nome_item_combate(item, uid)
            })

    # 1. Arma: 30% de chance ao causar dano.
    if gastar_arma and random.random() <= float(chance_arma):
        gastar_slot("arma", custo_arma)

    # 2. Defesa: 30% de chance de gastar UMA peça aleatória ao receber dano.
    if gastar_defesa and random.random() <= float(chance_defesa):
        slots_defesa = [
            "elmo",
            "armadura",
            "calca",
            "luvas",
            "botas",
            "colar",
            "anel",
            "brinco"
        ]

        slots_validos = []

        for slot in slots_defesa:
            uid = equipment.get(slot)
            if not uid:
                continue

            item = inventory.get(uid)
            if not isinstance(item, dict):
                continue

            cur, mx = _dur_tuple_combate(item.get("durability"))

            if mx > 0 and cur > 0:
                slots_validos.append(slot)

        if slots_validos:
            slot_sorteado = random.choice(slots_validos)
            gastar_slot(slot_sorteado, custo_defesa)

    player_data["inventory"] = inventory

    mensagens = []

    for item in quebrados:
        mensagens.append(f"⚠️ {item['nome']} quebrou durante o combate.")

    return {
        "alterados": alterados,
        "quebrados": quebrados,
        "mensagens": mensagens
    }

async def processar_turno_combate(
    user_id,
    acao,
    spawn_id,
    skill_id,
    sistema_cacada,
    MONSTERS_DATA,
    processar_acao_combate,
    sala_id=None,
    modo_grupo=False,
    target_id=None,
):
    from modules import player_manager
    from bson import ObjectId
    from modules.game_data.items_consumables import CONSUMABLES_DATA
    from modules.cooldowns import iniciar_turno

    await player_manager.clear_player_cache(ObjectId(user_id))
    player = users_collection.find_one({"_id": ObjectId(user_id)})
    if not player:
        return {"erro": "Herói não encontrado!"}

    # Localiza o mob antes de gastar turno/cooldown.
    mob_vivo = None
    regiao_atual = None
    for regiao, mobs in sistema_cacada.mobs_vivos.items():
        if spawn_id in mobs:
            mob_vivo = mobs[spawn_id]
            regiao_atual = regiao
            break

    if not mob_vivo:
        return {"erro": "O monstro sumiu!"}

    mob_hp = int(mob_vivo.get("hp_atual", mob_vivo.get("hp", 0)) or 0)

    # =============================================================
    # 🤝 VALIDA SALA/TURNO DE GRUPO ANTES DE GASTAR AÇÃO
    # =============================================================
    sala_grupo = None
    sala_retorno = None
    estado_grupo = None

    try:
        from modules.combat import group_combat_manager as gcm

        if sala_id:
            sala_grupo = gcm.obter_sala(str(sala_id))

        if not sala_grupo:
            sala_grupo = gcm.obter_sala_por_spawn(regiao_atual, spawn_id)

        if sala_id and not sala_grupo:
            return {'erro': 'A sala do grupo não está mais disponível.'}
        if sala_grupo:
            if str(user_id) not in list(map(str, sala_grupo.get('membros_ids', []))):
                return {'erro': 'Você não participa desta caçada.'}
            if str(gcm.pegar_combatente_atual(sala_grupo['sala_id'])) != str(user_id) and sala_grupo.get('estado') == gcm.ESTADO_EM_ANDAMENTO:
                return {'erro': 'Aguarde sua vez de agir.', 'sala': gcm.pacote_estado_sala(sala_grupo['sala_id'])}
            sala_id_real = sala_grupo["sala_id"]
            sala_retorno = gcm.pacote_estado_sala(sala_id_real)

            if sala_grupo.get("estado") != gcm.ESTADO_EM_ANDAMENTO:
                return {
                    "erro": "Aguardando todos os membros carregarem o combate.",
                    "grupo": True,
                    "sala_id": sala_id_real,
                    "sala": sala_retorno,
                    "mob_hp_atual": mob_hp,
                    "log": [],
                }
            
    except Exception as e:
        print("Erro ao validar turno de grupo:", e)
        return {"erro": "Não foi possível validar o turno. Tente novamente."}

    if int(player.get('current_hp', 0) or 0) <= 0:
        return {'erro': 'Seu herói está derrotado e não pode agir.'}
    if mob_hp <= 0:
        return {'erro': 'Este monstro já foi derrotado.'}
    # Cooldowns só passam depois que confirmou que era a vez do jogador.
    player, msgs_cooldown = iniciar_turno(player)

    aliados_ids = sala_grupo.get('membros_ids', []) if sala_grupo else None
    player_stats = await get_player_total_stats(player, aliados_ids)
    player_hp = int(player.get("current_hp", 50) or 0)
    player_mp = int(player.get("current_mp", 50) or 0)
    inventory = player.get("inventory", {}) or {}

    monster_id_real = mob_vivo.get("monster_id")
    mob_template = next(
        (
            m
            for cat, mobs in MONSTERS_DATA.items()
            if not cat.startswith("_")
            for m in mobs
            if m.get("id") == monster_id_real
        ),
        None,
    )

    mob_status_luta = mob_template.copy() if mob_template else {}
    mob_status_luta["attack"] = mob_vivo.get("attack", mob_status_luta.get("attack", 5))
    mob_status_luta["defense"] = mob_vivo.get("defense", mob_status_luta.get("defense", 0))
    mob_status_luta["xp_reward"] = mob_vivo.get("xp_reward", mob_status_luta.get("xp_reward", 0))
    mob_status_luta["gold_drop"] = mob_vivo.get("gold_drop", mob_status_luta.get("gold_drop", 0))
    mob_status_luta["hp"] = mob_hp
    mob_status_luta["max_hp"] = int(mob_vivo.get("hp_max", mob_vivo.get("hp", mob_hp)) or mob_hp)

    log_turno = []
    for msg in msgs_cooldown:
        log_turno.append({"autor": "sistema", "texto": msg, "dano": 0, "tipo": "suporte"})

    dano_heroi = 0
    acao_suporte_grupo = False

    # =============================================================
    # 4. AÇÃO DO JOGADOR
    # =============================================================
    skill_data_mesclada = _get_skill_data_mesclada(player, skill_id) if acao == "magia" and skill_id else None
    eh_skill_suporte = _is_skill_suporte(skill_data_mesclada)

    if acao == "usar_item":
        item_inst = inventory.get(skill_id)
        if not item_inst:
            return {"erro": "Item não encontrado!"}

        qtd = int(item_inst.get("quantity") if isinstance(item_inst, dict) else item_inst)
        if qtd <= 0:
            return {"erro": "Você não tem mais este item!"}

        item_static = CONSUMABLES_DATA.get(skill_id, {})
        efeitos = item_static.get("effects", {})
        cura_hp = int(efeitos.get("heal", 0))
        cura_mp = int(efeitos.get("mana", efeitos.get("mp", 0)))

        player_hp = min(player_stats.get("max_hp", 100), player_hp + cura_hp)
        player_mp = min(player_stats.get("max_mana", 50), player_mp + cura_mp)

        if isinstance(item_inst, dict):
            item_inst["quantity"] = qtd - 1
            if item_inst["quantity"] <= 0:
                inventory.pop(skill_id, None)
        else:
            inventory[skill_id] = qtd - 1
            if inventory[skill_id] <= 0:
                inventory.pop(skill_id, None)

        log_turno.append({
            "autor": "player",
            "texto": f"🧪 Usou {item_static.get('display_name', 'Item')}!",
            "dano": 0,
            "tipo": "cura",
        })

    elif eh_skill_suporte:
        # =========================================================
        # 🤝 SKILL DE SUPORTE / CURA / BUFF DE GRUPO
        # =========================================================
        acao_suporte_grupo = True
        from modules.cooldowns import verificar_cooldown, aplicar_cooldown

        nome_skill = skill_data_mesclada.get("display_name", "Habilidade de Suporte")
        effects = skill_data_mesclada.get("effects", {}) or {}
        rarity = _get_skill_rarity(player, skill_id)

        pode_usar, msg_erro = verificar_cooldown(player, skill_id)
        if not pode_usar:
            users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"cooldowns": player.get("cooldowns", {})}}
            )
            return {
                "erro": msg_erro,
                "grupo": sala_retorno is not None,
                "sala_id": sala_retorno.get("sala_id") if sala_retorno else None,
                "sala": sala_retorno,
                "mob_hp_atual": mob_hp,
                "player_hp": player_hp,
                "player_mp": player_mp,
                "cooldowns": player.get("cooldowns", {}),
                "log": [],
            }

        mana_cost = int(skill_data_mesclada.get("mana_cost", skill_data_mesclada.get("mp_cost", 0)) or 0)
        if player_mp < mana_cost:
            return {
                "erro": f"Mana insuficiente! Precisa de {mana_cost} MP.",
                "grupo": sala_retorno is not None,
                "sala_id": sala_retorno.get("sala_id") if sala_retorno else None,
                "sala": sala_retorno,
                "mob_hp_atual": mob_hp,
                "player_hp": player_hp,
                "player_mp": player_mp,
                "cooldowns": player.get("cooldowns", {}),
                "log": [],
            }

        player_mp -= mana_cost
        player["current_mp"] = player_mp
        player = aplicar_cooldown(player, skill_id, rarity)

        herois_sala = sala_grupo.get("herois", {}) if sala_grupo else {str(user_id): player}

        membros_vivos = []
        for hid, hdata in (herois_sala or {}).items():
            hp_h = int(hdata.get("current_hp", hdata.get("hp", 1)) or 0)
            if hp_h > 0:
                membros_vivos.append(str(hid))

        target_mode = effects.get("target")
        tem_efeito_party = any(k in effects for k in ["party_heal", "party_mana", "party_buff"])

        if effects.get("self_heal_percent") and not tem_efeito_party:
            alvos_ids = [str(user_id)]
        elif target_mode == "ally":
            target_id_str = str(target_id or "")
            if target_id_str and target_id_str in membros_vivos:
                alvos_ids = [target_id_str]
            else:
                # Sem seleção no frontend ainda: cura quem estiver com menor % de HP.
                menor_id = str(user_id)
                menor_pct = 999.0
                for hid in membros_vivos:
                    h = herois_sala.get(hid, {}) or {}
                    hp_atual_tmp = int(h.get("current_hp", h.get("hp", 0)) or 0)
                    hp_max_tmp = int(h.get("max_hp", 0) or 0)
                    if hp_max_tmp <= 0:
                        try:
                            pdata_tmp = users_collection.find_one({"_id": ObjectId(hid)}) or {}
                            stats_tmp = await get_player_total_stats(pdata_tmp)
                            hp_max_tmp = int(stats_tmp.get("max_hp", 1) or 1)
                        except Exception:
                            hp_max_tmp = 1
                    pct = hp_atual_tmp / max(1, hp_max_tmp)
                    if pct < menor_pct:
                        menor_pct = pct
                        menor_id = hid
                alvos_ids = [menor_id]
        else:
            alvos_ids = membros_vivos or [str(user_id)]

        cura_def = effects.get("party_heal") if isinstance(effects.get("party_heal"), dict) else None
        mana_def = effects.get("party_mana") if isinstance(effects.get("party_mana"), dict) else None
        buff_def = effects.get("party_buff") if isinstance(effects.get("party_buff"), dict) else None

        # Algumas skills de alvo único/party usam heal_type diretamente no effects.
        if not cura_def and (effects.get("heal_type") or effects.get("heal_scale") or effects.get("amount_percent_max_hp")):
            cura_def = effects

        total_cura = 0
        total_mana = 0
        alvos_nome = []

        for alvo_id in alvos_ids:
            alvo_id = str(alvo_id)
            try:
                alvo_player = player if alvo_id == str(user_id) else (users_collection.find_one({"_id": ObjectId(alvo_id)}) or {})
            except Exception:
                alvo_player = {}

            if alvo_id == str(user_id):
                alvo_stats = player_stats
            else:
                alvo_stats = await get_player_total_stats(alvo_player) if alvo_player else {}

            h_sala = herois_sala.get(alvo_id, {}) or {}

            hp_atual = int(h_sala.get("current_hp", alvo_player.get("current_hp", 1)) or 1)
            mp_atual = int(h_sala.get("current_mp", alvo_player.get("current_mp", 0)) or 0)

            hp_max = int(alvo_stats.get("max_hp", h_sala.get("max_hp", alvo_player.get("max_hp", hp_atual))) or hp_atual)
            mp_max = int(alvo_stats.get("max_mana", h_sala.get("max_mana", alvo_player.get("max_mana", alvo_player.get("max_mp", mp_atual)))) or mp_atual)

            cura = _calcular_cura_suporte(cura_def or {}, player_stats, {**alvo_stats, "max_hp": hp_max})
            mana_rec = _calcular_mana_suporte(mana_def or {}, {**alvo_stats, "max_mana": mp_max})

            if effects.get("self_heal_percent") and alvo_id == str(user_id):
                cura += int(hp_max * float(effects.get("self_heal_percent", 0) or 0))

            novo_hp_alvo = min(hp_max, hp_atual + cura)
            novo_mp_alvo = min(mp_max, mp_atual + mana_rec)

            total_cura += max(0, novo_hp_alvo - hp_atual)
            total_mana += max(0, novo_mp_alvo - mp_atual)

            nome_alvo = (
                h_sala.get("nome")
                or h_sala.get("character_name")
                or alvo_player.get("character_name")
                or alvo_player.get("nome")
                or "aliado"
            )
            alvos_nome.append(str(nome_alvo))

            if sala_grupo and alvo_id in sala_grupo.get("herois", {}):
                sala_grupo["herois"][alvo_id]["current_hp"] = novo_hp_alvo
                sala_grupo["herois"][alvo_id]["current_mp"] = novo_mp_alvo
                sala_grupo["herois"][alvo_id]["max_hp"] = hp_max
                sala_grupo["herois"][alvo_id]["max_mana"] = mp_max

            if alvo_id == str(user_id):
                player_hp = novo_hp_alvo
                player_mp = novo_mp_alvo
                player["current_hp"] = novo_hp_alvo
                player["current_mp"] = novo_mp_alvo

            try:
                users_collection.update_one(
                    {"_id": ObjectId(alvo_id)},
                    {"$set": {"current_hp": novo_hp_alvo, "current_mp": novo_mp_alvo}}
                )
            except Exception as e:
                print(f"Erro ao salvar cura de suporte no alvo {alvo_id}: {e}")

        partes_log = []
        if total_cura > 0:
            partes_log.append(f"curou {total_cura} HP")
        if total_mana > 0:
            partes_log.append(f"restaurou {total_mana} MP")
        if buff_def:
            partes_log.append(f"aplicou {_nome_buff_suporte(buff_def)}")
        if not partes_log:
            partes_log.append("conjurou suporte")

        if len(alvos_nome) > 2:
            alvo_txt = "o grupo"
        else:
            alvo_txt = ", ".join(alvos_nome) if alvos_nome else "o grupo"

        log_turno.append({
            "autor": "player",
            "texto": f"✨ Usou {nome_skill} em {alvo_txt}: " + " / ".join(partes_log) + ".",
            "dano": 0,
            "tipo": "cura",
            "anim_effect": skill_data_mesclada.get("anim_effect", ""),
            "tipo_skill": "support",
        })

    else:
        resultado = await processar_acao_combate(
            attacker_pdata=player,
            attacker_stats=player_stats,
            target_stats=mob_status_luta,
            skill_id=skill_id if acao == "magia" else None,
            attacker_current_hp=player_hp,
            attacker_current_mp=player_mp,
        )

        dano_heroi = int(resultado.get("total_damage", 0) or 0)
        player_mp = int(resultado.get("attacker_mp_left", player_mp))

        hp_mob_antes = mob_hp
        player_hp, player_mp, mob_hp, logs_golpes = _aplicar_golpes_combate(
            resultado, player_stats, player_hp, player_mp, mob_hp
        )
        log_turno.extend(logs_golpes)
        dano_heroi = hp_mob_antes - mob_hp
        mob_vivo["hp_atual"] = mob_hp

    recompensas = {"gold": 0, "xp": 0, "itens": []}
    ouro_perdido = 0
    xp_perdido = 0
    is_derrota = False
    bestiario = player.get("bestiario", {}) or {}

    # =============================================================
    # 5. CONTRA-ATAQUE OU VITÓRIA
    # =============================================================
    dano_mob = 0

    if mob_hp > 0 and not acao_suporte_grupo:
        from modules.combat.criticals import roll_damage
        defesa_alvo = dict(player_stats)
        # Preserva o peso da defesa usado pelas caçadas, aplicando também esquiva e resistências.
        defesa_alvo['defense'] = int(player_stats.get('defense', 0)) // 2
        atacante_mob = {**mob_status_luta, 'monster_name': mob_status_luta.get('name', 'Monstro')}
        dano_mob, critico_mob, mega_mob = roll_damage(atacante_mob, defesa_alvo)
        player_hp = max(0, player_hp - dano_mob)
        texto_mob = 'Você esquivou do ataque!' if dano_mob == 0 else f"{'Crítico! ' if critico_mob else ''}O monstro atacou: -{dano_mob} HP"
        log_turno.append({'autor': 'mob', 'texto': texto_mob, 'dano': dano_mob})

        if player_hp <= 0:
            is_derrota = True
            xp_perdido = int(mob_status_luta.get("xp_reward", 0)) * 2
            ouro_perdido = int(mob_status_luta.get("gold_drop", 0)) * 2

            player["xp"] = max(0, player.get("xp", 0) - xp_perdido)
            player["gold"] = max(0, player.get("gold", 0) - ouro_perdido)

    elif mob_hp <= 0:
        sistema_cacada.processar_morte(regiao_atual, spawn_id)

        if monster_id_real:
            bestiario[monster_id_real] = bestiario.get(monster_id_real, 0) + 1

        xp_ganho_base = int(mob_status_luta.get("xp_reward", 0))
        ouro_ganho_base = int(mob_status_luta.get("gold_drop", 0))

        from modules.combat.party_engine import dividir_recompensas_grupo
        from modules.game_data.season_pass import adicionar_xp_passe

        em_grupo, xp_final, ouro_final, membros_ids = dividir_recompensas_grupo(
            str(user_id),
            xp_ganho_base,
            ouro_ganho_base,
        )

        # =============================================================
        # 📜 MISSÕES DA GUILDA - REGISTRA ABATE REAL
        # =============================================================
        try:
            from modules.guild_missions.guild_mission_manager import (
                registrar_abate
            )

            if monster_id_real:

                # =====================================================
                # 👥 DESCOBRE O TIPO REAL DO COMBATE
                # =====================================================
                #
                # NÃO usamos "em_grupo" vindo de
                # dividir_recompensas_grupo().
                #
                # Aquela variável pertence ao sistema de recompensa
                # e depende do radar de jogadores online.
                #
                # Para MISSÕES, a fonte da verdade é a sala real
                # criada pelo group_combat_manager.
                # =====================================================

                herois_sala_missao = {}

                if (
                    sala_grupo
                    and isinstance(
                        sala_grupo,
                        dict
                    )
                ):

                    herois_sala_missao = (
                        sala_grupo.get(
                            "herois",
                            {}
                        )
                        or {}
                    )

                    if not isinstance(
                        herois_sala_missao,
                        dict
                    ):
                        herois_sala_missao = {}


                combate_guilda_em_grupo = (
                    bool(sala_grupo)
                    and
                    len(herois_sala_missao) >= 2
                )


                # =====================================================
                # 👥 COMBATE REAL EM GRUPO
                # =====================================================

                if combate_guilda_em_grupo:

                    membros_missao = {
                        str(membro_id)

                        for membro_id
                        in herois_sala_missao.keys()

                        if membro_id
                    }


                    # Segurança adicional:
                    # o jogador que matou o mob sempre entra.
                    membros_missao.add(
                        str(user_id)
                    )


                    print(
                        "📜 [GUILDA CHECK GRUPO] "
                        f"sala={sala_grupo.get('sala_id')} | "
                        f"membros={list(membros_missao)} | "
                        f"mob={monster_id_real} | "
                        f"regiao={regiao_atual}"
                    )


                    # Cada participante recebe o registro.
                    #
                    # O guild_mission_manager só incrementará
                    # aqueles que realmente possuem uma missão
                    # compatível ativa.
                    for membro_id in membros_missao:

                        progresso_guilda = (
                            registrar_abate(
                                user_id=membro_id,

                                monster_id=
                                    monster_id_real,

                                regiao=
                                    regiao_atual,

                                em_grupo=True,

                                quantidade=1,
                            )
                        )


                        if progresso_guilda:

                            print(
                                "📜 [GUILDA GRUPO] "
                                f"Jogador={membro_id} | "
                                f"mob={monster_id_real} | "
                                f"regiao={regiao_atual} | "
                                f"resultado={progresso_guilda}"
                            )


                # =====================================================
                # 👤 COMBATE REAL SOLO
                # =====================================================

                else:

                    progresso_guilda = (
                        registrar_abate(
                            user_id=str(user_id),

                            monster_id=
                                monster_id_real,

                            regiao=
                                regiao_atual,

                            em_grupo=False,

                            quantidade=1,
                        )
                    )


                    if progresso_guilda:

                        print(
                            "📜 [GUILDA SOLO] "
                            f"Jogador={user_id} | "
                            f"mob={monster_id_real} | "
                            f"regiao={regiao_atual} | "
                            f"resultado={progresso_guilda}"
                        )


        except Exception as erro_guilda:

            print(
                "⚠️ [GUILD MISSIONS] "
                f"Erro ao registrar abate: "
                f"{erro_guilda}"
            )


        # =============================================================
        # 🏰 MISSÃO COLETIVA DO CLÃ
        # =============================================================
        try:
            from modules.guild_missions.clan_guild_mission_manager import (
                registrar_abate_cla
            )

            if monster_id_real:

                herois_sala_cla = {}

                if (
                    sala_grupo
                    and isinstance(sala_grupo, dict)
                ):
                    herois_sala_cla = (
                        sala_grupo.get("herois", {})
                        or {}
                    )

                    if not isinstance(
                        herois_sala_cla,
                        dict
                    ):
                        herois_sala_cla = {}


                combate_cla_em_grupo = (
                    bool(sala_grupo)
                    and
                    len(herois_sala_cla) >= 2
                )


                progresso_cla_guilda = registrar_abate_cla(
                    user_id=str(user_id),
                    monster_id=monster_id_real,
                    regiao=regiao_atual,
                    em_grupo=combate_cla_em_grupo,
                    quantidade=1,
                )


                if progresso_cla_guilda:
                    print(
                        "🏰 [GUILDA CLÃ ABATE] "
                        f"Jogador={user_id} | "
                        f"mob={monster_id_real} | "
                        f"regiao={regiao_atual} | "
                        f"grupo={combate_cla_em_grupo} | "
                        f"resultado={progresso_cla_guilda}"
                    )


        except Exception as erro_missao_cla:

            print(
                "⚠️ [GUILD MISSIONS CLÃ] "
                f"Erro ao registrar abate coletivo: "
                f"{erro_missao_cla}"
            )


        # =====================================================
        # ✨ ELIXIR DE EXPERIÊNCIA
        # =====================================================

        xp_recebido_personagem = xp_final
        xp_boost_ativo = False

        try:
            from modules.alchemy.bruxa_pocoes import (
                calcular_xp_com_bonus
            )

            (
                xp_recebido_personagem,
                xp_boost_ativo,
            ) = calcular_xp_com_bonus(
                player,
                xp_final,
            )

        except Exception as e:
            print(
                "⚠️ [XP BOOST] "
                f"Falha ao calcular bônus: {e}"
            )

        player["xp"] = (
            player.get("xp", 0)
            + xp_recebido_personagem
        )

        player["gold"] = (
            player.get("gold", 0) +
            ouro_final
        )

        try:
            adicionar_xp_passe(
                player,
                xp_final,
            )
        except Exception as e:
            print(
                "Erro ao entregar XP "
                f"para o Passe: {e}"
            )

        # Entrega 10% do XP recebido
        # como contribuição ao clã.
        xp_cla_ganho = (
            _adicionar_xp_cla_combate(
                user_id=user_id,
                xp_recebido=xp_final,
            )
        )

        recompensas["xp"] = (
            xp_recebido_personagem
        )
        recompensas["gold"] = ouro_final
        recompensas["xp_cla"] = xp_cla_ganho

        if xp_cla_ganho > 0:
            log_turno.append({
                "autor": "sistema",
                "texto": (
                    f"🛡️ Você contribuiu com "
                    f"+{xp_cla_ganho} XP para o clã!"
                ),
                "dano": 0,
                "tipo": "cla",
            })
            
        if em_grupo:
            nome_mob = mob_status_luta.get("name", "Monstro")
            nome_matador = player.get("character_name", player.get("nome", "Um aliado"))

            avatar_matador = "avatar_padrao_m"
            ac = player.get("avatar_customizado")
            if ac and ac != "padrao":
                avatar_matador = ac.get("path", ac) if isinstance(ac, dict) else ac
            else:
                avatar_matador = player.get("avatar", "avatar_padrao_m")

            nome_puro = avatar_matador.split("/")[-1].replace(".png", "")
            if not nome_puro.startswith("avatar_") and "cunminicon" not in nome_puro:
                nome_puro = f"avatar_{nome_puro}"

            avatar_matador = f"https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/avatares/{nome_puro}.png"

            mensagem_chat = {
                "remetente": "🤝 Sistema de Grupo",
                "texto": f"{nome_matador} abateu um {nome_mob}! A party recebeu +{xp_final} XP e +{ouro_final} 💰.",
                "tipo": "grupo",
                "destinatarios": membros_ids,
                "avatar": avatar_matador,
            }

            if hasattr(sistema_cacada, "socketio") and sistema_cacada.socketio:
                sistema_cacada.socketio.emit("novaMensagemChat", mensagem_chat)

            log_turno.append({"autor": "sistema", "texto": "🤝 Recompensa dividida com o grupo!", "dano": 0})

        loot_table = mob_status_luta.get("loot_table", [])
        for loot in loot_table:
            chance = float(loot.get("drop_chance", 0))
            if random.uniform(0, 100) <= chance:
                item_id = loot.get("item_id")
                if not item_id:
                    continue

                recompensas["itens"].append(item_id)

                if item_id in inventory:
                    if isinstance(inventory[item_id], dict):
                        inventory[item_id]["quantity"] = inventory[item_id].get("quantity", 0) + 1
                    else:
                        inventory[item_id] += 1
                else:
                    inventory[item_id] = {"base_id": item_id, "quantity": 1}

        levels_gained, points_gained, msg = check_and_apply_level_up(
            player
        )

        if levels_gained > 0:

            recompensas["lv_up"] = True
            recompensas["new_level"] = player.get(
                "level",
                1
            )

            # =====================================================
            # ❤️💧 LEVEL UP = VIDA E MANA COMPLETAS
            # =====================================================

            # Recalcula os atributos já usando o NOVO nível.
            player_stats = await get_player_total_stats(
                player
            )

            max_hp_novo = int(
                player_stats.get(
                    "max_hp",
                    100
                ) or 100
            )

            max_mp_novo = int(
                player_stats.get(
                    "max_mana",
                    50
                ) or 50
            )

            # Atualiza as variáveis que serão salvas
            # no final desta função.
            player_hp = max_hp_novo
            player_mp = max_mp_novo

            # Atualiza também o objeto do jogador.
            player["current_hp"] = max_hp_novo
            player["current_mp"] = max_mp_novo

            player["max_hp"] = max_hp_novo
            player["max_mana"] = max_mp_novo

    # =============================================================
    # 6. GASTA DURABILIDADE DOS EQUIPAMENTOS DE COMBATE
    # =============================================================

    # A arma gasta quando o jogador realizou ataque/magia ofensiva e causou dano.
    gastar_arma_combate = (
        acao in ["atacar", "ataque", "normal", "basico", "magia"]
        and not acao_suporte_grupo
        and int(dano_heroi or 0) > 0
    )

    # Equipamentos defensivos gastam quando o monstro causou dano.
    gastar_defesa_combate = int(dano_mob or 0) > 0

    durabilidade_resultado = _gastar_durabilidade_equipamentos_combate(
        player,
        gastar_arma=gastar_arma_combate,
        gastar_defesa=gastar_defesa_combate,
        custo_arma=1,
        custo_defesa=1,
        chance_arma=0.30,
        chance_defesa=0.30
    )

    for msg_dur in durabilidade_resultado.get("mensagens", []):
        log_turno.append({
            "autor": "sistema",
            "texto": msg_dur,
            "dano": 0,
            "tipo": "durabilidade"
        })

    # Atualiza a referência do inventário, porque a função mexeu dentro de player.
    inventory = player.get("inventory", inventory)

    # =============================================================
    # 7. SALVA JOGADOR
    # =============================================================
    if player_hp > 0 and mob_hp > 0:
        hp_antes_regen, mp_antes_regen = player_hp, player_mp
        player_hp, player_mp = _recuperar_recursos_combate(player_stats, player_hp, player_mp, regenerar=True)
        if (player_hp, player_mp) != (hp_antes_regen, mp_antes_regen):
            log_turno.append({"autor": "sistema", "texto": f"Regeneração: +{player_hp - hp_antes_regen} HP / +{player_mp - mp_antes_regen} MP", "dano": 0})
    hp_banco = max(0, int(player_hp))
    mp_banco = int(player_mp)

    if is_derrota and not sala_grupo:
        hp_banco = player_stats.get("max_hp", 100)
        mp_banco = player_stats.get("max_mana", 50)

    luta_encerrada = (mob_hp <= 0) or (is_derrota and not sala_grupo)
    cooldowns_finais = {} if luta_encerrada else player.get("cooldowns", {})

    users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {
            "current_hp": hp_banco,
            "current_mp": mp_banco,
            "inventory": inventory,
            "xp": player.get("xp", 0),
            "gold": player.get("gold", 0),
            "level": player.get("level", 1),
            "stat_points": player.get("stat_points", 0),
            "base_stats": player.get("base_stats", {}),
            "bestiario": bestiario,
            "cooldowns": cooldowns_finais,
            "passe_batalha": player.get("passe_batalha", {}),
        }}
    )

    # =============================================================
    # 7. SINCRONIZA SALA, AVANÇA TURNO E EMITE PARA TODOS OS MEMBROS
    # =============================================================
    if sala_grupo:
        try:
            from modules.combat import group_combat_manager as gcm

            sala_id_real = sala_grupo["sala_id"]
            mob_id = next(iter(sala_grupo.get("mobs", {}).keys()), None)

            if mob_id:
                gcm.atualizar_hp_mob(sala_id_real, mob_id, mob_hp)

            # Atualiza todos os heróis da sala, porque skill de suporte pode curar aliado,
            # não apenas quem clicou.
            for hid, hdata in (sala_grupo.get("herois", {}) or {}).items():
                hp_h = int(hdata.get("current_hp", hdata.get("hp", 0)) or 0)
                mp_h = int(hdata.get("current_mp", hdata.get("mp", 0)) or 0)

                gcm.atualizar_hp_heroi(
                    sala_id_real,
                    str(hid),
                    max(0, hp_h)
                )

                if str(hid) == str(user_id):
                    player_hp = hp_h
                    player_mp = mp_h

            estado_grupo = gcm.verificar_fim_combate(sala_id_real)

            proximo_turno = None
            if estado_grupo == gcm.ESTADO_EM_ANDAMENTO and mob_hp > 0:
                proximo_turno = gcm.avancar_turno(sala_id_real)
            else:
                proximo_turno = gcm.pegar_combatente_atual(sala_id_real)

            sala_retorno = gcm.pacote_estado_sala(sala_id_real)

            turno_atual = sala_retorno.get("turno_atual") if sala_retorno else None

            payload_grupo = {
                "sala_id": sala_id_real,
                "spawn_id": spawn_id,
                "mob_hp": max(0, mob_hp),
                "mob_hp_atual": max(0, mob_hp),
                "player_id": str(user_id),
                "player_hp": max(0, int(player_hp)),
                "player_mp": int(player_mp),
                "sala": sala_retorno,
                "estado": estado_grupo,
                "turno_atual": turno_atual,
                "proximo_turno": proximo_turno,
                "finalizado": estado_grupo in [gcm.ESTADO_VITORIA, gcm.ESTADO_DERROTA],
                "recompensas": recompensas,
                "ouro_perdido": ouro_perdido,
                "xp_perdido": xp_perdido,
                "log": log_turno,
            }

            sio = getattr(sistema_cacada, "socketio", None)
            if sio:
                app_ref = getattr(sistema_cacada, "app", None)
                jogadores_online = {}

                if app_ref:
                    jogadores_online = app_ref.config.get("JOGADORES_ONLINE", {}) or {}

                membros_ids = set(str(x) for x in (sala_retorno or {}).get("membros_ids", []))
                sids_enviados = set()

                for sid, info in list(jogadores_online.items()):
                    char_online = str(info.get("char_id"))

                    if char_online in membros_ids:
                        sio.emit("grupoMobHpUpdate", payload_grupo, to=sid)
                        sio.emit("estadoSalaGrupo", payload_grupo, to=sid)
                        sio.emit("grupoCombateEstado", payload_grupo, to=sid)

                        sids_enviados.add(sid)

                        print(
                            f"[GRUPO COMBATE] Estado enviado para membro {char_online} "
                            f"SID={sid} turno={turno_atual} mob_hp={mob_hp}"
                        )

                # Broadcast SEMPRE.
                # Mesmo que tenha encontrado SID, pode ser SID velho ou aba errada.
                # O frontend filtra por sala_id, então outra sala ignora.
                print(
                    f"[GRUPO COMBATE] Broadcast geral da sala. "
                    f"Diretos={len(sids_enviados)} membros={len(membros_ids)} "
                    f"sala={sala_id_real} turno={turno_atual} proximo={proximo_turno}"
                )

                sio.emit("grupoMobHpUpdate", payload_grupo)
                sio.emit("estadoSalaGrupo", payload_grupo)
                sio.emit("grupoCombateEstado", payload_grupo)
        
        except Exception as e:
            import traceback
            print("Erro sync grupo:", e)
            print(traceback.format_exc())

    # =============================================================
    # 8. RESPOSTA PARA QUEM CLICOU
    # =============================================================
    return {
        "vitoria": mob_hp <= 0,
        "derrota": is_derrota and not sala_grupo,
        "log": log_turno,
        "player_hp": player_hp,
        "mob_hp_atual": mob_hp,
        "player_mp": player_mp,
        "cooldowns": cooldowns_finais,
        "recompensas": recompensas,
        "ouro_perdido": ouro_perdido,
        "xp_perdido": xp_perdido,
        "sala": sala_retorno,
        "grupo": sala_retorno is not None,
        "sala_id": sala_retorno.get("sala_id") if sala_retorno else None,
        "estado": estado_grupo,
        "turno_atual": sala_retorno.get("turno_atual") if sala_retorno else None,
        "finalizado": estado_grupo in ["vitoria", "derrota"] if estado_grupo else False,
        "durabilidade": durabilidade_resultado,
    }

async def _sync_all_stats_inplace(pdata: dict) -> bool: return False
def _migrate_point_pool_to_stat_points_inplace(pdata: dict) -> bool: return False
def _get_default_baseline_from_new_player() -> dict: return {"max_hp": 50, "attack": 5, "defense": 3, "initiative": 5, "luck": 5}
def _ensure_base_stats_block_inplace(pdata: dict) -> bool: return False
def _current_invested_delta_over_baseline(pdata: dict, baseline: dict) -> dict: return {}
async def _apply_class_progression_sync_inplace(pdata: dict) -> bool: return False
def _sync_stat_points_to_level_cap_inplace(pdata: dict) -> bool: return False