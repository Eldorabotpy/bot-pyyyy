# rotas/admin.py
import os
import traceback

from functools import wraps
from io import BytesIO

from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
    session,
    redirect,
    url_for,
    send_file,
    current_app,
)

from werkzeug.security import (
    check_password_hash,
)

# Importações necessárias do seu sistema
from modules.player.core import users_collection
from modules.game_data.season_pass import adicionar_xp_passe

# 1. Cria o Blueprint para as rotas administrativas
admin_bp = Blueprint('admin_bp', __name__)
# ============================================================
# 🔐 AUTENTICAÇÃO DO PAINEL GM
# ============================================================

ADMIN_USERNAME = str(
    os.getenv(
        "ADMIN_USERNAME",
        ""
    )
).strip()


ADMIN_PASSWORD_HASH = str(
    os.getenv(
        "ADMIN_PASSWORD_HASH",
        ""
    )
).strip()


def admin_required(funcao):

    @wraps(funcao)
    def wrapper(*args, **kwargs):

        if not session.get(
            "eldora_admin_autenticado"
        ):

            if request.path.startswith(
                "/admin/api/"
            ):

                return jsonify({
                    "success": False,
                    "error":
                        "Acesso administrativo não autorizado."
                }), 401


            return redirect(
                url_for(
                    "admin_bp.admin_login"
                )
            )


        return funcao(
            *args,
            **kwargs
        )


    return wrapper


# ============================================================
# 🔑 LOGIN
# ============================================================

@admin_bp.route(
    "/admin/login",
    methods=[
        "GET",
        "POST",
    ]
)
def admin_login():

    erro = None


    if request.method == "POST":

        usuario = str(
            request.form.get(
                "usuario",
                ""
            )
        ).strip()


        senha = str(
            request.form.get(
                "senha",
                ""
            )
        )


        configurado = (
            bool(ADMIN_USERNAME)
            and bool(
                ADMIN_PASSWORD_HASH
            )
        )


        if not configurado:

            erro = (
                "Administrador não configurado "
                "no servidor."
            )


        elif (
            usuario == ADMIN_USERNAME
            and check_password_hash(
                ADMIN_PASSWORD_HASH,
                senha,
            )
        ):

            session.clear()

            session[
                "eldora_admin_autenticado"
            ] = True

            session[
                "eldora_admin_usuario"
            ] = ADMIN_USERNAME


            return redirect(
                url_for(
                    "admin_bp.abrir_painel_admin"
                )
            )


        else:

            erro = (
                "Usuário ou senha incorretos."
            )


    return render_template(
        "admin_login.html",
        erro=erro,
    )


# ============================================================
# 🚪 LOGOUT
# ============================================================

@admin_bp.route(
    "/admin/logout"
)
def admin_logout():

    session.clear()

    return redirect(
        url_for(
            "admin_bp.admin_login"
        )
    )

# --- ROTAS DE GESTÃO DO PASSE E RECURSOS ---

@admin_bp.route('/admin/add_gems/<nome_personagem>/<int:quantidade>')
@admin_required
def admin_add_gems(nome_personagem, quantidade):
    pdata = users_collection.find_one({"character_name": nome_personagem})
    if pdata:
        nova_quantidade = pdata.get("gems", 0) + quantidade
        users_collection.update_one(
            {"_id": pdata["_id"]}, 
            {"$set": {"gems": nova_quantidade}}
        )
        return jsonify({
            "status": "success", 
            "msg": f"💎 {quantidade} Gemas enviadas para {nome_personagem}! Saldo total: {nova_quantidade}"
        })
    return jsonify({"status": "error", "msg": "Personagem não encontrado!"}), 404

@admin_bp.route('/admin/add_xp/<nome_personagem>/<int:quantidade>')
@admin_required
def admin_add_xp(nome_personagem, quantidade):
    pdata = users_collection.find_one({"character_name": nome_personagem})
    if pdata:
        subiu, nivel, xp_atual = adicionar_xp_passe(pdata, quantidade)
        users_collection.update_one(
            {"_id": pdata["_id"]}, 
            {"$set": {"passe_batalha": pdata['passe_batalha']}}
        )
        return jsonify({
            "status": "success", 
            "msg": f"✨ XP Adicionado para {nome_personagem}! Nível: {nivel} | XP: {xp_atual}"
        })
    return jsonify({"status": "error", "msg": "Personagem não encontrado!"}), 404

@admin_bp.route('/admin/reset_passe/<nome_personagem>')
@admin_required
def admin_reset_passe(nome_personagem):
    pdata = users_collection.find_one({"character_name": nome_personagem})
    if pdata:
        novo_passe = {
            "level": 1, "xp": 0, "is_premium": False,
            "resgatados_free": [], "resgatados_premium": []
        }
        users_collection.update_one(
            {"_id": pdata["_id"]}, 
            {"$set": {"passe_batalha": novo_passe}}
        )
        return jsonify({"status": "success", "msg": f"Passe de {nome_personagem} foi resetado com sucesso!"})
    return jsonify({"status": "error", "msg": "Personagem não encontrado!"}), 404

@admin_bp.route('/admin/reset_global_passe')
@admin_required
def admin_reset_global_passe():
    try:
        novo_passe = {
            "level": 1, "xp": 0, "is_premium": False, 
            "resgatados_free": [], "resgatados_premium": []
        }
        resultado = users_collection.update_many(
            {}, 
            {"$set": {"passe_batalha": novo_passe}}
        )
        return jsonify({
            "status": "success", 
            "msg": f"🚨 NOVA TEMPORADA INICIADA! O passe de {resultado.modified_count} personagens foi zerado com sucesso!"
        })
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500

# --- ROTAS DE INTERFACE E DEBUG ---

@admin_bp.route('/admin/painel')
@admin_required
def abrir_painel_admin():
    return render_template('admin_panel.html')

# ============================================================
# 💎 LOJA PREMIUM - PAINEL ADMINISTRATIVO
# ============================================================


# ============================================================
# 📋 LISTAR PEDIDOS
# ============================================================

@admin_bp.route(
    "/admin/api/premium/pedidos",
    methods=["GET"]
)
@admin_required
def admin_premium_listar_pedidos():
    try:
        from modules import (
            premium_store_manager
        )


        status = request.args.get(
            "status"
        )


        limite = request.args.get(
            "limite",
            100
        )


        resultado = (
            premium_store_manager
            .listar_pedidos_admin(
                status=status,
                limite=limite,
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
                f"Erro ao listar pedidos: {str(e)}",
        }), 500


# ============================================================
# 🖼️ ABRIR COMPROVANTE
# ============================================================

@admin_bp.route(
    "/admin/api/premium/comprovante/<codigo_pedido>",
    methods=["GET"]
)
@admin_required
def admin_premium_comprovante(
    codigo_pedido
):
    try:
        from modules import (
            premium_store_manager
        )


        resultado = (
            premium_store_manager
            .obter_comprovante_admin(
                codigo_pedido
            )
        )


        if not resultado.get(
            "success"
        ):
            return jsonify(
                resultado
            ), 404


        resposta = send_file(
            BytesIO(
                resultado["dados"]
            ),

            mimetype=
                resultado.get(
                    "mime_type",
                    "application/octet-stream",
                ),

            download_name=
                resultado.get(
                    "nome",
                    "comprovante",
                ),

            as_attachment=False,
        )


        # Impede o navegador de tentar
        # adivinhar outro tipo de arquivo.
        resposta.headers[
            "X-Content-Type-Options"
        ] = "nosniff"


        return resposta


    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error":
                f"Erro ao abrir comprovante: {str(e)}",
        }), 500


# ============================================================
# ✅ APROVAR PEDIDO
# ============================================================

@admin_bp.route(
    "/admin/api/premium/aprovar",
    methods=["POST"]
)
@admin_required
def admin_premium_aprovar():
    try:
        from modules import (
            premium_store_manager
        )


        dados = request.get_json(
            silent=True
        ) or {}


        codigo = str(
            dados.get(
                "codigo_pedido",
                ""
            )
        ).strip()


        if not codigo:
            return jsonify({
                "success": False,
                "error":
                    "Pedido não informado.",
            }), 400


        admin_usuario = session.get(
            "eldora_admin_usuario",
            "admin",
        )


        resultado = (
            premium_store_manager
            .aprovar_pedido_manual(
                codigo_pedido=
                    codigo,

                aprovado_por=
                    admin_usuario,
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
                f"Erro ao aprovar pedido: {str(e)}",
        }), 500


# ============================================================
# ❌ RECUSAR PEDIDO
# ============================================================

@admin_bp.route(
    "/admin/api/premium/recusar",
    methods=["POST"]
)
@admin_required
def admin_premium_recusar():
    try:
        from modules import (
            premium_store_manager
        )


        dados = request.get_json(
            silent=True
        ) or {}


        codigo = str(
            dados.get(
                "codigo_pedido",
                ""
            )
        ).strip()


        motivo = str(
            dados.get(
                "motivo",
                ""
            )
        ).strip()


        if not codigo:
            return jsonify({
                "success": False,
                "error":
                    "Pedido não informado.",
            }), 400


        admin_usuario = session.get(
            "eldora_admin_usuario",
            "admin",
        )


        resultado = (
            premium_store_manager
            .recusar_pedido_manual(
                codigo_pedido=
                    codigo,

                recusado_por=
                    admin_usuario,

                motivo=
                    motivo,
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
                f"Erro ao recusar pedido: {str(e)}",
        }), 500
    
@admin_bp.route('/debug/ganhar_xp_teste/<user_id>')
@admin_required
def debug_xp(user_id):
    pdata = users_collection.find_one({"telegram_id": int(user_id)})
    if pdata:
        subiu, nivel, xp_atual = adicionar_xp_passe(pdata, 500)
        users_collection.update_one(
            {"_id": pdata["_id"]}, 
            {"$set": {"passe_batalha": pdata['passe_batalha']}}
        )
        return f"✨ XP Adicionado! {pdata.get('character_name')} agora tem {xp_atual}/1000 no Nível {nivel}"
    return "Jogador não encontrado", 404

# ============================================================
# ⚔️ GUERRA DE CLÃS — CONTROLE GM
# ============================================================

@admin_bp.route(
    "/admin/api/guerra/teste/estado",
    methods=["GET"]
)
@admin_required
def admin_guerra_teste_estado():
    try:

        from modules.clan import (
            clan_war_manager
        )


        calendario = (
            clan_war_manager
            .obter_estado_calendario()
        )


        controle = (
            clan_war_manager
            .obter_controle_teste_guerra()
        )


        return jsonify({
            "success":
                True,

            "calendario":
                clan_war_manager
                .serializar_calendario(
                    calendario
                ),

            "controle":
                clan_war_manager
                ._json_seguro(
                    controle
                ),
        })


    except Exception as e:

        traceback.print_exc()


        return jsonify({
            "success":
                False,

            "error":
                str(e),
        }), 500


# ============================================================
# 🧪 FORÇAR FASE
# ============================================================

@admin_bp.route(
    "/admin/api/guerra/teste/fase",
    methods=["POST"]
)
@admin_required
def admin_guerra_teste_fase():
    try:

        from modules.clan import (
            clan_war_manager
        )


        dados = (
            request.get_json(
                silent=True
            )
            or {}
        )


        fase = str(
            dados.get(
                "fase",
                ""
            )
        ).strip()


        admin_usuario = (
            session.get(
                "eldora_admin_usuario",
                "GM"
            )
        )


        resultado = (
            clan_war_manager
            .definir_fase_teste_guerra(
                fase=
                    fase,

                alterado_por=
                    admin_usuario,
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
                str(e),
        }), 500


# ============================================================
# 🌐 VOLTAR AO CALENDÁRIO REAL
# ============================================================

@admin_bp.route(
    "/admin/api/guerra/teste/calendario-real",
    methods=["POST"]
)
@admin_required
def admin_guerra_calendario_real():
    try:

        from modules.clan import (
            clan_war_manager
        )


        admin_usuario = (
            session.get(
                "eldora_admin_usuario",
                "GM"
            )
        )


        resultado = (
            clan_war_manager
            .desativar_teste_guerra(
                alterado_por=
                    admin_usuario
            )
        )


        return jsonify(
            resultado
        )


    except Exception as e:

        traceback.print_exc()


        return jsonify({
            "success":
                False,

            "error":
                str(e),
        }), 500


# ============================================================
# 🔓 DESTRAVAR ESCALAÇÕES
# ============================================================

@admin_bp.route(
    "/admin/api/guerra/teste/destravar-escalacoes",
    methods=["POST"]
)
@admin_required
def admin_guerra_destravar_escalacoes():
    try:

        from modules.clan import (
            clan_war_manager
        )


        resultado = (
            clan_war_manager
            .gm_destravar_escalacoes()
        )


        return jsonify(
            resultado
        )


    except Exception as e:

        traceback.print_exc()


        return jsonify({
            "success":
                False,

            "error":
                str(e),
        }), 500

# ============================================================
# 🔄 GM — REINICIAR BATALHA DE UMA FRENTE
# ============================================================

@admin_bp.route(
    "/admin/api/guerra/teste/reiniciar-frente",
    methods=["POST"]
)
@admin_required
def admin_guerra_reiniciar_frente():

    try:

        from modules.clan import (
            clan_war_manager
        )


        dados = (
            request.get_json(
                silent=True
            )
            or {}
        )


        nome_personagem = str(
            dados.get(
                "nome_personagem",
                ""
            )
        ).strip()


        if not nome_personagem:

            return jsonify({
                "success": False,
                "error":
                    "Informe um personagem titular "
                    "da frente.",
            }), 400


        jogador = (
            users_collection
            .find_one({
                "character_name":
                    nome_personagem
            })
        )


        if not jogador:

            return jsonify({
                "success": False,

                "error":
                    (
                        "Personagem "
                        f"'{nome_personagem}' "
                        "não encontrado."
                    ),
            }), 404


        admin_usuario = (
            session.get(
                "eldora_admin_usuario",
                "GM"
            )
        )


        resultado = (
            clan_war_manager
            .gm_reiniciar_batalha_frente(

                user_id=
                    jogador["_id"],

                alterado_por=
                    admin_usuario,
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
                str(e),
        }), 500
        
# ============================================================
# ⚖️ GM — EXECUTAR PAREAMENTO
# ============================================================

@admin_bp.route(
    "/admin/api/guerra/teste/parear",
    methods=["POST"]
)
@admin_required
def admin_guerra_executar_pareamento():
    try:

        from modules.clan import (
            clan_war_manager
        )


        admin_usuario = (
            session.get(
                "eldora_admin_usuario",
                "GM"
            )
        )


        resultado = (
            clan_war_manager
            .executar_pareamento_semana(
                executado_por=
                    admin_usuario
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
                str(e),
        }), 500    

# ============================================================
# ⚔️ GM — INICIAR INVASÃO MANUALMENTE
# ============================================================

@admin_bp.route(
    "/admin/api/invasao/iniciar",
    methods=["POST"]
)
@admin_required
def admin_iniciar_invasao():
    try:

        sistema_invasao = current_app.config.get(
            "SISTEMA_INVASAO_MAPA"
        )

        jogadores_online = current_app.config.get(
            "JOGADORES_ONLINE",
            {}
        )

        if sistema_invasao is None:
            return jsonify({
                "success": False,
                "error":
                    "Sistema de invasão não está disponível."
            }), 500

        sistema_invasao.iniciar_invasao(
            jogadores_online
        )

        return jsonify({
            "success": True,
            "message":
                "⚔️ Invasão iniciada manualmente pelo GM."
        })

    except Exception:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error":
                "Erro ao iniciar a invasão."
        }), 500


# ============================================================
# 🧹 GM — LIMPAR TODAS AS PARTIES
# ============================================================

@admin_bp.route(
    "/admin/api/parties/resetar",
    methods=["POST"]
)
@admin_required
def admin_resetar_parties():
    try:

        from modules.combat.party_engine import (
            parties_collection
        )

        resultado = parties_collection.delete_many(
            {}
        )

        return jsonify({
            "success": True,
            "message":
                (
                    "🧹 Parties removidas com sucesso. "
                    f"Total removido: {resultado.deleted_count}"
                ),
            "removidas":
                int(resultado.deleted_count)
        })

    except Exception:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error":
                "Erro ao limpar as parties."
        }), 500
        