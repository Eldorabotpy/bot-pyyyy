# Em pvp/pvp_utils.py

import unicodedata
import re
from modules import file_ids

# Importamos nossas regras de Elo do arquivo de configuração
from .pvp_config import ELO_THRESHOLDS

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