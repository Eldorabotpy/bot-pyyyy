import logging
import datetime
import random
import math
from modules import player_manager
# Certifique-se de que pvp_config é importado corretamente se ARENA_MODIFIERS for usado
from .pvp_config import ARENA_MODIFIERS
from . import pvp_config

logger = logging.getLogger(__name__)

# --- Ferramentas de Cáculo de Crítico e Dano ---

def _crit_params_for_player(stats: dict) -> dict:
    """Calcula os parâmetros de crítico com base nos stats atuais."""
    if 'crit_chance' in stats: # Prioriza crit_chance se existir (modificador)
        chance = float(stats.get('crit_chance', 5.0))
    else: # Senão, calcula com base na sorte
        luck = int(stats.get("luck", 5))
        chance = 100.0 * (1.0 - (0.99 ** max(0, luck)))
        chance = max(1.0, min(chance, 40.0)) # Limita entre 1% e 40%

    luck = int(stats.get("luck", 5)) # Sorte para mega crítico
    mega_chance = min(25.0, luck / 2.0)

    return {"chance": chance, "mega_chance": mega_chance, "mult": 1.6, "mega_mult": 2.0, "min_damage": 1}

def _roll_damage(attacker_stats: dict, defender_stats: dict, crit_params: dict) -> tuple[int, list[str]]:
    """Calcula o dano de um ataque, incluindo chance de crítico e redução por defesa."""
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

    # Fórmula de Dano Percentual (Usando chaves em Inglês)
    attacker_atk = float(attacker_stats.get('attack', 0))
    defender_def = float(defender_stats.get('defense', 0))

    boosted_attack = math.ceil(attacker_atk * mult)

    # Cálculo da redução de dano
    if defender_def < 0: defender_def = 0
    damage_reduction = 100.0 / (100.0 + defender_def)
    final_damage = boosted_attack * damage_reduction

    # Aplica dano mínimo e converte para inteiro
    damage = max(int(crit_params.get("min_damage", 1)), int(final_damage))

    return damage, log

def simular_batalha_completa(player1_id, player2_id, modifier_effect=None):
    """
    Simula uma batalha PvP completa do início ao fim.
    Retorna o ID do vencedor e o log completo da batalha.
    """
    # Carrega dados dos jogadores
    p1_data = player_manager.get_player_data(player1_id)
    p2_data = player_manager.get_player_data(player2_id)

    # Retorna erro se não conseguir carregar dados
    if not p1_data or not p2_data:
        logger.error(f"Não foi possível carregar dados para pvp: P1={p1_data is not None}, P2={p2_data is not None}")
        return 0, ["Erro ao carregar dados dos combatentes."]

    # Prepara os stats (usando chaves em Inglês)
    try:
        p1_stats = player_manager.get_player_total_stats(p1_data).copy()
        p2_stats = player_manager.get_player_total_stats(p2_data).copy()
    except Exception as e_load_stats:
        logger.error(f"Erro ao carregar stats PvP para {player1_id} vs {player2_id}: {e_load_stats}", exc_info=True)
        return 0, [f"Erro ao carregar stats: {e_load_stats}"]

    # Adiciona user_id aos stats para referência
    p1_stats['user_id'] = player1_id
    p2_stats['user_id'] = player2_id

    # Pega HP inicial
    p1_hp = p1_stats.get('max_hp', 1)
    p2_hp = p2_stats.get('max_hp', 1)

    # Pega Nomes, Níveis e Classes para o cabeçalho
    p1_name = p1_data.get("character_name", f"ID: {player1_id}")
    p2_name = p2_data.get("character_name", f"ID: {player2_id}")
    p1_level = p1_data.get("level", 1)
    p2_level = p2_data.get("level", 1)
    # Lógica inteligente para encontrar a classe (retorna None se não houver)
    p1_class_key = (p1_data.get("class_key") or p1_data.get("class") or p1_data.get("classe") or p1_data.get("class_type"))
    p2_class_key = (p2_data.get("class_key") or p2_data.get("class") or p2_data.get("classe") or p2_data.get("class_type"))
    p1_class_display = p1_class_key.capitalize() if p1_class_key else "Novato"
    p2_class_display = p2_class_key.capitalize() if p2_class_key else "Novato"

    # Limita os nomes para evitar quebra de layout
    p1_name_short = p1_name[:15]
    p2_name_short = p2_name[:15]

    # Cria o bloco de cabeçalho estilizado com stats
    stats_header = (
        f"⚔️ <b>{p1_name}</b> (Nv. {p1_level} {p1_class_display}) VS <b>{p2_name}</b> (Nv. {p2_level} {p2_class_display}) ⚔️\n\n"
        f"╔════════════ ◆◈◆ ════════════╗\n"
        f"  <b>{p1_name_short}</b>\n"
        f"  ❤️ 𝐇𝐏: {p1_stats.get('max_hp', 0)}\n"
        f"  ⚔️ 𝐀𝐓𝐊: {p1_stats.get('attack', 0):<4} 🛡 𝐃𝐄𝐅: {p1_stats.get('defense', 0)}\n"
        f"  🏃‍♂️ 𝐈𝐍𝐈: {p1_stats.get('initiative', 0):<4} 🍀 𝐋𝐔𝐊: {p1_stats.get('luck', 0)}\n"
        f"════════════════════════════════\n"
        f"  <b>{p2_name_short}</b>\n"
        f"  ❤️ 𝐇𝐏: {p2_stats.get('max_hp', 0)}\n"
        f"  ⚔️ 𝐀𝐓𝐊: {p2_stats.get('attack', 0):<4} 🛡 𝐃𝐄𝐅: {p2_stats.get('defense', 0)}\n"
        f"  🏃‍♂️ 𝐈𝐍𝐈: {p2_stats.get('initiative', 0):<4} 🍀 𝐋𝐔𝐊: {p2_stats.get('luck', 0)}\n"
        f"╚════════════ ◆◈◆ ════════════╝\n"
    )

    # Inicializa o battle_log APENAS com o cabeçalho estilizado
    battle_log = [stats_header]

    # Lógica dos Modificadores de Arena (Adiciona ao Log e aplica aos stats)
    if modifier_effect:
        try:
            today_weekday = datetime.datetime.now().weekday()
            # Usa pvp_config aqui se ARENA_MODIFIERS veio de lá
            mod_data = pvp_config.ARENA_MODIFIERS.get(today_weekday)
            if mod_data and mod_data.get("effect") == modifier_effect:
                 # Adiciona linha em branco e depois o modificador
                 battle_log.append(f"\n🔥 <b>Modificador: {mod_data['name']}</b>")
                 battle_log.append(f"<i>{mod_data['description']}</i>\n")
        except Exception as e:
            logger.warning(f"Erro ao carregar descrição do modificador: {e}")

        # Função interna para aplicar modificadores (Usa Inglês)
        def apply_mods_to_stats(stats_dict, effect):
            if effect == "fury_day":
                stats_dict['attack'] = float(stats_dict.get('attack', 0)) * 1.20
                stats_dict['defense'] = float(stats_dict.get('defense', 0)) * 0.90
            elif effect == "agility_day":
                stats_dict['dodge_chance'] = float(stats_dict.get('dodge_chance', 0)) + 15
                stats_dict['double_attack_chance'] = float(stats_dict.get('double_attack_chance', 0)) + 15
            elif effect == "wall_day":
                stats_dict['defense'] = float(stats_dict.get('defense', 0)) * 1.5
                stats_dict['attack'] = float(stats_dict.get('attack', 0)) * 0.8
            elif effect == "critical_day":
                stats_dict['crit_chance'] = float(stats_dict.get('crit_chance', 0)) + 20
            elif effect == "glass_cannon_day":
                stats_dict['attack'] = float(stats_dict.get('attack', 0)) * 2.0
                stats_dict['defense'] = 0

        # Aplica os modificadores
        try:
            apply_mods_to_stats(p1_stats, modifier_effect)
            apply_mods_to_stats(p2_stats, modifier_effect)
        except Exception as e_apply_mod:
             logger.error(f"Erro ao aplicar modificador PvP '{modifier_effect}': {e_apply_mod}", exc_info=True)
             return 0, [f"Erro ao aplicar modificador: {e_apply_mod}"]

    # Decide quem ataca primeiro (Usa 'initiative' - Inglês)
    atacante_stats, defensor_stats = (p1_stats, p2_stats)
    # HPs para o loop de batalha começam com o HP máximo inicial
    atacante_hp, defensor_hp = (p1_hp, p2_hp)
    atacante_name, defensor_name = (p1_name, p2_name)

    # Troca se P2 for mais rápido
    if p2_stats.get('initiative', 0) > p1_stats.get('initiative', 0):
        atacante_stats, defensor_stats = (p2_stats, p1_stats)
        # HPs do loop também trocam
        atacante_hp, defensor_hp = (p2_hp, p1_hp)
        atacante_name, defensor_name = (p2_name, p1_name)

    # Loop da batalha (máximo de 20 rodadas)
    for round_num in range(1, 21):
        battle_log.append(f"\n--- <b>Turno {round_num}</b> ---")

        # --- Ataque do primeiro jogador ---
        try:
            crit_params = _crit_params_for_player(atacante_stats)
            dano, crit_log = _roll_damage(atacante_stats, defensor_stats, crit_params)
            defensor_hp -= dano # Reduz o HP do loop
            battle_log.append(f"➡️ {atacante_name} ataca!")
            battle_log.extend(crit_log)
            battle_log.append(f"💥 {defensor_name} recebe {dano} de dano. (HP restante: {max(0, int(defensor_hp))})")
        except Exception as e_atk1:
            logger.error(f"Erro no ataque de {atacante_name} no turno {round_num}: {e_atk1}", exc_info=True)
            battle_log.append(f"⚠️ Erro no ataque de {atacante_name}!")

        # Verifica se o defensor foi derrotado
        if defensor_hp <= 0:
            battle_log.append(f"\n🎉 <b>{atacante_name} venceu a batalha!</b>")
            return atacante_stats.get('user_id', 0), battle_log

        # --- Ataque do segundo jogador ---
        try:
            crit_params = _crit_params_for_player(defensor_stats)
            dano, crit_log = _roll_damage(defensor_stats, atacante_stats, crit_params)
            atacante_hp -= dano # Reduz o HP do loop
            battle_log.append(f"⬅️ {defensor_name} ataca!")
            battle_log.extend(crit_log)
            battle_log.append(f"💥 {atacante_name} recebe {dano} de dano. (HP restante: {max(0, int(atacante_hp))})")
        except Exception as e_atk2:
            logger.error(f"Erro no ataque de {defensor_name} no turno {round_num}: {e_atk2}", exc_info=True)
            battle_log.append(f"⚠️ Erro no ataque de {defensor_name}!")

        # Verifica se o atacante original foi derrotado
        if atacante_hp <= 0:
            battle_log.append(f"\n🎉 <b>{defensor_name} venceu a batalha!</b>")
            return defensor_stats.get('user_id', 0), battle_log

    # Se chegou a 20 turnos, declara empate
    battle_log.append("\n⚖️ A batalha foi longa e terminou em empate!")
    return 0, battle_log