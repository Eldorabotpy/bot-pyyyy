// /static/js/mapa.js - VERSÃO DEFINITIVA COM TRADUTOR DE SKIN E ALERTA 404
const socket = (typeof io !== 'undefined') ? io() : null;
window.eldoraSocket = socket;

class MapaScene extends Phaser.Scene {
    constructor() {
        super('MapaScene');
        this.target = new Phaser.Math.Vector2();
        this.isMoving = false;
        this.objetosInterativos = [];
    }

    init(data) {
        // Reset imediato de travas de estado e movimento[cite: 4]
        this.isDead = false; 
        this.isMoving = false;
        this.travadoNoPortal = true; // O jogador nasce ignorando portais
        this.graficosProntos = false;
        // Configurações de origem e região[cite: 4]
        this.veioDeRespawn = data && data.isRespawn ? true : false;
        this.regiaoAtual = data.regiao || 'capital_eldora';
        
        // Tratamento da skin e gênero[cite: 4]
        let skinCrua = localStorage.getItem("skinEquipada") || data.skin || window.minhaSkinAtual || 'aventureiro';
        this.skinAtiva = skinCrua.toLowerCase();
        
        // Definição do ponto de spawn[cite: 4]
        this.spawnX = data.spawnX || null;
        this.spawnY = data.spawnY || null;
        this.isRespawn = data.isRespawn || false;


        // ==========================================
        // 🌀 CHEGADA POR PORTAL
        // ==========================================

        this.portalChegadaId =
            data.portalChegadaId || null;

        this.veioDePortal =
            data.veioDePortal || false;

        // Limpeza de física e visibilidade caso a cena esteja sendo reiniciada[cite: 4]
        if (this.player) {
            if (this.player.body) {
                this.player.body.setEnable(true); // Reativa a física[cite: 4]
                this.player.body.stop(); // Para qualquer inércia anterior[cite: 4]
            }
            this.player.setVisible(true); // Garante que não apareça invisível[cite: 4]
            this.player.setAlpha(1); // Reseta transparência de morte[cite: 4]
        }
    }

    preload() {
        this.load.on('progress', (value) => {
            if (typeof window.atualizarCarregamento === 'function') {
                // A barra vai de 50% até 99% acompanhando o download real!
                let progresso = Math.floor(50 + (value * 49)); 
                window.atualizarCarregamento(progresso, `Desenhando o mundo... ${progresso}%`);
            }
        });
        if (!this.cache.tilemap.exists(this.regiaoAtual)) {

            this.load.tilemapTiledJSON(
                this.regiaoAtual,
                `/static/regions/${this.regiaoAtual}.tmj?v=${Date.now()}`
            );

        }
        
        this.load.image('tiles_grama', '/static/images/tilesets/grama reino.png');
        this.load.image('tiles_casas', '/static/images/tilesets/casas.png'); 
        this.load.image('tiles_hpg', '/static/images/tilesets/HPGLobbyTileset.png');
        this.load.image('tiles_arvores', '/static/images/tilesets/arvores.png');
        let genero = localStorage.getItem("generoEscolhido") || "masculino";
        if (genero !== "masculino" && genero !== "feminino") {
            genero = "masculino";
            localStorage.setItem("generoEscolhido", "masculino"); 
        }

        let nomeSkin = this.skinAtiva;

        nomeSkin = nomeSkin.replace('_masculino', '_m').replace('_feminino', '_f');

        if (nomeSkin === 'player' || nomeSkin === '') {
            nomeSkin = 'aventureiro';
        }

        if (!nomeSkin.endsWith('_m') && !nomeSkin.endsWith('_f') && !nomeSkin.includes('skin_')) {
            let generoCurto = (genero === 'feminino') ? 'f' : 'm';
            nomeSkin = `${nomeSkin}_${generoCurto}`;
        }
        
        this.skinAtiva = nomeSkin;
        this.skinResolvida = nomeSkin;
        // Carrega a imagem do Selo para a notificação de Nível 50
        this.load.image('icon_maestria', 'https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/itens/materiais/selo_maestria.png');
        // Usamos 'main' direto que é mais rápido e estável que refs/heads/main
        const GITHUB_ASSETS = "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/";
        
        // 👇 A MÁGICA CONTRA O CACHE DO GITHUB 👇
        const cacheBuster = `?v=${new Date().getTime()}`;
        
        // Adicionamos o cacheBuster no final das imagens
        let pathSkin = `${GITHUB_ASSETS}classes/${nomeSkin}.png${cacheBuster}`;
        
        let fWidth = 128; 
        let fHeight = 128;

        let generoCurtoFallback = (genero === 'feminino') ? 'f' : 'm';
        const pathFallback = `${GITHUB_ASSETS}classes/aventureiro_${generoCurtoFallback}.png${cacheBuster}`;
        
        this.load.once('loaderror', (fileObj) => {
            if (fileObj.key === this.skinAtiva) {
                alert(`🚨 ALERTA DO MAPA 🚨\n\nA skin não carregou porque o arquivo não foi encontrado no GitHub!\n\nO mapa tentou baixar:\n${fileObj.url}\n\nVerifique se o nome do arquivo lá é exatamente esse.`);
            }
        });

        this.load.spritesheet(this.skinAtiva, pathSkin, { frameWidth: fWidth, frameHeight: fHeight });
        this.load.spritesheet('aventureiro_base', pathFallback, { frameWidth: 48, frameHeight: 48 });
        
        this.load.spritesheet('explosao_sombria', '/static/assets/sprites/explosao_sombria.png', { frameWidth: 128, frameHeight: 128 });
        
        // ==========================================
        // 🌀 PORTAIS DE REGIÃO
        // ==========================================

        if (!this.textures.exists('portal_regiao')) {

            this.load.spritesheet(
                'portal_regiao',
                '/static/images/tilesets/portal_anim.png',
                {
                    frameWidth: 416,
                    frameHeight: 512
                }
            );

        }
        this.load.spritesheet('circulo_cura', '/static/assets/sprites/efeitos/magic_circle_heal.png', { frameWidth: 64, frameHeight: 64 });
        this.load.spritesheet('emoji_raiva', 'https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/emoji/emoji_raiva.png', { frameWidth: 32, frameHeight: 32 });
        
        this.load.image('npc_atendente', 'https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/npcs/atendente.png'); 
        // Carregamento do sprite do Merlin
        this.load.spritesheet('npc_merlin', 'https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/npcs/npc_merlin.png', { frameWidth: 48, frameHeight: 48 });
        this.load.image('moldura_skill', '/static/assets/sprites/slot_skill.png');
        this.load.spritesheet('circulo_magico', 'https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/efeitos/magic_circle_heal.png', {
            frameWidth: 64,
            frameHeight: 64
        });

        this.load.image('img_lapide', 'https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/efeitos/mort_player.png');
    
        if (!this.textures.exists('circulo_magico')) {
            this.load.spritesheet('circulo_magico', 'https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/efeitos/magic_circle_heal.png', {
                frameWidth: 64,
                frameHeight: 64
            });
        } 
        
        this.load.spritesheet('efeito_despertar', 'https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/efeitos/efeito_despertar.png', { 
            frameWidth: 96,   
            frameHeight: 256  
        });
        // 👇 ADICIONA ESTA LINHA PARA O VAREK APARECER 👇
        const URL_VAREK = "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/npcs/npc_varek.png";
        this.load.spritesheet('npc_varek', URL_VAREK, { frameWidth: 48, frameHeight: 48 });

        const URL_SELENE_REAL = "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/classes/npc_selene.png";
        this.load.spritesheet('npc_selene', URL_SELENE_REAL, { frameWidth: 48, frameHeight: 48 });
        
        const URL_THOREK = "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/classes/npc_thorek.png";
        this.load.spritesheet('npc_thorek', URL_THOREK, { frameWidth: 48, frameHeight: 48 });
        
        // 👇 1. ADICIONA ISTO AQUI (Os Novos Mestres de Profissão) 👇
        const BASE_NPC = "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/npcs/";
        this.load.spritesheet('npc_sylas', BASE_NPC + 'npc_sylas.png', { frameWidth: 48, frameHeight: 48 });
        this.load.spritesheet('npc_grom', BASE_NPC + 'npc_grom.png', { frameWidth: 48, frameHeight: 48 });
        this.load.spritesheet('npc_elara', BASE_NPC + 'npc_elara.png', { frameWidth: 48, frameHeight: 48 });
        this.load.spritesheet('npc_borin', BASE_NPC + 'npc_borin.png', { frameWidth: 48, frameHeight: 48 });
        this.load.spritesheet('npc_paracelso', BASE_NPC + 'npc_paracelso.png', { frameWidth: 48, frameHeight: 48 });
        // 👆 -------------------------------------------------------- 👆
   
        const baseUrlRecursos = 'https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/itens/recurssos_mapas/';
        this.load.image('item_arvore', baseUrlRecursos + 'arvore.png'); 
        this.load.image('item_pedra', baseUrlRecursos + 'pedra.png');
        this.load.image('item_linho', baseUrlRecursos + 'linho.png');
        this.load.image('item_ferro', baseUrlRecursos + 'ferro.png'); 
        
        this.load.image('item_pena', baseUrlRecursos + 'pena.png', { frameWidth: 48, frameHeight: 48 });
        
        this.load.image('item_sangue', baseUrlRecursos + 'sangue.png');
        // Nova imagem da Forja para o Thorek
        this.load.image('item_forja', 'https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/itens/recurssos_mapas/forja.png');
        this.load.image('item_fornalha', 'https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/itens/recurssos_mapas/refino.png');
        // ==========================================
        // 🏰 GUILDA DOS AVENTUREIROS
        // ==========================================

        this.load.image(
            'icone_guilda',
            'https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/ui/icone_guilda.png'
        );

    }

    create() {
        const meuIdDoBanco = localStorage.getItem("jogadorEldoraID");
        const meuNome = localStorage.getItem("jogadorEldoraNome") || "Aventureiro";
    
        const map = this.make.tilemap({ key: this.regiaoAtual });
        
        let todosTilesets = [];
        if (map.tilesets.some(t => t.name === 'grama reino')) todosTilesets.push(map.addTilesetImage('grama reino', 'tiles_grama'));
        if (map.tilesets.some(t => t.name === 'casas')) todosTilesets.push(map.addTilesetImage('casas', 'tiles_casas'));
        if (map.tilesets.some(t => t.name === 'HPGLobbyTileset')) todosTilesets.push(map.addTilesetImage('HPGLobbyTileset', 'tiles_hpg')); 
        if (map.tilesets.some(t => t.name === 'arvores')) todosTilesets.push(map.addTilesetImage('arvores', 'tiles_arvores'));
        
        // ==========================================
        // 📱 CORREÇÃO DE LINHAS ENTRE TILES
        // Principalmente em telas de celular
        // ==========================================
        [
            'tiles_grama',
            'tiles_casas',
            'tiles_hpg',
            'tiles_arvores'
        ].forEach(chave => {

            if (this.textures.exists(chave)) {

                const textura = this.textures.get(chave);

                textura.setFilter(
                    Phaser.Textures.FilterMode.NEAREST
                );
            }

        });
        
        // 👇 1. ADICIONADO A CAMADA 'grama' AQUI PARA A FLORESTA APARECER 👇
        const camadasBaixas = [
            // 1º TUDO QUE É CHÃO (A Base do mapa)
            'Chao Capital', 'Ruas Capital', 'Chao Catedral', 'Piso', 'chao', 'grama',
            
            // 2º ESTRUTURAS E DECORAÇÕES (Ficam em cima do chão)
            'Casas', 'Paredes', 'Muralha', 'Decoracao', 'casas',
            
            // 3º AS ÁRVORES (O Phaser desenha elas por último, cobrindo a grama)
            'arvores', 'arvores1', 'arvores2', 'pedras', 'pedras1', 'pedras2'
        ];
        
        camadasBaixas.forEach(l => {

            if (!map.getLayer(l)) {
                return;
            }

            let profundidade = 0;

            // ==========================================
            // 🏠 CASAS ACIMA DO MERLIN
            // ==========================================
            if (
                l === 'Casas' ||
                l === 'casas'
            ) {
                profundidade = 10;
            }

            map.createLayer(
                l,
                todosTilesets,
                0,
                0
            ).setDepth(profundidade);
        });


        // ==========================================
        // 🌀 PORTAIS DAS REGIÕES
        // ==========================================

        if (typeof PortalManager !== 'undefined') {

            this.portalManager =
                new PortalManager(
                    this,
                    map
                );

        } else {

            console.error(
                "❌ PortalManager não foi carregado."
            );

        }


        this.physics.world.setBounds(
            0,
            0,
            map.widthInPixels,
            map.heightInPixels
        );
    
        const skinFinal = this.textures.exists(this.skinAtiva) ? this.skinAtiva : 'aventureiro_base';
        this.player = this.physics.add.sprite(27 * 32, 29 * 32, skinFinal);
        this.player.setCollideWorldBounds(true).setDepth(15);

        // Reduz visualmente qualquer sprite para o tamanho final do mapa
        this.player.setDisplaySize(48, 48);

        // ==========================================
        // 🚶 HITBOX REAL NOS PÉS DO PERSONAGEM
        // ==========================================

        // O sprite original possui frame 128x128,
        // mas é exibido no mapa como 48x48.
        // Por isso a hitbox precisa usar as medidas
        // correspondentes ao frame original.

        this.player.body
            .setSize(54, 40)
            .setOffset(37, 80);   
        
        try { this.gerarAnimacoes(skinFinal); } catch(e) { console.error("Erro nas animações", e); }
    
        this.cameras.main.startFollow(this.player, true, 0.1, 0.1);
        this.cameras.main.setBounds(0, 0, map.widthInPixels, map.heightInPixels);
        this.cameras.main.setRoundPixels(true);
        
        // ==========================================
        // ⛺ NPC MERCADOR (SÓ APARECE NA CAPITAL) ⛺
        // ==========================================
        if (this.regiaoAtual === 'capital_eldora') {
            // 👇 AQUI: Trocamos 'aventureiro_m' por 'npc_merlin' 👇
            let npcMercador = this.add.sprite(432, 1136, 'npc_merlin'); 
            
            // 👇 Removi o setTint(0xf1c40f) para o novo sprite aparecer nas cores reais dele! 👇
            npcMercador.setDepth(5); 
            npcMercador.setFrame(1); 
            
            this.criarPlaquinhaNome(npcMercador.x, npcMercador.y - 20, '𝐌𝐞𝐫𝐥𝐢𝐧');


            let hitboxTenda = this.add.rectangle(npcMercador.x, npcMercador.y, 128, 128, 0xff0000, 0.001)
                .setDepth(100)
                .setInteractive({ useHandCursor: true });

            hitboxTenda.on('pointerdown', (pointer, localX, localY, event) => {
                if (event) event.stopPropagation();
                let dist = Phaser.Math.Distance.Between(this.player.x, this.player.y, npcMercador.x, npcMercador.y);
                
                if (dist > 160) {
                    let aviso = this.add.text(this.player.x, this.player.y - 50, "Preciso me aproximar da tenda...", {
                        fontSize: '12px', fontFamily: 'Arial', color: '#ef4444', fontStyle: 'bold', stroke: '#000', strokeThickness: 3
                    }).setOrigin(0.5, 1).setDepth(100);
                    this.tweens.add({ targets: aviso, y: aviso.y - 20, alpha: 0, duration: 2000, onComplete: () => aviso.destroy() });
                } else {
                    if (typeof window.abrirLojaAventureiro === 'function') window.abrirLojaAventureiro();
                }
            });
        }
        // ==========================================
        // ==========================================
        // ⚖️ NOVA LOJA: MERCADO DO AVENTUREIRO (ENTRE PLAYERS)
        // ==========================================
        if (this.regiaoAtual === 'capital_eldora') {
            // 📍 Defina as coordenadas X e Y da porta da casa escolhida no seu Tiled
            // Exemplo genérico (mude os números abaixo para bater com a casa do seu mapa)
            let casaMercadoX = 36 * 32; 
            let casaMercadoY = 18 * 32;

            // 1. Cria o Ícone da Balança flutuando no mapa estilo indicador de Quest
            let iconeBalanca = this.add.text(casaMercadoX, casaMercadoY - 60, '⚖️', {
                fontSize: '22px', 
                stroke: '#00000000', 
                strokeThickness: 4
            }).setOrigin(0.5).setDepth(30);

            // Animação de pulsação vertical para a balança ficar subindo e descendo
            this.tweens.add({
                targets: iconeBalanca,
                y: casaMercadoY - 53,
                duration: 700,
                yoyo: true,
                repeat: -1,
                ease: 'Sine.easeInOut'
            });

            // 2. Plaquinha oficial em cima da porta
            this.criarPlaquinhaNome(casaMercadoX, casaMercadoY - 80, 'Mercado Real');

            // 3. Hitbox interativa na porta da casa
            let hitboxPortaMercado = this.add.rectangle(casaMercadoX, casaMercadoY - 10, 170, 150, 0x00ff00, 0.001)
                .setDepth(50)
                .setInteractive({ useHandCursor: true });

            hitboxPortaMercado.on('pointerdown', (pointer, localX, localY, event) => {
                if (event) event.stopPropagation();
                if (this.player && this.player.isGathering) return;

                let dist = Phaser.Math.Distance.Between(this.player.x, this.player.y, casaMercadoX, casaMercadoY);
                
                if (dist > 30) {
                    // Auto-caminhada até a porta do Mercado se o player clicar de longe
                    this.target.set(casaMercadoX, casaMercadoY);
                    this.isMoving = true;
                    this.physics.moveToObject(this.player, this.target, 150);

                    let aviso = this.add.text(this.player.x, this.player.y - 50, "Indo ao Mercado...", {
                        fontSize: '12px', fontFamily: 'Arial', color: '#facc15', fontStyle: 'bold', stroke: '#000', strokeThickness: 3
                    }).setOrigin(0.5, 1).setDepth(100);
                    
                    this.tweens.add({ targets: aviso, y: aviso.y - 20, alpha: 0, duration: 1500, onComplete: () => aviso.destroy() });
                    return;
                }

                // Chegou perto: para a movimentação e abre a aba HTML nova!
                this.pararPersonagem();
                
                if (typeof abrirMercado === 'function') {
                    abrirMercado(); // Dispara o arquivo mercado.js que criamos
                } else {
                    console.error("Interface do Mercado (abrirMercado) não encontrada!");
                }

            });
        }
        
        // ============================================================
        // 🏰 GUILDA DOS AVENTUREIROS
        // 📍 Capital de Eldora - Tile 6,5
        // ============================================================

        if (this.regiaoAtual === 'capital_eldora') {

            // ==========================================
            // 📍 POSIÇÃO REAL NO MAPA
            // ==========================================

            const guildaTileX = 6;
            const guildaTileY = 5;

            const guildaX = guildaTileX * 32;
            const guildaY = guildaTileY * 32;


            // ==========================================
            // 🛡️ ÍCONE DA GUILDA
            // ==========================================

            let iconeGuilda = this.add.image(
                guildaX,
                guildaY - 45,
                'icone_guilda'
            )
            .setDepth(30)
            .setDisplaySize(40, 40)
            .setInteractive({
                useHandCursor: true
            });


            // ==========================================
            // ✨ ÍCONE FLUTUANDO
            // ==========================================

            this.tweens.add({
                targets: iconeGuilda,

                y: guildaY - 52,

                duration: 700,

                yoyo: true,

                repeat: -1,

                ease: 'Sine.easeInOut'
            });


            // ==========================================
            // 🏷️ PLAQUINHA
            // ==========================================

            this.criarPlaquinhaNome(
                guildaX,
                guildaY - 5,
                'Guilda dos Aventureiros'
            );


            // ==========================================
            // 👆 CLIQUE NO ÍCONE
            // ==========================================

            iconeGuilda.on(
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


                    // Não interage enquanto coleta
                    if (
                        this.player &&
                        this.player.isGathering
                    ) {
                        return;
                    }


                    const distancia =
                        Phaser.Math.Distance.Between(
                            this.player.x,
                            this.player.y,
                            guildaX,
                            guildaY
                        );


                    // ==================================
                    // 🚶 LONGE DA GUILDA
                    // ==================================

                    if (distancia > 110) {

                        this.target.set(
                            guildaX,
                            guildaY
                        );

                        this.isMoving = true;

                        this.physics.moveToObject(
                            this.player,
                            this.target,
                            150
                        );


                        let aviso =
                            this.add.text(
                                this.player.x,
                                this.player.y - 50,
                                "Indo à Guilda...",
                                {
                                    fontSize: '12px',
                                    fontFamily: 'Arial',
                                    color: '#facc15',
                                    fontStyle: 'bold',
                                    stroke: '#000',
                                    strokeThickness: 3
                                }
                            )
                            .setOrigin(0.5, 1)
                            .setDepth(100);


                        this.tweens.add({
                            targets: aviso,

                            y: aviso.y - 20,

                            alpha: 0,

                            duration: 1500,

                            onComplete: () => {
                                aviso.destroy();
                            }
                        });


                        return;
                    }


                    // ==================================
                    // 🏰 JÁ ESTÁ PERTO
                    // ==================================

                    if (
                        typeof this.pararPersonagem
                        === 'function'
                    ) {
                        this.pararPersonagem();
                    }


                    if (
                        typeof window.abrirGuildaMissoes
                        === 'function'
                    ) {

                        window.abrirGuildaMissoes();

                    } else {

                        console.error(
                            "❌ abrirGuildaMissoes() não encontrada. " +
                            "Verifique guild_missions.js."
                        );
                    }
                }
            );
        }

        // ============================================================
        // 🏰 CASA DO CLÃ
        // 📍 Capital de Eldora - Tile 54,33
        //
        // O brasão NÃO é decidido pelo mapa.
        // O backend informa qual é o clã atual do jogador
        // e qual logo foi escolhida na configuração.
        // ============================================================

        if (
            this.regiaoAtual ===
            'capital_eldora'
        ) {

            const clanTileX = 54;
            const clanTileY = 33;

            const clanX =
                clanTileX * 32;

            const clanY =
                clanTileY * 32;


            // ==========================================
            // 👤 PERSONAGEM ATUAL
            // ==========================================

            const jogadorId =
                localStorage.getItem(
                    "jogadorEldoraID"
                );


            if (jogadorId) {

                fetch(
                    `/api/clan/meu_clan/${encodeURIComponent(
                        jogadorId
                    )}?t=${Date.now()}`
                )
                .then(
                    resposta => {

                        if (!resposta.ok) {
                            throw new Error(
                                "Não foi possível consultar o clã."
                            );
                        }

                        return resposta.json();
                    }
                )
                .then(
                    dados => {

                        // ==================================
                        // 🛡️ JOGADOR SEM CLÃ
                        // ==================================

                        if (
                            !dados ||
                            !dados.success ||
                            !dados.possui_clan ||
                            !dados.clan
                        ) {

                            this.criarPlaquinhaNome(
                                clanX,
                                clanY - 15,
                                'Casa dos Clãs'
                            );

                            return;
                        }


                        const clan =
                            dados.clan;


                        const logoUrl =
                            String(
                                clan.logo_url ||
                                ""
                            ).trim();


                        const logoId =
                            String(
                                clan.logo_id ||
                                "padrao"
                            )
                            .replace(
                                /[^a-zA-Z0-9_-]/g,
                                "_"
                            );


                        const nomeClan =
                            String(
                                clan.nome ||
                                "Clã"
                            );


                        const tagClan =
                            String(
                                clan.tag ||
                                ""
                            );


                        // ==================================
                        // 🏷️ NOME DO CLÃ NO PRÉDIO
                        // ==================================

                        const nomeExibicao =
                            tagClan
                                ? `${nomeClan} [${tagClan}]`
                                : nomeClan;


                        this.criarPlaquinhaNome(
                            clanX,
                            clanY - 15,
                            nomeExibicao
                        );


                        // ==================================
                        // SEM URL DE BRASÃO
                        // ==================================

                        if (!logoUrl) {

                            console.warn(
                                "⚠️ O clã não possui logo_url."
                            );

                            return;
                        }


                        // ==================================
                        // 🖼️ TEXTURA ÚNICA POR BRASÃO
                        // ==================================

                        const textureKey =
                            `icone_cla_${logoId}`;


                        // ==================================
                        // 🛡️ CRIA O ÍCONE
                        // ==================================

                        const criarIconeCla =
                            () => {

                                // Evita criar duas vezes
                                // caso o loader emita mais de
                                // um evento.
                                if (
                                    this.iconeClaMapa
                                ) {
                                    return;
                                }


                                const iconeCla =
                                    this.add.image(
                                        clanX,
                                        clanY - 70,
                                        textureKey
                                    )
                                    .setDepth(31)
                                    .setDisplaySize(
                                        46,
                                        46
                                    );


                                this.iconeClaMapa =
                                    iconeCla;


                                // ==========================
                                // ✨ FLUTUAÇÃO
                                // ==========================

                                this.tweens.add({

                                    targets:
                                        iconeCla,

                                    y:
                                        clanY - 78,

                                    duration:
                                        900,

                                    yoyo:
                                        true,

                                    repeat:
                                        -1,

                                    ease:
                                        'Sine.easeInOut'
                                });


                                // ==========================
                                // ✨ PULSO SUAVE
                                // ==========================

                                this.tweens.add({

                                    targets:
                                        iconeCla,

                                    scaleX:
                                        1.08,

                                    scaleY:
                                        1.08,

                                    duration:
                                        900,

                                    yoyo:
                                        true,

                                    repeat:
                                        -1,

                                    ease:
                                        'Sine.easeInOut'
                                });

                            };


                        // ==================================
                        // ♻️ TEXTURA JÁ CARREGADA
                        // ==================================

                        if (
                            this.textures.exists(
                                textureKey
                            )
                        ) {

                            criarIconeCla();

                            return;
                        }


                        // ==================================
                        // 📥 CARREGA A LOGO ESCOLHIDA
                        // PELO LÍDER
                        // ==================================

                        this.load.image(
                            textureKey,
                            logoUrl
                        );


                        this.load.once(
                            `filecomplete-image-${textureKey}`,
                            criarIconeCla
                        );


                        this.load.once(
                            'loaderror',
                            arquivo => {

                                if (
                                    arquivo &&
                                    arquivo.key ===
                                    textureKey
                                ) {

                                    console.error(
                                        "❌ Não foi possível carregar " +
                                        "o brasão do clã:",
                                        logoUrl
                                    );
                                }
                            }
                        );


                        this.load.start();

                    }
                )
                .catch(
                    erro => {

                        console.error(
                            "❌ [CLÃ MAPA] " +
                            "Falha ao carregar brasão:",
                            erro
                        );
                    }
                );
            }
        }

        if (this.spawnX && this.spawnY) {

            this.player.setPosition(
                this.spawnX,
                this.spawnY
            );

        }
        else if (this.isRespawn) {

            this.player.setPosition(
                55 * 32,
                13 * 32
            );

        }  


        // ==========================================
        // 🌀 NASCE NO PORTAL DA REGIÃO
        // ==========================================

        if (
            this.portalChegadaId &&
            this.portalManager
        ) {

            this.portalManager
                .posicionarJogadorNaChegada(
                    this.portalChegadaId
                );

        }

        this.playerNameText = this.add.text(this.player.x, this.player.y - 25, meuNome, { 
            fontSize: '12px', color: '#f1c40f', fontFamily: 'Cinzel, Arial', stroke: '#000', strokeThickness: 3
        }).setOrigin(0.5, 1).setDepth(30);
        
        const camadasAltas = ['Acima do Jogador'];
        camadasAltas.forEach(l => { if (map.getLayer(l)) map.createLayer(l, todosTilesets, 0, 0).setDepth(20); });
    
        if (map.getLayer('Camada de Colisoes')) {

            let layerCol = map.createLayer(
                'Camada de Colisoes',
                todosTilesets,
                0,
                0
            );

            layerCol
                .setCollisionByExclusion([-1])
                .setVisible(false)

            this.physics.add.collider(this.player, layerCol);
        }

        this.target = new Phaser.Math.Vector2();
        
        try {
            // Inicialização do Multiplayer (Não apagar)
            if (typeof socket !== 'undefined' && socket) {
                if (typeof MapaHUD !== 'undefined') this.hud = new MapaHUD(this); 
                if (typeof MapaInterativo !== 'undefined') this.interativo = new MapaInterativo(this);
                if (typeof MotorDeInvasao !== 'undefined') this.motorInvasao = new MotorDeInvasao(this, socket);
                if (typeof MotorMultiplayer !== 'undefined') this.motorMultiplayer = new MotorMultiplayer(this, socket);
                
                if (typeof MotorCacada !== 'undefined') {
                    this.motorCacada = new MotorCacada(this, socket);
                }
            }

            // Inicialização dos NPCs
            if (typeof NPCsEngine !== 'undefined') {
                this.motorNPC = new NPCsEngine(this);
    
                // ==========================================
                // 📍 SPAWN DE MESTRES POR REGIÃO (IDs CORRIGIDOS)
                // ==========================================

                if (this.regiaoAtual === 'capital_eldora') {
                    this.motorNPC.spawnNPCAndante('varek', 'Capitão Varek', 'npc_varek', 15 * 32, 29 * 32, 21 * 32, 28 * 32);
                    this.motorNPC.spawnNPCAndante('selene', 'Arquimaga Selene', 'npc_selene', 22 * 32, 13 * 32, 28 * 32, 13 * 32);
                    this.motorNPC.spawnNPCAndante('thorek', 'Mestre-Artesão Thorek', 'npc_thorek', 48 * 32, 29 * 32, 55 * 32, 29 * 32);
                    this.motorNPC.spawnNPCAndante('paracelso', 'Alquimista Paracelso', 'npc_paracelso', 50 * 32, 37 * 32, 46 * 32, 37 * 32);
                }
                else if (this.regiaoAtual === 'pradaria_inicial') {
                    this.motorNPC.spawnNPCAndante('grom', 'Grom o Caçador', 'npc_grom', 48 * 32, 9 * 32, 48 * 32, 16 * 32);
                    this.motorNPC.spawnNPCAndante('elara', 'Madame Elara', 'npc_elara', 20 * 32, 30 * 32, 25 * 32, 30 * 32);
                }
                else if (this.regiaoAtual === 'floresta_sombria') {
                    this.motorNPC.spawnNPCAndante('sylas', 'Guarda-Bosque Sylas', 'npc_sylas', 37 * 32, 14 * 32, 30 * 32, 14 * 32);
                }
                else if (this.regiaoAtual === 'pedreira_granito') {
                    this.motorNPC.spawnNPCAndante('borin', 'Mestre Bórin', 'npc_borin', 15 * 32, 15 * 32, 20 * 32, 15 * 32);
                }

            } else {
                console.warn("Motor de NPCs não carregado no index.html!");
            }
        } catch (e) {
            console.error("Erro crítico na inicialização dos motores, o mapa foi salvo:", e);
        }
        
        // 👇 2. O CLIMA SOMBRIO, CHUVA E TROVÕES DA FLORESTA 👇
        if (this.regiaoAtual === 'floresta_sombria') {
            // --- A. FILTRO AZUL/SOMBRIO ---
            let filtroSombrio = this.add.rectangle(
                map.widthInPixels / 2, 
                map.heightInPixels / 2, 
                map.widthInPixels, 
                map.heightInPixels, 
                0x0f172a 
            );
            filtroSombrio.setAlpha(0.55); 
            filtroSombrio.setDepth(90); 
            
            // 👇 A MÁGICA ESTÁ AQUI: Diz pro Phaser que o clique passa reto pela escuridão 👇
            filtroSombrio.disableInteractive(); 
            
            // --- B. CRIANDO A GOTA DE CHUVA NO CÓDIGO ---
            // 👇 A TRAVA DE SEGURANÇA: Só cria a gota se ela não existir na memória! 👇
            if (!this.textures.exists('gota_chuva')) {
                let graficosChuva = this.make.graphics({ x: 0, y: 0, add: false });
                graficosChuva.fillStyle(0x88ccff, 0.6); 
                graficosChuva.fillRect(0, 0, 2, 12); 
                graficosChuva.generateTexture('gota_chuva', 2, 12); 
            }
            
            // --- C. SISTEMA DE PARTÍCULAS (CHUVA) ---
           let particulasChuva = this.add.particles(0, 0, 'gota_chuva', {
                // Nasce em toda a largura da TELA, e não mais do mapa inteiro
                x: { min: 0, max: this.cameras.main.width }, 
                y: -50, 
                lifespan: 1500, 
                speedY: { min: 500, max: 700 }, 
                speedX: { min: -30, max: 30 }, 
                scale: { start: 1, end: 0.5 }, 
                quantity: 8, // Diminuímos a quantidade porque a área coberta agora é menor
                blendMode: 'ADD' 
            });
            
            particulasChuva.setDepth(91);
            
            // 👇 A MÁGICA PROFISSIONAL AQUI 👇
            // Isso "descola" a chuva do chão do mapa e gruda na câmera do jogador!
            particulasChuva.setScrollFactor(0);

            // --- D. SISTEMA DE TROVÕES (RELÂMPAGOS) ---
            const dispararTrovao = () => {
                // Só dispara se a cena ainda estiver rodando e na floresta
                if (this.scene.isActive() && this.regiaoAtual === 'floresta_sombria') {
                    
                    // Cria um clarão branco rapidinho na tela toda (150ms) com força de 60%
                    this.cameras.main.flash(150, 255, 255, 255, 0.6);
                    
                    // Sorteia um tempo aleatório para o próximo trovão (entre 5 e 15 segundos)
                    let proximoTrovao = Phaser.Math.Between(5000, 15000);
                    
                    // Programa o próximo disparo!
                    this.time.delayedCall(proximoTrovao, dispararTrovao);
                }
            };
            
            // Começa o ciclo de relâmpagos 3 segundos depois que você entra no mapa
            this.time.delayedCall(3000, dispararTrovao);
        }
        
        this.input.on('pointerdown', (pointer) => {

            if (this.isDead) return;

            // ==========================================
            // 🛡️ HUD DE STATUS ABERTO
            // Não permite o clique chegar ao mapa.
            // ==========================================

            if (
                window.__painelStatusAberto
            ) {
                return;
            }

            // ==========================================
            // 🌀 MENU DO PORTAL ABERTO
            // ==========================================

            if (
                document.getElementById(
                    'eldora-portal-overlay'
                )
            ) {
                return;
            }
            
            // 👇 TRAVA DE MOVIMENTO: Se o diálogo do NPC estiver aberto, ignora o clique!
            const caixaDialogo = document.getElementById('rpg-dialogo-container');
            if (caixaDialogo && caixaDialogo.style.display === 'block') {
                return; 
            }
            // 🔥 TRAVA DE AÇÃO: Se estiver coletando, cancela o clique de andar!
            if (this.player && this.player.isGathering) {
                // Cria um textinho subindo pra avisar o jogador que ele tá ocupado
                let aviso = this.add.text(this.player.x, this.player.y - 60, "Ocupado...", {
                    fontSize: '12px', fontFamily: 'Arial', color: '#facc15', fontStyle: 'bold', stroke: '#000', strokeThickness: 3
                }).setOrigin(0.5, 1).setDepth(100);
                this.tweens.add({ targets: aviso, y: aviso.y - 20, alpha: 0, duration: 1500, onComplete: () => aviso.destroy() });
                return; // O 'return' impede o código de descer e fazer o boneco andar!
            }
            
            if (typeof window.AudioManager !== 'undefined' && !window.AudioManager.isMuted && !window.AudioManager.musicaAtual) {
                if (this.regiaoAtual === 'capital_eldora') window.AudioManager.tocarMusica('bgm_capital');
                else if (this.regiaoAtual === 'pradaria_inicial') window.AudioManager.tocarMusica('bgm_pradaria');
                else if (this.regiaoAtual === 'floresta_sombria') window.AudioManager.tocarMusica('bgm_floresta');
            }

            try {
                if (this.hud && typeof this.hud.clicouNaUI === 'function') {
                    if (this.hud.clicouNaUI(pointer)) return;
                }
            } catch(e) {}

            // 🤖 AUTO CAÇADA
            // Clique manual no mapa sempre cancela a Auto Caçada.
            if (
                this.motorCacada &&
                this.motorCacada.autoCacadaAtiva &&
                typeof this.motorCacada.pararAutoCacada === "function"
            ) {
                this.motorCacada.pararAutoCacada("clique manual no mapa", false);
            }
        
            this.target.set(pointer.worldX, pointer.worldY);
            this.isMoving = true;
            this.physics.moveToObject(this.player, this.target, 150);

        });
        this.cursores = this.input.keyboard.createCursorKeys();
        this.teclasWASD = this.input.keyboard.addKeys('W,A,S,D');

        // ==========================================
        // 🛡️ LIBERA TECLADO PARA CHAT / INPUTS
        // ==========================================
        try {
            const K = Phaser.Input.Keyboard.KeyCodes;

            [
                K.W,
                K.A,
                K.S,
                K.D,

                K.UP,
                K.DOWN,
                K.LEFT,
                K.RIGHT,

                // 🔥 IMPORTANTE:
                // createCursorKeys() também captura SPACE e SHIFT.
                // Se não liberarmos SPACE, não é possível escrever
                // frases normalmente nos inputs HTML.
                K.SPACE,
                K.SHIFT

            ].forEach(codigo => {
                this.input.keyboard.removeCapture(codigo);
            });

        } catch (e) {
            console.warn(
                "Aviso: não foi possível liberar as teclas para os inputs:",
                e
            );
        }

        this.instalarProtecaoTecladoInputs();
        
        if (typeof window.AudioManager !== 'undefined') {
            // Toca a música certa dependendo do mapa ao carregar a cena
            if (this.regiaoAtual === 'capital_eldora') {
                window.AudioManager.tocarMusica('bgm_capital');
            } else if (this.regiaoAtual === 'pradaria_inicial') {
                window.AudioManager.tocarMusica('bgm_pradaria');
            } else if (this.regiaoAtual === 'floresta_sombria') {
                window.AudioManager.tocarMusica('bgm_floresta');
            }
        }
        
        this.anims.create({
            key: 'anim_emoji_raiva',
            frames: this.anims.generateFrameNumbers('emoji_raiva', { start: 0, end: 3 }), 
            frameRate: 8, 
            repeat: -1    
        });

        if (this.regiaoAtual === 'capital_eldora') {
            let npcAtendente = this.add.sprite(42 * 32, 20 * 32, 'npc_atendente').setDepth(10);
            
            let nomeAtendente = this.criarPlaquinhaNome(npcAtendente.x, npcAtendente.y - 15, 'Lojista Flora');

            npcAtendente.setInteractive();
            npcAtendente.on('pointerover', () => { this.input.setDefaultCursor('pointer'); });
            npcAtendente.on('pointerout', () => { this.input.setDefaultCursor('default'); });

            npcAtendente.on('pointerdown', (pointer, localX, localY, event) => {
                event.stopPropagation(); 

                let dist = Phaser.Math.Distance.Between(this.player.x, this.player.y, npcAtendente.x, npcAtendente.y);
                
                if (dist < 80) { 
                    if (typeof window.abrirLojaReino === 'function') {
                        window.abrirLojaReino();
                    } else {
                        alert("A Lojista Flora está arrumando o estoque! (Verifique o F12)");
                    }
                } else { 
                    let aviso = this.add.text(this.player.x, this.player.y - 50, "Preciso chegar mais perto da Flora...", {
                        fontSize: '12px', fontFamily: 'Arial', color: '#ef4444', fontStyle: 'bold', stroke: '#000', strokeThickness: 3
                    }).setOrigin(0.5, 1).setDepth(100);
                    
                    this.tweens.add({ targets: aviso, y: aviso.y - 20, alpha: 0, duration: 2000, onComplete: () => aviso.destroy() });
                }
            });
        }
        // ==========================================
        // ⚒️ FORJA DO THOREK (SÓ NA CAPITAL)
        // ==========================================
        if (this.regiaoAtual === 'capital_eldora') {
            // Mantive as tuas coordenadas e aumentei o tamanho para 64x64 para clicar melhor
            let forjaThorek = this.physics.add.sprite(53 * 32, 27 * 32, 'item_forja').setDepth(20).setDisplaySize(64, 64);
            
            // Textinho flutuante em cima da forja
            this.add.text(forjaThorek.x, forjaThorek.y - 35, 'Forja', {
                fontSize: '12px', color: '#f30808', fontFamily: 'Cinzel, Arial', 
                stroke: '#000', strokeThickness: 4, fontStyle: 'bold'
            }).setOrigin(0.5).setDepth(30);

            forjaThorek.setInteractive({ useHandCursor: true });
            forjaThorek.on('pointerover', () => this.input.setDefaultCursor('pointer'));
            forjaThorek.on('pointerout', () => this.input.setDefaultCursor('default'));

            forjaThorek.on('pointerdown', (pointer, localX, localY, event) => {
                if (event) event.stopPropagation(); // Trava o personagem para não andar
                
                let dist = Phaser.Math.Distance.Between(this.player.x, this.player.y, forjaThorek.x, forjaThorek.y);
                
                // Distância aumentada para 120 para compensar o tamanho da bigorna
                if (dist > 120) {
                    let aviso = this.add.text(this.player.x, this.player.y - 50, "Preciso me aproximar da Forja...", {
                        fontSize: '12px', fontFamily: 'Arial', color: '#ef4444', fontStyle: 'bold', stroke: '#000', strokeThickness: 3
                    }).setOrigin(0.5, 1).setDepth(100);
                    this.tweens.add({ targets: aviso, y: aviso.y - 20, alpha: 0, duration: 2000, onComplete: () => aviso.destroy() });
                } else {
                    // AQUI ESTÁ A CORREÇÃO! Chama a função do ficheiro forja.js
                    if (typeof window.abrirUIForja === 'function') {
                        window.abrirUIForja();
                    } else {
                        alert("Atenção: A interface não abriu! Verifique se adicionou o <script src='/static/js/forja.js'></script> no seu index.html");
                        console.error("Função window.abrirUIForja não encontrada.");
                    }
                }
            });
        }

        // ==========================================
        // 🔥 FORNALHA DE REFINO (SÓ NA CAPITAL)
        // ==========================================
        if (this.regiaoAtual === 'capital_eldora') {
            // Coloquei a fornalha um pouco mais para a esquerda (X: 47, Y: 27) para não encavalar com a Forja (X: 53)
            let fornalhaRefino = this.physics.add.sprite(45 * 32, 36 * 32, 'item_fornalha').setDepth(20).setDisplaySize(48, 48);
            
            // Pinta ela de um tom meio laranja/avermelhado para diferenciar da forja
            //fornalhaRefino.setTint(a10cf7); 
            
            // Textinho flutuante em cima da fornalha
            this.add.text(fornalhaRefino.x, fornalhaRefino.y - 35, 'Refino', {
                fontSize: '12px', color: '#2f0cf7', fontFamily: 'Cinzel, Arial', 
                stroke: '#000', strokeThickness: 4, fontStyle: 'bold'
            }).setOrigin(0.5).setDepth(30);

            fornalhaRefino.setInteractive({ useHandCursor: true });
            fornalhaRefino.on('pointerover', () => this.input.setDefaultCursor('pointer'));
            fornalhaRefino.on('pointerout', () => this.input.setDefaultCursor('default'));

            fornalhaRefino.on('pointerdown', (pointer, localX, localY, event) => {
                if (event) event.stopPropagation(); 
                
                let dist = Phaser.Math.Distance.Between(this.player.x, this.player.y, fornalhaRefino.x, fornalhaRefino.y);
                
                if (dist > 120) {
                    let aviso = this.add.text(this.player.x, this.player.y - 50, "Preciso me aproximar da Fornalha...", {
                        fontSize: '12px', fontFamily: 'Arial', color: '#ef44446e', fontStyle: 'bold', stroke: '#000', strokeThickness: 3
                    }).setOrigin(0.5, 1).setDepth(100);
                    this.tweens.add({ targets: aviso, y: aviso.y - 20, alpha: 0, duration: 2000, onComplete: () => aviso.destroy() });
                } else {
                    // Chama a função mágica do seu refinaria.js!
                    if (typeof window.abrirUIRefinaria === 'function') {
                        window.abrirUIRefinaria();
                    } else {
                        alert("Atenção: A interface não abriu! Verifique se adicionou o <script src='/static/js/refinaria.js'></script> no seu index.html");
                    }
                }
            });
        }
        // ==========================================
        this.input.on('gameobjectdown', (pointer, gameObject, event) => {
            
            // 🔥 TRAVA DE AÇÃO: Bloqueia clique em NPCs ou Monstros durante a coleta
            if (this.player && this.player.isGathering) {
                if (event) event.stopPropagation();
                return;
            }

            // 👇 NOVA LÓGICA: Se a imagem do objeto clicado começar com 'npc_', é um NPC interativo!
            if (gameObject.texture && gameObject.texture.key.startsWith('npc_')) {
    
                // 👇 COMENTE OU REMOVA ESTA LINHA! Ela está matando o clique do npc.
                // if (event) event.stopPropagation();
    
                let dist = Phaser.Math.Distance.Between(this.player.x, this.player.y, gameObject.x, gameObject.y);
                
                if (dist < 80) { 
                    if (typeof window.motorMissoesNPC !== 'undefined') {
                        // Dicionário mágico: Liga a textura da imagem ao ID real do NPC
                        const npcMapeamento = {
                            'npc_selene':    { id: 'selene', nome: 'Arquimaga Selene' },
                            'npc_thorek':    { id: 'thorek', nome: 'Mestre Thorek' },
                            'npc_varek':     { id: 'varek', nome: 'Capitão Varek' },
                            'npc_sylas':     { id: 'sylas', nome: 'Guarda-Bosque Sylas' },
                            'npc_grom':      { id: 'grom', nome: 'Grom o Caçador' },
                            'npc_elara':     { id: 'elara', nome: 'Madame Elara' },
                            'npc_borin':     { id: 'borin', nome: 'Mestre Bórin' },
                            'npc_paracelso': { id: 'paracelso', nome: 'Alquimista Paracelso' }
                        };

                       if (dadosNPC) {

                            // =====================================================
                            // 🛡️ CAPITÃO VAREK
                            //
                            // O Varek já possui toda a sequência q1, q2 e q3
                            // controlada pelo NPCsEngine.
                            //
                            // Então NÃO chamamos o MotorDeMissoesNPC para ele,
                            // evitando duas falas no mesmo clique.
                            // =====================================================
                            if (dadosNPC.id === 'varek') {
                                return;
                            }

                            // Outros NPCs continuam usando o sistema novo normalmente.
                            let imgURL =
                                `https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/npcs/${gameObject.texture.key}_rosto.png`;

                            window.motorMissoesNPC.interagir(
                                dadosNPC.id,
                                dadosNPC.nome,
                                imgURL
                            );
                        }
                    }
                } else { 
                    let aviso = this.add.text(this.player.x, this.player.y - 50, "Preciso me aproximar mais...", {
                        fontSize: '12px', fontFamily: 'Arial', color: '#ef4444', fontStyle: 'bold', stroke: '#000', strokeThickness: 3
                    }).setOrigin(0.5, 1).setDepth(100);
                    
                    this.tweens.add({ targets: aviso, y: aviso.y - 20, alpha: 0, duration: 2000, onComplete: () => aviso.destroy() });
                }
            }
        });

        if (this.veioDeRespawn) {
            this.tocarAnimacaoRenascimento();
            this.veioDeRespawn = false; 
        }
        this.time.delayedCall(1500, () => {
            this.travadoNoPortal = false;
            console.log("🌍 Portais destravados e prontos para uso!");
        });
        // ==========================================
        // 🌿 SISTEMA DE RECURSOS (BRILHO PERMANENTE)
        // ==========================================
        this.recursosNoMapa = []; 

        const spawnRecurso = (idUnico, tipoRecurso, nomeExibicao, skinRecurso, tileX, tileY) => {
            let posX = tileX * 32;
            let posY = tileY * 32;
            
            let recurso = this.physics.add.sprite(posX, posY, skinRecurso).setDepth(13);
            // 👇 ADICIONE ESTAS 3 LINHAS PARA FORÇAR O TAMANHO DA PENA 👇
            if (skinRecurso === 'item_pena') {
                recurso.setDisplaySize(48, 48); // Esmaga a imagem gigante para caber num bloquinho de 32x32!
            }
            recurso.tipo = tipoRecurso;
            recurso.id = idUnico;
            recurso.estoque = 50; // Quantidade máxima
            
            // Texto mostrando quanto falta
            recurso.label = this.add.text(posX, posY - 30, `${nomeExibicao} (${recurso.estoque}/50)`, {
                fontSize: '11px', color: '#a7f3d0', fontFamily: 'Arial', stroke: '#000', strokeThickness: 3
            }).setOrigin(0.5).setDepth(30).setVisible(false);

            recurso.setInteractive({ useHandCursor: true });
            
            // ⭐ O CONTORNO BRILHANTE (AGORA FICA LIGADO PARA SEMPRE) ⭐

            // O mouse agora só muda o cursor (a mãozinha), não mexe mais no brilho
            recurso.on('pointerover', () => {
                this.input.setDefaultCursor('pointer'); 
            });
            
            recurso.on('pointerout', () => {
                this.input.setDefaultCursor('default'); 
            });
            
            // ⭐ AÇÃO DE CORTAR (COM PRÉ-VERIFICAÇÃO DE FERRAMENTA) ⭐
            recurso.on('pointerdown', async (pointer, localX, localY, event) => {
                if (event) event.stopPropagation();
                if (this.player.isGathering) return; 
                if (recurso.estoque <= 0) return; 
                
                let dist = Phaser.Math.Distance.Between(this.player.x, this.player.y, recurso.x, recurso.y);
                if (dist > 60) {
                    // 1. Faz o personagem andar até o recurso clicado
                    this.target.set(recurso.x, recurso.y);
                    this.isMoving = true;
                    this.physics.moveToObject(this.player, this.target, 150);

                    // 2. Mostra um aviso mais amigável de que ele está a caminho
                    let aviso = this.add.text(this.player.x, this.player.y - 50, "Me aproximando...", {
                        fontSize: '12px', fontFamily: 'Arial', color: '#facc15', fontStyle: 'bold', stroke: '#000', strokeThickness: 3
                    }).setOrigin(0.5, 1).setDepth(100);
        
                    this.tweens.add({ targets: aviso, y: aviso.y - 20, alpha: 0, duration: 1500, onComplete: () => aviso.destroy() });
        
                    // 3. Retorna para impedir que a coleta inicie enquanto ele ainda está longe
                    return; 
                }

                // ===============================================
                // 🛑 TRAVA DE PROFISSÃO: Cada macaco no seu galho!
                // ===============================================
                const p = window.perfilDadosGlobais || {};

                function normalizarProfissaoColetaMapa(valor) {
                    return String(valor || "")
                        .trim()
                        .toLowerCase()
                        .normalize("NFD")
                        .replace(/[\u0300-\u036f]/g, "");
                }

                function jogadorTemProfissaoColetaMapa(player, profExigida) {
                    profExigida = normalizarProfissaoColetaMapa(profExigida);

                    if (!profExigida) return true;

                    const encontradas = [];

                    const profAtual = player?.profession || {};

                    if (typeof profAtual === "string") {
                        encontradas.push(profAtual);
                    } else if (profAtual && typeof profAtual === "object") {
                        encontradas.push(profAtual.key);
                        encontradas.push(profAtual.type);

                        // Compatibilidade com formatos antigos:
                        // profession: {"colhedor": {"level": 1}}
                        Object.keys(profAtual).forEach(k => encontradas.push(k));
                    }

                    const learned = player?.learned_professions || {};

                    if (Array.isArray(learned)) {
                        learned.forEach(prof => {
                            if (typeof prof === "string") {
                                encontradas.push(prof);
                            } else if (prof && typeof prof === "object") {
                                encontradas.push(prof.key);
                                encontradas.push(prof.type);
                                encontradas.push(prof.profession);
                            }
                        });
                    } else if (learned && typeof learned === "object") {
                        Object.entries(learned).forEach(([key, value]) => {
                            encontradas.push(key);

                            if (typeof value === "string") {
                                encontradas.push(value);
                            } else if (value && typeof value === "object") {
                                encontradas.push(value.key);
                                encontradas.push(value.type);
                                encontradas.push(value.profession);
                            }
                        });
                    }

                    return encontradas.some(x => normalizarProfissaoColetaMapa(x) === profExigida);
                }

                const mapaProfissao = {
                    'madeira': 'lenhador',
                    'pedra': 'minerador',
                    'minerio_de_ferro': 'minerador',
                    'linho': 'colhedor',
                    'pena': 'esfolador',
                    'sangue': 'alquimista'
                };

                const profExigida = normalizarProfissaoColetaMapa(mapaProfissao[recurso.tipo]);

                let temProfissao = jogadorTemProfissaoColetaMapa(p, profExigida);

                if (profExigida && !temProfissao) {
                    let avisoProf = this.add.text(this.player.x, this.player.y - 50, `Requer: ${profExigida.toUpperCase()}`, {
                        fontSize: '12px', fontFamily: 'Arial', color: '#ef4444', fontStyle: 'bold', stroke: '#000', strokeThickness: 3
                    }).setOrigin(0.5, 1).setDepth(100);
                    
                    this.tweens.add({ targets: avisoProf, y: avisoProf.y - 20, alpha: 0, duration: 2000, onComplete: () => avisoProf.destroy() });
                    return;
                }

                // 1. TRAVA INICIAL E VERIFICAÇÃO NO SERVIDOR
                this.player.isGathering = true;
                this.pararPersonagem(); 

                // ✨ LIGA O BRILHO DOURADO AQUI (Ao iniciar a tentativa) ✨
                try {
                    recurso.fxGlow = recurso.preFX.addGlow(0xfacc15, 4, 0, false); // 0xfacc15 = Dourado
                } catch(e) {
                    recurso.setTint(0xfacc15); // Fallback para PCs/Telemóveis mais fracos
                }

                const charId = localStorage.getItem("jogadorEldoraID");

                try {
                    // Pergunta rápida ao servidor: "Tenho a ferramenta?"
                    const res = await fetch('/api/personagem/coletar', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user_id: charId, recurso_tipo: recurso.tipo, acao: 'verificar' }) 
                    });
                    
                    const data = await res.json();

                    // SE O SERVIDOR BARROU (NÃO TEM FERRAMENTA)
                    if (!data.success) {
                        this.player.isGathering = false; 
                        
                        // ❌ TIRA O BRILHO DOURADO SE DER ERRO ❌
                        if (recurso.fxGlow) { recurso.preFX.remove(recurso.fxGlow); recurso.fxGlow = null; }
                        recurso.clearTint();
                        
                        let avisoFerramenta = this.add.text(this.player.x, this.player.y - 50, data.error || "Não pode coletar!", {
                            fontSize: '12px', fontFamily: 'Arial', color: '#ef4444', fontStyle: 'bold', stroke: '#000', strokeThickness: 3
                        }).setOrigin(0.5, 1).setDepth(100);
                        
                        this.tweens.add({ targets: avisoFerramenta, y: avisoFerramenta.y - 20, alpha: 0, duration: 2000, onComplete: () => avisoFerramenta.destroy() });
                        return; 
                    }

                    // ===============================================
                    // SE CHEGOU AQUI, TEM A FERRAMENTA. COMEÇA O TRABALHO!
                    // ===============================================
                    
                    let tempoTrabalho = 120000; // Coloquei 5s pra teste rápido, mude para 60000 depois!
                    
                    // 🌟 1. CONTAINER DA UI 🌟
                    let uiContainer = this.add.container(this.player.x, this.player.y - 55).setDepth(200);

                    // Texto "Coletando..." centralizado e Amarelinho
                    let textoColeta = this.add.text(0, -16, "Coletando...", {
                        fontSize: '10px', fontFamily: 'Arial', color: '#facc15', stroke: '#000', strokeThickness: 3, fontStyle: 'bold'
                    }).setOrigin(0.5);

                    // 🌟 2. FUNDO DA BARRA (Cantos Arredondados) 🌟
                    let bgBar = this.add.graphics();
                    bgBar.fillStyle(0x0f172a, 0.8); // Fundo escuro azulado
                    bgBar.lineStyle(1.5, 0xca8a04, 1); // Borda Dourada
                    // Parâmetros: X, Y, Largura, Altura, Raio (Arredondamento)
                    bgBar.fillRoundedRect(-25, -4, 50, 8, 4); 
                    bgBar.strokeRoundedRect(-25, -4, 50, 8, 4);

                    // 🌟 3. BARRA DE PREENCHIMENTO 🌟
                    let fillBar = this.add.graphics();

                    // Adiciona tudo ao container
                    uiContainer.add([bgBar, fillBar, textoColeta]);

                    // Animações de esforço e pulsação
                    let pulsoTexto = this.tweens.add({ targets: textoColeta, alpha: 0.4, yoyo: true, duration: 600, repeat: -1 });
                    let animBatida = this.tweens.add({ targets: this.player, y: this.player.y - 3, angle: 5, yoyo: true, duration: 350, repeat: -1 });

                    // 🌟 4. A MÁGICA DE ENCHER A BARRA 🌟
                    // Criamos um objeto falso só para o Tween aumentar o valor de 0 até 46
                    let progresso = { valor: 0 };

                    this.tweens.add({
                        targets: progresso,
                        valor: 46, // Largura máxima interna (50 - margens)
                        duration: tempoTrabalho, 
                        onUpdate: () => {
                            // A cada milissegundo, a barra é redesenhada maior!
                            fillBar.clear();
                            if (progresso.valor > 0) {
                                fillBar.fillStyle(0xfacc15, 1); // 👈 Amarelo Eldora
                                fillBar.fillRoundedRect(-23, -2, progresso.valor, 4, 2); 
                            }
                        },
                        onComplete: () => {
                            // ❌ TIRA O BRILHO DOURADO QUANDO TERMINA A COLETA ❌
                            if (recurso.fxGlow) { recurso.preFX.remove(recurso.fxGlow); recurso.fxGlow = null; }
                            recurso.clearTint();

                            animBatida.stop();
                            this.player.y = this.player.y; 
                            this.player.angle = 0; 
                            
                            pulsoTexto.stop();
                            uiContainer.destroy(); 
                            
                            this.player.isGathering = false;
                            
                            recurso.estoque -= 1;
                            recurso.label.setText(`${nomeExibicao} (${recurso.estoque}/50)`);
                            
                            this.coletarRecursoAPI(recurso);

                            if (recurso.estoque <= 0) {
                                recurso.setVisible(false);
                                recurso.label.setVisible(false);
                                recurso.disableInteractive();
                                
                                setTimeout(() => {
                                    recurso.estoque = 50;
                                    recurso.label.setText(`${nomeExibicao} (${recurso.estoque}/50)`);
                                    recurso.setVisible(true);
                                    recurso.setInteractive();
                                }, 3600000); 
                            }
                        }
                    });

                } catch (e) {
                    this.player.isGathering = false; 
                    // ❌ TIRA O BRILHO DOURADO SE A REDE CAIR ❌
                    if (recurso.fxGlow) { recurso.preFX.remove(recurso.fxGlow); recurso.fxGlow = null; }
                    recurso.clearTint();
                    console.error("Erro ao verificar coleta:", e);
                }
            });
        }
        // 👇 DISTRIBUIÇÃO LÓGICA PELAS REGIÕES 👇
        // Substitua os números (X, Y) pelas coordenadas reais do seu Tiled!
        if (this.regiaoAtual === 'pradaria_inicial') {
            // Pradaria: Local do Grom (Iniciantes)
            spawnRecurso('pedra_1', 'pedra', '🪨 Rocha', 'item_pedra', 10, 15);
            spawnRecurso('pedra_2', 'pedra', '🪨 Rocha', 'item_pedra', 45, 10);
            spawnRecurso('linho_1', 'linho', '🌿 Linho', 'item_linho', 20, 30);
            spawnRecurso('linho_2', 'linho', '🌿 Linho', 'item_linho', 22, 32);
            spawnRecurso('arvore_1', 'madeira', '🌳 Árvore', 'item_arvore', 2, 26);
            spawnRecurso('arvore_1', 'madeira', '🌳 Árvore', 'item_arvore', 5, 36);
            spawnRecurso('ninho_1', 'pena', '🪶 Ninho de Harpia', 'item_pena', 28, 20);
        }
        else if (this.regiaoAtual === 'floresta_sombria') {
            // Floresta: Local do Sylas (Mais perigoso)
            spawnRecurso('arvore_2', 'madeira', '🌳 Carvalho Ancestral', 'item_arvore', 20, 18);
            spawnRecurso('arvore_3', 'madeira', '🌳 Carvalho Ancestral', 'item_arvore', 28, 25);
            spawnRecurso('veio_ferro_1', 'minerio_de_ferro', '🪨 Veio de Ferro', 'item_ferro', 35, 10);
            spawnRecurso('poca_sangue_1', 'sangue', '🩸 Poça Sombria', 'item_sangue', 32, 22);
        
        }
        else if (this.regiaoAtual === 'pedreira_granito') {
            // Minas: Local do Bórin
            spawnRecurso('pedra_1', 'pedra', '🪨 Rocha', 'item_pedra', 52, 7);
            spawnRecurso('pedra_2', 'pedra', '🪨 Rocha', 'item_pedra', 45, 16);
            spawnRecurso('veio_ferro_granito_1', 'minerio_de_ferro', '🪨 Veio de Ferro', 'item_ferro', 16, 9);
            spawnRecurso('veio_ferro_granito_2', 'minerio_de_ferro', '🪨 Veio de Ferro', 'item_ferro', 18, 15);
            spawnRecurso('veio_ferro_granito_3', 'minerio_de_ferro', '🪨 Veio de Ferro', 'item_ferro', 35, 10);
            spawnRecurso('poca_sangue_1', 'sangue', '🩸 Poça Sombria', 'item_sangue', 32, 22);
        
        }
        // Nota: capital_eldora não tem recursos para manter a cidade limpa.

        /// ==========================================
        // 📡 FUNÇÃO DE COMUNICAÇÃO COM O BACKEND (CORRIGIDA)
        // ==========================================
        this.coletarRecursoAPI = async (recurso) => {
            const charId = localStorage.getItem("jogadorEldoraID");

            try {
                const res = await fetch('/api/personagem/coletar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: charId, recurso_tipo: recurso.tipo, recurso_id: recurso.id })
                });
                
                const data = await res.json();
                
                if (data.success) {
                    // Efeito de texto subindo (+1 Madeira)
                    let floatText = this.add.text(recurso.x, recurso.y - 40, `+${data.quantidade} ${data.item_nome}`, {
                        fontSize: '14px', color: '#2ecc71', stroke: '#000', strokeThickness: 4, fontStyle: 'bold'
                    }).setOrigin(0.5).setDepth(100);
                    
                    this.tweens.add({ targets: floatText, y: floatText.y - 40, alpha: 0, duration: 2000, onComplete: () => floatText.destroy() });
                    
                    if (typeof window.AudioManager !== 'undefined') window.AudioManager.tocarSFX('som_coleta');

                    if (typeof window.carregarMeuPerfil === 'function') window.carregarMeuPerfil();
                    
                    // 🔥 APAGAMOS AQUI O CÓDIGO VELHO QUE FAZIA A ÁRVORE SUMIR!
                    // Agora a árvore só vai sumir quando o recurso.estoque chegar a 0 lá no spawnRecurso!

                } else {
                    if (window.alertaEldora) window.alertaEldora("Falha na Coleta", data.error, "erro");
                }
            } catch (e) {
                console.error(e);
            }
        };
    }

        instalarProtecaoTecladoInputs() {
        if (window.__eldoraProtecaoTecladoInputsInstalada) return;
        window.__eldoraProtecaoTecladoInputsInstalada = true;

        const ehCampoTexto = (el) => {
            if (!el) return false;

            const tag = String(el.tagName || "").toUpperCase();

            return (
                tag === "INPUT" ||
                tag === "TEXTAREA" ||
                tag === "SELECT" ||
                el.isContentEditable
            );
        };

        const campoEstaVisivel = (el) => {
            if (!el) return false;

            const style = getComputedStyle(el);
            if (style.display === "none" || style.visibility === "hidden") return false;

            const rect = el.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0;
        };

        const pausarTecladoMapa = () => {
            try {
                const cenaMapa = window.jogoEldora?.scene?.getScene("MapaScene");
                if (cenaMapa && cenaMapa.input && cenaMapa.input.keyboard) {
                    cenaMapa.input.keyboard.enabled = false;
                }
            } catch (e) {}
        };

        const liberarTecladoMapa = () => {
            try {
                const ativo = document.activeElement;

                // Se ainda está digitando em campo visível, mantém o teclado do mapa pausado.
                if (ehCampoTexto(ativo) && campoEstaVisivel(ativo)) {
                    return;
                }

                const cenaMapa = window.jogoEldora?.scene?.getScene("MapaScene");
                if (cenaMapa && cenaMapa.input && cenaMapa.input.keyboard) {
                    cenaMapa.input.keyboard.enabled = true;
                }
            } catch (e) {}
        };

        document.addEventListener("focusin", (evt) => {
            if (ehCampoTexto(evt.target)) {
                pausarTecladoMapa();
            }
        }, true);

        document.addEventListener("focusout", () => {
            setTimeout(liberarTecladoMapa, 80);
        }, true);

        document.addEventListener("keydown", (evt) => {
            const alvo = evt.target;

            if (!ehCampoTexto(alvo)) return;

            // Enter continua enviando mensagem normalmente.
            if (evt.key === "Enter") {
                if (alvo.id === "input-balao-mapa") {
                    evt.preventDefault();
                    if (typeof window.enviarBalaoMapa === "function") {
                        window.enviarBalaoMapa();
                    }
                }

                if (alvo.id === "input-chat") {
                    evt.preventDefault();
                    if (typeof window.enviarMensagemChat === "function") {
                        window.enviarMensagemChat();
                    }
                }
            }
        }, true);

        // Se uma janela fechar e deixar input escondido ainda focado,
        // isso tira o foco e devolve o WASD ao mapa.
        setInterval(() => {
            const ativo = document.activeElement;

            if (ehCampoTexto(ativo) && !campoEstaVisivel(ativo)) {
                ativo.blur();
                liberarTecladoMapa();
            }
        }, 300);
    }
    
    update() {
        if (!this.graficosProntos) {
            this.graficosProntos = true; // Garante que isso só rode 1 vez
            
            // O jogo JÁ PINTOU o primeiro frame na tela! Agora sim tiramos o loading do HTML.
            if (typeof window.finalizarCarregamento === 'function') {
                window.finalizarCarregamento();
            }
            
            // Bônus Épico: O mapa vai clarear suavemente saindo do escuro para disfarçar qualquer piscar de imagem!
            this.cameras.main.fadeIn(800, 0, 0, 0);
        }

        if (this.playerNameText) {
            this.playerNameText.setPosition(Math.floor(this.player.x), Math.floor(this.player.y - 30));
        }
    
        if (this.interativo) {
            this.interativo.verificarProximidade(this.player);
        }

        // 🤖 AUTO CAÇADA
        // Verifica se o personagem já chegou perto do mob escolhido.
        if (this.motorCacada && typeof this.motorCacada.verificarAutoCacada === "function") {
            this.motorCacada.verificarAutoCacada();
        }

        // 🛑 TRAVA DE SEGURANÇA (Não apague isso, impede o boneco de andar morto)
        if (this.isDead || this.travadoNoPortal) return;

        // ====================================================
        // 🎮 NOVA FÍSICA DE MOVIMENTO (JOYSTICK + TECLADO)
        // ====================================================
        let moveX = 0;
        let moveY = 0;

        // Se o jogador estiver digitando no chat/input,
        // WASD e setas não movem o personagem.
        const elementoAtivo = document.activeElement;
        const digitandoTexto =
            elementoAtivo &&
            (
                elementoAtivo.tagName === "INPUT" ||
                elementoAtivo.tagName === "TEXTAREA" ||
                elementoAtivo.tagName === "SELECT" ||
                elementoAtivo.isContentEditable
            );

        if (!digitandoTexto) {
            if (this.cursores.left.isDown || this.teclasWASD.A.isDown) moveX = -1;
            else if (this.cursores.right.isDown || this.teclasWASD.D.isDown) moveX = 1;

            if (this.cursores.up.isDown || this.teclasWASD.W.isDown) moveY = -1;
            else if (this.cursores.down.isDown || this.teclasWASD.S.isDown) moveY = 1;
        }

        // Novo analógico real: movimento livre em qualquer direção.
        const joyVector = window.joyVector || null;
        const usandoAnalogico =
            joyVector &&
            joyVector.active &&
            Math.sqrt((joyVector.x * joyVector.x) + (joyVector.y * joyVector.y)) > 0.08;

        if (usandoAnalogico) {
            moveX = joyVector.x;
            moveY = joyVector.y;
        }

        if (moveX !== 0 || moveY !== 0) {
            // 🤖 AUTO CAÇADA
            // Movimento manual por teclado/joystick cancela a Auto Caçada.
            if (
                this.motorCacada &&
                this.motorCacada.autoCacadaAtiva &&
                typeof this.motorCacada.pararAutoCacada === "function"
            ) {
                this.motorCacada.pararAutoCacada("movimento manual", false);
            }

            // Cancelar clique se usar o controle
            this.isMoving = false; 
            this.target.copy(this.player);
            
            const velocidadeBase = 150; 
            const vector = new Phaser.Math.Vector2(moveX, moveY);

            if (vector.length() > 1) {
                vector.normalize();
            }

            const intensidadeAnalogico = usandoAnalogico
                ? Math.max(0.35, Math.min(1, Number(joyVector.intensity || vector.length())))
                : 1;
            
            this.player.setVelocity(
                vector.x * velocidadeBase * intensidadeAnalogico,
                vector.y * velocidadeBase * intensidadeAnalogico
            );
            
            // Animações enquanto anda no analógico/teclado
            try {
                let chave = '_' + this.player.texture.key;
                if (Math.abs(moveX) > Math.abs(moveY)) { 
                    moveX > 0 ? this.player.anims.play('right' + chave, true) : this.player.anims.play('left' + chave, true); 
                } else { 
                    moveY > 0 ? this.player.anims.play('down' + chave, true) : this.player.anims.play('up' + chave, true); 
                }
            } catch(e) {}
            
        } else {
            // ====================================================
            // 🖱️ MANTÉM SEU SISTEMA DE CLIQUE ORIGINAL AQUI
            // ====================================================
            if (this.isMoving) {
                let dist = Phaser.Math.Distance.Between(this.player.x, this.player.y, this.target.x, this.target.y);
            
                if (dist < 5) {
                    this.pararPersonagem();
                } else {
                    const vxReal = this.player.body.velocity.x;
                    const vyReal = this.player.body.velocity.y;

                    if (Math.abs(vxReal) < 5 && Math.abs(vyReal) < 5) {
                        this.pararPersonagem();
                    } else {
                        this.physics.moveToObject(this.player, this.target, 150);

                        const vxNovo = this.player.body.velocity.x;
                        const vyNovo = this.player.body.velocity.y;

                        try {
                            let chave = '_' + this.player.texture.key;
                            if (Math.abs(vxNovo) > Math.abs(vyNovo)) { 
                                vxNovo > 0 ? this.player.anims.play('right' + chave, true) : this.player.anims.play('left' + chave, true); 
                            } else { 
                                vyNovo > 0 ? this.player.anims.play('down' + chave, true) : this.player.anims.play('up' + chave, true); 
                            }
                        } catch(e) {}
                    }
                }
            } else {
                // 🛑 AQUI ESTÁ A CORREÇÃO: O boneco fica 100% parado e olhando para frente
                this.player.setVelocity(0, 0);
                try {
                    this.player.anims.stop();
                    this.player.setFrame(1); // Frame padrão de "parado" na maioria dos seus sprites
                } catch(e) {}
            }
        }

        this.verificarTransicoes();
    }

    verificarTransicoes() {
        // Se o personagem acabou de nascer ou já está mudando de cena, cancela a leitura do portal!
        if (this.isDead || this.veioDeRespawn || this.travadoNoPortal) return;

        const mapaContexto = this.make.tilemap({ key: this.regiaoAtual });
        const camadaTransicoes = mapaContexto.getObjectLayer('Transicoes');

        if (camadaTransicoes && camadaTransicoes.objects) {
            camadaTransicoes.objects.forEach(obj => {
                let zona = new Phaser.Geom.Rectangle(obj.x, obj.y, obj.width, obj.height);
                
                if (Phaser.Geom.Rectangle.Contains(zona, this.player.x, this.player.y)) {
                    
                    let destino = null;
                    let nasceX = 10; 
                    let nasceY = 10; 

                    if (obj.properties && Array.isArray(obj.properties)) {
                        let propDestino = obj.properties.find(p => p.name === 'destino');
                        let propX = obj.properties.find(p => p.name === 'nasce_x');
                        let propY = obj.properties.find(p => p.name === 'nasce_y');

                        if (propDestino) destino = propDestino.value;
                        if (propX) nasceX = propX.value;
                        if (propY) nasceY = propY.value;
                    }

                    if (destino && this.regiaoAtual !== destino) {
                        console.log(`Viajando de ${this.regiaoAtual} para ${destino} (Spawn: X=${nasceX}, Y=${nasceY})`);
                        
                        let telaLoad = document.getElementById('tela-carregamento');
                        if (telaLoad) {
                            telaLoad.style.display = 'flex';
                            telaLoad.style.opacity = '1';
                            if (typeof window.atualizarCarregamento === 'function') {
                                window.atualizarCarregamento(50, "Viajando para " + destino + "...");
                            }
                        }

                        // Trava absoluta para impedir loops
                        this.travadoNoPortal = true;
                        this.isMoving = false;
                        this.player.body.stop();
                        
                        this.scene.restart({
                            regiao: destino, 
                            skin: this.skinAtiva,
                            spawnX: nasceX * 32, 
                            spawnY: nasceY * 32
                        });
                    }
                }
            });
        }
    }

    pararPersonagem() {
        this.player.body.stop();
        this.isMoving = false;
        this.player.anims.stop();
        this.player.setFrame(1);

        localStorage.setItem("eldora_lastX", Math.round(this.player.x));
        localStorage.setItem("eldora_lastY", Math.round(this.player.y));
        localStorage.setItem("eldora_lastRegiao", this.regiaoAtual);

        if (typeof socket !== 'undefined' && socket) {
            socket.emit('mover', { 
                x: Math.round(this.player.x), 
                y: Math.round(this.player.y), 
                skin: this.skinResolvida || this.skinAtiva 
            });
        }

        const uid = localStorage.getItem("jogadorEldoraID");
        if (uid) {
            fetch('/api/save_position', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_id: uid,
                    position: { x: Math.round(this.player.x), y: Math.round(this.player.y), regiao: this.regiaoAtual }
                })
            }).catch(()=>{}); 
        }
    }

    gerarAnimacoes(skin) {
        if (this.anims.exists('down_' + skin)) return;
        this.anims.create({ key: 'down_' + skin, frames: this.anims.generateFrameNumbers(skin, { start: 0, end: 2 }), frameRate: 10, repeat: -1 });
        this.anims.create({ key: 'left_' + skin, frames: this.anims.generateFrameNumbers(skin, { start: 3, end: 5 }), frameRate: 10, repeat: -1 });
        this.anims.create({ key: 'right_' + skin, frames: this.anims.generateFrameNumbers(skin, { start: 6, end: 8 }), frameRate: 10, repeat: -1 });
        this.anims.create({ key: 'up_' + skin, frames: this.anims.generateFrameNumbers(skin, { start: 9, end: 11 }), frameRate: 10, repeat: -1 });
    }

    tocarAnimacaoRenascimento() {
        if (!this.player) return;

        if (typeof window.AudioManager !== 'undefined') {
            window.AudioManager.tocarSFX('som_spawn');
        }

        if (!this.anims.exists('anim_respawn')) {
            this.anims.create({
                key: 'anim_respawn',
                frames: this.anims.generateFrameNumbers('circulo_magico', { start: 0, end: 15 }),
                frameRate: 6,  
                repeat: 0,     
                hideOnComplete: true 
            });
        }

        let circulo = this.add.sprite(this.player.x, this.player.y + 15, 'circulo_magico').setDepth(this.player.depth - 1);
        circulo.setScale(2.5);
        circulo.setBlendMode(Phaser.BlendModes.ADD); 
        circulo.play('anim_respawn');

        circulo.on('animationcomplete', () => {
            circulo.destroy();
        });

        this.cameras.main.flash(1200, 255, 255, 255); 

        let texto = this.add.text(this.player.x, this.player.y - 40, "RESSUSCITADO", {
            fontFamily: 'Cinzel, Arial', fontSize: '14px', color: '#d946ef', stroke: '#000000', strokeThickness: 5, fontStyle: 'bold'
        }).setOrigin(0.5).setDepth(this.player.depth + 20);

        this.tweens.add({
            targets: texto,
            y: texto.y - 50,
            alpha: 0,
            duration: 3500, 
            ease: 'Power1',
            onComplete: () => texto.destroy()
        });

        this.tweens.add({
            targets: this.player,
            alpha: 0.3,
            yoyo: true,
            repeat: 7, 
            duration: 350 
        });
        // 👇 ADICIONE ESTAS LINHAS AQUI 👇
        // Isso força a interface a atualizar os anéis de HP/MP e ler a vida cheia do banco de dados
        setTimeout(() => {
            if (typeof window.carregarMeuPerfil === 'function') window.carregarMeuPerfil();
            if (typeof window.atualizarHudCircular === 'function') window.atualizarHudCircular();
        }, 500);
    } 

    iniciarFuneralNoLocal() {
        // 🛡️ TRAVA DE SEGURANÇA: Impede que a função rode se o jogador já estiver morto
        if (!this.player || this.isDead) return;

        // Coordenadas de Resgate (Catedral de Eldora)
        const resgateX = 55 * 32;
        const resgateY = 13 * 32;

        // 🛑 PARADA IMEDIATA DE MOVIMENTO E FÍSICA
        this.isDead = true; // Ativa a trava de input imediatamente
        this.isMoving = false; // Reseta o estado de caminhada do update
        
        if (this.player.body) {
            this.player.body.stop(); // Para a inércia atual
            this.player.body.setEnable(false); // Desativa a física para não ser empurrado por mobs
        }

        // 📢 MULTIPLAYER: Avisa o servidor para mostrar a lápide aos outros jogadores
        if (typeof socket !== 'undefined' && socket) {
            socket.emit('jogador_morreu', { 
                x: Math.round(this.player.x), 
                y: Math.round(this.player.y), 
                nome: localStorage.getItem("jogadorEldoraNome") || "Um herói"
            });
        }

        // Configurações visuais locais
        this.player.setVisible(false);
        if (this.playerNameText) this.playerNameText.setVisible(false);
        this.cameras.main.stopFollow(); // Câmera trava no local da morte

        // Cria a lápide localmente para o jogador
        let tumulo = this.add.sprite(this.player.x, this.player.y, 'img_lapide')
            .setOrigin(0.5, 1)
            .setDepth(5) 
            .setDisplaySize(28, 48);
        
        // Texto do cronômetro de ressurreição
        let tempoRestante = 10;
        let tempoTxt = this.add.text(this.player.x, this.player.y - 60, tempoRestante + "s", {
            fontFamily: 'Cinzel, Arial', 
            fontSize: '18px', 
            color: '#ef4444', 
            stroke: '#000', 
            strokeThickness: 5, 
            fontStyle: 'bold'
        }).setOrigin(0.5).setDepth(this.player.depth + 1);
        
        // Evento de contagem regressiva
        this.time.addEvent({
            delay: 1000,
            repeat: 9,
            callback: () => {
                tempoRestante--;
                if (tempoRestante > 0) {
                    tempoTxt.setText(tempoRestante + "s");
                } else {
                    // Limpeza de objetos temporários antes do restart
                    tempoTxt.destroy(); 
                    tumulo.destroy();
                    
                    // Salva a nova posição de respawn na memória local
                    localStorage.setItem("eldora_lastX", resgateX);
                    localStorage.setItem("eldora_lastY", resgateY);
                    localStorage.setItem("eldora_lastRegiao", "capital_eldora");

                    // Reinicia a cena garantindo o reset de todas as variáveis de trava
                    this.scene.restart({
                        regiao: 'capital_eldora',
                        skin: this.skinAtiva,
                        isRespawn: true, 
                        spawnX: resgateX,
                        spawnY: resgateY
                    });
                }
            }
        });
        
    }
    // ==========================================
    // 🏷️ CRIADOR DE PLAQUINHAS DE NOME ESTILO RPG
    // ==========================================
    criarPlaquinhaNome(x, y, texto) {
        // Cria um container para segurar o fundo e o texto juntos
        let container = this.add.container(x, y).setDepth(30);

        // 1. Cria o Texto primeiro para sabermos a largura
        let txt = this.add.text(0, -8, texto, {
            fontSize: '11px',
            fontFamily: 'Arial',
            color: '#ffffff', // Texto branco
            fontStyle: 'bold'
        }).setOrigin(0.5, 1);

        let larg = txt.width + 16; // Margem horizontal
        let alt = txt.height + 8;  // Margem vertical

        let bg = this.add.graphics();

        // 2. Cores Exatas da Plaquinha (Marrom e Borda Escura)
        let corFundo = 0x5c3a21;
        let corBorda = 0x2a160c;

        bg.fillStyle(corFundo, 1);
        bg.lineStyle(2, corBorda, 1);

        let rx = -larg / 2;
        let ry = -txt.height - 12;

        // 3. Desenha o fundo arredondado
        bg.fillRoundedRect(rx, ry, larg, alt, 4);
        bg.strokeRoundedRect(rx, ry, larg, alt, 4);

        // 4. Desenha a setinha (triângulo) apontando para baixo
        bg.fillStyle(corFundo, 1);
        bg.fillTriangle(-5, ry + alt - 1, 5, ry + alt - 1, 0, ry + alt + 5);

        // 5. Desenha a linha escura contornando a setinha
        bg.lineStyle(2, corBorda, 1);
        bg.beginPath();
        bg.moveTo(-5, ry + alt);
        bg.lineTo(0, ry + alt + 5);
        bg.lineTo(5, ry + alt);
        bg.strokePath();

        // Junta tudo no container (o fundo entra primeiro para ficar atrás)
        container.add([bg, txt]);
        return container;
    }
}

let jogoEldora = null;

// ==========================================
// INICIALIZAÇÃO DO MAPA (COM MEMÓRIA DE POSIÇÃO)
// ==========================================
function iniciarMapa(reg, skin, x, y) {
    const largura = window.innerWidth;
    const altura = window.innerHeight;
    
    const PRACA_X = 27 * 32; 
    const PRACA_Y = 29 * 32;

    const config = { 
        type: Phaser.AUTO, 
        parent: 'game-container', 
        width: largura,    
        height: altura,
        pixelArt: false, 
        antialias: true,
        roundPixels: true, 
        scale: {
            mode: Phaser.Scale.RESIZE,
            autoCenter: Phaser.Scale.CENTER_BOTH
        },
        physics: { default: 'arcade', arcade: { debug: false } }, 
        render: {
            antialias: true,
            pixelArt: false,
            roundPixels: true,
            transparent: false
        },
        backgroundColor: '#000000' 
    };
    
    if (window.jogoEldora) {
        window.jogoEldora.destroy(true); 
    }
    
    let finalX = x ?? parseInt(localStorage.getItem("eldora_lastX")) ?? CATEDRAL_X;
    let finalY = y ?? parseInt(localStorage.getItem("eldora_lastY")) ?? CATEDRAL_Y;
    let finalReg = reg || localStorage.getItem("eldora_lastRegiao") || 'capital_eldora';

    window.jogoEldora = new Phaser.Game(config);
    
    window.jogoEldora.scene.add('MapaScene', MapaScene, true, { 
        regiao: finalReg, 
        skin: skin || window.minhaSkinAtual || 'aventureiro',
        spawnX: finalX, 
        spawnY: finalY 
    });

    localStorage.setItem("eldora_lastX", finalX);
    localStorage.setItem("eldora_lastY", finalY);
    localStorage.setItem("eldora_lastRegiao", finalReg);
}


window.animarLevelUpNoMapa = function(novoNivel) {
    const cena = window.jogoEldora.scene.getScene('MapaScene');
    if (!cena || !cena.player) return;

    const texto = cena.add.text(cena.player.x, cena.player.y - 50, `LEVEL UP! ${novoNivel}`, {
        fontFamily: 'Cinzel, serif',
        fontSize: '24px',
        fontWeight: '900',
        color: '#FFD700',
        stroke: '#000',
        strokeThickness: 4,
        align: 'center'
    }).setOrigin(0.5).setDepth(100).setScrollFactor(1); 

    cena.tweens.add({
        targets: texto,
        y: texto.y - 100, 
        alpha: 0,         
        scale: 1.5,       
        duration: 2000,
        ease: 'Power2',
        onComplete: () => texto.destroy() 
    });

}; 

// ==========================================
// ✨ EFEITO ÉPICO DE DESPERTAR DE CLASSE (COM SPRITE SHEET)
// ==========================================
window.animarDespertarClasse = function(nomeDaClasse, callbackFinal) {
    const cena = window.jogoEldora.scene.getScene('MapaScene');
    
    if (!cena || !cena.player) {
        if (callbackFinal) callbackFinal();
        return;
    }

    cena.player.body.stop();
    cena.isDead = true; 
    cena.player.anims.stop();
    cena.player.setFrame(1);

    if (typeof window.AudioManager !== 'undefined') {
        window.AudioManager.tocarSFX('som_spawn');
    }

    let escuridao = cena.add.rectangle(cena.player.x, cena.player.y, 2000, 2000, 0x000000, 0)
        .setDepth(cena.player.depth + 5);
    
    cena.tweens.add({
        targets: escuridao,
        fillAlpha: 0.7, 
        duration: 1000
    });

    cena.cameras.main.shake(3500, 0.008); 

    setTimeout(() => {
        cena.cameras.main.flash(500, 255, 255, 255); 

        if (!cena.anims.exists('anim_efeito_despertar')) {
            cena.anims.create({
                key: 'anim_efeito_despertar',
                frames: cena.anims.generateFrameNumbers('efeito_despertar', { start: 0, end: 11 }), 
                frameRate: 4, 
                repeat: 1,     
                hideOnComplete: true 
            });
        }

        let magia = cena.add.sprite(cena.player.x, cena.player.y + 40, 'efeito_despertar')
            .setDepth(cena.player.depth +1) 
            .setOrigin(0.5, 1) 
            .setAlpha(0.7) 
            .setBlendMode(Phaser.BlendModes.ADD); 

        magia.play('anim_efeito_despertar');

        magia.on('animationcomplete', () => {
            escuridao.destroy();
            magia.destroy();
        });

        setTimeout(() => {
            let falaMistica = `O firmamento reconhece seu poder! A ancestral linha de mana do ${nomeDaClasse} despertou em sua alma. Erga-se, herói de Eldora!`;
            
            window.mostrarDialogoRPG("Arquimaga Selene", falaMistica, () => {
                if (callbackFinal) callbackFinal();
            });
        }, 1000); 

    }, 1000); 
};

// ==========================================
// 🌍 EFEITO MULTIPLAYER: CÉU ESCURECENDO PARA TODOS (ÉPICO & LENTO)
// ==========================================
window.tocarEfeitoGlobalDespertar = function(nomeJogador, nomeDaClasse) {
    const cena = window.jogoEldora.scene.getScene('MapaScene');
    if (!cena) return;

    if (typeof window.AudioManager !== 'undefined') window.AudioManager.tocarSFX('som_spawn');

    cena.cameras.main.shake(6000, 0.005);

    let escuridao = cena.add.rectangle(
        cena.cameras.main.centerX, 
        cena.cameras.main.centerY, 
        4000, 4000, 0x000000, 0
    ).setDepth(9000).setScrollFactor(0);

    cena.tweens.add({
        targets: escuridao,
        fillAlpha: 0.85, 
        yoyo: true,      
        hold: 4000,      
        duration: 3000,  
        ease: 'Sine.easeInOut',
        onComplete: () => escuridao.destroy()
    });

    setTimeout(() => {
        cena.cameras.main.flash(500, 255, 255, 255); 
        if (typeof window.AudioManager !== 'undefined') window.AudioManager.tocarSFX('som_spawn'); 
    }, 2500);

    let textoAviso = cena.add.text(cena.cameras.main.centerX, cena.cameras.main.centerY - 80, 
        `O céu se contorce...\n${nomeJogador} despertou como ${nomeDaClasse}!`, {
        fontFamily: 'Cinzel, serif', 
        fontSize: '14px', 
        color: '#facc15', 
        stroke: '#000', 
        strokeThickness: 3,
        align: 'center',
        fontStyle: 'bold'
    }).setOrigin(0.5).setDepth(9001).setScrollFactor(0).setAlpha(0).setScale(0.8); 

    cena.tweens.add({
        targets: textoAviso,
        alpha: 1,
        scale: 1.2,      
        yoyo: true,
        hold: 3500,      
        duration: 2500,  
        ease: 'Sine.easeOut',
        delay: 1500,     
        onComplete: () => textoAviso.destroy()
    });
};

// ==========================================
// SISTEMA DE POÇÕES RÁPIDAS NO MAPA
// ==========================================
window.usarPocaoRapida = async function(tipoSlot) {
    const charId = localStorage.getItem("jogadorEldoraID");
    if (!charId) return;

    try {
        const res = await fetch('/api/personagem/usar_pocao_rapida', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ user_id: charId, tipo: tipoSlot }) 
        });
        
        const data = await res.json();
        
        if (data.sucesso) {
            // Efeito visual no Mapa (Texto subindo)
            if (window.jogoEldora) {
                const cena = window.jogoEldora.scene.getScene('MapaScene');
                if (cena && cena.player) {
                    let textoCura = cena.add.text(cena.player.x, cena.player.y - 40, `+${data.cura}`, {
                        fontFamily: 'Cinzel, Arial', fontSize: '20px', color: data.cor, 
                        stroke: '#000', strokeThickness: 4, fontStyle: 'bold'
                    }).setOrigin(0.5).setDepth(200);

                    cena.tweens.add({
                        targets: textoCura,
                        y: textoCura.y - 50,
                        alpha: 0,
                        duration: 1500,
                        ease: 'Power2',
                        onComplete: () => textoCura.destroy()
                    });
                }
            }
            
            // Toca um som de beber poção (se você tiver o AudioManager)
            if (typeof window.AudioManager !== 'undefined') {
                // Pode adicionar um som de "glup" depois se quiser
            }

            // Atualiza os anéis de HP/MP da interface imediatamente!
            // Atualiza perfil geral
            if (typeof carregarMeuPerfil === 'function') {
                carregarMeuPerfil();
            }

            // Atualiza os círculos HP/MP/XP
            if (typeof atualizarHudCircular === 'function') {
                atualizarHudCircular();
            }

            // Atualiza também a janela de status caso esteja aberta.
            // Isso atualiza HP/MP e também a quantidade das poções.
            if (typeof window.carregarDadosDoHUD === 'function') {
                window.carregarDadosDoHUD();
            }
            
        } else {
            // Se a poção acabou ou não equipou, avisa com o seu alerta bonito!
            if (window.alertaEldora) {
                window.alertaEldora("Aviso de Cinto", data.erro, "erro");
            } else {
                alert(data.erro);
            }
        }
    } catch(e) {
        console.error("Erro ao beber poção:", e);
    }
}

