# handlers/menu/events.py
# (VERSÃO BLINDADA: Lê do regions.py e usa Auth de Sessão)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Importa o CORE para pegar dados seguros (User ou Player)
from modules.player.core import get_player_data
# Importa as definições NOVAS (Onde está o Pico do Grifo)
from modules.dungeons.regions import REGIONAL_DUNGEONS

async def show_events_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Exibe a lista de Calabouços/Eventos lendo diretamente do regions.py.
    Verifica se o jogador (User ou Player) tem a chave necessária.
    """
    query = update.callback_query
    if query:
        await query.answer()

    # 1. SEGURANÇA: Pega o ID da Sessão
    # Isso é CRUCIAL: Contas novas têm ID de sessão (ObjectId), contas velhas têm ID numérico.
    # O context.user_data["logged_player_id"] garante que pegamos o certo.
    user_id = context.user_data.get("logged_player_id")
    
    if not user_id:
        if query:
            await query.edit_message_text("⚠️ Sessão expirada. Digite /start novamente.")
        return

    # 2. Carrega dados BLINDADOS
    # O core.get_player_data sabe procurar tanto em 'users' quanto em 'players'
    player_data = await get_player_data(user_id)
    
    if not player_data:
        msg = "❌ Perfil não encontrado."
        if query: await query.edit_message_text(msg)
        else: await context.bot.send_message(update.effective_chat.id, msg)
        return

    # Pega o inventário para checar as chaves
    inventory = player_data.get("inventory", {})

    # 3. Monta o teclado dinamicamente lendo o regions.py
    keyboard = []
    
    text = (
        "⚔️ <b>Masmorras e Eventos</b> ⚔️\n\n"
        "Selecione um local para explorar.\n"
        "<i>É necessário possuir o item de acesso.</i>\n"
    )

    # Loop inteligente: Varre todas as regiões configuradas no regions.py
    # Assim que você adicionar algo novo no regions.py, aparece aqui automaticamente.
    found_any = False
    
    for region_key, data in REGIONAL_DUNGEONS.items():
        found_any = True
        label = data.get("label", region_key.replace("_", " ").title())
        emoji = data.get("emoji", "🏰")
        key_item = data.get("key_item", "cristal_de_abertura")
        
        # --- VERIFICAÇÃO DE CHAVE ---
        # Compatível com sistema novo (dict) e velho (int)
        key_qty = 0
        inv_item = inventory.get(key_item)
        
        if isinstance(inv_item, dict): 
            key_qty = 1 # É um item único (nova estrutura)
        else:
            try: key_qty = int(inv_item or 0) # É quantidade simples (estrutura antiga)
            except: key_qty = 0

        # Define visual do botão
        status_icon = "✅" if key_qty > 0 else "🔒"
        
        # Se não tiver a chave, mostra que está trancado mas deixa o botão (ou remove se preferir)
        # Aqui deixei visível para o jogador saber que o evento existe
        btn_text = f"{emoji} {label} ({status_icon})"
        
        # O callback 'dungeon_open' é capturado pelo modules/dungeons/engine.py ou runtime.py
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"dungeon_open:{region_key}")])

    if not found_any:
        text += "\n🚫 <i>Nenhum evento ativo no momento.</i>"

    # Botão de Voltar padrão (gerenciado pelo menu_handler)
    keyboard.append([InlineKeyboardButton("🔙 Voltar", callback_data="continue_after_action")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # 4. Envia ou Edita a mensagem
    if query and query.message:
        # Tenta editar a mensagem existente para evitar spam
        try:
            await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="HTML")
        except:
            # Se falhar (ex: era uma foto e agora é texto), apaga e manda novo
            await query.delete_message()
            await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup, parse_mode="HTML")