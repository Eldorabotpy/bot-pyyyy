"""Daily free entry quota and paid extra tickets for the web Coliseum PvP."""

from datetime import datetime
from threading import Lock
from zoneinfo import ZoneInfo

from bson import ObjectId


DAILY_FREE_ENTRIES = 10
TICKETS_FIELD = "coliseu_pvp_entry_tickets"
DAILY_DATE_FIELD = "coliseu_pvp_daily_date"
DAILY_USED_FIELD = "coliseu_pvp_daily_used"
_ENTRY_LOCK = Lock()


def _today_sao_paulo():
    return datetime.now(ZoneInfo("America/Sao_Paulo")).date().isoformat()


def _safe_int(value, default=0):
    try:
        return int(float(value if value is not None else default))
    except (TypeError, ValueError, OverflowError):
        return int(default)


def _as_object_id(char_id):
    value = str(char_id)
    return ObjectId(value) if ObjectId.is_valid(value) else None


def get_daily_entry_quota(users_collection, char_id, today=None):
    oid = _as_object_id(char_id)
    if oid is None:
        return None
    player = users_collection.find_one({"_id": oid})
    if not player:
        return None
    day = today or _today_sao_paulo()
    used = _safe_int(player.get(DAILY_USED_FIELD), 0)
    if player.get(DAILY_DATE_FIELD) != day:
        used = 0
    tickets = max(0, _safe_int(player.get(TICKETS_FIELD), 0))
    return {
        "limite": DAILY_FREE_ENTRIES,
        "usadas": used,
        "restantes": max(0, DAILY_FREE_ENTRIES - used),
        "tickets": tickets,
        "dia": day,
    }


def _usage_filter(player):
    query = {"_id": player["_id"]}
    for field in (DAILY_DATE_FIELD, DAILY_USED_FIELD):
        query[field] = player[field] if field in player else {"$exists": False}
    return query


def _rollback(users_collection, applied, today):
    for item in reversed(applied):
        player = item["player"]
        query = {
            "_id": player["_id"],
            DAILY_DATE_FIELD: today,
            DAILY_USED_FIELD: item["used"] + 1,
        }
        set_fields = {}
        unset_fields = {}
        for field in (DAILY_DATE_FIELD, DAILY_USED_FIELD):
            if field in player:
                set_fields[field] = player[field]
            else:
                unset_fields[field] = ""
        update = {}
        if set_fields:
            update["$set"] = set_fields
        if unset_fields:
            update["$unset"] = unset_fields
        if item["ticket"]:
            update["$inc"] = {TICKETS_FIELD: 1}
        if update:
            users_collection.update_one(query, update)


def consume_daily_entries(users_collection, char_ids, today=None):
    """Consume one entry per character, preflighting the whole match before updates."""
    day = today or _today_sao_paulo()
    ids = list(dict.fromkeys(str(char_id) for char_id in char_ids))
    with _ENTRY_LOCK:
        plan = []
        for char_id in ids:
            oid = _as_object_id(char_id)
            if oid is None:
                return {"sucesso": False, "bloqueado_id": char_id, "erro": "Personagem inválido."}
            player = users_collection.find_one({"_id": oid})
            if not player:
                return {"sucesso": False, "bloqueado_id": char_id, "erro": "Personagem não encontrado."}
            used = _safe_int(player.get(DAILY_USED_FIELD), 0)
            if player.get(DAILY_DATE_FIELD) != day:
                used = 0
            tickets = max(0, _safe_int(player.get(TICKETS_FIELD), 0))
            use_ticket = used >= DAILY_FREE_ENTRIES
            if use_ticket and tickets < 1:
                return {
                    "sucesso": False,
                    "bloqueado_id": char_id,
                    "quota": get_daily_entry_quota(users_collection, char_id, day),
                }
            plan.append({"id": char_id, "player": player, "used": used, "ticket": use_ticket})

        applied = []
        for item in plan:
            query = _usage_filter(item["player"])
            update = {"$set": {DAILY_DATE_FIELD: day, DAILY_USED_FIELD: item["used"] + 1}}
            if item["ticket"]:
                query[TICKETS_FIELD] = {"$gt": 0}
                update["$inc"] = {TICKETS_FIELD: -1}
            result = users_collection.update_one(query, update)
            if not result.modified_count:
                _rollback(users_collection, applied, day)
                return {"sucesso": False, "bloqueado_id": item["id"], "erro": "Não consegui reservar as entradas. Tente novamente."}
            applied.append(item)

        return {
            "sucesso": True,
            "cotas": {item["id"]: get_daily_entry_quota(users_collection, item["id"], day) for item in plan},
        }
