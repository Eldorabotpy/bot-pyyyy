const NIVEIS_POR_PAGINA = 20;
const NIVEIS_PASSE = 100;
const CUSTO_PREMIUM_PASSE = 500;
let paginaPasseAtual = 0;
let totalNiveisPasse = 0;
let dadosPasseAtual = null;
let acaoPasseEmAndamento = false;

function obterIdPersonagemPasse() {
    return String(window.eldoraCharacterId || localStorage.getItem('jogadorEldoraID') || '');
}

function mostrarMensagemPasse(texto, tipo = 'info', permitirTentarNovamente = false) {
    const aviso = document.getElementById('pass-message');
    if (!aviso) return;
    aviso.replaceChildren();
    aviso.className = `pass-message ${tipo}`;
    aviso.hidden = !texto;
    if (!texto) return;

    const conteudo = document.createElement('span');
    conteudo.textContent = texto;
    aviso.appendChild(conteudo);
    if (permitirTentarNovamente) {
        const tentar = document.createElement('button');
        tentar.type = 'button';
        tentar.className = 'pass-retry';
        tentar.textContent = 'Tentar novamente';
        tentar.addEventListener('click', carregarPasse);
        aviso.appendChild(tentar);
    }
}

function definirCarregamento(ativo) {
    const lista = document.getElementById('lista-recompensas');
    const coleta = document.getElementById('btn-coletar-tudo');
    const premium = document.getElementById('btn-comprar-premium');
    if (coleta) coleta.disabled = ativo || !dadosPasseAtual;
    if (premium && ativo) premium.disabled = true;
    if (ativo && lista) {
        lista.replaceChildren();
        const loading = document.createElement('div');
        loading.className = 'pass-loading';
        loading.setAttribute('role', 'status');
        loading.textContent = 'Consultando a trilha...';
        lista.appendChild(loading);
    }
}

async function carregarPasse() {
    dadosPasseAtual = null;
    definirCarregamento(true);
    mostrarMensagemPasse('');

    try {
        const sessao = await window.portalSessionReady;
        if (!sessao?.authenticated) {
            throw new Error('Entre na sua conta Eldora para consultar o Passe de Batalha.');
        }

        const userId = obterIdPersonagemPasse();
        if (!userId) throw new Error('Selecione um personagem antes de abrir o Passe.');

        const response = await fetch(`/api/passe/status/${encodeURIComponent(userId)}`, { cache: 'no-store' });
        const data = await response.json();
        if (!response.ok || data.erro) throw new Error(data.erro || 'Não foi possível carregar o Passe.');
        if (!data.status || !data.catalogo) throw new Error('O servidor retornou dados incompletos do Passe.');

        dadosPasseAtual = data;
        atualizarCabecalhoPasse(data.status);
        desenharRecompensas(data.status, data.catalogo);
        atualizarCompraPremium(data.status);
        mostrarMensagemPasse('');
    } catch (erro) {
        console.error('Falha ao carregar o Passe:', erro);
        const lista = document.getElementById('lista-recompensas');
        if (lista) {
            lista.replaceChildren();
            const estado = document.createElement('div');
            estado.className = 'pass-empty-state';
            estado.textContent = 'As recompensas aparecem aqui assim que a conexão for restabelecida.';
            lista.appendChild(estado);
        }
        mostrarMensagemPasse(erro.message || 'Falha de conexão com o Passe.', 'error', true);
    } finally {
        definirCarregamento(false);
    }
}

function atualizarCabecalhoPasse(passe) {
    const nivel = Math.min(NIVEIS_PASSE, Math.max(1, Number(passe.level) || 1));
    const xp = Math.max(0, Number(passe.xp) || 0);
    const concluido = nivel >= NIVEIS_PASSE;
    const xpAtual = concluido ? 100 : Math.min(99, xp);
    const badge = document.getElementById('display-nivel-atual');
    const progress = document.getElementById('barra-progresso');
    const progressContainer = progress?.parentElement;
    const xpText = document.getElementById('texto-xp');

    if (badge) badge.textContent = `NÍVEL ${nivel} / ${NIVEIS_PASSE}`;
    if (progress) progress.style.width = `${xpAtual}%`;
    if (progressContainer) progressContainer.setAttribute('aria-valuenow', String(xpAtual));
    if (xpText) xpText.textContent = concluido ? 'Trilha concluída' : `${xpAtual} / 100 XP`;

    const fragmentos = document.getElementById('fragmentos-skin-passe');
    if (fragmentos) fragmentos.textContent = Math.max(0, Number(passe.skin_fragments) || 0).toLocaleString('pt-BR');
}

function atualizarCompraPremium(passe) {
    const status = document.getElementById('status-premium');
    const botao = document.getElementById('btn-comprar-premium');
    if (status) {
        status.textContent = passe.is_premium ? 'Passe Premium ativo' : 'Passe gratuito';
        status.classList.toggle('premium', Boolean(passe.is_premium));
    }
    if (!botao) return;

    if (passe.is_premium) {
        botao.hidden = true;
        botao.onclick = null;
    } else {
        botao.hidden = false;
        botao.disabled = Number(passe.gems) < CUSTO_PREMIUM_PASSE;
        botao.textContent = Number(passe.gems) < CUSTO_PREMIUM_PASSE
            ? `Premium · ${Number(passe.gems || 0).toLocaleString('pt-BR')} / ${CUSTO_PREMIUM_PASSE} 💎`
            : `Ativar Premium · ${CUSTO_PREMIUM_PASSE} 💎`;
        botao.onclick = comprarPassePremium;
    }
}

function criarRecompensa(nivel, tipo, recompensa, jaResgatou, nivelAlcancado, premiumAtivo, fragmentos, imagemFragmento) {
    const faixaPremium = tipo === 'premium';
    const bloqueada = faixaPremium && !premiumAtivo;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `reward-box reward-${tipo} ${jaResgatou ? 'resgatado' : ''} ${bloqueada ? 'locked' : ''} ${nivelAlcancado ? 'available' : 'unreached'}`;
    button.disabled = jaResgatou || !nivelAlcancado || bloqueada || acaoPasseEmAndamento;
    button.setAttribute('aria-label', `${faixaPremium ? 'Premium' : 'Grátis'}, nível ${nivel}: ${jaResgatou ? 'já resgatado' : recompensa.label}`);

    const art = document.createElement('span');
    art.className = `reward-art ${recompensa.tipo === 'gold' ? 'currency-gold' : ''}`;
    art.setAttribute('aria-hidden', 'true');
    const fallback = document.createElement('span');
    fallback.className = 'reward-art-fallback';
    fallback.textContent = recompensa.tipo === 'gold' ? '🪙' : recompensa.tipo === 'gems' ? '💎' : recompensa.tipo === 'banner' ? '⚑' : '✦';
    art.appendChild(fallback);
    if (recompensa.image_url) {
        const image = document.createElement('img');
        image.loading = 'lazy';
        image.decoding = 'async';
        image.src = recompensa.image_url;
        image.alt = '';
        image.addEventListener('load', () => { fallback.hidden = true; });
        image.addEventListener('error', () => { image.hidden = true; });
        art.appendChild(image);
    }

    const copy = document.createElement('span');
    copy.className = 'reward-copy';
    const faixa = document.createElement('small');
    faixa.textContent = faixaPremium ? 'PREMIUM' : 'GRÁTIS';
    const nome = document.createElement('span');
    nome.className = 'reward-name';
    nome.textContent = jaResgatou ? '✓ Resgatado' : recompensa.label;
    copy.append(faixa, nome);

    if (fragmentos > 0 && !jaResgatou) {
        const extra = document.createElement('span');
        extra.className = 'pass-fragment-reward';
        if (imagemFragmento) {
            const image = document.createElement('img');
            image.loading = 'lazy';
            image.decoding = 'async';
            image.src = imagemFragmento;
            image.alt = '';
            image.addEventListener('error', () => { image.hidden = true; });
            extra.appendChild(image);
        }
        const extraText = document.createElement('span');
        extraText.textContent = `+${fragmentos} fragmento${fragmentos === 1 ? '' : 's'} para a loja`;
        extra.appendChild(extraText);
        copy.appendChild(extra);
    }

    button.append(art, copy);
    if (bloqueada) {
        const lock = document.createElement('span');
        lock.className = 'reward-lock';
        lock.setAttribute('aria-hidden', 'true');
        lock.innerHTML = '<svg viewBox="0 0 16 18" focusable="false"><path d="M4 7V5a4 4 0 0 1 8 0v2"/><rect x="2" y="7" width="12" height="9" rx="2"/></svg>';
        button.appendChild(lock);
    }

    if (!button.disabled) {
        button.addEventListener('click', () => resgatarPremio(nivel, tipo));
    }
    return button;
}

function desenharRecompensas(passe, catalogo) {
    const lista = document.getElementById('lista-recompensas');
    const controles = document.getElementById('controles-pagina-passe');
    if (!lista || !controles) return;

    lista.replaceChildren();
    controles.replaceChildren();
    const niveis = Object.keys(catalogo).map(Number).filter(Number.isFinite).sort((a, b) => a - b);
    totalNiveisPasse = niveis.length;
    paginaPasseAtual = Math.min(paginaPasseAtual, Math.max(0, Math.ceil(totalNiveisPasse / NIVEIS_POR_PAGINA) - 1));

    if (!niveis.length) {
        const vazio = document.createElement('div');
        vazio.className = 'pass-empty-state';
        vazio.textContent = 'Ainda não há recompensas configuradas nesta trilha.';
        lista.appendChild(vazio);
        return;
    }

    const claimedFree = new Set((passe.resgatados_free || []).map(Number));
    const claimedPremium = new Set((passe.resgatados_premium || []).map(Number));
    const nivelAtual = Math.min(NIVEIS_PASSE, Math.max(1, Number(passe.level) || 1));
    const start = paginaPasseAtual * NIVEIS_POR_PAGINA;
    const pageLevels = niveis.slice(start, start + NIVEIS_POR_PAGINA);

    pageLevels.forEach((nivel) => {
        const config = catalogo[nivel] || catalogo[String(nivel)];
        if (!config?.free || !config?.premium) return;

        const row = document.createElement('article');
        row.className = `reward-row ${nivelAtual >= nivel ? 'completed' : ''}`;
        row.setAttribute('aria-label', `Nível ${nivel}`);
        row.appendChild(criarRecompensa(
            nivel, 'free', config.free, claimedFree.has(nivel), nivelAtual >= nivel, Boolean(passe.is_premium),
            Number(config.fragmentos_skin?.free) || 0, config.fragmentos_skin?.image_url
        ));

        const center = document.createElement('div');
        center.className = 'reward-level-center';
        const diamond = document.createElement('span');
        diamond.className = 'level-diamond';
        const diamondNumber = document.createElement('span');
        diamondNumber.textContent = String(nivel);
        diamond.appendChild(diamondNumber);
        center.appendChild(diamond);
        row.appendChild(center);

        row.appendChild(criarRecompensa(
            nivel, 'premium', config.premium, claimedPremium.has(nivel), nivelAtual >= nivel, Boolean(passe.is_premium),
            Number(config.fragmentos_skin?.premium) || 0, config.fragmentos_skin?.image_url
        ));
        lista.appendChild(row);
    });

    const totalPages = Math.max(1, Math.ceil(totalNiveisPasse / NIVEIS_POR_PAGINA));
    const firstLevel = start + 1;
    const lastLevel = Math.min(start + NIVEIS_POR_PAGINA, totalNiveisPasse);
    const previous = document.createElement('button');
    previous.type = 'button';
    previous.textContent = '← Anteriores';
    previous.disabled = paginaPasseAtual === 0;
    previous.addEventListener('click', () => mudarPaginaPasse(-1));
    const range = document.createElement('span');
    range.textContent = `${firstLevel}–${lastLevel} de ${totalNiveisPasse}`;
    const next = document.createElement('button');
    next.type = 'button';
    next.textContent = 'Próximos →';
    next.disabled = paginaPasseAtual >= totalPages - 1;
    next.addEventListener('click', () => mudarPaginaPasse(1));
    controles.append(previous, range, next);
}

function mudarPaginaPasse(delta) {
    const totalPaginas = Math.ceil(totalNiveisPasse / NIVEIS_POR_PAGINA);
    paginaPasseAtual = Math.max(0, Math.min(totalPaginas - 1, paginaPasseAtual + delta));
    if (dadosPasseAtual) desenharRecompensas(dadosPasseAtual.status, dadosPasseAtual.catalogo);
}

async function enviarAcaoPasse(url, payload) {
    const headers = await window.portalSessionHeaders({ 'Content-Type': 'application/json' });
    const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify({ user_id: obterIdPersonagemPasse(), ...payload }),
    });
    const data = await response.json();
    return { response, data };
}

async function resgatarPremio(nivel, tipo) {
    if (acaoPasseEmAndamento) return;
    acaoPasseEmAndamento = true;
    desenharRecompensas(dadosPasseAtual.status, dadosPasseAtual.catalogo);
    try {
        const { response, data } = await enviarAcaoPasse('/api/passe/resgatar', { nivel, tipo });
        if (!response.ok || data.status !== 'success') throw new Error(data.message || 'Não foi possível resgatar a recompensa.');
        alertaPasseEldora('Recompensa resgatada', data.message, true);
        await carregarPasse();
    } catch (erro) {
        alertaPasseEldora('Não foi possível resgatar', erro.message || 'Falha de comunicação com o servidor.', false);
    } finally {
        acaoPasseEmAndamento = false;
        if (dadosPasseAtual) desenharRecompensas(dadosPasseAtual.status, dadosPasseAtual.catalogo);
    }
}

function comprarPassePremium() {
    const passe = dadosPasseAtual?.status || {};
    if (Number(passe.gems) < CUSTO_PREMIUM_PASSE) {
        alertaPasseEldora('Gemas insuficientes', `Você tem ${Number(passe.gems || 0).toLocaleString('pt-BR')} gemas. São necessárias ${CUSTO_PREMIUM_PASSE}.`, false);
        return;
    }

    let modal = document.getElementById('modal-confirmar-premium');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'modal-confirmar-premium';
        modal.className = 'modal-passe-overlay';
        modal.innerHTML = `
            <section class="modal-passe-box" role="dialog" aria-modal="true" aria-labelledby="premium-title">
                <div class="modal-passe-icon" aria-hidden="true">💎</div>
                <h2 id="premium-title" class="modal-passe-title">Ativar faixa Premium</h2>
                <p class="modal-passe-msg"></p>
                <div class="modal-passe-botoes">
                    <button type="button" class="btn-passe-comprar">Ativar Premium</button>
                    <button type="button" class="btn-passe-cancelar">Agora não</button>
                </div>
            </section>`;
        modal.querySelector('.btn-passe-comprar').addEventListener('click', executarCompraPremium);
        modal.querySelector('.btn-passe-cancelar').addEventListener('click', () => { modal.hidden = true; });
        document.body.appendChild(modal);
    }
    modal.querySelector('.modal-passe-msg').textContent = `Ativar a faixa Premium por ${CUSTO_PREMIUM_PASSE} gemas? Seu saldo atual é ${Number(passe.gems || 0).toLocaleString('pt-BR')} gemas.`;
    modal.hidden = false;
}

async function executarCompraPremium() {
    const modal = document.getElementById('modal-confirmar-premium');
    if (modal) modal.hidden = true;
    if (acaoPasseEmAndamento) return;
    acaoPasseEmAndamento = true;
    try {
        const { response, data } = await enviarAcaoPasse('/api/passe/comprar_premium', {});
        if (!response.ok || !data.sucesso) throw new Error(data.message || 'Não foi possível ativar o Premium.');
        alertaPasseEldora('Faixa Premium ativada', data.message, true);
        await carregarPasse();
    } catch (erro) {
        alertaPasseEldora('Compra não concluída', erro.message || 'Falha de comunicação com o servidor.', false);
    } finally {
        acaoPasseEmAndamento = false;
        if (dadosPasseAtual) desenharRecompensas(dadosPasseAtual.status, dadosPasseAtual.catalogo);
    }
}

function alertaPasseEldora(titulo, mensagem, sucesso = true) {
    let modal = document.getElementById('modal-alerta-passe');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'modal-alerta-passe';
        modal.className = 'modal-passe-overlay';
        modal.innerHTML = `
            <section class="modal-passe-box" role="dialog" aria-modal="true" aria-labelledby="alerta-passe-titulo">
                <div class="modal-passe-icon" aria-hidden="true"></div>
                <h2 id="alerta-passe-titulo" class="modal-passe-title"></h2>
                <p id="alerta-passe-msg" class="modal-passe-msg"></p>
                <button type="button" class="btn-passe-continuar">Continuar</button>
            </section>`;
        modal.querySelector('.btn-passe-continuar').addEventListener('click', () => { modal.hidden = true; });
        document.body.appendChild(modal);
    }
    const cor = sucesso ? '#e4bd69' : '#e66b62';
    const box = modal.querySelector('.modal-passe-box');
    box.style.setProperty('--modal-accent', cor);
    modal.querySelector('.modal-passe-icon').textContent = sucesso ? '✓' : '!';
    modal.querySelector('#alerta-passe-titulo').textContent = titulo;
    modal.querySelector('#alerta-passe-msg').textContent = mensagem;
    modal.hidden = false;
}

async function coletarTudoLiberado() {
    if (acaoPasseEmAndamento) return;
    acaoPasseEmAndamento = true;
    const button = document.getElementById('btn-coletar-tudo');
    const labelOriginal = button?.textContent;
    if (button) {
        button.disabled = true;
        button.textContent = 'Coletando...';
    }
    try {
        const { response, data } = await enviarAcaoPasse('/api/passe/coletar_tudo', {});
        if (!response.ok || !['success', 'info'].includes(data.status)) throw new Error(data.message || 'Não foi possível coletar as recompensas.');
        alertaPasseEldora(data.status === 'success' ? 'Recompensas coletadas' : 'Tudo em dia', data.message, data.status !== 'error');
        await carregarPasse();
    } catch (erro) {
        alertaPasseEldora('Coleta não concluída', erro.message || 'Falha de comunicação com o servidor.', false);
    } finally {
        acaoPasseEmAndamento = false;
        if (button) button.textContent = labelOriginal || 'Coletar recompensas disponíveis';
        if (dadosPasseAtual) desenharRecompensas(dadosPasseAtual.status, dadosPasseAtual.catalogo);
    }
}

document.addEventListener('DOMContentLoaded', carregarPasse);
