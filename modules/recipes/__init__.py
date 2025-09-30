# modules/recipes/__init__.py
from __future__ import annotations
from typing import Dict, Any
import logging

from modules.crafting_registry import register_recipe

log = logging.getLogger(__name__)

# ============================================================
# Imports protegidos por try/except para cada classe e tier
# ============================================================

# --------- GUERREIRO ---------
try:
    from .guerreiro_t1 import RECIPES as GUERREIRO_T1
except Exception:
    GUERREIRO_T1: Dict[str, Dict[str, Any]] = {}
    log.debug("Pacote recipes: guerreiro_t1 ausente")

try:
    from .guerreiro_t2 import RECIPES as GUERREIRO_T2
except Exception:
    GUERREIRO_T2: Dict[str, Dict[str, Any]] = {}
    log.debug("Pacote recipes: guerreiro_t2 ausente")

# --------- MAGO ---------
try:
    from .mago_t1 import RECIPES as MAGO_T1
except Exception:
    MAGO_T1: Dict[str, Dict[str, Any]] = {}
    log.debug("Pacote recipes: mago_t1 ausente")

try:
    from .mago_t2 import RECIPES as MAGO_T2
except Exception:
    MAGO_T2: Dict[str, Dict[str, Any]] = {}
    log.debug("Pacote recipes: mago_t2 ausente")

# --------- BERSERKER ---------
try:
    from .berserker_t1 import RECIPES as BERSERKER_T1
except Exception:
    BERSERKER_T1: Dict[str, Dict[str, Any]] = {}
    log.debug("Pacote recipes: berserker_t1 ausente")

try:
    from .berserker_t2 import RECIPES as BERSERKER_T2
except Exception:
    BERSERKER_T2: Dict[str, Dict[str, Any]] = {}
    log.debug("Pacote recipes: berserker_t2 ausente")

# --------- CAÇADOR ---------
try:
    from .cacador_t1 import RECIPES as CACADOR_T1
except Exception:
    CACADOR_T1: Dict[str, Dict[str, Any]] = {}
    log.debug("Pacote recipes: cacador_t1 ausente")

try:
    from .cacador_t2 import RECIPES as CACADOR_T2
except Exception:
    CACADOR_T2: Dict[str, Dict[str, Any]] = {}
    log.debug("Pacote recipes: cacador_t2 ausente")

# --------- ASSASSINO ---------
try:
    from .assassino_t1 import RECIPES as ASSASSINO_T1
except Exception:
    ASSASSINO_T1: Dict[str, Dict[str, Any]] = {}
    log.debug("Pacote recipes: assassino_t1 ausente")

try:
    from .assassino_t2 import RECIPES as ASSASSINO_T2
except Exception:
    ASSASSINO_T2: Dict[str, Dict[str, Any]] = {}
    log.debug("Pacote recipes: assassino_t2 ausente")

# --------- BARDO ---------
try:
    from .bardo_t1 import RECIPES as BARDO_T1
except Exception:
    BARDO_T1: Dict[str, Dict[str, Any]] = {}
    log.debug("Pacote recipes: bardo_t1 ausente")

try:
    from .bardo_t2 import RECIPES as BARDO_T2
except Exception:
    BARDO_T2: Dict[str, Dict[str, Any]] = {}
    log.debug("Pacote recipes: bardo_t2 ausente")

# --------- MONGE ---------
try:
    from .monge_t1 import RECIPES as MONGE_T1
except Exception:
    MONGE_T1: Dict[str, Dict[str, Any]] = {}
    log.debug("Pacote recipes: monge_t1 ausente")

try:
    from .monge_t2 import RECIPES as MONGE_T2
except Exception:
    MONGE_T2: Dict[str, Dict[str, Any]] = {}
    log.debug("Pacote recipes: monge_t2 ausente")

# --------- SAMURAI ---------
try:
    from .samurai_t1 import RECIPES as SAMURAI_T1
except Exception:
    SAMURAI_T1: Dict[str, Dict[str, Any]] = {}
    log.debug("Pacote recipes: samurai_t1 ausente")

try:
    from .samurai_t2 import RECIPES as SAMURAI_T2
except Exception:
    SAMURAI_T2: Dict[str, Dict[str, Any]] = {}
    log.debug("Pacote recipes: samurai_t2 ausente")

# ============================================================
# Lista de grupos (ordem por classe e tier)
# ============================================================
_GROUPS: list[Dict[str, Dict[str, Any]]] = [
    GUERREIRO_T1, GUERREIRO_T2,
    MAGO_T1, MAGO_T2,
    BERSERKER_T1, BERSERKER_T2,
    CACADOR_T1, CACADOR_T2,
    ASSASSINO_T1, ASSASSINO_T2,
    BARDO_T1, BARDO_T2,
    MONGE_T1, MONGE_T2,
    SAMURAI_T1, SAMURAI_T2,
]

def register_all() -> int:
    """
    Registra todas as receitas carregadas dos submódulos.
    Retorna a quantidade registrada.
    """
    count = 0
    for group in _GROUPS:
        for rid, data in group.items():
            try:
                register_recipe(rid, data)
                count += 1
            except Exception as e:
                log.exception("[RECIPES] Erro registrando %s: %s", rid, e)
    log.info("[RECIPES] %d receitas registradas pelos pacotes.", count)
    return count
