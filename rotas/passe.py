# rotas/passe.py
from flask import Blueprint, jsonify, request, render_template
from bson.objectid import ObjectId
from modules.player.core import users_collection
from modules.game_data.season_pass import NIVEIS_PASSE_POR_TEMPORADA, RECOMPENSAS_PASSE
from modules.game_data.skins import SKIN_SHOP_CATALOG

# Cria o Blueprint do Passe
passe_bp = Blueprint('passe_bp', __name__)


@passe_bp.route('/loja-skins')
def pagina_loja_skins():
    return render_template('loja_skins.html')


def _buscar_jogador(user_id):
    if not user_id:
        return None
    jogador = None
    try:
        if ObjectId.is_valid(str(user_id)):
            jogador = users_collection.find_one({"_id": ObjectId(str(user_id))})
    except Exception:
        pass
    if not jogador:
        try:
            jogador = users_collection.find_one({"telegram_id": int(user_id)})
        except (TypeError, ValueError):
            pass
    return jogador


def _genero_chave(jogador):
    genero = str(jogador.get("gender", "masculino")).strip().lower()
    return "feminino" if genero in ("f", "feminino", "female", "mulher") else "masculino"


def _jogador_da_sessao(user_id, exigir_csrf=False):
    from modules.portal_auth import PlayerSessionError, require_csrf, require_player_identity
    try:
        if exigir_csrf:
            require_csrf()
        return require_player_identity(user_id), None
    except PlayerSessionError as erro:
        return None, (jsonify({"sucesso": False, "erro": str(erro)}), erro.status_code)
    except ValueError as erro:
        return None, (jsonify({"sucesso": False, "erro": str(erro)}), 403)


@passe_bp.route('/api/loja-skins/status/<user_id>')
def api_status_loja_skins(user_id):
    jogador, erro = _jogador_da_sessao(user_id)
    if erro:
        return erro
    genero = _genero_chave(jogador)
    skins = [{
        "id": item["id"],
        "skin_id": item["gender_variants"][genero],
        "nome": item["display_name"],
        "descricao": item["description"],
        "custo": item["cost"],
    } for item in SKIN_SHOP_CATALOG.values() if genero in item["gender_variants"]]
    return jsonify({
        "sucesso": True,
        "fragmentos": max(0, int(jogador.get("skin_fragments", 0) or 0)),
        "skins_desbloqueadas": jogador.get("unlocked_skins", []) or [],
        "skin_equipada": jogador.get("equipped_skin"),
        "genero": genero,
        "skins": skins,
    })


@passe_bp.route('/api/loja-skins/resgatar', methods=['POST'])
def api_resgatar_skin():
    dados = request.get_json(silent=True) or {}
    jogador, erro = _jogador_da_sessao(dados.get("user_id"), exigir_csrf=True)
    if erro:
        return erro
    item = SKIN_SHOP_CATALOG.get(str(dados.get("skin_id", "")))
    if not item:
        return jsonify({"sucesso": False, "erro": "Esta skin não está disponível na loja."}), 404

    skin_id = item["gender_variants"].get(_genero_chave(jogador))
    if not skin_id:
        return jsonify({"sucesso": False, "erro": "Esta skin está disponível apenas para personagens masculinos."}), 403
    resultado = users_collection.update_one(
        {
            "_id": jogador["_id"],
            "skin_fragments": {"$gte": item["cost"]},
            "unlocked_skins": {"$ne": skin_id},
        },
        {
            "$inc": {"skin_fragments": -item["cost"]},
            "$addToSet": {"unlocked_skins": skin_id},
        },
    )
    if resultado.modified_count:
        return jsonify({"sucesso": True, "message": f"{item['display_name']} resgatada!", "skin_id": skin_id})

    atualizado = users_collection.find_one({"_id": jogador["_id"]}) or jogador
    possuidas = atualizado.get("unlocked_skins", []) or []
    if skin_id in possuidas:
        return jsonify({"sucesso": False, "erro": "Você já possui esta skin."}), 409
    fragmentos = max(0, int(atualizado.get("skin_fragments", 0) or 0))
    return jsonify({"sucesso": False, "erro": f"Fragmentos insuficientes: {fragmentos}/{item['cost']}."}), 400


@passe_bp.route('/api/loja-skins/equipar', methods=['POST'])
def api_equipar_skin_loja():
    dados = request.get_json(silent=True) or {}
    jogador, erro = _jogador_da_sessao(dados.get("user_id"), exigir_csrf=True)
    if erro:
        return erro

    skin_id = str(dados.get("skin_id", ""))
    if not skin_id or skin_id not in (jogador.get("unlocked_skins", []) or []):
        return jsonify({"sucesso": False, "erro": "Você não possui esta aparência."}), 400

    esperado = "masculino" if skin_id.endswith("_m") else "feminino" if skin_id.endswith("_f") else None
    if esperado and esperado != _genero_chave(jogador):
        return jsonify({"sucesso": False, "erro": "Esta variante não é compatível com o gênero do personagem."}), 400

    users_collection.update_one({"_id": jogador["_id"]}, {"$set": {"equipped_skin": skin_id}})
    from modules.player.core import clear_player_cache
    import asyncio
    asyncio.run(clear_player_cache(jogador["_id"]))
    return jsonify({"sucesso": True})

@passe_bp.route('/passe')
def pagina_passe():
    return render_template('passe.html')

def _snapshot_filter(query, document, dotted_path):
    """Evita sobrescrever um inventário ou lista de resgates que mudou durante a ação."""
    current = document
    parts = dotted_path.split(".")
    for part in parts[:-1]:
        current = current.get(part, {}) if isinstance(current, dict) else {}
    leaf = parts[-1]
    query[dotted_path] = current[leaf] if isinstance(current, dict) and leaf in current else {"$exists": False}


def _add_to_set(update, field, values):
    values = list(dict.fromkeys(value for value in values if value is not None))
    if values:
        update.setdefault("$addToSet", {})[field] = {"$each": values}


def _clear_pass_player_cache(player_id):
    try:
        import asyncio
        from modules.player.core import clear_player_cache
        asyncio.run(clear_player_cache(player_id))
    except Exception:
        import logging
        logging.getLogger(__name__).debug("Não foi possível limpar o cache após atualizar o Passe", exc_info=True)


def _catalogo_passe_com_imagens():
    from copy import deepcopy
    from modules import game_data

    catalog = deepcopy(RECOMPENSAS_PASSE)
    assets = "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/"
    item_fallbacks = {
        "pocao_cura_grande": "itens/consumiveis/pocao_cura_grande.png",
        "pergaminho_de_reparo": "itens/consumiveis/pergaminho_de_reparo.png",
        "sigilo_de_protecao": "itens/consumiveis/sigilo_de_protecao.png",
    }

    for level_data in catalog.values():
        for track in ("free", "premium"):
            reward = level_data.get(track) or {}
            reward_type = reward.get("tipo")
            image_url = ""
            if reward_type == "item":
                item_id = reward.get("id")
                item_data = game_data.ITEMS_DATA.get(item_id, {})
                image_url = item_data.get("icon_url") or (
                    f"{assets}{item_fallbacks[item_id]}" if item_id in item_fallbacks else ""
                )
            elif reward_type == "gold":
                image_url = f"{assets}perfil/ouro.png"
            elif reward_type == "gems":
                image_url = f"{assets}itens/consumiveis/gems.png"
            elif reward_type == "banner" and reward.get("id") == "banner_xiongmaoren_s1":
                image_url = f"{assets}banners/banner_xiongmaoren_s1.png"
            if image_url:
                reward["image_url"] = image_url

        fragments = level_data.get("fragmentos_skin") or {}
        if fragments.get("free") or fragments.get("premium"):
            fragments["image_url"] = f"{assets}itens/consumiveis/fragmento_skin.png"

    return catalog


def _apply_pass_reward(player, reward, membership):
    """Prepara uma recompensa em memória; a rota persiste tudo numa única operação."""
    reward_type = reward.get("tipo")
    if reward_type == "gold":
        return {"gold": int(reward.get("qtd", 0) or 0)}
    if reward_type == "gems":
        return {"gems": int(reward.get("qtd", 0) or 0)}
    if reward_type == "item":
        from modules.player.inventory import try_add_item_to_inventory
        item_id = str(reward.get("id") or "")
        quantity = int(reward.get("qtd", 1) or 1)
        if not item_id or not try_add_item_to_inventory(player, item_id, quantity):
            return {"blocked": True}
        return {"inventory": True}
    if reward_type == "banner":
        if not reward.get("id"):
            return {"invalid": True}
        membership.setdefault("unlocked_banners", []).append(reward.get("id"))
        return {"banner": True}
    # Skins e avatares são desbloqueados na Loja de Skins, fora do Passe.
    return {"invalid": True}


@passe_bp.get('/api/passe/status/<user_id>')
def status_passe(user_id):
    jogador, erro = _jogador_da_sessao(user_id)
    if erro:
        return erro
    passe = jogador.get("passe_batalha") or {}
    try:
        level = int(passe.get("level", 1) or 1)
        xp = int(passe.get("xp", 0) or 0)
        fragmentos = int(jogador.get("skin_fragments", 0) or 0)
        gemas = int(jogador.get("gems", 0) or 0)
    except (TypeError, ValueError):
        return jsonify({"erro": "Dados do Passe inválidos. Atualize o personagem e tente novamente."}), 409
    response = jsonify({
        "status": {
            "level": min(max(1, level), NIVEIS_PASSE_POR_TEMPORADA),
            "xp": max(0, xp),
            "is_premium": bool(passe.get("is_premium", False)),
            "resgatados_free": passe.get("resgatados_free", []) or [],
            "resgatados_premium": passe.get("resgatados_premium", []) or [],
            "skin_fragments": max(0, fragmentos),
            "gems": max(0, gemas),
        },
        "catalogo": _catalogo_passe_com_imagens(),
    })
    response.headers["Cache-Control"] = "no-store"
    return response


@passe_bp.post('/api/passe/resgatar')
def api_resgatar_passe():
    from copy import deepcopy
    from modules.portal_auth import PlayerSessionError, require_csrf
    try:
        require_csrf()
        dados = request.get_json(silent=True) or {}
        jogador, erro = _jogador_da_sessao(dados.get("user_id"))
        if erro:
            return erro
        try:
            nivel = int(dados.get("nivel"))
        except (TypeError, ValueError):
            return jsonify(status="error", message="Nível de recompensa inválido."), 400
        tipo = str(dados.get("tipo") or "")
        if tipo not in ("free", "premium") or nivel not in RECOMPENSAS_PASSE:
            return jsonify(status="error", message="Recompensa não encontrada."), 404

        passe = jogador.get("passe_batalha") or {}
        if int(passe.get("level", 1) or 1) < nivel:
            return jsonify(status="error", message="Alcance esse nível para resgatar a recompensa."), 400
        if tipo == "premium" and not passe.get("is_premium"):
            return jsonify(status="error", message="Esta recompensa exige o Passe Premium."), 400

        claim_field = f"resgatados_{tipo}"
        claim_path = f"passe_batalha.{claim_field}"
        claimed = passe.get(claim_field) or []
        if nivel in {int(value) for value in claimed}:
            return jsonify(status="error", message="Esta recompensa já foi resgatada."), 409

        reward_config = RECOMPENSAS_PASSE[nivel]
        reward = reward_config.get(tipo)
        if not reward:
            return jsonify(status="error", message="Recompensa não configurada."), 404

        inventory_existed = "inventory" in jogador
        inventory_before = deepcopy(jogador.get("inventory", {}))
        membership = {}
        result = _apply_pass_reward(jogador, reward, membership)
        if result.get("blocked"):
            return jsonify(status="error", message="A mochila está cheia ou a pilha atingiu o limite. Libere espaço e tente novamente."), 409
        if result.get("invalid"):
            return jsonify(status="error", message="A recompensa está configurada incorretamente. Avise a equipe."), 500

        update = {"$addToSet": {claim_path: nivel}}
        increments = {}
        if result.get("gold"):
            increments["gold"] = result["gold"]
        if result.get("gems"):
            increments["gems"] = result["gems"]
        fragmentos = int((reward_config.get("fragmentos_skin") or {}).get(tipo, 0) or 0)
        if fragmentos:
            increments["skin_fragments"] = fragmentos
        if increments:
            update["$inc"] = increments
        for field, values in membership.items():
            _add_to_set(update, field, values)
        if result.get("inventory"):
            update["$set"] = {"inventory": jogador.get("inventory", {})}

        guard = {"_id": jogador["_id"]}
        if "level" in passe:
            guard["passe_batalha.level"] = {"$gte": nivel}
        else:
            guard["passe_batalha.level"] = {"$exists": False}
        if tipo == "premium":
            guard["passe_batalha.is_premium"] = True
        _snapshot_filter(guard, jogador, claim_path)
        if result.get("inventory"):
            if inventory_existed:
                guard["inventory"] = inventory_before
            else:
                guard["inventory"] = {"$exists": False}
        saved = users_collection.update_one(guard, update)
        if not saved.modified_count:
            return jsonify(status="error", message="O passe mudou enquanto você resgatava. Atualize a tela e tente novamente."), 409

        _clear_pass_player_cache(jogador["_id"])
        fragment_message = f"\n✨ +{fragmentos} fragmentos para a Loja de Skins" if fragmentos else ""
        return jsonify(status="success", message=f"Recebeu: {reward.get('label', 'Recompensa')}!{fragment_message}")
    except PlayerSessionError as erro:
        return jsonify(status="error", message=str(erro)), erro.status_code
    except ValueError as erro:
        return jsonify(status="error", message=str(erro)), 403
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Falha ao resgatar prêmio do Passe")
        return jsonify(status="error", message="Não foi possível entregar a recompensa. Tente novamente."), 500


@passe_bp.post('/api/passe/comprar_premium')
def api_comprar_premium_passe():
    from modules.portal_auth import PlayerSessionError, require_csrf
    try:
        require_csrf()
        dados = request.get_json(silent=True) or {}
        jogador, erro = _jogador_da_sessao(dados.get("user_id"))
        if erro:
            return erro

        custo = 500
        atualizado = users_collection.find_one_and_update(
            {
                "_id": jogador["_id"],
                "gems": {"$gte": custo},
                "passe_batalha.is_premium": {"$ne": True},
            },
            {
                "$inc": {"gems": -custo},
                "$set": {"passe_batalha.is_premium": True},
            },
            return_document=True,
        )
        if atualizado:
            _clear_pass_player_cache(jogador["_id"])
            return jsonify(sucesso=True, message="Passe Premium ativado. As recompensas premium desta trilha já podem ser resgatadas.")

        atual = users_collection.find_one({"_id": jogador["_id"]}) or jogador
        if (atual.get("passe_batalha") or {}).get("is_premium"):
            return jsonify(sucesso=False, message="Este personagem já possui o Passe Premium."), 409
        saldo = int(atual.get("gems", 0) or 0)
        return jsonify(sucesso=False, message=f"Gemas insuficientes: você tem {saldo} e precisa de {custo}."), 400
    except PlayerSessionError as erro:
        return jsonify(sucesso=False, message=str(erro)), erro.status_code
    except ValueError as erro:
        return jsonify(sucesso=False, message=str(erro)), 403
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Falha ao ativar Passe Premium")
        return jsonify(sucesso=False, message="Não foi possível ativar o Passe Premium. Tente novamente."), 500


@passe_bp.post('/api/passe/coletar_tudo')
def api_coletar_tudo():
    from copy import deepcopy
    from modules.portal_auth import PlayerSessionError, require_csrf
    try:
        require_csrf()
        dados = request.get_json(silent=True) or {}
        jogador, erro = _jogador_da_sessao(dados.get("user_id"))
        if erro:
            return erro

        passe = jogador.get("passe_batalha") or {}
        level = min(max(1, int(passe.get("level", 1) or 1)), NIVEIS_PASSE_POR_TEMPORADA)
        premium = bool(passe.get("is_premium", False))
        free_before = list(passe.get("resgatados_free") or [])
        premium_before = list(passe.get("resgatados_premium") or [])
        free_claimed = {int(value) for value in free_before}
        premium_claimed = {int(value) for value in premium_before}
        inventory_existed = "inventory" in jogador
        inventory_before = deepcopy(jogador.get("inventory", {}))
        jogador["inventory"] = deepcopy(inventory_before)
        membership = {}
        claims = {"free": [], "premium": []}
        totals = {"gold": 0, "gems": 0, "skin_fragments": 0, "rewards": 0, "blocked": 0}

        for nivel in range(1, level + 1):
            reward_set = RECOMPENSAS_PASSE.get(nivel) or {}
            for tipo, already_claimed in (("free", free_claimed), ("premium", premium_claimed)):
                if tipo == "premium" and not premium:
                    continue
                reward = reward_set.get(tipo)
                if nivel in already_claimed or not reward:
                    continue
                applied = _apply_pass_reward(jogador, reward, membership)
                if applied.get("blocked"):
                    totals["blocked"] += 1
                    continue
                if applied.get("invalid"):
                    return jsonify(status="error", message=f"A recompensa do nível {nivel} está configurada incorretamente."), 500
                totals["gold"] += applied.get("gold", 0)
                totals["gems"] += applied.get("gems", 0)
                totals["rewards"] += 1
                totals["skin_fragments"] += int((reward_set.get("fragmentos_skin") or {}).get(tipo, 0) or 0)
                claims[tipo].append(nivel)

        if not totals["rewards"]:
            if totals["blocked"]:
                return jsonify(status="error", message="A mochila não comporta as recompensas de item. Libere espaço e tente coletar novamente."), 409
            return jsonify(status="info", message="Não há recompensas novas para coletar.")

        guard = {
            "_id": jogador["_id"],
            "passe_batalha.is_premium": True if premium else {"$ne": True},
        }
        if "level" in passe:
            guard["passe_batalha.level"] = level
        else:
            guard["passe_batalha.level"] = {"$exists": False}
        _snapshot_filter(guard, jogador, "passe_batalha.resgatados_free")
        _snapshot_filter(guard, jogador, "passe_batalha.resgatados_premium")

        update = {}
        if claims["free"]:
            update.setdefault("$addToSet", {})["passe_batalha.resgatados_free"] = {"$each": claims["free"]}
        if claims["premium"]:
            update.setdefault("$addToSet", {})["passe_batalha.resgatados_premium"] = {"$each": claims["premium"]}
        for field, values in membership.items():
            _add_to_set(update, field, values)

        increments = {
            field: totals[field]
            for field in ("gold", "gems", "skin_fragments")
            if totals[field]
        }
        if increments:
            update["$inc"] = increments

        if jogador["inventory"] != inventory_before:
            update.setdefault("$set", {})["inventory"] = jogador["inventory"]
            if inventory_existed:
                guard["inventory"] = inventory_before
            else:
                guard["inventory"] = {"$exists": False}

        saved = users_collection.update_one(guard, update)
        if not saved.modified_count:
            return jsonify(status="error", message="O passe mudou durante a coleta. Atualize a tela e tente novamente."), 409

        _clear_pass_player_cache(jogador["_id"])
        resumo = (
            f"{totals['rewards']} recompensa(s) coletada(s).\n"
            f"✨ +{totals['skin_fragments']} fragmentos para a Loja de Skins\n"
            f"💰 +{totals['gold']} ouro\n"
            f"💎 +{totals['gems']} gemas"
        )
        if totals["blocked"]:
            resumo += f"\n{totals['blocked']} recompensa(s) de item ficaram pendentes porque a mochila está cheia."
        return jsonify(status="success", message=resumo)
    except PlayerSessionError as erro:
        return jsonify(status="error", message=str(erro)), erro.status_code
    except ValueError as erro:
        return jsonify(status="error", message=str(erro)), 403
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Falha ao coletar recompensas do Passe")
        return jsonify(status="error", message="Não foi possível coletar as recompensas. Tente novamente."), 500
