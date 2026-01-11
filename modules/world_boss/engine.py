# modules/world_boss/engine.py
# (VERSÃO FINAL: Full String ID + Compatibilidade ObjectId)

import json
import os
import random
import time
import logging
import asyncio
import html
from datetime import datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import Forbidden, TelegramError

from modules import player_manager, game_data, file_ids
from modules.combat import criticals, combat_engine
from modules.player import stats as player_stats_engine
from modules.cooldowns import verificar_cooldown, aplicar_cooldown, iniciar_turno
from modules.game_data.skills import SKILL_DATA, get_skill_data_with_rarity
from modules.game_data.skins import SKIN_CATALOG
from modules.combat.party_engine import process_party_effects

logger = logging.getLogger(__name__)

# --- CONSTANTES ---
BOSS_STATE_FILE = "world_boss_state.json"
ANNOUNCEMENT_CHAT_ID = -1002881364171 
ANNOUNCEMENT_THREAD_ID = 24           
PARTICIPATION_XP = 400
PARTICIPATION_GOLD = 1000

POSSIBLE_LOCATIONS = [
    "pradaria_inicial", "floresta_sombria", "pedreira_granito",
    "campos_linho", "pico_grifo", "mina_ferro",
    "forja_abandonada", "pantano_maldito"
]

SKILL_REWARD_POOL = [
    "samurai_sombra_demoniaca", "samurai_corte_iaijutsu", "samurai_passive_perfect_parry", 
    "assassino_ataque_furtivo", "assassino_active_guillotine_strike", "assassino_passive_potent_toxins",
    "bardo_melodia_restauradora", "bardo_passive_perfect_pitch", "bardo_passive_symphony_of_power",
    "mago_bola_de_fogo", "mago_active_arcane_ward", "mago_active_meteor_swarm",
    "monge_rajada_de_punhos", "monge_active_thunder_palm", "monge_active_transcendence",
    "cacador_flecha_precisa","cacador_active_ricochet_arrow", "cacador_passive_apex_predator",
    "berserker_golpe_selvagem", "berserker_golpe_divino_da_ira", "berserker_ultimo_recurso",
    "guerreiro_corte_perfurante", "guerreiro_colossal_defense", "guerreiro_bencao_sagrada"
]
SKILL_CHANCE = 1.0 

SKIN_REWARD_POOL = [
    "samurai_armadura_shogun", "samurai_armadura_demoniaca",
    "bardo_requiem_sombrio", "bardo_traje_maestro", 
    "monge_aspecto_asura", "monge_quimono_dragao", 
    "berserker_infernal", "berserker_pele_urso",
    "cacador_cacador_dragoes", "cacador_patrulheiro_elfico",
    "assassino_manto_espectral", "mago_arquimago_caos", "mago_traje_arcano",
    "guerreiro_placas_douradas", "guerreiro_armadura_negra", "guerreiro_armadura_jade"
]
SKIN_CHANCE = 2.0 

LOOT_REWARD_POOL = [
    ("pocao_cura_leve", 3, 7), ("pocao_cura_media", 3, 7),
    ("gems", 3, 5), ("frasco_sabedoria", 5, 10),
    ("cristal_de_abertura", 4, 10), ("pedra_do_aprimoramento", 3, 14),
    ("pergaminho_durabilidade", 5, 10), ("sigilo_protecao", 1, 10)
]
LOOT_CHANCE = 10.0

class WorldBossManager:
    def __init__(self):
        self.is_active = False
        self.location = "Terras Devastadas"
        self.entities = {}
        self.active_fighters = set() 
        self.waiting_queue = []      
        self.player_states = {}      
        self.max_concurrent_fighters = 20
        self.environment_hazard = False
        self.hazard_turns = 0
        self.damage_leaderboard = {}
        self.last_hitter_id = None
        
        self.load_state()

        if not self.entities:
            self._reset_entities()

    def _reset_entities(self):
        generated_loot = []
        for skill in SKILL_REWARD_POOL: generated_loot.append((skill, SKILL_CHANCE))
        for skin in SKIN_REWARD_POOL: generated_loot.append((skin, SKIN_CHANCE))
        for item_tuple in LOOT_REWARD_POOL: generated_loot.append((item_tuple[0], LOOT_CHANCE))

        self.entities = {
            "boss": {
                "name": "𝐋𝐨𝐫𝐝𝐞 𝐝𝐚𝐬 𝐒𝐨𝐦𝐛𝐫𝐚𝐬", "hp": 40000, "max_hp": 40000, 
                "alive": True, "stats": {"attack": 80, "defense": 60, "initiative": 5, "luck": 20},
                "turn_counter": 0,
                "loot_table": generated_loot
            },
            "witch_heal": {
                "name": "𝐁𝐫𝐮𝐱𝐚 𝐝𝐚 𝐂𝐮𝐫𝐚", "hp": 10000, "max_hp": 10000, 
                "alive": True, "stats": {"attack": 50, "defense": 50, "initiative": 5, "luck": 10},
                "turn_counter": 0 
            },
            "witch_debuff": {
                "name": "𝐁𝐫𝐮𝐱𝐚 𝐝𝐚 𝐂𝐚𝐨𝐬", "hp": 10000, "max_hp": 10000, 
                "alive": True, "stats": {"attack": 50, "defense": 50, "initiative": 5, "luck": 15},
                "turn_counter": 0 
            },
        }

    # --- PERSISTÊNCIA (JSON) ---
    def save_state(self):
        data = {
            "is_active": self.is_active,
            "location": self.location,
            "entities": self.entities,
            "active_fighters": list(self.active_fighters), 
            "waiting_queue": self.waiting_queue,
            "player_states": {str(k): v for k, v in self.player_states.items()}, # ✅ Força Chave String
            "environment_hazard": self.environment_hazard,
            "hazard_turns": self.hazard_turns,
            "damage_leaderboard": self.damage_leaderboard,
            "last_hitter_id": str(self.last_hitter_id) if self.last_hitter_id else None
        }
        try:
            with open(BOSS_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erro ao salvar estado do World Boss: {e}")

    def load_state(self):
        if not os.path.exists(BOSS_STATE_FILE): return

        try:
            with open(BOSS_STATE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.is_active = data.get("is_active", False)
            self.location = data.get("location", "Terras Devastadas")
            self.entities = data.get("entities", {})
            
            # ✅ Restaura como String
            self.active_fighters = set(str(x) for x in data.get("active_fighters", []))
            self.waiting_queue = [str(x) for x in data.get("waiting_queue", [])]
            
            # ✅ Restaura chaves do dict como String (ObjectId)
            p_states_raw = data.get("player_states", {})
            self.player_states = {str(k): v for k, v in p_states_raw.items()}
            
            self.environment_hazard = data.get("environment_hazard", False)
            self.hazard_turns = data.get("hazard_turns", 0)
            self.damage_leaderboard = data.get("damage_leaderboard", {})
            self.last_hitter_id = str(data.get("last_hitter_id")) if data.get("last_hitter_id") else None
            
            logger.info("Estado do World Boss carregado com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao carregar estado do World Boss: {e}")
            self._reset_entities()

    # --- CONTROLE ---
    
    @property
    def state(self):
        return {"is_active": self.is_active, "location": self.location, "entities": self.entities}
    
    async def get_battle_hud(self):
        # ... (Mantém igual)
        ents = self.entities
        boss = ents.get("boss")
        if not self.is_active or not boss or not boss["alive"]: return "O Boss foi derrotado!"
        pct = boss["hp"] / boss["max_hp"]
        fill = int(pct * 10)
        bar = "🟩" * fill + "⬜" * (10 - fill)
        txt = f"👹 <b>{boss['name']}</b>\n{bar} {boss['hp']:,}\n"
        w1 = ents.get("witch_heal", {})
        w2 = ents.get("witch_debuff", {})
        w1_st = "𝗖𝘂𝗿𝗮 💚" if w1.get("alive") else "💀"
        w2_st = "𝗖𝗮𝗼𝘀 ☠️" if w2.get("alive") else "💀"
        txt += f"Bruxas: {w1_st} | {w2_st}\n"
        if self.environment_hazard: txt += "🔥 𝘾𝘼𝙈𝙋𝙊 𝙀𝙈 𝘾𝙃𝘼𝙈𝘼𝙎!"
        return txt

    def start_event(self):
        if self.is_active: return {"error": "𝕁𝕒́ 𝕒𝕥𝕚𝕧𝕠."}
        self.is_active = True
        self.location = random.choice(POSSIBLE_LOCATIONS)
        self.active_fighters.clear()
        self.waiting_queue.clear()
        self.player_states.clear()
        self.damage_leaderboard.clear()
        self.environment_hazard = False
        self.hazard_turns = 0
        self._reset_entities()
        self.save_state()
        return {"success": True, "location": self.location}

    def end_event(self, reason="Ｔｅｍｐｏ　ｅｓｇｏｔａｄｏ"):
        active_status = self.is_active
        self.is_active = False
        self.active_fighters.clear()
        self.save_state()
        if not active_status: return {}
        return {
            "leaderboard": self.damage_leaderboard.copy(),
            "last_hitter_id": self.last_hitter_id,
            "boss_defeated": (reason == "Boss derrotado"),
            "boss": self.entities.get("boss", {})
        }

    async def add_player_to_event(self, user_id, player_data):
        user_id = str(user_id) # ✅ Garante String
        if not self.is_active: return "inactive"
        if user_id in self.active_fighters: return "active"
        if user_id in self.waiting_queue: return "waiting"

        if len(self.active_fighters) < self.max_concurrent_fighters:
            self.active_fighters.add(user_id)
            await self._setup_player_state(user_id, player_data)
            self.save_state()
            return "active"
        else:
            self.waiting_queue.append(user_id)
            self.save_state()
            return "waiting"

    async def _setup_player_state(self, user_id, player_data):
        stats = await player_manager.get_player_total_stats(player_data)
        self.player_states[str(user_id)] = {
            'hp': min(player_data.get('current_hp', 999), stats['max_hp']),
            'max_hp': stats['max_hp'],
            'mp': min(player_data.get('current_mp', 999), stats['max_mana']),
            'max_mp': stats['max_mana'],
            'current_target': 'boss', 
            'log': '𝗘𝗻𝘁𝗿𝗼𝘂 𝗻𝗮 𝗯𝗮𝘁𝗮𝗹𝗵𝗮!'
        }

    def set_target(self, user_id, target_key):
        user_id = str(user_id)
        if user_id in self.player_states and target_key in self.entities:
            self.player_states[user_id]['current_target'] = target_key
            self.save_state()
            return True
        return False

    async def process_action(self, user_id, player_data, action_type, skill_id=None):
        user_id = str(user_id) # ✅ Garante String
        if user_id not in self.active_fighters: 
            return {"error": "𝙑𝙤𝙘𝙚̂ 𝙣𝙖̃𝙤 𝙚𝙨𝙩𝙖́ 𝙣𝙖 𝙡𝙪𝙩𝙖."}
        
        state = self.player_states[user_id]
        respawn_until = state.get('respawn_until', 0)
        now = time.time()
        if now < respawn_until:
            wait_time = int(respawn_until - now)
            return {"error": f"👻 𝗥𝗲𝘀𝘀𝘂𝘀𝗰𝗶𝘁𝗮𝗻𝗱𝗼... 𝗔𝗴𝘂𝗮𝗿𝗱𝗲 {wait_time}𝘀"}
        
        target_key = state['current_target']
        target = self.entities.get(target_key)
        if not target or not target["alive"]:
            return {"error": "𝗔𝗹𝘃𝗼 𝗷𝗮́ 𝗱𝗲𝗿𝗿𝗼𝘁𝗮𝗱𝗼! 𝗘𝘀𝗰𝗼𝗹𝗵𝗮 𝗼𝘂𝘁𝗿𝗼."}

        logs = []
        p_stats = await player_manager.get_player_total_stats(player_data)
        current_mp_db = player_data.get("current_mp", 0)
        state['mp'] = current_mp_db 
        
        caster_name = player_data.get("character_name", "Aliado")
        dmg = 0
        witches_alive = self.entities["witch_heal"]["alive"] or self.entities["witch_debuff"]["alive"]
        boss_immune = (target_key == "boss" and witches_alive)

        # --- COMBATE ---
        if action_type == "attack":
            if boss_immune:
                logs.append("🛡️ 𝗕𝗢𝗦𝗦 𝗜𝗠𝗨𝗡𝗘! 𝗗𝗲𝗿𝗿𝗼𝘁𝗲 𝗮𝘀 𝗕𝗿𝘂𝘅𝗮𝘀 𝗽𝗿𝗶𝗺𝗲𝗶𝗿𝗼!")
            else:
                res = await combat_engine.processar_acao_combate(player_data, p_stats, target["stats"], None, state['hp'])
                dmg = res["total_damage"]
                target["hp"] = max(0, target["hp"] - dmg)
                logs.append(f"⚔️ 𝙑𝙤𝙘𝙚̂ 𝙘𝙖𝙪𝙨𝙤𝙪 {dmg} 𝗲𝗺 {target['name']}")
                self.damage_leaderboard[user_id] = self.damage_leaderboard.get(user_id, 0) + dmg
                self.last_hitter_id = user_id
        
        elif action_type == "skill":
            s_info = get_skill_data_with_rarity(player_data, skill_id)
            if not s_info: return {"error": "Skill inválida."}
            
            mana_cost = s_info.get("mana_cost", 0)
            if current_mp_db < mana_cost: return {"error": f"Mana insuficiente! ({current_mp_db}/{mana_cost})"}
            
            pode_usar, msg_cd = verificar_cooldown(player_data, skill_id)
            if not pode_usar: return {"error": msg_cd}
            
            player_data["current_mp"] -= mana_cost
            state['mp'] = player_data["current_mp"] 
            
            rarity = "comum"
            player_skills = player_data.get("skills", {})
            if skill_id in player_skills: rarity = player_skills[skill_id].get("rarity", "comum")
            player_data = aplicar_cooldown(player_data, skill_id, rarity)

            effects = s_info.get("effects", {})
            if "chance_to_stun" in effects and random.random() < float(effects["chance_to_stun"]):
                target["is_stunned"] = True
                logs.append(f"💫 <b>{target['name']} foi ATORDOADO!</b>")
            
            skill_type = s_info.get("type", "active")

            if skill_type == "support":
                support_logs = process_party_effects(user_id, caster_name, s_info, p_stats, self.player_states)
                logs.extend(support_logs)
                if not support_logs: logs.append("✨ Skill de suporte usada.")
            else:
                if boss_immune:
                    logs.append("🛡️ 𝗕𝗢𝗦𝗦 𝗜𝗠𝗨𝗡𝗘! 𝗗𝗲𝗿𝗿𝗼𝘁𝗲 𝗮𝘀 𝗕𝗿𝘂𝘅𝗮𝘀 𝗽𝗿𝗶𝗺𝗲𝗶𝗿𝗼!")
                else:
                    res = await combat_engine.processar_acao_combate(player_data, p_stats, target["stats"], skill_id, state['hp'])
                    dmg = res["total_damage"]
                    target["hp"] = max(0, target["hp"] - dmg)
                    logs.append(f"✨ 𝙑𝙤𝙘𝙚̂ 𝙪𝙨𝙤𝙪 𝙎𝙠𝙞𝙡𝙡: {dmg} 𝙙𝙖𝙣𝙤 𝙚𝙢 {target['name']}")
                    self.damage_leaderboard[user_id] = self.damage_leaderboard.get(user_id, 0) + dmg
                    self.last_hitter_id = user_id

        if target["hp"] <= 0:
            target["alive"] = False
            logs.append(f"💀 {target['name']} 𝗙𝗢𝗜 𝗗𝗘𝗥𝗥𝗢𝗧𝗔𝗗𝗢!")
            if target_key == "boss":
                self.save_state()
                return {"boss_defeated": True, "log": "𝗢 𝗥𝗘𝗜 𝗖𝗔𝗜𝗨!"}

        await self._process_mobs_turn(user_id, state, p_stats, logs)

        if state['hp'] <= 0:
            # Lógica de Morte / Milagre
            has_miracle = False
            # (Verificação simplificada de milagre - Mantenha sua lógica original se tiver passivas complexas)
            if not state.get("miracle_used") and has_miracle:
                state['hp'] = 1 
                state['miracle_used'] = True
                logs.append(f"✨ <b>MILAGRE!</b>")
            else:
                state['hp'] = state['max_hp']
                state['mp'] = state['max_mp']
                state['respawn_until'] = time.time() + 60 
                player_data['current_hp'] = state['max_hp']
                player_data['current_mp'] = state['max_mp']
                logs.append(f"☠️ 𝐕𝐎𝐂𝐄̂ 𝐌𝐎𝐑𝐑𝐄𝐔! (Curando... Retorno em 60s)")
                state['log'] = "\n".join(logs[-5:]) 
                
                real_id = player_data.get("_id", user_id)
                await player_manager.save_player_data(real_id, player_data)
                self.save_state()
                return {"respawning": True, "wait_time": 60, "state": state}

        player_data, msgs_cd = iniciar_turno(player_data)
        if msgs_cd: logs.extend(msgs_cd)

        all_logs = state.get('log', '').split('\n') + logs
        state['log'] = "\n".join(all_logs[-6:]) 
        
        player_data['current_hp'] = state['hp']
        player_data['current_mp'] = state['mp']
        
        real_id = player_data.get("_id", user_id)
        await player_manager.save_player_data(real_id, player_data)
        self.save_state() 
        return {"success": True, "state": state}
    
    async def _process_mobs_turn(self, user_id, state, p_stats, logs):
        # (Lógica mantida idêntica à sua, apenas garantindo que funcione)
        if self.environment_hazard:
            burn_dmg = int(state['max_hp'] * 0.05) 
            state['hp'] -= burn_dmg
            logs.append(f"🔥 𝙌𝙪𝙚𝙞𝙢𝙖𝙙𝙪𝙧𝙖: -{burn_dmg} HP")
            self.hazard_turns -= 1
            if self.hazard_turns <= 0: self.environment_hazard = False

        boss = self.entities["boss"]
        if boss.get("is_stunned", False):
            logs.append(f"💫 <b>Boss Atordoado!</b>")
            boss["is_stunned"] = False 
            return 

        if boss["alive"]:
            boss["turn_counter"] += 1
            if boss["turn_counter"] % 3 == 0:
                aoe_dmg = int(boss["stats"]["attack"] * 1.5)
                state['hp'] -= aoe_dmg
                logs.append(f"☄️ 𝐌𝐄𝐓𝐄𝐎𝐑𝐎! -{aoe_dmg} HP!")
                self.environment_hazard = True
                self.hazard_turns = 2 
                for fid in list(self.active_fighters):
                    if fid != user_id and fid in self.player_states:
                        self.player_states[fid]['hp'] -= aoe_dmg
            else:
                edmg, icrit, _ = criticals.roll_damage(boss["stats"], p_stats, {})
                state['hp'] -= edmg
                logs.append(f"🤕 𝗕𝗼𝘀𝘀 hit: -{edmg} HP")

        # Bruxas... (Código simplificado, mantendo a lógica original)
        for w_key in ["witch_heal", "witch_debuff"]:
            w = self.entities[w_key]
            if w["alive"]:
                dmg = int(w["stats"]["attack"] * 0.5)
                state['hp'] -= dmg

    def get_battle_view(self, user_id):
        return self.player_states.get(str(user_id))

world_boss_manager = WorldBossManager()

# ======================================================
# --- DM & LOOT DISTRIBUTION (CORE FIX HERE) ---
# ======================================================

async def _send_dm_to_winner(context: ContextTypes.DEFAULT_TYPE, chat_id: int, loot_messages: list[str]):
    if not loot_messages: return
    loot_str = "\n".join([f"• {item}" for item in loot_messages])
    message = (
        f"🎉 𝑹𝒆𝒄𝒐𝒎𝒑𝒆𝒏𝒔𝒂𝒔 𝒅𝒐 𝑫𝒆𝒎𝒐̂𝒏𝒊𝒐 𝑫𝒊𝒎𝒆𝒏𝒔𝒊𝒐𝒏𝒂𝒍 🎉\n\n"
        f"𝑷𝒂𝒓𝒂𝒃𝒆́𝒏𝒔! 𝑷𝒐𝒓 𝒔𝒖𝒂 𝒃𝒓𝒂𝒗𝒖𝒓𝒂 𝒏𝒂 𝒃𝒂𝒕𝒂𝒍𝒉𝒂, 𝒗𝒐𝒄𝒆̂ 𝒓𝒆𝒄𝒆𝒃𝒆𝒖:\n{loot_str}"
    )
    try:
        await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
    except (Forbidden, TelegramError): pass

async def distribute_loot_and_announce(context: ContextTypes.DEFAULT_TYPE, battle_results: dict):
    leaderboard = battle_results.get("participants", {}) 
    if not leaderboard: leaderboard = battle_results.get("leaderboard", {})
        
    last_hitter_id = str(battle_results.get("last_hitter_id"))
    boss_defeated = battle_results.get("boss_defeated", True)
    boss_data = battle_results.get("boss", {})

    if not leaderboard: return

    skill_winners_msg = []
    skin_winners_msg = []
    loot_summary = {} 
    total_participants = 0
    total_gold_distributed = 0
    total_xp_distributed = 0
    last_hit_msg = ""
    
    # --- TOP 3 ---
    ranking_data = []
    for uid_raw, dmg in leaderboard.items():
        ranking_data.append((str(uid_raw), dmg)) # ✅ Tudo String

    sorted_ranking = sorted(ranking_data, key=lambda item: item[1], reverse=True)
    
    top_3_msg = []
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, dmg) in enumerate(sorted_ranking[:3]):
        pdata = await player_manager.get_player_data(uid)
        safe_name = html.escape(pdata.get('character_name', 'Herói') if pdata else "Herói")
        medal = medals[i] if i < 3 else "🏅"
        top_3_msg.append(f"{medal} {safe_name} (<code>{dmg:,}</code> pts)")

    # --- LOOP DISTRIBUIÇÃO ---
    for user_id_raw, dmg_val in leaderboard.items():
        uid = str(user_id_raw) # ✅ ID String ObjectId
        dmg = dmg_val['damage'] if isinstance(dmg_val, dict) else dmg_val
        
        if dmg <= 0: continue
        
        pdata = await player_manager.get_player_data(uid) # ✅ Agora acha o jogador e inventário!
        if not pdata: continue
        
        total_participants += 1

        if boss_defeated:
            try:
                player_name = html.escape(pdata.get("character_name", f"Guerreiro"))
                loot_won_messages = []
                player_mudou = False

                # 1. Prêmios Fixos
                player_manager.add_gold(pdata, PARTICIPATION_GOLD)
                loot_won_messages.append(f"💰 <b>Ouro:</b> +{PARTICIPATION_GOLD}")
                total_gold_distributed += PARTICIPATION_GOLD
                
                player_manager.add_xp(pdata, PARTICIPATION_XP)
                loot_won_messages.append(f"✨ <b>XP:</b> +{PARTICIPATION_XP}")
                total_xp_distributed += PARTICIPATION_XP
                
                try:
                    _, _, level_up_msg = player_manager.check_and_apply_level_up(pdata)
                    if level_up_msg: loot_won_messages.append(level_up_msg)
                except: pass
                
                player_mudou = True

                # 2. Gacha Loot
                roll_rare = random.random() * 100
                rare_item_id = None
                
                if roll_rare <= 3.0: 
                    chosen_skin = random.choice(SKIN_REWARD_POOL)
                    rare_item_id = f"caixa_{chosen_skin}"
                    skn_id = rare_item_id.replace("caixa_", "")
                    d_name = SKIN_CATALOG.get(skn_id, {}).get("name", skn_id)
                    loot_won_messages.append(f"🎨 <b>SKIN RARA:</b> {d_name}")
                    skin_winners_msg.append(f"• {player_name} obteve <b>{d_name}</b>!")
                    
                elif roll_rare <= 10.0:
                    chosen_skill = random.choice(SKILL_REWARD_POOL)
                    rare_item_id = f"tomo_{chosen_skill}"
                    sk_id = rare_item_id.replace("tomo_", "")
                    d_name = SKILL_DATA.get(sk_id, {}).get("display_name", sk_id)
                    loot_won_messages.append(f"📚 <b>TÉCNICA:</b> {d_name}")
                    skill_winners_msg.append(f"• {player_name} obteve <b>{d_name}</b>!")

                if rare_item_id:
                    player_manager.add_item_to_inventory(pdata, rare_item_id, 1) # ✅ Inventário funciona agora
                    player_mudou = True

                if random.random() * 100 <= 50.0:
                    loot_tuple = random.choice(LOOT_REWARD_POOL)
                    item_id_common = loot_tuple[0]
                    qty = random.randint(loot_tuple[1], loot_tuple[2])
                    player_manager.add_item_to_inventory(pdata, item_id_common, qty)
                    player_mudou = True
                    d_name = game_data.ITEMS_DATA.get(item_id_common, {}).get("display_name", item_id_common)
                    loot_won_messages.append(f"📦 <b>Loot:</b> {d_name} (x{qty})")
                    loot_summary[d_name] = loot_summary.get(d_name, 0) + qty

                if player_mudou:
                    await player_manager.save_player_data(uid, pdata)
                
                # 3. Enviar DM (Precisa achar o ChatID numérico)
                target_chat_id = pdata.get("last_chat_id") or pdata.get("telegram_id_owner")
                if target_chat_id:
                    try:
                        await _send_dm_to_winner(context, int(target_chat_id), loot_won_messages)
                    except: pass

                if uid == last_hitter_id:
                    last_hit_msg = f"💥 <b>Golpe Final:</b> {player_name}"

            except Exception as e:
                logger.error(f"[WB_LOOT] Erro ao processar player {uid}: {e}")

    # --- ANÚNCIO CANAL (Mantido) ---
    separator = "━━━━━━━━━━━━━━━━━━"
    if not boss_defeated:
        title = "☁️ <b>AS SOMBRAS PERMANECEM...</b>"
        body = f"<i>Inimigo recuou.\n\n🛡️ <b>Top 3:</b>\n" + "\n".join(top_3_msg)
    else:
        title = "⚔️ <b>A LENDA FOI ESCRITA!</b>"
        body = f"<i>Boss <b>{boss_data.get('name')}</b> derrotado!</i>\n\n🏆 <b>MVP:</b>\n" + "\n".join(top_3_msg)
        if last_hit_msg: body += f"\n{last_hit_msg}"
        body += f"\n\n{separator}\n🌍 <b>ESPÓLIOS</b>\n├ ⚔️ <b>Heróis:</b> {total_participants}\n├ 💰 <b>Ouro:</b> {total_gold_distributed:,}\n└ ✨ <b>XP:</b> {total_xp_distributed:,}\n"
        
        if skin_winners_msg or skill_winners_msg:
            body += f"\n🚨 <b>ARTEFATOS LENDÁRIOS</b>\n"
            for msg in skin_winners_msg + skill_winners_msg:
                body += f"{msg.replace('• ', '🌟 ')}\n"

    try:
        if ANNOUNCEMENT_CHAT_ID:
            await context.bot.send_message(
                chat_id=ANNOUNCEMENT_CHAT_ID,
                message_thread_id=ANNOUNCEMENT_THREAD_ID,
                text=f"{title}\n\n{body}",
                parse_mode="HTML"
            )
    except: pass

async def broadcast_boss_announcement(application, location_key: str, forced_media_id: str = None):
    location_name = (game_data.REGIONS_DATA.get(location_key) or {}).get("display_name", location_key)
    
    # Busca o ID da mídia (Seja vídeo ou foto)
    media_id = forced_media_id
    if not media_id:
        try:
            file_ids.refresh_cache()
            media_id = file_ids.get_file_id("boss_raid")
        except: pass

    anuncio = f"🚨 𝐀𝐋𝐄𝐑𝐓𝐀 𝐆𝐋𝐎𝐁𝐀𝐋 🚨\nᴜᴍ ᴅᴇᴍôɴɪᴏ ᴅɪᴍᴇɴsɪᴏɴᴀʟ sᴜʀɢɪᴜ ᴇᴍ {location_name}!\n\nᴄʟɪǫᴜᴇ ᴀʙᴀɪxᴏ ᴘᴀʀᴀ ᴠɪᴀᴊᴀʀ!"
    keyboard = [[InlineKeyboardButton("🗺️ 𝔸𝔹ℝ𝕀ℝ 𝕄𝔸ℙ𝔸 𝔻𝔼 𝕍𝕀𝔸𝔾𝔼𝕄 🗺️", callback_data="travel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    count = 0
    
    # --- CORREÇÃO AQUI ---
    # Usamos 'pdata' para achar o Chat ID real do Telegram
    async for _oid, pdata in player_manager.iter_players():
        try:
            # Tenta pegar o ID numérico do Telegram
            target_chat_id = pdata.get("last_chat_id")
            if not target_chat_id:
                target_chat_id = pdata.get("telegram_id_owner")
            
            # Se não tiver ID numérico, pula (não dá pra mandar msg pra ObjectId)
            if not target_chat_id:
                continue
                
            chat_id_int = int(target_chat_id)
            sent = False
            
            # Se tivermos um ID de mídia, começamos a "Cascata Inteligente"
            if media_id:
                # 1ª Tentativa: VÍDEO
                try:
                    await application.bot.send_video(
                        chat_id=chat_id_int, 
                        video=media_id, 
                        caption=anuncio, 
                        parse_mode='HTML', 
                        reply_markup=reply_markup
                    )
                    sent = True
                except Exception:
                    # 2ª Tentativa: FOTO
                    try:
                        await application.bot.send_photo(
                            chat_id=chat_id_int, 
                            photo=media_id, 
                            caption=anuncio, 
                            parse_mode='HTML', 
                            reply_markup=reply_markup
                        )
                        sent = True
                    except Exception:
                        pass
            
            # 3ª Tentativa (Fallback): TEXTO PURO
            if not sent:
                await application.bot.send_message(
                    chat_id=chat_id_int, 
                    text=anuncio, 
                    parse_mode='HTML', 
                    reply_markup=reply_markup
                )
            
            # Anti-Flood leve
            count += 1
            if count % 20 == 0: await asyncio.sleep(1)
            else: await asyncio.sleep(0.05) 

        except Exception as e:
            # Se o usuário bloqueou o bot, ignora
            continue

async def end_world_boss_job(context: ContextTypes.DEFAULT_TYPE):
    battle_results = world_boss_manager.end_event(reason="Tempo esgotado")
    await distribute_loot_and_announce(context, battle_results)
    async for user_id, _ in player_manager.iter_players():
        try: await context.bot.send_message(chat_id=user_id, text="⏳ 𝗧𝗲𝗺𝗽𝗼 𝗘𝘀𝗴𝗼𝘁𝗮𝗱𝗼! 𝗕𝗼𝘀𝘀 𝘀𝘂𝗺𝗶𝘂.")
        except: pass

async def iniciar_world_boss_job(context: ContextTypes.DEFAULT_TYPE):
    if world_boss_manager.is_active: return
    res = world_boss_manager.start_event()
    if res.get("success"):
        await broadcast_boss_announcement(context.application, res["location"])
        hours = context.job.data.get("duration_hours", 1) if context.job.data else 1
        context.job_queue.run_once(end_world_boss_job, when=timedelta(hours=hours))