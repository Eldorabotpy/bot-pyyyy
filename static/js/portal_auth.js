(() => {
    const inTelegram=!!window.Telegram?.WebApp?.initData;
    const googleHandoffState=new URLSearchParams(window.location.search).get('google_handoff')||'';
    const googleHandoffMode=googleHandoffState==='1';
    const googleHandoffReturn=googleHandoffState==='return';
    const googleHandoffError=googleHandoffState==='error';
    const queryHandoffToken=new URLSearchParams(window.location.search).get('google_handoff_token')||'';
    const handoffParams=new URLSearchParams(window.location.hash.slice(1));
    const handoffToken=handoffParams.get('google_handoff')||'';
    if(queryHandoffToken){
        const cleanUrl=new URL(window.location.href);
        cleanUrl.searchParams.delete('google_handoff_token');
        history.replaceState(null,'',cleanUrl.pathname+cleanUrl.search+cleanUrl.hash);
    }
    if(handoffToken)history.replaceState(null,'',window.location.pathname+window.location.search);
    let status=null,busy=false,googleLoaded=false,googleReady=false,screen='login';
    const box=document.getElementById('portal-identidade');
    const linksTrigger=document.getElementById('portal-links-trigger');
    const linksDrawer=document.getElementById('portal-links-drawer');
    const linksOverlay=document.getElementById('portal-links-overlay');
    const confirmOverlay=document.getElementById('portal-confirm-overlay');
    const confirmDialog=document.getElementById('portal-confirm-dialog');
    let resolveConfirm=null,focusBeforeConfirm=null;
    const accountHome=document.getElementById('portal-account-home');
    const accountSettingsSlot=document.getElementById('portal-account-settings-slot');
    const googleControls=document.getElementById('portal-google-controls');
    const googleHome=document.getElementById('portal-google-home');
    const googleExternalButton=document.getElementById('portal-google-external');
    const telegramButton=document.getElementById('portal-telegram');
    const telegramHome=document.getElementById('portal-telegram-home');
    function renderGoogleButton(){
        const target=document.getElementById('portal-google');
        if(!googleReady||inTelegram||!target||!target.getClientRects().length)return;
        const mode=document.getElementById('portal-auth-mode').value;
        if(status?.authenticated&&status.google_linked&&mode!=='replace')return;
        if(!status?.authenticated&&!['google','create'].includes(screen))return;
        target.replaceChildren();
        google.accounts.id.renderButton(target,{type:'standard',theme:'outline',size:'large',text:!status?.authenticated&&screen==='create'?'signup_with':'signin_with',width:240});
    }
    function setLinksMenu(open,returnFocus=true){
        linksDrawer.hidden=!open;
        linksOverlay.hidden=!open;
        linksTrigger.setAttribute('aria-expanded',String(open));
        document.body.classList.toggle('portal-links-open',open);
        if(open)document.getElementById('portal-links-close').focus();
        else if(returnFocus&&!linksTrigger.hidden)linksTrigger.focus();
    }
    function finishConfirm(accepted){
        if(!resolveConfirm)return;
        confirmOverlay.hidden=true;
        document.body.classList.remove('portal-confirm-open');
        const resolve=resolveConfirm,restore=focusBeforeConfirm;
        resolveConfirm=null;focusBeforeConfirm=null;
        if(restore?.isConnected)restore.focus();
        resolve(accepted);
    }
    function confirmAction({title,message,confirmText='Confirmar',danger=false}){
        if(resolveConfirm)return Promise.resolve(false);
        return new Promise(resolve=>{
            resolveConfirm=resolve;
            focusBeforeConfirm=document.activeElement;
            document.getElementById('portal-confirm-title').textContent=title;
            document.getElementById('portal-confirm-message').textContent=message;
            document.getElementById('portal-confirm-accept').textContent=confirmText;
            confirmDialog.dataset.variant=danger?'danger':'normal';
            confirmOverlay.hidden=false;
            document.body.classList.add('portal-confirm-open');
            document.getElementById('portal-confirm-cancel').focus();
        });
    }
    const note=text=>{
        document.getElementById(status?.authenticated?'portal-links-message':'portal-auth-message').textContent=text;
    };
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
        const wasAuthenticated=!!status?.authenticated;
        status=await response.json();
        if(status.authenticated&&!wasAuthenticated)box.open=false;
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
        (status.authenticated?accountSettingsSlot:accountHome).appendChild(box);
        const googleSlot=document.getElementById('portal-google-slot');
        const telegramSlot=document.getElementById('portal-telegram-slot');
        (status.authenticated?googleSlot:googleHome).appendChild(googleControls);
        (status.authenticated?telegramSlot:telegramHome).appendChild(telegramButton);
        linksTrigger.hidden=!status.authenticated;
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
            document.getElementById('portal-account-summary').textContent='Acesso por senha';
            document.getElementById('portal-auth-state').textContent=`Conta ${status.display_name||status.username} · Google: ${status.google_linked?'vinculado':'não vinculado'} · Telegram: ${status.telegram_linked?'vinculado':'não vinculado'}`;
            document.getElementById('portal-links-account').textContent=`Conta ${status.display_name||status.username}`;
            const googleState=document.getElementById('portal-google-link-state');
            googleState.textContent=status.google_linked?'Vinculado a esta conta':'Ainda não vinculado';
            googleState.dataset.linked=String(!!status.google_linked);
            const telegramState=document.getElementById('portal-telegram-link-state');
            telegramState.textContent=status.telegram_linked?'Vinculado a esta conta':'Ainda não vinculado';
            telegramState.dataset.linked=String(!!status.telegram_linked);
            document.getElementById('portal-account-security-note').textContent=
                (status.auth_method==='unknown'?'Para trocar um provedor, entre novamente usando outro acesso da conta. ':'')+
                'Remover um vínculo libera aquele provedor para outra conta; os personagens permanecem nesta conta-mestre.';
        }else{
            actions.hidden=true;
            setLinksMenu(false,false);
            window.portalScreen(screen);
        }
        const telegram=window.Telegram?.WebApp?.initData;
        const telegramActionVisible=!!telegram&&(!status.authenticated||!status.telegram_linked);
        document.getElementById('portal-telegram').hidden=!telegramActionVisible;
        document.getElementById('portal-telegram').textContent=status.authenticated?'Vincular Telegram a esta conta':(screen==='create'?'Criar conta pelo Telegram':'Entrar com Telegram');
        document.getElementById('portal-telegram-hint').hidden=!(telegram&&!status.authenticated);
        const googleNote=document.getElementById('portal-google-note');
        googleNote.classList.toggle('portal-link-hint',!!(status.authenticated&&!status.google_linked));
        googleNote.textContent=status.authenticated&&!status.google_linked
            ?(inTelegram
                ?'O Google ainda não está vinculado a esta conta-mestre. Abra o Eldora no navegador e entre nesta mesma conta para conectar o Google; seus personagens permanecem aqui.'
                :'O Google ainda não está vinculado a esta conta-mestre. Selecione sua conta Google abaixo para vinculá-la a esta conta; seus personagens permanecem aqui.')
            :inTelegram
                ?(status.google_client_id?'Entre com o Google já vinculado. A confirmação abre o navegador; depois toque em “Voltar ao jogo” na mensagem do bot.':'Login Google ainda não configurado no servidor.')
                :status.google_client_id?'':'Login Google aguardando configuração. Contas existentes podem entrar com senha; novas contas podem ser criadas pelo Telegram.';
        const providerMode=document.getElementById('portal-auth-mode').value;
        document.getElementById('portal-google').hidden=inTelegram||!!(status.authenticated&&status.google_linked&&providerMode!=='replace');
        googleExternalButton.hidden=!(inTelegram&&!status.authenticated&&!!status.google_client_id&&screen==='google');
        if(status.authenticated&&status.google_linked&&providerMode==='replace'){
            googleNote.classList.remove('portal-link-hint');
            document.getElementById('portal-google-note').textContent='Clique no botão Google para confirmar a nova conta. Os personagens continuam nesta conta Eldora.';
        }
        if(!inTelegram&&status.google_client_id&&!googleLoaded){
            googleLoaded=true;
            const script=document.createElement('script');script.src='https://accounts.google.com/gsi/client';script.async=true;
            script.onload=()=>{
                try{
                    google.accounts.id.initialize({client_id:status.google_client_id,callback:r=>authenticate('google',{credential:r.credential})});
                    googleReady=true;
                    renderGoogleButton();
                }catch(error){
                    googleLoaded=false;
                    googleNote.textContent='Não foi possível preparar o acesso com Google. Atualize a página e tente novamente.';
                }
            };
            script.onerror=()=>{googleLoaded=false;googleNote.textContent='Não foi possível carregar o acesso do Google. Verifique a conexão e atualize a página.';};
            document.head.appendChild(script);
        }
        renderGoogleButton();
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
        const returnToTelegram=googleHandoffMode&&provider==='google'&&mode==='login'&&!inTelegram;
        busy=true;note('Validando identidade…');
        try{
            const result=await post('/api/auth/'+provider,{mode,...credentials,return_to_telegram:returnToTelegram});
            if(returnToTelegram&&result.telegram_deep_link){
                note('Google confirmado. Voltando ao Telegram…');
                window.location.assign(result.telegram_deep_link);
                return;
            }
            document.getElementById('telegram-password').value='';document.getElementById('telegram-password-confirm').value='';
            const refreshed=await window.portalRefresh();
            if(mode==='link'){
                const linked=provider==='google'?refreshed.google_linked:refreshed.telegram_linked;
                if(!linked)throw new Error('O servidor não confirmou o vínculo. Esta conta continua sem o provedor; tente novamente.');
            }
            window.portalAccept(result);
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
        document.getElementById('titulo-caixa').textContent=create?'CRIAR CONTA-MESTRE':'ENTRAR NO REINO';
        document.getElementById('tela-login').style.display=provider?'none':'block';
        document.getElementById('tela-registro-conta').style.display='none';
        document.getElementById('portal-auth-mode').value=create?'create':'login';
        document.getElementById('portal-account-actions').hidden=true;
        box.hidden=!provider;box.open=true;
        document.getElementById('portal-account-summary').textContent=create?(inTelegram?'Criar conta pelo Telegram':'Criar conta com Google'):(inTelegram?'Entrar com Google ou Telegram':'Entrar com Google');
        document.getElementById('portal-auth-state').textContent=create&&inTelegram
            ?'Isso cria uma nova conta-mestre. Se seus personagens estão em uma conta antiga, entre nela com usuário e senha e vincule o Telegram em Conta Eldora.'
            :create
                ?'Para criar uma conta nova, continue com uma conta Google ainda não vinculada. Se já tem conta ou personagens, entre com senha e vincule o Google nas configurações da conta.'
                :inTelegram
                    ?'Entre com o Google já vinculado. A confirmação acontece no navegador; depois toque em “Voltar ao jogo” na mensagem do bot.'
                    :'Use a identidade já vinculada à sua conta Eldora. Se aparecer “não vinculada”, entre na conta que guarda seus personagens e conecte o Google em Conta Eldora.';
        const telegramButton=document.getElementById('portal-telegram');
        const telegramHint=document.getElementById('portal-telegram-hint');
        googleExternalButton.hidden=!(inTelegram&&!status?.authenticated&&!!status?.google_client_id&&next==='google');
        telegramButton.hidden=!(inTelegram&&!status?.authenticated);
        telegramButton.textContent=create?'Criar conta pelo Telegram':'Entrar com Telegram';
        telegramHint.hidden=!(inTelegram&&!status?.authenticated);
        telegramHint.textContent=create?'Depois de preencher usuário e senha, confirme a criação pelo Telegram.':'Entre automaticamente com a identidade Telegram deste aplicativo.';
        document.querySelectorAll('#portal-entry-tabs button').forEach((el,index)=>el.setAttribute('aria-pressed',String(index===1?create:next==='login')));
        requestAnimationFrame(renderGoogleButton);
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
        const providerName=provider==='google'?'Google':'Telegram';
        const fallback=provider==='google'?'senha ou Telegram':'senha ou Google';
        if(!await confirmAction({title:`Remover vínculo do ${providerName}?`,message:`Seus personagens continuarão nesta conta-mestre. Depois, você poderá entrar por ${fallback}.`,confirmText:'Remover vínculo',danger:true}))return;
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
        if(busy||!await confirmAction({title:'Encerrar todas as sessões?',message:'Isso inclui esta sessão. Seus vínculos e personagens serão mantidos, mas você precisará entrar novamente.',confirmText:'Encerrar sessões',danger:true}))return;
        busy=true;
        try{await post('/api/auth/logout-all',{});location.href='/login';}
        catch(e){note(e.message);}finally{busy=false;}
    };
    document.getElementById('portal-replace-google').onclick=async()=>{
        if(!status?.fresh_auth){note('Saia e entre novamente por senha ou Telegram antes de trocar o Google.');return;}
        if(!await confirmAction({title:'Trocar Google vinculado?',message:'Na próxima etapa, escolha a nova conta Google. Seus personagens permanecem nesta conta-mestre.',confirmText:'Continuar'}))return;
        document.getElementById('portal-auth-mode').value='replace';
        document.getElementById('portal-google').hidden=inTelegram;
        document.getElementById('portal-google-note').textContent='Clique no botão Google para trocar o vínculo desta conta-mestre. Os personagens permanecem aqui.';
        requestAnimationFrame(renderGoogleButton);
    };
    document.getElementById('portal-replace-telegram').onclick=async()=>{
        if(!status?.fresh_auth){note('Saia e entre novamente por senha ou Google antes de trocar o Telegram.');return;}
        if(!await confirmAction({title:'Trocar Telegram vinculado?',message:'Na próxima etapa, confirme a nova conta Telegram. Seus personagens permanecem nesta conta-mestre.',confirmText:'Continuar'}))return;
        document.getElementById('portal-auth-mode').value='replace';
        document.getElementById('portal-telegram').hidden=false;
        document.getElementById('portal-telegram').textContent='Confirmar nova conta Telegram';
        document.getElementById('portal-account-security-note').textContent='Toque em “Confirmar nova conta Telegram” para validar a identidade que substituirá o vínculo.';
    };
    document.getElementById('portal-telegram').onclick=()=>authenticate('telegram',{init_data:window.Telegram?.WebApp?.initData||''});
    googleExternalButton.onclick=()=>{
        const url=new URL('/login?google_handoff=1',window.location.origin).href;
        const webApp=window.Telegram?.WebApp;
        if(typeof webApp?.openLink==='function')webApp.openLink(url);
        else note('Abra esta página no navegador para entrar com Google e retornar ao Telegram.');
    };
    linksTrigger.onclick=()=>setLinksMenu(true);
    document.getElementById('portal-links-close').onclick=()=>setLinksMenu(false);
    linksOverlay.onclick=()=>setLinksMenu(false);
    document.getElementById('portal-confirm-cancel').onclick=()=>finishConfirm(false);
    document.getElementById('portal-confirm-accept').onclick=()=>finishConfirm(true);
    confirmOverlay.onclick=event=>{if(event.target===confirmOverlay)finishConfirm(false);};
    document.addEventListener('keydown',event=>{
        if(!confirmOverlay.hidden){
            if(event.key==='Escape'){finishConfirm(false);return;}
            if(event.key!=='Tab')return;
            const focusable=[...confirmDialog.querySelectorAll('button:not([hidden]):not(:disabled),[href],input:not([hidden]):not(:disabled),select:not([hidden]):not(:disabled),[tabindex]:not([tabindex="-1"])')].filter(element=>element.getClientRects().length);
            if(!focusable.length){event.preventDefault();confirmDialog.focus();return;}
            const first=focusable[0],last=focusable[focusable.length-1];
            if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
            else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
            return;
        }
        if(linksDrawer.hidden)return;
        if(event.key==='Escape'){setLinksMenu(false);return;}
        if(event.key!=='Tab')return;
        const focusable=[...linksDrawer.querySelectorAll('button:not([hidden]):not(:disabled),[href],input:not([hidden]):not(:disabled),select:not([hidden]):not(:disabled),[tabindex]:not([tabindex="-1"])')].filter(element=>element.getClientRects().length);
        if(!focusable.length){event.preventDefault();linksDrawer.focus();return;}
        const first=focusable[0],last=focusable[focusable.length-1];
        if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
        else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
    });
    document.getElementById('portal-logout').onclick=async()=>{
        if(busy||!await confirmAction({title:'Sair desta conta?',message:'Você sairá desta sessão neste dispositivo. Os vínculos e personagens serão mantidos.',confirmText:'Sair da conta',danger:true}))return;
        busy=true;
        try{await post('/api/auth/logout',{});location.reload();}
        catch(e){note(e.message);}finally{busy=false;}
    };
    window.portalSelect=id=>post('/api/auth/select',{character_id:id});
    // Remove cópias antigas de senhas, preservando os dados dos personagens no servidor.
    try{localStorage.removeItem('eldora_contas_salvas');}catch(_){}
    window.portalAuthReady=window.portalRefresh().then(async data=>{
        document.getElementById('tela-registro-conta').style.display='none';
        if(handoffToken||queryHandoffToken||googleHandoffReturn){
            try{
                const payload={init_data:window.Telegram?.WebApp?.initData||''};
                if(handoffToken||queryHandoffToken)payload.token=handoffToken||queryHandoffToken;
                const result=await post('/api/auth/telegram-google-handoff',payload);
                const refreshed=await window.portalRefresh();
                window.portalAccept(result);
                if(!(result.personagens||[]).length)window.mostrarCriacao();
                note('Conta Google conectada. Escolha seu personagem.');
                return refreshed;
            }catch(error){
                window.portalScreen('google');
                document.getElementById('portal-auth-message').textContent=error.message;
                return data;
            }
        }
        if(googleHandoffError){
            window.portalScreen('google');
            document.getElementById('portal-auth-message').textContent='O retorno ao Telegram não foi validado. Inicie novamente a entrada com Google.';
            return data;
        }
        if(data.authenticated&&googleHandoffMode&&data.google_linked){
            try{
                const result=await post('/api/auth/telegram-google-handoff/issue',{});
                window.location.assign(result.telegram_deep_link);
                return data;
            }catch(error){
                window.portalAccept(data);
                window.mostrarAviso('Não foi possível voltar ao Telegram',error.message);
                return data;
            }
        }
        if(data.authenticated){
            window.portalAccept(data);
            if(googleHandoffMode)window.mostrarAviso('Google não vinculado','Entre nesta conta com Google depois de vincular essa identidade em Conta Eldora.');
        }else window.portalScreen(googleHandoffMode?'google':'login');
        return data;
    }).catch(error=>note(error.message));
})();
