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
        
        # A sequência de monstros (6 combates)
        "floors": [
            MobDef(
                key="lobo_sombrio",
                display="Lobo Sombrio",
                emoji="🐺",
                media_key="mob_lobo_sombrio", # Exemplo de chave no file_ids.json
                stats_base={"max_hp": 80, "attack": 12, "defense": 5, "initiative": 15, "luck": 5},
            ),
            MobDef(
                key="lobo_sombrio_2",
                display="Lobo Sombrio Feroz",
                emoji="🐺",
                media_key="mob_lobo_sombrio",
                stats_base={"max_hp": 90, "attack": 15, "defense": 6, "initiative": 16, "luck": 5},
            ),
            MobDef(
                key="aranha_gigante",
                display="Aranha Gigante",
                emoji="🕷️",
                media_key="mob_aranha_gigante",
                stats_base={"max_hp": 120, "attack": 18, "defense": 8, "initiative": 12, "luck": 8},
            ),
             MobDef(
                key="aranha_gigante_2",
                display="Aranha Gigante Peçonhenta",
                emoji="🕷️",
                media_key="mob_aranha_gigante",
                stats_base={"max_hp": 130, "attack": 20, "defense": 9, "initiative": 13, "luck": 9},
            ),
            MobDef(
                key="espirito_floresta",
                display="Espírito da Floresta Vingativo",
                emoji="👻",
                media_key="mob_espirito_floresta",
                stats_base={"max_hp": 150, "attack": 25, "defense": 15, "initiative": 20, "luck": 10},
            ),
            MobDef(
                key="guardiao_ancestral_boss",
                display="Guardião Ancestral (BOSS)",
                emoji="🌳",
                media_key="boss_guardiao_ancestral",
                stats_base={"max_hp": 300, "attack": 35, "defense": 20, "initiative": 18, "luck": 15},
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