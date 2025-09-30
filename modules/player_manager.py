# modules/player_manager.py

import os
import uuid
import pymongo
from pymongo.errors import ConnectionFailure
import json
import re as _re
import unicodedata
import time
from typing import Optional, Tuple, Iterator
from datetime import datetime, timedelta, timezone
from modules import clan_manager
import logging


# ========================================
# CONFIGURAÇÃO E CONEXÃO COM MONGODB
# ========================================

MONGO_CONNECTION_STRING = os.environ.get("MONGO_CONNECTION_STRING")
players_collection = None # A nossa "coleção" de jogadores

if not MONGO_CONNECTION_STRING:
    logging.error("CRÍTICO: A variável de ambiente MONGO_CONNECTION_STRING não foi definida!")
else:
    try:
        client = pymongo.MongoClient(MONGO_CONNECTION_STRING)
        client.admin.command('ping')
        logging.info("✅ Conexão com o MongoDB Atlas estabelecida com sucesso!")
        
        db = client.get_database("eldora_db")
        players_collection = db.get_collection("players")

        # NOVO: Criar índices para otimizar as buscas por nome e username.
        # Isso torna as buscas extremamente rápidas!
        logging.info("Garantindo a existência de índices no MongoDB...")
        players_collection.create_index("character_name_normalized")
        # Você pode adicionar mais índices se buscar por outros campos frequentemente
        # players_collection.create_index("username") 
        logging.info("✅ Índices do MongoDB verificados/criados.")

    except ConnectionFailure as e:
        logging.error(f"CRÍTICO: Falha ao conectar ao MongoDB Atlas: {e}")
    except Exception as e:
        logging.error(f"CRÍTICO: Ocorreu um erro inesperado na configuração do MongoDB: {e}")


# ========================================
# DADOS E CONSTANTES DO JOGO
# ========================================
try:
    from modules.game_data import PREMIUM_TIERS, ITEMS_DATA 
except Exception:
    PREMIUM_TIERS = {"free": {"perks": {}}}
    try:
        from modules.game_data import ITEMS_DATA
    except Exception:
        ITEMS_DATA = {}


GOLD_KEY = "ouro"
GEMS_KEY_PT = "gemas"   
GEMS_KEY_EN = "gems"
GEM_KEYS = {GEMS_KEY_PT, GEMS_KEY_EN}
DEFAULT_PVP_ENTRIES = 10 


CLASS_PROGRESSIONS = {
    "guerreiro": {
        "BASE":   {"max_hp": 52, "attack": 5, "defense": 4, "initiative": 4, "luck": 3},
        "PER_LVL": {"max_hp":  8, "attack": 1, "defense": 2, "initiative": 0, "luck": 0},
        "FREE_POINTS_PER_LVL": 1,
    },
    "berserker": {
        "BASE":   {"max_hp": 55, "attack": 6, "defense": 3, "initiative": 5, "luck": 3},
        "PER_LVL": {"max_hp":  9, "attack": 2, "defense": 0, "initiative": 1, "luck": 0},
        "FREE_POINTS_PER_LVL": 1,
    },
    "cacador": {
        "BASE":   {"max_hp": 48, "attack": 6, "defense": 3, "initiative": 6, "luck": 4},
        "PER_LVL": {"max_hp":  6, "attack": 2, "defense": 0, "initiative": 2, "luck": 1},
        "FREE_POINTS_PER_LVL": 1,
    },
    "monge": {
        "BASE":   {"max_hp": 50, "attack": 5, "defense": 4, "initiative": 6, "luck": 3},
        "PER_LVL": {"max_hp":  7, "attack": 1, "defense": 2, "initiative": 2, "luck": 0},
        "FREE_POINTS_PER_LVL": 1,
    },
    "mago": {
        "BASE":   {"max_hp": 45, "attack": 7, "defense": 2, "initiative": 5, "luck": 4},
        "PER_LVL": {"max_hp":  5, "attack": 3, "defense": 0, "initiative": 1, "luck": 1},
        "FREE_POINTS_PER_LVL": 1,
    },
    "bardo": {
        "BASE":   {"max_hp": 47, "attack": 5, "defense": 3, "initiative": 5, "luck": 6},
        "PER_LVL": {"max_hp":  6, "attack": 1, "defense": 1, "initiative": 1, "luck": 2},
        "FREE_POINTS_PER_LVL": 1,
    },
    "assassino": {
        "BASE":   {"max_hp": 47, "attack": 6, "defense": 2, "initiative": 7, "luck": 5},
        "PER_LVL": {"max_hp":  5, "attack": 2, "defense": 0, "initiative": 3, "luck": 1},
        "FREE_POINTS_PER_LVL": 1,
    },
    "samurai": {
        "BASE":   {"max_hp": 50, "attack": 6, "defense": 4, "initiative": 5, "luck": 4},
        "PER_LVL": {"max_hp":  7, "attack": 2, "defense": 1, "initiative": 1, "luck": 0},
        "FREE_POINTS_PER_LVL": 1,
    },
    "_default": {
        "BASE":   {"max_hp": 50, "attack": 5, "defense": 3, "initiative": 5, "luck": 5},
        "PER_LVL": {"max_hp":  7, "attack": 1, "defense": 1, "initiative": 1, "luck": 0},
        "FREE_POINTS_PER_LVL": 1,
    },
}

CLASS_POINT_GAINS = {
    "guerreiro": {"max_hp": 4, "attack": 1, "defense": 2, "initiative": 1, "luck": 1},
    "berserker": {"max_hp": 3, "attack": 2, "defense": 1, "initiative": 1, "luck": 1},
    "cacador":   {"max_hp": 3, "attack": 2, "defense": 1, "initiative": 2, "luck": 1},
    "monge":     {"max_hp": 3, "attack": 1, "defense": 2, "initiative": 2, "luck": 1},
    "mago":      {"max_hp": 2, "attack": 3, "defense": 1, "initiative": 1, "luck": 2},
    "bardo":     {"max_hp": 3, "attack": 1, "defense": 1, "initiative": 1, "luck": 2},
    "assassino": {"max_hp": 2, "attack": 2, "defense": 1, "initiative": 3, "luck": 2},
    "samurai":   {"max_hp": 3, "attack": 2, "defense": 2, "initiative": 1, "luck": 1},
    "_default":  {"max_hp": 3, "attack": 1, "defense": 1, "initiative": 1, "luck": 1},
}

_BASELINE_KEYS = ("max_hp", "attack", "defense", "initiative", "luck")


# ========================================
# CACHE DE JOGADORES (Ainda útil para evitar múltiplas buscas no DB)
# ========================================
_player_cache = {}


# ========================================
# FUNÇÕES AUXILIARES
# ========================================
def _parse_iso(dt_str: str) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None

def utcnow():
    return datetime.now(timezone.utc)

def _ival(x, default=0):
    try:
        return int(x)
    except Exception:
        return int(default)

# ========================================
# LEITURA E ESCRITA (MODIFICADO PARA MONGODB)
# ========================================

def _load_player_from_db(user_id: int) -> Optional[dict]:
    """NOVO: Função base que lê os dados do jogador do MongoDB."""
    if players_collection is None:
        logging.error("Tentativa de carregar jogador, mas a conexão com o MongoDB não está disponível.")
        return None
    
    player_doc = players_collection.find_one({"_id": user_id})
    if player_doc:
        player_doc.pop('_id', None) # Remove o campo _id para compatibilidade interna
    return player_doc

def save_player_data(user_id: int, player_info: dict) -> None:
    """ALTERADO: Salva os dados do jogador no MongoDB."""
    if players_collection is None:
        logging.error(f"Tentativa de salvar jogador {user_id}, mas a conexão com o MongoDB não está disponível.")
        return

    # Remove o _id do dicionário se ele existir, para não causar conflitos
    player_info.pop('_id', None)
    
    # Atualiza o cache com uma cópia limpa
    _player_cache[user_id] = player_info.copy()

    # Prepara os dados para salvar (limpeza, etc.)
    _sanitize_and_migrate_gold(player_info)
    player_info["gold"] = max(0, _ival(player_info.get("gold")))
    player_info["energy"] = max(0, _ival(player_info.get("energy")))
    cap = get_player_max_energy(player_info)
    if player_info["energy"] > cap: player_info["energy"] = cap
    if not player_info.get('energy_last_ts'):
        anchor = _parse_iso(player_info.get('last_energy_ts')) or utcnow()
        player_info['energy_last_ts'] = anchor.isoformat()
    if player_info.get('last_energy_ts'): player_info.pop('last_energy_ts', None)
    
    # Adiciona campo normalizado para busca rápida com índice
    player_info["character_name_normalized"] = _normalize_char_name(player_info.get("character_name", ""))
    
    # Salva no MongoDB.
    # replace_one: Substitui o documento inteiro.
    # {"_id": user_id}: O filtro para encontrar o jogador.
    # player_info: Os novos dados.
    # upsert=True: Se o jogador não existir, ele será criado.
    players_collection.replace_one({"_id": user_id}, player_info, upsert=True)

def get_player_data(user_id) -> Optional[dict]:
    """
    Carrega os dados do jogador, usando o cache para a leitura base,
    mas sempre aplicando as sincronizações importantes (ex: energia).
    """
    if user_id in _player_cache:
        raw_data = _player_cache[user_id].copy()
    else:
        raw_data = _load_player_from_db(user_id)
        if raw_data:
            _player_cache[user_id] = raw_data.copy()
            logging.info(f"[CACHE] Jogador {user_id} carregado do DB para o cache.")

    if not raw_data:
        return None

    data = raw_data 
    data["user_id"] = user_id

    # Funções de sincronização e migração
    if "inventory" not in data or not isinstance(data.get("inventory"), dict):
        data["inventory"] = {}
        
    _sanitize_and_migrate_gold(data)
    data["gold"] = max(0, _ival(data.get("gold")))
    
    changed_by_energy = _apply_energy_autoregen_inplace(data)
    mig = _migrate_point_pool_to_stat_points_inplace(data)
    base_changed = _ensure_base_stats_block_inplace(data)
    cls_sync = _apply_class_progression_sync_inplace(data)
    synced = _sync_stat_points_to_level_cap_inplace(data)

    if changed_by_energy or mig or base_changed or cls_sync or synced:
        save_player_data(user_id, data)

    return data

def get_player_data_light(user_id: int) -> Optional[dict]:
    """Versão leve que busca dados, agora otimizada com cache e MongoDB."""
    if user_id in _player_cache:
        data = _player_cache[user_id].copy()
    else:
        data = _load_player_from_db(user_id)
        if data:
            _player_cache[user_id] = data.copy()
            logging.info(f"[CACHE] Jogador {user_id} carregado do DB para o cache (leitura leve).")
    
    if not data:
        return None
    
    if "inventory" not in data or not isinstance(data.get("inventory"), dict):
        data["inventory"] = {}
    try:
        data["gold"] = max(0, int(data.get("gold", 0)))
    except Exception:
        data["gold"] = 0
    try:
        data["energy"] = max(0, int(data.get("energy", 0)))
    except Exception:
        data["energy"] = 0
    return data

# ========================================
# FUNÇÕES DE ITERAÇÃO E BUSCA (AGORA COM MONGODB)
# ========================================

def iter_player_ids() -> Iterator[int]:
    """ALTERADO: Itera sobre os IDs dos jogadores diretamente do MongoDB."""
    if players_collection is None:
        return
    # find({}, {"_id": 1}) busca todos os docs, mas retorna apenas o campo _id. Eficiente!
    for doc in players_collection.find({}, {"_id": 1}):
        yield doc["_id"]

def iter_players_paged(batch_size: int = 200, light: bool = True) -> Iterator[Tuple[int, dict]]:
    if players_collection is None:
        return

    loader = get_player_data_light if light else get_player_data
    for doc in players_collection.find({}, {"_id": 1}):
        uid = doc["_id"]
        pdata = loader(uid)
        if pdata:
            yield uid, pdata

def iter_players() -> Iterator[Tuple[int, dict]]:
    """ALTERADO: Itera sobre todos os dados dos jogadores do MongoDB."""
    if players_collection is None:
        return
    for doc in players_collection.find():
        user_id = doc.pop("_id")
        full_data = get_player_data(user_id) # Usa get_player_data para aplicar lógicas
        if full_data:
            yield user_id, full_data

def _normalize_char_name(_s: str) -> str:
    if not isinstance(_s, str):
        return ""
    INVISIBLE_CHARS = r"[\u200B-\u200D\uFEFF]"
    s = _re.sub(INVISIBLE_CHARS, "", _s)
    s = _re.sub(r"[\r\n\t]+", " ", s)
    s = _re.sub(r"\s+", " ", s).strip().lower()
    return s
def delete_player(user_id: int) -> bool:
    """
    NOVO: Apaga um jogador permanentemente do banco de dados e do cache.
    """
    if players_collection is None:
        logging.error(f"Tentativa de apagar jogador {user_id}, mas a conexão com o MongoDB não está disponível.")
        return False

    # Apaga do MongoDB
    result = players_collection.delete_one({"_id": user_id})

    # Apaga do cache em memória, se existir
    if user_id in _player_cache:
        del _player_cache[user_id]
        logging.info(f"Jogador {user_id} removido do cache.")

    # Retorna True se pelo menos um documento foi apagado do banco
    return result.deleted_count > 0

def find_player_by_name(name: str):
    # ...
    target_normalized = _normalize_char_name(name)
    if not target_normalized or players_collection is None: # <--- Correção aqui
        return None
    
    doc = players_collection.find_one({"character_name_normalized": target_normalized})
    if not doc:
        return None
        
    user_id = doc.pop('_id')
    return user_id, doc

def find_players_by_name_partial(query: str):
    def _normalize(s: str) -> str:
        import unicodedata as _u, re as _r
        s = (s or "")
        s = _u.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
        s = _r.sub(r"\s+", " ", s).strip().lower()
        return s

    nq = _normalize(query)
    if not nq or not players_collection:
        return []

    # A busca com regex é poderosa! "$options": "i" significa case-insensitive
    cursor = players_collection.find({"character_name_normalized": {"$regex": nq, "$options": "i"}})
    
    out = []
    for doc in cursor:
        uid = doc.pop("_id")
        out.append((uid, doc))
    return out


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

def find_player_by_name_norm(name: str) -> Optional[Tuple[int, dict]]:
    """
    NOVO: Busca um jogador pelo nome, lidando com variações de emoji,
    usando uma query direta e otimizada no MongoDB.
    """
    if players_collection is None:
        return None

    # Gera as possíveis variações de nome (com/sem caracteres especiais de emoji)
    qvars = list(_emoji_variants(name))
    if not qvars:
        return None
    
    normalized_variants = [_normalize_char_name(v) for v in qvars]
    doc = players_collection.find_one({"character_name_normalized": {"$in": normalized_variants}})
    
    if doc:
        user_id = doc.pop('_id')
        # Retorna os dados completos do jogador para consistência com outras funções
        full_data = get_player_data(user_id)
        return (user_id, full_data) if full_data else None
    
    return None

def find_by_username(username: str) -> Optional[dict]:
    u = (username or "").lstrip("@").strip().lower()
    if not u or not players_collection:
        return None
    CAND_KEYS = ("username", "telegram_username", "tg_username")
    
    # Usamos o operador $or para procurar em vários campos possíveis
    # É importante ter um índice em pelo menos um desses campos para ser rápido
    query = {"$or": [{k: u} for k in CAND_KEYS]}
    doc = players_collection.find_one(query)
    
    if doc:
        doc.pop("_id", None)
    return doc

# =========================
# AUTO-REGEN DE ENERGIA (Sem alterações)
# =========================
def _get_regen_seconds(player_data: dict) -> int:
    try:
        return int(get_player_perk_value(player_data, 'energy_regen_seconds', 300))
    except Exception:
        return 300

def _apply_energy_autoregen_inplace(player_data: dict) -> bool:
    changed = False
    max_e = get_player_max_energy(player_data)
    cur = _ival(player_data.get('energy'), 0)

    last_raw = player_data.get('energy_last_ts') or player_data.get('last_energy_ts')
    last_ts = _parse_iso(last_raw) or utcnow()
    regen_s = _get_regen_seconds(player_data)
    now = utcnow()

    if player_data.get('last_energy_ts'):
        player_data.pop('last_energy_ts', None)
        changed = True

    if cur >= max_e:
        prev_anchor = _parse_iso(player_data.get('energy_last_ts'))
        if (not prev_anchor) or (prev_anchor > now):
            player_data['energy_last_ts'] = now.isoformat()
            changed = True
        return changed

    if regen_s <= 0:
        if cur != max_e:
            player_data['energy'] = max_e
            changed = True
        prev_anchor = _parse_iso(player_data.get('energy_last_ts'))
        if (not prev_anchor) or (prev_anchor != now):
            player_data['energy_last_ts'] = now.isoformat()
            changed = True
        return changed

    elapsed = (now - last_ts).total_seconds()
    if elapsed < regen_s:
        if not player_data.get('energy_last_ts'):
            player_data['energy_last_ts'] = last_ts.isoformat()
            changed = True
        return changed

    gained = int(elapsed // regen_s)
    if gained > 0:
        new_energy = min(max_e, cur + gained)
        if new_energy != cur:
            player_data['energy'] = new_energy
            changed = True

        remainder = int(elapsed % regen_s)
        anchor = now - timedelta(seconds=remainder if new_energy < max_e else 0)
        if new_energy >= max_e:
            anchor = now

        prev_anchor = _parse_iso(player_data.get('energy_last_ts'))
        if (not prev_anchor) or (prev_anchor != anchor):
            player_data['energy_last_ts'] = anchor.isoformat()
            changed = True

    return changed


# =========================
# PLAYER CREATION
# =========================
def create_new_player(user_id, character_name: str) -> dict:
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

# =========================
# PREMIUM
# =========================
def grant_premium_status(user_id: int, tier: Optional[str], days: int) -> None:
    player_data = get_player_data(user_id)
    if not player_data:
        return

    if not tier or str(tier).lower() == "free":
        player_data['premium_tier'] = None
        player_data['premium_expires_at'] = None
        player_data['energy_last_ts'] = utcnow().isoformat()
        save_player_data(user_id, player_data)
        return

    tier = str(tier).lower()
    if tier not in PREMIUM_TIERS:
        player_data['premium_tier'] = None
        player_data['premium_expires_at'] = None
        player_data['energy_last_ts'] = utcnow().isoformat()
        save_player_data(user_id, player_data)
        return

    days = max(0, int(days))
    player_data['premium_tier'] = tier
    player_data['premium_expires_at'] = (
        (utcnow() + timedelta(days=days)).isoformat() if days > 0 else None
    )

    max_e = get_player_max_energy(player_data)
    cur = _ival(player_data.get("energy"))
    if cur < max_e:
        player_data["energy"] = max_e
    player_data['energy_last_ts'] = utcnow().isoformat()

    save_player_data(user_id, player_data)

def is_player_premium(player_data: dict) -> bool:
    tier = (player_data or {}).get("premium_tier")
    if not tier or tier == "free":
        return False
    tier = str(tier).lower()
    if tier not in PREMIUM_TIERS:
        return False

    expiration_str = player_data.get("premium_expires_at")
    if not expiration_str:
        return True

    expiration_date = _parse_iso(expiration_str)
    if not expiration_date:
        return True
    return expiration_date > utcnow()

def get_player_tier_info(player_data: dict) -> Optional[dict]:
    if not is_player_premium(player_data):
        return None
    tier_key = player_data.get('premium_tier')
    return PREMIUM_TIERS.get(tier_key)

def get_premium_perks(player_data: dict) -> dict:
    base = (PREMIUM_TIERS.get("free") or {}).get("perks", {}) or {}
    if not is_player_premium(player_data):
        return dict(base)
    tier_key = player_data.get("premium_tier")
    top = (PREMIUM_TIERS.get(tier_key) or {}).get("perks", {}) or {}
    merged = dict(base)
    merged.update(top)
    return merged

def player_has_perk(player_data: dict, perk_name: str) -> bool:
    perks = get_premium_perks(player_data)
    return perk_name in perks

def get_player_perk_value(player_data: dict, perk_name: str, default_value=1):
    perks = get_premium_perks(player_data)
    return perks.get(perk_name, default_value)

# =========================
# OURO / GEMAS / INVENTÁRIO
# =========================
def get_gold(player_data: dict) -> int:
    return _ival(player_data.get("gold"))

def set_gold(player_data: dict, value: int) -> dict:
    player_data["gold"] = max(0, int(value))
    return player_data

def add_gold(player_data: dict, amount: int) -> dict:
    cur = get_gold(player_data)
    return set_gold(player_data, cur + int(amount))

def spend_gold(player_data: dict, amount: int) -> bool:
    amount = int(amount)
    if amount <= 0:
        return True
    cur = get_gold(player_data)
    if cur < amount:
        return False
    set_gold(player_data, cur - amount)
    return True

def get_gems(player_data: dict) -> int:
    try:
        return int(player_data.get("gems", player_data.get(GEMS_KEY_PT, 0)))
    except Exception:
        return 0

def set_gems(player_data: dict, value: int) -> dict:
    val = max(0, int(value))
    player_data["gems"] = val
    if GEMS_KEY_PT in player_data:
        player_data[GEMS_KEY_PT] = val
    return player_data

def add_gems(player_data: dict, amount: int) -> dict:
    cur = get_gems(player_data)
    return set_gems(player_data, cur + int(amount))

def spend_gems(player_data: dict, amount: int) -> bool:
    amt = int(amount)
    if amt <= 0:
        return True
    cur = get_gems(player_data)
    if cur < amt:
        return False
    set_gems(player_data, cur - amt)
    return True

def _sanitize_and_migrate_gold(player_data: dict) -> None:
    inv = player_data.get("inventory", {}) or {}
    raw_gold = inv.get(GOLD_KEY)
    
    try:
        player_data["gold"] = int(player_data.get("gold", 0))
    except Exception:
        player_data["gold"] = 0
    if isinstance(raw_gold, (int, float)):
        add_gold(player_data, int(raw_gold))
        inv.pop(GOLD_KEY, None)

    for gk in (GEMS_KEY_EN, GEMS_KEY_PT):
        raw_gems = inv.get(gk)
        if isinstance(raw_gems, (int, float)):
            set_gems(player_data, get_gems(player_data) + int(raw_gems))
            inv.pop(gk, None)

    player_data["inventory"] = inv

def add_item_to_inventory(player_data: dict, item_id: str, quantity: int = 1):
    qty = int(quantity)
    if qty == 0:
        return player_data

    if item_id == GOLD_KEY:
        if qty > 0: add_gold(player_data, qty)
        else: spend_gold(player_data, -qty)
        return player_data

    if item_id in GEM_KEYS:
        if qty > 0: add_gems(player_data, qty)
        else: spend_gems(player_data, -qty)
        return player_data

    inventory = player_data.setdefault('inventory', {})
    current = _ival(inventory.get(item_id))
    new_val = current + qty
    if new_val <= 0:
        if item_id in inventory:
            del inventory[item_id]
    else:
        inventory[item_id] = new_val
    return player_data

def add_unique_item(player_data: dict, item_instance: dict) -> str:
    inventory = player_data.setdefault('inventory', {})
    unique_id = str(uuid.uuid4())
    inventory[unique_id] = item_instance
    return unique_id

def remove_item_from_inventory(player_data: dict, item_id: str, quantity: int = 1) -> bool:
    if item_id == GOLD_KEY:
        return spend_gold(player_data, int(quantity))
    if item_id in GEM_KEYS:
        return spend_gems(player_data, int(quantity))
    inventory = player_data.get('inventory', {})
    if item_id not in inventory:
        return False
    if isinstance(inventory[item_id], dict):
        del inventory[item_id]
        return True
    qty = int(quantity)
    have = int(inventory[item_id])
    if have >= qty > 0:
        new_val = have - qty
        if new_val <= 0:
            del inventory[item_id]
        else:
            inventory[item_id] = new_val
        return True
    return False

# =========================
# STATS & EQUIP
# =========================
def get_player_total_stats(player_data: dict) -> dict:
    total = {
        'max_hp': _ival(player_data.get('max_hp')),
        'attack': _ival(player_data.get('attack')),
        'defense': _ival(player_data.get('defense')),
        'initiative': _ival(player_data.get('initiative')),
        'luck': _ival(player_data.get('luck'))
    }
    inventory = player_data.get('inventory', {}) or {}
    equipped = player_data.get('equipment', {}) or {}
    for slot, unique_id in (equipped.items() if isinstance(equipped, dict) else []):
        if not unique_id: continue
        inst = inventory.get(unique_id)
        if not isinstance(inst, dict): continue
        ench = inst.get('enchantments', {}) or {}
        for stat_key, data in ench.items():
            val = _ival((data or {}).get('value'))
            if stat_key == 'dmg': total['attack'] += val
            elif stat_key == 'hp': total['max_hp'] += val
            elif stat_key in ('defense', 'initiative', 'luck'): total[stat_key] += val
    
    clan_id = player_data.get("clan_id")
    if clan_id:
        clan_buffs = clan_manager.get_clan_buffs(clan_id)
        
        if "all_stats_percent" in clan_buffs:
            percent_bonus = 1 + (clan_buffs["all_stats_percent"] / 100.0)
            total['max_hp'] = int(total['max_hp'] * percent_bonus)
            total['attack'] = int(total['attack'] * percent_bonus)
            total['defense'] = int(total['defense'] * percent_bonus)
            
        if "flat_hp_bonus" in clan_buffs:
            total['max_hp'] += clan_buffs["flat_hp_bonus"]
            
    return total

def get_player_dodge_chance(player_data: dict) -> float:
    total_stats = get_player_total_stats(player_data)
    initiative = total_stats.get('initiative', 0)
    dodge_chance = (initiative * 0.4) / 100.0
    return min(dodge_chance, 0.75)

def get_player_double_attack_chance(player_data: dict) -> float:
    total_stats = get_player_total_stats(player_data)
    initiative = total_stats.get('initiative', 0)
    double_attack_chance = (initiative * 0.25) / 100.0
    return min(double_attack_chance, 0.50)

def is_unique_item_entry(value) -> bool:
    return isinstance(value, dict) and ("base_id" in value or "tpl" in value or "id" in value)

def get_equipped_map(player_data: dict) -> dict:
    inv = player_data.get("inventory", {}) or {}
    eq  = player_data.get("equipment", {}) or {}
    out = {}
    for slot, uid in (eq or {}).items():
        if not uid:
            out[slot] = (None, None); continue
        inst = inv.get(uid)
        if is_unique_item_entry(inst):
            out[slot] = (uid, inst)
        else:
            out[slot] = (None, None)
    return out

def can_equip_slot(slot: str) -> bool:
    return slot in {"arma","elmo","armadura","calca","luvas","botas","colar","anel","brinco"}

def get_player_max_energy(player_data: dict) -> int:
    base_max = _ival(player_data.get('max_energy'), 20)
    bonus = _ival(get_player_perk_value(player_data, 'max_energy_bonus', 0))
    return base_max + bonus

def add_energy(player_data: dict, amount: int = 1) -> dict:
    max_e = get_player_max_energy(player_data)
    cur = _ival(player_data.get('energy'))
    new_val = min(cur + int(amount), max_e)
    player_data['energy'] = max(0, new_val)
    return player_data

def spend_energy(player_data: dict, amount: int = 1) -> bool:
    amount = max(0, int(amount))
    cur = _ival(player_data.get('energy'))
    if cur < amount:
        return False
    player_data['energy'] = cur - amount
    return True

def get_gather_energy_cost(player_data: dict) -> int:
    return int(get_player_perk_value(player_data, 'gather_energy_cost', 1))

def try_consume_energy_for_gather(player_data: dict) -> bool:
    cost = get_gather_energy_cost(player_data)
    if cost <= 0:
        return True
    return spend_energy(player_data, cost)

# =========================
# TIMED STATE HELPERS
# =========================
def set_last_chat_id(user_id: int, chat_id: int):
    pdata = get_player_data(user_id)
    if not pdata:
        return
    try:
        pdata["last_chat_id"] = int(chat_id)
    except Exception:
        pdata["last_chat_id"] = None
    save_player_data(user_id, pdata)

def ensure_timed_state(pdata: dict, action: str, seconds: int, details: dict | None, chat_id: int | None):
    start = utcnow().replace(microsecond=0)
    finish = start + timedelta(seconds=int(seconds))
    pdata["player_state"] = {
        "action": action,
        "started_at": start.isoformat(),
        "finish_time": finish.isoformat(),
        "details": details or {}
    }
    if chat_id is not None:
        try:
            pdata["last_chat_id"] = int(chat_id)
        except Exception:
            pdata["last_chat_id"] = None
    return pdata

def needs_class_choice(player_data: dict) -> bool:
    lvl = _ival(player_data.get("level"), 1)
    already_has_class = bool(player_data.get("class"))
    already_offered = bool(player_data.get("class_choice_offered"))
    return (lvl >= 10) and (not already_has_class) and (not already_offered)

def mark_class_choice_offered(user_id: int) -> None:
    pdata = get_player_data(user_id)
    if not pdata:
        return
    pdata["class_choice_offered"] = True
    save_player_data(user_id, pdata)

def _try_finalize_timed_action_inplace(player_data: dict) -> bool:
    state = player_data.get("player_state") or {}
    action = state.get("action")
    user_id = player_data.get("user_id")

    actions_com_timer = ("refining", "crafting", "collecting", "exploring", "travel")
    if action not in actions_com_timer:
        return False
    
    try:
        finish_time_iso = state.get("finish_time")
        finish_ts = state.get("travel_finish_ts")
        
        hora_de_termino = 0
        if finish_time_iso:
            hora_de_termino = datetime.fromisoformat(finish_time_iso).timestamp()
        elif finish_ts:
            hora_de_termino = float(finish_ts)
        
        hora_atual = time.time()
        
        if hora_de_termino > 0 and hora_atual >= hora_de_termino:
            if action == "travel":
                dest = state.get("travel_dest")
                if dest:
                    player_data["current_location"] = dest
            
            player_data["player_state"] = {"action": "idle"}
            return True
        else:
            return False
            
    except Exception as e:
        player_data["player_state"] = {"action": "idle"}
        return True

    return False

# =========================
# RESPEC / RESET DE STATS
# =========================
def _get_default_baseline_from_new_player() -> dict:
    return {"max_hp": 50, "attack": 5, "defense": 3, "initiative": 5, "luck": 5}

def _ensure_base_stats_block_inplace(pdata: dict) -> bool:
    changed = False
    base = pdata.get("base_stats")
    defaults = _get_default_baseline_from_new_player()

    if base is None and isinstance(pdata.get("invested"), dict):
        inv = pdata.get("invested") or {}
        hp_inv   = _ival(inv.get("hp"))
        atk_inv  = _ival(inv.get("attack"))
        def_inv  = _ival(inv.get("defense"))
        ini_inv  = _ival(inv.get("initiative"))
        luck_inv = _ival(inv.get("luck"))
        base = {
            "max_hp":     max(1, _ival(pdata.get("max_hp"), defaults["max_hp"]) - hp_inv),
            "attack":     max(0, _ival(pdata.get("attack"), defaults["attack"]) - atk_inv),
            "defense":    max(0, _ival(pdata.get("defense"), defaults["defense"]) - def_inv),
            "initiative": max(0, _ival(pdata.get("initiative"), defaults["initiative"]) - ini_inv),
            "luck":       max(0, _ival(pdata.get("luck"), defaults["luck"]) - luck_inv),
        }
        pdata["base_stats"] = base
        changed = True

    if not isinstance(pdata.get("base_stats"), dict):
        pdata["base_stats"] = dict(defaults)
        changed = True
    else:
        b = pdata["base_stats"]
        out = {}
        for k in _BASELINE_KEYS:
            out[k] = _ival(b.get(k), defaults[k])
        if out != b:
            pdata["base_stats"] = out
            changed = True

    return changed

def _get_class_key_normalized(pdata: dict) -> Optional[str]:
    ck = pdata.get("class_key") or pdata.get("class") or pdata.get("classe") or pdata.get("class_type")
    if isinstance(ck, str) and ck.strip():
        return ck.strip().lower()
    return None

def _get_point_gains_for_class(ckey: Optional[str]) -> dict:
    gains = CLASS_POINT_GAINS.get((ckey or "").lower()) or CLASS_POINT_GAINS["_default"]
    full = {}
    for k in _BASELINE_KEYS:
        full[k] = max(1, _ival(gains.get(k), CLASS_POINT_GAINS["_default"][k]))
    return full

def allowed_points_for_level(pdata: dict) -> int:
    return _allowed_points_for_level_with_class(pdata)

def compute_spent_status_points(pdata: dict) -> int:
    base = pdata.get("base_stats") or _get_default_baseline_from_new_player()
    ckey = _get_class_key_normalized(pdata)
    gains = _get_point_gains_for_class(ckey)

    spent = 0
    for k in _BASELINE_KEYS:
        cur = _ival(pdata.get(k), base[k])
        delta = cur - _ival(base.get(k))
        if delta <= 0:
            continue
        gp = max(1, int(gains.get(k, 1)))
        spent += (delta + gp - 1) // gp
    return spent

def _sync_stat_points_to_level_cap_inplace(pdata: dict) -> bool:
    allowed = allowed_points_for_level(pdata)
    spent = compute_spent_status_points(pdata)
    desired = max(0, allowed - spent)
    cur = max(0, _ival(pdata.get("stat_points"), 0))
    if cur != desired:
        pdata["stat_points"] = desired
        return True
    return False

def reset_stats_and_refund_points(pdata: dict) -> int:
    _ensure_base_stats_block_inplace(pdata)
    base = pdata["base_stats"]

    spent_before = compute_spent_status_points(pdata)

    for k in _BASELINE_KEYS:
        pdata[k] = _ival(base.get(k))

    pdata["stat_points"] = allowed_points_for_level(pdata)

    if isinstance(pdata.get("invested"), dict):
        pdata["invested"] = {k: 0 for k in ("hp", "attack", "defense", "initiative", "luck")}

    try:
        totals = get_player_total_stats(pdata)
        max_hp = _ival(totals.get("max_hp"), pdata.get("max_hp"))
        pdata["current_hp"] = max(1, min(_ival(pdata.get("current_hp"), max_hp), max_hp))
    except Exception:
        pass

    return spent_before

# =========================
# CLASS / EQUIP GATING
# =========================
def _normalize_class_key_from_player(player_data: dict) -> Optional[str]:
    def _as_dict(obj):
        return obj if isinstance(obj, dict) else {}
    candidates = [
        _as_dict(player_data.get("class")).get("type"),
        _as_dict(player_data.get("classe")).get("type"),
        player_data.get("class_type"),
        player_data.get("classe_tipo"),
        player_data.get("class_key"),
        player_data.get("classe"),
        player_data.get("class"),
    ]
    for c in candidates:
        if isinstance(c, str) and c.strip():
            return c.strip().lower()
    return None

def _class_req_from_base(base_id: Optional[str]):
    if not base_id:
        return None
    base = ITEMS_DATA.get(base_id) or {}
    return base.get("class_req")

def is_item_allowed_for_player_class(player_data: dict, item: dict) -> Tuple[bool, Optional[str]]:
    player_class = _normalize_class_key_from_player(player_data)

    req = item.get("class_req")
    if not req:
        req = _class_req_from_base(item.get("base_id"))

    if not req:
        return True, None

    if isinstance(req, str):
        req_list = [req.strip().lower()] if req.strip() else []
    elif isinstance(req, (list, tuple)):
        req_list = [str(x).strip().lower() for x in req if str(x).strip()]
    else:
        req_list = []

    if not req_list:
        return True, None

    if player_class is None:
        return False, "Classe do jogador não definida."

    if player_class in req_list:
        return True, None

    disp = item.get("display_name") or item.get("base_id") or "item"
    return False, f"⚠️ {disp} é exclusivo para {', '.join(req_list)}."

def _get_item_slot_from_base(base_id: Optional[str]) -> Optional[str]:
    if not base_id:
        return None
    entry = ITEMS_DATA.get(base_id) or {}
    slot = entry.get("slot")
    if isinstance(slot, str) and slot.strip():
        return slot.strip()
    return None

def _get_unique_item_from_inventory(player_data: dict, unique_id: str) -> Optional[dict]:
    inv = player_data.get("inventory", {}) or {}
    val = inv.get(unique_id)
    return val if is_unique_item_entry(val) else None

def equip_unique_item_for_user(user_id: int, unique_id: str, expected_slot: Optional[str] = None) -> Tuple[bool, str]:
    pdata = get_player_data(user_id)
    if not pdata:
        return False, "Jogador não encontrado."

    inv = pdata.get("inventory", {}) or {}
    item = _get_unique_item_from_inventory(pdata, unique_id)
    if not item:
        return False, "Item não encontrado no inventário."

    base_id = item.get("base_id")
    slot_from_item = _get_item_slot_from_base(base_id) or item.get("slot")
    if not slot_from_item:
        return False, "Item sem slot reconhecido."

    slot_from_item = str(slot_from_item).strip().lower()
    if not can_equip_slot(slot_from_item):
        return False, f"Slot inválido: {slot_from_item}"

    if expected_slot:
        exp = expected_slot.strip().lower()
        if exp != slot_from_item:
            return False, f"Este item é do slot '{slot_from_item}', não '{exp}'."

    ok, err = is_item_allowed_for_player_class(pdata, item)
    if not ok:
        return False, err or "Sua classe não pode equipar este item."

    eq = pdata.setdefault("equipment", {})
    prev = eq.get(slot_from_item)
    eq[slot_from_item] = unique_id

    save_player_data(user_id, pdata)

    name = item.get("display_name") or base_id or "Item"
    if prev and prev in inv and isinstance(inv[prev], dict):
        prev_name = inv[prev].get("display_name") or inv[prev].get("base_id") or prev
        return True, f"Equipado {name} em {slot_from_item}. (substituiu {prev_name})"
    return True, f"Equipado {name} em {slot_from_item}."

# =========================
# PROGRESSÃO / MIGRAÇÃO
# =========================
def _migrate_point_pool_to_stat_points_inplace(pdata: dict) -> bool:
    changed = False
    if "point_pool" in pdata:
        try:
            add = _ival(pdata.get("point_pool"), 0)
        except Exception:
            add = 0
        cur = _ival(pdata.get("stat_points"), 0)
        new_val = max(0, cur + max(0, add))
        if new_val != cur:
            pdata["stat_points"] = new_val
            changed = True
        del pdata["point_pool"]
        changed = True
    return changed

def _compute_class_baseline_for_level(class_key: Optional[str], level: int) -> dict:
    lvl = max(1, int(level or 1))
    prog = CLASS_PROGRESSIONS.get((class_key or "").lower()) or CLASS_PROGRESSIONS["_default"]

    base = dict(prog["BASE"])
    per  = dict(prog["PER_LVL"])
    if lvl <= 1:
        return base

    levels_up = lvl - 1
    out = {}
    for k in _BASELINE_KEYS:
        out[k] = _ival(base.get(k)) + _ival(per.get(k)) * levels_up
    return out

def _current_invested_delta_over_baseline(pdata: dict, baseline: dict) -> dict:
    delta = {}
    for k in _BASELINE_KEYS:
        cur = _ival(pdata.get(k), baseline.get(k))
        base = _ival(baseline.get(k))
        d = cur - base
        delta[k] = max(0, d)
    return delta

def _apply_class_progression_sync_inplace(pdata: dict) -> bool:
    changed = False
    lvl = _ival(pdata.get("level"), 1)
    ckey = _get_class_key_normalized(pdata)
    class_baseline = _compute_class_baseline_for_level(ckey, lvl)

    invested_delta = _current_invested_delta_over_baseline(pdata, class_baseline)

    cur_bs = pdata.get("base_stats") or {}
    if any(_ival(cur_bs.get(k)) != _ival(class_baseline.get(k)) for k in _BASELINE_KEYS):
        pdata["base_stats"] = {k: _ival(class_baseline.get(k)) for k in _BASELINE_KEYS}
        changed = True

    for k in _BASELINE_KEYS:
        desired = _ival(class_baseline.get(k)) + _ival(invested_delta.get(k))
        if _ival(pdata.get(k)) != desired:
            pdata[k] = desired
            changed = True

    try:
        totals = get_player_total_stats(pdata)
        max_hp = _ival(totals.get("max_hp"), pdata.get("max_hp"))
        cur_hp = _ival(pdata.get("current_hp"), max_hp)
        new_hp = min(max_hp, max(1, cur_hp))
        if new_hp != cur_hp:
            pdata["current_hp"] = new_hp
            changed = True
    except Exception:
        pass

    return changed

def _allowed_points_for_level_with_class(pdata: dict) -> int:
    lvl = _ival(pdata.get("level"), 1)
    ckey = _get_class_key_normalized(pdata)
    prog = CLASS_PROGRESSIONS.get(ckey or "") or CLASS_PROGRESSIONS["_default"]
    per_lvl = _ival(prog.get("FREE_POINTS_PER_LVL"), 0)
    return per_lvl * max(0, lvl - 1)

# =========================
# FUNÇÕES DE LÓGICA DO PVP
# =========================

def get_pvp_points(player_data: dict) -> int:
    return int(player_data.get("pvp_points", 0))

def add_pvp_points(player_data: dict, amount: int):
    current_points = get_pvp_points(player_data)
    player_data["pvp_points"] = max(0, current_points + amount)

def get_pvp_entries(player_data: dict) -> int:
    today = datetime.now(timezone.utc).date().isoformat()
    if player_data.get("last_pvp_entry_reset") != today:
        player_data["pvp_entries_left"] = DEFAULT_PVP_ENTRIES
        player_data["last_pvp_entry_reset"] = today
    
    return player_data.get("pvp_entries_left", DEFAULT_PVP_ENTRIES)

def use_pvp_entry(player_data: dict) -> bool:
    current_entries = get_pvp_entries(player_data)
    if current_entries > 0:
        player_data["pvp_entries_left"] = current_entries - 1
        return True
    return False

def add_pvp_entries(player_data: dict, amount: int):
    current_entries = get_pvp_entries(player_data)
    player_data["pvp_entries_left"] = current_entries + amount

    # Adicione estas duas funções no final de modules/player_manager.py

def clear_player_cache(user_id: int) -> bool:
    """
    NOVO: Remove um jogador específico do cache em memória.
    Retorna True se o jogador estava no cache e foi removido.
    """
    if user_id in _player_cache:
        del _player_cache[user_id]
        logging.info(f"Cache para o jogador {user_id} foi limpo manualmente.")
        return True
    return False

def clear_all_player_cache() -> int:
    """
    NOVO: Limpa completamente o cache de todos os jogadores.
    Retorna o número de jogadores que foram removidos do cache.
    """
    num_items = len(_player_cache)
    _player_cache.clear()
    logging.info(f"Cache completo foi limpo. {num_items} jogadores removidos.")
    return num_items