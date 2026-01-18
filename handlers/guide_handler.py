# handlers/guide_handler.py
# (VERSÃO ATUALIZADA: UI RENDERER + IMAGENS POR TÓPICO)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

# --- IMPORTS DE DADOS ---
from modules.player.stats import CLASS_PROGRESSIONS, CLASS_POINT_GAINS
from modules.game_data.classes import CLASSES_DATA
from modules.game_data.attributes import STAT_EMOJI
from modules import file_ids

# --- IMPORT VISUAL ---
from ui.ui_renderer import render_photo_or_text

logger = logging.getLogger(__name__)

# Mapeamento de nomes internos para exibição bonita
STAT_NAMES = {
    "max_hp": "HP",
    "attack": "Atk",
    "defense": "Def",
    "initiative": "Ini",
    "luck": "Sorte",
    "magic_attack": "Magia"
}

# ==============================================================================
# HELPERS VISUAIS
# ==============================================================================

def _pick_guide_media(topic="main"):
    """Seleciona a imagem baseada no tópico do guia."""
    key_map = {
        "main": "img_guide_main",       # Capa do guia
        "classes": "img_guide_classes", # Árvore de classes
        "stats": "img_guide_stats",     # Tabela de status
        "mana": "img_guide_mana"        # Explicação de mana
    }
    
    key = key_map.get(topic, "img_guide_main")
    
    try:
        fid = file_ids.get_file_id(key)
        if fid: return fid
    except: pass
    
    # Fallback genérico
    try:
        return file_ids.get_file_id("img_scroll_generic")
    except:
        return None

async def _render_guide(update, context, text, keyboard, topic="main"):
    """Renderiza a tela do guia usando o sistema unificado."""
    media_fid = _pick_guide_media(topic)
    
    await render_photo_or_text(
        update,
        context,
        text=text,
        photo_file_id=media_fid,
        reply_markup=InlineKeyboardMarkup(keyboard),
        scope="guide_book", # Mantém a navegação fluida na mesma "janela"
        parse_mode="HTML",
        allow_edit=True
    )

# ==============================================================================
# GERADORES DE TEXTO
# ==============================================================================

def _generate_stats_guide_text():
    text = "<b>📊 MATEMÁTICA DO PODER</b>\n\n"
    text += "<i>Como seus atributos crescem neste mundo:</i>\n\n"
    
    # 1. CRESCIMENTO POR NÍVEL
    text += "<b>1️⃣ CRESCIMENTO AUTOMÁTICO (Por Nível)</b>\n"
    text += "Ao subir de nível, você ganha status base:\n\n"
    
    tier_1_classes = [k for k, v in CLASSES_DATA.items() if v.get('tier') == 1]
    
    for cls_key in tier_1_classes:
        cls_info = CLASSES_DATA.get(cls_key, {})
        emoji = cls_info.get("emoji", "👤")
        name = cls_info.get("display_name", cls_key.title())
        
        prog = CLASS_PROGRESSIONS.get(cls_key, CLASS_PROGRESSIONS.get("_default"))
        per_lvl = prog.get("PER_LVL", {})
        
        gains_list = []
        for stat, val in per_lvl.items():
            if val > 0:
                stat_name = STAT_NAMES.get(stat, stat.title())
                gains_list.append(f"+{val} {stat_name}")
        
        if gains_list:
            text += f"{emoji} <b>{name}:</b> {', '.join(gains_list)}\n"
            
    text += "\n━━━━━━━━━━━━━━━━━\n\n"
    
    # 2. EFICIÊNCIA DOS PONTOS
    text += "<b>2️⃣ EFICIÊNCIA DOS PONTOS</b>\n"
    text += "Quanto ganha ao gastar <b>1 Ponto de Atributo</b>:\n\n"
    
    for cls_key in tier_1_classes:
        cls_info = CLASSES_DATA.get(cls_key, {})
        emoji = cls_info.get("emoji", "👤")
        name = cls_info.get("display_name", cls_key.title())
        
        gains = CLASS_POINT_GAINS.get(cls_key, CLASS_POINT_GAINS.get("_default"))
        
        bonus_list = []
        for stat, val in gains.items():
            if val > 1:
                stat_icon = STAT_EMOJI.get(stat, "")
                stat_name = STAT_NAMES.get(stat, stat.title())
                bonus_list.append(f"{stat_icon} {stat_name} = <b>+{val}</b>")
        
        if bonus_list:
            text += f"{emoji} <b>{name}:</b>\n   ╰ {', '.join(bonus_list)}\n"
        else:
            text += f"{emoji} <b>{name}:</b> Padrão (+1 em tudo)\n"

    text += "\n<i>💡 Demais atributos ganham +1 por ponto gasto.</i>"
    return text

def _generate_mana_guide_text():
    text = "<b>💧 FONTES DE MANA (MP)</b>\n\n"
    text += "Seu MP máximo depende de um atributo específico, baseado na sua classe:\n\n"
    
    mana_map = {}
    tier_1_classes = [k for k, v in CLASSES_DATA.items() if v.get('tier') == 1]
    
    for cls_key in tier_1_classes:
        prog = CLASS_PROGRESSIONS.get(cls_key, CLASS_PROGRESSIONS.get("_default"))
        mana_stat = prog.get("mana_stat", "luck")
        
        if mana_stat not in mana_map:
            mana_map[mana_stat] = []
        
        cls_name = CLASSES_DATA.get(cls_key, {}).get("display_name", cls_key.title())
        cls_emoji = CLASSES_DATA.get(cls_key, {}).get("emoji", "")
        mana_map[mana_stat].append(f"{cls_emoji} {cls_name}")

    for stat, classes_list in mana_map.items():
        stat_name = STAT_NAMES.get(stat, stat.upper())
        stat_emoji = STAT_EMOJI.get(stat, "❓")
        
        text += f"{stat_emoji} <b>{stat_name}:</b>\n"
        text += "\n".join([f" • {c}" for c in classes_list])
        text += "\n\n"

    text += "<i>⚠️ Dica: Distribua pontos neste atributo para aumentar sua Mana Máxima!</i>"
    return text

TEXT_MAIN_MENU = """
<b>📘 BIBLIOTECA DE ELDORA</b>

Os conhecimentos arcanos do servidor estão reunidos aqui.
Estes dados são extraídos diretamente das leis do mundo.

<i>Selecione um tomo para ler:</i>
"""

TEXT_CLASSES_INFO = """
<b>⛩️ ÁRVORES DE EVOLUÇÃO</b>

Conheça o destino glorioso de cada caminho:

⚔️ <b>GUERREIRO</b> ➔ Cavaleiro ➔ Templário ➔ Guardião Divino ➔ <b>Lenda Divina</b>
🪓 <b>BERSERKER</b> ➔ Bárbaro ➔ Selvagem ➔ Ira Primordial ➔ <b>Deus da Ira</b>
🏹 <b>CAÇADOR</b> ➔ Franco Atirador ➔ Olho de Águia ➔ O Horizonte ➔ <b>Lenda do Arco</b>
🔪 <b>ASSASSINO</b> ➔ Ladrão ➔ Ninja ➔ Ceifador ➔ <b>Aspecto da Noite</b>
🧙 <b>MAGO</b> ➔ Elementalista ➔ Arquimago ➔ Arcanista Supremo ➔ <b>Aspecto Arcano</b>
🧘 <b>MONGE</b> ➔ Punho Elemental ➔ Ascendente ➔ Dragão Interior ➔ <b>Lenda do Punho</b>
🥷 <b>SAMURAI</b> ➔ Ronin ➔ Kenshi ➔ Shogunato ➔ <b>Aspecto da Lâmina</b>
🎶 <b>BARDO</b> ➔ Menestrel ➔ Trovador ➔ Harmonista ➔ <b>Aspecto Musical</b>
🩹 <b>CURANDEIRO</b> ➔ Clérigo ➔ Sacerdote ➔ Oráculo Celestial ➔ <b>Lenda da Cura</b>
"""

# ==============================================================================
# HANDLERS
# ==============================================================================

async def show_guide_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Status & Pontos", callback_data="guide_topic_stats"),
            InlineKeyboardButton("💧 Mana & Atributos", callback_data="guide_topic_mana"),
        ],
        [InlineKeyboardButton("⛩️ Evolução de Classes", callback_data="guide_topic_classes")],
        [InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data="show_kingdom_menu")]
    ]
    
    await _render_guide(update, context, TEXT_MAIN_MENU, keyboard, topic="main")

async def show_topic_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    dynamic_text = _generate_stats_guide_text()
    keyboard = [[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="guide_main")]]
    
    await _render_guide(update, context, dynamic_text, keyboard, topic="stats")

async def show_topic_mana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    dynamic_text = _generate_mana_guide_text()
    keyboard = [[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="guide_main")]]
    
    await _render_guide(update, context, dynamic_text, keyboard, topic="mana")

async def show_topic_classes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="guide_main")]]
    
    await _render_guide(update, context, TEXT_CLASSES_INFO, keyboard, topic="classes")

# Lista para registrar no main.py
guide_handlers = [
    CallbackQueryHandler(show_guide_main, pattern="^guide_main$"),
    CallbackQueryHandler(show_topic_mana, pattern="^guide_topic_mana$"),
    CallbackQueryHandler(show_topic_classes, pattern="^guide_topic_classes$"),
    CallbackQueryHandler(show_topic_stats, pattern="^guide_topic_stats$"),
]