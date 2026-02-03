# handlers/tutorial/dora_gathering.py

from __future__ import annotations
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from modules import player_manager
from modules.auth_utils import get_current_player_id
from uuid import uuid4
import uuid
from modules.game_data.items_tools import TOOLS_DATA
from telegram import Update
from modules.player.inventory import add_unique_item, equip_unique_item_for_user

# Dados do jogo
try:
    from modules.game_data.professions import PROFESSIONS_DATA  # type: ignore
except Exception:
    PROFESSIONS_DATA = {}

try:
    from modules.game_data.regions import REGIONS_DATA  # type: ignore
except Exception:
    REGIONS_DATA = {}

try:
    from modules.game_data.items_tools import TOOLS_DATA  # type: ignore
except Exception:
    TOOLS_DATA = {}

# Se o seu projeto usa outro caminho para tools, ajuste aqui conforme necessário.

CB_GATH_OPEN_MAP = "dora_gath_open_map"
CB_GATH_TO_KINGDOM = "dora_gath_to_kingdom"
CB_GATH_HELP = "dora_gath_help"

# Mapeamento de profissão -> ferramenta inicial (ids reais do seu TOOLS_DATA)
STARTER_TOOL_BY_PROF = {
    "lenhador": "machado_pedra",
    "minerador": "picareta_pedra",
    "colhedor": "foice_pedra",
    "esfolador": "faca_pedra",
    "alquimista": "frasco_vidro",
}

# Mapeamento de profissão -> região recomendada (do seu REGIONS_DATA)
RECOMMENDED_REGION_BY_PROF = {
    "lenhador": "floresta_sombria",
    "minerador": "pedreira_granito",   # você escolheu A = pedra
    "colhedor": "campos_linho",
    "esfolador": "pico_grifo",
    "alquimista": "pantano_maldito",
}

def _extract_message(update: Update):
    if update.message:
        return update.message
    if update.callback_query and update.callback_query.message:
        return update.callback_query.message
    return None


def _get_prof_key(player_data: dict) -> str | None:
    prof = player_data.get("profession", {}) or {}
    return prof.get("type") or prof.get("key")


def _tool_label(tool_id: str) -> str:
    t = TOOLS_DATA.get(tool_id, {}) or {}
    name = t.get("display_name") or tool_id
    emoji = t.get("emoji") or ""
    return f"{emoji} {name}".strip()


def _region_label(region_key: str) -> str:
    r = REGIONS_DATA.get(region_key, {}) or {}
    name = r.get("name") or region_key.replace("_", " ").title()
    emoji = r.get("emoji") or "🗺️"
    return f"{emoji} {name}".strip()


async def _give_starter_tool_if_needed(user_id: str, player_data: dict) -> tuple[bool, bool, str | None]:
    """
    Entrega ferramenta inicial como UNIQUE ITEM (uuid) e equipa via equip_unique_item_for_user.
    Retorna (delivered_now, equipped_now, tool_base_id).
    """
    flags = player_data.setdefault("tutorial_flags", {}) or {}
    inv = player_data.setdefault("inventory", {}) or {}
    equip = player_data.setdefault("equipment", {}) or {}

    prof_key = _get_prof_key(player_data)
    if not prof_key:
        return (False, False, None)

    tool_base_id = STARTER_TOOL_BY_PROF.get(prof_key)
    if not tool_base_id:
        return (False, False, None)

    # 1) Se já tem uma tool equipada válida, encerra
    cur_uid = equip.get("tool")
    if cur_uid and isinstance(inv.get(cur_uid), dict):
        flags["starter_tool_given"] = True
        await player_manager.save_player_data(user_id, player_data)
        return (False, True, tool_base_id)

    # 2) Se já existe o item no inventário (unique), mas não está equipado: equipa
    existing_uid = None

    # tenta usar o UID salvo na flag (se já entregou antes)
    flag_uid = flags.get("starter_tool_uid")
    if flag_uid and isinstance(inv.get(flag_uid), dict):
        item = inv.get(flag_uid) or {}
        if item.get("base_id") == tool_base_id:
            existing_uid = flag_uid

    # se não achou, procura no inventário por base_id
    if not existing_uid:
        for uid_key, item in inv.items():
            if isinstance(item, dict) and item.get("base_id") == tool_base_id:
                existing_uid = uid_key
                break

    if existing_uid:
        ok, _msg = await equip_unique_item_for_user(user_id, existing_uid, "tool")
        return (False, ok, tool_base_id)

    # 3) Não tem ainda: cria unique item com uuid e durability
    base_tool = TOOLS_DATA.get(tool_base_id) or {}
    dur = list(base_tool.get("durability", [0, 0]))

    new_uid = str(uuid.uuid4())
    unique_item = {
        "uuid": new_uid,
        "base_id": tool_base_id,
        "durability": dur,
    }

    added_uid = add_unique_item(player_data, unique_item)
    flags["starter_tool_given"] = True
    flags["starter_tool_uid"] = added_uid

    # salva entrega do item
    await player_manager.save_player_data(user_id, player_data)

    # equipa via sistema oficial (ele recarrega e salva o player)
    ok, _msg = await equip_unique_item_for_user(user_id, added_uid, "tool")

    # 🔥 recarrega player_data para refletir equipamento
    player_data.clear()
    player_data.update(await player_manager.get_player_data(user_id))

    return (True, ok, tool_base_id)

async def show_gathering_chapter(update: Update, context: ContextTypes.DEFAULT_TYPE, player_data: dict):
    msg = _extract_message(update)
    if not msg:
        return

    # ✅ user_id precisa existir aqui
    user_id = context.user_data.get("logged_player_id") or get_current_player_id(update, context)
    if not user_id:
        await msg.reply_text("❌ Erro: sessão não encontrada. Use /start novamente.")
        return

    prof_key = _get_prof_key(player_data)
    if not prof_key:
        await msg.reply_text("❌ Erro: profissão não encontrada. Use /start novamente.")
        return

    # ✅ agora delivered/equipped ficam definidos
    delivered, equipped, tool_id = await _give_starter_tool_if_needed(user_id, player_data)

    region_key = RECOMMENDED_REGION_BY_PROF.get(prof_key, "reino_eldora")
    region_name = _region_label(region_key)

    resource = (REGIONS_DATA.get(region_key, {}) or {}).get("resource")
    resource_line = f"\n📦 Recurso da região: <b>{resource}</b>" if resource else ""

    tool_line = f"\n🧰 Ferramenta: <b>{_tool_label(tool_id)}</b>" if tool_id else ""

    intro = (
        "🧭 <b>TUTORIAL — COLETA</b>\n"
        "👩‍✈️ <b>Dora:</b> Agora vamos aprender o ciclo de coleta.\n\n"
        "✅ Passos:\n"
        "1) Equipar a ferramenta\n"
        "2) Viajar pelo <b>🗺️ Mapa</b>\n"
        "3) Coletar e aguardar o tempo\n"
        "4) Receber notificação e repetir\n"
        f"{tool_line}"
        f"{resource_line}\n\n"
        f"📍 Recomendação: viaje até <b>{region_name}</b> usando o <b>🗺️ Mapa</b>."
    )

    if delivered and tool_id:
        if equipped:
            intro += (
                "\n\n🎁 <b>Ferramenta inicial entregue e equipada automaticamente!</b>\n"
                "Agora você já pode coletar."
            )
        else:
            intro += (
                "\n\n🎁 <b>Ferramenta inicial entregue no inventário.</b>\n"
                "Vá em Inventário → Equipar para poder coletar."
            )

    kb_rows = [
        [InlineKeyboardButton("🗺️ Abrir Mapa", callback_data=CB_GATH_OPEN_MAP)],
        [InlineKeyboardButton("🏰 Ir para o Reino", callback_data=CB_GATH_TO_KINGDOM)],
        [InlineKeyboardButton("❓ Como funciona o tempo?", callback_data=CB_GATH_HELP)],
    ]

    # ✅ Se já estiver na região recomendada, mostra "⛏️ Coletar agora"
    current_loc = player_data.get("current_location")
    if current_loc == region_key and resource:
        kb_rows.insert(0, [InlineKeyboardButton("⛏️ Coletar agora", callback_data=f"collect_{resource}")])

    kb = InlineKeyboardMarkup(kb_rows)

    await msg.reply_text(intro, reply_markup=kb, parse_mode="HTML")

async def dora_gathering_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q or not q.message:
        return
    await q.answer()

    data = q.data or ""

    uid = context.user_data.get("logged_player_id") or get_current_player_id(update, context)
    if not uid:
        return

    player_data = await player_manager.get_player_data(uid)
    if not player_data:
        await q.message.reply_text("❌ Erro: personagem não encontrado.")
        return

    if data == CB_GATH_HELP:
        await q.message.reply_text(
            "⏳ <b>Tempo de espera</b>\n"
            "Quando você iniciar uma coleta, ela terá um tempo para terminar.\n"
            "Assim que acabar, você será <b>notificado</b> e poderá coletar novamente.\n\n"
            "📌 Dica: planos/premium podem reduzir tempo (se você usar isso no balanceamento).",
            parse_mode="HTML",
        )
        return

    if data == CB_GATH_TO_KINGDOM:
        from handlers.menu.kingdom import show_kingdom_menu
        await show_kingdom_menu(update, context, player_data=player_data)
        return

    if data == CB_GATH_OPEN_MAP:
        from handlers.menu.region import show_travel_menu
        await show_travel_menu(update, context)
        return
    
async def maybe_continue_gathering_tutorial(update, context, user_id, region_key: str):
    player_data = await player_manager.get_player_data(user_id) or {}
    stage = player_data.get("onboarding_stage")

    # só continua se está no capítulo de coleta
    if stage != "tutorial_gathering":
        return

    # qual região a Dora recomendou (no seu mapa)
    prof = (player_data.get("profession") or {}).get("type")
    target_region = RECOMMENDED_REGION_BY_PROF.get(prof)
    if not target_region:
        return

    # só continua se chegou na região recomendada
    if region_key != target_region:
        return

    flags = player_data.setdefault("tutorial_flags", {})
    if flags.get("gathering_arrived_done"):
        return

    # ✅ pega o recurso real da região (sem fallback)
    resource_id = (REGIONS_DATA.get(region_key, {}) or {}).get("resource")
    if not resource_id:
        # se por algum motivo a região recomendada não tiver resource, apenas avisa e não cria botão quebrado
        flags["gathering_arrived_done"] = True
        await player_manager.save_player_data(user_id, player_data)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "✅ <b>Perfeito!</b> Você chegou na região correta.\n\n"
                "⚠️ Porém, essa região não tem um recurso de coleta configurado.\n"
                "Abra o menu da região para continuar."
            ),
            parse_mode="HTML",
        )
        return

    flags["gathering_arrived_done"] = True
    await player_manager.save_player_data(user_id, player_data)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⛏️ Coletar agora", callback_data=f"collect_{resource_id}")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data=f"open_region:{region_key}")],
    ])

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "✅ <b>Perfeito!</b> Você chegou na região correta.\n\n"
            "Agora toque em <b>⛏️ Coletar agora</b>.\n"
            "Quando terminar, você será notificado e poderá repetir."
        ),
        parse_mode="HTML",
        reply_markup=kb
    )


