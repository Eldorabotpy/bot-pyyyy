window.Telegram.WebApp.ready();
window.Telegram.WebApp.expand();

function mudarAba(nomeDaAba) {
    document.querySelectorAll('.tab-content').forEach(aba => aba.classList.remove('active'));
    document.querySelectorAll('nav button').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`aba-${nomeDaAba}`).classList.add('active');
    document.getElementById(`btn-${nomeDaAba}`).classList.add('active');
    
    // Agora ele sabe carregar o Início também!
    if(nomeDaAba === 'home') carregarInicio();
    if(nomeDaAba === 'perfil') carregarMeuPerfil();
    if(nomeDaAba === 'ranking') voltarParaMenuRanking();
}

async function carregarInicio() {
    const conteudo = document.getElementById('aba-home'); // Pega a aba inteira para desenhar por cima
    
    // Pega o ID que salvamos lá na tela de login!
    const charId = localStorage.getItem("jogadorEldoraID");

    if (!charId) {
        conteudo.innerHTML = `
        <div style="text-align: center; padding: 40px 20px;">
            <h3 style="color: #e74c3c;">Nenhum Herói Selecionado</h3>
            <p style="color: #aaa;">Volte para o portal e escolha seu personagem.</p>
        </div>`;
        return;
    }

    conteudo.innerHTML = '<p style="text-align: center; color: #888; padding: 30px;">Sincronizando com os deuses de Eldora... ⏳</p>';

    try {
        // Vai lá no seu Python e pega a ficha criminal do jogador!
        const resposta = await fetch(`/api/personagem/${charId}`);
        const p = await resposta.json();

        if (p.erro) {
            conteudo.innerHTML = `<p style="color: #e74c3c; text-align: center; padding: 30px;">Erro: ${p.erro}</p>`;
            return;
        }

        // O NOVO VISUAL DA TELA INICIAL
        let html = `
        <div class="home-banner">
            <img src="/static/capa_eldora.jpg" onerror="this.src='https://placehold.co/600x300/111/333?text=Eldora'">
        </div>

        <div style="background: linear-gradient(145deg, #1e293b, #0f172a); border: 2px solid #f39c12; border-radius: 10px; padding: 15px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(243, 156, 18, 0.2);">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 10px; margin-bottom: 10px;">
                <h3 style="margin: 0; color: #f39c12; font-size: 1.3em;">🛡️ ${p.nome}</h3>
                <span style="background: #2563eb; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold;">Nv. ${p.level}</span>
            </div>
            
            <p style="margin: 0 0 15px 0; color: #cbd5e1; font-size: 0.95em;">⚔️ Classe: <b>${p.classe}</b></p>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px;">
                <div style="background: #020617; padding: 8px; border-radius: 6px; border-left: 3px solid #e74c3c; font-size: 0.85em;">
                    <span style="color: #94a3b8; font-weight: bold;">❤️ Vida</span><br>
                    <strong style="color: #f87171; font-size: 1.1em;">${p.hp} / ${p.max_hp}</strong>
                </div>
                <div style="background: #020617; padding: 8px; border-radius: 6px; border-left: 3px solid #3b82f6; font-size: 0.85em;">
                    <span style="color: #94a3b8; font-weight: bold;">💧 Mana</span><br>
                    <strong style="color: #60a5fa; font-size: 1.1em;">${p.mp} / ${p.max_mp}</strong>
                </div>
            </div>

            <div style="display: flex; gap: 10px; justify-content: space-around; background: #000; padding: 10px; border-radius: 8px; border: 1px solid #333;">
                <span style="color: #f1c40f; font-weight: bold; font-size: 1.1em;">💰 ${p.ouro}</span>
                <span style="color: #38bdf8; font-weight: bold; font-size: 1.1em;">💎 ${p.diamantes}</span>
            </div>
        </div>

        <div style="display: flex; flex-direction: column; gap: 10px;">
            <button class="game-menu-btn" onclick="mudarAba('ranking')">
                <div class="btn-icon">🏆</div><div class="btn-text"><span class="btn-title">Ranking Global</span><span class="btn-subtitle">Veja quem lidera a supremacia</span></div><div class="btn-arrow">➔</div>
            </button>
            <button class="game-menu-btn" onclick="mudarAba('wiki')">
                <div class="btn-icon">📖</div><div class="btn-text"><span class="btn-title">Enciclopédia</span><span class="btn-subtitle">Classes, Regiões e Monstros</span></div><div class="btn-arrow">➔</div>
            </button>
            <button class="game-menu-btn" onclick="mudarAba('perfil')">
                <div class="btn-icon">👤</div><div class="btn-text"><span class="btn-title">Meu Perfil</span><span class="btn-subtitle">Acesse seu status e inventário</span></div><div class="btn-arrow">➔</div>
            </button>
        </div>
        `;
        
        conteudo.innerHTML = html;

    } catch (erro) {
        conteudo.innerHTML = '<p style="color: red; text-align: center; padding: 30px;">Ocorreu um distúrbio na magia. Não foi possível carregar o reino.</p>';
    }
}

// Roda a mágica da tela inicial assim que o site abrir!
carregarInicio();