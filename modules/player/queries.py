# Em modules/player/queries.py

from __future__ import annotations
import re as _re
import unicodedata
import logging
from typing import AsyncIterator, Iterator, Tuple, Optional
from .core import players_collection, get_player_data, save_player_data, clear_player_cache

# ========================================
# FUNÇÕES AUXILIARES DE NORMALIZAÇÃO
# ========================================

logger = logging.getLogger(__name__)

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

async def create_new_player(user_id: int, character_name: str) -> dict:
    from .actions import utcnow  # Importação local para evitar ciclos

    now_iso = utcnow().isoformat() # Pega a hora atual uma vez

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
        "energy_last_ts": now_iso, # Usa a nova variável 'now_iso'
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

        # --- 👇 NOVOS CAMPOS ADICIONADOS 👇 ---
        "created_at": now_iso, # Guarda a data de criação
        "last_seen": now_iso,  # Guarda a última interação (agora)
        # --- 👆 FIM DOS NOVOS CAMPOS 👆 ---
    }
    await save_player_data(user_id, new_player_data)
    return new_player_data

async def get_or_create_player(user_id: int, default_name: str = "Aventureiro") -> dict:
    pdata = get_player_data(user_id)
    if pdata is None:
        pdata = await create_new_player(user_id, default_name)
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

async def find_player_by_name(name: str) -> Optional[Tuple[int, dict]]:
    target_normalized = _normalize_char_name(name)
    if not target_normalized or players_collection is None:
        return None
    
    doc = players_collection.find_one({"character_name_normalized": target_normalized})
    if doc:
        user_id = doc['_id']
        full_data = await get_player_data(user_id)
        return (user_id, full_data) if full_data else None
    return None

async def find_player_by_name_norm(name: str) -> Optional[Tuple[int, dict]]:
    if players_collection is None:
        return None

    qvars = list(_emoji_variants(name))
    if not qvars:
        return None
    
    normalized_variants = [_normalize_char_name(v) for v in qvars]
    doc = players_collection.find_one({"character_name_normalized": {"$in": normalized_variants}})
    
    if doc:
        user_id = doc['_id']
        full_data = await get_player_data(user_id)
        return (user_id, full_data) if full_data else None
    return None

async def find_players_by_name_partial(query: str) -> list:
    nq = _normalize_char_name(query)
    if not nq or not players_collection:
        return []

    cursor = players_collection.find({"character_name_normalized": {"$regex": nq, "$options": "i"}})
    out = []
    for doc in cursor:
        uid = doc["_id"]
        full_data = await get_player_data(uid)
        if full_data:
            out.append((uid, full_data))
    return out

async def find_by_username(username: str) -> Optional[dict]:
    u = (username or "").lstrip("@").strip().lower()
    if not u or not players_collection:
        return None
    
    CAND_KEYS = ("username", "telegram_username", "tg_username")
    query = {"$or": [{k: u} for k in CAND_KEYS]}
    doc = players_collection.find_one(query)
    
    if doc:
        user_id = doc['_id']
        return await get_player_data(user_id)
    return None

# ========================================
# FUNÇÕES DE ITERAÇÃO
# ========================================

def iter_player_ids() -> Iterator[int]:
    if players_collection is None:
        return
    for doc in players_collection.find({}, {"_id": 1}):
        yield doc["_id"]

# Em modules/player/queries.py

async def iter_players() -> AsyncIterator[Tuple[int, dict]]:
    if players_collection is None:
        logger.warning("[ITER_DEBUG] players_collection é None, iter_players não pode executar.")
        return
    
    logger.debug("[ITER_DEBUG] Iniciando iteração sobre player IDs...")
    count = 0
    # iter_player_ids é síncrono
    for user_id in iter_player_ids():
        try:
             count += 1
             logger.debug(f"[ITER_DEBUG] Processando ID #{count}: {user_id}")
             player_data = await get_player_data(user_id) # Chama a função com logs
             
             # Loga o que get_player_data retornou ANTES do if
             logger.debug(f"[ITER_DEBUG] get_player_data retornou para {user_id}: Tipo={type(player_data)}")
             
             if player_data is not None and isinstance(player_data, dict): # Verifica explicitamente se é dict
                 logger.debug(f"[ITER_DEBUG] Yielding dados VÁLIDOS para {user_id}")
                 yield user_id, player_data
             else:
                  # Loga se os dados foram filtrados (None ou tipo errado)
                  logger.warning(f"[ITER_DEBUG] Dados inválidos ou None recebidos para {user_id}. FILTRANDO.")
                  
        except Exception as e:
             # Loga erros durante a iteração de um ID específico
             logger.error(f"[ITER_DEBUG] Erro ao processar user_id {user_id} dentro de iter_players: {e}", exc_info=True)
             # Continua para o próximo ID
             continue 
             
    logger.debug(f"[ITER_DEBUG] Fim da iteração. Total de IDs processados: {count}")