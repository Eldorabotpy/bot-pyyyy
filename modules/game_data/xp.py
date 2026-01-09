# modules/game_data/xp.py
# (VERSÃO CORRIGIDA: Suporte ObjectId + Trava de Segurança de Multiplicador)

from __future__ import annotations
from typing import Dict, Optional, Tuple, Union
import logging

# --- Imports MongoDB ---
from bson import ObjectId

from modules import player_manager

# ✅ Tenta importar PremiumManager com segurança
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
MAX_MULTIPLIER_CAP: float = 3.0 # TRAVA DE SEGURANÇA: Ninguém ganha mais que 3x XP (nem Lenda)

# ================================
# Helpers
# ================================
def ensure_object_id(uid):
    """Garante que o ID seja compatível com o banco."""
    if isinstance(uid, ObjectId):
        return uid
    if isinstance(uid, str) and ObjectId.is_valid(uid):
        return ObjectId(uid)
    return uid

def _xp_formula(level: int) -> int:
    """XP necessário para o próximo nível."""
    if level >= MAX_LEVEL: return 0
    
    # Curva Quadrática (Padrão RPG)
    base = 200
    lin  = 100 * (level - 1)
    quad = 40 * (level - 1) * (level - 1)
    
    raw_xp = int(base + lin + quad)

    # Multiplicadores de Dificuldade ("O Muro")
    multiplier = 1.0
    if level >= 80: multiplier = 4.0
    elif level >= 50: multiplier = 2.5
    elif level >= 20: multiplier = 1.5

    return int(raw_xp * multiplier)

def get_xp_for_next_combat_level(level: int) -> int:
    try: level = int(level)
    except: level = 1
    level = max(1, level)
    return max(0, _xp_formula(level))

# ================================
# Núcleo de Level Up (Lógica Interna)
# ================================
def _apply_level_ups_inplace(player_data: dict) -> Dict[str, int]:
    """Aplica level ups diretamente no dicionário do jogador."""
    if not isinstance(player_data, dict):
        player_data = {"level": 1, "xp": 0}

    level_before = int(player_data.get("level", 1) or 1)
    xp_curr      = int(player_data.get("xp", 0) or 0)

    levels_gained = 0
    while True:
        need = get_xp_for_next_combat_level(level_before + levels_gained)
        if need <= 0: # Nível máximo
            xp_curr = 0; break
        if xp_curr < need:
            break
        xp_curr -= need
        levels_gained += 1
        if (level_before + levels_gained) >= MAX_LEVEL:
            xp_curr = 0; break

    if levels_gained > 0:
        new_level = level_before + levels_gained
        player_data["level"] = new_level
        player_data["xp"]    = xp_curr

        # Adiciona Pontos de Status
        reward_points = levels_gained * POINTS_PER_LEVEL
        try:
            player_data["point_pool"] = int(player_data.get("point_pool", 0)) + reward_points
        except:
            player_data["point_pool"] = reward_points

        # Restaura Energia/HP (Bônus de Level Up)
        try:
            player_data["current_hp"] = player_data.get("max_hp", 100)
            player_data["energy"] = player_data.get("max_energy", 20)
        except: pass

        return {
            "old_level": level_before, "new_level": new_level,
            "levels_gained": levels_gained, "points_awarded": reward_points,
            "current_xp": xp_curr, "next_level_xp": get_xp_for_next_combat_level(new_level),
        }

    # Se não upou
    return {
        "old_level": level_before, "new_level": level_before,
        "levels_gained": 0, "points_awarded": 0,
        "current_xp": xp_curr, "next_level_xp": get_xp_for_next_combat_level(level_before),
    }

def add_combat_xp_inplace(player_data: dict, amount: int) -> Dict[str, int]:
    """Versão síncrona para uso dentro de Engines que já carregaram o player."""
    if not isinstance(player_data, dict): return {}
    
    try: amount = int(amount)
    except: amount = 0
    
    if amount <= 0: return {}

    player_data["xp"] = int(player_data.get("xp", 0)) + amount
    return _apply_level_ups_inplace(player_data)

# ================================
# API Pública (Async + Premium Check)
# ================================
async def add_combat_xp(user_id, amount: int) -> Dict[str, int]:
    """
    Adiciona XP, aplica bônus Premium e salva no banco.
    Suporta ObjectId corretamente.
    """
    # 1. Garante ID correto para o Mongo
    db_id = ensure_object_id(user_id)
    
    pdata = await player_manager.get_player_data(db_id)
    if not pdata:
        logger.warning(f"Tentativa de dar XP para jogador inexistente: {user_id}")
        return {}
    
    # 2. Lógica de Multiplicador VIP (Com Trava de Segurança)
    final_amount = amount
    try:
        if PremiumManager:
            pm = PremiumManager(pdata)
            mult = float(pm.get_perk_value("xp_multiplier", 1.0))
            
            # TRAVA DE SEGURANÇA: Se o mult for absurdo (ex: 100.0), limita a 3.0
            if mult > MAX_MULTIPLIER_CAP:
                logger.warning(f"⚠️ Multiplicador XP suspeito ({mult}x) para {user_id}. Limitado a {MAX_MULTIPLIER_CAP}x.")
                mult = MAX_MULTIPLIER_CAP
            
            if mult > 1.0:
                final_amount = int(amount * mult)
    except Exception as e:
        logger.error(f"Erro ao aplicar XP Premium: {e}")

    # 3. Aplica e Salva
    result = add_combat_xp_inplace(pdata, final_amount)
    await player_manager.save_player_data(db_id, pdata)
    
    return result