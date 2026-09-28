const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../static/js/central_eldora.js'), 'utf8');
const section = source.slice(source.indexOf('    const ENCICLOPEDIA_ELDORA'), source.indexOf('    /*\n', source.indexOf('    function voltarMenuEnciclopediaCentral')) > -1 ? source.indexOf('    /*\n', source.indexOf('    function voltarMenuEnciclopediaCentral')) : source.indexOf('    /*\r\n', source.indexOf('    function voltarMenuEnciclopediaCentral')));
const elements = new Map();
function elemento(id) {
    if (!elements.has(id)) elements.set(id, {value: '', innerHTML: '', textContent: '', style: {}, offsetTop: 200, focus() {}});
    return elements.get(id);
}
const nodes = [
    {id: 'capital', parent: 'mundo', titulo: 'Reino de Eldora', resumo: 'Capital', icone: '🏰', secoes: []},
    {id: 'forja', parent: 'capital', titulo: 'Forja', resumo: 'Thorek', icone: '⚒️', secoes: [['Uso', 'Fabricar']]},
    ...Array.from({length: 35}, (_, i) => ({id: `recipe:${i}`, parent: 'forja', titulo: `Receita ${i}`, resumo: 'Poção', icone: '', secoes: []})),
];
let attempts = 0;
const context = vm.createContext({elemento, escaparHtmlCentral: x => String(x), fetch: async () => {
    attempts++;
    if (attempts === 1) throw new Error('offline');
    return {ok: true, json: async () => ({success: true, nodes})};
}});
vm.runInContext(section, context);
(async () => {
    await context.carregarEnciclopediaCentral();
    assert.match(elemento('central-enciclopedia-status').textContent, /tentar novamente/);
    await context.carregarEnciclopediaCentral();
    context.abrirVerbeteEnciclopediaCentral('forja');
    assert.match(elemento('central-enciclopedia-caminho').textContent, /Mundo e regiões › Reino de Eldora › Forja/);
    assert.equal(elemento('central-enciclopedia-mais').hidden, false);
    assert.equal((elemento('central-enciclopedia-detalhe-conteudo').innerHTML.match(/data-enciclopedia-id/g) || []).length, 30);
    context.voltarMenuEnciclopediaCentral();
    assert.equal(elemento('central-enciclopedia-detalhe-titulo').textContent, 'Reino de Eldora');
    context.voltarMenuEnciclopediaCentral();
    context.voltarMenuEnciclopediaCentral();
    assert.equal(elemento('central-enciclopedia-menu').style.display, 'block');
    context.renderizarEnciclopediaCentral('pocao');
    assert.match(elemento('central-enciclopedia-grade').innerHTML, /Receita 0/);
    context.abrirVerbeteEnciclopediaCentral('forja');
    elemento('central-enciclopedia-filtro').value = 'Receita 34';
    context.mostrarPaginaEnciclopedia(false);
    assert.equal(elemento('central-enciclopedia-mais').hidden, true);
    assert.match(elemento('central-enciclopedia-detalhe-conteudo').innerHTML, /Receita 34/);
    console.log('Enciclopédia: navegação, retorno, busca sem acento, paginação e recuperação de erro passaram.');
})().catch(error => { console.error(error); process.exitCode = 1; });
