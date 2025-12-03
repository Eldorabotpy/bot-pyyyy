# modules/dungeons/runtime_api.py
from __future__ import annotations
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Armazenamento em memória dos estados pendentes
# (Garante que o bot saiba onde você está entre um clique e outro)
_PENDING: dict[int, Dict[str, Any]] = {}

def set_pending_battle(user_id: int, dungeon_ctx: Dict[str, Any] | None) -> None:
    """
    Registra que o usuário está em um andar de dungeon.
    """
    if dungeon_ctx:
        # Cria uma cópia para evitar modificação acidental
        _PENDING[user_id] = dict(dungeon_ctx)
    else:
        # Se passar None, remove o registro
        _PENDING.pop(user_id, None)

def pop_pending(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Recupera e remove o contexto pendente.
    """
    return _PENDING.pop(user_id, None)

def get_pending(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Apenas lê o contexto sem remover (útil para verificações).
    """
    return _PENDING.get(user_id)

# =========================================================
# Integração com o Runtime (Avanço de Fase)
# =========================================================
async def resume_after_battle(context, user_id: int, victory: bool) -> None:
    """
    Ponte segura para chamar o runtime.py sem causar erro de importação circular.
    """
    try:
        # Importação tardia (dentro da função) é CRUCIAL aqui
        from modules.dungeons import runtime
        
        # Tenta pegar da memória
        dctx = pop_pending(user_id)
        
        # Se não estiver na memória, o runtime.py tem um backup de segurança
        # que lê do banco de dados, então podemos passar None se necessário.
        
        await runtime.resume_dungeon_after_battle(context, user_id, dctx, victory)
        
    except ImportError:
        logger.error("ERRO CRÍTICO: Não foi possível importar modules.dungeons.runtime")
    except Exception as e:
        logger.error(f"Erro ao retomar dungeon para user {user_id}: {e}", exc_info=True)