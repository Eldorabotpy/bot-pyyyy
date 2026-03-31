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

        // 👇 A MÁGICA ENTRA AQUI! BUSCANDO EVENTOS DO PYTHON 👇
        let htmlEventos = '';
        try {
            const resEventos = await fetch(`/api/eventos_ativos/${charId}`);
            const eventosAtivos = await resEventos.json();

            // SÓ MONTA O PAINEL SE TIVER EVENTO ROLANDO!
            if (eventosAtivos.length > 0) {
                let linhasEventos = eventosAtivos.map(evento => `
                    <div style="background: #020617; padding: 12px; border-radius: 8px; border-left: 3px solid ${evento.cor}; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong style="color: ${evento.cor}; font-size: 1em; display: block; margin-bottom: 4px;">${evento.nome}</strong>
                            <span style="color: #94a3b8; font-size: 0.8em;">${evento.descricao}</span>
                        </div>
                        <div style="text-align: right;">
                            <span style="color: #ef4444; font-size: 0.75em; font-weight: bold; display: block; margin-bottom: 6px;">${evento.tempo_texto}</span>
                            <button onclick="${evento.funcao_click}" style="${evento.btn_estilo} color: #f8fafc; border-width: 1px; border-style: solid; padding: 6px 12px; border-radius: 6px; font-size: 0.75em; cursor: pointer; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.3); transition: all 0.2s;">
                                ${evento.botao_texto}
                            </button>
                        </div>
                    </div>
                `).join('');

                htmlEventos = `
                <div style="background: #0f172a; border: 1px solid #1e293b; border-top: 3px solid #ef4444; border-radius: 12px; padding: 18px; margin-bottom: 25px; box-shadow: 0 8px 20px rgba(0,0,0,0.6); position: relative;">
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 12px; margin-bottom: 12px;">
                        <h3 style="margin: 0; color: #f8fafc; font-size: 1.2em; display: flex; align-items: center; gap: 8px; text-transform: uppercase; letter-spacing: 1px;">
                            <span style="font-size: 1.1em; filter: drop-shadow(0 0 5px rgba(239,68,68,0.5));">🔥</span> Eventos em Ação
                        </h3>
                        <span style="background: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; color: #ef4444; padding: 4px 10px; border-radius: 20px; font-size: 0.70em; font-weight: bold; letter-spacing: 1px; animation: blinker 1.5s linear infinite;">AO VIVO</span>
                    </div>
                    ${linhasEventos}
                </div>
                `;
            }
        } catch(e) {
            console.log("Erro ao buscar eventos ou nenhum ativo.");
        }
        // 👆 FIM DA MÁGICA DOS EVENTOS 👆

        let html = `
        <div class="home-banner">
            <img src="/static/capa_eldora.jpg" onerror="this.src='https://placehold.co/600x200/111/333?text=Eldora'">
        </div>

        ${tickerHtml}

        ${htmlEventos} <div style="background: #0f172a; border: 1px solid #1e293b; border-top: 3px solid #f39c12; border-radius: 12px; padding: 18px; margin-bottom: 25px; box-shadow: 0 8px 20px rgba(0,0,0,0.6); position: relative;">
            
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
        `;
        
        conteudo.innerHTML = html;

    } catch (erro) {
        conteudo.innerHTML = '<p style="color: red; text-align: center; padding: 30px;">Ocorreu um distúrbio na magia. Não foi possível carregar o reino.</p>';
    }
}

// ==========================================
// FUNÇÃO EXCLUSIVA DA ARENA DE DEFESA
// ==========================================
async function abrirArenaDefesa() {
    const charId = localStorage.getItem("jogadorEldoraID");
    if (!charId) return;

    // Força o site a mudar visualmente para a aba do reino 
    // (para não sobrepor a tela inicial)
    document.querySelectorAll('.tab-content').forEach(aba => aba.classList.remove('active'));
    document.querySelectorAll('nav button').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`aba-reino`).classList.add('active');
    document.getElementById(`btn-reino`).classList.add('active');

    const conteudo = document.getElementById('aba-reino');

    // Tela de loading imersiva
    conteudo.innerHTML = '<p style="text-align: center; color: #888; padding: 40px; font-size: 1.1em;">Viajando para os portões da Arena... 🏰⏳</p>';

    try {
        const res = await fetch('/api/defesa_reino/iniciar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: charId })
        });

        const dados = await res.json();

        // Se der erro de ticket ou evento fechado
        if (dados.erro) {
            conteudo.innerHTML = `
            <div style="text-align: center; padding: 50px 20px;">
                <h3 style="color: #ef4444; font-size: 1.5em; margin-bottom: 10px;">🛡️ Portões Fechados</h3>
                <p style="color: #94a3b8; font-size: 1.1em;">${dados.erro}</p>
                <button onclick="carregarReino()" style="margin-top: 20px; padding: 12px 25px; background: #334155; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; transition: 0.2s;">Voltar para o Centro do Reino</button>
            </div>`;
            return;
        }

        // Se a arena atingiu o limite (max_concurrent_fighters)
        if (dados.status === "waiting") {
             conteudo.innerHTML = `
            <div style="text-align: center; padding: 40px;">
                <h3 style="color: #f59e0b; font-size: 1.4em;">⛺ Fila de Reforços</h3>
                <p style="color: #94a3b8; white-space: pre-wrap; margin: 20px 0;">${dados.fila}</p>
                <button onclick="carregarReino()" style="padding: 12px 25px; background: linear-gradient(180deg, #2563eb 0%, #1e40af 100%); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">🔄 Atualizar Fila</button>
            </div>`;
            return;
        }

        // Se entrou na batalha com sucesso
        if (dados.status === "active") {
            const ehChefeHtml = dados.is_boss ? '<h3 style="color: #ef4444; text-align: center; animation: blinker 1.5s linear infinite; margin-top: -10px; margin-bottom: 20px;">🚨 CHEFE DA INVASÃO APARECEU 🚨</h3>' : '';

            conteudo.innerHTML = `
            <div style="background: #0f172a; padding: 25px; border-radius: 12px; border: 1px solid #1e293b; box-shadow: 0 10px 25px rgba(0,0,0,0.8);">
                <h2 style="color: #f8fafc; text-align: center; margin-top: 0; letter-spacing: 2px;">🌊 ONDA ${dados.wave} 🌊</h2>
                ${ehChefeHtml}

                <div style="display: flex; justify-content: space-between; align-items: center; margin: 20px 0; background: #020617; padding: 15px; border-radius: 10px; border: 1px solid #334155;">
                    <div style="text-align: center; width: 40%;">
                        <h4 style="color: #38bdf8; margin: 0 0 10px 0; font-size: 1.1em;">Você</h4>
                        <div style="color: #fca5a5; font-weight: bold; margin-bottom: 5px;">❤️ HP: ${dados.player_hp} / ${dados.player_max_hp}</div>
                        <div style="color: #93c5fd; font-weight: bold;">💙 MP: ${dados.player_mp} / ${dados.player_max_mp}</div>
                    </div>

                    <div style="font-size: 1.6em; font-weight: 900; color: #475569; text-shadow: 0 2px 4px rgba(0,0,0,0.5);">VS</div>

                    <div style="text-align: center; width: 40%;">
                        <h4 style="color: #ef4444; margin: 0 0 10px 0; font-size: 1.1em;">${dados.mob_nome}</h4>
                        <div style="color: #fca5a5; font-weight: bold;">❤️ HP: ${dados.mob_hp.toLocaleString('pt-BR')} / ${dados.mob_max_hp.toLocaleString('pt-BR')}</div>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 25px;">
                    <button id="btn-atacar-reino" onclick="alert('Implementaremos o Ataque na Fase 2!')" style="background: linear-gradient(180deg, #dc2626 0%, #991b1b 100%); color: white; border: 1px solid #ef4444; padding: 14px; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 1.1em; transition: 0.2s;">💥 ATACAR</button>
                    <button onclick="alert('Implementaremos as Magias na Fase 2!')" style="background: linear-gradient(180deg, #2563eb 0%, #1e40af 100%); color: white; border: 1px solid #3b82f6; padding: 14px; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 1.1em; transition: 0.2s;">✨ MAGIAS</button>
                </div>

                <div id="log-defesa" style="background: #020617; padding: 15px; border-radius: 8px; margin-top: 25px; font-family: monospace; color: #a3e635; height: 120px; overflow-y: auto; border-left: 3px solid #65a30d;">
                    > O campo de batalha está um caos!<br>> O que você vai fazer?
                </div>
            </div>
            `;
        }

    } catch (erro) {
        console.error("Erro no Carregar Reino:", erro);
        conteudo.innerHTML = '<p style="color: #ef4444; text-align: center; padding: 30px;">Ocorreu um erro ao conectar com o campo de batalha. Verifique o console.</p>';
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