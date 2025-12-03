# Arquivo: handlers/admin/admin_tools.py
import os
from telegram import Update
from telegram.ext import ContextTypes
from pymongo import MongoClient

# Tenta pegar a conexão das variáveis de ambiente ou usa a string direta (Cuidado com a senha!)
MONGO_URI = os.getenv("MONGO_CONNECTION_STRING")
# Se a variável de ambiente não funcionar, descomente a linha abaixo e coloque sua string:
# MONGO_URI = "mongodb+srv://eldora-cluster:SUA_SENHA@cluster0.4iqgjaf.mongodb.net/?..."

client = MongoClient(MONGO_URI)
db = client["eldora"] # Confirme se o nome do banco é "eldora"

# ID do Admin Supremo (Para segurança)
ADMIN_ID = 7262799478

async def cmd_trocar_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Sem permissão.")
        return

    try:
        args = context.args
        if len(args) != 2:
            raise ValueError
        
        id_antigo = int(args[0])
        id_novo = int(args[1])
        
        col_users = db["users"]
        
        # LISTA DE COLEÇÕES PARA ATUALIZAR (Adicione as suas aqui)
        referencias = [
            {"col": "inventory", "campo": "user_id"},
            {"col": "pets", "campo": "owner_id"},
            {"col": "quests", "campo": "player_id"},
            {"col": "clan_members", "campo": "member_id"}
        ]

        if not col_users.find_one({"_id": id_antigo}):
            await update.message.reply_text("❌ ID antigo não encontrado.")
            return

        if col_users.find_one({"_id": id_novo}):
            await update.message.reply_text("❌ ID novo já existe.")
            return

        # 1. Clona
        jogador = col_users.find_one({"_id": id_antigo})
        jogador["_id"] = id_novo
        col_users.insert_one(jogador)

        # 2. Atualiza Referências
        count = 0
        for ref in referencias:
            res = db[ref["col"]].update_many(
                {ref["campo"]: id_antigo},
                {"$set": {ref["campo"]: id_novo}}
            )
            count += res.modified_count

        # 3. Deleta Antigo
        col_users.delete_one({"_id": id_antigo})

        await update.message.reply_text(f"✅ Feito! ID trocado de {id_antigo} para {id_novo}.\nItens/Refs atualizados: {count}")

    except Exception as e:
        await update.message.reply_text(f"Erro: {e}")