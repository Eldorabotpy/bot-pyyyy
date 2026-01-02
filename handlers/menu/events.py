# handlers/menu/events.py
# (VERSÃO ZERO LEGADO: HUB DE EVENTOS + AUTH SEGURA)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from modules import player_manager
from modules.dungeon_definitions import DUNGEONS
from modules.auth_utils import get_current_player_id

async def show_events_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Mostra o menu de eventos (HUB).
    Lista tanto a Defesa do Reino quanto as Dungeons (Catacumbas).
    """
    query = update.callback_query
    
    # 🔒 SEGURANÇA: Identificação via Auth Central
    user_id = get_current_player_id(update, context)
    if not user_id:
        if query: await query.answer("Sessão inválida. Use /start.", show_alert=True)
        return

    await query.answer()

    # Recupera dados usando String ID
    player_data = await player_manager.get_player_data(user_id)
    if not player_data:
        await query.edit_message_text("Erro ao carregar perfil.")
        return
    
    # Normaliza a localização
    player_location = player_data.get("current_location", "reino_eldora")

    text = "💀 <b>HUB DE EVENTOS ESPECIAIS</b> 💀\n\nEscolha seu desafio:"
    keyboard = []
    
    # ==================================================================
    # 1. BOTÃO DA DEFESA DO REINO
    # ==================================================================
    # Verifica se o jogador está no reino
    if player_location == 'reino_eldora':
        keyboard.append([
            InlineKeyboardButton("🛡️ Defesa do Reino (Ondas)", callback_data="defesa_reino_main")
        ])

    # ==================================================================
    # 2. BOTÕES DAS DUNGEONS (CATACUMBAS, ETC)
    # ==================================================================
    event_found = False
    
    # DUNGEONS é um dict fixo, não precisa de await
    for dungeon_id, dungeon_info in DUNGEONS.items():
        # Verifica se a dungeon pertence ao local atual do jogador
        if dungeon_info.get("entry_location") == player_location:
            event_found = True
            display_name = dungeon_info.get('display_name', 'Masmorra')
            keyboard.append([
                InlineKeyboardButton(f"💀 {display_name}", callback_data=f"dungeon_info_{dungeon_id}")
            ])

    # ==================================================================
    # 3. NAVEGAÇÃO
    # ==================================================================
    
    if not keyboard:
        text += "\n\n🚫 <i>Nenhum evento disponível nesta localização.</i>"

    # Define para onde o botão "Voltar" leva
    back_callback = "back_to_kingdom" if player_location == 'reino_eldora' else "continue_after_action"
    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data=back_callback)])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Lógica de renderização (Tenta manter imagem se existir, senão manda texto)
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode='HTML')
    except Exception:
        # Fallback se a mensagem anterior não tinha caption (era texto puro)
        try:
            await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='HTML')
        except:
            # Último recurso: apaga e envia novo
            try: await query.delete_message()
            except: pass
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )