# Análise estática de sistemas — Aethric 3.26.4

## Escopo e método

Análise estática do APK fornecido, sem instalar nem executar o aplicativo. O pacote tem cerca de 223 MB e contém bundles JavaScript, recursos de interface, arquivos de idioma, áudio e imagens. Não foram encontrados source maps entre os arquivos JavaScript listados. Os nomes e textos de interface permitem identificar fluxos e regras apresentados ao jogador; não revelam por si só a implementação completa nem as regras mantidas pelo servidor.

O conteúdo do APK foi tratado como dado de referência. Este documento registra observações e uma proposta original para Eldora; não copia código, textos, imagens, sons ou outros recursos do jogo analisado.

## Sistemas identificados no cliente

- **Exploração e controle de áreas:** mapa do mundo, locais de interesse, encontros e progresso associado à exploração.
- **Desafios instanciados:** masmorras e sequências de combate, incluindo opções de dificuldade e recompensa.
- **Desafio de andares:** a interface descreve subir por uma estrutura em vários pisos, coletar uma moeda própria da atividade e decidir entre continuar ou sair. Há risco de perder parte do saque ainda não protegido ao falhar.
- **Atividades em grupo:** grupo, compartilhamento de experiência, incursões contra chefes e conteúdo de reino.
- **Progressão e economia:** classes, habilidades, equipamento, encantamento, missões, arena, pesca e materiais específicos de atividades.

Esses pontos vêm de nomes de recursos e textos de ajuda/localização empacotados no cliente. São evidência de fluxos apresentados, não confirmação de fórmulas exatas, taxas de saque ou validações do servidor.

## Comparação com Eldora

O repositório já contém combate e recompensa, calabouços regionais, checkpoints de uma instância web e eventos de chefe em grupo. Também há um módulo de Catacumbas do bot com cinco andares, mas a própria configuração o identifica como “MODO TESTE”; o estado das salas fica em dicionários de memória e não encontrei registro desse fluxo no ponto de inicialização nem uma torre na interface web. Isso não equivale a uma torre jogável no Eldora. A torre deve ser tratada como sistema novo; o protótipo de Catacumbas só pode servir como referência parcial para combate e progressão de andares.

## Direção proposta: Torre do Eclipse

Uma torre original de Eldora, instanciada e orientada a decisões, integrada ao combate existente. O estudo complementar define o loop de andares, risco, recompensa, persistência e o escopo recomendado para o protótipo.

1. A entrada cria uma expedição com semente, andar atual, modificadores e estado do jogador registrados no servidor.
2. Ao vencer cada andar, o jogador escolhe uma de duas rotas com risco e recompensa visíveis: combate padrão, encontro de elite ou sala de provisões.
3. Cada vitória concede **fragmentos de fenda** ainda não assegurados. Altares em andares definidos permitem encerrar a expedição e converter esses fragmentos em recompensa permanente.
4. Uma derrota encerra a tentativa e descarta apenas os fragmentos não assegurados; recompensas de marcos já resgatadas permanecem com o jogador.
5. A progressão aumenta a pressão por meio de modificadores e chefes com regras próprias de Eldora, sem reutilizar conteúdo visual do APK.
6. O placar registra melhor andar, tentativas concluídas e fragmentos obtidos. Recompensas e custo de entrada devem ser balanceados com a economia atual antes de liberar o modo.

### Encaixe técnico recomendado

- Criar um módulo isolado de expedição, com transições de estado explícitas (`aguardando`, `em_andar`, `extraído`, `derrotado`, `concluído`).
- Reutilizar o motor de combate e o inventário do Eldora; o módulo controla entrada, escolha de rota, checkpoint e encerramento.
- Persistir a expedição no documento do personagem ou em registro próprio para sobreviver à reconexão e impedir duplicação de recompensa.
- Validar cada ação no servidor e tornar a concessão de recompensa idempotente.
- Começar em modo individual; suporte a grupo pode ser uma etapa posterior, depois de definir regras para desconexão, derrota parcial e distribuição de saque.

## Limites da evidência

O APK permite levantar nomes de sistemas, recursos incluídos e parte das regras comunicadas pela interface. Não permite afirmar, sem observação adicional, os valores de balanceamento em produção, a lógica executada remotamente, as proteções antifraude do servidor ou o comportamento de todas as versões e eventos. A Torre do Eclipse é uma proposta de design para Eldora, não uma descrição do código ou das regras internas de Aethric.

## Próxima etapa sugerida

Ver o estudo complementar em [estudo_torre_eldora.md](estudo_torre_eldora.md), que aprofunda o loop de torre e recomenda uma direção original para Eldora antes da implementação.
