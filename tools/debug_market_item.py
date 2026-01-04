# tools/debug_market_item.py
from pymongo import MongoClient
import certifi

MONGO_STR = "mongodb+srv://eldora-cluster:pb060987@cluster0.4iqgjaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

def investigar():
    print("🕵️  DETETIVE DE MERCADO\n")
    
    try:
        client = MongoClient(MONGO_STR, tlsCAFile=certifi.where())
        db = client["eldora_db"]
        market_col = db["market_listings"]
        users_col = db["users"]

        # 1. Pega os 5 primeiros itens que ainda têm ID numérico (não migrados)
        print("🔍 Analisando itens antigos no mercado...")
        
        # Busca itens onde seller_id é numérico ou string numérica
        itens_antigos = []
        for item in market_col.find({}):
            sid = item.get("seller_id")
            # Verifica se parece um ID antigo (número)
            if isinstance(sid, int) or (isinstance(sid, str) and sid.isdigit() and len(sid) < 15):
                itens_antigos.append(item)
                if len(itens_antigos) >= 5: break
        
        if not itens_antigos:
            print("✅ Nenhum item com ID antigo encontrado! O mercado parece já estar todo migrado.")
            return

        print(f"⚠️ Encontrados {len(itens_antigos)} exemplos de itens não migrados.")
        
        for item in itens_antigos:
            seller_id = item.get("seller_id")
            nome_item = item.get("item_id", "Desconhecido")
            print(f"\n📦 Item: {nome_item} | Vendedor ID: {seller_id} (Tipo: {type(seller_id).__name__})")
            
            # Tenta achar esse dono na tabela de usuários novos
            # O campo 'telegram_id_owner' guarda o ID antigo
            dono_novo = users_col.find_one({"telegram_id_owner": int(seller_id)})
            
            if dono_novo:
                print(f"   ✅ DONO ENCONTRADO! O usuário migrou.")
                print(f"      Novo ID: {dono_novo.get('_id')}")
                print(f"      Nome: {dono_novo.get('character_name')}")
                print(f"      ERRO: O script de migração deveria ter pego este aqui.")
            else:
                print(f"   ❌ DONO NÃO ENCONTRADO.")
                print(f"      O jogador do ID {seller_id} ainda não fez a migração (ou criou conta do zero).")
                print(f"      O item ficará preso até ele usar a opção 'Resgatar Conta'.")

    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    investigar()