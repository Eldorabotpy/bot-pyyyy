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
        const linkMidia = p.skin_equipada || MIDIA_PERFIL_BASE[infoClasse.base] || MIDIA_PERFIL_BASE["aprendiz"];

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
            const podeUpar = p.pontos_livres > 0 ? `<button onclick="distribuirPonto('${key}')" style="background:#2ecc71; color:#000; border:none; border-radius:4px; width:24px; height:24px; font-weight:bold; cursor:pointer;">+</button>` : '';
            htmlStatus += `
                <div style="background: #1e293b; border: 1px solid #334155; padding: 10px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="font-size: 1.2em;">${st.emoji}</span>
                        <span style="color: #cbd5e1; font-size: 0.8em; text-transform: uppercase; margin-left: 5px;">${st.nome}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <strong style="color: #f8fafc; font-size: 1.1em;">${st.valor}</strong>
                        ${podeUpar}
                    </div>
                </div>`;
        }
        htmlStatus += `</div>`;

        // --- ABA DE EQUIPAMENTOS ---
        let htmlEquips = `<div style="display: grid; grid-template-columns: 1fr; gap: 8px; margin-top: 15px;">`;
        p.equipamentos.forEach(eq => {
            const corBorda = eq.vazio ? "#334155" : "#f59e0b";
            const corTexto = eq.vazio ? "#64748b" : "#f8fafc";
            htmlEquips += `
                <div style="background: #0f172a; border: 1px solid ${corBorda}; padding: 12px; border-radius: 8px; display: flex; align-items: center; gap: 10px;">
                    <div style="font-size: 1.5em; background: #1e293b; padding: 8px; border-radius: 8px;">${eq.emoji}</div>
                    <div style="flex: 1;">
                        <div style="color: #94a3b8; font-size: 0.7em; text-transform: uppercase; font-weight: bold;">${eq.slot}</div>
                        <div style="color: ${corTexto}; font-size: 0.9em; font-weight: bold;">${eq.nome}</div>
                    </div>
                    ${!eq.vazio ? `<button onclick="desequiparItem('${eq.slot}')" style="background:#e74c3c; color:white; border:none; padding:6px 10px; border-radius:6px; cursor:pointer;">Remover</button>` : ''}
                </div>`;
        });
        htmlEquips += `</div>`;

        // --- ABA DE INVENTÁRIO ---
        let htmlInv = `<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)); gap: 8px; margin-top: 15px;">`;
        if (p.inventario.length === 0) {
            htmlInv = `<p style="text-align: center; color: #64748b; padding: 20px;">Sua mochila está vazia.</p>`;
        } else {
            p.inventario.forEach(item => {
                htmlInv += `
                    <div onclick="usarOuEquiparItem('${item.id}')" style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 10px 5px; text-align: center; cursor: pointer; position: relative;">
                        <span style="position: absolute; top: -5px; right: -5px; background: #3b82f6; color: white; font-size: 0.7em; padding: 2px 6px; border-radius: 10px; font-weight: bold;">x${item.qtd}</span>
                        <div style="font-size: 1.8em; margin-bottom: 5px;">${item.emoji}</div>
                        <div style="color: #cbd5e1; font-size: 0.65em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${item.nome}</div>
                    </div>`;
            });
            htmlInv += `</div><p style="text-align:center; font-size:0.7em; color:#64748b; margin-top:10px;">Clique num item para interagir</p>`;
        }

        // ==========================================
        // 2. MONTAGEM DA TELA PRINCIPAL
        // ==========================================
        conteudo.innerHTML = `
            <div style="background: linear-gradient(135deg, #0f172a, #020617); padding: 20px; border-radius: 15px; border: 2px solid #f39c12; text-align: center; margin-bottom: 20px; position: relative; overflow: hidden;">
                <div id="media-container" style="width: 110px; height: 110px; margin: 0 auto 10px auto; border-radius: 10px; border: 2px solid #f39c12; overflow: hidden;"></div>
                <h2 style="margin: 0; color: #f39c12; font-size: 1.6em; text-shadow: 2px 2px 4px #000;">${p.nome}</h2>
                <span style="background: #f39c12; color: #000; padding: 3px 12px; border-radius: 5px; font-weight: bold; font-size: 0.8em; text-transform: uppercase;">${infoClasse.emoji} ${infoClasse.nome}</span>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px;">
                <div style="background: #1e1e1e; padding: 10px; border-radius: 8px; border-left: 3px solid #e74c3c;">
                    <span style="color: #e74c3c; font-size: 0.7em; font-weight: bold;">❤️ HP</span>
                    <div style="font-size: 1.1em; color: #fff;">${p.hp_atual} / ${p.hp_max}</div>
                </div>
                <div style="background: #1e1e1e; padding: 10px; border-radius: 8px; border-left: 3px solid #3498db;">
                    <span style="color: #3498db; font-size: 0.7em; font-weight: bold;">⚡ ENERGIA</span>
                    <div style="font-size: 1.1em; color: #fff;">${p.energy}</div>
                </div>
                <div style="background: #1e1e1e; padding: 10px; border-radius: 8px; border-left: 3px solid #f1c40f;">
                    <span style="color: #f1c40f; font-size: 0.7em; font-weight: bold;">💰 OURO</span>
                    <div style="font-size: 1.1em; color: #fff;">${p.gold.toLocaleString('pt-BR')}</div>
                </div>
                <div style="background: #1e1e1e; padding: 10px; border-radius: 8px; border-left: 3px solid #00f2fe;">
                    <span style="color: #00f2fe; font-size: 0.7em; font-weight: bold;">💎 GEMAS</span>
                    <div style="font-size: 1.1em; color: #fff;">${p.gems.toLocaleString('pt-BR')}</div>
                </div>
            </div>

            <div style="background: #252525; padding: 15px; border-radius: 10px; border: 1px solid #333; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; font-size: 0.8em; margin-bottom: 5px;">
                    <span style="color: #aaa;">Experiência (Nível <b>${p.level}</b>)</span>
                    <span style="color: #fff;">${p.xp.toLocaleString('pt-BR')} / ${p.xp_max.toLocaleString('pt-BR')}</span>
                </div>
                <div style="width: 100%; height: 10px; background: #111; border-radius: 5px; overflow: hidden;">
                    <div style="width: ${percentXP}%; height: 100%; background: linear-gradient(90deg, #8e44ad, #9b59b6); transition: 0.8s;"></div>
                </div>
            </div>

            <div style="display: flex; gap: 5px; background: #0f172a; padding: 5px; border-radius: 8px; border: 1px solid #1e293b;">
                <button onclick="alternarAbaPerfil('status')" id="btn-perf-status" style="flex:1; padding:10px; background:#1e293b; color:#fff; border:none; border-radius:6px; font-weight:bold; cursor:pointer;">Atributos ${p.pontos_livres > 0 ? `<span style="background:#e74c3c; padding:2px 6px; border-radius:10px; font-size:0.8em;">${p.pontos_livres}</span>` : ''}</button>
                <button onclick="alternarAbaPerfil('equips')" id="btn-perf-equips" style="flex:1; padding:10px; background:transparent; color:#94a3b8; border:none; border-radius:6px; font-weight:bold; cursor:pointer;">Equipamentos</button>
                <button onclick="alternarAbaPerfil('inv')" id="btn-perf-inv" style="flex:1; padding:10px; background:transparent; color:#94a3b8; border:none; border-radius:6px; font-weight:bold; cursor:pointer;">Mochila</button>
            </div>

            <div id="conteudo-perf-status" style="display: block;">${htmlStatus}</div>
            <div id="conteudo-perf-equips" style="display: none;">${htmlEquips}</div>
            <div id="conteudo-perf-inv" style="display: none;">${htmlInv}</div>
            
            <button onclick="sairDoJogo()" style="width: 100%; padding: 12px; margin-top: 25px; background: linear-gradient(180deg, #c0392b 0%, #922b21 100%); border: 1px solid #e74c3c; color: white; border-radius: 8px; font-weight: bold; font-size: 1em; cursor: pointer; display: flex; justify-content: center; align-items: center; gap: 8px;">
                🚪 Trocar Personagem
            </button>
        `;

        // Renderiza a mídia (Vídeo ou Imagem)
        const containerMedia = document.getElementById('media-container');
        if (linkMidia.toLowerCase().endsWith('.mp4')) {
            containerMedia.innerHTML = `<video src="${linkMidia}" autoplay loop muted playsinline style="width:100%; height:100%; object-fit:cover;"></video>`;
        } else {
            containerMedia.innerHTML = `<img src="${linkMidia}" style="width:100%; height:100%; object-fit:cover; object-position: top;">`;
        }

        document.getElementById('perfil-carregando').style.display = 'none';
        conteudo.style.display = 'block';

    } catch (erro) {
        console.error("Erro:", erro);
        document.getElementById('perfil-msg-carregando').innerText = "⚠️ Erro ao carregar perfil.";
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
}

// Funções placeholders para os botões novos
window.distribuirPonto = function(stat) {
    exibirAlertaCustom("Em breve", `A rota para adicionar ponto em ${stat.toUpperCase()} será ativada no próximo passo!`, true);
}
window.desequiparItem = function(slot) {
    exibirAlertaCustom("Em breve", `A rota para desequipar ${slot} será ativada no próximo passo!`, false);
}
window.usarOuEquiparItem = function(itemId) {
    exibirAlertaCustom("Em breve", `Menu de item abrirá em breve para equipar/vender.`, true);
}