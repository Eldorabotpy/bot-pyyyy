# Arquivo: kingdom_defense/engine.py (versão MARATONA PRIVADA)

import random
import logging
from telegram.ext import ContextTypes
from .data import WAVE_DEFINITIONS  # Importamos nossa estrutura de ondas
from modules import player_manager # Para gerenciar dados e inventário do jogador

logger = logging.getLogger(__name__)

# --- PASSO 1: ESTRUTURA INICIAL E __init__ ---
# A classe que vai gerenciar todo o estado e lógica do nosso novo evento.

class KingdomDefenseManager:
    def __init__(self):
        """
        O construtor da classe. Define todas as variáveis que controlam o evento.
        É chamado uma vez quando o bot inicia.
        """
        # Importa as definições do seu data.py
        self.wave_definitions = WAVE_DEFINITIONS

        # Variáveis de estado inicial. reset_event() cuida de limpá-las.
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

    # --- PASSO 2: FUNÇÕES DE GERENCIAMENTO DO EVENTO ---
    # Funções de alto nível para controlar o ciclo de vida do evento.

    def start_event(self):
        """Inicia o evento de defesa do reino."""
        if self.is_active:
            return {"error": "O evento já está ativo."}
        
        logger.info("Iniciando evento de Defesa do Reino.")
        self.reset_event() # Garante que tudo comece do zero
        self.is_active = True
        return {"success": "Evento iniciado com sucesso!"}

    def end_event(self):
        """Encerra o evento e limpa todos os dados."""
        logger.info("Encerrando evento de Defesa do Reino.")
        self.reset_event()
        return {"success": "Evento encerrado."}

    def reset_event(self):
        """Reseta todas as variáveis de estado para seus valores padrão."""
        self.is_active = False
        self.current_wave = 1
        self.global_kill_count = 0
        self.boss_mode_active = False
        self.boss_global_hp = 0
        self.active_fighters = set()
        self.waiting_queue = []
        self.player_states = {}

    # --- PASSO 3: LÓGICA DE ENTRADA E FILA ---
    # Gerencia como os jogadores entram na batalha ou na fila de espera.

    def get_player_status(self, user_id):
        """Verifica se um jogador está ativo, na fila ou fora."""
        if user_id in self.active_fighters:
            return "active"
        if user_id in self.waiting_queue:
            return "waiting"
        return "not_in_event"

    def add_player_to_event(self, user_id, player_data):
        """Adiciona um jogador à luta ou à fila."""
        print(f"\n--- [ENGINE] Função 'add_player_to_event' chamada para user_id: {user_id} ---")
        status = self.get_player_status(user_id)
        if status != "not_in_event":
            print(f"--- [ENGINE] Jogador já está no evento com status: '{status}'. Retornando. ---")
            return status
        
        print(f"--- [ENGINE] Verificando vagas... Ativas: {len(self.active_fighters)} / Máximo: {self.max_concurrent_fighters} ---")
        if len(self.active_fighters) < self.max_concurrent_fighters:
            print("--- [ENGINE] Vaga encontrada! Adicionando aos lutadores ativos. ---")
            self.active_fighters.add(user_id)
            self._setup_player_battle_state(user_id, player_data)
            return "active"
        else:
            print("--- [ENGINE] Sem vagas! Adicionando à fila de espera. ---")
            self.waiting_queue.append(user_id)
            return "waiting"

    # --- PASSO 4: PREPARANDO A BATALHA ---
    # Funções internas para configurar o estado de um jogador.

    def _setup_player_battle_state(self, user_id, player_data):
        """Prepara o estado de batalha inicial para um jogador."""
        total_stats = player_manager.get_player_total_stats(player_data)
        
        current_wave_info = self.wave_definitions[self.current_wave]
        mob_template = random.choice(current_wave_info["mobs"])
        
        # Cria uma cópia do monstro para este jogador
        mob_instance = mob_template.copy()
        
        self.player_states[user_id] = {
            'player_hp': total_stats.get('max_hp', 100),
            'player_max_hp': total_stats.get('max_hp', 100),
            'current_mob': mob_instance,
            'is_fighting_boss': False
        }
        logger.info(f"Jogador {user_id} configurado para lutar contra {mob_instance['name']}.")
    
    # --- PASSO 5: O CORAÇÃO DO JOGO - PROCESSANDO O ATAQUE ---
    # A função mais importante, que lida com cada clique no botão "Atacar".

    def process_player_attack(self, user_id, player_data):
        """Processa um turno de ataque do jogador na sua batalha privada."""
        if not self.is_active or user_id not in self.active_fighters:
            return {"error": "Você não está em uma batalha ativa."}

        player_state = self.player_states[user_id]
        mob = player_state['current_mob']
        player_stats = player_manager.get_player_total_stats(player_data)
        
        # Simplificação do dano (pode ser substituído pela sua engine de criticals)
        player_damage = max(1, player_stats.get('attack', 10) - mob.get('defense', 0))
        mob['hp'] -= player_damage

        action_log = f"Você ataca {mob['name']} e causa {player_damage} de dano!"

        # O monstro foi derrotado?
        if mob['hp'] <= 0:
            self.global_kill_count += 1
            
            # Adiciona o loot ao inventário do jogador
            reward_amount = mob.get("reward", 0)
            player_manager.add_item_to_inventory(player_data, 'fragmento_bravura', reward_amount)
            player_manager.save_player_data(user_id, player_data)

            loot_message = f"Você recebeu {reward_amount}x fragmento_bravura!"
            
            # Prepara o próximo monstro
            next_mob_template = random.choice(self.wave_definitions[self.current_wave]["mobs"])
            player_state['current_mob'] = next_mob_template.copy()
            
            return {
                "monster_defeated": True,
                "action_log": f"{action_log}\n☠️ {mob['name']} foi derrotado!",
                "loot_message": loot_message,
                "next_mob_data": player_state['current_mob']
            }

        # Se o monstro não foi derrotado, ele contra-ataca
        else:
            mob_damage = max(1, mob.get('attack', 5) - player_stats.get('defense', 0))
            player_state['player_hp'] -= mob_damage
            
            action_log += f"\n🩸 {mob['name']} contra-ataca, causando {mob_damage} de dano!"

            # O jogador foi derrotado?
            if player_state['player_hp'] <= 0:
                self.active_fighters.remove(user_id)
                del self.player_states[user_id]
                # TODO: Promover o próximo da fila de espera
                return { "game_over": True, "action_log": action_log }
            
            return {
                "monster_defeated": False,
                "action_log": action_log
            }
            
    # --- PASSO 6: FUNÇÕES DE APOIO (GETTERS) ---
    # Funções que o handler usará para obter informações e exibir ao jogador.
    
    def get_battle_data(self, user_id):
        """Retorna os dados necessários para o handler montar a mensagem de batalha."""
        if user_id not in self.player_states:
            return None
        return self.player_states[user_id]
        
    def get_queue_status_text(self):
        """Retorna o texto para a tela de espera."""
        wave_info = self.wave_definitions[self.current_wave]
        goal = wave_info['mob_count']
        return (
            f"Progresso da Onda {self.current_wave}: {self.global_kill_count}/{goal}\n"
            f"Defensores Ativos: {len(self.active_fighters)}/{self.max_concurrent_fighters}"
        )

# Adicione este código NO FINAL do arquivo kingdom_defense/engine.py

# --- FUNÇÕES DE JOB (AGENDADOR) ---
# Usadas pelo agendador do bot para iniciar/terminar o evento automaticamente.

async def start_event_job(context: ContextTypes.DEFAULT_TYPE):
    """Função para o agendador iniciar o evento."""
    logger.info("Job agendado: tentando iniciar o evento...")
    event_manager.start_event()

async def end_event_job(context: ContextTypes.DEFAULT_TYPE):
    """Função para o agendador encerrar o evento."""
    logger.info("Job agendado: tentando encerrar o evento...")
    event_manager.end_event()

def start_event_at_wave(self, wave_number: int):
        """Inicia o evento em uma onda específica para testes."""
        if self.is_active:
            return {"error": "O evento já está ativo."}
        
        if wave_number not in self.wave_definitions:
            return {"error": f"A Onda {wave_number} não existe nas definições."}
            
        logger.info(f"Iniciando evento de teste na Onda {wave_number}.")
        self.reset_event()
        self.is_active = True
        self.current_wave = wave_number # A única diferença da função start_event()
        
        return {"success": f"Evento de teste iniciado na Onda {wave_number}!"}
# --- INSTÂNCIA ÚNICA ---
# Criamos uma única instância que será usada por todo o bot
event_manager = KingdomDefenseManager()