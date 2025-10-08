# Arquivo: kingdom_defense/engine.py (versão final, completa e corrigida)

import random
import logging
import json
from pathlib import Path
from .data import WAVE_DEFINITIONS
from modules import player_manager, stats_engine, file_ids
from handlers.utils import format_dungeon_combat_message, create_progress_bar
from telegram.ext import ContextTypes
from modules.combat import criticals
from .utils import format_kd_battle_message

logger = logging.getLogger(__name__)
ATTACK_ENERGY_COST = 1
FALLBACK_IMAGE_ID = "ID_DA_SUA_IMAGEM_DE_ERRO_AQUI" 
STATE_FILE = Path(__file__).parent / "kd_event_state.json"

class KingdomDefenseManager:
    def __init__(self):
        self.reset_event()
        self.load_state()
        logger.info("Gerenciador de Defesa do Reino inicializado.")

    def save_state(self):
        state = {
            "is_active": self.is_active,
            "visual_mode": self.visual_mode,
            "current_wave_num": self.current_wave_num,
            "participants_status": self.participants_status,
            "wave_mobs": self.wave_mobs,
            "total_mobs_in_wave": self.total_mobs_in_wave,
            "battle_log": self.battle_log,
            "battle_message": getattr(self, 'battle_message', {})
        }
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Falha ao salvar o estado do evento: {e}")

    
    def load_state(self):
        if not STATE_FILE.exists(): return
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
                self.is_active = state.get("is_active", False)
                if self.is_active:
                    self.visual_mode = state.get("visual_mode", False)
                    self.current_wave_num = state.get("current_wave_num", 0)
                    self.participants_status = state.get("participants_status", {})
                    self.wave_mobs = state.get("wave_mobs", [])
                    self.total_mobs_in_wave = state.get("total_mobs_in_wave", 0)
                    self.battle_log = state.get("battle_log", [])
                    self.battle_message = state.get("battle_message", {})
                    logger.info("Estado do evento de defesa carregado.")
        except Exception as e:
            logger.error(f"Falha ao carregar o estado do evento: {e}")
            self.reset_event()


    def reset_event(self):
        self.is_active = False
        self.visual_mode = False
        self.current_wave_num = 0
        self.participants_status = {}
        self.wave_mobs = []
        self.total_mobs_in_wave = 0
        self.battle_log = []
        self.battle_message = {}
        
    def start_event(self):
        """Inicia o evento e retorna a mensagem de batalha inicial."""
        if self.is_active: 
            return {"message": "O evento já está ativo!"}
        
        self.reset_event()
        self.is_active = True
        self.load_wave(1)
        
        if not self.wave_mobs:
            self.end_event() # Não precisa de 'victory=True' aqui
            return {"text": "Erro: Nenhuma onda definida para o evento."}
        
        media_key = self.wave_mobs[0].get("media_key")
        file_id = file_ids.get_file_id(media_key)
        
        if file_id:
            self.visual_mode = True
            self.save_state() # Salva o estado após iniciar
            return {"file_id": file_id, "caption": self.get_battle_status_text()}
        else:
            self.visual_mode = False
            self.save_state() # Salva o estado após iniciar
            return {"text": self.get_battle_status_text()}

    def load_wave(self, wave_number):
        """Carrega os dados de uma nova onda."""
        wave_data = WAVE_DEFINITIONS.get(wave_number)
        if not wave_data:
            # Fim de todas as ondas, vitória!
            self.is_active = False # Marca como inativo para a lógica de finalização
            return

        self.current_wave_num = wave_number
        mobs = wave_data.get("mobs", [])
        boss = wave_data.get("boss")
        
        self.wave_mobs = [random.choice(mobs).copy() for _ in range(wave_data.get("mob_count", 10))]
        if boss:
            self.wave_mobs.append(boss.copy())
            
        random.shuffle(self.wave_mobs)
        self.total_mobs_in_wave = len(self.wave_mobs)
        self._add_log(f"🌊 Horda da Onda {self.current_wave_num} aproxima-se!")
    
    def start_event_at_wave(self, wave_number: int):
        """
        Inicia o evento em MODO DE TESTE diretamente em uma wave específica.
        """
        if self.is_active:
            return {"message": "Um evento já está ativo! Termine-o antes de iniciar um teste."}
        
        self.reset_event()
        self.is_active = True
        
        # Carrega a wave específica em vez da primeira
        self.load_wave(wave_number)
        
        if not self.wave_mobs:
            self.end_event()
            return {"text": f"Erro: A wave {wave_number} não foi encontrada ou está vazia."}
        
        # O resto é igual à função start_event normal
        media_key = self.wave_mobs[0].get("media_key")
        file_id = file_ids.get_file_id(media_key)
        
        if file_id:
            self.visual_mode = True
            self.save_state()
            return {"file_id": file_id, "caption": self.get_battle_status_text()}
        else:
            self.visual_mode = False
            self.save_state()
            return {"text": self.get_battle_status_text()}

    def start_event_at_wave(self, wave_number: int):
        if self.is_active: return {"message": "Um evento já está ativo!"}
        return self._start_logic(wave_number)
    
    def _start_logic(self, wave_number):
        self.reset_event()
        self.is_active = True
        self.load_wave(wave_number)
        
        if not self.wave_mobs:
            self.end_event()
            return {"text": f"Erro: A wave {wave_number} não foi encontrada ou está vazia."}
        
        media_key = self.wave_mobs[0].get("media_key")
        media_info = file_ids.get_media_info(media_key)
        
        if media_info and media_info.get("id"):
            self.visual_mode = True
            self.save_state()
            return {
                "file_id": media_info.get("id"), 
                "media_type": media_info.get("type", "photo"),
                "caption": self.get_battle_status_text()
            }
        else:
            self.visual_mode = False
            self.save_state()
            return {"text": self.get_battle_status_text()}
    def load_wave(self, wave_number):
        wave_data = WAVE_DEFINITIONS.get(wave_number)
        if not wave_data:
            self.is_active = False
            return

        self.current_wave_num = wave_number
        mobs = wave_data.get("mobs", [])
        boss = wave_data.get("boss")
        
        self.wave_mobs = [random.choice(mobs).copy() for _ in range(wave_data.get("mob_count", 10))]
        if boss: self.wave_mobs.append(boss.copy())
            
        random.shuffle(self.wave_mobs)
        self.total_mobs_in_wave = len(self.wave_mobs)
        self._add_log(f"🌊 Horda da Onda {self.current_wave_num} aproxima-se!")

    def end_event(self, victory=False):
        message = "Vitória! O Reino foi defendido!" if victory else "O evento foi encerrado."
        self.reset_event()
        self.save_state()
        if STATE_FILE.exists():
            try: STATE_FILE.unlink()
            except OSError as e: logger.error(f"Erro ao deletar arquivo de estado: {e}")
        return message

    def add_participant(self, user_id: int, player_data: dict):
        if not self.is_active: return False
        user_id_str = str(user_id)
        total_stats = player_manager.get_player_total_stats(player_data)
        max_hp = total_stats.get('max_hp', 1)
        self.participants_status[user_id_str] = {
            'hp': max_hp, 'max_hp': max_hp, 
            'name': player_data.get('character_name', 'Herói'),
            'damage_dealt': 0
        }
        self.save_state()
        return True
    
    def set_battle_message_info(self, message_id: int, chat_id: int):
        self.battle_message = {'id': message_id, 'chat_id': chat_id}
        self.save_state()

    def get_battle_message_info(self) -> dict:
        return self.battle_message

    def _add_log(self, text: str):
        """Adiciona uma entrada ao log de combate."""
        self.battle_log.append(text)
        if len(self.battle_log) > 5:
            self.battle_log.pop(0)

    def process_attack(self, user_id: int, player_data: dict) -> dict:
        user_id_str = str(user_id)
        if not self.is_active or user_id_str not in self.participants_status: 
            return {"private_message": "Você não está participando desta batalha!"}

        
        if self.participants_status[user_id_str]['hp'] <= 0:
            return {"private_message": "Você foi derrotado e não pode mais atacar! 💔"}
        
        if player_data.get('energy', 0) < ATTACK_ENERGY_COST: 
            return {"private_message": f"Sem energia! ({ATTACK_ENERGY_COST} ⚡️)"}
        
        if not self.wave_mobs:
            self.load_wave(self.current_wave_num + 1)
            if not self.is_active:
                self._add_log("🎉 VITÓRIA! O REINO ESTÁ A SALVO! 🎉")
                final_caption = self.get_battle_status_text()
                rewards = self.calculate_rewards()
                self.end_event(victory=True)
                return {
                    "event_over": True, "victory": True,
                    "final_caption": final_caption, "rewards": rewards
                }

        player_data['energy'] -= ATTACK_ENERGY_COST
        
        target_mob = self.wave_mobs.pop(0)
        self._add_log(f"⚡ {player_data['character_name']} encontra um {target_mob['name']}!")
        
        player_stats = player_manager.get_player_total_stats(player_data)
        damage, _, _ = criticals.roll_damage(player_stats.get('attack', 5), target_mob.get('defense', 0), {})
        
        self.participants_status[user_id_str]['damage_dealt'] += damage
        target_mob['hp'] -= damage
        self._add_log(f"⚔️ {player_data['character_name']} ataca ({damage} dano)!")

        if target_mob['hp'] <= 0:
            self._add_log(f"☠️ {target_mob['name']} foi derrotado!")
            reward = target_mob.get("reward", 0)
            if reward > 0: player_manager.add_item_to_inventory(player_data, 'fragmento_bravura', reward)
        else:
            damage_taken, _, _ = criticals.roll_damage(target_mob.get('attack', 5), player_stats.get('defense', 0), {})
            self.participants_status[user_id_str]['hp'] -= damage_taken
            self._add_log(f"🩸 {target_mob['name']} contra-ataca ({damage_taken} dano)!")
            if self.participants_status[user_id_str]['hp'] <= 0:
                self.participants_status[user_id_str]['hp'] = 0
                self._add_log(f"💔 {player_data['character_name']} foi derrotado!")
        
        player_manager.save_player_data(user_id, player_data)
        self.save_state()
        
        return {"caption" if self.visual_mode else "text": self.get_battle_status_text()}

    def calculate_rewards(self) -> dict:
        rewards = {}
        for user_id, status in self.participants_status.items():
            if status['damage_dealt'] > 0:
                rewards[user_id] = {'emblema_bravura': 10}
        return rewards
    
    def get_leaderboard_text(self) -> str:
        if not self.participants_status: return "Ninguém se juntou à batalha ainda."
        sorted_participants = sorted(self.participants_status.items(), key=lambda i: i[1]['damage_dealt'], reverse=True)
        
        lines = ["🏆 **Ranking de Dano** 🏆\n"]
        for i, (_, status) in enumerate(sorted_participants[:5]):
            medal = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, "🔹")
            lines.append(f"{medal} {status['name']}: {status['damage_dealt']:,} de dano")
        return "\n".join(lines)
    
    def get_battle_status_text(self) -> str:
        if not self.is_active: return "🎉 **VITÓRIA!** 🎉\nO Reino foi salvo!"
        header = f"🌊 **ONDA {self.current_wave_num}** 🌊\n"
        remaining, total = len(self.wave_mobs), self.total_mobs_in_wave
        progress_bar = create_progress_bar(total - remaining if total > 0 else 0, total)
        status_line = f"Monstros Restantes: {remaining}/{total}\n{progress_bar}"
        active_heroes = sum(1 for p in self.participants_status.values() if p['hp'] > 0)
        heroes_line = f"Heróis em Batalha: {active_heroes}"
        log_str = "\n\n**Últimos Acontecimentos:**\n" + "\n".join(self.battle_log)
        return f"{header}{heroes_line}\n{status_line}{log_str}"


    def _get_visual_caption(self) -> str:
        """Gera a legenda para o modo com imagem."""
        header = f"🌊 **ONDA {self.current_wave_num}** 🌊\n"
        remaining = len(self.wave_mobs); total = self.total_mobs_in_wave
        progress = total - remaining if total > 0 else 0
        progress_bar = create_progress_bar(progress, total)
        status_linha = f"Monstros Restantes: {remaining}/{total}\n{progress_bar}"
        
        active_heroes = sum(1 for p in self.participants_status.values() if p['hp'] > 0)
        heroes_linha = f"Heróis em Batalha: {active_heroes}"
        
        log_str = "\n\n**Últimos Acontecimentos:**\n" + "\n".join(self.battle_log)
        return header + heroes_linha + "\n" + status_linha + log_str

    def _get_text_mode_message(self) -> str:
        """Gera o painel de texto completo usando a nova função de formatação."""
        if not self.is_active: 
            return "O evento de Defesa do Reino terminou."

    # Prepara os dados exatamente como a nova função espera
        participants_str_keys = {str(k): v for k, v in self.participants_status.items()}
        monsters_dict = {f"mob_{i}": mob for i, mob in enumerate(self.wave_mobs)}

        dungeon_instance = {
            'combat_state': {
                'participants': participants_str_keys, 
                'monsters': monsters_dict, 
                'battle_log': self.battle_log
            }
        }

        # Recupera os dados completos dos jogadores
        all_players_data = {
            int(pid): player_manager.get_player_data(int(pid)) 
            for pid in participants_str_keys.keys()
        }

        # Chama a sua nova e poderosa função de formatação!
        return format_kd_battle_message(dungeon_instance, all_players_data)

# Instância única do gerenciador
event_manager = KingdomDefenseManager()

# Funções de job (agendador)
async def start_event_job(context: ContextTypes.DEFAULT_TYPE):
    if event_manager.is_active: return
    event_manager.start_event()

async def end_event_job(context: ContextTypes.DEFAULT_TYPE):
    if not event_manager.is_active: return
    event_manager.end_event()