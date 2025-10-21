# handlers/world_boss/engine.py (VERSÃO COMPLETA E CORRIGIDA)

import random
import logging
import asyncio
from datetime import timedelta, datetime, time
from telegram.ext import ContextTypes, Application
from modules import player_manager, game_data

from modules.combat import criticals
from modules.player.queries import iter_player_ids
from modules.player import stats as player_stats_engine
logger = logging.getLogger(__name__)

# --- CONFIGURAÇÕES DO BOSS ---
BOSS_STATS = {
    "name": "Demônio Dimensional",
    "max_hp": 10000,
    "attack": 50,
    "defense": 30,
    "luck": 50,
    "media_key": "demonio_dimensional_media"
}

# Lista de chaves das regiões onde o boss pode aparecer
POSSIBLE_LOCATIONS = [
    "floresta_sombria",
    "pedreira_granito",
    "mina_ferro",
]

# --- CLASSE DE GESTÃO DO EVENTO ---
class WorldBossManager:
    def __init__(self):
        self.is_active = False
        self.boss_hp = 0
        self.boss_location = None
        self.damage_leaderboard = {}

    def start_event(self):
        if self.is_active:
            return {"error": "O evento do Demônio Dimensional já está ativo."}
        self.is_active = True
        self.boss_hp = BOSS_STATS["max_hp"]
        self.boss_location = random.choice(POSSIBLE_LOCATIONS)
        self.damage_leaderboard = {}
        logger.info(f"EVENTO WORLD BOSS INICIADO! Demônio em '{self.boss_location}'.")
        return {"success": True, "location": self.boss_location}

    def end_event(self, reason: str):
        if not self.is_active: return
        logger.info(f"EVENTO WORLD BOSS FINALIZADO! Razão: {reason}")
        # TODO: Lógica de recompensas
        self.is_active = False
        self.boss_hp = 0
        self.boss_location = None
        self.damage_leaderboard = {}

    # Em handlers/world_boss/engine.py
# Substitui a função process_attack inteira

def process_attack(self, user_id: int, player_data: dict) -> dict:
    if not self.is_active:
        return {"error": "O Demônio Dimensional não está ativo."}
    
    if player_data.get("current_location") != self.boss_location:
        # Acessa o nome da região a partir do game_data para uma mensagem mais amigável
        region_name = (game_data.REGIONS_DATA.get(self.boss_location) or {}).get("display_name", self.boss_location)
        return {"error": f"Você precisa de estar em '{region_name}' para atacar o Demônio."}

    # --- ATAQUE DO JOGADOR ---
    player_stats = player_manager.get_player_total_stats(player_data)
    player_damage, is_crit, is_mega = criticals.roll_damage(player_stats, BOSS_STATS, {})
    self.boss_hp -= player_damage
    self.damage_leaderboard[user_id] = self.damage_leaderboard.get(user_id, 0) + player_damage

    # Prepara o log de batalha
    log_messages = []
    player_attack_log = f"Você ataca e causa {player_damage} de dano."
    if is_mega: player_attack_log += " 💥💥 MEGA CRÍTICO!"
    elif is_crit: player_attack_log += " 💥 DANO CRÍTICO!"
    log_messages.append(player_attack_log)
    
    # Verifica se o boss foi derrotado
    if self.boss_hp <= 0:
        self.end_event(reason="Boss derrotado")
        return {"boss_defeated": True, "log": "\n".join(log_messages)}

    # --- NOVO: CONTRA-ATAQUE DO BOSS ---
    dodge_chance = player_stats_engine.get_player_dodge_chance(player_data)
    if random.random() < dodge_chance:
        log_messages.append("💨 Você se esquivou do contra-ataque do Demônio!")
    else:
        # O boss ataca o jogador
        boss_damage, boss_is_crit, boss_is_mega = criticals.roll_damage(BOSS_STATS, player_stats, {})
        boss_attack_log = f"O Demônio contra-ataca e causa {boss_damage} de dano em você."
        if boss_is_mega: boss_attack_log += " ‼️ MEGA CRÍTICO!"
        elif boss_is_crit: boss_attack_log += " ❗️ DANO CRÍTICO!"
        log_messages.append(boss_attack_log)
        
    return {"success": True, "log": "\n".join(log_messages)}

    def get_status_text(self) -> str:
        if not self.is_active: return "Não há nenhum Demônio Dimensional ativo no momento."
        percent_hp = (self.boss_hp / BOSS_STATS["max_hp"]) * 100
        return (
            f"👹 **Demônio Dimensional**\n"
            f"📍 Localização: {self.boss_location.replace('_', ' ').title()}\n"
            f"❤️ HP: {self.boss_hp:,}/{BOSS_STATS['max_hp']:,} ({percent_hp:.2f}%)"
        )

# --- INSTÂNCIA ÚNICA (ESSENCIAL) ---
world_boss_manager = WorldBossManager()

# --- FUNÇÕES DE JOB (A PARTE QUE PROVAVELMENTE FALTOU) ---
async def end_world_boss_job(context: ContextTypes.DEFAULT_TYPE):
    world_boss_manager.end_event(reason="Tempo esgotado")
    anuncio = "O Demônio Dimensional era demasiado poderoso e desapareceu de volta para a sua dimensão..."
    for user_id in iter_player_ids():
        try:
            await context.bot.send_message(chat_id=user_id, text=anuncio)
            await asyncio.sleep(0.1)
        except Exception: continue

async def broadcast_boss_announcement(application: Application, location_key: str):
    """Envia o anúncio do World Boss para todos os jogadores."""
    location_name = (game_data.REGIONS_DATA.get(location_key) or {}).get("display_name", location_key)
    anuncio = (
        f"🚨 **ALERTA GLOBAL** 🚨\n\n"
        f"Um poderoso **Demônio Dimensional** surgiu do nada!\n\n"
        f"Ele foi visto pela última vez em <b>{location_name}</b>. O reino precisa da vossa ajuda para o derrotar!"
    )
    
    total_jogadores = 0
    for user_id in iter_player_ids():
        try:
            await application.bot.send_message(chat_id=user_id, text=anuncio, parse_mode='HTML')
            total_jogadores += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.warning(f"Falha ao enviar anúncio do boss para {user_id}: {e}")
            continue
    logger.info(f"Anúncio do World Boss enviado para {total_jogadores} jogadores.")

async def iniciar_world_boss_job(context: ContextTypes.DEFAULT_TYPE):
    """Job que efetivamente inicia o evento e chama a função de anúncio."""
    if world_boss_manager.is_active: return

    result = world_boss_manager.start_event()
    
    if result.get("success"):
        # Agora, apenas CHAMA a função de anúncio que criámos
        await broadcast_boss_announcement(context.application, result["location"])
        
        # Agenda o fim do evento
        context.job_queue.run_once(end_world_boss_job, when=timedelta(hours=1))

async def iniciar_world_boss_job(context: ContextTypes.DEFAULT_TYPE):
    if world_boss_manager.is_active: return
    result = world_boss_manager.start_event()
    location_name = result.get('location', 'local desconhecido').replace("_", " ").title()
    anuncio = (
        f"🚨 **ALERTA GLOBAL** 🚨\n\n"
        f"Um poderoso **Demônio Dimensional** surgiu do nada!\n\n"
        f"Ele foi visto pela última vez em <b>{location_name}</b>. O reino precisa da vossa ajuda para o derrotar!"
    )
    total_jogadores = 0
    for user_id in iter_player_ids():
        try:
            await context.bot.send_message(chat_id=user_id, text=anuncio, parse_mode='HTML')
            total_jogadores += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.warning(f"Falha ao enviar anúncio do boss para {user_id}: {e}")
            continue
    logger.info(f"Anúncio do World Boss enviado para {total_jogadores} jogadores.")
    context.job_queue.run_once(end_world_boss_job, when=timedelta(hours=1))

async def agendador_mestre_do_boss(context: ContextTypes.DEFAULT_TYPE):
    delay_em_segundos = random.randint(8 * 3600, 22 * 3600)
    context.job_queue.run_once(iniciar_world_boss_job, when=delay_em_segundos)
    hora_agendada = (datetime.now() + timedelta(seconds=delay_em_segundos)).strftime("%H:%M")
    logger.info(f"Agendador Mestre: O próximo Demônio Dimensional foi agendado para hoje às {hora_agendada}.")