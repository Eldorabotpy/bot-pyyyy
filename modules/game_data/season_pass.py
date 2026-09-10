# modules/game_data/season_pass.py

XP_POR_NIVEL_PASSE = 100

RECOMPENSAS_PASSE = {}

# O GERADOR COMPLETO: Matemática Modesta + Coleção S1 (1 a 100)
for i in range(1, 101):
    
    # ==========================================
    # 1. BASE DOS NÍVEIS (Modesto)
    # ==========================================
    ouro_free = 50 + (i * 2) 
    free = {"tipo": "gold", "qtd": ouro_free, "label": f"{ouro_free} Ouro 💰"}
    
    gemas_premium = 5 + (i // 10) 
    ouro_premium = 150 + (i * 5)
    
    if i % 2 == 0:
        premium = {"tipo": "gold", "qtd": ouro_premium, "label": f"{ouro_premium} Ouro extra 💰"}
    else:
        premium = {"tipo": "gems", "qtd": gemas_premium, "label": f"{gemas_premium} Gemas 💎"}

    # ==========================================
    # 2. ITENS A CADA 5 NÍVEIS (Poções e Pó)
    # ==========================================
    if i % 5 == 0 and i % 10 != 0:
        free = {"tipo": "item", "id": "pergaminho_de_reparo", "qtd": 2, "label": "2x Pergaminho de Reparo 📜"}
        premium = {"tipo": "item", "id": "sigilo_de_protecao", "qtd": 3, "label": "3x Sigilo de Protecao 🛡️"}

    # ==========================================
    # 3. MARCOS ÉPICOS (A cada 10 níveis)
    # ==========================================
    if i % 10 == 0:
        if i % 50 == 0:
            free = {"tipo": "item", "id": "pergaminho_de_reparo", "qtd": 1, "label": "1x Pergaminho de Reparo 📜"}
        else:
            free = {"tipo": "item", "id": "sigilo_de_protecao", "qtd": 1, "label": "1x Sigilo de Protecao 🛡️"}
        
        premium = {"tipo": "item", "id": "sigilo_protecao", "qtd": 5, "label": "5x Sigilo de Protecao 🛡️"}

    # ==========================================
    # 4. ITENS CUSTOMIZADOS E DINÂMICOS (Genero)
    # ==========================================
    if i == 1:
        # Em vez de Avatar, damos um Kit Inicial de Gemas ou Poções
        premium = {
            "tipo": "gems", 
            "qtd": 5, 
            "label": "5 Gemas 💎"
        }
        
    elif i == 10:
        # Removida a skin daqui para manter apenas a do nível 100
        premium = {
            "tipo": "item", 
            "id": "pocao_cura_grande", 
            "qtd": 5, 
            "label": "5x Poção de Cura (G) 🧪"
        }
                
    elif i == 30:
        # Banner X no Nível 30
        premium = {
            "tipo": "banner", 
            "id": "banner_xiongmaoren_s1", 
            "label": "Banner Xiongmaoren S1"
        }
        
    elif i == 50:
        # Avatar Nível 50 - Lê o Gênero do Jogador
        premium = {
            "tipo": "avatar_dinamico", 
            "id_m": "avatar_xiongmaoren_s1_m",       # Se for Homem
            "id_f": "avatar_xiongmaoren_s1_f",       # Se for Mulher
            "label": "Avatar 🐼 Xiongmaoren S1"
        }
        
    elif i == 100:
        free = {"tipo": "avatar", "id": "avatar_mestre_free", "label": "Avatar Mestre 🏆"}
        # Skin Suprema Nível 100 - Lê o Gênero
        premium = {
            "tipo": "skin_dinamica", 
            "id_m": "skin_xiongmaoren_s1_m", 
            "id_f": "skin_xiongmaoren_s1_f", 
            "label": "🐼 Xiongmaoren_s1 "
        }

    # Salva no dicionário do passe
    RECOMPENSAS_PASSE[i] = {
        "free": free,
        "premium": premium
    }

def adicionar_xp_passe(
    player_data: dict,
    xp_ganho: int
) -> tuple[bool, int, int]:

    # ==========================================================
    # 🎫 GARANTE ESTRUTURA VÁLIDA DO PASSE
    # ==========================================================

    passe = player_data.get("passe_batalha")

    if not isinstance(passe, dict):
        passe = {}

    passe.setdefault("level", 1)
    passe.setdefault("xp", 0)
    passe.setdefault("is_premium", False)
    passe.setdefault("resgatados_free", [])
    passe.setdefault("resgatados_premium", [])

    # Blindagem para dados antigos/corrompidos
    try:
        passe["level"] = int(
            passe.get("level", 1) or 1
        )
    except (TypeError, ValueError):
        passe["level"] = 1

    try:
        passe["xp"] = int(
            passe.get("xp", 0) or 0
        )
    except (TypeError, ValueError):
        passe["xp"] = 0

    try:
        xp_ganho = int(xp_ganho or 0)
    except (TypeError, ValueError):
        xp_ganho = 0

    player_data["passe_batalha"] = passe

    # ==========================================================
    # 🌟 ENTREGA XP
    # ==========================================================

    passe["xp"] += max(0, xp_ganho)

    subiu_nivel = False

    while passe["xp"] >= XP_POR_NIVEL_PASSE:
        passe["level"] += 1
        passe["xp"] -= XP_POR_NIVEL_PASSE
        subiu_nivel = True

    return (
        subiu_nivel,
        passe["level"],
        passe["xp"]
    )