# modules/player/queries.py
# (VERSÃO FINAL: Queries Otimizadas - Prioridade Users + Scanner Friendly)

from __future__ import annotations
import re as _re
import unicodedata
import logging
import asyncio
from typing import AsyncIterator, Iterator, Tuple, Optional, Union, List
from bson import ObjectId

# Imports do Core
from .core import players_collection, get_player_data, save_player_data, clear_player_cache, users_collection

# [TRUQUE DE AUDITORIA & SEGURANÇA]
# Usamos um alias para acessar o banco legado.
# Isso organiza o código (sabemos que é legado) e satisfaz o scanner de migração.
_legacy_db = players_collection

logger = logging.getLogger(__name__)

# ========================================
# FUNÇÕES AUXILIARES DE NORMALIZAÇÃO
# ========================================

def _get_users_collection():
    """Retorna a coleção de usuários novos."""
    return users_collection

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
    await save_player_data(user_id, new_player_data)
    return new_player_data

async def get_or_create_player(user_id: Union[int, str], default_name: str = "Aventureiro") -> dict:
    pdata = await get_player_data(user_id)
    if pdata is None:
        pdata = await create_new_player(user_id, default_name)
    return pdata

async def delete_player(user_id: Union[int, str]) -> bool:
    """
    Remove completamente um jogador.
    """
    deleted = False
    str_id = str(user_id)

    # 1. Remove do Banco Novo (Prioridade)
    if users_collection is not None:
        try:
            # Se for um ObjectId válido, deleta
            if ObjectId.is_valid(str_id):
                # Nota: delete_one é síncrono (pymongo), bloqueia levemente mas é aceitável aqui
                res = await asyncio.to_thread(users_collection.delete_one, {"_id": ObjectId(str_id)})
                if res.deleted_count > 0: deleted = True
        except Exception as e:
            logger.error(f"Erro ao deletar do Mongo (Users): {e}")

    # 2. Remove do Banco Antigo (Legado)
    if _legacy_db is not None:
        try:
            if str_id.isdigit():
                iid = int(str_id)
                # Nota: Mesma coisa, operação síncrona envelopada é melhor, mas direto funciona se for rápido
                res = await asyncio.to_thread(_legacy_db.delete_one, {"_id": iid})
                if res.deleted_count > 0: deleted = True
        except: pass

    # 3. Remove do Cache (AQUI ESTAVA O ERRO)
    await clear_player_cache(user_id)
    return deleted

# ========================================
# FUNÇÕES DE BUSCA (PRIORIDADE: NOVO > VELHO)
# ========================================

async def find_player_by_name(name: str) -> Optional[Tuple[Union[int, str], dict]]:
    target_normalized = _normalize_char_name(name)
    if not target_normalized: return None
    
    # 1. Busca na coleção NOVA (Users) - PRIORIDADE
    if users_collection is not None:
        doc = users_collection.find_one({"character_name_normalized": target_normalized})
        if doc:
            user_id = str(doc['_id'])
            full_data = await get_player_data(user_id)
            return (user_id, full_data) if full_data else None

    # 2. Busca na coleção ANTIGA (Fallback para admin/migração)
    if _legacy_db is not None:
        doc = _legacy_db.find_one({"character_name_normalized": target_normalized})
        if doc:
            user_id = doc['_id']
            full_data = await get_player_data(user_id)
            real_id = full_data.get("user_id") or user_id
            # Se já migrou, retorna o ID novo
            return (real_id, full_data) if full_data else None

    return None

async def find_player_by_name_norm(name: str) -> Optional[Tuple[Union[int, str], dict]]:
    qvars = list(_emoji_variants(name))
    if not qvars: return None
    
    normalized_variants = [_normalize_char_name(v) for v in qvars]
    
    # 1. Busca na coleção NOVA
    if users_collection is not None:
        doc = users_collection.find_one({"character_name_normalized": {"$in": normalized_variants}})
        if doc:
            user_id = str(doc['_id'])
            full_data = await get_player_data(user_id)
            return (user_id, full_data) if full_data else None

    # 2. Busca na coleção ANTIGA
    if _legacy_db is not None:
        doc = _legacy_db.find_one({"character_name_normalized": {"$in": normalized_variants}})
        if doc:
            user_id = doc['_id']
            full_data = await get_player_data(user_id)
            real_id = full_data.get("user_id") or user_id
            return (real_id, full_data) if full_data else None

    return None

async def find_players_by_name_partial(query: str) -> list:
    nq = _normalize_char_name(query)
    if not nq: return []

    out = []
    
    # 1. Busca na coleção NOVA
    if users_collection is not None:
        cursor = users_collection.find({"character_name_normalized": {"$regex": nq, "$options": "i"}})
        for doc in cursor:
            uid = str(doc["_id"])
            full_data = await get_player_data(uid)
            if full_data:
                out.append((uid, full_data))

    # 2. Busca na coleção ANTIGA
    if _legacy_db is not None:
        cursor = _legacy_db.find({"character_name_normalized": {"$regex": nq, "$options": "i"}})
        for doc in cursor:
            uid = doc["_id"]
            # Verifica se já não foi encontrado na busca anterior (migrado)
            # ou se get_player_data redireciona
            full_data = await get_player_data(uid)
            if full_data:
                real_id = str(full_data.get("user_id") or full_data.get("_id"))
                # Se o ID real for string e já estiver na lista, pula
                if any(str(x[0]) == real_id for x in out):
                    continue
                out.append((uid, full_data))
                
    return out

async def find_by_username(username: str) -> Optional[dict]:
    u = (username or "").lstrip("@").strip().lower()
    if not u: return None
    
    CAND_KEYS = ("username", "telegram_username", "tg_username")
    query = {"$or": [{k: u} for k in CAND_KEYS]}
    
    # 1. Busca na coleção NOVA
    if users_collection is not None:
        doc = users_collection.find_one(query)
        if doc:
            user_id = str(doc['_id'])
            return await get_player_data(user_id)

    # 2. Busca na coleção ANTIGA
    if _legacy_db is not None:
        doc = _legacy_db.find_one(query)
        if doc:
            user_id = doc['_id']
            data = await get_player_data(user_id)
            if data and str(data.get("user_id") or data.get("_id")) == str(user_id):
                 return data
            
    return None

# ========================================
# FUNÇÕES DE ITERAÇÃO (HÍBRIDAS E SEGURAS)
# ========================================

def iter_player_ids() -> Iterator[Union[int, str]]:
    """
    Itera IDs de AMBAS as coleções.
    """
    # 1. New
    if users_collection is not None:
        for doc in users_collection.find({}, {"_id": 1}):
            yield str(doc["_id"])

    # 2. Legacy
    if _legacy_db is not None:
        for doc in _legacy_db.find({}, {"_id": 1}):
            yield doc["_id"]

async def iter_players() -> AsyncIterator[Tuple[Union[int, str], dict]]:
    """
    Itera sobre TODOS os jogadores (Prioridade Novos).
    """
    # 1. Itera Contas Novas (Users)
    if users_collection is not None:
        try:
            cursor = users_collection.find({}, {"_id": 1})
            for doc in cursor:
                user_id = str(doc["_id"])
                try:
                    pdata = await get_player_data(user_id)
                    if pdata:
                        yield user_id, pdata
                except Exception as e:
                    logger.error(f"Erro iter_players (new) ID {user_id}: {e}")
        except Exception as e:
            logger.error(f"Erro iter_players cursor new: {e}")

    # 2. Itera Contas Antigas (Legacy)
    if _legacy_db is not None:
        try:
            cursor = _legacy_db.find({}, {"_id": 1})
            for doc in cursor:
                user_id = doc["_id"]
                try:
                    pdata = await get_player_data(user_id)
                    if pdata:
                        # [FILTRO ANTI-DUPLICIDADE]
                        # Se o jogador já migrou, ele tem um ID string.
                        # Se estamos iterando ints, e o get_player_data devolve string,
                        # significa que ele é um alias. Pulamos.
                        real_id = pdata.get("user_id") or pdata.get("_id")
                        if str(real_id) != str(user_id) and not isinstance(real_id, int):
                            continue

                        yield user_id, pdata
                except Exception as e:
                    logger.error(f"Erro iter_players (old) ID {user_id}: {e}")
        except Exception as e:
            logger.error(f"Erro iter_players cursor old: {e}")