# Entrada e vinculação de identidades — primeira etapa

## Configuração

Instalar requirements.txt no ambiente do servidor. O Client ID público fornecido pelo proprietário já está configurado como padrão em modules/portal_auth.py. GOOGLE_CLIENT_ID pode sobrescrever esse padrão; uma variável explicitamente vazia desativa Google. Não usa Client Secret nem Gmail API.

Registrar a origem HTTPS exata do jogo no Google Auth Platform (aplicativo Web). Este fluxo usa popup com callback JavaScript, sem rota de redirecionamento Google. Configurar público e informações de marca, além de usuários de teste quando aplicável. O login só ficará disponível após configurar o Client ID e reiniciar o backend.

FLASK_SECRET_KEY continua obrigatória e deve ser secreta e estável. Cookies HttpOnly, SameSite=Lax, Secure por padrão e validade de sete dias. Somente em desenvolvimento HTTP local, usar ELDORA_COOKIE_SECURE=0; manter 1 na produção HTTPS. Sessão assinada do Flask: não é um cadastro central de sessões revogáveis.

## Fluxos

- Conta antiga: entrar com usuário/senha para estabelecer sessão; vincular Google ou Telegram no painel Conta Eldora.
- Conta nova: selecionar explicitamente Criar nova conta e validar Google ou Telegram. Cadastro antigo sem validação retorna 403.
- Telegram: apenas initData assinado pelo bot, com validade máxima de 10 minutos. Reabrir pelo bot se expirado. Não confia em initDataUnsafe ou telegram_id histórico do banco. Contas antigas não são adotadas por esse ID: autenticar com a senha antes de vincular.
- Google: token validado com google-auth (assinatura, audiência, expiração, emissor e e-mail verificado), identidade pelo sub. Não une contas por e-mail.
- Vinculação exige sessão autenticada há no máximo 10 minutos e identidade ainda livre. Sem transferência de personagem ou fusão de contas. Índices únicos parciais para google_sub e telegram_verified_id.
- Perfil contém acesso a Conta. Vinculação também está disponível na seleção de personagens.
- Criação/listagem/seleção de personagens no portal usa a conta da sessão; não aceita o nome da conta enviado no corpo como autoridade.
- Senhas antigas salvas em localStorage são removidas ao abrir o portal. Senhas existentes no banco permanecem com hash, e os personagens são preservados.

## Publicação e testes

Esta alteração precisa do backend, templates e JS juntos, além das novas dependências. Sem GOOGLE_CLIENT_ID, o botão Google fica indisponível: contas antigas usam senha e contas novas precisam do Telegram validado. Cadastros novos pelo navegador sem Telegram dependem da configuração do Google.

`venv/Scripts/python.exe tools/check_portal_auth.py` testa isoladamente assinatura Telegram, expiração, CSRF, propriedade do personagem, vínculo e conflitos. Não acessa Mongo nem contas reais. Ainda falta testar com o Client ID real, Google em navegador e Telegram WebApp real (inclusive restrições de popup/webview).

## Limites e próxima etapa

Esta entrega protege o portal de autenticação e a vinculação. Endpoints legados de jogo e Socket.IO que ainda aceitam user_id precisam de migração para identidade da sessão antes de habilitar convites com gemas. Não considera o jogo inteiro protegido apenas pela adição deste login. Presença, missões de convite e pagamentos ainda não implementados nesta entrega.

Limite de tentativas persistido por IP em janelas de 15 minutos (30 tentativas), expiração TTL. Atrás de proxy, verificar a configuração confiável de endereço remoto; não confiar diretamente em X-Forwarded-For informado pelo cliente. Várias identidades Google/Telegram não garantem pessoas distintas.

Origem principal informada: `https://eldora-rpg.modappmania.workers.dev`. O proxy deve preservar cookies de sessão e não armazenar em cache `/api/auth/*` nem respostas de login. Não foi feita publicação remota nesta configuração.

## Fluxo atual — sem senha adicional

Conta nova: confirma Google (navegador) ou Telegram (Mini App), recebe identificador interno e vai à criação do personagem. Não pede nome de conta nem senha. A rota temporária /api/auth/register foi removida.

Conta antiga sem Google: pode entrar com usuário/senha e vincular Google depois. Ao vincular, acesso posterior por senha é recusado no servidor; o hash antigo é preservado, sem ser usado para liberar acesso web. Google e Telegram verificado continuam válidos.

Dentro do Telegram não carrega Google Identity Services nem mostra botão Google. Ao entrar por senha em conta antiga ainda sem Google, initData validado pode vincular esse Telegram, desde que não pertença a outra conta. Nunca adota telegram_id legado sem essa prova. Contas já vinculadas ao Google devem usar Google no navegador ou Telegram previamente verificado; não une contas automaticamente.

Painel de vinculação some após vincular Google. Sair / trocar conta permanece visível. Sessões anteriormente abertas mantêm sua validade até sair/expirar.

## Correção: credenciais próprias para contas Telegram

Cadastro novo pelo Telegram exige usuário e senha (com confirmação na interface) antes de criar personagem. A assinatura Telegram continua validada no servidor. Google permanece sem senha adicional. O usuário escolhido fica em login_alias, com índice único, sem alterar a chave interna username que liga os personagens. Login por senha aceita esse alias no navegador mesmo sem Telegram, para contas ainda sem Google vinculado.

Contas Telegram criadas anteriormente sem senha mostram formulário para Salvar meu acesso. Endpoint exige sessão, CSRF e prova Telegram assinada correspondente à conta. Só configura credenciais ausentes; não substitui senhas existentes. Reinstalar Telegram mantendo a mesma identidade não cria outra conta. Perder acesso ao Telegram antes de configurar credenciais ainda exige recuperação da conta; esta mudança não recupera automaticamente um número perdido.
