// ==========================================
// SISTEMA DE MAGIAS E SKILLS - MUNDO DE ELDORA
// ==========================================

async function abrirMenuMagias() {
    const charId = localStorage.getItem("jogadorEldoraID");
    
    // 1. Busca no servidor quais magias o jogador tem EQUIPADAS
    try {
        // Vamos criar essa rota no Python depois!
        const resposta = await fetch(`/api/personagem/${charId}/magias_equipadas`);
        const magias = await resposta.json();

        // 2. Verifica se o jogador tem magias equipadas
        if (!magias || magias.length === 0) {
            exibirAlertaCustom('Grimório Vazio', 'Você não tem nenhuma magia equipada no momento. Vá até o seu Perfil para equipar habilidades!', false);
            return;
        }

        // 3. Se tiver magias, abre o menu para escolher qual usar
        renderizarPainelMagias(magias);

    } catch (erro) {
        console.error("Erro ao buscar magias:", erro);
        exibirAlertaCustom('Erro', 'Ocorreu um distúrbio mágico ao ler seu grimório.', false);
    }
}

function renderizarPainelMagias(magias) {
    const painelBotoes = document.getElementById('menu-botoes');
    
    if (!window.botoesCombateOriginais) {
        window.botoesCombateOriginais = painelBotoes.innerHTML;
    }

    let htmlMagias = magias.map(magia => {
        // Verifica se a magia está em tempo de recarga
        const emCooldown = magia.cooldown_atual > 0;
        
        // Se estiver em cooldown, muda as cores e o bloqueia o clique
        const corBorda = emCooldown ? "#475569" : "#8b5cf6"; // Cinza ou Roxo
        const corTexto = emCooldown ? "#94a3b8" : "#f8fafc";
        const opacidade = emCooldown ? "0.6" : "1";
        const cursor = emCooldown ? "not-allowed" : "pointer";
        const efeitoImagem = emCooldown ? "grayscale(100%)" : "none";
        
        // Define o que o botão faz ao ser clicado
        const onclickAcao = emCooldown 
            ? `exibirAlertaCustom('Aguarde', 'Esta magia estará pronta em ${magia.cooldown_atual} turno(s)!', false)` 
            : `executarMagiaTurno('${magia.id}', ${magia.custo_mp})`;

        // Muda a informação de baixo dependendo se está pronto ou não
        let infoExtra = `<div style="font-size: 0.7em; color: #93c5fd;">Custo: ${magia.custo_mp} MP</div>`;
        if (emCooldown) {
            infoExtra = `<div style="font-size: 0.75em; color: #f87171; font-weight: bold;">⏳ Espera: ${magia.cooldown_atual}t</div>`;
        }

        return `
        <button class="modern-font modern-btn" 
                style="border-bottom: 3px solid ${corBorda}; opacity: ${opacidade}; cursor: ${cursor}; display: flex; align-items: center; justify-content: flex-start; gap: 10px; text-align: left; padding: 10px;" 
                onclick="${onclickAcao}">
            <span style="font-size: 1.5em; filter: ${efeitoImagem};">${magia.icone}</span> 
            <div style="flex: 1;">
                <div style="font-weight: 800; color: ${corTexto}; font-size: 0.9em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${magia.nome}</div>
                ${infoExtra}
            </div>
        </button>
        `;
    }).join('');

    htmlMagias += `
        <button class="modern-font modern-btn" style="border-bottom: 3px solid #64748b; padding: 10px;" onclick="voltarMenuCombate()">
            <span style="font-size: 1.2em;">⬅️</span> <span style="font-weight: 800;">Voltar</span>
        </button>
    `;

    painelBotoes.innerHTML = htmlMagias;
}

function voltarMenuCombate() {
    const painelBotoes = document.getElementById('menu-botoes');
    if (window.botoesCombateOriginais) {
        painelBotoes.innerHTML = window.botoesCombateOriginais;
    }
}

function executarMagiaTurno(magiaId, custoMp) {
    // Esconde o menu de magias e volta pra tela de combate
    voltarMenuCombate();
    
    // AGORA SIM: Dispara a magia lá pro Python!
    executarAcaoTurno('magia', magiaId);
}