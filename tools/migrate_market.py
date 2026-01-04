# tools/migrate_market_v4.py
# (VERSÃO COM FEEDBACK VISUAL)

import asyncio
from pymongo import MongoClient
import certifi
import sys

# Configuração
MONGO_STR = "mongodb+srv://eldora-cluster:pb060987@cluster0.4iqgjaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "eldora_db"
MARKET_COL_NAME = "market_listings" 

def migrate_market_visual():
    print(f"🛒 INICIANDO MIGRAÇÃO DO MERCADO (Alvo: {MARKET_COL_NAME})...\n")
    
    try:
        client = MongoClient(MONGO_STR, tlsCAFile=certifi.where())
        db = client[DB_NAME]
        
        market_col = db[MARKET_COL_NAME]
        users_col = db["users"]
        
        count_items = market_col.count_documents({})
        print(f"✅ Coleção encontrada com {count_items} itens listados.")

        # 1. Mapeamento
        print("\n1️⃣ Mapeando usuários migrados...")
        users_cursor = users_col.find({"telegram_id_owner": {"$exists": True}})
        
        migration_map = {}
        for user in users_cursor:
            old_id = user.get("telegram_id_owner")
            new_id = str(user.get("_id"))
            if old_id:
                migration_map[int(old_id)] = new_id
                
        print(f"✅ {len(migration_map)} usuários mapeados.")

        # 2. Migração com Progresso
        print("\n2️⃣ Migrando itens (Aguarde o contador)...")
        
        all_items = market_col.find({})
        total_checked = 0
        items_updated = 0
        
        for item in all_items:
            total_checked += 1
            
            # Feedback visual a cada 10 itens para não travar a tela
            if total_checked % 10 == 0:
                sys.stdout.write(f"\r⏳ Processando item {total_checked}/{count_items}...")
                sys.stdout.flush()

            seller_id = item.get("seller_id")
            
            # Validações
            if not seller_id: continue
            if isinstance(seller_id, str) and len(seller_id) > 20: continue

            try:
                seller_id_int = int(seller_id)
            except:
                continue 

            # Verifica dono
            if seller_id_int in migration_map:
                new_seller_id_str = migration_map[seller_id_int]
                
                market_col.update_one(
                    {"_id": item["_id"]},
                    {"$set": {"seller_id": new_seller_id_str}}
                )
                items_updated += 1

        print(f"\r✅ Processamento finalizado! {total_checked}/{count_items} verificados.      ") # Limpa a linha

        print("\n" + "="*40)
        print(f"📊 RESUMO FINAL:")
        print(f"   Itens Atualizados: {items_updated}")
        print("="*40)
        
        if items_updated > 0:
            print("🎉 SUCESSO! O mercado foi atualizado.")
        else:
            print("⚠️ Nenhum item precisou de atualização (todos já estão migrados ou donos não migraram).")

    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")

if __name__ == "__main__":
    migrate_market_visual()