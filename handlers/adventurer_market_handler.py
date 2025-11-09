# handlers/adventurer_market_handler.py
# (VERSÃO COM INDENTAÇÃO CORRIGIDA)

import logging
from typing import List, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules import mission_manager, player_manager, game_data, file_id_manager, market_manager, clan_manager
from modules.market_manager import render_listing_line as _mm_render_listing_line

# --- DISPLAY UTILS opcional (fallback consistente) ---
try:
    from modules import display_utils  # deve ter: formatar_item_para_exibicao(dict) -> str
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
#  BLOQUEIO: Itens de evolução de classe
# ==============================
EVOLUTION_ITEMS: set[str] = {
    "emblema_guerreiro", "essencia_guardia", "essencia_furia", "selo_sagrado", "essencia_luz",
    "emblema_berserker", "totem_ancestral", "emblema_cacador", "essencia_precisao",
    "marca_predador", "essencia_fera", "emblema_monge", "reliquia_mistica", "essencia_ki",
    "emblema_mago", "essencia_arcana", "essencia_elemental", "grimorio_arcano",
    "emblema_bardo", "essencia_harmonia", "essencia_encanto", "batuta_maestria",
    "emblema_assassino", "essencia_sombra", "essencia_letal", "manto_eterno",
    "emblema_samurai", "essencia_corte", "essencia_disciplina", "lamina_sagrada",
}

# 2. Tomos de Skill (CORRIGIDO com "tomo_")
SKILL_BOOK_ITEMS: set[str] = {
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
}

# 3. Caixas de Skin (CORRIGIDO com "caixa_")
SKIN_BOX_ITEMS: set[str] = {
    'caixa_guerreiro_armadura_negra', 'caixa_guerreiro_placas_douradas',
    'caixa_mago_traje_arcano', 'caixa_assassino_manto_espectral', 'caixa_cacador_patrulheiro_elfico',
    'caixa_berserker_pele_urso', 'caixa_monge_quimono_dragao', 'caixa_bardo_traje_maestro',
    'caixa_samurai_armadura_shogun', 'caixa_samurai_armadura_demoniaca', 'caixa_samurai_encarnacao_sangrenta',
    'caixa_samurai_guardiao_celestial', 'caixa_samurai_chama_aniquiladora', 
}

# --- Lista de Bloqueio Combinada ---
PREMIUM_BLOCK_LIST = EVOLUTION_ITEMS.union(SKILL_BOOK_ITEMS).union(SKIN_BOX_ITEMS)

# --- Mensagem de Bloqueio Unificada ---
PREMIUM_BLOCK_MSG = (
    "🚫 Este é um item premium (Evolução, Skill ou Skin) e não pode ser vendido "
    "no Mercado do Aventureiro (Ouro).\n\n"
    "Use a <b>🏛️ Casa de Leilões</b> (Diamantes) para negociar este item."
)

# ==============================
#  Utils básicos
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
        if info:
            return dict(info)
    except Exception:
        pass
    return (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id, {}) or {}

def _player_class_key(pdata: dict, fallback="guerreiro") -> str:
    for c in [
        (pdata.get("class") or pdata.get("classe")),
        pdata.get("class_type"), pdata.get("classe_tipo"),
        pdata.get("class_key"), pdata.get("classe"),
    ]:
        if isinstance(c, dict):
            t = c.get("type")
            if isinstance(t, str) and t.strip():
                return t.strip().lower()
        if isinstance(c, str) and c.strip():
            return c.strip().lower()
    return fallback

def _cut_middle(s: str, maxlen: int = 56) -> str:
    s = (s or "").strip()
    return s if len(s) <= maxlen else s[:maxlen//2 - 1] + "… " + s[-maxlen//2:]

# Em handlers/adventurer_market_handler.py

# Em handlers/adventurer_market_handler.py

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return # Sucesso
    except Exception as e:
        # <<< CORREÇÃO AQUI >>>
        if "message is not modified" in str(e).lower():
            return # Para a execução, está tudo bem.
        pass # Erro real (ex: era texto), tenta o próximo.
    
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return # Sucesso
    except Exception as e:
        # <<< CORREÇÃO AQUI >>>
        if "message is not modified" in str(e).lower():
            return # Para a execução, está tudo bem.
        pass # Erro real (ex: era media), tenta o próximo.
    
    # Se AMBOS falharam (ex: mensagem foi apagada), envia uma nova.
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

async def _send_with_media(chat_id: int, context: ContextTypes.DEFAULT_TYPE, caption: str, kb: InlineKeyboardMarkup, media_keys: List[str]):
    for key in media_keys:
        fd = file_id_manager.get_file_data(key)
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
#  Emojis/rotulagem (usa mapa oficial + fallback)
# ==============================
RARITY_LABEL: Dict[str, str] = {
    "comum": "Comum", "bom": "Boa", "raro": "Rara",
    "epico": "Épica", "lendario": "Lendária",
}

_CLASS_DMG_EMOJI_FALLBACK = {
    "guerreiro": "⚔️", "berserker": "🪓", "cacador": "🏹", "caçador": "🏹",
    "assassino": "🗡", "bardo": "🎵", "monge": "🙏", "mago": "✨", "samurai": "🗡",
}
_STAT_EMOJI_FALLBACK = {
    "dmg": "🗡", "hp": "❤️‍🩹", "vida": "❤️‍🩹", "defense": "🛡️", "defesa": "🛡️",
    "initiative": "🏃", "agilidade": "🏃", "luck": "🍀", "sorte": "🍀",
    "forca": "💪", "força": "💪", "foco": "🧘", "carisma": "😎", "bushido": "🥷",
    "inteligencia": "🧠", "inteligência": "🧠", "precisao": "🎯", "precisão": "🎯",
    "letalidade": "☠️", "furia": "🔥", "fúria": "🔥",
}

def _class_dmg_emoji(pclass: str) -> str:
    try:
        return getattr(game_data, "CLASS_DMG_EMOJI", {}).get((pclass or "").lower(), _CLASS_DMG_EMOJI_FALLBACK.get((pclass or "").lower(), "🗡"))
    except Exception:
        return _CLASS_DMG_EMOJI_FALLBACK.get((pclass or "").lower(), "🗡")

def _stat_emoji(stat: str, pclass: str) -> str:
    s = (stat or "").lower()
    try:
        attr_mod = getattr(game_data, "attributes", None)
        if attr_mod and hasattr(attr_mod, "ATTRIBUTE_ICONS"):
            em = attr_mod.ATTRIBUTE_ICONS.get(s)
            if em:
                return _class_dmg_emoji(pclass) if s == "dmg" else em
    except Exception:
        pass
    if s == "dmg":
        return _class_dmg_emoji(pclass)
    return _STAT_EMOJI_FALLBACK.get(s, "❔")

def _stack_inv_display(base_id: str, qty: int) -> str:
    info = _get_item_info(base_id)
    name = info.get("display_name") or info.get("nome_exibicao") or base_id
    emoji = info.get("emoji", "")
    return f"{emoji}{name} ×{qty}" if emoji else f"{name} ×{qty}"

def _render_unique_line_safe(inst: dict, pclass: str) -> str:
    try:
        return display_utils.formatar_item_para_exibicao(inst)
    except Exception:
        pass

    base_id = inst.get("base_id") or inst.get("tpl") or inst.get("id") or "item"
    info = _get_item_info(base_id)
    name = inst.get("display_name") or info.get("display_name") or info.get("nome_exibicao") or base_id
    item_emoji = inst.get("emoji") or info.get("emoji") or _class_dmg_emoji(pclass)
    try:
        cur_d, max_d = inst.get("durability", [20, 20]); cur_d, max_d = int(cur_d), int(max_d)
    except Exception:
        cur_d, max_d = 20, 20
    try:
        tier = int(inst.get("tier", 1))
    except Exception:
        tier = 1
    rarity = str(inst.get("rarity", "comum")).lower()
    rarity_label = RARITY_LABEL.get(rarity, rarity.capitalize())
    ench = inst.get("enchantments") or {}
    parts = []
    primary_key, primary_val = None, 0
    if isinstance(ench, dict):
        for k, v in ench.items():
            if k == "dmg" or not isinstance(v, dict): continue
            if str(v.get("source", "")).startswith("primary"):
                primary_key = k
                try: primary_val = int(v.get("value", 0) or 0)
                except Exception: primary_val = 0
                break
        if primary_key is None:
            best = None
            for k, v in ench.items():
                if k == "dmg" or not isinstance(v, dict): continue
                try: val = int(v.get("value", 0) or 0)
                except Exception: val = 0
                if best is None or val > best[1]: best = (k, val)
            if best: primary_key, primary_val = best
    if primary_key:
        parts.append(f"{_stat_emoji(primary_key, pclass)}+{int(primary_val)}")
    if isinstance(ench, dict):
        afx = []
        for k, v in ench.items():
            if k in ("dmg", primary_key) or not isinstance(v, dict): continue
            if str(v.get("source")) != "affix": continue
            try: val = int(v.get("value", 0) or 0)
            except Exception: val = 0
            afx.append((k, val))
        afx.sort(key=lambda t: (t[0], -t[1]))
        for k, val in afx:
            parts.append(f"{_stat_emoji(k, pclass)}+{int(val)}")
    stats_str = ", ".join(parts) if parts else "—"
    return f"『[{cur_d}/{max_d}] {item_emoji}{name} [ {tier} ] [ {rarity_label} ]: {stats_str}』"


async def market_adventurer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ponto de entrada para o Mercado do Aventureiro.
    (Agora permite que TODOS os jogadores entrem)
    """
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id

    # --- VERIFICAÇÃO PREMIUM REMOVIDA DESTA FUNÇÃO ---
    # Todos os jogadores podem aceder a este menu.

    text = (
        "🎒 <b>Mercado do Aventureiro</b>\n"
        "Compre e venda itens com outros jogadores."
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Listagens (Ver Itens)", callback_data="market_list")],
        [InlineKeyboardButton("➕ Vender Item", callback_data="market_sell:1")],
        [InlineKeyboardButton("👤 Minhas Listagens", callback_data="market_my")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market")],
    ])

    keys = ["mercado_aventureiro", "img_mercado_aventureiro", "market_adventurer", "market_aventurer_img"]
    try:
        await q.delete_message()
    except Exception:
        pass
    await _send_with_media(chat_id, context, text, kb, keys)

async def market_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    user_id = q.from_user.id
    
    # Carrega dados do jogador que está a ver a lista
    viewer_pdata = await player_manager.get_player_data(user_id) or {}

    # <<< CORREÇÃO APLICADA AQUI >>>
    # Verifica se o JOGADOR QUE ESTÁ A VER é premium
    is_premium_viewer = player_manager.has_premium_plan(viewer_pdata) 

    listings = market_manager.list_active() # Síncrono (corrigido antes)
    logger.info("[market_list] ativos=%d", len(listings))

    if not listings:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]])
        await _safe_edit_or_send(q, context, chat_id, "Não há listagens ativas no momento.", kb)
        return

    lines = ["📦 <b>Listagens ativas</b>\n"]
    
    # Adiciona um aviso se o jogador não for premium
    if not is_premium_viewer:
        lines.append("<i>Apenas Apoiadores (Premium) podem comprar itens.</i>\n")
        
    kb_rows = []
    for l in listings[:30]: 
        lines.append("• " + _mm_render_listing_line(l, viewer_player_data=viewer_pdata, show_price_per_unit=True))
        
        # <<< CORREÇÃO APLICADA AQUI >>>
        # Só mostra o botão "Comprar" se:
        # 1. O visualizador for premium
        # 2. O visualizador não for o vendedor do item
        if is_premium_viewer and int(l.get("seller_id", 0)) != user_id:
            kb_rows.append([InlineKeyboardButton(f"Comprar #{l['id']}", callback_data=f"market_buy_{l['id']}")])

    kb_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")])
    await _safe_edit_or_send(q, context, chat_id, "\n".join(lines), InlineKeyboardMarkup(kb_rows))

async def market_my(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id
    
    # Carrega dados do jogador (correto)
    viewer_pdata = await player_manager.get_player_data(user_id) or {}

    # <<< CORREÇÃO APLICADA AQUI: REMOVIDO 'await' >>>
    # list_by_seller é SÍNCRONO
    my = market_manager.list_by_seller(user_id) 

    # Se não houver listagens
    if not my:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]])
        await _safe_edit_or_send(q, context, chat_id, "Você não tem listagens ativas.", kb)
        return

    # Monta a lista e botões
    lines = ["👤 <b>Minhas listagens</b>\n"]
    kb_rows = []
    for l in my:
        # Renderiza linha (síncrono)
        lines.append("• " + _mm_render_listing_line(l, viewer_player_data=viewer_pdata, show_price_per_unit=True))
        # Adiciona botão de cancelar
        kb_rows.append([InlineKeyboardButton(f"Cancelar #{l['id']}", callback_data=f"market_cancel_{l['id']}")])

    # Adiciona botão de voltar
    kb_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")])
    
    # Envia mensagem
    await _safe_edit_or_send(q, context, chat_id, "\n".join(lines), InlineKeyboardMarkup(kb_rows))

async def market_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id
    
    try:
        lid = int(q.data.replace("market_cancel_", ""))
    except (ValueError, AttributeError):
        await q.answer("ID de listagem inválido.", show_alert=True)
        return

    # <<< CORREÇÃO 1: REMOVIDO 'await' >>>
    listing = market_manager.get_listing(lid) 

    if not listing or not listing.get("active"):
        await q.answer("Listagem inválida ou já cancelada.", show_alert=True)
        await market_my(update, context) 
        return
    if int(listing.get("seller_id", 0)) != int(user_id):
        await q.answer("Você não pode cancelar a listagem de outro jogador.", show_alert=True)
        return

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        await q.answer("Erro ao carregar seus dados.", show_alert=True)
        return
        
    # Devolve o item
    it = listing.get("item") 
    if isinstance(it, dict): 
        item_type = it.get("type")
        if item_type == "stack": 
            base_id = it.get("base_id")
            pack_qty = int(it.get("qty", 1))
            lots_left = int(listing.get("quantity", 0))
            total_return = pack_qty * max(0, lots_left)
            if total_return > 0 and base_id:
                player_manager.add_item_to_inventory(pdata, base_id, total_return)
        elif item_type == "unique": 
            uid = it.get("uid")
            inst = it.get("item")
            if uid and inst: 
                inv = pdata.get("inventory", {}) or {}
                new_uid = uid 
                count = 0
                while new_uid in inv: 
                    count += 1
                    new_uid = f"{uid}_ret_{count}"
                    if count > 5: break 
                
                if new_uid not in inv:
                    inv[new_uid] = inst
                    pdata["inventory"] = inv
                else:
                    logger.error(f"Não foi possível devolver o item único {uid} ao cancelar listagem {lid} (conflito UID).")
                    await context.bot.send_message(chat_id, f"⚠️ Erro ao devolver o item da listagem #{lid}. Contacte um admin.")
        else:
            logger.error(f"Tipo de item desconhecido ou inválido ao cancelar listagem {lid}: {item_type}")
            await context.bot.send_message(chat_id, f"⚠️ Erro ao processar o item da listagem #{lid}. Contacte um admin.")
    else: 
        logger.error(f"Estrutura de item inválida na listagem {lid} ao cancelar: {repr(it)}")
        await context.bot.send_message(chat_id, f"⚠️ Erro crítico ao ler o item da listagem #{lid}. Contacte um admin.")

    await player_manager.save_player_data(user_id, pdata)
    
    # <<< CORREÇÃO 2: REMOVIDO 'await' >>>
    market_manager.delete_listing(lid) 

    await _safe_edit_or_send(q, context, chat_id, f"❌ Listagem #{lid} cancelada e itens devolvidos.", InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market_my")]
    ]))

async def market_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    buyer_id = q.from_user.id
    chat_id = update.effective_chat.id
    
    try:
        lid = int(q.data.replace("market_buy_", ""))
    except (ValueError, AttributeError):
        await q.answer("ID de listagem inválido.", show_alert=True)
        return

    # --- ETAPA 1: Obter a Listagem ---
    listing = market_manager.get_listing(lid) # Síncrono

    if not listing or not listing.get("active"):
        await q.answer("Listagem não está mais ativa.", show_alert=True)
        return
    if int(listing.get("seller_id", 0)) == int(buyer_id):
        await q.answer("Você não pode comprar sua própria listagem.", show_alert=True)
        return

    # --- ETAPA 2: Carregar Jogadores ---
    buyer = await player_manager.get_player_data(buyer_id)
    
    # Verifica se o comprador é premium
    if not player_manager.has_premium_plan(buyer):
         await q.answer("Apenas Apoiadores Premium podem comprar itens.", show_alert=True)
         return
         
    seller_id = listing.get("seller_id")
    seller = None
    if seller_id:
         seller = await player_manager.get_player_data(seller_id)

    if not buyer or not seller:
        if not seller and seller_id:
             logger.error(f"Erro crítico: Vendedor {seller_id} da listagem {lid} não encontrado no DB.")
        await q.answer("Erro ao carregar dados do comprador ou vendedor.", show_alert=True)
        return

    # --- ETAPA 3: CORREÇÃO - Verificar Ouro ANTES ---
    total_price = int(listing.get("unit_price", 0)) * 1 # (Assumindo quantity=1)
    buyer_gold = _gold(buyer) # Usa o helper _gold

    if buyer_gold < total_price:
        await q.answer(f"Ouro insuficiente. Você tem {buyer_gold} 🪙, mas precisa de {total_price} 🪙.", show_alert=True)
        return

    # --- ETAPA 4: Processar a Compra (Atualizar JSON) ---
    try:
        # Tenta "reservar" o item no market_manager
        # (Isto remove o item do JSON)
        updated_listing, total_price_check = market_manager.purchase_listing(
            buyer_id=buyer_id, listing_id=lid, quantity=1 
        )
    except market_manager.MarketError as e:
        await q.answer(str(e), show_alert=True) 
        return
    except Exception as e: 
         logger.error(f"Erro inesperado durante purchase_listing para L{lid} B{buyer_id}: {e}", exc_info=True)
         await q.answer("Ocorreu um erro ao processar a compra.", show_alert=True)
         return

    # --- ETAPA 5: CORREÇÃO - Fazer a Transação e Entrega ---
    # Se chegámos aqui, a compra no JSON foi bem-sucedida.
    # Agora modificamos os dados dos jogadores EM MEMÓRIA.
    
    # 5a. Transferir o Ouro (Usando os helpers _set_gold)
    _set_gold(buyer, buyer_gold - total_price)
    _set_gold(seller, _gold(seller) + total_price)

    # 5b. Entregar o item ao comprador (Usando o 'buyer' original)
    it = listing.get("item") 
    if isinstance(it, dict):
        item_type = it.get("type")
        if item_type == "stack":
            base_id = it.get("base_id")
            pack_qty = int(it.get("qty", 1))
            if base_id:
                player_manager.add_item_to_inventory(buyer, base_id, pack_qty) # < MUDADO
        elif item_type == "unique":
            uid = it.get("uid")
            inst = it.get("item")
            if uid and inst:
                inv = buyer.get("inventory", {}) or {} # < MUDADO
                new_uid = uid 
                count = 0
                while new_uid in inv: 
                     count += 1
                     new_uid = f"{uid}_buy_{count}"
                     if count > 5: break
                
                if new_uid not in inv:
                     inv[new_uid] = inst
                     buyer["inventory"] = inv # < MUDADO
                else:
                     logger.error(f"Não foi possível entregar o item único {uid} da L{lid} (conflito UID).")
                     await context.bot.send_message(chat_id, f"⚠️ Erro CRÍTICO ao entregar o item da compra #{lid}! Contacte um admin.")
    else: 
        logger.error(f"Estrutura de item inválida na listagem {lid} durante a compra: {repr(it)}")
        await context.bot.send_message(chat_id, f"⚠️ Erro CRÍTICO ao processar o item da compra #{lid}! Contacte um admin.")

    # 5c. Atualizar Missões (para 'seller')
    seller["user_id"] = seller_id # Garante que o ID está no dict para o mission_manager
    mission_manager.update_mission_progress(
        seller, # < MUDADO
        event_type="MARKET_SELL",
        details={ "item_id": it.get("base_id") if isinstance(it, dict) else None, "quantity": 1 } 
    )
    clan_id = seller.get("clan_id") # < MUDADO
    if clan_id:
        try:
            await clan_manager.update_guild_mission_progress(
                clan_id=clan_id,
                mission_type='MARKET_SELL',
                details={
                    "item_id": it.get("base_id") if isinstance(it, dict) else None, 
                    "quantity": 1, "gold_value": total_price
                },
                context=context 
            )
        except Exception as e_clan_mission:
             logger.error(f"Erro ao atualizar missão de guilda MARKET_SELL para clã {clan_id}: {e_clan_mission}")

    # 5d. Salvar dados
    await player_manager.save_player_data(buyer_id, buyer) # < MUDADO
    await player_manager.save_player_data(seller_id, seller) # < MUDADO

    # 5e. Confirmação
    remaining_lots = int(updated_listing.get("quantity", 0)) if updated_listing.get("active") else 0
    suffix = f" Restam {remaining_lots} lote(s)." if remaining_lots > 0 else " Não restam lotes."
    await _safe_edit_or_send(q, context, chat_id, f"✅ Compra concluída (#{lid}). {total_price} 🪙 transferidos.{suffix}", InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market_list")]
    ]))

async def market_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = update.effective_chat.id

    # <<< CORREÇÃO 18: Adiciona await >>>
    pdata = await player_manager.get_player_data(user_id) or {}

    try:
        page = int(query.data.split(':')[1])
    except (IndexError, ValueError):
        page = 1

    ITEMS_PER_PAGE = 8
    inv = pdata.get("inventory", {}) or {}
    pclass = _player_class_key(pdata) # Síncrono

    sellable_items = []
    # Loop síncrono sobre o inventário
    for uid, inst in inv.items():
        if isinstance(inst, dict):
            base_id = inst.get("base_id") or inst.get("tpl") or inst.get("id")
            if base_id and base_id not in PREMIUM_BLOCK_LIST:
                sellable_items.append({"type": "unique", "uid": uid, "inst": inst})
    for base_id, qty in inv.items():
        if isinstance(qty, (int, float)) and int(qty) > 0:
            if base_id not in PREMIUM_BLOCK_LIST:
                sellable_items.append({"type": "stack", "base_id": base_id, "qty": int(qty)})

    sellable_items.sort(key=lambda x: x.get('uid', x.get('base_id')))

    start_index = (page - 1) * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    items_for_page = sellable_items[start_index:end_index]

    caption = f"➕ <b>Vender Item</b> (Página {page})\nSelecione um item do seu inventário:\n"
    keyboard_rows = []

    if not sellable_items:
        caption = "Você não tem itens vendáveis no seu inventário."
        keyboard_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")])
    elif not items_for_page:
        caption = "Não há mais itens para mostrar."
        keyboard_rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")])
    else:
        for item in items_for_page:
            if item["type"] == "unique":
                full_line = _render_unique_line_safe(item["inst"], pclass) # Síncrono
                callback_data = f"market_pick_unique_{item['uid']}"
                keyboard_rows.append([InlineKeyboardButton(_cut_middle(full_line, 56), callback_data=callback_data)]) # Síncrono
            else:
                label = f"📦 {_item_label_from_base(item['base_id'])} ({item['qty']}x)" # Síncrono
                callback_data = f"market_pick_stack_{item['base_id']}"
                keyboard_rows.append([InlineKeyboardButton(label, callback_data=callback_data)])

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"market_sell:{page - 1}"))
    if end_index < len(sellable_items):
        nav_buttons.append(InlineKeyboardButton("Próxima ➡️", callback_data=f"market_sell:{page + 1}"))

    if nav_buttons:
        keyboard_rows.append(nav_buttons)

    keyboard_rows.append([InlineKeyboardButton("⬅️ Voltar ao Mercado", callback_data="market_adventurer")])
    await _safe_edit_or_send(query, context, chat_id, caption, InlineKeyboardMarkup(keyboard_rows))

# Em handlers/adventurer_market_handler.py

def _render_price_spinner(price: int) -> InlineKeyboardMarkup:
    price = max(1, int(price))
    return InlineKeyboardMarkup([
        [
            # <<< BOTÃO ADICIONADO >>>
            InlineKeyboardButton("−1k",  callback_data="mktp_dec_1000"), 
            InlineKeyboardButton("−100", callback_data="mktp_dec_100"),
            InlineKeyboardButton("−10",  callback_data="mktp_dec_10"),
            InlineKeyboardButton("−1",   callback_data="mktp_dec_1"),
            InlineKeyboardButton("+1",   callback_data="mktp_inc_1"),
            InlineKeyboardButton("+10",  callback_data="mktp_inc_10"),
            InlineKeyboardButton("+100", callback_data="mktp_inc_100"),
            # <<< BOTÃO ADICIONADO >>>
            InlineKeyboardButton("+1k",  callback_data="mktp_inc_1000"), 
        ],
        [InlineKeyboardButton(f"💰 {price} 🪙", callback_data="noop")],
        [InlineKeyboardButton("✅ Confirmar", callback_data="mktp_confirm")],
        [InlineKeyboardButton("❌ Cancelar",  callback_data="market_cancel_new")]
    ])

async def _show_price_spinner(q, context, chat_id: int, caption_prefix: str = "Defina o preço:"):
    price = max(1, int(context.user_data.get("market_price", 50)))
    kb = _render_price_spinner(price)
    await _safe_edit_or_send(q, context, chat_id, f"{caption_prefix} <b>{price} 🪙</b>", kb)

# Em handlers/adventurer_market_handler.py
# (Cole isto antes de _render_lote_qty_spinner)

# Em handlers/adventurer_market_handler.py

def _render_pack_qty_spinner(qty: int, max_qty: int) -> InlineKeyboardMarkup:
    """Renderiza o spinner para o TAMANHO DO LOTE (Itens por Lote)."""
    qty = max(1, int(qty))
    max_qty = max(1, int(max_qty))
    
    current_qty = max(1, min(int(qty), max_qty))
    
    return InlineKeyboardMarkup([
        [
            # <<< BOTÕES ADICIONADOS >>>
            InlineKeyboardButton("−100", callback_data="mkt_pack_dec_100"),
            InlineKeyboardButton("−10", callback_data="mkt_pack_dec_10"),
            InlineKeyboardButton("−1",  callback_data="mkt_pack_dec_1"),
            InlineKeyboardButton("+1",  callback_data="mkt_pack_inc_1"),
            InlineKeyboardButton("+10", callback_data="mkt_pack_inc_10"),
            # <<< BOTÕES ADICIONADOS >>>
            InlineKeyboardButton("+100", callback_data="mkt_pack_inc_100"),
        ],
        [InlineKeyboardButton(f"📦 {current_qty} / {max_qty} Itens por Lote", callback_data="noop")],
        [InlineKeyboardButton("✅ Confirmar Tamanho do Lote", callback_data="mkt_pack_confirm")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="market_cancel_new")]
    ])

async def _show_pack_qty_spinner(q, context, chat_id: int, caption_prefix: str = "Defina quantos itens por lote:"):
    """
    Mostra o spinner de TAMANHO do lote (itens por lote).
    """
    pending = context.user_data.get("market_pending")
    if not pending or pending.get("type") != "stack":
        await market_cancel_new(q, context)
        return

    qty_have = int(pending.get("qty_have", 0)) # Total que tens (ex: 100)
    
    # Pega a quantidade atual do spinner (default 1)
    current_pack_qty = max(1, int(pending.get("qty", 1))) # 'qty' agora é o pack_qty
    current_pack_qty = min(current_pack_qty, qty_have)
    
    # Atualiza o pending com o valor atual
    pending["qty"] = current_pack_qty
    context.user_data["market_pending"] = pending

    kb = _render_pack_qty_spinner(current_pack_qty, qty_have)
    
    item_label = _item_label_from_base(pending["base_id"])
    caption = (
        f"Item: <b>{item_label}</b> (Você tem {qty_have} no total)\n\n"
        f"{caption_prefix}"
    )
    
    await _safe_edit_or_send(q, context, chat_id, caption, kb)

async def market_pack_qty_spin(update, context):
    """Handler para os botões +1, -1, +10 do spinner de TAMANHO DE LOTE."""
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    
    pending = context.user_data.get("market_pending")
    if not pending:
        await market_cancel_new(update, context); return

    cur = max(1, int(pending.get("qty", 1)))
    max_qty = max(1, int(pending.get("qty_have", 1)))
    
    action = q.data
    if action.startswith("mkt_pack_inc_"):
        step = int(action.split("_")[-1])
        cur = min(max_qty, cur + step)
    elif action.startswith("mkt_pack_dec_"):
        step = int(action.split("_")[-1])
        cur = max(1, cur - step)
        
    pending["qty"] = cur
    context.user_data["market_pending"] = pending # Salva a atualização

    # Atualiza a mensagem
    item_label = _item_label_from_base(pending["base_id"])
    caption = (
        f"Item: <b>{item_label}</b> (Você tem {max_qty} no total)\n\n"
        f"Defina quantos itens por lote:"
    )
    kb = _render_pack_qty_spinner(cur, max_qty)
    await _safe_edit_or_send(q, context, chat_id, caption, kb)

async def market_pack_qty_confirm(update, context):
    """Confirma o TAMANHO do lote e avança para o spinner de QUANTIDADE de lotes."""
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    
    # O tamanho do lote (pack_qty) já está em context.user_data["market_pending"]["qty"]
    
    # Prepara o spinner de *quantidade de lotes* (default 1)
    context.user_data["market_lote_qty"] = 1 
    
    await _show_lote_qty_spinner(q, context, chat_id, "Defina a <b>quantidade de lotes</b>:")


# Em handlers/adventurer_market_handler.py

def _render_lote_qty_spinner(qty: int, max_qty: int) -> InlineKeyboardMarkup:
    """Renderiza o spinner para a QUANTIDADE DE LOTES."""
    qty = max(1, int(qty))
    max_qty = max(1, int(max_qty))
    
    current_qty = max(1, min(int(qty), max_qty))
    
    return InlineKeyboardMarkup([
        [
            # <<< BOTÕES ADICIONADOS >>>
            InlineKeyboardButton("−100", callback_data="mkt_lote_dec_100"),
            InlineKeyboardButton("−10", callback_data="mkt_lote_dec_10"),
            InlineKeyboardButton("−1",  callback_data="mkt_lote_dec_1"),
            InlineKeyboardButton("+1",  callback_data="mkt_lote_inc_1"),
            InlineKeyboardButton("+10", callback_data="mkt_lote_inc_10"),
            # <<< BOTÕES ADICIONADOS >>>
            InlineKeyboardButton("+100", callback_data="mkt_lote_inc_100"),
        ],
        [InlineKeyboardButton(f"📦 {current_qty} / {max_qty} Lotes", callback_data="noop")],
        [InlineKeyboardButton("✅ Confirmar Lotes", callback_data="mkt_lote_confirm")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="market_cancel_new")]
    ])

async def _show_lote_qty_spinner(q, context, chat_id: int, caption_prefix: str = "Defina a quantidade de lotes:"):
    """
    Mostra o spinner de quantidade de lotes, calculando o máximo
    de lotes que o jogador pode vender.
    """
    pending = context.user_data.get("market_pending")
    if not pending or pending.get("type") != "stack":
        await market_cancel_new(q, context) # Cancela se o estado for inválido
        return

    qty_have = int(pending.get("qty_have", 0))  # Total de itens que tem (ex: 100)
    pack_qty = int(pending.get("qty", 1))     # Itens por lote (ex: 10)
    
    # Calcula o máximo de lotes que pode vender
    max_lotes = max(1, qty_have // pack_qty)
    
    # Guarda o máximo no user_data para o spin handler usar
    context.user_data["market_lote_max"] = max_lotes
    
    # Pega a quantidade atual do spinner (default 1)
    current_lotes = max(1, int(context.user_data.get("market_lote_qty", 1)))
    # Garante que não excede o máximo
    current_lotes = min(current_lotes, max_lotes)
    context.user_data["market_lote_qty"] = current_lotes

    kb = _render_lote_qty_spinner(current_lotes, max_lotes)
    
    # Mostra o item sendo vendido
    item_label = _item_label_from_base(pending["base_id"])
    caption = (
        f"Item: <b>{item_label} ×{pack_qty}</b> (Você tem {qty_have} no total)\n\n"
        f"{caption_prefix}"
    )
    
    await _safe_edit_or_send(q, context, chat_id, caption, kb)

async def market_lote_qty_spin(update, context):
    """Handler para os botões +1, -1, +10, -10 do spinner de LOTES."""
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id

    cur = max(1, int(context.user_data.get("market_lote_qty", 1)))
    max_qty = max(1, int(context.user_data.get("market_lote_max", 1)))
    
    action = q.data
    if action.startswith("mkt_lote_inc_"):
        step = int(action.split("_")[-1])
        cur = min(max_qty, cur + step) # Não pode passar do máximo
    elif action.startswith("mkt_lote_dec_"):
        step = int(action.split("_")[-1])
        cur = max(1, cur - step) # Não pode ser menor que 1
        
    context.user_data["market_lote_qty"] = cur

    # Simplesmente atualiza a mensagem
    pending = context.user_data.get("market_pending")
    item_label = _item_label_from_base(pending["base_id"])
    pack_qty = int(pending.get("qty", 1))
    qty_have = int(pending.get("qty_have", 0))

    caption = (
        f"Item: <b>{item_label} ×{pack_qty}</b> (Você tem {qty_have} no total)\n\n"
        f"Defina a quantidade de lotes:"
    )
    kb = _render_lote_qty_spinner(cur, max_qty)
    await _safe_edit_or_send(q, context, chat_id, caption, kb)


async def market_lote_qty_confirm(update, context):
    """Confirma a quantidade de lotes e avança para o spinner de PREÇO."""
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    
    # A quantidade de lotes já está em context.user_data["market_lote_qty"]
    # Apenas avançamos para o spinner de preço
    
    pending = context.user_data.get("market_pending")
    item_label = _item_label_from_base(pending["base_id"])
    pack_qty = int(pending.get("qty", 1))
    lote_qty = int(context.user_data.get("market_lote_qty", 1))

    # Preço inicial (podes mudar)
    context.user_data["market_price"] = 10 
    
    caption_prefix = (
        f"Item: <b>{item_label} ×{pack_qty}</b>\n"
        f"Lotes: <b>{lote_qty}</b>\n\n"
        f"Defina o <b>preço por lote</b>:"
    )
    
    await _show_price_spinner(q, context, chat_id, caption_prefix)

# =================================================================
# <<< CORREÇÃO DE INDENTAÇÃO COMEÇA AQUI >>>
# Todas as funções abaixo estavam com espaços a mais
# =================================================================

async def market_price_spin(update, context):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id

    cur = max(1, int(context.user_data.get("market_price", 50)))
    action = q.data
    if action.startswith("mktp_inc_"):
        step = int(action.split("_")[-1]); cur += step
    elif action.startswith("mktp_dec_"):
        step = int(action.split("_")[-1]); cur = max(1, cur - step)
    context.user_data["market_price"] = cur

    kb = _render_price_spinner(cur)
    await _safe_edit_or_send(q, context, chat_id, f"Defina o preço: <b>{cur} 🪙</b>", kb)

async def market_price_confirm(update, context):
    q = update.callback_query
    await q.answer()
    price = max(1, int(context.user_data.get("market_price", 1)))
    await market_finalize_listing(update, context, price)

async def market_pick_unique(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id
    uid = q.data.replace("market_pick_unique_", "")

    # <<< CORREÇÃO 19: Adiciona await >>>
    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {}) or {}
    inst = inv.get(uid)
    if not isinstance(inst, dict):
        await q.answer("Item não encontrado.", show_alert=True); return

    base_id = inst.get("base_id") or inst.get("tpl") or inst.get("id")
    if base_id in PREMIUM_BLOCK_LIST:
        await q.answer(PREMIUM_BLOCK_MSG, show_alert=True, parse_mode="HTML")
        return

    context.user_data["market_pending"] = {"type": "unique", "uid": uid, "item": inst}
    
    # Remove o item do inventário ANTES de mostrar o preço
    if uid in inv:
        del inv[uid]
        pdata["inventory"] = inv
        # <<< CORREÇÃO 20: Adiciona await >>>
        await player_manager.save_player_data(user_id, pdata)
    else:
        # Se o item já não estava no inventário (talvez removido em outra aba?), avisa erro.
        await q.answer("Erro: Item não encontrado no inventário.", show_alert=True)
        # Limpa o estado pendente e retorna ao menu de venda
        context.user_data.pop("market_pending", None)
        await market_sell(update, context)
        return

    context.user_data["market_price"] = 50 # Preço inicial
    # <<< CORREÇÃO 21: Adiciona await >>>
    await _show_price_spinner(q, context, chat_id, "Defina o <b>preço</b> deste item único:")

# Em handlers/adventurer_market_handler.py

async def market_pick_stack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id
    base_id = q.data.replace("market_pick_stack_", "")

    if base_id in PREMIUM_BLOCK_LIST:
        await q.answer(PREMIUM_BLOCK_MSG, show_alert=True, parse_mode="HTML")
        return

    pdata = await player_manager.get_player_data(user_id)
    inv = pdata.get("inventory", {}) or {}
    qty_have = int(inv.get(base_id, 0))
    if qty_have <= 0:
        await q.answer("Quantidade insuficiente.", show_alert=True); return

    # Prepara o estado pendente
    context.user_data["market_pending"] = {
        "type": "stack", 
        "base_id": base_id, 
        "qty_have": qty_have,
        "qty": 1  # 'qty' agora é o "tamanho do lote", começa em 1
    }
    
    # --- MUDANÇA PRINCIPAL ---
    # Chama o novo spinner de TAMANHO de lote
    await _show_pack_qty_spinner(
        q, context, chat_id,
        f"Quanto deseja colocar por <b>lote</b> em <b>{_item_label_from_base(base_id)}</b>?"
    )

async def market_choose_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    pending = context.user_data.get("market_pending") or {}
    if pending.get("type") != "stack":
        await market_cancel_new(update, context)
        return

    qty_have = int(pending.get("qty_have", 0))
    data = q.data
    if data == "market_qty_all":
        # Se escolheu 'Tudo', o tamanho do lote é a quantidade total
        # e o número de lotes será 1.
        qty = qty_have
    else:
        try:
            qty = int(data.replace("market_qty_", ""))
            if qty <= 0 or qty > qty_have:
                 await q.answer("Quantidade inválida.", show_alert=True); return
        except ValueError:
             await q.answer("Quantidade inválida.", show_alert=True); return

    pending["qty"] = qty # 'qty' aqui é o TAMANHO DO LOTE (pack_qty)
    context.user_data["market_pending"] = pending
    
    # Prepara o spinner de quantidade de lotes (default 1)
    context.user_data["market_lote_qty"] = 1 

    # --- MUDANÇA AQUI ---
    # Em vez de chamar o spinner de PREÇO, chamamos o spinner de LOTES
    await _show_lote_qty_spinner(q, context, chat_id, "Defina a <b>quantidade de lotes</b>:")

async def market_cancel_new(update, context):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = update.effective_chat.id

    pending = context.user_data.pop("market_pending", None)
    if pending and pending.get("type") == "unique":
        # <<< CORREÇÃO 25: Adiciona await >>>
        pdata = await player_manager.get_player_data(user_id)
        inv = pdata.get("inventory", {}) or {}
        uid = pending["uid"]
        new_uid = uid if uid not in inv else f"{uid}_back"
        inv[new_uid] = pending["item"]
        pdata["inventory"] = inv
        # <<< CORREÇÃO 26: Adiciona await >>>
        await player_manager.save_player_data(user_id, pdata)

    context.user_data.pop("market_price", None)
    # <<< CORREÇÃO 27: Adiciona await >>>
    await _safe_edit_or_send(q, context, chat_id, "Criação de listagem cancelada.", InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]
    ]))

# Em handlers/adventurer_market_handler.py

async def market_finalize_listing(update: Update, context: ContextTypes.DEFAULT_TYPE, price: int):
    logger.info("[market_finalize_listing] start price=%s has_cb=%s",
                 price, bool(update.callback_query))

    query_obj = None 
    if update.callback_query:
        user_id = update.callback_query.from_user.id
        chat_id = update.effective_chat.id
        query_obj = update.callback_query
    else:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

    pending = context.user_data.get("market_pending")
    if not pending:
        logger.warning("[market_finalize_listing] NADA pendente em user_data")
        await context.bot.send_message(chat_id=chat_id, text="Nada pendente para vender. Volte e selecione o item novamente.")
        return

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
         await context.bot.send_message(chat_id=chat_id, text="Erro ao carregar dados do jogador.")
         context.user_data.pop("market_pending", None)
         context.user_data.pop("market_price", None)
         context.user_data.pop("market_lote_qty", None) # Limpa novo estado
         context.user_data.pop("market_lote_max", None) # Limpa novo estado
         return

    inv = pdata.get("inventory", {}) or {}

    try:
        # --- LÓGICA DE LOTES (lote_qty) ---
        # Para 'unique', a quantidade de lotes é sempre 1.
        # Para 'stack', lemos o valor do user_data.
        lote_qty_to_sell = 1
        if pending["type"] == "stack":
            lote_qty_to_sell = max(1, int(context.user_data.get("market_lote_qty", 1)))
        
        
        if pending["type"] == "unique":
            base_id = (pending["item"] or {}).get("base_id")
            if base_id in PREMIUM_BLOCK_LIST:
                await context.bot.send_message(chat_id=chat_id, text=PREMIUM_BLOCK_MSG, parse_mode="HTML")
                inv = pdata.get("inventory", {}) or {}
                uid = pending["uid"]
                new_uid = uid if uid not in inv else f"{uid}_back_evol"
                inv[new_uid] = pending["item"]
                pdata["inventory"] = inv
                await player_manager.save_player_data(user_id, pdata)
                
                # Limpa estado e sai
                context.user_data.pop("market_pending", None)
                context.user_data.pop("market_price", None)
                return 

            item_payload = {"type": "unique", "uid": pending["uid"], "item": pending["item"]}
            
            # Para 'unique', 'quantity' (nº de lotes) é sempre 1
            listing = market_manager.create_listing(
                seller_id=user_id, 
                item_payload=item_payload, 
                unit_price=price, 
                quantity=1 # Fixo
            )
        
        else: # type == "stack"
            base_id = pending["base_id"]
            if base_id in PREMIUM_BLOCK_LIST:
                await context.bot.send_message(chat_id=chat_id, text=PREMIUM_BLOCK_MSG, parse_mode="HTML")
                context.user_data.pop("market_pending", None)
                context.user_data.pop("market_price", None)
                context.user_data.pop("market_lote_qty", None)
                context.user_data.pop("market_lote_max", None)
                return

            pack_qty = int(pending.get("qty", 0)) # Itens por lote (ex: 10)
            
            # --- MUDANÇA AQUI ---
            # Total a remover = (Itens por Lote) * (Nº de Lotes)
            total_to_remove = pack_qty * lote_qty_to_sell 
            
            have = int((pdata.get("inventory", {}) or {}).get(base_id, 0))
            
            # Verifica se tem o total_to_remove
            if total_to_remove <= 0 or have < total_to_remove:
                logger.warning("[market_finalize_listing] qty inválida: total_remove=%s (pack=%s lote_qty=%s) have=%s",
                             total_to_remove, pack_qty, lote_qty_to_sell, have)
                await context.bot.send_message(chat_id=chat_id, text="Quantidade inválida ou insuficiente.")
                context.user_data.pop("market_pending", None)
                context.user_data.pop("market_price", None)
                context.user_data.pop("market_lote_qty", None)
                context.user_data.pop("market_lote_max", None)
                return

            # Remove do inventário
            inv = pdata.get("inventory", {}) or {}
            inv[base_id] = have - total_to_remove # Remove o total
            if inv[base_id] <= 0:
                 del inv[base_id]
            pdata["inventory"] = inv
            
            await player_manager.save_player_data(user_id, pdata)

            item_payload = {"type": "stack", "base_id": base_id, "qty": pack_qty}
            
            # --- MUDANÇA AQUI ---
            # Passa a quantidade de lotes (lote_qty_to_sell) para o market_manager
            listing = market_manager.create_listing(
                seller_id=user_id, 
                item_payload=item_payload, 
                unit_price=price, 
                quantity=lote_qty_to_sell # Passa o nº de lotes
            )

        # Limpa o estado pendente
        context.user_data.pop("market_pending", None)
        context.user_data.pop("market_price", None)
        context.user_data.pop("market_lote_qty", None) # Limpa novo estado
        context.user_data.pop("market_lote_max", None) # Limpa novo estado

        text = f"✅ Listagem #{listing['id']} criada."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("👤 Minhas Listagens", callback_data="market_my")],
                                     [InlineKeyboardButton("⬅️ Voltar", callback_data="market_adventurer")]])

        if query_obj:
            await _safe_edit_or_send(query_obj, context, chat_id, text, kb)
        else:
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=kb, parse_mode='HTML')

        logger.info("[market_finalize_listing] OK -> #%s", listing["id"])

    except Exception as e:
        logger.exception("[market_finalize_listing] erro: %s", e)
        try:
             await context.bot.send_message(chat_id=chat_id, text="Falha ao criar a listagem. Tente novamente.")
        except Exception:
             pass 

        if pending and pending.get("type") == "unique":
             try:
                 pdata_reloaded = await player_manager.get_player_data(user_id)
                 inv_reloaded = (pdata_reloaded or {}).get("inventory", {}) or {}
                 uid = pending["uid"]
                 if uid not in inv_reloaded:
                      new_uid = uid 
                      count = 0
                      while new_uid in inv_reloaded:
                           count += 1
                           new_uid = f"{uid}_fail_ret_{count}"
                           if count > 5: break
                      
                      if new_uid not in inv_reloaded:
                           inv_reloaded[new_uid] = pending["item"]
                           pdata_reloaded["inventory"] = inv_reloaded
                           await player_manager.save_player_data(user_id, pdata_reloaded)
                           logger.info(f"Item único {uid} (como {new_uid}) devolvido após falha ao criar listagem.")
                      else:
                            logger.error(f"Não foi possível devolver o item único {uid} após falha (conflito de UID mesmo com sufixo).")
                 else:
                      logger.warning(f"Item único {uid} já estava no inventário ao tentar devolver após falha.")
                 
             except Exception as e_ret:
                 logger.error(f"Erro CRÍTICO ao tentar devolver item único {pending.get('uid')} após falha: {e_ret}")
        
        context.user_data.pop("market_pending", None) 
        context.user_data.pop("market_price", None) 
        context.user_data.pop("market_lote_qty", None) # Limpa novo estado
        context.user_data.pop("market_lote_max", None) # Limpa novo estado

# Em: handlers/adventurer_market_handler.py
# (No final do ficheiro)

# ==============================
#  Handlers (exports para este arquivo)
# ==============================
market_adventurer_handler = CallbackQueryHandler(market_adventurer, pattern=r'^market_adventurer$')
market_list_handler = CallbackQueryHandler(market_list, pattern=r'^market_list$')
market_my_handler = CallbackQueryHandler(market_my, pattern=r'^market_my$')
market_sell_handler = CallbackQueryHandler(market_sell, pattern=r'^market_sell(:(\d+))?$')
market_buy_handler = CallbackQueryHandler(market_buy, pattern=r'^market_buy_\d+$')
market_cancel_handler = CallbackQueryHandler(market_cancel, pattern=r'^market_cancel_\d+$')
market_pick_unique_handler= CallbackQueryHandler(market_pick_unique, pattern=r'^market_pick_unique_')
market_pick_stack_handler = CallbackQueryHandler(market_pick_stack, pattern=r'^market_pick_stack_')

# <<< market_qty_handler FOI REMOVIDO >>>

# Handlers do Spinner de TAMANHO de Lote (NOVO)
market_pack_qty_spin_handler = CallbackQueryHandler(market_pack_qty_spin, pattern=r'^mkt_pack_(inc|dec)_[0-9]+$')
market_pack_qty_confirm_handler = CallbackQueryHandler(market_pack_qty_confirm, pattern=r'^mkt_pack_confirm$')

# Handlers do Spinner de Preço
market_price_spin_handler = CallbackQueryHandler(market_price_spin,    pattern=r'^mktp_(inc|dec)_[0-9]+$')
market_price_confirm_handler = CallbackQueryHandler(market_price_confirm, pattern=r'^mktp_confirm$')

# Handlers do Spinner de Lotes (existente)
market_lote_qty_spin_handler = CallbackQueryHandler(market_lote_qty_spin, pattern=r'^mkt_lote_(inc|dec)_[0-9]+$')
market_lote_qty_confirm_handler = CallbackQueryHandler(market_lote_qty_confirm, pattern=r'^mkt_lote_confirm$')

# Handler de Cancelar Venda
market_cancel_new_handler = CallbackQueryHandler(market_cancel_new, pattern=r'^market_cancel_new$')
