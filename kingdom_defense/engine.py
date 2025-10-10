# Arquivo: kingdom_defense/engine.py (versão MARATONA PRIVADA)

import random
import logging
from telegram.ext import ContextTypes
from .data import WAVE_DEFINITIONS  # Importamos nossa estrutura de ondas
from modules import player_manager # Para gerenciar dados e inventário do jogador
from modules.player import stats as player_stats_engine

logger = logging.getLogger(__name__)

class KingdomDefenseManager:
    def __init__(self):
        self.wave_definitions = WAVE_DEFINITIONS
        self.is_active = False
        self.current_wave = 1
        self.global_kill_count = 0
        self.boss_mode_active = False
        self.boss_global_hp = 0
        self.max_concurrent_fighters = 10
        self.active_fighters = set()
        self.waiting_queue = []
        self.player_states = {}
        logger.info("Novo Gerenciador de Defesa do Reino (Maratona) inicializado.")

    def start_event(self):
        if self.is_active:
            return {"error": "O evento já está ativo."}
        logger.info("Iniciando evento de Defesa do Reino.")
        self.reset_event()
        self.is_active = True
        return {"success": "Evento iniciado com sucesso!"}

    def end_event(self):
        logger.info("Encerrando evento de Defesa do Reino.")
        self.reset_event()
        return {"success": "Evento encerrado."}

    def reset_event(self):
        self.is_active = False
        self.current_wave = 1
        self.global_kill_count = 0
        self.boss_mode_active = False
        self.boss_global_hp = 0
        self.active_fighters = set()
        self.waiting_queue = []
        self.player_states = {}

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
        if status != "not_in_event":
            return status
        if len(self.active_fighters) < self.max_concurrent_fighters:
            self.active_fighters.add(user_id)
            self._setup_player_battle_state(user_id, player_data)
            return "active"
        else:
            self.waiting_queue.append(user_id)
            return "waiting"

    def _setup_player_battle_state(self, user_id, player_data):
        total_stats = player_manager.get_player_total_stats(player_data)
        current_wave_info = self.wave_definitions[self.current_wave]
        mob_template = random.choice(current_wave_info["mobs"])
        mob_instance = mob_template.copy()
        
        # Garante que o monstro também tenha um max_hp para a barra de vida
        mob_instance['max_hp'] = mob_instance['hp']

        self.player_states[user_id] = {
            'player_hp': total_stats.get('max_hp', 100),
            'player_max_hp': total_stats.get('max_hp', 100),
            'current_mob': mob_instance,
            'is_fighting_boss': False
        }
        logger.info(f"Jogador {user_id} configurado para lutar contra {mob_instance['name']}.")

    def process_player_attack(self, user_id, player_data):
        if not self.is_active or user_id not in self.active_fighters:
            return {"error": "Você não está em uma batalha ativa."}

        player_state = self.player_states[user_id]
        mob = player_state['current_mob']
        player_full_stats = player_manager.get_player_total_stats(player_data)
        
        logs = []
        num_attacks = 1

        # 1. VERIFICA ATAQUE DUPLO
        double_attack_chance = player_stats_engine.get_player_double_attack_chance(player_data)
        if random.random() < double_attack_chance:
            num_attacks = 2
            logs.append("⚡ Ataque Duplo!")

        # 2. EXECUTA O(S) ATAQUE(S) DO JOGADOR
        for _ in range(num_attacks):
            player_damage = max(1, player_full_stats.get('attack', 10) - mob.get('defense', 0))
            mob['hp'] -= player_damage
            logs.append(f"Você ataca {mob['name']} e causa {player_damage} de dano.")
            if mob['hp'] <= 0:
                mob['hp'] = 0 # Garante que o HP não fique negativo
                break

        # 3. VERIFICA SE O MONSTRO FOI DERROTADO
        if mob['hp'] <= 0:
            self.global_kill_count += 1
            reward_amount = mob.get("reward", 0)
            player_manager.add_item_to_inventory(player_data, 'fragmento_bravura', reward_amount)
            player_manager.save_player_data(user_id, player_data)
            logs.append(f"☠️ {mob['name']} foi derrotado!")
            
            next_mob_template = random.choice(self.wave_definitions[self.current_wave]["mobs"])
            player_state['current_mob'] = next_mob_template.copy()
            player_state['current_mob']['max_hp'] = player_state['current_mob']['hp']

            return {
                "monster_defeated": True, "action_log": "\n".join(logs),
                "loot_message": f"Você recebeu {reward_amount}x fragmento_bravura!",
                "next_mob_data": player_state['current_mob']
            }

        # 4. SE O MONSTRO SOBREVIVEU, ELE CONTRA-ATACA (COM CHANCE DE ESQUIVA)
        else:
            dodge_chance = player_stats_engine.get_player_dodge_chance(player_data)
            if random.random() < dodge_chance:
                logs.append(f"💨 Você se esquivou do ataque de {mob['name']}!")
            else:
                mob_damage = max(1, mob.get('attack', 5) - player_full_stats.get('defense', 0))
                player_state['player_hp'] -= mob_damage
                logs.append(f"🩸 {mob['name']} contra-ataca, causando {mob_damage} de dano!")

            # 5. VERIFICA SE O JOGADOR FOI DERROTADO
            if player_state['player_hp'] <= 0:
                self.active_fighters.remove(user_id)
                del self.player_states[user_id]
                # TODO: Implementar a lógica para promover o próximo da fila de espera
                return { "game_over": True, "action_log": "\n".join(logs) }
            
            return { "monster_defeated": False, "action_log": "\n".join(logs) }

    def get_battle_data(self, user_id):
        if user_id not in self.player_states:
            return None
        return self.player_states[user_id]
        
    def get_queue_status_text(self):
        wave_info = self.wave_definitions[self.current_wave]
        goal = wave_info['mob_count']
        return (
            f"Progresso da Onda {self.current_wave}: {self.global_kill_count}/{goal}\n"
            f"Defensores Ativos: {len(self.active_fighters)}/{self.max_concurrent_fighters}"
        )

# --- INSTÂNCIA ÚNICA ---
event_manager = KingdomDefenseManager()

async def start_event_job(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Job agendado: tentando iniciar o evento...")
    event_manager.start_event()

async def end_event_job(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Job agendado: tentando encerrar o evento...")
    event_manager.end_event()