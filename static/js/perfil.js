// ==========================================
// MÍDIAS PADRÃO (Apenas as classes base e o aprendiz)
// ==========================================
const MIDIA_PERFIL_BASE = {
    "guerreiro": "LINK_GITHUB_GUERREIRO.mp4",
    "berserker": "LINK_GITHUB_BERSERKER.mp4",
    "cacador": "LINK_GITHUB_CACADOR.mp4",
    "monge": "LINK_GITHUB_MONGE.mp4",
    "mago": "LINK_GITHUB_MAGO.mp4",
    "bardo": "LINK_GITHUB_BARDO.mp4",
    "assassino": "https://github.com/user-attachments/assets/cbc6a4a3-26c6-46fe-b03f-4b594b5c3b47",
    "samurai": "LINK_GITHUB_SAMURAI.mp4",
    "curandeiro": "LINK_GITHUB_CURANDEIRO.mp4",
    "aprendiz": "LINK_GITHUB_APRENDIZ.mp4",
    "aventureiro": "https://github.com/user-attachments/assets/b0f8f158-3d54-46ef-b1df-9bbd9300609f"
};

// ==========================================
// DICIONÁRIO DE CLASSES COM SUAS BASES
// ==========================================
const CLASSES_INFO = {
    // SEM CLASSE
    'aprendiz': { nome: 'Aventureiro', emoji: '🎒', base: 'aprendiz' },
    'aventureiro': { nome: 'Aventureiro', emoji: '🎒', base: 'aprendiz' },

    // GUERREIRO
    'guerreiro': { nome: 'Guerreiro', emoji: '⚔️', base: 'guerreiro' },
    'cavaleiro': { nome: 'Cavaleiro', emoji: '🛡️', base: 'guerreiro' },
    'gladiador': { nome: 'Gladiador', emoji: '🔱', base: 'guerreiro' },
    'templario': { nome: 'Templário', emoji: '⚜️', base: 'guerreiro' },
    'guardiao_divino': { nome: 'Guardião Divino', emoji: '🛡️', base: 'guerreiro' },
    
    // BERSERKER
    'berserker': { nome: 'Berserker', emoji: '🪓', base: 'berserker' },
    'barbaro': { nome: 'Bárbaro', emoji: '🗿', base: 'berserker' },
    'juggernaut': { nome: 'Juggernaut', emoji: '🐗', base: 'berserker' },
    'ira_primordial': { nome: 'Ira Primordial', emoji: '👹', base: 'berserker' },
    
    // CAÇADOR
    'cacador': { nome: 'Caçador', emoji: '🏹', base: 'cacador' },
    'patrulheiro': { nome: 'Patrulheiro', emoji: '🐾', base: 'cacador' },
    'franco_atirador': { nome: 'Franco-Atirador', emoji: '🎯', base: 'cacador' },
    'olho_de_aguia': { nome: 'Olho de Águia', emoji: '🦅', base: 'cacador' },
    
    // MONGE
    'monge': { nome: 'Monge', emoji: '🧘', base: 'monge' },
    'guardiao_do_templo': { nome: 'Guardião do Templo', emoji: '🏯', base: 'monge' },
    'punho_elemental': { nome: 'Punho Elemental', emoji: '🔥', base: 'monge' },
    'ascendente': { nome: 'Ascendente', emoji: '🕊️', base: 'monge' },
    
    // MAGO
    'mago': { nome: 'Mago', emoji: '🧙', base: 'mago' },
    'feiticeiro': { nome: 'Feiticeiro', emoji: '🔮', base: 'mago' },
    'elementalista': { nome: 'Elementalista', emoji: '☄️', base: 'mago' },
    'arquimago': { nome: 'Arquimago', emoji: '🌌', base: 'mago' },
    
    // BARDO
    'bardo': { nome: 'Bardo', emoji: '🎶', base: 'bardo' },
    'menestrel': { nome: 'Menestrel', emoji: '📜', base: 'bardo' },
    'encantador': { nome: 'Encantador', emoji: '✨', base: 'bardo' },
    'maestro': { nome: 'Maestro', emoji: '🎼', base: 'bardo' },
    
    // ASSASSINO
    'assassino': { nome: 'Assassino', emoji: '🔪', base: 'assassino' },
    'ladrao_de_sombras': { nome: 'Ladrão de Sombras', emoji: '💨', base: 'assassino' },
    'ninja': { nome: 'Ninja', emoji: '🥷', base: 'assassino' },
    'mestre_das_laminas': { nome: 'Mestre das Lâminas', emoji: '⚔️', base: 'assassino' },
    
    // SAMURAI
    'samurai': { nome: 'Samurai', emoji: '🥷', base: 'samurai' },
    'kensei': { nome: 'Kensei', emoji: '🗡️', base: 'samurai' },
    'ronin': { nome: 'Ronin', emoji: '🧧', base: 'samurai' },
    'shogun': { nome: 'Shogun', emoji: '🏯', base: 'samurai' },
    
    // CURANDEIRO
    'curandeiro': { nome: 'Curandeiro', emoji: '🩹', base: 'curandeiro' },
    'clerigo': { nome: 'Clérigo', emoji: '✝️', base: 'curandeiro' },
    'druida': { nome: 'Druida', emoji: '🌳', base: 'curandeiro' },
    'sacerdote': { nome: 'Sacerdote', emoji: '⛪', base: 'curandeiro' }
};

async function carregarMeuPerfil() {
    const charId = localStorage.getItem("jogadorEldoraID");
    const conteudo = document.getElementById('perfil-dados');

    if (!charId) {
        document.getElementById('perfil-msg-carregando').innerHTML = "<span style='color: #e74c3c;'>Nenhum herói selecionado.</span>";
        return;
    }

    try {
        const resposta = await fetch(`/perfil/${charId}`);
        const p = await resposta.json();

        if (p.erro) {
            document.getElementById('perfil-msg-carregando').innerText = "⚠️ " + p.erro;
            return;
        }

        const classeKey = (p.classe || "aprendiz").toLowerCase();
        const infoClasse = CLASSES_INFO[classeKey] || CLASSES_INFO['aprendiz'];
        
        // Se a classe não tiver PNG, usamos um placeholder
        const avatarLink = p.avatar || 'https://github.com/user-attachments/assets/9a7300d0-63af-47bb-9f52-1fd99c40ed90';

        const xpAtual = p.xp || 0;
        const xpMaximo = p.xp_max || 1; 
        let percentXP = Math.min((xpAtual / xpMaximo) * 100, 100);

        // ==========================================
        // 1. GERANDO HTML DAS ABAS INTERNAS
        // ==========================================

        // --- ABA DE STATUS ---
        let htmlStatus = `<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px;">`;
        for (const key in p.status) {
            const st = p.status[key];
            const podeUpar = p.pontos_livres > 0 ? `<button onclick="distribuirPonto('${key}')" style="background:#2ecc71; color:#000; border:none; border-radius:4px; width:24px; height:24px; font-weight:bold; cursor:pointer; box-shadow: 0 2px 4px rgba(0,0,0,0.5);">+</button>` : '';
            htmlStatus += `
                <div style="background: #1e293b; border: 1px solid #334155; padding: 10px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);">
                    <div>
                        <span style="font-size: 1.2em;">${st.emoji}</span>
                        <span style="color: #cbd5e1; font-size: 0.8em; text-transform: uppercase; margin-left: 5px; font-weight: bold;">${st.nome}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <strong style="color: #f8fafc; font-size: 1.2em;">${st.valor}</strong>
                        ${podeUpar}
                    </div>
                </div>`;
        }
        htmlStatus += `</div>`;

        // --- ABA DE EQUIPAMENTOS (VISUAL RPG - CORRIGIDO) ---
        // Slots colados nas bordas (12% e 88%) para liberar o meio
        const POSICOES_SLOTS = {
            'elmo':     { top: '12%', left: '12%', transform: 'translate(-50%, -50%)' },
            'arma':     { top: '31%', left: '12%', transform: 'translate(-50%, -50%)' },
            'armadura': { top: '50%', left: '12%', transform: 'translate(-50%, -50%)' },
            'luvas':    { top: '69%', left: '12%', transform: 'translate(-50%, -50%)' },
            'tool':     { top: '88%', left: '12%', transform: 'translate(-50%, -50%)' },
            
            'colar':    { top: '12%', left: '88%', transform: 'translate(-50%, -50%)' },
            'brinco':   { top: '31%', left: '88%', transform: 'translate(-50%, -50%)' },
            'calca':    { top: '50%', left: '88%', transform: 'translate(-50%, -50%)' },
            'anel':     { top: '69%', left: '88%', transform: 'translate(-50%, -50%)' },
            'botas':    { top: '88%', left: '88%', transform: 'translate(-50%, -50%)' }
        };

        let htmlSlots = '';
        p.equipamentos.forEach(eq => {
            const pos = POSICOES_SLOTS[eq.slot] || { top: '50%', left: '50%' };
            const corBorda = eq.vazio ? "#334155" : "#f59e0b";
            const corFundo = eq.vazio ? "rgba(15, 23, 42, 0.8)" : "rgba(245, 158, 11, 0.15)";
            
            let visualItem = '';
            if (eq.vazio) {
                visualItem = `<span style="font-size: 1.4em; opacity: 0.3;">${eq.emoji}</span>`;
            } else if (eq.icon && eq.icon.length > 5 && eq.icon.includes('.')) { 
                visualItem = `<img src="${eq.icon}" alt="${eq.nome}" style="width: 85%; height: 85%; object-fit: contain; filter: drop-shadow(0 0 4px rgba(255,255,255,0.4));">`;
            } else { 
                visualItem = `<span style="font-size: 1.8em; text-shadow: 0 0 10px rgba(255,255,255,0.5);">${eq.icon || eq.emoji}</span>`;
            }

            htmlSlots += `
                <div onclick="${!eq.vazio ? `desequiparItem('${eq.slot}')` : ''}" 
                     style="position: absolute; ${Object.entries(pos).map(([k, v]) => `${k}:${v};`).join('')} 
                            width: 50px; height: 50px; background: ${corFundo}; border: 2px solid ${corBorda}; 
                            border-radius: 8px; display: flex; justify-content: center; align-items: center; 
                            cursor: ${eq.vazio ? 'default' : 'pointer'}; box-shadow: 0 4px 8px rgba(0,0,0,0.6); 
                            backdrop-filter: blur(4px);">
                    ${visualItem}
                </div>`;
        });

        // ESTRUTURA DE CAMADAS (Z-INDEX)
        const htmlEquips = `
            <div style="position: relative; width: 100%; height: 420px; margin-top: 15px; 
                        background: #020617; 
                        border-radius: 12px; border: 2px solid #334155; overflow: hidden;
                        box-shadow: inset 0 0 30px rgba(0,0,0,0.9);">
                
                <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); 
                            width: 100%; height: 100%; z-index: 0; pointer-events: none;">
                    <img src="https://github.com/user-attachments/assets/9a7300d0-63af-47bb-9f52-1fd99c40ed90" onerror="this.style.display='none'" style="width: 100%; height: 100%; object-fit: cover; opacity: 0.85;">
                </div>

                <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); 
                            width: 50%; height: 95%; z-index: 1; display: flex; justify-content: center; align-items: center;">
                    <img id="avatar-equip-tab" src="${avatarLink}" onerror="this.src='https://github.com/user-attachments/assets/b0f8f158-3d54-46ef-b1df-9bbd9300609f'" alt="Avatar" style="width: 100%; height: 100%; object-fit: contain; filter: drop-shadow(0px 10px 15px rgba(0,0,0,0.9)); pointer-events: none;">
                </div>

                <div style="position: relative; width: 100%; height: 100%; z-index: 2;">
                    ${htmlSlots}
                </div>
            </div>
            <p style="text-align:center; font-size:0.7em; color:#64748b; margin-top:8px;">Clique num equipamento para o remover.</p>`;

        // --- ABA DE INVENTÁRIO ---
        let htmlInv = `<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(70px, 1fr)); gap: 8px; margin-top: 15px;">`;
        if (p.inventario.length === 0) {
            htmlInv = `<p style="text-align: center; color: #64748b; padding: 20px;">Sua mochila está vazia.</p>`;
        } else {
            p.inventario.forEach(item => {
                htmlInv += `
                    <div onclick="usarOuEquiparItem('${item.id}')" style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 10px 5px; text-align: center; cursor: pointer; position: relative; box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);">
                        <span style="position: absolute; top: -5px; right: -5px; background: #3b82f6; color: white; font-size: 0.65em; padding: 2px 5px; border-radius: 10px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.5);">x${item.qtd}</span>
                        <div style="font-size: 1.8em; margin-bottom: 5px; text-shadow: 0 2px 4px rgba(0,0,0,0.5);">${item.emoji}</div>
                        <div style="color: #cbd5e1; font-size: 0.6em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: bold;">${item.nome}</div>
                    </div>`;
            });
            htmlInv += `</div><p style="text-align:center; font-size:0.7em; color:#64748b; margin-top:10px;">Clique num item para interagir</p>`;
        }

        // ==========================================
        // 2. MONTAGEM DA TELA PRINCIPAL
        // ==========================================
        conteudo.innerHTML = `
            <div style="background: linear-gradient(135deg, #0f172a, #020617); padding: 15px; border-radius: 12px; border: 1px solid #f39c12; text-align: center; margin-bottom: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">
                <h2 style="margin: 0 0 5px 0; color: #f39c12; font-size: 1.5em; text-shadow: 2px 2px 4px #000; text-transform: uppercase; letter-spacing: 1px;">${p.nome}</h2>
                <span style="background: #f39c12; color: #000; padding: 2px 10px; border-radius: 5px; font-weight: 900; font-size: 0.75em; text-transform: uppercase; box-shadow: 0 2px 4px rgba(0,0,0,0.5);">${infoClasse.emoji} ${infoClasse.nome}</span>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 15px;">
                <div style="background: #1e1e1e; padding: 8px 12px; border-radius: 8px; border-left: 3px solid #e74c3c; display: flex; justify-content: space-between; align-items: center; box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);">
                    <span style="color: #e74c3c; font-size: 0.7em; font-weight: bold;">❤️ HP</span>
                    <div style="font-size: 1em; color: #fff; font-weight: bold;">${p.hp_atual} <span style="font-size:0.7em; color:#7f1d1d;">/ ${p.hp_max}</span></div>
                </div>
                <div style="background: #1e1e1e; padding: 8px 12px; border-radius: 8px; border-left: 3px solid #3498db; display: flex; justify-content: space-between; align-items: center; box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);">
                    <span style="color: #3498db; font-size: 0.7em; font-weight: bold;">⚡ ENERGIA</span>
                    <div style="font-size: 1em; color: #fff; font-weight: bold;">${p.energy}</div>
                </div>
                <div style="background: #1e1e1e; padding: 8px 12px; border-radius: 8px; border-left: 3px solid #f1c40f; display: flex; justify-content: space-between; align-items: center; box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);">
                    <span style="color: #f1c40f; font-size: 0.7em; font-weight: bold;">💰 OURO</span>
                    <div style="font-size: 1em; color: #fff; font-weight: bold;">${p.gold.toLocaleString('pt-BR')}</div>
                </div>
                <div style="background: #1e1e1e; padding: 8px 12px; border-radius: 8px; border-left: 3px solid #00f2fe; display: flex; justify-content: space-between; align-items: center; box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);">
                    <span style="color: #00f2fe; font-size: 0.7em; font-weight: bold;">💎 GEMAS</span>
                    <div style="font-size: 1em; color: #fff; font-weight: bold;">${p.gems.toLocaleString('pt-BR')}</div>
                </div>
            </div>

            <div style="background: #252525; padding: 12px; border-radius: 10px; border: 1px solid #333; margin-bottom: 20px; box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);">
                <div style="display: flex; justify-content: space-between; font-size: 0.75em; margin-bottom: 5px;">
                    <span style="color: #aaa; font-weight: bold;">Experiência (Nível <span style="color:#fff;">${p.level}</span>)</span>
                    <span style="color: #fff;">${p.xp.toLocaleString('pt-BR')} / ${p.xp_max.toLocaleString('pt-BR')}</span>
                </div>
                <div style="width: 100%; height: 8px; background: #111; border-radius: 4px; overflow: hidden; border: 1px solid #000;">
                    <div style="width: ${percentXP}%; height: 100%; background: linear-gradient(90deg, #8e44ad, #9b59b6); transition: width 0.8s ease-in-out;"></div>
                </div>
            </div>

            <div style="display: flex; gap: 5px; background: #0f172a; padding: 5px; border-radius: 8px; border: 1px solid #1e293b; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                <button onclick="alternarAbaPerfil('status')" id="btn-perf-status" style="flex:1; padding:8px 5px; background:#1e293b; color:#fff; border:none; border-radius:6px; font-weight:bold; cursor:pointer; font-size:0.85em; display:flex; align-items:center; justify-content:center; gap:5px;">
                    Atributos ${p.pontos_livres > 0 ? `<span style="background:#e74c3c; padding:2px 6px; border-radius:10px; font-size:0.8em; color:white;">${p.pontos_livres}</span>` : ''}
                </button>
                <button onclick="alternarAbaPerfil('equips')" id="btn-perf-equips" style="flex:1; padding:8px 5px; background:transparent; color:#94a3b8; border:none; border-radius:6px; font-weight:bold; cursor:pointer; font-size:0.85em;">Equipamentos</button>
                <button onclick="alternarAbaPerfil('inv')" id="btn-perf-inv" style="flex:1; padding:8px 5px; background:transparent; color:#94a3b8; border:none; border-radius:6px; font-weight:bold; cursor:pointer; font-size:0.85em;">Mochila</button>
            </div>

            <div id="conteudo-perf-status" style="display: block;">${htmlStatus}</div>
            <div id="conteudo-perf-equips" style="display: none;">${htmlEquips}</div>
            <div id="conteudo-perf-inv" style="display: none;">${htmlInv}</div>
            
            <button onclick="sairDoJogo()" style="width: 100%; padding: 12px; margin-top: 25px; background: linear-gradient(180deg, #c0392b 0%, #922b21 100%); border: 1px solid #e74c3c; color: white; border-radius: 8px; font-weight: bold; font-size: 0.95em; cursor: pointer; display: flex; justify-content: center; align-items: center; gap: 8px; text-transform: uppercase; letter-spacing: 1px; box-shadow: 0 4px 10px rgba(0,0,0,0.4);">
                🚪 Trocar Personagem
            </button>
        `;

        document.getElementById('perfil-carregando').style.display = 'none';
        conteudo.style.display = 'block';

        // Salva a URL do Avatar globalmente para podermos puxar quando clicar na aba Equipamentos
        window._avatarAtualEldora = avatarLink;

    } catch (erro) {
        console.error("Erro:", erro);
        document.getElementById('perfil-msg-carregando').innerText = "⚠️ Erro ao carregar perfil. Verifique a conexão.";
    }
}

// ==========================================
// FUNÇÃO AUXILIAR DAS ABAS INTERNAS
// ==========================================
window.alternarAbaPerfil = function(abaID) {
    // Esconde todos os conteúdos
    document.getElementById('conteudo-perf-status').style.display = 'none';
    document.getElementById('conteudo-perf-equips').style.display = 'none';
    document.getElementById('conteudo-perf-inv').style.display = 'none';
    
    // Reseta o estilo dos botões
    const botoes = ['btn-perf-status', 'btn-perf-equips', 'btn-perf-inv'];
    botoes.forEach(b => {
        document.getElementById(b).style.background = 'transparent';
        document.getElementById(b).style.color = '#94a3b8';
    });

    // Mostra a aba selecionada e destaca o botão
    document.getElementById(`conteudo-perf-${abaID}`).style.display = 'block';
    document.getElementById(`btn-perf-${abaID}`).style.background = '#1e293b';
    document.getElementById(`btn-perf-${abaID}`).style.color = '#fff';

    // Ajusta o avatar do centro apenas quando entra na aba de Equipamentos
    if (abaID === 'equips' && window._avatarAtualEldora) {
        const imgCentro = document.getElementById('avatar-equip-tab');
        if (imgCentro) imgCentro.src = window._avatarAtualEldora;
    }
}

// ==========================================
// FUNÇÕES PLACEHOLDERS (Próximo Passo)
// ==========================================
window.distribuirPonto = function(stat) {
    exibirAlertaCustom("Aguarde...", `A rota mágica para upar o atributo <b>${stat.toUpperCase()}</b> será conjurada na nossa próxima lição!`, true);
}

window.desequiparItem = function(slot) {
    exibirAlertaCustom("Aguarde...", `Em breve poderás remover itens do slot de <b>${slot}</b>.`, false);
}

window.usarOuEquiparItem = function(itemId) {
    exibirAlertaCustom("Aguarde...", `O menu detalhado do item abrirá aqui para usar ou equipar a tua arma!`, true);
}