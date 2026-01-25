# handlers/guild/war.py
# (VERSÃO CORRIGIDA: UI RENDERER + IMERSÃO VISUAL)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, clan_manager, clan_war_engine, game_data, file_ids
from modules.auth_utils import get_current_player_id
from ui.ui_renderer import render_photo_or_text
from modules.clan_war_engine import get_war_targets_in_region, check_war_attack_cooldown

logger = logging.getLogger(__name__)

# Regiões fixas (conforme seu código original)
WAR_REGIONS = [
    "floresta_sombria",
    "pedreira_granito",
    "mina_ferro",
    "pantano_maldito",
    "pico_grifo"
]

# ==============================================================================
# HELPERS VISUAIS
# ==============================================================================

def _pick_war_media(clan_data, region_key=None):
    """
    Seleciona a melhor imagem para mostrar:
    1. Se for menu de região: Tenta imagem da região.
    2. Se for menu principal: Tenta logo do clã ou imagem genérica de guerra.
    """
    # 1. Tenta imagem específica da região
    if region_key:
        try:
            # Ex: img_region_floresta_sombria
            fid = file_ids.get_file_id(f"img_region_{region_key}")
            if fid: return fid
        except: pass

    # 2. Tenta logo do clã (se configurado)
    if clan_data and clan_data.get("logo_media_key"):
        return clan_data.get("logo_media_key")

    # 3. Fallback: Imagem padrão de clã ou guerra
    try:
        return file_ids.get_file_id("img_war_default") or file_ids.get_file_id("img_clan_default")
    except:
        return None

async def _render_war_screen(update, context, clan_data, text, keyboard, region_key=None):
    """Encapsula o ui_renderer para manter o padrão visual do Dashboard."""
    media_id = _pick_war_media(clan_data, region_key)
    
    await render_photo_or_text(
        update,
        context,
        text=text,
        photo_file_id=media_id,
        reply_markup=InlineKeyboardMarkup(keyboard),
        scope="clan_war_screen",  # Mantém o scope para edição fluida
        parse_mode="HTML",
        allow_edit=True
    )

# ==============================================================================
# 1. MENU PRINCIPAL DE GUERRA
# ==============================================================================
async def show_war_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()

    # 1. Validações Básicas
    user_id = get_current_player_id(update, context)
    if not user_id: return

    pdata = await player_manager.get_player_data(user_id)
    clan_id = pdata.get("clan_id")
    
    if not clan_id:
        await render_photo_or_text(update, context, "❌ Você precisa de um clã.", None)
        return

    cdata = await clan_manager.get_clan(clan_id)
    if not cdata: return

    # 2. Dados da Guerra
    ws = await clan_war_engine.get_war_status()
    season = ws.get("season", {})
    target_region = season.get("target_region_id")
    phase = str(season.get("phase", "PREP"))
    
    # Nome bonito da região
    reg_info = (getattr(game_data, "REGIONS_DATA", None) or {}).get(target_region, {})
    target_name = reg_info.get("display_name", str(target_region).title())

    # 3. Textos do Menu
    clan_name = cdata.get('display_name', 'Clã')
    text = (
        f"⚔️ <b>CENTRAL DE GUERRA: {clan_name}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📍 <b>Front de Batalha:</b> {target_name}\n"
        f"⏳ <b>Status:</b> {phase}\n\n"
        f"<i>Selecione uma região para ver o domínio territorial:</i>"
    )

    # 4. Grid de Regiões (Padrão)
    keyboard = []
    row = []
    for reg_key in WAR_REGIONS:
        r_name = (getattr(game_data, "REGIONS_DATA", None) or {}).get(reg_key, {}).get("display_name", reg_key)
        # Marca com um ícone se for a região alvo
        icon = "🔥" if reg_key == target_region else "📍"
        row.append(InlineKeyboardButton(f"{icon} {r_name}", callback_data=f"war_view:{reg_key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row: keyboard.append(row)

    # --- AQUI ESTÁ A MÁGICA DO BOTÃO ---
    
    # A) Verifica se a guerra está ativa
    if phase == "ACTIVE":
        # B) Verifica se o jogador está NA REGIÃO DA GUERRA
        player_location = pdata.get("current_location")
        
        # C) Verifica se é HORÁRIO DE PVP (Chama a função que criamos no Passo 1)
        is_pvp_time = await clan_war_engine.is_war_pvp_active()
        
        if player_location == target_region:
            if is_pvp_time:
                # TUDO CERTO: Mostra o botão
                keyboard.append([InlineKeyboardButton("🔭 BUSCAR OPONENTES (PvP)", callback_data="war_search_targets")])
            else:
                # Opcional: Mostra botão desativado ou mensagem informativa
                text += "\n\n🛡️ <i>O PvP está inativo neste horário. Foque em caçar monstros!</i>"
        else:
            # Avisa que ele precisa viajar
            text += f"\n\n⚠️ <i>Viaje para <b>{target_name}</b> para ver as opções de combate.</i>"

    # -----------------------------------

    keyboard.append([InlineKeyboardButton("🏆 Ranking da Semana", callback_data=f"war_view:{target_region}")])
    keyboard.append([InlineKeyboardButton("🔙 Voltar", callback_data="clan_menu")])

    await _render_war_screen(update, context, cdata, text, keyboard)


# ==============================================================================
# 2. RANKING DA REGIÃO
# ==============================================================================
async def show_region_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()

    # 🔒 Validação Rápida (para pegar o logo do clã pro render)
    user_id = get_current_player_id(update, context)
    clan_data = None
    if user_id:
        pdata = await player_manager.get_player_data(user_id)
        if pdata.get("clan_id"):
            clan_data = await clan_manager.get_clan(pdata["clan_id"])

    try:
        region_key = query.data.split(":")[1]
    except:
        return

    # Metadados da Região
    reg_info = (getattr(game_data, "REGIONS_DATA", None) or {}).get(region_key, {})
    reg_name = reg_info.get("display_name", region_key.replace("_", " ").title())

    # Busca Leaderboard
    try:
        leaderboard = await clan_war_engine.get_region_leaderboard(region_key)
    except Exception as e:
        logger.error(f"Erro leaderboard: {e}")
        leaderboard = []

    text = f"🚩 <b>DOMÍNIO: {reg_name.upper()}</b>\n━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not leaderboard:
        text += "<i>Nenhum clã conquistou pontos aqui ainda.\nSeja o primeiro a marcar território!</i>"
    else:
        medals = ["🥇", "🥈", "🥉"]
        text += "🏆 <b>Clãs Dominantes:</b>\n"
        
        for idx, entry in enumerate(leaderboard[:10]):
            rank_icon = medals[idx] if idx < 3 else f"<b>{idx+1}º</b>"
            c_name = entry.get("clan_name", "Clã Desconhecido")
            pts = entry.get("points", 0)
            
            # Destaque se for o clã do jogador
            if clan_data and c_name == clan_data.get('display_name'):
                text += f"👉 {rank_icon} <b>{c_name}</b>: {pts} pts\n"
            else:
                text += f"{rank_icon} <b>{c_name}</b>: {pts} pts\n"

    text += "\n<i>Pontue derrotando inimigos ou jogadores nesta região!</i>"

    keyboard = [[InlineKeyboardButton("🔙 Mapa de Guerra", callback_data="war_menu")]]
    
    # Renderiza passando a region_key para tentar pegar a foto da região
    await _render_war_screen(update, context, clan_data, text, keyboard, region_key=region_key)

async def show_war_targets_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = get_current_player_id(update, context)
    
    # 1. Valida Cooldown do Atacante (5 min)
    cd_left = await check_war_attack_cooldown(user_id)
    if cd_left:
        minutes = int(cd_left // 60)
        seconds = int(cd_left % 60)
        await query.answer(f"⏳ Descance! Aguarde {minutes}m {seconds}s para atacar novamente.", show_alert=True)
        return

    # 2. Pega Região Atual do Jogador
    pdata = await player_manager.get_player_data(user_id)
    current_region = pdata.get("current_location")
    
    # Valida se está na região da guerra
    ws = await clan_war_engine.get_war_status()
    target_region = ws.get("season", {}).get("target_region_id")
    
    if current_region != target_region:
        await query.answer(f"❌ Você precisa estar em {target_region} para buscar alvos!", show_alert=True)
        return

    # 3. Busca Inimigos
    targets = await get_war_targets_in_region(user_id, current_region)
    
    if not targets:
        text = (
            f"🔭 <b>RADAR DE GUERRA: {target_region.replace('_',' ').title()}</b>\n\n"
            "<i>Nenhum inimigo inscrito encontrado nesta área no momento.</i>\n"
            "Eles podem estar escondidos ou offline."
        )
        kb = [[InlineKeyboardButton("🔄 Atualizar Radar", callback_data="war_search_targets")]]
    else:
        text = (
            f"⚔️ <b>INIMIGOS ENCONTRADOS!</b>\n"
            f"Região: {target_region.replace('_',' ').title()}\n"
            f"<i>Ataque para remover pontos do clã rival e bloquear o farm deles!</i>"
        )
        kb = []
        for t in targets:
            # Botão de Ataque (Chama o seu sistema de PvP)
            # O callback 'pvp_challenge:ID' deve ser o que o seu bot já usa pra duelo
            # Se não for, mude para chamar uma função nossa de guerra
            btn_txt = f"⚔️ {t['name']} (Nv.{t['level']})"
            kb.append([InlineKeyboardButton(btn_txt, callback_data=f"war_attack:{t['user_id']}")])
            
        kb.append([InlineKeyboardButton("🔄 Atualizar Lista", callback_data="war_search_targets")])

    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="war_menu")])
    
    # Renderiza
    await _render_war_screen(update, context, None, text, kb, region_key=target_region)

# ==============================================================================
# HANDLERS
# ==============================================================================
# Nota: 'clan_war_menu' já é capturado no router do dashboard.py. 
# Aqui registramos apenas os callbacks específicos internos ou alternativos.

war_menu_handler = CallbackQueryHandler(show_war_menu, pattern=r"^war_menu$")
war_ranking_handler = CallbackQueryHandler(show_region_ranking, pattern=r"^war_view:")
war_search_handler = CallbackQueryHandler(show_war_targets_menu, pattern=r"^war_search_targets$")
