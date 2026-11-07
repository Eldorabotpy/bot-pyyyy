/* Medição voluntária: ?desempenho=1. Relatórios ficam apenas neste navegador. */
(function () {
    'use strict';
    function resumo(samples) {
        if (!samples.length) return null;
        const stat = key => {
            const values = samples.map(s => s[key]).filter(Number.isFinite).sort((a,b)=>a-b);
            if (!values.length) return null;
            return { media: +(values.reduce((a,b)=>a+b,0)/values.length).toFixed(2), p95: +values[Math.ceil(values.length*.95)-1].toFixed(2) };
        };
        const frame = stat('frame');
        return { quadros: samples.length, fps: +(1000/(samples.reduce((a,s)=>a+s.frame,0)/samples.length)).toFixed(1), intervaloMs: frame,
            cenaCpuMs: stat('scene'), desenhoCpuMs: stat('render'), quadrosAcima50ms: samples.filter(s=>s.frame>50).length };
    }
    if (typeof module !== 'undefined' && module.exports) { module.exports = { resumo }; return; }
    if (new URLSearchParams(location.search).get('desempenho') !== '1') return;
    function init() {
        let active = null, reports = [];
        try { reports = JSON.parse(sessionStorage.getItem('eldora-performance') || '[]'); if (!Array.isArray(reports)) reports=[]; } catch (_) {}
        const panel = document.createElement('section');
        panel.style.cssText='position:fixed;top:100px;left:8px;z-index:99999;width:260px;max-width:85vw;padding:10px;background:#101820ed;color:#fff;border:1px solid #c6ac65;border-radius:8px;font:13px Arial;box-sizing:border-box';
        panel.innerHTML='<strong>Medição de fluidez</strong><div data-status>Entre no mapa e escolha uma medição de 20 segundos.</div><button data-mode="parado">Medir parado</button> <button data-mode="andando">Medir andando</button><br><button data-stop>Parar</button> <button data-copy>Copiar relatório</button> <button data-close>Fechar</button><textarea data-report readonly aria-label="Relatório de desempenho" style="display:none;width:100%;height:150px;box-sizing:border-box"></textarea>';
        document.body.appendChild(panel);
        const status=panel.querySelector('[data-status]');
        panel.querySelectorAll('button').forEach(b=>{b.style.cssText='min-height:36px;margin:3px 0;touch-action:manipulation';});
        ['pointerdown','pointermove','pointerup','click','touchstart','touchmove','touchend'].forEach(event=>panel.addEventListener(event,e=>e.stopPropagation()));
        function finish(reason) {
            const c=active; if(!c)return; active=null;
            clearTimeout(c.timer); clearInterval(c.ui);
            c.scene.events.off('preupdate',c.pre);c.scene.events.off('postupdate',c.post);c.scene.events.off('shutdown',c.shutdown);
            c.game.events.off('prerender',c.renderPre);c.game.events.off('postrender',c.renderPost);
            const report={...c.meta,motivoFim:reason,segundos:+((performance.now()-c.start)/1000).toFixed(1),geral:resumo(c.samples),parado:resumo(c.samples.filter(s=>!s.moving)),andando:resumo(c.samples.filter(s=>s.moving))};
            reports.push(report);reports=reports.slice(-8);
            try{sessionStorage.setItem('eldora-performance',JSON.stringify(reports));}catch(_){}
            status.textContent=report.geral ? `${report.regiao}: ${report.geral.fps} FPS; ${report.geral.quadrosAcima50ms} quadros acima de 50 ms. Medição salva. Faça a outra medição e copie o relatório.` : 'Sem amostras. Aguarde o mapa carregar e tente novamente.';
        }
        function start(mode) {
            finish('nova medição');
            const game=window.jogoEldora, scene=game?.scene?.keys?.MapaScene;
            if(!scene?.player || !scene.carregamentoMapaFinalizado || !scene.sys.isActive()) {status.textContent='Entre no mapa e aguarde o carregamento terminar.';return;}
            const now=performance.now(),canvas=game.canvas;
            const c={scene,game,start:now,last:null,samples:[],sceneStart:0,sceneMs:0,renderStart:0};active=c;
            c.meta={versao:2,buildMapa:document.querySelector?.('script[src*="/static/js/mapa.js"]')?.src || null,data:new Date().toISOString(),regiao:scene.regiaoAtual,modoSolicitado:mode,renderer:game.renderer.gl?'WebGL':'Canvas',canvas:[canvas.width,canvas.height],telaCss:[innerWidth,innerHeight],pixelRatio:devicePixelRatio,navegador:navigator.userAgent,camadas:scene.tilemap?.layers?.length,corposEstaticos:scene.physics?.world?.staticBodies?.size,objetosCena:scene.children?.list?.length,observacao:'Primeiros 2s descartados. CPU do desenho não mede tempo da GPU. Não mede latência de rede.'};
            c.pre=()=>{c.sceneStart=performance.now();};
            c.post=()=>{c.sceneMs=performance.now()-c.sceneStart;};
            c.renderPre=()=>{c.renderStart=performance.now();};
            c.renderPost=()=>{
                const t=performance.now();
                if(c.last!==null && t-c.start>=2000 && c.samples.length<5000) {
                    const v=scene.player?.body?.velocity;
                    c.samples.push({frame:t-c.last,scene:c.sceneMs,render:t-c.renderStart,moving:Math.hypot(v?.x||0,v?.y||0)>1});
                }
                c.last=t;
            };
            c.shutdown=()=>finish('troca de mapa');
            scene.events.on('preupdate',c.pre);scene.events.on('postupdate',c.post);scene.events.once('shutdown',c.shutdown);
            game.events.on('prerender',c.renderPre);game.events.on('postrender',c.renderPost);
            c.ui=setInterval(()=>{status.textContent=`${scene.regiaoAtual}: ${mode==='parado'?'fique parado':'ande normalmente'} por mais ${Math.max(0,Math.ceil(20-(performance.now()-now)/1000))}s.`;},500);
            c.timer=setTimeout(()=>finish('20 segundos completos'),20000);
            status.textContent=mode==='parado'?'Fique parado por 20 segundos.':'Ande normalmente por 20 segundos.';
        }
        panel.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>start(b.dataset.mode));
        panel.querySelector('[data-stop]').onclick=()=>finish('interrompido pelo jogador');
        panel.querySelector('[data-close]').onclick=()=>{finish('painel fechado');document.removeEventListener('visibilitychange',hidden);panel.remove();};
        panel.querySelector('[data-copy]').onclick=async()=>{
            const text=JSON.stringify({eldoraDesempenho:reports},null,2),area=panel.querySelector('[data-report]');
            area.value=text;area.style.display='block';
            try{await navigator.clipboard.writeText(text);status.textContent='Relatório copiado. Cole na conversa.';}catch(_){area.focus();area.select();status.textContent='Selecione e copie o relatório abaixo para enviar na conversa.';}
        };
        function hidden(){if(document.hidden)finish('aplicativo foi para segundo plano');}
        document.addEventListener('visibilitychange',hidden);
    }
    if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
