# modules/display_utils.py
from __future__ import annotations
from typing import Dict, Any

# Dados do jogo
from modules import game_data
from modules.game_data.equipment import SLOT_EMOJI
from modules.game_data.attributes import ATTRIBUTE_ICONS

try:
    from modules.game_data.classes import get_primary_damage_profile, CLASSES_DATA
except Exception:
    CLASSES_DATA = {}
    def get_primary_damage_profile(_): return {"stat_key": "dmg"}

# -----------------------------
# Helpers
# -----------------------------

def _rarity_title(r: str) -> str:
    return (str(r or "comum")).capitalize()

def _item_info(base_id: str) -> dict:
    """Busca primeiro em ITEMS_DATA; se não achar, tenta o wrapper get_item_info()."""
    info = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(base_id)
    if info:
        return info
    try:
        alt = game_data.get_item_info(base_id)
        if alt:
            return alt
    except Exception:
        pass
    return {}

def _item_emoji(item: Dict[str, Any]) -> str:
    """Prioriza emoji da instância; depois do catálogo base; por fim, do slot."""
    if item.get("emoji"):
        return str(item["emoji"])
    info = _item_info(item.get("base_id", ""))
    if info.get("emoji"):
        return str(info["emoji"])
    slot = info.get("slot") or item.get("slot")
    return SLOT_EMOJI.get(slot, "🛠")

def _class_emoji_from_req(item: Dict[str, Any]) -> str:
    """Se class_req tem uma única classe, usa o emoji definido em CLASSES_DATA."""
    req = item.get("class_req")
    if isinstance(req, list) and len(req) == 1:
        ckey = (req[0] or "").lower()
        emj = (CLASSES_DATA.get(ckey) or {}).get("emoji")
        if emj:
            return str(emj)
    return ""

def _durability_str(item: Dict[str, Any]) -> str:
    dur = item.get("durability") or []
    if isinstance(dur, (list, tuple)) and len(dur) >= 2:
        try:
            cur, tot = int(dur[0]), int(dur[1])
            return f"[{cur}/{tot}]"
        except Exception:
            pass
    return "[?/??]"

def _display_name(item: Dict[str, Any]) -> str:
    if item.get("display_name"):
        return str(item["display_name"])
    info = _item_info(item.get("base_id", ""))
    name = info.get("display_name") or info.get("nome_exibicao")
    return str(name) if name else (item.get("base_id", "Item").replace("_", " ").title())

def _upgrade_level(item: Dict[str, Any]) -> int:
    try:
        return int(item.get("upgrade_level", 1))
    except Exception:
        return 1

def _attr_icon_for(key: str) -> str:
    """Mapeia chaves internas para os ícones configurados."""
    if not key:
        return "✨"
    alias = {
        "hp": "vida",
        "defense": "defesa",
        "initiative": "agilidade",
        "luck": "sorte",
        # "dmg" costuma ser exibido como o atributo da classe, não direto;
        # mas se algum lugar pedir explicitamente dmg, podemos cair num ícone genérico:
        "dmg": "forca",  # fallback visual (⚔️ não está no ATTRIBUTE_ICONS por padrão)
    }
    k = alias.get(key, key)
    return ATTRIBUTE_ICONS.get(k, "✨")

def _detect_item_class_key(item: Dict[str, Any]) -> str | None:
    """
    Descobre a classe alvo do item:
      1) pela restrição 'class_req' (se houver e for única)
      2) heurística pelo base_id contendo o nome da classe (ex.: *_samurai)
    """
    req = item.get("class_req")
    if isinstance(req, list) and req:
        return str(req[0]).lower()
    base_id = str(item.get("base_id", "")).lower()
    for ckey in ("guerreiro","mago","berserker","cacador","assassino","bardo","monge","samurai"):
        if ckey in base_id:
            return ckey
    return None

def _find_primary(item: Dict[str, Any]) -> tuple[str | None, int]:
    """
    Acha o PRIMÁRIO:
      1) enchant com source começando por 'primary' (inclui 'primary' e 'primary_mirror')
         - se a chave for 'dmg', mapeia para o stat da classe para ícone correto (ex.: 🎯 Precisão)
      2) se não achar, tenta o stat primário da classe diretamente nas enchants
      3) fallback: maior valor não-'dmg'
    Retorna (key_canonica, valor) ou (None, 0).
    """
    ench = item.get("enchantments") or {}
    if isinstance(ench, dict):
        # 1) 'primary' / 'primary_mirror'
        for k, v in ench.items():
            if not isinstance(v, dict):
                continue
            src = str(v.get("source", ""))
            if not src.startswith("primary"):
                continue
            try:
                val = int(v.get("value", 0))
            except Exception:
                val = 0

            if k == "dmg":
                # dmg como primário → converter para o stat da classe (para o ícone correto)
                ckey = _detect_item_class_key(item)
                if ckey:
                    stat_key = get_primary_damage_profile(ckey).get("stat_key") or "dmg"
                else:
                    stat_key = "dmg"
                return stat_key, val

            return k, val

        # 2) tenta pelo stat primário da classe
        ckey = _detect_item_class_key(item)
        if ckey:
            stat_key = get_primary_damage_profile(ckey).get("stat_key")
            if stat_key and stat_key in ench and isinstance(ench.get(stat_key), dict):
                try:
                    return stat_key, int(ench[stat_key].get("value", 0))
                except Exception:
                    return stat_key, 0

        # 3) maior valor não-'dmg'
        best = None
        for k, v in ench.items():
            if k == "dmg" or not isinstance(v, dict):
                continue
            try:
                val = int(v.get("value", 0))
            except Exception:
                val = 0
            if best is None or val > best[1]:
                best = (k, val)
        if best:
            return best

    return (None, 0)

def _collect_affixes(item: Dict[str, Any], exclude_key: str | None) -> list[tuple[str, int]]:
    """
    Coleta afixos (source='affix'), ignorando 'dmg' e a chave do primário.
    Ordena para estabilidade: por nome e valor desc.
    """
    out: list[tuple[str, int]] = []
    ench = item.get("enchantments") or {}
    if not isinstance(ench, dict):
        return out
    for k, v in ench.items():
        if k in ("dmg", exclude_key):
            continue
        if isinstance(v, dict) and str(v.get("source")) == "affix":
            try:
                out.append((k, int(v.get("value", 0))))
            except Exception:
                out.append((k, 0))
    out.sort(key=lambda t: (t[0], -t[1]))
    return out

# -----------------------------
# API pública
# -----------------------------

def formatar_item_para_exibicao(item: Dict[str, Any]) -> str:
    """
    Ex.: 『[20/20] 🥷⚔️ Katana Laminada [1][Bom]: 🥷 +1, 🍀 +1 』
    Regras de exibição:
      - Emoji da classe + emoji do item, sem duplicar (se forem iguais, mostra só um)
      - Primário sempre primeiro; afixos depois (exclui 'dmg' da lista)
      - Raridade capitalizada
    """
    dur = _durability_str(item)
    class_emo = _class_emoji_from_req(item)
    item_emo  = _item_emoji(item)
    name = _display_name(item)
    upg = _upgrade_level(item)
    rarity = _rarity_title(item.get("rarity", "comum"))

    # primário (robusto; lida com 'dmg' → stat da classe)
    pkey, pval = _find_primary(item)
    prim_icon = _attr_icon_for(pkey)

    # afixos (exclui chave do primário)
    affixes = _collect_affixes(item, exclude_key=pkey)
    parts = [f"{prim_icon} +{int(pval or 0)}"]
    for ak, av in affixes:
        parts.append(f"{_attr_icon_for(ak)} +{int(av or 0)}")
    stats_text = ", ".join(parts)

    # bloco de emoji sem duplicar
    emoji_block = item_emo
    if class_emo and class_emo != item_emo:
        emoji_block = f"{class_emo}{item_emo}"

    return f"『{dur} {emoji_block} {name} [{upg}][{rarity}]: {stats_text} 』"

# -------------------------------------------------------------------
# Extensões p/ Inventário, Equipamentos e Mercado do Aventureiro
# -------------------------------------------------------------------

def render_item_line(item: Dict[str, Any], *_args, **_kwargs) -> str:
    """
    Alias compatível com handlers antigos.
    Garante que todo lugar use o mesmo formato bonito de equipamento único.
    """
    return formatar_item_para_exibicao(item)

def _nome_de_item(item_id: str) -> str:
    info = (getattr(game_data, "ITEMS_DATA", {}) or {}).get(item_id, {}) or {}
    name = info.get("display_name")
    if name:
        return str(name)
    # fallback: "barra_de_ferro" -> "Barra de Ferro"
    words = item_id.replace("_", " ").strip().split()
    titled = [w.capitalize() for w in words]
    for i, w in enumerate(titled):
        if w.lower() in {"de", "da", "do", "das", "dos"} and i != 0:
            titled[i] = w.lower()
    return " ".join(titled) if titled else item_id

def formatar_empilhavel_para_exibicao(item_id: str, qty: int) -> str:
    """
    Mesmo padrão usado no inventário para itens empilháveis.
    Ex.: '• 5x Barra de Ferro'
    """
    try:
        q = int(qty)
    except Exception:
        q = 0
    return f"• {q}x {_nome_de_item(item_id)}"

def market_render_line(item_key: str, item_value) -> str:
    """
    Helper para o Mercado do Aventureiro:
      - se 'item_value' for dict com base_id (único): usa a linha bonita
      - se for número (empilhável): usa '• Qtd x Nome'
    """
    if isinstance(item_value, dict) and item_value.get("base_id"):
        return render_item_line(item_value)
    try:
        qty = int(item_value)
    except Exception:
        qty = 0
    return formatar_empilhavel_para_exibicao(item_key, qty)

# Renderização igual ao inventário/forja
try:
    from modules import display_utils  # formatar_item_para_exibicao(item: dict) -> str
except Exception:
    display_utils = None  # usamos fallback local se não existir
