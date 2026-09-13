# ============================================================
# 🏪 MUNDO DE ELDORA
# GERENCIADOR DA LOJA DA GUILDA DOS AVENTUREIROS
# ============================================================

from __future__ import annotations

from bson import ObjectId

from modules.player.core import (
    users_collection,
)

from . import guild_mission_manager

from .guild_mission_registry import (
    obter_rank_guilda,
)

from .guild_shop_registry import (
    TIPO_RECEITA,
    listar_itens_loja,
    obter_item_loja,
)


# ============================================================
# 🔧 HELPERS
# ============================================================

def _object_id(
    valor,
):

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
# 📜 LOCALIZA RECEITA PELO UNLOCK_ID
# ============================================================

def _localizar_receita_por_unlock(
    unlock_id,
):
    """
    Procura no crafting_registry a receita
    correspondente ao unlock_id vendido
    pela Loja da Guilda.
    """

    unlock_id = str(
        unlock_id
        or ""
    ).strip()


    if not unlock_id:
        return None


    from modules import (
        crafting_registry,
    )


    receitas = (
        crafting_registry
        .all_recipes()
    )


    for (
        recipe_id,
        receita
    ) in receitas.items():

        if not isinstance(
            receita,
            dict,
        ):
            continue


        recipe_unlock = str(
            receita.get(
                "unlock_id",
                "",
            )
            or ""
        ).strip()


        if (
            recipe_unlock
            != unlock_id
        ):
            continue


        return {
            "recipe_id":
                str(
                    recipe_id
                ),

            "receita":
                dict(
                    receita
                ),
        }


    return None


# ============================================================
# 🧪 VALIDAR CATÁLOGO COMPLETO
# ============================================================

def validar_catalogo_loja_guilda():
    """
    Confere a cadeia:

    produto da loja
        -> unlock_id
        -> receita real
        -> result_base_id
        -> item real

    Não acessa nenhum jogador.
    """

    from modules.game_data import (
        items as items_data,
    )


    erros = []

    produtos = (
        listar_itens_loja(
            apenas_ativos=False,
        )
    )


    for produto in produtos:

        item_id = str(
            produto.get(
                "id",
                "",
            )
        )


        if (
            produto.get(
                "tipo"
            )
            != TIPO_RECEITA
        ):
            continue


        unlock_id = str(
            produto.get(
                "unlock_id",
                "",
            )
            or ""
        ).strip()


        if not unlock_id:

            erros.append(
                f"{item_id}: "
                "unlock_id ausente."
            )

            continue


        localizada = (
            _localizar_receita_por_unlock(
                unlock_id
            )
        )


        if not localizada:

            erros.append(
                f"{item_id}: "
                f"nenhuma receita usa "
                f"'{unlock_id}'."
            )

            continue


        receita = (
            localizada[
                "receita"
            ]
        )


        result_base_id = str(
            receita.get(
                "result_base_id",
                "",
            )
            or ""
        ).strip()


        if not result_base_id:

            erros.append(
                f"{item_id}: "
                "receita sem result_base_id."
            )

            continue


        if (
            result_base_id
            not in
            items_data.ITEMS_DATA
        ):

            erros.append(
                f"{item_id}: "
                f"item final inexistente "
                f"'{result_base_id}'."
            )


    return {
        "success":
            len(
                erros
            ) == 0,

        "total_produtos":
            len(
                produtos
            ),

        "total_erros":
            len(
                erros
            ),

        "erros":
            erros,
    }


# ============================================================
# 🏪 CATÁLOGO PARA O JOGADOR
# ============================================================

def obter_catalogo_loja_guilda(
    user_id,
):

    player_id = _object_id(
        user_id
    )


    if not player_id:

        return {
            "success": False,
            "error":
                "ID de jogador inválido.",
        }


    jogador = (
        users_collection
        .find_one(
            {
                "_id":
                    player_id,
            },
            {
                "character_name":
                    1,

                "guild_missions":
                    1,
            },
        )
    )


    if not jogador:

        return {
            "success": False,
            "error":
                "Herói não encontrado.",
        }


    # ========================================================
    # 🏅 ESTADO OFICIAL DA GUILDA
    # ========================================================

    estado = (
        guild_mission_manager
        ._obter_estado(
            jogador
        )
    )


    migrou = (
        guild_mission_manager
        ._garantir_reputacao_persistida(
            jogador,
            estado,
        )
    )


    # Caso a reputação de uma conta antiga
    # tenha acabado de ser persistida,
    # fazemos uma leitura nova.
    if migrou:

        jogador = (
            users_collection
            .find_one(
                {
                    "_id":
                        player_id,
                },
                {
                    "character_name":
                        1,

                    "guild_missions":
                        1,
                },
            )
            or jogador
        )


        estado = (
            guild_mission_manager
            ._obter_estado(
                jogador
            )
        )


    saldo = int(
        estado.get(
            "pontos",
            0,
        )
        or 0
    )


    reputacao_total = int(
        estado.get(
            "pontos_total",
            saldo,
        )
        or 0
    )


    desbloqueadas = {
        str(
            unlock_id
        ).strip()

        for unlock_id
        in (
            estado.get(
                "receitas_desbloqueadas",
                [],
            )
            or []
        )

        if str(
            unlock_id
        ).strip()
    }


    rank_guilda = (
        obter_rank_guilda(
            reputacao_total
        )
    )


    produtos_formatados = []


    # ========================================================
    # 🛒 PRODUTOS
    # ========================================================

    for produto in (
        listar_itens_loja()
    ):

        dados = dict(
            produto
        )


        custo = int(
            dados.get(
                "custo_pontos",
                0,
            )
            or 0
        )


        reputacao_minima = int(
            dados.get(
                "reputacao_minima",
                0,
            )
            or 0
        )


        unlock_id = str(
            dados.get(
                "unlock_id",
                "",
            )
            or ""
        ).strip()


        desbloqueado = (
            bool(
                unlock_id
            )
            and
            unlock_id
            in desbloqueadas
        )


        atende_reputacao = (
            reputacao_total
            >=
            reputacao_minima
        )


        saldo_suficiente = (
            saldo
            >=
            custo
        )


        localizada = None

        if (
            dados.get(
                "tipo"
            )
            ==
            TIPO_RECEITA
        ):

            localizada = (
                _localizar_receita_por_unlock(
                    unlock_id
                )
            )


        receita_valida = (
            localizada
            is not None
        )


        recipe_id = None
        result_base_id = None


        if localizada:

            recipe_id = (
                localizada.get(
                    "recipe_id"
                )
            )


            result_base_id = str(
                (
                    localizada.get(
                        "receita",
                        {},
                    )
                    or {}
                ).get(
                    "result_base_id",
                    "",
                )
                or ""
            ).strip()


        dados[
            "desbloqueado"
        ] = desbloqueado


        dados[
            "atende_reputacao"
        ] = atende_reputacao


        dados[
            "saldo_suficiente"
        ] = saldo_suficiente


        dados[
            "pode_comprar"
        ] = bool(
            receita_valida
            and
            not desbloqueado
            and
            atende_reputacao
            and
            saldo_suficiente
        )


        dados[
            "recipe_id"
        ] = recipe_id


        dados[
            "result_base_id"
        ] = result_base_id


        dados[
            "receita_valida"
        ] = receita_valida


        dados[
            "pontos_faltantes"
        ] = max(
            0,
            custo
            -
            saldo,
        )


        dados[
            "reputacao_faltante"
        ] = max(
            0,
            reputacao_minima
            -
            reputacao_total,
        )


        produtos_formatados.append(
            dados
        )


    return {
        "success": True,

        "jogador": {
            "id":
                str(
                    player_id
                ),

            "nome":
                jogador.get(
                    "character_name",
                    "Aventureiro",
                ),
        },

        "pontos_guilda":
            saldo,

        "reputacao_total":
            reputacao_total,

        "rank_guilda":
            rank_guilda,

        "receitas_desbloqueadas":
            sorted(
                desbloqueadas
            ),

        "itens":
            produtos_formatados,
    }


# ============================================================
# 🛒 COMPRAR PRODUTO
# ============================================================

def comprar_item_loja_guilda(
    user_id,
    item_id,
):

    player_id = _object_id(
        user_id
    )


    if not player_id:

        return {
            "success": False,
            "error":
                "ID de jogador inválido.",
        }


    item_id = str(
        item_id
        or ""
    ).strip()


    if not item_id:

        return {
            "success": False,
            "error":
                "Produto não informado.",
        }


    # ========================================================
    # 📦 PRODUTO OFICIAL
    # ========================================================

    produto = (
        obter_item_loja(
            item_id
        )
    )


    if not produto:

        return {
            "success": False,
            "error":
                "Produto inexistente.",
        }


    if not produto.get(
        "ativa",
        False,
    ):

        return {
            "success": False,
            "error":
                "Este produto está indisponível.",
        }


    # ========================================================
    # 📜 RECEITA
    # ========================================================

    if (
        produto.get(
            "tipo"
        )
        !=
        TIPO_RECEITA
    ):

        return {
            "success": False,
            "error": (
                "Este tipo de produto ainda "
                "não pode ser comprado."
            ),
        }


    unlock_id = str(
        produto.get(
            "unlock_id",
            "",
        )
        or ""
    ).strip()


    if not unlock_id:

        return {
            "success": False,
            "error": (
                "Produto com desbloqueio "
                "inválido."
            ),
        }


    localizada = (
        _localizar_receita_por_unlock(
            unlock_id
        )
    )


    if not localizada:

        return {
            "success": False,
            "error": (
                "A receita deste produto "
                "não está registrada."
            ),
        }


    receita = (
        localizada.get(
            "receita",
            {}
        )
        or {}
    )


    result_base_id = str(
        receita.get(
            "result_base_id",
            "",
        )
        or ""
    ).strip()


    if not result_base_id:

        return {
            "success": False,
            "error": (
                "A receita não possui "
                "item final configurado."
            ),
        }


    from modules.game_data import (
        items as items_data,
    )


    if (
        result_base_id
        not in
        items_data.ITEMS_DATA
    ):

        return {
            "success": False,
            "error": (
                "O equipamento desta receita "
                "não existe no catálogo."
            ),
        }


    # ========================================================
    # 🔒 COMPRA ATÔMICA
    # ========================================================

    resultado = (
        guild_mission_manager
        .desbloquear_receita_guilda(

            user_id=
                player_id,

            unlock_id=
                unlock_id,

            custo_pontos=
                produto.get(
                    "custo_pontos",
                    0,
                ),

            reputacao_minima=
                produto.get(
                    "reputacao_minima",
                    0,
                ),
        )
    )


    if not resultado.get(
        "success"
    ):

        resultado[
            "item_id"
        ] = item_id

        return resultado


    # ========================================================
    # ✅ RESPOSTA
    # ========================================================

    resultado[
        "item_id"
    ] = item_id


    resultado[
        "produto"
    ] = {
        "id":
            item_id,

        "nome":
            produto.get(
                "nome",
                item_id,
            ),

        "tipo":
            produto.get(
                "tipo"
            ),

        "unlock_id":
            unlock_id,

        "rank_minimo":
            produto.get(
                "rank_minimo"
            ),

        "reputacao_minima":
            produto.get(
                "reputacao_minima",
                0,
            ),

        "custo_pontos":
            produto.get(
                "custo_pontos",
                0,
            ),

        "recipe_id":
            localizada.get(
                "recipe_id"
            ),

        "result_base_id":
            result_base_id,
    }


    return resultado