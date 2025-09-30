# handlers/admin/utils.py

from __future__ import annotations
import os
from telegram import Update

# Pega o ID e converte para número
ADMIN_ID = int(os.getenv("ADMIN_ID"))

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