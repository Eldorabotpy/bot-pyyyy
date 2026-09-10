# modules/events/dimensional_boss_manager.py

from __future__ import annotations

import copy
import random
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from bson import ObjectId

from modules.player.core import users_collection
from modules.player.combat_stats import get_combat_stats_sync
from modules.events.dimensional_boss_registry import BOSS_DIMENSIONAL_CONFIG


_evento_dimensional_ativo: Optional[Dict[str, Any]] = None
_contadores_abates_dimensional: Dict[str, Dict[str, Any]] = {}

def _agora() -> float:
    return time.time()


def _novo_evento_id() -> str:
    return f"dimensional_{uuid.uuid4().hex[:10]}"


def _normalizar_user_id(user_id) -> str:
    return str(user_id or "").strip()


def _buscar_player(user_id: str) -> Optional[dict]:
    try:
        if ObjectId.is_valid(str(user_id)):
            return users_collection.find_one({"_id": ObjectId(str(user_id))})
    except Exception:
        pass

    try:
        if str(user_id).isdigit():
            return users_collection.find_one({
                "$or": [
                    {"telegram_id": int(user_id)},
                    {"last_chat_id": int(user_id)}
                ]
            })
    except Exception:
        pass

    return None

def _resolver_user_id_no_evento(evento: Dict[str, Any], user_id: str) -> str:
    """
    Garante que, se vier telegram_id ou outro id, a gente tente resolver
    para o _id real do personagem dentro da sala.
    """
    user_id = _normalizar_user_id(user_id)
    jogadores = evento.get("jogadores", {}) or {}

    if user_id in jogadores:
        return user_id

    pdata = _buscar_player(user_id)

    if pdata:
        char_id = str(pdata.get("_id", user_id))
        if char_id in jogadores:
            return char_id

    return user_id

def _log_evento_dimensional(evento: Dict[str, Any], texto: str, tipo: str = "sistema"):
    evento.setdefault("logs", []).append({
        "ts": _agora(),
        "tipo": tipo,
        "texto": texto
    })

    evento["logs"] = evento["logs"][-40:]


def verificar_inicio_automatico(evento: Optional[Dict[str, Any]] = None, motivo: str = "verificacao") -> Optional[Dict[str, Any]]:
    """
    Regras da entrada da Fenda:
    - Se encheu 20/20, inicia automaticamente.
    - Se o tempo acabou e tem jogador dentro, inicia automaticamente.
    - Se o tempo acabou e ninguém entrou, remove a Fenda.
    """
    global _evento_dimensional_ativo

    evento = evento or _evento_dimensional_ativo

    if not evento:
        return None

    if evento.get("status") in ["em_combate", "vitoria", "derrota"]:
        return evento

    if evento.get("status") in ["finalizado", "cancelado"]:
        return None

    if evento.get("status") != "aguardando_jogadores":
        return evento

    jogadores = evento.get("jogadores") or {}
    qtd_jogadores = len(jogadores)
    max_jogadores = int(evento.get("max_jogadores", 20) or 20)

    entrada_encerra_em = float(evento.get("entrada_encerra_em", 0) or 0)
    tempo_acabou = entrada_encerra_em > 0 and _agora() >= entrada_encerra_em
    lotou = qtd_jogadores >= max_jogadores

    if not tempo_acabou and not lotou:
        return evento

    if qtd_jogadores <= 0:
        _log_evento_dimensional(
            evento,
            "O tempo de entrada acabou e nenhum herói entrou. A Fenda Dimensional se fechou.",
            "cancelado"
        )

        evento["status"] = "cancelado"
        evento["finalizado"] = True
        _evento_dimensional_ativo = None
        return None

    if lotou:
        _log_evento_dimensional(
            evento,
            f"A Fenda atingiu {qtd_jogadores}/{max_jogadores} heróis e iniciou automaticamente.",
            "sistema"
        )
    elif tempo_acabou:
        _log_evento_dimensional(
            evento,
            "O tempo de entrada acabou. A batalha iniciou automaticamente com os heróis presentes.",
            "sistema"
        )

    from modules.events import dimensional_boss_engine as engine

    resultado = engine.iniciar_batalha_evento(evento)

    if resultado.get("success"):
        evento["inicio_automatico"] = True
        evento["inicio_motivo"] = motivo
        return evento

    return evento

def serializar_evento(evento: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    evento = evento or _evento_dimensional_ativo

    if not evento:
        return None

    evento = verificar_inicio_automatico(evento, "serializar")

    if not evento:
        return None

    saida = copy.deepcopy(evento)

    jogadores_dict = saida.get("jogadores", {}) or {}

    saida["jogadores_lista"] = list(jogadores_dict.values())
    saida["qtd_jogadores"] = len(jogadores_dict)
    saida["max_jogadores"] = int(saida.get("max_jogadores", 20))

    entrada_encerra_em = float(saida.get("entrada_encerra_em", 0) or 0)
    saida["tempo_entrada_restante"] = max(0, int(entrada_encerra_em - _agora()))

    return saida

def _nome_mapa_dimensional(mapa: str) -> str:
    nomes = {
        "capital_eldora": "Capital de Eldora",
        "pradaria_inicial": "Pradaria Inicial",
        "floresta_sombria": "Floresta Sombria",
        "pedreira_granito": "Pedreira de Granito",
    }

    return nomes.get(str(mapa or ""), str(mapa or "mapa desconhecido").replace("_", " ").title())


def _config_abates_dimensional(mapa: str) -> Dict[str, Any]:
    cfg_spawn = BOSS_DIMENSIONAL_CONFIG.get("spawn_por_abates") or {}
    default = cfg_spawn.get("default") or {}

    conf_mapa = cfg_spawn.get(mapa) or {}

    return {
        "ativo": bool(cfg_spawn.get("ativo", True)),
        "limite_abates": int(
            conf_mapa.get(
                "limite_abates",
                default.get("limite_abates", 500)
            ) or 500
        ),
        "chance_percent": float(
            conf_mapa.get(
                "chance_percent",
                default.get("chance_percent", 100)
            ) or 100
        ),
    }


def _emitir_fenda_dimensional_surgiu(socketio, evento: Dict[str, Any], motivo: str = "abates"):
    if not evento:
        return

    mapa_evento = evento.get("mapa") or evento.get("regiao") or "mapa_desconhecido"
    mapa_nome = _nome_mapa_dimensional(mapa_evento)

    mensagem = f"🌌 Uma Fenda Dimensional surgiu em {mapa_nome}!"

    payload_socket = {
        "evento": evento,
        "evento_id": evento.get("evento_id"),
        "mapa": mapa_evento,
        "regiao": mapa_evento,
        "mapa_nome": mapa_nome,
        "entrada_encerra_em": evento.get("entrada_encerra_em"),
        "tempo_entrada_restante": evento.get("tempo_entrada_restante"),
        "max_jogadores": evento.get("max_jogadores"),
        "origem": motivo,
        "mensagem": mensagem
    }

    try:
        if socketio:
            socketio.emit("fendaDimensionalSurgiu", payload_socket)
            socketio.emit("novaMensagemChat", {
                "remetente": "Sistema",
                "texto": mensagem,
                "tipo": "evento"
            })

            print(f"🌌 [DIMENSIONAL SOCKET] Fenda emitida por {motivo}: {mapa_evento}")
    except Exception as e:
        print(f"⚠️ [DIMENSIONAL SOCKET] Falha ao emitir Fenda automática: {e}")

    try:
        users_collection.database.client["eldora_bot"]["chat_historico"].insert_one({
            "remetente": "Sistema",
            "texto": mensagem,
            "alvo": "global",
            "tipo": "evento",
            "origem": motivo,
            "data_envio": datetime.utcnow()
        })
    except Exception as e:
        print(f"⚠️ [DIMENSIONAL CHAT] Falha ao salvar aviso da Fenda automática: {e}")


def registrar_abate_mapa(
    regiao: str,
    spawn_id: Optional[str] = None,
    monster_id: Optional[str] = None,
    socketio=None
) -> Dict[str, Any]:
    """
    Registra abate de mob normal.

    REGRA:
    - O contador é GERAL para todos os mapas permitidos.
    - O mapa onde o último mob morreu é o mapa onde a Fenda nasce.
    """
    regiao = str(regiao or "").strip()
    spawn_id = str(spawn_id or "").strip()
    monster_id = str(monster_id or "").strip()

    if not regiao:
        return {
            "success": False,
            "error": "Região inválida."
        }

    mapas_permitidos = set(BOSS_DIMENSIONAL_CONFIG.get("mapas_permitidos", []))

    if regiao not in mapas_permitidos:
        return {
            "success": True,
            "contou": False,
            "motivo": "mapa_nao_permitido",
            "regiao": regiao
        }

    # Configuração global.
    # Usa o bloco default do registry como fonte principal.
    conf = _config_abates_dimensional("default")

    if not conf.get("ativo", True):
        return {
            "success": True,
            "contou": False,
            "motivo": "contador_desativado",
            "regiao": regiao
        }

    # Se já existe Fenda ativa, não cria outra e não soma.
    if obter_evento_ativo():
        contador_atual = _contadores_abates_dimensional.get("__global__", {}).get("abates", 0)

        return {
            "success": True,
            "contou": False,
            "motivo": "fenda_ja_ativa",
            "regiao": regiao,
            "abates": contador_atual
        }

    contador = _contadores_abates_dimensional.setdefault("__global__", {
        "tipo": "global",
        "abates": 0,
        "limite_abates": int(conf.get("limite_abates", 500)),
        "chance_percent": float(conf.get("chance_percent", 100)),
        "ultimo_mapa": None,
        "ultimo_spawn_id": None,
        "ultimo_monster_id": None,
        "atualizado_em": _agora(),
        "eventos_criados": 0
    })

    limite = int(
        conf.get(
            "limite_abates",
            contador.get("limite_abates", 500)
        ) or 500
    )

    chance = float(conf.get("chance_percent", contador.get("chance_percent", 100)) or 100)

    contador["limite_abates"] = limite
    contador["chance_percent"] = chance
    contador["abates"] = int(contador.get("abates", 0) or 0) + 1

    # Este mapa é importante:
    # se bater o limite agora, a Fenda nasce aqui.
    contador["ultimo_mapa"] = regiao
    contador["ultimo_spawn_id"] = spawn_id
    contador["ultimo_monster_id"] = monster_id
    contador["atualizado_em"] = _agora()

    if contador["abates"] < limite:
        return {
            "success": True,
            "contou": True,
            "evento_criado": False,
            "tipo": "global",
            "regiao": regiao,
            "ultimo_mapa": regiao,
            "abates": contador["abates"],
            "limite": limite,
            "faltam": max(0, limite - contador["abates"])
        }

    # Bateu o limite: reseta o contador e rola a chance.
    contador["abates"] = 0
    contador["ultimo_reset_em"] = _agora()

    rolagem = random.random() * 100

    if rolagem > chance:
        print(
            f"🌌 [DIMENSIONAL ABATES GLOBAL] Limite atingido, "
            f"mas a chance falhou: roll={rolagem:.2f} chance={chance} "
            f"ultimo_mapa={regiao}"
        )

        return {
            "success": True,
            "contou": True,
            "evento_criado": False,
            "tipo": "global",
            "regiao": regiao,
            "ultimo_mapa": regiao,
            "limite": limite,
            "chance_percent": chance,
            "roll": rolagem,
            "motivo": "chance_falhou"
        }

    # A Fenda nasce no mapa onde o último mob morreu.
    evento = criar_evento_debug(mapa=regiao)

    if _evento_dimensional_ativo:
        _evento_dimensional_ativo["origem_spawn"] = "contador_abates_global"
        _evento_dimensional_ativo["spawn_por_abates"] = {
            "tipo": "global",
            "mapa_ativador": regiao,
            "regiao": regiao,
            "limite_abates": limite,
            "chance_percent": chance,
            "roll": rolagem,
            "ultimo_spawn_id": spawn_id,
            "ultimo_monster_id": monster_id,
            "criado_em": _agora()
        }

        evento = serializar_evento(_evento_dimensional_ativo)

    contador["eventos_criados"] = int(contador.get("eventos_criados", 0) or 0) + 1
    contador["ultimo_evento_id"] = evento.get("evento_id") if evento else None

    _emitir_fenda_dimensional_surgiu(socketio, evento, "contador_abates_global")

    return {
        "success": True,
        "contou": True,
        "evento_criado": True,
        "tipo": "global",
        "regiao": regiao,
        "ultimo_mapa": regiao,
        "evento": evento,
        "evento_id": evento.get("evento_id") if evento else None,
        "limite": limite,
        "chance_percent": chance,
        "roll": rolagem
    }

def obter_status_abates_dimensional() -> Dict[str, Any]:
    mapas = BOSS_DIMENSIONAL_CONFIG.get("mapas_permitidos", [])
    conf = _config_abates_dimensional("default")

    contador = _contadores_abates_dimensional.get("__global__") or {}

    return {
        "success": True,
        "ativo": bool((BOSS_DIMENSIONAL_CONFIG.get("spawn_por_abates") or {}).get("ativo", True)),
        "tipo": "global",
        "contador_global": {
            "abates": int(contador.get("abates", 0) or 0),
            "limite_abates": int(conf.get("limite_abates", 500) or 500),
            "chance_percent": float(conf.get("chance_percent", 100) or 100),
            "ultimo_mapa": contador.get("ultimo_mapa"),
            "ultimo_mapa_nome": _nome_mapa_dimensional(contador.get("ultimo_mapa")),
            "ultimo_spawn_id": contador.get("ultimo_spawn_id"),
            "ultimo_monster_id": contador.get("ultimo_monster_id"),
            "eventos_criados": int(contador.get("eventos_criados", 0) or 0),
            "ultimo_evento_id": contador.get("ultimo_evento_id"),
        },
        "mapas_permitidos": [
            {
                "regiao": mapa,
                "mapa_nome": _nome_mapa_dimensional(mapa)
            }
            for mapa in mapas
        ],
        "evento_ativo": serializar_evento()
    }

def obter_evento_ativo() -> Optional[Dict[str, Any]]:
    global _evento_dimensional_ativo

    if not _evento_dimensional_ativo:
        return None

    if _evento_dimensional_ativo.get("status") in ["finalizado", "cancelado"]:
        return None

    return _evento_dimensional_ativo


def criar_evento_debug(mapa: Optional[str] = None) -> Dict[str, Any]:
    """
    Cria uma fenda manual para teste.
    Depois vamos trocar isso por spawn automático.
    """
    global _evento_dimensional_ativo

    cfg = BOSS_DIMENSIONAL_CONFIG

    mapas = cfg.get("mapas_permitidos", ["capital_eldora"])
    mapa_escolhido = mapa if mapa in mapas else random.choice(mapas)

    boss = copy.deepcopy(cfg["boss"])
    lacaios = copy.deepcopy(cfg["lacaios"])

    assets = copy.deepcopy(cfg.get("assets", {}))
    spritesheet = copy.deepcopy(cfg.get("spritesheet", {}))

    posicoes_por_mapa = cfg.get("posicoes_mapa", {}) or {}
    posicoes_tiles = copy.deepcopy(
        posicoes_por_mapa.get(mapa_escolhido)
        or posicoes_por_mapa.get("capital_eldora")
        or {}
    )

    def converter_posicoes_tiles(posicoes):
        saida = {}

        for chave, pos in (posicoes or {}).items():
            tile_x = int(pos.get("tile_x", 0) or 0)
            tile_y = int(pos.get("tile_y", 0) or 0)

            saida[chave] = {
                "tile_x": tile_x,
                "tile_y": tile_y,
                "x": tile_x * 32,
                "y": tile_y * 32
            }

        return saida

    posicoes_mapa = converter_posicoes_tiles(posicoes_tiles)

    now = _agora()

    evento = {
        "evento_id": _novo_evento_id(),
        "template_id": cfg["template_id"],
        "tipo": "boss_dimensional",
        "nome_evento": cfg["nome_evento"],
        "nome_boss": cfg["nome_boss"],
        "mapa": mapa_escolhido,
        "regiao": mapa_escolhido,
        "status": "aguardando_jogadores",
        "fase": 1,
        "rodada": 0,
        "max_jogadores": int(cfg.get("max_jogadores", 20)),
        "criado_em": now,
        "entrada_encerra_em": now + int(cfg.get("tempo_entrada_segundos", 600)),
        "jogadores": {},
        "inimigos": {
            boss["id"]: boss,
            lacaios[0]["id"]: lacaios[0],
            lacaios[1]["id"]: lacaios[1],
        },
        "logs": [
            {
                "ts": now,
                "tipo": "sistema",
                "texto": f"Uma Fenda Dimensional apareceu em {mapa_escolhido}."
            }
        ],
        "assets": assets,
        "spritesheet": spritesheet,
        "posicoes_mapa": posicoes_mapa,
        "finalizado": False
    }

    _evento_dimensional_ativo = evento
    return serializar_evento(evento)


def entrar_no_evento(user_id: str) -> Dict[str, Any]:
    evento = obter_evento_ativo()

    if not evento:
        return {
            "success": False,
            "error": "Nenhuma Fenda Dimensional ativa."
        }

    if evento.get("status") != "aguardando_jogadores":
        return {
            "success": False,
            "error": "A Fenda já começou ou foi encerrada."
        }

    if _agora() >= float(evento.get("entrada_encerra_em", 0) or 0):
        evento = verificar_inicio_automatico(evento, "entrada_tempo_esgotado")

        return {
            "success": False,
            "error": "O tempo de entrada da Fenda acabou. A batalha já começou ou a Fenda foi fechada.",
            "evento": serializar_evento(evento) if evento else None
        }

    user_id = _normalizar_user_id(user_id)

    if not user_id:
        return {
            "success": False,
            "error": "ID do jogador inválido."
        }

    jogadores = evento.setdefault("jogadores", {})

    if user_id in jogadores:
        return {
            "success": True,
            "evento": serializar_evento(evento),
            "message": "Você já está dentro da Fenda."
        }

    if len(jogadores) >= int(evento.get("max_jogadores", 20)):
        return {
            "success": False,
            "error": "A Fenda já está cheia."
        }

    pdata = _buscar_player(user_id)

    if not pdata:
        return {
            "success": False,
            "error": "Personagem não encontrado."
        }

    stats = get_combat_stats_sync(pdata)

    char_id = str(pdata.get("_id", user_id))

    skin_equipada = (
        pdata.get("equipped_skin") or
        pdata.get("skin_equipada") or
        pdata.get("skin") or
        "aventureiro_m"
    )

    jogadores[char_id] = {
        "user_id": char_id,
        "id": char_id,
        "char_id": char_id,
        "_id": char_id,

        "nome": pdata.get("character_name", pdata.get("nome", "Herói")),
        "classe": pdata.get("class", pdata.get("classe", "aventureiro")),

        "skin": skin_equipada,
        "equipped_skin": skin_equipada,
        "skin_equipada": skin_equipada,        "level": int(pdata.get("level", 1) or 1),
        "hp": int(stats.get("current_hp", stats.get("max_hp", 100)) or 100),
        "hp_max": int(stats.get("max_hp", 100) or 100),
        "mp": int(stats.get("current_mp", stats.get("max_mana", 50)) or 50),
        "mp_max": int(stats.get("max_mana", 50) or 50),
        "attack": int(stats.get("attack", 5) or 5),
        "defense": int(stats.get("defense", 0) or 0),
        "initiative": int(stats.get("initiative", 5) or 5),
        "luck": int(stats.get("luck", 0) or 0),
        "magic_attack": int(stats.get("magic_attack", 0) or 0),
        "vivo": True,
        "entrou_em": _agora(),
        "acao_enviada": False,
    }

    evento.setdefault("logs", []).append({
        "ts": _agora(),
        "tipo": "entrada",
        "texto": f"{jogadores[char_id]['nome']} entrou na Fenda Dimensional."
    })

    evento = verificar_inicio_automatico(evento, "entrada_jogador")

    return {
        "success": True,
        "evento": serializar_evento(evento) if evento else None,
        "message": "Você entrou na Fenda Dimensional."
    }


def sair_do_evento(user_id: str) -> Dict[str, Any]:
    evento = obter_evento_ativo()

    if not evento:
        return {
            "success": False,
            "error": "Nenhuma Fenda Dimensional ativa."
        }

    user_id = _normalizar_user_id(user_id)
    jogadores = evento.setdefault("jogadores", {})

    if user_id in jogadores:
        nome = jogadores[user_id].get("nome", "Herói")
        del jogadores[user_id]

        evento.setdefault("logs", []).append({
            "ts": _agora(),
            "tipo": "saida",
            "texto": f"{nome} saiu da Fenda Dimensional."
        })

    return {
        "success": True,
        "evento": serializar_evento(evento),
        "message": "Você saiu da Fenda Dimensional."
    }

def iniciar_batalha(user_id: str) -> Dict[str, Any]:
    evento = obter_evento_ativo()

    if not evento:
        return {
            "success": False,
            "error": "Nenhuma Fenda Dimensional ativa."
        }

    if evento.get("status") != "aguardando_jogadores":
        return {
            "success": False,
            "error": "A Fenda já começou ou foi encerrada.",
            "evento": serializar_evento(evento)
        }

    user_id = _resolver_user_id_no_evento(evento, user_id)

    jogadores = evento.get("jogadores", {}) or {}

    if user_id not in jogadores:
        return {
            "success": False,
            "error": "Entre na Fenda antes de iniciar a batalha.",
            "evento": serializar_evento(evento)
        }

    qtd_jogadores = len(jogadores)
    max_jogadores = int(evento.get("max_jogadores", 20) or 20)
    entrada_encerra_em = float(evento.get("entrada_encerra_em", 0) or 0)

    tempo_acabou = entrada_encerra_em > 0 and _agora() >= entrada_encerra_em
    lotou = qtd_jogadores >= max_jogadores

    if not tempo_acabou and not lotou:
        restante = max(0, int(entrada_encerra_em - _agora()))

        return {
            "success": False,
            "error": f"A Fenda só inicia quando o tempo acabar ou completar {max_jogadores}/{max_jogadores} heróis.",
            "tempo_entrada_restante": restante,
            "qtd_jogadores": qtd_jogadores,
            "max_jogadores": max_jogadores,
            "evento": serializar_evento(evento)
        }

    from modules.events import dimensional_boss_engine as engine

    if lotou:
        evento.setdefault("logs", []).append({
            "ts": _agora(),
            "tipo": "sistema",
            "texto": f"A Fenda atingiu {qtd_jogadores}/{max_jogadores} heróis e iniciou automaticamente."
        })
    else:
        evento.setdefault("logs", []).append({
            "ts": _agora(),
            "tipo": "sistema",
            "texto": "O tempo de entrada acabou. A batalha iniciou automaticamente."
        })

    resultado = engine.iniciar_batalha_evento(evento)

    return {
        **resultado,
        "evento": serializar_evento(evento)
    }


def executar_acao(user_id: str, alvo_id: str, tipo: str = "ataque_basico", skill_id: str = None) -> Dict[str, Any]:
    evento = obter_evento_ativo()

    if not evento:
        return {
            "success": False,
            "error": "Nenhuma Fenda Dimensional ativa."
        }

    user_id = _resolver_user_id_no_evento(evento, user_id)

    from modules.events import dimensional_boss_engine as engine

    if tipo in ["ataque_basico", "atacar"]:
        resultado = engine.executar_ataque_basico(evento, user_id, alvo_id)

    elif tipo in ["magia", "skill"]:
        resultado = engine.executar_skill(evento, user_id, alvo_id, skill_id)

    else:
        return {
            "success": False,
            "error": "Tipo de ação inválido."
        }

    return {
        **resultado,
        "evento": serializar_evento(evento)
    }

def encerrar_evento_debug() -> Dict[str, Any]:
    global _evento_dimensional_ativo

    if not _evento_dimensional_ativo:
        return {
            "success": True,
            "message": "Nenhuma Fenda Dimensional ativa."
        }

    evento_id = _evento_dimensional_ativo.get("evento_id")

    _evento_dimensional_ativo["status"] = "cancelado"
    _evento_dimensional_ativo["finalizado"] = True

    _evento_dimensional_ativo = None

    return {
        "success": True,
        "message": "Fenda Dimensional encerrada.",
        "evento_id": evento_id
    }

