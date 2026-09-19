const fs = require('fs'), vm = require('vm'), assert = require('node:assert/strict');
const source = fs.readFileSync(require('path').join(__dirname, '../static/js/combate.js'), 'utf8');
let now=0, seq=0, timers=new Map(), images=[], effects=[];
const timeout=(fn,ms)=>{const id=++seq;timers.set(id,{fn,at:now+ms});return id;};
const interval=(fn,ms)=>{const id=++seq;timers.set(id,{fn,at:now+ms,ms});return id;};
async function advance(ms){const end=now+ms;while(true){const next=[...timers].sort((a,b)=>a[1].at-b[1].at)[0];if(!next||next[1].at>end)break;const [id,t]=next;now=t.at;if(t.ms)t.at+=t.ms;else timers.delete(id);t.fn();await Promise.resolve();}now=end;await Promise.resolve();}
const elements=new Map();
function el(id){if(!elements.has(id))elements.set(id,{style:{opacity:'1'},isConnected:true,offsetLeft:0,offsetTop:0,offsetWidth:128,offsetHeight:128,parentElement:{appendChild(n){effects.push(n);}},innerText:'',innerHTML:''});return elements.get(id);}
const ctx={console,Image:class {constructor(){images.push(this);}set src(v){this.url=v;}},document:{getElementById:el,createElement:()=>({style:{},remove(){this.removed=true;}})},setTimeout:timeout,clearTimeout:id=>timers.delete(id),setInterval:interval,clearInterval:id=>timers.delete(id),window:{dadosCombateAtual:{}},animarEfeitoVisual(){effects.push({fallback:true});}};
vm.createContext(ctx);
vm.runInContext(source.slice(source.indexOf('window.animarMagiaSpriteGrid ='),source.indexOf('function atualizarControleTurnoGrupo(')),ctx);
(async()=>{
 let done=false;ctx.window.animarMagiaSpriteGrid('sprite-mob','test').then(()=>done=true);
 await advance(1800);assert.equal(done,false);assert.equal(effects.length,0);
 images.at(-1).onload();await advance(900);assert.equal(done,false);await advance(200);assert.equal(done,true);assert.equal(effects.at(-1).removed,true);
 done=false;ctx.window.animarMagiaSpriteGrid('sprite-mob','missing').then(()=>done=true);images.at(-1).onerror();await advance(601);assert.equal(done,true);
 done=false;ctx.window.animarMagiaSpriteGrid('sprite-mob','slow').then(()=>done=true);await advance(3101);assert.equal(done,true);assert.equal(images.at(-1).onload,null);
 const before=effects.length;ctx.window.animarMagiaSpriteGrid('sprite-mob','old');ctx.window.dadosCombateAtual={};images.at(-1).onload();assert.equal(effects.length,before);
 // Exercise the real round sequencer with a skill that has not finished loading.
 let finishSkill;const skill=new Promise(r=>finishSkill=r);let victories=0;
 Object.assign(ctx,{salasGrupoDevolvidas:new Set(),combatePacotePertenceAMim:()=>true,combateLogPertenceAMim:()=>true,atualizarVisualBarra(){},mostrarNumeroDano(){},musicaDeFundoAtual:null,finalizarAnimacaoCombate(){victories++;}});
 ctx.window.dadosCombateAtual={mobHpAtual:20,mobHpMax:20,playerHpAtual:100,playerHpMax:100};ctx.window.animarMagiaSpriteGrid=()=>skill;ctx.window.animarInvestidaSprite=()=>{};ctx.window.animarDanoSprite=()=>{};
 vm.runInContext(source.slice(source.indexOf('function animarAcoesDaRodada('),source.indexOf('function rodarAnimacaoLevelUp(')),ctx);
 ctx.animarAcoesDaRodada({log:[{autor:'player',texto:'Dano: 30',dano:30,anim_effect:'test'}],vitoria:true,mob_hp_atual:0},'magia','test','Teste');
 await advance(5000);assert.equal(el('sprite-mob').style.opacity,'1');assert.equal(ctx.window.dadosCombateAtual.mobHpAtual,20);assert.equal(victories,0);
 finishSkill(true);for(let i=0;i<5;i++)await Promise.resolve();assert.equal(ctx.window.dadosCombateAtual.mobHpAtual,0);
 await advance(1201);assert.equal(el('sprite-mob').style.opacity,'0');await advance(1001);assert.equal(victories,1);
 // Each hit advances its own damage, healing and label before the next hit.
 ctx.window.dadosCombateAtual={mobHpAtual:100,mobHpMax:100,playerHpAtual:50,playerHpMax:100};
 ctx.animarAcoesDaRodada({log:[
  {autor:'player',texto:'Ataque 1',golpe:1,dano:30,roubo_vida:3,player_hp_apos_golpe:53},
  {autor:'player',texto:'Ataque 2',golpe:2,dano:50,roubo_vida:5,player_hp_apos_golpe:58}
 ],vitoria:true,mob_hp_atual:0},'atacar');
 assert.equal(ctx.window.dadosCombateAtual.playerHpAtual,53);
 assert.equal(ctx.window.dadosCombateAtual.mobHpAtual,70);
 assert.match(el('log-texto-1').innerHTML,/Ataque 1/);
 await advance(1201);
 assert.equal(ctx.window.dadosCombateAtual.playerHpAtual,58);
 assert.equal(ctx.window.dadosCombateAtual.mobHpAtual,20);
 assert.match(el('log-texto-1').innerHTML,/Ataque 2/);
 await advance(2201);
 // A group victory arriving before HTTP must not hide the target.
 Object.assign(ctx,{extrairSalaPayloadGrupo:d=>d.sala,normalizarIdCombateGrupo:v=>String(v||'')});
 ctx.window.salaCombateGrupoAtual='room';ctx.window.dadosCombateAtual.rodadaVisualPendente=true;
 vm.runInContext(source.slice(source.indexOf('function aplicarEstadoCombateGrupo('),source.indexOf('function registrarSocketCombateGrupo(')),ctx);
 const packet={sala:{sala_id:'room',estado:'vitoria'}};
 assert.equal(ctx.aplicarEstadoCombateGrupo(packet),true);
 assert.equal(ctx.window.dadosCombateAtual.estadoGrupoAposAnimacao.dados,packet);
 assert.equal(victories,2);
 console.log('PASS delayed skill precedes damage/death; missing/timeout assets resolve; stale load cancelled');
})().catch(e=>{console.error(e);process.exitCode=1;});
