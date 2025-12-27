# handlers/christmas_shop.py

from datetime import datetime, timezone
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaVideo
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

from modules import player_manager
from modules import file_ids

logger = logging.getLogger(__name__)

# ==============================================================================
# ⚙️ CONFIGURAÇÕES DO EVENTO
# ==============================================================================
# O evento acaba dia 29 de Dezembro às 23:59 UTC
NOW = datetime.now(timezone.utc)
EVENT_END_DATE = datetime(NOW.year, 12, 29, 23, 59, 59, tzinfo=timezone.utc)

# Itens que dropam dos monstros (Configure no items.py)
ITEM_COMUM = "presente_perdido" # Troca por Sigilo
ITEM_RARO = "presente_dourado"  # Troca por Skins
KEY_VIDEO_NOEL = "video_cabana_noel"
# ==============================================================================
# 🎁 CATÁLOGO DA LOJA DO NOEL
# ==============================================================================
TROCAS_NOEL = {
    # --- 🔵 TROCAS POR PRESENTE PERDIDO (Itens Úteis) ---
    "sigilo_protecao": {
        "nome": "Sigilo de Proteção", # Nome do Item de Sigilo
        "custo": 100,                  # Preço em Presentes Perdidos
        "moeda": ITEM_COMUM,
        "recompensa_id": "sigilo_protecao", # <--- ID DO ITEM SIGILO NO SEU JOGO
        "qtd": 1, 
        "tipo": "item"
    },
    "pocao_cura_media": {
        "nome": "Poção de Cura Média",
        "custo": 30,
        "moeda": ITEM_COMUM,
        "recompensa_id": "pocao_cura_media",
        "qtd": 1,
        "tipo": "item"
    },
    "pocao_cura_leve": {
        "nome": "Poção de Cura Leve",
        "custo": 10,
        "moeda": ITEM_COMUM,
        "recompensa_id": "pocao_cura_leve",
        "qtd": 1,
        "tipo": "item"
    },

    # --- 🟡 TROCAS POR PRESENTE DOURADO (Skins de Natal - Uma por Classe) ---
    # Skins Físicas
    "sombra_de_krampus": {
        "nome": "Skin:Assassino Sombra de Krampus",
        "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "sombra_de_krampus", 
        "tipo": "skin"
    }, 
    "santo_da_nevasca": {
        "nome": "Skin:Mago Santo da Nevasca",
        "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "santo_da_nevasca", 
        "tipo": "skin"
    },
    "aprendiz_do_santo": {
        "nome": "Skin:Mago Aprendiz do Santo",
        "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "Aprendiz do Santo", 
        "tipo": "skin"
    },
    "discipulo_de_nicolau": {
        "nome": "Skin:Monge Discípulo de Nicolau",
        "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "espirito_da_rena_dourada", 
        "tipo": "skin"
    },
    "oni_de_natal": {
        "nome": "Skin:Samurai Oni de Natal",
        "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "oni_de_natal", 
        "tipo": "skin"
    },
    "lamina_da_estrela_guia": {
        "nome": "Skin: Guerreiro Lâmina da Estrela Guia",
        "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "lamina_da_estrela_guia", 
        "tipo": "skin"
    },
    "patrulheiro_do_polo_norte": {
        "nome": "Skin:Caçad Patrulheiro do Polo Norte",
        "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "patrulheiro_do_polo_norte", 
        "tipo": "skin"
    },

    "esmagador_de_chamines": {
        "nome": "Skin:Beserker Esmagador de Chaminés",
        "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "esmagador_de_chamines", 
        "tipo": "skin"
    },
    "maestro_da_noite_feliz": {
        "nome": "Skin:Bardo Maestro da Noite Feliz",
        "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "maestro_da_noite_feliz", 
        "tipo": "skin"
    },
    
}

# ==============================================================================
# 🎅 FUNÇÕES AUXILIARES
# ==============================================================================

def is_event_active():
    """Checa se o evento ainda está rolando."""
    return datetime.now(timezone.utc) < EVENT_END_DATE

async def _send_shop_interface(update, context, chat_id, text, reply_markup):
    """Envia ou Edita a mensagem da loja."""
    # Tenta enviar vídeo se disponível e for uma nova mensagem (não callback)
    # Mas como é navegação, vamos focar em editar texto para ser rápido.
    if update.callback_query:
        try:
            # Tenta editar a legenda (se for foto/video) ou texto
            try: await update.callback_query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="HTML")
            except: await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="HTML")
        except:
            # Se falhar (ex: mensagem muito antiga), envia nova
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        # Primeira abertura: Tenta mandar vídeo
        fd = file_ids.get_file_data(KEY_VIDEO_NOEL)
        if fd:
            try:
                if fd.get("type") == "video":
                    await context.bot.send_video(chat_id=chat_id, video=fd["id"], caption=text, reply_markup=reply_markup, parse_mode="HTML")
                else:
                    await context.bot.send_photo(chat_id=chat_id, photo=fd["id"], caption=text, reply_markup=reply_markup, parse_mode="HTML")
                return
            except: pass
        
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="HTML")

# ==============================================================================
#  MENU PRINCIPAL
# ==============================================================================
async def open_christmas_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if not is_event_active():
        await context.bot.send_message(chat_id, "🎅 <b>Ho Ho Ho... O Natal já acabou!</b>\nVolte ano que vem!", parse_mode="HTML")
        return

    # Recupera estado da aba (Padrão: 'items')
    current_tab = context.user_data.get("xmas_tab", "items")

    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {})
    
    # Saldos
    qtd_comum = int(inv.get(ITEM_COMUM, 0))
    qtd_raro = int(inv.get(ITEM_RARO, 0))

    # Texto Temático
    text = (
        "🎄 <b>CABANA DO PAPAI NOEL</b> 🎄\n"
        "╰┈➤ <i>Troque seus presentes por recompensas!</i>\n\n"
        f"🎒 <b>Seus Presentes:</b>\n"
        f"🎁 <b>Perdidos:</b> {qtd_comum}\n"
        f"🌟 <b>Dourados:</b> {qtd_raro}\n\n"
        f"⏳ <i>O evento acaba em breve!</i>"
    )

    # --- MONTAGEM DO TECLADO ---
    kb = []
    
    # 1. Linha de Abas
    # Destaca a aba ativa com ✅ ou brilho
    lbl_items = "✅ 🎁 ITENS" if current_tab == "items" else "🎁 Itens"
    lbl_skins = "✅ 🌟 SKINS" if current_tab == "skins" else "🌟 Skins"
    
    kb.append([
        InlineKeyboardButton(lbl_items, callback_data="xmas_tab_items"),
        InlineKeyboardButton(lbl_skins, callback_data="xmas_tab_skins")
    ])

    # 2. Grade de Itens (Baseada na Aba)
    items_to_show = []
    
    for key, data in TROCAS_NOEL.items():
        if current_tab == "items" and data["tipo"] == "item":
            items_to_show.append((key, data))
        elif current_tab == "skins" and data["tipo"] == "skin":
            items_to_show.append((key, data))

    # Monta grade 2x2
    row = []
    for key, data in items_to_show:
        price_emoji = "🎁" if data["moeda"] == ITEM_COMUM else "🌟"
        btn_text = f"{data['emoji']} {data['nome']} ({data['custo']}{price_emoji})"
        
        row.append(InlineKeyboardButton(btn_text, callback_data=f"xmas_buy_{key}"))
        
        if len(row) == 2:
            kb.append(row)
            row = []
    if row: kb.append(row) # Adiciona sobras

    # 3. Botão de Voltar (Para a região Picos Gelados)
    kb.append([InlineKeyboardButton("⬅️ Sair da Cabana", callback_data="open_region:picos_gelados")])

    reply_markup = InlineKeyboardMarkup(kb)
    
    await _send_shop_interface(update, context, chat_id, text, reply_markup)

# ==============================================================================
#  HANDLERS DE AÇÃO
# ==============================================================================

async def switch_tab_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Troca a aba e recarrega o menu."""
    query = update.callback_query
    new_tab = query.data.replace("xmas_tab_", "")
    
    # Atualiza estado
    context.user_data["xmas_tab"] = new_tab
    
    # Recarrega menu
    await open_christmas_shop(update, context)

async def buy_christmas_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa a compra."""
    query = update.callback_query
    # Não damos answer() aqui para poder mandar alerta se falhar, ou mensagem final
    
    key = query.data.replace("xmas_buy_", "")
    offer = TROCAS_NOEL.get(key)
    
    if not offer:
        await query.answer("Item não encontrado!", show_alert=True)
        return

    user_id = update.effective_user.id
    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {})
    
    custo = offer["custo"]
    moeda = offer["moeda"]
    
    # Verifica Saldo
    saldo = int(inv.get(moeda, 0))
    if saldo < custo:
        n_moeda = "Presentes Perdidos" if moeda == ITEM_COMUM else "Presentes Dourados"
        await query.answer(f"❌ Falta {custo - saldo} {n_moeda}!", show_alert=True)
        return

    # Verifica Skin Repetida
    if offer["tipo"] == "skin":
        unlocked = pdata.get("unlocked_skins", [])
        if offer["recompensa_id"] in unlocked:
            await query.answer("⚠️ Você já tem essa skin!", show_alert=True)
            return

    # --- EFETUA A COMPRA ---
    # 1. Remove moeda
    player_manager.remove_item_from_inventory(pdata, moeda, custo)
    
    # 2. Entrega Recompensa
    msg_f = ""
    if offer["tipo"] == "item":
        player_manager.add_item_to_inventory(pdata, offer["recompensa_id"], offer["qtd"])
        msg_f = f"✅ Comprou {offer['nome']}!"
    elif offer["tipo"] == "skin":
        pdata.setdefault("unlocked_skins", []).append(offer["recompensa_id"])
        msg_f = f"🎉 Skin {offer['nome']} liberada!"

    # 3. Salva
    await player_manager.save_player_data(user_id, pdata)
    
    await query.answer(msg_f, show_alert=True)
    
    # 4. Atualiza a loja (para mostrar saldo novo)
    await open_christmas_shop(update, context)

# ==============================================================================
#  REGISTRO DOS HANDLERS (Exportar isso para main.py ou registry)
# ==============================================================================
open_christmas_shop_handler = CallbackQueryHandler(open_christmas_shop, pattern="^christmas_shop_open$")
switch_tab_handler = CallbackQueryHandler(switch_tab_callback, pattern="^xmas_tab_")
buy_christmas_item_handler = CallbackQueryHandler(buy_christmas_item, pattern="^xmas_buy_")
christmas_command = CommandHandler("natal", open_christmas_shop)