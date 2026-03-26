// ==========================================
// inventario_modal.js - Lógica de Itens e Status
// ==========================================

// Injeta a Caixa Flutuante invisível na página assim que o script carrega
document.addEventListener("DOMContentLoaded", () => {
    const modalHtml = `
        <div id="modal-item-eldora" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); z-index:9999; justify-content:center; align-items:center; backdrop-filter: blur(3px);">
            <div style="background: linear-gradient(135deg, #1e293b, #0f172a); width: 85%; max-width: 350px; border-radius: 12px; border: 2px solid #f39c12; padding: 25px 20px; text-align: center; position: relative; box-shadow: 0 10px 25px rgba(0,0,0,0.9);">
                <span onclick="fecharModalItem()" style="position: absolute; top: 10px; right: 15px; font-size: 1.5em; color: #94a3b8; cursor: pointer;">&times;</span>
                
                <div id="modal-item-icon" style="font-size: 3.5em; margin-bottom: 5px; text-shadow: 0 0 15px rgba(255,255,255,0.2);">📦</div>
                <h3 id="modal-item-nome" style="margin: 0 0 5px 0; color: #fff; font-size: 1.2em;">Nome</h3>
                <span id="modal-item-raridade" style="font-size: 0.7em; text-transform: uppercase; padding: 2px 8px; border-radius: 4px; background: #334155; font-weight: bold;">Comum</span>
                
                <div id="modal-item-stats" style="display: flex; flex-wrap: wrap; justify-content: center; gap: 6px; margin-top: 15px;"></div>

                <p id="modal-item-desc" style="color: #94a3b8; font-size: 0.85em; margin: 15px 0; line-height: 1.4; min-height: 40px; border-top: 1px solid #334155; padding-top: 10px;">Descrição do item.</p>
                
                <div id="modal-item-acoes" style="display: flex; gap: 10px; justify-content: center; margin-top: 15px;"></div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
});

// Abre o Modal, lê o Refino e os Status Reais
window.abrirModalItem = function(idAlvo, origem) {
    if(!window.perfilDadosGlobais) return;
    let itemData = null;

    if (origem === 'mochila') itemData = window.perfilDadosGlobais.inventario.find(i => i.id === idAlvo);
    else if (origem === 'equipado') itemData = window.perfilDadosGlobais.equipamentos.find(e => e.slot === idAlvo);

    if (!itemData || itemData.vazio) return;

    // 1. NOME COM REFINO
    const refinoTxt = itemData.refino > 0 ? ` [+${itemData.refino}]` : '';
    document.getElementById('modal-item-nome').innerText = itemData.nome + refinoTxt;
    
    // 2. ÍCONE E DESCRIÇÃO
    document.getElementById('modal-item-icon').innerHTML = itemData.emoji || itemData.icon || "📦";
    document.getElementById('modal-item-desc').innerText = itemData.desc || "Sem descrição.";
    
    // 3. RARIDADE
    const rari = document.getElementById('modal-item-raridade');
    rari.innerText = itemData.raridade || "Comum";
    const coresRaridade = {'comum': '#94a3b8', 'incomum': '#22c55e', 'bom': '#22c55e', 'raro': '#3b82f6', 'epico': '#a855f7', 'lendario': '#eab308', 'unico': '#ef4444', 'mitico': '#00f2fe'};
    rari.style.color = coresRaridade[(itemData.raridade||'comum').toLowerCase()] || '#cbd5e1';

    // 4. TRADUTOR DE STATUS E EMOJIS
    let statsHtml = '';
    const mapEmojis = {
        'vida': '❤️', 'hp': '❤️', 'defesa': '🛡️', 'defense': '🛡️',
        'sorte': '🍀', 'luck': '🍀', 'agilidade': '🏃', 'initiative': '🏃',
        'forca': '💪', 'inteligencia': '🧠', 'furia': '🔥', 'precisao': '🎯',
        'letalidade': '💀', 'carisma': '😎', 'foco': '🧘', 'bushido': '🥷',
        'dmg': '⚔️', 'attack': '⚔️'
    };

    if (itemData.stats && Object.keys(itemData.stats).length > 0) {
        for (const [key, valObj] of Object.entries(itemData.stats)) {
            // A forja guarda como {"value": 16}, então extraímos o número
            let val = (typeof valObj === 'object' && valObj !== null) ? valObj.value : valObj;
            
            // Ocultar o DMG genérico se o item já tiver o atributo da classe (como Letalidade) para ficar limpo
            if (key.toLowerCase() === 'dmg' && Object.keys(itemData.stats).length > 1) continue;

            const emoji = mapEmojis[key.toLowerCase()] || '✨';
            const nomeStat = key.replace('_', ' ').toUpperCase();
            statsHtml += `<span style="background: #020617; padding: 4px 8px; border-radius: 6px; font-size: 0.8em; color: #fff; border: 1px solid #3f3f46; box-shadow: 0 2px 4px rgba(0,0,0,0.5);">${emoji} ${nomeStat}: +${val}</span>`;
        }
    } else if (['weapon', 'armor', 'helmet', 'boots', 'ring', 'necklace', 'earring', 'equipamento'].includes(itemData.tipo)) {
        statsHtml = `<span style="color: #64748b; font-size: 0.8em;">Sem atributos base</span>`;
    }
    document.getElementById('modal-item-stats').innerHTML = statsHtml;

    // 5. BOTÕES DE AÇÃO
    let botoesHtml = '';
    if (origem === 'mochila') {
        const t = (itemData.tipo || "").toLowerCase();
        if (['weapon', 'armor', 'helmet', 'boots', 'ring', 'necklace', 'earring', 'equipamento'].includes(t)) {
            botoesHtml = `<button onclick="usarOuEquiparItem('${itemData.id}')" style="flex:1; padding:10px; background:#10b981; color:white; border:none; border-radius:6px; font-weight:bold; cursor:pointer;">Equipar</button>`;
        } else if (['potion', 'consumable', 'scroll'].includes(t)) {
            botoesHtml = `<button onclick="usarOuEquiparItem('${itemData.id}')" style="flex:1; padding:10px; background:#3b82f6; color:white; border:none; border-radius:6px; font-weight:bold; cursor:pointer;">Usar</button>`;
        }
    } else if (origem === 'equipado') {
        botoesHtml = `<button onclick="desequiparItem('${itemData.slot}')" style="flex:1; padding:10px; background:#ef4444; color:white; border:none; border-radius:6px; font-weight:bold; cursor:pointer;">Remover</button>`;
    }
    botoesHtml += `<button onclick="fecharModalItem()" style="flex:1; padding:10px; background:#334155; color:white; border:none; border-radius:6px; font-weight:bold; cursor:pointer;">Fechar</button>`;
    
    document.getElementById('modal-item-acoes').innerHTML = botoesHtml;
    document.getElementById('modal-item-eldora').style.display = 'flex';
}

window.fecharModalItem = function() {
    document.getElementById('modal-item-eldora').style.display = 'none';
}

// Ações no Backend
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
        if(data.sucesso) { carregarMeuPerfil(); setTimeout(() => alternarAbaPerfil('equips'), 200); } else alert("Aviso: " + data.erro);
    } catch(e) { alert("⚠️ ERRO: " + e.message); }
}

window.usarOuEquiparItem = async function(itemId) {
    fecharModalItem();
    const charId = localStorage.getItem("jogadorEldoraID");
    try {
        const res = await fetch('/api/personagem/equipar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_id: charId, item_id: itemId }) });
        const data = await res.json();
        if(data.sucesso) { carregarMeuPerfil(); setTimeout(() => alternarAbaPerfil('equips'), 300); } else alert("Aviso: " + data.erro);
    } catch(e) { alert("⚠️ ERRO: " + e.message); }
}