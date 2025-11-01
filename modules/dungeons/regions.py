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
                stats_base={"max_hp": 60, "attack": 7, "defense": 10, "initiative": 16, "luck": 5},
            ),
            MobDef(
                key="enxame_de_vagalumes_cortantes",
                display="Enxame de Vagalumes Cortantes",
                emoji="🦟",
                media_key="enxame_de_vagalumes_cortantes_media",
                stats_base={"max_hp": 65, "attack": 18, "defense": 7, "initiative": 25, "luck": 30},
            ),
             MobDef(
                key="lobo_alfa_da_matilha",
                display="Lobo Alfa da Matilha",
                emoji="🐺",
                media_key="lobo_alfa_da_matilha_media",
                stats_base={"max_hp": 70, "attack": 12, "defense": 9, "initiative": 35, "luck": 30},
            ),
            MobDef(
                key="ent_protetor",
                display="Ent Protetor",
                emoji="🌳",
                media_key="ent_protetor_media",
                stats_base={"max_hp": 70, "attack": 10, "defense": 8, "initiative": 10, "luck": 10},
            ),
            MobDef(
                key="aranha_gigante_da_tocaia",
                display="GuarAranha Gigante da Tocaia",
                emoji="🌳",
                media_key="aranha_gigante_da_tocaia_media",
                stats_base={"max_hp": 80, "attack": 15, "defense": 10, "initiative": 18, "luck": 15},
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
                    
                    # Recompensas (que o runtime.py vai escalar)
                    "is_boss": True,
                    "xp_reward": 120,    # XP base (será multiplicado pela dificuldade)
                    "gold_drop": 50,     # Ouro base (será multiplicado pela dificuldade)
                      
                    # A Tabela de Loot que me enviaste
                    "loot_table": [
                        {"item_id": "emblema_guerreiro", "drop_chance": 5},
                        {"item_id": "essencia_guardia", "drop_chance": 5},
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