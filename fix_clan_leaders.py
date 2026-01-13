# fix_clan_leaders.py
# (VERSÃO CORRIGIDA: Resolve conflito de update no MongoDB)

import os
import logging
from pymongo import MongoClient
import certifi

# Configuração de Log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Conexão MongoDB
MONGO_STR = "mongodb+srv://eldora-cluster:pb060987@cluster0.4iqgjaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

def run_fix():
    try:
        client = MongoClient(MONGO_STR, tlsCAFile=certifi.where())
        db = client["eldora_db"]
        clans_col = db["clans"]
        users_col = db["users"]
        
        logger.info("🚀 Iniciando correção de líderes de clã...")
        
        all_clans = list(clans_col.find({}))
        logger.info(f"Encontrados {len(all_clans)} clãs.")
        
        fixed_count = 0
        skipped_count = 0
        
        for clan in all_clans:
            clan_id = clan["_id"]
            clan_name = clan.get("display_name", clan.get("name"))
            current_leader = clan.get("leader_id")
            
            # --- CASO 1: LÍDER É INTEIRO (LEGADO) ---
            if isinstance(current_leader, int) or (isinstance(current_leader, str) and current_leader.isdigit()):
                old_id = int(current_leader)
                logger.info(f"🔍 Clã '{clan_name}' (Líder {old_id}). Buscando novo usuário...")
                
                # Busca usuário novo
                new_user = users_col.find_one({
                    "$or": [
                        {"telegram_id_owner": old_id},
                        {"telegram_id": old_id}
                    ]
                })
                
                if new_user:
                    new_id_str = str(new_user["_id"])
                    logger.info(f"✅ Usuário encontrado! Novo ID: {new_id_str}")
                    
                    # ETAPA 1: Adiciona o novo ID e Define o Líder (Sem remover ainda)
                    clans_col.update_one(
                        {"_id": clan_id},
                        {
                            "$set": {"leader_id": new_id_str},
                            "$addToSet": {"members": new_id_str} 
                        }
                    )

                    # ETAPA 2: Remove o ID antigo (Em operação separada para evitar conflito code 40)
                    clans_col.update_one(
                        {"_id": clan_id},
                        {"$pull": {"members": old_id}}
                    )
                    
                    # Atualiza o Jogador
                    users_col.update_one(
                        {"_id": new_user["_id"]},
                        {"$set": {"clan_id": clan_id}}
                    )
                    
                    fixed_count += 1
                else:
                    logger.warning(f"⚠️ Usuário {old_id} ainda não migrou.")
                    skipped_count += 1
            
            # --- CASO 2: LIMPEZA DE MEMBROS ANTIGOS ---
            # Mesmo que o líder já esteja certo, pode haver membros antigos (int) na lista
            members = clan.get("members", [])
            integers_in_members = [m for m in members if isinstance(m, int)]
            
            if integers_in_members:
                logger.info(f"🧹 Limpando {len(integers_in_members)} membros legados em '{clan_name}'...")
                for old_m in integers_in_members:
                    # Tenta achar quem é e converter
                    u = users_col.find_one({"telegram_id_owner": old_m})
                    
                    # Remove o int (Separado)
                    clans_col.update_one({"_id": clan_id}, {"$pull": {"members": old_m}})
                    
                    if u:
                        nid = str(u["_id"])
                        # Adiciona o str (Separado)
                        clans_col.update_one({"_id": clan_id}, {"$addToSet": {"members": nid}})
                        # Vincula
                        users_col.update_one({"_id": u["_id"]}, {"$set": {"clan_id": clan_id}})

        logger.info("="*40)
        logger.info(f"🏁 CONCLUÍDO!")
        logger.info(f"✅ Clãs corrigidos: {fixed_count}")
        logger.info("="*40)

    except Exception as e:
        logger.error(f"Erro no script: {e}")

if __name__ == "__main__":
    run_fix()