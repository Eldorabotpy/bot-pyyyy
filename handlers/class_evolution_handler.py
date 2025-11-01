# handlers/class_evolution_handler.py (VERSÃO FINAL E CORRIGIDA)

from __future__ import annotations
import logging
from typing import Dict, Any, List, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from modules import player_manager
from modules import file_ids

# --- IMPORTAÇÕES DE DADOS ATUALIZADAS ---
from modules.game_data import classes as classes_data
from modules.game_data import items as items_data
from modules.game_data import class_evolution as evo_data
from modules.game_data import skills as skills_data 
from handlers.utils import format_combat_message
from modules import class_evolution_service
from modules.game_data import monsters as monsters_data
# Tabelas base
try:
    from modules.game_data.classes import CLASSES_DATA as _CLASSES_DATA
except Exception:
    _CLASSES_DATA = {}

try:
    from modules.game_data.items import ITEMS_DATA as _ITEMS_DATA
except Exception:
    _ITEMS_DATA = {}

from modules.game_data.class_evolution import (
    get_evolution_options,
    EVOLUTIONS as _EVOS,
)

logger = logging.getLogger(__name__)


# ============ Utils ============

def _level(pdata: dict) -> int:
    try:
        return int(pdata.get("level") or pdata.get("lvl") or 1)
    except Exception:
        return 1


def _inv_qty(pdata: dict, item_id: str) -> int:
    inv = pdata.get("inventory") or pdata.get("inventario") or {}
    if isinstance(inv, dict):
        try:
            return int(inv.get(item_id, 0))
        except Exception:
            return 0
    if isinstance(inv, list):
        total = 0
        for st in inv:
            sid = st.get("id") or st.get("item_id")
            if sid == item_id:
                try:
                    total += int(st.get("qty", 1))
                except Exception:
                    pass
        return total
    return 0


def _req_check(pdata: dict, req_items: Dict[str, int], min_level: int) -> Tuple[bool, List[str]]:
    lines: List[str] = []
    lvl = _level(pdata)
    lvl_ok = lvl >= int(min_level)
    lines.append(("✅" if lvl_ok else "❌") + f" 🧿 <b>Nível</b>: {lvl}/{min_level}")

    all_ok = lvl_ok
    for iid, need in (req_items or {}).items():
        have = _inv_qty(pdata, iid)
        item = (_ITEMS_DATA or {}).get(iid, {})
        name = item.get("display_name", iid)
        emoji = item.get("emoji", "•")
        ok = have >= int(need)
        all_ok = all_ok and ok
        lines.append(f"{'✅' if ok else '❌'} {emoji} <b>{name}</b>: {have}/{need}")

    return all_ok, lines


def _footer_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 𝐀𝐭𝐮𝐚𝐥𝐢𝐳𝐚𝐫", callback_data="evo_refresh")],
        [InlineKeyboardButton("⬅️ 𝐕𝐨𝐥𝐭𝐚𝐫 𝐚𝐨 𝐏𝐞𝐫𝐬𝐨𝐧𝐚𝐠𝐞𝐦", callback_data="status_open")],
    ])

def _all_options_for_class(curr_class_key: str) -> List[dict]:
    """
    Retorna TODAS as opções de evolução da classe atual.
    Procura em TODAS as classes base por evoluções
    que listam 'curr_class_key' em 'from_any_of'.
    """
    out: List[dict] = []
    
    # 1. Procura por evoluções T2 (se a classe atual for T1)
    base_data = _EVOS.get(curr_class_key)
    if base_data:
        for opt in base_data.get("tier2", []):
            out.append({"tier": "tier2", **opt})

    # 2. Procura por evoluções T3+ (que vêm de T2, como 'ronin')
    for base_class_key, base_class_data in _EVOS.items():
        for tier in ("tier3",): 
            tier_options = base_class_data.get(tier, [])
            if not isinstance(tier_options, list): continue
                
            for opt in tier_options:
                req_from = opt.get("from_any_of")
                
                if isinstance(req_from, list) and curr_class_key in req_from:
                    out.append({"tier": tier, **opt})
    
    return out

# ============ Renders ============

# Em handlers/class_evolution_handler.py

async def _render_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, as_new: bool = False) -> None:
    user_id = update.effective_user.id
    pdata = await player_manager.get_player_data(user_id) or {}

    curr_key = (pdata.get("class") or pdata.get("class_tag") or "").lower()
    curr_cfg = _CLASSES_DATA.get(curr_key, {})
    curr_emoji = curr_cfg.get("emoji", "🧬")
    curr_name = curr_cfg.get("display_name", (pdata.get("class") or "—").title())
    lvl = _level(pdata)

    opts = _all_options_for_class(curr_key) # Síncrono
    logger.info("[EVOL] user=%s class=%s lvl=%s options_all=%s", user_id, curr_key, lvl, len(opts))

    header = [
        "🧬 <b>Evolução de Classe</b>",
        f"Classe atual: {curr_emoji} <b>{curr_name}</b>",
        f"Nível atual: <b>{lvl}</b>",
        ""
    ]

    if not opts:
        text = "\n".join(header + [
            "Não há ramos de evolução configurados para sua classe atual.",
        ])
        query = update.callback_query
        if query and not as_new:
            try:
                await query.edit_message_caption(text, reply_markup=_footer_keyboard(), parse_mode="HTML")
                return
            except Exception:
                try:
                    await query.edit_message_text(text, reply_markup=_footer_keyboard(), parse_mode="HTML")
                    return
                except Exception:
                    pass
        if query:
            try: await query.delete_message()
            except Exception: pass
        await update.effective_chat.send_message(text, reply_markup=_footer_keyboard(), parse_mode="HTML")
        return

    full_text_parts = header
    full_keyboard = []

    for op in opts:
        to_key = op["to"]
        to_cfg = _CLASSES_DATA.get(to_key, {})
        to_name = to_cfg.get("display_name", to_key.title())
        to_emoji = to_cfg.get("emoji", "✨")

        eligible, req_lines = _req_check(
            pdata, dict(op.get("required_items") or {}), int(op.get("min_level", 0))
        )

        full_text_parts.append("──────────")
        full_text_parts.append(f"{to_emoji} <b>{to_name}</b> <i>({op.get('tier', '').upper()})</i>")
        if op.get("desc"):
            full_text_parts.append(f"• {op['desc']}")

        # --- 👇 INÍCIO DA MUDANÇA (LER A LISTA DE SKILLS) 👇 ---
        
        # Lê a chave nova (plural) OU a chave antiga (singular) por segurança
        skill_ids = op.get("unlocks_skills", [])
        if not skill_ids and op.get("unlocks_skill"):
            skill_ids = [op.get("unlocks_skill")] # Converte a singular para lista

        if skill_ids:
            # Mostra o título só se houver skills
            full_text_parts.append(f"🎁 <b>Habilidades Desbloqueadas:</b>")
            
            for skill_id in skill_ids:
                if skill_id in skills_data.SKILL_DATA:
                    skill_info = skills_data.SKILL_DATA[skill_id]
                    skill_name = skill_info.get("display_name", "Habilidade")
                    skill_desc = skill_info.get("description", "")
                    # Mostra cada skill numa linha separada
                    full_text_parts.append(f"   • <b>{skill_name}</b> - <i>{skill_desc}</i>")
        
        # --- 👆 FIM DA MUDANÇA 👆 ---

        full_text_parts.append("\n<b>Requisitos:</b>")
        full_text_parts.extend([f"   {ln}" for ln in req_lines])

        if eligible:
            full_keyboard.append([InlineKeyboardButton(f"⚡ Evoluir para {to_name}", callback_data=f"evo_do:{to_key}")])
        else:
            full_keyboard.append([InlineKeyboardButton("❌ Requisitos Pendentes", callback_data="evo_refresh")])

        full_text_parts.append("")

    full_text_parts.append("──────────")
    full_keyboard.extend(_footer_keyboard().inline_keyboard)

    final_text = "\n".join(full_text_parts)
    final_keyboard = InlineKeyboardMarkup(full_keyboard)

    query = update.callback_query
    if query and not as_new:
        try:
            await query.edit_message_caption(final_text, reply_markup=final_keyboard, parse_mode="HTML")
        except Exception:
            try:
                await query.edit_message_text(final_text, reply_markup=final_keyboard, parse_mode="HTML")
            except Exception:
                try: await query.delete_message()
                except Exception: pass
                await update.effective_chat.send_message(final_text, reply_markup=final_keyboard, parse_mode="HTML")
    else:
        if query:
            try: await query.delete_message()
            except Exception: pass
        await update.effective_chat.send_message(final_text, reply_markup=final_keyboard, parse_mode="HTML")
            
# ============ Actions ============

async def open_evolution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Apaga a mensagem anterior (Status, que tem mídia) e envia o 
    menu de evolução (texto) como uma nova mensagem.
    """
    query = update.callback_query
    if query:
        await query.answer() # Responde ao clique
        try:
            await query.delete_message()
        except Exception as e:
            logger.debug(f"Falha ao apagar msg em open_evolution: {e}")
            
    await _render_menu(update, context, as_new=True)

async def refresh_evolution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q:
        await q.answer()
    await _render_menu(update, context, as_new=False) # 'as_new=False' para editar


async def _send_evolution_media(chat, class_key: str, caption: str | None = None) -> bool:
    """
    Tenta enviar um vídeo/foto para a classe resultante da evolução.
    """
    keys = [f"evolution_video_{class_key}", f"classe_{class_key}_media"]
    for key in keys:
        fd = file_ids.get_file_data(key)
        if not fd or not fd.get("id"):
            continue
        try:
            if (fd.get("type") or "video").lower() == "video":
                await chat.send_video(video=fd["id"], caption=caption or "", parse_mode="HTML")
            else:
                await chat.send_photo(photo=fd["id"], caption=caption or "", parse_mode="HTML")
            return True
        except Exception as e:
            logger.warning("[EVOL_MEDIA] Falha ao enviar %s (%s): %s", key, fd.get("type"), e)
    return False

async def do_evolution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    _, to_key = query.data.split(":", 1)

    # 1. Chama o nosso serviço para iniciar a provação (ele consome os itens)
    result = await class_evolution_service.start_evolution_trial(user_id, to_key)

    if not result.get("success"):
        await query.answer(result.get("message", "Não foi possível iniciar a provação."), show_alert=True)
        await _render_menu(update, context)
        return

    # 2. Se for bem-sucedido, prepara a batalha de teste
    monster_id = result.get("trial_monster_id")
    if not monster_id:
        await query.answer("Erro: Monstro da provação não configurado.", show_alert=True)
        await _render_menu(update, context)
        return

    monster_template = None
    evolution_monsters = (getattr(monsters_data, "MONSTERS_DATA", {}) or {}).get("_evolution_trials", [])
    for mob in evolution_monsters:
        if mob.get("id") == monster_id:
            monster_template = mob
            break

    if not monster_template:
        await query.answer(f"Erro: Monstro de provação '{monster_id}' não encontrado nos dados.", show_alert=True)
        await _render_menu(update, context)
        return

    # 3. Inicia o combate
    pdata = await player_manager.get_player_data(user_id)
    if not pdata: 
        await query.answer("Erro ao carregar dados do jogador.", show_alert=True)
        return

    # Monta os detalhes do combate com a "marcação" especial
    combat_details = {
        "monster_name":       monster_template.get("name", "Guardião"),
        "monster_hp":         int(monster_template.get("hp", 100)),
        "monster_max_hp":     int(monster_template.get("hp", 100)),
        "monster_attack":     int(monster_template.get("attack", 10)),
        "monster_defense":    int(monster_template.get("defense", 10)),
        "monster_initiative": int(monster_template.get("initiative", 10)),
        "monster_luck":       int(monster_template.get("luck", 10)),
        "battle_log":         ["Você enfrenta o guardião da sua nova classe em uma batalha de provação!"],

        "evolution_trial": {
            "target_class": to_key
        }
    }

    pdata["player_state"] = {"action": "in_combat", "details": combat_details}
    await player_manager.save_player_data(user_id, pdata)

    # Envia a mensagem de combate
    
    # <<< CORREÇÃO CRÍTICA: Adiciona 'await' >>>
    # (Este era o bug que ia crashar o teu bot)
    caption = await format_combat_message(pdata) 

    kb = [
        [InlineKeyboardButton("⚔️ Atacar", callback_data="combat_attack"), InlineKeyboardButton("🧪 Poções", callback_data="combat_potion_menu")],
        [InlineKeyboardButton("🏃 Fugir", callback_data="combat_flee")]
    ]

    try:
        await query.delete_message()
    except Exception:
        pass

    try:
        await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem de combate de evolução para {user_id}: {e}", exc_info=True)
        try:
            await context.bot.send_message(chat_id=chat_id, text="Ocorreu um erro ao iniciar a batalha de provação.")
            pdata["player_state"] = {"action": "idle"}
            # <<< CORREÇÃO: Adiciona 'await' ao salvar >>>
            await player_manager.save_player_data(user_id, pdata)
        except Exception as e_fallback:
            logger.error(f"Erro CRÍTICO ao tentar reverter estado após falha em do_evolution: {e_fallback}")

# ============ Exports (handlers) ============

status_evolution_open_handler = CallbackQueryHandler(open_evolution, pattern=r"^status_evolution_open$")
evolution_command_handler     = CommandHandler("evoluir", open_evolution)
evolution_callback_handler    = CallbackQueryHandler(refresh_evolution, pattern=r"^evo_refresh$")
evolution_do_handler          = CallbackQueryHandler(do_evolution, pattern=r"^evo_do:.+$")
evolution_cancel_handler      = CallbackQueryHandler(refresh_evolution, pattern=r"^evo_cancel$")