# handlers/character_handler.py
# (VERSÃO FINAL: SISTEMA DE ID PADRONIZADO)

import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from modules import player_manager, game_data, file_id_manager
from handlers.menu.kingdom import show_kingdom_menu 
from handlers.utils import safe_update_message 
from modules.game_data import skills as skills_data
from telegram.constants import ParseMode
import html
from telegram.error import BadRequest

# --- Importação Centralizada de Auth ---
from modules.auth_utils import get_current_player_id

logger = logging.getLogger(__name__)

# =============================================================================
# FUNÇÕES DE EXIBIÇÃO
# =============================================================================
MAX_EQUIPPED_SKILLS = 8

def _format_enchantments(enchantments: dict) -> str:
    """Formata encantamentos com emojis e usa o VALUE do encanto."""
    if not enchantments:
        return ""
    emoji_map = {
        'dmg': game_data.STAT_EMOJI.get('dmg', '🗡'),
        'hp': game_data.STAT_EMOJI.get('hp', '❤️'),
        'defense': game_data.STAT_EMOJI.get('defense', '🛡️'),
        'initiative': game_data.STAT_EMOJI.get('initiative', '🏃‍♂️'),
        'luck': game_data.STAT_EMOJI.get('luck', '🍀'),
    }
    parts = []
    for stat, data in enchantments.items():
        val = int((data or {}).get('value', 0))
        if val <= 0:
            continue
        emoji = emoji_map.get(stat, '✨')
        parts.append(f"{emoji}+{val}")
    return f" [{', '.join(parts)}]" if parts else ""

def _create_progress_bar(current_val: int, max_val: int, bar_char: str = '🟧', empty_char: str = '⬜️', length: int = 10) -> tuple[str, str]:
    """Cria uma barra de progresso e a linha de texto correspondente."""
    current_val, max_val = int(current_val), int(max_val)
    if max_val <= 0:
        bar = bar_char * length
        line = f"{current_val}/— XP (nível máximo)"
    else:
        ratio = max(0.0, min(1.0, current_val / float(max_val)))
        blocks = int(round(ratio * length))
        bar = bar_char * blocks + empty_char * (length - blocks)
        line = f"{current_val}/{max_val} XP"
    return f"<code>[{bar}]</code>", line

# Função auxiliar _safe_edit_or_send
async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode=ParseMode.HTML):
    """Tenta editar caption, depois texto, depois envia nova mensagem."""
    if query: 
        try:
            await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
            return
        except BadRequest as e:
            if "message is not modified" in str(e).lower(): return 
            if "message can't be edited" in str(e).lower() or \
               "message to edit not found" in str(e).lower() or \
               "message has no caption" in str(e).lower() or \
               "there is no caption" in str(e).lower():
                pass 
            else:
                logger.warning(f"Erro ao editar caption em _safe_edit_or_send: {e}")
        except Exception as e:
             logger.warning(f"Erro inesperado ao editar caption em _safe_edit_or_send: {e}")

        try:
            await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
            return
        except BadRequest as e:
            if "message is not modified" in str(e).lower(): return 
            else:
                 logger.warning(f"Erro ao editar texto em _safe_edit_or_send: {e}")
        except Exception as e:
             logger.warning(f"Erro inesperado ao editar texto em _safe_edit_or_send: {e}")

    try:
        if query: await query.delete_message() 
    except Exception: pass
    try:
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        logger.error(f"Erro CRÍTICO ao enviar mensagem em _safe_edit_or_send para chat {chat_id}: {e}", exc_info=True)


async def show_skills_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a lista de habilidades ativas e passivas do jogador."""
    query = update.callback_query
    await query.answer()
    
    # 🔒 SEGURANÇA: ID via Auth Central
    user_id = get_current_player_id(update, context)
    chat_id = query.message.chat_id

    if not user_id:
        await _safe_edit_or_send(query, context, chat_id, "Sessão inválida. Use /start.")
        return

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await _safe_edit_or_send(query, context, chat_id, "Erro: Personagem não encontrado.")
        return

    player_skill_ids = player_data.get("skills", [])
    if not player_skill_ids:
        text = "📚 <b>Suas Habilidades</b>\n\nVocê ainda não aprendeu nenhuma habilidade."
        kb = [[InlineKeyboardButton("⬅️ Voltar ao Perfil", callback_data="char_sheet_main")]] 
        await _safe_edit_or_send(query, context, chat_id, text, InlineKeyboardMarkup(kb))
        return

    active_skills_lines = []
    passive_skills_lines = []

    for skill_id in player_skill_ids:
        skill_info = skills_data.SKILL_DATA.get(skill_id)
        if not skill_info:
            continue

        name = skill_info.get("display_name", skill_id)
        desc = skill_info.get("description", "Sem descrição.")
        mana_cost = skill_info.get("mana_cost")
        skill_type = skill_info.get("type", "unknown")

        line = f"• <b>{name}</b>"
        if mana_cost is not None:
            line += f" ({mana_cost} MP)"
        line += f": <i>{html.escape(desc)}</i>"

        if skill_type == "active" or skill_type.startswith("support"):
            active_skills_lines.append(line)
        elif skill_type == "passive":
            passive_skills_lines.append(line)

    text_parts = ["📚 <b>Suas Habilidades</b>\n"]

    if active_skills_lines:
        text_parts.append("✨ <b><u>Habilidades Ativas</u></b> ✨")
        text_parts.extend(active_skills_lines)
        text_parts.append(f"(Você pode equipar até {MAX_EQUIPPED_SKILLS} skills ativas para usar em combate)")
        text_parts.append("")

    if passive_skills_lines:
        text_parts.append("🛡️ <b><u>Habilidades Passivas</u></b> 🛡️")
        text_parts.extend(passive_skills_lines)
        text_parts.append("")

    kb = [[InlineKeyboardButton("⬅️ Voltar ao Perfil", callback_data="char_sheet_main")]] 

    if active_skills_lines:
        kb.insert(0, [InlineKeyboardButton("⚙️ Equipar Skills Ativas", callback_data="skills_equip_menu")])

    final_text = "\n".join(text_parts)
    reply_markup = InlineKeyboardMarkup(kb)

    await _safe_edit_or_send(query, context, chat_id, final_text, reply_markup)


async def show_equip_skills_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o menu para equipar/desequipar skills ativas."""
    query = update.callback_query
    await query.answer()
    
    # 🔒 SEGURANÇA: ID via Auth Central
    user_id = get_current_player_id(update, context)
    chat_id = query.message.chat_id

    if not user_id:
        return

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await _safe_edit_or_send(query, context, chat_id, "Erro: Personagem não encontrado.")
        return

    all_skill_ids = player_data.get("skills", [])
    equipped_ids = player_data.setdefault("equipped_skills", []) 
    if not isinstance(equipped_ids, list): 
        equipped_ids = []
        player_data["equipped_skills"] = equipped_ids

    active_skill_ids = [
        skill_id for skill_id in all_skill_ids
        if skills_data.SKILL_DATA.get(skill_id, {}).get("type") == "active" or
           skills_data.SKILL_DATA.get(skill_id, {}).get("type", "").startswith("support")
    ]

    if not active_skill_ids:
        text = "⚙️ Equipar Skills Ativas\n\nVocê não possui nenhuma skill ativa para equipar."
        kb = [[InlineKeyboardButton("⬅️ Voltar (Habilidades)", callback_data="skills_menu_open")]]
        await _safe_edit_or_send(query, context, chat_id, text, InlineKeyboardMarkup(kb))
        return

    text_parts = [f"⚙️ <b>Equipar Skills Ativas</b> (Limite: {len(equipped_ids)}/{MAX_EQUIPPED_SKILLS})\n"]
    kb_rows = []

    text_parts.append("✅ <b><u>Equipadas Atualmente</u></b> ✅")
    if not equipped_ids:
        text_parts.append("<i>Nenhuma skill ativa equipada.</i>")
    else:
        for skill_id in equipped_ids:
            skill_info = skills_data.SKILL_DATA.get(skill_id)
            if not skill_info: continue
            name = skill_info.get("display_name", skill_id)
            mana_cost = skill_info.get("mana_cost")
            line = f"• <b>{name}</b>"
            if mana_cost is not None: line += f" ({mana_cost} MP)"
            text_parts.append(line)
            kb_rows.append([InlineKeyboardButton(f"➖ Desequipar {name}", callback_data=f"unequip_skill:{skill_id}")])

    text_parts.append("\n" + ("─" * 20) + "\n")
    text_parts.append("➕ <b><u>Disponíveis para Equipar</u></b> ➕")
    slots_free = MAX_EQUIPPED_SKILLS - len(equipped_ids)
    available_to_equip_found = False

    for skill_id in active_skill_ids:
        if skill_id not in equipped_ids:
            available_to_equip_found = True
            skill_info = skills_data.SKILL_DATA.get(skill_id)
            if not skill_info: continue
            name = skill_info.get("display_name", skill_id)
            mana_cost = skill_info.get("mana_cost")
            line = f"• <b>{name}</b>"
            if mana_cost is not None: line += f" ({mana_cost} MP)"
            text_parts.append(line)

            if slots_free > 0:
                kb_rows.append([InlineKeyboardButton(f"➕ Equipar {name}", callback_data=f"equip_skill:{skill_id}")])
            else:
                kb_rows.append([InlineKeyboardButton(f"🚫 Limite Atingido", callback_data="noop")])

    if not available_to_equip_found:
         text_parts.append("<i>Não há outras skills ativas disponíveis ou todas já estão equipadas.</i>")

    kb_rows.append([InlineKeyboardButton("⬅️ Voltar (Habilidades)", callback_data="skills_menu_open")])

    final_text = "\n".join(text_parts)
    reply_markup = InlineKeyboardMarkup(kb_rows)

    await _safe_edit_or_send(query, context, chat_id, final_text, reply_markup)


async def equip_skill_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Equipa uma skill ativa se houver espaço."""
    query = update.callback_query
    await query.answer()
    
    # 🔒 SEGURANÇA
    user_id = get_current_player_id(update, context)
    if not user_id:
        return

    try:
        skill_id = query.data.split(":", 1)[1]
    except IndexError:
        await query.answer("Erro ao processar a ação.", show_alert=True)
        return

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await query.answer("Erro: Personagem não encontrado.", show_alert=True)
        return

    equipped_skills = player_data.setdefault("equipped_skills", [])
    if not isinstance(equipped_skills, list):
        equipped_skills = []
        player_data["equipped_skills"] = equipped_skills

    if skill_id in equipped_skills:
        await query.answer("Essa skill já está equipada.", show_alert=True)
        await show_equip_skills_menu(update, context) 
        return

    if len(equipped_skills) >= MAX_EQUIPPED_SKILLS:
        await query.answer(f"Limite de {MAX_EQUIPPED_SKILLS} skills equipadas atingido!", show_alert=True)
        await show_equip_skills_menu(update, context) 
        return

    equipped_skills.append(skill_id)
    await player_manager.save_player_data(user_id, player_data)
    await show_equip_skills_menu(update, context) 


async def unequip_skill_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Desequipa uma skill ativa."""
    query = update.callback_query
    await query.answer()
    
    # 🔒 SEGURANÇA
    user_id = get_current_player_id(update, context)
    if not user_id:
        return

    try:
        skill_id = query.data.split(":", 1)[1]
    except IndexError:
        await query.answer("Erro ao processar a ação.", show_alert=True)
        return

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await query.answer("Erro: Personagem não encontrado.", show_alert=True)
        return

    equipped_skills = player_data.setdefault("equipped_skills", [])
    if not isinstance(equipped_skills, list):
        equipped_skills = []
        player_data["equipped_skills"] = equipped_skills

    if skill_id in equipped_skills:
        equipped_skills.remove(skill_id)
        await player_manager.save_player_data(user_id, player_data)
    else:
        await query.answer("Essa skill não estava equipada.", show_alert=True)

    await show_equip_skills_menu(update, context)

async def noop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback que não faz nada, usado para botões desativados."""
    query = update.callback_query
    await query.answer("Limite de skills equipadas atingido!") 

async def show_character_sheet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tela principal da Ficha de Personagem."""
    
    # 🔒 SEGURANÇA JÁ EXISTENTE (Mantida)
    user_id = get_current_player_id(update, context)
    chat_id = update.effective_chat.id

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        if getattr(update, "message", None):
            await update.message.reply_text("Crie um personagem com /start primeiro.")
        elif getattr(update, "callback_query", None):
             try:
                 await update.callback_query.answer("Crie um personagem com /start primeiro.", show_alert=True)
             except Exception:
                 await context.bot.send_message(chat_id=chat_id, text="Crie um personagem com /start primeiro.")
        return

    player_class_key = player_data.get('class')
    file_id_name = "default_character_img"
    if player_class_key:
        file_id_name = game_data.CLASSES_DATA.get(player_class_key, {}).get('file_id_name', file_id_name)

    file_data = file_id_manager.get_file_data(file_id_name)
    caption = f"Ficha de Personagem de <b>{player_data.get('character_name','Aventureiro(a)')}</b>"

    keyboard = [
        [InlineKeyboardButton("⚜️ ꧁𓊈𒆜🅲🅻🅰🅽𒆜𓊉꧂ ⚜️", callback_data="clan_menu:profile")],
        [InlineKeyboardButton("📊 𝐒𝐭𝐚𝐭𝐮𝐬 & 𝐀𝐭𝐫𝐢𝐛𝐮𝐭𝐨𝐬", callback_data='char_status')],
        [InlineKeyboardButton("🎒 𝐈𝐧𝐯𝐞𝐧𝐭𝐚́𝐫𝐢𝐨", callback_data='char_inventory')],
        [InlineKeyboardButton("⚔️ 𝐄𝐪𝐮𝐢𝐩𝐚𝐦𝐞𝐧𝐭𝐨", callback_data='char_equipment')],
        [InlineKeyboardButton("📚 𝐇𝐚𝐛𝐢𝐥𝐢𝐝𝐚𝐝𝐞𝐬", callback_data='skills_menu_open')],
    ]
    
    if int(player_data.get('level', 1)) >= 5 and (player_data.get('profession') or {}).get('type') is None:
        keyboard.append([InlineKeyboardButton("📜 𝐄𝐬𝐜𝐨𝐥𝐡𝐞𝐫 𝐏𝐫𝐨𝐟𝐢𝐬𝐬𝐚̃𝐨", callback_data='prof_show_list')])
    keyboard.append([InlineKeyboardButton("⬅️ 𝐅𝐞𝐜𝐡𝐚𝐫", callback_data='char_close')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        try:
            await update.callback_query.delete_message()
        except Exception:
            pass

    if file_data and file_data.get("id"):
        file_id, file_type = file_data["id"], file_data.get("type")
        if file_type == 'video':
            await context.bot.send_video(chat_id=chat_id, video=file_id, caption=caption,
                                         reply_markup=reply_markup, parse_mode='HTML')
        else:
            await context.bot.send_photo(chat_id=chat_id, photo=file_id, caption=caption,
                                         reply_markup=reply_markup, parse_mode='HTML')
    else:
        await context.bot.send_message(chat_id=chat_id, text=caption,
                                       reply_markup=reply_markup, parse_mode='HTML')
                
async def show_status_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra status, progressões e upgrade de atributos com barras robustas."""
    query = update.callback_query
    await query.answer()
    
    # 🔒 SEGURANÇA
    user_id = get_current_player_id(update, context)
    if not user_id:
        return

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await safe_update_message(update, context, "Crie um personagem com /start primeiro.", None)
        return

    total_stats = player_manager.get_player_total_stats(player_data)
    caption = f"👤 <b>Status de {player_data.get('character_name','Aventureiro(a)')}</b>\n\n"

    stats_to_show = ['max_hp', 'attack', 'defense', 'initiative', 'luck']
    emoji_map = {'max_hp': '❤️', 'attack': '⚔️', 'defense': '🛡️', 'initiative': '🏃', 'luck': '🍀'}
    stat_name_map = {'max_hp': 'HP Máximo', 'attack': 'Ataque', 'defense': 'Defesa', 'initiative': 'Iniciativa', 'luck': 'Sorte'}

    for stat in stats_to_show:
        base_value = int(player_data.get(stat, 0))
        total_value = int(total_stats.get(stat, 0))
        bonus = total_value - base_value
        line = f"{emoji_map[stat]} <b>{stat_name_map[stat]}:</b> {total_value}"
        if bonus > 0:
            line += f" ({base_value} + {bonus})"
        caption += line + "\n"

    combat_level = int(player_data.get('level', 1))
    combat_xp = int(player_data.get('xp', 0))
    xp_to_next = game_data.get_xp_for_next_combat_level(combat_level) or 0
    combat_bar, combat_line = _create_progress_bar(combat_xp, xp_to_next, '🟧')
    caption += f"\n🎖️ <b>Nível de Combate: {combat_level}</b>\n{combat_bar} {combat_line}\n"

    profession_data = player_data.get('profession', {}) or {}
    prof_type = profession_data.get('type')
    if prof_type:
        prof_level = int(profession_data.get('level', 1))
        prof_xp = int(profession_data.get('xp', 0))
        xp_to_next_prof = game_data.get_xp_for_next_collection_level(prof_level) or 0
        prof_bar, prof_line = _create_progress_bar(prof_xp, xp_to_next_prof, '🟨')
        prof_name = game_data.PROFESSIONS_DATA.get(prof_type, {}).get('display_name', prof_type)
        caption += (f"\n💼 <b>Profissão: {prof_name} (Nvl. {prof_level})</b>\n"
                    f"{prof_bar} {prof_line}\n")

    available_points = int(player_data.get('stat_points', 0))
    caption += f"\n✨ <b>Pontos Disponíveis: {available_points}</b>"

    player_class_key = player_data.get('class')
    class_modifiers = game_data.CLASSES_DATA.get(player_class_key, {}).get(
        'stat_modifiers', {'attack': 1, 'defense': 1, 'initiative': 1, 'luck': 0.5}
    )

    keyboard = []
    if available_points > 0:
        keyboard.extend([
            [InlineKeyboardButton(f"➕ HP (+3)", callback_data='upgrade_hp'),
             InlineKeyboardButton(f"➕ ATK (+{class_modifiers.get('attack', 1):g})", callback_data='upgrade_attack')],
            [InlineKeyboardButton(f"➕ DEF (+{class_modifiers.get('defense', 1):g})", callback_data='upgrade_defense'),
             InlineKeyboardButton(f"➕ INI (+{class_modifiers.get('initiative', 1):g})", callback_data='upgrade_initiative')],
            [InlineKeyboardButton(f"➕ SRT (+{0.5 * class_modifiers.get('luck', 0.5):.2f})", callback_data='upgrade_luck')],
        ])

    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data='char_sheet_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    file_id_name = game_data.CLASSES_DATA.get(player_class_key, {}).get('file_id_name', "default_character_img")
    file_data = file_id_manager.get_file_data(file_id_name)

    await safe_update_message(
        update,
        context,
        new_text=caption,
        new_reply_markup=reply_markup,
        new_media_file_id=file_data.get("id"),
        new_media_type=file_data.get("type", "photo")
    )

async def show_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o inventário separando itens equipáveis e materiais."""
    query = update.callback_query
    await query.answer()
    
    # 🔒 SEGURANÇA
    user_id = get_current_player_id(update, context)
    if not user_id:
        return

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await safe_update_message(update, context, "Crie um personagem com /start primeiro.", None)
        return

    inventory = player_data.get('inventory', {}) or {}
    equipment = player_data.get('equipment', {}) or {}
    equipped_item_uuids = set(v for v in equipment.values() if v)

    caption = "🎒 <b>Inventário</b>\n\n"
    keyboard = []

    equipable_items_text = ""
    materials_text = "\n<b>Materiais e Itens:</b>\n"
    has_equipables = False
    has_materials = False

    for key, value in inventory.items():
        if isinstance(value, dict):
            has_equipables = True
            base_id = value.get('base_id')
            base_meta = game_data.ITEM_BASES.get(base_id, {})
            if not base_meta: continue

            rarity = (value.get('rarity') or 'comum').lower()
            rarity_info = game_data.RARITY_DATA.get(rarity, {'emoji': '•', 'name': rarity})
            durability = value.get('durability', [0, 0])
            enchants_str = _format_enchantments(value.get('enchantments', {}))
            tier = int(value.get('tier', 1))
            display_name = base_meta.get('display_name', base_id)

            item_line = (f"<code>[{int(durability[0])}/{int(durability[1])}]</code> "
                         f"{rarity_info.get('emoji','•')} {display_name} [ T{tier} ]{enchants_str}\n")
            equipable_items_text += item_line

            if key not in equipped_item_uuids:
                keyboard.append([InlineKeyboardButton(f"Equipar {display_name}", callback_data=f"equip_{key}")])

        elif isinstance(value, int) and value > 0:
            has_materials = True
            item_name = game_data.ITEMS_DATA.get(key, {}).get('display_name', key)
            materials_text += f"• {item_name}: {value}\n"

    if not has_equipables:
        equipable_items_text = "Você não possui itens equipáveis.\n"
    if not has_materials:
        materials_text = ""

    final_caption = caption + equipable_items_text + materials_text
    if not inventory:
        final_caption = "🎒 <b>Inventário</b>\n\nSua mochila está vazia."

    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data='char_sheet_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await safe_update_message(
        update,
        context,
        new_text=final_caption,
        new_reply_markup=reply_markup
    )

async def show_profession_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista de profissões para escolha."""
    query = update.callback_query
    await query.answer()
    text = ("Sua jornada te trouxe conhecimento. É hora de escolher uma profissão. "
            "Esta escolha é permanente e definirá seu papel no mundo de Eldora.")
    keyboard = []
    keyboard.append([InlineKeyboardButton("--- Profissões de Coleta ---", callback_data='prof_no_action')])
    for prof_key, prof_info in game_data.PROFESSIONS_DATA.items():
        if prof_info.get('category') == 'gathering':
            keyboard.append([InlineKeyboardButton(prof_info.get('display_name', prof_key), callback_data=f"prof_confirm_{prof_key}")])
    keyboard.append([InlineKeyboardButton("--- Profissões de Criação ---", callback_data='prof_no_action')])
    for prof_key, prof_info in game_data.PROFESSIONS_DATA.items():
        if prof_info.get('category') == 'crafting':
            keyboard.append([InlineKeyboardButton(prof_info.get('display_name', prof_key), callback_data=f"prof_confirm_{prof_key}")])
    keyboard.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data='char_sheet_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.delete_message()
    except Exception:
        pass
    await context.bot.send_message(chat_id=query.message.chat_id, text=text, reply_markup=reply_markup)

async def confirm_profession_choice(update: Update, context: ContextTypes.DEFAULT_TYPE, prof_key: str):
    """Atribui a profissão ao jogador (apenas se válida e ainda não tiver)."""
    query = update.callback_query
    await query.answer()
    
    # 🔒 SEGURANÇA
    user_id = get_current_player_id(update, context)
    if not user_id:
        return

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await query.edit_message_text("Crie um personagem com /start primeiro.")
        return

    if (player_data.get('profession') or {}).get('type'):
        await query.answer("Você já possui uma profissão.", show_alert=True)
        await show_character_sheet(update, context) 
        return

    prof_info = game_data.PROFESSIONS_DATA.get(prof_key)
    if not prof_info:
        await query.answer("Profissão inválida.", show_alert=True)
        return

    player_data['profession'] = {"type": prof_key, "level": 1, "xp": 0} 

    await player_manager.save_player_data(user_id, player_data)
    await query.answer(f"Você agora é um {prof_info.get('display_name', prof_key)}!", show_alert=True)
    await show_character_sheet(update, context)

async def show_equipment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra slots de equipamento (lendo UUIDs nos slots)."""
    query = update.callback_query
    await query.answer()
    
    # 🔒 SEGURANÇA
    user_id = get_current_player_id(update, context)
    if not user_id:
        return

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await query.edit_message_text("Crie um personagem com /start primeiro.")
        return

    equipment = player_data.get('equipment', {}) or {}
    inventory = player_data.get('inventory', {}) or {}

    slot_names = {
        "arma": "⚔️ Arma", "elmo": "🪖 Elmo", "armadura": "👕 Armadura", "calca": "👖 Calça",
        "luvas": "🧤 Luvas", "botas": "🥾 Botas", "anel": "💍 Anel", "colar": "📿 Colar", "brinco": "🧿 Brinco"
    }
    caption = "⚔️ 𝐄𝐪𝐮𝐢𝐩𝐚𝐦𝐞𝐧𝐭𝐨 𝐀𝐭𝐢𝐯𝐨:\n\n"
    keyboard = []

    for slot, display_name in slot_names.items():
        item_uuid = equipment.get(slot)
        item_name = "[Vazio]"
        if item_uuid:
            item_instance = inventory.get(item_uuid, {})
            base_id = item_instance.get('base_id')
            if base_id:
                base_meta = game_data.ITEM_BASES.get(base_id, {})
                item_name = base_meta.get('display_name', base_id)
                keyboard.append([InlineKeyboardButton(f"Desequipar {item_name}", callback_data=f"unequip_{slot}")])
        caption += f"<b>{display_name}:</b> {item_name}\n"

    keyboard.append([InlineKeyboardButton("🎒 𝐀𝐛𝐫𝐢𝐫 𝐈𝐧𝐯𝐞𝐧𝐭𝐚́𝐫𝐢𝐨 𝐩𝐚𝐫𝐚 𝐄𝐪𝐮𝐢𝐩𝐚𝐫", callback_data='char_inventory')])
    keyboard.append([InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data='char_sheet_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    file_data = file_id_manager.get_file_data('img_inventario')
    try:
        await query.delete_message()
    except Exception:
        pass
    chat_id = query.message.chat_id
    if file_data and file_data.get("id"):
        file_id, file_type = file_data["id"], file_data.get("type")
        if file_type == 'video':
            await context.bot.send_video(chat_id=chat_id, video=file_id, caption=caption,
                                         reply_markup=reply_markup, parse_mode='HTML')
        else:
            await context.bot.send_photo(chat_id=chat_id, photo=file_id, caption=caption,
                                         reply_markup=reply_markup, parse_mode='HTML')
    else:
        await context.bot.send_message(chat_id=chat_id, text=caption,
                                       reply_markup=reply_markup, parse_mode='HTML')

# =============================================================================
# FUNÇÕES DE CALLBACK
# =============================================================================
async def upgrade_stat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gasta 1 ponto e aumenta um atributo."""
    query = update.callback_query
    await query.answer()
    
    # 🔒 SEGURANÇA
    user_id = get_current_player_id(update, context)
    if not user_id:
        return

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await query.edit_message_text("Crie um personagem com /start primeiro.") 
        return

    stat_to_upgrade = query.data.replace('upgrade_', '')
    if int(player_data.get('stat_points', 0)) <= 0:
        await context.bot.answer_callback_query(query.id, "𝑽𝒐𝒄𝒆̂ 𝒏𝒂̃𝒐 𝒕𝒆𝒎 𝒑𝒐𝒏𝒕𝒐𝒔 𝒑𝒂𝒓𝒂 𝒈𝒂𝒔𝒕𝒂𝒓!", show_alert=True)
        return

    player_data['stat_points'] = int(player_data.get('stat_points', 0)) - 1
    player_class = player_data.get('class')
    modifiers = game_data.CLASSES_DATA.get(player_class, {}).get(
        'stat_modifiers', {'attack': 1, 'defense': 1, 'initiative': 1, 'luck': 0.5}
    )

    if stat_to_upgrade == 'hp':
        player_data['max_hp'] = int(player_data.get('max_hp', 0)) + 3
        player_data['current_hp'] = int(player_data.get('current_hp', 0)) + 3
    elif stat_to_upgrade == 'attack':
        player_data['attack'] = int(player_data.get('attack', 0) + (1 * modifiers.get('attack', 1)))
    elif stat_to_upgrade == 'defense':
        player_data['defense'] = int(player_data.get('defense', 0) + (1 * modifiers.get('defense', 1)))
    elif stat_to_upgrade == 'initiative':
        player_data['initiative'] = int(player_data.get('initiative', 0) + (1 * modifiers.get('initiative', 1)))
    elif stat_to_upgrade == 'luck':
        player_data['luck'] = int(player_data.get('luck', 0) + (0.5 * modifiers.get('luck', 0.5)))

    await player_manager.save_player_data(user_id, player_data)
    await show_status_menu(update, context)

async def equip_item_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Equipa um item único do inventário (guarda UUID no slot)."""
    query = update.callback_query
    await query.answer()
    
    # 🔒 SEGURANÇA
    user_id = get_current_player_id(update, context)
    if not user_id:
        return

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await query.edit_message_text("Crie um personagem com /start primeiro.")
        return

    item_uuid = query.data.replace('equip_', '')
    inventory = player_data.get('inventory', {}) or {}
    item_instance = inventory.get(item_uuid)
    if not isinstance(item_instance, dict):
        await query.answer("Erro: Item não encontrado ou não é equipamento.", show_alert=True)
        return

    base_id = item_instance.get('base_id')
    base_meta = game_data.ITEM_BASES.get(base_id)
    if not base_meta:
        await query.answer("Erro: Base do item inválida.", show_alert=True)
        return

    slot_to_equip = base_meta.get('slot')
    if not slot_to_equip:
        await query.answer("Este item não pode ser equipado.", show_alert=True)
        return

    player_data.setdefault('equipment', {})[slot_to_equip] = item_uuid

    await player_manager.save_player_data(user_id, player_data)

    await query.answer(f"{base_meta.get('display_name', 'Item')} equipado!", show_alert=False)
    await show_equipment(update, context)

async def unequip_item_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Desequipa um item, limpando o slot."""
    query = update.callback_query
    await query.answer()
    
    # 🔒 SEGURANÇA
    user_id = get_current_player_id(update, context)
    if not user_id:
        return

    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await query.edit_message_text("Crie um personagem com /start primeiro.") 
        return

    slot_to_unequip = query.data.replace('unequip_', '')
    equipped_uuid = (player_data.get('equipment', {}) or {}).get(slot_to_unequip)
    if not equipped_uuid:
        await query.answer("Não há nada equipado neste slot.", show_alert=True)
        return

    item_instance = (player_data.get('inventory', {}) or {}).get(equipped_uuid, {})
    base_id = item_instance.get('base_id')
    base_meta = game_data.ITEM_BASES.get(base_id, {})
    item_name = base_meta.get('display_name', 'Item')

    player_data['equipment'][slot_to_unequip] = None

    await player_manager.save_player_data(user_id, player_data)

    await query.answer(f"{item_name} desequipado.", show_alert=True) 
    await show_equipment(update, context)

async def character_sheet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Router da Ficha de Personagem e Profissões."""
    query = update.callback_query
    
    action = query.data
    if action == 'char_sheet_main':
        await show_character_sheet(update, context)
    elif action == 'char_status':
        await show_status_menu(update, context)
    elif action == 'char_inventory':
        await show_inventory(update, context)
    elif action == 'char_equipment':
        await show_equipment(update, context)
    elif action == 'char_close':
        await show_kingdom_menu(update, context) 
    elif action == 'prof_show_list':
        await show_profession_list(update, context)
    elif action.startswith('prof_confirm_'):
        prof_key = action.replace('prof_confirm_', '')
        await confirm_profession_choice(update, context, prof_key)
    elif action == 'prof_no_action':
        await query.answer()
        return
    
# =============================================================================
# HANDLERS
# =============================================================================
character_command_handler = CommandHandler("personagem", show_character_sheet)
character_callback_handler = CallbackQueryHandler(character_sheet_callback, pattern=r'^(char_|prof_)')
status_upgrade_handler = CallbackQueryHandler(upgrade_stat_callback, pattern=r'^upgrade_')
equip_item_handler = CallbackQueryHandler(equip_item_callback, pattern=r'^equip_')
unequip_item_handler = CallbackQueryHandler(unequip_item_callback, pattern=r'^unequip_')