# handlers/runes_handler.py
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules import player_manager, game_data
from modules.game_data import runes_data, items_runes
try:
    from modules import file_ids as media_ids
except ImportError:
    media_ids = None

# --- CONFIGURAÇÃO DE PREÇOS ---
COST_SOCKET_GOLD = 10000      # Preço para colocar runa
COST_REMOVE_GEM = 60         # Preço para tirar runa (salvar)
COST_REROLL_GEM = 30         # Preço para tentar a sorte

async def _send_media_menu(query, context, text, keyboard, media_key=None):
    """Envia ou edita mensagem com suporte a foto/vídeo."""
    chat_id = query.message.chat_id
    
    # Tenta pegar o ID da mídia (se configurado)
    file_data = None
    if media_ids and hasattr(media_ids, "get_file_data") and media_key:
        file_data = media_ids.get_file_data(media_key)

    # Se tiver mídia válida (Foto ou Vídeo)
    if file_data and file_data.get("id"):
        # Apaga a mensagem anterior para enviar a nova com foto limpa
        try: await query.delete_message()
        except Exception: pass

        media_type = (file_data.get("type") or "photo").lower()
        if media_type == "video":
            await context.bot.send_video(
                chat_id=chat_id, 
                video=file_data["id"], 
                caption=text, 
                reply_markup=InlineKeyboardMarkup(keyboard), 
                parse_mode="Markdown"
            )
        else:
            await context.bot.send_photo(
                chat_id=chat_id, 
                photo=file_data["id"], 
                caption=text, 
                reply_markup=InlineKeyboardMarkup(keyboard), 
                parse_mode="Markdown"
            )
    else:
        # Fallback: Se não tiver imagem, edita o texto (mais rápido)
        # Verifica se a mensagem anterior tinha mídia (para não dar erro de edição)
        if query.message.photo or query.message.video:
            try: await query.delete_message()
            except: pass
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==============================================================================
# LÓGICA DE BACKEND (ECONOMIA E MANIPULAÇÃO)
# ==============================================================================


async def _deduct_currency(user_id: int, pdata: dict, currency_type: str, amount: int) -> bool:
    """Helper para descontar dinheiro/diamante."""
    current = 0
    if currency_type == "gold":
        current = pdata.get("gold", 0)
    elif currency_type == "gems":
        current = pdata.get("gems", 0)
        
    if current >= amount:
        if currency_type == "gold":
            pdata["gold"] = current - amount
        else:
            pdata["gems"] = current - amount
        # Salva o desconto imediatamente para evitar dupes
        await player_manager.save_player_data(user_id, pdata)
        return True
    return False

async def logic_socket_rune(user_id: int, slot_name: str, slot_index: int, rune_id: str) -> str:
    pdata = await player_manager.get_player_data(user_id)
    
    # 1. Valida Item Equipado
    equipments = pdata.get("equipments", {})
    target_item = equipments.get(slot_name)
    
    if not target_item:
        return "❌ Erro: Você precisa estar com o item EQUIPADO para mexer nas runas."
        
    # 2. Valida Custo (GOLD)
    if not await _deduct_currency(user_id, pdata, "gold", COST_SOCKET_GOLD):
        return f"❌ Você não tem Ouro suficiente ({COST_SOCKET_GOLD} 💰)."

    # 3. Valida e Consome Runa do Inventário
    if not await player_manager.remove_item_from_inventory(pdata, rune_id, 1):
        # Estorno (caso raro de erro)
        pdata["gold"] += COST_SOCKET_GOLD
        await player_manager.save_player_data(user_id, pdata)
        return "❌ Você não possui essa runa no inventário."

    # 4. Aplica
    if "sockets" not in target_item: target_item["sockets"] = []
    # Garante tamanho da lista
    while len(target_item["sockets"]) <= slot_index:
        target_item["sockets"].append(None)
        
    target_item["sockets"][slot_index] = rune_id
    await player_manager.save_player_data(user_id, pdata)
    
    return "✅ Runa incrustada com sucesso!"

async def logic_remove_rune(user_id: int, slot_name: str, slot_index: int) -> str:
    pdata = await player_manager.get_player_data(user_id)
    target_item = pdata.get("equipments", {}).get(slot_name)
    
    if not target_item: return "❌ Item não equipado."
    
    # Valida Slot
    sockets = target_item.get("sockets", [])
    if slot_index >= len(sockets) or sockets[slot_index] is None:
        return "❌ Este slot já está vazio."
        
    rune_id = sockets[slot_index]

    # 2. Valida Custo (DIAMANTE)
    if not await _deduct_currency(user_id, pdata, "gems", COST_REMOVE_GEM):
        return f"❌ Você precisa de {COST_REMOVE_GEM} 💎 para remover esta runa com segurança."

    # 3. Remove e Devolve
    target_item["sockets"][slot_index] = None
    player_manager.add_item_to_inventory(pdata, rune_id, 1) # Devolve pro inv
    
    await player_manager.save_player_data(user_id, pdata)
    return "✅ Runa removida e devolvida ao inventário!"

async def logic_reroll_rune(user_id: int, slot_name: str, slot_index: int) -> str:
    pdata = await player_manager.get_player_data(user_id)
    target_item = pdata.get("equipments", {}).get(slot_name)
    
    if not target_item: return "❌ Item não equipado."
    
    sockets = target_item.get("sockets", [])
    current_rune_id = sockets[slot_index]
    if slot_index >= len(sockets) or current_rune_id is None:
        return "❌ Não há runa para roletar aqui."

    # 2. Valida Custo (DIAMANTE)
    if not await _deduct_currency(user_id, pdata, "gems", COST_REROLL_GEM):
        return f"❌ Você precisa de {COST_REROLL_GEM} 💎 para tentar a sorte."

    # 3. A Roleta (Gacha)
    # Descobre o Tier da runa atual para manter o nível
    info = runes_data.get_rune_info(current_rune_id)
    tier = info.get("tier", 1)
    
    # Busca todas as runas possíveis desse tier
    possible_runes = runes_data.get_runes_by_tier(tier)
    
    # Sorteia (pode cair a mesma)
    new_rune_id = random.choice(possible_runes)
    target_item["sockets"][slot_index] = new_rune_id
    
    await player_manager.save_player_data(user_id, pdata)
    
    new_info = runes_data.get_rune_info(new_rune_id)
    return f"🎰 **Roleta Mística!**\nSua runa se transformou em:\n{new_info.get('emoji')} **{new_info.get('name')}**!"

# ==============================================================================
# MENUS DO NPC (FRONTEND)
# ==============================================================================

async def npc_rune_master_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu principal do NPC: Visual Melhorado."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    pdata = await player_manager.get_player_data(user_id)
    equipments = pdata.get("equipments", {})
    
    # Filtra equipamentos válidos (Raro+)
    valid_items = []
    for slot, item in equipments.items():
        # Verifica se tem a lista de sockets (mesmo que vazia, item precisa ter capacidade)
        if isinstance(item, dict) and "sockets" in item:
            valid_items.append((slot, item))
            
    # --- CENÁRIO 1: SEM ITENS (Visual Triste) ---
    if not valid_items:
        text = (
            "🏜️ **Tenda do Místico**\n\n"
            "O velho mago olha para o seu equipamento e suspira com desprezo...\n\n"
            "🧙‍♂️ _\"Você vem até mim com essa sucata? A magia rúnica exige recipientes de poder!_\n"
            "_Volte quando tiver uma arma ou armadura **Rara, Épica ou Lendária** equipada.\"_"
        )
        kb = [[InlineKeyboardButton("🔙 Voltar", callback_data="show_kingdom_menu")]] # Ajuste o voltar se preferir
        
        # Usa a imagem de "triste" ou "recusa"
        await _send_media_menu(query, context, text, kb, media_key="npc_mistico_triste")
        return

    # --- CENÁRIO 2: COM ITENS (Menu Principal) ---
    kb = []
    for slot, item in valid_items:
        name = item.get("display_name", "Item")
        emoji = item.get("emoji", "⚔️")
        rarity = (item.get("rarity") or "").capitalize()
        
        # Contagem de slots visual (ex: [🟣⚪⚪])
        sockets = item.get("sockets", [])
        dots = ""
        for s in sockets:
            dots += "🟣" if s else "⚪"
            
        # Botão: ⚔️ Espada [Lendário] (🟣⚪)
        btn_text = f"{emoji} {name} [{rarity}] {dots}"
        kb.append([InlineKeyboardButton(btn_text, callback_data=f"rune_npc:select_item:{slot}")])
        
    kb.append([InlineKeyboardButton("🚪 Sair da Tenda", callback_data="show_kingdom_menu")])
    
    gold = pdata.get('gold', 0)
    gems = pdata.get('gems', 0)
    
    text = (
        "🏜️ **Cabana do Místico Rúnico**\n\n"
        "O ar dentro da tenda cheira a incenso e magia antiga. O Místico estende a mão esperando o pagamento.\n\n"
        "🧙‍♂️ _\"Posso fundir pedras de poder em seu equipamento... se você puder pagar.\"\_\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"💰 **Ouro:** `{gold:,}`\n"
        f"💎 **Gemas:** `{gems:,}`\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "👇 **Escolha um item equipado para encantar:**"
    )
    
    # Usa a imagem de "intro" ou "loja"
    await _send_media_menu(query, context, text, kb, media_key="npc_mistico_intro")

async def npc_manage_item_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra os slots de um item específico."""
    query = update.callback_query
    slot_name = query.data.split(":")[2]
    user_id = query.from_user.id
    
    pdata = await player_manager.get_player_data(user_id)
    item = pdata.get("equipments", {}).get(slot_name)
    
    if not item:
        await query.answer("Item não está mais equipado!", show_alert=True)
        return await npc_rune_master_main(update, context)

    sockets = item.get("sockets", [])
    kb = []
    
    for idx, rune_id in enumerate(sockets):
        if rune_id is None:
            # Slot Vazio -> Incrustar
            btn_txt = f"{idx+1}️⃣ [ VAZIO ] ➕ Incrustar ({COST_SOCKET_GOLD}💰)"
            cb_data = f"rune_npc:open_inv:{slot_name}:{idx}"
        else:
            # Slot Cheio -> Opções (Remover ou Roletar)
            r_info = runes_data.get_rune_info(rune_id)
            btn_txt = f"{idx+1}️⃣ {r_info.get('emoji')} {r_info.get('name')}"
            cb_data = f"rune_npc:options:{slot_name}:{idx}"
            
        kb.append([InlineKeyboardButton(btn_txt, callback_data=cb_data)])
        
    kb.append([InlineKeyboardButton("🔙 Escolher outro item", callback_data="rune_npc:main")])
    
    text = (f"🛠 **Gerenciando: {item.get('display_name')}**\n\n"
            "Escolha um slot para modificar:")
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def npc_slot_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sub-menu quando clica num slot ocupado (Remover ou Roletar)."""
    query = update.callback_query
    parts = query.data.split(":")
    slot_name, slot_idx = parts[2], parts[3]
    
    kb = [
        [InlineKeyboardButton(f"🎰 Tentar Sorte ({COST_REROLL_GEM}💎)", callback_data=f"rune_npc:do_reroll:{slot_name}:{slot_idx}")],
        [InlineKeyboardButton(f"⛏️ Remover Runa ({COST_REMOVE_GEM}💎)", callback_data=f"rune_npc:do_remove:{slot_name}:{slot_idx}")],
        [InlineKeyboardButton("🔙 Voltar", callback_data=f"rune_npc:select_item:{slot_name}")]
    ]
    
    text = ("🧙‍♂️ *O que deseja fazer com esta runa?*\n\n"
            f"🎰 **Roletar:** Troca por outra runa do mesmo grau aleatoriamente.\n"
            f"⛏️ **Remover:** Devolve a runa para sua mochila.")
            
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def npc_select_rune_inv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista runas do inventário para incrustar."""
    query = update.callback_query
    parts = query.data.split(":")
    slot_name, slot_idx = parts[2], parts[3]
    user_id = query.from_user.id
    
    pdata = await player_manager.get_player_data(user_id)
    inventory = pdata.get("inventory", {})
    
    # Filtra Runas
    runes_list = []
    for iid, data in inventory.items():
        qty = data if isinstance(data, int) else data.get("quantity", 0)
        if qty > 0 and iid in items_runes.RUNE_ITEMS_DATA:
             # Verifica se é "socketable" (evita fragmentos)
             r_db = items_runes.RUNE_ITEMS_DATA[iid]
             if r_db.get("category") == "socketable":
                 runes_list.append((iid, r_db, qty))
                 
    if not runes_list:
        await query.answer("Você não tem runas na mochila.", show_alert=True)
        return

    kb = []
    for iid, info, qty in runes_list:
        btn_txt = f"{info['emoji']} {info['display_name']} (x{qty})"
        kb.append([InlineKeyboardButton(btn_txt, callback_data=f"rune_npc:do_socket:{slot_name}:{slot_idx}:{iid}")])
        
    kb.append([InlineKeyboardButton("🔙 Cancelar", callback_data=f"rune_npc:select_item:{slot_name}")])
    
    await query.edit_message_text("🎒 **Escolha a Runa para incrustar:**", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

# --- HANDLERS DE AÇÃO ---

async def action_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    parts = data.split(":")
    action = parts[1]
    
    if action == "main":
        await npc_rune_master_main(update, context)
    elif action == "select_item":
        await npc_manage_item_slots(update, context)
    elif action == "open_inv":
        await npc_select_rune_inv(update, context)
    elif action == "options":
        await npc_slot_options(update, context)
        
    # Ações Lógicas
    elif action == "do_socket":
        # rune_npc:do_socket:slot_name:idx:rune_id
        msg = await logic_socket_rune(query.from_user.id, parts[2], int(parts[3]), parts[4])
        await query.answer(msg, show_alert=True)
        await npc_manage_item_slots(update, context)
        
    elif action == "do_remove":
        msg = await logic_remove_rune(query.from_user.id, parts[2], int(parts[3]))
        await query.answer(msg, show_alert=True)
        await npc_manage_item_slots(update, context)
        
    elif action == "do_reroll":
        msg = await logic_reroll_rune(query.from_user.id, parts[2], int(parts[3]))
        # Reroll pode ter mensagem longa, melhor editar texto
        await query.answer("A magia está acontecendo...", show_alert=False)
        await query.edit_message_text(msg, parse_mode="Markdown", 
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Ok", callback_data=f"rune_npc:select_item:{parts[2]}")]]))

# ==============================================================================
# ROUTER DE INVENTÁRIO (CORREÇÃO DE ERRO)
# ==============================================================================
# Como movemos tudo para o NPC, este handler agora apenas redireciona.
# Isso evita o erro "NameError" se o botão do inventário for clicado.

async def runes_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler para o botão 'Gerenciar Runas' do inventário.
    Avisa o jogador para ir ao NPC.
    """
    query = update.callback_query
    await query.answer("⚠️ Para gerenciar runas, equipe o item e visite o Místico Rúnico no Deserto Ancestral!", show_alert=True)