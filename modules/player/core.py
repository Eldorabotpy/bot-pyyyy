# modules/player/core.py
# (VERSÃO HÍBRIDA FINAL: Suporta Login Novo + Contas Antigas + Correções de Inventário)

import logging
import asyncio
from typing import Optional, Dict, Any, Union
from bson import ObjectId  # Necessário para o novo sistema

# Conexão centralizada
# Tenta importar players_col e db. Se db não vier, pegamos via players_col.database
try:
    from modules.database import players_col as players_collection
except ImportError:
    players_collection = None

# --- Globais ---
_player_cache: Dict[Union[int, str], Dict[str, Any]] = {}
_player_cache_lock: asyncio.Lock = asyncio.Lock()

logger = logging.getLogger(__name__)

if players_collection is None:
    logger.error("⚠️ CRÍTICO: players_collection é None. Verifique modules/database.py")
else:
    # --- CONFIGURAÇÃO HÍBRIDA ---
    # Usamos o mesmo banco de dados da coleção antiga para criar a nova 'users'
    db = players_collection.database
    users_collection = db["users"]

# ====================================================================
# FUNÇÕES AUXILIARES (Identificação de ID)
# ====================================================================
def to_object_id(user_id: Any) -> Optional[ObjectId]:
    """Converte string para ObjectId com segurança se for válido."""
    if isinstance(user_id, ObjectId):
        return user_id
    if isinstance(user_id, str) and ObjectId.is_valid(user_id):
        return ObjectId(user_id)
    return None

# ====================================================================
# FUNÇÕES SÍNCRONAS (Low Level)
# ====================================================================

def _load_player_from_db_sync(user_id: Union[int, str]) -> Optional[dict]:
    if players_collection is None: return None
    
    try:
        # ROTA 1: SISTEMA ANTIGO (ID Numérico / Telegram ID)
        if isinstance(user_id, int):
            player_doc = players_collection.find_one({"_id": user_id})
            if player_doc:
                player_copy = dict(player_doc)
                player_copy.pop("_id", None)
                # Garante que o user_id está presente no dict
                player_copy["user_id"] = user_id
                return player_copy
            return None

        # ROTA 2: NOVO SISTEMA (String / ObjectId)
        oid = to_object_id(user_id)
        if oid:
            # Busca na coleção NOVA ('users')
            user_doc = users_collection.find_one({"_id": oid})
            if user_doc:
                user_copy = dict(user_doc)
                # Converte o ObjectId do banco para string Python
                user_copy["user_id"] = str(user_copy.pop("_id"))
                return user_copy
        
        return None

    except Exception:
        logger.exception(f"Erro ao buscar player {user_id} no DB (sync).")
        return None

def _save_player_data_sync(user_id: Union[int, str], player_info: dict) -> None:
    from . import queries, actions # imports locais
    
    if players_collection is None: return

    try:
        to_save = dict(player_info)
        # Removemos identificadores internos para não duplicar no corpo do documento
        to_save.pop("_id", None)
        to_save.pop("user_id", None)

        # --- SANITIZAÇÕES (Mantidas do seu arquivo original) ---
        try:
            to_save["character_name_normalized"] = queries._normalize_char_name(to_save.get("character_name", ""))
        except Exception: pass
        
        try:
            actions.sanitize_and_cap_energy(to_save)
        except Exception: pass

        # Correção de Inventário (Chaves None -> String)
        if "inventory" in to_save and isinstance(to_save["inventory"], dict):
            clean_inventory = {}
            for item_id, quantity in to_save["inventory"].items():
                if item_id is not None:
                    clean_inventory[str(item_id)] = quantity
            to_save["inventory"] = clean_inventory

        # --- ROTEAMENTO DE SALVAMENTO ---
        
        # Caso 1: ID Numérico -> Salva na coleção antiga (players)
        if isinstance(user_id, int):
            players_collection.replace_one({"_id": user_id}, to_save, upsert=True)
            
        # Caso 2: ID Texto/ObjectId -> Salva na coleção nova (users)
        else:
            oid = to_object_id(user_id)
            if oid:
                # Atualiza os dados na coleção users
                users_collection.update_one({"_id": oid}, {"$set": to_save})

    except Exception:
        logger.exception(f"Erro ao salvar player {user_id} no DB (sync).")

# ====================================================================
# FUNÇÕES ASSÍNCRONAS (INTERFACE)
# ====================================================================

async def get_player_data(user_id: Union[int, str]) -> Optional[dict]:
    """
    Busca dados do jogador. Aceita INT (Legado) ou STR (Sessão Nova).
    """
    from . import actions, stats, inventory

    if players_collection is None: return None

    # Normaliza a chave de cache (String para novo, Int para velho)
    cache_key = str(user_id) if not isinstance(user_id, int) else user_id

    async with _player_cache_lock:
        cached = _player_cache.get(cache_key)
        if cached is not None:
            return dict(cached)

    try:
        raw_data = await asyncio.to_thread(_load_player_from_db_sync, user_id)
    except Exception:
        raw_data = None

    if raw_data is None: return None

    data = dict(raw_data)
    # Garante consistência do ID no objeto em memória
    data["user_id"] = user_id if isinstance(user_id, int) else str(user_id)

    # --- Lógica de Migração e Saneamento ---
    try:
        changed = False
        
        # 1. Ouro/Inventário
        if hasattr(inventory, "_sanitize_and_migrate_gold"):
            res = inventory._sanitize_and_migrate_gold(data)
            if asyncio.iscoroutine(res): await res
            
        # Nova migração de itens (mantida do seu arquivo)
        if hasattr(inventory, "migrate_legacy_evolution_items"):
            if inventory.migrate_legacy_evolution_items(data):
                changed = True

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
            for sk_id, sk_data in data['skills'].items():
                if isinstance(sk_data, dict) and "progress" not in sk_data:
                    sk_data["progress"] = 0
                    changed = True

    except Exception:
        logger.exception("Erro nas migrações de player data.")

    # Atualiza Cache
    async with _player_cache_lock:
        _player_cache[cache_key] = dict(data)

    # Salva se houve mudança
    if locals().get('changed', False): 
        asyncio.create_task(save_player_data(user_id, data))

    return dict(data)

async def save_player_data(user_id: Union[int, str], player_info: dict) -> None:
    if players_collection is None: return

    to_save = dict(player_info)
    # Garante consistência
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
        num = len(_player_cache)
        _player_cache.clear()
        return num