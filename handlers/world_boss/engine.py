# handlers/world_boss/engine.py (VERSÃO COM SISTEMA DE LOOT)

import random
import logging
import asyncio
import html
from datetime import timedelta, datetime, time
from telegram.ext import ContextTypes, Application
from telegram.error import Forbidden

from modules import player_manager, game_data
from modules.combat import criticals
from modules.player.queries import iter_player_ids
from modules.player import stats as player_stats_engine

# <<< [MUDANÇA] Importa os dados de recompensas >>>
from modules.game_data.skills import SKILL_DATA
from modules.game_data.skins import SKIN_CATALOG

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
POSSIBLE_LOCATIONS = [
    "pradaria_inicial",
    "floresta_sombria",
    "pedreira_granito",
    "campos_linho",
    "pico_grifo",
    "mina_ferro",
    "forja_abandonada"
    "pantano_maldito"
]

# --- [NOVO] CONFIGURAÇÕES DE LOOT ---
ANNOUNCEMENT_CHAT_ID = -1002881364171
ANNOUNCEMENT_THREAD_ID = 24

SKILL_REWARD_POOL = [
    "guerreiro_corte_perfurante", "berserker_golpe_selvagem",
    "cacador_flecha_precisa", "monge_rajada_de_punhos",
    "mago_bola_de_fogo", "bardo_melodia_restauradora",
    "assassino_ataque_furtivo", "samurai_corte_iaijutsu"
]
SKILL_CHANCE = 5.0 # (5%)

SKIN_REWARD_POOL = [
    'guerreiro_armadura_negra', 'guerreiro_placas_douradas',
    'mago_traje_arcano', 'assassino_manto_espectral',
    'cacador_patrulheiro_elfico', 'berserker_pele_urso',
    'monge_quimono_dragao', 'bardo_traje_maestro',
    'samurai_armadura_shogun'
]
SKIN_CHANCE = 1.0 # (1%)

# --- CLASSE DE GESTÃO DO EVENTO ---
class WorldBossManager:
    def __init__(self):
        self.is_active = False
        self.boss_hp = 0
        self.boss_location = None
        self.damage_leaderboard = {}
        self.last_hitter_id = None # <<< [NOVO] Guarda quem deu o último golpe

    def start_event(self):
        if self.is_active:
            return {"error": "O evento do Demônio Dimensional já está ativo."}
        self.is_active = True
        self.boss_hp = BOSS_STATS["max_hp"]
        self.boss_location = random.choice(POSSIBLE_LOCATIONS)
        self.damage_leaderboard = {}
        self.last_hitter_id = None
        logger.info(f"EVENTO WORLD BOSS INICIADO! Demônio em '{self.boss_location}'.")
        return {"success": True, "location": self.boss_location}

    def end_event(self, reason: str) -> dict:
        """Apenas limpa o estado e retorna os dados da batalha."""
        if not self.is_active: 
            return {}
            
        logger.info(f"EVENTO WORLD BOSS FINALIZADO! Razão: {reason}")
        
        # Prepara os dados para a função de loot
        battle_results = {
            "leaderboard": self.damage_leaderboard.copy(),
            "last_hitter_id": self.last_hitter_id,
            "boss_defeated": (reason == "Boss derrotado")
        }
        
        # Limpa o estado
        self.is_active = False
        self.boss_hp = 0
        self.boss_location = None
        self.damage_leaderboard = {}
        self.last_hitter_id = None
        
        return battle_results

    async def process_attack(self, user_id: int, player_data: dict) -> dict:
        """Processa o ataque do jogador (agora async)."""
        if not self.is_active:
            return {"error": "O Demônio Dimensional não está ativo."}
        
        if player_data.get("current_location") != self.boss_location:
            region_name = (game_data.REGIONS_DATA.get(self.boss_location) or {}).get("display_name", self.boss_location)
            return {"error": f"Você precisa de estar em '{region_name}' para atacar o Demônio."}

        player_stats = await player_manager.get_player_total_stats(player_data)
        
        player_damage, is_crit, is_mega = criticals.roll_damage(player_stats, BOSS_STATS, {})
        
        if player_damage > self.boss_hp:
            player_damage = self.boss_hp
            
        self.boss_hp -= player_damage
        self.damage_leaderboard[user_id] = self.damage_leaderboard.get(user_id, 0) + player_damage
        self.last_hitter_id = user_id

        log_messages = []
        player_attack_log = f"Você ataca e causa {player_damage} de dano."
        if is_mega: player_attack_log += " 💥💥 MEGA CRÍTICO!"
        elif is_crit: player_attack_log += " 💥 DANO CRÍTICO!"
        log_messages.append(player_attack_log)
        
        # --- 👇 MUDANÇA IMPORTANTE AQUI 👇 ---
        if self.boss_hp <= 0:
            # O Boss morreu! Chama end_event para limpar o estado e pegar os resultados
            battle_results = self.end_event(reason="Boss derrotado")
            # Retorna os resultados para o handler poder distribuir o loot
            return {"boss_defeated": True, "log": "\n".join(log_messages), "battle_results": battle_results}
        # --- 👆 FIM DA MUDANÇA 👆 ---

        # --- CONTRA-ATAQUE DO BOSS ---
        dodge_chance = await player_stats_engine.get_player_dodge_chance(player_data)
        
        if random.random() < dodge_chance:
            log_messages.append("💨 Você se esquivou do contra-ataque do Demônio!")
        else:
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

# ======================================================
# --- [NOVO] FUNÇÕES DE LOOT E ANÚNCIO ---
# ======================================================

async def _send_dm_to_winner(context: ContextTypes.DEFAULT_TYPE, user_id: int, loot_messages: list[str]):
    """Envia uma mensagem privada para um vencedor."""
    if not loot_messages:
        return # Não ganhou nada de especial
    
    loot_str = "\n".join([f"• {item}" for item in loot_messages])
    message = (
        f"🎉 <b>Recompensas do Demônio Dimensional</b> 🎉\n\n"
        f"Parabéns! Por sua bravura na batalha, você recebeu:\n{loot_str}"
    )
    try:
        await context.bot.send_message(chat_id=user_id, text=message, parse_mode='HTML')
        await asyncio.sleep(0.1) # Anti-spam
        return True
    except Forbidden:
        logger.warning(f"[WB_LOOT] Não foi possível enviar DM para {user_id} (Bot bloqueado).")
        return False # Bot bloqueado
    except Exception as e:
        logger.warning(f"[WB_LOOT] Falha ao enviar DM para {user_id}: {e}")
        return False

async def distribute_loot_and_announce(context: ContextTypes.DEFAULT_TYPE, battle_results: dict):
    """
    Itera sobre os participantes, rola o loot, salva,
    envia DMs e envia o anúncio final.
    """
    leaderboard = battle_results.get("leaderboard", {})
    last_hitter_id = battle_results.get("last_hitter_id")
    boss_defeated = battle_results.get("boss_defeated", False)

    if not leaderboard:
        logger.info("[WB_LOOT] O evento terminou sem participantes. Nenhuma recompensa distribuída.")
        return

    logger.info(f"[WB_LOOT] Distribuindo loot para {len(leaderboard)} participantes...")

    # Lista para o anúncio público
    skill_winners_msg = []
    skin_winners_msg = []
    last_hit_msg = ""
    
    # Ordena o ranking para o anúncio
    sorted_ranking = sorted(leaderboard.items(), key=lambda item: item[1], reverse=True)
    top_3_msg = [
        f"🥇 { (await player_manager.get_player_data(uid)).get('character_name', 'Herói')} ({dmg:,} dano)" for uid, dmg in sorted_ranking[:3]
    ]

    # Itera sobre TODOS os participantes para rolar o loot
    for user_id, damage_dealt in leaderboard.items():
        if damage_dealt <= 0:
            continue
        
        try:
            pdata = await player_manager.get_player_data(user_id)
            if not pdata:
                continue

            player_name = pdata.get("character_name", f"ID {user_id}")
            loot_won_messages = [] # O que este jogador ganhou

            # 1. Rola a SKILL
            if random.random() * 100 <= SKILL_CHANCE:
                won_skill_id = random.choice(SKILL_REWARD_POOL)
                skill_info = SKILL_DATA.get(won_skill_id, {})
                skill_name = skill_info.get("display_name", won_skill_id)
                
                # Adiciona a skill (se já não a tiver)
                if won_skill_id not in pdata.get("skills", []):
                    pdata.setdefault("skills", []).append(won_skill_id)
                    loot_won_messages.append(f"✨ Habilidade Rara: [{skill_name}]")
                    skill_winners_msg.append(f"• {player_name} encontrou a <b>Skill [{skill_name}]</b>!")
                else:
                    loot_won_messages.append(f"✨ Você já possui a skill [{skill_name}].")

            # 2. Rola a SKIN
            if random.random() * 100 <= SKIN_CHANCE:
                won_skin_id = random.choice(SKIN_REWARD_POOL)
                skin_info = SKIN_CATALOG.get(won_skin_id, {})
                skin_name = skin_info.get("display_name", won_skin_id)
                
                # Adiciona a skin como um item
                player_manager.add_item_to_inventory(pdata, won_skin_id, 1)
                loot_won_messages.append(f"🎨 Skin Rara: [{skin_name}]")
                skin_winners_msg.append(f"• {player_name} obteve a <b>Skin [{skin_name}]</b>!")

            # 3. Salva o jogador (se ele ganhou algo)
            if loot_won_messages:
                await player_manager.save_player_data(user_id, pdata)
                # Envia a DM para o sortudo
                await _send_dm_to_winner(context, user_id, loot_won_messages)

            # 4. Verifica o Último Golpe
            if user_id == last_hitter_id:
                last_hit_msg = f"💥 <b>Último Golpe:</b> {player_name}"

        except Exception as e:
            logger.error(f"[WB_LOOT] Erro ao processar loot para {user_id}: {e}", exc_info=True)

    # --- 5. Monta e Envia o Anúncio Global ---
    if not boss_defeated:
        announcement_title = "👹 <b>O Demônio Dimensional Escapou!</b> 👹"
        announcement_body = "O monstro era muito poderoso e retirou-se para a sua dimensão antes de ser derrotado.\n\nMais sorte da próxima vez!"
    else:
        announcement_title = "🎉 <b>O Demônio Dimensional Foi Derrotado!</b> 🎉"
        announcement_body = "Graças à bravura dos heróis, a ameaça foi contida!\n\n<b>Ranking de Dano (Top 3):</b>\n" + "\n".join(top_3_msg)
        
        if last_hit_msg:
            announcement_body += f"\n{last_hit_msg}"
        
        if skin_winners_msg:
            announcement_body += "\n\n🎨 <b>Recompensas Raras (Skins):</b>\n" + "\n".join(skin_winners_msg)
        
        if skill_winners_msg:
            announcement_body += "\n\n✨ <b>Recompensas Raras (Skills):</b>\n" + "\n".join(skill_winners_msg)
            
        if not skin_winners_msg and not skill_winners_msg:
            announcement_body += "\n\n<i>Nenhum item raro foi encontrado desta vez.</i>"

    final_announcement = f"{announcement_title}\n\n{announcement_body}"
    
    try:
        await context.bot.send_message(
            chat_id=ANNOUNCEMENT_CHAT_ID,
            message_thread_id=ANNOUNCEMENT_THREAD_ID,
            text=final_announcement,
            parse_mode="HTML"
        )
        logger.info(f"Anúncio de loot do World Boss enviado para o canal.")
    except Exception as e:
        logger.error(f"Falha ao enviar anúncio de loot do World Boss: {e}", exc_info=True)


# --- FUNÇÕES DE JOB ---
async def end_world_boss_job(context: ContextTypes.DEFAULT_TYPE):
    """Job que finaliza o evento (chamado pelo agendador se o tempo acabar)."""
    logger.info("Job 'end_world_boss_job' iniciado (Tempo Esgotado).")
    
    # Pega os resultados da batalha
    battle_results = world_boss_manager.end_event(reason="Tempo esgotado")
    
    # Distribui o loot (ou anuncia a fuga)
    await distribute_loot_and_announce(context, battle_results)
    
    anuncio = "O Demônio Dimensional era demasiado poderoso e desapareceu de volta para a sua dimensão..."
    async for user_id, _ in player_manager.iter_players(filter_query={}):
        try:
            await context.bot.send_message(chat_id=user_id, text=anuncio)
            await asyncio.sleep(0.1)
        except Exception: 
            continue

async def broadcast_boss_announcement(application: Application, location_key: str):
    """Envia o anúncio do World Boss para todos os jogadores."""
    location_name = (game_data.REGIONS_DATA.get(location_key) or {}).get("display_name", location_key)
    anuncio = (
        f"🚨 **ALERTA GLOBAL** 🚨\n\n"
        f"Um poderoso **Demônio Dimensional** surgiu do nada!\n\n"
        f"Ele foi visto pela última vez em <b>{location_name}</b>. O reino precisa da vossa ajuda para o derrotar!"
    )
    
    total_jogadores = 0
    async for user_id, _ in player_manager.iter_players(filter_query={}):
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
    if world_boss_manager.is_active: 
        logger.warning("iniciar_world_boss_job foi chamado, mas o evento já estava ativo.")
        return

    result = world_boss_manager.start_event()
    
    if result.get("success"):
        await broadcast_boss_announcement(context.application, result["location"])
        
        duration_hours = context.job.data.get("duration_hours", 1)
        
        context.job_queue.run_once(end_world_boss_job, when=timedelta(hours=duration_hours))
        logger.info(f"Job de finalização do World Boss agendado para daqui a {duration_hours} hora(s).")

async def agendador_mestre_do_boss(context: ContextTypes.DEFAULT_TYPE):
    """(Esta é a função ANTIGA) Agenda o boss para uma hora aleatória HOJE."""
    delay_em_segundos = random.randint(8 * 3600, 22 * 3600)
    
    job_data = {"duration_hours": 1}
    context.job_queue.run_once(iniciar_world_boss_job, when=delay_em_segundos, data=job_data)
    
    hora_agendada = (datetime.now() + timedelta(seconds=delay_em_segundos)).strftime("%H:%M")
    logger.info(f"Agendador Mestre: O próximo Demônio Dimensional foi agendado para hoje às {hora_agendada}.")