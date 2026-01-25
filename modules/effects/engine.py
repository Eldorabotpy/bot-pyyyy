# modules/effects/engine.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from modules.effects.models import (
    CombatContext,
    EffectInstance,
    EVENT_ON_APPLY,
    EVENT_ON_REFRESH,
    EVENT_ON_EXPIRE,
    EVENT_ON_TURN_START,
    EVENT_ON_TURN_END,
    EVENT_ON_BEFORE_DAMAGE,
    EVENT_ON_AFTER_DAMAGE,
    EVENT_ON_HEAL,
)
from modules.effects.registry import (
    get_effect_template,
    # modifier keys
    MOD_DAMAGE_DEALT_MULT,
    MOD_DAMAGE_TAKEN_MULT,
    MOD_HEAL_RECEIVED_MULT,
    MOD_CANNOT_ACT,
    MOD_SHIELD_FLAT,
    # tick keys
    TICK_DAMAGE,
    TICK_HEAL,
)

# -----------------------------------------------------------------------------
# Convenção simples:
# - "entidade" é um dict (player_data ou monster_stats do battle_cache)
# - efeitos ativos ficam em entity["_effects"] como lista de dict (serializado)
# - o engine converte para EffectInstance quando processa
# -----------------------------------------------------------------------------

EFFECTS_KEY = "_effects"  # não conflita com seus campos atuais


def _ensure_effects(entity: Dict[str, Any]) -> List[EffectInstance]:
    raw = entity.get(EFFECTS_KEY)
    if not raw:
        entity[EFFECTS_KEY] = []
        return []

    out: List[EffectInstance] = []
    changed = False
    for it in raw:
        if isinstance(it, EffectInstance):
            out.append(it)
        elif isinstance(it, dict):
            out.append(EffectInstance.from_dict(it))
            changed = True
        else:
            changed = True

    if changed:
        entity[EFFECTS_KEY] = [e.to_dict() for e in out]
    return out


def _save_effects(entity: Dict[str, Any], effects: List[EffectInstance]) -> None:
    entity[EFFECTS_KEY] = [e.to_dict() for e in effects]


def _find_effects_by_id(effects: List[EffectInstance], effect_id: str) -> List[EffectInstance]:
    return [e for e in effects if e.effect_id == effect_id]


def _remove_by_uid(effects: List[EffectInstance], uid: str) -> Tuple[List[EffectInstance], Optional[EffectInstance]]:
    removed = None
    kept = []
    for e in effects:
        if e.uid == uid and removed is None:
            removed = e
        else:
            kept.append(e)
    return kept, removed


def _remove_exclusive_group(entity: Dict[str, Any], effects: List[EffectInstance], group: str) -> List[EffectInstance]:
    kept = []
    for e in effects:
        tpl = get_effect_template(e.effect_id)
        if tpl and tpl.exclusive_group == group:
            # remove (expire)
            continue
        kept.append(e)
    return kept


# -----------------------------------------------------------------------------
# API pública do EffectEngine
# -----------------------------------------------------------------------------

def apply_effect(
    target: Dict[str, Any],
    effect_id: str,
    *,
    source_id: Optional[str] = None,
    source_type: Optional[str] = None,
    duration_turns: int = 0,
    permanent: bool = False,
    stacks: int = 1,
    potency: float = 1.0,
    dispellable: Optional[bool] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str]:
    """
    Aplica um efeito em target.
    Retorna (ok, msg_curta).
    """
    tpl = get_effect_template(effect_id)
    if not tpl:
        return False, f"Efeito desconhecido: {effect_id}"

    effects = _ensure_effects(target)

    # exclusive group (ex.: posture/aura)
    if tpl.exclusive_group:
        effects = _remove_exclusive_group(target, effects, tpl.exclusive_group)

    # procura existentes do mesmo effect_id
    existing = _find_effects_by_id(effects, effect_id)

    # define dispellable final
    final_dispellable = tpl.dispellable if dispellable is None else bool(dispellable)

    # se já existe e stack_mode não é separate_instances (ainda não usamos no MVP)
    if existing:
        # por simplicidade, usamos a primeira instância como "principal"
        e = existing[0]

        # stack rules
        mode = tpl.stack_mode or "refresh_duration"
        max_stacks = max(1, int(tpl.max_stacks or 1))

        if mode == "none":
            # só refresca duração se fizer sentido
            if not e.permanent:
                e.remaining = max(e.remaining, int(duration_turns))
            e.potency = max(float(e.potency), float(potency))
            e.dispellable = final_dispellable
            if meta:
                e.meta.update(meta)

        elif mode == "add_duration":
            if not e.permanent:
                e.remaining += int(duration_turns)
            # stacks sobem até max
            if e.stacks < max_stacks:
                e.stacks = min(max_stacks, e.stacks + int(stacks))
            e.potency = max(float(e.potency), float(potency))
            e.dispellable = final_dispellable
            if meta:
                e.meta.update(meta)

        elif mode == "increase_potency":
            # stacks sobem até max
            if e.stacks < max_stacks:
                e.stacks = min(max_stacks, e.stacks + int(stacks))
            # potency funciona como multiplicador do tick/mod (você calibra por efeito)
            e.potency = max(float(e.potency), float(potency))
            if not e.permanent:
                e.remaining = max(e.remaining, int(duration_turns))
            e.dispellable = final_dispellable
            if meta:
                e.meta.update(meta)

        else:  # refresh_duration (default)
            if e.stacks < max_stacks:
                e.stacks = min(max_stacks, e.stacks + int(stacks))
            if not e.permanent:
                e.remaining = max(e.remaining, int(duration_turns))
            e.potency = max(float(e.potency), float(potency))
            e.dispellable = final_dispellable
            if meta:
                e.meta.update(meta)

        _save_effects(target, effects)
        return True, f"{tpl.name} atualizado"

    # cria nova instância
    inst = EffectInstance(
        effect_id=tpl.effect_id,
        kind=tpl.kind,
        source_id=source_id,
        source_type=source_type,
        duration_kind="turns",
        remaining=int(duration_turns),
        permanent=bool(permanent),
        stacks=max(1, int(stacks)),
        potency=float(potency),
        dispellable=final_dispellable,
        tags=list(tpl.tags or []),
        rules={
            "max_stacks": int(tpl.max_stacks or 1),
            "stack_mode": tpl.stack_mode or "refresh_duration",
            "exclusive_group": tpl.exclusive_group,
            "priority": int(tpl.priority or 100),
        },
        meta=dict(meta or {}),
    )

    # shield usa potency como “valor do escudo” (saldo)
    if tpl.effect_id == "shield":
        inst.meta["shield_value"] = int(round(float(potency)))

    effects.append(inst)
    _save_effects(target, effects)
    return True, f"{tpl.name} aplicado"


def remove_effect_by_uid(target: Dict[str, Any], uid: str) -> Tuple[bool, str]:
    effects = _ensure_effects(target)
    new_list, removed = _remove_by_uid(effects, uid)
    if not removed:
        return False, "Efeito não encontrado"
    _save_effects(target, new_list)
    tpl = get_effect_template(removed.effect_id)
    return True, f"{tpl.name if tpl else removed.effect_id} removido"


def dispel(target: Dict[str, Any], *, remove_debuffs: bool = True, tags: Optional[List[str]] = None, max_remove: int = 99) -> int:
    """
    Remove efeitos dispellable por tipo/tags.
    Retorna quantidade removida.
    """
    effects = _ensure_effects(target)
    kept: List[EffectInstance] = []
    removed_count = 0
    tagset = set(tags or [])

    for e in effects:
        if removed_count >= max_remove:
            kept.append(e)
            continue

        if not e.dispellable:
            kept.append(e)
            continue

        tpl = get_effect_template(e.effect_id)
        if not tpl:
            kept.append(e)
            continue

        if remove_debuffs and tpl.kind != "debuff":
            kept.append(e)
            continue

        if tagset and not (set(tpl.tags or []) & tagset):
            kept.append(e)
            continue

        # remove
        removed_count += 1

    _save_effects(target, kept)
    return removed_count


def can_act(entity: Dict[str, Any]) -> bool:
    """
    Retorna False se algum efeito ativo bloquear ação (ex.: stun).
    """
    mods = get_modifiers(entity)
    return not bool(mods.get(MOD_CANNOT_ACT))


def get_modifiers(entity: Dict[str, Any]) -> Dict[str, Any]:
    """
    Consolida modifiers de todos os efeitos ativos no entity.
    Regras:
    - *_mult soma (ex.: -0.30 + 0.15 = -0.15)
    - flags booleanas: True se algum setar True
    """
    effects = _ensure_effects(entity)

    # ordena por prioridade (menor primeiro)
    effects_sorted = sorted(
        effects,
        key=lambda e: int((e.rules or {}).get("priority", 100))
    )

    out: Dict[str, Any] = {}
    for e in effects_sorted:
        tpl = get_effect_template(e.effect_id)
        if not tpl:
            continue

        for k, v in (tpl.modifiers or {}).items():
            if k in (MOD_DAMAGE_DEALT_MULT, MOD_DAMAGE_TAKEN_MULT, MOD_HEAL_RECEIVED_MULT):
                out[k] = float(out.get(k, 0.0)) + float(v)  # soma de deltas
            elif k == MOD_CANNOT_ACT:
                if bool(v):
                    out[k] = True
            elif k == MOD_SHIELD_FLAT:
                # shield é tratado no pipeline de dano via meta["shield_value"]
                out[k] = True
            else:
                # fallback
                out[k] = v

    return out


def _apply_shield_if_any(target: Dict[str, Any], damage: int) -> int:
    """
    Se existir shield ativo, absorve dano e retorna dano restante.
    Atualiza/remover efeito quando esgota.
    """
    if damage <= 0:
        return 0

    effects = _ensure_effects(target)
    if not effects:
        return damage

    changed = False
    for e in effects:
        if e.effect_id != "shield":
            continue

        shield_val = int(e.meta.get("shield_value", 0))
        if shield_val <= 0:
            continue

        # absorve
        absorbed = min(shield_val, damage)
        shield_val -= absorbed
        damage -= absorbed
        e.meta["shield_value"] = shield_val
        changed = True

        # remove se zerou
        if shield_val <= 0:
            e.remaining = 0  # marca como expirado (tick vai limpar)
            changed = True

        if damage <= 0:
            break

    if changed:
        _save_effects(target, effects)

    return damage


def dispatch(event: str, ctx: CombatContext) -> None:
    """
    Dispara um evento do engine.
    No MVP, implementamos:
    - on_before_damage: aplica modifiers e shield
    - on_heal: aplica modifiers
    """
    ctx.event = event

    if event == EVENT_ON_BEFORE_DAMAGE:
        # 1) Modificadores do source (dano causado)
        src_mods = get_modifiers(ctx.source)
        dmg = int(ctx.damage)

        dealt_delta = float(src_mods.get(MOD_DAMAGE_DEALT_MULT, 0.0))
        if dealt_delta != 0.0:
            dmg = int(round(dmg * (1.0 + dealt_delta)))

        # 2) Modificadores do target (dano recebido)
        tgt_mods = get_modifiers(ctx.target)
        taken_delta = float(tgt_mods.get(MOD_DAMAGE_TAKEN_MULT, 0.0))
        if taken_delta != 0.0:
            dmg = int(round(dmg * (1.0 + taken_delta)))

        # 3) Shield (absorção)
        dmg = _apply_shield_if_any(ctx.target, dmg)

        ctx.damage = max(0, int(dmg))
        return

    if event == EVENT_ON_HEAL:
        tgt_mods = get_modifiers(ctx.target)
        heal = int(ctx.heal)

        heal_delta = float(tgt_mods.get(MOD_HEAL_RECEIVED_MULT, 0.0))
        if heal_delta != 0.0:
            heal = int(round(heal * (1.0 + heal_delta)))

        ctx.heal = max(0, int(heal))
        return

    # outros eventos ficam prontos para expansão
    return


def tick_turn(entity: Dict[str, Any], battle: Dict[str, Any], *, apply_to_hp_key: str = "hp") -> List[str]:
    """
    Processa ticks de DOT/HOT e expiração.
    Retorna mensagens curtas (você pode plugar no log do combate).
    - apply_to_hp_key: chave do HP do entity (player/monster podem divergir)
    """
    msgs: List[str] = []
    effects = _ensure_effects(entity)
    if not effects:
        return msgs

    # 1) aplicar ticks em on_turn_start
    for e in list(effects):
        if e.is_expired():
            continue

        tpl = get_effect_template(e.effect_id)
        if not tpl or not tpl.tick:
            continue

        # tick dano
        if TICK_DAMAGE in tpl.tick:
            td = tpl.tick[TICK_DAMAGE]
            if td.get("at") == "on_turn_start":
                base = int(td.get("base", 0))
                per_stack = int(td.get("per_stack", 0))

                # Se o efeito tiver dot_tick, ele manda no dano por stack (escala com ATK do aplicador)
                dot_tick = e.meta.get("dot_tick")
                if dot_tick is not None:
                    dmg = int(dot_tick) * max(1, int(e.stacks))
                else:
                    dmg = int(round((base + per_stack * max(0, e.stacks)) * float(e.potency)))

                if dmg > 0:
                    # DOT passa pelo pipeline (shield e dano recebido)
                    ctx = CombatContext(
                        event=EVENT_ON_BEFORE_DAMAGE,
                        source=entity,     # para DOT, source pode ser o próprio (MVP)
                        target=entity,
                        battle=battle,
                        damage=dmg,
                        damage_type=str(td.get("damage_type", "true")),
                    )
                    dispatch(EVENT_ON_BEFORE_DAMAGE, ctx)
                    final = int(ctx.damage)

                    # aplica dano final
                    hp = int(entity.get(apply_to_hp_key, 0))
                    hp = max(0, hp - final)
                    entity[apply_to_hp_key] = hp

                    if final > 0:
                        msgs.append(f"⛔ {tpl.name}: -{final} HP")

        # tick cura
        if TICK_HEAL in tpl.tick:
            th = tpl.tick[TICK_HEAL]
            if th.get("at") == "on_turn_start":
                base = int(th.get("base", 0))
                per_stack = int(th.get("per_stack", 0))
                heal = int(round((base + per_stack * max(0, e.stacks)) * float(e.potency)))
                if heal > 0:
                    ctx = CombatContext(
                        event=EVENT_ON_HEAL,
                        source=entity,
                        target=entity,
                        battle=battle,
                        heal=heal,
                    )
                    dispatch(EVENT_ON_HEAL, ctx)
                    final = int(ctx.heal)

                    hp = int(entity.get(apply_to_hp_key, 0))
                    max_hp = int(entity.get("hp_max", entity.get("max_hp", 0)) or 0)
                    if max_hp > 0:
                        hp = min(max_hp, hp + final)
                    else:
                        hp = hp + final

                    entity[apply_to_hp_key] = hp
                    if final > 0:
                        msgs.append(f"✅ {tpl.name}: +{final} HP")

    # 2) tick duração e expirar
    expired_ids: List[str] = []
    for e in effects:
        if not e.permanent:
            e.tick()

    kept: List[EffectInstance] = []
    for e in effects:
        if e.is_expired():
            tpl = get_effect_template(e.effect_id)
            expired_ids.append(tpl.name if tpl else e.effect_id)
        else:
            kept.append(e)

    if expired_ids:
        for name in expired_ids:
            msgs.append(f"⌛ {name} terminou")

    _save_effects(entity, kept)
    return msgs
