# Arquivo: kingdom_defense/engine.py (VERSÃO COM A NOVA FUNÇÃO DE SKILL)

import random
import logging
from telegram.ext import ContextTypes
from .data import WAVE_DEFINITIONS
from modules import player_manager
from modules.player import stats as player_stats_engine
from . import leaderboard
from modules.combat import criticals
from modules.game_data import items as game_items
from modules.game_data.monsters import MONSTERS_DATA
from modules.game_data.skills import SKILL_DATA # Importa o banco de dados de skills

logger = logging.getLogger(__name__)

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

    def start_event(self):
        if self.is_active: return {"error": "O evento já está ativo."}
        self.reset_event()
        self.is_active = True
        self.setup_wave(1) 
        return {"success": "Evento iniciado!"}
    
    def end_event(self):
        logger.info("Encerrando evento de Defesa do Reino...")
        top_scorer = None
        max_damage = 0
        for user_id_str, state in self.player_states.items():
            user_id = int(user_id_str)
            if state.get('damage_dealt', 0) > max_damage:
                max_damage = state['damage_dealt']
                player_data = player_manager.get_player_data(user_id)
                if player_data:
                    top_scorer = {
                        "user_id": user_id,
                        "character_name": player_data.get("character_name", "Herói"),
                        "damage": max_damage
                    }
        if top_scorer:
            leaderboard.update_top_score(
                user_id=top_scorer["user_id"],
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
        self.active_fighters = set()
        self.waiting_queue = []
        self.player_states = {}
        self.current_wave_mob_pool = []
        self.total_mobs_in_wave = 0
        self.max_concurrent_fighters = 10
        self.boss_attack_counter = 0

    def start_event_at_wave(self, wave_number: int):
        if self.is_active: return {"error": "O evento já está ativo."}
        if wave_number not in self.wave_definitions: return {"error": f"A Onda {wave_number} não existe."}
        logger.info(f"Iniciando evento de teste na Onda {wave_number}.")
        self.reset_event()
        self.is_active = True
        self.setup_wave(wave_number)
        return {"success": f"Evento de teste iniciado na Onda {wave_number}!"}
    
    def setup_wave(self, wave_number: int):
        if wave_number not in self.wave_definitions:
            self.end_event()
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

    def get_player_status(self, user_id):
        if user_id in self.active_fighters: return "active"
        if user_id in self.waiting_queue: return "waiting"
        return "not_in_event"

    def add_player_to_event(self, user_id, player_data):
        if not self.is_active:
            logger.warning(f"Jogador {user_id} tentou entrar em um evento inativo.")
            return "event_inactive"
        status = self.get_player_status(user_id)
        if status != "not_in_event": return status
        if len(self.active_fighters) < self.max_concurrent_fighters:
            self.active_fighters.add(user_id)
            self._setup_player_battle_state(user_id, player_data)
            return "active"
        else:
            if user_id not in self.waiting_queue:
                self.waiting_queue.append(user_id)
            return "waiting"

    def _setup_player_battle_state(self, user_id, player_data):
        total_stats = player_manager.get_player_total_stats(player_data)
        current_wave_info = self.wave_definitions[self.current_wave]
        mob_template = None
        if not self.boss_mode_active:
            if not self.current_wave_mob_pool:
                logger.error(f"Tentativa de buscar monstro em um baralho vazio na onda {self.current_wave}.")
                return
            mob_id = self.current_wave_mob_pool.pop(0)
            mob_template = _find_monster_template(mob_id)
        else:
            boss_id = current_wave_info.get('boss_id')
            mob_template = _find_monster_template(boss_id)
        if not mob_template:
            logger.error(f"ERRO CRÍTICO: Não foi possível encontrar os dados do monstro para a onda {self.current_wave}.")
            return
        mob_instance = mob_template.copy()
        mob_instance['active_effects'] = []
        if self.boss_mode_active:
            mob_instance.update({'hp': self.boss_global_hp, 'max_hp': self.boss_max_hp, 'is_boss': True})
        else:
            mob_instance.update({'max_hp': mob_instance['hp'], 'is_boss': False})
        current_hp = total_stats.get('max_hp', 100)
        if user_id in self.player_states and 'player_hp' in self.player_states[user_id]:
            current_hp = self.player_states[user_id]['player_hp']
        current_damage = self.player_states.get(user_id, {}).get('damage_dealt', 0)
        self.player_states[user_id] = {
            'player_hp': current_hp,
            'player_max_hp': total_stats.get('max_hp', 100),
            'current_mob': mob_instance,
            'damage_dealt': current_damage,
            'active_effects': []
        }
        logger.info(f"Jogador {user_id} configurado para lutar contra {mob_instance['name']} com {current_hp} de HP.")

    def _promote_next_player(self):
        if self.waiting_queue and len(self.active_fighters) < self.max_concurrent_fighters:
            next_player_id = self.waiting_queue.pop(0)
            player_data = player_manager.get_player_data(next_player_id)
            if player_data:
                self.active_fighters.add(next_player_id)
                self._setup_player_battle_state(next_player_id, player_data)
                logger.info(f"Jogador {next_player_id} promovido da fila para a batalha.")

    def _resolve_turn(self, user_id: int, player_data: dict, logs: list) -> dict:
        player_state = self.player_states[user_id]
        mob = player_state['current_mob']
        is_boss_fight = mob.get('is_boss', False)
        player_full_stats = player_manager.get_player_total_stats(player_data)

        mob_hp = self.boss_global_hp if is_boss_fight else mob['hp']
        mob_is_defeated = mob_hp <= 0

        if mob_is_defeated:
            logs.append(f"☠️ {mob['name']} foi derrotado!")
            if is_boss_fight:
                logs.append(f"🎉 A ONDA {self.current_wave} FOI CONCLUÍDA! 🎉")
                self.setup_wave(self.current_wave + 1)
                if self.current_wave not in self.wave_definitions:
                    self.end_event()
                    return {"event_over": True, "action_log": "\n".join(logs)}
            else:
                reward_amount, item_id = 1, 'fragmento_bravura'
                player_manager.add_item_to_inventory(player_data, item_id, reward_amount)
                item_info = game_items.ITEMS_DATA.get(item_id, {})
                item_name = item_info.get('display_name', item_id)
                loot_message = f"Você recebeu {reward_amount}x {item_name}!"
                if not self.boss_mode_active and not self.current_wave_mob_pool:
                    self.boss_mode_active = True
                    boss_id = self.wave_definitions[self.current_wave].get("boss_id")
                    boss_template = _find_monster_template(boss_id) if boss_id else {}
                    num_participantes, hp_base = len(self.player_states), boss_template.get("hp", 500)
                    escala_base_por_jogador, hp_por_jogador = 40, escala_base_por_jogador * self.current_wave
                    self.boss_max_hp = int(hp_base + (hp_por_jogador * num_participantes))
                    self.boss_global_hp = self.boss_max_hp
                    boss_name = boss_template.get("name", "Chefe Desconhecido")
                    logs.append(f"🚨 O CHEFE, {boss_name}, APARECEU COM {self.boss_global_hp:,} DE HP! 🚨")

            self._setup_player_battle_state(user_id, player_data)
            player_manager.save_player_data(user_id, player_data)
            return {
                "monster_defeated": True, "action_log": "\n".join(logs),
                "loot_message": loot_message if 'loot_message' in locals() else "",
                "next_mob_data": self.player_states[user_id]['current_mob']
            }
        
        else: # Se o monstro não foi derrotado, ele contra-ataca
            if is_boss_fight: self.boss_attack_counter += 1
            special_attack_data = mob.get("special_attack")

            if is_boss_fight and special_attack_data and special_attack_data.get("is_aoe") and self.boss_attack_counter % 3 == 0:
                logs.append(f"👑 <b>ATAQUE EM ÁREA: {special_attack_data['name']}</b> 👑")
                logs.append(f"<i>{special_attack_data['log_text']}</i>")
                aoe_results = []
                for fighter_id in list(self.active_fighters):
                    fighter_state, fighter_data = self.player_states.get(fighter_id), player_manager.get_player_data(fighter_id)
                    if not fighter_state or not fighter_data: continue
                    fighter_full_stats = player_manager.get_player_total_stats(fighter_data)
                    damage_to_fighter, _, _ = criticals.roll_damage(mob, fighter_full_stats, {})
                    final_damage = int(damage_to_fighter * special_attack_data.get("damage_multiplier", 1.0))
                    fighter_state['player_hp'] -= final_damage
                    logs.append(f"🩸 {fighter_data.get('character_name', 'Herói')} sofre {final_damage} de dano!")
                    was_defeated = fighter_state['player_hp'] <= 0
                    aoe_results.append({"user_id": fighter_id, "was_defeated": was_defeated})
                    if was_defeated:
                        self.active_fighters.remove(fighter_id)
                        self._promote_next_player()
                return { "monster_defeated": False, "action_log": "\n".join(logs), "aoe_results": aoe_results }
            
            else: # Ataque de alvo único (normal ou especial)
                dodge_chance = player_stats_engine.get_player_dodge_chance(player_data)
                if random.random() < dodge_chance:
                    logs.append(f"💨 Você se esquivou do ataque de {mob['name']}!")
                else:
                    mob_damage, mob_is_crit, mob_is_mega = criticals.roll_damage(mob, player_full_stats, {})
                    if is_boss_fight and special_attack_data and self.boss_attack_counter % 3 == 0:
                        mob_damage = int(mob_damage * special_attack_data.get("damage_multiplier", 1.0))
                        logs.append(f"👑 <b>ATAQUE ESPECIAL: {special_attack_data['name']}</b> 👑")
                        logs.append(f"<i>{special_attack_data['log_text']}</i>")
                        logs.append(f"🩸 Você sofre um golpe massivo, recebendo {mob_damage} de dano!")
                    else:
                        logs.append(f"🩸 {mob['name']} contra-ataca, causando {mob_damage} de dano!")
                        if mob_is_mega: logs.append("‼️ MEGA CRÍTICO inimigo!")
                        elif mob_is_crit: logs.append("❗️ DANO CRÍTICO inimigo!")
                    player_state['player_hp'] -= mob_damage

            if player_state['player_hp'] <= 0:
                logs.append("\nVOCÊ FOI DERROTADO!")
                self.active_fighters.remove(user_id)
                self._promote_next_player()
                return { "game_over": True, "action_log": "\n".join(logs) }
            
            player_manager.save_player_data(user_id, player_data)
            return { "monster_defeated": False, "action_log": "\n".join(logs) }

    def process_player_attack(self, user_id, player_data):
        """Calcula o dano do ataque básico de um jogador e passa para a resolução do turno."""
        self._tick_effects(user_id)

        if not self.is_active or user_id not in self.active_fighters:
            return {"error": "Você não está em uma batalha ativa."}
    
        player_state = self.player_states[user_id]
        mob = player_state['current_mob']
        is_boss_fight = mob.get('is_boss', False)
        player_full_stats = player_manager.get_player_total_stats(player_data)
        logs, num_attacks = [], 1

        attacker_combat_stats = self._get_stats_with_effects(
            player_full_stats, 
            player_state.get('active_effects', [])
        )

        if random.random() < player_stats_engine.get_player_double_attack_chance(player_data):
            num_attacks = 2
            logs.append("⚡ Ataque Duplo!")

        for _ in range(num_attacks):
            # Aplica debuffs no alvo antes de calcular o dano
            target_combat_stats = self._get_stats_with_effects(mob, mob.get('active_effects', []))
        
            # --- CORREÇÃO: A LINHA ABAIXO ESTAVA FALTANDO ---
            # Ela calcula o dano e cria as variáveis damage, is_crit, e is_mega
            damage, is_crit, is_mega = criticals.roll_damage(attacker_combat_stats, target_combat_stats, {})
        
            logs.append(f"Você ataca {mob['name']} e causa {damage} de dano.")
            if is_mega: logs.append("💥💥 MEGA CRÍTICO!")
            elif is_crit: logs.append("💥 DANO CRÍTICO!")
        
            player_state['damage_dealt'] += damage
            if is_boss_fight: 
                self.boss_global_hp -= damage
            else: 
                mob['hp'] -= damage
        
            mob_hp = self.boss_global_hp if is_boss_fight else mob['hp']
            if mob_hp <= 0: 
                break
    
        # Chama a função auxiliar para resolver o resto do turno
        return self._resolve_turn(user_id, player_data, logs)

    def _resolve_turn(self, user_id: int, player_data: dict, logs: list) -> dict:
        """
        Função auxiliar que resolve o final de um turno após o jogador causar dano.
        Verifica a derrota do monstro e, se não, executa o contra-ataque.
        """
        player_state = self.player_states[user_id]
        mob = player_state['current_mob']
        is_boss_fight = mob.get('is_boss', False)
        player_full_stats = player_manager.get_player_total_stats(player_data)

        mob_hp = self.boss_global_hp if is_boss_fight else mob['hp']
        mob_is_defeated = mob_hp <= 0

        if mob_is_defeated:
            logs.append(f"☠️ {mob['name']} foi derrotado!")
            if is_boss_fight:
                logs.append(f"🎉 A ONDA {self.current_wave} FOI CONCLUÍDA! 🎉")
                self.setup_wave(self.current_wave + 1)
                if self.current_wave not in self.wave_definitions:
                    self.end_event()
                    return {"event_over": True, "action_log": "\n".join(logs)}
            else:
                reward_amount = 1
                item_id = 'fragmento_bravura'
                player_manager.add_item_to_inventory(player_data, item_id, reward_amount)
                item_info = game_items.ITEMS_DATA.get(item_id, {})
                item_name = item_info.get('display_name', item_id)
                loot_message = f"Você recebeu {reward_amount}x {item_name}!"
                if not self.boss_mode_active and not self.current_wave_mob_pool:
                    self.boss_mode_active = True
                    boss_id = self.wave_definitions[self.current_wave].get("boss_id")
                    boss_template = _find_monster_template(boss_id) if boss_id else {}
                    num_participantes = len(self.player_states)
                    hp_base = boss_template.get("hp", 500)
                    escala_base_por_jogador = 40 
                    hp_por_jogador = escala_base_por_jogador * self.current_wave
                    self.boss_max_hp = int(hp_base + (hp_por_jogador * num_participantes))
                    self.boss_global_hp = self.boss_max_hp
                    boss_name = boss_template.get("name", "Chefe Desconhecido")
                    logs.append(f"🚨 TODOS OS MONSTROS FORAM DERROTADOS! O CHEFE, {boss_name}, APARECEU COM {self.boss_global_hp:,} DE HP! 🚨")

            self._setup_player_battle_state(user_id, player_data)
            player_manager.save_player_data(user_id, player_data)
            return {
                "monster_defeated": True, "action_log": "\n".join(logs),
                "loot_message": loot_message if 'loot_message' in locals() else "",
                "next_mob_data": self.player_states[user_id]['current_mob']
            }
    
        else: # Se o monstro não foi derrotado, ele contra-ataca
            if is_boss_fight:
                self.boss_attack_counter += 1
            special_attack_data = mob.get("special_attack")

            if is_boss_fight and special_attack_data and special_attack_data.get("is_aoe") and self.boss_attack_counter % 3 == 0:
                logs.append(f"👑 <b>ATAQUE EM ÁREA: {special_attack_data['name']}</b> 👑")
                logs.append(f"<i>{special_attack_data['log_text']}</i>")
                aoe_results = []
                for fighter_id in list(self.active_fighters):
                    fighter_state = self.player_states.get(fighter_id)
                    fighter_data = player_manager.get_player_data(fighter_id)
                    if not fighter_state or not fighter_data: continue
                    fighter_full_stats = player_manager.get_player_total_stats(fighter_data)
                    damage_to_fighter, _, _ = criticals.roll_damage(mob, fighter_full_stats, {})
                    final_damage = int(damage_to_fighter * special_attack_data.get("damage_multiplier", 1.0))
                    fighter_state['player_hp'] -= final_damage
                    logs.append(f"🩸 {fighter_data.get('character_name', 'Herói')} sofre {final_damage} de dano!")
                    was_defeated = fighter_state['player_hp'] <= 0
                    aoe_results.append({"user_id": fighter_id, "was_defeated": was_defeated})
                    if was_defeated:
                        self.active_fighters.remove(fighter_id)
                        self._promote_next_player()
                return { "monster_defeated": False, "action_log": "\n".join(logs), "aoe_results": aoe_results }
        
            else: # Ataque de alvo único (normal ou especial)
                dodge_chance = player_stats_engine.get_player_dodge_chance(player_data)
                if random.random() < dodge_chance:
                    logs.append(f"💨 Você se esquivou do ataque de {mob['name']}!")
                else:
                    mob_damage, mob_is_crit, mob_is_mega = criticals.roll_damage(mob, player_full_stats, {})
                    if is_boss_fight and special_attack_data and self.boss_attack_counter % 3 == 0:
                        mob_damage = int(mob_damage * special_attack_data.get("damage_multiplier", 1.0))
                        logs.append(f"👑 <b>ATAQUE ESPECIAL: {special_attack_data['name']}</b> 👑")
                        logs.append(f"<i>{special_attack_data['log_text']}</i>")
                        logs.append(f"🩸 Você sofre um golpe massivo, recebendo {mob_damage} de dano!")
                    else:
                        logs.append(f"🩸 {mob['name']} contra-ataca, causando {mob_damage} de dano!")
                        if mob_is_mega: logs.append("‼️ MEGA CRÍTICO inimigo!")
                        elif mob_is_crit: logs.append("❗️ DANO CRÍTICO inimigo!")
                    player_state['player_hp'] -= mob_damage

            if player_state['player_hp'] <= 0:
                logs.append("\nVOCÊ FOI DERROTADO!")
                self.active_fighters.remove(user_id)
                self._promote_next_player()
                return { "game_over": True, "action_log": "\n".join(logs) }
        
            player_manager.save_player_data(user_id, player_data)
            return { "monster_defeated": False, "action_log": "\n".join(logs) }

    def process_player_skill(self, user_id, player_data, skill_id, target_id=None):
        # CORREÇÃO: Adicionada a contagem regressiva dos efeitos no início do turno
        self._tick_effects(user_id)

        if user_id not in self.active_fighters:
            return {"error": "Você não está em uma batalha ativa."}

        skill_info = SKILL_DATA.get(skill_id)
        if not skill_info: return {"error": "Habilidade desconhecida."}

        player_state = self.player_states[user_id]
        mob = player_state['current_mob']
        is_boss_fight = mob.get('is_boss', False)
        player_full_stats = player_manager.get_player_total_stats(player_data)
        logs = []

        mana_cost = skill_info.get("mana_cost", 0)
        if player_data.get("mana", 0) < mana_cost:
            return {"error": f"Mana insuficiente! ({player_data.get('mana', 0)}/{mana_cost})"}
    
        player_data["mana"] -= mana_cost
        logs.append(f"Você usa {skill_info['display_name']}! (-{mana_cost} MP)")

        skill_type = skill_info.get("type")

        # --- LÓGICA DE EXECUÇÃO DA SKILL ---
        if skill_type == "attack":
            attacker_combat_stats = self._get_stats_with_effects(player_full_stats, player_state.get('active_effects', []))
            target_combat_stats = self._get_stats_with_effects(mob, mob.get('active_effects', []))
        
            # --- CORREÇÃO: A LINHA ABAIXO ESTAVA FALTANDO ---
            damage, is_crit, is_mega = criticals.roll_damage(attacker_combat_stats, target_combat_stats, {})
        
            damage_multiplier = skill_info.get("effects", {}).get("damage_multiplier", 1.0)
            final_damage = int(damage * damage_multiplier)
            logs.append(f"Sua habilidade causa {final_damage} de dano!")
            if is_mega: logs.append("💥💥 MEGA CRÍTICO!")
            elif is_crit: logs.append("💥 DANO CRÍTICO!")
        
            if is_boss_fight: self.boss_global_hp -= final_damage
            else: mob['hp'] -= final_damage
            player_state['damage_dealt'] += final_damage

            # --- CORREÇÃO: LÓGICA DE DEBUFF MOVIDA PARA DENTRO DO BLOCO DE ATAQUE ---
            skill_effects = skill_info.get("effects", {})
            if "debuff_target" in skill_effects:
                debuff_info = skill_effects["debuff_target"]
                mob.get('active_effects', []).append({
                    "stat": debuff_info["stat"],
                    "multiplier": debuff_info["value"],
                    "turns_left": debuff_info["duration_turns"]
                })
                logs.append(f"🛡️ A defesa de {mob['name']} foi reduzida!")

        elif skill_type == "support_heal":
            heal_target_id = target_id if skill_info.get("target") == "single" else user_id
            target_state = self.player_states.get(heal_target_id)
            target_data = player_manager.get_player_data(heal_target_id)
            if target_state and target_data:
                max_hp = player_manager.get_player_total_stats(target_data).get('max_hp', 1)
                current_hp = target_state.get('player_hp', 0)
                healed_for = min(skill_info.get("heal_amount", 0), max_hp - current_hp)
                if healed_for > 0:
                    target_state['player_hp'] += healed_for
                    logs.append(f"✨ {target_data.get('character_name', 'Aliado')} foi curado em {healed_for} HP!")
                else:
                    logs.append("O alvo já está com a vida cheia!")
    
        elif skill_type == "support_buff":
            buff_info = skill_info.get("buff")
            if buff_info:
                target_state = self.player_states.get(user_id)
                if target_state:
                    target_state['active_effects'].append({
                        "stat": buff_info["stat"],
                        "multiplier": buff_info["multiplier"],
                        "turns_left": buff_info["duration"]
                    })
                    logs.append(f"🛡️ Você se sente mais forte! ({skill_info['display_name']})")

        # --- DECISÃO DE FIM DE TURNO ---
        if skill_type.startswith("support"):
            player_manager.save_player_data(user_id, player_data)
            return { "monster_defeated": False, "action_log": "\n".join(logs) }
    
        # Se a skill foi de ataque, a lógica de fim de turno (vitória ou contra-ataque) continua
        return self._resolve_turn(user_id, player_data, logs)

    def get_battle_data(self, user_id):
        if user_id not in self.player_states: return None
        player_state_copy = self.player_states[user_id].copy()
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
        """
        Pega os atributos base de um combatente e aplica os bônus ou penalidades de
        todos os efeitos ativos (buffs/debuffs) para o turno atual.
        """
        modified_stats = base_stats.copy()

        for effect in active_effects:
            stat_to_modify = effect.get("stat")
            multiplier = effect.get("multiplier", 0.0)
        
            if stat_to_modify in modified_stats:
                bonus_value = modified_stats[stat_to_modify] * multiplier
            
                # Adiciona o valor ao atributo. Multiplicadores negativos (debuffs) funcionarão corretamente.
                modified_stats[stat_to_modify] += int(bonus_value)

        return modified_stats
    
    def _tick_effects(self, user_id: int):
        """Reduz a duração dos efeitos ativos do jogador E do seu oponente."""
        player_state = self.player_states.get(user_id)
        if not player_state: 
            return

    # --- LÓGICA PARA O JOGADOR (BUFFS) ---
        if player_state.get('active_effects'):
            player_updated_effects = []
            for effect in player_state['active_effects']:
                effect['turns_left'] -= 1
                if effect['turns_left'] > 0:
                    player_updated_effects.append(effect)
            player_state['active_effects'] = player_updated_effects

        # --- NOVA LÓGICA: CONTAGEM REGRESSIVA PARA O INIMIGO (DEBUFFS) ---
        mob = player_state.get('current_mob')
        if mob and mob.get('active_effects'):
            mob_updated_effects = []
            for effect in mob['active_effects']:
                effect['turns_left'] -= 1
                if effect['turns_left'] > 0:
                    mob_updated_effects.append(effect)
            # Atualiza a lista de efeitos diretamente no dicionário do monstro
            mob['active_effects'] = mob_updated_effects

    def get_leaderboard_text(self) -> str:
        all_participants_ids = set(self.active_fighters) | set(self.player_states.keys())
        if not all_participants_ids: return "Nenhum herói participou do evento ainda."
        leaderboard_data = []
        for user_id in all_participants_ids:
            state = self.player_states.get(user_id)
            player_data = player_manager.get_player_data(user_id)
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
    event_manager.start_event()

async def end_event_job(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Job agendado: Encerrando o evento de defesa do reino...")
    event_manager.end_event()