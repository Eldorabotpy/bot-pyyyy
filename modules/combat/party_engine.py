# modules/combat/party_engine.py

import random

def calculate_heal_amount(caster_stats, target_max_hp, effect_data):
    """Calcula o valor numérico da cura/recuperação."""
    amount = 0
    
    # Cura baseada em % do HP Máximo do alvo (Ex: Guerreiro/Tanque)
    if "amount_percent_max_hp" in effect_data:
        pct = float(effect_data["amount_percent_max_hp"])
        amount = int(target_max_hp * pct)
        
    # Cura baseada em Atributo Mágico (Ex: Mago/Curandeiro)
    elif effect_data.get("heal_type") == "magic_attack":
        magic_atk = caster_stats.get("magic_attack", caster_stats.get("attack", 10))
        scale = float(effect_data.get("heal_scale", 1.0))
        amount = int(magic_atk * scale)
        
    # Cura fixa (Ex: Poção em área)
    elif "amount_flat" in effect_data:
        amount = int(effect_data["amount_flat"])

    return amount

def process_party_effects(caster_id, caster_name, skill_data, caster_stats, all_active_states):
    """
    Aplica efeitos de grupo em uma lista de estados de jogadores.
    
    Args:
        caster_id: ID de quem usou.
        caster_name: Nome de quem usou.
        skill_data: Dicionário da skill (SKILL_DATA).
        caster_stats: Stats totais do caster (para calcular força da skill).
        all_active_states: Dict {user_id: state} contendo hp, max_hp, log, etc.
    
    Returns:
        logs (list): Lista de logs para quem usou a skill.
    """
    logs = []
    effects = skill_data.get("effects", {})
    affected_count = 0
    
    # Itera sobre todos os aliados (incluindo o próprio caster se a skill permitir)
    # Nota: No World Boss, all_active_states é o self.player_states
    
    # 1. CURA EM ÁREA (party_heal)
    if "party_heal" in effects:
        heal_def = effects["party_heal"]
        
        for pid, state in all_active_states.items():
            if state['hp'] <= 0: continue # Não cura mortos
            
            # Calcula cura específica para este alvo (pois pode depender do Max HP dele)
            heal_val = calculate_heal_amount(caster_stats, state['max_hp'], heal_def)
            
            if heal_val > 0:
                old_hp = state['hp']
                state['hp'] = min(state['max_hp'], state['hp'] + heal_val)
                real_heal = state['hp'] - old_hp
                
                if real_heal > 0:
                    affected_count += 1
                    # Log para o aliado (se não for o próprio caster)
                    if pid != caster_id:
                        current_log = state.get('log', '')
                        state['log'] = current_log + f"\n💚 {caster_name} te curou (+{real_heal})"

        if affected_count > 0:
            logs.append(f"💚 𝐂𝐮𝐫𝐚 𝐞𝐦 𝐆𝐫𝐮𝐩𝐨: {affected_count} aliados recuperados.")

    # 2. RECUPERAÇÃO DE MANA EM ÁREA (party_mana) - Ex: Bardos
    if "party_mana" in effects:
        mana_def = effects["party_mana"]
        affected_count = 0
        
        for pid, state in all_active_states.items():
            if state['hp'] <= 0: continue
            
            # Lógica simples para mana (geralmente fixo ou % do max)
            val = 0
            if "amount_flat" in mana_def: val = int(mana_def["amount_flat"])
            
            if val > 0:
                state['mp'] = min(state['max_mp'], state['mp'] + val)
                affected_count += 1
                if pid != caster_id:
                    state['log'] = state.get('log', '') + f"\n💙 {caster_name} restaurou sua Mana (+{val})"

        if affected_count > 0:
            logs.append(f"💙 𝐌𝐚𝐧𝐚 𝐞𝐦 𝐆𝐫𝐮𝐩𝐨: {affected_count} aliados recuperados.")

    # 3. BUFFS DE STATUS (Guerreiro Defense, etc)
    # Nota: Como o World Boss Engine atual só salva HP/MP, buffs temporários
    # precisariam de um sistema de 'turns_left'. 
    # Por enquanto, podemos simular buffs como "Escudo" (Cura temporária) ou implementar no futuro.
    if "party_buff" in effects:
        # Aqui você implementaria lógica se o engine suportasse buffs temporários
        # Ex: state['temp_defense_bonus'] = 50
        logs.append("🛡️ Buff de grupo aplicado (Efeito visual).")

    return logs