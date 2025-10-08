import os

def listar_estrutura(diretorio_inicial, prefixo="", ignorar=None):
    if ignorar is None:
        ignorar = set()

    itens = sorted(os.listdir(diretorio_inicial))
    for i, item in enumerate(itens):
        if item in ignorar:
            continue

        caminho_completo = os.path.join(diretorio_inicial, item)
        e_ultimo = (i == len(itens) - 1)

        print(prefixo + ("└── " if e_ultimo else "├── ") + item)

        if os.path.isdir(caminho_completo):
            novo_prefixo = prefixo + ("    " if e_ultimo else "│   ")
            listar_estrutura(caminho_completo, novo_prefixo, ignorar)

# --- CONFIGURAÇÃO ---
PASTA_RAIZ = "."  # Ponto significa o diretório atual
PASTAS_A_IGNORAR = {"venv", "__pycache__", ".git", ".vscode"}

print(f"{os.path.basename(os.path.abspath(PASTA_RAIZ))}/")
listar_estrutura(PASTA_RAIZ, ignorar=PASTAS_A_IGNORAR)