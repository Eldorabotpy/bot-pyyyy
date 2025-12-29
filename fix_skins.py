import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient

# ==============================================================================
# ⚙️ CONFIGURAÇÃO
# ==============================================================================
# URL pega do seu arquivo .env
MONGO_URI = "mongodb+srv://eldora-cluster:pb060987@cluster0.4iqgjaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Mapa de Correções: "ID_ERRADO": "ID_CORRETO"
CORRECOES = {
    "Aprendiz do Santo": "aprendiz_do_santo",
    "espirito_da_rena_dourada": "discipulo_de_nicolau"
}

# ==============================================================================
# 🛠️ LÓGICA DO SCRIPT
# ==============================================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AutoFixer")

async def find_correct_database(client):
    """Procura qual banco de dados tem a coleção 'players' com dados."""
    logger.info("🕵️  Investigando nomes dos bancos de dados...")
    try:
        db_names = await client.list_database_names()
        logger.info(f"📁 Bancos encontrados: {db_names}")
        
        for name in db_names:
            if name in ["admin", "local"]: continue # Pula bancos do sistema
            
            db = client[name]
            count = await db["players"].count_documents({})
            if count > 0:
                logger.info(f"🎉 ENCONTRADO! O banco '{name}' tem {count} jogadores.")
                return name
        return None
    except Exception as e:
        logger.error(f"Erro ao listar bancos: {e}")
        return None

async def fix_skins():
    logger.info("🔌 Conectando ao MongoDB...")
    try:
        client = AsyncIOMotorClient(MONGO_URI)
    except Exception as e:
        logger.error(f"❌ Erro ao conectar: {e}")
        return

    # 1. Descobre o nome do banco automaticamente
    db_name = await find_correct_database(client)
    
    if not db_name:
        logger.error("❌ Não encontrei nenhum banco com jogadores (coleção 'players' vazia em todos).")
        logger.info("Tentando o padrão 'test' por garantia...")
        db_name = "test"

    db = client[db_name]
    collection = db["players"] 

    logger.info(f"🚀 Iniciando correção no banco: '{db_name}'")
    
    # 2. Executa a correção
    query = {
        "unlocked_skins": { "$in": list(CORRECOES.keys()) }
    }
    
    cursor = collection.find(query)
    count = 0
    
    async for player in cursor:
        user_id = player.get("user_id")
        skins = player.get("unlocked_skins", [])
        
        mudou = False
        new_skins = []
        
        for skin in skins:
            if skin in CORRECOES:
                correta = CORRECOES[skin]
                if correta not in skins and correta not in new_skins:
                    new_skins.append(correta)
                    logger.info(f"   🛠️ Corrigindo Jogador {user_id}: '{skin}' -> '{correta}'")
                    mudou = True
                else:
                    logger.info(f"   🗑️ Removendo duplicata quebrada de {user_id}: '{skin}'")
                    mudou = True
            else:
                new_skins.append(skin)
        
        if mudou:
            await collection.update_one(
                {"_id": player["_id"]},
                {"$set": {"unlocked_skins": new_skins}}
            )
            count += 1
            logger.info(f"✅ Jogador {user_id} salvo com sucesso.")

    if count == 0:
        logger.info("✨ Nenhuma conta precisou de correção neste banco.")
    else:
        logger.info(f"🏁 Fim! Total de jogadores corrigidos: {count}")

if __name__ == "__main__":
    try:
        asyncio.run(fix_skins())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Erro fatal: {e}")