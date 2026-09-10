# modules/combat/group_combat_manager.py
# ==========================================================
# CÉREBRO OFICIAL DO COMBATE EM GRUPO - ELDORA
# ==========================================================
# Responsável por coordenar todo combate em grupo:
# - Caçadas em grupo
# - Dungeons
# - Raids
# - Boss mundial
# - Eventos especiais
# - PvP em grupo futuramente
#
# IMPORTANTE:
# Este módulo NÃO substitui o combat_engine.py.
# O combat_engine.py continua sendo o motor matemático de dano.
# Este manager apenas organiza sala, membros, turnos, mobs, sincronização
# e estado compartilhado da batalha.
# ==========================================================

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple


# Dicionário global em memória para as batalhas ativas.
# Em produção futura, pode ser migrado para Redis/Mongo se precisar persistência.
batalhas_grupo_ativas: Dict[str, Dict[str, Any]] = {}


TIPO_CACADA = "cacada"
TIPO_DUNGEON = "dungeon"
TIPO_RAID = "raid"
TIPO_EVENTO = "evento"
TIPO_BOSS_MUNDIAL = "boss_mundial"
TIPO_PVP_GRUPO = "pvp_grupo"

ESTADO_AGUARDANDO = "aguardando"
ESTADO_EM_ANDAMENTO = "em_andamento"
ESTADO_VITORIA = "vitoria"
ESTADO_DERROTA = "derrota"
ESTADO_CANCELADA = "cancelada"


# ==========================================================
# HELPERS
# ==========================================================

def _novo_sala_id(prefixo: str = "grupo") -> str:
    return f"{prefixo}_{uuid.uuid4().hex[:10]}"


def _agora() -> float:
    return time.time()


def _normalizar_id(valor: Any) -> str:
    return str(valor) if valor is not None else ""


def _montar_combatente_heroi(heroi: Dict[str, Any]) -> Dict[str, Any]:
    """Cria o registro resumido do herói para fila/turno."""
    char_id = _normalizar_id(heroi.get("char_id") or heroi.get("id") or heroi.get("_id"))
    return {
        "id": char_id,
        "tipo": "heroi",
        "nome": heroi.get("nome") or heroi.get("character_name") or "Herói",
        "initiative": int(heroi.get("initiative", 5) or 5),
        "vivo": int(heroi.get("current_hp", heroi.get("hp", 1)) or 1) > 0,
        "ref_dados": heroi,
    }


def _montar_combatente_mob(mob: Dict[str, Any], indice: int) -> Dict[str, Any]:
    """Cria o registro resumido do monstro para fila/turno."""
    mob_id = _normalizar_id(mob.get("id")) or f"mob_{indice + 1}"
    mob["id"] = mob_id
    return {
        "id": mob_id,
        "tipo": "monstro",
        "nome": mob.get("name") or mob.get("nome") or "Monstro",
        "initiative": int(mob.get("initiative", 2) or 2),
        "vivo": int(mob.get("hp_atual", mob.get("hp", 1)) or 1) > 0,
        "ref_dados": mob,
    }


def _gerar_fila_iniciativa(herois: List[Dict[str, Any]], mobs: List[Dict[str, Any]]) -> List[str]:
    combatentes: List[Dict[str, Any]] = []

    for heroi in herois:
        combatentes.append(_montar_combatente_heroi(heroi))

    combatentes.sort(key=lambda c: c.get("initiative", 0), reverse=True)
    return [c["id"] for c in combatentes]

def _ids_membros(herois: List[Dict[str, Any]]) -> List[str]:
    ids = []
    for h in herois:
        hid = _normalizar_id(h.get("char_id") or h.get("id") or h.get("_id"))
        if hid:
            ids.append(hid)
    return ids


# ==========================================================
# CRIAÇÃO DE SALAS
# ==========================================================

def criar_sala_combate_grupo(
    *,
    tipo: str,
    equipe_herois: List[Dict[str, Any]],
    mobs: List[Dict[str, Any]],
    regiao: str,
    lider_id: Optional[str] = None,
    grupo_id: Optional[str] = None,
    spawn_id: Optional[str] = None,
    dungeon_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Cria uma sala genérica de combate em grupo.

    Use para caçada, dungeon, raid, boss mundial, evento e PvP futuro.
    """
    if not equipe_herois:
        raise ValueError("Não é possível criar combate em grupo sem heróis.")
    if not mobs:
        raise ValueError("Não é possível criar combate em grupo sem monstros/alvos.")

    tipo = tipo or TIPO_CACADA
    sala_id = _novo_sala_id(tipo)
    membros_ids = _ids_membros(equipe_herois)
    lider_id = _normalizar_id(lider_id or membros_ids[0])

    fila = _gerar_fila_iniciativa(equipe_herois, mobs)

    sala = {
        "sala_id": sala_id,
        "tipo": tipo,
        "estado": ESTADO_AGUARDANDO,
        "membros_prontos": {
            str(mid): False for mid in membros_ids
        },
        "tempo_aguardando_inicio": _agora(),
        "grupo_id": _normalizar_id(grupo_id) if grupo_id else None,
        "lider_id": lider_id,
        "membros_ids": membros_ids,
        "regiao": regiao,
        "spawn_id": spawn_id,
        "dungeon_id": dungeon_id,
        "herois": {
            _normalizar_id(h.get("char_id") or h.get("id") or h.get("_id")): h
            for h in equipe_herois
        },
        "mobs": {
            _normalizar_id(m.get("id")): m
            for m in mobs
        },
        "fila_iniciativa": fila,
        "index_turno_atual": 0,
        "tempo_inicio_turno": _agora(),
        "criado_em": _agora(),
        "atualizado_em": _agora(),
        "logs": [],
        "metadata": metadata or {},
    }

    batalhas_grupo_ativas[sala_id] = sala
    return sala


def criar_cacada_grupo(
    *,
    equipe_herois: List[Dict[str, Any]],
    mob_vivo: Dict[str, Any],
    regiao: str,
    spawn_id: str,
    lider_id: Optional[str] = None,
    grupo_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Cria uma sala de caçada em grupo usando o mob vivo do mapa.

    Importante:
    O mob_vivo deve ser a própria referência de sistema_cacada.mobs_vivos[regiao][spawn_id].
    Assim, o HP compartilhado continua funcionando.
    """
    return criar_sala_combate_grupo(
        tipo=TIPO_CACADA,
        equipe_herois=equipe_herois,
        mobs=[mob_vivo],
        regiao=regiao,
        lider_id=lider_id,
        grupo_id=grupo_id,
        spawn_id=spawn_id,
        metadata={"origem": "sistema_cacada.mobs_vivos"},
    )


def criar_dungeon_grupo(
    *,
    equipe_herois: List[Dict[str, Any]],
    mobs: List[Dict[str, Any]],
    regiao: str,
    dungeon_id: str,
    lider_id: Optional[str] = None,
    grupo_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Cria uma sala de dungeon/instância em grupo."""
    return criar_sala_combate_grupo(
        tipo=TIPO_DUNGEON,
        equipe_herois=equipe_herois,
        mobs=mobs,
        regiao=regiao,
        lider_id=lider_id,
        grupo_id=grupo_id,
        dungeon_id=dungeon_id,
        metadata=metadata or {},
    )


# ==========================================================
# CONSULTAS
# ==========================================================

def obter_sala(sala_id: str) -> Optional[Dict[str, Any]]:
    return batalhas_grupo_ativas.get(sala_id)


def obter_sala_do_jogador(char_id: str) -> Optional[Dict[str, Any]]:
    char_id = _normalizar_id(char_id)
    for sala in batalhas_grupo_ativas.values():
        if sala.get("estado") not in [ESTADO_EM_ANDAMENTO, ESTADO_AGUARDANDO]:
            continue
        if char_id in sala.get("membros_ids", []):
            return sala
    return None


def obter_sala_por_spawn(regiao: str, spawn_id: str) -> Optional[Dict[str, Any]]:
    for sala in batalhas_grupo_ativas.values():
        if sala.get("estado") not in [ESTADO_EM_ANDAMENTO, ESTADO_AGUARDANDO]:
            continue
        if sala.get("regiao") == regiao and sala.get("spawn_id") == spawn_id:
            return sala
    return None


def jogador_esta_em_combate_grupo(char_id: str) -> bool:
    return obter_sala_do_jogador(char_id) is not None


# ==========================================================
# TURNOS
# ==========================================================

def pegar_combatente_atual(sala_id: str) -> Optional[str]:
    sala = obter_sala(sala_id)
    if not sala:
        return None

    fila = sala.get("fila_iniciativa", [])
    if not fila:
        return None

    idx = int(sala.get("index_turno_atual", 0) or 0)
    if idx >= len(fila):
        idx = 0
        sala["index_turno_atual"] = 0

    return fila[idx]


def eh_turno_do_jogador(sala_id: str, char_id: str) -> bool:
    return _normalizar_id(char_id) == pegar_combatente_atual(sala_id)

def marcar_membro_pronto(sala_id: str, char_id: str) -> Optional[Dict[str, Any]]:
    sala = obter_sala(sala_id)
    if not sala:
        return None

    char_id = _normalizar_id(char_id)

    if char_id not in sala.get("membros_ids", []):
        return sala

    sala.setdefault("membros_prontos", {})

    for mid in sala.get("membros_ids", []):
        sala["membros_prontos"].setdefault(str(mid), False)

    sala["membros_prontos"][char_id] = True
    sala["atualizado_em"] = _agora()

    todos_prontos = all(
        sala["membros_prontos"].get(str(mid), False)
        for mid in sala.get("membros_ids", [])
    )

    if todos_prontos and sala.get("estado") == ESTADO_AGUARDANDO:
        sala["estado"] = ESTADO_EM_ANDAMENTO
        sala["tempo_inicio_turno"] = _agora()
        sala["atualizado_em"] = _agora()

    return sala

def avancar_turno(sala_id: str) -> Optional[str]:
    sala = obter_sala(sala_id)
    if not sala:
        return None

    fila = sala.get("fila_iniciativa", [])
    if not fila:
        return None

    idx_atual = int(sala.get("index_turno_atual", 0) or 0)
    total = len(fila)

    for i in range(1, total + 1):
        novo_idx = (idx_atual + i) % total
        candidato_id = str(fila[novo_idx])

        heroi = sala.get("herois", {}).get(candidato_id)
        if not heroi:
            continue

        hp = int(heroi.get("current_hp", heroi.get("hp", 1)) or 0)
        if hp > 0:
            sala["index_turno_atual"] = novo_idx
            sala["tempo_inicio_turno"] = _agora()
            sala["atualizado_em"] = _agora()
            return candidato_id

    return pegar_combatente_atual(sala_id)

def remover_combatente_da_fila(sala_id: str, combatente_id: str) -> None:
    sala = obter_sala(sala_id)
    if not sala:
        return

    combatente_id = _normalizar_id(combatente_id)
    fila = sala.get("fila_iniciativa", [])
    if combatente_id not in fila:
        return

    idx_atual = int(sala.get("index_turno_atual", 0) or 0)
    idx_removido = fila.index(combatente_id)
    fila.remove(combatente_id)

    if idx_removido < idx_atual:
        sala["index_turno_atual"] = max(0, idx_atual - 1)
    elif sala["index_turno_atual"] >= len(fila):
        sala["index_turno_atual"] = 0

    sala["atualizado_em"] = _agora()


# ==========================================================
# ESTADO DE HP / MOBS / HEROIS
# ==========================================================

def atualizar_hp_mob(sala_id: str, mob_id: str, novo_hp: int) -> Optional[Dict[str, Any]]:
    sala = obter_sala(sala_id)
    if not sala:
        return None

    mob_id = _normalizar_id(mob_id)
    mob = sala.get("mobs", {}).get(mob_id)
    if not mob:
        return None

    mob["hp_atual"] = max(0, int(novo_hp))
    if mob["hp_atual"] <= 0:
        mob["vivo"] = False
        remover_combatente_da_fila(sala_id, mob_id)

    sala["atualizado_em"] = _agora()
    verificar_fim_combate(sala_id)
    return mob


def aplicar_dano_mob(sala_id: str, mob_id: str, dano: int) -> Optional[Dict[str, Any]]:
    sala = obter_sala(sala_id)
    if not sala:
        return None

    mob_id = _normalizar_id(mob_id)
    mob = sala.get("mobs", {}).get(mob_id)
    if not mob:
        return None

    hp_atual = int(mob.get("hp_atual", mob.get("hp", 0)) or 0)
    return atualizar_hp_mob(sala_id, mob_id, hp_atual - int(dano or 0))


def atualizar_hp_heroi(sala_id: str, char_id: str, novo_hp: int) -> Optional[Dict[str, Any]]:
    sala = obter_sala(sala_id)
    if not sala:
        return None

    char_id = _normalizar_id(char_id)
    heroi = sala.get("herois", {}).get(char_id)
    if not heroi:
        return None

    heroi["current_hp"] = max(0, int(novo_hp))
    if heroi["current_hp"] <= 0:
        heroi["vivo"] = False
        remover_combatente_da_fila(sala_id, char_id)

    sala["atualizado_em"] = _agora()
    verificar_fim_combate(sala_id)
    return heroi


def mobs_vivos(sala: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [m for m in sala.get("mobs", {}).values() if int(m.get("hp_atual", m.get("hp", 0)) or 0) > 0]


def herois_vivos(sala: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [h for h in sala.get("herois", {}).values() if int(h.get("current_hp", h.get("hp", 1)) or 0) > 0]


def verificar_fim_combate(sala_id: str) -> str:
    sala = obter_sala(sala_id)
    if not sala:
        return ESTADO_CANCELADA

    if sala.get("estado") not in [ESTADO_EM_ANDAMENTO, ESTADO_AGUARDANDO]:
        return sala.get("estado", ESTADO_CANCELADA)

    if not mobs_vivos(sala):
        sala["estado"] = ESTADO_VITORIA
    elif not herois_vivos(sala):
        sala["estado"] = ESTADO_DERROTA

    sala["atualizado_em"] = _agora()
    return sala["estado"]


# ==========================================================
# LOGS E PACOTES PARA FRONTEND/SOCKET
# ==========================================================

def adicionar_log(sala_id: str, autor: str, texto: str, tipo: str = "sistema", dano: int = 0) -> None:
    sala = obter_sala(sala_id)
    if not sala:
        return

    sala.setdefault("logs", []).append({
        "ts": _agora(),
        "autor": autor,
        "texto": texto,
        "tipo": tipo,
        "dano": int(dano or 0),
    })
    sala["atualizado_em"] = _agora()


def pacote_estado_sala(sala_id: str) -> Optional[Dict[str, Any]]:
    """Retorna um pacote seguro para enviar ao frontend."""
    sala = obter_sala(sala_id)
    if not sala:
        return None

    return {
        "sala_id": sala["sala_id"],
        "tipo": sala["tipo"],
        "estado": sala["estado"],
        "grupo_id": sala.get("grupo_id"),
        "lider_id": sala.get("lider_id"),
        "membros_ids": sala.get("membros_ids", []),
        "membros_prontos": sala.get("membros_prontos", {}),
        "todos_prontos": all(
            (sala.get("membros_prontos", {}) or {}).get(str(mid), False)
            for mid in sala.get("membros_ids", [])
        ),
        "regiao": sala.get("regiao"),
        "spawn_id": sala.get("spawn_id"),
        "dungeon_id": sala.get("dungeon_id"),
        "turno_atual": pegar_combatente_atual(sala_id),
        "fila_iniciativa": sala.get("fila_iniciativa", []),
        "herois": list(sala.get("herois", {}).values()),
        "mobs": list(sala.get("mobs", {}).values()),
        "logs": sala.get("logs", [])[-20:],
    }

def emitir_para_membros(socketio: Any, sala_id: str, evento: str, payload: Dict[str, Any], jogadores_online: Dict[str, Dict[str, Any]]) -> None:
    """
    Envia um evento Socket.IO para todos os membros da sala.

    jogadores_online esperado no formato do main.py:
    {
        sid: {"char_id": "...", "nome": "...", ...}
    }
    """
    sala = obter_sala(sala_id)
    if not sala or not socketio:
        return

    membros = set(map(str, sala.get("membros_ids", [])))
    for sid, info in list((jogadores_online or {}).items()):
        if str(info.get("char_id")) in membros:
            socketio.emit(evento, payload, to=sid)


def broadcast_estado(socketio: Any, sala_id: str, jogadores_online: Dict[str, Dict[str, Any]], evento: str = "grupoCombateEstado") -> None:
    pacote = pacote_estado_sala(sala_id)
    if pacote:
        emitir_para_membros(socketio, sala_id, evento, pacote, jogadores_online)


# ==========================================================
# ENTRADA / SAÍDA / ENCERRAMENTO
# ==========================================================

def adicionar_heroi_na_sala(sala_id: str, heroi: Dict[str, Any]) -> bool:
    sala = obter_sala(sala_id)
    if not sala:
        return False

    char_id = _normalizar_id(heroi.get("char_id") or heroi.get("id") or heroi.get("_id"))
    if not char_id:
        return False

    if char_id not in sala["herois"]:
        sala["herois"][char_id] = heroi
        sala["membros_ids"].append(char_id)
        sala["fila_iniciativa"] = _gerar_fila_iniciativa(
            list(sala["herois"].values()),
            list(sala["mobs"].values()),
        )
        sala["index_turno_atual"] = 0
        sala["atualizado_em"] = _agora()

    return True


def remover_heroi_da_sala(sala_id: str, char_id: str) -> bool:
    sala = obter_sala(sala_id)
    if not sala:
        return False

    char_id = _normalizar_id(char_id)
    sala.get("herois", {}).pop(char_id, None)
    sala["membros_ids"] = [mid for mid in sala.get("membros_ids", []) if str(mid) != char_id]
    remover_combatente_da_fila(sala_id, char_id)
    sala["atualizado_em"] = _agora()
    verificar_fim_combate(sala_id)
    return True


def encerrar_sala(sala_id: str, estado: str = ESTADO_CANCELADA, remover: bool = False) -> Optional[Dict[str, Any]]:
    sala = obter_sala(sala_id)
    if not sala:
        return None

    sala["estado"] = estado
    sala["atualizado_em"] = _agora()

    if remover:
        return batalhas_grupo_ativas.pop(sala_id, None)
    return sala


def limpar_salas_antigas(max_idade_segundos: int = 60 * 60) -> int:
    """Remove salas encerradas/antigas da memória."""
    agora = _agora()
    removidas = 0

    for sala_id, sala in list(batalhas_grupo_ativas.items()):
        idade = agora - float(sala.get("atualizado_em", sala.get("criado_em", agora)))
        encerrada = sala.get("estado") in [ESTADO_VITORIA, ESTADO_DERROTA, ESTADO_CANCELADA]
        if encerrada and idade > max_idade_segundos:
            batalhas_grupo_ativas.pop(sala_id, None)
            removidas += 1

    return removidas


# ==========================================================
# PONTOS DE INTEGRAÇÃO FUTUROS
# ==========================================================

async def processar_acao_grupo_placeholder(*args, **kwargs) -> Dict[str, Any]:
    """
    Placeholder proposital.

    A próxima etapa é ligar aqui o combat_engine.processar_acao_combate()
    ou reaproveitar parte de stats.processar_turno_combate(), mas sem duplicar regra.
    """
    return {
        "sucesso": False,
        "erro": "processar_acao_grupo ainda não foi conectado ao combat_engine.",
    }
