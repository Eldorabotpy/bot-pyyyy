const fs = require('fs');
const vm = require('vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('static/js/perfil.js', 'utf8');
const start = source.indexOf('    // 👇 MÁGICA 2:');
const end = source.indexOf('    if (itemData.rune_slots?.length)', start);
assert.ok(start > 0 && end > start);
for (const origem of ['mochila', 'inventario', 'equipado']) {
  for (const scroll of ['pergaminho_de_reparo', 'pergaminho_durabilidade']) {
    const context = {origem, t: 'tool', idReal: 'martelo', nomeLower: 'martelo', itemData: {id:'crafted',slot:'tool',durability:[0,90]}, window: {perfilDadosGlobais:{inventario:[{base_id:scroll}]}}};
    vm.runInNewContext('let botoesHtml = "";\n' + source.slice(start,end) + '\nresult = botoesHtml;', context);
    assert.match(context.result, /CONSERTAR/);
    assert.match(context.result, origem === 'equipado' ? /Remover/ : /Equipar/);
  }
}
console.log('Reparo visível com ambos os pergaminhos na mochila e nos equipados.');
