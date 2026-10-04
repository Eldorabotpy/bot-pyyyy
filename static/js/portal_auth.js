(() => {
    let status=null,busy=false,googleLoaded=false,screen='login';
    const inTelegram=!!window.Telegram?.WebApp?.initData;
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
        status=await response.json();
        document.getElementById('telegram-credentials').hidden=!(inTelegram&&status.authenticated&&!status.has_password);
        document.getElementById('telegram-save-credentials').hidden=!(inTelegram&&status.authenticated&&!status.has_password);
        document.getElementById('portal-logout').hidden=!status.authenticated;
        document.getElementById('portal-entry-tabs').hidden=!!status.authenticated;
        document.getElementById('portal-auth-mode').innerHTML='<option value="login">Entrar</option><option value="create">Criar</option><option value="link">Vincular</option>';
        box.classList.toggle('portal-provider-simple',!status.authenticated);
        if(status.authenticated){
            document.getElementById('portal-auth-mode').value='link';
            box.hidden=inTelegram||status.google_linked;box.open=new URLSearchParams(location.search).has('conta');
            document.getElementById('portal-account-summary').textContent='Vincular Google ou Telegram à conta';
            document.getElementById('portal-auth-state').textContent=`Conta ${status.display_name||status.username} · Google: ${status.google_linked?'vinculado':'não vinculado'} · Telegram: ${status.telegram_linked?'vinculado':'não vinculado'}`;
        }else window.portalScreen(screen);
        const telegram=window.Telegram?.WebApp?.initData;
        document.getElementById('portal-telegram').hidden=!telegram;
        document.getElementById('portal-google-note').textContent=(inTelegram||status.google_client_id)?'':'Login Google aguardando configuração. Contas existentes podem entrar com senha; novas contas podem ser criadas pelo Telegram.';
        document.getElementById('portal-google').hidden=inTelegram;
        if(!inTelegram&&status.google_client_id&&!googleLoaded){
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
        if(provider==='telegram'&&mode==='create'){
            credentials.username=document.getElementById('telegram-username').value.trim();
            credentials.password=document.getElementById('telegram-password').value;
            if(!/^[a-zA-Z0-9_]{3,24}$/.test(credentials.username)||credentials.password.length<6||credentials.password!==document.getElementById('telegram-password-confirm').value){note('Preencha um usuário válido e confirme uma senha de pelo menos 6 caracteres.');return;}
        }
        busy=true;note('Validando identidade…');
        try{
            const result=await post('/api/auth/'+provider,{mode,...credentials});
            document.getElementById('telegram-password').value='';document.getElementById('telegram-password-confirm').value='';
            await window.portalRefresh();window.portalAccept(result);
            if(!(result.personagens||[]).length)window.mostrarCriacao();
            note(mode==='link'?'Vinculação concluída. Seus personagens continuam na mesma conta.':'Conta conectada. Escolha seu personagem.');
        }catch(error){note(error.message);}finally{busy=false;}
    }
    window.portalScreen=next=>{
        screen=next;
        const create=next==='create',provider=next==='google'||create;
        document.getElementById('telegram-credentials').hidden=!(inTelegram&&create);
        document.getElementById('telegram-save-credentials').hidden=true;
        document.getElementById('titulo-caixa').textContent=create?(inTelegram?'CRIAR SUA CONTA':'CONFIRME SUA IDENTIDADE'):'ENTRAR NO REINO';
        document.getElementById('tela-login').style.display=provider?'none':'block';
        document.getElementById('tela-registro-conta').style.display='none';
        document.getElementById('portal-auth-mode').value=create?'create':'login';
        box.hidden=!provider;box.open=true;
        document.getElementById('portal-account-summary').textContent=create?(inTelegram?'Criar conta pelo Telegram':'Criar conta com Google'):(inTelegram?'Entrar pelo Telegram':'Entrar com Google');
        document.getElementById('portal-auth-state').textContent=create&&inTelegram?'Defina seu usuário e senha e confirme pelo Telegram.':create?'Confirme sua identidade e crie seu personagem. Não é necessário criar outra senha.':'Use a identidade já vinculada à sua conta Eldora.';
        document.querySelectorAll('#portal-entry-tabs button').forEach((el,index)=>el.setAttribute('aria-pressed',String(create?index===1:index===0)));
    };
    document.getElementById('telegram-save-credentials').onclick=async()=>{
        if(busy)return;
        const message=document.getElementById('telegram-credentials-message');
        const password=document.getElementById('telegram-password').value;
        if(password!==document.getElementById('telegram-password-confirm').value){message.textContent='As senhas não conferem.';return;}
        busy=true;
        try{
            await post('/api/auth/telegram-credentials',{username:document.getElementById('telegram-username').value,password,init_data:window.Telegram?.WebApp?.initData||''});
            document.getElementById('telegram-password').value='';document.getElementById('telegram-password-confirm').value='';
            await window.portalRefresh();window.mostrarAviso('Acesso salvo','Seu usuário e senha foram configurados. Seus personagens continuam na mesma conta.');
        }catch(e){message.textContent=e.message;}finally{busy=false;}
    };
    document.getElementById('portal-telegram').onclick=()=>authenticate('telegram',{init_data:window.Telegram?.WebApp?.initData||''});
    document.getElementById('portal-logout').onclick=async()=>{try{await post('/api/auth/logout',{});location.reload();}catch(e){note(e.message);}};
    window.portalSelect=id=>post('/api/auth/select',{character_id:id});
    // Remove cópias antigas de senhas, preservando os dados dos personagens no servidor.
    localStorage.removeItem('eldora_contas_salvas');
    window.portalAuthReady=window.portalRefresh().then(data=>{
        document.getElementById('tela-registro-conta').style.display='none';
        if(data.authenticated)window.portalAccept(data);
        else window.portalScreen(inTelegram?'login':'google');
    }).catch(error=>note(error.message));
})();
