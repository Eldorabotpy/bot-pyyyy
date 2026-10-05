(() => {
    const modal = document.getElementById('coliseu-pvp-modal');
    if (!modal) return;

    const statusText = document.getElementById('coliseu-status');
    const rankedButton = document.getElementById('coliseu-queue-ranked');
    const eventButton = document.getElementById('coliseu-queue-event');
    const cancelButton = document.getElementById('coliseu-cancel-queue');
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
            updateCountdown();
            fillBoard('coliseu-ranked-board', data.ranking || []);
            fillBoard('coliseu-event-board', data.placar_evento || [], true);
            statusText.textContent = 'Escolha uma modalidade. As partidas começam quando outro aventureiro entrar na fila.';
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
        if (mode === 'evento' && !eventSchedule?.active) {
            statusText.textContent = 'O evento está fechado. Ele abre terça, quinta e sábado às 20h, horário de Brasília.';
            return;
        }
        queuedMode = mode;
        rankedButton.disabled = true;
        eventButton.disabled = true;
        cancelButton.hidden = false;
        statusText.textContent = 'Entrando na fila…';
        connection.emit('buscarFilaColiseu', {modo: mode});
    }

    function leaveQueue() {
        const connection = socket();
        if (queuedMode && connection?.connected) connection.emit('sairFilaColiseu', {});
        queuedMode = null;
        rankedButton.disabled = false;
        eventButton.disabled = !eventSchedule?.active;
        cancelButton.hidden = true;
    }

    window.abrirColiseuPvP = async () => {
        modal.hidden = false;
        modal.setAttribute('aria-hidden', 'false');
        window.__coliseuPvPAb = true;
        document.getElementById('coliseu-close').focus();
        await refreshStatus();
    };

    window.fecharColiseuPvP = () => {
        leaveQueue();
        modal.hidden = true;
        modal.setAttribute('aria-hidden', 'true');
        window.__coliseuPvPAb = false;
    };

    rankedButton.addEventListener('click', () => enterQueue('ranqueado'));
    eventButton.addEventListener('click', () => enterQueue('evento'));
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
        socket().on('coliseuFila', data => {
            statusText.textContent = data.mensagem || 'Fila atualizada.';
            if (data.estado === 'aguardando') {
                queuedMode = data.modo || queuedMode;
                rankedButton.disabled = true;
                eventButton.disabled = true;
                cancelButton.hidden = false;
            } else if (data.estado === 'cancelada' || data.estado === 'erro') {
                queuedMode = null;
                rankedButton.disabled = false;
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
            }
        });
    }

    window.setInterval(() => {
        if (!modal.hidden) updateCountdown();
    }, 1000);
})();
