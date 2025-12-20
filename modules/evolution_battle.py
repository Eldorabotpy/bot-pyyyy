# modules/evolution_battle.py
from __future__ import annotations
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes

from modules import player_manager, game_data
from modules.game_data.monsters import MONSTERS_DATA
from modules.game_data import class_evolution as evo_data
from modules import file_ids as file_id_manager
from handlers.utils import format_combat_message
from modules.dungeons.runtime import _send_battle_media # Reaproveita função visual

logger = logging.getLogger(__name__)

async def start_evolution_presentation(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, target_class: str):
    """
    FASE 1: A Apresentação Visual do Boss.
    Prepara o terreno, cura o jogador e mostra o inimigo.
    """
    # Tenta pegar chat_id de várias fontes
    chat_id = update.effective_chat.id if update.effective_chat else user_id
    
    pdata = await player_manager.get_player_data(user_id)
    
    # 1. Busca dados da Evolução
    evo_opt = evo_data.find_evolution_by_target(target_class)
    if not evo_opt:
        await context.bot.send_message(chat_id, "⚠️ Erro: Evolução não encontrada.")
        return

    monster_id = evo_opt.get('trial_monster_id')
    
    # 2. Busca o Monstro (na lista especial ou geral)
    monster_data = None
    if "_evolution_trials" in MONSTERS_DATA:
        for m in MONSTERS_DATA["_evolution_trials"]:
            if m["id"] == monster_id:
                monster_data = m
                break
    
    if not monster_data:
        monster_data = MONSTERS_DATA.get(monster_id)

    if not monster_data:
        await context.bot.send_message(chat_id, f"⚠️ Erro: Guardião '{monster_id}' não encontrado.")
        return

    # 3. Prepara o Jogador (Cura Total)
    await player_manager.full_restore(user_id)

    # 4. Define o Estado PRELIMINAR (Lobby)
    # Guardamos os dados do monstro aqui para não precisar buscar de novo no clique
    pdata['player_state'] = {
        'action': 'evolution_lobby', 
        'details': {
            'target_class': target_class,
            'monster_id': monster_id,
            'monster_data_snapshot': monster_data 
        }
    }
    await player_manager.save_player_data(user_id, pdata)

    # 5. Monta a Mensagem Visual
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

    # O Botão Mágico
    kb = [[InlineKeyboardButton("⚔️ COMEÇAR DUELO ⚔️", callback_data="start_evo_combat")]]
    reply_markup = InlineKeyboardMarkup(kb)

    # 6. Envio da Mídia
    media_key = monster_data.get("media_key")
    file_info = file_id_manager.get_file_data(media_key)
    
    sent = False
    if file_info:
        fid = file_info.get("id")
        ftype = file_info.get("type", "photo")
        try:
            if ftype == "video":
                await context.bot.send_video(chat_id, video=fid, caption=caption, reply_markup=reply_markup, parse_mode="HTML")
            else:
                await context.bot.send_photo(chat_id, photo=fid, caption=caption, reply_markup=reply_markup, parse_mode="HTML")
            sent = True
        except Exception as e:
            logger.error(f"Erro ao enviar mídia de trial: {e}")

    # Fallback se não tiver imagem ou der erro
    if not sent:
        # Se for callback, tenta editar, senão envia nova
        if update.callback_query:
            try: 
                await update.callback_query.edit_message_text(caption, reply_markup=reply_markup, parse_mode="HTML")
                sent = True
            except: pass
        
        if not sent:
            await context.bot.send_message(chat_id, text=caption, reply_markup=reply_markup, parse_mode="HTML")


async def start_evo_combat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    FASE 2: O Início do Combate.
    Chamado quando o jogador clica no botão. Transfere para o sistema de batalha principal.
    """
    query = update.callback_query
    await query.answer("A batalha começou!")
    user_id = query.from_user.id
    
    pdata = await player_manager.get_player_data(user_id)
    state = pdata.get('player_state', {})
    
    # Validação de segurança
    if state.get('action') != 'evolution_lobby':
        await query.edit_message_caption("⚠️ Sessão expirada. Abra o menu de ascensão novamente.")
        return

    details = state.get('details', {})
    monster_data = details.get('monster_data_snapshot', {})
    target_class = details.get('target_class')
    
    # Constrói o dicionário que o main_handler.py vai ler
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
        # FLAGS IMPORTANTES PARA O MAIN HANDLER:
        "is_evolution_trial": True, 
        "target_class_reward": target_class,
        "battle_log": [f"⚔️ O duelo contra {monster_data.get('name')} começou!"]
    }

    # Atualiza estado para 'evolution_combat' (o main_handler verifica isso na vitória)
    pdata['player_state'] = {
        'action': 'evolution_combat', 
        'details': combat_details
    }
    await player_manager.save_player_data(user_id, pdata)

    # Inicia visualmente
    caption = await format_combat_message(pdata)
    
    kb = [
        [InlineKeyboardButton("⚔️ Atacar", callback_data="combat_attack"), InlineKeyboardButton("✨ Skills", callback_data="combat_skill_menu")],
        [InlineKeyboardButton("🧪 Poções", callback_data="combat_potion_menu")] 
    ]
    
    # Envia a interface de combate
    await _send_battle_media(context, query.message.chat_id, caption, combat_details["file_id_name"], InlineKeyboardMarkup(kb))
    
    # Limpa a mensagem anterior do lobby
    try: await query.message.delete()
    except: pass