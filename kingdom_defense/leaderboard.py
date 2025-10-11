# Arquivo: kingdom_defense/leaderboard.py

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
        print(f"Erro ao salvar o leaderboard: {e}")

def update_top_score(user_id: int, character_name: str, damage: int):
    """Verifica se um novo recorde foi estabelecido e o salva."""
    leaderboard = _load_leaderboard()
    top_score = leaderboard.get("top_damage_record", {})
    
    # Se o novo dano for maior que o recorde anterior, atualiza
    if damage > top_score.get("damage", 0):
        new_record = {
            "user_id": user_id,
            "character_name": character_name,
            "damage": damage,
            "set_on": datetime.date.today().isoformat()
        }
        leaderboard["top_damage_record"] = new_record
        _save_leaderboard(leaderboard)
        print(f"NOVO RECORDE DE DANO ESTABELECIDO: {character_name} com {damage} de dano!")

def get_top_score_text() -> str:
    print("\n--- [DEBUG LEITURA] Buscando recorde para o menu do reino...")
    leaderboard = _load_leaderboard()
    print(f"--- [DEBUG LEITURA] 1. JSON carregado: {leaderboard}")
    top_score = leaderboard.get("top_damage_record")
    if not top_score or not top_score.get("character_name"):
        print("--- [DEBUG LEITURA] 2. Nenhum recorde válido encontrado.")
        return "" 
    name = top_score['character_name']
    damage = top_score.get('damage', 0)
    print(f"--- [DEBUG LEITURA] 2. Recorde encontrado: {name} com {damage} de dano.")
    return f"\n🏆 𝗥𝗲𝗰𝗼𝗿𝗱𝗶𝘀𝘁𝗮 𝗱𝗲 𝗗𝗮𝗻𝗼: <b>{name}</b> ({damage:,}) 🏆"