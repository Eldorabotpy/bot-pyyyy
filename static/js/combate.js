// ==========================================
// 1. DICIONÁRIO DE CENÁRIOS E CLASSES
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
// 2. DICIONÁRIO DE ÁUDIOS (Músicas e Efeitos)
// ==========================================
const AUDIO_ASSETS = {
    bgm_batalha: "https://github.com/user-attachments/files/26172245/psychronic-crystal-hunter-281389.mp3",
    som_espada: "https://github.com/user-attachments/files/26172264/attack.mp3",
    som_critico: "https://github.com/user-attachments/files/26172289/phatphrogstudio-rpg-female-attack-grunt-no-ai-481720.mp3",
    som_monstro: "https://github.com/user-attachments/files/26172322/voicebosch-snarls-and-growls-172823.mp3",
    som_vitoria: "https://github.com/user-attachments/files/26172334/eaglaxle-gaming-victory-464016.mp3"
};

let musicaDeFundoAtual = null;

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

// Atualiza cor da barra de HP estilo Pokémon
function atualizarVisualBarra(elementId, atual, maximo, isMana=false) {
    const barra = document.getElementById(elementId);
    if (!barra) return;

    let porcentagem = Math.max(0, (atual / maximo) * 100);
    barra.style.width = porcentagem + '%';

    if (!isMana) {
        if (porcentagem > 50) barra.style.backgroundColor = '#2ecc71'; 
        else if (porcentagem > 20) barra.style.backgroundColor = '#f1c40f';
        else barra.style.backgroundColor = '#e74c3c';
    }
}

// ==========================================
// SISTEMA DE COMBATE ANIMADO E REALISTA (ESTILO GBA)
// ==========================================
async function iniciarCacadaApp() {
    const conteudo = document.getElementById('aba-reino');
    const charId = localStorage.getItem("jogadorEldoraID");

    conteudo.innerHTML = `
        <div style="height: 300px; display: flex; flex-direction: column; justify-content: center; align-items: center; font-family: sans-serif;">
            <div style="font-size: 3em; animation: pulseRing 1s infinite;">⚔️</div>
            <h3 style="color: #e74c3c; margin-top: 15px; font-style: italic;">Adentrando a selva...</h3>
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

        if (AUDIO_ASSETS.bgm_batalha && !AUDIO_ASSETS.bgm_batalha.includes("LINK_")) {
            musicaDeFundoAtual = new Audio(AUDIO_ASSETS.bgm_batalha);
            musicaDeFundoAtual.loop = true;
            musicaDeFundoAtual.volume = 0.3;
            musicaDeFundoAtual.play().catch(e => console.log("Áudio bloqueado:", e));
        }

        const bgArena = FUNDOS_ARENAS[dados.regiao] || "https://placehold.co/600x400/111/222?text=Arena+Desconhecida";
        const urlSpritePlayer = SPRITES_COSTA[dados.classe_player] || SPRITES_COSTA["aventureiro"];
        
        // Dados de Mana e Vida (Garantindo que não fiquem vazios)
        const playerMpMax = dados.player.mp_max || 50;
        const playerHpMax = dados.player.hp_max || 100;
        const mobMpMax = dados.mob.mp_max || 0;
        const mobHpMax = dados.mob.hp_max || 50;

        // Guarda os dados globalmente para o botão "ATACAR" acessar depois
        window.dadosCombateAtual = {
            log: dados.log,
            vitoria: dados.vitoria,
            recompensas: dados.recompensas,
            playerHpAtual: playerHpMax,
            playerHpMax: playerHpMax,
            mobHpAtual: mobHpMax,
            mobHpMax: mobHpMax
        };

        conteudo.innerHTML = `
            <style>
                @import url('https://fonts.googleapis.com/css2?family=VT323&display=swap');
                
                @keyframes animCorte {
                    0% { width: 0px; opacity: 1; transform: translate(-50%, -50%) rotate(45deg); }
                    50% { width: 120px; opacity: 1; transform: translate(-50%, -50%) rotate(45deg); }
                    100% { width: 160px; opacity: 0; transform: translate(-50%, -50%) rotate(45deg); }
                }
                .slash-effect { position: absolute; height: 4px; background: #fff; border-radius: 50%; z-index: 30; pointer-events: none; animation: animCorte 0.3s ease-out forwards; }
                
                /* Estilos Pokémon GBA */
                .pkm-font { font-family: 'VT323', monospace; text-transform: uppercase; letter-spacing: 1px; }
                
                .pkm-hud { position: absolute; background-color: rgba(248, 248, 248, 0.9); border: 3px solid #606060; padding: 5px 12px; box-shadow: 2px 2px 0px rgba(0,0,0,0.3); z-index: 10; width: 150px;}
                #pkm-hud-monstro { top: 15px; left: 15px; border-radius: 5px; border-top-left-radius: 15px; }
                #pkm-hud-jogador { bottom: 15px; right: 15px; border-radius: 5px; border-bottom-right-radius: 15px; width: 160px; }
                
                .pkm-hp-bar-container { width: 100%; height: 8px; background-color: #505050; border: 2px solid #303030; margin-top: 2px; border-radius: 2px; }
                .pkm-hp-bar-fill { height: 100%; background-color: #2ecc71; transition: width 0.3s ease, background-color 0.3s ease; }
                .pkm-mp-bar-fill { height: 100%; background-color: #3498db; transition: width 0.3s ease; }

                .pkm-btn { background: #fff; border: 3px solid #606060; border-radius: 8px; padding: 12px; font-size: 20px; color: #303030; cursor: pointer; text-align: left; box-shadow: 2px 2px 0px rgba(0,0,0,0.2); transition: 0.1s; display: flex; align-items: center; gap: 8px;}
                .pkm-btn:active { transform: translateY(2px); box-shadow: 0px 0px 0px rgba(0,0,0,0.2); }
            </style>

            <div id="arena-box" class="pkm-font" style="background: url('${bgArena}') center bottom / cover no-repeat; height: 260px; width: 100%; border-radius: 8px 8px 0 0; border: 4px solid #303030; border-bottom: none; position: relative; overflow: hidden;">
                
                <div id="pkm-hud-monstro" class="pkm-hud">
                    <div style="display: flex; justify-content: space-between; align-items: baseline; color: #303030;">
                        <strong style="font-size: 18px;">${dados.mob.nome}</strong>
                    </div>
                    <div style="display: flex; align-items: center; margin-top: 5px;">
                        <span style="font-size: 14px; color: #f1c40f; font-weight: bold; margin-right: 5px;">HP</span>
                        <div class="pkm-hp-bar-container"><div id="bar-hp-mob" class="pkm-hp-bar-fill" style="width: 100%;"></div></div>
                    </div>
                </div>

                <div id="pkm-hud-jogador" class="pkm-hud">
                    <div style="display: flex; justify-content: space-between; align-items: baseline; color: #303030;">
                        <strong style="font-size: 18px;">VOCÊ</strong>
                    </div>
                    <div style="display: flex; align-items: center; margin-top: 5px;">
                        <span style="font-size: 14px; color: #f1c40f; font-weight: bold; margin-right: 5px;">HP</span>
                        <div class="pkm-hp-bar-container"><div id="bar-hp-player" class="pkm-hp-bar-fill" style="width: 100%;"></div></div>
                    </div>
                    <div style="display: flex; align-items: center; margin-top: 4px;">
                        <span style="font-size: 14px; color: #3498db; font-weight: bold; margin-right: 5px;">MP</span>
                        <div class="pkm-hp-bar-container"><div id="bar-mp-player" class="pkm-mp-bar-fill" style="width: 100%;"></div></div>
                    </div>
                </div>

                <img id="sprite-player" src="${urlSpritePlayer}" style="position: absolute; bottom: 10px; left: 10px; height: 130px; object-fit: contain; filter: drop-shadow(3px 10px 4px rgba(0,0,0,0.5)); transition: transform 0.1s;">
                
                <img id="sprite-mob" src="${dados.mob.imagem}" onerror="this.src='https://placehold.co/150x150/transparent/e74c3c?text=👹'" style="position: absolute; bottom: 80px; right: 15px; height: 120px; object-fit: contain; filter: drop-shadow(-3px 10px 4px rgba(0,0,0,0.5)); transition: transform 0.1s;">
                
                <div id="damage-flash" style="position: absolute; top:0; left:0; width:100%; height:100%; background: rgba(231, 76, 60, 0.4); opacity: 0; transition: opacity 0.1s; pointer-events: none; z-index: 20;"></div>
            </div>

            <div style="background: #f8f8f8; border: 4px solid #303030; border-radius: 0 0 8px 8px; padding: 15px; height: 160px; display: flex; flex-direction: column; justify-content: space-between;" class="pkm-font">
                
                <div id="combat-log-box" style="font-size: 22px; color: #303030; line-height: 1.2; height: 50px; overflow: hidden;">
                    UM ${dados.mob.nome} SELVAGEM APARECEU!<br>O QUE VOCÊ VAI FAZER?
                </div>

                <div id="menu-botoes" style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px;">
                    <button class="pkm-font pkm-btn" onclick="iniciarAnimacaoLog()">⚔️ ATACAR</button>
                    <button class="pkm-font pkm-btn" onclick="exibirAlertaCustom('Aviso', 'Magias em desenvolvimento!', false)">✨ MAGIAS</button>
                    <button class="pkm-font pkm-btn" onclick="exibirAlertaCustom('Aviso', 'Mochila em desenvolvimento!', false)">🎒 MOCHILA</button>
                    <button class="pkm-font pkm-btn" onclick="sairDaArena()">🏃 FUGIR</button>
                </div>
                
               <div id="botoes-fim-batalha" style="display: none; gap: 10px; margin-top: 10px;">
                    <button class="pkm-font pkm-btn" onclick="sairDaArena()" style="flex: 1; justify-content: center; background: #303030; color: white; font-size: 18px;">⬅️ SAIR</button>
                    <button class="pkm-font pkm-btn" onclick="iniciarCacadaApp()" style="flex: 1.5; justify-content: center; background: #27ae60; color: white; border-color: #1e8449; font-size: 18px;">⚔️ CAÇAR DE NOVO</button>
                </div>
        `;

    } catch(e) {
        console.error(e);
        exibirAlertaCustom("Erro", "Falha de conexão com a arena.", false);
        carregarReino();
    }
}

// Essa função simula a "Troca de Turno" rodando o log do backend
function iniciarAnimacaoLog() {
    document.getElementById('menu-botoes').style.display = 'none';
    const logBox = document.getElementById('combat-log-box');
    
    const elemSpriteMob = document.getElementById('sprite-mob');
    const elemSpritePlayer = document.getElementById('sprite-player');
    const flash = document.getElementById('damage-flash');
    
    let db = window.dadosCombateAtual;
    let index = 0;

    const intervaloCombate = setInterval(() => {
        if (index >= db.log.length) {
            clearInterval(intervaloCombate);
            
            if (db.vitoria) {
                elemSpriteMob.style.opacity = "0";
                tocarSFX(AUDIO_ASSETS.som_vitoria);
            } else {
                elemSpritePlayer.style.opacity = "0";
            }

            setTimeout(() => finalizarAnimacaoCombate(db), 1000);
            return;
        }

        const acao = db.log[index];
        
        if (acao.atacante === "player") {
            logBox.innerHTML = `⚔️ VOCÊ ATACA!<br><span style="color:#27ae60;">${acao.texto.toUpperCase()}</span>`;
            
            db.mobHpAtual -= acao.dano;
            atualizarVisualBarra('bar-hp-mob', db.mobHpAtual, db.mobHpMax, false);

            if (acao.texto.toUpperCase().includes("CRÍTICO")) {
                tocarSFX(AUDIO_ASSETS.som_critico);
                animarCorteVisual('sprite-mob', '#f1c40f'); 
            } else {
                tocarSFX(AUDIO_ASSETS.som_espada);
                animarCorteVisual('sprite-mob', '#e74c3c'); 
            }

            elemSpritePlayer.style.transform = "translate(15px, -15px)";
            elemSpriteMob.style.transform = "translate(10px, -5px) scale(0.9)";
            setTimeout(() => {
                elemSpritePlayer.style.transform = "translate(0, 0)";
                elemSpriteMob.style.transform = "translate(0, 0) scale(1)";
            }, 150);

        } else if (acao.atacante === "mob") {
            logBox.innerHTML = `🩸 O INIMIGO ATACA!<br><span style="color:#c0392b;">${acao.texto.toUpperCase()}</span>`;
            
            db.playerHpAtual -= acao.dano;
            atualizarVisualBarra('bar-hp-player', db.playerHpAtual, db.playerHpMax, false);

            tocarSFX(AUDIO_ASSETS.som_monstro);
            animarCorteVisual('sprite-player', '#9b59b6');

            elemSpriteMob.style.transform = "translate(-15px, 15px)";
            elemSpritePlayer.style.transform = "translate(-10px, 5px) scale(0.9)";
            flash.style.opacity = "1";
            setTimeout(() => {
                elemSpriteMob.style.transform = "translate(0, 0)";
                elemSpritePlayer.style.transform = "translate(0, 0) scale(1)";
                flash.style.opacity = "0";
            }, 150);
        }

        index++;
    }, 1200); // Mais lento pra dar tempo de ler como no GBA
}

function finalizarAnimacaoCombate(dados) {
    document.getElementById('combat-log-box').innerHTML = dados.vitoria ? "O INIMIGO FOI DERROTADO!" : "VOCÊ DESMAIOU...";
    document.getElementById('btn-voltar-combate').style.display = "flex";
    
    if (dados.vitoria) {
        let lootTexto = dados.recompensas.items.length > 0 ? `<br><br>📦 Saqueou: ${dados.recompensas.items.join(', ')}` : "";
        exibirAlertaCustom("Vitória!", `✨ +${dados.recompensas.xp} XP<br>💰 +${dados.recompensas.gold} Ouro${lootTexto}`, true);
    } else {
        exibirAlertaCustom("Derrota", "Você desmaiou em combate e foi resgatado...", false);
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