import os
import asyncio
import random
import time
import logging
from datetime import datetime
from threading import Thread
from flask import Flask, render_template, jsonify, request
from flask.json.provider import DefaultJSONProvider
from flask_socketio import SocketIO, emit
from bson import ObjectId, errors
from pymongo import MongoClient

from config import MONGO_CONNECTION_STRING
from modules.database import initialize_database
from modules.player.core import users_collection
from modules.webapp_api import webapp_bp
from modules.game_data.skills import SKILL_DATA
from modules.game_data.monsters import MONSTERS_DATA
from modules.game_data.season_pass import adicionar_xp_passe
from eventos_invasao import GerenciadorInvasao
from modules.mob_engine import GerenciadorCacada
from modules import player_manager
from modules.combat.party_engine import obter_grupo_do_jogador, sair_ou_desfazer_grupo
from modules.combat import group_combat_manager as gcm
# from modules.combat.web_battle_manager import WebBattleManager
# pyrefly: ignore [missing-import]
from telegram.ext import Application, CommandHandler
from telegram.error import NetworkError, TimedOut
from config import TELEGRAM_TOKEN
from start_handler import start_command
# ==============================================================================
# 🔇 CONTROLE DE LOGS EXTERNOS
# ==============================================================================
# Mantém o terminal limpo.
# WARNING e ERROR continuam aparecendo quando forem realmente importantes.
# ==============================================================================

logging.getLogger("werkzeug").setLevel(logging.WARNING)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)
logging.getLogger("start_handler").setLevel(logging.WARNING)
logging.getLogger("modules.crafting_registry").setLevel(logging.WARNING)
logging.getLogger("engineio").setLevel(logging.WARNING)
logging.getLogger("socketio").setLevel(logging.WARNING)

# 👇 IMPORTS CORRETOS DO NOVO SISTEMA DE PARTY 👇
from modules.combat.party_engine import parties_collection, criar_novo_grupo, adicionar_membro, obter_grupo
from modules.cooldowns import iniciar_turno, aplicar_cooldown
from modules.combat.combat_engine import processar_acao_combate
from modules.game_data.items_consumables import CONSUMABLES_DATA
from modules.player.combat_stats import get_combat_stats_sync, aplicar_combat_stats_no_player
# ==============================================================================
# 1. INICIALIZAÇÃO DO MOTOR E REGISTRO DE ROTAS
# ==============================================================================

class MongoJSONProvider(DefaultJSONProvider):
    """
    Permite enviar ObjectId do MongoDB em respostas JSON.
    O ObjectId permanece normal no banco e vira string apenas na resposta.
    """

    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)

        return super().default(obj)


initialize_database()

app = Flask('')

# JSON global compatível com ObjectId do MongoDB.
app.json = MongoJSONProvider(app)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY"
)

if not app.secret_key:
    raise RuntimeError(
        "FLASK_SECRET_KEY não configurada."
    )

client = MongoClient(
    MONGO_CONNECTION_STRING
)

# --- REGISTRO DOS BLUEPRINTS ---
app.register_blueprint(webapp_bp)

from rotas.admin import admin_bp
from rotas.passe import passe_bp
from rotas.character import character_bp
from rotas.loja_reino import registrar_loja_reino
from rotas.npc import npc_bp

app.register_blueprint(admin_bp)
app.register_blueprint(passe_bp)
app.register_blueprint(character_bp)
app.register_blueprint(npc_bp)

# --- INICIALIZAÇÃO SOCKET E MONGO ---
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading",
    logger=False,
    engineio_logger=False
)
conexoes_mapa = {}
url_do_jogo = "https://163-176-44-198.sslip.io"

db = client["eldora_bot"]
chat_collection = db["chat_historico"]
chat_collection.create_index("data_envio", expireAfterSeconds=43200)

# 📬 NOVA COLEÇÃO: Correios de Eldora (Mensagens Privadas Offline)
# 2592000 segundos = Exatamente 30 dias! Depois disso o Mongo apaga sozinho.
mensagens_offline_col = db["mensagens_offline"]
mensagens_offline_col.create_index("data_envio", expireAfterSeconds=2592000)

sistema_invasao_mapa = GerenciadorInvasao(socketio)

app.config[
    "SISTEMA_INVASAO_MAPA"
] = sistema_invasao_mapa

sistema_cacada = GerenciadorCacada(socketio)
sistema_cacada.app = app
# battle_manager = WebBattleManager(socketio)
app.config['SISTEMA_CACADA'] = sistema_cacada

# ==============================================================================
# 2. ROTAS PRINCIPAIS (TELA INICIAL E QUESTS)
# ==============================================================================

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def pagina_login():
    return render_template('login.html')

@app.route('/api/recent_premium')
def obter_recent_premium():
    try:
        cursor = users_collection.find(
            {"premium_tier": {"$ne": "free"}}, 
            {"character_name": 1, "premium_tier": 1, "_id": 0}
        ).sort("_id", -1).limit(5)
        
        colaboradores = [{"nome": c.get("character_name", "Aventureiro"), "tier": str(c.get("premium_tier", "VIP")).upper()} for c in cursor]
        return jsonify(colaboradores)
    except Exception:
        return jsonify([])

@app.route('/api/eventos_ativos/<user_id>', methods=['GET'])
def api_eventos_ativos_seguro(user_id):
    try:
        eventos = [
            {
                "id": "world_boss",
                "nome": "👹 World Boss",
                "descricao": "A fera está dormindo.",
                "tempo_texto": "⏰ 08h, 14h, 19h e 23h",
                "cor": "#475569",
                "botao_texto": "DORMINDO",
                "funcao_click": "console.log('Boss dormindo')",
                "btn_estilo": "background: #1e293b; border-color: #0f172a; color: #64748b; cursor: not-allowed;"
            }
        ]
        return jsonify(eventos)
    except Exception:
        return jsonify([])

@app.route('/api/quest/completar', methods=['POST'])
def completar_quest():
    try:
        data = request.json
        uid = data.get('user_id')
        qid = data.get('quest_id')
        
        player = users_collection.find_one({"_id": ObjectId(uid)})
        
        if player:
            quest_atual = player.get('quests', {}).get(qid, {})
            if quest_atual.get('status') == 'resgatada':
                return jsonify({"sucesso": False, "erro": "A missão já foi paga antes!"})
            
            users_collection.update_one(
                {"_id": ObjectId(uid)},
                {
                    "$set": {f"quests.{qid}.status": "resgatada"},
                    "$inc": {"gold": 100}
                }
            )
            return jsonify({"sucesso": True})
                
        return jsonify({"sucesso": False, "erro": "O servidor não encontrou este personagem pelo ObjectId."})
        
    except Exception as e:
        print("Erro crítico na API de quests:", str(e))
        return jsonify({"sucesso": False, "erro": f"Erro interno: {str(e)}"}), 500
      
@app.route('/api/quest/iniciar', methods=['POST'])
def iniciar_quest():
    try:
        data = request.json
        uid = data.get('user_id')
        qid = data.get('quest_id')
        qdata = data.get('quest_data')

        if not uid or not qid or not qdata:
            return jsonify({"sucesso": False, "erro": "Dados incompletos enviados ao servidor."}), 400

        player = users_collection.find_one({"_id": ObjectId(uid)})
        
        if player:
            users_collection.update_one(
            {"_id": ObjectId(uid)},
            {"$set": {f"quests.{qid}": qdata}}
            )
            return jsonify({"sucesso": True})
            
        return jsonify({"sucesso": False, "erro": f"Herói com ID {uid} não encontrado!"})
        
    except Exception as e:
        print("Erro ao iniciar quest:", str(e))
        return jsonify({"sucesso": False, "erro": str(e)}), 500

@app.route('/api/player/escolher_classe', methods=['POST'])
def escolher_classe():
    try:
        data = request.json
        user_id = data.get('user_id')
        nova_classe = data.get('nova_classe')

        player = users_collection.find_one({"_id": ObjectId(user_id)})
        if not player:
            return jsonify({"sucesso": False, "erro": "Jogador não encontrado!"})

        if player.get("level", 1) < 5:
            return jsonify({"sucesso": False, "erro": "Você precisa do Nível 5 para o ritual!"})

        from modules.game_data.classes import CLASSES_DATA, get_class_avatar
        dados_classe = CLASSES_DATA.get(nova_classe)

        if not dados_classe:
            return jsonify({"sucesso": False, "erro": "Esta classe não existe nos pergaminhos."})

        mods = dados_classe.get("stat_modifiers", {})
        level_atual = player.get("level", 5)
        
        # Fórmula: Base inicial + (Ganhos por level * multiplicador da classe)
        novo_max_hp = int(50 + (level_atual * 10 * mods.get('hp', 1.0)))
        novo_max_mp = int(50 + (level_atual * 5 * mods.get('max_mana', 1.0)))
        
        genero = player.get("gender", "masculino")
        nova_skin = f"{nova_classe}_{genero}" 
        novo_avatar_url = get_class_avatar(nova_classe, genero, "web")

        # 👇 1. Cria os IDs curtos para os cosméticos (Ex: guerreiro_m)
        genero_curto = "f" if genero == "feminino" else "m"
        nova_skin_id = f"{nova_classe}_{genero_curto}"
        novo_avatar_id = f"{nova_classe}_{genero_curto}"

        users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "class": nova_classe,
                    "skin": nova_skin,         
                    "avatar": novo_avatar_url, 
                    # 👇 2. FORÇA A TROCA NO SISTEMA DE COSMÉTICOS 👇
                    "equipped_skin": nova_skin_id,        
                    "avatar_customizado": novo_avatar_id, 
                    "max_hp": novo_max_hp,
                    "current_hp": novo_max_hp, 
                    "max_mana": novo_max_mp,
                    "current_mp": novo_max_mp,
                    "quests.q4_selene_classe.status": "resgatada"
                },
                # 👇 3. DESBLOQUEIA PARA SEMPRE NO GUARDA-ROUPA 👇
                "$addToSet": {
                    "unlocked_skins": nova_skin_id,
                    "unlocked_avatars": novo_avatar_id
                }
            }
        )

        return jsonify({"sucesso": True})
        
    except Exception as e:
        print(f"Erro na transmutação de classe: {str(e)}")
        return jsonify({"sucesso": False, "erro": "Falha na magia do servidor."})
        
@app.route('/api/debug/iniciar_invasao_mapa')
def admin_iniciar_invasao_mapa():
    try:
        sistema_invasao_mapa.iniciar_invasao(jogadores_online)
        return jsonify({"msg": "Invasão iniciada com sucesso no mapa!"})
    except Exception as e:
        import traceback
        erro_detalhado = traceback.format_exc()
        return f"<h1 style='color:red;'>🚨 ERRO! 🚨</h1><pre>{erro_detalhado}</pre>"

@app.route('/api/debug/reset_parties')
def admin_reset_parties():
    try:
        # Destrói todos os registos da coleção de grupos no MongoDB
        from modules.combat.party_engine import parties_collection
        parties_collection.delete_many({})
        return "<h1 style='color:#2ecc71; text-align:center; margin-top:50px;'>💥 BOOM! Todas as Parties Fantasmas foram destruídas! O Bastos está livre.</h1>"
    except Exception as e:
        return f"<h1 style='color:red;'>🚨 ERRO: {str(e)}</h1>"

def _buscar_sids_por_char_ids(char_ids):
    encontrados = {}
    alvo_set = set(str(x) for x in char_ids)

    for sid, info in jogadores_online.items():
        if str(info.get("char_id")) in alvo_set:
            encontrados[str(info.get("char_id"))] = sid

    return encontrados


def _ids_participantes_grupo(grupo):
    ids = []

    def adicionar(valor):
        if not valor:
            return

        if isinstance(valor, dict):
            valor = valor.get("char_id") or valor.get("_id") or valor.get("id")

        valor = str(valor)

        if valor and valor not in ids:
            ids.append(valor)

    adicionar(grupo.get("lider"))

    for membro_id in grupo.get("membros", []) or []:
        adicionar(membro_id)

    return ids[:5]


def _montar_equipe_herois_grupo(grupo, regiao_atual):
    from bson import ObjectId
    from modules.player.combat_stats import get_combat_stats_sync, aplicar_combat_stats_no_player

    equipe = []
    pendentes = []

    participantes_ids = _ids_participantes_grupo(grupo)

    online_por_char = {}

    for sid, info in list(jogadores_online.items()):
        char_id = str(info.get("char_id") or "")

        if char_id in participantes_ids:
            online_por_char[char_id] = info

    for membro_id_str in participantes_ids:
        online_info = online_por_char.get(membro_id_str)

        if not online_info:
            pendentes.append({
                "char_id": membro_id_str,
                "motivo": "offline_ou_webapp_nao_carregado"
            })
            continue

        try:
            player_db = users_collection.find_one({"_id": ObjectId(membro_id_str)})
        except Exception:
            player_db = None

        if not player_db:
            pendentes.append({
                "char_id": membro_id_str,
                "motivo": "personagem_nao_encontrado"
            })
            continue

        regiao_online = (
            online_info.get("regiao")
            or online_info.get("current_location")
            or player_db.get("current_location")
        )

        if regiao_online != regiao_atual:
            pendentes.append({
                "char_id": membro_id_str,
                "nome": player_db.get("character_name", "Herói"),
                "motivo": f"regiao_diferente:{regiao_online}"
            })
            continue

        stats = get_combat_stats_sync(player_db)
        player_db = aplicar_combat_stats_no_player(player_db, stats)

        equipe.append({
            "char_id": membro_id_str,
            "nome": player_db.get("character_name", "Herói"),
            "level": player_db.get("level", 1),
            "current_hp": stats.get("current_hp", stats.get("max_hp", 100)),
            "current_mp": stats.get("current_mp", stats.get("max_mana", 50)),
            "max_hp": stats.get("max_hp", 100),
            "max_mana": stats.get("max_mana", 50),
            "attack": stats.get("attack", 5),
            "defense": stats.get("defense", 0),
            "initiative": stats.get("initiative", 5),
            "luck": stats.get("luck", 0),
            "magic_attack": stats.get("magic_attack", 0),
        })

    return equipe, pendentes, participantes_ids

@app.route('/api/combate/iniciar', methods=['POST'])
def iniciar_combate():
    try:
        data = request.json
        user_id = data.get('user_id')
        if data.get('sala_id'):
            sala_convocada = gcm.obter_sala(data['sala_id'])
            if (not sala_convocada or sala_convocada.get('retorno_mapa') or
                    str(user_id) not in list(map(str, sala_convocada.get('membros_ids', [])))):
                return jsonify({'erro': 'Convocação expirada ou jogador fora desta caçada.'}), 403
        else:
            sala_em_curso = gcm.obter_sala_do_jogador(str(user_id))
            if sala_em_curso and sala_em_curso.get('spawn_id') != data.get('spawn_id'):
                return jsonify({'erro': 'Seu grupo já está em outra caçada.'}), 409

        spawn_id = data.get('spawn_id')

        # 🔍 Busca o jogador no banco de dados
        player = users_collection.find_one({"_id": ObjectId(user_id)})
        if not player:
            return jsonify({"erro": "Herói não encontrado nos registros."})

        # ==========================================
        # 💥 FONTE ÚNICA DE STATUS DE COMBATE
        # ==========================================
        player_stats_calculados = get_combat_stats_sync(player)
        player = aplicar_combat_stats_no_player(player, player_stats_calculados)

        hp_max_real = int(player_stats_calculados.get("max_hp", 50))
        mp_max_real = int(player_stats_calculados.get("max_mana", 50))

        player_hp = int(player_stats_calculados.get("current_hp", hp_max_real))
        player_mp = int(player_stats_calculados.get("current_mp", mp_max_real))

        # Determina a região e o monstro
        regiao_atual = player.get('current_location', 'capital_eldora')
        for sid, info in jogadores_online.items():
            if str(info.get('char_id')) == str(user_id):
                regiao_atual = info.get('regiao', regiao_atual)
                break
                
        monster_id_real = "slime_verde"
        mob_vivo = None 
        
        if regiao_atual in sistema_cacada.mobs_vivos and spawn_id in sistema_cacada.mobs_vivos[regiao_atual]:
            mob_vivo = sistema_cacada.mobs_vivos[regiao_atual][spawn_id]
            monster_id_real = mob_vivo.get("monster_id", "slime_verde")
            
        mob_data = None
        for categoria, mobs in MONSTERS_DATA.items():
            if categoria.startswith('_'): continue
            for m in mobs:
                if m.get('id') == monster_id_real:
                    mob_data = m
                    break
            if mob_data: break

        if not mob_data:
            return jsonify({"erro": "O monstro fugiu para a floresta!"})
            
        # Status dinâmicos do monstro
        mob_level_final = mob_vivo.get("level", mob_data.get('min_level', 1)) if mob_vivo else mob_data.get('min_level', 1)
        mob_hp_final = mob_vivo.get("hp_atual", mob_data.get('hp', 50)) if mob_vivo else mob_data.get('hp', 50)
        mob_hp_max = mob_vivo.get("hp_max", mob_data.get('hp', 50)) if mob_vivo else mob_data.get('hp', 50)
        mob_atk_final = mob_vivo.get("attack", mob_data.get('attack', 5)) if mob_vivo else mob_data.get('attack', 5)
        mob_def_final = mob_vivo.get("defense", mob_data.get('defense', 0)) if mob_vivo else mob_data.get('defense', 0)
        
        # ==========================================
        # 💥 SISTEMA DE EMBOSCADA (AMBUSH)
        # ==========================================
        ambush_log = None
        raw_chance = float(mob_data.get('ambush_chance', 0.0))
        
        if raw_chance > 0 and player_hp > 0:
            chance_base = raw_chance if raw_chance <= 1.0 else (raw_chance / 100.0)
            
            # Agilidade (Iniciativa) e Sorte reduzem a chance de emboscada
            evasao = (player_stats_calculados.get('initiative', 5) + player_stats_calculados.get('luck', 5)) * 0.005
            chance_final = max(0.02, chance_base - evasao)
            
            if random.random() < chance_final:
                defesa_player = player_stats_calculados.get('defense', 0)
                dano = max(1, mob_atk_final - (defesa_player // 2))
                player_hp = max(0, player_hp - dano)
                
                nome_mob_tela = mob_data.get('name', 'Monstro')
                textos_susto = [
                    f"⚠️ EMBOSCADA! O monstro atacou de surpresa: -{dano} HP!",
                    f"🩸 ATAQUE FURTIVO! {nome_mob_tela} saltou em você: -{dano} HP!"
                ]
                ambush_log = random.choice(textos_susto)
                
                # Salva o HP no banco imediatamente
                users_collection.update_one({"_id": player["_id"]}, {"$set": {"current_hp": player_hp}})
        
        # Lógica do Bestiário
        bestiario = player.get("bestiario", {})
        abates = bestiario.get(monster_id_real, 0)
        nivel_conhecimento = 3 if abates >= 50 else 2 if abates >= 10 else 1 if abates >= 1 else 0

        nome_mob_tela = mob_data.get('name', 'Monstro') if nivel_conhecimento > 0 else "Criatura Desconhecida"
        lvl_mob_tela = mob_level_final if nivel_conhecimento > 0 else "??"

        pastas_github = {"capital_eldora": "capital", "pradaria_inicial": "pradaria", "floresta_sombria": "floresta", "pedreira_granito": "pedreira"}
        nome_da_pasta = pastas_github.get(regiao_atual, regiao_atual)
        link_imagem_monstro = f"https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/mob/combate/{nome_da_pasta}/{mob_data.get('id')}.png"
        
        # Estado final enviado para o combate.js
        estado = {
            "regiao": regiao_atual,
            "spawn_id": spawn_id,
            "mob_nome": nome_mob_tela,
            "mob_img": link_imagem_monstro,
            "monster_level": lvl_mob_tela, 
            "monster_hp": mob_hp_final,
            "monster_stats": {
                "max_hp": mob_hp_max, 
                "attack": mob_atk_final,
                "defense": mob_def_final,
                "initiative": mob_data.get('initiative', 0),
                "luck": mob_data.get('luck', 0)
            },
            "player_hp": player_hp, 
            "player_mp": player_mp,
            "player_level": player.get('level', 1),
            # Envia os limites REAIS (155 Mana / 162 Vida) para o Javascript
            "player_stats": {"max_hp": hp_max_real, "max_mana": mp_max_real}, 
            "classe_player": player.get('class', 'aventureiro'),
            "genero_player": player.get('gender', 'masculino'),
            "nivel_conhecimento": nivel_conhecimento,
            "abates_bestiario": abates,
            "ambush_log": ambush_log 
        }
        
                # ==========================================
        # 🤝 ENTRADA EM COMBATE DE GRUPO
        # ==========================================
        sala_id_recebida = data.get("sala_id")
        modo_grupo = data.get("modo_grupo", False)

        # Se o jogador já veio convocado por uma sala existente
        if sala_id_recebida:
            sala_existente = gcm.obter_sala(sala_id_recebida)
            return jsonify({
                "estado": estado,
                "grupo": True,
                "sala_id": sala_id_recebida,
                "sala": gcm.pacote_estado_sala(sala_id_recebida) if sala_existente else None
            })

        grupo = obter_grupo_do_jogador(str(user_id))

        if grupo and mob_vivo:
            lider_id = str(grupo.get("lider"))

            if lider_id != str(user_id):
                sala_existente = gcm.obter_sala_por_spawn(regiao_atual, spawn_id)

                if sala_existente:
                    return jsonify({
                        "estado": estado,
                        "grupo": True,
                        "sala_id": sala_existente["sala_id"],
                        "sala": gcm.pacote_estado_sala(sala_existente["sala_id"])
                    })

                return jsonify({
                    "erro": "Apenas o líder do grupo pode iniciar a caçada em grupo."
                })

            # Por enquanto só o líder cria a sala
            if lider_id == str(user_id):
                sala_existente = gcm.obter_sala_por_spawn(regiao_atual, spawn_id)

                if sala_existente:
                    return jsonify({
                        "estado": estado,
                        "grupo": True,
                        "sala_id": sala_existente["sala_id"],
                        "sala": gcm.pacote_estado_sala(sala_existente["sala_id"])
                    })
                else:
                    equipe, pendentes, participantes_ids = _montar_equipe_herois_grupo(grupo, regiao_atual)

                    total_membros_grupo = len(participantes_ids)

                    if pendentes or len(equipe) != total_membros_grupo:

                        return jsonify({
                            "erro": f"Aguardando todos os membros do grupo carregarem o mapa. Prontos: {len(equipe)}/{total_membros_grupo}",
                            "grupo": True,
                            "aguardando_grupo": True,
                            "prontos": len(equipe),
                            "total": total_membros_grupo,
                            "participantes": participantes_ids,
                            "pendentes": pendentes
                        })

                    if len(equipe) >= 2:
                        sala = gcm.criar_cacada_grupo(
                            equipe_herois=equipe,
                            mob_vivo=mob_vivo,
                            regiao=regiao_atual,
                            spawn_id=spawn_id,
                            lider_id=str(user_id),
                            grupo_id=str(grupo.get("_id", ""))
                        )

                        pacote = {
                            "sala_id": sala["sala_id"],
                            "spawn_id": spawn_id,
                            "regiao": regiao_atual,
                            "lider_id": str(user_id),
                            "estado": estado,
                            "sala": gcm.pacote_estado_sala(sala["sala_id"])
                        }

                        sids = _buscar_sids_por_char_ids(sala.get("membros_ids", []))

                        for membro_id, sid in sids.items():
                            if str(membro_id) != str(user_id):
                                socketio.emit("convocarCombateGrupo", pacote, to=sid)

                        return jsonify({
                            "estado": estado,
                            "grupo": True,
                            "sala_id": sala["sala_id"],
                            "sala": gcm.pacote_estado_sala(sala["sala_id"])
                        })
        return jsonify({"estado": estado, "grupo": False})

    except Exception:
        import traceback
        print(
            "🚨 Erro ao iniciar combate:\n"
            + traceback.format_exc()
        )
        return jsonify({"erro": "Falha mágica no servidor!"}), 500

@app.route('/api/combate/grupo/pronto', methods=['POST'])
def combate_grupo_pronto():
    try:
        data = request.get_json() or {}

        sala_id = str(data.get("sala_id") or "")
        user_id = str(data.get("user_id") or data.get("char_id") or "")

        if not sala_id or not user_id:
            return jsonify({"erro": "Dados inválidos para marcar pronto."}), 400

        sala = gcm.marcar_membro_pronto(sala_id, user_id)

        if not sala:
            return jsonify({"erro": "Sala de combate não encontrada."}), 404

        pacote_sala = gcm.pacote_estado_sala(sala_id)

        payload = {
            "sala_id": sala_id,
            "spawn_id": sala.get("spawn_id"),
            "sala": pacote_sala,
            "estado": pacote_sala.get("estado") if pacote_sala else sala.get("estado"),
            "turno_atual": pacote_sala.get("turno_atual") if pacote_sala else None,
            "finalizado": False,
            "log": [],
        }

        membros_ids = set(str(x) for x in sala.get("membros_ids", []))
        sids_enviados = set()

        for sid, info in list(jogadores_online.items()):
            char_online = str(info.get("char_id"))

            if char_online in membros_ids:
                socketio.emit("estadoSalaGrupo", payload, to=sid)
                socketio.emit("grupoCombateEstado", payload, to=sid)
                sids_enviados.add(sid)

        # Broadcast sempre, para não depender de SID velho.
        socketio.emit("estadoSalaGrupo", payload)
        socketio.emit("grupoCombateEstado", payload)

        return jsonify(payload)

    except Exception:
        import traceback
        print(
            "🚨 Erro ao marcar membro pronto:\n"
            + traceback.format_exc()
        )
        return jsonify({"erro": "Falha ao marcar pronto no combate."}), 500
                               
# ==============================================================================
# 3. MULTIPLAYER (SOCKET.IO)
# ==============================================================================
jogadores_online = {}
app.config['JOGADORES_ONLINE'] = jogadores_online
registrar_loja_reino(socketio, db, jogadores_online)


@socketio.on('jogador_morreu')
def handle_jogador_morreu(data):
    emit('mostrarLapide', data, broadcast=True, include_self=False)

    player_sid = request.sid
    jogador_info = jogadores_online.get(player_sid)

    if not jogador_info or 'char_id' not in jogador_info:
        return

    char_id = jogador_info['char_id']
    player_data = users_collection.find_one({"_id": ObjectId(char_id)})

    if not player_data:
        return

    stats = get_combat_stats_sync(player_data)
    hp_maximo_real = int(stats.get("max_hp", 100))
    mp_maximo_real = int(stats.get("max_mana", 50))

    users_collection.update_one(
        {"_id": ObjectId(char_id)},
        {"$set": {
            "current_hp": hp_maximo_real,
            "current_mp": mp_maximo_real,
            "stats": aplicar_combat_stats_no_player(player_data, stats).get("stats", {}),
            "max_hp": hp_maximo_real,
            "max_mana": mp_maximo_real,
            "attack": int(stats.get("attack", 0)),
            "defense": int(stats.get("defense", 0)),
            "initiative": int(stats.get("initiative", 0)),
            "luck": int(stats.get("luck", 0)),
            "magic_attack": int(stats.get("magic_attack", 0)),
        }}
    )

@socketio.on('dispararEventoGlobal')
def handle_evento_global(dados):
    # Pega o evento que o Javascript enviou e repassa para TODOS os jogadores (broadcast=True)
    emit('efeitoGlobalMapa', dados, broadcast=True)
    
@socketio.on('enviarMensagemChat')
def handle_chat_message(dados):
    try:
        player_sid = request.sid
        if player_sid not in jogadores_online: 
            emit('solicitarRegistro', {}, to=player_sid)
            return

        remetente = jogadores_online[player_sid]['nome']
        char_id = jogadores_online[player_sid]['char_id']
        mensagem = dados.get('texto', '').strip()
        
        if not mensagem: return

        # 📸 MÁGICA DO AVATAR: Busca a foto real do jogador no banco de dados!
        jogador_db = users_collection.find_one({"_id": ObjectId(char_id)})
        avatar_real = "avatar_padrao_m"
        if jogador_db:
            ac = jogador_db.get("avatar_customizado")
            if ac and ac != "padrao":
                avatar_real = ac.get("path", ac) if isinstance(ac, dict) else ac
            else:
                avatar_real = jogador_db.get("avatar", "avatar_padrao_m")

        # 🔧 A CORREÇÃO: Adiciona o prefixo 'avatar_' se faltar!
        nome_puro = avatar_real.split("/")[-1].replace(".png", "")
        if not nome_puro.startswith("avatar_") and "cunminicon" not in nome_puro:
            nome_puro = f"avatar_{nome_puro}"
            
        avatar_real = f"https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/avatares/{nome_puro}.png"
         
        # 1. VERIFICA SUSSURRO (PRIVADO)
        if mensagem.startswith('/w '):
            nome_alvo = ""
            texto_real = ""
            if '"' in mensagem:
                partes = mensagem.split('"', 2)
                if len(partes) >= 3:
                    nome_alvo = partes[1]
                    texto_real = partes[2].strip()
            else:
                partes = mensagem.split(' ', 2)
                if len(partes) >= 3:
                    nome_alvo = partes[1]
                    texto_real = partes[2].strip()
                    
            if nome_alvo and texto_real:
                # Salva o Sussurro COM O AVATAR no banco
                pacote_offline = {
                    "remetente": remetente, "destinatario": nome_alvo,
                    "texto": texto_real, "data_envio": datetime.utcnow(), "lida": False,
                    "avatar": avatar_real 
                }
                mensagens_offline_col.insert_one(pacote_offline)

                emit('novaMensagemChat', {"remetente": f"Para {nome_alvo}", "texto": texto_real, "tipo": "privado", "nome_puro": nome_alvo, "avatar": avatar_real}, to=player_sid)

                alvo_online = False
                for sid, info in jogadores_online.items():
                    if info.get('nome') == nome_alvo:
                        emit('novaMensagemChat', {"remetente": remetente, "texto": texto_real, "tipo": "privado", "nome_puro": remetente, "avatar": avatar_real}, to=sid)
                        alvo_online = True
                        break
                
                if not alvo_online:
                    emit('novaMensagemChat', {"remetente": "Sistema", "texto": f"Aviso: {nome_alvo} está off-line. A mensagem foi guardada!", "tipo": "erro"}, to=player_sid)
            else:
                emit('novaMensagemChat', {"remetente": "Sistema", "texto": "Formato inválido.", "tipo": "erro"}, to=player_sid)
            
            return

        # 2. VERIFICA GRUPO
        if mensagem.startswith('/g '):
            texto_real = mensagem[3:].strip()
            if texto_real:
                grupo = obter_grupo_do_jogador(char_id)
                if grupo:
                    for membro_id in grupo.get('membros', []):
                        for sid, info in jogadores_online.items():
                            if str(info['char_id']) == str(membro_id):
                                emit('novaMensagemChat', {"remetente": remetente, "texto": texto_real, "tipo": "grupo", "avatar": avatar_real}, to=sid)
                else:
                     emit('novaMensagemChat', {"remetente": "Sistema", "texto": "Você não está em um grupo.", "tipo": "erro"}, to=player_sid)
            return

        # 3. SE CHEGOU AQUI É MENSAGEM GLOBAL!
        # Salva o Global COM O AVATAR no banco
        pacote_global = {
            "remetente": remetente, "texto": mensagem,
            "alvo": "global", "data_envio": datetime.utcnow(),
            "avatar": avatar_real 
        }
        chat_collection.insert_one(pacote_global)
        
        for sid in list(jogadores_online.keys()):
            emit('novaMensagemChat', {"remetente": remetente, "texto": mensagem, "tipo": "global", "avatar": avatar_real}, to=sid)
            
    except Exception as e:
        print(f"🚨 ERRO GRAVE NO CHAT: {str(e)}")
                     
@socketio.on('enviarConviteGrupo')
def handle_convite_grupo(dados):

    
    alvo_id = dados.get('alvo_id')
    remetente_sid = request.sid
    remetente = jogadores_online.get(remetente_sid)
    
    if not remetente:
        return
    if not alvo_id:
        return

    lider_id = str(remetente['char_id'])

    try:
        # 1. Verifica se o ALVO já tem grupo
        if obter_grupo_do_jogador(alvo_id):
            emit('novaMensagemChat', {'remetente': 'Sistema', 'texto': '❌ O jogador já está num grupo!', 'tipo': 'erro'}, room=remetente_sid)
            return

        # 2. Verifica se o LÍDER já tem grupo (para não duplicar)
        grupo_existente = obter_grupo_do_jogador(lider_id)
        if grupo_existente:
            if grupo_existente["lider"] != lider_id:
                emit(
                    'novaMensagemChat',
                    {
                        'remetente': 'Sistema',
                        'texto': '❌ Só o líder pode convidar!',
                        'tipo': 'erro'
                    },
                    room=remetente_sid
                )
                return
            party_id = str(grupo_existente["_id"])

        else:
            party_id = criar_novo_grupo(lider_id, remetente['nome'], remetente['regiao'])

        # Atualiza o HUD do líder na hora
        grupo_fresco = obter_grupo(party_id)
        if grupo_fresco:
            emit('atualizarListaGrupo', grupo_fresco, room=remetente_sid)

        # 3. Procura o Bastos online para mandar o modal Épico
        alvo_encontrado = False
        for sid, info in jogadores_online.items():
            if str(info['char_id']) == str(alvo_id):
                
                # Dispara o Modal para o Bastos
                emit('receberConviteGrupo', {'party_id': party_id, 'remetente_id': lider_id, 'remetente_nome': remetente['nome']}, room=sid)
                
                # Confirma no chat do remetente
                emit('novaMensagemChat', {'remetente': 'Sistema', 'texto': f'📩 Convite enviado para {info.get("nome", "aliado")}!', 'tipo': 'privado'}, room=remetente_sid)
                
                alvo_encontrado = True
                break

        # A BLINDAGEM: Se ele não achar o Bastos, avisa você!
        if not alvo_encontrado:
            emit('novaMensagemChat', {'remetente': 'Sistema', 'texto': '❌ O jogador está offline ou longe demais!', 'tipo': 'erro'}, room=remetente_sid)

    except Exception as e:
        print(f"🚨 [CRASH GRUPO] Ocorreu um erro no MongoDB ou Python: {str(e)}")
        emit('novaMensagemChat', {'remetente': 'Sistema', 'texto': '❌ Erro mágico no servidor.', 'tipo': 'erro'}, room=remetente_sid)

@socketio.on('marcarSussurrosLidos')
def handle_marcar_lidos(dados):
    player_sid = request.sid
    if player_sid not in jogadores_online: return
    
    nome_jogador = jogadores_online[player_sid]['nome']
    amigo = dados.get('amigo')
    
    if amigo:
        # Muda o status de "lida: False" para "lida: True"
        mensagens_offline_col.update_many(
            {"remetente": amigo, "destinatario": nome_jogador, "lida": False},
            {"$set": {"lida": True}}
        )
        
@socketio.on('aceitarGrupo')
def handle_aceitar_grupo(dados):
    party_id = dados.get('party_id')
    sid = request.sid
    jogador = jogadores_online.get(sid)
    if not jogador or not party_id: return

    sucesso, msg = adicionar_membro(party_id, str(jogador['char_id']), jogador['nome'])

    if sucesso:
        # 📸 Busca o avatar e FORÇA a URL certa
        jogador_db = users_collection.find_one({"_id": ObjectId(jogador['char_id'])})
        avatar_real = "avatar_padrao_m"
        if jogador_db:
            ac = jogador_db.get("avatar_customizado")
            if ac and ac != "padrao":
                avatar_real = ac.get("path", ac) if isinstance(ac, dict) else ac
            else:
                avatar_real = jogador_db.get("avatar", "avatar_padrao_m")
                
        nome_puro = avatar_real.split("/")[-1].replace(".png", "")
        if not nome_puro.startswith("avatar_") and "cunminicon" not in nome_puro:
            nome_puro = f"avatar_{nome_puro}"
            
        avatar_real = f"https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/avatares/{nome_puro}.png"

        grupo = obter_grupo(party_id)
        if grupo:
            for membro_id in grupo.get('membros', []):
                for sid_m, info_m in jogadores_online.items():
                    if str(info_m['char_id']) == str(membro_id):
                        if str(membro_id) != str(jogador['char_id']):
                            emit('novaMensagemChat', {'remetente': '⚔️ Party:', 'texto': f'🤝 {jogador["nome"]} entrou no grupo!', 'tipo': 'grupo', 'avatar': avatar_real}, room=sid_m)
                        else:
                            emit('novaMensagemChat', {'remetente': '⚔️ Party:', 'texto': f'✅ Você se juntou ao grupo!', 'tipo': 'grupo', 'avatar': avatar_real}, room=sid_m)
                        
                        emit('atualizarListaGrupo', grupo, room=sid_m)
    else:
        emit('novaMensagemChat', {'remetente': 'Sistema', 'texto': f'⚠️ {msg}', 'tipo': 'erro'}, room=sid)

@socketio.on('retornarGrupoMapa')
def retornar_grupo_mapa(data):
    jogador = jogadores_online.get(request.sid) or {}
    try:
        pacote = gcm.retornar_grupo_ao_mapa((data or {}).get('sala_id'), jogador.get('char_id'))
    except ValueError as erro:
        return {'success': False, 'error': str(erro)}
    gcm.emitir_para_membros(socketio, pacote['sala_id'], 'grupoRetornouMapa', pacote, jogadores_online)
    return {'success': True, 'sala': pacote}


@socketio.on('solicitarEstadoSala')
def solicitar_estado_sala(data):
    sala_id = (data or {}).get('sala_id')
    sala = gcm.obter_sala(sala_id)
    jogador = jogadores_online.get(request.sid) or {}
    if not sala or str(jogador.get('char_id')) not in list(map(str, sala.get('membros_ids', []))):
        return
    emit('estadoSalaGrupo', gcm.pacote_estado_sala(sala_id), to=request.sid)

@socketio.on('sairGrupo')
def handle_sair_grupo(dados):
    sid = request.sid
    jogador = jogadores_online.get(sid)
    if not jogador: return
    
    char_id = str(jogador['char_id'])
    sucesso, msg, membros_afetados = sair_ou_desfazer_grupo(char_id)
    
    if sucesso:
        emit('novaMensagemChat', {'remetente': 'Sistema', 'texto': msg, 'tipo': 'aviso'}, room=sid)
        emit('removerHudGrupo', {}, room=sid) # Apaga a caixinha do ecrã de quem saiu
        
        # Avisa a galera que sobrou
        for membro_id in membros_afetados:
            for sid_m, info_m in jogadores_online.items():
                if str(info_m['char_id']) == str(membro_id):
                    if "desfez" in msg:
                        emit('novaMensagemChat', {'remetente': 'Sistema', 'texto': '⚠️ O líder desfez o grupo.', 'tipo': 'erro'}, room=sid_m)
                        emit('removerHudGrupo', {}, room=sid_m)
                    else:
                        emit('novaMensagemChat', {'remetente': '⚔️ Party:', 'texto': f'🚪 {jogador["nome"]} saiu do grupo.', 'tipo': 'grupo'}, room=sid_m)
                        grupo_atualizado = obter_grupo_do_jogador(membro_id)
                        if grupo_atualizado:
                            emit('atualizarListaGrupo', grupo_atualizado, room=sid_m)
                                    
@socketio.on('enviarConviteAmizade')
def handle_convite_amizade(dados):
    remetente_sid = request.sid
    if remetente_sid not in jogadores_online: return
    
    remetente_id = jogadores_online[remetente_sid]['char_id']
    remetente_nome = jogadores_online[remetente_sid]['nome']
    alvo_id = dados.get('alvo_id')
    
    alvo_sid = None
    for sid, info in jogadores_online.items():
        if info.get('char_id') == alvo_id:
            alvo_sid = sid
            break
            
    if alvo_sid:
        emit('receberConviteAmizade', {"remetente_id": remetente_id, "remetente_nome": remetente_nome}, to=alvo_sid)
        emit('novaMensagemChat', {"remetente": "Sistema", "texto": "Convite de amizade enviado!", "tipo": "privado"}, to=remetente_sid)
    else:
        emit('novaMensagemChat', {"remetente": "Sistema", "texto": "O jogador está offline ou longe.", "tipo": "erro"}, to=remetente_sid)

@socketio.on('aceitarAmizade')
def handle_aceitar_amizade(dados):
    meu_sid = request.sid
    if meu_sid not in jogadores_online: return
    
    meu_id = jogadores_online[meu_sid]['char_id']
    meu_nome = jogadores_online[meu_sid]['nome']
    amigo_id = dados.get('amigo_id')
    amigo_nome = dados.get('amigo_nome')
    
    users_collection.update_one({"_id": ObjectId(meu_id)}, {"$addToSet": {"amigos": {"id": amigo_id, "nome": amigo_nome}}})
    users_collection.update_one({"_id": ObjectId(amigo_id)}, {"$addToSet": {"amigos": {"id": meu_id, "nome": meu_nome}}})
    
    for sid, info in jogadores_online.items():
        if info.get('char_id') == amigo_id:
            emit('novaMensagemChat', {"remetente": "Sistema", "texto": f"🤝 {meu_nome} aceitou o teu pedido de amizade!", "tipo": "privado"}, to=sid)
            break
            
    emit('novaMensagemChat', {"remetente": "Sistema", "texto": f"🤝 Agora és amigo de {amigo_nome}!", "tipo": "privado"}, to=meu_sid)

@socketio.on('pedirListaAmigos')
def handle_pedir_amigos():
    meu_sid = request.sid
    # 🛡️ Proteção: Verifica se quem pediu está na lista de online
    if meu_sid not in jogadores_online: return
    
    meu_id = jogadores_online[meu_sid]['char_id']
    jogador = users_collection.find_one({"_id": ObjectId(meu_id)})
    
    if jogador:
        amigos_salvos = jogador.get("amigos", [])
        amigos_enriquecidos = []
        
        # 🔍 Cria um "radar" instantâneo com os IDs de todo mundo que está online agora no servidor
        ids_online = {str(info.get('char_id')) for info in jogadores_online.values()}
        
        for amg in amigos_salvos:
            amigo_id = str(amg.get("id"))
            
            # 🟢 MÁGICA DO ONLINE: Checa se o ID do amigo está no radar
            ta_online = amigo_id in ids_online
            
            # 📖 MÁGICA DO AVATAR/LEVEL: Busca os dados reais do amigo no banco
            amigo_db = users_collection.find_one({"_id": ObjectId(amigo_id)})
            
            level_real = 1
            avatar_real = "avatar_padrao_m"
            
            if amigo_db:
                level_real = amigo_db.get("level", 1)
                ac = amigo_db.get("avatar_customizado")
                if ac and ac != "padrao":
                    avatar_real = ac.get("path", ac) if isinstance(ac, dict) else ac
                else:
                    avatar_real = amigo_db.get("avatar", "avatar_padrao_m")
                
            # 🔧 A CORREÇÃO NA LISTA DE AMIGOS
            nome_puro = avatar_real.split("/")[-1].replace(".png", "")
            if not nome_puro.startswith("avatar_") and "cunminicon" not in nome_puro:
                nome_puro = f"avatar_{nome_puro}"
                
            avatar_real = f"https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/avatares/{nome_puro}.png"
               
            # Monta o pacote completo para enviar ao JavaScript
            amigos_enriquecidos.append({
                "id": amigo_id,
                "nome": amg.get("nome", "Desconhecido"),
                "online": ta_online,
                "level": level_real,
                "avatar": avatar_real
            })
            
        emit('receberListaAmigos', amigos_enriquecidos, to=meu_sid)
                    
@socketio.on('entrarRegiao')
def handle_entrar_regiao(data):
    player_sid = request.sid
    char_id = data.get('char_id') 
    if not char_id: return 
    
    sids_para_remover = [sid for sid, info in jogadores_online.items() if info.get('char_id') == char_id and sid != player_sid]
    
    for old_sid in sids_para_remover:
        emit('desconectarDuplicado', {}, to=old_sid) 
        # 👇 CORREÇÃO: Usamos o .pop() com None para ignorar se a chave não existir mais
        jogadores_online.pop(old_sid, None) 
        emit('jogadorSaiu', old_sid, broadcast=True) 
    
    jogadores_online[player_sid] = {
        'id': player_sid, 'char_id': char_id,
        'nome': data.get('nome', 'Herói'), 'regiao': data.get('regiao', 'capital_eldora'),
        'x': data.get('x', 0), 'y': data.get('y', 0),
        'skin': data.get('skin', 'aventureiro_masculino') 
    }
    
    emit('jogadoresAtuais', jogadores_online, to=player_sid)
    emit('novoJogador', jogadores_online[player_sid], broadcast=True, include_self=False)
    
    if sistema_invasao_mapa.evento_ativo:
        emit('spawnMonstrosInvasao', sistema_invasao_mapa.monstros_vivos, to=player_sid)
    mobs_da_regiao = sistema_cacada.obter_mobs_regiao(data.get('regiao', 'capital_eldora'))
    emit('carregarMobsMapa', mobs_da_regiao, to=player_sid)
    
    grupo_atual = obter_grupo_do_jogador(char_id)
    if grupo_atual:
        emit('atualizarListaGrupo', grupo_atual, to=player_sid)
    
    # 🌌 FENDA DIMENSIONAL — se o jogador entrou no mapa depois do spawn,
    # envia o evento ativo para ele desenhar portal/mobs sem depender de reload.
    try:
        from modules.events import dimensional_boss_manager as dbm

        evento_dimensional = dbm.serializar_evento()

        if evento_dimensional and evento_dimensional.get("evento_id"):
            mapa_fenda = evento_dimensional.get("mapa") or evento_dimensional.get("regiao") or "mapa_desconhecido"

            emit("fendaDimensionalSurgiu", {
                "evento": evento_dimensional,
                "evento_id": evento_dimensional.get("evento_id"),
                "mapa": mapa_fenda,
                "regiao": mapa_fenda,
                "mensagem": f"🌌 Uma Fenda Dimensional está ativa em {mapa_fenda}!"
            }, to=player_sid)
        else:
            emit("fendaDimensionalEncerrada", {
                "mensagem": "Nenhuma Fenda Dimensional ativa."
            }, to=player_sid)

    except Exception as e:
        print(f"⚠️ [DIMENSIONAL SOCKET] Falha ao enviar Fenda ativa ao entrar no mapa: {e}")

    # 📜 CARREGAR HISTÓRICO NA TELA DO JOGADOR 📜
    nome_jogador = data.get('nome', 'Herói')
    
    hist_global = list(chat_collection.find({"alvo": "global"}).sort("data_envio", -1).limit(30))
    for msg in reversed(hist_global):
        emit('novaMensagemChat', {
            "remetente": msg["remetente"], 
            "texto": msg["texto"], 
            "tipo": msg.get("tipo", "global"), 
            "historico": True,
            "avatar": msg.get("avatar", "") 
        }, to=player_sid)
        
    hist_privado = list(mensagens_offline_col.find({
        "$or": [{"destinatario": nome_jogador}, {"remetente": nome_jogador}]
    }).sort("data_envio", -1).limit(30))
    
    for msg in reversed(hist_privado):
        if msg["remetente"] == nome_jogador:
            rem_format = f"Para {msg['destinatario']}"
            nome_p = msg['destinatario']
            foi_lida = True
        else:
            rem_format = msg["remetente"]
            nome_p = msg["remetente"]
            foi_lida = msg.get("lida", False) 
            
        emit('novaMensagemChat', {
            "remetente": rem_format, 
            "texto": msg["texto"], 
            "tipo": "privado", 
            "nome_puro": nome_p,
            "historico": True,
            "nao_lida": not foi_lida,
            "avatar": msg.get("avatar", "") 
        }, to=player_sid)
        
@socketio.on('enviarAcaoMapa')
def handle_acao_mapa(dados):
    player_sid = request.sid
    if player_sid not in jogadores_online: return
    
    char_id = str(jogadores_online[player_sid]['char_id'])
    
    # Manda os dois RGs! O 'char_id' pro dono reconhecer, e o 'socket_id' pros outros acharem!
    emit('acaoMapa', {
        "char_id": char_id,
        "socket_id": player_sid,
        "tipo": dados.get("tipo"),
        "valor": dados.get("valor")
    }, broadcast=True)
                    
@socketio.on('mover')
def handle_move(data):
    if request.sid in jogadores_online:
        jogadores_online[request.sid].update({'x': data.get('x'), 'y': data.get('y')})
        emit('jogadorMoveu', {'id': request.sid, 'x': data.get('x'), 'y': data.get('y')}, broadcast=True, include_self=False)

@socketio.on('atualizarVisual')
def handle_atualizar_visual(dados):
    if request.sid in jogadores_online:
        jogadores_online[request.sid]['skin'] = dados.get('skin')
        emit('visualAtualizado', {'id': request.sid, 'skin': dados.get('skin')}, broadcast=True, include_self=False)
        
@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in jogadores_online:
        del jogadores_online[request.sid]
        emit('jogadorSaiu', request.sid, broadcast=True)

@socketio.on('pedirCuraCatedral')
def curar_jogador_catedral(data):
    player_id = data.get('player_id')
    pdata = users_collection.find_one({"_id": ObjectId(player_id)})
    if pdata:
        users_collection.update_one({"_id": ObjectId(player_id)}, {"$set": {"current_hp": pdata.get('max_hp', 100)}})
        emit('pocaoUsadaSucesso', {'player_id': player_id, 'msg': 'Cura Divina!', 'cor': '#2ecc71'}, broadcast=True)

@socketio.on('sofrerDanoInvasao')
def handle_sofrer_dano_invasao(dados):
    if dados.get('player_id'):
        sistema_invasao_mapa.jogador_levou_dano_minion(dados.get('player_id'), "Herói", users_collection)

@socketio.on('atacarMonstroInvasao')
def handle_atacar_monstro(dados):
    player_id = dados.get('player_id')
    player_nome = dados.get('player_nome', 'Herói')
    monstro_id = dados.get('monstro_id')
    
    # 1. Verifica se a invasão está ativa e se o monstro existe
    monstro = sistema_invasao_mapa.monstros_vivos.get(monstro_id)
    if not monstro:
        emit('erroGeral', {'mensagem': "A criatura já foi derrotada ou fugiu!"}, to=request.sid)
        return
        
    # 2. Chama o sistema de Invasão (e não o battle_manager)
    # Passamos o 'users_collection' para ler os status
    # Passamos o 'jogadores_online' para puxar as conexões do Grupo
    sistema_invasao_mapa.processar_ataque(
        monstro_id, 
        player_id, 
        player_nome, 
        users_collection, 
        jogadores_online
    )

@socketio.on('checarStatusInvasao')
def handle_check_status():
    if sistema_invasao_mapa.evento_ativo or sistema_invasao_mapa.preparacao_ativa:
        restante = int(sistema_invasao_mapa.tempo_final_evento - time.time())
        if restante > 0:
            emit('statusInvasaoAtual', {"ativo": True, "onda": sistema_invasao_mapa.onda_atual if sistema_invasao_mapa.evento_ativo else 0, "tempo_restante": restante})

@socketio.on('usarPocaoMapa')
def handle_usar_pocao(data):
    from modules.player.inventory import consume_item
    from modules.game_data.items import ITEMS_DATA 
    from modules.player.stats import get_player_total_stats
    import asyncio
    
    player_id = data.get('player_id')
    tipo_pocao = data.get('tipo') 
    jogador = users_collection.find_one({"_id": ObjectId(player_id)})
    if not jogador: return
    
    # 👇 Calcula o limite real da classe incluindo os bônus! 👇
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    totals = loop.run_until_complete(get_player_total_stats(jogador))
    hp_max_real = int(totals.get("max_hp", 100))
    mp_max_real = int(totals.get("max_mana", 50))
    
    item_id = jogador.get("pocao_equipada_hp", "pocao_cura_leve") if tipo_pocao == 'hp' else jogador.get("pocao_equipada_mp", "pocao_energia_fraca") 
        
    if consume_item(jogador, item_id, 1):
        efeitos = ITEMS_DATA.get(item_id, {}).get("effects", {})
        if tipo_pocao == 'hp':
            cura = efeitos.get("heal", 50) 
            # ✅ Usa hp_max_real para travar a barra no número certo
            jogador['current_hp'] = min(hp_max_real, jogador.get('current_hp', 0) + cura)
            emit('pocaoUsadaSucesso', {'player_id': player_id, 'msg': f"+{cura} HP", 'cor': "#2ecc71"}, to=request.sid)
        else:
            cura = efeitos.get("mana", 100) 
            # ✅ Usa mp_max_real para travar a barra no número certo (ex: 155)
            jogador['current_mp'] = min(mp_max_real, jogador.get('current_mp', 0) + cura)
            emit('pocaoUsadaSucesso', {'player_id': player_id, 'msg': f"+{cura} MP", 'cor': "#3498db"}, to=request.sid)
            
        users_collection.replace_one({"_id": ObjectId(player_id)}, jogador)
    else:
        emit('erroGeral', {'mensagem': f"Sem poção na mochila!"}, to=request.sid)
        
@socketio.on('jogadorSofreuDanoFatalInvasao')
def handle_morte_jogador(data):
    sistema_invasao_mapa.jogador_morreu(request.sid, data.get('player_nome', 'Herói'))

@socketio.on('jogadorLevouDanoMinion')
def handle_dano_minion(data):
    sistema_invasao_mapa.jogador_levou_dano_minion(data['player_id'], data['player_nome'], users_collection)
        
@socketio.on('jogadorLevouDanoBoss')
def handle_dano_boss(data):
    sistema_invasao_mapa.jogador_levou_dano_boss(data['player_id'], data['player_nome'], users_collection)

@socketio.on('enviarConviteDuelo')
def handle_convite_duelo(dados):
    remetente_sid = request.sid
    if remetente_sid not in jogadores_online: return
    
    remetente = jogadores_online[remetente_sid]
    alvo_id = dados.get('alvo_id')
    
    # 1. Procura o alvo online
    alvo_sid = None
    for sid, info in jogadores_online.items():
        if str(info.get('char_id')) == str(alvo_id):
            alvo_sid = sid
            break
            
    if alvo_sid:
        # Verifica se alguém já está num duelo (precisaremos da flag 'em_combate' no dicionário)
        if remetente.get('em_combate') or jogadores_online[alvo_sid].get('em_combate'):
            emit('novaMensagemChat', {"remetente": "Sistema", "texto": "❌ Um dos jogadores já está em combate!", "tipo": "erro"}, to=remetente_sid)
            return

        emit('receberConviteDuelo', {
            "remetente_id": remetente['char_id'], 
            "remetente_nome": remetente['nome']
        }, to=alvo_sid)
        
        emit('novaMensagemChat', {"remetente": "Sistema", "texto": "⚔️ Desafio de duelo enviado!", "tipo": "privado"}, to=remetente_sid)
    else:
        emit('novaMensagemChat', {"remetente": "Sistema", "texto": "❌ O herói está offline ou muito longe.", "tipo": "erro"}, to=remetente_sid)

@socketio.on('recusarDuelo')
def handle_recusar_duelo(dados):
    meu_sid = request.sid
    desafiante_id = dados.get('desafiante_id')
    meu_nome = jogadores_online.get(meu_sid, {}).get('nome', 'Herói')
    
    # Avisa o desafiante
    for sid, info in jogadores_online.items():
        if str(info.get('char_id')) == str(desafiante_id):
            emit('novaMensagemChat', {"remetente": "Sistema", "texto": f"❌ {meu_nome} recusou o seu desafio.", "tipo": "erro"}, to=sid)
            break

@socketio.on('aceitarDuelo')
def handle_aceitar_duelo(dados):
    jogador_b_sid = request.sid
    if jogador_b_sid not in jogadores_online: return
    
    jogador_b_info = jogadores_online[jogador_b_sid]
    desafiante_id = dados.get('desafiante_id') # ID do Jogador A
    
    # Encontra o Jogador A (Desafiante)
    jogador_a_sid = None
    jogador_a_info = None
    for sid, info in jogadores_online.items():
        if str(info.get('char_id')) == str(desafiante_id):
            jogador_a_sid = sid
            jogador_a_info = info
            break
            
    if not jogador_a_sid:
        emit('novaMensagemChat', {"remetente": "Sistema", "texto": "❌ O desafiante fugiu ou desconectou.", "tipo": "erro"}, to=jogador_b_sid)
        return

    # 1. Trava os jogadores no mapa
    jogadores_online[jogador_a_sid]['em_combate'] = True
    jogadores_online[jogador_b_sid]['em_combate'] = True

    # 2. Busca os dados reais no banco de dados e calcula os status
    player_a_db = users_collection.find_one({"_id": ObjectId(jogador_a_info['char_id'])})
    player_b_db = users_collection.find_one({"_id": ObjectId(jogador_b_info['char_id'])})

    stats_a = get_combat_stats_sync(player_a_db)
    stats_b = get_combat_stats_sync(player_b_db)

    player_a_db = aplicar_combat_stats_no_player(player_a_db, stats_a)
    player_b_db = aplicar_combat_stats_no_player(player_b_db, stats_b)

    # Define HP/MP iniciais do duelo
    hp_a = int(stats_a.get('current_hp', stats_a.get('max_hp', 1)))
    hp_b = int(stats_b.get('current_hp', stats_b.get('max_hp', 1)))

    # 3. Cria a sessão do Duelo
    duelo_id = f"duelo_{jogador_a_info['char_id']}_{jogador_b_info['char_id']}"
    
    duelos_ativos[duelo_id] = {
        "id": duelo_id,
        "jogador_a": {"sid": jogador_a_sid, "db": player_a_db, "stats": stats_a, "hp": hp_a, "mp": stats_a.get("current_mp", stats_a.get("max_mana", 50))},
        "jogador_b": {"sid": jogador_b_sid, "db": player_b_db, "stats": stats_b, "hp": hp_b, "mp": stats_b.get("current_mp", stats_b.get("max_mana", 50))},
        "turno_de": jogador_a_sid # O desafiante começa atacando
    }

    # 4. Formata o pacote visual para o Frontend (combate.js)
    estado_para_a = {
        "duelo_id": duelo_id,
        "regiao": jogador_a_info.get('regiao', 'capital_eldora'), # 👈 AQUI: Pega o mapa exato onde vocês estão!
        "oponente_nome": jogador_b_info['nome'],
        "oponente_skin": jogador_b_info['skin'],
        "oponente_level": player_b_db.get('level', 1),
        "oponente_hp": hp_b,
        "oponente_max_hp": stats_b.get('max_hp', 1),
        "meu_level": player_a_db.get('level', 1),
        "meu_hp": hp_a,
        "meu_max_hp": stats_a.get('max_hp', 1),
        "meu_mp": stats_a.get("current_mp", stats_a.get("max_mana", 50)),
        "meu_max_mp": stats_a.get('max_mana', 50),
        "minha_vez": True 
    }
    
    estado_para_b = {
        "duelo_id": duelo_id,
        "regiao": jogador_b_info.get('regiao', 'capital_eldora'), # 👈 AQUI TAMBÉM!
        "oponente_nome": jogador_a_info['nome'],
        "oponente_skin": jogador_a_info['skin'],
        "oponente_level": player_a_db.get('level', 1),
        "oponente_hp": hp_a,
        "oponente_max_hp": stats_a.get('max_hp', 1),
        "meu_level": player_b_db.get('level', 1),
        "meu_hp": hp_b,
        "meu_max_hp": stats_b.get('max_hp', 1),
        "meu_mp": stats_b.get("current_mp", stats_b.get("max_mana", 50)),
        "meu_max_mp": stats_b.get('max_mana', 50),
        "minha_vez": False
    }

    emit('iniciarArenaPvP', estado_para_a, to=jogador_a_sid)
    emit('iniciarArenaPvP', estado_para_b, to=jogador_b_sid)

# 👇 Adicione isso junto aos outros ouvintes do Socket.IO no main.py 👇
      
def buscar_jogador(uid):
    query = []
    try:
        query.append({"_id": ObjectId(uid)})
    except (errors.InvalidId, TypeError):
        pass

    if str(uid).isdigit(): query.append({"telegram_id": int(uid)})
    query.append({"telegram_id": str(uid)})
    query.append({"username": str(uid)})
    return db.users.find_one({"$or": query})    

def notificar_dano_party(char_id, hp_atual, max_hp, mp_atual, max_mp):
    grupo = parties_collection.find_one({"membros": str(char_id)})
    if grupo:
        hp_pct = (hp_atual / max_hp) * 100 if max_hp > 0 else 0
        mp_pct = (mp_atual / max_mp) * 100 if max_mp > 0 else 0
        
        for membro_id in grupo.get('membros', []):
            for sid, info in jogadores_online.items():
                if str(info['char_id']) == str(membro_id):
                    socketio.emit('atualizarStatusParty', {
                        'char_id': str(char_id), 'hp_pct': hp_pct, 'mp_pct': mp_pct
                    }, room=sid)

# ==============================================================================
# ⛺ ROTA DA LOJA DO MERCADOR
# ==============================================================================
@app.route('/api/loja/comprar', methods=['POST'])
def loja_comprar():
    try:
        dados = request.json
        user_id = dados.get('user_id')
        item_id = dados.get('item_id')
        preco = int(dados.get('preco', 0))

        # 1. Busca o jogador no banco de dados pelo ID
        player = users_collection.find_one({"_id": ObjectId(user_id)})
        if not player:
            return jsonify({"erro": "Jogador não encontrado no banco de dados!"})

        # 2. Verifica o bolso do cliente (Ouro)
        ouro_atual = player.get("gold", 0)
        if ouro_atual < preco:
            return jsonify({"erro": f"Ouro insuficiente! Você tem {ouro_atual}💰 e precisa de {preco}💰."})

        # 3. Calcula o troco e prepara a mochila
        novo_ouro = ouro_atual - preco
        inventario = player.get("inventory", [])
        inventario.append(item_id) # Coloca a poção na lista

        # 4. Salva a transação no MongoDB!
        users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"gold": novo_ouro, "inventory": inventario}}
        )

        return jsonify({"sucesso": True, "novo_ouro": novo_ouro})

    except Exception as e:
        return jsonify({"erro": f"Erro na loja: {str(e)}"})

async def telegram_error_handler(update, context):
    erro = context.error

    # Falhas temporárias de conexão com o Telegram.
    # O polling já tenta reconectar automaticamente.
    if isinstance(erro, NetworkError):
        return

    # Erros reais do bot continuam aparecendo.
    print(f"🚨 Erro inesperado no Bot Telegram: {erro}")

def run_bot():
    """Roda o bot do Telegram num loop isolado."""

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while True:
        try:
            application = (
                Application
                .builder()
                .token(TELEGRAM_TOKEN)
                .build()
            )

            application.add_handler(
                CommandHandler("start", start_command)
            )

            application.add_error_handler(
                telegram_error_handler
            )

            print(
                "🤖 Corvos mensageiros a postos! "
                "Bot do Telegram escutando /start..."
            )

            application.run_polling(
                drop_pending_updates=True,
                close_loop=False,
                bootstrap_retries=5,
                stop_signals=None
            )

            # Se terminou normalmente, não reinicia.
            break

        except (TimedOut, NetworkError):
            print(
                "⚠️ Telegram indisponível temporariamente. "
                "Nova tentativa em 10 segundos..."
            )
            time.sleep(10)

        except Exception as e:
            print(
                f"🚨 Erro ao iniciar Bot Telegram: {e}"
            )
            time.sleep(10)
# ==============================================================================
# ⚔️ SISTEMA DE PVP (DUELOS 1V1)
# ==============================================================================
duelos_ativos = {} # Guarda o estado atual de cada duelo rolando no mapa

@socketio.on('enviarAcaoPvP')
def handle_acao_pvp(dados):
    sid = request.sid
    duelo_id = dados.get('duelo_id')
    acao = dados.get('acao')
    skill_id = dados.get('skill_id')

    if duelo_id not in duelos_ativos:
        return

    duelo = duelos_ativos[duelo_id]
    if duelo['turno_de'] != sid:
        return

    is_jogador_a = (sid == duelo['jogador_a']['sid'])
    atacante = duelo['jogador_a'] if is_jogador_a else duelo['jogador_b']
    alvo = duelo['jogador_b'] if is_jogador_a else duelo['jogador_a']

    # Usa as funções que já foram importadas no topo!
    atacante['db'], msgs_cd = iniciar_turno(atacante['db'])
    
    log_turno = []
    # Injeta avisos como "Corte Perfurante está pronto!" apenas como texto visual
    for msg in msgs_cd:
        log_turno.append({
            "autor_sid": sid, 
            "texto": msg, 
            "dano": 0, 
            "tipo_skill": "info", # 👈 Mudei de 'suporte' para 'info' para não disparar animação!
            "anim_effect": ""
        })

    vencedor_sid = None
    novo_hp = alvo['hp']

    if acao == 'render_se':
        log_turno.append({"autor_sid": sid, "texto": f"🏳️ {atacante['db'].get('nome', 'O Herói')} se rendeu!", "dano": 0})
        alvo['hp'] = 0
        vencedor_sid = alvo['sid']

    elif acao == 'item':
        item_static = CONSUMABLES_DATA.get(skill_id, {})
        efeitos = item_static.get('effects', {})
        cura_hp = int(efeitos.get('heal', 0))
        cura_mp = int(efeitos.get('mana', efeitos.get('mp', 0)))

        atacante['hp'] = min(atacante['stats'].get('max_hp', 100), atacante['hp'] + cura_hp)
        atacante['mp'] = min(atacante['stats'].get('max_mana', 50), atacante['mp'] + cura_mp)
        
        nome_item = item_static.get('display_name', 'Poção')
        log_turno.append({"autor_sid": sid, "texto": f"🧪 {atacante['db'].get('nome', 'O Herói')} usou {nome_item}!", "dano": 0})
        novo_hp = atacante['hp']

    else:
        # AQUI O ASYNCIO VOLTA, MAS SEM IMPORTS INTERNOS A ATRAPALHAR!
        try: loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        resultado = loop.run_until_complete(processar_acao_combate(
            attacker_pdata=atacante['db'], attacker_stats=atacante['stats'], target_stats=alvo['stats'],
            skill_id=skill_id if acao == 'magia' else None,
            attacker_current_hp=atacante['hp'], attacker_current_mp=atacante['mp']
        ))

        dano_causado = resultado.get('total_damage', 0)
        alvo['hp'] = max(0, alvo['hp'] - dano_causado)
        atacante['mp'] = resultado.get('attacker_mp_left', atacante['mp'])
        novo_hp = alvo['hp']

        for msg in resultado.get('log_messages', []):
            log_turno.append({
                "autor_sid": sid, "texto": msg, "dano": dano_causado if msg == resultado['log_messages'][-1] else 0,
                "anim_effect": resultado.get('anim_effect', ''), "tipo_skill": resultado.get('tipo_skill', '')
            })

    if alvo['hp'] <= 0:
        vencedor_sid = atacante['sid']

    proximo_turno_sid = alvo['sid'] if not vencedor_sid else None
    if not vencedor_sid:
        duelo['turno_de'] = proximo_turno_sid

    pacote_animacao = {
        "log": log_turno,
        "vencedor_sid": vencedor_sid,
        "novo_hp": novo_hp,
        "atacante_sid": sid, 
        "novo_mp": atacante['mp'], 
        "cooldowns": atacante['db'].get('cooldowns', {}), 
        "proximo_turno_sid": proximo_turno_sid
    }

    emit('animarTurnoPvP', pacote_animacao, to=duelo['jogador_a']['sid'])
    emit('animarTurnoPvP', pacote_animacao, to=duelo['jogador_b']['sid'])

    if vencedor_sid:
        if duelo['jogador_a']['sid'] in jogadores_online: jogadores_online[duelo['jogador_a']['sid']]['em_combate'] = False
        if duelo['jogador_b']['sid'] in jogadores_online: jogadores_online[duelo['jogador_b']['sid']]['em_combate'] = False
        del duelos_ativos[duelo_id]

# 👇 A ROTA QUE ESTAVA EM FALTA PARA A RAID! 👇
@socketio.on('enviarAcaoRaid')
def handle_acao_raid(dados):
    sid = request.sid
    raid_id = dados.get('raid_id')
    acao = dados.get('acao')
    alvo_id = dados.get('alvo_id')
    skill_id = dados.get('skill_id')

    from modules.combat.combat_raid_engine import processar_turno_raid, RAIDS_ATIVAS

    raid_antes = RAIDS_ATIVAS.get(raid_id)

    pacote = processar_turno_raid(
        raid_id,
        sid,
        acao,
        alvo_id,
        skill_id=skill_id
    )

    if not pacote:
        emit('erroGeral', {'mensagem': 'Ação inválida ou turno incorreto na raid.'}, to=sid)
        return

    raid = RAIDS_ATIVAS.get(raid_id) or raid_antes
    if not raid:
        return

    for jogador in raid.get('jogadores', {}).values():
        sid_destino = jogador.get('sid')
        if sid_destino:
            emit('animarTurnoRaid', pacote, to=sid_destino)

    if pacote.get('raid_encerrada'):
        try:
            metadata = raid.get('metadata', {}) or {}
            if metadata.get('tipo_evento') == 'invasao_reino':
                sistema_invasao_mapa.registrar_resultado_raid(raid, pacote)

        except Exception:
            import traceback
            print(
                "🚨 Erro ao registrar resultado da raid da invasão:\n"
                + traceback.format_exc()
            )

        for jogador in raid.get('jogadores', {}).values():
            sid_jogador = jogador.get('sid')
            if sid_jogador in jogadores_online:
                jogadores_online[sid_jogador]['em_combate'] = False

        RAIDS_ATIVAS.pop(raid_id, None)

def loop_agendamento_invasao():
    """Fica em segundo plano checando o relógio para rodar a invasão sozinho"""
    print("⏰ Cronômetro de Invasões ativado! Monitorando os horários do Reino...")
    
    # Lista dos horários exatos em que a invasão deve começar (Formato HH:MM)
    HORARIOS_ALVO = ["08:00", "14:00", "19:00", "23:00"]
    
    while True:
        try:
            agora = datetime.now()
            hora_minuto_atual = agora.strftime("%H:%M")
            
            # Se o relógio bater com um dos horários da lista, solta os monstros!
            if hora_minuto_atual in HORARIOS_ALVO:
                print(f"⚔️ CRON: Horário de Invasão atingido ({hora_minuto_atual})! Iniciando evento...")
                
                # Dispara a invasão passando a lista global de quem está online
                sistema_invasao_mapa.iniciar_invasao(jogadores_online)
                
                # Dorme por 61 segundos para evitar que o loop rode duas vezes no mesmo minuto
                time.sleep(61)
                
        except Exception as e:
            print(f"🚨 Erro no agendador automático de invasão: {str(e)}")
            
        # Checa o relógio a cada 30 segundos para não pesar o processador
        time.sleep(30)

# ==============================================================================
# 5. EXECUÇÃO PRINCIPAL (O INTERRUPTOR ÚNICO)
# ==============================================================================
if __name__ == "__main__":
    # 1. Inicia o Bot do Telegram
    bot_thread = Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # 👇 2. NOVO: Inicia o Relógio Automático de Invasões 👇
    cron_invasao_thread = Thread(target=loop_agendamento_invasao, daemon=True)
    cron_invasao_thread.start()
    
    print("🚀 Servidor Web de Eldora rodando em http://localhost:5000")
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        allow_unsafe_werkzeug=True
    )