# ============================================================
# 🏪 MUNDO DE ELDORA - LOJA DA GUILDA DOS AVENTUREIROS
# ============================================================
#
# Catálogo oficial da Loja da Guilda.
#
# O backend é autoridade sobre:
# - preço
# - Rank necessário
# - tipo de produto
# - unlock_id
# - disponibilidade
#
# A profissão necessária para fabricar NÃO pertence aqui.
# Ela continuará definida na própria receita do crafting.
#
# ============================================================

from __future__ import annotations

from copy import deepcopy

from .guild_mission_registry import (
    GUILD_RANKS,
)


# ============================================================
# 📦 TIPOS DE PRODUTO
# ============================================================

TIPO_RECEITA = "receita"
TIPO_COSMETICO = "cosmetico"
TIPO_ITEM = "item"


# ============================================================
# 🏅 RANKS
# ============================================================

RANK_ORDEM = {
    str(rank["id"]):
        indice

    for indice, rank
    in enumerate(GUILD_RANKS)
}


RANKS_POR_ID = {
    str(rank["id"]):
        dict(rank)

    for rank
    in GUILD_RANKS
}


# ============================================================
# 🏪 CATÁLOGO
# ============================================================
#
# PRIMEIRO CONJUNTO:
# Conjunto do Aventureiro da Guilda
#
# Por enquanto cadastramos somente os desbloqueios.
# As receitas reais serão criadas depois.
#
# ============================================================

GUILD_SHOP_ITEMS = {

    # --------------------------------------------------------
    # FERRO
    # --------------------------------------------------------

    "guild_receita_botas_aventureiro": {

        "id":
            "guild_receita_botas_aventureiro",

        "tipo":
            TIPO_RECEITA,

        "nome":
            "Receita: Botas do Aventureiro",

        "descricao": (
            "Desbloqueia permanentemente a receita "
            "das Botas do Aventureiro."
        ),

        "unlock_id":
            "guild_aventureiro_botas",

        "rank_minimo":
            "ferro",

        "custo_pontos":
            75,

        "ativa":
            True,
    },


    # --------------------------------------------------------
    # BRONZE
    # --------------------------------------------------------

    "guild_receita_luvas_aventureiro": {

        "id":
            "guild_receita_luvas_aventureiro",

        "tipo":
            TIPO_RECEITA,

        "nome":
            "Receita: Luvas do Aventureiro",

        "descricao": (
            "Desbloqueia permanentemente a receita "
            "das Luvas do Aventureiro."
        ),

        "unlock_id":
            "guild_aventureiro_luvas",

        "rank_minimo":
            "bronze",

        "custo_pontos":
            125,

        "ativa":
            True,
    },


    # --------------------------------------------------------
    # PRATA
    # --------------------------------------------------------

    "guild_receita_calcas_aventureiro": {

        "id":
            "guild_receita_calcas_aventureiro",

        "tipo":
            TIPO_RECEITA,

        "nome":
            "Receita: Calças do Aventureiro",

        "descricao": (
            "Desbloqueia permanentemente a receita "
            "das Calças do Aventureiro."
        ),

        "unlock_id":
            "guild_aventureiro_calcas",

        "rank_minimo":
            "prata",

        "custo_pontos":
            225,

        "ativa":
            True,
    },


    # --------------------------------------------------------
    # OURO
    # --------------------------------------------------------

    "guild_receita_couraca_aventureiro": {

        "id":
            "guild_receita_couraca_aventureiro",

        "tipo":
            TIPO_RECEITA,

        "nome":
            "Receita: Couraça do Aventureiro",

        "descricao": (
            "Desbloqueia permanentemente a receita "
            "da Couraça do Aventureiro."
        ),

        "unlock_id":
            "guild_aventureiro_couraca",

        "rank_minimo":
            "ouro",

        "custo_pontos":
            350,

        "ativa":
            True,
    },


    # --------------------------------------------------------
    # PLATINA
    # --------------------------------------------------------

    "guild_receita_elmo_aventureiro": {

        "id":
            "guild_receita_elmo_aventureiro",

        "tipo":
            TIPO_RECEITA,

        "nome":
            "Receita: Elmo do Aventureiro",

        "descricao": (
            "Desbloqueia permanentemente a receita "
            "do Elmo do Aventureiro."
        ),

        "unlock_id":
            "guild_aventureiro_elmo",

        "rank_minimo":
            "platina",

        "custo_pontos":
            500,

        "ativa":
            True,
    },
}


# ============================================================
# 🔧 HELPERS
# ============================================================

def obter_rank_loja(
    rank_id,
):
    """
    Retorna os dados oficiais de um Rank.
    """

    rank_id = str(
        rank_id or ""
    ).strip().lower()


    rank = RANKS_POR_ID.get(
        rank_id
    )


    if not rank:
        return None


    return deepcopy(
        rank
    )


def obter_reputacao_minima(
    rank_id,
):
    """
    Descobre a reputação mínima do Rank
    usando GUILD_RANKS como fonte oficial.
    """

    rank = obter_rank_loja(
        rank_id
    )


    if not rank:
        return None


    return int(
        rank.get(
            "reputacao_minima",
            0,
        )
        or 0
    )


def obter_item_loja(
    item_id,
):
    """
    Busca um produto pelo ID.
    """

    item_id = str(
        item_id or ""
    ).strip()


    item = GUILD_SHOP_ITEMS.get(
        item_id
    )


    if not item:
        return None


    dados = deepcopy(
        item
    )


    dados[
        "reputacao_minima"
    ] = obter_reputacao_minima(
        dados.get(
            "rank_minimo"
        )
    )


    return dados


def listar_itens_loja(
    apenas_ativos=True,
):
    """
    Lista o catálogo oficial.
    """

    itens = []


    for item_id in GUILD_SHOP_ITEMS:

        item = obter_item_loja(
            item_id
        )


        if not item:
            continue


        if (
            apenas_ativos
            and
            not item.get(
                "ativa",
                False,
            )
        ):
            continue


        itens.append(
            item
        )


    itens.sort(
        key=lambda item: (
            RANK_ORDEM.get(
                item.get(
                    "rank_minimo"
                ),
                999,
            ),

            int(
                item.get(
                    "custo_pontos",
                    0,
                )
                or 0
            ),

            str(
                item.get(
                    "nome",
                    "",
                )
            ),
        )
    )


    return itens


def obter_item_por_unlock(
    unlock_id,
):
    """
    Procura no catálogo qual produto
    concede determinado unlock_id.
    """

    unlock_id = str(
        unlock_id or ""
    ).strip()


    if not unlock_id:
        return None


    for item_id in GUILD_SHOP_ITEMS:

        item = obter_item_loja(
            item_id
        )


        if not item:
            continue


        if (
            str(
                item.get(
                    "unlock_id",
                    "",
                )
            ).strip()
            ==
            unlock_id
        ):
            return item


    return None