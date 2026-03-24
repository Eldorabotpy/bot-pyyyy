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
        const emCooldown = magia.cooldown_atual > 0;
        const corBorda = emCooldown ? "#475569" : "#8b5cf6"; 
        const corTexto = emCooldown ? "#94a3b8" : "#f8fafc";
        const opacidade = emCooldown ? "0.6" : "1";
        const cursor = emCooldown ? "not-allowed" : "pointer";
        const efeitoImagem = emCooldown ? "grayscale(100%)" : "none";
        
        // ADICIONADO: Passando o NOME da magia para ativar a animação correta depois
        const onclickAcao = emCooldown 
            ? `exibirAlertaCustom('Aguarde', 'Esta magia estará pronta em ${magia.cooldown_atual} turno(s)!', false)` 
            : `executarMagiaTurno('${magia.id}', ${magia.custo_mp}, '${magia.nome}')`;

        let infoExtra = `<div style="font-size: 0.7em; color: #93c5fd; margin-top: 2px;">Custo: ${magia.custo_mp} MP</div>`;
        if (emCooldown) {
            infoExtra = `<div style="font-size: 0.75em; color: #f87171; font-weight: bold; margin-top: 2px;">⏳ Espera: ${magia.cooldown_atual}t</div>`;
        }

        // AJUSTE DE CSS: overflow hidden, flex-shrink e max-width limitam o botão no grid!
        return `
        <button class="modern-font modern-btn" 
                style="border: 1px solid #1e293b; border-bottom: 3px solid ${corBorda}; opacity: ${opacidade}; cursor: ${cursor}; display: flex; align-items: center; justify-content: flex-start; gap: 8px; text-align: left; padding: 6px 8px; width: 100%; box-sizing: border-box; overflow: hidden; background: #0f172a;" 
                onclick="${onclickAcao}">
            <span style="font-size: 1.3em; filter: ${efeitoImagem}; flex-shrink: 0;">${magia.icone}</span> 
            <div style="display: flex; flex-direction: column; overflow: hidden; width: 100%;">
                <div style="font-weight: 800; color: ${corTexto}; font-size: 0.8em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%;">${magia.nome}</div>
                ${infoExtra}
            </div>
        </button>
        `;
    }).join('');

    // AJUSTE: O grid-column: span 2 faz o "Voltar" ficar centralizado na base
    htmlMagias += `
        <button class="modern-font modern-btn" style="border: 1px solid #334155; border-bottom: 3px solid #64748b; padding: 10px; grid-column: span 2; background: #1e293b;" onclick="voltarMenuCombate()">
            <span style="font-size: 1.2em; margin-right: 5px;">⬅️</span> <span style="font-weight: 800; color: #f8fafc;">Voltar</span>
        </button>
    `;

    painelBotoes.innerHTML = htmlMagias;
}

// ADICIONADO: O parâmetro magiaNome garante que o combate.js saiba o que animar
function executarMagiaTurno(magiaId, custoMp, magiaNome) {
    voltarMenuCombate();
    executarAcaoTurno('magia', magiaId, magiaNome); 
}

function voltarMenuCombate() {
    const painelBotoes = document.getElementById('menu-botoes');
    if (window.botoesCombateOriginais) {
        painelBotoes.innerHTML = window.botoesCombateOriginais;
    }
}
