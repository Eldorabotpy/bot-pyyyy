# handlers/guild/upgrades.py
# (VERSÃO CORRIGIDA: UI RENDERER + SEM DEPENDÊNCIA CIRCULAR)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, clan_manager, file_ids
from modules.game_data.clans import CLAN_PRESTIGE_LEVELS
from modules.auth_utils import get_current_player_id
from ui.ui_renderer import render_photo_or_text

# ==============================================================================
# HELPERS VISUAIS
# ==============================================================================

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
        "crafting_speed": "Velocidade de Forja",
        "member_cap": "Capacidade de Membros"
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

def _pick_upgrade_media(clan_data):
    """
    Tenta pegar uma imagem de 'Clan Hall' ou 'Castelo' para ilustrar a evolução.
    Se não tiver, usa o logo do clã.
    """
    # 1. Tenta imagem de upgrade/hall
    try:
        fid = file_ids.get_file_id("img_clan_hall")
        if fid: return fid
    except: pass

    # 2. Logo do Clã
    if clan_data and clan_data.get("logo_media_key"):
        return clan_data.get("logo_media_key")
    
    # 3. Fallback
    try:
        return file_ids.get_file_id("img_clan_default")
    except:
        return None

async def _render_upgrade_screen(update, context, clan_data, text, keyboard):
    """Renderiza a tela usando o sistema unificado UI Renderer."""
    media_id = _pick_upgrade_media(clan_data)
    
    await render_photo_or_text(
        update,
        context,
        text=text,
        photo_file_id=media_id,
        reply_markup=InlineKeyboardMarkup(keyboard),
        scope="clan_upgrade_screen", 
        parse_mode="HTML",
        allow_edit=True
    )

# ==============================================================================
# MENU DE APRIMORAMENTO
# ==============================================================================
async def show_clan_upgrade_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o menu de aprimoramento usando o renderizador imersivo."""
    query = update.callback_query
    
    user_id = get_current_player_id(update, context)
    if not user_id: return # Auth handler trata
    
    player_data = await player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")
    
    if not clan_id:
        if query: await query.answer("Você não tem um clã!", show_alert=True)
        return
        
    clan_data = await clan_manager.get_clan(clan_id)
    
    # Validação de Líder
    leader_id = str(clan_data.get("leader_id", 0))
    is_leader = (str(user_id) == leader_id)

    # Nota: Permitimos que membros vejam a tela, mas apenas líder vê botões de ação
    
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
        
        # Botões de Ação (Só aparecem se tiver XP suficiente E for Líder)
        if current_points >= points_needed:
            if is_leader:
                text += "\n✅ <b>XP Alcançado!</b> Escolha como pagar a taxa:"
                keyboard.append([InlineKeyboardButton(f"Pagar 🪙 {cost_gold:,} Ouro", callback_data='clan_upgrade_confirm:gold')])
                keyboard.append([InlineKeyboardButton(f"Pagar 💎 {cost_dimas:,} Dimas", callback_data='clan_upgrade_confirm:dimas')])
            else:
                 text += "\n⚠️ <i>Apenas o Líder pode realizar a evolução.</i>"
        else:
            remaining = points_needed - current_points
            text += f"\n🔒 <i>Complete missões e guerras para ganhar +{remaining} XP.</i>"

    else:
        text += "\n🌟 <b>NÍVEL MÁXIMO ATINGIDO!</b>\nSeu clã alcançou o ápice do poder."

    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data='clan_menu')])
    
    # --- RENDERIZAÇÃO IMERSIVA ---
    await _render_upgrade_screen(update, context, clan_data, text, keyboard)


# ==============================================================================
# CALLBACK DE CONFIRMAÇÃO
# ==============================================================================
async def confirm_clan_upgrade_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa o pagamento e a evolução."""
    query = update.callback_query
    user_id = get_current_player_id(update, context)
    
    player_data = await player_manager.get_player_data(user_id)
    clan_id = player_data.get("clan_id")
    
    # Validação extra de segurança
    if not clan_id: return
    clan_data = await clan_manager.get_clan(clan_id)
    if str(clan_data.get("leader_id")) != str(user_id):
        await query.answer("Apenas o líder pode fazer isso.", show_alert=True)
        return

    try:
        payment_method = query.data.split(':')[1]
    except:
        return

    try:
        # Tenta subir de nível (o clan_manager deve ter a lógica de descontar o XP e o Ouro)
        await clan_manager.level_up_clan(clan_id, user_id, payment_method)
        
        # Se não deu erro, sucesso!
        clan_data = await clan_manager.get_clan(clan_id) # Recarrega dados atualizados
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