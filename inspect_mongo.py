import pymongo
from pprint import pprint
import os

# --- Configurações (VERIFICADAS COM A IMAGEM) ---

# URI do MongoDB (Usando a string anterior)
# ATENÇÃO: Contém credenciais. Recomenda-se usar variáveis de ambiente no futuro.
MONGO_URI = "mongodb+srv://eldora-cluster:pb060987@cluster0.4iqgjaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

DB_NAME = "eldora_db"          # Confirmado pela imagem
COLLECTION_NAME = "jogadores"  # Confirmado pela imagem
USER_ID_FIELD = "_id"          # Confirmado pela imagem (assumindo que _id guarda o ID do Telegram)

# Lista dos IDs que queres inspecionar
IDS_PARA_INSPECIONAR = [7262799478, 1160420540] # Mantive os IDs do log anterior

# --- Fim das Configurações ---

client = None

try:
    print(f"Tentando conectar ao cluster MongoDB Atlas...")
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print("Conexão ao MongoDB Atlas bem-sucedida!")

    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    print(f"Acedendo à coleção: '{COLLECTION_NAME}' na base de dados '{DB_NAME}'")

    for user_id_to_find in IDS_PARA_INSPECIONAR:
        print(f"\n--- Procurando por {USER_ID_FIELD} = {user_id_to_find} ---")
        
        # <<< IMPORTANTE: O filtro agora usa USER_ID_FIELD (que é '_id') >>>
        query_filter = {USER_ID_FIELD: user_id_to_find} 
        document = collection.find_one(query_filter)
        
        if document:
            print(f"Documento encontrado para {user_id_to_find}:")
            if isinstance(document, dict):
                pprint(document)
            else:
                # Se for só um número ou outro tipo, indica corrupção
                print(f"CONTEÚDO NÃO É UM DICIONÁRIO (Possivelmente Corrompido): {repr(document)}")
        else:
            print(f"Nenhum documento encontrado para {USER_ID_FIELD} = {user_id_to_find}")

except pymongo.errors.ConfigurationError as e:
    print(f"\nErro de Configuração: Verifique a sua MONGO_URI. Detalhes: {e}")
except pymongo.errors.OperationFailure as e:
     print(f"\nErro de Operação (Autenticação?): Verifique usuário/senha ou permissões. Detalhes: {e}")
except pymongo.errors.ConnectionFailure as e:
    print(f"\nErro de Conexão: Não foi possível conectar ao servidor MongoDB Atlas. Verifique a URI, firewall ou estado do cluster. Detalhes: {e}")
except Exception as e:
    print(f"\nOcorreu um erro inesperado: {type(e).__name__} - {e}")

finally:
    if client:
        client.close()
        print("\nConexão fechada.")