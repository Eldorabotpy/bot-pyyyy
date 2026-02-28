# modules/events/catacumbas/config.py

from dataclasses import dataclass
from typing import List, Dict, Optional

# ==============================================================================
# ⚙️ CONFIGURAÇÕES GERAIS
# ==============================================================================
EVENT_NAME = "As Catacumbas Reais"
MIN_PLAYERS = 1  # Pode ser 1 para testes
MAX_PLAYERS = 6
REQUIRED_KEY_ITEM = "chave_catacumba"
TOTAL_FLOORS = 5 

# ==============================================================================
# 🖼️ SISTEMA DE MÍDIA
# ==============================================================================
MEDIA_KEYS = {
    "menu_banner": "evt_cat_banner_main",
    "lobby_screen": "evt_cat_lobby_wait",
    "victory": "evt_cat_victory_chest",
    "defeat": "evt_cat_game_over_skulls",
    "flee": "evt_cat_run_away",
    "mob_skeleton": "mob_skeleton_warrior_gif",
    "mob_guard": "mob_royal_guard_img",
    "mob_wraith": "mob_wraith_ghost_img",
    "boss_phase_1": "boss_eskel_throne_img",
    "boss_phase_2": "boss_eskel_standing_gif",
    "boss_ultimate": "boss_eskel_ultimate_gif"
}

# ==============================================================================
# 👹 INIMIGOS E BOSSES
# ==============================================================================
@dataclass
class EnemyConfig:
    name: str
    max_hp: int
    attack: int
    defense: int
    speed: int
    xp_reward: int
    image_key: str

MOBS = {
    "skeleton_warrior": EnemyConfig(
        name="Esqueleto Guerreiro",
        max_hp=150, attack=35, defense=10, speed=12,
        xp_reward=50, image_key="mob_skeleton"
    ),
    "royal_guard": EnemyConfig(
        name="Guarda Real Corrompido",
        max_hp=280, attack=55, defense=25, speed=10,
        xp_reward=120, image_key="mob_guard"
    ),
    "spectral_wraith": EnemyConfig(
        name="Aparição Espectral",
        max_hp=200, attack=70, defense=5, speed=25,
        xp_reward=150, image_key="mob_wraith"
    )
}

@dataclass
class BossConfig:
    name: str
    max_hp: int
    attack: int
    defense: int
    initiative: int
    image_normal: str
    image_enraged: str
    phases: List[str]

BOSS_CONFIG = BossConfig(
    name="Rei Eskel, o Traído",
    max_hp=2500,  
    attack=120,
    defense=40,
    initiative=15,
    image_normal="boss_phase_1",
    image_enraged="boss_phase_2",
    phases=["normal", "enraged"]
)

# ==============================================================================
# 🗺️ MAPA DOS ANDARES
# ==============================================================================
FLOOR_MAP = {
    1: "skeleton_warrior",
    2: "royal_guard",
    3: "spectral_wraith",
    4: "royal_guard", 
    5: "BOSS"
}

# ==============================================================================
# 💰 RECOMPENSAS
# ==============================================================================
REWARDS = {
    "xp_fixed": 800,
    "gold_fixed": 1500,
    "equipment_drop_chance": 0.85, # 85% de chance de o Boss dar um item do SET
    # Tabela exclusiva da Masmorra (O crafting usa outra tabela que não tem unico/mitico)
    "rarity_weights": {
        "comum": 30, "bom": 30, "raro": 20, "epico": 10, "lendario": 7, 
        "unico": 2.5,  # 2.5% de chance de ser Único
        "mitico": 0.5  # 0.5% de chance de ser Mítico
    }
}

TEXTS = {
    "intro": (
        "💀 **CATACUMBAS (MODO TESTE)** 💀\n\n"
        "Inimigos foram enfraquecidos para calibração.\n"
        "Avance para testar a mecânica de andares e loot.\n\n"
        "⚠️ **Requisito:** 1x Chave"
    ),
    "defeat": (
        "💀 **VOCÊ CAIU EM BATALHA!**\n\n"
        "Seus aliados ainda lutam... ou morrerão tentando.\n"
        "Você pode assistir e torcer, mas não pode mais agir."
    )
}