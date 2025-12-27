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

def is_event_active():
    return datetime.now(timezone.utc) < EVENT_END_DATE

async def _send_shop_interface(update, context, chat_id, text, reply_markup):
    """Gerencia envio ou edição da mensagem da loja."""
    # Tenta usar vídeo se disponível
    media_data = file_ids.get_file_data(KEY_VIDEO_NOEL)
    
    if update.callback_query:
        # Tenta editar
        try:
            if media_data and update.callback_query.message.video:
                # Se já tem vídeo e o ID bate, edita só legenda/botões
                await update.callback_query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="HTML")
            else:
                # Se não tem vídeo ou é texto, tenta editar texto
                await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="HTML")
        except Exception:
            # Se falhar a edição (ex: mudar de texto pra mídia), apaga e envia novo
            try: await update.callback_query.delete_message()
            except: pass
            
            if media_data:
                try: await context.bot.send_video(chat_id, media_data["id"], caption=text, reply_markup=reply_markup, parse_mode="HTML")
                except: await context.bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="HTML")
            else:
                await context.bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        # Comando /natal
        if media_data:
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
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if not is_event_active():
        await context.bot.send_message(chat_id, "🎅 <b>O Natal já passou!</b>\nVolte ano que vem!", parse_mode="HTML")
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
        f"🎒 <b>Seus Recursos:</b>\n"
        f"🎁 Perdidos: <b>{qtd_comum}</b>\n"
        f"🌟 Dourados: <b>{qtd_raro}</b>\n\n"
        f"⏳ <i>Fim: 29/Dez</i>"
    )

    # --- MONTAGEM DO TECLADO ---
    kb = []
    
    # 1. Linha de Abas
    lbl_items = "✅ 🎁 ITENS" if current_tab == "items" else "🎁 Itens"
    lbl_skins = "✅ 🌟 SKINS" if current_tab == "skins" else "🌟 Skins"
    
    kb.append([
        InlineKeyboardButton(lbl_items, callback_data="xmas_tab_items"),
        InlineKeyboardButton(lbl_skins, callback_data="xmas_tab_skins")
    ])

    # 2. Grade de Itens
    items_to_show = []
    for key, data in TROCAS_NOEL.items():
        if current_tab == "items" and data["tipo"] == "item":
            items_to_show.append((key, data))
        elif current_tab == "skins" and data["tipo"] == "skin":
            items_to_show.append((key, data))

    # Grade 2 colunas
    row = []
    for key, data in items_to_show:
        price_emoji = "🎁" if data["moeda"] == ITEM_COMUM else "🌟"
        btn_text = f"{data['emoji']} {data['nome']} ({data['custo']}{price_emoji})"
        # CORREÇÃO AQUI: Usa 'noel_buy:' para bater com o handler
        row.append(InlineKeyboardButton(btn_text, callback_data=f"noel_buy:{key}"))
        
        if len(row) == 2:
            kb.append(row); row = []
    if row: kb.append(row)

    # 3. Voltar
    kb.append([InlineKeyboardButton("⬅️ Sair da Cabana", callback_data="open_region:picos_gelados")])

    await _send_shop_interface(update, context, chat_id, text, InlineKeyboardMarkup(kb))

# ==============================================================================
#  AÇÕES (Abas e Compra)
# ==============================================================================

async def switch_tab_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    new_tab = query.data.replace("xmas_tab_", "")
    context.user_data["xmas_tab"] = new_tab
    await open_christmas_shop(update, context)

async def buy_christmas_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    # CORREÇÃO AQUI: Usa split para pegar o ID limpo
    try: 
        key = query.data.split(":")[1]
    except: 
        return

    offer = TROCAS_NOEL.get(key)
    if not offer:
        await query.answer("Item não encontrado!", show_alert=True)
        return

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

    # Efetua Compra
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
    
    # Recarrega para atualizar saldo
    await open_christmas_shop(update, context)

# ==============================================================================
#  REGISTRO (Estes nomes DEVEM bater com registries/regions.py)
# ==============================================================================
open_christmas_shop_handler = CallbackQueryHandler(open_christmas_shop, pattern="^christmas_shop_open$")
switch_tab_handler = CallbackQueryHandler(switch_tab_callback, pattern="^xmas_tab_")
buy_christmas_item_handler = CallbackQueryHandler(buy_christmas_item, pattern="^noel_buy:")
christmas_command = CommandHandler("natal", open_christmas_shop)