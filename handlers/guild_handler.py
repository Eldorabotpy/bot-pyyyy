# handlers/guild_handler.py
# (VERSÃO FINAL: DASHBOARD VISUAL + ROTEAMENTO DE HANDLERS + DELETAR CLÃ)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, file_ids

# Tenta importar o gerenciador de clã
try:
    from modules import clan_manager
except ImportError:
    clan_manager = None

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. FUNÇÃO VISUAL: DASHBOARD DO CLÃ
# ==============================================================================

async def show_clan_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE, came_from=None):
    """
    Exibe o painel principal do Clã (Dashboard).
    """
    query = update.callback_query
    if query: await query.answer()
    
    user_id = update.effective_user.id
    
    # Busca dados do jogador
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        return

    clan_id = player_data.get("clan_id")
    
    # Se não tem clã, redireciona para criação/busca
    if not clan_id:
        from handlers.guild.creation_search import show_create_clan_menu
        await show_create_clan_menu(update, context, came_from='guild_menu')
        return

    # --- DADOS DO CLÃ ---
    clan_name = "Clã Desconhecido"
    clan_lvl = 1
    clan_xp = 0
    clan_xp_next = 1000
    clan_gold = 0
    members_count = 1
    max_members = 10
    
    if clan_manager:
        # Tenta buscar dados reais
        try:
            cdata = await clan_manager.get_clan(clan_id)
            if cdata:
                clan_name = cdata.get("name") or cdata.get("display_name") or clan_name
                clan_lvl = cdata.get("prestige_level", clan_lvl)
                clan_xp = cdata.get("prestige_points", clan_xp)
                # Safe access to bank gold
                bank_data = cdata.get("bank", 0)
                clan_gold = bank_data.get("gold", 0) if isinstance(bank_data, dict) else bank_data
                
                m_list = cdata.get("members", [])
                members_count = len(m_list) if isinstance(m_list, list) else members_count
                
                # Tenta pegar max members da config se possível, senão usa padrão
                try:
                    from modules.game_data.clans import CLAN_PRESTIGE_LEVELS
                    level_info = CLAN_PRESTIGE_LEVELS.get(clan_lvl, {})
                    max_members = level_info.get("max_members", 10)
                except ImportError:
                    pass
        except Exception as e:
            logger.error(f"Erro ao ler dados do clã: {e}")

    # Barra de XP Visual
    ratio = 0
    if clan_xp_next > 0:
        ratio = min(1.0, max(0.0, clan_xp / clan_xp_next))
    filled = int(ratio * 10)
    bar = "🟦" * filled + "⬜" * (10 - filled)

    # Texto do Painel
    text = (
        f"🛡️ <b>CLÃ: {clan_name.upper()}</b> [Nv. {clan_lvl}]\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👥 <b>Membros:</b> {members_count}/{max_members}\n"
        f"💰 <b>Cofre:</b> {clan_gold:,} Ouro\n"
        f"💠 <b>Progresso:</b>\n"
        f"<code>[{bar}]</code> {clan_xp} XP\n\n"
        f"📢 <b>Mural:</b> <i>Juntos somos mais fortes!</i>"
    )

    # Botões Organizados
    keyboard = [
        [
            InlineKeyboardButton("👥 Membros", callback_data="clan_manage_menu"),
            InlineKeyboardButton("🏦 Banco", callback_data="clan_bank_menu")
        ],
        [
            InlineKeyboardButton("⚔️ Missões", callback_data="gld_clan_board"),
            InlineKeyboardButton("✨ Melhorias", callback_data="clan_upgrade_menu")
        ],
        # Botão para voltar à Instituição (NPC)
        [InlineKeyboardButton("🔙 Voltar à Guilda", callback_data="adventurer_guild_main")]
    ]

    # Envio com Mídia (Opcional)
    media_id = file_ids.get_file_id("img_clan_default") 
    
    if media_id:
        try:
            if query and query.message.photo:
                await query.edit_message_media(
                    media=InputMediaPhoto(media_id, caption=text, parse_mode="HTML"),
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                if query: await query.delete_message()
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id, 
                    photo=media_id, 
                    caption=text, 
                    reply_markup=InlineKeyboardMarkup(keyboard), 
                    parse_mode="HTML"
                )
            return
        except Exception:
            pass # Falha na mídia, cai para o texto

    # Envio Texto Puro (Fallback)
    try:
        if query:
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    except Exception:
        pass

# ==============================================================================
# 2. HANDLERS DE MENU (ROTEADORES)
# ==============================================================================

async def guild_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback genérico para abrir o menu do Clã."""
    await show_clan_dashboard(update, context)

async def clan_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback específico do botão do Clã."""
    await show_clan_dashboard(update, context)

# ==============================================================================
# 3. IMPORTAÇÃO E REGISTRO DOS SUB-HANDLERS
# ==============================================================================

# Definimos listas vazias caso a importação falhe para não quebrar o bot
sub_handlers = []

try:
    # 1. Criação e Busca
    from handlers.guild.creation_search import (
        clan_creation_conv_handler, clan_search_conv_handler, clan_apply_handler,
        clan_manage_apps_handler, clan_app_accept_handler, clan_app_decline_handler,
    )
    sub_handlers.extend([
        clan_creation_conv_handler, clan_search_conv_handler, clan_apply_handler,
        clan_manage_apps_handler, clan_app_accept_handler, clan_app_decline_handler
    ])

    # 2. Gestão (Management)
    from handlers.guild.management import (
        clan_transfer_leader_conv_handler, clan_logo_conv_handler, clan_manage_menu_handler,
        clan_kick_menu_handler, clan_kick_confirm_handler, clan_kick_do_handler,
        invite_conv_handler, 
        clan_delete_warn_handler, clan_delete_do_handler # <--- ADICIONADO AQUI: Handlers de Delete
    )
    sub_handlers.extend([
        clan_transfer_leader_conv_handler, clan_logo_conv_handler, clan_manage_menu_handler,
        clan_kick_menu_handler, clan_kick_confirm_handler, clan_kick_do_handler,
        invite_conv_handler,
        clan_delete_warn_handler, clan_delete_do_handler # <--- ADICIONADO AQUI TAMBÉM
    ])

    # 3. Missões
    from handlers.guild.missions import (
        missions_menu_handler, mission_claim_handler, mission_reroll_handler,
        clan_mission_start_handler, clan_board_purchase_handler,
        clan_guild_mission_details_handler,
        clan_mission_details_handler,
        clan_mission_preview_handler,
        clan_mission_accept_handler,
    )
    sub_handlers.extend([
        missions_menu_handler, mission_claim_handler, mission_reroll_handler,
        clan_mission_start_handler, clan_board_purchase_handler,
        clan_guild_mission_details_handler,
        clan_mission_details_handler,
        clan_mission_preview_handler,
        clan_mission_accept_handler
    ])

    # 4. Banco
    from handlers.guild.bank import (
        clan_bank_menu_handler, 
        clan_deposit_conv_handler, 
        clan_withdraw_conv_handler,
        clan_bank_log_handler,
    )
    sub_handlers.extend([
        clan_bank_menu_handler, clan_deposit_conv_handler, 
        clan_withdraw_conv_handler, clan_bank_log_handler
    ])

    # 5. Upgrades
    from handlers.guild.upgrades import (
        clan_upgrade_menu_handler, clan_upgrade_confirm_handler,
    )
    sub_handlers.extend([
        clan_upgrade_menu_handler, clan_upgrade_confirm_handler
    ])

except ImportError as e:
    logger.warning(f"⚠️ ALERTA: Alguns handlers de guilda falharam ao carregar: {e}")

# ==============================================================================
# 4. DEFINIÇÃO DOS HANDLERS LOCAIS
# ==============================================================================

guild_menu_handler = CallbackQueryHandler(guild_menu_callback, pattern=r'^guild_menu$')
clan_menu_handler = CallbackQueryHandler(clan_menu_callback, pattern=r"^clan_menu(:.*)?$")
noop_handler = CallbackQueryHandler(lambda u, c: c.bot.answer_callback_query(u.callback_query.id), pattern=r'^noop$')

# ==============================================================================
# 5. LISTA FINAL (EXPORTADA PARA O REGISTRIES)
# ==============================================================================

all_guild_handlers = [
    guild_menu_handler, 
    clan_menu_handler, 
    noop_handler
] + sub_handlers