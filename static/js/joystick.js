// static/js/joystick.js

// ==========================================
// 1. BLINDAGEM CONTRA VAZAMENTO DE CLIQUES
// ==========================================
(function blindaCliquesMapa() {
    document.addEventListener('DOMContentLoaded', () => {
        const blindagem = document.getElementById('joystick-blindagem-externa');
        if (!blindagem) return;

        const eventosParaTravar = [
            'pointerdown',
            'pointermove',
            'pointerup',
            'pointercancel',
            'mousedown',
            'mousemove',
            'mouseup',
            'touchstart',
            'touchmove',
            'touchend',
            'click',
            'dblclick'
        ];

        eventosParaTravar.forEach(evento => {
            blindagem.addEventListener(evento, (e) => {
                e.preventDefault();
                e.stopPropagation();
            }, { passive: false });
        });
    });
})();

// ==========================================
// 2. ANALÓGICO REAL DO MAPA
// ==========================================
// Compatibilidade antiga: mapa.js antigo ainda pode ler joyDir.
window.joyDir = { up: false, down: false, left: false, right: false };

// Novo sistema: vetor livre do analógico.
// x/y vão de -1 até 1.
// intensity vai de 0 até 1.
window.joyVector = {
    x: 0,
    y: 0,
    intensity: 0,
    active: false
};

function atualizarJoyDirCompatibilidade(x, y) {
    const limite = 0.28;

    window.joyDir.left = x < -limite;
    window.joyDir.right = x > limite;
    window.joyDir.up = y < -limite;
    window.joyDir.down = y > limite;
}

function atualizarJoyVector(x, y, ativo = true) {
    const deadzone = 0.08;
    const intensidade = Math.min(1, Math.sqrt((x * x) + (y * y)));

    if (intensidade < deadzone || !ativo) {
        window.joyVector.x = 0;
        window.joyVector.y = 0;
        window.joyVector.intensity = 0;
        window.joyVector.active = false;

        atualizarJoyDirCompatibilidade(0, 0);
        return;
    }

    window.joyVector.x = x;
    window.joyVector.y = y;
    window.joyVector.intensity = intensidade;
    window.joyVector.active = true;

    atualizarJoyDirCompatibilidade(x, y);
}

function resetarJoyVector() {
    atualizarJoyVector(0, 0, false);

    const container = document.getElementById('joystick-container');
    const knob = document.getElementById('joystick-knob');

    if (container) container.classList.remove('joy-ativo');

    if (knob) {
        knob.style.transform = 'translate(-50%, -50%)';
    }
}

// Mantém as funções antigas caso algum HTML ainda chame startMove/stopMove.
window.startMove = function(dir) {
    if (!window.joyDir) return;

    window.joyDir[dir] = true;

    const x = (window.joyDir.right ? 1 : 0) + (window.joyDir.left ? -1 : 0);
    const y = (window.joyDir.down ? 1 : 0) + (window.joyDir.up ? -1 : 0);

    const vec = new Phaser.Math.Vector2(x, y);
    if (vec.length() > 1) vec.normalize();

    atualizarJoyVector(vec.x, vec.y, true);
};

window.stopMove = function(dir) {
    if (!window.joyDir) return;

    window.joyDir[dir] = false;

    const x = (window.joyDir.right ? 1 : 0) + (window.joyDir.left ? -1 : 0);
    const y = (window.joyDir.down ? 1 : 0) + (window.joyDir.up ? -1 : 0);

    const vec = new Phaser.Math.Vector2(x, y);
    if (vec.length() > 1) vec.normalize();

    if (vec.length() <= 0) {
        resetarJoyVector();
    } else {
        atualizarJoyVector(vec.x, vec.y, true);
    }
};

function iniciarAnalogicoEldora() {
    const container = document.getElementById('joystick-container');
    if (!container) return;
    if (container.dataset.analogicoEldora === 'sim') return;

    container.dataset.analogicoEldora = 'sim';

    // Reconstrói o visual. Assim não precisa mexer agora no joystick.html.
    container.innerHTML = `
        <div class="joy-base-visual"></div>
        <div id="joystick-knob" class="joy-knob"></div>
    `;

    const knob = document.getElementById('joystick-knob');

    let pointerAtivo = null;

    function calcularMovimento(pointerEvent) {
        const rect = container.getBoundingClientRect();

        const centroX = rect.left + (rect.width / 2);
        const centroY = rect.top + (rect.height / 2);

        let dx = pointerEvent.clientX - centroX;
        let dy = pointerEvent.clientY - centroY;

        const raioMaximo = Math.min(rect.width, rect.height) * 0.33;
        const distancia = Math.sqrt((dx * dx) + (dy * dy));

        if (distancia > raioMaximo) {
            dx = (dx / distancia) * raioMaximo;
            dy = (dy / distancia) * raioMaximo;
        }

        const xNormalizado = dx / raioMaximo;
        const yNormalizado = dy / raioMaximo;

        if (knob) {
            knob.style.transform = `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px))`;
        }

        container.classList.add('joy-ativo');
        atualizarJoyVector(xNormalizado, yNormalizado, true);
    }

    container.addEventListener('pointerdown', (e) => {
        e.preventDefault();
        e.stopPropagation();

        pointerAtivo = e.pointerId;

        try {
            container.setPointerCapture(e.pointerId);
        } catch (err) {}

        calcularMovimento(e);
    }, { passive: false });

    container.addEventListener('pointermove', (e) => {
        if (pointerAtivo !== e.pointerId) return;

        e.preventDefault();
        e.stopPropagation();

        calcularMovimento(e);
    }, { passive: false });

    function finalizarPointer(e) {
        if (pointerAtivo !== null && e.pointerId !== pointerAtivo) return;

        e.preventDefault();
        e.stopPropagation();

        pointerAtivo = null;

        try {
            container.releasePointerCapture(e.pointerId);
        } catch (err) {}

        resetarJoyVector();
    }

    container.addEventListener('pointerup', finalizarPointer, { passive: false });
    container.addEventListener('pointercancel', finalizarPointer, { passive: false });
    container.addEventListener('lostpointercapture', resetarJoyVector);

    document.addEventListener('visibilitychange', () => {
        if (document.hidden) resetarJoyVector();
    });
}

document.addEventListener('DOMContentLoaded', iniciarAnalogicoEldora);

// ==========================================
// 3. LÓGICA DO HUB/MENU DE CONFIGURAÇÕES
// ==========================================

// Variáveis de referência para não ficar buscando no DOM toda hora
let hub = null;
let joystickArea = null;
let containerAjustavel = null;

// Alterna a abertura do Hub (Mostra/Esconde)
window.alternarHubControles = function() {
    if (!hub) hub = document.getElementById('eldora-controles-hub');
    
    // Alterna a classe que esconde/mostra o menu
    let menuFechado = hub.classList.toggle('oculta-hub');
    
    // Busca os botões que ficam flutuando no mapa (Passe e Chat)
    let botoesFlutuantes = document.querySelectorAll('.btn-passe-mapa, .btn-social-mapa');
    
    if (menuFechado) {
        // Se o menu fechou, devolve os botões do mapa para a tela
        botoesFlutuantes.forEach(b => b.style.display = ''); 
    } else {
        // Se o menu abriu, esconde os botões para a tela ficar limpa
        botoesFlutuantes.forEach(b => b.style.display = 'none');
    }
};

// --- AÇÕES DO MENU ---

// A. Alternar Mostrar/Esconder o Analógico
window.alternarVisibilidadeJoystick = function() {
    if (!joystickArea) joystickArea = document.getElementById('joystick-blindagem-externa');
    let checkbox = document.getElementById('check-visibilidade');
    
    if (checkbox.checked) {
        // Se ligou o switch, mostra o analógico
        joystickArea.classList.remove('oculta-joystick');
        localStorage.setItem('eldora_hud_joystick_visivel', 'sim');
    } else {
        // Se desligou, esconde
        joystickArea.classList.add('oculta-joystick');
        localStorage.setItem('eldora_hud_joystick_visivel', 'nao');
    }
};

// B. Ajustar Opacidade (Transparência)
window.ajustarOpacidadeJoystick = function() {
    if (!joystickArea) joystickArea = document.getElementById('joystick-blindagem-externa');
    let slider = document.getElementById('slider-opacidade');
    
    // Converte o valor 0-100 para 0.0-1.0
    let valor = slider.value / 100;
    
    // Aplica a opacidade no contêiner inteiro
    joystickArea.style.opacity = valor;
    
    localStorage.setItem('eldora_hud_joystick_opacidade', slider.value);
};

// C. Ajustar Tamanho (Redimensionar)
window.ajustarTamanhoJoystick = function() {
    if (!containerAjustavel) containerAjustavel = document.getElementById('joystick-container');
    let slider = document.getElementById('slider-tamanho');
    
    // Converte o valor 50-150 para 0.5-1.5 de escala
    let valor = slider.value / 100;
    
    // Aplica o redimensionamento orgânico com Transform Scale
    containerAjustavel.style.transform = `scale(${valor})`;
    
    localStorage.setItem('eldora_hud_joystick_tamanho', slider.value);
};

// ==========================================
// 4. RECUPERANDO A MEMÓRIA AO CARREGAR O JOGO
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    // 1. Busca os elementos
    hub = document.getElementById('eldora-controles-hub');
    joystickArea = document.getElementById('joystick-blindagem-externa');
    containerAjustavel = document.getElementById('joystick-container');
    
    // 2. Busca os Inputs do Menu
    let checkbox = document.getElementById('check-visibilidade');
    let sliderOpacidade = document.getElementById('slider-opacidade');
    let sliderTamanho = document.getElementById('slider-tamanho');

    if (!joystickArea) return; // Segurança

    // 3. Lê as preferências do localStorage
    let prefVisivel = localStorage.getItem('eldora_hud_joystick_visivel');
    let prefOpacidade = localStorage.getItem('eldora_hud_joystick_opacidade');
    let prefTamanho = localStorage.getItem('eldora_hud_joystick_tamanho');

    // Avisa ao CSS que as configurações já foram carregadas (para o media query de PC)
    joystickArea.classList.add('eldora-config-carregada');

    // 4. Aplica a Visibilidade Salva
    if (prefVisivel === 'sim') {
        checkbox.checked = true;
        joystickArea.classList.remove('oculta-joystick');
    } else if (prefVisivel === 'nao') {
        checkbox.checked = false;
        joystickArea.classList.add('oculta-joystick');
    } else {
        // Primeira vez carregando: No Mobile mostra, no PC depende do CSS
        checkbox.checked = true; // Switch começa ligado
    }

    // 5. Aplica a Opacidade Salva
    if (prefOpacidade !== null) {
        sliderOpacidade.value = prefOpacidade;
        ajustarOpacidadeJoystick(); // Chama a função que já aplica no HUD
    }

    // 6. Aplica o Tamanho Salvo
    if (prefTamanho !== null) {
        sliderTamanho.value = prefTamanho;
        ajustarTamanhoJoystick(); // Chama a função que já aplica no HUD
    }
});