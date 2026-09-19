// /static/js/arena_pvp.js - MOTOR VISUAL DE DUELOS (PVP)

// ==========================================
// 1. VARIÁVEIS GLOBAIS E ESTADO
// ==========================================
window.dadosPvPAtual = {
    dueloId: null,
    meuHpMax: 0,
    meuHpAtual: 0,
    meuMpMax: 0,
    meuMpAtual: 0,
    oponenteHpMax: 0,
    oponenteHpAtual: 0,
    minhaVez: false
};

window.bloqueioDeTurnoPvP = false;

// ==========================================
// 2. INICIALIZAÇÃO DA ARENA
// ==========================================
window.iniciarInterfacePvP = function(estado_arena) {
    // 1. Esconde o Mapa e blinda a Arena PvP
    document.getElementById('aba-reino').style.display = 'none';
    const telaPvp = document.getElementById('tela-pvp-global');
    if(telaPvp) {
        telaPvp.style.display = 'flex';
        telaPvp.style.position = 'fixed';
        telaPvp.style.zIndex = '99999999'; // 👈 Z-Index infinito para ficar acima de tudo
        telaPvp.style.justifyContent = 'center'; // 👈 Centraliza a caixa na tela
        telaPvp.style.paddingBottom = '60px'; // 👈 Empurra a arena de combate mais para cima
    }

    // 👇 1.5. MÁQUINA DE ESCONDER HUDS FLUTUANTES 👇
    const hudsParaEsconder = ['hud-moderno', 'menu-lateral', 'hud-direito', 'menu-inspecao'];
    hudsParaEsconder.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });

    // Oculta os botões flutuantes usando a sua técnica de classes!
    document.querySelectorAll('.btn-passe-mapa, .btn-social-mapa').forEach(btn => btn.style.display = 'none');

    // 2. Preenche os dados de estado
    window.dadosPvPAtual = {
        dueloId: estado_arena.duelo_id,
        meuHpMax: estado_arena.meu_max_hp,
        meuHpAtual: estado_arena.meu_hp,
        oponenteHpMax: estado_arena.oponente_max_hp,
        oponenteHpAtual: estado_arena.oponente_hp,
        minhaVez: estado_arena.minha_vez,
        oponenteNome: estado_arena.oponente_nome // 👈 ADICIONADO: Salva o nome para usar nos logs de turno!
    };

    // 3. Atualiza a Interface Visual
    document.getElementById('nome-oponente').innerText = estado_arena.oponente_nome;
    
    // 👇 Renderiza os Levels!
    document.getElementById('lvl-oponente').innerText = "LV." + estado_arena.oponente_level;
    document.getElementById('lvl-jogador-pvp').innerText = "LV." + estado_arena.meu_level;

    // 👇 Pinta o fundo correto com o link RAW limpo do GitHub!
    const bgArena = "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/fundos/pvp_combate.png";
        
    document.getElementById('pvp-arena-box').style.backgroundImage = `url('${bgArena}')`;

    // Sprites
    const LINK_BASE = "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/classes_costa/";
    const cache = `?v=${new Date().getTime()}`;
    
    let minhaSkin = localStorage.getItem("skinEquipada") || "aventureiro_m";
    minhaSkin = minhaSkin.replace('_masculino', '_m').replace('_feminino', '_f');
    if (minhaSkin === 'player' || minhaSkin === 'padrao') minhaSkin = 'aventureiro_m';
    
    let oponenteSkin = estado_arena.oponente_skin || 'aventureiro_m';
    oponenteSkin = oponenteSkin.replace('_masculino', '_m').replace('_feminino', '_f');
    
    document.getElementById('sprite-jogador-pvp').src = `${LINK_BASE}${minhaSkin}.png${cache}`;
    document.getElementById('sprite-oponente-pvp').src = `${LINK_BASE}${oponenteSkin}.png${cache}`;
    
    document.getElementById('sprite-jogador-pvp').style.opacity = "1";
    document.getElementById('sprite-oponente-pvp').style.opacity = "1";

    // 👇 Atualiza a Vida e a Mana com os novos dados!
    window.dadosPvPAtual.meuMpMax = estado_arena.meu_max_mp;
    window.dadosPvPAtual.meuMpAtual = estado_arena.meu_mp;

    atualizarBarraPvP('bar-hp-jogador-pvp', window.dadosPvPAtual.meuHpAtual, window.dadosPvPAtual.meuHpMax);
    atualizarBarraPvP('bar-hp-oponente', window.dadosPvPAtual.oponenteHpAtual, window.dadosPvPAtual.oponenteHpMax);
    atualizarBarraPvP('bar-mp-jogador-pvp', window.dadosPvPAtual.meuMpAtual, window.dadosPvPAtual.meuMpMax);

    document.getElementById('pvp-loading').style.display = 'none';
    document.getElementById('pvp-arena').style.display = 'flex';
    document.getElementById('pvp-botoes-fim-batalha').style.display = 'none';
    
    // ==========================================
    // 👇 NOVO SISTEMA DE LOGS APLICADO AQUI 👇
    // ==========================================
    
    // Limpa a caixa de scroll se for um novo duelo
    const containerLog = document.getElementById('pvp-caixa-logs-scroll');
    if (containerLog) containerLog.innerHTML = '';
    
    // Dispara a mensagem inicial usando a nova função
    if (typeof window.adicionarLogPvP === 'function') {
        window.adicionarLogPvP(`⚔️ O duelo contra <span style="color:#ef4444; font-weight:bold;">${estado_arena.oponente_nome}</span> começou!`);
        
        // Esconde os textos antigos para não conflitar com a caixa nova
        const log1 = document.getElementById('pvp-log-texto-1');
        const log2 = document.getElementById('pvp-log-texto-2');
        if (log1) log1.style.display = 'none';
        if (log2) log2.style.display = 'none';
    } else {
        // Fallback de segurança
        const log1 = document.getElementById('pvp-log-texto-1');
        if (log1) log1.innerHTML = `O duelo contra <span style="color:#ef4444;">${estado_arena.oponente_nome}</span> começou!`;
        const log2 = document.getElementById('pvp-log-texto-2');
        if (log2) log2.innerText = "";
    }

    atualizarControleDeTurno(estado_arena.minha_vez);
};
// ==========================================
// 3. CONTROLE DE TURNOS
// ==========================================
function atualizarControleDeTurno(minhaVez) {
    window.dadosPvPAtual.minhaVez = minhaVez;
    window.bloqueioDeTurnoPvP = !minhaVez; // Trava se não for a sua vez

    const menuBotoes = document.getElementById('pvp-menu-botoes');
    const painelBloqueio = document.getElementById('pvp-bloqueio-turno');
    const aviso = document.getElementById('aviso-turno-pvp');

    if (minhaVez) {
        menuBotoes.style.display = 'grid';
        painelBloqueio.style.display = 'none';
        
        // Pisca o aviso "SEU TURNO!"
        aviso.style.opacity = '1';
        aviso.style.transform = 'translate(-50%, -50%) scale(1.2)';
        if (window.AudioManager) AudioManager.tocarSFX('som_turno');
        
        setTimeout(() => {
            aviso.style.opacity = '0';
            aviso.style.transform = 'translate(-50%, -50%) scale(1)';
        }, 1500);

    } else {
        menuBotoes.style.display = 'none';
        painelBloqueio.style.display = 'flex';
    }
}

// O gatilho quando você clica em Atacar/Magia/Render-se
window.executarAcaoPvP = function(tipoAcao, skillId = null, skillNome = null) {
    if (window.bloqueioDeTurnoPvP) return;
    
    // Trava os botões imediatamente para evitar clique duplo
    window.bloqueioDeTurnoPvP = true;
    document.getElementById('pvp-menu-botoes').style.display = 'none';
    document.getElementById('pvp-bloqueio-turno').style.display = 'flex';
    document.getElementById('pvp-bloqueio-turno').innerHTML = `<span style="color: #facc15;">Enviando ação...</span>`;

    // Dispara via WebSocket
    if (window.eldoraSocket) {
        window.eldoraSocket.emit('enviarAcaoPvP', {
            duelo_id: window.dadosPvPAtual.dueloId,
            acao: tipoAcao,
            skill_id: skillId
        });
    } else {
        window.avisoEldora("Erro Crítico: Conexão com o servidor perdida!");
        sairDaArenaPvP();
    }
};

window.renderSePvP = async function() {
    if(await window.confirmarEldora("Tem certeza que deseja se render e perder o duelo?")) {
        executarAcaoPvP('render_se');
    }
};

// ==========================================
// 4. ANIMAÇÕES DO MOTOR DE COMBATE
// ==========================================

// Esta função será chamada pelo Socket.IO quando o servidor processar a matemática do turno
window.processarAnimacaoTurnoPvP = function(pacoteTurno) {
    // 👇 ADICIONAR ESTE BLOCO AQUI LOGO NO INÍCIO DA FUNÇÃO 👇
    if (pacoteTurno.atacante_sid === window.eldoraSocket.id) {
        if (pacoteTurno.novo_mp !== undefined) {
            window.dadosPvPAtual.meuMpAtual = pacoteTurno.novo_mp;
            atualizarBarraPvP('bar-mp-jogador-pvp', window.dadosPvPAtual.meuMpAtual, window.dadosPvPAtual.meuMpMax);
        }
        if (pacoteTurno.cooldowns !== undefined && window.perfilDadosGlobais) {
            window.perfilDadosGlobais.cooldowns = pacoteTurno.cooldowns;
        }
    }
    const elemLog1 = document.getElementById('pvp-log-texto-1');
    const elemLog2 = document.getElementById('pvp-log-texto-2');
    
    let db = window.dadosPvPAtual;
    let indexAcao = 0;
    
    // Esconde o painel de "aguardando..." durante a animação
    document.getElementById('pvp-bloqueio-turno').style.display = 'none';

    function lerProximoLogPvP() {
        if (indexAcao >= pacoteTurno.log.length) {
            
            // 👇 BUG RESOLVIDO: O JavaScript agora procura pelo nome certo (vencedor_sid)
            if (pacoteTurno.vencedor_sid) {
                finalizarDuelo(pacoteTurno);
            } else {
                // Passa a vez baseando-se na flag enviada pelo servidor
                atualizarControleDeTurno(pacoteTurno.proximo_turno_sid === window.eldoraSocket.id);
                document.getElementById('pvp-bloqueio-turno').innerHTML = `<span style="color: #94a3b8; font-style: italic;">Aguardando turno do adversário...</span>`;
            }
            return;
        }

        const acao = pacoteTurno.log[indexAcao];
        const euSouOAtacante = (acao.autor_sid === window.eldoraSocket.id);
        
        let txtAcao = (acao.texto || "").toUpperCase();
        let ehFalha = txtAcao.includes("FALHOU") || txtAcao.includes("ESQUIVOU") || txtAcao.includes("INSUFICIENTE");
        let ehCura = txtAcao.includes("CURA") || txtAcao.includes("USOU");
        let ehCritico = txtAcao.includes("CRÍTICO");
        let danoCausado = Math.max(0, Number(acao.dano) || 0);

        // Identifica quem é quem na tela
        const meuSpriteId = 'sprite-jogador-pvp';
        const oponenteSpriteId = 'sprite-oponente-pvp';
        
        const atacanteId = euSouOAtacante ? meuSpriteId : oponenteSpriteId;
        const alvoId = euSouOAtacante ? oponenteSpriteId : meuSpriteId;
        
        // 👇 NOVO: Definindo as cores e o nome para o log scrollável
        const corTexto = euSouOAtacante ? "#38bdf8" : "#ef4444"; 
        const nomeAtacante = euSouOAtacante ? "Você" : (window.dadosPvPAtual.oponenteNome || "Oponente");

        // 👇 NOVO: Log Visual usando o sistema de Scroll em vez de sobrescrever elemLog1
        if (typeof window.adicionarLogPvP === 'function') {
            window.adicionarLogPvP(`<strong style="color:${corTexto};">${nomeAtacante}:</strong> <span style="color:#e2e8f0;">${acao.texto}</span>`);
        } else {
            // Fallback de segurança caso a função não seja encontrada
            if (typeof elemLog1 !== 'undefined' && elemLog1) {
                elemLog1.innerHTML = `<span style="color:${corTexto}; font-weight:bold;">${acao.texto}</span>`;
            }
        }

        if (ehCura) {
            animarEfeitoVisualPvP(atacanteId, 'cura', '#2ecc71');
            if (window.AudioManager) AudioManager.tocarSFX('som_cura');
            
            if (euSouOAtacante) {
                db.meuHpAtual = pacoteTurno.novo_hp;
                atualizarBarraPvP('bar-hp-jogador-pvp', db.meuHpAtual, db.meuHpMax);
            } else {
                db.oponenteHpAtual = pacoteTurno.novo_hp;
                atualizarBarraPvP('bar-hp-oponente', db.oponenteHpAtual, db.oponenteHpMax);
            }
            
        } else if (ehFalha) {
            animarEsquivaPvP(alvoId, !euSouOAtacante);
        } else {
            // Ataque Bem Sucedido!
            animarInvestidaPvP(atacanteId, !euSouOAtacante);
            
            if (euSouOAtacante) {
                db.oponenteHpAtual = Math.max(0, db.oponenteHpAtual - danoCausado);
                atualizarBarraPvP('bar-hp-oponente', db.oponenteHpAtual, db.oponenteHpMax);
            } else {
                db.meuHpAtual = Math.max(0, db.meuHpAtual - danoCausado);
                atualizarBarraPvP('bar-hp-jogador-pvp', db.meuHpAtual, db.meuHpMax);
                piscarTelaDano();
            }

            if (danoCausado > 0) {
                mostrarNumeroDano(alvoId, `-${danoCausado}`, ehCritico);
                setTimeout(() => animarDanoRecebidoPvP(alvoId), 150);
            }
            
            if (window.AudioManager) AudioManager.tocarSFX(ehCritico ? 'som_critico' : 'som_espada');

            // Magia ou Ataque Básico?
            if (acao.anim_effect || acao.tipo_skill) {
                let nomeSprite = acao.anim_effect || 'corte_perfurante_anim';
                animarMagiaSpriteGridPvP(alvoId, nomeSprite);
            } else {
                animarEfeitoVisualPvP(alvoId, 'corte', ehCritico ? '#facc15' : '#ef4444');
            }
        }

        indexAcao++;
        setTimeout(lerProximoLogPvP, 1300); // Ritmo do duelo
    }
    
    lerProximoLogPvP();
};

// ==========================================
// 5. HELPER ANIMATIONS (COM FLIP CORRIGIDO)
// ==========================================

function animarInvestidaPvP(spriteId, isOponente) {
    const el = document.getElementById(spriteId);
    if (!el) return;
    
    // O Oponente precisa preservar o scaleX(-1) para não virar de costas!
    const transformBase = isOponente ? 'scaleX(-1)' : '';
    const moveX = isOponente ? '-50px' : '50px';
    const moveY = isOponente ? '30px' : '-30px';

    el.animate([
        { transform: `${transformBase} translate(0, 0) scaleY(1)` },
        { transform: `${transformBase} translate(${moveX}, ${moveY}) scaleY(1.15)`, offset: 0.2 },
        { transform: `${transformBase} translate(0, 0) scaleY(1)`, offset: 1 }
    ], { duration: 500, easing: 'cubic-bezier(0.25, 1, 0.5, 1)' });
}

function animarDanoRecebidoPvP(spriteId) {
    const el = document.getElementById(spriteId);
    if (!el) return;
    
    const isOponente = spriteId.includes('oponente');
    const transformBase = isOponente ? 'scaleX(-1)' : '';

    el.animate([
        { transform: `${transformBase} translate(0, 0)` },
        { transform: `${transformBase} translate(-6px, 4px)` },
        { transform: `${transformBase} translate(6px, -4px)` },
        { transform: `${transformBase} translate(0, 0)` }
    ], { duration: 300 });

    el.animate([
        { filter: 'brightness(1) saturate(1) hue-rotate(0deg)' },
        { filter: 'brightness(3) saturate(5) hue-rotate(-50deg)' }, 
        { filter: 'brightness(1) saturate(1) hue-rotate(0deg)' }
    ], { duration: 300 });
}

function animarEsquivaPvP(spriteId, isOponente) {
    const el = document.getElementById(spriteId);
    if (!el) return;
    const transformBase = isOponente ? 'scaleX(-1)' : '';
    const recuo = isOponente ? '20px' : '-20px';

    el.animate([
        { transform: `${transformBase} translate(0, 0)`, opacity: 1 },
        { transform: `${transformBase} translate(${recuo}, 0)`, opacity: 0.5, offset: 0.5 },
        { transform: `${transformBase} translate(0, 0)`, opacity: 1, offset: 1 }
    ], { duration: 400 });
}

function animarEfeitoVisualPvP(alvoId, tipoEfeito, corExtra) {
    // Reutiliza a lógica central do combate.js (impacto, corte, fogo, etc)
    if (typeof animarEfeitoVisual === 'function') {
        animarEfeitoVisual(alvoId, tipoEfeito, corExtra);
    }
}

function piscarTelaDano() {
    const flash = document.getElementById('pvp-damage-flash');
    if (flash) {
        flash.style.opacity = "1";
        setTimeout(() => { flash.style.opacity = "0"; }, 150);
    }
}

function atualizarBarraPvP(elementId, atual, maximo) {
    const barra = document.getElementById(elementId);
    if (!barra) return;
    let porcentagem = maximo > 0 ? (atual / maximo) * 100 : 0;
    barra.style.width = Math.min(100, Math.max(0, porcentagem)) + '%';
    
    const textoElemento = document.getElementById(elementId.replace('bar-', 'val-'));
    if (textoElemento) textoElemento.innerText = `${Math.floor(atual)}/${maximo}`;
}

// ==========================================
// 6. ADAPTAÇÃO DA MAGIA 3x4 (12 FRAMES)
// ==========================================
window.animarMagiaSpriteGridPvP = function(alvoId, nomeEfeito) {
    const alvo = document.getElementById(alvoId);
    if (!alvo) return;

    const LINK_BASE = "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/efeitos/";
    const urlImagem = `${LINK_BASE}${nomeEfeito}.png`;

    const imgPreload = new Image();
    imgPreload.src = urlImagem;

    imgPreload.onload = () => {
        // A matemática inviolável do Sprite Sheet 3x4 (3 colunas x 4 linhas)
        const colunas = 3;
        const totalFrames = 12; 
        const fps = 12;
        const tempoPorFrame = 1000 / fps;
        
        const larguraFrame = 128; 
        const alturaFrame = 128;

        const anim = document.createElement('div');
        anim.style.position = 'absolute';
        anim.style.width = `${larguraFrame}px`;
        anim.style.height = `${alturaFrame}px`;
        anim.style.backgroundImage = `url('${urlImagem}')`;
        anim.style.backgroundRepeat = 'no-repeat';
        
        // Força o fundo a ter o tamanho exato da grade 3x4
        anim.style.backgroundSize = `${larguraFrame * colunas}px ${alturaFrame * 4}px`;
        anim.style.pointerEvents = 'none';
        anim.style.zIndex = '10000';

        const offsetX = alvo.offsetLeft + (alvo.offsetWidth / 2) - (larguraFrame / 2);
        const offsetY = alvo.offsetTop + (alvo.offsetHeight / 2) - (alturaFrame / 2);
        anim.style.left = `${offsetX}px`;
        anim.style.top = `${offsetY}px`;

        alvo.parentElement.appendChild(anim);

        let frameAtual = 0;
        const intervalo = setInterval(() => {
            if (frameAtual >= totalFrames) {
                clearInterval(intervalo);
                anim.remove(); 
                return;
            }
            const eixoX = (frameAtual % colunas) * larguraFrame;
            const eixoY = Math.floor(frameAtual / colunas) * alturaFrame;
            
            anim.style.backgroundPosition = `-${eixoX}px -${eixoY}px`;
            frameAtual++;
        }, tempoPorFrame);
    };

    imgPreload.onerror = () => {
        // Fallback visual
        animarEfeitoVisualPvP(alvoId, 'corte', '#facc15');
    };
};

// ==========================================
// 7. CONCLUSÃO DO DUELO E LIMPEZA
// ==========================================
function finalizarDuelo(pacote) {
    const euVenci = (pacote.vencedor_sid === window.eldoraSocket.id);
    
    document.getElementById('pvp-menu-botoes').style.display = "none";
    document.getElementById('pvp-bloqueio-turno').style.display = "none";
    document.getElementById('pvp-botoes-fim-batalha').style.display = "flex";

    if (euVenci) {
        // 👇 NOVO: Usa a caixa de log scrollável para a vitória
        if (typeof window.adicionarLogPvP === 'function') {
            window.adicionarLogPvP(`<br><span style="color:#facc15; font-weight:bold; font-size: 1.2em;">🏆 VITÓRIA GLORIOSA! 🏆</span>`);
            window.adicionarLogPvP(`<span style="color:#94a3b8;">Você derrotou seu rival em um combate justo!</span>`);
        } else {
            // Fallback de segurança
            const log1 = document.getElementById('pvp-log-texto-1');
            const log2 = document.getElementById('pvp-log-texto-2');
            if (log1) log1.innerHTML = `<span style="color:#facc15; font-weight:bold; font-size: 1.2em;">🏆 VITÓRIA GLORIOSA! 🏆</span>`;
            if (log2) log2.innerHTML = `<span style="color:#94a3b8;">Você derrotou seu rival em um combate justo!</span>`;
        }

        document.getElementById('sprite-oponente-pvp').style.opacity = "0.2";
        document.getElementById('sprite-jogador-pvp').classList.add('pvp-winner-glow');
        if (window.AudioManager) AudioManager.tocarSFX('som_vitoria');
    } else {
        // 👇 NOVO: Usa a caixa de log scrollável para a derrota
        if (typeof window.adicionarLogPvP === 'function') {
            window.adicionarLogPvP(`<br><span style='color:#e74c3c; font-weight:bold; font-size: 1.2em;'>💀 DERROTA...</span>`);
            window.adicionarLogPvP(`<span style="color:#94a3b8;">Você caiu diante da força do oponente.</span>`);
        } else {
            // Fallback de segurança
            const log1 = document.getElementById('pvp-log-texto-1');
            const log2 = document.getElementById('pvp-log-texto-2');
            if (log1) log1.innerHTML = `<span style='color:#e74c3c; font-weight:bold; font-size: 1.2em;'>💀 DERROTA...</span>`;
            if (log2) log2.innerHTML = `<span style="color:#94a3b8;">Você caiu diante da força do oponente.</span>`;
        }

        document.getElementById('sprite-jogador-pvp').style.opacity = "0.2";
        document.getElementById('sprite-oponente-pvp').classList.add('pvp-winner-glow');
    }
}

window.sairDaArenaPvP = function() {
    // Remove o brilho caso tenha vencido
    document.getElementById('sprite-jogador-pvp').classList.remove('pvp-winner-glow');
    document.getElementById('sprite-oponente-pvp').classList.remove('pvp-winner-glow');
    
    // Limpa UI (Esconde a tela da Arena)
    document.getElementById('tela-pvp-global').style.display = 'none';
    
    // 👇 RESTAURA TODOS OS BOTÕES E MENUS DO MAPA 👇
    const hudTop = document.getElementById('hud-moderno');
    if(hudTop) hudTop.style.display = 'flex';
    
    const menuLat = document.getElementById('menu-lateral');
    if(menuLat) menuLat.style.display = 'block';
    
    // Devolve os botões flutuantes para a tela usando a sua técnica de classes!
    document.querySelectorAll('.btn-passe-mapa, .btn-social-mapa').forEach(btn => btn.style.display = 'flex');
    
    // Garante que a aba principal do jogo volte a aparecer
    document.getElementById('aba-reino').style.display = 'block';

    // Recarrega o mapa para evitar bugs visuais
    if (typeof carregarReino === 'function') carregarReino();
};

// ==========================================
// 8. MENUS (REUTILIZANDO O PVE COM SEQUESTRO LIMPO)
// ==========================================

window.abrirMenuMagiasPvP = function() {
    // Salva a função original do PvE
    const funcOriginal = window.executarAcaoTurno;
    
    // "Sequestra" o clique para mandar pro Socket.IO do PvP
    window.executarAcaoTurno = function(acao, skillId, skillNome) {
        const container = document.getElementById('menu-skills-combate');
        if (container) container.style.display = 'none';
        
        window.executarAcaoPvP(acao, skillId, skillNome);
        
        // Devolve a função original para não quebrar o PvE!
        window.executarAcaoTurno = funcOriginal;
    };

    if (typeof window.abrirMenuMagias === 'function') {
        window.abrirMenuMagias(); // Renderiza os botões
        setTimeout(() => {
            const container = document.getElementById('menu-skills-combate');
            if (container) document.getElementById('pvp-arena').appendChild(container); 
        }, 50);
    }
};

window.abrirMenuItensPvP = function() {
    const funcOriginal = window.executarAcaoTurno;
    
    window.executarAcaoTurno = function(acao, skillId, skillNome) {
        const container = document.getElementById('menu-itens-combate');
        if (container) container.style.display = 'none';
        
        // Ação 'usar_item' do PvE vira 'item' no backend PvP
        window.executarAcaoPvP('item', skillId, skillNome);
        
        window.executarAcaoTurno = funcOriginal;
    };

    if (typeof window.abrirMenuItens === 'function') {
        window.abrirMenuItens();
        setTimeout(() => {
            const container = document.getElementById('menu-itens-combate');
            if (container) document.getElementById('pvp-arena').appendChild(container); 
        }, 50);
    }
};
// ==========================================
// NOVA FUNÇÃO: CAIXA DE LOGS SCROLLÁVEL
// ==========================================
window.adicionarLogPvP = function(textoHTML) {
    let containerLog = document.getElementById('pvp-caixa-logs-scroll');
    
    // Se a caixa ainda não existe, nós a criamos substituindo os textos antigos
    if (!containerLog) {
        const oldLog1 = document.getElementById('pvp-log-texto-1');
        if (oldLog1) {
            const parentBox = oldLog1.parentElement;
            parentBox.innerHTML = ''; // Limpa os antigos
            
            containerLog = document.createElement('div');
            containerLog.id = 'pvp-caixa-logs-scroll';
            
            // Estilização direta no JS para garantir que funcione no Mini-App
            containerLog.style.height = '110px'; // Preenche aquele espaço vazio da imagem
            containerLog.style.overflowY = 'auto';
            containerLog.style.display = 'flex';
            containerLog.style.flexDirection = 'column';
            containerLog.style.gap = '6px';
            containerLog.style.padding = '8px';
            containerLog.style.textAlign = 'left';
            containerLog.style.fontSize = '0.95em';
            containerLog.style.fontFamily = 'monospace, sans-serif'; 
            containerLog.style.backgroundColor = 'rgba(0, 0, 0, 0.5)'; // Fundo escurecido
            containerLog.style.borderRadius = '6px';
            containerLog.style.border = '1px solid rgba(255, 255, 255, 0.1)';
            
            parentBox.appendChild(containerLog);
        }
    }

    if (containerLog) {
        const novaLinha = document.createElement('div');
        novaLinha.innerHTML = textoHTML;
        // Efeito suave ao aparecer a mensagem
        novaLinha.animate([
            {opacity: 0, transform: 'translateX(-5px)'}, 
            {opacity: 1, transform: 'translateX(0)'}
        ], {duration: 300});
        
        containerLog.appendChild(novaLinha);
        containerLog.scrollTop = containerLog.scrollHeight; // Auto-scroll para o final!
    }
};