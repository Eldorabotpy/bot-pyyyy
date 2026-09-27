const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const ctx={window:{perfilDadosGlobais:{inventario:[{base_id:'ferro',qtd:2},{base_id:'ferro',qtd:3}],equipamentos:[],equipment_tools:{ferreiro:'tool'}}},document:{getElementById:()=>null}};
vm.createContext(ctx);vm.runInContext(fs.readFileSync('static/js/forja.js','utf8'),ctx);
assert.equal(vm.runInContext('ForjaEngine.verificarPermissaoDeCraft({inputs:{ferro:5}}).podeCriar',ctx),true);
assert.equal(vm.runInContext('ForjaEngine.verificarPermissaoDeCraft({inputs:{ferro:6}}).podeCriar',ctx),false);
ctx.window.perfilDadosGlobais.inventario=[{id:'tool',tipo:'tool'},{id:'spare',tipo:'tool'}];
assert.equal(vm.runInContext('ForjaEngine.getItensParaDesmontar().length',ctx),1);
console.log('Materiais somados e ferramenta equipada excluída do desmonte.');

vm.runInContext(fs.readFileSync('static/js/forja_imagens.js','utf8'),ctx);
assert.ok(vm.runInContext("getCaminhosImagemMaterialForja('barra_de_ferro')[0]",ctx).endsWith('/materiais/barra_de_ferro.png'));
assert.ok(vm.runInContext("getCaminhosImagemItemForja({base_id:'craft_martelo_armeiro_t1'})[0]",ctx).endsWith('/equipamentos/craft_martelo_armeiro_t1.png'));
assert.equal(vm.runInContext("getCaminhosImagemItemForja({base_id:'x',icon_url:'https://example.org/item.png'})[0]",ctx),'https://example.org/item.png');
console.log('Imagens cadastradas têm prioridade sobre pastas presumidas.');
