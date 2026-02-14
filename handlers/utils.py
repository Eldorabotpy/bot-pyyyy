# handlers/utils.py
# (VERSÃO FINAL: COMPATÍVEL COM ORCHESTRATOR E IDS HÍBRIDOS)

import logging
import html
from typing import Optional, Union
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest
from modules import player_manager, game_data

logger = logging.getLogger(__name__)

# =============================================================================
# MELHORIA: A função 'render_item_stats_short' foi movida para cá
# para resolver uma importação circular com 'item_factory.py'.
# =============================================================================

async def safe_edit_message(query, text, reply_markup=None, parse_mode='HTML'):
    """Tenta editar a caption, fallback para text, ignora erros comuns."""
    if not query or not query.message:
        logger.warning("safe_edit_message: query ou query.message inválido.")
        return

    try:
        # Tenta editar caption primeiro
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except BadRequest as e_caption:
        # Se falhar porque não é caption ou erro comum, tenta editar texto
        if "message is not modified" in str(e_caption).lower():
            pass # Ignora, já está igual
        elif "message can't be edited" in str(e_caption).lower() or \
             "message to edit not found" in str(e_caption).lower():
             logger.debug(f"Não foi possível editar a mensagem (caption): {e_caption}")
             # Não tenta editar texto se a msg não pode ser editada ou não foi encontrada
        else:
            # Se foi outro erro de caption (ex: não tinha mídia), tenta texto
            try:
                await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
            except BadRequest as e_text:
                if "message is not modified" in str(e_text).lower():
                    pass # Ignora
                elif "message can't be edited" in str(e_text).lower() or \
                     "message to edit not found" in str(e_text).lower():
                     logger.debug(f"Não foi possível editar a mensagem (text): {e_text}")
                else:
                    logger.error(f"Erro inesperado ao editar mensagem (caption falhou, text falhou): {e_text}")
            except Exception as e_generic_text:
                 logger.error(f"Erro genérico ao editar texto: {e_generic_text}", exc_info=True)
    except Exception as e_generic_caption:
        logger.error(f"Erro genérico ao editar caption: {e_generic_caption}", exc_info=True)

async def safe_update_message(update: Update, context, new_text: str, new_reply_markup, new_media_file_id: str = None, new_media_type: str = 'photo'):
    """
    Atualiza uma mensagem de forma inteligente. Se for chamada por um botão, tenta
    editar a mensagem. Se for chamada por um comando, envia uma nova mensagem.
    """
    chat_id = update.effective_chat.id
    query = update.callback_query

    # --- Cenário 1: A chamada veio de um BOTÃO (query existe) ---
    if query:
        try: 
            await query.answer()
        except: pass
        
        # Lógica para tentar editar. Se não der, apaga e reenvia.
        # Esta é a lógica mais robusta para quando a mensagem muda de tipo (texto -> foto).
        try:
            can_edit = True
            is_new_media = bool(new_media_file_id)
            was_media = bool(query.message.photo or query.message.video)

            if is_new_media != was_media:
                can_edit = False

            if not can_edit:
                raise ValueError("Media type mismatch, cannot edit.")

            if was_media:
                await query.edit_message_caption(caption=new_text, reply_markup=new_reply_markup, parse_mode='HTML')
            else:
                await query.edit_message_text(text=new_text, reply_markup=new_reply_markup, parse_mode='HTML')
        
        except Exception:
            # Se a edição falhar, apaga a mensagem antiga e envia uma nova.
            try:
                await query.delete_message()
            except Exception:
                pass # A mensagem pode já ter sido apagada

            # Envia a nova mensagem (lógica de reenvio)
            if new_media_file_id:
                if new_media_type == 'video':
                    await context.bot.send_video(chat_id=chat_id, video=new_media_file_id, caption=new_text, reply_markup=new_reply_markup, parse_mode='HTML')
                else:
                    await context.bot.send_photo(chat_id=chat_id, photo=new_media_file_id, caption=new_text, reply_markup=new_reply_markup, parse_mode='HTML')
            else:
                await context.bot.send_message(chat_id=chat_id, text=new_text, reply_markup=new_reply_markup, parse_mode='HTML')

    # --- Cenário 2: A chamada veio de um COMANDO (query NÃO existe) ---
    else:
        # Simplesmente envia uma nova mensagem
        if new_media_file_id:
            if new_media_type == 'video':
                await context.bot.send_video(chat_id=chat_id, video=new_media_file_id, caption=new_text, reply_markup=new_reply_markup, parse_mode='HTML')
            else:
                await context.bot.send_photo(chat_id=chat_id, photo=new_media_file_id, caption=new_text, reply_markup=new_reply_markup, parse_mode='HTML')
        else:
            await context.bot.send_message(chat_id=chat_id, text=new_text, reply_markup=new_reply_markup, parse_mode='HTML')
            
def create_progress_bar(current: int, required: int, length: int = 10, fill_char: str = '⬛️', empty_char: str = '◻️') -> str:
    """Cria uma barra de progresso em texto."""
    if required <= 0:
        return f"[{fill_char * length}]"
        
    progress = min(1.0, current / required)
    filled_length = int(progress * length)
    bar = fill_char * filled_length + empty_char * (length - filled_length)
    return f"[{bar}]"
            
def _i(v) -> int:
    """Converte qualquer valor para inteiro (com round) de forma segura."""
    try:
        return int(round(float(v)))
    except (ValueError, TypeError):
        try:
            return int(v)
        except (ValueError, TypeError):
            return 0

def render_item_stats_short(item_instance: dict, player_class: str) -> str:
    """
    Renderiza uma string curta com os status principais de um item.
    Esta função agora vive em utils.py para evitar dependências cíclicas.
    """
    stats = item_instance.get("stats", {})
    enchants = item_instance.get("enchantments", {}) # Considera encantamentos também
    parts = []
    
    # Mapeamento de emojis (pode ser movido para o topo se preferir)
    emoji_map = {
        'attack': '⚔️', 'defense': '🛡️', 'initiative': '🏃‍♂️', 'luck': '🍀', 'max_hp': '❤️'
    }

    # Combina stats base e encantamentos
    combined_stats = {}
    for stat, value in stats.items():
        if stat in emoji_map:
            combined_stats[stat] = combined_stats.get(stat, 0) + _i(value)
            
    for stat, data in enchants.items():
        if stat in emoji_map:
             combined_stats[stat] = combined_stats.get(stat, 0) + _i((data or {}).get('value', 0))

    # Formata a saída
    for stat, value in combined_stats.items():
         if value > 0:
            parts.append(f"{emoji_map[stat]}{value}")
            
    return " ".join(parts)

# =============================================================================

def obter_titulo_e_icones_por_regiao(regiao_id: str) -> tuple[str, str]:
    dados = game_data.REGIONS_DATA.get(regiao_id)
    if not dados:
        return ("🌍 Região Desconhecida", "⚔️ 𝑽𝑺 ❓")

    nome = dados.get("display_name", regiao_id.replace("_", " ").title())
    emoji = dados.get("emoji", "❓")
    return (f"{emoji} {nome}", f"⚔️ 𝑽𝑺 {emoji}")

# ---------- Helpers de exibição (inteiros) ----------
def _fmt_player_stats_as_ints(total_stats: dict) -> tuple[int, int, int, int, int]:
    """
    Converte o dict retornado por get_player_total_stats em inteiros para exibição.
    """
    p_max_hp = _i(total_stats.get('max_hp', 0))
    p_atk    = _i(total_stats.get('attack', 0))
    p_def    = _i(total_stats.get('defense', 0))
    p_ini    = _i(total_stats.get('initiative', 0))
    p_srt    = _i(total_stats.get('luck', 0))
    return p_max_hp, p_atk, p_def, p_ini, p_srt

# SUBSTITUA a sua função format_combat_message por esta versão final
def _format_log_line(line: str) -> str:
    """Formata linhas de log de batalha para caberem na caixa estilizada."""
    
    # Substituições para simplificar o log
    line = line.replace("💥💥 𝐌𝐄𝐆𝐀 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎!", "💥💥 MEGA CRÍTICO!")
    line = line.replace("💥 𝐃𝐀𝐍𝐎 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎!", "💥 CRÍTICO!")
    line = line.replace("‼️ 𝕄𝔼𝔾𝔸 ℂℝ𝕀́𝐓𝐈ℂ𝕆 𝕚𝕟𝕚𝕞𝕚𝕘𝕠!", "‼️ MEGA CRÍTICO I.")
    line = line.replace("❗️ 𝔻𝔸𝐍𝐎 ℂℝ𝕀́𝐓𝐈ℂ𝕆 𝕚𝕟𝕚𝕞𝕚𝕘𝕠!", "❗️ CRÍTICO I.")
    line = line.replace("⚡ 𝐀𝐓𝐀𝐐𝐔𝐄 𝐃𝐔𝐏𝐋𝐎!", "⚡ ATAQUE DUPLO!")
    line = line.replace("ataca e causa", "causa")
    line = line.replace("recebe", "recebe")
    
    return html.escape(line) # Garante que o HTML é seguro para o bloco <code>

# Em handlers/utils.py

async def format_combat_message(player_data: dict, player_stats: dict | None = None) -> str:
    """
    Formata o estado atual do combate (Início da Luta).
    """
    if not player_data: return "Erro: Dados do jogador não encontrados."
    state = player_data.get('player_state', {})
    if state.get("action") != "in_combat": return "Você não está em combate."
    details = state.get('details', {})
    log_raw = details.get('battle_log', [])

    # 1. Carrega Stats
    if player_stats is None:
        player_stats = await player_manager.get_player_total_stats(player_data)
        if not player_stats: return "Erro: Não foi possível carregar stats do jogador."

    # 2. Dados da Região
    regiao_id = details.get('region_key', 'reino_eldora')
    region_info = (game_data.REGIONS_DATA or {}).get(regiao_id, {})
    titulo = f"{region_info.get('emoji', '🗺️')} <b>{region_info.get('display_name', 'Região')}</b>"

    # --- CORREÇÃO DO NOME ---
    # Pega o nome do personagem. Se tiver emoji de classe no nome, ele virá junto.
    p_name = player_data.get('character_name', 'Herói')
    m_name = details.get('monster_name', 'Inimigo')

    # 3. Status Jogador
    p_max_hp, p_atk, p_def, p_ini, p_srt = _fmt_player_stats_as_ints(player_stats)
    p_current_hp = max(0, min(_i(player_data.get('current_hp', p_max_hp)), p_max_hp))
    p_max_mp = _i(player_stats.get('max_mana', 10))
    p_current_mp = max(0, min(_i(player_data.get('current_mp', p_max_mp)), p_max_mp))
    
    # 4. Status Monstro
    m_hp = _i(details.get('monster_hp', 0))
    m_max = _i(details.get('monster_max_hp', 0))
    m_atk = _i(details.get('monster_attack', 0))
    m_def = _i(details.get('monster_defense', 0))
    m_ini = _i(details.get('monster_initiative', 0))
    m_srt = _i(details.get('monster_luck', 0))

    # --- BLOCO VISUAL (Padronizado) ---
    player_block = (
        f"<b>ㅤㅤㅤㅤㅤㅤ👤 {p_name}</b>\n"
        f"❤️ 𝐇𝐏: {p_current_hp}/{p_max_hp}\n"
        f"💙 𝐌𝐏: {p_current_mp}/{p_max_mp}\n"
        f"⚔️ 𝐀𝐓𝐊: {p_atk} ­ㅤ­ㅤ­­ㅤ­ㅤㅤ­ㅤ­ㅤ 🛡 𝐃𝐄𝐅: {p_def}\n"
        f"🏃‍♂️ 𝐕𝐄𝐋: {p_ini}  ­ㅤ­ㅤ­ㅤ­ㅤㅤ ­ㅤ­ㅤ🍀 𝐒𝐑𝐓: {p_srt}\n"
    )

    monster_block = (
        f"<b>­ㅤ­ㅤ­ㅤㅤ­­ㅤ­­­­👹 {m_name}</b>\n"
        f"❤️ 𝐇𝐏: {m_hp}/{m_max}\n"
        f"⚔️ 𝐀𝐓𝐊: {m_atk} ­ㅤ­ㅤ ­ㅤ­ㅤㅤ ­ㅤ­ㅤ🛡 𝐃𝐄𝐅: {m_def}\n"
        f"🏃‍♂️ 𝐕𝐄𝐋: {m_ini}  ­ㅤ­ㅤ ­ㅤ­ㅤㅤ ­ㅤ­ㅤ🍀 𝐒𝐑𝐓: {m_srt}\n"
    )

    log_lines = [_format_log_line(line) for line in log_raw[-6:]] 
    log_block = "\n".join(log_lines)
    if not log_block: log_block = "Aguardando sua ação..."

    final_message = (
        f"{titulo}\n"
        f"⚔️ 𝑽𝑺 <b>{m_name}</b>\n"
        "╔════════════ ◆◈◆ ════════════╗\n"
        f"{player_block}\n"
        "══════════════ ⚔️ ═════════════\n"
        f"{monster_block}\n"
        "══════════════ 📜 ═════════════\n"
        f"<code>{log_block}</code>\n"
        "╚════════════ ◆◈◆ ════════════╝"
    )

    return final_message


async def format_combat_message_from_cache(battle_cache: dict) -> str:
    """
    Formata a mensagem de combate lendo do cache (Durante a Luta).
    """
    if not battle_cache: return "Erro: Cache de batalha não encontrado."

    region_key = battle_cache.get('region_key', 'reino_eldora')
    region_info = (game_data.REGIONS_DATA or {}).get(region_key, {})
    titulo = f"{region_info.get('emoji', '🗺️')} <b>{region_info.get('display_name', 'Região')}</b>"

    # --- CORREÇÃO CRÍTICA DO NOME ---
    # 1. Tenta pegar 'player_name' direto do cache
    p_name = battle_cache.get('player_name')
    
    # 2. Se não achar, tenta pegar de DENTRO dos stats (onde geralmente fica salvo)
    if not p_name:
         p_name = battle_cache.get('player_stats', {}).get('character_name')

    # 3. Último caso, usa Herói
    if not p_name:
        p_name = 'Herói'

    m_stats = battle_cache.get('monster_stats', {})
    m_name = m_stats.get('name', 'Inimigo')

    p_stats = battle_cache.get('player_stats', {})
    p_max_hp, p_atk, p_def, p_ini, p_srt = _fmt_player_stats_as_ints(p_stats)
    p_current_hp = max(0, min(_i(battle_cache.get('player_hp', p_max_hp)), p_max_hp))
    p_max_mp = _i(p_stats.get('max_mana', 10))
    p_current_mp = max(0, min(_i(battle_cache.get('player_mp', p_max_mp)), p_max_mp))
    
    m_hp = _i(m_stats.get('hp', 0))
    m_max = _i(m_stats.get('max_hp', 0))
    m_atk = _i(m_stats.get('attack', 0))
    m_def = _i(m_stats.get('defense', 0))
    m_ini = _i(m_stats.get('initiative', 0))
    m_srt = _i(m_stats.get('luck', 0))

    # --- BLOCO VISUAL (Idêntico ao de cima) ---
    player_block = (
        f"<b>ㅤㅤㅤㅤㅤㅤ👤 {p_name}</b>\n"
        f"❤️ 𝐇𝐏: {p_current_hp}/{p_max_hp}\n"
        f"💙 𝐌𝐏: {p_current_mp}/{p_max_mp}\n"
        f"⚔️ 𝐀𝐓𝐊: {p_atk} ­ㅤ­ㅤ ­ㅤ­ㅤ­ㅤ­ㅤ 🛡 𝐃𝐄𝐅: {p_def}\n"
        f"🏃‍♂️ 𝐕𝐄𝐋: {p_ini}   ­ㅤ­ㅤ­ㅤ­ㅤ ­ㅤ­ㅤ🍀 𝐒𝐑𝐓: {p_srt}\n"
    )

    monster_block = (
        f"<b>­ㅤ­ㅤ­ㅤ­­ㅤ­­ㅤ­­👹 {m_name}</b>\n"
        f"❤️ 𝐇𝐏: {m_hp}/{m_max}\n"
        f"⚔️ 𝐀𝐓𝐊: {m_atk} ­ㅤ­ㅤ ­ㅤ­ㅤ ­ㅤ­ㅤ🛡 𝐃𝐄𝐅: {m_def}\n"
        f"🏃‍♂️ 𝐕𝐄𝐋: {m_ini}  ­ㅤ­ㅤ ­ㅤ­ㅤ ­ㅤ­ㅤ🍀 𝐒𝐑𝐓: {m_srt}\n"
    )

    log_raw = battle_cache.get('battle_log', [])
    log_lines = [_format_log_line(line) for line in log_raw[-6:]] 
    log_block = "\n".join(log_lines)
    if not log_block: log_block = "Aguardando sua ação..."

    final_message = (
        f"{titulo}\n"
        f"⚔️ 𝑽𝑺 <b>{m_name}</b>\n"
        "╔════════════ ◆◈◆ ════════════╗\n"
        f"{player_block}\n"
        "══════════════ ⚔️ ═════════════\n"
        f"{monster_block}\n"
        "══════════════ 📜 ═════════════\n"
        f"<code>{log_block}</code>\n"
        "╚════════════ ◆◈◆ ════════════╝"
    )

    return final_message

async def format_dungeon_combat_message(dungeon_instance: dict, all_players_data: dict) -> str:
    """
    Formata a mensagem de combate para dungeons (multi-participantes).
    """
    cs = dungeon_instance.get('combat_state', {})

    header = ["╔════════════ ◆◈◆ ════════════╗"]

    # Heróis
    heroes_blocks = []
    for player_id, combat_data in (cs.get('participants', {}) or {}).items():
        player_full_data = all_players_data.get(player_id)
        if not player_full_data:
            continue

        total_stats = await player_manager.get_player_total_stats(player_full_data)
        max_hp, atk, defense, vel, srt = _fmt_player_stats_as_ints(total_stats)
        current_hp = _i(combat_data.get('hp', 0))
        max_mp = _i(total_stats.get('max_mana', 10))
        current_mp = _i(combat_data.get('mp', max_mp)) # Assume que o 'mp' do combate está em combat_data
        
        player_block = (
            f"<b>{combat_data.get('name','Herói')}</b>\n"
            f"❤️ 𝐇𝐏: {current_hp}/{max_hp}\n"
            f"💙 𝐌𝐏: {current_mp}/{max_mp}\n"
            f"⚔️ 𝐀𝐓𝐊: {atk} 🛡️ 𝐃𝐄𝐅: {defense}\n"
            f"🏃‍♂️ 𝐕𝐄𝐋: {vel} 🍀 𝐒𝐑𝐓: {srt}"
        )
        heroes_blocks.append(player_block)

    # Inimigos
    enemies_blocks = []
    for monster_key, monster_data in (cs.get('monsters', {}) or {}).items():
        if _i(monster_data.get('hp', 0)) > 0:
            m_hp = _i(monster_data.get('hp', 0))
            m_max = _i(monster_data.get('max_hp', 0))
            m_atk = _i(monster_data.get('attack', 0))
            m_def = _i(monster_data.get('defense', 0))
            m_vel = _i(monster_data.get('initiative', 0))
            m_srt = _i(monster_data.get('luck', 0))

            monster_block = (
                f"<b>{monster_data.get('name','Inimigo')}</b>\n"
                f"❤️ 𝐇𝐏: {m_hp}/{m_max}\n"
                f"⚔️ 𝐀𝐓𝐊: {m_atk} 🛡️ 𝐃𝐄𝐅: {m_def}\n"
                f"🏃‍♂️ 𝐕𝐄𝐋: {m_vel} 🍀 𝐒𝐑𝐓: {m_srt}"
            )
            enemies_blocks.append(monster_block)

    # Log
    log_lines = ["═════════════ ◆◈◆ ═════════════"]
    battle_log = cs.get('battle_log', []) or []
    log_lines.extend([html.escape(str(x)) for x in battle_log[-4:]])

    footer = ["╚════════════ ◆◈◆ ════════════╝"]

    heroes_section = "\n\n".join(heroes_blocks)
    enemies_section = "═════════════════════════════\n" + "\n\n".join(enemies_blocks)

    return "\n".join(header + [heroes_section, enemies_section] + log_lines + footer)

# =============================================================================
# 💀 FORMATADOR ESPECÍFICO PARA CATACUMBAS (ESTILO DETALHADO)
# =============================================================================

async def format_catacomb_interface(session: dict, current_user_id: str, all_players_data: dict) -> str:
    """
    Gera a interface visual da Raid. 
    NOTA: current_user_id agora é STRING para compatibilidade.
    """
    
    # 1. CABEÇALHO
    floor = session.get("current_floor", 1)
    total_floors = session.get("total_floors", 3)
    header = f"🏰 **CATACUMBAS - ANDAR {floor}/{total_floors}**\n"

    # 2. BLOCO DOS HERÓIS (PLAYERS)
    heroes_blocks = []
    players_in_session = session.get("players", {}) # Dict {id: name}
    
    for pid in players_in_session:
        p_data = all_players_data.get(pid)
        if not p_data: continue

        # Calcula Stats Totais
        stats = await player_manager.get_player_total_stats(p_data)
        
        p_name = html.escape(p_data.get("character_name", "Herói")[:15])
        p_max_hp = _i(stats.get("max_hp", 100))
        p_current_hp = _i(p_data.get("current_hp", p_max_hp))
        p_max_mp = _i(stats.get("max_mana", 10))
        p_current_mp = _i(p_data.get("current_mp", p_max_mp))
        
        p_atk = _i(stats.get("attack", 0))
        p_def = _i(stats.get("defense", 0))
        p_ini = _i(stats.get("initiative", 0))
        p_srt = _i(stats.get("luck", 0))
        
        # Marcador visual se for o usuário atual (Compatibilidade int/str)
        if str(pid) == str(current_user_id):
            p_name = f"👉 {p_name}"
        if p_current_hp <= 0:
            p_name = f"💀 {p_name}"

        # 🔥 SEU BLOCO DE PLAYER 🔥
        player_block = (
            f"<b>{p_name}</b>\n"
            f"❤️ 𝐇𝐏: {p_current_hp}/{p_max_hp}\n"
            f"💙 𝐌𝐏: {p_current_mp}/{p_max_mp}\n"
            f"⚔️ 𝐀𝐓𝐊: {p_atk} | 🛡 𝐃𝐄𝐅: {p_def}\n"
            f"🏃‍♂️ 𝐕𝐄𝐋: {p_ini} | 🍀 𝐒𝐑𝐓: {p_srt}"
        )
        heroes_blocks.append(player_block)

    # 3. BLOCO DOS MONSTROS (MOBS)
    enemies_list = session.get("enemies", [])
    if not enemies_list and session.get("boss"):
        enemies_list = [session.get("boss")]

    mobs_blocks = []
    for idx, mob in enumerate(enemies_list):
        
        m_hp = _i(mob.get("current_hp", 0))
        if m_hp <= 0 and len(enemies_list) > 1: 
            continue # Se tem vários, esconde os mortos

        m_max = _i(mob.get("max_hp", 100))
        m_name = html.escape(mob.get("name", f"Inimigo {idx+1}"))
        
        m_atk = _i(mob.get("attack", 0))
        m_def = _i(mob.get("defense", 0))
        m_ini = _i(mob.get("initiative", mob.get("speed", 0)))
        m_srt = _i(mob.get("luck", 0))
        
        # Ícone de Chefe
        if mob.get("is_boss"):
            m_name = f"👿 {m_name}"
        else:
            m_name = f"👹 {m_name}"

        # 🔥 SEU BLOCO DE MONSTRO 🔥
        monster_block = (
            f"<b>{m_name}</b>\n"
            f"❤️ 𝐇𝐏: {m_hp}/{m_max}\n"
            f"⚔️ 𝐀𝐓𝐊: {m_atk} | 🛡 𝐃𝐄𝐅: {m_def}\n"
            f"🏃‍♂️ 𝐕𝐄𝐋: {m_ini} | 🍀 𝐒𝐑𝐓: {m_srt}"
        )
        mobs_blocks.append(monster_block)

    # 4. LOG
    log_raw = session.get("turn_log", [])
    log_lines = [_format_log_line(l) for l in log_raw[-4:]]
    log_block = "\n".join(log_lines) if log_lines else "O combate começou!"

    # 5. MONTAGEM FINAL
    heroes_section = "\n───────────────\n".join(heroes_blocks)
    mobs_section = "\n───────────────\n".join(mobs_blocks)

    final_msg = (
        f"{header}\n"
        f"╔═══════════ 👥 ═══════════╗\n"
        f"{heroes_section}\n"
        f"╠═══════════ ⚔️ ═══════════╣\n"
        f"{mobs_section}\n"
        f"╚═══════════════════════════╝\n"
        f"📜 <b>Log:</b>\n"
        f"<code>{log_block}</code>"
    )
    
    return final_msg

# ---------- Utilidades de dungeon ----------
def get_monster_template(dungeon_instance: dict, monster_key_in_combat: str) -> Optional[dict]:
    """
    Busca o modelo base de um monstro da dungeon usando a chave em combate.
    """
    cs = dungeon_instance.get('combat_state', {}) or {}
    monsters = cs.get('monsters', {}) or {}

    base_id = (monsters.get(monster_key_in_combat) or {}).get('base_id')
    if not base_id:
        return None

    dungeon_blueprint_id = dungeon_instance.get('dungeon_id')
    if not dungeon_blueprint_id:
        return None

    all_monsters = game_data.MONSTERS_DATA.get(dungeon_blueprint_id, []) or []
    return next((m for m in all_monsters if m.get('id') == base_id), None)

# ---------- Renderização de equipamentos/inventário ----------
def render_equipment_line(slot: str, uid: str | None, inst: dict | None, player_class: str) -> str:
    emoji_slot = game_data.SLOT_EMOJI.get(slot, "📦")
    if not inst:
        return f"{emoji_slot} <b>{slot.capitalize()}</b>: —"
    base = inst.get("base_id","")
    name = game_data.ITEM_BASES.get(base, {}).get("display_name", base)
    rarity = (inst.get("rarity","comum") or "comum").capitalize()
    cur_d, max_d = (inst.get("durability") or [0,0])
    stats = render_item_stats_short(inst, player_class)
    return f"{emoji_slot} <b>{slot.capitalize()}</b>: 『[{cur_d}/{max_d}] {name} [{rarity}]』 {stats}"

def render_inventory_row(uid: str, inst: dict, player_class: str) -> str:
    base = inst.get("base_id","")
    name = game_data.ITEM_BASES.get(base, {}).get("display_name", base)
    rarity = (inst.get("rarity","comum") or "comum").capitalize()
    cur_d, max_d = (inst.get("durability") or [0,0])
    stats = render_item_stats_short(inst, player_class)
    return f"『[{cur_d}/{max_d}] {name} [{rarity}]』 {stats}  <code>{uid[:8]}</code>"

# ---------- PvP (inteiros) ----------

async def format_pvp_result(resultado: dict, vencedor_data: Optional[dict], perdedor_data: Optional[dict]) -> tuple[str, InlineKeyboardMarkup]:
    """
    Formata o resultado de uma batalha PvP no estilo visual do bot.
    """
    log_texto = "\n".join([html.escape(str(x)) for x in resultado.get('log', [])]) 

    nome_vencedor = (vencedor_data or {}).get('character_name', 'Aventureiro(a)')
    nome_perdedor = (perdedor_data or {}).get('character_name', 'Oponente')

    if resultado.get('vencedor_id'):
    
        vstats = await player_manager.get_player_total_stats(vencedor_data or {})
        pstats = await player_manager.get_player_total_stats(perdedor_data or {})

        v_max_hp, v_atk, v_def, v_vel, v_srt = _fmt_player_stats_as_ints(vstats)
        p_max_hp, p_atk, p_def, p_vel, p_srt = _fmt_player_stats_as_ints(pstats)

        v_max_mp = _i(vstats.get('max_mana', 10))
        p_max_mp = _i(pstats.get('max_mana', 10))
        
        v_hp = _i((vencedor_data or {}).get('current_hp', v_max_hp))
        p_hp = _i((perdedor_data or {}).get('current_hp', p_max_hp))
        
        v_mp = _i((vencedor_data or {}).get('current_mp', v_max_mp))
        p_mp = _i((perdedor_data or {}).get('current_mp', p_max_mp))
   
        header = "╔════════════ ◆◈◆ ════════════╗\n"
        divider = "══════════════════════════════\n"
        footer = "╚════════════ ◆◈◆ ════════════╝"

        mensagem_texto = (
            f"{header}"
            f"<b>{html.escape(nome_vencedor)}</b>\n"
            f"❤️ 𝐇𝐏: {v_hp}/{v_max_hp}\n"
            f"💙 𝐌𝐏: {v_mp}/{v_max_mp}\n" 
            f"⚔️ 𝐀𝐓𝐊: {v_atk} 🛡️ 𝐃𝐄𝐅: {v_def}\n"
            f"🏃‍♂️ 𝐕𝐄𝐋: {v_vel} 🍀 𝐒𝐑𝐓: {v_srt}\n"
            f"{divider}"
            f"<b>{html.escape(nome_perdedor)}</b>\n"
            f"❤️ 𝐇𝐏: {p_hp}/{p_max_hp}\n"
            f"💙 𝐌𝐏: {p_mp}/{p_max_mp}\n" 
            f"⚔️ 𝐀𝐓𝐊: {p_atk} 🛡️ 𝐃𝐄𝐅: {p_def}\n"
            f"🏃‍♂️ 𝐕𝐄𝐋: {p_vel} 🍀 𝐒𝐑𝐓: {p_srt}\n"
            f"═════════════ ◆◈◆ ═════════════\n"
            f"📜 Log da Batalha:\n"
            f"<code>{log_texto}</code>\n"
            f"\n🎉 <b>{html.escape(nome_vencedor)} 𝒗𝒆𝒏𝒄𝒆𝒖 𝒂 𝒃𝒂𝒕𝒂𝒍𝒉𝒂!</b>\n"
            f"{footer}"
        )
    else:
        mensagem_texto = (
            f"⚔️ <b>𝑨 𝑩𝑨𝑻𝑨𝑳𝑯𝑨 𝑻𝑬𝑹𝑴𝑰𝑵𝑶𝑼 𝑬𝑴 𝑬𝑴IMATE!</b> ⚔️\n\n"
            f"📜 Log da Batalha:\n"
            f"<code>{log_texto}</code>\n"
        )

    keyboard = [[InlineKeyboardButton("⚔️ 𝐋𝐮𝐭𝐚𝐫 𝐍𝐨𝐯𝐚𝐦𝐞𝐧𝐭𝐞 ⚔️", callback_data='pvp_arena')]]
    return mensagem_texto, InlineKeyboardMarkup(keyboard)
    
def format_buffs_text(buffs_dict: dict) -> str:
    """Formata um dicionário de buffs para uma string legível."""
    if not buffs_dict:
        return "   - Nenhum\n"
    text = ""
    if buffs_dict.get("xp_bonus_percent"):
        text += f"   - Bónus de XP: +{buffs_dict['xp_bonus_percent']}%\n"
    if buffs_dict.get("gold_bonus_percent"):
        text += f"   - Bónus de Ouro: +{buffs_dict['gold_bonus_percent']}%\n"
    return text if text else "   - Nenhum\n"

def _format_effects(entity: dict) -> str:
    """
    Formata efeitos ativos (buffs/debuffs) de uma entidade.
    Espera algo como entity["_effects"] = { "bleed": {...}, ... }
    """
    effects = entity.get("_effects") or {}
    if not effects:
        return ""

    icons = {
        "bleed": "🩸",
        "poison": "☠️",
        "stun": "💫",
        "shield": "🛡",
        "regen": "✨"
    }

    parts = []
    for eid, data in effects.items():
        icon = icons.get(eid, "🔹")
        stacks = data.get("stacks", 1)
        parts.append(f"{icon}{stacks}")

    return " " + " ".join(parts)



async def format_catacomb_interface(session: dict, user_id, all_players_data: dict) -> str:
    """
    Interface visual da dungeon em grupo com suporte a Turno Sequencial.
    Blindada para identificação via ObjectID (strings).
    """

    # 1. Identificação do Turno Atual (Blindagem de ObjectID)
    turn_order = session.get("turn_order", [])
    current_idx = session.get("current_turn_idx", 0)
    
    # Garantimos que o ID do ator atual seja tratado como string para comparação
    current_actor_id = str(turn_order[current_idx]) if turn_order else None
    user_id_str = str(user_id) 

    # =========================
    # CABEÇALHO
    # =========================
    floor = session.get("current_floor", 1)
    leader_id = str(session.get("leader_id"))
    scaling = session.get("scaling_factor", 1.0)

    header = (
        f"🏰 **CATACUMBAS – ANDAR {floor}**\n"
        f"👑 Líder: {all_players_data.get(leader_id, {}).get('character_name', '???')}\n"
        f"👥 Grupo: {len(session.get('players', {}))}/6 | ⚔️ Desafio: {scaling}x\n"
    )

    # =========================
    # GRUPO (PLAYERS)
    # =========================
    group_lines = ["\n━━━━━━━━━━━━━━━━━━\n👥 **HERÓIS**"]

    for pid in session.get("players", {}):
        pid_str = str(pid) # Normalização do ObjectID do player
        pdata = all_players_data.get(pid_str, {})
        
        name = pdata.get("character_name") or pdata.get("name") or "Herói"
        hp = pdata.get("current_hp", 0)
        max_hp = pdata.get("max_hp") or pdata.get("hp") or "?"

        effects = _format_effects(pdata)
        
        # Marcadores Visuais (Comparação de Strings)
        is_my_turn = (pid_str == current_actor_id)
        turn_marker = "⚔️ " if is_my_turn else "  "
        marker = "👉" if pid_str == user_id_str else "  "

        # Se o HP for 0, marca como morto
        name_display = f"💀 {name}" if hp <= 0 else name

        group_lines.append(
            f"{marker}{turn_marker}{name_display} — ❤️ {hp}/{max_hp}{effects}"
        )

    # =========================
    # INIMIGO (BOSS/MOB)
    # =========================
    enemy = session.get("boss")
    enemy_block = []

    if enemy:
        is_boss_turn = (current_actor_id == "boss")
        boss_marker = "⚔️ " if is_boss_turn else ""
        
        e_name = enemy.get("name", "Inimigo")
        e_hp = enemy.get("current_hp", 0)
        e_max = enemy.get("max_hp", "?")
        atk = enemy.get("attack", "?")
        df = enemy.get("defense", "?")

        effects = _format_effects(enemy)

        enemy_block = [
            "\n━━━━━━━━━━━━━━━━━━",
            f"{boss_marker}👹 **INIMIGO**",
            f"<b>{e_name}</b>",
            f"❤️ {e_hp}/{e_max}",
            f"⚔ ATK {atk} | 🛡 DEF {df}{effects}"
        ]

    # =========================
    # STATUS DO TURNO
    # =========================
    if current_actor_id == "boss":
        turn_info = f"\n━━━━━━━━━━━━━━━━━━\n⚠️ **TURNO DO INIMIGO:** {enemy.get('name')} está agindo..."
    elif current_actor_id == user_id_str:
        turn_info = "\n━━━━━━━━━━━━━━━━━━\n🔥 **SEU TURNO!** Escolha sua ação abaixo."
    else:
        # Busca o nome do aliado que está agindo agora
        actor_data = all_players_data.get(current_actor_id, {})
        actor_name = actor_data.get("character_name") or actor_data.get("name") or "Companheiro"
        turn_info = f"\n━━━━━━━━━━━━━━━━━━\n⏳ **TURNO ATUAL:** {actor_name} agindo..."

    # =========================
    # LOG RECENTE
    # =========================
    logs = session.get("turn_log", [])[-3:]
    log_block = []
    if logs:
        log_block.append("\n━━━━━━━━━━━━━━━━━━\n📜 **ÚLTIMAS AÇÕES**")
        for l in logs:
            log_block.append(f"• {l}")

    # =========================
    # MONTAGEM FINAL
    # =========================
    full_text = "\n".join(
        [header] +
        group_lines +
        enemy_block +
        [turn_info] +
        log_block
    )

    return full_text
