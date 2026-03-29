# modules/game_data/items_consumables.py
# (VERSÃO CORRIGIDA: Itens Especiais removidos do mercado)

CONSUMABLES_DATA = {
    # --- POÇÕES & ALIMENTOS ---
    "frasco_com_agua": {
        "display_name": "Frasco com Água", "emoji": "💧", "type": "reagent",
        "description": "A base para a maioria das poções.",
        "icon_url": "https://raw.githubusercontent.com/SeuUsuario/SeuRepositorio/main/potion_red_small.webp", 
        "stackable": True
    },
    "pocao_cura_leve": {
        "display_name": "Poção de Cura Leve", "emoji": "❤️", "type": "potion",
        "category": "consumivel", "description": "Uma pequena e simples poção de cura 50 HP.",
        "stackable": True,
        "icon_url": "/static/items/potion_red_small.png", 
        "effects": {"heal": 50}
    },
    "pocao_cura_media": {
        "display_name": "Poção de Cura Média", "emoji": "❤️‍🩹", "type": "potion",
        "category": "consumivel", "description": "Recupera 150 HP.",
        "stackable": True, 
        "icon_url": "https://raw.githubusercontent.com/SeuUsuario/SeuRepositorio/main/potion_red_small.webp",
        "effects": {"heal": 150}
    },
    "pocao_energia_fraca": {
        "display_name": "Poção de Energia Fraca", "emoji": "⚡️", "type": "potion",
        "category": "consumivel", "description": "Recupera 10 Energia.",
        "stackable": True, 
        "icon_url": "https://raw.githubusercontent.com/SeuUsuario/SeuRepositorio/main/potion_red_small.webp",
        "effects": {"add_energy": 10}
    },
    "frasco_sabedoria": {
        "display_name": "Frasco de Sabedoria", "emoji": "🧠", "type": "potion",
        "category": "consumivel", "description": "Concede 500 XP.",
        "stackable": True, 
        "icon_url": "https://raw.githubusercontent.com/SeuUsuario/SeuRepositorio/main/potion_red_small.webp",
        "effects": {"add_xp": 500}
    },
    "seiva_escura": {
        "display_name": "Seiva Escura", "emoji": "🩸", 
        "type": "consumivel", "category": "buff",
        "description": "+10 Vida Máxima por 60 min.", "stackable": True,
        "icon_url": "https://raw.githubusercontent.com/SeuUsuario/SeuRepositorio/main/potion_red_small.webp",
        "on_use": {"effect_id": "buff_hp_flat", 
                   "duration_sec": 3600}
    },

    # --- TICKETS E ACESSOS (BLOQUEADOS NO MERCADO) ---
    "fragmento_bravura": {
        "display_name": "Fragmento de Bravura", "emoji": "🏅", 
        "type": "especial", "category": "evento", 
        "description": "Obtido ao defender o reino.", 
        "stackable": True,
        "icon_url": "https://raw.githubusercontent.com/SeuUsuario/SeuRepositorio/main/potion_red_small.webp",
        "tradable": False # 🔴 BLOQUEADO
    },
    "ticket_defesa_reino": {
        "display_name": "Ticket de Defesa", "emoji": "🎟️", 
        "type": "event_ticket", "category": "evento", 
        "description": "Entrada para Defesa do Reino.", 
        "icon_url": "https://raw.githubusercontent.com/SeuUsuario/SeuRepositorio/main/potion_red_small.webp",
        "stackable": True,
        "tradable": False # 🔴 BLOQUEADO
    },
    "ticket_arena": {
        "display_name": "Entrada da Arena", "emoji": "🎟️", 
        "type": "event_ticket", "category": "evento", 
        "description": "Entrada extra para Arena PvP.", 
        "icon_url": "https://raw.githubusercontent.com/SeuUsuario/SeuRepositorio/main/potion_red_small.webp",
        "stackable": True,
        "on_use": {"effect": "add_pvp_entries", "value": 1},
        "tradable": False # 🔴 BLOQUEADO
    },
    "chave_da_catacumba": {
        "display_name": "Chave da Catacumba", "emoji": "🗝", 
        "type": "especial", "category": "especial", 
        "description": "Abre a Catacumba do Reino.", 
        "icon_url": "https://raw.githubusercontent.com/SeuUsuario/SeuRepositorio/main/potion_red_small.webp",
        "stackable": True,
        "tradable": False # 🔴 BLOQUEADO
    },
    "cristal_de_abertura": {
        "display_name": "Cristal de Abertura", "emoji": "🔹", 
        "type": "especial", "category": "especial", 
        "description": "Chave arcana para Dungeons.", 
        "icon_url": "https://raw.githubusercontent.com/SeuUsuario/SeuRepositorio/main/potion_red_small.webp",
        "stackable": True,
        "tradable": False # 🔴 BLOQUEADO
    },

    # --- ESPECIAIS / UTILITÁRIOS ---
    "pedra_do_aprimoramento": {
        "display_name": "Pedra de Aprimoramento", "emoji": "✨", 
        "type": "consumivel", "category": "consumivel", 
        "icon_url": "https://raw.githubusercontent.com/SeuUsuario/SeuRepositorio/main/potion_red_small.webp",
        "stackable": True, "value": 300
    },
    "pergaminho_durabilidade": {
        "display_name": "Pergaminho de Durabilidade", "emoji": "📜", 
        "description": "Restaura a durabilidade de todos os seus equipamentos.",
        "type": "consumivel", "category": "consumivel", 
        "icon_url": "https://raw.githubusercontent.com/SeuUsuario/SeuRepositorio/main/potion_red_small.webp",
        "stackable": True, "value": 150
    },
    "nucleo_forja_comum": {
        "display_name": "Núcleo de Forja Comum", "emoji": "🔥", 
        "type": "material", "category": "consumivel", 
        "icon_url": "https://raw.githubusercontent.com/SeuUsuario/SeuRepositorio/main/potion_red_small.webp",
        "stackable": True, "value": 150
    },
    "nucleo_forja_fraco": {
        "display_name": "Núcleo de Forja Fraco", "emoji": "🔥", 
        "type": "material", "category": "consumivel", 
        "icon_url": "https://raw.githubusercontent.com/SeuUsuario/SeuRepositorio/main/potion_red_small.webp",
        "stackable": True, "value": 40
    },
    "sigilo_protecao": {
        "display_name": "Sigilo de Proteção",
        "emoji": "🛡️", 
        "type": "consumable",
        "stackable": True, 
        "description": "Um selo mágico imbuído com energia defensiva. Concede proteção temporária ou é usado em receitas de aprimoramento.",
        "category": "material",
        "icon_url": "https://raw.githubusercontent.com/SeuUsuario/SeuRepositorio/main/potion_red_small.webp",
        "tradable": False # 🔴 BLOQUEADO
    },
    "gems": {
        "display_name": "Diamante", "emoji": "💎", 
        "type": "currency", "stackable": True, 
        "description": "Moeda premium.",
        "icon_url": "https://raw.githubusercontent.com/SeuUsuario/SeuRepositorio/main/potion_red_small.webp",
        "tradable": False # 🔴 BLOQUEADO (Segurança extra)
    },
    
    # --- EVENTO DE NATAL ---
    "presente_perdido": {
        "display_name": "Presente Perdido",
        "emoji": "🎁",
        "type": "material",
        "description": "Um presente que caiu do trenó. O Noel troca por recompensas.",
        "stackable": True,
        "icon_url": "https://raw.githubusercontent.com/SeuUsuario/SeuRepositorio/main/potion_red_small.webp",
        "category": "evento"
    },
    
    "presente_dourado": {
        "display_name": "Presente Dourado",
        "emoji": "🎁🌟",
        "type": "material",
        "description": "Um presente raro e brilhante! Troque por visuais exclusivos.",
        "icon_url": "https://raw.githubusercontent.com/SeuUsuario/SeuRepositorio/main/potion_red_small.webp",
        "stackable": True,
        "category": "evento"
    },
}