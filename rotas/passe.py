# rotas/passe.py
from flask import Blueprint, jsonify, request, render_template
from bson.objectid import ObjectId
from modules.player.core import users_collection
from modules.game_data.season_pass import RECOMPENSAS_PASSE

# Cria o Blueprint do Passe
passe_bp = Blueprint('passe_bp', __name__)

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
        genero_jogador = pdata.get("gender", "masculino").lower()

        def entregar_premio(premio):
            nonlocal ouro_total, gemas_totais
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
                resgatados_free.append(lv)

            if is_premium and config_lv.get("premium") and lv not in resgatados_premium:
                entregar_premio(config_lv["premium"])
                resgatados_premium.append(lv)

        if not recompensas_ganhas:
            return jsonify({"status": "info", "message": "Não há nada novo para coletar! 🏜️"})

        users_collection.update_one(
            {"_id": pdata["_id"]},
            {
                "$set": {
                    "passe_batalha.resgatados_free": resgatados_free,
                    "passe_batalha.resgatados_premium": resgatados_premium
                },
                "$inc": {"gold": ouro_total, "gems": gemas_totais}
            }
        )

        msg_final = f"Coletaste {len(recompensas_ganhas)} itens!<br>💰 +{ouro_total} Ouro<br>💎 +{gemas_totais} Gemas"
        return jsonify({"status": "success", "message": msg_final})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500