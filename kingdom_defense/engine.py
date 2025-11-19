# Arquivo: kingdom_defense/engine.py
# (VERSÃO CORRIGIDA - PASSANDO 'attacker_pdata' PARA O COMBAT_ENGINE)

import random
import logging
from typing import Optional, Dict, Any # <-- ADICIONADO PARA _get_player_skill_data_by_rarity
from telegram.ext import ContextTypes
from .data import WAVE_DEFINITIONS
from modules import player_manager
from modules.player import stats as player_stats_engine
from . import leaderboard
from modules.combat import criticals
from modules.game_data import items as game_items
from modules.game_data.monsters import MONSTERS_DATA
from modules.game_data.skills import SKILL_DATA 
from modules.combat import combat_engine

logger = logging.getLogger(__name__)

# ================================================
# INÍCIO: FUNÇÃO AUXILIAR DE SKILL (COPIADA)
# ================================================
# (Necessária para ler custos/efeitos de skills de raridade no 'process_player_skill')
def _get_player_skill_data_by_rarity(pdata: dict, skill_id: str) -> Optional[dict]:
    """Busca os dados da skill mesclando com a raridade."""
    base_skill = SKILL_DATA.get(skill_id)
    if not base_skill: return None
    if "rarity_effects" not in base_skill: return base_skill

    player_skills = pdata.get("skills", {})
    rarity = "comum"
    if isinstance(player_skills, dict):
        player_skill_instance = player_skills.get(skill_id)
        if player_skill_instance:
            rarity = player_skill_instance.get("rarity", "comum")

    merged_data = base_skill.copy()
    rarity_data = base_skill["rarity_effects"].get(rarity, base_skill["rarity_effects"].get("comum", {}))
    merged_data.update(rarity_data)
    return merged_data

# ================================================
# FIM: FUNÇÃO AUXILIAR DE SKILL
# ================================================


def _find_monster_template(mob_id: str) -> dict | None:
    if not mob_id: return None
    for region_monsters in MONSTERS_DATA.values():
        for monster in region_monsters:
            if monster.get("id") == mob_id:
                return monster.copy()
    return None

class KingdomDefenseManager:
    def __init__(self):
        self.wave_definitions = WAVE_DEFINITIONS
        self.is_active = False
        self.reset_event()

    async def start_event(self):
        """Inicia o evento de defesa do reino a partir da Onda 1."""
        if self.is_active: return {"error": "O evento já está ativo."}
        self.reset_event()
        self.is_active = True
        await self.setup_wave(1) 
        logger.info("Evento de Defesa do Reino iniciado na Onda 1.")
        return {"success": "Evento iniciado!"}
    
    def store_player_message_id(self, user_id, message_id):
        """Armazena o message_id da batalha para um jogador."""
        if user_id in self.player_states:
            self.player_states[user_id]['message_id'] = message_id
            logger.info(f"Armazenado message_id {message_id} para jogador {user_id}")
        else:
            logger.warning(f"Tentativa de armazenar message_id para {user_id} sem estado de batalha.")

    async def end_event(self, context: ContextTypes.DEFAULT_TYPE | None = None): # Adiciona context para notificação
        logger.info("Encerrando evento de Defesa do Reino...")
        top_scorer = None
        max_damage = 0
        
        # Copia as chaves antes de iterar, pois _promote_next_player pode modificar o set
        all_participants = list(self.active_fighters) + self.waiting_queue
        
        for user_id in all_participants:
            state = self.player_states.get(user_id)
            if not state: continue

            # Resetar o estado do jogador para 'idle'
            try:
                # <<< CORREÇÃO 1: Adiciona await >>>
                player_data = await player_manager.get_player_data(user_id)
                if player_data:
                    player_data["player_state"] = {"action": "idle"}
                    # <<< CORREÇÃO 2: Adiciona await >>>
                    await player_manager.save_player_data(user_id, player_data)
                    
                    # Lógica do placar (movida para dentro do 'if player_data')
                    damage_dealt = state.get('damage_dealt', 0)
                    if damage_dealt > max_damage:
                        max_damage = damage_dealt
                        top_scorer = {
                            "user_id": user_id,
                            "character_name": player_data.get("character_name", "Herói"),
                            "damage": max_damage
                        }
                    
                    # Notifica o jogador que o evento acabou (opcional, mas bom)
                    if context:
                        try:
                            await context.bot.send_message(chat_id=user_id, text="⚔️ O evento de Defesa do Reino foi encerrado! ⚔️")
                        except Exception:
                            pass # Ignora se o bot for bloqueado
                        
            except Exception as e:
                logger.error(f"Erro ao finalizar evento/resetar estado para {user_id}: {e}")

        if top_scorer:
            # Assumindo que leaderboard.update_top_score é síncrono
            leaderboard.update_top_score(
                user_id=top_scorer["user_id"],
                character_name=top_scorer["character_name"],
                damage=top_scorer["damage"]
            )
            
        self.reset_event() # Síncrono
        return {"success": "Evento encerrado."}

    def reset_event(self):
        self.is_active = False
        self.current_wave = 0
        self.boss_mode_active = False
        self.boss_global_hp = 0
        self.boss_max_hp = 0
        self.active_fighters = set()
        self.waiting_queue = []
        self.player_states = {}
        self.current_wave_mob_pool = []
        self.total_mobs_in_wave = 0
        self.max_concurrent_fighters = 10
        self.boss_attack_counter = 0

    async def start_event_at_wave(self, wave_number: int):
        """Inicia um evento de teste numa onda específica."""
        if self.is_active: return {"error": "O evento já está ativo."}
        if wave_number not in self.wave_definitions: return {"error": f"A Onda {wave_number} não existe."}
        logger.info(f"Iniciando evento de teste na Onda {wave_number}.")
        self.reset_event() # Reset é síncrono
        self.is_active = True
        await self.setup_wave(wave_number) # <--- NECESSITA AWAIT
        return {"success": f"Evento de teste iniciado na Onda {wave_number}!"}
    
    async def setup_wave(self, wave_number: int):
        """Configura a próxima onda ou termina o evento se não houver mais ondas."""
        if wave_number not in self.wave_definitions:
            logger.info(f"Onda {wave_number} não encontrada. Encerrando o evento.")
            await self.end_event()
            return 

        logger.info(f"Configurando Onda {wave_number}...")
        self.current_wave = wave_number
        self.boss_mode_active = False
        limite_base = 5
        vagas_por_onda = 5
        self.max_concurrent_fighters = limite_base + (vagas_por_onda * self.current_wave)
        if self.max_concurrent_fighters > 50:
            self.max_concurrent_fighters = 50

        wave_data = self.wave_definitions[wave_number]
        self.current_wave_mob_pool = wave_data.get('mob_pool', []).copy()
        self.total_mobs_in_wave = len(self.current_wave_mob_pool)
        logger.info(f"Onda {wave_number} configurada com {self.total_mobs_in_wave} monstros e {self.max_concurrent_fighters} vagas.")

    def get_player_status(self, user_id):
        if user_id in self.active_fighters: return "active"
        if user_id in self.waiting_queue: return "waiting"
        return "not_in_event"

    async def add_player_to_event(self, user_id, player_data):
        if not self.is_active:
            logger.warning(f"Jogador {user_id} tentou entrar em um evento inativo.")
            return "event_inactive"
        status = self.get_player_status(user_id)
        if status != "not_in_event": return status
        
        if len(self.active_fighters) < self.max_concurrent_fighters:
            self.active_fighters.add(user_id)
            await self._setup_player_battle_state(user_id, player_data) 
            return "active"
        else:
            if user_id not in self.waiting_queue:
                self.waiting_queue.append(user_id)
            return "waiting"

    async def _setup_player_battle_state(self, user_id, player_data):
        # Obtém as estatísticas totais
        total_stats = await player_manager.get_player_total_stats(player_data) 
        current_wave_info = self.wave_definitions[self.current_wave]
        
        # Lógica do Monstro (Mantida)
        mob_template = None
        if not self.boss_mode_active:
            if self.current_wave_mob_pool:
                mob_id = self.current_wave_mob_pool[0] 
                mob_template = _find_monster_template(mob_id)
        else:
            boss_id = current_wave_info.get('boss_id')
            mob_template = _find_monster_template(boss_id)
            
        if not mob_template:
            logger.error(f"ERRO CRÍTICO: Monstro não encontrado (Onda {self.current_wave}).")
            return

        mob_instance = mob_template.copy()
        mob_instance['active_effects'] = []
        if self.boss_mode_active:
            mob_instance.update({'hp': self.boss_global_hp, 'max_hp': self.boss_max_hp, 'is_boss': True})
        else:
            mob_instance.update({'max_hp': mob_instance['hp'], 'is_boss': False})

        # --- HP DO JOGADOR ---
        max_hp = int(total_stats.get('max_hp', 100))
        # Se o jogador já está na memória do evento, mantém o HP atual.
        if user_id in self.player_states:
             current_hp = self.player_states[user_id].get('player_hp', max_hp)
        else:
             # Se é novo, pega do banco de dados (ou full se não tiver)
             current_hp = int(player_data.get('current_hp', max_hp))
        current_hp = min(current_hp, max_hp)

        # --- MP DO JOGADOR (CORREÇÃO AQUI) ---
        max_mp = int(total_stats.get('max_mana', 50))
        
        if user_id in self.player_states:
             # Se já está lutando, mantém o MP que tinha
             current_mp = self.player_states[user_id].get('player_mp', max_mp)
        else:
             # Se acabou de entrar, pega do banco de dados ('current_mp')
             current_mp = int(player_data.get('current_mp', max_mp))
        
        current_mp = min(current_mp, max_mp)

        # --- DADOS EXTRAS ---
        current_damage = self.player_states.get(user_id, {}).get('damage_dealt', 0)
        current_message_id = self.player_states.get(user_id, {}).get('message_id', None)
        saved_cooldowns = self.player_states.get(user_id, {}).get('skill_cooldowns', {})

        self.player_states[user_id] = {
            'player_hp': current_hp,
            'player_max_hp': max_hp,
            'player_mp': current_mp,
            'player_max_mp': max_mp,
            'current_mob': mob_instance,
            'damage_dealt': current_damage,
            'active_effects': [],
            'message_id': current_message_id,
            'skill_cooldowns': saved_cooldowns
        }
        logger.info(f"Jogador {user_id}: HP {current_hp}/{max_hp}, MP {current_mp}/{max_mp}")


    async def _promote_next_player(self):
        if self.waiting_queue and len(self.active_fighters) < self.max_concurrent_fighters:
            next_player_id = self.waiting_queue.pop(0)
            player_data = await player_manager.get_player_data(next_player_id)
            if player_data:
                self.active_fighters.add(next_player_id)
                await self._setup_player_battle_state(next_player_id, player_data) 
                logger.info(f"Jogador {next_player_id} promovido da fila para a batalha.")
            else:
                logger.warning(f"Jogador {next_player_id} estava na fila mas não foi encontrado (get_player_data retornou None).")

    async def _resolve_turn(self, user_id: int, player_data: dict, logs: list) -> dict:
        """
        Função auxiliar que resolve o final de um turno após o jogador causar dano.
        Verifica a derrota do monstro e, se não, executa o contra-ataque.
        """
        player_state = self.player_states[user_id]
        mob = player_state['current_mob']
        is_boss_fight = mob.get('is_boss', False)

        player_full_stats = await player_manager.get_player_total_stats(player_data)

        mob_hp = self.boss_global_hp if is_boss_fight else mob['hp']

        # --- MONSTRO DERROTADO ---
        if mob_hp <= 0:
            logs.append(f"☠️ {mob['name']} foi derrotado!")
            
            if is_boss_fight:
                logs.append(f"🎉 A ONDA {self.current_wave} FOI CONCLUÍDA! 🎉")
                await self.setup_wave(self.current_wave + 1)
                if not self.is_active:
                    return {"event_over": True, "action_log": "\n".join(logs)}
            else:
                # --- GERA RECOMPENSA (LOOT) ---
                reward_amount = 1
                item_id = 'fragmento_bravura'
                player_manager.add_item_to_inventory(player_data, item_id, reward_amount)
                
                item_info = game_items.ITEMS_DATA.get(item_id, {})
                item_name = item_info.get('display_name', 'Fragmento de Bravura')
                
                loot_msg = f"💎 𝐋𝐨𝐨𝐭: {reward_amount}x {item_name}"
                logs.append(loot_msg) 

                # ✅ CORREÇÃO CRUCIAL: Remove o monstro morto da piscina global
                if self.current_wave_mob_pool:
                    self.current_wave_mob_pool.pop(0)

                # Verifica se spawnou o Boss (agora funciona pq a lista diminuiu)
                if not self.boss_mode_active and not self.current_wave_mob_pool:
                    self.boss_mode_active = True
                    boss_id = self.wave_definitions[self.current_wave].get("boss_id")
                    boss_template = _find_monster_template(boss_id) if boss_id else {}
                    
                    # Configura HP do Boss
                    num_participantes = len(self.player_states)
                    hp_base = boss_template.get("hp", 500)
                    escala_base = 40
                    hp_extra = escala_base * self.current_wave * num_participantes
                    
                    self.boss_max_hp = int(hp_base + hp_extra)
                    self.boss_global_hp = self.boss_max_hp
                    
                    boss_name = boss_template.get("name", "Chefe")
                    logs.append(f"\n🚨 <b>{boss_name}</b> APARECEU COM {self.boss_global_hp:,} HP! 🚨")

            if user_id in self.player_states:
                # Carrega o PRÓXIMO monstro (agora será um novo, pois demos pop no antigo)
                await self._setup_player_battle_state(user_id, player_data)
                return {
                    "monster_defeated": True, 
                    "action_log": "\n".join(logs), 
                    "loot_message": loot_msg if 'loot_msg' in locals() else ""
                }
            else:
                return {
                    "event_over": True, 
                    "action_log": "\n".join(logs)
                }

        # --- MONSTRO VIVO (CONTRA-ATAQUE) ---
        else:
            if is_boss_fight:
                self.boss_attack_counter += 1
            
            special_attack_data = mob.get("special_attack")

            # Ataque Especial em Área (Boss)
            if is_boss_fight and special_attack_data and special_attack_data.get("is_aoe") and self.boss_attack_counter % 3 == 0:
                logs.append(f"👑 <b>{special_attack_data['name']}</b> (Em Área!)")
                aoe_results = []
                
                for fighter_id in list(self.active_fighters):
                    f_state = self.player_states.get(fighter_id)
                    f_data = await player_manager.get_player_data(fighter_id)
                    if not f_state or not f_data: continue
                    
                    f_stats = await player_manager.get_player_total_stats(f_data)
                    base_dmg, _, _ = criticals.roll_damage(mob, f_stats, {})
                    final_dmg = int(base_dmg * special_attack_data.get("damage_multiplier", 1.0))
                    
                    f_state['player_hp'] = max(0, f_state['player_hp'] - final_dmg)
                    
                    logs.append(f"🔥 {f_data.get('character_name','Herói')} sofreu {final_dmg}!")
                    
                    was_defeated = f_state['player_hp'] <= 0
                    aoe_results.append({"user_id": fighter_id, "was_defeated": was_defeated})
                    
                    if was_defeated:
                        self.active_fighters.remove(fighter_id)
                        await self._promote_next_player()
                
                return { "monster_defeated": False, "action_log": "\n".join(logs), "aoe_results": aoe_results }

            # Ataque Normal ou Especial Single-Target
            else:
                dodge_chance = await player_stats_engine.get_player_dodge_chance(player_data)
                if random.random() < dodge_chance:
                    logs.append(f"💨 Você se esquivou do ataque!")
                else:
                    mob_damage, mob_is_crit, mob_is_mega = criticals.roll_damage(mob, player_full_stats, {})
                    
                    if is_boss_fight and special_attack_data and not special_attack_data.get("is_aoe") and self.boss_attack_counter % 3 == 0:
                        mob_damage = int(mob_damage * special_attack_data.get("damage_multiplier", 1.0))
                        logs.append(f"👑 <b>{special_attack_data['name']}!</b>")
                    
                    player_state['player_hp'] = max(0, player_state['player_hp'] - mob_damage)
                    
                    if mob_is_mega: logs.append(f"‼️ <b>MEGA CRÍTICO!</b> Recebeu {mob_damage} de dano!")
                    elif mob_is_crit: logs.append(f"❗️ <b>CRÍTICO!</b> Recebeu {mob_damage} de dano!")
                    else: logs.append(f"🩸 Recebeu {mob_damage} de dano.")

                if player_state['player_hp'] <= 0:
                    logs.append("\n💀 <b>VOCÊ FOI DERROTADO!</b>")
                    self.active_fighters.remove(user_id)
                    await self._promote_next_player()
                    return { "game_over": True, "action_log": "\n".join(logs) }

                return { "monster_defeated": False, "game_over": False, "action_log": "\n".join(logs) }

    async def process_player_attack(self, user_id, player_data, player_full_stats):
        """Calcula o dano do ataque básico usando o 'combat_engine' unificado."""
        
        if not self.is_active or user_id not in self.active_fighters:
            return {"error": "Você não está em uma batalha ativa."}
        
        if user_id not in self.player_states:
            self.active_fighters.discard(user_id) 
            return {"error": "Seu estado de batalha não foi encontrado. Tente reentrar no evento."}

        self._tick_effects(user_id) 
        
        player_state = self.player_states[user_id]
        mob = player_state['current_mob']
        is_boss_fight = mob.get('is_boss', False)
        logs = []

        attacker_combat_stats = self._get_stats_with_effects(
            player_full_stats, 
            player_state.get('active_effects', [])
        )
        target_combat_stats = self._get_stats_with_effects(
            mob, 
            mob.get('active_effects', [])
        )
        
        # 1. CHAMA O CÉREBRO UNIFICADO
        
        # --- CORREÇÃO AQUI (passar player_data) ---
        resultado_combate = await combat_engine.processar_acao_combate(
            attacker_pdata=player_data, # <--- ADICIONADO
            attacker_stats=attacker_combat_stats,
            target_stats=target_combat_stats,
            skill_id=None, # 'None' significa ataque básico
            attacker_current_hp=player_state.get('player_hp')
        )
        
        # 2. APLICA OS RESULTADOS
        damage = resultado_combate["total_damage"]
        logs.extend(resultado_combate["log_messages"])
        
        player_state['damage_dealt'] += damage
        if is_boss_fight: 
            self.boss_global_hp = max(0, self.boss_global_hp - damage)
        else: 
            mob['hp'] = max(0, mob['hp'] - damage)
        
        # 3. CHAMA A RESOLUÇÃO DO TURNO
        return await self._resolve_turn(user_id, player_data, logs)

    async def process_player_skill(self, user_id, player_data, skill_id, target_id=None):
        """Processa o uso de skill, usando o 'combat_engine' para skills de ataque."""
        
        if user_id not in self.active_fighters:
            return {"error": "Você não está em uma batalha ativa."}

        # 1. AVANÇA OS TURNOS (Cooldowns diminuem aqui)
        self._tick_effects(user_id)

        player_state = self.player_states[user_id]
        
        # 2. VERIFICAÇÃO DE COOLDOWN
        current_cooldowns = player_state.get('skill_cooldowns', {})
        if current_cooldowns.get(skill_id, 0) > 0:
            turns_left = current_cooldowns[skill_id]
            return {"error": f"Habilidade em recarga! Aguarde {turns_left} turnos."}

        skill_info = _get_player_skill_data_by_rarity(player_data, skill_id)
        if not skill_info: return {"error": "Habilidade desconhecida."}

        mana_cost = skill_info.get("mana_cost", 0)
        
        # Verifica no estado da batalha (que é o mais atualizado)
        current_mp = player_state.get('player_mp', 0)
        
        if current_mp < mana_cost:
            return {"error": f"Mana insuficiente! ({current_mp}/{mana_cost})"}
        
        # --- GASTO DE MANA ---
        player_state['player_mp'] -= mana_cost
        
        # ✅ CORREÇÃO DE SINCRONIA (CRUCIAL):
        # Atualiza o player_data IMEDIATAMENTE para que o save funcione.
        # Atualizamos as duas chaves possíveis ('current_mp' e 'mana') para garantir que interface e banco fiquem iguais.
        player_data['current_mp'] = player_state['player_mp']
        player_data['mana'] = player_state['player_mp'] 
        
        logs = [f"Você usa {skill_info['display_name']}! (-{mana_cost} MP)"]

        # 3. APLICA O COOLDOWN
        cooldown_turns = skill_info.get("effects", {}).get("cooldown_turns", 0)
        if cooldown_turns > 0:
            player_state.setdefault('skill_cooldowns', {})[skill_id] = cooldown_turns + 1

        # --- LÓGICA DA SKILL ---
        skill_type = skill_info.get("type")
        skill_effects = skill_info.get("effects", {})
        mob = player_state['current_mob']
        is_boss_fight = mob.get('is_boss', False)
        
        # SKILL DE ATAQUE
        if skill_type == "active": 
            player_full_stats = await player_manager.get_player_total_stats(player_data)
            
            attacker_stats = self._get_stats_with_effects(player_full_stats, player_state.get('active_effects', []))
            target_stats = self._get_stats_with_effects(mob, mob.get('active_effects', []))
            
            result = await combat_engine.processar_acao_combate(
                attacker_pdata=player_data, 
                attacker_stats=attacker_stats, 
                target_stats=target_stats, 
                skill_id=skill_id, 
                attacker_current_hp=player_state.get('player_hp')
            )

            final_damage = result["total_damage"]
            logs.extend(result["log_messages"])
            player_state['damage_dealt'] += final_damage
            
            if is_boss_fight: self.boss_global_hp = max(0, self.boss_global_hp - final_damage)
            else: mob['hp'] = max(0, mob['hp'] - final_damage)

            if "debuff_target" in skill_effects:
                debuff = skill_effects["debuff_target"]
                mob.setdefault('active_effects', []).append({"stat": debuff["stat"], "multiplier": debuff["value"], "turns_left": debuff["duration_turns"]})
                logs.append(f"🛡️ Defesa inimiga reduzida!")

        # SKILL DE SUPORTE
        elif skill_type == "support": 
            heal_applied = False
            player_full_stats = await player_manager.get_player_total_stats(player_data)

            if "party_heal" in skill_effects:
                heal_def = skill_effects["party_heal"]
                heal_amount = 0
                if "amount_percent_max_hp" in heal_def:
                    heal_amount = int(player_full_stats.get('max_hp', 1) * heal_def["amount_percent_max_hp"])
                elif heal_def.get("heal_type") == "magic_attack":
                    m_atk = player_full_stats.get('magic_attack', player_full_stats.get('attack', 0))
                    heal_amount = int(m_atk * heal_def.get("heal_scale", 1.0))
                
                if heal_amount > 0:
                    for ally_id in list(self.active_fighters):
                        ally_state = self.player_states.get(ally_id)
                        if ally_state:
                            ally_state['player_hp'] += heal_amount
                            heal_applied = True
                    if heal_applied: logs.append(f"✨ Grupo curado em {heal_amount} HP!")
            
            if not heal_applied:
                logs.append("🎶 Efeitos de suporte ativados!")

            # Salva o player_data (que agora tem a mana atualizada)
            await player_manager.save_player_data(user_id, player_data) 
            return { "monster_defeated": False, "action_log": "\n".join(logs), "skip_monster_turn": True }
        
        return await self._resolve_turn(user_id, player_data, logs)

    def get_battle_data(self, user_id):
        if user_id not in self.player_states: return None
        player_state_copy = self.player_states[user_id].copy()
        player_state_copy['current_wave'] = self.current_wave
        if player_state_copy['current_mob'].get('is_boss'):
            player_state_copy['current_mob']['hp'] = self.boss_global_hp
        return player_state_copy

    def get_queue_status_text(self):
        wave_info = self.wave_definitions.get(self.current_wave)
        if not wave_info or not self.is_active:
            return "O evento não está ativo no momento."
        status_line = ""
        if self.boss_mode_active and self.boss_max_hp > 0:
            percent_hp = (self.boss_global_hp / self.boss_max_hp) * 100
            status_line = f"Vida do Chefe: {self.boss_global_hp:,}/{self.boss_max_hp:,} ({percent_hp:.1f}%)"
        else:
            mobs_derrotados = self.total_mobs_in_wave - len(self.current_wave_mob_pool)
            total_mobs = self.total_mobs_in_wave
            status_line = f"Progresso da Onda {self.current_wave}: {mobs_derrotados}/{total_mobs}"
        return (
            f"{status_line}\n"
            f"Defensores Ativos: {len(self.active_fighters)}/{self.max_concurrent_fighters}\n"
            f"Heróis na Fila: {len(self.waiting_queue)}"
        )
    
    def _get_stats_with_effects(self, base_stats: dict, active_effects: list) -> dict:
        """
        Pega os atributos base de um combatente e aplica os bônus ou penalidades de
        todos os efeitos ativos (buffs/debuffs) para o turno atual.
        """
        modified_stats = base_stats.copy()

        for effect in active_effects:
            stat_to_modify = effect.get("stat")
            multiplier = effect.get("multiplier", 0.0)
        
            if stat_to_modify in modified_stats:
                bonus_value = modified_stats[stat_to_modify] * multiplier
            
                # Adiciona o valor ao atributo. Multiplicadores negativos (debuffs) funcionarão corretamente.
                modified_stats[stat_to_modify] += int(bonus_value)

        return modified_stats
    
    def _tick_effects(self, user_id: int):
        """Reduz a duração dos efeitos e dos COOLDOWNS."""
        player_state = self.player_states.get(user_id)
        if not player_state: return

        # ✅ 1. Reduz Cooldowns das Skills (Lógica Nova)
        if 'skill_cooldowns' in player_state:
            new_cooldowns = {}
            for skill_id, turns in player_state['skill_cooldowns'].items():
                if turns > 1:
                    new_cooldowns[skill_id] = turns - 1
                # Se for 1, vira 0 e não entra na nova lista (ou seja, liberado)
            player_state['skill_cooldowns'] = new_cooldowns

        # 2. Efeitos do Jogador (Buffs)
        if player_state.get('active_effects'):
            player_updated_effects = []
            for effect in player_state['active_effects']:
                effect['turns_left'] -= 1
                if effect['turns_left'] > 0:
                    player_updated_effects.append(effect)
            player_state['active_effects'] = player_updated_effects

        # 3. Efeitos do Monstro (Debuffs)
        mob = player_state.get('current_mob')
        if mob and mob.get('active_effects'):
            mob_updated_effects = []
            for effect in mob['active_effects']:
                effect['turns_left'] -= 1
                if effect['turns_left'] > 0:
                    mob_updated_effects.append(effect)
            mob['active_effects'] = mob_updated_effects

    async def get_leaderboard_text(self) -> str:
        all_participants_ids = set(self.active_fighters) | set(self.player_states.keys())
        if not all_participants_ids: return "Nenhum herói participou do evento ainda."
        leaderboard_data = []
        for user_id in all_participants_ids:
            state = self.player_states.get(user_id)
            player_data = await player_manager.get_player_data(user_id)
            if state and player_data and state.get('damage_dealt', 0) > 0:
                leaderboard_data.append({
                    "name": player_data.get('character_name', 'Herói'),
                    "damage": state.get('damage_dealt', 0)
                })
        if not leaderboard_data: return "Ninguém causou dano ainda."
        sorted_participants = sorted(leaderboard_data, key=lambda i: i['damage'], reverse=True)
        lines = ["🏆 **Ranking de Dano do Evento** 🏆\n"]
        for i, status in enumerate(sorted_participants[:5]):
            medal = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, "🔹")
            lines.append(f"{medal} {status['name']}: {status['damage']:,} de dano")
        return "\n".join(lines)

# --- INSTÂNCIA ÚNICA ---
event_manager = KingdomDefenseManager()

async def start_event_job(context: ContextTypes.DEFAULT_TYPE):
    """Job agendado para iniciar o evento."""
    logger.info("Job agendado: Ativando o evento de defesa do reino...")
    # ANTES: event_manager.start_event()
    await event_manager.start_event()

async def end_event_job(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Job agendado: Encerrando o evento de defesa do reino...")
    # end_event é assíncrono e deve ser aguardado
    await event_manager.end_event(context)