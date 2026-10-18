# rotas/passe.py
from flask import Blueprint, jsonify, request, render_template
from bson.objectid import ObjectId
from modules.player.core import users_collection
from modules.game_data.season_pass import RECOMPENSAS_PASSE
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
    } for item in SKIN_SHOP_CATALOG.values()]
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

    skin_id = item["gender_variants"][_genero_chave(jogador)]
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

@passe_bp.route('/api/passe/comprar_premium', methods=['POST'])
def api_comprar_premium_passe():
    try:
        dados = request.json
        user_id = dados.get("user_id")
        
        # Busca o jogador (tenta ObjectId primeiro, depois Telegram ID)
        jogador = None
        try:
            if len(user_id) == 24:
                jogador = users_collection.find_one({"_id": ObjectId(user_id)})
        except: pass

        if not jogador:
            try:
                jogador = users_collection.find_one({"telegram_id": int(user_id)})
            except: pass

        if not jogador:
            return jsonify({"sucesso": False, "message": "Jogador não encontrado!"}), 404

        CUSTO_PREMIUM = 500 
        gemas_atuais = jogador.get("gems", 0)
        passe = jogador.get("passe_batalha", {})

        if passe.get("is_premium"):
            return jsonify({"sucesso": False, "message": "Tu já possuis o Passe Premium! 👑"}), 400

        if gemas_atuais < CUSTO_PREMIUM:
            return jsonify({"sucesso": False, "message": f"Gemas insuficientes. Precisas de {CUSTO_PREMIUM} 💎."}), 400

        nova_quantidade_gemas = gemas_atuais - CUSTO_PREMIUM
        passe["is_premium"] = True

        users_collection.update_one(
            {"_id": jogador["_id"]},
            {"$set": {
                "gems": nova_quantidade_gemas,
                "passe_batalha": passe
            }}
        )

        return jsonify({"sucesso": True, "message": "Passe Premium Ativado com Sucesso! Bem-vindo à Elite! 👑"})
        
    except Exception as e:
        return jsonify({"sucesso": False, "message": str(e)}), 500

@passe_bp.route('/api/passe/coletar_tudo', methods=['POST'])
def api_coletar_tudo():
    try:
        user_id = request.json.get("user_id")
        pdata = None
        
        try:
            if len(str(user_id)) == 24: pdata = users_collection.find_one({"_id": ObjectId(user_id)})
        except: pass

        if not pdata:
            try: pdata = users_collection.find_one({"telegram_id": int(user_id)})
            except: pass

        if not pdata: return jsonify({"status": "error", "message": "Jogador não encontrado"}), 404

        passe = pdata.get("passe_batalha", {})
        nivel_atual = passe.get("level", 1)
        is_premium = passe.get("is_premium", False)
        
        resgatados_free = passe.get("resgatados_free", [])
        resgatados_premium = passe.get("resgatados_premium", [])
        
        recompensas_ganhas = []
        ouro_total = 0
        gemas_totais = 0
        fragmentos_skin_total = 0
        genero_jogador = pdata.get("gender", "masculino").lower()

        def entregar_premio(premio):
            nonlocal ouro_total, gemas_totais, fragmentos_skin_total
            tipo = premio["tipo"]
            
            if tipo == "gold": 
                ouro_total += premio["qtd"]
            elif tipo == "gems": 
                gemas_totais += premio["qtd"]
            elif tipo == "skin_dinamica" or tipo == "avatar_dinamico":
                id_correto = premio["id_m"] if genero_jogador in ["masculino", "m"] else premio["id_f"]
                if tipo == "skin_dinamica":
                    users_collection.update_one({"_id": pdata["_id"]}, {"$addToSet": {"unlocked_skins": id_correto}})
                else:
                    users_collection.update_one({"_id": pdata["_id"]}, {"$addToSet": {"unlocked_avatars": id_correto}})
            elif tipo == "banner":
                users_collection.update_one({"_id": pdata["_id"]}, {"$addToSet": {"unlocked_banners": premio["id"]}})
            elif tipo == "avatar":
                users_collection.update_one({"_id": pdata["_id"]}, {"$addToSet": {"unlocked_avatars": premio["id"]}})
            elif tipo == "item":
                users_collection.update_one({"_id": pdata["_id"]}, {"$inc": {f"inventory.{premio['id']}": premio.get("qtd", 1)}})
                
            recompensas_ganhas.append(premio.get("label", "Item Misterioso"))

        for lv in range(1, nivel_atual + 1):
            config_lv = RECOMPENSAS_PASSE.get(lv) or RECOMPENSAS_PASSE.get(str(lv)) or {}
            
            if config_lv.get("free") and lv not in resgatados_free:
                entregar_premio(config_lv["free"])
                fragmentos_skin_total += int((config_lv.get("fragmentos_skin", {}) or {}).get("free", 0) or 0)
                resgatados_free.append(lv)

            if is_premium and config_lv.get("premium") and lv not in resgatados_premium:
                entregar_premio(config_lv["premium"])
                fragmentos_skin_total += int((config_lv.get("fragmentos_skin", {}) or {}).get("premium", 0) or 0)
                resgatados_premium.append(lv)

        if not recompensas_ganhas:
            return jsonify({"status": "info", "message": "Não há nada novo para coletar! 🏜️"})

        users_collection.update_one(
            {"_id": pdata["_id"]},
            {
                "$set": {
                    "passe_batalha.resgatados_free": resgatados_free,
                    "passe_batalha.resgatados_premium": resgatados_premium,
                    "skin_fragments": max(0, int(pdata.get("skin_fragments", 0) or 0)) + fragmentos_skin_total,
                },
                "$inc": {"gold": ouro_total, "gems": gemas_totais}
            }
        )

        msg_final = f"Coletaste {len(recompensas_ganhas)} itens!<br>✨ +{fragmentos_skin_total} Fragmentos de Skin<br>💰 +{ouro_total} Ouro<br>💎 +{gemas_totais} Gemas"
        return jsonify({"status": "success", "message": msg_final})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
