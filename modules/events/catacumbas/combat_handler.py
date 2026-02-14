# modules/events/catacumbas/combat_handler.py
# (VERSÃO FINAL UNIFICADA: 6 Jogadores + Engine de Efeitos + Escalonamento)

import random
import logging
from typing import Union
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager
from modules.combat import criticals, combat_engine
from handlers.profile_handler import _get_class_media
from modules.auth_utils import get_current_player_id

# Integração com a Engine de Efeitos e Visual
from modules.effects import engine as effects_engine
from modules.effects.models import CombatContext, EVENT_ON_BEFORE_DAMAGE
from . import config, utils

from . import config, raid_manager, entry_handler

from ui.ui_renderer import render_media_or_text  # Importa seu renderizador limpo
from ui import ui_renderer

logger = logging.getLogger(__name__)

# ==============================================================================
# 🎨 UTILITÁRIOS DE MÍDIA
# ==============================================================================

def _get_enemy_media(session: dict) -> str:
    """Seleciona a mídia correta baseada no tipo de inimigo e HP."""
    target = session.get("boss")
    if not target: return config.MEDIA_KEYS.get("lobby_screen")

    if target.get("is_boss"):
        percent = (target["current_hp"] / target["max_hp"])
        if percent > 0.5:
            return config.MEDIA_KEYS.get(target.get("image_normal", "boss_phase_1"), config.MEDIA_KEYS["lobby_screen"])
        return config.MEDIA_KEYS.get(target.get("image_enraged", "boss_phase_2"), config.MEDIA_KEYS["lobby_screen"])
    else:
        return config.MEDIA_KEYS.get(target.get("image"), config.MEDIA_KEYS["lobby_screen"])

# ==============================================================================
# 🖥️ INTERFACE PRINCIPAL (REFRESH)
# ==============================================================================

async def refresh_battle_interface(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE, 
    session: dict, 
    user_id: Union[int, str], 
    turn_state: str = "player_turn"
):
    """
    Renderiza a tela de combate detalhada para o grupo, mantendo o chat limpo.
    Usa o ui_renderer blindado para evitar crash por imagem.
    """
    user_id_str = str(user_id)
    current_pdata = await player_manager.get_player_data(user_id_str)
    
    if not current_pdata:
        return # Evita erro se o jogador não existir

    # Define o escopo para o ui_renderer (garante que ele limpe apenas msgs desta raid)
    UI_SCOPE = f"dungeon_raid_{session.get('raid_id')}"

    # ==========================================================================
    # 1. CASO: JOGADOR DERROTADO (OBSERVADOR)
    # ==========================================================================
    # 1. CASO: JOGADOR DERROTADO (OBSERVADOR)
    if current_pdata.get("current_hp", 0) <= 0:
        defeat_text = "💀 **Foste derrotado!**\nAguarda o fim do combate ou abandone a masmorra."
        
        kb = [
            [InlineKeyboardButton("🔄 Atualizar Visão", callback_data="cat_combat_refresh")],
            [InlineKeyboardButton("🚪 Abandonar Catacumba", callback_data="cat_leave_active")]
        ]
        
        # 1. Força apagar a mensagem anterior do Telegram para não dar erro de edição
        if update.callback_query and update.callback_query.message:
            try:
                await update.callback_query.message.delete()
            except Exception as e:
                logger.error(f"Erro ao apagar mensagem velha: {e}")

        # 2. Envia uma mensagem limpa, apenas de texto (Burla o erro do media)
        try:
            sent_msg = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=defeat_text,
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode="Markdown"
            )
            
            # 3. Informa ao bot que ESTA é a nova mensagem para ele gerenciar
            store = context.user_data.get("_ui_last_messages", {})
            store[UI_SCOPE] = sent_msg.message_id
            context.user_data["_ui_last_messages"] = store

        except Exception as e:
             logger.error(f"Erro Crítico ao enviar tela de derrota: {e}")
             
        return # Impede de rodar o código de interface de combate vivo
    
    # ==========================================================================
    # 2. CASO: ANDAR LIMPO (VITÓRIA)
    # ==========================================================================
    if session.get("floor_cleared", False):
        floor = session["current_floor"]
        txt = f"🚪 **ANDAR {floor} LIMPO!**\nOs inimigos foram derrotados.\nPreparem-se para descer..."
        
        kb = [[InlineKeyboardButton("⬇️ DESCER ESCADAS", callback_data="cat_act_next_floor")]]
        lobby_media = config.MEDIA_KEYS.get("lobby_screen", "cat_lobby_default")

        await ui_renderer.render_media_or_text(
            update=update,
            context=context,
            text=txt,
            media_key=lobby_media, # ✅ Correção
            reply_markup=InlineKeyboardMarkup(kb),
            scope=UI_SCOPE,
            allow_edit=True
        )
        return

    # ==========================================================================
    # 3. COMBATE ATIVO: Formatar Dados
    # ==========================================================================
    
    # Coleta dados atualizados de todos os jogadores da raid
    all_players_data = {}
    for pid in session.get("players", {}):
        p_data = await player_manager.get_player_data(str(pid))
        if p_data:
            all_players_data[str(pid)] = p_data

    # Formata o texto principal (HP do Boss, Turnos, Lista de Players)
    # Assumindo que utils.format_catacomb_interface existe e retorna string
    text = await utils.format_catacomb_interface(session, user_id_str, all_players_data)

    # 4. Configuração dos botões de Ação
    kb = [
        [InlineKeyboardButton("⚔️ ATACAR", callback_data="cat_act_attack"),
         InlineKeyboardButton("✨ SKILLS", callback_data="combat_skill_menu")],
        [InlineKeyboardButton("🧪 Poção", callback_data="cat_act_heal_small"),
         InlineKeyboardButton("🔄 Atualizar", callback_data="cat_combat_refresh")]
    ]

    # 5. Seleção Inteligente de Mídia (Boss ou Jogador)
    # Tenta pegar a imagem do Boss
    boss_data = session.get("boss", {})
    media_key = boss_data.get("image", "boss_default")
    
    # Se o Boss estiver "Enraged" (com raiva), muda a foto
    if boss_data.get("is_enraged") and boss_data.get("image_enraged"):
        media_key = boss_data["image_enraged"]
    
    # Se for turno de "Dano no Jogador", opcionalmente mostra a classe do jogador
    if turn_state == "monster_attacked":
        # Tenta achar a imagem da classe no pdata ou config
        class_name = current_pdata.get("class_name", "guerreiro").lower()
        # Exemplo: procura chave 'classe_guerreiro'
        class_media = f"classe_{class_name}" 
        # Aqui você pode refinar a lógica de busca se quiser
        # media_key = class_media 

    # 6. ENVIO SEGURO (UI RENDERER)
    await ui_renderer.render_media_or_text(
        update=update,
        context=context,
        text=text,
        media_key=media_key, # O renderer vai tentar achar o ID ou usar fallback
        reply_markup=InlineKeyboardMarkup(kb),
        scope=UI_SCOPE,
        allow_edit=True,
        delete_previous_on_send=True # Garante limpeza do chat
    )

# ==============================================================================
# 🎮 LÓGICA DE AÇÕES (COMBATE)
# ==============================================================================

async def combat_action_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(get_current_player_id(update, context))
    user_name = update.effective_user.first_name
    action = query.data
    
    code = raid_manager.PLAYER_LOCATION.get(user_id)
    session = raid_manager.ACTIVE_RAIDS.get(code)
    
    if not session:
        await query.answer("Sessão finalizada.")
        return

    # --- Ação: Próximo Andar ---
    if action == "cat_act_next_floor":
        if not session.get("floor_cleared"):
            await query.answer("Inimigos ainda vivos!", show_alert=True)
            return
        if raid_manager.advance_to_next_floor(session):
            await refresh_battle_interface(update, context, session, user_id)
        else:
            await _handle_victory(update, context, session)
        return

    # --- Validação de Turno ---
    target = session.get("boss")
    if session.get("floor_cleared") or (target and target["current_hp"] <= 0):
        await query.answer("Andar já limpo.")
        await refresh_battle_interface(update, context, session, user_id)
        return

    pdata = await player_manager.get_player_data(user_id)
    stats = await player_manager.get_player_total_stats(pdata)

    # ============================
    # 1. ENGINE DE EFEITOS (TICK)
    # ============================
    # Processa DOTs (bleed/poison) e HOTs no jogador e no mob antes da ação
    p_ticks = effects_engine.tick_turn(pdata, session, apply_to_hp_key="current_hp")
    m_ticks = effects_engine.tick_turn(target, session, apply_to_hp_key="current_hp")
    session["turn_log"].extend(p_ticks + m_ticks)

    if not effects_engine.can_act(pdata):
        await query.answer("💫 Você está atordoado e não pode agir!", show_alert=True)
        return

    # ============================
    # 2. TURNO DO JOGADOR
    # ============================
    if action == "cat_act_attack":
        # Motor de combate centralizado
        res = await combat_engine.processar_acao_combate(pdata, stats, target, None, pdata.get("current_hp", 100))
        
        # Pipeline de dano da Engine (Modificadores + Shields)
        ctx = CombatContext(event=EVENT_ON_BEFORE_DAMAGE, source=pdata, target=target, battle=session, damage=res["total_damage"])
        effects_engine.dispatch(EVENT_ON_BEFORE_DAMAGE, ctx)
        
        target["current_hp"] -= ctx.damage
        session["turn_log"].append(f"⚔️ {user_name} causou {ctx.damage} dano!")
        
    elif action == "cat_act_heal_small":
        heal = int(stats["max_hp"] * 0.15) # Cura 15% em vez de valor fixo
        pdata["current_hp"] = min(stats["max_hp"], pdata.get("current_hp", 0) + heal)
        session["turn_log"].append(f"🧪 {user_name} recuperou {heal} HP.")

    # Verifica Morte do Inimigo
    if target["current_hp"] <= 0:
        target["current_hp"] = 0
        session["floor_cleared"] = True
        session["turn_log"].append(f"💀 **{target['name']} DERROTADO!**")
        await player_manager.save_player_data(user_id, pdata)
        await refresh_battle_interface(update, context, session, user_id)
        return

    # ============================
    # 3. TURNO DO INIMIGO (GRUPO)
    # ============================
    # Seleciona um alvo aleatório do grupo que ainda esteja vivo
    alive_players = []
    for pid in session["players"]:
        p_check = await player_manager.get_player_data(pid)
        if p_check.get("current_hp", 0) > 0:
            alive_players.append(pid)

    if alive_players:
        victim_id = random.choice(alive_players)
        victim_data = await player_manager.get_player_data(victim_id)
        victim_stats = await player_manager.get_player_total_stats(victim_data)
        victim_name = session["players"][victim_id]

        # Inimigo ataca baseado nos status escalonados
        bdmg, is_crit, _ = criticals.roll_damage(target, victim_stats)
        
        # Dispatch de defesa para a vítima (Check de Escudos/Reduções)
        ctx_v = CombatContext(event=EVENT_ON_BEFORE_DAMAGE, source=target, target=victim_data, battle=session, damage=bdmg)
        effects_engine.dispatch(EVENT_ON_BEFORE_DAMAGE, ctx_v)
        
        victim_data["current_hp"] -= ctx_v.damage
        await player_manager.save_player_data(victim_id, victim_data)
        
        msg = f"👹 {target['name']} atacou {victim_name}: {ctx_v.damage}"
        if is_crit: msg += " (CRIT!)"
        session["turn_log"].append(msg)
    
    await player_manager.save_player_data(user_id, pdata)
    await refresh_battle_interface(update, context, session, user_id, turn_state="monster_attacked")

# ==============================================================================
# 🌟 SISTEMA DE AUTO-REVIVER
# ==============================================================================
async def auto_revive_player(user_id: str):
    """Verifica se o jogador está com 0 HP e o ressuscita com 20% de vida."""
    try:
        pdata = await player_manager.get_player_data(user_id)
        if pdata and pdata.get("current_hp", 0) <= 0:
            max_hp = 100
            if "stats" in pdata and "max_hp" in pdata["stats"]:
                max_hp = pdata["stats"]["max_hp"]
            
            # Cura 20% do HP máximo (no mínimo 1 de vida)
            novo_hp = max(1, int(max_hp * 0.20))
            pdata["current_hp"] = novo_hp
            
            await player_manager.save_player_data(user_id, pdata)
            print(f"[DEBUG] Jogador {user_id} ressuscitado com {novo_hp} HP.")
    except Exception as e:
        print(f"[ERRO] Falha ao tentar reviver jogador {user_id}: {e}")
                
async def _handle_victory(update: Update, context: ContextTypes.DEFAULT_TYPE, session: dict):
    if session.get("status") == "finished": return
    session["status"] = "finished"
    
    rewards = config.REWARDS
    scaling = session.get("scaling_factor", 1.0)
    
    for pid in session["players"]:
        pdata = await player_manager.get_player_data(pid)
        
        # Recompensa base escalonada pelo desafio
        gold = int(rewards["gold_fixed"] * scaling)
        xp = int(rewards["xp_fixed"] * scaling)
        
        pdata["gold"] = pdata.get("gold", 0) + gold
        pdata["xp"] = pdata.get("xp", 0) + xp
        
        # Sorteio de Loot
        inv = pdata.setdefault("inventory", {})
        for item in rewards.get("rare_items", []):
            if random.random() < item["chance"]:
                inv[item["id"]] = inv.get(item["id"], 0) + 1
        
        # Recuperação pós-raid
        ts = await player_manager.get_player_total_stats(pdata)
        pdata["current_hp"] = ts["max_hp"]
        
        await player_manager.save_player_data(pid, pdata)
        if pid in raid_manager.PLAYER_LOCATION: del raid_manager.PLAYER_LOCATION[pid]

    if session["raid_id"] in raid_manager.ACTIVE_RAIDS:
        del raid_manager.ACTIVE_RAIDS[session["raid_id"]]

    await entry_handler.send_event_interface(
        update, context, 
        f"{config.TEXTS['victory']}\n\nRecompensas distribuídas para o grupo!", 
        [[InlineKeyboardButton("🏆 SAIR", callback_data="back_to_kingdom")]],
        media_key=config.MEDIA_KEYS["victory"]
    )

async def execute_boss_turn(update: Update, context: ContextTypes.DEFAULT_TYPE, session: dict):
    """Executa a lógica automática do turno do inimigo."""
    target_boss = session.get("boss")
    if not target_boss or target_boss["current_hp"] <= 0:
        await pass_turn(update, context, session)
        return

    # 1. Escolha de Alvo Inteligente (foca no mais fraco que esteja vivo)
    alive_players = []
    for pid, name in session["players"].items():
        p_data = await player_manager.get_player_data(str(pid))
        if p_data.get("current_hp", 0) > 0:
            alive_players.append({"id": str(pid), "hp": p_data["current_hp"], "name": name})

    if not alive_players:
        session["turn_log"].append("💀 Todos os heróis caíram...")
        await refresh_battle_interface(update, context, session, session["leader_id"])
        return

    # Ordena por HP (ataca o que tem menos)
    alive_players.sort(key=lambda x: x["hp"])
    target_player = alive_players[0]
    
    # 2. Cálculo de Dano (Usando seu sistema de criticals)
    victim_data = await player_manager.get_player_data(target_player["id"])
    victim_stats = await player_manager.get_player_total_stats(victim_data)
    
    # Boss ataca o Player
    dmg, is_crit, _ = criticals.roll_damage(target_boss, victim_stats)
    
    # Aplica na Engine de Efeitos (Check de Escudos do Player)
    from modules.effects.models import CombatContext, EVENT_ON_BEFORE_DAMAGE
    from modules.effects import engine as effects_engine
    
    ctx = CombatContext(event=EVENT_ON_BEFORE_DAMAGE, source=target_boss, target=victim_data, battle=session, damage=dmg)
    effects_engine.dispatch(EVENT_ON_BEFORE_DAMAGE, ctx)
    
    victim_data["current_hp"] -= ctx.damage
    await player_manager.save_player_data(target_player["id"], victim_data)

    # 3. Log da Ação
    msg = f"👹 {target_boss['name']} atacou {target_player['name']}: {ctx.damage}"
    if is_crit: msg += " (CRIT! 💥)"
    session["turn_log"].append(msg)

    # 4. Avança o turno após o ataque do boss
    await pass_turn(update, context, session)

async def pass_turn(update: Update, context: ContextTypes.DEFAULT_TYPE, session: dict):
    """Avança o índice do turno e verifica quem é o próximo."""
    order = session.get("turn_order", [])
    if not order: return

    # Incrementa o índice
    session["current_turn_idx"] = (session.get("current_turn_idx", 0) + 1) % len(order)
    
    next_actor_id = str(order[session["current_turn_idx"]])

    # Se o próximo for o BOSS, executa a IA recursivamente
    if next_actor_id == "boss":
        await execute_boss_turn(update, context, session)
    else:
        # Se for um PLAYER, apenas atualiza a tela para todos
        # O marcador ⚔️ agora estará no player da vez
        await refresh_battle_interface(update, context, session, next_actor_id)

async def refresh_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(get_current_player_id(update, context))
    code = raid_manager.PLAYER_LOCATION.get(user_id)
    session = raid_manager.ACTIVE_RAIDS.get(code)
    if session:
        await refresh_battle_interface(update, context, session, user_id)
    elif update.callback_query:
        await update.callback_query.answer("Raid finalizada.")

async def process_player_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa a ação de ataque básico do jogador."""
    query = update.callback_query
    
    # 1. PEGA O ID COM SEGURANÇA E PROTEGE CONTRA 'None'
    from modules.auth_utils import get_current_player_id
    raw_id = get_current_player_id(update, context)
    user_id = str(raw_id)
    
    if not user_id or user_id == 'None':
        await query.answer("Erro de autenticação! Tente abrir o menu novamente.", show_alert=True)
        return
    
    # Verifica se está no lobby de espera
    lobby = raid_manager.get_player_lobby(user_id)
    if lobby:
        await query.answer("A Raid ainda não começou!", show_alert=True)
        return

    # Busca a raid ativa
    active_raid = None
    for code, session in raid_manager.ACTIVE_RAIDS.items():
        if user_id in session.get("players", {}):
            active_raid = session
            break
            
    if not active_raid:
        await query.answer("Você não está em uma Raid ativa.", show_alert=True)
        return
        
    if active_raid.get("floor_cleared"):
        await query.answer("O andar já está limpo! Desça as escadas.", show_alert=True)
        return

    # 1. Carrega dados do Atacante e do Alvo
    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        await query.answer("Erro: Dados do jogador não encontrados.", show_alert=True)
        return

    if pdata.get("current_hp", 0) <= 0:
        await query.answer("Você está morto e não pode atacar!", show_alert=True)
        return

    stats = await player_manager.get_player_total_stats(pdata)
    player_atk = stats.get("attack", 20)
    
    boss = active_raid.get("boss")
    if not boss:
        await query.answer("Erro crítico: Monstro não encontrado na sessão.", show_alert=True)
        return

    boss_def = boss.get("defense", 5)
    
    # 2. Calcula Dano do Jogador
    base_dmg = max(1, player_atk - int(boss_def * 0.5))
    variation = random.uniform(0.9, 1.1)
    final_dmg = int(base_dmg * variation)
    
    boss["current_hp"] = max(0, boss.get("current_hp", 0) - final_dmg)
    
    player_name = pdata.get("name", "Guerreiro")
    if player_name == "Guerreiro" and "username" in pdata:
        player_name = pdata["username"]

    log_msg = f"⚔️ **{player_name}** causou `{final_dmg}` de dano!"
    
    # Verifica se os logs existem na sessão
    if "turn_log" not in active_raid:
        active_raid["turn_log"] = []
    
    # 3. Verifica se o Monstro Morreu
    if boss["current_hp"] <= 0:
        active_raid["turn_log"].append(log_msg)
        active_raid["turn_log"].append(f"💀 **{boss['name']}** foi derrotado!")
        
        if active_raid["current_floor"] >= active_raid["total_floors"]:
            await query.answer("VITÓRIA! O Chefe caiu!", show_alert=True)
            active_raid["turn_log"].append("🏆 **VOCÊS VENCERAM A RAID!**")
        else:
            active_raid["floor_cleared"] = True
            await query.answer("Inimigo derrotado!")
            
        await refresh_battle_interface(update, context, active_raid, user_id)
        return

    # 4. Contra-ataque do Monstro (Apenas se o alvo estiver vivo)
    # BLINDAGEM: O monstro não bate se o jogador já morreu com veneno, etc.
    if pdata.get("current_hp", 0) > 0:
        boss_atk = boss.get("attack", 20)
        player_def = stats.get("defense", 10)
        
        base_boss_dmg = max(1, boss_atk - int(player_def * 0.6))
        boss_dmg = int(base_boss_dmg * random.uniform(0.9, 1.1))
        
        pdata["current_hp"] = max(0, pdata.get("current_hp", 100) - boss_dmg)
        await player_manager.save_player_data(user_id, pdata)
        
        log_msg += f"\n👹 O inimigo revidou com `{boss_dmg}` de dano!"
        
        # BLINDAGEM: Morte do Jogador
        if pdata["current_hp"] == 0:
             log_msg += f"\n💀 **{player_name} foi morto pelo golpe!**"
    
    active_raid["turn_log"].append(log_msg)
    
    if len(active_raid["turn_log"]) > 10:
        active_raid["turn_log"] = active_raid["turn_log"][-10:]

    try:
        await query.answer("Você atacou!")
    except: pass # Evita crash se o Telegram demorar
    
    await refresh_battle_interface(update, context, active_raid, user_id, turn_state="monster_attacked")

async def refresh_combat_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Atualiza a tela de combate para quem clicou (Vivo ou Morto)."""
    query = update.callback_query
    
    from modules.auth_utils import get_current_player_id
    user_id = str(get_current_player_id(update, context))
    
    # Encontra a raid ativa do jogador
    active_raid = None
    for code, session in raid_manager.ACTIVE_RAIDS.items():
        if user_id in session.get("players", {}):
            active_raid = session
            break
            
    if not active_raid:
        await query.answer("Nenhuma Raid ativa encontrada para você.", show_alert=True)
        return
        
    # Avisa o Telegram que o botão foi clicado
    try:
        await query.answer("Visão atualizada!")
    except: pass
    
    # Renderiza a interface novamente com os dados mais recentes do monstro e grupo
    await refresh_battle_interface(update, context, active_raid, user_id, turn_state="refresh")

# ==============================================================================
# 🚪 ABANDONAR A MASMORRA
# ==============================================================================
async def leave_active_raid_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Permite que um jogador abandone a raid ativa, limpe a sessão e ressuscite se necessário."""
    query = update.callback_query
    
    from modules.auth_utils import get_current_player_id
    raw_id = get_current_player_id(update, context)
    
    # Blindagem extra caso o get_current_player_id perca a sessão
    if not raw_id or str(raw_id) == "None":
        # Vai buscar pelo ID do Telegram como fallback
        from modules.database import get_collection
        doc = await get_collection("players").find_one({"telegram_id": update.effective_user.id})
        if doc:
            raw_id = str(doc["_id"])

    user_id = str(raw_id)
    
    # 1. FAZ A LIMPEZA TOTAL DA SESSÃO
    raid_found = False
    
    # Limpa Raids Ativas
    for code, session in list(raid_manager.ACTIVE_RAIDS.items()):
        if user_id in session.get("players", {}):
            del session["players"][user_id]
            raid_found = True
            if len(session["players"]) == 0:
                del raid_manager.ACTIVE_RAIDS[code]
            break
            
    # Limpa Lobbies Fantasmas (por segurança)
    for code, lobby in list(raid_manager.LOBBIES.items()):
        if user_id in lobby.get("players", {}):
            del lobby["players"][user_id]
            raid_found = True
            if len(lobby["players"]) == 0:
                del raid_manager.LOBBIES[code]
            break

    # Limpa a Localização
    if user_id in raid_manager.PLAYER_LOCATION:
        del raid_manager.PLAYER_LOCATION[user_id]
        raid_found = True

    # Limpa o Cache de Interface do Bot
    if "_ui_last_messages" in context.user_data:
        context.user_data["_ui_last_messages"].clear()

    # ==========================================================
    # 2. 🔥 CHAMA A RESSURREIÇÃO NO BANCO DE DADOS
    # ==========================================================
    await auto_revive_player(user_id)
    # ==========================================================

    if not raid_found:
        await query.answer("Os teus dados de sessão já estavam limpos.", show_alert=True)
    else:
        await query.answer("Abandonaste as Catacumbas e voltaste à cidade!")
    
    # 3. Volta ao menu principal
    try:
        from .entry_handler import menu_catacumba_main
        await menu_catacumba_main(update, context)
    except Exception as e:
        print(f"Erro ao voltar ao menu principal: {e}")
                                    
handlers = [
    CallbackQueryHandler(combat_action_cb, pattern="^cat_act_"),
    CallbackQueryHandler(refresh_cb, pattern="^cat_combat_refresh")

]