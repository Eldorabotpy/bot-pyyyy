# handlers/guild/upgrades.py
# (VERSÃO FINAL: VISUAL LIMPO, ORGANIZADO E IMERSIVO)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, clan_manager
from modules.game_data.clans import CLAN_PRESTIGE_LEVELS

# --- HELPER VISUAL PARA FORMATAR BUFFS ---
def _format_buffs(buffs):
    """Transforma o dicionário de buffs em texto legível."""
    if not buffs: 
        return "• <i>Nenhum bônus ativo</i>"
    
    lines = []
    # Dicionário para traduzir as chaves técnicas
    names = {
        "xp_bonus": "Bônus de XP",
        "gold_bonus": "Bônus de Ouro",
        "drop_rate": "Sorte de Drop",
        "damage": "Dano em Raids",
        "crafting_speed": "Velocidade de Forja"
    }
    
    for k, v in buffs.items():
        name = names.get(k, k.replace("_", " ").title())
        val = f"+{v}%" if isinstance(v, (int, float)) else v
        lines.append(f"🔹 {name}: <b>{val}</b>")
    
    return "\n".join(lines)

def _bar(current, total, blocks=10):
    """Gera a barra de progresso azul."""
    if total <= 0: return "🟦" * blocks
    ratio = min(1.0, max(0.0, current / total))
    filled = int(ratio * blocks)
    return "🟦" * filled + "⬜" * (blocks - filled)

# ==============================================================================
# MENU DE APRIMORAMENTO
# ==============================================================================
async def show_clan_upgrade_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o menu de aprimoramento usando o renderizador imersivo."""
    query = update.callback_query
    
    # IMPORTAÇÃO TARDIA (Essencial para usar a função do Dashboard sem travar)
    from handlers.guild.dashboard import _render_clan_screen

    user_id = update.effective_user.id
    
    player_data = await player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")
    
    if not clan_id:
        await query.answer("Você não tem um clã!", show_alert=True)
        return
        
    clan_data = await clan_manager.get_clan(clan_id)
    
    # Validação de Líder
    leader_id = int(clan_data.get("leader_id", 0))
    is_leader = (user_id == leader_id)

    if not is_leader:
        await query.answer("Apenas o líder pode gerenciar melhorias.", show_alert=True)
        return
        
    # Dados Atuais
    current_level = clan_data.get("prestige_level", 1)
    current_points = clan_data.get("prestige_points", 0)
    
    current_level_info = CLAN_PRESTIGE_LEVELS.get(current_level, {})
    
    # Dados do Próximo Nível
    next_level_idx = current_level + 1
    next_level_info = CLAN_PRESTIGE_LEVELS.get(next_level_idx)

    # --- MONTAGEM DO TEXTO (LAYOUT) ---
    text = (
        f"✨ <b>CENTRO DE APRIMORAMENTO</b>\n"
        f"Clã: <b>{clan_data.get('display_name')}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏰 <b>Nível Atual: {current_level}</b> - <i>{current_level_info.get('title', 'Iniciante')}</i>\n"
        f"<b>Bônus Atuais:</b>\n"
        f"{_format_buffs(current_level_info.get('buffs', {}))}\n\n"
    )
    
    keyboard = []
    
    # Se existe um próximo nível, mostra os requisitos
    if next_level_info:
        # Pega o XP necessário definido no nível atual para passar pro próximo
        points_needed = current_level_info.get("points_to_next_level", 999999)
        
        # Barra de Progresso
        prog_bar = _bar(current_points, points_needed)
        
        # Custos
        upgrade_cost = next_level_info.get("upgrade_cost", {})
        cost_gold = upgrade_cost.get("gold", 0)
        cost_dimas = upgrade_cost.get("dimas", 0)
        
        text += (
            f"🚀 <b>Rumo ao Nível {next_level_idx}:</b>\n"
            f"XP: <code>[{prog_bar}]</code> {current_points}/{points_needed}\n\n"
            f"🎁 <b>Novos Benefícios:</b>\n"
            f"👥 Membros: <b>{next_level_info.get('max_members', 0)}</b>\n"
            f"{_format_buffs(next_level_info.get('buffs', {}))}\n\n"
            f"💰 <b>Custo da Evolução:</b>\n"
            f"   🪙 {cost_gold:,} Ouro\n"
            f"   💎 {cost_dimas:,} Diamantes\n"
        )
        
        # Botões de Ação (Só aparecem se tiver XP suficiente)
        if current_points >= points_needed:
            text += "\n✅ <b>XP Alcançado!</b> Escolha como pagar a taxa:"
            keyboard.append([InlineKeyboardButton(f"Pagar 🪙 {cost_gold:,} Ouro", callback_data='clan_upgrade_confirm:gold')])
            keyboard.append([InlineKeyboardButton(f"Pagar 💎 {cost_dimas:,} Dimas", callback_data='clan_upgrade_confirm:dimas')])
        else:
            remaining = points_needed - current_points
            text += f"\n🔒 <i>Complete missões para ganhar +{remaining} XP.</i>"

    else:
        text += "\n🌟 <b>NÍVEL MÁXIMO ATINGIDO!</b>\nSeu clã alcançou o ápice do poder."

    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data='clan_menu')])
    
    # --- RENDERIZAÇÃO IMERSIVA ---
    # Mantém o logo do clã, sem piscar a tela
    await _render_clan_screen(update, context, clan_data, text, keyboard)


# ==============================================================================
# CALLBACK DE CONFIRMAÇÃO
# ==============================================================================
async def confirm_clan_upgrade_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa o pagamento e a evolução."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    player_data = await player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")
    payment_method = query.data.split(':')[1]
    
    try:
        # Tenta subir de nível (o clan_manager vai descontar o XP e o Ouro)
        await clan_manager.level_up_clan(clan_id, user_id, payment_method)
        
        # Se não deu erro, sucesso!
        clan_data = await clan_manager.get_clan(clan_id)
        new_level = clan_data.get("prestige_level")
        
        await query.answer(f"🎉 SUCESSO! Clã nível {new_level}!", show_alert=True)
        
        # Recarrega a tela para mostrar os novos status
        await show_clan_upgrade_menu(update, context)

    except ValueError as e:
        await query.answer(f"❌ {str(e)}", show_alert=True)
    except Exception as e:
        await query.answer("Erro técnico ao evoluir.", show_alert=True)

# --- HANDLERS EXPORTADOS ---
clan_upgrade_menu_handler = CallbackQueryHandler(show_clan_upgrade_menu, pattern=r'^clan_upgrade_menu$')
clan_upgrade_confirm_handler = CallbackQueryHandler(confirm_clan_upgrade_callback, pattern=r'^clan_upgrade_confirm:(gold|dimas)$')