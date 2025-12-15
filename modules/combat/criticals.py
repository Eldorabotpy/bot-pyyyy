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
    Rola o dano aplicando as novas regras.
    """
    if options is None:
        options = {}

    raw_attack = int(attacker_stats.get('attack', 0))
    target_defense = int(target_stats.get('defense', 0))
    
    # Pega os parâmetros calculados acima
    params = get_crit_params(attacker_stats)

    skill_mult = float(options.get("damage_multiplier", 1.0))

    # --- Rolagem do Dado ---
    r = random.random() * 100.0
    
    # Bônus direto na chance (ex: Skill ativa "Tiro Certeiro" +50% chance)
    # Esse bônus PODE passar do cap, pois é temporário da skill
    bonus_chance_skill = float(options.get("bonus_crit_chance", 0.0)) * 100.0
    
    # Bônus passivo flat (ex: +10% de chance fixa de um item lendário)
    passive_flat = float(attacker_stats.get("crit_chance_flat", 0.0)) # Já vem como 10.0
    
    final_chance = float(params.get("chance", 0.0)) + bonus_chance_skill + passive_flat
    
    is_crit = (r <= final_chance)
    crit_mult, is_mega = 1.0, False

    if is_crit:
        # Tenta Mega Crítico
        if random.random() * 100.0 <= float(params.get("mega_chance", 0.0)):
            crit_mult, is_mega = float(params.get("mega_mult", 2.0)), True
        else:
            crit_mult = float(params.get("mult", 1.6))
            
        # Adiciona bônus específico de Dano Crítico da skill (se houver)
        # Ex: "Próximo ataque tem +50% Dano Crítico"
        skill_crit_dmg_boost = float(options.get("next_hit_crit_damage_boost", 0.0))
        crit_mult += skill_crit_dmg_boost

    # --- Cálculo Final ---
    attack_with_skill = float(raw_attack) * skill_mult
    
    # Aplica o multiplicador (que agora pode ser gigante se tiver 200 Luck)
    boosted_attack = math.ceil(attack_with_skill * crit_mult)
    
    # Defesa reduz o dano final (exceto se for mágico puro ou penetração)
    damage_type = options.get("damage_type", "physical")
    
    if damage_type == "magic":
        # Magia ignora defesa física (usa M.Def em outro lugar, ou ignora aqui se for true dmg)
        final_damage = max(int(params.get("min_damage", 1)), boosted_attack)
    else:
        # Dano Físico sofre redução da defesa
        final_damage = max(int(params.get("min_damage", 1)), boosted_attack - target_defense)
    
    return final_damage, is_crit, is_mega