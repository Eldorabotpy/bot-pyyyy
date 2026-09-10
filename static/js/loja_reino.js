// static/js/loja_reino.js

window.abrirLojaReino = function() {
    // Esconde o menu de expressões caso esteja aberto
    const menuExp = document.getElementById('menu-expressoes');
    if (menuExp) menuExp.style.display = 'none';
    
    document.getElementById('modal-loja-reino').style.display = 'flex';
};

window.fecharLojaReino = function() {
    document.getElementById('modal-loja-reino').style.display = 'none';
};

window.comprarItemGema = function(itemId) {
    if (window.eldoraSocket) {
        window.eldoraSocket.emit('comprar_item_gema', { item: itemId });
    } else {
        alert("O reino está sem conexão no momento!");
    }
};

// Precisamos garantir que esse "ouvinte" só seja ativado depois que o Socket existir
// Vamos chamar essa função de dentro do mapa_multiplayer.js quando o jogador conectar!
window.configurarOuvintesLojaReino = function(socket) {
    // Remove listeners antigos para evitar compras duplicadas
    socket.off('respostaCompraGema'); 
    
    socket.on('respostaCompraGema', (dados) => {
        if (dados.sucesso) {
            alert("👑 SUCESSO: " + dados.mensagem);
            // Atualiza a tela de perfil se ela estiver aberta pra mostrar as gemas sumindo
            if (typeof carregarMeuPerfil === 'function') carregarMeuPerfil(); 
        } else {
            alert("❌ ERRO: " + dados.mensagem);
        }
    });
};