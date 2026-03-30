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
        "masculino": "https://github.com/user-attachments/assets/1c6ceff0-cb86-431c-a97f-7e7a0a016410",
        "feminino": "https://github.com/user-attachments/assets/9e817891-2ed2-40f7-ba51-e2f0bb618c95"
    },
    "aventureiro": {
        "masculino": "https://github.com/user-attachments/assets/1c6ceff0-cb86-431c-a97f-7e7a0a016410",
        "feminino": "https://github.com/user-attachments/assets/9e817891-2ed2-40f7-ba51-e2f0bb618c95"
    },
    
    "guerreiro": {
        "masculino": "https://github.com/user-attachments/assets/4662d025-505b-4816-8df7-9db66412467a",
        "feminino": "https://github.com/user-attachments/assets/97249aea-f6dc-4ce9-84f3-432b6146d63b"
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
        "masculino": "https://github.com/user-attachments/assets/321666e0-7f41-4d6a-b760-92e94cd62bd9",
        "feminino": "https://github.com/user-attachments/assets/402104bc-a2ea-4477-b641-c6eab30520ae"
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
        "masculino": "https://github.com/user-attachments/assets/5c3ac838-5962-4b20-a47f-9888e92db8a8",
        "feminino": "https://github.com/user-attachments/assets/10fb4d6d-5b9c-4f26-baa1-39132ed82dc8"
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
        "masculino": "https://github.com/user-attachments/assets/eace58a1-a49f-45d2-a7ef-eb1775ac0c00",
        "feminino": "https://github.com/user-attachments/assets/f8063071-2097-41f2-9c99-8a522bc06650"
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
        "masculino": "https://github.com/user-attachments/assets/807fc25d-0e25-4f9c-8af3-e4e3f5b741d1",
        "feminino": "https://github.com/user-attachments/assets/3e7bdd09-984e-4ecc-aa4f-874d6f58bff2"
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
        "masculino": "https://github.com/user-attachments/assets/84825dae-0a66-4435-825e-661b1f51e924",
        "feminino": "https://github.com/user-attachments/assets/67025149-f9fa-47ea-a4ae-3be21bd537df"
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
        "masculino": "https://github.com/user-attachments/assets/fe03e623-dbe5-4bc8-bd35-73fe169ccd75",
        "feminino": "https://github.com/user-attachments/assets/579e9e6a-1e79-41d0-9277-883ece55c8df"
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
        "masculino": "https://github.com/user-attachments/assets/b1b8af66-417b-47b8-b994-6ece16d2354a",
        "feminino": "https://github.com/user-attachments/assets/19f32053-34a3-483c-b22a-97cebf842665"
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