(() => {
    let status=null,busy=false,googleLoaded=false;
    const box=document.getElementById('portal-identidade');
    const note=text=>{document.getElementById('portal-auth-message').textContent=text;};
    window.portalAuthHeaders=()=>({'Content-Type':'application/json','X-Eldora-CSRF':status?.csrf||''});
    async function post(path,data){
        const response=await fetch(path,{method:'POST',headers:window.portalAuthHeaders(),body:JSON.stringify(data)});
        const result=await response.json();
        if(!response.ok||result.erro)throw new Error(result.erro||'Não foi possível entrar.');
        return result;
    }
    window.portalRefresh=async()=>{
        const response=await fetch('/api/auth/status',{cache:'no-store'});
        if(!response.ok)throw new Error('Não foi possível verificar sua sessão.');
        const previouslyAuthenticated=!!status?.authenticated;
        status=await response.json();
        if(previouslyAuthenticated!==!!status.authenticated||!status.authenticated)box.open=!status.authenticated;
        if(status.authenticated&&new URLSearchParams(location.search).has('conta')&&!previouslyAuthenticated)box.open=true;
        document.getElementById('portal-account-summary').textContent=status.authenticated?'Minha conta · vínculos e acesso':'Entrar ou criar conta';
        if(!status.authenticated)document.getElementById('titulo-caixa').textContent='ENTRAR NO REINO';
        document.getElementById('portal-auth-state').textContent=status.authenticated?`Conta conectada · Google: ${status.google_linked?'vinculado':'não vinculado'} · Telegram: ${status.telegram_linked?'vinculado':'não vinculado'}`:'Entre ou crie sua conta. Já joga? Entre na conta antiga antes de vincular.';
        const mode=document.getElementById('portal-auth-mode');
        mode.innerHTML=status.authenticated?'<option value="link">Vincular à minha conta atual</option>':'<option value="login">Entrar em conta vinculada</option><option value="create">Criar nova conta</option>';
        document.getElementById('portal-logout').hidden=!status.authenticated;
        const telegram=window.Telegram?.WebApp?.initData;
        document.getElementById('portal-telegram').hidden=!telegram;
        document.getElementById('portal-google-note').textContent=status.google_client_id?'':'Login Google aguardando configuração. Contas existentes podem entrar com senha; novas contas podem ser criadas pelo Telegram.';
        if(status.google_client_id&&!googleLoaded){
            googleLoaded=true;
            const script=document.createElement('script');script.src='https://accounts.google.com/gsi/client';script.async=true;
            script.onload=()=>{
                google.accounts.id.initialize({client_id:status.google_client_id,callback:r=>authenticate('google',{credential:r.credential})});
                google.accounts.id.renderButton(document.getElementById('portal-google'),{type:'standard',theme:'outline',size:'large',text:'continue_with',width:240});
            };
            script.onerror=()=>{googleLoaded=false;note('Não foi possível carregar o Google. Tente novamente.');};
            document.head.appendChild(script);
        }
        return status;
    };
    async function authenticate(provider,credentials){
        if(busy)return;
        const mode=document.getElementById('portal-auth-mode').value;
        if(mode==='create'&&!confirm('Criar uma conta nova? Se você já joga Eldora, cancele e entre na sua conta existente para vinculá-la.'))return;
        busy=true;note('Validando identidade…');
        try{
            const result=await post('/api/auth/'+provider,{mode,...credentials});
            await window.portalRefresh();window.portalAccept(result);
            note(mode==='link'?'Vinculação concluída. Seus personagens continuam na mesma conta.':'Conta conectada. Escolha seu personagem.');
        }catch(error){note(error.message);}finally{busy=false;}
    }
    document.getElementById('portal-auth-mode').onchange=event=>{
        if(!status?.authenticated)document.getElementById('titulo-caixa').textContent=event.target.value==='create'?'CRIAR SUA CONTA':'ENTRAR NO REINO';
        document.getElementById('tela-login').style.display=event.target.value==='create'?'none':status?.authenticated?'none':'block';
    };
    document.getElementById('portal-telegram').onclick=()=>authenticate('telegram',{init_data:window.Telegram?.WebApp?.initData||''});
    document.getElementById('portal-logout').onclick=async()=>{try{await post('/api/auth/logout',{});location.reload();}catch(e){note(e.message);}};
    window.portalSelect=id=>post('/api/auth/select',{character_id:id});
    // Remove cópias antigas de senhas, preservando os dados dos personagens no servidor.
    localStorage.removeItem('eldora_contas_salvas');
    window.portalAuthReady=window.portalRefresh().then(data=>{
        document.getElementById('tela-registro-conta').style.display='none';
        if(data.authenticated)window.portalAccept(data);
        else document.getElementById('tela-login').style.display='block';
    }).catch(error=>note(error.message));
})();
