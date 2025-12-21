# modules/game_data/class_evolution.py (VERSÃO FINAL COMPLETA)

from __future__ import annotations
from typing import Dict, Any, List

EVOLUTIONS: Dict[str, List[Dict[str, Any]]] = {
    
    # ========================= # CAMINHO DO GUERREIRO # =========================
    "guerreiro": [
        # T2 (Lvl 25)
        { 
            "tier_num": 2, 
            "from": "guerreiro", 
            "to": "cavaleiro", 
            "display_name": "Cavaleiro",
            "min_level": 25,
            "desc": "Defesa elevada e proteção de aliados.",
            
            "ascension_path": [
                {
                    "id": "cav_node_1", 
                    "desc": "Estudar Táticas Defensivas",
                    "cost": {"emblema_guerreiro": 10, "gold": 5000}
                },
                {
                    "id": "cav_node_2",
                    "desc": "Forjar a Primeira Placa",
                    "cost": {"essencia_guardia": 15, "gold": 10000}
                },
                {
                    "id": "cav_node_3",
                    "desc": "Meditação do Guardião",
                    "cost": {"emblema_guerreiro": 15, "essencia_guardia": 10, "gold": 15000}
                }
            ],
            "unlocks_skills": ["evo_knight_aegis"],
            "trial_monster_id": "guardian_of_the_aegis", 
        },
        # T3 (Lvl 40)
        { 
            "tier_num": 3, 
            "from": "cavaleiro", 
            "to": "templario", 
            "display_name": "Templario",
            "min_level": 40,
            "desc": "Paladino sagrado que combina defesa com suporte divino.",
            
            "ascension_path": [
                {
                    "id": "temp_node_1",
                    "desc": "Receber a Bênção da Luz",
                    "cost": {"selo_sagrado": 20, "gold": 25000}
                },
                {
                    "id": "temp_node_2",
                    "desc": "Juramento de Proteção",
                    "cost": {"essencia_luz": 40, "gold": 50000}
                }
            ],
            
            "unlocks_skills": ["evo_templar_divine_light"],
            "trial_monster_id": "aspect_of_the_divine",
        },
        # T4 (Lvl 60)
        { 
            "tier_num": 4, 
            "from": "templario", 
            "to": "guardiao_divino",
            "display_name": "Guardião Divino", 
            "min_level": 60,
            "desc": "Uma fortaleza impenetrável de fé e aço.",
            
            "ascension_path": [
                {
                    "id": "gd_node_1", 
                    "desc": "Dominar a Aura Protetora", 
                    "cost": {"coracao_do_colosso": 30, "gold": 100000}
                },
                {
                    "id": "gd_node_2", 
                    "desc": "Canalizar a Égide", 
                    "cost": {"essencia_luz": 60, "gold": 150000}
                }
            ],
            
            "unlocks_skills": ["evo_divine_guardian_fortress"],
            "trial_monster_id": "divine_sentinel",
        },
        # T5 (Lvl 80)
        { 
            "tier_num": 5, 
            "from": "guardiao_divino", 
            "to": "avatar_da_egide",
            "display_name": "Avatar da Egide",
            "min_level": 80,
            "desc": "A encarnação viva da proteção divina, imune a danos mortais.",
            
            "ascension_path": [
                {
                    "id": "aegis_node_1", 
                    "desc": "Infundir a Alma do Guardião", 
                    "cost": {"alma_do_guardiao": 80, "gold": 250000}
                },
                {
                    "id": "aegis_node_2", 
                    "desc": "Absorver a Luz Pura", 
                    "cost": {"essencia_luz_pura": 80, "gold": 300000}
                }
            ],
            
            "unlocks_skills": ["evo_aegis_avatar_incarnate"],
            "trial_monster_id": "celestial_bastion",
        },
        # T6 (Lvl 100)
        { 
            "tier_num": 6, 
            "from": "avatar_da_egide", 
            "to": "lenda_divina",
            "display_name": "Lenda Divina", 
            "min_level": 100,
            "desc": "Um herói lendário cuja defesa inspira milagres.",
            
            "ascension_path": [
                {
                    "id": "legdiv_node_1", 
                    "desc": "A Provação Divina Final", 
                    "cost": {"essencia_divina_eldora": 100, "gold": 1000000}
                },
                {
                    "id": "legdiv_node_2", 
                    "desc": "Forjar o Fragmento Celestial", 
                    "cost": {"fragmento_celestial": 100, "gold": 1500000}
                }
            ],
            
            "unlocks_skills": ["evo_divine_legend_miracle"],
            "trial_monster_id": "eldora_legend_guard",
        },
    ],

    # ========================= # CAMINHO DO BERSERKER # (JÁ ESTÁ NO FORMATO) # =========================
    "berserker": [
        # T2 (Lvl 25)
        {
            "tier_num": 2, 
            "from": "berserker", 
            "to": "barbaro", 
            "display_name": "Barbaro",
            "min_level": 25,
            "desc": "Dano bruto e resistência a controlo.",
            
            "ascension_path": [
                {
                    "id": "barb_node_1",
                    "desc": "Abraçar a Fúria",
                    "cost": {"emblema_berserker": 25, "gold": 5000}
                },
                {
                    "id": "barb_node_2",
                    "desc": "Sobreviver ao Ritual de Dor",
                    "cost": {"essencia_furia": 25, "gold": 10000}
                }
            ],
            
            "unlocks_skills": ["evo_barbarian_wrath"], 
            "trial_monster_id": "primal_spirit_of_rage",
        },
        # T3 (Lvl 40)
        {
            "tier_num": 3, 
            "from": "barbaro", 
            "to": "selvagem",
            "display_name": "Selvagem",
            "min_level": 40,
            "desc": "Abraça a fúria total, sacrificando defesa por poder de ataque.",
            
            "ascension_path": [
                {
                    "id": "selv_node_1",
                    "desc": "Despertar o Totem Ancestral",
                    "cost": {"totem_ancestral": 20, "gold": 20000}
                },
                {
                    "id": "selv_node_2",
                    "desc": "Canalizar a Dor em Poder",
                    "cost": {"essencia_furia": 40, "gold": 25000}
                },
                {
                    "id": "selv_node_3",
                    "desc": "A Marca do Caos",
                    "cost": {"totem_ancestral": 20, "gold": 30000}
                }
            ],
            
            "unlocks_skills": ["evo_savage_reckless_blows"],
            "trial_monster_id": "avatar_of_primal_wrath",
        },
        # T4 (Lvl 60)
        {
            "tier_num": 4, 
            "from": "selvagem", 
            "to": "ira_primordial",
            "display_name": "Ira Primordial", 
            "min_level": 60,
            "desc": "A própria encarnação da raiva, com ataques que não podem ser defendidos.",
            
            "ascension_path": [
                {
                    "id": "ira_node_1",
                    "desc": "Dominar a Raiva Incontrolável",
                    "cost": {"coracao_da_furia": 30, "gold": 50000}
                },
                {
                    "id": "ira_node_2",
                    "desc": "Tornar-se a Própria Ira",
                    "cost": {"essencia_furia": 60, "gold": 75000}
                }
            ],
            
            "unlocks_skills": ["evo_primal_wrath_armorbreaker"],
            "trial_monster_id": "primal_rage_incarnate",
        },
        # T5 (Lvl 80)
        {
            "tier_num": 5, 
            "from": "ira_primordial", 
            "to": "avatar_da_calamidade", 
            "display_name": "Avatar da Calamidade",
            "min_level": 80,
            "desc": "Um desastre natural ambulante, cuja fúria destrói o mundo.",
            
            "ascension_path": [
                {
                    "id": "calam_node_1",
                    "desc": "Quebrar os Limites Mortais",
                    "cost": {"alma_da_furia": 40, "gold": 100000}
                },
                {
                    "id": "calam_node_2",
                    "desc": "O Grito de Guerra Mundial",
                    "cost": {"essencia_furia_pura": 80, "gold": 150000}
                },
                {
                    "id": "calam_node_3",
                    "desc": "O Ritual Final",
                    "cost": {"alma_da_furia": 40, "gold": 200000}
                }
            ],
            
            "unlocks_skills": ["evo_calamity_shatter_earth"],
            "trial_monster_id": "calamity_bringer",
        },
        # T6 (Lvl 100)
        {
            "tier_num": 6, 
            "from": "avatar_da_calamidade", 
            "to": "deus_da_ira",
            "display_name": "Deus da Ira", 
            "min_level": 100,
            "desc": "A fúria de um deus. Seus golpes quebram a própria realidade.",
            
            "ascension_path": [
                {
                    "id": "deusira_node_1",
                    "desc": "A Provação Divina da Fúria",
                    "cost": {"essencia_divina_eldora": 100, "gold": 1000000}
                },
                {
                    "id": "deusira_node_2",
                    "desc": "Absorver o Fragmento do Caos",
                    "cost": {"fragmento_caos": 100, "gold": 1500000}
                }
            ],
            
            "unlocks_skills": ["evo_wrath_god_undying_rage"],
            "trial_monster_id": "wrath_god_incarnate",
        },
    ],
    
    # ========================= # CAMINHO DO CAÇADOR # =========================
    "cacador": [
        # T2 (Lvl 25)
        {
            "tier_num": 2, 
            "from": "cacador", 
            "to": "franco_atirador",
            "display_name": "Franco Atirador", 
            "min_level": 25,
            "desc": "Especialista em tiros à distância com dano crítico devastador.",
            
            "ascension_path": [
                {
                    "id": "franco_node_1",
                    "desc": "Estudar Pontos Vitais",
                    "cost": {"emblema_cacador": 10, "gold": 5000}
                },
                {
                    "id": "franco_node_2",
                    "desc": "Calibrar o Arco Longo",
                    "cost": {"essencia_precisao": 15, "gold": 10000}
                },
                {
                    "id": "franco_node_3",
                    "desc": "Meditação da Precisão",
                    "cost": {"emblema_cacador": 15, "essencia_precisao": 10, "gold": 15000}
                }
            ],
            
            "unlocks_skills": ["evo_sniper_precision"],
            "trial_monster_id": "phantom_of_the_watchtower",
        },
        # T3 (Lvl 40)
        {
            "tier_num": 3, 
            "from": "franco_atirador", 
            "to": "olho_de_aguia", 
            "display_name": "Olho de Aguia",
            "min_level": 40,
            "desc": "Seus tiros ignoram parcialmente a defesa inimiga.",
            
            "ascension_path": [
                {
                    "id": "aguia_node_1",
                    "desc": "Criar Lentes Infalíveis",
                    "cost": {"lente_infalivel": 20, "gold": 25000}
                },
                {
                    "id": "aguia_node_2",
                    "desc": "Treinar a Visão Penetrante",
                    "cost": {"essencia_precisao": 40, "gold": 50000}
                }
            ],
            
            "unlocks_skills": ["evo_hawkeye_piercing_gaze"],
            "trial_monster_id": "sky_piercer_hawk",
        },
        # T4 (Lvl 60)
        {
            "tier_num": 4, 
            "from": "olho_de_aguia", 
            "to": "atirador_espectral", 
            "display_name": "Atirador Espectral",
            "min_level": 60,
            "desc": "Seus tiros agora ricocheteiam, atingindo múltiplos alvos.",
            
            "ascension_path": [
                {
                    "id": "espec_node_1",
                    "desc": "Infundir o Arco com Ectoplasma",
                    "cost": {"arco_fantasma": 30, "gold": 100000}
                },
                {
                    "id": "espec_node_2",
                    "desc": "Dominar a Flecha Ricochete",
                    "cost": {"essencia_precisao": 60, "gold": 150000}
                }
            ],
            
            "unlocks_skills": ["evo_spectral_ricochet_shot"],
            "trial_monster_id": "spectral_marksman",
        },
        # T5 (Lvl 80)
        {
            "tier_num": 5, 
            "from": "atirador_espectral", 
            "to": "o_horizonte_longinquo",
            "display_name": "O Horizonte Longinquo", 
            "min_level": 80,
            "desc": "Um tiro, um fim. Seu alcance é infinito.",
            
            "ascension_path": [
                {
                    "id": "horiz_node_1",
                    "desc": "Capturar a Alma da Precisão",
                    "cost": {"alma_da_precisao": 80, "gold": 250000}
                },
                {
                    "id": "horiz_node_2",
                    "desc": "O Tiro Interdimensional",
                    "cost": {"essencia_precisao_pura": 80, "gold": 300000}
                }
            ],
            
            "unlocks_skills": ["evo_horizon_endless_shot"],
            "trial_monster_id": "horizon_walker",
        },
        # T6 (Lvl 100)
        {
            "tier_num": 6, 
            "from": "o_horizonte_longinquo", 
            "to": "lenda_do_arco", 
            "display_name": "Lenda do Arco", 
            "min_level": 100,
            "desc": "Suas flechas nunca erram, guiadas pelo próprio vento.",
            
            "ascension_path": [
                {
                    "id": "lendaarco_node_1",
                    "desc": "A Provação Divina da Mira",
                    "cost": {"essencia_divina_eldora": 100, "gold": 1000000}
                },
                {
                    "id": "lendaarco_node_2",
                    "desc": "A Flecha Celestial",
                    "cost": {"fragmento_celestial": 100, "gold": 1500000}
                }
            ],
            
            "unlocks_skills": ["evo_legend_phantom_wind"],
            "trial_monster_id": "legend_of_the_bow",
        },
    ],
    
    # ========================= # CAMINHO DO MONGE # =========================
    "monge": [
        # T2 (Lvl 25)
        {
            "tier_num": 2, 
            "from": "monge", 
            "to": "punho_elemental",
            "display_name": "Punho Elemental", 
            "min_level": 25,
            "desc": "Lutador que canaliza a fúria dos elementos nos seus punhos.",
            
            "ascension_path": [
                {
                    "id": "punelem_node_1",
                    "desc": "Despertar o Ki Interior",
                    "cost": {"emblema_monge": 10, "gold": 5000}
                },
                {
                    "id": "punelem_node_2",
                    "desc": "Infundir Punhos com Ki",
                    "cost": {"essencia_ki": 15, "gold": 10000}
                },
                {
                    "id": "punelem_node_3",
                    "desc": "Alcançar o Equilíbrio Elemental",
                    "cost": {"emblema_monge": 15, "essencia_ki": 10, "gold": 15000}
                }
            ],
            
            "unlocks_skills": ["evo_elemental_fist_attunement"],
            "trial_monster_id": "avatar_of_the_four_elements",
        },
        # T3 (Lvl 40)
        {
            "tier_num": 3, 
            "from": "punho_elemental", 
            "to": "ascendente",
            "display_name": "Ascendente",  
            "min_level": 40,
            "desc": "Atingiu a transcendência, movendo-se como o vento.",
            
            "ascension_path": [
                {
                    "id": "asc_node_1",
                    "desc": "Meditar sobre a Relíquia Mística",
                    "cost": {"reliquia_mistica": 20, "gold": 25000}
                },
                {
                    "id": "asc_node_2",
                    "desc": "Alcançar a Verdadeira Transcendência",
                    "cost": {"essencia_ki": 40, "gold": 50000}
                }
            ],
            
            "unlocks_skills": ["evo_ascendant_gait"],
            "trial_monster_id": "echo_of_the_grandmaster",
        },
        # T4 (Lvl 60)
        {
            "tier_num": 4, 
            "from": "ascendente", 
            "to": "punho_divino", 
            "display_name": "Punho Divino", 
            "min_level": 60,
            "desc": "Seu Ki é tão puro que seus golpes causam dano sagrado.",
            
            "ascension_path": [
                {
                    "id": "pundiv_node_1",
                    "desc": "Decifrar o Pergaminho Celestial",
                    "cost": {"pergaminho_celestial": 30, "gold": 100000}
                },
                {
                    "id": "pundiv_node_2",
                    "desc": "Canalizar o Ki Divino",
                    "cost": {"essencia_ki": 60, "gold": 150000}
                }
            ],
            
            "unlocks_skills": ["evo_divine_fist_strike"],
            "trial_monster_id": "divine_hand",
        },
        # T5 (Lvl 80)
        {
            "tier_num": 5, 
            "from": "punho_divino", 
            "to": "o_dragao_interior", 
            "display_name": "O Dragão Interior", 
            "min_level": 80,
            "desc": "Libera o dragão interior, o mestre supremo das artes marciais.",
            
            "ascension_path": [
                {
                    "id": "dragao_node_1",
                    "desc": "Confrontar o Dragão Interior",
                    "cost": {"alma_do_ki": 80, "gold": 250000}
                },
                {
                    "id": "dragao_node_2",
                    "desc": "Absorver a Essência Pura do Ki",
                    "cost": {"essencia_ki_pura": 80, "gold": 300000}
                }
            ],
            
            "unlocks_skills": ["evo_inner_dragon_unleashed"], 
            "trial_monster_id": "inner_dragon_spirit",
        },
        # T6 (Lvl 100)
        {
            "tier_num": 6, 
            "from": "o_dragao_interior", 
            "to": "lenda_do_punho", 
            "display_name": "Lenda do punho", 
            "min_level": 100,
            "desc": "Um com o universo. Seus golpes são o próprio equilíbrio.",
            
            "ascension_path": [
                {
                    "id": "lendapunho_node_1",
                    "desc": "A Provação Divina do Equilíbrio",
                    "cost": {"essencia_divina_eldora": 100, "gold": 1000000}
                },
                {
                    "id": "lendapunho_node_2",
                    "desc": "O Punho Celestial",
                    "cost": {"fragmento_celestial": 100, "gold": 1500000}
                }
            ],
            
            "unlocks_skills": ["evo_fist_legend_balance"],
            "trial_monster_id": "legend_of_the_fist",
        },
    ],
    
    # ========================= # CAMINHO DO MAGO # (JÁ ESTÁ NO FORMATO) # =========================
    "mago": [
        # T2 (Lvl 25)
        {
            "tier_num": 2, 
            "from": "mago", 
            "to": "elementalista", 
            "display_name": "Elementalista", 
            "min_level": 25,
            "desc": "Especialista em dano elemental massivo e em área.",
            
            "ascension_path": [
                {
                    "id": "elem_node_1",
                    "desc": "Estudar os Fundamentos Arcanos",
                    "cost": {"emblema_mago": 10, "gold": 5000}
                },
                {
                    "id": "elem_node_2",
                    "desc": "Dominar a Primeira Essência",
                    "cost": {"essencia_elemental": 15, "gold": 10000}
                },
                {
                    "id": "elem_node_3",
                    "desc": "Sintonização Elemental",
                    "cost": {"emblema_mago": 15, "essencia_elemental": 10, "gold": 15000}
                }
            ],
            
            "unlocks_skills": ["evo_elementalist_power"], 
            "trial_monster_id": "raging_elemental_vortex",
        },
        # T3 (Lvl 40)
        {
            "tier_num": 3, 
            "from": "elementalista", 
            "to": "arquimago", 
            "display_name": "Arquuimago", 
            "min_level": 40,
            "desc": "Um canal de poder arcano puro, mestre de todos os elementos.",
            
            "ascension_path": [
                {
                    "id": "arq_node_1",
                    "desc": "Decifrar o Grimório Arcano",
                    "cost": {"grimorio_arcano": 20, "gold": 25000}
                },
                {
                    "id": "arq_node_2",
                    "desc": "Alinhar os Focos Elementais",
                    "cost": {"essencia_elemental": 40, "gold": 50000}
                }
            ],
            
            "unlocks_skills": ["evo_archmage_elemental_weave"], 
            "trial_monster_id": "essence_of_pure_magic",
        },
        # T4 (Lvl 60)
        {
            "tier_num": 4, 
            "from": "arquimago", 
            "to": "mago_de_batalha",
            "display_name": "Mago de Batalha", 
            "min_level": 60,
            "desc": "Combina magia elemental com defesa arcana, lutando na linha de frente.",
            
            "ascension_path": [
                {
                    "id": "battlemage_node_1",
                    "desc": "Infundir o Foco Cristalino",
                    "cost": {"foco_cristalino": 30, "gold": 100000}
                },
                {
                    "id": "battlemage_node_2",
                    "desc": "Dominar a Armadura Arcana",
                    "cost": {"essencia_elemental": 60, "gold": 150000}
                }
            ],
            
            "unlocks_skills": ["evo_battlemage_mana_shield"], 
            "trial_monster_id": "battlemage_prime",
        },
        # T5 (Lvl 80)
        {
            "tier_num": 5, 
            "from": "mago_de_batalha", 
            "to": "arcanista_supremo",
            "display_name": "Arcanista Supremo", 
            "min_level": 80,
            "desc": "Transcendeu a magia, tornando-se a própria magia.",
            
            "ascension_path": [
                {
                    "id": "arcano_node_1",
                    "desc": "Absorver a Alma Elemental",
                    "cost": {"alma_elemental": 80, "gold": 250000}
                },
                {
                    "id": "arcano_node_2",
                    "desc": "Controlar a Essência Elemental Pura",
                    "cost": {"essencia_elemental_pura": 80, "gold": 300000}
                }
            ],
            
            "unlocks_skills": ["evo_arcanist_overcharge"], 
            "trial_monster_id": "supreme_arcanist",
        },
        # T6 (Lvl 100)
        {
            "tier_num": 6, 
            "from": "arcanista_supremo", 
            "to": "aspecto_arcano", 
            "display_name": "Aspecto Arcano", 
            "min_level": 100,
            "desc": "A realidade se dobra à sua vontade. Um deus da magia.",
            
            "ascension_path": [
                {
                    "id": "aspect_node_1",
                    "desc": "A Provação Divina do Conhecimento",
                    "cost": {"essencia_divina_eldora": 100, "gold": 1000000}
                },
                {
                    "id": "aspect_node_2",
                    "desc": "Absorver o Fragmento Arcano",
                    "cost": {"fragmento_arcano": 100, "gold": 1500000}
                }
            ],
            
            "unlocks_skills": ["evo_arcane_aspect_singularity"], 
            "trial_monster_id": "arcane_aspect",
        },
    ],
    
    # ========================= # CAMINHO DO BARDO # (JÁ ESTÁ NO FORMATO) # =========================
    "bardo": [
        # T2 (Lvl 25)
        {
            "tier_num": 2, 
            "from": "bardo", 
            "to": "menestrel",
            "display_name": "Menestrel",  
            "min_level": 25,
            "desc": "Foco em canções de suporte e inspiração para a equipe.",
        
            "ascension_path": [
                {
                    "id": "menestrel_node_1",
                    "desc": "Aprender as Primeiras Melodias",
                    "cost": {"emblema_bardo": 10, "gold": 5000}
                },
                {
                    "id": "menestrel_node_2",
                    "desc": "Dominar a Lira de Batalha",
                    "cost": {"corda_encantada": 15, "gold": 10000}
                },
                {
                    "id": "menestrel_node_3",
                    "desc": "Performance em Público",
                    "cost": {"emblema_bardo": 15, "corda_encantada": 10, "gold": 15000}
                }
            ],
        
            "unlocks_skills": ["evo_minstrel_healing_note"], 
            "trial_monster_id": "silencing_critics",
        },
        # T3 (Lvl 40)
        {
            "tier_num": 3, 
            "from": "menestrel", 
            "to": "trovador", 
            "display_name": "Trovador", 
            "min_level": 40,
            "desc": "Especialista em controlar o campo de batalha com canções hipnóticas.",
        
            "ascension_path": [
                {
                    "id": "trovador_node_1",
                    "desc": "Decifrar Partituras Antigas",
                    "cost": {"partitura_antiga": 20, "gold": 25000}
                },
                {
                    "id": "trovador_node_2",
                    "desc": "Afinar a Voz Mágica",
                    "cost": {"corda_encantada": 40, "gold": 50000}
                }
            ],
        
            "unlocks_skills": ["evo_troubadour_hypnotic_lullaby"], 
            "trial_monster_id": "deafening_silence",
        },
        # T4 (Lvl 60)
        {
            "tier_num": 4, 
            "from": "trovador", 
            "to": "mestre_de_concerto", 
            "display_name": "Mestre de Concerto", 
            "min_level": 60,
            "desc": "Transforma a música em dano sonoro puro e barreiras protetoras.",
        
            "ascension_path": [
                {
                    "id": "mestre_node_1",
                    "desc": "Infusão de Ressonância",
                    "cost": {"cristal_sonoro": 30, "gold": 100000}
                },
                {
                    "id": "mestre_node_2",
                    "desc": "Conduzir a Sinfonia",
                    "cost": {"corda_encantada": 60, "gold": 150000}
                }
            ],
        
            "unlocks_skills": ["evo_maestro_barrier_sonata"], 
            "trial_monster_id": "unruly_orchestra",
        },
        # T5 (Lvl 80)
        {
            "tier_num": 5, 
            "from": "mestre_de_concerto", 
            "to": "harmonista", 
            "display_name": "Harmonista", 
            "min_level": 80,
            "desc": "Um mestre da harmonia, capaz de equilibrar o suporte e o ataque.",
        
            "ascension_path": [
                {
                    "id": "harmonista_node_1",
                    "desc": "Absorver o Espírito da Música",
                    "cost": {"espirito_musica": 80, "gold": 250000}
                },
                {
                    "id": "harmonista_node_2",
                    "desc": "Controlar a Frequência Pura",
                    "cost": {"frequencia_pura": 80, "gold": 300000}
                }
            ],
        
            "unlocks_skills": ["evo_harmonist_grand_overture"], 
            "trial_monster_id": "chaotic_harmony",
        },
        # T6 (Lvl 100)
        {
            "tier_num": 6, 
            "from": "harmonista", 
            "to": "aspecto_musical", 
            "display_name": "Aspecto Musical", 
            "min_level": 100,
            "desc": "A encarnação do som, sua música reescreve a realidade.",
        
            "ascension_path": [
                {
                    "id": "aspect_node_1",
                    "desc": "A Provação Divina da Criação",
                    "cost": {"essencia_divina_eldora": 100, "gold": 1000000}
                },
                {
                    "id": "aspect_node_2",
                    "desc": "Absorver o Fragmento da Melodia Original",
                    "cost": {"fragmento_melodia": 100, "gold": 1500000}
                }
            ],
        
            "unlocks_skills": ["evo_aspect_primordial_symphony"], 
            "trial_monster_id": "primordial_symphony",
        },
    ],
    
    # ========================= # CAMINHO DO ASSASSINO # (JÁ ESTÁ NO FORMATO) # =========================
    "assassino": [
        # T2 (Lvl 25)
        { 
            "tier_num": 2, 
            "from": "assassino", 
            "to": "ladrao_de_sombras", 
            "display_name": "Ladrão de Sombras", 
            "min_level": 25,
            "desc": "Especialista em furtividade e ataques de oportunidade com dano extra.",
        
            "ascension_path": [
                {
                    "id": "shadow_node_1",
                    "desc": "Dominar a Arte da Furtividade",
                    "cost": {"emblema_assassino": 10, "gold": 5000}
                },
                {
                    "id": "shadow_node_2",
                    "desc": "Aprimoramento da Lâmina Oculta",
                    # CORRIGIDO: lâmina -> lamina
                    "cost": {"lamina_afiada": 15, "gold": 10000}
                },
                {
                    "id": "shadow_node_3",
                    "desc": "Transição para as Sombras",
                    # CORRIGIDO: lâmina -> lamina
                    "cost": {"emblema_assassino": 15, "lamina_afiada": 10, "gold": 15000}
                }
            ],
        
            "unlocks_skills": ["evo_shadow_thief_ambush"], 
            "trial_monster_id": "doppelganger_of_the_throne",
        },
        # T3 (Lvl 40)
        {
            "tier_num": 3, 
            "from": "ladrao_de_sombras", 
            "to": "ninja", 
            "display_name": "Ninja", 
            "min_level": 40,
            "desc": "Foco em velocidade, agilidade e uso de venenos e ferramentas táticas.",
        
            "ascension_path": [
                {
                    "id": "ninja_node_1",
                    "desc": "Aprender a Técnica de Substituição",
                    "cost": {"poeira_sombria": 20, "gold": 25000}
                },
                {
                    "id": "ninja_node_2",
                    "desc": "Infusão de Veneno Letal",
                    "cost": {"essencia_venenosa": 40, "gold": 50000}
                }
            ],
        
            "unlocks_skills": ["evo_ninja_poison_arts"], 
            "trial_monster_id": "quick_phantom",
        },
        # T4 (Lvl 60)
        {
            "tier_num": 4, 
            "from": "ninja",  
            "to":"mestre_das_laminas",
            "display_name": "Mestre das Laminas",  
            "min_level": 60,
            "desc": "Transforma o Assassino em um duelista mortal com foco em ataques críticos.",
        
            "ascension_path": [
                {
                    "id": "blade_master_node_1",
                    "desc": "Forjar a Lâmina Eterna",
                    # CORRIGIDO: aço -> aco
                    "cost": {"aco_sombrio": 30, "gold": 100000}
                },
                {
                    "id": "blade_master_node_2",
                    "desc": "Sexto Sentido Mortal",
                    "cost": {"essencia_venenosa": 60, "gold": 150000}
                }
            ],
        
            "unlocks_skills": ["evo_blademaster_focus"], 
            "trial_monster_id": "dual_wielding_ronin",
        },
        # T5 (Lvl 80)
        {
            "tier_num": 5, 
            "from": "mestre_das_laminas", 
            "to": "ceifador", 
            "display_name": "Ceifador", 
            "min_level": 80,
            "desc": "Canaliza a energia da morte, garantindo que nenhum alvo escape de seu destino.",
        
            "ascension_path": [
                {
                    "id": "reaper_node_1",
                    "desc": "Absorver a Energia Kármica",
                    "cost": {"energia_karmica": 80, "gold": 250000}
                },
                {
                    "id": "reaper_node_2",
                    "desc": "Controlar a Névoa da Morte",
                    "cost": {"nevoa_da_morte": 80, "gold": 300000}
                }
            ],
        
            "unlocks_skills": ["evo_reaper_mark_of_death"], 
            "trial_monster_id": "shadow_of_fate",
        },
        # T6 (Lvl 100)
        {
            "tier_num": 6, 
            "from": "ceifador", 
            "to": "aspecto_da_noite", 
            "display_name": "Aspecto de Noite", 
            "min_level": 100,
            "desc": "Tornou-se um com o manto da noite, capaz de eliminar qualquer criatura em um instante.",
        
            "ascension_path": [
                {
                    "id": "aspect_night_node_1",
                    "desc": "A Provação Divina da Sombra",
                    "cost": {"essencia_divina_eldora": 100, "gold": 1000000}
                },
                {
                    "id": "aspect_night_node_2",
                    "desc": "Absorver o Fragmento da Escuridão Pura",
                    "cost": {"fragmento_escuridao": 100, "gold": 1500000}
                }
            ],
        
            "unlocks_skills": ["evo_night_aspect_invisibility"], 
            "trial_monster_id": "avatar_of_the_void",
        },
    ],
    
    # ========================= # CAMINHO DO SAMURAI # (NOVO NO FORMATO) # =========================
    "samurai": [
        # T2 (Lvl 25)
        {
            "tier_num": 2, 
            "from": "samurai", 
            "to": "ronin", 
            "display_name": "Ronin", 
            "min_level": 25,
            "desc": "Um guerreiro errante focado em golpes rápidos e críticos de sobrevivência.",
            
            "ascension_path": [
                {
                    "id": "ronin_node_1",
                    "desc": "Aprender o Caminho do Sem-Mestre",
                    "cost": {"emblema_samurai": 10, "gold": 5000}
                },
                {
                    "id": "ronin_node_2",
                    "desc": "Forjar a Primeira Katana de Batalha",
                    "cost": {"aco_tamahagane": 15, "gold": 10000}
                },
                {
                    "id": "ronin_node_3",
                    "desc": "Foco na Meditação",
                    "cost": {"emblema_samurai": 15, "aco_tamahagane": 10, "gold": 15000}
                }
            ],
            
            "unlocks_skills": ["evo_ronin_wanderers_focus"], 
            "trial_monster_id": "phantom_of_the_dojo",
        },
        # T3 (Lvl 40)
        {
            "tier_num": 3, 
            "from": "ronin", 
            "to": "kenshi",
            "display_name": "Kenshi",  
            "min_level": 40,
            "desc": "Um Mestre da Espada que domina técnicas de corte aprimoradas e parry.",
            
            "ascension_path": [
                {
                    "id": "kenshi_node_1",
                    "desc": "Decifrar os Tomos do Kendo",
                    "cost": {"tomo_bushido": 20, "gold": 25000}
                },
                {
                    "id": "kenshi_node_2",
                    "desc": "Dominar o Iaijutsu (Saque Rápido)",
                    "cost": {"aco_tamahagane": 40, "gold": 50000}
                }
            ],
            
            "unlocks_skills": ["evo_kenshi_perfect_parry"], 
            "trial_monster_id": "master_swordsman_phantom",
        },
        # T4 (Lvl 60)
        {
            "tier_num": 4, 
            "from": "kenshi", 
            "to": "shogunato", 
            "display_name": "Shogunato", 
            "min_level": 60,
            "desc": "Guerreiro com capacidade de liderança, que inspira ou intimida seus aliados e inimigos.",
            
            "ascension_path": [
                {
                    "id": "shogun_node_1",
                    "desc": "Forjar a Armadura do Comandante",
                    "cost": {"placa_forjada": 30, "gold": 100000}
                },
                {
                    "id": "shogun_node_2",
                    "desc": "Aprender a Arte da Guerra",
                    "cost": {"tomo_bushido": 60, "gold": 150000}
                }
            ],
            
            "unlocks_skills": ["evo_shogun_banner_of_war"], 
            "trial_monster_id": "heavy_armored_general",
        },
        # T5 (Lvl 80)
        {
            "tier_num": 5, 
            "from": "shogunato", 
            "to": "mestre_de_bushido", 
            "display_name": "Mestre de Bushido", 
            "min_level": 80,
            "desc": "Alcançou a perfeição do bushido, focando em técnica e ataques de precisão final.",
            
            "ascension_path": [
                {
                    "id": "bushido_node_1",
                    "desc": "Unir Mente e Lâmina",
                    "cost": {"alma_katana": 80, "gold": 250000}
                },
                {
                    "id": "bushido_node_2",
                    "desc": "Dominar a Respiração Focada",
                    "cost": {"aura_bushido": 80, "gold": 300000}
                }
            ],
            
            "unlocks_skills": ["evo_bushido_final_cut"], 
            "trial_monster_id": "spirit_of_honor",
        },
        # T6 (Lvl 100)
        {
            "tier_num": 6, 
            "from": "mestre_de_bushido", 
            "to": "aspecto_da_lamina", 
            "display_name": "Aspecto da Lamina", 
            "min_level": 100,
            "desc": "Sua lâmina é a própria manifestação da vontade. Um corte que transcende a realidade.",
            
            "ascension_path": [
                {
                    "id": "aspect_blade_node_1",
                    "desc": "A Provação Divina da Disciplina",
                    "cost": {"essencia_divina_eldora": 100, "gold": 1000000}
                },
                {
                    "id": "aspect_blade_node_2",
                    "desc": "Absorver o Fragmento da Espada Original",
                    "cost": {"fragmento_espada_original": 100, "gold": 1500000}
                }
            ],
            
            "unlocks_skills": ["evo_blade_aspect_presence"], 
            "trial_monster_id": "divine_blade_incarnate",
        },
    ],
    
    # ========================= # CAMINHO DO CURANDEIRO # (ADICIONADO NO FORMATO) # =========================
    "curandeiro": [
        # T2 (Lvl 25)
        {
            "tier_num": 2, 
            "from": "curandeiro", 
            "to": "clerigo", 
            "display_name": "clerigo", 
            "min_level": 25,
            "desc": "Foco em magias de cura de alvo único e purificação.",
            
            "ascension_path": [
                {
                    "id": "cleric_node_1",
                    "desc": "Aprender o Toque Divino",
                    "cost": {"emblema_cura": 10, "gold": 5000}
                },
                {
                    "id": "cleric_node_2",
                    "desc": "Infusão da Primeira Fé",
                    "cost": {"essencia_fe": 15, "gold": 10000}
                },
                {
                    "id": "cleric_node_3",
                    "desc": "Jurar a Pureza",
                    "cost": {"emblema_cura": 15, "essencia_fe": 10, "gold": 15000}
                }
            ],
            
            "unlocks_skills": ["evo_cleric_divine_light"],
            "trial_monster_id": "plague_carrier_specter",
        },
        # T3 (Lvl 40)
        {
            "tier_num": 3, 
            "from": "clerigo", 
            "to": "sacerdote",
            "display_name": "Sacerdote",  
            "min_level": 40,
            "desc": "Especialista em cura em área e fortalecimento de defesas aliadas.",
            
            "ascension_path": [
                {
                    "id": "priest_node_1",
                    "desc": "Decifrar o Pergaminho Sagrado",
                    "cost": {"pergaminho_sagrado": 20, "gold": 25000}
                },
                {
                    "id": "priest_node_2",
                    "desc": "Aumentar a Aura de Cura",
                    "cost": {"essencia_fe": 40, "gold": 50000}
                }
            ],
            
            "unlocks_skills": ["evo_priest_holy_ground"],
            "trial_monster_id": "unholy_inquisitor",
        },
        # T4 (Lvl 60)
        {
            "tier_num": 4, 
            "from": "sacerdote", 
            "to": "hierofante", 
            "display_name": "Hierofante", 
            "min_level": 60,
            "desc": "Seu toque restaura até a vida perdida, revertendo o dano.",
            
            "ascension_path": [
                {
                    "id": "hiero_node_1",
                    "desc": "Infusão do Cálice da Luz",
                    "cost": {"calice_da_luz": 30, "gold": 100000}
                },
                {
                    "id": "hiero_node_2",
                    "desc": "Dominar a Magia Reversa",
                    "cost": {"essencia_fe": 60, "gold": 150000}
                }
            ],
            
            "unlocks_skills": ["evo_hierophant_divine_aegis"],
            "trial_monster_id": "avatar_of_restoration",
        },
        # T5 (Lvl 80)
        {
            "tier_num": 5, 
            "from": "hierofante", 
            "to": "oraculo_celestial", 
            "display_name": "Oraculo Celestial", 
            "min_level": 80,
            "desc": "Pode prever e anular ataques. Sua fé se manifesta como escudo de luz.",
            
            "ascension_path": [
                {
                    "id": "oracle_node_1",
                    "desc": "Capturar a Alma da Fé",
                    "cost": {"alma_da_fe": 80, "gold": 250000}
                },
                {
                    "id": "oracle_node_2",
                    "desc": "Absorver a Essência Pura da Fé",
                    "cost": {"essencia_fe_pura": 80, "gold": 300000}
                }
            ],
            
            "unlocks_skills": ["evo_celestial_oracle_preservation"],
            "trial_monster_id": "void_prophet",
        },
        # T6 (Lvl 100)
        {
            "tier_num": 6, 
            "from": "oraculo_celestial", 
            "to": "lenda_da_cura",
            "display_name": "Lenda da Cura",  
            "min_level": 100,
            "desc": "A própria luz da esperança. Capaz de ressuscitar aliados e curar o impossível.",
            
            "ascension_path": [
                {
                    "id": "legendcura_node_1",
                    "desc": "A Provação Divina da Esperança",
                    "cost": {"essencia_divina_eldora": 100, "gold": 1000000}
                },
                {
                    "id": "legendcura_node_2",
                    "desc": "O Milagre Final",
                    "cost": {"fragmento_celestial": 100, "gold": 1500000}
                }
            ],
            
            "unlocks_skills": ["evo_healing_legend_miracle"],
            "trial_monster_id": "divine_healer_legend",
        },
    ],
}

# =======================================================
# --- FUNÇÕES DE BUSCA (ATUALIZADAS) ---
# =======================================================

def get_evolution_options(
    current_class: str,
    current_level: int,
    show_locked: bool = True,
) -> List[dict]:
    """
    Retorna a PRÓXIMA opção de evolução disponível para a classe atual.
    """
    current_class = (current_class or "").lower()
    
    # Busca a classe base no mapa de hierarquia
    base_class = _CLASS_HIERARCHY_MAP.get(current_class)
    if not base_class:
        return [] 

    evolutions = EVOLUTIONS.get(base_class, [])
    if not evolutions:
        return []

    # Encontra a evolução onde "from" == classe atual
    next_evolution = None
    for evo in evolutions:
        if evo.get("from") == current_class:
            next_evolution = evo
            break
            
    if not next_evolution:
        return [] 

    min_lvl = int(next_evolution.get("min_level", 999))
    if show_locked or current_level >= min_lvl:
        return [next_evolution] 
        
    return []

def find_evolution_by_target(target_class: str) -> Dict[str, Any] | None:
    """
    Encontra a definição de uma evolução pela sua classe "alvo" (o "to").
    Ex: "templario" -> retorna o dicionário da evolução T3 do Guerreiro.
    """
    if not target_class:
        return None
        
    target_class_lower = target_class.lower()
    
    # Procura em todas as árvores de evolução
    for base_class, evolutions in EVOLUTIONS.items():
        for evo_option in evolutions:
            if evo_option.get("to") == target_class_lower:
                return evo_option # Encontrou!
                
    return None # Não encontrou a definição

# =======================================================
# --- MAPAS DE HIERARQUIA (GERAÇÃO AUTOMÁTICA) ---
# =======================================================

_CLASS_HIERARCHY_MAP: Dict[str, str] = {}
_DIRECT_PARENT_MAP: Dict[str, str] = {}

def _build_maps():
    """Constrói os mapas de hierarquia de classes."""
    global _CLASS_HIERARCHY_MAP, _DIRECT_PARENT_MAP
    
    if _CLASS_HIERARCHY_MAP: return # Já construído
    
    for base_class, evolutions in EVOLUTIONS.items():
        # A classe base aponta para si mesma
        _CLASS_HIERARCHY_MAP[base_class] = base_class
        
        current_parent = base_class
        
        # Ordena evoluções por tier para garantir a cadeia correta
        sorted_evos = sorted(evolutions, key=lambda x: x.get("tier_num", 0))
        
        for evo in sorted_evos:
            to_class = evo.get("to")
            from_class = evo.get("from")
            
            if to_class:
                # Todos apontam para a base (para achar a lista correta)
                _CLASS_HIERARCHY_MAP[to_class] = base_class
                
                # Mapa direto de parentesco (Filho -> Pai)
                if from_class:
                    _DIRECT_PARENT_MAP[to_class] = from_class

# Executa a construção ao carregar o módulo
_build_maps()

def get_class_ancestry(current_class: str) -> List[str]:
    """Retorna a cadeia de evolução do jogador: [classe_atual, pai, avô, base]"""
    ancestry = []
    current = (current_class or "").lower()
    
    # Evita loop infinito com limite de segurança
    safety_limit = 10
    
    while current and safety_limit > 0:
        if current in ancestry: break # Loop detectado
        ancestry.append(current)
        
        parent = _DIRECT_PARENT_MAP.get(current)
        if not parent or parent == current:
            break
        current = parent
        safety_limit -= 1
    
    return ancestry

def can_player_use_skill(player_class_key: str, allowed_classes: List[str]) -> bool:
    """
    Verifica se o jogador pode usar a skill verificando a classe atual 
    E TODA A SUA CADEIA DE EVOLUÇÃO.
    """
    if not allowed_classes:
        return True 
    
    player_class_key = player_class_key.lower()
    ancestry = get_class_ancestry(player_class_key)
    allowed_classes_lower = {c.lower() for c in allowed_classes}

    for class_node in ancestry:
        if class_node in allowed_classes_lower:
            return True

    return False