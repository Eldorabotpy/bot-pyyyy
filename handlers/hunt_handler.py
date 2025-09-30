# handlers/hunt_handler.py

import random
import re
import unicodedata
from datetime import datetime, timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from modules import player_manager, game_data
from modules import file_ids as file_id_manager
from handlers.utils import format_combat_message

# =========================
# Elites
# =========================
DEFAULT_ELITE_CHANCE = getattr(game_data, "ELITE_CHANCE", 0.12)  # 12% base
ELITE_MULTS = {
    "hp": 2.0,
    "attack": 1.4,
    "defense": 1.3,
    "initiative_add": 2,
    "luck_add": 5,
    "gold": 2.5,
    "xp": 2.0,
    "loot_bonus_pct": 10,
}

# =========================
# Utils
# =========================
def _slugify(text: str) -> str:
    if not text:
        return ""
    norm = unicodedata.normalize("NFKD", text)
    norm = norm.encode("ascii", "ignore").decode("ascii")
    norm = re.sub(r"\s+", "_", norm.strip().lower())
    norm = re.sub(r"[^a-z0-9_]", "", norm)
    return norm

def _get_region_info(region_key: str) -> dict:
    return (getattr(game_data, "REGIONS_DATA", {}) or {}).get(region_key, {}) or {}

def _get_monsters_from_region_dict(region_key: str):
    md = getattr(game_data, "MONSTERS_DATA", {}) or {}
    lst = md.get(region_key)
    return lst if isinstance(lst, list) and lst else None

def _get_monsters_from_region_field(region_key: str):
    info = _get_region_info(region_key)
    mons = info.get("monsters")
    if isinstance(mons, list) and mons:
        return mons
    return None

def _lookup_monster_by_id(mon_id: str) -> dict | None:
    cat = getattr(game_data, "MONSTER_TEMPLATES", {}) or {}
    v = cat.get(mon_id)
    return dict(v) if isinstance(v, dict) else None

def _coerce_monster_entry(entry) -> dict | None:
    if isinstance(entry, dict):
        return dict(entry)
    if isinstance(entry, str):
        return _lookup_monster_by_id(entry)
    return None

def _pick_monster_template(region_key: str, player_level: int) -> dict:
    # 1) MONSTERS_DATA[region_key] (lista de dicts)
    lst = _get_monsters_from_region_dict(region_key)
    if lst:
        pool = [e for e in lst if isinstance(e, dict)]
        if pool:
            return dict(random.choice(pool))

    # 2) REGIONS_DATA[region]['monsters'] (lista de dicts ou ids)
    mons = _get_monsters_from_region_field(region_key)
    if mons:
        pool = []
        for e in mons:
            m = _coerce_monster_entry(e)
            if m:
                pool.append(m)
        if pool:
            return dict(random.choice(pool))

    # 3) Fallback genérico escalonado
    base_hp = 20 + player_level * 5
    base_atk = 3 + player_level // 2
    base_def = 2 + max(0, player_level // 3)
    base_ini = 4 + max(0, player_level // 4)
    base_luk = 3 + max(0, player_level // 6)

    return {
        "id": f"generic_{region_key}",
        "name": "Criatura da Região",
        "hp": base_hp,
        "attack": base_atk,
        "defense": base_def,
        "initiative": base_ini,
        "luck": base_luk,
        "xp_reward": 8 + player_level * 2,
        "gold_drop": 4 + player_level * 2,
        "loot_table": [],
    }

def _roll_is_elite(luck_stat: int) -> bool:
    bonus = min(0.08, max(0.0, luck_stat / 2000.0))  # até +8pp de bônus
    p = DEFAULT_ELITE_CHANCE + bonus
    return random.random() < p

def _apply_elite_scaling(mon: dict) -> dict:
    m = dict(mon)
    name = m.get("name") or m.get("monster_name") or "Inimigo"
    m["name"] = f"{name} (🅴🅻🅸🆃🅴) 👑"

    hp_max = int(m.get("hp") or m.get("max_hp") or m.get("monster_max_hp") or 1)
    atk    = int(m.get("attack") or m.get("monster_attack") or 1)
    deff   = int(m.get("defense") or m.get("monster_defense") or 0)
    ini    = int(m.get("initiative") or m.get("monster_initiative") or 0)
    luk    = int(m.get("luck") or m.get("monster_luck") or 0)
    gold   = int(m.get("gold_drop") or m.get("monster_gold_drop") or 0)
    xp     = int(m.get("xp_reward") or m.get("monster_xp_reward") or 0)

    hp_max = int(hp_max * ELITE_MULTS["hp"])
    atk    = int(round(atk * ELITE_MULTS["attack"]))
    deff   = int(round(deff * ELITE_MULTS["defense"]))
    ini    = ini + ELITE_MULTS["initiative_add"]
    luk    = luk + ELITE_MULTS["luck_add"]
    gold   = int(round(gold * ELITE_MULTS["gold"]))
    xp     = int(round(xp * ELITE_MULTS["xp"]))

    m["max_hp"] = hp_max
    m["hp"] = hp_max
    m["attack"] = atk
    m["defense"] = deff
    m["initiative"] = ini
    m["luck"] = luk
    m["gold_drop"] = gold
    m["xp_reward"] = xp

    loot = []
    for it in (m.get("loot_table") or []):
        if not isinstance(it, dict):
            continue
        it2 = dict(it)
        try:
            it2["drop_chance"] = min(100.0, float(it2.get("drop_chance", 0.0)) + ELITE_MULTS["loot_bonus_pct"])
        except Exception:
            it2["drop_chance"] = min(100.0, 10.0 + ELITE_MULTS["loot_bonus_pct"])
        loot.append(it2)
    m["loot_table"] = loot
    m["_elite"] = True
    return m

def _build_combat_details_from_template(mon: dict) -> dict:
    name = mon.get("monster_name") or mon.get("name") or "Inimigo"

    max_hp = int(mon.get("monster_max_hp", mon.get("max_hp", mon.get("hp", 1))))
    hp     = int(mon.get("monster_hp", mon.get("hp", max_hp)))
    atk    = int(mon.get("monster_attack", mon.get("attack", 1)))
    deff   = int(mon.get("monster_defense", mon.get("defense", 0)))
    ini    = int(mon.get("monster_initiative", mon.get("initiative", 0)))
    luk    = int(mon.get("monster_luck", mon.get("luck", 0)))
    gold   = int(mon.get("monster_gold_drop", mon.get("gold_drop", 0)))
    xp     = int(mon.get("monster_xp_reward", mon.get("xp_reward", 0)))
    loot   = mon.get("loot_table", [])

    # guardamos pistas para mídia
    media_hint = (
        mon.get("file_id_name") or mon.get("file_id_key") or mon.get("media_key")
        or mon.get("id") or _slugify(name)
    )

    return {
        "id": mon.get("id"),
        "monster_name": name,
        "monster_hp": hp,
        "monster_max_hp": max_hp,
        "monster_attack": atk,
        "monster_defense": deff,
        "monster_initiative": ini,
        "monster_luck": luk,
        "monster_gold_drop": gold,
        "monster_xp_reward": xp,
        "loot_table": loot if isinstance(loot, list) else [],
        "battle_log": [],
        "media_hint": str(media_hint) if media_hint else None,
        "is_elite": bool(mon.get("_elite", False)),
    }

# =========================
# Energia para caçar
# =========================
def _hunt_energy_cost(player_data: dict, region_key: str) -> int:
    """
    Custo de energia para caçar:
      - 1) padrão global: game_data.HUNT_ENERGY_COST (default = 1)
      - 2) override por região: REGIONS_DATA[region]['hunt_energy_cost']
      - 3) override por perk: 'hunt_energy_cost' (por plano premium)
    """
    base = int(getattr(game_data, "HUNT_ENERGY_COST", 1))
    base = int(((getattr(game_data, "REGIONS_DATA", {}) or {}).get(region_key, {}) or {}).get("hunt_energy_cost", base))
    try:
        perk_val = int(player_manager.get_player_perk_value(player_data, "hunt_energy_cost", base))
    except Exception:
        perk_val = base
    return max(0, perk_val)

# =========================
# Mídia do monstro
# =========================
def _monster_media_candidates(mon_tpl: dict, region_key: str, is_elite: bool) -> list[str]:
    cands = []

    # pistas explícitas
    for k in ("file_id_name", "file_id_key", "media_key"):
        v = mon_tpl.get(k)
        if isinstance(v, str) and v.strip():
            cands.append(v.strip())

    # a partir de nome/id
    raw_name = mon_tpl.get("monster_name") or mon_tpl.get("name") or ""
    raw_id   = mon_tpl.get("id") or ""
    slug_name = _slugify(raw_name)
    slug_id   = _slugify(raw_id)

    base_slugs = []
    if slug_name:
        base_slugs.append(slug_name)
    if slug_id and slug_id not in base_slugs:
        base_slugs.append(slug_id)

    # se Elite, tente variantes específicas primeiro
    if is_elite:
        for s in base_slugs:
            cands += [
                f"{s}_elite_media",
                f"mob_{s}_elite",
                f"monster_{s}_elite_media",
                f"monstro_{s}_elite_media",
                f"{s}_elite_video",
                f"video_{s}_elite",
            ]

    # genéricas por monstro
    for s in base_slugs:
        cands += [
            f"mob_{s}",
            f"mob_video_{s}",
            f"monster_{s}_media",
            f"monstro_{s}_media",
            f"{s}_media",
            f"{s}_video",
            f"video_{s}",
            f"{s}_{region_key}_media",
        ]

    # por região (fallback)
    cands += [f"hunt_{region_key}", f"regiao_{region_key}"]

    # remove duplicatas mantendo ordem e ignora “abertura”
    seen = set()
    out = []
    for k in cands:
        if not k or "abertura" in k.lower():
            continue
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out

def _get_monster_media(mon_tpl: dict, region_key: str, is_elite: bool):
    for key in _monster_media_candidates(mon_tpl, region_key, is_elite):
        fd = file_id_manager.get_file_data(key)
        if fd and fd.get("id"):
            return fd
    return None

# =========================
# Handler principal
# =========================
async def hunt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    chat_id = query.message.chat_id

    pdata = player_manager.get_player_data(user_id)
    if not pdata:
        await context.bot.send_message(chat_id, "Crie um personagem com /start.")
        return

    st = pdata.get("player_state") or {"action": "idle"}
    if st.get("action") not in (None, "idle"):
        await query.answer("Você está ocupado em outra ação no momento.", show_alert=True)
        return

    region_key = (query.data or "").replace("hunt_", "", 1)
    if region_key not in (getattr(game_data, "REGIONS_DATA", {}) or {}):
        await query.answer("Região inválida para caça.", show_alert=True)
        return

    # ====== DEBITO DE ENERGIA ======
    cost = _hunt_energy_cost(pdata, region_key)
    if cost > 0:
        if not player_manager.spend_energy(pdata, cost):
            await query.answer(f"Energia insuficiente para caçar (precisa de {cost}).", show_alert=True)
            return
        # salva o débito imediatamente
        player_manager.save_player_data(user_id, pdata)

    total_stats = player_manager.get_player_total_stats(pdata)
    luck_stat = int(total_stats.get("luck", 5))
    player_level = int(pdata.get("level", 1))

    # escolhe monstro
    tpl = _pick_monster_template(region_key, player_level)

    # rola elite
    is_elite = _roll_is_elite(luck_stat)
    if is_elite:
        tpl = _apply_elite_scaling(tpl)

    # detalhes
    details = _build_combat_details_from_template(tpl)
    details["region_key"] = region_key

    # --- INÍCIO DO CÓDIGO DE DIAGNÓSTICO ---
    import json
    print("\n--- DEBUG: Conteúdo de combat_details ---")
    print(json.dumps(details, indent=2, ensure_ascii=False))
    print("--- FIM DO DEBUG ---\n")
# --- FIM DO CÓDIGO DE DIAGNÓSTICO ---
    # estado in_combat
    pdata["player_state"] = {
        "action": "in_combat",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "details": details,
    }
    pdata["last_chat_id"] = chat_id
    player_manager.save_player_data(user_id, pdata)

    caption = format_combat_message(pdata)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ 𝐀𝐭𝐚𝐜𝐚𝐫", callback_data='combat_attack'),
         InlineKeyboardButton("🏃 𝐅𝐮𝐠𝐢𝐫", callback_data='combat_flee')]
    ])

    # === MÍDIA: tenta monstro → região → texto
    media = _get_monster_media(tpl, region_key, is_elite)
    try:
        await query.delete_message()
    except Exception:
        pass

    if media and media.get("id"):
        fid = media["id"]
        mtype = (media.get("type") or "photo").lower()
        if mtype == "video":
            await context.bot.send_video(chat_id=chat_id, video=fid, caption=caption, reply_markup=kb, parse_mode="HTML")
        else:
            await context.bot.send_photo(chat_id=chat_id, photo=fid, caption=caption, reply_markup=kb, parse_mode="HTML")
    else:
        await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=kb, parse_mode="HTML")

# Exporta o handler
hunt_handler = CallbackQueryHandler(hunt_callback, pattern=r"^hunt_[A-Za-z0-9_]+$")
