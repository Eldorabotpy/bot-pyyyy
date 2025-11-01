# modules/game_data/skills.py (VERSÃO COM MANA)

SKILL_DATA = {

     #===================================================================
     # ================> HABILIDADES DE EVOLUCAO <=======================
     #===================================================================
     # --- Habilidades de Evolução do Guerreiro ---
    "passive_bulwark": {
        "display_name": "Baluarte", "type": "passive", 
        "description": "Aumenta a sua Defesa base permanentemente.", 
        "effects": {"stat_add_mult": {"defense": 0.05}}},
    "active_whirlwind": {
        "display_name": "Redemoinho de Aço", "type": "active", 
        "mana_cost": 20, # <<< ADICIONADO
        "description": "Um ataque giratório que atinge múltiplos alvos.", 
        "effects": {"cooldown_turns": 3}},
    "active_holy_blessing": {
        "display_name": "Bênção Sagrada", "type": "active", 
        "mana_cost": 15, # <<< ADICIONADO
        "description": "Invoca poder divino para curar levemente os aliados.", 
        "effects": {"cooldown_turns": 5}
    },

    # --- Habilidades de Evolução do Berserker ---
    "passive_unstoppable": {
        "display_name": "Inabalável", "type": "passive", "description": 
        "A sua fúria torna-o resistente a efeitos de atordoamento.", 
        "effects": {"resistance": "stun"}},
    "active_unbreakable_charge": {
        "display_name": "Investida Inquebrável", "type": "active", 
        "mana_cost": 15, # <<< ADICIONADO
        "description": "Avança, ignorando parte do dano no próximo turno.", 
        "effects": {"cooldown_turns": 4}},
    "passive_last_stand": {
        "display_name": "Último Recurso", "type": "passive", 
        "description": "O seu dano aumenta massivamente quando a sua vida está baixa.", 
        "effects": {"low_hp_dmg_boost": 0.20}},

    # --- Habilidades de Evolução do Caçador ---
    "passive_animal_companion": {
        "display_name": "Companheiro Animal", "type": "passive", 
        "description": "Um lobo leal luta ao seu lado, atacando ocasionalmente.", 
        "effects": {"companion_attack": {"damage": 20, "chance": 0.3}}},
    "active_deadeye_shot": {
        "display_name": "Tiro de Mira Mortal", "type": "active", 
        "mana_cost": 10, # <<< ADICIONADO
        "description": "Aumenta massivamente a chance de crítico do próximo ataque.", 
        "effects": {"cooldown_turns": 3, "next_hit_crit_chance_boost": 0.75}},
    "passive_apex_predator": {
        "display_name": "Predador Alfa", "type": "passive", 
        "description": "Causa dano extra a monstros do tipo 'Boss'.", 
        "effects": {"bonus_damage_vs_type": {"type": "boss", "value": 0.15}}
    },

    # --- Habilidades de Evolução do Monge ---
    "active_iron_skin": {
        "display_name": "Pele de Ferro", "type": "active", 
        "mana_cost": 20, # <<< ADICIONADO
        "description": "Endurece o corpo com Ki, reduzindo o dano recebido por 2 turnos.", 
        "effects": {"cooldown_turns": 5, "self_buff": {"effect": "damage_reduction", "value": 0.5, "duration_turns": 2}}},
    "passive_elemental_strikes": {
        "display_name": "Golpes Elementais", "type": "passive", 
        "description": "Os seus ataques têm uma chance de causar dano elemental extra.", 
        "effects": {"chance_on_hit": {"effect": "extra_elemental_damage", "value": 25, "chance": 0.2}}},
    "active_transcendence": {
        "display_name": "Transcendência", "type": "active", 
        "mana_cost": 10, # <<< ADICIONADO
        "description": "Medita por um turno para recuperar uma grande quantidade de HP e Energia.", 
        "effects": {"cooldown_turns": 6, "channel_heal_energy": {"hp": 100, "energy": 20}}
    },

    # --- Habilidades de Evolução do Mago ---
    "active_curse_of_weakness": {
        "display_name": "Maldição da Fraqueza", "type": "active", 
        "mana_cost": 15, # <<< ADICIONADO
        "description": "Amaldiçoa o alvo, reduzindo o seu ataque por 3 turnos.", 
        "effects": {"cooldown_turns": 4, "debuff_target": {"stat": "attack", "value": -0.20, "duration_turns": 3}}},
    "passive_elemental_attunement": {
        "display_name": "Sintonia Elemental", "type": "passive", 
        "description": "Aumenta todo o dano mágico causado.", 
        "effects": {"stat_add_mult": {"attack": 0.10}}},
    "active_meteor_swarm": {
        "display_name": "Chuva de Meteoros", "type": "active", 
        "mana_cost": 30, # <<< ADICIONADO
        "description": "Invoca uma chuva de meteoros que atinge todos os inimigos.", 
        "effects": {"cooldown_turns": 5}
    },

    # --- Habilidades de Evolução do Bardo ---
    "active_song_of_valor": {
        "display_name": "Canção do Valor", "type": "active", 
        "mana_cost": 15, # <<< ADICIONADO
        "description": "Inspira os aliados, aumentando o ataque de todos no grupo por 3 turnos.", 
        "effects": {"cooldown_turns": 4, "party_buff": {"stat": "attack", "value": 0.15, "duration_turns": 3}}},
    "active_dissonant_melody": {
        "display_name": "Melodia Dissonante", "type": "active", 
        "mana_cost": 10, # <<< ADICIONADO
        "description": "Confunde o inimigo, com uma chance de o fazer perder o próximo turno.", 
        "effects": {"cooldown_turns": 4, "chance_to_stun": 0.25}},
    "passive_symphony_of_power": {
        "display_name": "Sinfonia do Poder", "type": "passive", 
        "description": "Os efeitos dos seus buffs de grupo são ampliados.", 
        "effects": {"buff_potency_increase": 0.20}
    },

    # --- Habilidades de Evolução do Assassino ---
    "active_shadow_strike": {
        "display_name": "Golpe Sombrio", "type": "active", 
        "mana_cost": 15, # <<< ADICIONADO
        "description": "Um ataque rápido das sombras que não pode ser esquivado.", 
        "effects": {"cooldown_turns": 3, "guaranteed_hit": True}},
    "passive_potent_toxins": {
        "display_name": "Toxinas Potentes", "type": "passive", 
        "description": "Os seus ataques têm uma chance de aplicar um veneno que causa dano ao longo do tempo.", 
        "effects": {"chance_on_hit": {"effect": "poison", "damage": 15, "duration_turns": 3, "chance": 0.3}}},
    "active_dance_of_a_thousand_cuts": {
        "display_name": "Dança das Mil Lâminas", "type": "active", 
        "mana_cost": 25, # <<< ADICIONADO
        "description": "Desfere uma rajada de 3 a 5 golpes rápidos.", 
        "effects": {"cooldown_turns": 5}
    },

    # --- Habilidades de Evolução do Samurai ---
    "passive_iai_stance": {
        "display_name": "Postura Iai", "type": "passive", 
        "description": "O primeiro ataque em cada combate tem uma chance de crítico muito aumentada.", "effects": {"first_hit_crit_chance_boost": 0.50}},
    "active_parry_and_riposte": {
        "display_name": "Aparar e Ripostar", "type": "active", 
        "mana_cost": 10, # <<< ADICIONADO
        "description": "Assume uma postura defensiva. Se for atacado, anula o dano e contra-ataca.", "effects": {"cooldown_turns": 4}},
    "active_banner_of_command": {
        "display_name": "Estandarte de Comando", "type": "active", 
        "mana_cost": 20, # <<< ADICIONADO
        "description": "Ergue um estandarte que aumenta a defesa de todos os aliados próximos.", 
        "effects": {"cooldown_turns": 5, "party_buff": {"stat": "defense", "value": 0.20, "duration_turns": 3}}
    },
    
    #====================================================================
    # HABILIDADES BASICAS (Adiquiridas via Evento/Drop
    # #====================================================================
    # (Estas já estavam corretas e com 'mana_cost')
    "guerreiro_corte_perfurante": {
        "display_name": "Corte Perfurante", "type": "active", "mana_cost": 10,
        "description": "Um golpe focado que perfura a armadura do inimigo, causando dano e reduzindo sua defesa por 3 turnos.",
         "effects": {"cooldown_turns": 0, "damage_multiplier": 1.2, "debuff_target": {"stat": "defense", "value": -0.20, "duration_turns": 3}}
    },
    "berserker_golpe_selvagem": {
        "display_name": "Golpe Selvagem", "type": "active", "mana_cost": 12,
        "description": "Um ataque poderoso que causa mais dano quanto menos vida você tiver.",
        "effects": {"cooldown_turns": 0, "damage_multiplier": 1.5, "low_hp_dmg_boost": 0.5}
    },
    "cacador_flecha_precisa": {
        "display_name": "Flecha Precisa", "type": "active", "mana_cost": 15,
        "description": "Um tiro certeiro com alta chance de acerto crítico.",
        "effects": {"cooldown_turns": 0, "damage_multiplier": 1.3, "bonus_crit_chance": 0.50}
    },
    "monge_rajada_de_punhos": {
        "display_name": "Rajada de Punhos", "type": "active", "mana_cost": 18,
        "description": "Ataca rapidamente, golpeando o inimigo 2 vezes.",
        "effects": {"cooldown_turns": 0, "damage_multiplier": 0.8, "multi_hit": 2}
    },
    "mago_bola_de_fogo": {
        "display_name": "Bola de Fogo", "type": "active", "mana_cost": 25,
        "description": "Um feitiço de alvo único que causa alto dano de fogo.",
        "effects": {"cooldown_turns": 0, "damage_multiplier": 2.5}
    },
    "bardo_melodia_restauradora": {
        "display_name": "Melodia Restauradora", "type": "active", "mana_cost": 18,
        "description": "Uma melodia suave que cura uma pequena quantidade de vida de todos os aliados.",
        "effects": {"cooldown_turns": 2, "party_heal": {"amount": 30}}
    },
    "assassino_ataque_furtivo": {
        "display_name": "Ataque Furtivo", "type": "active", "mana_cost": 20,
        "description": "Um golpe letal que ignora parte da defesa do inimigo.",
        "effects": {"cooldown_turns": 0, "damage_multiplier": 1.6, "defense_penetration": 0.50}
    },
    "samurai_corte_iaijutsu": {
        "display_name": "Corte Iaijutsu", "type": "active", "mana_cost": 18,
        "description": "Um saque rápido e mortal com a katana, com alta chance de crítico.",
        "effects": {"cooldown_turns": 0, "damage_multiplier": 1.4, "bonus_crit_chance": 0.30}
    },
}