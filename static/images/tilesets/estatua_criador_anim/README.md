# Animações da estátua do criador

Faixas de quatro quadros transparentes para tilesets animados do Tiled. Cada quadro mede **192×256 px**, equivalente a **6×8 tiles** no mapa de 32×32 px.

## Arquivos

- `cristal_mana_rotacao.png` / `.tsx`: cristal de mana gira sobre o pedestal (720 ms por ciclo).
- `estatua_ergue_teclado.png` / `.tsx`: estátua levanta o teclado e retorna, com pausa no alto (1.4 s por ciclo).
- `animacoes.json`: ordem e duração dos quadros.

Abra os arquivos `.tsx` no Tiled ou importe-os como tilesets. Use o tile animado de ID 0. As imagens têm quatro quadros em uma linha; cada célula é 192×256 px.

O Tiled repete animações de tiles continuamente. Para tocar a elevação do teclado uma única vez e manter a estátua erguida, o jogo precisa disparar os quadros por código/evento e parar no quadro 3.
