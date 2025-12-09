# handlers/christmas_shop.py

from datetime import datetime, timezone
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaVideo
from telegram.ext import ContextTypes, CallbackQueryHandler

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
        "nome": "Skin: Sombra de Krampus",
        "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "sombra_de_krampus", 
        "tipo": "skin"
    },
    "santo_da_nevasca": {
        "nome": "Skin: Santo da Nevasca",
        "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "santo_da_nevasca", 
        "tipo": "skin"
    },
    "espirito_da_rena_dourada": {
        "nome": "Skin: Espírito da Rena Dourada",
        "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "espirito_da_rena_dourada", 
        "tipo": "skin"
    },
    "oni_de_natal": {
        "nome": "Skin: Oni de Natal",
        "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "oni_de_natal", 
        "tipo": "skin"
    },
    "lamina_da_estrela_guia": {
        "nome": "Skin: Lâmina da Estrela Guia",
        "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "lamina_da_estrela_guia", 
        "tipo": "skin"
    },
    "patrulheiro_do_polo_norte": {
        "nome": "Skin: Patrulheiro do Polo Norte",
        "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "patrulheiro_do_polo_norte", 
        "tipo": "skin"
    },

    # Skins Mágicas
    "esmagador_de_chamines": {
        "nome": "Skin: Esmagador de Chaminés",
        "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "esmagador_de_chamines", 
        "tipo": "skin"
    },
    "maestro_da_noite_feliz": {
        "nome": "Skin: Maestro da Noite Feliz",
        "custo": 100, "moeda": ITEM_RARO,
        "recompensa_id": "maestro_da_noite_feliz", 
        "tipo": "skin"
    },
    
}

# ==============================================================================
# 🎅 FUNÇÕES AUXILIARES
# ==============================================================================

def is_event_active() -> bool:
    """Retorna True se ainda for antes de 29/Dez."""
    return datetime.now(timezone.utc) <= EVENT_END_DATE

def _get_item_count(pdata: dict, item_id: str) -> int:
    inv = pdata.get("inventory", {})
    return int(inv.get(item_id, 0))

# ==============================================================================
# 🎅 HANDLERS (LÓGICA DA LOJA)
# ==============================================================================

async def open_christmas_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # Não usamos answer() ainda pois vamos carregar mídia
    
    user_id = query.from_user.id
    pdata = await player_manager.get_player_data(user_id)

    # 1. Validações
    if not is_event_active():
        await query.answer("🎅 O Natal já passou! Volte ano que vem.", show_alert=True)
        return

    current_loc = pdata.get("current_location")
    if current_loc != "picos_gelados":
        await query.answer("❄️ A Cabana fica nos Picos Gelados!", show_alert=True)
        return

    # 2. Prepara Texto e Botões
    qtd_comum = _get_item_count(pdata, ITEM_COMUM)
    qtd_raro = _get_item_count(pdata, ITEM_RARO)

    text = (
        "🎅 <b>CABANA DO PAPAI NOEL</b> 🏠\n\n"
        "<i>Bem-vindo à minha oficina nos Picos Gelados!\n"
        "Troque seus presentes por itens mágicos ou visuais exclusivos!</i>\n\n"
        f"⏳ <b>Fim:</b> 29/Dez\n\n"
        f"🎒 <b>Seus Presentes:</b>\n"
        f"🎁 Perdidos: <b>{qtd_comum}</b>\n"
        f"🎁🌟 Dourados: <b>{qtd_raro}</b>"
    )

    keyboard = []
    # Loop simples para gerar botões (certifique-se que TROCAS_NOEL está completo acima)
    for key, info in TROCAS_NOEL.items():
        icone = "🎁" if info["moeda"] == ITEM_COMUM else "🎁🌟"
        btn_text = f"{info['nome']} ({info['custo']} {icone})"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"noel_buy:{key}")])

    keyboard.append([InlineKeyboardButton("⬅️ Sair da Cabana", callback_data="open_region:picos_gelados")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    # 3. LÓGICA INTELIGENTE DE MÍDIA (File IDs)
    
    # Tenta pegar o ID do banco (Rápido ⚡)
    media_id = file_ids.get_file_id(KEY_VIDEO_NOEL)
    
    try:
        if media_id:
            # --- CENÁRIO A: VÍDEO JÁ SALVO (Usa ID) ---
            await query.edit_message_media(
                media=InputMediaVideo(media=media_id, caption=text, parse_mode="HTML"),
                reply_markup=reply_markup
            )
        else:
            # --- CENÁRIO B: PRIMEIRO ACESSO (Faz Upload do PC) ---
            caminho_local = "assets/videos/cabana_noel.mp4"
            
            if os.path.exists(caminho_local):
                with open(caminho_local, 'rb') as f:
                    # Envia e captura a mensagem retornada
                    msg = await query.edit_message_media(
                        media=InputMediaVideo(media=f, caption=text, parse_mode="HTML"),
                        reply_markup=reply_markup
                    )
                    
                    # SALVA O ID NO BANCO AUTOMATICAMENTE 💾
                    if msg.video:
                        file_ids.save_file_id(KEY_VIDEO_NOEL, msg.video.file_id, "video")
                        logger.info(f"🎅 [NATAL] Novo ID de vídeo salvo: {KEY_VIDEO_NOEL}")
            else:
                # Se não tiver vídeo no PC nem no banco, manda sem vídeo
                logger.error(f"Arquivo não encontrado: {caminho_local}")
                if query.message.photo:
                    await query.edit_message_caption(caption=text + "\n(Vídeo off)", reply_markup=reply_markup, parse_mode="HTML")
                else:
                    await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="HTML")

    except Exception as e:
        # Fallback de erro (ex: mensagem anterior era texto puro e não dá pra editar media)
        # Deleta e envia novo limpo
        await query.message.delete()
        
        # Tenta usar ID ou Local novamente no envio limpo
        midia_envio = media_id if media_id else open("assets/videos/cabana_noel.mp4", "rb")
        
        try:
            msg = await context.bot.send_video(
                chat_id=user_id,
                video=midia_envio,
                caption=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            # Salva ID se foi upload local
            if not media_id and msg.video:
                file_ids.save_file_id(KEY_VIDEO_NOEL, msg.video.file_id, "video")
                
        except Exception as err_envio:
            logger.error(f"Erro fatal ao enviar vídeo da loja: {err_envio}")
            await context.bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup, parse_mode="HTML")

    await query.answer()
    
async def buy_christmas_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (Mantenha sua função de compra idêntica à anterior) ...
    # Só vou colocar o esqueleto aqui pra não faltar no copy-paste
    query = update.callback_query
    user_id = query.from_user.id
    
    try:
        item_key = query.data.split(":")[1]
    except IndexError: return

    offer = TROCAS_NOEL.get(item_key)
    if not offer:
        await query.answer("Item inválido.", show_alert=True)
        return

    if not is_event_active():
        await query.answer("O evento acabou!", show_alert=True)
        return

    pdata = await player_manager.get_player_data(user_id)
    custo = offer["custo"]
    moeda = offer["moeda"]
    saldo = _get_item_count(pdata, moeda)

    if saldo < custo:
        n_moeda = "Presentes Perdidos" if moeda == ITEM_COMUM else "Presentes Dourados"
        await query.answer(f"❌ Falta {custo - saldo} {n_moeda}!", show_alert=True)
        return

    # Checa Skin Repetida
    if offer["tipo"] == "skin":
        unlocked = pdata.get("unlocked_skins", [])
        if offer["recompensa_id"] in unlocked:
            await query.answer("⚠️ Você já tem essa skin!", show_alert=True)
            return

    # Processa Compra
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
    
    # Atualiza a loja
    await open_christmas_shop(update, context)

# ==============================================================================
# 📤 EXPORTS (Adicione no main.py)
# ==============================================================================
christmas_shop_handler = CallbackQueryHandler(open_christmas_shop, pattern="^christmas_shop_open$")
christmas_buy_handler = CallbackQueryHandler(buy_christmas_item, pattern="^noel_buy:")
