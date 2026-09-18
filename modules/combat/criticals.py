# modules/combat/criticals.py (VERSÃO FINAL: Sorte Excedente vira Dano + Suporte a Passivas)
import random
import math

def _clamp(v: float, lo: float, hi: float) -> float:
    """Garante que um valor permaneça dentro de um intervalo."""
    return max(lo, min(hi, v))

def _diminishing_crit_chance_from_luck(luck: int) -> float:
    """
    Calcula a chance teórica baseada na sorte.
    Com 200 Luck, isso retorna ~86.6%.
    """
    l = max(0, int(luck))
    return 100.0 * (1.0 - (0.99 ** l))

def get_crit_params(stats: dict) -> dict:
    """
    Gera parâmetros de crítico. 
    Agora converte chance desperdiçada (acima do cap) em Dano Crítico.
    """
    luck = int(stats.get("luck", 5))
    is_monster = 'monster_luck' in stats or 'monster_name' in stats

    # --- 1. Definição dos Limites (Caps) ---
    # Monstros têm limite menor para não explodir o jogador
    chance_cap = 30.0 if is_monster else 45.0 
    mega_chance_cap = 25.0

    # --- 2. Cálculo da Chance Bruta ---
    raw_chance = _diminishing_crit_chance_from_luck(luck)
    
    # A chance final de critar obedece o limite
    final_chance = _clamp(raw_chance, 1.0, chance_cap)

    # --- 3. A MÁGICA: Conversão de Excesso em Dano ---
    # Se sua chance teórica (ex: 86%) for maior que o limite (45%),
    # a diferença (41%) vira bônus de dano.
    excess_chance = max(0.0, raw_chance - chance_cap)
    
    # Fator de conversão: Cada 1% de chance excedente vira +0.01x de Dano (1%)
    # Ex: 200 Luck -> ~41% excedente -> +0.41x de Dano Crítico
    luck_damage_bonus = excess_chance / 100.0

    # --- 4. Bônus de Stats (Itens/Passivas) ---
    # Soma com o bônus vindo de skills (ex: Assassino)
    stat_damage_bonus = float(stats.get("crit_damage_mult", 0.0))
    
    total_bonus_damage = luck_damage_bonus + stat_damage_bonus

    # --- 5. Multiplicadores Finais ---
    if is_monster:
        base_mult = 1.5
        mega_base = 1.75
    else:
        base_mult = 1.6
        mega_base = 2.0

    return {
        "chance": final_chance,
        # Mega Chance também obedece limite
        "mega_chance": min(mega_chance_cap, luck / 2.0),
        
        # O Multiplicador final agora inclui a Sorte Excedente
        "mult": base_mult + total_bonus_damage,
        "mega_mult": mega_base + total_bonus_damage,
        "min_damage": 1,
    }

def roll_damage(attacker_stats: dict, target_stats: dict, options: dict = None) -> tuple[int, bool, bool]:
    """
    Rola o dano aplicando crítico, mega crítico, sorte excedente
    e agora SUPORTE A ESQUIVA, ACERTO GARANTIDO E DANO MÁGICO.
    """
    if options is None:
        options = {}

    # ==========================================
    # 1. IDENTIFICAÇÃO DO ATRIBUTO (A CORREÇÃO)
    # ==========================================
    is_magic = options.get("is_magic", False)

    if is_magic or options.get("damage_type") == "magic":
        # Tenta puxar o 'magic_attack' novo. Se não achar, usa a 'inteligencia' velha!
        base_atk = float(attacker_stats.get("magic_attack", attacker_stats.get("inteligencia", 0)))
    else:
        base_atk = float(attacker_stats.get("attack", 0))

    target_defense = float(target_stats.get("defense", 0))

    # ==========================
    # ESQUIVA DO ALVO (TARGET EVADE)
    # ==========================
    cannot_be_dodged = bool(options.get("cannot_be_dodged", False) or attacker_stats.get("cannot_be_dodged", False))

    if not cannot_be_dodged:
        target_ini = float(
            target_stats.get(
                "initiative",
                0
            )
            or 0
        )


        attacker_acc = float(
            attacker_stats.get(
                "accuracy_flat",
                0.0
            )
            or 0.0
        )


        dodge_flat = float(
            target_stats.get(
                "dodge_chance_flat",
                0.0
            )
            or 0.0
        )


        # Chance natural por iniciativa.
        # Mantemos a fórmula atual do
        # combat_engine: máximo natural 25%.
        evade_base = min(
            0.25,
            (
                target_ini *
                0.25
            )
            /
            100.0,
        )


        # Bônus direto de equipamento/passiva.
        # O limite total segue o helper oficial
        # existente em stats.py: 75%.
        evade_chance = min(
            0.75,
            evade_base
            +
            dodge_flat,
        )


        # Precisão do atacante reduz esquiva.
        evade_chance = max(
            0.0,
            evade_chance
            -
            attacker_acc,
        )

        if random.random() < evade_chance:
            # Esquivou completamente
            return 0, False, False

    # ==========================
    # CRÍTICO / MEGA CRÍTICO
    # ==========================
    params = get_crit_params(attacker_stats)

    skill_mult = float(options.get("damage_multiplier", 1.0))

    r = random.random() * 100.0

    bonus_chance_skill = float(options.get("bonus_crit_chance", 0.0)) * 100.0
    passive_flat = float(attacker_stats.get("crit_chance_flat", 0.0))

    final_chance = float(params.get("chance", 0.0)) + bonus_chance_skill + passive_flat

    final_chance = max(0.0, min(100.0, final_chance - float(target_stats.get("crit_resistance_flat", 0.0)) * 100.0))
    is_crit = not target_stats.get("crit_immune", False) and (r < final_chance)
    crit_mult, is_mega = 1.0, False

    if is_crit:
        if random.random() * 100.0 <= float(params.get("mega_chance", 0.0)):
            crit_mult, is_mega = float(params.get("mega_chance", 2.0)), True # Garantia de fallback
            if "mega_mult" in params:
                 crit_mult = float(params.get("mega_mult", 2.0))
        else:
            crit_mult = float(params.get("mult", 1.6))

        skill_crit_dmg_boost = float(options.get("next_hit_crit_damage_boost", 0.0))
        crit_mult += skill_crit_dmg_boost

    # ==========================
    # CÁLCULO FINAL DE DANO
    # ==========================
    attack_with_skill = base_atk * skill_mult
    boosted_attack = math.ceil(attack_with_skill * crit_mult)

    if is_magic or options.get("damage_type") == "magic":
        # Magia ignora a defesa física básica nesta fórmula (já foi mitigada no combat_engine)
        final_damage = max(int(params.get("min_damage", 1)), int(boosted_attack))
    else:
        # Ataque Físico normal bate de frente com a armadura do monstro
        final_damage = max(int(params.get("min_damage", 1)), int(boosted_attack - target_defense))

    tipo_dano = 'magic' if is_magic or options.get('damage_type') == 'magic' else 'physical'
    resistencia = float((target_stats.get('resistance') or {}).get(tipo_dano, 0.0))
    final_damage = max(0, math.ceil(final_damage * (1.0 - _clamp(resistencia, 0.0, 1.0))))
    return int(final_damage), is_crit, is_mega