// Catálogo interno do Mercador (Loja a Ouro)
const CATALOGO_AVENTUREIRO = [
    { id: 'pocao_cura_leve', nome: 'Poção de Cura P', preco: 100, tipo: 'potion', desc: 'Recupera 100 de HP instantaneamente.' },
    { id: 'pocao_cura_media', nome: 'Poção de Cura M', preco: 300, tipo: 'potion', desc: 'Recupera 300 de HP instantaneamente.' },
    { id: 'pocao_cura_grande', nome: 'Poção de Cura G', preco: 1000, tipo: 'potion', desc: 'Recupera 1000 de HP instantaneamente.' },
    { id: 'pocao_mana_leve', nome: 'Poção de Mana P', preco: 100, tipo: 'potion', desc: 'Recupera 100 de MP instantaneamente.' },
    { id: 'pocao_mana_media', nome: 'Poção de Mana M', preco: 300, tipo: 'potion', desc: 'Recupera 300 de MP instantaneamente.' },
    { id: 'pocao_mana_grande', nome: 'Poção de Mana G', preco: 1000, tipo: 'potion', desc: 'Recupera 1000 de MP instantaneamente.' },
    { id: 'pedra_de_aprimoramento', nome: 'Pedra de Aprimoramento', preco: 500, tipo: 'consumivel', desc: 'Um fragmento mágico usado para evoluir equipamentos na forja.' },
    { id: 'pergaminho_de_reparo', nome: 'Pergaminho de Reparo', preco: 1000, tipo: 'consumivel', desc: 'Magia ancestral que restaura completamente a durabilidade de tudo que você veste.' },
    { id: 'nucleo_de_forja', nome: 'Núcleo de Forja', preco: 500, tipo: 'consumivel', desc: 'Material incandescente essencial para criar novos itens com o Ferreiro.' }
];


let merlinSelecionado = null;
let merlinComprando = false;
let merlinCatalogo = [];
const merlinEl = id => document.getElementById(id);
const merlinNumero = valor => Number(valor).toLocaleString('pt-BR');
function merlinImagem(item) {
    const base = window.CATALOGO_SISTEMA ? 'https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/itens/' : '/static/assets/itens/';
    return `${base}${window.obterPastaItem ? window.obterPastaItem(item.tipo) : 'consumiveis'}/${item.id}.png`;
}
window.abrirLojaAventureiro = async function() {
    if (merlinComprando) return;
    merlinSelecionado = null;
    merlinEl('merlin-compra').hidden = true;
    const lista = merlinEl('lista-itens-aventureiro');
    lista.hidden = false;
    lista.textContent = 'Consultando mercadorias…';
    merlinEl('menu-loja-aventureiro').style.display = 'flex';
    document.querySelectorAll('.btn-passe-mapa').forEach(btn => btn.style.display = 'none');
    try {
        const res = await fetch('/api/loja/catalogo');
        if (!res.ok) throw new Error();
        const dados = await res.json();
        merlinCatalogo = CATALOGO_AVENTUREIRO.flatMap(item => {
            const oficial = dados.itens.find(x => x.id === item.id);
            return oficial ? [{...item, preco: oficial.preco}] : [];
        });
        lista.replaceChildren();
        merlinCatalogo.forEach(item => {
            const button = document.createElement('button');
            button.type = 'button'; button.className = 'loja-item-card';
            const img = document.createElement('img');
            img.src = merlinImagem(item); img.alt = ''; img.className = 'loja-item-img';
            img.onerror = () => { img.hidden = true; };
            const nome = document.createElement('span');
            nome.className = 'loja-item-nome'; nome.textContent = item.nome;
            const preco = document.createElement('span');
            preco.className = 'loja-item-preco'; preco.textContent = `${merlinNumero(item.preco)} Ouro / un.`;
            button.append(img, nome, preco);
            button.onclick = () => selecionarItemMerlin(item.id);
            lista.append(button);
        });
    } catch (_) {
        lista.textContent = 'Não foi possível carregar a loja. Feche e tente novamente.';
    }
};
window.fecharLojaAventureiro = function() {
    if (merlinComprando) return;
    merlinEl('menu-loja-aventureiro').style.display = 'none';
    document.querySelectorAll('.btn-passe-mapa').forEach(btn => btn.style.display = 'flex');
};
window.selecionarItemMerlin = function(id) {
    if (merlinComprando) return;
    merlinSelecionado = merlinCatalogo.find(x => x.id === id);
    if (!merlinSelecionado) return;
    merlinEl('lista-itens-aventureiro').hidden = true;
    merlinEl('merlin-compra').hidden = false;
    merlinEl('merlin-imagem').src = merlinImagem(merlinSelecionado);
    merlinEl('merlin-nome').textContent = merlinSelecionado.nome;
    merlinEl('merlin-descricao').textContent = merlinSelecionado.desc;
    merlinEl('merlin-unitario').textContent = `${merlinNumero(merlinSelecionado.preco)} Ouro por unidade`;
    merlinEl('merlin-quantidade').value = 1;
    merlinEl('merlin-feedback').textContent = '';
    atualizarTotalMerlin();
};
window.voltarItensMerlin = function() {
    if (merlinComprando) return;
    merlinEl('merlin-compra').hidden = true;
    merlinEl('lista-itens-aventureiro').hidden = false;
};
window.atualizarTotalMerlin = function() {
    const qtd = Number(merlinEl('merlin-quantidade').value);
    const valido = Number.isInteger(qtd) && qtd >= 1 && qtd <= 999;
    merlinEl('merlin-total').textContent = valido && merlinSelecionado ? `${merlinNumero(qtd * merlinSelecionado.preco)} Ouro` : 'Quantidade inválida';
    merlinEl('merlin-confirmar').disabled = !valido || merlinComprando;
};
window.ajustarQuantidadeMerlin = function(delta) {
    const input = merlinEl('merlin-quantidade');
    input.value = Math.min(999, Math.max(1, (Number(input.value) || 1) + delta));
    atualizarTotalMerlin();
};
window.comprarItemAventureiro = async function() {
    if (merlinComprando || !merlinSelecionado) return;
    const quantidade = Number(merlinEl('merlin-quantidade').value);
    if (!Number.isInteger(quantidade) || quantidade < 1 || quantidade > 999) return;
    const userId = localStorage.getItem('jogadorEldoraID');
    if (!userId) { merlinEl('merlin-feedback').textContent = 'Entre novamente para comprar.'; return; }
    merlinComprando = true;
    merlinEl('merlin-confirmar').textContent = 'Comprando…';
    merlinEl('merlin-feedback').textContent = '';
    merlinEl('merlin-controles').disabled = true;
    atualizarTotalMerlin();
    try {
        const res = await fetch('/api/loja/comprar', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({user_id: userId, item_id: merlinSelecionado.id, quantidade})});
        const dados = await res.json();
        if (!res.ok || !dados.sucesso) throw new Error(dados.erro || 'Não foi possível comprar.');
        merlinEl('merlin-feedback').textContent = `${quantidade} × ${merlinSelecionado.nome} enviados à mochila. Ouro restante: ${merlinNumero(dados.novo_ouro)}.`;
        if (typeof carregarMeuPerfil === 'function') carregarMeuPerfil();
    } catch (erro) {
        merlinEl('merlin-feedback').textContent = erro.message || 'Conexão interrompida. Confira a mochila antes de tentar novamente.';
    } finally {
        merlinComprando = false;
        merlinEl('merlin-controles').disabled = false;
        merlinEl('merlin-confirmar').textContent = 'Confirmar compra';
        atualizarTotalMerlin();
    }
};
