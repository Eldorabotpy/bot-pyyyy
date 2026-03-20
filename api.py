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
# ROTAS DA WIKI: CLASSES
# ==========================================
@app.route('/wiki/classes')
def obter_classes():
    lista_de_classes = []
    from modules.game_data.classes import CLASSES_DATA
    from modules.game_data.class_evolution import EVOLUTIONS
    
    for chave, classe_info in CLASSES_DATA.items():
        if classe_info.get("tier") == 1:
            caminho_evolucao = EVOLUTIONS.get(chave, [])
            detalhes_evolucoes = [
                {"nome": evo.get("display_name", ""), "tier": evo.get("tier_num", 0), "descricao": evo.get("desc", "")}
                for evo in caminho_evolucao
            ]
            
            status = classe_info.get("stat_modifiers", {})
            
            dados_classe = {
                "id": chave,
                "nome": classe_info.get("display_name", "Desconhecida"),
                "emoji": classe_info.get("emoji", "❓"),
                "descricao": classe_info.get("description", "Sem descrição."),
                "hp": status.get("hp", 0),
                "ataque": status.get("attack", 0),
                "defesa": status.get("defense", 0),
                "imagem": classe_info.get("image_url", f"{request.host_url}static/classes/{chave}.png"),
                "video": classe_info.get("video_url", ""), # <--- A LINHA NOVA DO VÍDEO AQUI!
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
                # Tenta o link do Github primeiro, se não tiver, tenta a pasta local
                "imagem": info.get("image_url", f"{request.host_url}static/regions/{chave}.jpg")
            })
    except Exception as e:
        print(f"Erro ao ler regiões: {e}")
    return jsonify(sorted(lista, key=lambda x: x["level_min"]))

# ==========================================
# ROTA: MONSTROS (COM LOOT E ORDEM DE DIFICULDADE)
# ==========================================
@app.route('/wiki/monstros')
def obter_monstros():
    lista = []
    try:
        from modules.game_data.monsters import MONSTERS_DATA
        
        # Puxa o nome e o nível das regiões do seu arquivo worldmap
        nomes_regioes = {}
        poder_regioes = {}
        try:
            from modules.game_data.worldmap import REGIONS_DATA, REGION_TARGET_POWER
            for k, v in REGIONS_DATA.items():
                nomes_regioes[k] = v.get("display_name", k)
            poder_regioes = REGION_TARGET_POWER
        except: pass

        nomes_itens = {}
        try:
            from modules.game_data.items import ITEMS_DATA
            for k, v in ITEMS_DATA.items():
                emoji = v.get("emoji", "📦")
                nome = v.get("display_name", k.replace("_", " ").title())
                nomes_itens[k] = f"{emoji} {nome}"
        except: pass
            
        mobs_vistos = set() 
        for regiao_id, lista_mobs in MONSTERS_DATA.items():
            is_evento = regiao_id.startswith("_") or regiao_id in ["defesa_reino"]
            if regiao_id == "_evolution_trials": regiao_nome = "Desafios de Evolução"
            elif regiao_id == "defesa_reino": regiao_nome = "Defesa do Reino"
            else: regiao_nome = nomes_regioes.get(regiao_id, regiao_id.replace("_", " ").title())

            # Pegando a dificuldade (se for evento, joga lá pro final com 999)
            nivel_regiao = poder_regioes.get(regiao_id, 999) 

            for mob in lista_mobs:
                mob_id = mob.get("id")
                if mob_id in mobs_vistos: continue
                mobs_vistos.add(mob_id)
                
                loot_formatado = []
                for loot in mob.get("loot_table", []):
                    item_id = loot.get("item_id")
                    chance = loot.get("drop_chance", 0)
                    nome_formatado = nomes_itens.get(item_id, item_id.replace("_", " ").title())
                    loot_formatado.append({"nome": nome_formatado, "chance": chance})
                
                lista.append({
                    "id": mob_id,
                    "nome": mob.get("name", "Monstro Desconhecido"),
                    "level": mob.get("min_level", mob.get("level", 1)),
                    "hp": mob.get("hp", mob.get("max_hp", 0)),
                    "ataque": mob.get("attack", mob.get("atk", 0)),
                    "defesa": mob.get("defense", mob.get("def", 0)),
                    "xp": mob.get("xp_reward", 0),
                    "gold": mob.get("gold_drop", 0),
                    "loot": loot_formatado, 
                    "imagem": mob.get("image_url", f"{request.host_url}static/monsters/{mob_id}.jpg"),
                    "regiao_id": regiao_id,
                    "regiao_nome": regiao_nome,
                    "nivel_regiao": nivel_regiao, # <-- A dificuldade indo pro site!
                    "is_evento": is_evento
                })
    except Exception as e:
        print(f"Erro ao ler monstros: {e}")
        
    # Python já manda a lista arrumadinha!
    return jsonify(sorted(lista, key=lambda x: (x["is_evento"], x["nivel_regiao"], x["level"])))

# ==========================================
# ROTA: ITENS
# ==========================================
@app.route('/wiki/itens')
def obter_itens():
    lista = []
    try:
        from modules.game_data.items import ITEMS_DATA
        for chave, info in ITEMS_DATA.items():
            lista.append({
                "id": chave,
                "nome": info.get("display_name", "Item Desconhecido"),
                "raridade": str(info.get("rarity", "Comum")).capitalize(),
                "descricao": info.get("description", "Um item de Eldora."),
                "preco": info.get("value", info.get("price", 0)),
                # Tenta o link do Github primeiro
                "imagem": info.get("image_url", f"{request.host_url}static/items/{chave}.png")
            })
    except Exception as e:
        print(f"Erro ao ler itens: {e}")
    return jsonify(sorted(lista, key=lambda x: x["nome"]))

# ==========================================
# ROTA: SISTEMA DE LOGIN (SELEÇÃO DE PERSONAGEM)
# ==========================================
@app.route('/api/meus_personagens/<int:telegram_id>')
def listar_personagens(telegram_id):
    try:
        # Importa a conexão do seu banco de dados igual você faz nos seus arquivos
        from modules.player.core import users_collection
        
        if users_collection is None:
            return jsonify({"erro": "Banco de dados desconectado"}), 500

        # Busca personagens (usando a mesma lógica do seu queries.py)
        cursor = users_collection.find({
            "$or": [{"telegram_id": telegram_id}, {"telegram_owner_id": telegram_id}]
        })
        
        personagens = []
        for p in cursor:
            personagens.append({
                "id": str(p["_id"]), # O seu precioso ObjectId!
                "nome": p.get("character_name", "Desconhecido"),
                "classe": str(p.get("class", "aventureiro")).capitalize(),
                "level": p.get("level", 1)
            })
            
        return jsonify(personagens)
    except Exception as e:
        print(f"Erro ao buscar personagens do ID {telegram_id}: {e}")
        return jsonify([])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)