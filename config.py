import os
from dotenv import load_dotenv

# Esta linha carrega as variáveis do arquivo .env para que o Python possa lê-las
load_dotenv()

# --- VARIÁVEIS DE AMBIENTE ---
# O código agora lê os segredos do ambiente, não do código diretamente.
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID_STR = os.getenv("ADMIN_ID")

# Validação para garantir que o bot não inicie sem as variáveis essenciais
if not TELEGRAM_TOKEN:
    raise ValueError("Erro: A variável de ambiente TELEGRAM_TOKEN não foi definida!")
if not ADMIN_ID_STR:
    raise ValueError("Erro: A variável de ambiente ADMIN_ID não foi definida!")

# Converte o ADMIN_ID para um número inteiro
try:
    ADMIN_ID = int(ADMIN_ID_STR)
except (ValueError, TypeError):
    raise ValueError("Erro: A variável de ambiente ADMIN_ID deve ser um número inteiro!")

# --- CONFIGURAÇÕES DO JOGO ---
JOB_TIMEZONE = os.getenv("JOB_TIMEZONE", "America/Sao_Paulo")

# Seus horários de eventos (isto pode ficar no código, pois não é um segredo)
EVENT_TIMES = [
    (9, 00, 11, 0),   
    (14, 0, 14, 30), #horarios
]