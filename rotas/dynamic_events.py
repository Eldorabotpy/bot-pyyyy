from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request

from modules.events import dynamic_event_service as events

dynamic_events_bp = Blueprint("dynamic_events", __name__)


def _sincronizar_evento_no_mapa(*, force=True):
    """Mantém as instâncias e os clientes do mapa alinhados ao evento ativo."""
    try:
        manager = current_app.config.get("SISTEMA_CACADA")
        if manager:
            manager.atualizar_evento_corrupcao(force=force)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Falha ao sincronizar corrupção dos monstros")


def _error(exc, status=400):
    return jsonify(success=False, error=str(exc)), status


@dynamic_events_bp.get("/api/eventos")
def public_events():
    try:
        result = events.list_events()
        _sincronizar_evento_no_mapa(force=False)
        return jsonify(success=True, events=result)
    except Exception:
        return _error("Não foi possível consultar os eventos.", 503)


@dynamic_events_bp.get("/api/eventos/<event_id>")
def public_event_detail(event_id):
    character_id = request.args.get("user_id")
    try:
        return jsonify(success=True, event=events.event_detail(event_id, character_id))
    except events.EventError as exc:
        return _error(exc, 404)


@dynamic_events_bp.get("/api/eventos/<event_id>/ranking")
def public_event_ranking(event_id):
    try:
        return jsonify(success=True, **events.ranking(event_id, request.args.get("page", 1)))
    except events.EventError as exc:
        return _error(exc, 404)


@dynamic_events_bp.post("/api/eventos/<event_id>/resgatar")
def public_event_claim(event_id):
    data = request.get_json(silent=True) or {}
    character_id = str(data.get("user_id") or "")
    try:
        result = events.claim_reward(character_id, event_id, tier=data.get("tier"), collective=bool(data.get("collective")))
        from modules.player.core import clear_player_cache
        import asyncio
        try:
            asyncio.run(clear_player_cache(character_id))
        except RuntimeError:
            pass
        return jsonify(**result)
    except events.EventError as exc:
        return _error(exc)
    except Exception:
        return _error("Não foi possível resgatar a recompensa.", 500)


@dynamic_events_bp.post("/admin/api/eventos")
def admin_create_event():
    from rotas.admin import admin_required
    @admin_required
    def create():
        try:
            event = events.create_event(request.get_json(silent=True) or {})
            _sincronizar_evento_no_mapa()
            return jsonify(success=True, event=event), 201
        except events.EventError as exc:
            return _error(exc)
        except Exception as exc:
            if exc.__class__.__name__ == "DuplicateKeyError":
                return _error("Esse identificador de evento já existe.", 409)
            return _error("Falha ao criar o evento.", 500)
    return create()


@dynamic_events_bp.patch("/admin/api/eventos/<event_id>")
def admin_update_event(event_id):
    from rotas.admin import admin_required
    @admin_required
    def update():
        try:
            event = events.update_event(event_id, request.get_json(silent=True) or {})
            _sincronizar_evento_no_mapa()
            return jsonify(success=True, event=event)
        except events.EventError as exc:
            return _error(exc)
        except Exception:
            return _error("Falha ao atualizar o evento.", 500)
    return update()


@dynamic_events_bp.post("/admin/api/eventos/<event_id>/<action>")
def admin_transition_event(event_id, action):
    from rotas.admin import admin_required
    @admin_required
    def transition():
        try:
            event = events.transition_event(event_id, action)
            _sincronizar_evento_no_mapa()
            return jsonify(success=True, event=event)
        except events.EventError as exc:
            return _error(exc)
    return transition()


@dynamic_events_bp.get("/admin/api/eventos")
def admin_list_events():
    from rotas.admin import admin_required
    @admin_required
    def listing():
        try:
            return jsonify(success=True, events=events.list_events(include_past=True))
        except Exception:
            return _error("Falha ao consultar eventos.", 500)
    return listing()


@dynamic_events_bp.get("/admin/api/eventos/<event_id>/contribuicoes")
def admin_contributions(event_id):
    from rotas.admin import admin_required
    @admin_required
    def listing():
        try:
            oid = events._event_id(event_id)
            rows = list(events.CONTRIBUTIONS.find({"event_id": oid}, {"_id": 0}).sort("created_at", -1).limit(100))
            return jsonify(success=True, contributions=rows)
        except events.EventError as exc:
            return _error(exc)
        except Exception:
            return _error("Falha ao consultar contribuições.", 500)
    return listing()


@dynamic_events_bp.get("/admin/api/eventos/<event_id>/participantes")
def admin_participants(event_id):
    from rotas.admin import admin_required
    @admin_required
    def listing():
        try:
            oid = events._event_id(event_id)
            page = max(1, int(request.args.get("page", 1)))
            size = min(100, max(1, int(request.args.get("page_size", 50))))
            query = {"event_id": oid}
            rows = list(events.PARTICIPANTS.find(query, {"_id": 0, "character_id": 1, "character_name": 1, "points": 1, "points_today": 1, "day_key": 1, "claimed_tiers": 1, "collective_claimed": 1}).sort([("points", -1), ("updated_at", 1)]).skip((page - 1) * size).limit(size))
            return jsonify(success=True, page=page, page_size=size, total=events.PARTICIPANTS.count_documents(query), participants=rows)
        except events.EventError as exc:
            return _error(exc)
        except Exception:
            return _error("Falha ao consultar participantes.", 500)
    return listing()


@dynamic_events_bp.post("/admin/api/eventos/invasao-sombria/padrao")
def admin_create_default_invasion():
    from rotas.admin import admin_required
    @admin_required
    def create():
        now = datetime.now(timezone.utc)
        try:
            event = events.create_event({
                "event_key": f"invasao-sombria-{now:%Y%m%d%H%M%S}",
                "title": "A Invasão Sombria",
                "description": "Criaturas corrompidas ameaçam Eldora. Una forças para estabilizar a fenda e conquiste recompensas pessoais e coletivas.",
                "starts_at": now.isoformat(), "ends_at": (now + timedelta(days=7)).isoformat(),
                "global_goal": 5000, "daily_cap": 150, "min_level": 1,
                "rules": {"creature": 1, "elite": 5, "dungeon": 0, "event_boss": 0},
                "corruption": {
                    "enabled": True,
                    "chance": 15,
                    "portal_enabled": True,
                    "modifiers": {"hp": 1.2, "attack": 1.1, "defense": 1.1, "xp": 1.15},
                    "essence_drop_chance": 8,
                },
            })
            _sincronizar_evento_no_mapa()
            return jsonify(success=True, event=event), 201
        except Exception as exc:
            if exc.__class__.__name__ == "DuplicateKeyError":
                return _error("Já existe um evento com esse identificador.", 409)
            return _error(str(exc) if isinstance(exc, events.EventError) else "Falha ao criar a Invasão Sombria.", 500)
    return create()
