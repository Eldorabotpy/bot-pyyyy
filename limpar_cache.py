import os
import glob

def limpar_cache():
    # Lista de padrões de arquivos que costumam guardar o cache do bot
    padroes = [
        "job_queue_data*",    # Pega job_queue_data e job_queue_data.pickle
        "user_data*",         # Pega user_data e user_data.pickle
        "bot_data*",          # Pega bot_data e bot_data.pickle
        "conversationbot*",   # Pega conversationbot e conversationbot.pickle
        "*.pickle"            # Pega qualquer arquivo pickle solto
    ]

    print(f"📂 Procurando arquivos de cache em: {os.getcwd()}")
    encontrados = []

    # 1. Encontrar os arquivos
    for padrao in padroes:
        arquivos = glob.glob(padrao)
        encontrados.extend(arquivos)

    # Remove duplicatas da lista
    encontrados = list(set(encontrados))

    if not encontrados:
        print("✅ Nenhum arquivo de cache antigo encontrado! Sua pasta já está limpa.")
        print("Dica: Se os erros continuarem, verifique se há uma pasta 'cache' ou 'data'.")
        return

    # 2. Apagar os arquivos
    print(f"⚠️ Encontrei {len(encontrados)} arquivos de memória antiga:")
    for arq in encontrados:
        try:
            os.remove(arq)
            print(f"   🗑️ Deletado: {arq}")
        except Exception as e:
            print(f"   ❌ Erro ao deletar {arq}: {e}")

    print("\n✅ Limpeza concluída! Agora inicie o bot com 'python main.py'.")

if __name__ == "__main__":
    limpar_cache()