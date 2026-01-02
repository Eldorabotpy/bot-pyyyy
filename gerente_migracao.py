import os
import time

# Configuração
IGNORE_DIRS = {'.venv', '.git', '__pycache__', '.idea', '.vscode'}
OUTPUT_FILE = "relatorio_migracao.txt"

# Padrões de Risco
OLD_PATTERNS = [
    "update.effective_user.id",
    "query.from_user.id",
    "message.from_user.id",
    "players_collection.find",
    "players_col.find",
    "user_id: int",
    "user_id : int"
]

NEW_PATTERN = "get_current_player_id"

# --- LISTA BRANCA (Exceções Permitidas) ---
# Arquivos que PODEM usar certos comandos proibidos por necessidade técnica
WHITELIST = {
    # O Auth Handler precisa ler o ID do Telegram para saber quem está tentando logar
    "handlers\\auth_handler.py": ["update.effective_user.id"],
    "handlers/auth_handler.py": ["update.effective_user.id"],
    
    # O Auth Utils é quem cria a segurança, ele precisa ler o ID cru
    "modules\\auth_utils.py": ["update.effective_user.id"],
    "modules/auth_utils.py": ["update.effective_user.id"],
    
    # O Core do banco precisa acessar as coleções antigas para compatibilidade se necessário
    "modules\\player\\core.py": ["players_collection.find", "players_col.find"],
    "modules/player/core.py": ["players_collection.find", "players_col.find"],
}

# Prioridade de Correção (Do mais crítico para o menos crítico)
PRIORITY_ORDER = [
    "modules/player_manager.py",
    "modules/game_data",        
    "modules/player",           
    "modules/combat",           
    "modules/events",           
    "handlers/admin",           
    "handlers",                 
]

def get_priority_score(path):
    """Define a urgência do arquivo baseado na pasta onde ele está."""
    path = path.replace("\\", "/") 
    for i, p_check in enumerate(PRIORITY_ORDER):
        if path.endswith(p_check) or p_check in path:
            return i 
    return 99 

def generate_report():
    print("🕵️  Auditoria Inteligente v3.0 (Com Exceções)...\n")
    time.sleep(0.5)

    total_files = 0
    files_with_issues = []
    
    # Varredura
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            if file.endswith(".py") and file != os.path.basename(__file__):
                total_files += 1
                path = os.path.join(root, file)
                
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                        
                        found_issues = []
                        has_fix = NEW_PATTERN in content
                        
                        for pattern in OLD_PATTERNS:
                            # --- VERIFICAÇÃO DE EXCEÇÃO ---
                            # Se o arquivo está na whitelist e o padrão é permitido nele, ignora
                            normalized_path = path
                            is_whitelisted = False
                            
                            for w_path, w_patterns in WHITELIST.items():
                                if path.endswith(w_path):
                                    if pattern in w_patterns:
                                        is_whitelisted = True
                                        break
                            
                            if is_whitelisted:
                                continue
                            # ------------------------------

                            if pattern in content:
                                found_issues.append(pattern)
                        
                        if found_issues:
                            status = "⚠️ MISTO" if has_fix else "❌ CRÍTICO"
                            files_with_issues.append({
                                "path": path,
                                "status": status,
                                "issues": found_issues,
                                "priority": get_priority_score(path)
                            })
                            
                except Exception:
                    pass

    # Ordena por prioridade
    files_with_issues.sort(key=lambda x: x['priority'])

    # Estatísticas
    total_issues = len(files_with_issues)
    clean_files = total_files - total_issues
    progress = (clean_files / total_files) * 100 if total_files > 0 else 100

    # Saída no Terminal
    print("="*50)
    print(f"📊 PROGRESSO REAL: {progress:.1f}%")
    print(f"   Arquivos Limpos: {clean_files}")
    print(f"   Pendentes: {total_issues}")
    print("="*50 + "\n")

    if not files_with_issues:
        print("✅ PARABÉNS! O sistema está 100% migrado e seguro.")
        return

    print("🚀 PRÓXIMO PASSO (PRIORIDADE MÁXIMA):")
    
    next_target = files_with_issues[0]
    print(f"👉 Arquivo Alvo: {next_target['path']}")
    print(f"   Status: {next_target['status']}")
    print(f"   Problemas: {', '.join(next_target['issues'])}")
    
    print("\n💡 DICA:")
    if "admin" in next_target['path']:
        print("   Painéis de admin costumam ter código misto.")
        print("   Verifique se as funções de edição de player usam 'get_current_player_id'.")
    elif "handler" in next_target['path']:
        print("   Este handler está acessando o update do Telegram diretamente.")
        print("   Use 'uid = get_current_player_id(update, context)' no início das funções.")

    # Salva relatório
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write(f"RELATÓRIO DE MIGRAÇÃO - {progress:.1f}% CONCLUÍDO\n")
        out.write("="*50 + "\n\n")
        for item in files_with_issues:
            out.write(f"Arquivo: {item['path']}\n")
            out.write(f"Prioridade: {item['priority']} | Status: {item['status']}\n")
            out.write(f"Encontrado: {', '.join(item['issues'])}\n")
            out.write("-" * 40 + "\n")

if __name__ == "__main__":
    generate_report()