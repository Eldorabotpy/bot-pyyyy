# modules/game_data/classes.py

CLASSES_DATA = {
    # ========================= GUERREIRO =========================
    'guerreiro': {
        'display_name': 'Guerreiro', 'emoji': '⚔️',
        'description': 'Combatente equilibrado, mestre da espada e escudo.',
        'stat_modifiers': {'hp': 3.0, 'max_mana': 1.0,'attack': 1.4, 'defense': 1.4, 'initiative': 0.9, 'luck': 0.7},
        'file_id_name': 'classe_guerreiro_media',
        'tier': 1
    },
    'cavaleiro': {
        'display_name': 'Cavaleiro', 'emoji': '🛡️', 
        'description': 'Um bastião de defesa, inabalável no campo de batalha.', 
        'stat_modifiers': {'hp': 3.2, 'max_mana': 1.0, 'attack': 1.5, 'defense': 1.8, 'initiative': 0.8, 'luck': 0.7},
        'file_id_name': 'classe_guerreiro_media',
        'tier': 2
    },
    'gladiador': {'display_name': 'Gladiador', 'emoji': '🔱', 
        'description': 'Um mestre da arena, focado em ataques rápidos e brutais.', 
        'stat_modifiers': {'hp': 3.1, 'max_mana': 1.0, 'attack': 1.9, 'defense': 1.0, 'initiative': 1.3, 'luck': 0.9},
        'file_id_name': 'classe_guerreiro_media',
        'tier': 2
    },
    'templario': {
        'display_name': 'Templário', 'emoji': '⚜️', 
        'description': 'Um campeão sagrado, cuja fé é o seu escudo e a sua espada.', 
        'stat_modifiers': {'hp': 3.5, 'max_mana': 1.5, 'attack': 1.6, 'defense': 2.2, 'initiative': 0.7, 'luck': 1.0},
        'file_id_name': 'classe_guerreiro_media',
        'tier': 3
    },
    
    # ========================= BERSERKER =========================
    'berserker': {
        'display_name': 'Berserker', 'emoji': '🪓',
        'description': 'Dano massivo, sacrifica defesa.',
        'stat_modifiers': {'hp': 3.0, 'max_mana': 0.8, 'attack': 1.8, 'defense': 0.7, 'initiative': 1.1, 'luck': 0.9},
        'file_id_name': 'classe_berserker_media',
        'tier': 1
    },
    'barbaro': {'display_name': 'Bárbaro', 'emoji': '🗿', 
        'description': 'A fúria encarnada, troca qualquer resquício de defesa por poder de ataque puro.', 
        'stat_modifiers': {'hp': 3.0, 'max_mana': 0.7, 'attack': 2.2, 'defense': 0.5, 'initiative': 1.2, 'luck': 0.9},
        'file_id_name': 'classe_berserker_media',
        'tier': 2
    },
    'juggernaut': {'display_name': 'Juggernaut', 'emoji': '🐗', 
        'description': 'Uma força da natureza imparável, combinando resistência com investidas poderosas.', 
        'stat_modifiers': {'hp': 3.4, 'max_mana': 0.8, 'attack': 1.9, 'defense': 1.0, 'initiative': 1.0, 'luck': 0.8},
        'file_id_name': 'classe_berserker_media',
        'tier': 2
    },
    'ira_primordial': {
        'display_name': 'Ira Primordial', 'emoji': '👹', 
        'description': 'A personificação da fúria ancestral, mais forte à beira da morte.', 
        'stat_modifiers': {'hp': 2.8, 'max_mana': 0.6, 'attack': 2.6, 'defense': 0.6, 'initiative': 1.4, 'luck': 1.0},
        'file_id_name': 'classe_berserker_media',
        'tier': 3
    },

    # ========================= CAÇADOR =========================
    'cacador': {
        'display_name': 'Caçador', 'emoji': '🏹',
        'description': 'À distância, alta iniciativa e sorte.',
        'stat_modifiers': {'hp': 3.0, 'max_mana': 1.2, 'attack': 1.2, 'defense': 0.9, 'initiative': 1.6, 'luck': 1.3},
        'file_id_name': 'classe_cacador_media',
        'tier': 1
    },
    'patrulheiro': {
        'display_name': 'Patrulheiro', 'emoji': '🐾', 
        'description': 'Um com a natureza, luta em sincronia com um companheiro animal.', 
        'stat_modifiers': {'hp': 3.0, 'max_mana': 1.3, 'attack': 1.3, 'defense': 1.0, 'initiative': 1.7, 'luck': 1.4},
        'file_id_name': 'classe_cacador_media',
        'tier': 2
    },
    'franco_atirador': {
        'display_name': 'Franco-Atirador', 'emoji': '🎯', 
        'description': 'Um especialista em tiros precisos e mortais à distância.', 
        'stat_modifiers': {'hp': 2.8, 'max_mana': 1.4, 'attack': 1.5, 'defense': 0.8, 'initiative': 1.5, 'luck': 1.9},
        'file_id_name': 'classe_cacador_media',
        'tier': 2
    },
    'mestre_da_selva': {
        'display_name': 'Mestre da Selva', 'emoji': '🦁', 
        'description': 'O predador alfa, capaz de domar as feras mais selvagens.', 
        'stat_modifiers': {'hp': 3.2, 'max_mana': 1.5, 'attack': 1.6, 'defense': 1.1, 'initiative': 1.9, 'luck': 1.6},
        'file_id_name': 'classe_cacador_media',
        'tier': 3
    },
    
    # ========================= MONGE =========================
    'monge': {
        'display_name': 'Monge', 'emoji': '🧘',
        'description': 'Agilidade e defesa.',
        'stat_modifiers': {'hp': 3.0, 'max_mana': 1.5, 'attack': 1.0, 'defense': 1.6, 'initiative': 1.3, 'luck': 0.8},
        'file_id_name': 'classe_monge_media',
        'tier': 1
    },
    'guardiao_do_templo': {'display_name': 'Guardião do Templo', 'emoji': '🏯', 
        'description': 'Mestre da defesa que usa o Ki para criar barreiras e contra-atacar.', 
        'stat_modifiers': {'hp': 3.3, 'max_mana': 1.8, 'attack': 1.0, 'defense': 2.0, 'initiative': 1.2, 'luck': 0.8},
        'file_id_name': 'classe_monge_media',
        'tier': 2  
    },
    'punho_elemental': {'display_name': 'Punho Elemental', 'emoji': '🔥', 
        'description': 'Lutador que canaliza a fúria dos elementos nos seus punhos.', 
        'stat_modifiers': {'hp': 3.0, 'max_mana': 2.0, 'attack': 1.4, 'defense': 1.2, 'initiative': 1.6, 'luck': 1.0},
        'file_id_name': 'classe_monge_media',
        'tier': 2 
    },
    'ascendente': {
        'display_name': 'Ascendente', 'emoji': '🕊️', 
        'description': 'Atingiu a transcendência, movendo-se como o vento e golpeando como o trovão.', 
        'stat_modifiers': {'hp': 3.3, 'max_mana': 2.5, 'attack': 1.5, 'defense': 2.0, 'initiative': 1.8, 'luck': 1.0},
        'file_id_name': 'classe_monge_media',
        'tier': 3 
    },
   
    # ========================= MAGO =========================
    'mago': {
        'display_name': 'Mago', 'emoji': '🧙',
        'description': 'Poder arcano ofensivo.',
        'stat_modifiers': {'hp': 3.0, 'max_mana': 2.0, 'attack': 1.7, 'defense': 0.7, 'initiative': 0.9, 'luck': 0.9},
        'file_id_name': 'classe_mago_media',
        'tier': 1
    },
    'feiticeiro': {'display_name': 'Feiticeiro', 'emoji': '🔮', 
        'description': 'Mestre das maldições e do dano contínuo (DoT).', 
        'stat_modifiers': {'hp': 2.8, 'max_mana': 2.3, 'attack': 1.9, 'defense': 0.7, 'initiative': 1.0, 'luck': 1.2},
        'file_id_name': 'classe_mago_media',
        'tier': 2
    },
    'elementalista': {'display_name': 'Elementalista', 'emoji': '☄️', 
        'description': 'Especialista em dano elemental massivo e em área.', 
        'stat_modifiers': {'hp': 2.9, 'max_mana': 2.4, 'attack': 2.0, 'defense': 0.8, 'initiative': 1.1, 'luck': 0.9},
        'file_id_name': 'classe_mago_media',
        'tier': 2
    },
    'arquimago': {
        'display_name': 'Arquimago', 'emoji': '🌌', 
        'description': 'Um canal de poder arcano puro, capaz de alterar a própria realidade.', 
        'stat_modifiers': {'hp': 2.8, 'max_mana': 2.5, 'attack': 2.4, 'defense': 0.8, 'initiative': 1.2, 'luck': 1.3},
        'file_id_name': 'classe_mago_media',
        'tier': 3
    },
    
    # ========================= BARDO =========================
    'bardo': {
        'display_name': 'Bardo', 'emoji': '🎶',
        'description': 'Sorte e suporte.',
        'stat_modifiers': {'hp': 3.0, 'max_mana': 2.0, 'attack': 0.9, 'defense': 1.0, 'initiative': 1.2, 'luck': 1.8},
        'file_id_name': 'classe_bardo_media',
        'tier': 1
    },
    'menestrel': {'display_name': 'Menestrel', 'emoji': '📜', 
        'description': 'Focado em canções que curam e fortalecem os aliados.', 
        'stat_modifiers': {'hp': 3.1, 'max_mana': 2.2, 'attack': 0.9, 'defense': 1.2, 'initiative': 1.3, 'luck': 2.0},
        'file_id_name': 'classe_bardo_media',
        'tier': 2
    },
    'encantador': {'display_name': 'Encantador', 'emoji': '✨', 
        'description': 'Usa melodias para confundir e debilitar os inimigos.', 
        'stat_modifiers': {'hp': 3.0, 'max_mana': 2.3, 'attack': 1.0, 'defense': 1.0, 'initiative': 1.4, 'luck': 2.2},
        'file_id_name': 'classe_bardo_media',
        'tier': 2
    },
    'maestro': {
        'display_name': 'Maestro', 'emoji': '🎼', 
        'description': 'Rege o campo de batalha com sinfonias de poder que inspiram e aterrorizam.', 
        'stat_modifiers': {'hp': 3.2, 'max_mana': 2.8, 'attack': 1.1, 'defense': 1.3, 'initiative': 1.6, 'luck': 2.5},
        'file_id_name': 'classe_bardo_media',
        'tier': 3
    },

    # ========================= ASSASSINO (ADICIONADO) =========================
    'assassino': {
        'display_name': 'Assassino', 'emoji': '🔪',
        'description': 'Furtividade, dano crítico e alta velocidade.',
        # Status focados em ATK e INI, fraco em DEF
        'stat_modifiers': {'hp': 3.0, 'max_mana': 1.0, 'attack': 1.6, 'defense': 0.8, 'initiative': 1.5, 'luck': 1.2},
        'file_id_name': 'classe_assassino_media',
        'tier': 1
    },
    'ladrao_de_sombras': { 
        'display_name': 'Ladrão de Sombras', 'emoji': '💨', 
        'description': 'Mestre da furtividade e de ataques surpresa devastadores.', 
        'stat_modifiers': {'hp': 3.2, 'max_mana': 1.3, 'attack': 1.6, 'defense': 1.0, 'initiative': 2.2, 'luck': 1.7},
        'file_id_name': 'classe_assassino_media',
        'tier': 2
    },
    'ninja': { 
        'display_name': 'Ninja', 'emoji': '🥷', 
        'description': 'Velocidade extrema e uso de venenos táticos.', 
        'stat_modifiers': {'hp': 3.3, 'max_mana': 1.4, 'attack': 1.7, 'defense': 1.1, 'initiative': 2.4, 'luck': 1.8},
        'file_id_name': 'classe_assassino_media',
        'tier': 3
    },
    'mestre_das_laminas': {
        'display_name': 'Mestre das Lâminas', 'emoji': '⚔️', 
        'description': 'Um vulto letal cuja velocidade com as lâminas é inigualável.', 
        'stat_modifiers': {'hp': 3.4, 'max_mana': 1.5, 'attack': 1.9, 'defense': 1.2, 'initiative': 2.6, 'luck': 1.9},
        'file_id_name': 'classe_assassino_media',
        'tier': 4
    },
    
    # ========================= SAMURAI =========================
    'samurai': {
        'display_name': 'Samurai', 'emoji': '🥷',
        'description': 'Técnica, ataque e defesa equilibrados.',
        'stat_modifiers': {'hp': 3.0, 'max_mana': 1.1, 'attack': 1.5, 'defense': 1.3, 'initiative': 1.0, 'luck': 0.8},
        'file_id_name': 'classe_samurai_media',
        'tier': 1
    },
    'kensei': {'display_name': 'Kensei', 'emoji': '🗡️', 
        'description': 'O Santo da Espada, focado na perfeição técnica de cada golpe.', 
        'stat_modifiers': {'hp': 3.0, 'max_mana': 1.2, 'attack': 1.8, 'defense': 1.4, 'initiative': 1.2, 'luck': 0.8},
        'file_id_name': 'classe_samurai_media',
        'tier': 2
    },
    'ronin': {'display_name': 'Ronin', 'emoji': '🧧', 
        'description': 'Um guerreiro solitário, mestre do contra-ataque e da sobrevivência.', 
        'stat_modifiers': {'hp': 3.2, 'max_mana': 1.3, 'attack': 1.6, 'defense': 1.5, 'initiative': 1.0, 'luck': 0.9},
        'file_id_name': 'classe_samurai_media',
        'tier': 2
    },
    'shogun': {
        'display_name': 'Shogun', 'emoji': '🏯', 
        'description': 'Um líder no campo de batalha, cuja presença inspira os aliados e quebra a moral dos inimigos.', 
        'stat_modifiers': {'hp': 3.4, 'max_mana': 1.4, 'attack': 1.9, 'defense': 1.8, 'initiative': 1.1, 'luck': 1.0},
        'file_id_name': 'classe_samurai_media',
        'tier': 3
    },

    # ========================= CURANDEIRO =========================
    'curandeiro': {
       'display_name': 'Curandeiro', 'emoji': '🩹',
       'description': 'Suporte vital, cura e proteção.',
       'stat_modifiers': {'hp': 3.2, 'max_mana': 2.0, 'attack': 0.8, 'defense': 1.5, 'initiative': 1.0, 'luck': 1.5},
       'file_id_name': 'classe_curandeiro_media',
       'tier': 1
    },
    'clerigo': {
       'display_name': 'Clérigo', 'emoji': '✝️',
       'description': 'Canaliza poder divino para curas potentes e purificação.',
       'stat_modifiers': {'hp': 3.4, 'max_mana': 2.2, 'attack': 0.8, 'defense': 1.7, 'initiative': 1.1, 'luck': 1.8},
       'file_id_name': 'classe_curandeiro_media',
       'tier': 2
    },
    'druida': {
       'display_name': 'Druida', 'emoji': '🌳',
       'description': 'Usa o poder da natureza para curar aliados e prender inimigos.',
       'stat_modifiers': {'hp': 3.3, 'max_mana': 2.1, 'attack': 1.0, 'defense': 1.6, 'initiative': 1.3, 'luck': 1.6},
       'file_id_name': 'classe_curandeiro_media',
       'tier': 2
    },
    'sacerdote': {
       'display_name': 'Sacerdote', 'emoji': '⛪',
       'description': 'Um mestre da cura em área (HoT) e escudos sagrados.',
       'stat_modifiers': {'hp': 3.6, 'max_mana': 2.5, 'attack': 0.8, 'defense': 2.0, 'initiative': 1.2, 'luck': 2.0},
       'file_id_name': 'classe_curandeiro_media',
       'tier': 3
    },
}

# === DANO (ATRIBUTO) PRINCIPAL POR CLASSE =====================================
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

# ============================================================================
# AVATARES PNG DAS CLASSES (PARA O WEB APP)
# ============================================================================
# Cole aqui os links das imagens com fundo transparente (PNG) hospedadas no GitHub.

CLASS_AVATARS_BOT = {
    "aventureiro": {
        "masculino": "https://github.com/user-attachments/assets/44a0ced3-7e87-4792-8b89-1500442d45c8",
        "feminino": "https://github.com/user-attachments/assets/43cf1251-7902-4a0b-a4e2-b34a1b95ed7a"
    },
    
}
CLASS_AVATARS_WEB = {
    "aprendiz": {
        "masculino": "https://github.com/user-attachments/assets/51919153-c779-4778-92f5-c73a66d0fec6",
        "feminino": "https://github.com/user-attachments/assets/a33e78ea-359d-4ed5-9f85-2b672cf482d9"
    },
    "aventureiro": {
        "masculino": "https://github.com/user-attachments/assets/51919153-c779-4778-92f5-c73a66d0fec6",
        "feminino": "https://github.com/user-attachments/assets/a33e78ea-359d-4ed5-9f85-2b672cf482d9"
    },
    
    "guerreiro": {
        "masculino": "https://github.com/user-attachments/assets/47eacac6-48d1-4cc8-8485-ef250c80d318",
        "feminino": "https://github.com/user-attachments/assets/2dafb991-9beb-448e-b076-71a270676489"
    },
    "cavaleiro": {
        "masculino": "https://github.com/seulink/aventureiro_masculino.png",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    "gladiador": {
        "masculino": "https://github.com/seulink/aventureiro_masculino.png",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    "templario": {
        "masculino": "https://github.com/seulink/aventureiro_masculino.png",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    "guardiao_divino": {
        "masculino": "https://github.com/seulink/aventureiro_masculino.png",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    
    "berserker": {
        "masculino": "https://github.com/user-attachments/assets/2282f708-0871-4186-bd34-caa11f5eb698",
        "feminino": "https://github.com/user-attachments/assets/66649cb3-c119-4430-9e29-7a76e5d7a103"
    },
    "barbaro": {
        "masculino": "https://github.com/seulink/aventureiro_masculino.png",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    "juggernaut": {
        "masculino": "https://github.com/seulink/aventureiro_masculino.png",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    "ira_primordial": {
        "masculino": "https://github.com/seulink/aventureiro_masculino.png",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    
    "cacador": {
        "masculino": "https://github.com/user-attachments/assets/e3b557ba-7e06-441e-94a4-c29537f929b3",
        "feminino": "https://github.com/user-attachments/assets/8170e975-12a2-4aa5-9e53-e3c404c09dc2"
    },
    "patrulheiro": {
        "masculino": "https://github.com/seulink/aventureiro_masculino.png",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    "franco_atirador": {
        "masculino": "https://github.com/seulink/aventureiro_masculino.png",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    "olho_de_aguia": {
        "masculino": "",
        "feminino": ""
    },
    
    "monge": {
        "masculino": "https://github.com/user-attachments/assets/ed65c93c-6ed5-4a87-bba8-6ca8c0276dfd",
        "feminino": "https://github.com/user-attachments/assets/45098f38-a35a-4491-9364-476d25013ab7"
    },
    "guardiao_do_templo": {
        "masculino": "https://github.com/seulink/aventureiro_masculino.png",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    "punho_elemental": {
        "masculino": "https://github.com/seulink/aventureiro_masculino.png",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    "ascendente": {
        "masculino": "https://github.com/seulink/aventureiro_masculino.png",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    
    "mago": {
        "masculino": "https://github.com/user-attachments/assets/0acf0255-e003-4dc2-86ec-26513a574c7c",
        "feminino": "https://github.com/user-attachments/assets/9ca00492-0551-45af-b4fd-0b40e963b695"
    },
    "feiticeiro": {
        "masculino": "https://github.com/seulink/aventureiro_masculino.png",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    "elementalista": {
        "masculino": "https://github.com/seulink/aventureiro_masculino.png",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    "arquimago": {
        "masculino": "https://github.com/seulink/aventureiro_masculino.png",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    
    "bardo": {
        "masculino": "https://github.com/user-attachments/assets/cc8446ff-dd44-4f7a-8b36-e140c337b977",
        "feminino": "https://github.com/user-attachments/assets/3aeef591-9f0d-48fa-8a2a-445df928486d"
    },
    "menestrel": {
        "masculino": "https://github.com/seulink/aventureiro_masculino.png",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    "encantador": {
        "masculino": "https://github.com/seulink/aventureiro_masculino.png",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    "maestro": {
        "masculino": "https://github.com/seulink/aventureiro_masculino.png",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    
    "assassino": {
        "masculino": "https://github.com/user-attachments/assets/7e9a16e0-0840-4a86-aaa8-e72f30b1373c",
        "feminino": "https://github.com/user-attachments/assets/80f5a61e-c5d2-408f-b8f3-250b9489e6c7"
    },
    "ladrao_de_sombras": {
        "masculino": "https://github.com/user-attachments/assets/a74ed9a9-b79d-4d15-ba0c-8e3891eab02b",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    "ninja": {
        "masculino": "https://github.com/user-attachments/assets/d6b0cd6c-263e-4300-9b55-bb4e1345f614",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    "mestre_das_laminas": {
        "masculino": "https://github.com/user-attachments/assets/d8932eee-f2bc-42e5-a477-4a0e2bcfa441",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    
    "samurai": {
        "masculino": "https://github.com/user-attachments/assets/cbe4a404-74d7-41b3-a84b-666c49a325b3",
        "feminino": "https://github.com/user-attachments/assets/94f59145-94cd-4ca6-87d9-9411d4064a30"
    },
    "kensei": {
        "masculino": "https://github.com/seulink/aventureiro_masculino.png",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    "ronin": {
        "masculino": "https://github.com/seulink/aventureiro_masculino.png",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    "shogun": {
        "masculino": "https://github.com/seulink/aventureiro_masculino.png",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    
    "curandeiro": {
        "masculino": "https://github.com/user-attachments/assets/17c4a3b8-dd81-4834-8e41-23f4433357e4",
        "feminino": "https://github.com/user-attachments/assets/53e498e6-7770-4782-92a1-5eb542a9fc5e"
    },
    "clerigo": {
        "masculino": "https://github.com/seulink/aventureiro_masculino.png",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    "druida": {
        "masculino": "https://github.com/seulink/aventureiro_masculino.png",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
    "sacerdote": {
        "masculino": "https://github.com/seulink/aventureiro_masculino.png",
        "feminino": "https://github.com/seulink/aventureiro_feminino.png"
    },
}

def get_class_avatar(class_key: str, gender: str = "masculino", plataforma: str = "web") -> str:
    """Retorna o link da imagem da classe baseada no gênero e na plataforma."""
    
    if not class_key or class_key.lower() in ["", "none", "aprendiz"]:
        class_key = "aventureiro"
        
    ckey = class_key.lower()
    gen = gender.lower()

    if gen not in ["masculino", "feminino"]:
        gen = "masculino"

    # Escolhe a galeria certa dependendo de quem pediu
    galeria = CLASS_AVATARS_WEB if plataforma == "web" else CLASS_AVATARS_BOT

    class_data = galeria.get(ckey)

    if not class_data:
        return galeria.get("aventureiro", {}).get(gen, "")

    return class_data.get(gen, "")

def get_primary_damage_profile(player_class: str) -> dict:
    pc = (player_class or "").lower()
    return CLASS_PRIMARY_DAMAGE.get(
        pc,
        {"stat_key": "forca", "type": "fisico", "scales_with": "forca"},
    )

def get_stat_modifiers(player_class: str) -> dict:
    base = CLASSES_DATA.get((player_class or "").lower(), {})
    return base.get("stat_modifiers", {})