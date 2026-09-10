// ==========================================
// GERENCIADOR DO HUD DA INVASÃO (VISUAL)
// ==========================================

class HudInvasao {
    constructor() {
        this.timerInvasao = null;
        this.tempoRestante = 0; 
        
        // Constrói a interface assim que instanciado
        this.construirInterface();
    }

    construirInterface() {
        if (document.getElementById('hud-invasao')) return;

        const divInvasao = document.createElement('div');
        divInvasao.id = 'hud-invasao';
        
        Object.assign(divInvasao.style, {
            display: 'none'
        });

        divInvasao.innerHTML = `
            <div class="invasao-header">🛡️ DEFESA DO REINO 🛡️</div>
            <div class="invasao-onda" id="invasao-onda-texto">AGUARDANDO...</div>
            <div class="invasao-stats">
                <div class="stat-box">
                    <span class="stat-label">TEMPO RESTANTE</span>
                    <span class="stat-value" id="invasao-tempo">00:00</span>
                </div>
                <div class="stat-box">
                    <span class="stat-label">INIMIGOS VIVOS</span>
                    <span class="stat-value" id="invasao-mobs">0</span>
                </div>
            </div>
        `;

        document.body.appendChild(divInvasao);
    }

    /**
     * Exibe o HUD e inicia o contador com o tempo vindo do servidor
     * @param {number} onda - Número da onda atual (0 para preparação)
     * @param {number} segundos - Segundos restantes calculados pelo Python
     */
    mostrar(onda, segundos) {
        let hud = document.getElementById('hud-invasao');
        if (hud) hud.style.display = 'flex';
        
        const txtOnda = document.getElementById('invasao-onda-texto');
        if (txtOnda) {
            txtOnda.innerText = onda === 0 ? '🔥 PREPARAÇÃO 🔥' : `ONDA ${onda}`;
        }

        this.iniciarRelogio(segundos);
    }

    iniciarRelogio(segundos) {
        if (this.timerInvasao) clearInterval(this.timerInvasao);
    
        // 🛡️ BLINDAGEM ANTI-NaN
        // Se 'segundos' for inválido, tenta usar o que já estava no HUD ou 1800 padrão
        this.tempoRestante = (isNaN(segundos) || segundos === undefined) ? (this.tempoRestante || 1800) : segundos;
    
        const elTempo = document.getElementById('invasao-tempo');
        const formatar = (s) => `${Math.floor(s/60).toString().padStart(2,'0')}:${(s%60).toString().padStart(2,'0')}`;

        if (elTempo) elTempo.innerText = formatar(this.tempoRestante);

        this.timerInvasao = setInterval(() => {
            this.tempoRestante--;
            if (this.tempoRestante <= 0) {
                clearInterval(this.timerInvasao);
                this.tempoRestante = 0;
            }
            if (elTempo) elTempo.innerText = formatar(this.tempoRestante);
        }, 1000);
    }

    atualizarContador(quantidade) {
        let elMobs = document.getElementById('invasao-mobs');
        if (elMobs) elMobs.innerText = quantidade;
    }

    esconder() {
        if (this.timerInvasao) clearInterval(this.timerInvasao);
        
        let hud = document.getElementById('hud-invasao');
        if (hud) {
            // Efeito suave de saída
            hud.style.opacity = '0';
            setTimeout(() => {
                hud.style.display = 'none';
                hud.style.opacity = '1';
            }, 1000);
        }
    }
}