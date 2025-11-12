# handlers/class_evolution_handler.py
# (VERSÃO NOVA - LÊ O "CAMINHO DA ASCENSÃO")

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

from modules import player_manager
# Importa o NOVO serviço de lógica e o ficheiro de DADOS
from modules import class_evolution_service as evo_service
from modules.game_data import class_evolution as evo_data

logger = logging.getLogger(__name__)

# --- Funções Auxiliares de Formatação ---

def _format_cost_lines(cost: dict) -> str:
    """Formata o custo (itens/gold) para exibição."""
    lines = []
    if not cost:
        return "<i>Sem custo</i>"
        
    if "gold" in cost:
        lines.append(f"  • {cost['gold']:,} 🪙 Ouro")
    
    # Importa os dados dos itens aqui dentro para evitar importação circular
    from modules.game_data import items as game_items
    
    for item_id, qty in cost.items():
        if item_id == "gold":
            continue
        item_info = game_items.ITEMS_DATA.get(item_id, {})
        item_name = item_info.get("display_name", item_id)
        item_emoji = item_info.get("emoji", "💠")
        lines.append(f"  • {item_emoji} {item_name} x{qty}")
        
    return "\n".join(lines)

def _get_player_class_name(pdata: dict) -> str:
    """Pega o nome da classe atual do jogador."""
    class_key = (pdata.get("class") or "N/A").lower()
    
    # Tenta encontrar o nome no T1
    if class_key in evo_data.EVOLUTIONS:
        return class_key.title()
        
    # Tenta encontrar o nome nas evoluções
    evo_def = evo_data.find_evolution_by_target(class_key)
    if evo_def:
        return evo_def.get("to", class_key).title()
        
    return class_key.title()


# ================================================
# HANDLER PRINCIPAL (O MENU DA ÁRVORE)
# ================================================

async def open_evolution_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler principal. Mostra o estado atual da evolução
    e a "Árvore de Ascensão" (Ascension Path).
    """
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        await query.edit_message_text("Erro: Não foi possível carregar seus dados.")
        return

    # 1. Pega o status da evolução (esta é a nova função de LÓGICA)
    status_info = evo_service.get_player_evolution_status(pdata)
    
    current_class_name = _get_player_class_name(pdata)
    level = pdata.get("level", 1)
    
    caption_lines = [
        f"⛩️ <b>Caminho da Ascensão</b> ⛩️",
        f"Classe: {current_class_name} (Nível {level})",
        "---"
    ]
    keyboard = []

    # 2. Analisa o status retornado pelo serviço
    
    # Caso 1: Jogador está no T6 (Tier Máximo)
    if status_info["status"] == "max_tier":
        caption_lines.append("Você atingiu o auge da sua classe.")
        caption_lines.append("Não há mais evoluções disponíveis no momento.")
        
    # Caso 2: Jogador não tem nível suficiente
    elif status_info["status"] == "locked":
        evo_opt = status_info["option"]
        caption_lines.append(f"Próxima Evolução: <b>{evo_opt['to'].title()}</b>")
        caption_lines.append(f"🔒 {status_info['message']}") # Ex: "Requer Nível 25"

    # Caso 3: Jogador está no Caminho da Ascensão (A "ÁRVORE")
    elif status_info["status"] == "path_available":
        evo_opt = status_info["option"]
        target_class = evo_opt['to']
        
        caption_lines.append(f"Próxima Evolução: <b>{target_class.title()}</b>")
        caption_lines.append(f"<i>{evo_opt['desc']}</i>")
        caption_lines.append("\nComplete as tarefas da ascensão:")
        
        # 3a. Desenha a Árvore (os "nós")
        path_nodes = status_info.get("path_nodes", [])
        
        for node in path_nodes:
            if node["status"] == "complete":
                caption_lines.append(f"  ✅ <s>{node['desc']}</s> (Completo)")
            
            elif node["status"] == "available":
                # Este é o próximo nó a ser completado
                caption_lines.append(f"  🔘 <b>{node['desc']}</b>")
                # Adiciona um botão para o jogador ver o custo
                keyboard.append([
                    InlineKeyboardButton(
                        f"Ver Tarefa: {node['desc']}", 
                        callback_data=f"evo_node_info:{node['id']}"
                    )
                ])
                
            elif node["status"] == "locked":
                caption_lines.append(f"  🔒 <i>{node['desc']}</i> (Bloqueado)")

        # 3b. Verifica se a árvore está COMPLETA
        if status_info.get("all_nodes_complete", False):
            caption_lines.append("\n<b>Você completou todas as tarefas!</b>")
            caption_lines.append("O Teste Final está disponível.")
            keyboard.append([
                InlineKeyboardButton(
                    f"⚔️ Tentar o Teste: {target_class.title()}",
                    callback_data=f"evo_start_trial_confirm:{target_class}"
                )
            ])
    
    # (Adicione aqui o fallback para 'required_items' se ainda usar)
    elif status_info["status"] == "trial_ready":
         evo_opt = status_info["option"]
         target_class = evo_opt['to']
         caption_lines.append(f"Próxima Evolução: <b>{target_class.title()}</b>")
         caption_lines.append("Você possui os itens necessários (sistema antigo).")
         keyboard.append([
                InlineKeyboardButton(
                    f"⚔️ Tentar o Teste: {target_class.title()}",
                    callback_data=f"evo_start_trial_confirm:{target_class}"
                )
            ])

    # Botão de Voltar
    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="open_profile_menu")])
    
    try:
        await query.edit_message_text(
            "\n".join(caption_lines),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    except BadRequest as e:
        if "not modified" not in str(e):
            logger.warning(f"Erro ao editar menu de evolução: {e}")


# ================================================
# HANDLERS DA ÁRVORE (NOVOS)
# ================================================

async def show_node_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o custo de um nó (tarefa) da árvore de ascensão."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    try:
        node_id = query.data.split(":", 1)[1]
    except IndexError:
        await query.answer("Erro: ID da tarefa não encontrado.", show_alert=True)
        return

    pdata = await player_manager.get_player_data(user_id)
    status_info = evo_service.get_player_evolution_status(pdata)

    # Encontra o nó específico
    node_to_show = None
    if status_info.get("status") == "path_available":
        for node in status_info.get("path_nodes", []):
            if node["id"] == node_id and node["status"] == "available":
                node_to_show = node
                break
                
    if not node_to_show:
        await query.answer("Esta tarefa não está mais disponível.", show_alert=True)
        await open_evolution_menu(update, context) # Atualiza o menu
        return

    # Mostra o custo
    cost = node_to_show.get("cost", {})
    cost_str = _format_cost_lines(cost)
    
    caption_lines = [
        f"🔘 <b>Tarefa: {node_to_show['desc']}</b>",
        "\nCusto para completar:",
        cost_str
    ]
    
    keyboard = [
        [InlineKeyboardButton(
            f"✅ Completar Tarefa (Gastar Recursos)",
            callback_data=f"evo_complete_node:{node_id}"
        )],
        [InlineKeyboardButton("⬅️ Voltar para a Árvore", callback_data="open_evolution_menu")]
    ]
    
    await query.edit_message_text(
        "\n".join(caption_lines),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def complete_node(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tenta completar (pagar) um nó da árvore de ascensão."""
    query = update.callback_query
    
    try:
        node_id = query.data.split(":", 1)[1]
    except IndexError:
        await query.answer("Erro: ID da tarefa não encontrado.", show_alert=True)
        return

    user_id = query.from_user.id
    
    # Tenta completar o nó (esta função consome itens/ouro)
    success, message = await evo_service.attempt_ascension_node(user_id, node_id)
    
    await query.answer(message, show_alert=True)
    
    # Se conseguiu ou não, sempre atualiza o menu principal para
    # mostrar o novo estado da árvore (ou a mensagem de erro).
    await open_evolution_menu(update, context)


# ================================================
# HANDLERS DO TESTE (TRIAL)
# (Esta lógica provavelmente já existe, mas está aqui para completar)
# ================================================

async def start_trial_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pede confirmação antes de iniciar o teste (e consumir itens, se for o sistema antigo)."""
    query = update.callback_query
    
    try:
        target_class = query.data.split(":", 1)[1]
    except IndexError:
        await query.answer("Erro: Classe alvo não encontrada.", show_alert=True)
        return

    # Pega a definição da evolução
    evo_opt = evo_data.find_evolution_by_target(target_class)
    if not evo_opt:
        await query.answer("Erro: Definição da evolução não encontrada.", show_alert=True)
        return
        
    # Verifica se é sistema antigo (required_items) ou novo (ascension_path)
    cost_str = ""
    if "ascension_path" in evo_opt:
        cost_str = "Seu Caminho da Ascensão está completo."
    elif "required_items" in evo_opt:
        cost_str = "Isto consumirá os seguintes itens:\n"
        cost_str += _format_cost_lines(evo_opt["required_items"])
        
    caption = [
        f"⚔️ <b>Teste de Evolução: {target_class.title()}</b> ⚔️",
        "\nVocê está prestes a enfrentar o teste final.",
        cost_str,
        "\n<b>Esta ação não pode ser desfeita.</b>",
        "Se você falhar, terá que completar o Caminho (ou juntar os itens) novamente.",
        "\nDeseja continuar?"
    ]
    
    keyboard = [
        [InlineKeyboardButton(
            f"Sim, iniciar o Teste!",
            callback_data=f"evo_start_trial_execute:{target_class}"
        )],
        [InlineKeyboardButton("Não, voltar", callback_data="open_evolution_menu")]
    ]
    
    await query.edit_message_text(
        "\n".join(caption),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def start_trial_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia a batalha de provação."""
    query = update.callback_query
    await query.answer("Iniciando o teste...")
    user_id = query.from_user.id

    try:
        target_class = query.data.split(":", 1)[1]
    except IndexError:
        await query.answer("Erro: Classe alvo não encontrada.", show_alert=True)
        return
        
    # 1. Chama o serviço para consumir itens (se houver) e verificar
    result = await evo_service.start_evolution_trial(user_id, target_class)

    if not result.get("success"):
        await query.answer(result.get("message", "Erro desconhecido."), show_alert=True)
        await open_evolution_menu(update, context) # Atualiza o menu
        return

    # 2. Pega o monstro do teste
    monster_id = result.get("trial_monster_id")
    if not monster_id:
        await query.answer("ERRO CRÍTICO: Monstro de teste não definido!", show_alert=True)
        return

    # 3. Importa o motor de dungeon (que sabe como iniciar combates legados)
    from modules.dungeons import runtime as dungeons_runtime
    
    # 4. Inicia o combate
    # (Esta função deve apagar a mensagem atual e enviar a UI de combate)
    await dungeons_runtime.start_evolution_trial_battle(
        update, 
        context, 
        user_id, 
        monster_id,
        target_class # Passa a classe alvo para o 'finalize_evolution' saber
    )
    # ====================================================================
# HANDLERS DE EXPORTAÇÃO (Para serem importados pelo registries/character.py)
# ====================================================================

# Handler para abrir o menu da Árvore de Ascensão
# Esta variável é a que está faltando no seu registry!
status_evolution_open_handler = CallbackQueryHandler(
    open_evolution_menu, 
    pattern=r'^open_evolution_menu$'
)

# Handler para ver a informação/custo de um nó (tarefa)
show_node_info_handler = CallbackQueryHandler(
    show_node_info, 
    pattern=r'^evo_node_info:'
)

# Handler para completar a tarefa (pagar o custo)
complete_node_handler = CallbackQueryHandler(
    complete_node, 
    pattern=r'^evo_complete_node:'
)

# Handler para a tela de confirmação do teste final
start_trial_confirmation_handler = CallbackQueryHandler(
    start_trial_confirmation, 
    pattern=r'^evo_start_trial_confirm:'
)

# Handler para iniciar a execução da batalha
start_trial_execute_handler = CallbackQueryHandler(
    start_trial_execute, 
    pattern=r'^evo_start_trial_execute:'
)