// A navegação nunca depende da reprodução de áudio no WebView.
(() => {
    const actions={'btn-logar':'realizarLogin','btn-criar':'confirmarCriacao','btn-novo-heroi':'mostrarCriacao','btn-voltar-herois':'voltarParaSelecao'};
    for(const [id,action] of Object.entries(actions)){
        document.getElementById(id)?.addEventListener('click',()=>window[action]());
    }
    // Som independente da ação: erros de mídia não interrompem os controles.
    document.addEventListener('click',event=>{
        if(event.target.closest('button,summary,select')){try{window.playClick?.();}catch(_){}}
    });
    for(const id of ['login-password','telegram-password','telegram-password-confirm']){
        const input=document.getElementById(id);if(!input)continue;
        const toggle=document.createElement('button');toggle.type='button';toggle.className='portal-back';
        toggle.textContent='Mostrar senha';toggle.setAttribute('aria-controls',id);toggle.setAttribute('aria-pressed','false');
        toggle.addEventListener('click',()=>{const show=input.type==='password';input.type=show?'text':'password';toggle.textContent=show?'Ocultar senha':'Mostrar senha';toggle.setAttribute('aria-pressed',String(show));});
        input.after(toggle);
    }
    document.getElementById('login-password')?.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();window.realizarLogin();}});
    const music=new Audio('https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/game_sons/regioes/capital.mp3');
    music.loop=true;music.volume=.2;
    const sound=document.getElementById('portal-sound');let enabled=true,started=false;
    try{enabled=localStorage.getItem('eldora_portal_music')!=='off';}catch(_){}
    const label=()=>{sound.textContent=started?'Silenciar música':'Ativar música';sound.setAttribute('aria-pressed',String(started));};
    const startMusic=()=>{if(!enabled||document.hidden)return;try{music.play().then(()=>{started=true;label();}).catch(()=>{started=false;label();});}catch(_){}};
    sound.addEventListener('click',()=>{if(started){enabled=false;started=false;music.pause();}else{enabled=true;startMusic();}try{localStorage.setItem('eldora_portal_music',enabled?'on':'off');}catch(_){}label();});
    document.addEventListener('pointerdown',event=>{if(event.target!==sound&&!started)startMusic();},{passive:true});
    document.addEventListener('visibilitychange',()=>{if(document.hidden){music.pause();started=false;label();}else startMusic();});
    window.addEventListener('pagehide',()=>music.pause());
    const name=document.getElementById('reg-heroiname');
    name?.addEventListener('input',()=>{document.getElementById('creation-name').textContent=name.value.trim()||'Seu herói';});
    name?.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();window.confirmarCriacao();}});
})();
