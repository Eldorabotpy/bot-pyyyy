class MapaInterativo {
    constructor(scene) {
        this.scene = scene;
        this.objetosInterativos = [];
        this.ativacoesEstatuaPendentes = [];
        this.scene.events.on(
            'estatuaPedrocaAtivada',
            this.receberAtivacaoEstatua,
            this
        );
        this.scene.events.once('shutdown', () => {
            this.scene.events.off(
                'estatuaPedrocaAtivada',
                this.receberAtivacaoEstatua,
                this
            );
        });
        this.prepararAnimacoesEstatua();
        this.init();
    }

    prepararAnimacoesEstatua() {
        if (
            this.scene.regiaoAtual !== 'capital_eldora' ||
            !this.scene.textures.exists('estatua_pedroca_cristal') ||
            !this.scene.textures.exists('estatua_pedroca_despertar')
        ) {
            return;
        }

        const velocidadeQuadro = 1000 / 180;

        if (!this.scene.anims.exists('estatua_pedroca_cristal_idle')) {
            this.scene.anims.create({
                key: 'estatua_pedroca_cristal_idle',
                frames: this.scene.anims.generateFrameNumbers(
                    'estatua_pedroca_cristal',
                    { start: 0, end: 3 }
                ),
                frameRate: velocidadeQuadro,
                repeat: -1
            });
        }

        if (!this.scene.anims.exists('estatua_pedroca_despertar')) {
            this.scene.anims.create({
                key: 'estatua_pedroca_despertar',
                frames: this.scene.anims.generateFrameNumbers(
                    'estatua_pedroca_despertar',
                    { start: 0, end: 3 }
                ),
                frameRate: velocidadeQuadro,
                repeat: 0
            });
        }

        if (!this.scene.anims.exists('estatua_pedroca_recolher')) {
            this.scene.anims.create({
                key: 'estatua_pedroca_recolher',
                frames: [3, 2, 1, 0].map(frame => ({
                    key: 'estatua_pedroca_despertar',
                    frame
                })),
                frameRate: velocidadeQuadro,
                repeat: 0
            });
        }
    }

    receberAtivacaoEstatua(dados = {}) {
        if (
            dados.regiao &&
            dados.regiao !== this.scene.regiaoAtual
        ) {
            return;
        }

        const estatua = this.objetosInterativos.find(
            objeto => objeto.id === 'estatua_pedroca' && objeto.eEstatuaPedroca
        );

        if (!estatua) {
            this.ativacoesEstatuaPendentes.push(dados);
            return;
        }

        this.iniciarAnimacaoEstatua(estatua);
    }

    iniciarAnimacaoEstatua(objRef) {
        if (
            !objRef?.eEstatuaPedroca ||
            objRef.transicaoEstatua ||
            objRef.estatuaTransformada
        ) {
            return;
        }

        objRef.ativacaoSolicitada = false;
        objRef.transicaoEstatua = true;
        objRef.colisoesCristal?.forEach(corpo => { corpo.enable = false; });
        objRef.colisoesEstatua?.forEach(corpo => { corpo.enable = true; });
        objRef.botao.bloqueado = true;
        objRef.botao.setVisible(false);
        objRef.spriteEstatua
            .setFrame(0)
            .setVisible(true)
            .setAlpha(0);

        this.scene.tweens.add({
            targets: objRef.cristalEstatua,
            alpha: 0,
            duration: 220,
            ease: 'Sine.easeInOut',
            onComplete: () => objRef.cristalEstatua.setVisible(false)
        });
        this.scene.tweens.add({
            targets: objRef.spriteEstatua,
            alpha: 1,
            duration: 220,
            ease: 'Sine.easeInOut'
        });

        objRef.spriteEstatua.once('animationcomplete', animation => {
            if (animation.key !== 'estatua_pedroca_despertar') return;

            objRef.spriteEstatua.anims.stop();
            objRef.spriteEstatua.setFrame(3);
            objRef.estatuaTransformada = true;
            this.abrirBalaoMensagem(objRef);
        });
        objRef.spriteEstatua.play('estatua_pedroca_despertar');
    }

    reverterAnimacaoEstatua(objRef) {
        if (!objRef?.eEstatuaPedroca || !objRef.estatuaTransformada) return;

        objRef.transicaoEstatua = true;
        objRef.colisoesEstatua?.forEach(corpo => { corpo.enable = false; });
        objRef.colisoesCristal?.forEach(corpo => { corpo.enable = true; });
        objRef.botao.bloqueado = true;
        objRef.botao.setVisible(false);
        objRef.spriteEstatua
            .setFrame(3)
            .setAlpha(1)
            .setVisible(true);
        objRef.cristalEstatua
            .setAlpha(0)
            .setVisible(true);

        objRef.spriteEstatua.once('animationcomplete', animation => {
            if (animation.key !== 'estatua_pedroca_recolher') return;

            objRef.spriteEstatua.anims.stop();
            objRef.spriteEstatua.setFrame(0);

            this.scene.tweens.add({
                targets: objRef.spriteEstatua,
                alpha: 0,
                duration: 220,
                ease: 'Sine.easeInOut',
                onComplete: () => {
                    objRef.spriteEstatua
                        .setVisible(false)
                        .setAlpha(1);
                    objRef.cristalEstatua
                        .setVisible(true)
                        .setAlpha(1);
                    objRef.estatuaTransformada = false;
                    objRef.transicaoEstatua = false;
                    objRef.botao.bloqueado = false;

                    const dist = Phaser.Math.Distance.Between(
                        this.scene.player.x,
                        this.scene.player.y,
                        objRef.x,
                        objRef.y
                    );
                    objRef.botao.setVisible(dist <= 100);
                }
            });
            this.scene.tweens.add({
                targets: objRef.cristalEstatua,
                alpha: 1,
                duration: 220,
                ease: 'Sine.easeInOut'
            });
        });
        objRef.spriteEstatua.play('estatua_pedroca_recolher');
    }

    init() {
        // Pega a região atual definida no init() do mapa.js
        const regiao = this.scene.regiaoAtual;
        this.carregarObjetosDoMapa(regiao);
    }

    async carregarObjetosDoMapa(regiao) {
        try {
            const res = await fetch(`/api/mapa/objetos/${regiao}`);
            const objetos = await res.json();

            objetos.forEach(obj => {
                const eEstatuaPedroca = obj.id === 'estatua_pedroca'
                    && regiao === 'capital_eldora'
                    && this.scene.textures.exists('estatua_pedroca_cristal')
                    && this.scene.textures.exists('estatua_pedroca_despertar');
                const referenciaEstatua = eEstatuaPedroca
                    ? this.scene.tilemap
                        ?.getObjectLayer('Referencia da Estatua do Criador')
                        ?.objects
                        ?.find(referencia =>
                            referencia.type === 'referencia_visual' ||
                            referencia.name === 'Cristal e pedestal (referencia visual)'
                        )
                    : null;
                let cristalEstatua = null;
                let spriteEstatua = null;
                let colisoesCristal = [];
                let colisoesEstatua = [];
                let xInteracao = obj.x;
                let yInteracao = obj.y;
                let botaoX = obj.icone_x ?? (obj.x + 16);
                let botaoY = obj.icone_y ?? (obj.y - 15);

                if (eEstatuaPedroca) {
                    const larguraReferencia = Number(referenciaEstatua?.width) || 128;
                    const alturaReferencia = Number(referenciaEstatua?.height) || (256 * 2 / 3);
                    const xEstatua = Number(referenciaEstatua?.x) || obj.x;
                    const baseYEstatua = Number(referenciaEstatua?.y) || (obj.y + 128);
                    const escalaX = larguraReferencia / 192;
                    const escalaY = alturaReferencia / 256;

                    if (referenciaEstatua) {
                        // Mantém o ponto de interação no mesmo lugar relativo
                        // à arte, mesmo quando ela for movida ou redimensionada no Tiled.
                        xInteracao = xEstatua;
                        yInteracao = baseYEstatua - alturaReferencia * 0.75;
                        botaoX += xInteracao - obj.x;
                        botaoY += yInteracao - obj.y;
                    }

                    cristalEstatua = this.scene.add.sprite(
                        xEstatua,
                        baseYEstatua,
                        'estatua_pedroca_cristal',
                        0
                    )
                        .setOrigin(0.5, 1)
                        .setScale(escalaX, escalaY);

                    spriteEstatua = this.scene.add.sprite(
                        xEstatua,
                        baseYEstatua,
                        'estatua_pedroca_despertar',
                        0
                    )
                        .setOrigin(0.5, 1)
                        .setScale(escalaX, escalaY)
                        .setAlpha(0)
                        .setVisible(false);

                    if (typeof this.scene.adicionarColisaoDeObjetoTile === 'function') {
                        const gidCristal = this.scene.tilemap.tilesets.find(
                            tileset => tileset.name === 'cristal_mana_rotacao'
                        )?.firstgid;
                        const gidEstatua = this.scene.tilemap.tilesets.find(
                            tileset => tileset.name === 'estatua_ergue_teclado'
                        )?.firstgid;
                        const origemX = xEstatua - larguraReferencia / 2;
                        const origemY = baseYEstatua - alturaReferencia;
                        if (gidCristal) {
                            colisoesCristal = this.scene.adicionarColisaoDeObjetoTile(
                                gidCristal, origemX, origemY,
                                larguraReferencia, alturaReferencia
                            );
                        }
                        if (gidEstatua) {
                            colisoesEstatua = this.scene.adicionarColisaoDeObjetoTile(
                                gidEstatua, origemX, origemY,
                                larguraReferencia, alturaReferencia, false
                            );
                        }
                    }

                    // A base visível do pedestal termina antes do rodapé
                    // transparente do frame. A profundidade deve usar essa
                    // borda: ao passar por baixo, o jogador fica na frente.
                    const baseColisao = Math.max(
                        ...colisoesCristal.map(corpo => corpo.bottom),
                        ...colisoesEstatua.map(corpo => corpo.bottom),
                        baseYEstatua - alturaReferencia * 0.1
                    );
                    const profundidadeEstatua = typeof this.scene.calcularProfundidadeAtor === 'function'
                        ? this.scene.calcularProfundidadeAtor({
                            x: xEstatua, y: baseColisao, originY: 1, displayHeight: 0
                        })
                        : 14;
                    cristalEstatua.setDepth(profundidadeEstatua);
                    spriteEstatua.setDepth(profundidadeEstatua);

                    cristalEstatua.play('estatua_pedroca_cristal_idle');
                }

                // ==========================================
                // 1. ZONA INVISÍVEL DE CLIQUE
                // ==========================================
                const zona = this.scene.add.zone(xInteracao, yInteracao, 32, 32)
                    .setOrigin(0, 0)
                    .setInteractive()
                    .setDepth(50);

                // ==========================================
                // 2. POSIÇÃO DO BALÃO
                // ==========================================
                const botao = this.scene.add.container(botaoX, botaoY)
                    .setDepth(100)
                    .setVisible(false);

                botao.baseX = botaoX;
                botao.baseY = botaoY;
                botao.bloqueado = false;
                botao.aberto = false;
                botao.tweenPulso = null;
                botao.tweenBrilho = null;
                botao.eEntradaColiseu = obj.acao === 'abrir_coliseu_pvp';

                // Fundo gráfico do balão
                const fundo = this.scene.add.graphics();

                const eEntradaColiseu = botao.eEntradaColiseu;
                const temImagemEspadas = eEntradaColiseu
                    && this.scene.textures.exists('icone_espadas_coliseu');
                const brilho = eEntradaColiseu
                    ? this.scene.add.graphics()
                    : null;
                let iconeImagem = null;
                let simbolo = null;

                if (brilho) {
                    brilho.fillStyle(0xffd36b, 0.12);
                    brilho.fillCircle(0, -18, 27);
                    brilho.fillStyle(0xffe7a3, 0.1);
                    brilho.fillCircle(0, -18, 21);
                    brilho.setAlpha(0);
                }

                if (temImagemEspadas) {
                    iconeImagem = this.scene.add.image(
                        0,
                        -18,
                        'icone_espadas_coliseu'
                    )
                        .setOrigin(0.5)
                        .setDisplaySize(28, 28);
                } else {
                    simbolo = this.scene.add.text(0, -18, obj.texto_botao || '❗', {
                        fontFamily: 'Arial',
                        fontSize: '18px',
                        fontStyle: 'bold',
                        color: '#ff4d4d',
                        stroke: '#000000',
                        strokeThickness: 3
                    }).setOrigin(0.5);
                }

                // Texto da mensagem dentro do balão
                const textoMensagem = this.scene.add.text(0, -40, '', {
                    fontFamily: 'Cinzel, Arial',
                    fontSize: '13px',
                    color: '#f4ead2',
                    fontStyle: 'bold',
                    align: 'center',
                    wordWrap: {
                        width: 168,
                        useAdvancedWrap: true
                    }

                }).setOrigin(0.5).setVisible(false);

                const tituloMensagem = this.scene.add.text(0, -40, '', {
                    fontFamily: 'Cinzel, Georgia, serif',
                    fontSize: '9px',
                    fontStyle: 'bold',
                    color: '#f2ce73',
                    align: 'center',
                    letterSpacing: 1
                }).setOrigin(0.5).setVisible(false);

                const dicaMensagem = this.scene.add.text(0, -40, 'TOQUE PARA FECHAR', {
                    fontFamily: 'Arial, sans-serif',
                    fontSize: '8px',
                    fontStyle: 'bold',
                    color: '#9fb0c4',
                    align: 'center',
                    letterSpacing: 0.5
                }).setOrigin(0.5).setVisible(false);
                
                // ==========================================
                // 🔗 LIGA OS ELEMENTOS AO CONTAINER DO BALÃO
                // ==========================================

                botao.fundo = fundo;
                botao.brilho = brilho;
                botao.iconeImagem = iconeImagem;
                botao.simbolo = simbolo;
                botao.textoMensagem = textoMensagem;
                botao.tituloMensagem = tituloMensagem;
                botao.dicaMensagem = dicaMensagem;

                const elementosBotao = [];
                if (brilho) elementosBotao.push(brilho);
                elementosBotao.push(fundo);
                elementosBotao.push(
                    iconeImagem || simbolo,
                    tituloMensagem,
                    textoMensagem,
                    dicaMensagem
                );
                botao.add(elementosBotao);
                // Desenha o balão pequeno inicial
                this.redesenharBalao(botao, 38, 34);

                botao.setSize(38, 34);
                botao.setInteractive(
                    new Phaser.Geom.Rectangle(-21, -40, 42, 44),
                    Phaser.Geom.Rectangle.Contains
                );

                const objetoRef = {
                    id: obj.id || null,
                    x: xInteracao,
                    y: yInteracao,
                    acao: obj.acao || null,
                    botao: botao,
                    cristalEstatua,
                    spriteEstatua,
                    colisoesCristal,
                    colisoesEstatua,
                    eEstatuaPedroca,
                    transicaoEstatua: false,
                    estatuaTransformada: false,
                    ativacaoSolicitada: false,
                    tituloMensagem: obj.titulo_mensagem || (
                        eEstatuaPedroca ? 'MEMÓRIA DO CRIADOR' : 'AVISO DO REINO'
                    ),
                    mensagem: obj.mensagem || "Foi daqui\nque a lenda começou."
                };

                zona.on('pointerdown', (pointer, lx, ly, ev) => {
                    ev.stopPropagation();

                    if (objetoRef.eEstatuaPedroca && this.jogadorPerto(objetoRef)) {
                        this.interagirComObjeto(objetoRef);
                        return;
                    }

                    this.moverJogadorAte(objetoRef);
                });

                if (cristalEstatua && spriteEstatua) {
                    const aoClicarEstatua = (pointer, lx, ly, ev) => {
                        ev?.stopPropagation();

                        if (!this.jogadorPerto(objetoRef)) {
                            this.moverJogadorAte(objetoRef);
                            return;
                        }

                        this.interagirComObjeto(objetoRef);
                    };

                    cristalEstatua.setInteractive();
                    spriteEstatua.setInteractive();
                    cristalEstatua.on('pointerdown', aoClicarEstatua);
                    spriteEstatua.on('pointerdown', aoClicarEstatua);
                }

                // ==========================================
                // 3. CLIQUE NO BALÃO
                // ==========================================
                botao.on('pointerdown', (p, lx, ly, ev) => {
                    ev.stopPropagation();
                    if (objetoRef.botao.aberto) {
                        this.fecharBalaoMensagem(objetoRef);
                        return;
                    }
                    this.interagirComObjeto(objetoRef);
                });

                this.objetosInterativos.push(objetoRef);

                if (eEstatuaPedroca && this.ativacoesEstatuaPendentes.length) {
                    this.ativacoesEstatuaPendentes.splice(0).forEach(() => {
                        this.iniciarAnimacaoEstatua(objetoRef);
                    });
                }
            });
        } catch (e) {
            console.error("Erro ao carregar objetos interativos:", e);
        }
    }

    jogadorPerto(objRef) {
        const player = this.scene.player;
        if (!player) return false;

        return Phaser.Math.Distance.Between(
            player.x,
            player.y,
            objRef.x,
            objRef.y
        ) <= 100;
    }

    moverJogadorAte(objRef) {
        const player = this.scene.player;
        if (!player || !this.scene.target || !this.scene.physics) return;

        this.scene.target.set(objRef.x + 16, objRef.y + 48);
        this.scene.isMoving = true;
        this.scene.physics.moveToObject(player, this.scene.target, 150);
    }

    pararJogador() {
        const player = this.scene.player;
        player?.body?.stop();
        this.scene.isMoving = false;

        if (player?.anims) {
            player.anims.stop();
            player.setFrame(1);
        }
    }

    interagirComObjeto(objRef) {
        if (!objRef) return;

        if (objRef.botao?.aberto) {
            this.fecharBalaoMensagem(objRef);
            return;
        }

        if (objRef.acao === 'abrir_coliseu_pvp') {
            this.pararJogador();
            if (typeof window.abrirColiseuPvP === 'function') {
                window.abrirColiseuPvP();
            }
            return;
        }

        this.pararJogador();

        if (objRef.eEstatuaPedroca) {
            if (
                objRef.transicaoEstatua ||
                objRef.estatuaTransformada ||
                objRef.ativacaoSolicitada
            ) {
                return;
            }

            const socket = window.eldoraSocket;
            if (socket?.connected) {
                objRef.ativacaoSolicitada = true;
                objRef.botao.bloqueado = true;
                objRef.botao.setVisible(false);
                socket.emit('ativarEstatuaPedroca', {}, resposta => {
                    if (resposta?.sucesso || !objRef.ativacaoSolicitada) return;
                    this.iniciarAnimacaoEstatua(objRef);
                });
            } else {
                this.iniciarAnimacaoEstatua(objRef);
            }
            return;
        }

        this.abrirBalaoMensagem(objRef);
    }

    redesenharBalao(botao, largura, altura) {
        const fundo = botao.fundo;
        if (!fundo) return;

        fundo.clear();

        if (botao.eEntradaColiseu) {
            const centroY = -18;

            // Medalhão escuro com aro dourado para destacar as espadas na entrada.
            fundo.fillStyle(0x080e16, 0.7);
            fundo.fillCircle(1, centroY + 2, 22);

            fundo.fillStyle(0x392714, 1);
            fundo.fillCircle(0, centroY, 21);
            fundo.lineStyle(2, 0xf1c75b, 1);
            fundo.strokeCircle(0, centroY, 20);

            fundo.fillStyle(0x182638, 1);
            fundo.fillCircle(0, centroY, 17.5);
            fundo.lineStyle(1, 0xa77d2e, 0.95);
            fundo.strokeCircle(0, centroY, 16.5);

            fundo.fillStyle(0x23364a, 0.9);
            fundo.fillCircle(0, centroY, 14.5);

            // Rebites discretos completam o aro sem competir com o ícone.
            fundo.fillStyle(0xffdf82, 0.95);
            fundo.fillCircle(0, centroY - 18, 1.15);
            fundo.fillCircle(0, centroY + 18, 1.15);

            if (botao.simbolo) botao.simbolo.setPosition(0, centroY);
            if (botao.iconeImagem) botao.iconeImagem.setPosition(0, centroY);
            if (botao.textoMensagem) {
                botao.textoMensagem.setPosition(0, centroY + 22);
                botao.textoMensagem.setWordWrapWidth(largura - 30);
                botao.textoMensagem.setLineSpacing(2);
            }

            botao.setSize(42, 44);

            if (
                botao.input &&
                botao.input.hitArea &&
                typeof botao.input.hitArea.setTo === 'function'
            ) {
                botao.input.hitArea.setTo(-21, -40, 42, 44);
            }
            return;
        }

        const corFundo = 0x111b2a;
        const corBorda = 0xd1a94f;

        const balaoPequeno = largura <= 50;

        // ponta menor no balão do ❗
        const pontaMetade = balaoPequeno ? 5 : 9;
        const pontaAltura = balaoPequeno ? 5 : 11;
        const espacoPonta = balaoPequeno ? 9 : 15;
        const raioCanto = balaoPequeno ? 8 : 12;

        const rectX = -largura / 2;
        const rectY = -altura;
        const rectW = largura;
        const rectH = altura - espacoPonta;

        fundo.fillStyle(0x050a12, balaoPequeno ? 0.4 : 0.58);
        fundo.fillRoundedRect(rectX + 2, rectY + 4, rectW, rectH, raioCanto);
        fundo.fillStyle(corFundo, 0.98);
        fundo.lineStyle(balaoPequeno ? 2 : 2.5, corBorda, 1);
        fundo.fillRoundedRect(rectX, rectY, rectW, rectH, raioCanto);
        fundo.strokeRoundedRect(rectX, rectY, rectW, rectH, raioCanto);

        if (!balaoPequeno) {
            fundo.lineStyle(1, 0x6b7890, 0.65);
            fundo.strokeRoundedRect(rectX + 4, rectY + 4, rectW - 8, rectH - 8, 9);

            fundo.fillStyle(0x1b2a3d, 0.96);
            fundo.fillRoundedRect(rectX + 5, rectY + 5, rectW - 10, 24, 8);

            fundo.lineStyle(1, 0x786338, 0.9);
            fundo.beginPath();
            fundo.moveTo(rectX + 13, rectY + 31);
            fundo.lineTo(rectX + rectW - 13, rectY + 31);
            fundo.strokePath();

            fundo.fillStyle(0xe7c16a, 0.95);
            fundo.fillCircle(0, rectY + 31, 1.5);
        }

        const baseY = rectY + rectH - 1;

        // pontinha do balão
        fundo.fillStyle(corFundo, 0.98);
        fundo.fillTriangle(
            -pontaMetade, baseY,
             pontaMetade, baseY,
             0, baseY + pontaAltura
        );

        fundo.lineStyle(balaoPequeno ? 2 : 2.5, corBorda, 1);
        fundo.beginPath();
        fundo.moveTo(-pontaMetade, baseY);
        fundo.lineTo(0, baseY + pontaAltura);
        fundo.lineTo(pontaMetade, baseY);
        fundo.strokePath();

        if (botao.simbolo) {
            botao.simbolo.setPosition(
                0,
                balaoPequeno ? -18 : rectY + (rectH / 2) + 1
           );
        }

        if (botao.textoMensagem) {
            const alturaTexto = botao.alturaTextoMensagem || 32;
            botao.textoMensagem
                .setPosition(
                    0,
                    balaoPequeno
                        ? -40
                        : rectY + 40 + (alturaTexto / 2)
                )
                .setWordWrapWidth(largura - 34)
                .setLineSpacing(1);
        }

        if (botao.tituloMensagem) {
            botao.tituloMensagem
                .setPosition(0, balaoPequeno ? -40 : rectY + 17)
                .setWordWrapWidth(largura - 24);
        }

        if (botao.dicaMensagem) {
            botao.dicaMensagem
                .setPosition(0, balaoPequeno ? -40 : rectY + rectH - 10)
                .setWordWrapWidth(largura - 24);
        }

        botao.setSize(largura, altura + 2);

        if (
            botao.input &&
            botao.input.hitArea &&
            typeof botao.input.hitArea.setTo === 'function'
        ) {
            botao.input.hitArea.setTo(rectX, rectY, largura, altura + 4);
        }
    }

    abrirBalaoMensagem(objRef) {
        const botao = objRef.botao;
        if (!botao || botao.aberto) return;

        botao.aberto = true;
        botao.bloqueado = true;
        botao.fechando = false;

        if (botao.tweenPulso) {
            botao.tweenPulso.stop();
            botao.tweenPulso = null;
        }

        botao.setVisible(true);
        botao.setScale(0.88);

        botao.simbolo?.setVisible(false);
        botao.textoMensagem.setVisible(true).setText('');
        botao.tituloMensagem
            .setText(objRef.tituloMensagem || 'AVISO DO REINO')
            .setVisible(true);
        botao.dicaMensagem.setVisible(true);

        const larguraExpandida = 204;
        this.redesenharBalao(botao, larguraExpandida, 106);

        // Mede a mensagem completa antes do efeito de digitação para reservar
        // espaço para todas as linhas e manter a dica de fechar separada.
        botao.textoMensagem.setText(objRef.mensagem);
        botao.alturaTextoMensagem = Math.max(
            32,
            Math.ceil(botao.textoMensagem.height || 32)
        );
        botao.textoMensagem.setText('');

        const alturaExpandida = Math.max(
            106,
            Math.ceil(botao.alturaTextoMensagem + 80)
        );
        this.redesenharBalao(botao, larguraExpandida, alturaExpandida);

        botao.tweenAbertura = this.scene.tweens.add({
            targets: botao,
            scaleX: 1,
            scaleY: 1,
            duration: 220,
            ease: 'Back.Out',
            onComplete: () => {
                botao.tweenAbertura = null;
                if (!botao.aberto) return;
                botao.timerDigitacao = this.digitarTextoNoBalao(
                    botao.textoMensagem,
                    objRef.mensagem,
                    48,
                    () => {
                        botao.timerDigitacao = null;
                        botao.timerAutoFechamento = this.scene.time.delayedCall(6500, () => {
                            botao.timerAutoFechamento = null;
                            this.fecharBalaoMensagem(objRef);
                        });
                    }
                );
            }
        });
    }

    digitarTextoNoBalao(textoObj, mensagem, velocidade = 35, callback = null) {
        if (!textoObj) return;

        textoObj.setText('');
        let i = 0;

        const timer = this.scene.time.addEvent({
            delay: velocidade,
            loop: true,
            callback: () => {
                i++;
                textoObj.setText(mensagem.substring(0, i));

                if (i >= mensagem.length) {
                    timer.remove(false);
                    if (callback) callback();
                }
            }
        });

        return timer;
    }

    fecharBalaoMensagem(objRef) {
        const botao = objRef.botao;
        if (!botao || !botao.aberto || botao.fechando) return;

        botao.fechando = true;
        botao.timerDigitacao?.remove(false);
        botao.timerDigitacao = null;
        botao.timerAutoFechamento?.remove(false);
        botao.timerAutoFechamento = null;
        botao.tweenAbertura?.stop();
        botao.tweenAbertura = null;

        botao.textoMensagem.setVisible(false).setText('');
        botao.tituloMensagem.setVisible(false).setText('');
        botao.dicaMensagem.setVisible(false);
        botao.simbolo?.setVisible(true);

        this.redesenharBalao(botao, 38, 34);

        botao.tweenFechamento = this.scene.tweens.add({
            targets: botao,
            scaleX: 1,
            scaleY: 1,
            duration: 120,
            onComplete: () => {
                botao.tweenFechamento = null;
                botao.aberto = false;
                botao.fechando = false;

                if (objRef.eEstatuaPedroca && objRef.estatuaTransformada) {
                    this.reverterAnimacaoEstatua(objRef);
                    return;
                }

                botao.bloqueado = false;

                const dist = Phaser.Math.Distance.Between(
                    this.scene.player.x,
                    this.scene.player.y,
                    objRef.x,
                    objRef.y
                );

                botao.setVisible(dist <= 100);
            }
        });
    }

    // Função que deve ser chamada no update() do mapa.js
    verificarProximidade(player) {

        this.objetosInterativos.forEach(obj => {

            const botao = obj.botao;

            const dist = Phaser.Math.Distance.Between(
                player.x,
                player.y,
                obj.x,
                obj.y
            );

            const estaPerto = dist <= 100;

            // ==========================================
            // 💬 BALÃO ESTÁ ABERTO COM MENSAGEM
            // ==========================================
            // Enquanto a mensagem estiver aparecendo,
            // não escondemos nem pulsamos o balão.
            if (botao.aberto) {

                botao.setVisible(true);

                if (botao.tweenPulso) {

                    botao.tweenPulso.stop();
                    botao.tweenPulso = null;
                }

                if (botao.tweenBrilho) {
                    botao.tweenBrilho.stop();
                    botao.tweenBrilho = null;
                }

                if (botao.brilho) botao.brilho.setAlpha(0);

                botao.setScale(1);

                return;
            }


            // ==========================================
            // 🔒 TEMPORARIAMENTE BLOQUEADO
            // ==========================================
            if (botao.bloqueado) {

                if (botao.tweenPulso) {

                    botao.tweenPulso.stop();
                    botao.tweenPulso = null;
                }

                if (botao.tweenBrilho) {
                    botao.tweenBrilho.stop();
                    botao.tweenBrilho = null;
                }

                if (botao.brilho) botao.brilho.setAlpha(0);

                botao.setScale(1);

                return;
            }


            // ==========================================
            // ❗ JOGADOR CHEGOU PERTO
            // ==========================================
            if (estaPerto) {

                botao.setVisible(true);

                // Só cria UMA animação de pulsação.
                if (!botao.tweenPulso) {

                    botao.tweenPulso =
                        this.scene.tweens.add({

                            targets: botao,

                            scaleX: 1.08,
                            scaleY: 1.08,

                            duration: 700,

                            yoyo: true,
                            repeat: -1,

                            ease: 'Sine.easeInOut'
                        });
                }

                if (botao.brilho && !botao.tweenBrilho) {
                    botao.brilho.setAlpha(0.18);
                    botao.tweenBrilho = this.scene.tweens.add({
                        targets: botao.brilho,
                        alpha: 0.42,
                        duration: 850,
                        yoyo: true,
                        repeat: -1,
                        ease: 'Sine.easeInOut'
                    });
                }

            }

            // ==========================================
            // 🚶 JOGADOR SE AFASTOU
            // ==========================================
            else {

                botao.setVisible(false);

                if (botao.tweenPulso) {

                    botao.tweenPulso.stop();
                    botao.tweenPulso = null;
                }

                if (botao.tweenBrilho) {
                    botao.tweenBrilho.stop();
                    botao.tweenBrilho = null;
                }

                if (botao.brilho) botao.brilho.setAlpha(0);

                botao.setScale(1);
            }

        });
    }
}
