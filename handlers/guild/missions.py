# handlers/guild/missions.py
# (VERSÃO CORRIGIDA: UI RENDERER + IMAGENS DE MONSTROS + SEM DEPENDÊNCIA CIRCULAR)

import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, clan_manager, file_ids
from modules.database import db
from modules.auth_utils import get_current_player_id
from ui.ui_renderer import render_photo_or_text

# Tenta importar o catálogo novo. Se falhar, usa um fallback vazio.
try:
    from modules.game_data.guild_missions import GUILD_MISSIONS_CATALOG
except ImportError:
    GUILD_MISSIONS_CATALOG = {}

logger = logging.getLogger(__name__)

# ==============================================================================
# HELPERS VISUAIS
# ==============================================================================

def _pick_mission_media(clan_data, mission_data=None):
    """
    Tenta selecionar a imagem mais específica possível:
    1. Imagem do Monstro (se houver missão ativa).
    2. Imagem genérica de Missão.
    3. Logo do Clã.
    """
    # 1. Tenta imagem do monstro alvo
    if mission_data:
        mob_id = mission_data.get("target_monster_id")
        if mob_id:
            try:
                # Ex: img_mob_orc_warrior
                fid = file_ids.get_file_id(f"img_mob_{mob_id}")
                if fid: return fid
            except: pass
            
    # 2. Tenta imagem genérica de missões
    try:
        fid = file_ids.get_file_id("img_mission_board")
        if fid: return fid
    except: pass

    # 3. Fallback: Logo do Clã
    if clan_data and clan_data.get("logo_media_key"):
        return clan_data.get("logo_media_key")

    return None

async def _render_mission_screen(update, context, clan_data, text, keyboard, mission_data=None):
    """Renderiza a tela usando o sistema unificado UI Renderer."""
    media_id = _pick_mission_media(clan_data, mission_data)
    
    await render_photo_or_text(
        update,
        context,
        text=text,
        photo_file_id=media_id,
        reply_markup=InlineKeyboardMarkup(keyboard),
        scope="clan_mission_screen", 
        parse_mode="HTML",
        allow_edit=True
    )

# ==============================================================================
# 1. VISUALIZAR DETALHES DA MISSÃO ATIVA
# ==============================================================================
async def show_guild_mission_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # 🔒 SEGURANÇA
    user_id = get_current_player_id(update, context)
    if not user_id:
        if query: await query.answer("Sessão inválida.", show_alert=True)
        return

    player_data = await player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")
    
    if not clan_id:
        await render_photo_or_text(update, context, "Você não possui um clã!", None)
        return

    clan = await clan_manager.get_clan(clan_id)
    if not clan: return

    mission = clan.get("active_mission")
    
    # VERIFICAÇÃO DE PERMISSÃO
    can_manage = await clan_manager.check_permission(clan, user_id, 'mission_manage')

    # Filtra legado
    if mission and str(mission.get('type')).upper() == 'COLLECT':
        mission = None

    # --- CENÁRIO A: SEM MISSÃO ---
    if not mission:
        text = (
            "🛡️ <b>QUADRO DE CONTRATOS</b>\n"
            f"Clã: {clan.get('display_name')}\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            "<i>O quadro está vazio no momento.</i>\n\n"
            "Líderes e Generais podem assinar um novo contrato de caça para o clã ganhar Prestígio e Ouro."
        )
        kb = []
        if can_manage:
            kb.append([InlineKeyboardButton("⚔️ Iniciar Nova Caçada", callback_data="gld_mission_select_menu")])
        
        kb.append([InlineKeyboardButton("⬅️ Voltar ao Clã", callback_data="clan_menu")])
        
        await _render_mission_screen(update, context, clan, text, kb)
        return

    # --- CENÁRIO B: MISSÃO ATIVA ---
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
    
    # Gestão
    if can_manage:
        if prog >= target:
             text += "\n\n✅ <b>MISSÃO COMPLETA!</b>\nToque abaixo para resgatar a recompensa."
             kb.append([InlineKeyboardButton("🏆 Finalizar e Receber Prêmios", callback_data="gld_mission_finish")])
        else:
            # Opção de cancelar só aparece se incompleta
            kb.append([InlineKeyboardButton("❌ Cancelar Contrato", callback_data="gld_mission_cancel")])
    
    elif prog >= target:
        text += "\n\n✅ <b>Aguardando Líder/General finalizar.</b>"
    
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="clan_menu")])
    
    # Renderiza passando 'mission' para tentar pegar a foto do monstro
    await _render_mission_screen(update, context, clan, text, kb, mission_data=mission)


# ==============================================================================
# 2. MENU DE SELEÇÃO (LÍDER/GENERAL)
# ==============================================================================
async def show_mission_selection_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    user_id = get_current_player_id(update, context)
    if not user_id: return

    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)
    
    # Permissão
    if not await clan_manager.check_permission(clan, user_id, 'mission_manage'):
        await query.answer("Apenas Generais e Líderes podem iniciar missões!", show_alert=True)
        return

    text = (
        "⚔️ <b>MURAL DE CONTRATOS</b>\n\n"
        "Selecione a dificuldade da caçada.\n"
        "<i>Missões mais difíceis exigem mais abates, mas dão muito mais XP de Clã e Ouro.</i>"
    )

    kb = [
        [InlineKeyboardButton("🟢 Caçada Fácil (Nv. 1-15)", callback_data="gld_start_hunt:easy")],
        [InlineKeyboardButton("🟡 Caçada Média (Nv. 15-30)", callback_data="gld_start_hunt:medium")],
        [InlineKeyboardButton("🔴 Caçada Difícil (Nv. 30+)", callback_data="gld_start_hunt:hard")],
        [InlineKeyboardButton("🔙 Cancelar", callback_data="clan_mission_details")]
    ]
    
    await _render_mission_screen(update, context, clan, text, kb)


# ==============================================================================
# 3. LÓGICA DE INICIAR A MISSÃO
# ==============================================================================
async def start_mission_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = get_current_player_id(update, context)
    if not user_id: return
    
    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)

    if not await clan_manager.check_permission(clan, user_id, 'mission_manage'):
        await render_photo_or_text(update, context, "❌ Sem permissão.", None)
        return
    
    try:
        selected_difficulty = query.data.split(":")[1]
    except:
        selected_difficulty = "easy"
        
    # --- BUSCA NO CATÁLOGO ---
    available_keys = [
        k for k, v in GUILD_MISSIONS_CATALOG.items() 
        if v.get("difficulty") == selected_difficulty and v.get("type") == "HUNT"
    ]
    
    if not available_keys:
        mission_data = {
            "title": "Caçada de Emergência",
            "description": "Mate monstros aleatórios para proteger a área.",
            "target_monster_id": "slime_verde", # Default seguro
            "target_count": 15,
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
        clan["active_mission"] = new_mission # Atualiza local
            
        text = (
            f"✅ <b>CONTRATO ACEITO!</b>\n\n"
            f"📜 <b>{new_mission['title']}</b>\n"
            f"🎯 <b>Alvo Prioritário:</b> {monster_name}\n"
            f"💀 <b>Meta:</b> {target_count} abates.\n\n"
            f"Avisem os membros! A caçada começou."
        )
        kb = [[InlineKeyboardButton("🛡️ Voltar ao Clã", callback_data="clan_menu")]]
        
        # Mostra a tela com a foto do novo monstro alvo
        await _render_mission_screen(update, context, clan, text, kb, mission_data=new_mission)
        
    except Exception as e:
        logger.error(f"Erro ao iniciar missão: {e}")
        await query.answer("Erro técnico.", show_alert=True)


# ==============================================================================
# 4. FINALIZAR MISSÃO
# ==============================================================================
async def finish_mission_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    user_id = get_current_player_id(update, context)
    if not user_id: return

    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)
    
    mission = clan.get("active_mission")
    if not mission:
        await query.answer("Nenhuma missão ativa.", show_alert=True)
        return

    if not await clan_manager.check_permission(clan, user_id, 'mission_manage'):
        await query.answer("Sem permissão.", show_alert=True)
        return

    current = mission.get("current_progress", 0)
    target = mission.get("target_count", 1)
    
    if current < target:
        await query.answer(f"Incompleta! {current}/{target}", show_alert=True)
        return

    rewards = mission.get("rewards", {})
    xp = rewards.get("clan_xp") or rewards.get("guild_xp") or 0
    gold = rewards.get("clan_gold") or rewards.get("gold") or 0
    
    # Entrega Recompensas
    db.clans.update_one(
        {"_id": clan_id},
        {
            "$inc": {"prestige_points": xp, "bank": gold},
            "$unset": {"active_mission": ""}
        }
    )
    
    # Atualiza objeto local
    clan["prestige_points"] = clan.get("prestige_points", 0) + xp
    clan["bank"] = clan.get("bank", 0) + gold
    if "active_mission" in clan: del clan["active_mission"]
    
    text = (
        f"🏆 <b>MISSÃO CUMPRIDA!</b>\n\n"
        f"O contrato foi finalizado com sucesso.\n\n"
        f"💰 <b>+{gold}</b> Ouro (Cofre)\n"
        f"💠 <b>+{xp}</b> XP (Clã)\n\n"
        f"O clã ficou mais forte!"
    )
    kb = [[InlineKeyboardButton("🛡️ Voltar ao Clã", callback_data="clan_menu")]]
    
    await _render_mission_screen(update, context, clan, text, kb)

# ==============================================================================
# 5. CANCELAR MISSÃO
# ==============================================================================
async def cancel_mission_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    user_id = get_current_player_id(update, context)
    if not user_id: return

    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    clan = await clan_manager.get_clan(clan_id)
    
    if not await clan_manager.check_permission(clan, user_id, 'mission_manage'):
        await query.answer("Sem permissão.", show_alert=True)
        return

    db.clans.update_one(
        {"_id": clan_id},
        {"$unset": {"active_mission": ""}}
    )
    
    if "active_mission" in clan: del clan["active_mission"]

    text = (
        "❌ <b>CONTRATO CANCELADO</b>\n\n"
        "A missão foi abortada. O clã não recebeu recompensas, mas o mural está livre novamente."
    )
    kb = [[InlineKeyboardButton("🛡️ Voltar ao Clã", callback_data="clan_menu")]]
    
    await _render_mission_screen(update, context, clan, text, kb)


# ==============================================================================
# HANDLERS EXPORTADOS
# ==============================================================================

clan_mission_start_handler = CallbackQueryHandler(show_mission_selection_menu, pattern=r'^gld_mission_select_menu$')
clan_guild_mission_details_handler = CallbackQueryHandler(show_guild_mission_details, pattern=r'^clan_mission_details$')
clan_mission_accept_handler = CallbackQueryHandler(start_mission_callback, pattern=r'^gld_start_hunt:')
clan_mission_finish_handler = CallbackQueryHandler(finish_mission_callback, pattern=r'^gld_mission_finish$')
clan_mission_cancel_handler = CallbackQueryHandler(cancel_mission_callback, pattern=r'^gld_mission_cancel$')

async def placeholder_purchase(u, c): pass
clan_board_purchase_handler = CallbackQueryHandler(placeholder_purchase, pattern=r'^gld_buy_board$')