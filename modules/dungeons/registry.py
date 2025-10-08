# modules/dungeons/registry.py
from __future__ import annotations

def get_dungeon_for_region(region_key: str) -> dict | None:
    """
    Retorna a configuração completa de um calabouço para a região informada.
    Se a região não tiver um calabouço, retorna None.
    """
    
    # --- CALABOUÇO 1: FLORESTA SOMBRIA ---
    if region_key == "floresta_sombria":
        return {
            "display_name": "Calabouço da Floresta Sombria",
            "key_item": "cristal_de_abertura",
            
            # Multiplicadores de stats e recompensas baseados na dificuldade
            "final_gold": {"iniciante": 200, "veterano": 450, "infernal": 800},
            "difficulty_scale": {"iniciante": 1.0, "veterano": 3.0, "infernal": 5.25},
            
            # Lista de andares (monstros e chefe)
            "floors": [
                {
                    "id": "guardiao_raizes",
                    "name": "Guardião de Raízes",
                    "emoji": "🌱",
                    "file_id_name": "guardiao_raizes_media",
                    "hp": 60, "attack": 7, "defense": 10, "initiative": 6, "luck": 16,
                    
                    "loot_table": [
                        
                        {"item_id": "lamina_sagrada", "drop_chance": 0},
                    ],
                },
                {
                    "id": "enxame_de_vagalumes_cortantes",
                    "name": "Enxame de Vagalumes Cortantes",
                    "emoji": "🦟",
                    "file_id_name": "enxame_de_vagalumes_cortantes_media",
                    "hp": 65, "attack": 10, "defense": 7, "initiative": 25, "luck": 30,
                    
                    "loot_table": [
                        {"item_id": "lamina_sagrada", "drop_chance": 0},
                    ],
                },
                {
                    "id": "lobo_alfa_da_matilha",
                    "name": "Lobo Alfa da Matilha",
                    "emoji": "🐺",
                    "file_id_name": "lobo_alfa_da_matilha_media",
                    "hp": 70, "attack": 12, "defense": 9, "initiative": 35, "luck": 30,
                    
                    "loot_table": [
                        {"item_id": "emblema_guerreiro", "drop_chance": 0},
                        
                    ],
                },
                {
                    "id": "ent_protetor",
                    "name": "Ent Protetor",
                    "emoji": "🌳",
                    "file_id_name": "ent_protetor_media",
                    "hp": 75, "attack": 10, "defense": 8, "initiative": 10, "luck": 10,
                    
                    "loot_table": [
                        {"item_id": "emblema_guerreiro", "drop_chance": 0},
                        
                    ],
                },
                {
                    "id": "aranha_gigante_da_tocaia",
                    "name": "Aranha Gigante da Tocaia",
                    "emoji": "🕷️",
                    "file_id_name": "aranha_gigante_da_tocaia_media",
                    "hp": 80, "attack": 12, "defense": 8, "initiative": 20, "luck": 15,
                    
                    "loot_table": [
                        {"item_id": "emblema_guerreiro", "drop_chance": 0},
                        
                    ],
                },
                {
                    "id": "boss_anciao",
                    "name": "O Ancião da Floresta",
                    "emoji": "🌀",
                    "file_id_name": "anciao_floresta_media",
                    "hp": 100, "attack": 10, "defense": 14, "initiative": 18, "luck": 18,
                    "xp_reward": 120, "gold_drop": 120,
                    "is_boss": True,
                    "loot_table": [
                        {"item_id": "emblema_guerreiro", "drop_chance": 3},
                        {"item_id": "essencia_guardia", "drop_chance": 3},
                        {"item_id": "essencia_furia", "drop_chance": 3},
                        {"item_id": "selo_sagrado", "drop_chance": 3},
                        {"item_id": "essencia_luz", "drop_chance": 3},
                        {"item_id": "emblema_berserker", "drop_chance": 3},
                        {"item_id": "totem_ancestral", "drop_chance": 3},
                        {"item_id": "emblema_cacador", "drop_chance": 3},
                        {"item_id": "essencia_precisao", "drop_chance": 3},
                        {"item_id": "marca_predador", "drop_chance": 3},
                        {"item_id": "essencia_fera", "drop_chance": 3},
                        {"item_id": "emblema_monge", "drop_chance": 3},
                        {"item_id": "reliquia_mistica", "drop_chance": 3},
                        {"item_id": "essencia_ki", "drop_chance": 3},
                        {"item_id": "emblema_mago", "drop_chance": 3},
                        {"item_id": "essencia_arcana", "drop_chance": 3},
                        {"item_id": "essencia_elemental", "drop_chance": 3},
                        {"item_id": "grimorio_arcano", "drop_chance": 3},
                        {"item_id": "emblema_bardo", "drop_chance": 3},
                        {"item_id": "essencia_harmonia", "drop_chance": 3},
                        {"item_id": "essencia_encanto", "drop_chance": 3},
                        {"item_id": "batuta_maestria", "drop_chance": 3},
                        {"item_id": "emblema_assassino", "drop_chance": 3},
                        {"item_id": "essencia_sombra", "drop_chance": 3},
                        {"item_id": "essencia_letal", "drop_chance": 3},
                        {"item_id": "manto_eterno", "drop_chance": 3},
                        {"item_id": "emblema_samurai", "drop_chance": 3},
                        {"item_id": "essencia_corte", "drop_chance": 3},
                        {"item_id": "essencia_disciplina", "drop_chance": 3},
                        {"item_id": "lamina_sagrada", "drop_chance": 3},
                    ],
                },
            ],
            
        }

# Adicione este bloco a seguir ao 'if' da floresta_sombria
    elif region_key == "pedreira_granito":
        return {
            "display_name": "Calabouço da Pedreira de Granito",
            "key_item": "cristal_de_abertura", # Pode mudar se quiser uma chave específica
            "final_gold": {"facil": 250, "normal": 500, "infernal": 900},
            "difficulty_scale": {"facil": 2.5, "normal": 4.5, "infernal": 6.0},
            "floors": [
                {
                    "id": "elemental_da_terra_menor",
                    "name": "Elemental da Terra Menor",
                    "emoji": "🗿",
                    "file_id_name": "elemental_da_terra_menor_media",
                    "hp": 80, "attack": 8, "defense": 20, "initiative": 5, "luck": 5,
                    
                },
                {
                    "id": "basilisco_petrificante",
                    "name": "Basilisco Petrificante",
                    "emoji": "🐍",
                    "file_id_name": "basilisco_petrificante_media",
                    "hp": 100, "attack": 12, "defense": 18, "initiative": 40, "luck": 15,
                    
                },
                {
                    "id": "gargula_sentinela",
                    "name": "Gárgula Sentinela",
                    "emoji": "👹",
                    "file_id_name": "gargula_sentinela_media",
                    "hp": 120, "attack": 20, "defense": 18, "initiative": 8, "luck": 10,
                    
                },
                {
                    "id": "troll_da_pedreira",
                    "name": "Troll da Pedreira",
                    "emoji": "👹",
                    "file_id_name": "troll_da_pedreira_media",
                    "hp": 135, "attack": 14, "defense": 12, "initiative": 20, "luck": 20,
                    
                },
                {
                    "id": "verme_de_rocha_blindado",
                    "name": "Verme de rocha Blindado",
                    "emoji": "🐛",
                    "file_id_name": "verme_de_rocha_blindado_media",
                    "hp": 150, "attack": 15, "defense": 15, "initiative": 15, "luck": 25,
                    
                },
                {
                    "id": "colosso_de_granito",
                    "name": "Colosso de Granito (BOSS)",
                    "emoji": "🧌🪨",
                    "file_id_name": "colosso_de_granito_media",
                    "hp": 200, "attack": 18, "defense": 20, "initiative": 12, "luck": 30,
                    "xp_reward": 150, "gold_drop": 250,
                    "is_boss": True,
                    "loot_table": [
                        {"item_id": "emblema_guerreiro", "drop_chance": 3},
                        {"item_id": "essencia_guardia", "drop_chance": 3},
                        {"item_id": "essencia_furia", "drop_chance": 3},
                        {"item_id": "selo_sagrado", "drop_chance": 3},
                        {"item_id": "essencia_luz", "drop_chance": 3},
                        {"item_id": "emblema_berserker", "drop_chance": 3},
                        {"item_id": "totem_ancestral", "drop_chance": 3},
                        {"item_id": "emblema_cacador", "drop_chance": 3},
                        {"item_id": "essencia_precisao", "drop_chance": 3},
                        {"item_id": "marca_predador", "drop_chance": 3},
                        {"item_id": "essencia_fera", "drop_chance": 3},
                        {"item_id": "emblema_monge", "drop_chance": 3},
                        {"item_id": "reliquia_mistica", "drop_chance": 3},
                        {"item_id": "essencia_ki", "drop_chance": 3},
                        {"item_id": "emblema_mago", "drop_chance": 3},
                        {"item_id": "essencia_arcana", "drop_chance": 3},
                        {"item_id": "essencia_elemental", "drop_chance": 3},
                        {"item_id": "grimorio_arcano", "drop_chance": 3},
                        {"item_id": "emblema_bardo", "drop_chance": 3},
                        {"item_id": "essencia_harmonia", "drop_chance": 3},
                        {"item_id": "essencia_encanto", "drop_chance": 3},
                        {"item_id": "batuta_maestria", "drop_chance": 3},
                        {"item_id": "emblema_assassino", "drop_chance": 3},
                        {"item_id": "essencia_sombra", "drop_chance": 3},
                        {"item_id": "essencia_letal", "drop_chance": 3},
                        {"item_id": "manto_eterno", "drop_chance": 3},
                        {"item_id": "emblema_samurai", "drop_chance": 3},
                        {"item_id": "essencia_corte", "drop_chance": 3},
                        {"item_id": "essencia_disciplina", "drop_chance": 3},
                        {"item_id": "lamina_sagrada", "drop_chance": 3},   
                    ],
                },
            ],
        }
    
    return None    