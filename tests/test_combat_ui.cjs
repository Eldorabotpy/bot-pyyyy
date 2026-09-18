const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(require('path').join(__dirname,'../static/js/combate.js'),'utf8');
const elements=new Map();class El{constructor(){this.style={};this.dataset={};this.events={};this.innerHTML='';this.buttons=[new ElButton()];}addEventListener(n,f){this.events[n]=f;}querySelectorAll(){return this.buttons;}}
class ElButton{constructor(){this.style={};this.disabled=false;}}
const el=id=>{if(!elements.has(id))elements.set(id,new El());return elements.get(id);};
const scene={input:{enabled:true,keyboard:{enabled:true,resetKeys(){}}},player:{body:{stop(){}}}};
const ctx={console,window:{jogoEldora:{scene:{getScene:()=>scene}}},localStorage:{getItem:()=> 'member'},document:{getElementById:el,querySelector:()=>el('canvas')},atualizarBotaoRetornoGrupo(){},atualizarVisualBarra(){}};vm.createContext(ctx);
function func(name,next){vm.runInContext(source.slice(source.indexOf('function '+name),source.indexOf(next,source.indexOf('function '+name))),ctx);}
vm.runInContext('let entradaAntesCombate = null;',ctx);
func('travarMapaDuranteCombate(', 'instalarTravaCliqueCombate();');
func('atualizarControleTurnoGrupo(', 'function renderizarGrupoCombate(');
func('sincronizarMeuHudPelaSala(', 'function aplicarEstadoCombateGrupo(');
ctx.travarMapaDuranteCombate(true);ctx.travarMapaDuranteCombate(true);assert.equal(scene.input.enabled,false);assert.equal(scene.input.keyboard.enabled,false);
let stopped=0;el('tela-combate-global').events.click({stopPropagation(){stopped++;}});assert.equal(stopped,1);
ctx.travarMapaDuranteCombate(false);assert.equal(scene.input.enabled,true);assert.equal(scene.input.keyboard.enabled,true);
el('log-texto-1').innerHTML='Vitória!';ctx.atualizarControleTurnoGrupo({estado:'vitoria',membros_prontos:{a:true,b:true}});assert.equal(el('log-texto-1').innerHTML,'Vitória!');assert.equal(el('menu-botoes').style.display,'none');
ctx.atualizarControleTurnoGrupo({estado:'aguardando',membros_ids:['a','b'],membros_prontos:{a:true}});assert.match(el('log-texto-1').innerHTML,/1\/2/);
ctx.window.dadosCombateAtual={};ctx.sincronizarMeuHudPelaSala({herois:[{id:'member',current_hp:0,hp:100,current_mp:0,mp:50,max_hp:100,max_mana:50}]});assert.equal(ctx.window.dadosCombateAtual.playerHpAtual,0);assert.equal(ctx.window.dadosCombateAtual.playerMpAtual,0);
console.log('PASS combat input isolation, scene restore, victory state, loading state, zero HP/MP');
