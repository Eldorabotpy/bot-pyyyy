# Companheiros — primeira versão

Entrada: Bestiário > Companheiros ou perfil > Equipamentos > Companheiro.

- Conquista de 10 abates concede 1 incubadora de uso único, uma única vez por personagem.
- 50 abates acumulados no Bestiário de uma família concedem um ovo único. Progresso anterior conta; ondas de invasão não contam.
- Famílias: Slime (Defesa), Lobo (Iniciativa), Morcego (Mana máxima).
- Uma incubação por vez; iniciar consome 1 incubadora do estoque de Companheiros. 96.000 pixels = 3.000 blocos de 32px. Cerca de 11 minutos de caminhada contínua a 150px/s; valores iniciais sujeitos a balanceamento.
- Contador usa posições recebidas pelo socket do personagem. Saltos, intervalos longos, coordenadas inválidas e trocas de região não concedem progresso. Limite de velocidade validado pelo servidor; colisões continuam a cargo do mapa Phaser. Isto não é um motor de movimento totalmente autoritativo e não impede um cliente adulterado de fabricar deslocamentos lentos.
- Checkpoint de caminhada a cada segundo e ao sair/trocar de mapa. Reinício abrupto pode perder até um segundo ainda não consolidado, mas preserva ovo e progresso salvo.
- Ao completar a distância, tocar em Chocar entrega o pet. Se não houver pet equipado, ele é equipado automaticamente.
- Um pet ativo: ganha 10 XP e 1 vínculo por abate válido de caça, solo ou como aliado elegível na divisão de recompensas. Sem retirar XP do jogador; poção de XP não multiplica XP do pet. Pets guardados não evoluem.
- Caçar um membro das três famílias com pet equipado concede 1 essência daquela família, registrada na aba Companheiros.
- Nível máximo 25. Cada nível exige 50 × nível atual XP.
- Adulto: nível 10, 50 vitórias de vínculo e 25 essências da família.
- Ancestral: nível 25, 300 vitórias e 100 essências. Especialização escolhida no botão de evolução é definitiva nesta versão.
- Slime: Guardião/Defesa ou Vital/HP. Lobo: Veloz/Iniciativa ou Guardião/Defesa. Morcego: Arcano/Mana ou Veloz/Iniciativa.
- Bônus fixo: 1 + nível//5 + 2×estágio. HP/Mana multiplicam o valor por 3. Bônus é aplicado em get_player_total_stats, não grava atributos permanentes.
- No mapa, o pet equipado usa a imagem da criatura do Bestiário (Slime Verde, Lobo Magro ou Morcego das Minas), com ícone como fallback. Cabe em metade do tamanho do personagem: 24px para herói de 48px, preservando proporção. Segue o trajeto com distância de 32px e reposiciona após teleporte. Imagens ainda não têm animações próprias; visível no mapa do dono nesta versão. O cartão de estoque mostra a imagem da incubadora.

## Persistência e publicação

Coleção Mongo `companions` na mesma base de `users`, chave ObjectId do personagem e revisão otimista. Não há migração destrutiva nem dependência nova. Ovos não são itens negociáveis do inventário. Backup deve incluir a nova coleção.

Subir todos os arquivos alterados/novos e reiniciar o backend. Atualizações do HTML incluem versões de cache dos scripts. Não foi aplicado em produção.

## Verificação

`venv/Scripts/python.exe tools/check_companions.py` executa regressão isolada com armazenamento em memória: requisitos, resgate concorrente, ovo único, incubação persistida, XP, custos/evolução, bônus, limites de movimento e endpoints Flask. Não acessa Mongo real. Conferência visual local com dados fictícios em largura estreita. Ainda é necessário jogar o ciclo no servidor de teste para ajustar distância e balanceamento.

## Correção de caminhada e Códice

O mapa agora envia posições intermediárias a cada 250 ms, além da posição de parada. Antes, somente a parada emitia `mover`, e intervalos maiores que 3 segundos eram descartados pelo validador. A amostragem pertence à cena Phaser. A validação de velocidade e os checkpoints permanecem no servidor. Validado com o handler real em armazenamento isolado: 12 segundos caminhando avançaram 1.788 pixels; posição parada e teleporte não avançaram.

As abas Bestiário/Companheiros são independentes. Regiões seguem a ordem reino_eldora → pradaria_inicial → floresta_sombria → campos_linho → pedreira_granito → pico_grifo → mina_ferro → forja_abandonada → pantano_maldito → picos_gelados → deserto_ancestral. capital_eldora é apresentada como Reino de Eldora, preservando criaturas. Regiões extras aparecem depois. Layout e dossiê conferidos em prévia local de 360px, sem overflow horizontal da página.

## Incubadoras consumíveis

- Flora vende 1 unidade por 25 gemas. Estoque em Bestiário > Companheiros.
- Compra debita `gems` e grava recibo único em `users.companion_incubator_grants` na mesma operação. A sincronização aplica cada recibo somente uma vez em `companions.supply_receipts`, permitindo retomar entregas interrompidas.
- Ao iniciar, confirmação explica o consumo e bloqueio de troca do ovo. Unidade e ovo são removidos do estoque na mesma atualização da incubação. Nascimento não cobra novamente.
- Migração preguiçosa schema 2: chocadeira antiga livre vira 1 unidade; incubação antiga mantém família/distância e não recebe unidade extra. Conquista antiga já recebida permanece marcada. A conversão torna-se persistente na próxima mutação e é idempotente.
- Backup deve incluir tanto `users` (recibos) quanto `companions` (estoque, incubação e recibos aplicados).

## Missões do Eldora Premium por ciclo

- Independentes do passe de batalha. Usa `eldora_premium.activated_at` e `expires_at`, normalizados em UTC.
- Cada ciclo de 30 dias oferece metas cumulativas de 100, 500 e 1.500 abates; cada meta concede 1 incubadora (3 por ciclo).
- Só novos abates confirmados pelo fluxo de recompensas contam, com Premium ativo, mesmo sem pet equipado. Não importa abates anteriores do Bestiário. Mantém os critérios de abate válidos do gancho de companheiros.
- Renovação antecipada estende a validade sem reiniciar o ciclo; ao atingir 30 dias começa a próxima contagem. Reativação após expirar usa a nova data de ativação.
- Progresso e resgates ficam em `companions.premium_cycles`, com ID pela data inicial do ciclo. Metas concluídas continuam resgatáveis após expirar; metas incompletas encerram com o ciclo.
- Crédito da incubadora e marcação de resgate na mesma atualização com controle de revisão. Resgates legados do passe e estoque já recebido são preservados; não há novos resgates pelos níveis do passe.
- Não há cron necessário: ciclo é calculado no servidor em cada abate/leitura. Reiniciar não zera progresso. Assinantes atuais começam a contar novos abates no ciclo vigente após publicar a atualização.
