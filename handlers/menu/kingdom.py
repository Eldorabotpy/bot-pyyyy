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

try:
    from modules import leaderboard
except ImportError:
    leaderboard = None
    
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
    """Mostra o menu principal do Reino de Eldora sem erros de 'None'."""
    try:
        query = None
        if update and update.callback_query:
            query = update.callback_query

        # ------------------------------------------------------------
        # 1. Identificação de Chat ID (Telegram)
        # ------------------------------------------------------------
        if not chat_id and update and update.effective_chat:
            chat_id = update.effective_chat.id
        if not chat_id and query and query.message:
            chat_id = query.message.chat.id
        if not chat_id and player_data:
            chat_id = player_data.get("last_chat_id") or player_data.get("telegram_id_owner")

        if not chat_id:
            logger.error("ERRO CRÍTICO: Não foi possível identificar o Chat ID no menu Kingdom.")
            return

        # ------------------------------------------------------------
        # 2. Responde callback se for do Kingdom
        # ------------------------------------------------------------
        if query and (query.data in _KINGDOM_CALLBACKS):
            try:
                await query.answer()
            except Exception:
                pass

        # ------------------------------------------------------------
        # 3. Carregamento e Persistência de Dados
        # ------------------------------------------------------------
        user_id = None
        if player_data is None:
            if not update:
                return
            user_id = get_current_player_id(update, context)
            player_data = await player_manager.get_player_data(user_id)

        if not player_data:
            await context.bot.send_message(chat_id=chat_id, text="❌ Personagem não encontrado. Use /start.")
            return

        # Atualiza localização e salva com ID de Sessão (ObjectId)
        player_data["current_location"] = "reino_eldora"
        uid = user_id or player_data.get("_id") or player_data.get("user_id")
        if uid:
            await player_manager.save_player_data(uid, player_data)

        # ------------------------------------------------------------
        # 4. TRATAMENTO DE DADOS (CORREÇÃO DO 'NONE' E STATUS 0)
        # ------------------------------------------------------------
        
        # Correção Nome: Fallback triplo para evitar "None"
        character_name = (
            player_data.get("character_name") or 
            player_data.get("name") or 
            (update.effective_user.first_name if update and update.effective_user else "Aventureiro")
        )

        # Cálculo de Stats Totais (Garante Max HP/MP corretos)
        try:
            res = player_manager.get_player_total_stats(player_data)
            total_stats = await res if hasattr(res, "__await__") else res
        except Exception as e_stats:
            logger.error(f"Erro stats kingdom: {e_stats}")
            total_stats = {}

        # HP: Prioriza current_hp, fallback para chave hp simples
        p_hp = int(player_data.get("current_hp") or player_data.get("hp") or 0)
        p_max_hp = int(total_stats.get("max_hp") or player_data.get("max_hp") or 50)

        # MP/Mana: Correção do 0/45. Prioriza current_mp, tenta mana, tenta mp
        p_mp = int(player_data.get("current_mp") or player_data.get("mana") or player_data.get("mp") or 0)
        p_max_mp = int(total_stats.get("max_mana") or player_data.get("max_mana") or 50)

        # Energia
        p_energy = int(player_data.get("energy", 0))
        try:
            max_energy = int(player_manager.get_player_max_energy(player_data))
        except Exception:
            max_energy = 20

        # Profissão
        prof_data = player_data.get("profession", {}) or {}
        prof_lvl = int(prof_data.get("level", 1))
        prof_type = prof_data.get("type") or prof_data.get("key") or "adventurer"
        prof_name = prof_type.capitalize()
        if hasattr(game_data, "PROFESSIONS_DATA"):
            prof_name = (game_data.PROFESSIONS_DATA or {}).get(prof_type, {}).get("display_name", prof_name)

        # Economia
        p_gold = int(player_data.get("gold", 0))
        p_gems = int(player_data.get("gems", 0))

        # Plano e Ícones
        tier_key = str(player_data.get("premium_tier", "free")).lower().strip()
        tier_info = PREMIUM_TIERS.get(tier_key, {})
        plan_display = tier_info.get("display_name", tier_key.capitalize())
        
        icons = {"lenda": "👑", "vip": "💎", "premium": "🌟", "admin": "🛠️", "free": "🎗️"}
        plan_icon = icons.get(tier_key, "🎗️")
        if tier_key == "free": plan_display = "Aventureiro"

        # ------------------------------------------------------------
        # 5. MONTAGEM DA INTERFACE (HUD)
        # ------------------------------------------------------------
        status_hud = (
            f"╭──────── [ 𝐏𝐄𝐑𝐅𝐈𝐋 ] ────➤\n"
            f"│ ╭┈➤ 👤 <b>{character_name}</b>\n"
            f"│ ├┈➤ {plan_icon} <b>{plan_display}</b>\n"
            f"│ ├┈➤ 🛠 {prof_name} (Nv. {prof_lvl})\n"
            f"│ ├┈➤ ❤️ HP: <code>{p_hp}/{p_max_hp}</code>\n"
            f"│ ├┈➤ 💙 MP: <code>{p_mp}/{p_max_mp}</code>\n"
            f"│ ├┈➤ ⚡ ENRGIA: 🪫{p_energy}/🔋{max_energy}\n"
            f"│ ╰┈➤ 💰 {p_gold:,}  💎 {p_gems:,}\n"
            f"╰────────────────────────➤"
        )

        caption = (
            f"🏰 <b>𝐑𝐄𝐈𝐍𝐎 𝐃𝐄 𝐄𝐋𝐃𝐎𝐑𝐀</b>\n"
            f"╰┈➤ 𝗕𝗲𝗺-𝘃𝗶𝗻𝗱𝗼, {character_name}!\n\n"
            f"As muralhas da cidade oferecem segurança e oportunidades. "
            f"O que você gostaria de fazer hoje?\n"
            f"{status_hud}"
        )

        # Leaderboard/MVP
        if leaderboard and hasattr(leaderboard, 'get_top_score_text'):
            try:
                mvp = leaderboard.get_top_score_text()
                if mvp:
                    caption += f"\n\n🏆 <b>MVP DO EVENTO ATUALIZADO:</b>\n ╰┈➤ {mvp.strip()}\n"
            except Exception:
                pass

        keyboard = [
            [InlineKeyboardButton("🗺 𝐕𝐢𝐚𝐣𝐚𝐫", callback_data="travel"),
             InlineKeyboardButton("👤 𝐏𝐞𝐫𝐬𝐨𝐧𝐚𝐠𝐞𝐦", callback_data="profile")],
            [InlineKeyboardButton("🏪 𝐌𝐞𝐫𝐜𝐚𝐝𝐨", callback_data="market"),
             InlineKeyboardButton("⚒️ 𝐅𝐨𝐫𝐣𝐚", callback_data="forge:main")],
            [InlineKeyboardButton("🏰 𝐆𝐮𝐢𝐥𝐝𝐚", callback_data="adventurer_guild_main"),
             InlineKeyboardButton("🧪 𝐑𝐞𝐟𝐢𝐧𝐨", callback_data="refining_main")],
            [InlineKeyboardButton("⚔️ 𝐀𝐫𝐞𝐧𝐚 𝐏𝐯𝐏", callback_data="pvp_arena"),
             InlineKeyboardButton("💀 𝐄𝐯𝐞𝐧𝐭𝐨𝐬", callback_data="abrir_hub_eventos_v2")],
            [InlineKeyboardButton("📘 𝐆𝐮𝐢𝐚 𝐝𝐨 𝐀𝐯𝐞𝐧𝐭𝐮𝐫𝐞𝐢𝐫𝐨", callback_data="guide_main")],
        ]

        # Painel Admin (Usa Telegram ID para permissão visual)
        try:
            tg_id = str(update.effective_user.id if update and update.effective_user else player_data.get("telegram_id_owner", ""))
            if tg_id in ["5961634863"]:
                keyboard.append([InlineKeyboardButton("🛠️ Painel Admin", callback_data="admin_main")])
        except Exception:
            pass

        reply_markup = InlineKeyboardMarkup(keyboard)

        # ------------------------------------------------------------
        # 6. MÍDIA E RENDERIZAÇÃO
        # ------------------------------------------------------------
        media_id = None
        media_type = "photo"
        fd = file_ids.get_file_data("regiao_reino_eldora")
        if fd:
            media_id = fd.get("id")
            media_type = (fd.get("type") or "photo").lower()

        # Lógica de Edição para Callbacks
        if query and query.message:
            if query.data in _KINGDOM_CALLBACKS:
                try:
                    if query.message.caption is not None:
                        await query.edit_message_caption(caption=caption, reply_markup=reply_markup, parse_mode="HTML")
                    else:
                        await query.edit_message_text(text=caption, reply_markup=reply_markup, parse_mode="HTML")
                    return
                except Exception:
                    try: await query.delete_message()
                    except: pass

        # Envio de nova mensagem
        if media_id:
            try:
                if media_type == "video":
                    await context.bot.send_video(chat_id=chat_id, video=media_id, caption=caption, reply_markup=reply_markup, parse_mode="HTML")
                else:
                    await context.bot.send_photo(chat_id=chat_id, photo=media_id, caption=caption, reply_markup=reply_markup, parse_mode="HTML")
                return
            except Exception:
                pass

        await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML")

    except Exception as e_fatal:
        logger.exception(f"ERRO FATAL NO MENU KINGDOM: {e_fatal}")
        if chat_id:
            await context.bot.send_message(chat_id=chat_id, text="⚠️ Erro ao carregar o reino. Tente /start.")


# Handlers
kingdom_menu_handler = CallbackQueryHandler(show_kingdom_menu, pattern=r"^show_kingdom_menu$")
kingdom_back_handler = CallbackQueryHandler(show_kingdom_menu, pattern=r"^back_to_kingdom$")
