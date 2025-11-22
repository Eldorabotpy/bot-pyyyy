# handlers/profession_handler.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from modules import player_manager, game_data
from modules import player_manager, game_data, crafting_registry
# ==============================================================================
# CONFIGURAÇÃO DE TEXTOS E DETALHES (ATUALIZADO COM SUA LISTA OFICIAL)
# ==============================================================================
PROFESSION_INFO = {
    # --- COLETA (GATHERING) ---
    "lenhador": {
        "emoji": "🪓",
        "title": "Lenhador (Lumberjack)",
        "desc": "Conhecedores da floresta que extraem madeiras nobres.",
        "bonuses": ["Extração eficiente de madeira.", "Encontra tipos raros de toras."],
        "mechanic": "Foca em Força e Constituição.",
        "guide": (
            "🪓 <b>Guia do Lenhador:</b>\n\n"
            "📍 <b>Onde:</b> Florestas ou Locais de Coleta.\n"
            "🌲 <b>O que fazer:</b>\n"
            "1. <b>Cortar:</b> Use seu machado para obter 'Madeira' e toras raras.\n"
            "2. <b>Fornecer:</b> Venda madeira bruta para o mercado ou processe com outros artesãos."
        )
    },
    "minerador": {
        "emoji": "⛏️",
        "title": "Minerador (Miner)",
        "desc": "Trabalhadores robustos que extraem minérios das profundezas.",
        "bonuses": ["Extração de Pedra e Ferro.", "Chance de achar gemas brutas."],
        "mechanic": "Foca em Força.",
        "guide": (
            "⛏️ <b>Guia do Minerador:</b>\n\n"
            "📍 <b>Onde:</b> Cavernas e Minas.\n"
            "💎 <b>O que fazer:</b>\n"
            "1. <b>Minerar:</b> Obtenha 'Pedra' e 'Minério de Ferro'.\n"
            "2. <b>Fornecer:</b> Minérios são essenciais para Fundidores criarem barras."
        )
    },
    "colhedor": {
        "emoji": "🌿",
        "title": "Colhedor (Harvester)",
        "desc": "Especialistas em identificar e colher fibras naturais e ervas.",
        "bonuses": ["Colheita de Linho e Fibras.", "Encontra sementes raras."],
        "mechanic": "Foca em Destreza e Sabedoria.",
        "guide": (
            "🌿 <b>Guia do Colhedor:</b>\n\n"
            "📍 <b>Onde:</b> Campos e Planícies.\n"
            "🌾 <b>O que fazer:</b>\n"
            "1. <b>Colher:</b> Obtenha 'Linho' e plantas têxteis.\n"
            "2. <b>Fornecer:</b> O linho é a matéria-prima essencial para os Alfaiates."
        )
    },
    "esfolador": {
        "emoji": "🔪",
        "title": "Esfolador (Skinner)",
        "desc": "Mestres em obter recursos de criaturas abatidas.",
        "bonuses": ["Obtenção de Penas e Peles.", "Aproveitamento de carcaças."],
        "mechanic": "Foca em Destreza.",
        "guide": (
            "🔪 <b>Guia do Esfolador:</b>\n\n"
            "📍 <b>Onde:</b> Zonas de Caça (após derrotar monstros).\n"
            "🦅 <b>O que fazer:</b>\n"
            "1. <b>Esfolar:</b> Obtenha 'Pena', peles e couros brutos.\n"
            "2. <b>Fornecer:</b> Venda penas para flechas e peles para Curtidores."
        )
    },
    "alquimista": { # Na sua lista é Gathering (coleta sangue/ingredientes)
        "emoji": "⚗️",
        "title": "Alquimista (Gatherer)",
        "desc": "Estudiosos que coletam essências vitais e fluidos raros.",
        "bonuses": ["Coleta segura de Sangue e Venenos.", "Identificação de fluidos."],
        "mechanic": "Foca em Inteligência.",
        "guide": (
            "⚗️ <b>Guia do Alquimista:</b>\n\n"
            "📍 <b>Onde:</b> Pântanos e Zonas Mágicas.\n"
            "🩸 <b>O que fazer:</b>\n"
            "1. <b>Extrair:</b> Colete 'Sangue' e essências de monstros.\n"
            "2. <b>Estudar:</b> Prepare ingredientes base para poções poderosas."
        )
    },

    # --- PRODUÇÃO (CRAFTING) ---
    "ferreiro": {
        "emoji": "🔨",
        "title": "Ferreiro (Blacksmith)",
        "desc": "Forjam armaduras pesadas e escudos metálicos.",
        "bonuses": ["Criação de Armaduras de Placas.", "Reparos de itens de metal."],
        "mechanic": "Foca em Força.",
        "guide": (
            "🔨 <b>Guia do Ferreiro:</b>\n\n"
            "📍 <b>Local:</b> Forja .\n"
            "🛡️ <b>O que fazer:</b>\n"
            "1. <b>Forjar:</b> Use Barras de Ferro para criar Capacetes e Peitorais.\n"
            "2. <b>Requisito:</b> Precisa de 'Barra de Ferro' (feita pelo Fundidor)."
        )
    },
    "armeiro": {
        "emoji": "⚔️",
        "title": "Armeiro (Weaponsmith)",
        "desc": "Especialistas dedicados exclusivamente à criação de armas letais.",
        "bonuses": ["Criação de Espadas e Machados.", "Afiação de lâminas."],
        "mechanic": "Foca em Força e Precisão.",
        "guide": (
            "⚔️ <b>Guia do Armeiro:</b>\n\n"
            "📍 <b>Local:</b> Forja de Armas .\n"
            "🗡️ <b>O que fazer:</b>\n"
            "1. <b>Criar:</b> Forje Espadas, Machados e Lanças.\n"
            "2. <b>Materiais:</b> Usa Barras de Ferro, Madeira e Couro."
        )
    },
    "alfaiate": {
        "emoji": "🧵",
        "title": "Alfaiate (Tailor)",
        "desc": "Mestres dos tecidos que criam roupas leves e mantos mágicos.",
        "bonuses": ["Criação de Robes e Capas.", "Trabalho com Linho e Seda."],
        "mechanic": "Foca em Destreza e Inteligência.",
        "guide": (
            "🧵 <b>Guia do Alfaiate:</b>\n\n"
            "📍 <b>Local:</b> Ateliê .\n"
            "👕 <b>O que fazer:</b>\n"
            "1. <b>Costurar:</b> Use Linho para criar Túnicas e Chapéus.\n"
            "2. <b>Requisito:</b> Precisa de 'Linho' (colhido pelo Colhedor)."
        )
    },
    "joalheiro": {
        "emoji": "💍",
        "title": "Joalheiro (Jeweler)",
        "desc": "Artesãos delicados que trabalham com gemas e metais preciosos.",
        "bonuses": ["Criação de Anéis e Amuletos.", "Lapidação de gemas."],
        "mechanic": "Foca em Destreza e Sorte.",
        "guide": (
            "💍 <b>Guia do Joalheiro:</b>\n\n"
            "📍 <b>Local:</b> Bancada de Joias .\n"
            "💎 <b>O que fazer:</b>\n"
            "1. <b>Criar:</b> Produza acessórios que dão status extras.\n"
            "2. <b>Materiais:</b> Usa metais raros e pedras preciosas."
        )
    },
    "curtidor": {
        "emoji": "🧥",
        "title": "Curtidor (Tanner)",
        "desc": "Processam peles brutas para criar couro utilizável.",
        "bonuses": ["Refino de Peles em Couro.", "Criação de armaduras leves de couro."],
        "mechanic": "Foca em Constituição.",
        "guide": (
            "🧥 <b>Guia do Curtidor:</b>\n\n"
            "📍 <b>Local:</b> Curtume .\n"
            "🐂 <b>O que fazer:</b>\n"
            "1. <b>Processar:</b> Transforme peles/penas (do Esfolador) em Couro.\n"
            "2. <b>Criar:</b> Produza Botas e Luvas de couro."
        )
    },
    "fundidor": {
        "emoji": "🔥",
        "title": "Fundidor (Smelter)",
        "desc": "Trabalham com calor extremo para purificar minérios.",
        "bonuses": ["Derretimento de Minério em Barras.", "Purificação de metais."],
        "mechanic": "Foca em Resistência.",
        "guide": (
            "🔥 <b>Guia do Fundidor:</b>\n\n"
            "📍 <b>Local:</b> Fundição.\n"
            "🧱 <b>O que fazer:</b>\n"
            "1. <b>Fundir:</b> Transforme 'Minério de Ferro' (do Minerador) em 'Barra de Ferro'.\n"
            "2. <b>Fornecer:</b> As barras são a base para Ferreiros e Armeiros."
        )
    }
}

def _get_prof_info(key: str):
    key_lower = str(key).lower().strip()
    default = {
        "emoji": "💼",
        "title": key.capitalize(),
        "desc": "Profissão de produção.",
        "bonuses": [],
        "mechanic": "Padrão.",
        "guide": f"💼 <b>Guia de {key.capitalize()}:</b>\nUse /craft para ver receitas."
    }
    # Se não achar a profissão exata, tenta buscar na lista completa do game_data para não quebrar
    if key_lower not in PROFESSION_INFO:
        prof_data = (game_data.PROFESSIONS_DATA or {}).get(key_lower)
        if prof_data:
            default['title'] = prof_data.get('display_name', key.capitalize())
            return default
            
    return PROFESSION_INFO.get(key_lower, default)

# ==============================================================================
# NOVA FUNÇÃO: GERADOR DE LISTA DE RECEITAS
# ==============================================================================
def _get_recipes_text_for_profession(prof_key: str) -> str:
    """
    Busca no crafting_registry todas as receitas dessa profissão e monta uma lista.
    """
    all_recs = crafting_registry.all_recipes()
    if not all_recs:
        return "\n<i>(Nenhuma receita encontrada no sistema ainda)</i>"

    # Filtra receitas desta profissão
    my_recs = []
    for rid, rdata in all_recs.items():
        if rdata.get('profession') == prof_key:
            my_recs.append(rdata)

    if not my_recs:
        return "\n🚫 <i>Nenhuma receita disponível no momento.</i>"

    # Ordena por nível (Level 1 primeiro, depois Level 2...)
    my_recs.sort(key=lambda x: int(x.get('level_req', 1)))

    txt = "\n📜 <b>Receitas Conhecidas:</b>\n"
    
    # Lista as receitas (Limitamos a 15 para não ficar gigante se tiver muitas)
    for rec in my_recs[:15]:
        lvl = rec.get('level_req', 1)
        name = rec.get('display_name', 'Item Desconhecido')
        emoji = rec.get('emoji', '🔹')
        
        # Formato: [Nv. 1] 🧥 Couro Simples
        txt += f"• <code>[Nv. {lvl}]</code> {emoji} {name}\n"
        
    if len(my_recs) > 15:
        txt += f"<i>...e mais {len(my_recs) - 15} receitas.</i>"
        
    return txt

# ==============================================================================
# HANDLERS (Safe Edit e Menus mantidos)
# ==============================================================================

async def _safe_edit_or_send(query, context, chat_id, text, reply_markup=None, parse_mode='HTML'):
    # (Mesma função auxiliar de antes)
    try:
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except Exception: pass
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode); return
    except Exception: pass
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

async def show_profession_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # (Mesmo código de antes, sem alterações na lógica)
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    chat_id = q.message.chat_id

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        await _safe_edit_or_send(q, context, chat_id, "❌ Erro: Use /start.")
        return

    # JÁ TEM PROFISSÃO
    if (pdata.get('profession') or {}).get('type'):
        cur = pdata['profession']['type']
        info = _get_prof_info(cur)
        level = pdata['profession'].get('level', 1)
        xp = pdata['profession'].get('xp', 0)
        
        txt = (
            f"💼 <b>Sua Profissão: {info['title']}</b>\n"
            f"Nível: {level} | XP: {xp}\n\n"
            f"<i>{info['desc']}</i>"
        )
        
        kb = [
            [InlineKeyboardButton("❓ Guia & Receitas", callback_data=f"job_guide_{cur}")],
            [InlineKeyboardButton("👤 Voltar ao Personagem", callback_data="profile")]
        ]
        await _safe_edit_or_send(q, context, chat_id, txt, InlineKeyboardMarkup(kb))
        return

    # ESCOLHER PROFISSÃO
    title = "💼 <b>Guilda das Profissões</b>\nEscolha seu caminho:"
    kb = []
    for key, data in (game_data.PROFESSIONS_DATA or {}).items():
        info = _get_prof_info(key)
        display = f"{info['emoji']} {info['title']}"
        kb.append([InlineKeyboardButton(display, callback_data=f"job_view_{key}")])
    
    kb.append([InlineKeyboardButton("⬅️ Voltar", callback_data="profile")])
    await _safe_edit_or_send(q, context, chat_id, title, InlineKeyboardMarkup(kb))

async def view_profession_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # (Mesmo código de antes)
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    prof_key = data.replace("job_view_", "")
    info = _get_prof_info(prof_key)
    
    # Aqui também podemos mostrar uma prévia das receitas se quiser, 
    # mas para não poluir, mantemos só os bônus.
    bonuses_txt = "\n".join([f"• {b}" for b in info.get('bonuses', [])])
    
    text = (
        f"{info['emoji']} <b>{info['title']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{info['desc']}\n\n"
        f"✨ <b>Vantagens:</b>\n{bonuses_txt}\n\n"
        f"⚙️ <b>Mecânica:</b> {info['mechanic']}\n\n"
        f"⚠️ <i>Tem certeza? Mudar depois custa caro!</i>"
    )
    kb = [[InlineKeyboardButton("⬅️ Voltar", callback_data="job_menu"), InlineKeyboardButton("✅ Confirmar", callback_data=f"job_confirm_{prof_key}")]]
    await _safe_edit_or_send(q, context, q.message.chat_id, text, InlineKeyboardMarkup(kb))

async def confirm_profession_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # (Mesmo código de antes)
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    data = q.data or ""
    prof_key = data.replace("job_confirm_", "")
    
    pdata = await player_manager.get_player_data(user_id)
    if (pdata.get('profession') or {}).get('type'):
        await show_profession_menu(update, context); return

    pdata['profession'] = {"type": prof_key, "level": 1, "xp": 0}
    await player_manager.save_player_data(user_id, pdata)

    info = _get_prof_info(prof_key)
    txt = f"🎉 <b>Parabéns! Agora você é um {info['title']}!</b>\nClique abaixo para ver o que você pode criar."
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("❓ Guia & Receitas", callback_data=f"job_guide_{prof_key}")], [InlineKeyboardButton("👤 Perfil", callback_data="profile")]])
    await _safe_edit_or_send(q, context, q.message.chat_id, txt, kb)

async def show_profession_guide_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    HANDLER MODIFICADO: Agora busca receitas dinamicamente!
    """
    q = update.callback_query
    await q.answer()
    
    data = q.data or ""
    # Extrai a profissão da callback (ex: job_guide_curtidor)
    prof_key = data.replace("job_guide_", "")
    
    # 1. Pega o texto estático (Local, Dicas, Descrição)
    info = _get_prof_info(prof_key)
    base_text = info.get('guide', f"Guia de {prof_key}.")
    
    # 2. Gera a lista de receitas dinamicamente
    recipes_text = _get_recipes_text_for_profession(prof_key)
    
    # 3. Junta tudo
    full_text = base_text + recipes_text
    
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar", callback_data="job_menu")]])
    
    await _safe_edit_or_send(q, context, q.message.chat_id, full_text, kb)

# EXPORTS
job_menu_handler = CallbackQueryHandler(show_profession_menu, pattern=r'^job_menu$')
job_view_handler = CallbackQueryHandler(view_profession_detail, pattern=r'^job_view_[A-Za-z0-9_]+$')
job_confirm_handler = CallbackQueryHandler(confirm_profession_callback, pattern=r'^job_confirm_[A-Za-z0-9_]+$')
job_guide_handler = CallbackQueryHandler(show_profession_guide_callback, pattern=r'^job_guide_[A-Za-z0-9_]+$')
