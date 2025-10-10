# Arquivo: kingdom_defense/engine.py (versão MARATONA PRIVADA)

import random
import logging
from telegram.ext import ContextTypes
from .data import WAVE_DEFINITIONS  # Importamos nossa estrutura de ondas
from modules import player_manager # Para gerenciar dados e inventário do jogador
from modules.player import stats as player_stats_engine
from . import leaderboard

logger = logging.getLogger(__name__)

class KingdomDefenseManager:
    def __init__(self):
        # ... (seu __init__ continua igual)
        self.wave_definitions = WAVE_DEFINITIONS
        self.is_active = False
        self.current_wave = 1
        self.global_kill_count = 0
        self.boss_mode_active = False
        self.boss_global_hp = 0 # Manteremos para uma futura Raid Global
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

        # --- NOVA LÓGICA PARA SALVAR O RECORDE ---
        top_scorer = None
        max_damage = 0

        # Itera sobre todos os estados de jogador do evento que acabou
        for user_id_str, state in self.player_states.items():
            if state.get('damage_dealt', 0) > max_damage:
                max_damage = state['damage_dealt']
                player_data = player_manager.get_player_data(int(user_id_str))
                if player_data:
                    top_scorer = {
                        "user_id": int(user_id_str),
                        "character_name": player_data.get("character_name", "Herói"),
                        "damage": max_damage
                    }
        
        # Se encontramos um jogador com dano, tentamos atualizar o recorde
        if top_scorer:
            leaderboard.update_top_score(
                user_id=top_scorer["user_id"],
                character_name=top_scorer["character_name"],
                damage=top_scorer["damage"]
            )
        # --- FIM DA NOVA LÓGICA ---

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
        
        # --- LÓGICA ATUALIZADA AQUI ---
        # Se o modo chefe já estiver ativo quando o jogador entrar, ele vai direto para o chefe
        if self.boss_mode_active:
            mob_template = current_wave_info["boss"]
        else:
            mob_template = random.choice(current_wave_info["mobs"])
        
        mob_instance = mob_template.copy()
        mob_instance['max_hp'] = mob_instance['hp']
        mob_instance['is_boss'] = self.boss_mode_active # Adiciona uma flag para sabermos se é o chefe
        
        self.player_states[user_id] = {
            'player_hp': total_stats.get('max_hp', 100),
            'player_max_hp': total_stats.get('max_hp', 100),
            'current_mob': mob_instance,
            'damage_dealt': 0
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

        # Lógica de Ataque Duplo e dano (sem alterações)
        double_attack_chance = player_stats_engine.get_player_double_attack_chance(player_data)
        if random.random() < double_attack_chance:
            num_attacks = 2
            logs.append("⚡ Ataque Duplo!")
        for _ in range(num_attacks):
            player_damage = max(1, player_full_stats.get('attack', 10) - mob.get('defense', 0))
            mob['hp'] -= player_damage
            player_state['damage_dealt'] += player_damage
            logs.append(f"Você ataca {mob['name']} e causa {player_damage} de dano.")
            if mob['hp'] <= 0:
                mob['hp'] = 0
                break

        # --- NOVA LÓGICA DE PROGRESSÃO APÓS A MORTE DO MOB ---
        if mob['hp'] <= 0:
            logs.append(f"☠️ {mob['name']} foi derrotado!")
            
            # Se o monstro derrotado era o CHEFE...
            if mob.get('is_boss'):
                logs.append(f"🎉 A ONDA {self.current_wave} FOI CONCLUÍDA! 🎉")
                self.current_wave += 1
                self.global_kill_count = 0
                self.boss_mode_active = False
                self.max_concurrent_fighters = 10 + (self.current_wave - 1) * 5
                # Verifica se ainda há ondas ou se o evento acabou
                if self.current_wave not in self.wave_definitions:
                    self.end_event()
                    # TODO: Adicionar lógica de recompensa final
                    return { "event_over": True, "action_log": "\n".join(logs) }
            
            # Se era um mob normal, apenas incrementa o contador
            else:
                self.global_kill_count += 1

            # Dá o loot para o jogador
            reward_amount = mob.get("reward", 0)
            player_manager.add_item_to_inventory(player_data, 'fragmento_bravura', reward_amount)
            player_manager.save_player_data(user_id, player_data)
            loot_message = f"Você recebeu {reward_amount}x fragmento_bravura!"
            
            # --- DECIDE QUAL SERÁ O PRÓXIMO INIMIGO ---
            current_wave_info = self.wave_definitions[self.current_wave]
            goal = current_wave_info['mob_count']
            
            # Verifica se atingiu a meta E se o modo chefe ainda não está ativo
            if self.global_kill_count >= goal and not self.boss_mode_active:
                self.boss_mode_active = True
                next_mob_template = current_wave_info["boss"]
                logs.append(f"🚨 O CHEFE DA ONDA, {next_mob_template['name']}, APARECEU! 🚨")
            else:
                next_mob_template = random.choice(current_wave_info["mobs"])
            
            # Prepara o próximo monstro para o jogador
            player_state['current_mob'] = next_mob_template.copy()
            player_state['current_mob']['max_hp'] = player_state['current_mob']['hp']
            player_state['current_mob']['is_boss'] = self.boss_mode_active

            return {
                "monster_defeated": True, "action_log": "\n".join(logs),
                "loot_message": loot_message, "next_mob_data": player_state['current_mob']
            }

        # Lógica de contra-ataque e derrota do jogador (sem alterações)
        else:
            # ... (esta parte continua igual) ...
            dodge_chance = player_stats_engine.get_player_dodge_chance(player_data)
            if random.random() < dodge_chance:
                logs.append(f"💨 Você se esquivou do ataque de {mob['name']}!")
            else:
                mob_damage = max(1, mob.get('attack', 5) - player_full_stats.get('defense', 0))
                player_state['player_hp'] -= mob_damage
                logs.append(f"🩸 {mob['name']} contra-ataca, causando {mob_damage} de dano!")
            if player_state['player_hp'] <= 0:
                self.active_fighters.remove(user_id)
                del self.player_states[user_id]
                return { "game_over": True, "action_log": "\n".join(logs) }
            return { "monster_defeated": False, "action_log": "\n".join(logs) }

    def get_battle_data(self, user_id):
        """Retorna os dados necessários para o handler montar a mensagem de batalha."""
        if user_id not in self.player_states:
            return None
        
        # Fazemos uma cópia para adicionar a informação da onda
        player_state_copy = self.player_states[user_id].copy()
        player_state_copy['current_wave'] = self.current_wave # <-- ADICIONE ESTA LINHA
        
        return player_state_copy
        
    def get_queue_status_text(self):
        wave_info = self.wave_definitions[self.current_wave]
        goal = wave_info['mob_count']
        return (
            f"Progresso da Onda {self.current_wave}: {self.global_kill_count}/{goal}\n"
            f"Defensores Ativos: {len(self.active_fighters)}/{self.max_concurrent_fighters}"
        )
    def get_leaderboard_text(self) -> str:
        """Gera o texto do ranking de dano do evento."""
        if not self.active_fighters:
            return "Nenhum herói está na batalha para formar um ranking."

        # Pega os dados de nome e dano de todos os jogadores ativos
        leaderboard_data = []
        for user_id_str in self.active_fighters:
            state = self.player_states.get(user_id_str)
            # Precisamos do player_data para pegar o nome
            player_data = player_manager.get_player_data(user_id_str)
            if state and player_data:
                leaderboard_data.append({
                    "name": player_data.get('character_name', 'Herói'),
                    "damage": state.get('damage_dealt', 0)
                })
        
        # Ordena os jogadores por dano, do maior para o menor
        sorted_participants = sorted(leaderboard_data, key=lambda i: i['damage'], reverse=True)
        
        lines = ["🏆 **Ranking de Dano da Onda** 🏆\n"]
        for i, status in enumerate(sorted_participants[:5]): # Pega o Top 5
            medal = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, "🔹")
            lines.append(f"{medal} {status['name']}: {status['damage']:,} de dano")
            
        return "\n".join(lines)

# --- INSTÂNCIA ÚNICA ---
event_manager = KingdomDefenseManager()

async def start_event_job(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Job agendado: tentando iniciar o evento...")
    event_manager.start_event()

async def end_event_job(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Job agendado: tentando encerrar o evento...")
    event_manager.end_event()