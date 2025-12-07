# modules/market_utils.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Optional, Dict

# Constantes de configuração
MIN_GOLD_PRICE = 1
MIN_GEM_PRICE = 10 

# ==========================================================
# 1. Funções de Renderização de Teclado (Keyboards)
# ==========================================================

# modules/market_utils.py (Função render_spinner_kb - CORRIGIDA)

def render_spinner_kb(
    value: int,
    prefix_inc: str,
    prefix_dec: str,
    label: str,
    confirm_cb: str,
    currency_emoji: str = "",
    allow_large_steps: bool = True
) -> InlineKeyboardMarkup:
    """Renderiza um teclado genérico de spinner."""
    
    value = max(1, int(value))
    
    # Linha principal de passos pequenos (row1 permanece igual)
    row1 = [
        InlineKeyboardButton("-100", callback_data=f"{prefix_dec}100"),
        InlineKeyboardButton("-10", callback_data=f"{prefix_dec}10"),
        InlineKeyboardButton("-1", callback_data=f"{prefix_dec}1"),
        InlineKeyboardButton("+1", callback_data=f"{prefix_inc}1"),
        InlineKeyboardButton("+10", callback_data=f"{prefix_inc}10"),
        InlineKeyboardButton("+100", callback_data=f"{prefix_inc}100")
    ]
    
    kb = [row1]
    
    # Linha de passos grandes (opcional para preço)
    if allow_large_steps:
        row2 = [
            InlineKeyboardButton("−5k", callback_data=f"{prefix_dec}5000"),
            InlineKeyboardButton("−1k", callback_data=f"{prefix_dec}1000"),
            InlineKeyboardButton("+1k", callback_data=f"{prefix_inc}1000"),
            InlineKeyboardButton("+5k", callback_data=f"{prefix_inc}5000")
        ]
        kb.append(row2)

    # Linha do valor atual
    kb.append([InlineKeyboardButton(f"{label}: {currency_emoji} {value}", callback_data="noop")])
    
    # Linha de Ação (Ajustada para lidar com o callback de cancelamento no momento da criação)
    
    cancel_cb_data = "market_cancel_new"
    if "gem" in confirm_cb:
        cancel_cb_data = "gem_market_cancel_new"
        
    kb.append([
        InlineKeyboardButton("✅ Confirmar", callback_data=confirm_cb), 
        InlineKeyboardButton("❌ Cancelar", callback_data=cancel_cb_data) # <--- USO DO CALLBACK CORRIGIDO
    ])

    return InlineKeyboardMarkup(kb)

# ==========================================================
# 2. Funções de Cálculo (Cálculo de Incremento/Decremento)
# ==========================================================

def calculate_spin_value(
    current_value: int,
    action_data: str,
    prefix_inc: str,
    prefix_dec: str,
    min_value: int = 1,
    max_value: Optional[int] = None
) -> int:
    """Calcula o novo valor do spinner com base na ação."""
    
    current = max(min_value, int(current_value))
    
    # Extrai o passo (step) do callback_data
    try:
        step = int(action_data.split("_")[-1])
    except (ValueError, IndexError):
        return current # Retorna o valor atual em caso de erro

    if action_data.startswith(prefix_inc):
        new_value = current + step
    elif action_data.startswith(prefix_dec):
        new_value = current - step
    else:
        return current

    # Aplica o mínimo e o máximo
    new_value = max(min_value, new_value)
    if max_value is not None:
        new_value = min(max_value, new_value)
        
    return new_value