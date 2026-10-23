(() => {
    const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    let state = null, stateOwner = null, busy = false, pendingAction = '', loading = false, loadError = '';
    const statNames = {attack:'Ataque',defense:'Defesa',initiative:'Iniciativa',max_hp:'HP máximo',max_mana:'Mana máxima'};
    const button = (label, action, family='', disabled=false, specialty='') => {
        const saving=busy&&pendingAction===action;
        return `<button type="button" data-action="${escape(action)}" data-family="${escape(family)}" data-specialty="${escape(specialty)}" ${disabled||busy?'disabled':''}>${escape(saving?'Salvando…':label)}</button>`;
    };
    const art = (url, name, cls='mission-art', fallback='🐾') => '<span class="pet-art-frame">'+(url?'<img class="'+escape(cls)+'" src="'+escape(url)+'" alt="'+escape(name)+'" width="64" height="64" loading="lazy" onerror="this.hidden=true;this.nextElementSibling.hidden=false">':'')+'<span class="pet-art-fallback" '+(url?'hidden':'')+' aria-hidden="true">'+escape(fallback)+'</span></span>';
    const roadmap = family => family.journey.length<2?'':`<details class="pet-roadmap" data-panel="${escape(family.journey[0].species)}"><summary>Ver jornada de evolução</summary>${family.journey.map(step=>`<div class="pet-step">${art(step.image,step.name,'mission-art',family.icon)}<div><strong>${escape(step.name)}</strong><small>Capítulo ${step.chapter} · ${step.released?'Disponível':'Em breve'}</small></div></div>`).join('')}</details>`;
    const date = value => {
        const parsed=new Date(value);
        return Number.isNaN(parsed.getTime())?'Data indisponível':parsed.toLocaleDateString('pt-BR');
    };

    function paint() {
        const grid=document.getElementById('grid-monstros');
        if(!grid||grid.dataset.tab!=='companheiros')return;
        grid.setAttribute('aria-busy',String(loading||busy));
        if(loading){
            grid.innerHTML='<div class="pet-state" role="status"><span class="pet-spinner" aria-hidden="true"></span><span>Carregando seus companheiros…</span></div>';
            return;
        }
        if(loadError){
            grid.innerHTML=`<div class="pet-state" role="alert"><p>${escape(loadError)}</p><button type="button" class="pet-retry" data-retry-companheiros>Tentar de novo</button></div>`;
            grid.querySelector('[data-retry-companheiros]').onclick=()=>window.abrirCompanheiros();
            return;
        }
        if(!state){
            grid.innerHTML='<div class="pet-state" role="status"><p>Entre em um personagem para consultar seus companheiros.</p></div>';
            return;
        }

        const expanded=new Set([...grid.querySelectorAll('details[open][data-panel]')].map(element=>element.dataset.panel));
        const egg=state.incubation;
        const eggFamily=egg?state.families?.[egg.family]:null;
        const distance=Number(state.hatch_distance)||1;
        const pct=egg?Math.min(100,Math.floor(100*(Number(egg.distance)||0)/distance)):0;
        const eggs=state.eggs||[];
        const incubatorImage='https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/itens/incubadora_pet.png';

        grid.innerHTML=`<section class="companheiros-panel" aria-label="Companheiros">
            <header class="pet-intro">
                <div><h3>Do ovo ao companheiro</h3><p>Conquiste um ovo · Incube · Caminhe 3.000 blocos · Choque · Fortaleça</p></div>
                <span class="pet-chapter">Capítulo ${escape(state.chapter)}</span>
            </header>

            <article class="incubator-card">
                <div class="incubator-heading">
                    <img src="${incubatorImage}" alt="" width="56" height="56" loading="lazy" onerror="this.hidden=true">
                    <div><h4>Incubadoras</h4><p><strong>${Number(state.incubators)||0}</strong> disponíveis · uso único</p></div>
                </div>
                ${eggFamily?`<section class="pet-incubation" aria-label="Incubação em andamento">
                    <div class="pet-step">${art(state.families[egg.family].journey[0].image,state.families[egg.family].name,'mission-art',state.families[egg.family].icon)}<div><small>${pct===100?'PRONTO PARA NASCER':'INCUBAÇÃO EM ANDAMENTO'}</small><strong>Ovo de ${escape(state.families[egg.family].name)}</strong></div></div>
                    <div class="pet-progress-copy"><span>Progresso da caminhada</span><strong>${pct}%</strong></div>
                    <progress max="100" value="${pct}" aria-label="Incubação: ${pct}%"></progress>
                    <p>${Math.floor((Number(egg.distance)||0)/32).toLocaleString('pt-BR')} / ${Math.floor(distance/32).toLocaleString('pt-BR')} blocos percorridos</p>
                    ${button('Chocar ovo','hatch',egg.family,pct<100)}
                    <small>O progresso fica salvo. Parar ou teleportar não soma distância.</small>
                </section>`:egg?'<p class="pet-empty-note">Há um ovo antigo de uma família removida. Os dados salvos foram preservados.</p>':'<p class="pet-empty-note">Nenhum ovo está incubando. Para iniciar, escolha um ovo e use uma incubadora.</p>'}
                <div class="incubator-reward">
                    ${!state.incubator_claimed?`<div><strong>Primeiros Passos</strong><p>${Math.min(10,Number(state.incubator_progress)||0)} de 10 abates · 1 incubadora gratuita</p><progress max="10" value="${Math.min(10,Number(state.incubator_progress)||0)}" aria-label="Progresso da conquista da incubadora"></progress></div>${button('Resgatar incubadora','incubator','',(Number(state.incubator_progress)||0)<10)}`:'<p class="pet-claimed">Incubadora da conquista já resgatada.</p>'}
                </div>
                <p class="pet-shop-note">Mais unidades: Flora · 25 gemas cada.</p>
            </article>

            <section class="pet-families" aria-labelledby="pet-families-title">
                <h3 id="pet-families-title">Missões e companheiros</h3>
                ${Object.entries(state.families||{}).map(([key,family])=>{
                    const pet=state.pets?.[key];
                    const count=Math.max(0,Number(state.knowledge?.[key])||0);
                    const claimed=(state.claimed||[]).includes(key);
                    const familyEgg=eggs.includes(key);
                    if(!pet&&!family.available&&!claimed&&!familyEgg){
                        const chapter=family.journey?.[0]?.chapter;
                        return `<article class="pet-coming">${art(family.journey[0].image,family.name,'mission-art',family.icon)}<div><h4>${escape(family.name)}</h4><p>Jornada prevista para o capítulo ${escape(chapter)}.</p>${roadmap(family)}</div></article>`;
                    }
                    if(!pet){
                        const canIncubate=familyEgg&&Number(state.incubators)>0&&!egg;
                        const actionContent=!claimed
                            ?button('Resgatar ovo','claim',key,count<50)
                            :familyEgg
                                ?`${button('Iniciar incubação','incubate',key,!canIncubate)}${!state.incubators?'<p class="pet-action-note">Você precisa de uma incubadora livre.</p>':egg?'<p class="pet-action-note">Conclua a incubação atual antes de iniciar outra.</p>':''}`
                                :'<p class="pet-action-note">Ovo recebido. A incubação já está em andamento.</p>';
                        return `<article class="pet-quest">
                            <div class="pet-family-heading">${art(family.journey[0].image,family.name,'mission-art',family.icon)}<div><small>MISSÃO DE DESCOBERTA</small><h4>Ovo de ${escape(family.name)}</h4></div></div>
                            <div class="pet-progress-copy"><span>${escape(family.claim_label||'Abates desta família')}</span><strong>${Math.min(50,count)} / 50</strong></div>
                            <progress max="50" value="${Math.min(50,count)}" aria-label="${family.name}: ${Math.min(50,count)} de 50 abates"></progress>
                            ${actionContent}${roadmap(family)}
                        </article>`;
                    }
                    const active=state.active===key;
                    const firstEvolution=pet.stage===0;
                    const maxStage=Number.isInteger(family.max_stage)?family.max_stage:2;
                    const canEvolve=pet.stage<maxStage;
                    const finalEvolution=canEvolve&&pet.stage+1===maxStage;
                    const cost=firstEvolution?25:100;
                    const requiredLevel=firstEvolution?10:25;
                    const requiredBond=firstEvolution?50:300;
                    const essenceFamily=family.essence_family||key;
                    const essences=Number(state.essences?.[essenceFamily])||0;
                    const ready=pet.next_released&&pet.level>=requiredLevel&&pet.bond>=requiredBond&&essences>=cost;
                    const specialty=family.specialties?.[pet.specialty];
                    const stat=specialty?specialty[1]:family.stat;
                    const amount=(1+Math.floor(pet.level/5)+pet.stage*2)*(['max_hp','max_mana'].includes(stat)?3:1);
                    const nextForm=family.journey?.[pet.stage+1]?.name||'Próxima forma';
                    return `<article class="pet-card ${active?'pet-equipped':''}" data-stage="${pet.stage}">
                        <div class="pet-card-heading">${art(pet.art.image,pet.art.name,'pet-portrait-image',family.icon)}<div><p class="pet-status">${active?'Companheiro equipado':'Companheiro guardado'}</p><h4>${escape(family.name)} · ${escape(pet.form)}</h4><span class="pet-level">Nível ${pet.level}${specialty?' · '+escape(specialty[0]):''}</span></div></div>
                        <div class="pet-support"><span>Habilidade de apoio</span><strong>+${amount} ${escape(statNames[stat]||stat)}</strong><p>Vale enquanto este companheiro estiver equipado.</p></div>
                        <div class="pet-growth">
                            ${pet.level<25?`<div class="pet-progress-copy"><span>Experiência</span><strong>${pet.level_xp} / ${pet.next_xp} XP</strong></div><progress max="${pet.next_xp}" value="${pet.level_xp}" aria-label="Experiência: ${pet.level_xp} de ${pet.next_xp}"></progress><p>+10 XP por vitória com este pet equipado.</p>`:'<p class="pet-claimed">Nível máximo alcançado.</p>'}
                            <div class="pet-bond-row"><span>Vínculo</span><strong>${pet.bond} vitórias</strong>${canEvolve?`<span>Essências</span><strong>${essences}</strong>`:''}</div>
                        </div>
                        <div class="pet-card-actions">${button(active?'Guardar':'Equipar',active?'unequip':'equip',key)}</div>
                        ${canEvolve?`<section class="pet-evolution"><h4>Próxima forma: ${escape(nextForm)}</h4>${!pet.next_released?'<p class="pet-soon">Ainda não liberada. Seu XP e vínculo ficam salvos; nenhum material será consumido.</p>':''}
                            <div class="pet-requirements"><span>Nível<strong>${pet.level} / ${requiredLevel}</strong></span><span>Vínculo<strong>${pet.bond} / ${requiredBond}</strong></span><span>Essências<strong>${essences} / ${cost}</strong></span></div>
                            <p class="pet-map-change">Ao evoluir, a aparência do companheiro também muda no mapa.</p>
                            ${finalEvolution&&Object.keys(family.specialties||{}).length?Object.entries(family.specialties).map(([id,option])=>button('Evoluir: '+option[0],'evolve',key,!ready,id)).join(''):button('Evoluir','evolve',key,!ready)}
                        </section>`:maxStage===0?'<p class="pet-final">Forma única · o bônus cresce com o nível</p>':'<p class="pet-final">Evolução final concluída</p>'}
                        ${roadmap(family)}
                    </article>`;
                }).join('')}
            </section>

            <details class="premium-pet-missions" data-panel="premium"><summary>Missões do Eldora Premium</summary>
                <p>Metas de abates a cada ciclo de 30 dias. Até 3 incubadoras por ciclo.</p>
                ${!state.premium_missions?.active?'<p>Ative o Eldora Premium para começar a contar novos abates.</p>':''}
                ${(state.premium_missions?.cycles||[]).map(cycle=>`<section class="premium-cycle"><h4>${cycle.active?'Ciclo atual':'Recompensas pendentes'}</h4><p>${escape(date(cycle.start))} até ${escape(date(cycle.end))}</p>
                    ${cycle.rewards.filter(reward=>cycle.active||reward.eligible&&!reward.claimed).map(reward=>`<div class="premium-reward">
                        ${art(incubatorImage,'Incubadora','mission-art','🥚')}<strong>1 incubadora</strong>
                        <span>${Math.min(cycle.kills,reward.goal).toLocaleString('pt-BR')} / ${reward.goal.toLocaleString('pt-BR')} abates</span>
                        <progress max="${reward.goal}" value="${Math.min(cycle.kills,reward.goal)}" aria-label="Missão: ${Math.min(cycle.kills,reward.goal)} de ${reward.goal} abates"></progress>
                        ${button(reward.claimed?'Resgatada':'Resgatar incubadora','premium_incubator',reward.id,reward.claimed||!reward.eligible)}
                    </div>`).join('')}
                </section>`).join('')}
                <p>Os abates contam com o Premium ativo, mesmo sem pet equipado. Recompensas concluídas continuam disponíveis após o ciclo.</p>
            </details>

            <p class="pet-help">Só o pet equipado ganha XP e vínculo: +10 XP e 1 vínculo por vitória. Caçar Slimes, Lobos ou Morcegos com um pet equipado também rende 1 essência da família derrotada. Caminhar avança a incubação; ficar parado ou teleportar não conta.</p>
        </section>`;
        grid.querySelectorAll('details[data-panel]').forEach(element=>{element.open=expanded.has(element.dataset.panel);});
        grid.querySelectorAll('button[data-action]').forEach(element=>element.addEventListener('click',()=>act(element.dataset)));
    }

    async function refresh() {
        const id=localStorage.getItem('jogadorEldoraID');
        if(!id)throw new Error('Entre em um personagem para consultar seus companheiros.');
        const response=await fetch(`/api/companheiros/${encodeURIComponent(id)}`,{cache:'no-store'});
        const data=await response.json().catch(()=>({}));
        if(!response.ok)throw new Error(data.erro||'Não foi possível carregar os companheiros.');
        if(!data.state)throw new Error('O servidor não retornou os dados dos companheiros.');
        state=data.state;
        stateOwner=id;
        loadError='';
        window.dispatchEvent(new CustomEvent('eldora:companheiros',{detail:state}));
        paint();
        return state;
    }

    async function act(data) {
        if(busy)return;
        busy=true;
        pendingAction=data.action;
        paint();
        try {
            if(data.action==='incubate'){
                const accepted=await window.confirmarEldora('Iniciar incubação? Será consumida 1 incubadora. O ovo não poderá ser trocado e o progresso ficará salvo.','Usar incubadora');
                if(!accepted)return;
            }
            const id=localStorage.getItem('jogadorEldoraID');
            if(!id)throw new Error('Entre em um personagem para continuar.');
            const response=await fetch(`/api/companheiros/${encodeURIComponent(id)}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
            const result=await response.json().catch(()=>({}));
            if(!response.ok)throw new Error(result.erro||'Não foi possível concluir esta ação.');
            state=result.state;
            stateOwner=id;
            paint();
            window.dispatchEvent(new CustomEvent('eldora:companheiros',{detail:state}));
            if(window.avisoEldora)window.avisoEldora(result.message);
        } catch(error) {
            const message=error instanceof TypeError?'Sem conexão com o servidor. Confira a conexão e tente novamente.':error.message;
            if(window.avisoEldora)window.avisoEldora(message);
        } finally {
            busy=false;
            pendingAction='';
            paint();
        }
    }

    window.abrirCompanheiros=async()=>{
        window.prepararCodiceHunter?.();
        const grid=document.getElementById('grid-monstros');
        if(!grid)return;
        window.selecionarAbaCodice?.('companheiros');
        grid.dataset.tab='companheiros';
        grid.scrollTop=0;
        const id=localStorage.getItem('jogadorEldoraID');
        if(stateOwner!==id)state=null;
        loading=true;
        loadError='';
        paint();
        try{await refresh();}
        catch(error){loadError=error instanceof TypeError?'Sem conexão com o servidor. Confira a conexão e tente novamente.':error.message;}
        finally{loading=false;paint();}
    };

    window.addEventListener('eldora:companheiros',event=>{
        if(!event.detail)return;
        const owner=localStorage.getItem('jogadorEldoraID');
        if(stateOwner!==owner){state=null;stateOwner=owner;}
        if(state&&event.detail.version<state.version)return;
        state=event.detail;
        loadError='';
        paint();
    });
    window.carregarCompanheiros=refresh;
})();


// Companheiro local e incubação acompanham a vida útil da cena Phaser.
window.CompanionMapHUD = class {
    constructor(scene) {
        this.scene=scene;this.closed=false;this.state=null;this.fetching=false;
        this.pet=scene.add.sprite(0,0,'__DEFAULT').setOrigin(0.5,1).setVisible(false);
        this.fallback=scene.add.text(0,0,'',{fontSize:'24px'}).setOrigin(0.5,1).setVisible(false);
        this.trail=[];this.lastPlayer=null;this.placed=false;this.requestedArt=new Set();
        this.badge=scene.add.container(scene.scale.width/2,scene.scale.height-72).setScrollFactor(0).setDepth(950).setVisible(false);
        const bg=scene.add.graphics();bg.fillStyle(0x101827,.96);bg.fillRoundedRect(-72,-15,144,30,15);bg.lineStyle(1,0xc6a35c,.8);bg.strokeRoundedRect(-72,-15,144,30,15);
        this.text=scene.add.text(0,0,'',{fontFamily:'Arial',fontSize:'12px',color:'#ecd08c',fontStyle:'bold'}).setOrigin(.5).setResolution(2);
        this.badge.add([bg,this.text]);
        this.badge.setSize(144,30).setInteractive();
        this.badge.on('pointerdown',async(pointer,x,y,event)=>{event?.stopPropagation();await window.abrirCompanheiros();});
        this.listener=event=>this.apply(event.detail);
        window.addEventListener('eldora:companheiros',this.listener);
        this.timer=scene.time.addEvent({delay:5000,loop:true,callback:()=>this.refresh()});
        this.follow=scene.time.addEvent({delay:50,loop:true,callback:()=>this.position()});
        this.cleanup=()=>{if(this.closed)return;this.closed=true;this.abort?.abort();window.removeEventListener('eldora:companheiros',this.listener);this.timer.remove();this.follow.remove();this.scene.load.off('complete',this.artReady);this.pet.destroy();this.fallback.destroy();this.badge.destroy();scene.events.off('shutdown',this.cleanup);scene.events.off('destroy',this.cleanup);};
        scene.events.once('shutdown',this.cleanup);scene.events.once('destroy',this.cleanup);
        this.artReady=()=>{if(!this.closed&&this.state)this.apply(this.state);};
        this.scene.load.on('complete',this.artReady);
        this.refresh();
    }
    async refresh(){
        if(this.closed||this.fetching)return;
        const id=localStorage.getItem('jogadorEldoraID');if(!id)return;
        this.fetching=true;this.abort=new AbortController();
        try{const res=await fetch(`/api/companheiros/${encodeURIComponent(id)}`,{cache:'no-store',signal:this.abort.signal});if(res.ok){const data=await res.json();this.apply(data.state);if(!this.closed)window.dispatchEvent(new CustomEvent('eldora:companheiros',{detail:data.state}));}}
        catch(error){if(error.name!=='AbortError')console.warn('Companheiros: sincronização pendente.');}
        finally{this.fetching=false;}
    }
    apply(state){
        if(this.closed||!state||this.state&&state.version<this.state.version)return;
        this.state=state;
        const pet=state.pets[state.active];
        const species=pet?.art?.species;
        const sheet='pet_sheet_'+species, still='pet_still_'+species;
        if(species&&!this.requestedArt.has(species)){
            this.requestedArt.add(species);
            if(pet.art.image&&!this.scene.textures.exists(still))this.scene.load.image(still,pet.art.image);
            if(pet.art.sheet&&!this.scene.textures.exists(sheet))this.scene.load.spritesheet(sheet,pet.art.sheet,{frameWidth:64,frameHeight:64});
            if((pet.art.image||pet.art.sheet)&&!this.scene.load.isLoading())this.scene.load.start();
        }
        this.animated=!!species&&!!pet?.art?.sheet&&this.scene.textures.exists(sheet)&&this.scene.textures.get(sheet).frameTotal>=13;
        if(this.animated){
            ['down','left','right','up'].forEach((direction,row)=>{
                const key=sheet+'_'+direction;
                if(!this.scene.anims.exists(key))this.scene.anims.create({key,frames:this.scene.anims.generateFrameNumbers(sheet,{start:row*3,end:row*3+2}),frameRate:4,repeat:-1});
            });
        }
        this.sheetKey=sheet;
        const texture=this.animated?sheet:this.scene.textures.exists(still)?still:null;
        const hasImage=!!pet&&!!texture&&this.scene.textures.exists(texture);
        this.pet.setVisible(hasImage);
        this.fallback.setVisible(!!pet&&!hasImage);
        if(hasImage&&this.pet.texture.key!==texture){this.pet.stop();this.pet.setTexture(texture);}
        if(pet)this.fallback.setText(state.families[state.active].icon);
        else {this.trail=[];this.lastPlayer=null;this.placed=false;}
        const egg=state.incubation;
        this.badge.setVisible(!!egg);
        if(egg){const pct=Math.min(100,Math.floor(egg.distance/state.hatch_distance*100));this.text.setText(pct===100?'🥚 Pronto para chocar':'🥚 Incubando · '+pct+'%');}
        this.position();
    }
    position(){
        if(this.closed)return;
        this.badge.setPosition(this.scene.scale.width/2,this.scene.scale.height-72);
        const player=this.scene.player;
        if(!player||!this.state?.pets[this.state.active])return;
        const point={x:player.x,y:player.y};
        const jumped=this.lastPlayer&&Math.hypot(point.x-this.lastPlayer.x,point.y-this.lastPlayer.y)>150;
        if(!this.lastPlayer||jumped){
            this.trail=[{x:point.x-32,y:point.y},point];this.placed=false;
        } else if(Math.hypot(point.x-this.lastPlayer.x,point.y-this.lastPlayer.y)>0.5){
            this.trail.push(point);
            if(this.trail.length>128)this.trail.shift();
        }
        this.lastPlayer=point;
        let remaining=32,target=this.trail[0];
        for(let i=this.trail.length-1;i>0;i--){
            const a=this.trail[i],b=this.trail[i-1],length=Math.hypot(b.x-a.x,b.y-a.y);
            if(length>=remaining){const t=remaining/length;target={x:a.x+(b.x-a.x)*t,y:a.y+(b.y-a.y)*t};break;}
            remaining-=length;
        }
        const visual=this.pet.visible?this.pet:this.fallback;
        const size=Math.min(player.displayWidth,player.displayHeight)/2;
        const scale=size/Math.max(visual.width,visual.height,1);
        visual.setScale(scale);
        const feet=target.y+player.displayHeight*(1-(player.originY??0.5));
        const oldX=visual.x,oldY=visual.y;
        visual.setPosition(this.placed?visual.x+(target.x-visual.x)*.25:target.x,this.placed?visual.y+(feet-visual.y)*.25:feet);
        visual.setDepth(this.scene.calcularProfundidadeAtor
            ? this.scene.calcularProfundidadeAtor(visual)
            : player.depth+(target.y>player.y?1:-1));
        if(this.animated&&visual===this.pet){
            const dx=visual.x-oldX,dy=visual.y-oldY;
            if(Math.hypot(dx,dy)>.3){
                this.direction=Math.abs(dx)>Math.abs(dy)?(dx<0?'left':'right'):(dy<0?'up':'down');
                this.pet.play(this.sheetKey+'_'+this.direction,true);
            } else {this.pet.stop();this.pet.setFrame(['down','left','right','up'].indexOf(this.direction||'down')*3+1);}
        }
        this.placed=true;
    }
};
