import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
from bson import ObjectId

# Importações do seu jogo
from modules.game_data.classes import CLASSES_DATA
from modules.game_data.class_evolution import EVOLUTIONS
from modules.game_data.xp import get_xp_for_next_combat_level

# Carrega as variáveis do arquivo .env
load_dotenv()

app = Flask(__name__)
CORS(app) 

# Puxa a chave do banco de forma segura do .env
MONGO_URI = os.getenv("MONGO_CONNECTION_STRING")
client = MongoClient(MONGO_URI)
db = client['eldora_db']
users_collection = db['users']

# ==========================================
# ROTAS DE RANKING
# ==========================================

# 1. Ranking de Nível (Dados Reais)
@app.route('/ranking/level')
def ranking_level():
    top = users_collection.find({}, {"character_name": 1, "level": 1, "_id": 0}).sort("level", -1).limit(10)
    lista = [{"nome": j.get("character_name"), "valor": f"Lvl {j.get('level')}"} for j in top]
    return jsonify(lista)

# 2. Ranking de Ouro (Dados Reais)
@app.route('/ranking/ouro')
def ranking_ouro():
    top = users_collection.find({}, {"character_name": 1, "gold": 1, "_id": 0}).sort("gold", -1).limit(10)
    lista = [{"nome": j.get("character_name"), "valor": f"💰 {j.get('gold', 0)}"} for j in top]
    return jsonify(lista)

# 3. Ranking PvP (Dados de Teste - Temporário)
@app.route('/ranking/pvp')
def ranking_pvp():
    teste = [
        {"nome": "Murdock", "valor": "⚔️ 2500 Pontos"},
        {"nome": "Skuks", "valor": "⚔️ 2340 Pontos"},
        {"nome": "Tulkas", "valor": "⚔️ 2100 Pontos"}
    ]
    return jsonify(teste)

# 4. Ranking de Guildas (DADOS REAIS - Por Prestígio)
@app.route('/ranking/guildas')
def ranking_guildas():
    try:
        clans_collection = db['clans'] 
        
        # Busca as guildas e ordena PRIMEIRO pelo prestígio, e DEPOIS pelos pontos
        top_clans = clans_collection.find(
            {}, 
            {"name": 1, "prestige_level": 1, "prestige_points": 1, "_id": 0} 
        ).sort([("prestige_level", -1), ("prestige_points", -1)]).limit(10)
        
        lista = []
        for clan in top_clans:
            nome = clan.get("name", "Sem Nome")
            prestigio = clan.get("prestige_level", 0)
            pontos = clan.get("prestige_points", 0)
            
            lista.append({"nome": nome, "valor": f"🌟 Prestígio {prestigio} ({pontos} pts)"})
            
        if len(lista) == 0:
            return jsonify([{"nome": "Nenhuma guilda formada ainda", "valor": "-"}])
            
        return jsonify(lista)
        
    except Exception as e:
        print(f"Erro ao buscar guildas: {e}")
        return jsonify([{"nome": "Erro ao ler banco", "valor": "-"}])

# ==========================================
# ROTA DE PERFIL (CORRIGIDA PARA TELEGRAM ID)
# ==========================================
@app.route('/perfil/<user_id>')
def obter_perfil(user_id):
    try:
        # Tenta converter o ID da URL para número ( IDs do Telegram são números)
        if user_id.isdigit():
            busca_id = int(user_id)
        else:
            try:
                busca_id = ObjectId(user_id)
            except:
                busca_id = user_id

        # Busca flexível: tenta achar pelo telegram_id, user_id ou _id
        usuario = users_collection.find_one({
            "$or": [
                {"telegram_id": busca_id},
                {"user_id": busca_id},
                {"_id": busca_id}
            ]
        })

        if usuario:
            lvl = int(usuario.get("level", 1))
            
            # --- FÓRMULA DE EXIBIÇÃO DO BOT (CURVA QUADRÁTICA PURA) ---
            base = 200
            lin  = 100 * (lvl - 1)
            quad = 40 * (lvl - 1) * (lvl - 1)
            xp_visual_max = int(base + lin + quad) 
            # ---------------------------------------------------------

            dados_perfil = {
                "nome": usuario.get("character_name", "Aventureiro"),
                "level": lvl,
                "gold": usuario.get("gold", 0),
                "gems": usuario.get("gems", 0),
                "classe": usuario.get("class", "aprendiz"),
                "xp": int(usuario.get("xp", 0)),
                "xp_max": xp_visual_max,
                "hp_atual": usuario.get("current_hp", 0),
                "hp_max": usuario.get("max_hp", 0),
                "energy": usuario.get("energy", 0),
                "pontos_livres": usuario.get("stat_points", 0),
                # request.host_url ajusta automaticamente entre localhost e nuvem!
                "avatar": f"{request.host_url}static/classes/{usuario.get('class')}.png"
            }
            return jsonify(dados_perfil)
            
        return jsonify({"erro": "Personagem não encontrado"}), 404
        
    except Exception as e:
        return jsonify({"erro": str(e)}), 400
      
# ==========================================
# ROTAS DA WIKI
# ==========================================
@app.route('/wiki/classes')
def obter_classes():
    lista_de_classes = []
    for chave, classe_info in CLASSES_DATA.items():
        if classe_info.get("tier") == 1:
            caminho_evolucao = EVOLUTIONS.get(chave, [])
            detalhes_evolucoes = [
                {"nome": evo.get("display_name", ""), "tier": evo.get("tier_num", 0), "descricao": evo.get("desc", "")}
                for evo in caminho_evolucao
            ]
            dados_classe = {
                "id": chave,
                "nome": classe_info.get("display_name", "Desconhecida"),
                "emoji": classe_info.get("emoji", "❓"),
                "descricao": classe_info.get("description", "Sem descrição."),
                "hp": classe_info.get("stat_modifiers", {}).get("hp", 0),
                "ataque": classe_info.get("stat_modifiers", {}).get("attack", 0),
                "defesa": classe_info.get("stat_modifiers", {}).get("defense", 0),
                # request.host_url ajusta automaticamente
                "imagem": f"{request.host_url}static/classes/{chave}.png",
                "total_evolucoes": len(caminho_evolucao),
                "evolucoes": detalhes_evolucoes
            }
            lista_de_classes.append(dados_classe)

    return jsonify(sorted(lista_de_classes, key=lambda x: x["nome"]))

if __name__ == "__main__":
    # Configuração crucial para rodar em servidores na nuvem
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)