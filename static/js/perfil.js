async function carregarMeuPerfil() {
    const urlParams = new URLSearchParams(window.location.search);
    let userId = urlParams.get('char_id');

    if (!userId) {
        const user = window.Telegram.WebApp.initDataUnsafe?.user;
        userId = user ? user.id : '6952fb3566c4a0938686b8da'; 
    }

    try {
        const resposta = await fetch(`/perfil/${userId}`);
        const p = await resposta.json();

        if (p.erro) {
            const msg = document.getElementById('perfil-carregando');
            if(msg) msg.innerText = "⚠️ " + p.erro;
            return;
        }

        document.getElementById('perf-nome').innerText = p.nome;
        document.getElementById('perf-classe').innerText = p.classe.replace(/_/g, ' ');
        document.getElementById('perf-lvl').innerText = p.level;
        document.getElementById('perf-ouro').innerText = p.gold.toLocaleString('pt-BR');
        document.getElementById('perf-gems').innerText = p.gems.toLocaleString('pt-BR');
        document.getElementById('perf-hp-texto').innerText = `${p.hp_atual} / ${p.hp_max}`;
        document.getElementById('perf-energia').innerText = p.energy;
        document.getElementById('perf-pontos').innerText = p.pontos_livres;

        const xpAtual = p.xp;
        const xpMaximo = p.xp_max; 
        let percentagem = (xpAtual / xpMaximo) * 100;
        if (percentagem > 100) percentagem = 100;

        document.getElementById('perf-xp-barra').style.width = percentagem + "%";
        document.getElementById('perf-xp-texto').innerText = `${xpAtual.toLocaleString('pt-BR')} / ${xpMaximo.toLocaleString('pt-BR')}`;
        document.getElementById('perf-avatar').src = p.avatar;

        document.getElementById('perfil-carregando').style.display = 'none';
        document.getElementById('perfil-dados').style.display = 'block';

    } catch (erro) {
        const msg = document.getElementById('perfil-carregando');
        if(msg) msg.innerText = "⚠️ Erro ao conectar com o servidor.";
    }
}