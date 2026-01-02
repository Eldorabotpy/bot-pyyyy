# handlers/christmas_shop.py
# (VERSÃO FINAL: 100% BLINDADO - TODOS OS HANDLERS VERIFICADOS)

from datetime import datetime, timezone
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler
from modules.auth_utils import get_current_player_id  # <--- ÚNICA FONTE DE VERDADE
from modules import player_manager
from modules import file_ids

logger = logging.getLogger(__name__)

# ==============================================================================
# ⚙️ CONFIGURAÇÕES DO EVENTO
# ==============================================================================
NOW = datetime.now(timezone.utc)
EVENT_END_DATE = datetime(NOW.year + 1, 1, 1, 23, 59, 59, tzinfo=timezone.utc)

ITEM_COMUM = "presente_perdido" 
ITEM_RARO = "presente_dourado"  
KEY_VIDEO_NOEL = "video_cabana_noel"

# ==============================================================================
# 🎁 CATÁLOGO DA LOJA DO NOEL
# ==============================================================================
TROCAS_NOEL = {
    # --- 🔵 TROCAS POR PRESENTE PERDIDO ---
    "sigilo_protecao": {
        "nome": "Sigilo de Proteção", "custo": 100, "moeda": ITEM_COMUM,
        "recompensa_id": "sigilo_protecao", "qtd": 1, "tipo": "item", "emoji": "🛡️"
    },
    "pocao_cura_media": {
        "nome": "Poção de Cura Média", "custo": 30, "moeda": ITEM_COMUM,
        "recompensa_id": "pocao_cura_media", "qtd": 1, "tipo": "item", "emoji": "🍷"
    },
    "pocao_cura_leve": {
        "nome": "Poção de Cura Leve", "custo": 10, "moeda": ITEM_COMUM,
        "recompensa_id": "pocao_cura_leve", "qtd": 1, "tipo": "item", "emoji": "🧪"
    },
    # --- 🟡 TROCAS POR PRESENTE DOURADO ---
    "sombra_de_krampus": {
        "nome": "Skin: Sombra de Krampus", "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "sombra_de_krampus", "tipo": "skin", "emoji": "☠️"
    }, 
    "santo_da_nevasca": {
        "nome": "Skin: Santo da Nevasca", "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "santo_da_nevasca", "tipo": "skin", "emoji": "🧙‍♂️"
    },
    "aprendiz_do_santo": {
        "nome": "Skin: Aprendiz do Santo", "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "aprendiz_do_santo", "tipo": "skin", "emoji": "🧙‍♂️"
    },
    "discipulo_de_nicolau": {
        "nome": "Skin: Discípulo de Nicolau", "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "discipulo_de_nicolau", "tipo": "skin", "emoji": "👊"
    },
    "oni_de_natal": {
        "nome": "Skin: Oni de Natal", "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "oni_de_natal", "tipo": "skin", "emoji": "👺"
    },
    "lamina_da_estrela_guia": {
        "nome": "Skin: Lâmina da Estrela Guia", "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "lamina_da_estrela_guia", "tipo": "skin", "emoji": "💪"
    },
    "patrulheiro_do_polo_norte": {
        "nome": "Skin: Patrulheiro do Polo", "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "patrulheiro_do_polo_norte", "tipo": "skin", "emoji": "🏹"
    },
    "esmagador_de_chamines": {
        "nome": "Skin: Esmagador de Chaminés", "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "esmagador_de_chamines", "tipo": "skin", "emoji": "🪓"
    },
    "maestro_da_noite_feliz": {
        "nome": "Skin: Maestro da Noite", "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "maestro_da_noite_feliz", "tipo": "skin", "emoji": "😎"
    },
}

def is_event_active():
    return datetime.now(timezone.utc) < EVENT_END_DATE

async def _send_shop_interface(update, context, chat_id, text, reply_markup):
    """Gerencia envio ou edição da mensagem da loja de forma segura."""
    media_data = file_ids.get_file_data(KEY_VIDEO_NOEL)
    
    if update.callback_query:
        try:
            # Tenta editar caption se for mensagem de mídia
            if media_data and update.callback_query.message.video:
                await update.callback_query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="HTML")
            else:
                # Tenta editar texto se for mensagem normal
                await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="HTML")
        except Exception:
            # Fallback: apaga e envia novo
            try: await update.callback_query.delete_message()
            except: pass
            
            if media_data and media_data.get("id"):
                try: await context.bot.send_video(chat_id, media_data["id"], caption=text, reply_markup=reply_markup, parse_mode="HTML")
                except: await context.bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="HTML")
            else:
                await context.bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        # Resposta a comando
        if media_data and media_data.get("id"):
            try: await context.bot.send_video(chat_id, media_data["id"], caption=text, reply_markup=reply_markup, parse_mode="HTML")
            except: await context.bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="HTML")
        else:
            await context.bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="HTML")

# ==============================================================================
#  MENU PRINCIPAL
# ==============================================================================

async def open_christmas_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    # 🔒 BLINDAGEM 1: Identificação Segura
    user_id = get_current_player_id(update, context)
    chat_id = update.effective_chat.id

    if not user_id:
        if query: await query.answer("❌ Sessão inválida. Use /start.", show_alert=True)
        return

    if not is_event_active():
        await context.bot.send_message(chat_id, "🎅 <b>O Natal já passou!</b>\nVolte ano que vem!", parse_mode="HTML")
        return

    current_tab = context.user_data.get("xmas_tab", "items")

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        if query: await query.answer("❌ Perfil não encontrado.", show_alert=True)
        return

    inv = pdata.get("inventory", {})
    qtd_comum = int(inv.get(ITEM_COMUM, 0))
    qtd_raro = int(inv.get(ITEM_RARO, 0))

    text = (
        "🎄 <b>CABANA DO PAPAI NOEL</b> 🎄\n"
        "╰┈➤ <i>Troque seus presentes por recompensas!</i>\n\n"
        f"🎒 <b>Seus Recursos:</b>\n"
        f"🎁 Perdidos: <b>{qtd_comum}</b>\n"
        f"🌟 Dourados: <b>{qtd_raro}</b>\n\n"
        f"⏳ <i>Fim: 29/Dez</i>"
    )

    kb = []
    # Abas
    lbl_items = "✅ 🎁 ITENS" if current_tab == "items" else "🎁 Itens"
    lbl_skins = "✅ 🌟 SKINS" if current_tab == "skins" else "🌟 Skins"
    kb.append([
        InlineKeyboardButton(lbl_items, callback_data="xmas_tab_items"),
        InlineKeyboardButton(lbl_skins, callback_data="xmas_tab_skins")
    ])

    # Itens
    items_to_show = []
    for key, data in TROCAS_NOEL.items():
        if current_tab == "items" and data["tipo"] == "item":
            items_to_show.append((key, data))
        elif current_tab == "skins" and data["tipo"] == "skin":
            items_to_show.append((key, data))

    row = []
    for key, data in items_to_show:
        price_emoji = "🎁" if data["moeda"] == ITEM_COMUM else "🌟"
        default_emoji = "🎭" if data["tipo"] == "skin" else "📦"
        item_emoji = data.get("emoji", default_emoji) 
        
        btn_text = f"{item_emoji} {data['nome']} ({data['custo']}{price_emoji})"
        row.append(InlineKeyboardButton(btn_text, callback_data=f"noel_buy:{key}"))
        
        if len(row) == 2:
            kb.append(row); row = []
    if row: kb.append(row)

    kb.append([InlineKeyboardButton("⬅️ Sair da Cabana", callback_data="open_region:picos_gelados")])

    await _send_shop_interface(update, context, chat_id, text, InlineKeyboardMarkup(kb))

# ==============================================================================
#  AÇÕES (Abas e Compra)
# ==============================================================================

async def switch_tab_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # 🔒 BLINDAGEM 2: Verificação Obrigatória também na troca de abas
    user_id = get_current_player_id(update, context)
    if not user_id:
        await query.answer("❌ Sessão expirada.", show_alert=True)
        return

    new_tab = query.data.replace("xmas_tab_", "")
    context.user_data["xmas_tab"] = new_tab
    await open_christmas_shop(update, context)

async def buy_christmas_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # 🔒 BLINDAGEM 3: Verificação Obrigatória na compra
    user_id = get_current_player_id(update, context)
    
    if not user_id:
        await query.answer("❌ Sessão inválida. Digite /start.", show_alert=True)
        return

    try: 
        key = query.data.split(":")[1]
    except: 
        return

    offer = TROCAS_NOEL.get(key)
    if not offer:
        await query.answer("Item não encontrado!", show_alert=True)
        return

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        await query.answer("❌ Erro ao carregar perfil.", show_alert=True)
        return

    inv = pdata.get("inventory", {})
    custo = offer["custo"]
    moeda = offer["moeda"]
    
    saldo = int(inv.get(moeda, 0))
    if saldo < custo:
        n_moeda = "Presentes Perdidos" if moeda == ITEM_COMUM else "Presentes Dourados"
        await query.answer(f"❌ Falta {custo - saldo} {n_moeda}!", show_alert=True)
        return

    if offer["tipo"] == "skin":
        unlocked = pdata.get("unlocked_skins", [])
        if offer["recompensa_id"] in unlocked:
            await query.answer("⚠️ Você já tem essa skin!", show_alert=True)
            return

    # Transação
    player_manager.remove_item_from_inventory(pdata, moeda, custo)
    
    msg_f = ""
    if offer["tipo"] == "item":
        player_manager.add_item_to_inventory(pdata, offer["recompensa_id"], offer["qtd"])
        msg_f = f"✅ Comprou {offer['nome']}!"
    elif offer["tipo"] == "skin":
        pdata.setdefault("unlocked_skins", []).append(offer["recompensa_id"])
        msg_f = f"🎉 Skin {offer['nome']} liberada!"

    await player_manager.save_player_data(user_id, pdata)
    await query.answer(msg_f, show_alert=True)
    
    await open_christmas_shop(update, context)

# ==============================================================================
#  REGISTRO
# ==============================================================================
open_christmas_shop_handler = CallbackQueryHandler(open_christmas_shop, pattern="^christmas_shop_open$")
switch_tab_handler = CallbackQueryHandler(switch_tab_callback, pattern="^xmas_tab_")
buy_christmas_item_handler = CallbackQueryHandler(buy_christmas_item, pattern="^noel_buy:")
christmas_command = CommandHandler("natal", open_christmas_shop)