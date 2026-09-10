# limpar_inventarios.py
from modules.player.core import users_collection

def padronizar_todos_os_inventarios():
    print("🧹 Iniciando a grande faxina de inventários...")
    
    # Busca todos os jogadores direto da coleção OFICIAL do seu jogo
    jogadores = users_collection.find({})
    jogadores_atualizados = 0

    for player in jogadores:
        inventario_atual = player.get("inventory", {})
        inventario_novo = {}
        precisa_atualizar = False

        if isinstance(inventario_atual, dict):
            for item_id, dados in inventario_atual.items():
                
                # SE FOR O PADRÃO ANTIGO (Apenas um número ou float solto)
                if isinstance(dados, int) or isinstance(dados, float):
                    inventario_novo[item_id] = {
                        "base_id": item_id,
                        "quantity": int(dados)
                    }
                    precisa_atualizar = True
                
                # SE JÁ FOR O PADRÃO NOVO, SÓ COPIA MANTENDO SEGURO
                elif isinstance(dados, dict):
                    inventario_novo[item_id] = dados
        
        # Se encontrou sujeira e limpou, salva no banco de dados
        if precisa_atualizar:
            users_collection.update_one(
                {"_id": player["_id"]},
                {"$set": {"inventory": inventario_novo}}
            )
            jogadores_atualizados += 1
            print(f"✔️ Inventário de '{player.get('username', 'Desconhecido')}' padronizado!")

    print(f"\n✨ Faxina concluída! {jogadores_atualizados} jogadores tiveram o inventário corrigido.")

if __name__ == "__main__":
    padronizar_todos_os_inventarios()