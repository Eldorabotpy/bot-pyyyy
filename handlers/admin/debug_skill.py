# handlers/admin/debug_skill.py
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from modules import player_manager
from modules.game_data.skills import SKILL_DATA
from modules.game_data import items
from config import ADMIN_ID # Ou sua lista de admins
from modules.auth_utils import get_current_player_id
async def cmd_give_test_skill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando para testar o drop de skills.
    Uso: /test_skill <id_da_skill>
    Exemplo: /test_skill guerreiro_corte_perfurante
    """
    user_id = get_current_player_id(update, context)
    
    # Validação simples de Admin
    # (Adicione sua verificação real aqui se tiver uma lista)
    if str(user_id) != str(ADMIN_ID): 
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "⚠️ <b>Uso:</b> <code>/test_skill id_da_skill</code>\n"
            "Ex: <code>/test_skill guerreiro_corte_perfurante</code>",
            parse_mode="HTML"
        )
        return

    skill_id = args[0]

    # 1. Verifica se a skill existe
    if skill_id not in SKILL_DATA:
        await update.message.reply_text(f"❌ Skill <code>{skill_id}</code> não encontrada no skills.py.", parse_mode="HTML")
        return

    # 2. Simula a conversão do Boss (Skill -> Tomo)
    # O items.py gera com prefixo "tomo_"
    tomo_id = f"tomo_{skill_id}"
    
    # 3. Verifica se o Tomo foi gerado corretamente
    item_info = items.ITEMS_DATA.get(tomo_id)
    if not item_info:
        await update.message.reply_text(f"❌ Erro: O item <code>{tomo_id}</code> não existe no items.py. Reinicie o bot.", parse_mode="HTML")
        return

    # 4. Entrega o item
    pdata = await player_manager.get_player_data(user_id)
    player_manager.add_item_to_inventory(pdata, tomo_id, 1)
    await player_manager.save_player_data(user_id, pdata)

    display_name = item_info.get("display_name", tomo_id)
    
    await update.message.reply_text(
        f"✅ <b>Item Recebido!</b>\n"
        f"Você recebeu: <b>{display_name}</b>\n"
        f"🆔 Item: <code>{tomo_id}</code>\n"
        f"🆔 Skill: <code>{skill_id}</code>\n\n"
        f"👉 Vá no Inventário > Aprendizado e tente usar.",
        parse_mode="HTML"
    )

# Cria o handler para exportar
debug_skill_handler = CommandHandler("test_skill", cmd_give_test_skill)