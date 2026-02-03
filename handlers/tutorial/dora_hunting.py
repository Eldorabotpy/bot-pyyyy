# handlers/tutorial/dora_hunting.py
from __future__ import annotations

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram import Update
from modules import player_manager

CB_HUNT_OPEN_MAP = "dora_hunt_open_map"
CB_HUNT_HELP = "dora_hunt_help"
CB_HUNT_HUNT_NOW = "dora_hunt_now"

TARGET_REGION = "pradaria_inicial"
TARGET_LEVEL = 5 


def _extract_message(update: Update):
    if update.message:
        return update.message
    if update.callback_query and update.callback_query.message:
        return update.callback_query.message
    return None


async def start_hunting_chapter(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str):
    """
    Chamado quando termina a 1ª coleta: Dora manda ir para a pradaria.
    """
    msg = _extract_message(update)
    if not msg:
        return

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        return

    flags = player_data.setdefault("tutorial_flags", {})
    if flags.get("hunting_chapter_started"):
        return

    player_data["onboarding_stage"] = "tutorial_hunting"
    flags["hunting_chapter_started"] = True
    await player_manager.save_player_data(user_id, player_data)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗺️ Abrir Mapa", callback_data=CB_HUNT_OPEN_MAP)],
        [InlineKeyboardButton("❓ Como caçar?", callback_data=CB_HUNT_HELP)],
    ])

    await msg.reply_text(
        "🐺 <b>TUTORIAL — CAÇA</b>\n"
        "👩‍✈️ <b>Dora:</b> Agora vamos treinar combate.\n\n"
        "📍 Vá para <b>🌱 Pradaria Inicial</b>.\n"
        "Lá você vai caçar repetidas vezes até alcançar o <b>Nível 5</b>.\n\n"
        "✅ No nível 5 você desbloqueia a <b>Classe</b>.",
        parse_mode="HTML",
        reply_markup=kb
    )

async def start_hunting_chapter_job(context, chat_id: int, user_id: str):
    """
    Versão segura para JOB (sem update).
    """
    player_data = await player_manager.get_player_data(user_id) or {}
    flags = player_data.setdefault("tutorial_flags", {})

    if flags.get("hunting_chapter_started"):
        return

    player_data["onboarding_stage"] = "tutorial_hunting"
    flags["hunting_chapter_started"] = True
    await player_manager.save_player_data(user_id, player_data)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗺️ Ir para a Pradaria", callback_data="dora_hunt_open_map")],
        [InlineKeyboardButton("❓ Como caçar?", callback_data="dora_hunt_help")],
    ])

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🐺 <b>TUTORIAL — CAÇA</b>\n"
            "👩‍✈️ <b>Dora:</b> Ótimo! Você concluiu sua primeira coleta.\n\n"
            "Agora vamos treinar combate na <b>🌱 Pradaria Inicial</b>.\n"
            "Cace até alcançar o <b>Nível 5</b> para liberar sua <b>Classe</b>."
        ),
        parse_mode="HTML",
        reply_markup=kb
    )

async def maybe_continue_hunting_on_arrival(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str, region_key: str):
    """
    Hook chamado após viajar (open_region_callback).
    Se chegou na pradaria_inicial e está no estágio tutorial_hunting, Dora ensina caçar.
    """
    if region_key != TARGET_REGION:
        return

    player_data = await player_manager.get_player_data(user_id) or {}
    if player_data.get("onboarding_stage") != "tutorial_hunting":
        return

    flags = player_data.setdefault("tutorial_flags", {})
    if flags.get("hunting_arrival_intro_done"):
        return

    flags["hunting_arrival_intro_done"] = True
    await player_manager.save_player_data(user_id, player_data)

    # ⚠️ Ajuste o callback de caça abaixo para o SEU real callback
    # Coloquei como "hunt_start" porque é o mais comum.
    # Se seu projeto usa outro, você troca aqui 1 linha.
    hunt_callback = "hunt_start"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🐺 Caçar agora", callback_data=hunt_callback)],
        [InlineKeyboardButton("❓ Dicas de combate", callback_data=CB_HUNT_HELP)],
    ])

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "🌱 <b>Pradaria Inicial</b>\n"
            "👩‍✈️ <b>Dora:</b> Perfeito! Aqui é o campo de treino.\n\n"
            "✅ Agora toque em <b>🐺 Caçar agora</b>.\n"
            f"Repita até chegar ao <b>Nível {TARGET_LEVEL}</b>.\n\n"
            "📌 Dica: se sua energia acabar, espere regenerar (ou use itens/recursos, se existirem)."
        ),
        parse_mode="HTML",
        reply_markup=kb
    )


async def maybe_notify_level_progress(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str, new_level: int):
    """
    Dora acompanha a progressão na Pradaria:
    - se houver stat_points, ensina a abrir Status e distribuir
    - no lvl 5, mostra botão de escolher classe (class_open)
    """
    if not update or not update.effective_chat:
        return

    player_data = await player_manager.get_player_data(user_id) or {}
    if player_data.get("onboarding_stage") != "tutorial_hunting":
        return

    # Se já tem classe, não precisa tutorial
    if player_data.get("class"):
        return

    flags = player_data.setdefault("tutorial_flags", {}) or {}

    # evita spam: 1x por level
    key = f"hunting_level_{new_level}_notified"
    if flags.get(key):
        return

    flags[key] = True
    await player_manager.save_player_data(user_id, player_data)

    # ✅ verifica pontos de status
    stat_points = int(player_data.get("stat_points", 0) or 0)

    # ✅ chegou no nível 5: liberar classe (SEM evolução)
    if new_level >= TARGET_LEVEL:
        player_data["onboarding_stage"] = "class_unlock"
        flags["class_unlock_ready"] = True
        await player_manager.save_player_data(user_id, player_data)

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚔️ Escolher Classe", callback_data="class_open")]
        ])

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "🏅 <b>Parabéns!</b> Você chegou ao <b>Nível 5</b>.\n\n"
                "👩‍✈️ <b>Dora:</b> Agora você pode escolher sua <b>Classe</b>.\n"
                "Toque no botão abaixo:"
            ),
            parse_mode="HTML",
            reply_markup=kb
        )
        return

    # ✅ se tiver ponto, ensina a gastar
    if stat_points > 0:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Distribuir Pontos", callback_data="status_open")]
        ])

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"✅ <b>Nível {new_level}</b>!\n\n"
                f"👩‍✈️ <b>Dora:</b> Você tem <b>{stat_points} ponto(s)</b> de Status para distribuir.\n"
                "Abra <b>Status</b> e escolha onde investir (Ataque, Defesa, HP...).\n\n"
                f"Depois continue caçando na <b>🌱 Pradaria Inicial</b> até o <b>Nível {TARGET_LEVEL}</b>."
            ),
            parse_mode="HTML",
            reply_markup=kb
        )
        return

    # ✅ se não tiver ponto, só incentiva continuar
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            f"✅ <b>Nível {new_level}</b>!\n"
            f"Continue caçando na <b>🌱 Pradaria Inicial</b> até o <b>Nível {TARGET_LEVEL}</b>."
        ),
        parse_mode="HTML",
    )

async def dora_hunting_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q or not q.message:
        return
    await q.answer()

    data = q.data or ""

    if data == CB_HUNT_HELP:
        await q.message.reply_text(
            "⚔️ <b>Dicas rápidas</b>\n"
            "• Caçar dá XP e ouro.\n"
            "• Repita o ciclo para upar.\n"
            "• Se você perder, recupere HP/energia e tente de novo.\n\n"
            "🎯 Objetivo do tutorial: chegar ao <b>Nível 5</b> para liberar Classe.",
            parse_mode="HTML"
        )
        return

    if data == CB_HUNT_OPEN_MAP:
        # Abre o mapa real (se seu mapa for outra função, ajusta aqui)
        from handlers.menu.region import show_travel_menu
        await show_travel_menu(update, context)
        return
