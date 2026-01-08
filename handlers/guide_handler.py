# handlers/guide_handler.py
# (VERSÃO BLINDADA: Detecta se é Foto ou Texto para não dar erro)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

# --- IMPORTS PARA LER OS DADOS REAIS ---
from modules.player.stats import CLASS_PROGRESSIONS, CLASS_POINT_GAINS
from modules.game_data.classes import CLASSES_DATA
from modules.game_data.attributes import STAT_EMOJI

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
# HELPER DE EDIÇÃO SEGURA (A CORREÇÃO ESTÁ AQUI)
# ==============================================================================
async def _safe_edit_guide(query, text_content, keyboard):
    """
    Edita a mensagem verificando se ela é Mídia (Caption) ou Texto (Text).
    Isso evita o erro 'There is no caption in the message to edit'.
    """
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        # Verifica se a mensagem original tem mídia (Foto, Vídeo ou Documento)
        if query.message.photo or query.message.video or query.message.document:
            await query.edit_message_caption(
                caption=text_content,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            # Se não tiver mídia, edita como texto normal
            await query.edit_message_text(
                text=text_content,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Erro ao editar guia: {e}")
        # Em último caso, tenta enviar como nova mensagem se a edição falhar muito feio
        try:
            await query.message.reply_text(text_content, reply_markup=reply_markup, parse_mode="HTML")
        except: pass

# ==============================================================================
# GERADORES DE TEXTO DINÂMICO
# ==============================================================================

def _generate_stats_guide_text():
    """Gera o texto de status lendo direto do stats.py"""
    text = "<b>📊 MATEMÁTICA DO PODER (Dinâmico)</b>\n\n"
    text += "<i>Estes são os valores atuais do servidor:</i>\n\n"
    
    # --- 1. CRESCIMENTO POR NÍVEL ---
    text += "<b>1️⃣ CRESCIMENTO AUTOMÁTICO (Por Nível)</b>\n"
    text += "Ao subir de nível, você ganha isso automaticamente:\n\n"
    
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
    
    # --- 2. EFICIÊNCIA DOS PONTOS ---
    text += "<b>2️⃣ EFICIÊNCIA DOS PONTOS (Cliques)</b>\n"
    text += "O quanto seu atributo sobe ao gastar <b>1 Ponto</b>:\n\n"
    
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

    text += "\n<i>💡 Os demais atributos ganham +1 por ponto.</i>"
    return text

def _generate_mana_guide_text():
    """Gera o guia de Mana lendo a configuração do stats.py"""
    text = "<b>💧 FONTES DE MANA (MP)</b>\n\n"
    text += "Seu atributo de Mana depende da sua classe:\n\n"
    
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

    text += "<i>⚠️ Dica: Distribua pontos neste atributo para ganhar MP!</i>"
    return text

TEXT_MAIN_MENU = """
<b>📘 BIBLIOTECA DE ELDORA</b>

Os conhecimentos arcanos do servidor estão aqui.
Estes dados são extraídos diretamente das leis do mundo (código).

<i>Selecione um tópico:</i>
"""

TEXT_CLASSES_INFO = """
<b>⛩️ ÁRVORES DE EVOLUÇÃO</b>

Veja o destino de cada classe:

⚔️ <b>GUERREIRO</b> ➔ 
Cavaleiro ➔ Templário ➔ Guardião Divino ➔ Avatar da Égide ➔ <b>Lenda Divina</b>
🪓 <b>BERSERKER</b> ➔ 
Bárbaro ➔ Selvagem ➔ Ira Primordial ➔ Avatar da Calamidade ➔ <b>Deus da Ira</b>
🏹 <b>CAÇADOR</b> ➔ 
Franco Atirador ➔ Olho de Águia ➔ Atirador Espectral ➔ O Horizonte ➔ <b>Lenda do Arco</b>
🔪 <b>ASSASSINO</b> ➔ 
Ladrão de Sombras ➔ Ninja ➔ Mestre das Lâminas ➔ Ceifador ➔ <b>Aspecto da Noite</b>
🧙 <b>MAGO</b> ➔ 
Elementalista ➔ Arquimago ➔ Mago de Batalha ➔ Arcanista Supremo ➔ <b>Aspecto Arcano</b>
🧘 <b>MONGE</b> ➔ 
Punho Elemental ➔ Ascendente ➔ Punho Divino ➔ Dragão Interior ➔ <b>Lenda do Punho</b>
🥷 <b>SAMURAI</b> ➔ 
Ronin ➔ Kenshi ➔ Shogunato ➔ Mestre de Bushido ➔ <b>Aspecto da Lâmina</b>
🎶 <b>BARDO</b> ➔ 
Menestrel ➔ Trovador ➔ Mestre de Concerto ➔ Harmonista ➔ <b>Aspecto Musical</b>
🩹 <b>CURANDEIRO</b> ➔ 
Clérigo ➔ Sacerdote ➔ Hierofante ➔ Oráculo Celestial ➔ <b>Lenda da Cura</b>
"""

# ==============================================================================
# HANDLERS
# ==============================================================================

async def show_guide_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Status & Pontos", callback_data="guide_topic_stats"),
            InlineKeyboardButton("💧 Mana & Atributos", callback_data="guide_topic_mana"),
        ],
        [InlineKeyboardButton("⛩️ Evolução de Classes", callback_data="guide_topic_classes")],
        [InlineKeyboardButton("⬅️ Voltar ao Reino", callback_data="show_kingdom_menu")]
    ]
    
    # Usa o helper seguro
    await _safe_edit_guide(query, TEXT_MAIN_MENU, keyboard)

async def show_topic_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    dynamic_text = _generate_stats_guide_text()
    keyboard = [[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="guide_main")]]
    
    await _safe_edit_guide(query, dynamic_text, keyboard)

async def show_topic_mana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    dynamic_text = _generate_mana_guide_text()
    keyboard = [[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="guide_main")]]
    
    await _safe_edit_guide(query, dynamic_text, keyboard)

async def show_topic_classes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="guide_main")]]
    
    await _safe_edit_guide(query, TEXT_CLASSES_INFO, keyboard)

# Lista para registrar no main.py
guide_handlers = [
    CallbackQueryHandler(show_guide_main, pattern="^guide_main$"),
    CallbackQueryHandler(show_topic_mana, pattern="^guide_topic_mana$"),
    CallbackQueryHandler(show_topic_classes, pattern="^guide_topic_classes$"),
    CallbackQueryHandler(show_topic_stats, pattern="^guide_topic_stats$"),
]