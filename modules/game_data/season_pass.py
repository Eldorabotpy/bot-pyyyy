# modules/game_data/season_pass.py

XP_POR_NIVEL_PASSE = 100
NIVEIS_PASSE_POR_TEMPORADA = 100
FRAGMENTOS_SKIN_GRATIS_POR_TEMPORADA = 25
FRAGMENTOS_SKIN_PREMIUM_EXTRA_POR_TEMPORADA = 60
FRAGMENTOS_SKIN_POR_MARCO_PREMIUM = 5

# Em uma temporada de 100 níveis, a faixa grátis dá 1 fragmento a cada
# quatro níveis. A faixa Premium acrescenta 5 fragmentos a cada oito níveis.
INTERVALO_FRAGMENTOS_GRATIS = NIVEIS_PASSE_POR_TEMPORADA // FRAGMENTOS_SKIN_GRATIS_POR_TEMPORADA
INTERVALO_FRAGMENTOS_PREMIUM = NIVEIS_PASSE_POR_TEMPORADA // (FRAGMENTOS_SKIN_PREMIUM_EXTRA_POR_TEMPORADA // FRAGMENTOS_SKIN_POR_MARCO_PREMIUM)
NIVEIS_FRAGMENTOS_GRATIS = set(range(INTERVALO_FRAGMENTOS_GRATIS, NIVEIS_PASSE_POR_TEMPORADA + 1, INTERVALO_FRAGMENTOS_GRATIS))
NIVEIS_FRAGMENTOS_PREMIUM = set(range(INTERVALO_FRAGMENTOS_PREMIUM, NIVEIS_PASSE_POR_TEMPORADA + 1, INTERVALO_FRAGMENTOS_PREMIUM))

RECOMPENSAS_PASSE = {}

# O GERADOR COMPLETO: Matemática Modesta + Coleção S1 (1 a 100)
for i in range(1, NIVEIS_PASSE_POR_TEMPORADA + 1):
    
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
        premium = {"tipo": "item", "id": "sigilo_de_protecao", "qtd": 3, "label": "3x Sigilo de Proteção 🛡️"}

    # ==========================================
    # 3. MARCOS ÉPICOS (A cada 10 níveis)
    # ==========================================
    if i % 10 == 0:
        if i % 50 == 0:
            free = {"tipo": "item", "id": "pergaminho_de_reparo", "qtd": 1, "label": "1x Pergaminho de Reparo 📜"}
        else:
            free = {"tipo": "item", "id": "sigilo_de_protecao", "qtd": 1, "label": "1x Sigilo de Proteção 🛡️"}
        
        premium = {"tipo": "item", "id": "sigilo_de_protecao", "qtd": 5, "label": "5x Sigilo de Proteção 🛡️"}

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
        
    # Salva no dicionário do passe
    RECOMPENSAS_PASSE[i] = {
        "free": free,
        "premium": premium,
        "fragmentos_skin": {
            "free": 1 if i in NIVEIS_FRAGMENTOS_GRATIS else 0,
            "premium": FRAGMENTOS_SKIN_POR_MARCO_PREMIUM if i in NIVEIS_FRAGMENTOS_PREMIUM else 0,
        },
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

    passe["level"] = min(
        max(1, passe["level"]),
        NIVEIS_PASSE_POR_TEMPORADA,
    )
    passe["xp"] = max(0, passe["xp"])
    if passe["level"] >= NIVEIS_PASSE_POR_TEMPORADA:
        passe["xp"] = 0

    player_data["passe_batalha"] = passe

    # ==========================================================
    # 🌟 ENTREGA XP
    # ==========================================================

    if passe["level"] >= NIVEIS_PASSE_POR_TEMPORADA:
        return False, passe["level"], 0

    passe["xp"] += max(0, xp_ganho)

    subiu_nivel = False

    while (
        passe["xp"] >= XP_POR_NIVEL_PASSE
        and passe["level"] < NIVEIS_PASSE_POR_TEMPORADA
    ):
        passe["level"] += 1
        passe["xp"] -= XP_POR_NIVEL_PASSE
        subiu_nivel = True

    if passe["level"] >= NIVEIS_PASSE_POR_TEMPORADA:
        passe["xp"] = 0
    return (
        subiu_nivel,
        passe["level"],
        passe["xp"]
    )
