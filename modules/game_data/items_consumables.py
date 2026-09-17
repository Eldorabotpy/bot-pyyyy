# modules/game_data/items_consumables.py
# (VERSÃO CORRIGIDA: Itens Especiais removidos do mercado)

CONSUMABLES_DATA = {
    # --- POÇÕES & ALIMENTOS ---
    "frasco_com_agua": {
        "display_name": "Frasco com Água", "emoji": "💧", 
        "type": "reagent",
        "description": "A base para a maioria das poções.",
        "stackable": True
    },
    "pocao_cura_leve": {
        "display_name": "Poção de Cura P", "emoji": "❤️", 
        "type": "consumivel",
        "category": "consumivel", "description": "Uma pequena e simples poção de cura 100 HP.",
        "stackable": True,
        "effects": {"heal": 100},
        "price": 100
    },
    "pocao_cura_media": {
        "display_name": "Poção de Cura M",
        "emoji": "❤️‍🩹",
        "icon_url": (
            "https://raw.githubusercontent.com/"
            "Eldorabotpy/static-img/main/assets/"
            "itens/consumiveis/pocao_cura_media.png"
        ),
        "type": "consumivel",
        "category": "consumivel",
        "description": "Recupera 300 HP.",
        "stackable": True,
        "effects": {"heal": 300},
        "price": 300
    },
    "pocao_cura_grande": {
        "display_name": "Poção de Cura G", "emoji": "❤️", 
        "type": "consumivel",
        "category": "consumivel", "description": "Uma grande poção de cura 1000 HP.",
        "stackable": True, 
        "effects": {"heal": 1000},
        "price": 1000
    },
    "pocao_mana_leve": {
        "display_name": "Poção de Mana Pequena", "emoji": "💧", 
        "type": "consumivel",
        "category": "consumivel", "description": "Uma pequena e simples poção de Mana 100 MP.",
        "stackable": True,
        "effects": {"mana": 100},
        "price": 100  
    },
    "pocao_mana_media": {
        "display_name": "Poção de Mana M",
        "emoji": "💧",
        "icon_url": (
            "https://raw.githubusercontent.com/"
            "Eldorabotpy/static-img/main/assets/"
            "itens/consumiveis/pocao_mana_media.png"
        ),
        "type": "consumivel",
        "category": "consumivel",
        "description": "Recupera 300 MP.",
        "stackable": True,
        "effects": {"mana": 300},
        "price": 300
    },
    "pocao_mana_grande": {
        "display_name": "Poção de Mana G", "emoji": "💧", 
        "type": "consumivel",
        "category": "consumivel", "description": "Uma grande poção de mana 1000 MP.",
        "stackable": True,
        "effects": {"mana": 1000},
        "price": 1000
    },
        # ==========================================================
    # ✨ ELIXIRES DE EXPERIÊNCIA — BRUXA DA FLORESTA
    # ==========================================================

    "elixir_xp_dobrado_10m": {
        "display_name": "Elixir de Experiência",
        "emoji": "✨",
        "type": "consumivel",
        "category": "consumivel",
        "description": "Dobra o XP de combate recebido durante 10 minutos.",
        "stackable": True,
        "tradable": False,
        "on_use": {
            "effect": "xp_boost",
            "multiplier": 2.0,
            "duration_seconds": 600
        }
    },

    "elixir_xp_dobrado_30m": {
        "display_name": "Elixir Superior de Experiência",
        "emoji": "🌟",
        "type": "consumivel",
        "category": "consumivel",
        "description": "Dobra o XP de combate recebido durante 30 minutos.",
        "stackable": True,
        "tradable": False,
        "on_use": {
            "effect": "xp_boost",
            "multiplier": 2.0,
            "duration_seconds": 1800
        }
    },

    "fragmento_bravura": {
        "display_name": "Fragmento de Bravura", "emoji": "🏅", 
        "type": "especial", "category": "evento", 
        "description": "Obtido ao defender o reino.", 
        "stackable": True,
        "tradable": False # 🔴 BLOQUEADO
    },
    "ticket_de_arena": {
        "display_name": "Entrada da Arena", "emoji": "🎟️", 
        "type": "event_ticket", "category": "evento", 
        "description": "Entrada extra para Arena PvP.", 
        "stackable": True,
        "on_use": {"effect": "add_pvp_entries", "value": 1},
        "tradable": False # 🔴 BLOQUEADO
    },

    # ============================================================
    # 📜 ITEM DE HISTÓRIA — GUILDA DOS AVENTUREIROS
    # ============================================================

    "carta_recomendacao": {
        "display_name": "Carta de Recomendação",
        "emoji": "📜",

        "icon_url": (
            "https://raw.githubusercontent.com/"
            "Eldorabotpy/static-img/main/assets/"
            "itens/consumiveis/carta_recomendacao.png"
        ),

        "type": "especial",
        "category": "missao",

        "description": (
            "Documento oficial emitido pela Arquimaga Selene. "
            "Reconhece seu portador como alguém digno de se "
            "apresentar à Guilda dos Aventureiros."
        ),

        "stackable": True,
        "tradable": False,
    },

    # --- ESPECIAIS / UTILITÁRIOS ---
    "pedra_de_aprimoramento": {
        "display_name": "Pedra de Aprimoramento",
        "emoji": "✨",
        "icon_url": (
            "https://raw.githubusercontent.com/"
            "Eldorabotpy/static-img/main/assets/"
            "itens/consumiveis/pedra_de_aprimoramento.png"
        ),
        "type": "consumivel",
        "category": "consumivel",
        "stackable": True,
        "price": 300
    },
    "pergaminho_de_reparo": {
        "display_name": "Pergaminho de Reparo",
        "emoji": "📜",
        "icon_url": (
            "https://raw.githubusercontent.com/"
            "Eldorabotpy/static-img/main/assets/"
            "itens/consumiveis/pergaminho_de_reparo.png"
        ),
        "description": (
            "Restaura a durabilidade de todos "
            "os seus equipamentos."
        ),
        "type": "consumivel",
        "category": "consumivel",
        "stackable": True,
        "price": 1000
    },
    "nucleo_de_forja": {
        "display_name": "Núcleo de Forja",
        "emoji": "🔥",
        "icon_url": (
            "https://raw.githubusercontent.com/"
            "Eldorabotpy/static-img/main/assets/"
            "itens/consumiveis/nucleo_de_forja.png"
        ),
        "type": "consumivel",
        "category": "consumivel",
        "stackable": True,
        "price": 150
    },

    "sigilo_de_protecao": {
        "display_name": "Sigilo de Proteção",
        "emoji": "🛡️",
        "icon_url": (
            "https://raw.githubusercontent.com/"
            "Eldorabotpy/static-img/main/assets/"
            "itens/consumiveis/sigilo_de_protecao.png"
        ),
        "type": "consumivel",
        "stackable": True,
        "description": (
            "Um selo mágico imbuído com energia defensiva. "
            "Concede proteção temporária ou é usado em "
            "receitas de aprimoramento."
        ),
        "category": "consumivel",
        "tradable": False
    },
    "gems": {
        "display_name": "Diamante", "emoji": "💎", 
        "type": "currency", "stackable": True, 
        "description": "Moeda premium.",
        "tradable": False # 🔴 BLOQUEADO (Segurança extra)
    },
    
    # --- EVENTO DE NATAL ---
    "presente_perdido": {
        "display_name": "Presente Perdido",
        "emoji": "🎁",
        "type": "material",
        "description": "Um presente que caiu do trenó. O Noel troca por recompensas.",
        "stackable": True,
        "category": "evento"
    },
    
    "presente_dourado": {
        "display_name": "Presente Dourado",
        "emoji": "🎁🌟",
        "type": "material",
        "description": "Um presente raro e brilhante! Troque por visuais exclusivos.",
        "stackable": True,
        "category": "evento"
    },
}