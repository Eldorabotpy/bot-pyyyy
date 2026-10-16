# Em pvp/pvp_utils.py

import unicodedata
import re
import math
from .pvp_config import ELO_THRESHOLDS, ELO_DISPLAY


# --- FERRAMENTAS DE TEXTO ---

def _slugify(text: str) -> str:
    if not text:
        return ""
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    norm = re.sub(r"\s+", "_", norm.strip().lower())
    return re.sub(r"[^a-z0-9_]", "", norm)


# --- FERRAMENTAS DE MÍDIA ---

def get_player_class_media(player_data: dict):
    """
    Busca a mídia (foto/vídeo) da classe de um jogador.

    Regra:
    - Se o personagem tiver classe (class_key ou class), tenta buscar a mídia da classe.
    - Se não encontrar (ou não tiver classe), retorna SEMPRE 'classe_default_media' (fallback obrigatório).
    - Se o catálogo opcional de mídia não existir, retorna None sem quebrar o Elo.
    """
    # O módulo de mídia é opcional neste checkout e não deve impedir o uso
    # das funções de Elo deste arquivo.
    try:
        from modules import file_ids
    except ImportError:
        return None

    # Aceita 'class_key' (novo) ou 'class' (legado)
    raw_cls = (player_data.get("class_key") or player_data.get("class") or "").strip()
    cls = _slugify(raw_cls)

    candidates = []

    # Tentativas pela classe (se houver)
    if cls:
        candidates.extend([
            f"classe_{cls}_media",
            f"class_{cls}_media",
            f"{cls}_media",
        ])

    # Mantém compatibilidade com chave antiga/geral (se existir no seu file_ids)
    candidates.append("personagem_video")

    # Fallback obrigatório exigido por você
    candidates.append("classe_default_media")

    for key in candidates:
        fd = file_ids.get_file_data(key)
        # no seu projeto, às vezes vem "id" e às vezes "file_id"/"file"
        if fd and (fd.get("id") or fd.get("file_id") or fd.get("file")):
            return fd

    return None


# Em pvp/pvp_utils.py

def gerar_barra_hp(atual: int, maximo: int, tamanho: int = 10) -> str:
    """
    Gera uma barra de vida que muda de cor baseada na % restante.
    Ex: 🟩🟩🟩🟩🟩 (100%) -> 🟨🟨🟨⬜⬜ (50%) -> 🟥🟥⬜⬜⬜ (20%)
    """
    if maximo <= 0:
        maximo = 1
    if atual < 0:
        atual = 0
    if atual > maximo:
        atual = maximo

    porcentagem = atual / maximo
    cheios = int(porcentagem * tamanho)
    # Garante pelo menos 1 quadrado se tiver > 0 de vida
    if cheios == 0 and atual > 0:
        cheios = 1

    vazios = tamanho - cheios

    # Lógica de Cores (Paleta Satisfatória)
    if porcentagem > 0.6:     # Acima de 60% = Verde
        bloco = "🟩"
    elif porcentagem > 0.25:  # Entre 25% e 60% = Amarelo/Laranja
        bloco = "🟨"
    else:                     # Abaixo de 25% = Vermelho (Perigo!)
        bloco = "🟥"

    barra = (bloco * cheios) + ("⬜" * vazios)

    # Adiciona a % numérica para ficar mais RPG
    pct_txt = int(porcentagem * 100)
    return f"{barra} {pct_txt}%"


def get_player_elo(player_points: int) -> str:
    """
    Determina o nome do Elo de um jogador
    baseado nos thresholds configurados.
    """
    elo_name = "Bronze"  # Padrão

    # Itera sobre os Elos definidos no config, do maior para o menor
    for name, threshold in sorted(ELO_THRESHOLDS.items(), key=lambda item: item[1], reverse=True):
        if player_points >= threshold:
            elo_name = name
            break  # Para no primeiro que encontrar (o mais alto)

    return elo_name


def get_player_elo_details(points: int) -> tuple[str, str]:
    """Retorna o nome interno do Elo E o nome de exibição."""
    current_elo = "Bronze"  # Elo padrão
    # Ordena os limites do maior para o menor para facilitar a verificação
    sorted_thresholds = sorted(ELO_THRESHOLDS.items(), key=lambda item: item[1], reverse=True)

    for elo_name, min_points in sorted_thresholds:
        if points >= min_points:
            current_elo = elo_name
            break  # Encontrou o Elo correto

    # Pega o nome de exibição (ex: "🥉 Bronze")
    display_name = ELO_DISPLAY.get(current_elo, current_elo)  # Usa o nome interno como fallback

    return current_elo, display_name
