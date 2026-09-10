# modules/game_data/xp.py
# (VERSÃO CORRIGIDA: Unificação de stat_points + Migração Automática + Sincronização de Maestrias)

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
MAX_MULTIPLIER_CAP: float = 3.0 

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

    # --- AUTO-FIX: Recupera pontos perdidos na 'point_pool' ---
    # Se existirem pontos na chave antiga, move para a chave certa 'stat_points'
    stuck_points = player_data.pop("point_pool", 0)
    if stuck_points > 0:
        current_stats = int(player_data.get("stat_points", 0))
        player_data["stat_points"] = current_stats + int(stuck_points)
        logger.info(f"🔧 Auto-Fix XP: {stuck_points} pontos movidos de 'point_pool' para 'stat_points'.")
    # -----------------------------------------------------------

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

        # Adiciona Pontos de Status na chave CORRETA (stat_points)
        reward_points = levels_gained * POINTS_PER_LEVEL
        try:
            player_data["stat_points"] = int(player_data.get("stat_points", 0)) + reward_points
        except:
            player_data["stat_points"] = reward_points

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

    # Adiciona o XP para o Nível de Combate do jogador
    player_data["xp"] = int(player_data.get("xp", 0)) + amount

    # 👇 A MÁGICA: INTEGRAÇÃO COM O PASSE DE BATALHA 👇
    try:
        from modules.game_data.season_pass import adicionar_xp_passe
        # Envia a mesma quantidade de XP que o jogador ganhou para o Passe!
        # Como está dentro desta função, se o jogador tiver VIP, o bônus de XP VIP 
        # também se aplicará ao Passe automaticamente!
        adicionar_xp_passe(player_data, amount)
    except Exception as e:
        logger.error(f"Erro ao adicionar XP no passe: {e}")
    # 👆 FIM DA INTEGRAÇÃO 👆

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

# ================================
# XP DE PROFISSÃO (Coleta e Refino)
# ================================

PROF_MAX_LEVEL = 50

def get_xp_for_next_profession_level(level: int) -> int:
    if level >= PROF_MAX_LEVEL:
        return 0
    # curva mais leve que combate
    base = 40
    lin = 25 * (level - 1)
    quad = 8 * (level - 1) * (level - 1)
    return int(base + lin + quad)

def add_profession_xp_inplace(
    player_data: dict,
    amount: int,
    expected_type: str | None = None,
) -> dict:
    """
    Soma XP e Sincroniza a Profissão Ativa com a Mochila de Profissões (learned_professions).
    """
    if not isinstance(player_data, dict):
        return {}

    try:
        amount = int(amount)
    except Exception:
        amount = 0
    if amount <= 0:
        return {"xp_added": 0}

    expected = str(expected_type or "").strip().lower()

    # 1. Puxa a mochila nova
    learned = player_data.get("learned_professions", {})

    # Define qual profissão vai receber o XP
    if expected and expected in learned:
        prof_target = learned[expected]
    else:
        # Fallback para o legado
        prof_target = player_data.get("profession", {})

    if not prof_target:
        return {"xp_added": 0, "ignored": True}
        
    tipo = str(prof_target.get("type") or prof_target.get("key") or expected).lower()
    
    # Proteção para garantir que a XP não vá para a profissão errada
    if expected and tipo != expected:
        return {"xp_added": 0, "ignored": True}

    level = int(prof_target.get("level", 1) or 1)
    xp = int(prof_target.get("xp", 0) or 0)

    xp += amount

    levels_gained = 0
    while True:
        need = get_xp_for_next_profession_level(level + levels_gained)
        if need <= 0:
            xp = 0
            break
        if xp < need:
            break
        xp -= need
        levels_gained += 1
        if (level + levels_gained) >= PROF_MAX_LEVEL:
            xp = 0
            break

    new_level = level + levels_gained

    prof_target["level"] = new_level
    prof_target["xp"] = xp
    
    # 4. 🛡️ SINCRONIZAÇÃO ABSOLUTA: Salva nos dois lugares!
    if tipo:
        learned[tipo] = prof_target
    player_data["learned_professions"] = learned

    # Atualiza o campo legado para não quebrar compatibilidade
    legacy = player_data.get("profession", {})
    if legacy and str(legacy.get("type", "")).lower() == tipo:
        player_data["profession"] = prof_target
    elif not legacy:
        player_data["profession"] = prof_target

    return {
        "xp_added": amount,
        "old_level": level,
        "new_level": new_level,
        "levels_gained": levels_gained,
        "current_xp": xp,
        "next_level_xp": get_xp_for_next_profession_level(new_level),
        "profession_type": tipo,
    }