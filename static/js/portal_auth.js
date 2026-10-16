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
        document.getElementById('telegram-credentials').hidden=!status.authenticated;
        document.getElementById('telegram-save-credentials').hidden=!status.authenticated;
        document.getElementById('telegram-save-credentials').disabled=!status.fresh_auth;
        document.getElementById('telegram-save-credentials').textContent=status.has_password?'Atualizar acesso por senha':'Adicionar acesso por senha';
        document.getElementById('telegram-username').value=status.login_alias||'';
        document.getElementById('account-current-password-container').hidden=!(status.has_password&&status.auth_method==='password');
        document.getElementById('telegram-credentials-message').textContent=status.authenticated&&!status.fresh_auth?'Saia e entre novamente para confirmar sua identidade antes de alterar uma senha.':(status.has_password?'A senha já cadastrada continua válida como alternativa ao Google ou Telegram.':'');
        document.getElementById('portal-logout').hidden=!status.authenticated;
        document.getElementById('portal-entry-tabs').hidden=!!status.authenticated;
        document.getElementById('portal-auth-mode').innerHTML='<option value="login">Entrar</option><option value="create">Criar</option><option value="link">Vincular</option><option value="replace">Trocar</option>';
        box.classList.toggle('portal-provider-simple',!status.authenticated);
        const actions=document.getElementById('portal-account-actions');
        if(status.authenticated){
            document.getElementById('portal-auth-mode').value='link';
            box.hidden=false;
            actions.hidden=false;
            document.getElementById('portal-unlink-google').hidden=!status.google_linked;
            document.getElementById('portal-unlink-google').disabled=!status.can_unlink_google||status.auth_method==='google';
            document.getElementById('portal-unlink-telegram').hidden=!status.telegram_linked;
            document.getElementById('portal-unlink-telegram').disabled=!status.can_unlink_telegram||status.auth_method==='telegram';
            document.getElementById('portal-replace-google').hidden=!(status.google_linked&&status.can_unlink_google);
            document.getElementById('portal-replace-google').disabled=!status.fresh_auth||status.auth_method==='google';
            document.getElementById('portal-replace-telegram').hidden=!(inTelegram&&status.telegram_linked&&status.can_unlink_telegram);
            document.getElementById('portal-replace-telegram').disabled=!status.fresh_auth||status.auth_method==='telegram';
            document.getElementById('portal-account-summary').textContent='⚙️ Conta e segurança';
            document.getElementById('portal-auth-state').textContent=`Conta ${status.display_name||status.username} · Google: ${status.google_linked?'vinculado':'não vinculado'} · Telegram: ${status.telegram_linked?'vinculado':'não vinculado'}`;
            document.getElementById('portal-account-security-note').textContent=status.auth_method==='unknown'?'Para remover ou trocar um provedor, entre novamente usando outro acesso da conta.':'';
        }else{
            actions.hidden=true;
            window.portalScreen(screen);
        }
        const telegram=window.Telegram?.WebApp?.initData;
        const telegramActionVisible=!!telegram&&(!status.authenticated||!status.telegram_linked);
        document.getElementById('portal-telegram').hidden=!telegramActionVisible;
        document.getElementById('portal-telegram').textContent=status.authenticated?'Vincular Telegram a esta conta':(screen==='create'?'Criar conta pelo Telegram':'Entrar com Telegram');
        document.getElementById('portal-telegram-hint').hidden=!(telegram&&!status.authenticated);
        document.getElementById('portal-google-note').textContent=(inTelegram||status.google_client_id)?'':'Login Google aguardando configuração. Contas existentes podem entrar com senha; novas contas podem ser criadas pelo Telegram.';
        const providerMode=document.getElementById('portal-auth-mode').value;
        document.getElementById('portal-google').hidden=inTelegram||!!(status.authenticated&&status.google_linked&&providerMode!=='replace');
        if(status.authenticated&&status.google_linked&&providerMode==='replace'){
            document.getElementById('portal-google-note').textContent='Clique no botão Google para confirmar a nova conta. Os personagens continuam nesta conta Eldora.';
        }
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
        if(provider==='telegram'&&mode==='create'){
            credentials.username=document.getElementById('telegram-username').value.trim();
            credentials.password=document.getElementById('telegram-password').value;
            if(!/^[a-zA-Z0-9_]{3,24}$/.test(credentials.username)||credentials.username.toLowerCase().startsWith('eldora_')||credentials.password.length<6||credentials.password!==document.getElementById('telegram-password-confirm').value){note('Use um usuário de 3 a 24 caracteres (sem o prefixo reservado eldora_) e confirme uma senha de pelo menos 6 caracteres.');return;}
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
        note('');
        const create=next==='create',provider=next==='google'||create;
        document.getElementById('telegram-credentials').hidden=!(inTelegram&&create);
        document.getElementById('telegram-save-credentials').hidden=true;
        document.getElementById('titulo-caixa').textContent=create?(inTelegram?'CRIAR SUA CONTA':'CONFIRME SUA IDENTIDADE'):'ENTRAR NO REINO';
        document.getElementById('tela-login').style.display=provider?'none':'block';
        document.getElementById('tela-registro-conta').style.display='none';
        document.getElementById('portal-auth-mode').value=create?'create':'login';
        document.getElementById('portal-account-actions').hidden=true;
        box.hidden=!provider;box.open=true;
        document.getElementById('portal-account-summary').textContent=create?(inTelegram?'Criar conta pelo Telegram':'Criar conta com Google'):(inTelegram?'Entrar pelo Telegram':'Entrar com Google');
        document.getElementById('portal-auth-state').textContent=create&&inTelegram?'Defina seu usuário e senha e confirme pelo Telegram.':create?'Confirme sua identidade e crie seu personagem. Não é necessário criar outra senha.':'Use a identidade já vinculada à sua conta Eldora.';
        const telegramButton=document.getElementById('portal-telegram');
        const telegramHint=document.getElementById('portal-telegram-hint');
        telegramButton.hidden=!(inTelegram&&!status?.authenticated);
        telegramButton.textContent=create?'Criar conta pelo Telegram':'Entrar com Telegram';
        telegramHint.hidden=!(inTelegram&&!status?.authenticated);
        telegramHint.textContent=create?'Depois de preencher usuário e senha, confirme a criação pelo Telegram.':'Entre automaticamente com a identidade Telegram deste aplicativo.';
        document.querySelectorAll('#portal-entry-tabs button').forEach((el,index)=>el.setAttribute('aria-pressed',String(create?index===1:index===0)));
    };
    document.getElementById('telegram-save-credentials').onclick=async()=>{
        if(busy)return;
        const message=document.getElementById('telegram-credentials-message');
        const password=document.getElementById('telegram-password').value;
        if(password!==document.getElementById('telegram-password-confirm').value){message.textContent='As senhas não conferem.';return;}
        busy=true;
        try{
            await post('/api/auth/credentials',{username:document.getElementById('telegram-username').value,password,current_password:document.getElementById('account-current-password').value});
            document.getElementById('telegram-password').value='';document.getElementById('telegram-password-confirm').value='';
            document.getElementById('account-current-password').value='';
            await window.portalRefresh();window.mostrarAviso('Acesso alternativo criado','Seu usuário e senha agora entram na mesma conta e preservam seus personagens.');
        }catch(e){message.textContent=e.message;}finally{busy=false;}
    };
    async function unlink(provider){
        if(busy)return;
        busy=true;
        try{
            await post('/api/auth/unlink/'+provider,{});
            await window.portalRefresh();
            note('Vínculo removido. Seus personagens continuam na mesma conta.');
        }catch(e){note(e.message);}finally{busy=false;}
    }
    document.getElementById('portal-unlink-google').onclick=()=>unlink('google');
    document.getElementById('portal-unlink-telegram').onclick=()=>unlink('telegram');
    document.getElementById('portal-logout-all').onclick=async()=>{
        if(busy||!window.confirm('Encerrar a conta em todos os dispositivos? Você precisará entrar novamente.'))return;
        busy=true;
        try{await post('/api/auth/logout-all',{});location.href='/login';}
        catch(e){note(e.message);}finally{busy=false;}
    };
    document.getElementById('portal-replace-google').onclick=()=>{
        if(!status?.fresh_auth){note('Saia e entre novamente por senha ou Telegram antes de trocar o Google.');return;}
        document.getElementById('portal-auth-mode').value='replace';
        document.getElementById('portal-google').hidden=inTelegram;
        document.getElementById('portal-google-note').textContent='Clique no botão Google para confirmar a nova conta. Os personagens permanecem nesta conta.';
    };
    document.getElementById('portal-replace-telegram').onclick=()=>{
        if(!status?.fresh_auth){note('Saia e entre novamente por senha ou Google antes de trocar o Telegram.');return;}
        document.getElementById('portal-auth-mode').value='replace';
        document.getElementById('portal-telegram').hidden=false;
        document.getElementById('portal-telegram').textContent='Confirmar nova conta Telegram';
        document.getElementById('portal-account-security-note').textContent='Toque em “Confirmar nova conta Telegram” para validar a identidade que substituirá o vínculo.';
    };
    document.getElementById('portal-telegram').onclick=()=>authenticate('telegram',{init_data:window.Telegram?.WebApp?.initData||''});
    document.getElementById('portal-logout').onclick=async()=>{try{await post('/api/auth/logout',{});location.reload();}catch(e){note(e.message);}};
    window.portalSelect=id=>post('/api/auth/select',{character_id:id});
    // Remove cópias antigas de senhas, preservando os dados dos personagens no servidor.
    try{localStorage.removeItem('eldora_contas_salvas');}catch(_){}
    window.portalAuthReady=window.portalRefresh().then(data=>{
        document.getElementById('tela-registro-conta').style.display='none';
        if(data.authenticated)window.portalAccept(data);
        else window.portalScreen(inTelegram?'login':'google');
    }).catch(error=>note(error.message));
})();
