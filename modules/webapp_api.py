import asyncio
import traceback
from flask import Blueprint, jsonify, request
from bson.objectid import ObjectId
from modules.player.stats import _get_class_key_normalized
from modules.game_data.cosmetics import CATALOGO_AVATARES, CATALOGO_BANNERS
from modules.player.core import users_collection
from datetime import datetime, timezone
from modules import market_manager
from modules.game_data.season_pass import RECOMPENSAS_PASSE
from werkzeug.security import generate_password_hash, check_password_hash
from modules.player.core import db
from modules.game_data import items as items_data
import copy
import math
import random

contas_collection = db["contas_mestre"]
webapp_bp = Blueprint('webapp_bp', __name__)

def _run_async(coro):
    """Ferramenta interna para rodar funções Async do Telegram no Flask"""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(coro)
        loop.close()
        return res

def _json_seguro_mongo(valor):
    """
    Converte ObjectId do MongoDB para string antes de enviar ao frontend.
    Funciona também dentro de dicts e listas.
    """
    if isinstance(valor, ObjectId):
        return str(valor)

    if isinstance(valor, dict):
        return {
            chave: _json_seguro_mongo(conteudo)
            for chave, conteudo in valor.items()
        }

    if isinstance(valor, list):
        return [
            _json_seguro_mongo(item)
            for item in valor
        ]

    if isinstance(valor, tuple):
        return [
            _json_seguro_mongo(item)
            for item in valor
        ]

    return valor

def _formatar_stats_item_para_front(obj_item: dict) -> dict:
    """
    Junta todos os possíveis locais de atributos do item:
    - attributes
    - enchantments
    - stats
    - damage
    """
    if not isinstance(obj_item, dict):
        return {}

    stats_final = {}

    for campo in ("attributes", "enchantments", "stats"):
        bloco = obj_item.get(campo)
        if isinstance(bloco, dict):
            for chave, valor in bloco.items():
                if chave:
                    stats_final[chave] = valor

    damage = obj_item.get("damage")
    if isinstance(damage, dict) and "dmg" not in stats_final:
        dmin = damage.get("min") or damage.get("min_damage")
        dmax = damage.get("max") or damage.get("max_damage")

        if dmin is not None and dmax is not None:
            stats_final["dmg"] = {
                "value": f"{dmin}-{dmax}",
                "source": "damage"
            }

    return stats_final

# ============================================================
# 💎 LOJA PREMIUM - MUNDO DE ELDORA
# ============================================================


# ============================================================
# 🛍️ CATÁLOGO DE PACOTES
# ============================================================

@webapp_bp.route(
    '/api/premium/catalogo/<user_id>',
    methods=['GET']
)
def api_premium_catalogo(
    user_id
):
    try:
        from modules import (
            premium_store_manager
        )


        resultado = (
            premium_store_manager
            .obter_catalogo(
                user_id
            )
        )


        return jsonify(
            resultado
        ), (
            200
            if resultado.get(
                "success"
            )
            else 400
        )


    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,

            "error": (
                "Erro ao carregar "
                "a Loja de Eldora: "
                f"{str(e)}"
            ),
        }), 500


# ============================================================
# 🧾 CRIAR PEDIDO
# ============================================================

@webapp_bp.route(
    '/api/premium/pedido/criar',
    methods=['POST']
)
def api_premium_criar_pedido():
    try:
        from modules import (
            premium_store_manager
        )


        dados = request.json or {}


        resultado = (
            premium_store_manager
            .criar_pedido(
                user_id=
                    dados.get(
                        "user_id"
                    ),

                pacote_id=
                    dados.get(
                        "pacote_id"
                    ),
            )
        )


        return jsonify(
            resultado
        ), (
            200
            if resultado.get(
                "success"
            )
            else 400
        )


    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,

            "error": (
                "Erro ao criar pedido: "
                f"{str(e)}"
            ),
        }), 500


# ============================================================
# 📜 PEDIDOS DO JOGADOR
# ============================================================

@webapp_bp.route(
    '/api/premium/pedidos/<user_id>',
    methods=['GET']
)
def api_premium_pedidos(
    user_id
):
    try:
        from modules import (
            premium_store_manager
        )


        limite = request.args.get(
            "limite",
            20
        )


        resultado = (
            premium_store_manager
            .listar_pedidos_usuario(
                user_id=
                    user_id,

                limite=
                    limite,
            )
        )


        return jsonify(
            resultado
        ), (
            200
            if resultado.get(
                "success"
            )
            else 400
        )


    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,

            "error": (
                "Erro ao carregar "
                "os pedidos: "
                f"{str(e)}"
            ),
        }), 500

# ============================================================
# 💠 CHECKOUT PIX DO PEDIDO
# ============================================================

@webapp_bp.route(
    '/api/premium/pedido/pix',
    methods=['POST']
)
def api_premium_pedido_pix():
    try:
        from modules import (
            premium_store_manager
        )


        dados = request.json or {}


        resultado = (
            premium_store_manager
            .gerar_checkout_pix(
                user_id=
                    dados.get(
                        "user_id"
                    ),

                codigo_pedido=
                    dados.get(
                        "codigo_pedido"
                    ),
            )
        )


        return jsonify(
            resultado
        ), (
            200
            if resultado.get(
                "success"
            )
            else 400
        )


    except Exception as e:
        traceback.print_exc()


        return jsonify({
            "success": False,

            "error": (
                "Erro ao preparar "
                "o pagamento Pix: "
                f"{str(e)}"
            ),
        }), 500

# ============================================================
# 📎 ENVIAR COMPROVANTE PIX
# ============================================================

@webapp_bp.route(
    '/api/premium/pedido/comprovante',
    methods=['POST']
)
def api_premium_enviar_comprovante():
    try:
        from werkzeug.utils import (
            secure_filename
        )

        from modules import (
            premium_store_manager
        )


        user_id = request.form.get(
            "user_id"
        )


        codigo_pedido = request.form.get(
            "codigo_pedido"
        )


        arquivo = request.files.get(
            "comprovante"
        )


        if not user_id:
            return jsonify({
                "success": False,
                "error": "Jogador não informado.",
            }), 400


        if not codigo_pedido:
            return jsonify({
                "success": False,
                "error": "Pedido não informado.",
            }), 400


        if not arquivo:
            return jsonify({
                "success": False,
                "error": (
                    "Selecione o comprovante."
                ),
            }), 400


        nome = secure_filename(
            arquivo.filename
            or "comprovante"
        )


        dados_arquivo = arquivo.read()


        # Máximo: 5 MB
        limite_bytes = (
            5
            * 1024
            * 1024
        )


        if not dados_arquivo:
            return jsonify({
                "success": False,
                "error": "Arquivo vazio.",
            }), 400


        if len(
            dados_arquivo
        ) > limite_bytes:

            return jsonify({
                "success": False,
                "error": (
                    "O comprovante pode ter "
                    "no máximo 5 MB."
                ),
            }), 400


        # ----------------------------------------------------
        # 🔒 VALIDAÇÃO REAL DO FORMATO
        #
        # Não confiamos somente no MIME informado
        # pelo navegador.
        # ----------------------------------------------------

        mime_real = None


        # JPEG
        if dados_arquivo.startswith(
            b"\xff\xd8\xff"
        ):
            mime_real = "image/jpeg"


        # PNG
        elif dados_arquivo.startswith(
            b"\x89PNG\r\n\x1a\n"
        ):
            mime_real = "image/png"


        # PDF
        elif dados_arquivo.startswith(
            b"%PDF-"
        ):
            mime_real = "application/pdf"


        # WEBP
        elif (
            len(dados_arquivo) >= 12
            and dados_arquivo[:4] == b"RIFF"
            and dados_arquivo[8:12] == b"WEBP"
        ):
            mime_real = "image/webp"


        if not mime_real:

            return jsonify({
                "success": False,
                "error": (
                    "Formato inválido. "
                    "Envie JPG, PNG, WEBP ou PDF."
                ),
            }), 400


        resultado = (
            premium_store_manager
            .enviar_comprovante_pix(
                user_id=
                    user_id,

                codigo_pedido=
                    codigo_pedido,

                arquivo_bytes=
                    dados_arquivo,

                nome_arquivo=
                    nome,

                mime_type=
                    mime_real,
            )
        )


        return jsonify(
            resultado
        ), (
            200
            if resultado.get(
                "success"
            )
            else 400
        )


    except Exception as e:

        traceback.print_exc()


        return jsonify({
            "success": False,

            "error": (
                "Erro ao enviar comprovante: "
                f"{str(e)}"
            ),
        }), 500

         
# ==========================================
# 1. A ROTA ÚNICA E DEFINITIVA DO PERFIL
# ==========================================
@webapp_bp.route('/perfil/<user_id>')
def obter_perfil(user_id):
    try:
        from modules import player_manager
        from modules.game_data import items as items_data
        from modules.game_data.equipment import SLOT_EMOJI, SLOT_ORDER
        from modules.game_data.classes import get_class_avatar
        from modules.game_data.skins import get_skin_avatar
        
        # 🔍 1. Busca o jogador com suporte a ObjectId ou Telegram ID
        busca_id = ObjectId(user_id) if len(str(user_id)) == 24 else int(user_id) if str(user_id).isdigit() else user_id
        pdata = users_collection.find_one({"$or": [{"_id": busca_id}, {"last_chat_id": busca_id}, {"telegram_id_owner": busca_id}, {"telegram_id": busca_id}]})
        
        if not pdata:
            return jsonify({"erro": "Personagem não encontrado."}), 404

                # =====================================================
        # 🧹 AUTO-CORREÇÃO LEGACY — MISSÃO DO GRIMÓRIO Q6
        # =====================================================
        # Contas antigas podem já possuir a habilidade inicial
        # da classe, mas ainda ter a missão q6 como "ativa".
        #
        # Se a habilidade já foi aprendida, a missão foi
        # necessariamente concluída e deve ficar "resgatada".
        # =====================================================

        try:
            SKILLS_INICIAIS_Q6 = {
                "guerreiro_corte_perfurante",
                "mago_bola_de_fogo",
                "assassino_ataque_furtivo",
                "cacador_flecha_precisa",
                "curandeiro_chama_sagrada",
                "berserker_golpe_selvagem",
                "samurai_corte_iaijutsu",
                "monge_rajada_de_punhos",
                "bardo_nota_cortante",
            }

            # -----------------------------------------
            # 🔮 LÊ AS SKILLS DO JOGADOR
            # -----------------------------------------

            skills_q6 = pdata.get(
                "skills",
                {}
            ) or {}

            if not isinstance(
                skills_q6,
                dict
            ):
                skills_q6 = {}


            # -----------------------------------------
            # 🔍 VERIFICA SE ALGUMA SKILL INICIAL
            # JÁ FOI REALMENTE DESBLOQUEADA
            # -----------------------------------------

            possui_skill_q6 = False

            for skill_id in SKILLS_INICIAIS_Q6:

                if skill_id not in skills_q6:
                    continue

                dados_skill = skills_q6.get(
                    skill_id
                )

                # Formato moderno:
                #
                # "monge_rajada_de_punhos": {
                #     "unlocked": True,
                #     ...
                # }
                if isinstance(
                    dados_skill,
                    dict
                ):

                    if dados_skill.get(
                        "unlocked",
                        True
                    ):
                        possui_skill_q6 = True
                        break

                # Compatibilidade com formatos antigos
                else:
                    possui_skill_q6 = True
                    break


            # -----------------------------------------
            # 📜 LÊ O ESTADO ATUAL DA Q6
            # -----------------------------------------

            quests_q6 = pdata.get(
                "quests",
                {}
            ) or {}

            if not isinstance(
                quests_q6,
                dict
            ):
                quests_q6 = {}

            dados_q6 = quests_q6.get(
                "q6_selene_grimorio",
                {}
            ) or {}

            if isinstance(
                dados_q6,
                dict
            ):
                status_q6 = dados_q6.get(
                    "status"
                )
            else:
                status_q6 = None


            # -----------------------------------------
            # ✅ CORRIGE A CONTA ANTIGA
            # -----------------------------------------

            if (
                possui_skill_q6
                and status_q6 != "resgatada"
            ):

                users_collection.update_one(
                    {
                        "_id": pdata["_id"]
                    },
                    {
                        "$set": {
                            "quests.q6_selene_grimorio.status":
                                "resgatada"
                        }
                    }
                )


                # -------------------------------------
                # ⚡ CORRIGE TAMBÉM O pdata DESTA
                # MESMA REQUISIÇÃO.
                #
                # Assim não precisa carregar o perfil
                # duas vezes para o Diário perceber.
                # -------------------------------------

                if not isinstance(
                    pdata.get("quests"),
                    dict
                ):
                    pdata["quests"] = {}

                if not isinstance(
                    pdata["quests"].get(
                        "q6_selene_grimorio"
                    ),
                    dict
                ):
                    pdata["quests"][
                        "q6_selene_grimorio"
                    ] = {}

                pdata["quests"][
                    "q6_selene_grimorio"
                ][
                    "status"
                ] = "resgatada"


                print(
                    "✅ [Q6 LEGACY] "
                    f"Missão do Grimório corrigida para "
                    f"resgatada: {pdata.get('character_name')}"
                )


        except Exception as erro_q6:

            # Essa correção nunca deve impedir
            # o perfil de carregar.
            print(
                "⚠️ [Q6 LEGACY] "
                "Falha na auto-correção:",
                erro_q6
            )

        # =====================================================
        # 🧹 AUTO-CORREÇÃO LEGACY — MISSÃO DO GRIMÓRIO Q6
        # =====================================================
        # Contas antigas podem já possuir a habilidade inicial
        # da classe, mas ainda ter a missão q6 como "ativa".
        #
        # Se a habilidade já foi aprendida, a missão foi
        # necessariamente concluída e deve ficar "resgatada".
        # =====================================================

        try:
            SKILLS_INICIAIS_Q6 = {
                "guerreiro_corte_perfurante",
                "mago_bola_de_fogo",
                "assassino_ataque_furtivo",
                "cacador_flecha_precisa",
                "curandeiro_chama_sagrada",
                "berserker_golpe_selvagem",
                "samurai_corte_iaijutsu",
                "monge_rajada_de_punhos",
                "bardo_nota_cortante",
            }

            # -----------------------------------------
            # 🔮 LÊ AS SKILLS DO JOGADOR
            # -----------------------------------------

            skills_q6 = pdata.get(
                "skills",
                {}
            ) or {}

            if not isinstance(
                skills_q6,
                dict
            ):
                skills_q6 = {}


            # -----------------------------------------
            # 🔍 VERIFICA SE ALGUMA SKILL INICIAL
            # JÁ FOI REALMENTE DESBLOQUEADA
            # -----------------------------------------

            possui_skill_q6 = False

            for skill_id in SKILLS_INICIAIS_Q6:

                if skill_id not in skills_q6:
                    continue

                dados_skill = skills_q6.get(
                    skill_id
                )

                # Formato moderno:
                #
                # "monge_rajada_de_punhos": {
                #     "unlocked": True,
                #     ...
                # }
                if isinstance(
                    dados_skill,
                    dict
                ):

                    if dados_skill.get(
                        "unlocked",
                        True
                    ):
                        possui_skill_q6 = True
                        break

                # Compatibilidade com formatos antigos
                else:
                    possui_skill_q6 = True
                    break


            # -----------------------------------------
            # 📜 LÊ O ESTADO ATUAL DA Q6
            # -----------------------------------------

            quests_q6 = pdata.get(
                "quests",
                {}
            ) or {}

            if not isinstance(
                quests_q6,
                dict
            ):
                quests_q6 = {}

            dados_q6 = quests_q6.get(
                "q6_selene_grimorio",
                {}
            ) or {}

            if isinstance(
                dados_q6,
                dict
            ):
                status_q6 = dados_q6.get(
                    "status"
                )
            else:
                status_q6 = None


            # -----------------------------------------
            # ✅ CORRIGE A CONTA ANTIGA
            # -----------------------------------------

            if (
                possui_skill_q6
                and status_q6 != "resgatada"
            ):

                users_collection.update_one(
                    {
                        "_id": pdata["_id"]
                    },
                    {
                        "$set": {
                            "quests.q6_selene_grimorio.status":
                                "resgatada"
                        }
                    }
                )


                # -------------------------------------
                # ⚡ CORRIGE TAMBÉM O pdata DESTA
                # MESMA REQUISIÇÃO.
                #
                # Assim não precisa carregar o perfil
                # duas vezes para o Diário perceber.
                # -------------------------------------

                if not isinstance(
                    pdata.get("quests"),
                    dict
                ):
                    pdata["quests"] = {}

                if not isinstance(
                    pdata["quests"].get(
                        "q6_selene_grimorio"
                    ),
                    dict
                ):
                    pdata["quests"][
                        "q6_selene_grimorio"
                    ] = {}

                pdata["quests"][
                    "q6_selene_grimorio"
                ][
                    "status"
                ] = "resgatada"


                print(
                    "✅ [Q6 LEGACY] "
                    f"Missão do Grimório corrigida para "
                    f"resgatada: {pdata.get('character_name')}"
                )


        except Exception as erro_q6:

            # Essa correção nunca deve impedir
            # o perfil de carregar.
            print(
                "⚠️ [Q6 LEGACY] "
                "Falha na auto-correção:",
                erro_q6
            )
            
        # --- DADOS BÁSICOS E ATRIBUTOS ---
        lvl = int(pdata.get("level", 1))
        from modules import game_data
        try:
            xp_visual_max = int(game_data.get_xp_for_next_combat_level(lvl))
        except:
            xp_visual_max = int(200 + (100 * (lvl - 1)))
            
        classe_str = str(pdata.get("class", "aprendiz"))
        genero_str = str(pdata.get("gender", "masculino"))
        
        totals = _run_async(player_manager.get_player_total_stats(pdata))
        esquiva = int(_run_async(player_manager.get_player_dodge_chance(pdata)) * 100)
        atk_duplo = int(_run_async(player_manager.get_player_double_attack_chance(pdata)) * 100)
        
        hp_max = int(totals.get("max_hp", 100))
        mp_max = int(totals.get("max_mana", 50))
        hp_atual = min(int(pdata.get("current_hp", hp_max)), hp_max)
        mp_atual = min(int(pdata.get("current_mp", mp_max)), mp_max)

        status_formatados = {}
        for stat in ["attack", "defense", "initiative", "luck"]:
            val = int(totals.get(stat, 0))
            nome_pt = {"attack": "Ataque", "defense": "Defesa", "initiative": "Agilidade", "luck": "Sorte"}[stat]
            emoji = {"attack": "⚔️", "defense": "🛡️", "initiative": "🏃", "luck": "🍀"}[stat]
            status_formatados[stat] = {"nome": nome_pt, "emoji": emoji, "valor": val}

        # --- PROFISSÃO ---
        prof_nome, prof_lvl = "Nenhuma", 0
        prof_raw = pdata.get("profession")
        if prof_raw:
            if isinstance(prof_raw, dict):
                if "type" in prof_raw:
                    prof_nome, prof_lvl = str(prof_raw.get("type")).capitalize(), int(prof_raw.get("level", 1))
                else:
                    p_key = list(prof_raw.keys())[0]
                    prof_nome = str(p_key).capitalize()
                    prof_lvl = int(prof_raw[p_key].get("level", 1)) if isinstance(prof_raw[p_key], dict) else 1
            else:
                prof_nome, prof_lvl = str(prof_raw).capitalize(), 1

        # --- INVENTÁRIO ---
        inventario_cru = pdata.get("inventory") or {}
        inventario_formatado = []
        for item_id, qtd_ou_dict in inventario_cru.items():
            obj_item = qtd_ou_dict if isinstance(qtd_ou_dict, dict) else {}
            qtd = obj_item.get("quantity", 1) if obj_item else qtd_ou_dict
            if qtd > 0:
                base_id = obj_item.get("base_id", item_id) if obj_item else item_id
                info_item = items_data.ITEMS_DATA.get(base_id, {})
                inventario_formatado.append({
                    "id": item_id,
                    "base_id": base_id,
                    "nome": info_item.get("display_name", base_id.replace("_", " ").title()), 
                    "emoji": info_item.get("emoji", "📦"),
                    "qtd": qtd,
                    "tipo": info_item.get("type", obj_item.get("type", "material")),
                    "desc": info_item.get("description", "Um item de Eldora."),
                    "raridade": obj_item.get("rarity", info_item.get("rarity", "comum")),
                    "refino": obj_item.get("upgrade_level", 0),
                    "stats": _formatar_stats_item_para_front(obj_item),
                    "attributes": obj_item.get("attributes", {}),
                    "enchantments": obj_item.get("enchantments", {}),
                    "damage": obj_item.get("damage", {}),
                    "durability": obj_item.get("durability")
                })
        inventario_formatado.sort(key=lambda x: x["qtd"], reverse=True)

        # --- EQUIPAMENTOS ---
        equip_cru = pdata.get("equipment") or {}
        equip_tools_cru = pdata.get("equipment_tools") or {}
        inventario_cru = pdata.get("inventory") or {}

        if not isinstance(equip_cru, dict):
            equip_cru = {}

        if not isinstance(equip_tools_cru, dict):
            equip_tools_cru = {}

        equip_formatado = []

        TOOL_PROF_EMOJI = {
            "lenhador": "🪓",
            "minerador": "⛏️",
            "colhedor": "🌾",
            "esfolador": "🗡️",
            "alquimista": "🧪",
            "ferreiro": "🔨",
            "armeiro": "⚒️",
            "alfaiate": "🧵",
            "joalheiro": "💎",
            "curtidor": "🧴",
            "fundidor": "🔥",
        }

        TOOL_PROF_LABEL = {
            "lenhador": "Ferramenta de Lenhador",
            "minerador": "Ferramenta de Minerador",
            "colhedor": "Ferramenta de Colhedor",
            "esfolador": "Ferramenta de Esfolador",
            "alquimista": "Ferramenta de Alquimista",
            "ferreiro": "Ferramenta de Ferreiro",
            "armeiro": "Ferramenta de Armeiro",
            "alfaiate": "Ferramenta de Alfaiate",
            "joalheiro": "Ferramenta de Joalheiro",
            "curtidor": "Ferramenta de Curtidor",
            "fundidor": "Ferramenta de Fundidor",
        }

        def _norm_prof_key_api(valor):
            txt = str(valor or "").strip().lower()
            txt = (
                txt.replace("á", "a")
                   .replace("à", "a")
                   .replace("ã", "a")
                   .replace("â", "a")
                   .replace("é", "e")
                   .replace("ê", "e")
                   .replace("í", "i")
                   .replace("ó", "o")
                   .replace("ô", "o")
                   .replace("õ", "o")
                   .replace("ú", "u")
                   .replace("ç", "c")
            )
            return txt

        def _slot_vazio(slot, emoji, nome):
            return {
                "slot": slot,
                "emoji": emoji,
                "nome": nome,
                "icon": emoji,
                "vazio": True
            }

        # 1. Equipamentos normais.
        # O slot antigo "tool" é ignorado aqui, porque agora ferramentas
        # aparecem em slots dinâmicos por profissão.
        for slot in SLOT_ORDER:
            if slot == "tool":
                continue

            item_uid = equip_cru.get(slot)

            if item_uid and item_uid in inventario_cru:
                obj_item = inventario_cru[item_uid]

                if not isinstance(obj_item, dict):
                    equip_formatado.append(_slot_vazio(slot, SLOT_EMOJI.get(slot, "🔲"), "Vazio"))
                    continue

                base_id = obj_item.get("base_id", item_uid)
                info_item = items_data.ITEMS_DATA.get(base_id, {})
                tipo_item = (
                    info_item.get("type")
                    or obj_item.get("type")
                    or obj_item.get("tipo")
                    or "equipamento"
                )

                equip_formatado.append({
                    "slot": slot,
                    "id": item_uid,
                    "uid": item_uid,
                    "base_id": base_id,
                    "tipo": tipo_item,
                    "emoji": SLOT_EMOJI.get(slot, "🔲"),
                    "nome": info_item.get("display_name", obj_item.get("display_name", base_id.replace("_", " ").title())),
                    "icon": info_item.get("emoji", obj_item.get("emoji", "📦")),
                    "vazio": False,
                    "raridade": obj_item.get("rarity", info_item.get("rarity", "comum")),
                    "refino": obj_item.get("upgrade_level", obj_item.get("refino", 0)),
                    "upgrade_level": obj_item.get("upgrade_level", 0),
                    "stats": _formatar_stats_item_para_front(obj_item),
                    "attributes": obj_item.get("attributes", {}),
                    "enchantments": obj_item.get("enchantments", {}),
                    "damage": obj_item.get("damage", {}),
                    "desc": info_item.get("description", obj_item.get("description", "Um item de Eldora.")),
                    "durability": obj_item.get("durability")
                })
            else:
                equip_formatado.append(_slot_vazio(slot, SLOT_EMOJI.get(slot, "🔲"), "Vazio"))

        # 2. Descobre profissões liberadas.
        profissoes_liberadas = {}

        learned_raw = pdata.get("learned_professions") or {}
        if isinstance(learned_raw, dict):
            for p_key, p_info in learned_raw.items():
                pk = _norm_prof_key_api(p_key)
                if pk:
                    profissoes_liberadas[pk] = p_info if isinstance(p_info, dict) else {"key": pk}

        prof_atual = pdata.get("profession") or {}
        if isinstance(prof_atual, dict):
            pk = _norm_prof_key_api(prof_atual.get("key") or prof_atual.get("type"))
            if pk and pk not in profissoes_liberadas:
                profissoes_liberadas[pk] = prof_atual

        # 3. Compatibilidade: se ainda existir equipment["tool"], tenta encaixar
        # visualmente no slot correto da profissão.
        legacy_tool_uid = equip_cru.get("tool")
        if legacy_tool_uid and legacy_tool_uid in inventario_cru:
            legacy_item = inventario_cru.get(legacy_tool_uid)
            if isinstance(legacy_item, dict):
                legacy_base = legacy_item.get("base_id", legacy_tool_uid)
                legacy_info = items_data.ITEMS_DATA.get(legacy_base, {})
                legacy_type = _norm_prof_key_api(
                    legacy_info.get("tool_type")
                    or legacy_item.get("tool_type")
                )

                if legacy_type and not equip_tools_cru.get(legacy_type):
                    equip_tools_cru[legacy_type] = legacy_tool_uid

        # 4. Cria um slot de ferramenta para cada profissão liberada.
        for prof_key in sorted(profissoes_liberadas.keys()):
            slot_tool = f"tool_{prof_key}"
            item_uid = equip_tools_cru.get(prof_key)
            emoji_tool = TOOL_PROF_EMOJI.get(prof_key, "🛠️")
            nome_slot = TOOL_PROF_LABEL.get(prof_key, f"Ferramenta de {prof_key.capitalize()}")

            if item_uid and item_uid in inventario_cru:
                obj_item = inventario_cru[item_uid]

                if not isinstance(obj_item, dict):
                    equip_formatado.append(_slot_vazio(slot_tool, emoji_tool, nome_slot))
                    continue

                base_id = obj_item.get("base_id", item_uid)
                info_item = items_data.ITEMS_DATA.get(base_id, {})

                equip_formatado.append({
                    "slot": slot_tool,
                    "slot_profissao": prof_key,
                    "id": item_uid,
                    "uid": item_uid,
                    "base_id": base_id,
                    "tipo": "tool",
                    "emoji": emoji_tool,
                    "nome": info_item.get("display_name", obj_item.get("display_name", base_id.replace("_", " ").title())),
                    "icon": info_item.get("emoji", obj_item.get("emoji", emoji_tool)),
                    "vazio": False,
                    "raridade": obj_item.get("rarity", info_item.get("rarity", "comum")),
                    "refino": obj_item.get("upgrade_level", obj_item.get("refino", 0)),
                    "upgrade_level": obj_item.get("upgrade_level", 0),
                    "stats": _formatar_stats_item_para_front(obj_item),
                    "attributes": obj_item.get("attributes", {}),
                    "enchantments": obj_item.get("enchantments", {}),
                    "damage": obj_item.get("damage", {}),
                    "desc": info_item.get("description", obj_item.get("description", nome_slot)),
                    "durability": obj_item.get("durability"),
                    "tool_type": prof_key,
                    "tier": info_item.get("tier", obj_item.get("tier", 1)),
                    "tool_tier": info_item.get("tier", obj_item.get("tier", 1))
                })
            else:
                equip_formatado.append({
                    "slot": slot_tool,
                    "slot_profissao": prof_key,
                    "emoji": emoji_tool,
                    "nome": nome_slot,
                    "icon": emoji_tool,
                    "tipo": "tool",
                    "vazio": True,
                    "tool_type": prof_key
                })

        # --- 🎭 COSMÉTICOS (A PARTE CORRIGIDA) ---
        b_id = pdata.get("banner_customizado", "padrao")
        a_id = pdata.get("avatar_customizado", "padrao")
        letra_gen = (
            "f"
            if genero_str.lower() == "feminino"
            else "m"
        )

        skin_equipada = pdata.get("equipped_skin")

        if not skin_equipada or skin_equipada == "padrao":
            classe_skin = classe_str.lower()

            if classe_skin in ["aprendiz", "aventureiro"]:
                classe_skin = "aventureiro"

            skin_equipada = f"{classe_skin}_{letra_gen}"
        tem_passe = pdata.get("premium_tier", "free") != "free"
        
        # --- MÚLTIPLAS PROFISSÕES & BÔNUS ---
        learned_profs_raw = pdata.get("learned_professions", {})
        prof_atual_raw = pdata.get("profession", {})
        todas_profissoes = []

        # Garante que a atual também esteja na lista
        if prof_atual_raw and "key" in prof_atual_raw:
            if prof_atual_raw["key"] not in learned_profs_raw:
                learned_profs_raw[prof_atual_raw["key"]] = prof_atual_raw

        for p_key, p_data in learned_profs_raw.items():
            if not isinstance(p_data, dict): continue
            
            p_lvl = int(p_data.get("level", 1))
            p_xp = int(p_data.get("xp", 0))
            p_cat = p_data.get("category", "gathering")
            p_nome = p_data.get("display_name", p_key.capitalize())
            
            xp_necessario = 40 + (25 * (p_lvl - 1)) + (8 * ((p_lvl - 1) ** 2))
            
            # Textos dinâmicos dos bônus!
            if p_cat == "gathering":
                bonus_txt = f"🎯 +{p_lvl // 10} Drop Fixo | ✨ {p_lvl * 0.5:.1f}% Chance Duplo"
            else:
                bonus_txt = f"⏱️ -{p_lvl * 0.5:.1f}% Tempo de Forja"
                
            todas_profissoes.append({
                "key": p_key,
                "nome": p_nome,
                "level": p_lvl,
                "xp": p_xp,
                "xp_max": xp_necessario,
                "categoria": p_cat,
                "bonus": bonus_txt
            })
            
        todas_profissoes.sort(key=lambda x: x["level"], reverse=True)

        # Envia todas as listas de desbloqueio para o JavaScript[cite: 4, 5]
        return jsonify({
            "is_vip": tem_passe,
            "nome": pdata.get("character_name", "Aventureiro"), 
            "level": lvl, "gold": pdata.get("gold", 0), "gems": pdata.get("gems", 0),
            "classe": classe_str.capitalize(),
            "gender": genero_str, 
            "xp": int(pdata.get("xp", 0)), "xp_max": xp_visual_max,
            "hp_atual": hp_atual, "hp_max": hp_max, 
            "mp_atual": mp_atual, "mp_max": mp_max,
            "energy": pdata.get("energy", 0), "pontos_livres": pdata.get("stat_points", 0), 
            
            "avatar": f"https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/avatares/avatar_padrao_{letra_gen}.png",
            
            # 👇 LISTAS DE DESBLOQUEIO ESSENCIAIS 👇
            "unlocked_skins": pdata.get("unlocked_skins") or [], 
            "unlocked_banners": pdata.get("unlocked_banners") or [],
            "unlocked_avatars": pdata.get("unlocked_avatars") or [], # 👈 O Panda está aqui!
            
            # Seleções atuais
            "avatar_customizado": a_id, 
            "banner_customizado": b_id,        
            "equipped_skin": skin_equipada,
            "profession": pdata.get("profession"),
            "learned_professions": pdata.get("learned_professions", {}),
            "lista_profissoes": todas_profissoes,
            "quests": pdata.get("quests", {}),
            "status": status_formatados,
            "inventario": inventario_formatado, 
            "equipamentos": equip_formatado,
            "equipment_tools": equip_tools_cru,
            "esquiva": esquiva, "atk_duplo": atk_duplo, 
            "prof_nome": prof_nome, "prof_lvl": prof_lvl
        })
        
        
    except Exception as e: 
        import traceback
        traceback.print_exc()
        return jsonify({"erro": f"Erro interno Python: {str(e)}"}), 400
        
# ==========================================
# 2. RESTO DAS ROTAS MANTIDAS
# ==========================================


@webapp_bp.route('/api/personagem/distribuir_ponto', methods=['POST'])
def api_distribuir_ponto():
    try:
        data = request.json or {}

        from modules import player_manager
        from modules.player.combat_stats import sync_combat_stats_to_db

        user_id = data.get("user_id")
        stat_alvo = str(data.get("stat") or "").strip().lower()

        stats_validos = {"attack", "defense", "initiative", "luck"}

        if stat_alvo not in stats_validos:
            return jsonify({"erro": "Atributo inválido."}), 400

        busca_id = ObjectId(user_id) if len(str(user_id)) == 24 else int(user_id)
        pdata = users_collection.find_one({"_id": busca_id})

        if not pdata:
            return jsonify({"erro": "Personagem não encontrado."}), 404

        pontos_livres = int(pdata.get("stat_points", 0) or 0)

        if pontos_livres <= 0:
            return jsonify({"erro": "Você não tem pontos livres!"}), 400

        inv = pdata.get("invested", {}) or {}

        if not isinstance(inv, dict):
            inv = {}

        pontos_ja_investidos = int(inv.get(stat_alvo, 0) or 0)

        # REGRA SIMPLES:
        # 1 clique = gasta 1 ponto livre
        # 1 clique = adiciona +1 no investimento
        custo_do_ponto = 1
        novos_pontos_livres = pontos_livres - custo_do_ponto
        novo_investido = pontos_ja_investidos + 1

        inv[stat_alvo] = novo_investido

        pdata["invested"] = inv
        pdata["stat_points"] = novos_pontos_livres

        # CRÍTICO:
        # salva invested/stat_points ANTES de sincronizar status,
        # porque sync_combat_stats_to_db não salva esses dois campos.
        users_collection.update_one(
            {"_id": busca_id},
            {
                "$set": {
                    "invested": inv,
                    "stat_points": novos_pontos_livres
                }
            }
        )

        # Agora recalcula e salva os status finais.
        _run_async(sync_combat_stats_to_db(str(busca_id), pdata))

        # Limpa cache, se existir.
        try:
            from modules.player.core import clear_player_cache

            _run_async(clear_player_cache(busca_id))
            _run_async(clear_player_cache(str(busca_id)))

        except Exception:
            pass

        pdata_atualizado = users_collection.find_one({"_id": busca_id}) or pdata

        totals = _run_async(player_manager.get_player_total_stats(pdata_atualizado))
        esquiva = int(_run_async(player_manager.get_player_dodge_chance(pdata_atualizado)) * 100)
        atk_duplo = int(_run_async(player_manager.get_player_double_attack_chance(pdata_atualizado)) * 100)

        nomes = {
            "attack": "Ataque",
            "defense": "Defesa",
            "initiative": "Agilidade",
            "luck": "Sorte"
        }

        emojis = {
            "attack": "⚔️",
            "defense": "🛡️",
            "initiative": "🏃",
            "luck": "🍀"
        }

        status_formatados = {}

        for stat in ["attack", "defense", "initiative", "luck"]:
            status_formatados[stat] = {
                "nome": nomes[stat],
                "emoji": emojis[stat],
                "valor": int(totals.get(stat, 0) or 0)
            }

        hp_max = int(totals.get("max_hp", 100) or 100)
        mp_max = int(totals.get("max_mana", 50) or 50)

        hp_atual = min(int(pdata_atualizado.get("current_hp", hp_max) or hp_max), hp_max)
        mp_atual = min(int(pdata_atualizado.get("current_mp", mp_max) or mp_max), mp_max)

        return jsonify({
            "sucesso": True,
            "stat": stat_alvo,
            "custo": custo_do_ponto,
            "investido": novo_investido,
            "pontos_livres": novos_pontos_livres,
            "status": status_formatados,
            "esquiva": esquiva,
            "atk_duplo": atk_duplo,
            "hp_atual": hp_atual,
            "hp_max": hp_max,
            "mp_atual": mp_atual,
            "mp_max": mp_max
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": str(e)}), 500
    
@webapp_bp.route('/api/personagem/equipar', methods=['POST'])
def api_equipar_item():
    try:
        from modules.player.inventory import equip_unique_item_for_user
        sucesso, msg = _run_async(equip_unique_item_for_user(request.json.get("user_id"), request.json.get("item_id")))
        return jsonify({"sucesso": True, "msg": msg}) if sucesso else jsonify({"erro": msg}), 400
    except Exception as e: return jsonify({"erro": str(e)}), 500

@webapp_bp.route('/api/personagem/desequipar', methods=['POST'])
def api_desequipar_item():
    try:
        from modules.player.inventory import unequip_item_for_user
        sucesso, msg = _run_async(unequip_item_for_user(request.json.get("user_id"), request.json.get("slot")))
        return jsonify({"sucesso": True, "msg": msg}) if sucesso else jsonify({"erro": msg}), 400
    except Exception as e: return jsonify({"erro": str(e)}), 500

@webapp_bp.route('/api/personagem/equipar_pocao', methods=['POST'])
def api_equipar_pocao():
    try:
        data = request.json
        user_id = data.get("user_id")
        item_id = data.get("item_id")
        tipo = data.get("tipo") # Vai receber 'hp' ou 'mp'
        
        busca_id = ObjectId(user_id) if len(str(user_id)) == 24 else int(user_id)
        
        # Define em qual "gaveta" do banco de dados vamos guardar o nome da poção
        campo_banco = "pocao_equipada_hp" if tipo == "hp" else "pocao_equipada_mp"
        
        # Atualiza o jogador no banco de dados!
        users_collection.update_one(
            {"_id": busca_id},
            {"$set": {campo_banco: item_id}}
        )
        
        return jsonify({"sucesso": True})
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500
        
@webapp_bp.route('/api/personagem/equipar_skin', methods=['POST'])
def api_equipar_skin():
    try:
        data = request.json
        from modules import player_manager

        busca_id = ObjectId(data.get("user_id")) if len(str(data.get("user_id"))) == 24 else int(data.get("user_id"))
        pdata = users_collection.find_one({"_id": busca_id})

        if not pdata:
            return jsonify({"sucesso": False, "erro": "Herói não encontrado."}), 404

        skin_id = data.get("skin_id")

        classe_atual = str(
            pdata.get("class", "aprendiz")
        ).lower().strip()

        skins_aventureiro = {
            "aventureiro",
            "aventureiro_m",
            "aventureiro_f",
            "aventureiro_masculino",
            "aventureiro_feminino"
        }

        if (
            classe_atual not in {"aprendiz", "aventureiro"} and
            str(skin_id or "").lower() in skins_aventureiro
        ):
            return jsonify({
                "sucesso": False,
                "erro": "A aparência de Aventureiro não pode mais ser usada após escolher uma classe."
            }), 400

        if (
            skin_id and
            skin_id not in pdata.get("unlocked_skins", [])
        ):
            return jsonify({
                "sucesso": False,
                "erro": "Você não possui esta aparência."
            }), 400

        pdata["equipped_skin"] = skin_id

        _run_async(
            player_manager.save_player_data(
                data.get("user_id"),
                pdata
            )
        )

        return jsonify({"sucesso": True})

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@webapp_bp.route('/api/mapa/objetos/<regiao_id>')
def api_mapa_objetos(regiao_id):
    try:
        mapas_config = {
            "capital_eldora": [
                {
                    "id": "estatua_pedroca",

                    "x": 30 * 32,
                    "y": 27 * 32,

                    "icone_x": 960,
                    "icone_y": 882,

                    "texto_botao": "❗",
                    "mensagem": "Foi daqui\nque tudo começou.\nAqui nasceu o sonho\nde Eldora."
                },
            ]
        }

        return jsonify(
            mapas_config.get(regiao_id, [])
        )

    except Exception as e:
        return jsonify({
            "erro": str(e)
        }), 500    
# ==========================================
# ROTAS DO PORTAL (CRIAÇÃO E SELEÇÃO DE HERÓIS)
# ==========================================
@webapp_bp.route('/api/portal/criar_conta', methods=['POST'])
def api_criar_conta():
    try:
        data = request.json
        username = data.get("username", "").strip().lower()
        password = data.get("password", "")
        tg_id = data.get("tg_id", 12345)

        if not username or len(password) < 6:
            return jsonify({"sucesso": False, "erro": "Usuário ou senha inválidos."})

        # Verifica se o nome de usuário já existe no banco
        if contas_collection.find_one({"username": username}):
            return jsonify({"sucesso": False, "erro": "Esse nome de conta já está em uso!"})

        # Cria a conta mestre no MongoDB
        nova_conta = {
            "username": username,
            "password_hash": generate_password_hash(password),
            "telegram_id": tg_id,
            "criado_em": datetime.utcnow()
        }
        contas_collection.insert_one(nova_conta)
        
        return jsonify({"sucesso": True})
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500


@webapp_bp.route('/api/portal/login', methods=['POST'])
def api_login_conta():
    try:
        data = request.json
        username = data.get("username", "").strip().lower()
        password = data.get("password", "")

        # Busca a conta mestre no banco
        conta = contas_collection.find_one({"username": username})
        
        # Valida a senha
        if not conta or not check_password_hash(conta["password_hash"], password):
            return jsonify({"sucesso": False, "erro": "Usuário ou senha incorretos."})

        # Se logou com sucesso, busca todos os personagens vinculados a essa conta!
        personagens_db = list(users_collection.find({"conta_mestre": username}))
        
        lista_personagens = []
        for p in personagens_db:
            lista_personagens.append({
                "id": str(p["_id"]),
                "nome": p.get("character_name", "Herói"),
                "genero": p.get("gender", "masculino"),
                "level": p.get("level", 1),
                "classe": p.get("class", "aventureiro").capitalize(),
                "avatar_customizado": p.get("avatar_customizado", "padrao")
            })

        return jsonify({"sucesso": True, "personagens": lista_personagens})
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500

@webapp_bp.route('/api/loja/comprar', methods=['POST'])
def api_loja_comprar():
    try:
        from modules.player.core import users_collection
        from modules.game_data import items as items_data  # 👈 Importa o catálogo de itens
        from bson.objectid import ObjectId
        
        data = request.json
        user_id = data.get("user_id")
        item_id = data.get("item_id")

        # 1. Pega as informações reais do item no Backend
        info_item = items_data.ITEMS_DATA.get(item_id)
        if not info_item:
            return jsonify({"erro": "Este item não existe na loja."}), 404
            
        # 2. Pega o preço real (Se não tiver preço, bota um valor absurdo para bloquear)
        preco_real = int(info_item.get("price", info_item.get("preco", 9999999)))

        # Suporte para ObjectId ou ID numérico do Telegram
        busca_id = ObjectId(user_id) if len(str(user_id)) == 24 else int(user_id) if str(user_id).isdigit() else user_id
        pdata = users_collection.find_one({"$or": [{"_id": busca_id}, {"telegram_id": busca_id}]})

        if not pdata:
            return jsonify({"erro": "Herói não encontrado no banco."}), 404

        ouro_atual = int(pdata.get("gold", 0))
        
        # 3. Usa o preço REAL para a verificação
        if ouro_atual < preco_real:
            return jsonify({"erro": f"Ouro insuficiente! Custa {preco_real} moedas."}), 400

        # Atualização do Inventário
        inventario = pdata.get("inventory", {})
        if item_id in inventario:
            if isinstance(inventario[item_id], dict):
                inventario[item_id]["quantity"] = inventario[item_id].get("quantity", 1) + 1
            else:
                inventario[item_id] += 1
        else:
            inventario[item_id] = {"base_id": item_id, "quantity": 1}

        # Salva o novo saldo e o inventário
        users_collection.update_one(
            {"_id": pdata["_id"]},
            {"$set": {"gold": ouro_atual - preco_real, "inventory": inventario}}
        )

        return jsonify({"sucesso": True, "novo_ouro": ouro_atual - preco_real})
    except Exception as e:
        return jsonify({"erro": "Erro na transação: " + str(e)}), 500
    
@webapp_bp.route('/api/personagem/usar_pocao_rapida', methods=['POST'])
def api_usar_pocao_rapida():
    try:
        from modules.player.core import users_collection
        from modules.game_data.items_consumables import CONSUMABLES_DATA
        from bson.objectid import ObjectId
        from modules import player_manager
        
        data = request.json
        user_id = data.get("user_id")
        tipo_slot = data.get("tipo") # 'hp' ou 'mp'
        
        busca_id = ObjectId(user_id) if len(str(user_id)) == 24 else int(user_id)
        pdata = users_collection.find_one({"_id": busca_id})
        
        if not pdata: return jsonify({"erro": "Herói não encontrado."}), 404
            
        campo_equipado = f"pocao_equipada_{tipo_slot}"
        base_id_pocao = pdata.get(campo_equipado)
        
        if not base_id_pocao:
            return jsonify({"erro": "Vá à mochila e equipe uma poção neste slot primeiro!"}), 400
            
        inventario = pdata.get("inventory", {})
        item_uid_encontrado = None
        for uid, item_data in inventario.items():
            b_id = item_data.get("base_id", uid) if isinstance(item_data, dict) else uid
            if b_id == base_id_pocao:
                item_uid_encontrado = uid
                break
                
        if not item_uid_encontrado:
            users_collection.update_one({"_id": busca_id}, {"$unset": {campo_equipado: ""}})
            return jsonify({"erro": "Suas poções deste tipo acabaram!"}), 400
            
        info_pocao = CONSUMABLES_DATA.get(base_id_pocao, {})
        
        # 🎯 CORREÇÃO: Diferencia HP de MP para pegar o número exato do item!
        if tipo_slot == 'hp':
            cura_valor = info_pocao.get("effects", {}).get("heal", 50)
        else:
            cura_valor = info_pocao.get("effects", {}).get("mana", 100)
        
        totals = _run_async(player_manager.get_player_total_stats(pdata))
        
        if tipo_slot == 'hp':
            max_val = int(totals.get("max_hp", 100))
            atual = int(pdata.get("current_hp", max_val))
            if atual >= max_val: return jsonify({"erro": "Sua vida já está cheia!"}), 400
            novo_valor = min(atual + cura_valor, max_val)
            pdata["current_hp"] = novo_valor
            cor_hex = "#2ecc71"
        else:
            max_val = int(totals.get("max_mana", 50))
            atual = int(pdata.get("current_mp", max_val))
            if atual >= max_val: return jsonify({"erro": "Sua mana já está cheia!"}), 400
            novo_valor = min(atual + cura_valor, max_val)
            pdata["current_mp"] = novo_valor
            cor_hex = "#3498db"
            
        # Gasta a poção
        item_obj = inventario[item_uid_encontrado]
        qtd_atual = item_obj.get("quantity", item_obj) if isinstance(item_obj, dict) else item_obj
        if qtd_atual > 1:
            if isinstance(item_obj, dict): inventario[item_uid_encontrado]["quantity"] -= 1
            else: inventario[item_uid_encontrado] -= 1
        else:
            del inventario[item_uid_encontrado]
            
        pdata["inventory"] = inventario
        users_collection.update_one({"_id": busca_id}, {"$set": pdata})
        
        return jsonify({"sucesso": True, "cura": cura_valor, "cor": cor_hex})
        
    except Exception as e: return jsonify({"erro": str(e)}), 500


@webapp_bp.route('/api/personagem/usar_item', methods=['POST'])
def api_usar_item_direto():
    try:
        from modules.player.core import users_collection
        from modules.game_data import items as items_data
        from bson.objectid import ObjectId
        from modules import player_manager, profession_engine # 👈 Importa a Engine aqui!

        data = request.json
        user_id = data.get("user_id")
        item_uid = data.get("item_id")
        
        busca_id = ObjectId(user_id) if len(str(user_id)) == 24 else int(user_id)
        pdata = users_collection.find_one({"_id": busca_id})
        
        if not pdata: return jsonify({"erro": "Herói não encontrado."}), 404
            
        inventario = pdata.get("inventory", {})
        if item_uid not in inventario: return jsonify({"erro": "Item não encontrado."}), 400
            
        item_obj = inventario[item_uid]
        base_id = item_obj.get("base_id", item_uid) if isinstance(item_obj, dict) else item_uid
        quantidade = item_obj.get("quantity", item_obj) if isinstance(item_obj, dict) else item_obj
        info_item = items_data.ITEMS_DATA.get(base_id, {})
        
        # 👇 1. SE CLICOU NO PERGAMINHO: Aciona o reparo em massa!
        if base_id in ["pergaminho_durabilidade", "pergaminho_de_reparo"]:
            res = _run_async(profession_engine.restore_all_equipped_durability(pdata))
            
            if "error" in res:
                return jsonify({"erro": res["error"]}), 400
                
            # Salva no banco porque a engine alterou a durabilidade e já gastou o pergaminho
            _run_async(player_manager.save_player_data(str(busca_id), pdata))
            return jsonify({"sucesso": True, "msg": res.get("message", "Itens reparados com sucesso!")})

        # ==================================================
        # ✨ ELIXIR TEMPORÁRIO DE XP
        # ==================================================

        efeito_uso = (
            info_item.get(
                "on_use",
                {}
            )
            or {}
        )

        if (
            efeito_uso.get("effect")
            == "xp_boost"
        ):

            from datetime import (
                datetime,
                timezone,
                timedelta,
            )

            multiplicador = float(
                efeito_uso.get(
                    "multiplier",
                    2.0,
                )
            )

            duracao = int(
                efeito_uso.get(
                    "duration_seconds",
                    600,
                )
            )

            agora = datetime.now(
                timezone.utc
            )

            inicio = agora

            boost_atual = (
                pdata.get(
                    "xp_boost"
                )
                or {}
            )

            if isinstance(
                boost_atual,
                dict
            ):

                expiracao_atual = (
                    boost_atual.get(
                        "expires_at"
                    )
                )

                if expiracao_atual:

                    try:

                        dt_atual = (
                            datetime
                            .fromisoformat(
                                str(
                                    expiracao_atual
                                ).replace(
                                    "Z",
                                    "+00:00",
                                )
                            )
                        )

                        if dt_atual.tzinfo is None:
                            dt_atual = (
                                dt_atual.replace(
                                    tzinfo=
                                        timezone.utc
                                )
                            )

                        if dt_atual > agora:
                            inicio = dt_atual

                    except Exception:
                        pass

            expiracao = (
                inicio
                + timedelta(
                    seconds=duracao
                )
            )

            # Gasta exatamente uma unidade.
            if quantidade > 1:

                if isinstance(
                    item_obj,
                    dict
                ):
                    inventario[
                        item_uid
                    ][
                        "quantity"
                    ] -= 1

                else:
                    inventario[
                        item_uid
                    ] -= 1

            else:
                del inventario[
                    item_uid
                ]

            novo_boost = {
                "multiplier":
                    multiplicador,

                "expires_at":
                    expiracao
                    .isoformat(),
            }

            users_collection.update_one(
                {
                    "_id":
                        busca_id
                },
                {
                    "$set": {
                        "inventory":
                            inventario,

                        "xp_boost":
                            novo_boost,
                    }
                }
            )

            return jsonify({
                "sucesso": True,
                "msg": (
                    "✨ Experiência dobrada "
                    f"por {duracao // 60} minutos!"
                ),
                "xp_boost":
                    novo_boost,
            })


        # 👇 2. SE FOR OUTRO ITEM (Caixas, Baús, etc):
        msg_sucesso = f"Você usou {info_item.get('display_name', 'o item')}!"
            
        # Gasta o item normalmente
        if quantidade > 1:
            if isinstance(item_obj, dict): inventario[item_uid]["quantity"] -= 1
            else: inventario[item_uid] -= 1
        else:
            del inventario[item_uid]
            
        users_collection.update_one({"_id": busca_id}, {"$set": {"inventory": inventario}})
        return jsonify({"sucesso": True, "msg": msg_sucesso})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": "A magia falhou: " + str(e)}), 500

# ==========================================================
# 🧙‍♀️ BRUXA DA FLORESTA — ALQUIMIA
# ==========================================================

@webapp_bp.route(
    '/api/bruxa/receitas/<user_id>',
    methods=['GET']
)
def api_bruxa_receitas(user_id):

    try:
        from bson.objectid import ObjectId

        from modules.player.core import (
            users_collection
        )

        from modules.alchemy.bruxa_pocoes import (
            listar_receitas
        )

        busca_id = (
            ObjectId(user_id)
            if len(str(user_id)) == 24
            else int(user_id)
        )

        pdata = users_collection.find_one({
            "_id": busca_id
        })

        if not pdata:
            return jsonify({
                "success": False,
                "error": "Herói não encontrado."
            }), 404

        return jsonify({
            "success": True,
            "receitas": listar_receitas(
                pdata
            )
        })

    except Exception as e:

        import traceback
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@webapp_bp.route(
    '/api/bruxa/fabricar',
    methods=['POST']
)
def api_bruxa_fabricar():

    try:
        from bson.objectid import ObjectId

        from modules.player.core import (
            users_collection
        )

        from modules.alchemy.bruxa_pocoes import (
            fabricar
        )

        dados = request.json or {}

        user_id = dados.get(
            "user_id"
        )

        receita_id = dados.get(
            "receita_id"
        )

        if not user_id or not receita_id:
            return jsonify({
                "success": False,
                "error": "Dados incompletos."
            }), 400

        busca_id = (
            ObjectId(user_id)
            if len(str(user_id)) == 24
            else int(user_id)
        )

        pdata = users_collection.find_one({
            "_id": busca_id
        })

        if not pdata:
            return jsonify({
                "success": False,
                "error": "Herói não encontrado."
            }), 404

        # A gravação só será aceita se ouro e inventário não mudaram.
        estado_original = {
            "_id": busca_id,
            "inventory": copy.deepcopy(pdata.get("inventory", {"$exists": False})),
            "gold": pdata.get("gold", {"$exists": False}),
        }

        resultado = fabricar(
            pdata,
            receita_id
        )

        if not resultado.get(
            "success"
        ):
            return jsonify(
                resultado
            ), 400

        gravacao = users_collection.update_one(
            estado_original,
            {"$set": {"inventory": pdata.get("inventory", {})},
             "$inc": {"gold": -resultado["custo_ouro"]}},
        )
        if not gravacao.matched_count:
            return jsonify({
                "success": False,
                "error": "Seu ouro ou inventário mudou. Atualize as receitas e tente novamente.",
            }), 409

        try:
            from modules.player.core import (
                clear_player_cache
            )

            _run_async(
                clear_player_cache(
                    busca_id
                )
            )

        except Exception:
            pass

        return jsonify(
            resultado
        )

    except Exception as e:

        import traceback
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@webapp_bp.route('/api/mercado/criar_anuncio', methods=['POST'])
def api_criar_anuncio():
    from modules.player.core import users_collection
    try:
        dados = request.get_json(silent=True) or {}
        if not isinstance(dados, dict):
            return jsonify({"sucesso": False, "erro": "Dados inválidos."}), 400
        anuncio = market_manager.create_listing(
            seller_id=dados.get('user_id'), item_id=dados.get('item_id'),
            total_price=dados.get('preco'), quantity=dados.get('quantidade', 1),
            currency=dados.get('moeda', 'ouro'),
        )
        player_data = {"character_name": anuncio['seller_name']}
        base_id = anuncio['item']['base_id']
        qtd_desejada = anuncio['quantity']
        preco_total = anuncio['total_price']
        moeda = anuncio['currency']

        # 👇 NOTIFICAÇÃO 100% BLINDADA 👇
        try:
            from flask import current_app
            from modules.game_data import items as items_data
            from datetime import datetime
            
            nome_vendedor = player_data.get("character_name", "Aventureiro")
            info_real = items_data.ITEMS_DATA.get(base_id, {})
            nome_item = info_real.get("display_name", base_id.replace("_", " ").title())
            if qtd_desejada > 1: nome_item += f" (x{qtd_desejada})"
            
            moeda_txt = "Gemas 💎" if moeda in ["gema", "gemas"] else "Ouro 🪙"
            texto_anuncio = f"O mercador <b>{nome_vendedor}</b> anunciou <b>{nome_item}</b> por {preco_total} {moeda_txt}!"
            
            # Força salvar no banco correto do Chat (eldora_bot)
            db_certo = users_collection.database.client["eldora_bot"]
            db_certo["chat_historico"].insert_one({
                "remetente": "Sistema", "texto": texto_anuncio,
                "alvo": "global", "tipo": "mercado", "data_envio": datetime.utcnow()
            })
            
            # Puxa o SocketIO verdadeiro sem dar reload no app
            sio = current_app.extensions.get('socketio')
            if sio:
                sio.emit('novaMensagemChat', {"texto": texto_anuncio, "tipo": "mercado", "remetente": "Sistema"})
        except Exception as e:
            print(f"Erro ao emitir msg de mercado: {e}")
        # 👆 FIM DA NOTIFICAÇÃO 👆

        return jsonify({"sucesso": True, "mensagem": "Item anunciado com sucesso no Mercado Central!"})

    except Exception as e:
        return jsonify({"sucesso": False, "erro": f"A forja do anúncio falhou: {str(e)}"})
    
# ==========================================
# 2. ROTA: VITRINE DO MERCADO (RECONHECIMENTO DE ITENS)
# ==========================================
@webapp_bp.route('/api/mercado/listar', methods=['GET'])
def api_listar_mercado():
    try:
        # Puxa todas as vendas ativas direto pelo cérebro do gerenciador
        anuncios = market_manager.list_active(page_size=50)
        
        lista_ouro = []
        lista_gemas = []
        
        for anuncio in anuncios:
            anuncio['_id'] = str(anuncio['_id'])
            
            item_payload = anuncio.get('item', {})
            base_id = item_payload.get('base_id')
            
            # Se for do tipo 'unique', a ficha real do item está dentro da chave 'item'
            if item_payload.get("type") == "unique" and "item" in item_payload:
                base_id = item_payload["item"].get("base_id", base_id)

            quantidade = anuncio.get('quantity', 1)
            unit_price = anuncio.get('unit_price', 0)
            precio_total = unit_price * quantidade # O JS espera o preço total do bloco
            
            # Consulta o catálogo do sistema para pegar a tradução em português
            info_real = items_data.ITEMS_DATA.get(base_id, {})
            
            nome = info_real.get('display_name') or base_id.replace("_", " ").title()
            tipo_item = info_real.get('type') or 'material'
            
            if quantidade > 1:
                nome = f"{nome} (x{quantidade})"
                
            detalhe = copy.deepcopy(item_payload.get('item', {}))
            detalhe.update({
                "base_id": base_id, "nome": nome, "tipo": tipo_item,
                "raridade": detalhe.get('rarity', info_real.get('rarity', 'comum')),
                "refino": detalhe.get('upgrade_level', detalhe.get('refino', 0)),
                "classe": detalhe.get('class_req', info_real.get('class_req', info_real.get('class', 'Livre'))),
                "descricao": info_real.get('description', detalhe.get('description', '')),
                "stats": _formatar_stats_item_para_front(detalhe or info_real),
            })
            card_anuncio = {
                "id_venda": anuncio['_id'],
                "vendedor": anuncio.get('seller_name', 'Desconhecido'),
                "nome_item": nome,
                "item_id": base_id,  
                "tipo": tipo_item,   
                "preco": precio_total,
                "quantidade": quantidade,
                "preco_unitario": precio_total / max(1, quantidade),
                "item_details": detalhe,
                "moeda": anuncio.get('currency', 'ouro'), # market_manager opera por Ouro por padrão
                "seller_id": str(anuncio.get('seller_id', '')) # Essencial pro botão Cancelar aparecer!
            }
            
            if card_anuncio['moeda'] == 'ouro':
                lista_ouro.append(card_anuncio)
            else:
                lista_gemas.append(card_anuncio)
                
        return jsonify(_json_seguro_mongo({"sucesso": True, "ouro": lista_ouro, "gemas": lista_gemas}))
    except Exception as e:
        return jsonify({"sucesso": False, "erro": "Erro ao sintonizar a vitrine real."})

# ==========================================
# 3. ROTA: COMPRAR ITEM (USANDO O MOTOR DO MANAGER)
# ==========================================
@webapp_bp.route('/api/mercado/comprar', methods=['POST'])
def api_comprar_mercado():
    from modules import market_manager # Importe caso precise
    dados = request.get_json(silent=True) or {}
    if not isinstance(dados, dict):
        return jsonify({"sucesso": False, "erro": "Dados inválidos."}), 400
    comprador_id = dados.get('user_id')
    venda_id = dados.get('id_venda')

    if not comprador_id or not venda_id:
        return jsonify({"sucesso": False, "erro": "Dados de transação inválidos."})

    try:
        anuncio = market_manager.get_listing(venda_id)
        if not anuncio:
            return jsonify({"sucesso": False, "erro": "Este leilão já foi encerrado ou não existe."})

        _run_async(market_manager.purchase_listing(
            buyer_id=comprador_id,
            listing_id=venda_id,
            quantity=None
        ))

        # 👇 NOTIFICAÇÃO 100% BLINDADA 👇
        try:
            from flask import current_app
            from modules.player.core import users_collection
            from bson.objectid import ObjectId
            from datetime import datetime
            
            busca_comp_id = ObjectId(comprador_id) if len(str(comprador_id)) == 24 else int(comprador_id)
            comprador = users_collection.find_one({"_id": busca_comp_id})
            nome_comprador = comprador.get("character_name", "Alguém") if comprador else "Alguém"
            
            texto_anuncio = f"O herói <b>{nome_comprador}</b> comprou rapidamente um item no Mercado Central!"
            
            # Força salvar no banco correto
            db_certo = users_collection.database.client["eldora_bot"]
            db_certo["chat_historico"].insert_one({
                "remetente": "Sistema", "texto": texto_anuncio,
                "alvo": "global", "tipo": "mercado", "data_envio": datetime.utcnow()
            })
            
            sio = current_app.extensions.get('socketio')
            if sio:
                sio.emit('novaMensagemChat', {"texto": texto_anuncio, "tipo": "mercado", "remetente": "Sistema"})
        except Exception as e:
            print(f"Erro ao emitir msg de compra: {e}")

        return jsonify({"sucesso": True, "mensagem": "Compra realizada e computada com sucesso!"})

    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)})
    
# ==========================================
# 4. ROTA: CANCELAR VENDA (BLINDADA PARA ANÚNCIOS ANTIGOS)
# ==========================================
@webapp_bp.route('/api/mercado/cancelar', methods=['POST'])
def api_cancelar_mercado():
    from modules.player.core import users_collection
    try:
        dados = request.get_json(silent=True) or {}
        if not isinstance(dados, dict):
            return jsonify({"sucesso": False, "erro": "Dados inválidos."}), 400
        anuncio = _run_async(market_manager.cancel_listing(
            dados.get('id_venda'), seller_id=dados.get('user_id')
        ))
        jogador = {"character_name": anuncio.get('seller_name', 'Aventureiro')}

        # 👇 NOTIFICAÇÃO 100% BLINDADA 👇
        try:
            from flask import current_app
            from datetime import datetime
            
            nome_vendedor = jogador.get("character_name", "Aventureiro")
            texto_anuncio = f"O mercador <b>{nome_vendedor}</b> retirou o seu anúncio das vitrines."
            
            # Força salvar no banco correto
            db_certo = users_collection.database.client["eldora_bot"]
            db_certo["chat_historico"].insert_one({
                "remetente": "Sistema", "texto": texto_anuncio,
                "alvo": "global", "tipo": "mercado", "data_envio": datetime.utcnow()
            })
            
            sio = current_app.extensions.get('socketio')
            if sio:
                sio.emit('novaMensagemChat', {"texto": texto_anuncio, "tipo": "mercado", "remetente": "Sistema"})
        except Exception as e:
            print(f"Erro ao emitir msg de cancelamento: {e}")

        return jsonify({"sucesso": True})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"sucesso": False, "erro": f"Falha na devolução: {str(e)}"})
                     
@webapp_bp.route('/api/personagem/reparar_ferramenta', methods=['POST'])
def api_reparar_ferramenta():
    try:
        from modules.player.core import users_collection
        from bson.objectid import ObjectId
        from modules import profession_engine, player_manager

        data = request.json
        user_id = data.get("user_id")
        item_uid = data.get("item_id")

        busca_id = ObjectId(user_id) if len(str(user_id)) == 24 else int(user_id)
        pdata = users_collection.find_one({"_id": busca_id})

        if not pdata: return jsonify({"error": "Herói não encontrado."}), 404

        # Chama a sua engine de profissões para recuperar a durabilidade do item alvo
        resultado = _run_async(profession_engine.restore_durability(pdata, item_uid))

        if "error" in resultado:
            return jsonify({"success": False, "error": resultado["error"]})

        # Salva a barra de durabilidade cheia no banco de dados!
        _run_async(player_manager.save_player_data(str(busca_id), pdata))

        return jsonify({"success": True, "msg": "Equipamento restaurado com sucesso!"})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500
 
              
@webapp_bp.route('/api/portal/criar_personagem', methods=['POST'])
def api_criar_personagem():
    try:
        from modules.player.queries import create_new_player, _normalize_char_name
        from bson import ObjectId
        data = request.json
        
        # Pega de qual conta mestre esse personagem pertence
        conta_mestre = data.get("conta", "").strip().lower()
        nome = data.get("nome", "").strip()
        genero = data.get("genero", "masculino")
        
        if not conta_mestre:
            return jsonify({"erro": "Sessão da conta mestra não encontrada!"}), 400

        if not nome: 
            return jsonify({"erro": "O nome do herói é obrigatório!"}), 400

        # Valida se o nome do personagem já existe no reino todo
        nome_norm = _normalize_char_name(nome)
        if users_collection.find_one({"name_normalized": nome_norm}): 
            return jsonify({"erro": "Este nome já está em uso no reino!"}), 400

        # Gera o ID único do PERSONAGEM
        novo_id = ObjectId()
        
        # Chama a sua função oficial para criar a ficha do RPG
        _run_async(create_new_player(
            user_id=novo_id, 
            character_name=nome, 
            username=conta_mestre, 
            telegram_id=12345 # Pode usar um genérico ou puxar do request se preferir
        ))
        
        # MÁGICA: Vincula este herói à Conta Mestra!
        users_collection.update_one(
            {"_id": novo_id}, 
            {"$set": {
                "gender": genero,
                "conta_mestre": conta_mestre # <--- VINCULA À CONTA MESTRA
            }}
        )
        
        # Após criar o personagem, devolvemos a lista de personagens atualizada para o Lobby do Javascript
        personagens_db = list(users_collection.find({"conta_mestre": conta_mestre}))
        lista_atualizada = []
        for p in personagens_db:
            lista_atualizada.append({
                "id": str(p["_id"]),
                "nome": p.get("character_name", "Herói"),
                "genero": p.get("gender", "masculino"),
                "level": p.get("level", 1),
                "classe": p.get("class", "aventureiro").capitalize(),
                "avatar_customizado": p.get("avatar_customizado", "padrao")
            })
        
        return jsonify({"sucesso": True, "nova_lista_personagens": lista_atualizada})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": "Erro ao fundir a alma do herói."}), 500
            
# 👇 Nota que tirei o <int:> do caminho para ele não crashar com o "null" do Javascript
@webapp_bp.route('/api/portal/meus_personagens/<tg_id_recebido>', methods=['GET'])
def api_meus_personagens(tg_id_recebido):
    try:
        # 🛡️ MODO DESENVOLVEDOR: Proteção para testar no navegador do PC
        if not tg_id_recebido or tg_id_recebido in ["undefined", "null", "None"]:
            tg_id = 123456789
        else:
            tg_id = int(tg_id_recebido)
            
        # Busca todos os personagens do usuário
        cursor = users_collection.find({"telegram_id": tg_id})
        personagens = []
        
        for p in cursor:
            # Garante que acha o avatar ou usa um fallback
            avatar_padrao = f"aventureiro_{p.get('genero', 'masculino')}"
            avatar_equipado = p.get("cosmeticos", {}).get("avatar_equipado", avatar_padrao)
            
            personagens.append({
                "id": str(p["_id"]),
                "nome": p.get("nome", "Herói Desconhecido"),
                "classe": p.get("classe", "aventureiro").capitalize(),
                "level": p.get("level", 1),
                "avatar": avatar_equipado
            })
            
        return jsonify({"sucesso": True, "personagens": personagens})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"sucesso": False, "erro": str(e)})
    
@webapp_bp.route('/api/passe/status/<user_id>')
def status_passe(user_id):
    try:
        from modules.player.core import users_collection
        from modules.game_data.season_pass import RECOMPENSAS_PASSE
        from bson.objectid import ObjectId
        
        pdata = None
        
        # 1. Tenta buscar pelo _id do MongoDB
        try:
            if len(user_id) == 24: 
                pdata = users_collection.find_one({"_id": ObjectId(user_id)})
        except: pass

        # 2. Se não achou, tenta pelo telegram_id (convertendo para int)
        if not pdata:
            try:
                pdata = users_collection.find_one({"telegram_id": int(user_id)})
            except: pass

        if pdata:
            passe = pdata.get("passe_batalha", {"level": 1, "xp": 0, "is_premium": False})
            
            return jsonify({
                "status": {
                    "level": passe.get("level", 1),
                    "xp": passe.get("xp", 0),
                    "is_premium": passe.get("is_premium", False),
                    # 👇 ADICIONE ESTAS DUAS LINHAS 👇
                    "resgatados_free": passe.get("resgatados_free", []), 
                    "resgatados_premium": passe.get("resgatados_premium", [])
                },
                "catalogo": RECOMPENSAS_PASSE
            })
            
        return jsonify({"erro": "Jogador não encontrado"}), 404

    except Exception as e:
        print(f"❌ ERRO CRÍTICO NA API DO PASSE: {e}")
        return jsonify({"erro": str(e)}), 500
    
# Adicione no final do seu webapp_api.py

@webapp_bp.route('/api/passe/resgatar', methods=['POST'])
def resgatar_passe():
    try:
        from modules.player.core import users_collection
        from modules.game_data.season_pass import RECOMPENSAS_PASSE
        import uuid # Para gerar IDs únicos de itens
        
        dados = request.json
        user_id = dados.get('user_id')
        nivel_pedido = int(dados.get('nivel'))
        tipo_pedido = dados.get('tipo') # 'free' ou 'premium'

        busca_id = ObjectId(user_id) if len(str(user_id)) == 24 else int(user_id)
        pdata = users_collection.find_one({"_id": busca_id})

        if not pdata: return jsonify({"status": "error", "message": "Herói não encontrado"}), 404

        # 1. Pega os dados do passe (Garante consistência com o banco)
        passe = pdata.get("passe_batalha", {"level": 1, "xp": 0, "is_premium": False, "resgatados_free": [], "resgatados_premium": []})
        
        # 2. Verificações de Segurança
        if passe.get("level", 1) < nivel_pedido:
            return jsonify({"status": "error", "message": "Nível insuficiente!"}), 400
            
        if tipo_pedido == "premium" and not passe.get("is_premium"):
            return jsonify({"status": "error", "message": "Este prêmio exige o Passe Premium! 👑"}), 400

        lista_resgatados = passe.get(f"resgatados_{tipo_pedido}") or []
        if nivel_pedido in lista_resgatados:
            return jsonify({"status": "error", "message": "Você já resgatou este prêmio!"}), 400

        # 3. Identifica a Recompensa
        recompensa = RECOMPENSAS_PASSE.get(nivel_pedido, {}).get(tipo_pedido)
        if not recompensa: return jsonify({"status": "error", "message": "Prêmio não configurado."}), 404

        r_tipo = recompensa.get("tipo")
        genero = pdata.get("gender", "masculino").lower()
        inventario = pdata.get("inventory", {})

        # 4. LÓGICA DE ENTREGA REAL
        if r_tipo == "gold":
            pdata["gold"] = pdata.get("gold", 0) + recompensa.get("qtd", 0)
            
        elif r_tipo == "gems":
            pdata["gems"] = pdata.get("gems", 0) + recompensa.get("qtd", 0)

        elif r_tipo == "item":
            base_id = recompensa.get("id")
            qtd = recompensa.get("qtd", 1)
            # Entrega no formato moderno (empilhável se for material/consumível)
            encontrou = False
            for k, v in inventario.items():
                if isinstance(v, dict) and v.get("base_id") == base_id:
                    v['quantity'] = v.get('quantity', 1) + qtd
                    encontrou = True
                    break
            if not encontrou:
                inventario[base_id] = {
                    "base_id": base_id,
                    "quantity": qtd
                }
            pdata["inventory"] = inventario

        elif r_tipo == "banner":
            unlocked = pdata.get("unlocked_banners") or []
            if recompensa.get("id") not in unlocked: unlocked.append(recompensa.get("id"))
            pdata["unlocked_banners"] = unlocked

        elif r_tipo in ["avatar_dinamico", "skin_dinamica"]:
            unlocked = pdata.get("unlocked_skins") or []
            id_correto = recompensa["id_m"] if genero in ["masculino", "m"] else recompensa["id_f"]
            if id_correto not in unlocked: unlocked.append(id_correto)
            pdata["unlocked_skins"] = unlocked
            # Garante compatibilidade com avatares
            unlocked_av = pdata.get("unlocked_avatars") or []
            if id_correto not in unlocked_av: unlocked_av.append(id_correto)
            pdata["unlocked_avatars"] = unlocked_av

        # 5. Salva o progresso e o resgate
        lista_resgatados.append(nivel_pedido)
        passe[f"resgatados_{tipo_pedido}"] = lista_resgatados
        
        users_collection.update_one(
            {"_id": pdata["_id"]}, 
            {"$set": {
                "passe_batalha": passe, 
                "gold": pdata.get("gold", 0),
                "gems": pdata.get("gems", 0),
                "inventory": pdata.get("inventory", {}),
                "unlocked_skins": pdata.get("unlocked_skins", []),
                "unlocked_avatars": pdata.get("unlocked_avatars", []),
                "unlocked_banners": pdata.get("unlocked_banners", [])
            }}
        )
        return jsonify({"status": "success", "message": f"Recebeu: {recompensa.get('label')}!"})
        
    except Exception as e: 
        print(f"ERRO NO PASSE: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
@webapp_bp.route('/api/perfil/atualizar', methods=['POST'])
def atualizar_perfil_visual():
    try:
        from modules.player.core import users_collection
        from bson.objectid import ObjectId
        
        dados = request.json
        user_id = dados.get('user_id')
        
        busca_id = ObjectId(user_id) if len(str(user_id)) == 24 else int(user_id)
        
        # Prepara os dados de atualização baseados no que o JS enviou
        update_data = {}
        if 'avatar' in dados:
            update_data['avatar_customizado'] = dados.get('avatar')
        if 'banner' in dados:
            update_data['banner_customizado'] = dados.get('banner')
        if 'skin' in dados:
            update_data['equipped_skin'] = dados.get('skin') # 👈 SALVA A SKIN NO BANCO!
            
        if update_data:
            users_collection.update_one(
                {"_id": busca_id},
                {"$set": update_data}
            )
            
        return jsonify({"sucesso": True})
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500
    
@webapp_bp.route('/api/bestiario/<user_id>')
def obter_bestiario_completo(user_id):
    try:
        from modules.game_data.monsters import MONSTERS_DATA
        
        busca_id = ObjectId(user_id) if len(str(user_id)) == 24 else int(user_id)
        pdata = users_collection.find_one({"_id": busca_id})
        
        if not pdata:
            return jsonify({"erro": "Herói não encontrado."}), 404
            
        bestiario_player = pdata.get("bestiario", {})
        codice_final = {}
        
        # Tradutor de pastas para as imagens
        tradutor_pastas = {
            "capital_eldora": "capital", 
            "pradaria_inicial": "pradaria", # Corrigido para bater com o padrão
            "floresta_sombria": "floresta",
            "pedreira_granito": "pedreira"
        }
        
        for regiao, lista_mobs in MONSTERS_DATA.items():
            if regiao.startswith("_"): continue 
            
            codice_final[regiao] = []
            pasta = tradutor_pastas.get(regiao, regiao)
            
            for mob in lista_mobs:
                mob_id = mob.get("id")
                abates = bestiario_player.get(mob_id, 0)
                
                # Calcula nível de conhecimento
                nivel = 0
                if abates >= 50: nivel = 3
                elif abates >= 10: nivel = 2
                elif abates >= 1: nivel = 1
                
                # Monta a página completa do monstro no livro
                mob_info = {
                    "id": mob_id,
                    "nome": mob.get("name") if nivel >= 1 else "???",
                    "abates": abates,
                    "nivel_conhecimento": nivel,
                    "imagem": f"https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/mob/combate/{pasta}/{mob_id}.png",
                    "hp": mob.get("hp") if nivel >= 2 else "???",
                    "atk": mob.get("attack") if nivel >= 2 else "???",
                    "def": mob.get("defense") if nivel >= 2 else "???",
                    "agi": mob.get("initiative", 0) if nivel >= 2 else "???", # Novo
                    "sorte": mob.get("luck", 0) if nivel >= 2 else "???",       # Novo
                    "drops": mob.get("loot_table", []) if nivel >= 3 else []
                }
                codice_final[regiao].append(mob_info)
                
        return jsonify(codice_final)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
        
# ==========================================
# ⚒️ ROTAS DO SISTEMA DE FORJA E CRAFTING
# ==========================================
@webapp_bp.route('/api/crafting/start', methods=['POST'])
def api_start_craft():
    try:
        dados = request.json
        user_id = dados.get('user_id')
        recipe_id = dados.get('recipe_id')

        if not user_id or not recipe_id:
            return jsonify({"success": False, "error": "Faltam os dados da receita!"}), 400

        from modules import crafting_engine
        
        # Como o crafting_engine é async, usamos o _run_async (já existe no topo do seu ficheiro)
        resultado = _run_async(crafting_engine.start_craft(user_id, recipe_id))

        # Se retornar uma string, significa que deu erro (Ex: "Materiais insuficientes")
        if isinstance(resultado, str):
            return jsonify({"success": False, "error": resultado})

        return jsonify({"success": True, "data": resultado})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Erro mágico na forja: {str(e)}"}), 500


@webapp_bp.route('/api/crafting/finish', methods=['POST'])
def api_finish_craft():
    try:
        dados = request.json
        user_id = dados.get('user_id')

        if not user_id:
            return jsonify({"success": False, "error": "Falta o ID do ferreiro!"}), 400

        from modules import crafting_engine
        
        # Usa o _run_async para finalizar a forja e entregar o item na mochila
        resultado = _run_async(crafting_engine.finish_craft(user_id))

        if isinstance(resultado, str):
            return jsonify({"success": False, "error": resultado})

        # Se deu sucesso, o engine retorna o item criado
        return jsonify({
            "success": True,
            "item": resultado["item_criado"],
            "item_criado": resultado["item_criado"],
            "xp_ganho": resultado.get("xp_ganho", 0)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Erro na conclusão da forja: {str(e)}"}), 500

@webapp_bp.route('/api/crafting/recipes', methods=['GET'])
def api_obter_receitas():
    """Devolve todas as receitas carregadas automaticamente da pasta recipes/"""
    try:
        from modules import crafting_registry
        
        # Pega o dicionário gigante com todas as receitas de todas as classes
        todas_as_receitas = crafting_registry.all_recipes()
        
        return jsonify(todas_as_receitas)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": f"Erro ao buscar receitas: {str(e)}"}), 500
    
# ==========================================
# 🔥 ROTAS DA REFINARIA / FORNALHA
# ==========================================
@webapp_bp.route('/api/refining/recipes', methods=['GET'])
def api_obter_receitas_refino():
    """Devolve todas as receitas de refino para o JS desenhar a tela"""
    try:
        from modules.game_data import refining
        return jsonify(refining.REFINING_RECIPES)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": f"Erro ao buscar esquemas de refino: {str(e)}"}), 500

@webapp_bp.route('/api/refining/start_batch', methods=['POST'])
def api_start_batch_refining():
    """Inicia o refino em lote de minérios, couros, etc."""
    try:
        dados = request.json
        user_id = dados.get('user_id')
        recipe_id = dados.get('recipe_id')
        quantity = int(dados.get('quantity', 1))
        
        # 👇 EXTRAI A PROFISSÃO DA ABA QUE O JAVASCRIPT ENVIOU
        prof_selecionada = dados.get('profession')

        if not user_id or not recipe_id:
            return jsonify({"success": False, "error": "Faltam os dados da fornalha!"}), 400

        from modules.player.core import users_collection
        from bson.objectid import ObjectId
        from modules import refining_engine

        # Busca o jogador igual você faz nas outras rotas
        busca_id = ObjectId(user_id) if len(str(user_id)) == 24 else int(user_id)
        player_data = users_collection.find_one({"_id": busca_id})

        if not player_data:
            return jsonify({"success": False, "error": "Herói não encontrado."}), 404

        # 👇 CHAMA O MOTOR PASSANDO A PROFISSÃO FORÇADA
        resultado = _run_async(refining_engine.start_batch_refine(
            player_data, 
            recipe_id, 
            quantity, 
            forced_prof=prof_selecionada
        ))

        # Se retornar uma string, significa que deu erro (Ex: "Materiais insuficientes")
        if isinstance(resultado, str):
            return jsonify({"success": False, "error": resultado})

        return jsonify(resultado)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Erro na fornalha: {str(e)}"}), 500
     
@webapp_bp.route('/api/refining/finish', methods=['POST'])
def api_finish_batch_refining():
    try:
        dados = request.json
        user_id = dados.get('user_id')

        if not user_id:
            return jsonify({"success": False, "error": "Faltam os dados da fornalha!"}), 400

        from modules.player.core import users_collection
        from bson.objectid import ObjectId
        from modules import refining_engine

        # Busca o ID usando o formato correto
        busca_id = ObjectId(user_id) if len(str(user_id)) == 24 else int(user_id)
        player_data = users_collection.find_one({"_id": busca_id})

        if not player_data:
            return jsonify({"success": False, "error": "Herói não encontrado."}), 404

        # 1. Finaliza o refino
        resultado = _run_async(refining_engine.finish_refine(player_data))
        if isinstance(resultado, str):
            return jsonify({"success": False, "error": resultado})

        # 2. Re-busca o player
        player_atualizado = users_collection.find_one({"_id": busca_id})
        
        # 3. 🛡️ CONVERSÃO DE SEGURANÇA: Transforma ObjectId em String
        if player_atualizado and "_id" in player_atualizado:
            player_atualizado["_id"] = str(player_atualizado["_id"])

        return jsonify({
            "success": True, 
            "data": resultado,
            "player_data": player_atualizado # Agora o _id é uma string válida
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Erro na fornalha: {str(e)}"}), 500


@webapp_bp.route('/api/dismantle/start', methods=['POST'])
def api_start_dismantle():
    try:
        dados = request.json
        from modules.player.core import users_collection
        from bson.objectid import ObjectId
        from modules import dismantle_engine
        
        busca_id = ObjectId(dados.get('user_id')) if len(str(dados.get('user_id'))) == 24 else int(dados.get('user_id'))
        pdata = users_collection.find_one({"_id": busca_id})
        
        res = _run_async(dismantle_engine.start_dismantle(pdata, dados.get('unique_id')))
        if isinstance(res, str):
            return jsonify({
                "success": False,
                "error": res
            })

        return jsonify(
            _json_seguro_mongo(res)
        )
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@webapp_bp.route('/api/dismantle/finish', methods=['POST'])
def api_finish_dismantle():
    try:
        dados = request.json
        from modules.player.core import users_collection
        from bson.objectid import ObjectId
        from modules import dismantle_engine
        
        busca_id = ObjectId(dados.get('user_id')) if len(str(dados.get('user_id'))) == 24 else int(dados.get('user_id'))
        pdata = users_collection.find_one({"_id": busca_id})
        
        state = pdata.get("player_state", {})
        if state.get("action") != "dismantling": return jsonify({"success": False, "error": "Nenhum desmonte ativo."})
        
        res = _run_async(dismantle_engine.finish_dismantle(pdata, state.get("details", {})))
        if isinstance(res, str): return jsonify({"success": False, "error": res})
        
        # Devolve os dados atualizados para o navegador
        player_atualizado = users_collection.find_one(
            {"_id": busca_id}
        )

        return jsonify(
            _json_seguro_mongo({
                "success": True,
                "item_name": res[0],
                "rewards": res[1],
                "player_data": player_atualizado
            })
        )
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

# ==========================================
# ⬆️ ROTAS DE MELHORIA DE EQUIPAMENTO NA FORJA
# ==========================================

UPGRADE_STONE_ITEM_ID = "pedra_de_aprimoramento"
UPGRADE_PROTECTION_ITEM_ID = "sigilo_de_protecao"

UPGRADE_SKIP_RECIPE_MATERIALS = {
    "nucleo_de_forja",
    "nucleo_forja_fraco",
    "carvao",
    "martelo_gasto",
    "fluxo_solda"
}


def _forja_parse_user_id(user_id):
    return ObjectId(user_id) if len(str(user_id)) == 24 else int(user_id)


def _forja_get_item_name(base_id: str) -> str:
    info = items_data.ITEMS_DATA.get(base_id, {}) or {}
    return info.get("display_name") or str(base_id).replace("_", " ").title()


def _forja_is_upgradeable_item(item_uid: str, item_obj: dict) -> bool:
    if not isinstance(item_obj, dict):
        return False

    base_id = item_obj.get("base_id", item_uid)
    info = items_data.ITEMS_DATA.get(base_id, {}) or {}

    tipo = str(
        item_obj.get("type")
        or info.get("type")
        or info.get("tipo")
        or ""
    ).lower()

    tipos_validos = {
        "weapon", "armor", "helmet", "boots", "ring", "necklace", "earring",
        "arma", "armadura", "equipamento",
        "tool", "ferramenta"
    }

    if tipo in tipos_validos:
        return True

    # Itens únicos criados pela forja geralmente têm esses campos.
    if "upgrade_level" in item_obj or "durability" in item_obj or "enchantments" in item_obj:
        return True

    return False


def _forja_bool(value) -> bool:
    if value is True:
        return True

    txt = str(value or "").strip().lower()
    return txt in {"1", "true", "sim", "yes", "on", "usar", "usado"}


def _forja_normalizar_raridade(raridade: str) -> str:
    r = str(raridade or "comum").strip().lower()
    r = (
        r.replace("á", "a")
         .replace("à", "a")
         .replace("ã", "a")
         .replace("â", "a")
         .replace("é", "e")
         .replace("ê", "e")
         .replace("í", "i")
         .replace("ó", "o")
         .replace("ô", "o")
         .replace("õ", "o")
         .replace("ú", "u")
         .replace("ç", "c")
    )
    return r


def _forja_upgrade_cap(item_obj: dict) -> int:
    """
    Limite de melhoria por raridade.
    Usa UPGRADE_CAP_BY_RARITY do rarity.py.
    """
    raridade = _forja_normalizar_raridade(item_obj.get("rarity", "comum"))

    try:
        from modules.game_data.rarity import UPGRADE_CAP_BY_RARITY
        return int(UPGRADE_CAP_BY_RARITY.get(raridade, 20))
    except Exception:
        fallback = {
            "comum": 20,
            "bom": 25,
            "raro": 30,
            "epico": 35,
            "lendario": 40,
            "unico": 50,
            "mitico": 60,
        }
        return int(fallback.get(raridade, 20))


def _forja_upgrade_success_rate(proximo_nivel: int) -> float:
    """
    Chance de sucesso por faixa.

    +1 até +3  = 100%
    +4 até +5  = 90%
    +6 até +10 = 75%
    +11 até +15 = 60%
    +16 até +20 = 45%
    +21+ = 30%
    """
    n = int(proximo_nivel)

    if n <= 3:
        return 1.00
    if n <= 5:
        return 0.90
    if n <= 10:
        return 0.75
    if n <= 15:
        return 0.60
    if n <= 20:
        return 0.45

    return 0.30


def _forja_recipe_materials(recipe: dict) -> dict:
    """
    Aceita os três formatos que existem nas receitas:
    inputs, materials e ingredients.
    """
    if not isinstance(recipe, dict):
        return {}

    for key in ("inputs", "materials", "ingredients"):
        bloco = recipe.get(key)
        if isinstance(bloco, dict):
            return bloco

    return {}


def _forja_material_multiplier(proximo_nivel: int) -> float:
    """
    Quanto da receita original entra no custo da melhoria.
    """
    n = int(proximo_nivel)

    if n <= 3:
        return 0.25
    if n <= 5:
        return 0.35
    if n <= 10:
        return 0.50
    if n <= 15:
        return 0.65
    if n <= 20:
        return 0.80

    return 1.00


def _forja_upgrade_cost(item_obj: dict, nivel_atual: int, usar_sigilo: bool = False) -> dict:
    """
    Custo da melhoria:

    - Pedra de Aprimoramento obrigatória.
    - Parte da receita original do item.
    - Sigilo de Proteção opcional.
    """
    proximo = int(nivel_atual) + 1

    custo = {
        UPGRADE_STONE_ITEM_ID: 1 + ((proximo - 1) // 5)
    }

    base_id = item_obj.get("base_id")
    mult = _forja_material_multiplier(proximo)

    try:
        from modules import crafting_registry
        recipe = crafting_registry.get_recipe_by_item_id(base_id)
    except Exception:
        recipe = None

    materiais_receita = _forja_recipe_materials(recipe or {})

    for mat_id, qtd_original in materiais_receita.items():
        if mat_id in UPGRADE_SKIP_RECIPE_MATERIALS:
            continue

        try:
            qtd = int(math.ceil(int(qtd_original) * mult))
        except Exception:
            qtd = 1

        qtd = max(1, qtd)
        custo[mat_id] = custo.get(mat_id, 0) + qtd

    if usar_sigilo:
        custo[UPGRADE_PROTECTION_ITEM_ID] = custo.get(UPGRADE_PROTECTION_ITEM_ID, 0) + 1

    return custo


def _forja_real_stat_from_key(entry_key: str, entry_data: dict) -> str:
    if isinstance(entry_data, dict) and entry_data.get("stat"):
        return str(entry_data.get("stat"))

    key = str(entry_key or "")

    if "_" in key:
        base, suffix = key.rsplit("_", 1)
        if suffix.isdigit():
            return base

    return key


def _forja_sync_item_upgrade_values(item_obj: dict, novo_nivel: int) -> dict:
    """
    Atualiza todos os atributos para o novo nível sem juntar repetidos.

    forca   -> +2
    forca_2 -> +2
    sorte   -> +2
    """
    item_obj["upgrade_level"] = int(novo_nivel)
    item_obj["refino"] = int(novo_nivel)

    ench = item_obj.get("enchantments", {})
    if isinstance(ench, dict):
        for stat_key, stat_data in list(ench.items()):
            if isinstance(stat_data, dict):
                stat_data["stat"] = _forja_real_stat_from_key(stat_key, stat_data)
                stat_data["value"] = int(novo_nivel)
                ench[stat_key] = stat_data

            elif isinstance(stat_data, (int, float)):
                ench[stat_key] = {
                    "stat": _forja_real_stat_from_key(stat_key, {}),
                    "value": int(novo_nivel),
                    "source": "legacy"
                }

        item_obj["enchantments"] = ench

    attrs = item_obj.get("attributes", {})
    if isinstance(attrs, dict):
        for stat_key, stat_data in list(attrs.items()):
            if isinstance(stat_data, dict) and "value" in stat_data:
                stat_data["value"] = int(novo_nivel)
                attrs[stat_key] = stat_data
            elif isinstance(stat_data, (int, float)):
                attrs[stat_key] = int(novo_nivel)

        item_obj["attributes"] = attrs

    stats = item_obj.get("stats", {})
    if isinstance(stats, dict):
        for stat_key, stat_data in list(stats.items()):
            if isinstance(stat_data, dict) and "value" in stat_data:
                stat_data["value"] = int(novo_nivel)
                stats[stat_key] = stat_data
            elif isinstance(stat_data, (int, float)):
                stats[stat_key] = int(novo_nivel)

        item_obj["stats"] = stats

    return item_obj

def _forja_inventory_qty_by_base(inventory: dict, base_id: str) -> int:
    total = 0

    for uid, obj in inventory.items():
        if isinstance(obj, dict):
            item_base = obj.get("base_id", uid)
            if item_base == base_id:
                total += int(obj.get("quantity", obj.get("qtd", 1)) or 0)
        else:
            if uid == base_id:
                total += int(obj or 0)

    return total


def _forja_consume_by_base(inventory: dict, base_id: str, qty: int) -> bool:
    restante = int(qty)

    if restante <= 0:
        return True

    for uid in list(inventory.keys()):
        obj = inventory.get(uid)

        if isinstance(obj, dict):
            item_base = obj.get("base_id", uid)
            if item_base != base_id:
                continue

            atual = int(obj.get("quantity", obj.get("qtd", 1)) or 0)

            if atual <= restante:
                restante -= atual
                del inventory[uid]
            else:
                obj["quantity"] = atual - restante
                inventory[uid] = obj
                restante = 0

        else:
            if uid != base_id:
                continue

            atual = int(obj or 0)

            if atual <= restante:
                restante -= atual
                del inventory[uid]
            else:
                inventory[uid] = atual - restante
                restante = 0

        if restante <= 0:
            return True

    return restante <= 0


@webapp_bp.route('/api/equipment/upgrade/start', methods=['POST'])
def api_start_equipment_upgrade():
    try:
        from datetime import timedelta

        dados = request.json or {}
        user_id = dados.get("user_id")
        item_uid = dados.get("item_uid") or dados.get("unique_id") or dados.get("item_id")
        usar_sigilo = _forja_bool(dados.get("use_protection") or dados.get("usar_sigilo"))

        if not user_id or not item_uid:
            return jsonify({"success": False, "error": "Faltam dados do equipamento."}), 400

        busca_id = _forja_parse_user_id(user_id)
        pdata = users_collection.find_one({"_id": busca_id})

        if not pdata:
            return jsonify({"success": False, "error": "Herói não encontrado."}), 404

        estado = pdata.get("player_state", {}) or {}
        if estado.get("action") not in [None, "", "idle"]:
            return jsonify({"success": False, "error": "Você já está ocupado com outra ação."})

        inventory = pdata.get("inventory", {}) or {}
        equipment = pdata.get("equipment", {}) or {}
        equipment_tools = pdata.get("equipment_tools", {}) or {}

        item = inventory.get(item_uid)

        if not item or not isinstance(item, dict):
            return jsonify({"success": False, "error": "Equipamento não encontrado."})

        slot_equipado = None

        for slot, uid_equipado in equipment.items():
            if str(uid_equipado) == str(item_uid):
                slot_equipado = slot
                break

        if not slot_equipado:
            for prof_key, uid_equipado in equipment_tools.items():
                if str(uid_equipado) == str(item_uid):
                    slot_equipado = f"tool_{prof_key}"
                    break

        if not slot_equipado:
            return jsonify({
                "success": False,
                "error": "Este item precisa estar equipado para ser melhorado."
            })

        if not _forja_is_upgradeable_item(item_uid, item):
            return jsonify({"success": False, "error": "Este item não pode ser melhorado."})

        nivel_atual = int(item.get("upgrade_level", item.get("refino", 0)) or 0)
        cap = _forja_upgrade_cap(item)

        if nivel_atual >= cap:
            return jsonify({
                "success": False,
                "error": f"Este item já está no máximo +{cap} para a raridade dele."
            })

        proximo_nivel = nivel_atual + 1
        chance_sucesso = _forja_upgrade_success_rate(proximo_nivel)
        custo = _forja_upgrade_cost(item, nivel_atual, usar_sigilo)

        faltando = {}
        for mat_id, qtd in custo.items():
            tenho = _forja_inventory_qty_by_base(inventory, mat_id)
            if tenho < qtd:
                faltando[mat_id] = {"tenho": tenho, "precisa": qtd}

        if faltando:
            return jsonify({
                "success": False,
                "error": "Materiais insuficientes.",
                "missing": faltando
            })

        # Valida e gasta durabilidade da ferramenta antes de iniciar a melhoria.
        # A ferramenta é descoberta pela receita original do item.
        try:
            from modules import profession_engine

            tool_result = profession_engine.validate_and_consume_tool_for_item(
                player_data=pdata,
                item_obj=item,
                fallback_tool_type="ferreiro",
                action_name="melhorar"
            )

            if not tool_result.get("ok"):
                return jsonify({
                    "success": False,
                    "error": tool_result.get("error", "Ferramenta inválida para melhorar.")
                })

        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Erro ao validar ferramenta: {str(e)}"
            })

        for mat_id, qtd in custo.items():
            ok = _forja_consume_by_base(inventory, mat_id, qtd)
            if not ok:
                return jsonify({"success": False, "error": f"Erro ao consumir {mat_id}."})

        base_id = item.get("base_id", item_uid)
        nome_item = _forja_get_item_name(base_id)

        from modules import profession_engine

        base_duration = 60 + (nivel_atual * 30)

        prof_key_speed = profession_engine.get_profession_key_from_item_for_speed(
            item_inst=item,
            fallback="ferreiro"
        )

        tempo_calc = profession_engine.calculate_profession_work_duration(
            player_data=pdata,
            base_seconds=base_duration,
            profession_key=prof_key_speed,
            apply_perks=True
        )

        duration = int(tempo_calc.get("duration_seconds", base_duration))
        now = datetime.now(timezone.utc)
        finish_time = now + timedelta(seconds=duration)

        pdata["inventory"] = inventory
        pdata["player_state"] = {
            "action": "equipment_upgrading",
            "started_at": now.isoformat(),
            "finish_time": finish_time.isoformat(),
            "details": {
                "item_uid": item_uid,
                "slot": slot_equipado,
                "base_id": base_id,
                "item_name": nome_item,
                "old_level": nivel_atual,
                "target_level": proximo_nivel,
                "cap": cap,
                "cost": custo,
                "use_protection": usar_sigilo,
                "success_rate": chance_sucesso,
                "work_speed": tempo_calc,
                "tool_uid": tool_result.get("tool_uid"),
                "tool_type": tool_result.get("tool_type"),
                "tool_broke": tool_result.get("tool_broke", False)
            }
        }

        users_collection.update_one(
            {"_id": busca_id},
            {"$set": {
                "inventory": pdata["inventory"],
                "player_state": pdata["player_state"]
            }}
        )

        return jsonify({
            "success": True,
            "duration_seconds": duration,
            "finish_time": finish_time.isoformat(),
            "work_speed": tempo_calc,
            "new_level": nivel_atual + 1,
            "item_name": nome_item,
            "old_level": nivel_atual,
            "target_level": proximo_nivel,
            "cap": cap,
            "success_rate": chance_sucesso,
            "success_percent": int(chance_sucesso * 100),
            "use_protection": usar_sigilo,
            "cost": custo,
            "tool_broke": tool_result.get("tool_broke", False),
            "tool_message": tool_result.get("message", "")
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Erro ao iniciar melhoria: {str(e)}"}), 500

@webapp_bp.route('/api/equipment/upgrade/finish', methods=['POST'])
def api_finish_equipment_upgrade():
    try:
        dados = request.json or {}
        user_id = dados.get("user_id")

        if not user_id:
            return jsonify({"success": False, "error": "Falta o ID do jogador."}), 400

        busca_id = _forja_parse_user_id(user_id)
        pdata = users_collection.find_one({"_id": busca_id})

        if not pdata:
            return jsonify({"success": False, "error": "Herói não encontrado."}), 404

        state = pdata.get("player_state", {}) or {}

        if state.get("action") != "equipment_upgrading":
            return jsonify({"success": False, "error": "Nenhuma melhoria ativa."})

        details = state.get("details", {}) or {}
        item_uid = details.get("item_uid")

        old_level = int(details.get("old_level", 0) or 0)
        target_level = int(details.get("target_level", details.get("new_level", old_level + 1)) or (old_level + 1))
        chance_sucesso = float(details.get("success_rate", _forja_upgrade_success_rate(target_level)) or 0)
        usar_sigilo = bool(details.get("use_protection", False))

        inventory = pdata.get("inventory", {}) or {}
        equipment = pdata.get("equipment", {}) or {}
        equipment_tools = pdata.get("equipment_tools", {}) or {}

        item = inventory.get(item_uid)

        if not item or not isinstance(item, dict):
            pdata["player_state"] = {"action": "idle"}
            users_collection.update_one(
                {"_id": busca_id},
                {"$set": {"player_state": pdata["player_state"]}}
            )
            return jsonify({"success": False, "error": "O item sumiu."})

        ainda_equipado = False

        for _slot, uid_equipado in equipment.items():
            if str(uid_equipado) == str(item_uid):
                ainda_equipado = True
                break

        if not ainda_equipado:
            for _prof_key, uid_equipado in equipment_tools.items():
                if str(uid_equipado) == str(item_uid):
                    ainda_equipado = True
                    break

        if not ainda_equipado:
            pdata["player_state"] = {"action": "idle"}
            users_collection.update_one(
                {"_id": busca_id},
                {"$set": {"player_state": pdata["player_state"]}}
            )
            return jsonify({
                "success": False,
                "error": "O item foi desequipado durante a melhoria. A melhoria foi cancelada."
            })

        sucesso_upgrade = random.random() <= chance_sucesso

        protegido = False
        perdeu_nivel = False

        if sucesso_upgrade:
            nivel_final = target_level
            resultado_msg = f"Melhoria concluída! O item agora está +{nivel_final}."
        else:
            if usar_sigilo:
                protegido = True
                nivel_final = old_level
                resultado_msg = "A melhoria falhou, mas o Sigilo de Proteção impediu a perda de nível."
            else:
                piso = 0
                nivel_final = max(piso, old_level - 1)
                perdeu_nivel = nivel_final < old_level

                if perdeu_nivel:
                    resultado_msg = f"A melhoria falhou e o item caiu de +{old_level} para +{nivel_final}."
                else:
                    resultado_msg = "A melhoria falhou, mas o item não podia perder mais nível."

        item = _forja_sync_item_upgrade_values(item, nivel_final)

        inventory[item_uid] = item
        pdata["inventory"] = inventory
        pdata["player_state"] = {"action": "idle"}

        users_collection.update_one(
            {"_id": busca_id},
            {"$set": {
                "inventory": pdata["inventory"],
                "player_state": pdata["player_state"]
            }}
        )

        player_atualizado = users_collection.find_one({"_id": busca_id})

        player_atualizado = _json_seguro_mongo(
            player_atualizado
        )

        nome_item = details.get("item_name") or _forja_get_item_name(item.get("base_id", item_uid))

        return jsonify({
            "success": True,
            "upgrade_success": sucesso_upgrade,
            "protected": protegido,
            "downgraded": perdeu_nivel,
            "item_name": nome_item,
            "old_level": old_level,
            "target_level": target_level,
            "new_level": nivel_final,
            "final_level": nivel_final,
            "success_rate": chance_sucesso,
            "success_percent": int(chance_sucesso * 100),
            "message": resultado_msg,
            "item": item,
            "player_data": player_atualizado
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Erro ao concluir melhoria: {str(e)}"}), 500
    
# ==========================================
# 🌌 ROTAS DO BOSS DIMENSIONAL
# ==========================================
@webapp_bp.route('/api/dimensional/abates_status', methods=['GET'])
def api_dimensional_abates_status():
    try:
        from modules.events import dimensional_boss_manager as dbm

        return jsonify(dbm.obter_status_abates_dimensional())

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@webapp_bp.route('/api/dimensional/status', methods=['GET'])
def api_dimensional_status():
    try:
        from modules.events import dimensional_boss_manager as dbm

        dbm.verificar_inicio_automatico(motivo="status")
        evento = dbm.serializar_evento()

        return jsonify({
            "success": True,
            "ativo": bool(evento),
            "evento": evento
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@webapp_bp.route('/api/dimensional/criar_debug', methods=['POST'])
def api_dimensional_criar_debug():
    try:
        from modules.events import dimensional_boss_manager as dbm

        dados = request.json or {}
        mapa = dados.get("mapa") or dados.get("regiao")

        evento = dbm.criar_evento_debug(mapa=mapa)

        return jsonify({
            "success": True,
            "evento": evento
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@webapp_bp.route('/api/dimensional/entrar', methods=['POST'])
def api_dimensional_entrar():
    try:
        from modules.events import dimensional_boss_manager as dbm

        dados = request.json or {}
        user_id = dados.get("user_id") or dados.get("char_id")

        resultado = dbm.entrar_no_evento(user_id)

        status = 200 if resultado.get("success") else 400
        return jsonify(resultado), status

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@webapp_bp.route('/api/dimensional/sair', methods=['POST'])
def api_dimensional_sair():
    try:
        from modules.events import dimensional_boss_manager as dbm

        dados = request.json or {}
        user_id = dados.get("user_id") or dados.get("char_id")

        resultado = dbm.sair_do_evento(user_id)

        status = 200 if resultado.get("success") else 400
        return jsonify(resultado), status

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@webapp_bp.route('/api/dimensional/sala', methods=['GET'])
def api_dimensional_sala():
    try:
        from modules.events import dimensional_boss_manager as dbm

        evento = dbm.serializar_evento()

        if not evento:
            return jsonify({
                "success": False,
                "error": "Nenhuma Fenda Dimensional ativa."
            }), 404

        return jsonify({
            "success": True,
            "evento": evento
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@webapp_bp.route('/api/dimensional/iniciar', methods=['POST'])
def api_dimensional_iniciar():
    try:
        from modules.events import dimensional_boss_manager as dbm

        dados = request.json or {}
        user_id = dados.get("user_id") or dados.get("char_id")

        resultado = dbm.iniciar_batalha(user_id)

        status = 200 if resultado.get("success") else 400
        return jsonify(resultado), status

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@webapp_bp.route('/api/dimensional/acao', methods=['POST'])
def api_dimensional_acao():
    try:
        from modules.events import dimensional_boss_manager as dbm

        dados = request.json or {}

        user_id = dados.get("user_id") or dados.get("char_id")
        alvo_id = dados.get("alvo_id")
        tipo = dados.get("tipo") or "ataque_basico"
        skill_id = dados.get("skill_id")

        resultado = dbm.executar_acao(
            user_id=user_id,
            alvo_id=alvo_id,
            tipo=tipo,
            skill_id=skill_id
        )

        status = 200 if resultado.get("success") else 400
        return jsonify(resultado), status

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500        

# ==========================================
# 🌌 DEBUG — INICIAR FENDA DIMENSIONAL NO MAPA
# ==========================================

@webapp_bp.route('/api/debug/iniciar_dimensional_mapa', methods=['GET'])
def api_debug_iniciar_dimensional_mapa():
    try:
        from modules.events import dimensional_boss_manager as dbm

        mapa = (
            request.args.get("mapa") or
            request.args.get("regiao") or
            None
        )

        evento = dbm.criar_evento_debug(mapa=mapa)

        try:
            from flask import current_app
            from datetime import datetime

            mapa_evento = evento.get("mapa") or evento.get("regiao") or "mapa_desconhecido"

            nomes_mapas = {
                "capital_eldora": "Capital de Eldora",
                "pradaria_inicial": "Pradaria Inicial",
                "floresta_sombria": "Floresta Sombria",
                "pedreira_granito": "Pedreira de Granito"
            }

            mapa_nome = nomes_mapas.get(mapa_evento, str(mapa_evento).replace("_", " ").title())

            payload_socket = {
                "evento": evento,
                "evento_id": evento.get("evento_id"),
                "mapa": mapa_evento,
                "regiao": mapa_evento,
                "mapa_nome": mapa_nome,
                "entrada_encerra_em": evento.get("entrada_encerra_em"),
                "tempo_entrada_restante": evento.get("tempo_entrada_restante"),
                "max_jogadores": evento.get("max_jogadores"),
                "mensagem": f"🌌 Uma Fenda Dimensional surgiu em {mapa_nome}!"
            }

            sio = current_app.extensions.get("socketio")

            if sio:
                sio.emit("fendaDimensionalSurgiu", payload_socket)
                sio.emit("novaMensagemChat", {
                    "remetente": "Sistema",
                    "texto": payload_socket["mensagem"],
                    "tipo": "evento"
                })

            try:
                db["chat_historico"].insert_one({
                    "remetente": "Sistema",
                    "texto": payload_socket["mensagem"],
                    "alvo": "global",
                    "tipo": "evento",
                    "data_envio": datetime.utcnow()
                })
            except Exception as e:
                print(f"⚠️ [DIMENSIONAL CHAT] Não salvou aviso da Fenda no chat: {e}")

        except Exception as e:
            print(f"⚠️ [DIMENSIONAL SOCKET] Falha ao emitir nascimento da Fenda: {e}")

        return jsonify({
            "success": True,
            "message": "Fenda Dimensional iniciada no mapa.",
            "evento_id": evento.get("evento_id"),
            "mapa": evento.get("mapa"),
            "status": evento.get("status"),
            "qtd_jogadores": evento.get("qtd_jogadores"),
            "max_jogadores": evento.get("max_jogadores"),
            "tempo_entrada_restante": evento.get("tempo_entrada_restante"),
            "evento": evento
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500        
    
# ==========================================
# 🌌 DEBUG — ENCERRAR FENDA DIMENSIONAL
# ==========================================

@webapp_bp.route('/api/debug/encerrar_dimensional_mapa', methods=['GET'])
def api_debug_encerrar_dimensional_mapa():
    try:
        from modules.events import dimensional_boss_manager as dbm

        resultado = dbm.encerrar_evento_debug()

        try:
            from flask import current_app

            sio = current_app.extensions.get("socketio")

            if sio:
                sio.emit("fendaDimensionalEncerrada", {
                    "evento_id": resultado.get("evento_id"),
                    "mensagem": "🌌 A Fenda Dimensional se fechou."
                })

                sio.emit("novaMensagemChat", {
                    "remetente": "Sistema",
                    "texto": "🌌 A Fenda Dimensional se fechou.",
                    "tipo": "evento"
                })

        except Exception as e:
            print(f"⚠️ [DIMENSIONAL SOCKET] Falha ao emitir encerramento da Fenda: {e}")

        return jsonify(resultado)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500    
    
# ==========================================
# 🛡️ ROTAS COMPLETAS DOS CLÃS
# ==========================================
@webapp_bp.route(
    '/api/clan/logos',
    methods=['GET']
)
def api_clan_logos():
    try:
        from modules.clan.clan_logos import (
            listar_logos_publicas,
        )

        return jsonify({
            "success": True,
            "logos": listar_logos_publicas(),
        })

    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": (
                "Erro ao carregar as logos: "
                f"{str(e)}"
            ),
        }), 500

@webapp_bp.route('/api/clan/criar', methods=['POST'])
def api_clan_criar():
    from modules.clan import clan_manager

    dados = request.json or {}

    resultado = clan_manager.criar_cla(
        user_id=dados.get("user_id"),
        nome=dados.get("nome"),
        tag=dados.get("tag"),
        descricao=dados.get("descricao", ""),
        logo_id=dados.get("logo_id"),
    )

    return jsonify(resultado), (
        201 if resultado.get("success") else 400
    )


# ============================================================
# 🏰 MEU CLÃ
# ============================================================

@webapp_bp.route(
    '/api/clan/meu_clan/<user_id>',
    methods=['GET']
)
def api_clan_meu_clan(user_id):
    from modules.clan import clan_manager

    cla = (
        clan_manager
        .obter_cla_do_jogador(
            user_id
        )
    )

    return jsonify({
        "success": True,

        "possui_clan":
            bool(
                cla
            ),

        "clan":
            clan_manager
            .serializar_cla(
                cla
            ),

        "custo_criacao_ouro":
            clan_manager
            .CLAN_CUSTO_CRIACAO_OURO,
    })

# ============================================================
# 🏅 LOJA DO CLÃ — CATÁLOGO
# ============================================================

@webapp_bp.route(
    '/api/clan/loja/<user_id>',
    methods=['GET']
)
def api_clan_loja_catalogo(
    user_id
):
    try:

        from modules.clan import (
            clan_shop,
        )


        resultado = (
            clan_shop
            .obter_catalogo_loja_cla(
                user_id
            )
        )


        return jsonify(
            resultado
        ), (
            200
            if resultado.get(
                "success"
            )
            else 400
        )


    except Exception as e:

        traceback.print_exc()


        return jsonify({

            "success":
                False,

            "error": (
                "Erro ao carregar "
                "a Loja do Clã: "
                f"{str(e)}"
            ),

        }), 500

# ============================================================
# 🛒 LOJA DO CLÃ — COMPRAR
# ============================================================

@webapp_bp.route(
    '/api/clan/loja/comprar',
    methods=['POST']
)
def api_clan_loja_comprar():
    try:

        from modules.clan import (
            clan_shop,
        )


        dados = (
            request.get_json(
                silent=True
            )
            or {}
        )


        user_id = dados.get(
            "user_id"
        )


        resultado = (
            clan_shop
            .comprar_item_loja_cla(

                user_id=
                    user_id,

                item_id=
                    dados.get(
                        "item_id"
                    ),

                quantidade=
                    dados.get(
                        "quantidade",
                        1,
                    ),
            )
        )


        # ====================================================
        # 🧹 LIMPA CACHE APÓS COMPRA REAL
        # ====================================================

        if resultado.get(
            "success"
        ):

            try:
                from modules.player.core import (
                    clear_player_cache,
                )


                if ObjectId.is_valid(
                    str(
                        user_id
                    )
                ):

                    player_id = ObjectId(
                        str(
                            user_id
                        )
                    )


                    _run_async(
                        clear_player_cache(
                            player_id
                        )
                    )


                    _run_async(
                        clear_player_cache(
                            str(
                                player_id
                            )
                        )
                    )


            except Exception as erro_cache:

                print(
                    "⚠️ [LOJA DO CLÃ] "
                    "Falha ao limpar cache:",
                    erro_cache,
                )


        return jsonify(
            resultado
        ), (
            200
            if resultado.get(
                "success"
            )
            else 400
        )


    except Exception as e:

        traceback.print_exc()


        return jsonify({
            "success": False,

            "error": (
                "Erro ao realizar compra "
                "na Loja do Clã: "
                f"{str(e)}"
            ),
        }), 500
    
# ============================================================
# ⚔️ GUERRA DE CLÃS — ESTADO DA SEMANA
# ============================================================

@webapp_bp.route(
    '/api/clan/guerra/estado/<user_id>',
    methods=['GET']
)
def api_clan_guerra_estado(user_id):
    try:
        from modules.clan import (
            clan_war_manager,
        )

        resultado = (
            clan_war_manager
            .obter_estado_guerra_jogador(
                user_id
            )
        )

        return jsonify(
            resultado
        ), (
            200
            if resultado.get(
                "success"
            )
            else 400
        )

    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": (
                "Erro ao consultar a "
                "Guerra de Clãs: "
                f"{str(e)}"
            ),
        }), 500

# ============================================================
# 🏆 GUERRA DE CLÃS — RANKING
# ============================================================

@webapp_bp.route(
    '/api/clan/guerra/ranking',
    methods=['GET']
)
def api_clan_guerra_ranking():
    try:

        from modules.clan import (
            clan_war_manager,
        )


        semana_id = request.args.get(
            "semana_id"
        )


        limite = request.args.get(
            "limite",
            100,
        )


        resultado = (
            clan_war_manager
            .obter_ranking_guerra(

                semana_id=
                    semana_id,

                limite=
                    limite,
            )
        )


        return jsonify(
            resultado
        ), (
            200
            if resultado.get(
                "success"
            )
            else 400
        )


    except Exception as e:

        traceback.print_exc()


        return jsonify({
            "success": False,

            "error": (
                "Erro ao consultar o ranking "
                "da Guerra de Clãs: "
                f"{str(e)}"
            ),
        }), 500
    
# ============================================================
# 🚪 GUERRA DE CLÃS — ENTRAR NO LOBBY DA FRENTE
# ============================================================

@webapp_bp.route(
    '/api/clan/guerra/frente/entrar',
    methods=['POST']
)
def api_clan_guerra_frente_entrar():
    try:

        from modules.clan import (
            clan_war_manager,
        )


        dados = (
            request.get_json(
                silent=True
            )
            or {}
        )


        resultado = (
            clan_war_manager
            .entrar_lobby_frente_guerra(
                user_id=
                    dados.get(
                        "user_id"
                    )
            )
        )


        return jsonify(
            resultado
        ), (
            200
            if resultado.get(
                "success"
            )
            else 400
        )


    except Exception as e:

        traceback.print_exc()


        return jsonify({

            "success":
                False,

            "error":
                (
                    "Erro ao entrar no lobby "
                    "da Guerra de Clãs: "
                    f"{str(e)}"
                ),

        }), 500


# ============================================================
# ✅ GUERRA DE CLÃS — JOGADOR PRONTO NA FRENTE
# ============================================================

@webapp_bp.route(
    '/api/clan/guerra/frente/pronto',
    methods=['POST']
)
def api_clan_guerra_frente_pronto():
    try:

        from modules.clan import (
            clan_war_manager,
        )


        dados = (
            request.get_json(
                silent=True
            )
            or {}
        )


        resultado = (
            clan_war_manager
            .marcar_pronto_lobby_frente_guerra(
                user_id=
                    dados.get(
                        "user_id"
                    )
            )
        )


        return jsonify(
            resultado
        ), (
            200
            if resultado.get(
                "success"
            )
            else 400
        )


    except Exception as e:

        traceback.print_exc()


        return jsonify({
            "success": False,

            "error": (
                "Erro ao marcar PRONTO "
                "na Guerra de Clãs: "
                f"{str(e)}"
            ),
        }), 500

# ============================================================
# 🎯 GUERRA DE CLÃS — ESTADO DO TURNO
# ============================================================

@webapp_bp.route(
    '/api/clan/guerra/batalha/turno/<user_id>',
    methods=['GET']
)
def api_clan_guerra_batalha_turno(
    user_id
):
    try:

        from modules.clan import (
            clan_war_battle_engine,
        )


        resultado = (
            clan_war_battle_engine
            .obter_estado_turno_jogador(
                user_id=
                    user_id
            )
        )


        return jsonify(
            resultado
        ), (
            200
            if resultado.get(
                "success"
            )
            else 400
        )


    except Exception as e:

        traceback.print_exc()


        return jsonify({
            "success": False,

            "error": (
                "Erro ao consultar turno "
                "da Guerra de Clãs: "
                f"{str(e)}"
            ),
        }), 500
        
# ============================================================
# ⚔️ GUERRA DE CLÃS — INSCREVER CLÃ
# ============================================================

# ============================================================
# ⚔️ GUERRA DE CLÃS — ATAQUE BÁSICO
# ============================================================

@webapp_bp.route(
    '/api/clan/guerra/batalha/ataque',
    methods=['POST']
)
def api_clan_guerra_batalha_ataque():
    try:

        from modules.clan import (
            clan_war_battle_engine,
            clan_war_manager,
        )


        dados = (
            request.get_json(
                silent=True
            )
            or {}
        )


        user_id = dados.get(
            "user_id"
        )


        resultado = _run_async(
            clan_war_battle_engine
            .executar_ataque_basico(

                user_id=
                    user_id,

                alvo_id=
                    dados.get(
                        "alvo_id"
                    ),
            )
        )


        # Se o ataque funcionou, devolvemos também
        # o estado já atualizado para o jogador.
        if resultado.get(
            "success"
        ):

            estado_atual = (
                clan_war_manager
                .obter_estado_guerra_jogador(
                    user_id
                )
            )


            if estado_atual.get(
                "success"
            ):

                resultado[
                    "estado_guerra"
                ] = estado_atual


        return jsonify(
            resultado
        ), (
            200
            if resultado.get(
                "success"
            )
            else 400
        )


    except Exception as e:

        traceback.print_exc()


        return jsonify({
            "success": False,

            "error": (
                "Erro ao atacar na "
                "Guerra de Clãs: "
                f"{str(e)}"
            ),
        }), 500

# ============================================================
# ✨ GUERRA DE CLÃS — SKILL OFENSIVA
# ============================================================

@webapp_bp.route(
    '/api/clan/guerra/batalha/skill',
    methods=['POST']
)
def api_clan_guerra_batalha_skill():
    try:

        from modules.clan import (
            clan_war_battle_engine,
            clan_war_manager,
        )


        dados = (
            request.get_json(
                silent=True
            )
            or {}
        )


        user_id = dados.get(
            "user_id"
        )


        resultado = _run_async(
            clan_war_battle_engine
            .executar_skill_ofensiva(

                user_id=
                    user_id,

                alvo_id=
                    dados.get(
                        "alvo_id"
                    ),

                skill_id=
                    dados.get(
                        "skill_id"
                    ),
            )
        )


        if resultado.get(
            "success"
        ):

            estado_atual = (
                clan_war_manager
                .obter_estado_guerra_jogador(
                    user_id
                )
            )


            if estado_atual.get(
                "success"
            ):

                resultado[
                    "estado_guerra"
                ] = estado_atual


        return jsonify(
            resultado
        ), (
            200
            if resultado.get(
                "success"
            )
            else 400
        )


    except Exception as e:

        traceback.print_exc()


        return jsonify({
            "success": False,

            "error": (
                "Erro ao usar skill "
                "na Guerra de Clãs: "
                f"{str(e)}"
            ),
        }), 500
        
@webapp_bp.route(
    '/api/clan/guerra/inscrever',
    methods=['POST']
)
def api_clan_guerra_inscrever():
    try:
        from modules.clan import (
            clan_war_manager,
        )

        dados = (
            request.get_json(
                silent=True
            )
            or {}
        )

        resultado = (
            clan_war_manager
            .inscrever_cla_na_guerra(
                user_id=dados.get(
                    "user_id"
                )
            )
        )

        return jsonify(
            resultado
        ), (
            200
            if resultado.get(
                "success"
            )
            else 400
        )

    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": (
                "Erro ao inscrever o clã "
                "na Guerra Semanal: "
                f"{str(e)}"
            ),
        }), 500

# ============================================================
# ⚔️ GUERRA DE CLÃS — JOGADOR PARTICIPAR
# ============================================================

@webapp_bp.route(
    '/api/clan/guerra/participar',
    methods=['POST']
)
def api_clan_guerra_participar():
    try:
        from modules.clan import (
            clan_war_manager,
        )

        dados = (
            request.get_json(
                silent=True
            )
            or {}
        )

        resultado = (
            clan_war_manager
            .inscrever_jogador_na_guerra(
                dados.get(
                    "user_id"
                )
            )
        )

        return jsonify(
            resultado
        ), (
            200
            if resultado.get(
                "success"
            )
            else 400
        )

    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error":
                (
                    "Erro ao registrar "
                    "participação na Guerra: "
                    f"{str(e)}"
                ),
        }), 500


# ============================================================
# ⚔️ GUERRA DE CLÃS — SAIR DA INSCRIÇÃO
# ============================================================

@webapp_bp.route(
    '/api/clan/guerra/sair',
    methods=['POST']
)
def api_clan_guerra_sair():
    try:
        from modules.clan import (
            clan_war_manager,
        )

        dados = (
            request.get_json(
                silent=True
            )
            or {}
        )

        resultado = (
            clan_war_manager
            .remover_jogador_da_guerra(
                dados.get(
                    "user_id"
                )
            )
        )

        return jsonify(
            resultado
        ), (
            200
            if resultado.get(
                "success"
            )
            else 400
        )

    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error":
                (
                    "Erro ao retirar "
                    "participação da Guerra: "
                    f"{str(e)}"
                ),
        }), 500

# ============================================================
# 👑 GUERRA DE CLÃS — CONFIRMAR ESCALAÇÃO
# ============================================================

@webapp_bp.route(
    '/api/clan/guerra/escalacao/confirmar',
    methods=['POST']
)
def api_clan_guerra_confirmar_escalacao():
    try:

        from modules.clan import (
            clan_war_manager,
        )


        dados = (
            request.get_json(
                silent=True
            )
            or {}
        )


        resultado = (
            clan_war_manager
            .confirmar_escalacao_cla(

                user_id=
                    dados.get(
                        "user_id"
                    ),

                titulares_ids=
                    dados.get(
                        "titulares",
                        []
                    ),
            )
        )


        return jsonify(
            resultado
        ), (
            200
            if resultado.get(
                "success"
            )
            else 400
        )


    except Exception as e:

        traceback.print_exc()


        return jsonify({

            "success":
                False,

            "error":
                (
                    "Erro ao confirmar "
                    "a escalação da Guerra: "
                    f"{str(e)}"
                ),

        }), 500
            
@webapp_bp.route('/api/clan/convidar', methods=['POST'])
def api_clan_convidar():
    from modules.clan import clan_manager

    dados = request.json or {}

    resultado = clan_manager.convidar_jogador(
        autor_id=dados.get("user_id"),
        alvo_id=dados.get("alvo_id")
    )

    return jsonify(resultado), (
        200 if resultado.get("success") else 400
    )


@webapp_bp.route('/api/clan/convites/<user_id>')
def api_clan_convites(user_id):
    from modules.clan import clan_manager

    resultado = clan_manager.listar_convites(
        user_id
    )

    return jsonify(resultado)


@webapp_bp.route('/api/clan/convite/aceitar', methods=['POST'])
def api_clan_aceitar_convite():
    from modules.clan import clan_manager

    dados = request.json or {}

    resultado = clan_manager.aceitar_convite(
        user_id=dados.get("user_id"),
        clan_id=dados.get("clan_id")
    )

    return jsonify(resultado), (
        200 if resultado.get("success") else 400
    )


@webapp_bp.route('/api/clan/convite/recusar', methods=['POST'])
def api_clan_recusar_convite():
    from modules.clan import clan_manager

    dados = request.json or {}

    resultado = clan_manager.recusar_convite(
        user_id=dados.get("user_id"),
        clan_id=dados.get("clan_id")
    )

    return jsonify(resultado), (
        200 if resultado.get("success") else 400
    )

# ==========================================
# 📩 SOLICITAÇÕES PARA ENTRAR EM CLÃS
# ==========================================

@webapp_bp.route(
    '/api/clan/solicitar_entrada',
    methods=['POST']
)
def api_clan_solicitar_entrada():
    try:
        from modules.clan import clan_manager

        dados = request.json or {}

        resultado = clan_manager.solicitar_entrada(
            user_id=dados.get("user_id"),
            clan_id=dados.get("clan_id"),
        )

        return jsonify(resultado), (
            200
            if resultado.get("success")
            else 400
        )

    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": (
                "Erro ao enviar solicitação: "
                f"{str(e)}"
            ),
        }), 500


@webapp_bp.route(
    '/api/clan/solicitacoes/<user_id>',
    methods=['GET']
)
def api_clan_listar_solicitacoes(user_id):
    try:
        from modules.clan import clan_manager

        resultado = (
            clan_manager.listar_solicitacoes(
                autor_id=user_id
            )
        )

        return jsonify(resultado), (
            200
            if resultado.get("success")
            else 403
        )

    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": (
                "Erro ao listar solicitações: "
                f"{str(e)}"
            ),
        }), 500


@webapp_bp.route(
    '/api/clan/solicitacao/aceitar',
    methods=['POST']
)
def api_clan_aceitar_solicitacao():
    try:
        from modules.clan import clan_manager

        dados = request.json or {}

        resultado = (
            clan_manager.aceitar_solicitacao(
                autor_id=dados.get("user_id"),
                alvo_id=dados.get("alvo_id"),
            )
        )

        return jsonify(resultado), (
            200
            if resultado.get("success")
            else 400
        )

    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": (
                "Erro ao aceitar solicitação: "
                f"{str(e)}"
            ),
        }), 500


@webapp_bp.route(
    '/api/clan/solicitacao/recusar',
    methods=['POST']
)
def api_clan_recusar_solicitacao():
    try:
        from modules.clan import clan_manager

        dados = request.json or {}

        resultado = (
            clan_manager.recusar_solicitacao(
                autor_id=dados.get("user_id"),
                alvo_id=dados.get("alvo_id"),
            )
        )

        return jsonify(resultado), (
            200
            if resultado.get("success")
            else 400
        )

    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": (
                "Erro ao recusar solicitação: "
                f"{str(e)}"
            ),
        }), 500

@webapp_bp.route('/api/clan/sair', methods=['POST'])
def api_clan_sair():
    from modules.clan import clan_manager

    dados = request.json or {}

    resultado = clan_manager.sair_cla(
        dados.get("user_id")
    )

    return jsonify(resultado), (
        200 if resultado.get("success") else 400
    )


@webapp_bp.route('/api/clan/expulsar', methods=['POST'])
def api_clan_expulsar():
    from modules.clan import clan_manager

    dados = request.json or {}

    resultado = clan_manager.expulsar_membro(
        autor_id=dados.get("user_id"),
        alvo_id=dados.get("alvo_id")
    )

    return jsonify(resultado), (
        200 if resultado.get("success") else 400
    )


@webapp_bp.route('/api/clan/cargo', methods=['POST'])
def api_clan_alterar_cargo():
    from modules.clan import clan_manager

    dados = request.json or {}

    resultado = clan_manager.alterar_cargo(
        lider_id=dados.get("user_id"),
        alvo_id=dados.get("alvo_id"),
        novo_cargo=dados.get("novo_cargo")
    )

    return jsonify(resultado), (
        200 if resultado.get("success") else 400
    )

# ============================================================
# 🎖️ CARGOS PERSONALIZADOS DO CLÃ
# ============================================================


# ============================================================
# 📖 LISTAR CARGOS E PERMISSÕES
# ============================================================

@webapp_bp.route(
    '/api/clan/cargos/listar/<user_id>',
    methods=['GET']
)
def api_clan_listar_cargos(user_id):
    try:
        from modules.clan import clan_manager

        from modules.clan.clan_registry import (
            listar_permissoes_cargo,
        )


        cla = clan_manager.obter_cla_do_jogador(
            user_id
        )


        if not cla:
            return jsonify({
                "success": False,
                "error": (
                    "Você não pertence a um clã."
                ),
            }), 400


        dados_cla = (
            clan_manager.serializar_cla(
                cla
            )
            or {}
        )


        meu_cargo = None


        for membro in (
            cla.get(
                "membros",
                []
            )
            or []
        ):

            if (
                str(
                    membro.get(
                        "user_id"
                    )
                )
                ==
                str(user_id)
            ):

                meu_cargo = membro.get(
                    "cargo"
                )

                break


        configuracao_meu_cargo = (
            clan_manager
            .obter_config_cargo_cla(
                cla,
                meu_cargo,
            )
            or {}
        )


        sou_lider = (
            str(
                cla.get(
                    "lider_id"
                )
            )
            ==
            str(user_id)
        )


        return jsonify({
            "success": True,

            "clan_id":
                str(
                    cla["_id"]
                ),

            "meu_cargo":
                meu_cargo,

            "meu_cargo_nome":
                configuracao_meu_cargo.get(
                    "nome",
                    meu_cargo,
                ),

            "minhas_permissoes":
                configuracao_meu_cargo.get(
                    "permissoes",
                    {},
                ),

            # Criar/editar/excluir a estrutura
            # dos cargos continua exclusivo
            # do verdadeiro líder.
            "pode_editar_estrutura":
                sou_lider,

            "cargos":
                dados_cla.get(
                    "cargos_lista",
                    [],
                ),

            "permissoes":
                listar_permissoes_cargo(),

            "limite_cargos_personalizados":
                dados_cla.get(
                    "limite_cargos_personalizados",
                    0,
                ),

            "cargos_personalizados_total":
                dados_cla.get(
                    "cargos_personalizados_total",
                    0,
                ),
        })


    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": (
                "Erro ao carregar os cargos "
                f"do clã: {str(e)}"
            ),
        }), 500


# ============================================================
# ➕ CRIAR CARGO
# ============================================================

@webapp_bp.route(
    '/api/clan/cargos/criar',
    methods=['POST']
)
def api_clan_criar_cargo():
    try:
        from modules.clan import clan_manager

        dados = request.json or {}


        resultado = (
            clan_manager.criar_cargo_cla(
                user_id=
                    dados.get(
                        "user_id"
                    ),

                nome=
                    dados.get(
                        "nome"
                    ),

                ordem=
                    dados.get(
                        "ordem",
                        50,
                    ),

                permissoes=
                    dados.get(
                        "permissoes",
                        {},
                    ),
            )
        )


        return jsonify(
            resultado
        ), (
            201
            if resultado.get(
                "success"
            )
            else 400
        )


    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": (
                "Erro ao criar cargo: "
                f"{str(e)}"
            ),
        }), 500


# ============================================================
# ✏️ EDITAR CARGO
# ============================================================

@webapp_bp.route(
    '/api/clan/cargos/editar',
    methods=['POST']
)
def api_clan_editar_cargo():
    try:
        from modules.clan import clan_manager

        dados = request.json or {}


        resultado = (
            clan_manager.editar_cargo_cla(
                user_id=
                    dados.get(
                        "user_id"
                    ),

                cargo_id=
                    dados.get(
                        "cargo_id"
                    ),

                nome=
                    dados.get(
                        "nome"
                    ),

                ordem=
                    dados.get(
                        "ordem"
                    ),

                permissoes=
                    dados.get(
                        "permissoes"
                    ),
            )
        )


        return jsonify(
            resultado
        ), (
            200
            if resultado.get(
                "success"
            )
            else 400
        )


    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": (
                "Erro ao editar cargo: "
                f"{str(e)}"
            ),
        }), 500


# ============================================================
# 🗑️ EXCLUIR CARGO
# ============================================================

@webapp_bp.route(
    '/api/clan/cargos/excluir',
    methods=['POST']
)
def api_clan_excluir_cargo():
    try:
        from modules.clan import clan_manager

        dados = request.json or {}


        resultado = (
            clan_manager.excluir_cargo_cla(
                user_id=
                    dados.get(
                        "user_id"
                    ),

                cargo_id=
                    dados.get(
                        "cargo_id"
                    ),
            )
        )


        return jsonify(
            resultado
        ), (
            200
            if resultado.get(
                "success"
            )
            else 400
        )


    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": (
                "Erro ao excluir cargo: "
                f"{str(e)}"
            ),
        }), 500
        
@webapp_bp.route('/api/clan/transferir_lideranca', methods=['POST'])
def api_clan_transferir_lideranca():
    from modules.clan import clan_manager

    dados = request.json or {}

    resultado = clan_manager.transferir_lideranca(
        lider_id=dados.get("user_id"),
        novo_lider_id=dados.get("novo_lider_id")
    )

    return jsonify(resultado), (
        200 if resultado.get("success") else 400
    )


@webapp_bp.route('/api/clan/doar_ouro', methods=['POST'])
def api_clan_doar_ouro():
    from modules.clan import clan_manager

    dados = request.json or {}

    resultado = clan_manager.doar_ouro(
        user_id=dados.get("user_id"),
        quantidade=dados.get("quantidade")
    )

    return jsonify(resultado), (
        200 if resultado.get("success") else 400
    )

# ============================================================
# 💼 COMPRAR LICENÇA DA TESOURARIA
# ============================================================

@webapp_bp.route(
    '/api/clan/tesouraria/comprar',
    methods=['POST']
)
def api_clan_comprar_tesouraria():
    try:
        from modules.clan import (
            clan_manager
        )


        dados = request.json or {}


        resultado = (
            clan_manager
            .comprar_tesouraria(
                user_id=
                    dados.get(
                        "user_id"
                    )
            )
        )


        return jsonify(
            resultado
        ), (
            200
            if resultado.get(
                "success"
            )
            else 400
        )


    except Exception as e:

        traceback.print_exc()


        return jsonify({
            "success": False,

            "error": (
                "Erro ao ativar "
                "a Tesouraria: "
                f"{str(e)}"
            ),
        }), 500
    
# ============================================================
# 💰 ENVIAR OURO DO TESOURO PARA MEMBRO
# ============================================================

@webapp_bp.route(
    '/api/clan/tesouro/enviar',
    methods=['POST']
)
def api_clan_enviar_ouro_tesouro():
    try:
        from modules.clan import clan_manager

        dados = request.json or {}


        resultado = (
            clan_manager.enviar_ouro_tesouro(
                user_id=
                    dados.get(
                        "user_id"
                    ),

                alvo_id=
                    dados.get(
                        "alvo_id"
                    ),

                quantidade=
                    dados.get(
                        "quantidade"
                    ),
            )
        )


        return jsonify(
            resultado
        ), (
            200
            if resultado.get(
                "success"
            )
            else 400
        )


    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": (
                "Erro ao enviar ouro "
                "do tesouro: "
                f"{str(e)}"
            ),
        }), 500
    
@webapp_bp.route('/api/clan/melhorar', methods=['POST'])
def api_clan_melhorar():
    from modules.clan import clan_manager

    dados = request.json or {}

    resultado = clan_manager.melhorar_cla(
        dados.get("user_id")
    )

    return jsonify(resultado), (
        200 if resultado.get("success") else 400
    )

@webapp_bp.route(
    '/api/clan/alterar_logo',
    methods=['POST']
)
def api_clan_alterar_logo():
    try:
        from modules.clan import clan_manager

        dados = request.json or {}

        resultado = clan_manager.alterar_logo_cla(
            user_id=dados.get("user_id"),
            logo_id=dados.get("logo_id"),
        )

        return jsonify(resultado), (
            200
            if resultado.get("success")
            else 400
        )

    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": (
                "Erro ao alterar a logo do clã: "
                f"{str(e)}"
            ),
        }), 500
    
@webapp_bp.route('/api/clan/dissolver', methods=['POST'])
def api_clan_dissolver():
    from modules.clan import clan_manager

    dados = request.json or {}

    resultado = clan_manager.dissolver_cla(
        dados.get("user_id")
    )

    return jsonify(resultado), (
        200 if resultado.get("success") else 400
    )

# ==========================================
# 🔍 BUSCAS E LISTAGEM DE CLÃS
# ==========================================

@webapp_bp.route(
    '/api/clan/buscar_jogadores',
    methods=['GET']
)
def api_clan_buscar_jogadores():
    try:
        from modules.clan import clan_manager

        user_id = request.args.get("user_id")
        termo = request.args.get("termo", "")
        limite = request.args.get("limite", 15)

        resultado = (
            clan_manager
            .buscar_jogadores_para_convite(
                autor_id=user_id,
                termo=termo,
                limite=limite,
            )
        )

        return jsonify(resultado), (
            200
            if resultado.get("success")
            else 400
        )

    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": (
                "Erro ao buscar jogadores: "
                f"{str(e)}"
            ),
        }), 500


@webapp_bp.route(
    '/api/clan/listar',
    methods=['GET']
)
def api_clan_listar():
    try:
        from modules.clan import clan_manager

        termo = request.args.get("termo", "")
        limite = request.args.get("limite", 30)

        resultado = clan_manager.listar_clans(
            termo=termo,
            limite=limite,
        )

        return jsonify(resultado)

    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": (
                "Erro ao listar clãs: "
                f"{str(e)}"
            ),
        }), 500


@webapp_bp.route(
    '/api/clan/detalhes/<clan_id>',
    methods=['GET']
)
def api_clan_detalhes(clan_id):
    try:
        from modules.clan import clan_manager

        resultado = (
            clan_manager
            .obter_detalhes_publicos_cla(
                clan_id
            )
        )

        return jsonify(resultado), (
            200
            if resultado.get("success")
            else 404
        )

    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": (
                "Erro ao consultar o clã: "
                f"{str(e)}"
            ),
        }), 500

# ==========================================
# 🕵️ INSPECIONAR MEMBRO DO MESMO CLÃ
# ==========================================

@webapp_bp.route(
    '/api/clan/membro/<alvo_id>',
    methods=['GET']
)
def api_clan_inspecionar_membro(alvo_id):
    try:
        from modules.clan import clan_manager
        from modules import player_manager
        from modules.game_data import items as items_data

        solicitante_id = request.args.get("user_id")

        if not solicitante_id:
            return jsonify({
                "success": False,
                "error": "O jogador solicitante não foi informado."
            }), 400

        autorizacao = (
            clan_manager
            .validar_inspecao_membro(
                solicitante_id=solicitante_id,
                alvo_id=alvo_id,
            )
        )

        if not autorizacao.get("success"):
            return jsonify(autorizacao), 403

        if not ObjectId.is_valid(str(alvo_id)):
            return jsonify({
                "success": False,
                "error": "ID do membro inválido."
            }), 400

        alvo_object_id = ObjectId(str(alvo_id))

        jogador = users_collection.find_one({
            "_id": alvo_object_id
        })

        if not jogador:
            return jsonify({
                "success": False,
                "error": "Herói não encontrado."
            }), 404

        # Usa a fórmula oficial do projeto.
        totais = _run_async(
            player_manager.get_player_total_stats(
                jogador
            )
        )

        esquiva = int(
            _run_async(
                player_manager
                .get_player_dodge_chance(jogador)
            ) * 100
        )

        ataque_duplo = int(
            _run_async(
                player_manager
                .get_player_double_attack_chance(
                    jogador
                )
            ) * 100
        )

        inventario = jogador.get(
            "inventory",
            {},
        ) or {}

        equipamento_normal = jogador.get(
            "equipment",
            {},
        ) or {}

        equipamento_ferramentas = jogador.get(
            "equipment_tools",
            {},
        ) or {}

        equipamentos_formatados = []

        def adicionar_equipamento(
            slot,
            item_uid,
            tipo_slot="equipamento",
        ):
            if not item_uid:
                return

            item_obj = inventario.get(item_uid)

            if item_obj is None:
                item_obj = inventario.get(
                    str(item_uid)
                )

            if not isinstance(item_obj, dict):
                return

            base_id = item_obj.get(
                "base_id",
                str(item_uid),
            )

            info = items_data.ITEMS_DATA.get(
                base_id,
                {},
            ) or {}

            equipamentos_formatados.append({
                "slot": str(slot),
                "tipo_slot": tipo_slot,
                "uid": str(item_uid),
                "base_id": base_id,

                "nome": info.get(
                    "display_name",
                    item_obj.get(
                        "display_name",
                        str(base_id)
                        .replace("_", " ")
                        .title(),
                    ),
                ),

                "icone": info.get(
                    "emoji",
                    item_obj.get(
                        "emoji",
                        "📦",
                    ),
                ),

                "raridade": item_obj.get(
                    "rarity",
                    info.get(
                        "rarity",
                        "comum",
                    ),
                ),

                "refino": int(
                    item_obj.get(
                        "upgrade_level",
                        item_obj.get(
                            "refino",
                            0,
                        ),
                    ) or 0
                ),

                "stats": (
                    _formatar_stats_item_para_front(
                        item_obj
                    )
                ),
            })

        for slot, item_uid in equipamento_normal.items():
            adicionar_equipamento(
                slot=slot,
                item_uid=item_uid,
                tipo_slot="equipamento",
            )

        for profissao, item_uid in (
            equipamento_ferramentas.items()
        ):
            adicionar_equipamento(
                slot=f"tool_{profissao}",
                item_uid=item_uid,
                tipo_slot="ferramenta",
            )

        membro_cla = autorizacao.get(
            "membro",
            {},
        )

        entrou_em = membro_cla.get(
            "entrou_em"
        )

        if hasattr(entrou_em, "isoformat"):
            entrou_em = entrou_em.isoformat()

        profissao_raw = jogador.get(
            "profession"
        )

        profissao = {
            "nome": "Nenhuma",
            "nivel": 0,
        }

        if isinstance(profissao_raw, dict):
            profissao = {
                "nome": (
                    profissao_raw.get("display_name")
                    or profissao_raw.get("type")
                    or profissao_raw.get("key")
                    or "Profissão"
                ),
                "nivel": int(
                    profissao_raw.get(
                        "level",
                        1,
                    ) or 1
                ),
            }

        genero = str(
            jogador.get(
                "gender",
                "masculino",
            )
        ).lower()

        letra_genero = (
            "f"
            if genero.startswith("f")
            else "m"
        )

        avatar_padrao = (
            "https://raw.githubusercontent.com/"
            "Eldorabotpy/static-img/main/assets/"
            f"avatares/avatar_padrao_{letra_genero}.png"
        )

        avatar_id = jogador.get(
            "avatar_customizado",
            "padrao",
        )

        banner_id = jogador.get(
            "banner_customizado",
            "padrao",
        )

        avatar_url = avatar_padrao

        try:
            avatar_info = (
                CATALOGO_AVATARES.get(
                    avatar_id,
                    {},
                )
            )

            if isinstance(avatar_info, str):
                avatar_url = avatar_info

            elif isinstance(avatar_info, dict):
                avatar_url = (
                    avatar_info.get("imagem")
                    or avatar_info.get("image")
                    or avatar_info.get("url")
                    or avatar_info.get("src")
                    or avatar_padrao
                )

        except Exception:
            avatar_url = avatar_padrao

        banner_url = None

        try:
            banner_info = (
                CATALOGO_BANNERS.get(
                    banner_id,
                    {},
                )
            )

            if isinstance(banner_info, str):
                banner_url = banner_info

            elif isinstance(banner_info, dict):
                banner_url = (
                    banner_info.get("imagem")
                    or banner_info.get("image")
                    or banner_info.get("url")
                    or banner_info.get("src")
                )

        except Exception:
            banner_url = None

        hp_max = int(
            totais.get(
                "max_hp",
                jogador.get("max_hp", 100),
            ) or 100
        )

        mp_max = int(
            totais.get(
                "max_mana",
                jogador.get("max_mana", 50),
            ) or 50
        )

        return jsonify({
            "success": True,

            "membro": {
                "id": str(jogador["_id"]),

                "nome": jogador.get(
                    "character_name",
                    "Aventureiro",
                ),

                "classe": str(
                    jogador.get(
                        "class",
                        "aprendiz",
                    )
                ),

                "nivel": int(
                    jogador.get(
                        "level",
                        1,
                    ) or 1
                ),

                "genero": genero,

                "avatar_id": avatar_id,
                "avatar_url": avatar_url,

                "banner_id": banner_id,
                "banner_url": banner_url,

                "skin": jogador.get(
                    "equipped_skin"
                ),

                "cargo": membro_cla.get(
                    "cargo",
                    "membro",
                ),

                "contribuicao_ouro": int(
                    membro_cla.get(
                        "contribuicao_ouro",
                        0,
                    ) or 0
                ),

                "contribuicao_xp": int(
                    membro_cla.get(
                        "contribuicao_xp",
                        0,
                    ) or 0
                ),

                "entrou_em": entrou_em,

                "profissao": profissao,

                "hp_atual": min(
                    int(
                        jogador.get(
                            "current_hp",
                            hp_max,
                        ) or hp_max
                    ),
                    hp_max,
                ),

                "hp_max": hp_max,

                "mp_atual": min(
                    int(
                        jogador.get(
                            "current_mp",
                            mp_max,
                        ) or mp_max
                    ),
                    mp_max,
                ),

                "mp_max": mp_max,

                "status": {
                    "attack": int(
                        totais.get(
                            "attack",
                            jogador.get(
                                "attack",
                                0,
                            ),
                        ) or 0
                    ),

                    "defense": int(
                        totais.get(
                            "defense",
                            jogador.get(
                                "defense",
                                0,
                            ),
                        ) or 0
                    ),

                    "initiative": int(
                        totais.get(
                            "initiative",
                            jogador.get(
                                "initiative",
                                0,
                            ),
                        ) or 0
                    ),

                    "luck": int(
                        totais.get(
                            "luck",
                            jogador.get(
                                "luck",
                                0,
                            ),
                        ) or 0
                    ),

                    "esquiva": esquiva,
                    "ataque_duplo": ataque_duplo,
                },

                "equipamentos": equipamentos_formatados,
            }
        })

    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": (
                "Erro ao inspecionar membro: "
                f"{str(e)}"
            ),
        }), 500        

@webapp_bp.route(
    '/api/clan/configuracoes',
    methods=['POST']
)
def api_clan_atualizar_configuracoes():
    try:
        from modules.clan import clan_manager

        dados = request.json or {}

        resultado = (
            clan_manager
            .atualizar_configuracoes_cla(
                user_id=dados.get("user_id"),
                descricao=dados.get("descricao"),
                tipo_entrada=dados.get(
                    "tipo_entrada"
                ),
                nivel_minimo=dados.get(
                    "nivel_minimo"
                ),
            )
        )

        return jsonify(resultado), (
            200
            if resultado.get("success")
            else 400
        )

    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": (
                "Erro ao atualizar configurações: "
                f"{str(e)}"
            ),
        }), 500

# ============================================================
# 📜 MISSÕES DA GUILDA DOS AVENTUREIROS
# ============================================================
#
# IMPORTANTE:
# Sistema separado de player["quests"].
#
# guild_missions = contratos da Guilda
# quests         = história / evolução de classe
#
# ============================================================
# ============================================================
# 🔐 ACESSO À GUILDA DOS AVENTUREIROS
# ============================================================

def _status_acesso_guilda(
    user_id
):
    """
    Fonte oficial de autorização para os contratos
    da Guilda dos Aventureiros.

    Requisitos:
    - nível 20 ou superior
    - q7_selene_guildas concluída
    """

    try:
        uid_str = str(
            user_id
        )

        busca_id = (
            ObjectId(uid_str)
            if len(uid_str) == 24
            else int(uid_str)
        )

    except Exception:

        return {
            "success": False,
            "liberado": False,
            "error":
                "Identidade do aventureiro inválida.",
        }


    jogador = users_collection.find_one(
        {
            "_id": busca_id
        }
    )


    if not jogador:

        return {
            "success": False,
            "liberado": False,
            "error":
                "Aventureiro não encontrado.",
        }


    try:
        nivel = int(
            jogador.get(
                "level",
                1
            ) or 1
        )

    except (
        TypeError,
        ValueError,
    ):
        nivel = 1


    quests = (
        jogador.get(
            "quests",
            {}
        )
        or {}
    )


    q7 = (
        quests.get(
            "q7_selene_guildas",
            {}
        )
        or {}
    )


    q7_concluida = (
        q7.get("status")
        == "resgatada"
    )


    liberado = (
        nivel >= 20
        and
        q7_concluida
    )


    # ========================================================
    # 🔄 AUTOCORREÇÃO DO FLAG DE ACESSO
    # ========================================================

    if (
        liberado
        and
        not jogador.get(
            "guild_access_unlocked",
            False
        )
    ):

        users_collection.update_one(
            {
                "_id": busca_id
            },
            {
                "$set": {
                    "guild_access_unlocked":
                        True
                }
            }
        )


    apresentacao_concluida = bool(
        jogador.get(
            "guild_intro_seen",
            False
        )
    )


    if nivel < 20:

        mensagem = (
            "A Guilda dos Aventureiros ainda não "
            "aceita seus contratos. Alcance o Nível 20 "
            "e prove seu valor perante a Arquimaga Selene."
        )

    elif not q7_concluida:

        mensagem = (
            "Seu nível é suficiente, mas falta o "
            "reconhecimento oficial da Capital. "
            "Procure a Arquimaga Selene."
        )

    else:

        mensagem = (
            "A Carta de Recomendação foi reconhecida. "
            "Bem-vindo à Guilda dos Aventureiros."
        )


    return {
        "success": True,

        "liberado":
            liberado,

        "nivel":
            nivel,

        "q7_concluida":
            q7_concluida,

        "guild_access_unlocked":
            liberado,

        "apresentacao_pendente":
            (
                liberado
                and
                not apresentacao_concluida
            ),

        "apresentacao_concluida":
            apresentacao_concluida,

        "message":
            mensagem,
    }


# ============================================================
# 🛡️ CONSULTAR ACESSO À GUILDA
# ============================================================

@webapp_bp.route(
    '/api/guild/acesso/<user_id>',
    methods=['GET']
)
def api_guild_acesso(
    user_id
):

    resultado = (
        _status_acesso_guilda(
            user_id
        )
    )

    return jsonify(
        resultado
    ), (
        200
        if resultado.get("success")
        else 400
    )


# ============================================================
# 🏰 CONCLUIR APRESENTAÇÃO NA GUILDA
# ============================================================

@webapp_bp.route(
    '/api/guild/apresentacao/concluir',
    methods=['POST']
)
def api_guild_concluir_apresentacao():

    dados = (
        request.get_json(
            silent=True
        )
        or {}
    )


    user_id = dados.get(
        "user_id"
    )


    if not user_id:

        return jsonify({
            "success": False,
            "error":
                "ID do aventureiro não informado.",
        }), 400


    acesso = (
        _status_acesso_guilda(
            user_id
        )
    )


    if not acesso.get(
        "success"
    ):

        return jsonify(
            acesso
        ), 400


    if not acesso.get(
        "liberado"
    ):

        return jsonify({
            "success": False,
            "guild_locked": True,
            "error":
                acesso.get(
                    "message"
                ),
        }), 403


    try:
        uid_str = str(
            user_id
        )

        busca_id = (
            ObjectId(uid_str)
            if len(uid_str) == 24
            else int(uid_str)
        )

    except Exception:

        return jsonify({
            "success": False,
            "error":
                "Identidade inválida.",
        }), 400


    users_collection.update_one(
        {
            "_id": busca_id
        },
        {
            "$set": {
                "guild_intro_seen":
                    True
            }
        }
    )


    return jsonify({
        "success": True,

        "message":
            "Registro concluído. "
            "Você agora é reconhecido oficialmente "
            "pela Guilda dos Aventureiros.",
    })

# ============================================================
# 📖 LISTAR MISSÕES
# ============================================================

@webapp_bp.route(
    '/api/guild/missoes/<user_id>',
    methods=['GET']
)
def api_guild_listar_missoes(user_id):
    try:

        acesso = (
            _status_acesso_guilda(
                user_id
            )
        )

        if not acesso.get("success"):
            return jsonify(
                acesso
            ), 400

        if not acesso.get("liberado"):
            return jsonify({
                "success": False,
                "guild_locked": True,
                "error":
                    acesso.get(
                        "message"
                    ),
            }), 403

        from modules.guild_missions import (
            guild_mission_manager
        )

        resultado = (
            guild_mission_manager
            .listar_missoes_jogador(
                user_id
            )
        )

        return jsonify(resultado), (
            200
            if resultado.get("success")
            else 400
        )

    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": (
                "Erro ao carregar as missões "
                f"da Guilda: {str(e)}"
            ),
        }), 500


# ============================================================
# 📜 ACEITAR MISSÃO
# ============================================================

@webapp_bp.route(
    '/api/guild/missoes/aceitar',
    methods=['POST']
)
def api_guild_aceitar_missao():
    try:
        from modules.guild_missions import (
            guild_mission_manager
        )

        dados = request.json or {}

        user_id = dados.get("user_id")
        missao_id = dados.get("missao_id")

        if not user_id:
            return jsonify({
                "success": False,
                "error": "ID do jogador não informado.",
            }), 400

        if not missao_id:
            return jsonify({
                "success": False,
                "error": "Missão não informada.",
            }), 400

        acesso = (
            _status_acesso_guilda(
                user_id
            )
        )

        if not acesso.get("success"):
            return jsonify(
                acesso
            ), 400

        if not acesso.get("liberado"):
            return jsonify({
                "success": False,
                "guild_locked": True,
                "error":
                    acesso.get(
                        "message"
                    ),
            }), 403
        
        resultado = (
            guild_mission_manager
            .aceitar_missao(
                user_id=user_id,
                missao_id=missao_id,
            )
        )

        return jsonify(resultado), (
            200
            if resultado.get("success")
            else 400
        )

    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": (
                "Erro ao aceitar missão "
                f"da Guilda: {str(e)}"
            ),
        }), 500


# ============================================================
# 🎁 RESGATAR RECOMPENSA
# ============================================================

@webapp_bp.route(
    '/api/guild/missoes/resgatar',
    methods=['POST']
)
def api_guild_resgatar_missao():
    try:
        from modules.guild_missions import (
            guild_mission_manager
        )

        dados = request.json or {}

        user_id = dados.get("user_id")
        missao_id = dados.get("missao_id")

        if not user_id:
            return jsonify({
                "success": False,
                "error": "ID do jogador não informado.",
            }), 400

        if not missao_id:
            return jsonify({
                "success": False,
                "error": "Missão não informada.",
            }), 400

        acesso = (
            _status_acesso_guilda(
                user_id
            )
        )

        if not acesso.get("success"):
            return jsonify(
                acesso
            ), 400

        if not acesso.get("liberado"):
            return jsonify({
                "success": False,
                "guild_locked": True,
                "error":
                    acesso.get(
                        "message"
                    ),
            }), 403

        resultado = (
            guild_mission_manager
            .resgatar_recompensa(
                user_id=user_id,
                missao_id=missao_id,
            )
        )

        return jsonify(resultado), (
            200
            if resultado.get("success")
            else 400
        )

    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": (
                "Erro ao resgatar recompensa "
                f"da Guilda: {str(e)}"
            ),
        }), 500


# ============================================================
# 🧪 VALIDAR CATÁLOGO
# ============================================================

@webapp_bp.route(
    '/api/guild/missoes/validar',
    methods=['GET']
)
def api_guild_validar_catalogo():
    try:
        from modules.guild_missions.guild_mission_registry import (
            validar_catalogo_missoes,
        )

        erros = validar_catalogo_missoes()

        return jsonify({
            "success": len(erros) == 0,
            "total_erros": len(erros),
            "erros": erros,
        }), (
            200
            if len(erros) == 0
            else 400
        )

    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": (
                "Erro ao validar catálogo "
                f"da Guilda: {str(e)}"
            ),
        }), 500    

# ============================================================
# 🏪 LOJA DA GUILDA DOS AVENTUREIROS
# ============================================================


# ============================================================
# 📦 CATÁLOGO DA LOJA
# ============================================================

@webapp_bp.route(
    '/api/guild/loja/<user_id>',
    methods=['GET']
)
def api_guild_loja_catalogo(
    user_id
):
    try:

        from modules.guild_missions import (
            guild_shop_manager,
        )


        resultado = (
            guild_shop_manager
            .obter_catalogo_loja_guilda(
                user_id
            )
        )


        return jsonify(
            resultado
        ), (
            200
            if resultado.get(
                "success"
            )
            else 400
        )


    except Exception as e:

        traceback.print_exc()


        return jsonify({
            "success": False,

            "error": (
                "Erro ao carregar a Loja "
                "da Guilda: "
                f"{str(e)}"
            ),
        }), 500


# ============================================================
# 🛒 COMPRAR RECEITA
# ============================================================

@webapp_bp.route(
    '/api/guild/loja/comprar',
    methods=['POST']
)
def api_guild_loja_comprar():
    try:

        from modules.guild_missions import (
            guild_shop_manager,
        )


        dados = (
            request.get_json(
                silent=True
            )
            or {}
        )


        user_id = dados.get(
            "user_id"
        )


        item_id = dados.get(
            "item_id"
        )


        if not user_id:

            return jsonify({
                "success": False,
                "error": (
                    "ID do jogador "
                    "não informado."
                ),
            }), 400


        if not item_id:

            return jsonify({
                "success": False,
                "error": (
                    "Produto não informado."
                ),
            }), 400


        resultado = (
            guild_shop_manager
            .comprar_item_loja_guilda(

                user_id=
                    user_id,

                item_id=
                    item_id,
            )
        )


        return jsonify(
            resultado
        ), (
            200
            if resultado.get(
                "success"
            )
            else 400
        )


    except Exception as e:

        traceback.print_exc()


        return jsonify({
            "success": False,

            "error": (
                "Erro ao realizar compra "
                "na Loja da Guilda: "
                f"{str(e)}"
            ),
        }), 500

# ============================================================
# 🏰 MISSÕES COLETIVAS DO CLÃ - GUILDA DOS AVENTUREIROS
# ============================================================


# ============================================================
# 📖 LISTAR MISSÕES COLETIVAS
# ============================================================

@webapp_bp.route(
    "/api/guild/cla/missoes/<user_id>",
    methods=["GET"]
)
def api_guild_cla_listar_missoes(user_id):

    try:
        from modules.guild_missions.clan_guild_mission_manager import (
            listar_missoes_cla
        )

        resultado = listar_missoes_cla(
            user_id=user_id
        )

        return jsonify(
            resultado
        ), (
            200
            if resultado.get("success")
            else 400
        )

    except Exception as erro:

        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": (
                "Erro ao consultar missões "
                f"coletivas do clã: {erro}"
            ),
        }), 500


# ============================================================
# 📜 ACEITAR MISSÃO COLETIVA
# ============================================================

@webapp_bp.route(
    "/api/guild/cla/missoes/aceitar",
    methods=["POST"]
)
def api_guild_cla_aceitar_missao():

    try:
        from modules.guild_missions.clan_guild_mission_manager import (
            aceitar_missao_cla
        )

        dados = request.json or {}

        user_id = dados.get(
            "user_id"
        )

        missao_id = dados.get(
            "missao_id"
        )


        if not user_id:

            return jsonify({
                "success": False,
                "error": (
                    "ID do jogador não informado."
                ),
            }), 400


        if not missao_id:

            return jsonify({
                "success": False,
                "error": (
                    "ID da missão não informado."
                ),
            }), 400


        resultado = aceitar_missao_cla(
            user_id=user_id,
            missao_id=missao_id,
        )


        return jsonify(
            resultado
        ), (
            200
            if resultado.get("success")
            else 400
        )


    except Exception as erro:

        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": (
                "Erro ao aceitar missão "
                f"coletiva: {erro}"
            ),
        }), 500


# ============================================================
# 🎁 RESGATAR MISSÃO COLETIVA
# ============================================================

@webapp_bp.route(
    "/api/guild/cla/missoes/resgatar",
    methods=["POST"]
)
def api_guild_cla_resgatar_missao():

    try:
        from modules.guild_missions.clan_guild_mission_manager import (
            resgatar_recompensa_cla
        )

        dados = request.json or {}

        user_id = dados.get(
            "user_id"
        )

        missao_id = dados.get(
            "missao_id"
        )


        if not user_id:

            return jsonify({
                "success": False,
                "error": (
                    "ID do jogador não informado."
                ),
            }), 400


        if not missao_id:

            return jsonify({
                "success": False,
                "error": (
                    "ID da missão não informado."
                ),
            }), 400


        resultado = (
            resgatar_recompensa_cla(
                user_id=user_id,
                missao_id=missao_id,
            )
        )


        return jsonify(
            resultado
        ), (
            200
            if resultado.get("success")
            else 400
        )


    except Exception as erro:

        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": (
                "Erro ao entregar missão "
                f"coletiva: {erro}"
            ),
        }), 500

