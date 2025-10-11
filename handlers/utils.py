# handlers/utils.py

import html
from typing import Optional
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from modules import player_manager, game_data
from telegram import Update

# =============================================================================
# MELHORIA: A função 'render_item_stats_short' foi movida para cá
# para resolver uma importação circular com 'item_factory.py'.
# =============================================================================

async def safe_edit_message(query: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup = None, parse_mode: str = 'HTML'):
    """
    Edita uma mensagem de forma segura, tentando editar a legenda primeiro
    e, se falhar, edita o texto. Evita o erro 'BadRequest: There is no caption...'.
    """
    try:
        # Tenta editar a legenda (para mensagens com foto/vídeo)
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        try:
            # Se falhar, edita o texto (para mensagens de texto simples)
            await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e:
            # Se ambos falharem, é útil registrar o erro
            print(f"Falha ao editar a mensagem: {e}")

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

def render_item_stats_short(item_instance: dict, player_class: str) -> str:
    """
    Renderiza uma string curta com os status principais de um item.
    Esta função agora vive em utils.py para evitar dependências cíclicas.
    """
    # Supondo que a lógica original desta função seja algo parecido com isto:
    # (Adapte conforme a sua implementação original em item_factory.py)
    stats = item_instance.get("stats", {})
    parts = []
    if stats.get("attack"):
        parts.append(f"⚔️{_i(stats['attack'])}")
    if stats.get("defense"):
        parts.append(f"🛡️{_i(stats['defense'])}")
    if stats.get("initiative"):
        parts.append(f"🏃‍♂️{_i(stats['initiative'])}")
    if stats.get("luck"):
        parts.append(f"🍀{_i(stats['luck'])}")
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
    """
    p_max_hp = _i(total_stats.get('max_hp', 0))
    p_atk    = _i(total_stats.get('attack', 0))
    p_def    = _i(total_stats.get('defense', 0))
    p_ini    = _i(total_stats.get('initiative', 0))
    p_srt    = _i(total_stats.get('luck', 0))
    return p_max_hp, p_atk, p_def, p_ini, p_srt

# ---------- Mensagem de combate (sempre inteiros) ----------
def format_combat_message(player_data: dict) -> str:
    """Formata a mensagem de combate com um layout de duas colunas e log separado."""
    
    state = player_data.get('player_state', {})
    details = state.get('details', {})
    log = details.get('battle_log', [])
    
    # --- Dados da Região ---
    regiao_id = player_data.get("current_location", "floresta_sombria")
    # Usa a tua função helper que já existe!
    titulo, icones = obter_titulo_e_icones_por_regiao(regiao_id) 

    # --- Dados do Jogador ---
    player_stats = player_manager.get_player_total_stats(player_data)
    p_name = player_data.get('character_name', 'Herói')
    p_hp = f"❤️ HP: {_i(player_data.get('current_hp', 0))}/{_i(player_stats.get('max_hp', 0))}"
    p_atk = f"⚔️ ATK: {_i(player_stats.get('attack', 0))}"
    p_def = f"🛡️ DEF: {_i(player_stats.get('defense', 0))}"
    p_vel = f"🏃‍♂️ VEL: {_i(player_stats.get('initiative', 0))}"
    p_srt = f"🍀 SRT: {_i(player_stats.get('luck', 0))}"

    # --- Dados do Monstro ---
    m_name = details.get('monster_name', 'Inimigo')
    m_hp = f"❤️ HP: {_i(details.get('monster_hp', 0))}/{_i(details.get('monster_max_hp', 0))}"
    m_atk = f"⚔️ ATK: {_i(details.get('monster_attack', 0))}"
    m_def = f"🛡️ DEF: {_i(details.get('monster_defense', 0))}"
    m_vel = f"🏃‍♂️ VEL: {_i(details.get('monster_initiative', 0))}"
    m_srt = f"🍀 SRT: {_i(details.get('monster_luck', 0))}"

    # --- Montagem do Layout em Colunas ---
    # Define a largura da primeira coluna para alinhamento
    largura_coluna = 15

    stats_block_lines = [
        f"{p_name.ljust(largura_coluna)} │ {m_name}",
        f"{p_hp.ljust(largura_coluna)} │ {m_hp}",
        f"{p_atk.ljust(largura_coluna)} │ {m_atk}",
        f"{p_def.ljust(largura_coluna)} │ {m_def}",
        f"{p_vel.ljust(largura_coluna)} │ {m_vel}",
        f"{p_srt.ljust(largura_coluna)} │ {m_srt}",
    ]
    stats_block = "\n".join(stats_block_lines)
    
    # --- Montagem do Log (SEM CORTES) ---
    # Apenas pega as últimas 4 linhas e escapa caracteres especiais de HTML
    log_block = "\n".join([html.escape(str(line)) for line in log[-4:]])
    if not log_block:
        log_block = "Aguardando sua ação..."

    # --- Mensagem Final ---
    final_message = (
        f"{titulo}\n\n"  # Usa o título gerado pela tua função helper
        f"╔═════════ ⚔️ VS ⚔️ ═════════╗\n"
        f"<code>{stats_block}</code>\n"
        f"╚═══════════ 📜 ═══════════╝\n\n"
        f"<b>Últimas Ações:</b>\n"
        f"<code>{log_block}</code>"
    )
    
    return final_message

# ---------- Mensagem de dungeon (sempre inteiros) ----------
def format_dungeon_combat_message(dungeon_instance: dict, all_players_data: dict) -> str:
    """
    Formata a mensagem de combate para dungeons (multi-participantes).
    Exibe SEMPRE inteiros.
    """
    cs = dungeon_instance.get('combat_state', {})

    header = ["╔════════════ ◆◈◆ ════════════╗"]

    # Heróis
    heroes_blocks = []
    for player_id, combat_data in (cs.get('participants', {}) or {}).items():
        player_full_data = all_players_data.get(player_id)
        if not player_full_data:
            continue

        total_stats = player_manager.get_player_total_stats(player_full_data)
        max_hp, atk, defense, vel, srt = _fmt_player_stats_as_ints(total_stats) # MELHORIA: Renomeado 'defe' para 'defense'
        current_hp = _i(combat_data.get('hp', 0))

        player_block = (
            f"<b>{combat_data.get('name','Herói')}</b>\n"
            f"❤️ 𝐇𝐏: {current_hp}/{max_hp}\n"
            f"⚔️ 𝐀𝐓𝐊: {atk}  🛡️ 𝐃𝐄𝐅: {defense}\n"
            f"🏃‍♂️ 𝐕𝐄𝐋: {vel}  🍀 𝐒𝐑𝐓: {srt}"
        )
        heroes_blocks.append(player_block)

    # Inimigos
    enemies_blocks = []
    for monster_key, monster_data in (cs.get('monsters', {}) or {}).items():
        if _i(monster_data.get('hp', 0)) > 0:
            m_hp   = _i(monster_data.get('hp', 0))
            m_max  = _i(monster_data.get('max_hp', 0))
            m_atk  = _i(monster_data.get('attack', 0))
            m_def  = _i(monster_data.get('defense', 0))
            m_vel  = _i(monster_data.get('initiative', 0))
            m_srt  = _i(monster_data.get('luck', 0))

            monster_block = (
                f"<b>{monster_data.get('name','Inimigo')}</b>\n"
                f"❤️ 𝐇𝐏: {m_hp}/{m_max}\n"
                f"⚔️ 𝐀𝐓𝐊: {m_atk}  🛡️ 𝐃𝐄𝐅: {m_def}\n"
                f"🏃‍♂️ 𝐕𝐄𝐋: {m_vel}  🍀 𝐒𝐑𝐓: {m_srt}"
            )
            enemies_blocks.append(monster_block)

    # Log
    log_lines = ["═════════════ ◆◈◆ ═════════════"]
    battle_log = cs.get('battle_log', []) or []
    # MELHORIA: Adicionado html.escape para consistência e segurança.
    log_lines.extend([html.escape(str(x)) for x in battle_log[-4:]])

    footer = ["╚════════════ ◆◈◆ ════════════╝"]

    heroes_section  = "\n\n".join(heroes_blocks)
    enemies_section = "═════════════════════════════\n" + "\n\n".join(enemies_blocks)

    return "\n".join(header + [heroes_section, enemies_section] + log_lines + footer)

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
    # CORREÇÃO: Chamando a função que agora está neste mesmo arquivo.
    stats = render_item_stats_short(inst, player_class)
    return f"{emoji_slot} <b>{slot.capitalize()}</b>: 『[{cur_d}/{max_d}] {name} [{rarity}]』 {stats}"

def render_inventory_row(uid: str, inst: dict, player_class: str) -> str:
    base = inst.get("base_id","")
    name = game_data.ITEM_BASES.get(base, {}).get("display_name", base)
    rarity = (inst.get("rarity","comum") or "comum").capitalize()
    cur_d, max_d = (inst.get("durability") or [0,0])
    # CORREÇÃO: Chamando a função que agora está neste mesmo arquivo.
    stats = render_item_stats_short(inst, player_class)
    return f"『[{cur_d}/{max_d}] {name} [{rarity}]』 {stats}  <code>{uid[:8]}</code>"

# ---------- PvP (inteiros) ----------
def format_pvp_result(resultado: dict, vencedor_data: Optional[dict], perdedor_data: Optional[dict]) -> tuple[str, InlineKeyboardMarkup]:
    """
    Formata o resultado de uma batalha PvP no estilo visual do bot.
    Retorna (texto, teclado inline). Exibe tudo como inteiros.
    """
    log_texto = "\n".join([str(x) for x in resultado.get('log', [])])

    nome_vencedor = vencedor_data.get('character_name', 'Aventureiro(a)') if vencedor_data else None
    nome_perdedor = perdedor_data.get('character_name', 'Oponente') if perdedor_data else None

    if resultado.get('vencedor_id'):
        vstats = player_manager.get_player_total_stats(vencedor_data or {})
        pstats = player_manager.get_player_total_stats(perdedor_data or {})

        v_max, v_atk, v_def, v_vel, v_srt = _fmt_player_stats_as_ints(vstats)
        p_max, p_atk, p_def, p_vel, p_srt = _fmt_player_stats_as_ints(pstats)

        header = "╔════════════ ◆◈◆ ════════════╗\n"
        divider = "══════════════════════════════\n"
        footer = "╚════════════ ◆◈◆ ════════════╝"

        # CORREÇÃO: Garantir que 'vencedor_data' e 'perdedor_data' não sejam None ao acessar 'current_hp'.
        v_hp = _i((vencedor_data or {}).get('current_hp', 0))
        p_hp = _i((perdedor_data or {}).get('current_hp', 0))

        mensagem_texto = (
            f"{header}"
            f"{nome_vencedor}\n"
            f"❤️ 𝐇𝐏: {v_hp}/{v_max}\n"
            f"⚔️ 𝐀𝐓𝐊: {v_atk}  🛡️ 𝐃𝐄𝐅: {v_def}\n"
            f"🏃‍♂️ 𝐕𝐄𝐋: {v_vel}  🍀 𝐒𝐑𝐓: {v_srt}\n"
            f"{divider}"
            f"{nome_perdedor}\n"
            f"❤️ 𝐇𝐏: {p_hp}/{p_max}\n"
            f"⚔️ 𝐀𝐓𝐊: {p_atk}  🛡️ 𝐃𝐄𝐅: {p_def}\n"
            f"🏃‍♂️ 𝐕𝐄𝐋: {p_vel}  🍀 𝐒𝐑𝐓: {p_srt}\n"
            f"═════════════ ◆◈◆ ═════════════\n"
            f"📜 Log da Batalha:\n"
            f"{log_texto}\n"
            f"\n🎉 <b>{nome_vencedor} 𝒗𝒆𝒏𝒄𝒆𝒖 𝒂 𝒃𝒂𝒕𝒂𝒍𝒉𝒂!</b>\n"
            f"{footer}"
        )
    else:
        mensagem_texto = (
            f"⚔️ <b>𝑨 𝑩𝑨𝑻𝑨𝑳𝑯𝑨 𝑻𝑬𝑹𝑴𝑰𝑵𝑶𝑼 𝑬𝑴 𝑬𝑷𝑨𝑻𝑬!</b> ⚔️\n\n"
            f"📜 Log da Batalha:\n"
            f"{log_texto}\n"
        )

    keyboard = [[InlineKeyboardButton("⚔️ 𝐋𝐮𝐭𝐚𝐫 𝐍𝐨𝐯𝐚𝐦𝐞𝐧𝐭𝐞 ⚔️", callback_data='arena_de_eldora')]]
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