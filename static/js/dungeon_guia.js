/* Estátua da entrada: consulta a execução atual sem alterar seu progresso. */
window.DungeonGuardianGuide = class DungeonGuardianGuide {
    constructor(scene, map) {
        this.scene = scene;
        const obj = map.objects.flatMap(layer => layer.objects || [])
            .find(item => item.name === 'estatua_guardiao');
        if (!obj) return;
        const x = obj.x + obj.width / 2;
        const y = obj.y + obj.height;
        this.destination = {x, y: y + 26};
        this.zone = scene.add.zone(x, obj.y + obj.height / 2, obj.width, obj.height)
            .setDepth(25).setInteractive({useHandCursor: true});
        this.marker = scene.add.text(x, obj.y + 14, '📜', {
            fontSize: '23px', backgroundColor: '#152031', padding: {x: 5, y: 3}
        }).setOrigin(0.5).setDepth(26).setInteractive({useHandCursor: true});
        if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            this.pulse = scene.tweens.add({targets: this.marker, y: obj.y + 8,
                alpha: 0.65, duration: 900, yoyo: true, repeat: -1});
        }
        const interact = (pointer, lx, ly, event) => {
            event?.stopPropagation();
            if (window.combateAbertoBloqueandoMapa || window.__eldoraDialogAberto || scene.isDead) return;
            scene.motorCacada?.pararAutoCacada('consulta ao guardião', true);
            this.pending = true;
            this.deadline = Date.now() + 12000;
            scene.target = {...this.destination};
            scene.isMoving = true;
            scene.physics.moveToObject(scene.player, scene.target, 150);
        };
        this.zone.on('pointerdown', interact);
        this.marker.on('pointerdown', interact);
        this.tick = () => {
            if (!this.pending) return;
            if (Date.now() > this.deadline || window.combateAbertoBloqueandoMapa) {
                this.pending = false; return;
            }
            if (Math.hypot(scene.player.x - x, scene.player.y - y) <= 78) {
                this.pending = false;
                scene.player.body.stop(); scene.isMoving = false; scene.target = null;
                this.open();
            }
        };
        scene.events.on('update', this.tick);
        scene.events.once('shutdown', () => this.destroy());
        scene.events.once('destroy', () => this.destroy());
    }

    open() {
        if (this.dialog || window.__eldoraDialogAberto) return;
        const dialog = document.createElement('dialog');
        dialog.className = 'dungeon-guide';
        dialog.setAttribute('aria-labelledby', 'guardian-title');
        dialog.innerHTML = `
            <header><span class="guardian-icon" aria-hidden="true">📜</span><div>
                <small>CATACUMBAS DO REI CAÍDO</small><h2 id="guardian-title">Estátua do Guardião</h2>
            </div><button type="button" data-close aria-label="Fechar instruções">×</button></header>
            <div class="guardian-scroll"><p class="guardian-quote">“A coroa caída só despertará quando seus servos encontrarem o descanso. Observe as pedras, desconfie dos tesouros e siga até o trono.”</p>
            <section class="guardian-progress" aria-live="polite"><span data-progress>Consultando sua execução…</span>
                <progress value="0" max="1" aria-label="Monstros derrotados"></progress><strong data-boss></strong>
                <button type="button" data-refresh>↻ Atualizar</button></section>
            <nav role="tablist" aria-label="Instruções da dungeon">
                <button role="tab" id="guardian-tab-goal" aria-controls="guardian-goal" aria-selected="true" data-tab="goal">Objetivo</button>
                <button role="tab" id="guardian-tab-chests" aria-controls="guardian-chests" aria-selected="false" tabindex="-1" data-tab="chests">Baús</button>
                <button role="tab" id="guardian-tab-rules" aria-controls="guardian-rules" aria-selected="false" tabindex="-1" data-tab="rules">Regras</button>
            </nav>
            <section role="tabpanel" id="guardian-goal" aria-labelledby="guardian-tab-goal"><h3>Desperte o rei</h3><p>Derrote todos os monstros normais desta execução para fazer o Rei Caído aparecer. Mímicos não entram nessa contagem.</p><p>Os monstros derrotados não reaparecem durante a execução. Vença o Rei Caído para concluir as Catacumbas.</p></section>
            <section role="tabpanel" id="guardian-chests" aria-labelledby="guardian-tab-chests" hidden><h3>Cinco tesouros, dois desafios</h3><p><b>Baú do enigma:</b> consulte a charada e acerte a sequência das pedras. Uma sequência errada pode despertar um mímico.</p><p><b>Quatro baús comuns:</b> toque para tentar abrir. Cada um tem 30% de chance de revelar um mímico; vença-o para liberar o tesouro.</p><p>Cada baú entrega seu prêmio <b>uma vez por jogador, por execução</b>. Depois de resgatado, não abre novamente nessa execução.</p></section>
            <section role="tabpanel" id="guardian-rules" aria-labelledby="guardian-tab-rules" hidden><h3>Prepare sua expedição</h3><p>Cada jogador precisa de uma Chave de Masmorra para entrar. Retornar à mesma execução ativa não consome outra chave.</p><p>No grupo, participam os membros que estavam na equipe quando a execução começou. Quem entrar depois precisa aguardar a próxima.</p><p>Quando o último jogador sai, a execução termina. Entrar novamente inicia outra aventura e exige nova chave. No solo, sair também encerra sua execução.</p></section></div>
            <footer><button type="button" data-close>Entendido · continuar exploração</button></footer>`;
        this.dialog = dialog;
        this.previousInput = this.scene.input.enabled;
        this.previousKeyboard = this.scene.input.keyboard?.enabled;
        window.__eldoraDialogAberto = true;
        this.scene.input.enabled = false;
        if (this.scene.input.keyboard) {
            this.scene.input.keyboard.resetKeys(); this.scene.input.keyboard.enabled = false;
        }
        this.scene.player.body.stop();
        for (const event of ['pointerdown','pointerup','click','touchstart','touchend','wheel','keydown','keyup']) {
            dialog.addEventListener(event, e => e.stopPropagation());
        }
        dialog.querySelectorAll('[data-close]').forEach(b => b.onclick = () => this.close());
        dialog.addEventListener('cancel', e => {e.preventDefault(); this.close();});
        const tabs = [...dialog.querySelectorAll('[data-tab]')];
        const select = button => {
            tabs.forEach(tab => {const active = tab === button;
                tab.setAttribute('aria-selected', String(active)); tab.tabIndex = active ? 0 : -1;
                dialog.querySelector('#guardian-' + tab.dataset.tab).hidden = !active;});
        };
        tabs.forEach((button, i) => {
            button.onclick = () => select(button);
            button.onkeydown = e => {
                if (!['ArrowLeft','ArrowRight','Home','End'].includes(e.key)) return;
                e.preventDefault();
                const next = tabs[e.key === 'Home' ? 0 : e.key === 'End' ? 2 : (i + (e.key === 'ArrowRight' ? 1 : 2)) % 3];
                select(next); next.focus();
            };
        });
        dialog.querySelector('[data-refresh]').onclick = () => this.refresh();
        document.body.append(dialog); dialog.showModal();
        this.refresh();
        this.poll = setInterval(() => this.refresh(), 5000);
    }

    async refresh() {
        if (!this.dialog || this.loading) return;
        this.loading = true;
        const dialog = this.dialog;
        this.abort = new AbortController();
        const timeout = setTimeout(() => this.abort?.abort(), 8000);
        try {
            const params = new URLSearchParams({user_id: localStorage.getItem('jogadorEldoraID') || ''});
            const response = await fetch('/api/dungeon/guia?' + params, {cache: 'no-store', signal: this.abort.signal});
            const data = await response.json();
            if (!response.ok || !data.success) throw new Error(data.error || 'Não foi possível consultar o progresso.');
            if (this.dialog !== dialog) return;
            dialog.querySelector('[data-progress]').textContent = `Monstros restantes: ${data.restantes}/${data.total}`;
            const bar = dialog.querySelector('progress'); bar.max = Math.max(1, data.total); bar.value = data.total - data.restantes;
            dialog.querySelector('[data-boss]').textContent = `Rei Caído: ${data.boss}`;
        } catch (error) {
            if (this.dialog === dialog) {
                dialog.querySelector('[data-progress]').textContent = 'Progresso indisponível. Toque em Atualizar.';
                dialog.querySelector('[data-boss]').textContent = '';
                dialog.querySelector('progress').removeAttribute('value');
            }
        } finally { clearTimeout(timeout); this.loading = false; }
    }

    close() {
        if (!this.dialog) return;
        clearInterval(this.poll); this.abort?.abort();
        this.dialog.close(); this.dialog.remove(); this.dialog = null;
        window.__eldoraDialogAberto = false;
        this.scene.input.enabled = this.previousInput;
        if (this.scene.input.keyboard) {this.scene.input.keyboard.resetKeys(); this.scene.input.keyboard.enabled = this.previousKeyboard;}
    }

    destroy() {
        if (this.destroyed) return;
        this.destroyed = true;
        this.close(); this.pending = false;
        this.scene.events.off('update', this.tick);
        this.pulse?.stop(); this.zone?.destroy(); this.marker?.destroy();
    }
};
