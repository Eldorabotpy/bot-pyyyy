# modules/world_boss/engine.py (VERSÃO FINAL: TRINDADE + SMART HEAL + PERSISTÊNCIA)

import json
import os
import random
import logging
import asyncio
import html
from datetime import datetime, timedelta
from telegram.ext import ContextTypes
from telegram.error import Forbidden, TelegramError

from modules import player_manager, game_data
from modules.combat import criticals
from modules.player import stats as player_stats_engine
from modules import file_ids
# Importa dados de Skill e Skins
from modules.game_data.skills import SKILL_DATA
from modules.game_data.skins import SKIN_CATALOG

logger = logging.getLogger(__name__)

# --- CONFIGURAÇÕES ---
BOSS_STATE_FILE = "world_boss_state.json"
ANNOUNCEMENT_CHAT_ID = -1002881364171
ANNOUNCEMENT_THREAD_ID = 24

POSSIBLE_LOCATIONS = [
    "pradaria_inicial", "floresta_sombria", "pedreira_granito",
    "campos_linho", "pico_grifo", "mina_ferro",
    "forja_abandonada", "pantano_maldito"
]

# Configurações Iniciais do Evento
INITIAL_STATE = {
    "is_active": False,
    "location": None,
    "start_time": None,
    "environment_hazard": False, 
    "entities": {
        "boss": {
            "name": "Demônio Dimensional",
            "max_hp": 50000,
            "hp": 50000,
            "alive": True,
            "stats": {"attack": 150, "defense": 80, "luck": 50, "initiative": 50}
        },
        "witch_heal": {
            "name": "Bruxa do Tormento (Cura)",
            "max_hp": 15000,
            "hp": 15000,
            "alive": True,
            "stats": {"attack": 80, "defense": 40, "luck": 30, "initiative": 30}
        },
        "witch_buff": {
            "name": "Bruxa da Ruína (Buff)",
            "max_hp": 15000,
            "hp": 15000,
            "alive": True,
            "stats": {"attack": 80, "defense": 40, "luck": 30, "initiative": 30}
        }
    },
    "damage_leaderboard": {}, # {user_id_str: dano_total}
    "last_hitter_id": None
}

# Loot Tables
SKILL_REWARD_POOL = [
    "guerreiro_corte_perfurante", "guerreiro_colossal_defense", 
    "guerreiro_bencao_sagrada", "guerreiro_redemoinho_aco",
    "berserker_golpe_selvagem", "berserker_golpe_divino_da_ira", 
    "berserker_ultimo_recurso", "berserker_investida_inquebravel",
    "cacador_flecha_precisa", "active_ricochet_arrow", 
    "passive_apex_predator", "active_deadeye_shot",
    "monge_rajada_de_punhos", "active_thunder_palm", 
    "active_transcendence", "passive_elemental_strikes",
    "mago_bola_de_fogo", "active_arcane_ward", 
    "active_meteor_swarm", "passive_elemental_attunement", 
    "bardo_melodia_restauradora", "passive_perfect_pitch",
    "passive_symphony_of_power", "active_dissonant_melody",
    "assassino_ataque_furtivo","active_guillotine_strike",
    "active_dance_of_a_thousand_cuts", "passive_potent_toxins",
    "samurai_corte_iaijutsu","passive_iai_stance",
    "active_parry_and_riposte","active_banner_of_command"
]
SKILL_CHANCE = 4.0 # 4%

SKIN_REWARD_POOL = [
    'guerreiro_armadura_negra', 'guerreiro_placas_douradas',
    'mago_traje_arcano', 'mago_arquimago_caos', 'assassino_manto_espectral',
    'cacador_patrulheiro_elfico', 'cacador_cacador_dragoes', 'berserker_pele_urso',
    'berserker_infernal', 'monge_quimono_dragao', 'monge_aspecto_asura', 'bardo_traje_maestro',
    'bardo_requiem_sombrio', 'samurai_armadura_shogun', 'samurai_armadura_demoniaca'
]
SKIN_CHANCE = 2.0 # 2%

LOOT_REWARD_POOL = [
    ("pocao_cura_media", 3, 5),
    ("pedra_do_aprimoramento", 3, 5),
    ("gems", 1, 1),
    ("pergaminho_durabilidade", 5, 10),
    ("cristal_de_abertura", 5, 10),
    ("frasco_sabedoria", 2, 4),
    ("sigilo_protecao", 1, 2)
]
LOOT_CHANCE = 30.0 # 30% de chance de ganhar algo dessa lista

class WorldBossManager:
    def __init__(self):
        self.state = self.load_state()

    def load_state(self):
        """Carrega o estado do arquivo JSON para sobreviver a restarts."""
        if os.path.exists(BOSS_STATE_FILE):
            try:
                with open(BOSS_STATE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "entities" not in data: return INITIAL_STATE.copy()
                    return data
            except Exception as e:
                logger.error(f"Erro ao carregar World Boss: {e}")
                return INITIAL_STATE.copy()
        return INITIAL_STATE.copy()

    def save_state(self):
        """Salva o estado atual no disco."""
        try:
            with open(BOSS_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Erro ao salvar World Boss: {e}")

    def start_event(self):
        if self.state["is_active"]:
            return {"error": "O evento já está ativo."}
        
        # Reinicia o estado
        self.state = INITIAL_STATE.copy() # Reset total
        self.state["is_active"] = True
        self.state["location"] = random.choice(POSSIBLE_LOCATIONS)
        self.state["start_time"] = datetime.now().isoformat()
        
        # Randomiza um pouco os HPs para variar a dificuldade
        hp_mult = random.uniform(0.9, 1.2)
        for key in self.state["entities"]:
            base = self.state["entities"][key]["max_hp"]
            new_hp = int(base * hp_mult)
            self.state["entities"][key]["max_hp"] = new_hp
            self.state["entities"][key]["hp"] = new_hp

        self.save_state()
        logger.info(f"WB START: {self.state['location']}")
        return {"success": True, "location": self.state["location"]}

    def end_event(self, reason: str):
        if not self.state["is_active"]: return {}
        
        results = {
            "leaderboard": self.state["damage_leaderboard"].copy(),
            "last_hitter_id": self.state["last_hitter_id"],
            "boss_defeated": (reason == "Boss derrotado")
        }
        
        # Reset lógico
        self.state["is_active"] = False
        self.save_state()
        
        # Limpa o arquivo
        if os.path.exists(BOSS_STATE_FILE):
            os.remove(BOSS_STATE_FILE)
            
        return results

    # =========================================================================
    # --- HELPER: TRIAGEM INTELIGENTE (Smart Triage) ---
    # =========================================================================
    async def _get_most_injured_player(self):
        """Retorna o (user_id, player_data, cur_hp, max_hp) do jogador com menor % de vida."""
        most_injured = None
        lowest_pct = 1.1

        # Varre participantes (limitado a 50 para performance)
        active_ids = list(self.state["damage_leaderboard"].keys())
        random.shuffle(active_ids) # Randomiza para não curar sempre o mesmo se houver empate
        
        check_ids = active_ids[:50] 

        for uid_str in check_ids:
            try:
                uid = int(uid_str)
                pdata = await player_manager.get_player_data(uid)
                if not pdata: continue
                
                # Stats básicos (sem chamar calculation pesada)
                max_hp = pdata.get("base_stats", {}).get("max_hp", 100)
                # Se tiver buffs salvos, o max_hp pode ser maior, mas vamos usar o base para ser rápido
                cur_hp = pdata.get("current_hp", max_hp)
                
                if cur_hp >= max_hp: continue 
                
                pct = cur_hp / max_hp
                if pct < lowest_pct:
                    lowest_pct = pct
                    most_injured = (uid, pdata, cur_hp, max_hp)
            except: continue
        
        return most_injured

    # =========================================================================
    # --- HELPER: CURA EM MASSA (Mass Heal / AoE) ---
    # =========================================================================
    async def _perform_mass_heal(self, healer_id, heal_amount, max_targets=15):
        """Cura múltiplos aliados em paralelo."""
        candidate_ids = [int(uid) for uid in self.state["damage_leaderboard"].keys() if int(uid) != healer_id]
        if not candidate_ids: return 0, 0

        random.shuffle(candidate_ids)
        targets = candidate_ids[:max_targets]
        
        count_healed = 0
        total_restored = 0
        
        async def _heal_single(target_id):
            nonlocal count_healed, total_restored
            try:
                pdata = await player_manager.get_player_data(target_id)
                if not pdata: return
                
                max_hp = pdata.get("base_stats", {}).get("max_hp", 100)
                # Ajuste de segurança se o HP atual for maior que o base (devido a buffs)
                if pdata.get("current_hp", 0) > max_hp: max_hp = pdata["current_hp"]
                
                current = pdata.get("current_hp", max_hp)
                if current < max_hp:
                    new_val = min(max_hp, current + heal_amount)
                    diff = new_val - current
                    if diff > 0:
                        pdata["current_hp"] = new_val
                        await player_manager.save_player_data(target_id, pdata)
                        return diff
            except: pass
            return 0

        # Executa em paralelo
        results = await asyncio.gather(*[_heal_single(uid) for uid in targets])
        
        for res in results:
            if res and res > 0:
                count_healed += 1
                total_restored += res
                
        return count_healed, total_restored

    # =========================================================================
    # --- MOTOR DE AÇÃO PRINCIPAL ---
    # =========================================================================
    async def perform_action(self, user_id: int, player_data: dict, action_type: str, target_key: str = None, skill_id: str = None):
        """
        Action Types: 'attack', 'heal_ally', 'defend_ally'
        """
        if not self.state["is_active"]:
            return {"error": "Evento encerrado."}
        
        if player_data.get("current_location") != self.state["location"]:
            return {"error": "Você precisa estar no local do evento para agir."}

        log_msgs = []
        player_stats = await player_manager.get_player_total_stats(player_data)

        # ---------------------------------------------------------------------
        # 1. AÇÃO: SUPORTE (CURA)
        # ---------------------------------------------------------------------
        if action_type == 'heal_ally':
            # Verifica se é AoE (Bardo) ou Single Target
            is_aoe = False
            heal_base_scale = 2.5
            
            if skill_id:
                skill_data = SKILL_DATA.get(skill_id, {})
                effects = skill_data.get("rarity_effects", {}).get("comum", {}).get("effects", {})
                if "party_heal" in effects:
                    is_aoe = True
                    heal_base_scale = effects["party_heal"].get("heal_scale", 1.5)
            
            magic_atk = player_stats.get('magic_attack', 10)
            heal_amount = int(magic_atk * heal_base_scale)

            # >> MODO CURA EM MASSA (AoE) <<
            if is_aoe:
                count, total = await self._perform_mass_heal(user_id, heal_amount)
                if count > 0:
                    # Score no leaderboard (Cura conta como dano/contribuição)
                    self.state["damage_leaderboard"][str(user_id)] = self.state["damage_leaderboard"].get(str(user_id), 0) + total
                    
                    log_msgs.append(f"🎵 <b>MELODIA RESTAURADORA!</b>")
                    log_msgs.append(f"Sua música alcançou <b>{count} aliados</b>, restaurando um total de <b>{total} HP</b>!")
                else:
                    log_msgs.append("🎵 Você tocou sua música, mas todos parecem saudáveis.")
                
                return {"success": True, "log": "\n".join(log_msgs)}

            # >> MODO CURA ÚNICA (Smart Triage) <<
            else:
                target_info = await self._get_most_injured_player()
                if not target_info:
                    return {"log": "✅ <b>Todos os aliados visíveis estão saudáveis!</b>"}
                
                t_id, t_data, t_cur, t_max = target_info
                
                # Bônus percentual na cura single target
                bonus_heal = int(t_max * 0.05)
                final_heal = heal_amount + bonus_heal
                
                new_hp = min(t_max, t_cur + final_heal)
                real_healed = new_hp - t_cur
                
                t_data["current_hp"] = new_hp
                await player_manager.save_player_data(t_id, t_data)
                
                # Score
                self.state["damage_leaderboard"][str(user_id)] = self.state["damage_leaderboard"].get(str(user_id), 0) + real_healed

                t_name = html.escape(t_data.get("character_name", "Aliado"))
                pct_before = int((t_cur / t_max) * 100)
                pct_after = int((new_hp / t_max) * 100)
                
                log_msgs.append(f"💚 <b>CURA SALVADORA!</b>")
                log_msgs.append(f"Você socorreu <b>{t_name}</b> ({pct_before}%) restaurando <b>{real_healed} HP</b>!")
                log_msgs.append(f"O aliado agora está com {pct_after}% de vida.")
                
                return {"success": True, "log": "\n".join(log_msgs)}

        # ---------------------------------------------------------------------
        # 2. AÇÃO: SUPORTE (DEFESA)
        # ---------------------------------------------------------------------
        if action_type == 'defend_ally':
            # Tank limpa hazards (chão de fogo/meteoros)
            if self.state["environment_hazard"]:
                self.state["environment_hazard"] = False
                log_msgs.append(f"🛡️ <b>INTERCEPTAÇÃO!</b> Você se lançou à frente e protegeu o grupo da Chuva de Meteoros!")
            else:
                log_msgs.append(f"🛡️ Você ergueu seu escudo! A moral do grupo aumentou.")
            return {"success": True, "log": "\n".join(log_msgs)}

        # ---------------------------------------------------------------------
        # 3. AÇÃO: ATAQUE
        # ---------------------------------------------------------------------
        target_entity = self.state["entities"].get(target_key)
        if not target_entity or not target_entity["alive"]:
            return {"error": "Alvo inválido ou já derrotado."}

        # Verifica Escudo das Bruxas
        witches_alive = self.state["entities"]["witch_heal"]["alive"] or self.state["entities"]["witch_buff"]["alive"]
        damage_reduction = 0.90 if (target_key == "boss" and witches_alive) else 0.0

        skill_effects = {}
        # (Futuro: extrair dados da skill_id se passado)

        # Rola o dano
        dmg, is_crit, is_mega = criticals.roll_damage(player_stats, target_entity["stats"], skill_effects)
        
        # Redução do Escudo
        if damage_reduction > 0:
            dmg = int(dmg * (1.0 - damage_reduction))
            log_msgs.append("🛡️ <b>O Escudo das Bruxas absorveu 90% do dano!</b>")

        dmg = max(1, dmg)
        target_entity["hp"] -= dmg
        self.state["damage_leaderboard"][str(user_id)] = self.state["damage_leaderboard"].get(str(user_id), 0) + dmg
        self.state["last_hitter_id"] = user_id
        
        hit_icon = "💥" if is_crit else "⚔️"
        log_msgs.append(f"{hit_icon} Você causou <b>{dmg}</b> de dano em {target_entity['name']}.")

        # Morte do Mob
        if target_entity["hp"] <= 0:
            target_entity["hp"] = 0
            target_entity["alive"] = False
            log_msgs.append(f"💀 <b>{target_entity['name']} FOI DERROTADO!</b>")
            
            if target_key == "boss":
                res = self.end_event("Boss derrotado")
                return {"boss_defeated": True, "log": "\n".join(log_msgs), "battle_results": res}

        # IA dos Mobs (Reação)
        await self._mob_ai_turn(user_id, log_msgs)
        
        self.save_state()
        return {"success": True, "log": "\n".join(log_msgs)}

    async def _mob_ai_turn(self, user_id, log_msgs):
        """IA simples para os mobs reagirem."""
        # 1. Bruxa Healer
        witch_heal = self.state["entities"]["witch_heal"]
        if witch_heal["alive"] and random.random() < 0.15: # 15% chance
            heal = int(witch_heal["max_hp"] * 0.05)
            # Cura quem tiver menos vida entre os mobs
            targets = [e for e in self.state["entities"].values() if e["alive"] and e["hp"] < e["max_hp"]]
            if targets:
                t = random.choice(targets)
                t["hp"] = min(t["max_hp"], t["hp"] + heal)
                log_msgs.append(f"🧙‍♀️ {witch_heal['name']} curou {t['name']} em {heal} HP!")

        # 2. Boss AoE
        boss = self.state["entities"]["boss"]
        if boss["alive"]:
            # Dano passivo se tiver hazard
            if self.state["environment_hazard"]:
                log_msgs.append("🔥 <b>O solo em chamas queima você!</b> (Dano Ambiental)")
            
            # Chance de ativar Hazard
            if random.random() < 0.10 and not self.state["environment_hazard"]:
                self.state["environment_hazard"] = True
                log_msgs.append("☄️ <b>O Demônio invoca uma Chuva de Meteoros! O campo está perigoso!</b>")

    # =========================================================================
    # --- VISUAL HUD (ASYNC para buscar nomes) ---
    # =========================================================================
    async def get_battle_hud(self) -> str:
        def _bar(cur, max_v, length=8):
            pct = cur / max_v
            filled = int(pct * length)
            return "█" * filled + "░" * (length - filled)

        ents = self.state["entities"]
        
        # Boss Display
        boss = ents["boss"]
        boss_status = "🛡️ PROTEGIDO" if (ents["witch_heal"]["alive"] or ents["witch_buff"]["alive"]) else "🔥 VULNERÁVEL"
        if not boss["alive"]: boss_status = "💀 MORTO"
        
        txt = f"👹 <b>{boss['name']}</b>\n"
        txt += f"HP: `{_bar(boss['hp'], boss['max_hp'])}` {boss['hp']}/{boss['max_hp']} ({boss_status})\n\n"
        
        # Witches Display
        w1 = ents["witch_heal"]
        w1_icon = "💀" if not w1["alive"] else "🧙‍♀️"
        txt += f"{w1_icon} <b>{w1['name']}</b>: `{_bar(w1['hp'], w1['max_hp'], 6)}`\n"
        
        w2 = ents["witch_buff"]
        w2_icon = "💀" if not w2["alive"] else "🧙"
        txt += f"{w2_icon} <b>{w2['name']}</b>: `{_bar(w2['hp'], w2['max_hp'], 6)}`\n"

        if self.state["environment_hazard"]:
            txt += "\n⚠️ <b>ALERTA:</b> Chuva de Meteoros ativa! Tanks, usem [Proteger]!\n"

        # --- SEÇÃO DE ALERTA MÉDICO (Quem está morrendo?) ---
        txt += "\n" + ("-"*20) + "\n"
        
        critical_names = []
        check_ids = list(self.state["damage_leaderboard"].keys())
        # Ordena por quem bateu mais (geralmente os ativos), pega top 20 para checar vida
        # (Idealmente ordenaria por timestamp de ultima ação, mas leaderboard serve de proxy)
        sorted_ids = sorted(check_ids, key=lambda x: self.state["damage_leaderboard"][x], reverse=True)[:20]

        for uid in sorted_ids:
            try:
                p = await player_manager.get_player_data(int(uid))
                if not p: continue
                
                cur = p.get("current_hp", 100)
                max_h = p.get("base_stats", {}).get("max_hp", 100)
                
                if cur < (max_h * 0.30): # Menos de 30% HP
                    name = p.get("character_name", "Herói").split()[0]
                    pct_val = int((cur/max_h)*100)
                    critical_names.append(f"{name} ({pct_val}%)")
                    if len(critical_names) >= 3: break 
            except: continue

        if critical_names:
            txt += f"🚨 <b>PERIGO CRÍTICO:</b> " + ", ".join(critical_names)
        else:
            txt += "✅ Grupo Estável"

        return txt

# Instância Global
world_boss_manager = WorldBossManager()

# ======================================================
# --- FUNÇÕES DE LOOT E ANÚNCIO (RESTAURADO) ---
# ======================================================

async def _send_dm_to_winner(context: ContextTypes.DEFAULT_TYPE, user_id: int, loot_messages: list[str]):
    if not loot_messages: return
    loot_str = "\n".join([f"• {item}" for item in loot_messages])
    message = (
        f"🎉 <b>Recompensas do Demônio Dimensional</b> 🎉\n\n"
        f"Parabéns! Por sua bravura na batalha, você recebeu:\n{loot_str}"
    )
    try:
        await context.bot.send_message(chat_id=user_id, text=message, parse_mode='HTML')
        await asyncio.sleep(0.1) 
        return True
    except (Forbidden, TelegramError):
        return False

async def distribute_loot_and_announce(context: ContextTypes.DEFAULT_TYPE, battle_results: dict):
    """Distribui loot e anuncia resultados."""
    leaderboard = battle_results.get("leaderboard", {})
    last_hitter_id = battle_results.get("last_hitter_id")
    boss_defeated = battle_results.get("boss_defeated", False)

    if not leaderboard: return

    # Carrega dados dos participantes
    participant_data = {}
    for user_id_str in leaderboard.keys():
        try:
            uid = int(user_id_str)
            pdata = await player_manager.get_player_data(uid)
            if pdata: participant_data[uid] = pdata
        except Exception: pass
    
    if not participant_data: return

    # Listas para o anúncio global
    skill_winners_msg = []
    skin_winners_msg = []
    loot_winners_count = 0 # Para não flodar o chat global com poções
    last_hit_msg = ""
    
    # Monta Top 3
    sorted_ranking = sorted(leaderboard.items(), key=lambda item: item[1], reverse=True)
    top_3_msg = []
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid_str, dmg) in enumerate(sorted_ranking[:3]):
        uid = int(uid_str)
        pdata = participant_data.get(uid)
        name = html.escape(pdata.get('character_name', 'Herói')) if pdata else "Herói Desconhecido"
        medal = medals[i] if i < 3 else "🏅"
        top_3_msg.append(f"{medal} {name} ({dmg:,} pts)")

    # === DISTRIBUIÇÃO ===
    for user_id, pdata in participant_data.items():
        if leaderboard.get(str(user_id), 0) <= 0: continue
        
        try:
            player_name = pdata.get("character_name", f"ID {user_id}")
            loot_won_messages = [] # Mensagens privadas para o jogador
            player_mudou = False

            # 1. Roll SKILL (5%)
            if random.random() * 100 <= SKILL_CHANCE:
                won_skill_id = random.choice(SKILL_REWARD_POOL)
                won_item_id = f"tomo_{won_skill_id}" 
                item_info = game_data.ITEMS_DATA.get(won_item_id) or {}
                display_name = item_info.get("display_name", won_skill_id)
                
                player_manager.add_item_to_inventory(pdata, won_item_id, 1)
                loot_won_messages.append(f"📚 <b>SKILL RARA:</b> {display_name}")
                skill_winners_msg.append(f"• {html.escape(player_name)} obteve <b>{display_name}</b>!")
                player_mudou = True

            # 2. Roll SKIN (2%)
            if random.random() * 100 <= SKIN_CHANCE:
                won_skin_id = random.choice(SKIN_REWARD_POOL)
                won_item_id = f"caixa_{won_skin_id}"
                item_info = game_data.ITEMS_DATA.get(won_item_id) or {}
                display_name = item_info.get("display_name", won_skin_id)
                
                player_manager.add_item_to_inventory(pdata, won_item_id, 1)
                loot_won_messages.append(f"🎨 <b>SKIN LENDÁRIA:</b> {display_name}")
                skin_winners_msg.append(f"• {html.escape(player_name)} obteve <b>{display_name}</b>!")
                player_mudou = True

            # 3. Roll LOOT COMUM (50%) - NOVO!
            if random.random() * 100 <= LOOT_CHANCE:
                # Escolhe um item da lista
                loot_choice = random.choice(LOOT_REWARD_POOL)
                
                # Verifica se é tupla ("item", min, max) ou só string "item"
                if isinstance(loot_choice, tuple):
                    l_id = loot_choice[0]
                    l_qty = random.randint(loot_choice[1], loot_choice[2])
                else:
                    l_id = loot_choice
                    l_qty = 1
                
                # Adiciona ao inventário
                player_manager.add_item_to_inventory(pdata, l_id, l_qty)
                
                # Pega nome bonito
                i_info = game_data.ITEMS_DATA.get(l_id, {})
                i_name = i_info.get("display_name", l_id.replace("_", " ").title())
                i_emoji = i_info.get("emoji", "📦")
                
                loot_won_messages.append(f"{i_emoji} <b>Loot:</b> {l_qty}x {i_name}")
                loot_winners_count += 1
                player_mudou = True

            # Salva Player
            if player_mudou:
                await player_manager.save_player_data(user_id, pdata)
            
            # Envia DM com resumo do que ele ganhou
            if loot_won_messages:
                await _send_dm_to_winner(context, user_id, loot_won_messages)

            # Checa Last Hit
            if user_id == last_hitter_id:
                last_hit_msg = f"💥 <b>Último Golpe:</b> {html.escape(player_name)}"

        except Exception as e:
            logger.error(f"[WB_LOOT] Erro no player {user_id}: {e}")

    # === ANÚNCIO NO CANAL ===
    if not boss_defeated:
        title = "👹 <b>O Demônio Dimensional Escapou!</b> 👹"
        body = "O monstro era muito poderoso e retirou-se.\n\nMais sorte da próxima vez!"
    else:
        title = "🎉 <b>O Demônio Dimensional Foi Derrotado!</b> 🎉"
        body = "A ameaça foi contida!\n\n<b>Ranking de Contribuição (Top 3):</b>\n" + "\n".join(top_3_msg)
        
        if last_hit_msg: body += f"\n{last_hit_msg}"
        
        # Lista Skins e Skills (Itens raros merecem destaque)
        if skin_winners_msg: body += "\n\n🎨 <b>Skins Encontradas:</b>\n" + "\n".join(skin_winners_msg)
        if skill_winners_msg: body += "\n\n✨ <b>Skills Encontradas:</b>\n" + "\n".join(skill_winners_msg)
        
        # Apenas menciona quantos ganharam loot comum, pra não poluir
        if loot_winners_count > 0:
            body += f"\n\n📦 <b>{loot_winners_count} guerreiros</b> receberam espólios de guerra (Poções/Materiais)."

    try:
        await context.bot.send_message(
            chat_id=ANNOUNCEMENT_CHAT_ID,
            message_thread_id=ANNOUNCEMENT_THREAD_ID,
            text=f"{title}\n\n{body}",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Erro ao enviar anúncio no canal: {e}")

async def broadcast_boss_announcement(application, location_key: str):
    """Anuncia início para todos com IMAGEM (se houver)."""
    location_name = (game_data.REGIONS_DATA.get(location_key) or {}).get("display_name", location_key)
    
    # Pega o ID da imagem
    media_id = file_ids.get_file_id("boss_raid")
    
    anuncio = f"🚨 **ALERTA GLOBAL** 🚨\nUm Demônio Dimensional surgiu em <b>{location_name}</b>!\n\nUse /worldboss para ajudar na defesa!"
    
    async for user_id, _ in player_manager.iter_players():
        try:
            if media_id:
                await application.bot.send_photo(chat_id=user_id, photo=media_id, caption=anuncio, parse_mode='HTML')
            else:
                await application.bot.send_message(chat_id=user_id, text=anuncio, parse_mode='HTML')
            
            await asyncio.sleep(0.05) 
        except: continue