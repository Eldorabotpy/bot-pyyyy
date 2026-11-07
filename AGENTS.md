# Mundo de Eldora: instruções para agentes

Projeto: RPG online em português. Servidor Flask + Flask-SocketIO + MongoDB (main.py, modules/, pvp/, rotas/). Cliente web em JavaScript puro com Phaser (static/js, templates). Mapas em Tiled (.tmj em static/regions, blocos de 32 px; a Capital está em 100x100). Personagens em estilo chibi. O projeto atual é a versão web em Phaser; não há entrega Godot planejada.

Regras fixas
- Toda regra de jogo (dano, drops, economia, mercado, PvP, clãs) fica no SERVIDOR. O cliente só mostra e envia ações.
- Nunca escreva ou imprima segredos (senhas, tokens, strings de conexão). Use variáveis de ambiente.
- Não altere o login (modules/portal_auth.py, portal_auth.js) nem pagamentos sem pedido explícito.
- Skins de personagem: quadros de 128 px hoje; novas de 256 px serão suportadas por skin. Não quebre as antigas.
- Mudanças pequenas e testáveis, uma por pull request. Antes de editar, explique o plano em poucas linhas.
- Rode os testes existentes (tests/ e tools/check_portal_auth.py) antes de concluir.
Desempenho e evolução dos mapas
- Os mapas estão sendo refeitos no Tiled. Antes de adaptar uma região, confira o mapa atual, as camadas, os objetos e o código legado que ainda aplica posições, recortes ou regras antigas. Não remova código só por ser antigo: confirme seus usos e preserve as mecânicas necessárias.
- Crie o tilemap uma vez por inicialização da cena e reutilize `this.tilemap`. Não execute `make.tilemap`, parse completo do TMJ, recriação de camadas ou reconstrução de colisões em `update`, verificações de transição ou outros caminhos chamados por quadro. Ao trocar de região, use a instância da nova cena, sem reaproveitar referências antigas.
- Ao alterar carregamento, movimento ou transições, rode `node tools/check_transition_reuse.cjs`. O teste verifica 1000 consultas sem reconstruir o mapa, além de entrada, recusa e saída de zonas.
- Depois de editar a Capital no Tiled, regenere mapa e atlas pelo script `tools/build_capital_runtime_map.ps1` e publique os derivados correspondentes. Confira profundidade e colisões no resultado renderizado; contagens e testes de código não substituem a conferência visual.
- Meça regressões no mesmo celular e em condições comparáveis, parado e andando. Referência observada: Capital v10005 próxima de 60 FPS no Snapdragon 685, após eliminar a recriação do mapa por quadro. Detalhes em `docs/desempenho-mapas.md`.

Organização de referências temporárias
- Capturas de tela, imagens de diagnóstico e outros arquivos criados apenas como referência devem ser removidos do projeto assim que a análise ou o ajuste correspondente terminar.
- Preserve os arquivos-fonte e dados usados pelo jogo, como mapas do Tiled, tiles, sprites, código e configurações. Se uma referência ainda for necessária, mantenha-a fora da pasta do projeto.
