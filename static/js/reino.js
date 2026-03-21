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

// 👇 AQUI VOCÊ COLA OS LINKS DO GITHUB DE CADA IMAGEM QUADRADA 👇
const IMAGENS_DAS_REGIOES = {
    "reino_eldora": "https://github.com/user-attachments/assets/a9d487d1-8d12-4dcf-8681-0c7fd4ef8d98",
    "pradaria_inicial": "https://github.com/user-attachments/assets/04217592-0102-4e08-ae26-99a4d6aca905",
    "floresta_sombria": "https://github.com/user-attachments/assets/70a315c5-15c2-4277-af98-1ee79c7dc5a8", // Exemplo com a sua imagem da floresta!
    "pedreira_granito": "https://github.com/user-attachments/assets/76e836d2-3a23-4564-9810-678408c520b9",
    "campos_linho": "https://github.com/user-attachments/assets/24ced0e5-ab12-4a60-9962-c7efed362de5",
    "pico_grifo": "https://github.com/user-attachments/assets/1978a416-381b-4dda-a819-bd3eaf23c894",
    "mina_ferro": "https://github.com/user-attachments/assets/f3652694-9788-4676-bec1-2415b45be939",
    "forja_abandonada": "https://github.com/user-attachments/assets/4aa66f7c-25eb-4b85-a060-24598520d049",
    "pantano_maldito": "https://github.com/user-attachments/assets/28fb041c-7ec1-4d69-9d26-3b3001f1eb8e",
    "deserto_ancestral": "https://github.com/user-attachments/assets/bbb9415b-c709-430b-9994-ff0d1dbfe58d",
    "picos_gelados": "https://github.com/user-attachments/assets/18a87067-9158-4304-a9a7-3b71a8977263"
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
    const corBase = isSuccess ? '#2ecc71' : '#e74c3c';
    const icone = isSuccess ? '✨' : '❌';
    
    const modalHtml = `
    <div id="modal-alerta" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 9999; display: flex; justify-content: center; align-items: center; backdrop-filter: blur(3px);">
        <div style="background: linear-gradient(180deg, #1e293b, #0f172a); border: 2px solid ${corBase}; border-radius: 16px; padding: 20px; width: 75%; max-width: 280px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.8), inset 0 0 15px rgba(${isSuccess ? '46,204,113' : '231,76,60'}, 0.2);">
            <h3 style="color: ${corBase}; margin: 0 0 10px 0; font-size: 1.2em; text-transform: uppercase; letter-spacing: 1px;">${icone} ${titulo}</h3>
            <p style="color: #cbd5e1; margin: 0 0 20px 0; font-size: 0.95em; line-height: 1.4;">${mensagem}</p>
            <button onclick="document.getElementById('modal-alerta').remove()" style="width: 100%; padding: 10px; background: ${corBase}; border: none; color: #000; border-radius: 8px; cursor: pointer; font-weight: 800; font-size: 1em; text-transform: uppercase;">Entendido</button>
        </div>
    </div>`;
    
    const m = document.getElementById('modal-alerta');
    if(m) m.remove();
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

function confirmarViagemMapa(destino) {
    const ehVip = window.dadosViagemAtual.vip;
    const nome = NOMES_REGIOES[destino] || destino;
    
    // LORE RPG PARA O TEXTO
    const titulo = ehVip ? '🌌 Portal Místico' : '🗺️ Jornada Longa';
    const corBorda = ehVip ? '#8b5cf6' : '#f39c12';
    const corBotao = ehVip ? 'linear-gradient(90deg, #8b5cf6, #6d28d9)' : 'linear-gradient(90deg, #f59e0b, #d97706)';
    
    const msg = ehVip 
        ? `Usar magia arcana para abrir um portal direto para <b>${nome}</b>?`
        : `Deseja seguir pela estrada até <b>${nome}</b>?<br><span style="font-size:0.8em; color:#94a3b8; display:block; margin-top:8px;">⏳ A viagem levará 6 minutos.</span>`;

    const modalHtml = `
    <div id="modal-viagem" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 9999; display: flex; justify-content: center; align-items: center; backdrop-filter: blur(3px);">
        <div style="background: linear-gradient(180deg, #1e293b, #0f172a); border: 2px solid ${corBorda}; border-radius: 16px; padding: 20px; width: 75%; max-width: 280px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.8), 0 0 20px rgba(${ehVip ? '139,92,246' : '243,156,18'}, 0.3);">
            <h3 style="color: ${corBorda}; margin: 0 0 10px 0; font-size: 1.2em; text-transform: uppercase; letter-spacing: 1px; text-shadow: 0 0 8px ${corBorda};">${titulo}</h3>
            <p style="color: #e2e8f0; margin: 0 0 20px 0; font-size: 0.95em; line-height: 1.4;">${msg}</p>
            <div style="display: flex; gap: 10px;">
                <button onclick="document.getElementById('modal-viagem').remove()" style="flex: 1; padding: 10px; background: #0f172a; border: 1px solid #334155; color: #94a3b8; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 0.9em;">Cancelar</button>
                <button onclick="document.getElementById('modal-viagem').remove(); iniciarViagemServidor('${destino}');" style="flex: 1.2; padding: 10px; background: ${corBotao}; border: none; color: white; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 0.95em; box-shadow: 0 4px 10px rgba(0,0,0,0.3);">Viajar</button>
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

    conteudo.innerHTML = '<p style="text-align: center; color: #888; padding: 40px;">Conectando ao reino... 🐎</p>';

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

// ==========================================
// RENDERIZA A CIDADE (A CAPITAL)
// ==========================================
function renderizarCidade(conteudo, p) {
    const imgCidade = IMAGENS_DAS_REGIOES["reino_eldora"] || "/static/regions/reino_eldora.jpg";
    
    conteudo.innerHTML = `
        <div class="home-banner" style="border-color: #f39c12; margin-bottom: 15px; border-radius: 12px; overflow: hidden; position: relative;">
            <img src="${imgCidade}" onerror="this.src='https://placehold.co/600x600/111/333?text=A+Capital+de+Eldora'" style="width: 100%; aspect-ratio: 1 / 1; display: block; object-fit: cover;">
            
            <div style="position: absolute; bottom: 0; left: 0; width: 100%; height: 35%; background: linear-gradient(to bottom, transparent, rgba(0,0,0,0.9));"></div>
            
            <div style="position: absolute; bottom: 15px; width: 100%; text-align: center;">
                <h2 style="color: #f8fafc; margin: 0 0 5px 0; font-size: 1.6em; text-shadow: 2px 2px 5px #000;">A Capital</h2>
                <p style="color: #f39c12; font-size: 0.9em; font-weight: bold; margin: 0; text-shadow: 1px 1px 3px #000;">O coração do mundo.</p>
            </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px;">
            <button onclick="abrirMapaEldora()" style="background: #1e293b; border: 1px solid #334155; border-bottom: 3px solid #22c55e; padding: 15px; border-radius: 10px; cursor: pointer; display: flex; flex-direction: column; align-items: center; transition: 0.2s;">
                <span style="font-size: 2em; margin-bottom: 5px;">🗺️</span>
                <strong style="color: #f8fafc; font-size: 0.95em;">Viajar / Mapa</strong>
            </button>
            <button onclick="exibirAlertaCustom('Bloqueado', 'O Mercado Livre está em construção.', false)" style="background: #1e293b; border: 1px solid #334155; border-bottom: 3px solid #f59e0b; padding: 15px; border-radius: 10px; cursor: pointer; display: flex; flex-direction: column; align-items: center;">
                <span style="font-size: 2em; margin-bottom: 5px;">🏪</span><strong style="color: #f8fafc; font-size: 0.95em;">Mercado Livre</strong>
            </button>
            <button onclick="exibirAlertaCustom('Bloqueado', 'A Forja Real será aberta em breve.', false)" style="background: #1e293b; border: 1px solid #334155; border-bottom: 3px solid #64748b; padding: 15px; border-radius: 10px; cursor: pointer; display: flex; flex-direction: column; align-items: center;">
                <span style="font-size: 2em; margin-bottom: 5px;">⚒️</span><strong style="color: #f8fafc; font-size: 0.95em;">Forja Real</strong>
            </button>
            <button onclick="exibirAlertaCustom('Bloqueado', 'Arena em manutenção.', false)" style="background: #1e293b; border: 1px solid #334155; border-bottom: 3px solid #ef4444; padding: 15px; border-radius: 10px; cursor: pointer; display: flex; flex-direction: column; align-items: center;">
                <span style="font-size: 2em; margin-bottom: 5px;">⚔️</span><strong style="color: #f8fafc; font-size: 0.95em;">Arena PvP</strong>
            </button>
            <button onclick="exibirAlertaCustom('Bloqueado', 'Guildas não liberadas ainda.', false)" style="background: #1e293b; border: 1px solid #334155; border-bottom: 3px solid #eab308; padding: 15px; border-radius: 10px; cursor: pointer; display: flex; flex-direction: column; align-items: center;">
                <span style="font-size: 2em; margin-bottom: 5px;">🏰</span><strong style="color: #f8fafc; font-size: 0.95em;">Guilda</strong>
            </button>
            <button onclick="exibirAlertaCustom('Bloqueado', 'Laboratório isolado por risco de explosão.', false)" style="background: #1e293b; border: 1px solid #334155; border-bottom: 3px solid #06b6d4; padding: 15px; border-radius: 10px; cursor: pointer; display: flex; flex-direction: column; align-items: center;">
                <span style="font-size: 2em; margin-bottom: 5px;">🧪</span><strong style="color: #f8fafc; font-size: 0.95em;">Laboratório</strong>
            </button>
        </div>
    `;
}

// ==========================================
// RENDERIZA A SELVA (ÁREA EXTERNA)
// ==========================================
function renderizarSelva(conteudo, p) {
    const nomeRegiao = NOMES_REGIOES[p.local_atual] || "Terras Selvagens";
    const imagemLink = IMAGENS_DAS_REGIOES[p.local_atual] || ''; 
    
    conteudo.innerHTML = `
        <div class="home-banner" style="border-color: #2ecc71; margin-bottom: 15px; position: relative; border-radius: 12px; overflow: hidden;">
            <img src="${imagemLink}" onerror="this.src='https://placehold.co/600x600/111/333?text=${nomeRegiao}'" style="width: 100%; aspect-ratio: 1 / 1; display: block; object-fit: cover;">
            <div style="position: absolute; bottom: 0; left: 0; width: 100%; height: 35%; background: linear-gradient(to bottom, transparent, rgba(0,0,0,0.95));"></div>
            <div style="position: absolute; bottom: 12px; left: 15px;">
                <h3 style="color: #fff; margin: 0; font-size: 1.4em; text-shadow: 2px 2px 5px #000;">📍 ${nomeRegiao}</h3>
                <p style="color: #2ecc71; margin: 0; font-size: 0.9em; font-weight: bold; text-shadow: 1px 1px 3px #000;">Área de Exploração</p>
            </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
            <button onclick="exibirAlertaCustom('Aviso', 'A caça no mapa interativo será liberada em breve!', false)" style="background: linear-gradient(180deg, #1e293b, #0f172a); border: 1px solid #334155; border-bottom: 3px solid #e74c3c; padding: 12px; border-radius: 8px; cursor: pointer; color: white; font-weight: bold; font-size: 1.05em; display: flex; align-items: center; justify-content: center; gap: 8px;">
                <span style="font-size: 1.2em;">⚔️</span> Caçar
            </button>
            <button onclick="exibirAlertaCustom('Aviso', 'O Calabouço será liberado em breve!', false)" style="background: linear-gradient(180deg, #1e293b, #0f172a); border: 1px solid #334155; border-bottom: 3px solid #9b59b6; padding: 12px; border-radius: 8px; cursor: pointer; color: white; font-weight: bold; font-size: 1.05em; display: flex; align-items: center; justify-content: center; gap: 8px;">
                <span style="font-size: 1.2em;">🏰</span> Calabouço
            </button>
        </div>

        <div style="display: flex; gap: 8px; margin-bottom: 10px;">
            <button onclick="exibirAlertaCustom('Premium', 'Auto-Caça funciona apenas no chat do Telegram.', false)" style="flex: 1; background: #1e293b; border: 1px solid #334155; border-bottom: 2px solid #3498db; padding: 8px; border-radius: 6px; color: #cbd5e1; font-weight: bold; font-size: 0.9em; cursor: pointer;">⏱️ 10x</button>
            <button onclick="exibirAlertaCustom('Premium', 'Auto-Caça funciona apenas no chat do Telegram.', false)" style="flex: 1; background: #1e293b; border: 1px solid #334155; border-bottom: 2px solid #3498db; padding: 8px; border-radius: 6px; color: #cbd5e1; font-weight: bold; font-size: 0.9em; cursor: pointer;">⏱️ 25x</button>
            <button onclick="exibirAlertaCustom('Premium', 'Auto-Caça funciona apenas no chat do Telegram.', false)" style="flex: 1; background: #1e293b; border: 1px solid #334155; border-bottom: 2px solid #3498db; padding: 8px; border-radius: 6px; color: #cbd5e1; font-weight: bold; font-size: 0.9em; cursor: pointer;">⏱️ 35x</button>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px;">
            <button onclick="abrirMapaEldora()" style="background: #1e293b; border: 1px solid #334155; padding: 10px; border-radius: 6px; color: #94a3b8; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 6px; cursor: pointer;">🗺️ Mapa</button>
            <button onclick="exibirAlertaCustom('Info', 'Use a aba Wiki para estudar os monstros desta região.', true)" style="background: #1e293b; border: 1px solid #334155; padding: 10px; border-radius: 6px; color: #94a3b8; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 6px; cursor: pointer;">ℹ️ Info</button>
        </div>
    `;
}

// ==========================================
// FUNÇÃO: ABRIR O MAPA MÚNDI
// ==========================================
async function abrirMapaEldora() {
    const conteudo = document.getElementById('aba-reino');
    const charId = localStorage.getItem("jogadorEldoraID");

    conteudo.innerHTML = '<p style="text-align: center; color: #888; padding: 40px;">Abrindo pergaminho... 🗺️</p>';

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

        // TELA DE VIAGEM ANIMADA (Para jogadores Free)
        if (p.estado && p.estado.action === 'travel') {
            const dataFim = new Date(p.estado.finish_time);
            const destinoNome = NOMES_REGIOES[p.estado.details.destination] || "Região Desconhecida";
            
            infoPainel = `
                <style>
                    @keyframes pulseRing { 0% { transform: scale(0.9); opacity: 1; } 100% { transform: scale(1.3); opacity: 0; } }
                    @keyframes spin { 100% { transform: rotate(360deg); } }
                </style>
                <div style="background: linear-gradient(180deg, #0f172a, #020617); border: 2px solid #f39c12; border-radius: 12px; padding: 25px 15px; text-align: center; margin-bottom: 15px; box-shadow: 0 8px 20px rgba(0,0,0,0.6);">
                    <h3 style="color: #f39c12; margin: 0 0 5px 0; text-transform: uppercase; letter-spacing: 1px;">🐎 Na Estrada</h3>
                    <p style="color: #94a3b8; font-size: 0.9em; margin: 0 0 20px 0;">Caminhando para <b>${destinoNome}</b></p>
                    
                    <div style="position: relative; width: 60px; height: 60px; margin: 0 auto 20px auto;">
                        <div style="position: absolute; top:0; left:0; width:100%; height:100%; border-radius:50%; border: 3px dashed #f59e0b; animation: spin 4s linear infinite;"></div>
                        <div style="position: absolute; top:0; left:0; width:100%; height:100%; border-radius:50%; border: 3px solid #d97706; animation: pulseRing 1.5s ease-out infinite;"></div>
                        <div style="position: absolute; top:50%; left:50%; transform: translate(-50%, -50%); font-size: 1.5em;">🏇</div>
                    </div>
                    
                    <div style="font-size: 2.8em; color: #fff; font-weight: 800; font-family: monospace; text-shadow: 0 0 10px rgba(243,156,18,0.8);" id="timer-viagem">00:00</div>
                </div>
            `;
            iniciarCronometroViagem(dataFim);

            let coord = COORDENADAS_MAPA[p.estado.details.destination];
            if(coord) pinosHtml += `<div class="map-pin accessible" style="top: ${coord.top}%; left: ${coord.left}%;"></div>`;

        } else {
            // TELA DE ESCOLHER DESTINO NO MAPA
            let locaisPossiveis = ehVIP ? Object.keys(NOMES_REGIOES).filter(r => r !== p.local_atual) : (CONEXOES_MAPA[p.local_atual] || []);

            for (const regiaoId in COORDENADAS_MAPA) {
                let coord = COORDENADAS_MAPA[regiaoId];
                let classePino = 'map-pin';
                let cliqueAcao = `exibirAlertaCustom('Distante', 'Você precisa viajar para uma região vizinha primeiro.', false)`;

                if (regiaoId === p.local_atual) {
                    classePino += ' current';
                    cliqueAcao = `exibirAlertaCustom('Local Atual', 'Você já está acampado aqui.', true)`;
                } else if (locaisPossiveis.includes(regiaoId)) {
                    classePino += ' accessible';
                    cliqueAcao = `confirmarViagemMapa('${regiaoId}')`;
                }

                pinosHtml += `<div class="${classePino}" style="top: ${coord.top}%; left: ${coord.left}%;" onclick="${cliqueAcao}"><div class="map-pin-label">${NOMES_REGIOES[regiaoId]}</div></div>`;
            }

            infoPainel = `
                <div style="background: #020617; padding: 15px; border-radius: 12px; margin-bottom: 15px; border: 1px solid #1e293b; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 8px; margin-bottom: 8px;">
                        <span style="color: #94a3b8; font-size: 0.85em; font-weight: bold; text-transform: uppercase;">Você está em:</span>
                        <strong style="color: #f1c40f; font-size: 1.1em;">📍 ${NOMES_REGIOES[p.local_atual] || p.local_atual}</strong>
                    </div>
                    <div style="font-size: 0.8em; color: #cbd5e1; display: flex; flex-direction: column; gap: 4px;">
                        <div><span style="display:inline-block; width:10px; height:10px; background:#2ecc71; border-radius:50%; margin-right:5px; box-shadow: 0 0 5px #2ecc71;"></span> <span style="color:#2ecc71; font-weight:bold;">Verde:</span> Clique para viajar (${ehVIP ? 'Portal Instantâneo' : 'Caminhada 6 min'})</div>
                        <div><span style="display:inline-block; width:10px; height:10px; background:#e74c3c; border-radius:50%; margin-right:5px;"></span> <span style="color:#e74c3c; font-weight:bold;">Vermelho:</span> Muito distante / Bloqueado</div>
                    </div>
                </div>
            `;
        }

        const LINK_IMAGEM_GITHUB = 'https://github.com/user-attachments/assets/0d242135-57d0-4435-9251-d48acbd5deba'; 

        conteudo.innerHTML = `
            ${infoPainel}
            <div class="map-container" style="border: 2px solid ${p.estado && p.estado.action === 'travel' ? '#f39c12' : '#334155'}; transition: 0.3s;">
                <img src="${LINK_IMAGEM_GITHUB}" style="width: 100%; display: block;">
                ${pinosHtml}
            </div>
            <button onclick="carregarReino()" style="width: 100%; background: #0f172a; padding: 14px; border: 1px solid #334155; color: #cbd5e1; border-radius: 8px; font-weight: bold; font-size: 1em; margin-top: 10px; cursor: pointer;">⬅️ Voltar para a Região</button>
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
            exibirAlertaCustom("Magia Falhou", dados.erro, false); 
            return; 
        }

        if (dados.is_vip) {
            exibirAlertaCustom("Portal Aberto!", `A magia te transportou para ${NOMES_REGIOES[destino]}!`, true);
            carregarReino(); // Volta para a tela da região
        } else {
            abrirMapaEldora(); // Recarrega o mapa pra mostrar a animação de caminhada
        }
    } catch(e) {
        exibirAlertaCustom("Erro Obscuro", "Não foi possível conjurar a magia de viagem.", false);
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
                setTimeout(() => {
                    exibirAlertaCustom("Jornada Concluída!", "Você chegou ao seu destino a salvo.", true);
                    carregarReino(); 
                }, 1000); 
            });
            return;
        }

        const m = Math.floor((diffMS / 1000) / 60).toString().padStart(2, '0');
        const s = Math.floor((diffMS / 1000) % 60).toString().padStart(2, '0');
        elementoTimer.innerHTML = `${m}:${s}`;
    }, 1000);
}