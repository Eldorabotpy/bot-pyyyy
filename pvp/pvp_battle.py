# pvp/pvp_battle.py

import logging
import datetime
import random
import math
import html
from modules import player_manager
# Certifique-se de que pvp_config é importado corretamente
from .pvp_config import ARENA_MODIFIERS
from . import pvp_config
from . import pvp_utils

logger = logging.getLogger(__name__)

# --- NOVO HELPER DE BALANCEAMENTO ---
def _balancear_stats(stats, nivel_atual, nivel_meta):
    """
    Escalona os atributos para simular um nível meta.
    Ex: Se sou lvl 10 e a meta é 50, multiplica meus stats por 5.
    """
    if nivel_atual <= 0: nivel_atual = 1
    if nivel_meta <= 0: return stats # Sem balanceamento
    
    # Fator de Multiplicação (ex: 50 / 10 = 5.0)
    ratio = float(nivel_meta) / float(nivel_atual)
    
    # Aplica nos atributos principais
    novos_stats = stats.copy()
    chaves_escalaveis = ["hp", "max_hp", "max_mana", "attack", "defense", "magic_attack", "magic_defense", "initiative", "luck"]
    
    for k in chaves_escalaveis:
        val = novos_stats.get(k, 0)
        # Convertemos para int após multiplicar
        novos_stats[k] = int(val * ratio)
        
    return novos_stats, ratio

# --- Ferramentas de Cálculo de Crítico e Dano ---

def _crit_params_for_player(stats: dict) -> dict:
    """Calcula os parâmetros de crítico com base nos stats atuais."""
    if 'crit_chance' in stats: 
        chance = float(stats.get('crit_chance', 5.0))
    else: 
        luck = int(stats.get("luck", 5))
        chance = 100.0 * (1.0 - (0.99 ** max(0, luck)))
        chance = max(1.0, min(chance, 40.0)) 

    luck = int(stats.get("luck", 5))
    mega_chance = min(25.0, luck / 2.0)

    return {"chance": chance, "mega_chance": mega_chance, "mult": 1.6, "mega_mult": 2.0, "min_damage": 1}

def _roll_damage(attacker_stats: dict, defender_stats: dict, crit_params: dict) -> tuple[int, list[str]]:
    """Calcula o dano de um ataque."""
    log = []
    r = random.random() * 100.0
    is_crit = (r <= float(crit_params.get("chance", 0.0)))
    mult = 1.0
    if is_crit:
        if random.random() * 100.0 <= float(crit_params.get("mega_chance", 0.0)):
            mult = float(crit_params.get("mega_mult", 2.0))
            log.append("💥 𝐌𝐄𝐆𝐀 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎! 💥")
        else:
            mult = float(crit_params.get("mult", 1.6))
            log.append("✨ 𝐀𝐂𝐄RT𝐎 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎! ✨")

    attacker_atk = float(attacker_stats.get('attack', 0))
    defender_def = float(defender_stats.get('defense', 0))

    boosted_attack = math.ceil(attacker_atk * mult)

    if defender_def < 0: defender_def = 0
    damage_reduction = 100.0 / (100.0 + defender_def)
    final_damage = boosted_attack * damage_reduction

    damage = max(int(crit_params.get("min_damage", 1)), int(final_damage))

    return damage, log


async def simular_batalha_completa(player1_id, player2_id, modifier_effect=None, nivel_padrao=None):
    """
    Simula uma batalha PvP completa.
    ACEITA 'nivel_padrao': Se for informado (ex: 50), nivela os stats.
    Se for None (Padrão), usa os stats reais.
    """
    
    p1_data = await player_manager.get_player_data(player1_id)
    p2_data = await player_manager.get_player_data(player2_id)

    if not p1_data or not p2_data:
        logger.error(f"Não foi possível carregar dados para pvp: P1={p1_data is not None}, P2={p2_data is not None}")
        return 0, ["Erro ao carregar dados dos combatentes."]

    try:
        p1_stats = (await player_manager.get_player_total_stats(p1_data)).copy()
        p2_stats = (await player_manager.get_player_total_stats(p2_data)).copy()
    except Exception as e_load_stats:
        logger.error(f"Erro ao carregar stats PvP para {player1_id} vs {player2_id}: {e_load_stats}", exc_info=True)
        return 0, [f"Erro ao carregar stats: {e_load_stats}"]

    p1_stats['user_id'] = player1_id
    p2_stats['user_id'] = player2_id

    # === APLICAR BALANCEAMENTO (Lógica Nova) ===
    # Só roda se o Torneio pedir. No PvP normal (nivel_padrao=None), isso é ignorado.
    log_extra = []
    if nivel_padrao:
        lvl1 = int(p1_data.get("level", 1))
        lvl2 = int(p2_data.get("level", 1))
        
        p1_stats, r1 = _balancear_stats(p1_stats, lvl1, nivel_padrao)
        p2_stats, r2 = _balancear_stats(p2_stats, lvl2, nivel_padrao)
        
        log_extra.append(f"⚖️ <b>Torneio Balanceado (Meta Nv. {nivel_padrao})</b>")
        # log_extra.append(f"• P1: Nv.{lvl1} -> {nivel_padrao}") # Opcional: mostrar detalhe
        # log_extra.append(f"• P2: Nv.{lvl2} -> {nivel_padrao}\n")
    # ===========================================

    p1_max_hp = int(p1_stats.get('max_hp', 1))
    p2_max_hp = int(p2_stats.get('max_hp', 1))
    
    p1_hp = p1_max_hp
    p2_hp = p2_max_hp

    p1_name = p1_data.get("character_name", f"ID: {player1_id}")
    p2_name = p2_data.get("character_name", f"ID: {player2_id}")
    p1_level = p1_data.get("level", 1)
    p2_level = p2_data.get("level", 1)
    
    # Se estiver balanceado, mostramos o nível original visualmente, mas os stats são os novos
    p1_class_key = (p1_data.get("class_key") or p1_data.get("class") or "default")
    p2_class_key = (p2_data.get("class_key") or p2_data.get("class") or "default")
    p1_class_display = p1_class_key.capitalize()
    p2_class_display = p2_class_key.capitalize()
    p1_name_short = p1_name[:15]
    p2_name_short = p2_name[:15]

    stats_header = (
        f"⚔️ <b>{html.escape(p1_name)}</b> (Nv. {p1_level} {p1_class_display}) VS <b>{html.escape(p2_name)}</b> (Nv. {p2_level} {p2_class_display}) ⚔️\n\n"
        f"╔════════════ ◆◈◆ ════════════╗\n"
        f"  <b>{html.escape(p1_name_short)}</b>\n"
        f"  ❤️ 𝐇𝐏: {p1_max_hp}\n"
        f"  ⚔️ 𝐀𝐓𝐊: {p1_stats.get('attack', 0):<4} 🛡 𝐃𝐄𝐅: {p1_stats.get('defense', 0)}\n"
        f"  🏃‍♂️ 𝐈𝐍𝐈: {p1_stats.get('initiative', 0):<4} 🍀 𝐋𝐔𝐊: {p1_stats.get('luck', 0)}\n"
        f"════════════════════════════════\n"
        f"  <b>{html.escape(p2_name_short)}</b>\n"
        f"  ❤️ 𝐇𝐏: {p2_max_hp}\n"
        f"  ⚔️ 𝐀𝐓𝐊: {p2_stats.get('attack', 0):<4} 🛡 𝐃𝐄𝐅: {p2_stats.get('defense', 0)}\n"
        f"  🏃‍♂️ 𝐈𝐍𝐈: {p2_stats.get('initiative', 0):<4} 🍀 𝐋𝐔𝐊: {p2_stats.get('luck', 0)}\n"
        f"╚════════════ ◆◈◆ ════════════╝\n"
    )
    
    # Inicia o Log com os extras (balanceamento) + cabeçalho
    battle_log = list(log_extra)
    battle_log.append(stats_header)

    # Lógica dos Modificadores de Arena
    if modifier_effect:
        try:
            today_weekday = datetime.datetime.now().weekday()
            mod_data = pvp_config.ARENA_MODIFIERS.get(today_weekday)
            if mod_data and mod_data.get("effect") == modifier_effect:
                battle_log.append(f"\n🔥 <b>Modificador: {mod_data['name']}</b>")
                battle_log.append(f"<i>{mod_data['description']}</i>\n")
        except Exception as e:
            logger.warning(f"Erro ao carregar descrição do modificador: {e}")

        def apply_mods_to_stats(stats_dict, effect):
            if effect == "fury_day": stats_dict['attack'] = float(stats_dict.get('attack', 0)) * 1.20; stats_dict['defense'] = float(stats_dict.get('defense', 0)) * 0.90
            elif effect == "agility_day": stats_dict['dodge_chance'] = float(stats_dict.get('dodge_chance', 0)) + 15; stats_dict['double_attack_chance'] = float(stats_dict.get('double_attack_chance', 0)) + 15
            elif effect == "wall_day": stats_dict['defense'] = float(stats_dict.get('defense', 0)) * 1.5; stats_dict['attack'] = float(stats_dict.get('attack', 0)) * 0.8
            elif effect == "critical_day": stats_dict['crit_chance'] = float(stats_dict.get('crit_chance', 0)) + 20
            elif effect == "glass_cannon_day": stats_dict['attack'] = float(stats_dict.get('attack', 0)) * 2.0; stats_dict['defense'] = 0

        try:
            apply_mods_to_stats(p1_stats, modifier_effect)
            apply_mods_to_stats(p2_stats, modifier_effect)
        except Exception as e_apply_mod:
            logger.error(f"Erro ao aplicar modificador PvP: {e_apply_mod}")

    # Decide quem ataca primeiro
    atacante_stats, defensor_stats = (p1_stats, p2_stats)
    atacante_hp, defensor_hp = (p1_hp, p2_hp)
    atacante_name, defensor_name = (p1_name, p2_name)
    
    if p2_stats.get('initiative', 0) > p1_stats.get('initiative', 0):
        atacante_stats, defensor_stats = (p2_stats, p1_stats)
        atacante_hp, defensor_hp = (p2_hp, p1_hp)
        atacante_name, defensor_name = (p2_name, p1_name)

    def get_max_hp_by_id(user_id):
        if user_id == player1_id: return p1_max_hp
        if user_id == player2_id: return p2_max_hp
        return 100

    # Loop da batalha
    for round_num in range(1, 21):
        battle_log.append(f"\n--- <b>Turno {round_num}</b> ---")

        # --- Ataque do primeiro jogador ---
        try:
            crit_params = _crit_params_for_player(atacante_stats)
            dano, crit_log = _roll_damage(atacante_stats, defensor_stats, crit_params)
            defensor_hp -= dano
            
            defensor_id = defensor_stats.get('user_id')
            hp_atual_def = max(0, int(defensor_hp))
            hp_max_def = get_max_hp_by_id(defensor_id)
            
            try:
                barra_hp = pvp_utils.gerar_barra_hp(hp_atual_def, hp_max_def)
            except AttributeError:
                barra_hp = ""

            battle_log.append(f"➡️ {html.escape(atacante_name)} ataca!")
            battle_log.extend(crit_log)
            battle_log.append(f"💥 {html.escape(defensor_name)} recebe {dano} de dano.\n   {barra_hp} ({hp_atual_def}/{hp_max_def})")
            
        except Exception as e_atk1:
            logger.error(f"Erro no ataque 1: {e_atk1}")
            battle_log.append(f"⚠️ Erro no ataque de {html.escape(atacante_name)}!")

        if defensor_hp <= 0:
            battle_log.append(f"\n🎉 <b>{html.escape(atacante_name)} venceu a batalha!</b>")
            return atacante_stats.get('user_id', 0), battle_log

        # --- Ataque do segundo jogador ---
        try:
            crit_params = _crit_params_for_player(defensor_stats)
            dano, crit_log = _roll_damage(defensor_stats, atacante_stats, crit_params)
            atacante_hp -= dano

            atacante_id = atacante_stats.get('user_id')
            hp_atual_atk = max(0, int(atacante_hp))
            hp_max_atk = get_max_hp_by_id(atacante_id)

            try:
                barra_hp = pvp_utils.gerar_barra_hp(hp_atual_atk, hp_max_atk)
            except AttributeError:
                barra_hp = "" 

            battle_log.append(f"⬅️ {html.escape(defensor_name)} ataca!")
            battle_log.extend(crit_log)
            battle_log.append(f"💥 {html.escape(atacante_name)} recebe {dano} de dano.\n   {barra_hp} ({hp_atual_atk}/{hp_max_atk})")

        except Exception as e_atk2:
            logger.error(f"Erro no ataque 2: {e_atk2}")
            battle_log.append(f"⚠️ Erro no ataque de {html.escape(defensor_name)}!")

        if atacante_hp <= 0:
            battle_log.append(f"\n🎉 <b>{html.escape(defensor_name)} venceu a batalha!</b>")
            return defensor_stats.get('user_id', 0), battle_log

    battle_log.append("\n⚖️ A batalha foi longa e terminou em empate!")
    return 0, battle_log