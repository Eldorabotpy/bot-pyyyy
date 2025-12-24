# handlers/gem_market_handler.py
# (VERSÃO 4.2 - COM LOG DE VENDAS NO GRUPO)

import logging
import math
import html
from typing import List, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules.game_data.items_evolution import EVOLUTION_ITEMS_DATA
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
    
    # 1. Recupera o objeto 'pending' PRIMEIRO para evitar erros
    pending = context.user_data.get("gem_market_pending")
    if not pending:
        # Se a sessão expirou, cancela para evitar crash
        await gem_market_cancel_new(update, context)
        return

    base_id = pending.get("base_id")
    
    # 2. Lógica de Preço Mínimo Inteligente
    # Se for item de Evolução, força iniciar em 10.
    # Caso contrário, inicia em 1 (ou no mínimo global).
    is_evo = base_id in EVOLUTION_ITEMS_DATA
    start_price = 10 if is_evo else 1
    
    # Salva no context para o spinner usar
    context.user_data["gem_market_price"] = start_price 
    
    # 3. Prepara textos
    item_label = _item_label(base_id)
    pack_qty = int(pending.get("qty", 1))
    lote_qty = int(context.user_data.get("gem_market_lotes", 1))

    caption_prefix = (
        f"Item: <b>{item_label} ×{pack_qty}</b>\n"
        f"Lotes: <b>{lote_qty}</b>\n\n"
        f"Defina o <b>preço por lote</b> (em Diamantes):"
    )
    
    # 4. Renderiza o Spinner
    kb = market_utils.render_spinner_kb(
        value=start_price, 
        prefix_inc="gem_p_inc_", 
        prefix_dec="gem_p_dec_", 
        label="Preço por lote", 
        confirm_cb="gem_p_confirm",
        currency_emoji="💎",
        allow_large_steps=False # Gemas não precisam de saltos de 1k/5k
    )
    
    await _safe_edit_or_send(q, context, chat_id, f"{caption_prefix} <b>💎 {start_price}</b>", kb)
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
    """Jogador selecionou um item para vender."""
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id
    
    base_id = q.data.replace("gem_sell_item_", "")
    
    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {}) or {}
    qty_have = int(inv.get(base_id, 0))
    
    if qty_have <= 0:
        await q.answer("Você não tem mais esse item.", show_alert=True)
        return

    # Salva estado inicial
    context.user_data["gem_market_pending"] = {
        "type": "item_stack", 
        "base_id": base_id, 
        "qty_have": qty_have,
        "qty": 1 # Padrão
    }
    
    # === VERIFICAÇÃO DE EVOLUÇÃO (LÓGICA DE UI) ===
    is_evo = base_id in EVOLUTION_ITEMS_DATA
    
    if is_evo:
        # Se for evolução:
        # 1. Trava o tamanho do lote (pack) em 1
        context.user_data["gem_market_pending"]["qty"] = 1
        
        # 2. Pula direto para perguntar "Quantos lotes?" (_show_gem_lote_spinner)
        # O usuário não escolhe "quantos itens por lote", pois é fixo em 1.
        await _show_gem_lote_spinner(q, context, chat_id)
        return

    # Se NÃO for evolução (ex: poções, skins), mostra o spinner normal de tamanho do pacote
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

# ============================================================================
# CORREÇÃO: FINALIZAR VENDA (Classificação Automática de Tipo)
# ============================================================================
async def gem_market_finalize_listing(update: Update, context: ContextTypes.DEFAULT_TYPE, price_gems: int):
    q = update.callback_query
    # Não usamos await q.answer() aqui pois _safe_edit_or_send cuida disso ou mensagem nova
    
    user_id = q.from_user.id
    chat_id = q.message.chat_id

    pending = context.user_data.get("gem_market_pending")
    if not pending:
        await q.answer("Sessão expirada.", show_alert=True)
        await gem_market_main(update, context)
        return
        
    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        await q.answer("Erro ao carregar dados.", show_alert=True)
        return

    # Dados do Item
    base_id_original = pending["base_id"]
    pack_qty = int(pending.get("qty", 1))
    lote_qty = max(1, int(context.user_data.get("gem_market_lotes", 1)))
    total_to_remove = pack_qty * lote_qty
    
    # Validação de Estoque
    if not player_manager.has_item(pdata, base_id_original, total_to_remove):
        await q.answer(f"Você não tem itens suficientes ({total_to_remove}).", show_alert=True)
        await gem_market_cancel_new(update, context)
        return

    # Remove do Inventário
    player_manager.remove_item_from_inventory(pdata, base_id_original, total_to_remove)
    await player_manager.save_player_data(user_id, pdata)
    
    # --- CORREÇÃO DE TIPO (AQUI ESTAVA O ERRO) ---
    # Classifica o item corretamente para aparecer na aba certa
    item_type_for_backend = "item_stack" # Padrão (Outros)
    
    bid = base_id_original.lower()
    
    # 1. Skins
    if bid.startswith("caixa_") or bid.startswith("skin_") or "skin" in bid:
        item_type_for_backend = "skin"
        
    # 2. Skills (Habilidades) - AGORA RECONHECE TUDO
    elif bid.startswith("tomo_") or bid.startswith("livro_") or bid.startswith("scroll_") or bid.startswith("pergaminho_"):
        item_type_for_backend = "skill"
        
    # 3. Evolução
    elif bid in EVOLUTION_ITEMS or "essencia_" in bid or "emblema_" in bid or "cristal_" in bid:
        item_type_for_backend = "evo_item"
    
    item_payload = {
        "type": item_type_for_backend, 
        "base_id": base_id_original,
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
        logger.error(f"[GemMarket] Falha ao criar listagem: {e}")
        # Devolve o item se der erro no banco
        player_manager.add_item_to_inventory(pdata, base_id_original, total_to_remove)
        await player_manager.save_player_data(user_id, pdata)
        
        await q.answer("Erro ao criar venda. Item devolvido.", show_alert=True)
        return
        
    # Limpa dados temporários
    context.user_data.pop("gem_market_pending", None)
    context.user_data.pop("gem_market_price", None)
    context.user_data.pop("gem_market_lotes", None)
    
    # Confirmação Visual
    # Tenta pegar nome bonito
    dname = base_id_original
    try:
        if display_utils: 
            info = display_utils._item_info(base_id_original)
            if info: dname = info.get("display_name", base_id_original)
    except: pass
    
    text = f"✅ <b>Venda Criada!</b>\n\n📦 <b>Item:</b> {dname}\n🔢 <b>Qtd:</b> {pack_qty} x {lote_qty} lotes\n💎 <b>Preço:</b> {price_gems} Gemas cada"
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Minhas Vendas", callback_data="gem_market_my")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")]
    ])
    
    try:
        await q.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
    except:
        await context.bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")

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
# handlers/gem_market_handler.py
# (VERSÃO 6.0 FINAL - VISUAL CARD RPG + FUNCIONALIDADE COMPLETA)

import logging
import math
from typing import List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

# --- Nossos Módulos ---
from modules import player_manager, game_data, file_id_manager
from modules import gem_market_manager
from modules import market_utils
from modules.game_data.items_evolution import EVOLUTION_ITEMS_DATA

# Tenta importar display_utils
try:
    from modules import display_utils
except ImportError:
    display_utils = None

logger = logging.getLogger(__name__)

# ==============================
#  CONFIGURAÇÕES E LISTAS
# ==============================
LOG_GROUP_ID = -1002881364171
LOG_TOPIC_ID = 24475

# Emojis de Classe para o Visual
CLASS_ICONS = {
    "guerreiro": "🛡️", "cavaleiro": "🛡️", "gladiador": "⚔️",
    "mago": "🧙‍♂️", "arquimago": "🔮", "feiticeiro": "🔥",
    "cacador": "🏹", "arqueiro": "🏹",
    "assassino": "🗡️", "ninja": "🥷",
    "monge": "👊", "mestre": "🙏",
    "bardo": "🎵", "musico": "🪕",
    "berserker": "🪓", "barbaro": "👹",
    "samurai": "👺", "ronin": "🗡️",
    "sacerdote": "✝️", "clerigo": "✨",
    "universal": "🌎"
}

# ==============================
#  Helpers de Renderização (Estilo Card)
# ==============================
def _get_item_info(base_id: str) -> dict:
    try:
        info = game_data.get_item_info(base_id)
        if info: return dict(info)
    except Exception: pass
    if base_id in EVOLUTION_ITEMS_DATA:
        return EVOLUTION_ITEMS_DATA[base_id]
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

def _item_label(base_id: str) -> str:
    info = _get_item_info(base_id)
    emoji = info.get("emoji", "💎")
    name = info.get("display_name", base_id)
    return f"{emoji} {name}"

def _format_class_name(item_info: dict) -> str:
    """Tenta descobrir a classe do item para exibir o ícone."""
    name = item_info.get("display_name", "").lower()
    base_id = item_info.get("id", "").lower()
    
    for cls, icon in CLASS_ICONS.items():
        if cls in name or cls in base_id:
            return f"{icon} {cls.capitalize()}"
    return "🌎 Global"

def _render_card_simple(base_id: str, qty: int, price: int = 0, seller_name: str = None, lote_qty: int = 1) -> str:
    """Renderiza um card visual para itens de gemas."""
    info = _get_item_info(base_id)
    name = info.get("display_name") or base_id.replace("_", " ").title()
    emoji = info.get("emoji", "📦")
    desc = info.get("description", "Item Raro")
    
    if len(desc) > 30: desc = desc[:29] + "..."
    
    # Linha 1: Identificação
    line1 = f"{emoji} <b>{name}</b> (x{qty})"
    
    # Linha 2: Detalhes
    class_str = _format_class_name(info)
    line2 = f"├┈➤ {class_str} │ ℹ️ <i>{desc}</i>"

    # Linha 3: Preço e Vendedor
    if price > 0:
        seller_txt = f"👤 <i>{seller_name}</i>" if seller_name else ""
        lote_txt = f"📦 {lote_qty} Lotes" if lote_qty > 1 else "📦 1 Lote"
        line3 = f"╰┈➤ 💎 <b>{price}</b> │ {lote_txt} │ {seller_txt}"
        return f"{line1}\n{line2}\n{line3}"
    
    return f"{line1}\n╰┈➤ 📦 Estoque: <b>{qty}</b>"

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    try: await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except:
        try: await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        except: await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

async def _send_with_media(chat_id, context, text, kb, keys):
    for k in keys:
        fd = file_id_manager.get_file_data(k)
        if fd:
            try:
                await context.bot.send_photo(chat_id, fd["id"], caption=text, reply_markup=kb, parse_mode="HTML")
                return
            except: pass
    await context.bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")

# ==============================
#  MENU PRINCIPAL
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

    keys = ["mercado_gemas", "img_mercado_gemas", "gem_market"]
    try: await q.delete_message(); 
    except: pass
    await _send_with_media(chat_id, context, text, kb, keys)

# ==============================
#  NAVEGAÇÃO E FILTROS
# ==============================

async def show_buy_category_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    text = "📦 <b>Comprar: Escolha a Categoria</b>"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Itens de Evolução", callback_data="gem_list_filter:evo")],
        [InlineKeyboardButton("📚 Tomos de Skill", callback_data="gem_list_filter:skill")],
        [InlineKeyboardButton("🎨 Caixas de Skin", callback_data="gem_list_filter:skin")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")],
    ])
    await _safe_edit_or_send(q, context, q.message.chat_id, text, kb)

async def show_sell_category_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    text = "➕ <b>Vender: Escolha a Categoria</b>"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Itens de Evolução", callback_data="gem_sell_filter:evo")],
        [InlineKeyboardButton("📚 Tomos de Skill", callback_data="gem_sell_filter:skill")],
        [InlineKeyboardButton("🎨 Caixas de Skin", callback_data="gem_sell_filter:skin")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")],
    ])
    await _safe_edit_or_send(q, context, q.message.chat_id, text, kb)

# ==============================
#  LISTAGEM DE COMPRA
# ==============================
async def show_buy_items_filtered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    
    parts = q.data.split(":")
    item_type = parts[1] # evo, skill, skin
    page = int(parts[2]) if len(parts) > 2 else 1

    all_listings = gem_market_manager.list_active(page=1, page_size=200)
    if all_listings is None: all_listings = []

    # Lógica de Filtro Otimizada (Sem Listas Gigantes)
    filtered = []
    for l in all_listings:
        it = l.get("item", {})
        bid = it.get("base_id", "")
        
        is_match = False
        # Filtra por prefixo ou presença na lista de evolução
        if item_type == "evo" and (bid in EVOLUTION_ITEMS_DATA or "essencia" in bid): is_match = True
        elif item_type == "skill" and ("tomo" in bid or "livro" in bid): is_match = True
        elif item_type == "skin" and ("caixa" in bid or "skin" in bid): is_match = True
        
        if is_match: filtered.append(l)

    # Paginação
    PER_PAGE = 5
    total_items = len(filtered)
    total_pages = math.ceil(total_items / PER_PAGE)
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1
    
    start = (page - 1) * PER_PAGE
    end = start + PER_PAGE
    page_items = filtered[start:end]

    pdata = await player_manager.get_player_data(user_id)
    gems = player_manager.get_gems(pdata)

    lines = [
        f"╭┈┈┈┈┈➤ 🏛️ <b>MERCADO</b> ({page}/{total_pages}) ┈┈┈┈┈╮",
        f" │ 💎 <b>Seus Diamantes:</b> {gems}",
        f"╰┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤",
        ""
    ]

    if not page_items:
        lines.append("<i>Nenhum item encontrado nesta categoria.</i>")

    buttons_map = {}
    num_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

    for idx, listing in enumerate(page_items):
        icon_num = num_emojis[idx] if idx < 5 else f"{idx+1}"
        
        item_data = listing.get("item", {})
        base_id = item_data.get("base_id")
        qty = item_data.get("qty", 1)
        price = listing.get("unit_price_gems", 0)
        lotes = listing.get("quantity", 1)
        seller_id = listing.get("seller_id")
        lid = listing.get("id")
        
        seller_name = "Vendedor" 
        if int(seller_id) == user_id: seller_name = "Você"

        card = _render_card_simple(base_id, qty, price, seller_name, lotes)
        lines.append(f"{icon_num}┈➤{card}")
        lines.append("") 
        
        buttons_map[icon_num] = lid

    kb_rows = []
    btn_row = []
    
    for idx, (icon, lid) in enumerate(buttons_map.items()):
        btn_row.append(InlineKeyboardButton(f"🛒 {icon}", callback_data=f"gem_buy_confirm:{lid}"))
        
    if btn_row: kb_rows.append(btn_row)

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ Ant.", callback_data=f"gem_list_filter:{item_type}:{page-1}"))
    nav.append(InlineKeyboardButton("🔙 Menu", callback_data="gem_market_main"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("Prox. ➡️", callback_data=f"gem_list_filter:{item_type}:{page+1}"))
    kb_rows.append(nav)

    await _safe_edit_or_send(q, context, q.message.chat_id, "\n".join(lines), InlineKeyboardMarkup(kb_rows))

# ==============================
#  LISTAGEM DE VENDA
# ==============================
async def show_sell_items_filtered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    
    parts = q.data.split(":")
    item_type = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 1

    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {})

    # Filtra inventário
    sellable = []
    for bid, item_data in inv.items():
        qty = item_data.get("quantity", 0) if isinstance(item_data, dict) else int(item_data)
        if qty <= 0: continue
        
        is_match = False
        if item_type == "evo" and (bid in EVOLUTION_ITEMS_DATA or "essencia" in bid): is_match = True
        elif item_type == "skill" and ("tomo" in bid or "livro" in bid): is_match = True
        elif item_type == "skin" and ("caixa" in bid or "skin" in bid): is_match = True
        
        if is_match: sellable.append({"base_id": bid, "qty": qty})

    PER_PAGE = 5
    total_items = len(sellable)
    total_pages = math.ceil(total_items / PER_PAGE)
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1
    
    start = (page - 1) * PER_PAGE
    end = start + PER_PAGE
    page_items = sellable[start:end]

    lines = [f"➕ <b>VENDER ITEM</b> ({page}/{total_pages})\n<i>Selecione o número para vender:</i>\n"]
    if not page_items:
        lines.append("🎒 <i>Você não possui itens desta categoria.</i>")

    buttons_map = {}
    num_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

    for idx, item in enumerate(page_items):
        icon_num = num_emojis[idx] if idx < 5 else f"{idx+1}"
        base_id = item["base_id"]
        qty = item["qty"]
        
        card = _render_card_simple(base_id, qty)
        lines.append(f"{icon_num}┈➤{card}")
        lines.append("")
        
        buttons_map[icon_num] = base_id

    kb_rows = []
    btn_row = []
    for icon, bid in buttons_map.items():
        btn_row.append(InlineKeyboardButton(f"🛒 {icon}", callback_data=f"gem_sell_item_{bid}"))
    if btn_row: kb_rows.append(btn_row)

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ Ant.", callback_data=f"gem_sell_filter:{item_type}:{page-1}"))
    nav.append(InlineKeyboardButton("🔙 Menu", callback_data="gem_market_main"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("Prox. ➡️", callback_data=f"gem_sell_filter:{item_type}:{page+1}"))
    kb_rows.append(nav)

    await _safe_edit_or_send(q, context, q.message.chat_id, "\n".join(lines), InlineKeyboardMarkup(kb_rows))

# ==============================
#  LÓGICA DE COMPRA (Restaurada e Otimizada)
# ==============================

async def gem_market_buy_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    try: lid = int(q.data.split(":")[1])
    except: return

    listing = gem_market_manager.get_listing(lid)
    if not listing or not listing.get("active"):
        await q.answer("Item não disponível.", show_alert=True)
        await show_buy_category_menu(update, context)
        return

    item = listing.get("item", {})
    price = listing.get("unit_price_gems", 0)
    base_id = item.get("base_id")
    qty = item.get("qty", 1)
    
    info = _get_item_info(base_id)
    name = info.get("display_name", base_id)
    
    text = (
        f"🛒 <b>CONFIRMAR COMPRA</b>\n\n"
        f"📦 <b>Item:</b> {name} (x{qty})\n"
        f"💎 <b>Preço:</b> {price} Gemas\n\n"
        f"Deseja confirmar a transação?"
    )
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirmar", callback_data=f"gem_buy_execute_{lid}")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="gem_market_main")]
    ])
    
    await _safe_edit_or_send(q, context, q.message.chat_id, text, kb)

async def gem_market_buy_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Executa a compra de fato (Função que faltava)."""
    q = update.callback_query
    await q.answer("Processando...")
    
    buyer_id = q.from_user.id
    try: lid = int(q.data.replace("gem_buy_execute_", ""))
    except: await q.answer("ID inválido.", show_alert=True); return
        
    # 1. Validações
    listing = gem_market_manager.get_listing(lid)
    if not listing or not listing.get("active"):
        await q.answer("Item já vendido!", show_alert=True)
        await gem_market_main(update, context); return
        
    seller_id = int(listing.get("seller_id", 0))
    if buyer_id == seller_id:
        await q.answer("Não podes comprar o teu próprio item.", show_alert=True); return

    buyer_pdata = await player_manager.get_player_data(buyer_id)
    seller_pdata = await player_manager.get_player_data(seller_id)
    
    total_cost = int(listing.get("unit_price_gems", 0)) 
    buyer_gems = int(buyer_pdata.get("gems", 0))
    
    if buyer_gems < total_cost:
        await q.answer(f"Gemas insuficientes! Precisas de {total_cost}.", show_alert=True); return

    # 2. Transação Backend
    try:
        # Debita comprador (apenas para atualizar o objeto local, a transação real é no purchase_listing)
        buyer_pdata["gems"] = max(0, buyer_gems - total_cost)
        
        # Chama a função segura do manager
        await gem_market_manager.purchase_listing( 
            buyer_pdata=buyer_pdata, 
            seller_pdata=seller_pdata, 
            listing_id=lid,
            quantity=1
        )
    except Exception as e:
        await q.answer(f"Erro na transação: {e}", show_alert=True); return

    # 3. Entrega do Item
    item_payload = listing.get("item", {})
    base_id = item_payload.get("base_id") 
    pack_qty = int(item_payload.get("qty", 1))
    
    player_manager.add_item_to_inventory(buyer_pdata, base_id, pack_qty) 
    await player_manager.save_player_data(buyer_id, buyer_pdata)

    # 4. Notificação e Log
    item_label = _item_label(base_id)
    
    # Notifica Vendedor
    if seller_id:
        try:
            await context.bot.send_message(seller_id, f"💎 <b>Venda Realizada!</b>\nVendeste <b>{item_label}</b> por <b>{total_cost} Gemas</b>.", parse_mode="HTML")
        except: pass

    # Log Grupo
    try:
        buyer_name = buyer_pdata.get("character_name", q.from_user.first_name)
        seller_name = seller_pdata.get("character_name", "Desconhecido") if seller_pdata else "Desconhecido"
        log_text = (f"💎 <b>MERCADO GEMAS (VENDA)</b>\n👤 <b>Comprador:</b> {buyer_name}\n📦 <b>Item:</b> {item_label} x{pack_qty}\n💰 <b>Valor:</b> {total_cost} Gemas\n🤝 <b>Vendedor:</b> {seller_name}")
        await context.bot.send_message(chat_id=LOG_GROUP_ID, message_thread_id=LOG_TOPIC_ID, text=log_text, parse_mode="HTML")
    except: pass

    # Feedback Comprador
    text = f"✅ <b>Sucesso!</b>\nRecebeste <b>{item_label} (x{pack_qty})</b>.\nCusto: 💎 {total_cost}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="gem_list_cats")]])
    await _safe_edit_or_send(q, context, q.message.chat_id, text, kb)

# ==============================
#  MINHAS LISTAGENS E CANCELAMENTO
# ==============================

async def gem_market_my(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    
    my_listings = gem_market_manager.list_by_seller(user_id) 

    if not my_listings:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")]])
        await _safe_edit_or_send(q, context, q.message.chat_id, "Você não tem listagens ativas.", kb)
        return

    lines = ["👤 <b>Minhas Listagens (Gemas)</b>\n"]
    kb_rows = []
    
    for l in my_listings:
        item = l.get("item", {})
        price = l.get("unit_price_gems", 0)
        label = _item_label(item.get("base_id"))
        lines.append(f"• {label} (x{item.get('qty', 1)}) — 💎 {price}")
        kb_rows.append([InlineKeyboardButton(f"Cancelar #{l['id']}", callback_data=f"gem_cancel_{l['id']}")])

    kb_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")])
    await _safe_edit_or_send(q, context, q.message.chat_id, "\n".join(lines), InlineKeyboardMarkup(kb_rows))

async def gem_market_cancel_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("A cancelar...")
    user_id = q.from_user.id
    
    try: lid = int(q.data.replace("gem_cancel_", ""))
    except: return

    try:
        listing = await gem_market_manager.cancel_listing(seller_id=user_id, listing_id=lid)
    except Exception as e:
        await q.answer(f"Erro: {e}", show_alert=True)
        await gem_market_my(update, context); return
    
    # Mensagem de sucesso
    await _safe_edit_or_send(q, context, q.message.chat_id, f"✅ Listagem #{lid} cancelada. Itens devolvidos.", 
                             InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_my")]]))

# ==============================
#  LÓGICA DE VENDA (SPINNERS)
# ==============================

async def gem_market_pick_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    base_id = q.data.replace("gem_sell_item_", "")
    
    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {}) or {}
    qty_have = int(inv.get(base_id, 0))
    
    if qty_have <= 0:
        await q.answer("Você não tem mais esse item.", show_alert=True); return

    context.user_data["gem_market_pending"] = {
        "type": "item_stack", "base_id": base_id, "qty_have": qty_have, "qty": 1
    }
    
    # Regra: Se for evolução, lote é sempre 1
    if base_id in EVOLUTION_ITEMS_DATA:
        context.user_data["gem_market_pending"]["qty"] = 1
        await _show_gem_lote_spinner(q, context, q.message.chat_id)
    else:
        await _show_gem_pack_spinner(q, context, q.message.chat_id)

async def _show_gem_pack_spinner(q, context, chat_id):
    pending = context.user_data.get("gem_market_pending")
    qty_have = pending["qty_have"]
    cur = pending["qty"]
    kb = market_utils.render_spinner_kb(value=cur, prefix_inc="gem_pack_inc_", prefix_dec="gem_pack_dec_", label="Itens/Lote", confirm_cb="gem_pack_confirm")
    await _safe_edit_or_send(q, context, chat_id, f"Defina o tamanho do pacote:\nTotal disponível: {qty_have}", kb)

async def gem_market_pack_spin(update, context):
    q = update.callback_query; await q.answer()
    pending = context.user_data.get("gem_market_pending")
    max_q = pending["qty_have"]
    cur = market_utils.calculate_spin_value(pending["qty"], q.data, "gem_pack_inc_", "gem_pack_dec_", 1, max_q)
    pending["qty"] = cur
    await _show_gem_pack_spinner(q, context, update.effective_chat.id)

async def gem_market_pack_confirm(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["gem_market_lotes"] = 1
    await _show_gem_lote_spinner(q, context, update.effective_chat.id)

async def _show_gem_lote_spinner(q, context, chat_id):
    pending = context.user_data.get("gem_market_pending")
    qty_have = pending["qty_have"]
    pack_qty = pending["qty"]
    max_lotes = max(1, qty_have // pack_qty)
    context.user_data["gem_market_lote_max"] = max_lotes
    
    cur = context.user_data.get("gem_market_lotes", 1)
    kb = market_utils.render_spinner_kb(value=cur, prefix_inc="gem_lote_inc_", prefix_dec="gem_lote_dec_", label="Qtd Lotes", confirm_cb="gem_lote_confirm", allow_large_steps=False)
    await _safe_edit_or_send(q, context, chat_id, f"Quantos lotes de {pack_qty} itens?", kb)

async def gem_market_lote_spin(update, context):
    q = update.callback_query; await q.answer()
    max_l = context.user_data.get("gem_market_lote_max", 1)
    cur = market_utils.calculate_spin_value(context.user_data.get("gem_market_lotes", 1), q.data, "gem_lote_inc_", "gem_lote_dec_", 1, max_l)
    context.user_data["gem_market_lotes"] = cur
    await _show_gem_lote_spinner(q, context, update.effective_chat.id)

async def gem_market_lote_confirm(update, context):
    q = update.callback_query; await q.answer()
    pending = context.user_data.get("gem_market_pending")
    # Regra de Preço Mínimo
    base_id = pending.get("base_id")
    min_price = 10 if base_id in EVOLUTION_ITEMS_DATA else 1
    context.user_data["gem_market_price"] = min_price
    await _show_gem_price_spinner(q, context, update.effective_chat.id)

async def _show_gem_price_spinner(q, context, chat_id):
    price = context.user_data.get("gem_market_price", 1)
    kb = market_utils.render_spinner_kb(value=price, prefix_inc="gem_p_inc_", prefix_dec="gem_p_dec_", label="Preço (Gemas)", confirm_cb="gem_p_confirm", currency_emoji="💎", allow_large_steps=False)
    await _safe_edit_or_send(q, context, chat_id, f"Defina o preço por lote (Gemas): <b>{price}</b>", kb)

async def gem_market_price_spin(update, context):
    q = update.callback_query; await q.answer()
    pending = context.user_data.get("gem_market_pending")
    min_p = 10 if pending and pending["base_id"] in EVOLUTION_ITEMS_DATA else 1
    cur = market_utils.calculate_spin_value(context.user_data.get("gem_market_price", min_p), q.data, "gem_p_inc_", "gem_p_dec_", min_p)
    context.user_data["gem_market_price"] = cur
    await _show_gem_price_spinner(q, context, update.effective_chat.id)

async def gem_market_price_confirm(update, context):
    q = update.callback_query; await q.answer()
    price = context.user_data.get("gem_market_price", 1)
    
    # Finaliza a venda
    user_id = q.from_user.id
    pending = context.user_data.get("gem_market_pending")
    base_id = pending["base_id"]
    pack_qty = pending["qty"]
    lotes = context.user_data.get("gem_market_lotes", 1)
    total_remove = pack_qty * lotes
    
    pdata = await player_manager.get_player_data(user_id)
    if not player_manager.has_item(pdata, base_id, total_remove):
        await q.answer("Erro de estoque.", show_alert=True); return

    player_manager.remove_item_from_inventory(pdata, base_id, total_remove)
    await player_manager.save_player_data(user_id, pdata)
    
    # Define tipo para o backend
    itype = "evo_item" if base_id in EVOLUTION_ITEMS_DATA else "item_stack"
    if "tomo_" in base_id: itype = "skill"
    elif "skin_" in base_id or "caixa_" in base_id: itype = "skin"
    
    item_payload = {"type": itype, "base_id": base_id, "qty": pack_qty}
    gem_market_manager.create_listing(seller_id=user_id, item_payload=item_payload, unit_price=price, quantity=lotes)
    
    await _safe_edit_or_send(q, context, update.effective_chat.id, "✅ <b>Listagem criada com sucesso!</b>", 
                             InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")]]))

async def gem_market_cancel_new(update, context):
    q = update.callback_query; await q.answer()
    context.user_data.pop("gem_market_pending", None)
    await _safe_edit_or_send(q, context, update.effective_chat.id, "Operação cancelada.", 
                             InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="gem_market_main")]]))

# ==============================
#  HANDLERS EXPORT
# ==============================
gem_market_main_handler = CallbackQueryHandler(gem_market_main, pattern=r'^gem_market_main$')
gem_list_cats_handler = CallbackQueryHandler(show_buy_category_menu, pattern=r'^gem_list_cats$')
gem_sell_cats_handler = CallbackQueryHandler(show_sell_category_menu, pattern=r'^gem_sell_cats$')

gem_list_filter_handler = CallbackQueryHandler(show_buy_items_filtered, pattern=r'^gem_list_filter:')
gem_sell_filter_handler = CallbackQueryHandler(show_sell_items_filtered, pattern=r'^gem_sell_filter:')

gem_market_pick_item_handler = CallbackQueryHandler(gem_market_pick_item, pattern=r'^gem_sell_item_')
gem_market_buy_confirm_handler = CallbackQueryHandler(gem_market_buy_confirm, pattern=r'^gem_buy_confirm:')
gem_market_buy_execute_handler = CallbackQueryHandler(gem_market_buy_execute, pattern=r'^gem_buy_execute_')

gem_market_my_handler = CallbackQueryHandler(gem_market_my, pattern=r'^gem_market_my$')
gem_market_cancel_execute_handler = CallbackQueryHandler(gem_market_cancel_execute, pattern=r'^gem_cancel_')

# Spinners
gem_market_pack_spin_handler = CallbackQueryHandler(gem_market_pack_spin, pattern=r'^gem_pack_(inc|dec)_[0-9]+$')
gem_market_pack_confirm_handler = CallbackQueryHandler(gem_market_pack_confirm, pattern=r'^gem_pack_confirm$')
gem_market_lote_spin_handler = CallbackQueryHandler(gem_market_lote_spin, pattern=r'^gem_lote_(inc|dec)_[0-9]+$')
gem_market_lote_confirm_handler = CallbackQueryHandler(gem_market_lote_confirm, pattern=r'^gem_lote_confirm$')
gem_market_price_spin_handler = CallbackQueryHandler(gem_market_price_spin, pattern=r'^gem_p_(inc|dec)_[0-9]+$')
gem_market_price_confirm_handler = CallbackQueryHandler(gem_market_price_confirm, pattern=r'^gem_p_confirm$')
gem_market_cancel_new_handler = CallbackQueryHandler(gem_market_cancel_new, pattern=r'^gem_market_cancel_new$')
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