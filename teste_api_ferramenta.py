from flask import Flask

from modules.webapp_api import webapp_bp


USER_ID = "69fa8f60080408b128764720"


app = Flask(__name__)
app.register_blueprint(webapp_bp)


with app.test_client() as client:

    resposta = client.get(
        f"/perfil/{USER_ID}"
    )

    print(
        "STATUS HTTP:",
        resposta.status_code
    )

    dados = resposta.get_json()

    if not dados:
        print("❌ API não retornou JSON.")
        raise SystemExit

    if dados.get("erro"):
        print(
            "❌ ERRO:",
            dados["erro"]
        )
        raise SystemExit

    martelos = [
        item
        for item in dados.get(
            "inventario",
            []
        )
        if item.get("base_id")
        == "martelo_ferreiro_t1"
    ]

    print(
        "\nMartelos encontrados:",
        len(martelos)
    )

    for numero, item in enumerate(
        martelos,
        1
    ):

        print(
            "\n=============================="
        )

        print(
            f"🔨 MARTELO {numero}"
        )

        print(
            "=============================="
        )

        campos = [
            "id",
            "base_id",
            "nome",
            "tipo",
            "raridade",
            "refino",
            "upgrade_level",
            "tool_type",
            "tier",
            "tool_tier",
            "durability",
            "enchantments",
            "stats",
        ]

        for campo in campos:
            print(
                f"{campo}:",
                item.get(campo)
            )