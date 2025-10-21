# handlers/admin/utils.py

from __future__ import annotations
import os
import sys
import logging
from telegram import Update
from modules import player_manager

# Pega o ID e converte para número
admin_id_str = os.getenv("ADMIN_ID")
ADMIN_ID = None

if not admin_id_str:
    logging.critical("A variável de ambiente ADMIN_ID não foi definida! O bot não pode iniciar sem ela.")
    sys.exit("ERRO: ADMIN_ID não definido.")
try:
    ADMIN_ID = int(admin_id_str)
except (ValueError, TypeError):
    logging.critical(f"O valor de ADMIN_ID ('{admin_id_str}') não é um número válido!")
    sys.exit("ERRO: ADMIN_ID inválido.")

async def ensure_admin(update: Update) -> bool:
    """Verifica se o usuário é o admin e imprime logs de debug detalhados."""
    
    # ==========================================================
    # ================= CÓDIGO DE DEBUG ========================
    # ==========================================================
    print("--- [DEBUG] INICIANDO VERIFICAÇÃO DE ADMIN (Função Centralizada) ---")
    admin_id_from_env = os.getenv("ADMIN_ID")
    user_id_from_telegram = update.effective_user.id if update.effective_user else None

    print(f"[DEBUG] Valor de ADMIN_ID lido do Render: '{admin_id_from_env}'")
    print(f"[DEBUG] Tipo do ADMIN_ID lido: {type(admin_id_from_env)}")
    print(f"[DEBUG] User ID vindo do Telegram: {user_id_from_telegram}")
    print(f"[DEBUG] Tipo do User ID: {type(user_id_from_telegram)}")

    if admin_id_from_env is None:
        print("[DEBUG] ERRO CRÍTICO: A variável de ambiente ADMIN_ID não foi encontrada!")
    elif user_id_from_telegram is None:
        print("[DEBUG] ERRO CRÍTICO: Não foi possível obter o ID do usuário do Telegram.")
    else:
        try:
            is_admin_check = (int(admin_id_from_env) == user_id_from_telegram)
            print(f"[DEBUG] Resultado da comparação (int(Render) == Telegram): {is_admin_check}")
        except Exception as e:
            print(f"[DEBUG] ERRO ao tentar converter ADMIN_ID para int: {e}")

    print("--- [DEBUG] FIM DA VERIFICAÇÃO ---")
    # ==========================================================
    
    uid = update.effective_user.id if update.effective_user else None
    
    # Esta é a verificação de produção real
    if ADMIN_ID and uid != ADMIN_ID:
        q = getattr(update, "callback_query", None)
        if q:
            await q.answer("Somente ADMIN pode usar esta função.", show_alert=True)
        elif update.effective_chat:
            await update.effective_chat.send_message("Somente ADMIN pode usar esta função.")
        return False
        
    return True

async def find_player_from_input(text_input: str) -> tuple | None:
    """
    Encontra um jogador a partir de um input de texto,
    que pode ser um User ID ou um nome de personagem.
    Retorna uma tupla (user_id, player_data) ou None se não encontrar.
    """
    text_input = text_input.strip()
    try:
        # Tenta encontrar por ID
        user_id = int(text_input)
        pdata = player_manager.get_player_data(user_id)
        if pdata:
            return user_id, pdata
    except ValueError:
        # Se não for um ID, tenta encontrar por nome
        found = player_manager.find_player_by_name(text_input)
        if found:
            return found
    
    # Se não encontrou de nenhuma forma
    return None