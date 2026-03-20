async function carregarMeuPerfil() {
    // 1. Agora o Perfil pega EXATAMENTE o ID salvo no Portal!
    const charId = localStorage.getItem("jogadorEldoraID");

    if (!charId) {
        const msg = document.getElementById('perfil-carregando');
        if(msg) msg.innerHTML = "<span style='color: #e74c3c;'>Nenhum herói selecionado. Feche e abra o portal.</span>";
        return;
    }

    try {
        // 2. Busca no Python usando o ID único do personagem
        const resposta = await fetch(`/perfil/${charId}`);
        const p = await resposta.json();

        if (p.erro) {
            const msg = document.getElementById('perfil-carregando');
            if(msg) msg.innerText = "⚠️ " + p.erro;
            return;
        }

        // 3. Preenche a tela com os dados do personagem correto
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
        if(msg) msg.innerText = "⚠️ Erro ao conectar com os servidores reais.";
    }
}