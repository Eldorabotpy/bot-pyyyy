# handlers/class_selection_handler.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, game_data, file_id_manager
from handlers.menu_handler import show_kingdom_menu
from modules.balance import ui_display_modifiers
from modules.player.stats import CLASS_PROGRESSIONS, CLASS_POINT_GAINS

CLASS_MANA_INFO = {
    "guerreiro": "Sorte",
    "berserker": "Sorte",
    "cacador": "Iniciativa",
    "monge": "Iniciativa",
    "mago": "Ataque",
    "bardo": "Sorte",
    "assassino": "Iniciativa",
    "samurai": "Defesa",
    "curandeiro": "Sorte",
    "_default": "Sorte",
}
# =========================
# Fontes de classes + normalização
# =========================

def _try_import_classes_module():
    """Tenta importar modules.game_data.classes (opcional)."""
    try:
        from modules.game_data import classes as classes_mod  # type: ignore
        return classes_mod
    except Exception:
        return None

def _normalize_class_entry(class_key: str, cfg: dict) -> dict:
    """
    Normaliza para:
    {
      "key": str, "display_name": str, "emoji": str,
      "description": str, "stat_modifiers": dict, "file_id_name": Optional[str]
    }
    """
    cfg = cfg or {}
    disp = (
        cfg.get("display_name")
        or cfg.get("name")
        or cfg.get("nome")
        or str(class_key).replace("_", " ").title()
    )
    desc = (
        cfg.get("description")
        or cfg.get("desc")
        or cfg.get("descricao")
        or "Sem descrição."
    )
    emoji = cfg.get("emoji", "▫️")
    mods = (
        cfg.get("stat_modifiers")
        or cfg.get("modifiers")
        or cfg.get("stats")
        or {}
    )
    file_id_name = (
        cfg.get("file_id_name")
        or cfg.get("profile_media_key")
        or cfg.get("profile_file_id_key")
        or cfg.get("file_id_key")
    )
    return {
        "key": str(class_key),
        "display_name": str(disp),
        "emoji": str(emoji),
        "description": str(desc),
        "stat_modifiers": dict(mods) if isinstance(mods, dict) else {},
        "file_id_name": file_id_name if isinstance(file_id_name, str) else None,
        "tier": cfg.get("tier", 1)
    }

def _load_classes_dict() -> dict:
    """Tenta obter o dicionário bruto de classes de várias fontes."""
    # 1) direto de modules.game_data (reexportado no __init__.py)
    for attr in ("CLASSES_DATA", "CLASSES"):
        data = getattr(game_data, attr, None)
        if isinstance(data, dict) and data:
            return data

    # 2) do módulo modules.game_data.classes
    classes_mod = _try_import_classes_module()
    if classes_mod:
        for attr in ("CLASSES_DATA", "CLASSES"):
            data = getattr(classes_mod, attr, None)
            if isinstance(data, dict) and data:
                return data

    return {}

def _load_classes_list() -> list[dict]:
    """Lê as classes e normaliza; se nada, cai em fallback (2 classes)."""
    raw = _load_classes_dict()
    if isinstance(raw, dict) and raw:
        out = []
        for k, v in raw.items():
            if isinstance(v, dict):
                # Filtra apenas Tier 1
                if v.get('tier') == 1:
                    out.append(_normalize_class_entry(k, v))
        if out:
            out.sort(key=lambda e: e["display_name"].lower())
            return out

    # Fallback mínimo
    return [
        _normalize_class_entry("guerreiro", {"display_name": "Guerreiro", "emoji": "⚔️", "description": "Combatente robusto."}),
        _normalize_class_entry("mago", {"display_name": "Mago", "emoji": "🧙", "description": "Mestre das artes arcanas."}),
    ]


# =========================
# Elegibilidade (Síncrono)
# =========================
def _eligible_for_class(player_data: dict) -> bool:
    """Pode escolher classe se nível ≥ 5 e ainda não tiver classe.""" 
    if not player_data:
        return False
    try:
        lvl = int(player_data.get("level", 1))
    except Exception:
        lvl = 1
    return (lvl >= 5) and not bool(player_data.get("class")) 

# =========================
# Tela: Lista de Classes
# =========================
async def show_class_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o menu de seleção de classe em nova mensagem."""
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id if update.effective_user else None
    
    # CORREÇÃO: Adicionado 'await'
    player_data = await player_manager.get_player_data(user_id) if user_id else None

    # Já tem classe?
    if player_data and player_data.get("class"):
        text = f"Você já escolheu sua classe: <b>{player_data.get('class')}</b>."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="profile")]])
        if query:
            await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=kb)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode="HTML", reply_markup=kb)
        return

    # Checa nível (função síncrona, não precisa de await)
    if not _eligible_for_class(player_data or {}):
        msg = "Você ainda não atingiu o nível 5 para escolher uma classe."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="profile")]])
        if query:
            try:
                await query.edit_message_text(text=msg, reply_markup=kb)
            except Exception:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, reply_markup=kb)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, reply_markup=kb)
        return

    text = "Sua jornada o fortaleceu. Escolha a classe que definirá seu destino:"
    
    # Carrega classes (função síncrona)
    classes = _load_classes_list()

    keyboard = []
    for entry in classes:
        keyboard.append([
            InlineKeyboardButton(
                f"{entry['emoji']} {entry['display_name']}",
                callback_data=f"view_class_{entry['key']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data="profile")])

    # Limpa a mensagem anterior, se der
    if query and query.message:
        try:
            await query.delete_message()
        except Exception:
            pass

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# Tela: Detalhes da Classe
# =========================
# =========================
# Tela: Detalhes da Classe
# =========================
async def show_class_details(update: Update, context: ContextTypes.DEFAULT_TYPE, class_key: str):
    query = update.callback_query
    user_id = query.from_user.id if query else (update.effective_user.id if update.effective_user else None)

    player_data = await player_manager.get_player_data(user_id) if user_id else None

    if player_data and player_data.get("class"):
        await query.answer("Você já escolheu sua classe.", show_alert=True)
        return

    # Corrigido para Nv 5
    if not _eligible_for_class(player_data or {}):
        await query.answer("Você ainda não pode escolher classe (nível 5 necessário).", show_alert=True)
        return

    classes = _load_classes_list() # Síncrono
    entry = next((e for e in classes if e["key"] == class_key), None)
    if not entry:
        await query.edit_message_text(
            "Classe inválida.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="show_class_list")]])
        )
        return
    # --- INÍCIO DA LÓGICA DE TEXTO SUBSTITUÍDA ---
    # 1. Obter os dados dos dicionários
    prog = CLASS_PROGRESSIONS.get(class_key, CLASS_PROGRESSIONS["_default"])
    gains_manual = CLASS_POINT_GAINS.get(class_key, CLASS_POINT_GAINS["_default"])
    gains_default = CLASS_POINT_GAINS["_default"]
    
    mana_stat_name = CLASS_MANA_INFO.get(class_key, "Sorte")
    
    # 2. Ganhos Automáticos
    auto = prog.get("PER_LVL", {})
    auto_hp = auto.get("max_hp", 0)
    auto_atk = auto.get("attack", 0)
    auto_def = auto.get("defense", 0)
    auto_ini = auto.get("initiative", 0)
    auto_luk = auto.get("luck", 0)

    # 3. Ganhos Manuais (misturando o default com a classe)
    manual_hp = gains_manual.get("max_hp", gains_default.get("max_hp", 1))
    manual_atk = gains_manual.get("attack", gains_default.get("attack", 1))
    manual_def = gains_manual.get("defense", gains_default.get("defense", 1))
    manual_ini = gains_manual.get("initiative", gains_default.get("initiative", 1))
    manual_luk = gains_manual.get("luck", gains_default.get("luck", 1))

    # 4. Montar o texto
    details_text = (
        f"{entry['emoji']} <b>{entry['display_name']}</b>\n\n"
        f"<i>{entry.get('description', 'Sem descrição.')}</i>\n\n"

        "<b>📈 Ganhos Automáticos (por Nível):</b>\n"
        f"  ❤️ HP Máx: +{auto_hp}\n"
        f"  ⚔️ Ataque: +{auto_atk}\n"
        f"  🛡️ Defesa: +{auto_def}\n"
        f"  🏃 Iniciativa: +{auto_ini}\n"
        f"  🍀 Sorte: +{auto_luk}\n"
        f"  (Mana escala com: <b>{mana_stat_name}</b>)\n\n"
        
        "<b>📌 Distribuição Manual (1 Ponto = ...):</b>\n"
        f"  ❤️ HP Máx: +{manual_hp}\n"
        f"  ⚔️ Ataque: +{manual_atk}\n"
        f"  🛡️ Defesa: +{manual_def}\n"
        f"  🏃 Iniciativa: +{manual_ini}\n"
        f"  🍀 Sorte: +{manual_luk}\n\n"
        "Deseja escolher este caminho?"
    )
    # --- FIM DA LÓGICA DE TEXTO SUBSTITUÍDA ---

    keyboard = [[
        InlineKeyboardButton("✅ Confirmar", callback_data=f"confirm_class_{entry['key']}"),
        InlineKeyboardButton("⬅️ Voltar à Lista", callback_data='show_class_list'),
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Mídia (síncrono)
    file_data = None
    if entry.get("file_id_name"):
        file_data = file_id_manager.get_file_data(entry["file_id_name"])
    if not file_data:
        file_data = file_id_manager.get_file_data(f"classe_{entry['key']}_media")

    try:
        await query.delete_message()
    except Exception:
        pass

    chat_id = update.effective_chat.id # Pega chat_id aqui
    if file_data and file_data.get("id"):
        file_id, file_type = file_data["id"], (file_data.get("type") or "").lower()
        if file_type == 'video':
            await context.bot.send_video(
                chat_id=chat_id, video=file_id, caption=details_text,
                reply_markup=reply_markup, parse_mode='HTML'
            )
        else:
            await context.bot.send_photo(
                chat_id=chat_id, photo=file_id, caption=details_text,
                reply_markup=reply_markup, parse_mode='HTML'
            )
    else:
        await context.bot.send_message(
            chat_id=chat_id, text=details_text,
            reply_markup=reply_markup, parse_mode='HTML'
        )

# =========================
# Confirmar Escolha
# =========================
async def confirm_class_choice(update: Update, context: ContextTypes.DEFAULT_TYPE, class_key: str):
    query = update.callback_query
    user_id = query.from_user.id if query else (update.effective_user.id if update.effective_user else None)

    # CORREÇÃO 8: Adiciona await
    player_data = await player_manager.get_player_data(user_id) if user_id else None

    classes = _load_classes_list() # Síncrono
    entry = next((e for e in classes if e["key"] == class_key), None)
    if not entry or not player_data:
        if query:
            # CORREÇÃO 9: Adiciona await
            await query.edit_message_text(
                text="Classe inválida.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar", callback_data="show_class_list")]])
            )
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Classe inválida.")
        return

    # Síncrono
    if player_data.get('class') is not None:
        if query:
            await query.answer("Você já escolheu sua classe!", show_alert=True)
        return

    # Síncrono
    if not _eligible_for_class(player_data):
        if query:
            await query.answer("Você ainda não pode escolher classe (nível 10 necessário).", show_alert=True)
        return

    # Salva
    disp_name = entry["display_name"]
    player_data['class'] = disp_name
    player_data['class_key'] = entry["key"]
    player_data['class_choice_offered'] = True # Marca como escolhido

    # CORREÇÃO 10: Adiciona await
    await player_manager.save_player_data(user_id, player_data)

    if query:
        await query.answer(f"Você agora é um {disp_name}!", show_alert=True)

    # CORREÇÃO 11: Adiciona await
    await show_kingdom_menu(update, context) # Chama função async


# =========================
# Roteador (Callback)
# =========================
async def class_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query: # Ignora se não for callback
        return
    
    # Não responde aqui, deixa as funções específicas responderem (com await query.answer())
    # Isso evita o "relógio" de carregamento no Telegram se a função demorar.
    # As funções show_class_list, show_class_details, etc., dão o answer.

    data = query.data
    
    if data in ('show_class_list', 'class_open') or data.startswith('class_open:'):
        # CORREÇÃO 12: Adiciona await
        await show_class_list(update, context); return

    if data.startswith('view_class_'):
        class_key = data.replace('view_class_', '', 1)
        # CORREÇÃO 13: Adiciona await
        await show_class_details(update, context, class_key); return

    if data.startswith('confirm_class_'):
        class_key = data.replace('confirm_class_', '', 1)
        # CORREÇÃO 14: Adiciona await
        await confirm_class_choice(update, context, class_key); return

    # Se chegou aqui, é um callback desconhecido, responde silenciosamente
    try: await query.answer()
    except Exception: pass
    return

# =========================
# Exportação do Handler
# =========================
class_selection_handler = CallbackQueryHandler(
    class_selection_callback,
    pattern=r'^(?:show_class_list|class_open(?::\d+)?|view_class_[\w_]+|confirm_class_[\w_]+)$'
)

# Alias para chamadas diretas de outros módulos
show_class_selection_menu = show_class_list