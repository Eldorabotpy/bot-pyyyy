# modules/game_data/skills.py (VERSÃO COM MANA)

SKILL_DATA = {

    #===================================================================
    # ================> HABILIDADES DE EVOLUCAO <=======================
    #===================================================================
    
    # --- Habilidades de Evolução do Guerreiro/Tank ---
    "passive_bulwark": {
        "display_name": "Baluarte", "type": "passive", 
        "description": "Aumenta a sua Defesa base permanentemente.", 
        "effects": {"stat_add_mult": {"defense": 0.05}},
        "allowed_classes": ["guerreiro"]
    },         
    "active_whirlwind": {
        "display_name": "Redemoinho de Aço", "type": "active", 
        "mana_cost": 20, 
        "description": "Um ataque giratório que atinge múltiplos alvos.", 
        "effects": {"cooldown_turns": 3, "damage_multiplier": 1.1, "aoe": True},
        "allowed_classes": ["guerreiro"]
    },      
    "active_holy_blessing": {
        "display_name": "Bênção Sagrada", "type": "support", # <-- AJUSTADO PARA SUPORTE
        "mana_cost": 15, 
        "description": "Invoca poder divino para curar levemente os aliados (20% HP Máx do lançador).", 
        "effects": {"cooldown_turns": 5, "party_heal": {"amount_percent_max_hp": 0.20}},
        "allowed_classes": ["guerreiro"]
    },
    "guerreiro_placeholder_t4_def": {
        "display_name": "Defesa Colossal", "type": "passive", 
        "description": "Reduz o dano recebido permanentemente. (T4)",
        "effects": {"damage_reduction_mult": 0.05},
        "allowed_classes": ["guerreiro"]
    },
    
    # --- Habilidades de Evolução do Berserker ---
    "passive_unstoppable": {
        "display_name": "Inabalável", "type": "passive", 
        "description": "A sua fúria torna-o resistente a efeitos de atordoamento.", 
        "effects": {"resistance": "stun"},
        "allowed_classes": ["berserker"]
    },
    "active_unbreakable_charge": {
        "display_name": "Investida Inquebrável", "type": "active", 
        "mana_cost": 15, 
        "description": "Avança, ignorando parte do dano no próximo turno.", 
        "effects": {"cooldown_turns": 4, "self_buff": {"effect": "damage_reduction", "value": 0.4, "duration_turns": 1}},
        "allowed_classes": ["berserker"]
    },
    "passive_last_stand": {
        "display_name": "Último Recurso", "type": "passive", 
        "description": "O seu dano aumenta massivamente quando a sua vida está baixa (20% mais dano).", 
        "effects": {"low_hp_dmg_boost": 0.20},
        "allowed_classes": ["berserker"]     
    },
    "berserker_placeholder_t6_atk": {
        "display_name": "Golpe Divino da Ira", "type": "active", 
        "mana_cost": 60,
        "description": "Um ataque supremo que ignora defesa e causa 4x o dano base.",
        "effects": {"cooldown_turns": 8, "damage_multiplier": 4.0, "defense_penetration": 1.0},
        "allowed_classes": ["berserker"]
    },

    # --- Habilidades de Evolução do Caçador ---
    "passive_animal_companion": {
        "display_name": "Companheiro Animal", "type": "passive", 
        "description": "Um lobo leal luta ao seu lado, atacando ocasionalmente.", 
        "effects": {"companion_attack": {"damage": 20, "chance": 0.3}},
        "allowed_classes": ["cacador"]
    },
    "active_deadeye_shot": {
        "display_name": "Tiro de Mira Mortal", "type": "active", 
        "mana_cost": 10, 
        "description": "Aumenta massivamente a chance de crítico do próximo ataque.", 
        "effects": {"cooldown_turns": 3, "next_hit_crit_chance_boost": 0.75},
        "allowed_classes": ["cacador"]     
    },
    "passive_apex_predator": {
        "display_name": "Predador Alfa", "type": "passive", 
        "description": "Causa dano extra a monstros do tipo 'Boss'.", 
        "effects": {"bonus_damage_vs_type": {"type": "boss", "value": 0.15}},
        "allowed_classes": ["cacador"]
    },
    "cacador_placeholder_t4_atk": {
        "display_name": "Flecha Ricocheteante", "type": "active", 
        "mana_cost": 25,
        "description": "Atira uma flecha que acerta o alvo principal e ricocheteia, atingindo um segundo alvo.",
        "effects": {"cooldown_turns": 4, "damage_multiplier": 1.5, "multi_hit": 2, "single_target": False},
        "allowed_classes": ["cacador"]
    },

    # --- Habilidades de Evolução do Monge ---
    "active_iron_skin": {
        "display_name": "Pele de Ferro", "type": "support", # <-- AJUSTADO PARA SUPORTE
        "mana_cost": 20, 
        "description": "Endurece o corpo com Ki, reduzindo o dano recebido por 2 turnos.", 
        "effects": {"cooldown_turns": 5, "self_buff": {"effect": "damage_reduction", "value": 0.5, "duration_turns": 2}},
        "allowed_classes": ["monge"]      
    },
    "passive_elemental_strikes": {
        "display_name": "Golpes Elementais", "type": "passive", 
        "description": "Os seus ataques têm uma chance de causar dano elemental extra (Magia).", 
        "effects": {
            "chance_on_hit": {
                "effect": "extra_elemental_damage", 
                "value": 25, 
                "chance": 0.2,
                "damage_type": "magic" # <<< ADICIONADO
            }
        },
        "allowed_classes": ["monge"]      
    },
    "active_transcendence": {
        "display_name": "Transcendência", "type": "support", # <-- AJUSTADO PARA SUPORTE
        "mana_cost": 10,
        "description": "Medita por um turno para recuperar 15% HP e 15% MP/Energia.", 
        "effects": {"cooldown_turns": 6, "channel_heal_percent": {"hp": 0.15, "mp": 0.15}},
        "allowed_classes": ["monge"]
    },
    "monge_placeholder_t4_atk": {
        "display_name": "Palma do Trovão", "type": "active", 
        "mana_cost": 30,
        "description": "Libera uma onda de Ki que causa dano em área e tem chance de atordoar.",
        "effects": {"cooldown_turns": 5, "damage_multiplier": 1.5, "aoe": True, "chance_to_stun": 0.15},
        "allowed_classes": ["monge"]
    },


    # --- Habilidades de Evolução do Mago ---
    "active_curse_of_weakness": {
        "display_name": "Maldição da Fraqueza", "type": "support", # <-- AJUSTADO PARA SUPORTE
        "mana_cost": 15, 
        "description": "Amaldiçoa o alvo, reduzindo o seu ataque em 20% por 3 turnos.", 
        "effects": {"cooldown_turns": 4, "debuff_target": {"stat": "attack", "value": -0.20, "duration_turns": 3}},
        "allowed_classes": ["mago"]      
    },
    "passive_elemental_attunement": {
        "display_name": "Sintonia Elemental", "type": "passive", 
        "description": "Aumenta o dano mágico em 10% e o ataque base em 5%.", 
        "effects": {"damage_type_mult": {"magic": 0.10}, "stat_add_mult": {"attack": 0.05}},
        "allowed_classes": ["mago"]      
    },
    "active_meteor_swarm": {
        "display_name": "Chuva de Meteoros", "type": "active", 
        "mana_cost": 30,
        "description": "Invoca uma chuva de meteoros que atinge todos os inimigos (Dano Mágico).", 
        "effects": {
            "cooldown_turns": 5,
            "damage_multiplier": 2.0, 
            "damage_type": "magic", 
            "aoe": True
        },
        "allowed_classes": ["mago"]
    },
    "active_arcane_ward": { # NOVO T4 PLACEHOLDER (Defesa)
        "display_name": "Escudo Arcano", "type": "support",
        "mana_cost": 35,
        "description": "Cria uma barreira de mana que reduz em 25% o dano MÁGICO recebido pelo grupo por 2 turnos.",
        "effects": {"cooldown_turns": 6, "party_buff": {"stat": "magic_resistance", "value": 0.25, "duration_turns": 2}},
        "allowed_classes": ["mago"]
    },

    # --- Habilidades de Evolução do Bardo ---
    "active_song_of_valor": {
        "display_name": "Canção do Valor", "type": "support", # <-- AJUSTADO PARA SUPORTE
        "mana_cost": 15, 
        "description": "Inspira os aliados, aumentando o ataque de todos no grupo em 15% por 3 turnos.", 
        "effects": {"cooldown_turns": 4, "party_buff": {"stat": "attack", "value": 0.15, "duration_turns": 3}},
        "allowed_classes": ["bardo"]
    },
    "active_dissonant_melody": {
        "display_name": "Melodia Dissonante", "type": "support", # <-- AJUSTADO PARA SUPORTE (CC não gasta turno de ataque)
        "mana_cost": 10, 
        "description": "Confunde o inimigo, com 25% de chance de o fazer perder o próximo turno (Stun).", 
        "effects": {"cooldown_turns": 4, "chance_to_stun": 0.25},
        "allowed_classes": ["bardo"]      
    },
    "passive_symphony_of_power": {
        "display_name": "Sinfonia do Poder", "type": "passive", 
        "description": "Os efeitos dos seus buffs de grupo são ampliados em 20%.", 
        "effects": {"buff_potency_increase": 0.20},
        "allowed_classes": ["bardo"]
    },
    "passive_perfect_pitch": { # NOVO T5 PLACEHOLDER
        "display_name": "Tom Perfeito", "type": "passive", 
        "description": "Os seus buffs têm 100% de chance de serem aplicados (imunidade a falhas de debuff/buff).",
        "effects": {"guaranteed_buff_success": True},
        "allowed_classes": ["bardo"]
    },

    # --- Habilidades de Evolução do Assassino ---
    "active_shadow_strike": {
        "display_name": "Golpe Sombrio", "type": "active", 
        "mana_cost": 15, 
        "description": "Um ataque rápido das sombras que não pode ser esquivado.", 
        "effects": {"cooldown_turns": 3, "guaranteed_hit": True, "damage_multiplier": 1.4},
        "allowed_classes": ["assassino"]      
    },
    "passive_potent_toxins": {
        "display_name": "Toxinas Potentes", "type": "passive", 
        "description": "Os seus ataques têm 30% de chance de aplicar veneno (15 Dano/3 Turnos).", 
        "effects": {"chance_on_hit": {"effect": "poison", "damage": 15, "duration_turns": 3, "chance": 0.3}},
        "allowed_classes": ["assassino"]      
    },
    "active_dance_of_a_thousand_cuts": {
        "display_name": "Dança das Mil Lâminas", "type": "active", 
        "mana_cost": 25, 
        "description": "Desfere uma rajada de 3 a 5 golpes rápidos.", 
        "effects": {"cooldown_turns": 5, "multi_hit_min": 3, "multi_hit_max": 5, "damage_multiplier": 0.6},
        "allowed_classes": ["assassino"]
    },
    "active_guillotine_strike": { # NOVO T5 PLACEHOLDER
        "display_name": "Golpe Guilhotina", "type": "active", 
        "mana_cost": 45,
        "description": "Ataque massivo com 50% de dano bônus contra alvos com menos de 30% de HP (Execução).",
        "effects": {"cooldown_turns": 6, "damage_multiplier": 2.5, "bonus_damage_if_low_hp_target": 0.50},
        "allowed_classes": ["assassino"]
    },

    # --- Habilidades de Evolução do Samurai ---
    "passive_iai_stance": {
        "display_name": "Postura Iai", "type": "passive", 
        "description": "O primeiro ataque em cada combate tem uma chance de crítico muito aumentada (50%).", "effects": {"first_hit_crit_chance_boost": 0.50},
        "allowed_classes": ["samurai"]      
    },
    "active_parry_and_riposte": {
        "display_name": "Aparar e Ripostar", "type": "active", 
        "mana_cost": 10, 
        "description": "Assume uma postura que, se atacado, anula o dano e contra-ataca (próximo turno).", 
        "effects": {"cooldown_turns": 4, "stance_parry": True, "duration_turns": 1},
        "allowed_classes": ["samurai"]      
    },
    "active_banner_of_command": {
        "display_name": "Estandarte de Comando", "type": "support", # <-- AJUSTADO PARA SUPORTE
        "mana_cost": 20, 
        "description": "Ergue um estandarte que aumenta a defesa de todos os aliados próximos em 20% por 3 turnos.", 
        "effects": {"cooldown_turns": 5, "party_buff": {"stat": "defense", "value": 0.20, "duration_turns": 3}},
        "allowed_classes": ["samurai"]
    },
    "passive_perfect_parry": { # NOVO T5 PLACEHOLDER
        "display_name": "Aparar Perfeito", "type": "passive", 
        "description": "10% de chance de aparar automaticamente e anular o dano de qualquer ataque físico.",
        "effects": {"chance_to_block_physical": 0.10},
        "allowed_classes": ["samurai"]
    },


    # --- Habilidades de Evolução do CURANDEIRO (NOVA) ---
    "active_divine_touch": {
        "display_name": "Toque Divino", "type": "support", 
        "mana_cost": 20, 
        "description": "Cura 25% do HP Máximo do Curandeiro e remove 1 debuff.", 
        "effects": {"cooldown_turns": 3, "self_heal_percent": 0.25, "remove_debuffs": 1},
        "allowed_classes": ["curandeiro"]
    },
    "passive_aegis_of_faith": {
        "display_name": "Égide da Fé", "type": "passive", 
        "description": "Aumenta a potência dos buffs de Defesa e Resistência em 20%.",
        "effects": {"buff_stat_potency_increase": {"defense": 0.20, "magic_resistance": 0.20}},
        "allowed_classes": ["curandeiro"]
    },
    "active_celestial_shield": {
        "display_name": "Escudo Celestial", "type": "support", 
        "mana_cost": 40, 
        "description": "Dá um escudo a todos no grupo que absorve dano igual a 100% da Defesa do Curandeiro (1 turno).",
        "effects": {"cooldown_turns": 6, "party_buff": {"stat": "shield_based_on_def", "value": 1.0, "duration_turns": 1}},
        "allowed_classes": ["curandeiro"]
    },

    
    #====================================================================
    # HABILIDADES BASICAS (Adiquiridas via Evento/Drop)
    # #====================================================================
    "guerreiro_corte_perfurante": {
        "display_name": "Corte Perfurante", "type": "active", "mana_cost": 10,
        "description": "Um golpe focado que perfura a armadura, reduzindo a defesa inimiga em 20% por 3 turnos.",
         "effects": {"cooldown_turns": 0, "damage_multiplier": 1.2, "debuff_target": {"stat": "defense", "value": -0.20, "duration_turns": 3}},
         "allowed_classes": ["guerreiro"]
    },
    "berserker_golpe_selvagem": {
        "display_name": "Golpe Selvagem", "type": "active", "mana_cost": 12,
        "description": "Um ataque poderoso que causa mais dano quanto menos vida você tiver (50% bônus).",
        "effects": {"cooldown_turns": 0, "damage_multiplier": 1.5, "low_hp_dmg_boost": 0.5},
        "allowed_classes": ["berserker"]
    },
    "cacador_flecha_precisa": {
        "display_name": "Flecha Precisa", "type": "active", "mana_cost": 15,
        "description": "Um tiro certeiro com 50% de chance de acerto crítico bônus.",
        "effects": {"cooldown_turns": 0, "damage_multiplier": 1.3, "bonus_crit_chance": 0.50},
        "allowed_classes": ["cacador"]
    },
    "monge_rajada_de_punhos": {
        "display_name": "Rajada de Punhos", "type": "active", "mana_cost": 18,
        "description": "Ataca rapidamente, golpeando o inimigo 2 vezes (Dano reduzido).",
        "effects": {"cooldown_turns": 0, "damage_multiplier": 0.8, "multi_hit": 2},
        "allowed_classes": ["monge"]
    },
    "mago_bola_de_fogo": {
        "display_name": "Bola de Fogo", "type": "active", "mana_cost": 25,
        "description": "Um feitiço de alvo único que causa alto dano de fogo (Mágico).",
        "effects": {
            "cooldown_turns": 0, 
            "damage_multiplier": 2.5,
            "damage_type": "magic" 
        },
        "allowed_classes": ["mago"]
    },
    "bardo_melodia_restauradora": {
        "display_name": "Melodia Restauradora", "type": "support", # <-- AJUSTADO PARA SUPORTE
        "mana_cost": 18,
        "description": "Uma melodia suave que cura 30 HP de todos os aliados.",
        "effects": {"cooldown_turns": 2, "party_heal": {"amount": 30}},
        "allowed_classes": ["bardo"]
    },
    "assassino_ataque_furtivo": {
        "display_name": "Ataque Furtivo", "type": "active", "mana_cost": 20,
        "description": "Um golpe letal que ignora 50% da defesa do inimigo.",
        "effects": {"cooldown_turns": 0, "damage_multiplier": 1.6, "defense_penetration": 0.50},
        "allowed_classes": ["assassino"]
    },
    "samurai_corte_iaijutsu": {
        "display_name": "Corte Iaijutsu", "type": "active", "mana_cost": 18,
        "description": "Um saque rápido e mortal com a katana, com 30% de chance de crítico bônus.",
        "effects": {"cooldown_turns": 0, "damage_multiplier": 1.4, "bonus_crit_chance": 0.30},
        "allowed_classes": ["samurai"]
    },
    "samurai_sombra_demoniaca": {
        "display_name": "Sombra Demoníaca",
        "description": "Ataca duas vezes com 100% de chance de acerto crítico (Dano reduzido).",
        "type": "active", 
        "mana_cost": 25,
        
        "effects": {
            "cooldown_turns": 5, 
            "multi_hit": 2,
            "bonus_crit_chance": 1.0, 
            "damage_multiplier": 0.9
        }
    },
}