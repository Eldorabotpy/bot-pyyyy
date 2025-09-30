# handlers/admin/equip_builder.py
from __future__ import annotations
import logging
import os
from typing import List, Tuple, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler, CallbackQueryHandler, CommandHandler,
    MessageHandler, ContextTypes, filters
)

ADMIN_ID = int(os.getenv("ADMIN_ID"))
from modules import player_manager
# usamos diretamente o equipamento “novo”
from modules.game_data.equipment import (
    SLOT_ORDER, SLOT_EMOJI, ITEM_DATABASE, get_item_info
)

# tenta fabricar pelo stack novo; senão cai no legado
try:
    from modules import item_factory as new_factory  # type: ignore
except Exception:
    new_factory = None
try:
    from modules import crafting_engine  # type: ignore
except Exception:
    crafting_engine = None
try:
    import modules.display_utils as display_utils  # type: ignore
except Exception:
    display_utils = None

logger = logging.getLogger(__name__)

# Estados
ST_PICK_MODE, ST_TYPE_NAME, ST_PICK_PLAYER, ST_PICK_SLOT, ST_SLOT_ACTION, ST_BASE_SEARCH, ST_BASE_PICK, ST_RARITY, ST_BASE_MANUAL = range(9)

# -------------------------
# Helpers
# -------------------------
def _is_admin(update: Update) -> bool:
    return bool(update.effective_user and update.effective_user.id == ADMIN_ID)

def _kb(rows: List[List[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(rows)

def _list_all_players() -> List[Tuple[int, str]]:
    out: List[Tuple[int, str]] = []
    for uid, pdata in player_manager.iter_players():
        name = pdata.get("character_name") or str(uid)
        out.append((uid, name))
    out.sort(key=lambda x: x[1].lower())
    return out

def _recent_players(limit: int = 10) -> List[Tuple[int, str]]:
    return _list_all_players()[:limit]

def _search_players_by_substring(q: str, limit: int = 20) -> List[Tuple[int, str]]:
    ql = (q or "").strip().lower()
    if not ql:
        return []
    res: List[Tuple[int, str]] = []
    for uid, name in _list_all_players():
        if ql in name.lower():
            res.append((uid, name))
        if len(res) >= limit:
            break
    return res

def _bases_for_slot(slot: str) -> List[Tuple[str, str, str]]:
    """[(base_id, nome_exibicao, emoji_slot)] para o slot."""
    bases: List[Tuple[str, str, str]] = []
    for base_id, info in ITEM_DATABASE.items():
        if str(info.get("slot")) == str(slot):
            nome = info.get("nome_exibicao", base_id)
            emoji = SLOT_EMOJI.get(slot, "▫️")
            bases.append((base_id, nome, emoji))
    bases.sort(key=lambda t: t[1].lower())
    return bases

def _all_bases() -> List[Tuple[str, str, str]]:
    out: List[Tuple[str, str, str]] = []
    for base_id, info in ITEM_DATABASE.items():
        slot = info.get("slot", "")
        nome = info.get("nome_exibicao", base_id)
        emoji = SLOT_EMOJI.get(slot, "▫️")
        out.append((base_id, nome, emoji))
    out.sort(key=lambda t: t[1].lower())
    return out

def _paginate(items: List, page: int, per_page: int = 8):
    total = max(1, ((len(items) - 1) // per_page) + 1)
    page = max(1, min(page, total))
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end], page, total

def _actions_kb() -> InlineKeyboardMarkup:
    return _kb([
        [InlineKeyboardButton("🔎 Buscar base por nome", callback_data="equipgen_act:find")],
        [InlineKeyboardButton("📜 Listar bases do slot", callback_data="equipgen_act:list:1")],
        [InlineKeyboardButton("✍️ Digitar base_id", callback_data="equipgen_act:manual")],
        [InlineKeyboardButton("🎲 Sortear base do slot", callback_data="equipgen_act:random")],
        [InlineKeyboardButton("🏠 Admin", callback_data="admin_main")],
    ])

def _rarity_kb() -> InlineKeyboardMarkup:
    rars = ["comum", "bom", "raro", "epico", "lendario", "auto"]
    rows = [[InlineKeyboardButton(r.upper(), callback_data=f"equipgen_rar:{r}")] for r in rars]
    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="equipgen_back_actions"),
                 InlineKeyboardButton("🏠 Admin", callback_data="admin_main")])
    return _kb(rows)

def _render_item(item: dict, base_id: str, player_class: Optional[str] = None) -> str:
    # se houver utilitário visual
    if display_utils and hasattr(display_utils, "render_item_line"):
        try:
            return display_utils.render_item_line(item, player_class=player_class or item.get("class_tag"))
        except Exception:
            pass
    info = get_item_info(base_id) or {}
    slot = info.get("slot", "")
    nome = item.get("display_name") or info.get("nome_exibicao", base_id)
    emoji = SLOT_EMOJI.get(slot, "▫️")
    rarity = item.get("rarity", "?")
    return f"{emoji} <b>{nome}</b> [`{rarity}`]"

# ---------- criação/entrega ----------
def _create_item_new(pdata: dict, base_id: str, rarity: str) -> dict:
    if not new_factory:
        raise RuntimeError("item_factory ausente")
    for fname in ("create_item_from_base", "create_unique_item", "create"):
        fn = getattr(new_factory, fname, None)
        if callable(fn):
            try:
                if fname == "create_item_from_base":
                    return fn(pdata, base_id, force_rarity=rarity)
                if fname == "create_unique_item":
                    return fn(pdata, base_id, rarity=rarity)
                return fn(base_id=base_id, owner=pdata, force_rarity=rarity)
            except TypeError:
                continue
    raise RuntimeError("Nenhuma função conhecida na item_factory")

def _create_item_legacy(pdata: dict, base_id: str, rarity: str) -> dict:
    if not crafting_engine:
        raise RuntimeError("crafting_engine ausente")
    info = get_item_info(base_id) or {}
    recipe_stub = {
        "display_name": info.get("nome_exibicao", base_id),  # <== usa teu campo
        "emoji": SLOT_EMOJI.get(info.get("slot", ""), ""),   # sem emoji por item
        "profession": info.get("profession", "ferreiro"),
        "level_req": 1,
        "time_seconds": 1,
        "inputs": {},
        "result_base_id": base_id,
        "rarity_chances": {rarity: 1.0} if rarity in ("comum", "bom") else {"comum": 1.0},
        "affix_pools_to_use": ["geral"],
    }
    return crafting_engine._create_dynamic_unique_item(pdata, recipe_stub)  # noqa: SLF001

def _deliver_item(pdata: dict, item: dict) -> None:
    for fname in ("give_item", "add_item", "add_equipment", "add_to_inventory", "add_unique_item"):
        fn = getattr(player_manager, fname, None)
        if callable(fn):
            fn(pdata, item); return
    pdata.setdefault("inventory", []).append(item)

# -------------------------
# Entrada
# -------------------------
async def start_equip_builder_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    q = update.callback_query
    if q:
        await q.answer()
        try: await q.delete_message()
        except Exception: pass

    if not _is_admin(update):
        await context.bot.send_message(chat_id, "Sem permissão.")
        return ConversationHandler.END

    text = "🛠️ <b>Gerador de Equipamentos</b>\n\nComo quer escolher o jogador?"
    kb = _kb([
        [InlineKeyboardButton("🔎 Buscar por nome", callback_data="equipgen_find")],
        [InlineKeyboardButton("📜 Jogadores recentes", callback_data="equipgen_recent")],
        [InlineKeyboardButton("🏠 Admin", callback_data="admin_main")],
    ])
    await context.bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")
    return ST_PICK_MODE

async def cmd_equipgen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        await update.message.reply_text("Sem permissão.")
        return ConversationHandler.END
    return await start_equip_builder_entry(update, context)

# -------------------------
# Fluxo: escolher jogador
# -------------------------
async def pick_mode_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = q.message.chat.id
    data = q.data or ""

    if data == "equipgen_find":
        await context.bot.send_message(chat_id, "Digite parte do <b>nome</b> do personagem:", parse_mode="HTML")
        return ST_TYPE_NAME

    if data == "equipgen_recent":
        rec = _recent_players()
        if not rec:
            await context.bot.send_message(chat_id, "Nenhum jogador encontrado.")
            return ConversationHandler.END

        rows = [[InlineKeyboardButton(name, callback_data=f"equipgen_pick:{uid}")]
                for uid, name in rec]
        rows.append([InlineKeyboardButton("🏠 Admin", callback_data="admin_main")])
        await context.bot.send_message(chat_id, "Escolha o jogador:", reply_markup=_kb(rows))
        return ST_PICK_PLAYER

    return ST_PICK_MODE

async def type_name_recv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        await update.message.reply_text("Sem permissão.")
        return ConversationHandler.END

    query_txt = (update.message.text or "").strip()
    matches = _search_players_by_substring(query_txt)

    if not matches:
        await update.message.reply_text("Nenhum resultado. Tente outra parte do nome.")
        return ST_TYPE_NAME

    rows = [[InlineKeyboardButton(name, callback_data=f"equipgen_pick:{uid}")]
            for uid, name in matches]
    rows.append([InlineKeyboardButton("🏠 Admin", callback_data="admin_main")])
    await update.message.reply_text("Resultados:", reply_markup=_kb(rows))
    return ST_PICK_PLAYER

async def pick_player_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    if not data.startswith("equipgen_pick:"):
        return ST_PICK_PLAYER

    try:
        user_id = int(data.split(":", 1)[1])
    except Exception:
        await q.edit_message_text("Jogador inválido.")
        return ConversationHandler.END

    pdata = player_manager.get_player_data(user_id)
    if not pdata:
        await q.edit_message_text("Jogador não encontrado.")
        return ConversationHandler.END

    context.user_data["tg_target"] = user_id
    name = pdata.get("character_name", str(user_id))

    rows = []
    for slot in SLOT_ORDER:
        emoji = SLOT_EMOJI.get(slot, "▫️")
        rows.append([InlineKeyboardButton(f"{emoji} {slot}", callback_data=f"equipgen_slot:{slot}")])
    rows.append([InlineKeyboardButton("🏠 Admin", callback_data="admin_main")])

    msg = (f"🎯 Jogador selecionado: <b>{name}</b>\n\n"
           f"Escolha o <b>slot</b> do equipamento:")
    try:
        await q.edit_message_text(msg, parse_mode="HTML", reply_markup=_kb(rows))
    except Exception:
        await q.message.reply_text(msg, parse_mode="HTML", reply_markup=_kb(rows))
    return ST_PICK_SLOT

# -------------------------
# Após escolher SLOT -> ações
# -------------------------
async def pick_slot_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    try:
        slot = data.split(":", 1)[1]
    except Exception:
        await q.edit_message_text("Slot inválido.")
        return ConversationHandler.END

    context.user_data["slot"] = slot
    await q.edit_message_text(
        f"✅ Slot escolhido: <b>{slot}</b>\n\nEscolha como quer selecionar a <b>base</b>:",
        parse_mode="HTML",
        reply_markup=_actions_kb(),
    )
    return ST_SLOT_ACTION

async def slot_action_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = (q.data or "")
    parts = data.split(":")
    action = parts[1]
    slot = context.user_data.get("slot")

    if action == "find":
        await q.edit_message_text(
            "Digite parte do <b>nome</b> (nome_exibicao) ou <b>base_id</b>.\n"
            "Dica: “✍️ Digitar base_id” aceita o id exato imediatamente.",
            parse_mode="HTML"
        )
        return ST_BASE_SEARCH

    if action == "manual":
        await q.edit_message_text("✍️ Digite o <b>base_id</b> exato:", parse_mode="HTML")
        return ST_BASE_MANUAL

    if action == "list":
        page = int(parts[2]) if len(parts) > 2 else 1
        items = _bases_for_slot(slot)
        if not items:
            await q.edit_message_text(
                "⚠️ Nenhuma base cadastrada para este slot.\n\nEscolha outra opção:",
                parse_mode="HTML",
                reply_markup=_actions_kb()
            )
            return ST_SLOT_ACTION
        page_items, page, total = _paginate(items, page)
        rows = [[InlineKeyboardButton(f"{em} {name}", callback_data=f"equipgen_base:{bid}")]
                for (bid, name, em) in page_items]
        nav = []
        if page > 1:
            nav.append(InlineKeyboardButton("◀️ Anterior", callback_data=f"equipgen_act:list:{page-1}"))
        if page < total:
            nav.append(InlineKeyboardButton("Próxima ▶️", callback_data=f"equipgen_act:list:{page+1}"))
        if nav:
            rows.append(nav)
        rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="equipgen_back_actions"),
                     InlineKeyboardButton("🏠 Admin", callback_data="admin_main")])
        await q.edit_message_text(
            f"📜 Bases para <b>{slot}</b> — página {page}/{total}",
            parse_mode="HTML",
            reply_markup=_kb(rows)
        )
        return ST_BASE_PICK

    if action == "random":
        items = _bases_for_slot(slot)
        if not items:
            await q.edit_message_text(
                "⚠️ Nenhuma base cadastrada para este slot.\n\nEscolha outra opção:",
                parse_mode="HTML",
                reply_markup=_actions_kb()
            )
            return ST_SLOT_ACTION
        import random
        bid, name, em = random.choice(items)
        context.user_data["base_id"] = bid
        await q.edit_message_text(
            f"🎲 Base sorteada: {em} <b>{name}</b>\n\nEscolha a raridade:",
            parse_mode="HTML",
            reply_markup=_rarity_kb()
        )
        return ST_RARITY

    return ST_SLOT_ACTION

async def back_to_actions_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    slot = context.user_data.get("slot")
    await q.edit_message_text(
        f"✅ Slot escolhido: <b>{slot}</b>\n\nEscolha como quer selecionar a <b>base</b>:",
        parse_mode="HTML",
        reply_markup=_actions_kb(),
    )
    return ST_SLOT_ACTION

# --- busca por texto (slot preferencial; cai para global) ---
async def base_search_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    slot = context.user_data.get("slot")
    query = (update.message.text or "").strip().lower()

    # match direto de base_id
    if query in ITEM_DATABASE:
        context.user_data["base_id"] = query
        await update.message.reply_text("📦 Base escolhida.\n\nEscolha a raridade:", reply_markup=_rarity_kb(), parse_mode="HTML")
        return ST_RARITY

    pool = _bases_for_slot(slot) or _all_bases()
    matches = []
    for bid, name, em in pool:
        if query in bid.lower() or query in name.lower():
            matches.append((bid, name, em))
        if len(matches) >= 30:
            break

    if not matches:
        await update.message.reply_text(
            "Nenhuma base encontrada. Você pode clicar em “✍️ Digitar base_id”.",
            reply_markup=_actions_kb(),
            parse_mode="HTML"
        )
        return ST_SLOT_ACTION

    rows = [[InlineKeyboardButton(f"{em} {name}", callback_data=f"equipgen_base:{bid}")]
            for bid, name, em in matches]
    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="equipgen_back_actions"),
                 InlineKeyboardButton("🏠 Admin", callback_data="admin_main")])
    await update.message.reply_text("Resultados:", reply_markup=_kb(rows))
    return ST_BASE_PICK

# --- base manual ---
async def base_manual_recv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    base_id = (update.message.text or "").strip()
    # aceita mesmo que não esteja no catálogo (desde que a engine suporte)
    context.user_data["base_id"] = base_id
    await update.message.reply_text(
        f"📦 Base escolhida: <code>{base_id}</code>\n\nEscolha a raridade:",
        parse_mode="HTML",
        reply_markup=_rarity_kb()
    )
    return ST_RARITY

# --- escolher base (por botão) ---
async def pick_base_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    if not data.startswith("equipgen_base:"):
        return ST_BASE_PICK
    base_id = data.split(":", 1)[1]
    info = get_item_info(base_id) or {}
    nome = info.get("nome_exibicao", base_id)
    em = SLOT_EMOJI.get(info.get("slot", ""), "▫️")
    context.user_data["base_id"] = base_id
    await q.edit_message_text(
        f"📦 Base escolhida: {em} <b>{nome}</b>\n\nEscolha a raridade:",
        parse_mode="HTML",
        reply_markup=_rarity_kb()
    )
    return ST_RARITY

# --- escolher raridade e criar ---
def _determine_rarity_auto(player_level: int, luck: int) -> str:
    weights = {'comum':80.0,'bom':15.0,'raro':4.0,'epico':0.9,'lendario':0.1}
    bonus = (player_level / 120.0) + (luck / 150.0)
    for k in ('bom','raro','epico','lendario'):
        weights[k] *= (1.0 + bonus)
    import random as _rnd
    return _rnd.choices(list(weights.keys()), weights=list(weights.values()), k=1)[0]

async def pick_rarity_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    if not data.startswith("equipgen_rar:"):
        return ST_RARITY
    rarity = data.split(":", 1)[1]

    user_id = context.user_data.get("tg_target")
    base_id = context.user_data.get("base_id")
    if not (user_id and base_id):
        await q.edit_message_text("Contexto perdido. Reabra o gerador.")
        return ConversationHandler.END

    pdata = player_manager.get_player_data(user_id)
    if not pdata:
        await q.edit_message_text("Jogador não encontrado.")
        return ConversationHandler.END

    if rarity == "auto":
        total_stats = player_manager.get_player_total_stats(pdata) or {}
        luck = int(total_stats.get("luck", 5))
        p_level = int(pdata.get("level", 1))
        rarity = _determine_rarity_auto(p_level, luck)

    try:
        item = _create_item_new(pdata, base_id, rarity)
    except Exception:
        item = _create_item_legacy(pdata, base_id, rarity)

    _deliver_item(pdata, item)
    player_manager.save_player_data(user_id, pdata)

    preview = _render_item(item, base_id)
    rows = [[InlineKeyboardButton("🏠 Admin", callback_data="admin_main")]]
    await q.edit_message_text(
        f"✅ Item criado e entregue!\n\n{preview}",
        parse_mode="HTML",
        reply_markup=_kb(rows)
    )
    return ConversationHandler.END

# -------------------------
# Conversation handler
# -------------------------
equip_builder_conv = ConversationHandler(
    entry_points=[
        CommandHandler("equipgen", cmd_equipgen, filters=filters.User(ADMIN_ID)),
        CallbackQueryHandler(start_equip_builder_entry, pattern=r"^admin_equipgen$"),
    ],
    states={
        ST_PICK_MODE: [
            CallbackQueryHandler(pick_mode_cb, pattern=r"^equipgen_(find|recent)$"),
        ],
        ST_TYPE_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID), type_name_recv),
        ],
        ST_PICK_PLAYER: [
            CallbackQueryHandler(pick_player_cb, pattern=r"^equipgen_pick:\d+$"),
        ],
        ST_PICK_SLOT: [
            CallbackQueryHandler(pick_slot_cb, pattern=r"^equipgen_slot:[a-z_]+$"),
        ],
        ST_SLOT_ACTION: [
            CallbackQueryHandler(slot_action_cb, pattern=r"^equipgen_act:(?:find|random|manual)$"),
            CallbackQueryHandler(slot_action_cb, pattern=r"^equipgen_act:list:\d+$"),
            CallbackQueryHandler(back_to_actions_cb, pattern=r"^equipgen_back_actions$"),
        ],
        ST_BASE_SEARCH: [
            MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID), base_search_text),
        ],
        ST_BASE_MANUAL: [
            MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID), base_manual_recv),
        ],
        ST_BASE_PICK: [
            CallbackQueryHandler(pick_base_cb, pattern=r"^equipgen_base:[a-z0-9_]+$"),
            CallbackQueryHandler(slot_action_cb, pattern=r"^equipgen_act:list:\d+$"),
            CallbackQueryHandler(back_to_actions_cb, pattern=r"^equipgen_back_actions$"),
        ],
        ST_RARITY: [
            CallbackQueryHandler(pick_rarity_cb, pattern=r"^equipgen_rar:(comum|bom|raro|epico|lendario|auto)$"),
            CallbackQueryHandler(back_to_actions_cb, pattern=r"^equipgen_back_actions$"),
        ],
    },
    fallbacks=[],
    per_user=True,
    per_chat=True,
    name="equip_builder_conv",
    persistent=False,
)
