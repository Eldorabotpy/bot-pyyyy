# modules/player/core.py
# (VERSÃO PONTE: Redireciona IDs antigos para o Novo Sistema automaticamente)

import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from typing import Optional, Dict, Any, Union
from bson import ObjectId

try:
    from modules.database import players_col as players_collection
except ImportError:
    players_collection = None

# --- Globais ---
_player_cache: Dict[Union[int, str], Dict[str, Any]] = {}
_player_cache_lock: asyncio.Lock = asyncio.Lock()

logger = logging.getLogger(__name__)

if players_collection is None:
    logger.error("⚠️ CRÍTICO: players_collection é None.")
else:
    db = players_collection.database
    users_collection = db["users"]

# ====================================================================
# FUNÇÕES AUXILIARES
# ====================================================================
def to_object_id(user_id: Any) -> Optional[ObjectId]:
    if isinstance(user_id, ObjectId): return user_id
    if isinstance(user_id, str) and ObjectId.is_valid(user_id): return ObjectId(user_id)
    return None

def get_current_char_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logged_id = context.user_data.get("logged_player_id")
    if logged_id: return str(logged_id)
    return update.effective_user.id

# ====================================================================
# FUNÇÕES SÍNCRONAS (CORE DO REDIRECIONAMENTO)
# ====================================================================

def _load_player_from_db_sync(user_id: Union[int, str]) -> Optional[dict]:
    if players_collection is None: return None
    
    try:
        # --- ROTA 1: ID Numérico (Legado) ---
        if isinstance(user_id, int):
            # [A MÁGICA]: Verifica se esse Telegram ID tem uma conta MIGRADA na coleção nova
            migrated_user = users_collection.find_one({"telegram_id_owner": user_id})
            
            if migrated_user:
                # SE TIVER: Usa a conta nova, ignorando a antiga!
                user_copy = dict(migrated_user)
                user_copy["user_id"] = str(user_copy.pop("_id"))
                return user_copy
            
            # SE NÃO TIVER: Lê do banco antigo (comportamento normal)
            player_doc = players_collection.find_one({"_id": user_id})
            if player_doc:
                player_copy = dict(player_doc)
                player_copy.pop("_id", None)
                player_copy["user_id"] = user_id
                return player_copy
            return None

        # --- ROTA 2: ID Texto (Novo Sistema) ---
        oid = to_object_id(user_id)
        if oid:
            user_doc = users_collection.find_one({"_id": oid})
            if user_doc:
                user_copy = dict(user_doc)
                user_copy["user_id"] = str(user_copy.pop("_id"))
                return user_copy
        
        return None

    except Exception:
        logger.exception(f"Erro ao buscar player {user_id} no DB.")
        return None

def _save_player_data_sync(user_id: Union[int, str], player_info: dict) -> None:
    from . import queries, actions
    if players_collection is None: return

    try:
        to_save = dict(player_info)
        to_save.pop("_id", None)
        to_save.pop("user_id", None)

        # Sanitizações básicas
        try: to_save["character_name_normalized"] = queries._normalize_char_name(to_save.get("character_name", ""))
        except: pass
        try: actions.sanitize_and_cap_energy(to_save)
        except: pass

        if "inventory" in to_save and isinstance(to_save["inventory"], dict):
            to_save["inventory"] = {str(k): v for k, v in to_save["inventory"].items() if k is not None}

        # --- ROTEAMENTO DE SALVAMENTO ---
        
        # Caso 1: ID Numérico (Código Legado tentando salvar)
        if isinstance(user_id, int):
            # [A MÁGICA]: Verifica se existe conta nova para esse ID
            migrated_user = users_collection.find_one({"telegram_id_owner": user_id})
            
            if migrated_user:
                # REDIRECIONA O SAVE PARA A COLEÇÃO NOVA!
                users_collection.update_one({"_id": migrated_user["_id"]}, {"$set": to_save})
            else:
                # Salva no banco antigo
                players_collection.replace_one({"_id": user_id}, to_save, upsert=True)
            
        # Caso 2: ID Texto (Sistema Novo)
        else:
            oid = to_object_id(user_id)
            if oid:
                users_collection.update_one({"_id": oid}, {"$set": to_save})

    except Exception:
        logger.exception(f"Erro ao salvar player {user_id}.")

# ====================================================================
# FUNÇÕES ASSÍNCRONAS
# ====================================================================
# (O restante permanece igual, pois chama as funções sync acima)

async def get_player_data(user_id: Union[int, str]) -> Optional[dict]:
    from . import actions, stats, inventory
    if players_collection is None: return None
    cache_key = str(user_id) if not isinstance(user_id, int) else user_id

    async with _player_cache_lock:
        cached = _player_cache.get(cache_key)
        if cached: return dict(cached)

    raw_data = await asyncio.to_thread(_load_player_from_db_sync, user_id)
    if not raw_data: return None

    data = dict(raw_data)
    data["user_id"] = user_id if isinstance(user_id, int) else str(user_id)

    # Migrações em memória
    try:
        changed = False
        if hasattr(inventory, "_sanitize_and_migrate_gold"):
            res = inventory._sanitize_and_migrate_gold(data)
            if asyncio.iscoroutine(res): await res
        if hasattr(inventory, "migrate_legacy_evolution_items") and inventory.migrate_legacy_evolution_items(data):
            changed = True
        if actions._apply_energy_autoregen_inplace(data): changed = True
        if await stats._sync_all_stats_inplace(data): changed = True
        
        if 'mana' not in data: 
            data['mana'] = 50; data['max_mana'] = 50; changed = True
            
        if 'skills' not in data or isinstance(data.get('skills'), list):
            old = data.get('skills', []) if isinstance(data.get('skills'), list) else []
            data['skills'] = {sid: {"rarity": "comum", "progress": 0} for sid in old if sid}
            changed = True
    except Exception: pass

    async with _player_cache_lock:
        _player_cache[cache_key] = dict(data)

    if locals().get('changed', False): 
        asyncio.create_task(save_player_data(user_id, data))

    return dict(data)

async def save_player_data(user_id: Union[int, str], player_info: dict) -> None:
    if players_collection is None: return
    to_save = dict(player_info)
    to_save["user_id"] = str(user_id) if not isinstance(user_id, int) else user_id
    cache_key = str(user_id) if not isinstance(user_id, int) else user_id

    try:
        await asyncio.to_thread(_save_player_data_sync, user_id, to_save)
    except Exception:
        logger.exception(f"Erro ao salvar {user_id}.")
    finally:
        async with _player_cache_lock:
            _player_cache[cache_key] = dict(to_save)

async def clear_player_cache(user_id: Union[int, str]) -> bool:
    cache_key = str(user_id) if not isinstance(user_id, int) else user_id
    async with _player_cache_lock:
        if cache_key in _player_cache:
            del _player_cache[cache_key]
            return True
        return False

async def clear_all_player_cache() -> int:
    async with _player_cache_lock:
        n = len(_player_cache)
        _player_cache.clear()
        return n