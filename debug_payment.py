# debug_payment.py
import pymongo
import certifi

# Sua string de conexão configurada
MONGO_STR = "mongodb+srv://eldora-cluster:pb060987@cluster0.4iqgjaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

print("🔄 Conectando ao MongoDB...")

try:
    client = pymongo.MongoClient(MONGO_STR, tlsCAFile=certifi.where())
    # Força um teste de conexão
    client.admin.command('ping')
    print("✅ Conexão estabelecida com sucesso!")
    
    db = client["eldora_db"]
    col_players = db["players"]

    # O ID do vendedor que vimos no seu print
    TARGET_ID_INT = 7913385053
    TARGET_ID_STR = "7913385053"

    print(f"\n--- RASTREANDO VENDEDOR: {TARGET_ID_INT} ---")

    # 1. Procura por 'id' numérico
    p1 = col_players.find_one({"id": TARGET_ID_INT})
    if p1:
        print(f"✅ ENCONTRADO! O campo é 'id' (Número). Ouro atual: {p1.get('gold')}")
    else:
        print(f"❌ Não encontrado por 'id' numérico.")

    # 2. Procura por 'id' string
    p2 = col_players.find_one({"id": TARGET_ID_STR})
    if p2:
        print(f"✅ ENCONTRADO! O campo é 'id' (Texto). Ouro atual: {p2.get('gold')}")
    else:
        print(f"❌ Não encontrado por 'id' texto.")

    # 3. Procura por '_id' numérico
    p3 = col_players.find_one({"_id": TARGET_ID_INT})
    if p3:
        print(f"✅ ENCONTRADO! O campo é '_id' (Número). Ouro atual: {p3.get('gold')}")
    else:
        print(f"❌ Não encontrado por '_id' numérico.")

    # 4. Procura por '_id' string
    p4 = col_players.find_one({"_id": TARGET_ID_STR})
    if p4:
        print(f"✅ ENCONTRADO! O campo é '_id' (Texto). Ouro atual: {p4.get('gold')}")
    else:
        print(f"❌ Não encontrado por '_id' texto.")

    print("---------------------------------------------")

except Exception as e:
    print(f"\n🔥 ERRO DE CONEXÃO: {e}")