import pymongo
from pymongo import MongoClient

# ============================================================================
# ⚙️ CONFIGURAÇÃO
# ============================================================================
MONGO_URI = "mongodb+srv://eldora-cluster:pb060987@cluster0.4iqgjaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "eldora_db"
COLLECTION_NAME = "players"

def final_cleanup():
    print("🔌 Conectando ao MongoDB...")
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        col = db[COLLECTION_NAME]
        print(f"✅ Conectado a {DB_NAME}.{COLLECTION_NAME}")
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return

    print("\n🧹 INICIANDO LIMPEZA PESADA...")
    
    cursor = col.find({"inventory": {"$exists": True}})
    
    players_fixed = 0
    total_items_fixed = 0

    for player in cursor:
        user_id = player.get("user_id") or player.get("_id")
        inventory = player.get("inventory", {})
        
        if not inventory: continue

        changed = False
        
        # Lista de chaves atuais para iterar com segurança
        current_keys = list(inventory.keys())

        for key in current_keys:
            # ---------------------------------------------------------
            # 1. CORREÇÃO DE ID (tomo_tomo_ -> tomo_)
            # ---------------------------------------------------------
            if key.startswith("tomo_tomo_"):
                # Pega os dados do item ruim
                bad_item = inventory[key]
                qty = 0
                if isinstance(bad_item, dict):
                    qty = int(bad_item.get("quantity", 1))
                else:
                    qty = int(bad_item)

                # Define o ID bom
                good_key = key.replace("tomo_tomo_", "tomo_", 1)

                # Mescla ou Cria
                if good_key in inventory:
                    # Se já tem o bom, soma a quantidade
                    if isinstance(inventory[good_key], dict):
                        inventory[good_key]["quantity"] = int(inventory[good_key].get("quantity", 1)) + qty
                    else:
                        inventory[good_key] = int(inventory[good_key]) + qty
                else:
                    # Se não tem, transfere
                    inventory[good_key] = bad_item
                
                # Apaga o ruim
                del inventory[key]
                
                # Atualiza a referência para limpar o nome no passo 2
                target_key_for_name_fix = good_key
                changed = True
                total_items_fixed += 1
                print(f"   [ID FIX] Jogador {user_id}: {key} -> {good_key}")
            else:
                target_key_for_name_fix = key

            # ---------------------------------------------------------
            # 2. LIMPEZA DE NOME (Remove nomes salvos "Tomo Tomo...")
            # ---------------------------------------------------------
            # Verifica se o item (agora com ID certo) tem nome bugado
            if target_key_for_name_fix in inventory:
                item_data = inventory[target_key_for_name_fix]
                
                # Só mexe se for dicionário (item único/equipamento) e for um Tomo
                if isinstance(item_data, dict) and "tomo_" in target_key_for_name_fix:
                    cleaned_name = False
                    
                    # Lista de campos de nome para verificar
                    for name_field in ["display_name", "name", "custom_name"]:
                        if name_field in item_data:
                            nome_atual = str(item_data[name_field])
                            # Se o nome começar com "Tomo Tomo", deleta o campo
                            if "Tomo Tomo" in nome_atual or "tomo_tomo" in nome_atual:
                                del item_data[name_field]
                                cleaned_name = True
                    
                    if cleaned_name:
                        changed = True
                        print(f"   [NAME FIX] Jogador {user_id}: Nomes resetados em {target_key_for_name_fix}")

        # Salva se houve mudança
        if changed:
            col.update_one({"_id": player["_id"]}, {"$set": {"inventory": inventory}})
            players_fixed += 1

    print("\n" + "="*40)
    print(f"✅ LIMPEZA CONCLUÍDA")
    print(f"👥 Jogadores tocados: {players_fixed}")
    print(f"📚 Itens ajustados: {total_items_fixed}")
    print("="*40)

if __name__ == "__main__":
    confirm = input("Digite 'S' para rodar a Limpeza Pesada no banco eldora_db: ")
    if confirm.lower() == 's':
        final_cleanup()