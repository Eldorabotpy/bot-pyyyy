# Em pvp/pvp_utils.py

import unicodedata
import re
from modules import file_ids
from .pvp_config import ELO_THRESHOLDS, ELO_DISPLAY


# --- FERRAMENTAS DE TEXTO ---

def _slugify(text: str) -> str:
    if not text: return ""
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    norm = re.sub(r"\s+", "_", norm.strip().lower())
    return re.sub(r"[^a-z0-9_]", "", norm)

# --- FERRAMENTAS DE MÍDIA ---

def get_player_class_media(player_data: dict):
    """Busca a mídia (foto/vídeo) da classe de um jogador."""
    raw_cls = (player_data.get("class") or "").strip()
    cls = _slugify(raw_cls)
    candidates = [f"classe_{cls}_media", f"class_{cls}_media", f"{cls}_media", "personagem_video"]
    for key in candidates:
        fd = file_ids.get_file_data(key)
        if fd and fd.get("id"):
            return fd
    return None

# --- FERRAMENTAS DE LÓGICA DE JOGO (PvP) ---

def get_player_elo(player_points: int) -> str:
    """
    Determina o nome do Elo de um jogador com base em seus pontos,
    usando as regras do pvp_config.py.
    """
    elo_name = "Bronze" # Elo padrão se não atingir nenhum
    
    # Itera sobre os Elos definidos no config, do maior para o menor
    for name, threshold in sorted(ELO_THRESHOLDS.items(), key=lambda item: item[1], reverse=True):
        if player_points >= threshold:
            elo_name = name
            break # Para no primeiro que encontrar (o mais alto)
            
    return elo_name

def get_player_elo_details(points: int) -> tuple[str, str]:
    """Retorna o nome interno do Elo E o nome de exibição."""
    current_elo = "Bronze" # Elo padrão
    # Ordena os limites do maior para o menor para facilitar a verificação
    sorted_thresholds = sorted(ELO_THRESHOLDS.items(), key=lambda item: item[1], reverse=True)

    for elo_name, min_points in sorted_thresholds:
        if points >= min_points:
            current_elo = elo_name
            break # Encontrou o Elo correto

    # Pega o nome de exibição (ex: "🥉 Bronze")
    display_name = ELO_DISPLAY.get(current_elo, current_elo) # Usa o nome interno como fallback

    return current_elo, display_name