# modules/season_manager.py
from bson import ObjectId
from modules.player.core import users_collection
from modules.game_data.season_pass import adicionar_xp_passe

def dar_xp_passe(player_id, xp_ganho):
    """Adiciona XP ao passe e processa level up se necessário"""
    player = users_collection.find_one({"_id": ObjectId(player_id)})
    if not player:
        return None

    try:
        antigo_level = int((player.get("passe_batalha") or {}).get("level", 1) or 1)
    except (TypeError, ValueError):
        antigo_level = 1
    _, novo_level, novo_xp = adicionar_xp_passe(player, xp_ganho)

    # Usa a mesma progressão e o mesmo limite de nível dos demais fluxos.
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
