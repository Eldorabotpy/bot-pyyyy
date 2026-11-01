# Mundo de Eldora: instruções para agentes

Projeto: RPG online em português. Servidor Flask + Flask-SocketIO + MongoDB (main.py, modules/, pvp/, rotas/). Cliente web em JavaScript puro com Phaser (static/js, templates). Mapas em Tiled (.tmj em static/regions, 60x60 blocos de 32 px). Personagens em estilo chibi. Existe também o plano de um app Godot que usará a mesma API.

Regras fixas
- Toda regra de jogo (dano, drops, economia, mercado, PvP, clãs) fica no SERVIDOR. O cliente só mostra e envia ações.
- Nunca escreva ou imprima segredos (senhas, tokens, strings de conexão). Use variáveis de ambiente.
- Não altere o login (modules/portal_auth.py, portal_auth.js) nem pagamentos sem pedido explícito.
- Skins de personagem: quadros de 128 px hoje; novas de 256 px serão suportadas por skin. Não quebre as antigas.
- Mudanças pequenas e testáveis, uma por pull request. Antes de editar, explique o plano em poucas linhas.
- Rode os testes existentes (tests/ e tools/check_portal_auth.py) antes de concluir.
