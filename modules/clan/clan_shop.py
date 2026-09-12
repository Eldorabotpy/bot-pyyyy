# ============================================================
# 🏅 MUNDO DE ELDORA - LOJA DO CLÃ
# ============================================================

from __future__ import annotations

import copy

from bson import ObjectId

from modules.player.core import (
    users_collection,
)

from modules.player.inventory import (
    get_medalhas_cla,
)

from modules.game_data.items_consumables import (
    CONSUMABLES_DATA,
)

from modules.clan import (
    clan_manager,
)


# ============================================================
# 🛒 CATÁLOGO OFICIAL
# ============================================================

CLAN_SHOP_ITEMS = {

    "pocao_cura_media": {
        "custo_medalhas": 5,
        "limite_semanal": 10,
    },

    "pocao_mana_media": {
        "custo_medalhas": 5,
        "limite_semanal": 10,
    },

    "pedra_de_aprimoramento": {
        "custo_medalhas": 10,
        "limite_semanal": 5,
    },

    "nucleo_de_forja": {
        "custo_medalhas": 12,
        "limite_semanal": 5,
    },

    "pergaminho_de_reparo": {
        "custo_medalhas": 15,
        "limite_semanal": 3,
    },

    "sigilo_de_protecao": {
        "custo_medalhas": 30,
        "limite_semanal": 2,
    },
}


# ============================================================
# 🔧 HELPERS
# ============================================================

def _object_id(valor):

    if isinstance(
        valor,
        ObjectId,
    ):
        return valor


    if valor is None:
        return None


    texto = str(
        valor
    ).strip()


    if not ObjectId.is_valid(
        texto
    ):
        return None


    return ObjectId(
        texto
    )

# ============================================================
# 📅 SEMANA OFICIAL
# ============================================================

def _semana_id_atual():

    from modules.clan.clan_war_manager import (
        obter_semana_id,
    )


    return str(
        obter_semana_id()
    ).strip()


# ============================================================
# 📦 ADICIONAR ITEM EMPILHÁVEL
# ============================================================

def _adicionar_item_empilhavel(
    inventario,
    item_id,
    quantidade,
):

    if not isinstance(
        inventario,
        dict,
    ):
        inventario = {}


    quantidade = int(
        quantidade
    )


    # ========================================================
    # 📦 ITEM NA CHAVE PRINCIPAL
    # ========================================================

    if item_id in inventario:

        atual = inventario[
            item_id
        ]


        if isinstance(
            atual,
            dict,
        ):

            atual[
                "base_id"
            ] = (
                atual.get(
                    "base_id"
                )
                or item_id
            )


            atual[
                "quantity"
            ] = (
                int(
                    atual.get(
                        "quantity",
                        0,
                    )
                    or 0
                )
                +
                quantidade
            )


        else:

            inventario[
                item_id
            ] = (
                int(
                    atual
                    or 0
                )
                +
                quantidade
            )


        return inventario


    # ========================================================
    # 🔎 ITEM EMPILHÁVEL COM OUTRA CHAVE
    # ========================================================

    for (
        chave,
        item
    ) in inventario.items():

        if not isinstance(
            item,
            dict,
        ):
            continue


        if (
            str(
                item.get(
                    "base_id",
                    ""
                )
            )
            !=
            str(
                item_id
            )
        ):
            continue


        item[
            "quantity"
        ] = (
            int(
                item.get(
                    "quantity",
                    0,
                )
                or 0
            )
            +
            quantidade
        )


        inventario[
            chave
        ] = item


        return inventario


    # ========================================================
    # ➕ PRIMEIRA UNIDADE
    # ========================================================

    inventario[
        item_id
    ] = {
        "base_id":
            item_id,

        "quantity":
            quantidade,
    }


    return inventario

# ============================================================
# 🏅 OBTER CATÁLOGO DA LOJA
# ============================================================

def obter_catalogo_loja_cla(
    user_id,
):

    player_id = _object_id(
        user_id
    )


    if not player_id:
        return {
            "success": False,
            "error": (
                "Jogador inválido."
            ),
        }


    jogador = (
        users_collection.find_one(
            {
                "_id":
                    player_id,
            },
            {
                "character_name": 1,
                "medalhas_cla": 1,
                "clan_id": 1,
                "loja_cla": 1,
            },
        )
    )


    if not jogador:
        return {
            "success": False,
            "error": (
                "Jogador não encontrado."
            ),
        }


    # ========================================================
    # 🛡️ CONFIRMA O CLÃ REAL DO JOGADOR
    # ========================================================

    cla = (
        clan_manager
        .obter_cla_do_jogador(
            player_id
        )
    )


    if not cla:
        return {
            "success": False,
            "error": (
                "Você precisa pertencer "
                "a um clã para acessar "
                "a Loja do Clã."
            ),
        }


    # ========================================================
    # 🏅 SALDO REAL
    # ========================================================

    saldo_medalhas = (
        get_medalhas_cla(
            jogador
        )
    )

    # ========================================================
    # 📅 COMPRAS DA SEMANA ATUAL
    # ========================================================

    semana_id = (
        _semana_id_atual()
    )


    loja_atual = (
        jogador.get(
            "loja_cla"
        )
    )


    if not isinstance(
        loja_atual,
        dict,
    ):
        loja_atual = {}


    if (
        str(
            loja_atual.get(
                "semana_id",
                ""
            )
        )
        ==
        semana_id
    ):

        compras_semana = (
            loja_atual.get(
                "compras",
                {}
            )
        )


        if not isinstance(
            compras_semana,
            dict,
        ):
            compras_semana = {}

    else:

        compras_semana = {}

    # ========================================================
    # 🛒 MONTA CATÁLOGO
    # ========================================================

    itens = []


    for (
        item_id,
        configuracao
    ) in CLAN_SHOP_ITEMS.items():

        item = (
            CONSUMABLES_DATA.get(
                item_id
            )
        )


        if not item:
            continue

        limite_semanal = int(
            configuracao.get(
                "limite_semanal",
                0,
            )
            or 0
        )


        comprado_semana = int(
            compras_semana.get(
                item_id,
                0,
            )
            or 0
        )


        restante_semana = max(
            0,
            limite_semanal
            -
            comprado_semana,
        )

        itens.append({

            "item_id":
                item_id,

            "nome":
                item.get(
                    "display_name",
                    item_id,
                ),

            "emoji":
                item.get(
                    "emoji",
                    "📦",
                ),

            "icon_url":
                item.get(
                    "icon_url",
                    ""
                ),

            "descricao":
                item.get(
                    "description",
                    "",
                ),

            "custo_medalhas":
                int(
                    configuracao.get(
                        "custo_medalhas",
                        0,
                    )
                    or 0
                ),

            "limite_semanal":
                limite_semanal,

            "comprado_semana":
                comprado_semana,

            "restante_semana":
                restante_semana,
        })


    return {

        "success":
            True,

        "medalhas_cla":
            int(
                saldo_medalhas
            ),

        "semana_id":
            semana_id,

        "clan": {
            "id":
                str(
                    cla.get(
                        "_id"
                    )
                ),

            "nome":
                cla.get(
                    "nome",
                    "Clã",
                ),

            "tag":
                cla.get(
                    "tag",
                    "",
                ),
        },

        "itens":
            itens,
    }

# ============================================================
# 🛒 COMPRAR ITEM NA LOJA DO CLÃ
# ============================================================

def comprar_item_loja_cla(
    user_id,
    item_id,
    quantidade=1,
):

    player_id = _object_id(
        user_id
    )


    if not player_id:

        return {
            "success": False,
            "error": "Jogador inválido.",
        }


    item_id = str(
        item_id
        or ""
    ).strip()


    if not item_id:

        return {
            "success": False,
            "error": "Item não informado.",
        }


    try:
        quantidade = int(
            quantidade
        )

    except (
        TypeError,
        ValueError,
    ):

        quantidade = 0


    if quantidade <= 0:

        return {
            "success": False,
            "error": (
                "Quantidade inválida."
            ),
        }


    # ========================================================
    # 🛡️ CONFIRMA O CLÃ REAL
    # ========================================================

    cla = (
        clan_manager
        .obter_cla_do_jogador(
            player_id
        )
    )


    if not cla:

        return {
            "success": False,
            "error": (
                "Você precisa pertencer "
                "a um clã para comprar "
                "na Loja do Clã."
            ),
        }


    # ========================================================
    # 🛒 PRODUTO OFICIAL
    # ========================================================

    configuracao = (
        CLAN_SHOP_ITEMS.get(
            item_id
        )
    )


    if not configuracao:

        return {
            "success": False,
            "error": (
                "Este item não está disponível "
                "na Loja do Clã."
            ),
        }


    item = (
        CONSUMABLES_DATA.get(
            item_id
        )
    )


    if not item:

        return {
            "success": False,
            "error": (
                "O item configurado não existe "
                "no catálogo do jogo."
            ),
        }


    if not item.get(
        "stackable",
        False,
    ):

        return {
            "success": False,
            "error": (
                "Este tipo de item ainda não pode "
                "ser comprado nesta loja."
            ),
        }


    custo_unitario = int(
        configuracao.get(
            "custo_medalhas",
            0,
        )
        or 0
    )


    limite_semanal = int(
        configuracao.get(
            "limite_semanal",
            0,
        )
        or 0
    )


    if custo_unitario <= 0:

        return {
            "success": False,
            "error": (
                "Este item possui preço inválido."
            ),
        }


    custo_total = (
        custo_unitario
        *
        quantidade
    )


    semana_id = (
        _semana_id_atual()
    )


    # ========================================================
    # 🔒 ATUALIZAÇÃO OTIMISTA
    #
    # Evita duas compras simultâneas gastarem
    # o mesmo saldo ou ultrapassarem o limite.
    # ========================================================

    for _tentativa in range(
        3
    ):

        jogador = (
            users_collection.find_one({
                "_id":
                    player_id,
            })
        )


        if not jogador:

            return {
                "success": False,
                "error": (
                    "Jogador não encontrado."
                ),
            }


        saldo_atual = (
            get_medalhas_cla(
                jogador
            )
        )


        if (
            saldo_atual
            <
            custo_total
        ):

            return {
                "success": False,

                "error": (
                    "Medalhas de Clã "
                    "insuficientes."
                ),

                "medalhas_cla":
                    saldo_atual,

                "custo_total":
                    custo_total,
            }


        # ====================================================
        # 📅 COMPRAS DA SEMANA
        # ====================================================

        loja_original = (
            jogador.get(
                "loja_cla"
            )
        )


        loja_atual = (
            loja_original
            if isinstance(
                loja_original,
                dict,
            )
            else {}
        )


        if (
            str(
                loja_atual.get(
                    "semana_id",
                    ""
                )
            )
            ==
            semana_id
        ):

            compras_atuais = (
                loja_atual.get(
                    "compras",
                    {}
                )
            )


            if not isinstance(
                compras_atuais,
                dict,
            ):

                compras_atuais = {}

        else:

            compras_atuais = {}


        comprado_antes = int(
            compras_atuais.get(
                item_id,
                0,
            )
            or 0
        )


        comprado_depois = (
            comprado_antes
            +
            quantidade
        )


        if (
            limite_semanal > 0
            and
            comprado_depois
            >
            limite_semanal
        ):

            restante = max(
                0,
                limite_semanal
                -
                comprado_antes,
            )


            return {
                "success": False,

                "error": (
                    "Limite semanal "
                    "deste item atingido."
                ),

                "item_id":
                    item_id,

                "limite_semanal":
                    limite_semanal,

                "comprado_semana":
                    comprado_antes,

                "restante_semana":
                    restante,

                "semana_id":
                    semana_id,
            }


        # ====================================================
        # 📦 NOVO INVENTÁRIO
        # ====================================================

        inventario_original = (
            jogador.get(
                "inventory"
            )
        )


        inventario_base = (
            inventario_original
            if isinstance(
                inventario_original,
                dict,
            )
            else {}
        )


        novo_inventario = (
            copy.deepcopy(
                inventario_base
            )
        )


        novo_inventario = (
            _adicionar_item_empilhavel(
                novo_inventario,
                item_id,
                quantidade,
            )
        )


        # ====================================================
        # 📅 NOVO CONTROLE SEMANAL
        # ====================================================

        novas_compras = (
            copy.deepcopy(
                compras_atuais
            )
        )


        novas_compras[
            item_id
        ] = comprado_depois


        nova_loja = {
            "semana_id":
                semana_id,

            "compras":
                novas_compras,
        }


        novo_saldo = (
            saldo_atual
            -
            custo_total
        )


        # ====================================================
        # 🔒 COMPARE-AND-SET
        # ====================================================

        filtro = {
            "_id":
                player_id,
        }


        if (
            "medalhas_cla"
            in jogador
        ):

            filtro[
                "medalhas_cla"
            ] = jogador.get(
                "medalhas_cla"
            )

        else:

            filtro[
                "medalhas_cla"
            ] = {
                "$exists": False,
            }


        if (
            "inventory"
            in jogador
        ):

            filtro[
                "inventory"
            ] = inventario_original

        else:

            filtro[
                "inventory"
            ] = {
                "$exists": False,
            }


        if (
            "loja_cla"
            in jogador
        ):

            filtro[
                "loja_cla"
            ] = loja_original

        else:

            filtro[
                "loja_cla"
            ] = {
                "$exists": False,
            }


        resultado = (
            users_collection
            .update_one(
                filtro,
                {
                    "$set": {
                        "medalhas_cla":
                            novo_saldo,

                        "inventory":
                            novo_inventario,

                        "loja_cla":
                            nova_loja,
                    }
                },
            )
        )


        if (
            resultado.modified_count
            ==
            1
        ):

            restante_semana = max(
                0,
                limite_semanal
                -
                comprado_depois,
            )


            return {
                "success": True,

                "message": (
                    f"Você comprou "
                    f"{quantidade}x "
                    f"{item.get('display_name', item_id)}."
                ),

                "item": {
                    "item_id":
                        item_id,

                    "nome":
                        item.get(
                            "display_name",
                            item_id,
                        ),

                    "emoji":
                        item.get(
                            "emoji",
                            "📦",
                        ),
                },

                "quantidade":
                    quantidade,

                "custo_unitario":
                    custo_unitario,

                "custo_total":
                    custo_total,

                "medalhas_cla":
                    novo_saldo,

                "semana_id":
                    semana_id,

                "comprado_semana":
                    comprado_depois,

                "limite_semanal":
                    limite_semanal,

                "restante_semana":
                    restante_semana,
            }


    return {
        "success": False,
        "error": (
            "A ficha do jogador mudou durante "
            "a compra. Tente novamente."
        ),
    }

