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
    obter_pacote_gemas,
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

        "gemas":
            int(
                pedido.get(
                    "gemas",
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
        },
    )


    if not jogador:
        return {
            "success": False,
            "error":
                "Jogador não encontrado.",
        }


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

        "pacotes":
            pacotes,
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


    pacote = obter_pacote_gemas(
        pacote_id
    )


    if not pacote:
        return {
            "success": False,
            "error": (
                "Pacote de gemas inválido "
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

        "gemas":
            int(
                pacote["gemas"]
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

            "gemas":
                int(
                    pedido.get(
                        "gemas",
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

                "gemas":
                    int(
                        pedido.get(
                            "gemas",
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
                    "gems": 1
                },
            )
            or {}
        )


        return {
            "success": True,

            "ja_processado": True,

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


    if status not in {
        STATUS_EM_ANALISE,
        STATUS_PROCESSANDO_APROVACAO,
    }:

        return {
            "success": False,

            "error": (
                "Somente pedidos em análise "
                "podem ser aprovados."
            ),
        }


    agora = _agora()


    # --------------------------------------------------------
    # 🔒 RESERVA ATÔMICA DO PEDIDO
    #
    # Antes de mexer nas Gems, tira o pedido de "em_analise".
    # Assim uma recusa não pode acontecer simultaneamente.
    # --------------------------------------------------------

    if status == STATUS_EM_ANALISE:

        reservado = (
            premium_orders_col
            .update_one(
                {
                    "_id":
                        pedido["_id"],

                    "status":
                        STATUS_EM_ANALISE,
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
                            "gems": 1
                        },
                    )
                    or {}
                )


                return {
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


    gemas = int(
        pedido.get(
            "gemas",
            0,
        )
        or 0
    )


    if (
        not jogador_id
        or gemas <= 0
    ):
        return {
            "success": False,

            "error": (
                "Dados de crédito do pedido "
                "são inválidos."
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

                "status":
                    STATUS_EM_ANALISE,
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
                "Somente pedidos em análise "
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

    