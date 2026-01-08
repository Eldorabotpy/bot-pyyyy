# modules/evolution_battle.py
# (VERSÃO BLINDADA: Usa "Deletar e Enviar" para garantir que a tela mude)

from __future__ import annotations
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes

from modules import player_manager
from modules.game_data.monsters import MONSTERS_DATA
from modules.game_data import class_evolution as evo_data
from modules import file_ids as file_id_manager
from handlers.utils import format_combat_message

logger = logging.getLogger(__name__)

async def start_evolution_presentation(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, target_class: str):
    """
    FASE 1: Tela de Apresentação (VS).
    """
    # Garante o chat_id correto
    chat_id = update.effective_chat.id if update.effective_chat else user_id
    
    pdata = await player_manager.get_player_data(user_id)
    
    # 1. Busca Evolução e Monstro
    evo_opt = evo_data.find_evolution_by_target(target_class)
    if not evo_opt: return

    monster_id = evo_opt.get('trial_monster_id')
    monster_data = None
    
    # Procura na lista especial primeiro
    if "_evolution_trials" in MONSTERS_DATA:
        for m in MONSTERS_DATA["_evolution_trials"]:
            if m["id"] == monster_id:
                monster_data = m
                break
    # Procura nas listas gerais
    if not monster_data:
        monster_data = MONSTERS_DATA.get(monster_id)

    if not monster_data:
        # Fallback de erro visual
        await context.bot.send_message(chat_id, f"⚠️ Erro: Guardião '{monster_id}' não configurado.")
        return

    # 2. Cura e Salva Estado
    await player_manager.full_restore(user_id)
    
    # Salva o "snapshot" do monstro para usar na batalha
    pdata['player_state'] = {
        'action': 'evolution_lobby', 
        'details': {
            'target_class': target_class,
            'monster_id': monster_id,
            'monster_data_snapshot': monster_data 
        }
    }
    await player_manager.save_player_data(user_id, pdata)

    # 3. Monta Texto e Botão
    monster_name = monster_data.get('name', 'Guardião')
    hp = monster_data.get('hp', 1000)
    atk = monster_data.get('attack', 100)
    
    caption = (
        f"⚡ <b>PROVAÇÃO DE {target_class.upper()}</b> ⚡\n\n"
        f"O <b>{monster_name}</b> bloqueia seu destino!\n"
        f"<i>\"Apenas os dignos herdam este poder. Prove seu valor!\"</i>\n\n"
        f"📊 <b>Atributos do Inimigo:</b>\n"
        f"❤️ HP: {hp} | ⚔️ ATK: {atk}\n\n"
        f"✨ <i>Você foi curado completamente para este duelo.</i>"
    )

    kb = [[InlineKeyboardButton("⚔️ COMEÇAR DUELO ⚔️", callback_data="start_evo_combat")]]
    reply_markup = InlineKeyboardMarkup(kb)

    # 4. Envia Mídia
    media_key = monster_data.get("media_key")
    file_info = file_id_manager.get_file_data(media_key)
    
    # Tenta apagar mensagem anterior para limpar a tela
    if update.callback_query:
        try: await update.callback_query.message.delete()
        except: pass

    # Envia nova mensagem limpa
    try:
        if file_info:
            if file_info.get("type") == "video":
                await context.bot.send_video(chat_id, video=file_info["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
            else:
                await context.bot.send_photo(chat_id, photo=file_info["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
        else:
            # Se não tiver imagem, envia texto
            await context.bot.send_message(chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Erro ao enviar VS screen: {e}")
        await context.bot.send_message(chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML")


async def start_evo_combat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    FASE 2: Início do Combate (O Botão foi clicado)
    """
    query = update.callback_query
    await query.answer("⚔️ A arena se fecha...") # Feedback imediato

    user_id = query.from_user.id
    chat_id = query.message.chat_id

    pdata = await player_manager.get_player_data(user_id)
    state = pdata.get('player_state', {})
    
    # Validação de Sessão
    if state.get('action') != 'evolution_lobby':
        await context.bot.send_message(chat_id, "⚠️ Sessão expirada. Volte ao menu.")
        return

    details = state.get('details', {})
    monster_data = details.get('monster_data_snapshot', {})
    
    # 1. Configura o Combate nos dados do Jogador
    combat_details = {
        "monster_name":       monster_data.get("name"),
        "monster_hp":         int(monster_data.get("hp")),
        "monster_max_hp":     int(monster_data.get("hp")),
        "monster_attack":     int(monster_data.get("attack")),
        "monster_defense":    int(monster_data.get("defense")),
        "monster_initiative": int(monster_data.get("initiative")),
        "monster_luck":       int(monster_data.get("luck")),
        "monster_xp_reward":  0, 
        "monster_gold_drop":  0,
        "loot_table":         [],
        "id":                 monster_data.get("id"),
        "file_id_name":       monster_data.get("media_key"),
        # Flags Críticas
        "is_evolution_trial": True, 
        "target_class_reward": details.get('target_class'),
        "battle_log": [f"⚔️ O duelo contra {monster_data.get('name')} começou!"]
    }

    pdata['player_state'] = {
        'action': 'evolution_combat', 
        'details': combat_details
    }
    await player_manager.save_player_data(user_id, pdata)

    # 2. Prepara a Interface de Combate
    caption = await format_combat_message(pdata)
    
    kb = [
        [InlineKeyboardButton("⚔️ Atacar", callback_data="combat_attack"), InlineKeyboardButton("✨ Skills", callback_data="combat_skill_menu")],
        [InlineKeyboardButton("🧪 Poções", callback_data="combat_potion_menu")] 
    ]
    reply_markup = InlineKeyboardMarkup(kb)
    
    # 3. TROCA A TELA (Deletar VS -> Enviar Combate)
    # Isso evita erros de edição se a mídia falhar
    try:
        await query.message.delete()
    except:
        pass # Mensagem já pode ter sumido

    # Pega a mídia do monstro (se existir)
    media_key = combat_details.get("file_id_name")
    file_info = file_id_manager.get_file_data(media_key)
    
    try:
        if file_info:
            if file_info.get("type") == "video":
                await context.bot.send_video(chat_id, video=file_info["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
            else:
                await context.bot.send_photo(chat_id, photo=file_info["id"], caption=caption, reply_markup=reply_markup, parse_mode="HTML")
        else:
            # Fallback seguro sem imagem
            await context.bot.send_message(chat_id, text=f"👹 <b>{combat_details['monster_name']}</b>\n\n{caption}", reply_markup=reply_markup, parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"Erro crítico ao iniciar combat UI: {e}")
        # Última tentativa em caso de erro de mídia
        await context.bot.send_message(chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML")