// ==========================================
// MOTOR DE CAÇADA LIVRE - MUNDO DE ELDORA
// ==========================================
// ==========================================

class MotorCacada {
    constructor(scene, socket) {
        this.scene = scene;
        this.socket = socket;
        this.mobsNoMapa = this.scene.add.group();

        // ==========================================
        // 🤖 AUTO CAÇADA — ESTADO INICIAL
        // ==========================================
        // Etapa 1: apenas prepara o estado.
        // Ainda não anda sozinho, não abre combate e não ataca.
        this.autoCacadaAtiva = false;
        this.autoCacadaAlvo = null;
        this.autoCacadaSpawnId = null;
        this.autoCacadaUltimaPosicao = null;
        this.autoCacadaTempoParado = 0;
        this.autoCacadaDistanciaAtaque = 80;

        // Quando entra em combate, a Auto Caçada não desliga.
        // Ela apenas pausa e volta depois que sair da arena.
        this.autoCacadaPausadaPorCombate = false;
        this.autoCacadaRetomando = false;

        // Segurança contra travamento no caminho.
        this.autoCacadaUltimoReenvioMovimento = 0;
        this.autoCacadaIgnorarSpawnIds = {};
        this.caravanaQuestSprite = null;
        this.caravanaQuestMovimiento = null;
        this.caravanaQuestViajante = null;
        this.caravanaQuestViajanteAnim = null;
        this.caravanaQuestSocorro = null;
        this.caravanaQuestSocorroAnim = null;
        this.caravanaQuestIntegridade = null;
        this.caravanaQuestViajanteSalvo = false;
        this.caravanaQuestDestruida = false;
        this.caravanaIAEstado = null;
        
        this.iniciarEscutas();

        // Botão temporário para testar no Telegram, sem precisar de F12.
        this.criarBotaoTesteAutoCacada();
    }

    iniciarEscutas() {
        if (this.socket) {
            // ==========================================
            // 🛡️ A MÁGICA AQUI: LIMPANDO AS ESCUTAS FANTASMAS
            // ==========================================
            // Desliga os ouvidos antigos antes de ligar os novos.
            // Isso impede que o jogo acumule "lixo" na memória ao trocar de mapa!
            this.socket.off('carregarMobsMapa');
            this.socket.off('mobMapaMorreu');
            this.socket.off('mobMapaNasceu');
            this.socket.off('mobMapaAtualizado');
            this.socket.off('convocarCombateGrupo');
            this.socket.off('dungeonConcluida');
            this.socket.off('caravanaQuestAtiva');
            this.socket.off('caravanaQuestAtualizada');
            this.socket.off('caravanaIAAtualizada');

            this.socket.on('convocarCombateGrupo', async (dados) => {
                console.log("🤝 [MAPA] Convocado para combate em grupo:", dados);

                if (!dados || !dados.spawn_id || !dados.sala_id) {
                    console.warn("Pacote inválido:", dados);
                    return;
                }

                window.salaCombateGrupoAtual = dados.sala_id;
                window.estadoCombateGrupoAtual = dados.sala || null;

                if (typeof window.iniciarCacadaApp === 'function') {
                    await window.iniciarCacadaApp(dados.spawn_id, {
                        salaId: dados.sala_id,
                        modoGrupo: true
                    });
                } else {
                    console.error("iniciarCacadaApp não encontrada no mapa.");
                }
            });

            // 1. Carrega todos os mobs ao entrar no mapa
            this.socket.on('carregarMobsMapa', (mobs) => {
                Object.values(mobs).forEach(mob => this.spawnMob(mob));
            });

            this.socket.on('caravanaQuestAtiva', dados => {
                if (
                    String(dados?.owner_id || '') !==
                    String(localStorage.getItem('jogadorEldoraID') || '')
                ) return;
                this.mostrarCaravanaQuest(dados);
            });

            this.socket.on('caravanaQuestAtualizada', dados => {
                if (
                    String(dados?.owner_id || '') !==
                    String(localStorage.getItem('jogadorEldoraID') || '')
                ) return;

                const texto = dados.concluido
                    ? 'A caravana está segura. Alcance o Nível 5 e volte ao Capitão Varek.'
                    : `Goblins afastados da caravana: ${dados.mob_atual}/${dados.mob_total}.`;
                if (dados.concluido) {
                    this.caravanaQuestViajanteSalvo = true;
                    this.caravanaQuestDestruida = false;
                    this.acalmarViajanteCaravana();
                    this.removerCaravanaVisual();
                }
                window.alertaEldora?.(
                    dados.concluido ? 'Provação da Caravana' : 'Defesa da Caravana',
                    texto,
                    'sucesso'
                );
                if (dados.concluido) {
                    window.setTimeout(() => window.mostrarDialogoRPG?.(
                        'A Voz da Estrada',
                        'Uma figura pálida surge por um instante onde a caravana estava. “A estrada… não me deixa partir.” A presença aponta para algo entre os destroços e desaparece. Volte ao Capitão Varek: ele sentirá que algo aconteceu e pedirá sua decisão.'
                    ), 450);
                }
            });

            this.socket.on('caravanaIAAtualizada', dados => {
                if (
                    String(dados?.owner_id || '') !==
                    String(localStorage.getItem('jogadorEldoraID') || '')
                ) return;
                this.caravanaIAEstado = dados;
                this.atualizarIntegridadeCaravana(dados.vida_caravana, dados.vida_maxima);
                (dados.mobs || []).forEach(mobEstado => {
                    const sprite = this.mobsNoMapa.getChildren().find(mob =>
                        String(mob.spawn_id) === String(mobEstado.spawn_id)
                    );
                    if (sprite) this.aplicarEstadoIACaravana(sprite, mobEstado);
                });
                if (dados.caravana_destruida && !this.caravanaQuestDestruida) {
                    this.caravanaQuestDestruida = true;
                    this.caravanaQuestViajanteSalvo = false;
                    this.acalmarViajanteCaravana();
                    this.caravanaQuestViajante?.setTint(0x777777);
                    this.caravanaQuestSocorro?.setText('CARAVANA DESTRUÍDA');
                    this.caravanaQuestSocorro?.setStyle({
                        backgroundColor: '#54242a',
                        color: '#ffe1d5',
                    });
                    window.alertaEldora?.(
                        'A caravana caiu',
                        'Os goblins destruíram a caravana. Saia da Pradaria e volte para tentar o resgate novamente.',
                        'erro'
                    );
                }
            });

            // 2. Apaga o monstro do mapa quando ele morre
            this.socket.on('mobMapaMorreu', (dados) => {
                this.removerMob(dados.spawn_id);
            });

            // 3. Mobs nascendo no tempo certo
            this.socket.on('mobMapaNasceu', (dados) => {

                let regiaoAtual =
                    this.scene.regiaoAtual
                    || localStorage.getItem(
                        "eldora_lastRegiao"
                    );

                // ==========================================
                // 🏰 FILTRO DE INSTÂNCIA DA DUNGEON
                // ==========================================
                if (
                    dados.regiao === "dungeon_01"
                    && dados.mob_data
                ) {

                    const mobData =
                        dados.mob_data;

                    const dungeonInstanceId =
                        String(
                            mobData.dungeon_instance_id
                            || dados.dungeon_instance_id
                            || ""
                        );

                    // Se for mob de instância da dungeon,
                    // precisamos confirmar que este jogador
                    // pertence àquela execução.
                    if (dungeonInstanceId) {

                        const userId =
                            String(
                                localStorage.getItem(
                                    "jogadorEldoraID"
                                )
                                || ""
                            );

                        const membros =
                            Array.isArray(
                                mobData.dungeon_members
                            )
                                ? mobData.dungeon_members.map(
                                    id => String(id)
                                )
                                : [];

                        if (
                            !userId
                            || !membros.includes(
                                userId
                            )
                        ) {

                            console.log(
                                "🏰 [DUNGEON] Spawn ignorado de outra instância:",
                                dungeonInstanceId
                            );

                            return;
                        }
                    }

                }

                // Só desenha se o jogador estiver
                // realmente no mesmo mapa.
                if (
                    regiaoAtual === dados.regiao
                ) {

                    this.spawnMob(
                        dados.mob_data
                    );
                }
            });

            this.socket.on('mobMapaAtualizado', (dados) => {
                const regiaoAtual = this.scene.regiaoAtual || localStorage.getItem("eldora_lastRegiao");
                if (!dados || dados.regiao !== regiaoAtual || !dados.mob_data) return;
                this.atualizarMobVisual(dados.mob_data);
            });

            // ==========================================
            // 🏆 DUNGEON 01 CONCLUÍDA
            // ==========================================
            this.socket.on(
                'dungeonConcluida',
                (dados) => {

                    if (
                        !dados
                        || dados.dungeon_id !== 'dungeon_01'
                    ) {
                        return;
                    }

                    const userId =
                        String(
                            localStorage.getItem(
                                'jogadorEldoraID'
                            )
                            || ''
                        );

                    const membros =
                        Array.isArray(
                            dados.membros
                        )
                            ? dados.membros.map(
                                id => String(id)
                            )
                            : [];

                    if (
                        !userId
                        || (
                            membros.length > 0
                            && !membros.includes(
                                userId
                            )
                        )
                    ) {
                        return;
                    }

                    if (
                        this.autoCacadaAtiva
                    ) {
                        this.pararAutoCacada(
                            'dungeon concluída',
                            true
                        );
                    }

                    const nomeDungeon =
                        dados.nome
                        || 'Catacumbas do Rei Caído';

                    const boss =
                        dados.boss
                        || 'Rei Caído';

                    const mensagem =
                        `👑 ${boss} foi derrotado!\n\n`
                        + `${nomeDungeon} foi concluída.`;

                    if (
                        typeof window.alertaEldora
                        === 'function'
                    ) {

                        window.alertaEldora(
                            '🏆 DUNGEON CONCLUÍDA',
                            mensagem,
                            'aviso'
                        );

                    } else if (
                        typeof window.avisoEldora
                        === 'function'
                    ) {

                        window.avisoEldora(
                            `🏆 DUNGEON CONCLUÍDA\n\n`
                            + mensagem
                        );

                    } else {

                        alert(
                            `🏆 DUNGEON CONCLUÍDA\n\n`
                            + mensagem
                        );
                    }

                    console.log(
                        '🏆 [DUNGEON] Execução concluída:',
                        dados.dungeon_instance_id
                    );
                }
            );
        }
    }

    mostrarCaravanaQuest(dados) {
        const textureKey = 'quest_caravana_varek';
        const animKey = 'quest_caravana_varek_marcha';
        const viajanteTextureKey = 'npc_elara';
        const viajanteAnimKey = 'quest_elara_caravana_espera';
        this.caravanaIAEstado = {
            vida_caravana: Number(dados.vida_caravana ?? 300),
            vida_maxima: Number(dados.vida_maxima ?? 300),
        };
        this.caravanaQuestViajanteSalvo =
            Number(dados.mob_atual || 0) >= Number(dados.mob_total || 1);
        this.caravanaQuestDestruida = false;
        const desenhar = () => {
            this.removerCaravanaVisual();
            this.removerViajanteCaravana();

            const cena = this.scene;
            if (!this.caravanaQuestViajanteSalvo) {
                const sprite = cena.add.sprite(dados.x, dados.y, textureKey, 0)
                    .setDisplaySize(96, 144)
                    .setOrigin(0.5, 0.5)
                    .setDepth(cena.calcularProfundidadeAtor
                        ? cena.calcularProfundidadeAtor({
                            x: dados.x,
                            y: dados.y,
                            displayHeight: 144,
                            originY: 0.5,
                        })
                        : 14);

                cena.physics.add.existing(sprite, true);
                // A carroça passa devagar pelo trecho da estrada onde ocorreu a
                // emboscada. O corpo segue o sprite para manter a colisão alinhada.
                sprite.body.setSize(288, 96).setOffset(112, 560);
                sprite.body.updateFromGameObject();
                if (cena.player) cena.physics.add.collider(cena.player, sprite);
                if (!cena.anims.exists(animKey)) {
                    cena.anims.create({
                        key: animKey,
                        frames: cena.anims.generateFrameNumbers(textureKey, { start: 0, end: 3 }),
                        frameRate: 5,
                        repeat: -1,
                    });
                }
                sprite.play(animKey);
                this.caravanaQuestSprite = sprite;

                this.caravanaQuestMovimiento = cena.tweens.add({
                    targets: sprite,
                    y: dados.y - 40,
                    duration: 2400,
                    ease: 'Sine.easeInOut',
                    yoyo: true,
                    repeat: -1,
                    onUpdate: () => {
                        if (!sprite.active || !sprite.body) return;
                        sprite.body.updateFromGameObject();
                        sprite.setDepth(cena.calcularProfundidadeAtor
                            ? cena.calcularProfundidadeAtor({
                                x: sprite.x,
                                y: sprite.y,
                                displayHeight: 144,
                                originY: 0.5,
                            })
                            : sprite.y);
                    },
                });
            }

            const mostrarViajante = () => {
                const viajante = cena.add.sprite(dados.x, dados.y + 104, viajanteTextureKey, 1)
                    .setDisplaySize(48, 48)
                    .setDepth(dados.y + 120);
                if (!cena.anims.exists(viajanteAnimKey)) {
                    cena.anims.create({
                        key: viajanteAnimKey,
                        frames: cena.anims.generateFrameNumbers(viajanteTextureKey, { start: 0, end: 2 }),
                        frameRate: 4,
                        repeat: -1,
                    });
                }
                viajante.play(viajanteAnimKey);
                viajante.setInteractive({ useHandCursor: true });
                viajante.on('pointerdown', () => {
                    window.mostrarDialogoRPG?.(
                        'Elara, Viajante da Caravana',
                        this.caravanaQuestViajanteSalvo
                            ? 'Obrigado por me salvar. Agora a estrada está segura.'
                            : 'Os goblins estão me cercando! Afaste-os da carroça, por favor!'
                    );
                });
                this.caravanaQuestViajante = viajante;
                if (!this.caravanaQuestViajanteSalvo) {
                    this.caravanaQuestIntegridade = cena.add.text(
                        viajante.x,
                        viajante.y + 28,
                        `CARAVANA ${Number(dados.vida_caravana ?? 300)}/${Number(dados.vida_maxima ?? 300)}`,
                        {
                            fontFamily: 'Arial',
                            fontSize: '10px',
                            fontStyle: 'bold',
                            color: '#f4ead2',
                            backgroundColor: '#102128',
                            padding: { x: 5, y: 3 },
                            stroke: '#071115',
                            strokeThickness: 3,
                        }
                    ).setOrigin(0.5).setDepth(1000);
                }
                if (this.caravanaQuestViajanteSalvo) {
                    const agradecimento = cena.add.text(
                        viajante.x,
                        viajante.y - 32,
                        'OBRIGADO!',
                        {
                            fontFamily: 'Arial',
                            fontSize: '11px',
                            fontStyle: 'bold',
                            color: '#f4ead2',
                            backgroundColor: '#256044',
                            padding: { x: 6, y: 3 },
                            stroke: '#18241c',
                            strokeThickness: 3,
                        }
                    ).setOrigin(0.5).setDepth(1000);
                    this.caravanaQuestSocorro = agradecimento;
                    return;
                }

                this.caravanaQuestViajanteAnim = cena.tweens.add({
                    targets: viajante,
                    x: viajante.x + 3,
                    angle: 2,
                    duration: 220,
                    yoyo: true,
                    repeat: -1,
                    ease: 'Sine.easeInOut',
                });

                const socorro = cena.add.text(viajante.x, viajante.y - 32, 'SOCORRO!', {
                    fontFamily: 'Arial',
                    fontSize: '12px',
                    fontStyle: 'bold',
                    color: '#fff1d4',
                    backgroundColor: '#8b2635',
                    padding: { x: 6, y: 3 },
                    stroke: '#241217',
                    strokeThickness: 3,
                }).setOrigin(0.5).setDepth(1000);
                this.caravanaQuestSocorro = socorro;
                this.caravanaQuestSocorroAnim = cena.tweens.add({
                    targets: socorro,
                    y: socorro.y - 6,
                    alpha: 0.65,
                    duration: 550,
                    yoyo: true,
                    repeat: -1,
                });
                if (this.caravanaIAEstado && !this.caravanaQuestViajanteSalvo) {
                    this.atualizarIntegridadeCaravana(
                        this.caravanaIAEstado.vida_caravana,
                        this.caravanaIAEstado.vida_maxima
                    );
                }
            };

            mostrarViajante();
        };

        if (
            this.scene.textures.exists(textureKey)
            && this.scene.textures.exists(viajanteTextureKey)
        ) {
            desenhar();
            return;
        }

        const loader = this.scene.load;
        if (!this.scene.textures.exists(textureKey)) {
            loader.spritesheet(
                textureKey,
                '/static/assets/npcs/caravana_provacao_walk.png',
                { frameWidth: 512, frameHeight: 768 }
            );
        }
        if (!this.scene.textures.exists(viajanteTextureKey)) {
            loader.spritesheet(
                viajanteTextureKey,
                '/static/assets/npcs/npc_elara.png',
                { frameWidth: 48, frameHeight: 48 }
            );
        }
        loader.once('complete', desenhar);
        loader.start();
    }

    removerCaravanaVisual() {
        this.caravanaQuestMovimiento?.stop();
        this.caravanaQuestSprite?.destroy();
        this.caravanaQuestMovimiento = null;
        this.caravanaQuestSprite = null;
    }

    atualizarIntegridadeCaravana(vida, maxima) {
        if (!this.caravanaQuestIntegridade?.active) return;
        const atual = Math.max(0, Number(vida ?? 100));
        const total = Math.max(1, Number(maxima ?? 100));
        this.caravanaQuestIntegridade.setText(`CARAVANA ${atual}/${total}`);
        this.caravanaQuestIntegridade.setColor(atual <= total * 0.3 ? '#ff8b78' : '#f4ead2');
    }

    aplicarEstadoIACaravana(sprite, estado) {
        if (!sprite?.active || !estado) return;

        sprite.mobData = {
            ...(sprite.mobData || {}),
            x: estado.x,
            y: estado.y,
            ai_state: estado.estado,
        };
        sprite.caravanaAIMovimento?.stop();
        sprite.caravanaAIMovimento = this.scene.tweens.add({
            targets: sprite,
            x: Number(estado.x),
            y: Number(estado.y),
            duration: 240,
            ease: 'Linear',
            onUpdate: () => {
                if (!sprite.active) return;
                sprite.indicadorAlvo?.setPosition(sprite.x, sprite.y - 30);
                sprite.corruptionAura?.setPosition(sprite.x, sprite.y);
                if (this.scene.calcularProfundidadeAtor) {
                    sprite.setDepth(this.scene.calcularProfundidadeAtor({
                        x: sprite.x,
                        y: sprite.y,
                        displayHeight: sprite.displayHeight || 48,
                        originY: 0.5,
                    }));
                }
            },
        });

        const sequencia = Number(estado.sequencia_ataque || 0);
        if (estado.ataque && sequencia > Number(sprite.caravanaUltimoGolpe || 0)) {
            sprite.caravanaUltimoGolpe = sequencia;
            this.animarGolpeNaCaravana(sprite);
        }
    }

    animarGolpeNaCaravana(spriteAtacante) {
        const viajante = this.caravanaQuestViajante;
        if (!viajante?.active) return;

        viajante.setTint(0xff7777);
        this.scene.time.delayedCall(180, () => {
            if (viajante.active) viajante.clearTint();
        });

        const impacto = this.scene.add.text(
            viajante.x + Phaser.Math.Between(-10, 10),
            viajante.y - 18,
            '✦',
            {
                fontFamily: 'Arial',
                fontSize: '24px',
                fontStyle: 'bold',
                color: '#ff5b61',
                stroke: '#42151b',
                strokeThickness: 4,
            }
        ).setOrigin(0.5).setDepth(1001);

        this.scene.tweens.add({
            targets: impacto,
            y: impacto.y - 20,
            alpha: 0,
            scale: 1.25,
            duration: 360,
            onComplete: () => impacto.destroy(),
        });
        if (spriteAtacante?.active) spriteAtacante.setTint(0xffb6a6);
        this.scene.time.delayedCall(180, () => {
            if (spriteAtacante?.active) spriteAtacante.clearTint();
        });
    }

    removerViajanteCaravana() {
        this.caravanaQuestViajanteAnim?.stop();
        this.caravanaQuestSocorroAnim?.stop();
        this.caravanaQuestViajante?.destroy();
        this.caravanaQuestSocorro?.destroy();
        this.caravanaQuestIntegridade?.destroy();
        this.caravanaQuestViajanteAnim = null;
        this.caravanaQuestViajante = null;
        this.caravanaQuestSocorro = null;
        this.caravanaQuestIntegridade = null;
        this.caravanaQuestSocorroAnim = null;
    }

    acalmarViajanteCaravana() {
        this.caravanaQuestViajanteAnim?.stop();
        this.caravanaQuestSocorroAnim?.stop();
        this.caravanaQuestViajante?.setAngle(0);
        this.caravanaQuestIntegridade?.destroy();
        this.caravanaQuestIntegridade = null;
        if (!this.caravanaQuestDestruida && this.caravanaQuestSocorro?.active) {
            this.caravanaQuestSocorro.setText('OBRIGADO!');
            this.caravanaQuestSocorro.setPosition(
                this.caravanaQuestViajante?.x ?? this.caravanaQuestSocorro.x,
                (this.caravanaQuestViajante?.y ?? this.caravanaQuestSocorro.y) - 32
            );
            this.caravanaQuestSocorro.setStyle({
                backgroundColor: '#256044',
                color: '#f4ead2',
            });
        }
        this.caravanaQuestViajanteAnim = null;
        this.caravanaQuestSocorroAnim = null;
    }

    pararAutoCacada(motivo = "cancelado", pararMovimento = true) {
        this.autoCacadaAtiva = false;
        this.autoCacadaAlvo = null;
        this.autoCacadaSpawnId = null;
        this.autoCacadaUltimaPosicao = null;
        this.autoCacadaTempoParado = 0;
        this.autoCacadaPausadaPorCombate = false;
        this.autoCacadaRetomando = false;
        this.autoCacadaUltimoReenvioMovimento = 0;
        this.autoCacadaIgnorarSpawnIds = {};

        if (pararMovimento && this.scene && typeof this.scene.pararPersonagem === "function") {
            this.scene.pararPersonagem();
        }

        this.atualizarBotaoAutoCacada();

        console.log("🛑 [AUTO CAÇADA] Parada:", motivo);
    }

    atualizarBotaoAutoCacada() {
        const btn = document.getElementById("btn-teste-auto-cacada");
        if (!btn) return;

        if (this.autoCacadaAtiva) {
            btn.classList.add("auto-cacada-ativo");
            btn.title = "Parar Auto Caçada";
        } else {
            btn.classList.remove("auto-cacada-ativo");
            btn.title = "Iniciar Auto Caçada";
        }

        this.atualizarVisibilidadeBotaoAutoCacada();
    }

    atualizarVisibilidadeBotaoAutoCacada() {
        const btn = document.getElementById("btn-teste-auto-cacada");
        if (!btn) return;

        const abaReino = document.getElementById("aba-reino");
        const estaNoMapa =
            abaReino &&
            abaReino.classList.contains("active");

        const telaCombate = document.getElementById("tela-combate-global");
        const combateAberto =
            telaCombate &&
            telaCombate.style.display !== "none" &&
            getComputedStyle(telaCombate).display !== "none";

        // Se quiser mostrar no combate de caçada, deixa true quando a tela de combate estiver aberta.
        const estaEmCombateCacada =
            combateAberto &&
            window.dadosCombateAtual &&
            !window.salaCombateGrupoAtual &&
            !window.estadoCombateGrupoAtual &&
            !window.raidInvasaoAtual;

        const menuAberto =
            document.body.classList.contains("menu-aberto") ||
            document.body.classList.contains("ui-modal-aberta") ||
            document.getElementById("side-menu")?.classList.contains("aberto") ||
            document.getElementById("menu-overlay")?.classList.contains("ativo");

        const idsBloqueadores = [
            "hub-social",
            "modal-editar-perfil",
            "modal-ver-perfil",
            "menu-inspecao",
            "rpg-dialogo-container",
            "forja-container",
            "refinaria-container",
            "mercado-container",
            "loja-reino-container",
            "loja-aventureiro-container",
            "tela-raid-invasao",
            "tela-pvp-global"
        ];

        const algumaUiAberta = idsBloqueadores.some(id => {
            const el = document.getElementById(id);
            if (!el) return false;

            const display = getComputedStyle(el).display;
            return display !== "none" && el.style.display !== "none";
        });

        const podeMostrar =
            (estaNoMapa || estaEmCombateCacada) &&
            !menuAberto &&
            !algumaUiAberta;

        btn.style.display = podeMostrar ? "flex" : "none";
    }

    pausarAutoCacadaPorCombate() {
        if (!this.autoCacadaAtiva) return;

        this.autoCacadaPausadaPorCombate = true;
        this.autoCacadaAlvo = null;
        this.autoCacadaSpawnId = null;
        this.autoCacadaUltimaPosicao = null;
        this.autoCacadaTempoParado = 0;

        if (this.scene && typeof this.scene.pararPersonagem === "function") {
            this.scene.pararPersonagem();
        }

        this.atualizarBotaoAutoCacada();

        console.log("⏸️ [AUTO CAÇADA] Pausada por combate.");
    }

    retomarAutoCacadaDepoisCombate() {
        if (!this.autoCacadaAtiva) return;
        if (this.autoCacadaRetomando) return;

        this.autoCacadaRetomando = true;

        setTimeout(() => {
            this.autoCacadaRetomando = false;

            if (!this.autoCacadaAtiva) return;

            const player = this.scene && this.scene.player ? this.scene.player : null;

            if (!player) {
                this.pararAutoCacada("player não encontrado ao retomar", false);
                return;
            }

            if (this.scene.isDead) {
                this.pararAutoCacada("jogador morto ao retomar", true);
                return;
            }

            if (player.isGathering) {
                this.pararAutoCacada("coleta ativa ao retomar", true);
                return;
            }

            const telaCombate = document.getElementById("tela-combate-global");
            const combateAberto =
                telaCombate &&
                telaCombate.style.display !== "none" &&
                getComputedStyle(telaCombate).display !== "none";

            if (combateAberto) {
                console.log("⏳ [AUTO CAÇADA] Ainda em combate, aguardando...");
                this.retomarAutoCacadaDepoisCombate();
                return;
            }

            this.autoCacadaPausadaPorCombate = false;

            console.log("▶️ [AUTO CAÇADA] Retomando busca pelo próximo mob.");

            this.iniciarAutoCacada();
        }, 900);
    }

    encontrarMobMaisProximo() {
        const player = this.scene && this.scene.player ? this.scene.player : null;

        if (!player || !this.mobsNoMapa) {
            console.warn("⚠️ [AUTO CAÇADA] Player ou grupo de mobs não encontrado.");
            return null;
        }

        const mobsValidos = this.mobsNoMapa.getChildren().filter(mob => {
            if (!mob) return false;
            if (!(mob instanceof Phaser.GameObjects.Sprite)) return false;
            if (!mob.active || !mob.visible) return false;
            if (!mob.spawn_id) return false;

            // Se esse mob travou o caminho recentemente, ignora por alguns segundos.
            const chaveSpawn = String(mob.spawn_id);
            const ignorarAte = Number((this.autoCacadaIgnorarSpawnIds || {})[chaveSpawn] || 0);

            if (ignorarAte > Date.now()) {
                return false;
            }

            if (ignorarAte && ignorarAte <= Date.now()) {
                delete this.autoCacadaIgnorarSpawnIds[chaveSpawn];
            }

            const dadosMob = mob.mobData || {};

            // Segurança: por enquanto ignora possíveis mobs de evento/invasão/raid.
            const origem = String(
                dadosMob.origem ||
                dadosMob.tipo_evento ||
                dadosMob.tipo ||
                ""
            ).toLowerCase();

            if (
                dadosMob.invasao ||
                dadosMob.raid ||
                dadosMob.is_raid ||
                dadosMob.is_event ||
                dadosMob.evento === true ||
                origem.includes("invasao") ||
                origem.includes("invasão") ||
                origem.includes("raid") ||
                origem.includes("evento")
            ) {
                return false;
            }

            return true;
        });

        if (mobsValidos.length === 0) {
            console.log("🔎 [AUTO CAÇADA] Nenhum mob válido encontrado no mapa.");
            return null;
        }

        let mobMaisProximo = null;
        let menorDistancia = Infinity;

        mobsValidos.forEach(mob => {
            const distancia = Phaser.Math.Distance.Between(
                player.x,
                player.y,
                mob.x,
                mob.y
            );

            if (distancia < menorDistancia) {
                menorDistancia = distancia;
                mobMaisProximo = mob;
            }
        });

        if (mobMaisProximo) {
            console.log("🎯 [AUTO CAÇADA] Mob mais próximo encontrado:", {
                spawn_id: mobMaisProximo.spawn_id,
                monster_id: mobMaisProximo.mobData ? mobMaisProximo.mobData.monster_id : null,
                distancia: Math.round(menorDistancia)
            });
        }

        return mobMaisProximo;
    }

    iniciarAutoCacada() {
        const player = this.scene && this.scene.player ? this.scene.player : null;

        if (!player) {
            this.mostrarAvisoAutoCacada("Auto Caçada", "Personagem não encontrado.", "erro");
            return false;
        }

        if (this.scene.isDead) {
            this.mostrarAvisoAutoCacada("Auto Caçada", "Você não pode caçar enquanto está morto.", "erro");
            return false;
        }

        if (player.isGathering) {
            this.mostrarAvisoAutoCacada("Auto Caçada", "Você está coletando agora.", "aviso");
            return false;
        }

        const telaCombate = document.getElementById("tela-combate-global");
        const combateAberto =
            telaCombate &&
            telaCombate.style.display !== "none" &&
            getComputedStyle(telaCombate).display !== "none";

        if (combateAberto) {
            this.mostrarAvisoAutoCacada("Auto Caçada", "Você já está em combate.", "aviso");
            return false;
        }

        if (window.salaCombateGrupoAtual || window.estadoCombateGrupoAtual) {
            this.mostrarAvisoAutoCacada("Auto Caçada", "Auto Caçada não inicia em combate de grupo.", "aviso");
            return false;
        }

        const caixaDialogo = document.getElementById("rpg-dialogo-container");
        if (caixaDialogo && caixaDialogo.style.display === "block") {
            this.mostrarAvisoAutoCacada("Auto Caçada", "Feche o diálogo antes de caçar.", "aviso");
            return false;
        }

        this.autoCacadaPausadaPorCombate = false;

        const mob = this.encontrarMobMaisProximo();

        if (!mob) {

            this.mostrarAvisoAutoCacada("Auto Caçada", "Nenhum mob válido encontrado neste mapa.", "aviso");
            this.pararAutoCacada("sem mobs", false);
            return false;
        }

        this.autoCacadaAtiva = true;
        this.autoCacadaAlvo = mob;
        this.autoCacadaSpawnId = mob.spawn_id;
        const distanciaInicial = Phaser.Math.Distance.Between(
            player.x,
            player.y,
            mob.x,
            mob.y
        );

        this.autoCacadaUltimaPosicao = {
            x: player.x,
            y: player.y,
            tempo: Date.now(),
            distancia: distanciaInicial
        };
        this.autoCacadaTempoParado = 0;
        this.autoCacadaUltimoReenvioMovimento = Date.now();

        this.scene.target.set(mob.x, mob.y);
        this.scene.isMoving = true;
        this.scene.physics.moveToObject(player, this.scene.target, 150);

        this.atualizarBotaoAutoCacada();

        const monsterId = mob.mobData && mob.mobData.monster_id ? mob.mobData.monster_id : "mob";

        // Não mostra alerta aqui.
        // No Telegram, alertaEldora abre modal e trava a movimentação automática.
        console.log("🤖 [AUTO CAÇADA] Indo até o mob:", {
            spawn_id: mob.spawn_id,
            monster_id: monsterId
        });

        return true;
    }

    verificarAutoCacada() {
        if (!this.autoCacadaAtiva) return;
        if (this.autoCacadaPausadaPorCombate) return;

        const player = this.scene && this.scene.player ? this.scene.player : null;
        const alvo = this.autoCacadaAlvo;

        if (!player) {
            this.pararAutoCacada("player não encontrado", false);
            return;
        }

        if (this.scene.isDead) {
            this.pararAutoCacada("jogador morto", true);
            return;
        }

        if (player.isGathering) {
            this.pararAutoCacada("coleta iniciada", true);
            return;
        }

        const telaCombate = document.getElementById("tela-combate-global");
        const combateAberto =
            telaCombate &&
            telaCombate.style.display !== "none" &&
            getComputedStyle(telaCombate).display !== "none";

        if (combateAberto) {
            this.pararAutoCacada("combate já aberto", false);
            return;
        }

        if (!alvo || !alvo.active || !alvo.visible || !alvo.spawn_id) {
            this.pararAutoCacada("alvo inválido ou removido", true);
            return;
        }

        const distancia = Phaser.Math.Distance.Between(
            player.x,
            player.y,
            alvo.x,
            alvo.y
        );

        if (distancia > this.autoCacadaDistanciaAtaque) {
            const agora = Date.now();

            // Se o Phaser parou o personagem antes de chegar no mob,
            // reenviamos o movimento de tempos em tempos.
            const vx = player.body && player.body.velocity ? player.body.velocity.x : 0;
            const vy = player.body && player.body.velocity ? player.body.velocity.y : 0;

            const paradoSemChegar =
                !this.scene.isMoving ||
                (Math.abs(vx) < 5 && Math.abs(vy) < 5);

            if (
                paradoSemChegar &&
                agora - Number(this.autoCacadaUltimoReenvioMovimento || 0) > 800
            ) {
                this.scene.target.set(alvo.x, alvo.y);
                this.scene.isMoving = true;
                this.scene.physics.moveToObject(player, this.scene.target, 150);
                this.autoCacadaUltimoReenvioMovimento = agora;

                console.log("🔁 [AUTO CAÇADA] Reenviando movimento até o alvo:", alvo.spawn_id);
            }

            // Detecta se ficou preso por alguns segundos.
            const ultima = this.autoCacadaUltimaPosicao;

            if (ultima && agora - Number(ultima.tempo || 0) >= 1200) {
                const deslocamento = Phaser.Math.Distance.Between(
                    player.x,
                    player.y,
                    ultima.x,
                    ultima.y
                );

                const distanciaAnterior = Number(ultima.distancia || distancia);
                const aproximou = distancia < distanciaAnterior - 6;

                if (deslocamento < 8 && !aproximou) {
                    this.autoCacadaTempoParado += agora - Number(ultima.tempo || agora);
                } else {
                    this.autoCacadaTempoParado = 0;
                }

                this.autoCacadaUltimaPosicao = {
                    x: player.x,
                    y: player.y,
                    tempo: agora,
                    distancia: distancia
                };
            }

            if (this.autoCacadaTempoParado >= 3500) {
                const spawnTravado = String(alvo.spawn_id);

                // Ignora esse mob por 12 segundos para não escolher o mesmo alvo travado.
                this.autoCacadaIgnorarSpawnIds[spawnTravado] = Date.now() + 12000;

                console.warn("⚠️ [AUTO CAÇADA] Caminho travado. Procurando outro mob:", spawnTravado);

                this.autoCacadaAlvo = null;
                this.autoCacadaSpawnId = null;
                this.autoCacadaUltimaPosicao = null;
                this.autoCacadaTempoParado = 0;
                this.autoCacadaUltimoReenvioMovimento = 0;

                this.iniciarAutoCacada();
                return;
            }

            return;
        }

        const spawnId = alvo.spawn_id;
        const monsterId = alvo.mobData && alvo.mobData.monster_id ? alvo.mobData.monster_id : "mob";

        this.pausarAutoCacadaPorCombate();

        console.log("⚔️ [AUTO CAÇADA] Iniciando batalha contra:", {
            spawn_id: spawnId,
            monster_id: monsterId
        });

        if (typeof window.iniciarCacadaApp === "function") {
            window.iniciarCacadaApp(spawnId, {
                autoCacada: true,
                mobData: alvo.mobData || {}
            });
        } else {
            console.error("ERRO: window.iniciarCacadaApp não encontrada.");
            this.mostrarAvisoAutoCacada(
                "Auto Caçada",
                "Erro: função de combate não encontrada.",
                "erro"
            );
        }
    }

    mostrarAvisoAutoCacada(titulo, mensagem, tipo = "aviso") {

        if (typeof window.alertaEldora === "function") {
            window.alertaEldora(titulo, mensagem, tipo);
        } else {
            window.avisoEldora(`${titulo}\n${mensagem}`);
        }
    }

    instalarEstiloBotaoAutoCacada() {
        if (document.getElementById("style-botao-auto-cacada")) return;

        const style = document.createElement("style");
        style.id = "style-botao-auto-cacada";

        style.innerHTML = `
            #btn-teste-auto-cacada {
                --auto-bot-size: 42px;

                position: fixed;
                right: 12px;
                bottom: 92px;
                z-index: 80;

                width: 48px;
                height: 48px;
                padding: 0;

                display: flex;
                align-items: center;
                justify-content: center;

                background: transparent;
                border: none;
                border-radius: 0;
                box-shadow: none;

                cursor: pointer;
                overflow: visible;
                touch-action: manipulation;
            }

            #btn-teste-auto-cacada .auto-cacada-icone {
                width: var(--auto-bot-size);
                height: var(--auto-bot-size);

                background-image: url("https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/ui/botst.png?v=2");
                background-repeat: no-repeat;
                background-position: center;
                background-size: contain;

                pointer-events: none;
                filter: drop-shadow(0 2px 4px rgba(0,0,0,.55));
            }

            #btn-teste-auto-cacada.auto-cacada-ativo .auto-cacada-icone {
                background-image: url("https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/ui/botanim.png?v=2");
                background-position: 0 0;
                background-size: auto var(--auto-bot-size);
                animation: autoCacadaBotAnim 0.75s steps(6) infinite;
                filter:
                    drop-shadow(0 0 6px rgba(59,130,246,.55))
                    drop-shadow(0 2px 4px rgba(0,0,0,.55));
            }

            @keyframes autoCacadaBotAnim {
                from {
                    background-position: 0 0;
                }
                to {
                    background-position: calc(var(--auto-bot-size) * -6) 0;
                }
            }

            #btn-teste-auto-cacada:active {
                transform: scale(0.92);
            }
        `;

        document.head.appendChild(style);
    }

    async criarBotaoTesteAutoCacada() {
        this.instalarEstiloBotaoAutoCacada();

        let btn = document.getElementById("btn-teste-auto-cacada");

        const userId =
            localStorage.getItem(
                "jogadorEldoraID"
            );

        if (!userId) {
            if (btn) {
                btn.remove();
            }

            return;
        }

        try {
            const resposta = await fetch(
                `/api/premium/catalogo/${encodeURIComponent(userId)}?t=${Date.now()}`,
                {
                    cache: "no-store"
                }
            );

            const dados =
                await resposta.json();

            const premiumAtivo =
                resposta.ok &&
                dados.success &&
                dados.eldora_premium?.ativo === true &&
                dados.premium?.auto_cacada === true;

            if (!premiumAtivo) {
                if (btn) {
                    btn.remove();
                }

                return;
            }

        } catch (erro) {
            console.error(
                "❌ [AUTO CAÇADA] Falha ao carregar acesso Premium:",
                erro
            );

            if (btn) {
                btn.remove();
            }

            return;
        }

        if (!btn) {
            btn = document.createElement("button");
            btn.id = "btn-teste-auto-cacada";
            btn.type = "button";
            btn.title = "Iniciar Auto Caçada";
            btn.innerHTML = `<div class="auto-cacada-icone"></div>`;

            document.body.appendChild(btn);
        }

        btn.onclick = async (event) => {
            if (event) {
                event.preventDefault();
                event.stopPropagation();
            }

            if (this.autoCacadaAtiva) {
                this.pararAutoCacada("parada manualmente", true);
                return;
            }

            const userId =
                localStorage.getItem(
                    "jogadorEldoraID"
                );

            if (!userId) {
                this.mostrarAvisoAutoCacada(
                    "Auto Caçada",
                    "Herói não encontrado.",
                    "erro"
                );
                return;
            }

            try {
                const resposta = await fetch(
                    `/api/premium/catalogo/${encodeURIComponent(userId)}?t=${Date.now()}`,
                    {
                        cache: "no-store"
                    }
                );

                const dados =
                    await resposta.json();

                const premiumAtivo =
                    resposta.ok &&
                    dados.success &&
                    dados.eldora_premium?.ativo === true &&
                    dados.premium?.auto_cacada === true;

                if (!premiumAtivo) {
                    this.mostrarAvisoAutoCacada(
                        "Eldora Premium",
                        "👑 Auto Caçada é exclusiva do Eldora Premium.",
                        "aviso"
                    );
                    return;
                }

            } catch (erro) {
                console.error(
                    "❌ [AUTO CAÇADA] Falha ao validar Premium:",
                    erro
                );

                this.mostrarAvisoAutoCacada(
                    "Auto Caçada",
                    "Não foi possível validar seu Eldora Premium.",
                    "erro"
                );
                return;
            }

            this.iniciarAutoCacada();
        };

        this.atualizarBotaoAutoCacada();

        // Mantém o ícone escondido quando abrir menu, perfil, forja, mercado etc.
        if (!this._autoCacadaVisibilidadeTimer) {
            this._autoCacadaVisibilidadeTimer = setInterval(() => {
                this.atualizarVisibilidadeBotaoAutoCacada();
            }, 300);
        }
    }

    spawnMob(mobData) {

        this.removerMob(mobData.spawn_id);

        if (
            mobData.quest_event_id === 'q3_varek_provacao'
            && typeof window.preloadImagemCombate === 'function'
        ) {
            const pastaCombate = mobData.asset_region || 'floresta';
            const imagemCombate = `https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/mob/combate/${pastaCombate}/${mobData.monster_id || 'goblin_batedor'}.png`;
            window.preloadImagemCombate(imagemCombate).catch(erro => {
                console.warn('A imagem do Goblin Batedor será tentada novamente ao iniciar o combate.', erro);
            });
        }
        
        let regiaoAtual = this.scene.regiaoAtual || localStorage.getItem("eldora_lastRegiao") || "capital_eldora";

        // ==========================================
        // 🗺️ O TRADUTOR DE PASTAS DEFINITIVO 🗺️
        // ==========================================
        // Ensina para o código qual é o nome exato da pasta no GitHub para cada mapa!
        const tradutorPastas = {
            "capital_eldora": "capital",             // O mapa capital_eldora usa a pasta 'capital'
            "pradaria_inicial": "pradaria_inicial",  // O mapa pradaria_inicial usa a pasta 'pradaria_inicial'
            "floresta_sombria": "floresta",           // (Exemplo futuro) A floresta usa a pasta 'floresta'
        };

        // Ele busca no tradutor. Se não tiver no tradutor, ele tenta usar o próprio nome da região.
        let pastaRegiao = mobData.asset_region || tradutorPastas[regiaoAtual] || regiaoAtual;

        // Monta o link apontando para a pasta traduzida!
        const linkNuvem = `https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/mob/${pastaRegiao}/`;
        
        const textureKey = `ss_mob_${pastaRegiao}_${mobData.monster_id}`;

        if (!this.scene.textures.exists(textureKey)) {
            
            this.scene.load.spritesheet(
                textureKey,
                `${linkNuvem}${mobData.monster_id}.png`,
                {
                    frameWidth: 256,
                    frameHeight: 256
                }
            );
            
            this.scene.load.once(`filecomplete-spritesheet-${textureKey}`, () => {
                this.desenharSprite(mobData, textureKey);
            });

            this.scene.load.once('loaderror', (fileObj) => {
                if(fileObj.key === textureKey) {
                    window.avisoEldora("❌ Link não encontrado no GitHub:\n" + fileObj.url);
                }
            });

            this.scene.load.start();
        } else {
            this.desenharSprite(mobData, textureKey);
        }
    }

    aplicarAuraCorrompida(sprite, mobData) {
        if (!sprite || !sprite.scene) return;
        if (!mobData || mobData.corrupted !== true) {
            if (sprite.corruptionAura) sprite.corruptionAura.destroy();
            sprite.corruptionAura = null;
            return;
        }
        if (sprite.corruptionAura && sprite.corruptionAura.active) return;

        const ehBoss = mobData.is_boss === true || mobData.boss === true || mobData.dungeon_boss === true;
        const tamanho = ehBoss ? 148 : 62;
        const aura = this.scene.add.ellipse(
            sprite.x,
            sprite.y,
            tamanho,
            tamanho,
            0x8b3dff,
            0.20
        ).setStrokeStyle(ehBoss ? 4 : 2, 0xc084fc, 0.9).setDepth((sprite.depth || 14) - 1);

        sprite.corruptionAura = aura;
        this.scene.tweens.add({
            targets: aura,
            alpha: 0.38,
            scaleX: 1.12,
            scaleY: 1.14,
            duration: 850,
            yoyo: true,
            repeat: -1,
            ease: 'Sine.easeInOut'
        });
    }

    atualizarMobVisual(mobData) {
        const sprite = this.mobsNoMapa.getChildren().find(mob =>
            mob instanceof Phaser.GameObjects.Sprite && String(mob.spawn_id) === String(mobData.spawn_id)
        );
        if (!sprite) {
            this.spawnMob(mobData);
            return;
        }
        sprite.mobData = mobData;
        this.aplicarAuraCorrompida(sprite, mobData);
    }

    desenharSprite(mobData, textureKey) {
        try {
            // ==========================================
            // 👹 TAMANHO DOS MOBS NO MAPA
            // Mob normal = 48x48
            // Boss       = 128x128
            // ==========================================

            const ehBoss =
                mobData.is_boss === true ||
                mobData.boss === true ||
                String(mobData.tipo || '').toLowerCase() === 'boss';

            const tamanhoMob = ehBoss ? 128 : 48;

            let sprite = this.scene.add.sprite(
                mobData.x,
                mobData.y,
                textureKey,
                0
            ).setDepth(
                this.scene.calcularProfundidadeAtor
                    ? this.scene.calcularProfundidadeAtor({
                        x: mobData.x,
                        y: mobData.y,
                        displayHeight: tamanhoMob,
                        originY: 0.5
                    })
                    : 14
            );

            sprite.setDisplaySize(
                tamanhoMob,
                tamanhoMob
            );

            sprite.spawn_id = mobData.spawn_id;
            sprite.mobData = mobData;
            sprite.spawn_id = mobData.spawn_id;

            // Guarda os dados originais do mob dentro do sprite.
            // Isso será usado pela Auto Caçada para saber qual mob perseguir.
            sprite.mobData = mobData;

            let totalFrames =
                this.scene.textures.get(
                    textureKey
                ).frameTotal;

            // ==========================================
            // 🎞️ ANIMAÇÃO IDLE — 6 FRAMES
            // ==========================================
            if (totalFrames >= 6) {

                const animKey =
                    `${textureKey}_idle`;

                if (
                    !this.scene.anims.exists(
                        animKey
                    )
                ) {

                    this.scene.anims.create({
                        key:
                            animKey,

                        frames:
                            this.scene.anims.generateFrameNumbers(
                                textureKey,
                                {
                                    start: 0,
                                    end: 5
                                }
                            ),

                        frameRate: 6,

                        repeat: -1
                    });
                }

                sprite.play(
                    animKey
                );
            }

            // ==========================================
            // 🏹 SETA FLUTUANTE (Substitui o Texto)
            // ==========================================
            const offsetSeta = ehBoss ? 75 : 30;

            sprite.indicadorAlvo = this.scene.add.text(
                mobData.x,
                mobData.y - offsetSeta,
                '▼',
                {
                    fontSize: '18px',
                    color: '#ff4757',
                    stroke: '#000',
                    strokeThickness: 3
                }
            ).setOrigin(0.5).setDepth(30);

            // Animação da seta flutuando (sobe e desce sem parar)
            this.scene.tweens.add({
                targets: sprite.indicadorAlvo,
                y: mobData.y - offsetSeta + 8,
                duration: 600,
                yoyo: true,
                repeat: -1,
                ease: 'Sine.easeInOut'
            });

            // ==========================================
            // 👇 MÁGICA DA HITBOX E TRAVA DE DISTÂNCIA 👇
            // ==========================================
            sprite.setInteractive({ useHandCursor: true });
            sprite.input.hitArea.setTo(0, 0, sprite.width || 48, sprite.height || 48);
            
            sprite.on('pointerdown', () => {
                
                // 🤖 AUTO CAÇADA
                // Clique manual em qualquer mob cancela a Auto Caçada,
                // mas deixa o clique manual continuar funcionando normalmente.
                if (this.autoCacadaAtiva) {
                    this.pararAutoCacada("clique manual em mob", false);
                }

                // 1. TRAVA DE COLETA (Se estiver cortando árvore, não pode bater)
                if (this.scene.player && this.scene.player.isGathering) {
                    return; 
                }

                // 2. TRAVA DE DISTÂNCIA 
                // 2. TRAVA DE DISTÂNCIA E AUTO-CAMINHADA
                let distAtaque = Phaser.Math.Distance.Between(this.scene.player.x, this.scene.player.y, sprite.x, sprite.y);

                if (distAtaque > 80) { 
                    // 1. Faz o personagem andar na direção do monstro
                    this.scene.target.set(sprite.x, sprite.y);
                    this.scene.isMoving = true;
                    this.scene.physics.moveToObject(this.scene.player, this.scene.target, 150);

                    // 2. Tira o alerta antigo e coloca o aviso flutuante amigável
                    let aviso = this.scene.add.text(this.scene.player.x, this.scene.player.y - 50, "Me aproximando...", {
                        fontSize: '12px', fontFamily: 'Arial', color: '#facc15', fontStyle: 'bold', stroke: '#000', strokeThickness: 3
                    }).setOrigin(0.5, 1).setDepth(100);
                    
                    this.scene.tweens.add({ targets: aviso, y: aviso.y - 20, alpha: 0, duration: 1500, onComplete: () => aviso.destroy() });
                    
                    return; // Bloqueia a abertura da aba de batalha até chegar perto
                }

                // 3. SE ESTIVER PERTO, PARA DE ANDAR E ABRE A BATALHA!
                if (this.scene.isMoving && typeof this.scene.pararPersonagem === 'function') {
                    this.scene.pararPersonagem();
                }

                if (typeof window.iniciarCacadaApp === 'function') {
                    window.iniciarCacadaApp(mobData.spawn_id, { mobData });
                } else {
                    console.error("ERRO: A função iniciarCacadaApp não foi encontrada!");
                }
            });

            // ==========================================
            // ANIMAÇÃO DE POP-IN
            // Mantém corretamente 48x48 ou 128x128
            // ==========================================

            // Guarda a escala que o setDisplaySize calculou
            const escalaFinalX = sprite.scaleX;
            const escalaFinalY = sprite.scaleY;

            sprite.setScale(0);
            sprite.setAlpha(0);

            sprite.indicadorAlvo.setScale(0);
            sprite.indicadorAlvo.setAlpha(0);


            // Mob
            this.scene.tweens.add({
                targets: sprite,

                scaleX: escalaFinalX,
                scaleY: escalaFinalY,

                alpha: 1,

                duration: 800,
                ease: 'Bounce.easeOut'
            });


            // Seta
            this.scene.tweens.add({
                targets: sprite.indicadorAlvo,

                scaleX: 1,
                scaleY: 1,

                alpha: 1,

                duration: 800,
                ease: 'Bounce.easeOut'
            });

            this.mobsNoMapa.add(sprite);
            this.aplicarAuraCorrompida(sprite, mobData);
            if (mobData.quest_event_id === 'q3_varek_provacao') {
                const estadoIA = this.caravanaIAEstado?.mobs?.find(mob =>
                    String(mob.spawn_id) === String(mobData.spawn_id)
                );
                if (estadoIA) this.aplicarEstadoIACaravana(sprite, estadoIA);
            }
            
        } catch (e) {
            console.error("Erro ao desenhar mob:", e);
        }
    }

    removerMob(spawn_id) {
        // Se o mob removido era o alvo da Auto Caçada, cancela a perseguição.
        if (this.autoCacadaSpawnId && String(this.autoCacadaSpawnId) === String(spawn_id)) {
            this.pararAutoCacada("mob alvo removido");
        }

        // 🛡️ Filtro Robusto: Garante que estamos pegando apenas sprites válidos com o spawn_id correto
        const mobsParaDeletar = this.mobsNoMapa.getChildren().filter(mob => {
            // Verifica se é um sprite e se tem o spawn_id (convertendo ambos para string para comparação segura)
            return mob instanceof Phaser.GameObjects.Sprite && String(mob.spawn_id) === String(spawn_id);
        });
        
        mobsParaDeletar.forEach(mob => {
            console.log("☠️ Removendo visualmente o monstro do mapa:", spawn_id); 
            
            // ==========================================
            // 🛡️ DESTRUINDO A SETA (O CORAÇÃO DO PROBLEMA)
            // ==========================================
            // Como penduramos a seta no sprite em 'mob.indicadorAlvo' na função desenharSprite,
            // devemos garantir que ela seja destruída ANTES do mob.
            if (mob.indicadorAlvo && typeof mob.indicadorAlvo.destroy === 'function') {
                console.log("   -> Destruindo a seta flutuante.");
                mob.indicadorAlvo.destroy();
                mob.indicadorAlvo = null; // Limpa a referência
            }

            if (mob.corruptionAura && typeof mob.corruptionAura.destroy === 'function') {
                mob.corruptionAura.destroy();
                mob.corruptionAura = null;
            }

            // Fallback de segurança para o sistema antigo (se ainda existir algum player com nome antigo)
            if (mob.textoNome && typeof mob.textoNome.destroy === 'function') {
                mob.textoNome.destroy();
            }

            // Destrói o sprite do mob (o que remove o input e o visual do monstro)
            mob.destroy();
        });
    }
}
