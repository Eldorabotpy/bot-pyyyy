(() => {
    const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    let state = null, busy = false;
    const statNames = {defense:'Defesa',initiative:'Iniciativa',max_hp:'HP máximo',max_mana:'Mana máxima'};
    const button = (label, action, family='', disabled=false, specialty='') => `<button type="button" data-action="${action}" data-family="${family}" data-specialty="${specialty}" ${disabled?'disabled':''}>${label}</button>`;
    function paint() {
        const grid = document.getElementById('grid-monstros');
        if (!grid || grid.dataset.tab !== 'companheiros' || !state) return;
        const egg = state.incubation;
        const pct = egg ? Math.min(100, Math.floor(100*egg.distance/state.hatch_distance)) : 0;
        grid.innerHTML = `<section class="companheiros-panel">
            <header><h3>Companheiros de jornada</h3><p>Conquiste um ovo, explore com a chocadeira e fortaleça seu vínculo nas caçadas.</p></header>
            <article><h4>🥚 Chocadeira permanente</h4>${state.incubator ? (egg ? `<p>Ovo de ${escape(state.families[egg.family].name)} · <strong>${pct}%</strong></p><progress max="100" value="${pct}"></progress><p>${Math.floor(egg.distance/32)} / ${state.hatch_distance/32} blocos percorridos</p>${button('Chocar ovo', 'hatch', egg.family, pct<100)}` : '<p>Livre. Escolha um ovo abaixo para iniciar a incubação.</p>') : `<p>Conquista Primeiros Passos: ${Math.min(10,state.incubator_progress)}/10 abates registrados. Receba sua primeira chocadeira gratuitamente.</p>${button('Receber chocadeira','incubator','',state.incubator_progress<10)}`}</article>
            ${Object.entries(state.families).map(([key, family])=>{
                const pet=state.pets[key], count=state.knowledge[key], claimed=state.claimed.includes(key);
                if (!pet) return `<article><h4>${family.icon} Ovo de ${escape(family.name)}</h4><p>Conquista no Bestiário: ${Math.min(50,count)}/50 abates dessa família.</p><progress max="50" value="${Math.min(50,count)}"></progress>${!claimed ? button('Resgatar ovo','claim',key,count<50) : state.eggs.includes(key) ? button('Colocar na chocadeira','incubate',key,!state.incubator||!!egg) : '<p>Ovo em incubação.</p>'}</article>`;
                const active=state.active===key, adult=pet.stage===0, cost=adult?25:100, requiredLevel=adult?10:25, requiredBond=adult?50:300;
                const essences=state.essences[key]||0;
                const ready=pet.level>=requiredLevel&&pet.bond>=requiredBond&&essences>=cost;
                const specialty=family.specialties[pet.specialty];
                const stat=specialty?specialty[1]:family.stat;
                const amount=(1+Math.floor(pet.level/5)+pet.stage*2)*(['max_hp','max_mana'].includes(stat)?3:1);
                return `<article class="pet-card ${active?'pet-equipped':''}" data-stage="${pet.stage}"><div class="pet-portrait">${family.icon}</div><h4>${escape(family.name)} · ${escape(pet.form)}</h4><p>${active?'✦ Equipado · ':''}Nível ${pet.level}${specialty?' · '+escape(specialty[0]):''}</p><p>Habilidade de apoio: +${amount} ${statNames[stat]} enquanto equipado.</p>${pet.level<25?`<progress max="${pet.next_xp}" value="${pet.level_xp}"></progress><p>${pet.level_xp}/${pet.next_xp} XP · 10 XP por vitória</p>`:'<p>Nível máximo alcançado.</p>'}<p>Vínculo: ${pet.bond} vitórias · Essências: ${essences}</p>${button(active?'Guardar':'Equipar',active?'unequip':'equip',key)}${pet.stage<2?`<div class="pet-evolution"><strong>Próxima forma: ${adult?'Adulto':'Ancestral'}</strong><p>Nível ${requiredLevel} · ${requiredBond} vitórias de vínculo · ${cost} essências da família.</p>${adult?button('Evoluir','evolve',key,!ready):Object.entries(family.specialties).map(([id,sp])=>button('Evoluir: '+escape(sp[0]),'evolve',key,!ready,id)).join('')}</div>`:'<p>✦ Evolução final concluída</p>'}</article>`;
            }).join('')}
            <p class="pet-help">Somente o pet equipado ganha XP e vínculo. Caçar criaturas das três famílias com um pet equipado rende 1 essência da família por abate. A evolução é garantida e consome as essências indicadas. Caminhar avança a incubação; ficar parado ou teleportar não conta.</p>
        </section>`;
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
        this.pet=scene.add.text(0,0,'',{fontSize:'22px'}).setOrigin(0.5,1).setVisible(false);
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
        this.cleanup=()=>{if(this.closed)return;this.closed=true;this.abort?.abort();window.removeEventListener('eldora:companheiros',this.listener);this.timer.remove();this.follow.remove();this.pet.destroy();this.badge.destroy();scene.events.off('shutdown',this.cleanup);scene.events.off('destroy',this.cleanup);};
        scene.events.once('shutdown',this.cleanup);scene.events.once('destroy',this.cleanup);
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
        this.pet.setVisible(!!pet);
        if(pet){this.pet.setText(state.families[state.active].icon);this.pet.setFontSize(20+pet.stage*4);this.pet.setAlpha(.95);}
        const egg=state.incubation;
        this.badge.setVisible(!!egg);
        if(egg){const pct=Math.min(100,Math.floor(egg.distance/state.hatch_distance*100));this.text.setText(pct===100?'🥚 Pronto para chocar':'🥚 Incubando · '+pct+'%');}
        this.position();
    }
    position(){
        if(this.closed)return;
        this.badge.setPosition(this.scene.scale.width/2,this.scene.scale.height-72);
        const player=this.scene.player;
        if(player&&this.pet.visible){const x=player.x-23,y=player.y+12;const far=Math.hypot(this.pet.x-x,this.pet.y-y)>150;this.pet.setPosition(far?x:this.pet.x+(x-this.pet.x)*.3,far?y:this.pet.y+(y-this.pet.y)*.3);this.pet.setDepth(player.depth+1);}
    }
};
