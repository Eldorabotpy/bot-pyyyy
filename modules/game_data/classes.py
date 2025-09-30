# modules/game_data/classes.py

CLASSES_DATA = {
    'guerreiro': {
        'display_name': 'Guerreiro', 'emoji': '⚔️',
        'description': 'Combatente equilibrado, mestre da espada e escudo.',
        'stat_modifiers': {'hp': 3.0, 'attack': 1.4, 'defense': 1.4, 'initiative': 0.9, 'luck': 0.7},
        'file_id_name': 'classe_guerreiro_media'
    },
    'berserker': {
        'display_name': 'Berserker', 'emoji': '🪓',
        'description': 'Dano massivo, sacrifica defesa.',
        'stat_modifiers': {'hp': 3.0, 'attack': 1.8, 'defense': 0.7, 'initiative': 1.1, 'luck': 0.9},
        'file_id_name': 'classe_berserker_media'
    },
    'cacador': {
        'display_name': 'Caçador', 'emoji': '🏹',
        'description': 'À distância, alta iniciativa e sorte.',
        'stat_modifiers': {'hp': 3.0, 'attack': 1.2, 'defense': 0.9, 'initiative': 1.6, 'luck': 1.3},
        'file_id_name': 'classe_cacador_media'
    },
    'monge': {
        'display_name': 'Monge', 'emoji': '🧘',
        'description': 'Agilidade e defesa.',
        'stat_modifiers': {'hp': 3.0, 'attack': 1.0, 'defense': 1.6, 'initiative': 1.3, 'luck': 0.8},
        'file_id_name': 'classe_monge_media'
    },
    'mago': {
        'display_name': 'Mago', 'emoji': '🧙',
        'description': 'Poder arcano ofensivo.',
        'stat_modifiers': {'hp': 3.0, 'attack': 1.7, 'defense': 0.7, 'initiative': 0.9, 'luck': 0.9},
        'file_id_name': 'classe_mago_media'
    },
    'bardo': {
        'display_name': 'Bardo', 'emoji': '🎶',
        'description': 'Sorte e suporte.',
        'stat_modifiers': {'hp': 3.0, 'attack': 0.9, 'defense': 1.0, 'initiative': 1.2, 'luck': 1.8},
        'file_id_name': 'classe_bardo_media'
    },
    'assassino': {
        'display_name': 'Assassino', 'emoji': '🔪',
        'description': 'Furtividade, velocidade e críticos.',
        'stat_modifiers': {'hp': 3.0, 'attack': 1.3, 'defense': 0.8, 'initiative': 1.8, 'luck': 1.5},
        'file_id_name': 'classe_assassino_media'
    },
    'samurai': {
        'display_name': 'Samurai', 'emoji': '🥷',
        'description': 'Técnica, ataque e defesa equilibrados.',
        'stat_modifiers': {'hp': 3.0, 'attack': 1.5, 'defense': 1.3, 'initiative': 1.0, 'luck': 0.8},
        'file_id_name': 'classe_samurai_media'
    },
}

# === DANO (ATRIBUTO) PRINCIPAL POR CLASSE =====================================
# Use nomes que EXISTEM em ATTRIBUTE_ICONS para o stat_key,
# garantindo que o display mostre o ícone correto do atributo.
CLASS_PRIMARY_DAMAGE = {
    "guerreiro": {"stat_key": "forca",       "type": "corte",      "scales_with": "forca"},
    "samurai":   {"stat_key": "bushido",     "type": "corte",      "scales_with": "bushido"},
    "assassino": {"stat_key": "letalidade",  "type": "perfuracao", "scales_with": "letalidade"},
    "monge":     {"stat_key": "foco",        "type": "impacto",    "scales_with": "foco"},
    "mago":      {"stat_key": "inteligencia","type": "arcano",     "scales_with": "inteligencia"},
    "bardo":     {"stat_key": "carisma",     "type": "sonoro",     "scales_with": "carisma"},
    "berserker": {"stat_key": "furia",       "type": "impacto",    "scales_with": "furia"},
    "cacador":   {"stat_key": "precisao",    "type": "perfuracao", "scales_with": "precisao"},
}

def get_primary_damage_profile(player_class: str) -> dict:
    """
    Retorna o perfil (atributo-chave e metadados) usado na forja/itens para
    definir SEMPRE o atributo principal da classe no item.
    """
    pc = (player_class or "").lower()
    return CLASS_PRIMARY_DAMAGE.get(
        pc,
        {"stat_key": "forca", "type": "fisico", "scales_with": "forca"},
    )

def get_stat_modifiers(player_class: str) -> dict:
    """Acesso seguro aos modificadores de classe (cálculo de pontos)."""
    base = CLASSES_DATA.get((player_class or "").lower(), {})
    return base.get("stat_modifiers", {})
