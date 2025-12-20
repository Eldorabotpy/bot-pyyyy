# Arquivo: modules/cooldowns.py

from modules.game_data.skills import SKILL_DATA

def iniciar_turno(player):
    """
    Reduz os contadores de cooldown de todas as skills do jogador.
    Retorna o jogador atualizado e uma lista de mensagens (skills que ficaram prontas).
    """
    if "cooldowns" not in player:
        player["cooldowns"] = {}

    cooldowns_atuais = player["cooldowns"]
    novos_cooldowns = {}
    msgs = []

    for skill_id, turnos in cooldowns_atuais.items():
        # Garante que é inteiro
        try:
            t = int(turnos)
        except (ValueError, TypeError):
            t = 0
            
        if t > 1:
            # Se faltam mais de 1 turno, reduz e mantém
            novos_cooldowns[skill_id] = t - 1
        else:
            # Se chegou a 1 ou menos, a skill fica pronta (remove da lista)
            skill_info = SKILL_DATA.get(skill_id, {})
            skill_nome = skill_info.get("display_name", skill_id)
            msgs.append(f"✨ **{skill_nome}** está pronta!")
        
    player["cooldowns"] = novos_cooldowns
    return player, msgs

def verificar_cooldown(player, skill_id):
    """
    Verifica se uma skill pode ser usada.
    Retorna (True, "Ok") ou (False, "Mensagem de erro").
    """
    cooldowns = player.get("cooldowns", {})
    try:
        turnos_restantes = int(cooldowns.get(skill_id, 0))
    except (ValueError, TypeError):
        turnos_restantes = 0
        
    if turnos_restantes > 0:
        return False, f"⏳ Aguarde {turnos_restantes} turno(s)!"
    return True, "Ok"

def aplicar_cooldown(player, skill_id, raridade="comum"):
    """
    Aplica o tempo de recarga a uma skill baseada na sua raridade.
    Procura o valor em 'rarity_effects' ou usa o padrão da skill.
    """
    skill_info = SKILL_DATA.get(skill_id)
    if not skill_info: 
        return player

    # 1. Tenta pegar a configuração específica da raridade
    rarity_data = skill_info.get('rarity_effects', {}).get(raridade, {})
    
    # Procura 'cooldown_turns' direto na raridade OU dentro de 'effects' (para compatibilidade)
    tempo_recarga = rarity_data.get('cooldown_turns')
    if tempo_recarga is None:
        tempo_recarga = rarity_data.get('effects', {}).get('cooldown_turns')

    # 2. Se não achou na raridade específica, tenta na raridade "comum" (fallback)
    if tempo_recarga is None:
        common_data = skill_info.get('rarity_effects', {}).get('comum', {})
        tempo_recarga = common_data.get('cooldown_turns')
    
    # 3. Se ainda for None, tenta na raiz da skill (valor base)
    if tempo_recarga is None:
        tempo_recarga = skill_info.get('cooldown_turns', 0)

    # Converte para int e aplica
    try:
        tempo_recarga = int(tempo_recarga)
    except:
        tempo_recarga = 0

    if tempo_recarga > 0:
        if "cooldowns" not in player: 
            player["cooldowns"] = {}
        player["cooldowns"][skill_id] = tempo_recarga
        
    return player