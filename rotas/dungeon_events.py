# rotas/dungeon_events.py

from flask import Blueprint, current_app, jsonify, request

from modules.dungeon_event_service import (
    DungeonEventError,
    interagir_bau,
    interagir_luz,
    obter_estado_evento,
)


dungeon_events_bp = Blueprint(
    "dungeon_events",
    __name__
)


def _motor_cacada():
    return current_app.config.get(
        "SISTEMA_CACADA"
    )


@dungeon_events_bp.route(
    "/api/dungeon/evento/status",
    methods=["GET"]
)
def dungeon_event_status():
    try:
        user_id = request.args.get(
            "user_id"
        )
        dungeon_id = request.args.get(
            "dungeon_id"
        )
        puzzle_id = request.args.get(
            "puzzle_id"
        )

        result = obter_estado_evento(
            user_id=user_id,
            dungeon_id=dungeon_id,
            puzzle_id=puzzle_id,
            sistema_cacada=_motor_cacada(),
        )

        return jsonify(result), 200

    except DungeonEventError as exc:
        return jsonify({
            "success": False,
            "error": str(exc)
        }), 400

    except Exception:
        current_app.logger.exception(
            "Erro ao carregar evento de dungeon"
        )

        return jsonify({
            "success": False,
            "error": "Erro interno no evento da dungeon."
        }), 500


@dungeon_events_bp.route(
    "/api/dungeon/evento/luz",
    methods=["POST"]
)
def dungeon_event_light():
    try:
        data = (
            request.get_json(
                silent=True
            )
            or {}
        )

        result = interagir_luz(
            user_id=data.get(
                "user_id"
            ),
            dungeon_id=data.get(
                "dungeon_id"
            ),
            puzzle_id=data.get(
                "puzzle_id"
            ),
            indice=data.get(
                "indice"
            ),
            sistema_cacada=_motor_cacada(),
        )

        return jsonify(result), 200

    except DungeonEventError as exc:
        return jsonify({
            "success": False,
            "error": str(exc)
        }), 400

    except Exception:
        current_app.logger.exception(
            "Erro ao interagir com pedra da dungeon"
        )

        return jsonify({
            "success": False,
            "error": "Erro interno ao ativar a pedra."
        }), 500


@dungeon_events_bp.route(
    "/api/dungeon/evento/bau",
    methods=["POST"]
)
def dungeon_event_chest():
    try:
        data = (
            request.get_json(
                silent=True
            )
            or {}
        )

        result = interagir_bau(
            user_id=data.get(
                "user_id"
            ),
            dungeon_id=data.get(
                "dungeon_id"
            ),
            puzzle_id=data.get(
                "puzzle_id"
            ),
            sistema_cacada=_motor_cacada(),
        )

        # Enquanto o loot ainda não estiver configurado,
        # mantemos o estado do baú intacto.
        status = (
            200
            if result.get("success")
            else 409
        )

        return jsonify(
            result
        ), status

    except DungeonEventError as exc:
        return jsonify({
            "success": False,
            "error": str(exc)
        }), 400

    except Exception:
        current_app.logger.exception(
            "Erro ao interagir com baú da dungeon"
        )

        return jsonify({
            "success": False,
            "error": "Erro interno ao abrir o baú."
        }), 500