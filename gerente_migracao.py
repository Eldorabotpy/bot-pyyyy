import os
import time
import re

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
IGNORE_DIRS = {'.venv', '.git', '__pycache__', '.idea', '.vscode', 'env', 'venv'}
OUTPUT_FILE = "relatorio_migracao.txt"

# Padrões de Risco (Código Antigo)
OLD_PATTERNS = [
    "update.effective_user.id",
    "query.from_user.id",
    "message.from_user.id",
    "players_collection.find",
    "players_col.find",
    "user_id: int",
    "user_id : int",
]

# Padrões "NOVOS" (migração)
NEW_PATTERNS = [
    "get_current_player_id(",
    "get_current_player_id_async(",
]

# --- LISTA BRANCA (Exceções Permitidas) ---
WHITELIST = {
    # Windows paths
    "handlers\\auth_handler.py": ["update.effective_user.id"],
    "modules\\auth_utils.py": ["update.effective_user.id"],
    "modules\\player\\core.py": ["players_collection.find", "players_col.find"],

    # Linux/Mac paths
    "handlers/auth_handler.py": ["update.effective_user.id"],
    "modules/auth_utils.py": ["update.effective_user.id"],
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

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================

def get_priority_score(path: str) -> int:
    """Define a urgência do arquivo baseado na pasta onde ele está."""
    path = path.replace("\\", "/")
    for i, p_check in enumerate(PRIORITY_ORDER):
        if path.endswith(p_check) or p_check in path:
            return i
    return 99

def generate_project_tree(start_path=".") -> str:
    """Gera uma string visual da estrutura de diretórios e arquivos .py."""
    tree_output = ["\n" + "="*50, "📂 ESTRUTURA DO PROJETO (Arquivos .py)", "="*50 + "\n"]

    for root, dirs, files in os.walk(start_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        level = root.replace(start_path, "").count(os.sep)
        indent = "│   " * (level)

        folder_name = os.path.basename(root)
        if folder_name == ".":
            folder_name = "RAIZ (Projeto)"

        tree_output.append(f"{indent}📁 {folder_name}/")

        sub_indent = "│   " * (level + 1)
        for f in files:
            if f.endswith(".py"):
                tree_output.append(f"{sub_indent}📄 {f}")

    return "\n".join(tree_output)

def _is_whitelisted(path: str, pattern: str) -> bool:
    """Retorna True se o arquivo/padrão estiverem em whitelist."""
    for w_path, w_patterns in WHITELIST.items():
        if path.endswith(w_path) and pattern in w_patterns:
            return True
    return False

def _has_any_new_pattern(content: str) -> bool:
    return any(p in content for p in NEW_PATTERNS)

# ==============================================================================
# CHECKS ESPECÍFICOS (NOVO)
# ==============================================================================

def check_requires_login_ram_only(content: str) -> list[str]:
    """
    Detecta funções decoradas com @requires_login que ainda usam get_current_player_id()
    (RAM-only) dentro do handler. Isso costuma quebrar callbacks/eventos.
    """
    findings = []

    # Procura blocos: @requires_login ... def/async def ... (até o próximo def)
    # e verifica se contém "get_current_player_id(" sem async.
    # Observação: não é parser AST, mas é suficiente para auditoria prática.
    blocks = re.split(r"\n(?=def\s|async\s+def\s|@)", content)

    for blk in blocks:
        if "@requires_login" in blk:
            # Se o bloco contém get_current_player_id( mas não contém get_current_player_id_async(
            has_ram_only = "get_current_player_id(" in blk
            has_async = "get_current_player_id_async(" in blk
            if has_ram_only and not has_async:
                findings.append("requires_login + get_current_player_id (RAM-only) dentro do handler")
                break

    return findings

def check_sessions_objectid_validation(path: str, content: str) -> list[str]:
    """
    Para sessions.py: alerta se não houver validação explícita de ObjectId.is_valid
    e/ou normalização do player_id antes de salvar/retornar.
    """
    findings = []
    norm_path = path.replace("\\", "/").lower()

    if norm_path.endswith("modules/sessions.py") or norm_path.endswith("modules\\sessions.py".lower()):
        has_objectid_is_valid = "ObjectId.is_valid" in content
        has_normalize_fn = "def _normalize_player_id" in content or "normalize_player_id" in content

        if not has_objectid_is_valid:
            findings.append("sessions.py sem validação ObjectId.is_valid (risco de salvar ID legado)")
        if not has_normalize_fn:
            findings.append("sessions.py sem normalização/validação central de player_id")

    return findings

# ==============================================================================
# FUNÇÃO PRINCIPAL
# ==============================================================================

def generate_report():
    print("🕵️  Auditoria Inteligente v3.1 (ObjectId + Sessão + requires_login)...\n")
    time.sleep(0.3)

    total_files = 0
    files_with_issues = []

    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in files:
            if not file.endswith(".py"):
                continue
            if file == os.path.basename(__file__):
                continue

            total_files += 1
            path = os.path.join(root, file)

            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()

                found_issues = []
                has_fix = _has_any_new_pattern(content)

                # 1) Padrões antigos (com whitelist)
                for pattern in OLD_PATTERNS:
                    if _is_whitelisted(path, pattern):
                        continue
                    if pattern in content:
                        found_issues.append(pattern)

                # 2) Checks específicos
                found_issues.extend(check_requires_login_ram_only(content))
                found_issues.extend(check_sessions_objectid_validation(path, content))

                if found_issues:
                    status = "⚠️ MISTO" if has_fix else "❌ CRÍTICO"
                    files_with_issues.append({
                        "path": path,
                        "status": status,
                        "issues": sorted(set(found_issues)),
                        "priority": get_priority_score(path),
                        "has_fix": has_fix,
                    })

            except Exception as e:
                print(f"Erro ao ler {path}: {e}")

    # Ordena por prioridade (mais urgente primeiro)
    files_with_issues.sort(key=lambda x: x["priority"])

    total_issues = len(files_with_issues)
    clean_files = total_files - total_issues
    progress = (clean_files / total_files) * 100 if total_files > 0 else 100.0

    print("=" * 60)
    print(f"📊 PROGRESSO REAL: {progress:.1f}%")
    print(f"   Arquivos analisados: {total_files}")
    print(f"   Arquivos limpos:     {clean_files}")
    print(f"   Pendentes:           {total_issues}")
    print("=" * 60 + "\n")

    if not files_with_issues:
        print("✅ PARABÉNS! O sistema está 100% migrado e seguro.")
    else:
        print("🚀 PRÓXIMO PASSO (PRIORIDADE MÁXIMA):")
        next_target = files_with_issues[0]
        print(f"👉 Arquivo Alvo: {next_target['path']}")
        print(f"   Status: {next_target['status']}")
        print(f"   Problemas: {', '.join(next_target['issues'])}")

        print("\n💡 DICA:")
        if "requires_login + get_current_player_id" in ", ".join(next_target["issues"]):
            print("   Troque get_current_player_id(...) por await get_current_player_id_async(...).")
        elif "sessions.py" in next_target["path"].replace("\\", "/"):
            print("   Corrija sessions.py para validar ObjectId.is_valid antes de salvar/retornar player_id.")
        elif "handler" in next_target["path"]:
            print("   Handler acessando update/query diretamente. Migre para get_current_player_id_async.")

    # Salvar relatório + árvore
    try:
        project_tree = generate_project_tree(".")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
            out.write(f"RELATÓRIO DE MIGRAÇÃO - {progress:.1f}% CONCLUÍDO\n")
            out.write(f"Gerado em: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            out.write("=" * 60 + "\n\n")

            if not files_with_issues:
                out.write("Nenhum problema encontrado. Migração completa!\n")
            else:
                for item in files_with_issues:
                    out.write(f"Arquivo: {item['path']}\n")
                    out.write(f"Prioridade: {item['priority']} | Status: {item['status']}\n")
                    out.write(f"Encontrado: {', '.join(item['issues'])}\n")
                    out.write("-" * 60 + "\n")

            out.write(project_tree)

        print(f"\n📄 Relatório completo salvo em: {OUTPUT_FILE}")

    except Exception as e:
        print(f"Erro ao salvar arquivo de relatório: {e}")

if __name__ == "__main__":
    generate_report()
