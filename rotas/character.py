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
    return jsonify({"sucesso": False, "erro": "Use o login da conta Eldora."}), 410

# ==========================================
# 2. ROTA DE CRIAR CONTA / PERSONAGEM
# ==========================================
@character_bp.route('/api/portal/criar_personagem', methods=['POST'])
def api_portal_criar():
    return jsonify({"sucesso": False, "erro": "Entre na conta Eldora antes de criar um personagem."}), 410

@character_bp.route('/api/meus_personagens/<telegram_id>')
def listar_personagens(telegram_id):
    from modules.portal_auth import character_owner_query, current_account
    account = current_account()
    if not account:
        return jsonify(erro='Entre na sua conta.'), 401
    cursor = users_collection.find(character_owner_query(account))
    personagens = []
    for p in cursor:
        personagens.append({"id": str(p["_id"]), "nome": p.get("character_name"), "classe": str(p.get("class", "aventureiro")).capitalize(), "level": p.get("level", 1), "gender": p.get("gender", "masculino")})
    return jsonify(personagens)

@character_bp.route('/api/perfil/atualizar', methods=['POST'])
def atualizar_perfil_custom():
    try:
        from modules.portal_auth import require_csrf
        require_csrf()
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

        # Selecionar o corpo padrão remove a skin equipada. Skins especiais só
        # podem ser equipadas se estiverem desbloqueadas para este personagem.
        genero_curto = "f" if str(jogador.get("gender", "masculino")).lower() in {"f", "feminino", "female"} else "m"
        classe_padrao = str(jogador.get("class", "aventureiro")).lower()
        if classe_padrao in {"aprendiz", "aventureiro"}:
            skin_padrao_id = "aventureiro_feminino" if genero_curto == "f" else "aventureiro_masculino"
        else:
            skin_padrao_id = f"{classe_padrao}_{genero_curto}"

        if id_skin in (None, "", "padrao", skin_padrao_id):
            atualizacao["equipped_skin"] = None
        else:
            if id_skin not in (jogador.get("unlocked_skins") or []):
                return jsonify({"sucesso": False, "erro": "Você não possui esta skin."}), 403
            genero_skin = "f" if str(id_skin).endswith("_f") else "m" if str(id_skin).endswith("_m") else None
            if genero_skin and genero_skin != genero_curto:
                return jsonify({"sucesso": False, "erro": "Esta skin não corresponde ao gênero do personagem."}), 403
            atualizacao["equipped_skin"] = id_skin
        
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
            from modules.skill_progression import Q6_INITIAL_SKILLS_BY_CLASS
            SKILL_INICIAL = Q6_INITIAL_SKILLS_BY_CLASS
            id_certo = SKILL_INICIAL.get(classe_atual, "ataque_basico")
            skills_certas[id_certo] = {"unlocked": True, "rarity": "comum"}
            
            # Injeta a magia certa na conta e salva
            users_collection.update_one({"_id": ObjectId(personagem_id)}, {"$set": {"skills": skills_certas}})

        # Define o nome do sprite para o Phaser
        base_skin = skin_id if skin_id else classe_base
        nome_sprite_mapa = f"{base_skin}_{genero.lower()}"
        letra_gen = genero.lower()[0] if genero else "m"

        from modules.game_data.items import ITEMS_DATA
        from modules.skill_progression import (
            SKILL_MAX_LEVEL,
            SKILL_POWER_BONUS_PER_LEVEL,
            is_evolution_skill,
            skill_is_available_to_class,
        )
        database_skills_perfil = {
            skill_id: {
                **skill_info,
                "upgrade_tome_available": (
                    (ITEMS_DATA.get(f"tomo_{skill_id}") or {}).get("skill_tome_purpose") == "upgrade"
                ),
                "skill_upgrade_available": (
                    not is_evolution_skill(skill_id)
                    and (ITEMS_DATA.get(f"tomo_{skill_id}") or {}).get("type") == "skill_book"
                    and (ITEMS_DATA.get(f"tomo_{skill_id}") or {}).get("skill_tome_purpose") in {"learn", "upgrade"}
                    and skill_is_available_to_class(
                        classe_atual,
                        skill_id,
                        skill_info.get("allowed_classes") or [],
                    )
                ),
                "is_evolution_skill": is_evolution_skill(skill_id),
                "skill_upgrade_max_level": SKILL_MAX_LEVEL,
                "skill_upgrade_bonus_per_level_pct": int(SKILL_POWER_BONUS_PER_LEVEL * 100),
            }
            for skill_id, skill_info in SKILL_DATA.items()
        }

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
            "xp_boost": pdata.get("xp_boost") or {},
            "server_time": datetime.now(timezone.utc).isoformat(),
            "xp_max": xp_necessario,        
            "xp_next_level": xp_necessario, 
            "avatar": f"https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/avatares/avatar_padrao_{letra_gen}.png",
            "avatar_customizado": pdata.get("avatar_customizado", "padrao"),
            "banner_customizado": pdata.get("banner_customizado", "padrao"),
            "equipped_skin": skin_id, 
            "unlocked_skins": unlocked, 
            "skin_mapa": nome_sprite_mapa,
            "database_skills": database_skills_perfil,
            "skills_desbloqueadas": skills_certas,
            "skills_equipadas": pdata.get("equipped_skills", {}),
            "pocao_equipada_hp": pdata.get("pocao_equipada_hp"),
            "pocao_equipada_mp": pdata.get("pocao_equipada_mp"),
            "pergaminho_reparo_equipado": pdata.get("pergaminho_reparo_equipado", False),
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

            from modules.game_data.skills import SKILL_DATA
            from modules.skill_progression import skill_is_available_to_class
            skill_info = SKILL_DATA.get(str(skill_id)) or {}
            classe_jogador = str(
                jogador.get("class") or jogador.get("class_key") or jogador.get("classe") or ""
            )
            if not skill_info or not skill_is_available_to_class(
                classe_jogador,
                str(skill_id),
                skill_info.get("allowed_classes") or [],
            ):
                return jsonify({
                    "sucesso": False,
                    "erro": "Essa habilidade ainda não foi liberada para sua classe.",
                }), 403

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


@character_bp.route('/api/personagem/aprender_habilidade', methods=['POST'])
def api_aprender_habilidade_com_tomo():
    """Aprende uma habilidade consumindo um tomo compatível da mochila."""
    from copy import deepcopy
    from modules.portal_auth import (
        PlayerSessionError,
        require_csrf,
        require_player_identity,
    )
    from modules.game_data.items import ITEMS_DATA
    from modules.game_data.skills import SKILL_DATA
    from modules.skill_progression import (
        is_evolution_skill,
        is_q6_initial_skill,
        is_skill_tome_learnable,
        skill_is_available_to_class,
    )

    try:
        require_csrf()
        dados = request.get_json(silent=True) or {}
        user_id = str(dados.get("user_id") or "")
        item_uid = str(dados.get("item_id") or "").strip()
        if not user_id or not item_uid:
            return jsonify({"sucesso": False, "erro": "Selecione um tomo da mochila."}), 400

        jogador = require_player_identity(user_id)
        inventario_bruto = deepcopy(jogador.get("inventory")) if "inventory" in jogador else None
        if inventario_bruto is not None and not isinstance(inventario_bruto, dict):
            return jsonify({"sucesso": False, "erro": "O formato da mochila é inválido."}), 400
        inventario_original = inventario_bruto if isinstance(inventario_bruto, dict) else {}

        item_instancia = inventario_original.get(item_uid)
        if item_instancia is None:
            return jsonify({"sucesso": False, "erro": "Este tomo não está mais na mochila."}), 404

        base_id = (
            str(item_instancia.get("base_id") or item_uid)
            if isinstance(item_instancia, dict)
            else item_uid
        )
        info_item = ITEMS_DATA.get(base_id) or {}
        skill_id = str((info_item.get("effects") or {}).get("learn_skill") or "")
        skill_info = SKILL_DATA.get(skill_id)
        if info_item.get("type") != "skill_book" or not skill_id or not skill_info:
            return jsonify({"sucesso": False, "erro": "Este item não é um tomo de habilidade válido."}), 400

        if (
            not is_skill_tome_learnable(skill_id)
            or info_item.get("skill_tome_purpose", "learn") != "learn"
        ):
            if is_evolution_skill(skill_id):
                erro_progressao = "Esta habilidade é liberada somente ao concluir a evolução de classe correspondente."
            elif is_q6_initial_skill(skill_id):
                erro_progressao = "Esta habilidade inicial é aprendida ao concluir a missão do Grimório com Selene."
            else:
                erro_progressao = "Este tomo serve para aprimorar uma habilidade já aprendida, não para ensiná-la."
            return jsonify({"sucesso": False, "erro": erro_progressao}), 403

        classes_permitidas = (
            info_item.get("class_req")
            or info_item.get("required_class")
            or skill_info.get("allowed_classes")
            or []
        )
        if isinstance(classes_permitidas, str):
            classes_permitidas = [classes_permitidas]
        classe_jogador = str(jogador.get("class") or jogador.get("class_key") or jogador.get("classe") or "aventureiro")
        if not skill_is_available_to_class(classe_jogador, skill_id, classes_permitidas):
            return jsonify({
                "sucesso": False,
                "erro": "Seu personagem ainda não pode aprender essa habilidade.",
            }), 403

        def normalizar_skills(valor):
            if isinstance(valor, dict):
                return deepcopy(valor)
            resultado = {}
            if isinstance(valor, list):
                for skill_existente in valor:
                    if isinstance(skill_existente, dict):
                        sid = skill_existente.get("skill_id") or skill_existente.get("id")
                        if sid:
                            resultado[str(sid)] = deepcopy(skill_existente)
                    elif skill_existente:
                        resultado[str(skill_existente)] = {
                            "unlocked": True,
                            "rarity": "comum",
                            "level": 1,
                        }
            return resultado

        skills_anteriores = jogador.get("skills")
        skills_desbloqueadas_anteriores = jogador.get("skills_desbloqueadas")
        skills_novas = normalizar_skills(skills_anteriores)
        skills_desbloqueadas_novas = normalizar_skills(skills_desbloqueadas_anteriores)
        if skill_id in skills_novas or skill_id in skills_desbloqueadas_novas:
            nome_skill = skill_info.get("display_name") or skill_id
            return jsonify({
                "sucesso": False,
                "erro": f"Você já conhece {nome_skill}.",
            }), 409

        inventario_novo = deepcopy(inventario_original)
        entry = inventario_novo[item_uid]
        if isinstance(entry, dict):
            campo_quantidade = next(
                (campo for campo in ("quantity", "qty", "qtd", "quantidade") if campo in entry),
                "quantity",
            )
            try:
                quantidade = int(entry.get(campo_quantidade, 1))
            except (TypeError, ValueError):
                quantidade = 0
            if quantidade < 1:
                return jsonify({"sucesso": False, "erro": "A quantidade deste tomo é inválida."}), 400
            if quantidade == 1:
                del inventario_novo[item_uid]
            else:
                entry[campo_quantidade] = quantidade - 1
        else:
            try:
                quantidade = int(entry)
            except (TypeError, ValueError):
                quantidade = 0
            if quantidade < 1:
                return jsonify({"sucesso": False, "erro": "A quantidade deste tomo é inválida."}), 400
            if quantidade == 1:
                del inventario_novo[item_uid]
            else:
                inventario_novo[item_uid] = quantidade - 1

        skills_novas[skill_id] = {
            "unlocked": True,
            "rarity": "comum",
            "level": 1,
            "progress": 0,
        }
        skills_desbloqueadas_novas[skill_id] = deepcopy(skills_novas[skill_id])

        filtro = {"_id": jogador["_id"]}
        filtro["inventory"] = inventario_bruto if "inventory" in jogador else {"$exists": False}
        filtro["skills"] = skills_anteriores if "skills" in jogador else {"$exists": False}
        filtro["skills_desbloqueadas"] = (
            skills_desbloqueadas_anteriores
            if "skills_desbloqueadas" in jogador else {"$exists": False}
        )
        filtro["class"] = jogador["class"] if "class" in jogador else {"$exists": False}
        filtro["class_key"] = jogador["class_key"] if "class_key" in jogador else {"$exists": False}
        filtro["classe"] = jogador["classe"] if "classe" in jogador else {"$exists": False}
        atualizacao = users_collection.update_one(
            filtro,
            {"$set": {
                "inventory": inventario_novo,
                "skills": skills_novas,
                "skills_desbloqueadas": skills_desbloqueadas_novas,
            }},
        )
        if atualizacao.modified_count != 1:
            return jsonify({
                "sucesso": False,
                "erro": "A mochila ou as habilidades mudaram. Atualize e tente novamente.",
            }), 409

        try:
            from modules.player.core import clear_player_cache
            asyncio.run(clear_player_cache(str(jogador["_id"])))
        except Exception:
            pass

        nome_skill = skill_info.get("display_name") or skill_id
        return jsonify({
            "sucesso": True,
            "skill_id": skill_id,
            "msg": f"✨ Você aprendeu {nome_skill}! Agora equipe a habilidade no Grimório.",
        })
    except PlayerSessionError as exc:
        return jsonify({"sucesso": False, "erro": str(exc)}), exc.status_code
    except ValueError as exc:
        return jsonify({"sucesso": False, "erro": str(exc)}), 403
    except Exception:
        import traceback
        traceback.print_exc()
        return jsonify({"sucesso": False, "erro": "Não foi possível aprender a habilidade agora."}), 500


@character_bp.route('/api/personagem/evolucao/<personagem_id>', methods=['GET'])
def api_status_evolucao_classe(personagem_id):
    from modules.portal_auth import PlayerSessionError, require_player_identity
    from modules.class_evolution_service import get_player_evolution_status

    try:
        jogador = require_player_identity(personagem_id)
        status = get_player_evolution_status(jogador)
        opcao = status.get("option") or {}
        return jsonify({
            "sucesso": True,
            "classe": str(jogador.get("class") or jogador.get("class_key") or jogador.get("classe") or "aventureiro"),
            "level": int(jogador.get("level") or 1),
            "status": status.get("status"),
            "mensagem": status.get("message", ""),
            "opcao": {
                "from": opcao.get("from"),
                "to": opcao.get("to"),
                "tier_num": opcao.get("tier_num"),
                "display_name": opcao.get("display_name"),
                "desc": opcao.get("desc"),
                "min_level": opcao.get("min_level"),
                "trial_monster_id": opcao.get("trial_monster_id"),
            } if opcao else None,
            "etapas": status.get("path_nodes", []),
            "todas_etapas_concluidas": bool(status.get("all_nodes_complete")),
            "prova": status.get("trial"),
        })
    except PlayerSessionError as exc:
        return jsonify({"sucesso": False, "erro": str(exc)}), exc.status_code
    except Exception:
        import traceback
        traceback.print_exc()
        return jsonify({"sucesso": False, "erro": "Não foi possível carregar a evolução."}), 500


@character_bp.route('/api/personagem/evolucao/etapa', methods=['POST'])
def api_concluir_etapa_evolucao():
    import asyncio
    from modules.portal_auth import PlayerSessionError, require_csrf, require_player_identity
    from modules.class_evolution_service import attempt_ascension_node

    try:
        require_csrf()
        data = request.get_json(silent=True) or {}
        user_id = str(data.get("user_id") or "")
        node_id = str(data.get("node_id") or "").strip()
        if not user_id or not node_id:
            return jsonify({"sucesso": False, "erro": "Selecione uma etapa da evolução."}), 400
        jogador = require_player_identity(user_id)
        sucesso, mensagem = asyncio.run(attempt_ascension_node(jogador["_id"], node_id))
        return jsonify({"sucesso": sucesso, "mensagem": mensagem}), (200 if sucesso else 400)
    except PlayerSessionError as exc:
        return jsonify({"sucesso": False, "erro": str(exc)}), exc.status_code
    except Exception:
        import traceback
        traceback.print_exc()
        return jsonify({"sucesso": False, "erro": "Não foi possível registrar essa etapa."}), 500


# A prova será iniciada pela região própria quando ela for implementada.


@character_bp.route('/api/personagem/evolucao/finalizar', methods=['POST'])
def api_finalizar_evolucao_classe():
    import asyncio
    from modules.portal_auth import PlayerSessionError, require_csrf, require_player_identity
    from modules.class_evolution_service import finalize_evolution

    try:
        require_csrf()
        data = request.get_json(silent=True) or {}
        user_id = str(data.get("user_id") or "")
        target_class = str(data.get("target_class") or "").strip().lower()
        if not user_id or not target_class:
            return jsonify({"sucesso": False, "erro": "Dados incompletos para concluir a evolução."}), 400
        jogador = require_player_identity(user_id)
        sucesso, mensagem = asyncio.run(finalize_evolution(jogador["_id"], target_class))
        return jsonify({"sucesso": sucesso, "mensagem": mensagem}), (200 if sucesso else 400)
    except PlayerSessionError as exc:
        return jsonify({"sucesso": False, "erro": str(exc)}), exc.status_code
    except Exception:
        import traceback
        traceback.print_exc()
        return jsonify({"sucesso": False, "erro": "Não foi possível concluir a evolução."}), 500


@character_bp.get('/api/personagem/<personagem_id>/habilidades/<skill_id>/aprimoramento')
def api_consultar_aprimoramento_habilidade(personagem_id, skill_id):
    from modules.portal_auth import PlayerSessionError, require_player_identity
    from modules.class_evolution_service import get_skill_upgrade_quote

    try:
        jogador = require_player_identity(personagem_id)
        quote = get_skill_upgrade_quote(jogador, skill_id)
        response = jsonify({"sucesso": True, "formula": quote})
        response.headers["Cache-Control"] = "no-store"
        return response
    except PlayerSessionError as exc:
        return jsonify({"sucesso": False, "erro": str(exc)}), exc.status_code
    except Exception:
        import traceback
        traceback.print_exc()
        return jsonify({"sucesso": False, "erro": "Não foi possível consultar a fórmula."}), 500


@character_bp.route('/api/personagem/aprimorar_habilidade', methods=['POST'])
def api_aprimorar_habilidade_com_tomo():
    from copy import deepcopy
    import asyncio
    from modules.portal_auth import PlayerSessionError, require_csrf, require_player_identity
    from modules.class_evolution_service import apply_skill_upgrade_to_player_data

    try:
        require_csrf()
        data = request.get_json(silent=True) or {}
        user_id = str(data.get("user_id") or "")
        skill_id = str(data.get("skill_id") or "").strip()
        if not user_id or not skill_id:
            return jsonify({"sucesso": False, "erro": "Selecione uma habilidade para aprimorar."}), 400
        jogador = require_player_identity(user_id)
        jogador_atualizado = deepcopy(jogador)
        sucesso, mensagem, habilidade = apply_skill_upgrade_to_player_data(jogador_atualizado, skill_id)
        if not sucesso:
            return jsonify({"sucesso": False, "erro": mensagem}), 400

        campos_protegidos = (
            "gold",
            "inventory",
            "skills",
            "skills_desbloqueadas",
            "database_skills",
            "class",
            "class_key",
            "classe",
        )
        filtro = {"_id": jogador["_id"]}
        atualizacao = {}
        for campo in campos_protegidos:
            filtro[campo] = deepcopy(jogador[campo]) if campo in jogador else {"$exists": False}
            if campo in jogador_atualizado:
                atualizacao[campo] = jogador_atualizado[campo]

        resultado = users_collection.update_one(filtro, {"$set": atualizacao})
        if resultado.modified_count != 1:
            return jsonify({
                "sucesso": False,
                "erro": "A mochila ou o nível da habilidade mudou. Atualize e tente novamente.",
            }), 409

        try:
            from modules.player.core import clear_player_cache
            asyncio.run(clear_player_cache(str(jogador["_id"])))
        except Exception:
            pass
        return jsonify({"sucesso": sucesso, "mensagem": mensagem, "habilidade": habilidade}), (200 if sucesso else 400)
    except PlayerSessionError as exc:
        return jsonify({"sucesso": False, "erro": str(exc)}), exc.status_code
    except Exception:
        import traceback
        traceback.print_exc()
        return jsonify({"sucesso": False, "erro": "Não foi possível aprimorar a habilidade."}), 500
    
@character_bp.route('/api/npc/missao/grimorio', methods=['POST'])
def api_missao_grimorio():
    # Rota legada desativada: concluir o Grimório agora passa pelo registro
    # oficial de Selene, que valida a sequência completa da missão.
    return jsonify({
        "sucesso": False,
        "erro": "Use a entrega oficial da missão com a Arquimaga Selene."
    }), 410

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
    from modules.combat.durability import apply_equipment_combat_wear
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
            combate_ativo = False

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

                    if not mob:
                        continue

                    if int(mob.get("hp_atual", mob.get("hp", 0)) or 0) > 0:
                        combate_ativo = True

                    if is_dungeon_event_mob(mob):
                        mob_evento = mob

                    if combate_ativo and mob_evento:
                        break

            durabilidade_resultado = {"alterados": [], "quebrados": [], "mensagens": []}
            if combate_ativo:
                jogador = users_collection.find_one({"_id": ObjectId(user_id)})
                if jogador:
                    durabilidade_resultado = apply_equipment_combat_wear(
                        jogador,
                        amount=1,
                    )
                    users_collection.update_one(
                        {"_id": ObjectId(user_id)},
                        {"$set": {"inventory": jogador.get("inventory", {})}},
                    )

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

                ] + [
                    {
                        "autor": "sistema",
                        "texto": msg,
                        "dano": 0,
                        "tipo": "durabilidade",
                    }
                    for msg in durabilidade_resultado.get("mensagens", [])
                ],
                "durabilidade": durabilidade_resultado,

            })

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # 👈 2. Puxa o motor da memória de forma 100% segura!
        sistema_cacada = current_app.config.get('SISTEMA_CACADA')

        # O resto do código continua igual...
        import time
        inicio_acao_perf = time.perf_counter()
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

        duracao_acao_ms = (time.perf_counter() - inicio_acao_perf) * 1000
        current_app.logger.warning(
            "[COMBATE PERF] rota ação=%s total=%.0fms",
            acao,
            duracao_acao_ms,
        )
        resposta = jsonify(resultado)
        resposta.headers["Server-Timing"] = f"combat;dur={duracao_acao_ms:.1f}"
        return resposta

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
    from modules.player.inventory import can_add_bundle, try_add_item_to_inventory
    from modules.game_data.regions import REGIONS_DATA
    import copy
    import random

    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get('user_id')
        recurso_tipo = str(data.get('recurso_tipo') or '').strip().lower()
        acao = data.get('acao', 'coletar')
        
        if not user_id or not recurso_tipo:
            return jsonify({"success": False, "error": "Dados inválidos."}), 400
            
        player = users_collection.find_one({"_id": ObjectId(user_id)})
        if not player:
            return jsonify({"success": False, "error": "Herói não encontrado."}), 404
        from modules import profession_engine

        if acao not in {'verificar', 'coletar'}:
            return jsonify({"success": False, "error": "Ação de coleta inválida."}), 400

        preparo = profession_engine.validate_and_prepare_gather(player, recurso_tipo)
        if not preparo.get("ok"):
            return jsonify({"success": False, "error": preparo.get("error")}), 400

        ultima_posicao = player.get('last_pos') or {}
        regiao_salva = ultima_posicao.get('regiao') if isinstance(ultima_posicao, dict) else None
        regiao_id = str(data.get('regiao') or regiao_salva or '').strip()
        regiao = REGIONS_DATA.get(regiao_id)
        if not regiao:
            return jsonify({"success": False, "error": "Não foi possível identificar a região da coleta."}), 400

        prof_exigida = preparo['profession']
        tabela_regional = (regiao.get('gather_table') or {}).get(prof_exigida) or []
        if not tabela_regional:
            return jsonify({"success": False, "error": "Não há pontos de coleta para essa profissão nesta região."}), 400

        prof_atual = player.get("profession", {}) or {}
        if not isinstance(prof_atual, dict):
            prof_atual = {}
        learned = player.get("learned_professions", {}) or {}
        if isinstance(learned, dict):
            prof_alvo = learned.get(prof_exigida)
        elif isinstance(learned, list):
            prof_alvo = next((
                item for item in learned
                if isinstance(item, dict)
                and (item.get('key') or item.get('type') or item.get('profession')) == prof_exigida
            ), None)
        else:
            prof_alvo = None
        if not isinstance(prof_alvo, dict):
            prof_alvo = None
        if not prof_alvo and prof_atual.get("key") == prof_exigida:
            prof_alvo = prof_atual
        try:
            level_atual = max(1, int((prof_alvo or {}).get("level", 1) or 1))
        except (TypeError, ValueError):
            level_atual = 1

        tool_info = preparo.get('tool_info') or {}
        try:
            tool_tier = max(1, int(tool_info.get('tier', 1) or 1))
        except (TypeError, ValueError):
            tool_tier = 1

        from modules import game_data
        opcoes = []
        for linha in tabela_regional:
            try:
                nivel_minimo = max(1, int(linha.get('min_level', 1) or 1))
                tier_minimo = max(1, int(linha.get('min_tool_tier', 1) or 1))
                peso = float(linha.get('weight', 0) or 0)
            except (TypeError, ValueError):
                continue
            item_id = str(linha.get('item') or '').strip()
            if (
                item_id
                and item_id in game_data.ITEMS_DATA
                and peso > 0
                and level_atual >= nivel_minimo
                and tool_tier >= tier_minimo
            ):
                opcoes.append(linha)

        if not opcoes:
            return jsonify({
                "success": False,
                "error": "Seu nível de profissão ou ferramenta ainda não libera materiais nesta região."
            }), 400

        # A verificação não consome durabilidade, estoque nem materiais.
        if acao == 'verificar':
            return jsonify({"success": True, "regiao": regiao_id, "profissao": prof_exigida})

        # Cada linha elegível representa uma chance relativa. Uma coleta sorteia
        # um único material; peso 70 tem o dobro da chance de peso 35.
        linha_escolhida = random.choices(
            opcoes,
            weights=[float(linha.get('weight', 0) or 0) for linha in opcoes],
            k=1
        )[0]
        item_id = str(linha_escolhida['item'])
        try:
            quantidade = random.randint(
                max(1, int(linha_escolhida.get('min_qty', 1) or 1)),
                max(1, int(linha_escolhida.get('max_qty', 1) or 1)),
            )
        except (TypeError, ValueError):
            quantidade = 1

        # Bônus de profissão já existente: +1 por dez níveis e chance crítica.
        quantidade *= 1 + (level_atual // 10)
        if random.random() < min(0.25, level_atual * 0.005):
            quantidade *= 2

        jogador_atualizado = copy.deepcopy(player)
        recompensa = [{"item_id": item_id, "quantity": quantidade}]
        pode_adicionar, motivo, _ = can_add_bundle(jogador_atualizado, recompensa)
        if not pode_adicionar:
            return jsonify({"success": False, "error": motivo}), 400
        if not try_add_item_to_inventory(jogador_atualizado, item_id, quantidade):
            return jsonify({"success": False, "error": "Não foi possível guardar o material na mochila."}), 400

        ferramenta_usada_id = preparo["tool_uid"]
        inventario_atualizado = jogador_atualizado.get('inventory') or {}
        item_ferramenta = inventario_atualizado.get(ferramenta_usada_id)
        if not isinstance(item_ferramenta, dict):
            return jsonify({"success": False, "error": "A ferramenta equipada não está mais na mochila."}), 409
        atual, maximo = profession_engine._repair_durability(item_ferramenta, tool_info)
        item_ferramenta["durability"] = [max(0, atual - 1), maximo]

        # Ganha XP somente depois que a recompensa couber na mochila.
        learned = jogador_atualizado.get("learned_professions", {}) or {}
        prof_ativa = jogador_atualizado.get("profession", {}) or {}
        if not isinstance(prof_ativa, dict):
            prof_ativa = {}
        if isinstance(learned, dict):
            prof_alvo = learned.get(prof_exigida)
        elif isinstance(learned, list):
            prof_alvo = next((
                item for item in learned
                if isinstance(item, dict)
                and (item.get('key') or item.get('type') or item.get('profession')) == prof_exigida
            ), None)
        else:
            prof_alvo = None
        if not isinstance(prof_alvo, dict):
            prof_alvo = None
        if not prof_alvo and prof_ativa.get("key") == prof_exigida:
            prof_alvo = prof_ativa

        xp_ganho = 10
        subiu_nivel = False
        if prof_alvo:
            try:
                xp_atual = int(prof_alvo.get("xp", 0) or 0)
                nivel_profissao = max(1, int(prof_alvo.get("level", 1) or 1))
            except (TypeError, ValueError):
                xp_atual, nivel_profissao = 0, 1
            novo_xp = xp_atual + xp_ganho
            xp_necessario = 40 + (25 * (nivel_profissao - 1)) + (8 * ((nivel_profissao - 1) ** 2))
            while novo_xp >= xp_necessario:
                nivel_profissao += 1
                novo_xp -= xp_necessario
                subiu_nivel = True
                xp_necessario = 40 + (25 * (nivel_profissao - 1)) + (8 * ((nivel_profissao - 1) ** 2))
            prof_alvo["level"] = nivel_profissao
            prof_alvo["xp"] = int(novo_xp)
            if isinstance(learned, dict):
                learned[prof_exigida] = prof_alvo
            if prof_ativa.get("key") == prof_exigida:
                prof_ativa = prof_alvo

        users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "inventory": inventario_atualizado,
                "learned_professions": learned,
                "profession": prof_ativa,
            }}
        )

        try:
            import asyncio
            from modules.player.core import clear_player_cache
            asyncio.run(clear_player_cache(user_id))
        except Exception:
            pass

        item_nome = game_data.get_display_name(item_id)
        if subiu_nivel:
            item_nome = f"{item_nome} (Profissão subiu de nível!)"

        return jsonify({
            "success": True,
            "quantidade": quantidade,
            "item_nome": item_nome,
            "recompensas": [{"item_id": item_id, "item_nome": game_data.get_display_name(item_id), "quantidade": quantidade}],
            "regiao": regiao_id,
            "profissao": prof_exigida,
        })

    except Exception as e:
        print(f"Erro na Coleta: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    
# ==========================================
# 🛠️ ROTA: REPARAR FERRAMENTA
# ==========================================
@character_bp.route('/api/personagem/reparar_ferramenta', methods=['POST'])
def reparar_ferramenta():
    # Mantém a mesma regra independentemente da ordem dos blueprints.
    from modules.webapp_api import api_reparar_ferramenta
    return api_reparar_ferramenta()
