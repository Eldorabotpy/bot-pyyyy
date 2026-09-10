# modules/season_manager.py
from bson import ObjectId
from modules.player.core import users_collection
from modules.game_data.season_pass import XP_POR_NIVEL_PASSE, RECOMPENSAS_PASSE

def dar_xp_passe(player_id, xp_ganho):
    """Adiciona XP ao passe e processa level up se necessário"""
    player = users_collection.find_one({"_id": ObjectId(player_id)})
    if not player:
        return None

    # 👇 1. Puxa o dicionário. O "or {}" garante que nunca seja None.
    passe = player.get("passe_batalha") or {}

    # 👇 2. A BLINDAGEM: Se a chave 'level' não existir dentro do dic, assume Nível 1
    antigo_level = passe.get("level", 1)
    antigo_xp = passe.get("xp", 0)
    
    novo_xp = antigo_xp + xp_ganho
    novo_level = antigo_level

    # Lógica de subir de nível (loop caso ganhe muito XP de uma vez)
    while novo_xp >= XP_POR_NIVEL_PASSE:
        novo_xp -= XP_POR_NIVEL_PASSE
        novo_level += 1

    # 👇 Salva as informações novas direto no banco
    users_collection.update_one(
        {"_id": ObjectId(player_id)},
        {
            "$set": {
                "passe_batalha.level": novo_level,
                "passe_batalha.xp": novo_xp
            }
        }
    )

    if novo_level > antigo_level:
        return {"level_up": True, "novo_level": novo_level}
    
    return {"level_up": False, "xp_atual": novo_xp}