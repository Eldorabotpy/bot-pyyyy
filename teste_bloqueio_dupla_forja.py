import asyncio

from modules import player_manager
from modules.crafting_engine import start_craft


USER_ID = "69fa8f60080408b128764720"
RECIPE_ID = "craft_martelo_ferreiro_t1"
TOOL_UID = "martelo_ferreiro_t1"


async def main():

    print("\n==============================")
    print("🧪 TESTE DUPLA FORJA")
    print("==============================")

    # -----------------------------------------
    # ESTADO INICIAL
    # -----------------------------------------

    pdata = await player_manager.get_player_data(
        USER_ID
    )

    ferramenta = (
        pdata.get("inventory", {})
        .get(TOOL_UID, {})
    )

    dur_antes = list(
        ferramenta.get(
            "durability",
            []
        )
    )

    print(
        "Durabilidade inicial:",
        dur_antes
    )

    # -----------------------------------------
    # PRIMEIRA FORJA
    # -----------------------------------------

    print("\n--- PRIMEIRA TENTATIVA ---")

    resultado_1 = await start_craft(
        USER_ID,
        RECIPE_ID
    )

    print(
        "Resultado:",
        resultado_1
    )

    pdata = await player_manager.get_player_data(
        USER_ID
    )

    ferramenta = (
        pdata.get("inventory", {})
        .get(TOOL_UID, {})
    )

    dur_apos_primeira = list(
        ferramenta.get(
            "durability",
            []
        )
    )

    print(
        "Durabilidade após primeira:",
        dur_apos_primeira
    )

    # -----------------------------------------
    # SEGUNDA FORJA IMEDIATA
    # -----------------------------------------

    print("\n--- SEGUNDA TENTATIVA ---")

    resultado_2 = await start_craft(
        USER_ID,
        RECIPE_ID
    )

    print(
        "Resultado:",
        resultado_2
    )

    pdata = await player_manager.get_player_data(
        USER_ID
    )

    ferramenta = (
        pdata.get("inventory", {})
        .get(TOOL_UID, {})
    )

    dur_apos_segunda = list(
        ferramenta.get(
            "durability",
            []
        )
    )

    print(
        "Durabilidade após segunda:",
        dur_apos_segunda
    )

    # -----------------------------------------
    # RESULTADO
    # -----------------------------------------

    print("\n==============================")
    print("📋 RESULTADO")
    print("==============================")

    if (
        len(dur_antes) >= 1
        and len(dur_apos_primeira) >= 1
        and dur_apos_primeira[0]
        == dur_antes[0] - 1
    ):
        print(
            "✅ Primeira forja consumiu 1 "
            "de durabilidade."
        )
    else:
        print(
            "⚠️ Verifique o consumo da "
            "primeira forja."
        )

    if (
        dur_apos_segunda
        == dur_apos_primeira
    ):
        print(
            "✅ Segunda tentativa NÃO "
            "consumiu durabilidade."
        )
    else:
        print(
            "❌ ERRO: segunda tentativa "
            "consumiu durabilidade."
        )

    if isinstance(resultado_2, str):
        print(
            "✅ Segunda forja foi bloqueada."
        )
    else:
        print(
            "❌ ERRO: segunda forja foi iniciada."
        )

    print(
        "\nEstado atual:",
        pdata.get("player_state")
    )


asyncio.run(main())