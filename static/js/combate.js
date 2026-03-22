// ==========================================
// SISTEMA DE COMBATE (ESTILO POKÉMON GBA - PRO)
// ==========================================
async function iniciarCacadaApp(playerAvatar) {
    const conteudo = document.getElementById('aba-reino');
    const charId = localStorage.getItem("jogadorEldoraID");

    // Tela de Carregamento
    conteudo.innerHTML = `
        <div style="height: 300px; display: flex; flex-direction: column; justify-content: center; align-items: center;">
            <div style="font-size: 3em; animation: bob 1s infinite;">🌿</div>
            <h3 style="color: #2ecc71; margin-top: 15px; font-family: monospace;">Andando pelo mato alto...</h3>
        </div>
        <style>@keyframes bob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }</style>
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

        // ====================================================
        // CSS EMBUTIDO (UPGRADE POKÉMON ADVANCED)
        // ====================================================
        const arenaStyles = `
            <style>
                .pkmn-arena {
                    position: relative; width: 100%; height: 280px;
                    background: linear-gradient(to bottom, #1e3c72 0%, #2a5298 45%, #3e5151 45%, #609931 100%);
                    border: 4px solid #0f172a; border-radius: 8px; overflow: hidden; margin-bottom: 12px;
                    box-shadow: inset 0 0 30px rgba(0,0,0,0.5);
                }
                
                /* Sombras circulares no chão */
                .pkmn-base {
                    position: absolute; background: rgba(0,0,0,0.4); border-radius: 50%;
                    height: 25px; left: 50%; transform: translateX(-50%); bottom: -12px;
                    filter: blur(2px);
                }
                
                /* Sprites (Agora parecem Tokens de Batalha) */
                .pkmn-sprite {
                    position: relative; z-index: 2; border-radius: 12px; object-fit: cover;
                    box-shadow: 0 10px 20px rgba(0,0,0,0.7); border: 3px solid #d4af37;
                    background: #111;
                }

                /* Caixas de Status */
                .pkmn-info {
                    position: absolute; background: #fffde7; 
                    border: 3px solid #1e293b; border-bottom: 5px solid #1e293b; border-right: 5px solid #1e293b;
                    padding: 8px 12px; color: #1e293b; font-weight: 900; width: 160px; 
                    box-shadow: 2px 2px 5px rgba(0,0,0,0.4); z-index: 10;
                }
                /* Curvas assimétricas clássicas do GBA */
                .mob-info { border-radius: 8px 8px 8px 24px; top: 15px; left: 10px; }
                .player-info { border-radius: 8px 8px 24px 8px; bottom: 15px; right: 10px; }

                .pkmn-name { font-size: 0.95em; text-transform: uppercase; margin-bottom: 6px; display: flex; justify-content: space-between; letter-spacing: 0.5px; }
                
                /* Barra de HP de Elite */
                .hp-container { display: flex; align-items: center; background: #475569; border-radius: 10px; padding: 2px 4px; border: 2px solid #cbd5e1; box-shadow: inset 0 2px 4px rgba(0,0,0,0.5); }
                .hp-tag { color: #f1c40f; font-size: 0.7em; font-weight: 900; margin-right: 5px; text-shadow: 1px 1px 0px #000; letter-spacing: 1px; }
                .pkmn-hp-bg { background: #1e293b; height: 8px; border-radius: 4px; width: 100%; overflow: hidden; }
                .pkmn-hp-bar { background: #2ecc71; width: 100%; height: 100%; transition: width 0.3s ease, background-color 0.3s ease; box-shadow: inset 0 -2px 0 rgba(0,0,0,0.2); }

                /* Caixa de Diálogo Clássica */
                .pkmn-dialog {
                    background: #fffde7; border: 4px solid #475569; border-radius: 8px;
                    padding: 15px; font-family: 'Courier New', Courier, monospace; font-weight: 800;
                    font-size: 1.1em; color: #1e293b; height: 110px; overflow-y: auto;
                    box-shadow: inset 0 0 10px rgba(0,0,0,0.1), 0 4px 6px rgba(0,0,0,0.3);
                    position: relative;
                }
                /* Setinha vermelha piscando */
                .blinking-arrow {
                    position: absolute; bottom: 10px; right: 15px;
                    width: 0; height: 0; border-left: 8px solid transparent;
                    border-right: 8px solid transparent; border-top: 12px solid #e74c3c;
                    animation: blink 0.8s infinite;
                }

                /* Animações Mágicas */
                @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
                @keyframes idleMob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-5px); } }
                @keyframes atkPlayer { 0%, 100% { transform: translate(0, 0); } 50% { transform: translate(30px, -30px) scale(1.15); } }
                @keyframes atkMob { 0%, 100% { transform: translate(0, 0); } 50% { transform: translate(-30px, 30px) scale(1.15); } }
                @keyframes dmgFlash { 0%, 100% { filter: brightness(1); } 50% { filter: brightness(2) sepia(1) hue-rotate(320deg) saturate(5); } }
                @keyframes shake { 0%, 100% { transform: translateX(0); } 25% { transform: translateX(-6px) rotate(-3deg); } 50% { transform: translateX(6px) rotate(3deg); } 75% { transform: translateX(-6px) rotate(-3deg); } }

                .anim-idle { animation: idleMob 2.5s infinite ease-in-out; }
                .anim-atk-p { animation: atkPlayer 0.25s ease-in-out; }
                .anim-atk-m { animation: atkMob 0.25s ease-in-out; }
                /* O combo de dano: pisca vermelho E treme */
                .anim-dmg { animation: dmgFlash 0.4s ease-in-out, shake 0.4s ease-in-out; }
            </style>
        `;

        // ====================================================
        // ESTRUTURA HTML DA ARENA
        // ====================================================
        conteudo.innerHTML = arenaStyles + `
            <div class="pkmn-arena">
                <div class="pkmn-info mob-info">
                    <div class="pkmn-name"><span>${dados.mob.nome}</span> <span>Lv?</span></div>
                    <div class="hp-container">
                        <span class="hp-tag">HP</span>
                        <div class="pkmn-hp-bg"><div id="bar-hp-mob" class="pkmn-hp-bar"></div></div>
                    </div>
                </div>
                <div style="position: absolute; top: 40px; right: 25px; text-align: center;">
                    <div class="pkmn-base" style="width: 80px;"></div>
                    <img id="sprite-mob" src="${dados.mob.imagem}" onerror="this.src='https://placehold.co/100/333/e74c3c?text=👹'" class="pkmn-sprite anim-idle" style="width: 90px; height: 90px;">
                </div>

                <div style="position: absolute; bottom: 30px; left: 15px; text-align: center;">
                    <div class="pkmn-base" style="width: 100px;"></div>
                    <img id="sprite-player" src="${playerAvatar}" class="pkmn-sprite" style="width: 110px; height: 110px; object-position: top;">
                </div>
                <div class="pkmn-info player-info">
                    <div class="pkmn-name"><span>Você</span></div>
                    <div class="hp-container">
                        <span class="hp-tag">HP</span>
                        <div class="pkmn-hp-bg"><div id="bar-hp-player" class="pkmn-hp-bar"></div></div>
                    </div>
                    <div style="text-align: right; font-size: 0.85em; margin-top: 5px; color: #475569;">
                        <span id="txt-hp-player" style="color:#1e293b;">${dados.player.hp_max}</span> / ${dados.player.hp_max}
                    </div>
                </div>
            </div>

            <div class="pkmn-dialog" id="combat-log-box">
                <div class="blinking-arrow" id="dialog-arrow"></div>
                <div>Um <span style="color: #e74c3c;">${dados.mob.nome}</span> selvagem atacou!</div>
            </div>
            
            <button id="btn-voltar-combate" onclick="carregarReino()" style="width: 100%; background: #0f172a; padding: 14px; border: 2px solid #3b82f6; color: white; border-radius: 8px; margin-top: 15px; display: none; cursor: pointer; font-weight: 900; font-size: 1.1em; text-transform: uppercase; box-shadow: 0 4px 10px rgba(0,0,0,0.5);"> FUGIR / SAIR </button>
        `;

        // ====================================================
        // MOTOR DE ANIMAÇÃO DO COMBATE
        // ====================================================
        const logBox = document.getElementById('combat-log-box');
        const spritePlayer = document.getElementById('sprite-player');
        const spriteMob = document.getElementById('sprite-mob');
        const barPlayer = document.getElementById('bar-hp-player');
        const barMob = document.getElementById('bar-hp-mob');
        const txtHpPlayer = document.getElementById('txt-hp-player');

        let playerHpAtual = dados.player.hp_max;
        let mobHpAtual = dados.mob.hp_max;

        // Gerenciador de cor da barra de HP
        function atualizarBarra(barra, hpAtual, hpMax) {
            const pct = Math.max(0, (hpAtual / hpMax) * 100);
            barra.style.width = pct + '%';
            if (pct > 50) barra.style.backgroundColor = "#2ecc71"; // Verde (Saudável)
            else if (pct > 20) barra.style.backgroundColor = "#f1c40f"; // Amarelo (Atenção)
            else barra.style.backgroundColor = "#e74c3c"; // Vermelho (Perigo)
        }

        let index = 0;
        
        // Loop da Batalha (Lê os dados gerados pelo Python)
        const intervaloCombate = setInterval(() => {
            if (index >= dados.log.length) {
                clearInterval(intervaloCombate);
                finalizarAnimacaoCombate(dados);
                return;
            }

            const acao = dados.log[index];
            
            // Limpa as animações para reiniciar o ciclo
            spritePlayer.classList.remove('anim-atk-p', 'anim-dmg');
            spriteMob.classList.remove('anim-atk-m', 'anim-dmg');
            void spritePlayer.offsetWidth; 
            void spriteMob.offsetWidth;

            // Insere o novo log
            const msgDiv = document.createElement('div');
            msgDiv.style.marginTop = "10px";
            msgDiv.style.borderTop = "1px dashed #ccc";
            msgDiv.style.paddingTop = "5px";

            if (acao.atacante === "player") {
                // Jogador ataca
                spritePlayer.classList.add('anim-atk-p');
                setTimeout(() => spriteMob.classList.add('anim-dmg'), 150); 

                mobHpAtual -= acao.dano;
                atualizarBarra(barMob, mobHpAtual, dados.mob.hp_max);
                
                msgDiv.style.color = "#2980b9";
                msgDiv.innerHTML = `▶ ${acao.texto}`;
                
            } else if (acao.atacante === "mob") {
                // Monstro ataca
                spriteMob.classList.add('anim-atk-m');
                setTimeout(() => spritePlayer.classList.add('anim-dmg'), 150); 

                playerHpAtual -= acao.dano;
                txtHpPlayer.innerText = Math.max(0, playerHpAtual);
                atualizarBarra(barPlayer, playerHpAtual, dados.player.hp_max);
                
                msgDiv.style.color = "#c0392b";
                msgDiv.innerHTML = `▶ ${acao.texto}`;

            } else {
                // Dano de Sistema / Durabilidade
                msgDiv.style.color = "#7f8c8d";
                msgDiv.innerHTML = `▶ ${acao.texto}`;
            }

            logBox.appendChild(msgDiv);
            logBox.scrollTop = logBox.scrollHeight;
            index++;
            
        }, 1200); // 1.2s garante que dá tempo de ler e ver o tremor!

    } catch(e) {
        console.error(e);
        exibirAlertaCustom("Erro", "Falha ao desenhar a arena.", false);
        carregarReino();
    }
}

function finalizarAnimacaoCombate(dados) {
    const btnVoltar = document.getElementById('btn-voltar-combate');
    const logBox = document.getElementById('combat-log-box');
    const seta = document.getElementById('dialog-arrow');
    
    btnVoltar.style.display = "block";
    btnVoltar.innerText = "⬅️ Retornar ao Mapa";
    if (seta) seta.style.display = "none"; // Some a setinha de carregar
    
    if (dados.vitoria) {
        let lootTexto = dados.recompensas.items.length > 0 
            ? `<br><span style="color:#8e44ad;">Ganhou: ${dados.recompensas.items.join(', ')}</span>`
            : "";
            
        logBox.innerHTML += `<div style="color: #27ae60; margin-top: 15px; font-size: 1.1em; border-top: 2px dashed #ccc; padding-top: 10px;">
            <b>Batalha Vencida!</b><br>Você ganhou ${dados.recompensas.xp} XP e ${dados.recompensas.gold} Ouro.${lootTexto}
        </div>`;
        logBox.scrollTop = logBox.scrollHeight;
        
        // Inimigo desmaia (Cai para baixo da tela)
        document.getElementById('sprite-mob').style.transition = "transform 0.8s ease-in, opacity 0.8s";
        document.getElementById('sprite-mob').style.transform = "translateY(80px) scale(0.5)";
        document.getElementById('sprite-mob').style.opacity = "0";

    } else {
        logBox.innerHTML += `<div style="color: #c0392b; margin-top: 15px; font-size: 1.1em; border-top: 2px dashed #ccc; padding-top: 10px;">
            <b>Sua visão escureceu...</b><br>Você foi derrotado.
        </div>`;
        logBox.scrollTop = logBox.scrollHeight;
        
        // Jogador desmaia
        document.getElementById('sprite-player').style.transition = "transform 0.8s ease-in, opacity 0.8s";
        document.getElementById('sprite-player').style.transform = "translateY(80px) scale(0.5)";
        document.getElementById('sprite-player').style.opacity = "0";
    }
}