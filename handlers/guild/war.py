# handlers/guild/war.py
# (VERSÃO CORRIGIDA: UI RENDERER + IMERSÃO VISUAL)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, clan_manager, clan_war_engine, game_data, file_ids
from modules.auth_utils import get_current_player_id
from ui.ui_renderer import render_photo_or_text

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

    # 🔒 SEGURANÇA: Validação de Sessão e Clã
    user_id = get_current_player_id(update, context)
    if not user_id:
        return # Auth handler trata

    player_data = await player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")
    
    if not clan_id:
        await render_photo_or_text(update, context, "❌ Você precisa de um clã para acessar a guerra.", None)
        return

    clan_data = await clan_manager.get_clan(clan_id)
    if not clan_data:
        await render_photo_or_text(update, context, "❌ Clã não encontrado.", None)
        return

    # --- LÓGICA DO JOGO ---
    try:
        mode = clan_war_engine.get_current_war_mode()
    except Exception:
        mode = "PVE" # Fallback

    clan_name = clan_data.get('display_name', 'Clã')
    
    if mode == "PVP":
        header = f"🔥 <b>GUERRA DE SANGUE (PvP)</b>\nClã: {clan_name}\n━━━━━━━━━━━━━━━━━━━\n<i>Ataque jogadores rivais para pontuar!</i>"
    else:
        header = f"🌲 <b>DOMINAÇÃO (PvE)</b>\nClã: {clan_name}\n━━━━━━━━━━━━━━━━━━━\n<i>Cace monstros nas regiões para pontuar!</i>"

    text = (
        f"{header}\n\n"
        f"🗺️ <b>Territórios em Disputa:</b>\n"
        f"<i>Selecione uma região para ver o ranking:</i>"
    )

    # --- GRID DE BOTÕES (2 por linha) ---
    keyboard = []
    row = []
    for reg_key in WAR_REGIONS:
        # Busca nome bonito no game_data ou formata a string
        reg_info = (getattr(game_data, "REGIONS_DATA", None) or {}).get(reg_key, {})
        name = reg_info.get("display_name", reg_key.replace("_", " ").title())

        row.append(InlineKeyboardButton(f"📍 {name}", callback_data=f"war_view:{reg_key}"))
        
        if len(row) == 2:
            keyboard.append(row)
            row = []
            
    if row: keyboard.append(row)

    # Botões de Navegação
    keyboard.append([InlineKeyboardButton("⚔️ Minha Pontuação", callback_data="clan_war_menu")]) # Reuso do menu dashboard se quiser
    keyboard.append([InlineKeyboardButton("🔙 Voltar ao Clã", callback_data="clan_menu")])

    # Renderiza com UI System
    await _render_war_screen(update, context, clan_data, text, keyboard)


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


# ==============================================================================
# HANDLERS
# ==============================================================================
# Nota: 'clan_war_menu' já é capturado no router do dashboard.py. 
# Aqui registramos apenas os callbacks específicos internos ou alternativos.

war_menu_handler = CallbackQueryHandler(show_war_menu, pattern=r"^war_menu$")
war_ranking_handler = CallbackQueryHandler(show_region_ranking, pattern=r"^war_view:")