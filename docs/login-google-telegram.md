# Entrada e vinculação de identidades — primeira etapa

## Configuração

Instalar requirements.txt no ambiente do servidor. O Client ID público fornecido pelo proprietário já está configurado como padrão em modules/portal_auth.py. GOOGLE_CLIENT_ID pode sobrescrever esse padrão; uma variável explicitamente vazia desativa Google. Não usa Client Secret nem Gmail API.

Registrar a origem HTTPS exata do jogo no Google Auth Platform (aplicativo Web). Este fluxo usa popup com callback JavaScript, sem rota de redirecionamento Google. Configurar público e informações de marca, além de usuários de teste quando aplicável. O login só ficará disponível após configurar o Client ID e reiniciar o backend.

FLASK_SECRET_KEY continua obrigatória e deve ser secreta e estável. Cookies HttpOnly, SameSite=Lax, Secure por padrão e validade de sete dias. Somente em desenvolvimento HTTP local, usar ELDORA_COOKIE_SECURE=0; manter 1 na produção HTTPS. A sessão é assinada pelo Flask; `session_version` permite invalidar sessões antigas ao remover um provedor ou encerrar os outros dispositivos, sem manter uma lista de sessões por aparelho.

## Fluxos

- Conta antiga: entrar com usuário/senha para estabelecer sessão; vincular ou trocar Google/Telegram no painel Conta Eldora. A senha continua funcionando depois de vincular Google.
- Conta nova: selecionar explicitamente Criar nova conta e validar Google ou Telegram. Cadastro antigo sem validação retorna 403.
- Telegram: apenas initData assinado pelo bot, com validade máxima de 10 minutos. Reabrir pelo bot se expirado. Não confia em initDataUnsafe ou telegram_id histórico do banco. Contas antigas não são adotadas por esse ID: autenticar com a senha antes de vincular.
- Google: token validado com google-auth (assinatura, audiência, expiração, emissor e e-mail verificado), identidade pelo sub. Não une contas por e-mail.
- Vinculação exige sessão autenticada há no máximo 10 minutos e identidade ainda livre. Sem transferência de personagem ou fusão de contas. Índices únicos parciais para google_sub e telegram_verified_id.
- Perfil contém acesso a Conta. Vinculação também está disponível na seleção de personagens.
- Criação/listagem/seleção de personagens no portal usa a conta da sessão; não aceita o nome da conta enviado no corpo como autoridade. Novos personagens recebem `conta_mestre_id` (ObjectId); personagens antigos continuam sendo localizados pelo nome legado e recebem o ID imutável quando selecionados.
- As APIs HTTP que identificam o personagem por `user_id`, `char_id`, `jogador_id`, `player_id`, `character_id`, `personagem_id`, `id_personagem` ou `id_jogador` exigem que o ID seja o personagem escolhido na sessão. Isso também protege `/api/personagem/<personagem_id>`, que lê dados do personagem e pode corrigir habilidades antigas. A entrada no mapa valida a conta e o personagem; as ações Socket.IO usam o registro criado nessa validação. Aceitar amizade, grupo ou duelo exige convite emitido pelo servidor, ligado aos dois sockets e personagens, de uso único e com validade limitada. Logout, nova autenticação e troca de personagem desconectam os sockets da conta.
- Senhas antigas salvas em localStorage são removidas ao abrir o portal. Senhas existentes no banco permanecem com hash, e os personagens são preservados.

## Publicação e testes

Esta alteração precisa do backend, templates e JS juntos, além das novas dependências. Sem GOOGLE_CLIENT_ID, o botão Google fica indisponível: contas antigas usam senha e contas novas precisam do Telegram validado. Cadastros novos pelo navegador sem Telegram dependem da configuração do Google.

`venv/Scripts/python.exe tools/check_portal_auth.py` testa isoladamente assinatura Telegram, expiração, CSRF, propriedade e migração de personagem, cadastro, senha alternativa, login por senha após vincular Google, troca/remoção de provedor, revogação de sessão e conflitos. Não acessa Mongo nem contas reais. Ainda falta testar com o Client ID real, Google em navegador e Telegram WebApp real (inclusive restrições de popup/webview).

## Limites e próxima etapa

Auditoria da prioridade 2: os aliases de identidade HTTP foram revisados; o identificador `personagem_id` agora também é vinculado à sessão. Os eventos de aceite de amizade, grupo e duelo não confiam mais em IDs enviados pelo cliente sem convite pendente. Esta verificação cobre a identidade de conta nessas rotas e eventos, não é uma auditoria completa de todas as regras de jogo. Presença, missões de convite persistentes e pagamentos ainda não implementados nesta entrega.

Limite de tentativas persistido por IP em janelas de 15 minutos (30 tentativas), expiração TTL. Atrás de proxy, verificar a configuração confiável de endereço remoto; não confiar diretamente em X-Forwarded-For informado pelo cliente. Várias identidades Google/Telegram não garantem pessoas distintas.

Origem principal informada: `https://eldora-rpg.modappmania.workers.dev`. O proxy deve preservar cookies de sessão e não armazenar em cache `/api/auth/*` nem respostas de login. Não foi feita publicação remota nesta configuração.

## Fluxo atual — sem senha adicional

Conta nova: confirma Google (navegador) ou Telegram (Mini App), recebe identificador interno e vai à criação do personagem. Não pede nome de conta nem senha. A rota temporária /api/auth/register foi removida.

Conta Google sem senha: depois de entrar, pode configurar usuário e senha como acesso alternativo. A criação ou troca exige uma autenticação recente; quem entrou por senha também confirma a senha atual. Contas antigas já vinculadas ao Google continuam aceitando a senha previamente cadastrada.

O Mini App não executa Google Identity Services dentro do WebView. Para entrar com uma conta Google já vinculada, o botão abre o navegador seguro; após a validação, um código aleatório de uso único e validade de 10 minutos retorna pelo bot e cria a sessão no Mini App. O botão de retorno passa o código pela query da URL do Web App, e o portal o remove do endereço antes de enviá-lo à API. O código fica associado ao usuário Telegram que iniciou o retorno e só é consumido atomicamente após validar o `initData` assinado. Se o Google ainda não estiver vinculado, o login retorna erro e não cria nem une contas. Entrar com usuário e senha não vincula automaticamente a identidade Telegram; o login nativo só entra na conta que já pertence àquele Telegram verificado. Nunca adota telegram_id legado sem essa prova.

O retorno usa `TELEGRAM_BOT_USERNAME` (padrão `Eldora_rpg_bot`) e exige que o handler `/start` do bot esteja publicado junto com as rotas e o JavaScript do portal. Depois da autenticação Google, a pessoa toca em “Voltar ao jogo” na mensagem do bot para abrir o Mini App na conta correta.

O painel de acessos mostra os provedores vinculados. Para remover um provedor, a sessão precisa ter sido autenticada recentemente por outro método que continuará ativo; o último método de entrada nunca pode ser removido. Trocar Google/Telegram também exige outro método e a prova da nova identidade. Encerrar sessões de outros dispositivos incrementa a versão da conta e desconecta os sockets ativos.

## Correção: credenciais próprias para contas Telegram

Cadastro novo pelo Telegram exige usuário e senha (com confirmação na interface) antes de criar personagem. A assinatura Telegram continua validada no servidor. Google permanece sem senha adicional. O usuário escolhido fica em login_alias, com índice único, sem alterar a chave interna username que liga os personagens. Login por senha aceita esse alias no navegador mesmo sem Telegram, para contas ainda sem Google vinculado.

Contas antigas sem senha mostram um formulário para adicionar usuário e senha; contas com senha podem atualizá-la depois de reautenticar. Reinstalar Telegram mantendo a mesma identidade não cria outra conta. Sem uma senha alternativa ou outro provedor vinculado, perder acesso ao único provedor ainda exige suporte manual; o jogo não tem recuperação automática por e-mail.

## Ajustes do fluxo de entrada

No Mini App, Entrar oferece tanto acesso direto pela identidade Telegram validada quanto usuário e senha como recuperação. Criar conta pelo Telegram exige usuário e senha com pelo menos seis caracteres na senha; nomes numéricos de seis dígitos continuam válidos. No navegador, a conta antiga aceita login por username ou login_alias, e a nova conta Google segue direto para criação do personagem. A aba Entrar abre o formulário de senha; Criar conta abre o cadastro do provedor.

Manter minha conta conectada controla a duração do cookie de sessão do servidor. O navegador pode lembrar apenas o nome do usuário; senhas locais antigas são apagadas e nunca são gravadas novamente. A opção Mostrar senha e os controles de som funcionam mesmo quando o armazenamento local está indisponível.
