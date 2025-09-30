# modules/dungeons/runtime_api.py
from __future__ import annotations
from typing import Optional, Dict, Any

# estado simples em memória (troque por persistência se quiser)
_PENDING: dict[int, Dict[str, Any]] = {}

def set_pending_battle(user_id: int, dungeon_ctx: Dict[str, Any] | None) -> None:
    """Marca que o usuário está num andar aguardando resultado do combate."""
    if dungeon_ctx:
        _PENDING[user_id] = dict(dungeon_ctx)

def pop_pending(user_id: int) -> Optional[Dict[str, Any]]:
    """Consome e retorna o contexto pendente da dungeon desse usuário."""
    return _PENDING.pop(user_id, None)

# -------- integração com o motor do calabouço --------

async def resume_after_battle(context, user_id: int, victory: bool) -> None:
    """
    Chamado pelo combat_handler assim que a luta termina.
    Encaminha para o motor da dungeon retomar do andar atual.
    """
    from .engine import resume_dungeon_after_battle  # evite import circular
    dctx = pop_pending(user_id)
    await resume_dungeon_after_battle(context, user_id, dctx, victory)
