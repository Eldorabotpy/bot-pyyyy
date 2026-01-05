# handlers/jobs.py
# (VERSÃO FINAL BLINDADA: Expiração Estrita via 'users' + Jobs Otimizados)

from __future__ import annotations

import logging
import asyncio
import datetime
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Dict, Optional, Any

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

# --- IMPORTS DE DADOS E CORE ---
from modules import player_manager, game_data
from modules.auth_utils import get_current_player_id
# Importamos a coleção 'users' diretamente para garantir a fonte de verdade
from modules.player.core import users_collection, save_player_data, players_collection

# --- CONFIGURAÇÃO ---
from config import ADMIN_ID, JOB_TIMEZONE, ANNOUNCEMENT_CHAT_ID, ANNOUNCEMENT_THREAD_ID
from pvp.pvp_scheduler import executar_reset_pvp

# --- ENGINE IMPORTS ---
try:
    from modules.world_boss.engine import (
        world_boss_manager, 
        broadcast_boss_announcement, 
        distribute_boss_rewards
    )
except ImportError:
    world_boss_manager = None

try:
    from kingdom_defense.engine import event_manager
except ImportError:
    event_manager = None

logger = logging.getLogger(__name__)

# ==============================================================================
# UTILITÁRIOS
# ==============================================================================

def get_col_and_id(user_id):
    """Retorna a coleção e ID corretos (Híbrido) para jobs genéricos."""
    from bson import ObjectId
    # 1. Se já for ObjectId
    if isinstance(user_id, ObjectId):
        return users_collection, user_id
    # 2. Legado (Int)
    if isinstance(user_id, int):
        return players_collection, user_id
    # 3. String
    elif isinstance(user_id, str):
        if users_collection is not None and ObjectId.is_valid(user_id):
            return users_collection, ObjectId(user_id)
        if user_id.isdigit():
            return players_collection, int(user_id)
    return None, None

def _today_str() -> str:
    try:
        tz = ZoneInfo(JOB_TIMEZONE)
        now = datetime.now(tz)
    except Exception:
        now = datetime.now()
    return now.date().isoformat()

# ==============================================================================
# 1. ROTINA DE PREMIUM (ESTRITA - USERS ONLY)
# ==============================================================================
async def check_premium_expiration_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Verifica APENAS a coleção 'users'.
    Lógica: Se (Agora > Expira), define tier='free' e remove a data.
    """
    if users_collection is None:
        logger.error("❌ [JOB PREMIUM] users_collection não está conectado! Abortando.")
        return

    # Garante UTC para comparação
    now_utc = datetime.now(timezone.utc)
    count_downgraded = 0

    # Busca APENAS usuários que tenham uma data de expiração (ignora null/free)
    # Isso torna a query muito leve.
    query_filter = {"premium_expires_at": {"$ne": None}}
    
    try:
        # Pega todos os candidatos a expiração
        cursor = users_collection.find(query_filter)
        
        # Converte para lista para evitar timeout de cursor em async
        # (Assumindo que não há milhões de premiums simultâneos, isso é seguro)
        expired_candidates = list(cursor)

        for doc in expired_candidates:
            user_id = doc.get("_id")
            expires_str = doc.get("premium_expires_at")
            
            if not expires_str: 
                continue

            try:
                # 1. Parse da data (Formato ISO)
                expires_dt = datetime.fromisoformat(str(expires_str))
                
                # Garante Timezone Aware (UTC) para não dar erro de comparação
                if expires_dt.tzinfo is None:
                    expires_dt = expires_dt.replace(tzinfo=timezone.utc)
                
                # 2. VERIFICAÇÃO FINAL: VENCEU?
                if now_utc > expires_dt:
                    # >>> SIM, VENCEU. EXECUTAR DOWNGRADE <<<
                    
                    old_tier = doc.get("premium_tier", "Desconhecido")
                    
                    # Atualização Atômica no Mongo (Mais seguro que save_player_data aqui)
                    users_collection.update_one(
                        {"_id": user_id},
                        {
                            "$set": {
                                "premium_tier": "free",       # Volta para Comum
                                "premium_expires_at": None    # Limpa a data (vira permanente free)
                            }
                        }
                    )
                    
                    count_downgraded += 1
                    
                    # 3. Notifica o usuário (Fire and forget)
                    chat_id = doc.get("telegram_id_owner") or doc.get("last_chat_id")
                    if chat_id:
                        try:
                            msg = (
                                "⚠️ <b>ASSINATURA EXPIRADA</b>\n\n"
                                f"O seu plano <b>{str(old_tier).capitalize()}</b> chegou ao fim.\n"
                                "Sua conta retornou para <b>Aventureiro Comum</b>.\n\n"
                                "💎 <i>Renove na /loja_premium para recuperar as vantagens!</i>"
                            )
                            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")
                            await asyncio.sleep(0.05) # Delay anti-flood
                        except Exception:
                            pass # Bloqueado ou chat inválido

            except ValueError:
                # Se a data estiver corrompida (ex: string mal formatada), reseta por segurança
                logger.warning(f"[JOB] Data corrompida para {user_id}: {expires_str}. Resetando para Free.")
                users_collection.update_one(
                    {"_id": user_id},
                    {"$set": {"premium_tier": "free", "premium_expires_at": None}}
                )

    except Exception as e:
        logger.error(f"Erro fatal no loop de expiração premium: {e}")

    if count_downgraded > 0:
        logger.info(f"📉 [JOB PREMIUM] {count_downgraded} usuários voltaram para Aventureiro Comum.")

# ==============================================================================
# 2. RESET DE TICKETS (OTIMIZADO - UPDATE EM MASSA)
# ==============================================================================

async def daily_pvp_entry_reset_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Reseta os tickets de Arena PvP para 5 diariamente.
    Usa update_many para ser instantâneo.
    """
    today = _today_str()
    logger.info("[JOB] Resetando Tickets de Arena (Mass Update)...")
    
    try:
        # Atualiza Coleção Nova (Users)
        if users_collection is not None:
            res_users = users_collection.update_many(
                {}, # Todos
                {
                    "$set": {
                        "inventory.ticket_arena": 5,
                        "last_pvp_entry_reset": today
                    }
                }
            )
            logger.info(f"✅ [Arena] {res_users.modified_count} usuários (Novo) resetados.")

        # Atualiza Coleção Antiga (Players - Legado)
        if players_collection is not None:
            res_old = players_collection.update_many(
                {}, 
                {
                    "$set": {
                        "inventory.ticket_arena": 5,
                        "last_pvp_entry_reset": today
                    }
                }
            )
            logger.info(f"✅ [Arena] {res_old.modified_count} usuários (Legado) resetados.")
            
    except Exception as e:
        logger.error(f"Erro no reset de Arena: {e}")

async def distribute_kingdom_defense_ticket_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Entrega/Reseta o Ticket de Defesa do Reino (1 por dia/evento).
    """
    logger.info("[JOB] Distribuindo Tickets Kingdom Defense (Mass Update)...")
    
    try:
        # Define inventory.ticket_defesa_reino = 1 para TODOS
        if users_collection is not None:
            users_collection.update_many(
                {}, 
                {"$set": {"inventory.ticket_defesa_reino": 1}}
            )
            
        if players_collection is not None:
            players_collection.update_many(
                {}, 
                {"$set": {"inventory.ticket_defesa_reino": 1}}
            )
            
        logger.info("✅ [KD] Tickets de Defesa resetados para 1.")
        
    except Exception as e:
        logger.error(f"Erro na distribuição KD: {e}")

# ==============================================================================
# 3. WORLD BOSS & EVENTOS
# ==============================================================================

async def check_world_boss_spawn(context: ContextTypes.DEFAULT_TYPE):
    if not world_boss_manager: return
    try:
        # Garante UTC para hora consistente no servidor
        now = datetime.now(timezone.utc)
        # Ajuste manual para Horário de Brasília (-3) se o servidor for UTC puro
        # Se seu servidor já está em BRT, remova o delta.
        now_br = now - asyncio.timedelta(hours=3)

        # Se o boss morreu e o evento ainda consta ativo no manager
        if world_boss_manager.state["is_active"] and world_boss_manager.state["current_hp"] <= 0:
            await distribute_boss_rewards(context)
            return

        # Horários de Spawn: 12h e 20h
        SPAWN_HOURS = [12, 20] 
        if now_br.hour in SPAWN_HOURS and now_br.minute == 0:
            if not world_boss_manager.state["is_active"]:
                await world_boss_manager.spawn_boss()
                await broadcast_boss_announcement(context, "spawn")
                
    except Exception as e:
        logger.error(f"Erro no Job World Boss: {e}")

# ==============================================================================
# 4. FERRAMENTAS ADMIN (MANUAIS)
# ==============================================================================

async def cmd_force_pvp_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando ADMIN para forçar rotinas de PvP."""
    user_id = get_current_player_id(update, context)
    
    # Verifica ID Admin simples
    if str(user_id) != str(ADMIN_ID) and str(update.effective_user.id) != str(ADMIN_ID):
        return
        
    await update.message.reply_text("🔄 <b>DEBUG:</b> Rodando rotinas de PvP...", parse_mode="HTML")
    
    # Executa lógica de scheduler
    await executar_reset_pvp(context)
    # Executa o reset de tickets
    await daily_pvp_entry_reset_job(context)
    
    await update.message.reply_text("✅ Rotinas PvP finalizadas.", parse_mode="HTML")

async def reset_pvp_season(context: ContextTypes.DEFAULT_TYPE):
    """Job agendado para rodar as rotinas de PvP."""
    await executar_reset_pvp(context)

async def force_grant_daily_crystals(context: ContextTypes.DEFAULT_TYPE):
    """Pode ser usado para dar cristais manualmente se necessário."""
    pass

# ==============================================================================
# 5. REGENERAÇÃO DE ENERGIA (HÍBRIDA)
# ==============================================================================
# Variável global para controlar ticks (não mexer)
_non_premium_tick: Dict[str, int] = {"count": 0}

async def regenerate_energy_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Roda a cada X minutos. 
    Premium regenera todo tick. Free regenera a cada 2 ticks.
    """
    _non_premium_tick["count"] = (_non_premium_tick["count"] + 1) % 2
    regenerate_non_premium = (_non_premium_tick["count"] == 0)
    
    # Aqui precisamos iterar um por um para checar o limite máximo de cada um
    # Não dá pra fazer mass update fácil pois cada um tem um max_energy diferente
    async for user_id, pdata in player_manager.iter_players():
        try:
            if not isinstance(pdata, dict): continue
            
            # Pega limites
            max_e = int(player_manager.get_player_max_energy(pdata)) 
            cur_e = int(pdata.get("energy", 0))
            
            # Se já está cheio, ignora
            if cur_e >= max_e: continue 

            # Verifica Tier
            tier = pdata.get("premium_tier", "free")
            is_premium = tier in ["vip", "premium", "lenda", "admin"]
            
            # Lógica de Tick
            if is_premium or regenerate_non_premium:
                col, query_id = get_col_and_id(user_id)
                if col is not None:
                    # Incrementa 1 energia
                    col.update_one({"_id": query_id}, {"$inc": {"energy": 1}})
                    
                    # Limpa cache para refletir no menu
                    try:
                        if hasattr(player_manager, "clear_player_cache"):
                            await player_manager.clear_player_cache(user_id)
                    except: pass
                    
        except Exception: 
            pass # Ignora erros individuais no loop de energia para não travar