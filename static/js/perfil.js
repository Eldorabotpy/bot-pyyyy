// ==========================================
// CONFIGURAÇÕES GERAIS
// ==========================================
let perfilDadosGlobais = null; // Guarda os dados para usarmos no Modal

const CLASSES_INFO = {
    'aprendiz': { nome: 'Aventureiro', emoji: '🎒', base: 'aprendiz' },
    'aventureiro': { nome: 'Aventureiro', emoji: '🎒', base: 'aprendiz' },
    'guerreiro': { nome: 'Guerreiro', emoji: '⚔️', base: 'guerreiro' },
    'cavaleiro': { nome: 'Cavaleiro', emoji: '🛡️', base: 'guerreiro' },
    'gladiador': { nome: 'Gladiador', emoji: '🔱', base: 'guerreiro' },
    'templario': { nome: 'Templário', emoji: '⚜️', base: 'guerreiro' },
    'guardiao_divino': { nome: 'Guardião Divino', emoji: '🛡️', base: 'guerreiro' },
    'berserker': { nome: 'Berserker', emoji: '🪓', base: 'berserker' },
    'barbaro': { nome: 'Bárbaro', emoji: '🗿', base: 'berserker' },
    'juggernaut': { nome: 'Juggernaut', emoji: '🐗', base: 'berserker' },
    'ira_primordial': { nome: 'Ira Primordial', emoji: '👹', base: 'berserker' },
    'cacador': { nome: 'Caçador', emoji: '🏹', base: 'cacador' },
    'patrulheiro': { nome: 'Patrulheiro', emoji: '🐾', base: 'cacador' },
    'franco_atirador': { nome: 'Franco-Atirador', emoji: '🎯', base: 'cacador' },
    'olho_de_aguia': { nome: 'Olho de Águia', emoji: '🦅', base: 'cacador' },
    'monge': { nome: 'Monge', emoji: '🧘', base: 'monge' },
    'guardiao_do_templo': { nome: 'Guardião do Templo', emoji: '🏯', base: 'monge' },
    'punho_elemental': { nome: 'Punho Elemental', emoji: '🔥', base: 'monge' },
    'ascendente': { nome: 'Ascendente', emoji: '🕊️', base: 'monge' },
    'mago': { nome: 'Mago', emoji: '🧙', base: 'mago' },
    'feiticeiro': { nome: 'Feiticeiro', emoji: '🔮', base: 'mago' },
    'elementalista': { nome: 'Elementalista', emoji: '☄️', base: 'mago' },
    'arquimago': { nome: 'Arquimago', emoji: '🌌', base: 'mago' },
    'bardo': { nome: 'Bardo', emoji: '🎶', base: 'bardo' },
    'menestrel': { nome: 'Menestrel', emoji: '📜', base: 'bardo' },
    'encantador': { nome: 'Encantador', emoji: '✨', base: 'bardo' },
    'maestro': { nome: 'Maestro', emoji: '🎼', base: 'bardo' },
    'assassino': { nome: 'Assassino', emoji: '🔪', base: 'assassino' },
    'ladrao_de_sombras': { nome: 'Ladrão de Sombras', emoji: '💨', base: 'assassino' },
    'ninja': { nome: 'Ninja', emoji: '🥷', base: 'assassino' },
    'mestre_das_laminas': { nome: 'Mestre das Lâminas', emoji: '⚔️', base: 'assassino' },
    'samurai': { nome: 'Samurai', emoji: '🥷', base: 'samurai' },
    'kensei': { nome: 'Kensei', emoji: '🗡️', base: 'samurai' },
    'ronin': { nome: 'Ronin', emoji: '🧧', base: 'samurai' },
    'shogun': { nome: 'Shogun', emoji: '🏯', base: 'samurai' },
    'curandeiro': { nome: 'Curandeiro', emoji: '🩹', base: 'curandeiro' },
    'clerigo': { nome: 'Clérigo', emoji: '✝️', base: 'curandeiro' },
    'druida': { nome: 'Druida', emoji: '🌳', base: 'curandeiro' },
    'sacerdote': { nome: 'Sacerdote', emoji: '⛪', base: 'curandeiro' }
};

// ==========================================
// FUNÇÃO PRINCIPAL DE CARREGAMENTO
// ==========================================
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
        if (p.erro) { document.getElementById('perfil-msg-carregando').innerText = "⚠️ " + p.erro; return; }

        perfilDadosGlobais = p; // Salva globalmente
        const classeKey = (p.classe || "aprendiz").toLowerCase();
        const infoClasse = CLASSES_INFO[classeKey] || CLASSES_INFO['aprendiz'];
        const avatarLink = p.avatar || 'https://github.com/user-attachments/assets/9a7300d0-63af-47bb-9f52-1fd99c40ed90';
        let percentXP = Math.min((p.xp / p.xp_max) * 100, 100);

        // --- ABA DE STATUS ---
        let htmlStatus = `<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px;">`;
        for (const key in p.status) {
            const st = p.status[key];
            const podeUpar = p.pontos_livres > 0 ? `<button onclick="distribuirPonto('${key}')" style="background:#2ecc71; color:#000; border:none; border-radius:4px; width:24px; height:24px; font-weight:bold; cursor:pointer; box-shadow: 0 2px 4px rgba(0,0,0,0.5);">+</button>` : '';
            htmlStatus += `
                <div style="background: #1e293b; border: 1px solid #334155; padding: 10px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);">
                    <div><span style="font-size: 1.2em;">${st.emoji}</span> <span style="color: #cbd5e1; font-size: 0.8em; text-transform: uppercase; font-weight: bold;">${st.nome}</span></div>
                    <div style="display: flex; align-items: center; gap: 8px;"><strong style="color: #f8fafc; font-size: 1.2em;">${st.valor}</strong>${podeUpar}</div>
                </div>`;
        }
        htmlStatus += `</div>
            <div style="margin-top: 15px; background: #1e293b; border: 1px solid #334155; padding: 10px; border-radius: 8px; box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);">
                <div style="color: #94a3b8; font-size: 0.7em; font-weight: bold; text-transform: uppercase; margin-bottom: 8px;">🎲 Chances Secundárias</div>
                <div style="display: flex; justify-content: space-around; font-size: 0.9em;">
                    <div><span style="font-size: 1.2em;">💨</span> Esquiva: <strong style="color: #38bdf8;">${p.esquiva || 0}%</strong></div>
                    <div><span style="font-size: 1.2em;">⚔️</span> Atk Duplo: <strong style="color: #f87171;">${p.atk_duplo || 0}%</strong></div>
                </div>
            </div>
            <div style="margin-top: 10px; background: #1e293b; border: 1px solid #334155; padding: 10px; border-radius: 8px; box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);">
                <div style="color: #94a3b8; font-size: 0.7em; font-weight: bold; text-transform: uppercase; margin-bottom: 4px;">💼 Profissão</div>
                <div style="font-size: 0.95em; color: #fff;">${p.prof_nome || 'Nenhuma'} <span style="color: #fbbf24;">(Nível ${p.prof_lvl || 1})</span></div>
            </div>`;

        // --- ABA DE EQUIPAMENTOS ---
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
            let visualItem = eq.vazio ? `<span style="font-size: 1.4em; opacity: 0.3;">${eq.emoji}</span>` : 
                             (eq.icon.length > 5 && eq.icon.includes('.')) ? `<img src="${eq.icon}" style="width: 85%; height: 85%; object-fit: contain;">` : 
                             `<span style="font-size: 1.8em;">${eq.icon || eq.emoji}</span>`;

            // AGORA ABRE O MODAL AO INVÉS DE DESEQUIPAR DIRETO
            htmlSlots += `
                <div onclick="${!eq.vazio ? `abrirModalItem('${eq.slot}', 'equipado')` : ''}" 
                     style="position: absolute; ${Object.entries(pos).map(([k, v]) => `${k}:${v};`).join('')} 
                            width: 50px; height: 50px; background: ${corFundo}; border: 2px solid ${corBorda}; 
                            border-radius: 8px; display: flex; justify-content: center; align-items: center; 
                            cursor: ${eq.vazio ? 'default' : 'pointer'}; box-shadow: 0 4px 8px rgba(0,0,0,0.6);">
                    ${visualItem}
                </div>`;
        });

        const htmlEquips = `
            <div style="position: relative; width: 100%; height: 420px; margin-top: 15px; background: #020617; border-radius: 12px; border: 2px solid #334155; overflow: hidden; box-shadow: inset 0 0 30px rgba(0,0,0,0.9);">
                <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 100%; height: 100%; z-index: 0; pointer-events: none;">
                    <img src="https://github.com/user-attachments/assets/9a7300d0-63af-47bb-9f52-1fd99c40ed90" onerror="this.style.display='none'" style="width: 100%; height: 100%; object-fit: cover; opacity: 0.85;">
                </div>
                <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 50%; height: 95%; z-index: 1; display: flex; justify-content: center; align-items: center;">
                    <img id="avatar-equip-tab" src="${avatarLink}" onerror="this.src='https://github.com/user-attachments/assets/b0f8f158-3d54-46ef-b1df-9bbd9300609f'" style="width: 100%; height: 100%; object-fit: contain; filter: drop-shadow(0px 10px 15px rgba(0,0,0,0.9)); pointer-events: none;">
                </div>
                <div style="position: relative; width: 100%; height: 100%; z-index: 2;">${htmlSlots}</div>
            </div><p style="text-align:center; font-size:0.7em; color:#64748b; margin-top:8px;">Clique num equipamento para ver os detalhes.</p>`;

        // --- ABA DE INVENTÁRIO (AGORA COM SUB-ABAS) ---
        let htmlInv = `
            <div style="display: flex; gap: 5px; margin-top: 15px; margin-bottom: 15px; overflow-x: auto; padding-bottom: 5px;">
                <button onclick="filtrarMochila('todos')" id="btn-filtro-todos" style="flex: 1; padding: 6px; background: #3b82f6; color: #fff; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; font-size: 0.75em;">Todos</button>
                <button onclick="filtrarMochila('equips')" id="btn-filtro-equips" style="flex: 1; padding: 6px; background: #1e293b; color: #94a3b8; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; font-size: 0.75em;">Equips</button>
                <button onclick="filtrarMochila('materiais')" id="btn-filtro-materiais" style="flex: 1; padding: 6px; background: #1e293b; color: #94a3b8; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; font-size: 0.75em;">Materiais</button>
                <button onclick="filtrarMochila('usaveis')" id="btn-filtro-usaveis" style="flex: 1; padding: 6px; background: #1e293b; color: #94a3b8; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; font-size: 0.75em;">Usáveis</button>
            </div>
            <div id="grid-mochila" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(70px, 1fr)); gap: 8px;">
            </div>
            <p style="text-align:center; font-size:0.7em; color:#64748b; margin-top:10px;">Clique num item para interagir</p>
        `;

        // ==========================================
        // MONTAGEM DA TELA (INCLUINDO A CAIXA FLUTUANTE INVISÍVEL)
        // ==========================================
        const modalHtml = `
            <div id="modal-item" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); z-index:9999; justify-content:center; align-items:center;">
                <div style="background: linear-gradient(135deg, #1e293b, #0f172a); width: 85%; max-width: 350px; border-radius: 12px; border: 2px solid #f39c12; padding: 25px 20px; text-align: center; position: relative; box-shadow: 0 10px 25px rgba(0,0,0,0.9);">
                    <span onclick="fecharModalItem()" style="position: absolute; top: 10px; right: 15px; font-size: 1.5em; color: #94a3b8; cursor: pointer;">&times;</span>
                    <div id="modal-item-icon" style="font-size: 3.5em; margin-bottom: 10px; text-shadow: 0 0 15px rgba(255,255,255,0.2);">📦</div>
                    <h3 id="modal-item-nome" style="margin: 0 0 5px 0; color: #fff; font-size: 1.3em;">Nome</h3>
                    <span id="modal-item-raridade" style="font-size: 0.7em; text-transform: uppercase; padding: 2px 8px; border-radius: 4px; background: #334155; color: #cbd5e1; font-weight: bold;">Comum</span>
                    <p id="modal-item-desc" style="color: #94a3b8; font-size: 0.9em; margin: 15px 0; line-height: 1.4; min-height: 40px;">Descrição do item.</p>
                    <div id="modal-item-acoes" style="display: flex; gap: 10px; justify-content: center; margin-top: 20px;">
                        </div>
                </div>
            </div>
        `;

        conteudo.innerHTML = `
            ${modalHtml}
            <div style="background: linear-gradient(135deg, #0f172a, #020617); padding: 15px; border-radius: 12px; border: 1px solid #f39c12; text-align: center; margin-bottom: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">
                <h2 style="margin: 0 0 5px 0; color: #f39c12; font-size: 1.5em; text-shadow: 2px 2px 4px #000; text-transform: uppercase; letter-spacing: 1px;">${p.nome}</h2>
                <span style="background: #f39c12; color: #000; padding: 2px 10px; border-radius: 5px; font-weight: 900; font-size: 0.75em; text-transform: uppercase;">${infoClasse.emoji} ${infoClasse.nome}</span>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 15px;">
                <div style="background: #1e1e1e; padding: 8px 12px; border-radius: 8px; border-left: 3px solid #e74c3c; display: flex; justify-content: space-between; align-items: center;"><span style="color: #e74c3c; font-size: 0.7em; font-weight: bold;">❤️ HP</span><div style="font-size: 1em; color: #fff; font-weight: bold;">${p.hp_atual} <span style="font-size:0.7em; color:#7f1d1d;">/ ${p.hp_max}</span></div></div>
                <div style="background: #1e1e1e; padding: 8px 12px; border-radius: 8px; border-left: 3px solid #3b82f6; display: flex; justify-content: space-between; align-items: center;"><span style="color: #3b82f6; font-size: 0.7em; font-weight: bold;">💧 MP</span><div style="font-size: 1em; color: #fff; font-weight: bold;">${p.mp_atual} <span style="font-size:0.7em; color:#1e3a8a;">/ ${p.mp_max}</span></div></div>
                <div style="background: #1e1e1e; padding: 8px 12px; border-radius: 8px; border-left: 3px solid #f1c40f; display: flex; justify-content: space-between; align-items: center;"><span style="color: #f1c40f; font-size: 0.7em; font-weight: bold;">💰 OURO</span><div style="font-size: 1em; color: #fff; font-weight: bold;">${(p.gold||0).toLocaleString('pt-BR')}</div></div>
                <div style="background: #1e1e1e; padding: 8px 12px; border-radius: 8px; border-left: 3px solid #3498db; display: flex; justify-content: space-between; align-items: center;"><span style="color: #3498db; font-size: 0.7em; font-weight: bold;">⚡ ENE</span><div style="font-size: 1em; color: #fff; font-weight: bold;">${p.energy}</div></div>
            </div>

            <div style="background: #252525; padding: 12px; border-radius: 10px; border: 1px solid #333; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; font-size: 0.75em; margin-bottom: 5px;"><span style="color: #aaa; font-weight: bold;">Experiência (Nível <span style="color:#fff;">${p.level}</span>)</span><span style="color: #fff;">${(p.xp||0).toLocaleString('pt-BR')} / ${(p.xp_max||1).toLocaleString('pt-BR')}</span></div>
                <div style="width: 100%; height: 8px; background: #111; border-radius: 4px; border: 1px solid #000;"><div style="width: ${percentXP}%; height: 100%; background: linear-gradient(90deg, #8e44ad, #9b59b6);"></div></div>
            </div>

            <div style="display: flex; gap: 5px; background: #0f172a; padding: 5px; border-radius: 8px; border: 1px solid #1e293b; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                <button onclick="alternarAbaPerfil('status')" id="btn-perf-status" style="flex:1; padding:8px 5px; background:#1e293b; color:#fff; border:none; border-radius:6px; font-weight:bold; cursor:pointer; font-size:0.85em;">Atributos ${p.pontos_livres > 0 ? `<span style="background:#e74c3c; padding:2px 6px; border-radius:10px; font-size:0.8em; color:white;">${p.pontos_livres}</span>` : ''}</button>
                <button onclick="alternarAbaPerfil('equips')" id="btn-perf-equips" style="flex:1; padding:8px 5px; background:transparent; color:#94a3b8; border:none; border-radius:6px; font-weight:bold; cursor:pointer; font-size:0.85em;">Equipamentos</button>
                <button onclick="alternarAbaPerfil('inv')" id="btn-perf-inv" style="flex:1; padding:8px 5px; background:transparent; color:#94a3b8; border:none; border-radius:6px; font-weight:bold; cursor:pointer; font-size:0.85em;">Mochila</button>
            </div>

            <div id="conteudo-perf-status" style="display: block;">${htmlStatus}</div>
            <div id="conteudo-perf-equips" style="display: none;">${htmlEquips}</div>
            <div id="conteudo-perf-inv" style="display: none;">${htmlInv}</div>
            <button onclick="sairDoJogo()" style="width: 100%; padding: 12px; margin-top: 25px; background: linear-gradient(180deg, #c0392b 0%, #922b21 100%); border: 1px solid #e74c3c; color: white; border-radius: 8px; font-weight: bold; font-size: 0.95em; cursor: pointer; text-transform: uppercase;">🚪 Trocar Personagem</button>
        `;

        document.getElementById('perfil-carregando').style.display = 'none';
        conteudo.style.display = 'block';
        window._avatarAtualEldora = avatarLink;

        // Renderiza a mochila com filtro padrão
        filtrarMochila('todos');

    } catch (erro) {
        document.getElementById('perfil-msg-carregando').innerText = "⚠️ Erro ao carregar perfil. Verifique a conexão.";
    }
}

window.alternarAbaPerfil = function(abaID) {
    document.getElementById('conteudo-perf-status').style.display = 'none';
    document.getElementById('conteudo-perf-equips').style.display = 'none';
    document.getElementById('conteudo-perf-inv').style.display = 'none';
    
    ['btn-perf-status', 'btn-perf-equips', 'btn-perf-inv'].forEach(b => {
        document.getElementById(b).style.background = 'transparent';
        document.getElementById(b).style.color = '#94a3b8';
    });

    document.getElementById(`conteudo-perf-${abaID}`).style.display = 'block';
    document.getElementById(`btn-perf-${abaID}`).style.background = '#1e293b';
    document.getElementById(`btn-perf-${abaID}`).style.color = '#fff';

    if (abaID === 'equips' && window._avatarAtualEldora) {
        const imgCentro = document.getElementById('avatar-equip-tab');
        if (imgCentro) imgCentro.src = window._avatarAtualEldora;
    }
}

// ==========================================
// FILTROS DA MOCHILA
// ==========================================
window.filtrarMochila = function(filtro) {
    if(!perfilDadosGlobais) return;

    ['todos', 'equips', 'materiais', 'usaveis'].forEach(f => {
        document.getElementById(`btn-filtro-${f}`).style.background = '#1e293b';
        document.getElementById(`btn-filtro-${f}`).style.color = '#94a3b8';
    });
    document.getElementById(`btn-filtro-${filtro}`).style.background = '#3b82f6';
    document.getElementById(`btn-filtro-${filtro}`).style.color = '#fff';

    const container = document.getElementById('grid-mochila');
    let html = '';
    
    const itensFiltrados = perfilDadosGlobais.inventario.filter(i => {
        const t = (i.tipo || "").toLowerCase();
        if(filtro === 'todos') return true;
        if(filtro === 'equips') return ['weapon', 'armor', 'helmet', 'boots', 'ring', 'necklace', 'earring', 'equipamento'].includes(t);
        if(filtro === 'materiais') return ['material', 'forge', 'resource', 'crafting'].includes(t);
        if(filtro === 'usaveis') return ['potion', 'consumable', 'scroll', 'chest', 'box'].includes(t);
        return true;
    });

    if (itensFiltrados.length === 0) {
        html = `<p style="text-align: center; color: #64748b; padding: 20px; grid-column: 1 / -1;">Nenhum item nesta aba.</p>`;
    } else {
        itensFiltrados.forEach(item => {
            html += `
                <div onclick="abrirModalItem('${item.id}', 'mochila')" style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 10px 5px; text-align: center; cursor: pointer; position: relative; box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);">
                    <span style="position: absolute; top: -5px; right: -5px; background: #3b82f6; color: white; font-size: 0.65em; padding: 2px 5px; border-radius: 10px; font-weight: bold;">x${item.qtd}</span>
                    <div style="font-size: 1.8em; margin-bottom: 5px;">${item.emoji}</div>
                    <div style="color: #cbd5e1; font-size: 0.6em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: bold;">${item.nome}</div>
                </div>`;
        });
    }
    container.innerHTML = html;
}

// ==========================================
// CAIXA FLUTUANTE (MODAL) E AÇÕES
// ==========================================
window.abrirModalItem = function(idAlvo, origem) {
    if(!perfilDadosGlobais) return;
    let itemData = null;

    if (origem === 'mochila') {
        itemData = perfilDadosGlobais.inventario.find(i => i.id === idAlvo);
    } else if (origem === 'equipado') {
        itemData = perfilDadosGlobais.equipamentos.find(e => e.slot === idAlvo);
    }

    if (!itemData || itemData.vazio) return;

    // Preenche o Modal
    document.getElementById('modal-item-icon').innerText = itemData.emoji || itemData.icon || "📦";
    document.getElementById('modal-item-nome').innerText = itemData.nome;
    document.getElementById('modal-item-desc').innerText = itemData.desc || "Sem descrição.";
    
    const rari = document.getElementById('modal-item-raridade');
    rari.innerText = itemData.raridade || "Comum";
    // Cores de raridade
    const coresRaridade = {'comum': '#94a3b8', 'incomum': '#22c55e', 'raro': '#3b82f6', 'epico': '#a855f7', 'lendario': '#eab308'};
    rari.style.color = coresRaridade[(itemData.raridade||'comum').toLowerCase()] || '#cbd5e1';

    // Cria os Botões de Ação
    let botoesHtml = '';
    if (origem === 'mochila') {
        const t = (itemData.tipo || "").toLowerCase();
        if (['weapon', 'armor', 'helmet', 'boots', 'ring', 'necklace', 'earring', 'equipamento'].includes(t)) {
            botoesHtml = `<button onclick="usarOuEquiparItem('${itemData.id}')" style="flex:1; padding:10px; background:#10b981; color:white; border:none; border-radius:6px; font-weight:bold; cursor:pointer;">Equipar</button>`;
        } else if (['potion', 'consumable'].includes(t)) {
            botoesHtml = `<button onclick="usarOuEquiparItem('${itemData.id}')" style="flex:1; padding:10px; background:#3b82f6; color:white; border:none; border-radius:6px; font-weight:bold; cursor:pointer;">Usar</button>`;
        }
    } else if (origem === 'equipado') {
        botoesHtml = `<button onclick="desequiparItem('${itemData.slot}')" style="flex:1; padding:10px; background:#ef4444; color:white; border:none; border-radius:6px; font-weight:bold; cursor:pointer;">Remover</button>`;
    }
    
    botoesHtml += `<button onclick="fecharModalItem()" style="flex:1; padding:10px; background:#334155; color:white; border:none; border-radius:6px; font-weight:bold; cursor:pointer;">Cancelar</button>`;
    
    document.getElementById('modal-item-acoes').innerHTML = botoesHtml;
    document.getElementById('modal-item').style.display = 'flex'; // Mostra o Modal
}

window.fecharModalItem = function() {
    document.getElementById('modal-item').style.display = 'none';
}

// ==========================================
// AÇÕES DO BACKEND
// ==========================================
window.distribuirPonto = async function(stat) {
    const charId = localStorage.getItem("jogadorEldoraID");
    try {
        const res = await fetch('/api/personagem/distribuir_ponto', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_id: charId, stat: stat }) });
        const data = await res.json();
        if(data.sucesso) carregarMeuPerfil(); else alert("Aviso: " + data.erro);
    } catch(e) { alert("⚠️ ERRO: " + e.message); }
}

window.desequiparItem = async function(slot) {
    fecharModalItem();
    const charId = localStorage.getItem("jogadorEldoraID");
    try {
        const res = await fetch('/api/personagem/desequipar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_id: charId, slot: slot }) });
        const data = await res.json();
        if(data.sucesso) { carregarMeuPerfil(); setTimeout(() => alternarAbaPerfil('equips'), 200); } else { alert("Aviso: " + data.erro); }
    } catch(e) { alert("⚠️ ERRO: " + e.message); }
}

window.usarOuEquiparItem = async function(itemId) {
    fecharModalItem();
    const charId = localStorage.getItem("jogadorEldoraID");
    try {
        const res = await fetch('/api/personagem/equipar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_id: charId, item_id: itemId }) });
        const data = await res.json();
        if(data.sucesso) { carregarMeuPerfil(); setTimeout(() => alternarAbaPerfil('equips'), 300); } else { alert("Aviso: " + data.erro); }
    } catch(e) { alert("⚠️ ERRO: " + e.message); }
}