const vm=require('vm'),fs=require('fs'),assert=require('node:assert/strict'),path=require('path');
class El {constructor(){this.style={};this.dataset={};this.innerHTML='';this.scrollTop=0;this.classList={add(){},remove(){},toggle(){}};}addEventListener(){} }
const nodes=new Map(),get=id=>{if(!nodes.has(id))nodes.set(id,new El());return nodes.get(id);};
let requests=[],timers=new Map(),intervals=new Map(),n=0;
const ctx={console,AbortController,Date,JSON,Number,String,Math,localStorage:{getItem:()=> 'hero'},document:{visibilityState:'visible',getElementById:get,querySelectorAll:()=>[],addEventListener(){},body:{classList:{add(){},remove(){}}}},window:{},setTimeout:(f)=>{timers.set(++n,f);return n;},clearTimeout:id=>timers.delete(id),setInterval:f=>{intervals.set(++n,f);return n;},clearInterval:id=>intervals.delete(id),fetch:(url,options)=>new Promise((resolve,reject)=>{requests.push({url,options,resolve:data=>resolve({ok:true,json:async()=>data}),reject});options?.signal?.addEventListener('abort',()=>reject(Object.assign(new Error('abort'),{name:'AbortError'})));})};
vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/js/guild_missions.js'),'utf8'),ctx);
const data={success:true,pontos_guilda:120,pontos_guilda_total:320,rank_guilda:{nome:'Bronze'},ativas:[],disponiveis:[],concluidas:[]};
const settle=async()=>{for(let i=0;i<8;i++)await Promise.resolve();};
(async()=>{
 const open=ctx.window.abrirGuildaMissoes();assert.equal(requests.length,1);requests[0].resolve(data);await open;
 assert.match(get('guild-pontos-area').innerHTML,/120/);assert.equal(intervals.size,1);
 const old=ctx.window.recarregarGuildaMissoes();const shop=ctx.window.navegarGuilda('loja');requests.at(-1).resolve({...data,pontos_guilda:90,produtos:[]});await shop;await old;
 assert.match(get('guild-pontos-area').innerHTML,/90/);
 const personal=ctx.window.navegarGuilda('individual');requests.at(-1).resolve(data);await personal;
 ctx.window.mudarAbaGuildaMissoes('concluidas');get('guild-missoes-lista').scrollTop=80;
 const refresh=[...intervals.values()][0];refresh();requests.at(-1).resolve({...data,pontos_guilda:140});await settle();
 assert.match(get('guild-pontos-area').innerHTML,/140/);assert.match(get('guild-missoes-lista').innerHTML,/histórico/);assert.equal(get('guild-missoes-lista').scrollTop,80);
 const hanging=ctx.window.atualizarPainelGuilda();[...timers.values()].at(-1)();await hanging;assert.match(get('guild-missoes-lista').innerHTML,/Tentar novamente/);
 const b=new El(),before=requests.length;const accept=ctx.window.aceitarMissaoGuilda('m',b);await ctx.window.aceitarMissaoGuilda('m',b);assert.equal(requests.length,before+1);requests.at(-1).resolve({success:false,error:'Não disponível'});await accept;
 ctx.window.fecharGuildaMissoes();assert.equal(intervals.size,0);assert.equal(ctx.window.__guildaAberta,false);
 console.log('PASS guild: opening, balances, navigation races, periodic refresh, preserved tab/scroll, timeout retry, duplicate submit, close cleanup');
})().catch(e=>{console.error(e);process.exitCode=1;});
