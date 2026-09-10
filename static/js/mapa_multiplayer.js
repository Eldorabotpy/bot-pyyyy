// ==========================================
// 🛡️ HUD DO GRUPO (BOTÃO FLUTUANTE)
// ==========================================
window.desenharMiniHudGrupo = function(grupo) {
    let hud = document.getElementById('eldora-party-hud');
    const meuId = localStorage.getItem("jogadorEldoraID");
    
    // Proteção: Se eu não estou na lista, apaga o HUD
    if (!grupo.membros.includes(meuId)) {
        if (hud) hud.remove();
        return;
    }

    if (!hud) {
        hud = document.createElement('div');
        hud.id = 'eldora-party-hud';
        
        hud.style.cssText = `
            position: absolute; top: 180px; left: 10px; z-index: 50;
            font-family: 'Cinzel', serif; color: white; display: flex; align-items: flex-start; gap: 10px;
        `;
        
        const telaJogo = document.getElementById('aba-reino') || document.body;
        telaJogo.appendChild(hud);
    }

    // Verifica se a lista estava aberta antes de atualizar
    let painelAberto = false;
    const painelExistente = document.getElementById('eldora-party-lista');
    if (painelExistente && painelExistente.style.display !== 'none') {
        painelAberto = true;
    }

    // Link da imagem oficial enviada
    const urlIconeGrupo = "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/ui/grupo.png";

    let html = `
        <button onclick="window.toggleListaGrupo()" style="background: linear-gradient(145deg, #0f172a, #1e293b); border: 2px solid #ca8a04; border-radius: 50%; width: 30px; height: 30px; cursor: pointer; box-shadow: 0 4px 10px rgba(0,0,0,0.8); display: flex; flex-direction: column; align-items: center; justify-content: center; transition: transform 0.2s; padding: 0;" onmouseover="this.style.transform='scale(1.1)'" onmouseout="this.style.transform='scale(1)'" title="Abrir/Fechar Lista do Grupo">
            
            <img src="${urlIconeGrupo}" style="width: 26px; height: 26px; object-fit: contain; margin-bottom: 1px; filter: drop-shadow(0 2px 2px rgba(0,0,0,0.5));">
            
            <span style="font-size: 10px; font-weight: bold; color: #facc15; font-family: Arial, sans-serif; text-shadow: 0 1px 3px #000; line-height: 1;">
                ${grupo.membros.length}/5
            </span>
        </button>

        <div id="eldora-party-lista" style="display: ${painelAberto ? 'block' : 'none'}; background: rgba(15, 23, 42, 0.9); border: 1px solid #ca8a04; border-radius: 8px; padding: 8px; min-width: 140px; box-shadow: 0 5px 15px rgba(0,0,0,0.7); backdrop-filter: blur(5px);">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #ca8a04; padding-bottom: 5px; margin-bottom: 8px;">
                <h4 style="color: #facc15; margin: 0; font-size: 0.8em; letter-spacing: 1px;">ALIADOS</h4>
                <button onclick="sairDoGrupoEldora()" style="background: #ef4444; color: white; border: none; border-radius: 4px; padding: 2px 6px; cursor: pointer; font-family: Arial; font-weight: bold; font-size: 0.7em; transition: 0.2s;" onmouseover="this.style.background='#b91c1c'" onmouseout="this.style.background='#ef4444'" title="Abandonar Grupo">X</button>
            </div>
            <div style="display: flex; flex-direction: column; gap: 4px;">
    `;
    
    grupo.membros.forEach(id => {
        let nome = grupo.nomes_membros ? grupo.nomes_membros[id] : "Herói";
        let ehLider = (grupo.lider === id);
        
        html += `
            <div style="background: rgba(0,0,0,0.4); padding: 5px 8px; border-radius: 4px; display: flex; align-items: center; gap: 5px;">
                <span style="font-size: 1em;">${ehLider ? '👑' : '🛡️'}</span>
                <span style="font-size: 0.8em; font-weight: bold; color: ${ehLider ? '#facc15' : '#e2e8f0'}; font-family: 'Segoe UI', Arial, sans-serif; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 110px;">
                    ${nome}
                </span>
            </div>
        `;
    });
    html += `</div></div>`;
    
    hud.innerHTML = html;
};

// Nova função para abrir e fechar a lista
window.toggleListaGrupo = function() {
    let painel = document.getElementById('eldora-party-lista');
    if (painel) {
        painel.style.display = (painel.style.display === 'none') ? 'block' : 'none';
    }
};

window.sairDoGrupoEldora = function() {
    if (confirm("Tem certeza que deseja abandonar seus aliados?")) {
        if (window.eldoraSocket) window.eldoraSocket.emit('sairGrupo', {});
        let hud = document.getElementById('eldora-party-hud');
        if (hud) hud.remove();
    }
};

// ==========================================
// 🛡️ UI PREMIUM: CONVITE DE GRUPO
// ==========================================
window.exibirConviteGrupoCustom = function(dados, socket) {
    const antigo = document.getElementById('eldora-convite-bg');
    if (antigo) antigo.remove();

    const overlay = document.createElement('div');
    overlay.id = 'eldora-convite-bg';
    overlay.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(6px);
        display: flex; justify-content: center; align-items: center;
        z-index: 100000; opacity: 0; transition: opacity 0.3s ease;
    `;

    const caixa = document.createElement('div');
    caixa.style.cssText = `
        background: linear-gradient(145deg, #0f172a, #1e293b);
        border: 2px solid #ca8a04; border-radius: 12px;
        padding: 30px 25px; text-align: center; min-width: 320px; max-width: 85%;
        box-shadow: 0 20px 50px rgba(0,0,0,0.9), inset 0 0 15px rgba(202, 138, 4, 0.15);
        transform: scale(0.8) translateY(30px); transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        font-family: 'Cinzel', serif; color: #f8fafc;
    `;

    caixa.innerHTML = `
        <h3 style="margin: 0 0 15px 0; color: #facc15; font-size: 1.5em; text-shadow: 0 2px 4px #000; letter-spacing: 1px;">
            ⚔️ CONVITE DE GRUPO ⚔️
        </h3>
        <p style="margin: 0 0 25px 0; font-size: 1.1em; line-height: 1.6; color: #e2e8f0; font-family: 'Segoe UI', Arial, sans-serif;">
            O líder <strong style="color: #60a5fa; font-size: 1.15em;">${dados.remetente_nome}</strong> convidou-te para formar um Grupo!<br><br>
        </p>
        <div style="display: flex; gap: 12px; justify-content: center;">
            <button id="btn-recusar-grupo" style="flex: 1; background: #334155; border: 1px solid #475569; color: #cbd5e1; padding: 12px; border-radius: 6px; cursor: pointer; font-family: 'Cinzel', serif; font-weight: bold;">RECUSAR</button>
            <button id="btn-aceitar-grupo" style="flex: 1; background: linear-gradient(180deg, #10b981, #059669); border: 1px solid #047857; color: #fff; padding: 12px; border-radius: 6px; cursor: pointer; font-family: 'Cinzel', serif; font-weight: bold; text-shadow: 0 1px 2px #000;">ACEITAR</button>
        </div>
    `;

    overlay.appendChild(caixa);
    document.body.appendChild(overlay);

    requestAnimationFrame(() => { overlay.style.opacity = '1'; caixa.style.transform = 'scale(1) translateY(0)'; });

    const fecharModal = () => {
        overlay.style.opacity = '0'; caixa.style.transform = 'scale(0.8) translateY(30px)';
        setTimeout(() => overlay.remove(), 300);
    };

    document.getElementById('btn-recusar-grupo').onclick = fecharModal;
    document.getElementById('btn-aceitar-grupo').onclick = () => { socket.emit('aceitarGrupo', { party_id: dados.party_id }); fecharModal(); };
};

// ==========================================
// ⚔️ UI PREMIUM: CONVITE DE DUELO (PVP)
// ==========================================
window.exibirConviteDueloCustom = function(dados) {
    const antigo = document.getElementById('eldora-convite-duelo-bg');
    if (antigo) antigo.remove();

    const overlay = document.createElement('div');
    overlay.id = 'eldora-convite-duelo-bg';
    overlay.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(6px);
        display: flex; justify-content: center; align-items: center;
        z-index: 100000; opacity: 0; transition: opacity 0.3s ease;
    `;

    const caixa = document.createElement('div');
    // 👇 Fundo escuro com um leve degradê vermelho sangue
    caixa.style.cssText = `
        background: linear-gradient(145deg, #1e0f0f, #3b1e1e); 
        border: 2px solid #ef4444; border-radius: 12px;
        padding: 30px 25px; text-align: center; min-width: 320px; max-width: 85%;
        box-shadow: 0 20px 50px rgba(0,0,0,0.9), inset 0 0 15px rgba(239, 68, 68, 0.15);
        transform: scale(0.8) translateY(30px); transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        font-family: 'Cinzel', serif; color: #f8fafc;
    `;

    caixa.innerHTML = `
        <h3 style="margin: 0 0 15px 0; color: #ef4444; font-size: 1.5em; text-shadow: 0 2px 4px #000; letter-spacing: 1px;">
            ⚔️ DESAFIO DE DUELO ⚔️
        </h3>
        <p style="margin: 0 0 25px 0; font-size: 1.1em; line-height: 1.6; color: #e2e8f0; font-family: 'Segoe UI', Arial, sans-serif;">
            O herói <strong style="color: #facc15; font-size: 1.15em;">${dados.remetente_nome}</strong> te desafiou para a Arena!<br>
            <span style="font-size: 0.85em; color: #94a3b8;">Você aceita provar o seu valor?</span>
        </p>
        <div style="display: flex; gap: 12px; justify-content: center;">
            <button id="btn-recusar-duelo" style="flex: 1; background: #334155; border: 1px solid #475569; color: #cbd5e1; padding: 12px; border-radius: 6px; cursor: pointer; font-family: 'Cinzel', serif; font-weight: bold; transition: 0.2s;">FUGIR</button>
            <button id="btn-aceitar-duelo" style="flex: 1; background: linear-gradient(180deg, #dc2626, #991b1b); border: 1px solid #7f1d1d; color: #fff; padding: 12px; border-radius: 6px; cursor: pointer; font-family: 'Cinzel', serif; font-weight: bold; text-shadow: 0 1px 2px #000; transition: 0.2s;">LUTAR</button>
        </div>
    `;

    overlay.appendChild(caixa);
    document.body.appendChild(overlay);

    requestAnimationFrame(() => { overlay.style.opacity = '1'; caixa.style.transform = 'scale(1) translateY(0)'; });

    const fecharModal = () => {
        overlay.style.opacity = '0'; caixa.style.transform = 'scale(0.8) translateY(30px)';
        setTimeout(() => overlay.remove(), 300);
    };

    // Animações de Hover dos botões
    document.getElementById('btn-recusar-duelo').onmouseover = function() { this.style.background = '#475569'; };
    document.getElementById('btn-recusar-duelo').onmouseout = function() { this.style.background = '#334155'; };
    document.getElementById('btn-aceitar-duelo').onmouseover = function() { this.style.background = '#ef4444'; };
    document.getElementById('btn-aceitar-duelo').onmouseout = function() { this.style.background = 'linear-gradient(180deg, #dc2626, #991b1b)'; };

    // Conectando os cliques aos eventos do Socket
    document.getElementById('btn-recusar-duelo').onclick = () => {
        if (window.eldoraSocket) window.eldoraSocket.emit('recusarDuelo', { desafiante_id: dados.remetente_id });
        fecharModal();
    };
    
    document.getElementById('btn-aceitar-duelo').onclick = () => { 
        if (window.eldoraSocket) window.eldoraSocket.emit('aceitarDuelo', { desafiante_id: dados.remetente_id });
        fecharModal(); 
    };
};

// ==========================================
// 🤝 UI PREMIUM: CONVITE DE AMIZADE
// ==========================================
window.exibirConviteAmizadeCustom = function(dados) {
    const antigo = document.getElementById('eldora-convite-amizade-bg');
    if (antigo) antigo.remove();

    const overlay = document.createElement('div');
    overlay.id = 'eldora-convite-amizade-bg';
    overlay.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(6px);
        display: flex; justify-content: center; align-items: center;
        z-index: 100000; opacity: 0; transition: opacity 0.3s ease;
    `;

    const caixa = document.createElement('div');
    // 👇 Fundo com degradê azul noturno e esmeralda para simbolizar aliança/paz
    caixa.style.cssText = `
        background: linear-gradient(145deg, #0f172a, #064e3b);
        border: 2px solid #10b981; border-radius: 12px;
        padding: 30px 25px; text-align: center; min-width: 320px; max-width: 85%;
        box-shadow: 0 20px 50px rgba(0,0,0,0.9), inset 0 0 15px rgba(16, 185, 129, 0.15);
        transform: scale(0.8) translateY(30px); transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        font-family: 'Cinzel', serif; color: #f8fafc;
    `;

    caixa.innerHTML = `
        <h3 style="margin: 0 0 15px 0; color: #34d399; font-size: 1.5em; text-shadow: 0 2px 4px #000; letter-spacing: 1px;">
            🤝 NOVA ALIANÇA 🤝
        </h3>
        <p style="margin: 0 0 25px 0; font-size: 1.1em; line-height: 1.6; color: #e2e8f0; font-family: 'Segoe UI', Arial, sans-serif;">
            O herói <strong style="color: #facc15; font-size: 1.15em;">${dados.remetente_nome}</strong> deseja ser teu amigo!<br>
            <span style="font-size: 0.85em; color: #94a3b8;">Desejas forjar este laço?</span>
        </p>
        <div style="display: flex; gap: 12px; justify-content: center;">
            <button id="btn-recusar-amizade" style="flex: 1; background: #334155; border: 1px solid #475569; color: #cbd5e1; padding: 12px; border-radius: 6px; cursor: pointer; font-family: 'Cinzel', serif; font-weight: bold; transition: 0.2s;">RECUSAR</button>
            <button id="btn-aceitar-amizade" style="flex: 1; background: linear-gradient(180deg, #10b981, #059669); border: 1px solid #047857; color: #fff; padding: 12px; border-radius: 6px; cursor: pointer; font-family: 'Cinzel', serif; font-weight: bold; text-shadow: 0 1px 2px #000; transition: 0.2s;">ACEITAR</button>
        </div>
    `;

    overlay.appendChild(caixa);
    document.body.appendChild(overlay);

    requestAnimationFrame(() => { overlay.style.opacity = '1'; caixa.style.transform = 'scale(1) translateY(0)'; });

    const fecharModal = () => {
        overlay.style.opacity = '0'; caixa.style.transform = 'scale(0.8) translateY(30px)';
        setTimeout(() => overlay.remove(), 300);
    };

    // Hover dos botões
    document.getElementById('btn-recusar-amizade').onmouseover = function() { this.style.background = '#475569'; };
    document.getElementById('btn-recusar-amizade').onmouseout = function() { this.style.background = '#334155'; };
    document.getElementById('btn-aceitar-amizade').onmouseover = function() { this.style.background = '#059669'; };
    document.getElementById('btn-aceitar-amizade').onmouseout = function() { this.style.background = 'linear-gradient(180deg, #10b981, #059669)'; };

    // Cliques
    document.getElementById('btn-recusar-amizade').onclick = fecharModal;
    
    document.getElementById('btn-aceitar-amizade').onclick = () => { 
        if (window.eldoraSocket) window.eldoraSocket.emit('aceitarAmizade', { amigo_id: dados.remetente_id, amigo_nome: dados.remetente_nome });
        window.mostrarNotificacaoRPG(`Aliança forjada com ${dados.remetente_nome}!`, '🤝'); // Mostra a notificação de sucesso!
        fecharModal(); 
    };
};

window.mostrarLootInvasaoCompacto = function(dados) {
    if (!dados) return;

    let box = document.getElementById("toast-loot-invasao");

    if (!box) {
        box = document.createElement("div");
        box.id = "toast-loot-invasao";
        box.style.cssText = `
            position: fixed;
            left: 50%;
            top: 76px;
            transform: translateX(-50%) translateY(-10px);
            z-index: 1000002;
            width: min(88vw, 310px);
            background: rgba(2, 6, 23, .92);
            border: 1px solid rgba(250, 204, 21, .75);
            border-radius: 10px;
            box-shadow: 0 8px 22px rgba(0,0,0,.55);
            color: #fef3c7;
            font-family: Arial, sans-serif;
            font-size: 12px;
            line-height: 1.25;
            padding: 8px 10px;
            pointer-events: none;
            opacity: 0;
            transition: opacity .18s ease, transform .18s ease;
            text-align: center;
        `;
        document.body.appendChild(box);
    }

    const tipo = dados.tipo || "";
    const monstro = dados.monstro || dados.frente || "Invasão";

    const ouro = Number(dados.ouro || dados.gold || 0);
    const xp = Number(dados.xp || 0);
    const xpPasse = Number(dados.xp_passe || 0);
    const fragmentos = Number(dados.fragmentos || 0);

    let partes = [];

    if (ouro > 0) partes.push(`💰 +${ouro}`);
    if (xp > 0) partes.push(`🌟 +${xp} XP`);
    if (xpPasse > 0) partes.push(`🎫 +${xpPasse}`);
    if (fragmentos > 0) partes.push(`🏅 +${fragmentos}`);

    if (!partes.length) {
        const msg = String(dados.mensagem || "Recompensa recebida")
            .replace(/<br\s*\/?>/gi, " | ")
            .replace(/<[^>]+>/g, "");

        partes.push(msg);
    }

    box.innerHTML = `
        <div style="
            color:#facc15;
            font-weight:900;
            font-family:'Cinzel', Arial, sans-serif;
            font-size:12px;
            margin-bottom:3px;
            white-space:nowrap;
            overflow:hidden;
            text-overflow:ellipsis;
        ">
            🎁 ${tipo === "invasao_lacaio" ? "Lacaio derrotado" : "Recompensa da Invasão"}
        </div>

        <div style="
            color:#e2e8f0;
            font-size:11px;
            white-space:nowrap;
            overflow:hidden;
            text-overflow:ellipsis;
            margin-bottom:3px;
        ">
            ${String(monstro).replace(/<[^>]+>/g, "")}
        </div>

        <div style="
            color:#fef3c7;
            font-weight:800;
            font-size:12px;
            white-space:nowrap;
            overflow:hidden;
            text-overflow:ellipsis;
        ">
            ${partes.join("  |  ")}
        </div>
    `;

    clearTimeout(box.__timerLoot);

    box.style.opacity = "1";
    box.style.transform = "translateX(-50%) translateY(0)";

    box.__timerLoot = setTimeout(() => {
        box.style.opacity = "0";
        box.style.transform = "translateX(-50%) translateY(-10px)";
    }, 2200);
};

// ==========================================
// MOTOR MULTIPLAYER - MUNDO DE ELDORA
// ==========================================
class MotorMultiplayer {
    constructor(scene, socket) {
        this.scene = scene; this.socket = socket; window.eldoraSocket = socket;
        this.scene.outrosJogadores = this.scene.add.group();
        this.iniciarConexao(); this.iniciarEscutas();
    }
    
    atualizarPilula() {
        // 🌟 Agora usa a variável global em vez de contar os bonecos na tela
        let total = window.totalJogadoresOnline || 1;
        let textoContador = document.getElementById('online-count-text');
        if (textoContador) textoContador.innerText = total + " Online";
    }
    
    // ==========================================
    // 🧹 O FAXINEIRO BLINDADO (EVITA CRASHES)
    // ==========================================
    removerOutroJogador(id) {
        // Faz uma cópia da lista de jogadores na tela para não travar o loop
        const jogadoresNaTela = [...this.scene.outrosJogadores.getChildren()];
        
        jogadoresNaTela.forEach((velho) => {
            if (velho.playerId === id) {
                // 🛑 A MÁGICA ESTÁ AQUI: Paramos as animações antes de apagar!
                if (velho.movimentoTween) velho.movimentoTween.stop();
                if (velho.textoTween) velho.textoTween.stop();
                
                // 💣 Apaga as partes visuais
                if (velho.lapideAtiva) velho.lapideAtiva.destroy();
                if (velho.nomeTexto) velho.nomeTexto.destroy();
                if (velho.balaoAtivo) velho.balaoAtivo.destroy(); 
                
                // 👻 Manda o boneco para o além
                velho.destroy();
            }
        });
    }

    iniciarConexao() {
        const meuIdDoBanco = localStorage.getItem("jogadorEldoraID");
        const meuNome = localStorage.getItem("jogadorEldoraNome") || "Aventureiro";
        this.socket.emit('entrarRegiao', { regiao: this.scene.regiaoAtual, x: this.scene.player.x, y: this.scene.player.y, nome: meuNome, skin: this.scene.skinResolvida || this.scene.skinAtiva, char_id: meuIdDoBanco });
    }

    iniciarEscutas() {
        // 🛑 O ESCUDO ANTI-DUPLICAÇÃO: Limpa escutas antigas antes de criar novas!
        this.socket.off('novaMensagemChat');
        this.socket.off('receberListaAmigos');
        this.socket.off('receberConviteAmizade');
        this.socket.off('receberConviteGrupo');
        this.socket.off('connect');
        this.socket.off('solicitarRegistro');
        
        // 👇 ADICIONE ESTAS LINHAS AQUI PARA BLINDAR OS MONSTROS E JOGADORES:
        this.socket.off('carregarMobsMapa');
        this.socket.off('jogadoresAtuais');
        this.socket.off('novoJogador');
        this.socket.off('jogadorMoveu');
        this.socket.off('jogadorSaiu');
        this.socket.off('acaoMapa');
        this.socket.off('desconectarDuplicado');
        this.socket.off('forcarTeletransporte');
        this.socket.off('efeitoGlobalMapa');
        this.socket.off('lootRecebido');
        this.socket.off('iniciarRaidInterface');
        this.socket.off('animarTurnoRaid');

        this.socket.on('iniciarRaidInterface', function(estado_raid) {
            console.log("⚔️ O PORTAL DA RAID ABRIU!", estado_raid);
            if (typeof window.iniciarInterfaceRaid === 'function') {
                window.iniciarInterfaceRaid(estado_raid);
            }
        });

        this.socket.on('animarTurnoRaid', function(pacoteTurno) {
            console.log("⚔️ TURNO DE RAID RECEBIDO!", pacoteTurno);
            if (typeof window.processarAnimacaoTurnoRaid === 'function') {
                window.processarAnimacaoTurnoRaid(pacoteTurno);
            }
        });
        this.socket.on('lootRecebido', function(dados) {
            if (!dados) return;

            console.log("🎁 LOOT RECEBIDO:", dados);

            const meuId = String(localStorage.getItem("jogadorEldoraID") || "");
            const playerId = String(dados.player_id || dados.jogador_id || "");
   
            if (playerId && playerId !== meuId) return;

            const mensagemHtml = String(dados.mensagem || "Recompensa recebida!");

            if (typeof window.mostrarLootInvasaoCompacto === "function") {
                window.mostrarLootInvasaoCompacto(dados);
            }

            if (typeof window.raidAdicionarLog === "function" && window.raidInvasaoAtual) {
                window.raidAdicionarLog(`
                    <div style="
                        color:#facc15;
                        font-weight:900;
                        background:rgba(202,138,4,.10);
                        border:1px solid rgba(250,204,21,.35);
                        border-radius:8px;
                        padding:5px;
                        text-align:center;
                        margin-top:4px;
                        line-height:1.35;
                        font-size:11px;
                    ">
                        🎁 ${mensagemHtml}
                    </div>
                `);
            }
        });
        // 📡 Quando o servidor avisar que rolou um evento global...
        this.socket.on('efeitoGlobalMapa', (dados) => {
            if (dados.efeito === 'despertar_classe') {
                // Apenas os OUTROS jogadores rodam isso (para não duplicar a tela de quem já está vendo a luz da Selene)
                if (dados.jogador_id !== localStorage.getItem("jogadorEldoraID")) {
                    if (typeof window.tocarEfeitoGlobalDespertar === 'function') {
                        window.tocarEfeitoGlobalDespertar(dados.jogador_nome, dados.classe);
                    }
                }
            }
        });

        // Adicione dentro do método iniciarEscutas() da classe MotorMultiplayer
        this.socket.on('mostrar_lapide_global', (dados) => {
            this.scene.outrosJogadores.getChildren().forEach((outro) => {
                if (outro.nomeTexto && outro.nomeTexto.text === dados.nome) {
                    
                    // Se já houver uma lápide ativa, destrói antes de criar outra
                    if (outro.lapideAtiva) {
                        outro.lapideAtiva.destroy();
                    }

                    // Esconde a sprite do jogador e o seu nome
                    outro.setVisible(false);
                    outro.nomeTexto.setVisible(false);

                    // Cria a lápide e a atrela ao objeto do jogador
                    outro.lapideAtiva = this.scene.add.sprite(dados.x, dados.y, 'img_lapide')
                        .setOrigin(0.5, 1)
                        .setDisplaySize(28, 48)
                        .setDepth(5);
                }
            });
        });

        // 🛡️ O ESCUDO DE CONEXÃO: Impede que o Socket peça o histórico duas vezes no F5
        const chamarConexaoSegura = () => {
            if (window.travaConexaoF5) return; // Se já pediu há menos de 2 segundos, ignora!
            window.travaConexaoF5 = true;
            setTimeout(() => { window.travaConexaoF5 = false; }, 2000);
            this.iniciarConexao();
        };

        // 🛡️ O SEGREDO DO TELEGRAM MINI APP: Reconectar automaticamente!
        this.socket.on('connect', () => {
            console.log("🔌 Conectado ao reino! Registrando o herói...");
            chamarConexaoSegura(); // Usa a versão blindada!
        });

        if (typeof window.configurarOuvintesLojaReino === 'function') {
            window.configurarOuvintesLojaReino(this.socket);
        }

        // 🛡️ Se o servidor esquecer do jogador (app minimizado), ele pede os dados de novo
        this.socket.on('solicitarRegistro', () => {
            console.log("🔄 O servidor pediu nossos dados. Reconectando...");
            chamarConexaoSegura(); // Usa a versão blindada!
        });

        this.socket.on('desconectarDuplicado', () => { alert("🚨 A tua conta foi conectada noutro dispositivo!"); window.location.reload(); });
        this.socket.on('forcarTeletransporte', (dados) => { if (dados.player_id === localStorage.getItem("jogadorEldoraID")) this.scene.scene.restart({ regiao: dados.nova_regiao, skin: this.scene.skinAtiva, isRespawn: dados.is_respawn }); });
        
        // ==========================================
        // 🛡️ FILTROS EXORCISTAS (ANTI-FANTASMAS) 🛡️
        // ==========================================

        this.socket.on('jogadoresAtuais', (jogadores) => { 
            // 👇 SALVA O TOTAL GLOBAL QUE O SERVIDOR MANDOU 👇
            window.totalJogadoresOnline = Object.keys(jogadores).length;

            Object.keys(jogadores).forEach((id) => { 
                let infoPlayer = jogadores[id];
                // Continua desenhando só quem está na mesma região!
                if (id !== this.socket.id && infoPlayer.regiao === this.scene.regiaoAtual) {
                    this.adicionarOutroJogador(id, infoPlayer); 
                }
            }); 
            this.atualizarPilula(); 
        });

        this.socket.on('novoJogador', (info) => { 
            // 👇 SOMA 1 NO GLOBAL MESMO QUE ELE NASÇA EM OUTRO MAPA 👇
            window.totalJogadoresOnline = (window.totalJogadoresOnline || 1) + 1;

            if (info.regiao === this.scene.regiaoAtual) {
                this.adicionarOutroJogador(info.id, info); 
            }
            // Atualiza a pílula verde lá em cima!
            this.atualizarPilula(); 
        });

        this.socket.on('jogadorSaiu', (id) => { 
            this.removerOutroJogador(id); 
            
            // 👇 DIMINUI 1 DO GLOBAL (Garante que nunca mostre zero, pois você sempre está online) 👇
            window.totalJogadoresOnline = Math.max(1, (window.totalJogadoresOnline || 2) - 1);
            
            this.atualizarPilula(); 
        });
        
        // =====================================
        // 🏃 CORREÇÃO DO MOVIMENTO
        // =====================================
        this.socket.on('jogadorMoveu', (info) => {
            // Se o jogador que se moveu for para outra região, o Faxineiro apaga ele da nossa tela!
            if (info.regiao && info.regiao !== this.scene.regiaoAtual) {
                this.removerOutroJogador(info.id);
                return;
            }

            this.scene.outrosJogadores.getChildren().forEach((outro) => {
                if (outro.playerId === info.id) {
                    
                    // Se o jogador se moveu, destrói a lápide vinculada a ele
                    if (outro.lapideAtiva) {
                        outro.lapideAtiva.destroy();
                        outro.lapideAtiva = null;
                    }

                    // Restaura a visibilidade do jogador e do seu nome
                    if (!outro.visible) {
                        outro.setVisible(true);
                        if (outro.nomeTexto) outro.nomeTexto.setVisible(true);
                    }

                    let dist = Phaser.Math.Distance.Between(outro.x, outro.y, info.x, info.y);
                    if (dist < 5) { 
                        outro.setPosition(info.x, info.y); 
                        outro.nomeTexto.setPosition(info.x, info.y - 25); 
                        outro.anims.stop(); 
                        outro.setFrame(1); 
                        return; 
                    }
                    
                    let duracaoTempo = (dist / 150) * 1000; 
                    if (outro.movimentoTween) outro.movimentoTween.stop();
                    if (outro.textoTween) outro.textoTween.stop();
                    
                    let dx = info.x - outro.x, dy = info.y - outro.y;
                    let animacao = Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'right' : 'left') : (dy > 0 ? 'down' : 'up');
                    
                    let skinDele = outro.texture.key;
                    this.scene.gerarAnimacoes(skinDele); 
                    
                    try { 
                        outro.anims.play(animacao + '_' + skinDele, true); 
                    } catch(e){}
                    
                    outro.movimentoTween = this.scene.tweens.add({ 
                        targets: outro, 
                        x: info.x, 
                        y: info.y, 
                        duration: duracaoTempo, 
                        onComplete: () => { outro.anims.stop(); outro.setFrame(1); } 
                    });
                    
                    outro.textoTween = this.scene.tweens.add({ 
                        targets: outro.nomeTexto, 
                        x: info.x, 
                        y: info.y - 25, 
                        duration: duracaoTempo 
                    });
                }
            });
        });

        // 🚪 QUANDO ALGUÉM SAI DO JOGO
        this.socket.on('jogadorSaiu', (id) => { 
            this.removerOutroJogador(id); // Chama o Faxineiro!
            this.atualizarPilula(); 
        });
        
        // 💬 SISTEMA DE BALÕES NO MAPA E EMOJIS ANIMADOS 💬
        this.socket.on('acaoMapa', (dados) => {
            let alvo = null;
            const meuIdBanco = String(localStorage.getItem("jogadorEldoraID"));

            // 1. Sou eu? (Verifica pelo ID do Banco de Dados)
            if (String(dados.char_id) === meuIdBanco) {
                alvo = this.scene.player; 
            } 
            // 2. É outro jogador? (O mapa procura eles pelo ID de conexão)
            else {
                this.scene.outrosJogadores.getChildren().forEach(outro => {
                    if (outro.playerId === dados.socket_id) alvo = outro; 
                });
            }

            if (!alvo) return; // Se o cara não tá na minha tela, ignora.

            // Destrói o balão antigo se o cara flodar
            if (alvo.balaoAtivo) alvo.balaoAtivo.destroy();

            let balaoNovo = null;

            // (Daqui pra baixo continua com o código igualzinho)
            if (dados.tipo === "texto") {
                // 1. Texto Moderno: Cor clara e sombra suave para dar profundidade
                let textoBalao = this.scene.add.text(0, -12, dados.valor, {
                    fontSize: '12px', fontFamily: 'Arial', color: '#f8fafc', fontStyle: 'bold', 
                    align: 'center', wordWrap: { width: 180 }, // Um pouco mais largo
                    shadow: { offsetX: 1, offsetY: 1, color: '#000000', blur: 3, fill: true } // Efeito 3D sutil
                }).setOrigin(0.5, 1);

                // Aumentamos o "respiro" (padding) para não ficar espremido
                let largura = textoBalao.width + 24;
                let altura = textoBalao.height + 16;

                // 2. Desenha o Balão Moderno (Estilo Eldora UI)
                let fundoBalao = this.scene.add.graphics();
                
                // Fundo azul escuro meio transparente (combina com os seus menus)
                fundoBalao.fillStyle(0x0f172a, 0.85); 
                // Borda dourada fina elegante
                fundoBalao.lineStyle(1.5, 0xca8a04, 1); 
                
                // Caixa mais arredondada (radius 10)
                fundoBalao.fillRoundedRect(-largura/2, -altura - 6, largura, altura, 10);
                fundoBalao.strokeRoundedRect(-largura/2, -altura - 6, largura, altura, 10);
                
                // Rabinho do balão mais pontudo e elegante
                fundoBalao.beginPath();
                fundoBalao.moveTo(-6, -6);
                fundoBalao.lineTo(0, 4);   // Ponta desce um pouco mais
                fundoBalao.lineTo(6, -6);
                fundoBalao.closePath();
                fundoBalao.fillPath();
                fundoBalao.strokePath();
                
                // Apaga a borda dourada na base do rabinho para "emendar" perfeitamente
                fundoBalao.beginPath();
                fundoBalao.moveTo(-5, -6);
                fundoBalao.lineTo(5, -6);
                fundoBalao.lineStyle(3, 0x0f172a, 1); // Pinta com a cor do fundo!
                fundoBalao.strokePath();

                // 3. Junta tudo no Container
                balaoNovo = this.scene.add.container(alvo.x, alvo.y - 45, [fundoBalao, textoBalao]).setDepth(100);
            }
            else if (dados.tipo === "emoji") {
                balaoNovo = this.scene.add.sprite(alvo.x, alvo.y - 50, dados.valor).setDepth(100);
                try {
                    balaoNovo.play('anim_' + dados.valor); 
                } catch(e) { console.log("Animação não pronta."); }
            }

            alvo.balaoAtivo = balaoNovo;

            let atualizarBalao = () => {
                if (!alvo || !alvo.active || !alvo.balaoAtivo || alvo.balaoAtivo !== balaoNovo) {
                    this.scene.events.off('update', atualizarBalao); 
                    return;
                }
                alvo.balaoAtivo.setPosition(alvo.x, alvo.y - 50);
            };
            this.scene.events.on('update', atualizarBalao);

            setTimeout(() => {
                if (balaoNovo && balaoNovo.active) {
                    balaoNovo.destroy();
                    if (alvo.balaoAtivo === balaoNovo) alvo.balaoAtivo = null;
                }
            }, 5000);
        });

        // 🌟 SISTEMA DE ABAS DO CHAT (GLOBAL vs GRUPO vs PRIVADO) 🌟
        this.socket.on('novaMensagemChat', (msg) => {
            
            // 🛡️ O CADEADO DE PRIVACIDADE DO GRUPO (NOVO)
            if (msg.destinatarios) {
                const meuId = localStorage.getItem("jogadorEldoraID");
                // Se eu não estiver na lista de destinatários, aborto a mensagem!
                if (!msg.destinatarios.includes(meuId)) return; 
            }
            
            // 🛡️ O DESTRUIDOR DE CLONES: Garante que nenhuma mensagem repetida apareça
            if (msg.historico) {
                // Cria uma "identidade" para a mensagem
                const idMensagem = msg.remetente + "_" + msg.texto;
                window.historicoRecebido = window.historicoRecebido || new Set();
                
                // Se essa mensagem já foi desenhada na tela, ABORTA!
                if (window.historicoRecebido.has(idMensagem)) return; 
                
                // Se é a primeira vez, salva a identidade dela para bloquear os próximos clones
                window.historicoRecebido.add(idMensagem);
            }

            const chatBox = document.getElementById('chat-box');
            if (!chatBox) return;

            // Limpa as mensagens padrão de "Bem vindo"
            Array.from(chatBox.children).forEach(child => { if(child.tagName === 'P') child.remove(); });

            const linha = document.createElement('div');
            
            let canalDaMsg = 'global'; 
            if (msg.tipo === 'grupo' || msg.tipo === 'loot') canalDaMsg = 'grupo';
            else if (msg.tipo === 'privado') canalDaMsg = 'amigos';
            else if (msg.tipo === 'guilda' || msg.tipo === 'cla') canalDaMsg = 'guilda';
            
            linha.dataset.canal = canalDaMsg;

            // 🎨 VARIÁVEIS DE DESIGN PARA OS CARDS DE CHAT
            let bgCor, bordaCor, textoFormatado;
            
            // 📸 PUXANDO O AVATAR (Se o Python não mandar, usa o padrão automaticamente)
            let avatarFinal = msg.avatar || 'https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/avatares/avatar_padrao_m.png';

            if (msg.tipo === "grupo") {
                bgCor = "rgba(46, 204, 113, 0.1)"; bordaCor = "#2ecc71";
                textoFormatado = `
                    <div style="display: flex; gap: 10px;">
                        <div style="width: 32px; height: 32px; border-radius: 50%; border: 1px solid ${bordaCor}; flex-shrink: 0; overflow: hidden; box-shadow: 0 0 5px ${bordaCor};"><img src="${avatarFinal}" onerror="this.src='https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/avatares/avatar_padrao_m.png'" style="width: 100%; height: 100%; object-fit: cover;"></div>
                        <div style="flex-grow: 1; min-width: 0;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
                                <strong style="color: ${bordaCor}; font-size: 0.75em; text-transform: uppercase; letter-spacing: 1px;">${msg.remetente}</strong>
                                <span style="font-size: 0.6em; color: ${bordaCor}; opacity: 0.8;">⚔️ GRUPO</span>
                            </div>
                            <div style="color: #e2e8f0; font-size: 0.95em; line-height: 1.3;">${msg.texto}</div>
                        </div>
                    </div>
                `;
            } else if (msg.tipo === "loot") {
                bgCor = "rgba(241, 196, 15, 0.1)"; bordaCor = "#f1c40f";
                textoFormatado = `
                    <div style="display: flex; gap: 10px;">
                        <div style="width: 32px; height: 32px; border-radius: 50%; background: rgba(241, 196, 15, 0.2); display: flex; align-items: center; justify-content: center; flex-shrink: 0; border: 1px solid ${bordaCor};"><span style="font-size: 16px;">🎁</span></div>
                        <div style="flex-grow: 1; min-width: 0;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
                                <strong style="color: ${bordaCor}; font-size: 0.75em; text-transform: uppercase; letter-spacing: 1px;">SAQUE</strong>
                            </div>
                            <div style="color: #cbd5e1; font-style: italic; font-size: 0.9em; line-height: 1.3;">${msg.texto}</div>
                        </div>
                    </div>
                `;
            } else if (msg.tipo === "guilda" || msg.tipo === "cla") {
                bgCor = "rgba(155, 89, 182, 0.15)"; bordaCor = "#9b59b6";
                textoFormatado = `
                    <div style="display: flex; gap: 10px;">
                        <div style="width: 32px; height: 32px; border-radius: 50%; border: 1px solid ${bordaCor}; flex-shrink: 0; overflow: hidden; box-shadow: 0 0 5px ${bordaCor};"><img src="${avatarFinal}" onerror="this.src='https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/avatares/avatar_padrao_m.png'" style="width: 100%; height: 100%; object-fit: cover;"></div>
                        <div style="flex-grow: 1; min-width: 0;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
                                <strong style="color: ${bordaCor}; font-size: 0.75em; text-transform: uppercase; letter-spacing: 1px;">${msg.remetente}</strong>
                                <span style="font-size: 0.6em; color: ${bordaCor}; opacity: 0.8;">🛡️ CLÃ</span>
                            </div>
                            <div style="color: #e8daef; font-size: 0.95em; line-height: 1.3;">${msg.texto}</div>
                        </div>
                    </div>
                `;
            // 👇 1. ADICIONE ESTE BLOCO DO MERCADO AQUI 👇
            } else if (msg.tipo === "mercado") {
                bgCor = "rgba(202, 138, 4, 0.15)"; bordaCor = "#eab308";
                textoFormatado = `
                    <div style="display: flex; gap: 10px;">
                        <div style="width: 32px; height: 32px; border-radius: 50%; background: rgba(234, 179, 8, 0.2); display: flex; align-items: center; justify-content: center; flex-shrink: 0; border: 1px solid ${bordaCor}; box-shadow: 0 0 5px ${bordaCor};"><span style="font-size: 16px;">⚖️</span></div>
                        <div style="flex-grow: 1; min-width: 0;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
                                <strong style="color: ${bordaCor}; font-size: 0.75em; text-transform: uppercase; letter-spacing: 1px;">O MESTRE MERCADOR</strong>
                                <span style="font-size: 0.6em; color: ${bordaCor}; opacity: 0.8;">🪙 MERCADO</span>
                            </div>
                            <div style="color: #fef08a; font-weight: bold; font-size: 0.9em; line-height: 1.3;">${msg.texto}</div>
                        </div>
                    </div>
                `;    
            } else {
                // GLOBAL, PRIVADO E SISTEMA
                let isPrivado = msg.tipo === "privado";
                let isSistema = msg.tipo === "erro" || msg.remetente === "Sistema";

                if (isPrivado) { bgCor = "rgba(217, 70, 239, 0.1)"; bordaCor = "#d946ef"; } 
                else if (isSistema) { bgCor = "rgba(239, 68, 68, 0.1)"; bordaCor = "#ef4444"; } 
                else { bgCor = "rgba(56, 189, 248, 0.08)"; bordaCor = "#38bdf8"; }

                let corNome = isPrivado ? "#d946ef" : (isSistema ? "#ef4444" : "#38bdf8");
                let estiloTexto = isPrivado ? "font-style: italic; color: #f8fafc;" : (isSistema ? "color: #fca5a5;" : "color: #e2e8f0;");
                let prefixo = isPrivado ? "✉️ SUSSURRO" : (isSistema ? "⚠️ AVISO" : "🌍 GLOBAL");

                let acaoClique = (isPrivado && msg.nome_puro) ? `onclick="window.abrirChatPrivado('${msg.nome_puro}')"` : "";
                let cursorEstilo = (isPrivado && msg.nome_puro) ? "pointer" : "default";

                // Se for o sistema mandando aviso de erro, põe um ícone ⚠️ ao invés de foto
                let avatarHtml = isSistema 
                    ? `<div style="width: 32px; height: 32px; border-radius: 50%; background: rgba(239, 68, 68, 0.2); display: flex; align-items: center; justify-content: center; flex-shrink: 0; border: 1px solid ${bordaCor};"><span style="font-size: 16px;">⚠️</span></div>`
                    : `<div style="width: 32px; height: 32px; border-radius: 50%; border: 1px solid ${bordaCor}; flex-shrink: 0; overflow: hidden; background: #0f172a; box-shadow: 0 0 5px ${bordaCor};"><img src="${avatarFinal}" onerror="this.src='https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/avatares/avatar_padrao_m.png'" style="width: 100%; height: 100%; object-fit: cover;"></div>`;

                textoFormatado = `
                    <div style="display: flex; gap: 10px; cursor: ${cursorEstilo};" ${acaoClique}>
                        ${avatarHtml}
                        <div style="flex-grow: 1; min-width: 0;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
                                <strong style="color: ${corNome}; font-size: 0.8em; text-transform: uppercase; letter-spacing: 0.5px;">${msg.remetente}</strong>
                                <span style="font-size: 0.6em; color: ${bordaCor}; opacity: 0.7; letter-spacing: 0.5px; white-space: nowrap;">${prefixo}</span>
                            </div>
                            <div style="${estiloTexto} font-size: 0.9em; word-wrap: break-word; line-height: 1.3;">${msg.texto}</div>
                        </div>
                    </div>
                `;

                if (isPrivado && msg.nome_puro) linha.dataset.parceiro = msg.nome_puro;
            }

            // 🖌️ O ENVELOPE UNIVERSAL DA MENSAGEM (O Card)
            linha.style.cssText = `
                background: ${bgCor};
                border-left: 3px solid ${bordaCor};
                border-radius: 0 6px 6px 0;
                padding: 6px 10px;
                margin-bottom: 8px;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            `;
            linha.innerHTML = textoFormatado;

            chatBox.appendChild(linha);

            const abaAtiva = chatBox.dataset.abaAtiva || 'chat';
            const inputChat = document.getElementById('input-chat');
            const alvoAtual = inputChat ? inputChat.dataset.alvoPrivado : null;
            
            let mensagemEscondida = true;

            if (abaAtiva === 'chat' && canalDaMsg === 'global') {
                linha.style.display = 'block'; mensagemEscondida = false;
            } else if (abaAtiva === 'amigos' && canalDaMsg === 'amigos') {
                if (alvoAtual && linha.dataset.parceiro === alvoAtual) {
                    linha.style.display = 'block'; mensagemEscondida = false;
                } else {
                    linha.style.display = 'none';
                }
            } else if (abaAtiva === 'grupo' && canalDaMsg === 'grupo') {
                linha.style.display = 'block'; mensagemEscondida = false;
            } else if (abaAtiva === 'guilda' && canalDaMsg === 'guilda') {
                linha.style.display = 'block'; mensagemEscondida = false;
            } else {
                linha.style.display = 'none';
            }

            // 🔔 SISTEMA DE NOTIFICAÇÃO BLINDADO
            // Dispara se for uma mensagem Nova que você não viu, OU se for um histórico marcado como Não Lido pelo DB!
            let isNovaEscondida = (mensagemEscondida && msg.remetente !== "Sistema" && !msg.historico);
            let isHistoricoNaoLido = (msg.historico && msg.nao_lida);

            if (isNovaEscondida || isHistoricoNaoLido) {
                
                // 1. Contador para o Chat Privado
                if (canalDaMsg === 'amigos' && msg.nome_puro) {
                    window.notificacoesPrivadas = window.notificacoesPrivadas || {};
                    window.notificacoesPrivadas[msg.nome_puro] = (window.notificacoesPrivadas[msg.nome_puro] || 0) + 1;
                }

                // 2. Bolinhas de notificação nas abas internas
                document.querySelectorAll('.aba-soc').forEach(btn => {
                    let textoBotao = btn.innerText.toLowerCase();
                    let abaAlvo = false;

                    if (canalDaMsg === 'amigos' && textoBotao.includes('amigos')) abaAlvo = true;
                    if (canalDaMsg === 'grupo' && textoBotao.includes('grupo')) abaAlvo = true;
                    if (canalDaMsg === 'guilda' && textoBotao.includes('guilda')) abaAlvo = true;
                    if (canalDaMsg === 'global' && textoBotao.includes('chat')) abaAlvo = true;

                    if (abaAlvo) {
                        if (!btn.querySelector('.notificacao-badge')) {
                            btn.innerHTML += `<span class="notificacao-badge" style="background: #ef4444; color: white; border-radius: 50%; padding: 1px 6px; font-size: 0.7em; margin-left: 5px; box-shadow: 0 0 5px rgba(239, 68, 68, 0.8); vertical-align: middle;">!</span>`;
                        }
                    }
                });

                // 👇 3. NOVO: O CONTADOR NO ÍCONE DO MAPA! 👇
                const hubSocial = document.getElementById('hub-social');
                const btnMapa = document.getElementById('btn-chat-mapa');
                
                // Se a janela social estiver FECHADA, mostra a notificação no ícone!
                if (hubSocial && hubSocial.style.display === 'none' && btnMapa) {
                    window.totalNotificacoesMapa = (window.totalNotificacoesMapa || 0) + 1;
                    
                    let badgeMapa = document.getElementById('badge-chat-mapa');
                    if (!badgeMapa) {
                        badgeMapa = document.createElement('div');
                        badgeMapa.id = 'badge-chat-mapa';
                        badgeMapa.style.cssText = "position: absolute; top: -5px; right: -5px; background: #ef4444; color: white; border-radius: 50%; width: 22px; height: 22px; font-size: 11px; font-family: Arial; font-weight: bold; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 5px rgba(0,0,0,0.8); border: 2px solid #0f172a; z-index: 10;";
                        btnMapa.appendChild(badgeMapa);
                    }
                    
                    // Mostra o número. Se passar de 9, mostra "9+" para não desalinhar!
                    badgeMapa.innerText = window.totalNotificacoesMapa > 9 ? "9+" : window.totalNotificacoesMapa;
                    
                    // O Botão dá um "pulo" para chamar a atenção do jogador!
                    btnMapa.style.transform = 'scale(1.2)';
                    setTimeout(() => btnMapa.style.transform = 'scale(1)', 200);
                }
            }

            chatBox.scrollTop = chatBox.scrollHeight; 
        });

        this.socket.on('receberConviteAmizade', (dados) => { 
            if (typeof window.exibirConviteAmizadeCustom === 'function') {
                window.exibirConviteAmizadeCustom(dados);
            } else {
                // Fallback de segurança se der algum problema de carregamento
                if (confirm(`🤝 O jogador [${dados.remetente_nome}] enviou um pedido de amizade!\n\nAceitar?`)) { 
                    this.socket.emit('aceitarAmizade', { amigo_id: dados.remetente_id, amigo_nome: dados.remetente_nome }); 
                }
            }
        });
        this.socket.on('receberConviteGrupo', (dados) => { if (typeof window.exibirConviteGrupoCustom === 'function') window.exibirConviteGrupoCustom(dados, this.socket); });
        this.socket.on('atualizarListaGrupo', (grupo) => { if (typeof window.desenharMiniHudGrupo === 'function') window.desenharMiniHudGrupo(grupo); });
        
        this.socket.on('receberListaAmigos', (amigos) => {
            const conteudo = document.getElementById('chat-box');
            // Só desenha se a aba ativa for amigos e não estivermos numa conversa
            if (conteudo.dataset.abaAtiva !== 'amigos' || document.getElementById('input-chat').dataset.alvoPrivado) return;

            // Esconde o histórico do chat
            Array.from(conteudo.children).forEach(child => child.style.display = 'none');

            // Remove o texto de "Carregando..."
            let oldList = document.getElementById('container-lista-amigos');
            if (oldList) oldList.remove();

            // 🎯 CONTAINER DA LISTA
            let htmlLista = `<div id="container-lista-amigos" style="display: flex; flex-direction: column; gap: 8px; padding: 5px; width: 100%; box-sizing: border-box;">`;

            if (amigos.length === 0) {
                htmlLista += `<p style="color: #94a3b8; font-size: 0.9em; text-align: center; margin-top: 20px;">A tua lista está vazia.<br>Clica noutros jogadores no mapa para adicionar!</p>`;
            } else {
                amigos.forEach(amigo => {
                    let avatarFinal = amigo.avatar || 'https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/avatares/avatar_padrao_m.png';
                    let isOnline = amigo.online !== undefined ? amigo.online : true; 
                    let trofeusLevel = amigo.level || amigo.trofeus || 1;

                    // 🎯 Verifica se esse amigo tem mensagens não lidas
                    window.notificacoesPrivadas = window.notificacoesPrivadas || {};
                    let qtdeNaoLidas = window.notificacoesPrivadas[amigo.nome] || 0;
                    
                    // Se tiver mensagem, cria a bolinha vermelha!
                    let badgeNaoLidas = qtdeNaoLidas > 0 
                        ? `<div style="position: absolute; top: -8px; right: -5px; background: #ef4444; color: white; border-radius: 10px; padding: 2px 6px; font-size: 0.7em; font-weight: bold; box-shadow: 0 0 5px rgba(0,0,0,0.8); z-index: 10; border: 1px solid #7f1d1d;">${qtdeNaoLidas}</div>` 
                        : '';

                    htmlLista += `
                        <div style="background: linear-gradient(180deg, #e2e8f0, #94a3b8); border: 1px solid #475569; border-bottom: 3px solid #475569; border-radius: 8px; padding: 6px 10px; display: flex; align-items: center; gap: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.4);">
                            
                            <div style="width: 42px; height: 42px; border-radius: 6px; border: 2px solid #334155; overflow: hidden; background: #0f172a; flex-shrink: 0; box-shadow: inset 0 0 5px rgba(0,0,0,0.8);">
                                <img src="${avatarFinal}" onerror="this.src='https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/avatares/avatar_padrao_m.png'" style="width: 100%; height: 100%; object-fit: cover;">
                            </div>

                            <div style="flex-grow: 1; display: flex; flex-direction: column; justify-content: center;">
                                <span style="color: #0f172a; font-weight: 900; font-size: 1em; text-shadow: 0 1px 0 rgba(255,255,255,0.5); margin-bottom: 2px; font-family: Arial, sans-serif;">${amigo.nome}</span>
                                <div style="display: flex; align-items: center; gap: 4px;">
                                    <span style="font-size: 0.8em; filter: drop-shadow(0 1px 1px rgba(0,0,0,0.3));">🏆</span>
                                    <span style="color: #334155; font-weight: 900; font-size: 0.75em;">${trofeusLevel}</span>
                                </div>
                            </div>

                            <div style="display: flex; align-items: center; gap: 12px;">
                                <div style="display: flex; align-items: center; gap: 4px;">
                                    <div style="width: 8px; height: 8px; border-radius: 50%; background: ${isOnline ? '#2ecc71' : '#94a3b8'}; box-shadow: inset 0 1px 2px rgba(0,0,0,0.5), 0 0 5px ${isOnline ? '#2ecc71' : 'transparent'};"></div>
                                    <span style="color: ${isOnline ? '#166534' : '#64748b'}; font-weight: 900; font-size: 0.65em; text-transform: lowercase; font-family: Arial, sans-serif;">${isOnline ? 'on-line' : 'off-line'}</span>
                                </div>

                                <!-- 💬 Botão Verde 3D (Agora com position relative para segurar a bolinha) -->
                                <div style="position: relative;">
                                    ${badgeNaoLidas}
                                    <button onclick="window.abrirChatPrivado('${amigo.nome}')" style="background: linear-gradient(180deg, #a3e635, #65a30d); border: 1px solid #3f6212; border-bottom: 3px solid #3f6212; border-radius: 6px; width: 38px; height: 32px; display: flex; justify-content: center; align-items: center; cursor: pointer; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">
                                        <span style="font-size: 1.1em; color: white; text-shadow: 0 1px 2px rgba(0,0,0,0.8);">💬</span>
                                    </button>
                                </div>
                            </div>
                        </div>
                    `;
                });
            }
            htmlLista += `</div>`;
            conteudo.insertAdjacentHTML('beforeend', htmlLista);
        });
        
        this.socket.on('removerHudGrupo', () => { let hud = document.getElementById('eldora-party-hud'); if (hud) hud.remove(); });

        // 🟢 FUNÇÃO DE ENVIO DE MENSAGENS BLINDADA 🟢
        window.enviarMensagemChat = () => {
            const input = document.getElementById('input-chat');
            if (!input) return;
            let texto = input.value.trim(); 
            
            if (texto !== "") {
                const abaAtiva = input.dataset.abaAtual || 'chat';
                const alvoPrivado = input.dataset.alvoPrivado; 
                
                if (!texto.startsWith('/')) {
                    if (abaAtiva === 'grupo') {
                        texto = `/g ${texto}`;
                    } else if (abaAtiva === 'guilda') {
                        texto = `/c ${texto}`; 
                    } else if (abaAtiva === 'amigos') {
                        // 🛑 ESCUDO ANTI-VAZAMENTO: Bloqueia se tentar falar na aba de amigos sem alvo
                        if (!alvoPrivado) {
                            const chatBox = document.getElementById('chat-box');
                            chatBox.innerHTML += `<div style="color: #ef4444; font-size: 0.85em; text-align: center; margin-top: 5px; background: rgba(255,0,0,0.1); padding: 5px; border-radius: 4px;">⚠️ Clique num jogador para sussurrar!</div>`;
                            chatBox.scrollTop = chatBox.scrollHeight;
                            return; // Para tudo e NÃO envia pro servidor!
                        }
                        texto = `/w "${alvoPrivado}" ${texto}`;
                    }
                }

                if (window.eldoraSocket) {
                    window.eldoraSocket.emit('enviarMensagemChat', { texto: texto });
                }
                
                input.value = ""; 
            }
        };
        // 👇 1. OUVINTE: Quando alguém te desafia 👇
        window.eldoraSocket.on('receberConviteDuelo', function(dados) {
            
            // Usamos o novo Modal Bonito!
            if (typeof window.exibirConviteDueloCustom === 'function') {
                window.exibirConviteDueloCustom(dados);
            } else {
                // Se der algum erro e a função não carregar, usa o feio como segurança para não quebrar o jogo
                const aceitou = confirm(`⚔️ DESAFIO! O herói ${dados.remetente_nome} te desafiou para um Duelo 1v1!\n\nVocê aceita?`);
                if (aceitou) {
                    window.eldoraSocket.emit('aceitarDuelo', { desafiante_id: dados.remetente_id });
                } else {
                    window.eldoraSocket.emit('recusarDuelo', { desafiante_id: dados.remetente_id });
                }
            }
        });

        // 👇 2. OUVINTE: Quando a Arena for montada no Servidor 👇
        window.eldoraSocket.on('iniciarArenaPvP', async function(estado_arena) {
            console.log("⚔️ ARENA INSTANCIADA!", estado_arena);
    
            // 👇 A MÁGICA QUE FALTAVA: Baixar magias e itens para a memória global!
            const charId = localStorage.getItem("jogadorEldoraID");
            try {
                const resPerfil = await fetch(`/api/personagem/${charId}?t=${new Date().getTime()}`);
                window.perfilDadosGlobais = await resPerfil.json(); 
            } catch(e) {
                console.warn("Aviso: Não foi possível carregar o grimório para o PvP.", e);
            }

            if (typeof window.iniciarInterfacePvP === 'function') {
                window.iniciarInterfacePvP(estado_arena);
            }
        });

        // 🔥 3. OUVINTE NOVO (A CORREÇÃO): Ouve o cálculo de dano e descongela a tela! 🔥
        window.eldoraSocket.on('animarTurnoPvP', function(pacoteTurno) {
            console.log("⚔️ TURNO RECEBIDO DO BACKEND!", pacoteTurno);
            if (typeof window.processarAnimacaoTurnoPvP === 'function') {
                window.processarAnimacaoTurnoPvP(pacoteTurno);
            }
        });
        
        // 🔘 ATIVANDO OS BOTÕES (ENTER E BOTÃO AZUL) 🔘
        const inputChat = document.getElementById('input-chat');
        if (inputChat) {
            // Clona e substitui para remover event listeners velhos
            inputChat.replaceWith(inputChat.cloneNode(true)); 
            const novoInput = document.getElementById('input-chat');
            
            novoInput.addEventListener('keypress', (e) => { 
                if (e.key === 'Enter') window.enviarMensagemChat(); 
            });

            const btnEnviar = novoInput.nextElementSibling;
            if (btnEnviar && btnEnviar.tagName === 'BUTTON') {
                btnEnviar.onclick = window.enviarMensagemChat;
            }
        }
    }

    adicionarOutroJogador(id, info) {

        // Usa o nosso Faxineiro para limpar o velho sem congelar o jogo!
        this.removerOutroJogador(id);

        let skinDesejada = info.skin || 'aventureiro_base';
        let skinAtual = skinDesejada;

        const linkNuvem =
            "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/classes/";

        // ==========================================
        // 👥 CARREGA SKIN DO OUTRO JOGADOR
        // ==========================================
        if (!this.scene.textures.exists(skinDesejada)) {

            this.scene.load.spritesheet(
                skinDesejada,
                `${linkNuvem}${skinDesejada}.png`,
                {
                    frameWidth: 128,
                    frameHeight: 128
                }
            );

            this.scene.load.once(
                `filecomplete-spritesheet-${skinDesejada}`,
                () => {

                    this.scene.outrosJogadores.getChildren().forEach(o => {

                        if (o.playerId === id) {

                            o.setTexture(skinDesejada);
                            o.setFrame(1);

                            // Mesmo tamanho visual do jogador principal
                            o.setDisplaySize(48, 48);

                            // Cria animações dos 12 frames
                            try {
                                this.scene.gerarAnimacoes(skinDesejada);
                            } catch (e) {
                                console.warn(
                                    "Erro ao gerar animações do jogador remoto:",
                                    e
                                );
                            }
                        }
                    });
                }
            );

            this.scene.load.start();

            // Usa aventureiro temporariamente enquanto baixa a skin
            skinAtual = 'aventureiro_base';
        }

        // ==========================================
        // 👤 CRIA O OUTRO JOGADOR
        // ==========================================
        let outro = this.scene.add.sprite(
            info.x,
            info.y,
            skinAtual
        ).setDepth(15);

        outro.playerId = id;

        // 🔥 MESMO TAMANHO DO JOGADOR PRINCIPAL
        outro.setDisplaySize(48, 48);

        // Nome
        outro.nomeTexto = this.scene.add.text(
            outro.x,
            outro.y - 25,
            info.nome || "Herói",
            {
                fontSize: '10px',
                color: '#fff',
                fontFamily: 'Cinzel, Arial',
                stroke: '#000',
                strokeThickness: 2
            }
        )
        .setOrigin(0.5, 1)
        .setDepth(30);

        outro.setInteractive();

        outro.on('pointerdown', (pointer) => {

            const menu = document.getElementById('menu-inspecao');
            const titulo = document.getElementById('inspecao-nome');

            menu.dataset.alvoId = info.char_id;
            menu.dataset.alvoNome = info.nome || "Herói";

            if (titulo) {
                titulo.innerText = info.nome || "Herói";
            }

            menu.style.left = '';
            menu.style.top = '';
            menu.style.display = 'flex';
        });

        this.scene.outrosJogadores.add(outro);
    }
}
// ==========================================
// SISTEMA SOCIAL - CHAT PRIVADO INVISÍVEL
// ==========================================
window.setAlvoSussurro = function(nome) {
    const inputArea = document.querySelector('.chat-input-area'); 
    const input = document.getElementById('input-chat');
    
    // Remove botão velho se existir
    let oldBadge = document.getElementById('badge-sussurro'); 
    if(oldBadge) oldBadge.remove();
    
    if (nome) {
        input.dataset.alvoPrivado = nome; 
        input.placeholder = `Escreva para ${nome}...`;
        
        const badge = document.createElement('div'); 
        badge.id = 'badge-sussurro';
        
        // 🎯 O NOVO VISUAL: Fundo com degradê leve, bordas arredondadas e sombra
        badge.style.cssText = "background: linear-gradient(90deg, #1e293b, #0f172a); border: 1px solid #334155; border-radius: 6px; padding: 6px 10px; display: flex; justify-content: space-between; align-items: center; width: 100%; box-sizing: border-box; margin-bottom: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.4);";
        
        // 🔘 BOTÃO MODERNO e NOME ALINHADO
        badge.innerHTML = `
            <button onclick="window.limparSussurro()" style="background: #334155; color: #f8fafc; border: 1px solid #475569; border-radius: 4px; padding: 4px 10px; font-weight: bold; font-size: 0.75em; cursor: pointer; display: flex; align-items: center; gap: 4px; text-transform: uppercase; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">
                ◀ Voltar
            </button>
            <div style="color: #cbd5e1; font-size: 0.85em; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; display: flex; align-items: center; gap: 5px;">
                <span style="opacity: 0.8;">Chat:</span>
                <strong style="color: #d946ef; font-size: 1.1em; letter-spacing: 0.5px; text-shadow: 0 1px 2px rgba(0,0,0,0.8);">${nome}</strong>
            </div>
        `;
        
        inputArea.parentNode.insertBefore(badge, inputArea);
    } else { 
        delete input.dataset.alvoPrivado; 
        input.placeholder = "Fale com o reino..."; 
    }
};

window.limparSussurro = function() { window.setAlvoSussurro(null); };

// 🌟 O FILTRO MÁGICO DE ABAS (AGORA ISOLANDO 100% CADA CANAL) 🌟
window.mudarAbaSocial = function(aba, elemento) {
    document.querySelectorAll('.aba-soc').forEach(btn => btn.classList.remove('active'));
    if (elemento) {
        elemento.classList.add('active');
        // 🧽 LIMPEZA: Remove a bolinha de notificação quando clica na aba!
        let badge = elemento.querySelector('.notificacao-badge');
        if (badge) badge.remove();
    }
    const conteudo = document.getElementById('chat-box');
    const inputArea = document.querySelector('.chat-input-area');
    const input = document.getElementById('input-chat');
    if (!conteudo || !inputArea || !input) return;

    conteudo.dataset.abaAtiva = aba;
    input.dataset.abaAtual = aba;

    if (aba !== 'amigos') window.limparSussurroSemRecarregar();

    // Remove a lista de amigos/carregamento se ela existir
    let oldList = document.getElementById('container-lista-amigos');
    if (oldList) oldList.remove();

    // 🎯 A MÁGICA SEGURA: Esconde as mensagens em vez de deletar!
    if (aba === 'amigos' && !input.dataset.alvoPrivado) {
        inputArea.style.display = 'none'; 
        
        // Esconde o histórico sem apagar do HTML
        Array.from(conteudo.children).forEach(child => child.style.display = 'none');
        
        // Cria a área da lista com o texto de carregamento
        conteudo.insertAdjacentHTML('beforeend', `<div id="container-lista-amigos"><p style="color: #64748b; text-align: center; font-size: 0.8em; margin-top:20px;">A procurar aliados...</p></div>`);
        
        if (window.eldoraSocket) window.eldoraSocket.emit('pedirListaAmigos');
        return; 
    }

    // Limpa mensagens provisórias ("Bem vindo ao chat", etc)
    Array.from(conteudo.querySelectorAll('.msg-provisoria')).forEach(p => p.remove());

    inputArea.style.display = 'flex'; 
    let temMensagem = false;

    Array.from(conteudo.children).forEach(msgDiv => {
        if (msgDiv.tagName !== 'DIV' || msgDiv.id === 'container-lista-amigos') return;
        
        const canalDaMsg = msgDiv.dataset.canal || 'global';
        if (aba === 'chat' && canalDaMsg === 'global') {
            msgDiv.style.display = 'block'; temMensagem = true;
        } else if (aba === 'grupo' && canalDaMsg === 'grupo') {
            msgDiv.style.display = 'block'; temMensagem = true;
        } else if (aba === 'guilda' && canalDaMsg === 'guilda') {
            msgDiv.style.display = 'block'; temMensagem = true;
        } else {
            msgDiv.style.display = 'none';
        }
    });

    if (aba === 'chat') {
        input.placeholder = "Falar com o reino...";
        if(!temMensagem) conteudo.insertAdjacentHTML('beforeend', `<p class="msg-provisoria" style="color: #64748b; text-align: center; font-size: 0.8em; margin-top:20px;">Bem-vindo ao chat global!</p>`);
    } else if (aba === 'grupo') {
        input.placeholder = "Falar com o grupo...";
        if(!temMensagem) conteudo.insertAdjacentHTML('beforeend', `<p class="msg-provisoria" style="color: #64748b; text-align: center; font-size: 0.8em; margin-top:20px;">O chat do grupo está vazio.</p>`);
    } else if (aba === 'guilda') {
        input.placeholder = "Falar com o Clã...";
        if(!temMensagem) conteudo.insertAdjacentHTML('beforeend', `<p class="msg-provisoria" style="color: #64748b; text-align: center; font-size: 0.8em; margin-top:20px;">O chat do Clã está vazio.</p>`);
    }
    
    conteudo.scrollTop = conteudo.scrollHeight;
};

window.abrirChatPrivado = function(nome) {
    // 🧽 Apaga a notificação visual
    window.notificacoesPrivadas = window.notificacoesPrivadas || {};
    delete window.notificacoesPrivadas[nome];
    
    // 📡 AVISA O SERVIDOR PYTHON QUE LÊMOS AS MENSAGENS DESSE AMIGO!
    if (window.eldoraSocket) window.eldoraSocket.emit('marcarSussurrosLidos', { amigo: nome });

    const conteudo = document.getElementById('chat-box');
    const inputArea = document.querySelector('.chat-input-area');

    window.setAlvoSussurro(nome);
    inputArea.style.display = 'flex'; 

    // Remove APENAS a lista de amigos do caminho
    let lista = document.getElementById('container-lista-amigos');
    if (lista) lista.remove();
    
    Array.from(conteudo.querySelectorAll('.msg-provisoria')).forEach(p => p.remove());

    let temMensagem = false;
    Array.from(conteudo.children).forEach(child => {
        if (child.tagName === 'DIV' && child.dataset.canal === 'amigos') {
            if (child.dataset.parceiro === nome) {
                child.style.display = 'block';
                temMensagem = true;
            } else {
                child.style.display = 'none';
            }
        } else {
            child.style.display = 'none'; // Esconde mensagens globais
        }
    });

    if (!temMensagem) {
        const p = document.createElement('p');
        p.className = 'msg-provisoria';
        p.style.cssText = "color: #64748b; text-align: center; font-size: 0.8em; margin-top:20px;";
        p.innerText = `Comece uma conversa com ${nome}!`;
        conteudo.appendChild(p);
    }
    conteudo.scrollTop = conteudo.scrollHeight;
};

// Altera a função de limpar o alvo para voltar à lista
window.limparSussurro = function() {
    window.limparSussurroSemRecarregar();
    const inputArea = document.querySelector('.chat-input-area');
    inputArea.style.display = 'none';
    
    if (window.eldoraSocket) window.eldoraSocket.emit('pedirListaAmigos');
};

window.limparSussurroSemRecarregar = function() {
    const input = document.getElementById('input-chat');
    delete input.dataset.alvoPrivado;
    let oldBadge = document.getElementById('badge-sussurro'); 
    if(oldBadge) oldBadge.remove();
};

window.acaoInspecaoAmigo = function(nomeAmigo) {
    // 🎯 CAÇADOR DE ABAS: Procura especificamente a aba de AMIGOS
    const btnAmigos = Array.from(document.querySelectorAll('.aba-soc')).find(b => b.innerText.toUpperCase().includes('AMIGOS'));
    if (btnAmigos) btnAmigos.click(); 
    else mudarAbaSocial('amigos', null);
    
    window.setAlvoSussurro(nomeAmigo);
    document.getElementById('input-chat').focus();
};

window.acaoInspecao = function(acao) {
    try {
        const menu = document.getElementById('menu-inspecao');
        const alvoNome = menu.dataset.alvoNome;
        const alvoId = menu.dataset.alvoId;
        
        if (!alvoId) return;

        if (acao === 'sussurrar') {
            document.getElementById('hub-social').style.display = 'flex';
            const btnAmigos = Array.from(document.querySelectorAll('.aba-soc')).find(b => b.innerText.toUpperCase().includes('AMIGOS'));
            if (btnAmigos) btnAmigos.click(); 
            else mudarAbaSocial('amigos', null);
            
            if (typeof window.setAlvoSussurro === 'function') window.setAlvoSussurro(alvoNome);
            document.getElementById('input-chat').focus();
        } 
        else if (acao === 'amigo') {
            if (window.eldoraSocket) window.eldoraSocket.emit('enviarConviteAmizade', { alvo_id: alvoId });
            // Aproveitando para colocar a notificação bonita aqui também!
            window.mostrarNotificacaoRPG(`Convite de amizade enviado para ${alvoNome}!`, '🤝');
        } 
        else if (acao === 'grupo') {
            if (!alvoId) return;
            if (window.eldoraSocket) window.eldoraSocket.emit('enviarConviteGrupo', { alvo_id: alvoId });
            // E aqui também!
            window.mostrarNotificacaoRPG(`Convite de grupo enviado para ${alvoNome}!`, '🛡️');
        }
        else if (acao === 'perfil') {
            window.abrirPerfilJogador(alvoId);
        }
        else if (acao === 'desafiar') {
            if (window.eldoraSocket) {
                window.eldoraSocket.emit('enviarConviteDuelo', { alvo_id: alvoId });
                // 👇 AQUI ESTÁ A MÁGICA: Tchau alert(), olá Toast!
                window.mostrarNotificacaoRPG(`Convite de duelo enviado para ${alvoNome}!`, '⚔️');
            }
        }
        menu.style.display = 'none'; 
        
    } catch (erro) {
        console.warn("Erro na inspeção:", erro);
    }
};

window.abrirPerfilJogador = async function(charId) {
    let modal = document.getElementById('modal-ver-perfil');
    let conteudo = document.getElementById('conteudo-ver-perfil');
    
    if(!modal || !conteudo) { alert("Erro no modal de perfil!"); return; }

    modal.style.display = 'flex';
    Array.from(modal.querySelectorAll('*')).forEach(el => {
        if(el.children.length === 0 && el.textContent.trim().toUpperCase() === 'X') el.style.display = 'none';
    });
    
    modal.style.background = "rgba(2, 6, 23, 0.85)"; modal.style.backdropFilter = "blur(8px)";
    modal.style.position = "fixed"; modal.style.top = "0"; modal.style.left = "0";
    modal.style.width = "100%"; modal.style.height = "100%";
    modal.style.justifyContent = "center"; modal.style.alignItems = "center";
    modal.style.zIndex = "10000"; modal.style.animation = "fadeIn 0.3s ease-out"; 

    const container = modal.querySelector('.perfil-container-moderno');
    if (container) {
        container.style.display = 'block'; container.style.background = "linear-gradient(145deg, #0f172a, #1e293b)";
        container.style.border = "2px solid #ca8a04"; container.style.borderRadius = "16px";
        container.style.padding = "12px"; container.style.boxShadow = "0 20px 50px rgba(0, 0, 0, 0.9)";
        container.style.animation = "slideUp 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)"; 
        container.style.maxWidth = "310px"; container.style.width = "92%"; container.style.position = "relative";
    }

    conteudo.innerHTML = `
        <div style="text-align:center; padding: 30px 20px;">
            <p style="color: #facc15; font-family: 'Cinzel', serif; font-weight: bold; font-size: 1.1em; letter-spacing: 1px; margin-bottom: 15px; text-shadow: 0 2px 4px rgba(0,0,0,0.8);">A abrir os pergaminhos...</p>
            <div style="width: 100%; height: 8px; background: #0f172a; border-radius: 4px; border: 1px solid #ca8a04; overflow: hidden; position: relative; box-shadow: inset 0 2px 5px rgba(0,0,0,0.8);">
                <div style="position: absolute; top: 0; left: -40%; height: 100%; width: 40%; background: linear-gradient(90deg, transparent, #facc15, #fff, #facc15, transparent); animation: loadingMagico 3s infinite linear; box-shadow: 0 0 10px #facc15;"></div>
            </div>
            <style>@keyframes loadingMagico { 0% { left: -40%; } 100% { left: 100%; } }</style>
        </div>`;
        
    try {
        const response = await fetch(`/perfil/${charId}?t=${new Date().getTime()}`, { cache: 'no-store' });
        if (!response.ok) throw new Error("Herói não encontrado nas lendas.");
        const p = await response.json();
        if (p.erro) throw new Error(p.erro);
        
        let bannerCaminho = p.banner_customizado;
        if (typeof bannerCaminho === 'object' && bannerCaminho !== null) bannerCaminho = bannerCaminho.path;
        let bannerImgCss = 'linear-gradient(135deg, #0f172a, #1e293b)';
        
        if (bannerCaminho && bannerCaminho !== 'padrao' && bannerCaminho !== '') {
            if (window.CATALOGO_SISTEMA && window.CATALOGO_SISTEMA.banners[bannerCaminho]) bannerImgCss = `url('${window.CATALOGO_SISTEMA.banners[bannerCaminho].path}')`;
            else if (bannerCaminho.startsWith('http')) bannerImgCss = `url('${bannerCaminho}')`;
        }

        // 1. O Python geralmente envia 'genero' em vez de 'gender'
        const generoReal = p.genero || p.gender || "masculino";
        const generoCurto = (generoReal.toLowerCase() === 'feminino') ? 'f' : 'm';

        // 2. Limpar a classe (muda de "aprendiz" para "aventureiro", remove acentos e troca espaços por underline)
        let classeKey = (p.classe || "aventureiro").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/\s+/g, '_');
        
        // 3. Se o jogador tiver uma skin premium equipada, ela toma o lugar da classe base
        if (p.skin && p.skin !== 'padrao' && p.skin !== '') {
            classeKey = p.skin.toLowerCase();
        }

        const linkBaseNuvem = window.CATALOGO_SISTEMA ? "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/" : "/static/assets/";
        
        // 4. Monta o link da imagem (Skins premium geralmente não usam _m ou _f no final da imagem full)
        let arquivoImg = classeKey.includes('skin_') ? `${classeKey}_full.png` : `${classeKey}_${generoCurto}_full.png`;
        
        const fullBodyImgUrl = `${linkBaseNuvem}corpo_completo/${arquivoImg}`;
        const fallbackFullBody = `${linkBaseNuvem}corpo_completo/aventureiro_m_full.png`;
        conteudo.innerHTML = `
            <div style="color: #fff; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; display: flex; flex-direction: column; align-items: center;">
                <div style="background-image: ${bannerImgCss}; background-size: cover; background-position: center; position: relative; width: 100%; height: 130px; border-radius: 10px; overflow: hidden; border: 1px solid #ca8a04; margin-bottom: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">
                    <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(0deg, rgba(15,23,42,0.9) 0%, rgba(15,23,42,0.1) 70%); z-index: 1;"></div>
                    <img src="${fullBodyImgUrl}" onerror="this.src='${fallbackFullBody}'; this.onerror=null;" style="position: absolute; bottom: 0px; left: 50%; transform: translateX(-50%); height: 90%; max-width: 100%; object-fit: contain; z-index: 2; filter: drop-shadow(0 4px 6px rgba(0,0,0,0.9)); pointer-events: none;">
                </div>
                <h2 style="color: #facc15; margin: 0; font-family: 'Cinzel', serif; font-size: 1.4em; text-shadow: 0 2px 4px rgba(0,0,0,0.8); text-align: center; letter-spacing: 1px;">${p.nome}</h2>
                <p style="color: #94a3b8; margin: 2px 0 10px 0; font-weight: 800; text-transform: uppercase; font-size: 0.75em; letter-spacing: 1px; text-align: center;">Lvl ${p.level} • ${p.classe}</p>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; width: 100%; margin-bottom: 15px;">
                    <div style="background: rgba(0,0,0,0.6); padding: 6px; border-radius: 6px; border: 1px solid #334155; text-align: center;"><span style="display: block; color: #ef4444; font-weight: 900; font-size: 0.55em; text-transform: uppercase;">Max HP</span><span style="color: #fca5a5; font-weight: bold; font-size: 0.95em;">❤️ ${p.hp_max || p.max_hp || 50}</span></div>
                    <div style="background: rgba(0,0,0,0.6); padding: 6px; border-radius: 6px; border: 1px solid #334155; text-align: center;"><span style="display: block; color: #3b82f6; font-weight: 900; font-size: 0.55em; text-transform: uppercase;">Max MP</span><span style="color: #93c5fd; font-weight: bold; font-size: 0.95em;">🔵 ${p.mp_max || p.max_mp || 20}</span></div>
                    <div style="background: rgba(0,0,0,0.6); padding: 6px; border-radius: 6px; border: 1px solid #334155; text-align: center;"><span style="display: block; color: #f59e0b; font-weight: 900; font-size: 0.55em; text-transform: uppercase;">Ataque</span><span style="color: #fcd34d; font-weight: bold; font-size: 0.95em;">⚔️ ${p.attack || 5}</span></div>
                    <div style="background: rgba(0,0,0,0.6); padding: 6px; border-radius: 6px; border: 1px solid #334155; text-align: center;"><span style="display: block; color: #10b981; font-weight: 900; font-size: 0.55em; text-transform: uppercase;">Defesa</span><span style="color: #6ee7b7; font-weight: bold; font-size: 0.95em;">🛡️ ${p.defense || 3}</span></div>
                    <div style="background: rgba(0,0,0,0.6); padding: 6px; border-radius: 6px; border: 1px solid #334155; text-align: center;"><span style="display: block; color: #06b6d4; font-weight: 900; font-size: 0.55em; text-transform: uppercase;">Iniciativa</span><span style="color: #67e8f9; font-weight: bold; font-size: 0.95em;">⚡ ${p.initiative || 5}</span></div>
                    <div style="background: rgba(0,0,0,0.6); padding: 6px; border-radius: 6px; border: 1px solid #334155; text-align: center;"><span style="display: block; color: #a855f7; font-weight: 900; font-size: 0.55em; text-transform: uppercase;">Sorte</span><span style="color: #d8b4fe; font-weight: bold; font-size: 0.95em;">🍀 ${p.luck || 5}</span></div>
                </div>
                <div style="display: flex; gap: 6px; width: 100%;">
                    <button onclick="document.getElementById('modal-ver-perfil').style.display='none'; if(typeof window.acaoInspecaoAmigo === 'function') window.acaoInspecaoAmigo('${p.nome}');" style="flex: 1; padding: 10px; background: linear-gradient(180deg, #3b82f6, #2563eb); color: white; border: 1px solid #1d4ed8; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 0.85em; transition: all 0.2s; box-shadow: 0 2px 4px rgba(0,0,0,0.5);">💬 Falar</button>
                    <button onclick="if(window.eldoraSocket) window.eldoraSocket.emit('enviarConviteAmizade', { alvo_id: '${charId}' });" style="flex: 1; padding: 10px; background: linear-gradient(180deg, #10b981, #059669); color: white; border: 1px solid #047857; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 0.85em; transition: all 0.2s; box-shadow: 0 2px 4px rgba(0,0,0,0.5);">🤝 Adic.</button>
                    <button onclick="document.getElementById('modal-ver-perfil').style.display='none';" style="padding: 10px 15px; background: #334155; color: white; border: 1px solid #475569; border-radius: 6px; cursor: pointer; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.5);">✖</button>
                </div>
            </div>
            <style>@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } } @keyframes slideUp { from { opacity: 0; transform: translateY(40px) scale(0.9); } to { opacity: 1; transform: translateY(0) scale(1); } }</style>
        `;
    } catch (error) {
        conteudo.innerHTML = `<p style="color: #ef4444; font-weight: bold; text-align: center; padding: 20px;">${error.message}</p>`;
    }
};

// ==========================================
/// ==========================================
// 🎭 SISTEMA DE EXPRESSÕES DO MAPA INDEPENDENTE
// ==========================================

// Dicionário visual para os botões do menu
const iconesEmojiMenu = {
    "raiva": "😡",
    "sorriso": "😀",
    "choro": "😭",
    "festa": "🎉"
};

// Seus 6 slots (Por enquanto chumbado aqui para testar. Depois virá do Python!)
window.meusEmojisEquipados = ["raiva", "sorriso", "choro", "festa", null, null]; 

// Função que desenha os botões na tela
window.renderizarMenuEmojis = function() {
    const grid = document.getElementById('grid-emojis-dinamico');
    if (!grid) return;
    
    grid.innerHTML = ''; // Limpa a lousa

    // Roda 6 vezes para criar os 6 slots
    for (let i = 0; i < 6; i++) {
        let nomeDoEmoji = window.meusEmojisEquipados[i];

        if (nomeDoEmoji) {
            let icone = iconesEmojiMenu[nomeDoEmoji] || "✨";
            grid.innerHTML += `
                <button class="emoji-btn ativo" onclick="window.enviarEmojiMapa('${nomeDoEmoji}')" title="${nomeDoEmoji.toUpperCase()}">
                    ${icone}
                </button>
            `;
        } else {
            grid.innerHTML += `
                <button class="emoji-btn bloqueado" title="Slot Vazio">🔒</button>
            `;
        }
    }
};

window.toggleMenuExpressoes = function() {
    const menu = document.getElementById('menu-expressoes');
    const inputBalao = document.getElementById('input-balao-mapa');

    if (!menu) return;

    if (menu.style.display === 'none' || menu.style.display === '') {
        // Esconde outros menus se estiverem abertos
        const menuInspecao = document.getElementById('menu-inspecao');
        if (menuInspecao) menuInspecao.style.display = 'none';
        
        // Desenha os emojis antes de mostrar a janela.
        window.renderizarMenuEmojis(); 
        
        menu.style.display = 'block';

        if (inputBalao) {
            setTimeout(() => inputBalao.focus(), 50);
        }
    } else {
        menu.style.display = 'none';

        // Importantíssimo:
        // se o input continuar focado escondido, o mapa acha que ainda estamos digitando
        // e bloqueia WASD mesmo fora do menu.
        if (inputBalao && typeof inputBalao.blur === "function") {
            inputBalao.blur();
        }

        if (document.activeElement && document.activeElement.id === 'input-balao-mapa') {
            document.activeElement.blur();
        }
    }
};

window.enviarBalaoMapa = function() {
    const input = document.getElementById('input-balao-mapa');
    if (!input) return;

    const texto = input.value.trim();
    
    if (texto && window.eldoraSocket) {
        // Envia o grito pro Python
        window.eldoraSocket.emit('enviarAcaoMapa', { tipo: 'texto', valor: texto });
        input.value = '';

        // Tira o foco antes de fechar para devolver WASD ao mapa.
        if (typeof input.blur === "function") {
            input.blur();
        }

        window.toggleMenuExpressoes();
    }
};

window.enviarEmojiMapa = function(emojiName) {
    if (window.eldoraSocket) {
        // Envia a animação pro Python
        window.eldoraSocket.emit('enviarAcaoMapa', { tipo: 'emoji', valor: 'emoji_' + emojiName });
        window.toggleMenuExpressoes(); // Fecha o menu
    }
};

// ==========================================
// 🔔 NOTIFICAÇÕES FLUTUANTES (TOAST)
// ==========================================
window.mostrarNotificacaoRPG = function(mensagem, icone = '⚔️') {
    let toast = document.getElementById('eldora-toast');
    
    // Se não existir, cria a div vazia
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'eldora-toast';
        document.body.appendChild(toast);
    }

    // Injeta o texto e o ícone
    toast.innerHTML = `<span class="toast-icon">${icone}</span> <span>${mensagem}</span>`;
    
    // Força o navegador a recalcular o layout (necessário para a animação CSS rodar)
    void toast.offsetWidth;
    
    // Adiciona a classe que faz a caixinha descer
    toast.classList.add('mostrar');

    // Remove a classe para a caixinha subir depois de 3.5 segundos
    if (toast.hideTimeout) clearTimeout(toast.hideTimeout);
    toast.hideTimeout = setTimeout(() => {
        toast.classList.remove('mostrar');
    }, 3500);
};