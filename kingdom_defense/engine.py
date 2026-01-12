# Arquivo: kingdom_defense/engine.py
# (VERSÃO ZERO-TOLERANCE: IDs STRINGS OBRIGATÓRIOS)

import random
import logging
from typing import Optional, Dict, Any
from telegram.ext import ContextTypes
from .data import WAVE_DEFINITIONS
from modules import player_manager
from modules.player import stats as player_stats_engine
from . import leaderboard
from modules.combat import criticals
from modules.game_data import items as game_items
from modules.game_data.monsters import MONSTERS_DATA
from modules.game_data.skills import SKILL_DATA 
from modules.combat import combat_engine

logger = logging.getLogger(__name__)

# =============================================================================
# HELPER: Raridade de Skills
# =============================================================================
def _get_player_skill_data_by_rarity(pdata: dict, skill_id: str) -> dict | None:
    """Busca os dados da skill e ajusta o CUSTO DE MANA baseado na classe."""
    base_skill = SKILL_DATA.get(skill_id)
    if not base_skill: return None

    merged_data = base_skill.copy()
    
    if "rarity_effects" in base_skill:
        player_skills = pdata.get("skills", {})
        rarity = "comum"
        if isinstance(player_skills, dict):
            player_skill_instance = player_skills.get(skill_id)
            if player_skill_instance:
                rarity = player_skill_instance.get("rarity", "comum")
        
        rarity_data = base_skill["rarity_effects"].get(rarity, base_skill["rarity_effects"].get("comum", {}))
        merged_data.update(rarity_data)
    
    player_class = (pdata.get("class_key") or pdata.get("class") or "").lower()
    high_mana_classes = ["mago", "feiticeiro", "elementalista", "arquimago"]
    
    if player_class in high_mana_classes:
        original_cost = merged_data.get("mana_cost", 0)
        new_cost = int(original_cost * 2.0) 
        merged_data["mana_cost"] = new_cost

    return merged_data

def _find_monster_template(mob_id: str) -> dict | None:
    if not mob_id: return None
    for region_monsters in MONSTERS_DATA.values():
        for monster in region_monsters:
            if monster.get("id") == mob_id:
                return monster.copy()
    return None

class KingdomDefenseManager:
    def __init__(self):
        self.wave_definitions = WAVE_DEFINITIONS
        self.is_active = False
        self.reset_event()

    async def start_event(self):
        if self.is_active: return {"error": "O evento já está ativo."}
        self.reset_event()
        self.is_active = True
        await self.setup_wave(1) 
        logger.info("Evento de Defesa do Reino iniciado na Onda 1.")
        return {"success": "Evento iniciado!"}
    
    def store_player_message_id(self, user_id: str, message_id: int):
        """Armazena o message_id da batalha para um jogador."""
        # Garante string
        uid = str(user_id)
        if uid in self.player_states:
            self.player_states[uid]['message_id'] = message_id
        else:
            logger.warning(f"Tentativa de armazenar message_id para {uid} sem estado de batalha.")

    async def end_event(self, context: ContextTypes.DEFAULT_TYPE | None = None):
        logger.info("Encerrando evento de Defesa do Reino...")
        top_scorer = None
        max_damage = 0
        
        all_participants = list(self.active_fighters) + self.waiting_queue
        
        for user_id in all_participants:
            # user_id já é string aqui
            state = self.player_states.get(user_id)
            if not state: continue

            try:
                player_data = await player_manager.get_player_data(user_id)
                if player_data:
                    player_data["player_state"] = {"action": "idle"}
                    await player_manager.save_player_data(user_id, player_data)
                    
                    damage_dealt = state.get('damage_dealt', 0)
                    if damage_dealt > max_damage:
                        max_damage = damage_dealt
                        top_scorer = {
                            "user_id": user_id,
                            "character_name": player_data.get("character_name", "Herói"),
                            "damage": max_damage
                        }
                    
                    if context:
                        try:
                            # Tenta notificar (user_id é string, mas telegram aceita se for numérico valido)
                            await context.bot.send_message(chat_id=user_id, text="⚔️ O evento de Defesa do Reino foi encerrado! ⚔️")
                        except Exception:
                            pass 
                        
            except Exception as e:
                logger.error(f"Erro ao finalizar evento para {user_id}: {e}")

        if top_scorer:
            leaderboard.update_top_score(
                user_id=str(top_scorer["user_id"]),
                character_name=top_scorer["character_name"],
                damage=top_scorer["damage"]
            )
            
        self.reset_event()
        return {"success": "Evento encerrado."}

    def reset_event(self):
        self.is_active = False
        self.current_wave = 0
        self.boss_mode_active = False
        self.boss_global_hp = 0
        self.boss_max_hp = 0
        self.active_fighters = set() # Set de strings
        self.waiting_queue = []      # Lista de strings
        self.player_states = {}      # Dict {str: dict}
        self.current_wave_mob_pool = []
        self.total_mobs_in_wave = 0
        self.max_concurrent_fighters = 10
        self.boss_attack_counter = 0

    async def start_event_at_wave(self, wave_number: int):
        if self.is_active: return {"error": "O evento já está ativo."}
        if wave_number not in self.wave_definitions: return {"error": f"A Onda {wave_number} não existe."}
        self.reset_event()
        self.is_active = True
        await self.setup_wave(wave_number)
        return {"success": f"Evento de teste iniciado na Onda {wave_number}!"}
    
    async def setup_wave(self, wave_number: int):
        if wave_number not in self.wave_definitions:
            await self.end_event()
            return 

        self.current_wave = wave_number
        self.boss_mode_active = False
        limite_base = 5
        vagas_por_onda = 5
        self.max_concurrent_fighters = limite_base + (vagas_por_onda * self.current_wave)
        if self.max_concurrent_fighters > 50:
            self.max_concurrent_fighters = 50

        wave_data = self.wave_definitions[wave_number]
        self.current_wave_mob_pool = wave_data.get('mob_pool', []).copy()
        self.total_mobs_in_wave = len(self.current_wave_mob_pool)

    def get_player_status(self, user_id: str):
        uid = str(user_id)
        if uid in self.active_fighters: return "active"
        if uid in self.waiting_queue: return "waiting"
        return "not_in_event"

    async def add_player_to_event(self, user_id: str, player_data: dict):
        uid = str(user_id)
        if not self.is_active:
            return "event_inactive"
        status = self.get_player_status(uid)
        if status != "not_in_event": return status
        
        if len(self.active_fighters) < self.max_concurrent_fighters:
            self.active_fighters.add(uid)
            await self._setup_player_battle_state(uid, player_data) 
            return "active"
        else:
            if uid not in self.waiting_queue:
                self.waiting_queue.append(uid)
            return "waiting"

    async def _setup_player_battle_state(self, user_id: str, player_data: dict):
        uid = str(user_id)
        total_stats = await player_manager.get_player_total_stats(player_data) 
        current_wave_info = self.wave_definitions[self.current_wave]
        
        mob_template = None
        if not self.boss_mode_active:
            if not self.current_wave_mob_pool:
                if self.total_mobs_in_wave > 0:
                     return
            else:
                mob_id = self.current_wave_mob_pool[0] 
                mob_template = _find_monster_template(mob_id)
        else:
            boss_id = current_wave_info.get('boss_id')
            mob_template = _find_monster_template(boss_id)
            
        if not mob_template:
            return

        mob_instance = mob_template.copy()
        mob_instance['active_effects'] = []
        if self.boss_mode_active:
            mob_instance.update({'hp': self.boss_global_hp, 'max_hp': self.boss_max_hp, 'is_boss': True})
        else:
            mob_instance.update({'max_hp': mob_instance['hp'], 'is_boss': False})

        max_hp = int(total_stats.get('max_hp', 100))
        if uid in self.player_states and self.player_states[uid].get('player_hp', 0) > 0:
            previous_hp = self.player_states[uid]['player_hp']
            current_hp = min(previous_hp, max_hp) 
        else:
            db_hp = player_data.get('current_hp')
            if db_hp is None: db_hp = player_data.get('hp')
            current_hp = int(db_hp) if db_hp is not None else max_hp
            
        current_hp = min(current_hp, max_hp)

        max_mp = int(total_stats.get('max_mana', 50))
        
        if uid in self.player_states:
             current_mp = self.player_states[uid].get('player_mp', max_mp)
        else:
             db_mp = player_data.get('current_mp')
             if db_mp is None: db_mp = player_data.get('mana')
             current_mp = int(db_mp) if db_mp is not None else max_mp
        
        current_mp = min(current_mp, max_mp)

        current_damage = self.player_states.get(uid, {}).get('damage_dealt', 0)
        current_message_id = self.player_states.get(uid, {}).get('message_id', None)
        saved_cooldowns = self.player_states.get(uid, {}).get('skill_cooldowns', {})

        self.player_states[uid] = {
            'player_hp': current_hp,
            'player_max_hp': max_hp,
            'player_mp': current_mp,
            'player_max_mp': max_mp,
            'current_mob': mob_instance,
            'damage_dealt': current_damage,
            'active_effects': [],
            'message_id': current_message_id,
            'skill_cooldowns': saved_cooldowns
        }

    async def process_player_attack(self, user_id: str, player_data: dict, player_full_stats: dict):
        uid = str(user_id)
        if uid not in self.active_fighters:
            return {"error": "Você não está em uma batalha ativa."}

        player_state = self.player_states[uid]
        mob = player_state['current_mob']
        is_boss_fight = mob.get('is_boss', False)

        attacker_stats = self._get_stats_with_effects(player_full_stats, player_state.get('active_effects', []))
        target_stats = self._get_stats_with_effects(mob, mob.get('active_effects', []))

        try:
            result = await combat_engine.processar_acao_combate(
                attacker_pdata=player_data,
                attacker_stats=attacker_stats,
                target_stats=target_stats,
                skill_id=None,
                attacker_current_hp=player_state.get('player_hp')
            )
        except Exception as e:
            logger.error(f"Erro no combat_engine: {e}")
            return {"error": "Erro ao calcular dano."}

        final_damage = result.get("total_damage", 0)
        logs = result.get("log_messages", [])
        
        player_state['damage_dealt'] += final_damage

        if is_boss_fight:
            self.boss_global_hp = max(0, self.boss_global_hp - final_damage)
        else:
            mob['hp'] = max(0, mob['hp'] - final_damage)

        return await self._resolve_turn(uid, player_data, logs)
    
    async def _promote_next_player(self):
        if self.waiting_queue and len(self.active_fighters) < self.max_concurrent_fighters:
            next_player_id = str(self.waiting_queue.pop(0)) # Garante string
            player_data = await player_manager.get_player_data(next_player_id)
            if player_data:
                self.active_fighters.add(next_player_id)
                await self._setup_player_battle_state(next_player_id, player_data) 
                logger.info(f"Jogador {next_player_id} promovido da fila.")
            else:
                logger.warning(f"Jogador {next_player_id} na fila mas sem data.")

    async def _resolve_turn(self, user_id: str, player_data: dict, logs: list) -> dict:
        uid = str(user_id)
        player_state = self.player_states[uid]
        mob = player_state['current_mob']
        is_boss_fight = mob.get('is_boss', False)
        player_full_stats = await player_manager.get_player_total_stats(player_data)
        mob_hp = self.boss_global_hp if is_boss_fight else mob['hp']
        loot_msg = ""

        # --- MONSTRO DERROTADO ---
        if mob_hp <= 0:
            logs.append(f"☠️ {mob['name']} foi derrotado!")
        
            from modules.cooldowns import iniciar_turno 
            player_data, msgs_cd = iniciar_turno(player_data)
            if msgs_cd: logs.extend(msgs_cd)
        
            player_state['player_hp'] = player_data.get('current_hp')
            player_state['player_mp'] = player_data.get('current_mp')
            await player_manager.save_player_data(uid, player_data)

            if is_boss_fight:
                logs.append(f"🎉 A ONDA {self.current_wave} FOI CONCLUÍDA! 🎉")
                await self.setup_wave(self.current_wave + 1)
                
                if not self.is_active:
                    return {"event_over": True, "action_log": "\n".join(logs)}
                
                await self._setup_player_battle_state(uid, player_data)
                await player_manager.save_player_data(uid, player_data)
                
                return {
                    "monster_defeated": True, 
                    "action_log": "\n".join(logs), 
                    "loot_message": f"🌊 Inciando Onda {self.current_wave}!"
                }
            
            else:
                drops = []
                item_id = 'fragmento_bravura'
                player_manager.add_item_to_inventory(player_data, item_id, 1)
                item_info = game_items.ITEMS_DATA.get(item_id, {})
                item_name = item_info.get('display_name', 'Fragmento de Bravura')
                drops.append(f"1x {item_name}")
            
                if random.random() < 0.01:
                    novo_item_id = 'sigilo_protecao' 
                    player_manager.add_item_to_inventory(player_data, novo_item_id, 1)
                    novo_item_info = game_items.ITEMS_DATA.get(novo_item_id, {})
                    novo_item_name = novo_item_info.get('display_name', novo_item_id)
                    drops.append(f"1x {novo_item_name} (Raro!)")
            
                loot_msg = f"💎 𝐋𝐨𝐨𝐭: {', '.join(drops)}" 
                logs.append(loot_msg) 
            
                if self.current_wave_mob_pool:
                    self.current_wave_mob_pool.pop(0)

                if not self.boss_mode_active and not self.current_wave_mob_pool:
                    self.boss_mode_active = True
                    boss_id = self.wave_definitions[self.current_wave].get("boss_id")
                    boss_template = _find_monster_template(boss_id) if boss_id else {}
                
                    num_participantes = len(self.player_states)
                    hp_base = boss_template.get("hp", 500)
                    escala_base = 40
                    hp_extra = escala_base * self.current_wave * num_participantes
                
                    self.boss_max_hp = int(hp_base + hp_extra)
                    self.boss_global_hp = self.boss_max_hp
                
                    boss_name = boss_template.get("name", "Chefe")
                    logs.append(f"\n🚨 <b>{boss_name}</b> APARECEU COM {self.boss_global_hp:,} HP! 🚨")

            if uid in self.player_states:
                await self._setup_player_battle_state(uid, player_data)
                await player_manager.save_player_data(uid, player_data) 

                return {
                    "monster_defeated": True, 
                    "action_log": "\n".join(logs), 
                    "loot_message": loot_msg 
                }
            else:
                return {
                    "event_over": True, 
                    "action_log": "\n".join(logs)
                }

        # --- MONSTRO VIVO ---
        else:
            if is_boss_fight:
                self.boss_attack_counter += 1
        
            special_attack_data = mob.get("special_attack")

            # AOE
            if is_boss_fight and special_attack_data and special_attack_data.get("is_aoe") and self.boss_attack_counter % 3 == 0:
                logs.append(f"👑 <b>{special_attack_data['name']}</b> (Em Área!)")
                aoe_results = []
            
                for fighter_id in list(self.active_fighters):
                    # fighter_id é string
                    f_state = self.player_states.get(fighter_id)
                    f_data = await player_manager.get_player_data(fighter_id)
                    if not f_state or not f_data: continue
                
                    f_stats = await player_manager.get_player_total_stats(f_data)
                    base_dmg, _, _ = criticals.roll_damage(mob, f_stats, {})
                    final_dmg = int(base_dmg * special_attack_data.get("damage_multiplier", 1.0))
                
                    f_state['player_hp'] = max(0, f_state['player_hp'] - final_dmg)
                
                    logs.append(f"🔥 {f_data.get('character_name','Herói')} sofreu {final_dmg}!")
                
                    was_defeated = f_state['player_hp'] <= 0
                    aoe_results.append({"user_id": fighter_id, "was_defeated": was_defeated})
                
                    if was_defeated:
                        self.active_fighters.remove(fighter_id)
                        await self._promote_next_player()
                
                    f_data['current_hp'] = f_state['player_hp']
                    f_data['mana'] = f_state['player_mp']
                    f_data['current_mp'] = f_state['player_mp']
                    await player_manager.save_player_data(fighter_id, f_data)
            
                return { "monster_defeated": False, "action_log": "\n".join(logs), "aoe_results": aoe_results }

            # Single Target
            else:
                dodge_chance = await player_stats_engine.get_player_dodge_chance(player_data)
                if random.random() < dodge_chance:
                    logs.append(f"💨 Você se esquivou do ataque!")
                else:
                    mob_damage, mob_is_crit, mob_is_mega = criticals.roll_damage(mob, player_full_stats, {})
                
                    if is_boss_fight and special_attack_data and not special_attack_data.get("is_aoe") and self.boss_attack_counter % 3 == 0:
                        mob_damage = int(mob_damage * special_attack_data.get("damage_multiplier", 1.0))
                        logs.append(f"👑 <b>{special_attack_data['name']}!</b>")
                
                    player_state['player_hp'] = max(0, player_state['player_hp'] - mob_damage)
                
                    if mob_is_mega: logs.append(f"‼️ <b>MEGA CRÍTICO!</b> Recebeu {mob_damage} de dano!")
                    elif mob_is_crit: logs.append(f"❗️ <b>CRÍTICO!</b> Recebeu {mob_damage} de dano!")
                    else: logs.append(f"🩸 Recebeu {mob_damage} de dano.")

                if player_state['player_hp'] <= 0:
                    logs.append("\n💀 <b>VOCÊ FOI DERROTADO!</b>")
                    self.active_fighters.remove(uid)
                    await self._promote_next_player()
                
                    player_data['current_hp'] = 1 
                    player_data['player_state'] = {"action": "idle"}
                    await player_manager.save_player_data(uid, player_data)
                
                    return { "game_over": True, "action_log": "\n".join(logs) }

                from modules.cooldowns import iniciar_turno 
                player_data, msgs_cd = iniciar_turno(player_data)
                player_state['player_hp'] = player_data.get('current_hp')
                player_state['player_mp'] = player_data.get('current_mp')
                logs.extend(msgs_cd)
                await player_manager.save_player_data(uid, player_data)

                return { "monster_defeated": False, "game_over": False, "action_log": "\n".join(logs) }

    async def process_player_skill(self, user_id: str, player_data: dict, skill_id: str, target_id: str | None = None):
        uid = str(user_id)
        if uid not in self.active_fighters:
            return {"error": "Você não está em uma batalha ativa."}

        player_state = self.player_states[uid]
        
        from modules.cooldowns import verificar_cooldown
        pode_usar, msg_cd = verificar_cooldown(player_data, skill_id)
        if not pode_usar:
            return {"error": msg_cd}

        skill_info = _get_player_skill_data_by_rarity(player_data, skill_id)
        if not skill_info: return {"error": "Habilidade desconhecida."}

        mana_cost = skill_info.get("mana_cost", 0)
        current_mp = player_state.get('player_mp', 0)
        
        if current_mp < mana_cost:
            return {"error": f"Mana insuficiente! ({current_mp}/{mana_cost})"}
        
        player_state['player_mp'] -= mana_cost
        player_data['current_mp'] = player_state['player_mp']
        player_data['mana'] = player_state['player_mp'] 
        await player_manager.save_player_data(uid, player_data)
        
        logs = [f"Você usa {skill_info['display_name']}! (-{mana_cost} MP)"]

        from modules.cooldowns import aplicar_cooldown
        rarity = player_data.get("skills", {}).get(skill_id, {}).get("rarity", "comum")
        player_data = aplicar_cooldown(player_data, skill_id, rarity)

        skill_type = skill_info.get("type")
        skill_effects = skill_info.get("effects", {})
        mob = player_state['current_mob']
        is_boss_fight = mob.get('is_boss', False)
        
        if skill_type == "active": 
            player_full_stats = await player_manager.get_player_total_stats(player_data)
            attacker_stats = self._get_stats_with_effects(player_full_stats, player_state.get('active_effects', []))
            target_stats = self._get_stats_with_effects(mob, mob.get('active_effects', []))
            
            result = await combat_engine.processar_acao_combate(
                attacker_pdata=player_data, 
                attacker_stats=attacker_stats, 
                target_stats=target_stats, 
                skill_id=skill_id, 
                attacker_current_hp=player_state.get('player_hp')
            )

            final_damage = result["total_damage"]
            logs.extend(result["log_messages"])
            player_state['damage_dealt'] += final_damage
            
            if is_boss_fight: self.boss_global_hp = max(0, self.boss_global_hp - final_damage)
            else: mob['hp'] = max(0, mob['hp'] - final_damage)

            if "debuff_target" in skill_effects:
                debuff = skill_effects["debuff_target"]
                mob.setdefault('active_effects', []).append({"stat": debuff["stat"], "multiplier": debuff["value"], "turns_left": debuff["duration_turns"]})
                logs.append(f"🛡️ Defesa inimiga reduzida!")
            
        elif skill_type == "support": 
            heal_applied = False
            player_full_stats = await player_manager.get_player_total_stats(player_data)

            if "party_heal" in skill_effects:
                heal_def = skill_effects["party_heal"]
                heal_amount = 0
                if "amount_percent_max_hp" in heal_def:
                    heal_amount = int(player_full_stats.get('max_hp', 1) * heal_def["amount_percent_max_hp"])
                elif heal_def.get("heal_type") == "magic_attack":
                    m_atk = player_full_stats.get('magic_attack', player_full_stats.get('attack', 0))
                    heal_amount = int(m_atk * heal_def.get("heal_scale", 1.0))
                
                if heal_amount > 0:
                    for ally_id in list(self.active_fighters):
                        ally_state = self.player_states.get(ally_id)
                        if ally_state:
                            ally_state['player_hp'] = min(ally_state['player_max_hp'], ally_state['player_hp'] + heal_amount)
                            heal_applied = True
                    if heal_applied: logs.append(f"✨ Grupo curado em {heal_amount} HP!")
            
            if not heal_applied:
                logs.append("🎶 Efeitos de suporte ativados!")

            return { "monster_defeated": False, "action_log": "\n".join(logs), "skip_monster_turn": True }
        
        return await self._resolve_turn(uid, player_data, logs)

    def get_battle_data(self, user_id: str):
        uid = str(user_id)
        if uid not in self.player_states: return None
        player_state_copy = self.player_states[uid].copy()
        player_state_copy['current_wave'] = self.current_wave
        if player_state_copy['current_mob'].get('is_boss'):
            player_state_copy['current_mob']['hp'] = self.boss_global_hp
        return player_state_copy

    def get_queue_status_text(self):
        wave_info = self.wave_definitions.get(self.current_wave)
        if not wave_info or not self.is_active:
            return "O evento não está ativo no momento."
        status_line = ""
        if self.boss_mode_active and self.boss_max_hp > 0:
            percent_hp = (self.boss_global_hp / self.boss_max_hp) * 100
            status_line = f"Vida do Chefe: {self.boss_global_hp:,}/{self.boss_max_hp:,} ({percent_hp:.1f}%)"
        else:
            mobs_derrotados = self.total_mobs_in_wave - len(self.current_wave_mob_pool)
            total_mobs = self.total_mobs_in_wave
            status_line = f"Progresso da Onda {self.current_wave}: {mobs_derrotados}/{total_mobs}"
        return (
            f"{status_line}\n"
            f"Defensores Ativos: {len(self.active_fighters)}/{self.max_concurrent_fighters}\n"
            f"Heróis na Fila: {len(self.waiting_queue)}"
        )
    
    def _get_stats_with_effects(self, base_stats: dict, active_effects: list) -> dict:
        modified_stats = base_stats.copy()

        for effect in active_effects:
            stat_to_modify = effect.get("stat")
            multiplier = effect.get("multiplier", 0.0)
        
            if stat_to_modify in modified_stats:
                bonus_value = modified_stats[stat_to_modify] * multiplier
                modified_stats[stat_to_modify] += int(bonus_value)

        return modified_stats
    
    def _tick_effects(self, user_id: str):
        uid = str(user_id)
        player_state = self.player_states.get(uid)
        if not player_state: return

        if player_state.get('active_effects'):
            player_updated_effects = []
            for effect in player_state['active_effects']:
                effect['turns_left'] -= 1
                if effect['turns_left'] > 0:
                    player_updated_effects.append(effect)
            player_state['active_effects'] = player_updated_effects

        mob = player_state.get('current_mob')
        if mob and mob.get('active_effects'):
            mob_updated_effects = []
            for effect in mob['active_effects']:
                effect['turns_left'] -= 1
                if effect['turns_left'] > 0:
                    mob_updated_effects.append(effect)
            mob['active_effects'] = mob_updated_effects

    async def get_leaderboard_text(self) -> str:
        all_participants_ids = set(self.active_fighters) | set(self.player_states.keys())
        if not all_participants_ids: return "Nenhum herói participou do evento ainda."
        leaderboard_data = []
        for user_id in all_participants_ids:
            # user_id é string
            state = self.player_states.get(user_id)
            player_data = await player_manager.get_player_data(user_id)
            if state and player_data and state.get('damage_dealt', 0) > 0:
                leaderboard_data.append({
                    "name": player_data.get('character_name', 'Herói'),
                    "damage": state.get('damage_dealt', 0)
                })
        if not leaderboard_data: return "Ninguém causou dano ainda."
        sorted_participants = sorted(leaderboard_data, key=lambda i: i['damage'], reverse=True)
        lines = ["🏆 **Ranking de Dano do Evento** 🏆\n"]
        for i, status in enumerate(sorted_participants[:5]):
            medal = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, "🔹")
            lines.append(f"{medal} {status['name']}: {status['damage']:,} de dano")
        return "\n".join(lines)

# --- INSTÂNCIA ÚNICA ---
event_manager = KingdomDefenseManager()

async def start_event_job(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Job agendado: Ativando o evento de defesa do reino...")
    await event_manager.start_event()

async def end_event_job(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Job agendado: Encerrando o evento de defesa do reino...")
    await event_manager.end_event(context)