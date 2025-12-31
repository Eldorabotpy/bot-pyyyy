# fix_duplicate_vips.py
import asyncio
import os
from collections import defaultdict

# --- 1. FORÇA O CARREGAMENTO DO .ENV ---
try:
    from dotenv import load_dotenv
    load_dotenv() # Lê o arquivo .env para pegar o MONGO_CONNECTION_STRING
    print("✅ Variáveis de ambiente carregadas.")
except ImportError:
    print("⚠️ Aviso: 'python-dotenv' não encontrado. Se der erro de conexão, instale com: pip install python-dotenv")

# --- 2. AGORA IMPORTA O BANCO ---
try:
    # Importa o DB direto para garantir
    from modules.database import db
    
    # Tenta pegar a collection. Se o core.py falhar, pegamos direto do db
    try:
        from modules.player.core import users_collection
    except ImportError:
        if db is not None:
            print("⚠️ 'core.py' não exportou users_collection, pegando direto do DB...")
            users_collection = db["users"]
        else:
            raise Exception("Objeto 'db' é None.")
            
except Exception as e:
    print("\n" + "="*50)
    print(f"❌ ERRO CRÍTICO DE CONEXÃO: {e}")
    print("Verifique se o MONGO_CONNECTION_STRING está correto no arquivo .env")
    print("="*50 + "\n")
    exit()

# --- 3. LÓGICA DO SCRIPT ---
async def clean_duplicate_vips():
    print("🕵️‍♂️ Iniciando detetive de VIPs duplicados...")

    if users_collection is None:
        print("❌ Erro: Não foi possível acessar a coleção de usuários.")
        return

    # Pega TODOS os usuários que NÃO são free
    cursor = users_collection.find({"premium_tier": {"$ne": "free"}})
    
    owners_map = defaultdict(list)
    total_checked = 0
    
    # Agrupa por dono
    for user_doc in cursor:
        tg_id = user_doc.get("telegram_id_owner")
        if tg_id:
            owners_map[tg_id].append(user_doc)
            total_checked += 1

    print(f"📊 Analisando {total_checked} contas VIP encontradas...")
    
    fixed_count = 0

    for tg_id, accounts in owners_map.items():
        if len(accounts) > 1:
            # Ordena por XP (Maior XP primeiro)
            accounts.sort(key=lambda x: int(x.get("xp", 0)), reverse=True)
            
            main_account = accounts[0]
            clones = accounts[1:]
            
            print(f"\n👤 Dono ID {tg_id} tem {len(accounts)} contas VIP.")
            print(f"   👑 Mantendo VIP na principal: {main_account.get('username')} (XP: {main_account.get('xp', 0)})")
            
            for clone in clones:
                print(f"   ❌ Removendo VIP da secundária: {clone.get('username')} (XP: {clone.get('xp', 0)})")
                
                users_collection.update_one(
                    {"_id": clone["_id"]},
                    {
                        "$set": {
                            "premium_tier": "free",
                            "premium_expires_at": None
                        }
                    }
                )
                fixed_count += 1
    
    print("\n" + "="*40)
    print(f"✅ LIMPEZA CONCLUÍDA!")
    print(f"📉 Total de contas corrigidas para Free: {fixed_count}")
    print("="*40)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(clean_duplicate_vips())