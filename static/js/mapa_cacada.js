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
            this.socket.off('convocarCombateGrupo');

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

            // 2. Apaga o monstro do mapa quando ele morre
            this.socket.on('mobMapaMorreu', (dados) => {
                this.removerMob(dados.spawn_id);
            });

            // 3. Mobs nascendo no tempo certo
            this.socket.on('mobMapaNasceu', (dados) => {
                let regiaoAtual = this.scene.regiaoAtual || localStorage.getItem("eldora_lastRegiao");

                // Só desenha se o jogador estiver no mesmo mapa
                if (regiaoAtual === dados.regiao) {
                    this.spawnMob(dados.mob_data);
                }
            });
        }
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
                autoCacada: true
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
            alert(`${titulo}\n${mensagem}`);
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

    criarBotaoTesteAutoCacada() {
        this.instalarEstiloBotaoAutoCacada();

        let btn = document.getElementById("btn-teste-auto-cacada");

        if (!btn) {
            btn = document.createElement("button");
            btn.id = "btn-teste-auto-cacada";
            btn.type = "button";
            btn.title = "Iniciar Auto Caçada";
            btn.innerHTML = `<div class="auto-cacada-icone"></div>`;

            document.body.appendChild(btn);
        }

        btn.onclick = (event) => {
            if (event) {
                event.preventDefault();
                event.stopPropagation();
            }

            if (this.autoCacadaAtiva) {
                this.pararAutoCacada("parada manualmente", true);
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
        let pastaRegiao = tradutorPastas[regiaoAtual] || regiaoAtual;

        // Monta o link apontando para a pasta traduzida!
        const linkNuvem = `https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/mob/${pastaRegiao}/`;
        
        const textureKey = `ss_mob_${pastaRegiao}_${mobData.monster_id}`;

        if (!this.scene.textures.exists(textureKey)) {
            
            this.scene.load.spritesheet(textureKey, `${linkNuvem}${mobData.monster_id}.png`, {
                frameWidth: 48, 
                frameHeight: 48 
            });
            
            this.scene.load.once(`filecomplete-spritesheet-${textureKey}`, () => {
                this.desenharSprite(mobData, textureKey);
            });

            this.scene.load.once('loaderror', (fileObj) => {
                if(fileObj.key === textureKey) {
                    alert("❌ Link não encontrado no GitHub:\n" + fileObj.url);
                }
            });

            this.scene.load.start();
        } else {
            this.desenharSprite(mobData, textureKey);
        }
    }

    desenharSprite(mobData, textureKey) {
        try {
            let sprite = this.scene.add.sprite(mobData.x, mobData.y, textureKey, 0).setDepth(14);
            sprite.spawn_id = mobData.spawn_id;

            // Guarda os dados originais do mob dentro do sprite.
            // Isso será usado pela Auto Caçada para saber qual mob perseguir.
            sprite.mobData = mobData;

            let totalFrames = this.scene.textures.get(textureKey).frameTotal;
            if (totalFrames >= 3) {
                const animKey = `${textureKey}_idle`;
                if (!this.scene.anims.exists(animKey)) {
                    this.scene.anims.create({
                        key: animKey,
                        frames: this.scene.anims.generateFrameNumbers(textureKey, { start: 0, end: 2 }),
                        frameRate: 5,
                        repeat: -1
                    });
                }
                sprite.play(animKey);
            }

            // ==========================================
            // 🏹 SETA FLUTUANTE (Substitui o Texto)
            // ==========================================
            sprite.indicadorAlvo = this.scene.add.text(mobData.x, mobData.y - 30, '▼', {
                fontSize: '18px', color: '#ff4757', stroke: '#000', strokeThickness: 3
            }).setOrigin(0.5).setDepth(30);

            // Animação da seta flutuando (sobe e desce sem parar)
            this.scene.tweens.add({
                targets: sprite.indicadorAlvo,
                y: mobData.y - 22,
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
                    window.iniciarCacadaApp(mobData.spawn_id); 
                } else {
                    console.error("ERRO: A função iniciarCacadaApp não foi encontrada!");
                }
            });

            // ==========================================
            // ANIMAÇÃO DE POP-IN (GELATINA)
            // ==========================================
            sprite.setScale(0);
            sprite.setAlpha(0);
            sprite.indicadorAlvo.setScale(0);
            sprite.indicadorAlvo.setAlpha(0);

            this.scene.tweens.add({
                targets: [sprite, sprite.indicadorAlvo],
                scale: 1,
                alpha: 1,
                duration: 800,
                ease: 'Bounce.easeOut'
            });

            this.mobsNoMapa.add(sprite);
            
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

            // Fallback de segurança para o sistema antigo (se ainda existir algum player com nome antigo)
            if (mob.textoNome && typeof mob.textoNome.destroy === 'function') {
                mob.textoNome.destroy();
            }

            // Destrói o sprite do mob (o que remove o input e o visual do monstro)
            mob.destroy();
        });
    }
}