# Jornadas dos companheiros

Capítulo atual: 1, configurado por RELEASED_PET_CHAPTER em modules/companions.py. O Códice mostra a jornada completa, mesmo quando a família ou a próxima forma ainda está bloqueada. Slime Verde está liberado pontualmente por forma; Rei Slime, Lobo Alfa, Lobisomem e todas as formas do Morcego continuam bloqueados.

## Jornadas

- Slime: Pequeno Slime → Slime Verde → Rei Slime. Capítulos 1, 2 e 4.
- Lobo: Lobo Magro → Lobo Alfa → Lobisomem. Capítulos 1, 2 e 4.
- Morcego: Morcego das Minas → Morcego de Mana → Morcego Gigante. As três formas previstas para o capítulo 5; Morcego de Mana e Morcego Gigante já aparecem na configuração das Catacumbas.
- Os cinco slimes elementais não são companheiros. Continuam como monstros do mundo e suas imagens permanecem no repositório.

| Mudança | Liberação | Requisitos |
| --- | --- | --- |
| Pequeno Slime → Slime Verde | Capítulo 2 | Nível 10, vínculo 50 e 25 essências de Slime |
| Slime Verde → Rei Slime | Capítulo 4 | Nível 25, vínculo 300 e 100 essências; escolher especialização |
| Lobo Magro → Lobo Alfa | Capítulo 2 | Nível 10, vínculo 50 e 25 essências de Lobo |
| Lobo Alfa → Lobisomem | Capítulo 4 | Nível 25, vínculo 300 e 100 essências; escolher especialização |
| Morcego das Minas → Morcego de Mana | Capítulo 5 | Nível 10, vínculo 50 e 25 essências de Morcego |
| Morcego de Mana → Morcego Gigante | Capítulo 5 | Nível 25, vínculo 300 e 100 essências; escolher especialização |

O ovo de cada família exige 50 abates registrados no Bestiário. Abates de ondas de invasão não contam. A forma final recebe uma especialização. A mudança mantém nível, XP e vínculo; o estágio e o bônus avançam.

No Códice, a jornada detalhada identifica a forma atual, a próxima evolução e as formas futuras. Também mostra capítulo e requisitos de cada transição: nível 10, vínculo 50 e 25 essências na primeira; nível 25, vínculo 300 e 100 essências na final, com escolha de especialização.

Não há liberação automática por data. Para liberar uma forma isolada, use RELEASED_PET_FORM_OVERRIDES; para abrir um capítulo inteiro, confira suas artes e aumente RELEASED_PET_CHAPTER. A liberação atual é Pequeno Slime → Slime Verde. O bloqueio é validado no servidor antes de consumir essências.

## Arquivos de arte por forma

Os caminhos são relativos a `assets/` no repositório de imagens. Cada forma precisa de uma imagem estática para o Códice e de uma folha própria para andar no mapa.

| Família | Forma | Imagem estática | Folha animada |
| --- | --- | --- | --- |
| Slime | Pequeno Slime | `mob/combate/pradaria/pequeno_slime.png` | `mob/pet/pequeno_slime.png` |
| Slime | Slime Verde | `mob/combate/pradaria/slime_verde.png` | `mob/pet/slime_verde.png` |
| Slime | Rei Slime | `mob/combate/pradaria/rei_slime.png` | `mob/pet/rei_slime.png` |
| Lobo | Lobo Magro | `mob/combate/floresta/lobo_magro.png` | `mob/pet/lobo_magro.png` |
| Lobo | Lobo Alfa | `mob/combate/floresta/lobo_alfa.png` | `mob/pet/lobo_alfa.png` |
| Lobo | Lobisomem | `mob/combate/campos_linho/lobisomem_campones.png` | `mob/pet/lobisomem_campones.png` |
| Morcego | Morcego das Minas | `mob/combate/mina_ferro/morcego_das_minas.png` | `mob/pet/morcego_das_minas.png` |
| Morcego | Morcego de Mana | `mob/combate/dungeon_01/morcego_mana.png` | `mob/pet/morcego_mana.png` |
| Morcego | Morcego Gigante | `mob/combate/dungeon_01/morcego_gigante.png` | `mob/pet/morcego_gigante.png` |

## Mudança de forma e animação no mapa

Quando a API confirma uma evolução, o painel emite eldora:companheiros com o novo estado. CompanionMapHUD.apply lê pet.art.species, troca para a textura daquela espécie e reposiciona o pet junto ao jogador. A cada 50 ms, position compara o ponto atual do pet com o ponto anterior e suaviza o acompanhamento. Durante movimento, chama pet_sheet_<species>_<direcao> com direções down, left, right ou up, a 4 quadros por segundo. Parado, usa o quadro central da direção atual.

Uma folha tem 192 × 256 px: 3 colunas por 4 linhas de quadros 64 × 64, na ordem baixo, esquerda, direita e cima. Sem folha válida, o mapa mostra a ilustração estática da forma; sem imagem estática, usa o ícone da família. Para Lobisomem, as chaves são pet_sheet_lobisomem_campones_down, pet_sheet_lobisomem_campones_left, pet_sheet_lobisomem_campones_right e pet_sheet_lobisomem_campones_up. Para os morcegos, são pet_sheet_morcego_das_minas_<direcao>, pet_sheet_morcego_mana_<direcao> e pet_sheet_morcego_gigante_<direcao>. As folhas pendentes ficam em assets/mob/pet/ com o nome da espécie. O mapa usa fallback estático ou ícone até as folhas serem publicadas.

O catálogo local registra folhas animadas apenas para Pequeno Slime e Lobo Magro. As folhas para as demais formas já estão previstas em PET_SHEETS. As imagens estáticas de Slime Verde, Rei Slime, Lobo Alfa e Morcego de Mana estão cadastradas; Lobisomem, Morcego das Minas e Morcego Gigante têm caminhos preparados em PET_IMAGES para as novas artes. Os arquivos devem seguir esses nomes e pastas para aparecerem no Códice e no mapa.

## Compatibilidade

Pets, ovos, XP, vínculo, essências e resgates das famílias Slime, Lobo e Morcego são preservados. A implementação dos cinco slimes elementais não foi publicada; eles continuam como monstros e suas imagens permanecem disponíveis para Bestiário e mapa, sem ovos nem bônus de companheiro. Se houver dados de teste antigos desses pets, eles ficam guardados e inativos.

Uma incubação por vez; iniciar consome uma incubadora, percorre 3.000 blocos e exige tocar em Chocar. O pet equipado recebe XP e vínculo por vitória. Bônus são calculados ao consultar os atributos e não gravam atributos permanentes.

## Publicação

Enviar as nove folhas de pet para assets/mob/pet/, usando os nomes de espécie em PET_SHEETS. Para imagens estáticas, usar os caminhos definidos em PET_IMAGES. Cada folha deve ser PNG transparente de 192 × 256 px, com 3 colunas e 4 linhas de quadros 64 × 64, nas direções baixo, esquerda, direita e cima. Conferir alinhamento dos pés antes de liberar o capítulo. Esta alteração não publica arquivos no servidor de imagens.
