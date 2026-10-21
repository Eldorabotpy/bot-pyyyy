# Necromante — análise dos fluxos de combate

Este documento registra o levantamento dos motores de combate e a proposta inicial para integrar a mecânica de almas e esqueletos. A classe e as habilidades ainda não foram adicionadas ao jogo.

## Como os combates atuais são resolvidos

| Fluxo | Estado e resolução | Observações para invocações |
| --- | --- | --- |
| Caçada no mapa | `modules/player/stats.py::processar_turno_combate` resolve a ação, aplica dano ao monstro persistido na caçada, resolve o contra-ataque e salva o personagem. | Não existe uma sessão isolada por jogador e encontro. Um estado de invocação não pode ser salvo diretamente no monstro, que pode ser compartilhado. Precisa de chave de encontro por jogador ou sala. |
| Caçada em grupo | `modules/combat/group_combat_manager.py` guarda heróis, monstro compartilhado, fila de iniciativa e estado da sala. `stats.py` sincroniza HP e avança a fila. | Lacaios devem pertencer ao dono, não ao grupo inteiro nem ao monstro. Não devem receber turnos independentes. |
| Mímico de dungeon | O encontro é interceptado pelo serviço de dungeon, mas passa pelo fluxo de caçada em `stats.py`. | Deve herdar a regra da caçada e limpar a invocação ao encerrar o encontro. |
| Catacumbas | `modules/events/catacumbas/combat_handler.py` mantém uma sessão de raid e resolve ataques contra o chefe; o chefe reage após um contador de ações. O cálculo de golpe usa `combat_engine.py`. | O ataque do grupo precisa ocorrer dentro da ação do dono sem aumentar o contador de ações do chefe. A invocação deve ser limpa ao trocar de andar ou acabar a raid. |
| Invasão/defesa do reino | `modules/combat/combat_raid_engine.py` mantém heróis, monstros e uma fila de iniciativa; cada monstro pode agir separadamente. Habilidades usam `combat_engine.py`, mas ataques básicos e golpes dos monstros têm cálculo local. | Não inserir cada esqueleto na fila; isso adicionaria ações e mudaria muito o equilíbrio. Resolver o grupo como um único pacote de ataque vinculado à ação do Necromante. |
| Fendas dimensionais | `modules/events/dimensional_boss_engine.py` tem estado de evento próprio, aceita uma ação por herói por rodada e depois processa as ações inimigas. O cálculo de habilidades é local ao motor. Inimigos auxiliares já são entidades separadas. | A regra canônica de lacaios não pode depender do motor geral de dano. O evento precisa chamar a resolução do grupo e produzir animação de aliado sem colocar os esqueletos na lista de jogadores/inimigos. |
| Guerra de Clãs PvP | `modules/clan/clan_war_battle_engine.py` persiste batalhas de equipe, valida turno e alvo, e usa `combat_engine.py` para ataques e habilidades ofensivas. | Invocações como dano adicional e proteção alteram a disputa entre equipes. Recomenda-se não habilitar no PvP na primeira entrega; definir uma regra de arena antes de incluir. |
| Guerra de Guildas | `modules/guild_war/combat_integration.py` registra pontos de abates PvE/PvP e resultados; não é um motor de combate separado. | O comportamento acompanha o fluxo de combate que originou o abate. |

`modules/combat/battle_manager.py` não aparece ligado aos pontos de entrada atuais. `group_combat_manager.py::processar_acao_grupo_placeholder` também é explicitamente um ponto de integração futura; a caçada em grupo funcional atual é coordenada por `stats.py` com as funções de sala do gerenciador.

## Separação de responsabilidades existente

`modules/combat/combat_engine.py::processar_acao_combate` calcula o golpe e retorna dano, mana restante, recarga, animação e logs. O controlador que o chamou aplica o dano e encerra ou avança a luta. `modules/skills/skill_effects_adapter.py` aplica alguns efeitos existentes, como sangramento, veneno, escudo e regeneração; não cria entidades de combate.

Portanto, a habilidade de invocação precisa de integração explícita nos controladores. Cadastrar dados em `modules/game_data/skills.py` sozinho faria a habilidade seguir a resolução de ataque comum.

## Regra de combate proposta

1. **Almas são recurso temporário da batalha**, associado ao Necromante e ao encontro. Não ficam no inventário nem no monstro global.
2. **Levantar Esqueletos** gasta almas para aumentar o grupo até o limite atual da habilidade. Limite inicial: quatro. Melhorias futuras podem elevar para seis, oito e dez.
3. O grupo tem **uma resolução coletiva**, vinculada à ação do Necromante. Ele não recebe iniciativas nem turnos extras.
4. O dano coletivo escala com os esqueletos ativos, mas tem teto baseado nos atributos do dono para impedir que o número de unidades multiplique o dano sem limite.
5. Inimigos derrotados concedem almas no máximo uma vez por abate. O dano dos próprios esqueletos não gera almas, evitando ciclo de invocação infinita. Para chefes, a concessão deve ser limitada por combate ou por marcos de HP.
6. O estado dos lacaios termina com o encontro. Em salas com troca de andar, o controlador decide explicitamente se a invocação persiste ou é encerrada.
7. Cada controlador converte a mesma regra para seu formato de logs/animações e aplica o dano pelo seu caminho existente. A fila de turnos permanece sob controle do motor de cada modo.
8. **PvP fica fora da primeira entrega** até balancearmos alvo, proteção e dano extra em batalhas de equipes.

## Sequência recomendada

1. Definir e implementar um núcleo pequeno de estado de invocação e consumo de almas, sem acesso a banco de dados nem conhecimento de uma UI específica.
2. Integrar primeiro à caçada no mapa e à caçada em grupo, que compartilham o controlador de ação em `stats.py`; acertar chaves de estado, propriedade do invocador, limpeza e crédito de abate.
3. Levar o mesmo núcleo para Catacumbas e Mímicos, respeitando os limites de sessão e os contadores próprios.
4. Adaptar Invasão e Fendas separadamente, pois têm turnos e motores de dano diferentes.
5. Só então avaliar PvP de Clãs e integração de recompensas.

## Despertar da Centelha e escolha inicial de classe

### Fluxo atual encontrado

- Varek apresenta as missões iniciais `q1_varek_recruta`, `q2_varek_defesas` e `q3_varek_provacao`. A história fala em limpar Gosmas, repelir feras e salvar uma caravana, mas as interações do cliente liberam a conclusão pelo nível (2, 4 e 5). Não há registro confirmado de escolhas do jogador nessas cenas.
- A missão `q4_selene_classe`, em `modules/missoes.py`, é chamada **O Despertar da Centelha**, exige nível 5 e conduz à Selene.
- `static/js/npcs_engine.js` monta uma lista fixa de nove classes iniciais. O menu não recebe opções calculadas a partir do histórico da jornada.
- A rota usada pelo menu, `/api/player/escolher_classe` em `main.py`, verifica nível mínimo 5 e se a classe consta em `CLASSES_DATA`. Depois define a classe, recalcula HP/MP e marca Q4 como resgatada. Ela não exige a conclusão de Q3 nem valida afinidade/comportamento.
- Existe também `/api/npc/missao/despertar` em `rotas/npc.py`, que grava a classe e a missão sem validar nível, classe permitida ou pré-requisito. Para qualquer despertar condicionado ao histórico, a decisão precisa ser validada no servidor; o cliente não pode escolher ou fabricar seus próprios sinais.

### Proposta de descoberta sem tirar a escolha do jogador

O comportamento inicial **desbloqueia uma possibilidade**, mas não escolhe a classe automaticamente. Na conversa com Selene, o jogador continua escolhendo seu caminho. Quem demonstrou afinidade com as almas vê uma opção especial do Necromante junto às classes normais.

Para dar significado ao histórico, transformar a provação da caravana de Q3 em cenas curtas com escolhas registradas no servidor:

1. **Após a defesa da caravana:** o jogador encontra uma alma que não conseguiu partir. Pode libertá-la, ignorá-la ou escutar o que ela tenta avisar.
2. **No desfecho da provação:** o jogador decide o destino de um foco espiritual que ameaça os sobreviventes: selá-lo para proteger os vivos, destruí-lo ou acolher voluntariamente as vozes dos mortos.
3. **Reconhecimento da Centelha:** se o jogador escutou e acolheu os mortos sem sacrificar os sobreviventes, Selene percebe uma ressonância rara. Isso habilita o Necromante no menu; ainda cabe ao jogador aceitar ou recusar.

Isso apresenta necromancia como domínio e responsabilidade pelas almas, sem exigir uma origem Mago/Assassino e sem tornar a classe automaticamente maligna. Um rastreador de jornada pequeno, por exemplo `awakening_marks`, guardaria somente escolhas relevantes da abertura e seria atualizado por rotas do servidor. Não é necessário registrar toda ação ou todo golpe.

### Decisões como parte do sistema de missões

As escolhas não devem existir somente para liberar o Necromante. Q1, Q2, Q3 e missões futuras podem usar o mesmo mecanismo genérico de decisão. Cada escolha registra traços da jornada e pode influenciar a reação de NPCs, pequenos resultados da missão e, mais adiante, opções especiais de evolução. Não muda a classe do jogador automaticamente.

O fluxo inicial pode ser:

1. **Q1 — decisão de sobrevivência:** uma escolha simples entre seguir a ordem de Varek ou arriscar-se para ajudar um viajante. Registra traços gerais como `coragem` e `compaixao`.
2. **Q2 — decisão de prioridade:** proteger moradores, perseguir a ameaça ou investigar sua origem. Registra traços como `protecao`, `astucia` ou `curiosidade`.
3. **Q3 — caravana:** usa os inimigos e o combate comum existentes. No desfecho, o jogador escolhe como responder ao espírito do guarda e como tratar os sobreviventes. Pode registrar `vinculo_espiritual`, `compaixao` ou `dever` e também alterar a fala/recompensa da missão.
4. **Q4 — escolha com Selene:** todas as classes base continuam disponíveis. Selene comenta os traços mais fortes e pode revelar caminhos especiais que combinem com a jornada; o jogador escolhe se quer seguir um deles.

Exemplos de leitura dos traços: `vinculo_espiritual` junto de `compaixao` pode revelar o Necromante; `protecao` e `dever` podem apontar para um caminho de guardião; `curiosidade` e estudo podem revelar um caminho arcano. Esses são exemplos de afinidade, não requisitos para as nove classes base.

O diálogo atual (`mostrarDialogoRPG`) é uma caixa de texto fechada ao toque, sem opções. A primeira base técnica seria **um componente genérico de escolhas ligado à missão**, com opções e consequências definidas nos dados da missão e validação/registro pelo servidor. A caravana o usaria primeiro, mas o componente seria reutilizado por Varek, Selene e outros NPCs. Os mobs continuam usando o combate comum; não é necessário criar IA ou ações especiais de mob para registrar decisões narrativas.

Para manter o escopo inicial controlado, Q1 e Q2 podem começar com consequências leves e poucos traços; Q3 é o primeiro momento com cena completa. Depois, as missões restantes podem adotar o mesmo mecanismo gradualmente.

Para preservar o acesso universal combinado anteriormente, a afinidade da jornada inicial pode dar o **despertar antecipado no nível 5**. Quem não encontrou esse caminho continua podendo obter a classe depois pelo evento épico universal, cumprindo requisitos próprios. Assim, as ações iniciais alteram a descoberta e a história, mas não fecham a classe permanentemente para os demais jogadores.

### Decisões de design sugeridas

- Definir opções e resultados como dados de missão, para que o componente sirva a mais de uma quest.
- Gravar os traços no servidor, em histórico versionado da jornada; o navegador apenas apresenta as opções.
- Manter as nove classes base disponíveis para todos. Usar traços para revelar diálogos e caminhos especiais, sem forçar classe.
- Usar Q3 para apresentar a primeira cena completa da caravana; estender a estrutura às outras missões gradualmente.
- Conservar a rota tardia universal para quem não tiver revelado um caminho especial no início.

## Pendências de balanceamento antes da implementação completa

- Custo de almas por esqueleto e limite máximo de almas por luta.
- Se invocação pode ser repetida até preencher a capacidade em uma ação ou exige ações separadas.
- Vida coletiva dos lacaios e como inimigos podem removê-los.
- Coeficiente e teto do dano coletivo.
- Se lacaios continuam entre andares das Catacumbas.
- Regra de recompensa quando um esqueleto desfere o golpe final.
