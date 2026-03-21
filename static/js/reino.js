// ==========================================
// CONFIGURAÇÃO DO MAPA MÚNDI E PINOS
// ==========================================
const NOMES_REGIOES = {
    "reino_eldora": "Capital do Reino",
    "pradaria_inicial": "Pradaria Inicial",
    "floresta_sombria": "Floresta Sombria",
    "pedreira_granito": "Pedreira de Granito",
    "campos_linho": "Campos de Linho",
    "pico_grifo": "Pico do Grifo",
    "mina_ferro": "Mina de Ferro",
    "forja_abandonada": "Forja Abandonada",
    "pantano_maldito": "Pântano Maldito",
    "deserto_ancestral": "Deserto Ancestral",
    "picos_gelados": "Picos Gelados"
};

const COORDENADAS_MAPA = {
    "reino_eldora": { top: 48, left: 50 },
    "pradaria_inicial": { top: 33, left: 62 },
    "floresta_sombria": { top: 25, left: 82 },
    "pedreira_granito": { top: 45, left: 85 },
    "campos_linho": { top: 58, left: 78 },
    "pico_grifo": { top: 72, left: 75 },
    "mina_ferro": { top: 82, left: 58 },
    "forja_abandonada": { top: 78, left: 35 },
    "pantano_maldito": { top: 60, left: 20 },
    "deserto_ancestral": { top: 32, left: 22 },
    "picos_gelados": { top: 15, left: 50 }
};

const CONEXOES_MAPA = {
    "reino_eldora": ["pradaria_inicial", "pedreira_granito", "forja_abandonada", "deserto_ancestral"],
    "pradaria_inicial": ["reino_eldora", "floresta_sombria", "picos_gelados"],
    "floresta_sombria": ["pradaria_inicial", "pantano_maldito"],
    "pedreira_granito": ["reino_eldora", "campos_linho"],
    "campos_linho": ["pedreira_granito", "pico_grifo"],
    "pico_grifo": ["campos_linho", "mina_ferro"],
    "mina_ferro": ["pico_grifo", "forja_abandonada"],
    "forja_abandonada": ["reino_eldora", "mina_ferro", "pantano_maldito"],
    "pantano_maldito": ["floresta_sombria", "forja_abandonada", "deserto_ancestral"],
    "deserto_ancestral": ["pantano_maldito", "picos_gelados", "reino_eldora"],
    "picos_gelados": ["deserto_ancestral", "pradaria_inicial"]
};

let _intervaloViagem = null;
window.dadosViagemAtual = {};

// ==========================================
// FUNÇÕES DE DIÁLOGOS PERSONALIZADOS (MODALS)
// ==========================================
function exibirAlertaCustom(titulo, mensagem, isSuccess=true) {
    const cor = isSuccess ? '#2ecc71' : '#e74c3c';
    const icone = isSuccess ? '✅' : '❌';
    const modalHtml = `
    <div id="modal-alerta" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 9999; display: flex; justify-content: center; align-items: center; backdrop-filter: blur(4px);">
        <div style="background: #0f172a; border: 2px solid ${cor}; border-radius: 12px; padding: 25px; width: 80%; max-width: 320px; text-align: center; box-shadow: 0 0 25px rgba(${isSuccess ? '46,204,113' : '231,76,60'}, 0.4);">
            <h3 style="color: ${cor}; margin: 0 0 15px 0; font-size: 1.4em;">${icone} ${titulo}</h3>
            <p style="color: #e2e8f0; margin: 0 0 25px 0; font-size: 1.05em;">${mensagem}</p>
            <button onclick="document.getElementById('modal-alerta').remove()" style="width: 100%; padding: 12px; background: ${cor}; border: none; color: white; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 1.1em;">OK</button>
        </div>
    </div>`;
    const m = document.getElementById('modal-alerta');
    if(m) m.remove();
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

function confirmarViagemMapa(destino) {
    const ehVip = window.dadosViagemAtual.vip;
    const nome = NOMES_REGIOES[destino] || destino;
    const msg = ehVip 
        ? `Usar sua viagem VIP instantânea para <b>${nome}</b>?`
        : `Deseja iniciar a viagem para <b>${nome}</b>?<br><span style="font-size:0.85em; color:#94a3b8;">Leva 6 minutos para chegar.</span>`;

    const modalHtml = `
    <div id="modal-viagem" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 9999; display: flex; justify-content: center; align-items: center; backdrop-filter: blur(4px);">
        <div style="background: #0f172a; border: 2px solid #3b82f6; border-radius: 12px; padding: 25px; width: 80%; max-width: 320px; text-align: center; box-shadow: 0 0 25px rgba(59, 130, 246, 0.5);">
            <h3 style="color: #3b82f6; margin: 0 0 15px 0; font-size: 1.4em;">🗺️ Confirmar Destino</h3>
            <p style="color: #e2e8f0; margin: 0 0 25px 0; font-size: 1.05em;">${msg}</p>
            <div style="display: flex; gap: 10px;">
                <button onclick="document.getElementById('modal-viagem').remove()" style="flex: 1; padding: 12px; background: #1e293b; border: 1px solid #334155; color: #cbd5e1; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 1em;">Não</button>
                <button onclick="document.getElementById('modal-viagem').remove(); iniciarViagemServidor('${destino}');" style="flex: 1; padding: 12px; background: linear-gradient(90deg, #2563eb, #1d4ed8); border: none; color: white; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 1em;">Sim, Viajar</button>
            </div>
        </div>
    </div>`;
    
    const m = document.getElementById('modal-viagem');
    if(m) m.remove();
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

// ==========================================
// FUNÇÃO PRINCIPAL: O REINO DINÂMICO
// ==========================================
async function carregarReino() {
    const conteudo = document.getElementById('aba-reino');
    const charId = localStorage.getItem("jogadorEldoraID");

    if (!charId) return;

    conteudo.innerHTML = '<p style="text-align: center; color: #888; padding: 40px;">Viajando pelas terras de Eldora... 🐎</p>';

    try {
        const resposta = await fetch(`/api/personagem/${charId}`);
        const p = await resposta.json();
        
        if (p.erro) {
            conteudo.innerHTML = `<p style="color: #e74c3c; text-align: center; padding: 40px;">${p.erro}</p>`;
            return;
        }

        p.local_atual = p.local_atual || "reino_eldora";
        p.estado = p.estado || { action: "idle" };

        if (p.estado.action === 'travel') {
            abrirMapaEldora();
            return;
        }

        if (p.local_atual === "reino_eldora") {
            renderizarCidade(conteudo, p);
        } else {
            renderizarSelva(conteudo, p);
        }

    } catch (e) {
        conteudo.innerHTML = '<p style="color: red; text-align: center; padding: 40px;">Erro de conexão com os servidores do Reino.</p>';
    }
}

function renderizarCidade(conteudo, p) {
    conteudo.innerHTML = `
        <div class="home-banner" style="border-color: #f39c12; margin-bottom: 15px;">
            <img src="/static/regions/reino_eldora.jpg" onerror="this.src='https://github.com/user-attachments/assets/abdbcb1f-b3ba-4e42-b082-be1a5d839d73'">
        </div>
        
        <div style="text-align: center; margin-bottom: 20px;">
            <h2 style="color: #f8fafc; margin: 0 0 5px 0; font-size: 1.4em;">A Capital</h2>
            <p style="color: #94a3b8; font-size: 0.85em; margin: 0;">O coração econômico e militar do mundo.</p>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px;">
            <button onclick="abrirMapaEldora()" style="background: #1e293b; border: 1px solid #334155; border-bottom: 3px solid #22c55e; padding: 15px; border-radius: 10px; cursor: pointer; display: flex; flex-direction: column; align-items: center; transition: 0.2s;">
                <span style="font-size: 2em; margin-bottom: 5px;">🗺️</span>
                <strong style="color: #f8fafc; font-size: 0.95em;">Viajar / Mapa</strong>
            </button>
            <button onclick="exibirAlertaCustom('Desenvolvimento', 'O Mercado Livre está em construção.', false)" style="background: #1e293b; border: 1px solid #334155; border-bottom: 3px solid #f59e0b; padding: 15px; border-radius: 10px; cursor: pointer; display: flex; flex-direction: column; align-items: center;">
                <span style="font-size: 2em; margin-bottom: 5px;">🏪</span><strong style="color: #f8fafc; font-size: 0.95em;">Mercado Livre</strong>
            </button>
            <button onclick="exibirAlertaCustom('Desenvolvimento', 'A Forja Real será aberta em breve.', false)" style="background: #1e293b; border: 1px solid #334155; border-bottom: 3px solid #64748b; padding: 15px; border-radius: 10px; cursor: pointer; display: flex; flex-direction: column; align-items: center;">
                <span style="font-size: 2em; margin-bottom: 5px;">⚒️</span><strong style="color: #f8fafc; font-size: 0.95em;">Forja Real</strong>
            </button>
            <button onclick="exibirAlertaCustom('Desenvolvimento', 'Arena em manutenção.', false)" style="background: #1e293b; border: 1px solid #334155; border-bottom: 3px solid #ef4444; padding: 15px; border-radius: 10px; cursor: pointer; display: flex; flex-direction: column; align-items: center;">
                <span style="font-size: 2em; margin-bottom: 5px;">⚔️</span><strong style="color: #f8fafc; font-size: 0.95em;">Arena PvP</strong>
            </button>
            <button onclick="exibirAlertaCustom('Desenvolvimento', 'Guildas não liberadas ainda.', false)" style="background: #1e293b; border: 1px solid #334155; border-bottom: 3px solid #eab308; padding: 15px; border-radius: 10px; cursor: pointer; display: flex; flex-direction: column; align-items: center;">
                <span style="font-size: 2em; margin-bottom: 5px;">🏰</span><strong style="color: #f8fafc; font-size: 0.95em;">Guilda</strong>
            </button>
            <button onclick="exibirAlertaCustom('Desenvolvimento', 'Laboratório isolado por risco de explosão.', false)" style="background: #1e293b; border: 1px solid #334155; border-bottom: 3px solid #06b6d4; padding: 15px; border-radius: 10px; cursor: pointer; display: flex; flex-direction: column; align-items: center;">
                <span style="font-size: 2em; margin-bottom: 5px;">🧪</span><strong style="color: #f8fafc; font-size: 0.95em;">Laboratório</strong>
            </button>
        </div>
    `;
}

function renderizarSelva(conteudo, p) {
    const nomeRegiao = NOMES_REGIOES[p.local_atual] || "Terras Selvagens";
    
    conteudo.innerHTML = `
        <div class="home-banner" style="border-color: #2ecc71; margin-bottom: 15px; position: relative;">
            <img src="/static/regions/${p.local_atual}.jpg" onerror="this.src='https://placehold.co/600x300/111/333?text=${nomeRegiao}'" style="width: 100%; display: block; object-fit: cover;">
            <div style="position: absolute; bottom: 0; left: 0; width: 100%; height: 50%; background: linear-gradient(to bottom, transparent, rgba(0,0,0,0.9));"></div>
            <div style="position: absolute; bottom: 10px; left: 15px;">
                <h3 style="color: #fff; margin: 0; font-size: 1.3em; text-shadow: 1px 1px 5px #000;">📍 ${nomeRegiao}</h3>
                <p style="color: #2ecc71; margin: 0; font-size: 0.85em; font-weight: bold; text-shadow: 1px 1px 3px #000;">Área de Exploração</p>
            </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
            <button onclick="exibirAlertaCustom('Bloqueado', 'Caça será liberada no web app em breve!', false)" style="background: linear-gradient(180deg, #1e293b, #0f172a); border: 1px solid #334155; border-bottom: 3px solid #e74c3c; padding: 12px; border-radius: 8px; cursor: pointer; color: white; font-weight: bold; font-size: 1.05em; display: flex; align-items: center; justify-content: center; gap: 8px;">
                <span style="font-size: 1.2em;">⚔️</span> Caçar
            </button>
            <button onclick="exibirAlertaCustom('Bloqueado', 'Calabouço será liberado no web app em breve!', false)" style="background: linear-gradient(180deg, #1e293b, #0f172a); border: 1px solid #334155; border-bottom: 3px solid #9b59b6; padding: 12px; border-radius: 8px; cursor: pointer; color: white; font-weight: bold; font-size: 1.05em; display: flex; align-items: center; justify-content: center; gap: 8px;">
                <span style="font-size: 1.2em;">🏰</span> Calabouço
            </button>
        </div>

        <div style="display: flex; gap: 8px; margin-bottom: 10px;">
            <button onclick="exibirAlertaCustom('Auto-Caça', 'Apenas no bot por enquanto.', false)" style="flex: 1; background: #1e293b; border: 1px solid #334155; border-bottom: 2px solid #3498db; padding: 8px; border-radius: 6px; color: #cbd5e1; font-weight: bold; font-size: 0.9em; cursor: pointer;">⏱️ 10x</button>
            <button onclick="exibirAlertaCustom('Auto-Caça', 'Apenas no bot por enquanto.', false)" style="flex: 1; background: #1e293b; border: 1px solid #334155; border-bottom: 2px solid #3498db; padding: 8px; border-radius: 6px; color: #cbd5e1; font-weight: bold; font-size: 0.9em; cursor: pointer;">⏱️ 25x</button>
            <button onclick="exibirAlertaCustom('Auto-Caça', 'Apenas no bot por enquanto.', false)" style="flex: 1; background: #1e293b; border: 1px solid #334155; border-bottom: 2px solid #3498db; padding: 8px; border-radius: 6px; color: #cbd5e1; font-weight: bold; font-size: 0.9em; cursor: pointer;">⏱️ 35x</button>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px;">
            <button onclick="abrirMapaEldora()" style="background: #1e293b; border: 1px solid #334155; padding: 10px; border-radius: 6px; color: #94a3b8; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 6px; cursor: pointer;">🗺️ Mapa</button>
            <button onclick="exibirAlertaCustom('Info', 'Use a Wiki para obter dados da região.', false)" style="background: #1e293b; border: 1px solid #334155; padding: 10px; border-radius: 6px; color: #94a3b8; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 6px; cursor: pointer;">ℹ️ Info</button>
        </div>
    `;
}

// ==========================================
// FUNÇÃO: ABRIR O MAPA MÚNDI
// ==========================================
async function abrirMapaEldora() {
    const conteudo = document.getElementById('aba-reino');
    const charId = localStorage.getItem("jogadorEldoraID");

    conteudo.innerHTML = '<p style="text-align: center; color: #888; padding: 40px;">Desenhando pergaminho do mapa... 🗺️</p>';

    try {
        const resposta = await fetch(`/api/personagem/${charId}`);
        const p = await resposta.json();
        if (p.erro) return;

        p.local_atual = p.local_atual || "reino_eldora";
        p.tier = p.tier || "free";
        p.estado = p.estado || { action: "idle" };

        let ehVIP = ["lenda", "vip", "premium", "admin"].includes(p.tier);
        window.dadosViagemAtual = { local: p.local_atual, vip: ehVIP };
        
        let infoPainel = '';
        let pinosHtml = '';

        if (p.estado && p.estado.action === 'travel') {
            const dataFim = new Date(p.estado.finish_time);
            infoPainel = `
                <div style="background: #020617; border: 2px solid #ef4444; border-radius: 10px; padding: 15px; text-align: center; margin-bottom: 15px;">
                    <h3 style="color: #ef4444; margin: 0 0 5px 0;">Em Viagem...</h3>
                    <p style="color: #aaa; font-size: 0.9em; margin: 0 0 10px 0;">Destino: <b>${NOMES_REGIOES[p.estado.details.destination]}</b></p>
                    <div style="font-size: 2.5em; color: #f1c40f; font-weight: bold; font-family: monospace;" id="timer-viagem">00:00</div>
                </div>
            `;
            iniciarCronometroViagem(dataFim);

            let coord = COORDENADAS_MAPA[p.estado.details.destination];
            if(coord) pinosHtml += `<div class="map-pin accessible" style="top: ${coord.top}%; left: ${coord.left}%;"></div>`;

        } else {
            let locaisPossiveis = ehVIP ? Object.keys(NOMES_REGIOES).filter(r => r !== p.local_atual) : (CONEXOES_MAPA[p.local_atual] || []);

            for (const regiaoId in COORDENADAS_MAPA) {
                let coord = COORDENADAS_MAPA[regiaoId];
                let classePino = 'map-pin';
                let cliqueAcao = `exibirAlertaCustom('Distante', 'Você não pode viajar para cá agora! Vá para uma região vizinha primeiro.', false)`;

                if (regiaoId === p.local_atual) {
                    classePino += ' current';
                    cliqueAcao = `exibirAlertaCustom('Destino', 'Você já está em ${NOMES_REGIOES[regiaoId]}.', false)`;
                } else if (locaisPossiveis.includes(regiaoId)) {
                    classePino += ' accessible';
                    cliqueAcao = `confirmarViagemMapa('${regiaoId}')`;
                }

                pinosHtml += `<div class="${classePino}" style="top: ${coord.top}%; left: ${coord.left}%;" onclick="${cliqueAcao}"><div class="map-pin-label">${NOMES_REGIOES[regiaoId]}</div></div>`;
            }

            infoPainel = `
                <div style="background: #020617; padding: 12px; border-radius: 10px; margin-bottom: 15px; border: 1px solid #1e293b;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: #94a3b8; font-size: 0.85em;">Local Atual:</span>
                        <strong style="color: #f1c40f;">📍 ${NOMES_REGIOES[p.local_atual] || p.local_atual}</strong>
                    </div>
                    <div style="margin-top: 5px; font-size: 0.8em; color: #aaa;">
                        <span style="display:inline-block; width:10px; height:10px; background:#2ecc71; border-radius:50%; margin-right:5px;"></span> Destinos Disponíveis (${ehVIP ? 'Instântaneo' : '6 min'})<br>
                        <span style="display:inline-block; width:10px; height:10px; background:#e74c3c; border-radius:50%; margin-right:5px;"></span> Bloqueado
                    </div>
                </div>
            `;
        }

        const LINK_IMAGEM_GITHUB = 'https://github.com/user-attachments/assets/0d242135-57d0-4435-9251-d48acbd5deba'; 

        conteudo.innerHTML = `
            ${infoPainel}
            <div class="map-container">
                <img src="${LINK_IMAGEM_GITHUB}" style="width: 100%; display: block;">
                ${pinosHtml}
            </div>
            <button onclick="carregarReino()" style="width: 100%; background: #1a1a1a; padding: 12px; border: 1px solid #333; color: white; border-radius: 8px;">⬅️ Voltar para a Região</button>
        `;

    } catch (e) {
        conteudo.innerHTML = '<p style="color: red; text-align: center;">Erro ao carregar o mapa.</p>';
    }
}

// ==========================================
// FUNÇÃO: INICIAR VIAGEM + SERVIDOR
// ==========================================
async function iniciarViagemServidor(destino) {
    const charId = localStorage.getItem("jogadorEldoraID");
    try {
        const res = await fetch('/api/viajar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: charId, destino: destino })
        });
        const dados = await res.json();
        
        if (dados.erro) { 
            exibirAlertaCustom("Aviso", dados.erro, false); 
            return; 
        }

        if (dados.is_vip) {
            exibirAlertaCustom("Sucesso!", "Chegou ao destino instantaneamente!", true);
            carregarReino(); // Já volta direto pra região com os botões certos
        } else {
            abrirMapaEldora(); 
        }
    } catch(e) {
        exibirAlertaCustom("Erro", "Erro de magia nas rotas.", false);
    }
}

// ==========================================
// FUNÇÃO: CRONÔMETRO DE VIAGEM COM SINCRONIA
// ==========================================
function iniciarCronometroViagem(dataFim) {
    if (_intervaloViagem) clearInterval(_intervaloViagem);
    
    _intervaloViagem = setInterval(() => {
        const elementoTimer = document.getElementById("timer-viagem");
        if(!elementoTimer) { clearInterval(_intervaloViagem); return; } 

        const diffMS = dataFim - new Date();

        if (diffMS <= 0) {
            clearInterval(_intervaloViagem);
            elementoTimer.innerHTML = "Chegou!";
            elementoTimer.style.color = "#2ecc71";
            
            const charId = localStorage.getItem("jogadorEldoraID");
            fetch('/api/finalizar_viagem', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: charId })
            }).then(() => {
                setTimeout(() => carregarReino(), 1500); 
            });
            return;
        }

        const m = Math.floor((diffMS / 1000) / 60).toString().padStart(2, '0');
        const s = Math.floor((diffMS / 1000) % 60).toString().padStart(2, '0');
        elementoTimer.innerHTML = `${m}:${s}`;
    }, 1000);
}