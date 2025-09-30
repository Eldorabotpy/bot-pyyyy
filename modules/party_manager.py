# modules/party_manager.py

import json
import os
from typing import Iterator, Tuple, Optional

from modules import player_manager

PARTIES_DIR = "parties"


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


# -----------------------------
# Leitura / escrita de party
# -----------------------------
def get_party_data(party_id: str) -> Optional[dict]:
    """Busca os dados de um grupo pelo seu ID."""
    _ensure_dir_exists()
    data = _load_json(_party_file_path(party_id))
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
    return data

def save_party_data(party_id: str, party_info: dict) -> None:
    """Salva os dados de um grupo específico."""
    _ensure_dir_exists()
    # normaliza tipos
    party_info = dict(party_info or {})
    party_info["leader_id"] = str(party_info.get("leader_id", party_id))
    # garante dicts básicos
    members = party_info.get("members") or {}
    party_info["members"] = {str(k): v for k, v in (members.items() if isinstance(members, dict) else [])}
    plm = party_info.get("player_lobby_messages") or {}
    party_info["player_lobby_messages"] = {str(k): v for k, v in (plm.items() if isinstance(plm, dict) else [])}
    # grava
    _dump_json(_party_file_path(party_id), party_info)


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
# API principal
# -----------------------------
def create_party(leader_id: str, leader_name: str) -> dict:
    """
    Cria um novo grupo com o jogador como líder.
    Se já existir um grupo com o mesmo ID do líder, desfaz antes.
    """
    party_id = str(leader_id)
    # limpa uma party antiga com mesmo id (se houver lixo)
    old = get_party_data(party_id)
    if old:
        disband_party(party_id)

    new_party = {
        "leader_id": party_id,
        "leader_name": leader_name,
        "members": {party_id: leader_name},
        # campos opcionais, serão ajustados depois pelo fluxo
        "dungeon_id": None,
        "player_lobby_messages": {}
    }
    save_party_data(party_id, new_party)

    # seta vínculo no jogador
    p = player_manager.get_player_data(int(leader_id))
    if p:
        p["party_id"] = party_id
        player_manager.save_player_data(int(leader_id), p)

    return new_party


def add_member(party_id: str, user_id: int | str, character_name: str) -> bool:
    """
    Adiciona um membro a um grupo existente.
    Respeita a capacidade da dungeon (fallback 4).
    """
    party_data = get_party_data(party_id)
    if not party_data:
        return False

    # checa capacidade dinâmica
    max_players = _get_party_max_players(party_data)
    members = party_data.get("members", {})
    if len(members) >= max_players:
        return False

    uid_str = str(user_id)
    if uid_str in members:
        return True  # já está no grupo

    members[uid_str] = character_name
    party_data["members"] = members
    save_party_data(party_id, party_data)

    # vincula no jogador
    p = player_manager.get_player_data(int(user_id))
    if p:
        p["party_id"] = party_id
        player_manager.save_player_data(int(user_id), p)
    return True


def remove_member(party_id: str, user_id: int | str) -> None:
    """Remove um membro de um grupo (não deixa o líder automaticamente)."""
    party_data = get_party_data(party_id)
    if not party_data:
        return

    uid = str(user_id)
    if uid in party_data.get("members", {}):
        del party_data["members"][uid]
        save_party_data(party_id, party_data)

    p = player_manager.get_player_data(int(user_id))
    if p:
        p["party_id"] = None
        player_manager.save_player_data(int(user_id), p)


def disband_party(party_id: str) -> None:
    """Desfaz o grupo e limpa os dados de todos os membros."""
    party_data = get_party_data(party_id)
    if not party_data:
        # nada a fazer
        fp = _party_file_path(party_id)
        if os.path.exists(fp):
            os.remove(fp)
        return

    # limpa vínculo em todos os membros
    for member_id in list(party_data.get("members", {}).keys()):
        try:
            uid = int(member_id)
        except Exception:
            continue
        p = player_manager.get_player_data(uid)
        if p:
            p["party_id"] = None
            player_manager.save_player_data(uid, p)

    # remove arquivo
    fp = _party_file_path(party_id)
    if os.path.exists(fp):
        os.remove(fp)


# -----------------------------
# Ajuda ao fluxo de convite
# -----------------------------
def get_party_of(user_id: int | str) -> Optional[str]:
    """
    Retorna o party_id do grupo ao qual 'user_id' pertence, ou None.
    Usado para bloquear convite se o alvo já estiver em outro grupo.
    """
    uid = str(user_id)
    for pid, pdata in iter_parties():
        if uid in (pdata.get("members") or {}):
            return pid
    return None
