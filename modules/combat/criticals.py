# modules/combat/criticals.py (VERSÃO CORRIGIDA E UNIFICADA)
import random
import math

def _clamp(v: float, lo: float, hi: float) -> float:
    """Garante que um valor permaneça dentro de um intervalo mínimo e máximo."""
    return max(lo, min(hi, v))

def _diminishing_crit_chance_from_luck(luck: int) -> float:
    """Calcula a chance de crítico com base na sorte, com retornos decrescentes."""
    l = max(0, int(luck))
    # A fórmula 1 - (0.99^LUCK) cria uma curva que cresce rápido no início e desacelera.
    return 100.0 * (1.0 - (0.99 ** l))

def get_crit_params(stats: dict) -> dict:
    """
    Função unificada que gera os parâmetros de crítico para qualquer entidade (jogador ou monstro).
    """
    luck = int(stats.get("luck", 5))
    
    # Determina se é um monstro ou jogador para definir limites diferentes
    is_monster = 'monster_luck' in stats or 'monster_name' in stats

    # Chance base de crítico, com um teto maior para jogadores
    chance_cap = 30.0 if is_monster else 40.0
    chance = _clamp(_diminishing_crit_chance_from_luck(luck), 1.0, chance_cap)

    # Multiplicadores de dano
    mult = 1.5 if is_monster else 1.6
    mega_mult = 1.75 if is_monster else 2.0

    return {
        "chance": chance,
        "mega_chance": min(25.0, luck / 2.0), # Chance de um crítico virar um MEGA crítico
        "mult": mult,
        "mega_mult": mega_mult,
        "min_damage": 1,
    }

# Em: modules/combat/criticals.py

def roll_damage(attacker_stats: dict, target_stats: dict, options: dict = None) -> tuple[int, bool, bool]:
    """
    (VERSÃO CORRIGIDA: AGORA LÊ O 'damage_multiplier' DAS SKILLS)
    """
    if options is None:
        options = {}

    # 1. Extrai os valores numéricos de dentro dos dicionários
    raw_attack = int(attacker_stats.get('attack', 0))
    target_defense = int(target_stats.get('defense', 0))
    
    # 2. Gera os parâmetros de crítico para o atacante
    params = get_crit_params(attacker_stats)

    # --- 3. (NOVO) Lê o multiplicador da SKILL (dos 'options') ---
    # 'options' é o dicionário 'skill_effects' que passámos
    skill_mult = float(options.get("damage_multiplier", 1.0))

    # 4. Lógica de rolagem de CRÍTICO (inalterada)
    r = random.random() * 100.0
    is_crit = (r <= float(params.get("chance", 0.0)))
    crit_mult, is_mega = 1.0, False # Multiplicador do crítico

    if is_crit:
        if random.random() * 100.0 <= float(params.get("mega_chance", 0.0)):
            crit_mult, is_mega = float(params.get("mega_mult", 2.0)), True
        else:
            crit_mult = float(params.get("mult", 1.6))

    # --- 5. Cálculo do dano final (CORRIGIDO) ---
    
    # Primeiro, aplica o multiplicador da SKILL
    attack_with_skill = float(raw_attack) * skill_mult
    
    # Segundo, aplica o multiplicador do CRÍTICO
    boosted_attack = math.ceil(attack_with_skill * crit_mult)
    
    # Terceiro, subtrai a defesa
    final_damage = max(int(params.get("min_damage", 1)), boosted_attack - target_defense)
    
    return final_damage, is_crit, is_mega