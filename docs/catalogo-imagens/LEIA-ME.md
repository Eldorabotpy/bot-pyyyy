# Catálogo local de imagens do Eldora

Abra `ABRIR_CATALOGO.bat` com duplo clique. O catálogo abre no navegador; as prévias do GitHub precisam de internet.

As marcações, observações e itens adicionados são salvos no armazenamento local do navegador. Use **Exportar progresso** para guardar uma cópia JSON ou **Importar** para recuperá-la em outro navegador ou PC.

Nas abas **Biblioteca**, **Itens do jogo**, **Arquivos do jogo** e **Arquivos locais**, use **Marcar para substituir** nas imagens em `assets/itens/` que você pretende redesenhar. Essa marcação é independente de **Arte conferida** e acompanha o caminho do arquivo entre as abas. O filtro **Marcados para substituir** mostra essa lista; a exportação também guarda essas marcações.

Biblioteca de artes atualizada em 22/10/2026; os índices do jogo abaixo continuam no snapshot de 21/10/2026:

- `Eldorabotpy/static-img`, `main` no commit `509e74dbdc3adb7e87abbde02e3d282201cf0c08`: 971 imagens. A pasta `assets/itens/` contém 476 imagens marcáveis para substituição.
- `Eldorabotpy/bot-pyyyy`, `main` no commit `185ae6294b79ebd5a41afb42d38e1da77dc7ec07`: 178 arquivos de imagem.
- O índice da forja (`static/js/forja_imagens.js`, mesmo conteúdo local e no GitHub; SHA `c7d6b5ddab37f701d8966ece6155be9d71e43e66`) cobre 340 identificadores e 347 referências; são 345 caminhos únicos, todos encontrados no repositório de artes.
- Checkout local: 174 arquivos de imagem.
- 30 imagens do jogo estão no GitHub, mas não neste checkout. Conforme sua explicação, elas aparecem como **publicadas · sem cópia local**.
- 26 cópias locais de equipamento não estão no repositório do jogo. 22 têm correspondência por nome no `static-img`; quatro não foram localizadas pelo nome em nenhum dos dois repositórios. A aba **Arquivos locais** separa esses estados.
- **Pendências** traz nomes da auditoria anterior (`d3486a69e3e3a29027383d243ba2987fbcd510f8`, 30/09/2026). Essa lista ainda precisa ser reconciliada com os dados atuais do jogo antes de criar arte.

“Arte conferida” registra sua revisão visual. “Publicado” indica apenas em qual snapshot do GitHub o arquivo aparece. Os snapshots são estáticos e não sincronizam sozinhos.

O checkout estava no commit `bbe3df2`, 26 commits atrás do GitHub, e contém alterações de trabalho. O catálogo registra o estado consultado sem alterar arquivos do jogo.
