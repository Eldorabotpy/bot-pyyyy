# Arquivo: kingdom_defense/utils.py

import html
from collections import defaultdict
from modules import player_manager

# --- Funções Auxiliares de Formatação ---
# Estas pequenas funções ajudam a formatar os números e garantir que tudo seja inteiro

def _i(v) -> int:
    """Converte qualquer valor para inteiro (com round) de forma segura."""
    try:
        return int(round(float(v)))
    except (ValueError, TypeError):
        try:
            return int(v)
        except (ValueError, TypeError):
            return 0

def _fmt_player_stats_as_ints(total_stats: dict) -> tuple[int, int, int, int, int]:
    """Converte o dict de stats em uma tupla de inteiros para exibição."""
    p_max_hp = _i(total_stats.get('max_hp', 0))
    p_atk    = _i(total_stats.get('attack', 0))
    p_def    = _i(total_stats.get('defense', 0))
    p_vel    = _i(total_stats.get('initiative', 0))
    p_srt    = _i(total_stats.get('luck', 0))
    return p_max_hp, p_atk, p_def, p_vel, p_srt

# --- Função Principal de Renderização ---

def format_kd_battle_message(dungeon_instance: dict, all_players_data: dict) -> str:
    """
    Formata a mensagem de combate para o evento Kingdom Defense, agrupando monstros.
    """
    cs = dungeon_instance.get('combat_state', {}) or {}
    header = ["╔════════════ ◆◈◆ ════════════╗"]

    # --- Seção dos Heróis ---
    heroes_blocks = []
    # Se não houver participantes, mostra uma mensagem
    if not cs.get('participants'):
        heroes_blocks.append("Nenhum herói na batalha...")
    else:
        for player_id, combat_data in (cs.get('participants', {}) or {}).items():
            player_full_data = all_players_data.get(player_id)
            if not player_full_data: continue

            total_stats = player_manager.get_player_total_stats(player_full_data)
            max_hp, atk, defense, vel, srt = _fmt_player_stats_as_ints(total_stats)
            current_hp = _i(combat_data.get('hp', 0))

            player_block = (
                f"<b>{combat_data.get('name','Herói')}</b>\n"
                f"❤️ 𝐇𝐏: {current_hp}/{max_hp}\n"
                f"⚔️ 𝐀𝐓𝐊: {atk}  🛡️ 𝐃𝐄𝐅: {defense}\n"
                f"🏃‍♂️ 𝐕𝐄𝐋: {vel}  🍀 𝐒𝐑𝐓: {srt}"
            )
            heroes_blocks.append(player_block)

    # --- Seção dos Inimigos ---
    enemies_blocks = []
    grouped_monsters = defaultdict(lambda: {'count': 0, 'data': None})
    
    # Agrupa monstros pelo nome
    for monster_key, monster_data in (cs.get('monsters', {}) or {}).items():
        if _i(monster_data.get('hp', 0)) > 0:
            name = monster_data.get('name', 'Inimigo')
            grouped_monsters[name]['count'] += 1
            if grouped_monsters[name]['data'] is None:
                grouped_monsters[name]['data'] = monster_data

    if not grouped_monsters:
        enemies_blocks.append("Nenhum inimigo à vista...")
    else:
        for name, group_info in grouped_monsters.items():
            count = group_info['count']
            monster_data = group_info['data']
            
            m_max_hp = _i(monster_data.get('max_hp', 0))
            m_atk = _i(monster_data.get('attack', 0))
            m_def = _i(monster_data.get('defense', 0))
            m_vel = _i(monster_data.get('initiative', 0))
            m_srt = _i(monster_data.get('luck', 0))

            display_name = f"{name} (x{count})" if count > 1 else name

            monster_block = (
                f"<b>{display_name}</b>\n"
                f"❤️ 𝐇𝐏: ~{m_max_hp} (individual)\n"
                f"⚔️ 𝐀𝐓𝐊: {m_atk}  🛡️ 𝐃𝐄𝐅: {m_def}\n"
                f"🏃‍♂️ 𝐕𝐄𝐋: {m_vel}  🍀 𝐒𝐑𝐓: {m_srt}"
            )
            enemies_blocks.append(monster_block)
    
    # --- Seção do Log ---
    log_lines = ["═════════════ ◆◈◆ ═════════════"]
    battle_log = cs.get('battle_log', []) or []
    if not battle_log:
        log_lines.append("A batalha está prestes a começar...")
    else:
        log_lines.extend([html.escape(str(x)) for x in battle_log[-4:]])
    
    footer = ["╚════════════ ◆◈◆ ════════════╝"]
    heroes_section = "\n\n".join(heroes_blocks)
    enemies_section = "═════════════════════════════\n" + "\n\n".join(enemies_blocks)
    
    return "\n".join(header + [heroes_section, enemies_section] + log_lines + footer)