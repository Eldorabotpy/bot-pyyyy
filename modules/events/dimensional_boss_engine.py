# modules/events/dimensional_boss_engine.py

from __future__ import annotations

import random
import time
import copy
from typing import Any, Dict


def _agora() -> float:
    return time.time()


def _log(evento: Dict[str, Any], texto: str, tipo: str = "combate"):
    evento.setdefault("logs", []).append({
        "ts": _agora(),
        "tipo": tipo,
        "texto": texto
    })

    # Evita log infinito na memória
    evento["logs"] = evento["logs"][-40:]


def inimigos_vivos(evento: Dict[str, Any]):
    return [
        inimigo for inimigo in (evento.get("inimigos") or {}).values()
        if int(inimigo.get("hp", 0) or 0) > 0 and inimigo.get("vivo", True)
    ]


def lacaios_vivos(evento: Dict[str, Any]):
    return [
        inimigo for inimigo in inimigos_vivos(evento)
        if inimigo.get("tipo") == "lacaio"
    ]


def obter_boss(evento: Dict[str, Any]):
    for inimigo in (evento.get("inimigos") or {}).values():
        if inimigo.get("tipo") == "boss":
            return inimigo
    return None


def boss_esta_protegido(evento: Dict[str, Any]) -> bool:
    return len(lacaios_vivos(evento)) > 0


def atualizar_barreira_boss(evento: Dict[str, Any]):
    boss = obter_boss(evento)

    if not boss:
        return

    protegido = boss_esta_protegido(evento)
    estava_protegido = bool(boss.get("protegido", False))

    boss["protegido"] = protegido

    if estava_protegido and not protegido:
        evento["fase"] = 2
        _log(evento, "A barreira dimensional caiu! O Arauto do Vazio agora pode ser atacado.", "fase")


def iniciar_batalha_evento(evento: Dict[str, Any]) -> Dict[str, Any]:
    if evento.get("status") == "em_combate":
        return {
            "success": True,
            "message": "A batalha já está em andamento."
        }

    if evento.get("status") in ["vitoria", "derrota", "finalizado", "cancelado"]:
        return {
            "success": False,
            "error": "Este evento já foi encerrado."
        }

    jogadores = evento.get("jogadores") or {}

    if not jogadores:
        return {
            "success": False,
            "error": "Nenhum jogador entrou na Fenda."
        }

    evento["status"] = "em_combate"
    evento["rodada"] = 1
    evento["entrada_encerra_em"] = _agora()
    evento["fase"] = 1
    evento["acoes_pendentes"] = {}

    balancear_inimigos_para_grupo(evento)

    for jogador in (evento.get("jogadores") or {}).values():
        jogador["acao_enviada"] = False

    boss = obter_boss(evento)
    if boss:
        boss["protegido"] = True

    _log(evento, "A batalha contra a Fenda Dimensional começou!", "sistema")
    _log(evento, "Derrote os 2 lacaios para quebrar a proteção do boss.", "sistema")

    return {
        "success": True,
        "message": "Batalha iniciada."
    }


def calcular_dano_basico(jogador: Dict[str, Any], inimigo: Dict[str, Any]) -> Dict[str, Any]:
    ataque = int(jogador.get("attack", 5) or 5)
    sorte = int(jogador.get("luck", 0) or 0)
    defesa_alvo = int(inimigo.get("defense", 0) or 0)

    base = ataque - int(defesa_alvo * 0.35)
    base = max(1, base)

    variacao = random.uniform(0.85, 1.15)
    dano = max(1, int(base * variacao))

    chance_critico = min(25, max(3, sorte * 0.08))
    critico = random.uniform(0, 100) <= chance_critico

    if critico:
        dano = int(dano * 1.7)

    return {
        "dano": dano,
        "critico": critico
    }

def jogadores_vivos(evento: Dict[str, Any]):
    return [
        jogador for jogador in (evento.get("jogadores") or {}).values()
        if int(jogador.get("hp", 0) or 0) > 0 and jogador.get("vivo", True)
    ]

def quantidade_jogadores_evento(evento: Dict[str, Any]) -> int:
    return max(1, len(evento.get("jogadores") or {}))


def quantidade_jogadores_vivos_evento(evento: Dict[str, Any]) -> int:
    return max(1, len(jogadores_vivos(evento)))


def fator_hp_inimigos_por_grupo(qtd_jogadores: int) -> float:
    """
    Escala a vida da Fenda conforme a quantidade de jogadores no início da batalha.

    1 jogador: possível testar/solar com dificuldade.
    20 jogadores: usa a vida base cadastrada no registry.
    """
    qtd_jogadores = max(1, int(qtd_jogadores or 1))

    if qtd_jogadores <= 1:
        return 0.07
    if qtd_jogadores <= 2:
        return 0.12
    if qtd_jogadores <= 3:
        return 0.18
    if qtd_jogadores <= 5:
        return 0.28
    if qtd_jogadores <= 8:
        return 0.42
    if qtd_jogadores <= 12:
        return 0.62
    if qtd_jogadores <= 16:
        return 0.82

    return 1.00


def fator_dano_inimigos_por_grupo(evento: Dict[str, Any]) -> float:
    """
    Escala o dano dos inimigos conforme jogadores vivos.
    Isso impede 1 jogador de tomar hit de raid cheio.
    """
    vivos = quantidade_jogadores_vivos_evento(evento)

    if vivos <= 1:
        return 0.23
    if vivos <= 2:
        return 0.30
    if vivos <= 3:
        return 0.36
    if vivos <= 5:
        return 0.44
    if vivos <= 8:
        return 0.52
    if vivos <= 12:
        return 0.60
    if vivos <= 16:
        return 0.68

    return 0.76


def multiplicador_tipo_inimigo(inimigo: Dict[str, Any]) -> float:
    texto = f"{inimigo.get('id', '')} {inimigo.get('nome', '')}".lower()

    if inimigo.get("tipo") == "boss" or "arauto" in texto:
        return 1.00

    if "guardiao" in texto or "guardião" in texto:
        return 0.82

    if "sacerdote" in texto:
        return 0.70

    return 0.80


def limite_dano_por_golpe(evento: Dict[str, Any], jogador: Dict[str, Any], inimigo: Dict[str, Any]) -> int:
    """
    Trava dano máximo por golpe para evitar one-shot injusto.
    """
    hp_max = max(1, int(jogador.get("hp_max", jogador.get("hp", 1)) or 1))
    vivos = quantidade_jogadores_vivos_evento(evento)

    if vivos <= 1:
        pct = 0.32
    elif vivos <= 3:
        pct = 0.38
    elif vivos <= 6:
        pct = 0.45
    elif vivos <= 12:
        pct = 0.52
    else:
        pct = 0.60

    if inimigo.get("tipo") == "boss" and not boss_esta_protegido(evento):
        pct += 0.08

    return max(15, int(hp_max * pct))


def limite_acoes_inimigas_por_rodada(evento: Dict[str, Any]) -> int:
    """
    Controla quantos inimigos agem por rodada.
    Antes todos os inimigos atacavam sempre, o que destruía solo/duo.
    """
    vivos = quantidade_jogadores_vivos_evento(evento)

    if vivos <= 1:
        return 1
    if vivos <= 3:
        return 2

    return 3


def balancear_inimigos_para_grupo(evento: Dict[str, Any]):
    """
    Aplica balanceamento uma única vez no início da batalha.
    Usa os valores do registry como base para raid cheia.
    """
    if evento.get("balanceamento_inimigos_aplicado"):
        return

    qtd_jogadores = quantidade_jogadores_evento(evento)
    fator_hp = fator_hp_inimigos_por_grupo(qtd_jogadores)

    inimigos = evento.get("inimigos") or {}

    for inimigo in inimigos.values():
        hp_base = int(
            inimigo.get("hp_max_base")
            or inimigo.get("hp_max")
            or inimigo.get("hp")
            or 1
        )

        hp_novo = max(1, int(hp_base * fator_hp))

        inimigo["hp_max_base"] = hp_base
        inimigo["hp_max"] = hp_novo
        inimigo["hp"] = hp_novo
        inimigo["vivo"] = True

    evento["balanceamento_inimigos_aplicado"] = True
    evento["balanceamento"] = {
        "jogadores_inicio": qtd_jogadores,
        "fator_hp": fator_hp
    }

    _log(
        evento,
        f"Fenda balanceada para {qtd_jogadores} herói(s). Vida inimiga ajustada para {int(fator_hp * 100)}% da raid cheia.",
        "sistema"
    )    

def jogador_esta_vivo(jogador: Dict[str, Any]) -> bool:
    return bool(jogador) and int(jogador.get("hp", 0) or 0) > 0 and jogador.get("vivo", True)


def inimigo_esta_vivo(inimigo: Dict[str, Any]) -> bool:
    return bool(inimigo) and int(inimigo.get("hp", 0) or 0) > 0 and inimigo.get("vivo", True)

def _normalizar_texto_skill_dimensional(valor: str) -> str:
    txt = str(valor or "").strip().lower()

    txt = (
        txt.replace("á", "a")
           .replace("à", "a")
           .replace("ã", "a")
           .replace("â", "a")
           .replace("é", "e")
           .replace("ê", "e")
           .replace("í", "i")
           .replace("ó", "o")
           .replace("ô", "o")
           .replace("õ", "o")
           .replace("ú", "u")
           .replace("ç", "c")
    )

    txt = txt.replace("𝐂", "c").replace("𝐨", "o").replace("𝐫", "r").replace("𝐭", "t").replace("𝐞", "e")
    txt = txt.replace("𝐏", "p").replace("𝐟", "f").replace("𝐮", "u").replace("𝐚", "a").replace("𝐧", "n")

    txt = txt.replace(" ", "_").replace("-", "_")
    txt = "_".join([p for p in txt.split("_") if p])

    return txt


def _resolver_skill_id_dimensional(skill_id: str) -> str:
    """
    A Fenda recebe às vezes o id curto vindo do frontend, exemplo:
    corte_perfurante

    Mas no banco oficial a skill pode estar como:
    guerreiro_corte_perfurante

    Esta função encontra o ID real dentro de SKILL_DATA.
    """
    try:
        from modules.game_data.skills import SKILL_DATA
    except Exception:
        return str(skill_id or "")

    skill_id = str(skill_id or "").strip()

    if not skill_id:
        return ""

    if skill_id in SKILL_DATA:
        return skill_id

    alvo_norm = _normalizar_texto_skill_dimensional(skill_id)

    aliases_manuais = {
        "corte_perfurante": "guerreiro_corte_perfurante",
        "guerreiro_corte_perfurante": "guerreiro_corte_perfurante",
    }

    if alvo_norm in aliases_manuais and aliases_manuais[alvo_norm] in SKILL_DATA:
        return aliases_manuais[alvo_norm]

    for sid, dados in SKILL_DATA.items():
        sid_norm = _normalizar_texto_skill_dimensional(sid)
        icon_norm = _normalizar_texto_skill_dimensional(dados.get("icon", ""))
        nome_norm = _normalizar_texto_skill_dimensional(
            dados.get("display_name") or dados.get("name") or ""
        )

        if sid_norm == alvo_norm:
            return sid

        if sid_norm.endswith("_" + alvo_norm):
            return sid

        if icon_norm == alvo_norm or icon_norm.endswith("_" + alvo_norm):
            return sid

        if nome_norm == alvo_norm:
            return sid

    return skill_id


def _skill_dimensional_dados(jogador: Dict[str, Any], skill_id: str) -> Dict[str, Any] | None:
    if not skill_id:
        return None

    try:
        from modules.game_data.skills import SKILL_DATA
    except Exception:
        return None

    skill_id_original = str(skill_id or "")
    skill_id_real = _resolver_skill_id_dimensional(skill_id_original)

    base = SKILL_DATA.get(skill_id_real)

    if not base:
        return None

    skills_player = (
        jogador.get("skills")
        or jogador.get("skills_desbloqueadas")
        or {}
    )

    inst = {}

    if isinstance(skills_player, dict):
        inst = (
            skills_player.get(skill_id_real)
            or skills_player.get(skill_id_original)
            or {}
        )

    raridade = str(inst.get("rarity") or inst.get("raridade") or "comum")

    dados = copy.deepcopy(base)

    rarity_effects = base.get("rarity_effects") or {}
    dados_raridade = rarity_effects.get(raridade) or rarity_effects.get("comum") or {}

    dados.update(copy.deepcopy(dados_raridade))
    dados["raridade"] = raridade
    dados["skill_id"] = skill_id_real
    dados["skill_id_original"] = skill_id_original

    return dados

def _skill_dimensional_effects(skill: Dict[str, Any]) -> Dict[str, Any]:
    return skill.get("effects") or {}


def _skill_dimensional_mana(skill: Dict[str, Any]) -> int:
    return int(skill.get("mana_cost", skill.get("mp_cost", 0)) or 0)


def _skill_dimensional_cooldown(skill: Dict[str, Any]) -> int:
    effects = _skill_dimensional_effects(skill)
    return int(
        effects.get("cooldown_turns")
        or skill.get("cooldown_turns")
        or skill.get("cooldown")
        or 0
    )


def _skill_dimensional_nome(skill: Dict[str, Any], skill_id: str) -> str:
    return (
        skill.get("display_name")
        or skill.get("name")
        or str(skill_id).replace("_", " ").title()
    )


def _skill_dimensional_tipo(skill: Dict[str, Any]) -> str:
    return str(skill.get("type") or "active").lower()


def _skill_dimensional_eh_suporte(skill: Dict[str, Any]) -> bool:
    effects = _skill_dimensional_effects(skill)
    tipo = _skill_dimensional_tipo(skill)

    return (
        tipo == "support"
        or "party_heal" in effects
        or "party_mana" in effects
        or "party_buff" in effects
        or effects.get("target") in ["ally", "party"]
    )


def reduzir_cooldowns_jogadores(evento: Dict[str, Any]):
    for jogador in (evento.get("jogadores") or {}).values():
        cds = jogador.setdefault("cooldowns", {})

        for skill_id in list(cds.keys()):
            restante = int(cds.get(skill_id, 0) or 0) - 1

            if restante > 0:
                cds[skill_id] = restante
            else:
                cds.pop(skill_id, None)


def aplicar_custo_skill_dimensional(jogador: Dict[str, Any], skill: Dict[str, Any], skill_id: str):
    custo_mana = _skill_dimensional_mana(skill)
    cd = _skill_dimensional_cooldown(skill)

    jogador["mp"] = max(0, int(jogador.get("mp", 0) or 0) - custo_mana)

    if cd > 0:
        jogador.setdefault("cooldowns", {})[skill_id] = cd


def calcular_dano_skill_dimensional(jogador: Dict[str, Any], inimigo: Dict[str, Any], skill: Dict[str, Any]) -> Dict[str, Any]:
    effects = _skill_dimensional_effects(skill)

    tipo_dano = str(
        effects.get("damage_type")
        or effects.get("type")
        or skill.get("damage_type")
        or "physical"
    ).lower()

    if tipo_dano == "magic":
        ataque = int(jogador.get("magic_attack", 0) or 0)
        if ataque <= 0:
            ataque = int(jogador.get("attack", 5) or 5)
        redutor_defesa = 0.22
    else:
        ataque = int(jogador.get("attack", 5) or 5)
        redutor_defesa = 0.32

    mult = float(
        effects.get("damage_multiplier")
        or effects.get("damage_scale")
        or skill.get("damage_multiplier")
        or skill.get("damage_scale")
        or 1.35
    )

    defesa = int(inimigo.get("defense", 0) or 0)

    base = int((ataque * mult) - (defesa * redutor_defesa))
    base = max(1, base)

    variacao = random.uniform(0.88, 1.15)
    dano = max(1, int(base * variacao))

    sorte = int(jogador.get("luck", 0) or 0)
    chance_critico = min(30, max(4, sorte * 0.09))
    critico = random.uniform(0, 100) <= chance_critico

    if critico:
        dano = int(dano * 1.75)

    return {
        "dano": dano,
        "critico": critico
    }


def aplicar_skill_suporte_dimensional(evento: Dict[str, Any], jogador: Dict[str, Any], item: Dict[str, Any], skill: Dict[str, Any], skill_id: str):
    effects = _skill_dimensional_effects(skill)

    nome_jogador = jogador.get("nome", "Herói")
    nome_skill = _skill_dimensional_nome(skill, skill_id)

    aplicar_custo_skill_dimensional(jogador, skill, skill_id)

    total_cura = 0
    total_mana = 0

    party_heal = effects.get("party_heal")
    party_mana = effects.get("party_mana")

    if party_heal:
        for aliado in jogadores_vivos(evento):
            hp_atual = int(aliado.get("hp", 0) or 0)
            hp_max = int(aliado.get("hp_max", 1) or 1)

            if "amount_percent_max_hp" in party_heal:
                cura = int(hp_max * float(party_heal.get("amount_percent_max_hp", 0)))
            elif party_heal.get("heal_type") == "magic_attack":
                cura = int(int(jogador.get("magic_attack", 0) or 0) * float(party_heal.get("heal_scale", 1.0)))
            else:
                cura = int(party_heal.get("amount_flat", 0) or 0)

            cura = max(0, cura)

            if cura <= 0:
                continue

            novo_hp = min(hp_max, hp_atual + cura)
            cura_real = novo_hp - hp_atual

            aliado["hp"] = novo_hp
            total_cura += cura_real

    if party_mana:
        for aliado in jogadores_vivos(evento):
            mp_atual = int(aliado.get("mp", 0) or 0)
            mp_max = int(aliado.get("mp_max", 1) or 1)

            ganho = int(party_mana.get("amount_flat", 0) or 0)

            if "amount_percent_max_mp" in party_mana:
                ganho = int(mp_max * float(party_mana.get("amount_percent_max_mp", 0)))

            ganho = max(0, ganho)

            if ganho <= 0:
                continue

            novo_mp = min(mp_max, mp_atual + ganho)
            ganho_real = novo_mp - mp_atual

            aliado["mp"] = novo_mp
            total_mana += ganho_real

    texto_log = f"{nome_jogador} usou {nome_skill}"

    if total_cura > 0:
        texto_log += f" e curou o grupo em {total_cura} de HP"

    if total_mana > 0:
        texto_log += f" e restaurou {total_mana} de MP"

    if total_cura <= 0 and total_mana <= 0:
        buff = effects.get("party_buff") or {}
        buff_nome = buff.get("buff_name") or buff.get("buff_value") or "um efeito de suporte"
        texto_log += f" e aplicou {buff_nome}"

    texto_log += "."

    _log(evento, texto_log, "suporte")

    evento.setdefault("_animacoes_rodada", []).append({
        "ator_tipo": "jogador",
        "ator_id": str(item.get("ator_id", "")),
        "autor_id": str(item.get("ator_id", "")),
        "autor_nome": nome_jogador,
        "acao": "skill_suporte",
        "skill_id": skill_id,
        "skill_nome": nome_skill,
        "anim_effect": skill.get("anim_effect", ""),
        "tipo_skill": "support",
        "alvo_tipo": "grupo",
        "alvo_id": str(item.get("ator_id", "")),
        "dano": 0,
        "cura": total_cura,
        "mana": total_mana,
        "critico": False,
        "texto": texto_log,
        "is_inimigo": False
    })


def aplicar_skill_jogador_na_rodada(evento: Dict[str, Any], item: Dict[str, Any]):
    jogadores = evento.get("jogadores", {}) or {}
    inimigos = evento.get("inimigos", {}) or {}

    jogador = jogadores.get(str(item.get("ator_id", "")))

    if not jogador_esta_vivo(jogador):
        return

    skill_id = str(item.get("skill_id") or "")

    skill = _skill_dimensional_dados(jogador, skill_id)

    if not skill:
        _log(
            evento,
            f"{jogador.get('nome', 'Herói')} tentou usar uma skill inválida. skill_id recebido: {skill_id or 'vazio'}",
            "erro"
        )
        return

    nome_jogador = jogador.get("nome", "Herói")
    nome_skill = _skill_dimensional_nome(skill, skill_id)

    custo_mana = _skill_dimensional_mana(skill)
    mp_atual = int(jogador.get("mp", 0) or 0)

    if mp_atual < custo_mana:
        texto_log = f"{nome_jogador} tentou usar {nome_skill}, mas não tinha mana suficiente."
        _log(evento, texto_log, "erro")

        evento.setdefault("_animacoes_rodada", []).append({
            "ator_tipo": "jogador",
            "ator_id": str(item.get("ator_id", "")),
            "autor_id": str(item.get("ator_id", "")),
            "autor_nome": nome_jogador,
            "acao": "falha_skill",
            "skill_id": skill_id,
            "skill_nome": nome_skill,
            "dano": 0,
            "texto": texto_log,
            "is_inimigo": False
        })
        return

    cd_atual = int(jogador.setdefault("cooldowns", {}).get(skill_id, 0) or 0)

    if cd_atual > 0:
        texto_log = f"{nome_jogador} tentou usar {nome_skill}, mas a skill está em recarga por {cd_atual} turno(s)."
        _log(evento, texto_log, "erro")
        return

    if _skill_dimensional_eh_suporte(skill):
        aplicar_skill_suporte_dimensional(evento, jogador, item, skill, skill_id)
        return

    alvo_id = str(item.get("alvo_id", ""))
    alvo_principal = inimigos.get(alvo_id)

    if not inimigo_esta_vivo(alvo_principal):
        return

    if alvo_principal.get("tipo") == "boss" and boss_esta_protegido(evento):
        _log(evento, f"{nome_jogador} tentou usar {nome_skill}, mas a barreira dimensional bloqueou o boss.")
        return

    aplicar_custo_skill_dimensional(jogador, skill, skill_id)

    effects = _skill_dimensional_effects(skill)
    eh_area = bool(effects.get("aoe")) or effects.get("single_target") is False

    alvos = []

    if eh_area:
        for inimigo in inimigos_vivos(evento):
            if inimigo.get("tipo") == "boss" and boss_esta_protegido(evento):
                continue
            alvos.append(inimigo)
    else:
        alvos = [alvo_principal]

    participacao = evento.setdefault("participacao", {})
    dados_part = participacao.setdefault(str(item.get("ator_id", "")), {
        "dano": 0,
        "cura": 0,
        "rodadas": 0
    })

    for alvo in alvos:
        if not inimigo_esta_vivo(alvo):
            continue

        resultado = calcular_dano_skill_dimensional(jogador, alvo, skill)
        dano = int(resultado["dano"])
        critico = bool(resultado["critico"])

        hp_atual = int(alvo.get("hp", 0) or 0)
        hp_novo = max(0, hp_atual - dano)

        alvo["hp"] = hp_novo

        nome_alvo = alvo.get("nome", "inimigo")

        if critico:
            texto_log = f"{nome_jogador} usou {nome_skill} e acertou CRÍTICO de {dano} em {nome_alvo}!"
        else:
            texto_log = f"{nome_jogador} usou {nome_skill} e causou {dano} de dano em {nome_alvo}."

        _log(evento, texto_log)

        dados_part["dano"] = int(dados_part.get("dano", 0) or 0) + dano
        dados_part["rodadas"] = int(dados_part.get("rodadas", 0) or 0) + 1

        evento.setdefault("_animacoes_rodada", []).append({
            "ator_tipo": "jogador",
            "ator_id": str(item.get("ator_id", "")),
            "autor_id": str(item.get("ator_id", "")),
            "autor_nome": nome_jogador,
            "acao": "magia",
            "skill_id": skill_id,
            "skill_nome": nome_skill,
            "anim_effect": skill.get("anim_effect", ""),
            "tipo_skill": _skill_dimensional_tipo(skill),
            "alvo_tipo": "inimigo",
            "alvo_id": str(alvo.get("id", "")),
            "alvo_nome": nome_alvo,
            "dano": dano,
            "critico": critico,
            "novo_hp": hp_novo,
            "texto": texto_log,
            "is_inimigo": False
        })

        if hp_novo <= 0:
            alvo["vivo"] = False
            _log(evento, f"{nome_alvo} foi derrotado!", "morte")

def todos_jogadores_vivos_enviaram_acao(evento: Dict[str, Any]) -> bool:
    vivos = jogadores_vivos(evento)

    if not vivos:
        return False

    for jogador in vivos:
        if not jogador.get("acao_enviada"):
            return False

    return True


def calcular_dano_inimigo(evento: Dict[str, Any], inimigo: Dict[str, Any], jogador: Dict[str, Any]) -> int:
    ataque_fisico = int(inimigo.get("attack", 5) or 5)
    ataque_magico = int(inimigo.get("magic_attack", 0) or 0)
    ataque = max(ataque_fisico, ataque_magico)

    defesa = int(jogador.get("defense", 0) or 0)

    base = int(ataque * 0.55) - int(defesa * 0.30)
    base = max(1, base)

    fator_grupo = fator_dano_inimigos_por_grupo(evento)
    fator_tipo = multiplicador_tipo_inimigo(inimigo)

    base = max(1, int(base * fator_grupo * fator_tipo))

    variacao = random.uniform(0.85, 1.15)
    dano = max(1, int(base * variacao))

    limite = limite_dano_por_golpe(evento, jogador, inimigo)

    return max(1, min(dano, limite))


def escolher_alvo_jogador(evento: Dict[str, Any]):
    vivos = jogadores_vivos(evento)

    if not vivos:
        return None

    return random.choice(vivos)


def gerar_acoes_inimigos(evento: Dict[str, Any]):
    acoes = []

    vivos_players = jogadores_vivos(evento)

    if not vivos_players:
        return acoes

    inimigos = inimigos_vivos(evento)

    # Enquanto o boss está protegido, os lacaios seguram a linha de frente.
    # Isso evita boss + 2 lacaios atacando solo/duo na mesma rodada.
    if boss_esta_protegido(evento):
        somente_lacaios = [
            inimigo for inimigo in inimigos
            if inimigo.get("tipo") == "lacaio"
        ]

        if somente_lacaios:
            inimigos = somente_lacaios

    limite_acoes = limite_acoes_inimigas_por_rodada(evento)

    if len(inimigos) > limite_acoes:
        inimigos = random.sample(inimigos, limite_acoes)

    for inimigo in inimigos:
        
        inimigo_id = str(inimigo.get("id", ""))

        if not inimigo_id:
            continue

        nome = str(inimigo.get("nome", ""))

        # Sacerdote tenta curar aliado inimigo ferido.
        if "Sacerdote" in nome:
            aliados_feridos = [
                alvo for alvo in inimigos
                if inimigo_esta_vivo(alvo)
                and int(alvo.get("hp", 0) or 0) < int(alvo.get("hp_max", 1) or 1)
            ]

            if aliados_feridos and random.random() <= 0.55:
                alvo_cura = sorted(
                    aliados_feridos,
                    key=lambda x: int(x.get("hp", 0) or 0) / max(1, int(x.get("hp_max", 1) or 1))
                )[0]

                acoes.append({
                    "ator_tipo": "inimigo",
                    "ator_id": inimigo_id,
                    "tipo": "cura_inimigo",
                    "alvo_tipo": "inimigo",
                    "alvo_id": str(alvo_cura.get("id", "")),
                    "initiative": int(inimigo.get("initiative", 1) or 1)
                })
                continue

        alvo = escolher_alvo_jogador(evento)

        if not alvo:
            continue

        acoes.append({
            "ator_tipo": "inimigo",
            "ator_id": inimigo_id,
            "tipo": "ataque_inimigo",
            "alvo_tipo": "jogador",
            "alvo_id": str(alvo.get("user_id", "")),
            "initiative": int(inimigo.get("initiative", 1) or 1)
        })

    return acoes


def montar_fila_rodada(evento: Dict[str, Any]):
    fila = []

    jogadores = evento.get("jogadores", {}) or {}
    pendentes = evento.get("acoes_pendentes", {}) or {}

    for user_id, acao in pendentes.items():
        jogador = jogadores.get(str(user_id))

        if not jogador_esta_vivo(jogador):
            continue

        fila.append({
            "ator_tipo": "jogador",
            "ator_id": str(user_id),
            "tipo": acao.get("tipo", "ataque_basico"),
            "skill_id": str(acao.get("skill_id", "")),
            "skill_id_original": str(acao.get("skill_id_original", "")),
            "alvo_tipo": acao.get("alvo_tipo", "inimigo"),
            "alvo_id": str(acao.get("alvo_id", "")),
            "initiative": int(jogador.get("initiative", 1) or 1)
        })

    fila.extend(gerar_acoes_inimigos(evento))

    fila.sort(
        key=lambda item: (
            int(item.get("initiative", 0) or 0),
            random.random()
        ),
        reverse=True
    )

    return fila


def aplicar_ataque_jogador_na_rodada(evento: Dict[str, Any], item: Dict[str, Any]):
    jogadores = evento.get("jogadores", {}) or {}
    inimigos = evento.get("inimigos", {}) or {}

    jogador = jogadores.get(str(item.get("ator_id", "")))
    alvo = inimigos.get(str(item.get("alvo_id", "")))

    if not jogador_esta_vivo(jogador):
        return

    if not inimigo_esta_vivo(alvo):
        return

    if alvo.get("tipo") == "boss" and boss_esta_protegido(evento):
        _log(evento, f"{jogador.get('nome', 'Herói')} tentou atacar o boss, mas a barreira dimensional bloqueou o golpe.")
        return

    resultado_dano = calcular_dano_basico(jogador, alvo)
    dano = int(resultado_dano["dano"])
    critico = bool(resultado_dano["critico"])

    hp_atual = int(alvo.get("hp", 0) or 0)
    hp_novo = max(0, hp_atual - dano)

    alvo["hp"] = hp_novo

    nome_jogador = jogador.get("nome", "Herói")
    nome_alvo = alvo.get("nome", "inimigo")

    if critico:
        texto_log = f"{nome_jogador} acertou CRÍTICO de {dano} em {nome_alvo}!"
    else:
        texto_log = f"{nome_jogador} causou {dano} de dano em {nome_alvo}."

    _log(evento, texto_log)

    evento.setdefault("_animacoes_rodada", []).append({
        "ator_tipo": "jogador",
        "ator_id": str(item.get("ator_id", "")),
        "autor_id": str(item.get("ator_id", "")),
        "autor_nome": nome_jogador,
        "acao": "ataque_basico",
        "alvo_tipo": "inimigo",
        "alvo_id": str(alvo.get("id", item.get("alvo_id", ""))),
        "alvo_nome": nome_alvo,
        "dano": dano,
        "critico": critico,
        "novo_hp": hp_novo,
        "texto": texto_log,
        "is_inimigo": False
    })

    participacao = evento.setdefault("participacao", {})
    dados_part = participacao.setdefault(str(item.get("ator_id", "")), {
        "dano": 0,
        "cura": 0,
        "rodadas": 0
    })
    dados_part["dano"] = int(dados_part.get("dano", 0) or 0) + dano
    dados_part["rodadas"] = int(dados_part.get("rodadas", 0) or 0) + 1

    if hp_novo <= 0:
        alvo["vivo"] = False
        _log(evento, f"{nome_alvo} foi derrotado!", "morte")


def aplicar_ataque_inimigo_na_rodada(evento: Dict[str, Any], item: Dict[str, Any]):
    jogadores = evento.get("jogadores", {}) or {}
    inimigos = evento.get("inimigos", {}) or {}

    inimigo = inimigos.get(str(item.get("ator_id", "")))
    jogador = jogadores.get(str(item.get("alvo_id", "")))

    if not inimigo_esta_vivo(inimigo):
        return

    if not jogador_esta_vivo(jogador):
        return

    dano = calcular_dano_inimigo(evento, inimigo, jogador)

    hp_atual = int(jogador.get("hp", 0) or 0)
    hp_novo = max(0, hp_atual - dano)

    jogador["hp"] = hp_novo

    nome_inimigo = inimigo.get("nome", "Inimigo")
    nome_jogador = jogador.get("nome", "Herói")

    texto_log = f"{nome_inimigo} atacou {nome_jogador} e causou {dano} de dano."

    _log(evento, texto_log)

    evento.setdefault("_animacoes_rodada", []).append({
        "ator_tipo": "inimigo",
        "ator_id": str(item.get("ator_id", "")),
        "autor_id": str(item.get("ator_id", "")),
        "autor_nome": nome_inimigo,
        "acao": "ataque_inimigo",
        "alvo_tipo": "jogador",
        "alvo_id": str(item.get("alvo_id", "")),
        "alvo_nome": nome_jogador,
        "dano": dano,
        "critico": False,
        "novo_hp": hp_novo,
        "texto": texto_log,
        "is_inimigo": True
    })

    if hp_novo <= 0:
        jogador["vivo"] = False
        _log(evento, f"{nome_jogador} foi derrotado!", "morte")


def aplicar_cura_inimigo_na_rodada(evento: Dict[str, Any], item: Dict[str, Any]):
    inimigos = evento.get("inimigos", {}) or {}

    curador = inimigos.get(str(item.get("ator_id", "")))
    alvo = inimigos.get(str(item.get("alvo_id", "")))

    if not inimigo_esta_vivo(curador):
        return

    if not inimigo_esta_vivo(alvo):
        return

    poder = int(curador.get("magic_attack", 100) or 100)
    cura = max(50, int(poder * random.uniform(0.55, 0.85)))

    hp_atual = int(alvo.get("hp", 0) or 0)
    hp_max = int(alvo.get("hp_max", 1) or 1)
    hp_novo = min(hp_max, hp_atual + cura)

    cura_real = hp_novo - hp_atual

    if cura_real <= 0:
        return

    alvo["hp"] = hp_novo

    texto_log = f"{curador.get('nome', 'Sacerdote')} curou {alvo.get('nome', 'aliado')} em {cura_real} de HP."

    _log(evento, texto_log, "suporte")

    evento.setdefault("_animacoes_rodada", []).append({
        "ator_tipo": "inimigo",
        "ator_id": str(item.get("ator_id", "")),
        "autor_id": str(item.get("ator_id", "")),
        "autor_nome": curador.get("nome", "Sacerdote"),
        "acao": "cura_inimigo",
        "alvo_tipo": "inimigo",
        "alvo_id": str(item.get("alvo_id", "")),
        "alvo_nome": alvo.get("nome", "Aliado"),
        "cura": cura_real,
        "dano": 0,
        "critico": False,
        "texto": texto_log,
        "is_inimigo": True
    })


def verificar_fim_rodada(evento: Dict[str, Any]) -> bool:
    atualizar_barreira_boss(evento)

    boss = obter_boss(evento)

    if boss and int(boss.get("hp", 0) or 0) <= 0:
        boss["vivo"] = False
        evento["status"] = "vitoria"
        evento["finalizado"] = True
        _log(evento, "O Arauto do Vazio foi derrotado! Vitória dos heróis!", "vitoria")
        return True

    vivos = jogadores_vivos(evento)

    if not vivos:
        evento["status"] = "derrota"
        evento["finalizado"] = True
        _log(evento, "Todos os heróis foram derrotados. A Fenda Dimensional venceu.", "derrota")
        return True

    return False


def processar_rodada(evento: Dict[str, Any]) -> Dict[str, Any]:
    if evento.get("status") != "em_combate":
        return {
            "success": False,
            "error": "A batalha não está em andamento."
        }

    rodada_atual = int(evento.get("rodada", 1) or 1)

    # Limpa as animações temporárias da rodada anterior.
    evento["_animacoes_rodada"] = []

    _log(evento, f"Rodada {rodada_atual} começou.", "rodada")

    reduzir_cooldowns_jogadores(evento)

    fila = montar_fila_rodada(evento)

    for item in fila:
        if verificar_fim_rodada(evento):
            break

        tipo = item.get("tipo")

        if item.get("ator_tipo") == "jogador":
            if tipo in ["magia", "skill"]:
                aplicar_skill_jogador_na_rodada(evento, item)
            else:
                aplicar_ataque_jogador_na_rodada(evento, item)

        elif tipo == "ataque_inimigo":
            aplicar_ataque_inimigo_na_rodada(evento, item)

        elif tipo == "cura_inimigo":
            aplicar_cura_inimigo_na_rodada(evento, item)

        if verificar_fim_rodada(evento):
            break

    if evento.get("status") == "em_combate":
        evento["rodada"] = rodada_atual + 1
        evento["acoes_pendentes"] = {}

        for jogador in (evento.get("jogadores") or {}).values():
            if jogador_esta_vivo(jogador):
                jogador["acao_enviada"] = False

        _log(evento, f"Rodada {rodada_atual} terminou.", "rodada")

    animacoes_rodada = list(evento.get("_animacoes_rodada") or [])

    return {
        "success": True,
        "message": "Rodada processada.",
        "animacoes_rodada": animacoes_rodada,
        "animacoes": animacoes_rodada
    }

def processar_turno_inimigos(evento: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processa apenas as ações dos inimigos no fim da rodada.

    Importante:
    - Os jogadores já atacaram/usaram skill na hora do clique.
    - Aqui não pode processar jogador de novo.
    """
    if evento.get("status") != "em_combate":
        return {
            "success": False,
            "error": "A batalha não está em andamento."
        }

    rodada_atual = int(evento.get("rodada", 1) or 1)

    evento["_animacoes_rodada"] = []

    _log(evento, f"Rodada {rodada_atual}: inimigos reagiram.", "rodada")

    reduzir_cooldowns_jogadores(evento)

    fila = gerar_acoes_inimigos(evento)

    fila.sort(
        key=lambda item: (
            int(item.get("initiative", 0) or 0),
            random.random()
        ),
        reverse=True
    )

    for item in fila:
        if verificar_fim_rodada(evento):
            break

        tipo = item.get("tipo")

        if tipo == "ataque_inimigo":
            aplicar_ataque_inimigo_na_rodada(evento, item)

        elif tipo == "cura_inimigo":
            aplicar_cura_inimigo_na_rodada(evento, item)

        if verificar_fim_rodada(evento):
            break

    if evento.get("status") == "em_combate":
        evento["rodada"] = rodada_atual + 1
        evento["acoes_pendentes"] = {}

        for jogador in (evento.get("jogadores") or {}).values():
            if jogador_esta_vivo(jogador):
                jogador["acao_enviada"] = False

        _log(evento, f"Rodada {rodada_atual} terminou.", "rodada")

    animacoes_rodada = list(evento.get("_animacoes_rodada") or [])

    return {
        "success": True,
        "message": "Turno dos inimigos processado.",
        "animacoes_rodada": animacoes_rodada,
        "animacoes": animacoes_rodada
    }

def processar_turno_inimigos(evento: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processa apenas as ações dos inimigos no fim da rodada.

    Importante:
    - Os jogadores já atacaram na hora do clique.
    - Aqui não pode processar jogadores de novo.
    """
    if evento.get("status") != "em_combate":
        return {
            "success": False,
            "error": "A batalha não está em andamento."
        }

    rodada_atual = int(evento.get("rodada", 1) or 1)

    evento["_animacoes_rodada"] = []

    _log(evento, f"Rodada {rodada_atual}: inimigos reagiram.", "rodada")

    reduzir_cooldowns_jogadores(evento)

    fila = gerar_acoes_inimigos(evento)

    fila.sort(
        key=lambda item: (
            int(item.get("initiative", 0) or 0),
            random.random()
        ),
        reverse=True
    )

    for item in fila:
        if verificar_fim_rodada(evento):
            break

        tipo = item.get("tipo")

        if tipo == "ataque_inimigo":
            aplicar_ataque_inimigo_na_rodada(evento, item)

        elif tipo == "cura_inimigo":
            aplicar_cura_inimigo_na_rodada(evento, item)

        if verificar_fim_rodada(evento):
            break

    if evento.get("status") == "em_combate":
        evento["rodada"] = rodada_atual + 1
        evento["acoes_pendentes"] = {}

        for jogador in (evento.get("jogadores") or {}).values():
            if jogador_esta_vivo(jogador):
                jogador["acao_enviada"] = False

        _log(evento, f"Rodada {rodada_atual} terminou.", "rodada")

    animacoes_rodada = list(evento.get("_animacoes_rodada") or [])

    return {
        "success": True,
        "message": "Turno dos inimigos processado.",
        "animacoes_rodada": animacoes_rodada,
        "animacoes": animacoes_rodada
    }

def executar_ataque_basico(evento: Dict[str, Any], user_id: str, alvo_id: str) -> Dict[str, Any]:
    if evento.get("status") != "em_combate":
        return {
            "success": False,
            "error": "A batalha ainda não começou."
        }

    jogadores = evento.get("jogadores") or {}
    inimigos = evento.get("inimigos") or {}

    user_id = str(user_id)
    alvo_id = str(alvo_id)

    jogador = jogadores.get(user_id)

    if not jogador:
        return {
            "success": False,
            "error": "Você não está dentro desta Fenda."
        }

    if not jogador_esta_vivo(jogador):
        return {
            "success": False,
            "error": "Seu personagem está derrotado."
        }

    if jogador.get("acao_enviada"):
        return {
            "success": False,
            "error": "Você já escolheu sua ação nesta rodada."
        }

    alvo = inimigos.get(alvo_id)

    if not alvo:
        return {
            "success": False,
            "error": "Alvo inválido."
        }

    if not inimigo_esta_vivo(alvo):
        return {
            "success": False,
            "error": "Este alvo já foi derrotado."
        }

    if alvo.get("tipo") == "boss" and boss_esta_protegido(evento):
        return {
            "success": False,
            "error": "O boss está protegido pelos lacaios. Derrote os lacaios primeiro."
        }

    # Limpa o pacote visual só desta ação.
    evento["_animacoes_rodada"] = []

    item_acao = {
        "ator_tipo": "jogador",
        "ator_id": user_id,
        "tipo": "ataque_basico",
        "alvo_tipo": "inimigo",
        "alvo_id": alvo_id,
        "initiative": int(jogador.get("initiative", 1) or 1)
    }

    aplicar_ataque_jogador_na_rodada(evento, item_acao)

    jogador["acao_enviada"] = True

    animacoes_acao = list(evento.get("_animacoes_rodada") or [])

    verificar_fim_rodada(evento)

    processou_rodada = False
    animacoes_rodada = []

    # Depois que todos os jogadores vivos atacaram, só os inimigos resolvem a rodada.
    if evento.get("status") == "em_combate" and todos_jogadores_vivos_enviaram_acao(evento):
        evento["_animacoes_rodada"] = []
        resultado_rodada = processar_turno_inimigos(evento)
        processou_rodada = bool(resultado_rodada.get("success"))
        animacoes_rodada = list(evento.get("_animacoes_rodada") or [])

    vivos = jogadores_vivos(evento)
    enviados = len([j for j in vivos if j.get("acao_enviada")])

    return {
        "success": True,
        "message": f"Ataque realizado. Aguardando heróis: {enviados}/{len(vivos)}.",
        "processou_rodada": processou_rodada,
        "animacoes_acao": animacoes_acao,
        "animacoes_rodada": animacoes_rodada
    }

def executar_skill(evento: Dict[str, Any], user_id: str, alvo_id: str, skill_id: str) -> Dict[str, Any]:
    if evento.get("status") != "em_combate":
        return {
            "success": False,
            "error": "A batalha ainda não começou."
        }

    jogadores = evento.get("jogadores") or {}
    inimigos = evento.get("inimigos") or {}

    user_id = str(user_id)
    alvo_id = str(alvo_id or "")
    skill_id_original = str(skill_id or "")

    jogador = jogadores.get(user_id)

    if not jogador:
        return {
            "success": False,
            "error": "Você não está dentro desta Fenda."
        }

    if not jogador_esta_vivo(jogador):
        return {
            "success": False,
            "error": "Seu personagem está derrotado."
        }

    if jogador.get("acao_enviada"):
        return {
            "success": False,
            "error": "Você já escolheu sua ação nesta rodada."
        }

    skill = _skill_dimensional_dados(jogador, skill_id_original)

    if not skill:
        return {
            "success": False,
            "error": "Skill inválida ou não encontrada."
        }

    if _skill_dimensional_tipo(skill) == "passive":
        return {
            "success": False,
            "error": "Skill passiva não pode ser usada manualmente."
        }

    skill_id_real = str(skill.get("skill_id") or skill_id_original)

    custo_mana = _skill_dimensional_mana(skill)

    if int(jogador.get("mp", 0) or 0) < custo_mana:
        return {
            "success": False,
            "error": f"Mana insuficiente. Precisa de {custo_mana} MP."
        }

    cooldowns = jogador.setdefault("cooldowns", {})
    cd_atual = max(
        int(cooldowns.get(skill_id_original, 0) or 0),
        int(cooldowns.get(skill_id_real, 0) or 0)
    )

    if cd_atual > 0:
        return {
            "success": False,
            "error": f"Skill em recarga por {cd_atual} turno(s)."
        }

    eh_suporte = _skill_dimensional_eh_suporte(skill)

    if not eh_suporte:
        alvo = inimigos.get(alvo_id)

        if not alvo:
            return {
                "success": False,
                "error": "Alvo inválido."
            }

        if not inimigo_esta_vivo(alvo):
            return {
                "success": False,
                "error": "Este alvo já foi derrotado."
            }

        if alvo.get("tipo") == "boss" and boss_esta_protegido(evento):
            return {
                "success": False,
                "error": "O boss está protegido pelos lacaios. Derrote os lacaios primeiro."
            }

    # A skill agora executa na hora, igual ataque básico.
    evento["_animacoes_rodada"] = []

    item_acao = {
        "ator_tipo": "jogador",
        "ator_id": user_id,
        "tipo": "magia",
        "skill_id": skill_id_real,
        "skill_id_original": skill_id_original,
        "alvo_tipo": "grupo" if eh_suporte else "inimigo",
        "alvo_id": alvo_id,
        "initiative": int(jogador.get("initiative", 1) or 1)
    }

    aplicar_skill_jogador_na_rodada(evento, item_acao)

    jogador["acao_enviada"] = True

    animacoes_acao = list(evento.get("_animacoes_rodada") or [])

    verificar_fim_rodada(evento)

    processou_rodada = False
    animacoes_rodada = []

    # Se foi o último jogador vivo a agir, os inimigos reagem.
    if evento.get("status") == "em_combate" and todos_jogadores_vivos_enviaram_acao(evento):
        evento["_animacoes_rodada"] = []
        resultado_rodada = processar_turno_inimigos(evento)
        processou_rodada = bool(resultado_rodada.get("success"))
        animacoes_rodada = list(evento.get("_animacoes_rodada") or [])

    vivos = jogadores_vivos(evento)
    enviados = len([j for j in vivos if j.get("acao_enviada")])

    return {
        "success": True,
        "message": f"Skill usada. Aguardando heróis: {enviados}/{len(vivos)}.",
        "processou_rodada": processou_rodada,
        "animacoes_acao": animacoes_acao,
        "animacoes_rodada": animacoes_rodada,
        "cooldowns": jogador.get("cooldowns", {}),
        "player_mp": jogador.get("mp", 0)
    }