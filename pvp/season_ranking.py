"""Montagem do placar e da distribuição de elos da temporada ativa."""

from .pvp_config import ELO_THRESHOLDS, ELO_TIER_META
from .pvp_utils import get_player_elo

DIVISION_ROMANS = ("I", "II", "III", "IV", "V")
MASTER_DIVISION_STEP = 1000
ELO_DIVISION_ICON_BASE = "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/patente"


def _safe_int(value, default=0):
    try:
        return int(float(value if value is not None else default))
    except (TypeError, ValueError, OverflowError):
        return int(default)


def current_season_points(player, season_number):
    """Return zero for players whose stored Elo belongs to an older season."""
    if _safe_int((player or {}).get("pvp_season_number"), 0) != _safe_int(season_number, 0):
        return 0
    return max(0, _safe_int((player or {}).get("pvp_points"), 0))


def _standing_order(player):
    return (
        -max(0, _safe_int(player.get("pontos"), 0)),
        -max(0, _safe_int(player.get("vitorias"), 0)),
        max(0, _safe_int(player.get("derrotas"), 0)),
        str(player.get("nome") or "Herói").casefold(),
    )


def find_player_season_position(players, player_id):
    """Return one player's place and participant count using the standings order."""
    if player_id is None:
        return None
    ordered = sorted(players, key=_standing_order)
    for position, player in enumerate(ordered, 1):
        if str(player.get("id") or "") == str(player_id):
            return {
                "posicao_temporada": position,
                "participantes_temporada": len(ordered),
            }
    return None


def _build_divisions(tier, next_minimum):
    minimum = tier["minimo"]
    if next_minimum is None:
        step = MASTER_DIVISION_STEP
    else:
        step = (next_minimum - minimum) // len(DIVISION_ROMANS)

    divisions = []
    for index, roman in enumerate(DIVISION_ROMANS):
        division_minimum = minimum + index * step
        if next_minimum is None:
            division_maximum = None if index == len(DIVISION_ROMANS) - 1 else division_minimum + step - 1
        else:
            division_maximum = division_minimum + step - 1
        divisions.append({
            "numero": index + 1,
            "romano": roman,
            "nome": f"{tier['nome']} {roman}",
            "icone": f"{ELO_DIVISION_ICON_BASE}/{tier['nome'].replace(' ', '_')}_{roman}.png",
            "minimo": division_minimum,
            "maximo": division_maximum,
            "quantidade": 0,
            "jogadores": [],
        })
    return divisions, step


def build_elo_standings(players, ranking_limit=5):
    """Agrupa participantes por elo e patente, e retorna o Top 5 da temporada."""
    thresholds = sorted(ELO_THRESHOLDS.items(), key=lambda item: item[1])
    tiers = []
    tiers_by_key = {}
    division_steps = {}

    for index, (key, minimum) in enumerate(thresholds):
        next_minimum = thresholds[index + 1][1] if index + 1 < len(thresholds) else None
        tier = {
            **ELO_TIER_META[key],
            "minimo": int(minimum),
            "maximo": int(next_minimum - 1) if next_minimum is not None else None,
            "quantidade": 0,
            "jogadores": [],
        }
        tier["divisoes"], division_steps[key] = _build_divisions(tier, next_minimum)
        tiers.append(tier)
        tiers_by_key[key] = tier

    entries = []
    for player in players:
        points = max(0, _safe_int(player.get("pontos"), 0))
        key = get_player_elo(points)
        meta = ELO_TIER_META[key]
        tier = tiers_by_key[key]
        division_index = min(
            len(DIVISION_ROMANS) - 1,
            (points - tier["minimo"]) // division_steps[key],
        )
        division = tier["divisoes"][division_index]
        entry = {
            "nome": str(player.get("nome") or "Herói"),
            "nivel": max(1, _safe_int(player.get("nivel"), 1)),
            "pontos": points,
            "vitorias": max(0, _safe_int(player.get("vitorias"), 0)),
            "derrotas": max(0, _safe_int(player.get("derrotas"), 0)),
            "elo": meta["nome"],
            "elo_id": meta["id"],
            "icone": division["icone"],
            "icone_elo": meta["icone"],
            "divisao": division["romano"],
            "divisao_nome": division["nome"],
            "elo_completo": division["nome"],
        }
        tier["jogadores"].append(entry)
        tier["quantidade"] += 1
        division["jogadores"].append(entry)
        division["quantidade"] += 1
        entries.append(entry)

    entries.sort(key=_standing_order)
    for tier in tiers:
        tier["jogadores"].sort(key=_standing_order)
        for division in tier["divisoes"]:
            division["jogadores"].sort(key=_standing_order)

    ranking = [
        {"posicao": position, **entry}
        for position, entry in enumerate(entries[:max(1, _safe_int(ranking_limit, 5))], 1)
    ]
    return tiers, ranking, len(entries)


def build_player_season_rank(player):
    """Return a single player's current division and progress to the next one."""
    tiers, _, _ = build_elo_standings([player])
    current = next(
        division
        for tier in tiers
        for division in tier["divisoes"]
        if division["quantidade"]
    )
    divisions = [division for tier in tiers for division in tier["divisoes"]]
    current_index = divisions.index(current)
    next_division = divisions[current_index + 1] if current_index + 1 < len(divisions) else None
    points = current["jogadores"][0]["pontos"]

    result = {
        **current["jogadores"][0],
        "minimo": current["minimo"],
        "maximo": current["maximo"],
        "proxima_divisao": next_division["nome"] if next_division else None,
        "icone_proxima_divisao": next_division["icone"] if next_division else None,
        "pontos_para_proxima": max(0, next_division["minimo"] - points) if next_division else 0,
        "progresso_percentual": (
            int((points - current["minimo"]) * 100 / (next_division["minimo"] - current["minimo"]))
            if next_division else None
        ),
    }
    return result
