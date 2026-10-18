(() => {
    const userId = localStorage.getItem('jogadorEldoraID') || window.Telegram?.WebApp?.initDataUnsafe?.user?.id;
    const grid = document.getElementById('skin-grid');
    const message = document.getElementById('skin-shop-message');
    const fragmentsDisplay = document.getElementById('skin-fragments');
    const baseAssets = 'https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/';
    let shopData;

    function showMessage(text, error = false) {
        message.textContent = text;
        message.classList.toggle('error', error);
        message.hidden = false;
    }

    async function loadShop() {
        if (!userId) {
            grid.innerHTML = '<div class="empty-state">Entre no jogo e selecione um personagem para acessar a loja.</div>';
            return;
        }
        try {
            const sessionStatus = await window.portalSessionReady;
            if (!sessionStatus?.authenticated) throw new Error('Entre na sua conta Eldora antes de acessar o ateliê.');
            const response = await fetch(`/api/loja-skins/status/${encodeURIComponent(userId)}`);
            shopData = await response.json();
            if (!response.ok || !shopData.sucesso) throw new Error(shopData.erro || 'Não foi possível carregar a loja.');
            render();
        } catch (error) {
            grid.innerHTML = '';
            showMessage(error.message, true);
        }
    }

    function render() {
        const fragments = Number(shopData.fragmentos || 0);
        fragmentsDisplay.textContent = fragments.toLocaleString('pt-BR');
        const owned = new Set(shopData.skins_desbloqueadas || []);
        if (!shopData.skins.length) {
            grid.innerHTML = '<div class="empty-state">Nenhuma skin está disponível na loja agora.</div>';
            return;
        }
        grid.innerHTML = shopData.skins.map((skin) => {
            const hasSkin = owned.has(skin.skin_id);
            const equipped = shopData.skin_equipada === skin.skin_id;
            const progress = Math.min(100, Math.floor(fragments / skin.custo * 100));
            let action = 'resgatar';
            let label = `RESGATAR · ✨ ${skin.custo}`;
            let disabled = fragments < skin.custo;
            if (hasSkin) {
                action = 'equipar';
                label = equipped ? 'EQUIPADA' : 'EQUIPAR';
                disabled = equipped;
            }
            return `<article class="skin-card">
                <div class="skin-art">
                    <span class="fallback-art">✦</span>
                    <img loading="lazy" src="${baseAssets}corpo_completo/${encodeURIComponent(skin.skin_id)}_full.png" alt="${escapeHtml(skin.nome)}" onload="this.previousElementSibling.hidden=true" onerror="this.remove()">
                </div>
                <div class="skin-info"><h2>${escapeHtml(skin.nome)}</h2><p>${escapeHtml(skin.descricao)}</p></div>
                <div class="skin-progress"><span>${hasSkin ? 'Skin desbloqueada' : 'Seu progresso'}</span><strong>${hasSkin ? '✓' : `${fragments}/${skin.custo}`}</strong></div>
                <div class="progress-track"><i style="width:${hasSkin ? 100 : progress}%"></i></div>
                <button class="skin-action" data-action="${action}" data-skin="${escapeHtml(skin.id)}" ${disabled ? 'disabled' : ''}>${label}</button>
            </article>`;
        }).join('');
        grid.querySelectorAll('.skin-action:not(:disabled)').forEach((button) => button.addEventListener('click', () => act(button)));
    }

    function escapeHtml(value) {
        return String(value || '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
    }

    async function act(button) {
        const isRedeem = button.dataset.action === 'resgatar';
        button.disabled = true;
        try {
            if (isRedeem) {
                const headers = await window.portalSessionHeaders({ 'Content-Type': 'application/json' });
                const response = await fetch('/api/loja-skins/resgatar', {
                    method: 'POST', headers,
                    body: JSON.stringify({ user_id: userId, skin_id: button.dataset.skin })
                });
                const result = await response.json();
                if (!response.ok || !result.sucesso) throw new Error(result.erro || 'Não foi possível resgatar a skin.');
                showMessage(result.message);
            } else {
                const skin = shopData.skins.find((item) => item.id === button.dataset.skin);
                const headers = await window.portalSessionHeaders({ 'Content-Type': 'application/json' });
                const response = await fetch('/api/loja-skins/equipar', {
                    method: 'POST', headers,
                    body: JSON.stringify({ user_id: userId, skin_id: skin.skin_id })
                });
                const result = await response.json();
                if (!response.ok || !result.sucesso) throw new Error(result.erro || 'Não foi possível equipar a skin.');
                localStorage.setItem('skinEquipada', skin.skin_id);
                shopData.skin_equipada = skin.skin_id;
                showMessage(`${skin.nome} equipada.`);
            }
            await loadShop();
        } catch (error) {
            showMessage(error.message, true);
            button.disabled = false;
        }
    }

    loadShop();
})();
