# handlers/gem_market_handler.py
# (VERSÃO 4.2 - COM LOG DE VENDAS NO GRUPO)

import logging
import math
import html
from typing import List, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

# --- Nossos Módulos ---
from modules import player_manager, game_data, file_ids
from modules import gem_market_manager # O "Backend"
from modules.game_data.skins import SKIN_CATALOG
from modules.game_data import skills as skills_data
from modules import market_utils
try:
    from modules import display_utils
except ImportError:
    # Fallback caso o arquivo falhe, para o bot não parar
    display_utils = None
logger = logging.getLogger(__name__)

# ==============================
#  CONFIGURAÇÃO DE LOGS (Adicionado)
# ==============================
LOG_GROUP_ID = -1002881364171
LOG_TOPIC_ID = 24475

# ==============================
#  LISTAS DE ITENS VENDÁVEIS
# ==============================

EVOLUTION_ITEMS: set[str] = {
    "emblema_guerreiro", "essencia_guardia", "essencia_furia", "selo_sagrado", "essencia_luz",
    "emblema_berserker", "totem_ancestral",
    "emblema_cacador", "essencia_precisao", "marca_predador", "essencia_fera",
    "emblema_monge", "reliquia_mistica", "essencia_ki",
    "emblema_mago", "essencia_arcana", "essencia_elemental", "grimorio_arcano",
    "emblema_bardo", "essencia_harmonia", "essencia_encanto", "batuta_maestria",
    "emblema_assassino", "essencia_sombra", "essencia_letal", "manto_eterno",
    "emblema_samurai", "essencia_corte", "essencia_disciplina", "lamina_sagrada",
}
SKILL_BOOK_ITEMS: set[str] = {
    "tomo_passive_bulwark", 
    "tomo_active_whirlwind", 
    "tomo_active_holy_blessing", 
    "tomo_passive_unstoppable",
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
}
SKIN_BOX_ITEMS: set[str] = {
    'caixa_guerreiro_armadura_negra', 
    'guerreiro_armadura_negra', 
    'caixa_guerreiro_placas_douradas',
    'guerreiro_placas_douradas',
    'caixa_mago_traje_arcano', 
    'mago_traje_arcano', 
    'caixa_assassino_manto_espectral', 
    'assassino_manto_espectral'
    'caixa_cacador_patrulheiro_elfico',
    'cacador_patrulheiro_elfico',
    'caixa_berserker_pele_urso', 
    'berserker_pele_urso', 
    'caixa_monge_quimono_dragao', 
    'monge_quimono_dragao',
    'caixa_monge_aspecto_asura'
    'monge_aspecto_asura' 
    'caixa_bardo_traje_maestro',
    'bardo_traje_maestro',
    'caixa_samurai_armadura_shogun',
    'samurai_armadura_shogun', 
    'caixa_samurai_armadura_demoniaca', 
    'samurai_armadura_demoniaca',
    'caixa_samurai_encarnacao_sangrenta',
    'samurai_encarnacao_sangrenta',
    'caixa_samurai_guardiao_celestial',
    'samurai_guardiao_celestial', 
    'caixa_samurai_chama_aniquiladora',
    'samurai_chama_aniquiladora', 
}
EVO_ITEMS_BY_CLASS_MAP = {
    "guerreiro": {"emblema_guerreiro", "essencia_guardia", "essencia_furia", "selo_sagrado", "essencia_luz"},
    "berserker": {"emblema_berserker", "totem_ancestral"},
    "cacador":   {"emblema_cacador", "essencia_precisao", "marca_predador", "essencia_fera"},
    "monge":     {"emblema_monge", "reliquia_mistica", "essencia_ki"},
    "mago":      {"emblema_mago", "essencia_arcana", "essencia_elemental", "grimorio_arcano"},
    "bardo":     {"emblema_bardo", "essencia_harmonia", "essencia_encanto", "batuta_maestria"},
    "assassino": {"emblema_assassino", "essencia_sombra", "essencia_letal", "manto_eterno"},
    "samurai":   {"emblema_samurai", "essencia_corte", "essencia_disciplina", "lamina_sagrada"},
}
CLASSES_MAP = {
    "guerreiro": "⚔️ Guerreiro",
    "mago": "✨ Mago",
    "berserker": "🪓 Berserker",
    "cacador": "🏹 Caçador",
    "assassino": "🗡️ Assassino",
    "bardo": "🎵 Bardo",
    "monge": "🧘 Monge",
    "samurai": "🥷 Samurai",
}

# ==============================
#  Utils (Helpers)
# ==============================

def _get_item_info(base_id: str) -> dict:
    try:
        info = game_data.get_item_info(base_id)
        if info: return dict(info)
    except Exception: pass
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

def _item_label(base_id: str) -> str:
    info = _get_item_info(base_id)
    if base_id in SKILL_BOOK_ITEMS: emoji = "📚"
    elif base_id in SKIN_BOX_ITEMS: emoji = "🎨"
    elif base_id in EVOLUTION_ITEMS: emoji = "✨"
    else: emoji = info.get("emoji", "💎")
    name = info.get("display_name", base_id)
    return f"{emoji} {name}"

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except Exception as e:
        if "message is not modified" in str(e).lower():
            return
        pass
    
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except Exception as e:
        if "message is not modified" in str(e).lower():
            return
        pass
    
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

async def _send_with_media(chat_id: int, context: ContextTypes.DEFAULT_TYPE, caption: str, kb: InlineKeyboardMarkup, media_keys: List[str]):
    for key in media_keys:
        fd = file_ids.get_file_data(key)
        if fd and fd.get("id"):
            fid, ftype = fd["id"], fd.get("type")
            try:
                if ftype == "video":
                    await context.bot.send_video(chat_id=chat_id, video=fid, caption=caption, reply_markup=kb, parse_mode="HTML")
                else:
                    await context.bot.send_photo(chat_id=chat_id, photo=fid, caption=caption, reply_markup=kb, parse_mode="HTML")
                return
            except Exception:
                continue
    await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=kb, parse_mode="HTML")

# ==============================
#  Menu Principal (Ponto de Entrada)
# ==============================

async def gem_market_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id

    text = (
        "🏛️ <b>𝐂𝐨𝐦𝐞́𝐫𝐜𝐢𝐨 𝐝𝐞 𝐑𝐞𝐥𝐢́𝐪𝐮𝐢𝐚𝐬 ✨</b>\n\n"
        "Bem-vindo! Aqui podes negociar itens raros (Evolução, Skills, Skins) "
        "com outros aventureiros usando <b>Diamantes</b> (💎)."
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Ver Listagens (Comprar)", callback_data="gem_list_cats")],
        [InlineKeyboardButton("➕ Vender Item", callback_data="gem_sell_cats")],
        [InlineKeyboardButton("👤 Minhas Listagens", callback_data="gem_market_my")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market")],
    ])

    keys = ["mercado_gemas", "img_mercado_gemas", "gem_market", "gem_shop", "casa_leiloes"]
    try: await q.delete_message()
    except Exception: pass
    await _send_with_media(chat_id, context, text, kb, keys)

# ==============================
#  Seleção de Classe (Genérico)
# ==============================

def _build_class_picker_keyboard(callback_prefix: str, back_callback: str) -> InlineKeyboardMarkup:
    """Cria o teclado de 8 classes para compra ou venda."""
    kb = []
    row = []
    for class_key, class_label in CLASSES_MAP.items():
        row.append(InlineKeyboardButton(class_label, callback_data=f"{callback_prefix}:{class_key}:1"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
        
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data=back_callback)])
    return InlineKeyboardMarkup(kb)

# ==============================
#  Fluxo de Venda (Sell Flow)
# ==============================

async def show_sell_category_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra as 3 categorias de itens para VENDER."""
    q = update.callback_query
    await q.answer()
    
    text = "➕ <b>Vender Item</b>\n\nQue tipo de item premium desejas vender?"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Itens de Evolução", callback_data="gem_sell_filter:evo")],
        [InlineKeyboardButton("📚 Tomos de Skill", callback_data="gem_sell_filter:skill")],
        [InlineKeyboardButton("🎨 Caixas de Skin", callback_data="gem_sell_filter:skin")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")],
    ])
    await _safe_edit_or_send(q, context, q.message.chat_id, text, kb)

async def show_sell_class_picker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o seletor de classe para VENDER evo, skins ou skills."""
    q = update.callback_query
    await q.answer()
    
    try:
        item_type = q.data.split(":")[1] # 'evo', 'skill' ou 'skin'
    except IndexError:
        return 

    if item_type == "skill":
        text = "📚 <b>Vender Tomos de Skill</b>\n\nDe qual classe é a skill que queres vender?"
        callback_prefix = "gem_sell_class:skill"
    elif item_type == "skin":
        text = "🎨 <b>Vender Caixas de Skin</b>\n\nDe qual classe é a skin que queres vender?"
        callback_prefix = "gem_sell_class:skin"
    else: # evo
        text = "✨ <b>Vender Itens de Evolução</b>\n\nPara qual classe é o item que queres vender?"
        callback_prefix = "gem_sell_class:evo"
        
    kb = _build_class_picker_keyboard(callback_prefix, back_callback="gem_sell_cats")
    await _safe_edit_or_send(q, context, q.message.chat_id, text, kb)

async def show_sell_items_filtered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Pega categoria e página da URL (ex: gem_sell_class:skill:mago:1)
    try:
        _, category, class_filter, page_str = query.data.split(":")
        page = int(page_str)
    except:
        category = "skin"
        class_filter = "todos"
        page = 1

    user_id = query.from_user.id
    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {})

    # ====================================================
    # LÓGICA DE FILTRO CORRIGIDA (DINÂMICA)
    # ====================================================
    filtered_items = []

    for item_id, item_data in inv.items():
        # Normaliza ID e Qtd
        base_id = item_id 
        qty = 0
        if isinstance(item_data, dict):
            qty = item_data.get("quantity", 0)
        else:
            qty = int(item_data)

        if qty <= 0: continue

        # --- REGRAS DE CATEGORIA ---
        match = False
        
        # 1. SKINS (Começam com 'skin_' ou 'caixa_skin_')
        if category == "skin":
            if "skin_" in base_id or "caixa_" in base_id:
                match = True
                
        # 2. SKILLS (Começam com 'tomo_' ou 'livro_' ou 'pergaminho_')
        elif category == "skill":
            if base_id.startswith("tomo_") or base_id.startswith("livro_") or base_id.startswith("scroll_"):
                match = True
                # Proteção: Ignora tomos bugados se houver
                if base_id.startswith("tomo_tomo_"): match = False

        # 3. EVOLUÇÃO (Itens da lista EVOLUTION_ITEMS ou genéricos de evo)
        elif category == "evo":
            # Verifica se está na lista fixa OU se tem nome de item de evo comum
            if base_id in EVOLUTION_ITEMS or "essencia_" in base_id or "emblema_" in base_id or "cristal_" in base_id:
                match = True

        if match:
            # Filtro de Classe (Opcional, se você quiser filtrar skills por classe depois)
            # Por enquanto, vamos mostrar tudo para garantir que apareça
            filtered_items.append({"base_id": base_id, "qty": qty})

    # ====================================================
    # PAGINAÇÃO E EXIBIÇÃO
    # ====================================================
    ITEMS_PER_PAGE = 5
    total_items = len(filtered_items)
    total_pages = math.ceil(total_items / ITEMS_PER_PAGE)
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1

    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_items = filtered_items[start:end]

    # Monta a mensagem
    cat_names = {"skin": "🎨 Skins", "skill": "📜 Habilidades", "evo": "✨ Evolução"}
    cat_title = cat_names.get(category, category.title())
    
    text = f"💎 <b>Vender: {cat_title}</b> (Pág {page}/{total_pages})\n\nSelecione um item para vender por Gemas:"

    kb = []
    
    if not page_items:
        text += "\n\n<i>Nenhum item desta categoria encontrado no inventário.</i>"
    else:
        for item in page_items:
            bid = item["base_id"]
            q_val = item["qty"]
            # Nome Bonito
            dname = bid.replace("_", " ").title()
            
            # Tenta pegar nome real se tiver display_utils
            try: 
                info = display_utils._item_info(bid)
                if info and "display_name" in info: dname = info["display_name"]
            except: pass

            btn_text = f"{dname} (x{q_val})"
            kb.append([InlineKeyboardButton(btn_text, callback_data=f"gem_sell_item_{bid}")])

    # Navegação
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"gem_sell_class:{category}:{class_filter}:{page-1}"))
    
    nav.append(InlineKeyboardButton("🔙 Categorias", callback_data="gem_sell_menu"))
    
    if page < total_pages:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"gem_sell_class:{category}:{class_filter}:{page+1}"))
    
    kb.append(nav)

    try:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    except:
        await context.bot.send_message(query.message.chat_id, text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

# ==============================
#  Fluxo de Compra (Buy Flow)
# ==============================

async def show_buy_category_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    text = "📦 <b>Ver Listagens</b>\n\nQue tipo de item premium procuras?"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Itens de Evolução", callback_data="gem_list_filter:evo")],
        [InlineKeyboardButton("📚 Tomos de Skill", callback_data="gem_list_filter:skill")],
        [InlineKeyboardButton("🎨 Caixas de Skin", callback_data="gem_list_filter:skin")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")],
    ])
    await _safe_edit_or_send(q, context, q.message.chat_id, text, kb)

async def show_buy_class_picker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    try:
        item_type = q.data.split(":")[1] # 'evo', 'skill' ou 'skin'
    except IndexError:
        return

    if item_type == "skill":
        text = "📚 <b>Comprar Tomos de Skill</b>\n\nProcurando skills para qual classe?"
        callback_prefix = "gem_list_class:skill"
    elif item_type == "skin":
        text = "🎨 <b>Comprar Caixas de Skin</b>\n\nProcurando skins para qual classe?"
        callback_prefix = "gem_list_class:skin"
    else: # evo
        text = "✨ <b>Comprar Itens de Evolução</b>\n\nProcurando itens para qual classe?"
        callback_prefix = "gem_list_class:evo"
        
    kb = _build_class_picker_keyboard(callback_prefix, back_callback="gem_list_cats")
    await _safe_edit_or_send(q, context, q.message.chat_id, text, kb)

async def show_buy_items_filtered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra as listagens de Compra, filtradas por categoria E classe."""
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = q.message.chat_id

    # ⚠️ CORREÇÃO CRÍTICA: Limpa o cache do jogador antes de carregar as listagens.
    # Isso resolve problemas onde a listagem recém-criada não é visível devido a dados de sessão antigos.
    await player_manager.clear_player_cache(user_id) 

    parts = q.data.split(":")
    
    try:
        item_type_filter = parts[1] # evo, skill, skin
        class_key_filter = parts[2] # guerreiro, mago...
        page = int(parts[3])
    except (IndexError, ValueError):
        await q.answer("Erro de callback.", show_alert=True); return

    pdata = await player_manager.get_player_data(user_id)
    gems = player_manager.get_gems(pdata)

    # Assume list_active() está no gem_market_manager, conforme o restante do arquivo
    all_listings = gem_market_manager.list_active(page=1, page_size=500)
    
    # Adicionar o filtro defensivo após a migração para MongoDB
    if all_listings is None:
        all_listings = []
        
    filtered_listings = []
    
    # ⚠️ NORMALIZAÇÃO CRÍTICA: Garante que a chave do filtro esteja limpa
    normalized_filter_class = class_key_filter.strip().lower()

    for l in all_listings:
        item_payload = l.get("item", {})
        # item_type = item_payload.get("type") # IGNORADO
        base_id = item_payload.get("base_id")

        if not base_id:
            continue
            
        item_class_ok = False

        # --- FILTRO 1: ITENS DE EVOLUÇÃO (EVO) ---
        # Mantém a verificação de tipo "evo_item", pois é a mais limpa.
        if item_type_filter == "evo" and item_payload.get("type") == "evo_item": 
            if base_id in EVO_ITEMS_BY_CLASS_MAP.get(normalized_filter_class, set()):
                item_class_ok = True
        
        # --- FILTRO 2: SKILLS (TOMOS) ---
        # Item é elegível se tiver prefixo tomo_ E o skill_id permitir a classe_key
        elif item_type_filter == "skill" and base_id.startswith("tomo_"):
            skill_id = base_id.replace("tomo_", "")
            # Assume skills_data está importado (modules.game_data.skills)
            allowed = skills_data.SKILL_DATA.get(skill_id, {}).get("allowed_classes", [])
            if normalized_filter_class in allowed: 
                item_class_ok = True
        
        
        # --- FILTRO 3: SKINS (CAIXAS) ---
        elif item_type_filter == "skin":
            
            item_type_on_listing = item_payload.get("type")
            # Usa "item_stack" como fallback para listagens antigas que não definiram o tipo
            if item_type_on_listing not in ("skin", "item_stack"):
                continue

            # Tenta encontrar a classe do item com ou sem o prefixo 'caixa_'
            skin_id_clean = base_id.replace("caixa_", "")
            
            # Tenta encontrar a classe no catálogo com o ID limpo
            allowed_class = SKIN_CATALOG.get(skin_id_clean, {}).get("class")
            
            # Compara a classe limpa do filtro com a classe do catálogo
            if allowed_class and normalized_filter_class == allowed_class: 
                item_class_ok = True
        
        if item_class_ok:
            filtered_listings.append(l)

    ITEMS_PER_PAGE = 10
    start_index = (page - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    items_on_page = filtered_listings[start_index:end_index]
    total_pages = max(1, math.ceil(len(filtered_listings) / ITEMS_PER_PAGE))
    page = min(page, total_pages)

    title = f"{CLASSES_MAP.get(normalized_filter_class, normalized_filter_class).split(' ')[1]}"
    lines = [f"🏛️ <b>Listagens: {title}</b> (Pág. {page}/{total_pages})\nVocê tem <b>💎 {gems}</b>\n"]
    kb_rows = []

    if not items_on_page and page == 1:
        lines.append(f"<i>Nenhuma listagem de '{item_type_filter}' encontrada para esta classe.</i>")
    
    for l in items_on_page:
        lines.append(_render_listing_line(l))
        if int(l.get("seller_id", 0)) != user_id:
            back_cb_data = f":{item_type_filter}:{class_key_filter}:{page}"
            kb_rows.append([InlineKeyboardButton(f"Comprar [#{l['id']}]", callback_data=f"gem_buy_confirm{back_cb_data}:{l['id']}")])

    nav_buttons = []
    back_cb = f"gem_list_filter:{item_type_filter}"
    page_cb_base = f"gem_list_class:{item_type_filter}:{class_key_filter}"

    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"{page_cb_base}:{page - 1}"))
    
    nav_buttons.append(InlineKeyboardButton("⬅️ Voltar", callback_data=back_cb))
    
    if end_index < len(filtered_listings):
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"{page_cb_base}:{page + 1}"))
        
    kb_rows.append(nav_buttons)
    await _safe_edit_or_send(q, context, chat_id, "\n".join(lines), InlineKeyboardMarkup(kb_rows))

# ==============================
#  SPINNERS E FUNÇÕES DE FINALIZAÇÃO
# ==============================


async def gem_market_price_spin(update, context):
    q = update.callback_query; await q.answer()
    chat_id = update.effective_chat.id
    
    # MUDANÇA AQUI: Usa a função de cálculo centralizada
    cur = market_utils.calculate_spin_value(
        current_value=context.user_data.get("gem_market_price", market_utils.MIN_GEM_PRICE),
        action_data=q.data,
        prefix_inc="gem_p_inc_",
        prefix_dec="gem_p_dec_",
        min_value=market_utils.MIN_GEM_PRICE # Usa a constante de Gemas
    )
    
    context.user_data["gem_market_price"] = cur
    
    pending = context.user_data.get("gem_market_pending")
    if not pending:
        await gem_market_cancel_new(update, context); return
        
    item_label = _item_label(pending["base_id"])
    pack_qty = int(pending.get("qty", 1))
    lote_qty = int(context.user_data.get("gem_market_lotes", 1))

    caption = (
        f"Item: <b>{item_label} ×{pack_qty}</b>\n"
        f"Lotes: <b>{lote_qty}</b>\n\n"
        f"Defina o <b>preço por lote</b> (Mínimo: 10 💎):"
    )
    kb = market_utils.render_spinner_kb(
        value=cur,
        prefix_inc="gem_p_inc_",
        prefix_dec="gem_p_dec_",
        label="Preço por lote",
        confirm_cb="gem_p_confirm",
        currency_emoji="💎",
        allow_large_steps=False # Não precisamos de passos grandes de 1k/5k para gemas
    )
    await _safe_edit_or_send(q, context, chat_id, f"{caption} <b>💎 {cur}</b>", kb)

async def gem_market_price_confirm(update, context):
    q = update.callback_query
    # AQUI: Se por algum milagre o valor for menor que 10, força subir para 10
    price = max(10, int(context.user_data.get("gem_market_price", 10)))
    
    # Validação visual (opcional, mas bom pra feedback)
    if price < 10:
        await q.answer("O preço mínimo é 10 Gemas!", show_alert=True)
        return

    await q.answer()
    await gem_market_finalize_listing(update, context, price)

async def _show_gem_lote_spinner(q, context, chat_id: int):
    pending = context.user_data.get("gem_market_pending")
    if not pending or pending.get("type") != "item_stack":
        await gem_market_cancel_new(q, context); return

    qty_have = int(pending.get("qty_have", 0))
    pack_qty = int(pending.get("qty", 1))
    
    max_lotes = max(1, qty_have // pack_qty)
    context.user_data["gem_market_lote_max"] = max_lotes
    
    current_lotes = max(1, int(context.user_data.get("gem_market_lotes", 1)))
    current_lotes = min(current_lotes, max_lotes)
    context.user_data["gem_market_lotes"] = current_lotes

    kb = market_utils.render_spinner_kb(
        value=current_lotes, 
        prefix_inc="gem_lote_inc_", 
        prefix_dec="gem_lote_dec_", 
        label=f"📦 {current_lotes} / {max_lotes} Lotes", # Ajusta o label para incluir a info Max/Cur
        confirm_cb="gem_lote_confirm",
        allow_large_steps=False
    )
    
    item_label = _item_label(pending["base_id"])
    caption = (
        f"Item: <b>{item_label} ×{pack_qty}</b> (Você tem {qty_have} no total)\n\n"
        f"Defina a <b>quantidade de lotes</b> que deseja vender:"
    )
    
    await _safe_edit_or_send(q, context, chat_id, caption, kb)

async def gem_market_lote_spin(update, context):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id

    # CORREÇÃO: Carregar o valor máximo de lotes (que foi definido em _show_gem_lote_spinner)
    max_qty = max(1, int(context.user_data.get("gem_market_lote_max", 1))) 

    cur = market_utils.calculate_spin_value(
        current_value=context.user_data.get("gem_market_lotes", 1),
        action_data=q.data,
        prefix_inc="gem_lote_inc_",
        prefix_dec="gem_lote_dec_",
        min_value=1,
        max_value=max_qty # Agora max_qty está definido
    )
    
    context.user_data["gem_market_lotes"] = cur
    await _show_gem_lote_spinner(q, context, chat_id)

async def gem_market_lote_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    
    # Inicializa o preço mínimo para 10 (constante em market_utils)
    context.user_data["gem_market_price"] = market_utils.MIN_GEM_PRICE 
    
    pending = context.user_data.get("gem_market_pending")
    item_label = _item_label(pending["base_id"])
    pack_qty = int(pending.get("qty", 1))
    lote_qty = int(context.user_data.get("gem_market_lotes", 1))

    caption_prefix = (
        f"Item: <b>{item_label} ×{pack_qty}</b>\n"
        f"Lotes: <b>{lote_qty}</b>\n\n"
        f"Defina o <b>preço por lote</b> (em Diamantes):"
    )
    
    price = context.user_data["gem_market_price"]
    
    # CORREÇÃO AQUI: Usa a função genérica de renderização
    kb = market_utils.render_spinner_kb(
        value=price, 
        prefix_inc="gem_p_inc_", 
        prefix_dec="gem_p_dec_", 
        label="Preço por lote", 
        confirm_cb="gem_p_confirm",
        currency_emoji="💎",
        allow_large_steps=False # Não permite passos de 1k/5k para gemas
    )
    
    await _safe_edit_or_send(q, context, chat_id, f"{caption_prefix} <b>💎 {price}</b>", kb)

async def _show_gem_pack_spinner(q, context, chat_id: int):
    pending = context.user_data.get("gem_market_pending")
    if not pending or pending.get("type") != "item_stack":
        await gem_market_cancel_new(q, context); return

    qty_have = int(pending.get("qty_have", 0))
    current_pack_qty = max(1, int(pending.get("qty", 1)))
    current_pack_qty = min(current_pack_qty, qty_have)
    
    pending["qty"] = current_pack_qty
    context.user_data["gem_market_pending"] = pending

    kb = market_utils.render_spinner_kb(
        value=current_pack_qty, 
        prefix_inc="gem_pack_inc_", 
        prefix_dec="gem_pack_dec_", 
        label=f"📦 {current_pack_qty} / {qty_have} Itens",
        confirm_cb="gem_pack_confirm",
        allow_large_steps=False
    )
    
    item_label = _item_label(pending["base_id"])
    caption = (
        f"Item: <b>{item_label}</b> (Você tem {qty_have} no total)\n\n"
        f"Defina quantos itens vão em <b>cada lote</b>:"
    )
    
    await _safe_edit_or_send(q, context, chat_id, caption, kb)

async def gem_market_pack_spin(update, context):
    q = update.callback_query; await q.answer()
    # CORREÇÃO: Define chat_id explicitamente
    chat_id = update.effective_chat.id 
    
    pending = context.user_data.get("gem_market_pending")
    if not pending: await gem_market_cancel_new(update, context); return
    
    max_qty = max(1, int(pending.get("qty_have", 1)))
    
    # MUDANÇA AQUI: Usa a função de cálculo centralizada
    cur = market_utils.calculate_spin_value(
        current_value=pending.get("qty", 1),
        action_data=q.data,
        prefix_inc="gem_pack_inc_",
        prefix_dec="gem_pack_dec_",
        min_value=1,
        max_value=max_qty
    )
        
    pending["qty"] = cur
    context.user_data["gem_market_pending"] = pending
    
    # CORREÇÃO: Agora chat_id está definido
    await _show_gem_pack_spinner(q, context, chat_id)

async def gem_market_pack_confirm(update, context):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    context.user_data["gem_market_lotes"] = 1
    await _show_gem_lote_spinner(q, context, chat_id)

async def gem_market_pick_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Jogador selecionou um item (Evo, Skill ou Skin) para vender."""
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id
    
    base_id = q.data.replace("gem_sell_item_", "")
    
    pdata = await player_manager.get_player_data(user_id)
    
    if not pdata:
        logger.warning(f"[GemMarket] Falha ao carregar pdata para {user_id} em gem_market_pick_item.")
        await q.answer("Erro: Não foi possível carregar os seus dados. Tente novamente.", show_alert=True)
        try:
            await gem_market_main(update, context) 
        except Exception:
            pass 
        return

    inv = pdata.get("inventory", {}) or {}
    qty_have = int(inv.get(base_id, 0))
    
    if qty_have <= 0:
        await q.answer("Você não tem mais esse item.", show_alert=True)
        try:
            await gem_market_main(update, context) 
        except Exception:
            pass
        return

    context.user_data["gem_market_pending"] = {
        "type": "item_stack", 
        "base_id": base_id, 
        "qty_have": qty_have,
        "qty": 1  
    }
    
    await _show_gem_pack_spinner(q, context, chat_id)

async def gem_market_cancel_new(update, context):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    
    context.user_data.pop("gem_market_pending", None)
    context.user_data.pop("gem_market_price", None)
    context.user_data.pop("gem_market_lotes", None)
    context.user_data.pop("gem_market_lote_max", None)
    
    await _safe_edit_or_send(q, context, chat_id, "Criação de listagem cancelada.", InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")]
    ]))

async def gem_market_finalize_listing(update: Update, context: ContextTypes.DEFAULT_TYPE, price_gems: int):
    q = update.callback_query
    user_id = q.from_user.id
    chat_id = q.message.chat_id

    pending = context.user_data.get("gem_market_pending")
    if not pending or pending.get("type") != "item_stack":
        await q.answer("Erro: Estado de venda inválido. Tente novamente.", show_alert=True)
        await gem_market_cancel_new(update, context)
        return
        
    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        await q.answer("Erro ao carregar seus dados.", show_alert=True)
        return

    # --- CORREÇÃO: Usamos o ID EXATO que está no inventário ---
    base_id_original = pending["base_id"]
    
    pack_qty = int(pending.get("qty", 1))
    lote_qty = max(1, int(context.user_data.get("gem_market_lotes", 1)))
    total_to_remove = pack_qty * lote_qty
    item_label = _item_label(base_id_original) 

    # Verifica se tem o item
    if not player_manager.has_item(pdata, base_id_original, total_to_remove):
        await q.answer(f"Você não tem {total_to_remove}x {item_label}.", show_alert=True)
        await gem_market_cancel_new(update, context)
        return

    # Remove do inventário
    player_manager.remove_item_from_inventory(pdata, base_id_original, total_to_remove)
    await player_manager.save_player_data(user_id, pdata)
    
    # --- DEFINIÇÃO DE TIPO (Apenas para Filtros Visuais) ---
    # NÃO alteramos o base_id_original. O ID salvo é o ID real.
    item_type_for_backend = "item_stack" 
    
    if base_id_original.startswith("caixa_"):
        item_type_for_backend = "skin"
    elif base_id_original.startswith("tomo_") and base_id_original in SKILL_BOOK_ITEMS:
        item_type_for_backend = "skill"
    elif base_id_original in EVOLUTION_ITEMS:
        item_type_for_backend = "evo_item"
    
    item_payload = {
        "type": item_type_for_backend, 
        "base_id": base_id_original, # SALVA O ID COMPLETO (Ex: tomo_fogo, caixa_skin)
        "qty": pack_qty
    }

    try:
        listing = gem_market_manager.create_listing(
            seller_id=user_id,
            item_payload=item_payload,
            unit_price=price_gems,
            quantity=lote_qty
        )
    except Exception as e:
        logger.error(f"[GemMarket] Falha ao criar listagem para {user_id}: {e}", exc_info=True)
        # Devolve o item em caso de erro
        player_manager.add_item_to_inventory(pdata, base_id_original, total_to_remove)
        await player_manager.save_player_data(user_id, pdata)
        
        await _safe_edit_or_send(q, context, chat_id, f"⚠️ Erro ao criar venda. Item devolvido.", InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")]
        ]))
        return
        
    context.user_data.pop("gem_market_pending", None)
    context.user_data.pop("gem_market_price", None)
    context.user_data.pop("gem_market_lotes", None)
    context.user_data.pop("gem_market_lote_max", None)
    
    text = f"✅ Listagem #{listing['id']} criada!\n\n{lote_qty}x lote(s) de {item_label} (x{pack_qty}) por 💎 {price_gems} cada."
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Minhas Listagens", callback_data="gem_market_my")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")]
    ])
    await _safe_edit_or_send(q, context, chat_id, text, kb)

def _render_listing_line(listing: dict) -> str:
    item = listing.get("item", {})
    price = listing.get("unit_price_gems", 0)
    lotes = listing.get("quantity", 1)
    lid = listing.get("id")
    
    base_id = item.get("base_id")
    pack_qty = item.get("qty", 1)
    label = _item_label(base_id) 
    
    return f"• {label} (x{pack_qty}) — <b>💎 {price}</b> (Lotes: {lotes}) [#{lid}]"

async def gem_market_buy_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    
    try:
        parts = q.data.split(":") 
        lid = int(parts[-1])
        filter_parts = ":".join(parts[1:-1]) 
        
        if filter_parts:
            back_cb = f"gem_list_class:{filter_parts}"
        else:
            back_cb = "gem_list_cats"
            
    except (IndexError, ValueError):
        await q.answer("ID ou callback inválido.", show_alert=True); return

    listing = gem_market_manager.get_listing(lid)
    if not listing or not listing.get("active"):
        await q.answer("Esta listagem não está mais disponível.", show_alert=True)
        await gem_market_main(update, context); return
        
    line = _render_listing_line(listing)
    price = listing.get("unit_price_gems", 0)
    
    text = f"Você confirma a compra de 1 lote deste item?\n\n{line}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ Sim, comprar por 💎 {price}", callback_data=f"gem_buy_execute_{lid}")],
        [InlineKeyboardButton("❌ Não, voltar", callback_data=back_cb)]
    ])
    await _safe_edit_or_send(q, context, chat_id, text, kb)

async def gem_market_buy_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("Processando compra...")
    
    chat_id = update.effective_chat.id 
    buyer_id = q.from_user.id
    
    try: lid = int(q.data.replace("gem_buy_execute_", ""))
    except: await q.answer("ID inválido.", show_alert=True); return
        
    # 1. Validações Básicas
    listing = gem_market_manager.get_listing(lid)
    if not listing or not listing.get("active"):
        await q.answer("Item já vendido ou removido!", show_alert=True)
        await gem_market_main(update, context); return
        
    seller_id = int(listing.get("seller_id", 0))
    if buyer_id == seller_id:
        await q.answer("Você não pode comprar de si mesmo.", show_alert=True); return

    buyer_pdata = await player_manager.get_player_data(buyer_id)
    seller_pdata = await player_manager.get_player_data(seller_id)
    
    if not buyer_pdata:
        await q.answer("Erro ao carregar seus dados.", show_alert=True); return

    total_cost = int(listing.get("unit_price_gems", 0)) 
    buyer_gems = int(buyer_pdata.get("gems", 0))
    if buyer_gems < total_cost:
        await q.answer(f"Gemas insuficientes! Você precisa de {total_cost} 💎.", show_alert=True); return

    # 2. Executa a Transação (Backend)
    try:
        buyer_pdata["gems"] = max(0, buyer_gems - total_cost)
        updated_listing, _ = await gem_market_manager.purchase_listing( 
            buyer_pdata=buyer_pdata, 
            seller_pdata=seller_pdata, 
            listing_id=lid,
            quantity=1
        )
    except Exception as e:
        error_msg = str(e)
        if "Falha na baixa" in error_msg or "Anúncio não ativo" in error_msg:
             error_msg = "⚠️ Estoque acabou ou item indisponível!"
        await q.answer(error_msg, show_alert=True); return

    # 3. Entrega o Item (CORRIGIDO: SEM INVENTAR PREFIXOS)
    item_payload = listing.get("item", {})
    
    # PEGA O ID DIRETO DO BANCO DE DADOS
    base_id_final = item_payload.get("base_id") 
    pack_qty = int(item_payload.get("qty", 1))
    
    if not base_id_final:
        # Fallback de emergência se for uma listagem muito antiga
        logger.error(f"[GemMarket] Listagem {lid} sem base_id!")
        await q.answer("Erro crítico no item. Contate suporte.", show_alert=True); return
    
    # Entrega exata
    player_manager.add_item_to_inventory(buyer_pdata, base_id_final, pack_qty) 
    
    # 4. Notificações e Salvamento
    item_label = _item_label(base_id_final)
    if seller_id and seller_pdata:
        try:
            await context.bot.send_message(seller_id, f"💎 <b>Venda Realizada!</b>\nVocê vendeu <b>{item_label}</b> por <b>{total_cost} Gemas</b>.", parse_mode="HTML")
        except: pass

    await player_manager.save_player_data(buyer_id, buyer_pdata)

    # Log
    try:
        buyer_name = buyer_pdata.get("character_name", "Desconhecido")
        seller_name = seller_pdata.get("character_name", "Vendedor") if seller_pdata else "Desconhecido"
        log_text = (f"💎 <b>CASA DE LEILÕES (VENDA)</b>\n👤 <b>Comprador:</b> {buyer_name}\n📦 <b>Item:</b> {item_label} x{pack_qty}\n💰 <b>Valor:</b> {total_cost} Gemas\n🤝 <b>Vendedor:</b> {seller_name}")
        await context.bot.send_message(chat_id=LOG_GROUP_ID, message_thread_id=LOG_TOPIC_ID, text=log_text, parse_mode="HTML")
    except: pass

    text = f"✅ Compra concluída! Recebeste <b>{item_label} (x{pack_qty})</b> por 💎 {total_cost}."
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="gem_list_cats")]])
    await _safe_edit_or_send(q, context, chat_id, text, kb)
    
async def gem_market_my(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id
    
    my_listings = gem_market_manager.list_by_seller(user_id) 

    if not my_listings:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")]])
        await _safe_edit_or_send(q, context, chat_id, "Você não tem listagens ativas na Casa de Leilões.", kb)
        return

    lines = ["👤 <b>Minhas Listagens (Gemas)</b>\n"]
    kb_rows = []
    for l in my_listings:
        lines.append(_render_listing_line(l))
        kb_rows.append([InlineKeyboardButton(f"Cancelar [#{l['id']}]", callback_data=f"gem_cancel_{l['id']}")])

    kb_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")])
    await _safe_edit_or_send(q, context, chat_id, "\n".join(lines), InlineKeyboardMarkup(kb_rows))

async def gem_market_cancel_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("A cancelar...")
    user_id = q.from_user.id
    chat_id = update.effective_chat.id
    
    try: lid = int(q.data.replace("gem_cancel_", ""))
    except: await q.answer("ID inválido.", show_alert=True); return

    try:
        # --- CORREÇÃO AQUI: Adicionado 'await' ---
        listing = await gem_market_manager.cancel_listing(seller_id=user_id, listing_id=lid)
    except Exception as e:
        # Se der erro (ex: já cancelado), avisa e volta
        await q.answer(f"Erro: {e}", show_alert=True)
        await gem_market_my(update, context); return
        
    pdata = await player_manager.get_player_data(user_id)
    
    # Devolução usando ID puro
    item_payload = listing.get("item", {})
    base_id = item_payload.get("base_id")
    pack_qty = item_payload.get("qty", 1)
    lotes_left = listing.get("quantity", 0) 
    total_return = pack_qty * lotes_left
    item_label = _item_label(base_id)
    
    if base_id and total_return > 0:
        player_manager.add_item_to_inventory(pdata, base_id, total_return)
            
    await player_manager.save_player_data(user_id, pdata)
    
    text = f"✅ Listagem #{lid} ({item_label}) cancelada. Itens devolvidos."
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_my")]])
    await _safe_edit_or_send(q, context, chat_id, text, kb)

# ==============================
#  Handlers (Exports)
# ==============================

gem_market_main_handler = CallbackQueryHandler(gem_market_main, pattern=r'^gem_market_main$')

gem_list_cats_handler = CallbackQueryHandler(show_buy_category_menu, pattern=r'^gem_list_cats$')
gem_sell_cats_handler = CallbackQueryHandler(show_sell_category_menu, pattern=r'^gem_sell_cats$')

gem_list_filter_handler = CallbackQueryHandler(show_buy_class_picker, pattern=r'^gem_list_filter:(skin|skill|evo)$')
gem_list_class_handler = CallbackQueryHandler(show_buy_items_filtered, pattern=r'^gem_list_class:(skin|skill|evo):([a-z_]+):(\d+)$')

gem_sell_filter_handler = CallbackQueryHandler(show_sell_class_picker, pattern=r'^gem_sell_filter:(skin|skill|evo)$')
gem_sell_class_handler = CallbackQueryHandler(show_sell_items_filtered, pattern=r'^gem_sell_class:(skin|skill|evo):([a-z_]+):(\d+)$')

gem_market_pick_item_handler = CallbackQueryHandler(gem_market_pick_item, pattern=r'^gem_sell_item_')
gem_market_cancel_new_handler = CallbackQueryHandler(gem_market_cancel_new, pattern=r'^gem_market_cancel_new$')

gem_market_pack_spin_handler = CallbackQueryHandler(gem_market_pack_spin, pattern=r'^gem_pack_(inc|dec)_[0-9]+$')
gem_market_pack_confirm_handler = CallbackQueryHandler(gem_market_pack_confirm, pattern=r'^gem_pack_confirm$')

gem_market_lote_spin_handler = CallbackQueryHandler(gem_market_lote_spin, pattern=r'^gem_lote_(inc|dec)_[0-9]+$')
gem_market_lote_confirm_handler = CallbackQueryHandler(gem_market_lote_confirm, pattern=r'^gem_lote_confirm$')

gem_market_price_spin_handler = CallbackQueryHandler(gem_market_price_spin, pattern=r'^gem_p_(inc|dec)_[0-9]+$')
gem_market_price_confirm_handler = CallbackQueryHandler(gem_market_price_confirm, pattern=r'^gem_p_confirm$')

gem_market_buy_confirm_handler = CallbackQueryHandler(gem_market_buy_confirm, pattern=r'^gem_buy_confirm:.*:(\d+)$')
gem_market_buy_execute_handler = CallbackQueryHandler(gem_market_buy_execute, pattern=r'^gem_buy_execute_(\d+)$')

gem_market_my_handler = CallbackQueryHandler(gem_market_my, pattern=r'^gem_market_my$')
gem_market_cancel_execute_handler = CallbackQueryHandler(gem_market_cancel_execute, pattern=r'^gem_cancel_(\d+)$')