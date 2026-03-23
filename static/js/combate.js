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

    // --- NOVA TELA DE CARREGAMENTO MODERNA ---
    conteudo.innerHTML = `
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800&display=swap');
            
            .loading-container {
                height: 380px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                font-family: 'Poppins', sans-serif;
                background: radial-gradient(circle, #0f172a 0%, #020617 100%);
                border-radius: 16px;
                border: 1px solid #1e293b;
                box-shadow: inset 0 0 30px rgba(0,0,0,0.8), 0 10px 20px rgba(0,0,0,0.5);
                margin-top: 10px;
            }
            .loading-ring {
                width: 70px;
                height: 70px;
                border-radius: 50%;
                border: 4px solid transparent;
                border-top-color: #ef4444; /* Vermelho HP */
                border-bottom-color: #3b82f6; /* Azul MP */
                animation: spinLoader 1.2s linear infinite;
                margin-bottom: 25px;
                position: relative;
            }
            .loading-ring:before {
                content: '';
                position: absolute;
                top: 5px; left: 5px; right: 5px; bottom: 5px;
                border-radius: 50%;
                border: 4px solid transparent;
                border-left-color: #f1c40f; /* Dourado Ouro */
                animation: spinLoader 0.8s linear infinite reverse;
            }
            .loading-icon {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size: 1.5em;
                /* O ícone dentro não gira, só os anéis em volta */
            }
            .loading-title {
                color: #f8fafc;
                font-size: 1.3em;
                font-weight: 800;
                letter-spacing: 1.5px;
                text-transform: uppercase;
                margin: 0;
                animation: pulseText 2s ease-in-out infinite;
                text-shadow: 0 0 10px rgba(255,255,255,0.2);
            }
            .loading-subtitle {
                color: #64748b;
                font-size: 0.9em;
                margin-top: 8px;
                font-weight: 600;
            }
            @keyframes spinLoader { 100% { transform: rotate(360deg); } }
            @keyframes pulseText { 
                0%, 100% { opacity: 0.7; } 
                50% { opacity: 1; text-shadow: 0 0 15px rgba(255,255,255,0.5); } 
            }
        </style>
        
        <div class="loading-container">
            <div class="loading-ring">
                <div class="loading-icon" style="animation: spinLoader 1.2s linear infinite reverse;">⚔️</div>
            </div>
            <h3 class="loading-title">Rastreando Inimigo</h3>
            <p class="loading-subtitle">Empunhe sua arma e prepare-se...</p>
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

        // --- NOVO VISUAL DA ARENA (SLIM E ELEGANTE COMPLETO) ---
        conteudo.innerHTML = `
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800&display=swap');
                
                @keyframes animCorte {
                    0% { width: 0px; opacity: 1; transform: translate(-50%, -50%) rotate(45deg); }
                    50% { width: 120px; opacity: 1; transform: translate(-50%, -50%) rotate(45deg); }
                    100% { width: 160px; opacity: 0; transform: translate(-50%, -50%) rotate(45deg); }
                }
                .slash-effect { position: absolute; height: 4px; background: #fff; border-radius: 50%; z-index: 30; pointer-events: none; animation: animCorte 0.3s ease-out forwards; }
                
                .modern-font { font-family: 'Poppins', sans-serif; }
                
                /* Caixas de HUD - Muito mais finas */
                .modern-hud {
                    position: absolute;
                    background: linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(2, 6, 23, 0.9) 100%);
                    border: 1px solid #334155;
                    border-radius: 8px; 
                    padding: 6px 10px; 
                    color: #f8fafc;
                    box-shadow: 0 4px 10px rgba(0,0,0,0.5);
                    z-index: 10;
                    backdrop-filter: blur(2px);
                }

                #hud-monstro { top: 10px; left: 10px; width: 150px; border-top: 2px solid #e74c3c; }
                #hud-jogador { bottom: 10px; right: 10px; width: 150px; border-top: 2px solid #3b82f6; }

                .hud-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; border-bottom: 1px solid #1e293b; padding-bottom: 4px; }
                .hud-name { font-size: 0.8em; font-weight: 800; margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 75%; }
                .hud-level { font-size: 0.6em; color: #cbd5e1; font-weight: 800; background: rgba(255,255,255,0.1); padding: 1px 4px; border-radius: 4px; }

                .hud-bar-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
                .hud-bar-label { font-size: 0.65em; font-weight: 800; letter-spacing: 0.5px; }
                .label-hp { color: #ef4444; }
                .label-mp { color: #3b82f6; }

                .hud-bar-bg { width: 78%; height: 4px; background-color: #0f172a; border-radius: 2px; border: 1px solid #1e293b; overflow: hidden; }
                .hud-hp-fill { height: 100%; background: linear-gradient(90deg, #ef4444, #b91c1c); transition: width 0.3s ease; }
                .hud-mp-fill { height: 100%; background: linear-gradient(90deg, #3b82f6, #1d4ed8); transition: width 0.3s ease; }

                /* Botões Compactos */
                .modern-btn {
                    background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
                    border: 1px solid #334155;
                    border-radius: 6px;
                    padding: 8px 5px; 
                    font-size: 0.85em; 
                    color: #f8fafc;
                    font-weight: 600;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 6px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                    transition: all 0.2s ease;
                }
                .modern-btn:active:not(:disabled) { transform: translateY(2px); border-color: #64748b; }
                .btn-atk { border-bottom: 2px solid #ef4444; }
                .btn-mag { border-bottom: 2px solid #8b5cf6; }
                .btn-bag { border-bottom: 2px solid #f59e0b; }
                .btn-run { border-bottom: 2px solid #64748b; }
            </style>

            <div id="arena-box" class="modern-font" style="background: url('${bgArena}') center bottom / cover no-repeat; height: 320px; width: 100%; border-radius: 12px 12px 0 0; border: 1px solid #334155; border-bottom: none; position: relative; overflow: hidden; box-shadow: 0 5px 15px rgba(0,0,0,0.5);">
                
                <div style="position: absolute; width: 100%; height: 100%; background: radial-gradient(circle, rgba(0,0,0,0) 40%, rgba(0,0,0,0.3) 100%); pointer-events: none;"></div>

                <div id="hud-monstro" class="modern-hud">
                    <div class="hud-header">
                        <h4 class="hud-name">${est.mob_nome}</h4>
                        <span class="hud-level">LV.${est.monster_level || '??'}</span>
                    </div>
                    <div class="hud-bar-row">
                        <span class="hud-bar-label label-hp">HP</span>
                        <div class="hud-bar-bg"><div id="bar-hp-mob" class="hud-hp-fill" style="width: 100%;"></div></div>
                    </div>
                </div>

                <div id="hud-jogador" class="modern-hud">
                    <div class="hud-header">
                        <h4 class="hud-name">VOCÊ</h4>
                        <span class="hud-level">LV.${est.player_level || '??'}</span>
                    </div>
                    <div class="hud-bar-row">
                        <span class="hud-bar-label label-hp">HP</span>
                        <div class="hud-bar-bg"><div id="bar-hp-player" class="hud-hp-fill" style="width: 100%;"></div></div>
                    </div>
                    <div class="hud-bar-row">
                        <span class="hud-bar-label label-mp">MP</span>
                        <div class="hud-bar-bg"><div id="bar-mp-player" class="hud-mp-fill" style="width: 100%;"></div></div>
                    </div>
                </div>

                <img id="sprite-player" src="${urlSpritePlayer}" style="position: absolute; bottom: 10px; left: 10px; height: 120px; object-fit: contain; filter: drop-shadow(3px 10px 4px rgba(0,0,0,0.5)); transition: transform 0.1s;">
                <img id="sprite-mob" src="${est.mob_img}" onerror="this.src='https://placehold.co/150x150/transparent/e74c3c?text=👹'" style="position: absolute; bottom: 65px; right: 15px; height: 110px; object-fit: contain; filter: drop-shadow(-3px 10px 4px rgba(0,0,0,0.5)); transition: transform 0.1s;">
                <div id="damage-flash" style="position: absolute; top:0; left:0; width:100%; height:100%; background: rgba(231, 76, 60, 0.4); opacity: 0; transition: opacity 0.1s; pointer-events: none; z-index: 20;"></div>
            </div>

            <div style="background: #020617; border: 1px solid #334155; border-radius: 0 0 12px 12px; padding: 10px; display: flex; flex-direction: column; gap: 8px;" class="modern-font">
                
                <div id="combat-log-box" style="font-size: 0.9em; font-weight: 600; color: #cbd5e1; line-height: 1.3; height: 42px; overflow: hidden; background: #0f172a; padding: 6px 10px; border-radius: 6px; border: 1px solid #1e293b; box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);">
                    <span style="color: #ef4444;">Um ${est.mob_nome} selvagem apareceu!</span><br>O que você vai fazer?
                </div>

                <div id="menu-botoes" style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                    <button class="modern-font modern-btn btn-atk" onclick="executarAcaoTurno('atacar')"><span>⚔️</span> Atacar</button>
                    <button class="modern-font modern-btn btn-mag" onclick="exibirAlertaCustom('Aviso', 'Magias em breve!', false)"><span>✨</span> Magias</button>
                    <button class="modern-font modern-btn btn-bag" onclick="exibirAlertaCustom('Aviso', 'Mochila em breve!', false)"><span>🎒</span> Mochila</button>
                    <button class="modern-font modern-btn btn-run" onclick="executarAcaoTurno('fugir')"><span>🏃</span> Fugir</button>
                </div>
                
               <div id="botoes-fim-batalha" style="display: none; gap: 8px;">
                    <button class="modern-font modern-btn" onclick="sairDaArena()" style="flex: 1; background: #1e293b; border-color: #334155;">⬅️ Sair</button>
                    <button class="modern-font modern-btn" onclick="iniciarCacadaApp()" style="flex: 1.5; background: linear-gradient(180deg, #16a34a 0%, #15803d 100%); border-color: #14532d; color: white;">⚔️ Caçar Novamente</button>
                </div>
            </div>
        `;

        // Seta as barras iniciais (MANTÉM IGUAL PARA A ANIMAÇÃO FUNCIONAR)
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