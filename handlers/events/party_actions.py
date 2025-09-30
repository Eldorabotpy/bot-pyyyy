# handlers/events/party_actions.py (FINAL)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from modules import player_manager, party_manager, dungeon_definitions
from .dungeon_actions import show_dungeon_info

logger = logging.getLogger(__name__)


async def _update_lobby_for_all_members(context: ContextTypes.DEFAULT_TYPE, party_id: str):
    """Atualiza a tela de lobby para todos no grupo (edita se possível; se não, envia nova e atualiza mapeamento)."""
    party_data = party_manager.get_party_data(party_id)
    if not party_data:
        return

    dungeon_id = party_data.get("dungeon_id")
    dungeon_info = dungeon_definitions.DUNGEONS.get(dungeon_id)
    if not dungeon_info:
        logger.error(f"[LOBBY] dungeon_id '{dungeon_id}' não existe para party '{party_id}'")
        return

    members = party_data.get("members", {}) or {}
    member_names = list(members.values())
    members_list = "".join([f"👤 {name}\n" for name in member_names])
    spots = max(0, int(dungeon_info.get("max_players", 1)) - len(member_names))
    if spots:
        members_list += "".join(["❓ (Vaga Aberta)\n" for _ in range(spots)])

    text = (
        f"<b>Sala de Espera: {dungeon_info.get('display_name', dungeon_id)}</b>\n\n"
        f"Líder: {party_data.get('leader_name')}\n"
        "--------------------\n"
        f"<b>Grupo ({len(member_names)}/{dungeon_info.get('max_players', 1)}):</b>\n{members_list}"
    )

    is_full = len(member_names) >= int(dungeon_info.get("max_players", 1))
    party_data.setdefault("player_lobby_messages", {})

    for member_id_str in list(members.keys()):
        is_leader = (member_id_str == party_data.get("leader_id"))
        keyboard = []
        if is_leader:
            if not is_full:
                keyboard.append([InlineKeyboardButton("➡️ Convidar", callback_data=f"party_invite_{party_id}")])
            # Botão de entrar chama o handler de dungeon_enter (fica em outro módulo)
            keyboard.append([InlineKeyboardButton("🚪 Entrar na Masmorra", callback_data=f"dungeon_enter_{dungeon_id}")])
            keyboard.append([InlineKeyboardButton("❌ Desfazer Grupo", callback_data=f"party_disband_{party_id}")])
        else:
            keyboard.append([InlineKeyboardButton("🏃 Deixar Grupo", callback_data=f"party_leave_{party_id}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        msg_id = party_data["player_lobby_messages"].get(member_id_str)

        try:
            if msg_id:
                await context.bot.edit_message_text(
                    chat_id=member_id_str, message_id=msg_id,
                    text=text, reply_markup=reply_markup, parse_mode="HTML"
                )
            else:
                sent = await context.bot.send_message(
                    chat_id=member_id_str, text=text, reply_markup=reply_markup, parse_mode="HTML"
                )
                party_data["player_lobby_messages"][member_id_str] = sent.message_id
        except Exception as e:
            # Fallback: manda uma nova e atualiza o mapeamento
            logger.warning(f"[LOBBY] edit falhou p/ {member_id_str}: {e}")
            try:
                sent = await context.bot.send_message(
                    chat_id=member_id_str, text=text, reply_markup=reply_markup, parse_mode="HTML"
                )
                party_data["player_lobby_messages"][member_id_str] = sent.message_id
            except Exception as e2:
                logger.error(f"[LOBBY] send falhou p/ {member_id_str}: {e2}")

    # salva caso tenhamos atualizado player_lobby_messages
    party_manager.save_party_data(party_id, party_data)


async def show_party_lobby(update: Update, context: ContextTypes.DEFAULT_TYPE, params: list):
    """Mostra a tela de 'Sala de Espera' do grupo."""
    if not params:
        return
    party_id = params[0]
    await _update_lobby_for_all_members(context, party_id)


async def party_create_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, params: list):
    """Cria um grupo e entra na sala de espera."""
    query = update.callback_query
    user_id_str = str(query.from_user.id)
    pdata = player_manager.get_player_data(int(user_id_str)) or {}

    if pdata.get("party_id"):
        await query.answer("Você já está em um grupo!", show_alert=True)
        return

    dungeon_id = "_".join(params)  # catacumba_reino etc.
    party_data = party_manager.create_party(user_id_str, pdata.get("character_name", "Líder"))
    party_data["dungeon_id"] = dungeon_id
    party_data["player_lobby_messages"] = {}

    try:
        msg = await query.edit_message_text("Criando grupo...")
        party_data["player_lobby_messages"][user_id_str] = msg.message_id
    except Exception:
        # fallback se não conseguir editar
        sent = await context.bot.send_message(chat_id=user_id_str, text="Criando grupo...")
        party_data["player_lobby_messages"][user_id_str] = sent.message_id

    party_manager.save_party_data(user_id_str, party_data)
    await _update_lobby_for_all_members(context, user_id_str)


async def party_disband_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, params: list):
    """Desfaz um grupo."""
    query = update.callback_query
    user_id_str = str(query.from_user.id)
    if not params:
        await query.answer("Ação inválida.", show_alert=True); return
    party_id = params[0]

    p = party_manager.get_party_data(party_id)
    if not p or user_id_str != p.get("leader_id"):
        await query.answer("Apenas o líder pode desfazer o grupo.", show_alert=True)
        return

    dungeon_id = p.get("dungeon_id")

    # avisa geral
    for member_id_str in list((p.get("members") or {}).keys()):
        try:
            await context.bot.send_message(chat_id=member_id_str, text="O grupo foi desfeito pelo líder.")
        except Exception:
            pass

    party_manager.disband_party(party_id)

    # Volta para a tela de info da dungeon, sem mexer no query.data
    await show_dungeon_info(update, context, dungeon_id.split("_"))


async def party_leave_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, params: list):
    """Permite que um membro saia de um grupo."""
    query = update.callback_query
    user_id_str = str(query.from_user.id)
    pdata = player_manager.get_player_data(int(user_id_str)) or {}
    party_id = pdata.get("party_id")

    if not party_id:
        try:
            await query.edit_message_text("Você não está em um grupo.")
        except Exception:
            await context.bot.send_message(chat_id=user_id_str, text="Você não está em um grupo.")
        return

    p = party_manager.get_party_data(party_id) or {}
    if user_id_str == p.get("leader_id"):
        await query.answer("O líder não pode deixar o grupo, apenas desfazê-lo.", show_alert=True)
        return

    party_manager.remove_member(party_id, int(user_id_str))
    try:
        await query.edit_message_text("Você saiu do grupo.")
    except Exception:
        await context.bot.send_message(chat_id=user_id_str, text="Você saiu do grupo.")

    try:
        await context.bot.send_message(
            chat_id=p.get("leader_id"),
            text=f"🏃 {(pdata.get('character_name') or 'Membro')} saiu do grupo.",
        )
    except Exception:
        pass

    await _update_lobby_for_all_members(context, party_id)


async def invite_response_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, params: list):
    """Aceitar/Recusar convite."""
    query = update.callback_query
    user_id_str = str(query.from_user.id)
    action = (query.data or "").split("_")[1] if query.data else ""   # accept | decline
    if not params:
        await query.answer("Convite inválido.", show_alert=True); return
    party_id = params[0]

    p = party_manager.get_party_data(party_id)
    if not p:
        await query.edit_message_text("Este grupo não existe mais.")
        return

    if action == "decline":
        await query.edit_message_text("Você recusou o convite.")
        try:
            player = player_manager.get_player_data(int(user_id_str)) or {}
            await context.bot.send_message(
                chat_id=p.get("leader_id"),
                text=f"❌ {player.get('character_name','Jogador')} recusou seu convite."
            )
        except Exception:
            pass
        return

    # aceitar
    player_data = player_manager.get_player_data(int(user_id_str)) or {}
    if player_data.get("party_id"):
        await query.edit_message_text("Você já está em um grupo!")
        return

    dgn = dungeon_definitions.DUNGEONS.get(p.get("dungeon_id"), {})
    if len((p.get("members") or {})) >= int(dgn.get("max_players", 1)):
        await query.edit_message_text("O grupo ficou cheio antes que você pudesse entrar!")
        return

    ok = party_manager.add_member(party_id, int(user_id_str), player_data.get("character_name", "Membro"))
    if not ok:
        await query.edit_message_text("Não foi possível entrar no grupo.")
        return

    sent = await query.edit_message_text(
        f"Você entrou no grupo de <b>{p.get('leader_name')}</b>!", parse_mode="HTML"
    )

    # Atualiza o mapeamento de mensagem do lobby
    reloaded = party_manager.get_party_data(party_id) or {}
    reloaded.setdefault("player_lobby_messages", {})[user_id_str] = sent.message_id
    party_manager.save_party_data(party_id, reloaded)

    await _update_lobby_for_all_members(context, party_id)
