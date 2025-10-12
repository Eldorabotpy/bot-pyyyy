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

        # --- NOVA LÓGICA DE HP PERSISTENTE ---
        # Por padrão, o jogador começa com HP máximo
        current_hp = total_stats.get('max_hp', 100)
    
        # Mas, se o jogador já estava no evento, mantemos o HP que ele tinha
        if user_id in self.player_states and 'player_hp' in self.player_states[user_id]:
            current_hp = self.player_states[user_id]['player_hp']
        # --- FIM DA NOVA LÓGICA ---
    
        # Mantém o dano total causado, mesmo que o estado seja recriado
        current_damage = self.player_states.get(user_id, {}).get('damage_dealt', 0)

        self.player_states[user_id] = {
            'player_hp': current_hp, # Usa o valor de HP calculado (ou mantido)
            'player_max_hp': total_stats.get('max_hp', 100),
            'current_mob': mob_instance,
            'damage_dealt': current_damage
        }
        logger.info(f"Jogador {user_id} configurado para lutar contra {mob_instance['name']} com {current_hp} de HP.")

    def _promote_next_player(self):
        """Tira o próximo jogador da fila e o coloca na batalha."""
        if self.waiting_queue and len(self.active_fighters) < self.max_concurrent_fighters:
            next_player_id = self.waiting_queue.pop(0)
            player_data = player_manager.get_player_data(next_player_id)
            if player_data:
                self.active_fighters.add(next_player_id)
                self._setup_player_battle_state(next_player_id, player_data)
                logger.info(f"Jogador {next_player_id} promovido da fila para a batalha.")
                
    # Em kingdom_defense/engine.py

def process_player_attack(self, user_id, player_data):
    """
    Processa um turno de ataque, com a lógica de recompensa ajustada para 1 item por vitória.
    """
    if not self.is_active or user_id not in self.active_fighters:
        return {"error": "Você não está em uma batalha ativa."}

    player_state = self.player_states[user_id]
    mob = player_state['current_mob']
    is_boss_fight = mob.get('is_boss', False)

    player_full_stats = player_manager.get_player_total_stats(player_data)
    logs, num_attacks = [], 1
    
    # --- LÓGICA DE ATAQUE DO JOGADOR (com ataque duplo e crítico) ---
    double_attack_chance = player_stats_engine.get_player_double_attack_chance(player_data)
    if random.random() < double_attack_chance:
        num_attacks = 2
        logs.append("⚡ Ataque Duplo!")
    
    total_damage_dealt_in_turn = 0
    for _ in range(num_attacks):
        # A chamada para roll_damage agora passa os dicionários de stats
        damage, is_crit, is_mega = criticals.roll_damage(player_full_stats, mob, {})
        
        logs.append(f"Você ataca {mob['name']} e causa {damage} de dano.")
        if is_mega:
            logs.append("💥💥 MEGA CRÍTICO!")
        elif is_crit:
            logs.append("💥 DANO CRÍTICO!")
            
        total_damage_dealt_in_turn += damage
        
        if is_boss_fight:
            self.boss_global_hp -= damage
        else:
            mob['hp'] -= damage
        
        if (is_boss_fight and self.boss_global_hp <= 0) or (not is_boss_fight and mob['hp'] <= 0):
            break

    player_state['damage_dealt'] += total_damage_dealt_in_turn

    # --- VERIFICA O RESULTADO DA BATALHA ---
    mob_is_defeated = (is_boss_fight and self.boss_global_hp <= 0) or (not is_boss_fight and mob['hp'] <= 0)

    if mob_is_defeated:
        logs.append(f"☠️ {mob['name']} foi derrotado!")
    
        if is_boss_fight:
            logs.append(f"🎉 A ONDA {self.current_wave} FOI CONCLUÍDA! 🎉")
            self.current_wave += 1
            self.global_kill_count = 0
            self.boss_mode_active = False
            self.max_concurrent_fighters += 5
        
            if self.current_wave not in self.wave_definitions:
                self.end_event()
                return {"event_over": True, "action_log": "\n".join(logs)}
        else:
            self.global_kill_count += 1

        # --- CORREÇÃO DA LÓGICA DE LOOT ---
        # A quantidade de recompensa agora é sempre 1.
        reward_amount = 1
        item_id = 'fragmento_bravura' # O item que será dropado
        loot_message = ""
        
        player_manager.add_item_to_inventory(player_data, item_id, reward_amount)
        item_info = game_items.ITEMS_DATA.get(item_id, {})
        item_name = item_info.get('display_name', item_id)
        loot_message = f"Você recebeu {reward_amount}x {item_name}!"
        # --- FIM DA CORREÇÃO ---
        
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
        # LÓGICA DE CONTRA-ATAQUE (inalterada)
        dodge_chance = player_stats_engine.get_player_dodge_chance(player_data)
        if random.random() < dodge_chance:
            logs.append(f"💨 Você se esquivou do ataque de {mob['name']}!")
        else:
            mob_damage, mob_is_crit, mob_is_mega = criticals.roll_damage(mob, player_full_stats, {})
            
            logs.append(f"🩸 {mob['name']} contra-ataca, causando {mob_damage} de dano!")
            if mob_is_mega:
                logs.append("‼️ MEGA CRÍTICO inimigo!")
            elif mob_is_crit:
                logs.append("❗️ DANO CRÍTICO inimigo!")

            player_state['player_hp'] -= mob_damage

        if player_state['player_hp'] <= 0:
            logs.append("\nVOCÊ FOI DERROTADO!")
            self.active_fighters.remove(user_id)
            self._promote_next_player()
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
        
    # Em kingdom_defense/engine.py, dentro da classe KingdomDefenseManager

def get_queue_status_text(self):
    """Gera o texto de status para o menu e a fila de espera."""
    wave_info = self.wave_definitions.get(self.current_wave)
    if not wave_info:
        return "Aguardando informações da próxima onda..."

    status_line = ""
    # Se o chefe estiver ativo, mostra a vida dele
    if self.boss_mode_active and self.boss_max_hp > 0:
        percent_hp = (self.boss_global_hp / self.boss_max_hp) * 100
        status_line = f"Vida do Chefe: {self.boss_global_hp:,}/{self.boss_max_hp:,} ({percent_hp:.1f}%)"
    # Senão, mostra o progresso de abates
    else:
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