# modules/database.py
# Centraliza a conexão para todo o bot usar (Mongo Atlas ou Mongita em DEV)

from __future__ import annotations

import os
import logging
import pymongo
import certifi

logger = logging.getLogger(__name__)

# --- Globais Exportáveis ---
client = None
db = None
players_col = None
clans_col = None  # necessário para clãs/guerras

# Configuração
BOT_MODE = os.environ.get("BOT_MODE", "prod").lower()
MONGO_CONNECTION_STRING = os.environ.get("MONGO_CONNECTION_STRING")


def _get_mongo_uri_fallback() -> str | None:
    try:
        import config

        for name in ("MONGO_CONNECTION_STRING", "MONGO_URL", "MONGO_STR"):
            val = getattr(config, name, None)
            if isinstance(val, str) and val.strip():
                return val.strip()
    except Exception:
        pass
    return None



def initialize_database() -> None:
    global client, db, players_col, clans_col, MONGO_CONNECTION_STRING

    # Idempotente (não reabre conexão)
    if db is not None:
        return

    if BOT_MODE == "dev":
        # === MODO LOCAL (MONGITA) ===
        logger.warning("⚠️ MODO DEV: Usando Mongita (Disco Local).")
        try:
            from mongita import MongitaClientDisk
            client = MongitaClientDisk(host="./.local_db_data")
            db = client.get_database("eldora_test_db")
            logger.info("✅ Mongita conectado (eldora_test_db).")
        except ImportError:
            logger.error("❌ Erro: Instale o mongita (pip install mongita) ou mude para PROD.")
            return
        except Exception as e:
            logger.exception(f"❌ Falha ao iniciar Mongita: {e}")
            return

    else:
        # === MODO PROD (ATLAS) ===
        if not MONGO_CONNECTION_STRING:
            # fallback para config.MONGO_STR (ambiente local)
            MONGO_CONNECTION_STRING = _get_mongo_uri_fallback()

        if not MONGO_CONNECTION_STRING:
            logger.error(
                "❌ CRÍTICO: MONGO_CONNECTION_STRING ausente e config.MONGO_STR não encontrado.\n"
                "Defina a variável de ambiente MONGO_CONNECTION_STRING (Render) ou MONGO_STR no config.py (local)."
            )
            return

        try:
            ca = certifi.where()
            client = pymongo.MongoClient(MONGO_CONNECTION_STRING, tlsCAFile=ca)
            client.admin.command("ping")  # Teste rápido
            db = client.get_database("eldora_db")
            logger.info("✅ MongoDB Atlas conectado (eldora_db).")
        except Exception as e:
            logger.exception(f"❌ Falha ao conectar no MongoDB: {e}")
            return

    # Define as coleções
    try:
        players_col = db.get_collection("players")
        clans_col = db.get_collection("clans")

        # Índices (não críticos)
        try:
            players_col.create_index("character_name_normalized")
        except Exception:
            pass

    except Exception as e:
        logger.exception(f"❌ Falha ao preparar coleções: {e}")
        return


# Inicializa ao importar (mantém seu comportamento atual)
initialize_database()
