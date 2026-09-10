class MapaHUD {
    constructor(scene) {
        this.scene = scene;
        this.slotsContainers = []; 
        this.sidebarAberta = false; 
        this.btnToggle = null;
        this.init();
    }

    init() {
        const meuId = localStorage.getItem("jogadorEldoraID");
        if (!meuId) return;

        fetch(`/api/personagem/${meuId}?t=${new Date().getTime()}`)
            .then(r => r.json())
            .then(pdata => {
                //this.criarBarraHabilidades(pdata);
            })
            .catch(e => console.warn("Erro ao carregar o HUD:", e));
    }

    // 🛡️ TRAVA DE MOVIMENTO: Limpa para apenas bloquear objetos que REALMENTE existam na tela
    clicouNaUI(pointer) {
        let objetosClicados = this.scene.input.hitTestPointer(pointer);
        // Se bater num objeto real com profundidade alta (tipo as janelas), ele bloqueia.
        // Como o botão foi removido, a tela está livre!
        return objetosClicados.some(obj => obj.depth >= 1000);
    }

    //criarBarraHabilidades(pdata) {
        //const skillsEquipadas = pdata.skills_equipadas || {};
        //const dbSkills = pdata.database_skills || {};
        //const larguraCam = this.scene.cameras.main.width;
        //const alturaCam = this.scene.cameras.main.height;

        // 1. Botão Toggle (Aba Retrátil)
        //this.btnToggle = this.scene.add.container(larguraCam - 15, alturaCam / 2);
        
        // 🛠️ CORREÇÃO: setScrollFactor(0) cola o botão na tela (Câmera) e tira do chão!
        //this.btnToggle.setDepth(1001).setScrollFactor(0).setInteractive(new Phaser.Geom.Rectangle(-20, -35, 40, 70), Phaser.Geom.Rectangle.Contains);
        
        //const fundoBtn = this.scene.add.circle(0, 0, 18, 0x0f172a, 0.9).setStrokeStyle(2, 0x8b5cf6);
        //const seta = this.scene.add.text(-5, -10, "<", { fontSize: '20px', color: '#8b5cf6', fontStyle: 'bold' });
        //this.btnToggle.add([fundoBtn, seta]);

        //this.btnToggle.on('pointerdown', (pointer, localX, localY, event) => {
          //event.stopPropagation(); // Trava o Phaser
          //  this.alternarSidebar(seta);
        //});

        // 2. Criar Slots (Compatível com Array ou Object)
        //[1, 2, 3, 4, 5].forEach((slotNum, index) => {
          //  const skillId = Array.isArray(skillsEquipadas) ? null : skillsEquipadas[`slot_${slotNum}`];
            //if (!skillId) return;

            //const infoMagia = dbSkills[skillId] || {};
           // const nomeIcone = infoMagia.icon || 'default_skill';
           // const urlGitHub = `https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/sprites/skills/${nomeIcone}.png`;

           // const container = this.scene.add.container(larguraCam + 60, 120 + (index * 65));
            
            // 🛠️ CORREÇÃO: setScrollFactor(0) cola as magias na tela também!
            //container.setDepth(1000).setScrollFactor(0).setAlpha(0);
           // this.slotsContainers.push(container);

            // Desenha o círculo da skill
           // const bg = this.scene.add.circle(0, 0, 24, 0x0f172a, 0.9).setStrokeStyle(2, 0x8b5cf6);
            //container.add(bg);

            //this.scene.load.image(`icon_hud_${skillId}`, urlGitHub);
            //this.scene.load.once('complete', () => {
              //  const img = this.scene.add.image(0, 0, `icon_hud_${skillId}`).setDisplaySize(36, 36);
                //container.add(img);
            //});
            //this.scene.load.start();

            //container.setInteractive(new Phaser.Geom.Circle(0, 0, 24), Phaser.Geom.Circle.Contains);
           // container.on('pointerdown', (p, lx, ly, ev) => {
             //   ev.stopPropagation(); // Trava o movimento do mapa
               // this.scene.tweens.add({ targets: container, scale: 0.85, yoyo: true, duration: 100 });
              //  if (window.eldoraSocket) window.eldoraSocket.emit('usarSkillInvasao', { player_id: pdata._id, skill_id: skillId });
           // });
       // });
    //}

    alternarSidebar(seta) {
        this.sidebarAberta = !this.sidebarAberta;
        const larguraCam = this.scene.cameras.main.width;
        seta.setText(this.sidebarAberta ? ">" : "<");

        this.slotsContainers.forEach((c, i) => {
            this.scene.tweens.add({
                targets: c,
                x: this.sidebarAberta ? larguraCam - 45 : larguraCam + 60,
                alpha: this.sidebarAberta ? 1 : 0,
                duration: 300,
                delay: i * 50,
                ease: 'Back.easeOut'
            });
        });
    }
}