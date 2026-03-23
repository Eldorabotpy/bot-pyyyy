// ==========================================
// 1. DICIONÁRIO DE CENÁRIOS E CLASSES
// ==========================================
const FUNDOS_ARENAS = {
    "pradaria_inicial": "https://github.com/user-attachments/assets/8978e977-c5da-4d78-851a-ae28452b10ec", 
    "floresta_sombria": "https://placehold.co/600x400/2c3e50/111?text=Cenario+Floresta",
    "pedreira_granito": "https://placehold.co/600x400/7f8c8d/111?text=Cenario+Pedras",
    "reino_eldora": "https://placehold.co/600x400/2980b9/111?text=Cenario+Reino"
};

// 👇 AQUI FICAM AS 10 IMAGENS BASE DE COSTAS (PNG Transparente) 👇
const SPRITES_COSTA = {
    "aventureiro": "https://github.com/user-attachments/assets/6621c6b9-691f-45dd-b738-7915bb576f53", // Skin de quem tá sem classe
    "guerreiro": "LINK_GITHUB_GUERREIRO_COSTA.png",
    "berserker": "LINK_GITHUB_BERSERKER_COSTA.png",
    "cacador": "LINK_GITHUB_CACADOR_COSTA.png",
    "monge": "LINK_GITHUB_MONGE_COSTA.png",
    "mago": "LINK_GITHUB_MAGO_COSTA.png",
    "bardo": "LINK_GITHUB_BARDO_COSTA.png",
    "assassino": "LINK_GITHUB_ASSASSINO_COSTA.png",
    "samurai": "LINK_GITHUB_SAMURAI_COSTA.png",
    "curandeiro": "LINK_GITHUB_CURANDEIRO_COSTA.png"
};

// Dicionário para descobrir a base de qualquer evolução
const MAPA_CLASSES_BASE = {
    // Aventureiro (Sem classe)
    'aventureiro': 'aventureiro', 'aprendiz': 'aventureiro',

    // Guerreiro e evoluções
    'guerreiro': 'guerreiro', 'cavaleiro': 'guerreiro', 'gladiador': 'guerreiro', 'templario': 'guerreiro', 'guardiao_divino': 'guerreiro',
    
    // Berserker
    'berserker': 'berserker', 'barbaro': 'berserker', 'juggernaut': 'berserker', 'ira_primordial': 'berserker',
    
    // Caçador
    'cacador': 'cacador', 'patrulheiro': 'cacador', 'franco_atirador': 'cacador', 'olho_de_aguia': 'cacador',
    
    // Monge
    'monge': 'monge', 'guardiao_do_templo': 'monge', 'punho_elemental': 'monge', 'ascendente': 'monge',
    
    // Mago
    'mago': 'mago', 'feiticeiro': 'mago', 'elementalista': 'mago', 'arquimago': 'mago',
    
    // Bardo
    'bardo': 'bardo', 'menestrel': 'bardo', 'encantador': 'bardo', 'maestro': 'bardo',
    
    // Assassino
    'assassino': 'assassino', 'ladrao_de_sombras': 'assassino', 'ninja': 'assassino', 'mestre_das_laminas': 'assassino',
    
    // Samurai
    'samurai': 'samurai', 'kensei': 'samurai', 'ronin': 'samurai', 'shogun': 'samurai',
    
    // Curandeiro
    'curandeiro': 'curandeiro', 'clerigo': 'curandeiro', 'druida': 'curandeiro', 'sacerdote': 'curandeiro'
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
// NOVO SISTEMA DE COMBATE (ESTILO POKÉMON GBA)
// ==========================================
async function iniciarCacadaApp() {
    if (musicaDeFundoAtual) {
        musicaDeFundoAtual.pause(); 
        musicaDeFundoAtual.currentTime = 0; 
        musicaDeFundoAtual = null;
    }

    const conteudo = document.getElementById('aba-reino');
    const charId = localStorage.getItem("jogadorEldoraID");

    conteudo.innerHTML = `
        <div style="height: 300px; display: flex; flex-direction: column; justify-content: center; align-items: center; font-family: sans-serif;">
            <div style="font-size: 3em; animation: pulseRing 1s infinite;">⚔️</div>
            <h3 style="color: #e74c3c; margin-top: 15px; font-style: italic;">Adentrando a selva...</h3>
        </div>
    `;

    try {
        const res = await fetch('/api/combate/iniciar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: charId })
        });
        
        if (!res.ok) throw new Error(`Servidor recusou a conexão (Erro ${res.status}).`);
        
        const dados = await res.json();
        if (dados.erro) {
            exibirAlertaCustom("Aviso", dados.erro, false);
            carregarReino();
            return;
        }

        if (AUDIO_ASSETS.bgm_batalha) {
            musicaDeFundoAtual = new Audio(AUDIO_ASSETS.bgm_batalha);
            musicaDeFundoAtual.loop = true;
            musicaDeFundoAtual.volume = 0.3;
            musicaDeFundoAtual.play().catch(e => console.log("Áudio bloqueado"));
        }

        const est = dados.estado;
        const bgArena = FUNDOS_ARENAS[est.regiao] || "https://placehold.co/600x400/111/222?text=Arena+Desconhecida";
        const urlSpritePlayer = SPRITES_COSTA[dados.classe_player] || SPRITES_COSTA["aventureiro"];
        
        // Salvando estado para as animações de barra
        window.dadosCombateAtual = {
            mobNome: est.mob_nome,
            playerHpMax: est.player_stats.max_hp,
            playerMpMax: est.player_stats.max_mana,
            mobHpMax: est.monster_stats.max_hp,
            mobHpAtual: est.monster_hp,
            playerHpAtual: est.player_hp
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
                .pkm-font { font-family: 'VT323', monospace; text-transform: uppercase; letter-spacing: 1px; }
                
                /* HUD ESTILO ESCURO TRANSPARENTE */
                .pkm-hud-container {
                    position: absolute; background-color: rgba(0, 0, 0, 0.7);
                    border-radius: 5px; padding: 8px 12px; color: white;
                    box-shadow: 0px 4px 6px rgba(0,0,0,0.3); z-index: 10; width: 170px; 
                }
                .pkm-green-text { color: #50c878; } 
                .pkm-blue-text { color: #3498db; }
                #pkm-hud-monstro { top: 15px; left: 15px; border-top-left-radius: 15px; }
                #pkm-hud-jogador { bottom: 25px; right: 15px; width: 190px; border-bottom-right-radius: 15px; }

                .pkm-info-row { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 5px; }
                .pkm-name { font-size: 20px; font-weight: bold; }
                .pkm-level { font-size: 16px; color: white; text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000; }
                .pkm-hp-row, .pkm-mp-row { display: flex; align-items: center; justify-content: flex-end; margin-bottom: 5px; }
                .pkm-hp-label, .pkm-mp-label { font-size: 14px; font-weight: bold; margin-right: 5px; }

                .pkm-bar-container { width: 110px; height: 8px; background-color: #505050; border: 2px solid #303030; border-radius: 2px; position: relative; overflow: hidden; }
                .hp-bar-fill { height: 100%; background-color: #2ecc71; transition: width 0.3s ease, background-color 0.3s ease; }
                .mp-bar-fill { height: 100%; background-color: #3498db; transition: width 0.3s ease; }

                .pkm-btn { background: #fff; border: 3px solid #606060; border-radius: 8px; padding: 12px; font-size: 20px; color: #303030; cursor: pointer; transition: 0.1s; display: flex; align-items: center; gap: 8px;}
                .pkm-btn:active:not(:disabled) { transform: translateY(2px); }
                .pkm-btn:disabled { opacity: 0.5; cursor: not-allowed; }
            </style>

            <div id="arena-box" class="pkm-font" style="background: url('${bgArena}') center bottom / cover no-repeat; height: 350px; width: 100%; border: 4px solid #303030; border-bottom: none; position: relative; overflow: hidden;">
                
                <div id="pkm-hud-monstro" class="pkm-hud-container">
                    <div class="pkm-info-row">
                        <span class="pkm-name pkm-green-text">${est.mob_nome}</span>
                        <span class="pkm-level">LV${est.monster_level || '??'}</span>
                    </div>
                    <div class="pkm-hp-row">
                        <span class="pkm-hp-label pkm-green-text">HP</span>
                        <div class="pkm-bar-container"><div id="bar-hp-mob" class="hp-bar-fill"></div></div>
                    </div>
                </div>

                <div id="pkm-hud-jogador" class="pkm-hud-container">
                    <div class="pkm-info-row">
                        <span class="pkm-name pkm-green-text">VOCÊ</span>
                        <span class="pkm-level">LV${est.player_level || '??'}</span>
                    </div>
                    <div class="pkm-hp-row">
                        <span class="pkm-hp-label pkm-green-text">HP</span>
                        <div class="pkm-bar-container"><div id="bar-hp-player" class="hp-bar-fill"></div></div>
                    </div>
                    <div class="pkm-mp-row">
                        <span class="pkm-mp-label pkm-blue-text">MP</span>
                        <div class="pkm-bar-container"><div id="bar-mp-player" class="mp-bar-fill"></div></div>
                    </div>
                </div>

                <img id="sprite-player" src="${urlSpritePlayer}" style="position: absolute; bottom: 10px; left: 10px; height: 130px; object-fit: contain; filter: drop-shadow(3px 10px 4px rgba(0,0,0,0.5)); transition: transform 0.1s;">
                <img id="sprite-mob" src="${est.mob_img}" style="position: absolute; bottom: 80px; right: 15px; height: 120px; object-fit: contain; filter: drop-shadow(-3px 10px 4px rgba(0,0,0,0.5)); transition: transform 0.1s;">
                <div id="damage-flash" style="position: absolute; top:0; left:0; width:100%; height:100%; background: rgba(231, 76, 60, 0.4); opacity: 0; transition: opacity 0.1s; pointer-events: none; z-index: 20;"></div>
            </div>

            <div style="background: #f8f8f8; border: 4px solid #303030; border-radius: 0 0 8px 8px; padding: 15px; height: 160px; display: flex; flex-direction: column; justify-content: space-between;" class="pkm-font">
                <div id="combat-log-box" style="font-size: 22px; color: #303030; line-height: 1.2; height: 50px; overflow: hidden;">
                    UM ${est.mob_nome} SELVAGEM APARECEU!<br>O QUE VOCÊ VAI FAZER?
                </div>

                <div id="menu-botoes" style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px;">
                    <button class="pkm-font pkm-btn" onclick="executarAcaoTurno('atacar')">⚔️ ATACAR</button>
                    <button class="pkm-font pkm-btn" onclick="exibirAlertaCustom('Aviso', 'Magias em breve!', false)">✨ MAGIAS</button>
                    <button class="pkm-font pkm-btn" onclick="exibirAlertaCustom('Aviso', 'Mochila em breve!', false)">🎒 MOCHILA</button>
                    <button class="pkm-font pkm-btn" onclick="executarAcaoTurno('fugir')">🏃 FUGIR</button>
                </div>
                
               <div id="botoes-fim-batalha" style="display: none; gap: 10px; margin-top: 10px;">
                    <button class="pkm-font pkm-btn" onclick="sairDaArena()" style="flex: 1; justify-content: center; background: #303030; color: white;">⬅️ SAIR</button>
                    <button class="pkm-font pkm-btn" onclick="iniciarCacadaApp()" style="flex: 1.5; justify-content: center; background: #27ae60; color: white;">⚔️ CAÇAR DE NOVO</button>
                </div>
            </div>
        `;

        atualizarVisualBarra('bar-hp-mob', est.monster_hp, window.dadosCombateAtual.mobHpMax);
        atualizarVisualBarra('bar-hp-player', est.player_hp, window.dadosCombateAtual.playerHpMax);
        atualizarVisualBarra('bar-mp-player', est.player_mp, window.dadosCombateAtual.playerMpMax, true);

    } catch(e) {
        console.error(e);
        exibirAlertaCustom("Erro", e.message, false);
        carregarReino();
    }
}

// ==========================================
// NOVA FUNÇÃO: EXECUTA A AÇÃO NO BACKEND
// ==========================================
async function executarAcaoTurno(tipoAcao) {
    document.getElementById('menu-botoes').style.display = 'none';
    const logBox = document.getElementById('combat-log-box');
    logBox.innerHTML = "CALCULANDO...";
    
    const charId = localStorage.getItem("jogadorEldoraID");

    try {
        const res = await fetch('/api/combate/acao', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: charId, acao: tipoAcao })
        });
        const turno = await res.json();

        if (turno.erro) {
            exibirAlertaCustom("Erro", turno.erro, false);
            sairDaArena();
            return;
        }

        if (turno.fugiu) {
            logBox.innerHTML = `💨 ${turno.log[0].texto.toUpperCase()}`;
            setTimeout(() => sairDaArena(), 1500);
            return;
        }

        animarAcoesDaRodada(turno);

    } catch(e) {
        exibirAlertaCustom("Erro", "Conexão perdida.", false);
        sairDaArena();
    }
}

// ==========================================
// NOVA FUNÇÃO: LÊ O QUE O PYTHON MANDOU E ANIMA
// ==========================================
function animarAcoesDaRodada(turnoInfo) {
    const logBox = document.getElementById('combat-log-box');
    const elemSpriteMob = document.getElementById('sprite-mob');
    const elemSpritePlayer = document.getElementById('sprite-player');
    const flash = document.getElementById('damage-flash');
    let db = window.dadosCombateAtual;
    let indexAcao = 0;

    function lerProximoLog() {
        if (indexAcao >= turnoInfo.log.length) {
            if (turnoInfo.vitoria || turnoInfo.derrota) {
                if (turnoInfo.vitoria) {
                    elemSpriteMob.style.opacity = "0";
                    tocarSFX(AUDIO_ASSETS.som_vitoria);
                } else {
                    elemSpritePlayer.style.opacity = "0";
                }
                setTimeout(() => finalizarAnimacaoCombate(turnoInfo), 1000);
            } else {
                document.getElementById('menu-botoes').style.display = 'grid';
                logBox.innerHTML = `O QUE VOCÊ VAI FAZER?`;
            }
            return;
        }

        const acao = turnoInfo.log[indexAcao];

        if (acao.autor === "player") {
            logBox.innerHTML = `⚔️ VOCÊ ATACA!<br><span style="color:#27ae60;">${acao.texto.toUpperCase()}</span>`;
            db.mobHpAtual -= acao.dano;
            atualizarVisualBarra('bar-hp-mob', db.mobHpAtual, db.mobHpMax);
            
            tocarSFX(acao.texto.includes("CRÍTICO") ? AUDIO_ASSETS.som_critico : AUDIO_ASSETS.som_espada);
            animarCorteVisual('sprite-mob', acao.texto.includes("CRÍTICO") ? '#f1c40f' : '#e74c3c');

            elemSpritePlayer.style.transform = "translate(15px, -15px)";
            setTimeout(() => { elemSpritePlayer.style.transform = "translate(0, 0)"; }, 150);
        } 
        else if (acao.autor === "mob") {
            logBox.innerHTML = `🩸 INIMIGO ATACA!<br><span style="color:#c0392b;">${acao.texto.toUpperCase()}</span>`;
            db.playerHpAtual -= acao.dano;
            atualizarVisualBarra('bar-hp-player', db.playerHpAtual, db.playerHpMax);

            tocarSFX(AUDIO_ASSETS.som_monstro);
            animarCorteVisual('sprite-player', '#9b59b6');
            flash.style.opacity = "1";
            elemSpriteMob.style.transform = "translate(-15px, 15px)";
            setTimeout(() => { elemSpriteMob.style.transform = "translate(0, 0)"; flash.style.opacity = "0"; }, 150);
        }

        indexAcao++;
        setTimeout(lerProximoLog, 1400); 
    }
    lerProximoLog();
}

function finalizarAnimacaoCombate(dados) {
    document.getElementById('combat-log-box').innerHTML = dados.vitoria ? "O INIMIGO FOI DERROTADO!" : "VOCÊ DESMAIOU...";
    document.getElementById('botoes-fim-batalha').style.display = "flex";
    
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