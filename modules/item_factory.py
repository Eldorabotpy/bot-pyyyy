# modules/item_factory.py
# ----------------------------------------------------
# Geração de itens únicos (sem receitas fixas), com:
# - 1º bônus sempre sendo o dano da CLASSE do jogador
# - Demais bônus aleatórios de um pool comum
# - Escalonamento: a cada 5 níveis do jogador, +1 em TODOS os bônus
# - Renderização de uma linha compacta para exibir o item
#
# Também expõe give_generated_item_to_player(...) para o painel admin.

from __future__ import annotations
import random
from typing import Dict, List, Tuple, Optional

from modules import game_data, player_manager

# ----- Configurações de bônus -----

# Pool comum de bônus “extras” depois do primeiro (dano da classe).
# Pode expandir/alterar quando quiser.
BONUS_POOL: List[str] = ["luck", "hp", "defense", "initiative", "dmg"]

# Rótulos bonitos de raridade (acentuados)
RARITY_LABEL: Dict[str, str] = {
    "comum": "Comum",
    "bom": "Boa",
    "raro": "Rara",
    "epico": "Épica",
    "lendario": "Lendária",
}

# ----------------------------------------------------
# Utilitários internos
# ----------------------------------------------------

def _rarity_bonus_count(rarity: str) -> int:
    """Quantos bônus extras a raridade concede (além do dano ‘dmg’)."""
    return int(game_data.RARITY_BONUS_COUNT.get((rarity or "").lower(), 0))

def _class_damage_emoji(player_class: Optional[str]) -> str:
    """Retorna o emoji de dano por classe; fallback 🗡."""
    return game_data.CLASS_DMG_EMOJI.get((player_class or "").lower(), "🗡")

def _base_name(base_id: str) -> str:
    """Nome bonitinho da base (ITEM_BASES) ou retorna o próprio id."""
    return game_data.ITEM_BASES.get(base_id, {}).get("display_name", base_id)

def _normalize_rarity(rarity: Optional[str]) -> str:
    r = (rarity or "comum").strip().lower()
    if r not in game_data.RARITY_DATA:
        r = "comum"
    return r

def _bonus_rolls(n_extras: int) -> List[str]:
    """
    Sorteia n_extras do BONUS_POOL (sem repetir), ignorando 'dmg' aqui
    porque ‘dmg’ já é garantido como o primeiro bônus.
    """
    pool = [s for s in BONUS_POOL if s != "dmg"]
    random.shuffle(pool)
    return pool[:max(0, n_extras)]

# ----------------------------------------------------
# API pública de geração e exibição
# ----------------------------------------------------

def generate_item_instance(
    base_id: str,
    rarity: str,
    player_class: str,
    player_level: int,
    durab: int = 20
) -> dict:
    """
    Gera uma instância única de item baseada em:
      - base_id: chave de ITEM_BASES (apenas nome/slot importam)
      - rarity: 'comum' | 'bom' | 'raro' | 'epico' | 'lendario'
      - player_class: usado para o emoji de dano (primeiro bônus)
      - player_level: a cada 5 níveis, +1 em TODOS os bônus
      - durab: durabilidade total e atual (ex.: 20 -> [20,20])

    BÔNUS:
      * O 1º bônus SEMPRE é 'dmg' (dano da classe)
      * Resto é sorteado do BONUS_POOL sem repetir
      * Todos os bônus começam em +1 e recebem +1 por cada “faixa de 5 níveis”
    """
    rarity_key = _normalize_rarity(rarity)
    extras = _rarity_bonus_count(rarity_key)

    # Escolha dos bônus: dmg fixo + extras aleatórios
    chosen_stats = ["dmg"]
    chosen_stats.extend(_bonus_rolls(extras))

    # Valor base
    enchants: Dict[str, Dict[str, int]] = {stat: {"level": 1, "value": 1} for stat in chosen_stats}

    # Escalonamento por nível: +1 a cada 5 níveis
    extra_value = max(0, int(player_level) // 5)
    if extra_value > 0:
        for st in enchants:
            enchants[st]["value"] += extra_value

    instance = {
        "base_id": base_id,
        "rarity": rarity_key,
        "durability": [int(durab), int(durab)],
        "enchantments": enchants,
        "tier": game_data.RARITY_DATA.get(rarity_key, {}).get("tier", 1),
    }
    return instance

def render_item_line(instance: dict, player_class: str) -> str:
    """
    Renderiza no formato:
      『[20/20] ⚔️Espada Larga de Mithril [ 2 ] [ Rara ]: ⚔️+3, 🍀+2, ❤️‍🩹+2』
    O ícone de dano troca dinamicamente pelo emoji da classe.
    """
    base_id = instance.get("base_id", "")
    name = _base_name(base_id)

    rarity_key = _normalize_rarity(instance.get("rarity"))
    rarity_label = RARITY_LABEL.get(rarity_key, rarity_key.capitalize())
    tier = int(instance.get("tier", 1))
    cur_d, max_d = instance.get("durability", [20, 20])

    dmg_emoji = _class_damage_emoji(player_class)

    parts: List[str] = []
    for stat, data in (instance.get("enchantments") or {}).items():
        val = int(data.get("value", 1))
        # troca o emoji de dmg pelo emoji da classe
        if stat == "dmg":
            emo = dmg_emoji
        else:
            emo = game_data.STAT_EMOJI.get(stat, "❔")
        parts.append(f"{emo}+{val}")

    stats_str = ", ".join(parts) if parts else "—"
    # Nota: prefixamos o nome com o emoji de dano da classe
    return f"『[{cur_d}/{max_d}] {dmg_emoji}{name} [ {tier} ] [ {rarity_label} ]: {stats_str}』"

# ----------------------------------------------------
# Entregar item ao jogador (para painel admin e scripts)
# ----------------------------------------------------

def give_generated_item_to_player(
    user_id: int,
    base_id: str,
    rarity: str,
    player_class: Optional[str] = None,
    player_level: Optional[int] = None,
    *,
    durab: int = 20,
    save: bool = True,
) -> Tuple[str, str]:
    """
    Gera e entrega um item único para o jogador.
    Retorna (unique_id, linha_renderizada).

    - Se player_class/level não forem informados, usa do próprio jogador.
    - `save=True` salva o arquivo do jogador após adicionar.
    """
    pdata = player_manager.get_player_data(user_id)
    if not pdata:
        raise RuntimeError("Jogador não encontrado.")

    pc = (player_class or pdata.get("class") or "guerreiro").lower()
    pl = int(player_level or pdata.get("level", 1))

    # Gera e adiciona
    inst = generate_item_instance(base_id, rarity, pc, pl, durab)
    uid = player_manager.add_unique_item(pdata, inst)

    if save:
        player_manager.save_player_data(user_id, pdata)

    line = render_item_line(inst, pc)
    return uid, line

# ----------------------------------------------------
# Helpers opcionais para admin/menu
# ----------------------------------------------------

def preview_generated_item_line(
    base_id: str,
    rarity: str,
    player_class: str,
    player_level: int,
    durab: int = 20
) -> str:
    """Gera + renderiza (não salva). Útil para mostrar preview no admin."""
    inst = generate_item_instance(base_id, rarity, player_class, player_level, durab)
    return render_item_line(inst, player_class)

def available_item_bases() -> List[Tuple[str, str]]:
    """
    Retorna [(base_id, display_name), ...] a partir de ITEM_BASES
    (útil para montar botões de admin).
    """
    items = []
    for k, v in game_data.ITEM_BASES.items():
        items.append((k, v.get("display_name", k)))
    items.sort(key=lambda x: x[1].lower())
    return items

def available_rarities() -> List[str]:
    """Raridades válidas, na ordem do seu jogo."""
    return ["comum", "bom", "raro", "epico", "lendario"]

def render_item_stats_short(instance: dict, player_class: str) -> str:
    dmg_emoji = game_data.CLASS_DMG_EMOJI.get(player_class or "", "🗡")
    parts = []
    for stat, data in (instance.get("enchantments") or {}).items():
        val = int(data.get("value", 1))
        emo = dmg_emoji if stat == "dmg" else game_data.STAT_EMOJI.get(stat, "❔")
        parts.append(f"{emo}+{val}")
    return " ".join(parts) if parts else ""

