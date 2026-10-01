class MapaHUD {
    constructor(scene) {
        this.scene = scene;
        this.slotsContainers = []; 
        this.sidebarAberta = false; 
        this.btnToggle = null;
        this.criarContadorXP();
        this.init();
    }

    init() {
        const meuId = localStorage.getItem("jogadorEldoraID");
        if (!meuId) return;

        fetch(`/api/personagem/${meuId}?t=${new Date().getTime()}`)
            .then(r => r.json())
            .then(pdata => {
                if (!this.encerrado) this.sincronizarXP(pdata);
            })
            .catch(e => console.warn("Erro ao carregar o HUD:", e));
    }

    criarContadorXP() {
        this.encerrado = false;
        this.xpExpira = 0;
        this.xpRelogioOffset = 0;
        // Pequeno indicador no rodapé do mapa, sem capturar toques.
        this.xpTexto = this.scene.add.text(0, 0, '', {
            fontFamily: 'Arial, sans-serif', fontSize: '11px',
            color: '#e9d5ff', backgroundColor: '#171426cc',
            padding: { x: 7, y: 4 }
        }).setOrigin(0.5, 1).setScrollFactor(0).setDepth(950).setVisible(false);
        this.xpListener = event => this.sincronizarXP(event.detail);
        window.addEventListener('eldora:xp-boost', this.xpListener);
        this.xpTimer = this.scene.time.addEvent({ delay: 1000, loop: true, callback: () => this.atualizarContadorXP() });
        const limpar = () => {
            if (this.encerrado) return;
            this.encerrado = true;
            window.removeEventListener('eldora:xp-boost', this.xpListener);
            this.xpTimer.remove();
            this.xpTexto.destroy();
            this.scene.events.off('shutdown', limpar);
            this.scene.events.off('destroy', limpar);
        };
        this.scene.events.once('shutdown', limpar);
        this.scene.events.once('destroy', limpar);
    }

    sincronizarXP(dados) {
        if (this.encerrado || !dados || !Object.prototype.hasOwnProperty.call(dados, 'xp_boost')) return;
        const boost = dados.xp_boost || {};
        const servidor = Date.parse(dados.server_time);
        this.xpRelogioOffset = Number.isFinite(servidor) ? servidor - Date.now() : 0;
        this.xpExpira = Number(boost.multiplier) > 1 ? Date.parse(boost.expires_at) : 0;
        this.atualizarContadorXP();
    }

    atualizarContadorXP() {
        if (this.encerrado) return;
        const restante = Math.max(0, Math.ceil((this.xpExpira - Date.now() - this.xpRelogioOffset) / 1000));
        this.xpTexto.setVisible(Number.isFinite(restante) && restante > 0);
        if (!Number.isFinite(restante) || restante <= 0) return;
        const minutos = Math.floor(restante / 60);
        const segundos = String(restante % 60).padStart(2, '0');
        this.xpTexto.setText(`XP ×2 · ${minutos}:${segundos}`);
        this.xpTexto.setPosition(this.scene.scale.width / 2, this.scene.scale.height - 12);
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