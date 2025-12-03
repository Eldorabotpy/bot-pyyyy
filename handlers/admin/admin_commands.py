import os
from telegram import Update
from telegram.ext import ContextTypes
from pymongo import MongoClient

# --- CONFIGURAÇÃO DO BANCO ---
# Pega a string de conexão direto das suas variáveis de ambiente ou config
MONGO_URI = "mongodb+srv://eldora-cluster:SUA_SENHA_AQUI@cluster0.4iqgjaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)

# ⚠️ IMPORTANTE: Coloque o nome exato do banco de dados do seu RPG aqui
DB_NAME = "eldora" 
db = client[DB_NAME]

# ID do Admin Principal (O seu ID)
ADMIN_ID = 7262799478

async def cmd_trocar_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando: /trocarid <id_antigo> <id_novo>
    Descrição: Clona o jogador para um novo ID e atualiza referências.
    """
    user = update.effective_user
    
    # 1. Verificação de Segurança (Só você pode usar)
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Acesso negado. Apenas o Admin Supremo pode mexer na matrix.")
        return

    # 2. Validação dos Argumentos
    try:
        args = context.args
        if len(args) != 2:
            raise ValueError
        
        id_antigo = int(args[0])
        id_novo = int(args[1])
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Uso correto: `/trocarid 12345 67890`", parse_mode="Markdown")
        return

    # 3. Definição das Coleções (Tabelas)
    # AJUSTE AQUI: Liste todas as coleções onde o ID do jogador aparece
    col_jogadores = db["users"]  # Coleção principal do char
    
    # Coleções secundárias (inventário, missões, etc)
    # Onde o campo é, por exemplo, "user_id" ou "player_id"
    referencias = [
        {"col": "inventory", "campo": "user_id"},
        {"col": "pets", "campo": "owner_id"},
        {"col": "quests", "campo": "player_id"},
        {"col": "clan_members", "campo": "member_id"} 
    ]

    # 4. Lógica de Troca (Clonar -> Atualizar -> Deletar)
    try:
        # A. Busca o jogador original
        jogador_doc = col_jogadores.find_one({"_id": id_antigo})
        
        if not jogador_doc:
            await update.message.reply_text(f"❌ Erro: Jogador com ID `{id_antigo}` não encontrado no banco.", parse_mode="Markdown")
            return

        # B. Verifica se o novo ID já existe
        if col_jogadores.find_one({"_id": id_novo}):
            await update.message.reply_text(f"❌ Erro: O ID `{id_novo}` já está sendo usado por outra pessoa!", parse_mode="Markdown")
            return

        # C. Clona o documento principal
        jogador_doc["_id"] = id_novo # Troca o ID na memória
        col_jogadores.insert_one(jogador_doc) # Salva como novo documento
        
        # D. Atualiza referências nas outras tabelas
        log_updates = []
        for ref in referencias:
            collection = db[ref["col"]]
            campo = ref["campo"]
            
            # Atualiza todos os itens/pets/quests para o novo ID
            resultado = collection.update_many(
                {campo: id_antigo},
                {"$set": {campo: id_novo}}
            )
            if resultado.modified_count > 0:
                log_updates.append(f"{ref['col']}: {resultado.modified_count} itens movidos")

        # E. Deleta o jogador antigo (Só deleta se tudo acima deu certo)
        col_jogadores.delete_one({"_id": id_antigo})

        # F. Relatório final
        msg = (
            f"✅ **Transplante de Alma Concluído!**\n\n"
            f"👤 **De:** `{id_antigo}`\n"
            f"👤 **Para:** `{id_novo}`\n\n"
            f"📦 **Inventário/Dados migrados:**\n" +
            ("\n".join(log_updates) if log_updates else "Nenhuma referência extra encontrada.")
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"🔥 **Erro Crítico no Banco de Dados:**\n`{str(e)}`", parse_mode="Markdown")