# modules/player/core.py
# (VERSÃO CORRIGIDA: Com sanitização de chaves None no inventário)

import logging
import asyncio
from typing import Optional, Dict, Any

# Conexão centralizada
from modules.database import players_col as players_collection

# --- Globais ---
_player_cache: Dict[int, Dict[str, Any]] = {}
_player_cache_lock: asyncio.Lock = asyncio.Lock()

logger = logging.getLogger(__name__)

if players_collection is None:
    logger.error("⚠️ AVISO: players_collection é None. Verifique modules/database.py")

# ====================================================================
# FUNÇÕES SÍNCRONAS
# ====================================================================

def _load_player_from_db_sync(user_id: int) -> Optional[dict]:
    if players_collection is None: return None
    try:
        player_doc = players_collection.find_one({"_id": user_id})
        if player_doc:
            player_copy = dict(player_doc)
            player_copy.pop("_id", None)
            return player_copy
        return None
    except Exception:
        logger.exception(f"Erro ao buscar player {user_id} no DB (sync).")
        return None

def _save_player_data_sync(user_id: int, player_info: dict) -> None:
    from . import queries, actions # imports locais
    
    if players_collection is None: return

    try:
        to_save = dict(player_info)
        to_save.pop("_id", None)

        try:
            to_save["character_name_normalized"] = queries._normalize_char_name(to_save.get("character_name", ""))
        except Exception: pass
        
        try:
            actions.sanitize_and_cap_energy(to_save)
        except Exception: pass

        # --- CORREÇÃO DE SEGURANÇA (SANITIZAÇÃO DO INVENTÁRIO) ---
        # Remove chaves None e garante que todas sejam strings para o MongoDB
        if "inventory" in to_save and isinstance(to_save["inventory"], dict):
            clean_inventory = {}
            for item_id, quantity in to_save["inventory"].items():
                if item_id is not None:
                    # Converte chave para string (ex: números ou UUIDs viram texto)
                    clean_inventory[str(item_id)] = quantity
            to_save["inventory"] = clean_inventory
        # ---------------------------------------------------------

        players_collection.replace_one({"_id": user_id}, to_save, upsert=True)
    except Exception:
        logger.exception(f"Erro ao salvar player {user_id} no DB (sync).")

# ====================================================================
# FUNÇÕES ASSÍNCRONAS (INTERFACE)
# ====================================================================

async def get_player_data(user_id: int) -> Optional[dict]:
    from . import actions, stats, inventory

    if players_collection is None: return None

    async with _player_cache_lock:
        cached = _player_cache.get(user_id)
        if cached is not None:
            return dict(cached)

    try:
        raw_data = await asyncio.to_thread(_load_player_from_db_sync, user_id)
    except Exception:
        raw_data = None

    if raw_data is None: return None

    data = dict(raw_data)
    data["user_id"] = user_id

    # --- Lógica de Migração e Saneamento ---
    try:
        changed = False
        
        # 1. Ouro/Inventário
        if hasattr(inventory, "_sanitize_and_migrate_gold"):
            res = inventory._sanitize_and_migrate_gold(data)
            if asyncio.iscoroutine(res): await res
        
        # 2. Energia
        if actions._apply_energy_autoregen_inplace(data): changed = True
        
        # 3. Stats
        if await stats._sync_all_stats_inplace(data): changed = True

        # 4. Mana Base
        if 'mana' not in data:
            data['mana'] = 50; data['max_mana'] = 50
            changed = True

        # 5. Skills (Lista -> Dict)
        if 'skills' not in data or isinstance(data.get('skills'), list):
            old_list = data.get('skills', []) if isinstance(data.get('skills'), list) else []
            new_dict = {sid: {"rarity": "comum", "progress": 0} for sid in old_list if sid}
            data['skills'] = new_dict
            changed = True
        else:
            # Garante campo progress em skills antigas
            for sk_id, sk_data in data['skills'].items():
                if isinstance(sk_data, dict) and "progress" not in sk_data:
                    sk_data["progress"] = 0
                    changed = True

    except Exception:
        logger.exception("Erro nas migrações de player data.")

    # Atualiza Cache
    async with _player_cache_lock:
        _player_cache[user_id] = dict(data)

    # Salva se houve mudança
    if locals().get('changed', False): 
        asyncio.create_task(save_player_data(user_id, data))

    return dict(data)

async def save_player_data(user_id: int, player_info: dict) -> None:
    if players_collection is None: return

    to_save = dict(player_info)
    to_save["user_id"] = user_id

    try:
        await asyncio.to_thread(_save_player_data_sync, user_id, to_save)
    except Exception:
        logger.exception(f"Erro ao salvar {user_id}.")
    finally:
        async with _player_cache_lock:
            _player_cache[user_id] = dict(to_save)

async def clear_player_cache(user_id: int) -> bool:
    async with _player_cache_lock:
        if user_id in _player_cache:
            del _player_cache[user_id]
            return True
        return False

async def clear_all_player_cache() -> int:
    async with _player_cache_lock:
        num = len(_player_cache)
        _player_cache.clear()
        return num