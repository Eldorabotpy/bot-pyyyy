const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict'),path=require('path');
const source=fs.readFileSync(path.join(__dirname,'../static/js/combate.js'),'utf8');
function between(a,b){return source.slice(source.indexOf(a),source.indexOf(b,source.indexOf(a)));}
let uid='member',sent=[],handlers={},interval,closed=0,started=0;
const button={style:{},disabled:false},els=new Map();
function el(id){if(!els.has(id))els.set(id,{style:{},innerHTML:''});return els.get(id);}
const socket={connected:true,off(name){delete handlers[name];},on(name,fn){handlers[name]=fn;},emit(name,data){sent.push({name,data});},timeout(){return {emit:(name,data,cb)=>sent.push({name,data,cb})};}};
const ctx={console,Set,String,Number,Math,localStorage:{getItem:()=>uid},window:{eldoraSocket:socket},document:{querySelector:()=>button,getElementById:el,querySelectorAll:()=>[],dispatchEvent(){}},setInterval:fn=>interval=fn,setTimeout(){},fecharSeletorAlvoGrupo(){},restaurarUiMapaDepoisCombate(){closed++;},travarMapaDuranteCombate(){},normalizarIdCombateGrupo:x=>String(x||''),renderizarGrupoCombate(){},sincronizarMeuHudPelaSala(){},atualizarControleTurnoGrupo(){},extrairHpMobDaSalaGrupo:()=>null,finalizarAnimacaoCombate(){}};
vm.createContext(ctx);
vm.runInContext(between('const salasGrupoDevolvidas','// ==========================================')+between('function sairDaArena(', 'window.animarInvestidaSprite')+between('function extrairSalaPayloadGrupo(', 'function extrairHpMobDaSalaGrupo(')+between('function aplicarEstadoCombateGrupo(', '\nregistrarSocketCombateGrupo();'),ctx);
const room=(id='r')=>({sala_id:id,tipo:'cacada',lider_id:'leader',estado:'vitoria',membros_ids:['leader','member'],mobs:[]});
ctx.window.salaCombateGrupoAtual='r';ctx.window.estadoCombateGrupoAtual=room();ctx.registrarSocketCombateGrupo();
ctx.atualizarBotaoRetornoGrupo();assert.equal(button.disabled,true);ctx.sairDaArena();assert.equal(sent.length,0);assert.equal(closed,0);
uid='leader';ctx.atualizarBotaoRetornoGrupo();assert.equal(button.disabled,false);ctx.sairDaArena();ctx.sairDaArena();assert.equal(sent.length,1);
sent[0].cb(null,{success:true,sala:{...room(),retorno_mapa:true}});assert.equal(closed,1);assert.equal(ctx.window.salaCombateGrupoAtual,null);
assert.equal(ctx.aplicarEstadoCombateGrupo({...room(),retorno_mapa:false}),false);
ctx.window.salaCombateGrupoAtual='r2';ctx.window.estadoCombateGrupoAtual=room('r2');
handlers.grupoRetornouMapa({...room(),retorno_mapa:true});assert.equal(closed,1);
interval();assert.equal(sent.at(-1).name,'solicitarEstadoSala');
ctx.aplicarEstadoCombateGrupo({...room('r2'),retorno_mapa:true});assert.equal(closed,2);
ctx.window.salaCombateGrupoAtual='r3';ctx.window.estadoCombateGrupoAtual=room('r3');ctx.window.iniciarCacadaApp=async()=>{started++;};
(async()=>{
 await handlers.convocarCombateGrupo({sala_id:'r4',spawn_id:'new',sala:room('r4')});assert.equal(started,1);assert.equal(closed,3);assert.equal(ctx.window.salaCombateGrupoAtual,'r4');
 await handlers.convocarCombateGrupo({sala_id:'r3',spawn_id:'old',sala:room('r3')});assert.equal(started,1);
 console.log('PASS: leader/member controls, double click, confirmed collective return, missed message recovery, stale events, next hunt');
})().catch(e=>{console.error(e);process.exitCode=1;});
