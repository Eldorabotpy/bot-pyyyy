# handlers/status_handler.py (VERSÃO FINAL E CORRIGIDA)

import logging
import re
import unicodedata
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.error import BadRequest # <-- Importado corretamente

from modules import player_manager, game_data, file_ids

logger = logging.getLogger(__name__)

PROFILE_KEYS = ['max_hp', 'attack', 'defense', 'initiative', 'luck']

def _slugify(text: str) -> str:
    if not text: return ""
    # Normaliza, remove acentos, converte para minúsculas, substitui espaços, remove caracteres inválidos
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    norm = re.sub(r"[^\w\s-]", "", norm).strip().lower() # Permite hífens também
    norm = re.sub(r"[-\s]+", "_", norm) # Substitui hífens e espaços por underscore
    return norm

def _get_class_media(player_data: dict, purpose: str = "status"):
    """Busca a mídia (video/foto) associada à classe do jogador."""
    raw_cls = (player_data.get("class") or "").strip()
    # Usa a classe base se for uma subclasse (ex: Guerreiro -> guerreiro)
    base_cls_key = raw_cls.lower() # Adapte se sua estrutura de dados for diferente
    cls_slug = _slugify(base_cls_key) # Usa slugify para consistência

    # Tenta buscar config da classe (pode não existir se for classe base)
    classes_data = getattr(game_data, "CLASSES_DATA", {}) or {}
    cls_cfg = classes_data.get(raw_cls) or classes_data.get(base_cls_key) or {}

    # Lista de chaves candidatas para procurar no file_ids
    candidates = []
    # 1. Chave específica definida na config da classe (se houver)
    if cls_cfg.get("status_file_id_key"):
         candidates.append(cls_cfg["status_file_id_key"])
    # 2. Nomes padronizados baseados no slug da classe
    if cls_slug:
        candidates.extend([
            f"status_video_{cls_slug}", # status_video_guerreiro
            f"status_{cls_slug}",      # status_guerreiro
            f"class_{cls_slug}_status", # class_guerreiro_status
            f"classe_{cls_slug}_media" # classe_guerreiro_media (do seu código original)
        ])
    # 3. Fallback genérico
    candidates.append("status_video") # status_video (genérico)

    # Procura a primeira chave válida no file_ids
    for key in filter(None, candidates): # filter(None, ...) remove chaves vazias/nulas
        fd = file_ids.get_file_data(key)
        if fd and fd.get("id"):
            logger.info(f"Mídia de status encontrada para classe '{raw_cls}' (slug: '{cls_slug}') usando a chave: '{key}'")
            return fd # Retorna o primeiro encontrado
    logger.warning(f"Nenhuma mídia de status encontrada para classe '{raw_cls}' (slug: '{cls_slug}'). Chaves tentadas: {candidates}")
    return None # Retorna None se nada for encontrado

def _get_status_content(player_data: dict) -> tuple[str, InlineKeyboardMarkup]:
    """Gera o texto e o teclado do menu de status."""
    total_stats = player_manager.get_player_total_stats(player_data)
    char_name = player_data.get('character_name', 'Aventureiro(a)')
    status_text = f"👤 <b>Status de {char_name}</b>\n\n"
    emoji_map = {'max_hp': '❤️', 'attack': '⚔️', 'defense': '🛡️', 'initiative': '🏃', 'luck': '🍀'}
    name_map = {'max_hp': 'HP Máximo', 'attack': 'Ataque', 'defense': 'Defesa', 'initiative': 'Iniciativa', 'luck': 'Sorte'}

    for stat in PROFILE_KEYS:
        val = int(total_stats.get(stat, 0))
        status_text += f"{emoji_map[stat]} <b>{name_map[stat]}:</b> {val}\n"

    available_points = int(player_data.get('stat_points', 0) or 0)
    status_text += f"\n✨ <b>Pontos disponíveis:</b> {available_points}"

    keyboard_rows = []
    if available_points > 0:
        # Botões de upgrade (duas colunas)
        row1 = [InlineKeyboardButton("➕ HP (+3)", callback_data='upgrade_max_hp')]
        if 'attack' in PROFILE_KEYS: row1.append(InlineKeyboardButton("➕ ATK (+1)", callback_data='upgrade_attack'))
        keyboard_rows.append(row1)

        row2 = []
        if 'defense' in PROFILE_KEYS: row2.append(InlineKeyboardButton("➕ DEF (+1)", callback_data='upgrade_defense'))
        if 'initiative' in PROFILE_KEYS: row2.append(InlineKeyboardButton("➕ INI (+1)", callback_data='upgrade_initiative'))
        if row2: keyboard_rows.append(row2) # Adiciona linha 2 se tiver botões

        if 'luck' in PROFILE_KEYS:
             keyboard_rows.append([InlineKeyboardButton("➕ SORTE (+1)", callback_data='upgrade_luck')]) # Sorte em linha própria

    # Botões de Ação
    keyboard_rows.append([InlineKeyboardButton("🎐 𝐄𝐯𝐨𝐥𝐮çã𝐨 𝐝𝐞 𝐂𝐥𝐚𝐬𝐬𝐞", callback_data="status_evolution_open")])
    keyboard_rows.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data='profile')]) # Assume que 'profile' volta ao menu principal

    return status_text, InlineKeyboardMarkup(keyboard_rows)

async def show_status_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Mostra a tela de status.
    - Se chamado via /status: Envia nova mensagem de texto.
    - Se chamado via CallbackQuery (botão): Apaga a msg anterior e envia uma nova com mídia (se houver).
    """
    user_id = update.effective_user.id
    player_data = player_manager.get_player_data(user_id)
    chat_id = update.effective_chat.id

    if not player_data:
        text = "Você precisa criar um personagem. Use /start."
        if update.callback_query:
            await update.callback_query.answer()
            try:
                # Tenta editar a mensagem anterior para informar o erro
                await update.callback_query.edit_message_text(text)
            except BadRequest:
                 # Se não puder editar (ex: msg deletada), envia nova
                 if chat_id: await context.bot.send_message(chat_id, text)
        else:
            if update.message: await update.message.reply_text(text)
        return

    status_text, reply_markup = _get_status_content(player_data)

    # --- Lógica para CallbackQuery (Botão) ---
    if update.callback_query:
        query = update.callback_query
        await query.answer()

        # 1. Tenta apagar a mensagem anterior (do menu profile, por exemplo)
        try:
            await query.delete_message()
        except BadRequest as e:
            # Ignora se a mensagem já foi deletada, mas loga outros erros
            if "message to delete not found" not in str(e).lower():
                 logger.warning(f"Erro ao deletar mensagem anterior em show_status_menu: {e}")
        except Exception as e_del:
            logger.warning(f"Erro genérico ao deletar mensagem anterior em show_status_menu: {e_del}")


        # 2. Busca a mídia da classe
        media = _get_class_media(player_data, "status")

        # 3. Envia NOVA mensagem (com ou sem mídia)
        try:
            if media and media.get("id") and chat_id:
                media_id = media["id"]
                media_type = (media.get("type") or "photo").lower()
                if media_type == "video":
                    await context.bot.send_video(chat_id=chat_id, video=media_id, caption=status_text, reply_markup=reply_markup, parse_mode='HTML')
                else:
                    await context.bot.send_photo(chat_id=chat_id, photo=media_id, caption=status_text, reply_markup=reply_markup, parse_mode='HTML')
            elif chat_id: # Se não encontrou mídia, envia como texto
                await context.bot.send_message(chat_id=chat_id, text=status_text, reply_markup=reply_markup, parse_mode='HTML')
            else:
                 logger.error("show_status_menu (callback): chat_id inválido.")

        except Exception as e_send:
            logger.error(f"Erro ao enviar menu de status (callback) para {user_id}: {e_send}", exc_info=True)
            # Tenta enviar uma mensagem de erro simples
            if chat_id: await context.bot.send_message(chat_id, "Ocorreu um erro ao exibir o menu de status.")


    # --- Lógica para Comando /status ---
    else:
        if update.message and chat_id: # Garante que temos uma mensagem e chat_id
            await update.message.reply_text(text=status_text, reply_markup=reply_markup, parse_mode='HTML')
        else:
             logger.error("show_status_menu (comando): update.message ou chat_id inválido.")


async def upgrade_stat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aplica o upgrade de stat e edita a mensagem existente."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    player_data = player_manager.get_player_data(user_id)
    if not player_data: return # Sai se não encontrar dados

    pool = int(player_data.get("stat_points", 0) or 0)
    if pool <= 0:
        await query.answer("Você não tem pontos de atributo para gastar!", show_alert=True)
        return

    profile_stat = query.data.replace('upgrade_', '')
    if profile_stat not in PROFILE_KEYS:
        logger.warning(f"Callback de upgrade inválido recebido: {query.data}")
        return

    # Aplica o upgrade
    player_data["stat_points"] = pool - 1
    inc = 3 if profile_stat == "max_hp" else 1
    player_data[profile_stat] = int(player_data.get(profile_stat, 0)) + inc
    # Se aumentou HP max, cura o jogador pelo mesmo valor
    if profile_stat == "max_hp":
        player_data["current_hp"] = int(player_data.get("current_hp", 0)) + inc

    # Salva os dados
    player_manager.save_player_data(user_id, player_data)

    # Atualiza a mensagem
    status_text, reply_markup = _get_status_content(player_data)

    # =========================================================
    # <<< INÍCIO DA CORREÇÃO (Tratamento de Erro) >>>
    # =========================================================
    try:
        # Tenta editar caption primeiro (se a mensagem atual tiver mídia)
        await query.edit_message_caption(caption=status_text, reply_markup=reply_markup, parse_mode='HTML')
    except BadRequest as e_caption:
        # Se falhou porque não era caption ou por outro erro, tenta editar texto
        if "message has no caption" in str(e_caption).lower() or \
           "message can't be edited" in str(e_caption).lower() or \
           "message to edit not found" in str(e_caption).lower():
            try:
                await query.edit_message_text(text=status_text, reply_markup=reply_markup, parse_mode='HTML')
            except BadRequest as e_text:
                # Ignora o erro "Message is not modified"
                if "message is not modified" not in str(e_text).lower():
                    logger.error(f"Falha ao editar menu de status (texto) após fallback: {e_text}")
            except Exception as e_generic_text:
                 logger.error(f"Erro genérico ao editar menu de status (texto) após fallback: {e_generic_text}", exc_info=True)
        # Ignora o erro "Message is not modified" para caption também
        elif "message is not modified" not in str(e_caption).lower():
             logger.error(f"Falha ao editar menu de status (caption): {e_caption}")
    except Exception as e_generic_caption:
         logger.error(f"Erro genérico ao editar menu de status (caption): {e_generic_caption}", exc_info=True)
    # =========================================================
    # <<< FIM DA CORREÇÃO (Tratamento de Erro) >>>
    # =========================================================


async def close_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fecha (apaga) a mensagem de status."""
    query = update.callback_query
    await query.answer()
    try:
        await query.delete_message()
    except BadRequest as e:
         # Ignora se a mensagem já foi deletada
         if "message to delete not found" not in str(e).lower():
              logger.warning(f"Erro ao tentar fechar status: {e}")
    except Exception as e_del:
        logger.warning(f"Erro genérico ao fechar status: {e_del}")

# ==== EXPORTS ====
status_command_handler = CommandHandler("status", show_status_menu)
status_open_handler = CallbackQueryHandler(show_status_menu, pattern=r'^status_open$')
status_callback_handler = CallbackQueryHandler(upgrade_stat_callback, pattern=r'^upgrade_')
close_status_handler = CallbackQueryHandler(close_status_callback, pattern=r'^close_status$') # Assume que você tem um botão para fechar