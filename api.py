import os
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
from bson.objectid import ObjectId

# Importações do seu jogo
from modules.game_data.classes import CLASSES_DATA
from modules.game_data.class_evolution import EVOLUTIONS

load_dotenv()

app = Flask(__name__)
CORS(app) 

# Conexão com o Banco de Dados
MONGO_URI = os.getenv("MONGO_CONNECTION_STRING")

if not MONGO_URI:
    print("⚠️ AVISO: MONGO_CONNECTION_STRING não encontrada!")

try:
    client = MongoClient(MONGO_URI)
    db = client['eldora_db']
    users_collection = db['users']
except Exception as e:
    print(f"Erro ao conectar no Mongo: {e}")

# ==========================================
# ROTA PRINCIPAL (MOSTRA O SITE)
# ==========================================
@app.route('/')
def home():
    return send_file('index.html')

# ==========================================
# ROTAS DE RANKING (COM ESCUDO DE ERROS)
# ==========================================
@app.route('/ranking/level')
def ranking_level():
    try:
        top = users_collection.find({}, {"character_name": 1, "level": 1, "_id": 0}).sort("level", -1).limit(10)
        lista = [{"nome": j.get("character_name", "Desconhecido"), "valor": f"Lvl {j.get('level', 1)}"} for j in top]
        return jsonify(lista)
    except Exception as e:
        # Se der erro no banco, ele MOSTRA o erro na tela do celular!
        return jsonify([{"nome": "⚠️ Erro no Banco", "valor": str(e)}])

@app.route('/ranking/ouro')
def ranking_ouro():
    try:
        top = users_collection.find({}, {"character_name": 1, "gold": 1, "_id": 0}).sort("gold", -1).limit(10)
        lista = [{"nome": j.get("character_name", "Desconhecido"), "valor": f"💰 {j.get('gold', 0)}"} for j in top]
        return jsonify(lista)
    except Exception as e:
        return jsonify([{"nome": "⚠️ Erro no Banco", "valor": str(e)}])

@app.route('/ranking/pvp')
def ranking_pvp():
    teste = [
        {"nome": "Murdock", "valor": "⚔️ 2500 Pontos"},
        {"nome": "Skuks", "valor": "⚔️ 2340 Pontos"}
    ]
    return jsonify(teste)

@app.route('/ranking/guildas')
def ranking_guildas():
    try:
        clans_collection = db['clans'] 
        top_clans = clans_collection.find(
            {}, 
            {"name": 1, "prestige_level": 1, "prestige_points": 1, "_id": 0} 
        ).sort([("prestige_level", -1), ("prestige_points", -1)]).limit(10)
        
        lista = []
        for clan in top_clans:
            nome = clan.get("name", "Sem Nome")
            prestigio = clan.get("prestige_level", 0)
            pontos = clan.get("prestige_points", 0)
            lista.append({"nome": nome, "valor": f"🌟 Lvl {prestigio} ({pontos} pts)"})
            
        if len(lista) == 0:
            return jsonify([{"nome": "Nenhuma guilda formada", "valor": "-"}])
        return jsonify(lista)
    except Exception as e:
        return jsonify([{"nome": "⚠️ Erro no Banco", "valor": str(e)}])

# ==========================================
# ROTA DE PERFIL (BUSCA CORRETA PELO OBJECT_ID)
# ==========================================
@app.route('/perfil/<user_id>')
def obter_perfil(user_id):
    try:
        busca_id = user_id
        
        if len(str(user_id)) == 24:
            try:
                busca_id = ObjectId(user_id)
            except:
                pass
        elif str(user_id).isdigit():
            busca_id = int(user_id)

        usuario = users_collection.find_one({
            "$or": [
                {"_id": busca_id},
                {"last_chat_id": busca_id},
                {"telegram_id_owner": busca_id},
                {"telegram_id": busca_id}
            ]
        })

        if usuario:
            lvl = int(usuario.get("level", 1))
            base = 200
            lin  = 100 * (lvl - 1)
            quad = 40 * (lvl - 1) * (lvl - 1)
            xp_visual_max = int(base + lin + quad) 

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
                "avatar": f"{request.host_url}static/classes/{usuario.get('class')}.png"
            }
            return jsonify(dados_perfil)
            
        return jsonify({"erro": "Personagem não encontrado no banco."}), 404
    except Exception as e:
        return jsonify({"erro": str(e)}), 400

# ==========================================
# ROTAS DA WIKI (CORRIGIDA COM TODOS OS STATUS)
# ==========================================
@app.route('/wiki/classes')
def obter_classes():
    lista_de_classes = []
    for chave, classe_info in CLASSES_DATA.items():
        if classe_info.get("tier") == 1:
            # Puxa a lista de evoluções
            caminho_evolucao = EVOLUTIONS.get(chave, [])
            detalhes_evolucoes = [
                {"nome": evo.get("display_name", ""), "tier": evo.get("tier_num", 0), "descricao": evo.get("desc", "")}
                for evo in caminho_evolucao
            ]
            
            # Puxa os atributos
            status = classe_info.get("stat_modifiers", {})
            
            dados_classe = {
                "id": chave,
                "nome": classe_info.get("display_name", "Desconhecida"),
                "emoji": classe_info.get("emoji", "❓"),
                "descricao": classe_info.get("description", "Sem descrição."),
                "hp": status.get("hp", 0),
                "ataque": status.get("attack", 0),
                "defesa": status.get("defense", 0),
                "imagem": f"{request.host_url}static/classes/{chave}.png",
                "total_evolucoes": len(caminho_evolucao),
                "evolucoes": detalhes_evolucoes
            }
            lista_de_classes.append(dados_classe)
            
    return jsonify(sorted(lista_de_classes, key=lambda x: x["nome"]))

# ==========================================
# ROTA: REGIÕES
# ==========================================
@app.route('/wiki/regioes')
def obter_regioes():
    lista = []
    try:
        from modules.game_data.worldmap import REGIONS_DATA, REGION_TARGET_POWER
        for chave, info in REGIONS_DATA.items():
            poder = REGION_TARGET_POWER.get(chave, 1)
            lista.append({
                "id": chave,
                "nome": info.get("display_name", "Região Desconhecida"),
                "emoji": info.get("emoji", "🗺️"),
                "descricao": info.get("description", "Uma área selvagem de Eldora."),
                "level_min": poder,
                "imagem": f"{request.host_url}static/regions/{chave}.jpg"
            })
    except Exception as e:
        print(f"Erro ao ler regiões: {e}")
    return jsonify(sorted(lista, key=lambda x: x["level_min"]))

# ==========================================
# ROTA: MONSTROS
# ==========================================
@app.route('/wiki/monstros')
def obter_monstros():
    lista = []
    try:
        from modules.game_data.monsters import MONSTERS_DATA
        mobs_vistos = set() # Evita mostrar o mesmo monstro duas vezes se ele estiver em 2 mapas
        
        # Como o seu arquivo divide por regiões, precisamos de dois "fors"
        for regiao, lista_mobs in MONSTERS_DATA.items():
            for mob in lista_mobs:
                mob_id = mob.get("id")
                if mob_id in mobs_vistos:
                    continue
                mobs_vistos.add(mob_id)
                
                lista.append({
                    "id": mob_id,
                    "nome": mob.get("name", "Monstro Desconhecido"),
                    "level": mob.get("min_level", mob.get("level", 1)),
                    "hp": mob.get("hp", 0),
                    "ataque": mob.get("attack", 0),
                    "defesa": mob.get("defense", 0),
                    "imagem": f"{request.host_url}static/monsters/{mob_id}.jpg"
                })
    except Exception as e:
        print(f"Erro ao ler monstros: {e}")
    return jsonify(sorted(lista, key=lambda x: x["level"]))

# ==========================================
# ROTA: ITENS
# ==========================================
@app.route('/wiki/itens')
def obter_itens():
    lista = []
    try:
        # Puxando direto da pasta onde você confirmou que o items.py está!
        from modules.game_data.items import ITEMS_DATA
            
        for chave, info in ITEMS_DATA.items():
            lista.append({
                "id": chave,
                "nome": info.get("display_name", "Item Desconhecido"),
                "raridade": str(info.get("rarity", "Comum")).capitalize(),
                "descricao": info.get("description", "Um item de Eldora."),
                "preco": info.get("value", info.get("price", 0)),
                "imagem": f"{request.host_url}static/items/{chave}.png"
            })
    except Exception as e:
        print(f"Erro ao ler itens: {e}")
    return jsonify(sorted(lista, key=lambda x: x["nome"]))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)