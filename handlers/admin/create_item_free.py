# handlers/admin/create_item_free.py
from __future__ import annotations
import logging
from typing import Optional, Tuple

from telegram import Update
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Núcleo do projeto
from modules import player_manager
from modules import game_data

# Tentativa de usar a FÁBRICA NOVA primeiro
try:
    # ideal: toda a geração centralizada aqui
    from modules import item_factory as new_factory  # type: ignore
except Exception:
    new_factory = None  # fallback p/ legado

# Fallback legado (só se necessário)
try:
    from modules import crafting_engine  # usaremos apenas como último recurso
except Exception:
    crafting_engine = None  # type: ignore

# Display bonitinho (opcional)
try:
    import modules.display_utils as display_utils  # type: ignore
except Exception:
    display_utils = None  # fallback simples

logger = logging.getLogger(__name__)

# Estados da conversa
CIF_TARGET, CIF_BASE = range(2)

# ---------------------------
# Helpers (novos-safe)
# ---------------------------

RARITY_ALIASES = {
    "comum": "comum",
    "bom": "bom",
    "boa": "bom",
    "raro": "raro",
    "rara": "raro",
    "épico": "epico",
    "epico": "epico",
    "lendário": "lendario",
    "lendaria": "lendario",
    "lendario": "lendario",
}

def _norm_rarity(r: Optional[str]) -> Optional[str]:
    if not r:
        return None
    return RARITY_ALIASES.get(r.strip().lower(), None)

def _mk_recipe_stub(base_id: str, desired_rarity: Optional[str]) -> dict:
    """
    Stub apenas para o fallback legado. Mantém compatibilidade mas não
    é usado quando a fábrica nova existir.
    """
    rarity_chances = {"comum": 1.0}
    if desired_rarity in ("bom",):
        rarity_chances = {"comum": 0.0, "bom": 1.0}
    # Demais raridades não são sorteadas no legado; mantém padrão.

    info = (getattr(game_data, "get_item_info", None) or (lambda _id: {}))(base_id) or {}
    display_name = info.get("display_name", base_id)
    emoji = info.get("emoji", "")
    profession = info.get("profession", "ferreiro")

    return {
        "display_name": display_name,
        "emoji": emoji,
        "profession": profession,
        "level_req": 1,
        "time_seconds": 1,
        "inputs": {},
        "result_base_id": base_id,
        "rarity_chances": rarity_chances,
        "affix_pools_to_use": ["geral"],
    }

def _render_item(item: dict, base_id: str) -> str:
    """Usa display_utils se disponível; caso contrário, fallback simples."""
    if display_utils and hasattr(display_utils, "formatar_item_para_exibicao"):
        try:
            return display_utils.formatar_item_para_exibicao(item)
        except Exception:
            pass
    info_fn = getattr(game_data, "get_item_info", None)
    info = info_fn(base_id) if info_fn else {}  # pode ser {}
    name = info.get("display_name", item.get("display_name", base_id))
    emoji = info.get("emoji", item.get("emoji", ""))
    rarity = item.get("rarity", "?")
    return f"- {emoji} *{name}* (`{rarity}`)"

async def _safe_send(update: Update, text: str):
    try:
        if update.message:
            await update.message.reply_text(text, parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        logger.warning("Falha ao enviar mensagem admin item free: %s", e)

# ---------------------------
# Núcleo: criar + entregar (preferindo NOVO)
# ---------------------------

def _create_item_newstack(
    pdata: dict,
    base_id: str,
    force_rarity: Optional[str],
) -> dict:
    """
    Tenta criar o item usando *somente mecanismos novos*.
    Levanta exceção se não conseguir (para o chamador decidir o fallback).
    Ordem tentada (exemplos comuns em stacks recentes):
      1) new_factory.create_item_from_base(pdata, base_id, force_rarity=...)
      2) new_factory.create_unique_item(pdata, base_id, rarity=...)
      3) new_factory.create(base_id=..., owner=pdata, force_rarity=...)
    """
    if not new_factory:
        raise RuntimeError("item_factory ausente")

    # 1) API mais explícita
    fn = getattr(new_factory, "create_item_from_base", None)
    if callable(fn):
        return fn(pdata, base_id, force_rarity=force_rarity)

    # 2) Outra variação comum
    fn = getattr(new_factory, "create_unique_item", None)
    if callable(fn):
        return fn(pdata, base_id, rarity=force_rarity)

    # 3) Fábrica genérica
    fn = getattr(new_factory, "create", None)
    if callable(fn):
        return fn(base_id=base_id, owner=pdata, force_rarity=force_rarity)

    raise RuntimeError("Nenhuma função conhecida na item_factory")

def _deliver_item_newstack(pdata: dict, item: dict) -> bool:
    """
    Entrega o item usando *APIs novas* se existirem. Retorna True se
    alguma rota funcionou, False caso contrário.
    """
    # Preferências novas
    for fname in ("give_item", "add_item", "add_equipment", "add_to_inventory"):
        fn = getattr(player_manager, fname, None)
        if callable(fn):
            try:
                fn(pdata, item)
                return True
            except Exception as e:
                logger.warning("Falha em player_manager.%s: %s", fname, e)

    # Estrutura direta (último esforço "novo")
    try:
        inv = pdata.setdefault("inventory", [])
        inv.append(item)
        return True
    except Exception:
        return False

def _create_item_legacy(pdata: dict, base_id: str, force_rarity: Optional[str]) -> dict:
    if not crafting_engine:
        raise RuntimeError("crafting_engine ausente para fallback legado")
    recipe_stub = _mk_recipe_stub(base_id, force_rarity)
    # WARNING: chamada privada, MAS só se a nova fábrica não existir
    return crafting_engine._create_dynamic_unique_item(pdata, recipe_stub)  # noqa: SLF001

def _deliver_item_legacy(pdata: dict, item: dict) -> bool:
    fn = getattr(player_manager, "add_unique_item", None)
    if callable(fn):
        try:
            fn(pdata, item)
            return True
        except Exception as e:
            logger.warning("Falha em player_manager.add_unique_item: %s", e)
    return False

# ---------------------------
# Handlers da conversa
# ---------------------------

async def start_create_item_free(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entrada: /admin_item_free ou botão admin_item_free / admin:create_item_free"""
    if update.callback_query:
        await update.callback_query.answer()

    await _safe_send(update, "👤 Envie o *ID numérico* do jogador que receberá o item.")
    return CIF_TARGET

async def receive_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    try:
        target_id = int(text)
    except Exception:
        await _safe_send(update, "❌ ID inválido. Envie apenas números.")
        return CIF_TARGET

    pdata = player_manager.get_player_data(target_id)
    if not pdata:
        await _safe_send(update, "❌ Jogador não encontrado. Tente outro ID.")
        return CIF_TARGET

    context.user_data["cif_target_id"] = target_id
    await _safe_send(
        update,
        "📦 Envie o *base_id* do item e, opcionalmente, a raridade "
        "(`comum`, `bom`, `raro`, `epico`, `lendario`) no formato:\n"
        "`base_id;raridade`\n\nExemplos:\n"
        "`espada_ferro_guerreiro`\n"
        "`espada_ferro_guerreiro;raro`",
    )
    return CIF_BASE

def _parse_base_and_rarity(raw: str) -> Tuple[str, Optional[str]]:
    raw = (raw or "").strip()
    if ";" in raw:
        b, r = [p.strip() for p in raw.split(";", 1)]
        return b, _norm_rarity(r)
    return raw, None

async def receive_base(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = (update.message.text or "").strip()
    base_id, rarity = _parse_base_and_rarity(raw)

    # Validação flexível:
    # - Se existir game_data.get_item_info, checamos.
    # - Se não houver info, ainda tentaremos a fábrica nova (que pode conhecer a base).
    info_fn = getattr(game_data, "get_item_info", None)
    info = info_fn(base_id) if info_fn else None
    if info_fn and not info and not new_factory:
        await _safe_send(update, "❌ `base_id` desconhecido.")
        return CIF_BASE

    target_id = context.user_data.get("cif_target_id")
    pdata = player_manager.get_player_data(target_id)
    if not pdata:
        await _safe_send(update, "❌ Jogador não encontrado (foi removido?). Operação cancelada.")
        return ConversationHandler.END

    # 1) tenta NOVO
    item = None
    err_new = None
    try:
        item = _create_item_newstack(pdata, base_id, rarity)
    except Exception as e:
        err_new = e
        logger.info("Fábrica nova indisponível ou falhou (%s). Tentando legado…", e)

    # 2) se falhou, tenta LEGADO
    if item is None:
        try:
            item = _create_item_legacy(pdata, base_id, rarity)
        except Exception as e:
            logger.exception("Falha ao gerar item (novo e legado): %s", e)
            await _safe_send(update, "❌ Erro ao gerar o item (novo e legado indisponíveis).")
            return ConversationHandler.END

    # Entrega
    delivered = _deliver_item_newstack(pdata, item)
    if not delivered:
        delivered = _deliver_item_legacy(pdata, item)

    if not delivered:
        await _safe_send(update, "❌ Erro ao adicionar o item ao inventário do jogador.")
        return ConversationHandler.END

    # Persiste
    try:
        player_manager.save_player_data(target_id, pdata)
    except Exception as e:
        logger.exception("Falha ao salvar player %s: %s", target_id, e)
        await _safe_send(update, "⚠️ Item criado, mas houve erro ao salvar o jogador. Verifique os logs.")
        return ConversationHandler.END

    # Exibição
    pretty = _render_item(item, base_id)
    await _safe_send(
        update,
        f"✅ Item criado e entregue ao jogador `{target_id}`:\n{pretty}"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _safe_send(update, "Operação cancelada.")
    return ConversationHandler.END

# ---------------------------
# ConversationHandler exportado
# ---------------------------

create_item_free_conv = ConversationHandler(
    entry_points=[
        CommandHandler("admin_item_free", start_create_item_free, filters=filters.User() | filters.ChatType.PRIVATE),
        # aceita os dois padrões de callback
        CallbackQueryHandler(start_create_item_free, pattern=r"^(?:admin_item_free|admin:create_item_free)$"),
    ],
    states={
        CIF_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_target)],
        CIF_BASE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_base)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    name="create_item_free_conv",
    persistent=False,
)
