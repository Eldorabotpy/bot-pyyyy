(function(){
    const $ = (id) => document.getElementById(id);
    let currentEvent = null;
    let activeTab = 'overview';
    let rankingPage = 1;
    let countdownTimer = null;

    function esc(value){return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
    function charId(){return String(window.eldoraCharacterId||'');}
    async function getJson(url, options){
        const response = await fetch(url, {credentials:'same-origin',...options});
        const data = await response.json().catch(()=>({success:false,error:'Resposta inválida do servidor.'}));
        if(!response.ok || data.success===false) throw new Error(data.error||'Não foi possível concluir a solicitação.');
        return data;
    }
    window.abrirEventosEldora = async function(){
        const overlay=$('modal-eventos-eldora'); if(!overlay)return;
        clearInterval(countdownTimer);
        overlay.classList.add('aberto'); overlay.setAttribute('aria-hidden','false');
        document.body.style.overflow='hidden'; $('eventos-conteudo').innerHTML='<p class="eventos-carregando">Consultando os eventos do reino…</p>';
        try{
            const data=await getJson('/api/eventos');
            const list=data.events||[];
            if(!list.length){$('eventos-conteudo').innerHTML='<p class="eventos-empty">Nenhum evento está programado neste momento. Volte em breve, aventureiro.</p>';return;}
            currentEvent=list.find(e=>e.state==='active')||list[0]; activeTab='overview'; rankingPage=1; await renderEvent();
        }catch(error){$('eventos-conteudo').innerHTML=`<p class="eventos-error">${esc(error.message)}</p>`;}
    };
    window.fecharEventosEldora = function(){const el=$('modal-eventos-eldora');if(el){el.classList.remove('aberto');el.setAttribute('aria-hidden','true');document.body.style.overflow='';}clearInterval(countdownTimer);};

    async function renderEvent(){
        const id=encodeURIComponent(currentEvent.id), uid=encodeURIComponent(charId());
        const data=await getJson(`/api/eventos/${id}?user_id=${uid}`); currentEvent=data.event;
        const ev=currentEvent, personal=ev.personal||{}, pct=Math.min(100,Math.round((ev.global_points/Math.max(1,ev.global_goal))*100));
        const state={active:'ATIVO',scheduled:'PROGRAMADO',ended:'ENCERRADO',cancelled:'CANCELADO'}[ev.state]||ev.state;
        $('eventos-conteudo').innerHTML=`
          <header class="eventos-hero"><span class="eventos-kicker">Evento comunitário · ${state}</span><h2 id="eventos-titulo">${esc(ev.title)}</h2><p class="eventos-desc">${esc(ev.description||'')}</p></header>
          <div class="eventos-meta"><span>⏳ <b data-event-end="${esc(ev.ends_at)}">${dateRemaining(ev.ends_at)}</b></span><span>🛡️ ${Number(ev.participant_count||0).toLocaleString('pt-BR')} participantes</span><span>🌑 Sua contribuição: ${Number(personal.points||0).toLocaleString('pt-BR')} pts</span><span>📅 Hoje: ${Number(personal.points_today||0).toLocaleString('pt-BR')} / ${Number(ev.daily_cap||0)}</span></div>
          <div class="eventos-progress-label"><span>Integridade da Fenda Sombria</span><b>${Number(ev.global_points||0).toLocaleString('pt-BR')} / ${Number(ev.global_goal||0).toLocaleString('pt-BR')}</b></div><div class="eventos-progress" aria-label="Progresso coletivo"><i style="width:${pct}%"></i></div>
          <nav class="eventos-tabs"><button class="${activeTab==='overview'?'active':''}" data-tab="overview">Visão geral</button><button class="${activeTab==='missions'?'active':''}" data-tab="missions">Missões</button><button class="${activeTab==='rewards'?'active':''}" data-tab="rewards">Recompensas</button><button class="${activeTab==='ranking'?'active':''}" data-tab="ranking">Ranking</button></nav>
          <div class="eventos-panel" id="eventos-panel"></div>`;
        if(ev.banner && /^https:\/\//i.test(ev.banner)) $('eventos-conteudo').querySelector('.eventos-hero').style.backgroundImage=`linear-gradient(100deg,#130d20ee,#2b1639aa),url("${ev.banner.replace(/["\\\\\n\r]/g,'')}")`;
        clearInterval(countdownTimer);
        countdownTimer=setInterval(()=>{const timer=$('eventos-conteudo')?.querySelector('[data-event-end]');if(timer)timer.textContent=dateRemaining(timer.dataset.eventEnd);},60000);
        $('eventos-conteudo').querySelectorAll('[data-tab]').forEach(button=>button.addEventListener('click',()=>{activeTab=button.dataset.tab;if(activeTab==='ranking')rankingPage=1;renderEvent().catch(showError);}));
        await renderTab();
    }
    function dateRemaining(value){const ms=new Date(value).getTime()-Date.now();if(!Number.isFinite(ms)||ms<=0)return 'encerrado';const d=Math.floor(ms/86400000),h=Math.floor((ms%86400000)/3600000),m=Math.floor((ms%3600000)/60000);return d?`${d}d ${h}h restantes`:`${h}h ${m}min restantes`;}
    function rewardText(reward){const parts=[];if(reward?.gold)parts.push(`${Number(reward.gold).toLocaleString('pt-BR')} ouro`);for(const item of reward?.items||[])parts.push(`${item.quantity}× ${item.item_id.replaceAll('_',' ')}`);return parts.join(' · ')||'—';}
    async function renderTab(){
        const panel=$('eventos-panel'), ev=currentEvent, personal=ev.personal||{};
        if(activeTab==='overview'){
            panel.innerHTML=`<div class="eventos-row"><div><b>${ev.global_completed_at?'A fenda foi estabilizada!':'A fenda ainda ameaça Eldora'}</b><small>Contribua em caçadas e masmorras para avançar a meta comunitária.</small></div><span class="eventos-pill">Meta ${Number(ev.global_goal).toLocaleString('pt-BR')} pts</span></div><div class="eventos-row"><div><b>Seu limite diário</b><small>Caçada manual e Premium compartilham o mesmo limite.</small></div><span class="eventos-pill">${Number(personal.points_today||0)} / ${Number(ev.daily_cap)} pts</span></div>`;
        } else if(activeTab==='missions'){
            const names={creature:'Derrotar criatura elegível',elite:'Derrotar monstro elite',dungeon:'Concluir masmorra elegível',event_boss:'Derrotar chefe do evento'};
            panel.innerHTML=Object.entries(ev.rules||{}).map(([key,points])=>`<div class="eventos-row"><div><b>${names[key]||esc(key)}</b><small>Pontuação definida pelo servidor. Limite diário de ${Number(ev.daily_cap)} pontos.</small></div><span class="eventos-pill">+${Number(points)} pts</span></div>`).join('')||'<p class="eventos-empty">Nenhuma atividade configurada.</p>';
        } else if(activeTab==='rewards'){
            const tiers=(ev.tiers_view||[]).map(row=>`<div class="eventos-row"><div><b>Marco ${row.tier} · ${Number(row.points)} pontos</b><small>${esc(rewardText(row.reward))}</small></div><button class="eventos-claim" ${row.state!=='available'?'disabled':''} data-claim-tier="${row.tier}">${row.state==='claimed'?'Resgatada':row.state==='available'?'Resgatar':'Bloqueada'}</button></div>`).join('');
            const collectiveAvailable=!!ev.global_completed_at&&Number(personal.points||0)>=Number(ev.collective_min_points||1)&&!personal.collective_claimed;
            const collectiveState=personal.collective_claimed?'Resgatada':collectiveAvailable?'Resgatar':'Bloqueada';
            panel.innerHTML=`${tiers}<div class="eventos-row"><div><b>Recompensa coletiva</b><small>Requer meta global concluída e ${Number(ev.collective_min_points||1)} pontos pessoais · ${esc(rewardText(ev.collective_reward))}</small></div><button class="eventos-claim" ${collectiveAvailable?'':'disabled'} data-claim-collective="1">${collectiveState}</button></div>`;
            panel.querySelectorAll('[data-claim-tier]').forEach(button=>button.addEventListener('click',()=>claim({tier:Number(button.dataset.claimTier)})));
            panel.querySelector('[data-claim-collective]')?.addEventListener('click',()=>claim({collective:true}));
        } else if(activeTab==='ranking'){
            const data=await getJson(`/api/eventos/${encodeURIComponent(ev.id)}/ranking?page=${rankingPage}`);
            const pages=Math.max(1,Math.ceil(data.total/data.page_size));
            panel.innerHTML=(data.entries?.length?`<table class="eventos-ranking"><tbody>${data.entries.map(row=>`<tr><td>#${row.rank}</td><td>${esc(row.name)}</td><td>${Number(row.points).toLocaleString('pt-BR')} pts</td></tr>`).join('')}</tbody></table>`:'<p class="eventos-empty">Ainda não há contribuições classificadas.</p>')+`<div class="eventos-row"><button class="eventos-claim" data-rank-prev ${rankingPage<=1?'disabled':''}>Anterior</button><span>Página ${rankingPage} de ${pages} · ${Number(data.total)} aventureiros</span><button class="eventos-claim" data-rank-next ${rankingPage>=pages?'disabled':''}>Próxima</button></div>`;
            panel.querySelector('[data-rank-prev]')?.addEventListener('click',()=>{rankingPage--;renderEvent().catch(showError);});
            panel.querySelector('[data-rank-next]')?.addEventListener('click',()=>{rankingPage++;renderEvent().catch(showError);});
        }
    }
    async function claim(payload){
        try{await getJson(`/api/eventos/${encodeURIComponent(currentEvent.id)}/resgatar`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:charId(),...payload})});await renderEvent();}
        catch(error){if(typeof window.avisoEldora==='function')window.avisoEldora(error.message);else alert(error.message);}
    }
    function showError(error){const panel=$('eventos-panel');if(panel)panel.innerHTML=`<p class="eventos-error">${esc(error.message)}</p>`;}
    document.addEventListener('keydown',event=>{if(event.key==='Escape')window.fecharEventosEldora();});
    $('modal-eventos-eldora')?.addEventListener('click',event=>{if(event.target.id==='modal-eventos-eldora')window.fecharEventosEldora();});
})();
