// ==========================================
// BATALHA PVE (GRUPO/TURNOS)
// ==========================================

let pveBatalhaAtual = null;

// Escutando Eventos Globais
if (window.socket) {
    window.socket.on('batalha_iniciada', (dados) => {
        let meuId = localStorage.getItem("jogadorEldoraID");
        if (!dados.jogadores || !dados.jogadores[meuId]) return;

        console.log("⚔️ Batalha PvE Iniciada:", dados);
        pveBatalhaAtual = dados;
        
        // Pausar movimentação do jogador no mapa
        if (window.jogoEldora && window.jogoEldora.scene) {
            let cena = window.jogoEldora.scene.keys.Principal;
            if(cena) cena.isMoving = false;
        }

        abrirTelaBatalhaPvE(dados);
    });

    window.socket.on('atualizacao_batalha', (dados) => {
        if (!pveBatalhaAtual || pveBatalhaAtual.battle_id !== dados.battle_id) return;
        
        // Atualiza os HPs e MPs
        pveBatalhaAtual.monstro.hp = dados.monstro.hp;
        
        for(let pid in dados.jogadores) {
            if(pveBatalhaAtual.jogadores[pid]) {
                pveBatalhaAtual.jogadores[pid].hp = dados.jogadores[pid].hp;
                pveBatalhaAtual.jogadores[pid].mp = dados.jogadores[pid].mp;
                pveBatalhaAtual.jogadores[pid].is_dead = dados.jogadores[pid].is_dead;
            }
        }
        
        renderizarEstadoPvE();
        
        // Adiciona Logs
        const logBox = document.getElementById('pve-log-content');
        if (dados.logs && dados.logs.length > 0) {
            dados.logs.forEach(msg => {
                const sp = document.createElement('div');
                sp.innerText = msg;
                sp.style.margin = "2px 0";
                if(msg.includes('CRÍTICO')) sp.style.color = '#ef4444';
                else if(msg.includes('💚')) sp.style.color = '#10b981';
                else sp.style.color = '#e2e8f0';
                logBox.appendChild(sp);
            });
            document.getElementById('pve-log-box').scrollTop = document.getElementById('pve-log-box').scrollHeight;
        }

        // Se a batalha acabou, mostra os botões de voltar
        if (dados.vitoria || dados.derrota) {
            document.getElementById('pve-menu-botoes').style.display = 'none';
        }
    });

    window.socket.on('batalha_encerrada', (dados) => {
        if (!pveBatalhaAtual || pveBatalhaAtual.battle_id !== dados.battle_id) return;
        
        const logBox = document.getElementById('pve-log-content');
        const sp = document.createElement('div');
        sp.innerText = dados.msg_loot;
        sp.style.fontWeight = 'bold';
        sp.style.color = dados.vitoria ? '#facc15' : '#ef4444';
        sp.style.margin = "10px 0";
        logBox.appendChild(sp);
        document.getElementById('pve-log-box').scrollTop = document.getElementById('pve-log-box').scrollHeight;

        document.getElementById('pve-menu-botoes').style.display = 'none';
        document.getElementById('pve-botoes-fim-batalha').style.display = 'block';
    });
}

function abrirTelaBatalhaPvE(dados) {
    document.getElementById('tela-pve-global').style.display = 'flex';
    document.getElementById('pve-menu-botoes').style.display = 'grid';
    document.getElementById('pve-botoes-fim-batalha').style.display = 'none';
    document.getElementById('pve-log-content').innerHTML = '<div style="color:#facc15;">Batalha começou!</div>';
    
    // Configura o Monstro
    document.getElementById('nome-monstro-pve').innerText = dados.monstro.nome || 'Monstro';
    document.getElementById('lvl-monstro-pve').innerText = `LV.${dados.monstro.nivel || '?'}`;
    
    // Tentativa de puxar imagem. Se vier de 'dados.monstro.skin', a gente monta a url. 
    // Em eventos_invasao.py, o dict costuma ter 'skin' ou id.
    let mobSkin = dados.monstro.skin || dados.monstro.id || 'slime_verde';
    document.getElementById('sprite-monstro-pve').src = `https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/mob/invasao/${mobSkin}.png`;
    
    renderizarEstadoPvE();
}

function renderizarEstadoPvE() {
    if(!pveBatalhaAtual) return;
    
    // Monstro HP
    const m = pveBatalhaAtual.monstro;
    const hpMobPct = Math.max(0, m.hp / m.max_hp) * 100;
    document.getElementById('bar-hp-monstro-pve').style.width = hpMobPct + '%';
    document.getElementById('val-hp-monstro-pve').innerText = `${Math.floor(m.hp)}/${m.max_hp}`;
    
    // Jogadores
    const container = document.getElementById('pve-grupo-container');
    container.innerHTML = '';
    
    for (let pid in pveBatalhaAtual.jogadores) {
        let p = pveBatalhaAtual.jogadores[pid];
        let pctHp = Math.max(0, p.hp / p.max_hp) * 100;
        let pctMp = Math.max(0, p.mp / p.max_mp) * 100;
        
        let el = document.createElement('div');
        el.style.background = p.is_dead ? 'rgba(50, 0, 0, 0.8)' : 'rgba(15, 23, 42, 0.9)';
        el.style.border = '1px solid #3b82f6';
        el.style.borderRadius = '8px';
        el.style.padding = '4px';
        el.style.display = 'flex';
        el.style.alignItems = 'center';
        el.style.gap = '8px';
        el.style.width = '180px';
        
        el.innerHTML = `
            <img src="${p.avatar}" style="width: 32px; height: 32px; border-radius: 4px; filter: ${p.is_dead ? 'grayscale(100%)' : 'none'};">
            <div style="flex: 1;">
                <div style="font-size: 0.65em; color: #fff; font-weight: bold;">${p.nome}</div>
                
                <div style="height: 6px; background: #020617; border-radius: 2px; margin-bottom: 2px; position: relative;">
                    <div style="width: ${pctHp}%; height: 100%; background: #10b981;"></div>
                </div>
                
                <div style="height: 4px; background: #020617; border-radius: 2px; position: relative;">
                    <div style="width: ${pctMp}%; height: 100%; background: #3b82f6;"></div>
                </div>
            </div>
        `;
        container.appendChild(el);
    }
}

function executarAcaoPvE(acao, skill_id = null) {
    if (!pveBatalhaAtual) return;
    
    window.socket.emit('enviarAcaoBatalhaPvE', {
        battle_id: pveBatalhaAtual.battle_id,
        player_id: localStorage.getItem("jogadorEldoraID"),
        acao: acao,
        skill_id: skill_id
    });
    
    document.getElementById('modal-magias-pve').style.display = 'none';
}

function abrirMenuMagiasPvE() {
    let meuId = localStorage.getItem("jogadorEldoraID");
    if (!meuId || !pveBatalhaAtual) return;
    
    let meusDados = pveBatalhaAtual.jogadores[meuId];
    if (!meusDados || !meusDados.skills) {
        alert("Nenhuma magia encontrada.");
        return;
    }
    
    const lista = document.getElementById('lista-magias-pve');
    lista.innerHTML = '';
    
    for (const [s_id, s_data] of Object.entries(meusDados.skills)) {
        if (s_id === "ataque_basico") continue; // Pula ataque basico se tiver nas skills
        
        let div = document.createElement('div');
        div.style.background = '#1e293b';
        div.style.padding = '8px';
        div.style.borderRadius = '6px';
        div.style.display = 'flex';
        div.style.justifyContent = 'space-between';
        div.style.alignItems = 'center';
        
        let nomeSkill = s_data.name || s_id.replace(/_/g, ' ').toUpperCase();
        div.innerHTML = `
            <div>
                <strong style="color:#60a5fa; font-size: 0.9em;">${nomeSkill}</strong>
                <br>
                <span style="font-size: 0.75em; color: #94a3b8;">${s_data.mana_cost || 0} MP</span>
            </div>
            <button class="modern-btn" onclick="executarAcaoPvE('magia', '${s_id}')" style="padding: 4px 10px; font-size: 0.8em;">Usar</button>
        `;
        lista.appendChild(div);
    }
    
    document.getElementById('modal-magias-pve').style.display = 'flex';
}

function abrirMenuItensPvE() {
    alert("Função de inventário na batalha chegará em breve!");
}

function sairDaArenaPvE() {
    document.getElementById('tela-pve-global').style.display = 'none';
    pveBatalhaAtual = null;
    
    // Puxa status atualizados
    if (typeof carregarMeuPerfil === 'function') carregarMeuPerfil();
}
