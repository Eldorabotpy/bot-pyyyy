# handlers/menu/kingdom.py
# (VERSÃO CORRIGIDA: Voltar funciona + não salva com Telegram ID + callbacks do Kingdom tratados)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, game_data, file_ids
from kingdom_defense import leaderboard

# Auth (Session/ObjectId)
from modules.auth_utils import get_current_player_id, requires_login

# Importa DIRETAMENTE do seu arquivo premium.py
from modules.game_data.premium import PREMIUM_TIERS

logger = logging.getLogger(__name__)

# Callbacks que o Kingdom deve considerar "dele" para poder editar/enviar o menu
_KINGDOM_CALLBACKS = {"show_kingdom_menu", "back_to_kingdom"}


@requires_login
async def show_kingdom_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    player_data: dict | None = None,
    chat_id: int | None = None,
    message_id: int | None = None,
):
    """Mostra o menu principal do Reino de Eldora."""
    try:
        query = None

        if update and update.callback_query:
            query = update.callback_query

        # ------------------------------------------------------------
        # Chat ID robusto (sempre chat_id Telegram aqui, não é user_id do DB)
        # ------------------------------------------------------------
        if not chat_id and update and update.effective_chat:
            chat_id = update.effective_chat.id

        if not chat_id and query and query.message:
            chat_id = query.message.chat.id

        # Fallback: usa last_chat_id salvo (se existir)
        if not chat_id and player_data:
            chat_id = player_data.get("last_chat_id") or player_data.get("telegram_id_owner")

        if not chat_id:
            logger.error("ERRO CRÍTICO: Não foi possível identificar o Chat ID no menu Kingdom.")
            return

        # ------------------------------------------------------------
        # Responde callback se for do Kingdom (evita botão travado)
        # ------------------------------------------------------------
        if query and (query.data in _KINGDOM_CALLBACKS):
            try:
                await query.answer()
            except Exception:
                pass

        # ------------------------------------------------------------
        # Carrega player_data se não veio injetado
        # ------------------------------------------------------------
        user_id = None
        if player_data is None:
            if not update:
                return
            user_id = get_current_player_id(update, context)  # Session/ObjectId (str)
            player_data = await player_manager.get_player_data(user_id)

        if not player_data:
            await context.bot.send_message(chat_id=chat_id, text="Personagem não encontrado. Use /start.")
            return

        # ------------------------------------------------------------
        # Atualiza localização e salva COM SESSION/OBJECTID (nunca Telegram ID)
        # ------------------------------------------------------------
        player_data["current_location"] = "reino_eldora"

        # Prioridade 1: ID da sessão atual (se existe update)
        if update:
            uid = get_current_player_id(update, context)
            if uid:
                user_id = uid

        # Prioridade 2: ID já armazenado no player_data (string/ObjectId)
        if not user_id:
            user_id = player_data.get("user_id")

        if user_id:
            await player_manager.save_player_data(user_id, player_data)

        # ------------------------------------------------------------
        # --- DADOS PARA EXIBIÇÃO ---
        # ------------------------------------------------------------
        character_name = player_data.get("character_name", "Aventureiro(a)")

        try:
            res = player_manager.get_player_total_stats(player_data)
            total_stats = await res if hasattr(res, "__await__") else res
        except Exception as e_stats:
            logger.error(f"Erro stats kingdom: {e_stats}")
            total_stats = {}

        # Profissão
        prof_data = player_data.get("profession", {}) or {}
        prof_lvl = int(prof_data.get("level", 1))
        prof_type = prof_data.get("type", "adventurer")
        prof_name = prof_type.capitalize()
        try:
            if hasattr(game_data, "PROFESSIONS_DATA"):
                prof_name = (game_data.PROFESSIONS_DATA or {}).get(prof_type, {}).get("display_name", prof_name)
        except Exception:
            pass

        # Status
        p_hp = int(player_data.get("current_hp", 0))
        p_max_hp = int(total_stats.get("max_hp", 100))
        p_energy = int(player_data.get("energy", 0))
        try:
            max_energy = int(player_manager.get_player_max_energy(player_data_data := player_data))
        except Exception:
            max_energy = 100
        p_mp = int(player_data.get("current_mp", 0))
        p_max_mp = int(total_stats.get("max_mana", 50))

        # Economia
        try:
            p_gold = player_manager.get_gold(player_data)
            p_gems = player_manager.get_gems(player_data)
        except Exception:
            p_gold = player_data.get("gold", 0)
            p_gems = player_data.get("gems", 0)

        try:
            leaderboard_text = leaderboard.get_top_score_text()
        except Exception:
            leaderboard_text = ""

        # Plano
        tier_key = str(player_data.get("premium_tier", "free")).lower().strip()
        tier_info = PREMIUM_TIERS.get(tier_key, {})
        plan_display = tier_info.get("display_name", tier_key.capitalize())

        if tier_key == "lenda":
            plan_icon = "👑"
        elif tier_key == "vip":
            plan_icon = "💎"
        elif tier_key == "premium":
            plan_icon = "🌟"
        elif tier_key == "admin":
            plan_icon = "🛠️"
        else:
            plan_icon = "🎗️"
            if tier_key == "free":
                plan_display = "Aventureiro"

        status_hud = (
            f"\n"
            f"╭──────── [ 𝐏𝐄𝐑𝐅𝐈𝐋 ] ────➤\n"
            f"│ ╭┈➤ 👤 {character_name}\n"
            f"│ ├┈➤ {plan_icon} <b>{plan_display}</b>\n"
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
                f"   ╰┈➤ {leaderboard_text.strip()}\n"
            )

        keyboard = [
            [
                InlineKeyboardButton("🗺 𝐕𝐢𝐚𝐣𝐚𝐫", callback_data="travel"),
                InlineKeyboardButton("👤 𝐏𝐞𝐫𝐬𝐨𝐧𝐚𝐠𝐞𝐦", callback_data="profile"),
            ],
            [
                InlineKeyboardButton("🏪 𝐌𝐞𝐫𝐜𝐚𝐝𝐨", callback_data="market"),
                InlineKeyboardButton("⚒️ 𝐅𝐨𝐫𝐣𝐚", callback_data="forge:main"),
            ],
            [
                InlineKeyboardButton("🏰 𝐆𝐮𝐢𝐥𝐝𝐚", callback_data="adventurer_guild_main"),
                InlineKeyboardButton("🧪 𝐑𝐞𝐟𝐢𝐧𝐨", callback_data="refining_main"),
            ],
            [
                InlineKeyboardButton("⚔️ 𝐀𝐫𝐞𝐧𝐚 𝐏𝐯𝐏", callback_data="pvp_arena"),
                InlineKeyboardButton("💀 𝐄𝐯𝐞𝐧𝐭𝐨𝐬", callback_data="abrir_hub_eventos_v2"),
            ],
            [InlineKeyboardButton("📘 𝐆𝐮𝐢𝐚 𝐝𝐨 𝐀𝐯𝐞𝐧𝐭𝐮𝐫𝐞𝐢𝐫𝐨", callback_data="guide_main")],
        ]

        # Admin: aqui você está checando Telegram ID, o que é ok para permissão visual.
        # Só não use isso como ID de banco.
        try:
            tg_id = None
            if update and update.effective_user:
                tg_id = str(update.effective_user.id)
            if not tg_id:
                tg_id = str(player_data.get("telegram_id_owner") or "")
            if tg_id and tg_id in ["5961634863"]:
                keyboard.append([InlineKeyboardButton("🛠️ Painel Admin", callback_data="admin_main")])
        except Exception:
            pass

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Mídia
        media_id = None
        media_type = "photo"
        try:
            fd = file_ids.get_file_data("regiao_reino_eldora")
            if fd:
                media_id = fd.get("id")
                media_type = (fd.get("type") or "photo").lower()
        except Exception:
            pass

        # ------------------------------------------------------------
        # Edição/Render: só mexe na mensagem se callback for do Kingdom
        # Agora inclui back_to_kingdom (FIX do botão Voltar)
        # ------------------------------------------------------------
        if query and query.message:
            if query.data not in _KINGDOM_CALLBACKS:
                return

            try:
                # Se já tiver mídia, edita caption; senão edita texto
                if query.message.caption is not None:
                    if media_id:
                        await query.edit_message_caption(
                            caption=caption, reply_markup=reply_markup, parse_mode="HTML"
                        )
                    else:
                        await query.edit_message_text(
                            text=caption, reply_markup=reply_markup, parse_mode="HTML"
                        )
                else:
                    # Se não dá para editar (mensagem sem caption), recria
                    await query.delete_message()
                    raise Exception("Reload needed")
                return
            except Exception:
                try:
                    await query.delete_message()
                except Exception:
                    pass

        # Envio novo (sem query)
        if media_id:
            try:
                if media_type == "video":
                    await context.bot.send_video(
                        chat_id=chat_id,
                        video=media_id,
                        caption=caption,
                        reply_markup=reply_markup,
                        parse_mode="HTML",
                    )
                else:
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=media_id,
                        caption=caption,
                        reply_markup=reply_markup,
                        parse_mode="HTML",
                    )
                return
            except Exception as e:
                logger.debug("Falha mídia kingdom: %s", e)

        await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML")

    except Exception as e_fatal:
        logger.exception(f"ERRO FATAL NO MENU KINGDOM: {e_fatal}")
        try:
            if chat_id:
                await context.bot.send_message(chat_id=chat_id, text="⚠️ Erro ao carregar o reino.")
        except Exception:
            pass


# Handlers
kingdom_menu_handler = CallbackQueryHandler(show_kingdom_menu, pattern=r"^show_kingdom_menu$")
kingdom_back_handler = CallbackQueryHandler(show_kingdom_menu, pattern=r"^back_to_kingdom$")
