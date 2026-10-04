// A navegação nunca depende da reprodução de áudio no WebView.
(() => {
    const actions={'btn-logar':'realizarLogin','btn-criar':'confirmarCriacao','btn-novo-heroi':'mostrarCriacao','btn-voltar-herois':'voltarParaSelecao'};
    for(const [id,action] of Object.entries(actions)){
        document.getElementById(id)?.addEventListener('click',()=>window[action]());
    }
    const name=document.getElementById('reg-heroiname');
    name?.addEventListener('input',()=>{document.getElementById('creation-name').textContent=name.value.trim()||'Seu herói';});
    name?.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();window.confirmarCriacao();}});
})();
