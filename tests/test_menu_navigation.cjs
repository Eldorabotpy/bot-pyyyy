const fs = require('fs');
const assert = require('node:assert/strict');

const html = fs.readFileSync('templates/index.html', 'utf8');

for (const action of [
    'abrirCentralEldora',
    'abrirTelaCla',
    'abrirLojaPremium',
]) {
    const expected = `navegarMenuHeroi('aba-reino', '${action}')`;
    assert.ok(
        html.includes(expected),
        `${action} deve ativar o mapa antes de abrir sua janela`
    );
}

assert.ok(
    html.includes(`navegarMenuHeroi('aba-perfil')`),
    'Mochila e Perfil deve continuar abrindo a aba de perfil'
);

console.log('Destinos do menu ativam o contêiner correto antes de abrir janelas.');
