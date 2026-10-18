class MapaInterativo {
    constructor(scene) {
        this.scene = scene;
        this.objetosInterativos = [];
        this.init();
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
                // ==========================================
                // 1. ZONA INVISÍVEL DE CLIQUE
                // ==========================================
                const zona = this.scene.add.zone(obj.x, obj.y, 32, 32)
                    .setOrigin(0, 0)
                    .setInteractive()
                    .setDepth(50);

                zona.on('pointerdown', (pointer, lx, ly, ev) => {
                    ev.stopPropagation();
                    this.scene.target.set(obj.x + 16, obj.y + 48);
                    this.scene.isMoving = true;
                    this.scene.physics.moveToObject(this.scene.player, this.scene.target, 150);
                });

                // ==========================================
                // 2. POSIÇÃO DO BALÃO
                // ==========================================
                const botaoX = obj.icone_x ?? (obj.x + 16);
                const botaoY = obj.icone_y ?? (obj.y - 15);

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
                    fontSize: '15px',
                    color: '#f1c40f',
                    fontStyle: 'bold',
                    align: 'center',
                    wordWrap: {
                        width: 118,
                        useAdvancedWrap: true
                    }

                }).setOrigin(0.5).setVisible(false);
                
                // ==========================================
                // 🔗 LIGA OS ELEMENTOS AO CONTAINER DO BALÃO
                // ==========================================

                botao.fundo = fundo;
                botao.brilho = brilho;
                botao.iconeImagem = iconeImagem;
                botao.simbolo = simbolo;
                botao.textoMensagem = textoMensagem;

                const elementosBotao = [];
                if (brilho) elementosBotao.push(brilho);
                elementosBotao.push(fundo);
                elementosBotao.push(iconeImagem || simbolo, textoMensagem);
                botao.add(elementosBotao);
                // Desenha o balão pequeno inicial
                this.redesenharBalao(botao, 38, 34);

                botao.setSize(38, 34);
                botao.setInteractive(
                    new Phaser.Geom.Rectangle(-21, -40, 42, 44),
                    Phaser.Geom.Rectangle.Contains
                );

                const objetoRef = {
                    x: obj.x,
                    y: obj.y,
                    acao: obj.acao || null,
                    botao: botao,
                    mensagem: obj.mensagem || "Foi daqui\nque a lenda começou."
                };

                // ==========================================
                // 3. CLIQUE NO BALÃO
                // ==========================================
                botao.on('pointerdown', (p, lx, ly, ev) => {
                    ev.stopPropagation();

                    if (objetoRef.acao === 'abrir_coliseu_pvp') {
                        this.scene.player?.body?.stop();
                        this.scene.isMoving = false;
                        if (typeof window.abrirColiseuPvP === 'function') {
                            window.abrirColiseuPvP();
                        }
                        return;
                    }

                    this.scene.player.body.stop();
                    this.scene.isMoving = false;
                    this.scene.player.anims.stop();
                    this.scene.player.setFrame(1);

                    this.abrirBalaoMensagem(objetoRef);
                });

                this.objetosInterativos.push(objetoRef);
            });
        } catch (e) {
            console.error("Erro ao carregar objetos interativos:", e);
        }
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

        const corFundo = 0x243248;
        const corBorda = 0xd4a72c;

        const balaoPequeno = largura <= 50;

        // ponta menor no balão do ❗
        const pontaMetade = balaoPequeno ? 5 : 8;
        const pontaAltura = balaoPequeno ? 5 : 9;
        const espacoPonta = balaoPequeno ? 9 : 14;
        const raioCanto = balaoPequeno ? 8 : 10;

        const rectX = -largura / 2;
        const rectY = -altura;
        const rectW = largura;
        const rectH = altura - espacoPonta;

        fundo.fillStyle(corFundo, 0.96);
        fundo.lineStyle(2, corBorda, 1);

        fundo.fillRoundedRect(rectX, rectY, rectW, rectH, raioCanto);
        fundo.strokeRoundedRect(rectX, rectY, rectW, rectH, raioCanto);

        const baseY = rectY + rectH - 1;

        // pontinha do balão
        fundo.fillStyle(corFundo, 0.96);
        fundo.fillTriangle(
            -pontaMetade, baseY,
             pontaMetade, baseY,
             0, baseY + pontaAltura
        );

        fundo.lineStyle(2, corBorda, 1);
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
            botao.textoMensagem.setPosition(
                0,
                rectY + (rectH / 2) + 4
            );

            botao.textoMensagem.setWordWrapWidth(largura - 30);
            botao.textoMensagem.setLineSpacing(2);
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

        if (botao.tweenPulso) {
            botao.tweenPulso.stop();
            botao.tweenPulso = null;
        }

        botao.setVisible(true);
        botao.setScale(1);

        botao.simbolo.setVisible(false);
        botao.textoMensagem.setVisible(true).setText('');

        const larguraExpandida = 200;
        const alturaExpandida = 118;

        this.redesenharBalao(botao, larguraExpandida, alturaExpandida);

        this.scene.tweens.add({
            targets: botao,
            scaleX: 1.05,
            scaleY: 1.05,
            duration: 180,
            ease: 'Back.Out',
            onComplete: () => {
                this.digitarTextoNoBalao(
                    botao.textoMensagem,
                    objRef.mensagem,
                    70,
                    () => {
                        this.scene.time.delayedCall(4500, () => {
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
    }

    fecharBalaoMensagem(objRef) {
        const botao = objRef.botao;
        if (!botao) return;

        botao.textoMensagem.setVisible(false).setText('');
        botao.simbolo.setVisible(true);

        this.redesenharBalao(botao, 38, 34);

        this.scene.tweens.add({
            targets: botao,
            scaleX: 1,
            scaleY: 1,
            duration: 120,
            onComplete: () => {
                botao.aberto = false;
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
