# bot/modules/cooldowns.py
from modules.game_data.skills import SKILL_DATA

def iniciar_turno(player):
    if "cooldowns" not in player:
        player["cooldowns"] = {}

    cooldowns_atuais = player["cooldowns"]
    novos_cooldowns = {}
    msgs = []

    for skill_id, turnos in cooldowns_atuais.items():
        # Converte para inteiro para evitar erro se estiver como texto "1"
        try:
            t = int(turnos)
        except:
            t = 0
            
        if t > 1:
            # Se faltam 2 ou mais, reduz 1 e Mantém na lista
            novos_cooldowns[skill_id] = t - 1
        elif t <= 1:
            # Se é 1 (ou menos), Remove da lista (não adiciona em novos_cooldowns)
            # E avisa o jogador
            skill_info = SKILL_DATA.get(skill_id, {})
            skill_nome = skill_info.get("display_name", skill_id)
            msgs.append(f"✨ **{skill_nome}** está pronta!")
        
    player["cooldowns"] = novos_cooldowns
    return player, msgs

def verificar_cooldown(player, skill_id):
    cooldowns = player.get("cooldowns", {})
    try:
        turnos_restantes = int(cooldowns.get(skill_id, 0))
    except:
        turnos_restantes = 0
        
    if turnos_restantes > 0:
        return False, f"⏳ Aguarde {turnos_restantes} turno(s)!"
    return True, "Ok"

def aplicar_cooldown(player, skill_id, raridade="comum"):
    skill_info = SKILL_DATA.get(skill_id)
    if not skill_info: return player
    try:
        efeitos = skill_info['rarity_effects'].get(raridade, {}).get('effects', {})
        tempo_recarga = efeitos.get('cooldown_turns', 0)
    except:
        tempo_recarga = 0

    if tempo_recarga > 0:
        if "cooldowns" not in player: player["cooldowns"] = {}
        player["cooldowns"][skill_id] = tempo_recarga
    return player