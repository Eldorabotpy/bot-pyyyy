const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
for(const file of fs.readdirSync(path.join(root,'static/js')).filter(f=>f.endsWith('.js'))){
 const src=fs.readFileSync(path.join(root,'static/js',file),'utf8');
 new vm.Script(src,{filename:file});
 assert.doesNotMatch(src,/(?<![\w.])(?:alert|confirm|prompt)\s*\(/,file+' still has native dialogs');
}
for(const file of ['admin_panel.html','login.html','index.html']){
 const src=fs.readFileSync(path.join(root,'templates',file),'utf8');
 assert.ok(src.includes('/static/js/dialogos_eldora.js?v=1'),file+' missing dialogs');
 for(const [i,match] of [...src.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)].entries()){
  if(!match[1].trim())continue;
  const js=match[1].replace(/\{\{[\s\S]*?\}\}/g,'null').replace(/\{%[\s\S]*?%\}/g,'');
  new vm.Script(js,{filename:file+':script'+i});
 }
}
// Exercise actual party action: cancel emits nothing; confirmation emits once.
const src=fs.readFileSync(path.join(root,'static/js/mapa_multiplayer.js'),'utf8');
const start=src.indexOf('window.sairDoGrupoEldora =');const end=src.indexOf('\n};',start)+3;
let accept=false,sends=0,removed=0;
const ctx={window:{confirmarEldora:async()=>accept,eldoraSocket:{emit(){sends++;}}},document:{getElementById:()=>({remove(){removed++;}})}};
vm.createContext(ctx);vm.runInContext(src.slice(start,end),ctx);
(async()=>{await ctx.window.sairDoGrupoEldora();assert.equal(sends,0);assert.equal(removed,0);accept=true;await ctx.window.sairDoGrupoEldora();assert.equal(sends,1);assert.equal(removed,1);console.log('PASS script syntax, template wiring, no native dialogs, group cancel/confirm');})().catch(e=>{console.error(e);process.exitCode=1;});
