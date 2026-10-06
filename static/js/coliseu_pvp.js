(() => {
    const modal = document.getElementById('coliseu-pvp-modal');
    if (!modal) return;

    const statusText = document.getElementById('coliseu-status');
    const eventButton = document.getElementById('coliseu-queue-event');
    const cancelButton = document.getElementById('coliseu-cancel-queue');
    const refreshOpponentsButton = document.getElementById('coliseu-refresh-opponents');
    const opponentList = document.getElementById('coliseu-opponent-list');
    let eventSchedule = null;
    let queuedMode = null;

    const socket = () => window.eldoraSocket;
    const showValue = value => value === null || value === undefined ? '—' : String(value);

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
            const name = document.createElement('span');
            const score = document.createElement('span');
            name.textContent = `${row.posicao}. ${row.nome || 'Herói'}`;
            score.textContent = eventBoard
                ? `${showValue(row.vitorias)} vit.`
                : `${showValue(row.pontos)} · ${row.elo || ''}`;
            item.append(name, score);
            list.appendChild(item);
        }
    }

    function formatDate(value, includeDay = true) {
        if (!value) return 'Horário indisponível';
        const options = includeDay
            ? {weekday: 'long', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', timeZone: 'America/Sao_Paulo'}
            : {hour: '2-digit', minute: '2-digit', timeZone: 'America/Sao_Paulo'};
        return new Date(value).toLocaleString('pt-BR', options);
    }

    function updateCountdown() {
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
            document.getElementById('coliseu-event-schedule').textContent = 'Terça, quinta e sábado · 20h · horário de Brasília';
            document.getElementById('coliseu-event-board-title').textContent = eventSchedule?.active ? 'Evento atual' : 'Último evento';
            updateCountdown();
            fillBoard('coliseu-ranked-board', data.ranking || []);
            fillBoard('coliseu-event-board', data.placar_evento || [], true);
            const season = data.temporada;
            const seasonLabel = document.getElementById('coliseu-season-status');
            if (season) {
                const fim = formatDate(season.fim);
                seasonLabel.textContent = season.status === 'encerrando'
                    ? `Temporada ${season.numero} encerrando após as partidas em andamento. Prêmios do Top 3: 50, 20 e 5 gemas.`
                    : `Temporada ${season.numero} · termina em ${fim} · Top 3: 50, 20 e 5 gemas.`;
            }
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
            statusText.textContent = 'O PvP ranqueado usa espelhos. Busque um adversário na lista, mesmo que ele esteja offline.';
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
        opponentList.replaceChildren();
        const loading = document.createElement('li');
        loading.textContent = 'Buscando personagens próximos no Elo…';
        opponentList.appendChild(loading);
        refreshOpponentsButton.disabled = true;
        statusText.textContent = 'Buscando personagens próximos no Elo…';
        connection.emit('buscarAdversariosColiseu', {});
    }

    function renderOpponents(data) {
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
            const info = document.createElement('div');
            info.className = 'coliseu-opponent-info';
            const name = document.createElement('strong');
            name.textContent = opponent.nome || 'Herói';
            const detail = document.createElement('span');
            detail.textContent = `Nv. ${showValue(opponent.level)} · ${showValue(opponent.elo)} · ${showValue(opponent.pontos)} Elo`;
            const attack = document.createElement('button');
            attack.type = 'button';
            attack.textContent = 'Atacar espelho';
            attack.dataset.opponentId = opponent.id;
            attack.addEventListener('click', () => {
                const connection = socket();
                if (!connection?.connected) {
                    statusText.textContent = 'A conexão com o jogo foi perdida. Reconecte e tente novamente.';
                    return;
                }
                opponentList.querySelectorAll('button').forEach(button => { button.disabled = true; });
                statusText.textContent = `Preparando o espelho de ${name.textContent}…`;
                connection.emit('atacarEspelhoColiseu', {oponente_id: attack.dataset.opponentId});
            });
            info.append(name, detail);
            row.append(info, attack);
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
        modal.hidden = true;
        modal.setAttribute('aria-hidden', 'true');
        window.__coliseuPvPAb = false;
        if (typeof window.mostrarMenuGlobalEldora === 'function') window.mostrarMenuGlobalEldora();
    };

    eventButton.addEventListener('click', () => enterQueue('evento'));
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
        });
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
            } else if (data.estado === 'iniciada') {
                queuedMode = null;
                cancelButton.hidden = true;
            }
        });
        socket().on('coliseuResultado', data => {
            refreshStatus();
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
