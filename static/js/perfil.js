async function carregarMeuPerfil() {
    const charId = localStorage.getItem("jogadorEldoraID");

    if (!charId) {
        const msg = document.getElementById('perfil-msg-carregando');
        if(msg) msg.innerHTML = "<span style='color: #e74c3c;'>Nenhum herói selecionado. Volte ao portal.</span>";
        return;
    }

    try {
        const resposta = await fetch(`/perfil/${charId}`);
        const p = await resposta.json();

        if (p.erro) {
            const msg = document.getElementById('perfil-msg-carregando');
            if(msg) msg.innerText = "⚠️ " + p.erro;
            return;
        }

        // ==========================================
        // PROTEÇÃO CONTRA DADOS NULOS DO BANCO
        // ==========================================
        const nome = p.nome || "Aventureiro";
        const classe = p.classe || "Aprendiz";
        const avatar = p.avatar || "https://placehold.co/100x100/111/f39c12?text=?";

        // Preenche a tela
        document.getElementById('perf-nome').innerText = nome;
        document.getElementById('perf-classe').innerText = classe.replace(/_/g, ' ');
        document.getElementById('perf-lvl').innerText = p.level || 1;
        
        document.getElementById('perf-ouro').innerText = (p.gold || 0).toLocaleString('pt-BR');
        document.getElementById('perf-gems').innerText = (p.gems || 0).toLocaleString('pt-BR');
        
        document.getElementById('perf-hp-texto').innerText = `${p.hp_atual || 0} / ${p.hp_max || 0}`;
        document.getElementById('perf-energia').innerText = p.energy || 0;
        document.getElementById('perf-pontos').innerText = p.pontos_livres || 0;

        const xpAtual = p.xp || 0;
        const xpMaximo = p.xp_max || 1; 
        let percentagem = (xpAtual / xpMaximo) * 100;
        if (percentagem > 100) percentagem = 100;

        document.getElementById('perf-xp-barra').style.width = percentagem + "%";
        document.getElementById('perf-xp-texto').innerText = `${xpAtual.toLocaleString('pt-BR')} / ${xpMaximo.toLocaleString('pt-BR')}`;
        document.getElementById('perf-avatar').src = avatar;

        // Esconde o "Carregando" e mostra o cartão do perfil
        document.getElementById('perfil-carregando').style.display = 'none';
        document.getElementById('perfil-dados').style.display = 'block';

    } catch (erro) {
        console.error("Erro na aba perfil:", erro);
        const msg = document.getElementById('perfil-msg-carregando');
        if (msg) msg.innerText = "⚠️ Erro ao conjurar o feitiço do perfil. Tente novamente.";
    }
}