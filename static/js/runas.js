(() => {
 'use strict';
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 let dialog, state, selectedItem, selectedSlot=0, family='crueldade', busy=false, page='equipar';
 let inFlight=Promise.resolve();
 async function boundedFetch(url,options={}) {
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),10000);
  try{return await fetch(url,{...options,signal:controller.signal});}finally{clearTimeout(timer);}
 }
 window.fecharOficinaRunasParaCombate=async()=>{
  if(!dialog?.open)return;
  document.getElementById('modal-alerta-eldora')?.dispatchEvent(new Event('cancel',{cancelable:true}));
  await inFlight;
  if(dialog?.open){dialog.close();dialog.remove();window.__oficinaRunasAberta=false;}
 };
 const icon=r=>r?.icon?`<img src="${esc(r.icon)}" alt="" width="32" height="32">`:'<span class="rune-empty">◇</span>';
 window.renderRuneSockets = item => {
  const slots=item?.rune_slots;
  if(!slots?.length)return '';
  return `<span class="rune-mini-slots" aria-label="Runas ${slots.filter(Boolean).length} de ${slots.length}">${slots.map(r=>`<span title="${esc(r?.name||'Espaço vazio')}">${icon(r)}</span>`).join('')}</span>`;
 };
 window.renderRuneDetails = item => {
  if(!item?.rune_slots?.length)return '';
  return `<div class="rune-item-details"><b>Runas · ${item.rune_slots.filter(Boolean).length}/${item.rune_slots.length}</b>${item.rune_slots.map((r,i)=>`<div>${icon(r)}<span>${esc(r?.name||`Espaço ${i+1} vazio`)}<small>${esc(r?.desc||'Disponível para encaixar uma runa')}</small></span></div>`).join('')}</div>`;
 };
 const runeById=id=>state.runas.find(r=>r.id===id);
 const selectedGear=()=>state.equipamentos.find(i=>i.id===selectedItem);
 const costText=cost=>Object.entries(cost).map(([key,n])=>`${n} ${key==='gold'?'ouro':key==='po_runico'?'pó rúnico':'fragmento ancestral'}`).join(' + ');
 const canPay=cost=>Object.entries(cost).every(([k,n])=>(k==='gold'?state.gold:state.materiais[k]||0)>=n);
 function header(){return `<header><div><small>FORJA · INSCRIÇÕES RÚNICAS</small><h2>Oficina de Runas</h2></div><button data-action="fechar" aria-label="Fechar runas">×</button></header><div class="rune-wallet"><span>${state.gold.toLocaleString('pt-BR')} ouro</span><span>${state.materiais.po_runico} pó rúnico</span><span>${state.materiais.fragmento_runa_ancestral} fragmentos</span></div><nav><button data-page="equipar" class="${page==='equipar'?'active':''}">Equipamentos</button><button data-page="evoluir" class="${page==='evoluir'?'active':''}">Evolução</button></nav>`;}
 function gearPage(){
  if(!state.equipamentos.length)return '<p class="rune-notice">Você ainda não possui equipamentos. Os raros têm 1 espaço, épicos 2 e lendários 3.</p>';
  const item=selectedGear()||state.equipamentos[0];selectedItem=item.id;
  if(selectedSlot>=item.sockets.length)selectedSlot=0;
  const installed=item.rune_slots[selectedSlot];
  const slotRows=item.rune_slots.map((r,i)=>`<button class="rune-slot ${selectedSlot===i?'selected':''}" data-slot="${i}">${icon(r)}<span>${esc(r?.name||`Espaço ${i+1}`)}<small>${esc(r?.desc||'Vazio · selecione para encaixar')}</small></span></button>`).join('');
  const owned=state.runas.filter(r=>r.qtd>0);
  const candidates=owned.map(r=>{
   const duplicate=item.rune_slots.some(s=>s?.family===r.family);
   return `<div class="rune-card">${icon(r)}<div><b>${esc(r.name)}</b><small>${esc(r.desc)} · ${r.qtd} na mochila</small></div><button data-action="encaixar" data-rune="${esc(r.id)}" ${duplicate||installed||!item.sockets.length?'disabled':''}>${duplicate?'Já instalada':'Encaixar'}</button></div>`;
  }).join('');
  return `<label class="rune-label">Equipamento<select id="rune-gear">${state.equipamentos.map(g=>`<option value="${esc(g.id)}" ${g.id===item.id?'selected':''}>${esc(g.nome)} · ${esc(g.raridade)}${g.equipado?' · equipado':''}</option>`).join('')}</select></label>
  <p class="rune-notice">${item.equipado?'Bônus ativos enquanto este equipamento estiver equipado e íntegro.':'Equipe este item no personagem para ativar seus bônus.'} Uma runa de cada família por equipamento.</p>
  <div class="rune-slots">${slotRows||'<p>Esta raridade não possui espaços. Raro: 1 · Épico: 2 · Lendário: 3.</p>'}</div>
  ${installed?`<button class="rune-extract" data-action="extrair" ${state.gold<state.extracao_ouro?'disabled':''}>Extrair ${esc(installed.name)} · ${state.extracao_ouro} ouro</button><p class="rune-notice">A runa volta para a mochila. O equipamento é preservado.</p>`:''}
  <h3>Suas runas disponíveis</h3>${candidates||'<p class="rune-notice">Nenhuma runa solta na mochila. Runas instaladas devem ser extraídas antes de evoluir.</p>'}`;
 }
 function evolutionPage(){
  const families=[...new Map(state.runas.map(r=>[r.family,r.family_name])).entries()];
  const runes=state.runas.filter(r=>r.family===family).sort((a,b)=>a.tier-b.tier);
  return `<button data-action="forjar" ${state.materiais.fragmento_runa_ancestral<7?'disabled':''}>Forjar runa menor aleatória · 7 fragmentos</button><label class="rune-label">Família<select id="rune-family">${families.map(([id,name])=>`<option value="${id}" ${id===family?'selected':''}>${esc(name)}</option>`).join('')}</select></label>
  <p class="rune-notice">3 runas iguais + materiais → 1 runa do próximo nível. Sucesso garantido. Apenas runas da mochila são consumidas.</p><div class="rune-tree">${runes.map(r=>{
   const cost=state.custos_evolucao[r.tier];
   return `<article class="rune-tier">${icon(r)}<div><small>NÍVEL ${r.tier} · ${r.qtd} na mochila</small><h3>${esc(r.name)}</h3><p>${esc(r.desc)}</p></div>${r.next_id?`<p class="rune-cost">3 × ${esc(r.name)} + ${costText(cost)}</p><button data-action="evoluir" data-rune="${r.id}" ${r.qtd<3||!canPay(cost)?'disabled':''}>Evoluir para ${esc(runeById(r.next_id).name)}</button>`:'<p class="rune-notice">Evolução máxima desta família.</p>'}${r.qtd?`<button class="rune-secondary" data-action="dissolver" data-rune="${r.id}">Dissolver 1 → ${state.po_por_nivel[r.tier]} pó rúnico</button>`:''}</article>`;
  }).join('<div class="rune-branch" aria-hidden="true">↓</div>')}</div>`;
 }
 function render(){
  dialog.innerHTML=header()+`<section class="rune-content">${page==='equipar'?gearPage():evolutionPage()}</section><footer id="rune-status" role="status">Selecione um espaço ou explore a evolução das famílias.</footer>`;
  dialog.querySelector('#rune-gear')?.addEventListener('change',e=>{selectedItem=e.target.value;selectedSlot=0;render();});
  dialog.querySelector('#rune-family')?.addEventListener('change',e=>{family=e.target.value;render();});
 }
 async function operate(action,rid){
  if(busy)return;busy=true;
  const item=selectedGear(),rune=runeById(rid);
  const message={forjar:'Consumir 7 fragmentos para criar uma runa menor de uma família aleatória?',encaixar:`Encaixar ${rune?.name} em ${item?.nome}, espaço ${selectedSlot+1}? Uma runa será retirada da mochila.`,extrair:`Extrair a runa do espaço ${selectedSlot+1}? Custo: ${state.extracao_ouro} ouro. A runa voltará à mochila.`,evoluir:`Consumir 3 ${rune?.name} + ${rune?.next_id?costText(state.custos_evolucao[rune.tier]):''} para criar 1 ${rune?.next_id?runeById(rune.next_id).name:''}?`,dissolver:`Dissolver 1 ${rune?.name} para receber ${state.po_por_nivel[rune?.tier]} pó rúnico? A runa será consumida.`}[action];
  try{
   if(!await window.confirmarEldora(message,'Oficina de Runas'))return;
   dialog.querySelectorAll('button,select').forEach(e=>e.disabled=true);
   const response=await boundedFetch('/api/runas/operar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:localStorage.getItem('jogadorEldoraID'),action,rune_id:rid,item_id:selectedItem,slot:selectedSlot,revision:state.revision})});
   const result=await response.json();
   if(!result.success){await load();throw new Error(result.error||'Não foi possível concluir.');}
   state=result;render();dialog.querySelector('#rune-status').textContent='Operação concluída. Seus equipamentos foram atualizados.';
   await window.carregarMeuPerfil?.();
   if(window.perfilDadosGlobais&&document.getElementById('modal-item')?.style.display==='flex')window.fecharModalItem?.();
  }catch(error){render();dialog.querySelector('#rune-status').textContent=error.message;}
  finally{busy=false;dialog.querySelectorAll('button[data-action="fechar"]').forEach(e=>e.disabled=false);}
 }
 async function load(){
  const response=await boundedFetch(`/api/runas/${encodeURIComponent(localStorage.getItem('jogadorEldoraID')||'')}`);
  const result=await response.json();if(!response.ok||!result.success)throw new Error(result.error||'Falha ao carregar as runas.');state=result;render();
 }
 window.abrirOficinaRunas=async itemId=>{
  if(window.combateAbertoBloqueandoMapa||window.salaCombateGrupoAtual||window.raidInvasaoAtual){window.avisoEldora('Volte ao mapa antes de alterar runas.');return;}
  if(dialog?.open)return;
  selectedItem=itemId||selectedItem;page='equipar';busy=false;
  dialog=document.createElement('dialog');dialog.className='rune-workshop';dialog.setAttribute('aria-label','Oficina de Runas');dialog.innerHTML='<p>Carregando oficina…</p>';document.body.appendChild(dialog);
  window.__oficinaRunasAberta=true;dialog.showModal();
  const close=()=>{if(busy)return;dialog.close();dialog.remove();window.__oficinaRunasAberta=false;};
  dialog.addEventListener('cancel',e=>{e.preventDefault();close();});
  for(const type of ['click','dblclick','pointerdown','pointerup','pointermove','mousedown','mouseup','touchstart','touchend','touchmove','wheel','keydown','keyup'])dialog.addEventListener(type,e=>e.stopPropagation());
  dialog.addEventListener('click',e=>{
   const btn=e.target.closest('button');if(!btn||busy)return;
   if(btn.dataset.page){page=btn.dataset.page;render();}
   else if(btn.dataset.slot!==undefined){selectedSlot=Number(btn.dataset.slot);render();}
   else if(btn.dataset.action==='fechar')close();
   else if(btn.dataset.action)inFlight=operate(btn.dataset.action,btn.dataset.rune);
  });
  try{await load();}catch(error){dialog.innerHTML='<p></p><button data-action="fechar">Fechar</button>';dialog.querySelector('p').textContent=error.message;}
 };
})();
