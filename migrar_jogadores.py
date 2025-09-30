# migrar_jogadores.py

import os
import json
import pymongo
from dotenv import load_dotenv
import logging

# Configuração do logging para ver o que está a acontecer
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def migrar():
    """
    Lê os ficheiros .json da pasta 'players' e insere/atualiza os dados
    na coleção 'players' do MongoDB Atlas.
    """
    # 1. Carrega as variáveis de ambiente (o nosso ficheiro .env)
    load_dotenv()
    MONGO_CONNECTION_STRING = os.environ.get("MONGO_CONNECTION_STRING")
    
    if not MONGO_CONNECTION_STRING:
        logging.error("CRÍTICO: A variável MONGO_CONNECTION_STRING não foi encontrada no ficheiro .env!")
        return

    # Define o caminho para a pasta dos jogadores antigos
    PASTA_JOGADORES = "players"
    if not os.path.isdir(PASTA_JOGADORES):
        logging.error(f"A pasta '{PASTA_JOGADORES}' não foi encontrada. Não há nada para migrar.")
        return

    client = None
    try:
        # 2. Conecta-se ao MongoDB Atlas
        logging.info("A conectar ao MongoDB Atlas...")
        client = pymongo.MongoClient(MONGO_CONNECTION_STRING)
        client.admin.command('ping')
        db = client.get_database("eldora_db")
        players_collection = db.get_collection("players")
        logging.info("✅ Conexão estabelecida com sucesso!")

        # 3. Itera sobre os ficheiros .json e faz a migração
        logging.info(f"A iniciar a migração da pasta '{PASTA_JOGADORES}'...")
        total_migrados = 0
        for filename in os.listdir(PASTA_JOGADORES):
            if filename.endswith(".json"):
                file_path = os.path.join(PASTA_JOGADORES, filename)
                try:
                    # Extrai o user_id do nome do ficheiro
                    user_id = int(filename.replace(".json", ""))

                    # Lê os dados do ficheiro JSON
                    with open(file_path, 'r', encoding='utf-8') as f:
                        player_data = json.load(f)

                    # Prepara os dados para o MongoDB
                    # O campo principal no Mongo é o `_id`
                    player_data['_id'] = user_id
                    
                    # Adiciona o campo de busca normalizado que criámos
                    if "character_name" in player_data:
                         player_data["character_name_normalized"] = str(player_data["character_name"]).strip().lower()

                    # Usa replace_one com upsert=True.
                    # Isto vai ATUALIZAR o jogador se ele já existir, ou INSERIR se for novo.
                    # É mais seguro do que insert_one, pois pode executar o script várias vezes.
                    players_collection.replace_one({'_id': user_id}, player_data, upsert=True)
                    logging.info(f"✔️ Jogador {user_id} migrado/atualizado com sucesso.")
                    total_migrados += 1

                except Exception as e:
                    logging.error(f"❌ Falha ao migrar o ficheiro {filename}: {e}")
        
        logging.info(f"\n🎉 Migração concluída! Total de {total_migrados} jogadores processados.")

    except Exception as e:
        logging.error(f"Ocorreu um erro crítico durante o processo de migração: {e}")
    finally:
        if client:
            client.close()
            logging.info("Conexão com o MongoDB fechada.")

if __name__ == "__main__":
    migrar()