"""Novidades publicadas na Central de Eldora.

Para anunciar uma atualização, adicione um item com um ID novo e estável.
Jogadores recebem cada ID uma vez por personagem.
"""

CENTRAL_ELDORA_NEWS = (
    {
        "id": "central-canais-oficiais-2026-10",
        "titulo": "Novidades na Central de Eldora",
        "mensagem": "Confira os novos destaques e os acessos oficiais ao site e à comunidade do Telegram.",
        "aba": "atualizacoes",
    },
)


def obter_novidades_nao_lidas(ids_lidos=()):
    lidas = set(ids_lidos or [])
    return [item for item in CENTRAL_ELDORA_NEWS if item["id"] not in lidas]

