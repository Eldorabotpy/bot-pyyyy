const salasGrupoDevolvidas = new Set();
let retornoGrupoPendente = false;
function atualizarBotaoRetornoGrupo() {
    const botao = document.querySelector('#botoes-fim-batalha button');
    if (!botao) return;
    const sala = window.estadoCombateGrupoAtual;
    const grupo = !!window.salaCombateGrupoAtual && sala?.tipo === 'cacada';
    const lider = String(sala?.lider_id) === String(localStorage.getItem('jogadorEldoraID'));
    botao.disabled = grupo && (!lider || retornoGrupoPendente);
    botao.textContent = grupo ? (lider ? 'Voltar com o grupo ao mapa' : 'Aguardando o líder voltar ao mapa…') : '⬅️ Voltar ao Mapa';
}
function receberRetornoGrupo(sala) {
    const id = String(sala?.sala_id || '');
    if (!id || id !== String(window.salaCombateGrupoAtual || '')) return;
    salasGrupoDevolvidas.add(id);
    if (salasGrupoDevolvidas.size > 50) salasGrupoDevolvidas.delete(salasGrupoDevolvidas.values().next().value);
    retornoGrupoPendente = false;
    sairDaArena(true);
}

// /static/js/combate.js - VERSÃO DEFINITIVA COM TRADUTOR DE SKIN ATUALIZADO

// ==========================================
// 1. DICIONÁRIO DE CENÁRIOS
// ==========================================
const LINK_FUNDOS = "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/fundos/";
const FUNDOS_ARENAS = {
    "capital_eldora":   `${LINK_FUNDOS}capital.png`, 
    "pradaria_inicial": `${LINK_FUNDOS}pradaria.png`, 
    "floresta_sombria": `${LINK_FUNDOS}floresta.png`,
    "pedreira_granito": `${LINK_FUNDOS}pedreira.png`,
    "mina_ferro":       `${LINK_FUNDOS}mina.png` 
};

let musicaDeFundoAtual = null;
let sfxEmExecucao = [];

// ==========================================
// BLINDAGEM: IMPEDE CLIQUE VAZAR DO COMBATE PARA O MAPA
// ==========================================
function instalarTravaCliqueCombate() {
    if (window.__travaCliqueCombateInstalada) return;
    window.__travaCliqueCombateInstalada = true;

    const eventos = [
        'click',
        'dblclick',
        'mousedown',
        'mouseup',
        'pointerdown',
        'pointerup',
        'touchstart',
        'touchend',
        'contextmenu',
        'wheel'
    ];

    eventos.forEach(evtNome => {
        document.addEventListener(evtNome, function(evt) {
            const tela = document.getElementById('tela-combate-global');

            const combateAberto =
                tela &&
                tela.style.display !== 'none' &&
                getComputedStyle(tela).display !== 'none';

            if (!combateAberto || evt.target.closest?.('.eldora-dialog')) return;

            const clicouDentroCombate = tela.contains(evt.target);

            // Se o combate está aberto, qualquer clique fora dele é cancelado.
            // Isso impede o mapa/Phaser de receber clique por baixo.
            if (!clicouDentroCombate) {
                evt.preventDefault();
                evt.stopPropagation();
                evt.stopImmediatePropagation();
                return false;
            }
        }, true);
    });
}

let entradaAntesCombate = null;
function travarMapaDuranteCombate(ativo) {
    const cena = window.jogoEldora?.scene?.getScene('MapaScene');
    if (ativo && !entradaAntesCombate && cena?.input) {
        entradaAntesCombate = {cena, mouse:cena.input.enabled, teclado:cena.input.keyboard?.enabled};
        cena.input.enabled = false;
        if (cena.input.keyboard) { cena.input.keyboard.resetKeys?.(); cena.input.keyboard.enabled = false; }
        cena.isMoving = false;
        cena.player?.body?.stop();
    } else if (!ativo && entradaAntesCombate) {
        const anterior = entradaAntesCombate;
        entradaAntesCombate = null;
        anterior.cena.input.enabled = anterior.mouse;
        if (anterior.cena.input.keyboard) { anterior.cena.input.keyboard.resetKeys?.(); anterior.cena.input.keyboard.enabled = anterior.teclado; }
    }
    const tela = document.getElementById('tela-combate-global');
    if (tela && !tela.dataset.eventosIsolados) {
        tela.dataset.eventosIsolados = '1';
        for (const evento of ['click','dblclick','pointerdown','pointerup','pointermove','mousedown','mouseup','touchstart','touchend','touchmove','wheel','keydown','keyup']) tela.addEventListener(evento, e => e.stopPropagation());
    }
    const elementosMapa = [
        document.getElementById('game-container'),
        document.getElementById('phaser-game'),
        document.querySelector('canvas'),
        document.getElementById('hud-moderno'),
        document.getElementById('eldora-party-hud')
    ];

    elementosMapa.forEach(el => {
        if (!el) return;
        el.style.pointerEvents = ativo ? 'none' : '';
    });

    window.combateAbertoBloqueandoMapa = !!ativo;
}

instalarTravaCliqueCombate();
function ocultarUiMapaDuranteCombate() {
    const idsParaOcultar = [
        'btn-abrir-menu',
        'hud-moderno',
        'online-counter',
        'btn-chat-mapa',
        'eldora-party-hud'
    ];

    idsParaOcultar.forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;

        el.dataset.displayAntesCombate = el.style.display || '';
        el.style.display = 'none';
        el.style.pointerEvents = 'none';
    });

    document.querySelectorAll('.btn-passe-mapa, .btn-social-mapa').forEach(el => {
        el.dataset.displayAntesCombate = el.style.display || '';
        el.style.display = 'none';
        el.style.pointerEvents = 'none';
    });

    document.body.classList.add('combate-aberto');
}

function restaurarUiMapaDepoisCombate() {
    const idsParaRestaurar = [
        'btn-abrir-menu',
        'hud-moderno',
        'online-counter',
        'btn-chat-mapa',
        'eldora-party-hud'
    ];

    idsParaRestaurar.forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;

        el.style.display = el.dataset.displayAntesCombate || '';
        el.style.pointerEvents = '';
        delete el.dataset.displayAntesCombate;
    });

    document.querySelectorAll('.btn-passe-mapa, .btn-social-mapa').forEach(el => {
        el.style.display = el.dataset.displayAntesCombate || '';
        el.style.pointerEvents = '';
        delete el.dataset.displayAntesCombate;
    });

    document.body.classList.remove('combate-aberto');
}
// ==========================================
// UTILITIES
// ==========================================
function animarCorteVisual(alvoId, cor_brilho) { animarEfeitoVisual(alvoId, 'corte', cor_brilho); }

function animarEfeitoVisual(alvoId, tipoEfeito = 'corte', corExtra = '#fff') {
    const alvo = document.getElementById(alvoId);
    if (!alvo) return;
    const efeito = document.createElement('div');
    
    switch(tipoEfeito) {
        case 'impacto': efeito.className = 'impact-effect'; efeito.style.borderColor = corExtra; break;
        case 'fogo': efeito.className = 'fire-effect'; efeito.style.boxShadow = `0 0 20px ${corExtra}`; break;
        case 'cura': efeito.className = 'heal-effect'; efeito.style.background = `radial-gradient(circle, ${corExtra} 0%, transparent 70%)`; break;
        case 'trevas':
        case 'veneno': efeito.className = 'dark-effect'; efeito.style.background = corExtra; break;
        case 'corte':
        default: efeito.className = 'slash-effect'; efeito.style.boxShadow = `0 0 10px #fff, 0 0 20px ${corExtra}`; break;
    }
    
    efeito.style.left = (alvo.offsetLeft + alvo.offsetWidth / 2) + 'px';
    efeito.style.top = (alvo.offsetTop + alvo.offsetHeight / 2) + 'px';
    alvo.parentElement.appendChild(efeito);
    setTimeout(() => efeito.remove(), 600);
}

function mostrarNumeroDano(alvoId, valor, critico = false) {
    const alvo = document.getElementById(alvoId);
    const container = alvo ? alvo.parentElement : null;
    if (!alvo || !container) return;
    
    const num = document.createElement('div');
    num.innerText = valor;
    
    num.style.position = 'absolute';
    num.style.zIndex = '999';
    num.style.pointerEvents = 'none';
    num.style.fontFamily = "'Cinzel', 'Impact', sans-serif"; 
    num.style.fontWeight = '900';
    
    num.style.fontSize = critico ? '32px' : '24px'; 
    num.style.color = critico ? '#f1c40f' : (alvoId === 'sprite-player' ? '#ff4757' : '#ffffff');
    num.style.textShadow = '2px 2px 0 #000, -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000, 0 6px 10px rgba(0,0,0,0.8)';
    
    const alvoRect = alvo.getBoundingClientRect();
    const containerRect = container.getBoundingClientRect();
    const posX = (alvoRect.left - containerRect.left) + (alvoRect.width / 2);
    const posY = (alvoRect.top - containerRect.top) + (alvoRect.height / 2);
    
    num.style.left = posX + 'px';
    num.style.top = posY + 'px';
    
    container.appendChild(num);

    const direcao = alvoId === 'sprite-player' ? -1 : 1; 
    const desvioX = (Math.random() * 50 + 20) * direcao; 
    const desvioY = - (Math.random() * 40 + 60); 

    num.animate([
        { transform: 'translate(-50%, -50%) scale(0.3)', opacity: 0, offset: 0 },
        { transform: `translate(calc(-50% + ${desvioX * 0.2}px), calc(-50% - 20px)) scale(${critico ? 1.5 : 1.2})`, opacity: 1, offset: 0.15 },
        { transform: `translate(calc(-50% + ${desvioX}px), calc(-50% + ${desvioY}px)) scale(1)`, opacity: 1, offset: 0.7 },
        { transform: `translate(calc(-50% + ${desvioX}px), calc(-50% + ${desvioY - 15}px)) scale(0.9)`, opacity: 0, offset: 1 }
    ], {
        duration: critico ? 1100 : 900, 
        easing: 'cubic-bezier(0.25, 1, 0.5, 1)', 
        fill: 'forwards'
    });

    setTimeout(() => num.remove(), critico ? 1100 : 900);
}

function atualizarVisualBarra(elementId, atual, maximo, isMana = false) {
    const barra = document.getElementById(elementId);
    if (!barra) return;

    let vAtual = Number(atual) || 0;
    let vMaximo = Number(maximo); 
    
    let porcentagem = vMaximo > 0 ? (vAtual / vMaximo) * 100 : 0;
    
    // ==========================================
    // 🔒 MISTÉRIO DO BESTIÁRIO: CENSURAR BARRA
    // ==========================================
    let isMobNivelZero = (elementId === 'bar-hp-mob' && window.dadosCombateAtual && window.dadosCombateAtual.nivelConhecimento === 0);
    
    if (isMobNivelZero) {
        barra.style.width = '100%'; // A barra nunca desce visualmente!
        barra.style.backgroundColor = '#475569'; // Fica de uma cor neutra
    } else {
        barra.style.width = Math.min(100, porcentagem) + '%';
        if (elementId === 'bar-hp-mob') barra.style.backgroundColor = ''; // Restaura a cor vermelha original
    }

    const textId = elementId.replace('bar-', 'val-');
    const textoElemento = document.getElementById(textId);
    if (textoElemento) {
        if (isMobNivelZero) {
            textoElemento.innerText = `??? / ???`;
        } else {
            textoElemento.innerText = `${Math.floor(vAtual)}/${vMaximo}`;
        }
    }
}

async function avisarProntoCombateGrupo() {
    if (!window.salaCombateGrupoAtual || !window.dadosCombateAtual) return;

    const charId = localStorage.getItem("jogadorEldoraID");
    if (!charId) return;

    try {
        const res = await fetch('/api/combate/grupo/pronto', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: charId,
                sala_id: window.salaCombateGrupoAtual
            })
        });

        const dados = await res.json();

        if (dados && dados.sala) {
            aplicarEstadoCombateGrupo(dados, "grupoPronto");
        }

    } catch (e) {
        console.warn("Erro ao avisar pronto no combate de grupo:", e);
    }
}

// ==========================================
// INICIAR COMBATE (DOM MANIPULATION) 
// ==========================================
window.iniciarCacadaApp = async function(spawnId, opcoesGrupo = {}) {
    // ==========================================
    // 🛡️ TRAVA ANTI-CLIQUE FANTASMA 🛡️
    // ==========================================
    const telaGlobal = document.getElementById('tela-combate-global');

    if (
        telaGlobal &&
        telaGlobal.style.display === 'flex'
    ) {
        console.warn(
            "⛔ Clique fantasma bloqueado! " +
            "A arena já está em uso."
        );

        return;
    }


    // =====================================================
    // ⚔️ NOVA BATALHA SOLO = ESTADO DE TURNO LIMPO
    // =====================================================

    const ehCombateGrupo =
        opcoesGrupo.modoGrupo === true ||
        !!opcoesGrupo.salaId;

    if (!ehCombateGrupo) {

        window.bloqueioDeTurno = false;

        // Segurança contra qualquer resíduo de uma sala anterior.
        window.salaCombateGrupoAtual = null;
        window.estadoCombateGrupoAtual = null;


        // Segurança visual:
        // caso algum botão tenha sido desativado anteriormente.
        const menuBotoes =
            document.getElementById(
                'menu-botoes'
            );

        if (menuBotoes) {

            menuBotoes
                .querySelectorAll('button')
                .forEach(btn => {

                    btn.disabled = false;

                    btn.style.pointerEvents =
                        'auto';

                    btn.style.opacity =
                        '1';
                });
        }
    }


    try {
        if (musicaDeFundoAtual) {
            musicaDeFundoAtual.pause(); 
            musicaDeFundoAtual.currentTime = 0; 
            musicaDeFundoAtual = null;
        }

        if (!telaGlobal) {
            window.avisoEldora("ERRO HTML: A tela 'tela-combate-global' sumiu do index.html!");
            return;
        }
        
        telaGlobal.style.display = 'flex';
        telaGlobal.style.position = 'fixed';
        telaGlobal.style.top = '0';   
        telaGlobal.style.left = '0';  
        telaGlobal.style.zIndex = '99999';
        telaGlobal.style.backgroundColor = 'rgba(2, 6, 23, 0.95)';
        // Blindagem total da tela de combate
        telaGlobal.style.right = '0';
        telaGlobal.style.bottom = '0';
        telaGlobal.style.width = '100vw';
        telaGlobal.style.height = '100vh';
        telaGlobal.style.pointerEvents = 'auto';
        telaGlobal.style.overflow = 'hidden';
        // Esconde menu global, passe, chat, online e HUD enquanto luta
        ocultarUiMapaDuranteCombate();

        // Impede o mapa por baixo de receber clique enquanto o combate está aberto
        travarMapaDuranteCombate(true);

        // Impede o mapa por baixo de receber clique enquanto o combate está aberto
        travarMapaDuranteCombate(true);
        
        const hudMapa = document.getElementById('hud-moderno');
        if (hudMapa) hudMapa.style.display = 'none';

        document.getElementById('combate-loading').style.display = 'flex';
        const btnMute = document.getElementById('btn-mute-global');
        if (btnMute) btnMute.style.display = 'none';
        
        const partyHud = document.getElementById('eldora-party-hud');
        if (partyHud) partyHud.style.display = 'none';

        document.getElementById('combate-arena').style.display = 'none';
        
        const charId = localStorage.getItem("jogadorEldoraID");
        if (!charId) {
            window.avisoEldora("ERRO: ID do jogador não encontrado na memória!");
            return;
        }

        // 🛠️ NOVO: O Jogo baixa as suas magias atuais ANTES de entrar na arena!
        try {
            const resPerfil = await fetch(
                `/api/personagem/${charId}?t=${new Date().getTime()}`
            );

            const perfilCombate =
                await resPerfil.json();

            const perfilAnterior =
                window.perfilDadosGlobais || {};

            // =====================================================
            // 🛡️ NÃO DESTRUIR O ESTADO DA CAMPANHA
            // =====================================================
            //
            // O endpoint usado pelo combate serve principalmente
            // para atualizar skills e dados de combate.
            //
            // Nunca devemos apagar quests que já foram carregadas
            // pelo perfil oficial.
            // =====================================================

            window.perfilDadosGlobais = {
                ...perfilAnterior,
                ...perfilCombate,

                quests: {
                    ...(perfilAnterior.quests || {}),
                    ...(perfilCombate.quests || {})
                }
            };

            // ✅ Cada batalha começa com as skills prontas no frontend.
            if (window.perfilDadosGlobais) {
                window.perfilDadosGlobais.cooldowns = {};
            }

        } catch(e) {
            console.warn("Aviso: Não foi possível carregar as magias antes do combate.", e);
        }

        // Continua o combate normalmente...
        const res = await fetch('/api/combate/iniciar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: charId,
                spawn_id: spawnId,
                sala_id: opcoesGrupo.salaId || null,
                modo_grupo: opcoesGrupo.modoGrupo || false
            })
        });
        
        if (!res.ok) throw new Error(`Servidor recusou a conexão (Erro HTTP ${res.status}).`);
        const dados = await res.json();

        if (dados.erro) {
            window.avisoEldora("AVISO DO SERVIDOR: " + dados.erro);
            if(typeof sairDaArena === 'function') sairDaArena(true);
            return;
        }

        if (window.AudioManager) {
            window.AudioManager.tocarMusica('bgm_batalha');
        }

        const est = dados.estado;
        const bgArena = (typeof FUNDOS_ARENAS !== 'undefined' && FUNDOS_ARENAS[est.regiao]) ? FUNDOS_ARENAS[est.regiao] : "https://placehold.co/600x400/111/222?text=Arena+Desconhecida";
        
        // ==========================================
        // 1. DEFINIÇÃO DA SKIN DO JOGADOR
        // ==========================================
        const LINK_BASE_GITHUB = "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/";
        const cacheBuster = `?v=${new Date().getTime()}`; 
        
        let skinMemoria = localStorage.getItem("skinEquipada") || "";
        let urlSpritePlayer = ""; 

        if (skinMemoria && skinMemoria !== "padrao" && skinMemoria !== "") {
            let skinLimpa = skinMemoria.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/\s+/g, '_');
            skinLimpa = skinLimpa.replace('_masculino', '_m').replace('_feminino', '_f');
            if (skinLimpa === 'player') skinLimpa = 'aventureiro_m';
            urlSpritePlayer = `${LINK_BASE_GITHUB}classes_costa/${skinLimpa}.png${cacheBuster}`;
        } else {
            urlSpritePlayer = `${LINK_BASE_GITHUB}classes_costa/aventureiro_m.png${cacheBuster}`;
        }

        // ==========================================
        // 2. PREENCHENDO OS DADOS DO COMBATE E BESTIÁRIO
        // ==========================================
        window.dadosCombateAtual = {
            spawnId: spawnId,
            mobNome: est.mob_nome,
            playerHpMax: est.player_stats.max_hp, 
            playerMpMax: est.player_stats.max_mana, 
            mobHpMax: est.monster_stats.max_hp,
            mobHpAtual: est.monster_hp,
            playerHpAtual: est.player_hp, 
            playerMpAtual: est.player_mp,
            
            // 👉 VARIÁVEIS DO BESTIÁRIO:
            nivelConhecimento: est.nivel_conhecimento,
            abatesBestiario: est.abates_bestiario,
            monsterStats: est.monster_stats
        };

        // ==========================================
        // 📖 INJETANDO O HUD DO BESTIÁRIO (CORRIGIDO)
        // ==========================================
        let hudBestiario = document.getElementById('bestiario-mob-hud');
        if (hudBestiario) {
            hudBestiario.remove(); // Limpa o antigo para não bugar a tela
        }
        
        hudBestiario = document.createElement('div');
        hudBestiario.id = 'bestiario-mob-hud';
        
        // 🔥 A MÁGICA DO CSS AQUI: position: absolute e top: 100% garante que
        // ele nasça EXATAMENTE no limite inferior da barra de vida!
        hudBestiario.style = "position: absolute; top: 100%; margin-top: 12px; left: 0; font-size: 11.5px; text-align: center; width: 100%; display: flex; justify-content: center; flex-direction: column; align-items: center; z-index: 99;";
        
        const caixaVidaMob = document.getElementById('val-hp-mob');
        if (caixaVidaMob && caixaVidaMob.parentElement) {
            // Garante que o contêiner da barra seja a "âncora" do posicionamento
            caixaVidaMob.parentElement.style.position = 'relative';
            caixaVidaMob.parentElement.appendChild(hudBestiario);
        }

        const nivelC = est.nivel_conhecimento || 0;
        const abates = est.abates_bestiario || 0;
        
        if (nivelC === 0) {
            hudBestiario.innerHTML = `<span style="color: #94a3b8; font-style: italic; letter-spacing: 1px; text-shadow: 1px 1px 1px #000; background: rgba(0,0,0,0.5); padding: 2px 8px; border-radius: 5px;">Atributos ocultos nas sombras...</span>`;
        } else if (nivelC === 1) {
            let faltam = 10 - abates;
            hudBestiario.innerHTML = `
                <div style="background: rgba(0,0,0,0.7); border: 1px solid #475569; border-radius: 5px; padding: 3px 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.5);">
                    <span style="color: #cbd5e1;">Faltam <b>${faltam}</b> abates para atributos.</span>
                </div>`;
        } else if (nivelC >= 2) {
            let maestriaHtml = nivelC === 3 ? `<div style="color: #f1c40f; font-weight: bold; margin-bottom: 3px; font-size: 10px; text-shadow: 1px 1px 2px #000;">👑 ALVO DOMINADO (+5% DANO)</div>` : '';
            hudBestiario.innerHTML = `
                ${maestriaHtml}
                <div style="display: flex; gap: 8px; justify-content: center; background: rgba(0, 0, 0, 0); border: 1px solid ${nivelC === 3 ? '#f1c40f' : '#64748b'}; border-radius: 5px; padding: 4px 10px; color: #fff; text-shadow: 1px 1px 1px #000; box-shadow: 0 2px 5px rgba(0,0,0,0.5);">
                    <span title="Ataque">⚔️ ${est.monster_stats.attack}</span>
                    <span title="Defesa">🛡️ ${est.monster_stats.defense}</span>
                    <span title="Agilidade">🏃 ${est.monster_stats.initiative}</span>
                    <span title="Sorte">🍀 ${est.monster_stats.luck}</span>
                </div>
            `;
        }

        if (typeof atualizarVisualBarra === 'function') {
            atualizarVisualBarra('bar-mp-player', est.player_mp, est.player_stats.max_mana, true);
            atualizarVisualBarra('bar-hp-mob', est.monster_hp, est.monster_stats.max_hp);
            atualizarVisualBarra('bar-hp-player', est.player_hp, est.player_stats.max_hp);
        }
        // ==========================================
        // 3. ATUALIZANDO O VISUAL DA TELA E EMBOSCADA
        // ==========================================
        document.getElementById('arena-box').style.backgroundImage = `url('${bgArena}')`;
        document.getElementById('hud-nome-mob').innerText = est.mob_nome;
        document.getElementById('hud-lvl-mob').innerText = `LV.${est.monster_level || '??'}`;
        document.getElementById('hud-lvl-player').innerText = `LV.${est.player_level || '??'}`;
        
        document.getElementById('sprite-player').src = urlSpritePlayer;
        document.getElementById('sprite-mob').src = est.mob_img;
        
        document.getElementById('sprite-mob').style.opacity = "1";
        document.getElementById('sprite-player').style.opacity = "1";
        document.getElementById('sprite-mob').style.transform = "translate(0, 0)";
        document.getElementById('sprite-player').style.transform = "translate(0, 0)";

        // 💥 LÓGICA DE EMBOSCADA (TREMER TELA E LOG VERMELHO)
        if (est.ambush_log) {
            document.getElementById('log-texto-1').innerHTML = `<span style="color:#ef4444; font-weight:bold; text-shadow: 1px 1px 2px #000; font-size: 1.1em;">${est.ambush_log}</span>`;
            document.getElementById('log-texto-2').innerText = "Você foi pego de surpresa! O que vai fazer?";
            
            // Injeta o CSS do tremor mágico se não existir
            if (!document.getElementById('shake-style')) {
                const style = document.createElement('style');
                style.id = 'shake-style';
                style.innerHTML = `@keyframes shake-hard { 0% { transform: translate(1px, 1px) rotate(0deg); } 10% { transform: translate(-1px, -2px) rotate(-1deg); } 20% { transform: translate(-3px, 0px) rotate(1deg); } 30% { transform: translate(3px, 2px) rotate(0deg); } 40% { transform: translate(1px, -1px) rotate(1deg); } 50% { transform: translate(-1px, 2px) rotate(-1deg); } 60% { transform: translate(-3px, 1px) rotate(0deg); } 70% { transform: translate(3px, 1px) rotate(-1deg); } 80% { transform: translate(-1px, -1px) rotate(1deg); } 90% { transform: translate(1px, 2px) rotate(0deg); } 100% { transform: translate(1px, -2px) rotate(-1deg); } } .shake-hard { animation: shake-hard 0.4s; border: 2px solid #ef4444 !important; box-shadow: inset 0 0 40px rgba(239, 68, 68, 0.8) !important; }`;
                document.head.appendChild(style);
            }
            
            // Faz a arena toda tremer violentamente por meio segundo
            const arena = document.getElementById('arena-box');
            arena.classList.add('shake-hard');
            setTimeout(() => arena.classList.remove('shake-hard'), 450);
            
        } else {
            document.getElementById('log-texto-1').innerHTML = `Um <span style="color:#f1c40f;">${est.mob_nome}</span> selvagem apareceu!`;
            document.getElementById('log-texto-2').innerText = "O que você vai fazer?";
        }

        document.getElementById('botoes-fim-batalha').style.display = 'none';
        document.getElementById('menu-botoes').style.display = 'grid';
    
        document.getElementById('combate-loading').style.display = 'none';
        document.getElementById('combate-arena').style.display = 'flex';
        
        document.getElementById('combate-loading').style.display = 'none';
        document.getElementById('combate-arena').style.display = 'flex';

        if (dados.grupo && dados.sala_id) {
            window.salaCombateGrupoAtual = dados.sala_id;
            window.estadoCombateGrupoAtual = dados.sala || null;
            renderizarGrupoCombate(window.estadoCombateGrupoAtual);
            atualizarControleTurnoGrupo(window.estadoCombateGrupoAtual);

            // Só marca pronto depois que a arena já carregou na tela.
            avisarProntoCombateGrupo();
        }

        // 🤖 AUTO COMBATE
        // Só liga quando a batalha veio da Auto Caçada e não é grupo.
        if (
            opcoesGrupo.autoCacada === true &&
            !opcoesGrupo.modoGrupo &&
            !dados.grupo &&
            typeof window.iniciarAutoCombateCacada === "function"
        ) {
            window.iniciarAutoCombateCacada();
        }

    } catch(e) {

        window.avisoEldora("🚨 CRASH NO JAVASCRIPT: " + e.message);
        if(typeof sairDaArena === 'function') sairDaArena(true);
    }
}

// ==========================================
// EXECUTAR TURNO E LOGS
// ==========================================
window.bloqueioDeTurno = false;

// ==========================================
// 🤖 AUTO COMBATE DA AUTO CAÇADA
// Etapa 1: apenas ataque básico.
// Não usa skill e ainda não usa poção.
// ==========================================
window.autoCombateCacadaAtivo = false;
window.autoCombateCacadaTimer = null;

function autoCacadaMapaAindaLigada() {
    try {
        if (!window.jogoEldora) return false;

        const cenaMapa = window.jogoEldora.scene.getScene("MapaScene");

        return !!(
            cenaMapa &&
            cenaMapa.motorCacada &&
            cenaMapa.motorCacada.autoCacadaAtiva
        );
    } catch (e) {
        return false;
    }
}

function combateAutoCacadaAberto() {
    const tela = document.getElementById("tela-combate-global");
    const arena = document.getElementById("combate-arena");

    const telaAberta =
        tela &&
        tela.style.display !== "none" &&
        getComputedStyle(tela).display !== "none";

    const arenaAberta =
        arena &&
        arena.style.display !== "none" &&
        getComputedStyle(arena).display !== "none";

    return !!(telaAberta && arenaAberta);
}

function escolherPocaoCuraAutoCacada() {
    const p = window.perfilDadosGlobais || {};
    let inventarioBruto = p.inventory || p.inventario || {};

    if (typeof inventarioBruto === "string") {
        try {
            inventarioBruto = JSON.parse(inventarioBruto);
        } catch (e) {
            inventarioBruto = {};
        }
    }

    let itensArray = [];

    if (Array.isArray(inventarioBruto)) {
        itensArray = inventarioBruto;
    } else {
        itensArray = Object.entries(inventarioBruto).map(([id, valor]) => {
            if (valor && typeof valor === "object") {
                return { id, ...valor };
            }

            return {
                id,
                quantity: valor
            };
        });
    }

    const pocoes = itensArray
        .map(item => {
            const itemId = String(item.id || item.item_id || item.base_id || "").trim();

            const qtd = Number(
                item.quantity ??
                item.qtd ??
                item.quantidade ??
                item.amount ??
                0
            );

            if (!itemId.startsWith("pocao_cura")) return null;
            if (qtd <= 0) return null;

            let prioridade = 1;

            const idLower = itemId.toLowerCase();

            if (idLower.includes("suprema") || idLower.includes("lendaria")) prioridade = 6;
            else if (idLower.includes("maior") || idLower.includes("grande")) prioridade = 5;
            else if (idLower.includes("media") || idLower.includes("média")) prioridade = 4;
            else if (idLower.includes("pequena") || idLower.includes("menor")) prioridade = 3;

            const nomeExibicao = item.nome || item.name ||
                itemId
                    .replace(/_/g, " ")
                    .replace(/\b\w/g, letra => letra.toUpperCase())
                    .replace("Pocao", "Poção")
                    .replace("Media", "Média");

            return {
                id: itemId,
                nome: nomeExibicao,
                qtd,
                prioridade
            };
        })
        .filter(Boolean)
        .sort((a, b) => b.prioridade - a.prioridade);

    return pocoes.length > 0 ? pocoes[0] : null;
}

function pararAutoFarmPorFaltaDePocao() {
    window.pararAutoCombateCacada("sem poção de cura");

    try {
        if (window.jogoEldora) {
            const cenaMapa = window.jogoEldora.scene.getScene("MapaScene");

            if (
                cenaMapa &&
                cenaMapa.motorCacada &&
                typeof cenaMapa.motorCacada.pararAutoCacada === "function"
            ) {
                cenaMapa.motorCacada.pararAutoCacada("sem poção de cura", false);
            }
        }
    } catch (e) {
        console.warn("Erro ao parar Auto Caçada por falta de poção:", e);
    }

    const log1 = document.getElementById("log-texto-1");
    const log2 = document.getElementById("log-texto-2");

    if (log1) {
        log1.innerHTML = `<span style="color:#ef4444;">🧪 Auto Farm pausado: sem poção de cura.</span>`;
    }

    if (log2) {
        log2.innerText = "Seu HP está crítico. Assuma o controle manualmente.";
    }
}

window.pararAutoCombateCacada = function(motivo = "cancelado") {

    window.autoCombateCacadaAtivo = false;

    if (window.autoCombateCacadaTimer) {
        clearTimeout(window.autoCombateCacadaTimer);
        window.autoCombateCacadaTimer = null;
    }

    console.log("🛑 [AUTO COMBATE] Parado:", motivo);
};

window.agendarAutoCombateCacada = function(origem = "agendado") {
    if (window.autoCombateCacadaTimer) {
        clearTimeout(window.autoCombateCacadaTimer);
        window.autoCombateCacadaTimer = null;
    }

    window.autoCombateCacadaTimer = setTimeout(() => {
        if (!window.autoCombateCacadaAtivo) return;

        if (!autoCacadaMapaAindaLigada()) {
            window.pararAutoCombateCacada("Auto Caçada desligada no mapa");
            return;
        }

        // Segurança: não roda em grupo, raid ou invasão.
        if (window.salaCombateGrupoAtual || window.estadoCombateGrupoAtual || window.raidInvasaoAtual) {
            window.pararAutoCombateCacada("modo incompatível com Auto Combate");
            return;
        }

        if (!combateAutoCacadaAberto()) {
            window.agendarAutoCombateCacada("aguardando arena abrir");
            return;
        }

        if (!window.dadosCombateAtual) {
            window.agendarAutoCombateCacada("aguardando dados do combate");
            return;
        }

        const hpPlayer = Number(window.dadosCombateAtual.playerHpAtual || 0);
        const hpMob = Number(window.dadosCombateAtual.mobHpAtual || 0);

        if (hpPlayer <= 0) {
            window.pararAutoCombateCacada("jogador derrotado");
            return;
        }

        if (hpMob <= 0) {
            window.pararAutoCombateCacada("mob derrotado");
            return;
        }

        const botoesFim = document.getElementById("botoes-fim-batalha");
        const telaFimAberta =
            botoesFim &&
            botoesFim.style.display !== "none" &&
            getComputedStyle(botoesFim).display !== "none";

        if (telaFimAberta) {
            window.pararAutoCombateCacada("fim da batalha");
            return;
        }

        if (window.bloqueioDeTurno) {
            window.agendarAutoCombateCacada("aguardando turno liberar");
            return;
        }

        const menu = document.getElementById("menu-botoes");
        const menuAberto =
            menu &&
            menu.style.display !== "none" &&
            getComputedStyle(menu).display !== "none";

        if (!menuAberto) {
            window.agendarAutoCombateCacada("aguardando menu de ações");
            return;
        }

        const hpMaxPlayer = Number(window.dadosCombateAtual.playerHpMax || 0);
        const porcentagemHp = hpMaxPlayer > 0 ? (hpPlayer / hpMaxPlayer) * 100 : 100;

        // 🧪 AUTO POÇÃO
        // Regra pedida: usar poção apenas quando HP estiver abaixo ou igual a 5%.
        if (porcentagemHp <= 20) {
            const pocao = escolherPocaoCuraAutoCacada();

            if (!pocao) {
                console.warn("🧪 [AUTO COMBATE] HP crítico, mas não há poção de cura.");
                pararAutoFarmPorFaltaDePocao();
                return;
            }

            console.log("🧪 [AUTO COMBATE] Usando poção automaticamente:", {
                item_id: pocao.id,
                nome: pocao.nome,
                hp_atual: hpPlayer,
                hp_max: hpMaxPlayer,
                porcentagem: Math.round(porcentagemHp)
            });

            window.executarAcaoTurno("usar_item", pocao.id, pocao.nome);
            return;
        }

        console.log("⚔️ [AUTO COMBATE] Atacando automaticamente:", origem);

        window.executarAcaoTurno("atacar");
    }, 850);
};

window.iniciarAutoCombateCacada = function() {
    if (!autoCacadaMapaAindaLigada()) return;

    if (window.salaCombateGrupoAtual || window.estadoCombateGrupoAtual || window.raidInvasaoAtual) {
        return;
    }

    window.pararAutoCombateCacada("reiniciando");
    window.autoCombateCacadaAtivo = true;

    console.log("🤖 [AUTO COMBATE] Iniciado.");
    window.agendarAutoCombateCacada("início do combate");
};

window.executarAcaoTurno = async function(tipoAcao, skillId = null, skillNome = null, targetId = null) {
    const salaDaAcao = window.salaCombateGrupoAtual;

    // Segurança extra: em combate de grupo, só deixa agir se for sua vez
    if (window.estadoCombateGrupoAtual && window.estadoCombateGrupoAtual.turno_atual) {
        const meuIdTurno = String(localStorage.getItem("jogadorEldoraID") || "");
        const turnoAtual = String(window.estadoCombateGrupoAtual.turno_atual || "");

        if (turnoAtual !== meuIdTurno) {
            atualizarControleTurnoGrupo(window.estadoCombateGrupoAtual);
            return;
        }
    }

    if (window.bloqueioDeTurno) return;
    const combateDaAcao = window.dadosCombateAtual;
    combateDaAcao.rodadaVisualPendente = true;
    window.bloqueioDeTurno = true;

    document.getElementById('menu-botoes').style.display = 'none';

    const menuMagias = document.getElementById('menu-magias');
    if (menuMagias) menuMagias.style.display = 'none';

    const menuSkills = document.getElementById('menu-skills-combate');
    if (menuSkills) menuSkills.style.display = 'none';

    document.getElementById('log-texto-1').innerHTML = "<span style='color: #f1c40f;'>Calculando...</span>";
    document.getElementById('log-texto-2').innerText = "";

    const charId = localStorage.getItem("jogadorEldoraID");
    const spawnIdAtual = window.dadosCombateAtual.spawnId;

    if (window.salaCombateGrupoAtual) {
        window.__ultimoEnvioCombateGrupo = {
            sala_id: String(window.salaCombateGrupoAtual || ""),
            atacante_id: String(charId || ""),
            skill_id: skillId || null,
            acao: tipoAcao,
            ms: Date.now()
        };
    }

    try {
        const res = await fetch('/api/combate/acao', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: charId,
                spawn_id: spawnIdAtual,
                acao: tipoAcao,
                skill_id: skillId,
                target_id: targetId || null,

                // ESSENCIAL PARA COMBATE EM GRUPO
                sala_id: window.salaCombateGrupoAtual || null,
                modo_grupo: !!window.salaCombateGrupoAtual,

                mob_hp_atual: window.dadosCombateAtual.mobHpAtual,
                player_hp_atual: window.dadosCombateAtual.playerHpAtual
            })
        });

        if (!res.ok) throw new Error(`Crash no Servidor (Status ${res.status})`);

        const turno = await res.json();
        if (window.dadosCombateAtual !== combateDaAcao || combateDaAcao.rodadaVisualCancelada) return;
        if (salaDaAcao && (String(window.salaCombateGrupoAtual) !== String(salaDaAcao) || salasGrupoDevolvidas.has(String(salaDaAcao)))) return;

        if (turno.erro) {
            combateDaAcao.rodadaVisualPendente = false;
            window.bloqueioDeTurno = false;

            if (turno.sala) {
                window.estadoCombateGrupoAtual = turno.sala;
                renderizarGrupoCombate(turno.sala);
                atualizarControleTurnoGrupo(turno.sala);
            }

            document.getElementById('log-texto-1').innerHTML =
                `<span style="color:#facc15;">⚠️ ${turno.erro}</span>`;

            document.getElementById('log-texto-2').innerText = "";

            return;
        }

        if (turno.fugiu) {
            combateDaAcao.rodadaVisualPendente = false;
            document.getElementById('log-texto-1').innerHTML = `💨 ${turno.log[0].texto.toUpperCase()}`;

            setTimeout(() => {
                window.bloqueioDeTurno = false;
                sairDaArena(true);
            }, 1500);

            return;
        }

        animarAcoesDaRodada(turno, tipoAcao, skillId, skillNome);

    } catch(e) {
        combateDaAcao.rodadaVisualPendente = false;
        window.bloqueioDeTurno = false;
        console.error(e);
        if (salaDaAcao && String(window.salaCombateGrupoAtual) !== String(salaDaAcao)) return;
        window.avisoEldora("🚨 Erro Crítico de Conexão: " + e.message);
        sairDaArena(true);
    }
}

function animarInvestidaAtacar(atacanteId, alvoId, callbackHit) {
    const atacante = document.getElementById(atacanteId);
    
    atacante.style.transition = "transform 0.15s cubic-bezier(0.25, 0.46, 0.45, 0.94)";
    
    if (atacanteId === 'sprite-player') {
        atacante.style.transform = "translate(120px, -60px) scale(1.1)"; 
    } else {
        atacante.style.transform = "translate(-120px, 60px) scale(1.1)"; 
    }

    setTimeout(() => {
        if(callbackHit) callbackHit();
        
        const alvo = document.getElementById(alvoId);
        alvo.style.transform = "translate(10px, -10px)";
        setTimeout(() => alvo.style.transform = "translate(0, 0)", 100);

        setTimeout(() => {
            atacante.style.transition = "transform 0.3s ease-out";
            atacante.style.transform = "translate(0, 0) scale(1)";
        }, 200);

    }, 150); 
}

function combateMeuIdAtual() {
    return String(localStorage.getItem("jogadorEldoraID") || "");
}

function combateExtrairAtacanteId(turnoInfo = {}, acao = {}) {
    const candidatos = [
        acao.autor_id,
        acao.player_id,
        acao.char_id,
        acao.user_id,
        acao.atacante_id,
        turnoInfo.atacante_id,
        turnoInfo.player_id,
        turnoInfo.char_id,
        turnoInfo.user_id,
        turnoInfo.autor_id
    ];

    for (const valor of candidatos) {
        if (valor !== undefined && valor !== null && String(valor) !== "") {
            return String(valor);
        }
    }

    return "";
}

function combatePacotePertenceAMim(turnoInfo = {}) {
    const meuId = combateMeuIdAtual();
    const atacanteId = combateExtrairAtacanteId(turnoInfo, {});

    if (!window.salaCombateGrupoAtual) {
        return true;
    }

    if (atacanteId) {
        return atacanteId === meuId;
    }

    const ultimoEnvio = window.__ultimoEnvioCombateGrupo || null;

    if (
        ultimoEnvio &&
        ultimoEnvio.atacante_id === meuId &&
        String(ultimoEnvio.sala_id || "") === String(window.salaCombateGrupoAtual || "") &&
        Date.now() - Number(ultimoEnvio.ms || 0) < 8000
    ) {
        return true;
    }

    return false;
}

function combateLogPertenceAMim(turnoInfo = {}, acao = {}) {
    if (!window.salaCombateGrupoAtual) {
        return true;
    }

    const meuId = combateMeuIdAtual();
    const atacanteId = combateExtrairAtacanteId(turnoInfo, acao);

    if (atacanteId) {
        return atacanteId === meuId;
    }

    return !!turnoInfo.__pacoteDoMeuTurno;
}

function animarAcoesDaRodada(turnoInfo, tipoAcao, skillId, skillNome) { 
    const elemLog1 = document.getElementById('log-texto-1');
    const elemLog2 = document.getElementById('log-texto-2');
    const elemSpriteMob = document.getElementById('sprite-mob');
    const elemSpritePlayer = document.getElementById('sprite-player');
    const flash = document.getElementById('damage-flash');
    
    let db = window.dadosCombateAtual;
    let indexAcao = 0;
    
    // 👇 1. AGORA TEMOS DUAS MEMÓRIAS: UMA PARA VOCÊ E UMA PARA O MONSTRO 👇
    let logPlayerVisual = ""; 
    let logMobVisual = "";
    
    if (turnoInfo.sala) {
        window.estadoCombateGrupoAtual = turnoInfo.sala;
        renderizarGrupoCombate(turnoInfo.sala);
        atualizarControleTurnoGrupo(turnoInfo.sala);
    }

    const pacoteDoMeuTurno = combatePacotePertenceAMim(turnoInfo);
    turnoInfo.__pacoteDoMeuTurno = pacoteDoMeuTurno;

    // ✅ Em grupo, cooldown recebido só pode atualizar o dono da ação.
    // Se outro jogador usou skill, o meu grimório não deve entrar em recarga.
    if (pacoteDoMeuTurno && turnoInfo.cooldowns !== undefined && window.perfilDadosGlobais) {
        window.perfilDadosGlobais.cooldowns = turnoInfo.cooldowns;
    }

    // ✅ Em grupo, MP recebido só pode alterar o MP do dono da ação.
    if (pacoteDoMeuTurno && turnoInfo.player_mp !== undefined) {
        db.playerMpAtual = turnoInfo.player_mp;
        atualizarVisualBarra('bar-mp-player', db.playerMpAtual, db.playerMpMax, true);
    }

    const salaDaAnimacao = window.salaCombateGrupoAtual;
    db.rodadaVisualPendente = true;
    window.bloqueioDeTurno = true;
    async function lerProximoLog() {
        if (window.dadosCombateAtual !== db || db.rodadaVisualCancelada) return;
        if (salaDaAnimacao && (String(window.salaCombateGrupoAtual) !== String(salaDaAnimacao) || salasGrupoDevolvidas.has(String(salaDaAnimacao)))) return;
        if (indexAcao >= turnoInfo.log.length) {
            window.bloqueioDeTurno = !!(turnoInfo.vitoria || turnoInfo.derrota);

            if (turnoInfo.mob_hp_atual !== undefined) {
                db.mobHpAtual = Math.max(0, turnoInfo.mob_hp_atual);
                atualizarVisualBarra('bar-hp-mob', db.mobHpAtual, db.mobHpMax);
            }
            if (turnoInfo.player_hp !== undefined) {
                db.playerHpAtual = Math.max(0, turnoInfo.player_hp);
                atualizarVisualBarra('bar-hp-player', db.playerHpAtual, db.playerHpMax);
            }

            if (turnoInfo.vitoria || turnoInfo.derrota) {
                if (turnoInfo.vitoria) {
                    if (musicaDeFundoAtual) musicaDeFundoAtual.pause(); 
                    elemSpriteMob.style.opacity = "0";
                    if (window.AudioManager) window.AudioManager.tocarSFX('som_vitoria');
                } else {
                    elemSpritePlayer.style.opacity = "0";
                }
                setTimeout(() => {
                    if (window.dadosCombateAtual === db && !db.rodadaVisualCancelada) finalizarAnimacaoCombate(turnoInfo);
                }, 1000);

            } else {
                db.rodadaVisualPendente = false;
                document.getElementById('menu-botoes').style.display = 'grid';
                elemLog1.innerHTML = `<span style="color:#e74c3c; font-family: 'Cinzel', serif;">O QUE VOCÊ VAI FAZER?</span>`;
                if (turnoInfo.sala) {
                    window.estadoCombateGrupoAtual = turnoInfo.sala;
                    renderizarGrupoCombate(turnoInfo.sala);
                    atualizarControleTurnoGrupo(turnoInfo.sala);
                } else if (window.estadoCombateGrupoAtual) {
                    atualizarControleTurnoGrupo(window.estadoCombateGrupoAtual);
                }
                
                // 👇 3. INJETAMOS OS DOIS LOGS EMPILHADOS AQUI 👇
                if (logPlayerVisual !== "" || logMobVisual !== "") {
                    let historicoHtml = `<div style="font-size: 0.9em; background: rgba(0,0,0,0.3); border-radius: 6px; padding: 6px 10px; margin-top: 8px; border: 1px dashed #334155; display: inline-block; text-align: center; line-height: 1.4;">`;
                    
                    if (logPlayerVisual) {
                        historicoHtml += `<div style="margin-bottom: ${logMobVisual ? '4px' : '0'}; filter: drop-shadow(0 2px 2px rgba(0,0,0,0.8));">👤 ${logPlayerVisual}</div>`;
                    }
                    if (logMobVisual) {
                        historicoHtml += `<div style="filter: drop-shadow(0 2px 2px rgba(0,0,0,0.8));">👹 ${logMobVisual}</div>`;
                    }
                    
                    historicoHtml += `</div>`;
                    elemLog2.innerHTML = historicoHtml;
                } else {
                    elemLog2.innerText = "";
                }

                const pendente = db.estadoGrupoAposAnimacao;
                delete db.estadoGrupoAposAnimacao;
                if (pendente) aplicarEstadoCombateGrupo(pendente.dados, pendente.origem);

                // 🤖 AUTO COMBATE
                // Quando a animação do turno termina e o menu volta,
                // agenda o próximo ataque básico.
                if (
                    window.autoCombateCacadaAtivo &&
                    typeof window.agendarAutoCombateCacada === "function"
                ) {
                    window.agendarAutoCombateCacada("turno finalizado");
                }
            }
            return;
        }

        const acao = turnoInfo.log[indexAcao];

        const souAutorDestaAcao = combateLogPertenceAMim(turnoInfo, acao);

        // ✅ Combate em grupo:
        // Se outro jogador atacou, NÃO anima o meu personagem e NÃO altera meus cooldowns.
        if (acao.autor === "player" && !souAutorDestaAcao) {
            const nomeAliado = acao.autor_nome || acao.nome || "Aliado";
            let danoAliado = Number(acao.dano) || Number(acao.valor) || 0;

            if (danoAliado === 0 && acao.texto) {
                const matchRegex = String(acao.texto).match(/(?:DANO|CRÍTICO|CRITICO)\D*(\d+)/i);
                if (matchRegex && matchRegex[1]) {
                    danoAliado = parseInt(matchRegex[1]);
                }
            }

            danoAliado = Math.max(0, danoAliado);

            if (danoAliado > 0) {
                db.mobHpAtual = Math.max(0, db.mobHpAtual - danoAliado);
                atualizarVisualBarra('bar-hp-mob', db.mobHpAtual, db.mobHpMax);

                mostrarNumeroDano('sprite-mob', `-${danoAliado}`, false);
                setTimeout(() => window.animarDanoSprite('sprite-mob'), 100);
            }

            logPlayerVisual = `<span style="color:#93c5fd;">🛡️ ${nomeAliado} agiu e causou <b style="color:#ef4444;">${danoAliado}</b> de dano.</span>`;

            elemLog1.innerHTML = logPlayerVisual;
            elemLog2.innerText = "";

            indexAcao++;
            setTimeout(lerProximoLog, 900);
            return;
        }

        if (acao.autor === "player") {

            let txtAcao = (acao.texto || "").toUpperCase();
            let ehFalha = (txtAcao.includes("MANA") && txtAcao.includes("INSUFICIENTE")) || txtAcao.includes("FALHOU") || txtAcao.includes("ESQUIVOU");
            let ehCura = txtAcao.includes("USOU") || txtAcao.includes("CUROU") || txtAcao.includes("🧪");
            let ehCritico = !!acao.critico || txtAcao.includes("CRÍTICO");

            let danoCausado = Number(acao.dano) || Number(acao.valor) || 0;
            
            if (acao.dano == null && !ehFalha && !ehCura && danoCausado === 0 && acao.texto) {
                // 👇 CORREÇÃO: Só pega o número DEPOIS da palavra DANO ou CRÍTICO
                let matchRegex = acao.texto.match(/(?:DANO|CRÍTICO)\D*(\d+)/i);
                if (matchRegex && matchRegex[1]) {
                    danoCausado = parseInt(matchRegex[1]);
                }
            }

            danoCausado = Math.max(0, danoCausado); 

            // 👇 A MÁGICA: Filtra textos do servidor para não gerar ataques falsos! 👇
            if (danoCausado === 0 && !ehFalha && !ehCura && !acao.golpe) {
                elemLog1.innerHTML = `<span style="color:#facc15; font-style:italic;">${acao.texto}</span>`;
                elemLog2.innerText = "";
                indexAcao++;
                setTimeout(lerProximoLog, 800); // 800ms para a pessoa ler rápido
                return; // 👈 PÁRA AQUI! Não faz animação nem desconta vida
            } 

            // 👇 2A. SALVAMOS O LOG DO JOGADOR 👇
            if (ehCura) {
                let corTextoCura = (txtAcao.includes("MANA") || txtAcao.includes("ELIXIR") || txtAcao.includes("MÍSTICA")) ? "#3b82f6" : "#2ecc71";
                logPlayerVisual = `<span style="color:${corTextoCura};">${acao.texto}</span>`;
            } else if (ehFalha) {
                logPlayerVisual = `<span style="color:#ef4444; font-weight:bold; font-size:14px;">${acao.texto}</span>`;
            } else if (ehCritico) {
                let prefixo = (tipoAcao === 'magia' && skillNome) ? `✨ ${skillNome.toUpperCase()} CRÍTICO!` : `💥 ATAQUE CRÍTICO!`;
                logPlayerVisual = `<span style="color:#FFD700; font-weight:bold;">${prefixo} <span style="font-size:1.1em;">${danoCausado}</span> DE DANO!</span>`;
            } else {
                let prefixo = (tipoAcao === 'magia' && skillNome) ? `✨ Usou <span style="color:#c4b5fd;">${skillNome}</span> e causou` : `⚔️ Você causou`;
                logPlayerVisual = `<span style="color:#ffffff;">${prefixo} <span style="color:#ef4444; font-weight:bold;">${danoCausado}</span> de dano!</span>`;
            }
            
            if (acao.golpe) {
                const textoRoubo = acao.mostrar_roubo_vida && Number(acao.roubo_vida) > 0
                    ? ` · <b style="color:#4ade80;">roubou ${Number(acao.roubo_vida)} de vida</b>` : '';
                logPlayerVisual = `<span style="color:#fff;">${ehCritico ? '💥 Crítico! ' : ''}Ataque ${Number(acao.golpe)}: <b style="color:#f87171;">${danoCausado} de dano</b>${textoRoubo}</span>`;
            }
            elemLog1.innerHTML = logPlayerVisual; // Mostra na tela na hora da animação
            elemLog2.innerText = "";
            
            if (ehCura) {
                let ehMana = txtAcao.includes("MANA");
                animarEfeitoVisual('sprite-player', 'cura', ehMana ? '#3b82f6' : '#2ecc71');
                if (window.AudioManager) AudioManager.tocarSFX('som_cura'); 
                
                if (turnoInfo.player_hp !== undefined) {
                    db.playerHpAtual = turnoInfo.player_hp;
                    atualizarVisualBarra('bar-hp-player', db.playerHpAtual, db.playerHpMax);
                }
                if (turnoInfo.player_mp !== undefined) {
                    db.playerMpAtual = turnoInfo.player_mp;
                    atualizarVisualBarra('bar-mp-player', db.playerMpAtual, db.playerMpMax, true);
                }
            } else if (ehFalha) {
                const playerEl = document.getElementById('sprite-player');
                if (playerEl) {
                    playerEl.animate([
                        { transform: 'translate(0, 0)' },
                        { transform: 'translate(-5px, 0)' },
                        { transform: 'translate(5px, 0)' },
                        { transform: 'translate(0, 0)' }
                    ], { duration: 300 });
                }
            } else {
                window.animarInvestidaSprite('sprite-player');
                
                if (window.AudioManager) AudioManager.tocarSFX(ehCritico ? 'som_critico' : 'som_espada');

                let corEfeito = ehCritico ? '#FFD700' : '#8B0000';
                let tipoVisual = 'corte'; 

                if (tipoAcao === 'magia') {
                    let nomeSprite = acao.anim_effect;
                    if (!nomeSprite && skillId && window.perfilDadosGlobais && window.perfilDadosGlobais.database_skills) {
                        const skillDb = window.perfilDadosGlobais.database_skills[skillId];
                        if (skillDb && skillDb.anim_effect) { nomeSprite = skillDb.anim_effect; }
                    }
                    if (!nomeSprite) { nomeSprite = 'efeito_impacto_padrao'; }

                    let isSuporte = acao.tipo_skill === 'support';
                    let alvoDaAnimacao = isSuporte ? 'sprite-player' : 'sprite-mob';
                    await window.animarMagiaSpriteGrid(alvoDaAnimacao, nomeSprite);
                    if (window.dadosCombateAtual !== db || db.rodadaVisualCancelada) return;
                } else {
                    animarEfeitoVisual('sprite-mob', tipoVisual, corEfeito);
                }
                if (acao.player_hp_apos_golpe !== undefined) {
                    db.playerHpAtual = Number(acao.player_hp_apos_golpe);
                    atualizarVisualBarra('bar-hp-player', db.playerHpAtual, db.playerHpMax);
                    if (Number(acao.roubo_vida) > 0) mostrarNumeroDano('sprite-player', `+${acao.roubo_vida} HP`, false);
                }
                db.mobHpAtual = Math.max(0, db.mobHpAtual - danoCausado);
                atualizarVisualBarra('bar-hp-mob', db.mobHpAtual, db.mobHpMax);
                if (danoCausado > 0) {
                    mostrarNumeroDano('sprite-mob', `-${danoCausado}`, ehCritico);
                    window.animarDanoSprite('sprite-mob');
                }
            }
         
        } else if (acao.autor === "mob") {
            let danoTomado = Number(acao.dano) || Number(acao.valor) || 0;
            if (danoTomado === 0 && acao.texto) {
                // 👇 CORREÇÃO NO MOB: Impede que o "Golpe 2" te dê 2 de dano
                let matchRegex = acao.texto.match(/(?:DANO|CRÍTICO)\D*(\d+)/i);
                if (matchRegex && matchRegex[1]) {
                    danoTomado = parseInt(matchRegex[1]);
                }
            }

            danoTomado = Math.max(0, danoTomado);

            // 👇 2B. SALVAMOS O LOG DO MONSTRO 👇
            logMobVisual = `<span style="color:#8B0000;">Atacou! Você perdeu <span style="color:#FFD700; font-weight:bold;">${danoTomado}</span> de HP.</span>`;
            
            elemLog1.innerHTML = `<span style="color:#8B0000;">Inimigo atacou! Perdeu <span style="color:#FFD700; font-weight:bold;">${danoTomado}</span> de HP.</span>`; 
            elemLog2.innerText = ""; 
            
            db.playerHpAtual -= danoTomado;
            
            if (danoTomado > 0) {
                mostrarNumeroDano('sprite-player', `-${danoTomado}`, false);
            }
            
            if (db.playerHpAtual <= 0) db.playerHpAtual = 0;
            
            atualizarVisualBarra('bar-hp-player', db.playerHpAtual, db.playerHpMax);

            if (window.AudioManager) AudioManager.tocarSFX('som_monstro');
            animarEfeitoVisual('sprite-player', 'corte', '#9b59b6');
            
            window.animarInvestidaSprite('sprite-mob');
            if (danoTomado > 0) {
                setTimeout(() => window.animarDanoSprite('sprite-player'), 100);
            }
            
            if (flash) {
                flash.style.opacity = "1";
                setTimeout(() => { flash.style.opacity = "0"; }, 150);
            }
        }

        indexAcao++;
        setTimeout(lerProximoLog, 1200); 
    }
    lerProximoLog();
}

// ==========================================
// FUNÇÕES DE FIM DE COMBATE
// ==========================================
function rodarAnimacaoLevelUp(novoNivel) {
    const containerAlvo = document.getElementById('arena-box') || document.body;
    const oldOverlay = containerAlvo.querySelector('.level-up-overlay');
    if (oldOverlay) oldOverlay.remove();

    const overlay = document.createElement('div');
    overlay.className = 'level-up-overlay';
    
    overlay.style.position = "absolute"; overlay.style.top = "0"; overlay.style.left = "0";
    overlay.style.width = "100%"; overlay.style.height = "100%";
    overlay.style.background = "rgba(255, 215, 0, 0.4)"; overlay.style.zIndex = "100";
    overlay.style.display = "flex"; overlay.style.alignItems = "center"; overlay.style.justifyContent = "center";
    
    overlay.innerHTML = `
        <div style="text-align: center; background: #000; border: 2px solid #ffd700; padding: 20px; border-radius: 10px;">
            <h2 style="color: #ffd700; margin: 0; font-size: 2em;">LEVEL UP!</h2>
            <div style="font-size: 3em; font-weight: bold; color: #fff;">${novoNivel}</div>
        </div>
    `;

    containerAlvo.appendChild(overlay);
    document.getElementById('hud-lvl-player').innerText = `LV.${novoNivel}`;

    setTimeout(() => {
        overlay.style.transition = "opacity 0.4s ease";
        overlay.style.opacity = "0";
        setTimeout(() => overlay.remove(), 400);
    }, 3500);
}

function finalizarAnimacaoCombate(dados) {
    if (window.dadosCombateAtual) {
        window.dadosCombateAtual.rodadaVisualPendente = false;
        delete window.dadosCombateAtual.estadoGrupoAposAnimacao;
    }
    if (window.salaCombateGrupoAtual && window.estadoCombateGrupoAtual) {
        window.estadoCombateGrupoAtual.estado = dados.vitoria ? 'vitoria' : 'derrota';
    }
    const log1 = document.getElementById('log-texto-1');
    const log2 = document.getElementById('log-texto-2');

    const autoCombateEstavaAtivo = !!window.autoCombateCacadaAtivo;

    if (typeof window.pararAutoCombateCacada === "function") {
        window.pararAutoCombateCacada("fim da batalha");
    }
    
    if (dados.vitoria) {
        log1.innerHTML = `<span class="titulo-vitoria" style="color:#2ecc71; font-weight:bold;">✨ O INIMIGO FOI DERROTADO! ✨</span>`;
        
        let barraHpMob = document.getElementById('bar-hp-mob');
        if (barraHpMob) barraHpMob.style.width = '0%';
        
        const valMob = document.getElementById('val-hp-mob');
        if (valMob) valMob.innerText = `0/${window.dadosCombateAtual.mobHpMax}`;

        const mobSprite = document.getElementById('sprite-mob');
        if (mobSprite) mobSprite.style.opacity = "0";

        // Gatilho de Level Up vindo do Python
        if (dados.recompensas && dados.recompensas.lv_up) {
            window.subiuDeNivelNestaLuta = true;
            window.dadosCombateAtual.novoNivelConfirmado = dados.recompensas.new_level;
        }

    } else {
        log1.innerHTML = `<span style='color:#e74c3c; font-weight:bold;'>💀 VOCÊ DESMAIOU...</span>`;
        const ouro = dados.ouro_perdido || 0; 
        const xp = dados.xp_perdido || 0;
        log2.innerHTML = `<span style='color:#94a3b8; font-size: 0.9em;'>Os guardas te arrastaram para a segurança...</span><br>` +
                         `<span style="color: #ef4444; font-weight: bold; font-size: 1.1em; text-shadow: 1px 1px 2px #000;">` +
                         `Punição: -${ouro} Ouro e -${xp} XP</span>`;
    }
    
    document.getElementById('menu-botoes').style.display = "none";
    document.getElementById('botoes-fim-batalha').style.display = "flex";
    atualizarBotaoRetornoGrupo();

    // 🤖 AUTO FARM
    // Se a batalha veio da Auto Caçada, volta ao mapa sozinho.
    if (autoCombateEstavaAtivo) {
        setTimeout(() => {
            const telaCombate = document.getElementById("tela-combate-global");
            const botoesFim = document.getElementById("botoes-fim-batalha");

            const combateAberto =
                telaCombate &&
                telaCombate.style.display !== "none" &&
                getComputedStyle(telaCombate).display !== "none";

            const fimAberto =
                botoesFim &&
                botoesFim.style.display !== "none" &&
                getComputedStyle(botoesFim).display !== "none";

            if (combateAberto && fimAberto && typeof sairDaArena === "function") {
                sairDaArena();
            }
        }, 2200);
    }

    if (dados.vitoria) {

        const gold = dados.recompensas?.gold || 0;
        const xpGanho = dados.recompensas?.xp || 0;
        
        // ==========================================
        // 📦 LOGICA DE ITENS (COM AVISO DE VAZIO) 📦
        // ==========================================
        const itensDropados = dados.recompensas?.itens || dados.recompensas?.drops || dados.recompensas?.loot || [];
        let htmlItens = "";

        if (itensDropados.length > 0) {
            // Se caíram itens, desenhamos os cartões roxos
            htmlItens = `<div style="display: flex; gap: 5px; justify-content: center; margin-top: 8px; flex-wrap: wrap;">`;
            itensDropados.forEach(item => {
                let nomeItem = typeof item === 'string' ? item : (item.nome || item.name || item.item_id || "Item");
                nomeItem = nomeItem.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                htmlItens += `<div style="border: 1px solid #9b59b6; color: #d689e3; background: rgba(155, 89, 182, 0.15); padding: 2px 8px; border-radius: 10px; font-size: 0.85em; font-weight: bold; box-shadow: 0 0 5px rgba(155, 89, 182, 0.3);">📦 +1 ${nomeItem}</div>`;
            });
            htmlItens += `</div>`;
        } else {
            // 👇 SE NÃO CAIU NADA, MOSTRAMOS ESTE AVISO 👇
            htmlItens = `<div style="color: #64748b; font-size: 0.8em; margin-top: 10px; font-style: italic; letter-spacing: 0.5px;">Nenhum item encontrado nesta batalha.</div>`;
        }
        
        log2.innerHTML = `
            <div class="log-recompensas" style="display: flex; gap: 10px; justify-content: center; margin-top: 8px;">
                <div style="border: 1px solid #f1c40f; color: #f1c40f; background: rgba(241, 196, 15, 0.1); padding: 2px 8px; border-radius: 10px; font-weight: bold;">💰 +${gold}</div>
                <div style="border: 1px solid #3498db; color: #3498db; background: rgba(52, 152, 219, 0.1); padding: 2px 8px; border-radius: 10px; font-weight: bold;">🌟 +${xpGanho} XP</div>
            </div>
            ${htmlItens}
        `;
    }
}

function tremerArena() {
    const arena = document.getElementById('arena-box');
    arena.classList.add('shake-animation');
    setTimeout(() => arena.classList.remove('shake-animation'), 300);
}

function sairDaArena(retornoConfirmado = false) {

    // =====================================================
    // 🔓 LIBERA A TRAVA DO TURNO AO ENCERRAR A BATALHA
    // =====================================================
    //
    // Vitória/derrota deixa bloqueioDeTurno = true para
    // impedir novas ações enquanto a tela final está aberta.
    //
    // Ao voltar para o mapa essa trava precisa ser zerada,
    // senão a próxima batalha abre mas nenhum botão responde.
    // =====================================================

    window.bloqueioDeTurno = false;

    const sala = window.estadoCombateGrupoAtual;
    if (!retornoConfirmado && window.salaCombateGrupoAtual && sala?.tipo === 'cacada') {
        if (String(sala.lider_id) !== String(localStorage.getItem('jogadorEldoraID')) || retornoGrupoPendente) return;
        const socket = window.eldoraSocket || window.socket;
        if (!socket?.connected) { window.alertaEldora?.('Grupo', 'Aguarde a conexão voltar para retornar com o grupo.', 'erro'); return; }
        const salaId = window.salaCombateGrupoAtual;
        retornoGrupoPendente = true;
        atualizarBotaoRetornoGrupo();
        socket.timeout(8000).emit('retornarGrupoMapa', {sala_id:salaId}, (erro, resposta) => {
            if (String(window.salaCombateGrupoAtual) !== String(salaId)) return;
            retornoGrupoPendente = false;
            if (!erro && resposta?.success) receberRetornoGrupo(resposta.sala);
            else {
                atualizarBotaoRetornoGrupo();
                window.alertaEldora?.('Grupo', resposta?.error || 'Não foi possível confirmar o retorno. Tente novamente.', 'erro');
            }
        });
        return;
    }
    fecharSeletorAlvoGrupo();
    if (window.AudioManager) {
        window.AudioManager.pararTudo();
        const regAtual = localStorage.getItem("eldora_lastRegiao") || "capital_eldora";
        if (regAtual === 'capital_eldora') window.AudioManager.tocarMusica('bgm_capital');
    }
    
    const btnMute = document.getElementById('btn-mute-global');
    if (btnMute) btnMute.style.display = 'block';
    
    if (window.dadosCombateAtual) window.dadosCombateAtual.rodadaVisualCancelada = true;
    document.getElementById('tela-combate-global').style.display = 'none';

    // Restaura menu, passe, chat, online e HUD depois da luta
    restaurarUiMapaDepoisCombate();

    const hudMapa = document.getElementById('hud-moderno');
    if (hudMapa) hudMapa.style.display = 'flex';

    const partyHud = document.getElementById('eldora-party-hud');
    if (partyHud) partyHud.style.display = 'block';

    if (window.dadosCombateAtual && window.subiuDeNivelNestaLuta) {
        const nivelNovo = window.dadosCombateAtual.novoNivelConfirmado || "";
        if (typeof window.animarLevelUpNoMapa === 'function') {
            window.animarLevelUpNoMapa(nivelNovo);
        }
        window.subiuDeNivelNestaLuta = false;
    }

    if (window.dadosCombateAtual && window.dadosCombateAtual.mobHpAtual <= 0) {
        // Tenta apagar pelo Phaser (Caminho antigo)
        if (window.jogoEldora) {
            let cenaMapa = window.jogoEldora.scene.getScene('MapaScene');
            if (cenaMapa && cenaMapa.motorCacada) {
                cenaMapa.motorCacada.removerMob(window.dadosCombateAtual.spawnId);
            }
        }
        
        // 📡 ROTA INFALÍVEL: Dispara um grito global para o mapa_cacada.js ouvir!
        document.dispatchEvent(new CustomEvent('mobZumbiDerrubado', { 
            detail: { spawn_id: window.dadosCombateAtual.spawnId } 
        }));
    }

    if (window.dadosCombateAtual && window.dadosCombateAtual.playerHpAtual <= 0) {
        if (window.jogoEldora) {
            let cenaMapa = window.jogoEldora.scene.getScene('MapaScene');
            if (cenaMapa) {
                cenaMapa.iniciarFuneralNoLocal(); 
            }
        }
    } else {
        if (typeof carregarReino === 'function') carregarReino();
    }

    window.salaCombateGrupoAtual = null;
    window.estadoCombateGrupoAtual = null;

    const grupoContainer = document.getElementById('grupo-combate-container');
    if (grupoContainer) {
        grupoContainer.style.display = 'none';
        grupoContainer.innerHTML = '';
    }
    
    travarMapaDuranteCombate(false);

    // 🤖 AUTO CAÇADA CONTÍNUA
    // Se a Auto Caçada estava ligada antes do combate,
    // ela retoma a busca pelo próximo mob ao voltar para o mapa.
    try {
        const morreuNaBatalha =
            window.dadosCombateAtual &&
            Number(window.dadosCombateAtual.playerHpAtual || 0) <= 0;

        if (window.jogoEldora) {
            const cenaMapa = window.jogoEldora.scene.getScene("MapaScene");

            if (cenaMapa && cenaMapa.motorCacada) {
                if (morreuNaBatalha) {
                    cenaMapa.motorCacada.pararAutoCacada("jogador morreu na batalha", true);
                } else if (
                    cenaMapa.motorCacada.autoCacadaAtiva &&
                    typeof cenaMapa.motorCacada.retomarAutoCacadaDepoisCombate === "function"
                ) {
                    cenaMapa.motorCacada.retomarAutoCacadaDepoisCombate();
                }
            }
        }
    } catch (e) {
        console.warn("⚠️ Erro ao retomar Auto Caçada depois do combate:", e);
    }
}

window.animarInvestidaSprite = function(alvoId) {
    const el = document.getElementById(alvoId);
    if (!el) return;
    
    const isPlayer = alvoId === 'sprite-player';
    const moveX = isPlayer ? '40px' : '-40px';
    const moveY = isPlayer ? '-40px' : '40px';
    const rot = isPlayer ? '15deg' : '-15deg';

    el.animate([
        { transform: 'translate(0, 0) rotate(0) scale(1)' },
        { transform: `translate(${moveX}, ${moveY}) rotate(${rot}) scale(1.15)`, offset: 0.15 },
        { transform: 'translate(0, 0) rotate(0) scale(1)', offset: 1 }
    ], { duration: 600, easing: 'cubic-bezier(0.25, 1, 0.5, 1)' });
}

window.animarDanoSprite = function(alvoId) {
    const el = document.getElementById(alvoId);
    if (!el) return;
    
    el.animate([
        { transform: 'translate(0, 0)' },
        { transform: 'translate(-8px, 4px)' },
        { transform: 'translate(8px, -4px)' },
        { transform: 'translate(-8px, -4px)' },
        { transform: 'translate(8px, 4px)' },
        { transform: 'translate(0, 0)' }
    ], { duration: 300 });

    el.animate([
        { filter: 'brightness(1) saturate(1) hue-rotate(0deg)' },
        { filter: 'brightness(2.5) saturate(5) hue-rotate(-50deg)' }, 
        { filter: 'brightness(1) saturate(1) hue-rotate(0deg)' }
    ], { duration: 300 });
}

// Adicione ao final do seu combate.js

window.abrirMenuItens = function() {
    const p = window.perfilDadosGlobais || {}; 
    let container = document.getElementById('menu-itens-combate');
    
    if (!container) {
        container = document.createElement('div');
        container.id = 'menu-itens-combate';
        // Fundo escuro elegante com bordas vermelhas (Tema de Sangue/Cura)
        container.style = "display:none; position:absolute; top:50%; left:50%; transform:translate(-50%, -50%); background: linear-gradient(180deg, rgba(15,23,42,0.98) 0%, rgba(2,6,23,0.98) 100%); backdrop-filter: blur(10px); padding:20px; border:1px solid #334155; border-top: 3px solid #ef4444; border-bottom: 3px solid #ef4444; border-radius:8px; z-index:10000; width: 290px; box-shadow: 0 10px 40px rgba(0,0,0,0.9); text-align: center;";
        document.getElementById('combate-arena').appendChild(container);
    }
    
    let inventarioBruto = p.inventory || p.inventario || {};
    if (typeof inventarioBruto === 'string') {
        try { inventarioBruto = JSON.parse(inventarioBruto); } catch(e) { inventarioBruto = {}; }
    }

    let itensArray = [];
    if (Array.isArray(inventarioBruto)) {
        itensArray = inventarioBruto; 
    } else {
        itensArray = Object.entries(inventarioBruto).map(([k, v]) => {
            return typeof v === 'object' ? { id: k, ...v } : { id: k, quantity: v };
        });
    }

    container.style.display = 'block';
    // Título Centralizado com Ícone
    container.innerHTML = `
        <div style="display: flex; align-items: center; justify-content: center; gap: 8px; margin-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 10px;">
            <span style="font-size: 20px; filter: drop-shadow(0 0 5px #ef4444);">🧪</span>
            <h3 style="margin:0; color:#f87171; font-family:'Cinzel', serif; font-size:18px; text-shadow:0 0 10px rgba(239, 68, 68, 0.4); letter-spacing: 1px;">Cinto de Poções</h3>
        </div>
    `;

    // Grid Perfeito com 3 colunas
    const grid = document.createElement('div');
    grid.style = "display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; justify-items: center; max-height: 250px; overflow-y: auto; padding: 5px 0; scrollbar-width: thin; scrollbar-color: #ef4444 transparent;";

    let encontrouPocao = false;

    for (const item of itensArray) {
        const itemId = item.id || item.base_id || "";
        
        // Filtro de Ferro
        if (itemId.startsWith('pocao_cura') || itemId.startsWith('pocao_mana')) {
            
            const qtd = Number(item.quantity || item.qtd || item.quantidade || 0);
            if (qtd <= 0) continue;

            encontrouPocao = true;
            
            // Corrige o nome chato para o português correto ("Pocao" -> "Poção")
            let nomeExibicao = itemId.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            nomeExibicao = nomeExibicao.replace('Pocao', 'Poção').replace('Media', 'Média').replace('Magica', 'Mágica');

            // Magia das Cores: Poção de Mana brilha em azul, Poção de Cura em vermelho!
            const isMana = itemId.includes('mana');
            const corTema = isMana ? '#3b82f6' : '#ef4444';
            const corTemaFundo = isMana ? 'rgba(59, 130, 246, 0.1)' : 'rgba(239, 68, 68, 0.1)';

            const imgUrl = `https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/itens/consumiveis/${itemId}.png?v=${new Date().getTime()}`;
            const fallbackIcon = `https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/itens/consumiveis/default.png`;

            const btn = document.createElement('div');
            btn.style = "display:flex; flex-direction:column; align-items:center; cursor:pointer; width: 100%; position: relative;";
            
            btn.onclick = () => {
                container.style.display = 'none';
                window.executarAcaoTurno('usar_item', itemId, nomeExibicao);
            };

            // O Slot do Item (Formato Quadrado Profundo)
            btn.innerHTML = `
                <div class="pocao-slot" style="position:relative; width: 60px; height: 60px; background: ${corTemaFundo}; border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; box-shadow: inset 0 0 15px rgba(0,0,0,0.9); transition: 0.2s; display: flex; align-items: center; justify-content: center;">
                    <img src="${imgUrl}" onerror="this.onerror=null; this.src='${fallbackIcon}'" style="width: 75%; height: 75%; object-fit: contain; filter: drop-shadow(0 5px 5px rgba(0,0,0,0.8)); transition: 0.2s;" class="pocao-img">
                    
                    <div style="position: absolute; bottom: -8px; right: -8px; background: ${corTema}; color: #fff; font-size: 11px; font-weight: 900; border-radius: 6px; padding: 2px 6px; border: 2px solid #0f172a; box-shadow: 0 3px 5px rgba(0,0,0,0.8); font-family: 'Arial', sans-serif; letter-spacing: 0.5px;">x${qtd}</div>
                </div>
                <div style="margin-top: 12px; font-size: 11px; color: #cbd5e1; font-weight: bold; text-shadow: 1px 1px 2px #000; line-height: 1.1; font-family: 'Cinzel', serif;">${nomeExibicao}</div>
            `;

            // Animação Hover focada no Slot Quadrado
            btn.onmouseover = () => {
                const slot = btn.querySelector('.pocao-slot');
                const img = btn.querySelector('.pocao-img');
                if(slot) { slot.style.borderColor = corTema; slot.style.boxShadow = `0 0 15px ${corTema}88, inset 0 0 10px ${corTema}22`; }
                if(img) { img.style.transform = 'scale(1.15) translateY(-2px)'; }
            };
            btn.onmouseout = () => {
                const slot = btn.querySelector('.pocao-slot');
                const img = btn.querySelector('.pocao-img');
                if(slot) { slot.style.borderColor = 'rgba(255,255,255,0.05)'; slot.style.boxShadow = 'inset 0 0 15px rgba(0,0,0,0.9)'; }
                if(img) { img.style.transform = 'scale(1) translateY(0)'; }
            };

            grid.appendChild(btn);
        }
    }

    if (!encontrouPocao) {
        grid.innerHTML = `<div style="grid-column: 1 / -1; color: #64748b; font-size: 13px; font-style: italic; padding: 20px 0;">O teu cinto de poções está vazio.</div>`;
    }

    container.appendChild(grid);

    // Botão Fechar Minimalista
    const fecharBtn = document.createElement('button');
    fecharBtn.innerText = "Fechar Cinto";
    fecharBtn.style = "margin-top: 15px; background: transparent; color: #94a3b8; border: 1px solid #475569; padding: 8px 0; border-radius: 8px; cursor: pointer; font-family: 'Cinzel', serif; font-weight: bold; transition: 0.2s; width: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.3);";
    fecharBtn.onmouseover = () => { fecharBtn.style.color = "#fff"; fecharBtn.style.borderColor = "#94a3b8"; fecharBtn.style.background = "rgba(255,255,255,0.05)"; };
    fecharBtn.onmouseout = () => { fecharBtn.style.color = "#94a3b8"; fecharBtn.style.borderColor = "#475569"; fecharBtn.style.background = "transparent"; };
    fecharBtn.onclick = () => container.style.display = 'none';

    container.appendChild(fecharBtn);
};
// ==========================================
// SUPORTE DE GRUPO: ESCOLHER ALVO / DETECTAR CURA
// ==========================================
function obterDadosSkillCombate(skillId) {
    const p = window.perfilDadosGlobais || {};
    const dbSkills = p.database_skills || {};
    const baseSkill = dbSkills[skillId] || {};

    const minhasSkills = p.skills_desbloqueadas || p.skills || {};
    const instancia = minhasSkills[skillId] || {};
    const raridade = instancia.rarity || "comum";

    const rarityData = baseSkill.rarity_effects?.[raridade] ||
                       baseSkill.rarity_effects?.comum ||
                       {};

    return {
        ...baseSkill,
        ...rarityData,
        effects: rarityData.effects || baseSkill.effects || {},
        rarity: raridade
    };
}

function skillEhSuporteGrupo(skillId) {
    const skill = obterDadosSkillCombate(skillId);
    const effects = skill.effects || {};

    return (
        skill.type === "support" ||
        effects.party_heal ||
        effects.party_mana ||
        effects.party_buff ||
        effects.self_heal_percent ||
        effects.target === "ally" ||
        effects.target === "party"
    );
}

function skillPrecisaEscolherAliado(skillId) {
    const skill = obterDadosSkillCombate(skillId);
    const effects = skill.effects || {};

    return effects.target === "ally";
}

function fecharSeletorAlvoGrupo() {
    const seletor = document.getElementById("seletor-alvo-grupo-combate");
    if (seletor) seletor.remove();
}

function abrirSeletorAlvoGrupo(skillId, nomeMagia) {
    fecharSeletorAlvoGrupo();

    const sala = window.estadoCombateGrupoAtual;
    if (!sala || !Array.isArray(sala.herois)) {
        window.executarAcaoTurno("magia", skillId, nomeMagia);
        return;
    }

    const arena = document.getElementById("combate-arena") || document.body;
    const meuId = String(localStorage.getItem("jogadorEldoraID") || "");

    const overlay = document.createElement("div");
    overlay.id = "seletor-alvo-grupo-combate";
    overlay.style.cssText = `
        position:absolute;
        inset:0;
        z-index:10050;
        background:rgba(2,6,23,0.70);
        backdrop-filter:blur(4px);
        display:flex;
        align-items:center;
        justify-content:center;
        pointer-events:auto;
    `;

    const caixa = document.createElement("div");
    caixa.style.cssText = `
        width:320px;
        max-width:92vw;
        background:linear-gradient(180deg, rgba(15,23,42,.98), rgba(2,6,23,.98));
        border:1px solid #38bdf8;
        border-top:3px solid #22c55e;
        border-radius:12px;
        box-shadow:0 15px 45px rgba(0,0,0,.85);
        padding:14px;
        font-family:Arial, sans-serif;
        color:#fff;
        text-align:center;
    `;

    caixa.innerHTML = `
        <div style="font-family:'Cinzel',serif; color:#86efac; font-size:17px; font-weight:900; margin-bottom:4px;">
            Escolha o alvo
        </div>
        <div style="color:#cbd5e1; font-size:12px; margin-bottom:12px;">
            ${nomeMagia || "Magia de Suporte"}
        </div>
    `;

    const lista = document.createElement("div");
    lista.style.cssText = `
        display:flex;
        flex-direction:column;
        gap:8px;
        max-height:260px;
        overflow-y:auto;
    `;

    sala.herois.forEach(h => {
        const idHeroi = String(h.char_id || h.id || h._id || "");
        if (!idHeroi) return;

        const nome = h.nome || h.character_name || "Herói";
        const souEu = idHeroi === meuId;

        const hpAtual = Number(h.current_hp ?? h.hp ?? 0);
        const hpMax = Number(h.max_hp || 100);
        const mpAtual = Number(h.current_mp ?? h.mp ?? 0);
        const mpMax = Number(h.max_mana || h.max_mp || 50);

        const pctHp = hpMax > 0 ? Math.max(0, Math.min(100, (hpAtual / hpMax) * 100)) : 0;
        const pctMp = mpMax > 0 ? Math.max(0, Math.min(100, (mpAtual / mpMax) * 100)) : 0;

        const morto = hpAtual <= 0;

        const btn = document.createElement("button");
        btn.disabled = morto;
        btn.style.cssText = `
            width:100%;
            border:1px solid ${souEu ? "#facc15" : "#334155"};
            background:${morto ? "rgba(69,10,10,.78)" : "rgba(8,15,30,.96)"};
            border-radius:10px;
            padding:8px;
            cursor:${morto ? "not-allowed" : "pointer"};
            opacity:${morto ? ".55" : "1"};
            color:#fff;
            text-align:left;
        `;

        btn.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:5px;">
                <span style="font-weight:900; font-size:13px; color:${souEu ? "#facc15" : "#e2e8f0"};">
                    ${morto ? "💀" : "✨"} ${nome}
                </span>
                <span style="font-size:10px; color:#94a3b8;">
                    ${souEu ? "VOCÊ" : "ALIADO"}
                </span>
            </div>

            <div style="height:7px; background:#020617; border-radius:5px; overflow:hidden; margin-bottom:4px;">
                <div style="height:100%; width:${pctHp}%; background:#22c55e;"></div>
            </div>

            <div style="height:5px; background:#020617; border-radius:5px; overflow:hidden;">
                <div style="height:100%; width:${pctMp}%; background:#3b82f6;"></div>
            </div>

            <div style="display:flex; justify-content:space-between; font-size:10px; color:#94a3b8; margin-top:3px;">
                <span>HP ${Math.floor(hpAtual)}/${hpMax}</span>
                <span>MP ${Math.floor(mpAtual)}/${mpMax}</span>
            </div>
        `;

        btn.onclick = () => {
            if (morto) return;
            fecharSeletorAlvoGrupo();
            window.executarAcaoTurno("magia", skillId, nomeMagia, idHeroi);
        };

        lista.appendChild(btn);
    });

    caixa.appendChild(lista);

    const cancelar = document.createElement("button");
    cancelar.innerText = "Cancelar";
    cancelar.style.cssText = `
        margin-top:12px;
        width:100%;
        background:transparent;
        color:#94a3b8;
        border:1px solid #475569;
        border-radius:8px;
        padding:8px;
        cursor:pointer;
        font-family:'Cinzel',serif;
        font-weight:bold;
    `;
    cancelar.onclick = fecharSeletorAlvoGrupo;

    caixa.appendChild(cancelar);
    overlay.appendChild(caixa);
    arena.appendChild(overlay);
}

function sincronizarMeuHudPelaSala(sala) {
    if (!sala || !Array.isArray(sala.herois) || !window.dadosCombateAtual) return;

    const meuId = String(localStorage.getItem("jogadorEldoraID") || "");
    const eu = sala.herois.find(h => String(h.char_id || h.id || h._id || "") === meuId);

    if (!eu) return;

    const hpAtual = Number(eu.current_hp ?? eu.hp ?? 0);
    const hpMax = Number(eu.max_hp || window.dadosCombateAtual.playerHpMax || 100);
    const mpAtual = Number(eu.current_mp ?? eu.mp ?? 0);
    const mpMax = Number(eu.max_mana || eu.max_mp || window.dadosCombateAtual.playerMpMax || 50);

    window.dadosCombateAtual.playerHpAtual = hpAtual;
    window.dadosCombateAtual.playerHpMax = hpMax;
    window.dadosCombateAtual.playerMpAtual = mpAtual;
    window.dadosCombateAtual.playerMpMax = mpMax;

    atualizarVisualBarra("bar-hp-player", hpAtual, hpMax);
    atualizarVisualBarra("bar-mp-player", mpAtual, mpMax, true);
}

window.abrirMenuMagias = function() {
    const p = window.perfilDadosGlobais; 
    let container = document.getElementById('menu-skills-combate');
    
    if (!container) {
        container = document.createElement('div');
        container.id = 'menu-skills-combate';
        container.style = "display:none; position:absolute; top:50%; left:50%; transform:translate(-50%, -50%); background:rgba(15, 23, 42, 0.95); backdrop-filter: blur(8px); padding:20px; border:2px solid #8b5cf6; border-radius:12px; z-index:10000; width: 340px; box-shadow: 0 10px 30px rgba(0,0,0,0.9), inset 0 0 20px rgba(139, 92, 246, 0.15); text-align: center;";
        document.getElementById('combate-arena').appendChild(container);
    }
    
    const skillsEquipadas = p.skills_equipadas || {};
    const dbSkills = p.database_skills || {};
    const cooldownsAtivos = p.cooldowns || {}; // 👈 LÊ A CONTAGEM DE TURNOS

    container.style.display = 'block';
    container.innerHTML = `<h3 style="margin-top:0; margin-bottom:15px; color:#facc15; font-family:'Cinzel', serif; font-size:18px; text-shadow:0 0 10px rgba(250, 204, 21, 0.4); border-bottom:1px solid #334155; padding-bottom:10px;">Magias Preparadas</h3>`;

    const grid = document.createElement('div');
    grid.style = "display: grid; grid-template-columns: repeat(auto-fill, minmax(85px, 1fr)); gap: 12px; justify-items: center;";

    let encontrouSkill = false;
    let manaAtual = p.current_mp || 0;
    if (window.dadosCombateAtual) {
        manaAtual = window.dadosCombateAtual.playerMpAtual;
    } else if (window.dadosPvPAtual) {
        manaAtual = window.dadosPvPAtual.meuMpAtual;
    }

    [1, 2, 3, 4, 5].forEach(slotNum => {
        const skillId = skillsEquipadas[`slot_${slotNum}`];
        if (!skillId) return;

        encontrouSkill = true;
        const infoMagia = dbSkills[skillId] || {};
        const nomeIcone = infoMagia.icon || 'default_skill';
        const nomeMagia = infoMagia.display_name || 'Magia';
        
        let custoMana = infoMagia.mana_cost || infoMagia.mp_cost || 0;
        let turnosCD_Base = infoMagia.cooldown_turns || 0;

        if (infoMagia.rarity_effects && infoMagia.rarity_effects.comum) {
            custoMana = infoMagia.rarity_effects.comum.mana_cost || infoMagia.rarity_effects.comum.mp_cost || custoMana;
            if (infoMagia.rarity_effects.comum.effects && infoMagia.rarity_effects.comum.effects.cooldown_turns !== undefined) {
                turnosCD_Base = infoMagia.rarity_effects.comum.effects.cooldown_turns;
            }
        }
        
        // 👇 CÁLCULO DE BLOQUEIOS (MANA E TEMPO) 👇
        const cdRestante = parseInt(cooldownsAtivos[skillId] || 0);
        const emCooldown = cdRestante > 0;
        const semMana = manaAtual < custoMana;
        const estaBloqueado = semMana || emCooldown;
        const ehSuporte = skillEhSuporteGrupo(skillId);
        const precisaAlvo = skillPrecisaEscolherAliado(skillId);

        let etiquetaSkill = "";
        if (ehSuporte) {
            etiquetaSkill = precisaAlvo ? "ALVO" : "GRUPO";
        }

        const imgUrl = `https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/sprites/skills/${nomeIcone}.png`;
        const fallbackIcon = `https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/sprites/skills/default_skill.png`;

        const btn = document.createElement('div');
        btn.style = `display:flex; flex-direction:column; align-items:center; cursor:${estaBloqueado ? 'not-allowed' : 'pointer'}; background:rgba(30, 41, 59, 0.8); border:1px solid ${estaBloqueado ? '#ef4444' : '#475569'}; border-radius:8px; padding:8px; width: 100%; transition: all 0.2s; box-shadow: 0 4px 6px rgba(0,0,0,0.3); opacity: ${estaBloqueado ? '0.6' : '1'};`;
        
        if (!estaBloqueado) {
            btn.onmouseover = () => {
                btn.style.transform = "translateY(-3px)";
                btn.style.borderColor = "#8b5cf6";
                btn.style.boxShadow = "0 6px 12px rgba(139, 92, 246, 0.4)";
                btn.style.background = "rgba(30, 41, 59, 1)";
            };
            btn.onmouseout = () => {
                btn.style.transform = "translateY(0)";
                btn.style.borderColor = "#475569";
                btn.style.boxShadow = "0 4px 6px rgba(0,0,0,0.3)";
                btn.style.background = "rgba(30, 41, 59, 0.8)";
            };
        }

        btn.onclick = () => {
            if (estaBloqueado) {
                btn.style.animation = "shake-hard 0.3s";
                setTimeout(() => btn.style.animation = "", 300);
            return;
        }

        container.style.display = 'none';

        if (
            window.salaCombateGrupoAtual &&
            skillEhSuporteGrupo(skillId) &&
            skillPrecisaEscolherAliado(skillId)
        ) {
            abrirSeletorAlvoGrupo(skillId, nomeMagia);
            return;
        }

        window.executarAcaoTurno('magia', skillId, nomeMagia);
    };

        // 👇 A MÁGICA VISUAL DA CONTAGEM REGRESSIVA 👇
        let htmlImagemCentral = `
            <img src="${imgUrl}" onerror="this.onerror=null; this.src='${fallbackIcon}'" style="width:100%; height:100%; object-fit:cover; border-radius:6px; border: 1px solid #0f172a; background:#000; filter: ${estaBloqueado ? 'grayscale(100%)' : 'none'};">
        `;
        
        if (emCooldown) {
            htmlImagemCentral += `
            <div style="position:absolute; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.7); border-radius:6px; display:flex; align-items:center; justify-content:center; z-index:5;">
                <span style="color:#ef4444; font-size:26px; font-weight:900; text-shadow: 2px 2px 0 #000, -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000; font-family:'Impact', sans-serif;">${cdRestante}</span>
            </div>`;
        }

        btn.innerHTML = `
            <div style="position:relative; width:46px; height:46px;">
                ${htmlImagemCentral}
                <span style="position:absolute; top:-6px; right:-6px; background:#8b5cf6; border:1px solid #fff; padding:1px 5px; border-radius:6px; color:#fff; font-size:10px; font-weight:bold; box-shadow:0 0 5px #000; z-index:10;">S${slotNum}</span>
                ${etiquetaSkill ? `
                    <span style="
                        position:absolute;
                        bottom:-6px;
                        left:-6px;
                        background:${precisaAlvo ? '#22c55e' : '#0ea5e9'};
                        border:1px solid #fff;
                        padding:1px 5px;
                        border-radius:6px;
                        color:#fff;
                        font-size:8px;
                        font-weight:900;
                        box-shadow:0 0 5px #000;
                        z-index:10;
                    ">${etiquetaSkill}</span>
                ` : ""}
            </div>
            <span style="color:#cbd5e1; font-size:10px; font-weight:bold; margin-top:8px; text-align:center; line-height:1.2; word-wrap:break-word; text-shadow: 1px 1px 2px #000;">${nomeMagia}</span>
            
            <div style="display:flex; gap: 8px; margin-top: 6px; background: rgba(0,0,0,0.6); padding: 3px 6px; border-radius: 4px; border: 1px solid #334155;">
                <span style="color: ${semMana ? '#ef4444' : '#60a5fa'}; font-size: 11px; font-weight: bold;" title="Custo de Mana">💧${custoMana}</span>
                <span style="color: #f87171; font-size: 11px; font-weight: bold;" title="Tempo Base">⏳${turnosCD_Base}</span>
            </div>
        `;
        grid.appendChild(btn);
    });

    if (!encontrouSkill) {
        grid.innerHTML = `<div style="grid-column: 1 / -1; color: #94a3b8; font-size: 13px; font-style: italic; padding: 20px 0;">O teu grimório de batalha está vazio.</div>`;
    }

    container.appendChild(grid);

    const fecharBtn = document.createElement('button');
    fecharBtn.innerText = "Fechar";
    fecharBtn.style = "margin-top: 20px; background: transparent; color: #94a3b8; border: 1px solid #475569; padding: 6px 20px; border-radius: 6px; cursor: pointer; font-family: 'Cinzel', serif; font-weight: bold; transition: 0.2s; box-shadow: 0 2px 4px rgba(0,0,0,0.2);";
    fecharBtn.onmouseover = () => { fecharBtn.style.color = "#fff"; fecharBtn.style.borderColor = "#fff"; fecharBtn.style.background = "rgba(255,255,255,0.1)"; };
    fecharBtn.onmouseout = () => { fecharBtn.style.color = "#94a3b8"; fecharBtn.style.borderColor = "#475569"; fecharBtn.style.background = "transparent"; };
    fecharBtn.onclick = () => container.style.display = 'none';

    container.appendChild(fecharBtn);
};

// ==========================================
// MOTOR DE ANIMAÇÃO DE MAGIAS (COM PRELOAD)
// ==========================================
window.animarMagiaSpriteGrid = function(alvoId, nomeEfeito) {
    return new Promise(resolve => {
        const alvo = document.getElementById(alvoId);
        if (!alvo) { resolve(false); return; }
        const combate = window.dadosCombateAtual;
        if (!nomeEfeito || nomeEfeito === 'efeito_impacto_padrao') nomeEfeito = 'corte_perfurante_anim';
        const urlImagem = `https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/efeitos/${nomeEfeito}.png`;
        const img = new Image();
        let encerrado = false, anim = null, intervalo = null;
        const alvoValido = () => alvo.isConnected && window.dadosCombateAtual === combate && !combate?.rodadaVisualCancelada;
        const terminar = resultado => {
            if (encerrado) return;
            encerrado = true;
            clearTimeout(limiteCarga);
            clearInterval(intervalo);
            img.onload = img.onerror = null;
            if (anim) anim.remove();
            resolve(resultado);
        };
        const fallback = () => {
            if (encerrado) return;
            clearTimeout(limiteCarga);
            img.onload = img.onerror = null;
            if (!alvoValido()) { terminar(false); return; }
            animarEfeitoVisual(alvoId, 'corte', '#facc15');
            setTimeout(() => terminar(alvoValido()), 600);
        };
        const limiteCarga = setTimeout(fallback, 2500);
        img.onerror = fallback;
        img.onload = () => {
            if (encerrado) return;
            clearTimeout(limiteCarga);
            if (!alvoValido()) { terminar(false); return; }
            anim = document.createElement('div');
            Object.assign(anim.style, {
                position: 'absolute', width: '128px', height: '128px',
                backgroundImage: `url('${urlImagem}')`, backgroundRepeat: 'no-repeat',
                backgroundSize: '384px 512px', backgroundPosition: '0px 0px',
                pointerEvents: 'none', zIndex: '10000',
                left: `${alvo.offsetLeft + alvo.offsetWidth / 2 - 64}px`,
                top: `${alvo.offsetTop + alvo.offsetHeight / 2 - 64}px`
            });
            alvo.parentElement.appendChild(anim);
            let frame = 0;
            intervalo = setInterval(() => {
                if (!alvoValido()) { terminar(false); return; }
                frame++;
                if (frame >= 12) { terminar(true); return; }
                anim.style.backgroundPosition = `-${(frame % 3) * 128}px -${Math.floor(frame / 3) * 128}px`;
            }, 1000 / 12);
        };
        // Instala os callbacks antes de iniciar a carga, inclusive quando há cache.
        img.src = urlImagem;
    });
};

function atualizarControleTurnoGrupo(sala) {
    const menu = document.getElementById('menu-botoes');
    if (!menu) return;

    const botoes = menu.querySelectorAll('button');
    const meuId = String(localStorage.getItem("jogadorEldoraID") || "");
    
    if (sala && ['vitoria','derrota','cancelada'].includes(sala.estado)) {
        window.bloqueioDeTurno = true;
        menu.style.display = 'none';
        botoes.forEach(btn => { btn.disabled = true; });
        atualizarBotaoRetornoGrupo();
        return;
    }
    if (sala && sala.estado === "aguardando") {
        window.bloqueioDeTurno = true;
 
        menu.style.display = 'grid';

        botoes.forEach(btn => {
            btn.disabled = true;
            btn.style.opacity = "0.45";
            btn.style.pointerEvents = "none";
        });

        const prontos = sala.membros_prontos || {};
        const total = Array.isArray(sala.membros_ids) ? sala.membros_ids.length : 0;
        const qtdProntos = Object.values(prontos).filter(Boolean).length;

        const log1 = document.getElementById('log-texto-1');
        if (log1) {
            log1.innerHTML = `<span style="color:#facc15;">⏳ Aguardando grupo carregar... ${qtdProntos}/${total}</span>`;
        }

        return;
    }
    if (!sala || !sala.turno_atual) {
        window.bloqueioDeTurno = false;

        botoes.forEach(btn => {
            btn.disabled = false;
            btn.style.opacity = "1";
            btn.style.pointerEvents = "auto";
        });

        return;
    }

    const turnoAtual = String(sala.turno_atual || "");
    const minhaVez = turnoAtual === meuId;
    
    window.bloqueioDeTurno = !minhaVez;

    if (minhaVez) {
        menu.style.display = 'grid';
    }

    botoes.forEach(btn => {
        btn.disabled = !minhaVez;
        btn.style.opacity = minhaVez ? "1" : "0.45";
        btn.style.pointerEvents = minhaVez ? "auto" : "none";
    });

    const log1 = document.getElementById('log-texto-1');

    if (log1 && !minhaVez) {
        log1.innerHTML = `<span style="color:#94a3b8;">⏳ Aguarde sua vez...</span>`;
    }

    if (log1 && minhaVez) {
        log1.innerHTML = `<span style="color:#22c55e;">✅ Sua vez de agir!</span>`;
    }

    console.log("[TURNO GRUPO]", {
        meuId,
        turnoAtual,
        minhaVez,
        sala_id: sala.sala_id
    });
}

function renderizarGrupoCombate(sala) {
    const container = document.getElementById('grupo-combate-container');
    if (!container) return;

    if (!sala || !Array.isArray(sala.herois) || sala.herois.length <= 1) {
        container.style.display = 'none';
        container.innerHTML = '';
        return;
    }

    const meuId = String(localStorage.getItem("jogadorEldoraID") || "");

    const aliados = sala.herois.filter(h => {
        const idHeroi = String(h.char_id || h.id || h._id || '');
        return idHeroi && idHeroi !== meuId;
    });

    if (aliados.length === 0) {
        container.style.display = 'none';
        container.innerHTML = '';
        return;
    }

    container.style.cssText = `
        position: absolute;
        left: 12px;
        right: 58px;
        top: 82px;
        z-index: 80;
        display: flex;
        gap: 6px;
        align-items: center;
        justify-content: flex-start;
        pointer-events: none;
        overflow: hidden;
        height: 30px;
    `;

    container.innerHTML = '';

    aliados.slice(0, 4).forEach(h => {
        const idHeroi = String(h.char_id || h.id || h._id || '');
        const nome = h.nome || h.character_name || 'Herói';

        const nomeCurto = nome.length > 8 ? nome.slice(0, 8) + '…' : nome;

        const hpAtual = Number(h.current_hp ?? h.hp ?? 0);
        const hpMax = Number(h.max_hp || 100);
        const mpAtual = Number(h.current_mp ?? h.mp ?? 0);
        const mpMax = Number(h.max_mana || h.max_mp || 50);

        const pctHp = hpMax > 0 ? Math.max(0, Math.min(100, (hpAtual / hpMax) * 100)) : 0;
        const pctMp = mpMax > 0 ? Math.max(0, Math.min(100, (mpAtual / mpMax) * 100)) : 0;

        const morto = hpAtual <= 0;
        const ehTurno = String(sala.turno_atual || '') === idHeroi;

        const card = document.createElement('div');

        card.style.cssText = `
            width: 76px;
            height: 26px;
            flex: 0 0 76px;
            position: relative;
            background: ${morto ? 'rgba(69,10,10,.88)' : 'rgba(2,6,23,.72)'};
            border: 1px solid ${ehTurno ? '#facc15' : 'rgba(59,130,246,.55)'};
            border-radius: 9px;
            box-shadow: ${ehTurno ? '0 0 8px rgba(250,204,21,.75)' : '0 3px 8px rgba(0,0,0,.35)'};
            backdrop-filter: blur(3px);
            padding: 3px 5px;
            box-sizing: border-box;
            font-family: Arial, sans-serif;
            overflow: hidden;
        `;

        card.innerHTML = `
            <div style="
                display: flex;
                align-items: center;
                justify-content: space-between;
                height: 10px;
                margin-bottom: 2px;
            ">
                <span style="
                    color: ${ehTurno ? '#facc15' : '#e2e8f0'};
                    font-size: 9px;
                    font-weight: 900;
                    text-shadow: 1px 1px 2px #000;
                    max-width: 54px;
                    overflow: hidden;
                    white-space: nowrap;
                    text-overflow: ellipsis;
                    line-height: 1;
                ">
                    ${morto ? '💀' : '🛡️'} ${nomeCurto}
                </span>

                <span style="
                    color: ${ehTurno ? '#facc15' : '#64748b'};
                    font-size: 8px;
                    font-weight: 900;
                    line-height: 1;
                ">
                    ${ehTurno ? '▶' : ''}
                </span>
            </div>

            <div style="
                height: 5px;
                background: rgba(2,6,23,.95);
                border-radius: 5px;
                overflow: hidden;
                margin-bottom: 2px;
            ">
                <div style="
                    width: ${pctHp}%;
                    height: 100%;
                    background: ${morto ? '#7f1d1d' : '#10b981'};
                    transition: width .25s ease;
                "></div>
            </div>

            <div style="
                height: 4px;
                background: rgba(2,6,23,.95);
                border-radius: 5px;
                overflow: hidden;
            ">
                <div style="
                    width: ${pctMp}%;
                    height: 100%;
                    background: #3b82f6;
                    transition: width .25s ease;
                "></div>
            </div>
        `;

        container.appendChild(card);
    });
}

function normalizarIdCombateGrupo(valor) {
    return valor === undefined || valor === null ? "" : String(valor);
}

function extrairSalaPayloadGrupo(dados) {
    if (!dados) return null;
    if (dados.sala) return dados.sala;
    if (dados.sala_id && dados.membros_ids) return dados;
    return null;
}

function extrairHpMobDaSalaGrupo(sala) {
    if (!sala || !Array.isArray(sala.mobs) || sala.mobs.length === 0) return null;

    const mob = sala.mobs[0];
    const hp = mob.hp_atual ?? mob.hp ?? mob.current_hp;

    return hp === undefined || hp === null ? null : Number(hp);
}

function sincronizarMeuHudPelaSala(sala) {
    if (!sala || !Array.isArray(sala.herois) || !window.dadosCombateAtual) return;

    const meuId = String(localStorage.getItem("jogadorEldoraID") || "");
    const eu = sala.herois.find(h => String(h.char_id || h.id || h._id || "") === meuId);

    if (!eu) return;

    const hpAtual = Number(eu.current_hp ?? eu.hp ?? 0);
    const hpMax = Number(eu.max_hp || window.dadosCombateAtual.playerHpMax || 100);
    const mpAtual = Number(eu.current_mp ?? eu.mp ?? 0);
    const mpMax = Number(eu.max_mana || eu.max_mp || window.dadosCombateAtual.playerMpMax || 50);

    window.dadosCombateAtual.playerHpAtual = hpAtual;
    window.dadosCombateAtual.playerHpMax = hpMax;
    window.dadosCombateAtual.playerMpAtual = mpAtual;
    window.dadosCombateAtual.playerMpMax = mpMax;

    atualizarVisualBarra("bar-hp-player", hpAtual, hpMax);
    atualizarVisualBarra("bar-mp-player", mpAtual, mpMax, true);
}

function aplicarEstadoCombateGrupo(dados, origem = "socket") {
    if (!dados) return false;
    
    const sala = extrairSalaPayloadGrupo(dados);

    const salaIdPayload = normalizarIdCombateGrupo(
        dados.sala_id || dados.salaId || (sala && sala.sala_id) || window.salaCombateGrupoAtual
    );

    if (!salaIdPayload || salasGrupoDevolvidas.has(salaIdPayload)) return false;
    if (!window.salaCombateGrupoAtual) return false;
    if (sala?.retorno_mapa && salaIdPayload === String(window.salaCombateGrupoAtual)) {
        receberRetornoGrupo(sala); return true;
    }

    if (
        window.salaCombateGrupoAtual &&
        normalizarIdCombateGrupo(window.salaCombateGrupoAtual) !== salaIdPayload
    ) {
        console.warn("⚠️ Estado de outra sala ignorado:", {
            origem,
            recebido: salaIdPayload,
            atual: window.salaCombateGrupoAtual
        });

        return false;
    }

    // O resultado do socket pode chegar antes da resposta HTTP da ação.
    // A rodada local apresenta o golpe antes de aplicar o estado final.
    if (window.dadosCombateAtual?.rodadaVisualPendente) {
        window.dadosCombateAtual.estadoGrupoAposAnimacao = { dados, origem };
        return true;
    }

    window.salaCombateGrupoAtual = salaIdPayload;

    if (sala) {
        window.estadoCombateGrupoAtual = sala;
        renderizarGrupoCombate(sala);
        sincronizarMeuHudPelaSala(sala);
        atualizarControleTurnoGrupo(sala);
    }

    let mobHp = dados.mob_hp ?? dados.mobHp ?? dados.mob_hp_atual ?? null;

    if (mobHp === null && sala) {
        mobHp = extrairHpMobDaSalaGrupo(sala);
    }

    if (mobHp !== null && mobHp !== undefined && window.dadosCombateAtual) {
        mobHp = Math.max(0, Number(mobHp) || 0);
        window.dadosCombateAtual.mobHpAtual = mobHp;

        if (typeof atualizarVisualBarra === 'function') {
            const hpMax = window.dadosCombateAtual.mobHpMax || mobHp || 1;
            atualizarVisualBarra('bar-hp-mob', mobHp, hpMax);
        }
    }

    const estado = dados.estado || (sala && sala.estado) || "";
    const finalizado = !!dados.finalizado || estado === "vitoria" || estado === "derrota";

    if (finalizado) {
        window.bloqueioDeTurno = true;

        if (estado === "vitoria" && window.dadosCombateAtual) {
            window.dadosCombateAtual.mobHpAtual = 0;

            if (typeof atualizarVisualBarra === 'function') {
                atualizarVisualBarra('bar-hp-mob', 0, window.dadosCombateAtual.mobHpMax || 1);
            }
        }

        const fimVisivel = document.getElementById('botoes-fim-batalha')?.style.display === 'flex';
        atualizarBotaoRetornoGrupo();
        if (fimVisivel && !dados.recompensas) return true;
        finalizarAnimacaoCombate({
            vitoria: estado === "vitoria" || (window.dadosCombateAtual && window.dadosCombateAtual.mobHpAtual <= 0),
            derrota: estado === "derrota",
            recompensas: dados.recompensas || { gold: 0, xp: 0, itens: [] },
            ouro_perdido: dados.ouro_perdido || 0,
            xp_perdido: dados.xp_perdido || 0
        });

        return true;
    }

    return true;
}

function registrarSocketCombateGrupo(tentativa = 0) {
    const socketCombateGrupo = window.eldoraSocket || window.socket;

    if (!socketCombateGrupo) {
        if (tentativa < 80) {
            setTimeout(() => registrarSocketCombateGrupo(tentativa + 1), 250);
        } else {
            console.warn("⚠️ Nenhum socket encontrado para combate em grupo.");
        }

        return;
    }

    if (socketCombateGrupo.__combateGrupoRegistrado) return;
    socketCombateGrupo.__combateGrupoRegistrado = true;

    socketCombateGrupo.on('grupoRetornouMapa', receberRetornoGrupo);
    const recuperarRetorno = () => {
        if (window.salaCombateGrupoAtual && socketCombateGrupo.connected && ['vitoria','derrota','cancelada'].includes(window.estadoCombateGrupoAtual?.estado)) {
            socketCombateGrupo.emit('solicitarEstadoSala', {sala_id:window.salaCombateGrupoAtual});
        }
    };
    socketCombateGrupo.on('connect', recuperarRetorno);
    setInterval(recuperarRetorno, 3000);
    socketCombateGrupo.off('convocarCombateGrupo');
    socketCombateGrupo.on('convocarCombateGrupo', async function(dados) {
        console.log("🤝 Convocado para combate em grupo:", dados);

        if (!dados || !dados.spawn_id || !dados.sala_id) {
            console.warn("Pacote de combate em grupo inválido:", dados);
            return;
        }

        if (salasGrupoDevolvidas.has(String(dados.sala_id))) return;
        const anterior = window.estadoCombateGrupoAtual;
        if (window.salaCombateGrupoAtual && String(window.salaCombateGrupoAtual) !== String(dados.sala_id)) {
            if (!['vitoria','derrota','cancelada'].includes(anterior?.estado)) return;
            salasGrupoDevolvidas.add(String(window.salaCombateGrupoAtual));
            sairDaArena(true);
        }
        window.salaCombateGrupoAtual = normalizarIdCombateGrupo(dados.sala_id);
        window.estadoCombateGrupoAtual = dados.sala || null;

        if (typeof window.iniciarCacadaApp === 'function') {
            await window.iniciarCacadaApp(dados.spawn_id, {
                salaId: dados.sala_id,
                modoGrupo: true
            });
        }

        aplicarEstadoCombateGrupo(dados, "convocarCombateGrupo");
    });

    socketCombateGrupo.off('grupoMobHpUpdate');
    socketCombateGrupo.on('grupoMobHpUpdate', function(dados) {
        console.log("🤝 grupoMobHpUpdate recebido:", dados);
        aplicarEstadoCombateGrupo(dados, "grupoMobHpUpdate");
    });

    socketCombateGrupo.off('estadoSalaGrupo');
    socketCombateGrupo.on('estadoSalaGrupo', function(dados) {
        console.log("🤝 estadoSalaGrupo recebido:", dados);
        aplicarEstadoCombateGrupo(dados, "estadoSalaGrupo");
    });

    socketCombateGrupo.off('grupoCombateEstado');
    socketCombateGrupo.on('grupoCombateEstado', function(dados) {
        console.log("🤝 grupoCombateEstado recebido:", dados);
        aplicarEstadoCombateGrupo(dados, "grupoCombateEstado");
    });

    console.log("✅ Socket do combate em grupo registrado.");
}

registrarSocketCombateGrupo();

// ==========================================================
// RAID DA INVASÃO DO REINO — INTERFACE VISUAL
// ==========================================================

window.raidInvasaoAtual = null;
window.raidInvasaoAlvoSelecionado = null;
window.bloqueioTurnoRaid = false;

function raidEscapeHtml(txt) {
    return String(txt ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function raidMeuId() {
    return String(localStorage.getItem("jogadorEldoraID") || "");
}

function raidEhMinhaVez() {
    const raid = window.raidInvasaoAtual;
    if (!raid) return false;

    const ordem = raid.ordem_turnos || [];
    const idx = Number(raid.turno_index || 0);
    const turnoAtual = String(ordem[idx] || raid.proximo_turno_id || "");

    return turnoAtual === raidMeuId();
}

function raidCriarTelaSeNaoExiste() {
    let tela = document.getElementById("tela-raid-invasao");

    if (tela) return tela;

    if (!document.getElementById("raid-invasao-style")) {
        const style = document.createElement("style");
        style.id = "raid-invasao-style";
        style.innerHTML = `
            #tela-raid-invasao * {
                box-sizing: border-box;
            }

            .raid-card {
                background: rgba(8, 15, 30, .96);
                border: 1px solid #24334d;
                border-radius: 10px;
                padding: 7px;
                box-shadow: 0 4px 12px rgba(0,0,0,.35);
            }

            .raid-card-turno {
                border-color: #facc15 !important;
                box-shadow: 0 0 12px rgba(250,204,21,.35) !important;
            }

            .raid-card-eu {
                border-color: #38bdf8 !important;
            }

            .raid-card-alvo {
                border-color: #facc15 !important;
                background: rgba(88,18,18,.96) !important;
            }

            .raid-mini-bar {
                height: 7px;
                background: #020617;
                border-radius: 999px;
                overflow: hidden;
                margin-top: 4px;
            }

            .raid-btn {
                border: 1px solid #475569;
                border-radius: 10px;
                padding: 10px 8px;
                font-weight: 900;
                font-family: Cinzel, Arial, sans-serif;
                cursor: pointer;
                color: #fff;
                background: linear-gradient(180deg, rgba(30,41,59,.96), rgba(15,23,42,.96));
                box-shadow: 0 4px 10px rgba(0,0,0,.45);
            }

            .raid-btn:hover {
                filter: brightness(1.14);
            }

            .raid-btn-atacar {
                border-color: #ef4444;
            }

            .raid-btn-skill {
                border-color: #8b5cf6;
            }

            .raid-log-line {
                padding: 4px 6px;
                border-bottom: 1px solid rgba(148,163,184,.10);
            }

            @media (max-width: 430px) {
                #raid-invasao-box {
                    width: 100vw !important;
                    height: calc(100vh - 30px) !important;
                    border-radius: 0 !important;
                    border-left: 0 !important;
                    border-right: 0 !important;
                }

                #raid-palco {
                    min-height: 178px !important;
                }

                #raid-sprite-heroi {
                    height: 92px !important;
                    left: 18px !important;
                    bottom: 14px !important;
                }

                #raid-sprite-mob {
                    height: 118px !important;
                    right: 16px !important;
                    bottom: 12px !important;
                }
            }
        `;
        document.head.appendChild(style);
    }

    tela = document.createElement("div");
    tela.id = "tela-raid-invasao";
    tela.style.cssText = `
        display:none;
        position:fixed;
        inset:0;
        z-index:999999;
        background:rgba(2,6,23,.92);
        color:#fff;
        font-family:Arial, sans-serif;
        overflow:hidden;
        pointer-events:auto;
    `;

    tela.innerHTML = `
        <div id="raid-invasao-box" style="
            width:min(100vw, 430px);
            height:calc(100vh - 28px);
            margin:0 auto;
            background:linear-gradient(180deg, #0f172a 0%, #020617 100%);
            border:1px solid #334155;
            border-radius:14px;
            overflow:hidden;
            display:flex;
            flex-direction:column;
            box-shadow:0 20px 60px rgba(0,0,0,.85);
        ">
            <div style="
                padding:8px 10px;
                background:linear-gradient(90deg, rgba(127,29,29,.95), rgba(15,23,42,.98));
                border-bottom:1px solid #ca8a04;
                display:flex;
                align-items:center;
                justify-content:space-between;
                gap:8px;
                flex:0 0 auto;
            ">
                <div style="min-width:0;">
                    <div id="raid-invasao-titulo" style="
                        color:#facc15;
                        font-family:'Cinzel',serif;
                        font-size:15px;
                        font-weight:900;
                        white-space:nowrap;
                        overflow:hidden;
                        text-overflow:ellipsis;
                    ">🛡️ Frente da Invasão</div>

                    <div id="raid-invasao-subtitulo" style="
                        color:#cbd5e1;
                        font-size:11px;
                        margin-top:1px;
                        white-space:nowrap;
                        overflow:hidden;
                        text-overflow:ellipsis;
                    ">Onda — Grupo contra a horda</div>
                </div>

                <button onclick="sairDaRaidInvasao()" style="
                    flex:0 0 auto;
                    background:#1e293b;
                    color:#e2e8f0;
                    border:1px solid #64748b;
                    border-radius:9px;
                    padding:8px 10px;
                    font-weight:900;
                    cursor:pointer;
                ">SAIR</button>
            </div>

            <div id="raid-palco" style="
                position:relative;
                margin:8px;
                min-height:190px;
                flex:0 0 auto;
                border:1px solid #334155;
                border-radius:14px;
                overflow:hidden;
                background-image:url('https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/fundos/capital.png');
                background-size:cover;
                background-position:center;
                box-shadow:inset 0 0 65px rgba(0,0,0,.78);
            ">
                <div style="
                    position:absolute;
                    inset:0;
                    background:
                        radial-gradient(circle at 76% 56%, rgba(239,68,68,.22), transparent 35%),
                        linear-gradient(180deg, rgba(2,6,23,.08), rgba(2,6,23,.72));
                    pointer-events:none;
                "></div>

                <div id="raid-aviso-turno" style="
                    position:absolute;
                    top:8px;
                    left:50%;
                    transform:translateX(-50%);
                    z-index:20;
                    padding:6px 12px;
                    background:rgba(2,6,23,.82);
                    border:1px solid #facc15;
                    border-radius:999px;
                    color:#facc15;
                    font-size:12px;
                    font-weight:900;
                    text-align:center;
                    box-shadow:0 0 15px rgba(0,0,0,.55);
                    white-space:nowrap;
                ">Aguardando...</div>

                <img id="raid-sprite-heroi" src="" style="
                    position:absolute;
                    left:22px;
                    bottom:16px;
                    height:100px;
                    z-index:8;
                    filter:drop-shadow(0 10px 8px rgba(0,0,0,.85));
                ">

                <div style="
                    position:absolute;
                    left:50%;
                    top:50%;
                    transform:translate(-50%, -50%);
                    z-index:7;
                    font-family:'Cinzel',serif;
                    font-weight:900;
                    font-size:26px;
                    color:#facc15;
                    text-shadow:0 3px 5px #000;
                    opacity:.8;
                ">VS</div>

                <img id="raid-sprite-mob" src="" style="
                    position:absolute;
                    right:20px;
                    bottom:14px;
                    height:126px;
                    z-index:8;
                    filter:drop-shadow(0 10px 8px rgba(0,0,0,.9));
                    transform:scaleX(-1);
                ">

                <div id="raid-alvo-nome" style="
                    position:absolute;
                    right:10px;
                    bottom:6px;
                    z-index:12;
                    max-width:190px;
                    background:rgba(2,6,23,.78);
                    border:1px solid rgba(250,204,21,.45);
                    border-radius:8px;
                    padding:4px 7px;
                    color:#facc15;
                    font-size:11px;
                    font-weight:900;
                    text-align:right;
                    white-space:nowrap;
                    overflow:hidden;
                    text-overflow:ellipsis;
                ">Alvo</div>
            </div>

            <div style="
                padding:0 8px;
                display:grid;
                grid-template-columns:1fr 1fr;
                gap:7px;
                flex:0 0 auto;
                min-height:128px;
            ">
                <div style="
                    min-width:0;
                    background:rgba(15,23,42,.72);
                    border:1px solid #24334d;
                    border-radius:12px;
                    padding:7px;
                    overflow:hidden;
                ">
                    <div style="font-family:'Cinzel',serif;color:#60a5fa;font-size:12px;font-weight:900;margin-bottom:5px;">
                        🛡️ Heróis
                    </div>
                    <div id="raid-lista-herois" style="
                        display:flex;
                        flex-direction:column;
                        gap:5px;
                        max-height:96px;
                        overflow-y:auto;
                        padding-right:2px;
                    "></div>
                </div>

                <div style="
                    min-width:0;
                    background:rgba(15,23,42,.72);
                    border:1px solid #24334d;
                    border-radius:12px;
                    padding:7px;
                    overflow:hidden;
                ">
                    <div style="font-family:'Cinzel',serif;color:#f87171;font-size:12px;font-weight:900;margin-bottom:5px;">
                        👹 Inimigos
                    </div>
                    <div id="raid-lista-mobs" style="
                        display:flex;
                        flex-direction:column;
                        gap:5px;
                        max-height:96px;
                        overflow-y:auto;
                        padding-right:2px;
                    "></div>
                </div>
            </div>

            <div id="raid-log" style="
                margin:8px;
                flex:1 1 auto;
                min-height:72px;
                max-height:115px;
                background:rgba(2,6,23,.92);
                border:1px solid #24334d;
                border-radius:12px;
                padding:6px;
                overflow-y:auto;
                font-size:12px;
                line-height:1.35;
                color:#cbd5e1;
            "></div>

            <div id="raid-menu-botoes" style="
                display:grid;
                grid-template-columns:1fr 1fr;
                gap:8px;
                padding:0 8px 8px 8px;
                flex:0 0 auto;
            ">
                <button onclick="executarAcaoRaid('atacar')" class="raid-btn raid-btn-atacar">⚔️ Atacar</button>
                <button onclick="abrirMenuSkillsRaid()" class="raid-btn raid-btn-skill">✨ Skill</button>
            </div>

            <div id="raid-botoes-fim" style="
                display:none;
                padding:0 8px 8px 8px;
                flex:0 0 auto;
            ">
                <button onclick="sairDaRaidInvasao()" class="raid-btn" style="width:100%;border-color:#22c55e;">
                    ⬅️ Voltar ao Mapa
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(tela);
    return tela;
}

function raidAdicionarLog(html) {
    const box = document.getElementById("raid-log");
    if (!box) return;

    const linha = document.createElement("div");
    linha.className = "raid-log-line";
    linha.innerHTML = html;

    linha.animate(
        [
            { opacity: 0, transform: "translateX(-6px)" },
            { opacity: 1, transform: "translateX(0)" }
        ],
        { duration: 180 }
    );

    box.appendChild(linha);
    box.scrollTop = box.scrollHeight;
}
window.raidAdicionarLog = raidAdicionarLog;

function raidPct(atual, max) {
    atual = Number(atual || 0);
    max = Number(max || 1);
    return Math.max(0, Math.min(100, (atual / max) * 100));
}

const RAID_IMAGENS_INVASAO = {
    // ONDA 1 — Slimes
    "ond1_rei_slime": "rei_slime",
    "rei_slime": "rei_slime",

    "ond1_pequeno_slime": "pequeno_slime",
    "ond1_slime_verde": "slime_verde",
    "ond1_slime_azul": "slime_azul",
    "ond1_slime_magma": "slime_magma",
    "ond1_slime_terra": "slime_terra",
    "ond1_slime_venenoso": "slime_venenoso",
    "ond1_slime_eletrico": "slime_eletrico",
    "ond1_slime_brilhante": "slime_brilhante",
    "ond1_slime_escuridao": "slime_escuridao",

    // ONDA 2 — Esqueletos
    "onda2_soldado_esqueletico": "soldado_esqueletico",
    "onda2_lacaio_reanimado": "lacaio_reanimado",
    "onda2_arqueiro_esqueletico": "arqueiro_esqueletico",
    "onda2_bruto_reanimado": "bruto_reanimado",
    "onda2_mago_esqueletico": "mago_esqueletico",
    "onda2_espadachim_ossudo": "espadachim_ossudo",
    "onda2_legionario_caido": "legionario_caido",
    "onda2_lobo_esqueletico": "lobo_esqueletico",
    "onda2_esqueleto_amaldicoado": "esqueleto_amaldicoado",
    "onda2_campeao_do_sepulcro": "campeao_do_sepulcro",

    // ONDA 3 — Goblins
    "onda3_rei_goblin": "rei_goblin",
    "onda3_goblin_catador": "goblin_catador",
    "onda3_goblin_fura_pe": "goblin_fura_pe",
    "onda3_atirador_goblin": "atirador_goblin",
    "onda3_brutamontes_goblin": "brutamontes_goblin",
    "onda3_goblin_xama": "goblin_xama",
    "onda3_goblin_ardilheiro": "goblin_ardilheiro",
    "onda3_montador_de_lobo": "montador_de_lobo",
    "onda3_goblin_bombardeiro": "goblin_bombardeiro",
    "onda3_chefe_goblin": "chefe_goblin",

    // ONDA 4 — dragonoides
    "onda4_prole_de_dragao": "prole_de_dragao",
    "onda4_mineiro_kobold": "mineiro_kobold",
    "onda4_lanceiro_kobold": "lanceiro_kobold",
    "onda4_atirador_de_dardo": "atirador_de_dardo",
    "onda4_batedor_draconiano": "batedor_draconiano",
    "onda4_armadilheiro_kobold": "armadilheiro_kobold",
    "onda4_geomante_kobold": "geomante_kobold",
    "onda4_guarda_da_ninhada": "guarda_da_ninhada",
    "onda4_guerreiro_escamadura": "guerreiro_escamadura",
    "onda4_porta_estandarte_kobold": "porta_estandarte_kobold",

};

function raidNormalizarMobId(mob) {
    let id = String(
        mob?.skin ||
        mob?.monster_id ||
        mob?.base_id ||
        mob?.boss_base_id ||
        mob?.id ||
        ""
    );

    // Remove sufixos criados pela frente da invasão.
    id = id
        .replace(/_(norte|sul|leste|oeste|central)_summon_\d+$/i, "")
        .replace(/_(norte|sul|leste|oeste|central)_\d+$/i, "")
        .replace(/_(norte|sul|leste|oeste|central)$/i, "")
        .replace(/_summon_\d+$/i, "");

    return id;
}

function raidUrlMob(mob) {
    const idBase = raidNormalizarMobId(mob);

    let arquivo =
        RAID_IMAGENS_INVASAO[idBase] ||
        idBase;

    return `https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/mob/combate/invasao/${arquivo}.png?v=2`;
}

function raidImagemFallback(nome = "Inimigo") {
    const texto = encodeURIComponent(String(nome || "Inimigo").slice(0, 18));

    return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(`
        <svg xmlns="http://www.w3.org/2000/svg" width="220" height="220" viewBox="0 0 220 220">
            <rect width="220" height="220" rx="22" fill="#0f172a"/>
            <circle cx="110" cy="82" r="42" fill="#334155"/>
            <path d="M48 182c10-42 36-62 62-62s52 20 62 62" fill="#334155"/>
            <text x="110" y="205" text-anchor="middle" font-size="16" fill="#facc15" font-family="Arial" font-weight="bold">${texto}</text>
            <text x="110" y="92" text-anchor="middle" font-size="42" fill="#94a3b8" font-family="Arial" font-weight="bold">?</text>
        </svg>
    `)}`;
}

function raidNormalizarSkinHeroi(skinBruta) {
    let skin = String(skinBruta || "").trim();

    if (skin.includes("/")) {
        skin = skin.split("/").pop();
    }

    skin = skin.replace(".png", "");

    skin = skin
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/\s+/g, "_")
        .replace("_masculino", "_m")
        .replace("_feminino", "_f");

    if (!skin || skin === "player" || skin === "padrao" || skin === "undefined" || skin === "null") {
        skin = "aventureiro_m";
    }

    return skin;
}

function raidUrlHeroi(jogador = null) {
    const LINK_BASE = "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/classes_costa/";

    const meuId = raidMeuId();
    const jogadorId = String(jogador?.id || jogador?._id || jogador?.char_id || "");

    let skinBruta =
        jogador?.skin ||
        jogador?.skinEquipada ||
        jogador?.skin_equipada ||
        jogador?.sprite ||
        jogador?.classe_skin ||
        "";

    // Se for você e o backend não mandou skin, usa a memória local.
    if (!skinBruta && jogadorId === meuId) {
        skinBruta = localStorage.getItem("skinEquipada") || "";
    }

    const skin = raidNormalizarSkinHeroi(skinBruta);

    return `${LINK_BASE}${skin}.png?v=3`;
}

function raidJogadorVisualAtual() {
    const raid = window.raidInvasaoAtual;
    if (!raid) return null;

    // Durante uma animação, mostra o jogador que acabou de agir.
    const atacanteVisualId = String(window.raidInvasaoAtacanteVisualId || "");
    if (atacanteVisualId && raid.jogadores?.[atacanteVisualId]) {
        return raid.jogadores[atacanteVisualId];
    }

    const ordem = raid.ordem_turnos || [];
    const idx = Number(raid.turno_index || 0);
    const turnoAtual = String(raid.proximo_turno_id || ordem[idx] || "");

    if (turnoAtual && raid.jogadores?.[turnoAtual]) {
        return raid.jogadores[turnoAtual];
    }

    const meuId = raidMeuId();
    if (raid.jogadores?.[meuId]) {
        return raid.jogadores[meuId];
    }

    return Object.values(raid.jogadores || {})[0] || null;
}

function raidAtualizarSprites() {
    const raid = window.raidInvasaoAtual;
    if (!raid) return;

    const spriteHeroi = document.getElementById("raid-sprite-heroi");
    const spriteMob = document.getElementById("raid-sprite-mob");
    const alvoNome = document.getElementById("raid-alvo-nome");

    const jogadorVisual = raidJogadorVisualAtual();

    if (spriteHeroi && jogadorVisual) {
        const novaSrcHeroi = raidUrlHeroi(jogadorVisual);

        if (spriteHeroi.getAttribute("data-src-atual") !== novaSrcHeroi) {
            spriteHeroi.src = novaSrcHeroi;
            spriteHeroi.setAttribute("data-src-atual", novaSrcHeroi);
        }

        spriteHeroi.onerror = function() {
            this.onerror = null;
            this.src = "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/classes_costa/aventureiro_m.png?v=3";
        };

        let nomeHeroiPalco = document.getElementById("raid-heroi-nome");

        if (!nomeHeroiPalco && spriteHeroi.parentElement) {
            nomeHeroiPalco = document.createElement("div");
            nomeHeroiPalco.id = "raid-heroi-nome";
            nomeHeroiPalco.style.cssText = `
                position:absolute;
                left:10px;
                bottom:6px;
                z-index:12;
                max-width:175px;
                background:rgba(2,6,23,.78);
                border:1px solid rgba(56,189,248,.45);
                border-radius:8px;
                padding:4px 7px;
                color:#38bdf8;
                font-size:11px;
                font-weight:900;
                text-align:left;
                white-space:nowrap;
                overflow:hidden;
                text-overflow:ellipsis;
            `;
            spriteHeroi.parentElement.appendChild(nomeHeroiPalco);
        }

        if (nomeHeroiPalco) {
            const nomeHeroi = jogadorVisual.nome || jogadorVisual.character_name || "Herói";
            nomeHeroiPalco.innerText = `⚔️ ${nomeHeroi}`;
        }
    }

    const alvoId = window.raidInvasaoAlvoSelecionado;
    let mobAlvo = null;

    if (
        alvoId &&
        raid.monstros &&
        raid.monstros[alvoId] &&
        Number(raid.monstros[alvoId].hp || 0) > 0
    ) {
        mobAlvo = raid.monstros[alvoId];
    } else {
        mobAlvo = Object.values(raid.monstros || {}).find(m => Number(m.hp || 0) > 0);
        if (mobAlvo) window.raidInvasaoAlvoSelecionado = mobAlvo.id;
    }

    if (spriteMob && mobAlvo) {
        const novaSrc = raidUrlMob(mobAlvo);

        if (spriteMob.src !== novaSrc) {
            spriteMob.src = novaSrc;
        }

        spriteMob.onerror = function() {
            this.onerror = null;
            this.src = raidImagemFallback(mobAlvo?.nome || mobAlvo?.name || "Inimigo");
        };

        spriteMob.style.opacity = Number(mobAlvo.hp || 0) > 0 ? "1" : ".25";
    }

    if (alvoNome && mobAlvo) {
        alvoNome.innerText = mobAlvo.nome || mobAlvo.name || "Inimigo";
    }
}

function raidInfoSkill(skillId) {
    const perfil = window.perfilDadosGlobais || {};
    const dbSkills = perfil.database_skills || perfil.skills_database || {};

    if (!skillId) return {};

    return dbSkills[skillId] || {};
}

function raidDanoDoLog(log) {
    if (log.dano !== undefined && log.dano !== null) {
        return Math.max(0, Number(log.dano) || 0);
    }

    const texto = String(log.texto || "");
    const match = texto.match(/(?:causou|dano|crítico|critico)\D*(\d+)/i);

    return match ? Number(match[1]) : 0;
}

function raidAnimarNumero(alvoId, valor, critico = false) {
    const alvo = document.getElementById(alvoId);
    const container = alvo ? alvo.parentElement : null;

    if (!alvo || !container || !valor) return;

    const num = document.createElement("div");
    num.innerText = valor;
    num.style.cssText = `
        position:absolute;
        z-index:99999;
        pointer-events:none;
        font-family:'Cinzel', Impact, sans-serif;
        font-weight:900;
        font-size:${critico ? "30px" : "23px"};
        color:${critico ? "#facc15" : "#ffffff"};
        text-shadow:2px 2px 0 #000, -2px -2px 0 #000, 0 6px 12px rgba(0,0,0,.9);
    `;

    const a = alvo.getBoundingClientRect();
    const c = container.getBoundingClientRect();

    num.style.left = `${a.left - c.left + a.width / 2}px`;
    num.style.top = `${a.top - c.top + a.height / 2}px`;

    container.appendChild(num);

    num.animate(
        [
            { transform: "translate(-50%, -50%) scale(.4)", opacity: 0 },
            { transform: "translate(-50%, -80%) scale(1.25)", opacity: 1 },
            { transform: "translate(-50%, -155%) scale(1)", opacity: 0 }
        ],
        {
            duration: critico ? 1000 : 850,
            easing: "cubic-bezier(.2,1,.3,1)",
            fill: "forwards"
        }
    );

    setTimeout(() => num.remove(), critico ? 1050 : 900);
}

function raidTremerSprite(alvoId) {
    const el = document.getElementById(alvoId);
    if (!el) return;

    const baseTransform = alvoId === "raid-sprite-mob" ? "scaleX(-1)" : "translate(0,0)";

    el.animate(
        [
            { transform: `${baseTransform} translate(0,0)` },
            { transform: `${baseTransform} translate(-8px,4px)` },
            { transform: `${baseTransform} translate(8px,-4px)` },
            { transform: `${baseTransform} translate(0,0)` }
        ],
        { duration: 280 }
    );

    el.animate(
        [
            { filter: "brightness(1)" },
            { filter: "brightness(2.4) saturate(2)" },
            { filter: "brightness(1)" }
        ],
        { duration: 280 }
    );
}

function raidAnimarInvestida(atacanteId) {
    const el = document.getElementById(atacanteId);
    if (!el) return;

    if (atacanteId === "raid-sprite-heroi") {
        el.animate(
            [
                { transform: "translate(0,0) scale(1)" },
                { transform: "translate(58px,-24px) scale(1.08)" },
                { transform: "translate(0,0) scale(1)" }
            ],
            { duration: 520, easing: "cubic-bezier(.2,1,.3,1)" }
        );
    } else {
        el.animate(
            [
                { transform: "scaleX(-1) translate(0,0)" },
                { transform: "scaleX(-1) translate(48px,-16px)" },
                { transform: "scaleX(-1) translate(0,0)" }
            ],
            { duration: 520, easing: "cubic-bezier(.2,1,.3,1)" }
        );
    }
}

function raidAnimarLogVisual(log, pacoteTurno) {
    const inimigo = !!log.is_inimigo;
    const dano = raidDanoDoLog(log);
    const texto = String(log.texto || "").toLowerCase();
    const critico = texto.includes("crítico") || texto.includes("critico");

    const skillId = log.skill_id || pacoteTurno.skill_id || null;
    const skillInfo = raidInfoSkill(skillId);

    const animEffect =
        log.anim_effect ||
        pacoteTurno.anim_effect ||
        skillInfo.anim_effect ||
        "";

    const tipoSkill =
        log.tipo_skill ||
        pacoteTurno.tipo_skill ||
        skillInfo.type ||
        "";

    if (log.acao === "falha_skill" || tipoSkill === "erro") {
        raidTremerSprite("raid-sprite-heroi");
        return;
    }

    if (inimigo) {
        if (window.AudioManager) {
            window.AudioManager.tocarSFX("som_monstro");
        }

        raidAnimarInvestida("raid-sprite-mob");

        setTimeout(() => {
            raidTremerSprite("raid-sprite-heroi");
            raidAnimarNumero("raid-sprite-heroi", dano ? `-${dano}` : "", false);
        }, 240);

        return;
    }

    if (skillId || log.acao === "magia" || animEffect) {
        if (window.AudioManager) {
            let sfxSkill = "som_magia";

            if (String(animEffect || "").includes("fogo") || String(animEffect || "").includes("bola_de_fogo")) {
                sfxSkill = "som_fogo";
            }

            window.AudioManager.tocarSFX(critico ? "som_critico" : sfxSkill);
        }
        
        const alvoVisual = tipoSkill === "support" ? "raid-sprite-heroi" : "raid-sprite-mob";

        if (animEffect && typeof window.animarMagiaSpriteGrid === "function") {
            window.animarMagiaSpriteGrid(alvoVisual, animEffect);
        } else if (typeof animarEfeitoVisual === "function") {
            animarEfeitoVisual(
                alvoVisual,
                tipoSkill === "support" ? "cura" : "fogo",
                tipoSkill === "support" ? "#22c55e" : "#f97316"
            );
        }

        setTimeout(() => {
            if (alvoVisual === "raid-sprite-mob") {
                raidTremerSprite("raid-sprite-mob");
                raidAnimarNumero("raid-sprite-mob", dano ? `-${dano}` : "", critico);
            }
        }, 300);

        return;
    }
    
    if (window.AudioManager) {
        window.AudioManager.tocarSFX(critico ? "som_critico" : "som_espada");
    }

    raidAnimarInvestida("raid-sprite-heroi");

    setTimeout(() => {
        if (typeof animarEfeitoVisual === "function") {
            animarEfeitoVisual("raid-sprite-mob", "corte", "#ef4444");
        }

        raidTremerSprite("raid-sprite-mob");
        raidAnimarNumero("raid-sprite-mob", dano ? `-${dano}` : "", critico);
    }, 230);
}

function raidFormatarLog(log, pacoteTurno) {
    const autor = raidEscapeHtml(log.autor_nome || log.autor_id || "Sistema");
    const textoOriginal = raidEscapeHtml(log.texto || "");
    const inimigo = !!log.is_inimigo;

    const skillId = log.skill_id || pacoteTurno.skill_id || null;
    const skillInfo = raidInfoSkill(skillId);

    const nomeSkill =
        log.skill_nome ||
        pacoteTurno.skill_nome ||
        skillInfo.display_name ||
        "";

    const dano = raidDanoDoLog(log);

    if (log.acao === "falha_skill" || log.tipo_skill === "erro") {
        return `
            <span style="color:#facc15;font-weight:900;">⚠️ ${autor}</span>
            <span style="color:#e2e8f0;"> ${textoOriginal}</span>
        `;
    }

    if (inimigo) {
        return `
            <span style="color:#f87171;font-weight:900;">👹 ${autor}</span>
            <span style="color:#e2e8f0;"> atacou</span>
            ${dano ? `<span style="color:#facc15;font-weight:900;"> e causou ${dano} de dano</span>` : ""}
        `;
    }

    if (skillId || log.acao === "magia" || log.anim_effect || pacoteTurno.anim_effect) {
        return `
            <span style="color:#93c5fd;font-weight:900;">✨ ${autor}</span>
            <span style="color:#e2e8f0;"> usou </span>
            <span style="color:#c4b5fd;font-weight:900;">${raidEscapeHtml(nomeSkill || "Skill")}</span>
            ${dano ? `<span style="color:#f87171;font-weight:900;"> e causou ${dano} de dano</span>` : ""}
        `;
    }

    return `
        <span style="color:#93c5fd;font-weight:900;">⚔️ ${autor}</span>
        <span style="color:#e2e8f0;"> ${textoOriginal}</span>
    `;
}

function raidRenderizar() {
    const raid = window.raidInvasaoAtual;
    if (!raid) return;

    const metadata = raid.metadata || {};
    const titulo = document.getElementById("raid-invasao-titulo");
    const subtitulo = document.getElementById("raid-invasao-subtitulo");
    const listaHerois = document.getElementById("raid-lista-herois");
    const listaMobs = document.getElementById("raid-lista-mobs");
    const avisoTurno = document.getElementById("raid-aviso-turno");
    const menu = document.getElementById("raid-menu-botoes");

    if (titulo) titulo.innerText = `🛡️ ${metadata.frente_nome || "Frente da Invasão"}`;
    if (subtitulo) subtitulo.innerText = `Onda ${metadata.onda || "?"} — Grupo contra a horda`;

    const ordem = raid.ordem_turnos || [];
    const idx = Number(raid.turno_index || 0);
    const turnoAtual = String(raid.proximo_turno_id || ordem[idx] || "");
    const minhaVez = raidEhMinhaVez();

    if (avisoTurno) {
        if (minhaVez) {
            avisoTurno.innerText = "✅ Sua vez de agir!";
            avisoTurno.style.color = "#22c55e";
            avisoTurno.style.borderColor = "#22c55e";
            avisoTurno.style.boxShadow = "0 0 16px rgba(34,197,94,.25)";
        } else {
            const donoTurno =
                raid.jogadores?.[turnoAtual]?.nome ||
                raid.monstros?.[turnoAtual]?.nome ||
                raid.monstros?.[turnoAtual]?.name ||
                "aliado";

            avisoTurno.innerText = `⏳ Turno de ${donoTurno}`;
            avisoTurno.style.color = "#facc15";
            avisoTurno.style.borderColor = "#facc15";
            avisoTurno.style.boxShadow = "0 0 16px rgba(250,204,21,.20)";
        }
    }

    if (menu) {
        menu.style.display = minhaVez && !window.bloqueioTurnoRaid ? "grid" : "none";
    }

    if (listaHerois) {
        listaHerois.innerHTML = "";

        Object.values(raid.jogadores || {}).forEach(j => {
            const hp = Number(j.hp || 0);
            const maxHp = Number(j.max_hp || 1);
            const mp = Number(j.mp || 0);
            const maxMp = Number(j.max_mp || 1);
            const morto = hp <= 0;
            const ehTurno = String(j.id) === turnoAtual;
            const souEu = String(j.id) === raidMeuId();

            const nome = raidEscapeHtml(j.nome || "Herói");
            const nomeCurto = nome.length > 10 ? nome.slice(0, 10) + "…" : nome;

            const card = document.createElement("div");
            card.className = `raid-card ${ehTurno ? "raid-card-turno" : ""} ${souEu ? "raid-card-eu" : ""}`;
            card.style.opacity = morto ? ".55" : "1";

            card.innerHTML = `
                <div style="display:flex;justify-content:space-between;gap:5px;align-items:center;">
                    <b style="
                        color:${souEu ? "#38bdf8" : "#e2e8f0"};
                        font-size:11px;
                        white-space:nowrap;
                        overflow:hidden;
                        text-overflow:ellipsis;
                    ">
                        ${morto ? "💀" : "🛡️"} ${nomeCurto}
                    </b>
                    <span style="font-size:9px;color:#94a3b8;white-space:nowrap;">
                        ${souEu ? "VOCÊ" : ""} ${ehTurno ? "▶" : ""}
                    </span>
                </div>

                <div class="raid-mini-bar">
                    <div style="height:100%;width:${raidPct(hp, maxHp)}%;background:#22c55e;"></div>
                </div>

                <div class="raid-mini-bar" style="height:5px;">
                    <div style="height:100%;width:${raidPct(mp, maxMp)}%;background:#3b82f6;"></div>
                </div>

                <div style="display:flex;justify-content:space-between;font-size:9px;color:#94a3b8;margin-top:3px;">
                    <span>${Math.floor(hp)}/${maxHp}</span>
                    <span>MP ${Math.floor(mp)}/${maxMp}</span>
                </div>
            `;

            listaHerois.appendChild(card);
        });
    }

    if (listaMobs) {
        listaMobs.innerHTML = "";

        Object.values(raid.monstros || {}).forEach(m => {
            const hp = Number(m.hp || 0);
            const maxHp = Number(m.max_hp || 1);
            const morto = hp <= 0;
            const selecionado = String(window.raidInvasaoAlvoSelecionado || "") === String(m.id);
            const ehTurno = String(m.id) === turnoAtual;

            const nome = raidEscapeHtml(m.nome || m.name || "Monstro");
            const nomeCurto = nome.length > 12 ? nome.slice(0, 12) + "…" : nome;

            const card = document.createElement("button");
            card.disabled = morto;
            card.className = `raid-card ${selecionado ? "raid-card-alvo" : ""} ${ehTurno ? "raid-card-turno" : ""}`;
            card.style.width = "100%";
            card.style.textAlign = "left";
            card.style.color = "#fff";
            card.style.cursor = morto ? "not-allowed" : "pointer";
            card.style.opacity = morto ? ".45" : "1";

            card.onclick = () => {
                if (morto) return;
                window.raidInvasaoAlvoSelecionado = m.id;
                raidAtualizarSprites();
                raidRenderizar();
            };

            card.innerHTML = `
                <div style="display:flex;justify-content:space-between;gap:5px;align-items:center;">
                    <b style="
                        color:${m.is_boss ? "#facc15" : "#fca5a5"};
                        font-size:11px;
                        white-space:nowrap;
                        overflow:hidden;
                        text-overflow:ellipsis;
                    ">
                        ${m.is_boss ? "👑" : "👹"} ${nomeCurto}
                    </b>
                    <span style="font-size:9px;color:${selecionado ? "#facc15" : "#94a3b8"};white-space:nowrap;">
                        ${selecionado ? "ALVO" : ""}
                    </span>
                </div>

                <div class="raid-mini-bar">
                    <div style="height:100%;width:${raidPct(hp, maxHp)}%;background:#ef4444;"></div>
                </div>

                <div style="font-size:9px;color:#94a3b8;margin-top:3px;">
                    HP ${Math.floor(hp)}/${maxHp}
                </div>
            `;

            listaMobs.appendChild(card);
        });
    }

    raidAtualizarSprites();
}

function raidMeuJogadorAtual() {
    const raid = window.raidInvasaoAtual;

    if (!raid || !raid.jogadores) {
        return null;
    }

    const meuId = String(localStorage.getItem("jogadorEldoraID") || "");

    if (raid.jogadores[meuId]) {
        return raid.jogadores[meuId];
    }

    return Object.values(raid.jogadores || {}).find(j => {
        const jid = String(
            j.id ||
            j._id ||
            j.char_id ||
            j.player_id ||
            ""
        );

        return jid === meuId;
    }) || null;
}

function raidManaAtualDoMeuJogador() {
    const meu = raidMeuJogadorAtual();

    if (meu) {
        const mp = (
            meu.mp ??
            meu.current_mp ??
            meu.mana ??
            meu.current_mana ??
            meu.player_mp
        );

        if (mp !== undefined && mp !== null && !Number.isNaN(Number(mp))) {
            return Number(mp);
        }
    }

    if (window.dadosCombateAtual) {
        const mpCombate = window.dadosCombateAtual.playerMpAtual;

        if (mpCombate !== undefined && mpCombate !== null && !Number.isNaN(Number(mpCombate))) {
            return Number(mpCombate);
        }
    }

    if (window.perfilDadosGlobais) {
        const mpPerfil = (
            window.perfilDadosGlobais.current_mp ??
            window.perfilDadosGlobais.mp ??
            window.perfilDadosGlobais.mana
        );

        if (mpPerfil !== undefined && mpPerfil !== null && !Number.isNaN(Number(mpPerfil))) {
            return Number(mpPerfil);
        }
    }

    return 0;
}

window.abrirMenuSkillsRaid = function() {
    const perfil = window.perfilDadosGlobais || {};

    const skillsEquipadas =
        perfil.skills_equipadas ||
        perfil.equipped_skills ||
        {};

    const dbSkills =
        perfil.database_skills ||
        perfil.skills_database ||
        {};

    const cooldowns = perfil.cooldowns || {};

    let modal = document.getElementById("modal-skills-raid");

    if (!modal) {
        modal = document.createElement("div");
        modal.id = "modal-skills-raid";
        modal.style.cssText = `
            position:fixed;
            inset:0;
            z-index:1000001;
            background:rgba(2,6,23,.78);
            backdrop-filter:blur(5px);
            display:flex;
            align-items:center;
            justify-content:center;
            padding:12px;
            box-sizing:border-box;
        `;

        document.body.appendChild(modal);
    }

    const raid = window.raidInvasaoAtual;

    if (!raid) return;

    const meu = raidMeuJogadorAtual();
    const manaAtual = raidManaAtualDoMeuJogador();

    console.log("🧙 [RAID SKILL MENU] Mana detectada:", {
        meu_id: raidMeuId(),
        jogador: meu,
        manaAtual
    });

    let htmlSkills = "";

    [1, 2, 3, 4, 5].forEach(slot => {
        const skillId = skillsEquipadas[`slot_${slot}`];

        if (!skillId) return;

        const info = dbSkills[skillId] || {};
        const nome = info.display_name || info.name || skillId.replace(/_/g, " ");
        const icone = info.icon || "default_skill";

        let custoMana = Number(info.mana_cost || info.mp_cost || 0);

        if (info.rarity_effects && info.rarity_effects.comum) {
            custoMana = Number(
                info.rarity_effects.comum.mana_cost ||
                info.rarity_effects.comum.mp_cost ||
                custoMana
            );
        }

        const cd = Number(cooldowns[skillId] || 0);
        const semMana = Number(manaAtual) < Number(custoMana);
        const travada = cd > 0 || semMana;

        const motivo = cd > 0 ? `⏳ ${cd}` : semMana ? `Falta MP (${manaAtual}/${custoMana})` : "USAR";
        const img = `https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/sprites/skills/${icone}.png`;

        htmlSkills += `
            <button
                ${travada ? "disabled" : ""}
                onclick="usarSkillRaid('${skillId.replace(/'/g, "\\'")}')"
                style="
                    background:${travada ? "rgba(30,41,59,.55)" : "rgba(30,41,59,.95)"};
                    border:1px solid ${travada ? "#ef4444" : "#8b5cf6"};
                    border-radius:10px;
                    padding:8px;
                    color:#fff;
                    cursor:${travada ? "not-allowed" : "pointer"};
                    opacity:${travada ? ".55" : "1"};
                    display:flex;
                    flex-direction:column;
                    align-items:center;
                    gap:5px;
                    min-height:94px;
                "
            >
                <img src="${img}" onerror="this.src='https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/sprites/skills/default_skill.png'" style="
                    width:42px;
                    height:42px;
                    border-radius:7px;
                    object-fit:cover;
                    background:#020617;
                ">
                <b style="font-size:10px;line-height:1.1;text-align:center;color:#e2e8f0;">
                    ${raidEscapeHtml(nome)}
                </b>
                <span style="font-size:10px;color:${semMana ? "#ef4444" : "#60a5fa"};">
                    💧${custoMana} — ${motivo}
                </span>
            </button>
        `;
    });

    if (!htmlSkills) {
        htmlSkills = `
            <div style="grid-column:1/-1;color:#94a3b8;text-align:center;padding:16px;">
                Nenhuma skill equipada.
            </div>
        `;
    }

    modal.innerHTML = `
        <div style="
            width:min(92vw,360px);
            background:linear-gradient(180deg, rgba(15,23,42,.98), rgba(2,6,23,.98));
            border:1px solid #8b5cf6;
            border-top:3px solid #facc15;
            border-radius:14px;
            padding:14px;
            box-shadow:0 18px 45px rgba(0,0,0,.85);
            color:#fff;
        ">
            <div style="
                font-family:'Cinzel',serif;
                color:#facc15;
                font-weight:900;
                text-align:center;
                margin-bottom:10px;
            ">
                ✨ Escolha uma Skill
            </div>

            <div style="
                display:grid;
                grid-template-columns:repeat(2, minmax(0, 1fr));
                gap:8px;
                max-height:58vh;
                overflow-y:auto;
            ">
                ${htmlSkills}
            </div>

            <button onclick="fecharMenuSkillsRaid()" style="
                margin-top:12px;
                width:100%;
                background:transparent;
                color:#94a3b8;
                border:1px solid #475569;
                border-radius:9px;
                padding:9px;
                font-weight:900;
                cursor:pointer;
            ">Fechar</button>
        </div>
    `;

    modal.style.display = "flex";
};

window.fecharMenuSkillsRaid = function() {
    const modal = document.getElementById("modal-skills-raid");
    if (modal) modal.style.display = "none";
};

window.usarSkillRaid = function(skillId) {
    fecharMenuSkillsRaid();
    executarAcaoRaid("magia", skillId);
};

window.iniciarInterfaceRaid = async function(estadoRaid) {
    window.raidInvasaoAtual = estadoRaid;
    window.raidInvasaoAlvoSelecionado = null;
    window.bloqueioTurnoRaid = false;

    try {
        const charId = localStorage.getItem("jogadorEldoraID");

        if (charId) {
            const resPerfil = await fetch(
                `/api/personagem/${charId}?t=${Date.now()}`,
                {
                    cache: "no-store"
                }
            );

            const perfilRaid =
                await resPerfil.json();

            const perfilAnterior =
                window.perfilDadosGlobais || {};

            window.perfilDadosGlobais = {
                ...perfilAnterior,
                ...perfilRaid,

                quests: {
                    ...(perfilAnterior.quests || {}),
                    ...(perfilRaid.quests || {})
                }
            };

            console.log("🧙 Perfil carregado para Raid:", {
                skills_equipadas: window.perfilDadosGlobais.skills_equipadas,
                skills_desbloqueadas: window.perfilDadosGlobais.skills_desbloqueadas
            });
        }
    } catch (e) {
        console.warn("Não foi possível carregar perfil antes da raid:", e);
    }

    const tela = raidCriarTelaSeNaoExiste();

    if (typeof ocultarUiMapaDuranteCombate === "function") {
        ocultarUiMapaDuranteCombate();
    }

    if (typeof travarMapaDuranteCombate === "function") {
        travarMapaDuranteCombate(true);
    }

    document.body.classList.add("combate-aberto");

    tela.style.display = "block";
    
    if (window.AudioManager) {
        window.AudioManager.tocarMusica("bgm_batalha");
    }
    const log = document.getElementById("raid-log");
    if (log) log.innerHTML = "";

    raidAdicionarLog(`<span style="color:#facc15;font-weight:bold;">⚔️ A raid da invasão começou!</span>`);
    raidRenderizar();
};

window.executarAcaoRaid = function(acao, skillId = null) {
    const raid = window.raidInvasaoAtual;

    if (!raid || window.bloqueioTurnoRaid) return;

    if (!raidEhMinhaVez()) {
        raidAdicionarLog(`<span style="color:#94a3b8;">⏳ Ainda não é sua vez.</span>`);
        raidRenderizar();
        return;
    }

    let alvoId = window.raidInvasaoAlvoSelecionado;

    if (!alvoId || !raid.monstros?.[alvoId] || Number(raid.monstros[alvoId].hp || 0) <= 0) {
        const alvo = Object.values(raid.monstros || {}).find(m => Number(m.hp || 0) > 0);
        alvoId = alvo ? alvo.id : null;
        window.raidInvasaoAlvoSelecionado = alvoId;
    }

    if (!alvoId) {
        raidAdicionarLog(`<span style="color:#ef4444;">Nenhum inimigo vivo para atacar.</span>`);
        return;
    }

    window.bloqueioTurnoRaid = true;
    raidRenderizar();

    if (!window.eldoraSocket) {
        window.avisoEldora("Erro: socket da raid não encontrado.");
        window.bloqueioTurnoRaid = false;
        raidRenderizar();
        return;
    }

    raidAdicionarLog(`<span style="color:#60a5fa;">Enviando ação...</span>`);

    window.eldoraSocket.emit("enviarAcaoRaid", {
        raid_id: raid.raid_id,
        acao: acao,
        alvo_id: alvoId,
        skill_id: skillId
    });
};

window.processarAnimacaoTurnoRaid = function(pacoteTurno) {
    const raid = window.raidInvasaoAtual;
    if (!raid || !pacoteTurno) return;
        // 🔒 Anti-duplicação: evita o mesmo pacote da raid ser processado 2x
    const assinaturaPacote = JSON.stringify({
        raid_id: raid.raid_id,
        atacante_id: pacoteTurno.atacante_id || "",
        proximo_turno_id: pacoteTurno.proximo_turno_id || "",
        raid_encerrada: !!pacoteTurno.raid_encerrada,
        resultado: pacoteTurno.resultado || "",
        logs: (pacoteTurno.log || []).map(l => ({
            autor: l.autor_id || l.autor_nome || "",
            texto: l.texto || "",
            alvo: l.alvo_id || "",
            hp: l.novo_hp ?? "",
            dano: l.dano ?? ""
        }))
    });

    const agora = Date.now();

    if (
        window.__ultimaAssinaturaPacoteRaid === assinaturaPacote &&
        agora - (window.__ultimoPacoteRaidMs || 0) < 1500
    ) {
        console.warn("⚠️ Pacote duplicado da raid ignorado.");
        return;
    }

    window.__ultimaAssinaturaPacoteRaid = assinaturaPacote;
    window.__ultimoPacoteRaidMs = agora;
    
    // Remove mensagens temporárias antigas tipo "Enviando ação..."
    const logBox = document.getElementById("raid-log");
    if (logBox) {
        [...logBox.querySelectorAll(".raid-log-line")].forEach(linha => {
            if ((linha.innerText || "").includes("Enviando ação")) {
                linha.remove();
            }
        });
    }

    if (pacoteTurno.atacante_id && raid.jogadores?.[pacoteTurno.atacante_id]) {
        if (pacoteTurno.novo_mp !== undefined) {
            raid.jogadores[pacoteTurno.atacante_id].mp = pacoteTurno.novo_mp;
        }
    }

    if (
        pacoteTurno.atacante_id &&
        String(pacoteTurno.atacante_id) === raidMeuId() &&
        pacoteTurno.cooldowns !== undefined &&
        window.perfilDadosGlobais
    ) {
        window.perfilDadosGlobais.cooldowns = pacoteTurno.cooldowns;
    }

    const logs = Array.isArray(pacoteTurno.log) ? pacoteTurno.log : [];

    // ✅ Todos os jogadores veem no palco quem acabou de agir.
    if (pacoteTurno.atacante_id && raid.jogadores?.[String(pacoteTurno.atacante_id)]) {
        window.raidInvasaoAtacanteVisualId = String(pacoteTurno.atacante_id);
    }

    // ✅ Todos os jogadores veem no palco qual mob foi atacado.
    const logComAlvo = logs.find(l =>
        l &&
        l.alvo_id &&
        raid.monstros?.[String(l.alvo_id)]
    );

    if (logComAlvo) {
        window.raidInvasaoAlvoSelecionado = String(logComAlvo.alvo_id);
    }

    raidAtualizarSprites();
    raidRenderizar();

    if (!logs.length) {
        window.bloqueioTurnoRaid = false;
        window.raidInvasaoAtacanteVisualId = null;
        raidRenderizar();
        return;
    }

    logs.forEach((log, index) => {
        setTimeout(() => {
            raidAdicionarLog(raidFormatarLog(log, pacoteTurno));
            raidAnimarLogVisual(log, pacoteTurno);

            if (log.alvo_id && log.novo_hp !== undefined) {
                const alvoId = String(log.alvo_id);
                const novoHp = Math.max(0, Number(log.novo_hp || 0));

                if (raid.jogadores && raid.jogadores[alvoId]) {
                    raid.jogadores[alvoId].hp = novoHp;
                }

                if (raid.monstros && raid.monstros[alvoId]) {
                    raid.monstros[alvoId].hp = novoHp;
                }

                raidRenderizar();
            }
        }, index * 430);
    });

    const tempoFinal = Math.max(450, logs.length * 430 + 220);

    setTimeout(() => {
        if (pacoteTurno.proximo_turno_id) {
            raid.proximo_turno_id = String(pacoteTurno.proximo_turno_id);

            if (Array.isArray(raid.ordem_turnos)) {
                const idx = raid.ordem_turnos.findIndex(
                    id => String(id) === String(pacoteTurno.proximo_turno_id)
                );

                if (idx >= 0) raid.turno_index = idx;
            }
        }

        window.bloqueioTurnoRaid = false;
        window.raidInvasaoAtacanteVisualId = null;

        if (pacoteTurno.raid_encerrada) {
            const venceu =
                pacoteTurno.resultado === "vitoria" ||
                logs.some(l => String(l.texto || "").includes("DEFENDIDA"));
            
            if (window.AudioManager) {
                if (venceu) {
                    window.AudioManager.tocarSFX("som_vitoria");
                } else {
                    window.AudioManager.tocarSFX("som_monstro");
                }
            }

            const menu = document.getElementById("raid-menu-botoes");
            const fim = document.getElementById("raid-botoes-fim");

            if (menu) menu.style.display = "none";
            if (fim) fim.style.display = "block";

            raidAdicionarLog(
                venceu
                    ? `<div style="color:#22c55e;font-weight:900;font-size:15px;text-align:center;margin-top:8px;">🏆 FRENTE DEFENDIDA!</div>`
                    : `<div style="color:#ef4444;font-weight:900;font-size:15px;text-align:center;margin-top:8px;">💀 FRENTE PERDIDA!</div>`
            );
            
            if (pacoteTurno.recompensas) {
                const r = pacoteTurno.recompensas;

                const partes = [];

                if (r.gold || r.ouro) partes.push(`💰 ${r.gold || r.ouro} Ouro`);
                if (r.xp) partes.push(`🌟 ${r.xp} XP`);
                if (r.xp_passe) partes.push(`🎫 ${r.xp_passe} XP Passe`);
                if (r.fragmentos) partes.push(`🏅 ${r.fragmentos} Fragmentos`);

                if (Array.isArray(r.itens) && r.itens.length) {
                    partes.push(`📦 ${r.itens.join(", ")}`);
                }

                if (partes.length) {
                    const textoRecompensa = partes.join(" | ");

                    raidAdicionarLog(`
                        <div style="
                            color:#facc15;
                            font-weight:900;
                            background:rgba(202,138,4,.10);
                            border:1px solid rgba(250,204,21,.35);
                            border-radius:8px;
                            padding:7px;
                            text-align:center;
                            margin-top:6px;
                        ">
                            🎁 Recompensas: ${textoRecompensa}
                        </div>
                    `);

                    if (typeof window.mostrarNotificacaoRPG === "function") {
                        window.mostrarNotificacaoRPG(`Recompensas: ${textoRecompensa}`, "🎁");
                    }

                    if (typeof window.alertaEldora === "function") {
                        window.alertaEldora("Recompensa da Invasão", textoRecompensa, "sucesso");
                    }
                }
            }

            const aviso = document.getElementById("raid-aviso-turno");

            if (aviso) {
                aviso.innerText = venceu ? "🏆 Vitória!" : "💀 Derrota!";
                aviso.style.color = venceu ? "#22c55e" : "#ef4444";
                aviso.style.borderColor = venceu ? "#22c55e" : "#ef4444";
            }

            raidRenderizar();
            return;
        }

        raidRenderizar();
    }, tempoFinal);
};

window.sairDaRaidInvasao = function() {
    const tela = document.getElementById("tela-raid-invasao");
    if (tela) tela.style.display = "none";

    window.raidInvasaoAtual = null;
    window.raidInvasaoAlvoSelecionado = null;
    window.bloqueioTurnoRaid = false;

    if (typeof restaurarUiMapaDepoisCombate === "function") {
        restaurarUiMapaDepoisCombate();
    }

    if (typeof travarMapaDuranteCombate === "function") {
        travarMapaDuranteCombate(false);
    }

    document.body.classList.remove("combate-aberto");
    
    if (window.AudioManager) {
        window.AudioManager.pararMusica();

        const regAtual =
            localStorage.getItem("eldora_lastRegiao") ||
            localStorage.getItem("regiaoAtual") ||
            "capital_eldora";

        if (regAtual === "capital_eldora") {
            window.AudioManager.tocarMusica("bgm_capital");
        } else if (regAtual === "pradaria_inicial") {
            window.AudioManager.tocarMusica("bgm_pradaria");
        } else if (regAtual === "floresta_sombria") {
            window.AudioManager.tocarMusica("bgm_floresta");
        }
    }
    if (typeof carregarMeuPerfil === "function") {
        carregarMeuPerfil();
    }
};

// =====================================================
// 🛡️ RAID DA INVASÃO — UI MÍNIMA FUNCIONAL
// =====================================================
if (typeof window.iniciarInterfaceRaid !== "function") {
    window.raidInvasaoAtual = null;
    window.raidInvasaoAlvoSelecionado = null;
    window.bloqueioTurnoRaid = false;

    function raidMeuId() {
        return String(localStorage.getItem("jogadorEldoraID") || "");
    }

    function raidEscape(txt) {
        return String(txt ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    }

    function raidPct(a, b) {
        a = Number(a || 0);
        b = Number(b || 1);
        return Math.max(0, Math.min(100, b > 0 ? (a / b) * 100 : 0));
    }

    function raidTurnoId() {
        const raid = window.raidInvasaoAtual;
        if (!raid) return "";

        if (raid.proximo_turno_id) return String(raid.proximo_turno_id);

        const ordem = raid.ordem_turnos || [];
        const idx = Number(raid.turno_index || 0);

        return String(ordem[idx] || "");
    }

    function raidMinhaVez() {
        return raidTurnoId() === raidMeuId();
    }

    function raidTela() {
        let tela = document.getElementById("tela-raid-invasao");

        if (tela) return tela;

        tela = document.createElement("div");
        tela.id = "tela-raid-invasao";
        tela.style.cssText = `
            display:none;
            position:fixed;
            inset:0;
            z-index:999999;
            background:rgba(2,6,23,.96);
            color:#fff;
            font-family:Arial,sans-serif;
        `;

        tela.innerHTML = `
            <div style="
                width:min(100vw,430px);
                height:100vh;
                margin:0 auto;
                background:#020617;
                display:flex;
                flex-direction:column;
                border-left:1px solid #334155;
                border-right:1px solid #334155;
            ">
                <div style="
                    padding:9px;
                    background:linear-gradient(90deg,#450a0a,#0f172a);
                    border-bottom:1px solid #ca8a04;
                    display:flex;
                    justify-content:space-between;
                    align-items:center;
                ">
                    <div>
                        <div id="raid-titulo" style="color:#facc15;font-weight:900;font-family:Cinzel,serif;">
                            🛡️ INVASÃO
                        </div>
                        <div id="raid-turno" style="font-size:12px;color:#cbd5e1;">
                            Aguardando...
                        </div>
                    </div>

                    <button onclick="sairDaRaidInvasao()" style="
                        background:#1e293b;
                        color:#fff;
                        border:1px solid #64748b;
                        border-radius:8px;
                        padding:7px 10px;
                        font-weight:900;
                    ">SAIR</button>
                </div>

                <div style="
                    margin:8px;
                    padding:8px;
                    border:1px solid #334155;
                    border-radius:10px;
                    background:rgba(15,23,42,.75);
                ">
                    <div style="color:#f87171;font-weight:900;margin-bottom:6px;">
                        👹 Inimigos
                    </div>
                    <div id="raid-lista-mobs" style="display:flex;flex-direction:column;gap:6px;"></div>
                </div>

                <div id="raid-log" style="
                    flex:1;
                    margin:0 8px 8px;
                    padding:8px;
                    overflow-y:auto;
                    border:1px solid #334155;
                    border-radius:10px;
                    background:#020617;
                    font-size:12px;
                    line-height:1.4;
                "></div>

                <div id="raid-menu-botoes" style="
                    display:grid;
                    grid-template-columns:1fr 1fr;
                    gap:8px;
                    padding:8px;
                ">
                    <button onclick="executarAcaoRaid('atacar')" style="
                        background:#1e293b;
                        border:1px solid #ef4444;
                        color:#fff;
                        border-radius:10px;
                        padding:10px;
                        font-weight:900;
                    ">⚔️ ATACAR</button>

                    <button onclick="abrirMenuSkillsRaid()" style="
                        background:#1e293b;
                        border:1px solid #8b5cf6;
                        color:#fff;
                        border-radius:10px;
                        padding:10px;
                        font-weight:900;
                    ">✨ SKILL</button>
                </div>

                <div id="raid-botoes-fim" style="display:none;padding:8px;">
                    <button onclick="sairDaRaidInvasao()" style="
                        width:100%;
                        background:#1e293b;
                        border:1px solid #22c55e;
                        color:#fff;
                        border-radius:10px;
                        padding:10px;
                        font-weight:900;
                    ">⬅️ VOLTAR AO MAPA</button>
                </div>
            </div>
        `;

        document.body.appendChild(tela);
        return tela;
    }

    function raidAdicionarLog(html) {
        const box = document.getElementById("raid-log");
        if (!box) return;

        const linha = document.createElement("div");
        linha.className = "raid-log-line";
        linha.style.cssText = "padding:4px 2px;border-bottom:1px solid rgba(148,163,184,.12);";
        linha.innerHTML = html;

        box.appendChild(linha);
        box.scrollTop = box.scrollHeight;
    }

    window.raidAdicionarLog = raidAdicionarLog;

    function raidRenderizar() {
        const raid = window.raidInvasaoAtual;
        if (!raid) return;

        const lista = document.getElementById("raid-lista-mobs");
        const turno = document.getElementById("raid-turno");
        const titulo = document.getElementById("raid-titulo");
        const menu = document.getElementById("raid-menu-botoes");

        const meta = raid.metadata || {};
        const turnoId = raidTurnoId();

        if (titulo) {
            titulo.innerText = `🛡️ ${meta.frente_nome || "INVASÃO"}`;
        }

        if (turno) {
            turno.innerText = raidMinhaVez() ? "✅ Sua vez!" : "⏳ Aguarde o turno...";
            turno.style.color = raidMinhaVez() ? "#22c55e" : "#cbd5e1";
        }

        if (menu) {
            menu.style.display = raidMinhaVez() && !window.bloqueioTurnoRaid ? "grid" : "none";
        }

        if (!lista) return;

        lista.innerHTML = "";

        Object.values(raid.monstros || {}).forEach(m => {
            const hp = Number(m.hp || 0);
            const maxHp = Number(m.max_hp || 1);
            const selecionado = String(window.raidInvasaoAlvoSelecionado || "") === String(m.id);

            const btn = document.createElement("button");
            btn.disabled = hp <= 0;
            btn.onclick = () => {
                if (hp <= 0) return;
                window.raidInvasaoAlvoSelecionado = m.id;
                raidRenderizar();
            };

            btn.style.cssText = `
                width:100%;
                background:${selecionado ? "rgba(127,29,29,.95)" : "rgba(15,23,42,.95)"};
                border:1px solid ${selecionado ? "#facc15" : "#334155"};
                border-radius:8px;
                padding:7px;
                color:#fff;
                text-align:left;
                opacity:${hp <= 0 ? ".45" : "1"};
            `;

            btn.innerHTML = `
                <div style="display:flex;justify-content:space-between;font-weight:900;font-size:12px;">
                    <span>${m.is_boss ? "👑" : "👹"} ${raidEscape(m.nome || m.name || "Monstro")}</span>
                    <span style="color:#facc15;">${selecionado ? "ALVO" : ""}</span>
                </div>
                <div style="height:7px;background:#020617;border-radius:999px;overflow:hidden;margin-top:5px;">
                    <div style="height:100%;width:${raidPct(hp, maxHp)}%;background:#ef4444;"></div>
                </div>
                <div style="font-size:10px;color:#cbd5e1;margin-top:2px;">HP ${hp}/${maxHp}</div>
            `;

            lista.appendChild(btn);
        });
    }

    window.iniciarInterfaceRaid = async function(estadoRaid) {
        window.raidInvasaoAtual = estadoRaid;
        window.raidInvasaoAlvoSelecionado = null;
        window.bloqueioTurnoRaid = false;

        const primeiroMob = Object.values(estadoRaid.monstros || {}).find(m => Number(m.hp || 0) > 0);
        if (primeiroMob) window.raidInvasaoAlvoSelecionado = primeiroMob.id;

        try {
            const charId = localStorage.getItem("jogadorEldoraID");

            if (charId) {
                const res = await fetch(`/api/personagem/${charId}?t=${Date.now()}`, { cache: "no-store" });
                window.perfilDadosGlobais = await res.json();
            }
        } catch (e) {
            console.warn("Não carregou perfil antes da raid:", e);
        }

        const tela = raidTela();

        if (typeof ocultarUiMapaDuranteCombate === "function") ocultarUiMapaDuranteCombate();
        if (typeof travarMapaDuranteCombate === "function") travarMapaDuranteCombate(true);

        document.body.classList.add("combate-aberto");
        tela.style.display = "block";

        if (window.AudioManager) {
            window.AudioManager.tocarMusica("bgm_batalha");
        }

        const log = document.getElementById("raid-log");
        if (log) log.innerHTML = "";

        raidAdicionarLog(`<span style="color:#facc15;font-weight:900;">⚔️ A defesa da invasão começou!</span>`);
        raidRenderizar();
    };

    window.executarAcaoRaid = function(acao, skillId = null) {
        const raid = window.raidInvasaoAtual;
        if (!raid || window.bloqueioTurnoRaid) return;

        if (!raidMinhaVez()) {
            raidAdicionarLog(`<span style="color:#94a3b8;">⏳ Ainda não é sua vez.</span>`);
            return;
        }

        let alvoId = window.raidInvasaoAlvoSelecionado;

        if (!alvoId || !raid.monstros?.[alvoId] || Number(raid.monstros[alvoId].hp || 0) <= 0) {
            const alvo = Object.values(raid.monstros || {}).find(m => Number(m.hp || 0) > 0);
            alvoId = alvo ? alvo.id : null;
            window.raidInvasaoAlvoSelecionado = alvoId;
        }

        if (!alvoId) {
            raidAdicionarLog(`<span style="color:#ef4444;">Nenhum inimigo vivo.</span>`);
            return;
        }

        window.bloqueioTurnoRaid = true;
        raidRenderizar();

        window.eldoraSocket.emit("enviarAcaoRaid", {
            raid_id: raid.raid_id,
            acao,
            alvo_id: alvoId,
            skill_id: skillId
        });
    };

    window.processarAnimacaoTurnoRaid = function(pacoteTurno) {
        const raid = window.raidInvasaoAtual;
        if (!raid || !pacoteTurno) return;

        const logs = Array.isArray(pacoteTurno.log) ? pacoteTurno.log : [];

        logs.forEach(log => {
            const inimigo = !!log.is_inimigo;
            const autor = raidEscape(log.autor_nome || log.autor_id || "Sistema");
            const texto = raidEscape(log.texto || "");

            raidAdicionarLog(`
                <span style="color:${inimigo ? "#f87171" : "#93c5fd"};font-weight:900;">
                    ${inimigo ? "👹" : "⚔️"} ${autor}
                </span>
                <span>${texto}</span>
            `);

            if (log.alvo_id && log.novo_hp !== undefined) {
                const alvoId = String(log.alvo_id);
                const novoHp = Math.max(0, Number(log.novo_hp || 0));

                if (raid.jogadores?.[alvoId]) raid.jogadores[alvoId].hp = novoHp;
                if (raid.monstros?.[alvoId]) raid.monstros[alvoId].hp = novoHp;
            }
        });

        if (pacoteTurno.atacante_id && raid.jogadores?.[pacoteTurno.atacante_id]) {
            if (pacoteTurno.novo_mp !== undefined) {
                raid.jogadores[pacoteTurno.atacante_id].mp = pacoteTurno.novo_mp;
            }
        }

        if (pacoteTurno.proximo_turno_id) {
            raid.proximo_turno_id = String(pacoteTurno.proximo_turno_id);

            if (Array.isArray(raid.ordem_turnos)) {
                const idx = raid.ordem_turnos.findIndex(id => String(id) === String(pacoteTurno.proximo_turno_id));
                if (idx >= 0) raid.turno_index = idx;
            }
        }

        window.bloqueioTurnoRaid = false;

        if (pacoteTurno.raid_encerrada) {
            const venceu = pacoteTurno.resultado === "vitoria";

            const menu = document.getElementById("raid-menu-botoes");
            const fim = document.getElementById("raid-botoes-fim");

            if (menu) menu.style.display = "none";
            if (fim) fim.style.display = "block";

            raidAdicionarLog(
                venceu
                    ? `<div style="color:#22c55e;font-weight:900;text-align:center;margin-top:8px;">🏆 FRENTE DEFENDIDA!</div>`
                    : `<div style="color:#ef4444;font-weight:900;text-align:center;margin-top:8px;">💀 FRENTE PERDIDA!</div>`
            );

            if (window.AudioManager) {
                window.AudioManager.tocarSFX(venceu ? "som_vitoria" : "som_monstro");
            }
        }

        raidRenderizar();
    };

    window.sairDaRaidInvasao = function() {
        const tela = document.getElementById("tela-raid-invasao");
        if (tela) tela.style.display = "none";

        window.raidInvasaoAtual = null;
        window.raidInvasaoAlvoSelecionado = null;
        window.bloqueioTurnoRaid = false;

        if (typeof restaurarUiMapaDepoisCombate === "function") restaurarUiMapaDepoisCombate();
        if (typeof travarMapaDuranteCombate === "function") travarMapaDuranteCombate(false);

        document.body.classList.remove("combate-aberto");

        if (window.AudioManager) {
            window.AudioManager.pararMusica();
            window.AudioManager.tocarMusica("bgm_capital");
        }
    };

    window.abrirMenuSkillsRaid = function() {
        const p = window.perfilDadosGlobais || {};
        const skillsEquipadas = p.skills_equipadas || p.equipped_skills || {};
        const dbSkills = p.database_skills || p.skills_database || {};
        const cooldowns = p.cooldowns || {};

        let menu = document.getElementById("menu-skills-raid");

        if (!menu) {
            menu = document.createElement("div");
            menu.id = "menu-skills-raid";
            menu.style.cssText = `
                position:fixed;
                inset:0;
                z-index:1000000;
                background:rgba(2,6,23,.75);
                display:flex;
                align-items:center;
                justify-content:center;
            `;
            document.body.appendChild(menu);
        }

        let html = `
            <div style="
                width:min(92vw,340px);
                background:#0f172a;
                border:1px solid #8b5cf6;
                border-radius:12px;
                padding:14px;
                color:#fff;
            ">
                <div style="color:#facc15;font-weight:900;text-align:center;margin-bottom:10px;">
                    ✨ SKILLS
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
        `;

        let encontrou = false;

        Object.values(skillsEquipadas).forEach(skillId => {
            if (!skillId) return;

            encontrou = true;

            const info = dbSkills[skillId] || {};
            const nome = info.display_name || String(skillId).replace(/_/g, " ");
            const cd = Number(cooldowns[skillId] || 0);
            const bloqueado = cd > 0;

            html += `
                <button ${bloqueado ? "" : `onclick="usarSkillRaid('${skillId}')"`} style="
                    border:1px solid ${bloqueado ? "#ef4444" : "#8b5cf6"};
                    background:#1e293b;
                    color:#fff;
                    border-radius:9px;
                    padding:8px;
                    font-weight:900;
                    opacity:${bloqueado ? ".55" : "1"};
                ">
                    ${raidEscape(nome)}
                    ${bloqueado ? `<br><span style="color:#ef4444;">CD ${cd}</span>` : ""}
                </button>
            `;
        });

        if (!encontrou) {
            html += `<div style="grid-column:1/-1;color:#94a3b8;text-align:center;">Nenhuma skill equipada.</div>`;
        }

        html += `
                </div>
                <button onclick="fecharMenuSkillsRaid()" style="
                    margin-top:10px;
                    width:100%;
                    border:1px solid #475569;
                    background:transparent;
                    color:#cbd5e1;
                    border-radius:8px;
                    padding:8px;
                    font-weight:900;
                ">Fechar</button>
            </div>
        `;

        menu.innerHTML = html;
        menu.style.display = "flex";
    };

    window.fecharMenuSkillsRaid = function() {
        const menu = document.getElementById("menu-skills-raid");
        if (menu) menu.style.display = "none";
    };

    window.usarSkillRaid = function(skillId) {
        fecharMenuSkillsRaid();
        executarAcaoRaid("magia", skillId);
    };
}