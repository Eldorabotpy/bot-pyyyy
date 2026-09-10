# modules/combat/combat_raid_engine.py
import random
import logging

logger = logging.getLogger(__name__)

RAIDS_ATIVAS = {}


def _normalizar_jogador_para_raid(jog: dict) -> dict:
    from modules.player.combat_stats import get_combat_stats_sync, aplicar_combat_stats_no_player

    jog = dict(jog or {})
    stats = get_combat_stats_sync(jog)
    jog = aplicar_combat_stats_no_player(jog, stats)
    return jog


def criar_sala_raid(raid_id, grupo_jogadores, monstros_gerados, socketio, metadata=None):
    jogadores_dict = {}

    for jog in grupo_jogadores:
        jog = _normalizar_jogador_para_raid(jog)
        jid = str(jog.get("id") or jog.get("_id"))

        jogadores_dict[jid] = {
            "id": jid,
            "nome": jog.get("character_name") or jog.get("nome") or jog.get("name") or "Herói",
            "skin": jog.get("skin", "aventureiro_m"),
            "hp": int(jog.get("current_hp", jog.get("max_hp", 100)) or 1),
            "max_hp": int(jog.get("max_hp", 100) or 100),
            "mp": int(jog.get("current_mp", jog.get("max_mana", 50)) or 0),
            "max_mp": int(jog.get("max_mana", 50) or 50),
            "initiative": int(jog.get("initiative", 5) or 5),
            "attack": int(jog.get("attack", 10) or 10),
            "defense": int(jog.get("defense", 3) or 3),
            "magic_attack": int(jog.get("magic_attack", 0) or 0),
            "tipo": "player",
            "sid": jog.get("sid"),
        }

    monstros_dict = {}
    for mob in monstros_gerados:
        mid = str(mob.get("id"))
        monstros_dict[mid] = {
            "id": mid,
            "nome": mob.get("nome") or mob.get("name") or "Monstro",
            "skin": mob.get("skin", mob.get("monster_id", mid)),
            "hp": int(mob.get("hp", mob.get("hp_atual", 1)) or 1),
            "max_hp": int(mob.get("max_hp", mob.get("hp_max", mob.get("hp", 1))) or 1),
            "is_boss": bool(mob.get("is_boss", False)),
            "initiative": int(mob.get("initiative", -100) or -100),
            "attack": int(mob.get("attack", mob.get("ataque", 10)) or 10),
            "defense": int(mob.get("defense", mob.get("defesa", 3)) or 3),
            "tipo": "mob",
        }

    todos_combatentes = list(jogadores_dict.values()) + list(monstros_dict.values())
    todos_combatentes.sort(key=lambda x: int(x.get("initiative", 0) or 0), reverse=True)
    ordem_turnos = [str(c["id"]) for c in todos_combatentes if int(c.get("hp", 0) or 0) > 0]

    raid_state = {
        "raid_id": raid_id,
        "jogadores": jogadores_dict,
        "monstros": monstros_dict,
        "ordem_turnos": ordem_turnos,
        "turno_index": 0,
        "ativa": True,
        "metadata": metadata or {},

        # ✅ Cooldown temporário da RAID.
        # Não usa cooldown antigo salvo no banco.
        # Toda raid começa com as skills disponíveis.
        "cooldowns_raid": {
            str(jid): {}
            for jid in jogadores_dict.keys()
        },

        "participacao": {
            str(jid): {"dano": 0, "turnos": 0, "vivo_inicio": True}
            for jid in jogadores_dict.keys()
        },
    }

    RAIDS_ATIVAS[raid_id] = raid_state

    for info in jogadores_dict.values():
        if info.get("sid"):
            socketio.emit("iniciarRaidInterface", raid_state, room=info["sid"])

    return raid_state


def _avancar_indice_para_proximo_vivo(raid):
    ordem = raid.get("ordem_turnos", [])
    if not ordem:
        return None

    total = len(ordem)
    for _ in range(total):
        raid["turno_index"] = (int(raid.get("turno_index", 0) or 0) + 1) % len(ordem)
        cid = str(ordem[raid["turno_index"]])
        if cid in raid.get("jogadores", {}) and raid["jogadores"][cid].get("hp", 0) > 0:
            return cid
        if cid in raid.get("monstros", {}) and raid["monstros"][cid].get("hp", 0) > 0:
            return cid

    return None


def _remover_morto_da_ordem(raid, morto_id):
    morto_id = str(morto_id)
    ordem = raid.get("ordem_turnos", [])
    if morto_id not in ordem:
        return

    idx_atual = int(raid.get("turno_index", 0) or 0)
    idx_morto = ordem.index(morto_id)
    ordem.remove(morto_id)

    if idx_morto < idx_atual:
        raid["turno_index"] = max(0, idx_atual - 1)
    elif raid.get("turno_index", 0) >= len(ordem):
        raid["turno_index"] = 0


def processar_turno_raid(raid_id, atacante_sid, acao, alvo_id, skill_id=None):
    if raid_id not in RAIDS_ATIVAS:
        return None

    raid = RAIDS_ATIVAS[raid_id]
    ordem = raid.get("ordem_turnos", [])
    if not ordem:
        return None

    turno_atual_id = str(ordem[int(raid.get("turno_index", 0) or 0)])

    jogador = None
    for j in raid.get("jogadores", {}).values():
        if j.get("sid") == atacante_sid:
            jogador = j
            break

    if not jogador or str(jogador.get("id")) != turno_atual_id:
        return None

    herois_vivos_inicio = [
        h for h in raid.get("jogadores", {}).values()
        if int(h.get("hp", 0) or 0) > 0
    ]

    if not herois_vivos_inicio:
        raid["ativa"] = False
        return {
            "log": [{
                "autor_id": "Sistema",
                "autor_nome": "💀",
                "texto": "O SEU GRUPO FOI ANIQUILADO!",
                "is_inimigo": True
            }],
            "raid_encerrada": True,
            "resultado": "derrota",
            "atacante_id": str(jogador.get("id") or ""),
            "novo_mp": jogador.get("mp")
        }

    if int(jogador.get("hp", 0) or 0) <= 0:
        return None

    alvo = raid.get("monstros", {}).get(str(alvo_id))
    if not alvo or int(alvo.get("hp", 0) or 0) <= 0:
        return None

    log_turno = []
    jogador_id = str(jogador["id"])
    raid.setdefault("participacao", {}).setdefault(jogador_id, {"dano": 0, "turnos": 0, "vivo_inicio": True})
    raid["participacao"][jogador_id]["turnos"] += 1

    # ✅ Cooldown da raid reduz no começo do turno do jogador,
    # mesmo se ele usar ataque básico.
    # Antes só reduzia quando tentava usar magia.
    from modules.cooldowns import iniciar_turno

    raid.setdefault("cooldowns_raid", {})
    raid["cooldowns_raid"].setdefault(jogador_id, {})

    holder_cd = {
        "cooldowns": dict(raid["cooldowns_raid"].get(jogador_id) or {})
    }

    holder_cd, msgs_cd = iniciar_turno(holder_cd)
    raid["cooldowns_raid"][jogador_id] = dict(holder_cd.get("cooldowns", {}) or {})

    for msg_cd in msgs_cd:
        log_turno.append({
            "autor_id": jogador["id"],
            "autor_nome": jogador["nome"],
            "texto": msg_cd,
            "is_inimigo": False,
            "acao": "cooldown_pronto",
            "dano": 0
        })

    if acao in ("item", "usar_item"):
        return {"log": [{"autor_id": "Sistema", "autor_nome": "⚠️", "texto": "Itens não são permitidos durante a defesa do Reino!", "is_inimigo": False}], "raid_encerrada": False}

    if acao not in ("atacar", "magia"):
        return None

    if acao == "magia":
        if not skill_id:
            return {"log": [{"autor_id": "Sistema", "autor_nome": "⚠️", "texto": "Escolha uma skill para usar.", "is_inimigo": False}], "raid_encerrada": False}

        import asyncio
        from bson import ObjectId
        from modules.player.core import users_collection, clear_player_cache
        from modules.player.combat_stats import get_combat_stats
        from modules.combat.combat_engine import processar_acao_combate
        from modules.game_data.skills import get_skill_data_with_rarity

        player_db = users_collection.find_one({"_id": ObjectId(jogador["id"])})
        if not player_db:
            return {"log": [{"autor_id": "Sistema", "autor_nome": "⚠️", "texto": "Ficha do herói não encontrada.", "is_inimigo": False}], "raid_encerrada": False}

        skills_equipadas = player_db.get("equipped_skills") or player_db.get("skills_equipadas") or {}
        if isinstance(skills_equipadas, list):
            skills_equipadas = {}

        skill_id = str(skill_id)
        skill_info = get_skill_data_with_rarity(player_db, skill_id) or {}
        skill_nome = skill_info.get("display_name") or skill_id.replace("_", " ").title()
        skill_anim_effect = skill_info.get("anim_effect") or ""
        skill_tipo = skill_info.get("type") or "active"

        skill_valida = skill_id in [str(v) for v in skills_equipadas.values() if v]
        if not skill_valida:
            return {"log": [{"autor_id": jogador["id"], "autor_nome": jogador["nome"], "texto": f"tentou usar {skill_nome}, mas ela não está equipada.", "is_inimigo": False, "acao": "falha_skill", "skill_id": skill_id, "skill_nome": skill_nome, "anim_effect": "", "tipo_skill": "erro", "dano": 0}], "raid_encerrada": False, "atacante_id": jogador_id, "novo_mp": jogador.get("mp")}

        # ✅ A raid usa cooldown temporário da própria batalha.
        # Isso impede cooldown antigo do banco entrar na luta.
        player_db["cooldowns"] = dict(
            raid.get("cooldowns_raid", {}).get(jogador_id, {}) or {}
        )

        async def _rodar():
            stats_reais = await get_combat_stats(player_db)
            target_stats = {"hp": alvo.get("hp", 1), "max_hp": alvo.get("max_hp", alvo.get("hp", 1)), "attack": alvo.get("attack", 10), "defense": alvo.get("defense", 1), "initiative": alvo.get("initiative", 1), "luck": alvo.get("luck", 1)}
            return await processar_acao_combate(player_db, stats_reais, target_stats, skill_id, jogador.get("hp", 1), jogador.get("mp", 0))

        resultado = asyncio.run(_rodar())

        dano = int(resultado.get("total_damage", 0) or 0)
        logs_skill = resultado.get("log_messages", []) or []
        texto_resultado = " ".join(str(x) for x in logs_skill).lower()

        jogador["mp"] = int(resultado.get("attacker_mp_left", jogador.get("mp", 0)) or 0)
        player_db["current_mp"] = jogador["mp"]

        # ✅ Salva o cooldown só na raid atual, não no banco.
        raid.setdefault("cooldowns_raid", {})
        raid["cooldowns_raid"][jogador_id] = dict(player_db.get("cooldowns", {}) or {})

        # ✅ No banco salva apenas MP. Cooldown de batalha não deve persistir.
        users_collection.update_one(
            {"_id": ObjectId(jogador["id"])},
            {"$set": {"current_mp": jogador["mp"]}}
        )
        try:
            asyncio.run(clear_player_cache(ObjectId(jogador["id"])))
        except Exception:
            pass

        falha_bloqueio = dano <= 0 and any(x in texto_resultado for x in ("mana insuficiente", "aguarde", "cooldown", "recarga"))
        if falha_bloqueio:
            return {"log": [{"autor_id": jogador["id"], "autor_nome": jogador["nome"], "texto": logs_skill[0] if logs_skill else f"{skill_nome} não pôde ser usada.", "is_inimigo": False, "acao": "falha_skill", "skill_id": skill_id, "skill_nome": skill_nome, "anim_effect": "", "tipo_skill": "erro", "dano": 0}], "raid_encerrada": False, "atacante_id": jogador_id, "novo_mp": jogador.get("mp"), "cooldowns": player_db.get("cooldowns", {})}

        hp_antes = int(alvo.get("hp", 0) or 0)
        dano_real = min(hp_antes, dano)
        alvo["hp"] = max(0, hp_antes - dano)
        raid["participacao"][jogador_id]["dano"] += max(0, dano_real)

        if not logs_skill:
            logs_skill = [f"causou {dano} de dano!"]

        for idx, msg in enumerate(logs_skill):
            ultimo = idx == len(logs_skill) - 1
            texto = str(msg)
            if idx == 0:
                texto = f"usou {skill_nome}: {texto}"
            log_turno.append({"autor_id": jogador["id"], "autor_nome": jogador["nome"], "texto": texto, "is_inimigo": False, "alvo_id": alvo["id"] if ultimo else None, "novo_hp": alvo["hp"] if ultimo else None, "dano": dano if ultimo else 0, "acao": "magia", "skill_id": skill_id, "skill_nome": skill_nome, "anim_effect": (resultado.get("anim_effect") or skill_anim_effect) if ultimo else "", "tipo_skill": resultado.get("tipo_skill") or skill_tipo})

    else:
        atk_heroi = int(jogador.get("attack", 10) or 10)
        def_monstro = int(alvo.get("defense", 1) or 1)
        dano = max(1, int((atk_heroi * random.uniform(0.95, 1.15)) - (def_monstro * 0.85)))

        hp_antes = int(alvo.get("hp", 0) or 0)
        dano_real = min(hp_antes, dano)
        alvo["hp"] = max(0, hp_antes - dano)
        raid["participacao"][jogador_id]["dano"] += max(0, dano_real)

        log_turno.append({"autor_id": jogador["id"], "autor_nome": jogador["nome"], "texto": f"atacou {alvo['nome']} causando {dano} de dano!", "is_inimigo": False, "alvo_id": alvo["id"], "novo_hp": alvo["hp"], "dano": dano, "acao": "atacar"})

    if alvo["hp"] <= 0:
        alvo_morto_id = str(alvo["id"])

        log_turno.append({
            "autor_id": alvo_morto_id,
            "autor_nome": alvo["nome"],
            "texto": "foi destruído!",
            "is_inimigo": False,
            "acao": "morte",
            "dano": 0
        })

        _remover_morto_da_ordem(raid, alvo_morto_id)

        # ✅ BLINDAGEM:
        # Monstro morto não pode mais entrar em turno de ataque.
        # Antes ele saía da ordem, mas continuava dentro de raid["monstros"].
        raid.get("monstros", {}).pop(alvo_morto_id, None)
    
        # ✅ INVASÃO:
        # Se o Boss da frente morreu, a frente é considerada defendida.
        # Isso evita ficar preso porque algum lacaio sobrou na lista da raid.
        if alvo.get("is_boss"):
            for _mid, _mob in raid.get("monstros", {}).items():
                _mob["hp"] = 0

            raid["ordem_turnos"] = [
                cid for cid in raid.get("ordem_turnos", [])
                if cid in raid.get("jogadores", {})
            ]

            return {
                "log": log_turno + [{
                    "autor_id": "Sistema",
                    "autor_nome": "⚔️",
                    "texto": "A FRENTE FOI DEFENDIDA!",
                    "is_inimigo": False
                }],
                "raid_encerrada": True,
                "resultado": "vitoria",
                "atacante_id": jogador_id,
                "novo_mp": jogador.get("mp"),
                "cooldowns": raid.get("cooldowns_raid", {}).get(jogador_id, {})
            }
            
    # ✅ BLINDAGEM EXTRA:
    # Remove qualquer monstro morto que ainda tenha sobrado no estado da raid.
    for mid, mob in list(raid.get("monstros", {}).items()):
        if int(mob.get("hp", 0) or 0) <= 0:
            raid["monstros"].pop(str(mid), None)

    # ✅ BLINDAGEM EXTRA:
    # Reconstrói a ordem de turnos apenas com combatentes vivos.
    ordem_limpa = []

    for cid in raid.get("ordem_turnos", []):
        cid = str(cid)

        if cid in raid.get("jogadores", {}):
            if int(raid["jogadores"][cid].get("hp", 0) or 0) > 0:
                ordem_limpa.append(cid)

        elif cid in raid.get("monstros", {}):
            if int(raid["monstros"][cid].get("hp", 0) or 0) > 0:
                ordem_limpa.append(cid)

    raid["ordem_turnos"] = ordem_limpa

    if not raid["ordem_turnos"]:
        return {
            "log": log_turno + [{
                "autor_id": "Sistema",
                "autor_nome": "💀",
                "texto": "A raid terminou sem combatentes vivos.",
                "is_inimigo": True
            }],
            "raid_encerrada": True,
            "resultado": "derrota",
            "atacante_id": jogador_id,
            "novo_mp": jogador.get("mp")
        }

    vivos = [m for m in raid["monstros"].values() if int(m.get("hp", 0) or 0) > 0]
    if not vivos:
        return {
            "log": log_turno + [{
                "autor_id": "Sistema",
                "autor_nome": "⚔️",
                "texto": "A INVASÃO FOI REPELIDA!",
                "is_inimigo": False
            }],
            "raid_encerrada": True,
            "resultado": "vitoria",
            "atacante_id": jogador_id,
            "novo_mp": jogador.get("mp")
        }

    def rodar_turno_monstros():
        while True:
            proximo_id = _avancar_indice_para_proximo_vivo(raid)
            if not proximo_id:
                return
            if proximo_id in raid.get("jogadores", {}):
                return
            mob = raid.get("monstros", {}).get(str(proximo_id))

            if not mob:
                continue

            if int(mob.get("hp", 0) or 0) <= 0:
                raid.get("monstros", {}).pop(str(proximo_id), None)
                _remover_morto_da_ordem(raid, str(proximo_id))
                continue

            herois_vivos = [h for h in raid["jogadores"].values() if int(h.get("hp", 0) or 0) > 0]
            if not herois_vivos:
                return

            vitima = random.choice(herois_vivos)
            atk_mob = int(mob.get("attack", 10) or 10)
            if mob.get("is_boss"):
                atk_mob = max(atk_mob, 60)
            def_vitima = int(vitima.get("defense", 0) or 0)
            dano_mob = max(1, int((atk_mob * random.uniform(0.90, 1.15)) - (def_vitima * 0.55)))
            vitima["hp"] = max(0, int(vitima.get("hp", 0) or 0) - dano_mob)

            log_turno.append({"autor_id": mob["id"], "autor_nome": mob["nome"], "texto": f"atacou {vitima['nome']} e causou {dano_mob} de dano!", "is_inimigo": True, "alvo_id": vitima["id"], "novo_hp": vitima["hp"]})

            if vitima["hp"] <= 0:
                log_turno.append({"autor_id": vitima["id"], "autor_nome": vitima["nome"], "texto": "caiu em combate!", "is_inimigo": False})
                _remover_morto_da_ordem(raid, vitima["id"])

    rodar_turno_monstros()

    herois_de_pe = [h for h in raid["jogadores"].values() if int(h.get("hp", 0) or 0) > 0]
    if not herois_de_pe:
        return {"log": log_turno + [{"autor_id": "Sistema", "autor_nome": "💀", "texto": "O SEU GRUPO FOI ANIQUILADO!", "is_inimigo": True}], "raid_encerrada": True, "resultado": "derrota", "atacante_id": jogador_id, "novo_mp": jogador.get("mp")}

    return {
        "log": log_turno,
        "raid_encerrada": False,
        "proximo_turno_id": raid.get("ordem_turnos", [None])[int(raid.get("turno_index", 0) or 0)],
        "atacante_id": jogador_id,
        "novo_mp": jogador.get("mp"),
        "cooldowns": raid.get("cooldowns_raid", {}).get(jogador_id, {})
    }
