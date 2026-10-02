(() => {
    const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    let state = null, busy = false;
    const statNames = {defense:'Defesa',initiative:'Iniciativa',max_hp:'HP máximo',max_mana:'Mana máxima'};
    const button = (label, action, family='', disabled=false, specialty='') => `<button type="button" data-action="${action}" data-family="${family}" data-specialty="${specialty}" ${disabled?'disabled':''}>${label}</button>`;
    const art = (url, name, cls='mission-art') => `<img class="${cls}" src="${escape(url)}" alt="${escape(name)}" width="64" height="64" loading="lazy" onerror="this.style.visibility='hidden'">`;
    const roadmap = family => `<details class="pet-roadmap" data-panel="${escape(family.journey[0].species)}"><summary>Jornada de evolução</summary>${family.journey.map(step=>`<div class="pet-step">${art(step.image,step.name)}<div><strong>${escape(step.name)}</strong><small>Capítulo ${step.chapter} · ${step.released?'Disponível':'Em breve'}</small></div></div>`).join('')}</details>`;
    function paint() {
        const grid = document.getElementById('grid-monstros');
        if (!grid || grid.dataset.tab !== 'companheiros' || !state) return;
        const expanded = new Set([...grid.querySelectorAll('details[open][data-panel]')].map(el=>el.dataset.panel));
        const egg = state.incubation;
        const pct = egg ? Math.min(100, Math.floor(100*egg.distance/state.hatch_distance)) : 0;
        grid.innerHTML = `<section class="companheiros-panel">
            <header class="pet-intro"><small>CAPÍTULO ${state.chapter} · PRIMEIROS COMPANHEIROS</small><h3>Sua jornada começa com um ovo</h3><p>Conquiste → Incube → Explore → Evolua</p></header>
            <article><h4 class="incubator-heading"><img src="https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/itens/incubadora_pet.png" alt="Incubadora" width="56" height="56" onerror="this.hidden=true"><span>Incubadoras · uso único</span></h4><p>Disponíveis: <strong>${state.incubators || 0}</strong> · Cada ovo consome uma unidade ao iniciar.</p>${egg ? `<div class="pet-step">${art(state.families[egg.family].journey[0].image,state.families[egg.family].name)}<div><small>${pct===100?"PRONTO PARA NASCER":"INCUBAÇÃO EM ANDAMENTO"}</small><strong>${escape(state.families[egg.family].name)}</strong></div></div><p>Ovo de ${escape(state.families[egg.family].name)} · <strong>${pct}%</strong></p><progress max="100" value="${pct}"></progress><p>${Math.floor(egg.distance/32)} / ${state.hatch_distance/32} blocos percorridos</p><p>A incubadora deste ovo já foi utilizada. Seu progresso fica salvo.</p>${button('Chocar ovo', 'hatch', egg.family, pct<100)}` : '<p class="pet-soon">Incubadora livre · Escolha um ovo nas missões abaixo.</p><p>Uma unidade por nascimento. Confirme o ovo antes de iniciar: ele não poderá ser trocado durante a incubação.</p>'}${!state.incubator_claimed ? `<p>Conquista Primeiros Passos: ${Math.min(10,state.incubator_progress)}/10 abates · 1 incubadora gratuita.</p>${button('Resgatar incubadora','incubator','',state.incubator_progress<10)}` : '<p>✓ Incubadora da conquista já resgatada.</p>'}<p>Outras unidades estão à venda na Flora por 25 gemas.</p></article>
            <details class="premium-pet-missions" data-panel="premium"><summary>Missões do Eldora Premium</summary><p>Novas metas a cada ciclo de 30 dias. Até 3 incubadoras por ciclo. Renovar antes do vencimento preserva o progresso atual.</p>
            ${!state.premium_missions?.active ? '<p>Ative o Eldora Premium para começar a contar novos abates.</p>' : ''}
            ${(state.premium_missions?.cycles || []).map(c=>`<section><h4>${c.active?'Ciclo atual':'Recompensas pendentes'}</h4><p>${escape(new Date(c.start).toLocaleDateString('pt-BR'))} até ${escape(new Date(c.end).toLocaleDateString('pt-BR'))}</p>${c.rewards.filter(r=>c.active || r.eligible&&!r.claimed).map(r=>`<div class="pet-step">${art("https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/itens/incubadora_pet.png","Incubadora")}<strong>Recompensa: 1 incubadora</strong></div><p>${Math.min(c.kills,r.goal)} / ${r.goal} abates · 1 incubadora</p><progress max="${r.goal}" value="${Math.min(c.kills,r.goal)}"></progress>${button(r.claimed?'Resgatada':'Resgatar incubadora','premium_incubator',r.id,r.claimed||!r.eligible)}`).join('')}</section>`).join('')}
            <p>Abates contam com o Eldora Premium ativo, mesmo sem pet equipado. Recompensas concluídas continuam disponíveis após o ciclo.</p></details>
            ${Object.entries(state.families).map(([key, family])=>{
                const pet=state.pets[key], count=state.knowledge[key], claimed=state.claimed.includes(key);
                if (!pet && !family.available && !claimed && !state.eggs.includes(key)) return `<article class="pet-coming"><div class="pet-step">${art(family.journey[0].image,family.name)}<div><h4>${escape(family.name)}</h4><p>Uma nova jornada · Em breve</p></div></div></article>`;
                if (!pet) return `<article><div class="pet-step">${art(family.journey[0].image,family.name)}<div><small>MISSÃO · PRIMEIRO ENCONTRO</small><h4>Ovo de ${escape(family.name)}</h4></div></div><p>Conquista no Bestiário: ${Math.min(50,count)}/50 abates dessa família.</p><progress max="50" value="${Math.min(50,count)}"></progress>${!claimed ? button('Resgatar ovo','claim',key,count<50) : state.eggs.includes(key) ? button('Iniciar · usar 1 incubadora','incubate',key,!(state.incubators>0)||!!egg) : '<p>Ovo em incubação.</p>'}${roadmap(family)}</article>`;
                const active=state.active===key, adult=pet.stage===0, cost=adult?25:100, requiredLevel=adult?10:25, requiredBond=adult?50:300;
                const essences=state.essences[key]||0;
                const ready=pet.next_released&&pet.level>=requiredLevel&&pet.bond>=requiredBond&&essences>=cost;
                const specialty=family.specialties[pet.specialty];
                const stat=specialty?specialty[1]:family.stat;
                const amount=(1+Math.floor(pet.level/5)+pet.stage*2)*(['max_hp','max_mana'].includes(stat)?3:1);
                return `<article class="pet-card ${active?'pet-equipped':''}" data-stage="${pet.stage}">${art(pet.art.image,pet.art.name,"pet-portrait-image")}<h4>${escape(family.name)} · ${escape(pet.form)}</h4><p>${active?'✦ Equipado · ':''}Nível ${pet.level}${specialty?' · '+escape(specialty[0]):''}</p><p>Habilidade de apoio: +${amount} ${statNames[stat]} enquanto equipado.</p>${pet.level<25?`<progress max="${pet.next_xp}" value="${pet.level_xp}"></progress><p>${pet.level_xp}/${pet.next_xp} XP · 10 XP por vitória</p>`:'<p>Nível máximo alcançado.</p>'}<p>Vínculo: ${pet.bond} vitórias · Essências: ${essences}</p>${button(active?'Guardar':'Equipar',active?'unequip':'equip',key)}${pet.stage<2?`<div class="pet-evolution"><strong>Próxima forma: ${escape(family.journey[pet.stage+1]?.name || 'Nova evolução')}</strong>${!pet.next_released?'<p class="pet-soon">Em breve · Seu XP e vínculo ficam salvos. Nenhum material será consumido.</p>':''}<p>Nível ${requiredLevel} · ${requiredBond} vitórias de vínculo · ${cost} essências da família.</p>${adult?button('Evoluir','evolve',key,!ready):Object.entries(family.specialties).map(([id,sp])=>button('Evoluir: '+escape(sp[0]),'evolve',key,!ready,id)).join('')}</div>`:'<p>✦ Evolução final concluída</p>'}${roadmap(family)}</article>`;
            }).join('')}
            <p class="pet-help">Somente o pet equipado ganha XP e vínculo. Caçar criaturas das três famílias com um pet equipado rende 1 essência da família por abate. A evolução é garantida e consome as essências indicadas. Caminhar avança a incubação; ficar parado ou teleportar não conta.</p>
        </section>`;
        grid.querySelectorAll('details[data-panel]').forEach(el=>{el.open=expanded.has(el.dataset.panel);});
        grid.querySelectorAll('button[data-action]').forEach(el=>el.addEventListener('click',()=>act(el.dataset)));
    }
    async function refresh() {
        const id=localStorage.getItem('jogadorEldoraID');
        if (!id) return;
        const response=await fetch(`/api/companheiros/${encodeURIComponent(id)}`, {cache:'no-store'});
        const data=await response.json();
        if (!response.ok) throw new Error(data.erro||'Não foi possível carregar os companheiros.');
        state=data.state;
        window.dispatchEvent(new CustomEvent('eldora:companheiros',{detail:state}));
        paint();
    }
    async function act(data) {
        if(busy)return;
        busy=true;
        try {
            if (data.action === 'incubate') {
                const accepted = await window.confirmarEldora('Iniciar incubação? Será consumida 1 incubadora. O ovo não poderá ser trocado e o progresso ficará salvo.', 'Usar incubadora');
                if (!accepted) return;
            }
            const id=localStorage.getItem('jogadorEldoraID');
            const response=await fetch(`/api/companheiros/${encodeURIComponent(id)}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
            const result=await response.json();
            if(!response.ok)throw new Error(result.erro||'Não foi possível concluir.');
            state=result.state;paint();
            window.dispatchEvent(new CustomEvent('eldora:companheiros',{detail:state}));
            if(window.avisoEldora)window.avisoEldora(result.message);
        } catch(error) {if(window.avisoEldora)window.avisoEldora(error.message);}
        finally {busy=false;}
    }
    window.abrirCompanheiros=async()=>{
        const grid=document.getElementById('grid-monstros');if(!grid)return;
        window.selecionarAbaCodice?.('companheiros');
        grid.dataset.tab='companheiros';grid.scrollTop=0;grid.innerHTML='<p>Carregando companheiros…</p>';
        try {await refresh();}catch(e){grid.textContent=e.message;}
    };
    window.addEventListener('eldora:companheiros', event => {
        if (!event.detail || state && event.detail.version < state.version) return;
        state=event.detail;paint();
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
        this.badge.on('pointerdown',async(pointer,x,y,event)=>{event?.stopPropagation();await window.abrirCodiceHunter();await window.abrirCompanheiros();});
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
            if(!this.scene.textures.exists(still))this.scene.load.image(still,pet.art.image);
            if(!this.scene.textures.exists(sheet))this.scene.load.spritesheet(sheet,pet.art.sheet,{frameWidth:64,frameHeight:64});
            if(!this.scene.load.isLoading())this.scene.load.start();
        }
        this.animated=!!species&&this.scene.textures.exists(sheet)&&this.scene.textures.get(sheet).frameTotal>=13;
        if(this.animated){
            ['down','left','right','up'].forEach((direction,row)=>{
                const key=sheet+'_'+direction;
                if(!this.scene.anims.exists(key))this.scene.anims.create({key,frames:this.scene.anims.generateFrameNumbers(sheet,{start:row*3,end:row*3+2}),frameRate:8,repeat:-1});
            });
        }
        this.sheetKey=sheet;
        const texture=this.animated?sheet:this.scene.textures.exists(still)?still:'companion_'+state.active;
        const hasImage=!!pet&&this.scene.textures.exists(texture);
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
        visual.setPosition(this.placed?visual.x+(target.x-visual.x)*.4:target.x,this.placed?visual.y+(feet-visual.y)*.4:feet);
        visual.setDepth(player.depth+(target.y>player.y?1:-1));
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
