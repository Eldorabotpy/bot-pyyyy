# rotas/character.py
import re 
import asyncio
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Blueprint, jsonify, request
from bson import ObjectId
from modules.player.core import users_collection
from modules.game_data.skills import SKILL_DATA
from modules.game_data.skins import get_skin_avatar
from modules.game_data.cosmetics import CATALOGO_AVATARES, CATALOGO_BANNERS, COSMETICOS_VIP
from modules.player.core import users_collection
from modules.player.account_lock import check_account_lock

character_bp = Blueprint('character_bp', __name__)

# 1. ROTA DE LOGIN
# ==========================================
@character_bp.route('/api/portal/login', methods=['POST'])
def api_portal_login():
    try:
        dados = request.json
        username = dados.get('username')
        password = dados.get('password')
        tg_id = dados.get('tg_id') # Opcional, do Telegram

        if not username or not password:
            return jsonify({"sucesso": False, "erro": "Preencha o usuário e a senha."}), 400

        # Busca o jogador no banco ignorando maiúsculas/minúsculas
        jogador = users_collection.find_one({"character_name": re.compile(f"^{username}$", re.IGNORECASE)})
        
        if not jogador:
            return jsonify({"sucesso": False, "erro": "Este herói não existe nos registros."}), 404

        # Verifica se a senha bate com o Hash salvo
        senha_salva = jogador.get("password_hash")
        if not senha_salva or not check_password_hash(senha_salva, password):
            return jsonify({"sucesso": False, "erro": "Senha incorreta. Os deuses negaram seu acesso."}), 401

        # 🛡️ VERIFICAÇÃO DE BANIMENTO / CONTA TRANCADA
        ta_bloqueado, msg_bloqueio = check_account_lock(jogador)
        if ta_bloqueado:
            # Retorna o motivo exato do banimento que está no account_lock.py
            return jsonify({"sucesso": False, "erro": msg_bloqueio}), 403

        # (Opcional) Atualiza o ID do Telegram caso o jogador tenha logado por um aparelho novo
        if tg_id and jogador.get("telegram_id") != tg_id:
            users_collection.update_one({"_id": jogador["_id"]}, {"$set": {"telegram_id": tg_id}})

        # Login aprovado! Devolve os dados essenciais para o frontend salvar
        return jsonify({
            "sucesso": True,
            "jogador_id": str(jogador["_id"]),
            "jogador_nome": jogador.get("character_name"),
            "genero": jogador.get("gender", "masculino")
        })

    except Exception as e:
        print(f"Erro no Login: {e}")
        return jsonify({"sucesso": False, "erro": "Erro interno do servidor mágico."}), 500

# ==========================================
# 2. ROTA DE CRIAR CONTA / PERSONAGEM
# ==========================================
@character_bp.route('/api/portal/criar_personagem', methods=['POST'])
def api_portal_criar():
    try:
        dados = request.json
        nome = dados.get('nome')
        senha = dados.get('senha')
        genero = dados.get('genero', 'masculino')
        tg_id = dados.get('tg_id')

        if not nome or not senha or len(senha) < 6:
            return jsonify({"sucesso": False, "erro": "Nome inválido ou senha muito curta (mín. 6 caracteres)."}), 400

        # Verifica se o nome já está em uso
        existe = users_collection.find_one({"character_name": re.compile(f"^{nome}$", re.IGNORECASE)})
        if existe:
            return jsonify({"sucesso": False, "erro": "Este nome já foi clamado por outro herói!"}), 409

        # Criptografa a senha para salvar com segurança
        senha_criptografada = generate_password_hash(senha)

        # Monta a ficha base do novo jogador
        novo_jogador = {
            "character_name": nome,
            "password_hash": senha_criptografada, # 👈 Salva a senha embaralhada
            "gender": genero,
            "telegram_id": tg_id,
            "class": "aprendiz",
            "level": 1,
            "xp": 0,
            "gold": 0,
            "gems": 0,
            "current_hp": 100,
            "max_hp": 100,
            "current_mp": 50,
            "max_mp": 50,
            "energy": 20,
            "current_location": "capital_eldora",
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        users_collection.insert_one(novo_jogador)
        return jsonify({"sucesso": True})

    except Exception as e:
        print(f"Erro ao forjar herói: {e}")
        return jsonify({"sucesso": False, "erro": "As forjas falharam. Tente novamente."}), 500
        
@character_bp.route('/api/meus_personagens/<telegram_id>')
def listar_personagens(telegram_id):
    try:
        if not telegram_id or telegram_id in ["undefined", "null", ""]:
            return jsonify([])
        
        cursor = users_collection.find({"telegram_id": int(telegram_id)})
        personagens = []
        for p in cursor:
            personagens.append({
                "id": str(p["_id"]),
                "nome": p.get("character_name"),
                "classe": str(p.get("class")).capitalize(),
                "level": p.get("level", 1),
                "gender": p.get("gender", "masculino")
            })
        return jsonify(personagens)
    except Exception as e:
        print(f"Erro ao listar personagens: {e}")
        return jsonify([])

@character_bp.route('/api/perfil/atualizar', methods=['POST'])
def atualizar_perfil_custom():
    try:
        dados = request.json
        user_id = dados.get("user_id")
        if not user_id:
            return jsonify({"sucesso": False, "erro": "ID do herói não fornecido"}), 400

        id_avatar = dados.get("avatar")
        id_banner = dados.get("banner")
        id_skin = dados.get("skin")
        
        jogador = users_collection.find_one({"_id": ObjectId(user_id)})
        if not jogador:
            return jsonify({"sucesso": False, "erro": "Herói não encontrado"}), 404

        tem_passe = jogador.get("premium_tier", "free") != "free" 
        if not tem_passe:
            if (id_avatar in COSMETICOS_VIP) or (id_banner in COSMETICOS_VIP):
                return jsonify({"sucesso": False, "erro": "Este item é exclusivo do Passe VIP! 👑"}), 403

        atualizacao = {}
        if id_avatar: atualizacao["avatar_customizado"] = id_avatar
        if id_banner: atualizacao["banner_customizado"] = id_banner
        if id_skin:   atualizacao["equipped_skin"] = id_skin
        
        if atualizacao:
            users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": atualizacao})
            
        return jsonify({"sucesso": True})
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500

# ✨ CORREÇÃO: Transformado em rota e adicionado cálculo de XP Necessário
@character_bp.route('/api/personagem/<personagem_id>')
def obter_personagem_info(personagem_id):
    try:
        pdata = users_collection.find_one({"_id": ObjectId(personagem_id)})
        if not pdata:
            return jsonify({"erro": "Herói não encontrado no Reino"}), 404
            
        skin_id = pdata.get("equipped_skin") 
        genero = pdata.get("gender", "masculino") 
        unlocked = pdata.get("unlocked_skins", []) 

        # Mapeamento para sprites ortogonais do Tiled
        MAPA_CLASSES_BASE = {
            'aventureiro': 'aventureiro', 'aprendiz': 'aventureiro',
            'guerreiro': 'guerreiro', 'cavaleiro': 'guerreiro', 'mago': 'mago',
            'assassino': 'assassino', 'samurai': 'samurai', 'curandeiro': 'curandeiro'
        }

        classe_atual = pdata.get("class", "aprendiz").lower()
        classe_base = MAPA_CLASSES_BASE.get(classe_atual, "aventureiro")
        
        # 🛠️ AUTO-CORREÇÃO DE CONTA PRESA NO LIMBO
        q6 = pdata.get("quests", {}).get("q6_selene_grimorio", {})
        skills_certas = pdata.get("skills", {})
        
        # 👇 ADICIONE ESTAS DUAS LINHAS PARA CONVERTER A LISTA EM DICIONÁRIO 👇
        if isinstance(skills_certas, list):
            skills_certas = {}
        
        if q6.get("status") == "resgatada" and not skills_certas:
            SKILL_INICIAL = {
                "guerreiro": "guerreiro_corte_perfurante",
                "mago": "mago_bola_de_fogo",
                "assassino": "assassino_ataque_furtivo",
                "cacador": "cacador_flecha_precisa",
                "curandeiro": "curandeiro_chama_sagrada",
                "berserker": "berserker_golpe_selvagem",
                "samurai": "samurai_corte_iaijutsu",
                "monge": "monge_rajada_de_punhos",
                "bardo": "bardo_nota_cortante"
            }
            id_certo = SKILL_INICIAL.get(classe_atual, "ataque_basico")
            skills_certas[id_certo] = {"unlocked": True, "rarity": "comum"}
            
            # Injeta a magia certa na conta e salva
            users_collection.update_one({"_id": ObjectId(personagem_id)}, {"$set": {"skills": skills_certas}})

        # Define o nome do sprite para o Phaser
        base_skin = skin_id if skin_id else classe_base
        nome_sprite_mapa = f"{base_skin}_{genero.lower()}"
        letra_gen = genero.lower()[0] if genero else "m"

        # ✨ CÁLCULO DO XP NECESSÁRIO
        from modules.game_data.xp import _xp_formula
        xp_necessario = _xp_formula(pdata.get("level", 1))

        # 👇 A MÁGICA ENTRA AQUI: Chama o motor para ler os bônus reais do Mago (155) 👇
        import asyncio
        from modules.player.stats import get_player_total_stats
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        totals = loop.run_until_complete(get_player_total_stats(pdata))
        
        hp_max_real = int(totals.get("max_hp", pdata.get("max_hp", 100)))
        mp_max_real = int(totals.get("max_mana", pdata.get("max_mana", 50)))

        return jsonify({
            "nome": pdata.get("character_name", "Herói"),
            "classe": pdata.get("class", "aprendiz"),
            "level": pdata.get("level", 1),
            "hp": min(pdata.get("current_hp", hp_max_real), hp_max_real),
            "max_hp": hp_max_real, # ✅ Agora envia 155 pro Mapa
            "mp": min(pdata.get("current_mp", mp_max_real), mp_max_real),
            "max_mp": mp_max_real, # ✅ Agora envia 155 pro Mapa
            "ouro": pdata.get("gold", 0),
            "gems": pdata.get("gems", 0), 
            "xp": pdata.get("xp", 0),
            "xp_max": xp_necessario,        
            "xp_next_level": xp_necessario, 
            "avatar": f"https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/avatares/avatar_padrao_{letra_gen}.png",
            "avatar_customizado": pdata.get("avatar_customizado", "padrao"),
            "banner_customizado": pdata.get("banner_customizado", "padrao"),
            "equipped_skin": skin_id, 
            "unlocked_skins": unlocked, 
            "skin_mapa": nome_sprite_mapa,
            "database_skills": SKILL_DATA,
            "skills_desbloqueadas": skills_certas,
            "skills_equipadas": pdata.get("equipped_skills", {}),
            "pocao_equipada_hp": pdata.get("pocao_equipada_hp"),
            "pocao_equipada_mp": pdata.get("pocao_equipada_mp"),
            "profession": pdata.get("profession"),
            "learned_professions": pdata.get("learned_professions", {}),
            "equipment_tools": pdata.get("equipment_tools", {}),
            "inventory": pdata.get("inventory", {})
        })
    except Exception as e:
        import traceback
        print(f"Erro ao buscar personagem: {traceback.format_exc()}")
        return jsonify({"erro": str(e)}), 500
    
# ✨ CORREÇÃO: Registrado como rota POST para equipar magias
@character_bp.route('/api/equipar_skill', methods=['POST'])
def api_equipar_skill():
    from bson import ObjectId
    from flask import request, jsonify
    from modules.player.core import users_collection

    try:
        dados = request.json
        user_id = dados.get("user_id")
        skill_id = dados.get("skill_id") # Pode vir vazio se for para desequipar
        slot = dados.get("slot") # O JavaScript envia o número do slot (ex: 1, 2, 3)

        if not user_id or not slot:
            return jsonify({"sucesso": False, "erro": "Dados incompletos enviados ao servidor."}), 400

        jogador = users_collection.find_one({"_id": ObjectId(user_id)})
        if not jogador:
            return jsonify({"sucesso": False, "erro": "Herói não encontrado."})

        # 🛠️ CORREÇÃO: Garante que equipped_skills seja sempre um Dicionário {}
        equipadas = jogador.get("equipped_skills", {})
        if isinstance(equipadas, list):
            equipadas = {} 

        slot_key = f"slot_{slot}"

        # LÓGICA DE DESEQUIPAR (Se skill_id vier vazio)
        if not skill_id:
            if slot_key in equipadas:
                del equipadas[slot_key]
        
        # LÓGICA DE EQUIPAR
        else:
            skills_possuidas = jogador.get("skills", {})
            
            # Verifica se o jogador realmente tem a magia (segurança)
            if skill_id not in skills_possuidas:
                return jsonify({"sucesso": False, "erro": "Você não possui o conhecimento desta magia."})

            # Se a magia já estiver equipada em OUTRO slot, tira de lá primeiro
            for k, v in list(equipadas.items()):
                if v == skill_id:
                    del equipadas[k]
            
            # Equipa a magia no slot desejado
            equipadas[slot_key] = skill_id

        # Salva o novo Loadout no banco de dados
        users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"equipped_skills": equipadas}}
        )

        return jsonify({"sucesso": True})

    except Exception as e:
        import traceback
        print(f"Erro Crítico em /api/equipar_skill: {traceback.format_exc()}")
        return jsonify({"sucesso": False, "erro": str(e)}), 500
    
@character_bp.route('/api/npc/missao/grimorio', methods=['POST'])
def api_missao_grimorio():
    from bson import ObjectId
    from flask import request, jsonify
    from modules.player.core import users_collection

    try:
        dados = request.json
        user_id = dados.get("user_id")

        jogador = users_collection.find_one({"_id": ObjectId(user_id)})
        if not jogador:
            return jsonify({"sucesso": False, "erro": "Jogador não encontrado."})

        # Trava de Segurança: Nível
        if jogador.get("level", 1) < 17:
            return jsonify({"sucesso": False, "erro": "Sua alma ainda é fraca. Volte no Nível 17."})

        inv = jogador.get("inventory", {})

        def pegar_qtd(item_id):
            item = inv.get(item_id)
            if item is None: return 0 # Blindagem anti-erro
            if isinstance(item, dict): return int(item.get("quantity", 0))
            return int(item)

        # ✨ CORREÇÃO CRÍTICA: ID igual ao do seu banco de dados (JSON)
        qtd_ecto = pegar_qtd("ectoplasma")
        qtd_couro = pegar_qtd("couro_de_lobo_alfa") 

        if qtd_ecto < 15 or qtd_couro < 30:
            return jsonify({"sucesso": False, "erro": f"Faltam reagentes! Você possui {qtd_ecto}/15 Ectoplasmas e {qtd_couro}/30 Couros de Lobo Alfa."})

        # Consome os itens com segurança
        def reduzir_qtd(item_id, valor):
            item_atual = inv.get(item_id)
            if item_atual is None: return
            if isinstance(item_atual, dict):
                qtd_num = int(item_atual.get("quantity", 0))
                if qtd_num <= valor: del inv[item_id]
                else: inv[item_id]["quantity"] = qtd_num - valor
            else:
                if int(item_atual) <= valor: del inv[item_id]
                else: inv[item_id] -= valor

        reduzir_qtd("ectoplasma", 15)
        reduzir_qtd("couro_de_lobo_alfa", 30)

        # IDs EXATOS do seu skills.py
        SKILL_INICIAL = {
            "guerreiro": "guerreiro_corte_perfurante",
            "mago": "mago_bola_de_fogo",
            "assassino": "assassino_ataque_furtivo",
            "cacador": "cacador_flecha_precisa",
            "curandeiro": "curandeiro_chama_sagrada",
            "berserker": "berserker_golpe_selvagem",
            "samurai": "samurai_corte_iaijutsu",
            "monge": "monge_rajada_de_punhos",
            "bardo": "bardo_nota_cortante"
        }

        classe_atual = jogador.get("class", "aventureiro").lower()
        id_skill_ganha = SKILL_INICIAL.get(classe_atual, "ataque_basico")

        # 🛠️ CORREÇÃO DO MONGODB: Transforma a lista vazia [] em dicionário {}
        skills_atuais = jogador.get("skills", {})
        if isinstance(skills_atuais, list):
            skills_atuais = {} # Converte para o formato certo
            
        skills_atuais[id_skill_ganha] = {"unlocked": True, "rarity": "comum"}

        # Injeta a habilidade no Grimório e conclui a quest
        users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "inventory": inv,
                    "skills": skills_atuais, # 👈 Agora enviamos a gaveta completa consertada
                    "quests.q6_selene_grimorio.status": "resgatada"
                }
            }
        )

        return jsonify({"sucesso": True, "skill_ganha": id_skill_ganha})

    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)})
          
@character_bp.route('/api/save_position', methods=['POST'])
def save_position():
    try:
        data = request.json
        uid = data.get('user_id')
        pos = data.get('position')
        
        if uid and pos:
            users_collection.update_one(
                {"_id": ObjectId(uid)},
                {"$set": {"last_pos": pos}}
            )
            return jsonify({"sucesso": True})
        return jsonify({"sucesso": False, "erro": "Dados de posição ausentes"}), 400
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500
    
@character_bp.route('/api/combate/acao', methods=['POST'])
def acao_combate_migrada():
    import asyncio
    from flask import current_app
    from modules.player.stats import processar_turno_combate
    from modules.game_data.monsters import MONSTERS_DATA
    from modules.combat.combat_engine import processar_acao_combate
    from modules.dungeon_event_service import (
        finalizar_combate_mimico,
        is_dungeon_event_mob,
    )

    try:
        data = request.json
        user_id = data.get('user_id')
        acao = data.get('acao')
        spawn_id = data.get('spawn_id')
        skill_id = data.get('skill_id')

        if acao == 'fugir':

            from modules.player.core import users_collection
            from bson import ObjectId

            # Limpa trava normal de caça.
            users_collection.update_one(
                {
                    '_id':
                        ObjectId(user_id)
                },
                {
                    '$unset': {
                        'rune_hunt_active':
                            ''
                    }
                }
            )

            # ==========================================
            # 👹 VERIFICA SE É MÍMICO DE DUNGEON
            # ==========================================

            sistema_cacada = (
                current_app.config.get(
                    'SISTEMA_CACADA'
                )
            )

            mob_evento = None

            if sistema_cacada:

                mobs_vivos = getattr(
                    sistema_cacada,
                    "mobs_vivos",
                    {}
                )

                for (
                    _regiao,
                    mobs
                ) in mobs_vivos.items():

                    mob = (
                        mobs
                        or {}
                    ).get(
                        str(
                            spawn_id
                        )
                    )

                    if (
                        mob
                        and
                        is_dungeon_event_mob(
                            mob
                        )
                    ):

                        mob_evento = mob
                        break

            # ==========================================
            # 🧹 LIMPA O ESTADO DO MÍMICO
            # ==========================================

            if mob_evento:

                finalizar_combate_mimico(

                    user_id=
                        str(
                            user_id
                        ),

                    spawn_id=
                        str(
                            spawn_id
                        ),

                    sistema_cacada=
                        sistema_cacada,

                    resultado=
                        "fuga",

                )

            return jsonify({

                "fugiu":
                    True,

                "evento_dungeon":
                    bool(
                        mob_evento
                    ),

                "log": [

                    {
                        "autor":
                            "player",

                        "texto":
                            "Fugiste da batalha!"
                    }

                ]

            })

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # 👈 2. Puxa o motor da memória de forma 100% segura!
        sistema_cacada = current_app.config.get('SISTEMA_CACADA')

        # O resto do código continua igual...
        resultado = loop.run_until_complete(processar_turno_combate(
            user_id=user_id,
            acao=acao,
            spawn_id=spawn_id,
            skill_id=skill_id,
            sistema_cacada=sistema_cacada,
            MONSTERS_DATA=MONSTERS_DATA,
            processar_acao_combate=processar_acao_combate,
            sala_id=data.get("sala_id"),
            modo_grupo=data.get("modo_grupo", False),
            target_id=data.get("target_id")
        ))

        return jsonify(resultado)

    except Exception as e:
        import traceback
        print(f"Erro no combate modular: {traceback.format_exc()}")
        return jsonify({"erro": "Erro interno no servidor de combate"}), 500
    
# ==========================================
# 📜 ROTA: APRENDER OU TROCAR DE PROFISSÃO
# ==========================================
@character_bp.route('/api/personagem/aprender_profissao', methods=['POST'])
def aprender_profissao():
    from flask import request, jsonify
    from bson import ObjectId
    from modules.player.core import users_collection
    from modules.game_data.professions import PROFESSIONS_DATA

    try:
        data = request.json
        user_id = data.get('user_id')
        prof_key = data.get('profession_key')
        
        if not user_id or not prof_key:
            return jsonify({"success": False, "error": "Faltam componentes no contrato da guilda."}), 400
            
        prof_info = PROFESSIONS_DATA.get(prof_key)
        if not prof_info:
            return jsonify({"success": False, "error": "Este ofício é desconhecido."}), 404
            
        player = users_collection.find_one({"_id": ObjectId(user_id)})
        if not player:
            return jsonify({"success": False, "error": "Herói não encontrado."}), 404
            
        # ==========================================
        # ⚖️ O TRATADO DAS GUILDAS & CONSUMO DO SELO
        # ==========================================
        prof_atual = player.get("profession")
        my_inv = player.get("inventory", {}) # Carregamos a mochila para manipular
        
        if prof_atual:
            cat_atual = prof_atual.get("category")
            nova_cat = prof_info.get("category")
            
            # Bloqueia se tentar pegar duas de Coleta ou duas de Produção seguidas
            if cat_atual == nova_cat:
                tipo_nome = "Coleta" if cat_atual == "gathering" else "Produção"
                return jsonify({
                    "success": False, 
                    "error": f"As Guildas proíbem possuir dois ofícios de {tipo_nome}. Escolha o outro lado da moeda!"
                }), 400
                
            # Verifica se tem o item 'selo_de_maestria'
            item_selo = my_inv.get("selo_de_maestria", {})
            qtd_selo = item_selo.get("quantity", 0) if isinstance(item_selo, dict) else int(item_selo or 0)
            
            if qtd_selo < 1:
                return jsonify({
                    "success": False, 
                    "error": "Você precisa do Selo da Maestria para aprender um novo ofício!"
                }), 400

            # ✅ CONSOME O SELO (Correção aplicada aqui)
            if isinstance(item_selo, dict):
                nova_qtd = max(0, qtd_selo - 1)
                if nova_qtd <= 0:
                    my_inv.pop("selo_de_maestria", None) # Remove se zerar
                else:
                    item_selo["quantity"] = nova_qtd
            else:
                nova_qtd = max(0, qtd_selo - 1)
                if nova_qtd <= 0:
                    my_inv.pop("selo_de_maestria", None)
                else:
                    my_inv["selo_de_maestria"] = nova_qtd

        # ==========================================
        # 🎁 MAPEAMENTO E CRIAÇÃO DA FERRAMENTA
        # ==========================================
        FERRAMENTAS_INICIAIS = {
            'lenhador': 'machado_pedra', 'minerador': 'picareta_pedra',
            'esfolador': 'faca_pedra', 'colhedor': 'foice_pedra',
            'alquimista': 'frasco_vidro', 'ferreiro': 'martelo_ferreiro_t1',
            'armeiro': 'martelo_armeiro_t1', 'alfaiate': 'ferramentas_alfaiate_t1',
            'joalheiro': 'ferramentas_joalheiro_t1', 'curtidor': 'ferramentas_curtidor_t1',
            'fundidor': 'ferramentas_fundidor_t1'
        }

        nova_profissao_db = {
            "key": prof_key, "type": prof_key, "level": 1, "xp": 0,
            "category": prof_info.get("category"), "display_name": prof_info.get("display_name")
        }
        
        base_id_ferramenta = FERRAMENTAS_INICIAIS.get(prof_key)
        if base_id_ferramenta:
            ferramenta_db = {
                "base_id": base_id_ferramenta, "rarity": "comum",
                "upgrade_level": 1, "durability": [20, 20], "crafter": "Mestre Thorek"
            }
            # Adiciona a ferramenta na mochila local que já estamos manipulando
            my_inv[base_id_ferramenta] = ferramenta_db

        # 👇 1. SISTEMA DE MÚLTIPLAS PROFISSÕES 👇
        learned = player.get("learned_professions", {})
        
        if prof_atual and "key" in prof_atual:
            learned[prof_atual["key"]] = prof_atual
            
        if prof_key in learned:
            nova_profissao_db["level"] = learned[prof_key].get("level", 1)
            nova_profissao_db["xp"] = learned[prof_key].get("xp", 0)

        learned[prof_key] = nova_profissao_db

        # 🔨 SALVA TUDO NO BANCO DE DADOS EM UM ÚNICO PULL
        users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "profession": nova_profissao_db,
                    "learned_professions": learned,
                    "inventory": my_inv # Salva a mochila atualizada (sem o selo e com a ferramenta)
                }
            }
        )

        return jsonify({
            "success": True, 
            "message": f"Você agora domina a arte de {prof_info['display_name']}! Thorek colocou uma ferramenta na sua mochila."
        })
        
    except Exception as e:
        import traceback
        print(f"Erro em aprender_profissao: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500
    
@character_bp.route('/api/npc/resgatar_maestria', methods=['POST'])
def resgatar_maestria():
    from flask import request, jsonify
    from bson import ObjectId
    from modules.player.core import users_collection

    try:
        data = request.json
        user_id = data.get('user_id')
        npc_id = data.get('npc_id')

        player = users_collection.find_one({"_id": ObjectId(user_id)})
        if not player:
            return jsonify({"success": False, "error": "Herói não encontrado."}), 404

        prof_atual = player.get("profession", {})
        prof_key = prof_atual.get("key")
        prof_nivel = int(prof_atual.get("level", 1))

        # 1. Verifica se ele tem uma profissão ativa
        if not prof_key:
            return jsonify({"success": False, "error": "Você precisa de um ofício antes de buscar a maestria."}), 400

        # 2. Verifica se o Nível da PROFISSÃO (e não do personagem) é 50+
        if prof_nivel < 50:
            return jsonify({"success": False, "error": "Volte quando atingir o Nível 50 no seu ofício atual para provar seu valor."}), 400

        # 3. TRAVA DE SEGURANÇA: Impede que o jogador pegue selos infinitos com a mesma profissão
        maestrias_resgatadas = player.get("maestrias_resgatadas", [])
        if prof_key in maestrias_resgatadas:
            return jsonify({"success": False, "error": f"Você já recebeu o Selo de Maestria por suas habilidades como {prof_atual.get('display_name', prof_key)}. Aprenda um novo ofício!"}), 400

        # 4. Cria o Selo no Inventário
        inv = player.get("inventory", {})
        if "selo_de_maestria" in inv:
            if isinstance(inv["selo_de_maestria"], dict):
                inv["selo_de_maestria"]["quantity"] = int(inv["selo_de_maestria"].get("quantity", 0)) + 1
            else:
                inv["selo_de_maestria"] += 1
        else:
            inv["selo_de_maestria"] = {
                "base_id": "selo_de_maestria",
                "name": "Selo de Maestria",
                "type": "especial",
                "quantity": 1,
                "icon": "selo_de_maestria.png",
                "imagem": "selo_de_maestria.png"
            }

        # 5. Adiciona a profissão na lista de resgatadas para ele não pegar de novo
        maestrias_resgatadas.append(prof_key)

        # 6. Salva tudo no banco de dados
        users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "inventory": inv,
                    "maestrias_resgatadas": maestrias_resgatadas
                }
            }
        )

        return jsonify({"success": True, "message": "Maestria reconhecida!"})

    except Exception as e:
        import traceback
        print(f"Erro em resgatar_maestria: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500
          
## ==========================================
# 🌿 ROTA: COLETAR E GANHAR XP DE PROFISSÃO
# ==========================================
@character_bp.route('/api/personagem/coletar', methods=['POST'])
def coletar_recurso():
    from flask import request, jsonify
    from bson import ObjectId
    from modules.player.core import users_collection

    try:
        data = request.json
        user_id = data.get('user_id')
        recurso_tipo = data.get('recurso_tipo') 
        acao = data.get('acao', 'coletar') 
        
        if not user_id or not recurso_tipo:
            return jsonify({"success": False, "error": "Dados inválidos."}), 400
            
        player = users_collection.find_one({"_id": ObjectId(user_id)})
        my_inv = player.get("inventory", {})

        # ==========================================
        # 🚫 TRAVA DE FERRAMENTAS
        # ==========================================
        ferramenta_correta = False
        ferramenta_necessaria = ""
        ferramenta_usada_id = None # Para sabermos qual gastar

        if recurso_tipo == 'madeira':
            ferramenta_necessaria = "Machado"
            for k in my_inv.keys():
                if "machado" in k.lower():
                    ferramenta_correta = True
                    ferramenta_usada_id = k
                    break
                
        # 👇 MUDANÇA AQUI: Adicionado 'minerio_de_ferro' 👇
        elif recurso_tipo in ['pedra', 'ferro', 'minerio_de_ferro']:
            ferramenta_necessaria = "Picareta"
            for k in my_inv.keys():
                if "picareta" in k.lower():
                    ferramenta_correta = True
                    ferramenta_usada_id = k
                    break
                
        elif recurso_tipo == 'linho':
            ferramenta_necessaria = "Foice"
            for k in my_inv.keys():
                if "foice" in k.lower():
                    ferramenta_correta = True
                    ferramenta_usada_id = k
                    break
                
        elif recurso_tipo == 'pena':
            ferramenta_necessaria = "Faca"
            for k in my_inv.keys():
                if "faca" in k.lower():
                    ferramenta_correta = True
                    ferramenta_usada_id = k
                    break
                
        elif recurso_tipo == 'sangue':
            ferramenta_necessaria = "Frasco Vazio"
            for k in my_inv.keys():
                if "frasco" in k.lower():
                    ferramenta_correta = True
                    ferramenta_usada_id = k
                    break

        if not ferramenta_correta:
            return jsonify({"success": False, "error": f"Falta {ferramenta_necessaria}!"}), 400
        
        # ⚠️ VERIFICA SE A FERRAMENTA ESTÁ PARTIDA (DURABILIDADE)
        item_ferramenta = my_inv.get(ferramenta_usada_id, {})
        durabilidade = item_ferramenta.get("durability", [20, 20])
        atual = durabilidade[0]
        
        if atual <= 0:
            return jsonify({"success": False, "error": f"𝑺𝒖𝒂 𝒇𝒆𝒓𝒓𝒂𝒎𝒆𝒏𝒕𝒂 𝒑𝒂𝒓𝒕𝒊𝒖!\n𝑼𝒔𝒆 𝒖𝒎 📜 𝒅𝒆 𝑫𝒖𝒓𝒂𝒃𝒊𝒍𝒊𝒅𝒂𝒅𝒆."}), 400

        # Se for só verificação, pára aqui
        if acao == 'verificar':
            return jsonify({"success": True})

        # ==========================================
        # COMEÇA A COLETA REAL (COM BÔNUS DE NÍVEL!)
        # ==========================================
        prof_atual = player.get("profession", {})
        learned = player.get("learned_professions", {})
        
        # Acha o nível da profissão exigida
        prof_exigida = "lenhador"
        
        # 👇 MUDANÇA AQUI: Adicionado 'minerio_de_ferro' 👇
        if recurso_tipo in ['pedra', 'minerio_de_ferro']: prof_exigida = "minerador"
        elif recurso_tipo == 'linho': prof_exigida = "colhedor"
        elif recurso_tipo == 'pena': prof_exigida = "esfolador"
        elif recurso_tipo == 'sangue': prof_exigida = "alquimista"

        prof_alvo = learned.get(prof_exigida)
        if not prof_alvo and prof_atual.get("key") == prof_exigida:
            prof_alvo = prof_atual
            
        level_atual = int(prof_alvo.get("level", 1)) if prof_alvo else 1
        
        # BÔNUS 1: +1 Item a cada 10 Níveis
        quantidade = 1 + (level_atual // 10)
        
        # BÔNUS 2: Chance de Crítico de Coleta (0.5% por nível = 25% no lvl 50)
        import random
        if random.random() < (level_atual * 0.005):
            quantidade *= 2 # Pega o dobro!

        item_no_banco = my_inv.get(recurso_tipo, {})
        qtd_atual = item_no_banco.get("quantity", 0) if isinstance(item_no_banco, dict) else int(item_no_banco or 0)
        nova_qtd = qtd_atual + quantidade

        # 📉 Diminui 1 de durabilidade da ferramenta
        nova_durabilidade = [max(0, atual - 1), durabilidade[1]]
        item_ferramenta["durability"] = nova_durabilidade

        # CALCULA XP DA PROFISSÃO
        # ==========================================
        # 2. XP PARA A PROFISSÃO CORRETA (MULTI-PROFISSÃO)
        # ==========================================
        xp_ganho = 10
        subiu_nivel = False
        
        # Descobre qual profissão ele está usando agora
        prof_exigida = "lenhador"
        
        # 👇 MUDANÇA AQUI: Adicionado 'minerio_de_ferro' 👇
        if recurso_tipo in ['pedra', 'minerio_de_ferro']: prof_exigida = "minerador"
        elif recurso_tipo == 'linho': prof_exigida = "colhedor"
        elif recurso_tipo == 'pena': prof_exigida = "esfolador"
        elif recurso_tipo == 'sangue': prof_exigida = "alquimista"

        learned = player.get("learned_professions", {})
        prof_ativa = player.get("profession", {})
        
        # Pega os dados da profissão certa (seja da lista de aprendidas ou da ativa)
        prof_alvo = learned.get(prof_exigida)
        if not prof_alvo and prof_ativa.get("key") == prof_exigida:
            prof_alvo = prof_ativa
            
        if prof_alvo:
            xp_atual = int(prof_alvo.get("xp", 0))
            level_atual = int(prof_alvo.get("level", 1))
            novo_xp = xp_atual + xp_ganho
            xp_necessario = 40 + (25 * (level_atual - 1)) + (8 * ((level_atual - 1) ** 2))
            
            while novo_xp >= xp_necessario:
                level_atual += 1
                novo_xp -= xp_necessario
                subiu_nivel = True
                xp_necessario = 40 + (25 * (level_atual - 1)) + (8 * ((level_atual - 1) ** 2))
            
            prof_alvo["level"] = level_atual
            prof_alvo["xp"] = int(novo_xp)
            
            learned[prof_exigida] = prof_alvo # Atualiza na lista geral
            if prof_ativa.get("key") == prof_exigida:
                prof_ativa = prof_alvo # Atualiza a interface se for a ativa

        # SALVA NO BANCO DE DADOS
        update_query = {
            "$set": {
                f"inventory.{recurso_tipo}": {
                    "base_id": recurso_tipo,
                    "name": recurso_tipo.replace('_', ' ').title(), # Para ficar 'Minerio De Ferro' em vez de 'minerio_de_ferro'
                    "type": "material",                
                    "quantity": nova_qtd,
                    "icon": f"{recurso_tipo}.png",     
                    "imagem": f"{recurso_tipo}.png"    
                },
                f"inventory.{ferramenta_usada_id}": item_ferramenta,
                "learned_professions": learned,  # 👈 Salva a lista de conhecimentos
                "profession": prof_ativa         # 👈 Salva a do perfil
            }
        }

        users_collection.update_one({"_id": ObjectId(user_id)}, update_query)

        mensagem_extra = " (Level UP!)" if subiu_nivel else ""

        return jsonify({
            "success": True, 
            "quantidade": quantidade,
            "item_nome": f"{recurso_tipo.replace('_', ' ').title()}{mensagem_extra}" # Fica mais bonito na UI
        })
        
    except Exception as e:
        print(f"Erro na Coleta: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    
# ==========================================
# 🛠️ ROTA: REPARAR FERRAMENTA
# ==========================================
@character_bp.route('/api/personagem/reparar_ferramenta', methods=['POST'])
def reparar_ferramenta():
    from flask import request, jsonify
    from bson import ObjectId
    from modules.player.core import users_collection

    try:
        data = request.json
        user_id = data.get('user_id')
        item_uuid = data.get('item_id')

        player = users_collection.find_one({"_id": ObjectId(user_id)})
        inv = player.get("inventory", {})

        if "pergaminho_durabilidade" not in inv or int(inv["pergaminho_durabilidade"].get("quantity", 0)) < 1:
            return jsonify({"success": False, "error": "Não tens Pergaminhos de Durabilidade!"}), 400

        ferramenta = inv.get(item_uuid)
        if not ferramenta or "durability" not in ferramenta:
            return jsonify({"success": False, "error": "Item inválido para reparo."}), 400

        max_dur = ferramenta["durability"][1]
        ferramenta["durability"] = [max_dur, max_dur]

        # Consome 1 pergaminho
        inv["pergaminho_durabilidade"]["quantity"] = int(inv["pergaminho_durabilidade"]["quantity"]) - 1
        
        users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": {"inventory": inv}})
        
        return jsonify({"success": True, "msg": "Ferramenta restaurada como nova!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500