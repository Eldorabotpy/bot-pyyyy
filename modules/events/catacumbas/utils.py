# modules/events/catacumbas/utils.py

def get_hp_bar(current: int, max_val: int, length: int = 10) -> str:
    """Gera uma barra de vida visual (ex: 🟩🟩🟩⬜⬜)"""
    if max_val <= 0: max_val = 1
    pct = current / max_val
    
    # Limita entre 0 e 1
    if pct < 0: pct = 0
    if pct > 1: pct = 1
    
    filled = int(pct * length)
    empty = length - filled
    
    # Cores baseadas na vida
    bar_char = "🟩"
    if pct < 0.5: bar_char = "🟨"
    if pct < 0.2: bar_char = "🟥"
    
    return bar_char * filled + "⬜" * empty

async def format_catacomb_interface(session: dict, user_id: str, all_players_data: dict) -> str:
    """
    Gera o texto principal da tela de combate.
    Mostra: Andar, Boss (HP Bar), Lista de Jogadores e Log de Turnos.
    """
    # 1. Cabeçalho
    floor = session.get("current_floor", 1)
    scaling = session.get("scaling_factor", 1.0)
    raid_id = session.get("raid_id", "???")
    
    text = f"🏰 **CATACUMBAS REAIS** | Andar {floor}\n"
    text += f"💀 Dificuldade: {scaling}x | ID: `{raid_id}`\n"
    text += "─" * 20 + "\n"
    
    # 2. Status do Chefe / Inimigo
    boss = session.get("boss")
    if boss:
        b_name = boss.get("name", "Inimigo")
        b_hp = boss.get("current_hp", 0)
        b_max = boss.get("max_hp", 100)
        b_bar = get_hp_bar(b_hp, b_max, length=12)
        
        # Ícone de status do boss
        b_status = ""
        if boss.get("is_enraged"): b_status = "😡 **ENFURECIDO**"
        if boss.get("is_stunned"): b_status += " 💫 Atordoado"
        
        text += f"👹 **{b_name}** {b_status}\n"
        text += f"{b_bar} `({b_hp}/{b_max})`\n"
        
        # Mostra buffs/debuffs do boss se houver (opcional)
        if "_effects" in boss and boss["_effects"]:
            effects_str = ", ".join([e['name'] for e in boss["_effects"]])
            text += f"💫 Efeitos: _{effects_str}_\n"
            
    text += "\n"
    
    # 3. Status do Grupo
    text += "👥 **Esquadrão:**\n"
    for pid, pdata in all_players_data.items():
        # Nome e HP
        name = pdata.get("name", "Desconhecido")
        # Tenta pegar apelido do telegram se não tiver nome de char
        if name == "Desconhecido" and "username" in pdata:
             name = pdata["username"]

        hp = pdata.get("current_hp", 0)
        # Tenta pegar max_hp (pode não estar atualizado se não recalcular, mas serve para display rápido)
        max_hp = pdata.get("max_hp", 100) 
        if "stats" in pdata and "max_hp" in pdata["stats"]:
            max_hp = pdata["stats"]["max_hp"]

        # Identificador visual para o próprio usuário
        marker = "👤" if str(pid) == str(user_id) else "🛡️"
        
        if hp <= 0:
            text += f"{marker} ~{name}~ 💀 **MORTO**\n"
        else:
            hp_pct = int((hp / max_hp) * 100) if max_hp > 0 else 0
            text += f"{marker} **{name}**: {hp}/{max_hp} ({hp_pct}%)\n"
            
    # 4. Log de Combate (Últimas ações)
    turn_log = session.get("turn_log", [])
    if turn_log:
        text += "\n📜 **Registro de Batalha:**\n"
        # Mostra apenas as últimas 4 linhas para não poluir
        recent_logs = turn_log[-4:]
        for line in recent_logs:
            text += f"• {line}\n"
            
    return text