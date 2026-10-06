"""Premiações idempotentes do evento e das temporadas do Coliseu."""
from datetime import datetime, timedelta, timezone
import logging
from threading import RLock

from bson import ObjectId
from modules.player.core import clear_all_player_cache

from .coliseum_event import BRASILIA, get_ended_event_ids

logger = logging.getLogger(__name__)
UTC = timezone.utc
SEASON_DAYS = 35
SEASON_REWARDS = {1: 50, 2: 20, 3: 5}
EVENT_WINNER_REWARD = 10
_SEASON_LOCK = RLock()
_FINALIZED_EVENT_CACHE = set()


def _utc_now(value=None):
    value = value or datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def season_is_expired(season, now=None):
    return bool(season and season.get("fim") and _utc_now(season["fim"]) <= _utc_now(now))


def isoformat_utc(value):
    return _utc_now(value).isoformat().replace("+00:00", "Z") if value else None


def _create_first_season(users_collection, now):
    seasons = users_collection.database["coliseu_pvp_temporadas"]
    season = seasons.find_one({"_id": "atual"})
    if season:
        return season

    candidate = {
        "_id": "atual",
        "numero": 1,
        "status": "ativa",
        "inicio": now,
        "fim": now + timedelta(days=SEASON_DAYS),
    }
    result = seasons.update_one({"_id": "atual"}, {"$setOnInsert": candidate}, upsert=True)
    season = seasons.find_one({"_id": "atual"}) or candidate
    if result.upserted_id:
        # O primeiro ciclo começa com a mesma linha de largada para todos.
        users_collection.update_many({}, {"$set": {
            "pvp_points": 0,
            "pvp_season_number": 1,
            "pvp_season_matches": 0,
            "pvp_season_wins": 0,
            "pvp_season_losses": 0,
        }})
        clear_all_player_cache()
        logger.info("Temporada inicial do Coliseu criada por 35 dias; Elo inicial Bronze (0).")
    return season


def _premiar_jogador(users_collection, jogador, chave_premio, quantidade, origem):
    jogador_id = jogador.get("_id")
    if not isinstance(jogador_id, ObjectId):
        return False
    resultado = users_collection.update_one(
        {"_id": jogador_id, "coliseu_premios_recebidos": {"$ne": chave_premio}},
        {"$inc": {"gems": int(quantidade)}, "$addToSet": {"coliseu_premios_recebidos": chave_premio}},
    )
    if resultado.modified_count == 1:
        clear_all_player_cache()
    users_collection.database["coliseu_pvp_premios"].update_one(
        {"_id": chave_premio},
        {"$setOnInsert": {
            "char_id": str(jogador_id),
            "nome": jogador.get("character_name", "Aventureiro"),
            "gemas": int(quantidade),
            "origem": origem,
            "criado_em": datetime.now(UTC),
        }},
        upsert=True,
    )
    return resultado.modified_count == 1


def _fechar_temporada(users_collection, season, now):
    numero = int(season.get("numero", 1))
    temporadas = users_collection.database["coliseu_pvp_temporadas"]
    arquivo = users_collection.database["coliseu_pvp_historico"]
    registro = arquivo.find_one({"_id": numero})

    if not registro or registro.get("status") != "finalizada":
        jogadores = list(users_collection.find(
            {
                "pvp_season_number": numero,
                "pvp_season_matches": {"$gt": 0},
                "character_name": {"$exists": True, "$ne": ""},
            },
            {"character_name": 1, "pvp_points": 1, "pvp_season_wins": 1, "pvp_season_losses": 1},
        ).sort([
            ("pvp_points", -1),
            ("pvp_season_wins", -1),
            ("pvp_season_losses", 1),
            ("character_name", 1),
        ]).limit(3))

        vencedores = []
        for posicao, jogador in enumerate(jogadores, 1):
            gemas = SEASON_REWARDS[posicao]
            chave = f"coliseu-temporada:{numero}:lugar:{posicao}"
            _premiar_jogador(users_collection, jogador, chave, gemas, "temporada")
            vencedores.append({
                "posicao": posicao,
                "char_id": str(jogador["_id"]),
                "nome": jogador.get("character_name", "Aventureiro"),
                "pontos": int(jogador.get("pvp_points", 0) or 0),
                "vitorias": int(jogador.get("pvp_season_wins", 0) or 0),
                "derrotas": int(jogador.get("pvp_season_losses", 0) or 0),
                "gemas": gemas,
            })

        arquivo.update_one(
            {"_id": numero},
            {"$setOnInsert": {
                "numero": numero,
                "inicio": season.get("inicio"),
                "fim": season.get("fim"),
                "finalizada_em": now,
                "status": "finalizada",
                "vencedores": vencedores,
            }},
            upsert=True,
        )

    proxima = numero + 1
    users_collection.update_many({}, {"$set": {
        "pvp_points": 0,
        "pvp_season_number": proxima,
        "pvp_season_matches": 0,
        "pvp_season_wins": 0,
        "pvp_season_losses": 0,
    }})
    clear_all_player_cache()
    temporada_nova = {"numero": proxima, "inicio": now, "fim": now + timedelta(days=SEASON_DAYS), "status": "ativa"}
    temporadas.update_one({"_id": "atual"}, {"$set": temporada_nova}, upsert=True)
    logger.info("Temporada %s encerrada; temporada %s aberta por 35 dias.", numero, proxima)
    return {"_id": "atual", **temporada_nova}


def ensure_active_season(users_collection, duelos_ativos=None, now=None):
    """Cria a temporada inicial ou paga/renova a atual ao completar 35 dias."""
    if users_collection is None:
        return None
    now = _utc_now(now)
    with _SEASON_LOCK:
        season = _create_first_season(users_collection, now)
        fim = _utc_now(season.get("fim"))
        if fim <= now:
            numero = int(season.get("numero", 1))
            if any(
                duelo.get("modo") == "ranqueado" and duelo.get("season_number") == numero
                for duelo in list((duelos_ativos or {}).values())
            ):
                return {**season, "status": "encerrando"}
            seasons = users_collection.database["coliseu_pvp_temporadas"]
            if season.get("status") == "ativa":
                seasons.update_one(
                    {"_id": "atual", "numero": season.get("numero"), "status": "ativa"},
                    {"$set": {"status": "encerrando"}},
                )
                season = seasons.find_one({"_id": "atual"}) or season
            if season.get("status") == "encerrando":
                season = _fechar_temporada(users_collection, season, now)
        return season


def finalizar_eventos_encerrados(users_collection, duelos_ativos, now=None):
    """Fecha os placares após a janela e paga 10 gemas ao vencedor uma única vez."""
    if users_collection is None:
        return
    agora = _utc_now(now)
    placares = users_collection.database["coliseu_evento_pvp"]
    historico = users_collection.database["coliseu_pvp_eventos"]

    for event_id in get_ended_event_ids(now=agora.astimezone(BRASILIA)):
        if event_id in _FINALIZED_EVENT_CACHE:
            continue
        if historico.find_one({"_id": event_id, "status": "finalizado"}):
            _FINALIZED_EVENT_CACHE.add(event_id)
            continue
        if any(duelo.get("modo") == "evento" and duelo.get("event_id") == event_id for duelo in list(duelos_ativos.values())):
            continue

        participantes = list(placares.find({"event_id": event_id}))
        participantes.sort(key=lambda item: (
            -int(item.get("vitorias", 0) or 0),
            -(int(item.get("vitorias", 0) or 0) / max(1, int(item.get("partidas", 0) or 0))),
            int(item.get("derrotas", 0) or 0),
            str(item.get("nome", "")).casefold(),
            str(item.get("char_id", "")),
        ))
        vencedor = None
        if participantes and int(participantes[0].get("vitorias", 0) or 0) > 0:
            char_id = str(participantes[0].get("char_id", ""))
            if ObjectId.is_valid(char_id):
                vencedor = users_collection.find_one({"_id": ObjectId(char_id)})
                if vencedor:
                    _premiar_jogador(users_collection, vencedor, f"coliseu-evento:{event_id}:vencedor", EVENT_WINNER_REWARD, "evento")

        placar_final = [
            {"char_id": str(item.get("char_id", "")), "nome": item.get("nome", "Aventureiro"),
             "vitorias": int(item.get("vitorias", 0) or 0), "partidas": int(item.get("partidas", 0) or 0),
             "derrotas": int(item.get("derrotas", 0) or 0)}
            for item in participantes[:5]
        ]
        historico.update_one(
            {"_id": event_id},
            {"$setOnInsert": {
                "event_id": event_id,
                "status": "finalizado",
                "finalizado_em": agora,
                "vencedor_char_id": str(vencedor["_id"]) if vencedor else None,
                "vencedor_nome": vencedor.get("character_name") if vencedor else None,
                "recompensa_gemas": EVENT_WINNER_REWARD if vencedor else 0,
                "placar": placar_final,
            }},
            upsert=True,
        )
        _FINALIZED_EVENT_CACHE.add(event_id)
        logger.info("Evento do Coliseu %s finalizado; vencedor=%s", event_id, vencedor.get("character_name") if vencedor else "sem vencedor")
