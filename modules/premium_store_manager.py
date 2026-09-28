# ============================================================
# 💎 MUNDO DE ELDORA - GERENCIADOR DA LOJA PREMIUM
# ============================================================

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import certifi
import gridfs
from bson import ObjectId
from pymongo import (
    ASCENDING,
    DESCENDING,
    MongoClient,
    ReturnDocument,
)

from modules.premium_store_registry import (
    formatar_valor_reais,
    listar_pacotes_gemas,
    obter_eldora_premium,
    obter_pacote_gemas,
    obter_produto_loja,
)


MONGO_CONN_STR = os.getenv(
    "MONGO_CONNECTION_STRING"
)

PEDIDO_EXPIRA_HORAS = 24

STATUS_AGUARDANDO_PAGAMENTO = (
    "aguardando_pagamento"
)

STATUS_EM_ANALISE = "em_analise"

STATUS_PROCESSANDO_APROVACAO = (
    "processando_aprovacao"
)

STATUS_APROVADO = "aprovado"
STATUS_RECUSADO = "recusado"
STATUS_CANCELADO = "cancelado"
STATUS_EXPIRADO = "expirado"

CUSTO_TROCA_CLASSE = 550
CUSTO_TROCA_PROFISSAO = 250

SKILLS_INICIAIS_CLASSE = {
    "guerreiro": "guerreiro_corte_perfurante",
    "mago": "mago_bola_de_fogo",
    "cacador": "cacador_flecha_precisa",
    "assassino": "assassino_ataque_furtivo",
    "monge": "monge_rajada_de_punhos",
    "samurai": "samurai_corte_iaijutsu",
    "berserker": "berserker_golpe_selvagem",
    "curandeiro": "curandeiro_chama_sagrada",
    "bardo": "bardo_nota_cortante",
}


# ============================================================
# 🗄️ BANCO DE DADOS
# ============================================================

try:
    client = MongoClient(
        MONGO_CONN_STR,
        tlsCAFile=certifi.where(),
        tz_aware=True,
    )

    db = client["eldora_db"]

    premium_orders_col = db[
        "premium_store_orders"
    ]

    counters_col = db[
        "counters"
    ]

    users_col = db[
        "users"
    ]

    premium_receipts_fs = gridfs.GridFS(
        db,
        collection="premium_store_receipts",
    )

    premium_orders_col.create_index(
        "codigo",
        unique=True,
    )

    premium_orders_col.create_index(
        [
            ("user_id", ASCENDING),
            ("criado_em", DESCENDING),
        ]
    )

    premium_orders_col.create_index(
        [
            ("status", ASCENDING),
            ("criado_em", DESCENDING),
        ]
    )


except Exception as erro:
    print(
        "🔥 [LOJA PREMIUM] "
        f"Falha ao conectar ao MongoDB: {erro}"
    )

    client = None
    db = None

    premium_orders_col = None
    counters_col = None
    users_col = None
    premium_receipts_fs = None


# ============================================================
# 🔧 HELPERS
# ============================================================

def _agora():
    return datetime.now(
        timezone.utc
    )

def _normalizar_datetime_utc(
    valor,
):
    if not isinstance(
        valor,
        datetime,
    ):
        return valor


    # MongoDB/PyMongo pode devolver
    # datetime sem tzinfo.
    #
    # Como as datas da Loja são gravadas
    # em UTC, tratamos datetime antigo
    # sem timezone como UTC.
    if valor.tzinfo is None:

        return valor.replace(
            tzinfo=timezone.utc
        )


    return valor.astimezone(
        timezone.utc
    )

def _calcular_expiracao_eldora_premium(
    expira_atual,
    dias,
    agora=None,
):

    agora = _normalizar_datetime_utc(
        agora or _agora()
    )


    expira_atual = (
        _normalizar_datetime_utc(
            expira_atual
        )
    )


    dias = max(
        0,
        int(
            dias or 0
        ),
    )


    if dias <= 0:
        return None


    base = agora


    if (
        isinstance(
            expira_atual,
            datetime,
        )
        and expira_atual > agora
    ):
        base = expira_atual


    return (
        base
        + timedelta(
            days=dias
        )
    )

def _quantidade_chaves_masmorra(
    item,
):

    if isinstance(
        item,
        dict,
    ):

        try:
            return max(
                0,
                int(
                    item.get(
                        "quantity",
                        0,
                    )
                    or 0
                ),
            )

        except (
            TypeError,
            ValueError,
        ):
            return 0


    if isinstance(
        item,
        int,
    ):

        return max(
            0,
            int(item),
        )


    return 0


def _montar_chave_masmorra(
    item_atual,
    adicionar,
):

    quantidade_atual = (
        _quantidade_chaves_masmorra(
            item_atual
        )
    )


    adicionar = max(
        0,
        int(
            adicionar or 0
        ),
    )


    novo_item = {}


    if isinstance(
        item_atual,
        dict,
    ):
        novo_item = dict(
            item_atual
        )


    novo_item[
        "base_id"
    ] = "chave_masmorra"

    novo_item[
        "quantity"
    ] = (
        quantidade_atual
        + adicionar
    )


    return novo_item

def _montar_estado_eldora_premium(
    premium_atual,
    dias,
    trocas_classe,
    codigo_pedido,
    agora=None,
):

    agora = _normalizar_datetime_utc(
        agora or _agora()
    )


    if not isinstance(
        premium_atual,
        dict,
    ):
        premium_atual = {}


    expiracao_atual = (
        _normalizar_datetime_utc(
            premium_atual.get(
                "expires_at"
            )
        )
    )


    premium_ativo = (
        isinstance(
            expiracao_atual,
            datetime,
        )
        and expiracao_atual > agora
    )


    creditos_atuais = 0


    if premium_ativo:

        try:
            creditos_atuais = max(
                0,
                int(
                    premium_atual.get(
                        "class_change_credits",
                        0,
                    )
                    or 0
                ),
            )

        except (
            TypeError,
            ValueError,
        ):
            creditos_atuais = 0


    novos_creditos = (
        creditos_atuais
        + max(
            0,
            int(
                trocas_classe or 0
            ),
        )
    )


    nova_expiracao = (
        _calcular_expiracao_eldora_premium(
            expiracao_atual,
            dias,
            agora,
        )
    )


    activated_at = agora


    if premium_ativo:

        activated_at = (
            _normalizar_datetime_utc(
                premium_atual.get(
                    "activated_at"
                )
            )
            or agora
        )


    return {
        "activated_at":
            activated_at,

        "expires_at":
            nova_expiracao,

        "class_change_credits":
            novos_creditos,

        "last_order_code":
            str(
                codigo_pedido or ""
            ).strip(),

        "updated_at":
            agora,
    }

def _obter_status_eldora_premium(
    jogador,
    agora=None,
):

    agora = _normalizar_datetime_utc(
        agora or _agora()
    )


    if not isinstance(
        jogador,
        dict,
    ):
        jogador = {}


    premium = (
        jogador.get(
            "eldora_premium"
        )
        or {}
    )


    if not isinstance(
        premium,
        dict,
    ):
        premium = {}


    expires_at = (
        _normalizar_datetime_utc(
            premium.get(
                "expires_at"
            )
        )
    )


    ativo = (
        isinstance(
            expires_at,
            datetime,
        )
        and expires_at > agora
    )


    creditos_classe = 0


    if ativo:

        try:
            creditos_classe = max(
                0,
                int(
                    premium.get(
                        "class_change_credits",
                        0,
                    )
                    or 0
                ),
            )

        except (
            TypeError,
            ValueError,
        ):
            creditos_classe = 0


    return {
        "ativo":
            ativo,

        "expires_at":
            expires_at,

        "class_change_credits":
            creditos_classe,
    }

def _preparar_credito_eldora_premium(
    jogador,
    pedido,
    codigo_pedido,
    agora=None,
):

    if not isinstance(
        jogador,
        dict,
    ):
        return None


    if not isinstance(
        pedido,
        dict,
    ):
        return None


    agora = _normalizar_datetime_utc(
        agora or _agora()
    )


    dias = max(
        0,
        int(
            pedido.get(
                "dias",
                0,
            )
            or 0
        ),
    )


    chaves = max(
        0,
        int(
            pedido.get(
                "chaves_masmorra",
                0,
            )
            or 0
        ),
    )


    trocas_classe = max(
        0,
        int(
            pedido.get(
                "trocas_classe",
                0,
            )
            or 0
        ),
    )


    if dias <= 0:
        return None


    inventario_atual = (
        jogador.get(
            "inventory",
            {},
        )
        or {}
    )


    if not isinstance(
        inventario_atual,
        dict,
    ):
        inventario_atual = {}


    novo_inventario = dict(
        inventario_atual
    )


    chave_uid = (
        "chave_masmorra"
    )


    item_chave = (
        novo_inventario.get(
            chave_uid
        )
    )


    if item_chave is None:

        for uid, item in (
            novo_inventario.items()
        ):

            if (
                isinstance(
                    item,
                    dict,
                )
                and item.get(
                    "base_id"
                )
                == "chave_masmorra"
            ):
                chave_uid = uid
                item_chave = item
                break


    novo_inventario[
        chave_uid
    ] = _montar_chave_masmorra(
        item_chave,
        chaves,
    )


    novo_premium = (
        _montar_estado_eldora_premium(
            jogador.get(
                "eldora_premium"
            ),
            dias,
            trocas_classe,
            codigo_pedido,
            agora,
        )
    )


    return {
        "inventory":
            novo_inventario,

        "eldora_premium":
            novo_premium,
    }

def _object_id(valor):
    if isinstance(
        valor,
        ObjectId,
    ):
        return valor


    texto = str(
        valor or ""
    ).strip()


    if not ObjectId.is_valid(
        texto
    ):
        return None


    return ObjectId(
        texto
    )


def _proxima_sequencia():
    if counters_col is None:
        raise RuntimeError(
            "Banco de dados indisponível."
        )


    documento = (
        counters_col.find_one_and_update(
            {
                "_id":
                    "premium_store_order_id"
            },

            {
                "$inc": {
                    "seq": 1
                }
            },

            upsert=True,

            return_document=
                ReturnDocument.AFTER,
        )
    )


    return int(
        documento.get(
            "seq",
            0,
        )
    )


def _codigo_pedido():
    numero = _proxima_sequencia()

    return (
        f"ELD-{numero:08d}"
    )


def _serializar_data(valor):
    if isinstance(
        valor,
        datetime,
    ):
        return valor.isoformat()


    return valor


def _serializar_pedido(
    pedido,
):
    if not pedido:
        return None


    return {
        "id":
            str(
                pedido.get(
                    "_id",
                    "",
                )
            ),

        "codigo":
            pedido.get(
                "codigo",
                "",
            ),

        "user_id":
            str(
                pedido.get(
                    "user_id",
                    "",
                )
            ),

        "personagem_nome":
            pedido.get(
                "personagem_nome",
                "Aventureiro",
            ),

        "pacote_id":
            pedido.get(
                "pacote_id",
                "",
            ),

        "pacote_nome":
            pedido.get(
                "pacote_nome",
                "",
            ),

        "tipo_produto":
            pedido.get(
                "tipo_produto",
                "gemas",
            ),

        "gemas":
            int(
                pedido.get(
                    "gemas",
                    0,
                )
                or 0
            ),
        "dias":
            int(
                pedido.get(
                    "dias",
                    0,
                )
                or 0
            ),

        "chaves_masmorra":
            int(
                pedido.get(
                    "chaves_masmorra",
                    0,
                )
                or 0
            ),

        "trocas_classe":
            int(
                pedido.get(
                    "trocas_classe",
                    0,
                )
                or 0
            ),

        "valor_centavos":
            int(
                pedido.get(
                    "valor_centavos",
                    0,
                )
                or 0
            ),

        "valor_formatado":
            formatar_valor_reais(
                pedido.get(
                    "valor_centavos",
                    0,
                )
            ),

        "metodo":
            pedido.get(
                "metodo",
                "pix",
            ),

        "status":
            pedido.get(
                "status",
                STATUS_AGUARDANDO_PAGAMENTO,
            ),

        "criado_em":
            _serializar_data(
                pedido.get(
                    "criado_em"
                )
            ),

        "atualizado_em":
            _serializar_data(
                pedido.get(
                    "atualizado_em"
                )
            ),

        "expira_em":
            _serializar_data(
                pedido.get(
                    "expira_em"
                )
            ),

        "aprovado_em":
            _serializar_data(
                pedido.get(
                    "aprovado_em"
                )
            ),

        "aprovado_por":
            pedido.get(
                "aprovado_por",
                "",
            ),

        "recusado_em":
            _serializar_data(
                pedido.get(
                    "recusado_em"
                )
            ),

        "recusado_por":
            pedido.get(
                "recusado_por",
                "",
            ),

        "motivo_recusa":
            pedido.get(
                "motivo_recusa",
                "",
            ),

        "credito_confirmado":
            bool(
                pedido.get(
                    "credito_confirmado",
                    False,
                )
            ),
    }
def _expirar_pedidos_antigos(
    user_id=None,
):
    if premium_orders_col is None:
        return


    filtro = {
        "status":
            STATUS_AGUARDANDO_PAGAMENTO,

        "expira_em": {
            "$lte":
                _agora()
        },
    }


    if user_id is not None:
        filtro["user_id"] = user_id


    premium_orders_col.update_many(
        filtro,

        {
            "$set": {
                "status":
                    STATUS_EXPIRADO,

                "atualizado_em":
                    _agora(),
            }
        },
    )


# ============================================================
# 🛍️ CATÁLOGO
# ============================================================

def obter_catalogo(
    user_id,
):
    jogador_id = _object_id(
        user_id
    )


    if not jogador_id:
        return {
            "success": False,
            "error":
                "Jogador inválido.",
        }


    if users_col is None:
        return {
            "success": False,
            "error":
                "Banco de dados indisponível.",
        }


    jogador = users_col.find_one(
        {
            "_id":
                jogador_id,
        },

        {
            "character_name": 1,
            "gems": 1,
            "eldora_premium": 1,
        },
    )


    if not jogador:
        return {
            "success": False,
            "error":
                "Jogador não encontrado.",
        }

    status_premium = (
        _obter_status_eldora_premium(
            jogador
        )
    )

    pacotes = []


    for pacote in (
        listar_pacotes_gemas()
    ):
        pacotes.append({
            **pacote,

            "valor_formatado":
                formatar_valor_reais(
                    pacote.get(
                        "valor_centavos",
                        0,
                    )
                ),
        })

    premium = (
        obter_eldora_premium()
    )


    if premium:

        premium = {
            **premium,

            "valor_formatado":
                formatar_valor_reais(
                    premium.get(
                        "valor_centavos",
                        0,
                    )
                ),
        }


    return {
        "success": True,

        "jogador": {
            "id":
                str(
                    jogador_id
                ),

            "nome":
                jogador.get(
                    "character_name",
                    "Aventureiro",
                ),

            "gems":
                int(
                    jogador.get(
                        "gems",
                        0,
                    )
                    or 0
                ),
        },
        "eldora_premium": {

            "ativo":
                bool(
                    status_premium.get(
                        "ativo",
                        False,
                    )
                ),

            "expira_em":
                _serializar_data(
                    status_premium.get(
                        "expires_at"
                    )
                ),

            "trocas_classe_disponiveis":
                int(
                    status_premium.get(
                        "class_change_credits",
                        0,
                    )
                    or 0
                ),
        },
        "pacotes":
            pacotes,

        "premium":
            premium,
    }


# ============================================================
# 🧾 CRIAR PEDIDO
# ============================================================

def criar_pedido(
    user_id,
    pacote_id,
):
    jogador_id = _object_id(
        user_id
    )


    if not jogador_id:
        return {
            "success": False,
            "error":
                "Jogador inválido.",
        }


    pacote = obter_produto_loja(
        pacote_id
    )


    if not pacote:
        return {
            "success": False,
            "error": (
                "Produto inválido "
                "ou indisponível."
            ),
        }


    if (
        premium_orders_col is None
        or users_col is None
    ):
        return {
            "success": False,
            "error":
                "Banco de dados indisponível.",
        }


    jogador = users_col.find_one(
        {
            "_id":
                jogador_id,
        },

        {
            "character_name": 1,
        },
    )


    if not jogador:
        return {
            "success": False,
            "error":
                "Jogador não encontrado.",
        }


    _expirar_pedidos_antigos(
        jogador_id
    )


    agora = _agora()


    pedido = {
        "codigo":
            _codigo_pedido(),

        "user_id":
            jogador_id,

        "personagem_nome":
            jogador.get(
                "character_name",
                "Aventureiro",
            ),


        # Snapshot do pacote.
        #
        # Mesmo que você altere os preços
        # depois, um pedido já criado mantém
        # exatamente o valor daquela compra.

        "pacote_id":
            pacote["id"],

        "pacote_nome":
            pacote["nome"],
        "tipo_produto":
            pacote.get(
                "tipo_produto",
                "gemas",
            ),

        "gemas":
            int(
                pacote.get(
                    "gemas",
                    0,
                )
                or 0
            ),

        "dias":
            int(
                pacote.get(
                    "dias",
                    0,
                )
                or 0
            ),

        "chaves_masmorra":
            int(
                pacote.get(
                    "chaves_masmorra",
                    0,
                )
                or 0
            ),

        "trocas_classe":
            int(
                pacote.get(
                    "trocas_classe",
                    0,
                )
                or 0
            ),

        "valor_centavos":
            int(
                pacote[
                    "valor_centavos"
                ]
            ),

        "metodo":
            "pix",

        "status":
            STATUS_AGUARDANDO_PAGAMENTO,

        "criado_em":
            agora,

        "atualizado_em":
            agora,

        "expira_em":
            agora
            + timedelta(
                hours=
                    PEDIDO_EXPIRA_HORAS
            ),

        "comprovante":
            None,

        "aprovado_em":
            None,

        "aprovado_por":
            None,
    }


    try:
        resultado = (
            premium_orders_col
            .insert_one(
                pedido
            )
        )


    except Exception as erro:
        print(
            "⚠️ [LOJA PREMIUM] "
            "Erro ao criar pedido: "
            f"{erro}"
        )


        return {
            "success": False,
            "error": (
                "Não foi possível criar "
                "o pedido agora."
            ),
        }


    pedido["_id"] = (
        resultado.inserted_id
    )


    # ========================================================
    # 📲 AVISA O GM SOBRE O NOVO PEDIDO
    # ========================================================

    try:
        from modules.premium_telegram import (
            notificar_novo_pedido,
        )


        notificar_novo_pedido(
            codigo=
                pedido.get(
                    "codigo"
                ),

            personagem=
                pedido.get(
                    "personagem_nome",
                    "Aventureiro",
                ),

            gemas=
                pedido.get(
                    "gemas",
                    0,
                ),

            valor_formatado=
                formatar_valor_reais(
                    pedido.get(
                        "valor_centavos",
                        0,
                    )
                ),

            tipo_produto=
                pedido.get(
                    "tipo_produto",
                    "gemas",
                ),

            pacote_nome=
                pedido.get(
                    "pacote_nome",
                    "",
                ),

            dias=
                pedido.get(
                    "dias",
                    0,
                ),

            chaves_masmorra=
                pedido.get(
                    "chaves_masmorra",
                    0,
                ),

            trocas_classe=
                pedido.get(
                    "trocas_classe",
                    0,
                ),
        )


    except Exception as erro:

        print(
            "⚠️ [LOJA PREMIUM] "
            "Pedido criado, mas a "
            "notificação Telegram falhou: "
            f"{erro}"
        )


    return {
        "success": True,

        "message":
            "Pedido criado com sucesso.",

        "pedido":
            _serializar_pedido(
                pedido
            ),
    }


# ============================================================
# 📜 PEDIDOS DO JOGADOR
# ============================================================

def listar_pedidos_usuario(
    user_id,
    limite=20,
):
    jogador_id = _object_id(
        user_id
    )


    if not jogador_id:
        return {
            "success": False,
            "error":
                "Jogador inválido.",
        }


    if premium_orders_col is None:
        return {
            "success": False,
            "error":
                "Banco de dados indisponível.",
        }


    _expirar_pedidos_antigos(
        jogador_id
    )


    try:
        limite = int(
            limite
        )

    except (
        TypeError,
        ValueError,
    ):
        limite = 20


    limite = max(
        1,
        min(
            limite,
            50,
        ),
    )


    pedidos = list(
        premium_orders_col
        .find(
            {
                "user_id":
                    jogador_id,
            }
        )
        .sort(
            "criado_em",
            DESCENDING,
        )
        .limit(
            limite
        )
    )


    return {
        "success": True,

        "pedidos": [
            _serializar_pedido(
                pedido
            )
            for pedido in pedidos
        ],
    }

# ============================================================
# 💠 GERAR CHECKOUT PIX DO PEDIDO
# ============================================================

def gerar_checkout_pix(
    user_id,
    codigo_pedido,
):
    jogador_id = _object_id(
        user_id
    )


    if not jogador_id:
        return {
            "success": False,
            "error":
                "Jogador inválido.",
        }


    codigo_pedido = str(
        codigo_pedido or ""
    ).strip()


    if not codigo_pedido:
        return {
            "success": False,
            "error":
                "Pedido não informado.",
        }


    if premium_orders_col is None:
        return {
            "success": False,
            "error":
                "Banco de dados indisponível.",
        }


    # Atualiza pedidos vencidos antes
    # de permitir gerar o pagamento.
    _expirar_pedidos_antigos(
        jogador_id
    )


    pedido = premium_orders_col.find_one({
        "codigo":
            codigo_pedido,

        "user_id":
            jogador_id,
    })


    if not pedido:
        return {
            "success": False,
            "error":
                "Pedido não encontrado.",
        }


    status = pedido.get(
        "status"
    )


    if status == STATUS_EXPIRADO:
        return {
            "success": False,
            "error":
                "Este pedido expirou.",
        }


    if status == STATUS_CANCELADO:
        return {
            "success": False,
            "error":
                "Este pedido foi cancelado.",
        }


    if status == STATUS_RECUSADO:
        return {
            "success": False,
            "error":
                "Este pedido foi recusado.",
        }


    if status == STATUS_APROVADO:
        return {
            "success": False,
            "error":
                "Este pedido já foi aprovado.",
        }


    if status not in {
        STATUS_AGUARDANDO_PAGAMENTO,
        STATUS_EM_ANALISE,
    }:
        return {
            "success": False,
            "error":
                "Este pedido não aceita pagamento.",
        }


    try:
        from modules.premium_pix import (
            gerar_pix_copia_cola,
        )


        pix = gerar_pix_copia_cola(
            valor_centavos=
                pedido.get(
                    "valor_centavos",
                    0,
                ),

            codigo_pedido=
                pedido.get(
                    "codigo"
                ),
        )


    except Exception as erro:
        return {
            "success": False,
            "error": (
                "Não foi possível preparar "
                f"o Pix: {str(erro)}"
            ),
        }


    if not pix.get(
        "success"
    ):
        return pix


    return {
        "success": True,

        "pedido": {
            "codigo":
                pedido.get(
                    "codigo"
                ),

            "pacote_id":
                pedido.get(
                    "pacote_id"
                ),

            "pacote_nome":
                pedido.get(
                    "pacote_nome"
                ),

            "tipo_produto":
                pedido.get(
                    "tipo_produto",
                    "gemas",
                ),
                
            "gemas":
                int(
                    pedido.get(
                        "gemas",
                        0,
                    )
                    or 0
                ),

            "dias":
                int(
                    pedido.get(
                        "dias",
                        0,
                    )
                    or 0
                ),

            "chaves_masmorra":
                int(
                    pedido.get(
                        "chaves_masmorra",
                        0,
                    )
                    or 0
                ),

            "trocas_classe":
                int(
                    pedido.get(
                        "trocas_classe",
                        0,
                    )
                    or 0
                ),

            "valor_centavos":
                int(
                    pedido.get(
                        "valor_centavos",
                        0,
                    )
                    or 0
                ),

            "valor_formatado":
                formatar_valor_reais(
                    pedido.get(
                        "valor_centavos",
                        0,
                    )
                ),

            "status":
                status,

            "expira_em":
                _serializar_data(
                    pedido.get(
                        "expira_em"
                    )
                ),
        },

        "pix": {
            "codigo":
                pix.get(
                    "codigo_pix"
                ),

            "txid":
                pix.get(
                    "txid"
                ),

            "valor":
                pix.get(
                    "valor"
                ),
        },
    }

# ============================================================
# 📎 ENVIAR COMPROVANTE PIX
# ============================================================

def enviar_comprovante_pix(
    user_id,
    codigo_pedido,
    arquivo_bytes,
    nome_arquivo,
    mime_type,
):
    jogador_id = _object_id(
        user_id
    )


    if not jogador_id:
        return {
            "success": False,
            "error": "Jogador inválido.",
        }


    codigo_pedido = str(
        codigo_pedido or ""
    ).strip()


    if not codigo_pedido:
        return {
            "success": False,
            "error": "Pedido não informado.",
        }


    if (
        premium_orders_col is None
        or premium_receipts_fs is None
    ):
        return {
            "success": False,
            "error": "Banco de dados indisponível.",
        }


    if not arquivo_bytes:
        return {
            "success": False,
            "error": "Comprovante vazio.",
        }


    _expirar_pedidos_antigos(
        jogador_id
    )


    pedido = premium_orders_col.find_one({
        "codigo": codigo_pedido,
        "user_id": jogador_id,
    })


    if not pedido:
        return {
            "success": False,
            "error": "Pedido não encontrado.",
        }


    status = pedido.get(
        "status"
    )


    if status == STATUS_EM_ANALISE:
        return {
            "success": False,
            "error": (
                "Este comprovante já foi enviado "
                "e está em análise."
            ),
        }


    if status == STATUS_APROVADO:
        return {
            "success": False,
            "error": "Este pedido já foi aprovado.",
        }


    if status == STATUS_EXPIRADO:
        return {
            "success": False,
            "error": "Este pedido expirou.",
        }


    if status != STATUS_AGUARDANDO_PAGAMENTO:
        return {
            "success": False,
            "error": (
                "Este pedido não aceita "
                "envio de comprovante."
            ),
        }


    agora = _agora()


    expira_em = _normalizar_datetime_utc(
        pedido.get(
            "expira_em"
        )
    )


    if (
        isinstance(
            expira_em,
            datetime,
        )
        and expira_em <= agora
    ):
        
        premium_orders_col.update_one(
            {
                "_id": pedido["_id"],
            },
            {
                "$set": {
                    "status":
                        STATUS_EXPIRADO,

                    "atualizado_em":
                        agora,
                }
            },
        )


        return {
            "success": False,
            "error": "Este pedido expirou.",
        }


    arquivo_id = None


    try:
        arquivo_id = premium_receipts_fs.put(
            arquivo_bytes,

            filename=
                str(
                    nome_arquivo
                    or "comprovante"
                ),

            contentType=
                str(
                    mime_type
                    or "application/octet-stream"
                ),

            metadata={
                "codigo_pedido":
                    codigo_pedido,

                "user_id":
                    str(
                        jogador_id
                    ),

                "tipo":
                    "comprovante_pix",
            },
        )


        resultado = premium_orders_col.update_one(
            {
                "_id":
                    pedido["_id"],

                "user_id":
                    jogador_id,

                "status":
                    STATUS_AGUARDANDO_PAGAMENTO,

                "expira_em": {
                    "$gt":
                        agora,
                },
            },

            {
                "$set": {
                    "status":
                        STATUS_EM_ANALISE,

                    "comprovante": {
                        "arquivo_id":
                            arquivo_id,

                        "nome":
                            str(
                                nome_arquivo
                                or "comprovante"
                            ),

                        "mime_type":
                            str(
                                mime_type
                                or ""
                            ),

                        "tamanho":
                            len(
                                arquivo_bytes
                            ),

                        "enviado_em":
                            agora,
                    },

                    "atualizado_em":
                        agora,
                }
            },
        )


        if resultado.modified_count != 1:

            try:
                premium_receipts_fs.delete(
                    arquivo_id
                )
            except Exception:
                pass


            return {
                "success": False,
                "error": (
                    "O pedido mudou de estado "
                    "durante o envio. Tente novamente."
                ),
            }

        # ====================================================
        # 🚨 AVISA O GM QUE EXISTE COMPRA PARA ANALISAR
        # ====================================================

        try:
            from modules.premium_telegram import (
                notificar_comprovante_recebido,
            )


            notificar_comprovante_recebido(
                codigo=
                    codigo_pedido,

                personagem=
                    pedido.get(
                        "personagem_nome",
                        "Aventureiro",
                    ),

                gemas=
                    pedido.get(
                        "gemas",
                        0,
                    ),

                valor_formatado=
                    formatar_valor_reais(
                        pedido.get(
                            "valor_centavos",
                            0,
                        )
                    ),

                tipo_produto=
                    pedido.get(
                        "tipo_produto",
                        "gemas",
                    ),

                pacote_nome=
                    pedido.get(
                        "pacote_nome",
                        "",
                    ),

                dias=
                    pedido.get(
                        "dias",
                        0,
                    ),

                chaves_masmorra=
                    pedido.get(
                        "chaves_masmorra",
                        0,
                    ),

                trocas_classe=
                    pedido.get(
                        "trocas_classe",
                        0,
                    ),
            )


        except Exception as erro:

            print(
                "⚠️ [LOJA PREMIUM] "
                "Comprovante salvo, mas a "
                "notificação Telegram falhou: "
                f"{erro}"
            )


        return {
            "success": True,

            "message": (
                "Comprovante enviado "
                "para análise."
            ),

            "pedido": {
                "codigo":
                    codigo_pedido,

                "status":
                    STATUS_EM_ANALISE,

                "pacote_id":
                    pedido.get(
                        "pacote_id",
                        "",
                    ),

                "pacote_nome":
                    pedido.get(
                        "pacote_nome",
                        "",
                    ),

                "tipo_produto":
                    pedido.get(
                        "tipo_produto",
                        "gemas",
                    ),

                "gemas":
                    int(
                        pedido.get(
                            "gemas",
                            0,
                        )
                        or 0
                    ),

                "dias":
                    int(
                        pedido.get(
                            "dias",
                            0,
                        )
                        or 0
                    ),

                "chaves_masmorra":
                    int(
                        pedido.get(
                            "chaves_masmorra",
                            0,
                        )
                        or 0
                    ),

                "trocas_classe":
                    int(
                        pedido.get(
                            "trocas_classe",
                            0,
                        )
                        or 0
                    ),

                "valor_formatado":
                    formatar_valor_reais(
                        pedido.get(
                            "valor_centavos",
                            0,
                        )
                    ),
            },
        }


    except Exception as erro:

        if arquivo_id is not None:

            try:
                premium_receipts_fs.delete(
                    arquivo_id
                )
            except Exception:
                pass


        print(
            "⚠️ [LOJA PREMIUM] "
            "Erro ao guardar comprovante: "
            f"{erro}"
        )


        return {
            "success": False,
            "error": (
                "Não foi possível enviar "
                "o comprovante."
            ),
        }

# ============================================================
# 🛡️ ADMINISTRAÇÃO DA LOJA PREMIUM
# ============================================================


def _serializar_pedido_admin(
    pedido,
):
    if not pedido:
        return None


    comprovante = (
        pedido.get(
            "comprovante"
        )
        or {}
    )


    return {
        **(
            _serializar_pedido(
                pedido
            )
            or {}
        ),

        "tem_comprovante":
            bool(
                comprovante.get(
                    "arquivo_id"
                )
            ),

        "comprovante": {
            "nome":
                comprovante.get(
                    "nome",
                    "",
                ),

            "mime_type":
                comprovante.get(
                    "mime_type",
                    "",
                ),

            "tamanho":
                int(
                    comprovante.get(
                        "tamanho",
                        0,
                    )
                    or 0
                ),

            "enviado_em":
                _serializar_data(
                    comprovante.get(
                        "enviado_em"
                    )
                ),
        },

        "aprovado_em":
            _serializar_data(
                pedido.get(
                    "aprovado_em"
                )
            ),

        "aprovado_por":
            pedido.get(
                "aprovado_por"
            ),

        "recusado_em":
            _serializar_data(
                pedido.get(
                    "recusado_em"
                )
            ),

        "recusado_por":
            pedido.get(
                "recusado_por"
            ),

        "motivo_recusa":
            pedido.get(
                "motivo_recusa",
                "",
            ),
    }


# ============================================================
# 🏛️ SERVIÇOS PAGOS COM GEMAS
# ============================================================

def _profissoes_disponiveis_troca(jogador, catalogo):
    aprendidas = dict(jogador.get('learned_professions') or {})
    atual = jogador.get('profession') or {}
    chave_atual = str(atual.get('key') or atual.get('type') or '').strip().lower()
    if chave_atual:
        aprendidas[chave_atual] = atual
    maestrias = set(jogador.get('maestrias_resgatadas') or [])
    return {
        chave: dict(aprendidas.get(chave) or {'level': 1, 'xp': 0})
        for chave in catalogo
        if chave != chave_atual and chave not in maestrias
        and int((aprendidas.get(chave) or {}).get('level', 1) or 1) < 50
    }


def obter_servicos_jogador(user_id):
    jogador_id = _object_id(user_id)

    if not jogador_id or users_col is None:
        return {
            "success": False,
            "error": "Herói não encontrado.",
        }

    jogador = users_col.find_one({"_id": jogador_id})
    if not jogador:
        return {
            "success": False,
            "error": "Herói não encontrado.",
        }

    status_premium = (
        _obter_status_eldora_premium(
            jogador
        )
    )

    from modules.game_data.classes import CLASSES_DATA
    from modules.game_data.professions import PROFESSIONS_DATA

    classe_atual = str(
        jogador.get("class") or "aventureiro"
    ).strip().lower()

    classes = []
    if classe_atual in CLASSES_DATA:
        for chave, dados in CLASSES_DATA.items():
            if int(dados.get("tier", 0) or 0) != 1:
                continue
            classes.append({
                "id": chave,
                "nome": dados.get("display_name", chave.title()),
                "icone": dados.get("emoji", "⚔️"),
                "descricao": dados.get("description", ""),
                "atual": chave == classe_atual,
            })

    classes.sort(key=lambda item: item["nome"])

    aprendidas = dict(jogador.get("learned_professions") or {})
    profissao_atual = jogador.get("profession") or {}
    chave_atual = str(
        profissao_atual.get("key")
        or profissao_atual.get("type")
        or ""
    ).strip().lower()

    if chave_atual and chave_atual not in aprendidas:
        aprendidas[chave_atual] = profissao_atual

    profissoes = []
    for chave, progresso in _profissoes_disponiveis_troca(jogador, PROFESSIONS_DATA).items():
        chave = str(chave).strip().lower()
        dados = PROFESSIONS_DATA.get(chave)
        if not dados:
            continue
        progresso = progresso if isinstance(progresso, dict) else {}
        profissoes.append({
            "id": chave,
            "nome": dados.get("display_name", chave.title()),
            "categoria": dados.get("category", ""),
            "nivel": int(progresso.get("level", 1) or 1),
            "atual": chave == chave_atual,
        })

    profissoes.sort(key=lambda item: (-item["nivel"], item["nome"]))

    return {
        "success": True,
        "saldo_gemas": int(jogador.get("gems", 0) or 0),
        "eldora_premium": {

            "ativo":
                bool(
                    status_premium.get(
                        "ativo",
                        False,
                    )
                ),

            "expira_em":
                _serializar_data(
                    status_premium.get(
                        "expires_at"
                    )
                ),

            "trocas_classe_disponiveis":
                int(
                    status_premium.get(
                        "class_change_credits",
                        0,
                    )
                    or 0
                ),

            "troca_classe_gratis":
                (
                    bool(
                        status_premium.get(
                            "ativo",
                            False,
                        )
                    )
                    and
                    int(
                        status_premium.get(
                            "class_change_credits",
                            0,
                        )
                        or 0
                    ) > 0
                ),
        },
        "classe_atual": classe_atual,
        "profissao_atual": chave_atual,
        "classes": classes,
        "profissoes": profissoes,
        "custos": {
            "classe": CUSTO_TROCA_CLASSE,
            "profissao": CUSTO_TROCA_PROFISSAO,
        },
    }


def comprar_servico_gemas(
    user_id,
    tipo,
    destino,
    concordou=False,
):
    jogador_id = _object_id(user_id)
    tipo = str(tipo or "").strip().lower()
    destino = str(destino or "").strip().lower()

    if not concordou:
        return {
            "success": False,
            "error": "Marque Li e concordo antes de confirmar.",
        }

    if not jogador_id or users_col is None:
        return {"success": False, "error": "Herói não encontrado."}

    jogador = users_col.find_one({"_id": jogador_id})
    if not jogador:
        return {"success": False, "error": "Herói não encontrado."}

    acao_atual = str(
        (jogador.get("player_state") or {}).get("action") or "idle"
    ).strip().lower()
    if acao_atual not in {"", "idle"}:
        return {
            "success": False,
            "error": "Finalize sua atividade atual antes de usar este serviço.",
        }

    agora = _agora()

    reparo_ferramenta = tipo == 'reparar_ferramenta'
    if tipo == "profissao" or reparo_ferramenta:
        from modules.game_data.professions import PROFESSIONS_DATA
        from modules.profession_starter import prepare_profession_tool

        aprendidas = dict(jogador.get("learned_professions") or {})
        atual = jogador.get("profession") or {}
        atual_key = str(
            atual.get("key") or atual.get("type") or ""
        ).strip().lower()

        if atual_key:
            aprendidas[atual_key] = atual

        if reparo_ferramenta:
            destino = atual_key
            if destino in (jogador.get('premium_tool_recoveries') or []):
                return {'success': False, 'error': 'A ferramenta desta troca já foi recuperada. Confira sua mochila e o equipamento do ofício.'}
            if not destino or not any(
                row.get('tipo') == 'profissao' and row.get('destino') == destino
                for row in jogador.get('premium_service_history', [])
            ):
                return {'success': False, 'error': 'Não há troca da profissão atual pela loja para recuperar.'}

        if destino == atual_key and not reparo_ferramenta:
            return {"success": False, "error": "Este ofício já está ativo."}

        progresso = atual if reparo_ferramenta else _profissoes_disponiveis_troca(jogador, PROFESSIONS_DATA).get(destino)
        dados_profissao = PROFESSIONS_DATA.get(destino)
        if not isinstance(progresso, dict) or not dados_profissao:
            return {
                "success": False,
                "error": "Escolha uma profissão diferente da atual e ainda sem maestria.",
            }

        nova_profissao = dict(progresso)
        nova_profissao.update({
            "key": destino,
            "type": destino,
            "category": dados_profissao.get("category"),
            "display_name": dados_profissao.get("display_name"),
        })
        aprendidas[destino] = nova_profissao

        try:
            inventario, ferramentas = prepare_profession_tool(jogador, destino)
        except ValueError as erro:
            return {'success': False, 'error': str(erro)}
        if reparo_ferramenta and inventario == (jogador.get('inventory') or {}) and ferramentas == (jogador.get('equipment_tools') or {}):
            return {'success': True, 'message': 'A ferramenta do ofício já está equipada.', 'saldo_gemas': int(jogador.get('gems', 0))}

        custo = 0 if reparo_ferramenta else CUSTO_TROCA_PROFISSAO
        recuperacoes = list(jogador.get('premium_tool_recoveries') or [])
        if destino not in recuperacoes:
            recuperacoes.append(destino)
        atualizado = users_col.find_one_and_update(
            {
                "_id": jogador_id,
                "gems": {"$gte": custo},
                "profession": jogador.get('profession') if 'profession' in jogador else {"$exists": False},
                "learned_professions": jogador.get('learned_professions') if 'learned_professions' in jogador else {"$exists": False},
                "maestrias_resgatadas": jogador.get('maestrias_resgatadas') if 'maestrias_resgatadas' in jogador else {"$exists": False},
                "player_state": jogador.get('player_state') if 'player_state' in jogador else {"$exists": False},
                "inventory": jogador.get('inventory') if 'inventory' in jogador else {"$exists": False},
                "equipment_tools": jogador.get('equipment_tools') if 'equipment_tools' in jogador else {"$exists": False},
                "premium_tool_recoveries": jogador.get('premium_tool_recoveries') if 'premium_tool_recoveries' in jogador else {"$exists": False},
            },
            {
                "$inc": {"gems": -custo},
                "$set": {"profession": nova_profissao, "learned_professions": aprendidas,
                         "inventory": inventario, "equipment_tools": ferramentas,
                         "premium_tool_recoveries": recuperacoes},
                "$push": {
                    "premium_service_history": {
                        "tipo": tipo,
                        "destino": destino,
                        "custo_gemas": custo,
                        "criado_em": agora,
                    }
                },
            },
            return_document=ReturnDocument.AFTER,
        )

        nome_destino = dados_profissao.get("display_name", destino.title())

    elif tipo == "classe":
        from modules.game_data.classes import CLASSES_DATA

        dados_classe = CLASSES_DATA.get(destino)
        if not dados_classe or int(dados_classe.get("tier", 0) or 0) != 1:
            return {
                "success": False,
                "error": "Escolha uma classe base válida.",
            }

        classe_atual = str(
            jogador.get("class") or "aventureiro"
        ).strip().lower()
        if classe_atual not in CLASSES_DATA:
            return {
                "success": False,
                "error": "Desperte sua primeira classe antes de usar este serviço.",
            }

        if destino == classe_atual:
            return {"success": False, "error": "Esta já é sua classe atual."}

        arquivos = dict(jogador.get("class_skill_loadouts") or {})
        arquivos[classe_atual] = {
            "skills": dict(jogador.get("skills") or {}),
            "equipped_skills": dict(jogador.get("equipped_skills") or {}),
        }

        salvo_destino = arquivos.get(destino) or {}
        skills_destino = dict(salvo_destino.get("skills") or {})
        equipadas_destino = dict(
            salvo_destino.get("equipped_skills") or {}
        )

        if not skills_destino:
            skill_inicial = SKILLS_INICIAIS_CLASSE.get(destino)
            if skill_inicial:
                skills_destino[skill_inicial] = {
                    "unlocked": True,
                    "rarity": "comum",
                    "level": 1,
                }

        status_premium = (
            _obter_status_eldora_premium(
                jogador,
                agora,
            )
        )


        usar_credito_premium = (
            bool(
                status_premium.get(
                    "ativo",
                    False,
                )
            )
            and
            int(
                status_premium.get(
                    "class_change_credits",
                    0,
                )
                or 0
            ) > 0
        )


        if usar_credito_premium:

            custo = 0


            atualizado = (
                users_col.find_one_and_update(
                    {
                        "_id":
                            jogador_id,

                        "class": {
                            "$ne":
                                destino
                        },

                        "eldora_premium.expires_at": {
                            "$gt":
                                agora
                        },

                        "eldora_premium.class_change_credits": {
                            "$gte":
                                1
                        },
                    },

                    {
                        "$inc": {
                            "eldora_premium.class_change_credits":
                                -1
                        },

                        "$set": {
                            "class":
                                destino,

                            "equipment":
                                {},

                            "equipped_skin":
                                "padrao",

                            "evolution_progress":
                                {},

                            "skills":
                                skills_destino,

                            "equipped_skills":
                                equipadas_destino,

                            "class_skill_loadouts":
                                arquivos,

                            "eldora_premium.updated_at":
                                agora,
                        },

                        "$push": {
                            "premium_service_history": {
                                "tipo":
                                    tipo,

                                "destino":
                                    destino,

                                "custo_gemas":
                                    0,

                                "origem":
                                    "eldora_premium",

                                "criado_em":
                                    agora,
                            }
                        },
                    },

                    return_document=
                        ReturnDocument.AFTER,
                )
            )


            if not atualizado:

                return {
                    "success": False,

                    "error": (
                        "Seu crédito Premium mudou "
                        "durante a troca. "
                        "Atualize a loja e tente novamente."
                    ),
                }


        else:

            custo = CUSTO_TROCA_CLASSE


            atualizado = (
                users_col.find_one_and_update(
                    {
                        "_id":
                            jogador_id,

                        "gems": {
                            "$gte":
                                custo
                        },

                        "class": {
                            "$ne":
                                destino
                        },
                    },

                    {
                        "$inc": {
                            "gems":
                                -custo
                        },

                        "$set": {
                            "class":
                                destino,

                            "equipment":
                                {},

                            "equipped_skin":
                                "padrao",

                            "evolution_progress":
                                {},

                            "skills":
                                skills_destino,

                            "equipped_skills":
                                equipadas_destino,

                            "class_skill_loadouts":
                                arquivos,
                        },

                        "$push": {
                            "premium_service_history": {
                                "tipo":
                                    tipo,

                                "destino":
                                    destino,

                                "custo_gemas":
                                    custo,

                                "origem":
                                    "gemas",

                                "criado_em":
                                    agora,
                            }
                        },
                    },

                    return_document=
                        ReturnDocument.AFTER,
                )
            )

        nome_destino = dados_classe.get("display_name", destino.title())

    else:
        return {"success": False, "error": "Serviço inválido."}

    if not atualizado:
        atual = users_col.find_one({"_id": jogador_id}, {"gems": 1}) or {}
        if int(atual.get("gems", 0) or 0) < custo:
            erro = f"Saldo insuficiente. Este serviço custa {custo} Gemas."
        else:
            erro = "Não foi possível concluir a troca. Atualize e tente novamente."
        return {"success": False, "error": erro}

    return {
        "success": True,
        "message": f"Troca concluída: {nome_destino}.",
        "tipo": tipo,
        "destino": destino,
        "saldo_gemas": int(atualizado.get("gems", 0) or 0),
    }


# ============================================================
# 📋 LISTAR PEDIDOS PARA ADMIN
# ============================================================

def listar_pedidos_admin(
    status=None,
    limite=100,
):
    if premium_orders_col is None:
        return {
            "success": False,
            "error":
                "Banco de dados indisponível.",
        }


    try:
        limite = int(
            limite
        )

    except (
        TypeError,
        ValueError,
    ):
        limite = 100


    limite = max(
        1,
        min(
            limite,
            200,
        ),
    )


    status_texto = str(
        status or ""
    ).strip().lower()


    status_validos = {
        STATUS_AGUARDANDO_PAGAMENTO,
        STATUS_EM_ANALISE,
        STATUS_PROCESSANDO_APROVACAO,
        STATUS_APROVADO,
        STATUS_RECUSADO,
        STATUS_CANCELADO,
        STATUS_EXPIRADO,
    }


    if status_texto:

        if (
            status_texto
            not in status_validos
        ):
            return {
                "success": False,
                "error":
                    "Status de pedido inválido.",
            }


        filtro = {
            "status":
                status_texto
        }


    else:

        # Sem filtro explícito:
        # mostra o que exige atenção.
        filtro = {
            "status": {
                "$in": [
                    STATUS_AGUARDANDO_PAGAMENTO,
                    STATUS_EM_ANALISE,
                    STATUS_PROCESSANDO_APROVACAO,
                ]
            }
        }


    pedidos = list(
        premium_orders_col
        .find(
            filtro
        )
        .sort(
            "atualizado_em",
            DESCENDING,
        )
        .limit(
            limite
        )
    )


    return {
        "success": True,

        "total":
            len(
                pedidos
            ),

        "pedidos": [
            _serializar_pedido_admin(
                pedido
            )
            for pedido in pedidos
        ],
    }


# ============================================================
# 🖼️ OBTER COMPROVANTE
# ============================================================

def obter_comprovante_admin(
    codigo_pedido,
):
    codigo_pedido = str(
        codigo_pedido or ""
    ).strip()


    if not codigo_pedido:
        return {
            "success": False,
            "error":
                "Pedido não informado.",
        }


    if (
        premium_orders_col is None
        or premium_receipts_fs is None
    ):
        return {
            "success": False,
            "error":
                "Banco de dados indisponível.",
        }


    pedido = (
        premium_orders_col
        .find_one({
            "codigo":
                codigo_pedido,
        })
    )


    if not pedido:
        return {
            "success": False,
            "error":
                "Pedido não encontrado.",
        }


    comprovante = (
        pedido.get(
            "comprovante"
        )
        or {}
    )


    arquivo_id = (
        comprovante.get(
            "arquivo_id"
        )
    )


    if not arquivo_id:
        return {
            "success": False,
            "error":
                "Este pedido não possui comprovante.",
        }


    try:

        if not isinstance(
            arquivo_id,
            ObjectId,
        ):
            arquivo_id = ObjectId(
                str(
                    arquivo_id
                )
            )


        arquivo = (
            premium_receipts_fs
            .get(
                arquivo_id
            )
        )


        dados = arquivo.read()


        return {
            "success": True,

            "dados":
                dados,

            "nome":
                (
                    comprovante.get(
                        "nome"
                    )
                    or getattr(
                        arquivo,
                        "filename",
                        None,
                    )
                    or "comprovante"
                ),

            "mime_type":
                (
                    comprovante.get(
                        "mime_type"
                    )
                    or getattr(
                        arquivo,
                        "content_type",
                        None,
                    )
                    or "application/octet-stream"
                ),

            "tamanho":
                len(
                    dados
                ),
        }


    except Exception as erro:

        print(
            "⚠️ [LOJA PREMIUM] "
            "Erro ao ler comprovante "
            f"{codigo_pedido}: {erro}"
        )


        return {
            "success": False,
            "error":
                "Não foi possível abrir o comprovante.",
        }


# ============================================================
# ✅ APROVAR PEDIDO
# ============================================================

def aprovar_pedido_manual(
    codigo_pedido,
    aprovado_por="admin",
):
    codigo_pedido = str(
        codigo_pedido or ""
    ).strip()


    aprovado_por = str(
        aprovado_por or "admin"
    ).strip() or "admin"


    if not codigo_pedido:
        return {
            "success": False,
            "error":
                "Pedido não informado.",
        }


    if (
        premium_orders_col is None
        or users_col is None
    ):
        return {
            "success": False,
            "error":
                "Banco de dados indisponível.",
        }


    pedido = (
        premium_orders_col
        .find_one({
            "codigo":
                codigo_pedido,
        })
    )


    if not pedido:
        return {
            "success": False,
            "error":
                "Pedido não encontrado.",
        }


    status = pedido.get(
        "status"
    )


    # Já aprovado:
    # responde sucesso sem entregar novamente.
    if status == STATUS_APROVADO:

        jogador = (
            users_col.find_one(
                {
                    "_id":
                        pedido.get(
                            "user_id"
                        )
                },
                {
                    "gems": 1,
                    "inventory": 1,
                    "eldora_premium": 1,
                },
            )
            or {}
        )


        resposta = {
            "success": True,

            "ja_processado":
                True,

            "message":
                "Este pedido já havia sido aprovado.",

            "pedido":
                _serializar_pedido_admin(
                    pedido
                ),

            "novo_saldo_gemas":
                int(
                    jogador.get(
                        "gems",
                        0,
                    )
                    or 0
                ),
        }


        if (
            pedido.get(
                "tipo_produto",
                "gemas",
            )
            == "eldora_premium"
        ):

            premium_atual = (
                jogador.get(
                    "eldora_premium"
                )
                or {}
            )


            inventario_atual = (
                jogador.get(
                    "inventory"
                )
                or {}
            )


            item_chave = (
                inventario_atual.get(
                    "chave_masmorra"
                )
            )


            if item_chave is None:

                for _uid, _item in (
                    inventario_atual.items()
                ):

                    if (
                        isinstance(
                            _item,
                            dict,
                        )
                        and _item.get(
                            "base_id"
                        )
                        == "chave_masmorra"
                    ):
                        item_chave = _item
                        break


            resposta[
                "premium_expira_em"
            ] = _serializar_data(
                premium_atual.get(
                    "expires_at"
                )
            )


            resposta[
                "chaves_masmorra"
            ] = _quantidade_chaves_masmorra(
                item_chave
            )


            resposta[
                "trocas_classe_disponiveis"
            ] = int(
                premium_atual.get(
                    "class_change_credits",
                    0,
                )
                or 0
            )


        return resposta


    if status not in {
        STATUS_AGUARDANDO_PAGAMENTO,
        STATUS_EM_ANALISE,
        STATUS_PROCESSANDO_APROVACAO,
    }:

        return {
            "success": False,

            "error": (
                "Somente pedidos pendentes "
                "podem ser aprovados."
            ),
        }


    agora = _agora()


    # --------------------------------------------------------
    # 🔒 RESERVA ATÔMICA DO PEDIDO
    #
    # Antes de mexer nas Gems, reserva o pedido pendente.
    # Assim uma recusa não pode acontecer simultaneamente.
    # --------------------------------------------------------

    if status in {
        STATUS_AGUARDANDO_PAGAMENTO,
        STATUS_EM_ANALISE,
    }:

        reservado = (
            premium_orders_col
            .update_one(
                {
                    "_id":
                        pedido["_id"],

                    "status":
                        status,
                },

                {
                    "$set": {
                        "status":
                            STATUS_PROCESSANDO_APROVACAO,

                        "atualizado_em":
                            agora,
                    }
                },
            )
        )


        if reservado.modified_count != 1:

            pedido = (
                premium_orders_col
                .find_one({
                    "_id":
                        pedido["_id"]
                })
            )


            if not pedido:
                return {
                    "success": False,
                    "error":
                        "Pedido não encontrado.",
                }


            if (
                pedido.get(
                    "status"
                )
                == STATUS_APROVADO
            ):

                jogador = (
                    users_col.find_one(
                        {
                            "_id":
                                pedido.get(
                                    "user_id"
                                )
                        },
                        {
                            "gems": 1,
                            "inventory": 1,
                            "eldora_premium": 1,
                        },
                    )
                    or {}
                )


                resposta = {
                    "success": True,

                    "ja_processado":
                        True,

                    "message":
                        "Este pedido já havia sido aprovado.",

                    "pedido":
                        _serializar_pedido_admin(
                            pedido
                        ),

                    "novo_saldo_gemas":
                        int(
                            jogador.get(
                                "gems",
                                0,
                            )
                            or 0
                        ),
                }


                if (
                    pedido.get(
                        "tipo_produto",
                        "gemas",
                    )
                    == "eldora_premium"
                ):

                    premium_atual = (
                        jogador.get(
                            "eldora_premium"
                        )
                        or {}
                    )


                    inventario_atual = (
                        jogador.get(
                            "inventory"
                        )
                        or {}
                    )


                    item_chave = (
                        inventario_atual.get(
                            "chave_masmorra"
                        )
                    )


                    if item_chave is None:

                        for _uid, _item in (
                            inventario_atual.items()
                        ):

                            if (
                                isinstance(
                                    _item,
                                    dict,
                                )
                                and _item.get(
                                    "base_id"
                                )
                                == "chave_masmorra"
                            ):
                                item_chave = _item
                                break


                    resposta[
                        "premium_expira_em"
                    ] = _serializar_data(
                        premium_atual.get(
                            "expires_at"
                        )
                    )


                    resposta[
                        "chaves_masmorra"
                    ] = _quantidade_chaves_masmorra(
                        item_chave
                    )


                    resposta[
                        "trocas_classe_disponiveis"
                    ] = int(
                        premium_atual.get(
                            "class_change_credits",
                            0,
                        )
                        or 0
                    )


                return resposta


            if (
                pedido.get(
                    "status"
                )
                != STATUS_PROCESSANDO_APROVACAO
            ):

                return {
                    "success": False,

                    "error": (
                        "O pedido mudou de estado "
                        "durante a aprovação."
                    ),
                }


    jogador_id = pedido.get(
        "user_id"
    )


    tipo_produto = str(
        pedido.get(
            "tipo_produto",
            "gemas",
        )
        or "gemas"
    ).strip()


    gemas = int(
        pedido.get(
            "gemas",
            0,
        )
        or 0
    )


    if not jogador_id:
        return {
            "success": False,

            "error": (
                "Jogador do pedido "
                "não foi informado."
            ),
        }


    if tipo_produto == "gemas":

        if gemas <= 0:
            return {
                "success": False,

                "error": (
                    "Dados de crédito do pedido "
                    "são inválidos."
                ),
            }


    elif tipo_produto == "eldora_premium":

        dias = int(
            pedido.get(
                "dias",
                0,
            )
            or 0
        )


        chaves_masmorra = int(
            pedido.get(
                "chaves_masmorra",
                0,
            )
            or 0
        )


        trocas_classe = int(
            pedido.get(
                "trocas_classe",
                0,
            )
            or 0
        )


        if (
            dias <= 0
            or chaves_masmorra < 0
            or trocas_classe < 0
        ):
            return {
                "success": False,

                "error": (
                    "Dados do Eldora Premium "
                    "são inválidos."
                ),
            }


        # --------------------------------------------------------
        # 👑 CRÉDITO PREMIUM ATÔMICO E IDEMPOTENTE
        # --------------------------------------------------------

        jogador = (
            users_col.find_one(
                {
                    "_id":
                        jogador_id,
                },

                {
                    "inventory": 1,
                    "eldora_premium": 1,
                    "premium_order_credits": 1,
                    "gems": 1,
                },
            )
            or {}
        )


        if not jogador:
            return {
                "success": False,

                "error":
                    "Jogador do pedido não encontrado.",
            }


        creditos = (
            jogador.get(
                "premium_order_credits"
            )
            or []
        )


        ja_creditado = (
            codigo_pedido
            in creditos
        )


        if not ja_creditado:

            credito_premium = (
                _preparar_credito_eldora_premium(
                    jogador,
                    pedido,
                    codigo_pedido,
                    agora,
                )
            )


            if not credito_premium:
                return {
                    "success": False,

                    "error": (
                        "Não foi possível preparar "
                        "o crédito do Eldora Premium."
                    ),
                }


            filtro_credito = {
                "_id":
                    jogador_id,

                "premium_order_credits": {
                    "$ne":
                        codigo_pedido
                },
            }


            if "inventory" in jogador:

                filtro_credito[
                    "inventory"
                ] = jogador.get(
                    "inventory"
                )

            else:

                filtro_credito[
                    "inventory"
                ] = {
                    "$exists":
                        False
                }


            if "eldora_premium" in jogador:

                filtro_credito[
                    "eldora_premium"
                ] = jogador.get(
                    "eldora_premium"
                )

            else:

                filtro_credito[
                    "eldora_premium"
                ] = {
                    "$exists":
                        False
                }


            credito = (
                users_col.update_one(
                    filtro_credito,

                    {
                        "$set": {
                            "inventory":
                                credito_premium[
                                    "inventory"
                                ],

                            "eldora_premium":
                                credito_premium[
                                    "eldora_premium"
                                ],
                        },

                        "$addToSet": {
                            "premium_order_credits":
                                codigo_pedido
                        },
                    },
                )
            )


            if credito.modified_count != 1:

                jogador_conferencia = (
                    users_col.find_one(
                        {
                            "_id":
                                jogador_id,
                        },

                        {
                            "premium_order_credits": 1,
                        },
                    )
                    or {}
                )


                creditos = (
                    jogador_conferencia.get(
                        "premium_order_credits"
                    )
                    or []
                )


                if (
                    codigo_pedido
                    not in creditos
                ):
                    return {
                        "success": False,

                        "error": (
                            "Os dados do jogador mudaram "
                            "durante a aprovação. "
                            "Execute Aprovar novamente."
                        ),
                    }


        # --------------------------------------------------------
        # ✅ FINALIZA PEDIDO PREMIUM
        # --------------------------------------------------------

        finalizacao = (
            premium_orders_col
            .update_one(
                {
                    "_id":
                        pedido["_id"],

                    "status":
                        STATUS_PROCESSANDO_APROVACAO,
                },

                {
                    "$set": {
                        "status":
                            STATUS_APROVADO,

                        "aprovado_em":
                            agora,

                        "aprovado_por":
                            aprovado_por,

                        "atualizado_em":
                            agora,

                        "credito_confirmado":
                            True,
                    }
                },
            )
        )


        if finalizacao.modified_count != 1:

            pedido_atual = (
                premium_orders_col
                .find_one({
                    "_id":
                        pedido["_id"]
                })
            )


            if (
                not pedido_atual
                or pedido_atual.get(
                    "status"
                )
                != STATUS_APROVADO
            ):
                return {
                    "success": False,

                    "error": (
                        "O Eldora Premium foi registrado "
                        "para o jogador, mas o pedido "
                        "não conseguiu finalizar. "
                        "Execute Aprovar novamente para "
                        "concluir com segurança."
                    ),
                }


        jogador_atual = (
            users_col.find_one(
                {
                    "_id":
                        jogador_id,
                },

                {
                    "gems": 1,
                    "inventory": 1,
                    "eldora_premium": 1,
                },
            )
            or {}
        )


        premium_atual = (
            jogador_atual.get(
                "eldora_premium"
            )
            or {}
        )


        inventario_atual = (
            jogador_atual.get(
                "inventory"
            )
            or {}
        )


        item_chave = (
            inventario_atual.get(
                "chave_masmorra"
            )
        )


        if item_chave is None:

            for _uid, _item in (
                inventario_atual.items()
            ):

                if (
                    isinstance(
                        _item,
                        dict,
                    )
                    and _item.get(
                        "base_id"
                    )
                    == "chave_masmorra"
                ):
                    item_chave = _item
                    break


        quantidade_chaves = (
            _quantidade_chaves_masmorra(
                item_chave
            )
        )


        pedido_final = (
            premium_orders_col
            .find_one({
                "_id":
                    pedido["_id"]
            })
            or pedido
        )


        return {
            "success": True,

            "message": (
                f"Pedido {codigo_pedido} aprovado. "
                "Eldora Premium ativado com sucesso."
            ),

            "pedido":
                _serializar_pedido_admin(
                    pedido_final
                ),

            "novo_saldo_gemas":
                int(
                    jogador_atual.get(
                        "gems",
                        0,
                    )
                    or 0
                ),

            "premium_expira_em":
                _serializar_data(
                    premium_atual.get(
                        "expires_at"
                    )
                ),

            "chaves_masmorra":
                quantidade_chaves,

            "trocas_classe_disponiveis":
                int(
                    premium_atual.get(
                        "class_change_credits",
                        0,
                    )
                    or 0
                ),
        }


    else:
        return {
            "success": False,

            "error": (
                "Tipo de produto do pedido "
                "não é reconhecido."
            ),
        }

    # --------------------------------------------------------
    # 💎 GARANTIA DO FLUXO DE GEMAS
    # --------------------------------------------------------

    if tipo_produto != "gemas":
        return {
            "success": False,

            "error": (
                "O produto não pode utilizar "
                "o fluxo de crédito de Gemas."
            ),
        }
    
    jogador = users_col.find_one(
        {
            "_id":
                jogador_id,
        },

        {
            "gems": 1,
            "premium_order_credits": 1,
        },
    )


    if not jogador:
        return {
            "success": False,
            "error":
                "Jogador do pedido não encontrado.",
        }


    # --------------------------------------------------------
    # 💎 CRÉDITO ATÔMICO E IDEMPOTENTE
    #
    # Só entrega Gems se este código de pedido
    # ainda não estiver registrado no jogador.
    # --------------------------------------------------------

    credito = users_col.update_one(
        {
            "_id":
                jogador_id,

            "premium_order_credits": {
                "$ne":
                    codigo_pedido
            },
        },

        {
            "$inc": {
                "gems":
                    gemas
            },

            "$addToSet": {
                "premium_order_credits":
                    codigo_pedido
            },
        },
    )


    # Se não modificou, pode significar que
    # uma tentativa anterior já entregou.
    if credito.modified_count != 1:

        jogador = (
            users_col.find_one(
                {
                    "_id":
                        jogador_id,
                },

                {
                    "gems": 1,
                    "premium_order_credits": 1,
                },
            )
            or {}
        )


        creditos = (
            jogador.get(
                "premium_order_credits"
            )
            or []
        )


        if (
            codigo_pedido
            not in creditos
        ):

            return {
                "success": False,

                "error": (
                    "Não foi possível creditar "
                    "as Gemas. Tente a aprovação "
                    "novamente."
                ),
            }


    # --------------------------------------------------------
    # ✅ FINALIZA PEDIDO
    # --------------------------------------------------------

    finalizacao = (
        premium_orders_col
        .update_one(
            {
                "_id":
                    pedido["_id"],

                "status":
                    STATUS_PROCESSANDO_APROVACAO,
            },

            {
                "$set": {
                    "status":
                        STATUS_APROVADO,

                    "aprovado_em":
                        agora,

                    "aprovado_por":
                        aprovado_por,

                    "atualizado_em":
                        agora,

                    "credito_confirmado":
                        True,
                }
            },
        )
    )


    if finalizacao.modified_count != 1:

        pedido_atual = (
            premium_orders_col
            .find_one({
                "_id":
                    pedido["_id"]
            })
        )


        if (
            not pedido_atual
            or pedido_atual.get(
                "status"
            )
            != STATUS_APROVADO
        ):

            return {
                "success": False,

                "error": (
                    "As Gemas foram registradas "
                    "para o jogador, mas o pedido "
                    "não conseguiu finalizar. "
                    "Execute Aprovar novamente para "
                    "concluir com segurança."
                ),
            }


    jogador_atual = (
        users_col.find_one(
            {
                "_id":
                    jogador_id,
            },
            {
                "gems": 1,
            },
        )
        or {}
    )


    pedido_final = (
        premium_orders_col
        .find_one({
            "_id":
                pedido["_id"]
        })
        or pedido
    )


    return {
        "success": True,

        "message": (
            f"Pedido {codigo_pedido} aprovado. "
            f"+{gemas} Gemas entregues."
        ),

        "pedido":
            _serializar_pedido_admin(
                pedido_final
            ),

        "novo_saldo_gemas":
            int(
                jogador_atual.get(
                    "gems",
                    0,
                )
                or 0
            ),
    }


# ============================================================
# ❌ RECUSAR PEDIDO
# ============================================================

def recusar_pedido_manual(
    codigo_pedido,
    recusado_por="admin",
    motivo="",
):
    codigo_pedido = str(
        codigo_pedido or ""
    ).strip()


    recusado_por = str(
        recusado_por or "admin"
    ).strip() or "admin"


    motivo = str(
        motivo or ""
    ).strip()[:300]


    if not codigo_pedido:
        return {
            "success": False,
            "error":
                "Pedido não informado.",
        }


    if premium_orders_col is None:
        return {
            "success": False,
            "error":
                "Banco de dados indisponível.",
        }


    agora = _agora()


    pedido = (
        premium_orders_col
        .find_one_and_update(
            {
                "codigo":
                    codigo_pedido,

                "status": {
                    "$in": [
                        STATUS_AGUARDANDO_PAGAMENTO,
                        STATUS_EM_ANALISE,
                    ]
                },
            },

            {
                "$set": {
                    "status":
                        STATUS_RECUSADO,

                    "recusado_em":
                        agora,

                    "recusado_por":
                        recusado_por,

                    "motivo_recusa":
                        motivo,

                    "atualizado_em":
                        agora,
                }
            },

            return_document=
                ReturnDocument.AFTER,
        )
    )


    if not pedido:

        atual = (
            premium_orders_col
            .find_one({
                "codigo":
                    codigo_pedido
            })
        )


        if not atual:
            return {
                "success": False,
                "error":
                    "Pedido não encontrado.",
            }


        if (
            atual.get(
                "status"
            )
            == STATUS_RECUSADO
        ):

            return {
                "success": True,

                "ja_processado":
                    True,

                "message":
                    "Este pedido já havia sido recusado.",

                "pedido":
                    _serializar_pedido_admin(
                        atual
                    ),
            }


        return {
            "success": False,

            "error": (
                "Somente pedidos pendentes "
                "podem ser recusados."
            ),
        }


    return {
        "success": True,

        "message":
            f"Pedido {codigo_pedido} recusado.",

        "pedido":
            _serializar_pedido_admin(
                pedido
            ),
    }
