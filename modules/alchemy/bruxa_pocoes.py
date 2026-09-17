from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any

from modules.game_data.items import ITEMS_DATA


# ==========================================================
# 🧪 RECEITAS DA BRUXA
# ==========================================================

RECEITAS_BRUXA = {

    # ------------------------------------------------------
    # PRIMEIRA LEVA — DROPS DOS MOBS INICIAIS
    # ------------------------------------------------------

    "pocao_cura_leve": {
        "display_name": "Poção de Cura P",
        "emoji": "❤️",
        "tier": 1,
        "grupo": "Receitas Iniciais",
        "result_base_id": "pocao_cura_leve",
        "quantity": 1,
        "inputs": {
            "geleia_slime": 2,
            "raiz_da_fortuna": 1,
            "essencia_purificadora": 1,
        },
    },

    "pocao_mana_leve": {
        "display_name": "Poção de Mana P",
        "emoji": "💧",
        "tier": 1,
        "grupo": "Receitas Iniciais",
        "result_base_id": "pocao_mana_leve",
        "quantity": 1,
        "inputs": {
            "cristal_mana_bruto": 2,
            "essencia_purificadora": 1,
        },
    },

    "elixir_xp_dobrado_10m": {
        "display_name": "Elixir de Experiência",
        "emoji": "✨",
        "tier": 1,
        "grupo": "Receitas Iniciais",
        "result_base_id": "elixir_xp_dobrado_10m",
        "quantity": 1,
        "inputs": {
            "folha_sombria": 2,
            "essencia_purificadora": 2,
            "po_de_iniciativa": 1,
        },
    },


    # ------------------------------------------------------
    # SEGUNDA LEVA — REAGENTES DA FLORESTA
    # ------------------------------------------------------

    "pocao_cura_media": {
        "display_name": "Poção de Cura M",
        "emoji": "❤️‍🩹",
        "tier": 2,
        "grupo": "Receitas da Floresta",
        "result_base_id": "pocao_cura_media",
        "quantity": 1,
        "inputs": {
            "frasco_com_agua": 1,
            "raiz_sangrenta": 3,
            "esporo_de_cogumelo": 2,
        },
    },

    "pocao_mana_media": {
        "display_name": "Poção de Mana M",
        "emoji": "🔵",
        "tier": 2,
        "grupo": "Receitas da Floresta",
        "result_base_id": "pocao_mana_media",
        "quantity": 1,
        "inputs": {
            "frasco_com_agua": 1,
            "cogumelo_azul": 3,
            "flor_da_lua": 2,
        },
    },

    "elixir_xp_dobrado_30m": {
        "display_name": "Elixir Superior de Experiência",
        "emoji": "🌟",
        "tier": 2,
        "grupo": "Receitas da Floresta",
        "result_base_id": "elixir_xp_dobrado_30m",
        "quantity": 1,
        "inputs": {
            "frasco_com_agua": 1,
            "flor_da_lua": 3,
            "cogumelo_azul": 2,
            "esporo_de_cogumelo": 3,
        },
    },
}


# ==========================================================
# 📦 INVENTÁRIO — COMPATÍVEL COM STACK ANTIGO E NOVO
# ==========================================================

def quantidade_item(
    player_data: dict,
    item_id: str,
) -> int:

    inventario = (
        player_data.get("inventory", {})
        or {}
    )

    if not isinstance(inventario, dict):
        return 0

    total = 0

    for chave, item in inventario.items():

        if isinstance(item, dict):

            base_id = item.get(
                "base_id",
                chave,
            )

            if base_id != item_id:
                continue

            try:
                total += int(
                    item.get("quantity", 1)
                    or 0
                )
            except Exception:
                pass

        elif chave == item_id:

            try:
                total += int(item or 0)
            except Exception:
                pass

    return max(0, total)


def _consumir_item(
    player_data: dict,
    item_id: str,
    quantidade: int,
) -> bool:

    quantidade = int(quantidade or 0)

    if quantidade <= 0:
        return True

    if quantidade_item(
        player_data,
        item_id,
    ) < quantidade:
        return False

    inventario = (
        player_data.get("inventory", {})
        or {}
    )

    restante = quantidade

    for chave in list(inventario.keys()):

        if restante <= 0:
            break

        item = inventario.get(chave)

        if isinstance(item, dict):

            base_id = item.get(
                "base_id",
                chave,
            )

            if base_id != item_id:
                continue

            qtd = int(
                item.get("quantity", 1)
                or 0
            )

            retirar = min(
                qtd,
                restante,
            )

            nova_qtd = qtd - retirar
            restante -= retirar

            if nova_qtd <= 0:
                inventario.pop(
                    chave,
                    None,
                )
            else:
                item["quantity"] = nova_qtd

        else:

            if chave != item_id:
                continue

            qtd = int(item or 0)

            retirar = min(
                qtd,
                restante,
            )

            nova_qtd = qtd - retirar
            restante -= retirar

            if nova_qtd <= 0:
                inventario.pop(
                    chave,
                    None,
                )
            else:
                inventario[chave] = nova_qtd

    player_data["inventory"] = inventario

    return restante <= 0


def _adicionar_item(
    player_data: dict,
    item_id: str,
    quantidade: int = 1,
):

    inventario = (
        player_data.get("inventory", {})
        or {}
    )

    quantidade = max(
        1,
        int(quantidade or 1),
    )

    # Tenta reaproveitar stack já existente.
    for chave, item in inventario.items():

        if isinstance(item, dict):

            base_id = item.get(
                "base_id",
                chave,
            )

            if base_id == item_id:
                item["quantity"] = (
                    int(
                        item.get(
                            "quantity",
                            1,
                        )
                        or 1
                    )
                    + quantidade
                )

                player_data["inventory"] = inventario
                return

        elif chave == item_id:

            inventario[chave] = (
                int(item or 0)
                + quantidade
            )

            player_data["inventory"] = inventario
            return

    # Novo stack no formato usado pelo Web App.
    inventario[item_id] = {
        "base_id": item_id,
        "quantity": quantidade,
    }

    player_data["inventory"] = inventario


# ==========================================================
# 📜 LISTAGEM PARA O FRONTEND
# ==========================================================

def listar_receitas(
    player_data: dict,
) -> list:

    resposta = []

    for receita_id, receita in (
        RECEITAS_BRUXA.items()
    ):

        ingredientes = []
        pode_criar = True

        for item_id, necessario in (
            receita["inputs"].items()
        ):

            possui = quantidade_item(
                player_data,
                item_id,
            )

            info = (
                ITEMS_DATA.get(
                    item_id,
                    {},
                )
                or {}
            )

            if possui < necessario:
                pode_criar = False

            ingredientes.append({
                "item_id": item_id,

                "nome": info.get(
                    "display_name",
                    item_id
                    .replace("_", " ")
                    .title(),
                ),

                "emoji": info.get(
                    "emoji",
                    "📦",
                ),

                "possui": possui,
                "necessario": necessario,
            })

        resposta.append({
            "receita_id": receita_id,
            "nome": receita["display_name"],
            "emoji": receita.get(
                "emoji",
                "🧪",
            ),
            "tier": receita.get(
                "tier",
                1,
            ),
            "grupo": receita.get(
                "grupo",
                "Alquimia",
            ),
            "resultado": receita[
                "result_base_id"
            ],
            "quantidade": receita.get(
                "quantity",
                1,
            ),
            "ingredientes": ingredientes,
            "pode_criar": pode_criar,
        })

    return resposta


# ==========================================================
# ⚗️ FABRICAÇÃO
# ==========================================================

def fabricar(
    player_data: dict,
    receita_id: str,
) -> Dict[str, Any]:

    receita = RECEITAS_BRUXA.get(
        receita_id
    )

    if not receita:
        return {
            "success": False,
            "error": "Receita desconhecida.",
        }

    # Primeiro valida tudo.
    faltando = []

    for item_id, necessario in (
        receita["inputs"].items()
    ):

        possui = quantidade_item(
            player_data,
            item_id,
        )

        if possui < necessario:

            info = (
                ITEMS_DATA.get(
                    item_id,
                    {},
                )
                or {}
            )

            faltando.append(
                info.get(
                    "display_name",
                    item_id,
                )
            )

    if faltando:

        return {
            "success": False,
            "error": (
                "Ingredientes insuficientes: "
                + ", ".join(faltando)
            ),
        }

    # Só consome depois de validar TODOS.
    for item_id, necessario in (
        receita["inputs"].items()
    ):

        if not _consumir_item(
            player_data,
            item_id,
            necessario,
        ):
            return {
                "success": False,
                "error": (
                    "Falha ao consumir "
                    f"{item_id}."
                ),
            }

    resultado_id = receita[
        "result_base_id"
    ]

    quantidade_resultado = receita.get(
        "quantity",
        1,
    )

    _adicionar_item(
        player_data,
        resultado_id,
        quantidade_resultado,
    )

    return {
        "success": True,
        "receita_id": receita_id,
        "resultado": resultado_id,
        "quantidade": quantidade_resultado,
        "nome": receita[
            "display_name"
        ],
    }


# ==========================================================
# ✨ MULTIPLICADOR TEMPORÁRIO DE XP
# ==========================================================

def calcular_xp_com_bonus(
    player_data: dict,
    xp_base: int,
):

    xp_base = max(
        0,
        int(xp_base or 0),
    )

    boost = (
        player_data.get(
            "xp_boost"
        )
        or {}
    )

    if not isinstance(boost, dict):
        return xp_base, False

    expires_at = boost.get(
        "expires_at"
    )

    if not expires_at:
        return xp_base, False

    try:

        expiracao = datetime.fromisoformat(
            str(expires_at).replace(
                "Z",
                "+00:00",
            )
        )

        if expiracao.tzinfo is None:
            expiracao = expiracao.replace(
                tzinfo=timezone.utc
            )

    except Exception:
        return xp_base, False

    agora = datetime.now(
        timezone.utc
    )

    if agora >= expiracao:
        return xp_base, False

    try:
        multiplicador = float(
            boost.get(
                "multiplier",
                1.0,
            )
        )
    except Exception:
        multiplicador = 1.0

    multiplicador = max(
        1.0,
        multiplicador,
    )

    xp_final = int(
        xp_base
        * multiplicador
    )

    return xp_final, True