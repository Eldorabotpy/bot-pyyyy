# modules/crafting_engine.py

from __future__ import annotations
from datetime import datetime, timezone, timedelta
import uuid
import random
REPEAT_ATTR_CHANCE = 0.10
from typing import Any, Dict, Tuple, List, Union
# Módulos do projeto (Removemos game_data daqui de cima para evitar o ciclo)
from modules import player_manager
# Importamos apenas o essencial aqui
from modules.crafting_registry import get_recipe
# Classes raramente causam ciclo, mas se causar, moveremos também.
try:
    from modules.game_data.classes import get_primary_damage_profile
except ImportError:
    # Fallback caso classes também esteja no ciclo
    def get_primary_damage_profile(_): return {"stat_key": "dmg"}

try:
    from modules.game_data import rarity as rarity_tables
except ImportError:
    rarity_tables = None

# =========================
# Utilitários básicos
# =========================

def _get_game_data():
    """
    Importação 'preguiçosa' (Lazy Import) para quebrar o Ciclo de Importação.
    Só chama o game_data quando a função for executada, não no início do arquivo.
    """
    try:
        from modules import game_data
        return game_data
    except ImportError:
        return None

def _as_dict(obj: Any, default: Dict | None = None) -> Dict:
    if isinstance(obj, dict):
        return obj
    return {} if default is None else default

def _as_tuple_2(val: Any, fallback: Tuple[int, int] = (1, 1)) -> Tuple[int, int]:
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

async def _seconds_with_perks(player_data: dict, base_seconds: int) -> int:
    craft_mult_raw = player_manager.get_perk_value(player_data, "craft_speed_multiplier", None)
    
    if craft_mult_raw is None:
        mult = float(player_manager.get_perk_value(player_data, "refine_speed_multiplier", 1.0))
    else:
        mult = float(craft_mult_raw)  
    mult = max(0.25, min(4.0, mult))
    
    return max(1, int(base_seconds / mult))

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

def _get_item_info(base_id: str) -> dict:
    # Usa o Lazy Import
    gd = _get_game_data()
    try:
        if gd:
            info = gd.get_item_info(base_id)
            if info:
                return dict(info)
            # Tenta acessar ITEMS_DATA direto se get_item_info falhar
            return _as_dict(getattr(gd, "ITEMS_DATA", {})).get(base_id, {}) or {}
    except Exception:
        pass
    return {}

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
# Receitas desbloqueáveis
# =========================

def _recipe_unlock_id(
    recipe: dict,
) -> str | None:
    """
    Retorna o identificador de desbloqueio
    exigido pela receita.

    Receitas normais não possuem unlock_id
    e continuam funcionando normalmente.
    """

    if not isinstance(
        recipe,
        dict,
    ):
        return None


    unlock_id = str(
        recipe.get(
            "unlock_id",
            "",
        )
        or ""
    ).strip()


    return (
        unlock_id
        if unlock_id
        else None
    )


def _recipe_is_unlocked(
    player_data: dict,
    recipe: dict,
) -> bool:
    """
    Confirma se o personagem possui o
    desbloqueio permanente da receita.

    Receita sem unlock_id:
        sempre liberada.

    Receita com unlock_id:
        precisa existir em
        guild_missions.receitas_desbloqueadas.
    """

    unlock_id = (
        _recipe_unlock_id(
            recipe
        )
    )


    # Receita normal do jogo.
    if not unlock_id:
        return True


    guild_missions = (
        player_data.get(
            "guild_missions",
            {},
        )
        or {}
    )


    desbloqueadas = (
        guild_missions.get(
            "receitas_desbloqueadas",
            [],
        )
        or []
    )


    if not isinstance(
        desbloqueadas,
        (
            list,
            tuple,
            set,
        ),
    ):
        return False


    ids = {
        str(item).strip()

        for item
        in desbloqueadas

        if str(item).strip()
    }


    return (
        unlock_id
        in ids
    )
# =========================
# Preview / Start
# =========================

async def preview_craft(
    recipe_id: str,
    player_data: dict
) -> dict | None:

    rec = get_recipe(
        recipe_id
    )

    if not rec:
        return None

    rec = dict(
        rec
    )

    # ========================================================
    # 🔒 DESBLOQUEIO DA RECEITA
    # ========================================================

    unlock_id = _recipe_unlock_id(
        rec
    )

    desbloqueada = _recipe_is_unlocked(
        player_data,
        rec
    )

    # ========================================================
    # 👷 PROFISSÃO
    # Mesma regra usada em start_craft()
    # ========================================================

    req_prof = (
        rec.get("profession")
        or rec.get("profession_req")
        or rec.get("required_tool_type")
    )

    req_lvl = int(
        rec.get(
            "level_req",
            1
        )
    )

    learned = (
        player_data.get(
            "learned_professions",
            {}
        )
        or {}
    )

    my_lvl = 0

    if (
        isinstance(learned, dict)
        and req_prof in learned
    ):

        prof_data = learned.get(
            req_prof
        )

        if isinstance(prof_data, dict):
            my_lvl = int(
                prof_data.get(
                    "level",
                    1
                )
            )

    if my_lvl <= 0:

        legacy = _as_dict(
            player_data.get(
                "profession"
            )
        )

        if (
            legacy.get("type") == req_prof
            or legacy.get("key") == req_prof
        ):

            my_lvl = int(
                legacy.get(
                    "level",
                    1
                )
            )

    ok_prof = (
        my_lvl >= req_lvl
    )

    # ========================================================
    # 📦 MATERIAIS
    # Compatível com todos os formatos de receita.
    # ========================================================

    inputs = _as_dict(
        rec.get("inputs")
        or rec.get("materials")
        or rec.get("ingredients")
    )

    ok_materials = _has_materials(
        player_data,
        inputs
    )

    # ========================================================
    # 🔨 FERRAMENTA
    # Apenas verifica. NÃO consome durabilidade.
    # ========================================================

    try:
        from modules import profession_engine

        tool_check = (
            profession_engine
            .check_profession_tool_for_recipe(
                player_data=player_data,
                recipe=rec,
                action_name="forjar"
            )
        )

    except Exception as e:

        tool_check = {
            "ok": False,
            "error": (
                "Erro ao verificar ferramenta: "
                f"{str(e)}"
            )
        }

    ok_tool = bool(
        tool_check.get(
            "ok"
        )
    )

    # ========================================================
    # ⏱️ TEMPO REAL
    # Profissão + Tier + Refino + Velocidade da ferramenta.
    # ========================================================

    base_time = int(
        rec.get(
            "time_seconds",
            60
        )
    )

    try:

        tempo_calc = (
            profession_engine
            .calculate_profession_work_duration(
                player_data=player_data,
                base_seconds=base_time,
                profession_key=req_prof,
                apply_perks=True
            )
        )

        duration = int(
            tempo_calc.get(
                "duration_seconds",
                base_time
            )
        )

    except Exception:

        duration = await _seconds_with_perks(
            player_data,
            base_time
        )

        tempo_calc = {
            "duration_seconds":
                duration,
            "base_seconds":
                base_time,
        }

    # ========================================================
    # 🍀 QUALIDADE PREVISTA
    # Não sorteia a raridade.
    # Apenas mostra os bônus atuais.
    # ========================================================

    try:

        quality_calc = (
            profession_engine
            .calculate_crafting_quality_bonus(
                player_data=player_data,
                profession_key=req_prof
            )
        )

    except Exception:

        quality_calc = {
            "quality_bonus_points": 0.0
        }

    # ========================================================
    # 📤 RESULTADO
    # ========================================================

    return {
        "can_craft": bool(
            desbloqueada
            and ok_prof
            and ok_materials
            and ok_tool
        ),

        "requer_desbloqueio":
            bool(
                unlock_id
            ),

        "desbloqueada":
            bool(
                desbloqueada
            ),

        "unlock_id":
            unlock_id,

        "profession":
            req_prof,

        "profession_level":
            my_lvl,

        "required_profession_level":
            req_lvl,

        "profession_ok":
            ok_prof,

        "materials_ok":
            ok_materials,

        "tool_ok":
            ok_tool,

        "tool":
            tool_check,

        "duration_seconds":
            duration,

        "work_speed":
            tempo_calc,

        "craft_quality":
            quality_calc,

        "inputs":
            dict(
                inputs
            ),

        "result_base_id":
            rec.get(
                "result_base_id"
            ),

        "display_name":
            rec.get(
                "display_name",
                recipe_id
            ),

        "emoji":
            rec.get(
                "emoji",
                ""
            ),
    }

async def start_craft(user_id: str, recipe_id: str):
    pdata = await player_manager.get_player_data(
        user_id
    )

    rec = get_recipe(
        recipe_id
    )


    if not pdata or not rec:
        return (
            "Receita de forja inválida."
        )


    rec = dict(
        rec
    )

    # ========================================================
    # 🔒 IMPEDE DUAS FORJAS AO MESMO TEMPO
    # ========================================================

    current_state = _as_dict(
        pdata.get(
            "player_state"
        )
    )

    if current_state.get("action") == "crafting":

        finish_raw = current_state.get(
            "finish_time"
        )

        if finish_raw:

            try:

                finish_dt = datetime.fromisoformat(
                    str(finish_raw).replace(
                        "Z",
                        "+00:00"
                    )
                )

                if finish_dt.tzinfo is None:
                    finish_dt = finish_dt.replace(
                        tzinfo=timezone.utc
                    )

                agora = datetime.now(
                    timezone.utc
                )

                if agora < finish_dt:

                    restante = max(
                        1,
                        int(
                            (
                                finish_dt
                                - agora
                            ).total_seconds()
                            + 0.999
                        )
                    )

                    return (
                        "Você já possui uma forja em andamento. "
                        f"Aguarde {restante}s."
                    )

                return (
                    "Sua forja anterior já terminou. "
                    "Conclua a fabricação antes de iniciar outra."
                )

            except Exception:

                return (
                    "Já existe uma forja pendente. "
                    "Conclua-a antes de iniciar outra."
                )

        return (
            "Já existe uma forja pendente. "
            "Conclua-a antes de iniciar outra."
        )


    # ========================================================
    # 🔒 RECEITA ESPECIAL DESBLOQUEÁVEL
    # ========================================================

    if not _recipe_is_unlocked(
        pdata,
        rec,
    ):
        return (
            "Esta receita especial ainda "
            "não foi desbloqueada."
        )


    # 1. Validação de Profissão Inteligente
    req_prof = (
        rec.get("profession")
        or rec.get("profession_req")
        or rec.get("required_tool_type")
    )

    req_lvl = int(
        rec.get(
            "level_req",
            1
        )
    )
    
    learned = pdata.get("learned_professions", {})
    my_lvl = 0
    if req_prof in learned:
        my_lvl = int(learned[req_prof].get("level", 1))
    else:
        legacy = _as_dict(pdata.get("profession"))
        if legacy.get("type") == req_prof or legacy.get("key") == req_prof:
            my_lvl = int(legacy.get("level", 1))
            
    if my_lvl < req_lvl: 
        return f"Requer {str(req_prof).capitalize()} Nível {req_lvl}."
    
    # 2. Validação de Materiais
    inputs = _as_dict(
        rec.get("inputs")
        or rec.get("materials")
        or rec.get("ingredients")
    )
    if not _has_materials(pdata, inputs):
        return "Materiais insuficientes."

    # 2.5. Validação e gasto de durabilidade da ferramenta
    # Import lazy para evitar ciclo de importação.
    try:
        from modules import profession_engine

        tool_result = profession_engine.validate_and_consume_tool_for_recipe(
            player_data=pdata,
            recipe=rec,
            action_name="forjar"
        )

        if not tool_result.get("ok"):
            return tool_result.get("error", "Ferramenta inválida para forjar.")

    except Exception as e:
        return f"Erro ao validar ferramenta: {str(e)}"
    
    # 3. Tempo com bônus de profissão + ferramenta
    from modules import profession_engine

    base_time = int(rec.get("time_seconds", 60))

    tempo_calc = profession_engine.calculate_profession_work_duration(
        player_data=pdata,
        base_seconds=base_time,
        profession_key=req_prof,
        apply_perks=True
    )

    duration = int(
        tempo_calc.get(
            "duration_seconds",
            base_time
        )
    )

    # Congela os bônus no momento em que a fabricação começa.
    # Assim não adianta trocar de ferramenta durante a produção.
    quality_calc = (
        profession_engine
        .calculate_crafting_quality_bonus(
            player_data=pdata,
            profession_key=req_prof
        )
    )

    _consume_materials(
        pdata,
        inputs
    )
    
    finish = datetime.now(timezone.utc) + timedelta(seconds=duration)
    pdata["player_state"] = {
        "action": "crafting",
        "finish_time": finish.isoformat(),
        "details": {
            "recipe_id": recipe_id,
            "prof_used": req_prof,
            "work_speed": tempo_calc,
            "craft_quality": quality_calc,
            "tool_uid": tool_result.get("tool_uid"),
            "tool_type": tool_result.get("tool_type"),
            "tool_broke": tool_result.get("tool_broke", False)
        }
    }
    
    await player_manager.save_player_data(user_id, pdata)
    return {
        "duration_seconds": duration,
        "finish_time": finish.isoformat(),
        "work_speed": tempo_calc,
        "craft_quality": quality_calc,
        "tool_broke": tool_result.get("tool_broke", False),
        "tool_message": tool_result.get("message", "")
    }

# =========================
# Mapeamento/seleção de atributos
# =========================

def _attr_to_enchant_key(attr_name: str) -> str:
    """
    Padroniza o nome do atributo para as chaves usadas no attributes.py e rarity.py.
    Força o padrão em PORTUGUÊS para garantir que os emojis apareçam no menu.
    """
    a = str(attr_name or "").lower().strip()
    if not a: return "vida"
    
    # --- MAPEAMENTO DE TRADUÇÃO/PADRONIZAÇÃO ---
    
    # VIDA / HP
    if a in {"vida", "hp", "saude", "saúde", "health", "max_hp", "vitalidade"}:
        return "vida"
        
    # ATAQUE / DANO (Genérico, geralmente vira Força ou Ataque)
    if a in {"ataque", "attack", "dano", "damage", "dmg", "poder"}:
        return "ataque"
        
    # FORÇA (Específico)
    if a in {"forca", "força", "strength", "str"}:
        return "forca"

    # DEFESA
    if a in {"defesa", "defense", "def", "armor", "blindagem", "resistencia"}:
        return "defesa"
        
    # INICIATIVA (Velocidade de Turno)
    if a in {"iniciativa", "initiative", "velocidade", "speed", "ini"}:
        return "iniciativa"
        
    # AGILIDADE (Stat Base)
    if a in {"agilidade", "agility", "agi"}:
        return "agilidade"
    
    # SORTE
    if a in {"sorte", "luck", "lucky", "luk"}:
        return "sorte"
        
    # INTELIGÊNCIA
    if a in {"inteligencia", "intelligence", "int"}:
        return "inteligencia"
        
    # PRECISÃO
    if a in {"precisao", "mira", "precision", "accuracy"}:
        return "precisao"
        
    # LETALIDADE
    if a in {"letalidade", "lethality", "morte"}:
        return "letalidade"
        
    # FÚRIA
    if a in {"furia", "rage", "fury"}:
        return "furia"
        
    # CRÍTICO
    if a in {"crit", "critico", "critical", "crit_chance", "crit_chance_flat"}:
        return "crit_chance_flat"

    # Retorna a própria chave se não cair em nenhum filtro (ex: bushido, carisma, foco)
    return a

def _class_primary_attr(player_class: str | None) -> str:
    profile = get_primary_damage_profile((player_class or "").lower()) or {}
    key = profile.get("stat_key") or "dmg"
    return key

def _rarity_target_attr_count(rarity: str) -> int:
    default_map = {"comum": 1, "bom": 2, "raro": 3, "epico": 4, "lendario": 5}
    table = getattr(rarity_tables, "ATTR_COUNT_BY_RARITY", None)
    
    r_key = (rarity or "").lower()
    
    if isinstance(table, dict) and table:
        val = table.get(r_key)
        if val is not None:
            return int(val)
            
    return int(default_map.get(r_key, 1))

def _secondary_attr_pool(recipe: dict, player_class: str | None) -> List[str]:
    """
    Tenta carregar AFFIX_POOLS do game_data. 
    Se falhar (por ciclo de importação ou erro), usa o BACKUP_POOL.
    """
    gd = _get_game_data() # Lazy Import
    AFFIX_POOLS = {}
    
    if gd:
        AFFIX_POOLS = getattr(gd, "AFFIX_POOLS", {}) or {}
    
    # Pool de segurança se o game_data falhar
    BACKUP_POOL = ["hp", "defense", "initiative", "luck"] 
    
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

    if len(combined) < 4:
        combined.extend(BACKUP_POOL)

    out: List[str] = []
    seen = {"dmg", "damage", "ataque"}
    
    for a in combined:
        key_norm = _attr_to_enchant_key(a)
        if not key_norm or key_norm in seen:
            continue
        if key_norm not in out:
            out.append(key_norm)
            
    if not out:
        out = ["hp", "defense", "initiative", "luck"]

    return out

def _tool_attribute_pool(tool_type: str | None) -> List[str]:
    """
    Pool própria para ferramentas de profissão.
    Esses atributos NÃO são atributos de combate.
    """
    return [
        "velocidade_trabalho",
        "sorte_oficio",
        "maestria",
        "resistencia_ferramenta",
    ]


def _pick_attribute_keys_for_tool(
    rarity: str,
    tool_type: str | None
) -> List[str]:
    """
    Ferramentas usam a mesma quantidade de atributos por raridade
    dos outros equipamentos.

    Comum      = 1
    Bom        = 2
    Raro       = 3
    Épico      = 4
    Lendário   = 5

    Velocidade de Trabalho é o atributo-base da ferramenta.
    """
    target = max(
        1,
        _rarity_target_attr_count(rarity)
    )

    pool = _tool_attribute_pool(
        tool_type
    )

    out: List[str] = [
        "velocidade_trabalho"
    ]

    if target <= 1:
        return out

    while len(out) < target:

        deve_repetir = (
            random.random()
            < REPEAT_ATTR_CHANCE
        )

        if deve_repetir and out:
            out.append(
                random.choice(out)
            )
            continue

        usados = set(out)

        disponiveis = [
            attr
            for attr in pool
            if attr not in usados
        ]

        if disponiveis:
            escolhido = random.choice(
                disponiveis
            )
        else:
            escolhido = random.choice(
                out
            )

        out.append(
            escolhido
        )

    return out[:target]

def _pick_attribute_keys_for_item(rarity: str, primary_key: str, recipe: dict, player_class: str | None) -> List[str]:
    """
    Escolhe os atributos do item conforme a raridade.

    Regra:
    - O primeiro atributo continua sendo o principal atual do sistema.
    - Cada atributo extra tem REPEAT_ATTR_CHANCE de repetir algum atributo já sorteado.
    - Se não repetir, tenta pegar um atributo novo.
    - Se acabar a lista de atributos novos, repete algum já existente.
    """
    target = max(1, _rarity_target_attr_count(rarity))
    primary_norm = _attr_to_enchant_key(primary_key)

    out: List[str] = [primary_norm]

    if target <= 1:
        return out

    candidates = _secondary_attr_pool(recipe, player_class)
    candidates = [_attr_to_enchant_key(c) for c in candidates if c]

    # Fallback seguro caso a pool venha pequena ou vazia
    fallback_stats = ["vida", "defesa", "iniciativa", "sorte", "agilidade"]
    for fb in fallback_stats:
        fb_norm = _attr_to_enchant_key(fb)
        if fb_norm not in candidates:
            candidates.append(fb_norm)

    while len(out) < target:
        deve_repetir = random.random() < REPEAT_ATTR_CHANCE

        if deve_repetir and out:
            escolhido = random.choice(out)
            out.append(escolhido)
            continue

        usados = set(out)
        disponiveis = [c for c in candidates if c not in usados]

        if disponiveis:
            escolhido = random.choice(disponiveis)
        else:
            escolhido = random.choice(out)

        out.append(escolhido)

    return out[:target]

# =========================
# Raridade / meta de dano
# =========================

def _quality_adjusted_rarity_chances(
    recipe: dict,
    quality_bonus_points: float = 0.0
) -> dict:
    """
    Aplica o bônus de qualidade nas chances da receita.

    Exemplo:
        quality_bonus_points = 7.2
        retira 7.2 pontos percentuais de Comum.

    Distribuição:
        55% -> Bom
        30% -> Raro
        10% -> Épico
         5% -> Lendário

    Máximo absoluto: +15 pontos percentuais.
    """

    base_chances = dict(
        recipe.get(
            "rarity_chances",
            {"comum": 1.0}
        )
    )

    rarities = [
        "comum",
        "bom",
        "raro",
        "epico",
        "lendario",
    ]

    cleaned = {}

    for rarity in rarities:
        try:
            cleaned[rarity] = max(
                0.0,
                float(
                    base_chances.get(
                        rarity,
                        0.0
                    )
                    or 0.0
                )
            )
        except Exception:
            cleaned[rarity] = 0.0

    total = sum(cleaned.values())

    if total <= 0:
        cleaned = {
            "comum": 1.0,
            "bom": 0.0,
            "raro": 0.0,
            "epico": 0.0,
            "lendario": 0.0,
        }
        total = 1.0

    norm = {
        rarity: value / total
        for rarity, value
        in cleaned.items()
    }

    try:
        bonus_fraction = float(
            quality_bonus_points or 0.0
        ) / 100.0
    except Exception:
        bonus_fraction = 0.0

    bonus_fraction = min(
        0.15,
        max(
            0.0,
            bonus_fraction
        )
    )

    shifted = min(
        norm.get(
            "comum",
            0.0
        ),
        bonus_fraction
    )

    norm["comum"] = max(
        0.0,
        norm.get(
            "comum",
            0.0
        ) - shifted
    )

    redistribution = {
        "bom": 0.55,
        "raro": 0.30,
        "epico": 0.10,
        "lendario": 0.05,
    }

    for rarity, weight in redistribution.items():
        norm[rarity] = (
            norm.get(
                rarity,
                0.0
            )
            + shifted * weight
        )

    final_total = sum(
        norm.values()
    ) or 1.0

    return {
        rarity: value / final_total
        for rarity, value
        in norm.items()
    }


def _roll_rarity(
    player_data: dict,
    recipe: dict,
    quality_bonus_points: float = 0.0
) -> str:

    norm = _quality_adjusted_rarity_chances(
        recipe=recipe,
        quality_bonus_points=quality_bonus_points
    )

    order = [
        "lendario",
        "epico",
        "raro",
        "bom",
        "comum",
    ]

    roll = random.random()
    acc = 0.0

    for rarity in order:

        acc += norm.get(
            rarity,
            0.0
        )

        if roll < acc:
            return rarity

    return "comum"

# =========================
# Aplicação de atributos (= upgrade_level)
# =========================

def _next_enchantment_key(ench: dict, stat_key: str) -> str:
    """
    Cria uma chave única para permitir atributo repetido.

    Exemplo:
    primeira força  -> forca
    segunda força   -> forca_2
    terceira força  -> forca_3
    """
    base = _attr_to_enchant_key(stat_key)

    if base not in ench:
        return base

    idx = 2
    while f"{base}_{idx}" in ench:
        idx += 1

    return f"{base}_{idx}"


def _apply_attr_with_upgrade(item: dict, attr_key: str, upgrade_level: int, source: str) -> None:
    """
    Aplica um atributo no item sem juntar atributos repetidos.

    Exemplo:
    se cair força duas vezes, salva assim:

    enchantments["forca"] = {"stat": "forca", "value": 1}
    enchantments["forca_2"] = {"stat": "forca", "value": 1}

    Assim o jogador vê:
    💪 +1, 💪 +1

    E ao melhorar para +2:
    💪 +2, 💪 +2
    """
    ench = item.setdefault("enchantments", {})

    stat_key = _attr_to_enchant_key(attr_key)
    entry_key = _next_enchantment_key(ench, stat_key)

    ench[entry_key] = {
        "stat": stat_key,
        "value": int(upgrade_level),
        "source": source
    }


def _real_enchantment_stat(entry_key: str, entry_data: dict) -> str:
    """
    Descobre o atributo real de uma entrada.

    forca    -> forca
    forca_2  -> forca
    sorte_3  -> sorte
    """
    if isinstance(entry_data, dict) and entry_data.get("stat"):
        return _attr_to_enchant_key(entry_data.get("stat"))

    key = str(entry_key or "")

    if "_" in key:
        base, suffix = key.rsplit("_", 1)
        if suffix.isdigit():
            return _attr_to_enchant_key(base)

    return _attr_to_enchant_key(key)


def sync_enchantments_to_upgrade_level(item: dict) -> dict:
    """
    Atualiza todos os atributos visíveis para o nível atual do item.

    Exemplo:
    upgrade_level = 2

    forca   vira +2
    forca_2 vira +2
    sorte   vira +2

    Não transforma em forca +4.
    Mantém separado.
    """
    try:
        upg = int(item.get("upgrade_level", 1))
    except Exception:
        upg = 1

    ench = item.get("enchantments")
    if not isinstance(ench, dict):
        return item

    for entry_key, entry_data in list(ench.items()):
        if not isinstance(entry_data, dict):
            continue

        entry_data["stat"] = _real_enchantment_stat(entry_key, entry_data)
        entry_data["value"] = upg

    return item

# =========================
# Criação do item
# =========================

def _create_dynamic_unique_item(
    player_data: dict,
    recipe: dict,
    quality_bonus_points: float = 0.0
) -> dict:

    final_rarity = _roll_rarity(
        player_data=player_data,
        recipe=recipe,
        quality_bonus_points=quality_bonus_points
    )
    base_id = recipe["result_base_id"]

    from modules.game_data.rune_rules import SOCKETS_BY_RARITY as SOCKETS_MAP
    num_sockets = SOCKETS_MAP.get(final_rarity, 0)
    initial_sockets = [None] * num_sockets

    new_item = {
        "uuid": str(uuid.uuid4()),
        "base_id": base_id,
        "rarity": final_rarity,
        "upgrade_level": 1,
        "durability": [20, 20],
        "sockets": initial_sockets, 
        "enchantments": {},
    }

    info = _get_item_info(base_id)
    slot = (info.get("slot") or "").lower()

    item_type = str(
        info.get("type")
        or ""
    ).strip().lower()

    is_tool = (
        item_type in {
            "tool",
            "ferramenta"
        }
        or slot == "tool"
    )

    if is_tool:

        dur_atual, dur_max = _as_tuple_2(
            info.get("durability"),
            (20, 20)
        )

        new_item["durability"] = [
            dur_atual,
            dur_max
        ]

        # Ferramentas não recebem sockets de runa.
        new_item["sockets"] = []

        new_item["type"] = "tool"

        new_item["tool_type"] = str(
            info.get("tool_type")
            or recipe.get("profession")
            or recipe.get("profession_req")
            or recipe.get("required_tool_type")
            or ""
        ).strip().lower()

        new_item["tier"] = max(
            1,
            int(
                info.get(
                    "tier",
                    1
                )
                or 1
            )
        )

    if isinstance(recipe.get("class_req"), (list, tuple)) and recipe["class_req"]:
        target_class = str(recipe["class_req"][0]).strip().lower()
    else:
        target_class = _get_player_class_key(player_data)

    # --- CORREÇÃO CRÍTICA: Mapeia o atributo primário visível para o atributo ESPECÍFICO da classe ---
    CLASS_VISIBLE_PRIMARY_ATTR = {
        "guerreiro": "forca", 
        "berserker": "furia", 
        "samurai": "bushido",
        "cacador": "precisao", 
        "assassino": "letalidade", 
        "monge": "foco",
        "mago": "inteligencia", 
        "bardo": "carisma", 
        "curandeiro": "fe" # ou "inteligencia" dependendo do seu sistema
    }

    if is_tool:

        primary_attr = "velocidade_trabalho"
        mirror_dmg = False

    elif _is_weapon_slot(slot):
        primary_attr = CLASS_VISIBLE_PRIMARY_ATTR.get((target_class or ""), "forca")
        mirror_dmg = True # Permite que o atributo dmg seja espelhado

        dmg_info = _as_dict(recipe.get("damage_info"))
        dmin, dmax = _as_tuple_2(dmg_info, (10, 20))
        class_profile = get_primary_damage_profile(target_class or "")
        scales_with = str(dmg_info.get("scales_with", class_profile.get("scales_with", "for")))
        
        new_item["damage"] = {
            "type": str(dmg_info.get("type", class_profile.get("type", "fisico"))),
            "min": int(dmg_info.get("min_damage", dmin)),
            "max": int(dmg_info.get("max_damage", dmax)),
            "scales_with": scales_with,
        }
    else:
        # Lógica para equipamentos (HP, Sorte, Agilidade)
        slot_stats = _as_dict(getattr(rarity_tables, "BASE_STATS_BY_RARITY", {})).get(slot)
        
        if slot_stats:
            # Pega a chave definida na tabela de raridade (ex: "__class_primary__" para anel/brinco)
            raw_primary = next(iter(slot_stats.keys()), "hp")
            
            # === CORREÇÃO: Resolve a tag especial para o atributo da classe ===
            if raw_primary == "__class_primary__":
                primary_attr = CLASS_VISIBLE_PRIMARY_ATTR.get((target_class or ""), "hp")
            else:
                primary_attr = raw_primary
        else:
            primary_attr = "hp"
            
        mirror_dmg = False

    if is_tool:

        attr_keys = _pick_attribute_keys_for_tool(
            final_rarity,
            new_item.get("tool_type")
        )

    else:

        attr_keys = _pick_attribute_keys_for_item(
            final_rarity,
            primary_attr,
            recipe,
            target_class
        )

    # REMOÇÃO DA LÓGICA DE FORÇAR DMG: 
    # O atributo da classe (Letalidade/Furia) agora é o primeiro encantamento (idx=0).

    upg = int(new_item["upgrade_level"])
    for idx, ak in enumerate(attr_keys):
        source = "primary" if idx == 0 else "affix"
        _apply_attr_with_upgrade(new_item, _attr_to_enchant_key(ak), upg, source)

    # BLOCO MIRROR_DMG: Garante que a chave 'dmg' existe (se for arma) e tem o mesmo valor do upgrade.
    if mirror_dmg:
        has_dmg = False
        for k, v in new_item["enchantments"].items():
            if k == "dmg":
                has_dmg = True
                break
            if isinstance(v, dict) and v.get("stat") == "dmg":
                has_dmg = True
                break

        if not has_dmg:
            # O atributo DMG fica em segundo plano para o cálculo de arma.
            # Ele não deve aparecer como atributo visual principal.
            new_item["enchantments"]["dmg"] = {
                "stat": "dmg",
                "value": upg,
                "source": "primary_mirror"
            }

    dn = info.get("display_name") or info.get("nome_exibicao") or info.get("name") or base_id.replace("_", " ").title()
    if dn:
        new_item["display_name"] = str(dn)
    
    emoji_found = info.get("emoji") or recipe.get("emoji")
    if emoji_found:
        new_item["emoji"] = emoji_found

    class_req = recipe.get("class_req")
    if isinstance(class_req, (list, tuple)):
        new_item["class_req"] = [str(x).strip().lower() for x in class_req if str(x).strip()]
    elif isinstance(class_req, str) and class_req.strip():
        new_item["class_req"] = [class_req.strip().lower()]

    return new_item

# =========================
# Finish / XP
# =========================

async def finish_craft(user_id: str):

    pdata = await player_manager.get_player_data(
        user_id
    )

    pstate = (
        _as_dict(
            pdata.get("player_state")
        )
        if pdata
        else {}
    )

    if (
        not pdata
        or pstate.get("action") != "crafting"
    ):
        return "Nenhuma forja em andamento."

    # ========================================================
    # ⏳ SEGURANÇA — NÃO FINALIZA ANTES DO TEMPO
    # ========================================================

    finish_raw = pstate.get(
        "finish_time"
    )

    if not finish_raw:
        return (
            "Tempo de conclusão da forja "
            "não foi encontrado."
        )

    try:

        finish_dt = datetime.fromisoformat(
            str(finish_raw).replace(
                "Z",
                "+00:00"
            )
        )

        if finish_dt.tzinfo is None:
            finish_dt = finish_dt.replace(
                tzinfo=timezone.utc
            )

    except Exception:

        return (
            "Tempo de conclusão da forja "
            "é inválido."
        )

    agora = datetime.now(
        timezone.utc
    )

    if agora < finish_dt:

        restante = max(
            1,
            int(
                (
                    finish_dt
                    - agora
                ).total_seconds()
                + 0.999
            )
        )

        return (
            "Forja ainda em andamento. "
            f"Aguarde {restante}s."
        )

    details = _as_dict(
        pstate.get(
            "details"
        )
    )

    rid = details.get(
        "recipe_id"
    )

    prof_used = details.get(
        "prof_used"
    )

    quality_snapshot = _as_dict(
        details.get(
            "craft_quality"
        )
    )

    try:
        quality_bonus_points = float(
            quality_snapshot.get(
                "quality_bonus_points",
                0.0
            )
            or 0.0
        )
    except Exception:
        quality_bonus_points = 0.0

    rec = get_recipe(rid)
    
    if not rec:
        pdata["player_state"] = {"action": "idle"}
        await player_manager.save_player_data(user_id, pdata)
        return "Receita não encontrada ao concluir."

    rec = dict(rec)

    novo_item_criado = _create_dynamic_unique_item(
        player_data=pdata,
        recipe=rec,
        quality_bonus_points=quality_bonus_points
    )
    player_manager.add_unique_item(pdata, novo_item_criado)

    # 4. Distribuição de XP Inteligente
    xp_gain = int(rec.get("xp_gain", 10))
    if prof_used:
        learned = pdata.get("learned_professions", {})
        if prof_used in learned:
            prof_data = learned[prof_used]
            prof_data["xp"] = int(prof_data.get("xp", 0)) + xp_gain
            
            # Level up manual
            while True:
                lvl = int(prof_data.get("level", 1))
                need = 40 + (25 * (lvl - 1)) + (8 * ((lvl - 1) ** 2))
                if prof_data["xp"] >= need:
                    prof_data["xp"] -= need
                    prof_data["level"] = lvl + 1
                else:
                    break
            learned[prof_used] = prof_data
            pdata["learned_professions"] = learned

    pdata["player_state"] = {"action": "idle"}
    await player_manager.save_player_data(user_id, pdata)
    return {"status": "success", "item_criado": novo_item_criado, "xp_ganho": xp_gain}
