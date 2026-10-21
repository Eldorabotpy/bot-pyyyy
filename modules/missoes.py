# modules/missoes.py
from bson import ObjectId
from modules.player.core import users_collection

# ==========================================
# 📜 CATÁLOGO DE MISSÕES DO REINO DE ELDORA
# ==========================================
# modules/missoes.py

QUESTS_DATA = {
    # Jornada inicial de Varek: as escolhas registram sinais de comportamento,
    # sem bloquear nenhuma classe nem alterar o combate atual.
    "q1_varek_recruta": {
        "titulo": "O Primeiro Dever",
        "npc": "varek",
        "level_req": 1,
        "conclusao_nivel": 2,
        "pre_req": None,
        "objetivo": "Conquiste experiência nos arredores, alcance o Nível 2 e volte ao Capitão Varek.",
        "req_itens": {},
        "recompensas": {"gold": 100},
        "escolhas": [
            {"id": "proteger", "titulo": "Proteger os moradores", "descricao": "Priorizar quem está perto do perigo.", "sinais": {"protecao": 1, "compaixao": 1}},
            {"id": "investigar", "titulo": "Observar as criaturas", "descricao": "Entender a ameaça antes de agir.", "sinais": {"curiosidade": 1, "prudencia": 1}},
            {"id": "avancar", "titulo": "Ir direto ao combate", "descricao": "Enfrentar o risco sem hesitar.", "sinais": {"coragem": 1, "determinacao": 1}},
        ],
        "fala_aceite": "Varek anotou sua decisão. Entre o ruído da pradaria e o som distante das criaturas, você ouve um sussurro: ‘Ainda há alguém…’. Quando olha ao redor, não há ninguém ali.",
        "fala_conclusao": "Você voltou mais experiente. Ao entregar o relatório, o sussurro retorna: ‘A estrada guarda os que ficaram para trás’. Varek não ouviu nada. Ele paga sua recompensa."
    },
    "q2_varek_defesas": {
        "titulo": "As Defesas da Fronteira",
        "npc": "varek",
        "level_req": 2,
        "conclusao_nivel": 4,
        "pre_req": "q1_varek_recruta",
        "objetivo": "Continue sua jornada, alcance o Nível 4 e retorne ao Capitão Varek para receber a avaliação da fronteira.",
        "req_itens": {},
        "recompensas": {"gold": 150},
        "escolhas": [
            {"id": "barricada", "titulo": "Reforçar as barricadas", "descricao": "Manter a rota segura para os moradores.", "sinais": {"protecao": 1, "dever": 1}},
            {"id": "rastrear", "titulo": "Rastrear a ameaça", "descricao": "Procurar de onde vêm as feras.", "sinais": {"curiosidade": 1, "prudencia": 1}},
            {"id": "patrulhar", "titulo": "Patrulhar a linha de frente", "descricao": "Conter o perigo onde ele aparecer.", "sinais": {"coragem": 1, "dever": 1}},
        ],
        "fala_aceite": "Varek registrou sua prioridade. Naquela noite, uma voz desconhecida murmura: ‘A caravana… não deixem a estrada em silêncio’. O som desaparece antes que encontre sua origem.",
        "fala_conclusao": "A fronteira resistiu enquanto você amadurecia. No silêncio que sucede a conversa, a voz retorna: ‘A caravana guarda uma alma’. Varek não percebe o sussurro; ele reconhece sua disciplina e paga a recompensa."
    },
    "q3_varek_provacao": {
        "titulo": "O Sinal da Caravana",
        "npc": "varek",
        "level_req": 4,
        "conclusao_nivel": 5,
        "pre_req": "q2_varek_defesas",
        "objetivo": "Proteja o viajante na Pradaria: derrote os 3 Goblins Batedores antes que a caravana seja destruída. Alcance o Nível 5 e volte ao Capitão Varek.",
        "req_itens": {},
        "req_abates_evento": 3,
        "nome_abates_evento": "Goblin Batedor",
        "recompensas": {"gold": 250},
        "escolhas": [
            {"id": "resgatar", "titulo": "Priorizar os viajantes", "descricao": "A vida de quem está na caravana vem primeiro.", "sinais": {"compaixao": 1, "protecao": 1}},
            {"id": "conter", "titulo": "Conter a ameaça", "descricao": "Impedir que a emboscada alcance a estrada e a cidade.", "sinais": {"coragem": 1, "dever": 1}},
            {"id": "planejar", "titulo": "Avaliar o terreno", "descricao": "Procurar uma forma segura de ajudar os sobreviventes.", "sinais": {"prudencia": 1, "curiosidade": 1}},
        ],
        "decisoes_finais": {
            "alma_guardiao": {
                "pergunta": "Quando os últimos goblins caem, uma presença pálida surge junto à estrada. A voz parece vir de alguém que protegeu a caravana: ‘Não consigo encontrar o caminho’. O que você faz?",
                "escolhas": [
                    {"id": "libertar", "titulo": "Ajudar a alma a partir", "descricao": "Agradecer sua proteção e deixá-la seguir em paz.", "sinais": {"compaixao": 1, "dever": 1}},
                    {"id": "ignorar", "titulo": "Voltar aos sobreviventes", "descricao": "A prioridade agora é garantir que os vivos estejam seguros.", "sinais": {"protecao": 1}},
                    {"id": "escutar", "titulo": "Escutar o que ela tenta dizer", "descricao": "Permanecer diante da presença e ouvir seu aviso.", "sinais": {"vinculo_espiritual": 1, "curiosidade": 1}}
                ]
            },
            "foco_espiritual": {
                "pergunta": "A presença aponta para um foco espiritual preso sob os destroços. Sua energia perturba os sobreviventes, mas também mantém a alma ligada à estrada. Qual será seu destino?",
                "escolhas": [
                    {"id": "selar", "titulo": "Selar o foco", "descricao": "Conter a energia para proteger os vivos e deixar a alma descansar.", "sinais": {"protecao": 1, "dever": 1}},
                    {"id": "destruir", "titulo": "Destruir o foco", "descricao": "Encerrar o perigo de forma definitiva.", "sinais": {"coragem": 1, "determinacao": 1}},
                    {"id": "acolher", "titulo": "Acolher as vozes", "descricao": "Aceitar ouvir os mortos e assumir a responsabilidade por esse vínculo.", "sinais": {"vinculo_espiritual": 1, "compaixao": 1}}
                ]
            }
        },
        "fala_aceite": "Varek anotou sua decisão. Ao se afastar, um sussurro atravessa o vento: ‘A estrada… ajude-nos’. A caravana aguarda na Pradaria.",
        "fala_conclusao": "Varek registra o que você fez na estrada. Por um instante, a sombra de uma figura acompanha você — e então desaparece. Agora, apresente-se à Arquimaga Selene."
    },
    # 1. O Despertar (Nível 5)
    "q4_selene_classe": {
        "titulo": "O Despertar da Centelha",
        "npc": "selene_arquimaga",
        "level_req": 5,
        "pre_req": "q3_varek_provacao",
        "objetivo": "Fale com Selene. As escolhas feitas na Pradaria podem revelar uma ressonância que ela nunca viu antes.",
        "req_itens": {},
        "recompensas": {}
    },

    ## 2. A Forja do Destino (Nível 7)
    "q5_thorek_profissao": {
        "titulo": "A Voz do Aço e da Terra",
        "npc": "thorek_mestre",
        "level_req": 7,
        "pre_req": "q4_selene_classe",
        "objetivo": "Escolha um ofício com Thorek e receba o seu Kit de Ferramentas Iniciante.",
        "req_itens": {},
        "recompensas": {"xp": 300, "gold": 200}
    },

    # 3. O SELO DO GRIMÓRIO (Nível 17 - A LONGA JORNADA)
    "q6_selene_grimorio": {
        "titulo": "A Provação do Conhecimento Proibido",
        "npc": "selene_arquimaga",
        "level_req": 17,
        "pre_req": "q5_thorek_profissao",
        "objetivo": "Sobreviva à Floresta Sombria. Traga 15 Ectoplasmas e 30 Couro de lobo Alfa para Selene.",
        "req_itens": {"ectoplasma": 15, "couro_de_lobo_alfa": 30},
        "recompensas": {"xp": 1000, "gold": 500} # A Skill será injetada via npc.py
    },
    
    # 4. O RECONHECIMENTO DA CAPITAL (Nível 20)
    "q7_selene_guildas": {
        "titulo": "O Reconhecimento da Capital",
        "npc": "selene_arquimaga",
        "level_req": 20,
        "pre_req": "q6_selene_grimorio",

        "objetivo": (
            "Possuir um Grimório não faz de você um aventureiro reconhecido. "
            "Viaje até a Pedreira de Granito e prove que sabe controlar "
            "o poder que despertou. Derrote 3 Kobolds Escavadores, "
            "2 Golens de Pedra Pequenos e 1 Gárgula de Vigia."
        ),

        "regiao_objetivo": "pedreira_granito",
        "regiao_nome": "Pedreira de Granito",

        "req_itens": {},

        "req_abates": {
            "kobold_escavador": 3,
            "golem_de_pedra_pequeno": 2,
            "gargula_de_vigia": 1,
        },

        "nomes_abates": {
            "kobold_escavador": "Kobold Escavador",
            "golem_de_pedra_pequeno": "Golem de Pedra Pequeno",
            "gargula_de_vigia": "Gárgula de Vigia",
        },

        "recompensas": {
            "xp": 2000,
            "gold": 1500,
            "itens": {
                "carta_recomendacao": 1
            }
        }
    }
}

def _int_seguro(valor, padrao=0):
    try:
        return int(valor or padrao)
    except (TypeError, ValueError):
        return int(padrao)


def _quantidade_item(inventario: dict, item_id: str) -> int:
    """
    Suporta os dois formatos existentes da mochila:

    item_id: 5

    e

    item_id: {
        "base_id": item_id,
        "quantity": 5
    }
    """
    if not isinstance(inventario, dict):
        return 0

    item = inventario.get(item_id, 0)

    if isinstance(item, dict):
        return _int_seguro(
            item.get(
                "quantity",
                item.get("qtd", 0)
            )
        )

    return _int_seguro(item)


def _calcular_progresso_abates(
    player_data: dict,
    quest_id: str,
    quest_data: dict,
):
    requisitos = (
        quest_data.get("req_abates", {})
        or {}
    )

    if not requisitos:
        return {}, True

    bestiario = (
        player_data.get("bestiario", {})
        or {}
    )

    quests = (
        player_data.get("quests", {})
        or {}
    )

    estado_quest = (
        quests.get(quest_id, {})
        or {}
    )

    inicio = (
        estado_quest.get("abates_inicio", {})
        or {}
    )

    nomes = (
        quest_data.get("nomes_abates", {})
        or {}
    )

    progresso = {}
    completo = True

    for monstro_id, quantidade_necessaria in requisitos.items():

        quantidade_necessaria = max(
            1,
            _int_seguro(
                quantidade_necessaria,
                1
            )
        )

        total_atual = _int_seguro(
            bestiario.get(monstro_id, 0)
        )

        total_inicio = _int_seguro(
            inicio.get(monstro_id, 0)
        )

        feitos = max(
            0,
            total_atual - total_inicio
        )

        concluido = (
            feitos >= quantidade_necessaria
        )

        if not concluido:
            completo = False

        progresso[monstro_id] = {
            "nome": nomes.get(
                monstro_id,
                monstro_id.replace("_", " ").title()
            ),
            "atual": min(
                feitos,
                quantidade_necessaria
            ),
            "necessario": quantidade_necessaria,
            "concluido": concluido,
        }

    return progresso, completo

# ==========================================
# ⚙️ MOTOR DE PROCESSAMENTO DE MISSÕES
# ==========================================

def obter_status_npc(player_data: dict, npc_id: str) -> dict:
    """
    Descobre quais missões o NPC pode oferecer,
    quais estão em andamento e quais já podem
    ser entregues.
    """

    my_level = _int_seguro(
        player_data.get("level", 1),
        1
    )

    my_quests = (
        player_data.get("quests")
        or {}
    )

    my_inv = (
        player_data.get("inventory")
        or {}
    )

    missoes_disponiveis = []
    missoes_em_andamento = []
    missoes_concluidas = []
    missoes_bloqueadas = []

    for q_id, q_data in QUESTS_DATA.items():

        if q_data["npc"] != npc_id:
            continue

        quest_salva = (
            my_quests.get(q_id, {})
            or {}
        )

        status_atual = (
            quest_salva.get("status")
        )

        # Já terminou essa etapa da história.
        if status_atual == "resgatada":
            continue

        # Missão anterior obrigatória.
        pre_req = q_data.get("pre_req")

        if (
            pre_req
            and
            my_quests.get(
                pre_req,
                {}
            ).get("status") != "resgatada"
        ):
            continue

        level_req = _int_seguro(q_data.get("level_req", 1), 1)
        if my_level < level_req:
            missoes_bloqueadas.append({
                "id": q_id,
                "data": q_data,
                "nivel_atual": my_level,
                "nivel_necessario": level_req,
            })
            continue

        # Aceita tanto o formato oficial deste motor
        # quanto o formato legado usado pelo NPCsEngine.
        if status_atual in (
            "ativa",
            "em_andamento",
        ):

            pode_entregar = True

            nivel_conclusao = _int_seguro(q_data.get("conclusao_nivel", 0))
            progresso_nivel = None
            if nivel_conclusao:
                progresso_nivel = {
                    "atual": min(my_level, nivel_conclusao),
                    "necessario": nivel_conclusao,
                    "concluido": my_level >= nivel_conclusao,
                }
                if my_level < nivel_conclusao:
                    pode_entregar = False

            progresso_itens = {}

            for item_req, qtd_req in (
                q_data.get(
                    "req_itens",
                    {}
                )
                or {}
            ).items():

                qtd_req = _int_seguro(
                    qtd_req
                )

                qtd_atual = _quantidade_item(
                    my_inv,
                    item_req
                )

                progresso_itens[item_req] = {
                    "atual": min(
                        qtd_atual,
                        qtd_req
                    ),
                    "necessario": qtd_req,
                    "concluido": (
                        qtd_atual >= qtd_req
                    ),
                }

                if qtd_atual < qtd_req:
                    pode_entregar = False

            (
                progresso_abates,
                abates_concluidos,
            ) = _calcular_progresso_abates(
                player_data,
                q_id,
                q_data,
            )

            if not abates_concluidos:
                pode_entregar = False

            dados_quest_visiveis = dict(q_data)
            pacote = {
                "id": q_id,
                "data": dados_quest_visiveis,
                "progresso_itens":
                    progresso_itens,
                "progresso_abates":
                    progresso_abates,
                "progresso_nivel":
                    progresso_nivel,
            }

            abates_evento_necessarios = _int_seguro(
                q_data.get("req_abates_evento", 0)
            )
            if abates_evento_necessarios:
                abates_evento_feitos = min(
                    _int_seguro(quest_salva.get("abates_evento", 0)),
                    abates_evento_necessarios,
                )
                pacote["progresso_evento"] = {
                    "nome": q_data.get("nome_abates_evento", "Alvos do evento"),
                    "atual": abates_evento_feitos,
                    "necessario": abates_evento_necessarios,
                    "concluido": abates_evento_feitos >= abates_evento_necessarios,
                }
                if abates_evento_feitos < abates_evento_necessarios:
                    pode_entregar = False

                if q_id == "q3_varek_provacao" and abates_evento_feitos >= abates_evento_necessarios:
                    alma = quest_salva.get("decisao_alma")
                    foco = quest_salva.get("decisao_foco")
                    etapa = "alma_guardiao" if not alma else ("foco_espiritual" if not foco else None)
                    if etapa:
                        dados_quest_visiveis["decisao_ativa"] = {
                            "etapa": etapa,
                            **q_data["decisoes_finais"][etapa],
                        }
                        pode_entregar = False

            if pode_entregar:
                missoes_concluidas.append(
                    pacote
                )
            else:
                missoes_em_andamento.append(
                    pacote
                )

        else:

            missoes_disponiveis.append({
                "id": q_id,
                "data": q_data,
            })

    return {
        "disponiveis":
            missoes_disponiveis,

        "em_andamento":
            missoes_em_andamento,

        "prontas_para_entrega":
            missoes_concluidas,

        "bloqueadas":
            missoes_bloqueadas,
        "jornada": {
            "necromante_revelado": (
                (my_quests.get("q3_varek_provacao", {}) or {}).get("decisao_alma") == "escutar"
                and (my_quests.get("q3_varek_provacao", {}) or {}).get("decisao_foco") == "acolher"
            )
        },
    }


def registrar_decisao_jornada(user_id: str, etapa: str, escolha_id: str) -> dict:
    """Registra as duas decisões narrativas finais da provação da caravana."""
    quest_id = "q3_varek_provacao"
    etapas = QUESTS_DATA[quest_id].get("decisoes_finais", {})
    etapa_anterior = {"alma_guardiao": None, "foco_espiritual": "alma_guardiao"}
    campo = {"alma_guardiao": "decisao_alma", "foco_espiritual": "decisao_foco"}
    if etapa not in etapas:
        return {"success": False, "error": "Essa decisão não pertence à jornada."}
    escolha = next((item for item in etapas[etapa]["escolhas"] if item["id"] == escolha_id), None)
    if not escolha:
        return {"success": False, "error": "Escolha narrativa inválida."}
    try:
        oid = ObjectId(user_id)
    except Exception:
        return {"success": False, "error": "Identidade do herói inválida."}
    player = users_collection.find_one({"_id": oid})
    if not player:
        return {"success": False, "error": "Herói não encontrado."}
    quest = (player.get("quests", {}) or {}).get(quest_id, {}) or {}
    necessario = _int_seguro(QUESTS_DATA[quest_id].get("req_abates_evento", 0))
    if quest.get("status") not in ("ativa", "em_andamento") or _int_seguro(quest.get("abates_evento", 0)) < necessario:
        return {"success": False, "error": "A presença só pode ser encontrada depois de proteger a caravana."}
    if etapa_anterior[etapa] and quest.get(campo[etapa_anterior[etapa]]) is None:
        return {"success": False, "error": "Primeiro responda à alma do guardião."}
    if quest.get(campo[etapa]) is not None:
        return {"success": False, "error": "Você já tomou essa decisão."}
    filtro = {
        "_id": oid,
        f"quests.{quest_id}.status": {"$in": ["ativa", "em_andamento"]},
        f"quests.{quest_id}.abates_evento": {"$gte": necessario},
        f"quests.{quest_id}.{campo[etapa]}": None,
    }
    if etapa_anterior[etapa]:
        filtro[f"quests.{quest_id}.{campo[etapa_anterior[etapa]]}"] = quest.get(campo[etapa_anterior[etapa]])
    atualizacao = {"$set": {f"quests.{quest_id}.{campo[etapa]}": escolha_id}}
    sinais = escolha.get("sinais", {})
    if sinais:
        atualizacao["$inc"] = {f"jornada.sinais.{sinal}": int(valor) for sinal, valor in sinais.items()}
    resultado = users_collection.update_one(filtro, atualizacao)
    if not resultado.modified_count:
        return {"success": False, "error": "Sua jornada mudou. Fale novamente com Varek para ver a decisão atual."}
    return {"success": True, "message": "Sua escolha foi guardada na memória da estrada."}

def aceitar_missao(
    user_id: str,
    quest_id: str,
    escolha_id: str = None,
) -> dict:

    q_data = QUESTS_DATA.get(
        quest_id
    )

    if not q_data:
        return {
            "success": False,
            "error":
                "Missão não encontrada nas lendas."
        }

    try:
        oid = ObjectId(user_id)
    except Exception:
        return {
            "success": False,
            "error":
                "Identidade do herói inválida."
        }

    player = users_collection.find_one({
        "_id": oid
    })

    if not player:
        return {
            "success": False,
            "error":
                "Herói não encontrado."
        }

    quests = (
        player.get("quests", {})
        or {}
    )

    estado_atual = (
        quests.get(quest_id, {})
        or {}
    )

    status_atual = (
        estado_atual.get("status")
    )

    if status_atual == "resgatada":
        return {
            "success": False,
            "error":
                "Esta missão já foi concluída."
        }

    if status_atual in (
        "ativa",
        "em_andamento",
    ):
        return {
            "success": False,
            "error":
                "Esta missão já está em andamento."
        }

    level_req = _int_seguro(
        q_data.get("level_req", 1),
        1
    )

    level_player = _int_seguro(
        player.get("level", 1),
        1
    )

    if level_player < level_req:
        return {
            "success": False,
            "error":
                f"Você precisa alcançar o nível {level_req}."
        }

    pre_req = q_data.get(
        "pre_req"
    )

    if (
        pre_req
        and
        quests.get(
            pre_req,
            {}
        ).get("status") != "resgatada"
    ):
        return {
            "success": False,
            "error":
                "A etapa anterior da sua jornada "
                "ainda não foi concluída."
        }

    escolha = None
    escolhas_validas = q_data.get("escolhas", []) or []
    if escolhas_validas:
        escolha = next(
            (item for item in escolhas_validas if item.get("id") == escolha_id),
            None,
        )
        if not escolha:
            return {
                "success": False,
                "error": "Escolha uma resposta para registrar antes de aceitar a missão."
            }

    dados_missao = {
        "titulo":
            q_data["titulo"],

        "objetivo":
            q_data["objetivo"],

        "status":
            "ativa",
    }

    if escolha:
        dados_missao["escolha"] = escolha["id"]
        dados_missao["sinais_jornada"] = escolha.get("sinais", {})

    abates_evento_necessarios = _int_seguro(
        q_data.get("req_abates_evento", 0)
    )
    if abates_evento_necessarios:
        dados_missao["abates_evento"] = 0
        dados_missao["abates_evento_registrados"] = []
        dados_missao["tentativa_evento"] = 1
        dados_missao["caravana_integridade"] = 100
        dados_missao["event_spawn_ids"] = [
            f"q3_caravana_{user_id}_1_{indice}"
            for indice in range(1, abates_evento_necessarios + 1)
        ]

    # =====================================================
    # ⚔️ MARCO INICIAL DOS ABATES
    # =====================================================

    req_abates = (
        q_data.get("req_abates", {})
        or {}
    )

    if req_abates:

        bestiario = (
            player.get("bestiario", {})
            or {}
        )

        dados_missao[
            "abates_inicio"
        ] = {
            monstro_id:
                _int_seguro(
                    bestiario.get(
                        monstro_id,
                        0
                    )
                )

            for monstro_id
            in req_abates.keys()
        }

    atualizacao = {
        "$set": {
            f"quests.{quest_id}": dados_missao
        }
    }
    if escolha:
        atualizacao["$inc"] = {
            f"jornada.sinais.{sinal}": int(valor)
            for sinal, valor in escolha.get("sinais", {}).items()
        }

    users_collection.update_one(
        {
            "_id": oid
        },
        atualizacao
    )

    return {
        "success": True,
        "message": q_data.get("fala_aceite") or f"Missão aceita: {q_data['titulo']}"
    }

def entregar_missao(
    user_id: str,
    player_data: dict,
    quest_id: str,
) -> dict:

    q_data = QUESTS_DATA.get(
        quest_id
    )

    if not q_data:
        return {
            "success": False,
            "error":
                "Missão não encontrada."
        }

    quests = (
        player_data.get(
            "quests",
            {}
        )
        or {}
    )

    estado_quest = (
        quests.get(
            quest_id,
            {}
        )
        or {}
    )

    status_atual = (
        estado_quest.get(
            "status"
        )
    )

    if status_atual == "resgatada":
        return {
            "success": False,
            "error":
                "Esta missão já foi concluída."
        }

    if status_atual not in (
        "ativa",
        "em_andamento",
    ):
        return {
            "success": False,
            "error":
                "Esta missão ainda não foi aceita."
        }

    caravana_integridade = _int_seguro(estado_quest.get("caravana_integridade", 100), 100)
    if q_data.get("req_abates_evento") and caravana_integridade <= 0:
        return {
            "success": False,
            "error": "A caravana foi destruída. Volte à Pradaria para tentar resgatar o viajante novamente."
        }

    nivel_conclusao = _int_seguro(q_data.get("conclusao_nivel", 0))
    nivel_atual = _int_seguro(player_data.get("level", 1), 1)
    if nivel_conclusao and nivel_atual < nivel_conclusao:
        return {
            "success": False,
            "error": f"Alcance o Nível {nivel_conclusao} antes de prestar contas desta missão."
        }

    abates_evento_necessarios = _int_seguro(q_data.get("req_abates_evento", 0))
    abates_evento_feitos = _int_seguro(estado_quest.get("abates_evento", 0))
    if abates_evento_feitos < abates_evento_necessarios:
        return {
            "success": False,
            "error": (
                f"A caravana ainda está cercada. Derrote {q_data.get('nome_abates_evento', 'os inimigos')} "
                f"({abates_evento_feitos}/{abates_evento_necessarios})."
            )
        }

    inventario = (
        player_data.get(
            "inventory",
            {}
        )
        or {}
    )

    # =====================================================
    # 📦 VALIDA ITENS
    # =====================================================

    for item_req, qtd_req in (
        q_data.get(
            "req_itens",
            {}
        )
        or {}
    ).items():

        qtd_atual = _quantidade_item(
            inventario,
            item_req
        )

        if qtd_atual < _int_seguro(
            qtd_req
        ):
            return {
                "success": False,
                "error":
                    f"Falta material: {item_req}"
            }

    # =====================================================
    # ⚔️ VALIDA ABATES
    # =====================================================

    (
        progresso_abates,
        abates_concluidos,
    ) = _calcular_progresso_abates(
        player_data,
        quest_id,
        q_data,
    )

    if not abates_concluidos:

        faltando = []

        for dados in (
            progresso_abates.values()
        ):

            if not dados.get(
                "concluido"
            ):

                faltando.append(
                    (
                        f"{dados['nome']}: "
                        f"{dados['atual']}/"
                        f"{dados['necessario']}"
                    )
                )

        return {
            "success": False,
            "error":
                "Sua provação ainda não terminou. "
                + " | ".join(faltando)
        }

    # =====================================================
    # 📦 INVENTÁRIO
    # =====================================================

    inventario_novo = dict(
        inventario
    )

    # Consome requisitos.
    for item_req, qtd_req in (
        q_data.get(
            "req_itens",
            {}
        )
        or {}
    ).items():

        qtd_req = _int_seguro(
            qtd_req
        )

        item_atual = (
            inventario_novo.get(
                item_req
            )
        )

        if isinstance(
            item_atual,
            dict
        ):

            item_atual = dict(
                item_atual
            )

            nova_qtd = (
                _quantidade_item(
                    inventario_novo,
                    item_req
                )
                -
                qtd_req
            )

            if nova_qtd > 0:
                item_atual[
                    "quantity"
                ] = nova_qtd

                inventario_novo[
                    item_req
                ] = item_atual
            else:
                inventario_novo.pop(
                    item_req,
                    None
                )

        else:

            nova_qtd = (
                _int_seguro(
                    item_atual
                )
                -
                qtd_req
            )

            if nova_qtd > 0:
                inventario_novo[
                    item_req
                ] = nova_qtd
            else:
                inventario_novo.pop(
                    item_req,
                    None
                )

    recompensas = (
        q_data.get(
            "recompensas",
            {}
        )
        or {}
    )

    # Adiciona itens de recompensa.
    for item_ganho, qtd_ganha in (
        recompensas.get(
            "itens",
            {}
        )
        or {}
    ).items():

        qtd_ganha = _int_seguro(
            qtd_ganha
        )

        atual = (
            inventario_novo.get(
                item_ganho
            )
        )

        if isinstance(
            atual,
            dict
        ):

            atual = dict(
                atual
            )

            atual["quantity"] = (
                _quantidade_item(
                    inventario_novo,
                    item_ganho
                )
                +
                qtd_ganha
            )

            atual.setdefault(
                "base_id",
                item_ganho
            )

            inventario_novo[
                item_ganho
            ] = atual

        else:

            inventario_novo[
                item_ganho
            ] = {
                "base_id":
                    item_ganho,

                "quantity":
                    _int_seguro(
                        atual
                    )
                    +
                    qtd_ganha,
            }

    update_set = {
        "inventory":
            inventario_novo,

        f"quests.{quest_id}.status":
            "resgatada",
    }

    # =====================================================
    # 🏰 q7 = RECONHECIMENTO OFICIAL
    # =====================================================

    if quest_id == "q7_selene_guildas":
        update_set[
            "guild_access_unlocked"
        ] = True

    update_inc = {}

    xp_reward = _int_seguro(
        recompensas.get(
            "xp",
            0
        )
    )

    gold_reward = _int_seguro(
        recompensas.get(
            "gold",
            0
        )
    )

    if xp_reward > 0:
        update_inc["xp"] = (
            xp_reward
        )

    if gold_reward > 0:
        update_inc["gold"] = (
            gold_reward
        )

    update_query = {
        "$set":
            update_set
    }

    if update_inc:
        update_query[
            "$inc"
        ] = update_inc

    users_collection.update_one(
        {
            "_id":
                ObjectId(user_id)
        },
        update_query
    )

    return {
        "success": True,

        "message": q_data.get("fala_conclusao") or (
            "Missão concluída! Você recebeu suas recompensas."
        ),

        "recompensas_entregues":
            recompensas,
    }

    
