import textwrap

THEMES = {
    "sombrio": {
        "title": "⚔️ 𝐀𝐑𝐄𝐍𝐀 𝐃𝐄 𝐄𝐋𝐃𝐎𝐑𝐀 ⚔️",
        "top":  "╭┈┈┈┈┈➤➤{title}",
        "mid":  "├┈➤",
        "pipe": "│",
        "bot":  "╰┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈➤",
        "sep":  "├┈➤════════════════════════════",
        "accent": "🕯️",
    },
    "dourado": {
        "title": "🏰 𝐀𝐑𝐄𝐍𝐀 𝐃𝐄 𝐄𝐋𝐃𝐎𝐑𝐀 🏰",
        "top":  "╭✦══════════ {title} ══════════✦",
        "mid":  "│ ✦ ",
        "pipe": "│",
        "bot":  "╰✦════════════════════════════✦",
        "sep":  "│ ✦ ──────────────────────────",
        "accent": "✨",
    },
    "arcano": {
        "title": "🔮 𝐀𝐑𝐄𝐍𝐀 𝐃𝐄 𝐄𝐋𝐃𝐎𝐑𝐀 🔮",
        "top":  "╭⋆══════════ {title} ══════════⋆",
        "mid":  "│ ⋆ ",
        "pipe": "│",
        "bot":  "╰⋆════════════════════════════⋆",
        "sep":  "│ ⋆ ──────────────────────────",
        "accent": "🜁",
    },
}

EFFECT_ICONS = {
    "defense": "🛡️",
    "attack": "⚔️",
    "evasion": "🌀",
    "crit": "🎯",
    "hp": "❤️",
    "xp": "📘",
    "gold": "💰",
    "speed": "⚡",
}

def bar(value: int, max_value: int, width: int = 10):
    """
    Barra visual ▰▱ com largura fixa.
    """
    if max_value <= 0:
        max_value = 1
    value = max(0, min(int(value), int(max_value)))
    filled = int(round((value / max_value) * width))
    filled = max(0, min(width, filled))
    return "▰" * filled + "▱" * (width - filled)

def wrap_lines(text: str, width: int = 42):
    return textwrap.wrap(text or "", width=width) if text else []

def theme_get(pdata: dict):
    # você pode salvar no perfil do jogador depois: pdata.get("ui_theme")
    # por enquanto pode fixar: "sombrio" / "dourado" / "arcano"
    return THEMES.get(pdata.get("ui_theme", "sombrio"), THEMES["sombrio"])

def format_effect_lines(day_title: str, day_desc: str, theme_mid: str, width: int = 42):
    """
    Tenta transformar descrições comuns em linhas com ícones.
    Se não conseguir inferir, apenas quebra o texto.
    """
    lines = []
    if day_title:
        lines.append(f"{theme_mid}📅 <b>Evento:</b> {day_title}")

    # Heurística simples de ícones com base em palavras-chave
    desc = (day_desc or "").lower()

    icon = None
    if "defes" in desc:
        icon = EFFECT_ICONS["defense"]
    elif "ataque" in desc or "dano" in desc:
        icon = EFFECT_ICONS["attack"]
    elif "esquiv" in desc:
        icon = EFFECT_ICONS["evasion"]
    elif "crit" in desc:
        icon = EFFECT_ICONS["crit"]
    elif "hp" in desc or "vida" in desc:
        icon = EFFECT_ICONS["hp"]
    elif "xp" in desc or "exper" in desc:
        icon = EFFECT_ICONS["xp"]
    elif "ouro" in desc or "gold" in desc:
        icon = EFFECT_ICONS["gold"]
    elif "veloc" in desc or "agil" in desc:
        icon = EFFECT_ICONS["speed"]

    # Se achou um ícone principal, usa bullet com ícone
    wrapped = wrap_lines(day_desc or "", width=width)
    if wrapped:
        first_prefix = f"{theme_mid}{icon} " if icon else f"{theme_mid}• "
        lines.append(first_prefix + f"<i>{wrapped[0]}</i>")
        for w in wrapped[1:]:
            lines.append(f"{theme_mid}  <i>{w}</i>")

    return lines

def build_arena_screen(pdata: dict, elo_name: str, points: int, wins: int, losses: int, day_title: str, day_desc: str):
    t = theme_get(pdata)

    # status (fallback seguro se não existir)
    hp = int(pdata.get("current_hp", pdata.get("hp", 0)) or 0)
    max_hp = int(pdata.get("max_hp", 1) or 1)

    energy = int(pdata.get("energy", 0) or 0)
    max_energy = int(pdata.get("max_energy", 1) or 1)

    xp = int(pdata.get("xp", 0) or 0)
    xp_max = int(pdata.get("xp_to_level", pdata.get("next_xp", 1)) or 1)

    lines = []
    lines.append(t["top"].format(title=t["title"]))
    lines.append(t["pipe"])
    lines.append(f'{t["mid"]}👤 <b>Guerreiro:</b> {pdata.get("character_name")}')
    lines.append(f'{t["mid"]}🏆 <b>Elo:</b> {elo_name} ({points} pts)')
    lines.append(f'{t["mid"]}📊 <b>Histórico:</b> {wins}V / {losses}D')
    lines.append(t["pipe"])

    # Barras RPG (mantém seu estilo, mas mais “game”)
    lines.append(f'{t["mid"]}❤️ <b>HP</b> {hp}/{max_hp} {bar(hp, max_hp, 10)}')
    lines.append(f'{t["mid"]}⚡ <b>Energia</b> {energy}/{max_energy} {bar(energy, max_energy, 10)}')
    lines.append(f'{t["mid"]}📘 <b>XP</b> {xp}/{xp_max} {bar(xp, xp_max, 10)}')

    lines.append(t["pipe"])
    lines.append(t["sep"])

    # Evento com ícones e quebra automática
    lines.extend(format_effect_lines(day_title, day_desc, t["mid"], width=42))

    lines.append(t["bot"])
    return "\n".join(lines)
