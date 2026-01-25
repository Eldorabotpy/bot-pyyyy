# handlers/guild/dashboard.py
# (VERSÃO FINAL: HUB CENTRAL + WAR ENGINE INTEGRADO + UI RENDERER)

import logging
from typing import Any, Dict, Optional, Tuple, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, clan_manager, file_ids
from modules.game_data.clans import CLAN_PRESTIGE_LEVELS
from modules.auth_utils import get_current_player_id
from ui.ui_renderer import render_photo_or_text

# Tenta importar o engine. Se falhar, define como None para tratamento posterior.
try:
    from modules import clan_war_engine
except ImportError:
    clan_war_engine = None

logger = logging.getLogger(__name__)

# ==============================================================================
# 0. HELPERS E UTILITÁRIOS
# ==============================================================================

def _sid(x: Any) -> str:
    return str(x) if x is not None else ""

async def _safe_answer(query, text: str = "", show_alert: bool = False):
    if not query: return
    try: await query.answer(text, show_alert=show_alert)
    except: pass

async def _show_loading_overlay(update: Update, context: ContextTypes.DEFAULT_TYPE, title: str):
    """Edita a mensagem rapidamente para mostrar que o bot está processando."""
    query = update.callback_query
    if not query: return
    try:
        txt = f"⏳ <b>{title}</b>..."
        # Tenta editar caption (se tiver foto) ou text
        if query.message.photo or query.message.video:
            await query.edit_message_caption(txt, parse_mode="HTML")
        else:
            await query.edit_message_text(txt, parse_mode="HTML")
    except: pass

async def _engine_call(fn_name: str, *args, **kwargs) -> Dict[str, Any]:
    """
    Wrapper seguro para chamadas ao clan_war_engine.
    Evita que o bot pare se o engine estiver offline ou com erro.
    """
    if clan_war_engine is None:
        return {"ok": False, "message": "Sistema de Guerra em manutenção (Engine offline)."}

    fn = getattr(clan_war_engine, fn_name, None)
    if not fn:
        # Se a função não existe, retornamos erro suave
        return {"ok": False, "message": f"Função {fn_name} não disponível."}

    try:
        # Suporta funções async e sync no engine
        res = fn(*args, **kwargs)
        if hasattr(res, "__await__"):
            res = await res
            
        # Normalização do retorno para garantir que sempre tenha 'ok'
        if isinstance(res, dict):
            if "ok" not in res:
                # Se tem 'season' ou 'success', assume ok=True, senão False
                res["ok"] = bool(res.get("success", True) if "season" in res else res.get("success", False))
            return res
        elif isinstance(res, bool):
            return {"ok": res}
        
        return {"ok": False, "message": "Retorno inválido do engine."}
        
    except Exception as e:
        logger.error(f"[DASHBOARD] Engine Error ({fn_name}): {e}")
        return {"ok": False, "message": f"Erro interno no comando de guerra: {e}"}

async def _require_clan_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Tuple[Optional[str], Optional[dict], Optional[dict], bool]:
    """
    Valida sessão, carrega dados e verifica se o jogador ainda é membro (Anti-Fantasma).
    Retorna: (user_id, player_data, clan_data, is_leader)
    """
    query = update.callback_query
    user_id = get_current_player_id(update, context)
    
    if not user_id:
        await _safe_answer(query, "Sessão expirada.", show_alert=True)
        return None, None, None, False

    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    
    if not clan_id:
        return str(user_id), pdata, None, False

    try:
        cdata = await clan_manager.get_clan(clan_id)
    except:
        cdata = None

    # Se o clã não existe mais no banco
    if not cdata:
        pdata["clan_id"] = None
        await player_manager.save_player_data(user_id, pdata)
        return str(user_id), pdata, None, False

    leader_id = str(cdata.get("leader_id", "0"))
    is_leader = (str(user_id) == leader_id)
    members = [str(x) for x in (cdata.get("members", []) or [])]

    # Verifica se o jogador está na lista de membros (ou é líder)
    if (not is_leader) and (str(user_id) not in members):
        # Anti-fantasma: remove clan_id do jogador
        pdata["clan_id"] = None
        await player_manager.save_player_data(user_id, pdata)
        await _safe_answer(query, "Você não faz mais parte deste clã.", show_alert=True)
        
        # Redireciona para criação (importação tardia para evitar ciclo)
        from handlers.guild import creation_search
        await creation_search.show_create_clan_menu(update, context)
        return None, None, None, False

    return str(user_id), pdata, cdata, is_leader

# ==============================================================================
# 0. HELPER DE RENDERIZAÇÃO COMPARTILHADO (EVITA IMPORT CIRCULAR)
# ==============================================================================
async def _render_clan_screen(update, context, clan_data, text, keyboard):
    """
    Função auxiliar usada por outros módulos (missions, upgrades) para renderizar
    telas mantendo o padrão visual do Dashboard.
    """
    media_fid = None
    if clan_data:
        media_fid = clan_data.get("logo_media_key")
    
    if not media_fid:
        media_fid = file_ids.get_file_id("img_clan_default")

    await render_photo_or_text(
        update, context, 
        text=text, 
        photo_file_id=media_fid, 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        scope="clan_dashboard", 
        allow_edit=True
    )

# ==============================================================================
# 1. ENTRY POINT & DASHBOARD
# ==============================================================================

async def adventurer_guild_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu principal: Redireciona para Dashboard ou Criação."""
    user_id, pdata, clan_data, _ = await _require_clan_member(update, context)
    
    if not user_id: return
    
    if clan_data:
        await show_clan_dashboard(update, context)
    else:
        from handlers.guild import creation_search
        await creation_search.show_create_clan_menu(update, context)

async def show_clan_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await _safe_answer(query)

    # 1. CORREÇÃO AQUI: Captura o 'pdata' (segundo retorno) em vez de ignorar com '_'
    user_id, pdata, clan_data, is_leader = await _require_clan_member(update, context)
    if not clan_data: return

    # 2. Define a região atual para o botão voltar funcionar
    current_region = pdata.get("current_location", "reino_eldora")

    # Dados Visuais
    clan_name = clan_data.get("display_name", "Clã")
    level = int(clan_data.get("prestige_level", 1) or 1)
    xp = int(clan_data.get("prestige_points", 0) or 0)
    
    lvl_info = CLAN_PRESTIGE_LEVELS.get(level, {})
    xp_needed = int(lvl_info.get("points_to_next_level", 1000))
    if xp_needed < 1: xp_needed = 1
    
    # Barra de XP
    percent = min(1.0, max(0.0, xp / xp_needed))
    filled = int(percent * 10)
    bar = "🟦" * filled + "⬜" * (10 - filled)

    members_count = len(clan_data.get("members", []))
    max_members = int(lvl_info.get("max_members", 10))
    
    # Texto
    text = (
        f"🛡️ <b>CLÃ: {clan_name.upper()}</b> [Nv. {level}]\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👥 <b>Membros:</b> {members_count}/{max_members}\n"
        f"💰 <b>Cofre:</b> {int(clan_data.get('bank', 0)):,} Ouro\n"
        f"💠 <b>Progresso:</b>\n"
        f"<code>[{bar}]</code> {xp}/{xp_needed} XP\n\n"
        f"📢 <b>Mural:</b> <i>{clan_data.get('mural_text', 'Juntos somos mais fortes!')}</i>"
    )

    keyboard = [
        [InlineKeyboardButton("📜 Missões", callback_data="clan_mission_details"),
         InlineKeyboardButton("🏦 Banco", callback_data="clan_bank_menu")],
        [InlineKeyboardButton("👥 Membros", callback_data="clan_view_members"),
         InlineKeyboardButton("✨ Melhorias", callback_data="clan_upgrade_menu")],
        [InlineKeyboardButton("⚔️ Guerra de Clãs", callback_data="clan_war_menu")],
    ]

    if is_leader:
        keyboard.append([InlineKeyboardButton("👑 Gerir Clã", callback_data="clan_manage_menu")])

    # 3. Agora a variável current_region existe e o botão funciona
    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data=f"open_region:{current_region}")])

    await _render_clan_screen(update, context, clan_data, text, keyboard)

# ==============================================================================
# 2. GUERRA DE CLÃS (Lógica Avançada no Dashboard)
# ==============================================================================

async def show_clan_war_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu principal de Guerra com lógica de Engine integrada."""
    query = update.callback_query
    if query: await _safe_answer(query)

    user_id, pdata, clan_data, is_leader = await _require_clan_member(update, context)
    if not clan_data: return

    clan_id = str(pdata.get("clan_id"))
    clan_name = clan_data.get("display_name", "Clã")

    # 1. Pega Status do Engine
    ws = await _engine_call("get_war_status")
    season = ws.get("season", {}) or {}
    
    phase = str(season.get("phase", "PREP")).upper()
    season_id = str(season.get("season_id") or season.get("campaign_id") or "?")
    
    # Região Alvo
    region_id = season.get("target_region_id")
    region_name = str(region_id).replace("_", " ").title() if region_id else "Desconhecida"
    
    # Inscrição Aberta?
    is_open = bool(season.get("signup_open", False))

    # 2. Verifica Inscrição do Clã e do Jogador
    clan_registered = False
    me_registered = False
    reg_count = 0
    
    try:
        # Tenta pegar dados de inscrição
        signup_data = await _engine_call("get_clan_signup", season_id, clan_id)
        if signup_data.get("ok"):
            clan_registered = True
            members = signup_data.get("members", [])
            reg_count = len(members)
            if str(user_id) in members:
                me_registered = True
    except:
        pass 

    # 3. Score
    score_data = await _engine_call("get_clan_weekly_score", clan_id)
    total_pts = score_data.get("total", 0)

    # TEXTO
    text = (
        f"⚔️ <b>GUERRA DE CLÃS — {clan_name.upper()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>Rodada:</b> <code>{season_id}</code>\n"
        f"⏳ <b>Fase:</b> <b>{phase}</b>\n"
        f"📍 <b>Região Alvo:</b> {region_name}\n\n"
        f"📝 <b>Inscrição:</b> {'🟢 ABERTA' if is_open else '🔴 FECHADA'}\n"
        f"🏷️ <b>Clã:</b> {'✅ INSCRITO' if clan_registered else '❌ NÃO INSCRITO'}\n"
        f"👥 <b>Membros Prontos:</b> {reg_count}\n"
        f"👤 <b>Você:</b> {'✅ PRONTO' if me_registered else '❌ NÃO INSCRITO'}\n\n"
        f"⭐ <b>Pontos da Semana:</b> {total_pts}"
    )

    keyboard = []

    # AÇÕES DISPONÍVEIS (Baseado na Fase)
    if phase == "PREP":
        if is_leader:
            # Líder gerencia inscrição do CLÃ
            if not clan_registered:
                keyboard.append([InlineKeyboardButton("🏷️ Inscrever Clã", callback_data="clan_war_register_clan")])
            
            # Líder abre/fecha inscrição para MEMBROS
            if not is_open:
                keyboard.append([InlineKeyboardButton("🔓 Abrir Vagas", callback_data="clan_war_open")])
            else:
                keyboard.append([InlineKeyboardButton("🔒 Fechar Vagas", callback_data="clan_war_close")])
        
        # Membros entram/saem se estiver aberto e clã inscrito
        if is_open and clan_registered:
            if not me_registered:
                keyboard.append([InlineKeyboardButton("✅ Participar da Guerra", callback_data="clan_war_join")])
            else:
                keyboard.append([InlineKeyboardButton("❌ Sair da Lista", callback_data="clan_war_leave")])
        
        if not clan_registered:
            text += "\n\n⚠️ <i>O Líder precisa inscrever o clã para os membros participarem.</i>"

    elif phase == "ACTIVE":
        text += "\n\n🔥 <b>A GUERRA COMEÇOU!</b>\nPontue atacando na região alvo ou em PVP."

    # Navegação
    # Se clicar em Ranking, vai para o war.py (visualização)
    target_rank_callback = f"war_view:{region_id}" if region_id else "clan_noop"
    keyboard.append([InlineKeyboardButton("🏆 Ranking da Região", callback_data=target_rank_callback)])
    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="clan_menu")])

    # Mídia de Guerra
    media_fid = file_ids.get_file_id("img_war_default")
    if not media_fid and clan_data: media_fid = clan_data.get("logo_media_key")

    await render_photo_or_text(
        update, context, text, media_fid, 
        InlineKeyboardMarkup(keyboard), 
        scope="clan_war_menu", allow_edit=True
    )

# --- AÇÕES DE GUERRA (Chamadas pelo Router) ---

async def clan_war_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _show_loading_overlay(update, context, "Abrindo Vagas")
    # Tenta definir status no engine
    await _engine_call("set_signup_status", open=True) 
    await show_clan_war_menu(update, context)

async def clan_war_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _show_loading_overlay(update, context, "Fechando Vagas")
    await _engine_call("set_signup_status", open=False)
    await show_clan_war_menu(update, context)

async def clan_war_register_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await _show_loading_overlay(update, context, "Inscrevendo Clã")
    
    user_id, _, _, is_leader = await _require_clan_member(update, context)
    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")

    if is_leader:
        res = await _engine_call("register_clan_for_war", clan_id, str(user_id))
        if not res.get("ok"):
            await _safe_answer(query, f"Erro: {res.get('message', 'Falha ao inscrever.')}", show_alert=True)
        else:
            await _safe_answer(query, "Clã inscrito com sucesso!", show_alert=True)
    
    await show_clan_war_menu(update, context)

async def clan_war_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await _show_loading_overlay(update, context, "Entrando na Lista")
    
    user_id, _, _, _ = await _require_clan_member(update, context)
    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")

    res = await _engine_call("member_join_war", clan_id, str(user_id))
    if not res.get("ok"):
         await _safe_answer(query, f"Erro: {res.get('message', 'Falha ao entrar.')}", show_alert=True)
    
    await show_clan_war_menu(update, context)

async def clan_war_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await _show_loading_overlay(update, context, "Saindo da Lista")
    
    user_id, _, _, _ = await _require_clan_member(update, context)
    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")

    await _engine_call("member_leave_war", clan_id, str(user_id))
    await show_clan_war_menu(update, context)

async def clan_war_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a lista de membros inscritos na guerra."""
    query = update.callback_query
    await _show_loading_overlay(update, context, "Carregando Lista")
    
    user_id, pdata, clan_data, _ = await _require_clan_member(update, context)
    if not clan_data: return

    clan_id = str(pdata.get("clan_id"))
    
    # Busca dados do engine
    res = await _engine_call("get_clan_signup", None, clan_id)
    
    text = "📋 <b>LISTA DE INSCRITOS</b>\n━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not res.get("ok") or not res.get("members"):
        text += "<i>Nenhum membro inscrito ou erro ao buscar dados.</i>"
    else:
        members = res.get("members", [])
        count = len(members)
        text += f"👥 <b>Total: {count} guerreiros prontos.</b>\n\n"
        
        # Lista simplificada (apenas contagem e IDs se não tiver nomes cacheados)
        # Em produção, você pode cruzar os IDs com o player_manager para pegar nomes
        text += "<i>Use 'Participar' no menu anterior para se juntar à lista.</i>"

    keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data="clan_war_menu")]]
    
    # Usa o renderizador visual
    media_fid = clan_data.get("logo_media_key") or file_ids.get_file_id("img_war_default")
    await render_photo_or_text(
        update, context, text, media_fid, 
        InlineKeyboardMarkup(keyboard), 
        scope="clan_war_view", allow_edit=True
    )
    
# ==============================================================================
# 3. ROUTER CENTRAL (Distribui para todos os arquivos)
# ==============================================================================

async def clan_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Central de comando. Importa os handlers específicos aqui dentro
    para evitar erros de importação circular com o dashboard.
    """
    query = update.callback_query
    if not query: return
    action = query.data

    # --- IMPORTAÇÕES TARDIAS (CRUCIAL) ---
    from handlers.guild import (
        management, 
        missions, 
        bank, 
        upgrades, 
        war, 
        creation_search
    )

    # --- DASHBOARD & GUERRA (Local) ---
    if action == "clan_menu":
        await show_clan_dashboard(update, context)
        return
    if action == "clan_war_menu":
        await show_clan_war_menu(update, context)
        return
    if action == "clan_war_open": await clan_war_open(update, context); return
    if action == "clan_war_close": await clan_war_close(update, context); return
    if action == "clan_war_register_clan": await clan_war_register_clan(update, context); return
    if action == "clan_war_join": await clan_war_join(update, context); return
    if action == "clan_war_leave": await clan_war_leave(update, context); return
    
    # Redireciona visualização de ranking para o war.py (arquivo visual)
    if action.startswith("war_view:"):
        await war.show_region_ranking(update, context)
        return

    # --- BANCO ---
    if action == "clan_bank_menu":
        await bank.show_clan_bank_menu(update, context)
        return
    if action.startswith("clan_deposit") or action.startswith("clan_withdraw"):
        # Depósito é via ConversationHandler no main, mas aqui tratamos cliques soltos redirecionando
        await bank.show_clan_bank_menu(update, context)
        return

    # --- MISSÕES ---
    if action == "clan_mission_details":
        await missions.show_guild_mission_details(update, context)
        return
    if action.startswith("gld_mission_") or action.startswith("gld_start_hunt"):
        if "finish" in action: await missions.finish_mission_callback(update, context)
        elif "cancel" in action: await missions.cancel_mission_callback(update, context)
        elif "select" in action: await missions.show_mission_selection_menu(update, context)
        elif "hunt" in action: await missions.start_mission_callback(update, context)
        return

    # --- MELHORIAS ---
    if action == "clan_upgrade_menu":
        await upgrades.show_clan_upgrade_menu(update, context)
        return
    if action.startswith("clan_upgrade_confirm"):
        await upgrades.confirm_clan_upgrade_callback(update, context)
        return

    # --- GESTÃO & MEMBROS ---
    if action == "clan_manage_menu":
        await management.show_clan_management_menu(update, context)
        return
    if action in ["clan_view_members", "gld_view_members"]:
        await management.show_members_list(update, context)
        return
    if action.startswith("clan_profile:"):
        await management.show_member_profile(update, context)
        return
    
    # Prefixos de Gestão
    if action.startswith("clan_kick_") or action.startswith("clan_leave_") or action.startswith("clan_delete_"):
        if "kick_ask" in action: await management.warn_kick_member(update, context)
        elif "kick_do" in action: await management.do_kick_member(update, context)
        elif "leave_ask" in action: await management.warn_leave_clan(update, context)
        elif "leave_perform" in action: await management.do_leave_clan(update, context)
        elif "delete_ask" in action: await management.warn_delete_clan(update, context)
        elif "delete_confirm" in action: await management.perform_delete_clan(update, context)
        return
        
    if action.startswith("clan_cleanup_"):
        if "menu" in action: await management.show_cleanup_menu(update, context)
        elif "apps" in action: await management.do_cleanup_apps(update, context)
        elif "members" in action: await management.do_cleanup_members(update, context)
        return
        
    if action.startswith("clan_setrank_") or action.startswith("clan_do_rank"):
        if "menu" in action: await management.show_rank_selection_menu(update, context)
        else: await management.perform_rank_change(update, context)
        return

    # --- CRIAÇÃO & BUSCA ---
    if action == "clan_create_menu_start":
        await creation_search.show_create_clan_menu(update, context)
        return
    if action.startswith("clan_manage_apps") or action.startswith("clan_app_"):
        if "manage" in action: await creation_search.show_applications_menu(update, context)
        elif "accept" in action: await creation_search.accept_application_callback(update, context)
        elif "decline" in action: await creation_search.decline_application_callback(update, context)
        return

    if action == "clan_noop":
        await _safe_answer(query)
        return

    await _safe_answer(query, "Opção indisponível.", show_alert=True)

# Handler principal
clan_handler = CallbackQueryHandler(clan_router, pattern=r"^clan_|^gld_|^war_|^clan_menu$")
