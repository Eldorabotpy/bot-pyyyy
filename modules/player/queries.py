# Em modules/player/queries.py
from __future__ import annotations
import re as _re
import unicodedata
from typing import Iterator, Tuple, Optional

# Importa as funções essenciais do nosso novo módulo 'core'
from .core import players_collection, get_player_data, save_player_data, clear_player_cache

# ========================================
# FUNÇÕES AUXILIARES DE NORMALIZAÇÃO
# ========================================

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

def create_new_player(user_id: int, character_name: str) -> dict:
    from .actions import utcnow  # Importação local para evitar ciclos
    
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
        "energy_last_ts": utcnow().isoformat(),
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
    }
    save_player_data(user_id, new_player_data)
    return new_player_data

def get_or_create_player(user_id: int, default_name: str = "Aventureiro") -> dict:
    pdata = get_player_data(user_id)
    if pdata is None:
        pdata = create_new_player(user_id, default_name)
    return pdata

def delete_player(user_id: int) -> bool:
    if players_collection is None:
        return False
    result = players_collection.delete_one({"_id": user_id})
    clear_player_cache(user_id)
    return result.deleted_count > 0

# ========================================
# FUNÇÕES DE BUSCA (QUERIES)
# ========================================

def find_player_by_name(name: str) -> Optional[Tuple[int, dict]]:
    target_normalized = _normalize_char_name(name)
    if not target_normalized or players_collection is None:
        return None
    
    doc = players_collection.find_one({"character_name_normalized": target_normalized})
    if doc:
        user_id = doc['_id']
        full_data = get_player_data(user_id)
        return (user_id, full_data) if full_data else None
    return None

def find_player_by_name_norm(name: str) -> Optional[Tuple[int, dict]]:
    if players_collection is None:
        return None

    qvars = list(_emoji_variants(name))
    if not qvars:
        return None
    
    normalized_variants = [_normalize_char_name(v) for v in qvars]
    doc = players_collection.find_one({"character_name_normalized": {"$in": normalized_variants}})
    
    if doc:
        user_id = doc['_id']
        full_data = get_player_data(user_id)
        return (user_id, full_data) if full_data else None
    return None

def find_players_by_name_partial(query: str) -> list:
    nq = _normalize_char_name(query)
    if not nq or not players_collection:
        return []

    cursor = players_collection.find({"character_name_normalized": {"$regex": nq, "$options": "i"}})
    out = []
    for doc in cursor:
        uid = doc["_id"]
        full_data = get_player_data(uid)
        if full_data:
            out.append((uid, full_data))
    return out

def find_by_username(username: str) -> Optional[dict]:
    u = (username or "").lstrip("@").strip().lower()
    if not u or not players_collection:
        return None
    
    CAND_KEYS = ("username", "telegram_username", "tg_username")
    query = {"$or": [{k: u} for k in CAND_KEYS]}
    doc = players_collection.find_one(query)
    
    if doc:
        user_id = doc['_id']
        return get_player_data(user_id)
    return None

# ========================================
# FUNÇÕES DE ITERAÇÃO
# ========================================

def iter_player_ids() -> Iterator[int]:
    if players_collection is None:
        return
    for doc in players_collection.find({}, {"_id": 1}):
        yield doc["_id"]

def iter_players() -> Iterator[Tuple[int, dict]]:
    if players_collection is None:
        return
    for user_id in iter_player_ids():
        player_data = get_player_data(user_id)
        if player_data:
            yield user_id, player_data