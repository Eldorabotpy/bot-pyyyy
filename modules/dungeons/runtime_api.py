# modules/dungeons/runtime_api.py
from __future__ import annotations

from typing import Optional, Dict, Any, Union
import logging

from bson import ObjectId

logger = logging.getLogger(__name__)

PlayerId = Union[ObjectId, str]

# Armazenamento em memória dos estados pendentes
# Chave: string canônica de ObjectId
_PENDING: dict[str, Dict[str, Any]] = {}


def _pid_to_key(player_id: PlayerId) -> str:
    """
    Normaliza player_id para string canônica de ObjectId.
    Aceita ObjectId ou string válida de ObjectId.
    """
    if isinstance(player_id, ObjectId):
        return str(player_id)
    if isinstance(player_id, str) and ObjectId.is_valid(player_id.strip()):
        return str(ObjectId(player_id.strip()))
    raise ValueError("player_id inválido (esperado ObjectId ou string de ObjectId).")


def set_pending_battle(player_id: PlayerId, dungeon_ctx: Dict[str, Any] | None) -> None:
    """
    Registra que o jogador está em um andar de dungeon.
    """
    try:
        key = _pid_to_key(player_id)
    except Exception:
        # Se não for um ObjectId válido, não grava (evita poluir cache)
        return

    if dungeon_ctx:
        # Cria uma cópia para evitar modificação acidental
        _PENDING[key] = dict(dungeon_ctx)
    else:
        # Se passar None, remove o registro
        _PENDING.pop(key, None)


def pop_pending(player_id: PlayerId) -> Optional[Dict[str, Any]]:
    """
    Recupera e remove o contexto pendente.
    """
    try:
        key = _pid_to_key(player_id)
    except Exception:
        return None
    return _PENDING.pop(key, None)


def get_pending(player_id: PlayerId) -> Optional[Dict[str, Any]]:
    """
    Apenas lê o contexto sem remover (útil para verificações).
    """
    try:
        key = _pid_to_key(player_id)
    except Exception:
        return None
    return _PENDING.get(key)


# =========================================================
# Integração com o Runtime (Avanço de Fase)
# =========================================================
async def resume_after_battle(context, player_id: PlayerId, victory: bool) -> None:
    """
    Ponte segura para chamar o runtime.py sem causar erro de importação circular.
    """
    try:
        # Importação tardia (dentro da função) é CRUCIAL aqui
        from modules.dungeons import runtime

        # Tenta pegar da memória
        dctx = pop_pending(player_id)

        # Se não estiver na memória, o runtime.py tem um backup de segurança
        # que lê do banco de dados, então podemos passar None se necessário.
        await runtime.resume_dungeon_after_battle(context, player_id, dctx, victory)

    except ImportError:
        logger.error("ERRO CRÍTICO: Não foi possível importar modules.dungeons.runtime")
    except Exception as e:
        logger.error(f"Erro ao retomar dungeon: {e}", exc_info=True)
