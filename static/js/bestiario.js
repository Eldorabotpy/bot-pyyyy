window.abrirCodiceHunter = async function() {
    const charId = localStorage.getItem("jogadorEldoraID");
    
    let modal = document.getElementById('modal-bestiario');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'modal-bestiario';
        modal.style = "position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.95); z-index:100000; display:flex; align-items:center; justify-content:center; font-family: 'Cinzel', serif;";
        document.body.appendChild(modal);
    }
    
    modal.innerHTML = `<div style="color:#d4af37; font-size:1.5em; text-shadow: 2px 2px #000; text-align: center;">📜<br>Lendo Pergaminhos...</div>`;
    modal.style.display = 'flex';

    try {
        const res = await fetch(`/api/bestiario/${charId}`);
        const dados = await res.json();

        let html = `
            <div id="container-livro" style="background: url('https://www.transparenttextures.com/patterns/wood-pattern.png') #1a120b; border: 3px solid #d4af37; width: 95%; max-width: 600px; height: 85vh; border-radius: 12px; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.9); position: relative;">
                
                <div style="background: linear-gradient(to bottom, #3e2723, #1a120b); padding: 15px; text-align: center; border-bottom: 2px solid #d4af37; position: relative;">
                    <h2 style="margin:0; color:#d4af37; font-family: 'Cinzel', serif; letter-spacing: 1px; font-size: 1.4em; text-shadow: 2px 2px 4px #000;">📖 CÓDICE DE ELDORA</h2>
                    <span onclick="document.getElementById('modal-bestiario').style.display='none'" style="position:absolute; top:10px; right:15px; cursor:pointer; color:#ef4444; font-size:28px; font-weight:bold; text-shadow: 1px 1px #000;">&times;</span>
                </div>
                
                <div style="background: rgba(0,0,0,0.6); border-bottom: 1px solid #5d4037; padding: 10px; display: flex; overflow-x: auto; gap: 10px; white-space: nowrap; align-items: center; min-height: 60px; scrollbar-width: none;">
                    ${Object.keys(dados).map((reg) => `
                        <button onclick="window.renderizarCategoriaCodice('${reg}')" style="background: #3e2723; border: 1px solid #d4af37; border-radius: 20px; padding: 8px 15px; color: #f5f5f5; font-family: 'Cinzel', serif; font-size: 0.85em; font-weight: bold; cursor: pointer; flex-shrink: 0; box-shadow: 0 4px 6px rgba(0,0,0,0.5); transition: 0.2s;">
                            📍 ${reg.replace(/_/g, ' ').toUpperCase()}
                        </button>
                    `).join('')}
                </div>

                <div id="grid-monstros" style="flex:1; padding: 15px; overflow-y: auto; background: rgba(0,0,0,0.4); display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 12px; align-content: start;">
                    <div style="grid-column: 1/-1; text-align: center; margin-top: 40px; color: #d4af37; font-family: 'Cinzel', serif; font-size: 1.1em; opacity: 0.8;">
                        ⬅️ Deslize o menu de regiões para os lados e selecione uma.<br><br>Clique nas criaturas para abrir o Dossiê!
                    </div>
                </div>
            </div>
        `;
        modal.innerHTML = html;
        window.dadosCodiceCache = dados;

    } catch (e) {
        modal.innerHTML = `<div style="color:#ff4757; background: #000; padding: 20px; border-radius: 10px; text-align:center;">Erro ao carregar o códice.<br>${e.message}<br><button style="padding:10px 20px; margin-top:10px;" onclick="document.getElementById('modal-bestiario').style.display='none'">Fechar</button></div>`;
    }
};

window.renderizarCategoriaCodice = function(regiao) {
    const grid = document.getElementById('grid-monstros');
    const monstros = window.dadosCodiceCache[regiao];
    
    if (!monstros || monstros.length === 0) {
        grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: #8d6e63; margin-top: 20px;">Nenhuma criatura registrada.</div>`;
        return;
    }

    // Transformamos o Card num botão clicável que passa a Região e o ID do Mob
    grid.innerHTML = monstros.map(mob => {
        const n = mob.nivel_conhecimento;
        const estiloImg = n === 0 ? "filter: brightness(0) drop-shadow(0 0 5px #000);" : "filter: drop-shadow(0 4px 6px rgba(0,0,0,0.8));";
        const bordaColor = n === 3 ? "#f1c40f" : n === 2 ? "#94a3b8" : "#5d4037";
        const bgCard = n === 3 ? "linear-gradient(to bottom, rgba(241, 196, 15, 0.15), rgba(0,0,0,0.8))" : "linear-gradient(to bottom, rgba(255,255,255,0.05), rgba(0,0,0,0.8))";

        return `
            <div onclick="window.abrirDetalhesMob('${regiao}', '${mob.id}')" style="cursor: pointer; background: ${bgCard}; border: 1px solid ${bordaColor}; border-radius: 10px; padding: 12px 8px; text-align: center; position: relative; box-shadow: inset 0 0 20px rgba(0,0,0,0.8), 0 4px 8px rgba(0,0,0,0.5); transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                
                <div style="height: 75px; display: flex; align-items: center; justify-content: center; margin-bottom: 8px;">
                    <img src="${mob.imagem}" style="max-width: 70px; max-height: 70px; object-fit: contain; ${estiloImg}">
                </div>
                
                <div style="color: ${n >= 1 ? '#fff' : '#8d6e63'}; font-family: 'Arial', sans-serif; font-size: 0.75em; font-weight: 900; margin-bottom: 5px; min-height: 28px; display: flex; align-items: center; justify-content: center; text-transform: uppercase; letter-spacing: 0.5px; text-shadow: 1px 1px 2px #000;">
                    ${mob.nome}
                </div>
                
                <div style="font-size: 0.75em; color: #d4af37; background: rgba(0,0,0,0.6); border: 1px solid #d4af37; border-radius: 12px; padding: 2px 10px; font-weight: bold;">
                    ⚔️ Abates: ${mob.abates}
                </div>

                ${n === 3 ? `<div style="position: absolute; top: -10px; right: -10px; background: #000; border: 2px solid #f1c40f; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-size: 12px; box-shadow: 0 0 10px #f1c40f;" title="Maestria">👑</div>` : ''}
            </div>
        `;
    }).join('');
};

// ==========================================
// 📖 NOVO: PÁGINA DO DOSSIÊ DA CRIATURA
// ==========================================
window.abrirDetalhesMob = function(regiao, mobId) {
    const monstros = window.dadosCodiceCache[regiao];
    const mob = monstros.find(m => m.id === mobId);
    if(!mob) return;

    const n = mob.nivel_conhecimento;
    const estiloImg = n === 0 ? "filter: brightness(0) drop-shadow(0 0 10px #000);" : "filter: drop-shadow(0 10px 20px rgba(0,0,0,0.9));";

    // Constrói a lista de Drops
    let dropsHtml = "";
    if (n >= 3) {
        if (mob.drops && mob.drops.length > 0) {
            // Desenha item a item (você pode futuramente linkar com a foto do item)
            dropsHtml = mob.drops.map(d => `
                <div style="background: rgba(0,0,0,0.8); border: 1px solid #334155; padding: 8px; border-radius: 5px; margin-bottom: 5px; display: flex; justify-content: space-between; font-family: Arial;">
                    <span style="color:#e2e8f0;">📦 ${d.item_id.replace(/_/g, ' ').toUpperCase()}</span>
                    <span style="color:#2ecc71; font-weight: bold;">${d.drop_chance}%</span>
                </div>
            `).join('');
        } else {
            dropsHtml = `<div style="color:#94a3b8; font-style:italic;">Esta criatura não carrega tesouros.</div>`;
        }
    } else {
         dropsHtml = `<div style="color:#ef4444; font-size: 0.9em; border: 1px dashed #ef4444; padding: 10px; border-radius: 5px;">👑 Alcance a Maestria (50 abates) para revelar a Tabela de Drops.</div>`;
    }

    // Cria o painel de detalhes que vai deslizar por cima
    const painel = document.createElement('div');
    painel.id = "painel-detalhes-mob";
    painel.style = "position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: #1a120b; z-index: 10; display: flex; flex-direction: column; box-sizing: border-box; animation: slideIn 0.3s ease-out;";

    painel.innerHTML = `
        <div style="background: linear-gradient(to right, #3e2723, #1a120b); display:flex; justify-content:space-between; align-items:center; border-bottom: 2px solid #d4af37; padding: 15px;">
            <button onclick="document.getElementById('painel-detalhes-mob').remove()" style="background:transparent; border:none; color:#d4af37; font-size:24px; cursor:pointer; text-shadow: 1px 1px #000;">◀ Voltar</button>
            <h2 style="color:#d4af37; font-family:'Cinzel', serif; margin:0; font-size: 1.2em; text-shadow: 2px 2px #000;">Dossiê da Criatura</h2>
            <div style="width:70px;"></div> </div>

        <div style="flex:1; overflow-y:auto; padding: 20px; background: url('https://www.transparenttextures.com/patterns/dark-leather.png'); display:flex; flex-direction:column; align-items:center;">
            
            <h1 style="color:#fff; font-family:'Cinzel', serif; margin: 0 0 15px 0; font-size: 1.6em; text-align: center; text-transform: uppercase;">${mob.nome}</h1>
            
            <div style="width: 100%; display: flex; justify-content: center; margin-bottom: 20px;">
                <img src="${mob.imagem}" style="width: 150px; height: 150px; object-fit: contain; ${estiloImg}">
            </div>

            <div style="background: rgba(0,0,0,0.7); border: 2px solid #5d4037; border-radius: 10px; width: 100%; max-width: 400px; padding: 15px; box-sizing: border-box; margin-bottom: 20px; box-shadow: 0 5px 15px rgba(0,0,0,0.8);">
                <h3 style="color:#d4af37; margin-top:0; font-size:16px; text-align:center; border-bottom: 1px solid #5d4037; padding-bottom: 5px;">🛡️ ATRIBUTOS BASE</h3>
                
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; font-size:15px; color:#fff; text-align:center; font-weight: bold; font-family: Arial;">
                    <div style="background:#2b1d12; padding:10px; border-radius:5px; border-left: 3px solid #e74c3c;">❤️ HP: ${mob.hp}</div>
                    <div style="background:#2b1d12; padding:10px; border-radius:5px; border-left: 3px solid #c0392b;">⚔️ ATK: ${mob.atk}</div>
                    <div style="background:#2b1d12; padding:10px; border-radius:5px; border-left: 3px solid #3498db;">🛡️ DEF: ${mob.def}</div>
                    <div style="background:#2b1d12; padding:10px; border-radius:5px; border-left: 3px solid #f39c12;">🏃 AGI: ${mob.agi}</div>
                    <div style="background:#2b1d12; padding:10px; border-radius:5px; border-left: 3px solid #2ecc71; grid-column: span 2;">🍀 SORTE: ${mob.sorte}</div>
                </div>
                
                <div style="margin-top: 15px; background: #000; border: 1px solid #f1c40f; color: #f1c40f; text-align: center; padding: 8px; border-radius: 5px; font-weight: bold;">
                    💀 REGISTRO DE ABATES: ${mob.abates}
                </div>
            </div>

            <div style="background: rgba(0,0,0,0.7); border: 2px solid #5d4037; border-radius: 10px; width: 100%; max-width: 400px; padding: 15px; box-sizing: border-box; margin-bottom: 20px; box-shadow: 0 5px 15px rgba(0,0,0,0.8);">
                <h3 style="color:#d4af37; margin-top:0; font-size:16px; text-align:center; border-bottom: 1px solid #5d4037; padding-bottom: 5px;">💰 TESOUROS E DROPS</h3>
                ${dropsHtml}
            </div>

        </div>
    `;

    // Injeta o CSS da animação de deslizar e a tela do monstro
    const styleBlock = document.createElement('style');
    styleBlock.innerHTML = `@keyframes slideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }`;
    painel.appendChild(styleBlock);
    
    document.getElementById('container-livro').appendChild(painel);
}