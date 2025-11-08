# modules/dungeons/config.py (Versão Corrigida)

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List

@dataclass(frozen=True)
class Difficulty:
    key: str
    label: str
    emoji: str
    gold_mult: float
    stat_mult: float
    key_cost: int

# ✅ 3 dificuldades com a nova progressão
DIFFICULTIES: Dict[str, Difficulty] = {
    "iniciante":  Difficulty("iniciante",  "Iniciante", "☠️", 1.00, 1.00, 1),
    "infernal":   Difficulty("infernal",   "Infernal",  "👺", 3.80, 2.50, 1), 
    "pesadelo":   Difficulty("pesadelo",   "Pesadelo",  "👹", 5.90, 4.40, 1),
}

# ✅ Ordem corrigida
DEFAULT_DIFFICULTY_ORDER = ("iniciante", "infernal", "pesadelo")

# O resto do ficheiro permanece igual
ENTRY_KEY_ITEM_ID = "cristal_de_abertura"
EVOLUTION_ITEM_POOL: List[str] = [
    "evo_fragmento_guerreiro",
    "evo_fragmento_mago",
    "evo_fragmento_bardo",
    "evo_fragmento_monge",
    "evo_fragmento_assassino",
    "evo_fragmento_samurai",
]