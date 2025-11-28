# handlers/world_boss/engine.py (VERSÃO FINAL OTIMIZADA)

import random
import logging
import asyncio
import html
from datetime import timedelta, datetime, time
from telegram.ext import ContextTypes, Application
from telegram.error import Forbidden, TelegramError

from modules import player_manager, game_data
from modules.combat import criticals
from modules.player import stats as player_stats_engine

# Dados de Recompensa (Skills e Skins)
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
    "pradaria_inicial", "floresta_sombria", "pedreira_granito",
    "campos_linho", "pico_grifo", "mina_ferro",
    "forja_abandonada", "pantano_maldito"
]

# --- CONFIGURAÇÕES DE LOOT ---
# Sugestão: Mover esses IDs para um arquivo de configuração (.env) no futuro
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
        self.last_hitter_id = None

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
        """Limpa o estado e retorna os resultados da batalha."""
        if not self.is_active: 
            return {}
            
        logger.info(f"EVENTO WORLD BOSS FINALIZADO! Razão: {reason}")
        
        battle_results = {
            "leaderboard": self.damage_leaderboard.copy(),
            "last_hitter_id": self.last_hitter_id,
            "boss_defeated": (reason == "Boss derrotado")
        }
        
        # Reset
        self.is_active = False
        self.boss_hp = 0
        self.boss_location = None
        self.damage_leaderboard = {}
        self.last_hitter_id = None
        
        return battle_results

    async def process_attack(self, user_id: int, player_data: dict) -> dict:
        """Processa o ataque do jogador."""
        if not self.is_active:
            return {"error": "O Demônio Dimensional não está ativo."}
        
        if player_data.get("current_location") != self.boss_location:
            region_name = (game_data.REGIONS_DATA.get(self.boss_location) or {}).get("display_name", self.boss_location)
            return {"error": f"Você precisa estar em '{region_name}' para atacar o Demônio."}

        player_stats = await player_manager.get_player_total_stats(player_data)
        
        # Rola o dano do jogador contra o boss
        player_damage, is_crit, is_mega = criticals.roll_damage(player_stats, BOSS_STATS, {})
        
        # Capa o dano para não exceder a vida restante do boss
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
        
        # Checa morte do Boss
        if self.boss_hp <= 0:
            battle_results = self.end_event(reason="Boss derrotado")
            return {"boss_defeated": True, "log": "\n".join(log_messages), "battle_results": battle_results}

        # Contra-ataque do Boss
        dodge_chance = await player_stats_engine.get_player_dodge_chance(player_data)
        
        if random.random() < dodge_chance:
            log_messages.append("💨 Você se esquivou do contra-ataque do Demônio!")
        else:
            boss_damage, boss_is_crit, boss_is_mega = criticals.roll_damage(BOSS_STATS, player_stats, {})
            boss_attack_log = f"O Demônio contra-ataca e causa {boss_damage} de dano em você."
            if boss_is_mega: boss_attack_log += " ‼️ MEGA CRÍTICO!"
            elif boss_is_crit: boss_attack_log += " ❗️ DANO CRÍTICO!"
            log_messages.append(boss_attack_log)
            
            # Aplica dano ao jogador (opcional, se quiser que o boss tire vida real)
            # await player_actions.take_damage(player_data, boss_damage)
            
        return {"success": True, "log": "\n".join(log_messages)}

    def get_status_text(self) -> str:
        if not self.is_active: return "Não há nenhum Demônio Dimensional ativo no momento."
        percent_hp = (self.boss_hp / BOSS_STATS["max_hp"]) * 100
        return (
            f"👹 **Demônio Dimensional**\n"
            f"📍 Localização: {self.boss_location.replace('_', ' ').title()}\n"
            f"❤️ HP: {self.boss_hp:,}/{BOSS_STATS['max_hp']:,} ({percent_hp:.2f}%)"
        )

# Instância Global
world_boss_manager = WorldBossManager()

# ======================================================
# --- FUNÇÕES DE LOOT E ANÚNCIO ---
# ======================================================

async def _send_dm_to_winner(context: ContextTypes.DEFAULT_TYPE, user_id: int, loot_messages: list[str]):
    """Envia DM para um vencedor com suas recompensas."""
    if not loot_messages: return
    
    loot_str = "\n".join([f"• {item}" for item in loot_messages])
    message = (
        f"🎉 <b>Recompensas do Demônio Dimensional</b> 🎉\n\n"
        f"Parabéns! Por sua bravura na batalha, você recebeu:\n{loot_str}"
    )
    try:
        await context.bot.send_message(chat_id=user_id, text=message, parse_mode='HTML')
        await asyncio.sleep(0.1) 
        return True
    except Forbidden:
        logger.warning(f"Não foi possível enviar DM para {user_id} (Bloqueado).")
        return False
    except Exception as e:
        logger.error(f"Erro ao enviar DM para {user_id}: {e}")
        return False

async def distribute_loot_and_announce(context: ContextTypes.DEFAULT_TYPE, battle_results: dict):
    """Distribui loot e anuncia resultados."""
    leaderboard = battle_results.get("leaderboard", {})
    last_hitter_id = battle_results.get("last_hitter_id")
    boss_defeated = battle_results.get("boss_defeated", False)

    if not leaderboard:
        logger.info("[WB_LOOT] Sem participantes. Abortando.")
        return

    # 1. Carrega dados dos jogadores (Cache Local)
    participant_data = {}
    for user_id in leaderboard.keys():
        try:
            pdata = await player_manager.get_player_data(user_id)
            if pdata: participant_data[user_id] = pdata
        except Exception: pass
    
    if not participant_data: return

    skill_winners_msg = []
    skin_winners_msg = []
    last_hit_msg = ""
    
    sorted_ranking = sorted(leaderboard.items(), key=lambda item: item[1], reverse=True)
    
    # 2. Constrói Top 3 (CORRIGIDO AS MEDALHAS)
    top_3_msg = []
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, dmg) in enumerate(sorted_ranking[:3]):
        pdata = participant_data.get(uid)
        name = html.escape(pdata.get('character_name', 'Herói')) if pdata else "Herói Desconhecido"
        medal = medals[i] if i < 3 else "🏅"
        top_3_msg.append(f"{medal} {name} ({dmg:,} dano)")

    # 3. Distribui Loot
    for user_id, pdata in participant_data.items():
        if leaderboard.get(user_id, 0) <= 0: continue
        
        try:
            player_name = pdata.get("character_name", f"ID {user_id}")
            loot_won_messages = []
            player_mudou = False

            # Roll SKILL (5%)
            if random.random() * 100 <= SKILL_CHANCE:
                won_skill_id = random.choice(SKILL_REWARD_POOL)
                won_item_id = f"tomo_{won_skill_id}" 
                
                # Busca segura no ITEMS_DATA
                item_info = game_data.ITEMS_DATA.get(won_item_id) or {}
                display_name = item_info.get("display_name", won_skill_id)

                player_manager.add_item_to_inventory(pdata, won_item_id, 1)
                loot_won_messages.append(f"📚 Item Raro: [{display_name}]")
                skill_winners_msg.append(f"• {html.escape(player_name)} obteve o <b>{display_name}</b>!")
                player_mudou = True

            # Roll SKIN (1%)
            if random.random() * 100 <= SKIN_CHANCE:
                won_skin_id = random.choice(SKIN_REWARD_POOL)
                won_item_id = f"caixa_{won_skin_id}"
                
                # Busca segura no ITEMS_DATA
                item_info = game_data.ITEMS_DATA.get(won_item_id) or {}
                display_name = item_info.get("display_name", won_skin_id)
                
                player_manager.add_item_to_inventory(pdata, won_item_id, 1)
                loot_won_messages.append(f"🎨 Item Raro: [{display_name}]")
                skin_winners_msg.append(f"• {html.escape(player_name)} obteve a <b>{display_name}</b>!")
                player_mudou = True

            if player_mudou:
                await player_manager.save_player_data(user_id, pdata)
            
            if loot_won_messages:
                await _send_dm_to_winner(context, user_id, loot_won_messages)

            if user_id == last_hitter_id:
                last_hit_msg = f"💥 <b>Último Golpe:</b> {html.escape(player_name)}"

        except Exception as e:
            logger.error(f"[WB_LOOT] Erro no player {user_id}: {e}")

    # 4. Anúncio Global
    if not boss_defeated:
        title = "👹 <b>O Demônio Dimensional Escapou!</b> 👹"
        body = "O monstro era muito poderoso e retirou-se.\n\nMais sorte da próxima vez!"
    else:
        title = "🎉 <b>O Demônio Dimensional Foi Derrotado!</b> 🎉"
        body = "Graças à bravura dos heróis, a ameaça foi contida!\n\n<b>Ranking de Dano (Top 3):</b>\n" + "\n".join(top_3_msg)
        
        if last_hit_msg: body += f"\n{last_hit_msg}"
        if skin_winners_msg: body += "\n\n🎨 <b>Skins Encontradas:</b>\n" + "\n".join(skin_winners_msg)
        if skill_winners_msg: body += "\n\n✨ <b>Skills Encontradas:</b>\n" + "\n".join(skill_winners_msg)
        
        if not skin_winners_msg and not skill_winners_msg:
            body += "\n\n<i>Nenhum item raro foi encontrado desta vez.</i>"

    try:
        await context.bot.send_message(
            chat_id=ANNOUNCEMENT_CHAT_ID,
            message_thread_id=ANNOUNCEMENT_THREAD_ID,
            text=f"{title}\n\n{body}",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Erro ao enviar anúncio no canal: {e}")

# --- JOBS ---
async def end_world_boss_job(context: ContextTypes.DEFAULT_TYPE):
    """Finaliza o evento por tempo."""
    battle_results = world_boss_manager.end_event(reason="Tempo esgotado")
    await distribute_loot_and_announce(context, battle_results)
    
    # Notifica todos os players (Otimizado)
    async for user_id, _ in player_manager.iter_players():
        try:
            await context.bot.send_message(chat_id=user_id, text="O tempo acabou! O Demônio Dimensional desapareceu...")
            await asyncio.sleep(0.05) # Delay reduzido para ser mais rápido
        except (Forbidden, TelegramError):
            continue # Ignora usuários que bloquearam
        except Exception: 
            continue

async def broadcast_boss_announcement(application: Application, location_key: str):
    """Anuncia início para todos."""
    location_name = (game_data.REGIONS_DATA.get(location_key) or {}).get("display_name", location_key)
    anuncio = f"🚨 **ALERTA GLOBAL** 🚨\nUm Demônio Dimensional surgiu em <b>{location_name}</b>!"
    
    async for user_id, _ in player_manager.iter_players():
        try:
            await application.bot.send_message(chat_id=user_id, text=anuncio, parse_mode='HTML')
            await asyncio.sleep(0.05) # Delay reduzido
        except (Forbidden, TelegramError):
            continue # Ignora usuários que bloquearam
        except Exception: 
            continue

async def iniciar_world_boss_job(context: ContextTypes.DEFAULT_TYPE):
    """Inicia o evento."""
    if world_boss_manager.is_active: return

    result = world_boss_manager.start_event()
    if result.get("success"):
        await broadcast_boss_announcement(context.application, result["location"])
        
        duration = context.job.data.get("duration_hours", 1)
        context.job_queue.run_once(end_world_boss_job, when=timedelta(hours=duration))

async def agendador_mestre_do_boss(context: ContextTypes.DEFAULT_TYPE):
    """Agenda para hoje."""
    delay = random.randint(8 * 3600, 22 * 3600)
    context.job_queue.run_once(iniciar_world_boss_job, when=delay, data={"duration_hours": 1})