const vm = require('vm'), fs = require('fs'), assert = require('node:assert/strict');
const path = require('path');
const elements = new Map();
class El {
 constructor(){this.value='';this.style={};this.dataset={};this.events={};this.max='';this.parentElement={querySelector:()=>null};}
 addEventListener(name,fn){this.events[name]=fn;}
 contains(el){return el===this;}
 querySelector(){return null;}
 querySelectorAll(){return [];}
 removeAttribute(name){delete this[name];}
 setAttribute(){}
 blur(){}
}
const el = id => {if(!elements.has(id)) elements.set(id,new El());return elements.get(id);};
let posts=0, body, release, alerts=[];
const scene={input:{enabled:true,keyboard:{enabled:true,resetKeys(){}}},player:{body:{stop(){}}}};
const ctx={console,Set,localStorage:{getItem:()=> 'player'},document:{activeElement:new El(),getElementById:el,querySelector:()=>el('submit'),querySelectorAll:()=>[],addEventListener(){}},window:{jogoEldora:{scene:{getScene:()=>scene}},alertaEldora:(...a)=>alerts.push(a)},fetch:async (url,options)=>{posts++;body=JSON.parse(options.body);await new Promise(r=>release=r);return {ok:true,text:async()=>JSON.stringify({sucesso:true})};}};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/js/mercado.js'),'utf8'),ctx);
ctx.carregarInventarioNoMercado=()=>{};ctx.carregarVitrineMercado=async()=>{};
assert.equal(ctx.mercadoItemEhUnico({tipo:'consumivel',stats:{},attributes:{},enchantments:{},refino:0}),false);
assert.equal(ctx.mercadoItemEhUnico({tipo:'consumivel',stackable:true,upgrade_level:0}),false);
assert.equal(ctx.mercadoItemEhUnico({tipo:'weapon',stats:{}}),true);
for (const invalid of ['1.5','1e3','-1','0','', '9007199254740992']) assert.equal(ctx.mercadoInteiroPositivo(invalid),0);
assert.equal(ctx.mercadoInteiroPositivo('150'),150);
ctx.abrirMercado();ctx.abrirMercado();
assert.equal(scene.input.enabled,false);assert.equal(scene.input.keyboard.enabled,false);
let stopped=0;
for(const event of ['pointerdown','click','keydown','touchstart'])el('ui-mercado').events[event]({target:el('input-preco'),stopPropagation(){stopped++;},preventDefault(){throw Error('Native editing was blocked');}});
assert.equal(stopped,4);
assert.equal(el('lista-dropdown-venda').style.display,'none');
ctx.fecharMercado();assert.equal(scene.input.enabled,true);assert.equal(scene.input.keyboard.enabled,true);assert.equal(ctx.window.__mercadoAberto,false);
el('select-item-venda').value='pocao_cura_leve';el('input-qtd').value='3';el('input-qtd').max='10';el('input-preco').value='150';el('select-moeda').value='ouro';
(async()=>{
 el('input-preco').value='1.5';await ctx.confirmarVenda();assert.equal(posts,0);
 el('input-preco').value='150';el('input-qtd').value='11';await ctx.confirmarVenda();assert.equal(posts,0);
 el('input-qtd').value='3';ctx.calcularTaxaReino();assert.equal(el('res-liquido').innerText,'135 🪙');
 const pending=ctx.confirmarVenda();await ctx.confirmarVenda();assert.equal(posts,1);
 assert.equal(body.quantidade,3);assert.equal(body.preco,150);assert.equal(body.item_id,'pocao_cura_leve');
 release();await pending;assert.equal(ctx.window.__mercadoVendendo,false);assert.equal(el('submit').disabled,false);
 let profiles=0, vitrines=0;
 ctx.window.carregarMeuPerfil=async()=>{profiles++;};ctx.carregarVitrineMercado=async()=>{vitrines++;};
 const events=new Map(), socket={on:(k,f)=>events.set(k,f),off:(k,f)=>{if(events.get(k)===f)events.delete(k);}};
 ctx.window.configurarOuvintesMercado(socket);ctx.window.configurarOuvintesMercado(socket);
 assert.equal(events.size,2);
 ctx.window.__mercadoAberto=false;
 await events.get('mercadoAtualizado')({jogadores:['player','buyer']});
 assert.equal(profiles,1);assert.equal(vitrines,0);
 await events.get('mercadoAtualizado')({jogadores:['other']});assert.equal(profiles,1);
 ctx.window.__mercadoAberto=true;el('input-preco').value='777';
 await events.get('mercadoAtualizado')({jogadores:['player']});
 assert.equal(profiles,2);assert.equal(vitrines,1);assert.equal(el('input-preco').value,'777');
 await events.get('connect')();assert.equal(profiles,3);assert.equal(vitrines,2);
 const replacement={on(){},off(){}};ctx.window.configurarOuvintesMercado(replacement);assert.equal(events.size,0);
 console.log('PASS: seller refresh with market closed/open, unrelated users, reconnect, listener cleanup, preserved form');
 console.log('PASS: potion classification, integer validation, input isolation, scene restore, stock limit, tax, sale payload and double submit');
})().catch(e=>{console.error(e);process.exitCode=1;});

