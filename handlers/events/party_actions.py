# handlers/events/party_actions.py
# (VERSÃO BLINDADA: AUTH UNIFICADA + SUPORTE A STRING ID)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

# --- IMPORTAÇÃO DA SEGURANÇA ---
from modules.auth_utils import get_current_player_id 

# --- Módulos do Jogo ---
from modules import player_manager
try:
    # Tenta importar o gerenciador de grupo e definições
    from modules.events import party_manager
    from modules.dungeons import dungeon_definitions
except ImportError:
    party_manager = None
    dungeon_definitions = None

logger = logging.getLogger(__name__)

async def party_actions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Gerencia todas as ações de grupo (Criar, Entrar, Sair, Iniciar, Convites).
    """
    query = update.callback_query
    
    # 🔒 SEGURANÇA: Identificação via Auth Central
    user_id = get_current_player_id(update, context)
    
    if not user_id:
        await query.answer("❌ Sessão inválida ou expirada. Use /start para logar.", show_alert=True)
        return

    # Recupera dados para validação (Nome, Nível, etc)
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await query.answer("❌ Perfil não encontrado.", show_alert=True)
        return

    data = query.data
    # Padrão esperado: party:ACTION:ARG1:ARG2...
    parts = data.split(":")
    if len(parts) < 2:
        return 
        
    action = parts[1]

    # Verifica se o gerenciador de party está carregado
    if not party_manager:
        await query.answer("⚠️ Sistema de grupos indisponível no momento.", show_alert=True)
        return

    try:
        # --- AÇÃO: CRIAR GRUPO ---
        if action == "create":
            # Ex: party:create:dungeon_id
            dungeon_id = parts[2] if len(parts) > 2 else "generic"
            
            result = await party_manager.create_party(user_id, player_data, dungeon_id)
            if result["success"]:
                await query.answer("✅ Grupo criado!", show_alert=False)
                await _refresh_party_menu(query, result["party_id"])
            else:
                await query.answer(f"❌ {result.get('message', 'Erro ao criar grupo.')}", show_alert=True)

        # --- AÇÃO: ENTRAR (JOIN) OU ACEITAR (ACCEPT) ---
        elif action in ("join", "accept"):
            party_id = parts[2]
            
            # Tenta entrar no grupo
            result = await party_manager.join_party(user_id, player_data, party_id)
            
            if result["success"]:
                await query.answer("✅ Você entrou no grupo!", show_alert=False)
                # Se foi aceitar convite, apaga a msg do convite ou atualiza
                if action == "accept":
                    try: await query.delete_message()
                    except: pass
                else:
                    await _refresh_party_menu(query, party_id)
            else:
                msg_erro = result.get('message', 'Não foi possível entrar.')
                if action == "accept":
                    try: await query.edit_message_text(f"❌ {msg_erro}")
                    except: pass
                else:
                    await query.answer(f"❌ {msg_erro}", show_alert=True)

        # --- AÇÃO: RECUSAR CONVITE (DECLINE) ---
        elif action == "decline":
            # party:decline:party_id
            try:
                await query.edit_message_text("❌ Convite recusado.")
            except:
                pass

        # --- AÇÃO: SAIR (LEAVE) ---
        elif action == "leave":
            party_id = parts[2]
            result = await party_manager.leave_party(user_id, party_id)
            
            if result["success"]:
                await query.answer("Você saiu do grupo.", show_alert=False)
                # Tenta fechar o menu para quem saiu
                try: await query.delete_message()
                except: pass
            else:
                await query.answer(f"❌ {result.get('message', 'Erro ao sair.')}", show_alert=True)

        # --- AÇÃO: INICIAR (START - Apenas Líder) ---
        elif action == "start":
            party_id = parts[2]
            # Verifica se é líder
            is_leader = await party_manager.is_party_leader(party_id, user_id)
            
            if not is_leader:
                await query.answer("⚠️ Apenas o líder pode iniciar a aventura!", show_alert=True)
                return

            result = await party_manager.start_party_event(party_id)
            if result["success"]:
                await query.answer("🚀 Aventura iniciada!", show_alert=True)
            else:
                await query.answer(f"❌ {result.get('message', 'Não foi possível iniciar.')}", show_alert=True)

        # --- AÇÃO: ATUALIZAR (REFRESH) ---
        elif action == "refresh":
            party_id = parts[2]
            await query.answer("Atualizado.")
            await _refresh_party_menu(query, party_id)

        # --- AÇÃO: EXPULSAR (KICK - Apenas Líder) ---
        elif action == "kick":
            party_id = parts[2]
            target_id = parts[3] 
            
            # Verifica permissão
            is_leader = await party_manager.is_party_leader(party_id, user_id)
            if not is_leader:
                await query.answer("⚠️ Apenas o líder pode expulsar membros.", show_alert=True)
                return
                
            # Comparação segura de Strings (ObjectIds)
            if str(target_id) == str(user_id):
                await query.answer("Você não pode se expulsar. Use 'Sair'.", show_alert=True)
                return

            result = await party_manager.kick_member(party_id, target_id)
            if result["success"]:
                await query.answer("🥾 Membro removido.", show_alert=True)
                await _refresh_party_menu(query, party_id)
            else:
                await query.answer("Erro ao remover membro.", show_alert=True)

    except Exception as e:
        logger.error(f"Erro no handler de party ({action}): {e}", exc_info=True)
        await query.answer("❌ Erro interno no sistema de grupos.", show_alert=True)

async def _refresh_party_menu(query, party_id):
    """
    Atualiza a mensagem visual do grupo com os membros atuais.
    """
    party_data = await party_manager.get_party_info(party_id)
    if not party_data:
        try: await query.edit_message_text("⚠️ Este grupo foi desfeito ou expirou.")
        except: pass
        return

    # Renderização da Lista de Membros
    members = party_data.get("members", [])
    
    # Determina max slots
    max_slots = 4
    dungeon_id = party_data.get("dungeon_id")
    if dungeon_definitions:
        dgn_def = dungeon_definitions.DUNGEONS.get(dungeon_id, {})
        max_slots = int(dgn_def.get("max_players", 4))
    
    dungeon_name = party_data.get("dungeon_name", "Aventura")
    
    text = (
        f"🏰 <b>GRUPO: {dungeon_name}</b>\n"
        f"👥 Membros: {len(members)}/{max_slots}\n"
        "─────────────────\n"
    )

    kb = []
    # Itera membros para mostrar na lista
    for member in members:
        role_icon = "👑" if member.get("is_leader") else "🛡️"
        name = member.get("name", "Jogador")
        lvl = member.get("level", 1)
        cls = member.get("class_name", "Aventureiro")
        text += f"{role_icon} <b>{name}</b> (Nv.{lvl} {cls})\n"

    text += "─────────────────\n"
    text += "<i>Aguardando início...</i>"

    # Botões de Controle
    kb.append([InlineKeyboardButton("🚀 INICIAR AVENTURA", callback_data=f"party:start:{party_id}")])
    kb.append([InlineKeyboardButton("🔄 Atualizar", callback_data=f"party:refresh:{party_id}"),
               InlineKeyboardButton("🚪 Sair", callback_data=f"party:leave:{party_id}")])

    markup = InlineKeyboardMarkup(kb)

    try:
        await query.edit_message_text(text=text, reply_markup=markup, parse_mode="HTML")
    except Exception:
        pass

# ==============================================================================
# REGISTRO DO HANDLER
# ==============================================================================
party_actions_handler = CallbackQueryHandler(party_actions_callback, pattern=r"^party:.*")