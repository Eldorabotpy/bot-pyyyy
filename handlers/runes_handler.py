# handlers/runes_handler.py
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules import player_manager, game_data
from modules.game_data import runes_data, items_runes

# Tenta importar o gerenciador de arquivos (para as imagens)
try:
    from modules import file_ids as media_ids
except ImportError:
    media_ids = None

# --- CONFIGURAÇÃO DE PREÇOS ---
COST_SOCKET_GOLD = 1000      # Preço para colocar runa
COST_REMOVE_GEM = 50         # Preço para tirar runa (salvar)
COST_REROLL_GEM = 25         # Preço para roletar

# ==============================================================================
# HELPER: PEGAR EQUIPAMENTOS (CORREÇÃO DO BUG)
# ==============================================================================
def get_safe_equipments(pdata: dict) -> dict:
    """Tenta pegar 'equipment' ou 'equipments' para evitar erro de chave."""
    return pdata.get("equipment") or pdata.get("equipments") or {}

# ==============================================================================
# 1. HELPER VISUAL (FOTO/VÍDEO)
# ==============================================================================
async def _send_media_menu(query, context, text, keyboard, media_key=None):
    chat_id = query.message.chat_id
    file_data = None
    if media_ids and hasattr(media_ids, "get_file_data") and media_key:
        file_data = media_ids.get_file_data(media_key)

    reply_markup = InlineKeyboardMarkup(keyboard)

    if file_data and file_data.get("id"):
        media_id = file_data["id"]
        media_type = (file_data.get("type") or "photo").lower()
        try: await query.delete_message()
        except Exception: pass

        if media_type == "video":
            await context.bot.send_video(chat_id=chat_id, video=media_id, caption=text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await context.bot.send_photo(chat_id=chat_id, photo=media_id, caption=text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        if query.message.photo or query.message.video:
            try: await query.delete_message()
            except: pass
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# ==============================================================================
# 2. LÓGICA DE BACKEND
# ==============================================================================

async def _deduct_currency(user_id: int, pdata: dict, currency_type: str, amount: int) -> bool:
    current = pdata.get("gold", 0) if currency_type == "gold" else pdata.get("gems", 0)
    if current >= amount:
        if currency_type == "gold": pdata["gold"] = current - amount
        else: pdata["gems"] = current - amount
        await player_manager.save_player_data(user_id, pdata)
        return True
    return False

async def logic_craft_rune_from_fragments(user_id: int) -> str:
    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {})
    frag_id = "fragmento_runa_ancestral"
    qtd = inv.get(frag_id, 0)
    if isinstance(qtd, dict): qtd = qtd.get("quantity", 0)
    
    if qtd < 7: return f"❌ Você precisa de 7 Fragmentos. Você só tem {qtd}."

    await player_manager.remove_item_from_inventory(pdata, frag_id, 7)
    
    # 7% Comum, 3% Maior, 0.5% Ancestral (Usando range 1000)
    roll = random.randint(1, 1000)
    if roll <= 5: tier = 3      # 0.5% (1-5)
    elif roll <= 200: tier = 2  # 19.5% (6-200)
    else: tier = 1              # 80% (201-1000)
    
    possiveis = runes_data.get_runes_by_tier(tier)
    rune_won = random.choice(possiveis) if possiveis else "runa_vampiro_menor"
        
    player_manager.add_item_to_inventory(pdata, rune_won, 1)
    await player_manager.save_player_data(user_id, pdata)
    r_info = runes_data.get_rune_info(rune_won)
    return f"✨ **SUCESSO!**\n\nOs fragmentos vibraram e se fundiram em:\n{r_info['emoji']} **{r_info['name']}**"

async def logic_socket_rune(user_id: int, slot_name: str, slot_index: int, rune_id: str) -> str:
    pdata = await player_manager.get_player_data(user_id)
    equipments = get_safe_equipments(pdata) # <-- USA O HELPER SEGURO
    target_item = equipments.get(slot_name)
    
    if not target_item: return "❌ Item não equipado."
    if not await _deduct_currency(user_id, pdata, "gold", COST_SOCKET_GOLD):
        return f"❌ Ouro insuficiente ({COST_SOCKET_GOLD} 💰)."
    if not await player_manager.remove_item_from_inventory(pdata, rune_id, 1):
        pdata["gold"] += COST_SOCKET_GOLD
        return "❌ Runa não encontrada."

    if "sockets" not in target_item: target_item["sockets"] = []
    while len(target_item["sockets"]) <= slot_index: target_item["sockets"].append(None)
        
    target_item["sockets"][slot_index] = rune_id
    await player_manager.save_player_data(user_id, pdata)
    return "✅ Runa incrustada com sucesso!"

async def logic_remove_rune(user_id: int, slot_name: str, slot_index: int) -> str:
    pdata = await player_manager.get_player_data(user_id)
    equipments = get_safe_equipments(pdata)
    target_item = equipments.get(slot_name)
    if not target_item: return "❌ Erro."
    
    rune_id = target_item["sockets"][slot_index]
    if not await _deduct_currency(user_id, pdata, "gems", COST_REMOVE_GEM):
        return f"❌ Gemas insuficientes ({COST_REMOVE_GEM} 💎)."

    target_item["sockets"][slot_index] = None
    player_manager.add_item_to_inventory(pdata, rune_id, 1)
    await player_manager.save_player_data(user_id, pdata)
    return "✅ Runa removida!"

async def logic_reroll_rune(user_id: int, slot_name: str, slot_index: int) -> str:
    pdata = await player_manager.get_player_data(user_id)
    equipments = get_safe_equipments(pdata)
    target_item = equipments.get(slot_name)
    
    rune_id = target_item["sockets"][slot_index]
    if not await _deduct_currency(user_id, pdata, "gems", COST_REROLL_GEM):
        return f"❌ Gemas insuficientes ({COST_REROLL_GEM} 💎)."

    info = runes_data.get_rune_info(rune_id)
    tier = info.get("tier", 1)
    possible_runes = runes_data.get_runes_by_tier(tier)
    new_rune_id = random.choice(possible_runes)
    
    target_item["sockets"][slot_index] = new_rune_id
    await player_manager.save_player_data(user_id, pdata)
    new_info = runes_data.get_rune_info(new_rune_id)
    return f"🎰 **Roleta Mística!**\nNova runa:\n{new_info.get('emoji')} **{new_info.get('name')}**!"

# ==============================================================================
# 3. MENUS (FRONTEND)
# ==============================================================================

async def npc_rune_master_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    pdata = await player_manager.get_player_data(user_id)
    equipments = get_safe_equipments(pdata) # <-- CORREÇÃO AQUI
    
    valid_items = []
    for slot, item in equipments.items():
        # Lógica Importante: O item precisa ter a lista 'sockets' para aparecer.
        # Itens antigos não têm isso. 
        if isinstance(item, dict) and "sockets" in item:
            valid_items.append((slot, item))
            
    # CENÁRIO 1: SEM ITENS VÁLIDOS
    if not valid_items:
        text = (
            "🏜️ **Tenda do Místico**\n\n"
            "O velho mago olha para o seu equipamento e suspira com desprezo...\n\n"
            "🧙‍♂️ _\"Você vem até mim com essa sucata? A magia rúnica exige recipientes de poder!_\n"
            "_Volte quando tiver uma arma ou armadura *Rara, Épica ou Lendária* equipada. (Itens antigos não servem, você precisa forjar novos!)\"_"
        )
        # Adiciona o botão de Craft mesmo se não tiver itens, para o jogador poder fundir runas
        kb = [
            [InlineKeyboardButton("✨ Mesa de Fusão (Craft)", callback_data="rune_npc:craft_menu")],
            [InlineKeyboardButton("🔙 Voltar", callback_data="show_kingdom_menu")]
        ]
        await _send_media_menu(query, context, text, kb, media_key="npc_mistico_triste")
        return

    # CENÁRIO 2: COM ITENS
    kb = []
    for slot, item in valid_items:
        name = item.get("display_name", "Item")
        emoji = item.get("emoji", "⚔️")
        dots = "".join(["🟣" if s else "⚪" for s in item.get("sockets", [])])
        kb.append([InlineKeyboardButton(f"{emoji} {name} {dots}", callback_data=f"rune_npc:select_item:{slot}")])
        
    kb.append([InlineKeyboardButton("✨ Fundir Fragmentos", callback_data="rune_npc:craft_menu")])
    kb.append([InlineKeyboardButton("🚪 Sair", callback_data="show_kingdom_menu")])
    
    gold = pdata.get('gold', 0)
    gems = pdata.get('gems', 0)
    
    text = (
        "🏜️ **Cabana do Místico Rúnico**\n\n"
        "🧙‍♂️ _\"Posso despertar o poder oculto do seu equipamento... por um preço.\"\_\n\n"
        f"💰 **Ouro:** `{gold:,}`   💎 **Gemas:** `{gems:,}`\n"
        "────────────────\n"
        "👇 **Escolha um item equipado:**"
    )
    await _send_media_menu(query, context, text, kb, media_key="npc_mistico_intro")

async def npc_crafting_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {})
    frag_id = "fragmento_runa_ancestral"
    qtd = inv.get(frag_id, 0)
    if isinstance(qtd, dict): qtd = qtd.get("quantity", 0)
    
    needed = 7
    bar = "🟦" * min(qtd, needed) + "⬜" * max(0, needed - qtd)
    
    text = (
        "⚗️ **Mesa de Fusão Rúnica**\n\n"
        f"🧩 **Fragmentos:** {qtd}\n"
        f"💠 **Progresso:** `{bar}` ({needed} necess.)\n\n"
        "_Junte 7 fragmentos para criar uma Runa Aleatória._"
    )
    kb = []
    if qtd >= needed:
        kb.append([InlineKeyboardButton("✨ FUNDIR AGORA ✨", callback_data="rune_npc:do_craft")])
    else:
        kb.append([InlineKeyboardButton(f"Faltam {needed-qtd} Fragmentos", callback_data="rune_npc:ignore")])
    kb.append([InlineKeyboardButton("🔙 Voltar", callback_data="rune_npc:main")])
    await _send_media_menu(query, context, text, kb, media_key="npc_mistico_intro")

async def npc_manage_item_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    slot_name = query.data.split(":")[2]
    user_id = query.from_user.id
    pdata = await player_manager.get_player_data(user_id)
    equipments = get_safe_equipments(pdata)
    item = equipments.get(slot_name)
    
    if not item:
        await query.answer("Item não encontrado!", show_alert=True)
        return await npc_rune_master_main(update, context)

    sockets = item.get("sockets", [])
    kb = []
    for idx, rune_id in enumerate(sockets):
        if rune_id is None:
            btn = f"{idx+1}️⃣ VAZIO ➕ Incrustar ({COST_SOCKET_GOLD}💰)"
            cb = f"rune_npc:open_inv:{slot_name}:{idx}"
        else:
            r_info = runes_data.get_rune_info(rune_id)
            btn = f"{idx+1}️⃣ {r_info.get('emoji')} {r_info.get('name')}"
            cb = f"rune_npc:options:{slot_name}:{idx}"
        kb.append([InlineKeyboardButton(btn, callback_data=cb)])
        
    kb.append([InlineKeyboardButton("🔙 Voltar", callback_data="rune_npc:main")])
    text = f"🛠 **{item.get('display_name')}**\n\nSelecione um engaste:"
    await _send_media_menu(query, context, text, kb, media_key="npc_mistico_intro")

async def npc_select_rune_inv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split(":")
    slot_name, slot_idx = parts[2], parts[3]
    user_id = query.from_user.id
    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {})
    
    runes_list = []
    for iid, data in inv.items():
        qty = data if isinstance(data, int) else data.get("quantity", 0)
        if qty > 0 and iid in items_runes.RUNE_ITEMS_DATA:
             r_db = items_runes.RUNE_ITEMS_DATA[iid]
             if r_db.get("category") == "socketable":
                 runes_list.append((iid, r_db, qty))
                 
    kb = []
    if not runes_list:
        kb.append([InlineKeyboardButton("🔙 Sem Runas (Voltar)", callback_data=f"rune_npc:select_item:{slot_name}")])
    else:
        for iid, info, qty in runes_list:
            btn = f"{info['emoji']} {info['display_name']} (x{qty})"
            kb.append([InlineKeyboardButton(btn, callback_data=f"rune_npc:do_socket:{slot_name}:{slot_idx}:{iid}")])
        kb.append([InlineKeyboardButton("🔙 Cancelar", callback_data=f"rune_npc:select_item:{slot_name}")])
    
    text = "🎒 **Selecione a Runa da sua mochila:**"
    await _send_media_menu(query, context, text, kb, media_key="npc_mistico_intro")

async def npc_slot_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split(":")
    slot_name, slot_idx = parts[2], parts[3]
    kb = [
        [InlineKeyboardButton(f"🎰 Roletar ({COST_REROLL_GEM}💎)", callback_data=f"rune_npc:do_reroll:{slot_name}:{slot_idx}")],
        [InlineKeyboardButton(f"⛏️ Remover ({COST_REMOVE_GEM}💎)", callback_data=f"rune_npc:do_remove:{slot_name}:{slot_idx}")],
        [InlineKeyboardButton("🔙 Voltar", callback_data=f"rune_npc:select_item:{slot_name}")]
    ]
    text = (f"🔮 **Manipulação Rúnica**\n\n"
            f"🎰 **Roletar:** Troca por outra aleatória do mesmo nível.\n"
            f"⛏️ **Remover:** Devolve a runa para a mochila.")
    await _send_media_menu(query, context, text, kb, media_key="npc_mistico_intro")

# ==============================================================================
# ROUTERS
# ==============================================================================

async def action_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    parts = data.split(":")
    action = parts[1]
    
    if action == "main": await npc_rune_master_main(update, context)
    elif action == "craft_menu": await npc_crafting_menu(update, context)
    elif action == "select_item": await npc_manage_item_slots(update, context)
    elif action == "open_inv": await npc_select_rune_inv(update, context)
    elif action == "options": await npc_slot_options(update, context)
    elif action == "ignore": await query.answer("Falta recursos!", show_alert=True)
    
    elif action == "do_craft":
        msg = await logic_craft_rune_from_fragments(query.from_user.id)
        await query.answer("Feito!", show_alert=False)
        await npc_crafting_menu(update, context)
        await context.bot.send_message(query.message.chat_id, msg, parse_mode="Markdown")

    elif action == "do_socket":
        msg = await logic_socket_rune(query.from_user.id, parts[2], int(parts[3]), parts[4])
        await query.answer(msg, show_alert=True)
        await npc_manage_item_slots(update, context)
        
    elif action == "do_remove":
        msg = await logic_remove_rune(query.from_user.id, parts[2], int(parts[3]))
        await query.answer(msg, show_alert=True)
        await npc_manage_item_slots(update, context)
        
    elif action == "do_reroll":
        msg = await logic_reroll_rune(query.from_user.id, parts[2], int(parts[3]))
        await query.answer("Feito!", show_alert=False)
        await npc_manage_item_slots(update, context)
        await context.bot.send_message(query.message.chat_id, msg, parse_mode="Markdown")

async def runes_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⚠️ Visite o Místico Rúnico no Deserto Ancestral!", show_alert=True)