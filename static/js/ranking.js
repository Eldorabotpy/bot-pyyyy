const configBanners = {
    'level': { img: 'banner_level.jpg', desc: 'Os guerreiros com maior nível do servidor.' },
    'ouro': { img: 'banner_ouro.jpg', desc: 'As fortunas mais incalculáveis do reino.' },
    'pvp': { img: 'banner_pvp.jpg', desc: 'Os gladiadores mais letais da arena.' },
    'guildas': { img: 'banner_guildas.jpg', desc: 'A glória das maiores ordens unidas.' }
};

function voltarParaMenuRanking() {
    document.getElementById('container-menu-ranking').style.display = 'block';
    document.getElementById('conteudo-ranking').style.display = 'none';
}

async function abrirTabelaRanking(tipoEndpoint, titulo) {
    document.getElementById('container-menu-ranking').style.display = 'none';
    document.getElementById('conteudo-ranking').style.display = 'block';
    const info = configBanners[tipoEndpoint];
    
    document.getElementById('img-banner-ranking').src = `/static/rankings/${info.img}`;
    document.getElementById('titulo-tabela-ranking').innerText = titulo;
    document.getElementById('desc-tabela-ranking').innerText = info.desc;
    
    const tabela = document.getElementById('corpo-tabela-ranking');
    tabela.innerHTML = '<tr><td colspan="3" style="text-align:center; color: #888; padding: 30px;">Consultando oráculos... 🔮</td></tr>';

    try {
        const resposta = await fetch(`/ranking/${tipoEndpoint}`);
        const dados = await resposta.json();
        tabela.innerHTML = ''; 
        dados.forEach((linha, index) => {
            let posicao = index + 1;
            let classeLinha = 'rank-row';
            if (posicao === 1) classeLinha += ' rank-1';
            else if (posicao === 2) classeLinha += ' rank-2';
            else if (posicao === 3) classeLinha += ' rank-3';

            tabela.innerHTML += `<tr class="${classeLinha}"><td style="font-weight: 800; width: 15%; text-align: center;">#${posicao}</td><td>${linha.nome}</td><td style="text-align: right;">${linha.valor}</td></tr>`;
        });
    } catch (erro) {
        tabela.innerHTML = `<tr><td colspan="3" style="color: red; text-align: center;">Erro de conexão. O servidor pode estar reiniciando.</td></tr>`;
    }
}