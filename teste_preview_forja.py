import asyncio
import copy

from modules import player_manager
from modules import profession_engine
from modules.crafting_engine import preview_craft


USER_ID = "69fa8f60080408b128764720"
RECIPE_ID = "craft_martelo_ferreiro_t1"
PROFISSAO = "ferreiro"


async def main():

    pdata = await player_manager.get_player_data(
        USER_ID
    )

    if not pdata:
        print("❌ Jogador não encontrado.")
        return

    # -------------------------------------------------
    # Ferramenta equipada ANTES do preview
    # -------------------------------------------------

    tool_uid, tool_inst, tool_info = (
        profession_engine
        .get_equipped_tool_for_speed(
            pdata,
            PROFISSAO
        )
    )

    durabilidade_antes = copy.deepcopy(
        tool_inst.get("durability")
        if isinstance(tool_inst, dict)
        else None
    )

    print("\n==============================")
    print("🔨 FERRAMENTA EQUIPADA")
    print("==============================")

    print("UID:", tool_uid)

    if isinstance(tool_inst, dict):
        print(
            "Base ID:",
            tool_inst.get("base_id")
        )

        print(
            "Raridade:",
            tool_inst.get("rarity")
        )

        print(
            "Refino:",
            tool_inst.get("upgrade_level")
        )

        print(
            "Encantamentos:",
            tool_inst.get("enchantments")
        )

    print(
        "Durabilidade antes:",
        durabilidade_antes
    )

    # -------------------------------------------------
    # Preview
    # -------------------------------------------------

    resultado = await preview_craft(
        RECIPE_ID,
        pdata
    )

    print("\n==============================")
    print("📜 PREVIEW DA FORJA")
    print("==============================")

    if not resultado:
        print("❌ Preview retornou vazio.")
        return

    campos = [
        "can_craft",
        "profession",
        "profession_level",
        "required_profession_level",
        "profession_ok",
        "materials_ok",
        "tool_ok",
        "duration_seconds",
    ]

    for campo in campos:
        print(
            f"{campo}:",
            resultado.get(campo)
        )

    print("\n==============================")
    print("⚡ VELOCIDADE")
    print("==============================")

    work_speed = (
        resultado.get("work_speed")
        or {}
    )

    for chave, valor in work_speed.items():
        print(
            f"{chave}: {valor}"
        )

    print("\n==============================")
    print("🍀 QUALIDADE")
    print("==============================")

    craft_quality = (
        resultado.get("craft_quality")
        or {}
    )

    for chave, valor in craft_quality.items():
        print(
            f"{chave}: {valor}"
        )

    print("\n==============================")
    print("🔨 FERRAMENTA")
    print("==============================")

    tool_preview = (
        resultado.get("tool")
        or {}
    )

    for chave, valor in tool_preview.items():
        print(
            f"{chave}: {valor}"
        )

    # -------------------------------------------------
    # Confere se preview consumiu durabilidade
    # -------------------------------------------------

    durabilidade_depois = copy.deepcopy(
        tool_inst.get("durability")
        if isinstance(tool_inst, dict)
        else None
    )

    print("\n==============================")
    print("🛡️ TESTE DE DURABILIDADE")
    print("==============================")

    print(
        "Antes:",
        durabilidade_antes
    )

    print(
        "Depois:",
        durabilidade_depois
    )

    if (
        durabilidade_antes
        == durabilidade_depois
    ):
        print(
            "✅ Preview NÃO gastou durabilidade."
        )
    else:
        print(
            "❌ ERRO: preview alterou a durabilidade."
        )


asyncio.run(main())