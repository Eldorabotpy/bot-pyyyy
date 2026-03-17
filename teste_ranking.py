from pymongo import MongoClient

# Sua string de conexão (Mantenha isso em segredo no futuro!)
MONGO_URI = "mongodb+srv://eldora-cluster:pb060987@cluster0.4iqgjaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

def testar_ranking():
    print("Conectando ao banco de dados do Eldora...")
    
    try:
        # Conecta ao MongoDB
        client = MongoClient(MONGO_URI)
        
        # Acessa o banco e a coleção exata do seu projeto
        db = client['eldora_db']
        users_collection = db['users']
        
        print("Conexão bem-sucedida! Buscando os top 10 jogadores...")
        print("-" * 30)
        
        # Busca os jogadores, ordena pelo 'level' do maior para o menor (-1) e pega os 10 primeiros
        top_jogadores = users_collection.find(
            {}, 
            {"character_name": 1, "level": 1, "_id": 0} 
        ).sort("level", -1).limit(10)
        
        # Mostra o resultado na tela do terminal
        posicao = 1
        for jogador in top_jogadores:
            nome = jogador.get("character_name", "Desconhecido")
            nivel = jogador.get("level", 0)
            print(f"#{posicao} - {nome} (Lvl: {nivel})")
            posicao += 1
            
        print("-" * 30)
        print("Teste finalizado com sucesso!")
        
    except Exception as e:
        print(f"Ocorreu um erro ao conectar: {e}")

if __name__ == "__main__":
    testar_ranking()