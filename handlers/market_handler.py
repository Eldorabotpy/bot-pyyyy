# handlers/market_handler.py
# (VERSÃO 7.0: CORREÇÃO DE PAGAMENTO - OURO ENTRANDO NA CONTA)

import logging
import math
from typing import List, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters

# --- IMPORTS DE MÓDULOS ---
from modules import player_manager, game_data, file_id_manager, market_manager
from modules.game_data.attributes import ATTRIBUTE_ICONS
from modules.market_manager import render_listing_line as _mm_render_listing_line
from modules.player import inventory
from modules import market_utils
# --- CONFIGURAÇÃO DE LOGS ---
MARKET_BANNER_ID = "AgACAgEAAxkBAAED2yNpSeuYoYMKgn3QOSw8muSx60krHAACWQtrG65hUEbfXp3FzKe9PQEAAwIAA3kAAzYE"
LOG_GROUP_ID = -1002881364171
LOG_TOPIC_ID = 24475

# --- DISPLAY UTILS ---
try:
    from modules import display_utils
except Exception:
    class _DisplayFallback:
        @staticmethod
        def formatar_item_para_exibicao(item_criado: dict) -> str:
            emoji = item_criado.get("emoji", "🛠")
            name = item_criado.get("display_name", item_criado.get("name", "Item"))
            rarity = item_criado.get("rarity", "")
            if rarity:
                name = f"{name} [{rarity}]"
            return f"{emoji} {name}"
    display_utils = _DisplayFallback()

logger = logging.getLogger(__name__)

# ==============================
#  BLOQUEIO: Itens Premium
# ==============================
PREMIUM_BLOCK_LIST = {
    "emblema_guerreiro", "essencia_guardia", "essencia_furia", "selo_sagrado", "essencia_luz",
    "emblema_berserker", "totem_ancestral", "emblema_cacador", "essencia_precisao",
    "marca_predador", "essencia_fera", "emblema_monge", "reliquia_mistica", "essencia_ki",
    "emblema_mago", "essencia_arcana", "essencia_elemental", "grimorio_arcano",
    "emblema_bardo", "essencia_harmonia", "essencia_encanto", "batuta_maestria",
    "emblema_assassino", "essencia_sombra", "essencia_letal", "manto_eterno",
    "emblema_samurai", "essencia_corte", "essencia_disciplina", "lamina_sagrada",
    "tomo_passive_bulwark", "tomo_active_whirlwind", "tomo_active_holy_blessing", "tomo_passive_unstoppable",
    "tomo_active_unbreakable_charge", "tomo_passive_last_stand", "tomo_passive_animal_companion",
    "tomo_active_deadeye_shot", "tomo_passive_apex_predator", "tomo_active_iron_skin",
    "tomo_passive_elemental_strikes", "tomo_active_transcendence", "tomo_active_curse_of_weakness", 
    "tomo_passive_elemental_attunement", "tomo_active_meteor_swarm", "tomo_active_song_of_valor",
    "tomo_active_dissonant_melody", "tomo_passive_symphony_of_power", "tomo_active_shadow_strike", 
    "tomo_passive_potent_toxins", "tomo_active_dance_of_a_thousand_cuts", "tomo_passive_iai_stance",
    "tomo_active_parry_and_riposte", "tomo_active_banner_of_command", 
    "tomo_guerreiro_corte_perfurante", "tomo_berserker_golpe_selvagem", "tomo_cacador_flecha_precisa",
    "tomo_monge_rajada_de_punhos", "tomo_mago_bola_de_fogo", "tomo_bardo_melodia_restauradora",
    "tomo_assassino_ataque_furtivo", "tomo_samurai_corte_iaijutsu",
    'caixa_guerreiro_armadura_negra', 'caixa_guerreiro_placas_douradas',
    'caixa_mago_traje_arcano', 'caixa_assassino_manto_espectral', 'caixa_cacador_patrulheiro_elfico',
    'caixa_berserker_pele_urso', 'caixa_monge_quimono_dragao', 'caixa_bardo_traje_maestro',
    'caixa_samurai_armadura_shogun', 'caixa_samurai_armadura_demoniaca', 'caixa_samurai_encarnacao_sangrenta',
    'caixa_samurai_guardiao_celestial', 'caixa_samurai_chama_aniquiladora', 
}

PREMIUM_BLOCK_MSG = "🚫 Este é um item premium e deve ser vendido na Casa de Leilões (Gemas)."

# ==============================
#  UTILS BÁSICOS
# ==============================
def _gold(pdata: dict) -> int:
    return int(pdata.get("gold", 0))

def _set_gold(pdata: dict, value: int):
    pdata["gold"] = max(0, int(value))

def _item_label_from_base(base_id: str) -> str:
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}).get("display_name", base_id)

def _get_item_info(base_id: str) -> dict:
    try:
        info = game_data.get_item_info(base_id)
        if info: return dict(info)
    except Exception: pass
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

def _player_class_key(pdata: dict, fallback="guerreiro") -> str:
    for c in [(pdata.get("class") or pdata.get("classe")), pdata.get("class_type"), pdata.get("classe")]:
        if isinstance(c, dict): return c.get("type", "").strip().lower()
        if isinstance(c, str): return c.strip().lower()
    return fallback

def _cut_middle(s: str, maxlen: int = 56) -> str:
    s = (s or "").strip()
    return s if len(s) <= maxlen else s[:maxlen//2 - 1] + "… " + s[-maxlen//2:]

# ============================================================================
# HELPER: ENVIO INTELIGENTE (FOTO + TEXTO)
# ============================================================================
async def _update_market_interface(query, context, text, kb, image_id=None):
    """
    Tenta enviar imagem. Se falhar (ID errado, erro de servidor), 
    envia APENAS TEXTO para não travar o bot.
    """
    chat_id = query.message.chat_id
    
    # 1. Tenta enviar com Imagem
    if image_id:
        try:
            if query.message.photo:
                # Já tem foto -> Edita a mídia
                media = InputMediaPhoto(media=image_id, caption=text, parse_mode="HTML")
                await query.edit_message_media(media=media, reply_markup=kb)
                return # Sucesso, para por aqui
            else:
                # Era texto -> Apaga e manda foto
                await query.message.delete()
                await context.bot.send_photo(chat_id=chat_id, photo=image_id, caption=text, reply_markup=kb, parse_mode="HTML")
                return # Sucesso
        except Exception as e:
            # Se falhar (ex: ID errado), apenas loga e continua para o fallback de texto
            print(f"⚠️ Falha ao carregar imagem do mercado ({e}). Usando modo texto.")
    
    # 2. Fallback: Apenas Texto (Se a imagem falhou ou não foi fornecida)
    try:
        # Tenta editar se for mensagem de texto
        if not query.message.photo:
             await query.edit_message_text(text=text, reply_markup=kb, parse_mode="HTML")
        else:
             # Se era foto e deu erro ao editar mídia, apaga e manda texto
             await query.message.delete()
             await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=kb, parse_mode="HTML")
    except Exception as e2:
        # Último recurso: Apaga tudo e manda mensagem nova
        try: await query.message.delete()
        except: pass
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=kb, parse_mode="HTML")
        
async def _send_with_media(chat_id: int, context: ContextTypes.DEFAULT_TYPE, caption: str, kb: InlineKeyboardMarkup, media_keys: List[str]):
    for key in media_keys:
        fd = file_id_manager.get_file_data(key)
        if fd and fd.get("id"):
            try:
                if fd.get("type") == "video":
                    await context.bot.send_video(chat_id=chat_id, video=fd["id"], caption=caption, reply_markup=kb, parse_mode="HTML")
                else:
                    await context.bot.send_photo(chat_id=chat_id, photo=fd["id"], caption=caption, reply_markup=kb, parse_mode="HTML")
                return
            except Exception: continue
    await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=kb, parse_mode="HTML")

# ==============================
#  RENDERIZAÇÃO
# ==============================
RARITY_LABEL = {"comum": "Comum", "bom": "Boa", "raro": "Rara", "epico": "Épica", "lendario": "Lendária"}
_CLASS_DMG_EMOJI_FALLBACK = {"guerreiro": "⚔️", "berserker": "🪓", "cacador": "🏹", "assassino": "🗡", "bardo": "🎵", "monge": "🙏", "mago": "✨", "samurai": "🗡"}
_STAT_EMOJI_FALLBACK = {"dmg": "🗡", "hp": "❤️‍🩹", "defense": "🛡️", "initiative": "🏃", "luck": "🍀", "forca": "💪", "inteligencia": "🧠", "furia": "🔥"}

def _class_dmg_emoji(pclass: str) -> str:
    return getattr(game_data, "CLASS_DMG_EMOJI", {}).get((pclass or "").lower(), _CLASS_DMG_EMOJI_FALLBACK.get((pclass or "").lower(), "🗡"))

def _stat_emoji(stat: str, pclass: str) -> str:
    s = (stat or "").lower()
    if s == "dmg": return _class_dmg_emoji(pclass)
    return _STAT_EMOJI_FALLBACK.get(s, "❔")

# ============================================================================
# HELPER: Renderização Detalhada (Versão Oficial Integrada)
# ============================================================================
def _render_unique_line_safe(inst: dict, pclass: str) -> str:
    """
    Retorna o item formatado em 2 linhas usando os ÍCONES OFICIAIS.
    Linha 1: 『[20/20] 🧙 Brinco de Gema
    Linha 2: [1][Epico]: 🧠+1, ❤️‍🩹+50... 』 (⚪️⚪️)
    """
    
    # 1. Identificação
    base_id = inst.get("base_id") or inst.get("tpl") or "item"
    
    # Tenta usar display_utils para pegar info, se falhar usa fallback
    try:
        info = display_utils._item_info(base_id)
    except:
        info = {}
        
    name = inst.get("display_name") or inst.get("custom_name") or info.get("display_name") or base_id
    emoji = inst.get("emoji") or info.get("emoji") or "⚔️"
    
    # 2. Durabilidade
    try:
        cur_d, max_d = inst.get("durability", [20, 20])
        dura_str = f"[{int(cur_d)}/{int(max_d)}]"
    except:
        dura_str = "[??/??]"

    # 3. Tier e Raridade
    tier = inst.get("tier", 1)
    rarity = str(inst.get("rarity", "comum")).lower()
    # Tenta pegar título bonitinho (ex: Raro)
    try:
        rarity_label = display_utils._rarity_title(rarity)
    except:
        rarity_label = rarity.capitalize()

    # 4. CAPTURA DE ATRIBUTOS (Usando ATTRIBUTE_ICONS oficial)
    parts = []
    
    # Dano e Defesa (Físicos)
    atk = inst.get("attack") or inst.get("atk") or 0
    df = inst.get("defense") or inst.get("def") or 0
    if int(atk) > 0: parts.append(f"⚔️{atk}")
    if int(df) > 0:  parts.append(f"🛡️{df}")

    # Mescla Encantamentos + Atributos
    all_stats = {}
    
    # Pega 'attributes' (comuns em drops)
    attrs = inst.get("attributes", {})
    if isinstance(attrs, dict):
        all_stats.update(attrs)
        
    # Pega 'enchantments' (comuns em craft)
    enchs = inst.get("enchantments", {})
    if isinstance(enchs, dict):
        all_stats.update(enchs)

    # Itera sobre tudo
    for key, val_obj in all_stats.items():
        # Ignora chaves técnicas
        if key in ["slots", "runes", "durability", "rarity", "tier", "source", "class_lock"]: 
            continue
            
        # Normaliza o valor
        final_val = 0
        if isinstance(val_obj, (int, float)):
            final_val = int(val_obj)
        elif isinstance(val_obj, dict):
            final_val = int(val_obj.get("value", 0))
            
        if final_val > 0:
            # --- AQUI ESTA A MÁGICA: Usa o ícone do attributes.py ---
            # Ex: "vida" vira "❤️‍🩹", "forca" vira "💪"
            icon = ATTRIBUTE_ICONS.get(key.lower())
            
            # Se não achou no oficial, tenta mapear chaves em inglês/português comuns
            if not icon:
                k = key.lower()
                if k in ["str", "strength"]: icon = "💪"
                elif k in ["int", "intelligence"]: icon = "🧠"
                elif k in ["agi", "agility"]: icon = "🏃"
                elif k in ["vit", "vitality", "hp_max"]: icon = "❤️‍🩹"
                elif k in ["luk", "luck"]: icon = "🍀"
                elif k in ["crit", "crit_chance"]: icon = "🎯"
                else: icon = "✨" # Genérico
            
            parts.append(f"{icon}+{final_val}")

    stats_str = ", ".join(parts)
    if stats_str: stats_str = f": {stats_str}" 

    # 5. Sockets
    sockets_str = ""
    slots = int(inst.get("slots", 0))
    if slots > 0:
        runes = inst.get("runes", [])
        visuals = ["⚫" if i < len(runes) else "⚪️" for i in range(slots)]
        sockets_str = f" ({''.join(visuals)})"

    # MONTAGEM FINAL EM 2 LINHAS
    line1 = f"『{dura_str} {emoji} {name}"
    line2 = f"[{tier}][{rarity_label}]{stats_str} 』{sockets_str}"
    
    return f"{line1}\n{line2}"

# ============================================================================
# 🎨 RENDERIZADOR ESTILIZADO (COM DETECTOR DE CLASSE)
# ============================================================================

# Lista de Classes para detecção e emojis
CLASS_ICONS = {
    "guerreiro": "⚔️",
    "cavaleiro": "🛡️", 
    "gladiador": "🔱",
    "mago": "🧙‍♂️",
    "arquimago": "🔮",
    "feiticeiro": "🔥",
    "arqueiro": "🏹",
    "cacador": "🏹",
    "patrulheiro": "🍃",
    "clerigo": "✝️",
    "sacerdote": "🙏",
    "ladino": "🗡️",
    "assassino": "🥷",
    "ninja": "🥷",
    "paladino": "🛡️",
    "necromante": "💀",
    "druida": "🌿",
    "monge": "👊",
    "bardo": "🎶",
    "berserker": "🪓",
    "samurai": "👺",
    "universal": "🌎",
    "todos": "🌎"
}

def _render_card_item(inst: dict, pclass: str, price: int, seller: str, lid: int) -> str:
    """
    Renderiza item Único com detecção automática de classe pelo ID.
    """
    # 1. Dados Básicos
    base_id = inst.get("base_id") or inst.get("tpl") or "item"
    try: info = display_utils._item_info(base_id)
    except: info = {}
        
    name = inst.get("display_name") or inst.get("custom_name") or info.get("display_name") or base_id
    emoji = inst.get("emoji") or info.get("emoji") or "⚔️"
    rarity = str(inst.get("rarity", "comum")).upper()
    
    # 2. DETECÇÃO DE CLASSE (Lógica Melhorada)
    # Tenta pegar do item salvo ou do info
    raw_class = inst.get("class_lock") or inst.get("class") or info.get("class_lock")
    
    # --- FALLBACK INTELIGENTE ---
    # Se não achou a classe, procura o nome dela dentro do ID do item (ex: 'brinco_mago')
    if not raw_class or str(raw_class).lower() in ["none", "universal", "todos"]:
        base_id_lower = base_id.lower()
        found = False
        # Verifica se alguma classe conhecida está no nome do item
        for c_key in CLASS_ICONS.keys():
            if c_key in ["universal", "todos"]: continue
            if c_key in base_id_lower:
                raw_class = c_key
                found = True
                break
        if not found:
            raw_class = "universal"

    raw_class = str(raw_class).lower()
    
    # Formata o visual (ex: "⚔️ Guerreiro")
    class_emoji = CLASS_ICONS.get(raw_class, "🛡️") 
    if raw_class == "universal":
        class_display = "🌎 Universal"
    else:
        class_display = f"{class_emoji} {raw_class.capitalize()}"
    
    # Durabilidade
    try:
        cur, mx = inst.get("durability", [20,20])
        dura_str = f"[{int(cur)}/{int(mx)}]"
    except: dura_str = ""

    # 3. Atributos (Stats)
    parts = []
    
    # Dano/Defesa
    atk = inst.get("attack") or inst.get("atk") or 0
    df = inst.get("defense") or inst.get("def") or 0
    if int(atk) > 0: parts.append(f"⚔️{atk}")
    if int(df) > 0:  parts.append(f"🛡️{df}")

    # Stats Gerais
    all_stats = {}
    if isinstance(inst.get("attributes"), dict): all_stats.update(inst["attributes"])
    if isinstance(inst.get("enchantments"), dict): all_stats.update(inst["enchantments"])

    for key, val_obj in all_stats.items():
        if key in ["slots", "runes", "durability", "rarity", "tier", "source", "class_lock", "class"]: continue
        
        final_val = 0
        if isinstance(val_obj, (int, float)): final_val = int(val_obj)
        elif isinstance(val_obj, dict): final_val = int(val_obj.get("value", 0))
            
        if final_val > 0:
            icon = ATTRIBUTE_ICONS.get(key.lower(), "✨")
            parts.append(f"{icon}+{final_val}")

    stats_text = ", ".join(parts)
    if not stats_text: stats_text = "Sem atributos"

    # Sockets
    slots = int(inst.get("slots", 0))
    runes = inst.get("runes", [])
    socket_vis = ""
    if slots > 0:
        socket_vis = " " + "".join(["⚫" if i < len(runes) else "⚪️" for i in range(slots)])

    # 4. Montagem Final
    line1 = f"{emoji} <b>{name}</b> [{rarity}] {dura_str}"
    line2 = f"├┈➤ <b>{class_display}</b> │ <i>{stats_text}</i>{socket_vis}"
    line3 = f"╰┈➤ 💸 <b>{price:,} 🪙</b>  👤 <i>{seller}</i>"

    return f"{line1}\n{line2}\n{line3}"

def _render_card_stack(inst: dict, price: int, seller: str, lote_qty: int) -> str:
    """Renderiza item Stack com o mesmo estilo."""
    base_id = inst.get("base_id")
    qty = inst.get("qty", 1)
    
    try: info = display_utils._item_info(base_id)
    except: info = {}
    
    name = info.get("display_name") or base_id.replace("_", " ").title()
    emoji = info.get("emoji", "📦")
    
    line1 = f"{emoji} <b>{name}</b> x{qty}"
    line2 = f"├┈➤ 📦 <i>Lote de {lote_qty} un.</i>"
    line3 = f"╰┈➤ 💸 <b>{price:,} 🪙</b>  👤 <i>{seller}</i>"
    
    return f"{line1}\n{line2}\n{line3}"

# ==============================
#  MENUS PRINCIPAIS
# ==============================
async def market_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎒 𝐌𝐞𝐫𝐜𝐚𝐝𝐨 𝐝𝐨 𝐀𝐯𝐞𝐧𝐭𝐮𝐫𝐞𝐢𝐫𝐨", callback_data="market_adventurer")],
        [InlineKeyboardButton(" 🏛️ 𝐂𝐨𝐦𝐞́𝐫𝐜𝐢𝐨 𝐝𝐞 𝐑𝐞𝐥𝐢́𝐪𝐮𝐢𝐚𝐬 💎 ", callback_data="gem_market_main")],
        [InlineKeyboardButton("🏰 𝐋𝐨𝐣𝐚 𝐝𝐨 𝐑𝐞𝐢𝐧𝐨", callback_data="market_kingdom")],
        [InlineKeyboardButton("💎 𝐋𝐨𝐣𝐚 𝐝𝐞 𝐆𝐞𝐦𝐚𝐬", callback_data="gem_shop")],
        [InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫", callback_data="continue_after_action")],
    ])
    try: await q.delete_message()
    except Exception: pass 
    await _send_with_media(chat_id, context, "🛒 <b>Mercado</b>\nEscolha uma opção:", kb, ["market", "mercado_principal"])

async def market_adventurer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Listagens (Ver Itens)", callback_data="market_list")],
        [InlineKeyboardButton("➕ Vender Item", callback_data="market_sell:1")],
        [InlineKeyboardButton("👤 Minhas Listagens", callback_data="market_my")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market")],
    ])
    text = "🎒 <b>Mercado do Aventureiro</b>\nCompre e venda itens com outros jogadores."
    try: await q.delete_message()
    except Exception: pass
    await _send_with_media(update.effective_chat.id, context, text, kb, ["mercado_aventureiro", "market_adventurer"])

# ============================================================================
# NOVA VERSÃO: MARKET LIST (Estilo RPG + Paginação)
# ============================================================================
async def market_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    
    try: page = int(q.data.split(':')[1])
    except: page = 1

    pdata = await player_manager.get_player_data(user_id)
    pclass = _player_class_key(pdata)
    is_premium = player_manager.has_premium_plan(pdata)
    current_gold = inventory.get_gold(pdata)

    # Carrega itens
    all_listings = market_manager.list_active(viewer_id=user_id, page=1, page_size=200)
    
    if not all_listings:
        await _safe_edit_or_send(q, context, update.effective_chat.id, 
            "💤 <b>Mercado Vazio</b>\n\nNinguém está vendendo nada agora.", 
            InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]]))
        return

    # Paginação
    ITEMS_PER_PAGE = 5 
    total_items = len(all_listings)
    total_pages = math.ceil(total_items / ITEMS_PER_PAGE)
    page = max(1, min(page, total_pages))
    
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    current_page_listings = all_listings[start:end]

    # --- CABEÇALHO PERSONALIZADO ---
    lines = [
        f"╭┈┈┈┈┈➤ 🛒 <b>MERCADO</b> ({page}/{total_pages}) ┈┈┈┈┈╮",
        f" │ 💰 <b>Seu Saldo:</b> {current_gold:,} 🪙",
        f"╰┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤",
        ""
    ]
    if not is_premium: lines.append("🔒 <i>Apenas VIPs podem comprar.</i>\n")

    item_map = {} 
    
    for idx, l in enumerate(current_page_listings, start=1):
        item_data = l.get("item", {})
        item_type = item_data.get("type")
        price = l.get("unit_price", 0)
        lid = l.get("id")
        
        # Resolve Vendedor
        seller_name = l.get("seller_name")
        seller_id = l.get("seller_id")
        if (not seller_name or seller_name == "Desconhecido") and seller_id:
            try:
                s_data = await player_manager.get_player_data(int(seller_id))
                if s_data: seller_name = s_data.get("character_name", "Vendedor")
            except: seller_name = "Vendedor"
        if not seller_name: seller_name = str(seller_id)

        item_map[idx] = lid
        icon_num = f"{idx}\uFE0F\u20E3" 

        # Renderiza o Card
        if item_type == "unique":
            card = _render_card_item(item_data.get("item", {}), pclass, price, seller_name, lid)
        else:
            qty_lotes = l.get("quantity", 1)
            card = _render_card_stack(item_data, price, seller_name, qty_lotes)

        # Monta a linha com a seta conectando o número ao item
        # Ex: 1️⃣┈➤🧿 Item...
        lines.append(f"{icon_num}┈➤{card}")
        lines.append("") # Espaço entre itens

    # Botões
    kb = []
    buy_row = []
    for idx in range(1, len(current_page_listings) + 1):
        real_id = item_map[idx]
        btn_txt = f"{idx} 🛒"
        if is_premium:
            buy_row.append(InlineKeyboardButton(btn_txt, callback_data=f"market_buy_{real_id}"))
        else:
            buy_row.append(InlineKeyboardButton(f"{idx} 🔒", callback_data="noop_vip_only"))
    if buy_row: kb.append(buy_row)

    nav_row = []
    if page > 1: nav_row.append(InlineKeyboardButton("⬅️ Ant.", callback_data=f"market_list:{page-1}"))
    nav_row.append(InlineKeyboardButton("🎒 Menu", callback_data="market_adventurer"))
    if page < total_pages: nav_row.append(InlineKeyboardButton("Prox. ➡️", callback_data=f"market_list:{page+1}"))
    kb.append(nav_row)

    await _update_market_interface(q, context, "\n".join(lines), InlineKeyboardMarkup(kb), image_id=MARKET_BANNER_ID)

# Helpers
def _player_class_key(pdata):
    return pdata.get("class", "guerreiro") if pdata else "guerreiro"

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup):
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="HTML")

# Função auxiliar para evitar travamento se context.user_data não tiver class
def _player_class_key(pdata):
    return pdata.get("class", "guerreiro") if pdata else "guerreiro"

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup):
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="HTML")

async def market_my(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    pdata = await player_manager.get_player_data(user_id)
    
    my = market_manager.list_by_seller(user_id)
    if not my:
        await _safe_edit_or_send(q, context, update.effective_chat.id, "Você não tem listagens.", 
                                 InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]]))
        return

    lines = ["👤 <b>Minhas listagens</b>\n"]
    kb = []
    for l in my:
        lines.append("• " + _mm_render_listing_line(l, viewer_player_data=pdata, show_price_per_unit=True))
        kb.append([InlineKeyboardButton(f"Cancelar #{l['id']}", callback_data=f"market_cancel_{l['id']}")])
    
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")])
    await _safe_edit_or_send(q, context, update.effective_chat.id, "\n".join(lines), InlineKeyboardMarkup(kb))

# ==============================
#  FLUXO DE VENDA
# ==============================
# handlers/market_handler.py

async def market_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    
    try: page = int(q.data.split(':')[1])
    except: page = 1
    
    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {}) or {}
    pclass = _player_class_key(pdata)
    
    sellable = []
    
    # --- FILTRO DE LIMPEZA VISUAL ---
    # Itens que contiverem isso no ID serão ignorados na venda
    BAD_PATTERNS = ["tomo_tomo_", "livro_livro_", "undefined", "null"]
    # --------------------------------

    for uid, inst in inv.items():
        # Verifica se é item bugado
        if any(bad in str(uid) for bad in BAD_PATTERNS): continue

        if isinstance(inst, dict):
            base_id = inst.get("base_id", uid)
            # Verifica se base_id é bugado ou bloqueado
            if any(bad in str(base_id) for bad in BAD_PATTERNS): continue
            if base_id not in PREMIUM_BLOCK_LIST:
                if len(f"market_pick_unique_{uid}") > 60: continue
                sellable.append({"type": "unique", "uid": uid, "inst": inst, "sort": base_id})
                
    for bid, qty in inv.items():
        # Verifica se é item bugado
        if any(bad in str(bid) for bad in BAD_PATTERNS): continue

        if isinstance(qty, (int, float)) and qty > 0 and bid not in PREMIUM_BLOCK_LIST:
            sellable.append({"type": "stack", "base_id": bid, "qty": int(qty), "sort": bid})
    
    sellable.sort(key=lambda x: x["sort"] or "")
    
    ITEMS_PER_PAGE = 8
    total = len(sellable)
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    items_page = sellable[start:end]
    
    if not sellable:
        await _safe_edit_or_send(q, context, update.effective_chat.id, 
            "🎒 <b>Inventário vazio ou itens não listáveis.</b>", 
            InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]]))
        return

    kb = []
    for it in items_page:
        if it["type"] == "unique":
            txt = _render_unique_line_safe(it["inst"], pclass)
            kb.append([InlineKeyboardButton(_cut_middle(txt, 56), callback_data=f"market_pick_unique_{it['uid']}")])
        else:
            name = _item_label_from_base(it["base_id"])
            kb.append([InlineKeyboardButton(f"📦 {name} ({it['qty']}x)", callback_data=f"market_pick_stack_{it['base_id']}")])
            
    nav = []
    if page > 1: nav.append(InlineKeyboardButton("⬅️ Ant", callback_data=f"market_sell:{page-1}"))
    if end < total: nav.append(InlineKeyboardButton("Prox ➡️", callback_data=f"market_sell:{page+1}"))
    if nav: kb.append(nav)
    kb.append([InlineKeyboardButton("⬅️ Voltar ao Mercado", callback_data="market_adventurer")])
    
    await _safe_edit_or_send(q, context, update.effective_chat.id, f"➕ <b>Vender Item</b> (Página {page})", InlineKeyboardMarkup(kb))
    
async def market_pick_unique(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.data.replace("market_pick_unique_", "")
    user_id = q.from_user.id
    
    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {}) or {}
    if uid not in inv:
        await q.answer("Item não encontrado.", show_alert=True); return
    
    inst = inv[uid]
    if inst.get("base_id") in PREMIUM_BLOCK_LIST:
        await q.answer(PREMIUM_BLOCK_MSG, show_alert=True, parse_mode="HTML"); return

    del inv[uid]
    pdata["inventory"] = inv
    await player_manager.save_player_data(user_id, pdata)
    
    context.user_data["market_pending"] = {"type": "unique", "uid": uid, "item": inst}
    context.user_data["market_price"] = 50
    await _show_price_spinner(q, context, update.effective_chat.id, "Defina o <b>preço</b> deste item:")

async def market_pick_stack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    base_id = q.data.replace("market_pick_stack_", "")
    user_id = q.from_user.id
    
    if base_id in PREMIUM_BLOCK_LIST:
        await q.answer(PREMIUM_BLOCK_MSG, show_alert=True, parse_mode="HTML"); return

    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {}) or {}
    qty = int(inv.get(base_id, 0))
    if qty <= 0:
        await q.answer("Quantidade insuficiente.", show_alert=True); return
        
    context.user_data["market_pending"] = {"type": "stack", "base_id": base_id, "qty_have": qty, "qty": 1}
    await _show_pack_qty_spinner(q, context, update.effective_chat.id)

async def _show_pack_qty_spinner(q, context, chat_id):
    pending = context.user_data.get("market_pending")
    cur = pending["qty"]
    max_val = pending["qty_have"]
    item_name = _item_label_from_base(pending["base_id"])
    
    # MUDANÇA AQUI: Usa a função de renderização centralizada
    kb = market_utils.render_spinner_kb(
        value=cur,
        prefix_inc="mkt_pack_inc_", 
        prefix_dec="mkt_pack_dec_", 
        label="Itens/Lote", 
        confirm_cb="mkt_pack_confirm",
        allow_large_steps=False # Não precisamos de passos de 1k/5k para quantidade de lote
    )    
    await _safe_edit_or_send(q, context, chat_id, f"Item: <b>{item_name}</b> (Total: {max_val})\n\nDefina o tamanho do lote:", kb)

async def market_pack_qty_spin(update, context):
    q = update.callback_query; await q.answer()
    pending = context.user_data.get("market_pending")
    if not pending: await market_cancel_new(update, context); return
    
    # MUDANÇA AQUI: Usa a função de cálculo centralizada
    cur = market_utils.calculate_spin_value(
        current_value=pending["qty"],
        action_data=q.data,
        prefix_inc="mkt_pack_inc_",
        prefix_dec="mkt_pack_dec_",
        min_value=1,
        max_value=pending["qty_have"]
    )
    
    pending["qty"] = cur
    context.user_data["market_pending"] = pending
    await _show_pack_qty_spinner(q, context, update.effective_chat.id)

async def market_pack_qty_confirm(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["market_lote_qty"] = 1
    await _show_lote_qty_spinner(q, context, update.effective_chat.id)

async def _show_lote_qty_spinner(q, context, chat_id):
    pending = context.user_data.get("market_pending")
    pack_size = pending["qty"]
    max_lotes = max(1, pending["qty_have"] // pack_size)
    context.user_data["market_lote_max"] = max_lotes
    cur_lotes = min(context.user_data.get("market_lote_qty", 1), max_lotes)
    context.user_data["market_lote_qty"] = cur_lotes
    kb = market_utils.render_spinner_kb(
        value=cur_lotes, 
        prefix_inc="mkt_lote_inc_", 
        prefix_dec="mkt_lote_dec_", 
        label="Qtd Lotes", 
        confirm_cb="mkt_lote_confirm",
        allow_large_steps=False # Não precisamos de passos de 1k/5k para quantidade de lote
    )
    await _safe_edit_or_send(q, context, chat_id, f"Tamanho do Lote: {pack_size}\n\nDefina quantos lotes vender:", kb)

async def market_lote_qty_spin(update, context):
    q = update.callback_query; await q.answer()
    max_lotes = context.user_data.get("market_lote_max", 1)
    
    # MUDANÇA AQUI: Usa a função de cálculo centralizada
    cur = market_utils.calculate_spin_value(
        current_value=context.user_data.get("market_lote_qty", 1),
        action_data=q.data,
        prefix_inc="mkt_lote_inc_",
        prefix_dec="mkt_lote_dec_",
        min_value=1,
        max_value=max_lotes
    )

    context.user_data["market_lote_qty"] = cur
    await _show_lote_qty_spinner(q, context, update.effective_chat.id)

async def market_lote_qty_confirm(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["market_price"] = 10
    await _show_price_spinner(q, context, update.effective_chat.id)

async def _show_price_spinner(q, context, chat_id, text="Defina o preço:"):
    price = context.user_data.get("market_price", 10)
    kb = market_utils.render_spinner_kb(
        value=price, 
        prefix_inc="mktp_inc_", 
        prefix_dec="mktp_dec_", 
        label="Preço", 
        confirm_cb="mktp_confirm",
        currency_emoji="🪙",
        allow_large_steps=True
    )
    await _safe_edit_or_send(q, context, chat_id, f"{text} <b>{price} 🪙</b>", kb)

async def market_price_spin(update, context):
    q = update.callback_query; await q.answer()
    
    # MUDANÇA AQUI: Usa a função de cálculo centralizada
    cur = market_utils.calculate_spin_value(
        current_value=context.user_data.get("market_price", 10),
        action_data=q.data,
        prefix_inc="mktp_inc_",
        prefix_dec="mktp_dec_",
        min_value=market_utils.MIN_GOLD_PRICE # Usa a constante definida
    )
    
    context.user_data["market_price"] = cur
    await _show_price_spinner(q, context, update.effective_chat.id)

async def market_price_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    price = context.user_data.get("market_price", 1)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 Venda Pública (Todos)", callback_data="mkt_type_public")],
        [InlineKeyboardButton("🔒 Venda Privada (VIP)", callback_data="mkt_type_private")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="market_cancel_new")]
    ])
    await _safe_edit_or_send(q, context, update.effective_chat.id, f"💰 Preço: <b>{price} 🪙</b>\n\nComo deseja anunciar?", kb)

async def market_type_public(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data.pop("market_target_id", None)
    context.user_data.pop("market_target_name", None)
    price = context.user_data.get("market_price", 1)
    await market_finalize_listing(update, context, price)

async def market_type_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    pdata = await player_manager.get_player_data(user_id)
    if not player_manager.has_premium_plan(pdata):
        await q.answer("🔒 Recurso VIP!", show_alert=True); return
    
    await q.answer()
    context.user_data["awaiting_market_name"] = True
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="market_cancel_new")]])
    await _safe_edit_or_send(q, context, update.effective_chat.id, "🔒 <b>VENDA PRIVADA</b>\n\nDigite o <b>nome exato</b> do jogador no chat:", kb)

async def market_catch_input_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_market_name"): return 
    
    target_name = update.message.text.strip()
    user_id = update.effective_user.id
    
    found = await player_manager.find_player_by_name(target_name)
    if not found:
        await update.message.reply_text(f"❌ Jogador <b>{target_name}</b> não encontrado.\nTente novamente ou clique em Cancelar.", parse_mode="HTML")
        return

    target_id, target_pdata = found
    if target_id == user_id:
        await update.message.reply_text("❌ Não pode vender para si mesmo.")
        return

    context.user_data.pop("awaiting_market_name", None)
    context.user_data["market_target_id"] = target_id
    context.user_data["market_target_name"] = target_pdata.get("character_name", target_name)
    
    price = context.user_data.get("market_price", 1)
    await market_finalize_listing(update, context, price)

async def market_finalize_listing(update: Update, context: ContextTypes.DEFAULT_TYPE, price: int):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    pending = context.user_data.get("market_pending")
    if not pending:
        await context.bot.send_message(chat_id, "Erro: Nenhuma venda pendente.")
        return

    target_id = context.user_data.get("market_target_id")
    target_name = context.user_data.get("market_target_name")
    
    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {}) or {}

    try:
        if pending["type"] == "unique":
            item_payload = {"type": "unique", "uid": pending["uid"], "item": pending["item"]}
            listing = market_manager.create_listing(
                seller_id=user_id, item_payload=item_payload, unit_price=price, quantity=1,
                target_buyer_id=target_id, target_buyer_name=target_name
            )
        else: # Stack
            base_id = pending["base_id"]
            pack_size = pending["qty"]
            lote_qty = context.user_data.get("market_lote_qty", 1)
            total_remove = pack_size * lote_qty
            
            have = int(inv.get(base_id, 0))
            if have < total_remove:
                await context.bot.send_message(chat_id, "Erro crítico: Quantidade insuficiente ao finalizar.")
                return
                
            inv[base_id] = have - total_remove
            if inv[base_id] <= 0: del inv[base_id]
            pdata["inventory"] = inv
            await player_manager.save_player_data(user_id, pdata)
            
            item_payload = {"type": "stack", "base_id": base_id, "qty": pack_size}
            listing = market_manager.create_listing(
                seller_id=user_id, item_payload=item_payload, unit_price=price, quantity=lote_qty,
                target_buyer_id=target_id, target_buyer_name=target_name
            )

        context.user_data.pop("market_pending", None)
        context.user_data.pop("market_price", None)
        context.user_data.pop("market_lote_qty", None)
        context.user_data.pop("market_lote_max", None)
        context.user_data.pop("market_target_id", None)
        context.user_data.pop("market_target_name", None)

        msg = f"✅ <b>Venda Privada!</b>\nReservado para: <b>{target_name}</b>" if target_name else f"✅ Listagem #{listing['id']} criada!"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("👤 Minhas Listagens", callback_data="market_my")]])
        await context.bot.send_message(chat_id, msg, reply_markup=kb, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Erro CRÍTICO ao criar listing: {e}")
        await context.bot.send_message(chat_id, f"⚠️ Erro ao criar listagem: {e}\nSeus itens foram devolvidos.")
        
        # DEVOLUÇÃO
        pdata_rescue = await player_manager.get_player_data(user_id)
        if pending["type"] == "unique":
            inv = pdata_rescue.get("inventory", {})
            uid = pending["uid"]
            if uid in inv: uid = f"{uid}_rescue"
            inv[uid] = pending["item"]
            pdata_rescue["inventory"] = inv
        elif pending["type"] == "stack":
            lote_qty = context.user_data.get("market_lote_qty", 1)
            total = pending["qty"] * lote_qty
            player_manager.add_item_to_inventory(pdata_rescue, pending["base_id"], total)
            
        await player_manager.save_player_data(user_id, pdata_rescue)

async def market_cancel_new(update, context):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id 
    
    pending = context.user_data.pop("market_pending", None)
    if pending and pending.get("type") == "unique":
        pdata = await player_manager.get_player_data(user_id)
        inv = pdata.get("inventory", {}) or {}
        inv[pending["uid"]] = pending["item"]
        pdata["inventory"] = inv
        await player_manager.save_player_data(user_id, pdata)

    context.user_data.pop("market_price", None)
    context.user_data.pop("awaiting_market_name", None)
    context.user_data.pop("market_lote_qty", None)
    context.user_data.pop("market_lote_max", None)
    
    try: await q.delete_message()
    except Exception: pass
        
    await context.bot.send_message(chat_id=chat_id, text="❌ Operação cancelada.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao Mercado", callback_data="market_adventurer")]]))

# ==============================
#  COMPRA (CORREÇÃO DE PAGAMENTO)
# ==============================
# handlers/market_handler.py (Substituir a função market_buy)
async def market_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try: await q.answer()
    except: pass

    buyer_id = q.from_user.id
    chat_id = update.effective_chat.id
    
    try:
        lid = int(q.data.replace("market_buy_", ""))
    except ValueError:
        return

    # 1. RECUPERA A LISTAGEM ANTES DE TUDO
    listing = market_manager.get_listing(lid)
    if not listing:
        await q.answer("Este item já foi vendido ou removido!", show_alert=True)
        # Tenta atualizar a mensagem para remover o botão antigo
        await _safe_edit_or_send(q, context, chat_id, "❌ Item indisponível.", 
             InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_list")]]))
        return

    seller_id = int(listing.get("seller_id", 0))
    price = int(listing.get("price") or listing.get("unit_price", 0))
    qty_listing = int(listing.get("quantity", 1)) 
    
    cost = price 
    buyer = await player_manager.get_player_data(buyer_id)
    buyer_balance = int(buyer.get("gold", 0)) 

    if buyer_balance < cost:
        await q.answer(f"Ouro insuficiente! Você precisa de {cost}.", show_alert=True)
        return

    # Bloqueio VIP 
    if not player_manager.has_premium_plan(buyer):
        await q.answer("🔒 Apenas VIPs podem comprar no mercado.", show_alert=True)
        return

    # --- DEFINA A QUANTIDADE DA COMPRA AQUI ---
    amount_to_buy = 1 

    try:
        # 3. EXECUTA A TRANSAÇÃO NO GERENCIADOR
        updated_listing, _ = market_manager.purchase_listing(
            buyer_id=buyer_id, listing_id=lid, quantity=amount_to_buy
        )
        
        # 4. PROCESSA O ITEM (Adiciona ao Comprador)
        item_data = listing.get("item", {}) 
        item_type = item_data.get("type")
        item_name_display = "Item"

        if item_type == "stack":
            base_id = item_data.get("base_id")
            
            # --- CORREÇÃO AQUI ---
            # Antes estava: total_qty = qty_per_pack * qty_listing (ERRADO: multiplicava pelo estoque total)
            
            qty_per_pack = int(item_data.get("qty", 1))
            total_qty = qty_per_pack * amount_to_buy  # <--- CORRETO: Multiplica pelo que foi comprado (1)
            
            # ADICIONA AO INVENTÁRIO
            inventory.add_item_to_inventory(buyer, base_id, total_qty)
            name = _item_label_from_base(base_id)
            
            # Ajuste visual da mensagem
            item_name_display = f"{name} x{total_qty}"
            if amount_to_buy > 1:
                item_name_display += f" ({amount_to_buy} lotes)"

        elif item_type == "unique":
            real_item = item_data.get("item")
            if real_item:
                inventory.add_unique_item(buyer, real_item)
                item_name_display = real_item.get("display_name") or "Equipamento Raro"
            else:
                raise Exception("Dados do item único corrompidos.")

        # 5. PAGAMENTO E SALVAMENTO (ATÔMICO)
        
        # DEDUZ O OURO DO COMPRADOR E SALVA O ITEM NO INVENTÁRIO (OPERAÇÃO ÚNICA)
        buyer["gold"] = max(0, int(buyer.get("gold", 0)) - cost)
        await player_manager.save_player_data(buyer_id, buyer)

        # PAGA AO VENDEDOR (APENAS NOTIFICAÇÃO)
        if seller_id and seller_id != 0:
            # O pagamento já foi feito pelo market_manager. Apenas notifique.
            try:
                # Recarregamos apenas para obter o nome para o Log, e notificação, se necessário.
                # Não usamos para salvar, pois o market_manager já limpou seu cache.
                seller = await player_manager.get_player_data(seller_id)
                
                await context.bot.send_message(
                    seller_id, 
                    f"💰 <b>Venda realizada!</b>\nSeu item <b>{item_name_display}</b> foi vendido por {cost} moedas.",
                    parse_mode="HTML"
                )
            except Exception: pass

        # 6. FEEDBACK
        await _safe_edit_or_send(q, context, chat_id, 
            f"✅ <b>Compra realizada com sucesso!</b>\n\n"
            f"📦 <b>Recebido:</b> {item_name_display}\n"
            f"💰 <b>Pago:</b> {cost} 🪙",
            InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_list")]])
        )

        # LOG NO GRUPO
        try:
            buyer_name = buyer.get("character_name") or q.from_user.first_name
            seller_name = "Desconhecido"
            if seller_id and seller_id != 0:
                # Recarrega o vendedor para o nome (se não falhou na etapa 5)
                # Reutilizamos a variável 'seller' se ela foi carregada na notificação acima.
                if 'seller' not in locals():
                     seller = await player_manager.get_player_data(seller_id)
                
                seller_name = seller.get("character_name", f"ID: {seller_id}")
        
            log_text = (
                f"💸 <b>MERCADO (OURO)</b>\n\n"
                f"👤 <b>Comprador:</b> {buyer_name}\n"
                f"📦 <b>Item:</b> {item_name_display}\n"
                f"💰 <b>Valor:</b> {cost} 🪙\n"
                f"🤝 <b>Vendedor:</b> {seller_name}\n"
                f"🔗 <b>Listagem ID:</b> {lid}"
            )
        
            await context.bot.send_message(chat_id=LOG_GROUP_ID, message_thread_id=LOG_TOPIC_ID, text=log_text, parse_mode="HTML")
        except Exception as e_log:
            logger.warning(f"Log error: {e_log}")

    except Exception as e:
        logger.error(f"Erro CRÍTICO na compra {lid}: {e}", exc_info=True)
        await q.answer("Ocorreu um erro ao processar a compra.", show_alert=True)
        
async def market_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    lid = int(q.data.replace("market_cancel_", ""))
    user_id = q.from_user.id
    
    try:
        listing = market_manager.get_listing(lid)
        if not listing or int(listing["seller_id"]) != user_id:
            await q.answer("Erro ao cancelar.", show_alert=True); return
            
        market_manager.delete_listing(lid) 
        
        pdata = await player_manager.get_player_data(user_id)
        it = listing["item"]
        if it["type"] == "stack":
            player_manager.add_item_to_inventory(pdata, it["base_id"], int(it["qty"]) * int(listing["quantity"]))
        else:
            inv = pdata.get("inventory", {})
            inv[it["uid"]] = it["item"]
            pdata["inventory"] = inv
        await player_manager.save_player_data(user_id, pdata)
        
        await _safe_edit_or_send(q, context, update.effective_chat.id, "✅ Anúncio cancelado e item devolvido.", 
                                 InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_my")]]))
    except Exception as e:
        logger.error(f"Erro cancel: {e}")
        await q.answer("Erro ao cancelar.", show_alert=True)

# ==============================
#  EXPORTS DE HANDLERS
# ==============================
market_open_handler = CallbackQueryHandler(market_open, pattern=r'^market$')
market_adventurer_handler = CallbackQueryHandler(market_adventurer, pattern=r'^market_adventurer$')
# Permite "market_list" (página 1) ou "market_list:2" (página específica)
market_list_handler = CallbackQueryHandler(market_list, pattern=r'^market_list(:(\d+))?$')
market_my_handler = CallbackQueryHandler(market_my, pattern=r'^market_my$')
market_sell_handler = CallbackQueryHandler(market_sell, pattern=r'^market_sell(:(\d+))?$')
market_buy_handler = CallbackQueryHandler(market_buy, pattern=r'^market_buy_\d+$')
market_cancel_handler = CallbackQueryHandler(market_cancel, pattern=r'^market_cancel_\d+$')
market_pick_unique_handler = CallbackQueryHandler(market_pick_unique, pattern=r'^market_pick_unique_')
market_pick_stack_handler = CallbackQueryHandler(market_pick_stack, pattern=r'^market_pick_stack_')

market_pack_qty_spin_handler = CallbackQueryHandler(market_pack_qty_spin, pattern=r'^mkt_pack_(inc|dec)_[0-9]+$')
market_pack_qty_confirm_handler = CallbackQueryHandler(market_pack_qty_confirm, pattern=r'^mkt_pack_confirm$')
market_lote_qty_spin_handler = CallbackQueryHandler(market_lote_qty_spin, pattern=r'^mkt_lote_(inc|dec)_[0-9]+$')
market_lote_qty_confirm_handler = CallbackQueryHandler(market_lote_qty_confirm, pattern=r'^mkt_lote_confirm$')
market_price_spin_handler = CallbackQueryHandler(market_price_spin, pattern=r'^mktp_(inc|dec)_[0-9]+$')
market_price_confirm_handler = CallbackQueryHandler(market_price_confirm, pattern=r'^mktp_confirm$')
market_cancel_new_handler = CallbackQueryHandler(market_cancel_new, pattern=r'^market_cancel_new$')
market_catch_input_text_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, market_catch_input_text)
