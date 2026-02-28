# modules/events/catacumbas/utils.py
import re
from modules.effects import engine as effects_engine

def clean_md(text: str) -> str:
    """Garante que o texto não quebre o Markdown do Telegram."""
    if not text: return ""
    # Remove caracteres que costumam causar 'Can't find end of entity'
    return text.replace("_", " ").replace("*", "").replace("`", "").replace("[", "(").replace("]", ")")

def get_hp_bar(current: int, max_val: int, length: int = 10) -> str:
    """Gera uma barra de vida visual (ex: 🟩🟩🟩⬜⬜)"""
    if max_val <= 0: max_val = 1
    pct = current / max_val
    
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
    Gera o texto principal da tela de combate com suporte à Engine de Efeitos.
    Blindado contra erros de formatação Markdown.
    """
    # 1. Cabeçalho
    floor = session.get("current_floor", 1)
    total_floors = session.get("total_floors", 5)
    scaling = session.get("scaling_factor", 1.0)
    raid_id = session.get("raid_id", "???")
    
    text = f"🏰 **As Catacumbas Reais** (Sala: `{raid_id}`)\n"
    text += f"📍 Andar {floor}/{total_floors} | ⚖️ Escalonamento: {scaling}x\n\n"
    
    # ==========================================================
    # 2. STATUS DO MONSTRO / BOSS
    # ==========================================================
    boss = session.get("boss")
    if boss:
        nome_monstro = clean_md(boss.get("name", "Monstro"))
        icone = "👑" if boss.get("is_boss") else "👹"
        
        hp = int(boss.get("current_hp", 0))
        max_hp = int(boss.get("hp_max", boss.get("max_hp", 100)))
        
        text += f"{icone} **{nome_monstro}**\n"
        
        if hp <= 0:
            text += "💀 **DERROTADO**\n"
        else:
            hp_bar = get_hp_bar(hp, max_hp, length=10)
            text += f"❤️ Vida: {hp_bar} {hp}/{max_hp}\n"
            text += f"⚔️ ATK: {boss.get('attack', 0)} | 🛡️ DEF: {boss.get('defense', 0)}\n"
            
            # EXIBIÇÃO DE EFEITOS ATIVOS (Engine)
            try:
                # Usa a lógica interna da engine para recuperar instâncias ativas
                active_effects = effects_engine._ensure_effects(boss)
                if active_effects:
                    eff_list = []
                    for e in active_effects:
                        # Limpa o ID do efeito para não quebrar o MD (ex: 'stun_effect' -> 'Stun Effect')
                        name = clean_md(e.effect_id.replace("_", " ").title())
                        stacks = f" x{e.stacks}" if e.stacks > 1 else ""
                        eff_list.append(f"{name}{stacks}")
                    
                    if eff_list:
                        text += f"💫 Efeitos: _{', '.join(eff_list)}_\n"
            except: pass
                
    text += "\n"
    
    # ==========================================================
    # 3. STATUS DO GRUPO (JOGADORES)
    # ==========================================================
    text += "👥 **Esquadrão:**\n"
    for pid, pdata in all_players_data.items():
        # Nome blindado contra caracteres especiais
        raw_name = pdata.get("name") or pdata.get("username", "Desconhecido")
        name = clean_md(raw_name)
        
        level = pdata.get("level", 1)
        classe = clean_md(pdata.get("class", "Novato")).capitalize()

        hp = int(pdata.get("current_hp", 0))
        max_hp = int(pdata.get("hp_max", pdata.get("max_hp", 100)))

        marker = "👤" if str(pid) == str(user_id) else "🛡️"
        
        if hp <= 0:
            text += f"{marker} ~Lv.{level} {name}~ 💀 **MORTO**\n"
        else:
            # Check de Atordoamento via Engine
            status_icon = ""
            if not effects_engine.can_act(pdata):
                status_icon = " 💫"

            hp_bar = get_hp_bar(hp, max_hp, length=6)
            text += f"{marker} **Lv.{level} {name}** ({classe}){status_icon}\n"
            text += f"   ❤️ {hp_bar} {hp}/{max_hp} HP\n"
            
    text += "\n"
    
    # ==========================================================
    # 4. LOG DE COMBATE (Últimos Eventos)
    # ==========================================================
    turn_log = session.get("turn_log", [])
    if turn_log:
        text += "📜 **Últimos Eventos:**\n"
        # Mostra apenas as últimas 5 linhas e escapa caracteres de MD em cada uma
        recent_logs = turn_log[-5:]
        for line in recent_logs:
            # Escapa manualmente o underscore para evitar erro de itálico não fechado
            safe_line = line.replace("_", "\\_")
            text += f"• {safe_line}\n"

    return text
