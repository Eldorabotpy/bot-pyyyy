# fix_professions.py
# (VERSÃO INDEPENDENTE: Conecta direto sem depender de modules.database)

import asyncio
import logging
import certifi
from pymongo import MongoClient

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FixProfissao")

# === CONEXÃO DIRETA (Copiada do seu core.py) ===
MONGO_STR = "mongodb+srv://eldora-cluster:pb060987@cluster0.4iqgjaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

def get_users_collection():
    print("🔌 Conectando ao MongoDB...")
    try:
        client = MongoClient(MONGO_STR, tlsCAFile=certifi.where())
        db = client["eldora_db"]
        return db["users"]
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return None

async def fix_all_professions():
    logger.info("Iniciando correção de profissões...")
    
    users_col = get_users_collection()
    if users_col is None:
        return

    # 1. Busca jogadores com o bug (tem 'key' mas não tem 'type')
    query = {
        "profession.key": {"$exists": True},
        "profession.type": {"$exists": False}
    }
    
    # Executa a contagem
    try:
        count = users_col.count_documents(query)
        logger.info(f"🔎 Encontrados {count} jogadores com profissão bugada ('key').")
    except Exception as e:
        logger.error(f"Erro ao buscar: {e}")
        return
    
    if count == 0:
        logger.info("✅ Nenhum reparo necessário.")
        return

    # 2. Busca e Corrige
    cursor = users_col.find(query)
    fixed = 0
    
    # Itera sobre a lista de documentos
    for pdata in cursor:
        uid = pdata["_id"]
        prof_data = pdata.get("profession", {})
        prof_value = prof_data.get("key")
        
        if prof_value:
            # Atualiza: Cria 'type' e remove 'key'
            update_result = users_col.update_one(
                {"_id": uid},
                {
                    "$set": {"profession.type": prof_value},
                    "$unset": {"profession.key": ""}
                }
            )
            
            if update_result.modified_count > 0:
                fixed += 1
                logger.info(f"✅ Corrigido jogador {uid}: {prof_value}")

    logger.info(f"🏁 Finalizado! Total corrigidos: {fixed}/{count}")

if __name__ == "__main__":
    # Roda o script
    asyncio.run(fix_all_professions())