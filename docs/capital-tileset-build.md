# Mapa de runtime otimizado da Capital

`static/regions/capital_eldora.tmj` e `static/images/regions/capital_eldora/tilesets/capital eldora.png` são as fontes editáveis no Tiled.

Depois de salvar mudanças no mapa, gere novamente os arquivos usados pelo jogo em um PowerShell 7:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\tools\build_capital_runtime_map.ps1
```

O jogo Phaser carrega os arquivos gerados:

- `static/regions/generated/capital_eldora.runtime.tmj`
- `static/images/regions/capital_eldora/tilesets/generated/capital_eldora_compact.png`

O mapa de runtime preserva as posições, camadas, objetos e colisões dos tiles usados. O PNG compacto mantém os pixels originais e adiciona uma borda extrudada de 1 px, com margem de 1 px e espaçamento de 2 px entre tiles, para evitar linhas de amostragem nas bordas durante a renderização. Os GIDs e os IDs locais das colisões são remapeados juntos. O gerador confere o hash dos pixels originais de cada tile antes de substituir os arquivos derivados.

Edite somente o TMJ e o PNG originais no Tiled. Os dois arquivos gerados são derivados e devem ser regenerados após cada edição. O script interrompe a geração se encontrar um formato de dados ou recurso do tileset que ainda não saiba remapear.
