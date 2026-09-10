// ============================================================
// 🌀 PORTAL MANAGER - MUNDO DE ELDORA
// ============================================================
// Responsável pelos portais colocados no Tiled.
// Neste primeiro estágio:
// - encontra a camada "Portais"
// - lê posição e tamanho
// - cria o sprite HD
// - executa a animação
// ============================================================

class PortalManager {

    constructor(scene, map) {

        this.scene = scene;
        this.map = map;

        this.portais = [];

        // Portal que o jogador clicou de longe.
        // Quando chegar perto, a interação continua automaticamente.
        this.portalPendente = null;


        // ============================================================
        // 🌍 REGIÕES DO SISTEMA DE PORTAIS
        // ============================================================

        this.regioesPortal = {

            capital_eldora: {
                nome: 'Capital de Eldora',
                icone: '🏰',
                descricao: 'Coração do Reino'
            },

            pradaria_inicial: {
                nome: 'Pradaria Inicial',
                icone: '🌿',
                descricao: 'Campos verdes de Eldora'
            },

            floresta_sombria: {
                nome: 'Floresta Sombria',
                icone: '🌲',
                descricao: 'Terras tomadas pelas sombras'
            },

            pedreira_granito: {
                nome: 'Pedreira de Granito',
                icone: '⛏️',
                descricao: 'Minas e rochas ancestrais'
            }

        };


        // Menu aberto atualmente
        this.menuPortal = null;


        // ============================================================
        // 🎟️ PASSE DE VIAGEM
        // ============================================================
        // false = liberado durante nossos testes
        // true  = futuramente exige o Passe
        // ============================================================

        this.EXIGIR_PASSE_PORTAL = false;


        this.criarAnimacao();
        this.carregarPortaisDoTiled();

        // ==========================================
        // 🎭 PROFUNDIDADE DINÂMICA DOS PORTAIS
        // ==========================================
        this.scene.events.on(
            'update',
            this.atualizarProfundidade,
            this
        );

        // Evita duplicar o evento quando troca de mapa
        this.scene.events.once('shutdown', () => {

            this.scene.events.off(
                'update',
                this.atualizarProfundidade,
                this
            );

        });

    }
    // ============================================================
    // 🎭 PROFUNDIDADE DINÂMICA
    // ============================================================

    atualizarProfundidade() {

        const player = this.scene.player;

        if (!player) {
            return;
        }

        this.portais.forEach(item => {
 
            const portal = item.sprite;

            if (!portal) {
                return;
            }


            // Linha imaginária próxima à parte superior
            // da base de pedra do portal.
            // Linha localizada aproximadamente no começo
            // da plataforma de pedra.
            //
            // Jogador acima desta linha:
            // fica ATRÁS do portal.
            //
            // Jogador abaixo desta linha:
            // fica NA FRENTE do portal.
            const linhaProfundidade =
                portal.y -
                (portal.displayHeight * 0.32);

            // ==========================================
            // 👤 JOGADOR ESTÁ ATRÁS DO PORTAL
            // ==========================================

           if (player.y < linhaProfundidade) {

            portal.setDepth(16);

            }

            // ==========================================
            // 👤 JOGADOR ESTÁ NA FRENTE DO PORTAL
            // ==========================================

            else {

                portal.setDepth(10);

            }

        });

        // ============================================================
        // 🚶 JOGADOR ESTÁ INDO ATÉ UM PORTAL
        // ============================================================

        if (this.portalPendente) {

            const item =
                this.portalPendente;

            const portal =
                item.sprite;


            const portalX =
                portal.x +
                (portal.displayWidth / 2);

            const portalY =
                portal.y - 20;


            const distancia =
                Phaser.Math.Distance.Between(
                    player.x,
                    player.y,
                    portalX,
                    portalY
                );


            // Chegou suficientemente perto.
            if (distancia <= 75) {

                // Limpa primeiro para não executar várias vezes.
                this.portalPendente = null;


                if (
                    typeof this.scene.pararPersonagem
                    === 'function'
                ) {

                    this.scene.pararPersonagem();

                } else {

                    player.body.stop();

                    this.scene.isMoving = false;

                }


                // Continua a interação do portal.
                this.usarPortal(item);

            }

        }
    }

    
    // ============================================================
    // 🌀 CRIA A ANIMAÇÃO GLOBAL DO PORTAL
    // ============================================================

    criarAnimacao() {

        if (
            this.scene.anims.exists(
                'portal_regiao_anim'
            )
        ) {
            return;
        }


        this.scene.anims.create({

            key: 'portal_regiao_anim',

            frames:
                this.scene.anims.generateFrameNumbers(
                    'portal_regiao',
                    {
                        start: 0,
                        end: 4
                    }
                ),

            frameRate: 8,

            repeat: -1

        });

    }


    // ============================================================
    // 🗺️ LÊ A CAMADA "Portais" DO TILED
    // ============================================================

    carregarPortaisDoTiled() {

        const camada =
            this.map.getObjectLayer(
                'Portais'
            );


        if (
            !camada ||
            !Array.isArray(camada.objects)
        ) {

            console.log(
                `🌀 Nenhuma camada Portais encontrada em ${this.scene.regiaoAtual}`
            );

            return;
        }


        console.log(
            `🌀 Portais encontrados em ${this.scene.regiaoAtual}:`,
            camada.objects.length
        );


        camada.objects.forEach(
            objetoTiled => {

                this.criarPortal(
                    objetoTiled
                );

            }
        );

    }


    // ============================================================
    // ✨ CRIA UM PORTAL
    // ============================================================

    criarPortal(objetoTiled) {

        // ------------------------------------------
        // PROPRIEDADES PERSONALIZADAS DO TILED
        // ------------------------------------------

        const propriedades = {};

        if (
            Array.isArray(
                objetoTiled.properties
            )
        ) {

            objetoTiled.properties.forEach(
                propriedade => {

                    propriedades[
                        propriedade.name
                    ] = propriedade.value;

                }
            );
        }


        // Futuramente poderemos ter outros objetos
        // dentro da mesma camada.
        if (
            propriedades.tipo &&
            propriedades.tipo !== 'portal_regiao'
        ) {
            return;
        }


        // ------------------------------------------
        // TAMANHO DEFINIDO DIRETAMENTE NO TILED
        // ------------------------------------------

        const largura =
            Number(objetoTiled.width) || 130;

        const altura =
            Number(objetoTiled.height) || 160;


        // ============================================================
        // 🌀 PORTAL ÚNICO
        // ============================================================

        const portal =
            this.scene.add.sprite(
                objetoTiled.x,
                objetoTiled.y,
                'portal_regiao'
            );

        portal
            .setOrigin(0, 1)
            .setDisplaySize(
                largura,
                altura
            )
            .setDepth(10);


        // ============================================================
        // 🆔 IDENTIFICAÇÃO
        // ============================================================

        portal.portalId =
            propriedades.portal_id ||
            objetoTiled.name ||
            null;

        portal.tipoPortal =
            propriedades.tipo ||
            'portal_regiao';


        // ============================================================
        // ✨ ANIMAÇÃO
        // ============================================================

        portal.play(
            'portal_regiao_anim'
        );


        // ============================================================
        // 📦 REGISTRA
        // ============================================================

        const registro = {

            portalId: portal.portalId,

            sprite: portal,

            objetoTiled: objetoTiled,

            propriedades: propriedades

        };

        this.portais.push(registro);


        // ============================================================
        // 👆 PORTAL INTERATIVO
        // ============================================================

        portal.setInteractive({
            useHandCursor: true
        });


        portal.on(
            'pointerdown',
            (
                pointer,
                localX,
                localY,
                event
            ) => {

                if (event) {
                    event.stopPropagation();
                }

                this.usarPortal(registro);

            }
        );


        console.log(
            '✅ Portal criado:',
            portal.portalId || '(sem ID)',
            `X=${objetoTiled.x}`,
            `Y=${objetoTiled.y}`,
            `${largura}x${altura}`
        );

    }

    // ============================================================
    // 🌀 USAR PORTAL
    // ============================================================

    usarPortal(item) {

        const player = this.scene.player;

        if (!player) {
            return;
        }


        // Enquanto acabou de entrar no mapa,
        // o portal fica temporariamente bloqueado.
        if (this.scene.travadoNoPortal) {
            return;
        }


        const portal = item.sprite;


        // Centro aproximado da plataforma.
        const portalX =
            portal.x +
            (portal.displayWidth / 2);

        const portalY =
            portal.y - 20;


        const distancia =
            Phaser.Math.Distance.Between(
                player.x,
                player.y,
                portalX,
                portalY
            );


        // ==========================================
        // 🚶 JOGADOR ESTÁ LONGE
        // ==========================================

        if (distancia > 120) {

            // Guarda qual portal o jogador quer usar.
            this.portalPendente = item;

            // Faz o personagem caminhar até o centro da plataforma.
            this.scene.target.set(
                portalX,
                portalY
            );

            this.scene.isMoving = true;

            this.scene.physics.moveToObject(
                this.scene.player,
                this.scene.target,
                150
            );

            this.mostrarAvisoPortal(
                "Indo ao portal..."
            );

            return;
        }


        // ==========================================
        // 🛑 CHEGOU AO PORTAL
        // ==========================================

        if (
            typeof this.scene.pararPersonagem
            === 'function'
        ) {

            this.scene.pararPersonagem();

        }


        // ==========================================
        // 🌀 ABRE O MENU DE DESTINOS
        // ==========================================

        this.abrirMenuPortal(item);

    }

    // ============================================================
    // 🌍 DESTINOS DISPONÍVEIS
    // ============================================================

    obterDestinosPortal() {

        const regiaoAtual =
            this.scene.regiaoAtual;


        // ========================================================
        // 🏰 CAPITAL
        // Pode mostrar todas as regiões
        // ========================================================

        if (
            regiaoAtual ===
            'capital_eldora'
        ) {

            return Object.entries(
                this.regioesPortal
            )
            .filter(
                ([id]) =>
                    id !== 'capital_eldora'
            )
            .map(
                ([id, dados]) => ({

                    regiao: id,

                    portalChegadaId: id,

                    nome: dados.nome,

                    icone: dados.icone,

                    descricao:
                        dados.descricao,

                    // Futuramente exige Passe
                    exigePasse: true

                })
            );

        }


        // ========================================================
        // 🌍 OUTRAS REGIÕES
        // Retorno gratuito para a Capital
        // ========================================================

        const capital =
            this.regioesPortal.capital_eldora;


        return [

            {

                regiao:
                    'capital_eldora',

                portalChegadaId:
                    'capital_eldora',

                nome:
                    capital.nome,

                icone:
                    capital.icone,

                descricao:
                    'Retorno livre ao Reino',

                exigePasse:
                    false

            }

        ];

    }


    // ============================================================
    // 🌀 ABRIR MENU DO PORTAL - HTML
    // ============================================================

    abrirMenuPortal(item) {

        if (this.menuPortal) {
            return;
        }


        const destinos =
            this.obterDestinosPortal();


        if (!destinos.length) {

            this.mostrarAvisoPortal(
                'Nenhum destino disponível.'
            );

            return;
        }


        // ==========================================
        // 🛑 PARA O PERSONAGEM
        // ==========================================

        if (
            typeof this.scene.pararPersonagem
            === 'function'
        ) {

            this.scene.pararPersonagem();

        }


        // ==========================================
        // 🔒 BLOQUEIA OUTRAS UIs
        // ==========================================

        if (
            typeof window.ocultarMenuGlobalEldora
            === 'function'
        ) {

            window.ocultarMenuGlobalEldora();

        } else {

            document.body.classList.add(
                'ui-modal-aberta'
            );

        }


        // ==========================================
        // 🎨 CSS - CRIA APENAS UMA VEZ
        // ==========================================

        if (
            !document.getElementById(
                'eldora-portal-menu-style'
            )
        ) {

            const style =
                document.createElement('style');

            style.id =
                'eldora-portal-menu-style';

            style.textContent = `

                /* =====================================================
                   🌀 FUNDO DO MENU
                   ===================================================== */

                #eldora-portal-overlay {

                    position: fixed;
                    inset: 0;

                    z-index: 2147483000;

                    display: flex;
                    align-items: center;
                    justify-content: center;

                    padding: 14px;

                    box-sizing: border-box;

                    background:
                        rgba(2, 6, 15, 0.78);

                    backdrop-filter:
                        blur(2px);

                    -webkit-backdrop-filter:
                        blur(2px);

                    touch-action: none;

                }


                /* =====================================================
                   🏛️ PAINEL PRINCIPAL
                   ===================================================== */

                #eldora-portal-panel {

                    position: relative;

                    width:
                        min(312px, calc(100vw - 28px));
            
                    max-height:
                        min(560px, calc(100vh - 36px));
            
                    overflow-y: auto;
                    overflow-x: hidden;
            
                    padding:
                        14px 10px 11px;
            
                    box-sizing: border-box;
            
            
                    background:
            
                        radial-gradient(
                            circle at 50% -15%,
                            rgba(35, 105, 210, 0.20),
                            transparent 145px
                        ),
            
                        linear-gradient(
                            180deg,
                            #111c2d 0%,
                            #09121f 100%
                        );
            
            
                    border:
                        1px solid
                        #d0a634;
            
                    border-radius:
                        11px;
            
            
                    box-shadow:
            
                        0 0 0 2px
                        rgba(13, 26, 44, 0.95),
            
                        0 0 0 3px
                        rgba(208, 166, 52, 0.16),
            
                        0 16px 42px
                        rgba(0, 0, 0, 0.68),
            
                        inset 0 1px 0
                        rgba(255, 255, 255, 0.035);
            
            
                    color: white;
            
                    font-family:
                        Arial,
                        sans-serif;
            
                    scrollbar-width: thin;
                    scrollbar-color:
                        #775f25
                        #0b1421;
            
                }
            
            
                /* =====================================================
                   CABEÇALHO
                   ===================================================== */
            
                .eldora-portal-header {
            
                    position: relative;
            
                    min-height: 34px;
            
                    display: flex;
            
                    align-items: center;
                    justify-content: center;
            
                    padding:
                        0 31px 9px;
            
                    border-bottom:
                        1px solid
                        rgba(208, 166, 52, 0.27);
            
                }
            
            
                .eldora-portal-titulo {
            
                    display: flex;
            
                    align-items: center;
                    justify-content: center;
            
                    gap: 6px;
            
            
                    color:
                        #f2d47b;
            
                    font-family:
                        Cinzel,
                        serif;
            
                    font-size:
                        14px;
            
                    font-weight:
                        900;
            
                    letter-spacing:
                        0.35px;
            
                    text-align:
                        center;
            
                    text-shadow:
                        0 2px 3px
                        rgba(0, 0, 0, 0.9);
            
                }
            
            
                /* =====================================================
                   ✨ SÍMBOLO MÁGICO DO PORTAL
                   ===================================================== */
            
                .eldora-portal-runa {
            
                    display: inline-flex;
            
                    align-items: center;
                    justify-content: center;
            
                    width: 19px;
                    height: 19px;
            
            
                    color:
                        #38a9ff;
            
                    font-size:
                        15px;
            
                    text-shadow:
            
                        0 0 5px
                        rgba(56, 169, 255, 0.95),
            
                        0 0 11px
                        rgba(56, 169, 255, 0.45);
            
            
                    animation:
                        eldoraPortalRuna 2s ease-in-out infinite;
            
                }
            
            
                @keyframes eldoraPortalRuna {
            
                    0%,
                    100% {
            
                        transform:
                            scale(1);
            
                        opacity:
                            0.8;
            
                    }
            
                    50% {
            
                        transform:
                            scale(1.14);
            
                        opacity:
                            1;
            
                    }
            
                }
            
            
                /* =====================================================
                   ❌ FECHAR
                   ===================================================== */
            
                .eldora-portal-fechar {
            
                    position: absolute;
            
                    right: 0;
                    top: -2px;
            
                    width: 28px;
                    height: 28px;
            
            
                    display: flex;
            
                    align-items: center;
                    justify-content: center;
            
            
                    padding: 0;
            
            
                    color:
                        #ff7373;
            
            
                    background:
                        rgba(77, 16, 21, 0.30);
            
            
                    border:
                        1px solid
                        rgba(248, 113, 113, 0.30);
            
            
                    border-radius:
                        7px;
            
            
                    font-size:
                        15px;
            
                    font-weight:
                        900;
            
            
                    cursor:
                        pointer;
            
            
                    transition:
                        background 0.14s ease,
                        transform 0.14s ease;
            
                }
            
            
                .eldora-portal-fechar:hover {
            
                    background:
                        rgba(127, 29, 29, 0.46);
            
                }
            
            
                .eldora-portal-fechar:active {
            
                    transform:
                        scale(0.90);
            
                }
            
            
                /* =====================================================
                   📍 REGIÃO ATUAL
                   ===================================================== */
            
                .eldora-portal-local {
            
                    width:
                        max-content;
            
                    max-width:
                        calc(100% - 24px);
            
            
                    margin:
                        8px auto 10px;
            
            
                    padding:
                        3px 9px;
            
            
                    box-sizing:
                        border-box;
            
            
                    color:
                        #a8b5c7;
            
            
                    background:
                        rgba(3, 9, 18, 0.42);
            
            
                    border:
                        1px solid
                        rgba(106, 126, 153, 0.18);
            
            
                    border-radius:
                        10px;
            
            
                    font-size:
                        8px;
            
                    font-weight:
                        700;
            
            
                    text-align:
                        center;
            
                }
            
            
                /* =====================================================
                   🌍 LISTA DE DESTINOS
                   ===================================================== */
            
                .eldora-portal-destinos {
            
                    display: flex;
            
                    flex-direction: column;
            
                    gap: 6px;
            
                }
            
            
                /* =====================================================
                   🗺️ CARD DE DESTINO
                   ===================================================== */
            
                .eldora-portal-destino {
            
                    position: relative;
            
                    width: 100%;
            
                    min-height: 52px;
            
            
                    display: grid;
            
                    grid-template-columns:
                        34px
                        minmax(0, 1fr)
                        27px;
            
            
                    align-items: center;
            
            
                    gap: 7px;
            
            
                    padding:
                        6px 8px;
            
            
                    box-sizing:
                        border-box;
            
            
                    color:
                        white;
            
            
                    background:
            
                        linear-gradient(
                            135deg,
                            rgba(31, 48, 71, 0.97),
                            rgba(19, 32, 50, 0.98)
                        );
            
            
                    border:
                        1px solid
                        rgba(202, 161, 55, 0.48);
            
            
                    border-radius:
                        7px;
            
            
                    box-shadow:
            
                        inset 0 1px 0
                        rgba(255, 255, 255, 0.025);
            
            
                    cursor:
                        pointer;
            
            
                    text-align:
                        left;
            
            
                    touch-action:
                        manipulation;
            
            
                    transition:
            
                        transform 0.13s ease,
                        
                        border-color 0.13s ease,
            
                        background 0.13s ease,
            
                        box-shadow 0.13s ease;
            
                }
            
            
                .eldora-portal-destino:hover {
            
                    border-color:
                        rgba(236, 195, 79, 0.92);
            
            
                    background:
            
                        linear-gradient(
                            135deg,
                            rgba(43, 63, 91, 1),
                            rgba(24, 40, 62, 1)
                        );
            
            
                    box-shadow:
            
                        0 0 10px
                        rgba(213, 174, 63, 0.08),
            
                        inset 3px 0 0
                        rgba(218, 178, 66, 0.68);
            
                }
            
            
                .eldora-portal-destino:active {
            
                    transform:
                        scale(0.983);
            
                }
            
            
                /* =====================================================
                   🌿 ÍCONE
                   ===================================================== */
            
                .eldora-portal-icone {
            
                    width: 30px;
                    height: 30px;
            
            
                    display: flex;
            
                    align-items: center;
                    justify-content: center;
            
            
                    background:
            
                        radial-gradient(
                            circle,
                            rgba(38, 80, 126, 0.26),
                            rgba(5, 15, 28, 0.38)
                        );
            
            
                    border:
                        1px solid
                        rgba(134, 160, 192, 0.14);
            
            
                    border-radius:
                        7px;
            
            
                    box-shadow:
            
                        inset 0 1px 0
                        rgba(255, 255, 255, 0.03);
            

                    font-size:
                        19px;
            
                }
            
            
                /* =====================================================
                   🏷️ NOME
                   ===================================================== */
            
                .eldora-portal-nome {
            
                    color:
                        #f1d997;
            
            
                    font-family:
                        Cinzel,
                        serif;
            
            
                    font-size:
                        10px;
            
            
                    font-weight:
                        900;
            
            
                    letter-spacing:
                        0.18px;
            
            
                    white-space:
                        nowrap;
            
                }
            
            
                /* =====================================================
                   📜 DESCRIÇÃO
                   ===================================================== */
            
                .eldora-portal-descricao {
            
                    margin-top:
                        3px;
            
            
                    color:
                        #8797ab;
            
            
                    font-size:
                        8px;
            
            
                    font-weight:
                        600;
            
                }
            
            
                /* =====================================================
                   ➜ STATUS / SETA
                   ===================================================== */
            
                .eldora-portal-status {
            
                    width: 24px;
                    height: 24px;
            
            
                    display: flex;
            
                    align-items: center;
                    justify-content: center;
            
            
                        color:
                        #f2c63f;
            
            
                    background:
                        rgba(203, 158, 38, 0.09);
            
            
                    border:
                        1px solid
                        rgba(216, 174, 56, 0.24);
            
            
                    border-radius:
                        50%;
            
            
                    font-size:
                        14px;
            
            
                    font-weight:
                        900;
            
            
                    text-align:
                        center;
            
            
                    transition:
                        transform 0.15s ease,
                        background 0.15s ease;

                }


                .eldora-portal-destino:hover
                .eldora-portal-status {

                    transform:
                        translateX(2px);


                    background:
                        rgba(203, 158, 38, 0.17);
            
                }
            
            
                /* =====================================================
                   🔒 DESTINO BLOQUEADO
                   ===================================================== */
            
                .eldora-portal-destino.bloqueado {
            
                    border-color:
                        rgba(239, 68, 68, 0.42);


                    opacity:
                        0.72;

                }


                .eldora-portal-destino.bloqueado
                .eldora-portal-status {

                    background:
                        rgba(127, 29, 29, 0.20);
            
            
                    border-color:
                        rgba(248, 113, 113, 0.25);
            
                }
            
            
                /* =====================================================
                   📜 RODAPÉ
                   ===================================================== */
            
                .eldora-portal-rodape {
            
                    margin-top:
                        9px;
            
            
                    padding-top:
                        8px;
            
            
                    border-top:
                        1px solid
                        rgba(148, 163, 184, 0.08);
            
            
                    color:
                        #596a80;
            
            
                    font-size:
                        7px;
            
            
                    font-weight:
                        600;
            
            
                    text-align:
                        center;
            
                }
            

                /* =====================================================
                   📱 TELAS MUITO PEQUENAS
                   ===================================================== */
            
                @media (max-width: 340px) {
            
                    #eldora-portal-panel {
            
                        width:
                            calc(100vw - 20px);
            
                    }
            
            
                    .eldora-portal-nome {
            
                        font-size:
                            9px;
            
                    }
            
                }

            `;


            document.head.appendChild(
                style
            );

        }


        // ==========================================
        // 🌑 OVERLAY
        // ==========================================

        const overlay =
            document.createElement('div');

        overlay.id =
            'eldora-portal-overlay';


        // ==========================================
        // 🪟 PAINEL
        // ==========================================

        const painel =
            document.createElement('div');

        painel.id =
            'eldora-portal-panel';


        // Impede que clique no painel feche o modal.
        painel.addEventListener(
            'pointerdown',
            event => {

                event.stopPropagation();

            }
        );


        // ==========================================
        // CABEÇALHO
        // ==========================================

        const header =
            document.createElement('div');

        header.className =
            'eldora-portal-header';


        const titulo =
            document.createElement('div');

        titulo.className =
            'eldora-portal-titulo';

        titulo.innerHTML =
            '<span class="eldora-portal-runa">◈</span> PORTAL DE ELDORA';


        const fechar =
            document.createElement('button');

        fechar.type =
            'button';

        fechar.className =
            'eldora-portal-fechar';

        fechar.textContent =
            '✕';


        fechar.addEventListener(
            'pointerdown',
            event => {

                event.preventDefault();
                event.stopPropagation();

                this.fecharMenuPortal();

            }
        );


        header.appendChild(
            titulo
        );

        header.appendChild(
            fechar
        );


        painel.appendChild(
            header
        );


        // ==========================================
        // REGIÃO ATUAL
        // ==========================================

        const atual =
            this.regioesPortal[
                this.scene.regiaoAtual
            ];


        const localAtual =
            document.createElement('div');

        localAtual.className =
            'eldora-portal-local';

        localAtual.textContent =
            `Local atual: ${
                atual?.nome ||
                this.scene.regiaoAtual
            }`;


        painel.appendChild(
            localAtual
        );


        // ==========================================
        // DESTINOS
        // ==========================================

        const lista =
            document.createElement('div');

        lista.className =
            'eldora-portal-destinos';


        destinos.forEach(
            destino => {

                const bloqueado =
                    destino.exigePasse &&
                    this.EXIGIR_PASSE_PORTAL &&
                    !this.jogadorTemPassePortal();


                const botao =
                    document.createElement('button');

                botao.type =
                    'button';

                botao.className =
                    'eldora-portal-destino';


                if (bloqueado) {

                    botao.classList.add(
                        'bloqueado'
                    );

                }


                const icone =
                    document.createElement('div');

                icone.className =
                    'eldora-portal-icone';

                icone.textContent =
                    destino.icone;


                const textos =
                    document.createElement('div');


                const nome =
                    document.createElement('div');

                nome.className =
                    'eldora-portal-nome';

                nome.textContent =
                    destino.nome;


                const descricao =
                    document.createElement('div');

                descricao.className =
                    'eldora-portal-descricao';

                descricao.textContent =
                    destino.descricao;


                textos.appendChild(
                    nome
                );

                textos.appendChild(
                    descricao
                );


                const status =
                    document.createElement('div');

                status.className =
                    'eldora-portal-status';

                status.textContent =
                    bloqueado
                        ? '🔒'
                        : '➜';


                botao.appendChild(
                    icone
                );

                botao.appendChild(
                    textos
                );

                botao.appendChild(
                    status
                );


                botao.addEventListener(
                    'pointerdown',
                    event => {

                        event.preventDefault();
                        event.stopPropagation();


                        this.selecionarDestinoPortal(
                            destino
                        );

                    }
                );


                lista.appendChild(
                    botao
                );

            }
        );


        painel.appendChild(
            lista
        );


        // ==========================================
        // RODAPÉ
        // ==========================================

        const rodape =
            document.createElement('div');

        rodape.className =
            'eldora-portal-rodape';


        if (
            this.scene.regiaoAtual ===
            'capital_eldora'
        ) {

            rodape.textContent =
                this.EXIGIR_PASSE_PORTAL
                    ? 'Destinos regionais requerem Passe de Viagem.'
                    : 'Viagens liberadas durante os testes.';

        } else {

            rodape.textContent =
                'Retorno à Capital disponível.';

        }


        painel.appendChild(
            rodape
        );


        overlay.appendChild(
            painel
        );


        // ==========================================
        // CLIQUE FORA = FECHA
        // ==========================================

        overlay.addEventListener(
            'pointerdown',
            event => {

                event.preventDefault();
                event.stopPropagation();


                if (
                    event.target === overlay
                ) {

                    this.fecharMenuPortal();

                }

            }
        );


        document.body.appendChild(
            overlay
        );


        this.menuPortal =
            overlay;

    }


    // ============================================================
    // 🌍 DESTINO SELECIONADO
    // ============================================================

    selecionarDestinoPortal(
        destino
    ) {

        if (
            destino.exigePasse &&
            this.EXIGIR_PASSE_PORTAL &&
            !this.jogadorTemPassePortal()
        ) {

            this.fecharMenuPortal();

            this.mostrarAvisoPortal(
                'Você precisa do Passe de Viagem.'
            );

            return;
        }


        this.fecharMenuPortal();


        this.viajarPortal(
            destino
        );

    }


    // ============================================================
    // 🎟️ VERIFICAÇÃO DO PASSE
    // ============================================================

    jogadorTemPassePortal() {

        const perfil =
            window.perfilDadosGlobais ||
            {};


        // Estes nomes são provisórios.
        // Quando criarmos o Passe,
        // ligaremos ao campo real do backend.
        return Boolean(

            perfil.passe_viagem ||
            perfil.passe_portal ||
            perfil.travel_pass

        );

    }


    // ============================================================
    // ❌ FECHAR MENU
    // ============================================================

    fecharMenuPortal() {

        if (!this.menuPortal) {
            return;
        }


        if (
            this.menuPortal.parentNode
        ) {

            this.menuPortal.parentNode.removeChild(
                this.menuPortal
            );

        }


        this.menuPortal =
            null;


        if (
            typeof window.mostrarMenuGlobalEldora
            === 'function'
        ) {

            window.mostrarMenuGlobalEldora();

        } else {

            document.body.classList.remove(
                'ui-modal-aberta'
            );

        }

    }

    // ============================================================
    // 🚀 EXECUTA A VIAGEM
    // ============================================================

    viajarPortal(destino) {

        const scene = this.scene;


        scene.travadoNoPortal = true;

        scene.isMoving = false;


        if (
            scene.player &&
            scene.player.body
        ) {

            scene.player.body.stop();

        }


        // ==========================================
        // 📱 TELA DE CARREGAMENTO
        // ==========================================

        const tela =
            document.getElementById(
                'tela-carregamento'
            );


        if (tela) {

            tela.style.display = 'flex';

            tela.style.opacity = '1';

        }


        if (
            typeof window.atualizarCarregamento
            === 'function'
        ) {

            window.atualizarCarregamento(
                50,
                `Viajando para ${destino.nome}...`
            );

        }


        console.log(
            `🌀 Portal: ${scene.regiaoAtual} -> ${destino.regiao}`
        );


        // ==========================================
        // 🌍 TROCA O MAPA
        // ==========================================

        scene.scene.restart({

            regiao:
                destino.regiao,

            skin:
                scene.skinAtiva,

            portalChegadaId:
                destino.portalChegadaId,

            veioDePortal:
                true

        });

    }


    // ============================================================
    // 📍 SPAWN NO PORTAL DE DESTINO
    // ============================================================

    posicionarJogadorNaChegada(portalId) {

        const player = this.scene.player;

        if (!player) {
            return false;
        }


        const item =
            this.portais.find(
                portal =>
                    portal.portalId === portalId
            );


        if (!item) {

            console.warn(
                `⚠️ Portal de chegada não encontrado: ${portalId}`
            );

            return false;
        }


        const obj =
            item.objetoTiled;


        // Propriedades que configuramos no Tiled.
        const offsetX =
            Number(
                item.propriedades.spawn_offset_x ?? 0
            );

        const offsetY =
            Number(
                item.propriedades.spawn_offset_y ?? -20
            );


        // Centro horizontal do portal.
        const x =
            Number(obj.x) +
            (Number(obj.width) / 2) +
            offsetX;


        // Posição vertical definida pelo Tiled.
        const y =
            Number(obj.y) +
            offsetY;


        player.setPosition(
            x,
            y
        );


        if (player.body) {
            player.body.stop();
        }


        console.log(
            `✅ Chegada pelo portal ${portalId}`,
            `X=${x}`,
            `Y=${y}`
        );


        return true;

    }


    // ============================================================
    // 💬 AVISO
    // ============================================================

    mostrarAvisoPortal(mensagem) {

        const player =
            this.scene.player;

        if (!player) {
            return;
        }


        const aviso =
            this.scene.add.text(
                player.x,
                player.y - 45,
                mensagem,
                {
                    fontFamily:
                        'Arial',

                    fontSize:
                        '12px',

                    color:
                        '#facc15',

                    stroke:
                        '#000000',

                    strokeThickness:
                        4,

                    fontStyle:
                        'bold'
                }
            )
            .setOrigin(0.5)
            .setDepth(500);


        this.scene.tweens.add({

            targets: aviso,

            y: aviso.y - 25,

            alpha: 0,

            duration: 1800,

            onComplete: () => {
                aviso.destroy();
            }

        });

    }    

}