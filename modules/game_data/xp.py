# modules/game_data/xp.py
from __future__ import annotations
from typing import Dict, Optional, Tuple

from modules import player_manager

# ================================
# Configuração de Progressão
# ================================
MAX_LEVEL: int = 100

def _xp_formula(level: int) -> int:
    """
    XP necessário para passar do 'level' atual para o próximo.
    Fórmula suave e crescente. Ajuste se quiser a progressão mais rápida/lenta.
    """
    if level >= MAX_LEVEL:
        return 0
    # curva quadrática leve
    base = 100         # XP base para sair do nível 1
    lin  = 35 * (level - 1)
    quad = 10 * (level - 1) * (level - 1)
    return int(base + lin + quad)

def get_xp_for_next_combat_level(level: int) -> int:
    """Compat: usado pela UI para exibir o alvo do próximo nível."""
    try:
        level = int(level)
    except Exception:
        level = 1
    return max(0, _xp_formula(level))

# Quantos pontos de atributo (point_pool) cada nível concede
POINTS_PER_LEVEL: int = 2

# ================================
# Núcleo de Level Up
# ================================
def _apply_level_ups_inplace(player_data: dict) -> Dict[str, int]:
    """
    Verifica se o XP atual ultrapassa o necessário e aplica múltiplos level ups,
    concedendo pontos ao 'point_pool'. Retorna resumo.
    Espera que player_data contenha: 'level' (int) e 'xp' (int).
    """
    level_before = int(player_data.get("level", 1))
    xp_curr      = int(player_data.get("xp", 0))

    # loop de subida de níveis (suporta ganhar vários níveis de uma vez)
    levels_gained = 0
    while True:
        need = get_xp_for_next_combat_level(level_before + levels_gained)
        if need <= 0:
            # chegou ao nível máximo: zera XP de barra
            xp_curr = 0
            break
        if xp_curr < need:
            break
        # sobe 1 nível
        xp_curr -= need
        levels_gained += 1
        if (level_before + levels_gained) >= MAX_LEVEL:
            xp_curr = 0
            break

    if levels_gained > 0:
        new_level = level_before + levels_gained
        player_data["level"] = new_level
        player_data["xp"]    = xp_curr

        # migração suave para o novo sistema: garantir estruturas
        if "point_pool" not in player_data:
            try:
                player_data["point_pool"] = int(player_data.get("stat_points", 0) or 0)
            except Exception:
                player_data["point_pool"] = 0
        if "invested" not in player_data or not isinstance(player_data["invested"], dict):
            player_data["invested"] = {"hp": 0, "attack": 0, "defense": 0, "initiative": 0, "luck": 0}

        # drenar qualquer stat_points legado
        try:
            legacy = int(player_data.get("stat_points", 0) or 0)
        except Exception:
            legacy = 0
        if legacy > 0:
            player_data["point_pool"] = int(player_data["point_pool"]) + legacy
            player_data["stat_points"] = 0

        # conceder pontos pelo(s) níveis ganhos
        reward_points = levels_gained * POINTS_PER_LEVEL
        player_data["point_pool"] = int(player_data.get("point_pool", 0)) + reward_points

        return {
            "old_level": level_before,
            "new_level": new_level,
            "levels_gained": levels_gained,
            "points_awarded": reward_points,
            "current_xp": xp_curr,
            "next_level_xp": get_xp_for_next_combat_level(new_level),
        }

    # sem level up, apenas retorna estado atual
    curr_level = int(player_data.get("level", 1))
    player_data["xp"] = xp_curr
    return {
        "old_level": curr_level,
        "new_level": curr_level,
        "levels_gained": 0,
        "points_awarded": 0,
        "current_xp": xp_curr,
        "next_level_xp": get_xp_for_next_combat_level(curr_level),
    }

# ================================
# API Pública
# ================================
def add_combat_xp_inplace(player_data: dict, amount: int) -> Dict[str, int]:
    """
    Adiciona XP ao jogador em memória e processa level ups.
    Não salva em disco. Retorna resumo do resultado.
    """
    try:
        amount = int(amount)
    except Exception:
        amount = 0

    if amount <= 0:
        # não altera nada, só retorna o estado atual
        lvl = int(player_data.get("level", 1))
        return {
            "old_level": lvl,
            "new_level": lvl,
            "levels_gained": 0,
            "points_awarded": 0,
            "current_xp": int(player_data.get("xp", 0)),
            "next_level_xp": get_xp_for_next_combat_level(lvl),
        }

    # garante campos mínimos
    try:
        player_data["level"] = int(player_data.get("level", 1))
    except Exception:
        player_data["level"] = 1
    try:
        player_data["xp"] = int(player_data.get("xp", 0))
    except Exception:
        player_data["xp"] = 0

    # se já está no nível máximo, não acumula XP
    if int(player_data["level"]) >= MAX_LEVEL:
        player_data["xp"] = 0
        lvl = int(player_data["level"])
        return {
            "old_level": lvl,
            "new_level": lvl,
            "levels_gained": 0,
            "points_awarded": 0,
            "current_xp": 0,
            "next_level_xp": 0,
        }

    # adiciona e processa
    player_data["xp"] += amount
    return _apply_level_ups_inplace(player_data)

def add_combat_xp(user_id: int, amount: int) -> Dict[str, int]:
    """
    Carrega o jogador, adiciona XP, processa level ups e salva.
    Retorna um resumo do que aconteceu (níveis ganhos, pontos etc.).
    """
    pdata = player_manager.get_player_data(user_id)
    if not pdata:
        return {
            "old_level": 1,
            "new_level": 1,
            "levels_gained": 0,
            "points_awarded": 0,
            "current_xp": 0,
            "next_level_xp": get_xp_for_next_combat_level(1),
        }
    result = add_combat_xp_inplace(pdata, amount)
    player_manager.save_player_data(user_id, pdata)
    return result
