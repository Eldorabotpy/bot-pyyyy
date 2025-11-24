# modules/events/catacumbas/config.py

from dataclasses import dataclass
from typing import List, Dict, Optional

# ==============================================================================
# ⚙️ CONFIGURAÇÕES GERAIS
# ==============================================================================
EVENT_NAME = "As Catacumbas Reais"
MIN_PLAYERS = 1  # Mantido em 1 para você testar sozinho
MAX_PLAYERS = 4
REQUIRED_KEY_ITEM = "chave_catacumba"
TOTAL_FLOORS = 3 

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
# 👹 DEFINIÇÃO DOS INIMIGOS (MODO TESTE - NERFADO)
# ==============================================================================
@dataclass
class RaidEnemy:
    id: str
    name: str
    max_hp: int
    attack: int
    defense: int
    speed: int
    image_key: str
    xp_reward: int
    desc: str

MOBS = {
    "skeleton_warrior": RaidEnemy(
        id="skeleton_warrior",
        name="Esqueleto Fraco",  # Nome alterado para indicar teste
        max_hp=300,             # Antes: 5000 (Agora morre em ~3 hits)
        attack=15,              # Antes: 80 (Agora tira ~15% da vida de um novato)
        defense=5,
        speed=2,                # Lento, para você atacar primeiro
        image_key="mob_skeleton",
        xp_reward=50,
        desc="Um esqueleto velho e quebradiço."
    ),
    "royal_guard": RaidEnemy(
        id="royal_guard",
        name="Guarda Zumbi",
        max_hp=600,             # Antes: 8500
        attack=25,              # Antes: 110
        defense=10,
        speed=4,
        image_key="mob_guard",
        xp_reward=100,
        desc="Ainda sabe usar a espada, mas é lento."
    ),
    "spectral_wraith": RaidEnemy(
        id="spectral_wraith",
        name="Fantasminha",
        max_hp=200,             # Antes: 4000
        attack=40,              # Antes: 150 (Bate forte, mas tem pouca vida)
        defense=0,
        speed=15,               # Rápido
        image_key="mob_wraith",
        xp_reward=150,
        desc="Assustador, mas frágil."
    )
}

# ==============================================================================
# ☠️ CONFIGURAÇÃO DO BOSS (MODO TESTE - NERFADO)
# ==============================================================================
@dataclass
class RaidBossConfig:
    name: str
    max_hp: int
    attack: int
    defense: int
    initiative: int
    image_normal: str
    image_enraged: str
    phases: List[str]

BOSS_CONFIG = RaidBossConfig(
    name="Lorde Eskel (Teste)",
    max_hp=1500,        # Antes: 65000 (Agora é viável solar)
    attack=45,          # Antes: 180 (Não dá Hit Kill em lvl baixo)
    defense=15,         # Antes: 50
    initiative=8,       # Antes: 15
    image_normal="boss_phase_1",
    image_enraged="boss_phase_2",
    phases=["normal", "enraged"]
)

# ==============================================================================
# 🗺️ MAPA DOS ANDARES
# ==============================================================================
# Define quem aparece em cada andar
FLOOR_MAP = {
    1: "skeleton_warrior",
    2: "royal_guard",
    3: "BOSS"
}

# ==============================================================================
# 💰 RECOMPENSAS
# ==============================================================================
REWARDS = {
    "xp_fixed": 500,
    "gold_fixed": 1000,
    "rare_items": [
        {"id": "espada_teste", "chance": 0.50},
        {"id": "bau_tesouro_evento", "chance": 1.00}
    ]
}

TEXTS = {
    "intro": (
        "💀 **CATACUMBAS (MODO TESTE)** 💀\n\n"
        "Inimigos foram enfraquecidos para calibração.\n"
        "Avance para testar a mecânica de andares e loot.\n\n"
        "⚠️ **Requisito:** 1x Chave"
    ),
    "victory": (
        "🏆 **VITÓRIA (TESTE CONCLUÍDO)!** 🏆\n\n"
        "O sistema de combate funcionou.\n"
        "Você derrotou o chefe de teste."
    ),
    "defeat": (
        "☠️ **DERROTA**\n\n"
        "Você morreu. Se isso aconteceu no primeiro turno, verifique se sua vida está cheia.\n"
        "Use uma poção ou peça cura."
    )
}