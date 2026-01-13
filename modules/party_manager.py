# modules/party_manager.py

from __future__ import annotations

import json
import os
from typing import Iterator, Tuple, Optional, Union

from bson import ObjectId

from modules import player_manager

PARTIES_DIR = "parties"
PlayerId = Union[ObjectId, str]


# -----------------------------
# Utils de arquivo / diretório
# -----------------------------
def _ensure_dir_exists():
    os.makedirs(PARTIES_DIR, exist_ok=True)


def _party_file_path(party_id: str) -> str:
    return os.path.join(PARTIES_DIR, f"{party_id}.json")


def _load_json(fp: str) -> Optional[dict]:
    try:
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _dump_json(fp: str, data: dict) -> None:
    tmp = fp + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    os.replace(tmp, fp)


def _normalize_player_id(pid: PlayerId) -> str:
    """
    Normaliza para string de ObjectId (forma canônica usada no arquivo JSON).
    """
    if isinstance(pid, ObjectId):
        return str(pid)
    if isinstance(pid, str) and ObjectId.is_valid(pid.strip()):
        return str(ObjectId(pid.strip()))
    raise ValueError("player_id inválido (esperado ObjectId ou string de ObjectId).")


# -----------------------------
# Leitura / escrita de party
# -----------------------------
def get_party_data(party_id: str) -> Optional[dict]:
    """Busca os dados de um grupo pelo seu ID (party_id é string de ObjectId)."""
    _ensure_dir_exists()
    data = _load_json(_party_file_path(str(party_id)))
    if not data:
        return None

    # saneamento mínimo
    data.setdefault("leader_id", str(party_id))
    data.setdefault("leader_name", "")
    data.setdefault("members", {})
    if not isinstance(data["members"], dict):
        data["members"] = {}

    # campos opcionais usados pelo lobby
    data.setdefault("dungeon_id", None)
    data.setdefault("player_lobby_messages", {})
    if not isinstance(data["player_lobby_messages"], dict):
        data["player_lobby_messages"] = {}

    # normaliza chaves do members / player_lobby_messages
    data["members"] = {str(k): v for k, v in (data["members"].items() if isinstance(data["members"], dict) else [])}
    data["player_lobby_messages"] = {
        str(k): v for k, v in (data["player_lobby_messages"].items() if isinstance(data["player_lobby_messages"], dict) else [])
    }

    return data


def save_party_data(party_id: str, party_info: dict) -> None:
    """Salva os dados de um grupo específico."""
    _ensure_dir_exists()

    party_info = dict(party_info or {})
    party_info["leader_id"] = str(party_info.get("leader_id", party_id))

    members = party_info.get("members") or {}
    party_info["members"] = {str(k): v for k, v in (members.items() if isinstance(members, dict) else [])}

    plm = party_info.get("player_lobby_messages") or {}
    party_info["player_lobby_messages"] = {str(k): v for k, v in (plm.items() if isinstance(plm, dict) else [])}

    _dump_json(_party_file_path(str(party_id)), party_info)


def iter_parties() -> Iterator[Tuple[str, dict]]:
    """Itera sobre (party_id, party_data) existentes."""
    _ensure_dir_exists()
    for fname in os.listdir(PARTIES_DIR):
        if not fname.endswith(".json"):
            continue
        party_id = fname[:-5]
        pdata = get_party_data(party_id)
        if pdata:
            yield party_id, pdata


# -----------------------------
# Regras de capacidade
# -----------------------------
def _get_party_max_players(party_data: dict) -> int:
    """
    Obtém o limite de jogadores do grupo baseado na dungeon associada.
    Fallback: 4.
    """
    try:
        dungeon_id = (party_data or {}).get("dungeon_id")
        if dungeon_id:
            # import lazy para evitar ciclos
            from modules.dungeon_definitions import DUNGEONS  # type: ignore
            info = (DUNGEONS.get(dungeon_id) or {})
            return int(info.get("max_players", 4))
    except Exception:
        pass
    return 4


# -----------------------------
# API principal (ObjectId)
# -----------------------------
async def create_party(leader_id: PlayerId, leader_name: str) -> dict:
    """
    Cria um novo grupo com o jogador como líder.
    party_id = leader_id (string ObjectId).
    Se já existir um grupo com o mesmo ID do líder, desfaz antes.
    """
    party_id = _normalize_player_id(leader_id)

    # limpa uma party antiga com mesmo id (se houver lixo)
    old = get_party_data(party_id)
    if old:
        await disband_party(party_id)

    new_party = {
        "leader_id": party_id,
        "leader_name": leader_name,
        "members": {party_id: leader_name},
        "dungeon_id": None,
        "player_lobby_messages": {}
    }
    save_party_data(party_id, new_party)

    # seta vínculo no jogador (ObjectId)
    pdata = await player_manager.get_player_data(party_id)
    if pdata:
        pdata["party_id"] = party_id
        await player_manager.save_player_data(party_id, pdata)

    return new_party


async def add_member(party_id: str, player_id: PlayerId, character_name: str) -> bool:
    """
    Adiciona um membro a um grupo existente.
    Respeita a capacidade da dungeon (fallback 4).
    """
    party_data = get_party_data(str(party_id))
    if not party_data:
        return False

    # checa capacidade dinâmica
    max_players = _get_party_max_players(party_data)
    members = party_data.get("members", {}) or {}
    if len(members) >= max_players:
        return False

    pid_str = _normalize_player_id(player_id)
    if pid_str in members:
        return True  # já está no grupo

    members[pid_str] = character_name
    party_data["members"] = members
    save_party_data(str(party_id), party_data)

    # vincula no jogador
    pdata = await player_manager.get_player_data(pid_str)
    if pdata:
        pdata["party_id"] = str(party_id)
        await player_manager.save_player_data(pid_str, pdata)

    return True


async def remove_member(party_id: str, player_id: PlayerId) -> None:
    """Remove um membro de um grupo (não remove o líder automaticamente)."""
    party_data = get_party_data(str(party_id))
    if not party_data:
        return

    pid_str = _normalize_player_id(player_id)

    members = party_data.get("members", {}) or {}
    if pid_str in members:
        del members[pid_str]
        party_data["members"] = members
        save_party_data(str(party_id), party_data)

    pdata = await player_manager.get_player_data(pid_str)
    if pdata:
        pdata["party_id"] = None
        await player_manager.save_player_data(pid_str, pdata)


async def disband_party(party_id: str) -> None:
    """Desfaz o grupo e limpa os dados de todos os membros."""
    party_data = get_party_data(str(party_id))
    if not party_data:
        fp = _party_file_path(str(party_id))
        if os.path.exists(fp):
            os.remove(fp)
        return

    # limpa vínculo em todos os membros
    for member_id in list((party_data.get("members") or {}).keys()):
        if not (isinstance(member_id, str) and ObjectId.is_valid(member_id)):
            continue

        pdata = await player_manager.get_player_data(member_id)
        if pdata:
            pdata["party_id"] = None
            await player_manager.save_player_data(member_id, pdata)

    # remove arquivo
    fp = _party_file_path(str(party_id))
    if os.path.exists(fp):
        os.remove(fp)


# -----------------------------
# Ajuda ao fluxo de convite
# -----------------------------
def get_party_of(player_id: PlayerId) -> Optional[str]:
    """
    Retorna o party_id do grupo ao qual o jogador pertence, ou None.
    Usado para bloquear convite se o alvo já estiver em outro grupo.
    """
    try:
        pid_str = _normalize_player_id(player_id)
    except Exception:
        return None

    for pid, pdata in iter_parties():
        if pid_str in (pdata.get("members") or {}):
            return pid
    return None
