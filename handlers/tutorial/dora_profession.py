# handlers/tutorial/dora_profession.py

from __future__ import annotations
from typing import Dict, Any

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from modules import player_manager
from modules.auth_utils import get_current_player_id

# Tenta importar do local padrão do projeto
try:
    from modules.game_data.professions import PROFESSIONS_DATA  # type: ignore
except Exception:
    PROFESSIONS_DATA = {}

# Callbacks (padronizados)
CB_PROF_MENU = "dora_prof_menu"
CB_PROF_CAT_GATHER = "dora_prof_cat_gather"
CB_PROF_CAT_CRAFT = "dora_prof_cat_craft"
CB_PROF_VIEW_PREFIX = "dora_prof_view:"       # + key
CB_PROF_CONFIRM_PREFIX = "dora_prof_confirm:" # + key
CB_PROF_BACK = "dora_prof_back"


def is_gathering_profession(prof_key: str) -> bool:
    info = PROFESSIONS_DATA.get(prof_key, {}) or {}
    return info.get("category") == "gathering"


def _extract_message(update: Update):
    if update.message:
        return update.message
    if update.callback_query and update.callback_query.message:
        return update.callback_query.message
    return None


def _prof_display(key: str) -> str:
    info = PROFESSIONS_DATA.get(key, {}) or {}
    return info.get("display_name") or key.replace("_", " ").title()


def _prof_emoji(key: str) -> str:
    # Se você tiver emoji nas profissões, usa; senão, define por categoria
    info = PROFESSIONS_DATA.get(key, {}) or {}
    if info.get("category") == "gathering":
        return "🌲"
    return "⚒️"


async def show_profession_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, player_data: dict):
    msg = _extract_message(update)
    if not msg:
        return

    cname = (player_data.get("character_name") or "Aventureiro(a)").strip()

    text = (
        "🔨 <b>GUILDA DO PORTO</b>\n"
        f"👩‍✈️ <b>Dora:</b> Certo, <b>{cname}</b>.\n\n"
        "Agora escolha sua <b>profissão</b>.\n"
        "Você pode <b>ler</b> sobre cada uma antes de confirmar.\n\n"
        "🌲 <b>Coleta</b>: explora e extrai recursos.\n"
        "⚒️ <b>Criação</b>: transforma recursos em itens.\n"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌲 Profissões de Coleta", callback_data=CB_PROF_CAT_GATHER)],
        [InlineKeyboardButton("⚒️ Profissões de Criação", callback_data=CB_PROF_CAT_CRAFT)],
    ])

    await msg.reply_text(text, reply_markup=kb, parse_mode="HTML")


async def _show_category(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
    q = update.callback_query
    if not q or not q.message:
        return
    await q.answer()

    keys = []
    for k, v in (PROFESSIONS_DATA or {}).items():
        if (v or {}).get("category") == category:
            keys.append(k)

    title = "🌲 <b>COLETA</b>" if category == "gathering" else "⚒️ <b>CRIAÇÃO</b>"
    text = (
        f"{title}\n\n"
        "Toque em uma profissão para ver detalhes.\n"
        "Depois, confirme quando tiver certeza."
    )

    rows = []
    for k in sorted(keys):
        rows.append([InlineKeyboardButton(f"{_prof_emoji(k)} {_prof_display(k)}", callback_data=f"{CB_PROF_VIEW_PREFIX}{k}")])

    rows.append([InlineKeyboardButton("🔙 Voltar", callback_data=CB_PROF_MENU)])

    await q.message.reply_text(text, reply_markup=InlineKeyboardMarkup(rows), parse_mode="HTML")


async def _show_prof_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, prof_key: str):
    q = update.callback_query
    if not q or not q.message:
        return
    await q.answer()

    info: Dict[str, Any] = PROFESSIONS_DATA.get(prof_key, {}) or {}
    if not info:
        await q.message.reply_text("❌ Profissão inválida.")
        return

    name = _prof_display(prof_key)
    cat = info.get("category")
    cat_label = "Coleta" if cat == "gathering" else "Criação"

    # Recursos (para coleta) aparecem no seu data em "resources"
    resources = info.get("resources", {}) or {}
    res_lines = ""
    if cat == "gathering" and resources:
        res_lines = "\n<b>Você coleta:</b>\n" + "\n".join([f"• {rk}" for rk in resources.keys()])

    text = (
        f"{_prof_emoji(prof_key)} <b>{name}</b>\n"
        f"Categoria: <b>{cat_label}</b>\n\n"
        f"{info.get('description','').strip() or '<i>Sem descrição.</i>'}"
        f"{res_lines}\n\n"
        "⚠️ <b>Atenção:</b> você só pode ter <b>UMA</b> profissão."
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Escolher esta profissão", callback_data=f"{CB_PROF_CONFIRM_PREFIX}{prof_key}")],
        [InlineKeyboardButton("🔙 Ver outras", callback_data=CB_PROF_MENU)],
    ])

    await q.message.reply_text(text, reply_markup=kb, parse_mode="HTML")


async def _confirm_profession(update: Update, context: ContextTypes.DEFAULT_TYPE, prof_key: str):
    q = update.callback_query
    if not q or not q.message:
        return
    await q.answer()

    uid = get_current_player_id(update, context)
    if not uid:
        return

    player_data = await player_manager.get_player_data(uid)
    if not player_data:
        await q.message.reply_text("❌ Erro: personagem não encontrado.")
        return

    # Se já tem profissão, não deixa trocar (regra do seu sistema atual)
    prof_data = player_data.get("profession", {}) or {}
    if prof_data.get("type") or prof_data.get("key"):
        await q.message.reply_text("⚠️ Você já tem uma profissão definida.")
        return

    if prof_key not in PROFESSIONS_DATA:
        await q.message.reply_text("❌ Profissão inválida.")
        return

    # Salva no mesmo formato que seu handler de profissão usa hoje
    player_data["profession"] = {"type": prof_key, "level": 1, "xp": 0}
    player_data.setdefault("tutorial_flags", {})
    player_data["onboarding_stage"] = "tutorial_gathering" if is_gathering_profession(prof_key) else "tutorial_crafting"

    await player_manager.save_player_data(player_data["_id"], player_data)

    await q.message.reply_text(
        f"✅ Profissão definida: <b>{_prof_display(prof_key)}</b>.",
        parse_mode="HTML",
    )

    # Próximo capítulo
    if is_gathering_profession(prof_key):
        from handlers.tutorial import dora_gathering
        await dora_gathering.show_gathering_chapter(update, context, player_data)
    else:
        # Por enquanto, só sinaliza. Depois implementamos o tutorial de criação.
        await q.message.reply_text(
            "⚒️ <b>Próximo passo:</b> Tutorial de Criação.\n"
            "Vamos implementar em seguida (com ferramenta + 5 materiais didáticos).",
            parse_mode="HTML",
        )


async def dora_profession_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return

    data = q.data or ""

    if data == CB_PROF_MENU:
        uid = get_current_player_id(update, context)
        if not uid:
            return
        player_data = await player_manager.get_player_data(uid)
        if not player_data:
            return
        await show_profession_menu(update, context, player_data)
        return

    if data == CB_PROF_CAT_GATHER:
        await _show_category(update, context, "gathering")
        return

    if data == CB_PROF_CAT_CRAFT:
        await _show_category(update, context, "crafting")
        return

    if data.startswith(CB_PROF_VIEW_PREFIX):
        prof_key = data.split(":", 1)[1].strip()
        await _show_prof_detail(update, context, prof_key)
        return

    if data.startswith(CB_PROF_CONFIRM_PREFIX):
        prof_key = data.split(":", 1)[1].strip()
        await _confirm_profession(update, context, prof_key)
        return
