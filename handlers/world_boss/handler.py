# handlers/world_boss/handler.py
# (VERSÃO CORRIGIDA: IDs String OBRIGATÓRIOS + Layout Preservado)

import logging
import html
import time
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler
from telegram.error import BadRequest

from modules.world_boss.engine import (
    world_boss_manager, 
    broadcast_boss_announcement, 
    distribute_loot_and_announce
)
from handlers.menu.region import send_region_menu
from modules import player_manager, game_data, file_ids
from modules.player import actions as player_actions

# ✅ IMPORTAÇÃO CENTRALIZADA
from modules.game_data.skills import get_skill_data_with_rarity
from modules.cooldowns import verificar_cooldown
from modules.auth_utils import get_current_player_id
logger = logging.getLogger(__name__)

BOSS_MEDIA = "boss_raid" 
ADMIN_ID = 7262799478

# ============================================================================
# 🛠️ HELPER: EDIÇÃO INTELIGENTE
# ============================================================================
async def _smart_edit_message(query, text, reply_markup):
    """
    Tenta editar a mensagem atual. Se falhar (ex: era vídeo e virou texto),
    apaga e manda uma nova para destravar o usuário.
    """
    try:
        if query.message.caption is not None:
            await query.edit_message_caption(
                caption=text, 
                reply_markup=reply_markup, 
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text(
                text=text, 
                reply_markup=reply_markup, 
                parse_mode="HTML"
            )
    except BadRequest:
        try:
            await query.delete_message()
        except: pass
        
        await query.message.reply_text(
            text=text, 
            reply_markup=reply_markup, 
            parse_mode="HTML"
        )

# ============================================================================
# FORMATADORES E HELPERS DE ID
# ============================================================================

def _get_boss_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Retorna o ID correto do jogador como STRING.
    Essencial para o sistema de ObjectId.
    """
    if context.user_data and "logged_player_id" in context.user_data:
        return str(context.user_data["logged_player_id"])
    return str(update.effective_user.id)

def _format_log_line(text):
    return f"• {text}"

def _format_battle_screen(user_id, player_data, total_stats):
    # --- MANTIDO EXATAMENTE COMO SOLICITADO ---
    state = world_boss_manager.get_battle_view(user_id)
    if not state: return "Erro de estado."
    
    is_dead = False
    wait_txt = ""
    respawn_until = state.get('respawn_until', 0)
    now = time.time()
    
    if respawn_until > now:
        is_dead = True
        remaining = int(respawn_until - now)
        wait_txt = f"👻 𝐑𝐄𝐒𝐒𝐔𝐒𝐂𝐈𝐓𝐀𝐍𝐃𝐎: {remaining}𝐬"

    p_name = player_data.get('character_name', 'Herói')
    
    p_current_hp = max(0, state['hp']) 
    p_max_hp = state['max_hp']
    
    p_current_mp, p_max_mp = state['mp'], state['max_mp']
    p_atk = int(total_stats.get('attack', 0))
    p_def = int(total_stats.get('defense', 0))
    p_ini = int(total_stats.get('initiative', 0))
    p_srt = int(total_stats.get('luck', 0))

    t_key = state['current_target']
    target = world_boss_manager.entities.get(t_key)
    
    if not target or not target['alive']:
        return "⚠️ 𝐎 𝐚𝐥𝐯𝐨 𝐜𝐚𝐢𝐮! 𝐕𝐨𝐥𝐭𝐞 𝐞 𝐬𝐞𝐥𝐞𝐜𝐢𝐨𝐧𝐞 𝐨𝐮𝐭𝐫𝐨."

    m_name = target['name']
    m_hp, m_max = target['hp'], target['max_hp']
    m_stats = target['stats']
    m_atk, m_def = m_stats['attack'], m_stats['defense']
    m_ini, m_srt = m_stats['initiative'], m_stats['luck']

    player_block = (
        f"<b>ㅤㅤㅤㅤㅤㅤ👤 {p_name}</b>\n"
        f"❤️ 𝐇𝐏: {p_current_hp}/{p_max_hp}\n"
        f"💙 𝐌𝐏: {p_current_mp}/{p_max_mp}\n"
        f"⚔️ 𝐀𝐓𝐊: {p_atk} ­ㅤ­ㅤ ­ㅤ­ㅤ­ㅤ­ㅤ 🛡 𝐃𝐄𝐅: {p_def}\n"
        f"🏃‍♂️ 𝐕𝐄𝐋: {p_ini}   ­ㅤ­ㅤ­ㅤ­ㅤ ­ㅤ­ㅤ🍀 𝐒𝐑𝐓: {p_srt}\n"
    )

    monster_block = (
        f"<b>­ㅤ­ㅤ­ㅤ­­ㅤ­­ㅤ­­👹 {m_name}</b>\n"
        f"❤️ 𝐇𝐏: {m_hp}/{m_max}\n"
        f"⚔️ 𝐀𝐓𝐊: {m_atk} ­ㅤ­ㅤ ­ㅤ­ㅤ ­ㅤ­ㅤ🛡 𝐃𝐄𝐅: {m_def}\n"
        f"🏃‍♂️ 𝐕𝐄𝐋: {m_ini}  ­ㅤ­ㅤ ­ㅤ­ㅤ ­ㅤ­ㅤ🍀 𝐒𝐑𝐓: {m_srt}\n"
    )

    log_raw = state.get('log', '').split('\n')
    log_lines = [_format_log_line(line) for line in log_raw[-5:]]
    log_block = "\n".join(log_lines)
    if not log_block: log_block = "Aguardando sua ação..."
    
    titulo = "🌋 𝐑𝐀𝐈𝐃 𝐁𝐎𝐒𝐒"
    
    if is_dead:
        titulo += f" | {wait_txt}"
    elif world_boss_manager.environment_hazard:
        titulo += " | 🔥 𝗖𝗔𝗠𝗣𝗢 𝗘𝗠 𝗖𝗛𝗔𝗠𝗔𝗦"
    
    witches_alive = world_boss_manager.entities["witch_heal"]["alive"] or world_boss_manager.entities["witch_debuff"]["alive"]
    if t_key == "boss" and witches_alive:
        m_name += " (🛡️ IMUNE)"

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

# ============================================================================
# HANDLERS DE COMANDO
# ============================================================================

async def iniciar_worldboss_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ✅ CORREÇÃO: Use update.effective_user.id para comparar com ADMIN_ID (que é numérico)
    if update.effective_user.id != ADMIN_ID: 
        return 
    
    result = world_boss_manager.start_event()
    if result.get("success"):
        # O broadcast agora vai funcionar porque corrigimos o loop acima
        await broadcast_boss_announcement(context.application, result["location"])
        await update.message.reply_text("✅ 𝑬𝒗𝒆𝒏𝒕𝒐 𝒊𝒏𝒊𝒄𝒊𝒂𝒅𝒐!")
    else:
        await update.message.reply_text(f"⚠️ Erro: {result.get('error')}")
        
async def encerrar_worldboss_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ATENÇÃO: Verificação de Admin usa o ID do TELEGRAM (Inteiro).
    if update.effective_user.id != ADMIN_ID: return
    
    if not world_boss_manager.is_active:
        await update.message.reply_text("⚠️ 𝗡𝗮̃𝗼 𝗵𝗮́ 𝗲𝘃𝗲𝗻𝘁𝗼 𝗮𝘁𝗶𝘃𝗼.")
        return
    battle_results = world_boss_manager.end_event(reason="Boss derrotado") 
    await distribute_loot_and_announce(context, battle_results)
    await update.message.reply_text("🛑 𝗘𝗻𝗰𝗲𝗿𝗿𝗮𝗱𝗼 (Simulando Vitória).")

async def wb_return_to_map(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    # CORREÇÃO CRÍTICA: Pegar o ID do Personagem (String) e não do Telegram
    user_id = _get_boss_user_id(update, context)
    chat_id = query.message.chat_id if query else update.effective_chat.id
    
    # Remove da lista do Boss
    world_boss_manager.active_fighters.discard(user_id)
    if user_id in world_boss_manager.waiting_queue:
        world_boss_manager.waiting_queue.remove(user_id)
        
    # Chama o menu de região (agora compatível com ID String)
    await send_region_menu(context, user_id, chat_id)
    
    if query:
        try: await query.delete_message()
        except: pass

async def wb_start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: 
        try: await query.answer()
        except: pass
    
    kb_inactive = [[InlineKeyboardButton("🌍 𝐕𝐨𝐥𝐭𝐚𝐫 𝐚𝐨 𝐌𝐚𝐩𝐚", callback_data='wb_return_map')]]

    if not world_boss_manager.is_active:
        msg = "😴 𝐎 𝐁𝐨𝐬𝐬 𝐧𝐚̃𝐨 𝐞𝐬𝐭𝐚́ 𝐚𝐭𝐢𝐯𝐨 𝐧𝐨 𝐦𝐨𝐦𝐞𝐧𝐭𝐨."
        if query:
            await _smart_edit_message(query, msg, InlineKeyboardMarkup(kb_inactive))
        else:
            await context.bot.send_message(update.effective_chat.id, msg, reply_markup=InlineKeyboardMarkup(kb_inactive), parse_mode="HTML")
        return

    ents = world_boss_manager.entities
    txt = "🌋 𝐑𝐀𝐈𝐃: 𝐎 𝐋𝐎𝐑𝐃𝐄 𝐃𝐀𝐒 𝐒𝐎𝐌𝐁𝐑𝐀𝐒\n\n"
    
    for key, ent in ents.items():
        status = f"{ent['hp']:,}/{ent['max_hp']:,}" if ent['alive'] else "💀 🄼🄾🅁🅃🄰"
        icon = "👹" if key == "boss" else "🧙‍♀️"
        txt += f"{icon} <b>{ent['name']}:</b> {status}\n"
    
    witches_up = ents["witch_heal"]["alive"] or ents["witch_debuff"]["alive"]
    if witches_up:
        txt += "\n🛡️ 𝐁𝐎𝐒𝐒 𝐈𝐌𝐔𝐍𝐄! Dᴇʀʀᴏᴛᴇ ᴀs ʙʀᴜxᴀs ᴘᴀʀᴀ ǫᴜᴇʙʀᴀʀ ᴏ ᴇsᴄᴜᴅᴏ!"

    txt += f"\n👥 𝐋𝐮𝐭𝐚𝐝𝐨𝐫𝐞𝐬: {len(world_boss_manager.active_fighters)}/{world_boss_manager.max_concurrent_fighters}"
    
    kb = [
        [InlineKeyboardButton("⚔️ 𝐄𝐍𝐓𝐑𝐀𝐑 𝐍𝐀 𝐁𝐀𝐓𝐀𝐋𝐇𝐀 ⚔️", callback_data='wb_join')],
        [InlineKeyboardButton("🔄 𝐀𝐭𝐮𝐚𝐥𝐢𝐳𝐚𝐫 🔄", callback_data='wb_menu')],
        [InlineKeyboardButton("🌍 𝐕𝐨𝐥𝐭𝐚𝐫 𝐚𝐨 𝐌𝐚𝐩𝐚 🌍", callback_data='wb_return_map')]
    ]
    
    markup = InlineKeyboardMarkup(kb)
    mid = file_ids.get_file_id(BOSS_MEDIA)
    
    if query:
        try:
            if query.message.caption is not None:
                await query.edit_message_caption(caption=txt, reply_markup=markup, parse_mode="HTML")
            else:
                await query.delete_message()
                raise BadRequest("Recriar com Mídia")
        except BadRequest:
            try: await query.delete_message()
            except: pass
            
            if mid:
                try:
                    await context.bot.send_video(update.effective_chat.id, mid, caption=txt, reply_markup=markup, parse_mode="HTML")
                except:
                    try:
                        await context.bot.send_photo(update.effective_chat.id, mid, caption=txt, reply_markup=markup, parse_mode="HTML")
                    except:
                        await context.bot.send_message(update.effective_chat.id, txt, reply_markup=markup, parse_mode="HTML")
            else:
                await context.bot.send_message(update.effective_chat.id, txt, reply_markup=markup, parse_mode="HTML")
    else:
        if mid:
            try:
                await context.bot.send_video(update.effective_chat.id, mid, caption=txt, reply_markup=markup, parse_mode="HTML")
            except:
                try:
                    await context.bot.send_photo(update.effective_chat.id, mid, caption=txt, reply_markup=markup, parse_mode="HTML")
                except:
                    await context.bot.send_message(update.effective_chat.id, txt, reply_markup=markup, parse_mode="HTML")
        else:
            await context.bot.send_message(update.effective_chat.id, txt, reply_markup=markup, parse_mode="HTML")

async def wb_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() 
    
    user_id = _get_boss_user_id(update, context) # ID String
    pdata = await player_manager.get_player_data(user_id)
    
    status = await world_boss_manager.add_player_to_event(user_id, pdata)
    
    if status == "active":
        await wb_target_selection(update, context)
    elif status == "waiting":
        await query.answer("𝑭𝒊𝒍𝒂 𝒄𝒉𝒆𝒊𝒂! 𝑨𝒈𝒖𝒂𝒓𝒅𝒆.", show_alert=True)

async def wb_target_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = _get_boss_user_id(update, context)
    
    if user_id not in world_boss_manager.active_fighters:
        await query.answer("𝑽𝒐𝒄𝒆̂ 𝒔𝒂𝒊𝒖 𝒅𝒂 𝒍𝒖𝒕𝒂.", show_alert=True)
        await wb_start_menu(update, context)
        return

    kb = []
    ents = world_boss_manager.entities
    
    for key, ent in ents.items():
        if ent['alive']:
            status = " (🛡️)" if key == "boss" and (ents["witch_heal"]["alive"] or ents["witch_debuff"]["alive"]) else ""
            btn_txt = f"🎯 {ent['name']}{status}"
            kb.append([InlineKeyboardButton(btn_txt, callback_data=f"wb_set_target:{key}")])
            
    kb.append([InlineKeyboardButton("🔙 𝑽𝒐𝒍𝒕𝒂𝒓 / 𝑺𝒂𝒊𝒓", callback_data="wb_leave")])
    
    txt = "🏹 𝑺𝑬𝑳𝑬𝑪𝑰𝑶𝑵𝑬 𝑺𝑬𝑼 𝑨𝑳𝑽𝑶\n\nBʀᴜxᴀs ᴘʀᴏᴛᴇɢᴇᴍ ᴏ Bᴏss ᴇ ʟᴀɴᴄ̧ᴀᴍ ᴍᴀʟᴅɪᴄ̧ᴏ̃ᴇs!"
    await _smart_edit_message(query, txt, InlineKeyboardMarkup(kb))

async def wb_fight_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = _get_boss_user_id(update, context)
    
    pdata = await player_manager.get_player_data(user_id)
    stats = await player_manager.get_player_total_stats(pdata)
    
    txt = _format_battle_screen(user_id, pdata, stats)
    
    state = world_boss_manager.get_battle_view(user_id)
    respawn_until = state.get('respawn_until', 0) if state else 0
    now = time.time()
    
    kb = []
    
    if respawn_until > now:
        remaining = int(respawn_until - now)
        kb = [
            [InlineKeyboardButton(f"⏳ 𝐑𝐞𝐬𝐬𝐮𝐬𝐜𝐢𝐭𝐚𝐧𝐝𝐨... ({remaining}𝐬)", callback_data='wb_fight_return')],
            [InlineKeyboardButton("🏃 𝐅𝐮𝐠𝐢𝐫 / 𝐒𝐚𝐢𝐫", callback_data='wb_leave')]
        ]
        
    else:
        kb = [
            [
                InlineKeyboardButton("⚔️ 𝐀𝐓𝐀𝐂𝐀𝐑", callback_data='wb_act:attack'), 
                InlineKeyboardButton("✨ 𝐒𝐊𝐈𝐋𝐋𝐒", callback_data='wb_skills')
            ],
            [
                InlineKeyboardButton("🧪 𝐏𝐨ç𝐨̃𝐞𝐬", callback_data='wb_potion'),
                InlineKeyboardButton("🎯 𝐌𝐮𝐝𝐚𝐫 𝐀𝐥𝐯𝐨", callback_data='wb_targets')
            ],
            [
                InlineKeyboardButton("🏃 𝐅𝐮𝐠𝐢𝐫", callback_data='wb_leave')
            ]
        ]
    
    await _smart_edit_message(query, txt, InlineKeyboardMarkup(kb))

async def wb_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = _get_boss_user_id(update, context)
    
    if data.startswith("wb_set_target:"):
        target = data.split(":")[1]
        if world_boss_manager.set_target(user_id, target):
            await query.answer(f"Alvo: {target}")
            await wb_fight_screen(update, context)
        else:
            await query.answer("Alvo inválido.", show_alert=True)
            await wb_target_selection(update, context)
        return

    if data == "wb_targets":
        await wb_target_selection(update, context); return
    if data == "wb_leave":
        world_boss_manager.active_fighters.discard(user_id)
        await wb_start_menu(update, context); return

    if data.startswith("wb_act:") or data.startswith("wb_skill:"):
        pdata = await player_manager.get_player_data(user_id)
        
        if data.startswith("wb_skill:"):
            skill_id = data.split(":")[1]
            res = await world_boss_manager.process_action(user_id, pdata, "skill", skill_id)
        else:
            res = await world_boss_manager.process_action(user_id, pdata, "attack")
            
        if "error" in res:
            await query.answer(res['error'], show_alert=True)
            if "derrotado" in res['error']: await wb_target_selection(update, context)
            return
        
        if res.get("respawning"):
            wait = res.get("wait_time", 60)
            await query.answer(f"☠️ Morto! Aguarde {wait}s", show_alert=True)
            await wb_fight_screen(update, context) 
            return
        
        log_lines = res.get("state", {}).get("log", "").split("\n")
        last_log = log_lines[-1] if log_lines else "Ação OK"
        await query.answer(last_log[:100])

        if res.get("boss_defeated"):
            battle_results = world_boss_manager.end_event(reason="Boss derrotado")
            await distribute_loot_and_announce(context, battle_results)

            kb_vic = [[InlineKeyboardButton("🌍 𝐕𝐨𝐥𝐭𝐚𝐫 𝐚𝐨 𝐌𝐚𝐩𝐚", callback_data='wb_return_map')]]
            await _smart_edit_message(
                query, 
                "🏆 𝑽𝑰𝑻𝑶́𝑹𝑰𝑨! 𝑶 𝑩𝑶𝑺𝑺 𝑭𝑶𝑰 𝑫𝑬𝑹𝑹𝑶𝑻𝑨𝑫𝑶!\n\n💰 𝑂𝑠 𝑝𝑟𝑒̂𝑚𝑖𝑜𝑠 𝑓𝑜𝑟𝑎𝑚 𝑒𝑛𝑣𝑖𝑎𝑑𝑜𝑠 𝑝𝑜𝑟 𝑚𝑒𝑛𝑠𝑎𝑔𝑒𝑚 𝑝𝑟𝑖𝑣𝑎𝑑𝑎!", 
                InlineKeyboardMarkup(kb_vic)
            )
            return
        
        if res.get("game_over"):
            kb_die = [[InlineKeyboardButton("🔙 𝕄𝕖𝕟𝕦 𝕕𝕠 𝔹𝕠𝕤𝕤", callback_data='wb_menu'), InlineKeyboardButton("🌍 𝐌𝐀𝐏𝐀", callback_data='wb_return_map')]]
            await _smart_edit_message(query, f"☠️ 𝐕𝐎𝐂𝐄̂ 𝐌𝐎𝐑𝐑𝐄𝐔!\n\n{res['log']}", InlineKeyboardMarkup(kb_die))
            return
            
        await wb_fight_screen(update, context)

async def wb_skill_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = _get_boss_user_id(update, context)
    pdata = await player_manager.get_player_data(user_id)
    equipped = pdata.get("equipped_skills", [])
    kb = []
    
    for sid in equipped:
        sdata = get_skill_data_with_rarity(pdata, sid)
        if not sdata: continue
        
        name = sdata.get("display_name", sid)
        cost = sdata.get("mana_cost", 0)
        
        pode, msg = verificar_cooldown(pdata, sid)
        
        if not pode:
            kb.append([InlineKeyboardButton(f"⏳ {name} (ℂ𝔻)", callback_data="noop")])
        elif pdata.get("current_mp", 0) < cost:
            kb.append([InlineKeyboardButton(f"❌ {name} ({cost} 𝕄ℙ)", callback_data="noop")])
        else:
            kb.append([InlineKeyboardButton(f"✨ {name} ({cost} 𝕄ℙ)", callback_data=f"wb_skill:{sid}")])
            
    kb.append([InlineKeyboardButton("🔙 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="wb_fight_return")])
    
    await _smart_edit_message(query, "Selecione a Habilidade:", InlineKeyboardMarkup(kb))

async def wb_potion_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = _get_boss_user_id(update, context)
    pdata = await player_manager.get_player_data(user_id)
    inventory = pdata.get("inventory", {})
    
    kb = []
    has_potions = False
    
    for item_id, qty in inventory.items():
        item_info = game_data.ITEMS_DATA.get(item_id, {})
        if item_info.get("type") == "potion":
            has_potions = True
            name = item_info.get("display_name", item_id)
            emoji = item_info.get("emoji", "🧪")
            kb.append([InlineKeyboardButton(f"{emoji} {name} (x{qty})", callback_data=f"wb_use_potion:{item_id}")])
    
    if not has_potions:
        kb.append([InlineKeyboardButton("❌ Sem Poções", callback_data="noop")])
        
    kb.append([InlineKeyboardButton("🔙 Voltar", callback_data="wb_fight_return")])
    await _smart_edit_message(query, "🧪 <b>Selecione uma poção:</b>", InlineKeyboardMarkup(kb))

async def wb_use_potion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = _get_boss_user_id(update, context)
    data = query.data
    
    try:
        item_id = data.split(":")[1]
    except: return

    pdata = await player_manager.get_player_data(user_id)
    
    if not player_manager.remove_item_from_inventory(pdata, item_id, 1):
        await query.answer("Acabou!", show_alert=True)
        await wb_potion_menu(update, context)
        return

    item_info = game_data.ITEMS_DATA.get(item_id, {})
    effects = item_info.get("effects", {})
    msg_feed = ""
    
    if 'heal' in effects:
        await player_actions.heal_player(pdata, effects['heal'])
        msg_feed = f"Recuperou {effects['heal']} HP"
    elif 'add_mana' in effects:
        await player_actions.add_mana(pdata, effects['add_mana'])
        msg_feed = f"Recuperou {effects['add_mana']} MP"
    elif 'buff' in effects:
        player_actions.add_buff(pdata, effects['buff'])
        msg_feed = "Buff aplicado!"
    
    state = world_boss_manager.player_states.get(user_id)
    if state:
        state['hp'] = pdata.get("current_hp")
        state['mp'] = pdata.get("current_mp")
        if msg_feed:
            current_log = state.get('log', '')
            state['log'] = current_log + f"\n🧪 {msg_feed}"

    await player_manager.save_player_data(user_id, pdata)
    world_boss_manager.save_state()
    await query.answer(f"🧪 {msg_feed}")
    await wb_fight_screen(update, context)

async def wb_fight_return(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await wb_fight_screen(update, context)

wb_start_cmd = CommandHandler("iniciar_worldboss", iniciar_worldboss_command)
wb_stop_cmd = CommandHandler("encerrar_worldboss", encerrar_worldboss_command)
wb_cmd_handler = CommandHandler("worldboss", wb_start_menu)
wb_menu_handler = CallbackQueryHandler(wb_start_menu, pattern="^wb_menu$")
wb_join_handler = CallbackQueryHandler(wb_join, pattern="^wb_join$")
wb_router_handler = CallbackQueryHandler(wb_router, pattern="^(wb_set_target|wb_targets|wb_leave|wb_act|wb_skill:)")
wb_skill_menu_handler = CallbackQueryHandler(wb_skill_menu, pattern="^wb_skills$")
wb_potion_menu_handler = CallbackQueryHandler(wb_potion_menu, pattern="^wb_potion$")
wb_use_potion_handler = CallbackQueryHandler(wb_use_potion, pattern="^wb_use_potion:")
wb_fight_return_handler = CallbackQueryHandler(wb_fight_return, pattern="^wb_fight_return$")
wb_map_handler = CallbackQueryHandler(wb_return_to_map, pattern="^wb_return_map$")
wb_noop_handler = CallbackQueryHandler(lambda u,c: u.callback_query.answer("Indisponível"), pattern="^noop$")

all_world_boss_handlers = [
    wb_start_cmd, wb_stop_cmd, wb_cmd_handler, wb_menu_handler,
    wb_join_handler, wb_router_handler, wb_skill_menu_handler,
    wb_potion_menu_handler, wb_use_potion_handler,
    wb_fight_return_handler, wb_map_handler, wb_noop_handler
]