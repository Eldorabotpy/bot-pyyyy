# modules/game_data/skills.py (VERSÃO COM MANA)

SKILL_DATA = {

    # ===================================================================
    # ================> SKILLS DE EVOLUÇÃO (T2-T6) <===============
    # ===================================================================

    # --- Novas Habilidades de Evolução do Guerreiro (Defesa) ---

    "evo_knight_aegis": {
        "display_name": "Égide do Cavaleiro",
        "type": "passive",
        "description": "Sua dedicação à defesa aumenta seu HP máximo e sua Defesa Física.",
        "allowed_classes": ["guerreiro"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: +10% HP Máx, +5% DEF.",
                "effects": {"stat_add_mult": {"max_hp": 0.10, "defense": 0.05}}
            },
            "epica": {
                "description": "Épica: +15% HP Máx, +8% DEF, +10% Resist. Física.",
                "effects": {"stat_add_mult": {"max_hp": 0.15, "defense": 0.08}, 
                            "resistance_mult": {"physical": 0.10}}
            },
            "lendaria": {
                "description": "Lendária: +20% HP Máx, +10% DEF, +10% Resist. Física, -15% Chance de Crítico Sofrido.",
                "effects": {"stat_add_mult": {"max_hp": 0.20, "defense": 0.10}, 
                            "resistance_mult": {"physical": 0.10}, 
                            "crit_resistance_flat": 0.15}
            }
        }
    },

    "evo_templar_divine_light": {
        "display_name": "Luz Divina do Templário",
        "type": "support",  # <--- Focamos no Suporte para garantir a Cura/Buff
        "description": "Invoca a Luz Divina, curando aliados e punindo inimigos com poder sagrado.",
        "allowed_classes": ["guerreiro"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 4, Mana 20): Cura o grupo (50% do M.Atk do Templário).",
                "mana_cost": 20,
                "effects": {
                    "cooldown_turns": 4,
                    # Adaptação: Cura baseada no Ataque Mágico (Híbrido)
                    "party_heal": {
                        "heal_type": "magic_attack",
                        "heal_scale": 0.5
                    },
                    "party_buff": {
                        "buff_name": "Luz Sagrada",
                        "buff_value": "Cura e Dano Sagrado",
                        "duration": "Instantâneo"
                    }
                }
            },
            "epica": {
                "description": "Épica (CD 4, Mana 20): Cura (75% M.Atk) e Purifica o grupo.",
                "mana_cost": 20,
                "effects": {
                    "cooldown_turns": 4,
                    "party_heal": {
                        "heal_type": "magic_attack",
                        "heal_scale": 0.75
                    },
                    "party_buff": {
                        "buff_name": "Purificação Sagrada",
                        "buff_value": "Cura / Remove Debuffs",
                        "duration": "Instantâneo"
                    }
                }
            },
            "lendaria": {
                "description": "Lendária (CD 3, Mana 20): Cura (100% M.Atk), Purifica e +10% DEF.",
                "mana_cost": 20,
                "effects": {
                    "cooldown_turns": 3,
                    "party_heal": {
                        "heal_type": "magic_attack",
                        "heal_scale": 1.0
                    },
                    # O Buff visual combina a purificação e a defesa
                    "party_buff": {
                        "buff_name": "Julgamento Divino",
                        "buff_value": "Purificar / +10% DEF",
                        "duration": "2 turnos"
                    }
                }
            }
        }
    },

    "evo_divine_guardian_fortress": {
        "display_name": "Fortaleza do Guardião Divino",
        "type": "passive",
        "description": "Sua fé e aço se unem, tornando-o uma fortaleza impenetrável.",
        "allowed_classes": ["guerreiro"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: +15% Resist. Física, +15% Resist. Mágica. Imune a Acertos Críticos.",
                "effects": {"resistance_mult": {"physical": 0.15, "magic": 0.15},
                            "crit_immune": True}
            },
            "epica": {
                "description": "Épica: Resists +20%. Imune a Crítico. Ganha Escudo de 15% HP no início do combate.",
                "effects": {"resistance_mult": {"physical": 0.20, "magic": 0.20},
                            "crit_immune": True,
                            "start_of_combat_shield_percent": 0.15}
            },
            "lendaria": {
                "description": "Lendária: Resists +25%. Imune a Crítico. Escudo inicial de 25% HP. Sobrevive a 1 golpe mortal (1/combate).",
                "effects": {"resistance_mult": {"physical": 0.25, "magic": 0.25},
                            "crit_immune": True,
                            "start_of_combat_shield_percent": 0.25,
                            "ignore_death_once": True}
            }
        }
    },

    "evo_aegis_avatar_incarnate": {
        "display_name": "Encarnação da Égide",
        "type": "support",  # <--- Ativa o sistema de logs de grupo
        "description": "Torna-se a proteção divina, refletindo dano e recusando a morte.",
        "allowed_classes": ["guerreiro"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 8, Mana 40): Reflete 100% do dano (Visual/Roleplay).",
                "mana_cost": 40,
                "effects": {
                    "cooldown_turns": 8,
                    # Log Visual para o grupo saber que o Tank está ativo
                    "party_buff": {
                        "buff_name": "Espinhos da Égide",
                        "buff_value": "Refletir 100% Dano",
                        "duration": "2 turnos"
                    }
                }
            },
            "epica": {
                "description": "Épica (CD 7, Mana 40): Reflete 100% e Reduz 30% do dano.",
                "mana_cost": 40,
                "effects": {
                    "cooldown_turns": 7,
                    "party_buff": {
                        "buff_name": "Barreira de Retaliação",
                        "buff_value": "Refletir / -30% Dano",
                        "duration": "3 turnos"
                    }
                }
            },
            "lendaria": {
                "description": "Lendária (CD 7, Mana 40): Reflete, Reduz 50% e Imortalidade.",
                "mana_cost": 40,
                "effects": {
                    "cooldown_turns": 7,
                    "party_buff": {
                        "buff_name": "Avatar da Égide",
                        "buff_value": "Refletir / -50% Dano / IMORTAL",
                        "duration": "3 turnos"
                    },
                    # Chave marcadora (para uso futuro ou lógica personalizada)
                    "prevent_death_active": True
                }
            }
        }
    },

    "evo_divine_legend_miracle": {
        "display_name": "Milagre da Lenda Divina",
        "type": "passive",  # <--- Aura processada pelo stats.py
        "description": "Sua presença lendária inspira milagres, protegendo todo o grupo da morte.",
        "allowed_classes": ["guerreiro"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: Aura (+5% HP Máx, +5% Resistências).",
                "effects": {
                    "party_aura": {
                        "stat_add_mult": {
                            "max_hp": 0.05
                        },
                        "resistance_mult": {
                            "physical": 0.05,
                            "magic": 0.05
                        }
                    }
                }
            },
            "epica": {
                "description": "Épica: Aura (+10% HP, +8% Resistências). Regeneração de 1% HP/turno.",
                "effects": {
                    "party_aura": {
                        "stat_add_mult": {
                            "max_hp": 0.10
                        },
                        "resistance_mult": {
                            "physical": 0.08,
                            "magic": 0.08
                        },
                        # Simula "Aumento de Cura" através de Regen passiva
                        "hp_regen_percent": 0.01
                    }
                }
            },
            "lendaria": {
                "description": "Lendária: Aura (+15% HP, +12% Resists). Reg. 2% HP/turno. Chance de evitar a morte.",
                "effects": {
                    "party_aura": {
                        "stat_add_mult": {
                            "max_hp": 0.15
                        },
                        "resistance_mult": {
                            "physical": 0.12,
                            "magic": 0.12
                        },
                        "hp_regen_percent": 0.02,
                        # Chave especial para lógica futura ou engine.py
                        "prevent_death_mechanic": True
                    }
                }
            }
        }
    },

    # --- Novas Habilidades de Evolução do Berserker (Ofensiva) ---

    "evo_barbarian_wrath": {
        "display_name": "Ira do Bárbaro",
        "type": "passive",
        "description": "A fúria alimenta seus golpes, aumentando seu ataque e tenacidade.",
        "allowed_classes": ["berserker"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: +10% Ataque Físico, +10% Tenacidade (Resist. Stun/Slow).",
                "effects": {"stat_add_mult": {"attack": 0.10}, "tenacity_mult": 0.10}
            },
            "epica": {
                "description": "Épica: +15% Atk, +15% Tenacidade, +5% Agilidade (Vel. Ataque).",
                "effects": {"stat_add_mult": {"attack": 0.15, "agility": 0.05}, "tenacity_mult": 0.15}
            },
            "lendaria": {
                "description": "Lendária: +20% Atk, +20% Tenacidade, +8% Agilidade. 10% de chance de aplicar 'Fratura' (-10% DEF).",
                "effects": {"stat_add_mult": {"attack": 0.20, "agility": 0.08}, "tenacity_mult": 0.20,
                            "chance_on_hit": {"effect": "debuff_target", "chance": 0.10, "stat": "defense", "value": -0.10, "duration_turns": 2}}
            }
        }
    },
    # --- Novas Habilidades de Evolução do Berserker (Ofensiva) ---

    "evo_savage_reckless_blows": {
        "display_name": "Golpes Impiedosos do Selvagem",
        "type": "active", # Buff
        "description": "Abraça a fúria total, sacrificando sua defesa por um poder de ataque avassalador.",
        "allowed_classes": ["berserker"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (3 turnos, CD 6): Reduz sua Defesa Fís/Mag em 50%, mas aumenta seu Ataque Físico em 30%.",
                "mana_cost": 15,
                "effects": {"cooldown_turns": 6, "duration_turns": 3,
                            "apply_self_buff": {"effect": "multi_stat_buff",
                                                "buffs": {"attack_mult": 0.30, "defense_mult": -0.50, "magic_resist_mult": -0.50}}}
            },
            "epica": {
                "description": "Épica (3 turnos, CD 5): Reduz Defesa em 40%, Aumenta Ataque em 40%. Ganha +10% de Chance de Crítico.",
                "mana_cost": 15,
                "effects": {"cooldown_turns": 5, "duration_turns": 3,
                            "apply_self_buff": {"effect": "multi_stat_buff",
                                                "buffs": {"attack_mult": 0.40, "defense_mult": -0.40, "magic_resist_mult": -0.40, "crit_chance_flat": 0.10}}}
            },
            "lendaria": {
                "description": "Lendária (4 turnos, CD 5): Reduz Defesa em 30%, Aumenta Ataque em 50%. Ganha +15% Crítico e +10% Roubo de Vida.",
                "mana_cost": 15,
                "effects": {"cooldown_turns": 5, "duration_turns": 4,
                            "apply_self_buff": {"effect": "multi_stat_buff",
                                                "buffs": {"attack_mult": 0.50, "defense_mult": -0.30, "magic_resist_mult": -0.30, "crit_chance_flat": 0.15, "lifesteal_flat": 0.10}}}
            }
        }
    },

    "evo_primal_wrath_armorbreaker": {
        "display_name": "Quebra-Armadura da Ira Primordial",
        "type": "passive",
        "description": "A encarnação da raiva. Seus golpes são tão poderosos que ignoram defesas.",
        "allowed_classes": ["berserker"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: Você ganha permanentemente 15% de Penetração de Armadura e +10% de Dano Crítico.",
                "effects": {"stat_add_mult": {"armor_penetration": 0.15, "crit_damage_mult": 0.10}}
            },
            "epica": {
                "description": "Épica: +20% Pen. Armadura, +20% Dano Crítico. Seus ataques não podem ser 'Esquivados'.",
                "effects": {"stat_add_mult": {"armor_penetration": 0.20, "crit_damage_mult": 0.20},
                            "cannot_be_dodged": True}
            },
            "lendaria": {
                "description": "Lendária: +30% Pen. Armadura, +30% Dano Crítico. Seus ataques não podem ser 'Esquivados' nem 'Bloqueados/Aparados'.",
                "effects": {"stat_add_mult": {"armor_penetration": 0.30, "crit_damage_mult": 0.30},
                            "cannot_be_dodged": True,
                            "cannot_be_blocked": True}
            }
        }
    },

    "evo_calamity_shatter_earth": {
        "display_name": "Ruína da Calamidade",
        "type": "active", # Ataque AoE
        "description": "Um desastre natural ambulante. Bate no chão com fúria apocalíptica, destruindo tudo.",
        "allowed_classes": ["berserker"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 8): Causa 200% do seu Ataque Físico a todos os inimigos. Dano bônus vs 'Fratura'.",
                "mana_cost": 45,
                "effects": {"cooldown_turns": 8, "aoe": True, "damage_type": "physical", "damage_scale": 2.0,
                            "bonus_damage_vs_debuff": {"debuff": "Fratura", "bonus_mult": 0.50}}
            },
            "epica": {
                "description": "Épica (CD 7): Dano 250% (AoE). Dano bônus 75% vs 'Fratura'. 30% de chance de Atordoar (Stun) alvos.",
                "mana_cost": 45,
                "effects": {"cooldown_turns": 7, "aoe": True, "damage_type": "physical", "damage_scale": 2.5,
                            "bonus_damage_vs_debuff": {"debuff": "Fratura", "bonus_mult": 0.75},
                            "chance_on_hit": {"effect": "stun", "chance": 0.30, "duration_turns": 1}}
            },
            "lendaria": {
                "description": "Lendária (CD 7): Dano 300% (AoE). Dano bônus 100% vs 'Fratura'. 50% chance de Stun. Custa 10% HP (não Mana). CD reduz por morte.",
                "hp_cost_percent": 0.10, # Custa HP, não Mana
                "effects": {"cooldown_turns": 7, "aoe": True, "damage_type": "physical", "damage_scale": 3.0,
                            "bonus_damage_vs_debuff": {"debuff": "Fratura", "bonus_mult": 1.0},
                            "chance_on_hit": {"effect": "stun", "chance": 0.50, "duration_turns": 1},
                            "cooldown_reduction_on_kill": 1}
            }
        }
    },

    "evo_wrath_god_undying_rage": {
        "display_name": "Fúria Imortal do Deus da Ira",
        "type": "passive",
        "description": "A fúria de um deus o impede de morrer, desencadeando um poder inimaginável no limiar da morte.",
        "allowed_classes": ["berserker"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: Ao receber um golpe mortal, sobrevive com 1 HP e ganha +50% Ataque e +20% Roubo de Vida por 3 turnos (1/combate).",
                "effects": {"ignore_death_once": True,
                            "on_ignore_death_buff": {"duration_turns": 3, "buffs": {"attack_mult": 0.50, "lifesteal_flat": 0.20}}}
            },
            "epica": {
                "description": "Épica: Buff de 'Fúria Imortal' (+75% Atk, +30% Roubo de Vida) dura 4 turnos e concede Imunidade a Stun/Controle.",
                "effects": {"ignore_death_once": True,
                            "on_ignore_death_buff": {"duration_turns": 4, "buffs": {"attack_mult": 0.75, "lifesteal_flat": 0.30, "control_immune": True}}}
            },
            "lendaria": {
                "description": "Lendária: Buff (+100% Atk, +50% Roubo de Vida, Imune a Controle) dura 4 turnos. Se você matar um inimigo durante o buff, o efeito 'Ignore Death' é resetado.",
                "effects": {"ignore_death_once": True,
                            "on_ignore_death_buff": {"duration_turns": 4, "buffs": {"attack_mult": 1.00, "lifesteal_flat": 0.50, "control_immune": True}},
                            "reset_death_ignore_on_kill_during_buff": True}
            }
        }
    },
    # --- Novas Habilidades de Evolução do Caçador (Precisão) ---

    "evo_sniper_precision": {
        "display_name": "Precisão do Franco Atirador",
        "type": "passive",
        "description": "Seu treino de precisão aumenta seu Dano Crítico e sua Chance de Crítico.",
        "allowed_classes": ["cacador"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: +15% Dano Crítico, +5% Chance de Crítico.",
                "effects": {"stat_add_mult": {"crit_damage_mult": 0.15, "crit_chance_flat": 0.05}}
            },
            "epica": {
                "description": "Épica: +20% Dano Crítico, +8% Chance de Crítico, +10% Agilidade.",
                "effects": {"stat_add_mult": {"crit_damage_mult": 0.20, "crit_chance_flat": 0.08, "agility": 0.10}}
            },
            "lendaria": {
                "description": "Lendária: +30% Dano Crítico, +10% Chance de Crítico, +15% Agilidade. Seus ataques não podem ser 'Esquivados'.",
                "effects": {"stat_add_mult": {"crit_damage_mult": 0.30, "crit_chance_flat": 0.10, "agility": 0.15},
                            "cannot_be_dodged": True}
            }
        }
    },

    "evo_hawkeye_piercing_gaze": {
        "display_name": "Olhar Perfurante do Olho de Águia",
        "type": "passive",
        "description": "Seus tiros veem além da armadura inimiga, ignorando defesas.",
        "allowed_classes": ["cacador"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: Ganha permanentemente 15% de Penetração de Armadura.",
                "effects": {"stat_add_mult": {"armor_penetration": 0.15}}
            },
            "epica": {
                "description": "Épica: +25% Pen. Armadura. Causa 10% de dano bônus contra alvos com buffs de defesa ativos.",
                "effects": {"stat_add_mult": {"armor_penetration": 0.25},
                            "bonus_damage_vs_buff_type": {"buff_type": "defense", "bonus_mult": 0.10}}
            },
            "lendaria": {
                "description": "Lendária: +35% Pen. Armadura. Causa 20% de dano bônus vs buffs de defesa. Seus Críticos aplicam 'Exposto' (-15% DEF).",
                "effects": {"stat_add_mult": {"armor_penetration": 0.35},
                            "bonus_damage_vs_buff_type": {"buff_type": "defense", "bonus_mult": 0.20},
                            "on_crit_debuff": {"effect": "debuff_target", "stat": "defense", "value": -0.15, "duration_turns": 3}}
            }
        }
    },

    "evo_spectral_ricochet_shot": {
        "display_name": "Tiro Ricocheteante Espectral",
        "type": "active", # Ataque AoE
        "description": "Infunde suas flechas com poder espectral, permitindo que elas ricocheteiem.",
        "allowed_classes": ["cacador"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 4, Mana 25): Ataca o alvo (1.5x Dano) e ricocheteia para 1 outro inimigo (0.75x Dano).",
                "mana_cost": 25,
                "effects": {"cooldown_turns": 4, "damage_type": "physical", "damage_scale": 1.5,
                            "ricochet": {"hits": 1, "damage_scale": 0.75}}
            },
            "epica": {
                "description": "Épica (CD 3, Mana 25): Ataca o alvo (1.5x Dano) e ricocheteia para 2 outros inimigos (1.0x Dano).",
                "mana_cost": 25,
                "effects": {"cooldown_turns": 3, "damage_type": "physical", "damage_scale": 1.5,
                            "ricochet": {"hits": 2, "damage_scale": 1.0}}
            },
            "lendaria": {
                "description": "Lendária (CD 3, Mana 20): Ataca o alvo (1.5x Dano) e ricocheteia para 3 outros inimigos (1.0x Dano). Inimigos atingidos pelo ricochete recebem 'Lentidão' (-20% Agi).",
                "mana_cost": 20,
                "effects": {"cooldown_turns": 3, "damage_type": "physical", "damage_scale": 1.5,
                            "ricochet": {"hits": 3, "damage_scale": 1.0, 
                                         "debuff": {"stat": "agility", "value": -0.20, "duration_turns": 2}}}
            }
        }
    },

    "evo_horizon_endless_shot": {
        "display_name": "Tiro Infinito do Horizonte",
        "type": "active", # Ultimate
        "description": "Um tiro, um fim. Um disparo de longo alcance que perfura a própria realidade.",
        "allowed_classes": ["cacador"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 8, Mana 50): Causa 2.0x Dano. Este tiro tem 100% de Chance de Crítico e 100% de Penetração de Armadura.",
                "mana_cost": 50,
                "effects": {"cooldown_turns": 8, "damage_type": "physical", "damage_scale": 2.0,
                            "guaranteed_crit": True, "guaranteed_armor_pen": True}
            },
            "epica": {
                "description": "Épica (CD 7, Mana 45): Dano 2.5x (100% Crítico/Penetração). Se este tiro matar o alvo, o Cooldown é reduzido em 50%.",
                "mana_cost": 45,
                "effects": {"cooldown_turns": 7, "damage_type": "physical", "damage_scale": 2.5,
                            "guaranteed_crit": True, "guaranteed_armor_pen": True,
                            "cooldown_reduction_on_kill": 0.50} # 50%
            },
            "lendaria": {
                "description": "Lendária (CD 7, Mana 40): Dano 3.0x (100% Crítico/Penetração). Se este tiro matar o alvo, o Cooldown é resetado.",
                "mana_cost": 40,
                "effects": {"cooldown_turns": 7, "damage_type": "physical", "damage_scale": 3.0,
                            "guaranteed_crit": True, "guaranteed_armor_pen": True,
                            "cooldown_reduction_on_kill": 1.0} # 100%
            }
        }
    },
    # --- Novas Habilidades de Evolução do Monge (Ki/Equilíbrio) ---

    "evo_elemental_fist_attunement": {
        "display_name": "Sintonia do Punho Elemental",
        "type": "passive",
        "description": "Você canaliza Ki em seus golpes, fazendo com que seus ataques básicos causem dano mágico adicional.",
        "allowed_classes": ["monge"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: Seus ataques básicos causam 10% do seu Ataque como Dano Mágico (Ki) adicional.",
                "effects": {"on_hit_bonus_damage": {"damage_type": "magic", "scale": "attack", "value": 0.10}}
            },
            "epica": {
                "description": "Épica: Dano Mágico adicional aumentado para 15%. Ganha +10% Agilidade.",
                "effects": {"on_hit_bonus_damage": {"damage_type": "magic", "scale": "attack", "value": 0.15},
                            "stat_add_mult": {"agility": 0.10}}
            },
            "lendaria": {
                "description": "Lendária: Dano Mágico adicional 20%. +15% Agi. O dano de Ki reduz a Resist. Mágica do alvo em 10% por 3s (acumula 3x).",
                "effects": {"on_hit_bonus_damage": {"damage_type": "magic", "scale": "attack", "value": 0.20,
                                                    "debuff": {"stat": "magic_resist", "value": -0.10, "duration_turns": 3, "stack": 3}},
                            "stat_add_mult": {"agility": 0.15}}
            }
        }
    },

    "evo_ascendant_gait": {
        "display_name": "Passo do Ascendente",
        "type": "passive",
        "description": "Você atingiu a transcendência, movendo-se como o vento, tornando-se difícil de acertar.",
        "allowed_classes": ["monge"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: Aumenta permanentemente sua Chance de Evasão (Dodge) em 10% e sua Agilidade em 10%.",
                "effects": {"stat_add_mult": {"dodge_chance_flat": 0.10, "agility": 0.10}}
            },
            "epica": {
                "description": "Épica: +15% Evasão, +15% Agilidade.",
                "effects": {"stat_add_mult": {"dodge_chance_flat": 0.15, "agility": 0.15}}
            },
            "lendaria": {
                "description": "Lendária: +20% Evasão, +20% Agilidade. Após 'Evadir' com sucesso, seu próximo ataque causa 50% de dano bônus.",
                "effects": {"stat_add_mult": {"dodge_chance_flat": 0.20, "agility": 0.20},
                            "on_dodge_buff": {"effect": "next_hit_bonus_damage", "value": 0.50, "duration_turns": 1}}
            }
        }
    },

    "evo_divine_fist_strike": {
        "display_name": "Golpe do Punho Divino",
        "type": "active", # Ataque
        "description": "Seu Ki é tão puro que seus golpes causam dano sagrado, penetrando defesas.",
        "allowed_classes": ["monge"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 5, Mana 30): Causa 2.5x Dano Mágico (Ki) que ignora 50% da Resistência Mágica do alvo.",
                "mana_cost": 30,
                "effects": {"cooldown_turns": 5, "damage_type": "magic", "damage_scale": 2.5,
                            "magic_penetration": 0.50}
            },
            "epica": {
                "description": "Épica (CD 4, Mana 30): Dano 3.0x (Ki). Ignora 100% da Resistência Mágica.",
                "mana_cost": 30,
                "effects": {"cooldown_turns": 4, "damage_type": "magic", "damage_scale": 3.0,
                            "magic_penetration": 1.0}
            },
            "lendaria": {
                "description": "Lendária (CD 4, Mana 25): Dano 3.5x (Ki). Ignora 100% Res. Mágica. Recupera 25% do dano causado como HP.",
                "mana_cost": 25,
                "effects": {"cooldown_turns": 4, "damage_type": "magic", "damage_scale": 3.5,
                            "magic_penetration": 1.0,
                            "lifesteal_percent_of_damage": 0.25}
            }
        }
    },

    "evo_inner_dragon_unleashed": {
        "display_name": "Libertação do Dragão Interior",
        "type": "active", # Buff/Transformação
        "description": "Libera o dragão interior, o mestre supremo das artes marciais.",
        "allowed_classes": ["monge"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 8, Mana 50): Por 3 turnos, seus ataques básicos se tornam 'Sopro do Dragão' (1.2x Dano Mágico em Área/AoE).",
                "mana_cost": 50,
                "effects": {"cooldown_turns": 8, "duration_turns": 3,
                            "apply_self_buff": {"effect": "transform_attack", "damage_type": "magic", "damage_scale": 1.2, "aoe": True}}
            },
            "epica": {
                "description": "Épica (CD 7, Mana 45): Dura 4 turnos. 'Sopro do Dragão' (1.5x Dano) agora também aplica 'Queimadura de Ki' (Dano por turno).",
                "mana_cost": 45,
                "effects": {"cooldown_turns": 7, "duration_turns": 4,
                            "apply_self_buff": {"effect": "transform_attack", "damage_type": "magic", "damage_scale": 1.5, "aoe": True,
                                                "dot": {"damage_type": "magic", "scale": "attack", "value": 0.3, "duration_turns": 3}}}
            },
            "lendaria": {
                "description": "Lendária (CD 7, Mana 40): Dura 4 turnos. 'Sopro do Dragão' (1.5x Dano) tem 20% de Lifesteal. Você fica Imune a Controle (Stun/Slow) durante o efeito.",
                "mana_cost": 40,
                "effects": {"cooldown_turns": 7, "duration_turns": 4,
                            "apply_self_buff": {"effect": "transform_attack", "damage_type": "magic", "damage_scale": 1.5, "aoe": True, "lifesteal_flat": 0.20},
                            "control_immune": True}
            }
        }
    },

    "evo_fist_legend_balance": {
        "display_name": "Equilíbrio da Lenda do Punho",
        "type": "passive", # Aura de Grupo
        "description": "Um com o universo. Seus golpes são o próprio equilíbrio, inspirando aliados.",
        "allowed_classes": ["monge"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: Concede +10% Agilidade e +10% Tenacidade (Resist. Controle) para todo o grupo.",
                "effects": {"party_aura": {"stat_add_mult": {"agility": 0.10}, "tenacity_mult": 0.10}}
            },
            "epica": {
                "description": "Épica: Aura (+15% Agi, +15% Tenacidade). A aura agora também concede +10% de Redução de Cooldown (CDR) para o grupo.",
                "effects": {"party_aura": {"stat_add_mult": {"agility": 0.15}, "tenacity_mult": 0.15, "cooldown_reduction_mult": 0.10}}
            },
            "lendaria": {
                "description": "Lendária: Aura (+20% Agi, +20% Tenacidade, +15% CDR). O grupo agora recupera 1% do HP Máx por turno em combate.",
                "effects": {"party_aura": {"stat_add_mult": {"agility": 0.20}, "tenacity_mult": 0.20, "cooldown_reduction_mult": 0.15,
                                          "hp_regen_percent": 0.01}}
            }
        }
    },

    "evo_legend_phantom_wind": {
        "display_name": "Vento Fantasma da Lenda",
        "type": "passive",  # <--- Processada pelo stats.py
        "description": "Suas flechas nunca erram, guiadas pelo próprio vento, inspirando seus aliados.",
        "allowed_classes": ["cacador"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: Aura (+10% Iniciativa, +5% Crítico).",
                "effects": {
                    "party_aura": {
                        "stat_add_mult": {
                            "initiative": 0.10,      # "Agilidade" no sistema é Initiative
                            "crit_chance_flat": 5.0  # 5.0 = 5% de chance real
                        }
                    }
                }
            },
            "epica": {
                "description": "Épica: Aura (+15% Ini, +8% Crit). Ataque Duplo Pessoal (15%).",
                "effects": {
                    "party_aura": {
                        "stat_add_mult": {
                            "initiative": 0.15,
                            "crit_chance_flat": 8.0
                        }
                    },
                    # Nota: O engine precisa suportar 'double_attack_chance_flat' ou você ganha isso via Iniciativa
                    "stat_add_mult": {
                        "double_attack_chance_flat": 15.0 
                    }
                }
            },
            "lendaria": {
                "description": "Lendária: Aura (+20% Ini, +10% Crit). Ataques do grupo nunca erram (No Dodge).",
                "effects": {
                    "party_aura": {
                        "stat_add_mult": {
                            "initiative": 0.20,
                            "crit_chance_flat": 10.0
                        },
                        # Isso garante que NENHUM inimigo esquive dos ataques do grupo
                        "cannot_be_dodged": True
                    },
                    # Bônus pessoal de Ataque Duplo
                    "stat_add_mult": {
                        "double_attack_chance_flat": 25.0
                    }
                }
            }
        }
    },
    # --- Novas Habilidades de Evolução do Mago (Arcano) ---

    "evo_elementalist_power": {
        "display_name": "Poder do Elementalista",
        "type": "passive",
        "description": "Seu domínio sobre os elementos aumenta seu poder mágico bruto.",
        "allowed_classes": ["mago"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: +10% Dano Mágico, +5% Mana Máxima.",
                "effects": {"stat_add_mult": {"magic_attack": 0.10, "max_mp": 0.05}}
            },
            "epica": {
                "description": "Épica: +15% Dano Mágico, +10% Mana Máx. Magias têm 10% de chance de aplicar 'Queimadura' ou 'Congelamento'.",
                "effects": {"stat_add_mult": {"magic_attack": 0.15, "max_mp": 0.10},
                            "chance_on_magic_hit": {"effects": ["burn", "frost"], "chance": 0.10}}
            },
            "lendaria": {
                "description": "Lendária: +20% Dano Mágico, +15% Mana Máx. Chance de 20% (Queimadura/Gelo). Ganha +10% Penetração Mágica.",
                "effects": {"stat_add_mult": {"magic_attack": 0.20, "max_mp": 0.15, "magic_penetration": 0.10},
                            "chance_on_magic_hit": {"effects": ["burn", "frost"], "chance": 0.20}}
            }
        }
    },

    "evo_archmage_elemental_weave": {
        "display_name": "Trama Elemental do Arquimago",
        "type": "active", # Controle/Híbrida
        "description": "Dispara um raio de energia pura que se manifesta com um efeito elemental aleatório.",
        "allowed_classes": ["mago"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 6, Mana 30): Causa 1.5x Dano Mágico e aplica um efeito aleatório: Queimadura, Congelamento ou Choque (-M.Def).",
                "mana_cost": 30,
                "effects": {"cooldown_turns": 6, "damage_type": "magic", "damage_scale": 1.5,
                            "random_debuff": ["burn", "frost", "shock"]}
            },
            "epica": {
                "description": "Épica (CD 5, Mana 30): Dano 2.0x. Efeitos mais fortes. Agora pode causar 'Atordoamento' (Stun) de 1 turno.",
                "mana_cost": 30,
                "effects": {"cooldown_turns": 5, "damage_type": "magic", "damage_scale": 2.0,
                            "random_debuff": ["burn_strong", "frost_strong", "shock_strong", "stun_1_turn"]}
            },
            "lendaria": {
                "description": "Lendária (CD 4, Mana 25): Dano 2.5x. Você pode *escolher* o efeito (Fogo/Gelo/Raio/Atordoamento) em vez de ser aleatório.",
                "mana_cost": 25,
                "effects": {"cooldown_turns": 4, "damage_type": "magic", "damage_scale": 2.5,
                            "choose_debuff": ["burn_strong", "frost_strong", "shock_strong", "stun_1_turn"]}
            }
        }
    },

    "evo_battlemage_mana_shield": {
        "display_name": "Escudo de Mana do Mago de Batalha",
        "type": "active", # Defesa/Punição
        "description": "Cria uma barreira de pura mana que absorve dano e pune atacantes.",
        "allowed_classes": ["mago"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 7, Mana 20): Por 3 turnos, 30% de todo o dano recebido é absorvido pela Mana em vez do HP.",
                "mana_cost": 20,
                "effects": {"cooldown_turns": 7, "duration_turns": 3,
                            "apply_self_buff": {"effect": "mana_shield", "value": 0.30}} # 30% do dano vai para a mana
            },
            "epica": {
                "description": "Épica (CD 6, Mana 20): Dura 3 turnos. 50% do dano é absorvido pela Mana. Atacantes recebem 10% do dano de volta.",
                "mana_cost": 20,
                "effects": {"cooldown_turns": 6, "duration_turns": 3,
                            "apply_self_buff": {"effect": "mana_shield", "value": 0.50, "reflect_damage": 0.10}}
            },
            "lendaria": {
                "description": "Lendária (CD 6, Mana 20): Dura 4 turnos. 50% do dano vai para Mana. Atacantes têm 25% de chance de serem 'Atordoados'.",
                "mana_cost": 20,
                "effects": {"cooldown_turns": 6, "duration_turns": 4,
                            "apply_self_buff": {"effect": "mana_shield", "value": 0.50, "chance_to_stun_attacker": 0.25}}
            }
        } 
    },

    "evo_arcanist_overcharge": {
        "display_name": "Sobrecarga do Arcanista",
        "type": "active", # Buff/Transformação
        "description": "Transcende os limites da mana, usando a própria força vital para conjurar.",
        "allowed_classes": ["mago"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 9, Mana 0): Por 3 turnos, suas magias não custam Mana, mas custam 5% do seu HP Máx.",
                "mana_cost": 0,
                "effects": {"cooldown_turns": 9, "duration_turns": 3,
                            "apply_self_buff": {"effect": "no_mana_cost", "hp_cost_percent": 0.05}}
            },
            "epica": {
                "description": "Épica (CD 8, Mana 0): Dura 4 turnos. Magias custam 3% HP. Ganha +20% Dano Mágico durante o efeito.",
                "mana_cost": 0,
                "effects": {"cooldown_turns": 8, "duration_turns": 4,
                            "apply_self_buff": {"effect": "no_mana_cost", "hp_cost_percent": 0.03, "magic_attack_mult": 0.20}}
            },
            "lendaria": {
                "description": "Lendária (CD 8, Mana 0): Dura 4 turnos. Magias não custam Mana (sem custo de HP). Ganha +30% Dano Mágico e +25% Pen. Mágica.",
                "mana_cost": 0,
                "effects": {"cooldown_turns": 8, "duration_turns": 4,
                            "apply_self_buff": {"effect": "no_mana_cost", "hp_cost_percent": 0, 
                                                "magic_attack_mult": 0.30, "magic_penetration": 0.25}}
            }
        }
    },

    "evo_arcane_aspect_singularity": {
        "display_name": "Singularidade do Aspecto Arcano",
        "type": "passive",
        "description": "Você é a própria magia. Seu poder escala com sua reserva de mana.",
        "allowed_classes": ["mago"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: A cada 100 de Mana máxima que você possui, ganha +0.5% de Dano Mágico.",
                "effects": {"stat_scaling": {"source_stat": "max_mp", "target_stat": "magic_attack_mult", "ratio": 0.00005}} # 0.5% por 100
            },
            "epica": {
                "description": "Épica: +0.75% Dano Mágico por 100 Mana. A cada 500 de Mana gasta, ganha um 'Selo Arcano' (Acumula 5x, +5% Dano por selo).",
                "effects": {"stat_scaling": {"source_stat": "max_mp", "target_stat": "magic_attack_mult", "ratio": 0.000075},
                            "on_mana_spent": {"mana_threshold": 500, "effect": "gain_stack", "stack_name": "arcane_seal", "max_stacks": 5, "buff_per_stack": {"magic_attack_mult": 0.05}}}
            },
            "lendaria": {
                "description": "Lendária: +1% Dano Mágico por 100 Mana. 'Selos Arcanos' (Acumula 10x). Sua Regeneração de Mana em combate é dobrada.",
                "effects": {"stat_scaling": {"source_stat": "max_mp", "target_stat": "magic_attack_mult", "ratio": 0.0001},
                            "on_mana_spent": {"mana_threshold": 500, "effect": "gain_stack", "stack_name": "arcane_seal", "max_stacks": 10, "buff_per_stack": {"magic_attack_mult": 0.05}},
                            "stat_add_mult": {"mp_regen_mult": 1.0}} # 1.0 = +100%
            }
        }
    },
    # --- Novas Habilidades de Evolução do Bardo (Suporte/Controle) ---

    "evo_minstrel_healing_note": {
        "display_name": "Nota Curativa do Menestrel",
        "type": "support",  # <--- Ativa o sistema de grupo
        "description": "Uma melodia encantada que busca e restaura a vitalidade dos aliados.",
        "allowed_classes": ["bardo"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 2, Mana 10): Cura o grupo (150% M.Atk).",
                "mana_cost": 10,
                "effects": {
                    "cooldown_turns": 2,
                    "party_heal": {
                        "heal_type": "magic_attack",
                        "heal_scale": 1.5
                    }
                }
            },
            "epica": {
                "description": "Épica (CD 1, Mana 10): Cura (200% M.Atk) e Purifica (Visual).",
                "mana_cost": 10,
                "effects": {
                    "cooldown_turns": 1,
                    "party_heal": {
                        "heal_type": "magic_attack",
                        "heal_scale": 2.0
                    },
                    # Simula a chance de remover debuff garantindo o efeito visual
                    "party_buff": {
                        "buff_name": "Nota Purificadora",
                        "buff_value": "Remove Debuffs",
                        "duration": "Instantâneo"
                    }
                }
            },
            "lendaria": {
                "description": "Lendária (CD 0, Mana 10): Cura (250% M.Atk), Purifica e +10% DEF.",
                "mana_cost": 10,
                "effects": {
                    "cooldown_turns": 0, # Sem Cooldown! (Spammable se tiver mana)
                    "party_heal": {
                        "heal_type": "magic_attack",
                        "heal_scale": 2.5
                    },
                    # Combina a purificação e o buff de defesa
                    "party_buff": {
                        "buff_name": "Acorde Protetor",
                        "buff_value": "Purificar / +10% DEF",
                        "duration": "2 turnos"
                    }
                }
            }
        }
    },

    "evo_troubadour_hypnotic_lullaby": {
        "display_name": "Canção de Ninar Hipnótica",
        "type": "active", # Controle/Debuff
        "description": "Toca uma canção hipnótica que afeta todos os inimigos, com chance de 'Atordoar'.",
        "allowed_classes": ["bardo"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 6, Mana 25): 20% de chance de 'Atordoar' (Stun) todos os inimigos por 1 turno.",
                "mana_cost": 25,
                "effects": {"cooldown_turns": 6, "aoe": True, "target": "enemy",
                            "chance_on_hit": {"effect": "stun", "chance": 0.20, "duration_turns": 1}}
            },
            "epica": {
                "description": "Épica (CD 5, Mana 25): 30% de chance de Stun. Alvos atordoados recebem -15% DEF por 3 turnos.",
                "mana_cost": 25,
                "effects": {"cooldown_turns": 5, "aoe": True, "target": "enemy",
                            "chance_on_hit": {"effect": "stun", "chance": 0.30, "duration_turns": 1, 
                                              "debuff": {"stat": "defense", "value": -0.15, "duration_turns": 3}}}
            },
            "lendaria": {
                "description": "Lendária (CD 5, Mana 20): 40% de chance de Stun (Boss). Stun garantido vs. inimigos normais. Aplica -25% DEF.",
                "mana_cost": 20,
                "effects": {"cooldown_turns": 5, "aoe": True, "target": "enemy",
                            "chance_on_hit": {"effect": "stun", "chance": 0.40, "duration_turns": 1, "guaranteed_vs_minion": True,
                                              "debuff": {"stat": "defense", "value": -0.25, "duration_turns": 3}}}
            }
        }
    },

    "evo_maestro_barrier_sonata": {
        "display_name": "Sonata da Barreira do Mestre",
        "type": "support", # <--- Envia para o party_engine
        "description": "Cria uma barreira sonora que protege e restaura os aliados.",
        "allowed_classes": ["bardo"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 7, Mana 35): Escudo de 100% M.Atk (Cura Imediata) e Proteção Visual.",
                "mana_cost": 35,
                "effects": {
                    "cooldown_turns": 7,
                    # Simula o escudo curando o dano que o time já levou
                    "party_heal": {
                        "heal_type": "magic_attack",
                        "heal_scale": 1.0
                    },
                    # Aviso visual da proteção
                    "party_buff": {
                        "buff_name": "Barreira Sonora",
                        "buff_value": "Escudo Ativo",
                        "duration": "3 turnos"
                    }
                }
            },
            "epica": {
                "description": "Épica (CD 6, Mana 35): Escudo de 150% M.Atk. Aumenta cura recebida (Visual).",
                "mana_cost": 35,
                "effects": {
                    "cooldown_turns": 6,
                    "party_heal": {
                        "heal_type": "magic_attack",
                        "heal_scale": 1.5
                    },
                    "party_buff": {
                        "buff_name": "Barreira Ressonante",
                        "buff_value": "Escudo / +10% Cura Recebida",
                        "duration": "3 turnos"
                    }
                }
            },
            "lendaria": {
                "description": "Lendária (CD 6, Mana 30): Escudo de 200% M.Atk e Cura Residual.",
                "mana_cost": 30,
                "effects": {
                    "cooldown_turns": 6,
                    "party_heal": {
                        "heal_type": "magic_attack",
                        "heal_scale": 2.0 # Valor alto para simular o escudo + cura ao quebrar
                    },
                    "party_buff": {
                        "buff_name": "Cúpula do Maestro",
                        "buff_value": "Escudo Max / Cura ao Quebrar",
                        "duration": "3 turnos"
                    }
                }
            }
        }
    },

    "evo_harmonist_grand_overture": {
        "display_name": "Grande Abertura do Harmonista",
        "type": "support",  # <--- Ativa o sistema de grupo
        "description": "A obra-prima do Harmonista. Eleva o potencial de todos os aliados ao máximo.",
        "allowed_classes": ["bardo"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 9, Mana 50): +15% Status Gerais (3 turnos).",
                "mana_cost": 50,
                "effects": {
                    "cooldown_turns": 9,
                    "party_buff": {
                        "buff_name": "Grande Abertura",
                        "buff_value": "+15% ATK/M.ATK/AGI",
                        "duration": "3 turnos"
                    }
                }
            },
            "epica": {
                "description": "Épica (CD 8, Mana 45): +20% Status Gerais e +15% CDR (4 turnos).",
                "mana_cost": 45,
                "effects": {
                    "cooldown_turns": 8,
                    "party_buff": {
                        "buff_name": "Concerto Épico",
                        "buff_value": "+20% Status / +15% CDR",
                        "duration": "4 turnos"
                    }
                }
            },
            "lendaria": {
                "description": "Lendária (CD 8, Mana 40): +25% Status, CDR e Imunidade a Controle.",
                "mana_cost": 40,
                "effects": {
                    "cooldown_turns": 8,
                    "party_buff": {
                        "buff_name": "Obra-Prima Lendária",
                        "buff_value": "+25% Status / Imune a CC",
                        "duration": "4 turnos"
                    }
                }
            }
        }
    },

    "evo_aspect_primordial_symphony": {
        "display_name": "Sinfonia Primordial do Aspecto",
        "type": "passive",  # <--- Aura processada pelo stats.py
        "description": "Sua música é a própria realidade, regenerando e fortalecendo aliados passivamente.",
        "allowed_classes": ["bardo"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: Aura (+5% M.Atk/DEF). Reg: 0.5% HP/MP por turno.",
                "effects": {
                    "party_aura": {
                        "stat_add_mult": {
                            "magic_attack": 0.05,
                            "defense": 0.05
                        },
                        "hp_regen_percent": 0.005,
                        "mp_regen_percent": 0.005
                    }
                }
            },
            "epica": {
                "description": "Épica: Aura (+8% M.Atk/DEF). Reg: 1.0% HP/MP por turno.",
                "effects": {
                    "party_aura": {
                        "stat_add_mult": {
                            "magic_attack": 0.08,
                            "defense": 0.08
                        },
                        "hp_regen_percent": 0.01,
                        "mp_regen_percent": 0.01
                    }
                }
            },
            "lendaria": {
                "description": "Lendária: Aura (+12% M.Atk/DEF). Reg: 1.5% HP/MP. Potência de Buffs +20%.",
                "effects": {
                    "party_aura": {
                        "stat_add_mult": {
                            "magic_attack": 0.12,
                            "defense": 0.12
                        },
                        "hp_regen_percent": 0.015,
                        "mp_regen_percent": 0.015
                    },
                    # Simulamos "Potência de Buff" aumentando o atributo base do Bardo
                    # Isso fará as curas dele ficarem 20% mais fortes naturalmente
                    "stat_add_mult": {
                        "magic_attack": 0.20
                    }
                }
            }
        }
    },
    # --- Novas Habilidades de Evolução do Assassino (Furtividade/Crítico) ---

    "evo_shadow_thief_ambush": {
        "display_name": "Emboscada do Ladrão de Sombras",
        "type": "passive",
        "description": "Especialista em ataques de oportunidade. Seu primeiro ataque em combate causa dano massivo.",
        "allowed_classes": ["assassino"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: O primeiro ataque em cada combate causa +50% de dano e tem +25% de Chance de Crítico.",
                "effects": {"first_hit_bonus": {"damage_mult": 0.50, "crit_chance_flat": 0.25}}
            },
            "epica": {
                "description": "Épica: Primeiro ataque causa +75% de dano, +50% Chance de Crítico e ignora 50% da DEF.",
                "effects": {"first_hit_bonus": {"damage_mult": 0.75, "crit_chance_flat": 0.50, "armor_penetration": 0.50}}
            },
            "lendaria": {
                "description": "Lendária: Primeiro ataque causa +100% de dano, tem 100% de Chance de Crítico e ignora 100% da DEF.",
                "effects": {"first_hit_bonus": {"damage_mult": 1.0, "crit_chance_flat": 1.0, "armor_penetration": 1.0}}
            }
        }
    },

    "evo_ninja_poison_arts": {
        "display_name": "Artes Venenosas do Ninja",
        "type": "passive",
        "description": "Mestre de venenos e ferramentas táticas, seus ataques aplicam toxinas letais.",
        "allowed_classes": ["assassino"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: 20% de chance de aplicar 'Veneno Letal' (10% Atk por 3 turnos).",
                "effects": {"chance_on_hit": {"effect": "dot", "chance": 0.20, "damage_type": "physical", "scale": "attack", "value": 0.10, "duration_turns": 3}}
            },
            "epica": {
                "description": "Épica: 30% chance 'Veneno Letal' (15% Atk por 3 turnos). O veneno agora acumula 2x.",
                "effects": {"chance_on_hit": {"effect": "dot", "chance": 0.30, "damage_type": "physical", "scale": "attack", "value": 0.15, "duration_turns": 3, "stack": 2}}
            },
            "lendaria": {
                "description": "Lendária: 40% chance 'Veneno Letal' (20% Atk por 3 turnos). Acumula 3x. Alvos envenenados recebem -15% DEF.",
                "effects": {"chance_on_hit": {"effect": "dot", "chance": 0.40, "damage_type": "physical", "scale": "attack", "value": 0.20, "duration_turns": 3, "stack": 3,
                                              "debuff": {"stat": "defense", "value": -0.15, "duration_turns": 3}}}
            }
        }
    },

    "evo_blademaster_focus": {
        "display_name": "Foco do Mestre das Lâminas",
        "type": "passive",
        "description": "Um duelista mortal focado em ataques críticos e precisão.",
        "allowed_classes": ["assassino"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: +10% Chance de Crítico, +25% Dano Crítico.",
                "effects": {"stat_add_mult": {"crit_chance_flat": 0.10, "crit_damage_mult": 0.25}}
            },
            "epica": {
                "description": "Épica: +15% Chance de Crítico, +40% Dano Crítico. Ataques críticos ganham +15% Pen. Armadura.",
                "effects": {"stat_add_mult": {"crit_chance_flat": 0.15, "crit_damage_mult": 0.40},
                            "on_crit_buff": {"effect": "armor_penetration", "value": 0.15}}
            },
            "lendaria": {
                "description": "Lendária: +20% Chance de Crítico, +60% Dano Crítico. Críticos ganham +30% Pen. Armadura. Críticos não podem ser 'Esquivados'.",
                "effects": {"stat_add_mult": {"crit_chance_flat": 0.20, "crit_damage_mult": 0.60},
                            "on_crit_buff": {"effect": "armor_penetration", "value": 0.30, "cannot_be_dodged": True}}
            }
        }
    },

    "evo_reaper_mark_of_death": {
        "display_name": "Marca do Ceifador",
        "type": "active", # Execução
        "description": "Canaliza a energia da morte, marcando um alvo para o abate. Garante que nenhum alvo escape.",
        "allowed_classes": ["assassino"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 8, Mana 40): Causa 2.5x Dano. Causa 50% de dano bônus contra alvos com menos de 25% HP.",
                "mana_cost": 40,
                "effects": {"cooldown_turns": 8, "damage_type": "physical", "damage_scale": 2.5,
                            "bonus_damage_vs_low_hp": {"hp_threshold": 0.25, "bonus_mult": 0.50}}
            },
            "epica": {
                "description": "Épica (CD 7, Mana 35): Dano 2.8x. Causa 100% de dano bônus contra alvos com menos de 35% HP.",
                "mana_cost": 35,
                "effects": {"cooldown_turns": 7, "damage_type": "physical", "damage_scale": 2.8,
                            "bonus_damage_vs_low_hp": {"hp_threshold": 0.35, "bonus_mult": 1.0}}
            },
            "lendaria": {
                "description": "Lendária (CD 6, Mana 30): Dano 3.0x. Causa 150% de dano bônus contra alvos com menos de 50% HP. Se esta skill matar o alvo, o Cooldown é resetado.",
                "mana_cost": 30,
                "effects": {"cooldown_turns": 6, "damage_type": "physical", "damage_scale": 3.0,
                            "bonus_damage_vs_low_hp": {"hp_threshold": 0.50, "bonus_mult": 1.50},
                            "cooldown_reduction_on_kill": 1.0} # 1.0 = Reseta
            }
        }
    },

    "evo_night_aspect_invisibility": {
        "display_name": "Aspecto da Noite Eterna",
        "type": "passive",
        "description": "Tornou-se um com o manto da noite. Abates o fazem desaparecer.",
        "allowed_classes": ["assassino"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: Ao matar um inimigo, você ganha 'Invisibilidade' por 1 turno (impossível de ser alvo).",
                "effects": {"on_kill_buff": {"effect": "invisibility", "duration_turns": 1}}
            },
            "epica": {
                "description": "Épica: Ao matar, ganha 'Invisibilidade' por 1 turno. O primeiro ataque saindo da 'Invisibilidade' é um Crítico Garantido.",
                "effects": {"on_kill_buff": {"effect": "invisibility", "duration_turns": 1,
                                              "on_exit_buff": {"effect": "guaranteed_crit", "duration_turns": 1}}}
            },
            "lendaria": {
                "description": "Lendária: Ao matar, ganha 'Invisibilidade' (2 turnos). Sair da 'Invisibilidade' concede +50% Atk e +50% Crítico Dano por 3 turnos.",
                "effects": {"on_kill_buff": {"effect": "invisibility", "duration_turns": 2,
                                              "on_exit_buff": {"effect": "multi_stat_buff", "duration_turns": 3,
                                                               "buffs": {"attack_mult": 0.50, "crit_damage_mult": 0.50}}}}
            }
        }
    },
    # --- Novas Habilidades de Evolução do Samurai (Bushido/Lâmina) ---

    "evo_ronin_wanderers_focus": {
        "display_name": "Foco do Errante (Ronin)",
        "type": "passive",
        "description": "Focado em golpes rápidos e sobrevivência, você ataca com agilidade e se recupera no calor da batalha.",
        "allowed_classes": ["samurai"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: +10% Agilidade, +5% Chance de Crítico.",
                "effects": {"stat_add_mult": {"agility": 0.10, "crit_chance_flat": 0.05}}
            },
            "epica": {
                "description": "Épica: +15% Agi, +8% Crítico, +5% Roubo de Vida (Lifesteal).",
                "effects": {"stat_add_mult": {"agility": 0.15, "crit_chance_flat": 0.08, "lifesteal_flat": 0.05}}
            },
            "lendaria": {
                "description": "Lendária: +20% Agi, +10% Crítico, +10% Roubo de Vida. Ganha +10% de Ataque Físico.",
                "effects": {"stat_add_mult": {"agility": 0.20, "crit_chance_flat": 0.10, "lifesteal_flat": 0.10, "attack": 0.10}}
            }
        }
    },

    "evo_kenshi_perfect_parry": {
        "display_name": "Aparar Perfeito (Kenshi)",
        "type": "active", # Defesa/Postura
        "description": "Domina a técnica de aparar. Assume uma postura que, se atacado, anula o dano e contra-ataca.",
        "allowed_classes": ["samurai"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 6, Mana 10): Postura (1 turno). Se atacado fisicamente, anula o dano e contra-ataca (150% Atk).",
                "mana_cost": 10,
                "effects": {"cooldown_turns": 6, "duration_turns": 1,
                            "stance_parry": {"damage_scale": 1.5}}
            },
            "epica": {
                "description": "Épica (CD 5, Mana 10): Postura (2 turnos). Contra-ataque (200% Atk).",
                "mana_cost": 10,
                "effects": {"cooldown_turns": 5, "duration_turns": 2,
                            "stance_parry": {"damage_scale": 2.0}}
            },
            "lendaria": {
                "description": "Lendária (CD 4, Mana 10): Postura (2 turnos). Contra-ataque (250% Atk) é Crítico Garantido.",
                "mana_cost": 10,
                "effects": {"cooldown_turns": 4, "duration_turns": 2,
                            "stance_parry": {"damage_scale": 2.5, "guaranteed_crit": True}}
            }
        }
    },

    "evo_shogun_banner_of_war": {
        "display_name": "Estandarte de Guerra (Shogun)",
        "type": "support",  # <--- Essencial para ativar a lógica de grupo
        "description": "Ergue um estandarte de comando, inspirando aliados com poder ofensivo e defensivo.",
        "allowed_classes": ["samurai"], 
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 8, Mana 40): +15% ATK/DEF (3 turnos).",
                "mana_cost": 40,
                "effects": {
                    "cooldown_turns": 8,
                    "party_buff": {
                        "buff_name": "Estandarte de Guerra",
                        "buff_value": "+15% ATK / +15% DEF",
                        "duration": "3 turnos"
                    }
                }
            },
            "epica": {
                "description": "Épica (CD 7, Mana 40): +20% ATK/DEF (4 turnos).",
                "mana_cost": 40,
                "effects": {
                    "cooldown_turns": 7,
                    "party_buff": {
                        "buff_name": "Comando do General",
                        "buff_value": "+20% ATK / +20% DEF",
                        "duration": "4 turnos"
                    }
                }
            },
            "lendaria": {
                "description": "Lendária (CD 7, Mana 35): +25% ATK/DEF e +10% Crítico (4 turnos).",
                "mana_cost": 35,
                "effects": {
                    "cooldown_turns": 7,
                    "party_buff": {
                        "buff_name": "Glória do Shogun",
                        # Agrupamos os status para ficar legível no log
                        "buff_value": "+25% ATK/DEF / +10% CRIT",
                        "duration": "4 turnos"
                    }
                }
            }
        }
    },

    "evo_bushido_final_cut": {
        "display_name": "Corte Final (Bushido)",
        "type": "active", # Ataque/Ultimate
        "description": "A perfeição do bushido. Um ataque de precisão final que não pode ser evitado.",
        "allowed_classes": ["samurai"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 8, Mana 50): Causa 3.0x Dano. Ignora 50% DEF. Não pode ser 'Esquivado'.",
                "mana_cost": 50,
                "effects": {"cooldown_turns": 8, "damage_type": "physical", "damage_scale": 3.0,
                            "armor_penetration": 0.50, "cannot_be_dodged": True}
            },
            "epica": {
                "description": "Épica (CD 7, Mana 45): Dano 3.5x. Ignora 100% DEF. Não pode ser 'Esquivado'.",
                "mana_cost": 45,
                "effects": {"cooldown_turns": 7, "damage_type": "physical", "damage_scale": 3.5,
                            "armor_penetration": 1.0, "cannot_be_dodged": True}
            },
            "lendaria": {
                "description": "Lendária (CD 7, Mana 40): Dano 4.0x. Ignora 100% DEF. Não pode ser 'Esquivado' ou 'Bloqueado'. Se matar o alvo, recupera 30% HP/MP.",
                "mana_cost": 40,
                "effects": {"cooldown_turns": 7, "damage_type": "physical", "damage_scale": 4.0,
                            "armor_penetration": 1.0, "cannot_be_dodged": True, "cannot_be_blocked": True,
                            "on_kill_recover": {"hp_percent": 0.30, "mp_percent": 0.30}}
            }
        }
    },

    "evo_blade_aspect_presence": {
        "display_name": "Presença do Aspecto da Lâmina",
        "type": "passive",  # <--- Processado pelo stats.py
        "description": "Sua lâmina manifesta uma aura que afia os golpes de todos os aliados.",
        "allowed_classes": ["samurai"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: Aura de +10% Chance de Crítico para o grupo.",
                "effects": {
                    "party_aura": {
                        "stat_add_mult": {
                            # Use 10.0 para 10% (escala 0-100)
                            "crit_chance_flat": 10.0
                        }
                    }
                }
            },
            "epica": {
                "description": "Épica: Aura de +15% Chance e +15% Dano Crítico.",
                "effects": {
                    "party_aura": {
                        "stat_add_mult": {
                            "crit_chance_flat": 15.0,
                            # Multiplicadores de dano geralmente são decimais (0.15 = +15%)
                            "crit_damage_mult": 0.15
                        }
                    }
                }
            },
            "lendaria": {
                "description": "Lendária: Aura de +20% Chance, +25% Dano Crítico e +10% Pen. Armadura.",
                "effects": {
                    "party_aura": {
                        "stat_add_mult": {
                            "crit_chance_flat": 20.0,
                            "crit_damage_mult": 0.25,
                            "armor_penetration": 0.10
                        }
                    }
                }
            }
        }
    },
    # --- Novas Habilidades de Evolução do Curandeiro (Suporte/Cura) ---

    "evo_cleric_divine_light": {
        "display_name": "Luz Divina (Clérigo)",
        "type": "active", # Suporte/Cura
        "description": "Cura um alvo com o toque divino (baseado no Atk Mágico) e remove debuffs.",
        "allowed_classes": ["curandeiro"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 2, Mana 15): Cura um alvo (200% M.Atk).",
                "mana_cost": 15,
                "effects": {"cooldown_turns": 2, "target": "ally", "heal_type": "magic_attack", "heal_scale": 2.0}
            },
            "epica": {
                "description": "Épica (CD 2, Mana 15): Cura (250% M.Atk). Remove 1 debuff.",
                "mana_cost": 15,
                "effects": {"cooldown_turns": 2, "target": "ally", "heal_type": "magic_attack", "heal_scale": 2.5,
                            "remove_debuffs": 1}
            },
            "lendaria": {
                "description": "Lendária (CD 1, Mana 15): Cura (300% M.Atk). Remove 2 debuffs. Concede +15% Defesa ao alvo por 2 turnos.",
                "mana_cost": 15,
                "effects": {"cooldown_turns": 1, "target": "ally", "heal_type": "magic_attack", "heal_scale": 3.0,
                            "remove_debuffs": 2,
                            "on_heal_buff": {"stat": "defense", "value": 0.15, "duration_turns": 2}}
            }
        }
    },

    "evo_priest_holy_ground": {
        "display_name": "Solo Sagrado (Sacerdote)",
        "type": "active", # Suporte/Cura AoE
        "description": "Consagra o chão, curando todos os aliados por turno (HoT).",
        "allowed_classes": ["curandeiro"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 7, Mana 30): Cura o grupo (40% M.Atk) por 3 turnos.",
                "mana_cost": 30,
                "effects": {"cooldown_turns": 7, "duration_turns": 3,
                            "party_buff": {"effect": "hot", "heal_type": "magic_attack", "heal_scale": 0.40}}
            },
            "epica": {
                "description": "Épica (CD 6, Mana 30): Cura o grupo (60% M.Atk) por 3 turnos.",
                "mana_cost": 30,
                "effects": {"cooldown_turns": 6, "duration_turns": 3,
                            "party_buff": {"effect": "hot", "heal_type": "magic_attack", "heal_scale": 0.60}}
            },
            "lendaria": {
                "description": "Lendária (CD 6, Mana 25): Cura o grupo (75% M.Atk) por 4 turnos. Também purifica 1 debuff por turno.",
                "mana_cost": 25,
                "effects": {"cooldown_turns": 6, "duration_turns": 4,
                            "party_buff": {"effect": "hot", "heal_type": "magic_attack", "heal_scale": 0.75,
                                           "remove_debuffs_per_turn": 1}}
            }
        }
    },

    "evo_hierophant_divine_aegis": {
        "display_name": "Égide Divina (Hierofante)",
        "type": "active", # Suporte/Escudo
        "description": "Invoca um escudo de luz que absorve dano (baseado no HP Máx do Curandeiro).",
        "allowed_classes": ["curandeiro"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 7, Mana 35): Escuda o grupo por 15% do HP Máx do Curandeiro por 3 turnos.",
                "mana_cost": 35,
                "effects": {"cooldown_turns": 7, "duration_turns": 3,
                            "party_buff": {"effect": "shield", "shield_type": "max_hp", "shield_scale": 0.15}}
            },
            "epica": {
                "description": "Épica (CD 6, Mana 35): Escudo (20% HP Máx) por 3 turnos. Enquanto o escudo dura, aumenta a cura recebida em 15%.",
                "mana_cost": 35,
                "effects": {"cooldown_turns": 6, "duration_turns": 3,
                            "party_buff": {"effect": "shield", "shield_type": "max_hp", "shield_scale": 0.20,
                                           "buffs": {"heal_potency_mult": 0.15}}}
            },
            "lendaria": {
                "description": "Lendária (CD 6, Mana 30): Escudo (25% HP Máx) por 4 turnos. Aumenta cura recebida em 20%. Metade do dano absorvido é devolvido como Dano Sagrado.",
                "mana_cost": 30,
                "effects": {"cooldown_turns": 6, "duration_turns": 4,
                            "party_buff": {"effect": "shield", "shield_type": "max_hp", "shield_scale": 0.25,
                                           "buffs": {"heal_potency_mult": 0.20},
                                           "reflect_absorbed_damage": {"reflect_type": "magic", "value": 0.50}}}
            }
        }
    },

    "evo_celestial_oracle_preservation": {
        "display_name": "Preservação (Oráculo Celestial)",
        "type": "active", # Suporte/Ultimate
        "description": "Prevê e anula o destino. A 'Ultimate' de cura.",
        "allowed_classes": ["curandeiro"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 9, Mana 60): Cura 50% do HP Máx de TODOS os aliados. Remove todos os debuffs.",
                "mana_cost": 60,
                "effects": {"cooldown_turns": 9, "target": "party", "heal_type": "percent_max_hp", "heal_scale": 0.50,
                            "remove_debuffs": "all"}
            },
            "epica": {
                "description": "Épica (CD 8, Mana 50): Cura 60% HP. Remove todos os debuffs. Concede 'Imunidade a Debuff' por 2 turnos.",
                "mana_cost": 50,
                "effects": {"cooldown_turns": 8, "target": "party", "heal_type": "percent_max_hp", "heal_scale": 0.60,
                            "remove_debuffs": "all",
                            "party_buff": {"effect": "debuff_immune", "duration_turns": 2}}
            },
            "lendaria": {
                "description": "Lendária (CD 8, Mana 50): Cura 75% HP. Remove debuffs. Concede 'Imunidade a Debuff' (3t). Se curar um aliado abaixo de 10% HP, ele fica 'Invulnerável' por 1 turno.",
                "mana_cost": 50,
                "effects": {"cooldown_turns": 8, "target": "party", "heal_type": "percent_max_hp", "heal_scale": 0.75,
                            "remove_debuffs": "all",
                            "party_buff": {"effect": "debuff_immune", "duration_turns": 3},
                            "on_heal_low_hp_buff": {"hp_threshold": 0.10, "effect": "invulnerable", "duration_turns": 1}}
            }
        }
    },

    "evo_healing_legend_miracle": {
        "display_name": "Milagre (Lenda da Cura)",
        "type": "passive", # Passiva/Aura
        "description": "A própria luz da esperança. Sua presença pode reverter a morte.",
        "allowed_classes": ["curandeiro"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: Concede +10% M.Atk e +10% HP Máx (Aura de Grupo).",
                "effects": {"party_aura": {"stat_add_mult": {"magic_attack": 0.10, "max_hp": 0.10}}}
            },
            "epica": {
                "description": "Épica: Aura (+15% M.Atk, +15% HP). Aumenta a potência de cura do Curandeiro em 20%.",
                "effects": {"party_aura": {"stat_add_mult": {"magic_attack": 0.15, "max_hp": 0.15}},
                            "heal_potency_mult": 0.20} # Apenas no Curandeiro
            },
            "lendaria": {
                "description": "Lendária: Aura (+15% M.Atk, +15% HP). Potência de cura +30%. Uma vez por combate, o primeiro aliado a morrer é 'Ressuscitado' com 30% HP.",
                "effects": {"party_aura": {"stat_add_mult": {"magic_attack": 0.15, "max_hp": 0.15}},
                            "heal_potency_mult": 0.30,
                            "party_revive_once": {"revive_hp_percent": 0.30}}
            }
        }
    },
    # --- HABILIDADES DE EVENTO (Guerreiro) ---

    "passive_bulwark": {
        "display_name": "Baluarte", "type": "passive", 
        "description": "Uma skill passiva de defesa.", 
        "allowed_classes": ["guerreiro"], # Trava de classe mantida!
        "rarity_effects": {
            "comum": {
                "description": "Comum: Aumenta a Defesa base em 5%.",
                "effects": {"stat_add_mult": {"defense": 0.05}}
            },
            "epica": {
                "description": "Épica: Aumenta a Defesa base em 10% e HP Máx em 5%.",
                "effects": {"stat_add_mult": {"defense": 0.10, "max_hp": 0.05}}
            },
            "lendaria": {
                "description": "Lendária: Defesa +15%, HP Máx +8%. Ganha +5% Resist. Física.",
                "effects": {"stat_add_mult": {"defense": 0.15, "max_hp": 0.08},
                            "resistance_mult": {"physical": 0.05}}
            }
        }
    }, 
    "guerreiro_redemoinho_aco": {
        "display_name": "Redemoinho de Aço", "type": "active", 
        "description": "Um ataque giratório que atinge múltiplos alvos.", 
        "allowed_classes": ["guerreiro"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 3, Mana 20): Dano 1.1x (AoE).",
                "mana_cost": 20, 
                "effects": {"cooldown_turns": 3, "damage_multiplier": 1.1, "aoe": True}
            },
            "epica": {
                "description": "Épica (CD 3, Mana 18): Dano 1.3x (AoE). 15% de chance de aplicar 'Sangramento'.",
                "mana_cost": 18, 
                "effects": {"cooldown_turns": 3, "damage_multiplier": 1.3, "aoe": True,
                            "chance_on_hit": {"effect": "dot", "chance": 0.15, "value": 0.1, "duration_turns": 2}}
            },
            "lendaria": {
                "description": "Lendária (CD 2, Mana 15): Dano 1.5x (AoE). 30% de chance de 'Sangramento'.",
                "mana_cost": 15, 
                "effects": {"cooldown_turns": 2, "damage_multiplier": 1.5, "aoe": True,
                            "chance_on_hit": {"effect": "dot", "chance": 0.30, "value": 0.1, "duration_turns": 3}}
            }
        }
    }, 
    # evento portal 
    "guerreiro_bencao_sagrada": {
        "display_name": "Bênção Sagrada",
        "type": "support", # <--- Ativa o sistema de grupo
        "description": "Invoca poder divino para curar os ferimentos dos aliados.",
        "allowed_classes": ["guerreiro"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 5, Mana 15): Cura 20% do HP Máx (Party).",
                "mana_cost": 15,
                "effects": {
                    "cooldown_turns": 5,
                    "party_heal": {
                        "amount_percent_max_hp": 0.20
                    }
                }
            },
            "epica": {
                "description": "Épica (CD 4, Mana 15): Cura 25% do HP Máx (Party).",
                "mana_cost": 15,
                "effects": {
                    "cooldown_turns": 4,
                    "party_heal": {
                        "amount_percent_max_hp": 0.25
                    }
                }
            },
            "lendaria": {
                "description": "Lendária (CD 4, Mana 10): Cura 30% do HP Máx e remove debuffs.",
                "mana_cost": 10,
                "effects": {
                    "cooldown_turns": 4,
                    "party_heal": {
                        "amount_percent_max_hp": 0.30
                    },
                    # Adiciona o aviso visual da purificação
                    "party_buff": {
                        "buff_name": "Purificação Divina",
                        "buff_value": "Remove Debuffs",
                        "duration": "Instantâneo"
                    }
                }
            }
        }
    },

    "guerreiro_colossal_defense": {  
        "display_name": "Defesa Colossal", "type": "passive", 
        "description": "Reduz o dano recebido permanentemente.",
        "allowed_classes": ["guerreiro"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: Reduz o dano recebido em 5%.",
                "effects": {"damage_reduction_mult": 0.05}
            },
            "epica": {
                "description": "Épica: Reduz o dano recebido em 8%.",
                "effects": {"damage_reduction_mult": 0.08}
            },
            "lendaria": {
                "description": "Lendária: Reduz o dano recebido em 12%. Concede +5% HP Máx.",
                "effects": {"damage_reduction_mult": 0.12, "stat_add_mult": {"max_hp": 0.05}}
            }
        }
    }, 
    
    # --- HABILIDADES DE EVENTO (Berserker) ---

    "passive_unstoppable": {
        "display_name": "Inabalável", "type": "passive", 
        "description": "A sua fúria torna-o resistente a efeitos de controlo.", 
        "allowed_classes": ["berserker"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: Aumenta a Tenacidade (resist. a Stun/Slow) em 20%.",
                "effects": {"tenacity_mult": 0.20}
            },
            "epica": {
                "description": "Épica: Tenacidade aumentada para 35%.",
                "effects": {"tenacity_mult": 0.35}
            },
            "lendaria": {
                "description": "Lendária: Tenacidade aumentada para 50%. Ao resistir a um Stun, ganha +20% ATK por 3 turnos.",
                "effects": {"tenacity_mult": 0.50,
                            "on_resist_buff": {"resist_type": "stun", "buff": {"stat": "attack", "value": 0.20, "duration_turns": 3}}}
            }
        }
    },
    "berserker_investida_inquebravel": {
        "display_name": "Investida Inquebrável", "type": "active", 
        "description": "Avança, ignorando parte do dano no próximo turno.", 
        "allowed_classes": ["berserker"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 4, Mana 15): Reduz 40% do dano recebido por 1 turno.",
                "mana_cost": 15, 
                "effects": {"cooldown_turns": 4, "self_buff": {"effect": "damage_reduction", "value": 0.4, "duration_turns": 1}}
            },
            "epica": {
                "description": "Épica (CD 4, Mana 10): Reduz 50% do dano (1t). Causa 50% Atk como dano.",
                "mana_cost": 10, 
                "effects": {"cooldown_turns": 4, "self_buff": {"effect": "damage_reduction", "value": 0.5, "duration_turns": 1},
                            "damage_type": "physical", "damage_scale": 0.5}
            },
            "lendaria": {
                "description": "Lendária (CD 3, Mana 10): Reduz 60% do dano (1t). Causa 100% Atk como dano.",
                "mana_cost": 10, 
                "effects": {"cooldown_turns": 3, "self_buff": {"effect": "damage_reduction", "value": 0.6, "duration_turns": 1},
                            "damage_type": "physical", "damage_scale": 1.0}
            }
        }
    },
    # evento portal
    "berserker_ultimo_recurso": {
        "display_name": "Último Recurso", "type": "passive", 
        "description": "O seu dano aumenta massivamente quando a sua vida está baixa.", 
        "allowed_classes": ["berserker"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: Ganha +20% Dano de Ataque quando abaixo de 30% HP.",
                "effects": {"low_hp_dmg_boost": {"hp_threshold": 0.30, "bonus_mult": 0.20}}
            },
            "epica": {
                "description": "Épica: +30% Dano quando abaixo de 30% HP. Ganha +10% Roubo de Vida neste estado.",
                "effects": {"low_hp_dmg_boost": {"hp_threshold": 0.30, "bonus_mult": 0.30, "lifesteal_flat": 0.10}}
            },
            "lendaria": {
                "description": "Lendária: +40% Dano e +20% Roubo de Vida quando abaixo de 40% HP.",
                "effects": {"low_hp_dmg_boost": {"hp_threshold": 0.40, "bonus_mult": 0.40, "lifesteal_flat": 0.20}}
            }
        }
    },
    "berserker_golpe_divino_da_ira": {
        "display_name": "Golpe Divino da Ira", "type": "active", 
        "description": "Um ataque supremo que ignora defesa e causa dano massivo.",
        "allowed_classes": ["berserker"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 8, Mana 60): Dano 4.0x, Ignora 100% DEF.",
                "mana_cost": 60,
                "effects": {"cooldown_turns": 8, "damage_multiplier": 4.0, "defense_penetration": 1.0}
            },
            "epica": {
                "description": "Épica (CD 7, Mana 50): Dano 4.5x, Ignora 100% DEF.",
                "mana_cost": 50,
                "effects": {"cooldown_turns": 7, "damage_multiplier": 4.5, "defense_penetration": 1.0}
            },
            "lendaria": {
                "description": "Lendária (CD 7, Custa 20% HP): Dano 5.0x, Ignora 100% DEF. Se matar o alvo, o Cooldown é resetado.",
                "hp_cost_percent": 0.20,
                "effects": {"cooldown_turns": 7, "damage_multiplier": 5.0, "defense_penetration": 1.0, "cooldown_reduction_on_kill": 1.0}
            }
        }
    },
    # --- HABILIDADES DE EVENTO (Caçador) ---

    "cacador_passive_animal_companion": {
        "display_name": "Companheiro Animal", "type": "passive", 
        "description": "Um lobo leal luta ao seu lado, atacando ocasionalmente.", 
        "allowed_classes": ["cacador"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: 30% de chance de atacar (dano de 30% do Atk).",
                # Efeito original (dano 20) era muito fraco; mudei para escalar com Atk.
                "effects": {"companion_attack": {"damage_type": "physical", "scale": "attack", "value": 0.3, "chance": 0.3}}
            },
            "epica": {
                "description": "Épica: 40% de chance de atacar (dano de 40% do Atk).",
                "effects": {"companion_attack": {"damage_type": "physical", "scale": "attack", "value": 0.4, "chance": 0.4}}
            },
            "lendaria": {
                "description": "Lendária: 50% de chance (dano 50% Atk). Ataque aplica 'Sangramento'.",
                "effects": {"companion_attack": {"damage_type": "physical", "scale": "attack", "value": 0.5, "chance": 0.5,
                                                 "debuff": {"effect": "dot", "value": 0.15, "duration_turns": 3}}}
            }
        }
    },
    "cacador_active_deadeye_shot": {
        "display_name": "Tiro de Mira Mortal", "type": "active", 
        "description": "Aumenta a chance de crítico do próximo ataque.", 
        "allowed_classes": ["cacador"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 3, Mana 10): Próximo ataque tem +75% Chance de Crítico.",
                "mana_cost": 10, 
                "effects": {"cooldown_turns": 3, "next_hit_crit_chance_boost": 0.75}
            },
            "epica": {
                "description": "Épica (CD 2, Mana 10): Próximo ataque é Crítico Garantido (100%).",
                "mana_cost": 10, 
                "effects": {"cooldown_turns": 2, "next_hit_crit_chance_boost": 1.0}
            },
            "lendaria": {
                "description": "Lendária (CD 2, Mana 5): Próximo ataque é Crítico Garantido e ganha +50% Dano Crítico.",
                "mana_cost": 5, 
                "effects": {"cooldown_turns": 2, "next_hit_crit_chance_boost": 1.0, "next_hit_crit_damage_boost": 0.50}
            }
        }
    },
    #evento portal
    "cacador_passive_apex_predator": {
        "display_name": "Predador Alfa", "type": "passive", 
        "description": "Causa dano extra a monstros do tipo 'Boss'.", 
        "allowed_classes": ["cacador"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: Causa 15% de dano bônus contra 'Bosses'.",
                "effects": {"bonus_damage_vs_type": {"type": "boss", "value": 0.15}}
            },
            "epica": {
                "description": "Épica: Causa 25% de dano bônus contra 'Bosses'.",
                "effects": {"bonus_damage_vs_type": {"type": "boss", "value": 0.25}}
            },
            "lendaria": {
                "description": "Lendária: Causa 35% de dano bônus contra 'Bosses' e 10% contra 'Elites'.",
                "effects": {"bonus_damage_vs_type": {"type": "boss", "value": 0.35},
                            "bonus_damage_vs_type_2": {"type": "elite", "value": 0.10}}
            }
        }
    },
    # ID do placeholder antigo foi renomeado para ficar mais limpo
    "cacador_active_ricochet_arrow": {
        "display_name": "Flecha Ricocheteante", "type": "active", 
        "description": "Atira uma flecha que acerta o alvo principal e ricocheteia.",
        "allowed_classes": ["cacador"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 4, Mana 25): Atinge 2 alvos com 1.5x Dano.",
                "mana_cost": 25,
                # A definição original (multi_hit: 2, damage_multiplier: 1.5) é ambígua.
                # Assumindo 1.5x de dano em 2 alvos.
                "effects": {"cooldown_turns": 4, "damage_multiplier": 1.5, "multi_hit": 2, "single_target": False}
            },
            "epica": {
                "description": "Épica (CD 3, Mana 25): Atinge 3 alvos com 1.5x Dano.",
                "mana_cost": 25,
                "effects": {"cooldown_turns": 3, "damage_multiplier": 1.5, "multi_hit": 3, "single_target": False}
            },
            "lendaria": {
                "description": "Lendária (CD 3, Mana 20): Atinge 3 alvos com 1.8x Dano.",
                "mana_cost": 20,
                "effects": {"cooldown_turns": 3, "damage_multiplier": 1.8, "multi_hit": 3, "single_target": False}
            }
        }
    },
    # --- HABILIDADES DE EVENTO (Monge) ---
    "monge_active_iron_skin": {
        "display_name": "Pele de Ferro",
        "type": "support",  # <--- Envia para o party_engine
        "description": "Endurece o corpo com Ki, inspirando defesa no grupo.",
        "allowed_classes": ["monge"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 5, Mana 20): Postura defensiva (30% Redução - Visual).",
                "mana_cost": 20,
                "effects": {
                    "cooldown_turns": 5,
                    # Configuração para o Log Visual
                    "party_buff": {
                        "buff_name": "Pele de Ferro",
                        "buff_value": "30% Redução de Dano",
                        "duration": "2 turnos"
                    }
                }
            },
            "epica": {
                "description": "Épica (CD 4, Mana 18): Postura defensiva (40% Redução).",
                "mana_cost": 18,
                "effects": {
                    "cooldown_turns": 4,
                    "party_buff": {
                        "buff_name": "Corpo de Aço",
                        "buff_value": "40% Redução de Dano",
                        "duration": "2 turnos"
                    }
                }
            },
            "lendaria": {
                "description": "Lendária (CD 4, Mana 15): Postura defensiva (50% Red. + Espinhos).",
                "mana_cost": 15,
                "effects": {
                    "cooldown_turns": 4,
                    "party_buff": {
                        "buff_name": "Pele de Adamantium",
                        "buff_value": "50% Redução / Refletir Dano",
                        "duration": "2 turnos"
                    }
                }
            }
        }
    },
    "monge_passive_elemental_strikes": {
        "display_name": "Golpes Elementais", "type": "passive", 
        "description": "Os seus ataques têm uma chance de causar dano elemental extra (Magia).", 
        "allowed_classes": ["monge"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: 20% de chance de causar 20% do M.Atk como dano mágico extra.",
                # O dano original (25) não escala. Mudei para escalar com M.Atk.
                "effects": {"chance_on_hit": {"effect": "extra_elemental_damage", "chance": 0.2, "damage_type": "magic", "scale": "magic_attack", "value": 0.20}}
            },
            "epica": {
                "description": "Épica: 25% de chance de causar 30% do M.Atk como dano mágico extra.",
                "effects": {"chance_on_hit": {"effect": "extra_elemental_damage", "chance": 0.25, "damage_type": "magic", "scale": "magic_attack", "value": 0.30}}
            },
            "lendaria": {
                "description": "Lendária: 30% de chance (40% M.Atk). Aplica 'Choque' (-10% M.Def).",
                "effects": {"chance_on_hit": {"effect": "extra_elemental_damage", "chance": 0.30, "damage_type": "magic", "scale": "magic_attack", "value": 0.40,
                                              "debuff": {"stat": "magic_resist", "value": -0.10, "duration_turns": 3}}}
            }
        }
    },
    #evento portal
    "monge_active_transcendence": {
        "display_name": "Transcendência",
        "type": "support", # <--- Ativa o sistema de grupo
        "description": "Emana uma aura de paz, recuperando Vida e Mana de todos os aliados.",
        "allowed_classes": ["monge"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 6, Mana 10): Recupera 15% HP e 10 MP do grupo.",
                "mana_cost": 10,
                "effects": {
                    "cooldown_turns": 6,
                    # Recupera 15% do HP Máximo de cada aliado
                    "party_heal": {
                        "amount_percent_max_hp": 0.15
                    },
                    # Recupera 10 de Mana (Valor fixo, pois engine atual usa amount_flat)
                    "party_mana": {
                        "amount_flat": 10
                    }
                }
            },
            "epica": {
                "description": "Épica (CD 5, Mana 10): Recupera 20% HP e 15 MP do grupo.",
                "mana_cost": 10,
                "effects": {
                    "cooldown_turns": 5,
                    "party_heal": {
                        "amount_percent_max_hp": 0.20
                    },
                    "party_mana": {
                        "amount_flat": 15
                    }
                }
            },
            "lendaria": {
                "description": "Lendária (CD 5, Mana 5): Recupera 30% HP/MP e Purifica o grupo.",
                "mana_cost": 5,
                "effects": {
                    "cooldown_turns": 5,
                    "party_heal": {
                        "amount_percent_max_hp": 0.30
                    },
                    "party_mana": {
                        "amount_flat": 20
                    },
                    # Usa o Buff visual para indicar a purificação no log
                    "party_buff": {
                        "buff_name": "Purificação Espiritual",
                        "buff_value": "Remove Debuffs",
                        "duration": "Instantâneo"
                    }
                }
            }
        }
    },
    # ID do placeholder antigo foi renomeado para ficar mais limpo
    "monge_active_thunder_palm": {
        "display_name": "Palma do Trovão", "type": "active", 
        "description": "Libera uma onda de Ki que causa dano em área e tem chance de atordoar.",
        "allowed_classes": ["monge"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 5, Mana 30): Dano 1.5x (AoE), 15% chance de Stun.",
                "mana_cost": 30,
                "effects": {"cooldown_turns": 5, "damage_multiplier": 1.5, "aoe": True, "chance_to_stun": 0.15}
            },
            "epica": {
                "description": "Épica (CD 4, Mana 25): Dano 1.8x (AoE), 25% chance de Stun.",
                "mana_cost": 25,
                "effects": {"cooldown_turns": 4, "damage_multiplier": 1.8, "aoe": True, "chance_to_stun": 0.25}
            },
            "lendaria": {
                "description": "Lendária (CD 4, Mana 25): Dano 2.0x (AoE), 35% chance de Stun. Aplica 'Choque' (-15% M.Def).",
                "mana_cost": 25,
                "effects": {"cooldown_turns": 4, "damage_multiplier": 2.0, "aoe": True, "chance_to_stun": 0.35,
                            "debuff_target": {"stat": "magic_resist", "value": -0.15, "duration_turns": 3}}
            }
        }
    },


    # --- HABILIDADES DE EVENTO (Mago) ---

    "mago_active_curse_of_weakness": {
        "display_name": "Maldição da Fraqueza",
        "type": "support",  # <--- Mantemos support para não calcular dano direto
        "description": "Amaldiçoa o alvo, reduzindo seu poder ofensivo.",
        "allowed_classes": ["mago"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 4, Mana 15): Reduz Ataque em 20% (3 turnos).",
                "mana_cost": 15,
                "effects": {
                    "cooldown_turns": 4,
                    # Configuração para o Log de Debuff no engine.py
                    "debuff_target": {
                        "stat": "Ataque",
                        "value": "-20%",
                        "duration": "3 turnos"
                    }
                }
            },
            "epica": {
                "description": "Épica (CD 4, Mana 12): Reduz Ataque em 25% (4 turnos).",
                "mana_cost": 12,
                "effects": {
                    "cooldown_turns": 4,
                    "debuff_target": {
                        "stat": "Ataque",
                        "value": "-25%",
                        "duration": "4 turnos"
                    }
                }
            },
            "lendaria": {
                "description": "Lendária (CD 3, Mana 10): Reduz ATK e M.ATK em 30% (4 turnos).",
                "mana_cost": 10,
                "effects": {
                    "cooldown_turns": 3,
                    # Combinamos os textos para aparecer tudo em uma linha no log
                    "debuff_target": {
                        "stat": "ATK e Poder Mágico",
                        "value": "-30%",
                        "duration": "4 turnos"
                    }
                }
            }
        }
    },
    "mago_passive_elemental_attunement": {
        "display_name": "Sintonia Elemental", "type": "passive", 
        "description": "Aumenta o dano mágico e o ataque base.", 
        "allowed_classes": ["mago"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: +10% Dano Mágico, +5% Ataque base.",
                "effects": {"damage_type_mult": {"magic": 0.10}, "stat_add_mult": {"attack": 0.05}}
            },
            "epica": {
                "description": "Épica: +15% Dano Mágico, +7% Ataque base.",
                "effects": {"damage_type_mult": {"magic": 0.15}, "stat_add_mult": {"attack": 0.07}}
            },
            "lendaria": {
                "description": "Lendária: +20% Dano Mágico, +10% Ataque base, +5% Pen. Mágica.",
                "effects": {"damage_type_mult": {"magic": 0.20}, "stat_add_mult": {"attack": 0.10, "magic_penetration": 0.05}}
            }
        }
    },
    #evento portal
    "mago_active_meteor_swarm": {
        "display_name": "Chuva de Meteoros", "type": "active", 
        "description": "Invoca uma chuva de meteoros que atinge todos os inimigos.", 
        "allowed_classes": ["mago"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 5, Mana 30): Dano 2.0x (AoE, Mágico).",
                "mana_cost": 30,
                "effects": {"cooldown_turns": 5, "damage_multiplier": 2.0, "damage_type": "magic", "aoe": True}
            },
            "epica": {
                "description": "Épica (CD 4, Mana 28): Dano 2.2x (AoE, Mágico).",
                "mana_cost": 28,
                "effects": {"cooldown_turns": 4, "damage_multiplier": 2.2, "damage_type": "magic", "aoe": True}
            },
            "lendaria": {
                "description": "Lendária (CD 4, Mana 25): Dano 2.5x (AoE). Aplica 'Queimadura' (10% M.Atk/2t).",
                "mana_cost": 25,
                "effects": {"cooldown_turns": 4, "damage_multiplier": 2.5, "damage_type": "magic", "aoe": True,
                            "chance_on_hit": {"effect": "dot", "chance": 1.0, "scale": "magic_attack", "value": 0.1, "duration_turns": 2}}
            }
        }
    },
    "mago_active_arcane_ward": {
        "display_name": "Escudo Arcano",
        "type": "support",  # <--- Ativa o party_engine
        "description": "Cria uma barreira de mana que protege o grupo contra magia.",
        "allowed_classes": ["mago"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 6, Mana 35): +25% Resist. Mágica (2 turnos).",
                "mana_cost": 35,
                "effects": {
                    "cooldown_turns": 6,
                    "party_buff": {
                        "buff_name": "Escudo Arcano",
                        "buff_value": "+25% M.RES",
                        "duration": "2 turnos"
                    }
                }
            },
            "epica": {
                "description": "Épica (CD 6, Mana 30): +35% Resist. Mágica (3 turnos).",
                "mana_cost": 30,
                "effects": {
                    "cooldown_turns": 6,
                    "party_buff": {
                        "buff_name": "Barreira Mística",
                        "buff_value": "+35% M.RES",
                        "duration": "3 turnos"
                    }
                }
            },
            "lendaria": {
                "description": "Lendária (CD 5, Mana 30): +40% M.RES e +15% DEF (3 turnos).",
                "mana_cost": 30,
                "effects": {
                    "cooldown_turns": 5,
                    "party_buff": {
                        "buff_name": "Fortaleza Arcana",
                        "buff_value": "+40% M.RES / +15% DEF",
                        "duration": "3 turnos"
                    }
                }
            }
        }
    },

    # --- HABILIDADES DE EVENTO (Bardo) ---

    "bardo_active_song_of_valor": {
        "display_name": "Canção do Valor",
        "type": "support",  # <--- Envia para o processador de grupo
        "description": "Inspira os aliados, aumentando o ataque do grupo.",
        "allowed_classes": ["bardo"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 4, Mana 15): +15% Ataque (3 turnos).",
                "mana_cost": 15,
                "effects": {
                    "cooldown_turns": 4,
                    # Configuração para o Log Visual do party_engine
                    "party_buff": {
                        "buff_name": "Valor",
                        "buff_value": "+15% ATK",
                        "duration": "3 turnos"
                    }
                }
            },
            "epica": {
                "description": "Épica (CD 4, Mana 12): +20% Ataque (3 turnos).",
                "mana_cost": 12,
                "effects": {
                    "cooldown_turns": 4,
                    "party_buff": {
                        "buff_name": "Valor Heroico",
                        "buff_value": "+20% ATK",
                        "duration": "3 turnos"
                    }
                }
            },
            "lendaria": {
                "description": "Lendária (CD 3, Mana 10): +25% Ataque (4 turnos).",
                "mana_cost": 10,
                "effects": {
                    "cooldown_turns": 3,
                    "party_buff": {
                        "buff_name": "Hino da Vitória",
                        "buff_value": "+25% ATK",
                        "duration": "4 turnos"
                    }
                }
            }
        }
    },
    "bardo_active_dissonant_melody": {
        "display_name": "Melodia Dissonante",
        "type": "support", 
        "description": "Confunde o inimigo, com chance de atordoá-lo.",
        "allowed_classes": ["bardo"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 4, Mana 10): 25% de chance de Stun.",
                "mana_cost": 10,
                "effects": {
                    "cooldown_turns": 4,
                    "chance_to_stun": 0.25
                }
            },
            "epica": {
                "description": "Épica (CD 3, Mana 10): 35% de chance de Stun.",
                "mana_cost": 10,
                "effects": {
                    "cooldown_turns": 3,
                    "chance_to_stun": 0.35
                }
            },
            "lendaria": {
                "description": "Lendária (CD 3, Mana 5): 50% Stun e reduz Resistência Mágica.",
                "mana_cost": 5,
                "effects": {
                    "cooldown_turns": 3,
                    "chance_to_stun": 0.50,
                    # O debuff visual será processado no log
                    "debuff_target": {
                        "stat": "magic_resist", 
                        "value": "-15%", 
                        "duration": "3 turnos"
                    }
                }
            }
        }
    },
    # evento portal
    "bardo_passive_symphony_of_power": {
        "display_name": "Sinfonia do Poder", "type": "passive",
        "description": "Os efeitos dos seus buffs de grupo são ampliados.",
        "allowed_classes": ["bardo"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: Os efeitos dos seus buffs de grupo são ampliados em 20%.",
                "effects": {"buff_potency_increase": 0.20}
            },
            "epica": {
                "description": "Épica: Efeitos de buffs ampliados em 30%.",
                "effects": {"buff_potency_increase": 0.30}
            },
            "lendaria": {
                "description": "Lendária: Efeitos de buffs +40%. Efeitos de 'Debuffs' +10%.",
                "effects": {"buff_potency_increase": 0.40, "debuff_potency_increase": 0.10}
            }
        }
    },
    "bardo_passive_perfect_pitch": {
        "display_name": "Tom Perfeito",
        "type": "passive", # <--- O stats.py lê isso automaticamente
        "description": "Sua afinação perfeita amplifica a potência mágica e a sorte.",
        "allowed_classes": ["bardo"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: Aumenta a Sorte em 10% (Melhora Críticos e Drops).",
                "effects": {
                    # stat_add_mult aumenta a porcentagem dos atributos base
                    "stat_add_mult": {"luck": 0.10}
                }
            },
            "epica": {
                "description": "Épica: Sorte +15% e Poder Mágico +10% (Amplifica Curas).",
                "effects": {
                    "stat_add_mult": {"luck": 0.15, "magic_attack": 0.10}
                }
            },
            "lendaria": {
                "description": "Lendária: Sorte +20%, Poder Mágico +15% e Iniciativa +10%.",
                "effects": {
                    "stat_add_mult": {"luck": 0.20, "magic_attack": 0.15, "initiative": 0.10}
                }
            }
        }
    },
    "bardo_nota_cortante": { # [NOVO] Essencial para solar
        "display_name": "𝐍𝐨𝐭𝐚 𝐂𝐨𝐫𝐭𝐚𝐧𝐭𝐞", "type": "active", 
        "description": "Lança uma onda sonora afiada que corta o inimigo.",
        "allowed_classes": ["bardo"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 0, Mana 15): Dano 1.5x (Mágico).",
                "mana_cost": 15,
                "effects": {"cooldown_turns": 0, "damage_multiplier": 1.5, "damage_type": "magic"}
            },
            "epica": {
                "description": "Épica (CD 0, Mana 12): Dano 1.7x (Mágico).",
                "mana_cost": 12,
                "effects": {"cooldown_turns": 0, "damage_multiplier": 1.7, "damage_type": "magic"}
            },
            "lendaria": {
                "description": "Lendária (CD 0, Mana 10): Dano 2.0x (Mágico).",
                "mana_cost": 10,
                "effects": {"cooldown_turns": 0, "damage_multiplier": 2.0, "damage_type": "magic"}
            }
        }
    },
    # --- HABILIDADES DE EVENTO (Assassino) ---

    "assassino_active_shadow_strike": {
        "display_name": "𝐆𝐨𝐥𝐩𝐞 𝐒𝐨𝐦𝐛𝐫𝐢𝐨", "type": "active", 
        "description": "Um ataque rápido das sombras que não pode ser esquivado.", 
        "allowed_classes": ["assassino"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 3, Mana 15): Dano 1.4x, Acerto Garantido.",
                "mana_cost": 15, 
                "effects": {"cooldown_turns": 3, "guaranteed_hit": True, "damage_multiplier": 1.4}
            },
            "epica": {
                "description": "Épica (CD 3, Mana 12): Dano 1.6x, Acerto Garantido, +10% Chance de Crítico.",
                "mana_cost": 12, 
                "effects": {"cooldown_turns": 3, "guaranteed_hit": True, "damage_multiplier": 1.6, "bonus_crit_chance": 0.10}
            },
            "lendaria": {
                "description": "Lendária (CD 2, Mana 10): Dano 1.8x, Acerto Garantido, +25% Chance de Crítico.",
                "mana_cost": 10, 
                "effects": {"cooldown_turns": 2, "guaranteed_hit": True, "damage_multiplier": 1.8, "bonus_crit_chance": 0.25}
            }
        }
    },
    # evento portal
    "assassino_passive_potent_toxins": {
        "display_name": "𝐓𝐨𝐱𝐢𝐧𝐚𝐬 𝐏𝐨𝐭𝐞𝐧𝐭𝐞𝐬", "type": "passive", 
        "description": "Os seus ataques têm chance de aplicar veneno.", 
        "allowed_classes": ["assassino"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: 30% de chance de aplicar veneno (10% Atk / 3 turnos).",
                # Dano original (15) não escala. Mudei para escalar com Atk.
                "effects": {"chance_on_hit": {"effect": "dot", "damage_type": "physical", "scale": "attack", "value": 0.10, "duration_turns": 3, "chance": 0.3}}
            },
            "epica": {
                "description": "Épica: 35% chance, veneno (15% Atk / 3t). Acumula 2x.",
                "effects": {"chance_on_hit": {"effect": "dot", "damage_type": "physical", "scale": "attack", "value": 0.15, "duration_turns": 3, "chance": 0.35, "stack": 2}}
            },
            "lendaria": {
                "description": "Lendária: 40% chance, veneno (20% Atk / 3t). Acumula 3x. Alvos envenenados têm -10% Agilidade.",
                "effects": {"chance_on_hit": {"effect": "dot", "damage_type": "physical", "scale": "attack", "value": 0.20, "duration_turns": 3, "chance": 0.40, "stack": 3,
                                              "debuff": {"stat": "agility", "value": -0.10, "duration_turns": 3}}}
            }
        }
    },
    "assassino_active_dance_of_a_thousand_cuts": {
        "display_name": "𝐃𝐚𝐧𝐜̧𝐚 𝐝𝐚𝐬 𝐌𝐢𝐥 𝐋𝐚̂𝐦𝐢𝐧𝐚𝐬", "type": "active", 
        "description": "Desfere uma rajada de golpes rápidos.", 
        "allowed_classes": ["assassino"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 5, Mana 25): 3-5 golpes (0.6x Dano).",
                "mana_cost": 25, 
                "effects": {"cooldown_turns": 5, "multi_hit_min": 3, "multi_hit_max": 5, "damage_multiplier": 0.6}
            },
            "epica": {
                "description": "Épica (CD 4, Mana 20): 4-6 golpes (0.6x Dano).",
                "mana_cost": 20, 
                "effects": {"cooldown_turns": 4, "multi_hit_min": 4, "multi_hit_max": 6, "damage_multiplier": 0.6}
            },
            "lendaria": {
                "description": "Lendária (CD 4, Mana 20): 5-7 golpes (0.7x Dano). Cada golpe tem 10% de chance de aplicar 'Sangramento'.",
                "mana_cost": 20, 
                "effects": {"cooldown_turns": 4, "multi_hit_min": 5, "multi_hit_max": 7, "damage_multiplier": 0.7,
                            "chance_on_hit": {"effect": "dot", "chance": 0.10, "value": 0.1, "duration_turns": 2}}
            }
        }
    },
    "assassino_active_guillotine_strike": {
        "display_name": "𝐆𝐨𝐥𝐩𝐞 𝐆𝐮𝐢𝐥𝐡𝐨𝐭𝐢𝐧𝐚", "type": "active", 
        "description": "Ataque massivo com dano bônus contra alvos com HP baixo (Execução).",
        "allowed_classes": ["assassino"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 6, Mana 45): Dano 2.5x. +50% Dano bônus se alvo < 30% HP.",
                "mana_cost": 45,
                "effects": {"cooldown_turns": 6, "damage_multiplier": 2.5, "bonus_damage_if_low_hp_target": {"threshold": 0.30, "bonus": 0.50}}
            },
            "epica": {
                "description": "Épica (CD 6, Mana 40): Dano 2.5x. +75% Dano bônus se alvo < 40% HP.",
                "mana_cost": 40,
                "effects": {"cooldown_turns": 6, "damage_multiplier": 2.5, "bonus_damage_if_low_hp_target": {"threshold": 0.40, "bonus": 0.75}}
            },
            "lendaria": {
                "description": "Lendária (CD 5, Mana 35): Dano 3.0x. +100% Dano bônus se alvo < 50% HP. Reseta o Cooldown se matar o alvo.",
                "mana_cost": 35,
                "effects": {"cooldown_turns": 5, "damage_multiplier": 3.0, "bonus_damage_if_low_hp_target": {"threshold": 0.50, "bonus": 1.0},
                            "cooldown_reduction_on_kill": 1.0}
            }
        }
    },

    # --- HABILIDADES DE EVENTO (Samurai) ---

    "samurai_passive_iai_stance": {
        "display_name": "Postura Iai", "type": "passive", 
        "description": "O primeiro ataque em cada combate tem uma chance de crítico aumentada.", 
        "allowed_classes": ["samurai"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: O primeiro ataque tem +50% de Chance de Crítico.",
                "effects": {"first_hit_crit_chance_boost": 0.50}
            },
            "epica": {
                "description": "Épica: O primeiro ataque tem +75% Chance de Crítico e +25% Dano Crítico.",
                "effects": {"first_hit_crit_chance_boost": 0.75, "first_hit_crit_damage_boost": 0.25}
            },
            "lendaria": {
                "description": "Lendária: O primeiro ataque é um Crítico Garantido (100%) com +50% Dano Crítico.",
                "effects": {"first_hit_crit_chance_boost": 1.0, "first_hit_crit_damage_boost": 0.50}
            }
        }
    },
    "samurai_active_parry_and_riposte": {
        "display_name": "Aparar e Ripostar", "type": "active", 
        "description": "Assume uma postura que, se atacado, anula o dano e contra-ataca.", 
        "allowed_classes": ["samurai"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 4, Mana 10): Postura (1 turno). Se atacado, anula o dano e contra-ataca (100% Atk).",
                "mana_cost": 10, 
                # Dano de contra-ataque não estava definido, assumindo 1.0x
                "effects": {"cooldown_turns": 4, "stance_parry": True, "duration_turns": 1, "damage_scale": 1.0}
            },
            "epica": {
                "description": "Épica (CD 3, Mana 10): Postura (1 turno). Contra-ataque (150% Atk).",
                "mana_cost": 10, 
                "effects": {"cooldown_turns": 3, "stance_parry": True, "duration_turns": 1, "damage_scale": 1.5}
            },
            "lendaria": {
                "description": "Lendária (CD 3, Mana 5): Postura (1 turno). Contra-ataque (200% Atk) que ignora 50% DEF.",
                "mana_cost": 5, 
                "effects": {"cooldown_turns": 3, "stance_parry": True, "duration_turns": 1, "damage_scale": 2.0, "armor_penetration": 0.50}
            }
        }
    },
    "samurai_active_banner_of_command": {
        "display_name": "Estandarte de Comando",
        "type": "support",  # <--- IMPORTANTE: Define que vai para o party_engine
        "description": "Ergue um estandarte que inspira e protege os aliados.",
        "allowed_classes": ["samurai"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 5, Mana 20): Defesa da party +20% (3 turnos).",
                "mana_cost": 20,
                "effects": {
                    "cooldown_turns": 5,
                    "party_buff": {
                        "buff_name": "Defesa",
                        "buff_value": "20%",
                        "duration": "3 turnos"
                    }
                }
            },
            "epica": {
                "description": "Épica (CD 5, Mana 20): Defesa da party +25% (4 turnos).",
                "mana_cost": 20,
                "effects": {
                    "cooldown_turns": 5,
                    "party_buff": {
                        "buff_name": "Defesa Reforçada",
                        "buff_value": "25%",
                        "duration": "4 turnos"
                    }
                }
            },
            "lendaria": {
                "description": "Lendária (CD 4, Mana 20): Defesa +30% e Res. Mágica +10%.",
                "mana_cost": 20,
                "effects": {
                    "cooldown_turns": 4,
                    "party_buff": {
                        "buff_name": "Muralha Impenetrável",
                        "buff_value": "30% DEF / 10% M.RES",
                        "duration": "4 turnos"
                    }
                }
            }
        }
    },
    #evento portal dimen
    "samurai_passive_perfect_parry": {
        "display_name": "Aparar Perfeito", "type": "passive", 
        "description": "Chance de aparar automaticamente e anular o dano de ataques físicos.",
        "allowed_classes": ["samurai"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: 10% de chance de aparar e anular dano físico.",
                "effects": {"chance_to_block_physical": 0.10}
            },
            "epica": {
                "description": "Épica: 15% de chance de aparar.",
                "effects": {"chance_to_block_physical": 0.15}
            },
            "lendaria": {
                "description": "Lendária: 20% de chance de aparar. Ao aparar, reflete 50% do dano anulado.",
                "effects": {"chance_to_block_physical": 0.20, "reflect_on_block": 0.50}
            }
        }
    },


   # --- HABILIDADES DE EVENTO (Curandeiro) ---

    "active_divine_touch": {
        "display_name": "Toque Divino", "type": "support", 
        "description": "Cura a si mesmo e remove debuffs.", 
        "allowed_classes": ["curandeiro"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 3, Mana 20): Cura 25% do HP Máximo (Self) e remove 1 debuff.",
                "mana_cost": 20, 
                "effects": {"cooldown_turns": 3, "self_heal_percent": 0.25, "remove_debuffs": 1}
            },
            "epica": {
                "description": "Épica (CD 2, Mana 20): Cura 30% HP (Self). Remove 2 debuffs.",
                "mana_cost": 20, 
                "effects": {"cooldown_turns": 2, "self_heal_percent": 0.30, "remove_debuffs": 2}
            },
            "lendaria": {
                "description": "Lendária (CD 2, Mana 15): Cura 40% HP (Self). Remove 2 debuffs. Ganha +20% Resist. Mágica por 2 turnos.",
                "mana_cost": 15, 
                "effects": {"cooldown_turns": 2, "self_heal_percent": 0.40, "remove_debuffs": 2,
                            "self_buff": {"effect": "magic_resistance", "value": 0.20, "duration_turns": 2}}
            }
        }
    },
    "passive_aegis_of_faith": {
        "display_name": "Égide da Fé", "type": "passive", 
        "description": "Aumenta a potência dos buffs de Defesa e Resistência que você lança.",
        "allowed_classes": ["curandeiro"],
        "rarity_effects": {
            "comum": {
                "description": "Comum: Aumenta a potência dos buffs de Def/M.Res em 20%.",
                "effects": {"buff_stat_potency_increase": {"defense": 0.20, "magic_resistance": 0.20}}
            },
            "epica": {
                "description": "Épica: Aumenta a potência em 30%.",
                "effects": {"buff_stat_potency_increase": {"defense": 0.30, "magic_resistance": 0.30}}
            },
            "lendaria": {
                "description": "Lendária: Aumenta a potência em 40%. Também afeta buffs de Ataque e Atk Mágico (em 10%).",
                "effects": {"buff_stat_potency_increase": {"defense": 0.40, "magic_resistance": 0.40, "attack": 0.10, "magic_attack": 0.10}}
            }
        }
    },
    "active_celestial_shield": {
        "display_name": "Escudo Celestial", "type": "support", 
        "description": "Dá um escudo ao grupo baseado na Defesa do Curandeiro.",
        "allowed_classes": ["curandeiro"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 6, Mana 40): Escudo (100% DEF do Curandeiro) para a party (1 turno).",
                "mana_cost": 40, 
                "effects": {"cooldown_turns": 6, "party_buff": {"stat": "shield_based_on_def", "value": 1.0, "duration_turns": 1}}
            },
            "epica": {
                "description": "Épica (CD 5, Mana 40): Escudo (150% DEF) para a party (2 turnos).",
                "mana_cost": 40, 
                "effects": {"cooldown_turns": 5, "party_buff": {"stat": "shield_based_on_def", "value": 1.5, "duration_turns": 2}}
            },
            "lendaria": {
                "description": "Lendária (CD 5, Mana 35): Escudo (200% DEF) (2t). Também cura 50% da DEF do Curandeiro.",
                "mana_cost": 35, 
                "effects": {"cooldown_turns": 5, "party_buff": {"stat": "shield_based_on_def", "value": 2.0, "duration_turns": 2},
                            "party_heal": {"amount_based_on_def": 0.5}}
            }
        }
    },
    
    # ====================================================================
    # HABILIDADES BASICAS (Adiquiridas via Evento/Drop)
    # ====================================================================

    "guerreiro_corte_perfurante": {
        "display_name": "𝐂𝐨𝐫𝐭𝐞 𝐏𝐞𝐫𝐟𝐮𝐫𝐚𝐧𝐭𝐞", 
        "type": "active", 
        "description": "Um golpe focado que perfura a armadura, reduzindo a defesa inimiga.",
        "allowed_classes": ["guerreiro"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 0, Mana 10): Dano 1.2x. Reduz -20% DEF por 3t.",
                "mana_cost": 10,
                "effects": {"cooldown_turns": 0, "damage_multiplier": 1.2, "debuff_target": {"stat": "defense", "value": -0.20, "duration_turns": 3}}
            },
            "epica": {
                "description": "Épica (CD 0, Mana 8): Dano 1.4x. Reduz -25% DEF por 3t.",
                "mana_cost": 8,
                "effects": {"cooldown_turns": 0, "damage_multiplier": 1.4, "debuff_target": {"stat": "defense", "value": -0.25, "duration_turns": 3}}
            },
            "lendaria": {
                "description": "Lendária (CD 0, Mana 5): Dano 1.5x. Reduz -30% DEF por 4t.",
                "mana_cost": 5,
                "effects": {"cooldown_turns": 0, "damage_multiplier": 1.5, "debuff_target": {"stat": "defense", "value": -0.30, "duration_turns": 4}}
            }
        }
    },
    "berserker_golpe_selvagem": {
        "display_name": "𝐆𝐨𝐥𝐩𝐞 𝐒𝐞𝐥𝐯𝐚𝐠𝐞𝐦", "type": "active", 
        "description": "Um ataque poderoso que causa mais dano quanto menos vida você tiver.",
        "allowed_classes": ["berserker"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 0, Mana 12): Dano 1.5x. +50% Dano bônus se < 30% HP.",
                "mana_cost": 12,
                "effects": {"cooldown_turns": 0, "damage_multiplier": 1.5, "low_hp_dmg_boost": {"threshold": 0.30, "bonus": 0.5}}
            },
            "epica": {
                "description": "Épica (CD 0, Mana 10): Dano 1.6x. +75% Dano bônus se < 35% HP.",
                "mana_cost": 10,
                "effects": {"cooldown_turns": 0, "damage_multiplier": 1.6, "low_hp_dmg_boost": {"threshold": 0.35, "bonus": 0.75}}
            },
            "lendaria": {
                "description": "Lendária (CD 0, Mana 10): Dano 1.7x. +100% Dano bônus se < 40% HP.",
                "mana_cost": 10,
                "effects": {"cooldown_turns": 0, "damage_multiplier": 1.7, "low_hp_dmg_boost": {"threshold": 0.40, "bonus": 1.0}}
            }
        }
    },
    "cacador_flecha_precisa": {
        "display_name": "𝐅𝐥𝐞𝐜𝐡𝐚 𝐏𝐫𝐞𝐜𝐢𝐬𝐚", "type": "active", 
        "description": "Um tiro certeiro com chance de acerto crítico bônus.",
        "allowed_classes": ["cacador"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 0, Mana 15): Dano 1.3x. +50% Chance de Crítico.",
                "mana_cost": 15,
                "effects": {"cooldown_turns": 0, "damage_multiplier": 1.3, "bonus_crit_chance": 0.50}
            },
            "epica": {
                "description": "Épica (CD 0, Mana 12): Dano 1.4x. +75% Chance de Crítico.",
                "mana_cost": 12,
                "effects": {"cooldown_turns": 0, "damage_multiplier": 1.4, "bonus_crit_chance": 0.75}
            },
            "lendaria": {
                "description": "Lendária (CD 0, Mana 10): Dano 1.5x. Crítico Garantido (100%).",
                "mana_cost": 10,
                "effects": {"cooldown_turns": 0, "damage_multiplier": 1.5, "bonus_crit_chance": 1.0}
            }
        }
    },
    "monge_rajada_de_punhos": {
        "display_name": "𝐑𝐚𝐣𝐚𝐝𝐚 𝐝𝐞 𝐏𝐮𝐧𝐡𝐨𝐬", "type": "active", 
        "description": "Ataca rapidamente, golpeando o inimigo várias vezes.",
        "allowed_classes": ["monge"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 0, Mana 18): 2 golpes (0.8x Dano).",
                "mana_cost": 18,
                "effects": {"cooldown_turns": 0, "damage_multiplier": 0.8, "multi_hit": 2}
            },
            "epica": {
                "description": "Épica (CD 0, Mana 15): 3 golpes (0.8x Dano).",
                "mana_cost": 15,
                "effects": {"cooldown_turns": 0, "damage_multiplier": 0.8, "multi_hit": 3}
            },
            "lendaria": {
                "description": "Lendária (CD 0, Mana 15): 3 golpes (0.9x Dano).",
                "mana_cost": 15,
                "effects": {"cooldown_turns": 0, "damage_multiplier": 0.9, "multi_hit": 3}
            }
        }
    },
    "mago_bola_de_fogo": {
        "display_name": "𝐁𝐨𝐥𝐚 𝐝𝐞 𝐅𝐨𝐠𝐨", "type": "active", 
        "description": "Um feitiço de alvo único que causa alto dano de fogo (Mágico).",
        "allowed_classes": ["mago"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 0, Mana 25): Dano 2.5x (Mágico).",
                "mana_cost": 75,
                "effects": {"cooldown_turns": 5, "damage_multiplier": 1.7, "damage_type": "magic"}
            },
            "epica": {
                "description": "Épica (CD 0, Mana 22): Dano 2.8x (Mágico).",
                "mana_cost": 122,
                "effects": {"cooldown_turns": 4, "damage_multiplier": 2.1, "damage_type": "magic"}
            },
            "lendaria": {
                "description": "Lendária (CD 0, Mana 20): Dano 3.0x (Mágico). Aplica 'Queimadura'.",
                "mana_cost": 180,
                "effects": {"cooldown_turns": 3, "damage_multiplier": 2.4, "damage_type": "magic",
                            "chance_on_hit": {"effect": "dot", "chance": 1.0, "scale": "magic_attack", "value": 0.15, "duration_turns": 2}}
            }
        }
    },
    "bardo_melodia_restauradora": {
        "display_name": "𝐌𝐞𝐥𝐨𝐝𝐢𝐚 𝐑𝐞𝐬𝐭𝐚𝐮𝐫𝐚𝐝𝐨𝐫𝐚",
        "type": "support",  # <--- Essencial para ativar o sistema de grupo
        "description": "Uma melodia suave que cura todos os aliados.",
        "allowed_classes": ["bardo"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 2, Mana 18): Cura 100% M.Atk (Party).",
                "mana_cost": 18,
                "effects": {
                    "cooldown_turns": 2,
                    "party_heal": {
                        "heal_type": "magic_attack",
                        "heal_scale": 1.0
                    }
                }
            },
            "epica": {
                "description": "Épica (CD 2, Mana 15): Cura 130% M.Atk (Party).",
                "mana_cost": 15,
                "effects": {
                    "cooldown_turns": 2,
                    "party_heal": {
                        "heal_type": "magic_attack",
                        "heal_scale": 1.3
                    }
                }
            },
            "lendaria": {
                "description": "Lendária (CD 1, Mana 12): Cura 150% M.Atk (Party).",
                "mana_cost": 12,
                "effects": {
                    "cooldown_turns": 1,
                    "party_heal": {
                        "heal_type": "magic_attack",
                        "heal_scale": 1.5
                    }
                }
            }
        }
    },

    "assassino_ataque_furtivo": {
        "display_name": "𝐀𝐭𝐚𝐪𝐮𝐞 𝐅𝐮𝐫𝐭𝐢𝐯𝐨", "type": "active", 
        "description": "Um golpe letal que ignora parte da defesa do inimigo.",
        "allowed_classes": ["assassino"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 0, Mana 20): Dano 1.6x, Ignora 50% DEF.",
                "mana_cost": 20,
                "effects": {"cooldown_turns": 0, "damage_multiplier": 1.6, "defense_penetration": 0.50}
            },
            "epica": {
                "description": "Épica (CD 0, Mana 18): Dano 1.8x, Ignora 60% DEF.",
                "mana_cost": 18,
                "effects": {"cooldown_turns": 0, "damage_multiplier": 1.8, "defense_penetration": 0.60}
            },
            "lendaria": {
                "description": "Lendária (CD 0, Mana 15): Dano 2.0x, Ignora 75% DEF.",
                "mana_cost": 15,
                "effects": {"cooldown_turns": 0, "damage_multiplier": 2.0, "defense_penetration": 0.75}
            }
        }
    },
    "samurai_corte_iaijutsu": {
        "display_name": "𝐂𝐨𝐫𝐭𝐞 𝐈𝐚𝐢𝐣𝐮𝐭𝐬𝐮", "type": "active", 
        "description": "Um saque rápido e mortal com a katana.",
        "allowed_classes": ["samurai"],
        "rarity_effects": {
            "comum": {
               "description": "Comum (CD 0, Mana 18): Dano 1.4x, +30% Chance de Crítico.",
               "mana_cost": 18,
               "effects": {"cooldown_turns": 0, "damage_multiplier": 1.4, "bonus_crit_chance": 0.30}
            },
            "epica": {
                "description": "Épica (CD 0, Mana 15): Dano 1.5x, +50% Chance de Crítico.",
                "mana_cost": 15,
                "effects": {"cooldown_turns": 0, "damage_multiplier": 1.5, "bonus_crit_chance": 0.50}
            },
            "lendaria": {
                "description": "Lendária (CD 0, Mana 12): Dano 1.6x, +75% Chance de Crítico.",
                "mana_cost": 12,
                "effects": {"cooldown_turns": 0, "damage_multiplier": 1.6, "bonus_crit_chance": 0.75}
            }
        }
    },
    "samurai_sombra_demoniaca": {
        "display_name": "𝐒𝐨𝐦𝐛𝐫𝐚 𝐃𝐞𝐦𝐨𝐧𝐢́𝐚𝐜𝐚",
        "description": "Ataca duas vezes com 100% de chance de acerto crítico.",
        "type": "active", 
        "allowed_classes": ["samurai"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 5, Mana 25): 2 golpes (0.9x Dano), Crítico Garantido.",
                "mana_cost": 25,
                "effects": {"cooldown_turns": 5, "multi_hit": 2, "bonus_crit_chance": 1.0, "damage_multiplier": 0.9}
            },
            "epica": {
                "description": "Épica (CD 4, Mana 22): 2 golpes (1.0x Dano), Crítico Garantido.",
                "mana_cost": 22,
                "effects": {"cooldown_turns": 4, "multi_hit": 2, "bonus_crit_chance": 1.0, "damage_multiplier": 1.0}
            },
            "lendaria": {
                "description": "Lendária (CD 4, Mana 20): 3 golpes (0.9x Dano), Crítico Garantido.",
                "mana_cost": 20,
                "effects": {"cooldown_turns": 4, "multi_hit": 3, "bonus_crit_chance": 1.0, "damage_multiplier": 0.9}
            }
        }
    },
    "curandeiro_chama_sagrada": { # [NOVO] Essencial para solar
        "display_name": "𝐂𝐡𝐚𝐦𝐚 𝐒𝐚𝐠𝐫𝐚𝐝𝐚", "type": "active", 
        "description": "Queima o inimigo com fogo sagrado.",
        "allowed_classes": ["curandeiro"],
        "rarity_effects": {
            "comum": {
                "description": "Comum (CD 0, Mana 15): Dano 1.5x (Mágico).",
                "mana_cost": 15,
                "effects": {"cooldown_turns": 0, "damage_multiplier": 1.5, "damage_type": "magic"}
            },
            "epica": {
                "description": "Épica (CD 0, Mana 12): Dano 1.8x (Mágico).",
                "mana_cost": 12,
                "effects": {"cooldown_turns": 0, "damage_multiplier": 1.8, "damage_type": "magic"}
            },
            "lendaria": {
                "description": "Lendária (CD 0, Mana 10): Dano 2.2x (Mágico).",
                "mana_cost": 10,
                "effects": {"cooldown_turns": 0, "damage_multiplier": 2.2, "damage_type": "magic"}
            }
        }
    },
    
    
}


def get_skill_data_with_rarity(player_data: dict, skill_id: str) -> dict | None:
    """
    Retorna os dados da skill (SKILL_DATA) mesclados com os efeitos 
    da raridade que o jogador possui.
    """
    base_skill = SKILL_DATA.get(skill_id)
    if not base_skill: 
        return None

    # Se a skill não tem variação de raridade, retorna o base direto
    if "rarity_effects" not in base_skill:
        return base_skill.copy()

    # Verifica qual raridade o jogador tem
    player_skills = player_data.get("skills", {})
    rarity = "comum"
    
    if isinstance(player_skills, dict):
        player_skill_instance = player_skills.get(skill_id)
        if player_skill_instance:
            rarity = player_skill_instance.get("rarity", "comum")

    # Cria uma cópia para não alterar o original e mescla os efeitos
    merged_data = base_skill.copy()
    rarity_data = base_skill["rarity_effects"].get(rarity, base_skill["rarity_effects"].get("comum", {}))
    merged_data.update(rarity_data)
    
    return merged_data