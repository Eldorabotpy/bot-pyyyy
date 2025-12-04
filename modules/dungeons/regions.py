# Em modules/dungeons/regions.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class MobDef:
    key: str  
    display: str  
    emoji: str = "💀"
    media_key: Optional[str] = None  
    stats_base: Dict[str, int] = field(default_factory=dict) 

REGIONAL_DUNGEONS = {
    
    "pradaria_inicial": {
        "label": "𝙿𝚛𝚊𝚍𝚊𝚛𝚒𝚊 𝚍𝚘𝚜 𝚂𝚕𝚒𝚖𝚎𝚜",
        "emoji": "🌱",
        "key_item": "cristal_de_abertura", 
        "gold_base": 400, 
        "menu_media_key": "media_calabouco_pradaria_iniciala",
        "floors": [
             
            MobDef(
                key="slime_bebe",
                display="𝕊𝕝𝕚𝕞𝕖 𝔹𝕖𝕓𝕖́",
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
                display="𝕊𝕝𝕚𝕞𝕖 𝕍𝕖𝕣𝕕𝕖",
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
                display="𝕊𝕝𝕚𝕞𝕖 𝔸𝕫𝕦𝕝",
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
                display="𝕊𝕝𝕚𝕞𝕖 𝕍𝕖𝕣𝕞𝕖𝕝𝕙𝕠",
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
                display="𝕊𝕝𝕚𝕞𝕖 𝕕𝕒 ℙ𝕣𝕒𝕕𝕒𝕣𝕚𝕒",
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
                display="ℝ𝕖𝕚 𝕊𝕝𝕚𝕞𝕖",
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
        ] 
    }, 

    "floresta_sombria": {
        "label": "𝙲𝚘𝚛𝚊𝚌̧𝚊̃𝚘 𝚍𝚊 𝙵𝚕𝚘𝚛𝚎𝚜𝚝𝚊",
        "emoji": "🌳",
        "key_item": "cristal_de_abertura", 
        "gold_base": 800, 
        "menu_media_key": "media_calabouco_floresta_sombria",
        "floors": [
             
            MobDef(
                key="guardiao_raizes",
                display="𝔾𝕦𝕒𝕣𝕕𝕚𝕒̃𝕠 𝕕𝕖 ℝ𝕒𝕚́𝕫𝕖𝕤",
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
                display="𝔼𝕟𝕩𝕒𝕞𝕖 𝕕𝕖 𝕍𝕒𝕘𝕒𝕝𝕦𝕞𝕖𝕤",
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
                display="𝕃𝕠𝕓𝕠 𝔸𝕝𝕗𝕒",
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
                display="𝔼𝕟𝕥 ℙ𝕣𝕠𝕥𝕖𝕥𝕠𝕣",
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
                display="𝔸𝕣𝕒𝕟𝕙𝕒 𝔾𝕚𝕘𝕒𝕟𝕥𝕖",
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
                display="𝕆 𝔸𝕟𝕔𝕚𝕒̃𝕠 𝕕𝕒 𝔽𝕝𝕠𝕣𝕖𝕤𝕥𝕒",
                emoji="🌀",
                media_key="anciao_floresta_media",
                stats_base={
                    "max_hp": 100, 
                    "attack": 10, 
                    "defense": 10, 
                    "initiative": 18, 
                    "luck": 15,
                    "is_boss": True,
                    "xp_reward": 120,    
                    "gold_drop": 50,
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
        ] 
    }, 
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
    
    # --- Adicione isto ao regions.py logo após a "pedreira_granito" ---
    "pico_grifo": {
        "label": "Pico do Grifo",
        "emoji": "🦅",
        "key_item": "cristal_de_abertura",
        "gold_base": 1200, # Baseado no "infernal" do registry antigo
        "menu_media_key": "media_calabouco_pico_grifo",
        "floors": [
            MobDef(
                key="ninho_de_wyverns",
                display="Ninho de Wyverns",
                emoji="🐉🪺",
                media_key="ninho_de_wyverns_media",
                stats_base={"max_hp": 450, "attack": 28, "defense": 20, "initiative": 15, "luck": 5},
            ),
            MobDef(
                key="manticora_jovem",
                display="Manticora Jovem",
                emoji="🦁",
                media_key="manticora_jovem_media",
                stats_base={"max_hp": 560, "attack": 22, "defense": 18, "initiative": 40, "luck": 15},
            ),
            MobDef(
                key="roc_o_passaro_trovao",
                display="Roc, o Pássaro Trovão",
                emoji="🦤⚡️",
                media_key="roc_o_passaro_provao_media",
                stats_base={"max_hp": 680, "attack": 20, "defense": 18, "initiative": 8, "luck": 10},
            ),
            MobDef(
                key="elemental_da_tempestade",
                display="Elemental da Tempestade",
                emoji="⛈",
                media_key="elemental_da_tempestade_media",
                stats_base={"max_hp": 700, "attack": 14, "defense": 12, "initiative": 20, "luck": 20},
            ),
            MobDef(
                key="gigante_das_nuvens",
                display="Gigante das Nuvens",
                emoji="🌬☁️",
                media_key="gigante_das_nuvens_media",
                stats_base={"max_hp": 850, "attack": 15, "defense": 15, "initiative": 15, "luck": 25},
            ),
            # --- O BOSS ---
            MobDef(
                key="grifo_alfa",
                display="Grifo Alfa",
                emoji="🐦‍🔥",
                media_key="grifo_alfa_media",
                stats_base={
                    "max_hp": 900, "attack": 18, "defense": 20, "initiative": 12, "luck": 30,
                    "is_boss": True,
                    "xp_reward": 150,
                    "gold_drop": 800,
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