(() => {
    const order = ['reino_eldora','pradaria_inicial','floresta_sombria','campos_linho','pedreira_granito','pico_grifo','mina_ferro','forja_abandonada','pantano_maldito','picos_gelados','deserto_ancestral'];
    const names = {reino_eldora:'Reino de Eldora',pradaria_inicial:'Pradaria Inicial',floresta_sombria:'Floresta Sombria',campos_linho:'Campos de Linho',pedreira_granito:'Pedreira de Granito',pico_grifo:'Pico do Grifo',mina_ferro:'Mina de Ferro',forja_abandonada:'Forja Abandonada',pantano_maldito:'Pântano Maldito',picos_gelados:'Picos Gelados',deserto_ancestral:'Deserto Ancestral'};
    const esc = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const name = key => names[key] || key.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase());
    let selected='reino_eldora', opener=null, activeTab='criaturas', loading=null;

    window.ordenarRegioesCodice = data => {
        const result=Object.fromEntries(order.map(key=>[key,[]]));
        for(const [key,mobs] of Object.entries(data||{})) {
            if(!Array.isArray(mobs))continue;
            const canonical=key==='capital_eldora'?'reino_eldora':key;
            result[canonical]=[...(result[canonical]||[]),...mobs].filter((m,i,list)=>list.findIndex(other=>other.id===m.id)===i);
        }
        return result;
    };

    function bindModal(modal) {
        if(modal.dataset.codiceBound)return;
        modal.dataset.codiceBound='true';
        modal.addEventListener('pointerdown',event=>event.stopPropagation());
        modal.addEventListener('keydown',event=>{
            event.stopPropagation();
            if(event.key==='Escape'){event.preventDefault();window.fecharCodice();return;}
            if(event.key!=='Tab')return;
            const focusable=[...modal.querySelectorAll('button:not([disabled]),summary,[href],[tabindex]:not([tabindex="-1"])')].filter(el=>!el.hidden&&el.getClientRects().length);
            if(!focusable.length)return;
            const first=focusable[0],last=focusable[focusable.length-1];
            if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
            else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
        });
        modal.addEventListener('click',event=>{
            if(event.target.closest('[data-retry-codice]'))loadBestiary();
        });
    }

    function prepare() {
        let modal=document.getElementById('modal-bestiario');
        const created=!modal;
        if(created){
            modal=document.createElement('div');
            modal.id='modal-bestiario';
            modal.style.display='none';
            document.body.appendChild(modal);
        }
        const opening=created||modal.style.display==='none';
        if(opening)opener=document.activeElement;
        if(!modal.querySelector('#container-livro')){
            modal.innerHTML=`<section id="container-livro" role="dialog" aria-modal="true" aria-labelledby="codice-title">
                <header class="codice-header"><span class="codice-seal" aria-hidden="true">📖</span><h2 id="codice-title">Códice de Eldora</h2><button class="codice-close" type="button" aria-label="Fechar Códice">×</button></header>
                <nav class="codice-tabs" role="tablist" aria-label="Seções do Códice"><button id="tab-criaturas" type="button" role="tab" aria-controls="grid-monstros" data-codice-tab="criaturas" aria-selected="true">📖 Bestiário</button><button id="tab-companheiros" type="button" role="tab" aria-controls="grid-monstros" data-codice-tab="companheiros" aria-selected="false">🥚 Companheiros</button></nav>
                <nav id="codice-regioes" aria-label="Regiões na ordem da jornada"></nav>
                <div id="grid-monstros" role="tabpanel" aria-labelledby="tab-criaturas" aria-live="polite"></div>
            </section>`;
            bindModal(modal);
            modal.querySelector('.codice-close').onclick=window.fecharCodice;
            modal.querySelector('[data-codice-tab="criaturas"]').onclick=()=>window.renderizarCategoriaCodice(selected);
            modal.querySelector('[data-codice-tab="companheiros"]').onclick=()=>window.abrirCompanheiros();
        }
        modal.style.display='flex';
        if(opening)modal.querySelector('.codice-close')?.focus();
        return modal;
    }

    window.prepararCodiceHunter=prepare;
    window.fecharCodice=()=>{
        const modal=document.getElementById('modal-bestiario');
        if(modal)modal.style.display='none';
        opener?.focus?.();
        opener=null;
    };
    window.selecionarAbaCodice=tab=>{
        activeTab=tab;
        document.querySelectorAll('#modal-bestiario [data-codice-tab]').forEach(button=>button.setAttribute('aria-selected',String(button.dataset.codiceTab===tab)));
        const regions=document.getElementById('codice-regioes');
        if(regions)regions.hidden=tab==='companheiros';
        const grid=document.getElementById('grid-monstros');
        if(grid){
            grid.dataset.tab=tab;
            grid.setAttribute('aria-labelledby',tab==='companheiros'?'tab-companheiros':'tab-criaturas');
        }
        document.getElementById('painel-detalhes-mob')?.remove();
    };

    function renderRegions(data) {
        const regions=document.getElementById('codice-regioes');
        if(!regions)return;
        regions.innerHTML=Object.keys(data).map((key,i)=>`<button type="button" data-region="${esc(key)}"><span>${String(i+1).padStart(2,'0')}</span>${esc(name(key))}</button>`).join('');
        regions.querySelectorAll('[data-region]').forEach(button=>button.onclick=()=>window.renderizarCategoriaCodice(button.dataset.region));
    }

    function loadingMarkup() {
        return '<div class="codice-state" role="status"><span class="codice-spinner" aria-hidden="true"></span><span>Abrindo o Códice…</span></div>';
    }

    function loadBestiary() {
        if(loading)return loading;
        const grid=document.getElementById('grid-monstros');
        if(!grid)return Promise.resolve();
        if(activeTab==='criaturas'&&!window.dadosCodiceCache)grid.innerHTML=loadingMarkup();
        loading=(async()=>{
            try {
                const playerId=localStorage.getItem('jogadorEldoraID');
                if(!playerId)throw new Error('Entre em um personagem para consultar o Bestiário.');
                const response=await fetch(`/api/bestiario/${encodeURIComponent(playerId)}`,{cache:'no-store'});
                const payload=await response.json().catch(()=>({}));
                if(!response.ok)throw new Error(payload.erro||'Não foi possível carregar o Bestiário.');
                const data=window.ordenarRegioesCodice(payload);
                window.dadosCodiceCache=data;
                renderRegions(data);
                if(activeTab==='criaturas')window.renderizarCategoriaCodice(selected in data?selected:'reino_eldora');
            } catch(error) {
                if(activeTab==='criaturas'){
                    const message=error instanceof TypeError?'Sem conexão com o servidor. Confira a conexão e tente novamente.':error.message;
                    grid.innerHTML=`<div class="codice-state" role="alert"><p>${esc(message)}</p><button type="button" data-retry-codice>Tentar de novo</button></div>`;
                }
            }
        })().finally(()=>{loading=null;});
        return loading;
    }

    window.abrirCodiceHunter=async()=>{
        const modal=prepare();
        window.selecionarAbaCodice('criaturas');
        const grid=modal.querySelector('#grid-monstros');
        grid.scrollTop=0;
        if(!window.dadosCodiceCache)grid.innerHTML=loadingMarkup();
        await loadBestiary();
        return modal;
    };

    window.renderizarCategoriaCodice=region=>{
        const grid=document.getElementById('grid-monstros');
        if(!grid)return;
        selected=region||selected;
        window.selecionarAbaCodice('criaturas');
        grid.scrollTop=0;
        const data=window.dadosCodiceCache;
        if(!data){grid.innerHTML=loadingMarkup();loadBestiary();return;}
        if(!(selected in data))selected='reino_eldora';
        document.querySelectorAll('#codice-regioes button').forEach(button=>{
            const current=button.dataset.region===selected;
            button.setAttribute('aria-current',String(current));
            if(current)button.scrollIntoView({block:'nearest',inline:'nearest',behavior:'smooth'});
        });
        const mobs=data[selected]||[];
        const discovered=mobs.filter(m=>m.nivel_conhecimento>0).length;
        grid.innerHTML=`<header class="codice-region-title"><h3>${esc(name(selected))}</h3><span>${discovered}/${mobs.length} descobertos</span></header>${mobs.length?mobs.map(m=>`<button type="button" class="codice-creature" data-mob="${esc(m.id)}" data-known="${m.nivel_conhecimento}" aria-label="Ver ${esc(m.nome)}"><span class="codice-art"><img src="${esc(m.imagem)}" alt="" loading="lazy"></span><strong>${esc(m.nome)}</strong><span class="codice-kills">${m.abates} abates</span><progress class="codice-mastery" max="50" value="${Math.min(50,m.abates)}" aria-label="Progresso de conhecimento"></progress><small>${['Desconhecido','Descoberto','Estudado','✦ Maestria'][m.nivel_conhecimento]||'Descoberto'}</small></button>`).join(''):'<div class="codice-empty">Nenhuma criatura de caça registrada nesta região.<br>Escolha a próxima região para continuar sua jornada.</div>'}`;
        grid.querySelectorAll('[data-mob]').forEach(button=>button.onclick=()=>window.abrirDetalhesMob(selected,button.dataset.mob));
    };

    window.abrirDetalhesMob=(region,id)=>{
        const mob=window.dadosCodiceCache?.[region]?.find(item=>item.id===id);
        if(!mob)return;
        document.getElementById('painel-detalhes-mob')?.remove();
        const panel=document.createElement('section');
        panel.id='painel-detalhes-mob';
        panel.innerHTML=`<header class="codice-detail-header"><button type="button" aria-label="Voltar para a região">← Voltar</button><span>Dossiê da criatura</span></header><div class="codice-detail-body"><small>${esc(name(region))}</small><h2>${esc(mob.nome)}</h2><img class="codice-detail-art" src="${esc(mob.imagem)}" alt="" ${mob.nivel_conhecimento===0?'style="filter:brightness(0)"':''}><span class="codice-kills">${mob.abates} abates registrados</span><article><h3>Atributos base</h3><div class="codice-stats">${[['❤️ HP',mob.hp],['⚔️ Ataque',mob.atk],['🛡️ Defesa',mob.def],['🏃 Iniciativa',mob.agi],['🍀 Sorte',mob.sorte]].map(([label,value])=>`<div><span>${label}</span><strong>${esc(value)}</strong></div>`).join('')}</div></article><article><h3>Tesouros e drops</h3>${mob.nivel_conhecimento<3?'<p>Alcance a maestria com 50 abates para revelar os drops.</p>':mob.drops?.length?mob.drops.map(drop=>`<div class="codice-drop"><span>${esc(drop.item_id.replace(/_/g,' '))}</span><strong>${esc(drop.drop_chance)}%</strong></div>`).join(''):'<p>Esta criatura não carrega tesouros.</p>'}</article></div>`;
        panel.querySelector('button').onclick=()=>{panel.remove();[...document.querySelectorAll('[data-mob]')].find(button=>button.dataset.mob===id)?.focus();};
        document.getElementById('container-livro').appendChild(panel);
        panel.querySelector('button').focus();
    };
})();
