# handlers/guild/missions.py
# (VERSÃO ZERO LEGADO: MISSÕES DE CLÃ + AUTH SEGURA + STRING IDs)

import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, clan_manager
from modules.database import db
from modules.auth_utils import get_current_player_id

# Tenta importar o catálogo novo. Se falhar, usa um fallback vazio.
try:
    from modules.game_data.guild_missions import GUILD_MISSIONS_CATALOG
except ImportError:
    GUILD_MISSIONS_CATALOG = {}

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. VISUALIZAR DETALHES DA MISSÃO ATIVA
# ==============================================================================
async def show_guild_mission_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # 🔒 SEGURANÇA: Identificação via Auth Central
    user_id = get_current_player_id(update, context)
    if not user_id:
        if query: await query.answer("Sessão inválida.", show_alert=True)
        return

    # IMPORTAÇÃO TARDIA PARA EVITAR CICLO
    from handlers.guild.dashboard import _render_clan_screen
    
    player_data = await player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")
    
    if not clan_id:
        await query.answer("Sem clã!", show_alert=True)
        return

    clan = await clan_manager.get_clan(clan_id)
    if not clan: return

    mission = clan.get("active_mission")
    # Comparação segura de IDs (String)
    is_leader = (str(clan.get("leader_id")) == str(user_id))

    # Filtra missões antigas do tipo COLLECT se necessário, ou adapta
    if mission and str(mission.get('type')).upper() == 'COLLECT':
        mission = None

    if not mission:
        text = (
            "🛡️ <b>QUADRO DE CONTRATOS</b>\n"
            f"Clã: {clan.get('display_name')}\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            "<i>Nenhuma missão ativa no momento.</i>\n\n"
            "O Líder deve selecionar um contrato para iniciar a caçada."
        )
        kb = []
        if is_leader:
            kb.append([InlineKeyboardButton("⚔️ Iniciar Nova Caçada", callback_data="gld_mission_select_menu")])
        
        kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="clan_menu")])
        await _render_clan_screen(update, context, clan, text, kb)
        return

    title = mission.get("title", "Missão de Caça")
    desc = mission.get("description", "Derrote os monstros.")
    prog = mission.get("current_progress", 0)
    target = mission.get("target_count", 10)
    
    monster_id = mission.get("target_monster_id", "Monstro")
    monster_name = str(monster_id).replace("_", " ").title()
    
    percent = (prog / target) * 100 if target > 0 else 0
    percent = min(100, percent)
    blocks = int(percent / 10)
    bar = "🟩" * blocks + "⬜" * (10 - blocks)

    text = (
        f"📜 <b>CONTRATO ATIVO: {title}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"<i>{desc}</i>\n\n"
        f"🎯 <b>Alvo:</b> {monster_name}\n"
        f"📊 <b>Progresso:</b> {prog}/{target} ({percent:.1f}%)\n"
        f"<code>[{bar}]</code>\n\n"
        f"⚠️ <i>Todos os membros contribuem matando este monstro.</i>"
    )

    kb = []
    if is_leader:
        if prog >= target:
             text += "\n\n✅ <b>MISSÃO COMPLETA!</b>"
             kb.append([InlineKeyboardButton("🏆 Finalizar e Receber Prêmios", callback_data="gld_mission_finish")])
        kb.append([InlineKeyboardButton("❌ Cancelar Missão (Líder)", callback_data="gld_mission_cancel")])
    
    elif prog >= target:
        text += "\n\n✅ <b>Aguardando Líder finalizar.</b>"
    
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="clan_menu")])
    await _render_clan_screen(update, context, clan, text, kb)


# ==============================================================================
# 2. MENU DE SELEÇÃO (LÍDER)
# ==============================================================================
async def show_mission_selection_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    from handlers.guild.dashboard import _render_clan_screen

    # 🔒 Auth
    user_id = get_current_player_id(update, context)
    if not user_id: return

    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)
    
    if not clan or str(clan.get("leader_id")) != str(user_id):
        await query.answer("Apenas o líder pode iniciar missões!", show_alert=True)
        return

    text = (
        "⚔️ <b>MURAL DE CONTRATOS</b>\n\n"
        "Escolha a dificuldade da caçada para o seu clã.\n"
        "<i>Missões mais difíceis dão mais XP de Clã e Ouro para o Banco.</i>"
    )

    kb = [
        [InlineKeyboardButton("🟢 Caçada Fácil (Nv. 1-15)", callback_data="gld_start_hunt:easy")],
        [InlineKeyboardButton("🟡 Caçada Média (Nv. 15-30)", callback_data="gld_start_hunt:medium")],
        [InlineKeyboardButton("🔴 Caçada Difícil (Nv. 30+)", callback_data="gld_start_hunt:hard")],
        [InlineKeyboardButton("🔙 Cancelar", callback_data="clan_mission_details")]
    ]
    await _render_clan_screen(update, context, clan, text, kb)


# ==============================================================================
# 3. LÓGICA DE INICIAR A MISSÃO
# ==============================================================================
async def start_mission_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gera a missão a partir do CATÁLOGO externo e exibe com MÍDIA."""
    query = update.callback_query
    from handlers.guild.dashboard import _render_clan_screen
    
    # 🔒 Auth
    user_id = get_current_player_id(update, context)
    if not user_id:
        await query.answer("Sessão inválida.")
        return

    await query.answer()
    
    try:
        selected_difficulty = query.data.split(":")[1]
    except:
        selected_difficulty = "easy"
        
    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)
    
    # --- FILTRAGEM DO CATÁLOGO ---
    available_keys = [
        k for k, v in GUILD_MISSIONS_CATALOG.items() 
        if v.get("difficulty") == selected_difficulty and v.get("type") == "HUNT"
    ]
    
    if not available_keys:
        logger.warning(f"Nenhuma missão encontrada no catálogo para diff: {selected_difficulty}. Usando fallback.")
        mission_data = {
            "title": "Caçada de Emergência",
            "description": "Mate monstros aleatórios.",
            "target_monster_id": "slime_verde",
            "target_count": 10,
            "rewards": {"clan_xp": 100, "clan_gold": 500}
        }
    else:
        chosen_key = random.choice(available_keys)
        mission_data = GUILD_MISSIONS_CATALOG[chosen_key]

    monster_id = mission_data.get("target_monster_id")
    monster_name = str(monster_id).replace("_", " ").title()
    target_count = mission_data.get("target_count", 10)
    
    new_mission = {
        "type": "HUNT",
        "title": mission_data.get("title"),
        "description": mission_data.get("description"),
        "target_monster_id": monster_id,
        "target_count": target_count,
        "current_progress": 0,
        "rewards": mission_data.get("rewards", {}),
        "completed": False,
        "start_date": str(query.message.date)
    }
    
    try:
        # Salva no banco
        db.clans.update_one({"_id": clan_id}, {"$set": {"active_mission": new_mission}})
        
        # Atualiza o objeto clan local para refletir a nova missão na tela
        clan["active_mission"] = new_mission
            
        text = (
            f"✅ <b>CONTRATO ACEITO!</b>\n\n"
            f"📜 <b>{new_mission['title']}</b>\n"
            f"🎯 <b>Alvo:</b> {monster_name}\n"
            f"💀 <b>Meta:</b> {target_count} abates.\n\n"
            f"Avisem os membros do clã! Cada abate conta."
        )
        kb = [[InlineKeyboardButton("🛡️ Voltar ao Clã", callback_data="clan_menu")]]
        
        await _render_clan_screen(update, context, clan, text, kb)
        
    except Exception as e:
        logger.error(f"Erro ao iniciar missão: {e}")
        await query.answer("Erro técnico ao iniciar missão.", show_alert=True)


# ==============================================================================
# 4. FINALIZAR MISSÃO (Líder)
# ==============================================================================
async def finish_mission_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    from handlers.guild.dashboard import _render_clan_screen

    # 🔒 Auth
    user_id = get_current_player_id(update, context)
    if not user_id: return

    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)
    
    mission = clan.get("active_mission")
    if not mission:
        await query.answer("Nenhuma missão ativa.", show_alert=True)
        return

    if str(clan.get("leader_id")) != str(user_id):
        await query.answer("Apenas o líder pode finalizar.", show_alert=True)
        return

    current = mission.get("current_progress", 0)
    target = mission.get("target_count", 1)
    
    if current < target:
        await query.answer(f"Incompleta! {current}/{target}", show_alert=True)
        return

    rewards = mission.get("rewards", {})
    xp = rewards.get("clan_xp") or rewards.get("guild_xp") or 0
    gold = rewards.get("clan_gold") or rewards.get("gold") or 0
    
    db.clans.update_one(
        {"_id": clan_id},
        {
            "$inc": {"prestige_points": xp, "bank": gold},
            "$unset": {"active_mission": ""}
        }
    )
    
    updated_clan = await clan_manager.get_clan(clan_id)
    
    text = (
        f"🏆 <b>MISSÃO CUMPRIDA!</b>\n\n"
        f"O clã recebeu:\n"
        f"💠 <b>+{xp}</b> Pontos de Prestígio\n"
        f"💰 <b>+{gold}</b> Ouro no Cofre\n\n"
        f"Bom trabalho, líder! O clã está mais forte."
    )
    kb = [[InlineKeyboardButton("🛡️ Voltar", callback_data="clan_menu")]]
    await _render_clan_screen(update, context, updated_clan, text, kb)

# ==============================================================================
# 5. CANCELAR MISSÃO
# ==============================================================================
async def cancel_mission_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    from handlers.guild.dashboard import _render_clan_screen

    # 🔒 Auth
    user_id = get_current_player_id(update, context)
    if not user_id: return

    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)
    
    if str(clan.get("leader_id")) != str(user_id):
        await query.answer("Apenas o líder!", show_alert=True)
        return

    db.clans.update_one(
        {"_id": clan_id},
        {"$unset": {"active_mission": ""}}
    )
    
    if "active_mission" in clan:
        del clan["active_mission"]

    text = (
        "❌ <b>Missão Cancelada.</b>\n\n"
        "O contrato foi rasgado. Você pode escolher outra missão no mural."
    )
    kb = [[InlineKeyboardButton("🛡️ Voltar ao Clã", callback_data="clan_menu")]]
    await _render_clan_screen(update, context, clan, text, kb)


# ==============================================================================
# 6. HANDLERS EXPORTADOS
# ==============================================================================

clan_mission_start_handler = CallbackQueryHandler(show_mission_selection_menu, pattern=r'^gld_mission_select_menu$')
clan_guild_mission_details_handler = CallbackQueryHandler(show_guild_mission_details, pattern=r'^clan_mission_details$')
clan_mission_accept_handler = CallbackQueryHandler(start_mission_callback, pattern=r'^gld_start_hunt:')
clan_mission_finish_handler = CallbackQueryHandler(finish_mission_callback, pattern=r'^gld_mission_finish$')
clan_mission_cancel_handler = CallbackQueryHandler(cancel_mission_callback, pattern=r'^gld_mission_cancel$')

async def placeholder_purchase(u, c): pass
clan_board_purchase_handler = CallbackQueryHandler(placeholder_purchase, pattern=r'^gld_buy_board$')