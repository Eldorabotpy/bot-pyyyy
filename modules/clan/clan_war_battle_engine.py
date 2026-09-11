# ============================================================
# ⚔️ MUNDO DE ELDORA - BATALHA DA GUERRA DE CLÃS
# ============================================================

from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)

from bson import ObjectId

from modules.player.core import (
    db,
    users_collection,
)

from modules.player.combat_stats import (
    get_combat_stats_sync,
)

from modules.combat.combat_engine import (
    processar_acao_combate,
)

from .clan_war_registry import (
    GUERRA_STATUS_EM_ANDAMENTO,
    GUERRA_STATUS_FINALIZADA,
)


# ============================================================
# 🗄️ COLEÇÃO
# ============================================================

clan_wars_collection = db[
    "clan_wars"
]


# ============================================================
# ⚔️ ESTADOS DA BATALHA
# ============================================================

BATALHA_STATUS_PREPARADA = (
    "preparada"
)

BATALHA_STATUS_FINALIZADA = (
    "finalizada"
)

# ============================================================
# 🔧 HELPERS
# ============================================================

def _agora():
    return datetime.now(
        timezone.utc
    )


def _object_id(
    valor,
):
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


def _localizar_frente(
    guerra,
    numero_frente,
):
    for frente in (
        guerra.get(
            "frentes",
            []
        )
        or []
    ):

        try:

            numero = int(
                frente.get(
                    "numero",
                    0
                )
                or 0
            )

        except (
            TypeError,
            ValueError,
        ):

            numero = 0


        if (
            numero
            ==
            numero_frente
        ):

            return frente


    return None

# ============================================================
# 💾 CAMPOS OFICIAIS DA FRENTE
# ============================================================

def _montar_campos_persistencia_batalha(
    batalha,
    agora,
    batalha_finalizada=False,
    vencedor_clan_id=None,
):
    """
    Monta os campos que serão persistidos
    na mesma atualização atômica da ação.

    Quando a batalha termina, registra também
    o resultado oficial da Frente.
    """

    campos = {

        "frentes.$.batalha":
            batalha,

        "atualizado_em":
            agora,
    }


    if batalha_finalizada:

        vencedor_id = _object_id(
            vencedor_clan_id
        )


        if vencedor_id:

            campos.update({

                "frentes.$.status":
                    GUERRA_STATUS_FINALIZADA,

                "frentes.$.resultado.vencedor_clan_id":
                    vencedor_id,

                "frentes.$.resultado.finalizada_em":
                    agora,
            })


    return campos

# ============================================================
# 🏆 CONSOLIDAR GUERRA APÓS FINALIZAR FRENTE
# ============================================================

def _consolidar_guerra_apos_finalizar_frente(
    guerra_id,
):
    """
    Solicita ao gerenciador oficial da Guerra
    que recalcule o placar geral depois que
    uma frente foi persistida como finalizada.

    Uma falha aqui NÃO desfaz o último ataque,
    pois o resultado da frente já foi salvo.
    """

    try:

        from modules.clan import (
            clan_war_manager,
        )


        resultado = (
            clan_war_manager
            .consolidar_resultado_guerra(
                guerra_id
            )
        )


        if not resultado.get(
            "success"
        ):

            print(
                "⚠️ [GUERRA DE CLÃS] "
                "A Frente terminou, mas o "
                "resultado geral da Guerra "
                "não pôde ser consolidado: "
                +
                str(
                    resultado.get(
                        "error",
                        "erro desconhecido",
                    )
                )
            )


        return resultado


    except Exception as erro:

        print(
            "⚠️ [GUERRA DE CLÃS] "
            "Erro ao consolidar resultado "
            "geral após finalizar Frente: "
            f"{erro}"
        )


        return {
            "success": False,
            "error": str(
                erro
            ),
        }
    
# ============================================================
# ⚔️ HELPERS DE TURNO DA BATALHA
# ============================================================

def _localizar_combatente(
    batalha,
    user_id,
):
    """
    Localiza um combatente dentro da batalha
    usando somente o ID oficial salvo no backend.
    """

    player_id = _object_id(
        user_id
    )


    if not player_id:

        return None


    for combatente in (
        batalha.get(
            "combatentes",
            []
        )
        or []
    ):

        if (
            _object_id(
                combatente.get(
                    "user_id"
                )
            )
            ==
            player_id
        ):

            return combatente


    return None


def _combatente_esta_vivo(
    combatente,
):
    """
    Consideramos o combatente vivo somente
    quando:

    - vivo != False
    - hp_atual > 0

    Isso protege contra estados antigos
    parcialmente atualizados.
    """

    if not combatente:

        return False


    if (
        combatente.get(
            "vivo",
            True
        )
        is False
    ):

        return False


    try:

        hp_atual = int(
            combatente.get(
                "hp_atual",
                0
            )
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):

        hp_atual = 0


    return (
        hp_atual >
        0
    )


def _eh_turno_jogador(
    batalha,
    user_id,
):
    """
    Validação oficial do turno.

    O frontend nunca decide isso.
    """

    player_id = _object_id(
        user_id
    )


    turno_user_id = _object_id(
        batalha.get(
            "turno_user_id"
        )
    )


    if (
        not player_id
        or
        not turno_user_id
    ):

        return False


    combatente = _localizar_combatente(
        batalha,
        player_id,
    )


    if not _combatente_esta_vivo(
        combatente
    ):

        return False


    return (
        player_id
        ==
        turno_user_id
    )


def _listar_inimigos_vivos(
    batalha,
    user_id,
):
    """
    Retorna somente inimigos vivos
    do jogador informado.

    Não permite selecionar aliado.
    """

    meu_combatente = (
        _localizar_combatente(
            batalha,
            user_id,
        )
    )


    if not meu_combatente:

        return []


    meu_lado = str(
        meu_combatente.get(
            "lado",
            ""
        )
        or ""
    ).lower()


    if meu_lado not in {
        "a",
        "b",
    }:

        return []


    inimigos = []


    for combatente in (
        batalha.get(
            "combatentes",
            []
        )
        or []
    ):

        lado = str(
            combatente.get(
                "lado",
                ""
            )
            or ""
        ).lower()


        if (
            lado ==
            meu_lado
        ):

            continue


        if not _combatente_esta_vivo(
            combatente
        ):

            continue


        inimigos.append({
            "user_id":
                str(
                    combatente.get(
                        "user_id"
                    )
                ),

            "clan_id":
                str(
                    combatente.get(
                        "clan_id"
                    )
                ),

            "lado":
                lado,

            "nome":
                combatente.get(
                    "nome",
                    "Aventureiro",
                ),

            "nivel":
                int(
                    combatente.get(
                        "nivel",
                        1
                    )
                    or 1
                ),

            "classe":
                combatente.get(
                    "classe",
                    "aventureiro",
                ),

            "hp_atual":
                int(
                    combatente.get(
                        "hp_atual",
                        0
                    )
                    or 0
                ),

            "hp_max":
                int(
                    (
                        combatente.get(
                            "stats",
                            {}
                        )
                        or {}
                    ).get(
                        "max_hp",
                        1
                    )
                    or 1
                ),
        })


    return inimigos


def _avancar_turno_batalha(
    batalha,
):
    """
    Avança para o próximo combatente vivo.

    - mantém a ordem de iniciativa original;
    - pula derrotados;
    - aumenta a rodada quando volta
      ao início da fila.

    Esta função altera somente o dicionário
    recebido em memória.

    A persistência no MongoDB será feita
    pela futura ação de combate.
    """

    ordem_turnos = (
        batalha.get(
            "ordem_turnos",
            []
        )
        or []
    )


    if not ordem_turnos:

        return None


    total = len(
        ordem_turnos
    )


    try:

        indice_atual = int(
            batalha.get(
                "turno_indice",
                0
            )
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):

        indice_atual = 0


    if (
        indice_atual < 0
        or
        indice_atual >= total
    ):

        indice_atual = 0


    for deslocamento in range(
        1,
        total + 1,
    ):

        indice_candidato = (
            indice_atual
            +
            deslocamento
        ) % total


        item_ordem = (
            ordem_turnos[
                indice_candidato
            ]
        )


        candidato_id = _object_id(
            item_ordem.get(
                "user_id"
            )
        )


        combatente = (
            _localizar_combatente(
                batalha,
                candidato_id,
            )
        )


        if not _combatente_esta_vivo(
            combatente
        ):

            continue


        # ====================================================
        # 🔄 COMPLETOU A VOLTA DA FILA
        # ====================================================

        passou_pelo_inicio = (
            indice_candidato
            <=
            indice_atual
        )


        if passou_pelo_inicio:

            batalha["rodada"] = (
                int(
                    batalha.get(
                        "rodada",
                        1
                    )
                    or 1
                )
                +
                1
            )


        batalha[
            "turno_indice"
        ] = indice_candidato


        batalha[
            "turno_user_id"
        ] = candidato_id


        # ====================================================
        # ⏳ COOLDOWN DA GUERRA
        #
        # Reduz somente quando ESTE combatente
        # recebe novamente o seu turno.
        #
        # iniciar_turno() trabalha somente com
        # combatente["cooldowns"].
        # ====================================================

        from modules.cooldowns import (
            iniciar_turno,
        )


        combatente[
            "cooldowns"
        ] = dict(
            combatente.get(
                "cooldowns",
                {}
            )
            or {}
        )


        combatente, mensagens_cd = (
            iniciar_turno(
                combatente
            )
        )


        return {
            "user_id":
                candidato_id,

            "indice":
                indice_candidato,

            "rodada":
                int(
                    batalha.get(
                        "rodada",
                        1
                    )
                    or 1
                ),

            "nome":
                combatente.get(
                    "nome",
                    "Aventureiro",
                ),

            "lado":
                combatente.get(
                    "lado"
                ),
            "cooldown_mensagens":
                mensagens_cd,                
        }


    return None

# ============================================================
# 👤 CRIAR COMBATENTE DA GUERRA
# ============================================================

def _criar_combatente(
    jogador_snapshot,
    clan_id,
    lado,
):
    player_id = _object_id(
        jogador_snapshot.get(
            "user_id"
        )
    )


    if not player_id:

        return None


    player_db = (
        users_collection
        .find_one({
            "_id":
                player_id
        })
    )


    if not player_db:

        return None


    stats = (
        get_combat_stats_sync(
            player_db
        )
        or {}
    )


    max_hp = max(
        1,
        int(
            stats.get(
                "max_hp",
                100
            )
            or 100
        ),
    )


    max_mana = max(
        0,
        int(
            stats.get(
                "max_mana",
                50
            )
            or 50
        ),
    )


    # ========================================================
    # ⚔️ REGRA DA GUERRA
    #
    # A batalha começa cheia.
    #
    # NÃO alteramos current_hp/current_mp
    # do personagem na coleção users.
    # Estes valores pertencem somente
    # ao estado isolado desta frente.
    # ========================================================

    return {

        "user_id":
            player_id,

        "clan_id":
            _object_id(
                clan_id
            ),

        "lado":
            lado,

        "nome":
            str(
                player_db.get(
                    "character_name"
                )
                or
                jogador_snapshot.get(
                    "nome"
                )
                or
                "Aventureiro"
            ),

        "nivel":
            int(
                player_db.get(
                    "level",
                    jogador_snapshot.get(
                        "nivel",
                        1
                    )
                )
                or 1
            ),

        "classe":
            str(
                player_db.get(
                    "class"
                )
                or
                jogador_snapshot.get(
                    "classe"
                )
                or
                "aventureiro"
            ),

        "stats": {

            "max_hp":
                max_hp,

            "max_mana":
                max_mana,

            "attack":
                int(
                    stats.get(
                        "attack",
                        5
                    )
                    or 0
                ),

            "defense":
                int(
                    stats.get(
                        "defense",
                        0
                    )
                    or 0
                ),

            "initiative":
                int(
                    stats.get(
                        "initiative",
                        5
                    )
                    or 0
                ),

            "luck":
                int(
                    stats.get(
                        "luck",
                        0
                    )
                    or 0
                ),

            "magic_attack":
                int(
                    stats.get(
                        "magic_attack",
                        0
                    )
                    or 0
                ),
            "armor_penetration":
                float(
                    stats.get(
                        "armor_penetration",
                        0.0
                    )
                    or 0.0
                ),

            "accuracy_flat":
                float(
                    stats.get(
                        "accuracy_flat",
                        0.0
                    )
                    or 0.0
                ),

            "crit_chance_flat":
                float(
                    stats.get(
                        "crit_chance_flat",
                        0.0
                    )
                    or 0.0
                ),

            "crit_damage_mult":
                float(
                    stats.get(
                        "crit_damage_mult",
                        0.0
                    )
                    or 0.0
                ),

            "double_attack_chance_flat":
                float(
                    stats.get(
                        "double_attack_chance_flat",
                        0.0
                    )
                    or 0.0
                ),

            "dodge_chance_flat":
                float(
                    stats.get(
                        "dodge_chance_flat",
                        0.0
                    )
                    or 0.0
                ),                
        },

        "hp_atual":
            max_hp,

        "mp_atual":
            max_mana,

        "vivo":
            True,

        "derrotado_em":
            None,

        # Cooldowns exclusivos desta batalha.
        # Nunca usamos os cooldowns normais
        # salvos no personagem.
        "cooldowns":
            {},
    }


# ============================================================
# ⚔️ GARANTIR ESTADO INICIAL DA BATALHA
# ============================================================

def garantir_batalha_inicial(
    guerra_id,
    numero_frente,
):
    """
    Cria de forma idempotente o estado
    inicial da batalha 5x5.

    Esta etapa:
    - valida a guerra;
    - exige lobby pronto;
    - carrega os 10 personagens reais;
    - calcula status oficiais;
    - ordena por iniciativa;
    - define quem será o primeiro turno.

    NÃO processa ataques.
    """

    guerra_id = _object_id(
        guerra_id
    )


    if not guerra_id:

        return {
            "success": False,
            "error": "Guerra inválida.",
        }


    try:

        numero_frente = int(
            numero_frente
        )

    except (
        TypeError,
        ValueError,
    ):

        return {
            "success": False,
            "error": "Frente inválida.",
        }


    if numero_frente <= 0:

        return {
            "success": False,
            "error": "Frente inválida.",
        }


    # ========================================================
    # ⚔️ BUSCA ESTADO MAIS RECENTE
    # ========================================================

    guerra = (
        clan_wars_collection
        .find_one({
            "_id":
                guerra_id
        })
    )


    if not guerra:

        return {
            "success": False,
            "error": "Guerra não encontrada.",
        }


    if (
        guerra.get(
            "status"
        )
        !=
        GUERRA_STATUS_EM_ANDAMENTO
    ):

        return {
            "success": False,

            "error": (
                "A Guerra de Clãs não está "
                "em andamento."
            ),
        }


    frente = _localizar_frente(
        guerra,
        numero_frente,
    )


    if not frente:

        return {
            "success": False,
            "error": "Frente não encontrada.",
        }


    # ========================================================
    # 🔁 JÁ FOI CRIADA
    # ========================================================

    batalha_existente = (
        frente.get(
            "batalha",
            {}
        )
        or {}
    )


    if batalha_existente.get(
        "estado"
    ):

        return {
            "success": True,

            "ja_existia":
                True,

            "batalha":
                batalha_existente,
        }


    # ========================================================
    # ✅ FRENTE PRECISA ESTAR PRONTA
    # ========================================================

    lobby = (
        frente.get(
            "lobby",
            {}
        )
        or {}
    )


    if (
        lobby.get(
            "estado"
        )
        !=
        "pronta_para_combate"
    ):

        return {
            "success": False,

            "error": (
                "A frente ainda não está "
                "pronta para combate."
            ),
        }


    # ========================================================
    # 👥 TITULARES DOS DOIS CLÃS
    # ========================================================

    lado_a = (
        frente.get(
            "clan_a",
            {}
        )
        or {}
    )


    lado_b = (
        frente.get(
            "clan_b",
            {}
        )
        or {}
    )


    jogadores_a = (
        lado_a.get(
            "jogadores",
            []
        )
        or []
    )


    jogadores_b = (
        lado_b.get(
            "jogadores",
            []
        )
        or []
    )


    if (
        len(
            jogadores_a
        )
        != 5
        or
        len(
            jogadores_b
        )
        != 5
    ):

        return {
            "success": False,

            "error": (
                "A frente precisa possuir "
                "exatamente 5 jogadores "
                "de cada clã."
            ),
        }


    # ========================================================
    # ✅ CONFERE OS 10 PRONTOS
    # ========================================================

    titulares_ids = set()


    for jogador in (
        jogadores_a
        +
        jogadores_b
    ):

        jogador_id = _object_id(
            jogador.get(
                "user_id"
            )
        )


        if jogador_id:

            titulares_ids.add(
                jogador_id
            )


    prontos_ids = {

        _object_id(
            valor
        )

        for valor
        in (
            lobby.get(
                "prontos_ids",
                []
            )
            or []
        )

        if _object_id(
            valor
        )
    }


    if (
        len(
            titulares_ids
        )
        != 10
        or
        not titulares_ids.issubset(
            prontos_ids
        )
    ):

        return {
            "success": False,

            "error": (
                "Os 10 titulares ainda não "
                "confirmaram PRONTO."
            ),
        }


    # ========================================================
    # ⚔️ MONTA OS 10 COMBATENTES
    # ========================================================

    combatentes = []


    for jogador in jogadores_a:

        combatente = _criar_combatente(

            jogador_snapshot=
                jogador,

            clan_id=
                lado_a.get(
                    "clan_id"
                ),

            lado=
                "a",
        )


        if not combatente:

            return {
                "success": False,

                "error": (
                    "Um dos jogadores do Clã A "
                    "não foi encontrado."
                ),
            }


        combatentes.append(
            combatente
        )


    for jogador in jogadores_b:

        combatente = _criar_combatente(

            jogador_snapshot=
                jogador,

            clan_id=
                lado_b.get(
                    "clan_id"
                ),

            lado=
                "b",
        )


        if not combatente:

            return {
                "success": False,

                "error": (
                    "Um dos jogadores do Clã B "
                    "não foi encontrado."
                ),
            }


        combatentes.append(
            combatente
        )


    # ========================================================
    # 🎲 ORDEM OFICIAL DE INICIATIVA
    #
    # Maior iniciativa joga primeiro.
    #
    # Empate:
    # usamos user_id somente como critério
    # determinístico para que dois pedidos
    # simultâneos não gerem ordens diferentes.
    # ========================================================

    combatentes.sort(

        key=lambda item: (

            -int(
                (
                    item.get(
                        "stats",
                        {}
                    )
                    or {}
                ).get(
                    "initiative",
                    0
                )
                or 0
            ),

            str(
                item.get(
                    "user_id"
                )
            ),
        )
    )


    ordem_turnos = []


    for (
        indice,
        combatente
    ) in enumerate(
        combatentes,
        start=1,
    ):

        ordem_turnos.append({

            "posicao":
                indice,

            "user_id":
                combatente[
                    "user_id"
                ],

            "clan_id":
                combatente[
                    "clan_id"
                ],

            "lado":
                combatente[
                    "lado"
                ],

            "nome":
                combatente[
                    "nome"
                ],

            "initiative":
                int(
                    combatente[
                        "stats"
                    ].get(
                        "initiative",
                        0
                    )
                    or 0
                ),
        })


    primeiro = (
        ordem_turnos[
            0
        ]
    )


    agora = _agora()


    batalha = {

        "estado":
            BATALHA_STATUS_PREPARADA,

        "rodada":
            1,

        "turno_indice":
            0,

        "turno_user_id":
            primeiro[
                "user_id"
            ],

        "ordem_turnos":
            ordem_turnos,

        "combatentes":
            combatentes,

        "criada_em":
            agora,

        "iniciada_em":
            None,

        "finalizada_em":
            None,

        "vencedor_clan_id":
            None,

        "log":
            [],
    }


    # ========================================================
    # 💾 CRIAÇÃO ATÔMICA
    #
    # Apenas uma requisição pode criar
    # a batalha pela primeira vez.
    # ========================================================

    resultado = (
        clan_wars_collection
        .update_one(

            {
                "_id":
                    guerra_id,

                "frentes": {
                    "$elemMatch": {

                        "numero":
                            numero_frente,

                        "lobby.estado":
                            "pronta_para_combate",

                        "batalha.estado": {
                            "$exists":
                                False
                        },
                    }
                },
            },

            {
                "$set": {

                    "frentes.$.batalha":
                        batalha,

                    "atualizado_em":
                        agora,
                }
            },
        )
    )


    # ========================================================
    # 🔁 OUTRA REQUISIÇÃO PODE TER CRIADO PRIMEIRO
    # ========================================================

    if (
        resultado.modified_count
        != 1
    ):

        guerra_atual = (
            clan_wars_collection
            .find_one({
                "_id":
                    guerra_id
            })
            or {}
        )


        frente_atual = _localizar_frente(
            guerra_atual,
            numero_frente,
        )


        batalha_atual = (
            (
                frente_atual
                or {}
            ).get(
                "batalha",
                {}
            )
            or {}
        )


        if batalha_atual.get(
            "estado"
        ):

            return {
                "success": True,

                "ja_existia":
                    True,

                "batalha":
                    batalha_atual,
            }


        return {
            "success": False,

            "error": (
                "Não foi possível criar "
                "a batalha desta frente."
            ),
        }


    return {
        "success": True,

        "ja_existia":
            False,

        "batalha":
            batalha,
    }

# ============================================================
# 🎯 CONTEXTO OFICIAL DO TURNO DO JOGADOR
# ============================================================

def obter_contexto_turno_jogador(
    user_id,
):
    """
    Retorna o contexto oficial do jogador
    na batalha ativa da Guerra de Clãs.

    NÃO executa ataques.
    NÃO avança turno.
    NÃO altera HP.
    """

    player_id = _object_id(
        user_id
    )


    if not player_id:

        return {
            "success": False,
            "error": "Jogador inválido.",
        }


    # ========================================================
    # 🔎 LOCALIZA A GUERRA PELO PRÓPRIO COMBATENTE
    #
    # O jogador NÃO informa guerra, frente nem lado.
    # ========================================================

    guerra = (
        clan_wars_collection
        .find_one({

            "status":
                GUERRA_STATUS_EM_ANDAMENTO,

            "frentes.batalha.combatentes.user_id":
                player_id,
        })
    )


    if not guerra:

        return {
            "success": False,

            "error": (
                "Você não possui uma batalha "
                "ativa na Guerra de Clãs."
            ),
        }


    frente_encontrada = None


    for frente in (
        guerra.get(
            "frentes",
            []
        )
        or []
    ):

        batalha = (
            frente.get(
                "batalha",
                {}
            )
            or {}
        )


        if _localizar_combatente(
            batalha,
            player_id,
        ):

            frente_encontrada = frente
            break


    if not frente_encontrada:

        return {
            "success": False,

            "error":
                "Frente da batalha não encontrada.",
        }


    batalha = (
        frente_encontrada.get(
            "batalha",
            {}
        )
        or {}
    )


    meu_combatente = (
        _localizar_combatente(
            batalha,
            player_id,
        )
    )


    if not meu_combatente:

        return {
            "success": False,

            "error":
                "Combatente não encontrado.",
        }


    turno_user_id = _object_id(
        batalha.get(
            "turno_user_id"
        )
    )


    combatente_turno = (
        _localizar_combatente(
            batalha,
            turno_user_id,
        )
        if turno_user_id
        else None
    )


    return {
        "success": True,

        "guerra_id":
            str(
                guerra["_id"]
            ),

        "frente_numero":
            int(
                frente_encontrada.get(
                    "numero",
                    0
                )
                or 0
            ),

        "estado":
            batalha.get(
                "estado"
            ),

        "rodada":
            int(
                batalha.get(
                    "rodada",
                    1
                )
                or 1
            ),

        "turno_indice":
            int(
                batalha.get(
                    "turno_indice",
                    0
                )
                or 0
            ),

        "meu_turno":
            _eh_turno_jogador(
                batalha,
                player_id,
            ),

        "estou_vivo":
            _combatente_esta_vivo(
                meu_combatente
            ),

        "meu_lado":
            meu_combatente.get(
                "lado"
            ),

        "turno_atual": {

            "user_id":
                (
                    str(
                        combatente_turno.get(
                            "user_id"
                        )
                    )
                    if combatente_turno
                    else None
                ),

            "nome":
                (
                    combatente_turno.get(
                        "nome",
                        "Aventureiro",
                    )
                    if combatente_turno
                    else None
                ),

            "lado":
                (
                    combatente_turno.get(
                        "lado"
                    )
                    if combatente_turno
                    else None
                ),
        },

        "alvos_validos":
            (
                _listar_inimigos_vivos(
                    batalha,
                    player_id,
                )
                if _eh_turno_jogador(
                    batalha,
                    player_id,
                )
                else []
            ),
    }

# ============================================================
# 🎯 ESTADO DO TURNO PARA O JOGADOR
# ============================================================

def obter_estado_turno_jogador(
    user_id,
):
    """
    Localiza a batalha ativa da Guerra de Clãs
    em que o jogador participa e informa o
    estado oficial do turno.

    Esta função NÃO executa ações.
    """

    player_id = _object_id(
        user_id
    )


    if not player_id:

        return {
            "success": False,
            "error": "ID de jogador inválido.",
        }


    # ========================================================
    # 🔎 LOCALIZA GUERRA/FRENTE PELO COMBATENTE
    # ========================================================

    guerra = (
        clan_wars_collection
        .find_one({

            "status":
                GUERRA_STATUS_EM_ANDAMENTO,

            "frentes.batalha.combatentes.user_id":
                player_id,
        })
    )


    if not guerra:

        return {
            "success": False,

            "error": (
                "Nenhuma batalha ativa da "
                "Guerra de Clãs foi encontrada "
                "para este jogador."
            ),
        }


    frente_encontrada = None


    for frente in (
        guerra.get(
            "frentes",
            []
        )
        or []
    ):

        batalha = (
            frente.get(
                "batalha",
                {}
            )
            or {}
        )


        combatentes = (
            batalha.get(
                "combatentes",
                []
            )
            or []
        )


        pertence = any(

            _object_id(
                combatente.get(
                    "user_id"
                )
            )
            ==
            player_id

            for combatente
            in combatentes
        )


        if pertence:

            frente_encontrada = frente
            break


    if not frente_encontrada:

        return {
            "success": False,

            "error": (
                "A frente do jogador "
                "não foi encontrada."
            ),
        }


    batalha = (
        frente_encontrada.get(
            "batalha",
            {}
        )
        or {}
    )


    if (
        batalha.get(
            "estado"
        )
        !=
        BATALHA_STATUS_PREPARADA
    ):

        return {
            "success": False,

            "error": (
                "A batalha desta frente "
                "não está preparada."
            ),
        }


    # ========================================================
    # 👤 COMBATENTE DO JOGADOR
    # ========================================================

    meu_combatente = next(
        (
            combatente

            for combatente
            in (
                batalha.get(
                    "combatentes",
                    []
                )
                or []
            )

            if _object_id(
                combatente.get(
                    "user_id"
                )
            )
            ==
            player_id
        ),

        None,
    )


    if not meu_combatente:

        return {
            "success": False,

            "error": (
                "O jogador não pertence "
                "a esta batalha."
            ),
        }


    # ========================================================
    # ⚡ ORDEM OFICIAL
    # ========================================================

    ordem_turnos = (
        batalha.get(
            "ordem_turnos",
            []
        )
        or []
    )


    turno_user_id = _object_id(
        batalha.get(
            "turno_user_id"
        )
    )


    turno_indice = int(
        batalha.get(
            "turno_indice",
            0
        )
        or 0
    )


    rodada = int(
        batalha.get(
            "rodada",
            1
        )
        or 1
    )


    turno_atual = None


    if (
        0 <= turno_indice <
        len(
            ordem_turnos
        )
    ):

        turno_atual = (
            ordem_turnos[
                turno_indice
            ]
        )


    # Segurança:
    # turno_user_id continua sendo a
    # autoridade principal.
    if not turno_atual:

        turno_atual = next(
            (
                item

                for item
                in ordem_turnos

                if _object_id(
                    item.get(
                        "user_id"
                    )
                )
                ==
                turno_user_id
            ),

            None,
        )


    # ========================================================
    # 📍 POSIÇÃO DO PRÓPRIO JOGADOR
    # ========================================================

    minha_ordem = next(
        (
            item

            for item
            in ordem_turnos

            if _object_id(
                item.get(
                    "user_id"
                )
            )
            ==
            player_id
        ),

        None,
    )


    vivo = bool(
        meu_combatente.get(
            "vivo",
            True
        )
    )


    meu_turno = bool(
        vivo
        and
        turno_user_id
        ==
        player_id
    )


    # ========================================================
    # 📤 RESPOSTA SEGURA
    # ========================================================

    return {
        "success": True,

        "guerra_id":
            str(
                guerra["_id"]
            ),

        "frente_numero":
            int(
                frente_encontrada.get(
                    "numero",
                    0
                )
                or 0
            ),

        "batalha_estado":
            batalha.get(
                "estado"
            ),

        "rodada":
            rodada,

        "turno_indice":
            turno_indice,

        "meu_turno":
            meu_turno,

        "estou_vivo":
            vivo,

        "meu_lado":
            meu_combatente.get(
                "lado"
            ),

        "minha_posicao":
            (
                int(
                    minha_ordem.get(
                        "posicao",
                        0
                    )
                    or 0
                )

                if minha_ordem
                else 0
            ),

        "turno_atual": {

            "user_id":
                (
                    str(
                        turno_atual.get(
                            "user_id"
                        )
                    )
                    if turno_atual
                    else None
                ),

            "nome":
                (
                    turno_atual.get(
                        "nome"
                    )
                    if turno_atual
                    else None
                ),

            "lado":
                (
                    turno_atual.get(
                        "lado"
                    )
                    if turno_atual
                    else None
                ),

            "posicao":
                (
                    int(
                        turno_atual.get(
                            "posicao",
                            0
                        )
                        or 0
                    )
                    if turno_atual
                    else 0
                ),

            "initiative":
                (
                    int(
                        turno_atual.get(
                            "initiative",
                            0
                        )
                        or 0
                    )
                    if turno_atual
                    else 0
                ),
        },
    }

# ============================================================
# ⚔️ ATAQUE BÁSICO — GUERRA DE CLÃS
# ============================================================

async def executar_ataque_basico(
    user_id,
    alvo_id,
):
    """
    Executa UMA ação de ataque básico na
    batalha 5x5 da Guerra de Clãs.

    O frontend informa somente:
    - quem está tentando agir;
    - alvo desejado.

    Todo o restante é validado no servidor.
    """

    player_id = _object_id(
        user_id
    )

    target_id = _object_id(
        alvo_id
    )


    if not player_id:

        return {
            "success": False,
            "error": "Jogador inválido.",
        }


    if not target_id:

        return {
            "success": False,
            "error": "Alvo inválido.",
        }


    # ========================================================
    # 🔎 LOCALIZA A GUERRA DO ATACANTE
    # ========================================================

    guerra = (
        clan_wars_collection
        .find_one({

            "status":
                GUERRA_STATUS_EM_ANDAMENTO,

            "frentes.batalha.combatentes.user_id":
                player_id,
        })
    )


    if not guerra:

        return {
            "success": False,

            "error": (
                "Nenhuma batalha ativa foi "
                "encontrada para este jogador."
            ),
        }


    # ========================================================
    # ⚔️ LOCALIZA A FRENTE
    # ========================================================

    frente_encontrada = None


    for frente in (
        guerra.get(
            "frentes",
            []
        )
        or []
    ):

        batalha_teste = (
            frente.get(
                "batalha",
                {}
            )
            or {}
        )


        if _localizar_combatente(
            batalha_teste,
            player_id,
        ):

            frente_encontrada = frente
            break


    if not frente_encontrada:

        return {
            "success": False,
            "error": "Frente não encontrada.",
        }


    numero_frente = int(
        frente_encontrada.get(
            "numero",
            0
        )
        or 0
    )


    batalha = (
        frente_encontrada.get(
            "batalha",
            {}
        )
        or {}
    )


    if (
        batalha.get(
            "estado"
        )
        !=
        BATALHA_STATUS_PREPARADA
    ):

        return {
            "success": False,

            "error": (
                "Esta batalha não aceita "
                "novas ações."
            ),
        }


    # ========================================================
    # 🔒 TURNO É AUTORIDADE DO BACKEND
    # ========================================================

    if not _eh_turno_jogador(
        batalha,
        player_id,
    ):

        turno_id = _object_id(
            batalha.get(
                "turno_user_id"
            )
        )


        combatente_turno = (
            _localizar_combatente(
                batalha,
                turno_id,
            )
            if turno_id
            else None
        )


        return {
            "success": False,

            "error": (
                "Não é o seu turno."
                +
                (
                    (
                        " Turno atual: "
                        +
                        str(
                            combatente_turno.get(
                                "nome",
                                "Aventureiro",
                            )
                        )
                        +
                        "."
                    )
                    if combatente_turno
                    else ""
                )
            ),
        }


    atacante = _localizar_combatente(
        batalha,
        player_id,
    )


    alvo = _localizar_combatente(
        batalha,
        target_id,
    )


    if not atacante:

        return {
            "success": False,
            "error": "Atacante não encontrado.",
        }


    if not _combatente_esta_vivo(
        atacante
    ):

        return {
            "success": False,
            "error": "Você foi derrotado.",
        }


    if not alvo:

        return {
            "success": False,
            "error": "Alvo não pertence à batalha.",
        }


    if not _combatente_esta_vivo(
        alvo
    ):

        return {
            "success": False,
            "error": "Este alvo já foi derrotado.",
        }


    lado_atacante = str(
        atacante.get(
            "lado",
            ""
        )
        or ""
    ).lower()


    lado_alvo = str(
        alvo.get(
            "lado",
            ""
        )
        or ""
    ).lower()


    if (
        lado_atacante
        not in {
            "a",
            "b",
        }
        or
        lado_alvo
        not in {
            "a",
            "b",
        }
    ):

        return {
            "success": False,
            "error": "Lado da batalha inválido.",
        }


    if (
        lado_atacante
        ==
        lado_alvo
    ):

        return {
            "success": False,
            "error": "Você não pode atacar um aliado.",
        }


    # ========================================================
    # 📌 ESTADO ANTES DA AÇÃO
    #
    # Usado também na trava contra duplo clique.
    # ========================================================

    turno_indice_antes = int(
        batalha.get(
            "turno_indice",
            0
        )
        or 0
    )


    hp_alvo_antes = int(
        alvo.get(
            "hp_atual",
            0
        )
        or 0
    )


    # ========================================================
    # 👤 DADOS REAIS DO PERSONAGEM
    #
    # combat_engine precisa do player_data para
    # regras como arma/durabilidade.
    #
    # Os atributos de dano continuam sendo os
    # atributos congelados na batalha.
    # ========================================================

    atacante_db = (
        users_collection
        .find_one({
            "_id":
                player_id
        })
    )


    if not atacante_db:

        return {
            "success": False,
            "error": "Dados do atacante não encontrados.",
        }


    attacker_stats = dict(
        atacante.get(
            "stats",
            {}
        )
        or {}
    )


    target_stats = dict(
        alvo.get(
            "stats",
            {}
        )
        or {}
    )


    # Também deixamos o HP atual disponível
    # ao motor para efeitos futuros.
    target_stats[
        "hp"
    ] = hp_alvo_antes


    target_stats[
        "max_hp"
    ] = int(
        target_stats.get(
            "max_hp",
            hp_alvo_antes,
        )
        or hp_alvo_antes
        or 1
    )


    # ========================================================
    # ⚔️ MOTOR OFICIAL DO COMBATE
    # ========================================================

    resultado_motor = (
        await processar_acao_combate(

            attacker_pdata=
                atacante_db,

            attacker_stats=
                attacker_stats,

            target_stats=
                target_stats,

            # None = ataque básico oficial
            skill_id=
                None,

            attacker_current_hp=
                int(
                    atacante.get(
                        "hp_atual",
                        0
                    )
                    or 0
                ),

            attacker_current_mp=
                int(
                    atacante.get(
                        "mp_atual",
                        0
                    )
                    or 0
                ),
        )
    )


    dano = max(
        0,
        int(
            resultado_motor.get(
                "total_damage",
                0
            )
            or 0
        ),
    )


    numero_golpes = max(
        1,
        int(
            resultado_motor.get(
                "num_hits",
                1
            )
            or 1
        ),
    )


    mensagens_motor = [
        str(
            mensagem
        )

        for mensagem
        in (
            resultado_motor.get(
                "log_messages",
                []
            )
            or []
        )
    ]


    # ========================================================
    # ❤️ APLICA DANO SOMENTE NA BATALHA DA GUERRA
    # ========================================================

    hp_alvo_depois = max(
        0,
        hp_alvo_antes
        -
        dano,
    )


    alvo[
        "hp_atual"
    ] = hp_alvo_depois


    alvo_derrotado = (
        hp_alvo_depois
        <= 0
    )


    agora = _agora()


    if alvo_derrotado:

        alvo[
            "vivo"
        ] = False

        alvo[
            "derrotado_em"
        ] = agora


    # Ataque básico normalmente não consome MP,
    # mas mantemos o retorno oficial do motor.
    mp_max_atacante = max(
        0,
        int(
            attacker_stats.get(
                "max_mana",
                0
            )
            or 0
        ),
    )


    atacante[
        "mp_atual"
    ] = max(
        0,
        min(
            mp_max_atacante,
            int(
                resultado_motor.get(
                    "attacker_mp_left",
                    atacante.get(
                        "mp_atual",
                        0
                    ),
                )
                or 0
            ),
        ),
    )


    if not batalha.get(
        "iniciada_em"
    ):

        batalha[
            "iniciada_em"
        ] = agora


    # ========================================================
    # 📜 REGISTRO DA AÇÃO
    # ========================================================

    acao_id = str(
        ObjectId()
    )


    evento = {

        "acao_id":
            acao_id,

        "tipo":
            "ataque_basico",

        "rodada":
            int(
                batalha.get(
                    "rodada",
                    1
                )
                or 1
            ),

        "atacante_id":
            str(
                player_id
            ),

        "atacante_nome":
            atacante.get(
                "nome",
                "Aventureiro",
            ),

        "atacante_lado":
            lado_atacante,

        "alvo_id":
            str(
                target_id
            ),

        "alvo_nome":
            alvo.get(
                "nome",
                "Aventureiro",
            ),

        "alvo_lado":
            lado_alvo,

        "dano":
            dano,

        "numero_golpes":
            numero_golpes,

        "hp_antes":
            hp_alvo_antes,

        "hp_depois":
            hp_alvo_depois,

        "alvo_derrotado":
            alvo_derrotado,

        "mensagens":
            mensagens_motor,

        "criado_em":
            agora,
    }


    log_atual = (
        batalha.get(
            "log",
            []
        )
        or []
    )


    batalha[
        "log"
    ] = (
        log_atual
        +
        [
            evento
        ]
    )[-80:]


    # ========================================================
    # 🏆 VERIFICA SE TODO O LADO INIMIGO CAIU
    # ========================================================

    ainda_existe_inimigo = any(

        (
            str(
                combatente.get(
                    "lado",
                    ""
                )
                or ""
            ).lower()
            ==
            lado_alvo
        )
        and
        _combatente_esta_vivo(
            combatente
        )

        for combatente
        in (
            batalha.get(
                "combatentes",
                []
            )
            or []
        )
    )


    batalha_finalizada = (
        not ainda_existe_inimigo
    )


    proximo_turno = None


    if batalha_finalizada:

        batalha[
            "estado"
        ] = (
            BATALHA_STATUS_FINALIZADA
        )

        batalha[
            "finalizada_em"
        ] = agora

        batalha[
            "vencedor_clan_id"
        ] = atacante.get(
            "clan_id"
        )

        batalha[
            "turno_user_id"
        ] = None

        batalha[
            "turno_indice"
        ] = -1


    else:

        proximo_turno = (
            _avancar_turno_batalha(
                batalha
            )
        )


        if not proximo_turno:

            return {
                "success": False,

                "error": (
                    "Não foi possível localizar "
                    "o próximo combatente vivo."
                ),
            }


    # ========================================================
    # 🔒 GRAVAÇÃO ATÔMICA
    #
    # A requisição só vence se:
    # - ainda for o turno do mesmo jogador;
    # - estiver no mesmo índice;
    # - o alvo ainda tiver o mesmo HP.
    #
    # Isso bloqueia duplo clique.
    # ========================================================

    resultado_update = (
        clan_wars_collection
        .update_one(

            {
                "_id":
                    guerra["_id"],

                "status":
                    GUERRA_STATUS_EM_ANDAMENTO,

                "frentes": {
                    "$elemMatch": {

                        "numero":
                            numero_frente,

                        "batalha.estado":
                            BATALHA_STATUS_PREPARADA,

                        "batalha.turno_user_id":
                            player_id,

                        "batalha.turno_indice":
                            turno_indice_antes,

                        "batalha.combatentes": {
                            "$elemMatch": {

                                "user_id":
                                    target_id,

                                "hp_atual":
                                    hp_alvo_antes,

                                "vivo":
                                    True,
                            }
                        },
                    }
                },
            },

            {
                "$set":
                    _montar_campos_persistencia_batalha(

                        batalha=
                            batalha,

                        agora=
                            agora,

                        batalha_finalizada=
                            batalha_finalizada,

                        vencedor_clan_id=
                            atacante.get(
                                "clan_id"
                            ),
                    )
            },
        )
    )


    if (
        resultado_update.modified_count
        != 1
    ):

        return {
            "success": False,

            "error": (
                "O estado da batalha mudou "
                "antes da ação ser concluída. "
                "Atualize a batalha."
            ),

            "recarregar":
                True,
        }

    # ========================================================
    # 🏆 ATUALIZA RESULTADO GERAL DA GUERRA
    # ========================================================

    resultado_guerra = None


    if batalha_finalizada:

        resultado_guerra = (
            _consolidar_guerra_apos_finalizar_frente(
                guerra["_id"]
            )
        )
        
    # ========================================================
    # 📤 RESPOSTA
    # ========================================================

    proximo_serializado = None


    if proximo_turno:

        proximo_serializado = {

            "user_id":
                str(
                    proximo_turno.get(
                        "user_id"
                    )
                ),

            "nome":
                proximo_turno.get(
                    "nome"
                ),

            "lado":
                proximo_turno.get(
                    "lado"
                ),

            "indice":
                int(
                    proximo_turno.get(
                        "indice",
                        0
                    )
                    or 0
                ),

            "rodada":
                int(
                    proximo_turno.get(
                        "rodada",
                        1
                    )
                    or 1
                ),
        }


    return {
        "success": True,

        "acao": {

            "acao_id":
                acao_id,

            "tipo":
                "ataque_basico",

            "atacante_id":
                str(
                    player_id
                ),

            "atacante_nome":
                atacante.get(
                    "nome",
                    "Aventureiro",
                ),

            "atacante_lado":
                lado_atacante,

            "alvo_id":
                str(
                    target_id
                ),

            "alvo_nome":
                alvo.get(
                    "nome",
                    "Aventureiro",
                ),

            "alvo_lado":
                lado_alvo,

            "dano":
                dano,

            "numero_golpes":
                numero_golpes,

            "hp_antes":
                hp_alvo_antes,

            "hp_depois":
                hp_alvo_depois,

            "alvo_derrotado":
                alvo_derrotado,

            "mensagens":
                mensagens_motor,
        },

        "rodada":
            int(
                batalha.get(
                    "rodada",
                    1
                )
                or 1
            ),

        "proximo_turno":
            proximo_serializado,

        "batalha_finalizada":
            batalha_finalizada,

        "vencedor_clan_id":
            (
                str(
                    atacante.get(
                        "clan_id"
                    )
                )
                if batalha_finalizada
                else None
            ),
    }

# ============================================================
# ✨ SKILL OFENSIVA — GUERRA DE CLÃS
# ============================================================

async def executar_skill_ofensiva(
    user_id,
    alvo_id,
    skill_id,
):
    """
    Executa uma skill ofensiva na Guerra.

    - somente skill equipada;
    - somente no turno oficial;
    - somente inimigo vivo;
    - MP isolado da Guerra;
    - cooldown isolado da Guerra;
    - cálculo pelo combat_engine oficial.
    """

    from modules.game_data.skills import (
        get_skill_data_with_rarity,
    )

    from modules.cooldowns import (
        verificar_cooldown,
    )


    player_id = _object_id(
        user_id
    )


    target_id = _object_id(
        alvo_id
    )


    skill_id = str(
        skill_id or ""
    ).strip()


    if not player_id:

        return {
            "success": False,
            "error": "Jogador inválido.",
        }


    if not target_id:

        return {
            "success": False,
            "error": "Alvo inválido.",
        }


    if not skill_id:

        return {
            "success": False,
            "error": "Skill não informada.",
        }


    # ========================================================
    # 🔎 GUERRA ATIVA
    # ========================================================

    guerra = (
        clan_wars_collection
        .find_one({

            "status":
                GUERRA_STATUS_EM_ANDAMENTO,

            "frentes.batalha.combatentes.user_id":
                player_id,
        })
    )


    if not guerra:

        return {
            "success": False,

            "error": (
                "Nenhuma batalha ativa "
                "foi encontrada."
            ),
        }


    # ========================================================
    # ⚔️ FRENTE DO JOGADOR
    # ========================================================

    frente_encontrada = None


    for frente in (
        guerra.get(
            "frentes",
            []
        )
        or []
    ):

        batalha_teste = (
            frente.get(
                "batalha",
                {}
            )
            or {}
        )


        if _localizar_combatente(
            batalha_teste,
            player_id,
        ):

            frente_encontrada = frente
            break


    if not frente_encontrada:

        return {
            "success": False,
            "error": "Frente não encontrada.",
        }


    numero_frente = int(
        frente_encontrada.get(
            "numero",
            0
        )
        or 0
    )


    batalha = (
        frente_encontrada.get(
            "batalha",
            {}
        )
        or {}
    )


    if (
        batalha.get(
            "estado"
        )
        !=
        BATALHA_STATUS_PREPARADA
    ):

        return {
            "success": False,

            "error": (
                "Esta batalha não aceita "
                "novas ações."
            ),
        }


    # ========================================================
    # 🔒 TURNO
    # ========================================================

    if not _eh_turno_jogador(
        batalha,
        player_id,
    ):

        return {
            "success": False,
            "error": "Não é o seu turno.",
        }


    atacante = _localizar_combatente(
        batalha,
        player_id,
    )


    alvo = _localizar_combatente(
        batalha,
        target_id,
    )


    if not atacante:

        return {
            "success": False,
            "error": "Atacante não encontrado.",
        }


    if not alvo:

        return {
            "success": False,
            "error": "Alvo não encontrado.",
        }


    if not _combatente_esta_vivo(
        atacante
    ):

        return {
            "success": False,
            "error": "Você foi derrotado.",
        }


    if not _combatente_esta_vivo(
        alvo
    ):

        return {
            "success": False,
            "error": "Este alvo já foi derrotado.",
        }


    lado_atacante = str(
        atacante.get(
            "lado",
            ""
        )
        or ""
    ).lower()


    lado_alvo = str(
        alvo.get(
            "lado",
            ""
        )
        or ""
    ).lower()


    if (
        lado_atacante
        ==
        lado_alvo
    ):

        return {
            "success": False,

            "error": (
                "Skill ofensiva não pode "
                "ser usada em aliado."
            ),
        }


    # ========================================================
    # 👤 FICHA REAL
    # ========================================================

    atacante_db_original = (
        users_collection
        .find_one({
            "_id":
                player_id
        })
    )


    if not atacante_db_original:

        return {
            "success": False,
            "error": "Ficha do jogador não encontrada.",
        }


    # Trabalhamos com cópia.
    atacante_db = dict(
        atacante_db_original
    )


    # ========================================================
    # ✨ PRECISA ESTAR EQUIPADA
    # ========================================================

    equipadas = (
        atacante_db.get(
            "equipped_skills"
        )
        or
        atacante_db.get(
            "skills_equipadas"
        )
        or {}
    )


    if isinstance(
        equipadas,
        list,
    ):

        equipadas = {}


    skill_valida = (
        skill_id
        in [
            str(valor)

            for valor
            in equipadas.values()

            if valor
        ]
    )


    if not skill_valida:

        return {
            "success": False,

            "error": (
                "Esta skill não está "
                "equipada no seu grimório."
            ),
        }


    # ========================================================
    # 🔮 DADOS DA RARIDADE REAL
    # ========================================================

    skill_info = (
        get_skill_data_with_rarity(
            atacante_db,
            skill_id,
        )
        or {}
    )


    if not skill_info:

        return {
            "success": False,
            "error": "Skill não encontrada.",
        }


    skill_nome = (
        skill_info.get(
            "display_name"
        )
        or
        skill_info.get(
            "name"
        )
        or
        skill_id.replace(
            "_",
            " "
        ).title()
    )


    skill_tipo = str(
        skill_info.get(
            "type",
            "active"
        )
        or "active"
    ).lower()


    effects = (
        skill_info.get(
            "effects",
            {}
        )
        or {}
    )


    # ========================================================
    # 🚫 NESTA ETAPA SOMENTE OFENSIVAS
    # ========================================================

    chaves_suporte = {
        "party_heal",
        "party_mana",
        "party_buff",
        "self_heal_percent",
        "heal_type",
        "heal_scale",
        "on_heal_buff",
        "on_heal_low_hp_buff",
    }


    eh_suporte = (
        skill_tipo
        ==
        "support"

        or
        effects.get(
            "target"
        )
        in {
            "ally",
            "party",
            "grupo",
        }

        or
        any(
            chave
            in effects

            for chave
            in chaves_suporte
        )
    )


    if (
        skill_tipo
        ==
        "passive"
    ):

        return {
            "success": False,
            "error": "Skill passiva não pode ser ativada.",
        }


    if eh_suporte:

        return {
            "success": False,

            "error": (
                "Esta é uma skill de suporte. "
                "Ela será habilitada na "
                "próxima etapa."
            ),
        }


    # ========================================================
    # 💧 MP DA GUERRA
    # ========================================================

    mp_antes = int(
        atacante.get(
            "mp_atual",
            0
        )
        or 0
    )


    mana_cost = int(
        skill_info.get(
            "mana_cost",
            skill_info.get(
                "mp_cost",
                0
            )
        )
        or 0
    )


    if (
        mp_antes
        <
        mana_cost
    ):

        return {
            "success": False,

            "error": (
                f"Mana insuficiente. "
                f"{skill_nome} precisa "
                f"de {mana_cost} MP."
            ),
        }


    # ========================================================
    # ⏳ COOLDOWN DA GUERRA
    # ========================================================

    cooldowns_guerra = dict(
        atacante.get(
            "cooldowns",
            {}
        )
        or {}
    )


    holder_cd = {
        "cooldowns":
            cooldowns_guerra
    }


    pode_usar, msg_cd = (
        verificar_cooldown(
            holder_cd,
            skill_id,
        )
    )


    if not pode_usar:

        return {
            "success": False,
            "error": msg_cd,
        }


    # ========================================================
    # 🛡️ ISOLA COOLDOWN NORMAL
    #
    # combat_engine verá SOMENTE cooldown
    # desta batalha.
    # ========================================================

    atacante_db[
        "cooldowns"
    ] = dict(
        cooldowns_guerra
    )


    # ========================================================
    # 📌 ESTADO ANTES DA AÇÃO
    # ========================================================

    turno_indice_antes = int(
        batalha.get(
            "turno_indice",
            0
        )
        or 0
    )


    hp_alvo_antes = int(
        alvo.get(
            "hp_atual",
            0
        )
        or 0
    )


    attacker_stats = dict(
        atacante.get(
            "stats",
            {}
        )
        or {}
    )


    target_stats = dict(
        alvo.get(
            "stats",
            {}
        )
        or {}
    )


    target_stats[
        "hp"
    ] = hp_alvo_antes


    target_stats[
        "max_hp"
    ] = int(
        target_stats.get(
            "max_hp",
            hp_alvo_antes,
        )
        or hp_alvo_antes
        or 1
    )


    # ========================================================
    # ✨ MOTOR OFICIAL
    # ========================================================

    resultado_motor = (
        await processar_acao_combate(

            attacker_pdata=
                atacante_db,

            attacker_stats=
                attacker_stats,

            target_stats=
                target_stats,

            skill_id=
                skill_id,

            attacker_current_hp=
                int(
                    atacante.get(
                        "hp_atual",
                        0
                    )
                    or 0
                ),

            attacker_current_mp=
                mp_antes,
        )
    )


    dano = max(
        0,
        int(
            resultado_motor.get(
                "total_damage",
                0
            )
            or 0
        ),
    )


    mensagens_motor = [
        str(msg)

        for msg
        in (
            resultado_motor.get(
                "log_messages",
                []
            )
            or []
        )
    ]


    numero_golpes = max(
        1,
        int(
            resultado_motor.get(
                "num_hits",
                1
            )
            or 1
        ),
    )


    anim_effect = str(
        resultado_motor.get(
            "anim_effect"
        )
        or
        skill_info.get(
            "anim_effect"
        )
        or ""
    )


    tipo_skill_resultado = str(
        resultado_motor.get(
            "tipo_skill"
        )
        or
        skill_tipo
        or
        "active"
    )


    # ========================================================
    # 💧 SALVA MP SOMENTE NA GUERRA
    # ========================================================

    mp_depois = max(
        0,
        int(
            resultado_motor.get(
                "attacker_mp_left",
                mp_antes,
            )
            or 0
        ),
    )


    atacante[
        "mp_atual"
    ] = mp_depois


    # ========================================================
    # ⏳ SALVA COOLDOWN SOMENTE NA GUERRA
    #
    # aplicar_cooldown() foi chamado pelo
    # combat_engine e alterou a cópia.
    # ========================================================

    atacante[
        "cooldowns"
    ] = dict(
        atacante_db.get(
            "cooldowns",
            {}
        )
        or {}
    )


    # ========================================================
    # ❤️ DANO
    # ========================================================

    hp_alvo_depois = max(
        0,
        hp_alvo_antes
        -
        dano,
    )


    alvo[
        "hp_atual"
    ] = hp_alvo_depois


    alvo_derrotado = (
        hp_alvo_depois
        <= 0
    )


    agora = _agora()


    if alvo_derrotado:

        alvo[
            "vivo"
        ] = False

        alvo[
            "derrotado_em"
        ] = agora


    if not batalha.get(
        "iniciada_em"
    ):

        batalha[
            "iniciada_em"
        ] = agora


    # ========================================================
    # 📜 LOG
    # ========================================================

    acao_id = str(
        ObjectId()
    )


    evento = {

        "acao_id":
            acao_id,

        "tipo":
            "skill_ofensiva",

        "rodada":
            int(
                batalha.get(
                    "rodada",
                    1
                )
                or 1
            ),

        "atacante_id":
            str(
                player_id
            ),

        "atacante_nome":
            atacante.get(
                "nome",
                "Aventureiro",
            ),

        "atacante_lado":
            lado_atacante,

        "alvo_id":
            str(
                target_id
            ),

        "alvo_nome":
            alvo.get(
                "nome",
                "Aventureiro",
            ),

        "alvo_lado":
            lado_alvo,

        "skill_id":
            skill_id,

        "skill_nome":
            skill_nome,

        "anim_effect":
            anim_effect,

        "tipo_skill":
            tipo_skill_resultado,

        "dano":
            dano,

        "numero_golpes":
            numero_golpes,

        "hp_antes":
            hp_alvo_antes,

        "hp_depois":
            hp_alvo_depois,

        "mp_antes":
            mp_antes,

        "mp_depois":
            mp_depois,

        "alvo_derrotado":
            alvo_derrotado,

        "mensagens":
            mensagens_motor,

        "criado_em":
            agora,
    }


    batalha[
        "log"
    ] = (
        (
            batalha.get(
                "log",
                []
            )
            or []
        )
        +
        [
            evento
        ]
    )[-80:]


    # ========================================================
    # 🏆 FIM DA FRENTE?
    # ========================================================

    ainda_existe_inimigo = any(

        (
            str(
                combatente.get(
                    "lado",
                    ""
                )
                or ""
            ).lower()
            ==
            lado_alvo
        )

        and

        _combatente_esta_vivo(
            combatente
        )

        for combatente
        in (
            batalha.get(
                "combatentes",
                []
            )
            or []
        )
    )


    batalha_finalizada = (
        not ainda_existe_inimigo
    )


    proximo_turno = None


    if batalha_finalizada:

        batalha[
            "estado"
        ] = (
            BATALHA_STATUS_FINALIZADA
        )

        batalha[
            "finalizada_em"
        ] = agora

        batalha[
            "vencedor_clan_id"
        ] = atacante.get(
            "clan_id"
        )

        batalha[
            "turno_user_id"
        ] = None

        batalha[
            "turno_indice"
        ] = -1


    else:

        proximo_turno = (
            _avancar_turno_batalha(
                batalha
            )
        )


        if not proximo_turno:

            return {
                "success": False,

                "error": (
                    "Não foi possível localizar "
                    "o próximo combatente."
                ),
            }


    # ========================================================
    # 🔒 UPDATE ATÔMICO
    # ========================================================

    resultado_update = (
        clan_wars_collection
        .update_one(

            {
                "_id":
                    guerra["_id"],

                "status":
                    GUERRA_STATUS_EM_ANDAMENTO,

                "frentes": {
                    "$elemMatch": {

                        "numero":
                            numero_frente,

                        "batalha.estado":
                            BATALHA_STATUS_PREPARADA,

                        "batalha.turno_user_id":
                            player_id,

                        "batalha.turno_indice":
                            turno_indice_antes,

                        "batalha.combatentes": {
                            "$elemMatch": {

                                "user_id":
                                    target_id,

                                "hp_atual":
                                    hp_alvo_antes,

                                "vivo":
                                    True,
                            }
                        },
                    }
                },
            },

            {
                "$set":
                    _montar_campos_persistencia_batalha(

                        batalha=
                            batalha,

                        agora=
                            agora,

                        batalha_finalizada=
                            batalha_finalizada,

                        vencedor_clan_id=
                            atacante.get(
                                "clan_id"
                            ),
                    )
            },
        )
    )



    if (
        resultado_update.modified_count
        != 1
    ):

        return {
            "success": False,

            "error": (
                "O estado da batalha mudou "
                "antes da skill ser concluída."
            ),

            "recarregar":
                True,
        }
    # ========================================================
    # 🏆 ATUALIZA RESULTADO GERAL DA GUERRA
    # ========================================================

    resultado_guerra = None


    if batalha_finalizada:

        resultado_guerra = (
            _consolidar_guerra_apos_finalizar_frente(
                guerra["_id"]
            )
        )

    return {
        "success": True,

        "acao": {
            "acao_id":
                acao_id,

            "tipo":
                "skill_ofensiva",

            "atacante_id":
                str(player_id),

            "atacante_nome":
                atacante.get(
                    "nome",
                    "Aventureiro",
                ),

            "atacante_lado":
                lado_atacante,

            "alvo_id":
                str(target_id),

            "alvo_nome":
                alvo.get(
                    "nome",
                    "Aventureiro",
                ),

            "alvo_lado":
                lado_alvo,

            "skill_id":
                skill_id,

            "skill_nome":
                skill_nome,

            "anim_effect":
                anim_effect,

            "tipo_skill":
                tipo_skill_resultado,

            "dano":
                dano,

            "numero_golpes":
                numero_golpes,

            "hp_antes":
                hp_alvo_antes,

            "hp_depois":
                hp_alvo_depois,

            "mp_antes":
                mp_antes,

            "mp_depois":
                mp_depois,

            "cooldowns":
                dict(
                    atacante.get(
                        "cooldowns",
                        {}
                    )
                    or {}
                ),

            "alvo_derrotado":
                alvo_derrotado,

            "mensagens":
                mensagens_motor,
        },

        "rodada":
            int(
                batalha.get(
                    "rodada",
                    1
                )
                or 1
            ),

        "batalha_finalizada":
            batalha_finalizada,

        "vencedor_clan_id":
            (
                str(
                    atacante.get(
                        "clan_id"
                    )
                )
                if batalha_finalizada
                else None
            ),
    }
