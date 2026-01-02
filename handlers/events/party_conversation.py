# handlers/events/party_conversation.py
# (VERSÃO BLINDADA: Auth Híbrida + Remoção de Leitura de Arquivos + Suporte ObjectId)

import logging
import unicodedata
from typing import Optional, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import ContextTypes, ConversationHandler

# --- AUTH SECURITY ---
from modules.auth_utils import get_current_player_id

# --- Módulos do Jogo ---
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

async def _resolve_target_player(text: str) -> Optional[Tuple[str, dict]]:
    """
    Busca um jogador pelo input de texto.
    Ordem: ID Exato -> @Username -> Nome Exato -> Nome Normalizado
    """
    t = (text or "").strip()
    if not t:
        return None

    # 1) Tenta buscar diretamente por ID (Int ou ObjectId String)
    # O player_manager.get_player_data já sabe lidar com ambos
    try:
        # Se for dígito puro, pode ser ID legado, se for string longa, ObjectId
        possible_id = int(t) if t.isdigit() else t
        pd = await player_manager.get_player_data(possible_id)
        if pd:
            logger.info(f"[INVITE] Resolveu por ID Direto: {possible_id}")
            # Retorna o ID real do documento para consistência
            real_id = str(pd.get("_id") or possible_id)
            return real_id, pd
    except Exception:
        pass

    # 2) @username
    if t.startswith("@"):
        finder = getattr(player_manager, "find_by_username", None)
        if callable(finder):
            # Nota: find_by_username deve ser async na nova arquitetura
            # Se não for, usamos await asyncio.to_thread ou chamada direta se for síncrona
            # Assumindo player_manager.find_by_username atualizado para async ou sync compatível
            try:
                # Tenta await
                pd = await finder(t[1:])
            except TypeError:
                # Fallback se for sync
                pd = finder(t[1:])
                
            if pd:
                uid = str(pd.get("_id") or pd.get("user_id"))
                if uid:
                    logger.info(f"[INVITE] Resolveu por @username: {t} -> {uid}")
                    return uid, pd

    # 3) Nome exato ou Normalizado
    # Usamos o buscador inteligente do player_manager (que consulta o Mongo)
    try:
        # find_player_by_name deve retornar (user_id, user_data)
        finder_name = getattr(player_manager, "find_player_by_name", None)
        if callable(finder_name):
            try:
                res = await finder_name(t)
            except TypeError:
                res = finder_name(t)
                
            if res:
                logger.info(f"[INVITE] Resolveu por nome: {t}")
                return str(res[0]), res[1]
    except Exception:
        pass

    logger.info(f"[INVITE] NÃO encontrou jogador para: {t!r}")
    return None

def _get_target_chat_id(target_data: dict) -> Optional[int]:
    """Recupera o Chat ID do Telegram para enviar a notificação."""
    # 1. Tenta last_chat_id (mais recente)
    lc = target_data.get("last_chat_id")
    if lc: return int(lc)
    
    # 2. Tenta telegram_id_owner (ID fixo do usuário)
    to = target_data.get("telegram_id_owner")
    if to: return int(to)
    
    # 3. Fallback legado: Se o ID do documento for int, assume que é o ID do telegram
    doc_id = target_data.get("_id") or target_data.get("user_id")
    if isinstance(doc_id, int):
        return doc_id
    if isinstance(doc_id, str) and doc_id.isdigit():
        return int(doc_id)
        
    return None

def _explain_send_error(e: Exception) -> str:
    s = str(e).lower()
    if "forbidden" in s and ("blocked" in s or "bot was blocked" in s):
        return "O jogador bloqueou o bot."
    if "forbidden" in s and "user is deactivated" in s:
        return "A conta do jogador foi desativada."
    if "chat not found" in s or "peer_id_invalid" in s:
        return "O Telegram não encontrou esse chat (o jogador precisa mandar /start no bot)."
    if "not enough rights" in s:
        return "O bot não tem permissão para enviar mensagem."
    return "Falha ao enviar."

# ================== Fluxo de convite ==================

async def ask_for_invitee_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    # 🔒 SEGURANÇA: Identifica quem está clicando
    user_id = get_current_player_id(update, context)
    if not user_id:
        await query.answer("Sessão inválida. Use /start.", show_alert=True)
        return ConversationHandler.END

    party_id = (query.data or "").replace("party_invite_", "")
    context.user_data["party_id_for_invite"] = party_id

    # Verifica liderança
    p = await party_manager.get_party_info(party_id) # Usar get_party_info preferencialmente se existir e for async
    if not p:
         # Fallback para get_party_data síncrono se necessário, mas ideal é async
         p = party_manager.get_party_data(party_id)

    if not p:
        await query.answer("Grupo não encontrado.", show_alert=True)
        return ConversationHandler.END
        
    # Comparação segura de Strings
    if str(p.get("leader_id")) != str(user_id):
        await query.answer("Apenas o líder pode convidar.", show_alert=True)
        return ConversationHandler.END

    await query.message.reply_text(
        "Digite o **Nome do Personagem**, **@username** ou **ID** do jogador para convidar.\n"
        "Use /cancel para cancelar."
    )
    return AWAITING_INVITEE_NAME


async def send_invite_to_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # 🔒 SEGURANÇA
    leader_id = get_current_player_id(update, context)
    if not leader_id:
        await update.message.reply_text("Erro de autenticação.")
        context.user_data.clear()
        return ConversationHandler.END
    
    leader_id_str = str(leader_id)

    party_id = context.user_data.get("party_id_for_invite")
    if not party_id:
        await update.message.reply_text("Sessão expirada.")
        context.user_data.clear()
        return ConversationHandler.END

    # Cancelamento
    text_in = _extract_text_with_custom_emoji(update.message)
    if text_in.lower() == "/cancel":
        await update.message.reply_text("Convite cancelado.")
        context.user_data.clear()
        return ConversationHandler.END

    # Dados do Grupo
    p = party_manager.get_party_data(party_id)
    if not p:
        await update.message.reply_text("Grupo não encontrado.")
        context.user_data.clear()
        return ConversationHandler.END

    if str(p.get("leader_id")) != leader_id_str:
        await update.message.reply_text("Apenas o líder do grupo pode convidar.")
        context.user_data.clear()
        return ConversationHandler.END

    dgn = dungeon_definitions.DUNGEONS.get(p.get("dungeon_id"), {})
    max_players = int(dgn.get("max_players", max(1, len(p.get("members", [])))))
    if len(p.get("members", [])) >= max_players:
        await update.message.reply_text("O grupo já está cheio!")
        context.user_data.clear()
        return ConversationHandler.END

    # Busca o Alvo
    target_res = await _resolve_target_player(text_in)
    if not target_res:
        await update.message.reply_text(
            "❌ Jogador não encontrado.\n"
            "Verifique o nome exato ou peça o ID do jogador (/stats)."
        )
        # Não encerra conversa, permite tentar de novo
        return AWAITING_INVITEE_NAME 

    target_id_str, target_data = target_res
    
    # Auto-invite check
    if target_id_str == leader_id_str:
        await update.message.reply_text("Você já está no grupo.")
        return AWAITING_INVITEE_NAME

    # Verifica se já tem grupo
    # party_manager.get_party_of deve suportar string ID
    already_in_party = False
    try:
        if await party_manager.get_party_of(target_id_str):
            already_in_party = True
    except:
        # Fallback sync
        if party_manager.get_party_of(target_id_str):
            already_in_party = True
            
    if already_in_party:
        await update.message.reply_text(f"⚠️ {target_data.get('character_name')} já está em um grupo.")
        context.user_data.clear()
        return ConversationHandler.END

    # Envia o Convite
    # Precisamos do Chat ID do alvo, não do ObjectId do jogo
    target_chat_id = _get_target_chat_id(target_data)
    
    if not target_chat_id:
        await update.message.reply_text("❌ Erro: Não foi possível contatar este jogador (Chat ID desconhecido).")
        context.user_data.clear()
        return ConversationHandler.END

    leader_data = await player_manager.get_player_data(leader_id)
    leader_name = leader_data.get("character_name", "Líder") if leader_data else "Um jogador"
    dname = dgn.get("display_name", "Masmorra")
    
    text = f"🏰 <b>CONVITE DE GRUPO</b>\n\n<b>{leader_name}</b> convidou você para: <b>{dname}</b>."
    
    keyboard = [[
        InlineKeyboardButton("✅ Aceitar", callback_data=f"party:accept:{party_id}"),
        InlineKeyboardButton("❌ Recusar", callback_data=f"party:decline:{party_id}"),
    ]]

    try:
        await context.bot.send_message(
            chat_id=target_chat_id, 
            text=text, 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        shown_name = target_data.get("character_name", "Jogador")
        await update.message.reply_text(f"✅ Convite enviado para <b>{shown_name}</b>!", parse_mode="HTML")
        logger.info(f"[INVITE] OK: {leader_id_str} -> {target_id_str}")
    except Exception as e:
        reason = _explain_send_error(e)
        logger.error(f"[INVITE] Falha envio {target_id_str}: {e}")
        await update.message.reply_text(
            f"❌ Não foi possível enviar o convite.\nMotivo: {reason}"
        )

    context.user_data.clear()
    return ConversationHandler.END

async def cancel_invite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Convite cancelado.")
    context.user_data.clear()
    return ConversationHandler.END