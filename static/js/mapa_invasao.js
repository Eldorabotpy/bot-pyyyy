// ==========================================
// MOTOR DE INVASÕES E MONSTROS - MUNDO DE ELDORA
// ==========================================

class MotorDeInvasao {
    constructor(scene, socket) {
        this.scene = scene;
        this.socket = socket;
        this.monstrosNaTela = {};

        // 👇 CONECTANDO O NOVO ARQUIVO DE HUD 👇
        this.hud = new HudInvasao();

        this.iniciarEscutas();
        this.iniciarAtaqueDosMinions();
    }
    estaNaCapital() {
        const regiao =
            (this.scene?.regiaoAtual ||
            window.regiaoAtual ||
            localStorage.getItem("regiaoAtual") ||
            localStorage.getItem("eldora_lastRegiao") ||
            "").toLowerCase();

        return regiao.includes("capital");
    }

    esconderPainelFrentesInvasao() {
        const painel = document.getElementById("painel-frentes-invasao");
        if (painel) painel.style.display = "none";
    }

    mostrarAvisoInvasao(texto, cor = "#facc15") {
        if (!this.scene || !this.scene.add || !this.scene.player) return;

        const aviso = this.scene.add.text(
            this.scene.player.x,
            this.scene.player.y - 55,
            texto,
            {
                fontSize: "12px",
                fontFamily: "Cinzel, Arial",
                color: cor,
                stroke: "#000",
                strokeThickness: 4,
                align: "center"
            }
        ).setOrigin(0.5).setDepth(5000);

        this.scene.tweens.add({
            targets: aviso,
            y: aviso.y - 25,
            alpha: 0,
            duration: 1800,
            onComplete: () => aviso.destroy()
        });
    }

    atualizarPainelFrentesInvasao(dados) {
        if (!dados || !dados.ativo || !this.estaNaCapital()) {
            this.esconderPainelFrentesInvasao();
            return;
        }

        let painel = document.getElementById("painel-frentes-invasao");

        if (!painel) {
            painel = document.createElement("div");
            painel.id = "painel-frentes-invasao";
            painel.style.cssText = `
                position: fixed;
                top: 78px;
                left: 50%;
                transform: translateX(-50%);
                z-index: 90;
                width: min(58vw, 170px);
                background: rgba(2, 6, 23, .90);
                border: 1px solid #ca8a04;
                border-radius: 8px;
                padding: 4px 5px;
                color: #e2e8f0;
                font-family: Arial, sans-serif;
                box-shadow: 0 3px 8px rgba(0,0,0,.45);
                backdrop-filter: blur(4px);
                pointer-events: none;
            `;
            document.body.appendChild(painel);
        }

        if (!dados || !dados.ativo) {
            painel.style.display = "none";
            return;
        }

        const frentes = Array.isArray(dados.frentes) ? dados.frentes : [];

        const frentesHtml = frentes.map(f => {
            const status = String(f.status || "aberta");

            let cor = "#facc15";
            let texto = "ABERTA";

            if (status === "em_combate") {
                cor = "#38bdf8";
                texto = "LUTA";
            } else if (status === "defendida") {
                cor = "#22c55e";
                texto = "OK";
            } else if (status === "perdida") {
                cor = "#ef4444";
                texto = "CAIU";
            }

            return `
                <div style="
                    display:flex;
                    align-items:center;
                    justify-content:space-between;
                    gap:4px;
                    background:rgba(15,23,42,.88);
                    border:1px solid rgba(148,163,184,.18);
                    border-radius:6px;
                    padding:3px 5px;
                    min-height:18px;
                ">
                    <span style="
                        color:#fff;
                        font-size:10px;
                        font-weight:800;
                        white-space:nowrap;
                        overflow:hidden;
                        text-overflow:ellipsis;
                    ">
                        ${f.nome || f.id || "Frente"}
                    </span>

                    <span style="
                        color:${cor};
                        font-size:8px;
                        font-weight:900;
                        white-space:nowrap;
                    ">
                        ${texto}
                    </span>
                </div>
            `;
        }).join("");

        painel.innerHTML = `
            <div style="
                display:flex;
                justify-content:space-between;
                align-items:center;
                gap:5px;
                margin-bottom:3px;
                font-family:'Cinzel', Arial, sans-serif;
                font-size:10px;
                font-weight:900;
                color:#facc15;
                line-height:1;
            ">
                <span style="
                    white-space:nowrap;
                    overflow:hidden;
                    text-overflow:ellipsis;
                ">
                    🛡️ INVASÃO
                </span>

                <span style="
                    color:#facc15;
                    font-size:10px;
                    white-space:nowrap;
                ">
                    O${dados.onda || "?"}
                </span>

                <span style="
                    color:#facc15;
                    font-size:9px;
                    white-space:nowrap;
                ">
                    ${dados.defendidas || 0}/${dados.total_frentes || frentes.length || 0}
                </span>
            </div>

            <div style="
                display:grid;
                grid-template-columns:1fr;
                gap:3px;
                max-height:72px;
                overflow:hidden;
            ">
                ${frentesHtml}
            </div>
        `;

        painel.style.display = "block";
    }
    iniciarEscutas() {
        // Isso vai escutar TODOS os eventos que o servidor enviar
        this.socket.on('spawnMonstroInvasao', (dados) => {
            // Se o Python esquecer a região, assumimos que é a Capital!
            let regiaoMob = dados.regiao || 'capital_eldora';
            if (regiaoMob === this.scene.regiaoAtual) {
                this.desenharMonstro(dados);
            }
        });

        // 2. Escuta de Onda de Monstros (O Grande Conserto!)
        this.socket.on('spawnMonstrosInvasao', (listaMonstros) => {
            // 👇 Converte Dicionário do Python para Lista do Javascript automaticamente! 👇
            let monstros = Array.isArray(listaMonstros) ? listaMonstros : Object.values(listaMonstros);

            monstros.forEach(dados => {
                let regiaoMob = dados.regiao || 'capital_eldora';
                if (regiaoMob === this.scene.regiaoAtual) {
                    this.desenharMonstro(dados);
                }
            });
        });

        this.socket.on('removerMonstrosInvasao', (ids) => {
            const lista = Array.isArray(ids) ? ids : Object.values(ids || {});

            lista.forEach(id => this.removerMonstroInvasao(id));

            if (this.hud && typeof this.hud.atualizarContador === "function") {
                this.hud.atualizarContador(Object.keys(this.monstrosNaTela).length);
            }
        });
        
        this.socket.on('statusInvasaoFrentes', (dados) => {
            this.atualizarPainelFrentesInvasao(dados);
        });

        this.socket.on('eventoEncerrado', (dados = {}) => {
            this.ultimoEncerramentoInvasao = dados || {};

            const resultado = String(
                dados.resultado || ""
            ).toLowerCase();

            this.limparMonstrosInvasao();
            this.atualizarPainelFrentesInvasao({
                ativo: false
            });

            if (
                this.hud &&
                typeof this.hud.esconder === "function"
            ) {
                this.hud.esconder();
            }

            if (resultado === "vitoria") {
                this.tocarCinematicaVitoria(dados);
                return;
            }

            if (resultado === "derrota") {
                this.tocarCinematicaDerrota();
            }
        });
        
         this.socket.on('erroGeral', (dados) => {
            const msg = dados?.mensagem || "Ação bloqueada.";
            this.mostrarAvisoInvasao(msg, "#ef4444");
            window.__invasaoCliqueTravado = false;
        });

        // 🔥 A MÁGICA DO ATAQUE EM ÁREA (AoE) 🔥
        this.socket.on('bossPreparandoAtaque', (dados) => {
            if (!this.estaNaCapital()) return;
            // 1. Desenha a "Área de Perigo" (um círculo vermelho semitransparente) no chão
            let zonaPerigo = this.scene.add.circle(dados.x, dados.y, dados.raio, 0xff0000, 0.3).setDepth(16);

            // Faz o círculo pulsar para assustar o jogador
            this.scene.tweens.add({ targets: zonaPerigo, alpha: 0.6, yoyo: true, repeat: -1, duration: 250 });

            // 2. Coloca o nome do golpe flutuando
            let txtGolpe = this.scene.add.text(dados.x, dados.y - dados.raio, dados.nome_ataque, {
                fontSize: '16px', color: '#ff0000', stroke: '#000', strokeThickness: 5, fontStyle: 'bold'
            }).setOrigin(0.5).setDepth(200);

            // 3. O Relógio Tiquetaqueia... (2.5 segundos de Cast)
            this.scene.time.delayedCall(dados.tempo_cast, () => {
                // A EXPLOSÃO ACONTECE! Limpa os desenhos da tela
                zonaPerigo.destroy();
                txtGolpe.destroy();
                this.scene.cameras.main.shake(300, 0.02); // Treme a tela inteira

                // 4. A VERIFICAÇÃO: O jogador foi burro de ficar no círculo?
                let distancia = Phaser.Math.Distance.Between(this.scene.player.x, this.scene.player.y, dados.x, dados.y);

                if (distancia <= dados.raio) {
                    // TOMOU DANO! Pisca vermelho e avisa o Python!
                    this.scene.player.setTint(0xff0000);
                    this.scene.time.delayedCall(300, () => this.scene.player.clearTint());

                    let meuId = localStorage.getItem("jogadorEldoraID");
                    let meuNome = localStorage.getItem("jogadorEldoraNome");
                    if (meuId) {
                        this.socket.emit('jogadorLevouDanoBoss', { player_id: meuId, player_nome: meuNome });
                    }
                }
                
            });
        }); // 🛑 A CHAVE DO BOSS FECHA AQUI!

        // ========================================================
        // 📺 AVISA O HUD PARA LIGAR OU DESLIGAR A TELA (AGORA SOLTO)
        // ========================================================
        this.socket.on('alertaInvasao', (dados) => {
            if (!this.estaNaCapital()) {
                if (this.hud && typeof this.hud.esconder === "function") {
                    this.hud.esconder();
                }
                this.esconderPainelFrentesInvasao();
                return;
            }

            if (dados.tempo_restante) {
                let ondaAtual = dados.onda || (dados.mensagem.includes('10 MINUTOS') ? 0 : 1);
                this.hud.mostrar(ondaAtual, dados.tempo_restante);
            }

            let msg = String(dados.mensagem || "").toUpperCase();
            let resultado = String(dados.resultado || "").toLowerCase();

            const ehDerrota =
                resultado === "derrota" ||
                msg.includes("DERROTA") ||
                msg.includes("TEMPO ESGOTOU") ||
                msg.includes("CAPITAL CAIU") ||
                msg.includes("UMA OU MAIS FRENTES CAÍRAM") ||
                msg.includes("UMA OU MAIS FRENTES CAIRAM");

            const ehVitoria =
                resultado === "vitoria" ||
                resultado === "vitória" ||
                msg.includes("REPELIDA") ||
                msg.includes("SUCESSO") ||
                msg.includes("VITÓRIA") ||
                msg.includes("VITORIA");

            if (ehDerrota) {
                this.hud.esconder();
                this.tocarCinematicaDerrota();
            }
            else if (msg.includes('ONDA 1 COMEÇOU')) {
                this.tocarCinematicaStart();
                this.hud.mostrar(1);
            }
            else if (msg.includes('COMEÇOU') || msg.includes('COMEÇA')) {
                let ondaMatch = msg.match(/ONDA (\d+)/);
                let numeroOnda = ondaMatch ? ondaMatch[1] : 1;
                this.hud.mostrar(numeroOnda);
            }

            else if (msg.includes('CAIU') || msg.includes('SUCUMBIU')) {
                this.hud.esconder();
            }
        });
        // 🔄 SOLUÇÃO PARA O F5:
        // Assim que conectar, pergunta ao servidor se tem evento rolando
        this.socket.emit('checarStatusInvasao');

        this.socket.on('statusInvasaoAtual', (dados) => {
            if (dados.ativo && this.estaNaCapital()) {
                this.hud.mostrar(dados.onda, dados.tempo_restante);
            } else {
                if (this.hud && typeof this.hud.esconder === "function") {
                    this.hud.esconder();
                }
                this.esconderPainelFrentesInvasao();
            }
        });

        // ========================================================
        // 🩸 ESCUTANDO O DANO NO JOGADOR (AGORA SOLTO)
        // ========================================================
        this.socket.on('atualizarHUDVida', (dados) => {
            const meuId = localStorage.getItem("jogadorEldoraID");

            if (dados.player_id === meuId) {
                // 1. Treme a tela e pisca de vermelho
                this.scene.cameras.main.shake(150, 0.005);
                this.scene.player.setTint(0xff0000);
                this.scene.time.delayedCall(200, () => this.scene.player.clearTint());

                // 2. Faz o número vermelho voar da sua cabeça!
                let danoText = this.scene.add.text(this.scene.player.x, this.scene.player.y - 40, `-${dados.dano}`, {
                    fontSize: '18px', fontFamily: 'Courier', color: '#ff0000', stroke: '#000000', strokeThickness: 4, fontStyle: 'bold'
                }).setOrigin(0.5).setDepth(200);

                this.scene.tweens.add({ targets: danoText, y: danoText.y - 40, alpha: 0, duration: 1000, onComplete: () => danoText.destroy() });

                // 3. Força as bolhas de HP do HUD a descerem na hora!
                if (typeof window.atualizarHudCircular === 'function') window.atualizarHudCircular();
                if (typeof carregarDadosDoHUD === 'function') carregarDadosDoHUD();
            }
        });

        // ========================================================
        // Mantemos os eventos de dano e morte normais
        // ========================================================
        this.socket.on('danoMonstroInvasao', (dados) => {
            const m = this.monstrosNaTela[dados.id];
            if (m) {
                let pct = Math.max(0, dados.hp / m.max_hp);
                m.atualizarBarra(pct);

                let danoText = this.scene.add.text(m.sprite.x, m.sprite.y - 40, `-${dados.dano}`, {
                    fontSize: '16px', fontFamily: 'Courier', color: '#ff0000', stroke: '#000000', strokeThickness: 3, fontStyle: 'bold'
                }).setOrigin(0.5);

                this.scene.tweens.add({ targets: danoText, y: danoText.y - 30, alpha: 0, duration: 1000, onComplete: () => danoText.destroy() });
                m.sprite.setTint(0xff0000);
                this.scene.time.delayedCall(150, () => m.sprite.clearTint());

                if (dados.hp <= 0) {
                    m.bgBar.destroy(); m.hpBar.destroy(); m.textoNome.destroy();
                    if (this.scene.anims.exists('anim_explosao')) {
                        m.sprite.play('anim_explosao');
                        m.sprite.on('animationcomplete', () => m.sprite.destroy());
                    } else { m.sprite.destroy(); }

                    delete this.monstrosNaTela[dados.id];
                    // 👇 A LINHA QUE FALTAVA PARA O NÚMERO DESCER 👇
                    this.hud.atualizarContador(Object.keys(this.monstrosNaTela).length);
                }
            }
        });

        this.socket.on('monstroInvasaoMorreu', (id) => {
            this.removerMonstroInvasao(id);

            if (this.hud && typeof this.hud.atualizarContador === "function") {
                this.hud.atualizarContador(Object.keys(this.monstrosNaTela).length);
            }
        });
    }

    // 🎬 EFEITO DE INÍCIO DA INVASÃO (EXTREMO DRAMA)
    tocarCinematicaStart() {
        this.scene.cameras.main.shake(3000, 0.015);

        // Pisca Preto e Branco
        this.scene.cameras.main.flash(400, 255, 255, 255);
        setTimeout(() => this.scene.cameras.main.flash(400, 0, 0, 0), 400);

        // 👇 REDUZIMOS O FONTSIZE PARA 40PX (Era 60px) 👇
        let txt = this.scene.add.text(this.scene.cameras.main.centerX, this.scene.cameras.main.centerY, "A INVASÃO COMEÇOU", {
            fontFamily: 'Cinzel, serif',
            fontSize: '20px',
            color: '#ffffff',
            stroke: '#000000',
            strokeThickness: 8,
            fontStyle: 'bold',
            align: 'center',
            shadow: { offsetX: 0, offsetY: 0, color: '#ff0000', blur: 15, stroke: true, fill: true }
        }).setOrigin(0.5).setScrollFactor(0).setDepth(20000).setScale(0.01).setAlpha(0);

        this.scene.tweens.add({
            targets: txt,
            alpha: 1,
            scale: 1, // Cresce até o tamanho real (40px)
            duration: 1200,
            ease: 'Power2',
            onComplete: () => {
                this.scene.tweens.add({
                    targets: txt,
                    scale: 1, // 👇 REDUZIMOS A EXPANSÃO PARA 1.8x (Era 4x)
                    alpha: 0,
                    duration: 800,
                    delay: 500,
                    ease: 'Power3',
                    onComplete: () => txt.destroy()
                });
            }
        });
    }

        // 💀 EFEITO DE DERROTA DA INVASÃO
    tocarCinematicaDerrota() {
        if (this.hud && typeof this.hud.esconder === "function") {
            this.hud.esconder();
        }

        if (!this.scene || !this.scene.cameras || !this.scene.add) return;

        this.scene.cameras.main.shake(900, 0.01);
        this.scene.cameras.main.flash(700, 120, 0, 0);

        let txtDerrota = this.scene.add.text(
            this.scene.cameras.main.centerX,
            this.scene.cameras.main.centerY - 80,
            "DERROTA!\nO Reino sofreu perdas",
            {
                fontFamily: 'Cinzel',
                fontSize: '32px',
                color: '#ef4444',
                stroke: '#000',
                strokeThickness: 8,
                align: 'center'
            }
        ).setOrigin(0.5).setScrollFactor(0).setDepth(20000).setAlpha(0);

        this.scene.tweens.add({
            targets: txtDerrota,
            alpha: 1,
            duration: 900,
            yoyo: true,
            hold: 2500,
            onComplete: () => txtDerrota.destroy()
        });
    }
    
    carregarSpriteResultadoInvasao(nomeDoArquivo, x, y, ehBoss = true) {
        if (!nomeDoArquivo) {
            return null;
        }

        const tamanhoOriginal = ehBoss ? 128 : 48;
        const chaveTextura = `resultado_invasao_${nomeDoArquivo}_${ehBoss ? "boss128" : "mob48"}`;
        const urlImagem = `https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/mob/invasao/${nomeDoArquivo}.png`;

        const criarSprite = () => {
            let sprite = this.scene.add.sprite(x, y, chaveTextura, 0).setDepth(15);
            sprite.setDisplaySize(ehBoss ? 96 : 48, ehBoss ? 96 : 48);

            try {
                const chaveAnim = 'idle_' + chaveTextura;
  
                if (!this.scene.anims.exists(chaveAnim)) {
                    this.scene.anims.create({
                        key: chaveAnim,
                        frames: this.scene.anims.generateFrameNumbers(chaveTextura, { start: 0, end: 2 }),
                        frameRate: 5,
                        repeat: -1
                    });
                }

                sprite.play(chaveAnim);
            } catch (e) {
                console.warn("Sem animação de vitória para:", chaveTextura);
            }

            return sprite;
        };

        if (this.scene.textures.exists(chaveTextura)) {
            return criarSprite();
        }

        this.scene.load.spritesheet(chaveTextura, urlImagem, {
            frameWidth: tamanhoOriginal,
            frameHeight: tamanhoOriginal
        });

        this.scene.load.once(`filecomplete-spritesheet-${chaveTextura}`, () => {
            criarSprite();
        });

        this.scene.load.start();

        return null;
    }

    // 🏆 EFEITO DE VITÓRIA (BAÚ E NPC)
    carregarNpcVitoriaRei(x, y) {
        const chave = "npc_comemoracao_rei";
        const url = "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/npcs/comemoracao_rei.png";

        // AJUSTE SE NECESSÁRIO:
        // assumindo sprite sheet 3x4 = 384x512
        // então cada frame = 128x128
        const frameWidth = 128;
        const frameHeight = 128;

        const criarSprite = () => {

        // Remove um rei antigo, caso ainda exista.
        if (
            this.reiVitoriaAtual &&
            this.reiVitoriaAtual.active
        ) {
            this.reiVitoriaAtual.destroy();
        }

        const rei = this.scene.add.sprite(
            x,
            y,
            chave,
            1
        ).setDepth(15);

        // Guarda uma referência real do sprite criado.
        this.reiVitoriaAtual = rei;

            // tamanho visual
            rei.setDisplaySize(64, 64);

            const animKey = "rei_comemoracao_idle";

            if (!this.scene.anims.exists(animKey)) {
                this.scene.anims.create({
                    key: animKey,

                    // primeira linha = frames 0, 1, 2
                    // faz loop frontal da comemoração
                    frames: [
                        { key: chave, frame: 0 },
                        { key: chave, frame: 1 },
                        { key: chave, frame: 2 },
                        { key: chave, frame: 1 }
                    ],

                    frameRate: 4,
                    repeat: -1
                });
            }

            rei.play(animKey);

            return rei;
        };

        if (this.scene.textures.exists(chave)) {
            return criarSprite();
        }

        this.scene.load.spritesheet(chave, url, {
            frameWidth,
            frameHeight
        });

        this.scene.load.once(`filecomplete-spritesheet-${chave}`, () => {
            criarSprite();
        });

        this.scene.load.start();
  
        return null;
    }

    tocarCinematicaVitoria(dados = {}) {
        if (this.hud && typeof this.hud.esconder === "function") {
            this.hud.esconder();
        }

        this.scene.cameras.main.flash(2000, 255, 215, 0);

        const titulo = dados.titulo || "VITÓRIA!\nO Reino foi Salvo";
        const falaNpc = dados.fala_npc || "Glória aos Heróis!\nAs recompensas estão no baú!";
        const npcVitoria = String(dados.npc_vitoria || "comemoracao_rei");

        let centroX = this.scene.cameras.main.centerX;
        let centroY = this.scene.cameras.main.centerY;
        // Posição REAL no mapa, no centro da praça.
        const reiX = 29 * 32;
        const reiY = 31 * 32;

        let txtVitoria = this.scene.add.text(
            centroX,
            centroY - 130,
            titulo,
            {
                fontFamily: 'Cinzel',
                fontSize: '40px',
                color: '#f1c40f',
                stroke: '#000',
                strokeThickness: 8,
                align: 'center'
            }
        ).setOrigin(0.5).setScrollFactor(0).setDepth(20000).setAlpha(0);

        this.scene.tweens.add({
            targets: txtVitoria,
            alpha: 1,
            duration: 1200,
            yoyo: true,
            hold: 3000
        });

        let rei = null;

        if (npcVitoria === "comemoracao_rei") {
            rei = this.carregarNpcVitoriaRei(
                reiX,
                reiY
            );
        }

        // pequeno atraso pra garantir que o sprite já apareceu
        this.scene.time.delayedCall(200, () => {
            const balao = this.criarBalaoRei(
                reiX,
                reiY - 105,
                falaNpc
            );

            this.scene.tweens.add({
                targets: [balao.bg, balao.txt, balao.seta],
                alpha: { from: 0, to: 1 },
                duration: 250
            });

            this.scene.time.delayedCall(15000, () => {

                if (
                    this.reiVitoriaAtual &&
                    this.reiVitoriaAtual.active
                ) {
                    this.reiVitoriaAtual.destroy();
                    this.reiVitoriaAtual = null;
                }

                if (balao.bg) {
                    balao.bg.destroy();
                }

                if (balao.txt) {
                    balao.txt.destroy();
                }

                if (balao.seta) {
                    balao.seta.destroy();
                }
            });
        });
    }
    
    criarBalaoRei(x, y, texto) {
        const largura = 280;
        const altura = 84;

        const bg = this.scene.add.graphics().setDepth(210);

        bg.fillStyle(0x0b1630, 0.96);
        bg.lineStyle(3, 0xd8a431, 1);
        bg.fillRoundedRect(x - largura / 2, y - altura / 2, largura, altura, 14);
        bg.strokeRoundedRect(x - largura / 2, y - altura / 2, largura, altura, 14);

        const txt = this.scene.add.text(
            x - largura / 2 + 14,
            y - altura / 2 + 12,
            texto,
            {
                fontFamily: 'Arial',
                fontSize: '18px',
                color: '#f2f2f2',
                wordWrap: { width: largura - 28 },
                lineSpacing: 4,
                fontStyle: 'bold'
            }
        ).setDepth(211);

        // setinha amarela embaixo
        const seta = this.scene.add.graphics().setDepth(210);
        seta.fillStyle(0xe0b126, 1);
        seta.fillTriangle(
            x - 10, y + altura / 2,
            x + 10, y + altura / 2,
            x, y + altura / 2 + 14
        );

        return { bg, txt, seta };
    }

    removerMonstroInvasao(id) {
        const m = this.monstrosNaTela[id];
        if (!m) return;

        if (m.bgBar) m.bgBar.destroy();
        if (m.hpBar) m.hpBar.destroy();
        if (m.textoNome) m.textoNome.destroy();
        if (m.textoFrente) m.textoFrente.destroy();
        if (m.auraFrente) m.auraFrente.destroy();
        if (m.sprite) m.sprite.destroy();

        delete this.monstrosNaTela[id];
    }

    limparMonstrosInvasao() {
        Object.keys(this.monstrosNaTela).forEach(id => {
            this.removerMonstroInvasao(id);
        });

        this.monstrosNaTela = {};

        if (this.hud && typeof this.hud.atualizarContador === "function") {
            this.hud.atualizarContador(0);
        }
    }

    iniciarAtaqueDosMinions() {
        this.scene.time.addEvent({
            delay: 1500,
            callback: () => {
                const jogadorPos = new Phaser.Math.Vector2(this.scene.player.x, this.scene.player.y);
                Object.values(this.monstrosNaTela).forEach(m => {
                    const monstroPos = new Phaser.Math.Vector2(m.sprite.x, m.sprite.y);
                    if (jogadorPos.distance(monstroPos) < 50) {
                        this.scene.time.delayedCall(150, () => this.scene.player.clearTint());
                        let meuId = localStorage.getItem("jogadorEldoraID");
                        if (meuId) {
                            this.socket.emit('sofrerDanoInvasao', { player_id: meuId, dano: Phaser.Math.Between(5, 15) });
                        }
                    }
                });
            },
            loop: true
        });
    }

    desenharMonstro(dados) {
        if (this.monstrosNaTela[dados.id]) return;

        // 👇 PROTEÇÃO ANTI-F5 BLINDADA (Lê o CSS real!) 👇
        let elementoHud = document.getElementById('hud-invasao');
        if (elementoHud && window.getComputedStyle(elementoHud).display === 'none') {
            // Lê o ID do monstro (ex: "onda2_soldado") para adivinhar a onda atual
            let matchOnda = (dados.id || dados.skin || '').match(/ond[a]?(\d+)/i);
            let numOnda = matchOnda ? matchOnda[1] : 1;
            this.hud.mostrar(numOnda);
        }
        let nomeDoArquivo = dados.skin || 'ond1_slime_verde';

        const ehBoss = !!dados.is_boss;
        const tamanhoDoCorteDaImagemOriginal = ehBoss ? 128 : 48;

        // importante: chave diferente para boss, senão o Phaser usa cache antigo de 48x48
        let chaveTextura = `mob_arte_${nomeDoArquivo}_${ehBoss ? "boss128" : "mob48"}`;

        // 👇 CONTROLE DE TAMANHO VISUAL NO MAPA 👇
        // Isso dita o quão grande o bicho aparece na tela (ignora o tamanho original da foto)
        let tamanhoDesejado = dados.is_boss ? 112 : 48;

        const criarSpriteMonstro = () => {
            if (this.monstrosNaTela[dados.id]) return;

            // Cria o sprite com a chave, se não existir, o Phaser usa um quadrado verde automaticamente
            let texturaUsada = this.scene.textures.exists(chaveTextura) ? chaveTextura : 'player';
            let auraFrente = null;

            if (dados.is_boss) {
                auraFrente = this.scene.add.circle(dados.x, dados.y, 58, 0xca8a04, 0.18)
                    .setDepth(14);

                this.scene.tweens.add({
                    targets: auraFrente,
                    alpha: 0.38,
                    scale: 1.12,
                    yoyo: true,
                    repeat: -1,
                    duration: 650
                });
            }

            let sprite = this.scene.physics.add.sprite(dados.x, dados.y, texturaUsada).setDepth(16);

            if (this.hud && typeof this.hud.atualizarContador === 'function') {
                this.hud.atualizarContador(Object.keys(this.monstrosNaTela).length + 1);
            }

            sprite.setDisplaySize(tamanhoDesejado, tamanhoDesejado);

            if (dados.is_boss) {
                sprite.body.setSize(64, 64);
            } else {
                sprite.body.setSize(32, 32);
            }

            // 🔥 A VERDADEIRA ANIMAÇÃO DE VOLTA! 🔥
            const tentarAnimar = () => {
                if (this.scene.textures.exists(chaveTextura) && this.scene.textures.get(chaveTextura).key !== '__MISSING') {
                    try {
                        if (!this.scene.anims.exists('idle_' + chaveTextura)) {
                            this.scene.anims.create({
                                key: 'idle_' + chaveTextura,
                                frames: this.scene.anims.generateFrameNumbers(chaveTextura, { start: 0, end: 2 }),
                                frameRate: 5,
                                repeat: -1
                            });
                        }
                        sprite.play('idle_' + chaveTextura);
                    } catch (e) { console.warn("Sem animação idle para:", chaveTextura); }
                }
            };

            tentarAnimar();

            // Se a textura carregou depois, atualiza
            if (!this.scene.textures.exists(chaveTextura)) {
                sprite.setData('aguardandoTextura', chaveTextura);
            }

            // Textos e Barras
            let offsetTextoY = dados.is_boss ? 50 : 36;
            let offsetBarraY = dados.is_boss ? 36 : 27;

            // Nome limpo: remove frente repetida do nome do boss.
            let nomeMobLimpo = String(dados.nome || dados.name || "Monstro")
                .replace(/\s*-\s*Portão\s+Norte/gi, "")
                .replace(/\s*-\s*Portão\s+Sul/gi, "")
                .replace(/\s*-\s*Muralha\s+Leste/gi, "")
                .replace(/\s*-\s*Muralha\s+Oeste/gi, "")
                .replace(/\s*-\s*Frente\s+Central/gi, "")
                .trim();

            let textoLegenda = dados.is_boss
                ? `Lv.${dados.nivel || "?"} ${nomeMobLimpo}`
                : `${nomeMobLimpo}`;

            let textoNome = this.scene.add.text(
                dados.x,
                dados.y - offsetTextoY,
                textoLegenda,
                {
                    fontSize: dados.is_boss ? "9px" : "8px",
                    color: dados.is_boss ? "#facc15" : "#f87171",
                    stroke: "#000",
                    strokeThickness: 2,
                    fontFamily: "Arial",
                    fontStyle: "bold",
                    align: "center"
                }
            ).setOrigin(0.5).setDepth(30);

            // Limita largura para não atravessar a tela.
            textoNome.setWordWrapWidth(dados.is_boss ? 115 : 80);
            textoNome.setAlign("center");

            let bgBar = this.scene.add.rectangle(dados.x, dados.y - offsetBarraY, 40, 5, 0x000000).setOrigin(0.5).setDepth(30);
            let hpBar = this.scene.add.rectangle(dados.x - 20, dados.y - offsetBarraY, 40, 5, 0xff0000).setOrigin(0, 0.5).setDepth(30);

            const atualizarBarra = (pct) => { hpBar.width = 40 * Math.max(0, pct); };
            atualizarBarra(dados.hp / dados.max_hp);

            sprite.setInteractive();
            sprite.on('pointerdown', () => {
                if (window.__invasaoCliqueTravado) {
                    this.mostrarAvisoInvasao("Aguarde...", "#facc15");
                    return;
                }

                let dist = Phaser.Math.Distance.Between(this.scene.player.x, this.scene.player.y, sprite.x, sprite.y);

                if (dist < 70) {
                    this.scene.tweens.add({
                        targets: this.scene.player,
                        y: this.scene.player.y - 10,
                        yoyo: true,
                        duration: 100
                    });

                    if (dados.is_boss) {
                        window.__invasaoCliqueTravado = true;
                        this.mostrarAvisoInvasao(`Entrando na ${dados.frente_nome || "frente"}...`, "#60a5fa");

                        setTimeout(() => {
                            window.__invasaoCliqueTravado = false;
                        }, 5000);
                    }

                    this.socket.emit('atacarMonstroInvasao', {
                        monstro_id: dados.id,
                        player_nome: localStorage.getItem("jogadorEldoraNome"),
                        player_id: localStorage.getItem("jogadorEldoraID")
                    });

                } else {
                    this.scene.target.set(sprite.x, sprite.y);
                    this.scene.isMoving = true;
                    this.scene.physics.moveToObject(this.scene.player, this.scene.target, 150);
                }
            });

            this.monstrosNaTela[dados.id] = {
                sprite,
                textoNome,
                bgBar,
                hpBar,
                auraFrente,
                atualizarBarra,
                max_hp: dados.max_hp,
                frente_id: dados.frente_id,
                frente_nome: dados.frente_nome,
                is_boss: !!dados.is_boss,
                tentarAnimar
            };
        };

        // CHAMA A CRIAÇÃO IMEDIATAMENTE (mesmo se a textura não existir, usa fallback)
        criarSpriteMonstro();

        if (!this.scene.textures.exists(chaveTextura)) {
            if (!window.texturasCarregando) window.texturasCarregando = {};

            // Só manda carregar se ainda não estiver na fila
            if (!window.texturasCarregando[chaveTextura]) {
                window.texturasCarregando[chaveTextura] = true;

                let urlImagem = `https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/mob/invasao/${nomeDoArquivo}.png`;
                this.scene.load.spritesheet(chaveTextura, urlImagem, {
                    frameWidth: tamanhoDoCorteDaImagemOriginal,
                    frameHeight: tamanhoDoCorteDaImagemOriginal
                });

                this.scene.load.once(`filecomplete-spritesheet-${chaveTextura}`, () => {
                    // Quando a imagem baixar, atualiza todos os monstros que estavam esperando por ela
                    Object.values(this.monstrosNaTela).forEach(m => {
                        if (m.sprite && m.sprite.getData('aguardandoTextura') === chaveTextura) {
                            m.sprite.setTexture(chaveTextura);

                            const tamanho = m.is_boss ? 96 : 48;
                            m.sprite.setDisplaySize(tamanho, tamanho);

                            if (m.sprite.body) {
                                m.sprite.body.setSize(m.is_boss ? 64 : 32, m.is_boss ? 64 : 32);
                            }

                            m.sprite.setData('aguardandoTextura', null);
                            if (typeof m.tentarAnimar === 'function') m.tentarAnimar();
                        }
                    });
                });
                this.scene.load.start();
            }
        }
    }
}