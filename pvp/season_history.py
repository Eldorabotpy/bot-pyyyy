"""Transforma partidas ranqueadas do Coliseu no histórico de um personagem."""


def _safe_int(value, default=0):
    try:
        return int(float(value if value is not None else default))
    except (TypeError, ValueError, OverflowError):
        return int(default)


def build_player_match_history(player_id, matches, limit=10):
    """Return recent ranked matches from one player's point of view."""
    player_id = str(player_id)
    limit = max(0, _safe_int(limit, 10))
    if not player_id or not limit:
        return []

    history = []
    for match in matches:
        player_ids = [str(value) for value in (match.get("jogadores") or [])]
        if player_id not in player_ids:
            continue
        player_index = player_ids.index(player_id)
        opponent_index = next((index for index in range(len(player_ids)) if index != player_index), None)
        if opponent_index is None:
            continue

        names = match.get("nomes") or []
        changes = match.get("alteracoes") or []
        player_change = changes[player_index] if player_index < len(changes) and isinstance(changes[player_index], dict) else {}
        winner_id = str(match.get("vencedor") or "")
        opponent_name = names[opponent_index] if opponent_index < len(names) else None
        history.append({
            "vitoria": winner_id == player_id,
            "adversario": str(opponent_name or "Aventureiro"),
            "variacao": _safe_int(player_change.get("delta"), 0),
            "pontos": _safe_int(player_change.get("pontos"), 0),
            "temporada": _safe_int(match.get("temporada"), 0),
            "data": match.get("criado_em"),
        })
        if len(history) >= max(0, int(limit)):
            break
    return history
