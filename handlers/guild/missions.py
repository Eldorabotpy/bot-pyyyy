# handlers/guild/missions.py
# (VERSÃO CORRIGIDA: LENDO DO GUILD_MISSIONS_CATALOG)

import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, clan_manager
from modules.database import db

# Tenta importar o catálogo novo. Se falhar, usa um fallback vazio para não quebrar.
try:
    from modules.game_data.guild_missions import GUILD_MISSIONS_CATALOG
except ImportError:
    GUILD_MISSIONS_CATALOG = {}

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. VISUALIZAR DETALHES DA MISSÃO ATIVA
# ==============================================================================
async def show_guild_mission_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o status detalhado da missão atual do clã."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    player_data = await player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")
    
    if not clan_id:
        await query.edit_message_text("Você não tem um clã.")
        return

    # Busca dados do clã
    clan = await clan_manager.get_clan(clan_id)
    if not clan:
        await query.edit_message_text("Clã não encontrado.")
        return

    mission = clan.get("active_mission")
    is_leader = (int(clan.get("leader_id")) == user_id)

    # [PROTEÇÃO] Remove missões de coleta antigas se existirem
    if mission and str(mission.get('type')).upper() == 'COLLECT':
        mission = None

    if not mission:
        text = (
            "🛡️ <b>Missão do Clã</b>\n\n"
            "<i>Nenhuma missão ativa no momento.</i>\n"
            "O Líder deve acessar o menu do clã para iniciar uma nova caçada."
        )
        kb = []
        if is_leader:
            kb.append([InlineKeyboardButton("⚔️ Iniciar Nova Caçada", callback_data="gld_mission_select_menu")])
        
        kb.append([InlineKeyboardButton("🔙 Voltar", callback_data="clan_menu")])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return

    # Dados da missão ativa
    title = mission.get("title", "Missão de Caça")
    desc = mission.get("description", "Derrote os monstros.")
    prog = mission.get("current_progress", 0)
    target = mission.get("target_count", 10)
    monster_id = mission.get("target_monster_id")
    monster_name = str(monster_id).replace("_", " ").title()
    
    # Barra de progresso
    percent = (prog / target) * 100 if target > 0 else 0
    blocks = int(percent / 10)
    bar = "🟩" * blocks + "⬜" * (10 - blocks)

    text = (
        f"📜 <b>{title}</b>\n"
        f"<i>{desc}</i>\n\n"
        f"🎯 <b>Alvo:</b> {monster_name}\n"
        f"📊 <b>Progresso:</b> {prog}/{target} ({percent:.1f}%)\n"
        f"<code>[{bar}]</code>\n\n"
        f"⚠️ <i>Todos os membros do clã contribuem matando este monstro.</i>"
    )

    kb = []
    
    if is_leader:
        # Se completou: Finalizar
        if prog >= target:
             kb.append([InlineKeyboardButton("✅ Finalizar e Receber Prêmios", callback_data="gld_mission_finish")])
        else:
             text += "\n\n✅ <b>Missão Completa! Aguardando Líder finalizar.</b>" if prog >= target else ""
             # Botão de Cancelar para trocar de missão se quiser
             kb.append([InlineKeyboardButton("❌ Cancelar Missão (Líder)", callback_data="gld_mission_cancel")])
    
    kb.append([InlineKeyboardButton("🔙 Voltar", callback_data="clan_menu")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")


# ==============================================================================
# 2. MENU DE SELEÇÃO (LÍDER)
# ==============================================================================
async def show_mission_selection_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra opções de dificuldade para nova missão."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)
    
    if not clan or int(clan.get("leader_id")) != user_id:
        await query.answer("Apenas o líder pode iniciar missões!", show_alert=True)
        return

    # Verifica se já tem missão ativa (e não é bugada)
    if clan.get("active_mission") and not clan.get("active_mission", {}).get("completed"):
        if str(clan.get("active_mission", {}).get("type")).upper() != 'COLLECT':
            await query.answer("Já existe uma missão ativa!", show_alert=True)
            return

    text = (
        "⚔️ <b>Mural de Contratos</b>\n\n"
        "Escolha a dificuldade da caçada para o seu clã.\n"
        "<i>Missões mais difíceis dão mais XP de Clã e Ouro para o Banco.</i>"
    )

    kb = [
        [InlineKeyboardButton("🟢 Caçada Fácil (Nv. 1-15)", callback_data="gld_start_hunt:easy")],
        [InlineKeyboardButton("🟡 Caçada Média (Nv. 15-30)", callback_data="gld_start_hunt:medium")],
        [InlineKeyboardButton("🔴 Caçada Difícil (Nv. 30+)", callback_data="gld_start_hunt:hard")],
        [InlineKeyboardButton("🔙 Cancelar", callback_data="clan_menu")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")


# ==============================================================================
# 3. LÓGICA DE INICIAR A MISSÃO (AGORA USA O CATÁLOGO)
# ==============================================================================
async def start_mission_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gera a missão a partir do CATÁLOGO externo."""
    query = update.callback_query
    await query.answer()
    
    try:
        selected_difficulty = query.data.split(":")[1]
    except:
        selected_difficulty = "easy"
        
    user_id = query.from_user.id
    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    
    # --- FILTRAGEM DO CATÁLOGO ---
    # Encontra todas as chaves no catálogo que batem com a dificuldade
    available_keys = [
        k for k, v in GUILD_MISSIONS_CATALOG.items() 
        if v.get("difficulty") == selected_difficulty and v.get("type") == "HUNT"
    ]
    
    # Se não achar nenhuma (ou catálogo vazio), usa fallback genérico
    if not available_keys:
        logger.warning(f"Nenhuma missão encontrada no catálogo para diff: {selected_difficulty}. Usando fallback.")
        # Fallback de segurança
        mission_data = {
            "title": "Caçada de Emergência",
            "description": "Mate monstros aleatórios.",
            "target_monster_id": "slime_verde", # Monster default
            "target_count": 10,
            "rewards": {"clan_xp": 100, "clan_gold": 500}
        }
    else:
        # Sorteia uma missão do catálogo daquela dificuldade
        chosen_key = random.choice(available_keys)
        mission_data = GUILD_MISSIONS_CATALOG[chosen_key]

    # Prepara o objeto para salvar no banco
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
        if hasattr(clan_manager, "set_active_mission"):
            await clan_manager.set_active_mission(clan_id, new_mission)
        else:
            db.clans.update_one({"_id": clan_id}, {"$set": {"active_mission": new_mission}})
            
        await query.edit_message_text(
            f"✅ <b>Contrato Aceito!</b>\n\n"
            f"📜 <b>{new_mission['title']}</b>\n"
            f"🎯 Alvo: <b>{monster_name}</b>\n"
            f"💀 Meta: {target_count} abates.\n\n"
            f"Avisem os membros do clã! Cada abate conta.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛡️ Voltar ao Clã", callback_data="clan_menu")]])
        , parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Erro ao iniciar missão: {e}")
        await query.edit_message_text("Erro técnico ao iniciar missão. Tente novamente.")


# ==============================================================================
# 4. FINALIZAR MISSÃO (Líder)
# ==============================================================================
async def finish_mission_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)
    
    mission = clan.get("active_mission")
    if not mission: return

    if mission.get("current_progress", 0) < mission.get("target_count", 1):
        await query.answer("A missão ainda não foi concluída!", show_alert=True)
        return

    rewards = mission.get("rewards", {})
    # Suporte a várias chaves de dicionário para evitar erro
    xp = rewards.get("clan_xp") or rewards.get("guild_xp") or 0
    gold = rewards.get("clan_gold") or rewards.get("gold") or 0
    
    # Atualiza o banco do clã
    db.clans.update_one(
        {"_id": clan_id},
        {
            "$inc": {"prestige_points": xp, "bank": gold},
            "$unset": {"active_mission": ""}
        }
    )
    
    await query.edit_message_text(
        f"🏆 <b>MISSÃO CUMPRIDA!</b>\n\n"
        f"O clã recebeu:\n"
        f"➕ {xp} Pontos de Prestígio\n"
        f"💰 {gold} Ouro no Cofre\n\n"
        f"Bom trabalho, líder! O clã está mais forte.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛡️ Voltar", callback_data="clan_menu")]])
    , parse_mode="HTML")

# ==============================================================================
# 5. CANCELAR MISSÃO
# ==============================================================================
async def cancel_mission_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)
    
    if int(clan.get("leader_id")) != user_id:
        await query.answer("Apenas o líder pode cancelar!", show_alert=True)
        return

    db.clans.update_one(
        {"_id": clan_id},
        {"$unset": {"active_mission": ""}}
    )
    
    await query.edit_message_text(
        "❌ <b>Missão Cancelada.</b>\n\n"
        "O contrato foi rasgado. Você pode escolher outra missão no mural.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛡️ Voltar ao Clã", callback_data="clan_menu")]])
    , parse_mode="HTML")


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