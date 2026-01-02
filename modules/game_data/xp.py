# modules/game_data/xp.py
# (VERSÃO FINAL: Lógica Completa + Suporte a Premium/VIP)

from __future__ import annotations
from typing import Dict, Optional, Tuple, Union
import logging

from modules import player_manager

# ✅ Tenta importar PremiumManager (dentro de try/except para evitar erro de import circular)
try:
    from modules.player.premium import PremiumManager
except ImportError:
    PremiumManager = None

logger = logging.getLogger(__name__)

# ================================
# Configuração de Progressão
# ================================
MAX_LEVEL: int = 100
POINTS_PER_LEVEL: int = 1

def _xp_formula(level: int) -> int:
    """
    XP necessário para passar do 'level' atual para o próximo.
    """
    if level >= MAX_LEVEL:
        return 0
    
    # Cálculo Base (Curva Quadrática)
    base = 200
    lin  = 100 * (level - 1)
    quad = 40 * (level - 1) * (level - 1)
    
    raw_xp = int(base + lin + quad)

    # Multiplicadores de Dificuldade (O "Muro")
    multiplier = 1.0
    if level < 20:
        multiplier = 1.0
    elif 20 <= level < 50:
        multiplier = 1.5
    elif 50 <= level < 80:
        multiplier = 2.5
    elif level >= 80:
        multiplier = 4.0

    return int(raw_xp * multiplier)

def get_xp_for_next_combat_level(level: int) -> int:
    """Retorna o XP necessário para o próximo nível."""
    try:
        level = int(level)
    except Exception:
        level = 1
    level = max(1, level)
    return max(0, _xp_formula(level))

# ================================
# Núcleo de Level Up (Lógica Interna)
# ================================
def _apply_level_ups_inplace(player_data: dict) -> Dict[str, int]:
    """
    Verifica e aplica level ups em player_data (in-place).
    Retorna resumo do que aconteceu.
    """
    if not isinstance(player_data, dict):
        player_data = {"level": 1, "xp": 0}

    level_before = int(player_data.get("level", 1) or 1)
    xp_curr      = int(player_data.get("xp", 0) or 0)

    levels_gained = 0
    while True:
        need = get_xp_for_next_combat_level(level_before + levels_gained)
        if need <= 0:
            xp_curr = 0
            break
        if xp_curr < need:
            break
        xp_curr -= need
        levels_gained += 1
        if (level_before + levels_gained) >= MAX_LEVEL:
            xp_curr = 0
            break

    if levels_gained > 0:
        new_level = level_before + levels_gained
        player_data["level"] = new_level
        player_data["xp"]    = xp_curr

        # Garante estrutura de pontos
        if "point_pool" not in player_data:
            try: player_data["point_pool"] = int(player_data.get("stat_points", 0) or 0)
            except: player_data["point_pool"] = 0

        # Pontos legados
        try: legacy = int(player_data.get("stat_points", 0) or 0)
        except: legacy = 0
        
        if legacy > 0:
            player_data["point_pool"] = int(player_data.get("point_pool", 0)) + legacy
            player_data["stat_points"] = 0

        # Entrega recompensas
        reward_points = levels_gained * POINTS_PER_LEVEL
        player_data["point_pool"] = int(player_data.get("point_pool", 0)) + reward_points

        # Restaura HP/MP/Energia ao upar (Bônus clássico de RPG)
        try:
            from modules.player.actions import get_player_max_energy
            stats = player_manager.get_player_total_stats(player_data)
            # Como get_player_total_stats é async, aqui dentro de func sincrona 
            # não conseguimos chamar fácil, então ignoramos o HP/MP full heal 
            # ou fazemos só o básico seguro:
            player_data["energy"] = get_player_max_energy(player_data)
        except: pass

        return {
            "old_level": level_before,
            "new_level": new_level,
            "levels_gained": levels_gained,
            "points_awarded": reward_points,
            "current_xp": xp_curr,
            "next_level_xp": get_xp_for_next_combat_level(new_level),
        }

    # Se não upou
    curr_level = int(player_data.get("level", 1) or 1)
    player_data["xp"] = xp_curr
    return {
        "old_level": curr_level,
        "new_level": curr_level,
        "levels_gained": 0,
        "points_awarded": 0,
        "current_xp": xp_curr,
        "next_level_xp": get_xp_for_next_combat_level(curr_level),
    }

def add_combat_xp_inplace(player_data: dict, amount: int) -> Dict[str, int]:
    """
    Função síncrona que adiciona o valor ao dicionário e calcula levels.
    NÃO SALVA NO BANCO (quem chama deve salvar).
    """
    if not isinstance(player_data, dict):
        player_data = {"level": 1, "xp": 0}

    try: amount = int(amount)
    except: amount = 0

    if amount <= 0:
        lvl = int(player_data.get("level", 1) or 1)
        return {
            "old_level": lvl, "new_level": lvl, "levels_gained": 0,
            "points_awarded": 0, "current_xp": int(player_data.get("xp", 0) or 0),
            "next_level_xp": get_xp_for_next_combat_level(lvl),
        }

    # Inicializa campos se não existirem
    if "level" not in player_data: player_data["level"] = 1
    if "xp" not in player_data: player_data["xp"] = 0

    if int(player_data["level"]) >= MAX_LEVEL:
        player_data["xp"] = 0
        lvl = int(player_data["level"])
        return {
            "old_level": lvl, "new_level": lvl, "levels_gained": 0,
            "points_awarded": 0, "current_xp": 0, "next_level_xp": 0,
        }

    player_data["xp"] = int(player_data["xp"]) + amount
    return _apply_level_ups_inplace(player_data)

# ================================
# API Pública (Async + Premium Check)
# ================================

async def add_combat_xp(user_id: str, amount: int) -> Dict[str, int]:
    """
    Adiciona XP de combate e salva no banco.
    APLICA MULTIPLICADOR PREMIUM AUTOMATICAMENTE.
    """
    # Garante string para o player_manager
    user_id = str(user_id)
    
    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        return {
            "old_level": 1, "new_level": 1, "levels_gained": 0,
            "points_awarded": 0, "current_xp": 0, "next_level_xp": 100,
        }
    
    # ✅ Lógica de Multiplicador VIP
    final_amount = amount
    try:
        if PremiumManager:
            pm = PremiumManager(pdata)
            mult = float(pm.get_perk_value("xp_multiplier", 1.0))
            
            if mult > 1.0:
                final_amount = int(amount * mult)
    except Exception as e:
        logger.error(f"Erro ao aplicar XP Premium para {user_id}: {e}")

    # Usa a função inplace definida acima
    result = add_combat_xp_inplace(pdata, final_amount) 
    
    await player_manager.save_player_data(user_id, pdata)
    return result