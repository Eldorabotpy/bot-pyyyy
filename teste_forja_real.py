import asyncio
import json

from modules import player_manager
from modules.crafting_engine import (
    start_craft,
    finish_craft,
)


USER_ID = "69fa8f60080408b128764720"
RECIPE_ID = "craft_martelo_ferreiro_t1"


async def main():

    print("\n==============================")
    print("🔨 INICIANDO FORJA REAL")
    print("==============================")

    pdata_antes = await player_manager.get_player_data(
        USER_ID
    )

    martelo_antes = (
        pdata_antes
        .get("inventory", {})
        .get("martelo_ferreiro_t1", {})
    )

    print(
        "Durabilidade martelo antes:",
        martelo_antes.get("durability")
    )

    resultado_inicio = await start_craft(
        USER_ID,
        RECIPE_ID
    )

    print("\nSTART_CRAFT:")
    print(
        json.dumps(
            resultado_inicio,
            indent=2,
            ensure_ascii=False,
            default=str
        )
    )

    if isinstance(resultado_inicio, str):
        print(
            "\n❌ Não foi possível iniciar:",
            resultado_inicio
        )
        return

    pdata_meio = await player_manager.get_player_data(
        USER_ID
    )

    martelo_meio = (
        pdata_meio
        .get("inventory", {})
        .get("martelo_ferreiro_t1", {})
    )

    print(
        "\nDurabilidade após start:",
        martelo_meio.get("durability")
    )

    print("\nPlayer state:")
    print(
        json.dumps(
            pdata_meio.get("player_state"),
            indent=2,
            ensure_ascii=False,
            default=str
        )
    )

    print("\n==============================")
    print("🏁 FINALIZANDO")
    print("==============================")

    resultado_final = await finish_craft(
        USER_ID
    )

    print(
        json.dumps(
            resultado_final,
            indent=2,
            ensure_ascii=False,
            default=str
        )
    )

    if not isinstance(
        resultado_final,
        dict
    ):
        return

    item = resultado_final.get(
        "item_criado",
        {}
    )

    print("\n==============================")
    print("✨ ITEM CRIADO")
    print("==============================")

    print(
        "UUID:",
        item.get("uuid")
    )

    print(
        "Base ID:",
        item.get("base_id")
    )

    print(
        "Raridade:",
        item.get("rarity")
    )

    print(
        "Tier:",
        item.get("tier")
    )

    print(
        "Tool type:",
        item.get("tool_type")
    )

    print(
        "Durabilidade:",
        item.get("durability")
    )

    print(
        "Sockets:",
        item.get("sockets")
    )

    print("\nAtributos:")

    for chave, dados in (
        item.get("enchantments", {})
        or {}
    ).items():

        print(
            chave,
            "=>",
            dados
        )

    pdata_final = await player_manager.get_player_data(
        USER_ID
    )

    print(
        "\nEstado final:",
        pdata_final.get("player_state")
    )


asyncio.run(main())