# modules/dungeons/registry.py
# ARQUIVO LIMPO E REFATORADO
# Agora ele apenas aponta para as definições corretas em regions.py
from __future__ import annotations
from modules.dungeons.regions import REGIONAL_DUNGEONS

def get_dungeon_for_region(region_key: str) -> dict | None:
    """
    Retorna a configuração do calabouço buscando diretamente do regions.py.
    Mantém a compatibilidade com sistemas antigos que chamam esta função.
    """
    # Verifica se existe no novo sistema
    dungeon_def = REGIONAL_DUNGEONS.get(region_key)
    
    if not dungeon_def:
        return None
        
    # Adaptador simples caso algum código legado espere chaves antigas
    # O regions.py usa "gold_base", o antigo usava "final_gold" dict.
    # Se necessário, o código que CHAMA esta função deve ser atualizado,
    # mas retornamos o dict do regions.py puro aqui.
    return dungeon_def