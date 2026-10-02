# Pets: lançamento gradual

Capítulo atual: 1, configurado em `modules/companions.py`, constante `RELEASED_PET_CHAPTER`.

## Etapas

1. Pequeno Slime e Lobo Magro: conquista de ovo, incubação, caminhada, XP e vínculo.
2. Slime Verde e Lobo Alfa: evolução exige nível 10, vínculo 50 e 25 essências. Bloqueada até liberar capítulo 2.
3. Reservado para caminhos alternativos do Slime Azul e Magma. Ramificações ainda não ativadas: precisam de regras e artes antes da implementação.
4. Rei Slime e Lobisomem: nível 25, vínculo 300 e 100 essências, mantendo escolha de especialização. Bloqueados até capítulo 4.
5. Morcego: nova conquista bloqueada por enquanto; ovos, incubação e pets antigos continuam utilizáveis.

Não há liberação automática por data. Publicar artes, validar missões e então atualizar a constante. Abrir capítulo 4 não cria automaticamente as ramificações reservadas ao capítulo 3.

## Artes no repositório static-img

Pasta: `assets/mob/pet/`
Primeiros arquivos: `pequeno_slime.png` e `lobo_magro.png`.
Depois: `slime_verde.png`, `lobo_alfa.png`, `rei_slime.png`, `lobisomem_campones.png`.
Morcego preservado: `morcego_das_minas.png`.

PNG transparente 192 × 256 px, 3 colunas e 4 linhas, quadros de 64 × 64. Linhas: baixo, esquerda, direita, cima. Quadro central parado; caminhada a 8 quadros/s. Pés alinhados na mesma altura. Exibição contém a arte em 24 × 24 para herói de 48 × 48.

O mapa tenta carregar a folha da forma atual. Arquivo ausente mantém arte estática do Bestiário; recarregar após enviar uma folha nova. As folhas não são geradas por esta alteração.

## Compatibilidade

Nenhum pet, estoque, ovo, XP, vínculo, essência ou resgate existente é removido. Pets antigos mantêm o nome genérico da forma e os bônus anteriores; a arte acompanha o estágio equivalente. Pets novos recebem nomes da jornada. Bloqueio de evolução é validado no servidor antes de debitar essências. Um ovo antigo de Morcego ainda pode ser incubado e chocado.

Uma incubação por vez, consome uma incubadora ao iniciar, percorre 3.000 blocos e exige tocar em Chocar. Imagens nas missões, prévia do ovo ativo e roteiro recolhível por família. Missões Premium recolhíveis para reduzir a rolagem.

## Ainda fora desta entrega

Baú da Flora e ovos repetidos, novas famílias de outras regiões, caminhos elementais e animações de ataque. Antes de vender o baú, definir duplicatas: atualmente só existe um pet por família. Não cadastrar ovos repetidos na loja com a regra atual.
