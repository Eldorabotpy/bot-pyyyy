# modules/player/queries.py
# (VERSÃO BLINDADA: Busca Híbrida + Iterador Inteligente Anti-Duplicidade)

from __future__ import annotations
import re as _re
import unicodedata
import logging
from typing import AsyncIterator, Iterator, Tuple, Optional, Union, List
from .core import players_collection, get_player_data, save_player_data, clear_player_cache
from modules.player.core import players_collection, _player_cache
from bson import ObjectId

# ========================================
# FUNÇÕES AUXILIARES DE NORMALIZAÇÃO
# ========================================

logger = logging.getLogger(__name__)

def _get_users_collection():
    """Helper para pegar a coleção de usuários novos."""
    if players_collection is not None:
        return players_collection.database["users"]
    return None

def _normalize_char_name(_s: str) -> str:
    if not isinstance(_s, str):
        return ""
    INVISIBLE_CHARS = r"[\u200B-\u200D\uFEFF]"
    s = _re.sub(INVISIBLE_CHARS, "", _s)
    s = _re.sub(r"[\r\n\t]+", " ", s)
    s = _re.sub(r"\s+", " ", s).strip().lower()
    return s

_VS_SET = {0xFE0E, 0xFE0F}
def _is_skin_tone(cp: int) -> bool:
    return 0x1F3FB <= cp <= 0x1F3FF

def _strip_vs_and_tones(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKC", s)
    out = []
    for ch in s:
        cp = ord(ch)
        if cp in _VS_SET or _is_skin_tone(cp):
            continue
        out.append(ch)
    return "".join(out).strip()

def _emoji_variants(s: str):
    base = _strip_vs_and_tones(s)
    yield base
    if "\u200D" in base:
        yield base.replace("\u200D", "")

# ========================================
# CICLO DE VIDA DO JOGADOR
# ========================================

async def create_new_player(user_id: Union[int, str], character_name: str) -> dict:
    from .actions import utcnow 

    now_iso = utcnow().isoformat()

    new_player_data = {
        "character_name": character_name,
        "class": None,
        "level": 1,
        "xp": 0,
        "max_hp": 50,
        "current_hp": 50,
        "attack": 5,
        "defense": 3,
        "initiative": 5,
        "luck": 5,
        "stat_points": 0,
        "energy": 20,
        "max_energy": 20,
        "energy_last_ts": now_iso,
        "gold": 0,
        "gems": 0, 
        "premium_tier": None,
        "premium_expires_at": None,
        "party_id": None,
        "profession": {},
        "inventory": {},
        "equipment": {
            "arma": None, "elmo": None, "armadura": None, "calca": None,
            "luvas": None, "botas": None, "anel": None, "colar": None, "brinco": None
        },
        "current_location": "reino_eldora",
        "last_travel_time": None,
        "player_state": {'action': 'idle'},
        "last_chat_id": None,
        "class_choice_offered": False,
        "base_stats": {"max_hp": 50, "attack": 5, "defense": 3, "initiative": 5, "luck": 5},
        "created_at": now_iso,
        "last_seen": now_iso,
    }
    # O core.save_player_data já decide se salva em 'players' ou 'users' baseado no tipo do ID
    await save_player_data(user_id, new_player_data)
    return new_player_data

async def get_or_create_player(user_id: Union[int, str], default_name: str = "Aventureiro") -> dict:
    pdata = await get_player_data(user_id)
    if pdata is None:
        pdata = await create_new_player(user_id, default_name)
    return pdata

def delete_player(user_id: Union[int, str]) -> bool:
    """
    Remove completamente um jogador do banco de dados e do cache.
    Suporta ID numérico (antigo) e string/ObjectId (novo).
    """
    deleted = False
    str_id = str(user_id)

    # 1. Tenta remover do MongoDB (Coleção Antiga)
    if players_collection is not None:
        try:
            if str_id.isdigit():
                iid = int(str_id)
                res = players_collection.delete_one({"_id": iid})
                if res.deleted_count > 0: deleted = True
        except: pass

    # 2. Tenta remover do MongoDB (Coleção Nova)
    users_col = _get_users_collection()
    if users_col is not None:
        try:
            if ObjectId.is_valid(str_id):
                res = users_col.delete_one({"_id": ObjectId(str_id)})
                if res.deleted_count > 0: deleted = True
        except Exception as e:
            print(f"Erro ao deletar do Mongo (Users): {e}")

    # 3. Remove do Cache (Memória)
    keys_to_remove = [str_id]
    if str_id.isdigit(): keys_to_remove.append(int(str_id))

    for k in keys_to_remove:
        if k in _player_cache:
            del _player_cache[k]
            deleted = True 

    return deleted

# ========================================
# FUNÇÕES DE BUSCA (QUERIES HÍBRIDAS)
# ========================================

async def find_player_by_name(name: str) -> Optional[Tuple[Union[int, str], dict]]:
    target_normalized = _normalize_char_name(name)
    if not target_normalized or players_collection is None:
        return None
    
    # 1. Busca na coleção ANTIGA (Players)
    doc = players_collection.find_one({"character_name_normalized": target_normalized})
    if doc:
        user_id = doc['_id']
        full_data = await get_player_data(user_id)
        # Se full_data retornar um ID diferente (redirecionado), usamos o novo
        real_id = full_data.get("user_id") or user_id
        return (real_id, full_data) if full_data else None

    # 2. Busca na coleção NOVA (Users)
    users_col = _get_users_collection()
    if users_col:
        doc = users_col.find_one({"character_name_normalized": target_normalized})
        if doc:
            user_id = str(doc['_id'])
            full_data = await get_player_data(user_id)
            return (user_id, full_data) if full_data else None

    return None

async def find_player_by_name_norm(name: str) -> Optional[Tuple[Union[int, str], dict]]:
    if players_collection is None: return None

    qvars = list(_emoji_variants(name))
    if not qvars: return None
    
    normalized_variants = [_normalize_char_name(v) for v in qvars]
    
    # 1. Busca na coleção ANTIGA
    doc = players_collection.find_one({"character_name_normalized": {"$in": normalized_variants}})
    if doc:
        user_id = doc['_id']
        full_data = await get_player_data(user_id)
        real_id = full_data.get("user_id") or user_id
        return (real_id, full_data) if full_data else None

    # 2. Busca na coleção NOVA
    users_col = _get_users_collection()
    if users_col:
        doc = users_col.find_one({"character_name_normalized": {"$in": normalized_variants}})
        if doc:
            user_id = str(doc['_id'])
            full_data = await get_player_data(user_id)
            return (user_id, full_data) if full_data else None

    return None

async def find_players_by_name_partial(query: str) -> list:
    nq = _normalize_char_name(query)
    if not nq or not players_collection: return []

    out = []
    
    # 1. Busca na coleção ANTIGA
    cursor = players_collection.find({"character_name_normalized": {"$regex": nq, "$options": "i"}})
    for doc in cursor:
        uid = doc["_id"]
        full_data = await get_player_data(uid)
        if full_data:
            # Verifica se já migrou (não adiciona se for o caso, pois vai aparecer na busca da nova)
            if str(full_data.get("user_id")) != str(uid): continue 
            out.append((uid, full_data))
            
    # 2. Busca na coleção NOVA
    users_col = _get_users_collection()
    if users_col:
        cursor = users_col.find({"character_name_normalized": {"$regex": nq, "$options": "i"}})
        for doc in cursor:
            uid = str(doc["_id"])
            full_data = await get_player_data(uid)
            if full_data:
                out.append((uid, full_data))
                
    return out

async def find_by_username(username: str) -> Optional[dict]:
    u = (username or "").lstrip("@").strip().lower()
    if not u or not players_collection: return None
    
    CAND_KEYS = ("username", "telegram_username", "tg_username")
    query = {"$or": [{k: u} for k in CAND_KEYS]}
    
    # 1. Busca na coleção ANTIGA
    doc = players_collection.find_one(query)
    if doc:
        user_id = doc['_id']
        data = await get_player_data(user_id)
        if data and str(data.get("user_id")) == str(user_id):
             return data

    # 2. Busca na coleção NOVA
    users_col = _get_users_collection()
    if users_col:
        doc = users_col.find_one(query)
        if doc:
            user_id = str(doc['_id'])
            return await get_player_data(user_id)
            
    return None

# ========================================
# FUNÇÕES DE ITERAÇÃO (HÍBRIDAS E SEGURAS)
# ========================================

def iter_player_ids() -> Iterator[Union[int, str]]:
    """
    Itera IDs de AMBAS as coleções (Legacy e New).
    Útil para correções em massa (como fix_tomos).
    """
    # 1. Legacy
    if players_collection:
        for doc in players_collection.find({}, {"_id": 1}):
            yield doc["_id"]

    # 2. New
    users_col = _get_users_collection()
    if users_col:
        for doc in users_col.find({}, {"_id": 1}):
            yield str(doc["_id"])

async def iter_players() -> AsyncIterator[Tuple[Union[int, str], dict]]:
    """
    Itera sobre TODOS os jogadores (Antigos e Novos).
    ⚡ INTELIGENTE: Evita processar a mesma pessoa duas vezes se ela já migrou.
    """
    if players_collection is None:
        logger.warning("[ITER_DEBUG] players_collection é None.")
        return
    
    # 1. Itera Contas Antigas (Players)
    count = 0
    try:
        cursor = players_collection.find({}, {"_id": 1})
        for doc in cursor:
            user_id = doc["_id"]
            try:
                pdata = await get_player_data(user_id)
                if pdata:
                    # [FILTRO ANTI-DUPLICIDADE]
                    # Se get_player_data redirecionou para um ID novo (String/ObjectId),
                    # significa que este usuário já migrou.
                    # PULA ele aqui, pois ele será pego no loop 2 (Users).
                    real_id = pdata.get("user_id") or pdata.get("_id")
                    if str(real_id) != str(user_id) and not isinstance(real_id, int):
                        continue

                    yield user_id, pdata
                    count += 1
            except Exception as e:
                logger.error(f"Erro iter_players (old) ID {user_id}: {e}")
    except Exception as e:
        logger.error(f"Erro iter_players cursor old: {e}")

    # 2. Itera Contas Novas (Users)
    users_col = _get_users_collection()
    if users_col:
        try:
            cursor = users_col.find({}, {"_id": 1})
            for doc in cursor:
                user_id = str(doc["_id"]) # ObjectId -> Str
                try:
                    pdata = await get_player_data(user_id)
                    if pdata:
                        yield user_id, pdata
                        count += 1
                except Exception as e:
                    logger.error(f"Erro iter_players (new) ID {user_id}: {e}")
        except Exception as e:
            logger.error(f"Erro iter_players cursor new: {e}")
             
    # logger.debug(f"[ITER_DEBUG] Fim da iteração híbrida. Processados: {count}")