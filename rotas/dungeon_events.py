# rotas/dungeon_events.py

from flask import Blueprint, current_app, jsonify, request

from modules.dungeon_event_service import (
    DungeonEventError,
    consumir_chave_masmorra,
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


@dungeon_events_bp.route("/api/dungeon/guia", methods=["GET"])
def dungeon_guide():
    """Consulta a execução ativa, sem criar instância nem consumir chave."""
    from modules.game_data.map_spawns import MAP_SPAWNS

    user_id = str(request.args.get("user_id") or "").strip()
    if not user_id:
        return jsonify(success=False, error="Jogador não informado."), 400
    motor = _motor_cacada()
    if not motor:
        return jsonify(success=False, error="Dungeon indisponível."), 503
    instance_id = motor.dungeon_jogador_instancia.get(user_id)
    if not instance_id:
        return jsonify(success=False, error="Você não está em uma execução ativa."), 404
    mobs = [m for m in list(motor.mobs_vivos.get("dungeon_01", {}).values())
            if m.get("dungeon_instance_id") == instance_id and not m.get("event_owner_id")]
    def is_boss(mob):
        return mob.get("dungeon_boss") or mob.get("monster_id") == "rei_caido_dungeon_01"
    remaining = sum(1 for m in mobs if m.get("dungeon_mob") and not is_boss(m))
    completed = motor.dungeon_instancia_concluida(instance_id)
    boss = "derrotado" if completed else "desperto" if any(is_boss(m) for m in mobs) else "adormecido"
    return jsonify(success=True, restantes=remaining,
                   total=len(MAP_SPAWNS.get("dungeon_01", [])), boss=boss)

# ============================================================
# 🗝️ ENTRADA EM DUNGEON
# ============================================================

@dungeon_events_bp.route(
    "/api/dungeon/entrada",
    methods=["POST"]
)
def dungeon_entry():
    try:

        data = (
            request.get_json(
                silent=True
            )
            or {}
        )


        user_id = data.get(
            "user_id"
        )

        dungeon_id = data.get(
            "dungeon_id"
        )


        # ====================================================
        # 🔎 VALIDAÇÃO BÁSICA
        # ====================================================

        if not user_id:

            return jsonify({
                "success": False,
                "autorizado": False,
                "error": "Jogador não informado."
            }), 400


        if not dungeon_id:

            return jsonify({
                "success": False,
                "autorizado": False,
                "error": "Dungeon não informada."
            }), 400


        # ====================================================
        # 🏰 CONTROLE DA EXECUÇÃO DA DUNGEON 01
        # ====================================================

        dungeon_id = str(
            dungeon_id
            or ""
        ).strip()

        user_id = str(
            user_id
            or ""
        )

        motor = (
            _motor_cacada()
        )

        group_id = None

        # ================================================
        # 👥 DESCOBRIR PARTY
        # ================================================
        if dungeon_id == "dungeon_01":

            from modules.combat.party_engine import (
                obter_grupo_do_jogador
            )

            grupo = (
                obter_grupo_do_jogador(
                    user_id
                )
            )

            if grupo:

                group_id = str(
                    grupo.get(
                        "_id"
                    )
                    or ""
                ).strip()

            if not motor:

                return jsonify({
                    "success": False,
                    "autorizado": False,
                    "error": (
                        "Sistema da dungeon "
                        "indisponível."
                    )
                }), 503

            # ============================================
            # 🔒 PARTICIPANTE DA EXECUÇÃO?
            # ============================================
            #
            # Se a party já começou a dungeon,
            # somente os membros congelados no início
            # podem participar daquela execução.
            # ============================================
            pode_participar = (
                motor.pode_participar_dungeon(
                    regiao=dungeon_id,
                    user_id=user_id,
                    group_id=group_id
                )
            )

            if not pode_participar:

                return jsonify({
                    "success": False,
                    "autorizado": False,
                    "acao": "fora_da_execucao",
                    "dungeon_id": dungeon_id,
                    "error": (
                        "Esta execução da dungeon "
                        "já começou. Você entrou na "
                        "party depois do início e "
                        "deverá aguardar a próxima run."
                    )
                }), 403

            # ============================================
            # 🔁 REENTRADA NA MESMA RUN
            # ============================================
            #
            # Já consumiu a chave desta execução:
            # não cobra novamente e, principalmente,
            # NÃO apaga os baús/puzzle pessoais.
            # ============================================
            ja_pagou = (
                motor.jogador_ja_pagou_dungeon(
                    regiao=dungeon_id,
                    user_id=user_id,
                    group_id=group_id
                )
            )

            if ja_pagou:

                return jsonify({
                    "success": True,
                    "autorizado": True,
                    "acao": "reentrada_execucao",
                    "dungeon_id": dungeon_id,
                    "item_id": "chave_masmorra",
                    "consumido": 0,
                    "mensagem": (
                        "Você retornou à execução "
                        "atual da dungeon. Nenhuma "
                        "Chave de Masmorra foi consumida."
                    )
                }), 200

        # ====================================================
        # 🗝️ NOVA ENTRADA — CONSUMIR CHAVE
        # ====================================================

        result = consumir_chave_masmorra(
            user_id=user_id,
            dungeon_id=dungeon_id,
        )


        # ====================================================
        # ✅ AUTORIZADO
        # ====================================================

        if result.get(
            "autorizado"
        ):

            # Dungeon 01 usa o sistema de instâncias.
            if (
                dungeon_id == "dungeon_01"
                and motor
            ):

                motor.registrar_pagamento_dungeon(
                    regiao=dungeon_id,
                    user_id=user_id,
                    group_id=group_id
                )

            return jsonify(
                result
            ), 200


        # ====================================================
        # 🔒 SEM CHAVE / NÃO AUTORIZADO
        # ====================================================

        return jsonify(
            result
        ), 403


    except DungeonEventError as exc:

        return jsonify({
            "success": False,
            "autorizado": False,
            "error": str(exc)
        }), 400


    except Exception:

        current_app.logger.exception(
            "Erro ao autorizar entrada na dungeon"
        )

        return jsonify({
            "success": False,
            "autorizado": False,
            "error": (
                "Erro interno ao tentar entrar "
                "na dungeon."
            )
        }), 500
    
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
