# handlers/utils.py
import logging
import html
from telegram import Update
from telegram.error import BadRequest
from typing import Optional
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from modules import player_manager, game_data
from telegram import Update


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
        await query.answer()
        
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
    """
    Converte o dict retornado por get_player_total_stats em inteiros para exibição.
    (Mantido)
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

async def format_combat_message(player_data: dict, player_stats: dict | None = None) -> str:
    """
    Formata o estado atual do combate com a estrutura original e async correto.
    """
    if not player_data: return "Erro: Dados do jogador não encontrados."
    state = player_data.get('player_state', {})
    if state.get("action") != "in_combat": return "Você não está em combate."
    details = state.get('details', {})
    log_raw = details.get('battle_log', [])

    # 1. Carrega Stats Totais (se não passados)
    if player_stats is None:
        player_stats = await player_manager.get_player_total_stats(player_data)
        if not player_stats: return "Erro: Não foi possível carregar stats do jogador."

    # 2. Obter Dados da Região e Nomes
    regiao_id = details.get('region_key', 'reino_eldora')
    region_info = (game_data.REGIONS_DATA or {}).get(regiao_id, {})
    titulo = f"{region_info.get('emoji', '🗺️')} <b>{region_info.get('display_name', 'Região')}</b>"

    p_name = player_data.get('character_name', 'Herói')
    m_name = details.get('monster_name', 'Inimigo')

    # 3. Status do Jogador (Usa os stats já carregados ou passados)
    p_max_hp, p_atk, p_def, p_ini, p_srt = _fmt_player_stats_as_ints(player_stats)
    p_current_hp = max(0, min(_i(player_data.get('current_hp', p_max_hp)), p_max_hp))
    p_max_mp = _i(player_stats.get('max_mana', 10))
    p_current_mp = max(0, min(_i(player_data.get('current_mp', p_max_mp)), p_max_mp))
    
    # 4. Status do Monstro
    m_hp = _i(details.get('monster_hp', 0))
    m_max = _i(details.get('monster_max_hp', 0))
    m_atk = _i(details.get('monster_attack', 0))
    m_def = _i(details.get('monster_defense', 0))
    m_ini = _i(details.get('monster_initiative', 0))
    m_srt = _i(details.get('monster_luck', 0))

    # 5. Blocos de Status Consolidados
    player_block = (
        f"<b>{p_name}</b>\n"
        f"❤️ 𝐇𝐏: {p_current_hp}/{p_max_hp}\n"
        f"💙 𝐌𝐏: {p_current_mp}/{p_max_mp}\n"
        f"⚔️ 𝐀𝐓𝐊: {p_atk} | 🛡 𝐃𝐄𝐅: {p_def}\n"
        f"🏃‍♂️ 𝐕𝐄𝐋: {p_ini}  | 🍀 𝐒𝐑𝐓: {p_srt}"
    )

    monster_block = (
        f"<b>{m_name}</b>\n"
        f"❤️ 𝐇𝐏: {m_hp}/{m_max}\n"
        f"⚔️ 𝐀𝐓𝐊: {m_atk} | 🛡 𝐃𝐄𝐅: {m_def}\n"
        f"🏃‍♂️ 𝐕𝐄𝐋: {m_ini}  | 🍀 𝐒𝐑𝐓: {m_srt}"
    )

    # 6. Montagem do Log
    log_lines = [_format_log_line(line) for line in log_raw[-4:]] # Pega as últimas 4 linhas
    log_block = "\n".join(log_lines)
    # Mensagem padrão se o log estiver vazio (início do combate)
    if not log_block:
         log_block = "Aguardando sua ação..."

    # 7. Construção da Caixa Final (Usando a tua estrutura original)
    final_message = (
        f"{titulo}\n"
        f"⚔️ 𝑽𝑺 <b>{m_name}</b>\n"
        "╔════════════ ◆◈◆ ════════════╗\n"
        # Bloco do Jogador
        f"{player_block}\n"
        "══════════════════════════════\n"
        # Bloco do Monstro
        f"{monster_block}\n"
        "═════════════ 📜 ═════════════\n"
        # Log formatado dentro de <code>
        f"<code>{log_block}</code>\n"
        "╚════════════ ◆◈◆ ════════════╝"
    )

    return final_message
# ---------- Mensagem de dungeon (sempre inteiros) ----------
# Em: handlers/utils.py


async def format_dungeon_combat_message(dungeon_instance: dict, all_players_data: dict) -> str:
    """
    Formata a mensagem de combate para dungeons (multi-participantes).
    (VERSÃO CORRIGIDA E LIMPA)
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

async def format_catacomb_interface(session: dict, current_user_id: int, all_players_data: dict) -> str:
    """
    Gera a interface visual da Raid usando os blocos detalhados solicitados.
    Suporta múltiplos jogadores e múltiplos mobs (se existirem na sessão).
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
        
        # Marcador visual se for o usuário atual
        if pid == current_user_id:
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
    # Tenta pegar lista 'enemies' (se você implementou 6 mobs), senão pega o 'boss' único e põe numa lista
    enemies_list = session.get("enemies", [])
    if not enemies_list and session.get("boss"):
        enemies_list = [session.get("boss")]

    mobs_blocks = []
    for idx, mob in enumerate(enemies_list):
        # Se o mob já morreu (HP 0), podemos pular ou mostrar como morto
        # Aqui vou mostrar mesmo morto para manter o layout fixo dos 6 mobs se desejar
        
        m_hp = _i(mob.get("current_hp", 0))
        if m_hp <= 0 and len(enemies_list) > 1: 
            continue # Se tem vários, esconde os mortos para economizar espaço

        m_max = _i(mob.get("max_hp", 100))
        m_name = html.escape(mob.get("name", f"Inimigo {idx+1}"))
        
        # Se for Boss/Mob único, tentamos pegar stats detalhados se existirem no dict
        # Se não existirem (mob simples), usamos 0 ou valor padrão
        m_atk = _i(mob.get("attack", 0))
        m_def = _i(mob.get("defense", 0))
        m_ini = _i(mob.get("initiative", mob.get("speed", 0))) # Tenta initiative ou speed
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
    # Junta todos os heróis separados por linha vazia
    heroes_section = "\n───────────────\n".join(heroes_blocks)
    
    # Junta todos os mobs separados por linha vazia
    mobs_section = "\n───────────────\n".join(mobs_blocks)

    final_msg = (
        f"{header}\n"
        f"╔═══════════ 👥 ═══════════╗\n"
        f"{heroes_section}\n"
        f"╠═══════════ ⚔️ ═══════════╣\n"
        f"{mobs_section}\n"
        f"╚══════════════════════════╝\n"
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
    (VERSÃO CORRIGIDA COM MANA e ASYNC)
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
    # Adicione aqui a formatação para outros buffs que você tiver
    return text if text else "   - Nenhum\n"

# Em: handlers/utils.py

# ... (imports no topo) ...
# ... (função _format_log_line) ...


# --- 👇 ADICIONE ESTA NOVA FUNÇÃO COMPLETA 👇 ---

async def format_combat_message_from_cache(battle_cache: dict) -> str:
    """
    Formata a mensagem de combate (para Caçadas) lendo os dados 
    diretamente do 'battle_cache' (context.user_data['battle_cache']).
    """
    if not battle_cache:
        return "Erro: Cache de batalha não encontrado."

    # 1. Obter Dados da Região e Nomes
    region_key = battle_cache.get('region_key', 'reino_eldora')
    region_info = (game_data.REGIONS_DATA or {}).get(region_key, {})
    titulo = f"{region_info.get('emoji', '🗺️')} <b>{region_info.get('display_name', 'Região')}</b>"

    p_name = battle_cache.get('player_name', 'Herói')
    m_stats = battle_cache.get('monster_stats', {})
    m_name = m_stats.get('name', 'Inimigo')

    # 2. Status do Jogador (lido do cache)
    p_stats = battle_cache.get('player_stats', {})
    p_max_hp, p_atk, p_def, p_ini, p_srt = _fmt_player_stats_as_ints(p_stats)
    p_current_hp = max(0, min(_i(battle_cache.get('player_hp', p_max_hp)), p_max_hp))
    p_max_mp = _i(p_stats.get('max_mana', 10))
    p_current_mp = max(0, min(_i(battle_cache.get('player_mp', p_max_mp)), p_max_mp))
    
    # 3. Status do Monstro (lido do cache)
    m_hp = _i(m_stats.get('hp', 0))
    m_max = _i(m_stats.get('max_hp', 0))
    m_atk = _i(m_stats.get('attack', 0))
    m_def = _i(m_stats.get('defense', 0))
    m_ini = _i(m_stats.get('initiative', 0))
    m_srt = _i(m_stats.get('luck', 0))

    # 4. Blocos de Status Consolidados
    player_block = (
        f"<b>{p_name}</b>\n"
        f"❤️ 𝐇𝐏: {p_current_hp}/{p_max_hp}\n"
        f"💙 𝐌𝐏: {p_current_mp}/{p_max_mp}\n"
        f"⚔️ 𝐀𝐓𝐊: {p_atk} | 🛡 𝐃𝐄𝐅: {p_def}\n"
        f"🏃‍♂️ 𝐕𝐄𝐋: {p_ini} | 🍀 𝐒𝐑𝐓: {p_srt}"
    )

    monster_block = (
        f"<b>{m_name}</b>\n"
        f"❤️ 𝐇𝐏: {m_hp}/{m_max}\n"
        f"⚔️ 𝐀𝐓𝐊: {m_atk} | 🛡 𝐃𝐄𝐅: {m_def}\n"
        f"🏃‍♂️ 𝐕𝐄𝐋: {m_ini} | 🍀 𝐒𝐑𝐓: {m_srt}"
    )

    # 5. Montagem do Log
    log_raw = battle_cache.get('battle_log', [])
    log_lines = [_format_log_line(line) for line in log_raw[-4:]] # Pega as últimas 4 linhas
    log_block = "\n".join(log_lines)
    if not log_block:
        log_block = "Aguardando sua ação..."

    # 6. Construção da Caixa Final
    final_message = (
        f"{titulo}\n"
        f"⚔️ 𝑽𝑺 <b>{m_name}</b>\n"
        "╔════════════ ◆◈◆ ════════════╗\n"
        f"{player_block}\n"
        "══════════════════════════════\n"
        f"{monster_block}\n"
        "═════════════ 📜 ═════════════\n"
        f"<code>{log_block}</code>\n"
        "╚════════════ ◆◈◆ ════════════╝"
    )

    return final_message

