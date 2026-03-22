// ==========================================
// SISTEMA DE COMBATE ANIMADO (WEB APP)
// ==========================================
async function iniciarCacadaApp(playerAvatar) {
    const conteudo = document.getElementById('aba-reino');
    const charId = localStorage.getItem("jogadorEldoraID");

    // Tela de Carregamento da Arena
    conteudo.innerHTML = `
        <div style="height: 300px; display: flex; flex-direction: column; justify-content: center; align-items: center;">
            <div style="font-size: 3em; animation: pulseRing 1s infinite;">⚔️</div>
            <h3 style="color: #e74c3c; margin-top: 15px;">Procurando oponentes...</h3>
        </div>
    `;

    try {
        const res = await fetch('/api/cacar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: charId })
        });
        const dados = await res.json();

        if (dados.erro) {
            exibirAlertaCustom("Aviso", dados.erro, false);
            carregarReino();
            return;
        }

        // Desenha a Arena de Combate
        conteudo.innerHTML = `
            <div style="background: url('https://placehold.co/600x400/111/222?text=Arena') center/cover; border-radius: 12px; padding: 15px; border: 2px solid #e74c3c; position: relative; overflow: hidden; margin-bottom: 20px;">
                <div style="position: absolute; top:0; left:0; width:100%; height:100%; background: rgba(0,0,0,0.6);"></div>
                
                <div style="position: relative; display: flex; justify-content: space-between; align-items: flex-end; height: 160px; padding-bottom: 10px;">
                    
                    <div style="text-align: center; width: 40%;">
                        <div style="width: 100%; height: 12px; background: #333; border-radius: 6px; border: 1px solid #000; margin-bottom: 5px; overflow: hidden;">
                            <div id="bar-hp-player" style="width: 100%; height: 100%; background: #2ecc71; transition: 0.3s;"></div>
                        </div>
                        <img src="${playerAvatar}" style="width: 80px; height: 80px; border-radius: 8px; border: 2px solid #2ecc71; object-fit: cover; object-position: top;">
                        <div style="color: white; font-weight: bold; font-size: 0.85em; margin-top: 5px;">Você</div>
                    </div>

                    <div style="font-size: 2.5em; color: #e74c3c; font-weight: 900; text-shadow: 2px 2px 0 #000;">VS</div>

                    <div style="text-align: center; width: 40%;">
                        <div style="width: 100%; height: 12px; background: #333; border-radius: 6px; border: 1px solid #000; margin-bottom: 5px; overflow: hidden;">
                            <div id="bar-hp-mob" style="width: 100%; height: 100%; background: #e74c3c; transition: 0.3s;"></div>
                        </div>
                        <img src="${dados.mob.imagem}" onerror="this.src='https://placehold.co/100x100/333/e74c3c?text=👹'" style="width: 80px; height: 80px; border-radius: 8px; border: 2px solid #e74c3c; object-fit: cover;">
                        <div style="color: white; font-weight: bold; font-size: 0.85em; margin-top: 5px;">${dados.mob.nome}</div>
                    </div>
                </div>
            </div>

            <div style="background: #020617; border: 1px solid #1e293b; border-radius: 8px; padding: 15px; height: 150px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px;" id="combat-log-box">
                <div style="color: #f1c40f; text-align: center; font-weight: bold; margin-bottom: 5px;">Um ${dados.mob.nome} selvagem apareceu!</div>
            </div>
            
            <button id="btn-voltar-combate" onclick="carregarReino()" style="width: 100%; background: #1a1a1a; padding: 12px; border: 1px solid #333; color: white; border-radius: 8px; margin-top: 15px; display: none; cursor: pointer;">⬅️ Voltar para Região</button>
        `;

        // ----------------------------------------------------
        // ANIMAÇÃO DO LOG
        // ----------------------------------------------------
        const logBox = document.getElementById('combat-log-box');
        let playerHpAtual = dados.player.hp_max;
        let mobHpAtual = dados.mob.hp_max;

        let index = 0;
        const intervaloCombate = setInterval(() => {
            if (index >= dados.log.length) {
                clearInterval(intervaloCombate);
                finalizarAnimacaoCombate(dados);
                return;
            }

            const acao = dados.log[index];
            const pElem = document.createElement('div');
            
            if (acao.atacante === "player") {
                pElem.style.color = "#2ecc71";
                pElem.innerHTML = acao.texto;
                mobHpAtual -= acao.dano;
                const pctMob = Math.max(0, (mobHpAtual / dados.mob.hp_max) * 100);
                document.getElementById('bar-hp-mob').style.width = pctMob + '%';
            } else if (acao.atacante === "mob") {
                pElem.style.color = "#e74c3c";
                pElem.innerHTML = acao.texto;
                playerHpAtual -= acao.dano;
                const pctPlayer = Math.max(0, (playerHpAtual / dados.player.hp_max) * 100);
                document.getElementById('bar-hp-player').style.width = pctPlayer + '%';
            } else {
                pElem.style.color = "#f39c12";
                pElem.innerHTML = acao.texto;
            }

            logBox.appendChild(pElem);
            logBox.scrollTop = logBox.scrollHeight;
            index++;
        }, 800);

    } catch(e) {
        console.error(e);
        exibirAlertaCustom("Erro", "Falha de conexão com a arena.", false);
        carregarReino();
    }
}

function finalizarAnimacaoCombate(dados) {
    document.getElementById('btn-voltar-combate').style.display = "block";
    
    if (dados.vitoria) {
        let lootTexto = dados.recompensas.items.length > 0 
            ? `<br><br><span style="color:#a855f7;">📦 Loot: ${dados.recompensas.items.join(', ')}</span>`
            : "";
            
        exibirAlertaCustom(
            "Vitória!", 
            `O monstro caiu!<br><br>✨ +${dados.recompensas.xp} XP<br>💰 +${dados.recompensas.gold} Ouro${lootTexto}`, 
            true
        );
    } else {
        exibirAlertaCustom(
            "Derrota", 
            "Você desmaiou em combate e perdeu experiência... Volte quando estiver mais forte.", 
            false
        );
    }
}