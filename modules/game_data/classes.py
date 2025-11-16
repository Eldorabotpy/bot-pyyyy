# modules/game_data/classes.py

CLASSES_DATA = {
    'guerreiro': {
        'display_name': 'Guerreiro', 'emoji': '⚔️',
        'description': 'Combatente equilibrado, mestre da espada e escudo.',
        'stat_modifiers': {'hp': 3.0, 'attack': 1.4, 'defense': 1.4, 'initiative': 0.9, 'luck': 0.7},
        'file_id_name': 'classe_guerreiro_media',
        'tier': 1
    },
    # EVOLUÇÕES TIER 2 #
    'cavaleiro': {
        'display_name': 'Cavaleiro', 'emoji': '🛡️', 
        'description': 'Um bastião de defesa, inabalável no campo de batalha.', 
        'stat_modifiers': {'hp': 3.2, 'attack': 1.5, 'defense': 1.8, 'initiative': 0.8, 'luck': 0.7},
        'file_id_name': 'classe_guerreiro_media',
        'tier': 2
    },
    'gladiador': {'display_name': 'Gladiador', 'emoji': '🔱', 
        'description': 'Um mestre da arena, focado em ataques rápidos e brutais.', 
        'stat_modifiers': {'hp': 3.1, 'attack': 1.9, 'defense': 1.0, 'initiative': 1.3, 'luck': 0.9},
        'file_id_name': 'classe_guerreiro_media',
        'tier': 2
    },
    # EVOLUÇÕES TIER 3 #
    'templario': {
        'display_name': 'Templário', 'emoji': '⚜️', 
        'description': 'Um campeão sagrado, cuja fé é o seu escudo e a sua espada.', 
        'stat_modifiers': {'hp': 3.5, 'attack': 1.6, 'defense': 2.2, 'initiative': 0.7, 'luck': 1.0},
        'file_id_name': 'classe_guerreiro_media',
        'tier': 3
    },
    
    #------------------------------------------------------------------------------------------------
    'berserker': {
        'display_name': 'Berserker', 'emoji': '🪓',
        'description': 'Dano massivo, sacrifica defesa.',
        'stat_modifiers': {'hp': 3.0, 'attack': 1.8, 'defense': 0.7, 'initiative': 1.1, 'luck': 0.9},
        'file_id_name': 'classe_berserker_media',
        'tier': 1
    },
    # EVOLUÇÕES TIER 2 #
    'barbaro': {'display_name': 'Bárbaro', 'emoji': '🗿', 
        'description': 'A fúria encarnada, troca qualquer resquício de defesa por poder de ataque puro.', 
        'stat_modifiers': {'hp': 3.0, 'attack': 2.2, 'defense': 0.5, 'initiative': 1.2, 'luck': 0.9},
        'file_id_name': 'classe_berserker_media',
        'tier': 2
    },
    'juggernaut': {'display_name': 'Juggernaut', 'emoji': '🐗', 
        'description': 'Uma força da natureza imparável, combinando resistência com investidas poderosas.', 
        'stat_modifiers': {'hp': 3.4, 'attack': 1.9, 'defense': 1.0, 'initiative': 1.0, 'luck': 0.8},
        'file_id_name': 'classe_berserker_media',
        'tier': 2
    },
    # EVOLUÇÕES TIER 3 #
    'ira_primordial': {
        'display_name': 'Ira Primordial', 'emoji': '👹', 
        'description': 'A personificação da fúria ancestral, mais forte à beira da morte.', 
        'stat_modifiers': {'hp': 2.8, 'attack': 2.6, 'defense': 0.6, 'initiative': 1.4, 'luck': 1.0},
        'file_id_name': 'classe_berserker_media',
        'tier': 3
    },

    #-------------------------------------------------------------------------------------------------------
    
    'cacador': {
        'display_name': 'Caçador', 'emoji': '🏹',
        'description': 'À distância, alta iniciativa e sorte.',
        'stat_modifiers': {'hp': 3.0, 'attack': 1.2, 'defense': 0.9, 'initiative': 1.6, 'luck': 1.3},
        'file_id_name': 'classe_cacador_media',
        'tier': 1
    },
    # EVOLUÇÕES TIER 2 #
    'patrulheiro': {
        'display_name': 'Patrulheiro', 'emoji': '🐾', 
        'description': 'Um com a natureza, luta em sincronia com um companheiro animal.', 
        'stat_modifiers': {'hp': 3.0, 'attack': 1.3, 'defense': 1.0, 'initiative': 1.7, 'luck': 1.4},
        'file_id_name': 'classe_cacador_media',
        'tier': 2
    },
    'franco_atirador': {
        'display_name': 'Franco-Atirador', 'emoji': '🎯', 
        'description': 'Um especialista em tiros precisos e mortais à distância.', 
        'stat_modifiers': {'hp': 2.8, 'attack': 1.5, 'defense': 0.8, 'initiative': 1.5, 'luck': 1.9},
        'file_id_name': 'classe_cacador_media',
        'tier': 2
    },
    # EVOLUÇÕES TIER 3 #
    'mestre_da_selva': {
        'display_name': 'Mestre da Selva', 'emoji': '🦁', 
        'description': 'O predador alfa, capaz de domar as feras mais selvagens.', 
        'stat_modifiers': {'hp': 3.2, 'attack': 1.6, 'defense': 1.1, 'initiative': 1.9, 'luck': 1.6},
        'file_id_name': 'classe_cacador_media',
        'tier': 3
    },
    
    #--------------------------------------------------------------------------------------------------------
    'monge': {
        'display_name': 'Monge', 'emoji': '🧘',
        'description': 'Agilidade e defesa.',
        'stat_modifiers': {'hp': 3.0, 'attack': 1.0, 'defense': 1.6, 'initiative': 1.3, 'luck': 0.8},
        'file_id_name': 'classe_monge_media',
        'tier': 1
    },
    # EVOLUÇÕES TIER 2 #
    'guardiao_do_templo': {'display_name': 'Guardião do Templo', 'emoji': '🏯', 
        'description': 'Mestre da defesa que usa o Ki para criar barreiras e contra-atacar.', 
        'stat_modifiers': {'hp': 3.3, 'attack': 1.0, 'defense': 2.0, 'initiative': 1.2, 'luck': 0.8},
        'file_id_name': 'classe_monge_media',
        'tier': 2  
    },
    'punho_elemental': {'display_name': 'Punho Elemental', 'emoji': '🔥', 
        'description': 'Lutador que canaliza a fúria dos elementos nos seus punhos.', 
        'stat_modifiers': {'hp': 3.0, 'attack': 1.4, 'defense': 1.2, 'initiative': 1.6, 'luck': 1.0},
        'file_id_name': 'classe_monge_media',
        'tier': 2 
    },
    # EVOLUÇÕES TIER 3 #
    'ascendente': {
        'display_name': 'Ascendente', 'emoji': '🕊️', 
        'description': 'Atingiu a transcendência, movendo-se como o vento e golpeando como o trovão.', 
        'stat_modifiers': {'hp': 3.3, 'attack': 1.5, 'defense': 2.0, 'initiative': 1.8, 'luck': 1.0},
        'file_id_name': 'classe_monge_media',
        'tier': 3 
    },
   
    #---------------------------------------------------------------------------------------------------------
    'mago': {
        'display_name': 'Mago', 'emoji': '🧙',
        'description': 'Poder arcano ofensivo.',
        'stat_modifiers': {'hp': 3.0, 'attack': 1.7, 'defense': 0.7, 'initiative': 0.9, 'luck': 0.9},
        'file_id_name': 'classe_mago_media',
        'tier': 1
    },
    # EVOLUÇÕES TIER 2 #
    'feiticeiro': {'display_name': 'Feiticeiro', 'emoji': '🔮', 
        'description': 'Mestre das maldições e do dano contínuo (DoT).', 
        'stat_modifiers': {'hp': 2.8, 'attack': 1.9, 'defense': 0.7, 'initiative': 1.0, 'luck': 1.2},
        'file_id_name': 'classe_mago_media',
        'tier': 2
    },
    'elementalista': {'display_name': 'Elementalista', 'emoji': '☄️', 
        'description': 'Especialista em dano elemental massivo e em área.', 
        'stat_modifiers': {'hp': 2.9, 'attack': 2.0, 'defense': 0.8, 'initiative': 1.1, 'luck': 0.9},
        'file_id_name': 'classe_mago_media',
        'tier': 2
    },

     # EVOLUÇÕES TIER 3 #
    'arquimago': {
        'display_name': 'Arquimago', 'emoji': '🌌', 
        'description': 'Um canal de poder arcano puro, capaz de alterar a própria realidade.', 
        'stat_modifiers': {'hp': 2.8, 'attack': 2.4, 'defense': 0.8, 'initiative': 1.2, 'luck': 1.3},
        'file_id_name': 'classe_mago_media',
        'tier': 3
    },
    
    #----------------------------------------------------------------------------------------------------------
    'bardo': {
        'display_name': 'Bardo', 'emoji': '🎶',
        'description': 'Sorte e suporte.',
        'stat_modifiers': {'hp': 3.0, 'attack': 0.9, 'defense': 1.0, 'initiative': 1.2, 'luck': 1.8},
        'file_id_name': 'classe_bardo_media',
        'tier': 1
    },
    # EVOLUÇÕES TIER 2 #
    'menestrel': {'display_name': 'Menestrel', 'emoji': '📜', 
        'description': 'Focado em canções que curam e fortalecem os aliados.', 
        'stat_modifiers': {'hp': 3.1, 'attack': 0.9, 'defense': 1.2, 'initiative': 1.3, 'luck': 2.0},
        'file_id_name': 'classe_bardo_media',
        'tier': 2
    },
    'encantador': {'display_name': 'Encantador', 'emoji': '✨', 
        'description': 'Usa melodias para confundir e debilitar os inimigos.', 
        'stat_modifiers': {'hp': 3.0, 'attack': 1.0, 'defense': 1.0, 'initiative': 1.4, 'luck': 2.2},
        'file_id_name': 'classe_bardo_media',
        'tier': 2
    },
    # EVOLUÇÕES TIER 3 #
    'maestro': {
        'display_name': 'Maestro', 'emoji': '🎼', 
        'description': 'Rege o campo de batalha com sinfonias de poder que inspiram e aterrorizam.', 
        'stat_modifiers': {'hp': 3.2, 'attack': 1.1, 'defense': 1.3, 'initiative': 1.6, 'luck': 2.5},
        'file_id_name': 'classe_bardo_media',
        'tier': 3
    },

    #-----------------------------------------------------------------------------------------------------------
    'assassino': {
        'display_name': 'Assassino', 'emoji': '🔪',
        'description': 'Furtividade, velocidade e críticos.',
        'stat_modifiers': {'hp': 3.0, 'attack': 1.3, 'defense': 0.8, 'initiative': 1.8, 'luck': 1.5},
        'file_id_name': 'classe_assassino_media',
        'tier': 1
    },
    # EVOLUÇÕES TIER 2 #
    'sombra': {'display_name': 'Sombra', 'emoji': '💨', 
        'description': 'Mestre da furtividade e de ataques surpresa devastadores.', 
        'stat_modifiers': {'hp': 2.9, 'attack': 1.4, 'defense': 0.7, 'initiative': 2.2, 'luck': 1.7},
        'file_id_name': 'classe_assassino_media',
        'tier': 2
    },
    'venefico': {'display_name': 'Venéfico', 'emoji': '☠️', 
        'description': 'Especialista em venenos e toxinas que causam dano ao longo do tempo.', 
        'stat_modifiers': {'hp': 3.0, 'attack': 1.5, 'defense': 0.9, 'initiative': 1.6, 'luck': 1.6},
        'file_id_name': 'classe_assassino_media',
        'tier': 2
    },
    # EVOLUÇÕES TIER 3 #
    'mestre_das_laminas': {
        'display_name': 'Mestre das Lâminas', 'emoji': '⚔️', 
        'description': 'Um vulto letal cuja velocidade com as lâminas é inigualável.', 
        'stat_modifiers': {'hp': 3.0, 'attack': 1.7, 'defense': 0.8, 'initiative': 2.5, 'luck': 1.9},
        'file_id_name': 'classe_assassino_media',
        'tier': 3
    },
    
    #------------------------------------------------------------------------------------------------------------
    'samurai': {
        'display_name': 'Samurai', 'emoji': '🥷',
        'description': 'Técnica, ataque e defesa equilibrados.',
        'stat_modifiers': {'hp': 3.0, 'attack': 1.5, 'defense': 1.3, 'initiative': 1.0, 'luck': 0.8},
        'file_id_name': 'classe_samurai_media',
        'tier': 1
    },
    # EVOLUÇÕES TIER 2 
    'kensei': {'display_name': 'Kensei', 'emoji': '🗡️', 
        'description': 'O Santo da Espada, focado na perfeição técnica de cada golpe.', 
        'stat_modifiers': {'hp': 3.0, 'attack': 1.8, 'defense': 1.4, 'initiative': 1.2, 'luck': 0.8},
        'file_id_name': 'classe_samurai_media',
        'tier': 2
    },
    'ronin': {'display_name': 'Ronin', 'emoji': '🧧', 
        'description': 'Um guerreiro solitário, mestre do contra-ataque e da sobrevivência.', 
        'stat_modifiers': {'hp': 3.2, 'attack': 1.6, 'defense': 1.5, 'initiative': 1.0, 'luck': 0.9},
        'file_id_name': 'classe_samurai_media',
        'tier': 2
    },
    # EVOLUÇÕES TIER 3 
    'shogun': {
        'display_name': 'Shogun', 'emoji': '🏯', 
        'description': 'Um líder no campo de batalha, cuja presença inspira os aliados e quebra a moral dos inimigos.', 
        'stat_modifiers': {'hp': 3.4, 'attack': 1.9, 'defense': 1.8, 'initiative': 1.1, 'luck': 1.0},
        'file_id_name': 'classe_samurai_media',
        'tier': 3
    },
    
    # ... (depois do bloco do 'shogun') ...

    #------------------------------------------------------------------------------------------------------------
    'curandeiro': {
        'display_name': 'Curandeiro', 'emoji': '🩹',
        'description': 'Suporte focado em cura e buffs.',
        'stat_modifiers': {'hp': 3.2, 'attack': 0.8, 'defense': 1.5, 'initiative': 1.0, 'luck': 1.5},
        'file_id_name': 'classe_curandeiro_media',
        'tier': 1
    },
    # EVOLUÇÕES TIER 2 
    'clerigo': {
        'display_name': 'Clérigo', 'emoji': '✝️',
        'description': 'Canaliza poder divino para curas potentes e purificação.',
        'stat_modifiers': {'hp': 3.4, 'attack': 0.8, 'defense': 1.7, 'initiative': 1.1, 'luck': 1.8},
        'file_id_name': 'classe_curandeiro_media',
        'tier': 2
    },
    'druida': {
        'display_name': 'Druida', 'emoji': '🌳',
        'description': 'Usa o poder da natureza para curar aliados e prender inimigos.',
        'stat_modifiers': {'hp': 3.3, 'attack': 1.0, 'defense': 1.6, 'initiative': 1.3, 'luck': 1.6},
        'file_id_name': 'classe_curandeiro_media',
        'tier': 2
    },
    # EVOLUÇÕES TIER 3 
    'sacerdote': {
        'display_name': 'Sacerdote', 'emoji': '⛪',
        'description': 'Um mestre da cura em área (HoT) e escudos sagrados.',
        'stat_modifiers': {'hp': 3.6, 'attack': 0.8, 'defense': 2.0, 'initiative': 1.2, 'luck': 2.0},
        'file_id_name': 'classe_curandeiro_media',
        'tier': 3
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
    "curandeiro":{"stat_key": "fe",          "type": "sagrado",    "scales_with": "fe"}, 
}


# ✅ NOVO DICIONÁRIO ADICIONADO
# Define o emoji específico para o atributo de dano de cada classe,
# usado pelo item_factory para renderizar os itens.
CLASS_DMG_EMOJI = {
    "guerreiro": "⚔️",
    "berserker": "🪓",
    "cacador": "🏹",
    "monge": "🧘",
    "mago": "🪄",
    "bardo": "🎶",
    "assassino": "🔪",
    "samurai": "🥷",
    "curandeiro": "🩹",
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
