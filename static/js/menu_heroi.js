(() => {
    const menu = document.getElementById('side-menu');
    const toggle = document.getElementById('btn-abrir-menu');
    if (!menu || !toggle) return;
    const blockers = '.modal-moderno, .eldora-modal, [role="dialog"], dialog[open], #tela-combate-global, #tela-pvp-global, #tela-raid-invasao, #forja-container, #refinaria-container, #mercado-container, #loja-reino-container, #loja-aventureiro-container, #rpg-dialogo-container, #modal-item';
    let nivelBuscaId = '';
    let perfilCarregadoId = '';
    let nivelBuscaPendente = false;
    let nivelTentarNovamenteEm = 0;
    const visible = el => {
        const style = getComputedStyle(el);
        return !el.hidden && style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity) !== 0 && el.getClientRects().length > 0;
    };
    function carregarPerfilParaNivel() {
        const charId = String(window.eldoraCharacterId || localStorage.getItem('jogadorEldoraID') || '');
        if (!charId) return;
        if (nivelBuscaId !== charId) {
            nivelBuscaId = charId;
            perfilCarregadoId = '';
            nivelTentarNovamenteEm = 0;
        }
        if (perfilCarregadoId === charId || nivelBuscaPendente || Date.now() < nivelTentarNovamenteEm) return;

        nivelBuscaPendente = true;
        fetch(`/perfil/${encodeURIComponent(charId)}?t=${Date.now()}`, { cache: 'no-store' })
            .then(resposta => {
                if (!resposta.ok) throw new Error('Não foi possível carregar o perfil do herói.');
                return resposta.json();
            })
            .then(perfil => {
                if (!perfil || perfil.erro) return;
                const charIdAtual = String(window.eldoraCharacterId || localStorage.getItem('jogadorEldoraID') || '');
                if (charIdAtual !== charId) return;
                perfilCarregadoId = charId;
                window.perfilDadosGlobais = { ...(window.perfilDadosGlobais || {}), ...perfil };
                syncResumoHeroi();
            })
            .catch(() => { nivelTentarNovamenteEm = Date.now() + 15000; })
            .finally(() => { nivelBuscaPendente = false; });
    }
    function syncNivelHeroi() {
        const nivelEl = document.getElementById('eldora-menu-nivel') || document.querySelector('#side-menu .eldora-menu-avatar-selo');
        const perfil = window.perfilDadosGlobais || {};
        const nivel = Number.parseInt(perfil.level ?? perfil.nivel ?? window.eldoraCharacterLevel, 10);
        const nivelValido = Number.isFinite(nivel) && nivel > 0;

        if (nivelEl) {
            const textoNivel = nivelValido ? String(nivel) : '…';
            const tituloNivel = nivelValido ? `Nível ${nivel}` : 'Carregando nível do herói';
            if (nivelEl.textContent !== textoNivel) nivelEl.textContent = textoNivel;
            if (nivelEl.title !== tituloNivel) nivelEl.title = tituloNivel;
        }
    }
    function resolverImagemAvatar(perfil, hudAvatar) {
        let avatar = perfil.avatar_customizado;
        if (avatar && typeof avatar === 'object') avatar = avatar.path || avatar.id || '';

        const catalogo = window.CATALOGO_SISTEMA?.avatares || {};
        if (typeof avatar === 'string' && avatar && avatar !== 'padrao') {
            if (catalogo[avatar]?.path) return catalogo[avatar].path;
            if (/^https?:\/\//i.test(avatar) || avatar.startsWith('/static/')) return avatar;
            const nomeArquivo = avatar.startsWith('avatar_') ? avatar : `avatar_${avatar}`;
            return `https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/avatares/${nomeArquivo}.png`;
        }

        if (typeof perfil.avatar === 'string' && perfil.avatar && perfil.avatar !== 'padrao') return perfil.avatar;
        if (hudAvatar?.src && !hudAvatar.src.includes('placehold.co')) return hudAvatar.src;
        return '';
    }
    function sincronizarBannerPerfil(perfil) {
        const resumo = document.getElementById('eldora-menu-resumo');
        if (!resumo) return;

        let banner = perfil.banner_customizado;
        if (banner && typeof banner === 'object') banner = banner.path || banner.id || '';
        const catalogo = window.CATALOGO_SISTEMA?.banners || {};
        let url = '';
        if (typeof banner === 'string' && banner) {
            if (catalogo[banner]?.path) url = catalogo[banner].path;
            else if (/^https?:\/\//i.test(banner) || banner.startsWith('/static/')) url = banner;
        }

        let bannerCss = 'none';
        if (url) {
            try {
                const seguro = new URL(url, window.location.origin);
                if (seguro.protocol === 'https:' || seguro.origin === window.location.origin) {
                    const escapado = seguro.href.replace(/\\/g, '%5C').replace(/"/g, '%22');
                    bannerCss = `url("${escapado}")`;
                }
            } catch (_) {}
        }
        if (resumo.dataset.eldoraBannerCss === bannerCss) return;
        resumo.style.setProperty('--eldora-menu-banner', bannerCss);
        resumo.dataset.eldoraBannerCss = bannerCss;
    }
    function syncResumoHeroi() {
        carregarPerfilParaNivel();
        const perfil = window.perfilDadosGlobais || {};
        const nome = window.eldoraCharacterName || localStorage.getItem('jogadorEldoraNome') || 'Aventureiro';
        const nomeEl = document.getElementById('eldora-menu-nome-heroi');
        if (nomeEl && nomeEl.textContent !== nome) nomeEl.textContent = nome;
        syncNivelHeroi();
        sincronizarBannerPerfil(perfil);

        const hudAvatar = document.getElementById('hud-img-avatar');
        const menuAvatar = document.getElementById('eldora-menu-avatar');
        const avatarWrap = document.getElementById('eldora-menu-avatar-wrap');
        const avatarUrl = resolverImagemAvatar(perfil, hudAvatar);
        if (avatarUrl && menuAvatar) {
            let avatarFinal = '';
            try { avatarFinal = new URL(avatarUrl, window.location.origin).href; } catch (_) {}
            if (avatarFinal && menuAvatar.src !== avatarFinal) {
                menuAvatar.src = avatarFinal;
                menuAvatar.onload = () => avatarWrap?.classList.add('tem-avatar');
                menuAvatar.onerror = () => avatarWrap?.classList.remove('tem-avatar');
            }
        }

        [
            ['label-hp', 'eldora-menu-hp-barra', 'eldora-menu-hp-valor'],
            ['label-mp', 'eldora-menu-mp-barra', 'eldora-menu-mp-valor'],
            ['label-xp', 'eldora-menu-xp-barra', 'eldora-menu-xp-valor']
        ].forEach(([origemId, barraId, valorId]) => {
            const texto = document.getElementById(origemId)?.textContent || '';
            const valor = document.getElementById(valorId);
            const barra = document.getElementById(barraId);
            const match = texto.match(/(\d+(?:[.,]\d+)?)\s*%/);
            const percentual = match ? Math.max(0, Math.min(100, Number(match[1].replace(',', '.')))) : null;
            const textoValor = percentual === null ? '--' : `${Math.round(percentual)}%`;
            const largura = percentual === null ? '0%' : `${percentual}%`;
            if (valor && valor.textContent !== textoValor) valor.textContent = textoValor;
            if (barra && barra.style.width !== largura) barra.style.width = largura;
        });
    }
    function sync() {
        syncResumoHeroi();
        const blocked = [...document.querySelectorAll(blockers)].some(el => el !== menu && !menu.contains(el) && visible(el));
        document.body.classList.toggle('game-overlay-active', blocked);
        document.body.classList.toggle('fora-do-mapa', !document.getElementById('aba-reino')?.classList.contains('active'));
        if (blocked && menu.classList.contains('aberto')) window.fecharMenu();
        const open = menu.classList.contains('aberto');
        menu.inert = !open;
        toggle.setAttribute('aria-expanded', String(open));
    }
    const openOriginal = window.abrirMenu;
    const closeOriginal = window.fecharMenu;
    window.abrirMenu = function() {
        sync();
        if (document.body.classList.contains('game-overlay-active') || document.body.classList.contains('combate-aberto')) return;
        openOriginal();
        sync();
        if (menu.classList.contains('aberto')) document.getElementById('btn-fechar-menu')?.focus();
    };
    window.fecharMenu = function() {
        closeOriginal();
        menu.inert = true;
        toggle.setAttribute('aria-expanded', 'false');
    };

    window.navegarMenuHeroi = function(destino, nomeAcao) {
        window.fecharMenu();

        window.requestAnimationFrame(() => {
            if (destino && typeof window.showTab === 'function') {
                window.showTab(destino);
            }

            if (nomeAcao && typeof window[nomeAcao] === 'function') {
                window[nomeAcao]();
            }
        });
    };
    window.atualizarResumoHeroiMenu = syncResumoHeroi;
    document.addEventListener('keydown', e => {
        if (!menu.classList.contains('aberto')) return;
        if (e.key === 'Escape') { window.fecharMenu(); toggle.focus(); }
        if (e.key === 'Tab') {
            const buttons = [...menu.querySelectorAll('button:not(:disabled), a[href]')].filter(visible);
            const first = buttons[0], last = buttons[buttons.length - 1];
            if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); }
            else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
        }
    });
    [menu, toggle, document.getElementById('menu-overlay'), document.getElementById('eldora-hub-toggle'), document.getElementById('eldora-controles-hub')].filter(Boolean).forEach(el => {
        ['pointerdown','pointerup','click','touchstart','touchend'].forEach(type => el.addEventListener(type, e => e.stopPropagation(), {passive:true}));
    });
    let scheduled = false;
    new MutationObserver(() => {
        if (scheduled) return;
        scheduled = true;
        requestAnimationFrame(() => { scheduled = false; sync(); });
    }).observe(document.body, {subtree:true, childList:true, attributes:true, attributeFilter:['style','class','hidden','open']});
    const hudAvatar = document.getElementById('hud-img-avatar');
    if (hudAvatar) new MutationObserver(syncResumoHeroi).observe(hudAvatar, {attributes:true, attributeFilter:['src']});
    sync();
})();
