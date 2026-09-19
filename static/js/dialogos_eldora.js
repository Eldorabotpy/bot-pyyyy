(() => {
    'use strict';
    const queue = [];
    let active = null;
    const icons = {
        aviso: '<path d="M12 3 2 21h20L12 3Z"/><path d="M12 9v5m0 3v1"/>',
        sucesso: '<path d="m5 12 4 4L19 6"/><circle cx="12" cy="12" r="10"/>',
        erro: '<circle cx="12" cy="12" r="10"/><path d="m8 8 8 8m0-8-8 8"/>',
        confirmar: '<path d="m12 2 9 4v6c0 5-9 10-9 10S3 17 3 12V6l9-4Z"/><path d="m8 12 3 3 5-6"/>',
        texto: '<path d="M5 4h14v16H5zM8 8h8M8 12h8M8 16h4"/>',
        pocao: '<path d="M9 2h6m-5 0v7l-6 9a3 3 0 0 0 3 4h10a3 3 0 0 0 3-4l-6-9V2M7 15h10"/>'
    };
    function openNext() {
        if (active || !queue.length) return;
        if (!document.body) { document.addEventListener('DOMContentLoaded', openNext, {once:true}); return; }
        const request = queue.shift();
        const previousFocus = document.activeElement;
        const dialog = document.createElement('dialog');
        dialog.id = 'modal-alerta-eldora';
        dialog.className = 'eldora-dialog';
        dialog.setAttribute('aria-labelledby', 'eldora-dialog-title');
        dialog.setAttribute('aria-describedby', 'eldora-dialog-message');
        const type = icons[request.type] ? request.type : 'aviso';
        dialog.dataset.type = type;
        dialog.innerHTML = `<div class="eldora-dialog-top"><span>REINO DE ELDORA</span><button class="eldora-dialog-close" type="button" aria-label="Fechar">×</button></div>
            <div class="eldora-dialog-content"><div class="eldora-dialog-emblem" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">${icons[type]}</svg></div>
            <h2 id="eldora-dialog-title"></h2><p id="eldora-dialog-message"></p>
            <label class="eldora-dialog-field" hidden><span>Sua resposta</span><input type="text" autocomplete="off" maxlength="500"></label></div>
            <div class="eldora-dialog-actions"><button type="button" class="eldora-dialog-cancel">Cancelar</button><button type="button" class="eldora-dialog-accept"></button></div>`;
        dialog.querySelector('h2').textContent = request.title;
        dialog.querySelector('p').textContent = String(request.message ?? '');
        const cancel = dialog.querySelector('.eldora-dialog-cancel');
        const accept = dialog.querySelector('.eldora-dialog-accept');
        const input = dialog.querySelector('input');
        cancel.hidden = request.mode === 'alert';
        accept.textContent = request.mode === 'alert' ? 'Entendido' : 'Confirmar';
        if (request.mode === 'prompt') {
            dialog.querySelector('label').hidden = false;
            input.value = request.initial;
        }
        const scene = window.jogoEldora?.scene?.getScene('MapaScene');
        scene?.player?.body?.stop();
        if (scene) scene.isMoving = false;
        scene?.input?.keyboard?.resetKeys?.();
        window.__eldoraDialogAberto = true;
        let settled = false;
        const finish = ok => {
            if (settled) return;
            settled = true;
            const result = request.mode === 'prompt' ? (ok ? input.value : null) : !!ok;
            dialog.close();
            dialog.remove();
            active = null;
            window.__eldoraDialogAberto = false;
            previousFocus?.isConnected && previousFocus.focus?.({preventScroll:true});
            request.resolve(result);
            openNext();
        };
        active = {dialog, request};
        cancel.onclick = () => finish(false);
        accept.onclick = () => finish(true);
        dialog.querySelector('.eldora-dialog-close').onclick = () => finish(false);
        dialog.addEventListener('cancel', event => {event.preventDefault(); finish(false);});
        dialog.addEventListener('keydown', event => {
            if (event.key === 'Enter' && event.target === input) { event.preventDefault(); finish(true); }
        });
        for (const name of ['pointerdown','pointerup','pointermove','mousedown','mouseup','click','dblclick','touchstart','touchend','touchmove','wheel','keydown','keyup']) {
            dialog.addEventListener(name, event => event.stopPropagation());
        }
        document.body.appendChild(dialog);
        dialog.showModal();
        (request.mode === 'prompt' ? input : request.mode === 'confirm' ? cancel : accept).focus();
    }
    function enqueue(mode, message, title, type, initial = '') {
        // A repeated click shares the same pending choice instead of stacking identical questions.
        const duplicate = [active?.request, ...queue].find(r => r && r.mode === mode && r.message === message && r.title === title);
        if (duplicate) return mode === 'alert' ? duplicate.promise : Promise.resolve(mode === 'prompt' ? null : false);
        let resolve;
        const promise = new Promise(r => {resolve = r;});
        queue.push({mode,message,title,type,initial,resolve,promise});
        openNext();
        return promise;
    }
    window.alertaEldora = (title, message, type = 'aviso') => enqueue('alert', message, title, type);
    window.avisoEldora = message => window.alertaEldora('Aviso de Eldora', message);
    window.confirmarEldora = (message, title = 'Confirmar ação') => enqueue('confirm', message, title, 'confirmar');
    window.solicitarTextoEldora = (message, initial = '') => enqueue('prompt', message, 'Sua confirmação', 'texto', initial);
})();
