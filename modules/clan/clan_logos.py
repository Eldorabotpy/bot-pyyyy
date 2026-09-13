# ============================================================
# 🛡️ MUNDO DE ELDORA - CATÁLOGO DE LOGOS DOS CLÃS
# ============================================================

LOGO_BASE_URL = (
    "https://raw.githubusercontent.com/"
    "Eldorabotpy/static-img/main/assets/logo_clans"
)


LOGO_PADRAO_ID = "logo_1"


CLAN_LOGOS = {

    "logo_1": {
        "nome": "Brasão Padrão",
        "arquivo": "logo_1.png",
    },
    "logo_2": {
            "nome": "Logo 2",
            "arquivo": "logo_2.png",
        },
    "logo_3": {
                "nome": "Logo 3",
                "arquivo": "logo_3.png",
            },   
    "logo_4": {
                "nome": "Logo 4",
                "arquivo": "logo_4.png",
            },  
    "logo_5": {
                "nome": "Logo 5",
                "arquivo": "logo_5.png",
            }, 
    "logo_6": {
                "nome": "Logo 6",
                "arquivo": "logo_6.png",
            },  
    "logo_7": {
                "nome": "Logo 7",
                "arquivo": "logo_7.png",
            }, 
    "logo_8": {
                "nome": "Logo 8",
                "arquivo": "logo_8.png",
            },  
    "logo_9": {
                "nome": "Logo 9",
                "arquivo": "logo_9.png",
            },
    "logo_10": {
                "nome": "Logo 10",
                "arquivo": "logo_10.png",
            },
    "logo_11": {
                "nome": "Logo 11",
                "arquivo": "logo_11.png",
            },
    "logo_12": {
                "nome": "Logo 12",
                "arquivo": "logo_12.png",
            },                               
    # Adicione novas logos seguindo este padrão:
    #
    # "dragao_vermelho": {
    #     "nome": "Dragão Vermelho",
    #     "arquivo": "dragao_vermelho.png",
    # },
}


def logo_valida(logo_id):
    return str(logo_id or "") in CLAN_LOGOS


def obter_logo_id_valido(logo_id):
    logo_id = str(logo_id or "").strip()

    if logo_id in CLAN_LOGOS:
        return logo_id

    return LOGO_PADRAO_ID


def obter_logo_url(logo_id):
    logo_id = obter_logo_id_valido(logo_id)
    arquivo = CLAN_LOGOS[logo_id]["arquivo"]

    return f"{LOGO_BASE_URL}/{arquivo}"


def listar_logos_publicas():
    resultado = []

    for logo_id, dados in CLAN_LOGOS.items():
        resultado.append({
            "id": logo_id,
            "nome": dados["nome"],
            "url": obter_logo_url(logo_id),
        })

    return resultado