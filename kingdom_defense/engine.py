# Arquivo: kingdom_defense/engine.py (versão final, completa e corrigida)

import random
import logging
from .data import WAVE_DEFINITIONS
from modules import player_manager, stats_engine, file_ids
from handlers.utils import format_dungeon_combat_message, create_progress_bar
from telegram.ext import ContextTypes
from modules.combat import criticals

logger = logging.getLogger(__name__)
ATTACK_ENERGY_COST = 1
FALLBACK_IMAGE_ID = "ID_DA_SUA_IMAGEM_DE_ERRO_AQUI" 

class KingdomDefenseManager:
    def __init__(self):
        self.reset_event()
        logger.info("Gerenciador de Defesa do Reino inicializado.")

    def reset_event(self):
        """Reseta completamente o estado do evento, garantindo que todas as variáveis existam."""
        self.is_active = False
        self.visual_mode = False
        self.current_wave_num = 0
        self.participants_status = {}
        self.total_participants = set()
        self.wave_mobs = []
        self.total_mobs_in_wave = 0
        self.current_boss = None
        self.wave_phase = None # Garante que 'wave_phase' sempre exista
        self.battle_log = []

    def start_event(self):
        """Inicia o evento e retorna a mensagem de batalha inicial."""
        if self.is_active: 
            return {"message": "O evento já está ativo!"}
        
        self.reset_event()
        self.is_active = True
        self.load_wave(1)
        
        if not self.wave_mobs and not self.current_boss:
            self.end_event()
            return {"text": "Erro: Nenhuma onda definida para o evento."}
        
        # Determina o modo (visual ou texto)
        media_key = self.wave_mobs[0].get("media_key") if self.wave_mobs else self.current_boss.get("media_key")
        file_id = file_ids.get_file_id(media_key)
        
        if file_id:
            self.visual_mode = True
            return {"file_id": file_id, "caption": self.get_battle_status_text()}
        else:
            self.visual_mode = False
            return {"text": self.get_battle_status_text()}

    def load_wave(self, wave_number):
        """Carrega os dados de uma nova onda e sua reserva de monstros."""
        wave_data = WAVE_DEFINITIONS.get(wave_number)
        if not wave_data:
            self.end_event(victory=True)
            return

        self.current_wave_num = wave_number
        self.wave_phase = 'mobs' # Define a fase inicial
        self.wave_mobs = [random.choice(wave_data["mobs"]).copy() for _ in range(wave_data["mob_count"])]
        self.wave_mobs.append(wave_data["boss"].copy())
        random.shuffle(self.wave_mobs)
        self.total_mobs_in_wave = len(self.wave_mobs)
        self._add_log(f"🌊 Uma horda de {self.total_mobs_in_wave} monstros da Onda {self.current_wave_num} aproxima-se!")

    def end_event(self, victory=False):
        """Encerra o evento."""
        if not self.is_active: return "Nenhum evento ativo para encerrar."
        message = "Vitória! O Reino foi defendido!" if victory else "O evento foi encerrado."
        self.is_active = False
        return message

    def add_participant(self, user_id: int, player_data: dict):
        """Adiciona um jogador ao evento."""
        if not self.is_active: return False
        total_stats = player_manager.get_player_total_stats(player_data)
        max_hp = total_stats.get('max_hp', 1)
        self.participants_status[user_id] = {'hp': max_hp, 'max_hp': max_hp, 'name': player_data.get('character_name', 'Herói')}
        self.total_participants.add(user_id)
        return True

    def _add_log(self, text: str):
        """Adiciona uma entrada ao log de combate."""
        self.battle_log.append(text)
        if len(self.battle_log) > 5:
            self.battle_log.pop(0)

    def process_attack(self, user_id: int, player_data: dict) -> dict:
        """Processa um duelo 1-contra-1 de um jogador contra um monstro da reserva."""
        if not self.is_active or user_id not in self.participants_status: 
            return {"private_message": "Você não está participando desta batalha!"}
        if player_data.get('energy', 0) < ATTACK_ENERGY_COST: 
            return {"private_message": f"Sem energia! ({ATTACK_ENERGY_COST} ⚡️)"}
        
        if not self.wave_mobs:
            self.load_wave(self.current_wave_num + 1)
            if not self.is_active:
                self._add_log("🎉 VITÓRIA! O REINO ESTÁ A SALVO! 🎉")
                return {"text": self.get_battle_status_text()}

        player_data['energy'] -= ATTACK_ENERGY_COST
        
        target_mob = self.wave_mobs.pop(0)
        self._add_log(f"⚡ {player_data['character_name']} encontra um {target_mob['name']}!")
        
        player_stats = player_manager.get_player_total_stats(player_data)
        player_crit_params = criticals.get_crit_params_for_player(player_data, player_stats)
        damage, is_crit, is_mega = criticals.roll_damage(player_stats.get('attack', 5), target_mob.get('defense', 0), player_crit_params)
        target_mob['hp'] -= damage
        self._add_log(f"⚔️ {player_data['character_name']} ataca ({damage} dano)!{'💥' if is_crit else ''}")

        if target_mob['hp'] <= 0:
            self._add_log(f"☠️ {target_mob['name']} foi derrotado!")
            reward = target_mob.get("reward", 0)
            if reward > 0: player_manager.add_item_to_inventory(player_data, 'fragmento_bravura', reward)
        else:
            monster_crit_params = criticals.get_crit_params_for_monster(target_mob)
            damage_taken, is_crit, is_mega = criticals.roll_damage(target_mob.get('attack', 5), player_stats.get('defense', 0), monster_crit_params)
            player_status = self.participants_status[user_id]
            player_status['hp'] -= damage_taken
            self._add_log(f"🩸 {target_mob['name']} contra-ataca ({damage_taken} dano)!{'💥' if is_crit else ''}")
            if player_status['hp'] <= 0:
                player_status['hp'] = 0
                self._add_log(f"💔 {player_data['character_name']} foi derrotado!")
        
        player_manager.save_player_data(user_id, player_data)
        
        if self.visual_mode: 
            return {"caption": self.get_battle_status_text()}
        else: 
            return {"text": self.get_battle_status_text()}

    def get_battle_status_text(self) -> str:
        """Retorna o texto de status formatado para o modo de batalha atual."""
        if self.visual_mode:
            return self._get_visual_caption()
        else:
            return self._get_text_mode_message()

    def _get_visual_caption(self) -> str:
        """Gera a legenda para o modo com imagem."""
        if not self.is_active: return "O evento terminou."
        header = f"🌊 **ONDA {self.current_wave_num}** 🌊\n"
        remaining = len(self.wave_mobs); total = self.total_mobs_in_wave
        progress_bar = create_progress_bar(total - remaining, total)
        status_linha = f"Monstros Restantes: {remaining}/{total}\n{progress_bar}"
        active_heroes = sum(1 for p in self.participants_status.values() if p['hp'] > 0)
        heroes_linha = f"Heróis em Batalha: {active_heroes}"
        log_str = "\n\n**Últimos Acontecimentos:**\n" + "\n".join(self.battle_log)
        return header + heroes_linha + "\n" + status_linha + log_str

    def _get_text_mode_message(self) -> str:
        """Gera o painel de texto completo."""
        if not self.is_active: return "O evento de Defesa do Reino terminou."
        monsters_dict = {f"mob_{i}": mob for i, mob in enumerate(self.wave_mobs)}
        dungeon_instance = {'combat_state': {'participants': self.participants_status, 'monsters': monsters_dict, 'battle_log': self.battle_log}}
        all_players_data = {pid: player_manager.get_player_data(pid) for pid in self.participants_status.keys()}
        return format_dungeon_combat_message(dungeon_instance, all_players_data)

# Instância única do gerenciador
event_manager = KingdomDefenseManager()

# Funções de job (agendador)
async def start_event_job(context: ContextTypes.DEFAULT_TYPE):
    if event_manager.is_active: return
    event_manager.start_event()

async def end_event_job(context: ContextTypes.DEFAULT_TYPE):
    if not event_manager.is_active: return
    event_manager.end_event()