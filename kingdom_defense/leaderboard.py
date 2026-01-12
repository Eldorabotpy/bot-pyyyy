import json
from pathlib import Path
import datetime

# O arquivo que vai guardar nosso recorde
LEADERBOARD_FILE = Path(__file__).parent / "kd_leaderboard.json"

def _load_leaderboard() -> dict:
    """Carrega os dados do recorde do arquivo JSON."""
    if not LEADERBOARD_FILE.exists():
        return {}
    try:
        return json.loads(LEADERBOARD_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return {}

def _save_leaderboard(data: dict):
    """Salva os dados do recorde no arquivo JSON."""
    try:
        LEADERBOARD_FILE.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
    except IOError as e:
        print(f"Erro crítico ao salvar leaderboard: {e}")

# MUDANÇA: user_id agora é str (ObjectId)
def update_top_score(user_id: str, character_name: str, damage: int):
    """
    Salva o MVP do evento atual.
    """
    leaderboard = _load_leaderboard()
    
    # Cria o registro do novo vencedor
    new_record = {
        "user_id": str(user_id), # Garante string
        "character_name": character_name,
        "damage": damage,
        "set_on": datetime.date.today().isoformat()
    }
    
    # Atualiza e salva
    leaderboard["top_damage_record"] = new_record
    _save_leaderboard(leaderboard)

def get_top_score_text() -> str:
    """
    Retorna apenas o nome e o dano formatado para o Menu do Reino.
    """
    leaderboard = _load_leaderboard()
    top_score = leaderboard.get("top_damage_record")
    
    if not top_score or not top_score.get("character_name"):
        return "" 
        
    name = top_score['character_name']
    damage = top_score.get('damage', 0)
    
    return f"<b>{name}</b> ({damage:,}) 🏆"