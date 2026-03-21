// ==========================================
// CONFIGURAÇÃO DO MAPA MÚNDI
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

// ==========================================
// 📍 COORDENADAS DOS PINOS NO MAPA (%)
// ==========================================
const COORDENADAS_MAPA = {
    "reino_eldora": { top: 48, left: 50 }, // Castelo (Centro)
    "pradaria_inicial": { top: 33, left: 62 }, // Casinha com plantação
    "floresta_sombria": { top: 25, left: 82 }, // Árvores arroxeadas (Topo Dir)
    "pedreira_granito": { top: 45, left: 85 }, // Pedras e picaretas (Meio Dir)
    "campos_linho": { top: 58, left: 78 }, // Flores azuis e brancas
    "pico_grifo": { top: 72, left: 75 }, // Montanha com ninho
    "mina_ferro": { top: 82, left: 58 }, // Caverna com trilhos
    "forja_abandonada": { top: 78, left: 35 }, // Ruína com fogo azul
    "pantano_maldito": { top: 60, left: 20 }, // Água verde e caveira
    "deserto_ancestral": { top: 32, left: 22 }, // Areia e pilares (Topo Esq)
    "picos_gelados": { top: 15, left: 50 }  // Neve e lagos (Topo Centro)
};

// Quem se conecta com quem (para jogadores Free)
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
window.dadosViagemAtual = {}; // Guarda estado pra usar nos cliques do mapa

function carregarReino() {
    const conteudo = document.getElementById('aba-reino');
    
    conteudo.innerHTML = `
        <div class="home-banner" style="border-color: #f39c12; margin-bottom: 15px;">
            <img src="/static/regions/reino_eldora.jpg" onerror="this.src='https://github.com/user-attachments/assets/abdbcb1f-b3ba-4e42-b082-be1a5d839d73'">
        </div>
        
        <div style="text-align: center; margin-bottom: 20px;">
            <h2 style="color: #f8fafc; margin: 0 0 5px 0; font-size: 1.4em;">A Capital</h2>
            <p style="color: #94a3b8; font-size: 0.85em; margin: 0;">Explore ou prepare-se para caçar.</p>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px;">
            <button onclick="abrirMapaEldora()" style="background: #1e293b; border: 1px solid #334155; border-bottom: 3px solid #22c55e; padding: 15px; border-radius: 10px; cursor: pointer; display: flex; flex-direction: column; align-items: center; transition: 0.2s;">
                <span style="font-size: 2em; margin-bottom: 5px;">🗺️</span>
                <strong style="color: #f8fafc; font-size: 0.95em;">Mapa e Viagem</strong>
            </button>
            <button onclick="alert('Mercado em desenvolvimento!')" style="background: #1e293b; border: 1px solid #334155; border-bottom: 3px solid #f59e0b; padding: 15px; border-radius: 10px; cursor: pointer; display: flex; flex-direction: column; align-items: center; transition: 0.2s;">
                <span style="font-size: 2em; margin-bottom: 5px;">🏪</span>
                <strong style="color: #f8fafc; font-size: 0.95em;">Mercado Livre</strong>
            </button>
            <button onclick="alert('Forja em desenvolvimento!')" style="background: #1e293b; border: 1px solid #334155; border-bottom: 3px solid #64748b; padding: 15px; border-radius: 10px; cursor: pointer; display: flex; flex-direction: column; align-items: center; transition: 0.2s;">
                <span style="font-size: 2em; margin-bottom: 5px;">⚒️</span><strong style="color: #f8fafc; font-size: 0.95em;">Forja Real</strong>
            </button>
            <button onclick="alert('Arena em desenvolvimento!')" style="background: #1e293b; border: 1px solid #334155; border-bottom: 3px solid #ef4444; padding: 15px; border-radius: 10px; cursor: pointer; display: flex; flex-direction: column; align-items: center; transition: 0.2s;">
                <span style="font-size: 2em; margin-bottom: 5px;">⚔️</span><strong style="color: #f8fafc; font-size: 0.95em;">Arena PvP</strong>
            </button>
        </div>
    `;
}

async function abrirMapaEldora() {
    const conteudo = document.getElementById('aba-reino');
    const charId = localStorage.getItem("jogadorEldoraID");

    conteudo.innerHTML = '<p style="text-align: center; color: #888;">Desenhando pergaminho do mapa... 🗺️</p>';

    try {
        const resposta = await fetch(`/api/personagem/${charId}`);
        const p = await resposta.json();
        if (p.erro) return;
        // FORÇA O VALOR PADRÃO CASO O PYTHON ESTEJA LENTO OU FALHE
        p.local_atual = p.local_atual || "reino_eldora";
        p.tier = p.tier || "free";
        p.estado = p.estado || { action: "idle" };

        let ehVIP = ["lenda", "vip", "premium", "admin"].includes(p.tier);
        window.dadosViagemAtual = { local: p.local_atual, vip: ehVIP };
        
        let infoPainel = '';
        let pinosHtml = '';

        // SE ESTIVER VIAJANDO
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

            // Desenha apenas o pino do destino pulsando
            let coord = COORDENADAS_MAPA[p.estado.details.destination];
            if(coord) {
                pinosHtml += `<div class="map-pin accessible" style="top: ${coord.top}%; left: ${coord.left}%;"></div>`;
            }

        // SE ESTIVER PARADO (Mostra o mapa interativo completo)
        } else {
            let locaisPossiveis = ehVIP ? Object.keys(NOMES_REGIOES).filter(r => r !== p.local_atual) : (CONEXOES_MAPA[p.local_atual] || []);

            // Loop para criar os pinos em cima do mapa
            for (const regiaoId in COORDENADAS_MAPA) {
                let coord = COORDENADAS_MAPA[regiaoId];
                let classePino = 'map-pin';
                let cliqueAcao = `alert('Você não pode viajar para cá agora! Vá para uma região vizinha primeiro.')`;

                if (regiaoId === p.local_atual) {
                    classePino += ' current';
                    cliqueAcao = `alert('Você já está em ${NOMES_REGIOES[regiaoId]}.')`;
                } else if (locaisPossiveis.includes(regiaoId)) {
                    classePino += ' accessible';
                    cliqueAcao = `confirmarViagemMapa('${regiaoId}')`;
                }

                pinosHtml += `
                    <div class="${classePino}" style="top: ${coord.top}%; left: ${coord.left}%;" onclick="${cliqueAcao}">
                        <div class="map-pin-label">${NOMES_REGIOES[regiaoId]}</div>
                    </div>
                `;
            }

            infoPainel = `
                <div style="background: #020617; padding: 12px; border-radius: 10px; margin-bottom: 15px; border: 1px solid #1e293b;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: #94a3b8; font-size: 0.85em;">Local Atual:</span>
                        <strong style="color: #f1c40f;">📍 ${NOMES_REGIOES[p.local_atual] || p.local_atual}</strong>
                    </div>
                    <div style="margin-top: 5px; font-size: 0.8em; color: #aaa;">
                        <span style="display:inline-block; width:10px; height:10px; background:#2ecc71; border-radius:50%; margin-right:5px;"></span> Verde: Regiões de Destino (${ehVIP ? 'Instântaneo' : '6 min'})<br>
                        <span style="display:inline-block; width:10px; height:10px; background:#e74c3c; border-radius:50%; margin-right:5px;"></span> Vermelho: Distante / Bloqueado
                    </div>
                </div>
            `;
        }

        // O LINK DO SEU GITHUB VAI AQUI 👇
        const LINK_IMAGEM_GITHUB = 'https://github.com/user-attachments/assets/0d242135-57d0-4435-9251-d48acbd5deba'; // Substitua pelo link correto do seu mapa caso precise

        conteudo.innerHTML = `
            ${infoPainel}
            <div class="map-container">
                <img src="${LINK_IMAGEM_GITHUB}" style="width: 100%; display: block;">
                ${pinosHtml}
            </div>
            <button onclick="carregarReino()" style="width: 100%; background: #1a1a1a; padding: 12px; border: 1px solid #333; color: white; border-radius: 8px;">⬅️ Voltar para a Cidade</button>
        `;

    } catch (e) {
        conteudo.innerHTML = '<p style="color: red; text-align: center;">Erro ao carregar o mapa.</p>';
    }
}

// Interação quando clica num pino verde
function confirmarViagemMapa(destino) {
    let msg = window.dadosViagemAtual.vip 
        ? `Viajar instantaneamente para ${NOMES_REGIOES[destino]}?`
        : `Iniciar viagem para ${NOMES_REGIOES[destino]}? (Leva 6 minutos)`;

    if(confirm(msg)) {
        iniciarViagemServidor(destino);
    }
}

async function iniciarViagemServidor(destino) {
    const charId = localStorage.getItem("jogadorEldoraID");
    try {
        const res = await fetch('/api/viajar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: charId, destino: destino })
        });
        const dados = await res.json();
        
        if (dados.erro) { alert(dados.erro); return; }

        if (dados.is_vip) {
            alert("🚀 Chegou ao destino instantaneamente!");
            abrirMapaEldora(); 
        } else {
            abrirMapaEldora(); // Recarrega o mapa pra mostrar o relógio rolando
        }
    } catch(e) {
        alert("Erro de magia nas rotas.");
    }
}

function iniciarCronometroViagem(dataFim) {
    if (_intervaloViagem) clearInterval(_intervaloViagem);
    
    _intervaloViagem = setInterval(() => {
        const elementoTimer = document.getElementById("timer-viagem");
        if(!elementoTimer) { clearInterval(_intervaloViagem); return; } // Saiu da tela

        const diffMS = dataFim - new Date();

        if (diffMS <= 0) {
            clearInterval(_intervaloViagem);
            elementoTimer.innerHTML = "Chegou!";
            elementoTimer.style.color = "#2ecc71";
            setTimeout(() => abrirMapaEldora(), 1500); 
            return;
        }

        const m = Math.floor((diffMS / 1000) / 60).toString().padStart(2, '0');
        const s = Math.floor((diffMS / 1000) % 60).toString().padStart(2, '0');
        elementoTimer.innerHTML = `${m}:${s}`;
    }, 1000);
}