import os
from dotenv import load_dotenv

# Esta linha carrega as variáveis do arquivo .env para que o Python possa lê-las
load_dotenv()

# --- VARIÁVEIS DE AMBIENTE ---
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


# --- 👇 MUDANÇA PRINCIPAL AQUI 👇 ---

# Horários de início e fim dos 4 eventos
# Formato: (hora_inicio, min_inicio, hora_fim, min_fim)
EVENT_TIMES = [
    (9,  10,   9, 40),  # Evento das 09:00 (dura 30 min)
    (12, 0,  12, 30),  # Evento das 12:00 (dura 30 min)
    (15, 20,  15, 30),  # Evento das 18:00 (dura 30 min)
    (22, 0,  22, 30),  # Evento das 22:00 (dura 30 min)
]

WORLD_BOSS_TIMES = [
    (8,  0,   9, 0),  # Evento das 08:00 (duração: 1 hora)
    (14, 0,  15, 0),  # Evento das 14:00 (duração: 1 hora)
    (19, 0,  20, 0),  # Evento das 19:00 (duração: 1 hora)
    (23, 0,   1, 0),  # Evento das 23:00 (duração: 2 horas, termina à 01:00 do dia seguinte)
]
