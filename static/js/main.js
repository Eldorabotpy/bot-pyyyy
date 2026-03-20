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
    const conteudo = document.getElementById('aba-home'); 
    
    // Pega o ID salvo no login
    const charId = localStorage.getItem("jogadorEldoraID");

    if (!charId) {
        conteudo.innerHTML = `
        <div style="text-align: center; padding: 60px 20px;">
            <h2 style="color: #e74c3c; margin-bottom: 10px;">Nenhum Herói Selecionado</h2>
            <p style="color: #aaa; margin-bottom: 30px;">Os portões do reino estão fechados. Por favor, identifique-se no portal mágico.</p>
            <button onclick="window.location.href='/login'" style="background: linear-gradient(180deg, #f1c40f 0%, #d35400 100%); border: 2px solid #f39c12; padding: 12px 25px; border-radius: 8px; color: black; font-weight: bold; font-size: 1.1em; cursor: pointer;">Ir para o Portal de Login</button>
        </div>`;
        return;
    }

    conteudo.innerHTML = '<p style="text-align: center; color: #888; padding: 30px;">Sincronizando com os deuses de Eldora... ⏳</p>';

    try {
        const resposta = await fetch(`/api/personagem/${charId}`);
        const p = await resposta.json();

        if (p.erro) {
            conteudo.innerHTML = `<p style="color: #e74c3c; text-align: center; padding: 30px;">Erro: ${p.erro}</p>`;
            return;
        }

        // VISUAL DA TELA INICIAL
        let html = `
        <div class="home-banner">
            <img src="/static/capa_eldora.jpg" onerror="this.src='https://placehold.co/600x200/111/333?text=Eldora'">
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

        <h4 style="color: #aaa; border-bottom: 1px solid #333; padding-bottom: 5px; margin-bottom: 10px; font-weight: normal;">Ações do Reino</h4>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px;">
            
            <button onclick="alert('Sistema de Combate em desenvolvimento! ⚔️')" style="background: linear-gradient(135deg, #2c3e50, #1a252f); border: 1px solid #3498db; padding: 15px; border-radius: 8px; cursor: pointer; display: flex; flex-direction: column; align-items: center; transition: 0.2s;">
                <span style="font-size: 1.8em; margin-bottom: 5px; filter: drop-shadow(0 2px 2px rgba(0,0,0,0.5));">⚔️</span>
                <strong style="color: #3498db; font-size: 1em;">Caçar</strong>
            </button>
            
            <button onclick="alert('Os portões do evento se abrirão em breve! 🎪')" style="background: linear-gradient(135deg, #8e44ad, #5e3370); border: 1px solid #9b59b6; padding: 15px; border-radius: 8px; cursor: pointer; display: flex; flex-direction: column; align-items: center; transition: 0.2s;">
                <span style="font-size: 1.8em; margin-bottom: 5px; filter: drop-shadow(0 2px 2px rgba(0,0,0,0.5));">🎪</span>
                <strong style="color: #9b59b6; font-size: 1em;">Eventos</strong>
            </button>
            
            <button onclick="alert('As caravanas mercantes estão a caminho! 🏪')" style="background: linear-gradient(135deg, #d35400, #a04000); border: 1px solid #e67e22; padding: 15px; border-radius: 8px; cursor: pointer; display: flex; flex-direction: column; align-items: center; transition: 0.2s;">
                <span style="font-size: 1.8em; margin-bottom: 5px; filter: drop-shadow(0 2px 2px rgba(0,0,0,0.5));">🏪</span>
                <strong style="color: #e67e22; font-size: 1em;">Mercado</strong>
            </button>
            
            <button onclick="alert('O calor da forja ainda está fraco... 🔥')" style="background: linear-gradient(135deg, #7f8c8d, #34495e); border: 1px solid #95a5a6; padding: 15px; border-radius: 8px; cursor: pointer; display: flex; flex-direction: column; align-items: center; transition: 0.2s;">
                <span style="font-size: 1.8em; margin-bottom: 5px; filter: drop-shadow(0 2px 2px rgba(0,0,0,0.5));">🔨</span>
                <strong style="color: #95a5a6; font-size: 1em;">Forja</strong>
            </button>

        </div>
        `;
        
        conteudo.innerHTML = html;

    } catch (erro) {
        conteudo.innerHTML = '<p style="color: red; text-align: center; padding: 30px;">Ocorreu um distúrbio na magia. Não foi possível carregar o reino.</p>';
    }
}

// ==========================================
// FUNÇÃO DE SAIR / TROCAR PERSONAGEM
// ==========================================
function sairDoJogo() {
    // Confirma se o jogador quer mesmo sair
    if(confirm("Tem certeza que deseja fechar o grimório e trocar de personagem?")) {
        // Apaga a memória do navegador
        localStorage.removeItem("jogadorEldoraID");
        localStorage.removeItem("jogadorEldoraNome");
        
        // Manda de volta para o Portal do Mago
        window.location.href = "/login";
    }
}

// Roda a mágica da tela inicial assim que o site abrir!
carregarInicio();