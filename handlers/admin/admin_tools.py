# handlers/admin/admin_tools.py
from __future__ import annotations

import logging
from typing import Optional, Tuple

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from modules import player_manager
from modules.balance import STAT_RULES

# Catálogos (podem não existir em setups antigos)
try:
    from modules.game_data.classes import CLASSES_DATA
except Exception:
    CLASSES_DATA = {}

try:
    from modules.game_data import PROFESSIONS_DATA
except Exception:
    PROFESSIONS_DATA = {}

logger = logging.getLogger(__name__)

# ------- helpers de normalização --------
def _normalize(s: str) -> str:
    return (s or "").strip().lower()

def _slugify(s: str) -> str:
    import re, unicodedata
    if not s:
        return ""
    norm = unicodedata.normalize("NFKD", s)
    norm = norm.encode("ascii", "ignore").decode("ascii")
    norm = re.sub(r"\s+", "_", norm.strip().lower())
    norm = re.sub(r"[^a-z0-9_]", "", norm)
    return norm

def _resolve_user(user_token: str) -> Tuple[Optional[int], Optional[dict], str]:
    """
    Tenta resolver <user_token> como:
      - ID numérico (players/<id>.json)
      - Nome do personagem (exato, case-insensitive)
    Retorna (user_id, player_data, erro_msg)
    """
    token = (user_token or "").strip()
    if not token:
        return None, None, "Forneça um ID ou nome."
    # 1) ID
    if token.isdigit():
        uid = int(token)
        pdata = player_manager.get_player_data(uid)
        if pdata:
            return uid, pdata, ""
        return None, None, f"Jogador com ID {uid} não encontrado."
    # 2) Nome
    res = player_manager.find_player_by_name(token)
    if res:
        uid, pdata = res
        return uid, pdata, ""
    return None, None, f"Jogador '{token}' não encontrado. Use ID numérico ou nome exato."

def _reset_points_inplace(pdata: dict) -> None:
    inv = pdata.setdefault("invested", {})
    for s in STAT_RULES.keys():
        inv[s] = 0
    pdata["invested"] = inv
    pdata["point_pool"] = 0           # novo pool
    pdata["stat_points"] = 0          # legado, para não conflitar
    # clamp HP atual ao máximo atual
    try:
        totals = player_manager.get_player_total_stats(pdata)
        max_hp = int(totals.get("max_hp", 1))
        cur = int(pdata.get("current_hp", max_hp))
        pdata["current_hp"] = max(0, min(cur, max_hp))
    except Exception:
        pass

# ======= UI base =======
def _menu_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("🔁 𓂀 ℤ𝕖𝕣𝕒𝕣 𝕡𝕠𝕟𝕥𝕠𝕤 (𝕋𝕆𝔻𝕆𝕊) 𓂀", callback_data="admtools_reset_all_confirm")],
        [InlineKeyboardButton("🧹 𓂀 ℤ𝕖𝕣𝕒𝕣 𝕡𝕠𝕟𝕥𝕠𝕤 (𝕁𝕠𝕘𝕒𝕕𝕠𝕣) 𓂀", callback_data="admtools_reset_one")],
        [InlineKeyboardButton("📈 𓂀 𝔻𝕖𝕗𝕚𝕟𝕚𝕣 ℕí𝕧𝕖𝕝 (𝕁𝕠𝕘𝕒𝕕𝕠𝕣) 𓂀", callback_data="admtools_set_level")],
        [InlineKeyboardButton("🎭 𓂀 𝕄𝕦𝕕𝕒𝕣 ℂ𝕝𝕒𝕤𝕤𝕖 (𝕁𝕠𝕘𝕒𝕕𝕠𝕣) 𓂀", callback_data="admtools_set_class")],
        [InlineKeyboardButton("🛠️ 𓂀 𝕄𝕦𝕕𝕒𝕣 ℙ𝕣𝕠𝕗𝕚𝕤𝕤ã𝕠 (𝕁𝕠𝕘𝕒𝕕𝕠𝕣) 𓂀", callback_data="admtools_set_prof")],
        [InlineKeyboardButton("❌ 𓂀 𝔽𝕖𝕔𝕙𝕒𝕣 𓂀", callback_data="admtools_close")],
    ]
    return InlineKeyboardMarkup(rows)

async def adm_tools_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_chat.send_message(
        "⚙️ <b>Painel ADM — Ferramentas</b>\nEscolha uma ação:",
        parse_mode="HTML",
        reply_markup=_menu_kb(),
    )

# ======= Router de callbacks =======
async def adm_tools_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data or ""

    # memória por admin: context.user_data['admtools'] = {...}
    ud = context.user_data.setdefault("admtools", {})

    # --------- fechar ----------
    if data == "admtools_close":
        try:
            await q.delete_message()
        except Exception:
            pass
        return

    # --------- voltar ao menu ----------
    if data == "admtools_menu":
        try:
            await q.edit_message_text(
                "⚙️ <b>Painel ADM — Ferramentas</b>\nEscolha uma ação:",
                parse_mode="HTML",
                reply_markup=_menu_kb(),
            )
        except Exception:
            await q.message.reply_text("Menu ADM:", reply_markup=_menu_kb(), parse_mode="HTML")
        ud.clear()
        return

    # --------- reset all (confirmação) ----------
    if data == "admtools_reset_all_confirm":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Sim, zerar TODOS", callback_data="admtools_reset_all_yes")],
            [InlineKeyboardButton("⬅️ Cancelar", callback_data="admtools_menu")],
        ])
        await q.edit_message_text(
            "⚠️ Tem certeza que deseja <b>zerar os pontos de TODOS</b> os jogadores?",
            parse_mode="HTML",
            reply_markup=kb,
        )
        return

    if data == "admtools_reset_all_yes":
        count = 0
        for uid, pdata in player_manager.iter_players():
            try:
                _reset_points_inplace(pdata)
                player_manager.save_player_data(uid, pdata)
                count += 1
            except Exception as e:
                logger.warning("[ADM] Falha ao zerar %s: %s", uid, e)
        await q.edit_message_text(
            f"✅ Pontos zerados para <b>{count}</b> jogadores.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admtools_menu")]]),
        )
        return

    # --------- reset one (pergunta id/nome -> confirmação) ----------
    if data == "admtools_reset_one":
        ud.clear()
        ud["await"] = "reset_one_target"
        await q.edit_message_text(
            "🧹 Envie o <b>ID</b> ou <b>nome do personagem</b> a zerar.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admtools_menu")]]),
        )
        return

    if data.startswith("admtools_reset_one_yes:"):
        # admtools_reset_one_yes:<uid>
        try:
            uid = int(data.split(":", 1)[1])
        except Exception:
            await q.answer("Alvo inválido.", show_alert=True); return
        pdata = player_manager.get_player_data(uid)
        if not pdata:
            await q.answer("Jogador não encontrado.", show_alert=True); return
        _reset_points_inplace(pdata)
        player_manager.save_player_data(uid, pdata)
        await q.edit_message_text(
            f"✅ Pontos zerados para ID {uid} (<b>{pdata.get('character_name','?')}</b>).",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admtools_menu")]]),
        )
        context.user_data.get("admtools", {}).clear()
        return

    # --------- definir nível (pergunta id/nome -> pergunta nível -> confirma) ----------
    if data == "admtools_set_level":
        ud.clear()
        ud["await"] = "set_level_target"
        await q.edit_message_text(
            "📈 Envie o <b>ID</b> ou <b>nome do personagem</b> para definir o nível.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admtools_menu")]]),
        )
        return

    if data.startswith("admtools_set_level_yes:"):
        # admtools_set_level_yes:<uid>:<lvl>
        try:
            _, payload = data.split(":", 1)
            uid_s, lvl_s = payload.split(":")
            uid, lvl = int(uid_s), int(lvl_s)
        except Exception:
            await q.answer("Dados inválidos.", show_alert=True); return

        pdata = player_manager.get_player_data(uid)
        if not pdata:
            await q.answer("Jogador não encontrado.", show_alert=True); return

        lvl = max(1, lvl)
        pdata["level"] = lvl
        # mantém XP atual dentro do próximo cap
        try:
            from modules import game_data
            need = int(game_data.get_xp_for_next_combat_level(lvl))
            cur = int(pdata.get("xp", 0))
            pdata["xp"] = max(0, min(cur, need))
        except Exception:
            pass

        player_manager.save_player_data(uid, pdata)
        await q.edit_message_text(
            f"✅ Nível do jogador ID {uid} (<b>{pdata.get('character_name','?')}</b>) definido para <b>{lvl}</b>.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admtools_menu")]]),
        )
        context.user_data.get("admtools", {}).clear()
        return

    # --------- mudar classe (pergunta id/nome -> botões de classe -> aplica direto) ----------
    if data == "admtools_set_class":
        ud.clear()
        ud["await"] = "set_class_target"
        await q.edit_message_text(
            "🎭 Envie o <b>ID</b> ou <b>nome do personagem</b> para mudar a classe.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admtools_menu")]]),
        )
        return

    if data.startswith("admtools_pick_class:"):
        # admtools_pick_class:<uid>:<class_key>
        try:
            _, payload = data.split(":", 1)
            uid_s, class_key = payload.split(":")
            uid = int(uid_s)
        except Exception:
            await q.answer("Dados inválidos.", show_alert=True); return

        pdata = player_manager.get_player_data(uid)
        if not pdata:
            await q.answer("Jogador não encontrado.", show_alert=True); return
        if class_key not in CLASSES_DATA:
            await q.answer("Classe inválida.", show_alert=True); return

        pdata["class_key"] = class_key
        pdata["class"] = (CLASSES_DATA.get(class_key) or {}).get("display_name", class_key.title())
        player_manager.save_player_data(uid, pdata)

        await q.edit_message_text(
            f"✅ Classe alterada para <b>{pdata['class']}</b> no jogador ID {uid} ({pdata.get('character_name','?')}).",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admtools_menu")]]),
        )
        context.user_data.get("admtools", {}).clear()
        return

    # --------- mudar profissão (pergunta id/nome -> botões de profissão/nível) ----------
    if data == "admtools_set_prof":
        ud.clear()
        ud["await"] = "set_prof_target"
        await q.edit_message_text(
            "🛠️ Envie o <b>ID</b> ou <b>nome do personagem</b> para mudar a profissão.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admtools_menu")]]),
        )
        return

    if data.startswith("admtools_pick_prof:"):
        # admtools_pick_prof:<uid>:<prof_key>
        try:
            _, payload = data.split(":", 1)
            uid_s, prof_key = payload.split(":")
            uid = int(uid_s)
        except Exception:
            await q.answer("Dados inválidos.", show_alert=True); return

        if prof_key not in PROFESSIONS_DATA:
            await q.answer("Profissão inválida.", show_alert=True); return

        # mostra níveis rápidos + outro
        quick = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Nível 1", callback_data=f"admtools_pick_prof_lvl:{uid}:{prof_key}:1"),
                InlineKeyboardButton("Nível 5", callback_data=f"admtools_pick_prof_lvl:{uid}:{prof_key}:5"),
            ],
            [
                InlineKeyboardButton("Nível 10", callback_data=f"admtools_pick_prof_lvl:{uid}:{prof_key}:10"),
                InlineKeyboardButton("Nível 20", callback_data=f"admtools_pick_prof_lvl:{uid}:{prof_key}:20"),
            ],
            [InlineKeyboardButton("Outro nível…", callback_data=f"admtools_pick_prof_lvl_custom:{uid}:{prof_key}")],
            [InlineKeyboardButton("⬅️ Cancelar", callback_data="admtools_menu")],
        ])
        disp = (PROFESSIONS_DATA.get(prof_key) or {}).get("display_name", prof_key.title())
        await q.edit_message_text(
            f"🛠️ Profissão escolhida: <b>{disp}</b>.\nSelecione o nível:",
            parse_mode="HTML",
            reply_markup=quick,
        )
        return

    if data.startswith("admtools_pick_prof_lvl:"):
        # admtools_pick_prof_lvl:<uid>:<prof_key>:<lvl>
        try:
            _, payload = data.split(":", 1)
            uid_s, prof_key, lvl_s = payload.split(":")
            uid, lvl = int(uid_s), int(lvl_s)
        except Exception:
            await q.answer("Dados inválidos.", show_alert=True); return

        pdata = player_manager.get_player_data(uid)
        if not pdata:
            await q.answer("Jogador não encontrado.", show_alert=True); return
        if prof_key not in PROFESSIONS_DATA:
            await q.answer("Profissão inválida.", show_alert=True); return

        lvl = max(1, lvl)
        pdata["profession"] = {"type": prof_key, "level": lvl, "xp": 0}
        player_manager.save_player_data(uid, pdata)
        disp = (PROFESSIONS_DATA.get(prof_key) or {}).get("display_name", prof_key.title())
        await q.edit_message_text(
            f"✅ Profissão definida: <b>{disp}</b> (nível {lvl}) no jogador ID {uid} ({pdata.get('character_name','?')}).",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admtools_menu")]]),
        )
        context.user_data.get("admtools", {}).clear()
        return

    if data.startswith("admtools_pick_prof_lvl_custom:"):
        # admtools_pick_prof_lvl_custom:<uid>:<prof_key>
        try:
            _, payload = data.split(":", 1)
            uid_s, prof_key = payload.split(":")
            uid = int(uid_s)
        except Exception:
            await q.answer("Dados inválidos.", show_alert=True); return
        ud.clear()
        ud["await"] = "set_prof_level_custom"
        ud["prof_uid"] = uid
        ud["prof_key"] = prof_key
        await q.edit_message_text(
            "Informe o <b>nível</b> desejado (número inteiro ≥ 1):",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Cancelar", callback_data="admtools_menu")]]),
        )
        return

# ======= Router de mensagens livres (texto) =======
async def adm_tools_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Interpreta o texto do ADMIN quando algum passo está 'aguardando'.
    """
    if "admtools" not in context.user_data:
        return  # nada aguardando
    ud = context.user_data["admtools"] or {}
    mode = ud.get("await")
    if not mode:
        return

    text = (update.message.text or "").strip()

    # --- ZERAR (um) — receber ID|nome -> confirmar
    if mode == "reset_one_target":
        uid, pdata, err = _resolve_user(text)
        if err:
            await update.message.reply_text(f"❌ {err}")
            return
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"✅ Sim, zerar {pdata.get('character_name','?')}", callback_data=f"admtools_reset_one_yes:{uid}")],
            [InlineKeyboardButton("⬅️ Cancelar", callback_data="admtools_menu")],
        ])
        await update.message.reply_text(
            f"Confirmar zerar pontos do jogador ID {uid} (<b>{pdata.get('character_name','?')}</b>)?",
            parse_mode="HTML",
            reply_markup=kb,
        )
        ud.clear()
        return

    # --- SET LEVEL — primeiro alvo -> depois pedir nível
    if mode == "set_level_target":
        uid, pdata, err = _resolve_user(text)
        if err:
            await update.message.reply_text(f"❌ {err}")
            return
        ud["await"] = "set_level_value"
        ud["lvl_uid"] = uid
        ud["lvl_name"] = pdata.get("character_name", "?")
        await update.message.reply_text(
            f"Jogador: <b>{ud['lvl_name']}</b> (ID {uid})\n"
            "Informe o <b>novo nível</b> (inteiro ≥ 1):",
            parse_mode="HTML",
        )
        return

    if mode == "set_level_value":
        try:
            lvl = int(text)
            if lvl < 1:
                raise ValueError
        except Exception:
            await update.message.reply_text("Informe um número inteiro válido (≥ 1).")
            return
        uid = int(ud.get("lvl_uid"))
        name = ud.get("lvl_name", "?")
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"✅ 𝐂𝐨𝐧𝐟𝐢𝐫𝐦𝐚𝐫 𝐧í𝐯𝐞𝐥 {lvl}", callback_data=f"admtools_set_level_yes:{uid}:{lvl}")],
            [InlineKeyboardButton("⬅️ 𝐂𝐚𝐧𝐜𝐞𝐥𝐚𝐫", callback_data="admtools_menu")],
        ])
        await update.message.reply_text(
            f"Confirmar definir nível de <b>{name}</b> (ID {uid}) para <b>{lvl}</b>?",
            parse_mode="HTML",
            reply_markup=kb,
        )
        ud.clear()
        return

    # --- SET CLASS — alvo -> mostrar botões de classes
    if mode == "set_class_target":
        uid, pdata, err = _resolve_user(text)
        if err:
            await update.message.reply_text(f"❌ {err}")
            return
        # monta botões de classes (2 por linha)
        rows = []
        row = []
        for k, cfg in (CLASSES_DATA or {}).items():
            disp = cfg.get("display_name", k.title())
            row.append(InlineKeyboardButton(disp, callback_data=f"admtools_pick_class:{uid}:{k}"))
            if len(row) == 2:
                rows.append(row); row = []
        if row:
            rows.append(row)
        rows.append([InlineKeyboardButton("⬅️ Cancelar", callback_data="admtools_menu")])
        await update.message.reply_text(
            f"Jogador: <b>{pdata.get('character_name','?')}</b> (ID {uid})\nSelecione a nova classe:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(rows),
        )
        ud.clear()
        return

    # --- SET PROF — alvo -> mostrar botões de profissões
    if mode == "set_prof_target":
        uid, pdata, err = _resolve_user(text)
        if err:
            await update.message.reply_text(f"❌ {err}")
            return
        rows = []
        row = []
        for k, cfg in (PROFESSIONS_DATA or {}).items():
            disp = (cfg or {}).get("display_name", k.title())
            row.append(InlineKeyboardButton(disp, callback_data=f"admtools_pick_prof:{uid}:{k}"))
            if len(row) == 2:
                rows.append(row); row = []
        if row:
            rows.append(row)
        rows.append([InlineKeyboardButton("⬅️ Cancelar", callback_data="admtools_menu")])
        await update.message.reply_text(
            f"Jogador: <b>{pdata.get('character_name','?')}</b> (ID {uid})\nSelecione a profissão:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(rows),
        )
        ud.clear()
        return

    # --- SET PROF nivel custom
    if mode == "set_prof_level_custom":
        try:
            lvl = int(text)
            if lvl < 1:
                raise ValueError
        except Exception:
            await update.message.reply_text("Informe um número inteiro válido (≥ 1).")
            return
        uid = int(ud.get("prof_uid"))
        pkey = ud.get("prof_key")
        pdata = player_manager.get_player_data(uid)
        if not pdata or pkey not in PROFESSIONS_DATA:
            await update.message.reply_text("Alvo inválido ou profissão inválida.")
            context.user_data["admtools"].clear()
            return
        lvl = max(1, lvl)
        pdata["profession"] = {"type": pkey, "level": lvl, "xp": 0}
        player_manager.save_player_data(uid, pdata)
        disp = (PROFESSIONS_DATA.get(pkey) or {}).get("display_name", pkey.title())
        await update.message.reply_text(
            f"✅ Profissão definida: <b>{disp}</b> (nível {lvl}) no jogador ID {uid} ({pdata.get('character_name','?')}).",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="admtools_menu")]]),
        )
        context.user_data["admtools"].clear()
        return
