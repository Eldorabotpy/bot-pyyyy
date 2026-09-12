# ============================================================
# 🏅 MUNDO DE ELDORA - LOJA DO CLÃ
# ============================================================

from __future__ import annotations

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
                int(
                    configuracao.get(
                        "limite_semanal",
                        0,
                    )
                    or 0
                ),
        })


    return {

        "success":
            True,

        "medalhas_cla":
            int(
                saldo_medalhas
            ),

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