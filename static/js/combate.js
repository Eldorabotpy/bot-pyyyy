// ==========================================
// SISTEMA DE COMBATE (ESTILO POKÉMON GBA)
// ==========================================
async function iniciarCacadaApp(playerAvatar) {
    const conteudo = document.getElementById('aba-reino');
    const charId = localStorage.getItem("jogadorEldoraID");

    // Tela de Carregamento
    conteudo.innerHTML = `
        <div style="height: 300px; display: flex; flex-direction: column; justify-content: center; align-items: center;">
            <div style="font-size: 3em; animation: bob 1s infinite;">🌿</div>
            <h3 style="color: #2ecc71; margin-top: 15px;">Andando pelo mato alto...</h3>
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
        // CSS EMBUTIDO DA ARENA RETRÔ (ANIMAÇÕES E LAYOUT)
        // ====================================================
        const arenaStyles = `
            <style>
                .pkmn-arena {
                    position: relative; width: 100%; height: 280px;
                    background: linear-gradient(to bottom, #4facfe 0%, #00f2fe 45%, #7ec850 45%, #5ebd3e 100%);
                    border: 4px solid #1e293b; border-radius: 8px; overflow: hidden; margin-bottom: 10px;
                    box-shadow: inset 0 0 20px rgba(0,0,0,0.3);
                }
                
                /* Sombras circulares (As bases) */
                .pkmn-base {
                    position: absolute; background: rgba(0,0,0,0.3); border-radius: 50%;
                    height: 25px; left: 50%; transform: translateX(-50%); bottom: -10px;
                }
                
                /* Sprites dos personagens */
                .pkmn-sprite {
                    position: relative; z-index: 2; border-radius: 8px; object-fit: cover;
                    box-shadow: 0 4px 10px rgba(0,0,0,0.5); border: 2px solid #fff;
                }

                /* Caixas de HP Flutuantes */
                .pkmn-info {
                    position: absolute; background: #fffde7; border: 3px solid #475569;
                    border-radius: 6px; padding: 6px 10px; color: #1e293b;
                    font-weight: bold; width: 145px; box-shadow: 2px 2px 0px rgba(0,0,0,0.3);
                    z-index: 10;
                }
                .pkmn-name { font-size: 0.9em; text-transform: uppercase; margin-bottom: 4px; display: flex; justify-content: space-between; }
                .pkmn-hp-bg { background: #475569; height: 8px; border-radius: 4px; width: 100%; overflow: hidden; border: 1px solid #1e293b; }
                .pkmn-hp-bar { background: #2ecc71; width: 100%; height: 100%; transition: width 0.3s ease, background-color 0.3s ease; }
                
                /* Caixas de Texto estilo GameBoy */
                .pkmn-dialog {
                    background: #fffde7; border: 4px solid #475569; border-radius: 8px;
                    padding: 12px; font-family: 'Courier New', Courier, monospace; font-weight: 800;
                    font-size: 1.05em; color: #1e293b; height: 100px; overflow-y: auto;
                    box-shadow: 2px 2px 0px rgba(0,0,0,0.3);
                }

                /* Animações (Keyframes) */
                @keyframes idleMob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
                @keyframes atkPlayer { 0%, 100% { transform: translate(0, 0); } 50% { transform: translate(25px, -25px) scale(1.1); } }
                @keyframes atkMob { 0%, 100% { transform: translate(0, 0); } 50% { transform: translate(-25px, 25px) scale(1.1); } }
                @keyframes dmgFlash { 0%, 100% { filter: brightness(1); } 50% { filter: brightness(2) sepia(1) hue-rotate(320deg) saturate(5); } }

                .anim-idle { animation: idleMob 2.5s infinite ease-in-out; }
                .anim-atk-p { animation: atkPlayer 0.3s ease-in-out; }
                .anim-atk-m { animation: atkMob 0.3s ease-in-out; }
                .anim-dmg { animation: dmgFlash 0.3s ease-in-out; }
            </style>
        `;

        // ====================================================
        // ESTRUTURA HTML DA ARENA
        // ====================================================
        conteudo.innerHTML = arenaStyles + `
            <div class="pkmn-arena">
                <div class="pkmn-info" style="top: 15px; left: 15px;">
                    <div class="pkmn-name"><span>${dados.mob.nome}</span> <span>Lv?</span></div>
                    <div class="pkmn-hp-bg"><div id="bar-hp-mob" class="pkmn-hp-bar"></div></div>
                </div>
                <div style="position: absolute; top: 40px; right: 25px; text-align: center;">
                    <div class="pkmn-base" style="width: 80px;"></div>
                    <img id="sprite-mob" src="${dados.mob.imagem}" onerror="this.src='https://placehold.co/100/333/e74c3c?text=👹'" class="pkmn-sprite anim-idle" style="width: 85px; height: 85px;">
                </div>

                <div style="position: absolute; bottom: 30px; left: 20px; text-align: center;">
                    <div class="pkmn-base" style="width: 100px;"></div>
                    <img id="sprite-player" src="${playerAvatar}" class="pkmn-sprite" style="width: 110px; height: 110px;">
                </div>
                <div class="pkmn-info" style="bottom: 15px; right: 15px;">
                    <div class="pkmn-name"><span>Você</span></div>
                    <div class="pkmn-hp-bg"><div id="bar-hp-player" class="pkmn-hp-bar"></div></div>
                    <div style="text-align: right; font-size: 0.8em; margin-top: 4px;">HP: <span id="txt-hp-player">${dados.player.hp_max}</span> / ${dados.player.hp_max}</div>
                </div>
            </div>

            <div class="pkmn-dialog" id="combat-log-box">
                Um <span style="color: #e74c3c;">${dados.mob.nome}</span> selvagem atacou!
            </div>
            
            <button id="btn-voltar-combate" onclick="carregarReino()" style="width: 100%; background: #1a1a1a; padding: 12px; border: 1px solid #333; color: white; border-radius: 8px; margin-top: 15px; display: none; cursor: pointer; font-weight: bold;"> Fugir / Voltar </button>
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

        // Função auxiliar para mudar a cor da barra de vida igual Pokémon
        function atualizarBarra(barra, hpAtual, hpMax) {
            const pct = Math.max(0, (hpAtual / hpMax) * 100);
            barra.style.width = pct + '%';
            if (pct > 50) barra.style.backgroundColor = "#2ecc71"; // Verde
            else if (pct > 20) barra.style.backgroundColor = "#f1c40f"; // Amarelo
            else barra.style.backgroundColor = "#e74c3c"; // Vermelho
        }

        let index = 0;
        
        // Loop a cada 1 segundo para dar tempo de ver a animação
        const intervaloCombate = setInterval(() => {
            if (index >= dados.log.length) {
                clearInterval(intervaloCombate);
                finalizarAnimacaoCombate(dados);
                return;
            }

            const acao = dados.log[index];
            
            // Remove animações antigas para poder tocar de novo
            spritePlayer.classList.remove('anim-atk-p', 'anim-dmg');
            spriteMob.classList.remove('anim-atk-m', 'anim-dmg');
            
            // Força o navegador a recalcular as classes (Truque de magia do CSS)
            void spritePlayer.offsetWidth; 
            void spriteMob.offsetWidth;

            if (acao.atacante === "player") {
                // Jogador ataca, Monstro toma dano
                spritePlayer.classList.add('anim-atk-p');
                setTimeout(() => spriteMob.classList.add('anim-dmg'), 150); // Monstro pisca logo depois

                mobHpAtual -= acao.dano;
                atualizarBarra(barMob, mobHpAtual, dados.mob.hp_max);
                
                // Texto azul/verde clássico para o herói
                logBox.innerHTML += `<div style="color: #2980b9; margin-top: 8px;">▶ ${acao.texto}</div>`;
                
            } else if (acao.atacante === "mob") {
                // Monstro ataca, Jogador toma dano
                spriteMob.classList.add('anim-atk-m');
                setTimeout(() => spritePlayer.classList.add('anim-dmg'), 150); // Jogador pisca

                playerHpAtual -= acao.dano;
                txtHpPlayer.innerText = Math.max(0, playerHpAtual);
                atualizarBarra(barPlayer, playerHpAtual, dados.player.hp_max);
                
                // Texto vermelho para inimigo
                logBox.innerHTML += `<div style="color: #c0392b; margin-top: 8px;">▶ ${acao.texto}</div>`;
            } else {
                // Dano de sistema/veneno
                logBox.innerHTML += `<div style="color: #7f8c8d; margin-top: 8px;">▶ ${acao.texto}</div>`;
            }

            // Faz a caixa de texto rolar para baixo automaticamente
            logBox.scrollTop = logBox.scrollHeight;
            index++;
            
        }, 1100); // 1.1 segundos entre cada golpe para a animação não engasgar

    } catch(e) {
        console.error(e);
        exibirAlertaCustom("Erro", "Falha ao desenhar a arena.", false);
        carregarReino();
    }
}

function finalizarAnimacaoCombate(dados) {
    document.getElementById('btn-voltar-combate').style.display = "block";
    document.getElementById('btn-voltar-combate').innerText = "⬅️ Voltar para o Mapa";
    
    const logBox = document.getElementById('combat-log-box');
    
    if (dados.vitoria) {
        let lootTexto = dados.recompensas.items.length > 0 
            ? `<br><span style="color:#8e44ad;">Ganhou: ${dados.recompensas.items.join(', ')}</span>`
            : "";
            
        logBox.innerHTML += `<div style="color: #27ae60; margin-top: 10px; font-size: 1.1em; border-top: 2px dashed #ccc; padding-top: 5px;">
            <b>Vitória!</b><br>Você ganhou ${dados.recompensas.xp} XP e ${dados.recompensas.gold} Ouro.${lootTexto}
        </div>`;
        logBox.scrollTop = logBox.scrollHeight;
        
        // Faz o monstro "desmaiar" afundando na tela
        document.getElementById('sprite-mob').style.transition = "transform 1s, opacity 1s";
        document.getElementById('sprite-mob').style.transform = "translateY(50px)";
        document.getElementById('sprite-mob').style.opacity = "0";

    } else {
        logBox.innerHTML += `<div style="color: #c0392b; margin-top: 10px; font-size: 1.1em; border-top: 2px dashed #ccc; padding-top: 5px;">
            <b>Sua visão escureceu...</b><br>Você perdeu a batalha.
        </div>`;
        logBox.scrollTop = logBox.scrollHeight;
        
        // Faz o jogador "desmaiar"
        document.getElementById('sprite-player').style.transition = "transform 1s, opacity 1s";
        document.getElementById('sprite-player').style.transform = "translateY(50px)";
        document.getElementById('sprite-player').style.opacity = "0";
    }
}