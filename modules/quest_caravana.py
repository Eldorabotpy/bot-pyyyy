"""Encontro pessoal da caravana na Pradaria Inicial."""

import math
import threading
import time

from bson import ObjectId

from modules.player.core import users_collection


QUEST_ID = "q3_varek_provacao"
REGIAO = "pradaria_inicial"
CARAVANA = {"x": 560, "y": 496}
MONSTER_ID = "goblin_batedor"
MOBS = (
    ("lado_oeste", 14 * 32, 15 * 32),
    ("lado_leste", 21 * 32, 15 * 32),
    ("trilha_sul", 17 * 32, 21 * 32),
)
AI_ROUTES = {
    1: ((480, 560), (520, 592)),
    2: ((640, 560), (600, 592)),
    3: ((560, 640),),
}
AI_VELOCIDADE = 38.0
AI_INTERVALO_ATAQUE = 3.2
CARAVANA_VIDA_MAXIMA = 300
DANO_CARAVANA_POR_ATAQUE = 1
IA_DURACAO_MAXIMA = 900
_IA_ATIVA = {}
_IA_LOCK = threading.RLock()


def preparar_encontro(player: dict, sistema_cacada) -> dict | None:
    """Cria mobs pessoais da missão e retorna os dados visuais da caravana."""
    player_id = str(player.get("_id") or "")
    quest = (player.get("quests") or {}).get(QUEST_ID) or {}
    if (
        not player_id
        or quest.get("status") not in ("ativa", "em_andamento")
        or sistema_cacada is None
    ):
        return None

    required = len(MOBS)
    vivos = sistema_cacada.mobs_vivos.setdefault(REGIAO, {})
    try:
        tentativa = max(1, int(quest.get("tentativa_evento", 1) or 1))
        integridade_salva = max(0, int(quest.get("caravana_integridade", CARAVANA_VIDA_MAXIMA)))
        vida_maxima_salva = max(1, int(quest.get("caravana_vida_maxima", 100) or 100))
        integridade = min(
            CARAVANA_VIDA_MAXIMA,
            round(integridade_salva * CARAVANA_VIDA_MAXIMA / vida_maxima_salva),
        )
    except (TypeError, ValueError):
        tentativa, integridade = 1, CARAVANA_VIDA_MAXIMA

    # A caravana destruída pode ser tentada novamente ao retornar à Pradaria.
    if integridade <= 0:
        for spawn_id, mob in list(vivos.items()):
            if mob.get("quest_event_id") == QUEST_ID and str(mob.get("event_owner_id")) == player_id:
                vivos.pop(spawn_id, None)
        tentativa += 1
        integridade = CARAVANA_VIDA_MAXIMA
        quest["abates_evento"] = 0
        quest["abates_evento_registrados"] = []
        quest["tentativa_evento"] = tentativa
        quest["caravana_integridade"] = integridade
        quest["caravana_vida_maxima"] = CARAVANA_VIDA_MAXIMA
        quest["event_spawn_ids"] = [
            f"q3_caravana_{player_id}_{tentativa}_{index}"
            for index in range(1, required + 1)
        ]
        users_collection.update_one(
            {"_id": player["_id"], f"quests.{QUEST_ID}.status": {"$in": ["ativa", "em_andamento"]}},
            {"$set": {
                f"quests.{QUEST_ID}.abates_evento": 0,
                f"quests.{QUEST_ID}.abates_evento_registrados": [],
                f"quests.{QUEST_ID}.tentativa_evento": tentativa,
                f"quests.{QUEST_ID}.caravana_integridade": integridade,
                f"quests.{QUEST_ID}.caravana_vida_maxima": CARAVANA_VIDA_MAXIMA,
                f"quests.{QUEST_ID}.event_spawn_ids": quest["event_spawn_ids"],
            }},
        )

    try:
        defeated = max(0, min(required, int(quest.get("abates_evento", 0) or 0)))
    except (TypeError, ValueError):
        defeated = 0

    spawn_ids = quest.get("event_spawn_ids") or [
        f"q3_caravana_{player_id}_{tentativa}_{index}"
        for index in range(1, required + 1)
    ]
    registered = quest.get("abates_evento_registrados")
    if not isinstance(registered, list):
        registered = []

    # Migra missões q3 que já estavam ativas antes da emboscada ser implementada.
    if (
        not quest.get("event_spawn_ids")
        or "abates_evento" not in quest
        or "caravana_integridade" not in quest
        or quest.get("caravana_vida_maxima") != CARAVANA_VIDA_MAXIMA
        or "tentativa_evento" not in quest
    ):
        users_collection.update_one(
            {"_id": player["_id"], f"quests.{QUEST_ID}.status": {"$in": ["ativa", "em_andamento"]}},
            {"$set": {
                f"quests.{QUEST_ID}.event_spawn_ids": spawn_ids,
                f"quests.{QUEST_ID}.abates_evento": defeated,
                f"quests.{QUEST_ID}.abates_evento_registrados": registered,
                f"quests.{QUEST_ID}.caravana_integridade": integridade,
                f"quests.{QUEST_ID}.caravana_vida_maxima": CARAVANA_VIDA_MAXIMA,
                f"quests.{QUEST_ID}.tentativa_evento": tentativa,
            }},
        )

    for index in range(defeated, required):
        spawn_id = spawn_ids[index]
        if spawn_id in vivos:
            continue

        config = {
            "spawn_id": spawn_id,
            "monster_id": MONSTER_ID,
            "x": MOBS[index][1],
            "y": MOBS[index][2],
            "respawn_segundos": 0,
        }
        mob = sistema_cacada.gerar_mob_dinamico(config, REGIAO)
        if not mob:
            continue

        # Os inimigos desta provação usam o nível-base do catálogo, sem rolagem
        # de elite/corrupção que possa tornar o encontro inicial imprevisível.
        base = sistema_cacada.buscar_status_base(MONSTER_ID) or {}
        nivel = int(base.get("min_level", 1) or 1)
        vida = max(1, int(base.get("hp", 1) or 1))
        mob.update({
            "level": nivel,
            "hp_max": vida,
            "max_hp": vida,
            "hp_atual": vida,
            "hp": vida,
            "attack": int(base.get("attack", 1) or 1),
            "defense": int(base.get("defense", 0) or 0),
            "initiative": int(base.get("initiative", 0) or 0),
            "luck": int(base.get("luck", 0) or 0),
            "xp_reward": int(base.get("xp_reward", 0) or 0),
            "gold_drop": int(base.get("gold_drop", 0) or 0),
            "elite": False,
            "is_elite": False,
            "elite_generated": False,
            "corrupted": False,
            "name": base.get("name", "Goblin Batedor"),
            "nome": base.get("name", "Goblin Batedor"),
        })
        mob.pop("corruption_event_id", None)

        mob.update({
            "event_owner_id": player_id,
            "quest_event_id": QUEST_ID,
            "quest_spawn_index": index + 1,
            "asset_region": "floresta",
            "respawn_segundos": 0,
            "ai_route": list(AI_ROUTES[index + 1]),
            "ai_route_index": 0,
            "ai_state": "avancando",
            "ai_attack_count": 0,
            "ai_last_attack": 0.0,
        })
        if not isinstance(mob.get("ai_route"), list):
            mob["ai_route"] = list(AI_ROUTES[index + 1])
            mob["ai_route_index"] = 0
        vivos[spawn_id] = mob

    return {
        "owner_id": player_id,
        "quest_id": QUEST_ID,
        "x": CARAVANA["x"],
        "y": CARAVANA["y"],
        "mob_atual": defeated,
        "mob_total": required,
        "vida_caravana": integridade,
        "vida_maxima": CARAVANA_VIDA_MAXIMA,
    }


def iniciar_ia_caravana(player_id, player_sid, sistema_cacada, socketio, jogador_no_mapa):
    """Executa a IA dos goblins apenas na instância pessoal da missão."""
    player_id = str(player_id or "")
    if not player_id or sistema_cacada is None or socketio is None:
        return False

    token = time.monotonic_ns()
    with _IA_LOCK:
        _IA_ATIVA[player_id] = token

    try:
        socketio.start_background_task(
            _executar_ia_caravana,
            player_id,
            player_sid,
            sistema_cacada,
            socketio,
            jogador_no_mapa,
            token,
        )
    except Exception:
        with _IA_LOCK:
            if _IA_ATIVA.get(player_id) == token:
                _IA_ATIVA.pop(player_id, None)
        raise
    return True


def _executar_ia_caravana(player_id, player_sid, sistema_cacada, socketio, jogador_no_mapa, token):
    """Move os goblins por rotas ao redor da carroça e os faz golpear o viajante."""
    ultimo_tick = time.monotonic()
    proxima_validacao = 0.0
    encerramento = ultimo_tick + IA_DURACAO_MAXIMA
    missao_ativa = True
    vida_caravana = CARAVANA_VIDA_MAXIMA

    try:
        while time.monotonic() < encerramento:
            with _IA_LOCK:
                if _IA_ATIVA.get(player_id) != token:
                    break
            agora = time.monotonic()
            delta = max(0.0, min(0.5, agora - ultimo_tick))
            ultimo_tick = agora

            if not jogador_no_mapa():
                break

            if agora >= proxima_validacao:
                player = users_collection.find_one(
                    {"_id": ObjectId(player_id)},
                    {f"quests.{QUEST_ID}.status": 1, f"quests.{QUEST_ID}.caravana_integridade": 1},
                ) or {}
                quest = (player.get("quests") or {}).get(QUEST_ID) or {}
                missao_ativa = quest.get("status") in ("ativa", "em_andamento")
                if not missao_ativa:
                    break
                vida_caravana = max(
                    0,
                    int(quest.get("caravana_integridade", CARAVANA_VIDA_MAXIMA) or 0),
                )
                if vida_caravana <= 0:
                    socketio.emit("caravanaIAAtualizada", {
                        "owner_id": player_id,
                        "quest_id": QUEST_ID,
                        "mobs": [],
                        "vida_caravana": 0,
                        "vida_maxima": CARAVANA_VIDA_MAXIMA,
                        "caravana_destruida": True,
                    }, to=player_sid)
                    break
                proxima_validacao = agora + 2

            vivos = sistema_cacada.mobs_vivos.get(REGIAO, {})
            mobs_evento = [
                (spawn_id, mob)
                for spawn_id, mob in list(vivos.items())
                if mob.get("quest_event_id") == QUEST_ID
                and str(mob.get("event_owner_id")) == player_id
            ]
            if not mobs_evento:
                break

            snapshot = []
            for spawn_id, mob in mobs_evento:
                rota = mob.get("ai_route") or list(AI_ROUTES.get(int(mob.get("quest_spawn_index", 1)), AI_ROUTES[1]))
                indice_rota = max(0, int(mob.get("ai_route_index", 0) or 0))
                pos_x = float(mob.get("x", 0) or 0)
                pos_y = float(mob.get("y", 0) or 0)
                atacando = indice_rota >= len(rota)

                if not atacando:
                    alvo_x, alvo_y = rota[indice_rota]
                    distancia = math.hypot(alvo_x - pos_x, alvo_y - pos_y)
                    if distancia <= 8:
                        indice_rota += 1
                        mob["ai_route_index"] = indice_rota
                        atacando = indice_rota >= len(rota)
                    elif delta > 0:
                        passo = min(AI_VELOCIDADE * delta, distancia)
                        pos_x += (alvo_x - pos_x) / distancia * passo
                        pos_y += (alvo_y - pos_y) / distancia * passo
                        mob["x"] = round(pos_x, 1)
                        mob["y"] = round(pos_y, 1)

                mob["ai_state"] = "atacando" if atacando else "avancando"
                atacou = False
                if atacando and agora - float(mob.get("ai_last_attack", 0) or 0) >= AI_INTERVALO_ATAQUE:
                    mob["ai_last_attack"] = agora
                    mob["ai_attack_count"] = int(mob.get("ai_attack_count", 0) or 0) + 1
                    atacou = True

                snapshot.append({
                    "spawn_id": str(spawn_id),
                    "x": round(float(mob.get("x", 0) or 0), 1),
                    "y": round(float(mob.get("y", 0) or 0), 1),
                    "estado": mob["ai_state"],
                    "ataque": atacou,
                    "sequencia_ataque": int(mob.get("ai_attack_count", 0) or 0),
                })

            dano = DANO_CARAVANA_POR_ATAQUE * sum(1 for item in snapshot if item["ataque"])
            if dano:
                users_collection.update_one(
                    {"_id": ObjectId(player_id), f"quests.{QUEST_ID}.status": {"$in": ["ativa", "em_andamento"]}},
                    {"$inc": {f"quests.{QUEST_ID}.caravana_integridade": -dano}},
                )
                vida_caravana = max(0, vida_caravana - dano)
            socketio.emit("caravanaIAAtualizada", {
                "owner_id": player_id,
                "quest_id": QUEST_ID,
                "mobs": snapshot,
                "vida_caravana": vida_caravana,
                "vida_maxima": CARAVANA_VIDA_MAXIMA,
                "caravana_destruida": vida_caravana <= 0,
            }, to=player_sid)
            if vida_caravana <= 0:
                break
            socketio.sleep(0.25)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Falha na IA da emboscada da caravana")
    finally:
        with _IA_LOCK:
            if _IA_ATIVA.get(player_id) == token:
                _IA_ATIVA.pop(player_id, None)


def registrar_abate(player_id: str, spawn_id: str, sistema_cacada) -> int | None:
    """Registra uma vitória validada pelo motor de combate, uma vez por mob."""
    try:
        oid = ObjectId(str(player_id))
    except Exception:
        return None

    resultado = users_collection.update_one(
        {
            "_id": oid,
            f"quests.{QUEST_ID}.status": {"$in": ["ativa", "em_andamento"]},
            f"quests.{QUEST_ID}.event_spawn_ids": str(spawn_id),
            f"quests.{QUEST_ID}.abates_evento_registrados": {"$ne": str(spawn_id)},
        },
        {
            "$inc": {f"quests.{QUEST_ID}.abates_evento": 1},
            "$addToSet": {f"quests.{QUEST_ID}.abates_evento_registrados": str(spawn_id)},
        },
    )
    if not resultado.modified_count:
        return None

    player = users_collection.find_one(
        {"_id": oid},
        {f"quests.{QUEST_ID}.abates_evento": 1, f"quests.{QUEST_ID}.caravana_integridade": 1},
    ) or {}
    quest = (player.get("quests") or {}).get(QUEST_ID) or {}
    abatidos = min(len(MOBS), int(quest.get("abates_evento", 0) or 0))
    integridade = max(0, int(quest.get("caravana_integridade", CARAVANA_VIDA_MAXIMA) or 0))

    if sistema_cacada is not None and getattr(sistema_cacada, "socketio", None):
        sistema_cacada.socketio.emit("caravanaQuestAtualizada", {
            "owner_id": str(player_id),
            "quest_id": QUEST_ID,
            "mob_atual": abatidos,
            "mob_total": len(MOBS),
            "concluido": abatidos >= len(MOBS) and integridade > 0,
            "vida_caravana": integridade,
            "vida_maxima": CARAVANA_VIDA_MAXIMA,
        })

    return abatidos
