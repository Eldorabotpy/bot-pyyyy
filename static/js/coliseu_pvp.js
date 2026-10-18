(() => {
    const modal = document.getElementById('coliseu-pvp-modal');
    if (!modal) return;

    const statusText = document.getElementById('coliseu-status');
    const eventButton = document.getElementById('coliseu-queue-event');
    const cancelButton = document.getElementById('coliseu-cancel-queue');
    const refreshOpponentsButton = document.getElementById('coliseu-refresh-opponents');
    const opponentList = document.getElementById('coliseu-opponent-list');
    const myRankCard = document.getElementById('coliseu-my-rank');
    const quotaTitle = document.getElementById('coliseu-entry-quota-title');
    const quotaDetail = document.getElementById('coliseu-entry-quota-detail');
    const buyTicketButton = document.getElementById('coliseu-buy-ticket');
    let eventSchedule = null;
    let currentSeason = null;
    let queuedMode = null;
    let opponentSearchTimer = null;

    const socket = () => window.eldoraSocket;
    const showValue = value => value === null || value === undefined ? '—' : String(value);
    const formatPoints = value => new Intl.NumberFormat('pt-BR').format(Number(value) || 0);

    function refreshEntryQuota() {
        const connection = socket();
        if (connection?.connected) connection.emit('consultarCotaColiseu', {});
    }

    function renderEntryQuota(data) {
        if (!quotaTitle || !quotaDetail || !data || data.erro) return;
        const limit = Number(data.limite) || 10;
        const remaining = Math.max(0, Number(data.restantes) || 0);
        const tickets = Math.max(0, Number(data.tickets) || 0);
        quotaTitle.textContent = `Entradas gratuitas hoje: ${formatPoints(remaining)}/${formatPoints(limit)}`;
        if (remaining > 0) {
            quotaDetail.textContent = tickets
                ? `${formatPoints(tickets)} ${tickets === 1 ? 'ticket extra guardado' : 'tickets extras guardados'}; usados depois das entradas gratuitas.`
                : 'Você pode iniciar até 10 lutas por dia. Tickets extras entram após as gratuitas.';
        } else if (tickets > 0) {
            quotaDetail.textContent = `${formatPoints(tickets)} ${tickets === 1 ? 'ticket extra disponível' : 'tickets extras disponíveis'} para continuar lutando hoje.`;
        } else {
            quotaDetail.textContent = 'Suas entradas gratuitas acabaram. Adquira um ticket por 10 💎 na Loja da Flora.';
        }
    }

    function openTicketShop() {
        if (typeof window.abrirLojaReino !== 'function') {
            statusText.textContent = 'A loja está indisponível no momento.';
            return;
        }
        window.fecharColiseuPvP();
        window.abrirLojaReino();
    }

    function renderMyRank(data) {
        if (!data) {
            myRankCard.hidden = true;
            return;
        }

        const emblem = document.getElementById('coliseu-my-rank-emblem');
        const title = document.getElementById('coliseu-my-rank-title');
        const name = document.getElementById('coliseu-my-rank-name');
        const points = document.getElementById('coliseu-my-rank-points');
        const position = document.getElementById('coliseu-my-rank-position');
        const progress = document.getElementById('coliseu-my-rank-progress');
        const next = document.getElementById('coliseu-my-rank-next');
        const remaining = document.getElementById('coliseu-my-rank-remaining');
        const fill = document.getElementById('coliseu-my-rank-fill');
        const record = document.getElementById('coliseu-my-rank-record');
        myRankCard.hidden = false;
        emblem.hidden = true;
        title.textContent = 'Carregando sua patente…';
        name.textContent = '';
        points.textContent = '';
        position.textContent = '';
        position.hidden = true;
        progress.hidden = true;
        record.textContent = '';

        if (!data.participou || !data.patente) {
            title.textContent = 'Sua jornada começa aqui';
            name.textContent = 'Jogue uma partida ranqueada para aparecer na temporada.';
            record.textContent = `Temporada ${data.temporada || ''}`.trim();
            return;
        }

        const rank = data.patente;
        emblem.src = rank.icone;
        emblem.alt = rank.elo_completo;
        emblem.hidden = false;
        emblem.onerror = () => { emblem.hidden = true; };
        title.textContent = rank.elo_completo;
        name.textContent = `${rank.nome} · Nv. ${showValue(rank.nivel)}`;
        points.textContent = `${formatPoints(rank.pontos)} Elo`;
        if (Number(data.posicao_temporada) > 0) {
            position.textContent = `#${formatPoints(data.posicao_temporada)} de ${formatPoints(data.participantes_temporada)}`;
            position.hidden = false;
        }
        record.textContent = `${showValue(rank.vitorias)} vitórias · ${showValue(rank.derrotas)} derrotas`;

        if (rank.proxima_divisao) {
            const percent = Math.max(0, Math.min(100, Number(rank.progresso_percentual) || 0));
            next.textContent = `Próxima patente: ${rank.proxima_divisao}`;
            remaining.textContent = `Faltam ${formatPoints(rank.pontos_para_proxima)} Elo`;
            fill.style.width = `${percent}%`;
            progress.querySelector('[role="progressbar"]').setAttribute('aria-valuenow', String(percent));
            progress.hidden = false;
        } else {
            record.textContent += ' · Patente máxima alcançada';
        }
    }

    function renderMatchHistory(history) {
        const panel = document.getElementById('coliseu-match-history');
        const list = document.getElementById('coliseu-match-history-list');
        const count = document.getElementById('coliseu-match-history-count');
        if (!Array.isArray(history)) {
            panel.hidden = true;
            return;
        }

        panel.hidden = false;
        count.textContent = `${history.length} ${history.length === 1 ? 'partida' : 'partidas'}`;
        list.replaceChildren();
        if (!history.length) {
            const empty = document.createElement('li');
            empty.className = 'coliseu-match-history-empty';
            empty.textContent = 'Suas partidas ranqueadas aparecerão aqui.';
            list.appendChild(empty);
            return;
        }

        for (const match of history) {
            const item = document.createElement('li');
            item.className = `coliseu-match-history-row ${match.vitoria ? 'is-win' : 'is-loss'}`;

            const outcome = document.createElement('span');
            outcome.className = 'coliseu-match-history-outcome';
            outcome.textContent = match.vitoria ? 'VITÓRIA' : 'DERROTA';

            const opponent = document.createElement('span');
            opponent.className = 'coliseu-match-history-opponent';
            const opponentName = document.createElement('strong');
            opponentName.textContent = match.adversario || 'Aventureiro';
            const date = document.createElement('small');
            const dateLabel = match.data
                ? new Date(match.data).toLocaleString('pt-BR', {day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', timeZone: 'America/Sao_Paulo'})
                : 'Data indisponível';
            date.textContent = `Temporada ${showValue(match.temporada)} · ${dateLabel}`;
            opponent.append(opponentName, date);

            const score = document.createElement('span');
            score.className = 'coliseu-match-history-score';
            const delta = Number(match.variacao) || 0;
            const change = document.createElement('strong');
            change.textContent = `${delta > 0 ? '+' : ''}${formatPoints(delta)} Elo`;
            const total = document.createElement('small');
            total.textContent = `${formatPoints(match.pontos)} Elo total`;
            score.append(change, total);

            item.append(outcome, opponent, score);
            list.appendChild(item);
        }
    }

    function clearOpponentSearchTimer() {
        if (opponentSearchTimer !== null) {
            window.clearTimeout(opponentSearchTimer);
            opponentSearchTimer = null;
        }
    }

    function fillBoard(id, rows, eventBoard = false) {
        const list = document.getElementById(id);
        list.replaceChildren();
        if (!rows?.length) {
            const empty = document.createElement('li');
            empty.textContent = eventBoard ? 'Ainda sem vitórias neste evento.' : 'O ranking ainda está vazio.';
            list.appendChild(empty);
            return;
        }
        for (const row of rows) {
            const item = document.createElement('li');
            const place = Number(row.posicao) || 0;
            if (place >= 1 && place <= 3) item.classList.add(`coliseu-board-row-top-${place}`);
            const name = document.createElement('span');
            name.className = 'coliseu-board-name';
            const position = document.createElement('span');
            position.className = 'coliseu-board-position';
            position.textContent = String(place || '—');
            position.title = place ? `${place}º lugar` : 'Posição';
            name.appendChild(position);
            const score = document.createElement('span');
            if (!eventBoard && row.icone) {
                const icon = document.createElement('img');
                icon.src = row.icone;
                icon.alt = '';
                icon.loading = 'lazy';
                const label = document.createElement('span');
                label.textContent = row.nome || 'Herói';
                name.append(icon, label);
            } else {
                const label = document.createElement('span');
                label.textContent = row.nome || 'Herói';
                name.appendChild(label);
            }
            score.textContent = eventBoard
                ? `${showValue(row.vitorias)} vit.`
                : `${showValue(row.pontos)} · ${row.elo_completo || row.elo || ''}`;
            item.append(name, score);
            list.appendChild(item);
        }
    }

    function fillEloDistribution(tiers, total, ownRank) {
        const grid = document.getElementById('coliseu-elo-distribution');
        const totalLabel = document.getElementById('coliseu-elo-total');
        grid.replaceChildren();
        totalLabel.textContent = `${formatPoints(total)} ${Number(total) === 1 ? 'jogador' : 'jogadores'}`;

        if (!tiers.length) {
            const empty = document.createElement('p');
            empty.className = 'coliseu-elo-empty';
            empty.textContent = 'Não foi possível carregar a divisão dos elos.';
            grid.appendChild(empty);
            return;
        }

        for (const tier of tiers) {
            const card = document.createElement('details');
            card.className = `coliseu-elo-card elo-${tier.id || 'bronze'}`;
            card.open = Boolean(ownRank && ownRank.elo_id === tier.id);

            const summary = document.createElement('summary');
            const emblem = document.createElement('img');
            emblem.className = 'coliseu-elo-emblem';
            emblem.src = tier.divisoes?.[0]?.icone || tier.icone;
            emblem.alt = '';
            emblem.loading = 'lazy';

            const title = document.createElement('span');
            title.className = 'coliseu-elo-name';
            title.textContent = tier.nome;

            const count = document.createElement('span');
            count.className = 'coliseu-elo-count';
            count.textContent = formatPoints(tier.quantidade);

            const scoreRange = document.createElement('span');
            scoreRange.className = 'coliseu-elo-range';
            scoreRange.textContent = tier.maximo === null
                ? `${formatPoints(tier.minimo)}+ Elo`
                : `${formatPoints(tier.minimo)}–${formatPoints(tier.maximo)} Elo`;

            summary.append(emblem, title, count, scoreRange);
            card.appendChild(summary);

            const divisions = document.createElement('div');
            divisions.className = 'coliseu-elo-divisions';
            for (const division of tier.divisoes || []) {
                const divisionCard = document.createElement('details');
                divisionCard.className = 'coliseu-division-card';
                const isOwnDivision = Boolean(ownRank && ownRank.elo_completo === division.nome);
                divisionCard.open = isOwnDivision;
                if (isOwnDivision) divisionCard.classList.add('is-current-division');

                const divisionSummary = document.createElement('summary');
                const divisionEmblem = document.createElement('img');
                divisionEmblem.className = 'coliseu-division-emblem';
                divisionEmblem.src = division.icone;
                divisionEmblem.alt = '';
                divisionEmblem.loading = 'lazy';
                const divisionTitle = document.createElement('strong');
                divisionTitle.textContent = division.nome;
                if (isOwnDivision) {
                    const currentTag = document.createElement('span');
                    currentTag.className = 'coliseu-current-division-tag';
                    currentTag.textContent = 'SUA PATENTE';
                    divisionTitle.appendChild(currentTag);
                }
                const divisionCount = document.createElement('span');
                divisionCount.className = 'coliseu-division-count';
                divisionCount.textContent = `${formatPoints(division.quantidade)} ${Number(division.quantidade) === 1 ? 'jogador' : 'jogadores'}`;
                const divisionRange = document.createElement('small');
                divisionRange.textContent = division.maximo === null
                    ? `${formatPoints(division.minimo)}+ Elo`
                    : `${formatPoints(division.minimo)}–${formatPoints(division.maximo)} Elo`;
                divisionSummary.append(divisionEmblem, divisionTitle, divisionCount, divisionRange);
                divisionCard.appendChild(divisionSummary);

                const players = document.createElement('ul');
                players.className = 'coliseu-elo-players';
                if (!division.jogadores?.length) {
                    const empty = document.createElement('li');
                    empty.className = 'coliseu-elo-empty';
                    empty.textContent = 'Ainda sem participantes nesta patente.';
                    players.appendChild(empty);
                } else {
                    for (const player of division.jogadores) {
                        const row = document.createElement('li');
                        const identity = document.createElement('span');
                        identity.className = 'coliseu-elo-player-identity';
                        const name = document.createElement('strong');
                        name.textContent = player.nome || 'Herói';
                        const level = document.createElement('small');
                        level.textContent = `Nv. ${showValue(player.nivel)}`;
                        identity.append(name, level);

                        const stats = document.createElement('span');
                        stats.className = 'coliseu-elo-player-stats';
                        stats.textContent = `${formatPoints(player.pontos)} Elo · ${showValue(player.vitorias)}V/${showValue(player.derrotas)}D`;
                        row.append(identity, stats);
                        players.appendChild(row);
                    }
                }
                divisionCard.appendChild(players);
                divisions.appendChild(divisionCard);
            }
            card.appendChild(divisions);
            grid.appendChild(card);
        }
    }

    function formatDate(value, includeDay = true) {
        if (!value) return 'Horário indisponível';
        const options = includeDay
            ? {weekday: 'long', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', timeZone: 'America/Sao_Paulo'}
            : {hour: '2-digit', minute: '2-digit', timeZone: 'America/Sao_Paulo'};
        return new Date(value).toLocaleString('pt-BR', options);
    }

    function updateSeasonCountdown() {
        const seasonLabel = document.getElementById('coliseu-season-status');
        if (!currentSeason || !seasonLabel) return;

        if (currentSeason.status === 'encerrando') {
            seasonLabel.textContent = `Temporada ${currentSeason.numero} encerrando após as partidas em andamento · Top 3: 50, 20 e 5 gemas.`;
            return;
        }

        const endAt = Date.parse(currentSeason.fim || '');
        if (!Number.isFinite(endAt)) return;
        const seconds = Math.floor((endAt - Date.now()) / 1000);
        if (seconds <= 0) {
            seasonLabel.textContent = `Temporada ${currentSeason.numero} encerrando · Top 3: 50, 20 e 5 gemas.`;
            return;
        }

        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const remaining = days > 0
            ? `${days}d ${hours}h`
            : hours > 0 ? `${hours}h ${minutes}min` : `${Math.max(1, minutes)}min`;
        seasonLabel.textContent = `Temporada ${currentSeason.numero} · restam ${remaining} · encerra ${formatDate(currentSeason.fim)} · Top 3: 50, 20 e 5 gemas.`;
    }

    function updateCountdown() {
        updateSeasonCountdown();
        const state = document.getElementById('coliseu-event-state');
        const countdown = document.getElementById('coliseu-event-countdown');
        const dot = modal.querySelector('.coliseu-live-dot');
        if (!eventSchedule) return;
        if (eventSchedule.active && eventSchedule.ends_at) {
            const seconds = Math.max(0, Math.floor((new Date(eventSchedule.ends_at).getTime() - Date.now()) / 1000));
            if (seconds === 0) {
                eventSchedule.active = false;
                state.textContent = 'ENCERRADO';
                dot.classList.remove('is-live');
                countdown.textContent = 'Esta edição terminou. Consulte a próxima data da agenda.';
                eventButton.disabled = true;
                if (queuedMode === 'evento') {
                    leaveQueue();
                    statusText.textContent = 'O evento encerrou e sua busca foi cancelada.';
                }
                eventSchedule = null;
                return;
            }
            state.textContent = 'AO VIVO';
            dot.classList.add('is-live');
            countdown.textContent = `Encerra em ${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')} · aberto por uma hora.`;
            eventButton.disabled = false;
        } else {
            state.textContent = eventSchedule.starts_at ? `Próximo: ${formatDate(eventSchedule.starts_at)}` : 'Agenda indisponível';
            dot.classList.remove('is-live');
            countdown.textContent = 'Abre terça, quinta e sábado às 20h (Brasília) por uma hora.';
            eventButton.disabled = true;
        }
    }

    async function refreshStatus() {
        statusText.textContent = 'Consultando agenda do Coliseu…';
        try {
            const response = await fetch('/api/pvp/coliseu/status', {cache: 'no-store'});
            if (!response.ok) throw new Error('Agenda indisponível no momento.');
            const data = await response.json();
            eventSchedule = data.evento || null;
            currentSeason = data.temporada || null;
            document.getElementById('coliseu-event-schedule').textContent = 'Terça, quinta e sábado · 20h · horário de Brasília';
            document.getElementById('coliseu-event-board-title').textContent = eventSchedule?.active ? 'Evento atual' : 'Último evento';
            updateCountdown();
            fillBoard('coliseu-ranked-board', data.ranking || []);
            fillBoard('coliseu-event-board', data.placar_evento || [], true);
            fillEloDistribution(data.elos_temporada || [], data.participantes_temporada || 0, data.minha_patente?.patente || null);
            renderMyRank(data.minha_patente);
            renderMatchHistory(data.historico_pessoal);
            updateSeasonCountdown();
            refreshEntryQuota();
        } catch (error) {
            eventSchedule = null;
            eventButton.disabled = true;
            statusText.textContent = error.message || 'Não foi possível carregar o Coliseu.';
        }
    }

    function enterQueue(mode) {
        const connection = socket();
        if (!connection?.connected) {
            statusText.textContent = 'Reconectando ao mapa. Tente novamente em alguns segundos.';
            return;
        }
        if (mode !== 'evento') {
            statusText.textContent = 'O ranqueado é disputado em desafios diretos. Escolha seu próximo rival na lista.';
            return;
        }
        if (!eventSchedule?.active) {
            statusText.textContent = 'O evento está fechado. Ele abre terça, quinta e sábado às 20h, horário de Brasília.';
            return;
        }
        queuedMode = mode;
        eventButton.disabled = true;
        cancelButton.hidden = false;
        statusText.textContent = 'Entrando na fila…';
        connection.emit('buscarFilaColiseu', {modo: mode});
    }

    function refreshOpponents() {
        const connection = socket();
        if (!connection?.connected) {
            statusText.textContent = 'Conectando ao jogo. Aguarde alguns segundos e tente novamente.';
            return;
        }
        clearOpponentSearchTimer();
        opponentList.replaceChildren();
        const loading = document.createElement('li');
        loading.textContent = 'Buscando contas registradas, inclusive offline…';
        opponentList.appendChild(loading);
        refreshOpponentsButton.disabled = true;
        statusText.textContent = 'Buscando contas registradas, inclusive offline…';
        opponentSearchTimer = window.setTimeout(() => {
            opponentSearchTimer = null;
            refreshOpponentsButton.disabled = false;
            statusText.textContent = 'A busca não respondeu. Verifique sua conexão com o jogo e tente novamente.';
            opponentList.replaceChildren();
            const empty = document.createElement('li');
            empty.textContent = 'O servidor não respondeu à busca. Tente novamente em alguns segundos.';
            opponentList.appendChild(empty);
        }, 15000);
        connection.emit('buscarAdversariosColiseu', {});
    }

    function renderOpponents(data) {
        clearOpponentSearchTimer();
        opponentList.replaceChildren();
        const adversarios = Array.isArray(data?.adversarios) ? data.adversarios : [];
        statusText.textContent = data?.mensagem || 'Lista de adversários atualizada.';
        refreshOpponentsButton.disabled = false;
        if (!adversarios.length) {
            const empty = document.createElement('li');
            empty.textContent = data?.mensagem || 'Nenhum adversário disponível no momento.';
            opponentList.appendChild(empty);
            return;
        }
        for (const opponent of adversarios) {
            const row = document.createElement('li');
            const emblem = document.createElement('img');
            emblem.className = 'coliseu-opponent-emblem';
            emblem.src = opponent.icone || '';
            emblem.alt = opponent.elo_completo || opponent.elo || 'Patente';
            emblem.loading = 'lazy';
            emblem.onerror = () => { emblem.hidden = true; };
            const info = document.createElement('div');
            info.className = 'coliseu-opponent-info';
            const name = document.createElement('strong');
            name.textContent = opponent.nome || 'Herói';
            const detail = document.createElement('span');
            detail.textContent = `${showValue(opponent.elo_completo || opponent.elo)} · ${formatPoints(opponent.pontos)} Elo`;
            const attack = document.createElement('button');
            attack.type = 'button';
            attack.textContent = '⚔️ DESAFIAR';
            attack.dataset.opponentId = opponent.id;
            attack.addEventListener('click', () => {
                const connection = socket();
                if (!connection?.connected) {
                    statusText.textContent = 'A conexão com o jogo foi perdida. Reconecte e tente novamente.';
                    return;
                }
                opponentList.querySelectorAll('button').forEach(button => { button.disabled = true; });
                statusText.textContent = `Convocando ${name.textContent} para o duelo…`;
                connection.emit('atacarEspelhoColiseu', {oponente_id: attack.dataset.opponentId});
            });
            info.append(name, detail);
            row.append(emblem, info, attack);
            opponentList.appendChild(row);
        }
    }

    function leaveQueue() {
        const connection = socket();
        if (queuedMode && connection?.connected) connection.emit('sairFilaColiseu', {});
        queuedMode = null;
        eventButton.disabled = !eventSchedule?.active;
        cancelButton.hidden = true;
    }

    window.abrirColiseuPvP = async () => {
        if (typeof window.ocultarMenuGlobalEldora === 'function') window.ocultarMenuGlobalEldora();
        modal.hidden = false;
        modal.setAttribute('aria-hidden', 'false');
        window.__coliseuPvPAb = true;
        document.getElementById('coliseu-close').focus();
        await Promise.all([refreshStatus(), Promise.resolve(refreshOpponents())]);
    };

    window.fecharColiseuPvP = () => {
        leaveQueue();
        clearOpponentSearchTimer();
        modal.hidden = true;
        modal.setAttribute('aria-hidden', 'true');
        window.__coliseuPvPAb = false;
        if (typeof window.mostrarMenuGlobalEldora === 'function') window.mostrarMenuGlobalEldora();
    };

    eventButton.addEventListener('click', () => enterQueue('evento'));
    buyTicketButton?.addEventListener('click', openTicketShop);
    refreshOpponentsButton.addEventListener('click', refreshOpponents);
    cancelButton.addEventListener('click', () => {
        leaveQueue();
        statusText.textContent = 'Busca cancelada.';
    });
    document.getElementById('coliseu-close').addEventListener('click', window.fecharColiseuPvP);
    modal.addEventListener('click', event => {
        if (event.target === modal) window.fecharColiseuPvP();
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && !modal.hidden) window.fecharColiseuPvP();
    });

    if (socket()) {
        socket().on('coliseuAdversarios', renderOpponents);
        socket().on('coliseuErro', data => {
            statusText.textContent = data?.mensagem || 'Não foi possível iniciar essa batalha.';
            refreshOpponentsButton.disabled = false;
            opponentList.querySelectorAll('button').forEach(button => { button.disabled = false; });
            refreshEntryQuota();
        });
        socket().on('coliseuCota', renderEntryQuota);
        socket().on('coliseuFila', data => {
            statusText.textContent = data.mensagem || 'Fila atualizada.';
            if (data.estado === 'aguardando') {
                queuedMode = data.modo || queuedMode;
                eventButton.disabled = true;
                cancelButton.hidden = false;
            } else if (data.estado === 'cancelada' || data.estado === 'erro') {
                queuedMode = null;
                eventButton.disabled = !eventSchedule?.active;
                cancelButton.hidden = true;
                refreshEntryQuota();
            } else if (data.estado === 'iniciada') {
                queuedMode = null;
                cancelButton.hidden = true;
                refreshEntryQuota();
            }
        });
        socket().on('coliseuResultado', data => {
            refreshStatus();
            refreshEntryQuota();
            if (modal.hidden && typeof window.adicionarLogPvP === 'function') {
                const texto = data.modo === 'ranqueado'
                    ? `📊 PvP ranqueado: ${data.delta >= 0 ? '+' : ''}${data.delta} Elo · total ${data.pontos}.`
                    : `🏟️ ${data.vitoria ? 'Vitória registrada' : 'Partida registrada'} no evento do Coliseu.`;
                setTimeout(() => window.adicionarLogPvP(`<span style="color:#e7d49f">${texto}</span>`), 1400);
            } else if (data.modo === 'ranqueado') {
                statusText.textContent = `Partida concluída: ${data.delta >= 0 ? '+' : ''}${data.delta} Elo · total ${data.pontos}.`;
            } else if (data.modo === 'evento') {
                statusText.textContent = data.vitoria
                    ? 'Vitória registrada no evento. O placar foi atualizado.'
                    : 'Partida registrada no placar do evento.';
            }
        });
    }

    window.setInterval(() => {
        if (!modal.hidden) updateCountdown();
    }, 1000);
})();
