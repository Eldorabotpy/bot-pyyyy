# handlers/menu/kingdom.py
# (VERSÃO CORRIGIDA: Compatível com novo sistema de Login)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules import player_manager, game_data, file_ids
from kingdom_defense import leaderboard 
from modules.auth_utils import get_current_player_id # <--- Importante

logger = logging.getLogger(__name__)

# Alteração 1: Aceita chat_id e message_id como argumentos opcionais
async def show_kingdom_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, player_data: dict | None = None, chat_id: int | None = None, message_id: int | None = None):
    """Mostra o menu principal do Reino de Eldora."""
    try:
        query = None
        user = None
        
        # Verifica se 'update' existe antes de tentar acessá-lo
        if update:
            if update.callback_query:
                query = update.callback_query
            user = update.effective_user

        # =================================================================
        # 🛡️ BLINDAGEM NÍVEL 2 (FIX ERRO NoneType)
        # =================================================================
        
        # 1. Se o chat_id não veio nos argumentos, tenta descobrir pelo Update do Telegram
        if not chat_id and update:
            if update.effective_chat:
                chat_id = update.effective_chat.id
            elif query and query.message:
                chat_id = query.message.chat.id
            elif user:
                chat_id = user.id
        
        # 2. (NOVO) Se ainda não achou, tenta pegar de dentro do player_data
        if not chat_id and player_data:
            # Tenta pegar o chat ID salvo ou o ID do dono (Telegram ID)
            chat_id = player_data.get("last_chat_id") or player_data.get("telegram_id_owner")
            # Se for conta antiga, o próprio _id/user_id é o chat_id
            if not chat_id:
                uid = player_data.get("user_id")
                if isinstance(uid, int):
                    chat_id = uid

        # Se ainda assim falhar, aborta
        if not chat_id:
            logger.error("ERRO CRÍTICO: Não foi possível identificar o Chat ID no menu Kingdom.")
            return
        # =================================================================

        if query and query.data == "show_kingdom_menu":
            try: await query.answer() 
            except: pass

        # Carrega dados do jogador se não vierem nos argumentos
        if player_data is None:
            if update:
                # MUDANÇA CRÍTICA AQUI: Usa a função ponte para pegar o ID correto (Sessão ou Telegram)
                user_id = get_current_player_id(update, context)
                player_data = await player_manager.get_player_data(user_id)
            else:
                # Se não tem update e nem player_data, não tem como saber quem é.
                logger.error("show_kingdom_menu chamado sem update e sem player_data.")
                return
        
        if not player_data:
            # Tenta avisar usando o chat_id recuperado
            await context.bot.send_message(chat_id=chat_id, text="Personagem não encontrado. Use /start.")
            return

        # Atualiza localização
        player_data['current_location'] = 'reino_eldora'
        # Salva o user_id se ele veio do player_data
        user_id_save = player_data.get("user_id")
        if user_id_save:
            await player_manager.save_player_data(user_id_save, player_data) 

        # --- PREPARAÇÃO DOS DADOS PARA EXIBIÇÃO ---
        character_name = player_data.get("character_name", "Aventureiro(a)")
        
        # Stats (Híbrido)
        try:
            res = player_manager.get_player_total_stats(player_data)
            total_stats = await res if hasattr(res, '__await__') else res
        except Exception as e_stats:
            logger.error(f"Erro stats kingdom: {e_stats}")
            total_stats = {} 
        
        # Profissão
        prof_data = player_data.get("profession", {})
        prof_lvl = int(prof_data.get("level", 1))
        prof_type = prof_data.get("type", "adventurer")
        prof_name = prof_type.capitalize()
        try:
            if hasattr(game_data, 'PROFESSIONS_DATA'):
                prof_name = game_data.PROFESSIONS_DATA.get(prof_type, {}).get("display_name", prof_name)
        except: pass

        # Status
        p_hp = int(player_data.get('current_hp', 0))
        p_max_hp = int(total_stats.get('max_hp', 100))
        p_energy = int(player_data.get('energy', 0))
        try: max_energy = int(player_manager.get_player_max_energy(player_data))
        except: max_energy = 100
        p_mp = int(player_data.get('current_mp', 0))
        p_max_mp = int(total_stats.get('max_mana', 50))

        # Economia
        try:
            p_gold = player_manager.get_gold(player_data)
            p_gems = player_manager.get_gems(player_data)
        except:
            p_gold = player_data.get("gold", 0)
            p_gems = player_data.get("gems", 0)

        # Leaderboard
        try: leaderboard_text = leaderboard.get_top_score_text()
        except: leaderboard_text = ""
        
        # --- NOVO VISUAL ESTILO HUD ---
        status_hud = (
            f"\n"
            f"╭──────── [ 𝐏𝐄𝐑𝐅𝐈𝐋 ] ────➤\n"
            f"│ ╭┈➤ 👤 {character_name}\n"
            f"│ ├┈➤ 🛠 {prof_name} (Nv. {prof_lvl})\n"
            f"│ ├┈➤ ❤️ HP: {p_hp}/{p_max_hp}\n"
            f"│ ├┈➤ 💙 MP: {p_mp}/{p_max_mp}\n"
            f"│ ├┈➤ ⚡ ENRGIA: 🪫{p_energy}/🔋{max_energy}\n"
            f"│ ╰┈➤ 💰 {p_gold:,}  💎 {p_gems:,}\n"
            f"╰────────────────────────➤"
            
        )

        caption = (
            f"🏰 <b>𝐑𝐄𝐈𝐍𝐎 𝐃𝐄 𝐄𝐋𝐃𝐎𝐑𝐀</b>\n"
            f"╰┈➤ 𝗕𝗲𝗺-𝘃𝗶𝗻𝗱𝗼, {character_name}!\n\n"
            f"𝗔𝘀 𝗺𝘂𝗿𝗮𝗹𝗵𝗮𝘀 𝗱𝗮 𝗰𝗶𝗱𝗮𝗱𝗲 𝗼𝗳𝗲𝗿𝗲𝗰𝗲𝗺 𝘀𝗲𝗴𝘂𝗿𝗮𝗻𝗰̧𝗮 𝗲 𝗼𝗽𝗼𝗿𝘁𝘂𝗻𝗶𝗱𝗮𝗱𝗲𝘀. "
            f"𝗢 𝗾𝘂𝗲 𝘃𝗼𝗰𝗲̂ 𝗴𝗼𝘀𝘁𝗮𝗿𝗶𝗮 𝗱𝗲 𝗳𝗮𝘇𝗲𝗿 𝗵𝗼𝗷𝗲?\n"
            f"{status_hud}"
        )

        if leaderboard_text:
            caption += (
                f"\n\n🏆 <b>MVP DO EVENTO ATUALIZADO:</b>\n"
                f"   ╰┈➤ {leaderboard_text.strip()}"
                f"\n"
            )
        # --- TECLADO ---
        keyboard = [
            # LINHA 1: Ações Principais (Viajar e Perfil)
            [
                InlineKeyboardButton("🗺 𝐕𝐢𝐚𝐣𝐚𝐫", callback_data='travel'),
                InlineKeyboardButton("👤 𝐏𝐞𝐫𝐬𝐨𝐧𝐚𝐠𝐞𝐦", callback_data='profile')
            ],
            # LINHA 2: Economia (Mercado e Forja)
            [
                InlineKeyboardButton("🏪 𝐌𝐞𝐫𝐜𝐚𝐝𝐨", callback_data='market'),
                InlineKeyboardButton("⚒️ 𝐅𝐨𝐫𝐣𝐚", callback_data='forge:main'),
            ],
            # LINHA 3: Social e Avançado (Guilda e Refino)
            [
                InlineKeyboardButton("🏰 𝐆𝐮𝐢𝐥𝐝𝐚", callback_data='adventurer_guild_main'),
                InlineKeyboardButton("🧪 𝐑𝐞𝐟𝐢𝐧𝐨", callback_data='refining_main'),
            ],
            # LINHA 4: Combate e Eventos (Destaque para ação)
            [
                InlineKeyboardButton("⚔️ 𝐀𝐫𝐞𝐧𝐚 𝐏𝐯𝐏", callback_data='pvp_arena'), 
                InlineKeyboardButton("💀 𝐄𝐯𝐞𝐧𝐭𝐨𝐬", callback_data='evt_hub_principal')
            ],
            # LINHA 5: Rodapé (Info)
            [InlineKeyboardButton("ℹ️ 𝐒𝐨𝐛𝐫𝐞 𝐨 𝐑𝐞𝐢𝐧𝐨", callback_data='region_info:reino_eldora')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # --- LÓGICA DE MÍDIA ---
        media_id = None
        media_type = "photo"
        try:
            fd = file_ids.get_file_data('regiao_reino_eldora')
            if fd:
                media_id = fd.get("id")
                media_type = (fd.get("type") or "photo").lower()
        except: pass

        # Tenta editar se for callback E se a mensagem original existir
        if query and query.message:
            try:
                if media_id:
                    media = InputMediaVideo(media_id, caption=caption, parse_mode='HTML') if media_type == "video" else InputMediaPhoto(media_id, caption=caption, parse_mode='HTML')
                    await query.edit_message_media(media=media, reply_markup=reply_markup)
                else:
                    await query.edit_message_text(text=caption, reply_markup=reply_markup, parse_mode='HTML')
                return
            except Exception:
                try: await query.delete_message()
                except: pass

        # Fallback: Envio de Nova Mensagem
        if media_id:
            try:
                if media_type == "video":
                    await context.bot.send_video(chat_id=chat_id, video=media_id, caption=caption, reply_markup=reply_markup, parse_mode='HTML')
                else:
                    await context.bot.send_photo(chat_id=chat_id, photo=media_id, caption=caption, reply_markup=reply_markup, parse_mode='HTML')
                return
            except Exception as e:
                logger.debug("Falha mídia kingdom: %s", e)

        await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode='HTML')

    except Exception as e_fatal:
        logger.exception(f"ERRO FATAL NO MENU KINGDOM: {e_fatal}")
        if 'chat_id' in locals() and chat_id:
             try: await context.bot.send_message(chat_id=chat_id, text="⚠️ Erro ao carregar o reino.")
             except: pass

# Handler
kingdom_menu_handler = CallbackQueryHandler(show_kingdom_menu, pattern=r'^show_kingdom_menu$')