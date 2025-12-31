# Arquivo: destravar_jogador.py
from pymongo import MongoClient
import certifi

# 1. Conexão com seu Banco (Copiado do seu projeto)
MONGO_STR = "mongodb+srv://eldora-cluster:pb060987@cluster0.4iqgjaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

def destravar():
    print("🔄 Conectando ao MongoDB...")
    try:
        # Usa o certifi igual ao seu projeto original
        client = MongoClient(MONGO_STR, tlsCAFile=certifi.where())
        db = client["eldora_db"]
        users_col = db["users"] # Coleção NOVA
        print("✅ Conectado!")
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return

    # 2. Pergunta quem é o jogador travado
    target_user = input("\n👤 Digite o USUÁRIO do jogador (ex: mlvdz12): ").strip().lower()

    # 3. Busca a conta que está atrapalhando (na users)
    conta_bloqueadora = users_col.find_one({"username": target_user})

    if not conta_bloqueadora:
        print(f"❌ Não encontrei nenhum usuário '{target_user}' na coleção NOVA (users).")
        print("Talvez ele já tenha deletado ou o nome está errado.")
        return

    print(f"\n⚠️ ENCONTRADO NA COLEÇÃO NOVA (BLOQUEANDO MIGRAÇÃO):")
    print(f"   ID: {conta_bloqueadora.get('_id')}")
    print(f"   User: {conta_bloqueadora.get('username')}")
    print(f"   Criado em: {conta_bloqueadora.get('created_at')}")
    
    # 4. Confirmação
    confirm = input("\n🗑️ Tem certeza que deseja APAGAR essa conta Nível 1 para liberar a migração? (S/N): ")
    
    if confirm.lower() == 's':
        users_col.delete_one({"_id": conta_bloqueadora["_id"]})
        print(f"\n✅ SUCESSO! A conta nova de '{target_user}' foi removida.")
        print(f"👉 Peça para ele digitar /start no bot agora. O botão de MIGRAR vai aparecer!")
    else:
        print("\nOperação cancelada.")

if __name__ == "__main__":
    destravar()