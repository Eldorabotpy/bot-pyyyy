# Em modules/dungeons/regions.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ===================================================================
# 1. A ESTRUTURA DE UM MONSTRO (MobDef)
# Usamos um dataclass para manter tudo organizado.
# ===================================================================
@dataclass
class MobDef:
    key: str  # ID único do monstro, ex: "goblin_arqueiro"
    display: str  # Nome que aparece para o jogador, ex: "Goblin Arqueiro"
    emoji: str = "💀"
    media_key: Optional[str] = None  # Chave para a imagem/vídeo no file_ids.json
    stats_base: Dict[str, int] = field(default_factory=dict) # Stats base (max_hp, attack, etc.)

# ===================================================================
# 2. A DEFINIÇÃO DOS CALABOUÇOS
# Este é o dicionário principal que o registry.py lê.
# ===================================================================
REGIONAL_DUNGEONS = {
    # --- Exemplo de Calabouço para a Floresta Sombria ---
    "pradaria_inicial": {
        "label": "Pradaria dos Slimes",
        "emoji": "🌱",
        "key_item": "cristal_de_abertura", # Item necessário para entrar
        "gold_base": 400, # Recompensa de ouro na dificuldade Normal
        "menu_media_key": "media_calabouco_pradaria_iniciala",
        # A sequência de monstros (6 combates)
        "floors": [
             
            MobDef(
                key="slime_bebe",
                display="Slime Bebé",
                emoji="💧",
                media_key="media_slime_bebe",
                stats_base={"max_hp": 20, 
                            "attack": 3, 
                            "defense": 0, 
                            "initiative": 5, 
                            "luck": 10},
            ),
            MobDef(
                key="slime_verde",
                display="Slime Verde",
                emoji="🟢",
                media_key="slime_verde_media",
                stats_base={"max_hp": 35, 
                            "attack": 4, 
                            "defense": 3, 
                            "initiative": 25, 
                            "luck": 30},
            ),
             MobDef(
                key="slime_azul",
                display="Slime Azul",
                emoji="🔵",
                media_key="slime_azul_media",
                stats_base={"max_hp": 40, 
                            "attack": 5, 
                            "defense": 3, 
                            "initiative": 35, 
                            "luck": 30},
            ),
            MobDef(
                key="slime_vermelho",
                display="Slime Vermelho",
                emoji="🔴",
                media_key="slime_vermelho_media",
                stats_base={"max_hp": 50, 
                            "attack": 6, 
                            "defense": 3, 
                            "initiative": 10, 
                            "luck": 10},
            ),
            MobDef(
                key="slime_pradaria",
                display="Slime da Pradaria",
                emoji="🌿",
                media_key="slime_da_pradaria_media",
                stats_base={"max_hp": 60, 
                            "attack": 7, 
                            "defense": 3, 
                            "initiative": 18, 
                            "luck": 15},
            ),
            # --- 👇 O BOSS (Com a tabela de loot correta) 👇 ---
            MobDef(
                key="rei_slime",
                display="Rei Slime",
                emoji="👑",
                media_key="rei_slime_media",
                stats_base={
                    "max_hp": 80, 
                    "attack": 10, 
                    "defense": 8, 
                    "initiative": 4, 
                    "luck": 3,
                    "is_boss": True,
                    "xp_reward": 80,    # XP base (será multiplicado pela dificuldade)
                    "gold_drop": 25,     # Ouro base (será multiplicado pela dificuldade)
                      
                    # A Tabela de Loot que me enviaste
                    "loot_table": [
                        {"item_id": "emblema_guerreiro", "drop_chance": 8},
                        {"item_id": "essencia_guardia", "drop_chance": 8},
                        {"item_id": "essencia_furia", "drop_chance": 5},
                        {"item_id": "selo_sagrado", "drop_chance": 5},
                        {"item_id": "essencia_luz", "drop_chance": 5},
                        {"item_id": "emblema_berserker", "drop_chance": 5},
                        {"item_id": "totem_ancestral", "drop_chance": 5},
                        {"item_id": "emblema_cacador", "drop_chance": 5},
                        {"item_id": "essencia_precisao", "drop_chance": 5},
                        {"item_id": "marca_predador", "drop_chance": 5},
                        {"item_id": "essencia_fera", "drop_chance": 5},
                        {"item_id": "emblema_monge", "drop_chance": 5},
                        {"item_id": "reliquia_mistica", "drop_chance": 5},
                        {"item_id": "essencia_ki", "drop_chance": 5},
                        {"item_id": "emblema_mago", "drop_chance": 5},
                        {"item_id": "essencia_arcana", "drop_chance": 5},
                        {"item_id": "essencia_elemental", "drop_chance": 5},
                        {"item_id": "grimorio_arcano", "drop_chance": 5},
                        {"item_id": "emblema_bardo", "drop_chance": 5},
                        {"item_id": "essencia_harmonia", "drop_chance": 5},
                        {"item_id": "essencia_encanto", "drop_chance": 5},
                        {"item_id": "batuta_maestria", "drop_chance": 5},
                        {"item_id": "emblema_assassino", "drop_chance": 5},
                        {"item_id": "essencia_sombra", "drop_chance": 5},
                        {"item_id": "essencia_letal", "drop_chance": 5},
                        {"item_id": "manto_eterno", "drop_chance": 5},
                        {"item_id": "emblema_samurai", "drop_chance": 5},
                        {"item_id": "essencia_corte", "drop_chance": 5},
                        {"item_id": "essencia_disciplina", "drop_chance": 5},
                        {"item_id": "lamina_sagrada", "drop_chance": 5},
                   ]
                }
            ),
        ] # <-- Fim da lista "floors"
    }, # <-- Fim do calabouço "floresta_sombria"

    # --- Exemplo de Calabouço para a Floresta Sombria ---
    "floresta_sombria": {
        "label": "Coração da Floresta",
        "emoji": "🌳",
        "key_item": "cristal_de_abertura", # Item necessário para entrar
        "gold_base": 800, # Recompensa de ouro na dificuldade Normal
        "menu_media_key": "media_calabouco_floresta_sombria",
        # A sequência de monstros (6 combates)
        "floors": [
             
            MobDef(
                key="guardiao_raizes",
                display="Guardião de Raízes",
                emoji="🌱",
                media_key="guardiao_raizes_media",
                stats_base={"max_hp": 60, 
                            "attack": 7, 
                            "defense": 10, 
                            "initiative": 16, 
                            "luck": 5},
            ),
            MobDef(
                key="enxame_de_vagalumes_cortantes",
                display="Enxame de Vagalumes Cortantes",
                emoji="🦟",
                media_key="enxame_de_vagalumes_cortantes_media",
                stats_base={"max_hp": 65, 
                            "attack": 18, 
                            "defense": 7, 
                            "initiative": 25, 
                            "luck": 30},
            ),
             MobDef(
                key="lobo_alfa_da_matilha",
                display="Lobo Alfa da Matilha",
                emoji="🐺",
                media_key="lobo_alfa_da_matilha_media",
                stats_base={"max_hp": 70, 
                            "attack": 12, 
                            "defense": 9, 
                            "initiative": 35, 
                            "luck": 30},
            ),
            MobDef(
                key="ent_protetor",
                display="Ent Protetor",
                emoji="🌳",
                media_key="ent_protetor_media",
                stats_base={"max_hp": 70, 
                            "attack": 10, 
                            "defense": 8, 
                            "initiative": 10, 
                            "luck": 10},
            ),
            MobDef(
                key="aranha_gigante_da_tocaia",
                display="Aranha Gigante da Tocaia",
                emoji="🌳",
                media_key="aranha_gigante_da_tocaia_media",
                stats_base={"max_hp": 80, 
                            "attack": 15, 
                            "defense": 10, 
                            "initiative": 18, 
                            "luck": 15},
            ),
            # --- 👇 O BOSS (Com a tabela de loot correta) 👇 ---
            MobDef(
                key="boss_anciao",
                display="O Ancião da Floresta",
                emoji="🌀",
                media_key="anciao_floresta_media",
                stats_base={
                    # Stats de Combate (os que tinhas)
                    "max_hp": 100, 
                    "attack": 10, 
                    "defense": 10, 
                    "initiative": 18, 
                    "luck": 15,
                    "is_boss": True,
                    "xp_reward": 120,    # XP base (será multiplicado pela dificuldade)
                    "gold_drop": 50,     # Ouro base (será multiplicado pela dificuldade)
                      
                    # A Tabela de Loot que me enviaste
                    "loot_table": [
                        {"item_id": "emblema_guerreiro", "drop_chance": 5},
                        {"item_id": "essencia_guardia", "drop_chance": 5},
                        {"item_id": "essencia_furia", "drop_chance": 8},
                        {"item_id": "selo_sagrado", "drop_chance": 8},
                        {"item_id": "essencia_luz", "drop_chance": 5},
                        {"item_id": "emblema_berserker", "drop_chance": 5},
                        {"item_id": "totem_ancestral", "drop_chance": 5},
                        {"item_id": "emblema_cacador", "drop_chance": 5},
                        {"item_id": "essencia_precisao", "drop_chance": 5},
                        {"item_id": "marca_predador", "drop_chance": 5},
                        {"item_id": "essencia_fera", "drop_chance": 5},
                        {"item_id": "emblema_monge", "drop_chance": 5},
                        {"item_id": "reliquia_mistica", "drop_chance": 5},
                        {"item_id": "essencia_ki", "drop_chance": 5},
                        {"item_id": "emblema_mago", "drop_chance": 5},
                        {"item_id": "essencia_arcana", "drop_chance": 5},
                        {"item_id": "essencia_elemental", "drop_chance": 5},
                        {"item_id": "grimorio_arcano", "drop_chance": 5},
                        {"item_id": "emblema_bardo", "drop_chance": 5},
                        {"item_id": "essencia_harmonia", "drop_chance": 5},
                        {"item_id": "essencia_encanto", "drop_chance": 5},
                        {"item_id": "batuta_maestria", "drop_chance": 5},
                        {"item_id": "emblema_assassino", "drop_chance": 5},
                        {"item_id": "essencia_sombra", "drop_chance": 5},
                        {"item_id": "essencia_letal", "drop_chance": 5},
                        {"item_id": "manto_eterno", "drop_chance": 5},
                        {"item_id": "emblema_samurai", "drop_chance": 5},
                        {"item_id": "essencia_corte", "drop_chance": 5},
                        {"item_id": "essencia_disciplina", "drop_chance": 5},
                        {"item_id": "lamina_sagrada", "drop_chance": 5},
                   ]
                }
            ),
        ] # <-- Fim da lista "floors"
    }, # <-- Fim do calabouço "floresta_sombria"
    # --- Exemplo de Calabouço para a Floresta Sombria ---
    "campos_linho": {
        "label": "Onde o vento dança entre as fibras douradas.",
        "emoji": "🌾",
        "key_item": "cristal_de_abertura", # Item necessário para entrar
        "gold_base": 900, # Recompensa de ouro na dificuldade Normal
        "menu_media_key": "media_calabouco_campos_linho",
        # A sequência de monstros (6 combates)
        "floors": [
             
            MobDef(
                key="espirito_da_colheita",
                display="Espírito da Colheita",
                emoji="👻",
                media_key="espírito_da_colheita_media",
                stats_base={"max_hp": 90, 
                            "attack": 28, 
                            "defense": 20, 
                            "initiative": 16, 
                            "luck": 5},
            ),
            MobDef(
                key="lobisomem_alfa",
                display="Lobisomem Alfa",
                emoji="🐺",
                media_key="lobisomem_alfa_media",
                stats_base={"max_hp": 100, 
                            "attack": 28, 
                            "defense": 17, 
                            "initiative": 40, 
                            "luck": 30},
            ),
             MobDef(
                key="banshee_agourenta",
                display="Banshee Agourenta",
                emoji="👹",
                media_key="banshee_agourenta_media",
                stats_base={"max_hp": 110, 
                            "attack": 20, 
                            "defense": 19, 
                            "initiative": 35, 
                            "luck": 30},
            ),
            MobDef(
                key="cavaleiro_de_palha",
                display="Cavaleiro de Palha",
                emoji="🍂",
                media_key="ent_protetor_media",
                stats_base={"max_hp": 130, 
                            "attack": 14, 
                            "defense": 28, 
                            "initiative": 20, 
                            "luck": 20},
            ),
            MobDef(
                key="golem_de_feno",
                display="Golem de Feno",
                emoji="🪨🌾",
                media_key="golem_de_feno_media",
                stats_base={"max_hp": 180, 
                            "attack": 15, 
                            "defense": 15, 
                            "initiative": 15, 
                            "luck": 25},
            ),
            # --- 👇 O BOSS (Com a tabela de loot correta) 👇 ---
            MobDef(
                key="o_rei_espantalho",
                display="O Rei Espantalho (BOSS)",
                emoji="🐉",
                media_key="o_rei_espantalho_media",
                stats_base={
                    # Stats de Combate (os que tinhas)
                    "max_hp": 200, 
                    "attack": 18, 
                    "defense": 18, 
                    "initiative": 28, 
                    "luck": 35,
                    "is_boss": True,
                    "xp_reward": 150,    # XP base (será multiplicado pela dificuldade)
                    "gold_drop": 80,     # Ouro base (será multiplicado pela dificuldade)
                      
                    # A Tabela de Loot que me enviaste
                    "loot_table": [
                        {"item_id": "emblema_guerreiro", "drop_chance": 5},
                        {"item_id": "essencia_guardia", "drop_chance": 5},
                        {"item_id": "essencia_furia", "drop_chance": 5},
                        {"item_id": "selo_sagrado", "drop_chance": 5},
                        {"item_id": "essencia_luz", "drop_chance": 8},
                        {"item_id": "emblema_berserker", "drop_chance": 8},
                        {"item_id": "totem_ancestral", "drop_chance": 5},
                        {"item_id": "emblema_cacador", "drop_chance": 5},
                        {"item_id": "essencia_precisao", "drop_chance": 5},
                        {"item_id": "marca_predador", "drop_chance": 5},
                        {"item_id": "essencia_fera", "drop_chance": 5},
                        {"item_id": "emblema_monge", "drop_chance": 5},
                        {"item_id": "reliquia_mistica", "drop_chance": 5},
                        {"item_id": "essencia_ki", "drop_chance": 5},
                        {"item_id": "emblema_mago", "drop_chance": 5},
                        {"item_id": "essencia_arcana", "drop_chance": 5},
                        {"item_id": "essencia_elemental", "drop_chance": 5},
                        {"item_id": "grimorio_arcano", "drop_chance": 5},
                        {"item_id": "emblema_bardo", "drop_chance": 5},
                        {"item_id": "essencia_harmonia", "drop_chance": 5},
                        {"item_id": "essencia_encanto", "drop_chance": 5},
                        {"item_id": "batuta_maestria", "drop_chance": 5},
                        {"item_id": "emblema_assassino", "drop_chance": 5},
                        {"item_id": "essencia_sombra", "drop_chance": 5},
                        {"item_id": "essencia_letal", "drop_chance": 5},
                        {"item_id": "manto_eterno", "drop_chance": 5},
                        {"item_id": "emblema_samurai", "drop_chance": 5},
                        {"item_id": "essencia_corte", "drop_chance": 5},
                        {"item_id": "essencia_disciplina", "drop_chance": 5},
                        {"item_id": "lamina_sagrada", "drop_chance": 5},
                   ]
                }
            ),
        ] # <-- Fim da lista "floors"
    }, # <-- Fim do calabouço "floresta_sombria"
    "pedreira_granito": {
        "label": "Cuidado onde pisa algumas rochas mordem",
        "emoji": "🪨",
        "key_item": "cristal_de_abertura", # Item necessário para entrar
        "gold_base": 1000, # Recompensa de ouro na dificuldade Normal
        "menu_media_key": "media_calabouco_pedreira_granito",
        # A sequência de monstros (6 combates)
        "floors": [
             
            MobDef(
                key="elemental_da_terra_menor",
                display="Elemental da Terra Menor",
                emoji="🗿",
                media_key="espírito_da_colheita_media",
                stats_base={"max_hp": 150, 
                            "attack": 48, 
                            "defense": 30, 
                            "initiative": 46, 
                            "luck": 55},
            ),
            MobDef(
                key="basilisco_petrificante",
                display="Basilisco Petrificante",
                emoji="🐍",
                media_key="basilisco_petrificante_media",
                stats_base={"max_hp": 165, 
                            "attack": 58, 
                            "defense": 47, 
                            "initiative": 40, 
                            "luck": 30},
            ),
             MobDef(
                key="gargula_sentinela",
                display="Gargula Sentinela",
                emoji="👹",
                media_key="gargula_sentinela_media",
                stats_base={"max_hp": 180, 
                            "attack": 50, 
                            "defense": 49, 
                            "initiative": 55, 
                            "luck": 50},
            ),
            MobDef(
                key="troll_da_pedreira",
                display="Troll da Pedreira",
                emoji="🧌",
                media_key="ent_protetor_media",
                stats_base={"max_hp": 200, 
                            "attack": 14, 
                            "defense": 28, 
                            "initiative": 20, 
                            "luck": 20},
            ),
            MobDef(
                key="verme_de_rocha_blindado",
                display="Verme de Rocha Blindado",
                emoji="🪨🌾",
                media_key="verme_de_rocha_blindado_media",
                stats_base={"max_hp": 220, 
                            "attack": 15, 
                            "defense": 15, 
                            "initiative": 15, 
                            "luck": 25},
            ),
            # --- 👇 O BOSS (Com a tabela de loot correta) 👇 ---
            MobDef(
                key="colosso_de_granito",
                display="colosso_de_granito",
                emoji="🐉",
                media_key="colosso_de_granito_media",
                stats_base={
                    # Stats de Combate (os que tinhas)
                    "max_hp": 250, 
                    "attack": 18, 
                    "defense": 18, 
                    "initiative": 28, 
                    "luck": 35,
                    "is_boss": True,
                    "xp_reward": 180,    # XP base (será multiplicado pela dificuldade)
                    "gold_drop": 80,     # Ouro base (será multiplicado pela dificuldade)
                      
                    # A Tabela de Loot que me enviaste
                    "loot_table": [
                        {"item_id": "emblema_guerreiro", "drop_chance": 5},
                        {"item_id": "essencia_guardia", "drop_chance": 5},
                        {"item_id": "essencia_furia", "drop_chance": 5},
                        {"item_id": "selo_sagrado", "drop_chance": 5},
                        {"item_id": "essencia_luz", "drop_chance": 5},
                        {"item_id": "emblema_berserker", "drop_chance": 5},
                        {"item_id": "totem_ancestral", "drop_chance": 8},
                        {"item_id": "emblema_cacador", "drop_chance": 8},
                        {"item_id": "essencia_precisao", "drop_chance": 5},
                        {"item_id": "marca_predador", "drop_chance": 5},
                        {"item_id": "essencia_fera", "drop_chance": 5},
                        {"item_id": "emblema_monge", "drop_chance": 5},
                        {"item_id": "reliquia_mistica", "drop_chance": 5},
                        {"item_id": "essencia_ki", "drop_chance": 5},
                        {"item_id": "emblema_mago", "drop_chance": 5},
                        {"item_id": "essencia_arcana", "drop_chance": 5},
                        {"item_id": "essencia_elemental", "drop_chance": 5},
                        {"item_id": "grimorio_arcano", "drop_chance": 5},
                        {"item_id": "emblema_bardo", "drop_chance": 5},
                        {"item_id": "essencia_harmonia", "drop_chance": 5},
                        {"item_id": "essencia_encanto", "drop_chance": 5},
                        {"item_id": "batuta_maestria", "drop_chance": 5},
                        {"item_id": "emblema_assassino", "drop_chance": 5},
                        {"item_id": "essencia_sombra", "drop_chance": 5},
                        {"item_id": "essencia_letal", "drop_chance": 5},
                        {"item_id": "manto_eterno", "drop_chance": 5},
                        {"item_id": "emblema_samurai", "drop_chance": 5},
                        {"item_id": "essencia_corte", "drop_chance": 5},
                        {"item_id": "essencia_disciplina", "drop_chance": 5},
                        {"item_id": "lamina_sagrada", "drop_chance": 5},
                   ]
                }
            ),
        ] 
    },
    
    # --- Adicione aqui outros calabouços para outras regiões ---
    # "cavernas_de_gelo": {
    #     "label": "Gruta Congelada",
    #     "emoji": "❄️",
    #     ...
    #     "floors": [
    #         MobDef(...),
    #         MobDef(...),
    #     ]
    # },
}