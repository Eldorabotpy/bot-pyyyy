# modules/database.py
# (NOVO ARQUIVO: Centraliza a conexão para todo o bot usar)

import os
import logging
import pymongo
from pymongo.errors import ConnectionFailure, ConfigurationError
import certifi

logger = logging.getLogger(__name__)

# --- Globais Exportáveis ---
client = None
db = None
players_col = None
clans_col = None # <--- Necessário para as missões de guilda!

# Configuração
BOT_MODE = os.environ.get("BOT_MODE", "prod").lower()
MONGO_CONNECTION_STRING = os.environ.get("MONGO_CONNECTION_STRING")

def initialize_database():
    global client, db, players_col, clans_col

    if BOT_MODE == "dev":
        # === MODO LOCAL (MONGITA) ===
        logger.warning("⚠️ MODO DEV: Usando Mongita (Disco Local).")
        try:
            from mongita import MongitaClientDisk
            client = MongitaClientDisk(host="./.local_db_data")
            db = client.get_database("eldora_test_db")
            logger.info("✅ Mongita conectado.")
        except ImportError:
            logger.error("❌ Erro: Instale o mongita (pip install mongita) ou mude para PROD.")
            return
    else:
        # === MODO PROD (ATLAS) ===
        if not MONGO_CONNECTION_STRING:
            logger.error("❌ CRÍTICO: MONGO_CONNECTION_STRING ausente.")
            return
        
        try:
            ca = certifi.where()
            client = pymongo.MongoClient(MONGO_CONNECTION_STRING, tlsCAFile=ca)
            client.admin.command('ping') # Teste
            db = client.get_database("eldora_db")
            logger.info("✅ MongoDB Atlas conectado.")
        except Exception as e:
            logger.exception(f"❌ Falha ao conectar no MongoDB: {e}")
            return

    # Define as coleções
    if db is not None:
        players_col = db.get_collection("players")
        clans_col = db.get_collection("clans")
        
        # Índices
        try:
            players_col.create_index("character_name_normalized")
            # clans_col.create_index("name") # Exemplo futuro
        except Exception:
            pass

# Inicializa ao importar
initialize_database()