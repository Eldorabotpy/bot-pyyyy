(() => {
    const menu = document.getElementById('side-menu');
    const toggle = document.getElementById('btn-abrir-menu');
    if (!menu || !toggle) return;
    const blockers = '.modal-moderno, .eldora-modal, [role="dialog"], dialog[open], #tela-combate-global, #tela-pvp-global, #tela-raid-invasao, #forja-container, #refinaria-container, #mercado-container, #loja-reino-container, #loja-aventureiro-container, #rpg-dialogo-container, #modal-item';
    const visible = el => {
        const style = getComputedStyle(el);
        return !el.hidden && style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity) !== 0 && el.getClientRects().length > 0;
    };
    function syncResumoHeroi() {
        const nome = window.eldoraCharacterName || localStorage.getItem('jogadorEldoraNome') || 'Aventureiro';
        const nomeEl = document.getElementById('eldora-menu-nome-heroi');
        if (nomeEl && nomeEl.textContent !== nome) nomeEl.textContent = nome;

        const hudAvatar = document.getElementById('hud-img-avatar');
        const menuAvatar = document.getElementById('eldora-menu-avatar');
        const avatarWrap = document.getElementById('eldora-menu-avatar-wrap');
        if (hudAvatar?.src && menuAvatar && !hudAvatar.src.includes('placehold.co') && menuAvatar.src !== hudAvatar.src) {
            menuAvatar.src = hudAvatar.src;
            menuAvatar.onload = () => avatarWrap?.classList.add('tem-avatar');
            menuAvatar.onerror = () => avatarWrap?.classList.remove('tem-avatar');
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
