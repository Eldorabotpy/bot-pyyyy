# handlers/class_evolution_handler.py
from __future__ import annotations

import logging
from typing import Dict, Any, List, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from modules import player_manager
from modules import file_ids  # ✅ para buscar vídeo/foto cadastrados

# Tabelas base
try:
    from modules.game_data.classes import CLASSES_DATA as _CLASSES_DATA
except Exception:
    _CLASSES_DATA = {}

try:
    from modules.game_data.items import ITEMS_DATA as _ITEMS_DATA
except Exception:
    _ITEMS_DATA = {}

from modules.game_data.class_evolution import (
    get_evolution_options,
    EVOLUTIONS as _EVOS,
)

logger = logging.getLogger(__name__)


# ============ Utils ============

def _level(pdata: dict) -> int:
    try:
        return int(pdata.get("level") or pdata.get("lvl") or 1)
    except Exception:
        return 1


def _inv_qty(pdata: dict, item_id: str) -> int:
    inv = pdata.get("inventory") or pdata.get("inventario") or {}
    if isinstance(inv, dict):
        try:
            return int(inv.get(item_id, 0))
        except Exception:
            return 0
    if isinstance(inv, list):
        total = 0
        for st in inv:
            sid = st.get("id") or st.get("item_id")
            if sid == item_id:
                try:
                    total += int(st.get("qty", 1))
                except Exception:
                    pass
        return total
    return 0


def _req_check(pdata: dict, req_items: Dict[str, int], min_level: int) -> Tuple[bool, List[str]]:
    lines: List[str] = []
    lvl = _level(pdata)
    lvl_ok = lvl >= int(min_level)
    lines.append(("✅" if lvl_ok else "❌") + f" 🧿 <b>Nível</b>: {lvl}/{min_level}")

    all_ok = lvl_ok
    for iid, need in (req_items or {}).items():
        have = _inv_qty(pdata, iid)
        item = (_ITEMS_DATA or {}).get(iid, {})
        name = item.get("display_name", iid)
        emoji = item.get("emoji", "•")
        ok = have >= int(need)
        all_ok = all_ok and ok
        lines.append(f"{'✅' if ok else '❌'} {emoji} <b>{name}</b>: {have}/{need}")

    return all_ok, lines


def _footer_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 𝐀𝐭𝐮𝐚𝐥𝐢𝐳𝐚𝐫", callback_data="evo_refresh")],
        [InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫 𝐚𝐨 𝐏𝐞𝐫𝐬𝐨𝐧𝐚𝐠𝐞𝐦", callback_data="status_open")],
    ])


def _all_options_for_class(curr_class_key: str) -> List[dict]:
    """
    Retorna TODAS as opções de evolução da classe atual,
    sem filtrar por nível/itens — apenas respeitando 'from_any_of'.
    """
    data = _EVOS.get(curr_class_key) or {}
    out: List[dict] = []
    for tier in ("tier2", "tier3"):
        for opt in data.get(tier, []) or []:
            req_from = opt.get("from_any_of")
            if isinstance(req_from, list) and curr_class_key not in req_from:
                continue
            out.append({"tier": tier, **opt})
    return out


# ============ Renders ============

async def _render_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, as_new: bool = False) -> None:
    user_id = update.effective_user.id
    pdata = player_manager.get_player_data(user_id) or {}

    curr_key = (pdata.get("class") or pdata.get("class_tag") or "").lower()
    curr_cfg = _CLASSES_DATA.get(curr_key, {})
    curr_emoji = curr_cfg.get("emoji", "🧬")
    curr_name = curr_cfg.get("display_name", (pdata.get("class") or "—").title())
    lvl = _level(pdata)

    opts = _all_options_for_class(curr_key)
    logger.info("[EVOL] user=%s class=%s lvl=%s options_all=%s", user_id, curr_key, lvl, len(opts))

    header = [
        "🧬 <b>Evolução de Classe</b>",
        f"Classe atual: {curr_emoji} <b>{curr_name}</b>",
        f"Nível atual: <b>{lvl}</b>",
        ""
    ]

    if not opts:
        text = "\n".join(header + [
            "Não há ramos de evolução configurados para sua classe atual.",
        ])
        if update.callback_query and not as_new:
            try:
                await update.callback_query.edit_message_text(
                    text, reply_markup=_footer_keyboard(), parse_mode="HTML"
                )
                return
            except Exception:
                pass
        await update.effective_chat.send_message(text, reply_markup=_footer_keyboard(), parse_mode="HTML")
        return

    intro_sent = False
    for op in opts:
        to_key = op["to"]
        to_cfg = _CLASSES_DATA.get(to_key, {})
        to_name = to_cfg.get("display_name", to_key.title())
        to_emoji = to_cfg.get("emoji", "✨")

        eligible, req_lines = _req_check(
            pdata, dict(op.get("required_items") or {}), int(op.get("min_level", 0))
        )

        block: List[str] = []
        if not intro_sent:
            block.extend(header)
            intro_sent = True

        block.append("— — — — —")
        block.append(f"{to_emoji} <b>{to_name}</b>  <i>({op.get('tier', '').upper()})</i>")
        if op.get("desc"):
            block.append(f"• {op['desc']}")
        prev = op.get("preview_mods") or {}
        if prev:
            pv = ", ".join([f"{k}: {v}" for k, v in prev.items()])
            block.append(f"• Prévia: {pv}")
        block.append("• Requisitos:")
        block.extend([f"   {ln}" for ln in req_lines])

        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("⚡ Evoluir", callback_data=f"evo_do:{to_key}")]]
            if eligible else
            [[InlineKeyboardButton("❌ Requisitos pendentes", callback_data="evo_refresh")]]
        )

        text = "\n".join(block)

        if update.callback_query and not as_new:
            try:
                await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                await update.effective_chat.send_message(text, reply_markup=kb, parse_mode="HTML")
        else:
            await update.effective_chat.send_message(text, reply_markup=kb, parse_mode="HTML")

    await update.effective_chat.send_message("— — —", reply_markup=_footer_keyboard(), parse_mode="HTML")


# ============ Actions ============

async def open_evolution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _render_menu(update, context, as_new=True)


async def refresh_evolution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q:
        await q.answer()
    await _render_menu(update, context)


async def _send_evolution_media(chat, class_key: str, caption: str | None = None) -> bool:
    """
    Tenta enviar um vídeo/foto para a classe resultante da evolução.
    Ordem de busca:
      1) evolution_video_<classe>
      2) classe_<classe>_media
    Retorna True se alguma mídia foi enviada.
    """
    keys = [f"evolution_video_{class_key}", f"classe_{class_key}_media"]
    for key in keys:
        fd = file_ids.get_file_data(key)
        if not fd or not fd.get("id"):
            continue
        try:
            if (fd.get("type") or "video").lower() == "video":
                await chat.send_video(video=fd["id"], caption=caption or "", parse_mode="HTML")
            else:
                await chat.send_photo(photo=fd["id"], caption=caption or "", parse_mode="HTML")
            return True
        except Exception as e:
            logger.warning("[EVOL_MEDIA] Falha ao enviar %s (%s): %s", key, fd.get("type"), e)
    return False


async def do_evolution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q:
        await q.answer()
    user_id = update.effective_user.id
    pdata = player_manager.get_player_data(user_id) or {}
    lvl = _level(pdata)
    curr_key = (pdata.get("class") or pdata.get("class_tag") or "").lower()

    data = (q.data if q else "") or ""
    _, to_key = data.split(":", 1)

    # Validação final (por nível/itens)
    target = None
    for op in get_evolution_options(curr_key, lvl):
        if op.get("to") == to_key:
            target = op
            break
    if not target:
        await update.effective_chat.send_message(
            "❌ Opção de evolução não disponível no seu nível atual.",
            reply_markup=_footer_keyboard(),
            parse_mode="HTML",
        )
        return

    ok, _ = _req_check(
        pdata, dict(target.get("required_items") or {}), int(target.get("min_level", 0))
    )
    if not ok:
        await update.effective_chat.send_message(
            "❌ Requisitos não atendidos.", reply_markup=_footer_keyboard(), parse_mode="HTML"
        )
        return

    # Debita itens
    req = dict(target.get("required_items") or {})
    inv = pdata.get("inventory") or pdata.get("inventario") or {}
    if isinstance(inv, dict):
        for iid, need in req.items():
            inv[iid] = max(0, int(inv.get(iid, 0)) - int(need))
        pdata["inventory"] = inv
    elif isinstance(inv, list):
        for iid, need in req.items():
            rest = int(need)
            for st in inv:
                sid = st.get("id") or st.get("item_id")
                if sid != iid:
                    continue
                qtty = int(st.get("qty", 1))
                take = min(qtty, rest)
                st["qty"] = qtty - take
                rest -= take
                if rest <= 0:
                    break
        pdata["inventory"] = [s for s in inv if int(s.get("qty", 0)) > 0]

    # Aplica classe nova
    pdata["class"] = to_key
    pdata["class_tag"] = to_key
    player_manager.save_player_data(user_id, pdata)

    # 🎬 Tenta mandar o vídeo de evolução
    to_cfg = _CLASSES_DATA.get(to_key, {})
    pretty = f"{to_cfg.get('emoji','✨')} <b>{to_cfg.get('display_name', to_key.title())}</b>"
    sent = await _send_evolution_media(update.effective_chat, to_key, caption=f"🎉 Evolução concluída: {pretty}")

    # Mensagem de texto (sempre manda)
    await update.effective_chat.send_message(
        f"🎉 Você evoluiu para {pretty}!",
        parse_mode="HTML",
    )

    # Reabre o menu
    await _render_menu(update, context, as_new=True)


# ============ Exports (handlers) ============

status_evolution_open_handler = CallbackQueryHandler(open_evolution, pattern=r"^status_evolution_open$")
evolution_command_handler     = CommandHandler("evoluir", open_evolution)
evolution_callback_handler    = CallbackQueryHandler(refresh_evolution, pattern=r"^evo_refresh$")
evolution_do_handler          = CallbackQueryHandler(do_evolution, pattern=r"^evo_do:.+$")
evolution_cancel_handler      = CallbackQueryHandler(refresh_evolution, pattern=r"^evo_cancel$")