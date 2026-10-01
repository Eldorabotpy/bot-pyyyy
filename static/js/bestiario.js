(() => {
    const order = ['reino_eldora','pradaria_inicial','floresta_sombria','campos_linho','pedreira_granito','pico_grifo','mina_ferro','forja_abandonada','pantano_maldito','picos_gelados','deserto_ancestral'];
    const names = {reino_eldora:'Reino de Eldora',pradaria_inicial:'Pradaria Inicial',floresta_sombria:'Floresta Sombria',campos_linho:'Campos de Linho',pedreira_granito:'Pedreira de Granito',pico_grifo:'Pico do Grifo',mina_ferro:'Mina de Ferro',forja_abandonada:'Forja Abandonada',pantano_maldito:'Pântano Maldito',picos_gelados:'Picos Gelados',deserto_ancestral:'Deserto Ancestral'};
    const esc = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const name = key => names[key] || key.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase());
    let selected='reino_eldora', opener;
    window.ordenarRegioesCodice = data => {
        const result=Object.fromEntries(order.map(key=>[key,[]]));
        for(const [key,mobs] of Object.entries(data)) {
            if(!Array.isArray(mobs))continue;
            const canonical=key==='capital_eldora'?'reino_eldora':key;
            result[canonical]=[...(result[canonical]||[]),...mobs].filter((m,i,list)=>list.findIndex(other=>other.id===m.id)===i);
        }
        return result;
    };
    window.fecharCodice = () => {document.getElementById('modal-bestiario').style.display='none';opener?.focus?.();};
    window.selecionarAbaCodice = tab => {
        document.querySelectorAll('#modal-bestiario [data-codice-tab]').forEach(button=>button.setAttribute('aria-selected',String(button.dataset.codiceTab===tab)));
        const regions=document.getElementById('codice-regioes');if(regions)regions.hidden=tab==='companheiros';
        document.getElementById('painel-detalhes-mob')?.remove();
    };
    window.abrirCodiceHunter = async () => {
        opener=document.activeElement;
        let modal=document.getElementById('modal-bestiario');
        if(!modal){modal=document.createElement('div');modal.id='modal-bestiario';document.body.appendChild(modal);modal.addEventListener('pointerdown',e=>e.stopPropagation());modal.addEventListener('keydown',e=>{e.stopPropagation();if(e.key==='Escape')window.fecharCodice();});}
        modal.style.display='flex';modal.innerHTML='<div class="codice-loading">Abrindo o Códice…</div>';
        try {
            const res=await fetch(`/api/bestiario/${encodeURIComponent(localStorage.getItem('jogadorEldoraID'))}`,{cache:'no-store'});
            if(!res.ok)throw new Error('Não foi possível carregar o Bestiário.');
            const data=window.ordenarRegioesCodice(await res.json());window.dadosCodiceCache=data;
            modal.innerHTML=`<section id="container-livro" role="dialog" aria-modal="true" aria-labelledby="codice-title">
                <header class="codice-header"><span class="codice-seal">📖</span><div><small>CONHECIMENTO DO REINO</small><h2 id="codice-title">Códice de Eldora</h2></div><button class="codice-close" aria-label="Fechar Bestiário">×</button></header>
                <nav class="codice-tabs" role="tablist" aria-label="Seções do Códice"><button role="tab" data-codice-tab="criaturas" aria-selected="true">📖 Bestiário</button><button role="tab" data-codice-tab="companheiros" aria-selected="false">🥚 Companheiros</button></nav>
                <nav id="codice-regioes" aria-label="Regiões na ordem da jornada">${Object.keys(data).map((key,i)=>`<button data-region="${esc(key)}"><span>${String(i+1).padStart(2,'0')}</span>${esc(name(key))}</button>`).join('')}</nav>
                <div id="grid-monstros"></div>
            </section>`;
            modal.querySelector('.codice-close').onclick=window.fecharCodice;
            modal.querySelector('[data-codice-tab="criaturas"]').onclick=()=>window.renderizarCategoriaCodice(selected);
            modal.querySelector('[data-codice-tab="companheiros"]').onclick=()=>window.abrirCompanheiros();
            modal.querySelectorAll('[data-region]').forEach(b=>b.onclick=()=>window.renderizarCategoriaCodice(b.dataset.region));
            window.renderizarCategoriaCodice(selected in data?selected:'reino_eldora');modal.querySelector('.codice-close').focus();
        } catch(e){modal.innerHTML=`<div class="codice-loading">${esc(e.message)}<button onclick="window.fecharCodice()">Fechar</button></div>`;}
    };
    window.renderizarCategoriaCodice = region => {
        const grid=document.getElementById('grid-monstros');if(!grid)return;
        selected=region;window.selecionarAbaCodice('criaturas');grid.dataset.tab='criaturas';grid.scrollTop=0;
        document.querySelectorAll('#codice-regioes button').forEach(b=>{b.setAttribute('aria-current',String(b.dataset.region===region));});
        const mobs=window.dadosCodiceCache[region]||[];
        const discovered=mobs.filter(m=>m.nivel_conhecimento>0).length;
        grid.innerHTML=`<header class="codice-region-title"><div><small>EXPLORE E DESCUBRA</small><h3>${esc(name(region))}</h3></div><span>${discovered}/${mobs.length} descobertos</span></header>${mobs.length?mobs.map(m=>`<button class="codice-creature" data-mob="${esc(m.id)}" data-known="${m.nivel_conhecimento}" aria-label="Ver ${esc(m.nome)}"><span class="codice-art"><img src="${esc(m.imagem)}" alt="" loading="lazy"></span><strong>${esc(m.nome)}</strong><span class="codice-kills">${m.abates} abates</span><small>${['Desconhecido','Descoberto','Estudado','✦ Maestria'][m.nivel_conhecimento]||'Descoberto'}</small></button>`).join(''):'<div class="codice-empty">Nenhuma criatura de caça registrada nesta região.<br>Escolha a próxima região para continuar sua jornada.</div>'}`;
        grid.querySelectorAll('[data-mob]').forEach(b=>b.onclick=()=>window.abrirDetalhesMob(region,b.dataset.mob));
    };
    window.abrirDetalhesMob = (region,id) => {
        const mob=window.dadosCodiceCache[region]?.find(m=>m.id===id);if(!mob)return;
        document.getElementById('painel-detalhes-mob')?.remove();
        const panel=document.createElement('section');panel.id='painel-detalhes-mob';
        panel.innerHTML=`<header class="codice-detail-header"><button aria-label="Voltar para a região">← Voltar</button><span>Dossiê da criatura</span></header><div class="codice-detail-body"><small>${esc(name(region))}</small><h2>${esc(mob.nome)}</h2><img class="codice-detail-art" src="${esc(mob.imagem)}" alt="" ${mob.nivel_conhecimento===0?'style="filter:brightness(0)"':''}><span class="codice-kills">${mob.abates} abates registrados</span><article><h3>Atributos base</h3><div class="codice-stats">${[['❤️ HP',mob.hp],['⚔️ Ataque',mob.atk],['🛡️ Defesa',mob.def],['🏃 Iniciativa',mob.agi],['🍀 Sorte',mob.sorte]].map(([label,value])=>`<div><span>${label}</span><strong>${esc(value)}</strong></div>`).join('')}</div></article><article><h3>Tesouros e drops</h3>${mob.nivel_conhecimento<3?'<p>Alcance a maestria com 50 abates para revelar os drops.</p>':mob.drops?.length?mob.drops.map(d=>`<div class="codice-drop"><span>${esc(d.item_id.replace(/_/g,' '))}</span><strong>${esc(d.drop_chance)}%</strong></div>`).join(''):'<p>Esta criatura não carrega tesouros.</p>'}</article></div>`;
        panel.querySelector('button').onclick=()=>panel.remove();document.getElementById('container-livro').appendChild(panel);
    };
})();
