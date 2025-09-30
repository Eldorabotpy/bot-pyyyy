# handlers/admin/itemgen_conv.py

import random
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CallbackQueryHandler,
    MessageHandler, CommandHandler, filters
)

from modules import player_manager, game_data

# --- tentativas de integrações disponíveis ---
try:
    from modules import item_factory as new_factory  # stack novo (se houver)
except Exception:
    new_factory = None

try:
    from modules import crafting_engine  # fallback legado
except Exception:
    crafting_engine = None  # type: ignore

try:
    import modules.display_utils as display_utils  # render bonito (se houver)
except Exception:
    display_utils = None

STATE_GET_PLAYER, STATE_GET_BASE, STATE_GET_CLASS, STATE_GET_LVL, STATE_GET_RAR = range(5)
ADMIN_ID = int(os.getenv("ADMIN_ID"))
# -----------------------
# Helpers
# -----------------------
def _is_admin(update: Update) -> bool:
    return bool(update.effective_user and update.effective_user.id == ADMIN_ID)

def _base_durability(base_id: str) -> int:
    return int(game_data.ITEM_BASES.get(base_id, {}).get("durability", 100))

def _determine_rarity_auto(player_level: int, luck: int) -> str:
    weights = {
        'comum':   80.0,
        'bom':     15.0,
        'raro':     4.0,
        'epico':    0.9,
        'lendario': 0.1,
    }
    bonus = (player_level / 120.0) + (luck / 150.0)
    for k in ('bom', 'raro', 'epico', 'lendario'):
        weights[k] *= (1.0 + bonus)
    rarities = list(weights.keys())
    chances = list(weights.values())
    return random.choices(rarities, weights=chances, k=1)[0]

def _kb(rows):
    return InlineKeyboardMarkup(rows)

def _classes_kb():
    rows = []
    for cls in game_data.CLASS_DMG_EMOJI.keys():
        rows.append([InlineKeyboardButton(cls.capitalize(), callback_data=f"itemgen_pick_class:{cls}")])
    rows.append([InlineKeyboardButton("⬅️ Voltar ao Admin", callback_data="admin_main")])
    return _kb(rows)

def _rarity_kb():
    rars = ["comum", "bom", "raro", "epico", "lendario", "auto"]
    rows = [[InlineKeyboardButton(r.upper(), callback_data=f"itemgen_pick_rar:{r}")] for r in rars]
    rows.append([InlineKeyboardButton("⬅️ Voltar ao Admin", callback_data="admin_main")])
    return _kb(rows)

def _render_item_line(item: dict, player_class: str) -> str:
    if display_utils and hasattr(display_utils, "render_item_line"):
        try:
            return display_utils.render_item_line(item, player_class=player_class)
        except Exception:
            pass
    # fallback simples
    name = item.get("display_name") or game_data.ITEM_BASES.get(item.get("base_id",""), {}).get("display_name") or item.get("base_id","Item")
    emoji = item.get("emoji", "")
    rarity = item.get("rarity", "?")
    lvl = item.get("level", item.get("player_level", "?"))
    return f"{emoji} <b>{name}</b> [{rarity}] — classe: {player_class} — nível: {lvl}"

# ---------- criação/entrega com preferência pelo stack novo ----------
def _create_item_new(pdata: dict, base_id: str, rarity: str, player_class: str, player_level: int, durab: int) -> dict:
    if not new_factory:
        raise RuntimeError("item_factory ausente")
    # tenta algumas assinaturas comuns
    fn = getattr(new_factory, "create_item_from_base", None)
    if callable(fn):
        item = fn(pdata, base_id, force_rarity=rarity)
    else:
        fn = getattr(new_factory, "create_unique_item", None)
        if callable(fn):
            item = fn(pdata, base_id, rarity=rarity)
        else:
            fn = getattr(new_factory, "create", None)
            if callable(fn):
                item = fn(base_id=base_id, owner=pdata, force_rarity=rarity)
            else:
                raise RuntimeError("Nenhuma função conhecida na item_factory")

    # garante metadados desejados
    item.setdefault("base_id", base_id)
    item.setdefault("rarity", rarity)
    item.setdefault("emoji", game_data.ITEM_BASES.get(base_id, {}).get("emoji", ""))
    item.setdefault("display_name", game_data.ITEM_BASES.get(base_id, {}).get("display_name", base_id))
    item["player_level"] = player_level
    item["class_tag"] = player_class
    item["durability"] = durab
    return item

def _create_item_legacy(pdata: dict, base_id: str, rarity: str, player_class: str, player_level: int, durab: int) -> dict:
    if not crafting_engine:
        raise RuntimeError("crafting_engine ausente")
    # stub mínimo para a engine
    info = game_data.ITEM_BASES.get(base_id, {})
    recipe_stub = {
        "display_name": info.get("display_name", base_id),
        "emoji": info.get("emoji", ""),
        "profession": info.get("profession", "ferreiro"),
        "level_req": 1,
        "time_seconds": 1,
        "inputs": {},
        "result_base_id": base_id,
        "rarity_chances": {rarity: 1.0} if rarity in ("comum","bom") else {"comum": 1.0},
        "affix_pools_to_use": ["geral"],
    }
    item = crafting_engine._create_dynamic_unique_item(pdata, recipe_stub)  # noqa: SLF001
    # injeta metadados extras desejados
    item.setdefault("base_id", base_id)
    item.setdefault("emoji", info.get("emoji",""))
    item.setdefault("display_name", info.get("display_name", base_id))
    item["rarity"] = item.get("rarity", rarity)
    item["player_level"] = player_level
    item["class_tag"] = player_class
    item["durability"] = durab
    return item

def _deliver_item(pdata: dict, item: dict) -> None:
    # preferir métodos novos, mas cair para o legado
    for fname in ("give_item", "add_item", "add_equipment", "add_to_inventory", "add_unique_item"):
        fn = getattr(player_manager, fname, None)
        if callable(fn):
            fn(pdata, item)
            return
    # último recurso
    pdata.setdefault("inventory", []).append(item)

# -----------------------
# Fluxo
# -----------------------
async def start_itemgen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_cb = bool(update.callback_query)
    chat_id = update.effective_chat.id

    if not _is_admin(update):
        if is_cb:
            await update.callback_query.answer("Sem permissão.", show_alert=True)
        else:
            await update.message.reply_text("Sem permissão.")
        return ConversationHandler.END

    if is_cb:
        await update.callback_query.answer()
        try:
            await update.callback_query.delete_message()
        except Exception:
            pass

    await context.bot.send_message(
        chat_id,
        "👤 Nome <b>exato</b> do personagem destino? (ou /cancelar)",
        parse_mode="HTML"
    )
    return STATE_GET_PLAYER

async def recv_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        await update.message.reply_text("Sem permissão.")
        return ConversationHandler.END

    name = (update.message.text or "").strip()
    res = player_manager.find_player_by_name(name)
    if not res:
        await update.message.reply_text("Jogador não encontrado. /cancelar")
        return ConversationHandler.END

    target_user_id, pdata = res
    context.user_data["tg_target"] = target_user_id

    await update.message.reply_text(
        "📦 Base do item?\n"
        "Ex.: <code>espada_larga_mithril</code>, <code>adaga_sombria</code>\n\n"
        f"Opções atuais ({len(game_data.ITEM_BASES)}):\n"
        + ", ".join(f"<code>{k}</code>" for k in game_data.ITEM_BASES.keys()),
        parse_mode="HTML"
    )
    return STATE_GET_BASE

async def recv_base(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        await update.message.reply_text("Sem permissão.")
        return ConversationHandler.END

    base_key = (update.message.text or "").strip()
    if base_key not in game_data.ITEM_BASES:
        await update.message.reply_text("Base inválida. /cancelar")
        return ConversationHandler.END

    context.user_data["base_key"] = base_key
    await update.message.reply_text(
        "🧭 Classe do dano? "
        "(assassino, samurai, guerreiro, berserker, cacador, monge, mago, bardo)",
        reply_markup=_classes_kb()
    )
    return STATE_GET_CLASS

async def recv_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        await update.message.reply_text("Sem permissão.")
        return ConversationHandler.END

    cls = (update.message.text or "").strip().lower()
    if cls not in game_data.CLASS_DMG_EMOJI:
        await update.message.reply_text("Classe inválida. /cancelar")
        return ConversationHandler.END

    context.user_data["class_key"] = cls
    await update.message.reply_text("🔢 Nível para marcar no item? (ex.: 1, 10, 25)")
    return STATE_GET_LVL

async def pick_class_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    _, cls = data.split(":", 1)
    if cls not in game_data.CLASS_DMG_EMOJI:
        await q.edit_message_text("Classe inválida.")
        return ConversationHandler.END

    context.user_data["class_key"] = cls
    await q.edit_message_text("🔢 Nível para marcar no item? (ex.: 1, 10, 25)")
    return STATE_GET_LVL

async def recv_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        await update.message.reply_text("Sem permissão.")
        return ConversationHandler.END

    try:
        lvl = int((update.message.text or "").strip())
    except Exception:
        await update.message.reply_text("Nível inválido. /cancelar")
        return ConversationHandler.END

    context.user_data["lvl"] = lvl
    await update.message.reply_text(
        "⭐ Raridade? Escolha ou digite:\n"
        "<code>comum</code>, <code>bom</code>, <code>raro</code>, <code>epico</code>, <code>lendario</code>, <code>auto</code>",
        parse_mode="HTML",
        reply_markup=_rarity_kb()
    )
    return STATE_GET_RAR

async def recv_rarity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        await update.message.reply_text("Sem permissão.")
        return ConversationHandler.END

    rar = (update.message.text or "").strip().lower()
    if rar not in ("comum", "bom", "raro", "epico", "lendario", "auto"):
        await update.message.reply_text("Raridade inválida. /cancelar")
        return ConversationHandler.END

    return await _finalize_and_give(update, context, rar)

async def pick_rarity_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    _, rar = data.split(":", 1)
    if rar not in ("comum", "bom", "raro", "epico", "lendario", "auto"):
        await q.edit_message_text("Raridade inválida.")
        return ConversationHandler.END

    # reusa o chat para saída padrão
    dummy_update = Update(update.update_id, message=q.message)
    return await _finalize_and_give(dummy_update, context, rar)

async def _finalize_and_give(update: Update, context: ContextTypes.DEFAULT_TYPE, rar: str):
    user_id = context.user_data.get("tg_target")
    if not user_id:
        await update.message.reply_text("Jogador não selecionado. /cancelar")
        return ConversationHandler.END

    pdata = player_manager.get_player_data(user_id)
    if not pdata:
        await update.message.reply_text("Jogador não encontrado. /cancelar")
        return ConversationHandler.END

    base_key = context.user_data.get("base_key")
    cls = context.user_data.get("class_key")
    lvl = int(context.user_data.get("lvl", 1))

    if rar == "auto":
        total_stats = player_manager.get_player_total_stats(pdata) or {}
        luck = int(total_stats.get("luck", 5))
        rarity = _determine_rarity_auto(lvl, luck)
    else:
        rarity = rar

    durab = _base_durability(base_key)

    # gerar item (novo -> legado)
    try:
        inst = _create_item_new(pdata, base_key, rarity, cls, lvl, durab)
    except Exception:
        inst = _create_item_legacy(pdata, base_key, rarity, cls, lvl, durab)

    _deliver_item(pdata, inst)
    player_manager.save_player_data(user_id, pdata)

    preview = _render_item_line(inst, player_class=cls)
    kb = [[InlineKeyboardButton("⬅️ Voltar ao Admin", callback_data="admin_main")]]
    await update.message.reply_text(
        f"✅ Item entregue!\n\n{preview}",
        reply_markup=_kb(kb),
        parse_mode="HTML"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return ConversationHandler.END
    await update.message.reply_text("Cancelado.")
    return ConversationHandler.END

itemgen_conversation = ConversationHandler(
    entry_points=[
        CommandHandler("itemgen", start_itemgen, filters=filters.User(ADMIN_ID)),
        CallbackQueryHandler(start_itemgen, pattern=r"^admin_itemgen$"),  # opcional via botão
    ],
    states={
        STATE_GET_PLAYER: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID), recv_player)],
        STATE_GET_BASE:   [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID), recv_base)],
        STATE_GET_CLASS:  [
            MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID), recv_class),
            CallbackQueryHandler(pick_class_cb, pattern=r"^itemgen_pick_class:[a-z_]+$"),
        ],
        STATE_GET_LVL:    [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID), recv_level)],
        STATE_GET_RAR:    [
            MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID), recv_rarity),
            CallbackQueryHandler(pick_rarity_cb, pattern=r"^itemgen_pick_rar:(comum|bom|raro|epico|lendario|auto)$"),
        ],
    },
    fallbacks=[CommandHandler("cancelar", cancel, filters=filters.User(ADMIN_ID))],
    per_user=True, per_chat=True,
)
