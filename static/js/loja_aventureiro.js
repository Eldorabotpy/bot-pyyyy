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

window.abrirLojaAventureiro = function() {
    const menuLoja = document.getElementById('menu-loja-aventureiro');
    const lista = document.getElementById('lista-itens-aventureiro');
    
    if (!menuLoja || !lista) return console.error("HTML da loja não encontrado!");

    lista.innerHTML = '';
    const linkBaseNuvem = window.CATALOGO_SISTEMA ? "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/itens/" : "/static/assets/itens/";

    CATALOGO_AVENTUREIRO.forEach(item => {
        const pasta = window.obterPastaItem ? window.obterPastaItem(item.tipo) : 'consumiveis';
        const imgUrl = `${linkBaseNuvem}${pasta}/${item.id}.png`;

        let corNome = "#e74c3c"; 
        if(item.id.includes('mana')) corNome = "#3498db"; 
        if(item.id.includes('pedra')) corNome = "#9b59b6"; 
        if(item.id.includes('pergaminho')) corNome = "#f39c12"; 
        if(item.id.includes('nucleo')) corNome = "#e67e22"; 

        // 👇 A MÁGICA: Passamos o imgUrl para o 'onclick' da div 👇
        lista.innerHTML += `
            <div class="loja-item-card" onclick="mostrarDescricaoMerlin('${item.nome}', '${item.desc}', '${imgUrl}')">
                <div class="loja-item-info">
                    <img src="${imgUrl}" class="loja-item-img" onerror="this.src='https://placehold.co/44x44/111/f1c40f?text=📦'">
                    <div>
                        <span class="loja-item-nome" style="color: ${corNome};">${item.nome}</span>
                        <span class="loja-item-preco">💰 ${item.preco.toLocaleString('pt-BR')} Ouro</span>
                    </div>
                </div>
                <button class="btn-comprar-loja" onclick="event.stopPropagation(); comprarItemAventureiro('${item.id}', ${item.preco})">Comprar</button>
            </div>
        `;
    });

    menuLoja.style.display = 'block';
};

window.fecharLojaAventureiro = function() {
    document.getElementById('menu-loja-aventureiro').style.display = 'none';
};

// 👇 A MÁGICA DO ALERTA: Troca o Emoji pela Imagem real na hora de abrir 👇
window.mostrarDescricaoMerlin = function(nomeItem, descItem, imgUrl) {
    if (window.alertaEldora) {
        window.alertaEldora(nomeItem, descItem, 'pocao');
        
        setTimeout(() => {
            const iconeEl = document.getElementById('alerta-eldora-icone');
            if (iconeEl) {
                iconeEl.innerHTML = `<img src="${imgUrl}" style="width: 56px; height: 56px; object-fit: contain; filter: drop-shadow(0 4px 6px rgba(0,0,0,0.9)); margin-bottom: 5px;">`;
                iconeEl.style.textShadow = 'none'; // Tira o brilho de texto para não borrar a imagem
            }
        }, 10);
    } else {
        alert(`${nomeItem}\n\n${descItem}`);
    }
};

window.comprarItemAventureiro = async function(itemId, preco) {
    const charId = localStorage.getItem("jogadorEldoraID");
    if(!charId) return alert("Sessão não encontrada. Faça login novamente.");

    try {
        const res = await fetch('/api/loja/comprar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: charId, item_id: itemId, preco: preco })
        });
        
        const dados = await res.json();
    
        if (dados.erro) {
            if (window.alertaEldora) window.alertaEldora("Fundos Insuficientes", dados.erro, "erro");
            else alert("❌ " + dados.erro);
        } else {
            if (window.alertaEldora) window.alertaEldora("Compra Realizada!", `Sua compra foi enviada para a mochila.\nOuro restante: ${dados.novo_ouro.toLocaleString('pt-BR')}`, "sucesso");
            else alert("✅ Compra realizada!");
            
            if (typeof carregarMeuPerfil === 'function') carregarMeuPerfil();
        }
    } catch(e) {
        console.error(e);
        if (window.alertaEldora) window.alertaEldora("Conexão Perdida", "O mercador não conseguiu processar seu pedido.", "erro");
    }
};