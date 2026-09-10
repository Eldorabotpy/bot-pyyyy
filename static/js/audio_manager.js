// audio_manager.js - Central de Áudio do Mundo de Eldora

const AudioManager = {
    // Configurações Iniciais
    isMuted: localStorage.getItem("eldora_muted") === "true",

    musicaAtual: null,
    chaveAtual: null,
    srcAtual: null,

    listaSfx: [],

    audioDesbloqueado: false,
    audioUnlock: null,

    // 🎵 DICIONÁRIO DE SONS (Centralizado)
    assets: {
        bgm_batalha: [
            "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/game_sons/batalha/battle1.mp3",
            "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/game_sons/batalha/battle2.mp3",
            "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/game_sons/batalha/battle3.mp3",
            "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/game_sons/batalha/battle4.mp3",
        ],
        // ⚔️ GUERRA DE CLÃS
        bgm_guerra_clans: [
            "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/game_sons/sons_guerra_clan/guerra_batalha1.mp3",
            "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/game_sons/sons_guerra_clan/guerra_batalha2.mp3",
            "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/game_sons/sons_guerra_clan/guerra_batalha3.mp3",
        ],

        bgm_capital: "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/game_sons/regioes/capital.mp3",
        bgm_pradaria: "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/game_sons/regioes/pradaria.mp3",
        bgm_floresta: "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/game_sons/regioes/floresta.mp3",
        som_spawn: "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/game_sons/regioes/som_spawn.mp3",
        som_espada: "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/game_sons/ataque/attack.mp3",
        som_critico: "https://github.com/user-attachments/files/26172289/phatphrogstudio-rpg-female-attack-grunt-no-ai-481720.mp3",
        som_monstro: "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/game_sons/ataque/monster-bite.mp3",
        som_vitoria: "https://github.com/user-attachments/files/26172334/eaglaxle-gaming-victory-464016.mp3",
        som_magia: "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/game_sons/ataque/magic.mp3",
        som_fogo: "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/game_sons/ataque/fire.mp3",
    },
    // ========================================================
    // 🔓 DESBLOQUEAR ÁUDIO NO TELEGRAM / WEBVIEW
    // ========================================================

    desbloquearAudio() {

        if (
            this.isMuted
            ||
            this.audioDesbloqueado
        ) {
            return;
        }


        try {

            if (!this.audioUnlock) {

                this.audioUnlock =
                    new Audio(
                        "data:audio/wav;base64,"
                        +
                        "UklGRiwAAABXQVZFZm10IBAAAAABAAEA"
                        +
                        "QB8AAEAfAAABAAgAZGF0YQgAAACAgICAgICAgA=="
                    );


                this.audioUnlock.volume =
                    0.01;
            }


            const tentativa =
                this.audioUnlock.play();


            if (
                tentativa
                &&
                typeof tentativa.then ===
                    "function"
            ) {

                tentativa
                    .then(
                        () => {

                            this.audioDesbloqueado =
                                true;


                            this.audioUnlock.pause();


                            this.audioUnlock.currentTime =
                                0;


                            console.log(
                                "🔊 [ÁUDIO] Desbloqueado."
                            );
                        }
                    )
                    .catch(
                        erro => {

                            console.warn(
                                "⚠️ [ÁUDIO] "
                                + "Ainda bloqueado:",
                                erro
                            );
                        }
                    );


            } else {

                this.audioDesbloqueado =
                    true;
            }


        } catch (
            erro
        ) {

            console.warn(
                "⚠️ [ÁUDIO] "
                + "Falha ao desbloquear:",
                erro
            );
        }
    },
    // 🔊 FUNÇÃO PARA TOCAR EFEITOS (SFX)
    tocarSFX(chave) {
        if (this.isMuted || !this.assets[chave]) return;

        let sfx = new Audio(this.assets[chave]);
        sfx.volume = 0.6; //
        sfx.play().catch(e => console.warn("Áudio bloqueado:", e));
        this.listaSfx.push(sfx);

        // Limpa a memória quando o som acabar
        sfx.onended = () => {
            this.listaSfx = this.listaSfx.filter(s => s !== sfx);
        };
    },

    // 🎼 FUNÇÃO PARA MÚSICA DE FUNDO (BGM)
    tocarMusica(chave) {

        // ====================================================
        // 🎵 A MESMA CATEGORIA JÁ ESTÁ TOCANDO
        //
        // Importantíssimo para listas aleatórias:
        // não sorteia outra música se a categoria
        // atual já estiver ativa.
        // ====================================================

        if (
            this.chaveAtual === chave
            &&
            this.musicaAtual
        ) {

            return;
        }


        let linkMusica =
            this.assets[chave];


        if (
            Array.isArray(
                linkMusica
            )
        ) {

            if (
                !linkMusica.length
            ) {

                return;
            }


            const indexAleatorio =
                Math.floor(
                    Math.random()
                    *
                    linkMusica.length
                );


            linkMusica =
                linkMusica[
                    indexAleatorio
                ];
        }


        if (
            this.isMuted
            ||
            !linkMusica
        ) {

            return;
        }


        this.pararMusica();


        this.chaveAtual =
            chave;


        this.srcAtual =
            linkMusica;


        this.musicaAtual =
            new Audio(
                linkMusica
            );


        this.musicaAtual.loop =
            true;


        this.musicaAtual.volume =
            0.3;


        this.musicaAtual
            .play()
            .catch(
                e =>
                    console.warn(
                        "BGM bloqueada:",
                        e
                    )
            );
    },

    pararMusica() {
        if (this.musicaAtual) {
            this.musicaAtual.pause();
            this.musicaAtual.currentTime = 0;
            this.musicaAtual.removeAttribute('src'); // Limpeza profunda para evitar vazamentos
            this.musicaAtual.load();
            this.musicaAtual = null;
            this.chaveAtual = null;
            this.srcAtual = null;
        }
    },

    pararTudo() {
        this.pararMusica();
        this.listaSfx.forEach(s => {
            s.pause();
            s.src = "";
        });
        this.listaSfx = [];
    },

    // 🔕 BOTÃO MESTRE: LIGA/DESLIGA
    toggleMute() {
        this.isMuted = !this.isMuted;
        localStorage.setItem("eldora_muted", this.isMuted);
        
        if (this.isMuted) {
            this.pararTudo();
        } else {
            // Se o jogador religou o som, verifica onde ele está e volta a tocar!
            if (window.jogoEldora) {
                let cenaMapa = window.jogoEldora.scene.getScene('MapaScene');
                if (cenaMapa && cenaMapa.regiaoAtual === 'capital_eldora') {
                    this.tocarMusica('bgm_capital');
                }
            }
        }
        
        this.atualizarIconeBotao();
        return this.isMuted;
    },

    atualizarIconeBotao() {
        const img = document.getElementById("img-mute-icon");
        if (img) {
            // Links diretos para as imagens no seu repositório assets/ui
            const iconeLigado = "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/ui/som_on.png";
            const iconeDesligado = "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/ui/Som%2520mudo.png";
        
            // Define a imagem baseada no estado de mudo
            img.src = this.isMuted ? iconeDesligado : iconeLigado;
        
            // Feedback visual extra (opcional): deixa um pouco transparente quando mudo
            img.style.opacity = this.isMuted ? "0.6" : "1";
        }
    }
};

// Exporta para ser usado em qualquer lugar (combate.js ou mapa.js)
window.AudioManager = AudioManager;