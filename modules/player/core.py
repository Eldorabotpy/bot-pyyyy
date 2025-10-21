# Em modules/player/core.py
import os
import logging
import time
import pymongo
from pymongo.errors import ConnectionFailure

MONGO_CONNECTION_STRING = os.environ.get("MONGO_CONNECTION_STRING")
players_collection = None
_player_cache = {}

if not MONGO_CONNECTION_STRING:
    logging.error("CRÍTICO: MONGO_CONNECTION_STRING não definida!")
else:
    try:
        client = pymongo.MongoClient(MONGO_CONNECTION_STRING)
        client.admin.command('ping')
        logging.info("✅ Conexão com o MongoDB estabelecida!")
        db = client.get_database("eldora_db")
        players_collection = db.get_collection("players")
        players_collection.create_index("character_name_normalized")
    except Exception as e:
        logging.error(f"CRÍTICO: Falha na conexão com o MongoDB: {e}")

def get_player_data(user_id: int) -> dict | None:

    from . import actions, stats
    
    if user_id in _player_cache:
        raw_data = _player_cache[user_id].copy()
    else:
        raw_data = _load_player_from_db(user_id)
        if raw_data:
            _player_cache[user_id] = raw_data.copy()

    if not raw_data:
        return None

    data = raw_data
    data["user_id"] = user_id
    is_newly_updated = False
    if 'mana' not in data:    
        data['mana'] = 50 
        data['max_mana'] = 50 
        is_newly_updated = True
        
    if 'skills' not in data:
        data['skills'] = [] 
        is_newly_updated = True

    changed_by_energy = actions._apply_energy_autoregen_inplace(data)
    changed_by_sync = stats._sync_all_stats_inplace(data)

    if changed_by_energy or changed_by_sync or is_newly_updated:
        save_player_data(user_id, data)
            
    return data

def save_player_data(user_id: int, player_info: dict) -> None:
    from . import queries, actions # Importações locais para evitar ciclos
    
    if players_collection is None: return
    
    _player_cache[user_id] = player_info.copy()
    player_info.pop('_id', None)
    
    # Normalizações antes de salvar
    player_info["character_name_normalized"] = queries._normalize_char_name(player_info.get("character_name", ""))
    actions.sanitize_and_cap_energy(player_info)
    
    players_collection.replace_one({"_id": user_id}, player_info, upsert=True)

def _load_player_from_db(user_id: int) -> dict | None:
    if players_collection is None: return None
    player_doc = players_collection.find_one({"_id": user_id})
    if player_doc:
        player_doc.pop('_id', None)
    return player_doc

def clear_player_cache(user_id: int) -> bool:
    if user_id in _player_cache:
        del _player_cache[user_id]
        return True
    return False

def clear_all_player_cache() -> int:
    num_items = len(_player_cache)
    _player_cache.clear()
    return num_items