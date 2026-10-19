"""Persistent, server-authoritative dynamic events for Eldora."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256

from bson import ObjectId
from pymongo import ReturnDocument

from modules.player.core import users_collection
from modules.game_data.items import ITEMS_DATA


EVENTS = users_collection.database["dynamic_events"] if users_collection is not None else None
PARTICIPANTS = users_collection.database["dynamic_event_participants"] if users_collection is not None else None
CONTRIBUTIONS = users_collection.database["dynamic_event_contributions"] if users_collection is not None else None
_indexes_ready = False

DEFAULT_TIERS = [25, 80, 170, 300, 500]
DEFAULT_REWARDS = [
    {"gold": 100, "items": [{"item_id": "folha_sombria", "quantity": 2}]},
    {"gold": 200, "items": [{"item_id": "essencia_purificadora", "quantity": 1}]},
    {"gold": 350, "items": [{"item_id": "folha_sombria", "quantity": 5}]},
    {"gold": 500, "items": [{"item_id": "essencia_purificadora", "quantity": 3}]},
    {"gold": 1000, "items": [{"item_id": "folha_sombria", "quantity": 10}]},
]
DEFAULT_CORRUPTION = {
    "enabled": False,
    "chance": 15,
    "portal_enabled": True,
    "modifiers": {"hp": 2.0, "attack": 2.0, "defense": 2.0, "xp": 1.15},
    "essence_drop_chance": 8,
}


class EventError(ValueError):
    pass


def utcnow():
    return datetime.now(timezone.utc)


def points_after_daily_cap(base_points, already_today, daily_cap):
    return min(max(0, int(base_points)), max(0, int(daily_cap) - int(already_today)))


def ensure_indexes():
    global _indexes_ready
    if EVENTS is None:
        return
    if _indexes_ready:
        return
    EVENTS.create_index("event_key", unique=True)
    EVENTS.create_index([("state", 1), ("starts_at", 1), ("ends_at", 1)])
    PARTICIPANTS.create_index([("event_id", 1), ("character_id", 1)], unique=True)
    PARTICIPANTS.create_index([("event_id", 1), ("points", -1), ("updated_at", 1)])
    CONTRIBUTIONS.create_index([("event_id", 1), ("character_id", 1), ("action_key", 1)], unique=True)
    _indexes_ready = True


def _event_id(event_id):
    try:
        return ObjectId(str(event_id))
    except Exception as exc:
        raise EventError("Evento inválido.") from exc


def _public(doc):
    if not doc:
        return None
    result = dict(doc)
    result["id"] = str(result.pop("_id"))
    return result


def normalize_config(data: dict, *, partial=False):
    cfg = {}
    if not partial or "title" in data:
        cfg["title"] = str(data.get("title", "")).strip()[:80]
        if not cfg["title"]:
            raise EventError("Informe o nome do evento.")
    for key, limit in (("description", 1000), ("banner", 500)):
        if key in data or not partial:
            cfg[key] = str(data.get(key, "")).strip()[:limit]
    if cfg.get("banner") and not cfg["banner"].startswith("https://"):
        raise EventError("O banner deve usar um endereço HTTPS.")
    if not partial or "starts_at" in data:
        cfg["starts_at"] = _parse_date(data.get("starts_at"))
    if not partial or "ends_at" in data:
        cfg["ends_at"] = _parse_date(data.get("ends_at"))
    if "starts_at" in cfg and "ends_at" in cfg and cfg["ends_at"] <= cfg["starts_at"]:
        raise EventError("O encerramento precisa ser posterior ao início.")
    for key, minimum, maximum, default in (
        ("global_goal", 1, 100_000_000, 5000),
        ("daily_cap", 1, 100_000, 150),
        ("min_level", 1, 10000, 1),
        ("collective_min_points", 1, 100_000, 25),
    ):
        if key in data or not partial:
            value = int(data.get(key, default))
            if not minimum <= value <= maximum:
                raise EventError(f"{key} fora do intervalo permitido.")
            cfg[key] = value
    if "rules" in data or not partial:
        rules = data.get("rules") or {"creature": 1, "elite": 5, "dungeon": 20, "event_boss": 50}
        cfg["rules"] = {}
        for key in ("creature", "elite", "dungeon", "event_boss"):
            value = int(rules.get(key, 0))
            if not 0 <= value <= 10000:
                raise EventError("Regra de pontuação inválida.")
            cfg["rules"][key] = value
    if "tiers" in data or not partial:
        tiers = data.get("tiers") or DEFAULT_TIERS
        if not isinstance(tiers, list) or not 1 <= len(tiers) <= 10:
            raise EventError("Configure de 1 a 10 marcos de recompensa.")
        cfg["tiers"] = [int(x) for x in tiers]
        if any(x <= 0 for x in cfg["tiers"]) or cfg["tiers"] != sorted(set(cfg["tiers"])):
            raise EventError("Os marcos devem ser únicos e crescentes.")
    if "rewards" in data or not partial:
        rewards = data.get("rewards") or DEFAULT_REWARDS
        if not isinstance(rewards, list) or len(rewards) != len(cfg.get("tiers", DEFAULT_TIERS)):
            raise EventError("Informe uma recompensa para cada marco.")
        cfg["rewards"] = [_validate_reward(r) for r in rewards]
    if "collective_reward" in data or not partial:
        cfg["collective_reward"] = _validate_reward(data.get("collective_reward") or {"gold": 750, "items": [{"item_id": "essencia_purificadora", "quantity": 2}]})
    if "corruption" in data or not partial:
        raw_corruption = data.get("corruption") or {}
        if not isinstance(raw_corruption, dict):
            raise EventError("A configuração de corrupção precisa ser um objeto.")
        enabled = raw_corruption.get("enabled", False)
        if not isinstance(enabled, bool):
            raise EventError("A opção de corrupção precisa ser verdadeira ou falsa.")
        portal_enabled = raw_corruption.get("portal_enabled", True)
        if not isinstance(portal_enabled, bool):
            raise EventError("A opção do Portal Sombrio precisa ser verdadeira ou falsa.")
        try:
            chance = int(raw_corruption.get("chance", DEFAULT_CORRUPTION["chance"]))
        except (TypeError, ValueError) as exc:
            raise EventError("A chance de corrupção precisa ser um número inteiro.") from exc
        if not 0 <= chance <= 100:
            raise EventError("A chance de corrupção deve ficar entre 0 e 100.")
        raw_modifiers = raw_corruption.get("modifiers") or DEFAULT_CORRUPTION["modifiers"]
        if not isinstance(raw_modifiers, dict):
            raise EventError("Os modificadores da corrupção precisam ser um objeto.")
        modifiers = {}
        for stat, default in DEFAULT_CORRUPTION["modifiers"].items():
            try:
                value = float(raw_modifiers.get(stat, default))
            except (TypeError, ValueError) as exc:
                raise EventError(f"Modificador de {stat} inválido.") from exc
            if not 1.0 <= value <= 4.0:
                raise EventError(f"Modificador de {stat} deve ficar entre 1 e 4.")
            modifiers[stat] = value
        try:
            essence_drop_chance = int(raw_corruption.get(
                "essence_drop_chance", DEFAULT_CORRUPTION["essence_drop_chance"]
            ))
        except (TypeError, ValueError) as exc:
            raise EventError("A chance da Essência Sombria precisa ser um número inteiro.") from exc
        if not 0 <= essence_drop_chance <= 100:
            raise EventError("A chance da Essência Sombria deve ficar entre 0 e 100.")
        cfg["corruption"] = {
            "enabled": enabled,
            "chance": chance,
            "portal_enabled": portal_enabled,
            "modifiers": modifiers,
            "essence_drop_chance": essence_drop_chance,
        }
    if "tiers" in cfg and "rewards" not in cfg and not partial:
        cfg["rewards"] = DEFAULT_REWARDS[:len(cfg["tiers"])]
    if "tiers" in cfg and "rewards" in cfg and len(cfg["tiers"]) != len(cfg["rewards"]):
        raise EventError("A quantidade de recompensas deve corresponder aos marcos.")
    return cfg


def _parse_date(value):
    if isinstance(value, datetime):
        dt = value
        # PyMongo decodes BSON datetimes as naive UTC unless tz_aware is enabled.
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception as exc:
            raise EventError("Data inválida; use ISO 8601 com fuso horário.") from exc
    if dt.tzinfo is None:
        raise EventError("As datas precisam incluir fuso horário.")
    return dt.astimezone(timezone.utc)


def _validate_reward(value):
    if not isinstance(value, dict):
        raise EventError("Formato de recompensa inválido.")
    gold = int(value.get("gold", 0))
    if gold < 0 or gold > 1_000_000:
        raise EventError("Quantidade de ouro inválida.")
    items = []
    for entry in value.get("items", []):
        item_id = str(entry.get("item_id", ""))
        qty = int(entry.get("quantity", 0))
        meta = ITEMS_DATA.get(item_id)
        if not meta or not meta.get("stackable") or not 1 <= qty <= 10000:
            raise EventError(f"Item ou quantidade inválida: {item_id or '(vazio)'}.")
        items.append({"item_id": item_id, "quantity": qty})
    return {"gold": gold, "items": items}


def create_event(data: dict):
    ensure_indexes()
    cfg = normalize_config(data)
    now = utcnow()
    doc = {
        **cfg,
        "event_key": str(data.get("event_key") or f"invasao-sombria-{now:%Y%m%d%H%M%S}"),
        "state": "scheduled" if cfg["starts_at"] > now else "active",
        "global_points": 0,
        "participant_count": 0,
        "global_completed_at": None,
        "created_at": now,
        "updated_at": now,
    }
    result = EVENTS.insert_one(doc)
    return _public({**doc, "_id": result.inserted_id})


def update_event(event_id, data):
    existing = EVENTS.find_one({"_id": _event_id(event_id), "state": {"$in": ["scheduled", "active"]}})
    if not existing:
        raise EventError("Evento não encontrado ou já encerrado.")
    merged = {**existing, **data}
    normalized = normalize_config(merged)
    cfg = {key: normalized[key] for key in data if key in normalized}
    cfg["updated_at"] = utcnow()
    doc = EVENTS.find_one_and_update({"_id": _event_id(event_id), "state": {"$in": ["scheduled", "active"]}}, {"$set": cfg}, return_document=ReturnDocument.AFTER)
    if not doc:
        raise EventError("Evento não encontrado ou já encerrado.")
    return _public(doc)


def transition_event(event_id, action):
    target = {"start": "active", "end": "ended", "cancel": "cancelled"}.get(action)
    if not target:
        raise EventError("Ação inválida.")
    allowed = ["scheduled", "active"] if action != "start" else ["scheduled"]
    now = utcnow()
    changes = {"state": target, "updated_at": now}
    if action == "start":
        changes["starts_at"] = now
    doc = EVENTS.find_one_and_update({"_id": _event_id(event_id), "state": {"$in": allowed}}, {"$set": changes}, return_document=ReturnDocument.AFTER)
    if not doc:
        raise EventError("Estado do evento não permite essa ação.")
    return _public(doc)


def close_expired_events(now=None):
    if EVENTS is None:
        return
    now = now or utcnow()
    EVENTS.update_many({"state": "scheduled", "starts_at": {"$lte": now}, "ends_at": {"$gt": now}}, {"$set": {"state": "active", "updated_at": now}})
    EVENTS.update_many({"state": {"$in": ["scheduled", "active"]}, "ends_at": {"$lte": now}}, {"$set": {"state": "ended", "updated_at": now}})


def list_events(include_past=False):
    ensure_indexes()
    close_expired_events()
    query = {} if include_past else {"state": {"$in": ["scheduled", "active"]}}
    return [_public(x) for x in EVENTS.find(query).sort("starts_at", -1).limit(50)]


def active_corruption_event(now=None):
    """Retorna a invasão ativa que controla a corrupção dos mobs do mapa."""
    if EVENTS is None:
        return None
    now = now or utcnow()
    close_expired_events(now)
    active = EVENTS.find(
        {
            "state": "active",
            "starts_at": {"$lte": now},
            "ends_at": {"$gt": now},
        }
    ).sort("starts_at", -1)
    for event in active:
        corruption = event.get("corruption")
        # Compatibilidade com Invasões Sombrias criadas antes deste campo existir.
        if not isinstance(corruption, dict):
            if str(event.get("event_key", "")).startswith("invasao-sombria-"):
                corruption = {"enabled": True, "chance": DEFAULT_CORRUPTION["chance"]}
            else:
                continue
        if not corruption.get("enabled"):
            continue
        result = dict(event)
        try:
            chance = int(corruption.get("chance", DEFAULT_CORRUPTION["chance"]))
        except (TypeError, ValueError):
            chance = DEFAULT_CORRUPTION["chance"]
        result["corruption"] = {
            "enabled": True,
            "chance": max(0, min(100, chance)),
            "portal_enabled": corruption.get("portal_enabled", True) is True,
            "modifiers": {
                stat: max(1.0, min(4.0, float((corruption.get("modifiers") or {}).get(stat, default))))
                for stat, default in DEFAULT_CORRUPTION["modifiers"].items()
            },
            "essence_drop_chance": max(0, min(100, int(corruption.get(
                "essence_drop_chance", DEFAULT_CORRUPTION["essence_drop_chance"]
            )))),
        }
        return result
    return None


def event_detail(event_id, character_id=None):
    close_expired_events()
    doc = EVENTS.find_one({"_id": _event_id(event_id)})
    if not doc:
        raise EventError("Evento não encontrado.")
    participant = PARTICIPANTS.find_one({"event_id": doc["_id"], "character_id": str(character_id)}) if character_id else None
    safe = _public(doc)
    safe["personal"] = _public(participant) if participant else {"points": 0, "points_today": 0, "claimed_tiers": [], "collective_claimed": False}
    safe["tiers_view"] = [{"tier": i + 1, "points": points, "reward": doc["rewards"][i], "state": "claimed" if participant and i in participant.get("claimed_tiers", []) else "available" if participant and participant.get("points", 0) >= points else "locked"} for i, points in enumerate(doc["tiers"])]
    return safe


def ranking(event_id, page=1, page_size=20):
    doc = EVENTS.find_one({"_id": _event_id(event_id)}, {"_id": 1})
    if not doc:
        raise EventError("Evento não encontrado.")
    page, page_size = max(1, int(page)), min(50, max(1, int(page_size)))
    rows = list(PARTICIPANTS.find({"event_id": doc["_id"], "points": {"$gt": 0}}, {"character_id": 1, "character_name": 1, "points": 1}).sort([("points", -1), ("updated_at", 1)]).skip((page - 1) * page_size).limit(page_size))
    return {"page": page, "page_size": page_size, "total": PARTICIPANTS.count_documents({"event_id": doc["_id"], "points": {"$gt": 0}}), "entries": [{"rank": (page - 1) * page_size + i + 1, "name": row.get("character_name", "Aventureiro"), "points": int(row.get("points", 0))} for i, row in enumerate(rows)]}


def contribute(character_id, action_key, kind, *, character_name="Aventureiro", origin="manual", battle_id=None, corruption_event_id=None):
    """Award points once; all writes for an action are committed atomically."""
    ensure_indexes()
    now = utcnow()
    action_key = str(action_key or "")
    if not action_key or len(action_key) > 200:
        return None
    close_expired_events(now)
    player = users_collection.find_one({"_id": ObjectId(str(character_id))}, {"level": 1, "character_name": 1})
    if not player:
        return None
    session = EVENTS.database.client.start_session()
    result = {"awards": [], "duplicate": False}
    def txn(s):
        nonlocal result
        active_events = list(EVENTS.find({"state": "active", "starts_at": {"$lte": now}, "ends_at": {"$gt": now}}, session=s).sort("starts_at", -1))
        awards = []
        daily_key = now.strftime("%Y-%m-%d")
        for event in active_events:
            if kind not in event.get("rules", {}) or int(event.get("rules", {}).get(kind, 0)) <= 0:
                continue
            corruption = event.get("corruption")
            if not isinstance(corruption, dict) and str(event.get("event_key", "")).startswith("invasao-sombria-"):
                corruption = {"enabled": True, "chance": DEFAULT_CORRUPTION["chance"]}
            is_invasion = isinstance(corruption, dict) and corruption.get("enabled")
            if is_invasion:
                # A invasão só progride com monstros que o servidor marcou
                # como corrompidos para este evento específico.
                if str(event["_id"]) != str(corruption_event_id or ""):
                    continue
            if int(player.get("level", 1) or 1) < int(event.get("min_level", 1)):
                continue
            # The same server-validated activity may contribute to each active event.
            contribution_id = sha256(f"{event['_id']}:{character_id}:{action_key}".encode()).hexdigest()
            if CONTRIBUTIONS.find_one({"_id": contribution_id}, session=s):
                continue
            pkey = {"event_id": event["_id"], "character_id": str(character_id)}
            participant = PARTICIPANTS.find_one(pkey, session=s)
            current_today = int((participant or {}).get("points_today", 0)) if (participant or {}).get("day_key") == daily_key else 0
            amount = points_after_daily_cap(event["rules"][kind], current_today, event["daily_cap"])
            CONTRIBUTIONS.insert_one({"_id": contribution_id, "event_id": event["_id"], "character_id": str(character_id), "action_key": action_key, "kind": kind, "points_awarded": amount, "origin": origin, "battle_id": str(battle_id) if battle_id else None, "created_at": now}, session=s)
            if not participant:
                PARTICIPANTS.insert_one({**pkey, "character_name": str(player.get("character_name") or character_name)[:80], "points": 0, "points_today": 0, "day_key": daily_key, "claimed_tiers": [], "collective_claimed": False, "created_at": now}, session=s)
                EVENTS.update_one({"_id": event["_id"]}, {"$inc": {"participant_count": 1}}, session=s)
            participant_update = {
                "$set": {"day_key": daily_key, "updated_at": now, "character_name": str(player.get("character_name") or character_name)[:80]},
                "$inc": {"points": amount},
            }
            if (participant or {}).get("day_key") == daily_key:
                participant_update["$inc"]["points_today"] = amount
            else:
                participant_update["$set"]["points_today"] = amount
            PARTICIPANTS.update_one(pkey, participant_update, session=s)
            updated = EVENTS.find_one_and_update({"_id": event["_id"]}, {"$inc": {"global_points": amount}, "$set": {"updated_at": now}}, return_document=ReturnDocument.AFTER, session=s)
            if updated.get("global_points", 0) >= updated["global_goal"] and not updated.get("global_completed_at"):
                EVENTS.update_one({"_id": event["_id"], "global_completed_at": None}, {"$set": {"global_completed_at": now}}, session=s)
            awards.append({"awarded": amount, "event_id": str(event["_id"])})
        result = {"awards": awards, "duplicate": not awards and bool(active_events)}
    try:
        session.with_transaction(txn)
    except Exception as exc:
        if exc.__class__.__name__ == "DuplicateKeyError":
            result["duplicate"] = True
            return result
        raise
    finally:
        session.end_session()
    return result


def _apply_reward(player, reward):
    from modules.player.inventory import add_item_to_inventory, add_gold
    if reward.get("gold"):
        add_gold(player, int(reward["gold"]))
    for item in reward.get("items", []):
        add_item_to_inventory(player, item["item_id"], int(item["quantity"]))


def claim_reward(character_id, event_id, *, tier=None, collective=False):
    ensure_indexes()
    event_oid = _event_id(event_id)
    session = EVENTS.database.client.start_session()
    outcome = {}
    now = utcnow()
    def txn(s):
        nonlocal outcome
        event = EVENTS.find_one({"_id": event_oid}, session=s)
        if not event:
            raise EventError("Evento não encontrado.")
        pkey = {"event_id": event_oid, "character_id": str(character_id)}
        participant = PARTICIPANTS.find_one(pkey, session=s)
        if not participant:
            raise EventError("Você ainda não contribuiu para este evento.")
        if collective:
            if not event.get("global_completed_at") or participant.get("points", 0) < event.get("collective_min_points", 1):
                raise EventError("A recompensa coletiva ainda não está disponível para você.")
            if participant.get("collective_claimed"):
                raise EventError("Recompensa coletiva já resgatada.")
            reward = event["collective_reward"]
            updated = PARTICIPANTS.update_one({**pkey, "collective_claimed": {"$ne": True}, "points": {"$gte": event["collective_min_points"]}}, {"$set": {"collective_claimed": True, "updated_at": now}}, session=s)
        else:
            index = int(tier) - 1
            if index < 0 or index >= len(event["tiers"]):
                raise EventError("Marco de recompensa inválido.")
            threshold = event["tiers"][index]
            reward = event["rewards"][index]
            updated = PARTICIPANTS.update_one({**pkey, "points": {"$gte": threshold}, "claimed_tiers": {"$ne": index}}, {"$addToSet": {"claimed_tiers": index}, "$set": {"updated_at": now}}, session=s)
        if updated.modified_count != 1:
            raise EventError("Recompensa ainda bloqueada ou já resgatada.")
        player = users_collection.find_one({"_id": ObjectId(str(character_id))}, session=s)
        if not player:
            raise EventError("Personagem não encontrado.")
        _apply_reward(player, reward)
        users_collection.update_one({"_id": player["_id"]}, {"$set": {"inventory": player.get("inventory", {}), "gold": player.get("gold", 0)}}, session=s)
        outcome = {"success": True, "reward": reward, "gold": player.get("gold", 0)}
    try:
        session.with_transaction(txn)
    finally:
        session.end_session()
    return outcome
