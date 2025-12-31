import os

# Configuração
IGNORE_DIRS = {'.venv', '.git', '__pycache__', '.idea', '.vscode'}
OUTPUT_FILE = "relatorio_migracao.txt"

# Padrões que indicam código VELHO (Perigo)
OLD_PATTERNS = [
    "update.effective_user.id",
    "query.from_user.id",
    "message.from_user.id",
    "players_collection.find",
    "players_col.find",
    "user_id: int",
    "user_id : int"
]

# Padrão que indica código NOVO (Seguro)
NEW_PATTERN = "get_current_player_id"

def generate_report():
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write("="*50 + "\n")
        out.write("🔍 RELATÓRIO DE ESTRUTURA E MIGRAÇÃO\n")
        out.write("="*50 + "\n\n")

        # 1. IMPRIMIR ESTRUTURA
        out.write("📂 ESTRUTURA DE ARQUIVOS:\n")
        for root, dirs, files in os.walk("."):
            # Remove pastas ignoradas
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            level = root.replace(".", "").count(os.sep)
            indent = " " * 4 * (level)
            out.write(f"{indent}[{os.path.basename(root)}/]\n")
            
            subindent = " " * 4 * (level + 1)
            for f in files:
                out.write(f"{subindent}{f}\n")
        
        out.write("\n" + "="*50 + "\n\n")
        out.write("🚨 ANÁLISE DE CÓDIGO (Arquivos que precisam de atenção):\n")

        # 2. SCANEAR CÓDIGO
        files_with_issues = []
        
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            for file in files:
                if file.endswith(".py") and file != "mapeamento.py":
                    path = os.path.join(root, file)
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            content = f.read()
                            
                            found_issues = []
                            has_fix = NEW_PATTERN in content
                            
                            for pattern in OLD_PATTERNS:
                                if pattern in content:
                                    found_issues.append(pattern)
                            
                            if found_issues:
                                # Se tem issues mas tem o fix, é 'Misto' (talvez ok)
                                # Se tem issues e NÃO tem fix, é 'Crítico'
                                status = "⚠️ MISTO (Verificar)" if has_fix else "❌ CRÍTICO (Alterar Urgente)"
                                files_with_issues.append((path, status, found_issues))
                                
                    except Exception as e:
                        out.write(f"Erro ao ler {path}: {e}\n")

        if not files_with_issues:
            out.write("✅ NENHUM PROBLEMA ENCONTRADO! O SISTEMA ESTÁ LIMPO.\n")
        else:
            for path, status, issues in files_with_issues:
                out.write(f"\nArquivo: {path}\n")
                out.write(f"Status: {status}\n")
                out.write(f"Encontrado: {', '.join(issues)}\n")
                out.write("-" * 40 + "\n")

    print(f"✅ Relatório gerado com sucesso em: {OUTPUT_FILE}")
    print("Por favor, envie o conteúdo deste arquivo para análise.")

if __name__ == "__main__":
    generate_report()