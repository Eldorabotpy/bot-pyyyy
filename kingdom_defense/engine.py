# Arquivo: kingdom_defense/engine.py (versão MARATONA PRIVADA)

import random
import logging
from telegram.ext import ContextTypes
from .data import WAVE_DEFINITIONS  # Importamos nossa estrutura de ondas
from modules import player_manager # Para gerenciar dados e inventário do jogador
from modules.player import stats as player_stats_engine
from . import leaderboard
from modules.combat import criticals
from modules.game_data import items as game_items

logger = logging.getLogger(__name__)

class KingdomDefenseManager:
    def __init__(self):
        # ... (seu __init__ continua igual)
        self.wave_definitions = WAVE_DEFINITIONS
        self.is_active = False
        self.current_wave = 1
        self.global_kill_count = 0
        self.boss_mode_active = False
        self.boss_global_hp = 0
        self.boss_max_hp = 0 # Adicionado para exibir a barra de vida
        self.max_concurrent_fighters = 10
        self.active_fighters = set()
        self.waiting_queue = []
        self.player_states = {}
        logger.info("Gerenciador de Defesa do Reino (Maratona) inicializado.")

    def start_event(self):
        if self.is_active: return {"error": "O evento já está ativo."}
        logger.info("Iniciando evento de Defesa do Reino.")
        self.reset_event()
        self.is_active = True
        return {"success": "Evento iniciado com sucesso!"}

    def end_event(self):
        """Encerra o evento, calcula o melhor jogador e limpa os dados."""
        logger.info("Encerrando evento de Defesa do Reino...")

        top_scorer = None
        max_damage = 0

        for user_id_str, state in self.player_states.items():
            user_id = int(user_id_str) # Garante que user_id é int
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
        self.current_wave = 1
        self.global_kill_count = 0
        self.boss_mode_active = False
        self.boss_global_hp = 0
        self.boss_max_hp = 0
        self.active_fighters = set()
        self.waiting_queue = []
        self.player_states = {}
        self.max_concurrent_fighters = 10

    def start_event_at_wave(self, wave_number: int):
        if self.is_active:
            return {"error": "O evento já está ativo."}
        if wave_number not in self.wave_definitions:
            return {"error": f"A Onda {wave_number} não existe nas definições."}
        logger.info(f"Iniciando evento de teste na Onda {wave_number}.")
        self.reset_event()
        self.is_active = True
        self.current_wave = wave_number
        return {"success": f"Evento de teste iniciado na Onda {wave_number}!"}

    def get_player_status(self, user_id):
        if user_id in self.active_fighters:
            return "active"
        if user_id in self.waiting_queue:
            return "waiting"
        return "not_in_event"

    def add_player_to_event(self, user_id, player_data):
        status = self.get_player_status(user_id)
        if status != "not_in_event": return status
        
        # Garante que as vagas aumentam com as ondas
        self.max_concurrent_fighters = min(15, 10 + (self.current_wave - 1))

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
        
        if self.boss_mode_active:
            mob_template = current_wave_info["boss"]
        else:
            mob_template = random.choice(current_wave_info["mobs"])
        
        mob_instance = mob_template.copy()
        
        if self.boss_mode_active:
            mob_instance['hp'] = self.boss_global_hp
            mob_instance['max_hp'] = self.boss_max_hp
            mob_instance['is_boss'] = True
        else:
            mob_instance['max_hp'] = mob_instance['hp']
            mob_instance['is_boss'] = False
        
        self.player_states[user_id] = {
            'player_hp': total_stats.get('max_hp', 100),
            'player_max_hp': total_stats.get('max_hp', 100),
            'current_mob': mob_instance,
            'damage_dealt': self.player_states.get(user_id, {}).get('damage_dealt', 0) # Mantém o dano
        }
        logger.info(f"Jogador {user_id} configurado para lutar contra {mob_instance['name']}.")

    def _promote_next_player(self):
        """Tira o próximo jogador da fila e o coloca na batalha."""
        if self.waiting_queue and len(self.active_fighters) < self.max_concurrent_fighters:
            next_player_id = self.waiting_queue.pop(0)
            player_data = player_manager.get_player_data(next_player_id)
            if player_data:
                self.active_fighters.add(next_player_id)
                self._setup_player_battle_state(next_player_id, player_data)
                logger.info(f"Jogador {next_player_id} promovido da fila para a batalha.")
                
    def process_player_attack(self, user_id, player_data):
        if not self.is_active or user_id not in self.active_fighters:
            return {"error": "Você não está em uma batalha ativa."}

        player_state = self.player_states[user_id]
        mob = player_state['current_mob']
        is_boss_fight = mob.get('is_boss', False)
    
        player_full_stats = player_manager.get_player_total_stats(player_data)
        logs, num_attacks = [], 1
    
        double_attack_chance = player_stats_engine.get_player_double_attack_chance(player_data)
        if random.random() < double_attack_chance:
            num_attacks = 2
            logs.append("⚡ Ataque Duplo!")
        
        total_damage_dealt_in_turn = 0
        for _ in range(num_attacks):
            damage, is_crit, _ = criticals.roll_damage(player_full_stats, mob, {})
            if is_crit:
                logs.append("💥 DANO CRÍTICO! 💥")
            logs.append(f"Você ataca {mob['name']} e causa {damage} de dano.")
            total_damage_dealt_in_turn += damage
            
            if is_boss_fight:
                self.boss_global_hp -= damage
            else:
                mob['hp'] -= damage
            
            if (is_boss_fight and self.boss_global_hp <= 0) or (not is_boss_fight and mob['hp'] <= 0):
                break

        player_state['damage_dealt'] += total_damage_dealt_in_turn
    
        mob_is_defeated = (is_boss_fight and self.boss_global_hp <= 0) or (not is_boss_fight and mob['hp'] <= 0)
    
        if mob_is_defeated:
            logs.append(f"☠️ {mob['name']} foi derrotado!")
        
            if is_boss_fight:
                logs.append(f"🎉 A ONDA {self.current_wave} FOI CONCLUÍDA! 🎉")
                self.current_wave += 1
                self.global_kill_count = 0
                self.boss_mode_active = False
                self.max_concurrent_fighters = min(15, 10 + (self.current_wave - 1))
            
                if self.current_wave not in self.wave_definitions:
                    self.end_event()
                    return {"event_over": True, "action_log": "\n".join(logs)}
            else:
                self.global_kill_count += 1

            reward_amount = mob.get("reward", 0)
            item_id = 'fragmento_bravura' 
            loot_message = ""
            if reward_amount > 0:
                player_manager.add_item_to_inventory(player_data, item_id, reward_amount)
                item_info = game_items.ITEMS_DATA.get(item_id, {})
                item_name = item_info.get('display_name', item_id)
                loot_message = f"Você recebeu {reward_amount}x {item_name}!"
            
            current_wave_info = self.wave_definitions[self.current_wave]
            goal = current_wave_info.get('mob_count', float('inf'))
        
            if not self.boss_mode_active and self.global_kill_count >= goal:
                self.boss_mode_active = True
                boss_template = current_wave_info["boss"]
                self.boss_max_hp = boss_template['hp']
                self.boss_global_hp = boss_template['hp']
                logs.append(f"🚨 O CHEFE DA ONDA, {boss_template['name']}, APARECEU! 🚨")
        
            self._setup_player_battle_state(user_id, player_data)
            player_manager.save_player_data(user_id, player_data)

            return {
                "monster_defeated": True, "action_log": "\n".join(logs),
                "loot_message": loot_message, "next_mob_data": self.player_states[user_id]['current_mob']
            }
        else:
            dodge_chance = player_stats_engine.get_player_dodge_chance(player_data)
            if random.random() < dodge_chance:
                logs.append(f"💨 Você se esquivou do ataque de {mob['name']}!")
            else:
                mob_damage, mob_is_crit, _ = criticals.roll_damage(mob, player_full_stats, {})
                if mob_is_crit:
                    logs.append("💥 DANO CRÍTICO INIMIGO! 💥")
                player_state['player_hp'] -= mob_damage
                logs.append(f"🩸 {mob['name']} contra-ataca, causando {mob_damage} de dano!")

            if player_state['player_hp'] <= 0:
                logs.append("\nVOCÊ FOI DERROTADO!")
                self.active_fighters.remove(user_id)
                # NOTA: Não removemos o player_state daqui para manter o score de dano.
                # Apenas o tiramos da luta ativa.
                
                # _# CORRIGIDO: Chama a função para promover o próximo da fila #_
                self._promote_next_player()
                
                # _# CORRIGIDO: Retorna um estado claro de 'game_over' #_
                return { "game_over": True, "action_log": "\n".join(logs) }
        
            player_manager.save_player_data(user_id, player_data)
            return { "monster_defeated": False, "action_log": "\n".join(logs) }
        
    def get_battle_data(self, user_id):
        if user_id not in self.player_states:
            return None
        
        player_state_copy = self.player_states[user_id].copy()
        player_state_copy['current_wave'] = self.current_wave
        
        # _# MELHORIA: Atualiza o HP do chefe para todos os jogadores #_
        if player_state_copy['current_mob'].get('is_boss'):
             player_state_copy['current_mob']['hp'] = self.boss_global_hp

        return player_state_copy
        
    def get_queue_status_text(self):
        wave_info = self.wave_definitions.get(self.current_wave)
        if not wave_info: return "Aguardando informações da próxima onda..."

        status_line = ""
        if self.boss_mode_active:
            # Mostra a vida do chefe
            status_line = f"Chefe: {self.boss_global_hp}/{self.boss_max_hp} HP"
        else:
            # Mostra o progresso de abates
            goal = wave_info.get('mob_count', 0)
            status_line = f"Progresso da Onda {self.current_wave}: {self.global_kill_count}/{goal}"

        return (
            f"{status_line}\n"
            f"Defensores Ativos: {len(self.active_fighters)}/{self.max_concurrent_fighters}\n"
            f"Heróis na Fila: {len(self.waiting_queue)}"
        )
    
    def get_leaderboard_text(self) -> str:
        """Gera o texto do ranking de dano do evento."""
        # Combina lutadores ativos e jogadores derrotados que participaram
        all_participants_ids = set(self.active_fighters) | set(self.player_states.keys())

        if not all_participants_ids:
            return "Nenhum herói participou do evento ainda."

        leaderboard_data = []
        for user_id in all_participants_ids:
            state = self.player_states.get(user_id)
            player_data = player_manager.get_player_data(user_id)
            if state and player_data and state.get('damage_dealt', 0) > 0:
                leaderboard_data.append({
                    "name": player_data.get('character_name', 'Herói'),
                    "damage": state.get('damage_dealt', 0)
                })
        
        if not leaderboard_data:
            return "Ninguém causou dano ainda."

        sorted_participants = sorted(leaderboard_data, key=lambda i: i['damage'], reverse=True)
        
        lines = ["🏆 **Ranking de Dano do Evento** 🏆\n"]
        for i, status in enumerate(sorted_participants[:5]): # Pega o Top 5
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