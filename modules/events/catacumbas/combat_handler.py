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
from modules.game_data.skills import get_skill_data_with_rarity
from modules.cooldowns import verificar_cooldown
from . import combat_handler

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
    Renderiza a tela de combate detalhada para o grupo.
    Prioriza a Tela de Vitória para não prender os jogadores no Andar 5.
    """
    user_id_str = str(user_id)
    current_pdata = await player_manager.get_player_data(user_id_str)
    
    if not current_pdata:
        return

    UI_SCOPE = f"dungeon_raid_{session.get('raid_id')}"

    # ==========================================================================
    # 1. PRIORIDADE MÁXIMA: RAID FINALIZADA (VITÓRIA FINAL)
    # ==========================================================================
    if session.get("status") == "finished" or turn_state == "victory":
        txt = "🏆 **MASMORRA CONCLUÍDA!** 🏆\n\nTodos os inimigos foram derrotados e os tesouros foram garantidos!\n\n"
        
        # 🔥 Lê APENAS o log de Loot (ignora os ataques)
        loot_log = session.get("loot_log", [])
        if loot_log:
            txt += "📜 **Recompensas do Grupo:**\n"
            for line in loot_log:
                safe_line = line.replace('_', '\\_') # Evita erro de Markdown
                txt += f"• {safe_line}\n"
                
        kb = [[InlineKeyboardButton("🚪 Retornar à Cidade", callback_data="evt_cat_menu")]]
        
        # O ui_renderer vai cuidar de mostrar a imagem ou o fallback de texto
        await ui_renderer.render_media_or_text(
            update=update, context=context, text=txt, media_key="cat_lobby_default",
            reply_markup=InlineKeyboardMarkup(kb), scope=UI_SCOPE, allow_edit=True
        )
        return

    # ==========================================================================
    # 2. CASO: JOGADOR DERROTADO (OBSERVADOR)
    # ==========================================================================
    if current_pdata.get("current_hp", 0) <= 0:
        defeat_text = "💀 **Foste derrotado!**\nAguarda o fim do combate ou abandone a masmorra."
        kb = [
            [InlineKeyboardButton("🔄 Atualizar Visão", callback_data="cat_combat_refresh")],
            [InlineKeyboardButton("🚪 Abandonar Catacumba", callback_data="cat_leave_active")]
        ]
        
        if update.callback_query and update.callback_query.message:
            try: await update.callback_query.message.delete()
            except: pass

        try:
            sent_msg = await context.bot.send_message(
                chat_id=update.effective_chat.id, text=defeat_text,
                reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
            )
            store = context.user_data.get("_ui_last_messages", {})
            store[UI_SCOPE] = sent_msg.message_id
            context.user_data["_ui_last_messages"] = store
        except Exception as e:
            logger.error(f"Erro ao enviar tela de derrota: {e}")
        return
    
    # ==========================================================================
    # 3. CASO: ANDAR LIMPO (PREPARAÇÃO PARA O PRÓXIMO OU PARA O LOOT)
    # ==========================================================================
    if session.get("floor_cleared", False):
        floor = session.get("current_floor", 1)
        total = session.get("total_floors", 5)
        
        # Se estamos no último andar, muda o texto para ficar mais épico!
        if floor >= total:
            txt = f"🚪 **SALA FINAL LIMPA!**\nO Guardião foi aniquilado.\nReivindiquem as vossas recompensas!"
            btn_txt = "🏆 COLETAR LOOT"
        else:
            txt = f"🚪 **ANDAR {floor} LIMPO!**\nOs inimigos foram derrotados.\nPreparem-se para descer..."
            btn_txt = "⬇️ DESCER ESCADAS"
            
        kb = [[InlineKeyboardButton(btn_txt, callback_data="cat_act_next_floor")]]
        lobby_media = config.MEDIA_KEYS.get("lobby_screen", "cat_lobby_default")

        await ui_renderer.render_media_or_text(
            update=update, context=context, text=txt, media_key=lobby_media,
            reply_markup=InlineKeyboardMarkup(kb), scope=UI_SCOPE, allow_edit=True
        )
        return

    # ==========================================================================
    # 4. COMBATE ATIVO: Formatar Dados
    # ==========================================================================
    all_players_data = {}
    for pid in session.get("players", {}):
        p_data = await player_manager.get_player_data(str(pid))
        if p_data: all_players_data[str(pid)] = p_data

    text = await utils.format_catacomb_interface(session, user_id_str, all_players_data)

    kb = [
        [
            InlineKeyboardButton("⚔️ ATACAR", callback_data="cat_act_attack"),
            InlineKeyboardButton("✨ SKILLS", callback_data="cat_act_skills"),
            InlineKeyboardButton("🧪 Poção", callback_data="cat_act_heal_small")
        ],
        [
            InlineKeyboardButton("🔄 Atualizar Visão", callback_data="cat_combat_refresh"),
            InlineKeyboardButton("🎒 Mochila", callback_data="cat_inventory")
        ]
    ]

    boss_data = session.get("boss", {})
    media_key = boss_data.get("image", "boss_default")
    
    if boss_data.get("is_enraged") and boss_data.get("image_enraged"):
        media_key = boss_data["image_enraged"]

    await ui_renderer.render_media_or_text(
        update=update, context=context, text=text, media_key=media_key,
        reply_markup=InlineKeyboardMarkup(kb), scope=UI_SCOPE, allow_edit=True,
        delete_previous_on_send=True
    )

# ==============================================================================
# 🎮 LÓGICA DE AÇÕES (COMBATE)
# ==============================================================================

# ==============================================================================
# ✨ SISTEMA DE SKILLS NAS CATACUMBAS
# ==============================================================================
async def show_catacomb_skills_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Abre o menu para escolher uma habilidade na Raid."""
    query = update.callback_query
    
    from .entry_handler import _get_safe_id
    user_id = await _get_safe_id(update, context)
    if not user_id:
        await query.answer("Erro de sessão.", show_alert=True)
        return

    from . import raid_manager
    active_raid = None
    for code, session in raid_manager.ACTIVE_RAIDS.items():
        if user_id in session.get("players", {}):
            active_raid = session
            break
            
    if not active_raid:
        await query.answer("Não estás numa raid ativa.", show_alert=True)
        return

    pdata = await player_manager.get_player_data(user_id)
    skills = pdata.get("skills", {})
    
    if not skills:
        await query.answer("Não tens nenhuma habilidade equipada!", show_alert=True)
        return

    from modules.game_data.skills import get_skill_data_with_rarity
    from modules.cooldowns import verificar_cooldown
    
    kb = []
    current_row = []
    
    for skill_id in skills.keys():
        s_data = get_skill_data_with_rarity(pdata, skill_id)
        if not s_data: continue
        
        if s_data.get("type") == "passive": continue
        
        name = s_data.get("display_name", skill_id)
        mana = s_data.get("mana_cost", 0)
        
        # 🔥 CORREÇÃO DA LEITURA DE COOLDOWN 🔥
        pode_usar, msg_cd = verificar_cooldown(pdata, skill_id)
        
        if not pode_usar:
            # Pega os turnos diretamente do dicionário do jogador para ter o número exato
            turnos_restantes = pdata.get("cooldowns", {}).get(skill_id, 0)
            btn_text = f"⏳ {name} ({turnos_restantes}T)"
            cb_data = f"cat_skill_cd:{turnos_restantes}" 
        else:
            btn_text = f"✨ {name} (-{mana}MP)"
            cb_data = f"cat_use_skill:{skill_id}" 
            
        current_row.append(InlineKeyboardButton(btn_text, callback_data=cb_data))
        
        if len(current_row) == 2:
            kb.append(current_row)
            current_row = []
            
    if current_row:
        kb.append(current_row)
        
    kb.append([InlineKeyboardButton("⬅️ Voltar ao Combate", callback_data="cat_combat_refresh")])

    try:
        await query.answer()
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))
    except Exception: pass
        
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
            # FIX: Adicionado user_id que faltava na chamada
            await _handle_victory(update, context, session, user_id)
        return

    # --- Ação: Ataque ---
    if action == "cat_act_attack":
        pdata = await player_manager.get_player_data(user_id)
        if pdata.get("current_hp", 0) <= 0:
            await query.answer("Estás morto!", show_alert=True)
            return

        boss = session.get("boss")
        stats = await player_manager.get_player_total_stats(pdata)

        # 1. PROCESSA ATAQUE VIA ENGINE (Garante Críticos e Atributos Reais)
        res = await combat_engine.processar_acao_combate(
            attacker_pdata=pdata,
            attacker_stats=stats,
            target_stats=boss,
            skill_id=None,
            attacker_current_hp=pdata.get("current_hp", 100)
        )

        # 2. DISPATCH DE EFEITOS
        ctx = CombatContext(event=EVENT_ON_BEFORE_DAMAGE, source=pdata, target=boss, battle=session, damage=res["total_damage"])
        effects_engine.dispatch(EVENT_ON_BEFORE_DAMAGE, ctx)
        
        boss["current_hp"] = max(0, boss["current_hp"] - ctx.damage)
        
        # 3. LOGS
        for msg in res["log_messages"]:
            session["turn_log"].append(f"⚔️ {msg}")

        # 4. VERIFICA MORTE DO BOSS OU TURNO DO MONSTRO
        if boss["current_hp"] <= 0:
            session["floor_cleared"] = True
            session["turn_log"].append(f"💀 **{boss['name']} DERROTADO!**")
        else:
            # Incrementa contador de turno do monstro
            session["monster_turn_counter"] = session.get("monster_turn_counter", 0) + 1
            if session["monster_turn_counter"] >= session.get("monster_turn_threshold", 3):
                session["monster_turn_counter"] = 0
                await execute_boss_turn(update, context, session)

        await player_manager.save_player_data(user_id, pdata)
        await refresh_battle_interface(update, context, session, user_id, turn_state="player_attacked")

async def catacomb_use_skill_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa o uso de uma habilidade na Raid com Motor Unificado."""
    query = update.callback_query
    
    try:
        skill_id = query.data.split(":")[1]
    except IndexError:
        await query.answer("Erro ao ler habilidade.", show_alert=True)
        return

    from .entry_handler import _get_safe_id
    user_id = await _get_safe_id(update, context)
    if not user_id: return
    
    from . import raid_manager
    code = raid_manager.PLAYER_LOCATION.get(str(user_id))
    active_raid = raid_manager.ACTIVE_RAIDS.get(code)
            
    if not active_raid or active_raid.get("floor_cleared"):
        await query.answer("Ação inválida no momento.", show_alert=True)
        return

    pdata = await player_manager.get_player_data(user_id)
    if not pdata or pdata.get("current_hp", 0) <= 0:
        await query.answer("Estás morto ou inválido!", show_alert=True)
        return

    from modules.effects import engine as effects_engine
    if not effects_engine.can_act(pdata):
        await query.answer("💫 Estás atordoado e não podes agir!", show_alert=True)
        return

    from modules.game_data.skills import get_skill_data_with_rarity
    s_data = get_skill_data_with_rarity(pdata, skill_id)
    if not s_data:
        await query.answer("Habilidade não encontrada!", show_alert=True)
        return

    # 🔥 CORREÇÃO DO BLOQUEIO AQUI 🔥
    from modules.cooldowns import verificar_cooldown, aplicar_cooldown, iniciar_turno
    pode_usar, msg_cd = verificar_cooldown(pdata, skill_id)
    if not pode_usar:
        await query.answer(msg_cd, show_alert=True)
        return

    mana_cost = int(s_data.get("mana_cost", 0))
    from modules.player.actions import spend_mana
    if not spend_mana(pdata, mana_cost):
        await query.answer(f"Mana insuficiente! Precisas de {mana_cost} MP.", show_alert=True)
        return

    rarity = pdata.get("skills", {}).get(skill_id, {}).get("rarity", "comum")
    pdata = aplicar_cooldown(pdata, skill_id, rarity)

    boss = active_raid.get("boss")
    stats = await player_manager.get_player_total_stats(pdata)
    
    from modules.combat import combat_engine
    res = await combat_engine.processar_acao_combate(
        attacker_pdata=pdata,
        attacker_stats=stats,
        target_stats=boss,
        skill_id=skill_id,
        attacker_current_hp=pdata.get("current_hp", 100)
    )

    from modules.effects.models import CombatContext, EVENT_ON_BEFORE_DAMAGE
    ctx = CombatContext(event=EVENT_ON_BEFORE_DAMAGE, source=pdata, target=boss, battle=active_raid, damage=res["total_damage"])
    effects_engine.dispatch(EVENT_ON_BEFORE_DAMAGE, ctx)
    
    boss["current_hp"] = max(0, int(boss.get("current_hp", 0)) - ctx.damage)
    
    skill_name = s_data.get("display_name", skill_id)
    player_name = pdata.get("name", "Jogador")
    
    if "turn_log" not in active_raid: active_raid["turn_log"] = []
    active_raid["turn_log"].append(f"✨ **{player_name}** usou **{skill_name}**!")
    
    for msg in res["log_messages"]:
        active_raid["turn_log"].append(f"   {msg}")

    pdata, msgs_cd = iniciar_turno(pdata)
    if msgs_cd: active_raid["turn_log"].extend(msgs_cd)
    
    await player_manager.save_player_data(user_id, pdata)

    if boss["current_hp"] <= 0:
        active_raid["floor_cleared"] = True
        active_raid["turn_log"].append(f"💀 **{boss['name']}** foi derrotado!")
        if active_raid["current_floor"] >= active_raid["total_floors"]:
            await _handle_victory(update, context, active_raid, user_id)
            return
    else:
        active_raid["monster_turn_counter"] = active_raid.get("monster_turn_counter", 0) + 1
        if active_raid["monster_turn_counter"] >= active_raid.get("monster_turn_threshold", 3):
            active_raid["monster_turn_counter"] = 0
            active_raid["turn_log"].append(f"⚠️ **{boss['name']} revida em área!**")
            boss_atk = boss.get("attack", 20)
            
            for pid in list(active_raid["players"].keys()):
                ally_data = await player_manager.get_player_data(str(pid))
                if ally_data and ally_data.get("current_hp", 0) > 0:
                    ally_stats = await player_manager.get_player_total_stats(ally_data)
                    boss_dmg = max(1, int(boss_atk * 0.8) - int(ally_stats.get("defense", 10) * 0.6))
                    ally_data["current_hp"] = max(0, ally_data.get("current_hp", 100) - boss_dmg)
                    await player_manager.save_player_data(str(pid), ally_data)
                    
                    if ally_data["current_hp"] == 0:
                        active_raid["turn_log"].append(f"💀 {active_raid['players'][pid]} caiu!")

    if len(active_raid["turn_log"]) > 10: 
        active_raid["turn_log"] = active_raid["turn_log"][-10:]

    try: await query.answer()
    except: pass 
    
    from .combat_handler import refresh_battle_interface
    await refresh_battle_interface(update, context, active_raid, user_id)

async def catacomb_skill_cd_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    turnos = query.data.split(":")[1]
    await query.answer(f"⏳ Habilidade em recarga! Aguarda {turnos} turnos.", show_alert=True)
    
# ==============================================================================
# 🌟 SISTEMA DE RESTAURAÇÃO (PÓS-RAID)
# ==============================================================================
async def auto_revive_player(user_id: str):
    """Restaura 100% do HP e MP do jogador ao finalizar ou abandonar a Raid."""
    try:
        pdata = await player_manager.get_player_data(user_id)
        if pdata:
            # Puxa os status totais reais do jogador (com equipamentos e bónus)
            stats = await player_manager.get_player_total_stats(pdata)
            
            # Restaura a Vida e a Mana aos valores máximos
            pdata["current_hp"] = stats.get("max_hp", 100)
            pdata["current_mp"] = stats.get("max_mana", 50)
            
            # Liberta o jogador do estado de combate (evita que fique preso)
            pdata["player_state"] = {"action": "idle"}
            
            await player_manager.save_player_data(user_id, pdata)
            print(f"[DEBUG] Jogador {user_id} 100% restaurado após as Catacumbas.")
    except Exception as e:
        print(f"[ERRO] Falha ao tentar restaurar jogador {user_id}: {e}")
                
async def _handle_victory(update: Update, context: ContextTypes.DEFAULT_TYPE, active_raid: dict, user_id: str):
    """Processa a vitória final, gera loot específico da classe e limpa a sessão."""
    from modules.player import inventory as player_inventory
    from modules.game_data.equipment import ITEM_DATABASE
    from modules.game_data.rarity import RARITY_DATA
    from . import raid_manager, config
    import random
    
    active_raid["turn_log"].append(f"🏆 **VITÓRIA LENDÁRIA!** O Guardião caiu!")
    
    # 🔥 NOVO: Cria uma lista exclusiva só para o Loot!
    active_raid["loot_log"] = []

    scaling = active_raid.get("scaling_factor", 1.0)
    xp_final = int(config.REWARDS.get("xp_fixed", 800) * scaling)
    gold_final = int(config.REWARDS.get("gold_fixed", 1500) * scaling)
    
    drop_chance = config.REWARDS.get("equipment_drop_chance", 0.85)
    rarity_weights = config.REWARDS.get("rarity_weights", {
        "comum": 30, "bom": 30, "raro": 20, "epico": 10, "lendario": 7, "unico": 2.5, "mitico": 0.5
    })

    player_ids = list(active_raid.get("players", {}).keys())

    for pid in player_ids:
        pid_str = str(pid)
        pdata = await player_manager.get_player_data(pid_str)
        if not pdata: continue
        
        p_name = active_raid['players'][pid_str]

        # 1. Dá Ouro e XP
        player_manager.add_gold(pdata, gold_final)
        pdata["xp"] = pdata.get("xp", 0) + xp_final
        active_raid["loot_log"].append(f"✨ **{p_name}**: +{xp_final} XP | 💰 +{gold_final} Ouro")
        
        # 2. Rola o Drop de Equipamento do Set
        if random.random() <= drop_chance:
            player_class = pdata.get("class", "guerreiro").lower()
            
            # Filtra os itens do Set que a classe do jogador pode usar
            possible_items = []
            for item_id, item_data in ITEM_DATABASE.items():
                if item_data.get("set_id") == "set_heranca_real":
                    if player_class in item_data.get("class_req", []):
                        possible_items.append((item_id, item_data))
            
            if possible_items:
                # Escolhe uma peça aleatória (Elmo, Arma, Calça, etc)
                chosen_item_id, chosen_item_data = random.choice(possible_items)
                
                # Rola a Raridade (Pode ser Mítico!)
                r_keys = list(rarity_weights.keys())
                r_weights = list(rarity_weights.values())
                chosen_rarity = random.choices(r_keys, weights=r_weights, k=1)[0]
                rarity_emoji = RARITY_DATA.get(chosen_rarity, {}).get("emoji", "💠")
                
                # Cria o item único e dá ao jogador
                novo_item = {
                    "base_id": chosen_item_id,
                    "rarity": chosen_rarity,
                    "obtido_em": "Catacumbas Reais",
                    "stats": {} 
                }
                player_inventory.add_unique_item(pdata, novo_item)
                
                # Registra no painel visual
                active_raid["loot_log"].append(f"📦 **{p_name}** achou: {rarity_emoji} _{chosen_item_data['nome_exibicao']}_ ({chosen_rarity.upper()})")

        # Verifica Level Up e salva
        player_manager.check_and_apply_level_up(pdata)
        await player_manager.save_player_data(pid_str, pdata)
        
        # Ressurreição automática pós-raid
        from .combat_handler import auto_revive_player
        await auto_revive_player(pid_str)

    # 3. Finaliza a Raid
    active_raid["status"] = "finished"
    for pid in player_ids:
        if str(pid) in raid_manager.PLAYER_LOCATION:
            del raid_manager.PLAYER_LOCATION[str(pid)]

    # Chama a interface final
    await refresh_battle_interface(update, context, active_raid, user_id, turn_state="victory")
    
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
    CallbackQueryHandler(refresh_cb, pattern="^cat_combat_refresh"),
    # 👇 ADICIONA ESTES DOIS 👇
    CallbackQueryHandler(combat_handler.catacomb_use_skill_cb, pattern="^cat_use_skill:.*$"),
    CallbackQueryHandler(combat_handler.catacomb_skill_cd_cb, pattern="^cat_skill_cd:.*$"),

]