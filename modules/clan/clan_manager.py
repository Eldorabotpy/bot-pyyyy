# ============================================================
# 🛡️ MUNDO DE ELDORA - GERENCIADOR DE CLÃS
# ============================================================

from __future__ import annotations

import asyncio
import inspect
import re
import unicodedata

from datetime import datetime, timezone, timedelta
from typing import Any, Optional, Union

from bson import ObjectId
from pymongo.errors import DuplicateKeyError, PyMongoError

from modules.player.core import (
    db,
    users_collection,
    clear_player_cache,
)

from .clan_registry import (
    CARGO_LIDER,
    CARGO_VICE_LIDER,
    CARGO_OFICIAL,
    CARGO_MEMBRO,

    CLAN_NIVEL_INICIAL,

    PERMISSOES_CARGO_VALIDAS,

    PERMISSAO_CONVIDAR,
    PERMISSAO_ACEITAR_SOLICITACOES,
    PERMISSAO_GERENCIAR_CARGOS,
    PERMISSAO_EXPULSAR,

    PERMISSAO_EDITAR_CLA,
    PERMISSAO_ALTERAR_BRASAO,
    PERMISSAO_MELHORAR_CLA,
    PERMISSAO_GERENCIAR_TESOURO,

    obter_capacidade,
    obter_proximo_nivel,
    obter_custo_evolucao,
    obter_beneficios_nivel,
    obter_dias_tesouraria,

    obter_cargos_padrao,
    obter_config_cargo_padrao,
    obter_limite_cargos_personalizados,
    normalizar_permissoes_cargo,
)

from .clan_logos import (
    LOGO_PADRAO_ID,
    logo_valida,
    obter_logo_id_valido,
    obter_logo_url,
)

clans_collection = db["clans"]
clan_invites_collection = db["clan_invites"]
clan_requests_collection = db["clan_requests"]
# ============================================================
# 🏰 CUSTO PARA FUNDAÇÃO DE CLÃ
# ============================================================

CLAN_CUSTO_CRIACAO_OURO = 5000
# ============================================================
# 💼 LICENÇA DA TESOURARIA
# ============================================================

TESOURARIA_CUSTO_GEMAS = 100

# ============================================================
# 🔧 HELPERS
# ============================================================

def _agora():
    return datetime.now(timezone.utc)

def _normalizar_datetime_utc(
    valor,
):
    if not isinstance(
        valor,
        datetime,
    ):
        return None

    if valor.tzinfo is None:
        return valor.replace(
            tzinfo=timezone.utc
        )

    return valor.astimezone(
        timezone.utc
    )


def obter_estado_tesouraria(
    cla,
):
    agora = _agora()
    try:
        nivel_cla = int(
            cla.get(
                "nivel",
                CLAN_NIVEL_INICIAL,
            )
            or CLAN_NIVEL_INICIAL
        )

    except (
        TypeError,
        ValueError,
    ):
        nivel_cla = (
            CLAN_NIVEL_INICIAL
        )


    duracao_dias = int(
        obter_dias_tesouraria(
            nivel_cla
        )
    )    

    tesouraria = (
        cla.get(
            "tesouraria",
            {},
        )
        or {}
    )

    expira_em = (
        _normalizar_datetime_utc(
            tesouraria.get(
                "expira_em"
            )
        )
    )

    ativa = bool(
        expira_em
        and
        expira_em > agora
    )

    segundos_restantes = 0

    if ativa:
        segundos_restantes = max(
            0,
            int(
                (
                    expira_em -
                    agora
                ).total_seconds()
            ),
        )

    dias_restantes = 0

    if segundos_restantes > 0:
        dias_restantes = (
            segundos_restantes
            + 86399
        ) // 86400


    return {
        "ativa":
            ativa,

        "custo_gemas":
            TESOURARIA_CUSTO_GEMAS,

        "duracao_dias":
            duracao_dias,

        "ativada_em":
            _normalizar_datetime_utc(
                tesouraria.get(
                    "ativada_em"
                )
            ),

        "expira_em":
            expira_em,

        "dias_restantes":
            int(
                dias_restantes
            ),

        "ciclo":
            int(
                tesouraria.get(
                    "ciclo",
                    0,
                )
                or 0
            ),
    }

def _object_id(valor):
    if isinstance(valor, ObjectId):
        return valor

    if valor is None:
        return None

    texto = str(valor).strip()

    if not ObjectId.is_valid(texto):
        return None

    return ObjectId(texto)


def _limpar_cache(player_id):
    """
    Limpa o cache aceitando clear_player_cache
    tanto síncrona quanto assíncrona.
    """

    if not player_id:
        return

    valores = (
        player_id,
        str(player_id),
    )

    for valor in valores:
        try:
            resultado = clear_player_cache(
                valor
            )

            if not inspect.isawaitable(
                resultado
            ):
                continue

            try:
                loop = asyncio.get_running_loop()

            except RuntimeError:
                asyncio.run(resultado)

            else:
                loop.create_task(resultado)

        except Exception as erro:
            print(
                "⚠️ [CLÃ CACHE] "
                f"Não foi possível limpar "
                f"{valor}: {erro}"
            )


def _normalizar_busca(texto):
    texto = " ".join(str(texto or "").strip().split())
    texto = unicodedata.normalize("NFKD", texto)

    texto = "".join(
        c for c in texto
        if not unicodedata.combining(c)
    )

    return texto.casefold()


def _normalizar_nome(nome):
    return " ".join(str(nome or "").strip().split())


def _normalizar_tag(tag):
    tag = unicodedata.normalize("NFKD", str(tag or ""))

    tag = "".join(
        c for c in tag
        if not unicodedata.combining(c)
    )

    tag = re.sub(r"\s+", "", tag).upper()

    return tag

def _normalizar_id_cargo(nome):
    """
    Transforma o nome visual do cargo em um ID
    estável para salvar no MongoDB.

    Exemplo:
    "Capitão de Guerra" -> "capitao_de_guerra"
    """

    texto = str(
        nome or ""
    ).strip().lower()

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    texto = "".join(
        c for c in texto
        if not unicodedata.combining(c)
    )

    texto = re.sub(
        r"[^a-z0-9]+",
        "_",
        texto,
    )

    texto = texto.strip("_")

    return texto

def _json_seguro(valor: Any):
    if isinstance(valor, ObjectId):
        return str(valor)

    if isinstance(valor, datetime):
        return valor.isoformat()

    if isinstance(valor, dict):
        return {
            chave: _json_seguro(item)
            for chave, item in valor.items()
        }

    if isinstance(valor, list):
        return [
            _json_seguro(item)
            for item in valor
        ]

    return valor


def serializar_cla(cla):
    if not cla:
        return None


    cla = _garantir_cargos_cla(
        cla
    )


    dados = _json_seguro(
        cla
    )

    # ========================================================
    # 💼 ESTADO DA TESOURARIA
    # ========================================================

    dados["tesouraria"] = (
        _json_seguro(
            obter_estado_tesouraria(
                cla
            )
        )
    )
    # ========================================================
    # 🎨 LOGO DO CLÃ
    # ========================================================

    logo_id = obter_logo_id_valido(
        dados.get("logo_id")
    )

    dados["logo_id"] = logo_id
    dados["logo_url"] = obter_logo_url(
        logo_id
    )

    # ========================================================
    # 📈 PRÓXIMA EVOLUÇÃO
    # ========================================================

    nivel_atual = int(
        dados.get(
            "nivel",
            CLAN_NIVEL_INICIAL,
        ) or CLAN_NIVEL_INICIAL
    )

    # ========================================================
    # 🎁 BENEFÍCIOS DO NÍVEL ATUAL
    # ========================================================

    beneficios_atuais = (
        obter_beneficios_nivel(
            nivel_atual
        )
    )


    dados["beneficios_nivel"] = (
        _json_seguro(
            beneficios_atuais
        )
    )
    
    # ========================================================
    # 🎖️ INFORMAÇÕES DOS CARGOS
    # ========================================================

    cargos_lista = (
        listar_cargos_cla(
            cla
        )
    )


    dados["cargos_lista"] = (
        _json_seguro(
            cargos_lista
        )
    )


    dados[
        "limite_cargos_personalizados"
    ] = (
        obter_limite_cargos_personalizados(
            nivel_atual
        )
    )


    dados[
        "cargos_personalizados_total"
    ] = sum(
        1

        for cargo
        in cargos_lista

        if not cargo.get(
            "sistema",
            False,
        )
    )

    xp_atual = int(
        dados.get("xp", 0) or 0
    )

    tesouro = (
        dados.get("tesouro", {})
        or {}
    )

    ouro_atual = int(
        tesouro.get("ouro", 0) or 0
    )

    capacidade_atual = int(
        dados.get(
            "capacidade_membros",
            obter_capacidade(nivel_atual),
        ) or obter_capacidade(nivel_atual)
    )

    proximo_nivel = obter_proximo_nivel(
        nivel_atual
    )

    if proximo_nivel:
        custo = (
            obter_custo_evolucao(
                nivel_atual
            )
            or {}
        )
        beneficios_proximo_nivel = (
            obter_beneficios_nivel(
                proximo_nivel
            )
        )


        limite_cargos_atual = (
            obter_limite_cargos_personalizados(
                nivel_atual
            )
        )


        proximo_limite_cargos = (
            obter_limite_cargos_personalizados(
                proximo_nivel
            )
        )

        xp_necessario = int(
            custo.get("xp", 0) or 0
        )

        ouro_necessario = int(
            custo.get("ouro", 0) or 0
        )

        proxima_capacidade = int(
            obter_capacidade(
                proximo_nivel
            )
        )

        xp_faltante = max(
            0,
            xp_necessario - xp_atual,
        )

        ouro_faltante = max(
            0,
            ouro_necessario - ouro_atual,
        )

        dados["nivel_maximo"] = False

        dados["proxima_melhoria"] = {
            "nivel": int(
                proximo_nivel
            ),

            "xp_atual": xp_atual,
            "xp_necessario": xp_necessario,
            "xp_faltante": xp_faltante,

            "ouro_atual": ouro_atual,
            "ouro_necessario": ouro_necessario,
            "ouro_faltante": ouro_faltante,

            "capacidade_atual":
                capacidade_atual,

            "proxima_capacidade":
                proxima_capacidade,

            "limite_cargos_atual":
                int(
                    limite_cargos_atual
                ),

            "proximo_limite_cargos":
                int(
                    proximo_limite_cargos
                ),

            "beneficios_atuais":
                _json_seguro(
                    beneficios_atuais
                ),

            "beneficios_proximo_nivel":
                _json_seguro(
                    beneficios_proximo_nivel
                ),

            "pode_melhorar": (
                xp_atual >= xp_necessario
                and
                ouro_atual >= ouro_necessario
            ),
        }

    else:
        dados["nivel_maximo"] = True
        dados["proxima_melhoria"] = None

    return dados


def _validar_nome(nome):
    nome = _normalizar_nome(nome)

    if len(nome) < 3:
        return False, "O nome precisa ter pelo menos 3 caracteres.", ""

    if len(nome) > 30:
        return False, "O nome pode ter no máximo 30 caracteres.", ""

    if not all(
        c.isalnum() or c in " -_'"
        for c in nome
    ):
        return False, "O nome possui caracteres inválidos.", ""

    return True, "", nome


def _validar_tag(tag):
    tag = _normalizar_tag(tag)

    if not re.fullmatch(r"[A-Z0-9]{2,5}", tag):
        return False, "A tag deve ter de 2 a 5 letras ou números.", ""

    return True, "", tag


def _obter_membro(cla, player_id):
    for membro in cla.get("membros", []):
        if membro.get("user_id") == player_id:
            return membro

    return None

def _cargo_no_cla(cla, player_id):
    membro = _obter_membro(cla, player_id)

    if not membro:
        return None

    return membro.get("cargo")

# ============================================================
# 🎖️ SISTEMA MODERNO DE CARGOS
# ============================================================

CLAN_SCHEMA_VERSION = 2

def _garantir_capacidade_cla(
    cla,
):
    """
    Mantém a capacidade de membros sincronizada
    com o nível oficial definido no clan_registry.

    Corrige automaticamente clãs antigos que ainda
    possuam capacidade de uma regra anterior.
    """

    if not isinstance(
        cla,
        dict,
    ):
        return cla


    clan_id = cla.get(
        "_id"
    )

    if not clan_id:
        return cla


    try:
        nivel = int(
            cla.get(
                "nivel",
                CLAN_NIVEL_INICIAL,
            )
            or CLAN_NIVEL_INICIAL
        )

    except (
        TypeError,
        ValueError,
    ):
        nivel = (
            CLAN_NIVEL_INICIAL
        )


    capacidade_oficial = int(
        obter_capacidade(
            nivel
        )
    )


    try:
        capacidade_salva = int(
            cla.get(
                "capacidade_membros",
                0,
            )
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):
        capacidade_salva = 0


    if (
        capacidade_salva
        ==
        capacidade_oficial
    ):
        return cla


    # Atualiza imediatamente o objeto usado
    # pela requisição atual.
    cla[
        "capacidade_membros"
    ] = capacidade_oficial


    try:

        resultado = (
            clans_collection.update_one(
                {
                    "_id":
                        clan_id,
                },
                {
                    "$set": {
                        "capacidade_membros":
                            capacidade_oficial,

                        "atualizado_em":
                            _agora(),
                    }
                },
            )
        )


        if (
            resultado.modified_count
            == 1
        ):
            print(
                "🛠️ [CLÃ] "
                "Capacidade corrigida: "
                f"{capacidade_salva} -> "
                f"{capacidade_oficial} "
                f"(Nv.{nivel})"
            )


    except Exception as erro:

        print(
            "⚠️ [CLÃ CAPACIDADE] "
            "Não foi possível sincronizar "
            f"o clã {clan_id}: {erro}"
        )


    return cla

def _garantir_cargos_cla(
    cla,
):
    """
    Garante que o clã possua o catálogo moderno
    de cargos.

    Clãs antigos recebem automaticamente os
    quatro cargos padrão sem precisar de
    migração manual no MongoDB.
    """

    if not isinstance(
        cla,
        dict,
    ):
        return cla

    clan_id = cla.get("_id")

    if not clan_id:
        return cla


    # ========================================================
    # 👥 SINCRONIZA CAPACIDADE PELO NÍVEL
    # ========================================================

    cla = _garantir_capacidade_cla(
        cla
    )


    cargos_atuais = cla.get(
        "cargos"
    )


    if not isinstance(
        cargos_atuais,
        dict,
    ):
        cargos_atuais = {}


    cargos_finais = dict(
        cargos_atuais
    )


    cargos_padrao = (
        obter_cargos_padrao()
    )


    alterou = False


    # ========================================================
    # GARANTE OS 4 CARGOS DO SISTEMA
    # ========================================================

    for (
        cargo_id,
        configuracao
    ) in cargos_padrao.items():

        cargo_existente = (
            cargos_finais.get(
                cargo_id
            )
        )


        if not isinstance(
            cargo_existente,
            dict,
        ):

            cargos_finais[
                cargo_id
            ] = configuracao

            alterou = True


    # ========================================================
    # ATUALIZA O OBJETO EM MEMÓRIA
    # ========================================================

    cla["cargos"] = (
        cargos_finais
    )


    versao_atual = int(
        cla.get(
            "schema_version",
            1,
        ) or 1
    )


    if (
        versao_atual
        < CLAN_SCHEMA_VERSION
    ):
        cla[
            "schema_version"
        ] = CLAN_SCHEMA_VERSION

        alterou = True


    # ========================================================
    # SALVA MIGRAÇÃO AUTOMÁTICA
    # ========================================================

    if alterou:

        try:

            clans_collection.update_one(
                {
                    "_id":
                        clan_id,
                },
                {
                    "$set": {

                        "cargos":
                            cargos_finais,

                        "schema_version":
                            CLAN_SCHEMA_VERSION,

                        "atualizado_em":
                            _agora(),
                    }
                },
            )

            print(
                "🎖️ [CLÃ] "
                f"Estrutura de cargos atualizada: "
                f"{clan_id}"
            )

        except Exception as erro:

            # Uma falha de migração não deve
            # impedir o clã de abrir.
            print(
                "⚠️ [CLÃ CARGOS] "
                f"Falha ao preparar cargos "
                f"do clã {clan_id}: {erro}"
            )


    return cla


def obter_config_cargo_cla(
    cla,
    cargo_id,
):
    """
    Retorna a configuração real de um cargo
    pertencente ao clã.

    Funciona tanto para cargos padrão quanto
    para cargos personalizados.
    """

    cargo_id = str(
        cargo_id or ""
    ).strip()


    if not cargo_id:
        return None


    cla = _garantir_cargos_cla(
        cla
    )


    cargos = (
        cla.get(
            "cargos",
            {}
        )
        or {}
    )


    configuracao = cargos.get(
        cargo_id
    )


    if isinstance(
        configuracao,
        dict,
    ):
        return configuracao


    # Compatibilidade extra caso algum clã
    # antigo ainda esteja incompleto.
    return obter_config_cargo_padrao(
        cargo_id
    )


def tem_permissao_cla(
    cla,
    cargo_id,
    permissao,
):
    """
    Verifica se determinado cargo possui
    determinada permissão.
    """

    permissao = str(
        permissao or ""
    ).strip()


    if (
        permissao
        not in PERMISSOES_CARGO_VALIDAS
    ):
        return False


    configuracao = (
        obter_config_cargo_cla(
            cla,
            cargo_id,
        )
    )


    if not configuracao:
        return False


    permissoes = (
        configuracao.get(
            "permissoes",
            {}
        )
        or {}
    )


    return bool(
        permissoes.get(
            permissao,
            False,
        )
    )


def obter_ordem_cargo_cla(
    cla,
    cargo_id,
):
    """
    Retorna a posição hierárquica do cargo.
    """

    configuracao = (
        obter_config_cargo_cla(
            cla,
            cargo_id,
        )
    )


    if not configuracao:
        return 0


    try:
        return int(
            configuracao.get(
                "ordem",
                0,
            ) or 0
        )

    except (
        TypeError,
        ValueError,
    ):
        return 0


def cargo_superior_no_cla(
    cla,
    cargo_a,
    cargo_b,
):
    """
    Compara dois cargos usando a hierarquia
    específica daquele clã.
    """

    return (
        obter_ordem_cargo_cla(
            cla,
            cargo_a,
        )
        >
        obter_ordem_cargo_cla(
            cla,
            cargo_b,
        )
    )


def listar_cargos_cla(
    cla,
):
    """
    Retorna cargos padrão e personalizados
    ordenados pela hierarquia.
    """

    cla = _garantir_cargos_cla(
        cla
    )


    cargos = (
        cla.get(
            "cargos",
            {}
        )
        or {}
    )


    resultado = []


    for (
        cargo_id,
        configuracao
    ) in cargos.items():

        if not isinstance(
            configuracao,
            dict,
        ):
            continue


        resultado.append({

            "id":
                str(cargo_id),

            "nome":
                str(
                    configuracao.get(
                        "nome",
                        cargo_id,
                    )
                ),

            "ordem":
                int(
                    configuracao.get(
                        "ordem",
                        0,
                    ) or 0
                ),

            "sistema":
                bool(
                    configuracao.get(
                        "sistema",
                        False,
                    )
                ),

            "protegido":
                bool(
                    configuracao.get(
                        "protegido",
                        False,
                    )
                ),

            "permissoes":
                normalizar_permissoes_cargo(
                    configuracao.get(
                        "permissoes",
                        {},
                    )
                ),
        })


    resultado.sort(
        key=lambda cargo:
            (
                -cargo["ordem"],
                cargo["nome"].casefold(),
            )
    )


    return resultado

# ============================================================
# ➕ CRIAR CARGO PERSONALIZADO
# ============================================================

def criar_cargo_cla(
    user_id,
    nome,
    ordem=50,
    permissoes=None,
):
    player_id = _object_id(
        user_id
    )

    if not player_id:
        return {
            "success": False,
            "error": "ID de jogador inválido.",
        }


    cla = obter_cla_do_jogador(
        player_id
    )

    if not cla:
        return {
            "success": False,
            "error": "Você não pertence a um clã.",
        }


    # Criação/edição da estrutura dos cargos
    # continua sendo poder exclusivo do líder.
    if cla.get(
        "lider_id"
    ) != player_id:

        return {
            "success": False,
            "error": (
                "Somente o líder pode criar "
                "cargos personalizados."
            ),
        }


    nome = " ".join(
        str(nome or "")
        .strip()
        .split()
    )


    if len(nome) < 2:
        return {
            "success": False,
            "error": (
                "O nome do cargo precisa ter "
                "pelo menos 2 caracteres."
            ),
        }


    if len(nome) > 24:
        return {
            "success": False,
            "error": (
                "O nome do cargo pode ter "
                "no máximo 24 caracteres."
            ),
        }


    cargo_id = _normalizar_id_cargo(
        nome
    )


    if not cargo_id:
        return {
            "success": False,
            "error": "Nome de cargo inválido.",
        }


    # Nunca permite sobrescrever cargos internos.
    if cargo_id in {
        CARGO_LIDER,
        CARGO_VICE_LIDER,
        CARGO_OFICIAL,
        CARGO_MEMBRO,
    }:
        return {
            "success": False,
            "error": (
                "Este nome pertence a um "
                "cargo reservado do sistema."
            ),
        }


    cargos = (
        cla.get(
            "cargos",
            {}
        )
        or {}
    )


    if cargo_id in cargos:
        return {
            "success": False,
            "error": (
                "Já existe um cargo com esse nome."
            ),
        }


    # Também impede nomes iguais com
    # capitalização diferente.
    nome_normalizado = (
        nome.casefold()
    )


    for configuracao in cargos.values():

        if not isinstance(
            configuracao,
            dict,
        ):
            continue

        nome_existente = str(
            configuracao.get(
                "nome",
                "",
            )
        ).strip().casefold()

        if (
            nome_existente
            == nome_normalizado
        ):
            return {
                "success": False,
                "error": (
                    "Já existe um cargo "
                    "com esse nome."
                ),
            }


    # ========================================================
    # LIMITE PELO NÍVEL DO CLÃ
    # ========================================================

    limite = (
        obter_limite_cargos_personalizados(
            cla.get(
                "nivel",
                CLAN_NIVEL_INICIAL,
            )
        )
    )


    personalizados = sum(
        1

        for configuracao
        in cargos.values()

        if (
            isinstance(
                configuracao,
                dict,
            )
            and
            not configuracao.get(
                "sistema",
                False,
            )
        )
    )


    if personalizados >= limite:
        return {
            "success": False,
            "error": (
                f"O clã pode possuir no máximo "
                f"{limite} cargos personalizados "
                f"neste nível."
            ),
        }


    # ========================================================
    # HIERARQUIA
    # ========================================================

    try:
        ordem = int(
            ordem
        )

    except (
        TypeError,
        ValueError,
    ):
        ordem = 50


    # Membro = 10
    # Vice = 90
    #
    # Cargos personalizados ficam
    # obrigatoriamente entre eles.
    if ordem < 20 or ordem > 80:
        return {
            "success": False,
            "error": (
                "A hierarquia do cargo precisa "
                "estar entre 20 e 80."
            ),
        }


    permissoes_finais = (
        normalizar_permissoes_cargo(
            permissoes
        )
    )


    novo_cargo = {

        "nome":
            nome,

        "ordem":
            ordem,

        "sistema":
            False,

        "protegido":
            False,

        "permissoes":
            permissoes_finais,

        "criado_em":
            _agora(),

        "criado_por":
            player_id,
    }


    campo = (
        f"cargos.{cargo_id}"
    )


    resultado = (
        clans_collection.update_one(
            {
                "_id":
                    cla["_id"],

                "lider_id":
                    player_id,

                campo: {
                    "$exists":
                        False,
                },
            },
            {
                "$set": {

                    campo:
                        novo_cargo,

                    "atualizado_em":
                        _agora(),
                }
            },
        )
    )


    if (
        resultado.modified_count
        != 1
    ):
        return {
            "success": False,
            "error": (
                "Não foi possível criar "
                "o cargo."
            ),
        }


    membro_lider = (
        _obter_membro(
            cla,
            player_id,
        )
        or {}
    )


    _registrar_atividade(
        clan_id=cla["_id"],

        tipo="cargo",

        mensagem=(
            f"{membro_lider.get('nome', 'O líder')} "
            f"criou o cargo '{nome}'."
        ),

        autor_id=
            player_id,

        autor_nome=
            membro_lider.get(
                "nome",
                "Líder",
            ),

        dados={
            "cargo_id":
                cargo_id,

            "cargo_nome":
                nome,
        },
    )


    return {
        "success": True,

        "message": (
            f"Cargo '{nome}' criado "
            f"com sucesso."
        ),

        "cargo": {
            "id":
                cargo_id,

            **_json_seguro(
                novo_cargo
            ),
        },
    }

# ============================================================
# ✏️ EDITAR CARGO PERSONALIZADO
# ============================================================

def editar_cargo_cla(
    user_id,
    cargo_id,
    nome=None,
    ordem=None,
    permissoes=None,
):
    player_id = _object_id(
        user_id
    )

    if not player_id:
        return {
            "success": False,
            "error": "ID de jogador inválido.",
        }


    cargo_id = str(
        cargo_id or ""
    ).strip()


    if not cargo_id:
        return {
            "success": False,
            "error": "Cargo inválido.",
        }


    cla = obter_cla_do_jogador(
        player_id
    )

    if not cla:
        return {
            "success": False,
            "error": "Você não pertence a um clã.",
        }


    if cla.get(
        "lider_id"
    ) != player_id:

        return {
            "success": False,
            "error": (
                "Somente o líder pode editar "
                "cargos personalizados."
            ),
        }


    cargos = (
        cla.get(
            "cargos",
            {}
        )
        or {}
    )


    cargo_atual = cargos.get(
        cargo_id
    )


    if not isinstance(
        cargo_atual,
        dict,
    ):
        return {
            "success": False,
            "error": "Cargo não encontrado.",
        }


    # Líder / vice / oficial / membro
    # nunca podem ser editados por aqui.
    if (
        cargo_atual.get(
            "sistema",
            False,
        )
        or
        cargo_atual.get(
            "protegido",
            False,
        )
    ):
        return {
            "success": False,
            "error": (
                "Os cargos padrão do sistema "
                "não podem ser alterados."
            ),
        }


    atualizacao = {}


    # ========================================================
    # NOME
    # ========================================================

    if nome is not None:

        nome_novo = " ".join(
            str(nome or "")
            .strip()
            .split()
        )


        if (
            len(nome_novo) < 2
            or
            len(nome_novo) > 24
        ):
            return {
                "success": False,
                "error": (
                    "O nome do cargo precisa ter "
                    "entre 2 e 24 caracteres."
                ),
            }


        for (
            outro_id,
            outra_config
        ) in cargos.items():

            if (
                outro_id == cargo_id
                or
                not isinstance(
                    outra_config,
                    dict,
                )
            ):
                continue


            if (
                str(
                    outra_config.get(
                        "nome",
                        "",
                    )
                )
                .strip()
                .casefold()
                ==
                nome_novo.casefold()
            ):
                return {
                    "success": False,
                    "error": (
                        "Já existe outro cargo "
                        "com esse nome."
                    ),
                }


        atualizacao[
            f"cargos.{cargo_id}.nome"
        ] = nome_novo


    # ========================================================
    # ORDEM
    # ========================================================

    if ordem is not None:

        try:
            ordem_nova = int(
                ordem
            )

        except (
            TypeError,
            ValueError,
        ):
            return {
                "success": False,
                "error": (
                    "Hierarquia do cargo inválida."
                ),
            }


        if (
            ordem_nova < 20
            or
            ordem_nova > 80
        ):
            return {
                "success": False,
                "error": (
                    "A hierarquia precisa estar "
                    "entre 20 e 80."
                ),
            }


        atualizacao[
            f"cargos.{cargo_id}.ordem"
        ] = ordem_nova


    # ========================================================
    # PERMISSÕES
    # ========================================================

    if permissoes is not None:

        atualizacao[
            f"cargos.{cargo_id}.permissoes"
        ] = (
            normalizar_permissoes_cargo(
                permissoes
            )
        )


    if not atualizacao:
        return {
            "success": True,
            "message": (
                "Nenhuma alteração foi necessária."
            ),
        }


    atualizacao[
        f"cargos.{cargo_id}.atualizado_em"
    ] = _agora()

    atualizacao[
        "atualizado_em"
    ] = _agora()


    resultado = (
        clans_collection.update_one(
            {
                "_id":
                    cla["_id"],

                "lider_id":
                    player_id,

                f"cargos.{cargo_id}.sistema":
                    False,
            },
            {
                "$set":
                    atualizacao
            },
        )
    )


    if (
        resultado.modified_count
        != 1
    ):
        return {
            "success": False,
            "error": (
                "Não foi possível atualizar "
                "o cargo."
            ),
        }


    nome_final = (
        atualizacao.get(
            f"cargos.{cargo_id}.nome"
        )
        or
        cargo_atual.get(
            "nome",
            cargo_id,
        )
    )


    membro_lider = (
        _obter_membro(
            cla,
            player_id,
        )
        or {}
    )


    _registrar_atividade(
        clan_id=cla["_id"],

        tipo="cargo",

        mensagem=(
            f"{membro_lider.get('nome', 'O líder')} "
            f"editou o cargo '{nome_final}'."
        ),

        autor_id=
            player_id,

        autor_nome=
            membro_lider.get(
                "nome",
                "Líder",
            ),

        dados={
            "cargo_id":
                cargo_id,
        },
    )


    cla_atualizado = (
        obter_cla_por_id(
            cla["_id"]
        )
    )


    cargo_atualizado = (
        obter_config_cargo_cla(
            cla_atualizado,
            cargo_id,
        )
    )


    return {
        "success": True,

        "message":
            "Cargo atualizado com sucesso.",

        "cargo": {
            "id":
                cargo_id,

            **_json_seguro(
                cargo_atualizado
                or {}
            ),
        },
    }

# ============================================================
# 🗑️ EXCLUIR CARGO PERSONALIZADO
# ============================================================

def excluir_cargo_cla(
    user_id,
    cargo_id,
):
    player_id = _object_id(
        user_id
    )

    if not player_id:
        return {
            "success": False,
            "error": "ID de jogador inválido.",
        }


    cargo_id = str(
        cargo_id or ""
    ).strip()


    if not cargo_id:
        return {
            "success": False,
            "error": "Cargo inválido.",
        }


    cla = obter_cla_do_jogador(
        player_id
    )

    if not cla:
        return {
            "success": False,
            "error": "Você não pertence a um clã.",
        }


    if cla.get(
        "lider_id"
    ) != player_id:

        return {
            "success": False,
            "error": (
                "Somente o líder pode excluir "
                "cargos personalizados."
            ),
        }


    cargo = (
        cla.get(
            "cargos",
            {}
        )
        or {}
    ).get(
        cargo_id
    )


    if not isinstance(
        cargo,
        dict,
    ):
        return {
            "success": False,
            "error": "Cargo não encontrado.",
        }


    if (
        cargo.get(
            "sistema",
            False,
        )
        or
        cargo.get(
            "protegido",
            False,
        )
    ):
        return {
            "success": False,
            "error": (
                "Os cargos padrão não "
                "podem ser excluídos."
            ),
        }


    # Não exclui enquanto alguém estiver
    # usando o cargo.
    membros_com_cargo = [

        membro

        for membro
        in (
            cla.get(
                "membros",
                []
            )
            or []
        )

        if (
            membro.get(
                "cargo"
            )
            == cargo_id
        )
    ]


    if membros_com_cargo:

        return {
            "success": False,

            "error": (
                f"Existem {len(membros_com_cargo)} "
                f"membro(s) usando este cargo. "
                f"Altere o cargo deles antes "
                f"de excluí-lo."
            ),
        }


    campo = (
        f"cargos.{cargo_id}"
    )


    resultado = (
        clans_collection.update_one(
            {
                "_id":
                    cla["_id"],

                "lider_id":
                    player_id,

                f"{campo}.sistema":
                    False,
            },
            {
                "$unset": {
                    campo: "",
                },

                "$set": {
                    "atualizado_em":
                        _agora(),
                },
            },
        )
    )


    if (
        resultado.modified_count
        != 1
    ):
        return {
            "success": False,
            "error": (
                "Não foi possível excluir "
                "o cargo."
            ),
        }


    membro_lider = (
        _obter_membro(
            cla,
            player_id,
        )
        or {}
    )


    nome_cargo = str(
        cargo.get(
            "nome",
            cargo_id,
        )
    )


    _registrar_atividade(
        clan_id=cla["_id"],

        tipo="cargo",

        mensagem=(
            f"{membro_lider.get('nome', 'O líder')} "
            f"excluiu o cargo '{nome_cargo}'."
        ),

        autor_id=
            player_id,

        autor_nome=
            membro_lider.get(
                "nome",
                "Líder",
            ),

        dados={
            "cargo_id":
                cargo_id,

            "cargo_nome":
                nome_cargo,
        },
    )


    return {
        "success": True,

        "message": (
            f"Cargo '{nome_cargo}' "
            f"excluído com sucesso."
        ),
    }

# ============================================================
# 📜 HISTÓRICO DE ATIVIDADES
# ============================================================

LIMITE_ATIVIDADES_CLA = 50
TIPO_ENTRADA_SOLICITACAO = "solicitacao"
TIPO_ENTRADA_CONVITE = "convite"
TIPO_ENTRADA_FECHADO = "fechado"

TIPOS_ENTRADA_VALIDOS = {
    TIPO_ENTRADA_SOLICITACAO,
    TIPO_ENTRADA_CONVITE,
    TIPO_ENTRADA_FECHADO,
}

def _nome_cargo(
    cargo,
    cla=None,
):
    """
    Retorna o nome visual de um cargo.

    Se o clã for informado, também reconhece
    cargos personalizados.
    """

    cargo = str(
        cargo or ""
    ).strip()


    if isinstance(
        cla,
        dict,
    ):

        configuracao = (
            obter_config_cargo_cla(
                cla,
                cargo,
            )
        )

        if configuracao:

            nome = str(
                configuracao.get(
                    "nome",
                    "",
                )
            ).strip()

            if nome:
                return nome


    nomes = {
        CARGO_LIDER:
            "Líder",

        CARGO_VICE_LIDER:
            "Vice-líder",

        CARGO_OFICIAL:
            "Oficial",

        CARGO_MEMBRO:
            "Membro",
    }


    if cargo in nomes:
        return nomes[cargo]


    if cargo:
        return (
            cargo
            .replace("_", " ")
            .title()
        )


    return "Membro"


def _registrar_atividade(
    clan_id,
    tipo,
    mensagem,
    autor_id=None,
    autor_nome=None,
    dados=None,
):
    """
    Registra uma atividade sem impedir a ação principal
    caso o histórico apresente algum erro.

    Mantém somente as 50 atividades mais recentes.
    """

    clan_id = _object_id(clan_id)

    if not clan_id:
        return False

    atividade = {
        "_id": ObjectId(),
        "tipo": str(tipo or "geral"),
        "mensagem": str(mensagem or "").strip(),
        "autor_id": _object_id(autor_id),
        "autor_nome": str(
            autor_nome or "Sistema"
        ),
        "dados": (
            dados
            if isinstance(dados, dict)
            else {}
        ),
        "criado_em": _agora(),
    }

    try:
        resultado = clans_collection.update_one(
            {
                "_id": clan_id,
                "status": "ativo",
            },
            {
                "$push": {
                    "atividades": {
                        "$each": [atividade],
                        "$position": 0,
                        "$slice": LIMITE_ATIVIDADES_CLA,
                    }
                }
            },
        )

        return resultado.matched_count == 1

    except Exception as erro:
        print(
            "⚠️ [CLÃ ATIVIDADE] "
            f"Não foi possível registrar: {erro}"
        )

        return False

# ============================================================
# 🧱 ÍNDICES
# ============================================================

def _remover_indices_legados_cla():
    """
    Remove índices de versões antigas do
    sistema de clãs que não são mais usados.
    """

    indices_legados = {
        "name_lower_1",
    }


    try:

        indices_atuais = list(
            clans_collection.list_indexes()
        )


        for indice in indices_atuais:

            nome = str(
                indice.get(
                    "name",
                    ""
                )
            )


            if (
                nome
                not in indices_legados
            ):
                continue


            clans_collection.drop_index(
                nome
            )


            print(
                "🧹 [CLÃ] Índice legado "
                f"removido: {nome}"
            )


    except Exception as erro:

        print(
            "⚠️ [CLÃ] Não foi possível "
            "verificar índices legados: "
            f"{erro}"
        )

def _garantir_indice_membro_unico_ativo():
    """
    Garante que um personagem participe de apenas
    UM clã ATIVO.

    Registros históricos/inativos não devem impedir
    o personagem de entrar ou fundar um novo clã.
    """

    nome_indice = (
        "clan_membro_unico"
    )


    filtro_correto = {
        "status":
            "ativo",

        "membros.user_id": {
            "$exists":
                True,
        },
    }


    indice_atual = None


    try:

        for indice in (
            clans_collection
            .list_indexes()
        ):

            if (
                indice.get(
                    "name"
                )
                ==
                nome_indice
            ):
                indice_atual = indice
                break


        # ====================================================
        # CONFERE SE O ÍNDICE ANTIGO PRECISA SER SUBSTITUÍDO
        # ====================================================

        if indice_atual:

            parcial_atual = (
                indice_atual.get(
                    "partialFilterExpression"
                )
            )


            eh_unico = bool(
                indice_atual.get(
                    "unique",
                    False,
                )
            )


            if (
                eh_unico
                and
                parcial_atual
                ==
                filtro_correto
            ):
                return


            print(
                "🛠️ [CLÃ] Atualizando índice "
                "de membro único..."
            )


            clans_collection.drop_index(
                nome_indice
            )


        # ====================================================
        # NOVO ÍNDICE
        # ====================================================

        clans_collection.create_index(
            [
                (
                    "membros.user_id",
                    1,
                ),
            ],

            unique=True,

            partialFilterExpression=
                filtro_correto,

            name=
                nome_indice,
        )


        print(
            "✅ [CLÃ] Índice de membros "
            "ativos preparado."
        )


    except Exception as erro:

        print(
            "⚠️ [CLÃ ÍNDICE] "
            "Falha ao preparar índice "
            f"de membros: {erro}"
        )

def garantir_indices():

    _remover_indices_legados_cla()

    clans_collection.create_index(
        "nome_normalizado",
        unique=True,
        name="clan_nome_unico",
    )

    clans_collection.create_index(
        "tag_normalizada",
        unique=True,
        name="clan_tag_unica",
    )

    _garantir_indice_membro_unico_ativo()

    clans_collection.create_index(
        "lider_id",
        name="clan_lider",
    )

    clan_invites_collection.create_index(
        [
            ("clan_id", 1),
            ("user_id", 1),
        ],
        unique=True,
        name="clan_convite_unico",
    )

    clan_invites_collection.create_index(
        "expira_em",
        expireAfterSeconds=0,
        name="clan_convite_expiracao",
    )

    clan_requests_collection.create_index(
        [
            ("clan_id", 1),
            ("user_id", 1),
        ],
        unique=True,
        name="clan_solicitacao_unica",
    )

    clan_requests_collection.create_index(
        "expira_em",
        expireAfterSeconds=0,
        name="clan_solicitacao_expiracao",
    )

# ============================================================
# 🔎 CONSULTAS
# ============================================================

def obter_cla_por_id(clan_id):
    clan_id = _object_id(clan_id)

    if not clan_id:
        return None


    cla = clans_collection.find_one({
        "_id": clan_id,
        "status": "ativo",
    })


    if not cla:
        return None


    return _garantir_cargos_cla(
        cla
    )

def obter_cla_do_jogador(
    user_id,
    reparar_vinculo=True,
):
    player_id = _object_id(user_id)

    if not player_id:
        return None

    jogador = users_collection.find_one(
        {"_id": player_id},
        {"clan_id": 1},
    )

    if not jogador:
        return None

    clan_id = _object_id(
        jogador.get("clan_id")
    )

    # Primeiro verifica o ponteiro salvo no jogador.
    if clan_id:
        cla = obter_cla_por_id(clan_id)

        # O ponteiro só é válido se o jogador
        # também estiver na lista de membros.
        if cla and _obter_membro(
            cla,
            player_id,
        ):
            return cla

        if reparar_vinculo:
            users_collection.update_one(
                {"_id": player_id},
                {
                    "$set": {
                        "clan_id": None,
                    }
                },
            )

            _limpar_cache(player_id)

    # Depois tenta localizar diretamente
    # o jogador dentro dos clãs.
    cla = clans_collection.find_one({
        "status": "ativo",
        "membros.user_id": player_id,
    })

    if cla:
        cla = _garantir_cargos_cla(
            cla
        )

    if cla and reparar_vinculo:
        users_collection.update_one(
            {"_id": player_id},
            {
                "$set": {
                    "clan_id": cla["_id"],
                }
            },
        )

        _limpar_cache(player_id)

    return cla

# ============================================================
# 🔍 BUSCAS PARA A INTERFACE
# ============================================================

def buscar_jogadores_para_convite(
    autor_id,
    termo,
    limite=15,
    
):
    """
    Busca personagens disponíveis para receber convite.

    Somente cargos com permissão para convidar podem usar.
    Não devolve:
    - o próprio autor;
    - jogadores que já possuem clã;
    - dados privados do personagem.
    """

    autor_id = _object_id(autor_id)

    if not autor_id:
        return {
            "success": False,
            "error": "ID do jogador inválido.",
        }

    cla = obter_cla_do_jogador(autor_id)

    if not cla:
        return {
            "success": False,
            "error": "Você não pertence a um clã.",
        }

    cargo_autor = _cargo_no_cla(
        cla,
        autor_id,
    )


    if not tem_permissao_cla(
        cla,
        cargo_autor,
        PERMISSAO_CONVIDAR,
    ):
        return {
            "success": False,
            "error": (
                "Seu cargo não permite procurar "
                "jogadores para convite."
            ),
        }

    termo_original = str(termo or "").strip()
    termo_normalizado = _normalizar_busca(
        termo_original
    )

    if len(termo_normalizado) < 2:
        return {
            "success": False,
            "error": (
                "Digite pelo menos 2 caracteres "
                "do nome do herói."
            ),
        }

    try:
        limite = int(limite)
    except (TypeError, ValueError):
        limite = 15

    limite = max(1, min(limite, 30))

    busca_segura_original = re.escape(
        termo_original
    )

    busca_segura_normalizada = re.escape(
        termo_normalizado
    )

    consulta = {
        "$and": [
            {
                "_id": {
                    "$ne": autor_id,
                }
            },
            {
                "$or": [
                    {
                        "clan_id": {
                            "$exists": False,
                        }
                    },
                    {
                        "clan_id": None,
                    },
                ]
            },
            {
                "$or": [
                    {
                        "name_normalized": {
                            "$regex": busca_segura_normalizada,
                            "$options": "i",
                        }
                    },
                    {
                        "character_name": {
                            "$regex": busca_segura_original,
                            "$options": "i",
                        }
                    },
                ]
            },
        ]
    }

    cursor = users_collection.find(
        consulta,
        {
            "character_name": 1,
            "level": 1,
            "class": 1,
            "gender": 1,
            "equipped_skin": 1,
            "avatar_customizado": 1,
        },
    ).limit(limite)

    jogadores = []

    for jogador in cursor:
        jogadores.append({
            "id": str(jogador["_id"]),
            "nome": jogador.get(
                "character_name",
                "Aventureiro",
            ),
            "level": int(
                jogador.get("level", 1) or 1
            ),
            "classe": str(
                jogador.get("class", "aprendiz")
            ),
            "genero": jogador.get(
                "gender",
                "masculino",
            ),
            "skin": jogador.get(
                "equipped_skin"
            ),
            "avatar": jogador.get(
                "avatar_customizado",
                "padrao",
            ),
        })

    jogadores.sort(
        key=lambda item: item["nome"].casefold()
    )

    return {
        "success": True,
        "jogadores": jogadores,
        "total": len(jogadores),
    }


def listar_clans(
    termo="",
    limite=30,
):
    """
    Lista clãs ativos para a tela pública.
    """

    termo_original = str(termo or "").strip()
    termo_normalizado = _normalizar_busca(
        termo_original
    )

    try:
        limite = int(limite)
    except (TypeError, ValueError):
        limite = 30

    limite = max(1, min(limite, 50))

    consulta = {
        "status": "ativo",
    }

    if termo_normalizado:
        consulta["$or"] = [
            {
                "nome_normalizado": {
                    "$regex": re.escape(
                        termo_normalizado
                    ),
                    "$options": "i",
                }
            },
            {
                "tag_normalizada": {
                    "$regex": re.escape(
                        termo_normalizado
                    ),
                    "$options": "i",
                }
            },
        ]

    cursor = clans_collection.find(
        consulta,
        {
            "nome": 1,
            "tag": 1,
            "descricao": 1,
            "logo_id": 1,
            "nivel": 1,
            "xp": 1,
            "lider_id": 1,
            "membros_total": 1,
            "capacidade_membros": 1,
            "configuracoes": 1,
            "criado_em": 1,
        },
    ).sort(
        [
            ("nivel", -1),
            ("membros_total", -1),
            ("nome", 1),
        ]
    ).limit(limite)

    clans = []

    for cla in cursor:
        membros_total = int(
            cla.get("membros_total", 0) or 0
        )

        capacidade = int(
            cla.get("capacidade_membros", 10) or 10
        )

        logo_id = obter_logo_id_valido(
            cla.get("logo_id")
        )

        clans.append({
            "id": str(cla["_id"]),
            "nome": cla.get(
                "nome",
                "Clã sem nome",
            ),
            "tag": cla.get("tag", ""),
            "descricao": cla.get(
                "descricao",
                "",
            ),
            "logo_id": logo_id,
            "logo_url": obter_logo_url(
                logo_id
            ),
            "nivel": int(
                cla.get("nivel", 1) or 1
            ),
            "xp": int(
                cla.get("xp", 0) or 0
            ),
            "membros_total": membros_total,
            "capacidade_membros": capacidade,
            "possui_vaga": (
                membros_total < capacidade
            ),
            "tipo_entrada": (
                cla.get("configuracoes", {})
                .get("tipo_entrada", "convite")
            ),
            "nivel_minimo": int(
                cla.get("configuracoes", {})
                .get("nivel_minimo", 1)
                or 1
            ),
        })

    return {
        "success": True,
        "clans": clans,
        "total": len(clans),
    }


def obter_detalhes_publicos_cla(
    clan_id,
):
    """
    Consulta pública de um clã.

    Não devolve tesouro completo,
    convites ou informações internas.
    """

    cla = obter_cla_por_id(clan_id)

    if not cla:
        return {
            "success": False,
            "error": "Clã não encontrado.",
        }

    membros_publicos = []


    for membro in cla.get(
        "membros",
        [],
    ):

        cargo_id = membro.get(
            "cargo",
            CARGO_MEMBRO,
        )


        membros_publicos.append({

            "user_id":
                str(
                    membro.get(
                        "user_id"
                    )
                ),

            "nome":
                membro.get(
                    "nome",
                    "Aventureiro",
                ),

            "cargo":
                cargo_id,

            "cargo_nome":
                _nome_cargo(
                    cargo_id,
                    cla,
                ),

            "cargo_ordem":
                obter_ordem_cargo_cla(
                    cla,
                    cargo_id,
                ),

            "nivel_entrada":
                int(
                    membro.get(
                        "nivel_entrada",
                        1,
                    ) or 1
                ),

            "contribuicao_xp":
                int(
                    membro.get(
                        "contribuicao_xp",
                        0,
                    ) or 0
                ),
        })


    membros_publicos.sort(
        key=lambda membro: (

            -int(
                membro.get(
                    "cargo_ordem",
                    0,
                )
                or 0
            ),

            membro[
                "nome"
            ].casefold(),
        )
    )

    membros_total = int(
        cla.get("membros_total", 0) or 0
    )

    capacidade = int(
        cla.get("capacidade_membros", 10)
        or 10
    )

    logo_id = obter_logo_id_valido(
        cla.get("logo_id")
    )

    return {
        "success": True,
        "clan": {
            "id": str(cla["_id"]),
            "nome": cla.get("nome"),
            "tag": cla.get("tag"),
            "descricao": cla.get(
                "descricao",
                "",
            ),
            "logo_id": logo_id,
            "logo_url": obter_logo_url(
                logo_id
            ),
            "nivel": int(
                cla.get("nivel", 1) or 1
            ),
            "xp": int(
                cla.get("xp", 0) or 0
            ),
            "membros_total": membros_total,
            "capacidade_membros": capacidade,
            "possui_vaga": (
                membros_total < capacidade
            ),
            "tipo_entrada": (
                cla.get("configuracoes", {})
                .get("tipo_entrada", "convite")
            ),
            "nivel_minimo": int(
                cla.get("configuracoes", {})
                .get("nivel_minimo", 1)
                or 1
            ),
            "membros": membros_publicos,
        },
    }

# ============================================================
# 🕵️ INSPEÇÃO DE MEMBROS
# ============================================================

def validar_inspecao_membro(
    solicitante_id,
    alvo_id,
):
    """
    Verifica se o solicitante e o alvo pertencem
    ao mesmo clã.

    Esta função não devolve dados privados do jogador.
    Ela apenas autoriza ou bloqueia a inspeção.
    """

    solicitante_id = _object_id(solicitante_id)
    alvo_id = _object_id(alvo_id)

    if not solicitante_id or not alvo_id:
        return {
            "success": False,
            "error": "ID de jogador inválido.",
        }

    cla_solicitante = obter_cla_do_jogador(
        solicitante_id
    )

    if not cla_solicitante:
        return {
            "success": False,
            "error": "Você não pertence a um clã.",
        }

    cla_alvo = obter_cla_do_jogador(
        alvo_id
    )

    if not cla_alvo:
        return {
            "success": False,
            "error": "Esse jogador não pertence a um clã.",
        }

    if cla_solicitante["_id"] != cla_alvo["_id"]:
        return {
            "success": False,
            "error": (
                "Você só pode inspecionar membros "
                "do seu próprio clã."
            ),
        }

    membro_alvo = _obter_membro(
        cla_solicitante,
        alvo_id,
    )

    if not membro_alvo:
        return {
            "success": False,
            "error": "Membro não encontrado no clã.",
        }

    return {
        "success": True,
        "clan_id": cla_solicitante["_id"],
        "clan_nome": cla_solicitante.get(
            "nome",
            "Clã",
        ),
        "membro": membro_alvo,
    }

# ============================================================
# 👑 CRIAR CLÃ
# ============================================================

def criar_cla(
    user_id,
    nome,
    tag,
    descricao="",
    logo_id=None,
):
    player_id = _object_id(user_id)

    if not player_id:
        return {
            "success": False,
            "error": "ID de jogador inválido.",
        }

    nome_ok, erro, nome_limpo = _validar_nome(nome)

    if not nome_ok:
        return {
            "success": False,
            "error": erro,
        }

    tag_ok, erro, tag_limpa = _validar_tag(tag)

    if not tag_ok:
        return {
            "success": False,
            "error": erro,
        }

    descricao = str(descricao or "").strip()

    if len(descricao) > 300:
        return {
            "success": False,
            "error": "A descrição pode ter no máximo 300 caracteres.",
        }

    logo_id = str(
        logo_id or LOGO_PADRAO_ID
    ).strip()

    if not logo_valida(logo_id):
        return {
            "success": False,
            "error": "A logo selecionada é inválida.",
        }
    
    jogador = users_collection.find_one(
        {"_id": player_id},
        {
            "character_name": 1,
            "level": 1,
            "clan_id": 1,
            "gold": 1,
        },
    )

    if not jogador:
        return {
            "success": False,
            "error": "Herói não encontrado.",
        }

    cla_atual = (
        obter_cla_do_jogador(
            player_id,
            reparar_vinculo=True,
        )
    )


    if cla_atual:

        return {
            "success": False,

            "error": (
                "Você já pertence ao clã "
                f"{cla_atual.get('nome', 'atual')}."
            ),
        }

    # ========================================================
    # 🪙 CUSTO DE FUNDAÇÃO
    # ========================================================

    ouro_atual = int(
        jogador.get(
            "gold",
            0,
        )
        or 0
    )


    if (
        ouro_atual <
        CLAN_CUSTO_CRIACAO_OURO
    ):
        return {
            "success": False,

            "error": (
                "Ouro insuficiente. "
                "Fundar um clã custa "
                f"{CLAN_CUSTO_CRIACAO_OURO:,} moedas."
            ).replace(",", "."),

            "custo_ouro":
                CLAN_CUSTO_CRIACAO_OURO,

            "ouro_atual":
                ouro_atual,
        }
    
    garantir_indices()

    agora = _agora()
    nivel = CLAN_NIVEL_INICIAL

    novo_cla = {
        "schema_version": CLAN_SCHEMA_VERSION,

        "nome": nome_limpo,
        "nome_normalizado": _normalizar_busca(nome_limpo),

        "tag": tag_limpa,
        "tag_normalizada": tag_limpa.casefold(),

        "descricao": descricao,
        "logo_id": logo_id,

        "nivel": nivel,
        "xp": 0,

        "capacidade_membros": obter_capacidade(nivel),
        "membros_total": 1,

        "lider_id": player_id,
        # ====================================================
        # 🎖️ CARGOS DO CLÃ
        # ====================================================

        "cargos":
            obter_cargos_padrao(),
            
        "membros": [
            {
                "user_id": player_id,
                "nome": jogador.get(
                    "character_name",
                    "Aventureiro",
                ),
                "nivel_entrada": int(
                    jogador.get("level", 1) or 1
                ),
                "cargo": CARGO_LIDER,
                "contribuicao_ouro": 0,
                "contribuicao_xp": 0,
                "entrou_em": agora,
            }
        ],

        "atividades": [
            {
                "_id": ObjectId(),
                "tipo": "criacao",
                "mensagem": (
                    f"{jogador.get('character_name', 'Aventureiro')} "
                    f"fundou o clã."
                ),
                "autor_id": player_id,
                "autor_nome": jogador.get(
                    "character_name",
                    "Aventureiro",
                ),
                "dados": {},
                "criado_em": agora,
            }
        ],

        "tesouro": {
            "ouro": 0,
        },

        # ====================================================
        # 💼 LICENÇA DA TESOURARIA
        # ====================================================

        "tesouraria": {
            "ativada_em": None,
            "expira_em": None,
            "ativada_por": None,
            "custo_gemas": 0,
            "ciclo": 0,
        },

        # ====================================================
        # 🏰 MISSÕES COLETIVAS DA GUILDA
        # ====================================================

        "guild_missions": {

            # Missões atualmente aceitas pelo clã.
            "ativas": {},

            # Histórico coletivo.
            "concluidas": {},

            # Pontuação própria do clã
            # dentro da Guilda.
            "pontos": 0,
        },
                
        "configuracoes": {
            "tipo_entrada": "convite",
            "nivel_minimo": 1,
        },

        "status": "ativo",

        "criado_em": agora,
        "atualizado_em": agora,
    }

    clan_id = None

    try:
        resultado = clans_collection.insert_one(novo_cla)
        clan_id = resultado.inserted_id

        resultado_player = users_collection.update_one(
            {
                "_id":
                    player_id,

                "gold": {
                    "$gte":
                        CLAN_CUSTO_CRIACAO_OURO,
                },

                "$or": [
                    {
                        "clan_id": {
                            "$exists":
                                False,
                        }
                    },
                    {
                        "clan_id":
                            None,
                    },
                ],
            },

            {
                "$set": {
                    "clan_id":
                        clan_id,
                },

                "$inc": {
                    "gold":
                        -CLAN_CUSTO_CRIACAO_OURO,
                },
            },
        )

        if (
            resultado_player.modified_count
            != 1
        ):
            # O clã provisório não pode ficar
            # abandonado no banco.
            clans_collection.delete_one({
                "_id":
                    clan_id
            })


            jogador_atual = (
                users_collection.find_one(
                    {
                        "_id":
                            player_id,
                    },
                    {
                        "clan_id": 1,
                        "gold": 1,
                    },
                )
                or {}
            )


            if jogador_atual.get(
                "clan_id"
            ):
                return {
                    "success": False,
                    "error": (
                        "Você já entrou em "
                        "outro clã."
                    ),
                }


            ouro_atualizado = int(
                jogador_atual.get(
                    "gold",
                    0,
                )
                or 0
            )


            if (
                ouro_atualizado <
                CLAN_CUSTO_CRIACAO_OURO
            ):
                return {
                    "success": False,

                    "error": (
                        "Ouro insuficiente. "
                        "Fundar um clã custa "
                        f"{CLAN_CUSTO_CRIACAO_OURO:,} "
                        "moedas."
                    ).replace(",", "."),

                    "custo_ouro":
                        CLAN_CUSTO_CRIACAO_OURO,

                    "ouro_atual":
                        ouro_atualizado,
                }


            return {
                "success": False,

                "error": (
                    "Não foi possível concluir "
                    "a fundação do clã."
                ),
            }

        _limpar_cache(player_id)

        clan_invites_collection.delete_many({
            "user_id": player_id,
        })

        clan_requests_collection.delete_many({
            "user_id": player_id,
        })

        cla = clans_collection.find_one({
            "_id":
                clan_id
        })


        jogador_final = (
            users_collection.find_one(
                {
                    "_id":
                        player_id,
                },
                {
                    "gold": 1,
                },
            )
            or {}
        )


        ouro_restante = int(
            jogador_final.get(
                "gold",
                0,
            )
            or 0
        )


        return {
            "success": True,

            "message": (
                f"Clã {nome_limpo} "
                "fundado com sucesso!"
            ),

            "custo_ouro":
                CLAN_CUSTO_CRIACAO_OURO,

            "ouro_restante":
                ouro_restante,

            "clan":
                serializar_cla(
                    cla
                ),
        }

    except DuplicateKeyError as erro_dup:

        if clan_id:

            clans_collection.delete_one({
                "_id":
                    clan_id
            })


        # ====================================================
        # NOME DUPLICADO
        # ====================================================

        if clans_collection.find_one({
            "nome_normalizado":
                _normalizar_busca(
                    nome_limpo
                )
        }):

            mensagem = (
                "Já existe um clã "
                "com esse nome."
            )


        # ====================================================
        # TAG DUPLICADA
        # ====================================================

        elif clans_collection.find_one({
            "tag_normalizada":
                tag_limpa.casefold()
        }):

            mensagem = (
                "Já existe um clã "
                "com essa tag."
            )


        # ====================================================
        # MEMBRO REALMENTE EM OUTRO CLÃ ATIVO
        # ====================================================

        else:

            cla_conflitante = (
                clans_collection
                .find_one(
                    {
                        "status":
                            "ativo",

                        "membros.user_id":
                            player_id,
                    },
                    {
                        "nome": 1,
                        "tag": 1,
                    },
                )
            )


            if cla_conflitante:

                mensagem = (
                    "Você já pertence ao clã "
                    f"{cla_conflitante.get('nome', 'atual')}."
                )

            else:

                mensagem = (
                    "Houve um conflito ao registrar "
                    "o personagem no clã. "
                    "Tente novamente."
                )


        return {
            "success": False,
            "error":
                mensagem,
        }


    except PyMongoError as erro:
        if clan_id:
            clans_collection.delete_one({
                "_id": clan_id
            })

        return {
            "success": False,
            "error": f"Erro ao criar o clã: {erro}",
        }


# ============================================================
# ✉️ CONVITES
# ============================================================

def convidar_jogador(
    autor_id,
    alvo_id,
):
    autor_id = _object_id(autor_id)
    alvo_id = _object_id(alvo_id)

    if not autor_id or not alvo_id:
        return {
            "success": False,
            "error": "ID inválido.",
        }

    if autor_id == alvo_id:
        return {
            "success": False,
            "error": "Você não pode convidar a si mesmo.",
        }

    cla = obter_cla_do_jogador(autor_id)

    if not cla:
        return {
            "success": False,
            "error": "Você não pertence a um clã.",
        }

    configuracoes = cla.get(
        "configuracoes",
        {},
    ) or {}

    tipo_entrada = configuracoes.get(
        "tipo_entrada",
        TIPO_ENTRADA_CONVITE, 
    )

    if tipo_entrada == TIPO_ENTRADA_FECHADO:
        return {
            "success": False,
            "error": (
                "O recrutamento deste clã está fechado."
            ),
        }
    
    cargo_autor = _cargo_no_cla(
        cla,
        autor_id,
    )


    if not tem_permissao_cla(
        cla,
        cargo_autor,
        PERMISSAO_CONVIDAR,
    ):
        return {
            "success": False,
            "error": (
                "Seu cargo não permite "
                "enviar convites."
            ),
        }

    alvo = users_collection.find_one(
        {"_id": alvo_id},
        {
            "character_name": 1,
            "level": 1,
            "clan_id": 1,
        },
    )

    if not alvo:
        return {
            "success": False,
            "error": "Herói não encontrado.",
        }

    if alvo.get("clan_id") or obter_cla_do_jogador(alvo_id):
        return {
            "success": False,
            "error": "Esse herói já pertence a um clã.",
        }

    total = int(cla.get("membros_total", 0))
    capacidade = int(cla.get("capacidade_membros", 10))

    if total >= capacidade:
        return {
            "success": False,
            "error": "O clã atingiu o limite de membros.",
        }

    nivel_minimo = int(
        cla.get("configuracoes", {}).get(
            "nivel_minimo",
            1,
        )
    )

    if int(alvo.get("level", 1)) < nivel_minimo:
        return {
            "success": False,
            "error": (
                f"O clã exige nível mínimo {nivel_minimo}."
            ),
        }

    garantir_indices()

    agora = _agora()
    expira = agora + timedelta(days=7)

    clan_invites_collection.update_one(
        {
            "clan_id": cla["_id"],
            "user_id": alvo_id,
        },
        {
            "$set": {
                "convidado_por": autor_id,
                "criado_em": agora,
                "expira_em": expira,
                "status": "pendente",
            }
        },
        upsert=True,
    )

    return {
        "success": True,
        "message": (
            f"Convite enviado para "
            f"{alvo.get('character_name', 'Aventureiro')}."
        ),
    }


def listar_convites(user_id):
    player_id = _object_id(user_id)

    if not player_id:
        return {
            "success": False,
            "error": "ID inválido.",
        }

    convites = list(
        clan_invites_collection.find({
            "user_id": player_id,
            "status": "pendente",
            "expira_em": {"$gt": _agora()},
        })
    )

    resultado = []

    for convite in convites:
        cla = obter_cla_por_id(
            convite.get("clan_id")
        )

        if not cla:
            continue

        resultado.append({
            "clan_id": str(cla["_id"]),
            "nome": cla.get("nome"),
            "tag": cla.get("tag"),
            "nivel": cla.get("nivel", 1),
            "membros_total": cla.get("membros_total", 0),
            "capacidade_membros": cla.get(
                "capacidade_membros",
                10,
            ),
            "expira_em": convite.get(
                "expira_em"
            ).isoformat(),
        })

    return {
        "success": True,
        "convites": resultado,
    }


def aceitar_convite(
    user_id,
    clan_id,
):
    player_id = _object_id(user_id)
    clan_id = _object_id(clan_id)

    if not player_id or not clan_id:
        return {
            "success": False,
            "error": "Dados inválidos.",
        }

    convite = clan_invites_collection.find_one({
        "clan_id": clan_id,
        "user_id": player_id,
        "status": "pendente",
        "expira_em": {"$gt": _agora()},
    })

    if not convite:
        return {
            "success": False,
            "error": "Convite inexistente ou expirado.",
        }

    jogador = users_collection.find_one(
        {"_id": player_id},
        {
            "character_name": 1,
            "level": 1,
            "clan_id": 1,
        },
    )

    if not jogador:
        return {
            "success": False,
            "error": "Herói não encontrado.",
        }

    if (
        jogador.get("clan_id")
        or obter_cla_do_jogador(player_id)
    ):
        return {
            "success": False,
            "error": "Você já pertence a um clã.",
        }

    # Revalida o estado atual do clã
    # no momento da aceitação.
    cla = obter_cla_por_id(clan_id)

    if not cla:
        clan_invites_collection.delete_one({
            "clan_id": clan_id,
            "user_id": player_id,
        })

        return {
            "success": False,
            "error": (
                "O clã não está mais disponível."
            ),
        }

    configuracoes = (
        cla.get("configuracoes", {})
        or {}
    )

    tipo_entrada = str(
        configuracoes.get(
            "tipo_entrada",
            TIPO_ENTRADA_CONVITE,
        )
    ).strip().lower()

    if tipo_entrada == TIPO_ENTRADA_FECHADO:
        clan_invites_collection.delete_one({
            "clan_id": clan_id,
            "user_id": player_id,
        })

        return {
            "success": False,
            "error": (
                "O recrutamento deste clã "
                "está fechado."
            ),
        }

    nivel_jogador = int(
        jogador.get("level", 1) or 1
    )

    nivel_minimo = int(
        configuracoes.get(
            "nivel_minimo",
            1,
        ) or 1
    )

    if nivel_jogador < nivel_minimo:
        return {
            "success": False,
            "error": (
                f"O clã exige nível mínimo "
                f"{nivel_minimo}."
            ),
        }

    membros_total = int(
        cla.get("membros_total", 0) or 0
    )

    capacidade = int(
        cla.get(
            "capacidade_membros",
            10,
        ) or 10
    )

    if membros_total >= capacidade:
        return {
            "success": False,
            "error": (
                "O clã atingiu o limite "
                "de membros."
            ),
        }

    resultado_player = users_collection.update_one(

        {
            "_id": player_id,
            "$or": [
                {"clan_id": {"$exists": False}},
                {"clan_id": None},
            ],
        },
        {
            "$set": {
                "clan_id": clan_id,
            }
        },
    )

    if resultado_player.modified_count != 1:
        return {
            "success": False,
            "error": "Você já entrou em outro clã.",
        }

    agora = _agora()

    novo_membro = {
        "user_id": player_id,
        "nome": jogador.get(
            "character_name",
            "Aventureiro",
        ),
        "nivel_entrada": int(
            jogador.get("level", 1) or 1
        ),
        "cargo": CARGO_MEMBRO,
        "contribuicao_ouro": 0,
        "contribuicao_xp": 0,
        "entrou_em": agora,
    }

    try:
        resultado_cla = clans_collection.update_one(
            {
                "_id": clan_id,
                "status": "ativo",
                "membros.user_id": {
                    "$ne": player_id
                },
                "$expr": {
                    "$lt": [
                        "$membros_total",
                        "$capacidade_membros",
                    ]
                },
            },
            {
                "$push": {
                    "membros": novo_membro,
                },
                "$inc": {
                    "membros_total": 1,
                },
                "$set": {
                    "atualizado_em": agora,
                },
            },
        )

        if resultado_cla.modified_count != 1:
            users_collection.update_one(
                {
                    "_id": player_id,
                    "clan_id": clan_id,
                },
                {
                    "$set": {
                        "clan_id": None,
                    }
                },
            )

            return {
                "success": False,
                "error": (
                    "O clã está cheio ou não está mais disponível."
                ),
            }

        _registrar_atividade(
            clan_id=clan_id,
            tipo="entrada",
            mensagem=(
                f"{jogador.get('character_name', 'Aventureiro')} "
                f"entrou no clã por convite."
            ),
            autor_id=player_id,
            autor_nome=jogador.get(
                "character_name",
                "Aventureiro",
            ),
        )
        
        clan_invites_collection.delete_many({
            "user_id": player_id
        })

        clan_requests_collection.delete_many({
            "user_id": player_id
        })

        _limpar_cache(player_id)

        cla_atualizado = obter_cla_por_id(
            clan_id
        )

        nome_cla = (
            cla_atualizado.get(
                "nome",
                "Clã",
            )
            if cla_atualizado
            else "Clã"
        )

        return {
            "success": True,
            "message": (
                f"Você entrou no clã "
                f"{nome_cla}!"
            ),
            "clan": serializar_cla(
                cla_atualizado
            ),
        }

    except Exception as erro:
        users_collection.update_one(
            {
                "_id": player_id,
                "clan_id": clan_id,
            },
            {
                "$set": {
                    "clan_id": None,
                }
            },
        )

        return {
            "success": False,
            "error": f"Erro ao entrar no clã: {erro}",
        }


def recusar_convite(
    user_id,
    clan_id,
):
    player_id = _object_id(user_id)
    clan_id = _object_id(clan_id)

    if not player_id or not clan_id:
        return {
            "success": False,
            "error": "Dados inválidos.",
        }

    resultado = clan_invites_collection.delete_one({
        "user_id": player_id,
        "clan_id": clan_id,
    })

    if resultado.deleted_count != 1:
        return {
            "success": False,
            "error": "Convite não encontrado.",
        }

    return {
        "success": True,
        "message": "Convite recusado.",
    }

# ============================================================
# 📩 SOLICITAÇÕES DE ENTRADA
# ============================================================

def solicitar_entrada(
    user_id,
    clan_id,
):
    player_id = _object_id(user_id)
    clan_id = _object_id(clan_id)

    if not player_id or not clan_id:
        return {
            "success": False,
            "error": "Dados inválidos.",
        }

    jogador = users_collection.find_one(
        {"_id": player_id},
        {
            "character_name": 1,
            "level": 1,
            "class": 1,
            "clan_id": 1,
        },
    )

    if not jogador:
        return {
            "success": False,
            "error": "Herói não encontrado.",
        }

    if (
        jogador.get("clan_id")
        or obter_cla_do_jogador(player_id)
    ):
        return {
            "success": False,
            "error": "Você já pertence a um clã.",
        }

    cla = obter_cla_por_id(clan_id)

    if not cla:
        return {
            "success": False,
            "error": "Clã não encontrado.",
        }

    configuracoes = cla.get(
        "configuracoes",
        {},
    ) or {}

    tipo_entrada = configuracoes.get(
        "tipo_entrada",
        "convite",
    )

    if tipo_entrada == TIPO_ENTRADA_FECHADO:
        return {
            "success": False,
            "error": (
                "Este clã está com o recrutamento fechado."
            ),
        }

    if tipo_entrada == TIPO_ENTRADA_CONVITE:
        return {
            "success": False,
            "error": (
                "Este clã aceita somente jogadores convidados."
            ),
        }

    if tipo_entrada != TIPO_ENTRADA_SOLICITACAO:
        return {
            "success": False,
            "error": (
                "A política de entrada deste clã "
                "não permite solicitações."
            ),
        }

    membros_total = int(
        cla.get("membros_total", 0) or 0
    )

    capacidade = int(
        cla.get("capacidade_membros", 10)
        or 10
    )

    if membros_total >= capacidade:
        return {
            "success": False,
            "error": "O clã atingiu o limite de membros.",
        }

    nivel_jogador = int(
        jogador.get("level", 1) or 1
    )

    nivel_minimo = int(
        configuracoes.get("nivel_minimo", 1)
        or 1
    )

    if nivel_jogador < nivel_minimo:
        return {
            "success": False,
            "error": (
                f"Este clã exige nível mínimo "
                f"{nivel_minimo}."
            ),
        }

    convite = clan_invites_collection.find_one({
        "clan_id": clan_id,
        "user_id": player_id,
        "status": "pendente",
        "expira_em": {
            "$gt": _agora(),
        },
    })

    if convite:
        return {
            "success": False,
            "error": (
                "Você já recebeu um convite deste clã. "
                "Abra Meus convites para aceitar."
            ),
        }

    garantir_indices()

    pedido_existente = (
        clan_requests_collection.find_one({
            "clan_id": clan_id,
            "user_id": player_id,
            "status": "pendente",
            "expira_em": {
                "$gt": _agora(),
            },
        })
    )

    if pedido_existente:
        return {
            "success": True,
            "pendente": True,
            "message": (
                "Sua solicitação para este clã "
                "já está pendente."
            ),
        }

    agora = _agora()
    expira_em = agora + timedelta(days=7)

    clan_requests_collection.update_one(
        {
            "clan_id": clan_id,
            "user_id": player_id,
        },
        {
            "$set": {
                "status": "pendente",
                "criado_em": agora,
                "expira_em": expira_em,
            }
        },
        upsert=True,
    )

    return {
        "success": True,
        "pendente": True,
        "message": (
            f"Solicitação enviada para o clã "
            f"{cla.get('nome', 'Clã')}."
        ),
    }


def listar_solicitacoes(
    autor_id,
):
    autor_id = _object_id(autor_id)

    if not autor_id:
        return {
            "success": False,
            "error": "ID inválido.",
        }

    cla = obter_cla_do_jogador(autor_id)

    if not cla:
        return {
            "success": False,
            "error": "Você não pertence a um clã.",
        }

    cargo = _cargo_no_cla(
        cla,
        autor_id,
    )


    if not tem_permissao_cla(
        cla,
        cargo,
        PERMISSAO_ACEITAR_SOLICITACOES,
    ):
        return {
            "success": False,
            "error": (
                "Seu cargo não permite "
                "analisar solicitações de entrada."
            ),
        }

    pedidos = list(
        clan_requests_collection.find({
            "clan_id": cla["_id"],
            "status": "pendente",
            "expira_em": {
                "$gt": _agora(),
            },
        }).sort("criado_em", 1)
    )

    resultado = []

    for pedido in pedidos:
        player_id = pedido.get("user_id")

        jogador = users_collection.find_one(
            {"_id": player_id},
            {
                "character_name": 1,
                "level": 1,
                "class": 1,
                "clan_id": 1,
            },
        )

        if not jogador:
            clan_requests_collection.delete_one({
                "_id": pedido["_id"],
            })
            continue

        if jogador.get("clan_id"):
            clan_requests_collection.delete_one({
                "_id": pedido["_id"],
            })
            continue

        criado_em = pedido.get("criado_em")
        expira_em = pedido.get("expira_em")

        resultado.append({
            "user_id": str(player_id),

            "nome": jogador.get(
                "character_name",
                "Aventureiro",
            ),

            "nivel": int(
                jogador.get("level", 1) or 1
            ),

            "classe": str(
                jogador.get(
                    "class",
                    "aventureiro",
                )
            ),

            "criado_em": (
                criado_em.isoformat()
                if hasattr(criado_em, "isoformat")
                else None
            ),

            "expira_em": (
                expira_em.isoformat()
                if hasattr(expira_em, "isoformat")
                else None
            ),
        })

    return {
        "success": True,
        "solicitacoes": resultado,
        "total": len(resultado),
    }


def aceitar_solicitacao(
    autor_id,
    alvo_id,
):
    autor_id = _object_id(autor_id)
    alvo_id = _object_id(alvo_id)

    if not autor_id or not alvo_id:
        return {
            "success": False,
            "error": "Dados inválidos.",
        }

    cla = obter_cla_do_jogador(autor_id)

    if not cla:
        return {
            "success": False,
            "error": "Você não pertence a um clã.",
        }

    cargo = _cargo_no_cla(
        cla,
        autor_id,
    )


    if not tem_permissao_cla(
        cla,
        cargo,
        PERMISSAO_ACEITAR_SOLICITACOES,
    ):
        return {
            "success": False,
            "error": (
                "Seu cargo não permite "
                "aceitar solicitações de entrada."
            ),
        }

    tipo_entrada = str(
        (
            cla.get("configuracoes", {})
            or {}
        ).get(
            "tipo_entrada",
            TIPO_ENTRADA_CONVITE,
        )
    ).strip().lower()

    if (
        tipo_entrada !=
        TIPO_ENTRADA_SOLICITACAO
    ):
        clan_requests_collection.delete_many({
            "clan_id": cla["_id"],
        })

        return {
            "success": False,
            "error": (
                "Este clã não está mais "
                "aceitando solicitações."
            ),
        }

    pedido = clan_requests_collection.find_one({
        "clan_id": cla["_id"],
        "user_id": alvo_id,
        "status": "pendente",
        "expira_em": {
            "$gt": _agora(),
        },
    })

    if not pedido:
        return {
            "success": False,
            "error": (
                "Solicitação inexistente ou expirada."
            ),
        }

    jogador = users_collection.find_one(
        {"_id": alvo_id},
        {
            "character_name": 1,
            "level": 1,
            "class": 1,
            "clan_id": 1,
        },
    )

    if not jogador:
        return {
            "success": False,
            "error": "Herói não encontrado.",
        }

    if (
        jogador.get("clan_id")
        or obter_cla_do_jogador(alvo_id)
    ):
        clan_requests_collection.delete_many({
            "user_id": alvo_id,
        })

        return {
            "success": False,
            "error": (
                "Esse jogador já pertence a um clã."
            ),
        }

    membros_total = int(
        cla.get("membros_total", 0) or 0
    )

    capacidade = int(
        cla.get("capacidade_membros", 10)
        or 10
    )

    if membros_total >= capacidade:
        return {
            "success": False,
            "error": "O clã atingiu o limite de membros.",
        }

    nivel_jogador = int(
        jogador.get("level", 1) or 1
    )

    nivel_minimo = int(
        cla.get("configuracoes", {})
        .get("nivel_minimo", 1)
        or 1
    )

    if nivel_jogador < nivel_minimo:
        return {
            "success": False,
            "error": (
                f"O jogador precisa estar no nível "
                f"{nivel_minimo}."
            ),
        }

    resultado_player = users_collection.update_one(
        {
            "_id": alvo_id,
            "$or": [
                {
                    "clan_id": {
                        "$exists": False,
                    }
                },
                {
                    "clan_id": None,
                },
            ],
        },
        {
            "$set": {
                "clan_id": cla["_id"],
            }
        },
    )

    if resultado_player.modified_count != 1:
        return {
            "success": False,
            "error": (
                "O jogador já entrou em outro clã."
            ),
        }

    agora = _agora()

    novo_membro = {
        "user_id": alvo_id,

        "nome": jogador.get(
            "character_name",
            "Aventureiro",
        ),

        "nivel_entrada": nivel_jogador,

        "cargo": CARGO_MEMBRO,

        "contribuicao_ouro": 0,
        "contribuicao_xp": 0,

        "entrou_em": agora,
    }

    try:
        resultado_cla = clans_collection.update_one(
            {
                "_id": cla["_id"],
                "status": "ativo",

                "membros.user_id": {
                    "$ne": alvo_id,
                },

                "$expr": {
                    "$lt": [
                        "$membros_total",
                        "$capacidade_membros",
                    ]
                },
            },
            {
                "$push": {
                    "membros": novo_membro,
                },

                "$inc": {
                    "membros_total": 1,
                },

                "$set": {
                    "atualizado_em": agora,
                },
            },
        )

        if resultado_cla.modified_count != 1:
            users_collection.update_one(
                {
                    "_id": alvo_id,
                    "clan_id": cla["_id"],
                },
                {
                    "$set": {
                        "clan_id": None,
                    }
                },
            )

            return {
                "success": False,
                "error": (
                    "O clã está cheio ou não está "
                    "mais disponível."
                ),
            }

        membro_autor = _obter_membro(
            cla,
            autor_id,
        ) or {}

        _registrar_atividade(
            clan_id=cla["_id"],
            tipo="entrada",
            mensagem=(
                f"{jogador.get('character_name', 'Aventureiro')} "
                f"foi aceito no clã."
            ),
            autor_id=autor_id,
            autor_nome=membro_autor.get(
                "nome",
                "Líder",
            ),
            dados={
                "novo_membro_id": str(alvo_id),
                "novo_membro_nome": jogador.get(
                    "character_name",
                    "Aventureiro",
                ),
            },
        )
        
        clan_requests_collection.delete_many({
            "user_id": alvo_id,
        })

        clan_invites_collection.delete_many({
            "user_id": alvo_id,
        })

        _limpar_cache(alvo_id)

        return {
            "success": True,
            "message": (
                f"{jogador.get('character_name', 'O jogador')} "
                f"entrou no clã."
            ),
        }

    except Exception as erro:
        users_collection.update_one(
            {
                "_id": alvo_id,
                "clan_id": cla["_id"],
            },
            {
                "$set": {
                    "clan_id": None,
                }
            },
        )

        return {
            "success": False,
            "error": (
                f"Erro ao aceitar solicitação: {erro}"
            ),
        }


def recusar_solicitacao(
    autor_id,
    alvo_id,
):
    autor_id = _object_id(autor_id)
    alvo_id = _object_id(alvo_id)

    if not autor_id or not alvo_id:
        return {
            "success": False,
            "error": "Dados inválidos.",
        }

    cla = obter_cla_do_jogador(autor_id)

    if not cla:
        return {
            "success": False,
            "error": "Você não pertence a um clã.",
        }

    cargo = _cargo_no_cla(
        cla,
        autor_id,
    )


    if not tem_permissao_cla(
        cla,
        cargo,
        PERMISSAO_ACEITAR_SOLICITACOES,
    ):
        return {
            "success": False,
            "error": (
                "Seu cargo não permite "
                "recusar solicitações de entrada."
            ),
        }

    resultado = clan_requests_collection.delete_one({
        "clan_id": cla["_id"],
        "user_id": alvo_id,
        "status": "pendente",
    })

    if resultado.deleted_count != 1:
        return {
            "success": False,
            "error": "Solicitação não encontrada.",
        }

    return {
        "success": True,
        "message": "Solicitação recusada.",
    }

# ============================================================
# 🚪 SAÍDA E EXPULSÃO
# ============================================================

def sair_cla(user_id):
    player_id = _object_id(user_id)

    if not player_id:
        return {
            "success": False,
            "error": "ID inválido.",
        }

    cla = obter_cla_do_jogador(player_id)

    if not cla:
        return {
            "success": False,
            "error": "Você não pertence a um clã.",
        }

    membro_saida = _obter_membro(
        cla,
        player_id,
    )

    nome_saida = (
        membro_saida.get("nome", "Aventureiro")
        if membro_saida
        else "Aventureiro"
    )

    cargo = _cargo_no_cla(cla, player_id)

    if cargo == CARGO_LIDER:
        return {
            "success": False,
            "error": (
                "O líder precisa transferir a liderança "
                "ou dissolver o clã."
            ),
        }

    resultado = clans_collection.update_one(
        {
            "_id": cla["_id"],
            "membros.user_id": player_id,
        },
        {
            "$pull": {
                "membros": {
                    "user_id": player_id,
                }
            },
            "$inc": {
                "membros_total": -1,
            },
            "$set": {
                "atualizado_em": _agora(),
            },
        },
    )

    if resultado.modified_count != 1:
        return {
            "success": False,
            "error": "Não foi possível sair do clã.",
        }

    # ========================================================
    # ⚔️ REMOVE PARTICIPAÇÃO NA GUERRA
    # ========================================================

    try:

        from modules.clan import (
            clan_war_manager,
        )


        clan_war_manager.remover_participacao_forcada(
            user_id=player_id,
            clan_id=cla["_id"],
            motivo="saida_cla",
        )


    except Exception as erro:

        print(
            "⚠️ [CLÃ/GUERRA] "
            "Não foi possível remover "
            "participação após saída: "
            f"{erro}"
        )

    _registrar_atividade(
        clan_id=cla["_id"],
        tipo="saida",
        mensagem=f"{nome_saida} saiu do clã.",
        autor_id=player_id,
        autor_nome=nome_saida,
    )

    users_collection.update_one(
        {
            "_id": player_id,
            "clan_id": cla["_id"],
        },
        {
            "$set": {
                "clan_id": None,
            }
        },
    )

    _limpar_cache(player_id)

    return {
        "success": True,
        "message": "Você saiu do clã.",
    }


def expulsar_membro(
    autor_id,
    alvo_id,
):
    autor_id = _object_id(autor_id)
    alvo_id = _object_id(alvo_id)

    if not autor_id or not alvo_id:
        return {
            "success": False,
            "error": "ID inválido.",
        }

    if autor_id == alvo_id:
        return {
            "success": False,
            "error": "Use a opção de sair do clã.",
        }

    cla = obter_cla_do_jogador(autor_id)

    if not cla:
        return {
            "success": False,
            "error": "Você não pertence a um clã.",
        }

    membro_autor = _obter_membro(
        cla,
        autor_id,
    )

    membro_alvo = _obter_membro(
        cla,
        alvo_id,
    )


    if not membro_autor:
        return {
            "success": False,
            "error": (
                "Seu vínculo com o clã "
                "não foi encontrado."
            ),
        }


    if not membro_alvo:
        return {
            "success": False,
            "error": (
                "Esse jogador não pertence "
                "ao seu clã."
            ),
        }


    cargo_autor = membro_autor.get(
        "cargo",
        CARGO_MEMBRO,
    )

    cargo_alvo = membro_alvo.get(
        "cargo",
        CARGO_MEMBRO,
    )


    if not tem_permissao_cla(
        cla,
        cargo_autor,
        PERMISSAO_EXPULSAR,
    ):
        return {
            "success": False,
            "error": (
                "Seu cargo não permite "
                "expulsar membros."
            ),
        }


    if not cargo_superior_no_cla(
        cla,
        cargo_autor,
        cargo_alvo,
    ):
        return {
            "success": False,
            "error": (
                "Você só pode expulsar "
                "membros de hierarquia inferior."
            ),
        }

    resultado = clans_collection.update_one(
        {
            "_id": cla["_id"],
            "membros.user_id": alvo_id,
        },
        {
            "$pull": {
                "membros": {
                    "user_id": alvo_id,
                }
            },
            "$inc": {
                "membros_total": -1,
            },
            "$set": {
                "atualizado_em": _agora(),
            },
        },
    )

    if resultado.modified_count != 1:
        return {
            "success": False,
            "error": "Não foi possível expulsar o membro.",
        }

    # ========================================================
    # ⚔️ REMOVE O EXPULSO DA GUERRA
    # ========================================================

    try:

        from modules.clan import (
            clan_war_manager,
        )


        clan_war_manager.remover_participacao_forcada(
            user_id=alvo_id,
            clan_id=cla["_id"],
            motivo="expulsao_cla",
        )


    except Exception as erro:

        print(
            "⚠️ [CLÃ/GUERRA] "
            "Não foi possível remover "
            "o expulso da Guerra: "
            f"{erro}"
        )

        
    _registrar_atividade(
        clan_id=cla["_id"],
        tipo="expulsao",
        mensagem=(
            f"{membro_alvo.get('nome', 'Aventureiro')} "
            f"foi expulso do clã."
        ),
        autor_id=autor_id,
        autor_nome=membro_autor.get(
            "nome",
            "Aventureiro",
        ),
        dados={
            "alvo_id": str(alvo_id),
            "alvo_nome": membro_alvo.get(
                "nome",
                "Aventureiro",
            ),
        },
    )

    users_collection.update_one(
        {
            "_id": alvo_id,
            "clan_id": cla["_id"],
        },
        {
            "$set": {
                "clan_id": None,
            }
        },
    )

    _limpar_cache(alvo_id)

    return {
        "success": True,
        "message": (
            f"{membro_alvo.get('nome', 'O jogador')} "
            f"foi expulso do clã."
        ),
    }


# ============================================================
# 👑 CARGOS E LIDERANÇA
# ============================================================

def alterar_cargo(
    lider_id,
    alvo_id,
    novo_cargo,
):
    """
    Altera o cargo de um membro.

    Mantemos o nome do parâmetro lider_id
    por compatibilidade com a API atual,
    mas ele representa o autor da ação.
    """

    autor_id = _object_id(
        lider_id
    )

    alvo_id = _object_id(
        alvo_id
    )


    if not autor_id or not alvo_id:
        return {
            "success": False,
            "error": "ID inválido.",
        }


    if autor_id == alvo_id:
        return {
            "success": False,
            "error": (
                "Você não pode alterar "
                "o próprio cargo."
            ),
        }


    novo_cargo = str(
        novo_cargo or ""
    ).strip()


    if not novo_cargo:
        return {
            "success": False,
            "error": "Cargo inválido.",
        }


    cla = obter_cla_do_jogador(
        autor_id
    )


    if not cla:
        return {
            "success": False,
            "error": "Você não pertence a um clã.",
        }


    membro_autor = _obter_membro(
        cla,
        autor_id,
    )


    if not membro_autor:
        return {
            "success": False,
            "error": (
                "Seu vínculo com o clã "
                "não foi encontrado."
            ),
        }


    membro_alvo = _obter_membro(
        cla,
        alvo_id,
    )


    if not membro_alvo:
        return {
            "success": False,
            "error": "Membro não encontrado.",
        }


    cargo_autor = membro_autor.get(
        "cargo",
        CARGO_MEMBRO,
    )

    cargo_anterior = membro_alvo.get(
        "cargo",
        CARGO_MEMBRO,
    )


    # ========================================================
    # 🔐 PERMISSÃO
    # ========================================================

    if not tem_permissao_cla(
        cla,
        cargo_autor,
        PERMISSAO_GERENCIAR_CARGOS,
    ):
        return {
            "success": False,
            "error": (
                "Seu cargo não permite "
                "administrar cargos."
            ),
        }


    # Liderança continua sendo especial.
    if cargo_anterior == CARGO_LIDER:
        return {
            "success": False,
            "error": (
                "Use a transferência "
                "de liderança."
            ),
        }


    # Também não é possível transformar
    # alguém em líder por esta função.
    if novo_cargo == CARGO_LIDER:
        return {
            "success": False,
            "error": (
                "Use a transferência "
                "de liderança para definir "
                "um novo líder."
            ),
        }


    # ========================================================
    # 🎖️ CONFIRMA QUE O NOVO CARGO EXISTE
    # ========================================================

    config_novo_cargo = (
        obter_config_cargo_cla(
            cla,
            novo_cargo,
        )
    )


    if not config_novo_cargo:
        return {
            "success": False,
            "error": (
                "Esse cargo não existe "
                "neste clã."
            ),
        }


    # ========================================================
    # 🏰 PROTEÇÃO DE HIERARQUIA
    # ========================================================

    eh_lider = (
        cargo_autor
        == CARGO_LIDER
        and
        cla.get("lider_id")
        == autor_id
    )


    if not eh_lider:

        # Só pode alterar alguém abaixo dele.
        if not cargo_superior_no_cla(
            cla,
            cargo_autor,
            cargo_anterior,
        ):
            return {
                "success": False,
                "error": (
                    "Você não pode alterar "
                    "o cargo de alguém com "
                    "hierarquia igual ou superior."
                ),
            }


        ordem_autor = (
            obter_ordem_cargo_cla(
                cla,
                cargo_autor,
            )
        )

        ordem_novo = (
            obter_ordem_cargo_cla(
                cla,
                novo_cargo,
            )
        )


        # Um administrador não pode conceder
        # cargo igual ou superior ao próprio.
        if ordem_novo >= ordem_autor:
            return {
                "success": False,
                "error": (
                    "Você não pode conceder "
                    "um cargo de hierarquia "
                    "igual ou superior à sua."
                ),
            }


    # ========================================================
    # JÁ POSSUI
    # ========================================================

    if cargo_anterior == novo_cargo:

        return {
            "success": True,

            "message": (
                f"{membro_alvo.get('nome', 'O membro')} "
                f"já possui o cargo de "
                f"{_nome_cargo(novo_cargo, cla)}."
            ),
        }


    # ========================================================
    # SALVA
    # ========================================================

    resultado = clans_collection.update_one(
        {
            "_id":
                cla["_id"],

            "membros": {
                "$elemMatch": {
                    "user_id":
                        alvo_id,

                    "cargo":
                        cargo_anterior,
                }
            },
        },
        {
            "$set": {

                "membros.$.cargo":
                    novo_cargo,

                "atualizado_em":
                    _agora(),
            }
        },
    )


    if resultado.modified_count != 1:
        return {
            "success": False,
            "error": (
                "Não foi possível alterar "
                "o cargo."
            ),
        }


    nome_anterior = _nome_cargo(
        cargo_anterior,
        cla,
    )

    nome_novo = _nome_cargo(
        novo_cargo,
        cla,
    )


    _registrar_atividade(
        clan_id=
            cla["_id"],

        tipo=
            "cargo",

        mensagem=(
            f"{membro_alvo.get('nome', 'Aventureiro')} "
            f"passou de {nome_anterior} "
            f"para {nome_novo}."
        ),

        autor_id=
            autor_id,

        autor_nome=
            membro_autor.get(
                "nome",
                "Aventureiro",
            ),

        dados={
            "alvo_id":
                str(alvo_id),

            "cargo_anterior":
                cargo_anterior,

            "novo_cargo":
                novo_cargo,
        },
    )


    return {
        "success": True,

        "message":
            "Cargo alterado com sucesso.",

        "cargo": {
            "id":
                novo_cargo,

            "nome":
                nome_novo,
        },
    }

def transferir_lideranca(
    lider_id,
    novo_lider_id,
):
    lider_id = _object_id(lider_id)
    novo_lider_id = _object_id(novo_lider_id)

    if not lider_id or not novo_lider_id:
        return {
            "success": False,
            "error": "ID inválido.",
        }

    if lider_id == novo_lider_id:
        return {
            "success": False,
            "error": "Você já é o líder.",
        }

    cla = obter_cla_do_jogador(lider_id)

    if not cla or cla.get("lider_id") != lider_id:
        return {
            "success": False,
            "error": "Somente o líder atual pode fazer isso.",
        }

    alvo = _obter_membro(cla, novo_lider_id)

    if not alvo:
        return {
            "success": False,
            "error": "O novo líder precisa pertencer ao clã.",
        }

    resultado = clans_collection.update_one(
        {
            "_id": cla["_id"],
            "lider_id": lider_id,
        },
        {
            "$set": {
                "lider_id": novo_lider_id,
                "membros.$[antigo].cargo": CARGO_VICE_LIDER,
                "membros.$[novo].cargo": CARGO_LIDER,
                "atualizado_em": _agora(),
            }
        },
        array_filters=[
            {
                "antigo.user_id": lider_id
            },
            {
                "novo.user_id": novo_lider_id
            },
        ],
    )

    if resultado.modified_count != 1:
        return {
            "success": False,
            "error": "Não foi possível transferir a liderança.",
        }

    antigo_lider = _obter_membro(
        cla,
        lider_id,
    ) or {}

    _registrar_atividade(
        clan_id=cla["_id"],
        tipo="lideranca",
        mensagem=(
            f"{alvo.get('nome', 'Aventureiro')} "
            f"tornou-se o novo líder do clã."
        ),
        autor_id=lider_id,
        autor_nome=antigo_lider.get(
            "nome",
            "Líder",
        ),
        dados={
            "lider_anterior_id": str(lider_id),
            "novo_lider_id": str(novo_lider_id),
        },
    )

    return {
        "success": True,
        "message": (
            f"{alvo.get('nome', 'O membro')} "
            f"agora é o líder do clã."
        ),
    }


# ============================================================
# 💰 TESOURO E XP
# ============================================================
def comprar_tesouraria(
    user_id,
):
    player_id = _object_id(
        user_id
    )


    if not player_id:
        return {
            "success": False,
            "error": (
                "ID de jogador inválido."
            ),
        }


    # ========================================================
    # 🏰 LOCALIZA O CLÃ
    # ========================================================

    cla = obter_cla_do_jogador(
        player_id
    )


    if not cla:
        return {
            "success": False,
            "error": (
                "Você não pertence a um clã."
            ),
        }


    # ========================================================
    # 👑 SOMENTE O LÍDER COMPRA
    # ========================================================

    if (
        cla.get(
            "lider_id"
        )
        != player_id
    ):
        return {
            "success": False,
            "error": (
                "Somente o líder do clã "
                "pode ativar a Tesouraria."
            ),
        }


    estado_atual = (
        obter_estado_tesouraria(
            cla
        )
    )

    duracao_dias = int(
        estado_atual.get(
            "duracao_dias",
            30,
        )
        or 30
    )

    # ========================================================
    # ✅ JÁ ESTÁ ATIVA
    # ========================================================

    if estado_atual.get(
        "ativa"
    ):
        return {
            "success": False,
            "error": (
                "A Tesouraria do clã "
                "já está ativa."
            ),

            "tesouraria":
                _json_seguro(
                    estado_atual
                ),
        }


    # ========================================================
    # 🔐 IDENTIFICADOR IDEMPOTENTE
    #
    # Duas requisições simultâneas usam o mesmo ciclo.
    # Assim nunca descontamos duas vezes pelo mesmo período.
    # ========================================================

    ciclo_atual = int(
        estado_atual.get(
            "ciclo",
            0,
        )
        or 0
    )


    proximo_ciclo = (
        ciclo_atual + 1
    )


    operacao_id = (
        f"tesouraria:"
        f"{cla['_id']}:"
        f"{proximo_ciclo}"
    )


    # ========================================================
    # 👤 CONFIRMA O JOGADOR
    # ========================================================

    jogador = (
        users_collection.find_one(
            {
                "_id":
                    player_id,
            },
            {
                "gems": 1,
                "clan_id": 1,
                "character_name": 1,
                "clan_tesouraria_compras": 1,
            },
        )
    )


    if not jogador:
        return {
            "success": False,
            "error": (
                "Herói não encontrado."
            ),
        }


    if (
        _object_id(
            jogador.get(
                "clan_id"
            )
        )
        != cla["_id"]
    ):
        return {
            "success": False,
            "error": (
                "Seu vínculo com o clã "
                "foi alterado."
            ),
        }


    compras_processadas = (
        jogador.get(
            "clan_tesouraria_compras",
            [],
        )
        or []
    )


    credito_ja_reservado = (
        operacao_id
        in compras_processadas
    )


    # ========================================================
    # 💎 DESCONTA AS 100 GEMAS
    # ========================================================

    if not credito_ja_reservado:

        try:
            resultado_player = (
                users_collection.update_one(
                    {
                        "_id":
                            player_id,

                        "clan_id":
                            cla["_id"],

                        "gems": {
                            "$gte":
                                TESOURARIA_CUSTO_GEMAS,
                        },

                        "clan_tesouraria_compras": {
                            "$ne":
                                operacao_id,
                        },
                    },

                    {
                        "$inc": {
                            "gems":
                                -TESOURARIA_CUSTO_GEMAS,
                        },

                        "$addToSet": {
                            "clan_tesouraria_compras":
                                operacao_id,
                        },
                    },
                )
            )

        except PyMongoError as erro:

            print(
                "⚠️ [TESOURARIA] "
                "Erro ao reservar Gemas: "
                f"{erro}"
            )

            return {
                "success": False,
                "error": (
                    "Não foi possível acessar "
                    "suas Gemas."
                ),
            }


        if (
            resultado_player.modified_count
            != 1
        ):

            jogador_atual = (
                users_collection.find_one(
                    {
                        "_id":
                            player_id,
                    },
                    {
                        "gems": 1,
                        "clan_id": 1,
                        "clan_tesouraria_compras": 1,
                    },
                )
                or {}
            )


            compras_atuais = (
                jogador_atual.get(
                    "clan_tesouraria_compras",
                    [],
                )
                or []
            )


            # Outra requisição pode ter feito
            # exatamente esta mesma reserva.
            if (
                operacao_id
                in compras_atuais
            ):
                credito_ja_reservado = True

            elif int(
                jogador_atual.get(
                    "gems",
                    0,
                )
                or 0
            ) < TESOURARIA_CUSTO_GEMAS:

                return {
                    "success": False,
                    "error": (
                        "Gemas insuficientes. "
                        "A Tesouraria custa "
                        f"{TESOURARIA_CUSTO_GEMAS} Gemas."
                    ),
                }

            else:
                return {
                    "success": False,
                    "error": (
                        "Não foi possível iniciar "
                        "a compra da Tesouraria."
                    ),
                }


    # ========================================================
    # 🗓️ ATIVA PELO PERÍODO DO NÍVEL DO CLÃ
    # ========================================================

    agora = _agora()

    expira_em = (
        agora
        +
        timedelta(
            days=duracao_dias
        )
    )


    filtro_ciclo = {
        "$or": [
            {
                "tesouraria.ciclo":
                    ciclo_atual,
            }
        ]
    }


    if ciclo_atual == 0:
        filtro_ciclo["$or"].append({
            "tesouraria.ciclo": {
                "$exists":
                    False,
            }
        })


    try:
        resultado_cla = (
            clans_collection.update_one(
                {
                    "_id":
                        cla["_id"],

                    "status":
                        "ativo",

                    "lider_id":
                        player_id,

                    "$and": [

                        {
                            "$or": [
                                {
                                    "tesouraria.expira_em": {
                                        "$exists":
                                            False,
                                    }
                                },

                                {
                                    "tesouraria.expira_em":
                                        None,
                                },

                                {
                                    "tesouraria.expira_em": {
                                        "$lte":
                                            agora,
                                    }
                                },
                            ]
                        },

                        filtro_ciclo,
                    ],
                },

                {
                    "$set": {

                        "tesouraria.ativada_em":
                            agora,

                        "tesouraria.expira_em":
                            expira_em,

                        "tesouraria.ativada_por":
                            player_id,

                        "tesouraria.custo_gemas":
                            TESOURARIA_CUSTO_GEMAS,

                        "tesouraria.ciclo":
                            proximo_ciclo,

                        "atualizado_em":
                            agora,
                    }
                },
            )
        )

    except PyMongoError as erro:

        resultado_cla = None

        print(
            "⚠️ [TESOURARIA] "
            "Erro ao ativar licença: "
            f"{erro}"
        )


    # ========================================================
    # 🛡️ CONFIRMA SE OUTRA REQUISIÇÃO JÁ FINALIZOU
    # ========================================================

    ativacao_confirmada = bool(
        resultado_cla
        and
        resultado_cla.modified_count
        == 1
    )


    if not ativacao_confirmada:

        cla_atualizado = (
            obter_cla_por_id(
                cla["_id"]
            )
        )


        if cla_atualizado:

            estado_depois = (
                obter_estado_tesouraria(
                    cla_atualizado
                )
            )


            if (
                estado_depois.get(
                    "ativa"
                )
                and
                int(
                    estado_depois.get(
                        "ciclo",
                        0,
                    )
                    or 0
                )
                >= proximo_ciclo
            ):
                ativacao_confirmada = True


    # ========================================================
    # ↩️ ROLLBACK DAS GEMAS
    # ========================================================

    if not ativacao_confirmada:

        users_collection.update_one(
            {
                "_id":
                    player_id,

                "clan_tesouraria_compras":
                    operacao_id,
            },

            {
                "$inc": {
                    "gems":
                        TESOURARIA_CUSTO_GEMAS,
                },

                "$pull": {
                    "clan_tesouraria_compras":
                        operacao_id,
                },
            },
        )


        _limpar_cache(
            player_id
        )


        return {
            "success": False,

            "error": (
                "Não foi possível ativar "
                "a Tesouraria. "
                "As Gemas foram devolvidas."
            ),
        }


    # ========================================================
    # 📜 HISTÓRICO
    # ========================================================

    membro_lider = (
        _obter_membro(
            cla,
            player_id,
        )
        or {}
    )


    nome_lider = (
        membro_lider.get(
            "nome"
        )
        or
        jogador.get(
            "character_name"
        )
        or
        "Líder"
    )


    _registrar_atividade(
        clan_id=
            cla["_id"],

        tipo=
            "tesouro",

        mensagem=(
            f"{nome_lider} ativou a "
            f"Tesouraria do clã por "
            f"{duracao_dias} dias."
        ),

        autor_id=
            player_id,

        autor_nome=
            nome_lider,

        dados={
            "custo_gemas":
                TESOURARIA_CUSTO_GEMAS,

            "duracao_dias":
                duracao_dias,

            "ciclo":
                proximo_ciclo,
        },
    )


    _limpar_cache(
        player_id
    )


    jogador_final = (
        users_collection.find_one(
            {
                "_id":
                    player_id,
            },
            {
                "gems": 1,
            },
        )
        or {}
    )


    cla_final = (
        obter_cla_por_id(
            cla["_id"]
        )
    )


    return {
        "success": True,

        "message": (
            "Tesouraria ativada por "
            f"{duracao_dias} dias!"
        ),

        "gemas_gastas":
            TESOURARIA_CUSTO_GEMAS,

        "gemas_restantes":
            int(
                jogador_final.get(
                    "gems",
                    0,
                )
                or 0
            ),

        "tesouraria":
            _json_seguro(
                obter_estado_tesouraria(
                    cla_final
                    or cla
                )
            ),
    }

def doar_ouro(
    user_id,
    quantidade,
):
    player_id = _object_id(user_id)

    try:
        quantidade = int(quantidade)
    except (TypeError, ValueError):
        quantidade = 0

    if not player_id or quantidade <= 0:
        return {
            "success": False,
            "error": "Quantidade inválida.",
        }

    cla = obter_cla_do_jogador(player_id)

    if not cla:
        return {
            "success": False,
            "error": "Você não pertence a um clã.",
        }

    resultado_player = users_collection.update_one(
        {
            "_id": player_id,
            "gold": {
                "$gte": quantidade
            },
        },
        {
            "$inc": {
                "gold": -quantidade,
            }
        },
    )

    if resultado_player.modified_count != 1:
        return {
            "success": False,
            "error": "Ouro insuficiente.",
        }

    resultado_cla = clans_collection.update_one(
        {
            "_id": cla["_id"],
            "membros.user_id": player_id,
        },
        {
            "$inc": {
                "tesouro.ouro": quantidade,
                "membros.$.contribuicao_ouro": quantidade,
            },
            "$set": {
                "atualizado_em": _agora(),
            },
        },
    )

    if resultado_cla.modified_count != 1:
        users_collection.update_one(
            {"_id": player_id},
            {
                "$inc": {
                    "gold": quantidade,
                }
            },
        )

        return {
            "success": False,
            "error": "Não foi possível depositar no tesouro.",
        }

    membro_doador = _obter_membro(
        cla,
        player_id,
    ) or {}

    nome_doador = membro_doador.get(
        "nome",
        "Aventureiro",
    )

    quantidade_formatada = (
        f"{quantidade:,}".replace(",", ".")
    )

    _registrar_atividade(
        clan_id=cla["_id"],
        tipo="doacao",
        mensagem=(
            f"{nome_doador} doou "
            f"{quantidade_formatada} moedas ao clã."
        ),
        autor_id=player_id,
        autor_nome=nome_doador,
        dados={
            "quantidade": quantidade,
        },
    )

    _limpar_cache(player_id)

    return {
        "success": True,
        "message": (
            f"Você doou {quantidade} moedas ao clã."
        ),
    }

def enviar_ouro_tesouro(
    user_id,
    alvo_id,
    quantidade,
):
    autor_id = _object_id(
        user_id
    )

    destinatario_id = _object_id(
        alvo_id
    )


    try:
        quantidade = int(
            quantidade
        )

    except (
        TypeError,
        ValueError,
    ):
        quantidade = 0


    if (
        not autor_id
        or not destinatario_id
        or quantidade <= 0
    ):
        return {
            "success": False,
            "error": (
                "Dados da transferência "
                "são inválidos."
            ),
        }


    # ========================================================
    # 🏰 LOCALIZA O CLÃ DO ADMINISTRADOR
    # ========================================================

    cla = obter_cla_do_jogador(
        autor_id
    )


    if not cla:
        return {
            "success": False,
            "error": (
                "Você não pertence a um clã."
            ),
        }


    cargo_autor = _cargo_no_cla(
        cla,
        autor_id,
    )


    # ========================================================
    # 🔐 PERMISSÃO
    # ========================================================
    #
    # O verdadeiro líder sempre pode administrar.
    #
    # Outros cargos precisam possuir explicitamente
    # "gerenciar_tesouro".
    # ========================================================

    if (
        cla.get(
            "lider_id"
        ) != autor_id
        and
        not tem_permissao_cla(
            cla,
            cargo_autor,
            PERMISSAO_GERENCIAR_TESOURO,
        )
    ):
        return {
            "success": False,
            "error": (
                "Seu cargo não permite "
                "administrar o tesouro do clã."
            ),
        }

    # ========================================================
    # 💼 LICENÇA DA TESOURARIA
    # ========================================================

    estado_tesouraria = (
        obter_estado_tesouraria(
            cla
        )
    )

    duracao_tesouraria = int(
        estado_tesouraria.get(
            "duracao_dias",
            30,
        )
        or 30
    )

    if not estado_tesouraria.get(
        "ativa"
    ):
        return {
            "success": False,

            "error": (
                "A Tesouraria do clã não está ativa. "
                "O líder precisa adquirir a licença "
                f"de {duracao_tesouraria} dias."
            ),
        }
    
    # ========================================================
    # 👤 DESTINATÁRIO PRECISA ESTAR NO MESMO CLÃ
    # ========================================================

    membro_destinatario = (
        _obter_membro(
            cla,
            destinatario_id,
        )
    )


    if not membro_destinatario:
        return {
            "success": False,
            "error": (
                "O destinatário precisa ser "
                "membro do mesmo clã."
            ),
        }


    jogador_destinatario = (
        users_collection.find_one(
            {
                "_id":
                    destinatario_id,

                "clan_id":
                    cla["_id"],
            },
            {
                "character_name": 1,
            },
        )
    )


    if not jogador_destinatario:
        return {
            "success": False,
            "error": (
                "O personagem destinatário "
                "não foi encontrado no clã."
            ),
        }


    # ========================================================
    # 💰 RESERVA O OURO DO TESOURO
    # ========================================================
    #
    # Primeiro retiramos do tesouro.
    #
    # Isso evita criar ouro caso alguma etapa posterior
    # falhe.
    #
    # O filtro também confirma novamente:
    #
    # - clã ainda ativo
    # - autor ainda pertence ao clã
    # - autor ainda possui o mesmo cargo
    # - destinatário ainda pertence ao clã
    # - tesouro ainda possui o valor
    # ========================================================

    try:
        resultado_cla = (
            clans_collection.update_one(
                {
                    "_id":
                        cla["_id"],

                    "status":
                        "ativo",

                    "tesouro.ouro": {
                        "$gte":
                            quantidade,
                    },

                    "tesouraria.expira_em": {
                        "$gt":
                            _agora(),
                    },
                    
                    "$and": [
                        {
                            "membros": {
                                "$elemMatch": {
                                    "user_id":
                                        autor_id,

                                    "cargo":
                                        cargo_autor,
                                }
                            }
                        },

                        {
                            "membros": {
                                "$elemMatch": {
                                    "user_id":
                                        destinatario_id,
                                }
                            }
                        },
                    ],

                    "$or": [
                        {
                            "lider_id":
                                autor_id,
                        },

                        {
                            (
                                f"cargos.{cargo_autor}."
                                f"permissoes."
                                f"{PERMISSAO_GERENCIAR_TESOURO}"
                            ):
                                True,
                        },
                    ],
                },

                {
                    "$inc": {
                        "tesouro.ouro":
                            -quantidade,
                    },

                    "$set": {
                        "atualizado_em":
                            _agora(),
                    },
                },
            )
        )

    except PyMongoError as erro:
        print(
            "⚠️ [CLÃ TESOURO] "
            "Erro ao reservar ouro: "
            f"{erro}"
        )

        return {
            "success": False,
            "error": (
                "Não foi possível acessar "
                "o tesouro do clã."
            ),
        }


    # ========================================================
    # ❌ NÃO CONSEGUIU RETIRAR
    # ========================================================

    if (
        resultado_cla.modified_count
        != 1
    ):
        cla_atual = (
            clans_collection.find_one(
                {
                    "_id":
                        cla["_id"],
                },
                {
                    "tesouro.ouro": 1,
                },
            )
            or {}
        )


        saldo_atual = int(
            (
                cla_atual.get(
                    "tesouro",
                    {},
                )
                or {}
            ).get(
                "ouro",
                0,
            )
            or 0
        )


        if saldo_atual < quantidade:
            return {
                "success": False,
                "error": (
                    "O tesouro do clã não possui "
                    "ouro suficiente."
                ),
            }


        return {
            "success": False,
            "error": (
                "O clã foi alterado durante "
                "a operação. Tente novamente."
            ),
        }


    # ========================================================
    # ↩️ ROLLBACK DE SEGURANÇA
    # ========================================================
    #
    # Caso o crédito no personagem falhe,
    # o ouro reservado volta ao tesouro.
    # ========================================================

    def _devolver_ouro_ao_tesouro():
        try:
            rollback = (
                clans_collection.update_one(
                    {
                        "_id":
                            cla["_id"],
                    },

                    {
                        "$inc": {
                            "tesouro.ouro":
                                quantidade,
                        },

                        "$set": {
                            "atualizado_em":
                                _agora(),
                        },
                    },
                )
            )


            if (
                rollback.modified_count
                != 1
            ):
                print(
                    "🚨 [CLÃ TESOURO] "
                    "Falha crítica ao devolver "
                    f"{quantidade} moedas ao clã "
                    f"{cla['_id']}."
                )


        except Exception as erro:
            print(
                "🚨 [CLÃ TESOURO] "
                "Erro crítico no rollback: "
                f"{erro}"
            )


    # ========================================================
    # 🪙 ENTREGA AO PERSONAGEM
    # ========================================================

    try:
        resultado_player = (
            users_collection.update_one(
                {
                    "_id":
                        destinatario_id,

                    "clan_id":
                        cla["_id"],
                },

                {
                    "$inc": {
                        "gold":
                            quantidade,
                    }
                },
            )
        )


    except PyMongoError as erro:
        _devolver_ouro_ao_tesouro()


        print(
            "⚠️ [CLÃ TESOURO] "
            "Falha ao creditar jogador: "
            f"{erro}"
        )


        return {
            "success": False,
            "error": (
                "Não foi possível entregar "
                "o ouro ao destinatário."
            ),
        }


    if (
        resultado_player.modified_count
        != 1
    ):
        _devolver_ouro_ao_tesouro()


        return {
            "success": False,
            "error": (
                "O destinatário não está mais "
                "disponível para receber o ouro."
            ),
        }


    # ========================================================
    # 📜 REGISTRA A MOVIMENTAÇÃO
    # ========================================================

    membro_autor = (
        _obter_membro(
            cla,
            autor_id,
        )
        or {}
    )


    nome_autor = membro_autor.get(
        "nome",
        "Aventureiro",
    )


    nome_destinatario = (
        membro_destinatario.get(
            "nome"
        )
        or
        jogador_destinatario.get(
            "character_name"
        )
        or
        "Aventureiro"
    )


    quantidade_formatada = (
        f"{quantidade:,}"
        .replace(
            ",",
            ".",
        )
    )


    _registrar_atividade(
        clan_id=
            cla["_id"],

        tipo=
            "tesouro",

        mensagem=(
            f"{nome_autor} enviou "
            f"{quantidade_formatada} moedas "
            f"do tesouro para "
            f"{nome_destinatario}."
        ),

        autor_id=
            autor_id,

        autor_nome=
            nome_autor,

        dados={
            "quantidade":
                quantidade,

            "destinatario_id":
                str(
                    destinatario_id
                ),

            "destinatario_nome":
                nome_destinatario,
        },
    )


    # ========================================================
    # 🧹 CACHE
    # ========================================================

    _limpar_cache(
        destinatario_id
    )

    _limpar_cache(
        autor_id
    )


    return {
        "success": True,

        "message": (
            f"{quantidade_formatada} moedas "
            f"foram enviadas para "
            f"{nome_destinatario}."
        ),

        "quantidade":
            quantidade,

        "destinatario_id":
            str(
                destinatario_id
            ),

        "destinatario_nome":
            nome_destinatario,
    }

def adicionar_xp_cla(
    user_id,
    quantidade,
):
    player_id = _object_id(user_id)

    try:
        quantidade = int(quantidade)
    except (TypeError, ValueError):
        quantidade = 0

    if not player_id or quantidade <= 0:
        return False

    cla = obter_cla_do_jogador(player_id)

    if not cla:
        return False

    resultado = clans_collection.update_one(
        {
            "_id": cla["_id"],
            "membros.user_id": player_id,
        },
        {
            "$inc": {
                "xp": quantidade,
                "membros.$.contribuicao_xp": quantidade,
            },
            "$set": {
                "atualizado_em": _agora(),
            },
        },
    )

    return resultado.modified_count == 1

# ============================================================
# ⚙️ CONFIGURAÇÕES DO CLÃ
# ============================================================

def atualizar_configuracoes_cla(
    user_id,
    descricao=None,
    tipo_entrada=None,
    nivel_minimo=None,
):
    player_id = _object_id(user_id)

    if not player_id:
        return {
            "success": False,
            "error": "ID de jogador inválido.",
        }

    cla = obter_cla_do_jogador(player_id)

    if not cla:
        return {
            "success": False,
            "error": "Você não pertence a um clã.",
        }

    cargo = _cargo_no_cla(
        cla,
        player_id,
    )


    if not tem_permissao_cla(
        cla,
        cargo,
        PERMISSAO_EDITAR_CLA,
    ):
        return {
            "success": False,
            "error": (
                "Seu cargo não permite alterar "
                "as configurações do clã."
            ),
        }

    configuracoes_atuais = cla.get(
        "configuracoes",
        {},
    ) or {}

    descricao_atual = str(
        cla.get("descricao", "") or ""
    ).strip()

    tipo_atual = str(
        configuracoes_atuais.get(
            "tipo_entrada",
            TIPO_ENTRADA_CONVITE,
        )
    ).strip().lower()

    nivel_atual = int(
        configuracoes_atuais.get(
            "nivel_minimo",
            1,
        ) or 1
    )

    descricao_nova = (
        descricao_atual
        if descricao is None
        else str(descricao or "").strip()
    )

    if len(descricao_nova) > 300:
        return {
            "success": False,
            "error": (
                "A descrição pode ter no máximo "
                "300 caracteres."
            ),
        }

    tipo_novo = str(
        tipo_entrada or tipo_atual
    ).strip().lower()

    if tipo_novo not in TIPOS_ENTRADA_VALIDOS:
        return {
            "success": False,
            "error": "Tipo de entrada inválido.",
        }

    try:
        nivel_novo = int(
            nivel_minimo
            if nivel_minimo is not None
            else nivel_atual
        )
    except (TypeError, ValueError):
        return {
            "success": False,
            "error": "O nível mínimo é inválido.",
        }

    if nivel_novo < 1 or nivel_novo > 999:
        return {
            "success": False,
            "error": (
                "O nível mínimo precisa estar "
                "entre 1 e 999."
            ),
        }

    nada_mudou = (
        descricao_nova == descricao_atual
        and tipo_novo == tipo_atual
        and nivel_novo == nivel_atual
    )

    if nada_mudou:
        return {
            "success": True,
            "message": "Nenhuma configuração foi alterada.",
            "configuracoes": {
                "tipo_entrada": tipo_atual,
                "nivel_minimo": nivel_atual,
            },
            "descricao": descricao_atual,
        }

    agora = _agora()

    resultado = clans_collection.update_one(
        {
            "_id": cla["_id"],
            "status": "ativo",
            "membros.user_id": player_id,
        },
        {
            "$set": {
                "descricao": descricao_nova,
                "configuracoes.tipo_entrada": tipo_novo,
                "configuracoes.nivel_minimo": nivel_novo,
                "atualizado_em": agora,
            }
        },
    )

    if resultado.modified_count != 1:
        return {
            "success": False,
            "error": (
                "Não foi possível atualizar "
                "as configurações do clã."
            ),
        }

    # Só limpa pendências quando a política
    # de recrutamento realmente mudou.
    if tipo_novo != tipo_atual:
        if tipo_novo in {
            TIPO_ENTRADA_CONVITE,
            TIPO_ENTRADA_FECHADO,
        }:
            clan_requests_collection.delete_many({
                "clan_id": cla["_id"],
            })

        if tipo_novo == TIPO_ENTRADA_FECHADO:
            clan_invites_collection.delete_many({
                "clan_id": cla["_id"],
            })

    membro_autor = _obter_membro(
        cla,
        player_id,
    ) or {}

    nomes_entrada = {
        TIPO_ENTRADA_SOLICITACAO:
            "Solicitações abertas",

        TIPO_ENTRADA_CONVITE:
            "Somente por convite",

        TIPO_ENTRADA_FECHADO:
            "Recrutamento fechado",
    }

    _registrar_atividade(
        clan_id=cla["_id"],
        tipo="configuracao",
        mensagem=(
            f"{membro_autor.get('nome', 'Aventureiro')} "
            "alterou as configurações do clã."
        ),
        autor_id=player_id,
        autor_nome=membro_autor.get(
            "nome",
            "Aventureiro",
        ),
        dados={
            "tipo_anterior": tipo_atual,
            "novo_tipo": tipo_novo,
            "nivel_minimo_anterior": nivel_atual,
            "novo_nivel_minimo": nivel_novo,
        },
    )

    return {
        "success": True,
        "message": "Configurações atualizadas com sucesso!",
        "descricao": descricao_nova,
        "configuracoes": {
            "tipo_entrada": tipo_novo,
            "tipo_entrada_nome": nomes_entrada[tipo_novo],
            "nivel_minimo": nivel_novo,
        },
    }

# ============================================================
# 📈 EVOLUÇÃO DO CLÃ
# ============================================================

def melhorar_cla(user_id):
    player_id = _object_id(user_id)

    if not player_id:
        return {
            "success": False,
            "error": "ID inválido.",
        }

    cla = obter_cla_do_jogador(player_id)

    if not cla:
        return {
            "success": False,
            "error": "Você não pertence a um clã.",
        }

    cargo = _cargo_no_cla(
        cla,
        player_id,
    )


    if not tem_permissao_cla(
        cla,
        cargo,
        PERMISSAO_MELHORAR_CLA,
    ):
        return {
            "success": False,
            "error": (
                "Seu cargo não permite "
                "melhorar o clã."
            ),
        }

    nivel_atual = int(cla.get("nivel", 1))
    proximo_nivel = obter_proximo_nivel(nivel_atual)

    if not proximo_nivel:
        return {
            "success": False,
            "error": "O clã já está no nível máximo.",
        }

    custo = obter_custo_evolucao(nivel_atual)

    xp_necessario = int(custo["xp"] or 0)
    ouro_necessario = int(custo["ouro"] or 0)

    xp_atual = int(cla.get("xp", 0))
    ouro_atual = int(
        cla.get("tesouro", {}).get("ouro", 0)
    )

    if xp_atual < xp_necessario:
        return {
            "success": False,
            "error": (
                f"XP insuficiente: "
                f"{xp_atual}/{xp_necessario}."
            ),
        }

    if ouro_atual < ouro_necessario:
        return {
            "success": False,
            "error": (
                f"Tesouro insuficiente: "
                f"{ouro_atual}/{ouro_necessario}."
            ),
        }

    nova_capacidade = obter_capacidade(
        proximo_nivel
    )

    resultado = clans_collection.update_one(
        {
            "_id": cla["_id"],
            "status": "ativo",
            "membros.user_id": player_id,
            "nivel": nivel_atual,
            "xp": {
                "$gte": xp_necessario
            },
            "tesouro.ouro": {
                "$gte": ouro_necessario
            },
        },
        {
            "$inc": {
                "xp": -xp_necessario,
                "tesouro.ouro": -ouro_necessario,
            },
            "$set": {
                "nivel": proximo_nivel,
                "capacidade_membros": nova_capacidade,
                "atualizado_em": _agora(),
            },
        },
    )

    if resultado.modified_count != 1:
        return {
            "success": False,
            "error": "Não foi possível melhorar o clã.",
        }

    membro_autor = _obter_membro(
        cla,
        player_id,
    ) or {}

    _registrar_atividade(
        clan_id=cla["_id"],
        tipo="evolucao",
        mensagem=(
            f"O clã alcançou o nível {proximo_nivel} "
            f"e agora suporta {nova_capacidade} membros."
        ),
        autor_id=player_id,
        autor_nome=membro_autor.get(
            "nome",
            "Aventureiro",
        ),
        dados={
            "nivel_anterior": nivel_atual,
            "novo_nivel": proximo_nivel,
            "nova_capacidade": nova_capacidade,
            "xp_gasto": xp_necessario,
            "ouro_gasto": ouro_necessario,
        },
    )

    return {
        "success": True,
        "message": (
            f"Clã elevado ao nível {proximo_nivel}! "
            f"Agora suporta {nova_capacidade} membros."
        ),
        "nivel": proximo_nivel,
        "capacidade_membros": nova_capacidade,
    }

# ============================================================
# 🎨 ALTERAR LOGO DO CLÃ
# ============================================================

def alterar_logo_cla(
    user_id,
    logo_id,
):
    player_id = _object_id(user_id)

    if not player_id:
        return {
            "success": False,
            "error": "ID de jogador inválido.",
        }

    logo_id = str(logo_id or "").strip()

    if not logo_valida(logo_id):
        return {
            "success": False,
            "error": "A logo selecionada é inválida.",
        }

    cla = obter_cla_do_jogador(player_id)

    if not cla:
        return {
            "success": False,
            "error": "Você não pertence a um clã.",
        }

    cargo = _cargo_no_cla(
        cla,
        player_id,
    )


    if not tem_permissao_cla(
        cla,
        cargo,
        PERMISSAO_ALTERAR_BRASAO,
    ):
        return {
            "success": False,
            "error": (
                "Seu cargo não permite alterar "
                "o brasão do clã."
            ),
        }

    if cla.get("logo_id") == logo_id:
        return {
            "success": True,
            "message": "Esta logo já está sendo utilizada.",
            "logo_id": logo_id,
            "logo_url": obter_logo_url(logo_id),
        }

    resultado = clans_collection.update_one(
        {
            "_id": cla["_id"],
            "status": "ativo",
            "membros.user_id": player_id,
        },
        {
            "$set": {
                "logo_id": logo_id,
                "atualizado_em": _agora(),
            }
        },
    )

    if resultado.modified_count != 1:
        return {
            "success": False,
            "error": "Não foi possível trocar a logo.",
        }

    membro_autor = _obter_membro(
        cla,
        player_id,
    ) or {}

    _registrar_atividade(
        clan_id=cla["_id"],
        tipo="logo",
        mensagem=(
            f"{membro_autor.get('nome', 'Aventureiro')} "
            f"alterou o brasão do clã."
        ),
        autor_id=player_id,
        autor_nome=membro_autor.get(
            "nome",
            "Aventureiro",
        ),
        dados={
            "logo_anterior": cla.get("logo_id"),
            "nova_logo": logo_id,
        },
    )

    return {
        "success": True,
        "message": "Logo do clã alterada com sucesso!",
        "logo_id": logo_id,
        "logo_url": obter_logo_url(logo_id),
    }

# ============================================================
# 💀 DISSOLVER CLÃ
# ============================================================

def dissolver_cla(user_id):
    player_id = _object_id(user_id)

    if not player_id:
        return {
            "success": False,
            "error": "ID inválido.",
        }

    cla = obter_cla_do_jogador(player_id)

    if not cla or cla.get("lider_id") != player_id:
        return {
            "success": False,
            "error": "Somente o líder pode dissolver o clã.",
        }

    membros_ids = [
        membro.get("user_id")
        for membro in cla.get("membros", [])
        if membro.get("user_id")
    ]

    users_collection.update_many(
        {
            "_id": {
                "$in": membros_ids
            },
            "clan_id": cla["_id"],
        },
        {
            "$set": {
                "clan_id": None,
            }
        },
    )

    clan_invites_collection.delete_many({
        "clan_id": cla["_id"]
    })

    clan_requests_collection.delete_many({
       "clan_id": cla["_id"]
    })


    # ========================================================
    # ⚔️ CANCELA A GUERRA DO CLÃ
    # ========================================================

    try:

        from modules.clan import (
            clan_war_manager,
        )


        clan_war_manager.cancelar_inscricao_cla_dissolvido(
            clan_id=cla["_id"]
        )


    except Exception as erro:

        print(
            "⚠️ [CLÃ/GUERRA] "
            "Não foi possível cancelar "
            "a inscrição da Guerra "
            "durante a dissolução: "
            f"{erro}"
        )


    clans_collection.delete_one({
        "_id": cla["_id"]
    })

    for membro_id in membros_ids:
        _limpar_cache(membro_id)

    return {
        "success": True,
        "message": "O clã foi dissolvido.",
    }