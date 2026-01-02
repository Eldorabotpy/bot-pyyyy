# handlers/admin/grant_skill.py
# (VERSÃO FINAL: Compatível com IDs Híbridos/String)

import logging
import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from modules import player_manager
from modules.game_data.skills import SKILL_DATA 

# [IMPORT NOVO] Necessário para identificar o admin corretamente no sistema novo
from modules.auth_utils import get_current_player_id

from handlers.admin.utils import (
    ADMIN_LIST,
    confirmar_jogador,
    jogador_confirmado,
    cancelar_conversa,
    INPUT_TEXTO,
    CONFIRMAR_JOGADOR,
)

logger = logging.getLogger(__name__)

SKILLS_PER_PAGE = 8 
(SHOW_CATALOG, CONFIRMAR_GRANT) = range(2, 4) 
ASK_PLAYER = INPUT_TEXTO  

async def grant_skill_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ponto de entrada: Pede o ID ou Nome do jogador."""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "📚 <b>Ensinar Habilidade (Skill)</b>\n\n"
        "Envie o ID (número) ou o Nome exato do personagem que receberá a habilidade.\n\n"
        "Use /cancelar para sair.",
        parse_mode="HTML"
    )
    return ASK_PLAYER 

async def show_skill_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1) -> int:
    """
    Jogador foi confirmado. Mostra o catálogo de skills paginado.
    """

    try:
        sorted_skills = sorted(
            SKILL_DATA.items(), 
            key=lambda item: item[1].get('display_name', item[0])
        )
    except Exception as e:
        logger.error(f"Erro ao ordenar SKILL_DATA: {e}")
        sorted_skills = list(SKILL_DATA.items())

    start_index = (page - 1) * SKILLS_PER_PAGE
    end_index = start_index + SKILLS_PER_PAGE
    paginated_skills = sorted_skills[start_index:end_index]
    
    total_pages = math.ceil(len(sorted_skills) / SKILLS_PER_PAGE)

    keyboard = []
    for skill_id, skill_info in paginated_skills:
        skill_name = skill_info.get('display_name', skill_id)
        skill_type = skill_info.get('type', 'N/A')[0].upper() # Pega a primeira letra (P)assive, (A)ctive
        
        button_text = f"[{skill_type}] {skill_name}"
        callback_data = f"admin_gskill_select:{skill_id}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"admin_gskill_page:{page-1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("Próxima ➡️", callback_data=f"admin_gskill_page:{page+1}"))
    
    if nav_row:
        keyboard.append(nav_row)
        
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_admin_conv")])
    
    player_name = context.user_data['target_player_name']
    text = (
        f"Jogador: <code>{player_name}</code>\n"
        f"Selecione a Habilidade (Pág. {page}/{total_pages}):"
    )

    if update.callback_query and update.callback_query.data.startswith("admin_gskill_page"):
        await update.callback_query.edit_message_text(
            text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:

        await update.message.reply_text(
            text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    return SHOW_CATALOG 

async def skill_catalog_pager(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lida com os botões 'Anterior' e 'Próxima'."""
    await update.callback_query.answer()
    page = int(update.callback_query.data.split(':')[-1])
    await show_skill_catalog(update, context, page=page)
    return SHOW_CATALOG

async def select_skill_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin clicou numa skill. Valida e pede confirmação."""
    await update.callback_query.answer()
    skill_id = update.callback_query.data.split(':')[-1]

    skill_info = SKILL_DATA.get(skill_id)
    if not skill_info:
        await update.callback_query.answer("Erro: Skill não encontrada.", show_alert=True)
        return SHOW_CATALOG

    context.user_data['target_skill_id'] = skill_id
    
    target_player_name = context.user_data['target_player_name']
    skill_name = skill_info.get('display_name', skill_id)
    skill_type = skill_info.get('type', 'desconhecido').capitalize()

    text = (
        f"<b>Confirmação Final</b>\n\n"
        f"Jogador: <code>{target_player_name}</code>\n"
        f"Habilidade: <code>{skill_name}</code> (Tipo: <code>{skill_type}</code>)\n\n"
        f"Você confirma?"
    )
    keyboard = [
        [InlineKeyboardButton("✅ Sim, ensinar", callback_data="confirm_grant_skill")],
        [InlineKeyboardButton("⬅️ Voltar ao Catálogo", callback_data="back_to_skill_catalog")],
    ]
    await update.callback_query.edit_message_text(
        text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRMAR_GRANT 

async def grant_skill_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """O admin confirmou. Adiciona a skill ao jogador."""
    await update.callback_query.answer()
    
    user_id = context.user_data['target_user_id']
    skill_id = context.user_data['target_skill_id']
    target_player_name = context.user_data['target_player_name']
    
    try:
        player_data = await player_manager.get_player_data(user_id)
        if not player_data:
            await update.callback_query.edit_message_text("Erro: O jogador alvo desapareceu. Ação cancelada.")
            return ConversationHandler.END

        # Define 'skills' como um dicionário
        player_skills = player_data.setdefault("skills", {})

        # Salvaguarda de migração (se o admin mexer num player antigo)
        if not isinstance(player_skills, dict):
            logger.warning(f"Admin grant_skill: Migrando 'skills' (era lista) para {user_id}...")
            # Converte a lista antiga para o dicionário novo (com progress)
            new_skills_dict = {sid: {"rarity": "comum", "progress": 0} for sid in player_skills if sid}
            player_data["skills"] = new_skills_dict
            player_skills = new_skills_dict

        # Verifica se a CHAVE da skill já existe
        if skill_id not in player_skills:
            # Adiciona a skill no novo formato de dicionário (com progress)
            player_skills[skill_id] = {"rarity": "comum", "progress": 0}
        else:
            await update.callback_query.edit_message_text(
                f"Aviso: <code>{target_player_name}</code> já conhecia a skill <code>{skill_id}</code>.",
                parse_mode="HTML"
            )
            return ConversationHandler.END

        await player_manager.save_player_data(user_id, player_data)
        skill_name = SKILL_DATA.get(skill_id, {}).get('display_name', skill_id)
        
        await update.callback_query.edit_message_text(
            f"✅ Sucesso!\n\n"
            f"O jogador <code>{target_player_name}</code> aprendeu <b>{skill_name}</b>!",
            parse_mode="HTML"
        )
        
        # [CORREÇÃO] Comparação segura de IDs (Admin vs Alvo)
        # Usamos get_current_player_id para garantir compatibilidade com o sistema novo
        admin_id = get_current_player_id(update, context)
        
        # Comparamos como string para evitar erro Int vs ObjectId
        if str(user_id) != str(admin_id):
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📚 Você aprendeu uma nova habilidade: <b>{skill_name}</b>!",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    except Exception as e:
        await update.callback_query.edit_message_text(f"Ocorreu um erro grave: {e}")

    context.user_data.clear()
    return ConversationHandler.END

async def back_to_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Volta da confirmação para o catálogo."""
    await update.callback_query.answer()
    await show_skill_catalog(update, context, page=1)
    return SHOW_CATALOG

grant_skill_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(grant_skill_entry, pattern=r"^admin_grant_skill$")],
    states={
        ASK_PLAYER: [ 
            MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_LIST), confirmar_jogador(show_skill_catalog))
        ],
        CONFIRMAR_JOGADOR: [ 
             CallbackQueryHandler(jogador_confirmado(show_skill_catalog), pattern=r"^confirm_player_")
        ],
        SHOW_CATALOG: [ 
            CallbackQueryHandler(select_skill_callback, pattern=r"^admin_gskill_select:"),
            CallbackQueryHandler(skill_catalog_pager, pattern=r"^admin_gskill_page:"),
        ],
        CONFIRMAR_GRANT: [ 
            CallbackQueryHandler(grant_skill_confirmed, pattern=r"^confirm_grant_skill$"),
            CallbackQueryHandler(back_to_catalog, pattern=r"^back_to_skill_catalog$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancelar", cancelar_conversa, filters=filters.User(ADMIN_LIST)),
        CallbackQueryHandler(cancelar_conversa, pattern=r"^cancelar_admin_conv$"),
    ],
    per_message=False
)