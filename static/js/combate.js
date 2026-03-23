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
// Cole os links dos seus arquivos .mp3 ou .ogg aqui!
// ==========================================
const AUDIO_ASSETS = {
    bgm_batalha: "https://github.com/user-attachments/files/26172245/psychronic-crystal-hunter-281389.mp3", // Música tocando em loop
    som_espada: "https://github.com/user-attachments/files/26172264/attack.mp3",     // Som de ataque do herói
    som_critico: "https://github.com/user-attachments/files/26172289/phatphrogstudio-rpg-female-attack-grunt-no-ai-481720.mp3",     // Som de impacto forte
    som_monstro: "https://github.com/user-attachments/files/26172322/voicebosch-snarls-and-growls-172823.mp3",  // Som de garra ou magia inimiga
    som_vitoria: "https://github.com/user-attachments/files/26172334/eaglaxle-gaming-victory-464016.mp3" // Toca quando o mob morre
};

let musicaDeFundoAtual = null; // Variável para controlar a música

// Função auxiliar para tocar Efeitos Sonoros
function tocarSFX(url) {
    if (!url || url.includes("LINK_")) return; // Ignora se o link for o placeholder
    let sfx = new Audio(url);
    sfx.volume = 0.6; // Volume dos golpes (0.0 a 1.0)
    sfx.play().catch(e => console.log("Áudio bloqueado:", e));
}

// Função auxiliar para criar a Animação Visual de Corte
function animarCorteVisual(alvoId, cor_brilho) {
    const alvo = document.getElementById(alvoId);
    if (!alvo) return;

    // Cria a "lâmina" de energia
    const corte = document.createElement('div');
    corte.className = 'slash-effect';
    corte.style.boxShadow = `0 0 10px #fff, 0 0 20px ${cor_brilho}`; // Cor do clarão
    
    // Posiciona exatamente no meio do alvo
    corte.style.left = (alvo.offsetLeft + alvo.offsetWidth / 2) + 'px';
    corte.style.top = (alvo.offsetTop + alvo.offsetHeight / 2) + 'px';

    alvo.parentElement.appendChild(corte);

    // Remove o efeito da tela após a animação (0.3s)
    setTimeout(() => corte.remove(), 300);
}

// ==========================================
// SISTEMA DE COMBATE ANIMADO E REALISTA
// ==========================================
async function iniciarCacadaApp() {
    const conteudo = document.getElementById('aba-reino');
    const charId = localStorage.getItem("jogadorEldoraID");

    conteudo.innerHTML = `
        <div style="height: 300px; display: flex; flex-direction: column; justify-content: center; align-items: center;">
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

        // TOCA A MÚSICA DE FUNDO 🎵
        if (AUDIO_ASSETS.bgm_batalha && !AUDIO_ASSETS.bgm_batalha.includes("LINK_")) {
            musicaDeFundoAtual = new Audio(AUDIO_ASSETS.bgm_batalha);
            musicaDeFundoAtual.loop = true;
            musicaDeFundoAtual.volume = 0.3; // Volume da música mais baixo que o dos golpes
            musicaDeFundoAtual.play().catch(e => console.log("Áudio bloqueado:", e));
        }

        const bgArena = FUNDOS_ARENAS[dados.regiao] || "https://placehold.co/600x400/111/222?text=Arena+Desconhecida";
        const urlSpritePlayer = SPRITES_COSTA[dados.classe_player] || SPRITES_COSTA["aventureiro"];

        // Adicionamos a tag <style> com a animação mágica do corte
        conteudo.innerHTML = `
            <style>
                @keyframes animCorte {
                    0% { width: 0px; opacity: 1; transform: translate(-50%, -50%) rotate(45deg); }
                    50% { width: 120px; opacity: 1; transform: translate(-50%, -50%) rotate(45deg); }
                    100% { width: 160px; opacity: 0; transform: translate(-50%, -50%) rotate(45deg); }
                }
                .slash-effect {
                    position: absolute;
                    height: 4px;
                    background: #fff;
                    border-radius: 50%;
                    z-index: 30;
                    pointer-events: none;
                    animation: animCorte 0.3s ease-out forwards;
                }
            </style>

            <div style="background: url('${bgArena}') center bottom / cover no-repeat; aspect-ratio: 3 / 2; width: 100%; box-sizing: border-box; border-radius: 12px; border: 2px solid #f39c12; position: relative; overflow: hidden; margin-bottom: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.8);">
                
                <div style="position: absolute; top:0; left:0; width:100%; box-sizing: border-box; padding: 10px 15px 30px 15px; background: linear-gradient(to bottom, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0) 100%); display: flex; flex-direction: column; gap: 5px; z-index: 10;">
                    
                    <div style="display: flex; justify-content: space-between; align-items: flex-end; width: 100%; box-sizing: border-box;">
                        <div style="color: #fff; font-weight: 900; font-size: 0.9em; text-shadow: 1px 1px 3px #000; width: 45%;">Você</div>
                        <div style="color: #fff; font-weight: 900; font-size: 0.9em; text-shadow: 1px 1px 3px #000; text-align: right; width: 50%; line-height: 1.1; word-wrap: break-word;">${dados.mob.nome}</div>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; width: 100%; box-sizing: border-box;">
                        <div style="width: 45%; height: 10px; background: rgba(0,0,0,0.7); border-radius: 5px; border: 1px solid #111; box-shadow: 0 0 5px #000;">
                            <div id="bar-hp-player" style="width: 100%; height: 100%; background: linear-gradient(90deg, #27ae60, #2ecc71); border-radius: 4px; transition: width 0.3s;"></div>
                        </div>
                        <div style="width: 45%; height: 10px; background: rgba(0,0,0,0.7); border-radius: 5px; border: 1px solid #111; box-shadow: 0 0 5px #000; transform: scaleX(-1);">
                            <div id="bar-hp-mob" style="width: 100%; height: 100%; background: linear-gradient(90deg, #c0392b, #e74c3c); border-radius: 4px; transition: width 0.3s;"></div>
                        </div>
                    </div>
                </div>

                <div id="arena-characters" style="position: absolute; bottom: 10%; left:0; width: 100%; box-sizing: border-box; display: flex; justify-content: space-between; align-items: flex-end; padding: 0 15px; z-index: 5;">
                    <img id="sprite-player" src="${urlSpritePlayer}" style="height: 125px; max-width: 45%; object-fit: contain; filter: drop-shadow(3px 12px 4px rgba(0,0,0,0.6)); transition: transform 0.15s ease, opacity 0.3s;">
                    <img id="sprite-mob" src="${dados.mob.imagem}" onerror="this.src='https://placehold.co/150x150/transparent/e74c3c?text=👹'" style="height: 125px; max-width: 50%; object-fit: contain; filter: drop-shadow(-3px 12px 4px rgba(0,0,0,0.6)); transition: transform 0.15s ease, opacity 0.3s;">
                </div>
                
                <div id="damage-flash" style="position: absolute; top:0; left:0; width:100%; height:100%; background: rgba(231, 76, 60, 0.4); opacity: 0; transition: opacity 0.1s; pointer-events: none; z-index: 20;"></div>
            </div>

            <div style="background: linear-gradient(180deg, #020617, #0f172a); border: 2px solid #334155; border-radius: 8px; padding: 15px; height: 160px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; box-shadow: inset 0 0 15px rgba(0,0,0,0.9);" id="combat-log-box">
                <div style="color: #f1c40f; text-align: center; font-weight: bold; margin-bottom: 5px; border-bottom: 1px solid #334155; padding-bottom: 5px;">⚔️ Um ${dados.mob.nome} selvagem ataca!</div>
            </div>
            
            <button id="btn-voltar-combate" onclick="sairDaArena()" style="width: 100%; background: linear-gradient(90deg, #1e293b, #0f172a); padding: 14px; border: 1px solid #334155; color: #cbd5e1; border-radius: 8px; margin-top: 15px; display: none; cursor: pointer; font-weight: bold; text-transform: uppercase; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">⬅️ Sair da Arena</button>
        `;

        const logBox = document.getElementById('combat-log-box');
        const elemSpriteMob = document.getElementById('sprite-mob');
        const elemSpritePlayer = document.getElementById('sprite-player');
        const flash = document.getElementById('damage-flash');

        let playerHpAtual = dados.player.hp_max;
        let mobHpAtual = dados.mob.hp_max;

        let index = 0;
        const intervaloCombate = setInterval(() => {
            if (index >= dados.log.length) {
                clearInterval(intervaloCombate);
                
                if (dados.vitoria) {
                    elemSpriteMob.style.opacity = "0";
                    tocarSFX(AUDIO_ASSETS.som_vitoria); // Toca fanfarra!
                } else {
                    elemSpritePlayer.style.opacity = "0";
                }

                setTimeout(() => finalizarAnimacaoCombate(dados), 1000);
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

                // EFEITO SONORO E VISUAL DO JOGADOR 🎵✨
                if (acao.texto.includes("CRÍTICO")) {
                    tocarSFX(AUDIO_ASSETS.som_critico);
                    animarCorteVisual('sprite-mob', '#f1c40f'); // Clarão Dourado
                } else {
                    tocarSFX(AUDIO_ASSETS.som_espada);
                    animarCorteVisual('sprite-mob', '#e74c3c'); // Clarão Vermelho
                }

                // Animação Movimento
                elemSpritePlayer.style.transform = "translateX(20px)";
                elemSpriteMob.style.transform = "translateX(15px) scale(0.9)";
                setTimeout(() => {
                    elemSpritePlayer.style.transform = "translateX(0)";
                    elemSpriteMob.style.transform = "translateX(0) scale(1)";
                }, 150);

            } else if (acao.atacante === "mob") {
                pElem.style.color = "#e74c3c";
                pElem.innerHTML = acao.texto;
                
                playerHpAtual -= acao.dano;
                const pctPlayer = Math.max(0, (playerHpAtual / dados.player.hp_max) * 100);
                document.getElementById('bar-hp-player').style.width = pctPlayer + '%';

                // EFEITO SONORO E VISUAL DO MONSTRO 🎵✨
                tocarSFX(AUDIO_ASSETS.som_monstro);
                animarCorteVisual('sprite-player', '#9b59b6'); // Clarão Roxo no jogador

                // Animação Movimento e Piscar
                elemSpriteMob.style.transform = "translateX(-20px)";
                elemSpritePlayer.style.transform = "translateX(-10px) scale(0.9)";
                flash.style.opacity = "1";
                setTimeout(() => {
                    elemSpriteMob.style.transform = "translateX(0)";
                    elemSpritePlayer.style.transform = "translateX(0) scale(1)";
                    flash.style.opacity = "0";
                }, 150);
            } else {
                pElem.style.color = "#f39c12";
                pElem.innerHTML = acao.texto;
            }

            logBox.appendChild(pElem);
            logBox.scrollTop = logBox.scrollHeight;
            index++;
        }, 900); 

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
            ? `<br><br><span style="color:#a855f7; font-weight: bold;">📦 Saqueou: ${dados.recompensas.items.join(', ')}</span>`
            : "";
            
        exibirAlertaCustom(
            "Vitória!", 
            `O inimigo tombou!<br><br>✨ +${dados.recompensas.xp} XP<br>💰 +${dados.recompensas.gold} Ouro${lootTexto}`, 
            true
        );
    } else {
        exibirAlertaCustom(
            "Derrota", 
            "Você desmaiou em combate e foi resgatado... Perdeu experiência.", 
            false
        );
    }
}

// Função para parar a música ao sair da arena
function sairDaArena() {
    if (musicaDeFundoAtual) {
        musicaDeFundoAtual.pause(); // Para a música
        musicaDeFundoAtual.currentTime = 0; // Reseta o áudio
        musicaDeFundoAtual = null;
    }
    carregarReino(); // Volta pro mapa
}