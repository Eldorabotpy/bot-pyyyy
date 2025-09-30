# modules/dungeons/engine.py
from __future__ import annotations
import logging, random
from typing import Callable, Dict, Optional, List

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
)

from modules import player_manager, file_ids
from .config import (
    DIFFICULTIES, DEFAULT_DIFFICULTY_ORDER,
    ENTRY_KEY_ITEM_ID, EVOLUTION_ITEM_POOL,
)
from .regions import REGIONAL_DUNGEONS, MobDef

log = logging.getLogger(__name__)

# ===== Hook de combate (injeção) =====
CombatFn = Callable[[Update, ContextTypes.DEFAULT_TYPE, dict], "bool|int|None"]
_COMBAT_HOOK: Optional[CombatFn] = None

def set_combat_hook(fn: Optional[CombatFn]) -> None:
    """Permite ao main.py (ou outro módulo) plugar a engine de combate."""
    global _COMBAT_HOOK
    _COMBAT_HOOK = fn

# ===== Helpers =====
def _kb(rows): return InlineKeyboardMarkup(rows)

def _scale_stats(stats_base: Dict[str, int], mult: float) -> Dict[str, int]:
    return {k: max(1, int(round(v * mult))) for k, v in stats_base.items()}

async def _send_media(chat, media_key: Optional[str], caption: str):
    if not media_key:
        await chat.send_message(caption, parse_mode="HTML"); return
    fd = file_ids.get_file_data(media_key)
    if not fd or not fd.get("id"):
        await chat.send_message(caption, parse_mode="HTML"); return
    if (fd.get("type") or "video").lower() == "video":
        await chat.send_video(fd["id"], caption=caption, parse_mode="HTML")
    else:
        await chat.send_photo(fd["id"], caption=caption, parse_mode="HTML")

def _inv_has(pdata: dict, item_id: str, need: int) -> bool:
    inv = pdata.get("inventory") or {}
    if isinstance(inv, dict): return int(inv.get(item_id, 0)) >= need
    if isinstance(inv, list):
        c = 0
        for st in inv:
            if (st.get("id") or st.get("item_id")) == item_id: c += int(st.get("qty", 1))
        return c >= need
    return False

def _inv_consume(pdata: dict, item_id: str, qty: int) -> None:
    inv = pdata.get("inventory") or {}
    if isinstance(inv, dict):
        inv[item_id] = max(0, int(inv.get(item_id, 0)) - qty)
        pdata["inventory"] = inv; return
    if isinstance(inv, list):
        rest = qty
        for st in inv:
            if (st.get("id") or st.get("item_id")) != item_id: continue
            qtty = int(st.get("qty", 1))
            take = min(qtty, rest)
            st["qty"] = qtty - take
            rest -= take
            if rest <= 0: break
        pdata["inventory"] = [s for s in inv if int(s.get("qty", 0)) > 0]

def _inv_add(pdata: dict, item_id: str, qty: int = 1) -> None:
    inv = pdata.get("inventory") or {}
    if isinstance(inv, dict):
        inv[item_id] = int(inv.get(item_id, 0)) + qty
        pdata["inventory"] = inv; return
    if isinstance(inv, list):
        for st in inv:
            if (st.get("id") or st.get("item_id")) == item_id:
                st["qty"] = int(st.get("qty", 1)) + qty
                pdata["inventory"] = inv; return
        inv.append({"id": item_id, "qty": qty})
        pdata["inventory"] = inv

STATE_KEY = "dgn2"

# ===== Hub / UX =====
async def open_dungeon_hub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = []
    for rkey, cfg in REGIONAL_DUNGEONS.items():
        label = f"{cfg.get('emoji','🗺️')} {cfg['label']}"
        rows.append([InlineKeyboardButton(label, callback_data=f"d2_region:{rkey}")])
    txt = "🏰 <b>Calabouços</b>\n\nEscolha a <b>região</b>:"
    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(txt, reply_markup=_kb(rows), parse_mode="HTML")
        except Exception:
            await update.effective_chat.send_message(txt, reply_markup=_kb(rows), parse_mode="HTML")
    else:
        await update.effective_chat.send_message(txt, reply_markup=_kb(rows), parse_mode="HTML")

async def pick_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    rkey = q.data.split(":", 1)[1]
    cfg = REGIONAL_DUNGEONS.get(rkey)
    if not cfg:
        await q.edit_message_text("Região inválida."); return

    rows = []
    for dkey in DEFAULT_DIFFICULTY_ORDER:
        d = DIFFICULTIES[dkey]
        rows.append([InlineKeyboardButton(
            f"{d.emoji} {d.label} — custo {d.key_cost}x Cristal",
            callback_data=f"d2_enter:{rkey}:{dkey}"
        )])
    rows.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="d2_home")])
    txt = f"{cfg.get('emoji','🗺️')} <b>{cfg['label']}</b>\n\nEscolha a <b>dificuldade</b>:"
    await q.edit_message_text(txt, reply_markup=_kb(rows), parse_mode="HTML")

async def enter_dungeon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, rkey, dkey = q.data.split(":", 2)
    rcfg = REGIONAL_DUNGEONS.get(rkey)
    diff = DIFFICULTIES.get(dkey)
    if not rcfg or not diff:
        await q.edit_message_text("Parâmetros inválidos."); return

    user_id = update.effective_user.id
    pdata = player_manager.get_player_data(user_id) or {}

    if not _inv_has(pdata, ENTRY_KEY_ITEM_ID, diff.key_cost):
        await q.edit_message_text("❌ Você não possui chaves suficientes (Cristal de Abertura)."); return

    _inv_consume(pdata, ENTRY_KEY_ITEM_ID, diff.key_cost)
    player_manager.save_player_data(user_id, pdata)

    context.user_data[STATE_KEY] = {"region": rkey, "diff": dkey, "i": 0}
    await q.edit_message_text(
        f"🔮 Portal aberto para <b>{rcfg['label']}</b> — {diff.emoji} <b>{diff.label}</b>!",
        parse_mode="HTML"
    )
    await _next_floor(update, context)

async def _next_floor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    st = context.user_data.get(STATE_KEY) or {}
    rkey, dkey, i = st.get("region"), st.get("diff"), int(st.get("i", 0))
    rcfg = REGIONAL_DUNGEONS.get(rkey); diff = DIFFICULTIES.get(dkey)
    if not rcfg or not diff:
        await update.effective_chat.send_message("⚠️ Expedição inválida.")
        context.user_data[STATE_KEY] = None; return

    floors: List[MobDef] = rcfg["floors"]  # type: ignore
    total = len(floors)
    if i >= total:
        # Recompensa final
        gold_base = int(rcfg.get("gold_base", 0))
        gold = int(round(gold_base * diff.gold_mult))
        evo_item = random.choice(EVOLUTION_ITEM_POOL) if EVOLUTION_ITEM_POOL else None

        user_id = update.effective_user.id
        pdata = player_manager.get_player_data(user_id) or {}
        pdata["gold"] = int(pdata.get("gold", 0)) + gold
        if evo_item: _inv_add(pdata, evo_item, 1)
        player_manager.save_player_data(user_id, pdata)

        extra = f" + 1x <code>{evo_item}</code>" if evo_item else ""
        await update.effective_chat.send_message(
            f"🏆 <b>Calabouço concluído!</b>\nRecompensa: <b>{gold} ouro</b>{extra}",
            parse_mode="HTML"
        )
        context.user_data[STATE_KEY] = None
        return

    mob = floors[i]
    scaled = _scale_stats(mob.stats_base, diff.stat_mult)
    intro = (
        f"⚔️ Andar {i+1}/{total} — {mob.emoji} <b>{mob.display}</b>\n"
        f"<i>Dificuldade:</i> {diff.emoji} {diff.label}\n"
        f"<i>Stats:</i> HP {scaled['max_hp']} | ATK {scaled['attack']} | "
        f"DEF {scaled['defense']} | INI {scaled['initiative']} | LUCK {scaled['luck']}"
    )
    await _send_media(update.effective_chat, mob.media_key, caption=intro)

    # Combate
    won = True
    if _COMBAT_HOOK:
        try:
            won = bool(await _COMBAT_HOOK(update, context, {
                "mob_key": mob.key,
                "display": mob.display,
                "emoji": mob.emoji,
                "stats": scaled,
                "region": rkey,
                "difficulty": dkey,
            }))
        except Exception as e:
            log.exception("[DGN2] Erro no hook de combate: %s", e)
            won = False
    else:
        await update.effective_chat.send_message(
            "🧪 (Sem engine de combate ligada — simulando vitória para teste)", parse_mode="HTML"
        )
        won = True

    if not won:
        context.user_data[STATE_KEY] = None
        await update.effective_chat.send_message("💀 Você foi derrotado e expulso do calabouço.", parse_mode="HTML")
        return

    # Próximo
    context.user_data[STATE_KEY]["i"] = i + 1
    await update.effective_chat.send_message("✅ Vitória! Avançando…", parse_mode="HTML")
    await _next_floor(update, context)

# ===== Exports (Handlers) =====
dungeons_hub_command      = CommandHandler("calaboucos", open_dungeon_hub)
dungeons_hub_open_cb      = CallbackQueryHandler(open_dungeon_hub, pattern=r"^d2_home$")
dungeons_region_pick_cb   = CallbackQueryHandler(pick_region,     pattern=r"^d2_region:.+$")
dungeons_enter_cb         = CallbackQueryHandler(enter_dungeon,   pattern=r"^d2_enter:.+:.+$")
