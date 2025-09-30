# handlers/events/party_conversation.py
import logging
import os
import json
import unicodedata
from typing import Optional, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import ContextTypes, ConversationHandler

from modules import player_manager, party_manager, dungeon_definitions

logger = logging.getLogger(__name__)

# Estado da conversa
AWAITING_INVITEE_NAME = 0

# ---- Normalização para nomes com emoji ----
VS_SET = {0xFE0E, 0xFE0F}  # Variation Selectors (texto/emoji)
ZWJ = "\u200D"


def _is_skin_tone(cp: int) -> bool:
    return 0x1F3FB <= cp <= 0x1F3FF  # tons de pele


def _strip_vs_and_tones(s: str) -> str:
    """Remove variation selectors (FE0E/FE0F) e tons de pele; mantém ZWJ."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    out = []
    for ch in s:
        cp = ord(ch)
        if cp in VS_SET or _is_skin_tone(cp):
            continue
        out.append(ch)
    return "".join(out).strip()


def _normalize_display_name(s: str) -> str:
    return _strip_vs_and_tones(s)


def _normalize_variants(s: str):
    base = _normalize_display_name(s)
    yield base
    if ZWJ in base:
        yield base.replace(ZWJ, "")


# Caminho para fallback linear
PLAYERS_DIR = "players"


def _read_player_file(fp: str) -> Optional[dict]:
    try:
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"[INVITE] Falha lendo {fp}: {e}")
        return None


def _search_by_character_name_norm_linear(query_text: str) -> Optional[Tuple[str, dict]]:
    if not query_text:
        return None

    q_vars = list(_normalize_variants(query_text))

    try:
        for fname in os.listdir(PLAYERS_DIR):
            if not fname.endswith(".json"):
                continue
            fp = os.path.join(PLAYERS_DIR, fname)
            pdata = _read_player_file(fp)
            if not pdata:
                continue

            name = pdata.get("character_name", "")
            n_vars = list(_normalize_variants(name))
            ok = any(qv == nv for qv in q_vars for nv in n_vars)
            if ok:
                user_id = pdata.get("user_id") or os.path.splitext(fname)[0]
                logger.info(f"[INVITE] Match por varredura: {query_text!r} -> {name!r} (id={user_id})")
                return str(user_id), pdata
    except FileNotFoundError:
        logger.warning(f"[INVITE] Pasta '{PLAYERS_DIR}' não encontrada (fallback linear).")
    except Exception as e:
        logger.warning(f"[INVITE] Falha no fallback linear: {e}")

    return None


def _extract_text_with_custom_emoji(msg: Message) -> str:
    t = (msg.text or "").strip()
    if t:
        return t
    try:
        if msg.entities:
            parts = []
            for ent in msg.entities:
                try:
                    parts.append(ent.get_text(msg.text or ""))
                except Exception:
                    pass
            return "".join(parts).strip()
    except Exception:
        pass
    return ""


def _chat_id_of(target_id_str: str):
    if target_id_str and target_id_str.isdigit():
        try:
            return int(target_id_str)
        except Exception:
            pass
    return target_id_str


def _resolve_target_player(text: str) -> Optional[Tuple[str, dict]]:
    t = (text or "").strip()
    if not t:
        return None

    # 1) ID numérico
    if t.isdigit():
        uid = int(t)
        pd = player_manager.get_player_data(uid)
        if pd:
            logger.info(f"[INVITE] Resolveu por ID: {uid}")
            return str(uid), pd

    # 2) @username
    if t.startswith("@"):
        finder = getattr(player_manager, "find_by_username", None)
        if callable(finder):
            pd = finder(t[1:])
            if pd:
                uid = pd.get("user_id")
                if uid is not None:
                    logger.info(f"[INVITE] Resolveu por @username: {t} -> {uid}")
                    return str(uid), pd

    # 3) Nome exato (case/acentos já normalizados pelo player_manager)
    try:
        res = player_manager.find_player_by_name(t)
        if res:
            logger.info(f"[INVITE] Resolveu por nome exato: {t}")
            return res
    except Exception:
        pass

    # 4) Nome normalizado (emoji-safe)
    finder_norm = getattr(player_manager, "find_player_by_name_norm", None)
    if callable(finder_norm):
        res = finder_norm(_normalize_display_name(t))
        if res:
            logger.info(f"[INVITE] Resolveu por find_player_by_name_norm: {t}")
            return res

    # 5) Fallback linear (varredura de arquivos)
    res = _search_by_character_name_norm_linear(t)
    if res:
        return res

    logger.info(f"[INVITE] NÃO encontrou jogador para: {t!r}")
    return None


def _explain_send_error(e: Exception) -> str:
    s = str(e).lower()
    if "forbidden" in s and ("blocked" in s or "bot was blocked" in s):
        return "O jogador bloqueou o bot."
    if "forbidden" in s and "user is deactivated" in s:
        return "A conta do jogador foi desativada."
    if "chat not found" in s or "peer_id_invalid" in s:
        return "O Telegram não encontrou esse chat/ID (o jogador precisa mandar /start no bot antes)."
    if "not enough rights" in s or "need administrator" in s:
        return "O bot não tem permissão para enviar mensagem nesse chat."
    return "Falha ao enviar (verifique se o jogador já deu /start no bot)."


# ================== Fluxo de convite ==================

async def ask_for_invitee_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    party_id = (query.data or "").replace("party_invite_", "")
    context.user_data["party_id_for_invite"] = party_id

    # segurança: só líder
    p = party_manager.get_party_data(party_id)
    if not p or p.get("leader_id") != str(query.from_user.id):
        await query.answer("Apenas o líder pode convidar.", show_alert=True)
        return ConversationHandler.END

    await query.message.reply_text(
        "Digite o nome do personagem (aceita emoji), @username ou ID numérico.\n"
        "Dica: primeiro teste com o **ID numérico** do jogador.\n"
        "Use /cancel para cancelar."
    )
    return AWAITING_INVITEE_NAME


async def send_invite_to_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    leader_id_str = str(update.effective_user.id)
    party_id = context.user_data.get("party_id_for_invite")
    if not party_id:
        await update.message.reply_text("Sessão de convite expirada. Abra novamente o convite.")
        context.user_data.clear()
        return ConversationHandler.END

    # cancel
    text_in = _extract_text_with_custom_emoji(update.message)
    if text_in.lower() == "/cancel":
        await update.message.reply_text("Convite cancelado.")
        context.user_data.clear()
        return ConversationHandler.END

    p = party_manager.get_party_data(party_id)
    if not p:
        await update.message.reply_text("Grupo não encontrado.")
        context.user_data.clear()
        return ConversationHandler.END

    if p.get("leader_id") != leader_id_str:
        await update.message.reply_text("Apenas o líder do grupo pode convidar.")
        context.user_data.clear()
        return ConversationHandler.END

    dgn = dungeon_definitions.DUNGEONS.get(p.get("dungeon_id"), {})
    max_players = int(dgn.get("max_players", max(1, len(p.get("members", [])))))
    if len(p.get("members", [])) >= max_players:
        await update.message.reply_text("O grupo já está cheio!")
        context.user_data.clear()
        return ConversationHandler.END

    target_res = _resolve_target_player(text_in)
    if not target_res:
        await update.message.reply_text(
            "Jogador não encontrado.\n"
            "Tente **ID numérico** ou peça para o jogador enviar /start no bot e tente de novo."
        )
        context.user_data.clear()
        return ConversationHandler.END

    target_id_str, target_data = target_res
    if target_id_str == leader_id_str:
        await update.message.reply_text("Você não pode convidar a si mesmo.")
        context.user_data.clear()
        return ConversationHandler.END

    if party_manager.get_party_of(int(target_id_str)) if hasattr(party_manager, "get_party_of") else False:
        await update.message.reply_text("Esse jogador já está em outro grupo.")
        context.user_data.clear()
        return ConversationHandler.END

    # Mensagem simples (sem HTML) e com botões — menor chance de erro
    leader_name = (player_manager.get_player_data(int(leader_id_str)) or {}).get("character_name", "Líder")
    dname = dgn.get("display_name", "Masmorra")
    text = f"Convite de {leader_name} para a masmorra {dname}."
    keyboard = [[
        InlineKeyboardButton("✅ Aceitar", callback_data=f"party_accept_{party_id}"),
        InlineKeyboardButton("❌ Recusar", callback_data=f"party_decline_{party_id}"),
    ]]
    chat_id = _chat_id_of(target_id_str)

    try:
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        shown_name = target_data.get("character_name", target_id_str)
        await update.message.reply_text(f"✅ Convite enviado para {shown_name} (id={target_id_str}).")
        logger.info(f"[INVITE] OK -> {shown_name} (id={target_id_str})")
    except Exception as e:
        reason = _explain_send_error(e)
        logger.error(f"[INVITE] Falha ao enviar para {target_id_str}: {e}")
        await update.message.reply_text(
            "❌ Não foi possível enviar o convite.\n"
            f"Motivo provável: {reason}\n"
            "Dica: peça para o jogador mandar /start no bot e tente de novo, ou convide por ID."
        )

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_invite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Convite cancelado.")
    context.user_data.clear()
    return ConversationHandler.END
