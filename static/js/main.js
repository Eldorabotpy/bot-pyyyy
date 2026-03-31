window.Telegram.WebApp.ready();
window.Telegram.WebApp.expand();

function mudarAba(nomeDaAba) {
    document.querySelectorAll('.tab-content').forEach(aba => aba.classList.remove('active'));
    document.querySelectorAll('nav button').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`aba-${nomeDaAba}`).classList.add('active');
    document.getElementById(`btn-${nomeDaAba}`).classList.add('active');
    
    if(nomeDaAba === 'home') carregarInicio();
    if(nomeDaAba === 'reino') carregarReino();
    if(nomeDaAba === 'perfil') carregarMeuPerfil();
    if(nomeDaAba === 'ranking') voltarParaMenuRanking();
}

async function carregarInicio() {
    const conteudo = document.getElementById('aba-home'); 
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

        let tickerHtml = '';
        try {
            const resPremium = await fetch('/api/recent_premium');
            const premiums = await resPremium.json();
            
            if (premiums.length > 0) {
                let frases = premiums.map(jog => 
                    `✨ O jogador <span style="color: #f1c40f; font-weight: 900; text-transform: uppercase; letter-spacing: 1px; text-shadow: 0 0 8px #f1c40f;">${jog.nome}</span> ativou o plano <span style="color: #00f2fe; font-weight: 900; text-transform: uppercase; text-shadow: 0 0 8px #00f2fe;">${jog.tier}</span> e sua jornada agora será épica!`
                ).join(' &nbsp;&nbsp;&nbsp;🌟&nbsp;&nbsp;&nbsp; ');
                
                tickerHtml = `
                <div class="premium-ticker-container">
                    <div class="premium-ticker-text">${frases}</div>
                </div>`;
            }
        } catch(e) { }

let html = `
        <div class="home-banner">
            <img src="/static/capa_eldora.jpg" onerror="this.src='https://placehold.co/600x200/111/333?text=Eldora'">
        </div>

        ${tickerHtml}

        <div style="background: #0f172a; border: 1px solid #1e293b; border-top: 3px solid #f39c12; border-radius: 12px; padding: 18px; margin-bottom: 25px; box-shadow: 0 8px 20px rgba(0,0,0,0.6); position: relative;">
            
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 12px; margin-bottom: 12px;">
                <h3 style="margin: 0; color: #f8fafc; font-size: 1.3em; display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 1.1em; filter: drop-shadow(0 0 5px rgba(243,156,18,0.5));">🛡️</span> ${p.nome}
                </h3>
                <span style="background: linear-gradient(90deg, #2563eb, #1d4ed8); color: white; padding: 4px 10px; border-radius: 20px; font-size: 0.75em; font-weight: bold; letter-spacing: 0.5px; box-shadow: 0 2px 5px rgba(37,99,235,0.4);">Lv. ${p.level}</span>
            </div>
            
            <p style="margin: 0 0 18px 0; color: #94a3b8; font-size: 0.9em; display: flex; align-items: center; gap: 6px;">
                ⚔️ Classe: <span style="color: #cbd5e1; font-weight: 500;">${p.classe ? p.classe.replace(/_/g, ' ') : 'Aventureiro'}</span>
            </p>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 18px;">
                <div style="background: #020617; padding: 10px; border-radius: 8px; border-left: 3px solid #ef4444; position: relative; overflow: hidden;">
                    <span style="color: #64748b; font-size: 0.75em; font-weight: bold; text-transform: uppercase;">Vida</span><br>
                    <strong style="color: #fca5a5; font-size: 1.1em; text-shadow: 0 0 8px rgba(239,68,68,0.3);">${p.hp} <span style="font-size: 0.8em; color: #7f1d1d;">/ ${p.max_hp}</span></strong>
                </div>
                <div style="background: #020617; padding: 10px; border-radius: 8px; border-left: 3px solid #3b82f6; position: relative; overflow: hidden;">
                    <span style="color: #64748b; font-size: 0.75em; font-weight: bold; text-transform: uppercase;">Mana</span><br>
                    <strong style="color: #93c5fd; font-size: 1.1em; text-shadow: 0 0 8px rgba(59,130,246,0.3);">${p.mp} <span style="font-size: 0.8em; color: #1e3a8a;">/ ${p.max_mp}</span></strong>
                </div>
            </div>

            <div style="display: flex; justify-content: space-around; background: #020617; padding: 12px; border-radius: 8px; border: 1px solid #1e293b;">
                <span style="color: #f1c40f; font-weight: bold; font-size: 1.05em; display: flex; align-items: center; gap: 5px;">💰 ${p.ouro.toLocaleString('pt-BR')}</span>
                <span style="width: 1px; background: #334155;"></span>
                <span style="color: #38bdf8; font-weight: bold; font-size: 1.05em; display: flex; align-items: center; gap: 5px;">💎 ${p.diamantes.toLocaleString('pt-BR')}</span>
            </div>
        </div>

        <div style="background: #0f172a; border: 1px solid #1e293b; border-top: 3px solid #ef4444; border-radius: 12px; padding: 18px; margin-bottom: 25px; box-shadow: 0 8px 20px rgba(0,0,0,0.6); position: relative;">
            
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 12px; margin-bottom: 12px;">
                <h3 style="margin: 0; color: #f8fafc; font-size: 1.2em; display: flex; align-items: center; gap: 8px; text-transform: uppercase; letter-spacing: 1px;">
                    <span style="font-size: 1.1em; filter: drop-shadow(0 0 5px rgba(239,68,68,0.5));">🔥</span> Eventos em Ação
                </h3>
                <span style="background: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; color: #ef4444; padding: 4px 10px; border-radius: 20px; font-size: 0.70em; font-weight: bold; letter-spacing: 1px; animation: blinker 1.5s linear infinite;">AO VIVO</span>
            </div>
            
            <div style="background: #020617; padding: 12px; border-radius: 8px; border-left: 3px solid #f59e0b; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong style="color: #f1c40f; font-size: 1em; display: block; margin-bottom: 4px;">🛡️ Defesa do Reino</strong>
                    <span style="color: #94a3b8; font-size: 0.8em;">Invasão nos portões!</span>
                </div>
                <div style="text-align: right;">
                    <span style="color: #ef4444; font-size: 0.75em; font-weight: bold; display: block; margin-bottom: 6px;">Termina em 25m</span>
                    <button onclick="exibirAlertaCustom('Aviso', 'Aba de Eventos em Breve!', false)" style="background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%); color: #f8fafc; border: 1px solid #334155; padding: 6px 12px; border-radius: 6px; font-size: 0.75em; cursor: pointer; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">ENTRAR ⚔️</button>
                </div>
            </div>

            <div style="background: #020617; padding: 12px; border-radius: 8px; border-left: 3px solid #8b5cf6; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong style="color: #a78bfa; font-size: 1em; display: block; margin-bottom: 4px;">👹 World Boss</strong>
                    <span style="color: #94a3b8; font-size: 0.8em;">O monstro despertou!</span>
                </div>
                <div style="text-align: right;">
                    <span style="color: #ef4444; font-size: 0.75em; font-weight: bold; display: block; margin-bottom: 6px;">Termina em 50m</span>
                    <button onclick="exibirAlertaCustom('Aviso', 'Aba do Boss em Breve!', false)" style="background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%); color: #f8fafc; border: 1px solid #334155; padding: 6px 12px; border-radius: 6px; font-size: 0.75em; cursor: pointer; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">ATACAR ⚔️</button>
                </div>
            </div>

        </div>
        `;
        
        conteudo.innerHTML = html;

    } catch (erro) {
        conteudo.innerHTML = '<p style="color: red; text-align: center; padding: 30px;">Ocorreu um distúrbio na magia. Não foi possível carregar o reino.</p>';
    }
}

// ==========================================
// FUNÇÃO PARA COLETAR TICKETS DE EVENTOS
// ==========================================
async function coletarTicketsEvento() {
    const charId = localStorage.getItem("jogadorEldoraID");
    
    // Mostra um alertinha de carregamento (opcional, mas legal)
    exibirAlertaCustom("Aguarde...", "Canalizando energia dos deuses de Eldora... ⏳", false);

    try {
        const res = await fetch('/api/coletar_entradas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: charId })
        });
        
        const dados = await res.json();

        if (dados.sucesso) {
            // Mostra o que ele ganhou!
            exibirAlertaCustom("Sucesso!", dados.mensagem, true);
            
            // 🔥 O PULO DO GATO: Recarrega a tela de Início para o botão 
            // mudar automaticamente de "COLETAR" para "ENTRAR"!
            carregarInicio(); 
        } else {
            exibirAlertaCustom("Aviso", dados.erro, false);
        }
    } catch(e) {
        exibirAlertaCustom("Erro", "A conexão com os deuses falhou.", false);
    }
}

function sairDoJogo() {
    if(confirm("Tem certeza que deseja fechar o grimório e trocar de personagem?")) {
        localStorage.removeItem("jogadorEldoraID");
        localStorage.removeItem("jogadorEldoraNome");
        window.location.href = "/login";
    }
}

carregarInicio();