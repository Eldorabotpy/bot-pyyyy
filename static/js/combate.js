// ==========================================
// 1. DICIONÁRIO DE CENÁRIOS DAS ARENAS
// ==========================================
const FUNDOS_ARENAS = {
    "pradaria_inicial": "https://github.com/user-attachments/assets/3a16a7b1-69f4-4563-9493-20f07cf0b228", 
    "floresta_sombria": "LINK_DA_FLORESTA",
    "pedreira_granito": "LINK_DA_PEDREIRA",
    "defesa_reino": "https://placehold.co/600x400/2980b9/111?text=Invasao+do+Reino" // Fundo para o evento de invasão!
};

// ==========================================
// 2. DICIONÁRIO DAS CLASSES (DE COSTAS EM PNG)
// ==========================================
const SPRITES_COSTA = {
    "aventureiro": "https://github.com/Eldorabotpy/personagem-costa-/issues/1#issue-4117552988", 
    "assassino": "https://github.com/Eldorabotpy/personagem-costa-/issues/2#issue-4117557838",
    "guerreiro": "https://placehold.co/200x300/transparent/fff?text=Guerreiro",
    "mago": "https://placehold.co/200x300/transparent/fff?text=Mago",
    "arqueiro": "https://placehold.co/200x300/transparent/fff?text=Arqueiro"
};

// ==========================================
// SISTEMA DE COMBATE ANIMADO E REALISTA
// ==========================================
async function iniciarCacadaApp() {
    const conteudo = document.getElementById('aba-reino');
    const charId = localStorage.getItem("jogadorEldoraID");

    // Tela de Carregamento
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

        // CORREÇÃO: Nomes de variáveis separados para não dar conflito
        const bgArena = FUNDOS_ARENAS[dados.regiao] || "https://placehold.co/600x400/111/222?text=Arena+Desconhecida";
        const urlSpritePlayer = SPRITES_COSTA[dados.classe_player] || SPRITES_COSTA["aventureiro"];

        // DESENHA A ARENA IMERSIVA
        conteudo.innerHTML = `
            <div style="background: url('${bgArena}') center/cover; height: 260px; border-radius: 12px; border: 2px solid #f39c12; position: relative; overflow: hidden; margin-bottom: 20px; box-shadow: 0 5px 15px rgba(0,0,0,0.8);">
                
                <div style="position: absolute; top:0; left:0; width:100%; height: 70px; background: linear-gradient(to bottom, rgba(0,0,0,0.8), transparent);"></div>
                
                <div style="position: absolute; top: 12px; width: 100%; display: flex; justify-content: space-between; padding: 0 15px; z-index: 10;">
                    <div style="width: 42%;">
                        <div style="color: white; font-weight: 900; font-size: 0.9em; margin-bottom: 4px; text-shadow: 2px 2px 3px #000;">Você</div>
                        <div style="width: 100%; height: 12px; background: rgba(0,0,0,0.8); border-radius: 6px; border: 2px solid #111; box-shadow: 0 0 5px #000;">
                            <div id="bar-hp-player" style="width: 100%; height: 100%; background: linear-gradient(90deg, #27ae60, #2ecc71); transition: 0.3s;"></div>
                        </div>
                    </div>

                    <div style="width: 42%; text-align: right;">
                        <div style="color: white; font-weight: 900; font-size: 0.9em; margin-bottom: 4px; text-shadow: 2px 2px 3px #000;">${dados.mob.nome}</div>
                        <div style="width: 100%; height: 12px; background: rgba(0,0,0,0.8); border-radius: 6px; border: 2px solid #111; box-shadow: 0 0 5px #000; transform: scaleX(-1);">
                            <div id="bar-hp-mob" style="width: 100%; height: 100%; background: linear-gradient(90deg, #c0392b, #e74c3c); transition: 0.3s;"></div>
                        </div>
                    </div>
                </div>

                <div style="position: absolute; bottom: 5px; width: 100%; display: flex; justify-content: space-between; align-items: flex-end; padding: 0 20px;">
                    <img id="sprite-player" src="${urlSpritePlayer}" style="height: 140px; object-fit: contain; filter: drop-shadow(4px 10px 5px rgba(0,0,0,0.6)); transition: 0.15s;">
                    
                    <img id="sprite-mob" src="${dados.mob.imagem}" onerror="this.src='https://placehold.co/150x150/transparent/e74c3c?text=👹'" style="height: 150px; object-fit: contain; filter: drop-shadow(-4px 10px 5px rgba(0,0,0,0.6)); transition: 0.15s; margin-bottom: 30px;">
                </div>
                
                <div id="damage-flash" style="position: absolute; top:0; left:0; width:100%; height:100%; background: rgba(231, 76, 60, 0.5); opacity: 0; transition: 0.1s; pointer-events: none;"></div>
            </div>

            <div style="background: linear-gradient(180deg, #020617, #0f172a); border: 2px solid #334155; border-radius: 8px; padding: 15px; height: 150px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; box-shadow: inset 0 0 15px rgba(0,0,0,0.9);" id="combat-log-box">
                <div style="color: #f1c40f; text-align: center; font-weight: bold; margin-bottom: 5px; border-bottom: 1px solid #334155; padding-bottom: 5px;">⚔️ Um ${dados.mob.nome} selvagem ataca!</div>
            </div>
            
            <button id="btn-voltar-combate" onclick="carregarReino()" style="width: 100%; background: linear-gradient(90deg, #1e293b, #0f172a); padding: 14px; border: 1px solid #334155; color: #cbd5e1; border-radius: 8px; margin-top: 15px; display: none; cursor: pointer; font-weight: bold; text-transform: uppercase;">⬅️ Sair da Arena</button>
        `;

        // ----------------------------------------------------
        // ANIMAÇÃO DE GOLPES E TREMIDAS DE TELA
        // ----------------------------------------------------
        const logBox = document.getElementById('combat-log-box');
        const elemSpriteMob = document.getElementById('sprite-mob');
        // CORREÇÃO: Nova variável para controlar o HTML da foto na animação
        const elemSpritePlayer = document.getElementById('sprite-player');
        const flash = document.getElementById('damage-flash');

        let playerHpAtual = dados.player.hp_max;
        let mobHpAtual = dados.mob.hp_max;

        let index = 0;
        const intervaloCombate = setInterval(() => {
            if (index >= dados.log.length) {
                clearInterval(intervaloCombate);
                
                if (dados.vitoria) elemSpriteMob.style.opacity = "0";
                else elemSpritePlayer.style.opacity = "0";

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