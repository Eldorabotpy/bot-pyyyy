# Estudo de referência e proposta — Torre de Eldora

## O que conseguimos aprender com o APK

O APK 3.26.4 revela uma torre como uma expedição com risco e progressão, não apenas uma lista de batalhas. O material de ajuda do cliente indica que:

- cada andar exige vencer pelo menos um guardião para liberar a subida;
- encontros podem reapresentar desafios enfrentados pelo personagem em outras partes do jogo;
- o jogador pode sair da torre levando a moeda acumulada; uma derrota encerra a subida e reduz parte do que foi juntado;
- chegar ao Titã é a forma de concluir a expedição sem a penalidade de derrota;
- a torre também comporta eventos/tesouros e, conforme a apresentação oficial do sistema, quebra-cabeças e melhorias temporárias que duram entre encontros.

O APK não revela a fórmula exata de dificuldade, o gerador de andares nem as tabelas completas de recompensa. Esses pontos devem ser definidos para Eldora, não inferidos como se fossem dados recuperados.

## O que aprendemos com o histórico oficial

O anúncio dos criadores apresenta a torre como conteúdo longo de progressão e exploração. Os fragmentos da atividade servem a escolhas permanentes de progressão, e a subida aumenta a dificuldade. A publicação também cita desafios, tesouros escondidos, melhorias persistentes e enigmas. [Anúncio oficial da torre](https://blog.ornarpg.com/towers-of-olympia-revealing-the-new-endgame-system-for-orna-and-hero-of-aethric/)

As notas posteriores mostram dois aprendizados de operação importantes:

- Em 2025, a entrega dos fragmentos do Titã foi movida para o momento da vitória, para evitar perda caso o jogo fechasse antes de o jogador sair da torre. O Titã também passou a fornecer a recompensa final da atividade. Isso favorece um pagamento confirmado no servidor, separado da animação ou da saída da sala. [Notas oficiais, atualização 1.200](https://playorna.com/releases/?p=8)
- Em 2026, algumas torres de evento tiveram menos andares e mais fragmentos por conclusão; em outra atualização, o ganho de materiais por andar foi aumentado. Isso sugere que duração e recompensa por minuto precisaram de ajustes. Para Eldora, a primeira versão deve ter sessões curtas e telemetria antes de aumentar a duração. [Notas oficiais, atualizações 1.220–1.222](https://playorna.com/releases/?p=6)

Essas são referências de produto do próprio estúdio, não números que devemos transplantar. A primeira publicação também descreve uma versão inicial; as notas posteriores confirmam que o sistema foi balanceado depois.

## Situação de Eldora

Não encontrei uma Torre na interface web nem um sistema de torre em `modules`, `templates` ou `static/js`. Há um módulo de Catacumbas do bot com cinco andares, mas ele traz o rótulo de modo de teste, guarda salas e progresso em memória e não aparece registrado no inicializador do bot. Ele confirma que há ideias antigas de combate em sequência, mas não atende ao pedido de uma torre jogável.

Eldora já tem combate, monstros, inventário, efeitos, mapas Phaser, persistência de instâncias e eventos. A implementação da torre precisa conectar esses sistemas sem depender do protótipo de Catacumbas nem dos recursos do APK.

## Proposta de jogo: Torre do Eclipse

Uma torre original de Eldora em que cada piso é uma pequena sala explorável no mapa, com uma rota clara para o próximo andar. O objetivo não é só vencer o maior número de inimigos: o jogador monta uma estratégia durante a subida e decide quando proteger o que ganhou.

### Loop de uma expedição

1. O jogador entra pelo portal da torre e inicia uma tentativa individual. A entrada consome um **Selo do Eclipse**; voltar após desconexão retoma a mesma tentativa sem cobrar outro selo.
2. Cada andar tem uma sala compacta feita com peças e arte de Eldora. Um Guardião da Torre bloqueia a escada. Baús, eventos e rotas opcionais ficam fora do caminho obrigatório.
3. Depois do Guardião, o jogador escolhe uma entre duas portas, com o tipo de risco e a categoria de recompensa anunciados antes da escolha. Exemplos: combate de elite por mais fragmentos, sala de provisões para recuperar recursos ou enigma para receber uma melhoria temporária.
4. A cada três andares há um Altar de Vigília. Nele o jogador pode guardar os fragmentos coletados e sair com eles, ou continuar sem guardar para tentar alcançar recompensas melhores. O altar também oferece uma escolha limitada de recuperação ou melhoria.
5. O décimo andar fecha a primeira expedição com um chefe original. Vencê-lo entrega o pagamento final e encerra a tentativa. Depois de calibrar o tempo e as recompensas, a torre pode ganhar uma trilha avançada mais longa.

### Risco e recompensa próprios de Eldora

- **Fragmentos do Eclipse:** moeda exclusiva da torre, obtida em salas e andares. Só pode ser usada na progressão da torre, evitando inflação direta de ouro ou gemas.
- **Fragmentos carregados:** saldo ainda não guardado. Ao perder uma batalha, o jogador perde uma parte desse saldo; a porcentagem é uma decisão de balanceamento a validar. O saldo guardado nos altares é permanente.
- **Pagamento do chefe:** concedido no servidor no instante da vitória e marcado como pago na mesma transação lógica. Reabrir, atualizar ou desconectar não pode duplicar nem apagar a recompensa.
- **Destinos de gasto:** uma oficina da torre oferece três escolhas com valor distinto: aprimoramento de combate da torre, desbloqueios permanentes cosméticos/de coleção e materiais raros para receitas existentes. Nada deve competir com itens premium.

### Variedade entre subidas

- **Bençãos temporárias:** escolhas que duram somente naquela tentativa, como fortalecer uma família de habilidades, melhorar defesa após cura ou ganhar recurso ao vencer sem receber dano. Elas incentivam adaptar equipamento e estilo sem criar poder permanente obrigatório.
- **Andares de evento:** a cada subida, algumas salas são sorteadas de um conjunto escrito à mão: guardião, elite, enigma curto, tesouro, armadilha ou altar. A sequência usa semente salva no servidor para poder retomar a mesma run.
- **Chefes com leitura própria:** cada chefe deve mudar uma regra de combate, não apenas multiplicar vida e dano. Exemplo original: alternar entre duas posturas e abrir uma janela de dano quando o jogador responde à telegráfica correta.
- **Memória do jogador:** uma sala pode projetar uma versão especial de um monstro já conhecido no Eldora. A projeção deve combinar criaturas do próprio jogo e modificadores novos; não replicar personagens ou nomes do APK.

## Escopo inicial recomendado

Para a primeira versão, recomendo:

- 10 andares, com três pontos de saída/depósito e um chefe final;
- modo solo, mapa 2D pequeno por andar, duas rotas de escolha e um encontro obrigatório por andar;
- 4 famílias de salas no lançamento: combate, elite, tesouro/provisões e enigma;
- fragmentos não guardados com penalidade moderada em derrota; fragmentos depositados sempre preservados;
- 3–5 bênçãos por run, escolhidas entre opções simples e mutuamente exclusivas;
- sem modo infinito, PvP ou grupo na primeira entrega. Grupo exige regras extras para jogador que cai, sai ou fica desconectado, além da distribuição de recompensa.

Esses números são uma proposta inicial de escopo para Eldora, não propriedades recuperadas de Aethric. O tempo-alvo deve ser medido com jogadores reais; a hipótese para protótipo é uma expedição de aproximadamente 15 minutos.

## Persistência e segurança necessárias

O estado mínimo de uma tentativa deve conter: `run_id`, dono, versão do esquema, semente, andar, sala ativa, portas reveladas, bênçãos, fragmentos carregados, fragmentos guardados, estado de combate, estado da run e registro do pagamento final.

As transições precisam ser validadas no servidor: entrar, escolher porta, concluir combate, depositar, sair, morrer e vencer o chefe. Persistir após cada transição permite retomar a run. A recompensa deve usar uma chave idempotente ligada ao `run_id` e à conclusão. Uma queda do navegador ou do servidor não pode transformar uma vitória em perda de prêmio.

## Decisões de design antes de codificar

1. Quem pode acessar a torre: nível, missão ou todos desde o início?
2. A torre fica como local no mapa de Eldora ou como instância acessada por um menu/portal?
3. Quantos selos por dia e como se obtêm entradas adicionais?
4. Qual porcentagem dos fragmentos carregados se perde na derrota?
5. Os altares restauram HP/MP ou apenas guardam recursos? Recuperação ilimitada pode permitir partidas sem risco.
6. Qual é o destino principal dos fragmentos? É preciso equilibrar o custo da progressão com o ritmo das runs.
7. Queremos grupo no lançamento ou entregamos primeiro uma versão solo estável?

Minha recomendação é começar com acesso por missão, portal no mapa, 10 andares solo e depósitos nos andares 3, 6 e 9. Depois do protótipo, ajustamos custo de entrada e fragmentos observando duração, taxa de abandono, andares alcançados, mortes e recompensas por hora.
