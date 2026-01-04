# tools/find_legacy_usage.py
import os

# Configuração
TARGET_STRING = "player_manager"
IGNORE_DIRS = {'.venv', '.git', '__pycache__', '.idea', '.vscode', 'env', 'venv'}

def find_legacy_usage():
    print(f"🕵️  CAÇADOR DE LEGADO: Procurando quem importa '{TARGET_STRING}'...\n")
    
    count = 0
    dependents = []

    # Varre a partir da pasta raiz (subindo um nível se estiver em tools)
    start_dir = "."
    if os.path.basename(os.getcwd()) == "tools":
        start_dir = ".."

    for root, dirs, files in os.walk(start_dir):
        # Ignora pastas de sistema/venv
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            # Ignora o próprio arquivo de player_manager e este script
            if file.endswith(".py") and file != "player_manager.py" and file != "find_legacy_usage.py":
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        
                    found_lines = []
                    for i, line in enumerate(lines):
                        # Procura linhas que tenham "player_manager" E "import"
                        if TARGET_STRING in line and ("import" in line or "from" in line):
                            clean_line = line.strip()
                            # Ignora comentários
                            if not clean_line.startswith("#"):
                                found_lines.append(f"   Line {i+1}: {clean_line}")
                    
                    if found_lines:
                        dependents.append((path, found_lines))
                        count += 1
                        
                except Exception as e:
                    # Ignora erros de leitura (arquivos binários, etc)
                    pass

    print("="*60)
    if count == 0:
        print("✅ LIMPEZA COMPLETA!")
        print("🎉 Nenhum arquivo importa 'player_manager'.")
        print("🗑️  Você pode deletar 'modules/player_manager.py' AGORA.")
    else:
        print(f"⚠️  ATENÇÃO: {count} arquivos ainda dependem do sistema antigo:\n")
        for path, lines in dependents:
            print(f"📁 {path}")
            for l in lines:
                print(l)
            print("-" * 40)
            
        print("\n🔧 AÇÃO: Vá nesses arquivos e troque por 'modules.player.core'!")
    print("="*60)

if __name__ == "__main__":
    find_legacy_usage()
    