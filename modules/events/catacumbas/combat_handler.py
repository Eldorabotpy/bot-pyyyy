# modules/events/catacumbas/combat_handler.py
# (VERSÃO BLINDADA: Auth Híbrida + Correção de IDs)

import random
import logging
from typing import Union
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules import player_manager
from modules.combat import criticals, combat_engine
from handlers.profile_handler import _get_class_media
from modules.auth_utils import get_current_player_id

# Importamos o formatador visual novo
from handlers import utils 

from . import config, raid_manager, entry_handler

logger = logging.getLogger(__name__)

# ==============================================================================
# 🎨 UTILITÁRIOS DE MÍDIA
# ==============================================================================

def _get_enemy_media(session: dict) -> str:
    """Seleciona a mídia correta (Boss ou Mob)."""
    # Se tiver uma lista de inimigos, pega o primeiro vivo ou o Boss
    enemies = session.get("enemies", [])
    boss = session.get("boss")
    
    # Prioridade visual: Boss > Primeiro Inimigo Vivo
    target = boss
    if not target and enemies:
        target = next((m for m in enemies if m["current_hp"] > 0), enemies[0])
    
    if not target: return config.MEDIA_KEYS.get("lobby_screen")

    if target.get("current_hp", 0) <= 0:
         pass 
         
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

async def refresh_battle_interface(update: Update, context: ContextTypes.DEFAULT_TYPE, session: dict, user_id: Union[int, str], turn_state: str = "player_turn"):
    """
    Renderiza a tela de combate usando o novo visual detalhado.
    """
    # 1. Carrega dados do usuário atual (para validar morte)
    # player_manager já foi blindado para aceitar Union[int, str]
    current_pdata = await player_manager.get_player_data(user_id)
    
    if current_pdata.get("current_hp", 0) <= 0:
        await entry_handler.send_event_interface(
            update, context, 
            config.TEXTS["defeat"], 
            [[InlineKeyboardButton("🔄 Observar Batalha", callback_data="cat_combat_refresh")]],
            media_key=config.MEDIA_KEYS["defeat"]
        )
        return

    # 2. Verifica se o Andar foi Limpo
    if session.get("floor_cleared", False):
        floor = session["current_floor"]
        txt = f"🚪 **ANDAR {floor} LIMPO!**\nOs inimigos foram derrotados.\nPreparem-se para descer..."
        kb = [[InlineKeyboardButton("⬇️ DESCER ESCADAS", callback_data="cat_act_next_floor")]]
        await entry_handler.send_event_interface(
            update, context, txt, kb, media_key=config.MEDIA_KEYS["lobby_screen"]
        )
        return

    # 3. CARREGA DADOS DE TODOS OS JOGADORES
    # (Necessário para o novo visual mostrar a lista de aliados com HP/MP)
    all_players_data = {}
    for pid in session.get("players", {}):
        all_players_data[pid] = await player_manager.get_player_data(pid)

    # 4. GERA O TEXTO USANDO O HANDLERS/UTILS.PY
    # Aqui está a mágica: chamamos a função que você pediu para editar
    text = await utils.format_catacomb_interface(session, user_id, all_players_data)

    # 5. Botões de Ação
    kb = [
        [InlineKeyboardButton("⚔️ ATACAR", callback_data="cat_act_attack")],
        # Futuro: [InlineKeyboardButton("🔥 SKILL", callback_data="cat_skill_menu")],
        [InlineKeyboardButton("🧪 Poção", callback_data="cat_act_heal_small"),
         InlineKeyboardButton("🔄 Atualizar", callback_data="cat_combat_refresh")]
    ]

    # 6. Seleciona Mídia
    media_key = _get_enemy_media(session)
    
    # Se o jogador foi atacado, mostra a foto dele (efeito visual)
    if turn_state == "monster_attacked":
        p_media = _get_class_media(current_pdata, purpose="combate")
        if p_media and p_media.get("id"): 
            media_key = p_media.get("id")

    await entry_handler.send_event_interface(update, context, text, kb, media_key=media_key)

# ==============================================================================
# 🎮 LÓGICA DE AÇÕES (COMBATE)
# ==============================================================================

async def combat_action_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # --- AUTH HÍBRIDA ---
    # Usamos user_id seguro para lógica e user.first_name para visual
    user_id = get_current_player_id(update, context)
    user_name = update.effective_user.first_name
    action = query.data
    
    # Busca sessão usando o ID seguro
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

    # --- Verifica Alvo Vivo ---
    target = session.get("boss")
    # (Se você implementar lista de enemies, adapte aqui para selecionar qual atacar)
    
    if session.get("floor_cleared") or (target and target["current_hp"] <= 0):
        await query.answer("Inimigo já derrotado.")
        await refresh_battle_interface(update, context, session, user_id)
        return

    # --- Prepara Dados para Combate ---
    pdata = await player_manager.get_player_data(user_id)
    stats = await player_manager.get_player_total_stats(pdata)
    
    # Define stats do inimigo para o motor de combate
    enemy_stats = {
        "name": target["name"],
        "hp": target["current_hp"], "max_hp": target["max_hp"],
        "attack": target["attack"], "defense": target["defense"],
        "initiative": target["initiative"], "luck": 5, "monster_luck": True
    }

    # 1. Turno do Jogador
    if action == "cat_act_attack":
        res = await combat_engine.processar_acao_combate(
            pdata, stats, enemy_stats, None, pdata.get("current_hp", 100)
        )
        dmg = res["total_damage"]
        target["current_hp"] -= dmg
        session["turn_log"].append(f"⚔️ {user_name} causou {dmg} dano!")
        
    elif action == "cat_act_heal_small":
        heal = 250
        pdata["current_hp"] = min(stats["max_hp"], pdata.get("current_hp", 0) + heal)
        session["turn_log"].append(f"🧪 {user_name} curou {heal}.")

    # 2. Verifica Morte do Inimigo
    if target["current_hp"] <= 0:
        target["current_hp"] = 0
        session["floor_cleared"] = True # Marca andar como limpo
        session["turn_log"].append(f"💀 **{target['name']} MORREU!**")
        await refresh_battle_interface(update, context, session, user_id)
        return

    # 3. Turno do Inimigo (Contra-ataque)
    # 10% de chance de esquiva passiva do jogador
    if random.random() > 0.10:
        bdmg, is_crit, _ = criticals.roll_damage(enemy_stats, stats)
        pdata["current_hp"] -= bdmg
        msg = f"👹 {target['name']} atacou: {bdmg}"
        if is_crit: msg += " (CRIT!)"
        session["turn_log"].append(msg)
    else:
        session["turn_log"].append(f"💨 {user_name} esquivou!")
    
    await player_manager.save_player_data(user_id, pdata)
    await refresh_battle_interface(update, context, session, user_id, turn_state="monster_attacked")

# ==============================================================================
# 🔄 LOOP DE ATUALIZAÇÃO
# ==============================================================================

async def refresh_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_current_player_id(update, context)
    code = raid_manager.PLAYER_LOCATION.get(user_id)
    session = raid_manager.ACTIVE_RAIDS.get(code)
    if session:
        await refresh_battle_interface(update, context, session, user_id)
    else:
        if update.callback_query:
            await update.callback_query.answer("Raid não encontrada.")

async def _handle_victory(update: Update, context: ContextTypes.DEFAULT_TYPE, session: dict):
    if session["status"] == "finished": return
    session["status"] = "finished"
    if session["raid_id"] in raid_manager.ACTIVE_RAIDS:
        del raid_manager.ACTIVE_RAIDS[session["raid_id"]]

    loot_log = []
    rewards = config.REWARDS

    for pid in session["players"]:
        pdata = await player_manager.get_player_data(pid)
        pdata["gold"] = pdata.get("gold", 0) + rewards["gold_fixed"]
        pdata["xp"] = pdata.get("xp", 0) + rewards["xp_fixed"]
        
        # Loot Raro
        inv = pdata.setdefault("inventory", {})
        for item in rewards.get("rare_items", []):
            if random.random() < item["chance"]:
                inv[item["id"]] = inv.get(item["id"], 0) + 1
                if pid == session["leader_id"]: # Log só uma vez ou para todos (simplificado)
                     loot_log.append(f"- {item['id']}")
        
        # Cura Full
        ts = await player_manager.get_player_total_stats(pdata)
        pdata["current_hp"] = ts["max_hp"]
        await player_manager.save_player_data(pid, pdata)
        if pid in raid_manager.PLAYER_LOCATION: del raid_manager.PLAYER_LOCATION[pid]

    # Usa utils.format_catacomb_interface mesmo na vitória? Não, melhor texto simples ou dedicado
    extra = "\n".join(set(loot_log))
    full_txt = f"{config.TEXTS['victory']}\n\n💰 Ouro: {rewards['gold_fixed']}\n✨ XP: {rewards['xp_fixed']}\n🎁 Loot:\n{extra}"

    await entry_handler.send_event_interface(
        update, context, full_txt, 
        [[InlineKeyboardButton("🏆 SAIR", callback_data="back_to_kingdom")]],
        media_key=config.MEDIA_KEYS["victory"]
    )

handlers = [
    CallbackQueryHandler(combat_action_cb, pattern="^cat_act_"),
    CallbackQueryHandler(refresh_cb, pattern="^cat_combat_refresh")
]