// ==========================================
// 1. DICIONÁRIO DE CENÁRIOS E CLASSES (LINKS MANTIDOS)
// ==========================================
const FUNDOS_ARENAS = {
    "pradaria_inicial": "https://github.com/user-attachments/assets/8978e977-c5da-4d78-851a-ae28452b10ec", 
    "floresta_sombria": "https://placehold.co/600x400/2c3e50/111?text=Cenario+Floresta",
    "pedreira_granito": "https://placehold.co/600x400/7f8c8d/111?text=Cenario+Pedras",
    "reino_eldora": "https://placehold.co/600x400/2980b9/111?text=Cenario+Reino"
};

const SPRITES_COSTA = {
    "aventureiro": "https://github.com/user-attachments/assets/6621c6b9-691f-45dd-b738-7915bb576f53", 
    "guerreiro": "https://placehold.co/200x300/transparent/fff?text=Guerreiro",
    "mago": "https://placehold.co/200x300/transparent/fff?text=Mago",
    "arqueiro": "https://placehold.co/200x300/transparent/fff?text=Arqueiro"
};

// ==========================================
// 2. DICIONÁRIO DE ÁUDIOS (LINKS MANTIDOS)
// ==========================================
const AUDIO_ASSETS = {
    bgm_batalha: "https://github.com/user-attachments/files/26172245/psychronic-crystal-hunter-281389.mp3", 
    som_espada: "https://github.com/user-attachments/files/26172264/attack.mp3",     
    som_critico: "https://github.com/user-attachments/files/26172289/phatphrogstudio-rpg-female-attack-grunt-no-ai-481720.mp3",     
    som_monstro: "https://github.com/user-attachments/files/26172322/voicebosch-snarls-and-growls-172823.mp3",  
    som_vitoria: "https://github.com/user-attachments/files/26172334/eaglaxle-gaming-victory-464016.mp3" 
};

let musicaDeFundoAtual = null; 
let COMBATE_ATUAL = null; // Guarda o estado da batalha (Turnos)

// ==========================================
// 3. FUNÇÕES AUXILIARES (Som, Animação e Barras)
// ==========================================
function tocarSFX(url) {
    if (!url || url.includes("LINK_")) return; 
    let sfx = new Audio(url);
    sfx.volume = 0.6; 
    sfx.play().catch(e => console.log("Áudio bloqueado:", e));
}

function animarCorteVisual(alvoId, cor_brilho) {
    const alvo = document.getElementById(alvoId);
    if (!alvo) return;

    const corte = document.createElement('div');
    corte.className = 'slash-effect';
    corte.style.boxShadow = `0 0 10px #fff, 0 0 20px ${cor_brilho}`; 
    
    corte.style.left = (alvo.offsetLeft + alvo.offsetWidth / 2) + 'px';
    corte.style.top = (alvo.offsetTop + alvo.offsetHeight / 2) + 'px';

    alvo.parentElement.appendChild(corte);
    setTimeout(() => corte.remove(), 300);
}

function atualizarVisualBarra(elementId, porcentagem, isHP = true) {
    const barra = document.getElementById(elementId);
    if (!barra) return;

    porcentagem = Math.max(0, Math.min(100, porcentagem));
    barra.style.width = porcentagem + '%';

    // Lógica de Cores do GBA para HP
    if (isHP) {
        if (porcentagem > 50) {
            barra.style.backgroundColor = '#2ecc71'; // Verde
        } else if (porcentagem > 20) {
            barra.style.backgroundColor = '#f1c40f'; // Amarelo
        } else {
            barra.style.backgroundColor = '#e74c3c'; // Vermelho
        }
    }
}

function sairDaArena() {
    if (musicaDeFundoAtual) {
        musicaDeFundoAtual.pause(); 
        musicaDeFundoAtual.currentTime = 0; 
        musicaDeFundoAtual = null;
    }
    carregarReino(); 
}

// ==========================================
// 4. INICIA A BATALHA (Carrega o Mapa e a UI)
// ==========================================
async function iniciarCacadaApp() {
    const conteudo = document.getElementById('aba-reino');
    const charId = localStorage.getItem("jogadorEldoraID");

    conteudo.innerHTML = `
        <div style="height: 300px; display: flex; flex-direction: column; justify-content: center; align-items: center;">
            <div style="font-size: 3em; animation: pulseRing 1s infinite;">⚔️</div>
            <h3 style="color: #e74c3c; margin-top: 15px; font-family: 'Courier New', monospace;">Procurando inimigos...</h3>
        </div>
    `;

    try {
        const res = await fetch('/api/combate/iniciar', {
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

        COMBATE_ATUAL = dados.estado; // Salva HPs e Nomes

        // TOCA A MÚSICA DE FUNDO 🎵
        if (AUDIO_ASSETS.bgm_batalha && !AUDIO_ASSETS.bgm_batalha.includes("LINK_")) {
            musicaDeFundoAtual = new Audio(AUDIO_ASSETS.bgm_batalha);
            musicaDeFundoAtual.loop = true;
            musicaDeFundoAtual.volume = 0.3; 
            musicaDeFundoAtual.play().catch(e => console.log("Áudio bloqueado:", e));
        }

        const bgArena = FUNDOS_ARENAS[COMBATE_ATUAL.regiao] || "https://placehold.co/600x400/111/222?text=Arena+Desconhecida";
        const urlSpritePlayer = SPRITES_COSTA[dados.classe_player] || SPRITES_COSTA["aventureiro"];

        // RENDERIZAÇÃO DA ARENA ESTILO POKÉMON GBA
        conteudo.innerHTML = `
            <style>
                @import url('https://fonts.googleapis.com/css2?family=VT323&display=swap');
                
                .gba-font { font-family: 'VT323', monospace; text-transform: uppercase; letter-spacing: 1px; }
                
                /* Animação do Corte (Mantida) */
                @keyframes animCorte {
                    0% { width: 0px; opacity: 1; transform: translate(-50%, -50%) rotate(45deg); }
                    50% { width: 120px; opacity: 1; transform: translate(-50%, -50%) rotate(45deg); }
                    100% { width: 160px; opacity: 0; transform: translate(-50%, -50%) rotate(45deg); }
                }
                .slash-effect { position: absolute; height: 4px; background: #fff; border-radius: 50%; z-index: 30; pointer-events: none; animation: animCorte 0.3s ease-out forwards; }

                /* Estilos HUD Pokémon */
                .pkm-hud { position: absolute; background-color: rgba(248, 248, 248, 0.9); border: 2px solid #606060; border-radius: 5px; padding: 5px 10px; box-shadow: 2px 2px 0px rgba(0,0,0,0.3); min-width: 140px; z-index: 10; }
                #pkm-hud-monstro { top: 15px; left: 15px; border-top-left-radius: 15px; }
                #pkm-hud-jogador { bottom: 20px; right: 15px; border-bottom-right-radius: 15px; }
                
                .pkm-name { font-size: 18px; color: #303030; font-weight: bold; margin-bottom: 2px; display: inline-block;}
                .pkm-lv { font-size: 14px; color: #d35400; margin-left: 5px; font-weight: bold;}
                
                .pkm-hp-bar-container { width: 100px; height: 6px; background-color: #505050; border: 1px solid #303030; margin-top: 3px; position: relative; overflow: hidden; }
                .pkm-hp-bar-fill { height: 100%; background-color: #2ecc71; transition: width 0.4s ease, background-color 0.3s ease; }
                .pkm-mp-bar-fill { height: 100%; background-color: #3498db; transition: width 0.4s ease; }
                
                /* Caixa de Texto */
                .log-box-gba { height: 90px; background-color: #f8f8f8; border: 4px solid #606060; border-radius: 8px; padding: 10px 15px; overflow-y: auto; color: #303030; font-size: 20px; line-height: 1.2; margin-bottom: 10px; box-shadow: inset 2px 2px 5px rgba(0,0,0,0.1);}
                
                /* Botões GBA */
                .menu-btn { padding: 12px; border: 3px solid #606060; border-radius: 5px; cursor: pointer; font-size: 20px; font-weight: bold; background: #fff; color: #303030; transition: all 0.1s; text-align: left; padding-left: 20px;}
                .menu-btn:active { background: #e0e0e0; transform: scale(0.98); }
            </style>

            <div id="container-arena" class="gba-font" style="background: url('${bgArena}') center bottom / cover no-repeat; width: 100%; height: 260px; box-sizing: border-box; border: 4px solid #303030; position: relative; overflow: hidden; margin-bottom: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.8);">
                
                <div id="pkm-hud-monstro" class="pkm-hud">
                    <div style="display: flex; justify-content: space-between; align-items: baseline;">
                        <span class="pkm-name">${COMBATE_ATUAL.mob_nome}</span>
                    </div>
                    <div style="display: flex; align-items: center; justify-content: flex-end;">
                        <span style="font-size: 12px; color: #f1c40f; margin-right: 3px; font-weight: bold;">HP</span>
                        <div class="pkm-hp-bar-container">
                            <div id="bar-hp-monstro" class="pkm-hp-bar-fill" style="width: 100%;"></div>
                        </div>
                    </div>
                </div>

                <div id="pkm-hud-jogador" class="pkm-hud">
                    <div style="text-align: left;">
                        <span class="pkm-name">VOCÊ</span>
                    </div>
                    <div style="display: flex; align-items: center; justify-content: flex-end;">
                        <span style="font-size: 12px; color: #f1c40f; margin-right: 3px; font-weight: bold;">HP</span>
                        <div class="pkm-hp-bar-container" style="width: 110px;">
                            <div id="bar-hp-player" class="pkm-hp-bar-fill" style="width: 100%;"></div>
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; justify-content: flex-end; margin-top: 2px;">
                        <span style="font-size: 12px; color: #3498db; margin-right: 3px; font-weight: bold;">MP</span>
                        <div class="pkm-hp-bar-container" style="width: 110px;">
                            <div id="bar-mp-player" class="pkm-mp-bar-fill" style="width: 100%;"></div>
                        </div>
                    </div>
                </div>

                <div id="arena-characters" style="position: absolute; bottom: 5%; left:0; width: 100%; box-sizing: border-box; display: flex; justify-content: space-between; align-items: flex-end; padding: 0 15px; z-index: 5;">
                    <img id="sprite-player" src="${urlSpritePlayer}" style="height: 110px; max-width: 45%; object-fit: contain; filter: drop-shadow(3px 12px 4px rgba(0,0,0,0.6)); transition: transform 0.15s ease, opacity 0.3s;">
                    <img id="sprite-mob" src="${COMBATE_ATUAL.mob_img}" onerror="this.src='https://placehold.co/150x150/transparent/e74c3c?text=👹'" style="height: 110px; max-width: 50%; object-fit: contain; filter: drop-shadow(-3px 12px 4px rgba(0,0,0,0.6)); transition: transform 0.15s ease, opacity 0.3s;">
                </div>
            </div>

            <div id="combat-log-box" class="log-box-gba gba-font">
                Um <span style="color:#e74c3c;">${COMBATE_ATUAL.mob_nome}</span> selvagem apareceu!<br>O que você vai fazer?
            </div>

            <div id="menu-acoes" class="gba-font" style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                <button class="menu-btn" onclick="enviarAcaoCombate('atacar')">⚔️ ATACAR</button>
                <button class="menu-btn" onclick="alert('Sistema de Skills no próximo passo!')">✨ MAGIAS</button>
                <button class="menu-btn" onclick="alert('Sistema de Mochila no próximo passo!')">🎒 MOCHILA</button>
                <button class="menu-btn" onclick="enviarAcaoCombate('fugir')">🏃 FUGIR</button>
            </div>
            
            <button id="btn-voltar-combate" class="gba-font" onclick="sairDaArena()" style="width: 100%; background: #303030; padding: 14px; border: 3px solid #606060; color: #fff; border-radius: 5px; margin-top: 10px; display: none; cursor: pointer; font-size: 20px;">SAIR DA ARENA</button>
        `;

        // Ajusta as barras iniciais baseadas no HP máximo
        atualizarVisualBarra('bar-hp-player', (COMBATE_ATUAL.player_hp / COMBATE_ATUAL.player_stats.max_hp) * 100, true);
        atualizarVisualBarra('bar-mp-player', (COMBATE_ATUAL.player_mp / COMBATE_ATUAL.player_stats.max_mana) * 100, false);
        atualizarVisualBarra('bar-hp-monstro', (COMBATE_ATUAL.monster_hp / COMBATE_ATUAL.monster_stats.max_hp) * 100, true);

    } catch(e) {
        console.error(e);
        exibirAlertaCustom("Erro", "Falha de conexão com a arena.", false);
        carregarReino();
    }
}

// ==========================================
// 5. PROCESSA O TURNO DO JOGADOR E MONSTRO
// ==========================================
async function enviarAcaoCombate(acao, targetId = null) {
    const charId = localStorage.getItem("jogadorEldoraID");
    const logBox = document.getElementById('combat-log-box');
    const menu = document.getElementById('menu-acoes');
    const elemSpriteMob = document.getElementById('sprite-mob');
    const elemSpritePlayer = document.getElementById('sprite-player');

    // Esconde o menu para evitar double click
    menu.style.display = 'none';
    logBox.innerHTML = ""; // Limpa a caixa

    try {
        const res = await fetch('/api/combate/acao', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: charId, acao: acao, target_id: targetId })
        });
        const turnoData = await res.json();

        if (turnoData.erro) {
            logBox.innerHTML = `<span style="color:#e74c3c;">Erro: ${turnoData.erro}</span>`;
            menu.style.display = 'grid';
            return;
        }

        if (turnoData.fugiu) {
            tocarSFX(AUDIO_ASSETS.som_vitoria); // Som genérico de saída
            logBox.innerHTML = "Você fugiu em segurança!";
            setTimeout(() => sairDaArena(), 1500);
            return;
        }

        // Atualiza os valores globais
        COMBATE_ATUAL.player_hp = turnoData.player_hp;
        COMBATE_ATUAL.monster_hp = turnoData.monster_hp;

        // Atualiza as Barras Visuais
        atualizarVisualBarra('bar-hp-player', (turnoData.player_hp / COMBATE_ATUAL.player_stats.max_hp) * 100, true);
        atualizarVisualBarra('bar-hp-monstro', (turnoData.monster_hp / COMBATE_ATUAL.monster_stats.max_hp) * 100, true);

        // Imprime os Logs com "Delay" (Efeito Máquina de Escrever/GBA)
        let indexLog = 0;
        
        function mostrarProximoLog() {
            if (indexLog >= turnoData.log.length) {
                // Fim do turno, verifica se alguém morreu
                if (turnoData.vitoria) {
                    elemSpriteMob.style.opacity = "0";
                    tocarSFX(AUDIO_ASSETS.som_vitoria);
                    setTimeout(() => finalizarAnimacaoCombate(turnoData), 1000);
                } else if (turnoData.derrota) {
                    elemSpritePlayer.style.opacity = "0";
                    setTimeout(() => finalizarAnimacaoCombate(turnoData), 1000);
                } else {
                    // Turno acabou e ninguém morreu, volta o menu!
                    menu.style.display = 'grid';
                }
                return;
            }

            const linha = turnoData.log[indexLog];
            let htmlLinha = "";

            if (linha.autor === "player") {
                htmlLinha = `<span style="color:#27ae60;">${linha.texto}</span><br>`;
                
                // Animações de Dano no Monstro
                if (linha.texto.includes("CRÍTICO")) {
                    tocarSFX(AUDIO_ASSETS.som_critico);
                    animarCorteVisual('sprite-mob', '#f1c40f'); 
                } else {
                    tocarSFX(AUDIO_ASSETS.som_espada);
                    animarCorteVisual('sprite-mob', '#e74c3c'); 
                }
                elemSpritePlayer.style.transform = "translateX(20px)";
                elemSpriteMob.style.transform = "translateX(10px)";
                setTimeout(() => {
                    elemSpritePlayer.style.transform = "translateX(0)";
                    elemSpriteMob.style.transform = "translateX(0)";
                }, 150);

            } else if (linha.autor === "mob") {
                htmlLinha = `<span style="color:#e74c3c;">${linha.texto}</span><br>`;
                
                // Animações de Dano no Jogador
                tocarSFX(AUDIO_ASSETS.som_monstro);
                animarCorteVisual('sprite-player', '#8e44ad');
                
                elemSpriteMob.style.transform = "translateX(-20px)";
                elemSpritePlayer.style.transform = "translateX(-10px)";
                setTimeout(() => {
                    elemSpriteMob.style.transform = "translateX(0)";
                    elemSpritePlayer.style.transform = "translateX(0)";
                }, 150);

            } else {
                htmlLinha = `<span style="color:#d35400;">${linha.texto}</span><br>`;
            }

            logBox.innerHTML += htmlLinha;
            logBox.scrollTop = logBox.scrollHeight;
            indexLog++;
            
            // Chama o próximo log após 600ms (dá tempo de ler)
            setTimeout(mostrarProximoLog, 600);
        }

        // Inicia a leitura do log
        mostrarProximoLog();

    } catch(e) {
        console.error(e);
        logBox.innerHTML = "Erro na conexão com o servidor.";
        menu.style.display = 'grid'; 
    }
}

// ==========================================
// 6. TELA DE RECOMPENSAS
// ==========================================
function finalizarAnimacaoCombate(dados) {
    document.getElementById('menu-acoes').style.display = "none";
    document.getElementById('btn-voltar-combate').style.display = "block";
    
    if (dados.vitoria) {
        let lootTexto = dados.recompensas.items.length > 0 
            ? `<br><br><span style="color:#8e44ad; font-weight: bold;">📦 Obteve: ${dados.recompensas.items.join(', ')}</span>`
            : "";
            
        exibirAlertaCustom(
            "Vitória!", 
            `A criatura caiu!<br><br>✨ +${dados.recompensas.xp} XP<br>💰 +${dados.recompensas.gold} Ouro${lootTexto}`, 
            true
        );
    } else {
        exibirAlertaCustom(
            "Derrota", 
            "Você desmaiou e foi resgatado para a cidade...", 
            false
        );
    }
}