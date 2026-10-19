one
    jogador_a_info = jogadores_online.get(jogador_a_sid) if jogador_a_sid else None
    if (
        not convite
        or not jogador_a_info
        or str(jogador_a_info.get('char_id')) != desafiante_id
    ):
        emit('novaMensagemChat', {"remetente": "Sistema", "texto": "❌ O desafiante fugiu ou desconectou.", "tipo": "erro"}, to=jogador_b_sid)
        return

    if jogador_a_info.get('em_combate') or jogador_b_info.get('em_combate'):
        emit('novaMensagemChat', {"remetente": "Sistema", "texto": "❌ Um dos jogadores já está em combate!", "tipo": "erro"}, to=jogador_b_sid)
        return

    # 1. Trava os jogadores no mapa
    jogadores_online[jogador_a_sid]['em_combate'] = True
    jogadores_online[jogador_b_sid]['em_combate'] = True

    # 2. Busca os dados reais no banco de dados e calcula os status
    player_a_db = users_collection.find_one({"_id": ObjectId(jogador_a_info['char_id'])})
    player_b_db = users_collection.find_one({"_id": ObjectId(jogador_b_info['char_id'])})

    stats_a = get_combat_stats_sync(player_a_db)
    stats_b = get_combat_stats_sync(player_b_db)

    player_a_db = aplicar_combat_stats_no_player(player_a_db, stats_a)
    player_b_db = aplicar_combat_stats_no_player(player_b_db, stats_b)

    # Define HP/MP iniciais do duelo
    hp_a = int(stats_a.get('current_hp', stats_a.get('max_hp', 1)))
    hp_b = int(stats_b.get('current_hp', stats_b.get('max_hp', 1)))

    # 3. Cria a sessão do Duelo
    duelo_id = f"duelo_{jogador_a_info['char_id']}_{jogador_b_info['char_id']}"
    
    duelos_ativos[duelo_id] = {
        "id": duelo_id,
        "jogador_a": {"sid": jogador_a_sid, "db": player_a_db, "stats": stats_a, "hp": hp_a, "mp": stats_a.get("current_mp", stats_a.get("max_mana", 50))},
        "jogador_b": {"sid": jogador_b_sid, "db": player_b_db, "stats": stats_b, "hp": hp_b, "mp": stats_b.get("current_mp", stats_b.get("max_mana", 50))},
        "turno_de": jogador_a_sid # O desafiante começa atacando
    }

    # 4. Formata o pacote visual para o Frontend (combate.js)
    estado_para_a = {
        "duelo_id": duelo_id,
        "regiao": jogador_a_info.get('regiao', 'capital_eldora'), # 👈 AQUI: Pega o mapa exato onde vocês estão!
        "oponente_nome": jogador_b_info['nome'],
        "oponente_skin": jogador_b_info['skin'],
        "oponente_level": player_b_db.get('level', 1),
        "oponente_hp": hp_b,
        "oponente_max_hp": stats_b.get('max_hp', 1),
        "meu_level": player_a_db.get('level', 1),
        "meu_hp": hp_a,
        "meu_max_hp": stats_a.get('max_hp', 1),
        "meu_mp": stats_a.get("current_mp", stats_a.get("max_mana", 50)),
        "meu_max_mp": stats_a.get('max_mana', 50),
        "minha_vez": True 
    }
    
    estado_para_b = {
        "duelo_id": duelo_id,
        "regiao": jogador_b_info.get('regiao', 'capital_eldora'), # 👈 AQUI TAMBÉM!
        "oponente_nome": jogador_a_info['nome'],
        "oponente_skin": jogador_a_info['skin'],
        "oponente_level": player_a_db.get('level', 1),
        "oponente_hp": hp_a,
        "oponente_max_hp": stats_a.get('max_hp', 1),
        "meu_level": player_b_db.get('level', 1),
        "meu_hp": hp_b,
        "meu_max_hp": stats_b.get('max_hp', 1),
        "meu_mp": stats_b.get("current_mp", stats_b.get("max_mana", 50)),
        "meu_max_mp": stats_b.get('max_mana', 50),
        "minha_vez": False
    }

    emit('iniciarArenaPvP', estado_para_a, to=jogador_a_sid)
    emit('iniciarArenaPvP', estado_para_b, to=jogador_b_sid)

# 👇 Adicione isso junto aos outros ouvintes do Socket.IO no main.py 👇
      
def buscar_jogador(uid):
    query = []
    try:
        query.append({"_id": ObjectId(uid)})
    except (errors.InvalidId, TypeError):
        pass

    if str(uid).isdigit(): query.append({"telegram_id": int(uid)})
    query.append({"telegram_id": str(uid)})
    query.append({"username": str(uid)})
    return db.users.find_one({"$or": query})    

def notificar_dano_party(char_id, hp_atual, max_hp, mp_atual, max_mp):
    grupo = parties_collection.find_one({"membros": str(char_id)})
    if grupo:
        hp_pct = (hp_atual / max_hp) * 100 if max_hp > 0 else 0
        mp_pct = (mp_atual / max_mp) * 100 if max_mp > 0 else 0
        
        for membro_id in grupo.get('membros', []):
            for sid, info in jogadores_online.items():
                if str(info['char_id']) == str(membro_id):
                    socketio.emit('atualizarStatusParty', {
                        'char_id': str(char_id), 'hp_pct': hp_pct, 'mp_pct': mp_pct
                    }, room=sid)

# ==============================================================================
# ⛺ ROTA DA LOJA DO MERCADOR
# ==============================================================================
@app.route('/api/loja/comprar', methods=['POST'])
def loja_comprar():
    try:
        dados = request.json
        user_id = dados.get('user_id')
        item_id = dados.get('item_id')
        preco = int(dados.get('preco', 0))

        # 1. Busca o jogador no banco de dados pelo ID
        player = users_collection.find_one({"_id": ObjectId(user_id)})
        if not player:
            return jsonify({"erro": "Jogador não encontrado no banco de dados!"})

        # 2. Verifica o bolso do cliente (Ouro)
        ouro_atual = player.get("gold", 0)
        if ouro_atual < preco:
            return jsonify({"erro": f"Ouro insuficiente! Você tem {ouro_atual}💰 e precisa de {preco}💰."})

        # 3. Calcula o troco e prepara a mochila
        novo_ouro = ouro_atual - preco
        inventario = player.get("inventory", [])
        inventario.append(item_id) # Coloca a poção na lista

        # 4. Salva a transação no MongoDB!
        users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"gold": novo_ouro, "inventory": inventario}}
        )

        return jsonify({"sucesso": True, "novo_ouro": novo_ouro})

    except Exception as e:
        return jsonify({"erro": f"Erro na loja: {str(e)}"})

async def telegram_error_handler(update, context):
    erro = context.error

    # Falhas temporárias de conexão com o Telegram.
    # O polling já tenta reconectar automaticamente.
    if isinstance(erro, NetworkError):
        return

    # Erros reais do bot continuam aparecendo.
    print(f"🚨 Erro inesperado no Bot Telegram: {erro}")

def run_bot():
    """Roda o bot do Telegram num loop isolado."""

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while True:
        try:
            application = (
                Application
                .builder()
                .token(TELEGRAM_TOKEN)
                .build()
            )

            application.add_handler(
                CommandHandler("start", start_command)
            )

            application.add_error_handler(
                telegram_error_handler
            )

            print(
                "🤖 Corvos mensageiros a postos! "
                "Bot do Telegram escutando /start..."
            )

            application.run_polling(
                drop_pending_updates=True,
                close_loop=False,
                bootstrap_retries=5,
                stop_signals=None
            )

            # Se terminou normalmente, não reinicia.
            break

        except (TimedOut, NetworkError):
            print(
                "⚠️ Telegram indisponível temporariamente. "
                "Nova tentativa em 10 segundos..."
            )
            time.sleep(10)

        except Exception as e:
            print(
                f"🚨 Erro ao iniciar Bot Telegram: {e}"
            )
            time.sleep(10)
# ==============================================================================
# ⚔️ SISTEMA DE PVP (DUELOS 1V1)
# ==============================================================================
duelos_ativos = {} # Guarda o estado atual de cada duelo rolando no mapa
filas_coliseu = {"evento": []}
fila_coliseu_lock = Lock()
resultado_coliseu_lock = Lock()
duelo_espelho_coliseu_lock = Lock()
espelhos_coliseu_ativos = set()
fila_coliseu_evento_id = None
fila_coliseu_entrada = {}
COLISEU_ENTRADAS_DIARIAS = DAILY_FREE_ENTRIES
COLISEU_ENTRADA_X = 4 * 32
COLISEU_ENTRADA_Y = 35 * 32
COLISEU_RAIO_FILA = 150


def _resumo_cota_coliseu(char_id):
    return get_daily_entry_quota(users_collection, char_id)


def _consumir_entradas_coliseu(char_ids):
    return consume_daily_entries(users_collection, char_ids)


def _mensagem_sem_entrada_coliseu(char_id):
    resumo = _resumo_cota_coliseu(char_id) or {}
    if resumo.get("tickets", 0) > 0:
        return "Não foi possível usar o Ticket de Entrada. Atualize o Coliseu e tente novamente."
    return "Você usou as 10 entradas gratuitas de hoje. Compre um Ticket do Coliseu na Loja da Flora por 10 💎 para continuar."


def _emitir_cota_coliseu(sid):
    info = jogadores_online.get(sid) or {}
    resumo = _resumo_cota_coliseu(info.get("char_id", ""))
    if resumo:
        socketio.emit("coliseuCota", resumo, to=sid)
    return resumo


@socketio.on("consultarCotaColiseu")
def handle_consultar_cota_coliseu(_data=None):
    sid = request.sid
    if not jogadores_online.get(sid):
        socketio.emit("coliseuCota", {"erro": "Entre no jogo para consultar suas entradas."}, to=sid)
        return
    _emitir_cota_coliseu(sid)


def _esta_no_portao_coliseu(info):
    try:
        x = float(info.get("x", 0))
        y = float(info.get("y", 0))
    except (TypeError, ValueError):
        return False
    return math.hypot(x - COLISEU_ENTRADA_X, y - COLISEU_ENTRADA_Y) <= COLISEU_RAIO_FILA


def _limite_elo_fila(segundos_esperando):
    """Amplia a faixa de Elo com a espera e remove o limite após 90 segundos."""
    if segundos_esperando < 15:
        return 100
    if segundos_esperando < 30:
        return 250
    if segundos_esperando < 60:
        return 500
    if segundos_esperando < 90:
        return 1000
    return float("inf")


def _emitir_fila_coliseu(sid, estado, mensagem, modo=None):
    socketio.emit("coliseuFila", {"estado": estado, "mensagem": mensagem, "modo": modo}, to=sid)


def _iniciar_duelo_coliseu(sid_a, sid_b, modo, event_id=None, season_number=None):
    """Prepara um duelo do Coliseu com personagens e atributos lidos no servidor."""
    info_a = jogadores_online.get(sid_a)
    info_b = jogadores_online.get(sid_b)
    if not info_a or not info_b or info_a.get("em_combate") or info_b.get("em_combate"):
        return False
    if str(info_a.get("char_id")) == str(info_b.get("char_id")):
        return False
    if modo == "evento" and any(not _esta_no_portao_coliseu(info) for info in (info_a, info_b)):
        return False
    if not ObjectId.is_valid(str(info_a.get("char_id"))) or not ObjectId.is_valid(str(info_b.get("char_id"))):
        return False

    player_a_db = users_collection.find_one({"_id": ObjectId(str(info_a["char_id"]))})
    player_b_db = users_collection.find_one({"_id": ObjectId(str(info_b["char_id"]))})
    if not player_a_db or not player_b_db:
        return False
    try:
        stats_a = get_combat_stats_sync(player_a_db)
        stats_b = get_combat_stats_sync(player_b_db)
        player_a_db = aplicar_combat_stats_no_player(player_a_db, stats_a)
        player_b_db = aplicar_combat_stats_no_player(player_b_db, stats_b)
    except Exception:
        app.logger.exception("Falha ao preparar duelo do Coliseu")
        return False

    hp_a = int(stats_a.get("current_hp", stats_a.get("max_hp", 1)))
    hp_b = int(stats_b.get("current_hp", stats_b.get("max_hp", 1)))
    consumo = _consumir_entradas_coliseu([info_a.get("char_id"), info_b.get("char_id")])
    if not consumo.get("sucesso"):
        bloqueado = str(consumo.get("bloqueado_id", ""))
        for sid, info in ((sid_a, info_a), (sid_b, info_b)):
            if str(info.get("char_id", "")) == bloqueado:
                _emitir_fila_coliseu(sid, "erro", _mensagem_sem_entrada_coliseu(bloqueado), modo)
            else:
                _emitir_fila_coliseu(sid, "erro", "O adversário não tem entradas disponíveis para esta luta.", modo)
            _emitir_cota_coliseu(sid)
        return "cota_esgotada" if consumo.get("quota") is not None else False
    _emitir_cota_coliseu(sid_a)
    _emitir_cota_coliseu(sid_b)
    duelo_id = f"coliseu_{uuid4().hex}"
    jogadores_online[sid_a]["em_combate"] = True
    jogadores_online[sid_b]["em_combate"] = True
    duelos_ativos[duelo_id] = {
        "id": duelo_id,
        "modo": modo,
        "event_id": event_id,
        "season_number": season_number,
        "jogador_a": {"sid": sid_a, "db": player_a_db, "stats": stats_a, "hp": hp_a, "mp": stats_a.get("current_mp", stats_a.get("max_mana", 50))},
        "jogador_b": {"sid": sid_b, "db": player_b_db, "stats": stats_b, "hp": hp_b, "mp": stats_b.get("current_mp", stats_b.get("max_mana", 50))},
        "turno_de": sid_a,
    }

    def estado(meu_sid, rival_sid, meu_db, rival_db, minha_vez):
        meu = jogadores_online[meu_sid]
        rival = jogadores_online[rival_sid]
        return {
            "duelo_id": duelo_id,
            "regiao": meu.get("regiao", "capital_eldora"),
            "oponente_nome": rival.get("nome", rival_db.get("character_name", "Aventureiro")),
            "oponente_skin": rival.get("skin", "aventureiro_m"),
            "oponente_level": rival_db.get("level", 1),
            "oponente_hp": rival_db.get("current_hp", rival_db.get("max_hp", 1)),
            "oponente_max_hp": rival_db.get("max_hp", 1),
            "meu_level": meu_db.get("level", 1),
            "meu_hp": meu_db.get("current_hp", meu_db.get("max_hp", 1)),
            "meu_max_hp": meu_db.get("max_hp", 1),
            "meu_mp": meu_db.get("current_mp", meu_db.get("max_mana", 50)),
            "meu_max_mp": meu_db.get("max_mana", 50),
            "minha_vez": minha_vez,
            "modo_pvp": modo,
        }

    _emitir_fila_coliseu(sid_a, "iniciada", "O adversário foi encontrado. A luta vai começar!", modo)
    _emitir_fila_coliseu(sid_b, "iniciada", "O adversário foi encontrado. A luta vai começar!", modo)
    socketio.emit("iniciarArenaPvP", estado(sid_a, sid_b, player_a_db, player_b_db, True), to=sid_a)
    socketio.emit("iniciarArenaPvP", estado(sid_b, sid_a, player_b_db, player_a_db, False), to=sid_b)
    return True


def _registrar_resultado_coliseu(duelo, vencedor_sid):
    """Grava Elo ou placar do evento uma vez, usando o vencedor calculado pelo servidor."""
    with resultado_coliseu_lock:
        if duelo.get("resultado_registrado"):
            return
        modo = duelo.get("modo", "casual")
        if modo not in ("ranqueado", "evento"):
            return
        duelo["resultado_registrado"] = True
        participantes = [duelo["jogador_a"], duelo["jogador_b"]]
        documentos = [participantes[0]["db"], participantes[1]["db"]]
        ids = [doc.get("_id") for doc in documentos]
        venceu = [participantes[i]["sid"] == vencedor_sid for i in range(2)]

        if modo == "ranqueado":
            pontos = [_elo_points(doc) for doc in documentos]
            esperado_a = 1 / (1 + 10 ** ((pontos[1] - pontos[0]) / 400))
            esperado_b = 1 - esperado_a
            deltas = [round(32 * (int(venceu[0]) - esperado_a)), round(32 * (int(venceu[1]) - esperado_b))]
            resultados = []
            season_number = int(duelo.get("season_number", 1))
            for i, doc in enumerate(documentos):
                total = max(0, pontos[i] + deltas[i])
                contador = "pvp_wins" if venceu[i] else "pvp_losses"
                contador_temporada = "pvp_season_wins" if venceu[i] else "pvp_season_losses"
                users_collection.update_one(
                    {"_id": ids[i], "pvp_season_number": season_number},
                    {"$set": {"pvp_points": total}, "$inc": {contador: 1, "pvp_season_matches": 1, contador_temporada: 1}},
                )
                resultados.append({"delta": total - pontos[i], "pontos": total})
            users_collection.database["coliseu_pvp_partidas"].update_one(
                {"_id": duelo["id"]},
                {"$setOnInsert": {"jogadores": [str(ids[0]), str(ids[1])], "nomes": [_nome_personagem_db(doc) or "Aventureiro" for doc in documentos], "vencedor": str(ids[0] if venceu[0] else ids[1]), "alteracoes": resultados, "temporada": season_number, "criado_em": datetime.utcnow()}},
                upsert=True,
            )
            clear_all_player_cache()
            for i, participante in enumerate(participantes):
                if participante.get("espelho"):
                    continue
                socketio.emit("coliseuResultado", {"modo": modo, "delta": resultados[i]["delta"], "pontos": resultados[i]["pontos"], "vitoria": venceu[i]}, to=participante["sid"])
            return

        event_id = duelo.get("event_id")
        if not event_id:
            return
        placar = users_collection.database["coliseu_evento_pvp"]
        for i, doc in enumerate(documentos):
            placar.update_one(
                {"_id": f"{event_id}:{ids[i]}", "event_id": event_id},
                {"$setOnInsert": {"event_id": event_id, "char_id": str(ids[i]), "nome": _nome_personagem_db(doc) or "Aventureiro"},
                 "$inc": {"partidas": 1, ("vitorias" if venceu[i] else "derrotas"): 1}},
                upsert=True,
            )
            socketio.emit("coliseuResultado", {"modo": modo, "vitoria": venceu[i], "event_id": event_id}, to=participantes[i]["sid"])


def _encerrar_duelo_coliseu_ao_desconectar(sid):
    """Trata desconexão em partida competitiva como desistência e libera o rival."""
    for duelo_id, duelo in list(duelos_ativos.items()):
        if duelo.get("modo") not in ("ranqueado", "evento") and not duelo.get("espelho"):
            continue
        participantes = [duelo["jogador_a"], duelo["jogador_b"]]
        perdedor = next((p for p in participantes if p["sid"] == sid), None)
        if not perdedor:
            continue
        vencedor = next(p for p in participantes if p["sid"] != sid)
        try:
            _registrar_resultado_coliseu(duelo, vencedor["sid"])
        except Exception:
            app.logger.exception("Falha ao salvar resultado após desconexão no Coliseu")
        if duelo.get("espelho"):
            espelho_id = str(duelo["jogador_b"]["db"].get("_id"))
            with duelo_espelho_coliseu_lock:
                espelhos_coliseu_ativos.discard(espelho_id)
        if vencedor["sid"] in jogadores_online:
            jogadores_online[vencedor["sid"]]["em_combate"] = False
            socketio.emit("animarTurnoPvP", {
                "log": [{"autor_sid": vencedor["sid"], "texto": "O adversário desconectou. Vitória por desistência.", "dano": 0}],
                "vencedor_sid": vencedor["sid"],
                "novo_hp": 0,
                "atacante_sid": vencedor["sid"],
                "novo_mp": vencedor["mp"],
                "proximo_turno_sid": None,
            }, to=vencedor["sid"])
        jogadores_online.get(sid, {})["em_combate"] = False
        duelos_ativos.pop(duelo_id, None)


def _preparar_personagem_temporada(char_id, season_number):
    """Garante que todo personagem usado no ranqueado começa na temporada atual."""
    oid = ObjectId(str(char_id))
    users_collection.update_one(
        {"_id": oid, "pvp_season_number": {"$ne": int(season_number)}},
        {"$set": {
            "pvp_points": 0,
            "pvp_season_number": int(season_number),
            "pvp_season_matches": 0,
            "pvp_season_wins": 0,
            "pvp_season_losses": 0,
        }},
    )
    return users_collection.find_one({"_id": oid})


def _nome_personagem_db(player):
    """Lê o campo de nome atual e o campo legado usado por heróis antigos."""
    for field in ("character_name", "name", "nome"):
        value = player.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _nome_adversario_coliseu(player):
    """Usa o nome do personagem ou, em contas antigas, o identificador da conta."""
    nome = _nome_personagem_db(player)
    if nome:
        return nome
    for field in ("username", "telegram_username", "tg_username"):
        value = player.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip().lstrip("@")
    return "Herói do Reino"


def _safe_int(value, default=0):
    try:
        return int(float(value if value is not None else default))
    except (TypeError, ValueError, OverflowError):
        return int(default)


def _elo_points(player):
    return max(0, _safe_int((player or {}).get("pvp_points"), 0))


def _skin_personagem_salvo(player):
    skin = player.get("equipped_skin") or player.get("skin_equipada")
    if skin and skin != "padrao":
        return str(skin)
    classe = str(player.get("class") or player.get("class_key") or "aventureiro").strip().lower()
    if classe in ("aprendiz", "aventureiro"):
        classe = "aventureiro"
    genero = "f" if str(player.get("gender", "masculino")).lower() == "feminino" else "m"
    return f"{classe}_{genero}"


@socketio.on("buscarAdversariosColiseu")
def handle_buscar_adversarios_coliseu(_data=None):
    sid = request.sid
    info = jogadores_online.get(sid)
    if not info:
        socketio.emit("coliseuAdversarios", {"adversarios": [], "mensagem": "Entre no jogo para buscar adversários."}, to=sid)
        return
    if info.get("em_combate"):
        socketio.emit("coliseuAdversarios", {"adversarios": [], "mensagem": "Termine o combate atual antes de buscar adversários."}, to=sid)
        return
    char_id = str(info.get("char_id", ""))
    if not ObjectId.is_valid(char_id):
        socketio.emit("coliseuAdversarios", {"adversarios": [], "mensagem": "Não consegui validar seu personagem."}, to=sid)
        return

    try:
        season = ensure_active_season(users_collection, duelos_ativos)
    except Exception:
        app.logger.exception("Falha ao carregar temporada para busca de espelhos")
        socketio.emit("coliseuAdversarios", {"adversarios": [], "mensagem": "O ranqueado está temporariamente indisponível. Tente novamente."}, to=sid)
        return
    if not season or season.get("status") != "ativa":
        socketio.emit("coliseuAdversarios", {"adversarios": [], "mensagem": "A temporada está encerrando partidas em andamento. Tente novamente em instantes."}, to=sid)
        return
    season_number = int(season["numero"])
    try:
        player = _preparar_personagem_temporada(char_id, season_number)
    except Exception:
        app.logger.exception("Falha ao preparar personagem para temporada ranqueada")
        socketio.emit("coliseuAdversarios", {"adversarios": [], "mensagem": "Não consegui carregar seus dados de Elo. Tente novamente."}, to=sid)
        return
    if not player:
        socketio.emit("coliseuAdversarios", {"adversarios": [], "mensagem": "Personagem não encontrado."}, to=sid)
        return

    my_points = _elo_points(player)
    try:
        from pvp.season_ranking import build_player_season_rank, current_season_points
        candidates = list(users_collection.find(
            {"_id": {"$ne": ObjectId(char_id)}},
            {"character_name": 1, "name": 1, "nome": 1, "username": 1, "telegram_username": 1, "tg_username": 1, "level": 1, "pvp_points": 1, "pvp_season_number": 1, "pvp_season_matches": 1},
        ))
        docs_candidatos_encontrados = len(candidates)
        candidates = [candidate for candidate in candidates if ObjectId.is_valid(str(candidate.get("_id", "")))]
        candidates_encontrados = len(candidates)
        with duelo_espelho_coliseu_lock:
            espelhos_ocupados = set(espelhos_coliseu_ativos)
        candidates = [candidate for candidate in candidates if str(candidate.get("_id")) not in espelhos_ocupados]
        espelhos_ocupados_count = candidates_encontrados - len(candidates)
        for candidate in candidates:
            candidate["_elo_temporada"] = current_season_points(candidate, season_number)
        candidates.sort(key=lambda candidate: (
            abs(candidate["_elo_temporada"] - my_points),
            _nome_adversario_coliseu(candidate).casefold(),
        ))
        if candidates:
            closest = candidates[:min(20, len(candidates))]
            pool = [candidate for candidate in closest if abs(candidate["_elo_temporada"] - my_points) <= 400]
            if len(pool) < min(5, len(closest)):
                pool = [candidate for candidate in closest if abs(candidate["_elo_temporada"] - my_points) <= 1000]
            if len(pool) < min(5, len(closest)):
                pool = closest
            chosen = random.sample(pool, min(5, len(pool)))
        else:
            chosen = []
        adversarios = []
        for candidate in chosen:
            rank = build_player_season_rank({
                "nome": _nome_adversario_coliseu(candidate),
                "nivel": max(1, _safe_int(candidate.get("level"), 1)),
                "pontos": candidate["_elo_temporada"],
            })
            adversarios.append({
                "id": str(candidate["_id"]),
                "nome": _nome_adversario_coliseu(candidate),
                "level": max(1, _safe_int(candidate.get("level"), 1)),
                "pontos": candidate["_elo_temporada"],
                "elo": rank["elo"],
                "elo_completo": rank["elo_completo"],
                "icone": rank["icone"],
            })
        if not adversarios:
            app.logger.warning(
                "Busca do Coliseu sem adversários: documentos=%d, fichas_validas=%d, espelhos_ocupados=%d",
                docs_candidatos_encontrados,
                candidates_encontrados,
                espelhos_ocupados_count,
            )
    except Exception:
        app.logger.exception("Falha ao buscar espelhos do Coliseu")
        socketio.emit("coliseuAdversarios", {"adversarios": [], "mensagem": "Não foi possível buscar adversários agora."}, to=sid)
        return

    mensagem = "Adversários carregados do cadastro, inclusive os que estão offline." if adversarios else (
        "Todas as outras contas estão em batalha agora. Tente novamente em instantes."
        if espelhos_ocupados_count else
        "Não encontrei outras contas cadastradas no PvP."
    )
    socketio.emit("coliseuAdversarios", {"adversarios": adversarios, "mensagem": mensagem}, to=sid)


@socketio.on("atacarEspelhoColiseu")
def handle_atacar_espelho_coliseu(data):
    sid = request.sid
    info = jogadores_online.get(sid)
    target_id = str((data or {}).get("oponente_id", ""))
    if not info:
        socketio.emit("coliseuErro", {"mensagem": "Entre no jogo para iniciar o PvP ranqueado."}, to=sid)
        return
    if info.get("em_combate"):
        socketio.emit("coliseuErro", {"mensagem": "Você já está em combate."}, to=sid)
        return
    my_id = str(info.get("char_id", ""))
    if not ObjectId.is_valid(my_id) or not ObjectId.is_valid(target_id) or my_id == target_id:
        socketio.emit("coliseuErro", {"mensagem": "Adversário inválido. Atualize a lista e tente de novo."}, to=sid)
        return

    try:
        season = ensure_active_season(users_collection, duelos_ativos)
        if not season or season.get("status") != "ativa":
            socketio.emit("coliseuErro", {"mensagem": "A temporada está encerrando as partidas em andamento. Tente novamente em instantes."}, to=sid)
            return
        season_number = int(season["numero"])
        player_a = _preparar_personagem_temporada(my_id, season_number)
        player_b = _preparar_personagem_temporada(target_id, season_number)
    except Exception:
        app.logger.exception("Falha ao carregar participantes do espelho do Coliseu")
        socketio.emit("coliseuErro", {"mensagem": "Não consegui carregar os dados para essa luta. Atualize a lista e tente de novo."}, to=sid)
        return
    if not player_a or not player_b:
        socketio.emit("coliseuErro", {"mensagem": "Esse personagem não está mais disponível. Atualize a lista."}, to=sid)
        return

    duel_id = None
    try:
        stats_a = get_combat_stats_sync(player_a)
        stats_b = get_combat_stats_sync(player_b)
        player_a = aplicar_combat_stats_no_player(player_a, stats_a)
        player_b = aplicar_combat_stats_no_player(player_b, stats_b)
        player_a["character_name"] = _nome_personagem_db(player_a) or "Herói"
        player_b["character_name"] = _nome_adversario_coliseu(player_b)
        # Espelhos representam a defesa completa salva, não o HP que o dono deixou ao sair.
        stats_b["current_hp"] = stats_b.get("max_hp", 1)
        stats_b["current_mp"] = stats_b.get("max_mana", 10)
        player_b["current_hp"] = stats_b["current_hp"]
        player_b["current_mp"] = stats_b["current_mp"]
        hp_a = max(1, int(stats_a.get("current_hp", stats_a.get("max_hp", 1))))
        hp_b = max(1, int(stats_b.get("max_hp", 1)))
        duel_id = f"coliseu_espelho_{uuid4().hex}"
        mirror_sid = f"espelho:{target_id}:{uuid4().hex}"
        with duelo_espelho_coliseu_lock:
            info_atual = jogadores_online.get(sid)
            if not info_atual or info_atual.get("em_combate") or target_id in espelhos_coliseu_ativos:
                socketio.emit("coliseuErro", {"mensagem": "Esse guerreiro já foi convocado para outra batalha. Escolha outro rival."}, to=sid)
                return
            consumo = _consumir_entradas_coliseu([my_id])
            if not consumo.get("sucesso"):
                socketio.emit("coliseuErro", {"mensagem": _mensagem_sem_entrada_coliseu(my_id)}, to=sid)
                _emitir_cota_coliseu(sid)
                return
            info_atual["em_combate"] = True
            espelhos_coliseu_ativos.add(target_id)
            duelos_ativos[duel_id] = {
                "id": duel_id,
                "modo": "ranqueado",
                "espelho": True,
                "season_number": season_number,
                "jogador_a": {"sid": sid, "db": player_a, "stats": stats_a, "hp": hp_a, "mp": stats_a.get("current_mp", stats_a.get("max_mana", 50))},
                "jogador_b": {"sid": mirror_sid, "db": player_b, "stats": stats_b, "hp": hp_b, "mp": stats_b.get("current_mp", stats_b.get("max_mana", 50)), "espelho": True},
                "turno_de": sid,
            }
        _emitir_cota_coliseu(sid)
        socketio.emit("iniciarArenaPvP", {
            "duelo_id": duel_id,
            "regiao": info.get("regiao", "capital_eldora"),
            "oponente_nome": _nome_personagem_db(player_b) or "Herói",
            "oponente_skin": _skin_personagem_salvo(player_b),
            "oponente_level": player_b.get("level", 1),
            "oponente_hp": hp_b,
            "oponente_max_hp": stats_b.get("max_hp", 1),
            "meu_level": player_a.get("level", 1),
            "meu_hp": hp_a,
            "meu_max_hp": stats_a.get("max_hp", 1),
            "meu_mp": stats_a.get("current_mp", stats_a.get("max_mana", 50)),
            "meu_max_mp": stats_a.get("max_mana", 50),
            "minha_vez": True,
            "modo_pvp": "ranqueado",
            "espelho": True,
        }, to=sid)
    except Exception:
        app.logger.exception("Falha ao iniciar luta contra espelho do Coliseu")
        if duel_id:
            duelos_ativos.pop(duel_id, None)
        if sid in jogadores_online:
            jogadores_online[sid]["em_combate"] = False
        with duelo_espelho_coliseu_lock:
            espelhos_coliseu_ativos.discard(target_id)
        socketio.emit("coliseuErro", {"mensagem": "Não foi possível preparar o combate. Tente novamente."}, to=sid)


@socketio.on("buscarFilaColiseu")
def handle_buscar_fila_coliseu(data):
    global fila_coliseu_evento_id
    sid = request.sid
    modo = (data or {}).get("modo")
    if modo != "evento":
        if modo == "ranqueado":
            _emitir_fila_coliseu(sid, "erro", "O ranqueado acontece por desafios diretos. A fila abre somente durante os eventos.", modo)
            return
        _emitir_fila_coliseu(sid, "erro", "Modalidade inválida.")
        return
    info = jogadores_online.get(sid)
    if not info:
        _emitir_fila_coliseu(sid, "erro", "Entre no jogo para participar da fila do evento.", modo)
        return
    if info.get("regiao") != "capital_eldora" or not _esta_no_portao_coliseu(info):
        _emitir_fila_coliseu(sid, "erro", "Aproxime-se do portão do Coliseu, na Capital de Eldora.", modo)
        return
    if info.get("em_combate"):
        _emitir_fila_coliseu(sid, "erro", "Você já está em combate.", modo)
        return
    if not ObjectId.is_valid(str(info.get("char_id"))):
        _emitir_fila_coliseu(sid, "erro", "Não consegui validar seu personagem.", modo)
        return
    jogador = users_collection.find_one({"_id": ObjectId(str(info["char_id"]))}, {"pvp_points": 1})
    if not jogador:
        _emitir_fila_coliseu(sid, "erro", "Personagem não encontrado.", modo)
        return

    cota = _resumo_cota_coliseu(info.get("char_id"))
    if cota and cota["restantes"] <= 0 and cota["tickets"] <= 0:
        _emitir_fila_coliseu(sid, "erro", _mensagem_sem_entrada_coliseu(info.get("char_id")), modo)
        _emitir_cota_coliseu(sid)
        return

    agenda = get_event_status()
    if not agenda.get("active"):
        _emitir_fila_coliseu(sid, "erro", "O evento está fechado. Abre terça, quinta e sábado às 20h (Brasília).", modo)
        return
    event_id = agenda.get("event_id")

    candidato = None
    filas_anteriores = []
    agora_mono = time.monotonic()
    with fila_coliseu_lock:
        if fila_coliseu_evento_id != event_id:
            filas_anteriores = list(filas_coliseu["evento"])
            filas_coliseu["evento"].clear()
            for sid_antigo in filas_anteriores:
                fila_coliseu_entrada.pop(sid_antigo, None)
            fila_coliseu_evento_id = event_id
        for fila_existente in filas_coliseu.values():
            fila_existente[:] = [item for item in fila_existente if item != sid]
        fila_coliseu_entrada.pop(sid, None)
        fila = filas_coliseu[modo]
        opcoes = []
        for outro_sid in fila:
            outro = jogadores_online.get(outro_sid)
            if not outro or outro.get("em_combate"):
                continue
            if outro.get("regiao") != "capital_eldora" or not _esta_no_portao_coliseu(outro):
                continue
            if str(outro.get("char_id")) == str(info.get("char_id")):
                continue
            outro_id = str(outro.get("char_id"))
            if not ObjectId.is_valid(outro_id):
                continue
            doc = users_collection.find_one({"_id": ObjectId(outro_id)}, {"pvp_points": 1}) or {}
            diferenca = abs(int(doc.get("pvp_points", 0) or 0) - int(jogador.get("pvp_points", 0) or 0))
            espera = max(agora_mono - fila_coliseu_entrada.get(outro_sid, agora_mono), 0)
            limite = _limite_elo_fila(espera)
            if diferenca <= limite:
                opcoes.append((diferenca, espera, outro_sid))
        if opcoes:
            opcoes.sort(key=lambda item: (item[0], -item[1]))
            candidato = opcoes[0][2]
            fila.remove(candidato)
            fila_coliseu_entrada.pop(candidato, None)
        else:
            fila.append(sid)
            fila_coliseu_entrada[sid] = agora_mono

    for sid_antigo in filas_anteriores:
        if sid_antigo != sid:
            _emitir_fila_coliseu(sid_antigo, "erro", "A edição anterior do evento terminou. Entre novamente na próxima abertura.", "evento")

    if candidato:
        resultado = _iniciar_duelo_coliseu(candidato, sid, modo, event_id)
        if resultado == "cota_esgotada":
            return
        if not resultado:
            _emitir_fila_coliseu(sid, "erro", "Não foi possível preparar a partida. Tente novamente.", modo)
            _emitir_fila_coliseu(candidato, "erro", "O adversário não pôde entrar na partida.", modo)
        return
    _emitir_fila_coliseu(sid, "aguardando", "Na fila. O Coliseu avisará quando encontrar um adversário.", modo)


@socketio.on("sairFilaColiseu")
def handle_sair_fila_coliseu(_data=None):
    sid = request.sid
    _retirar_fila_coliseu(sid)
    _emitir_fila_coliseu(sid, "cancelada", "Busca cancelada.")


def _retirar_fila_coliseu(sid):
    with fila_coliseu_lock:
        for fila in filas_coliseu.values():
            fila[:] = [item for item in fila if item != sid]
        fila_coliseu_entrada.pop(sid, None)

@socketio.on('enviarAcaoPvP')
def handle_acao_pvp(dados):
    sid = request.sid
    duelo_id = dados.get('duelo_id')
    acao = dados.get('acao')
    skill_id = dados.get('skill_id')

    if duelo_id not in duelos_ativos:
        return

    duelo = duelos_ativos[duelo_id]
    if duelo['turno_de'] != sid:
        return

    is_jogador_a = (sid == duelo['jogador_a']['sid'])
    atacante = duelo['jogador_a'] if is_jogador_a else duelo['jogador_b']
    alvo = duelo['jogador_b'] if is_jogador_a else duelo['jogador_a']

    # Usa as funções que já foram importadas no topo!
    atacante['db'], msgs_cd = iniciar_turno(atacante['db'])
    
    log_turno = []
    # Injeta avisos como "Corte Perfurante está pronto!" apenas como texto visual
    for msg in msgs_cd:
        log_turno.append({
            "autor_sid": sid, 
            "texto": msg, 
            "dano": 0, 
            "tipo_skill": "info", # 👈 Mudei de 'suporte' para 'info' para não disparar animação!
            "anim_effect": ""
        })

    vencedor_sid = None
    novo_hp = alvo['hp']

    if acao == 'render_se':
        log_turno.append({"autor_sid": sid, "texto": f"🏳️ {atacante['db'].get('nome', 'O Herói')} se rendeu!", "dano": 0})
        alvo['hp'] = 0
        vencedor_sid = alvo['sid']

    elif acao == 'item':
        item_static = CONSUMABLES_DATA.get(skill_id, {})
        efeitos = item_static.get('effects', {})
        cura_hp = int(efeitos.get('heal', 0))
        cura_mp = int(efeitos.get('mana', efeitos.get('mp', 0)))

        atacante['hp'] = min(atacante['stats'].get('max_hp', 100), atacante['hp'] + cura_hp)
        atacante['mp'] = min(atacante['stats'].get('max_mana', 50), atacante['mp'] + cura_mp)
        
        nome_item = item_static.get('display_name', 'Poção')
        log_turno.append({"autor_sid": sid, "texto": f"🧪 {atacante['db'].get('nome', 'O Herói')} usou {nome_item}!", "dano": 0})
        novo_hp = atacante['hp']

    else:
        # AQUI O ASYNCIO VOLTA, MAS SEM IMPORTS INTERNOS A ATRAPALHAR!
        try: loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        resultado = loop.run_until_complete(processar_acao_combate(
            attacker_pdata=atacante['db'], attacker_stats=atacante['stats'], target_stats=alvo['stats'],
            skill_id=skill_id if acao == 'magia' else None,
            attacker_current_hp=atacante['hp'], attacker_current_mp=atacante['mp']
        ))

        dano_causado = resultado.get('total_damage', 0)
        alvo['hp'] = max(0, alvo['hp'] - dano_causado)
        atacante['mp'] = resultado.get('attacker_mp_left', atacante['mp'])
        novo_hp = alvo['hp']

        for msg in resultado.get('log_messages', []):
            log_turno.append({
                "autor_sid": sid, "texto": msg, "dano": dano_causado if msg == resultado['log_messages'][-1] else 0,
                "anim_effect": resultado.get('anim_effect', ''), "tipo_skill": resultado.get('tipo_skill', '')
            })

    if alvo['hp'] <= 0:
        vencedor_sid = atacante['sid']

    if duelo.get("espelho") and not vencedor_sid:
        # O espelho joga automaticamente depois da ação do jogador; os dois turnos
        # seguem no mesmo pacote para evitar animações concorrentes no navegador.
        espelho = duelo["jogador_b"]
        heroi = duelo["jogador_a"]
        espelho["db"], msgs_espelho = iniciar_turno(espelho["db"])
        for mensagem in msgs_espelho:
            log_turno.append({"autor_sid": espelho["sid"], "texto": mensagem, "dano": 0, "tipo_skill": "info", "anim_effect": ""})

        try:
            loop_espelho = asyncio.new_event_loop()
            try:
                resultado_espelho = loop_espelho.run_until_complete(processar_acao_combate(
                    attacker_pdata=espelho["db"],
                    attacker_stats=espelho["stats"],
                    target_stats=heroi["stats"],
                    skill_id=None,
                    attacker_current_hp=espelho["hp"],
                    attacker_current_mp=espelho["mp"],
                ))
            finally:
                loop_espelho.close()
        except Exception:
            app.logger.exception("Falha na ação automática do espelho do Coliseu")
            log_turno.append({"autor_sid": espelho["sid"], "texto": "O adversário perdeu a concentração e não conseguiu atacar.", "dano": 0, "tipo_skill": "info", "anim_effect": ""})
            resultado_espelho = {"total_damage": 0, "log_messages": [], "attacker_mp_left": espelho["mp"]}

        dano_espelho = max(0, int(resultado_espelho.get("total_damage", 0) or 0))
        heroi["hp"] = max(0, heroi["hp"] - dano_espelho)
        espelho["mp"] = resultado_espelho.get("attacker_mp_left", espelho["mp"])
        mensagens_ataque = resultado_espelho.get("log_messages", [])
        for indice, mensagem in enumerate(mensagens_ataque):
            log_turno.append({
                "autor_sid": espelho["sid"],
                "texto": mensagem,
                "dano": dano_espelho if indice == len(mensagens_ataque) - 1 else 0,
                "anim_effect": resultado_espelho.get("anim_effect", ""),
                "tipo_skill": resultado_espelho.get("tipo_skill", ""),
            })
        if heroi["hp"] <= 0:
            vencedor_sid = espelho["sid"]

    proximo_turno_sid = (duelo["jogador_a"]["sid"] if duelo.get("espelho") else alvo["sid"]) if not vencedor_sid else None
    if not vencedor_sid:
        duelo['turno_de'] = proximo_turno_sid

    pacote_animacao = {
        "log": log_turno,
        "vencedor_sid": vencedor_sid,
        "novo_hp": novo_hp,
        "atacante_sid": sid, 
        "novo_mp": atacante['mp'], 
        "cooldowns": atacante['db'].get('cooldowns', {}), 
        "proximo_turno_sid": proximo_turno_sid
    }

    emit('animarTurnoPvP', pacote_animacao, to=duelo['jogador_a']['sid'])
    if not duelo.get("espelho"):
        emit('animarTurnoPvP', pacote_animacao, to=duelo['jogador_b']['sid'])

    if vencedor_sid:
        _registrar_resultado_coliseu(duelo, vencedor_sid)
        if duelo['jogador_a']['sid'] in jogadores_online: jogadores_online[duelo['jogador_a']['sid']]['em_combate'] = False
        if duelo['jogador_b']['sid'] in jogadores_online: jogadores_online[duelo['jogador_b']['sid']]['em_combate'] = False
        if duelo.get("espelho"):
            with duelo_espelho_coliseu_lock:
                espelhos_coliseu_ativos.discard(str(duelo["jogador_b"]["db"].get("_id")))
        del duelos_ativos[duelo_id]

# 👇 A ROTA QUE ESTAVA EM FALTA PARA A RAID! 👇
@socketio.on('enviarAcaoRaid')
def handle_acao_raid(dados):
    sid = request.sid
    raid_id = dados.get('raid_id')
    acao = dados.get('acao')
    alvo_id = dados.get('alvo_id')
    skill_id = dados.get('skill_id')

    from modules.combat.combat_raid_engine import processar_turno_raid, RAIDS_ATIVAS

    raid_antes = RAIDS_ATIVAS.get(raid_id)

    pacote = processar_turno_raid(
        raid_id,
        sid,
        acao,
        alvo_id,
        skill_id=skill_id
    )

    if not pacote:
        emit('erroGeral', {'mensagem': 'Ação inválida ou turno incorreto na raid.'}, to=sid)
        return

    raid = RAIDS_ATIVAS.get(raid_id) or raid_antes
    if not raid:
        return

    for jogador in raid.get('jogadores', {}).values():
        sid_destino = jogador.get('sid')
        if sid_destino:
            emit('animarTurnoRaid', pacote, to=sid_destino)

    if pacote.get('raid_encerrada'):
        try:
            metadata = raid.get('metadata', {}) or {}
            if metadata.get('tipo_evento') == 'invasao_reino':
                sistema_invasao_mapa.registrar_resultado_raid(raid, pacote)

        except Exception:
            import traceback
            print(
                "🚨 Erro ao registrar resultado da raid da invasão:\n"
                + traceback.format_exc()
            )

        for jogador in raid.get('jogadores', {}).values():
            sid_jogador = jogador.get('sid')
            if sid_jogador in jogadores_online:
                jogadores_online[sid_jogador]['em_combate'] = False

        RAIDS_ATIVAS.pop(raid_id, None)

def loop_agendamento_invasao():
    """Fica em segundo plano checando o relógio para rodar a invasão sozinho"""
    print("⏰ Cronômetro de Invasões ativado! Monitorando os horários do Reino...")
    
    # Lista dos horários exatos em que a invasão deve começar (Formato HH:MM)
    HORARIOS_ALVO = ["08:00", "14:00", "19:00", "23:00"]
    
    while True:
        try:
            agora = datetime.now()
            hora_minuto_atual = agora.strftime("%H:%M")
            
            # Se o relógio bater com um dos horários da lista, solta os monstros!
            if hora_minuto_atual in HORARIOS_ALVO:
                print(f"⚔️ CRON: Horário de Invasão atingido ({hora_minuto_atual})! Iniciando evento...")
                
                # Dispara a invasão passando a lista global de quem está online
                sistema_invasao_mapa.iniciar_invasao(jogadores_online)
                
                # Dorme por 61 segundos para evitar que o loop rode duas vezes no mesmo minuto
                time.sleep(61)
                
        except Exception as e:
            print(f"🚨 Erro no agendador automático de invasão: {str(e)}")
            
        # Checa o relógio a cada 30 segundos para não pesar o processador
        time.sleep(30)


def loop_agendamento_coliseu():
    """Fecha eventos e temporadas mesmo quando nenhum jogador abre o painel."""
    global fila_coliseu_evento_id
    while True:
        try:
            finalizar_eventos_encerrados(users_collection, duelos_ativos)
            from modules.events.dynamic_event_service import close_expired_events
            close_expired_events()
            ensure_active_season(users_collection, duelos_ativos)
            filas_evento_encerradas = []
            with fila_coliseu_lock:
                if not get_event_status().get("active") and filas_coliseu["evento"]:
                    filas_evento_encerradas = list(filas_coliseu["evento"])
                    filas_coliseu["evento"].clear()
                    for sid_antigo in filas_evento_encerradas:
                        fila_coliseu_entrada.pop(sid_antigo, None)
                    fila_coliseu_evento_id = None

            for sid_antigo in filas_evento_encerradas:
                _emitir_fila_coliseu(sid_antigo, "erro", "O horário do evento terminou; a busca foi encerrada.", "evento")
        except Exception:
            app.logger.exception("Falha no agendador do Coliseu PvP")
        time.sleep(30)

# ==============================================================================
# 5. EXECUÇÃO PRINCIPAL (O INTERRUPTOR ÚNICO)
# ==============================================================================
if __name__ == "__main__":
    # 1. Inicia o Bot do Telegram
    bot_thread = Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # 👇 2. NOVO: Inicia o Relógio Automático de Invasões 👇
    cron_invasao_thread = Thread(target=loop_agendamento_invasao, daemon=True)
    cron_invasao_thread.start()

    # Recompensas e reinícios do PvP continuam funcionando sem jogadores online.
    cron_coliseu_thread = Thread(target=loop_agendamento_coliseu, daemon=True)
    cron_coliseu_thread.start()
    
    print("🚀 Servidor Web de Eldora rodando em http://localhost:5000")
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        allow_unsafe_werkzeug=True
    )
