// ==========================================
// MOTOR DE NPCs E MISSÕES - MUNDO DE ELDORA (BLINDADO)
// ==========================================

// Variáveis para controlar a animação do texto
let typewriterInterval;
let dialogoCallback = null;

// Função blindada que garante que a caixa apareça na tela
window.mostrarDialogoRPG = function(nome, texto, callbackEspecial = null) {
    if (typeof playClick === 'function') playClick();

    let container = document.getElementById('rpg-dialogo-container');

    // Se o HTML apagou a caixa, nós recriamos ela com prioridade máxima!
    if (!container) {
        const htmlBlindado = `
        <div id="rpg-dialogo-container" onclick="window.fecharDialogoRPG()" style="display: none; position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); width: 90%; max-width: 600px; background: rgba(15, 23, 42, 0.95); border: 3px solid #d4af37; border-radius: 12px; padding: 20px; z-index: 9999999; box-shadow: 0 0 20px rgba(0,0,0,0.8); cursor: pointer; backdrop-filter: blur(4px);">
            <div id="rpg-dialogo-nome" style="color: #facc15; font-family: 'Cinzel', serif; font-size: 22px; font-weight: 900; margin-bottom: 10px; text-shadow: 2px 2px 4px #000; border-bottom: 1px solid #d4af37; padding-bottom: 5px;"></div>
            <div id="rpg-dialogo-texto" style="color: #e2e8f0; font-family: Arial, sans-serif; font-size: 16px; line-height: 1.5;"></div>
            <div id="rpg-dialogo-seta" style="position: absolute; bottom: 10px; right: 20px; color: #facc15; font-size: 20px; animation: bounce 1s infinite;">▼</div>
            <style>@keyframes bounce { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(5px); } }</style>
        </div>`;
        document.body.insertAdjacentHTML('beforeend', htmlBlindado);
        container = document.getElementById('rpg-dialogo-container');
    }

    const elNome = document.getElementById('rpg-dialogo-nome');
    const elTexto = document.getElementById('rpg-dialogo-texto');

    elNome.innerText = nome;
    elTexto.innerHTML = "";
    container.style.display = 'block';
    dialogoCallback = callbackEspecial;

    clearInterval(window.typewriterInterval);
    let i = 0;
    
    window.typewriterInterval = setInterval(() => {
        elTexto.innerHTML += texto.charAt(i);
        i++;
        if (i >= texto.length) {
            clearInterval(window.typewriterInterval);
        }
    }, 25);
};

window.fecharDialogoRPG = function() {
    document.getElementById('rpg-dialogo-container').style.display = 'none';
    clearInterval(typewriterInterval); 
    
    if (dialogoCallback) {
        let tempCb = dialogoCallback;
        dialogoCallback = null;
        tempCb(); 
    }
};

class NPCsEngine {
    constructor(scene) {
        this.scene = scene;
        this.npcs = {};
        this.linkBaseNuvem = "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/classes/";
        
        // Injeta o HTML das Missões e Diálogos
        this.injetarInterfaceMissao();
    }

    injetarInterfaceMissao() {
        if (document.getElementById('rpg-dialogo-container')) return;

        const divDialogo = `
            <div id="rpg-dialogo-container" onclick="window.fecharDialogoRPG()">
                <div id="rpg-dialogo-box">
                    <div id="rpg-dialogo-nome">Nome do NPC</div>
                    <div id="rpg-dialogo-texto"></div>
                    <div id="rpg-dialogo-seta">▼</div>
                </div>
            </div>`;

        const divDiario = `
            <style>
                #btn-quest-log { background: transparent !important; border: none !important; outline: none !important; box-shadow: none !important; -webkit-appearance: none !important; -webkit-tap-highlight-color: rgba(0,0,0,0) !important; padding: 0; margin: 0; }
                #img-pergaminho-quest { transition: transform 0.15s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
                #btn-quest-log:hover #img-pergaminho-quest { transform: scale(1.15) !important; }
                #btn-quest-log:active #img-pergaminho-quest { transform: scale(1.3) !important; }
            </style>

            <button id="btn-quest-log" onclick="window.toggleDiarioQuests()" style="position: absolute; top: 170px; right: 10px; z-index: 10; cursor: pointer;">
                <div style="position: relative; display: flex; justify-content: center; align-items: center;">
                    <img id="img-pergaminho-quest" src="https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/ui/icone_pergaminho.png" style="width: 40px; height: 40px; filter: drop-shadow(2px 3px 4px rgba(0,0,0,0.8)); display: block;">
                    <div id="quest-badge" style="display: none; position: absolute; top: -1px; right: -1px; width: 10px; height: 10px; background: #ef4444; border: 2px solid #fff; border-radius: 50%; box-shadow: 0 2px 4px rgba(0,0,0,0.6); z-index: 2;"></div>
                </div>
            </button>

            <div id="modal-diario-quests" style="z-index: 100000;">
                <div class="diario-container">
                    <button onclick="window.toggleDiarioQuests()" style="position: absolute; top: 10px; right: 15px; background: transparent; border: none; color: #ca8a04; font-size: 1.5em; cursor: pointer; outline: none;">×</button>
                    <h2 style="color: #facc15; font-family: 'Cinzel', serif; text-align: center; margin-top: 0;">Diário de Aventuras</h2>
                    <div id="lista-de-quests" style="max-height: 300px; overflow-y: auto; margin-top: 15px;"></div>
                </div>
            </div>`;

        // 🔥 A MÁGICA FINAL: Injetar DENTRO do Mapa (aba-reino) em vez do document.body 🔥
        const abaReino = document.getElementById('aba-reino');
        if (abaReino) {
            abaReino.insertAdjacentHTML('beforeend', divDialogo + divDiario);
        } else {
            document.body.insertAdjacentHTML('beforeend', divDialogo + divDiario);
        }
    }

    spawnNPCAndante(id, nome, skin, posX, posY, destinoX, destinoY) {
        try {
            if (this.scene.textures.exists(skin)) {
                this.criarSprite(id, nome, skin, posX, posY, destinoX, destinoY);
            } else {
                this.scene.load.spritesheet(skin, `${this.linkBaseNuvem}${skin}.png`, { frameWidth: 48, frameHeight: 48 });
                this.scene.load.once(`filecomplete-spritesheet-${skin}`, () => {
                    this.criarSprite(id, nome, skin, posX, posY, destinoX, destinoY);
                });
                this.scene.load.start();
            }
        } catch (e) {
            console.error("[NPCsEngine] Erro:", e);
        }
    }

    criarSprite(id, nome, skinFinal, posX, posY, destinoX, destinoY) {
        try {
            if (!this.scene.textures.exists(skinFinal)) skinFinal = 'aventureiro_base'; 

            const npc = this.scene.physics.add.sprite(posX, posY, skinFinal).setDepth(14);
            npc.nome = nome;
            
            npc.setInteractive();
            npc.on('pointerdown', () => {
                const npcId = id.toLowerCase();
                const p = window.perfilDadosGlobais;
                
                if (!p) {
                    window.mostrarDialogoRPG("Sistema", "Aguarde, lendo pergaminhos...");
                    return;
                }
                if (!p.quests) p.quests = {};
                
                // ===============================================
                // 🛡️ CAPITÃO VAREK: O Guia Inicial (Níveis 1 a 4)
                // ===============================================
                if (npcId.includes('varek')) {
                    if (p.quests["q0_boas_vindas"] && p.quests["q0_boas_vindas"].status !== 'resgatada') {
                        p.quests["q0_boas_vindas"].status = 'resgatada';
                        fetch('/api/quest/completar', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ user_id: localStorage.getItem("jogadorEldoraID"), quest_id: "q0_boas_vindas" })
                        }).catch(()=>{});
                    }

                    const q1 = p.quests["q1_varek_recruta"];
                    const q2 = p.quests["q2_varek_defesas"];
                    const q3 = p.quests["q3_varek_provacao"];

                    if (!q1 || q1.status !== 'resgatada') {
                        window.interagirComNPC(
                            "q1_varek_recruta", "Capitão Varek", 
                            "Pelo Decreto do Despertar do Rei, todo cidadão com potencial deve lutar. Os antigos selos estão fracos. Prove que não vai morrer no primeiro dia: limpe as Gosmas nos arredores e alcance o Nível 2.", 
                            "Você ainda está muito fraco, recruta. Volte apenas quando atingir o Nível 2.", 
                            "Bom trabalho. Você sobreviveu ao primeiro dia. Tome 100 de Ouro. Mas as invasões estão piorando...", 
                            2, null
                        );
                    } 
                    else if (!q2 || q2.status !== 'resgatada') {
                        window.interagirComNPC(
                            "q2_varek_defesas", "Capitão Varek",
                            "O exército real está focado em proteger os nobres no castelo... sobra para nós protegermos os plebeus. Alcance o Nível 4 repelindo as feras nas nossas fronteiras.",
                            "As feras ainda ameaçam as casas dos plebeus. Volte quando atingir o Nível 4.",
                            "As barricadas estão seguras por agora. Você lutou bem, recruta. Mas o verdadeiro teste se aproxima.",
                            4, null
                        );
                    } 
                    else if (!q3 || q3.status !== 'resgatada') {
                        window.interagirComNPC(
                            "q3_varek_provacao", "Capitão Varek",
                            "Alerta! Uma caravana foi emboscada perto da floresta! Sobreviva a esta provação infernal, salve a caravana e alcance o Nível 5.",
                            "Essa missão é suicídio para o seu nível atual. Vá treinar e volte no Nível 5!",
                            "Pelos deuses de Eldora... você despertou a Centelha de Batalha! O exército real precisa de você. Leve minha carta de recomendação para a Arquimaga Selene, no pátio do castelo.",
                            5, null
                        );
                    } 
                    else {
                        window.mostrarDialogoRPG("Capitão Varek", "Eu já lhe ensinei tudo o que podia para sobreviver. A Arquimaga Selene o aguarda no Castelo Majestoso.");
                    }
                } 
                // ===============================================
                // 🔮 ARQUIMAGA SELENE: Mestra das Artes Arcanas
                // ===============================================
                else if (npcId.includes('selene')) {
                    if (!p.quests["q3_varek_provacao"] || p.quests["q3_varek_provacao"].status !== 'resgatada') {
                        window.mostrarDialogoRPG("Arquimaga Selene", "Sinto potencial em ti, mas o Capitão Varek ainda não atestou o teu valor. Retorne aos arredores da cidade.");
                        return;
                    }

                    let classeAtual =
                        p.class_key ||
                        p.class ||
                        p.classe ||
                        "aventureiro";

                    let jaTemClasse = (classeAtual.toLowerCase() !== 'aventureiro' && classeAtual.toLowerCase() !== 'aprendiz');
                    
                    if (!jaTemClasse || !p.quests["q4_selene_classe"] || p.quests["q4_selene_classe"].status !== 'resgatada') {
                        let acaoDaSelene = jaTemClasse ? null : "abrir_menu_classes";
                        window.interagirComNPC(
                            "q4_selene_classe", "Arquimaga Selene", 
                            "Sua alma arde... Escolha seu caminho. O poder o aguarda, mas escolha com sabedoria, pois sua alma será moldada por este caminho.", 
                            "A aura ainda oscila... Volte no Nível 5.", 
                            "Sua alma está pronta. Agora, vá e aprenda um ofício com o Mestre Thorek antes de prosseguirmos.", 
                            5, acaoDaSelene
                        );
                        return;
                    }

                    let fezThorek = p.quests["q5_thorek_profissao"] && p.quests["q5_thorek_profissao"].status === 'resgatada';
                    if (!fezThorek) {
                        window.mostrarDialogoRPG("Arquimaga Selene", "Mãos macias não conseguem segurar o conhecimento arcano. Vá falar com Thorek na capital e consiga um ofício primeiro.");
                        return;
                    }

                    if (!p.quests["q6_selene_grimorio"] || p.quests["q6_selene_grimorio"].status !== 'resgatada') {
                        window.interagirComNPC(
                            "q6_selene_grimorio", "Arquimaga Selene", 
                            "A centelha brilha em ti! É o momento de romper os selos do seu Grimório. Mas o conhecimento exige tributo: traga-me 15 Ectoplasmas e 30 Couros de Lobo Alfa. Além disso, seu corpo precisa da têmpera do Nível 17.", 
                            "A tua aura vacila... Volta quando fores Nível 17 e tiveres os 15 Ectoplasmas e 30 Couros de Lobo Alfa!", 
                            "Sente o poder! Os antigos selos foram estraçalhados. A tua primeira habilidade de classe foi gravada na tua alma. Use-a com sabedoria!", 
                            17, "abrir_menu_magias"
                        );
                        return;
                    }

                    // =====================================================
                    // 🏰 Q7 — O RECONHECIMENTO DA CAPITAL
                    // =====================================================

                    const q7Guilda =
                        p.quests["q7_selene_guildas"];

                    if (
                        !q7Guilda ||
                        q7Guilda.status !== 'resgatada'
                    ) {

                        // Ainda não atingiu o nível necessário.
                        if (p.level < 20) {

                            window.mostrarDialogoRPG(
                                "Arquimaga Selene",
                                "O Grimório respondeu ao seu chamado, mas poder recém-desperto é instável. Treine, fortaleça seu corpo e retorne quando alcançar o Nível 20. Então decidirei se está pronto para carregar o nome de Eldora diante da Guilda dos Aventureiros."
                            );

                            return;
                        }

                        // =================================================
                        // 📜 ABRE A MISSÃO OFICIAL Q7
                        // =================================================

                        if (
                            window.motorMissoesNPC &&
                            typeof window.motorMissoesNPC.interagir === 'function'
                        ) {

                            const rostoSelene =
                                "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/npcs/npc_selene_rosto.png";

                            window.motorMissoesNPC.interagir(
                                "selene_arquimaga",
                                "Arquimaga Selene",
                                rostoSelene
                            );

                            return;
                        }

                        // Fallback caso a interface de missão não esteja carregada.
                        window.mostrarDialogoRPG(
                            "Arquimaga Selene",
                            "Seu treinamento chegou ao momento decisivo. Há uma prova que deve cumprir antes que eu possa recomendá-lo à Guilda dos Aventureiros."
                        );

                        return;
                    }

                    // =====================================================
                    // ✅ Q7 JÁ CONCLUÍDA
                    // =====================================================

                    window.mostrarDialogoRPG(
                        "Arquimaga Selene",
                        "Você conquistou meu reconhecimento. A Carta de Recomendação leva meu selo e confirma seu valor perante a Capital. Apresente-se agora à Guilda dos Aventureiros. A partir daqui, sua jornada deixa de ser apenas sobrevivência."
                    );
                }
                // ===============================================
                // 🧠 LÓGICA INTELIGENTE DOS MESTRES DE GUILDA
                // ===============================================
                const interagirMestre = (idMestre, nomeMestre, falaAprender, falaSeuMestre, falaOutraGuilda) => {
                    const p = window.perfilDadosGlobais || {};
                    const profAtual = p.profession || null;
                    const inventario = p.inventario || p.inventory || [];

                    // 👇 ADICIONE ESTA LINHA AQUI!
                    let qtdSelo = 0;

                    if (Array.isArray(inventario)) {
                        // Se for uma Lista (Array), usamos o .find()
                        const itemSelo = inventario.find(i => i.base_id === 'selo_de_maestria' || i.id === 'selo_de_maestria');
                        if (itemSelo) qtdSelo = itemSelo.quantity || itemSelo.qtd || itemSelo.quantidade || 0;
                    } else {
                        // Se for um Objeto Dicionário, usamos a busca direta
                        const itemSelo = inventario['selo_de_maestria'];
                        if (itemSelo) qtdSelo = typeof itemSelo === 'object' ? (itemSelo.quantity || itemSelo.qtd || itemSelo.quantidade || 0) : itemSelo;
                    }
                    
                    const profsDoNpc = {
                        'sylas': ['lenhador'], 'borin': ['minerador'], 'grom': ['esfolador', 'curtidor'],
                        'elara': ['colhedor', 'alfaiate'], 'paracelso': ['alquimista', 'joalheiro'], 'thorek': ['ferreiro', 'armeiro']
                    };

                    if (!profAtual || !profAtual.key) {
                        // 1. Novato sem profissão
                        window.mostrarDialogoRPG(nomeMestre, falaAprender, () => { if (typeof window.abrirModalProfissoes === 'function') window.abrirModalProfissoes(idMestre); });
                    } else if (qtdSelo < 1) {
                        // 2. Tem profissão, mas não tem o Selo da Maestria
                        if (profsDoNpc[idMestre] && profsDoNpc[idMestre].includes(profAtual.key)) {
                            
                            // 🔥 AQUI ENTRA A FORMATURA: É o seu mestre e você atingiu Nível 50?
                            if (profAtual.level >= 50) {
                                window.mostrarDialogoRPG(nomeMestre, 
                                    `Pelos Deuses Antigos! Você atingiu o ápice das minhas artes. Como seu mentor, eu o declaro um verdadeiro Mestre-Artesão de Eldora. Tome este Selo de Maestria como prova do seu valor!`, 
                                    () => { window.tentarResgatarSelo(idMestre, nomeMestre); }
                                );
                            } else {
                                // Ainda não é mestre (Nível < 50), apenas fala o diálogo normal
                                window.mostrarDialogoRPG(nomeMestre, falaSeuMestre); 
                            }
                            
                        } else {
                            // É um Mestre de outra Guilda (Apenas fala, NÃO ABRE O MENU!)
                            window.mostrarDialogoRPG(nomeMestre, falaOutraGuilda); 
                        }
                    } else {
                        // 3. Tem o Selo! Pode aprender mais uma profissão
                        window.mostrarDialogoRPG(nomeMestre, "Vejo o Selo da Maestria no seu peito... Deseja assinar o Tratado e aprender os segredos da minha guilda também?", () => {
                            if (typeof window.abrirModalProfissoes === 'function') window.abrirModalProfissoes(idMestre);
                        });
                    }
                };

                // ===============================================
                // 🔨 MESTRE THOREK (Capital)
                // ===============================================
                if (npcId.includes('thorek')) {
                    if (!p.quests["q4_selene_classe"] || p.quests["q4_selene_classe"].status !== 'resgatada') {
                        window.mostrarDialogoRPG("Mestre-Artesão Thorek", "Humpf! Não perco meu tempo com novatos sem classe definida. Vá falar com a Arquimaga Selene primeiro.");
                        return;
                    }
                    if (!p.quests["q5_thorek_profissao"] || p.quests["q5_thorek_profissao"].status !== 'resgatada') {
                        window.interagirComNPC(
                            "q5_thorek_profissao", "Mestre-Artesão Thorek", 
                            "Magia e fúria não bastam se sua armadura for de papel. Fale comigo e eu te darei uma Licença de Guilda.",
                            "Ainda não tem calos nas mãos suficientes. Volte no Nível 7.",
                            "Finalmente. Aqui está sua Licença de Guilda. Eu ensino Ferreiro e Armeiro. Se quiser dominar a natureza, procure os outros mestres nos mapas!",
                            7, "abrir_menu_profissoes"
                        );
                    } else {
                        interagirMestre('thorek', "Mestre-Artesão Thorek", 
                            "A forja aguarda. Quer aprender a moldar o metal?",
                            "Você já é da forja! A sua bancada de trabalho estará pronta em breve.",
                            "Você já serve a outra guilda. Concentre-se no seu ofício e volte quando tiver o Selo da Maestria."
                        );
                    }
                }
                // ===============================================
                // 🪓 SYLAS: Guarda-Bosque (Pradaria/Floresta)
                // ===============================================
                else if (npcId.includes('sylas')) {
                    if (!p.quests["q5_thorek_profissao"] || p.quests["q5_thorek_profissao"].status !== 'resgatada') window.mostrarDialogoRPG("Sylas, o Guarda-Bosque", "A floresta não tolera amadores. Consiga sua licença com o Thorek na Capital primeiro.");
                    else interagirMestre('sylas', "Sylas, o Guarda-Bosque", "Quer aprender a extrair a madeira sem irritar os Ents?", "Vá cortar lenha! Sua bancada de carpintaria logo estará disponível.", "Você tem cheiro de outra guilda. Siga seu caminho.");
                }
                // ===============================================
                // ⛏️ BÓRIN: O Quebra-Pedras (Minas)
                // ===============================================
                else if (npcId.includes('borin')) {
                    if (!p.quests["q5_thorek_profissao"] || p.quests["q5_thorek_profissao"].status !== 'resgatada') window.mostrarDialogoRPG("Bórin Quebra-Pedras", "Bah! Suas mãos são macias demais. Fale com o Thorek.");
                    else interagirMestre('borin', "Bórin Quebra-Pedras", "Pedra e minério... Veio aprender a quebrar rochas?", "As pedras não vão se quebrar sozinhas! A fundição logo chegará.", "A mina é só para quem tem vocação. Vá evoluir o ofício que escolheu.");
                }
                // ===============================================
                // 🐺 GROM: O Caçador (Pradaria)
                // ===============================================
                else if (npcId.includes('grom')) {
                    if (!p.quests["q5_thorek_profissao"] || p.quests["q5_thorek_profissao"].status !== 'resgatada') window.mostrarDialogoRPG("Grom, o Caçador", "Você tem cheiro de presa. Licença do Thorek, agora.");
                    else interagirMestre('grom', "Grom, o Caçador", "Sangue e couro... Veio aprender o ofício da sobrevivência?", "A pele não vai se curtir sozinha. Em breve teremos bancadas de couro.", "Caçadores trabalham sozinhos. Você já escolheu sua matilha.");
                }
                // ===============================================
                // 🧶 MADAME ELARA: Tecelã (Pradaria)
                // ===============================================
                else if (npcId.includes('elara')) {
                    if (!p.quests["q5_thorek_profissao"] || p.quests["q5_thorek_profissao"].status !== 'resgatada') window.mostrarDialogoRPG("Madame Elara", "Querido, a lei da guilda é clara. Fale com o Thorek antes.");
                    else interagirMestre('elara', "Madame Elara", "Um bom fio pode estrangular um orc ou aquecer um rei. Vamos costurar?", "As agulhas estão afiadas! Em breve faremos mantos mágicos.", "Suas mãos são desajeitadas para a agulha. Foque no que você já sabe fazer.");
                }
                // ===============================================
                // 🧪 PARACELSO: Alquimista (Capital)
                // ===============================================
                else if (npcId.includes('paracelso')) {
                    if (!p.quests["q5_thorek_profissao"] || p.quests["q5_thorek_profissao"].status !== 'resgatada') window.mostrarDialogoRPG("Alquimista Paracelso", "Saia do meu laboratório! Só atendo licenciados pelo Thorek.");
                    else interagirMestre('paracelso', "Alquimista Paracelso", "A condensação de ectoplasma requer precisão... quer aprender?", "Os caldeirões estão fervendo! Logo faremos poções poderosas.", "Você não tem a mente de um cientista. Vá trabalhar na sua guilda.");
                }
            });

            npc.label = this.scene.add.text(posX, posY - 30, nome, {
                fontSize: '10px', 
                color: '#2ecc71',
                fontFamily: 'Cinzel, Arial', 
                stroke: '#000000', 
                strokeThickness: 3
            }).setOrigin(0.5).setDepth(30);

            this.npcs[id] = npc;

            if (typeof this.scene.gerarAnimacoes === 'function') {
                try { this.scene.gerarAnimacoes(skinFinal); } catch(e) {}
            }

            const dist = Phaser.Math.Distance.Between(posX, posY, destinoX, destinoY);
            if (dist > 5) {
                const duracao = (dist / 80) * 1000;
                let animDir = (Math.abs(destinoX - posX) > Math.abs(destinoY - posY)) ? 
                           (destinoX > posX ? 'right' : 'left') : (destinoY > posY ? 'down' : 'up');
                const nomeAnim = animDir + '_' + skinFinal;
                
                if (this.scene.anims.exists(nomeAnim)) {
                    npc.anims.play(nomeAnim, true);
                }

                this.scene.tweens.add({
                    targets: [npc, npc.label],
                    x: destinoX,
                    y: (target) => target === npc.label ? destinoY - 30 : destinoY,
                    duration: duracao,
                    onComplete: () => {
                        try {
                            if(npc && npc.anims) npc.anims.stop();
                            if(npc) npc.setFrame(1);
                        } catch(e){}
                    }
                });
            } else {
                npc.setFrame(1);
            }
        } catch (e) {
            console.error("Erro na criação do NPC:", e);
        }
    }
}

// ==========================================
// LÓGICA DE MISSÕES COM O NOVO DIÁLOGO
// ==========================================
window.interagirComNPC = async function(idMissao, nomeNPC, falaInicial, falaIncompleta, falaConcluida, reqLevel, acaoEspecial) {
    try {
        const charId = localStorage.getItem("jogadorEldoraID");
        const p = window.perfilDadosGlobais; 
        
        if (!p) {
            window.mostrarDialogoRPG("Sistema", "Aguarde, lendo pergaminhos...");
            return;
        }

        if (!p.quests) p.quests = {};
        const questAtual = p.quests[idMissao];

        const executarAcaoEspecial = () => {
            if (acaoEspecial === 'abrir_menu_classes') {
                if (typeof window.abrirModalClasses === 'function') {
                    window.abrirModalClasses();
                }
            } 
            // 🔨 CORREÇÃO DO THOREK (Profissões)
            else if (acaoEspecial === 'abrir_menu_profissoes') {
                // Tenta chamar a função do modal de profissão, ou abre a aba direto
                if (typeof window.abrirModalProfissoes === 'function') {
                    window.abrirModalProfissoes();
                } else if (typeof window.abrirAba === 'function') {
                    window.abrirAba('profissoes'); // Substitua 'profissoes' pelo ID da sua aba se for diferente
                } else {
                    window.avisoEldora("Acesso Liberado! O menu de Profissões do Thorek precisa ser criado/conectado.");
                }
            } 
           // 🔮 CORREÇÃO DA SELENE (Grimório do Nível 17)
            else if (acaoEspecial === 'abrir_menu_magias') {
                if (typeof window.alertaEldora === 'function') {
                    window.alertaEldora("Grimório Desperto!", "Acesse a sua Mochila e clique na aba de Magias para equipar seu novo poder.", "sucesso");
                } else {
                    window.mostrarDialogoRPG("Sistema", "Magia liberada! Abra seu Perfil e acesse a aba Magias para equipar.");
                }
            }
        };

        if (!questAtual) {
            window.mostrarDialogoRPG(nomeNPC, falaInicial);
            p.quests[idMissao] = { 
                titulo: `Missão: ${nomeNPC}`, 
                objetivo: `Alcance o Nível ${reqLevel} e fale com ${nomeNPC}.`, 
                status: "em_andamento" 
            };

            fetch('/api/quest/iniciar', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user_id: charId, quest_id: idMissao, quest_data: p.quests[idMissao] })
            }).catch(()=>{});
            return;
        }

        if (questAtual.status === 'em_andamento') {
            if (p.level >= reqLevel) {
                try {
                    let resposta, dados;

                    // 👇 INTERCEPTA A MISSÃO 6 PARA COBRAR OS ITENS 👇
                    if (idMissao === "q6_selene_grimorio") {
                        resposta = await fetch('/api/npc/missao/grimorio', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ user_id: charId })
                        });
                        dados = await resposta.json();
                    } else {
                        // Rota normal para missões que só pedem nível
                        resposta = await fetch('/api/quest/completar', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ user_id: charId, quest_id: idMissao })
                        });
                        dados = await resposta.json();
                    }

                    if (dados.sucesso) {
                        window.mostrarDialogoRPG(nomeNPC, falaConcluida, executarAcaoEspecial);
                        p.quests[idMissao].status = 'resgatada';
                        
                        // Opcional: Um alerta bonitão na tela avisando que a skill chegou!
                        if (idMissao === "q6_selene_grimorio" && typeof window.alertaEldora === 'function') {
                            window.alertaEldora("Grimório Desperto", "Você aprendeu sua primeira habilidade de classe!", "sucesso");
                        }

                        if (typeof carregarMeuPerfil === 'function') carregarMeuPerfil(); 
                    } else {
                        // O servidor vai devolver exatamente o que faltou (ex: faltam 2 ectoplasmas)
                        window.mostrarDialogoRPG("Selene Irritada", dados.erro);
                    }
                } catch (e) {
                    console.error("Erro ao completar missão:", e);
                }
            } else {
                window.mostrarDialogoRPG(nomeNPC, falaIncompleta);
            }
            return;
        }

        if (questAtual.status === 'resgatada') {
            // 🔍 BUSCA PELA PRÓXIMA MISSÃO NA LORE
            const todasQuests = [
                {id: "q4_selene_classe", lvl: 5, nome: "Despertar"},
                {id: "q5_thorek_profissao", lvl: 7, nome: "Profissão"},
                {id: "q6_selene_grimorio", lvl: 17, nome: "Grimório"},
                {id: "q7_selene_guildas", lvl: 20, nome: "Reconhecimento"}
            ];

            // Encontra qual seria a próxima missão deste NPC específico
            const proxima = todasQuests.find(q => {
                const dadosQ = p.quests[q.id];
                return (!dadosQ || dadosQ.status !== 'resgatada');
            });

            if (proxima && p.level < proxima.lvl) {
                window.mostrarDialogoRPG(nomeNPC, `Você concluiu sua tarefa anterior, mas sua alma ainda não é forte o suficiente para o próximo passo. Retorne quando alcançar o Nível ${proxima.lvl}.`);
            } else {
                window.mostrarDialogoRPG(nomeNPC, "Você já cumpriu seu dever aqui por enquanto. Siga sua jornada, herói.");
            }
            
            if (executarAcaoEspecial) executarAcaoEspecial();
            return;
        }

    } catch (err) {}
};

// ==========================================
// SISTEMA DE ESCOLHA DE CLASSES (ARQUIMAGA SELENE)
// ==========================================

window.abrirModalClasses = function() {
    // Se já existe, apenas mostra e garante que volta para a tela inicial de grade
    if (document.getElementById('modal-escolha-classe')) {
        document.getElementById('modal-escolha-classe').style.display = 'flex';
        if (typeof window.voltarGradeClasses === 'function') window.voltarGradeClasses();
        return;
    }

    const estiloRPG = `
        <style>
            #modal-escolha-classe * { box-sizing: border-box; }
            .classe-btn {
                background: linear-gradient(180deg, rgba(30,41,59,0.9) 0%, rgba(15,23,42,0.9) 100%);
                border: 2px solid #475569; border-radius: 10px; padding: 12px 5px; cursor: pointer;
                display: flex; flex-direction: column; align-items: center; justify-content: center;
                transition: all 0.2s; color: #cbd5e1; box-shadow: 0 4px 6px rgba(0,0,0,0.4);
            }
            .classe-btn:hover {
                transform: translateY(-3px) scale(1.02); border-color: var(--cor-classe, #facc15);
                box-shadow: 0 0 15px var(--cor-classe, #facc15); color: #fff;
            }
            .classe-nome { 
                font-size: 0.8em; font-weight: 900; font-family: 'Cinzel', serif; 
                letter-spacing: 0.5px; text-transform: uppercase; margin-top: 8px; text-align: center;
            }
            .btn-voltar {
                background: transparent; border: 1px solid #64748b; border-radius: 6px;
                color: #94a3b8; font-family: 'Segoe UI', Arial; font-size: 0.8em; font-weight: bold;
                padding: 4px 10px; cursor: pointer; transition: 0.2s;
                position: absolute; top: 0; left: 0; z-index: 10;
            }
            .btn-voltar:hover { background: #334155; color: #fff; border-color: #cbd5e1; }
            .btn-confirmar {
                background: linear-gradient(to bottom, #ca8a04, #a16207); border: 2px solid #fef08a; border-radius: 8px;
                color: #fff; font-family: 'Cinzel', serif; font-size: 1.2em; font-weight: bold; padding: 12px 20px;
                cursor: pointer; text-shadow: 1px 1px 2px #000; box-shadow: 0 4px 6px rgba(0,0,0,0.5);
                transition: transform 0.1s, filter 0.2s; margin-top: 20px; width: 100%;
            }
            .btn-confirmar:hover { filter: brightness(1.2); transform: scale(1.02); }
            .btn-confirmar:active { transform: scale(0.95); }
            
            #grid-classes::-webkit-scrollbar { width: 6px; }
            #grid-classes::-webkit-scrollbar-track { background: rgba(0,0,0,0.3); border-radius: 4px; }
            #grid-classes::-webkit-scrollbar-thumb { background: #ca8a04; border-radius: 4px; }
            
            .fade-in { animation: fadeInUI 0.3s forwards; }
            @keyframes fadeInUI { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        </style>
    `;

    const classes = [
        { id: 'guerreiro', nome: 'Guerreiro', cor: '#ef4444', desc: 'Mestres do combate corpo-a-corpo. Possuem alta vitalidade e defesa impenetrável.' },
        { id: 'mago', nome: 'Mago', cor: '#3b82f6', desc: 'Canalizam os elementos para causar dano massivo em área, exigindo distância segura.' },
        { id: 'assassino', nome: 'Assassino', cor: '#8b5cf6', desc: 'Furtivos e letais. Especialistas em dano crítico rápido e evasão das sombras.' },
        { id: 'cacador', nome: 'Caçador', cor: '#22c55e', desc: 'Atacam à distância com precisão letal. Sobreviventes natos das florestas.' },
        { id: 'curandeiro', nome: 'Curandeiro', cor: '#facc15', desc: 'A luz do reino. Mantêm aliados vivos e curam ferimentos profundos no calor da batalha.' },
        { id: 'berserker', nome: 'Berserker', cor: '#dc2626', desc: 'Movidos pela fúria crua. Trocam sua defesa por um poder de ataque devastador.' },
        { id: 'samurai', nome: 'Samurai', cor: '#64748b', desc: 'Disciplinados e imponentes. Desferem cortes precisos com velocidade inigualável.' },
        { id: 'monge', nome: 'Monge', cor: '#f97316', desc: 'Lutadores espirituais que combinam artes marciais fluídas com energia vital interior.' },
        { id: 'bardo', nome: 'Bardo', cor: '#ec4899', desc: 'Inspiram aliados com melodias mágicas, concedendo vantagens e fortalecendo o grupo.' }
    ];

    window.dadosClassesEldora = classes;
    window.classeSelecionadaEldora = null;

    let generoSalvo = localStorage.getItem("generoEscolhido") || "masculino";
    let sufixo = (generoSalvo === "feminino") ? "_f" : "_m";
    const LINK_GITHUB_ROSTOS = "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/avatares/class_selec/";

    let botoesHtml = classes.map(c => {
        let urlIconeRosto = `${LINK_GITHUB_ROSTOS}${c.id}${sufixo}.png`;
        return `
        <button class="classe-btn" style="--cor-classe: ${c.cor};" onclick="window.selecionarClasseNaUI('${c.id}')">
            <img src="${urlIconeRosto}" alt="${c.nome}" 
                 style="width: 60px; height: 60px; object-fit: contain; object-position: center; display: block; filter: drop-shadow(0 3px 3px rgba(0,0,0,0.8));" 
                 onerror="this.src='https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/avatares/avatar_padrao_m.png'">
            <span class="classe-nome" style="color: ${c.cor}">${c.nome}</span>
        </button>
        `;
    }).join('');

    const htmlModal = `
        ${estiloRPG}
        <div id="modal-escolha-classe" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 100005; display: flex; justify-content: center; align-items: center; backdrop-filter: blur(5px);">
            <div style="background: linear-gradient(145deg, #0f172a, #1e293b); border: 2px solid #ca8a04; border-radius: 12px; padding: 25px; width: 95%; max-width: 500px; display: flex; flex-direction: column; box-shadow: 0 10px 30px rgba(0,0,0,0.9); position: relative;">
                
                <!-- ============================== -->
                <!-- TELA 1: A GRADE DE ROSTOS -->
                <!-- ============================== -->
                <div id="tela-grade-classes" class="fade-in" style="display: flex; flex-direction: column; width: 100%;">
                    <h2 style="color: #facc15; font-family: 'Cinzel', serif; margin: 0 0 5px 0; text-align: center; font-size: 1.8em; text-shadow: 1px 1px 2px #000;">O Despertar da Alma</h2>
                    <p style="color: #cbd5e1; font-size: 0.9em; text-align: center; margin-bottom: 20px;">Qual caminho guiará seu destino?</p>
                    
                    <div id="grid-classes" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; max-height: 50vh; overflow-y: auto; padding: 5px;">
                        ${botoesHtml}
                    </div>
                    
                    <button onclick="document.getElementById('modal-escolha-classe').style.display='none'" style="margin-top: 20px; align-self: center; padding: 8px 25px; background: transparent; border: 1px solid #ef4444; color: #ef4444; border-radius: 6px; cursor: pointer; font-weight: bold; font-family: 'Cinzel', serif;">Pensar Mais</button>
                </div>

                <!-- ============================== -->
                <!-- TELA 2: OS DETALHES DA CLASSE -->
                <!-- ============================== -->
                <div id="tela-detalhes-classe" style="display: none; flex-direction: column; width: 100%; position: relative;">
                    <!-- Botão Pequeno de Voltar -->
                    <button class="btn-voltar" onclick="window.voltarGradeClasses()">⬅ Voltar</button>
                    
                    <!-- Espaço que será preenchido pelo JS -->
                    <div id="conteudo-detalhes" style="display: flex; flex-direction: column; align-items: center; text-align: center; margin-top: 25px;">
                    </div>
                    
                    <button id="btn-confirmar-classe" class="btn-confirmar" onclick="window.dispararConfirmacao()">Abraçar Destino</button>
                </div>

            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', htmlModal);
};

// 4. Lógica de UI: Mostra a descrição ao clicar, mas não confirma a compra ainda
window.selecionarClasseNaUI = function(classeId) {
    const classe = window.dadosClassesEldora.find(c => c.id === classeId);
    if (!classe) return;
    window.classeSelecionadaEldora = classe;

    let generoSalvo = localStorage.getItem("generoEscolhido") || "masculino";
    let sufixo = (generoSalvo === "feminino") ? "_f" : "_m";

    // 👉 O CAMINHO EXATO: Com "refs/heads/main" e o "_full.png" no final da string!
    const LINK_GITHUB_CORPO = "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/corpo_completo/";
    const urlImagemPersonagem = `${LINK_GITHUB_CORPO}${classe.id}${sufixo}_full.png`;

    // Troca as telas
    document.getElementById('tela-grade-classes').style.display = 'none';
    const telaDetalhes = document.getElementById('tela-detalhes-classe');
    telaDetalhes.style.display = 'flex';
    telaDetalhes.classList.remove('fade-in');
    void telaDetalhes.offsetWidth; // Força reinício da animação
    telaDetalhes.classList.add('fade-in');

    const conteudo = document.getElementById('conteudo-detalhes');
    
    conteudo.innerHTML = `
        <div style="height: 250px; display: flex; justify-content: center; align-items: flex-end; margin-bottom: 15px; width: 100%;">
            <img src="${urlImagemPersonagem}" 
                 alt="${classe.nome}" 
                 onerror="this.src='https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/avatares/avatar_padrao_m.png'" 
                 style="max-height: 100%; max-width: 100%; object-fit: contain; object-position: bottom; filter: drop-shadow(0 10px 20px ${classe.cor}); animation: floatImgGigante 3s ease-in-out infinite;">
        </div>

        <h3 style="color: ${classe.cor}; margin: 0 0 10px 0; font-family: 'Cinzel', serif; font-size: 1.8em; text-transform: uppercase; text-shadow: 1px 1px 2px #000; letter-spacing: 1px;">${classe.nome}</h3>
        
        <div style="background: rgba(0,0,0,0.4); border: 1px inset #334155; border-radius: 8px; padding: 15px; width: 100%;">
            <p style="color: #cbd5e1; font-size: 0.95em; line-height: 1.5; margin: 0; font-family: 'Segoe UI', Arial;">${classe.desc}</p>
        </div>
        
        <style>
            @keyframes floatImgGigante { 
                0% { transform: translateY(0px); } 
                50% { transform: translateY(-10px); } 
                100% { transform: translateY(0px); } 
            }
        </style>
    `;
};

// Não esqueça de manter a função de disparo abaixo delas:
window.dispararConfirmacao = function() {
    const classe = window.classeSelecionadaEldora;
    if (!classe) return;

    // Cria um modal de confirmação estilo RPG (sem usar o alert do navegador!)
    let modalConfirm = document.getElementById('modal-confirm-rpg');
    if (!modalConfirm) {
        modalConfirm = document.createElement('div');
        modalConfirm.id = 'modal-confirm-rpg';
        modalConfirm.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); z-index: 100010; display: flex; justify-content: center; align-items: center; backdrop-filter: blur(4px);';
        document.body.appendChild(modalConfirm);
    }

    modalConfirm.innerHTML = `
        <div style="background: linear-gradient(145deg, #0f172a, #1e293b); border: 2px solid #ca8a04; border-radius: 12px; padding: 30px; text-align: center; max-width: 400px; box-shadow: 0 0 30px rgba(202, 138, 4, 0.4);">
            <h3 style="color: #ef4444; font-family: 'Cinzel', serif; font-size: 1.5em; margin-top: 0; text-shadow: 2px 2px 4px #000;">Caminho Sem Volta</h3>
            <p style="color: #cbd5e1; font-size: 1.1em; margin-bottom: 25px; line-height: 1.5;">Tem certeza que deseja abraçar o caminho do <strong style="color: ${classe.cor}; text-transform: uppercase;">${classe.nome}</strong>?<br><br>Esta escolha moldará seus atributos para sempre!</p>
            <div style="display: flex; gap: 15px; justify-content: center;">
                <button onclick="document.getElementById('modal-confirm-rpg').style.display='none'" style="padding: 10px 20px; background: #334155; border: 1px solid #64748b; color: #f8fafc; border-radius: 6px; cursor: pointer; font-weight: bold; flex: 1; font-family: 'Cinzel', serif;">Repensar</button>
                <button onclick="window.executarEscolhaClasse('${classe.id}', '${classe.nome}')" style="padding: 10px 20px; background: linear-gradient(180deg, #10b981, #059669); border: 1px solid #047857; color: white; border-radius: 6px; cursor: pointer; font-weight: bold; flex: 1; box-shadow: 0 4px 6px rgba(0,0,0,0.5); font-family: 'Cinzel', serif;">Aceitar Destino</button>
            </div>
        </div>
    `;
    modalConfirm.style.display = 'flex';
};

window.executarEscolhaClasse = async function(classeId, nomeDaClasse) {

    document.getElementById('modal-confirm-rpg').style.display = 'none';

    const charId =
        localStorage.getItem("jogadorEldoraID");

    const meuNome =
        localStorage.getItem("jogadorEldoraNome")
        || "Um herói";

    try {

        // =====================================================
        // ⚔️ ROTA OFICIAL DE ESCOLHA DE CLASSE
        //
        // Esta rota:
        // - troca a classe
        // - equipa a skin
        // - equipa o avatar
        // - desbloqueia skin/avatar
        // - enche HP/MP
        // - conclui q4_selene_classe
        // =====================================================

        const res = await fetch(
            '/api/player/escolher_classe',
            {
                method: 'POST',

                headers: {
                    'Content-Type': 'application/json'
                },

                body: JSON.stringify({
                    user_id: charId,
                    nova_classe: classeId
                })
            }
        );

        const dados = await res.json();


        // IMPORTANTE:
        // essa rota retorna "sucesso"
        if (dados.sucesso) {

            // =================================================
            // 🎭 ATUALIZA A SKIN LOCAL
            //
            // mapa.js dá prioridade para:
            // localStorage.getItem("skinEquipada")
            //
            // então precisamos substituir a skin antiga ANTES
            // do reload.
            // =================================================

            let generoSalvo =
                localStorage.getItem("generoEscolhido")
                || "masculino";

            let generoCurto =
                generoSalvo === "feminino"
                    ? "f"
                    : "m";

            const novaSkinId =
                `${classeId}_${generoCurto}`;

            localStorage.setItem(
                "skinEquipada",
                novaSkinId
            );

            window.minhaSkinAtual =
                novaSkinId;


            // =================================================
            // 🔄 ATUALIZA MEMÓRIA DO PERFIL
            // =================================================

            if (window.perfilDadosGlobais) {

                window.perfilDadosGlobais.class =
                    classeId;

                window.perfilDadosGlobais.class_key =
                    classeId;

                window.perfilDadosGlobais.equipped_skin =
                    novaSkinId;

                window.perfilDadosGlobais.avatar_customizado =
                    novaSkinId;
            }


            document.getElementById(
                'modal-escolha-classe'
            ).style.display = 'none';


            // =================================================
            // 🌍 EVENTO GLOBAL
            // =================================================

            if (window.eldoraSocket) {

                window.eldoraSocket.emit(
                    'dispararEventoGlobal',
                    {
                        efeito: 'despertar_classe',
                        jogador_id: charId,
                        jogador_nome: meuNome,
                        classe: nomeDaClasse
                    }
                );

                window.eldoraSocket.emit(
                    'enviarMensagemChat',
                    {
                        texto:
                            `O céu sobre a capital escureceu... ` +
                            `${meuNome} despertou como um poderoso ` +
                            `${nomeDaClasse}!`
                    }
                );
            }


            // =================================================
            // ✨ ANIMAÇÃO E RELOAD
            // =================================================

            if (
                typeof window.animarDespertarClasse
                === 'function'
            ) {

                window.animarDespertarClasse(
                    nomeDaClasse,
                    () => {
                        window.location.reload();
                    }
                );

            } else {

                window.location.reload();
            }

        } else {

            window.avisoEldora(
                "A Arquimaga Selene encontrou uma distorção: "
                + (dados.erro || "Erro desconhecido.")
            );
        }

    } catch (e) {

        console.error(
            "Erro ao escolher classe:",
            e
        );

        window.avisoEldora(
            "Erro de conexão ao canalizar a magia."
        );
    }
};

window.voltarGradeClasses = function() {
    // Esconde a Tela de Detalhes
    document.getElementById('tela-detalhes-classe').style.display = 'none';
    
    // Mostra a Tela de Grade novamente com animação
    const telaGrade = document.getElementById('tela-grade-classes');
    telaGrade.style.display = 'flex';
    telaGrade.classList.remove('fade-in');
    void telaGrade.offsetWidth; // Força reinício da animação
    telaGrade.classList.add('fade-in');
};

// ==========================================
// 🔔 SISTEMA DE NOTIFICAÇÕES GLOBAIS
// ==========================================
window.ativarNotificacaoPergaminho = function() {
    const badge = document.getElementById('quest-badge');
    if (badge) {
        badge.style.display = 'block';
    }
    if (typeof window.AudioManager !== 'undefined') {
        window.AudioManager.tocarSFX('som_notificacao'); // Toca um barulhinho se tiver
    }
};

// ==========================================
// 🎓 CERIMÔNIA DE MAESTRIA (RESGATE DE SELO)
// ==========================================
window.tentarResgatarSelo = async function(npcId, nomeNPC) {
    const charId = localStorage.getItem("jogadorEldoraID");
    
    try {
        const res = await fetch('/api/npc/resgatar_maestria', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: charId, npc_id: npcId })
        });
        
        const data = await res.json();

        if (data.success) {
            window.fecharDialogoRPG(); // Fecha a caixinha de diálogo
            
            // Um alerta épico de sucesso!
            if (window.alertaEldora) {
                window.alertaEldora("MAESTRIA ALCANÇADA", "Você recebeu o Selo de Maestria! A marca dourada agora repousa na sua mochila.", "sucesso");
            }
            
            // Acende a notificação do Pergaminho
            if (typeof window.ativarNotificacaoPergaminho === 'function') {
                window.ativarNotificacaoPergaminho();
            }
            
            // Atualiza os dados na tela (Inventário)
            if (typeof window.carregarMeuPerfil === 'function') window.carregarMeuPerfil();
            
        } else {
            window.mostrarDialogoRPG(nomeNPC, data.error);
        }
    } catch (e) {
        console.error("Erro ao resgatar o selo:", e);
        window.mostrarDialogoRPG(nomeNPC, "A magia falhou. Tente novamente mais tarde.");
    }
};

