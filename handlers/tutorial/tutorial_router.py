# handlers/tutorial/tutorial_router.py

from __future__ import annotations
from typing import Optional, Tuple

from telegram import Update
from telegram.ext import ContextTypes

from handlers.tutorial import dora_intro, dora_profession, dora_gathering


def _needs_name(player_data: dict) -> bool:
    name = (player_data.get("character_name") or "").strip()
    return not name


def _needs_profession(player_data: dict) -> bool:
    prof = player_data.get("profession", {}) or {}
    return not (prof.get("type") or prof.get("key"))


def _is_gathering_prof(player_data: dict) -> bool:
    # dora_profession salva "type"
    prof = player_data.get("profession", {}) or {}
    pkey = prof.get("type") or prof.get("key")
    if not pkey:
        return False
    return dora_profession.is_gathering_profession(pkey)


def _did_first_collect(player_data: dict) -> bool:
    flags = player_data.get("tutorial_flags", {}) or {}
    return bool(flags.get("did_first_collect"))


async def route_onboarding(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    player_data: dict,
) -> bool:
    """
    Retorna True se o tutorial assumiu o controle (não deve abrir reino/região).
    Retorna False se pode seguir o jogo normal.
    """

    # 1) Nome do personagem (primeira etapa após login/cadastro)
    if _needs_name(player_data):
        await dora_intro.show_intro(update, context, player_data)
        return True

    # 2) Escolha de profissão
    if _needs_profession(player_data):
        await dora_profession.show_profession_menu(update, context, player_data)
        return True

    # 3) Se for coleta e ainda não fez a primeira coleta, entra no capítulo de coleta
    if _is_gathering_prof(player_data) and not _did_first_collect(player_data):
        await dora_gathering.show_gathering_chapter(update, context, player_data)
        return True

    # 4) Tudo ok
    return False
