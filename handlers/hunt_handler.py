# handlers/hunt_handler.py

import random
import re
import unicodedata
import logging
import asyncio
from typing import Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, CallbackQuery
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

from modules import player_manager, game_data
from modules import file_ids as file_id_manager
from handlers.utils import format_combat_message_from_cache
from modules.player.premium import PremiumManager
from modules import auto_hunt_engine
from handlers.profile_handler import _get_class_media

# Importa a DB de skills para garantir acesso (se necessário no futuro)
from modules.game_data.monsters import MONSTER_SKILLS_DB

logger = logging.getLogger(__name__)

# =========================
# Elites
# =========================
DEFAULT_ELITE_CHANCE = getattr(game_data, "ELITE_CHANCE", 0.12)
ELITE_MULTS = {
    "hp": 2.0, "attack": 1.4, "defense": 1.3,
    "initiative_add": 2, "luck_add": 5,
    "gold": 2.5, "xp": 3.0, "loot_bonus_pct": 10,
}

# =========================
# Utils
# =========================
def _slugify(text: str) -> str:
    if not text: return ""
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    norm = re.sub(r"[^a-z0-9_]", "", re.sub(r"\s+", "_", norm.strip().lower()))
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
    if isinstance(mons, list) and mons: return mons
    return None

def _lookup_monster_by_id(mon_id: str) -> dict | None:
    cat = getattr(game_data, "MONSTER_TEMPLATES", {}) or {}
    v = cat.get(mon_id)
    return dict(v) if isinstance(v, dict) else None

def _coerce_monster_entry(entry) -> dict | None:
    if isinstance(entry, dict): return dict(entry)
    if isinstance(entry, str): return _lookup_monster_by_id(entry)
    return None

def _pick_monster_template(region_key: str, player_level: int) -> dict:
    # Tenta pegar da lista principal
    lst = _get_monsters_from_region_dict(region_key)
    if lst:
        pool = [e for e in lst if isinstance(e, dict)]
        if pool: return dict(random.choice(pool))

    # Tenta pegar da definição da região
    mons = _get_monsters_from_region_field(region_key)
    if mons:
        pool = []
        for e in mons:
            m = _coerce_monster_entry(e)
            if m: pool.append(m)
        if pool: return dict(random.choice(pool))

    # Fallback Genérico
    base_hp = 20 + player_level * 5
    return {
        "id": f"generic_{region_key}", "name": "Criatura Sombria",
        "hp": base_hp, "max_hp": base_hp, # Garante max_hp
        "attack": 3 + player_level // 2, "defense": 2,
        "initiative": 4, "luck": 3,
        "xp_reward": 8 + player_level, "gold_drop": 4 + player_level,
        "loot_table": [],
    }

def _roll_is_elite(luck_stat: int) -> bool:
    bonus = min(0.08, max(0.0, luck_stat / 2000.0)) 
    return random.random() < (DEFAULT_ELITE_CHANCE + bonus)

def _apply_elite_scaling(mon: dict) -> dict:
    m = dict(mon)
    name = m.get("name") or "Inimigo"
    m["name"] = f"{name} (🅴🅻I🆃🅴) 👑"
    m["_elite"] = True
    
    # Aplica multiplicadores de Elite
    keys_mult = [("max_hp", "hp"), ("attack", "attack"), ("defense", "defense"), 
                 ("xp_reward", "xp"), ("gold_drop", "gold")]
    
    for k_mon, k_mult in keys_mult:
        base = int(m.get(k_mon, 0))
        m[k_mon] = int(base * ELITE_MULTS[k_mult])
    
    m["hp"] = m["max_hp"] # Cura total
    m["initiative"] = int(m.get("initiative", 0)) + ELITE_MULTS["initiative_add"]
    m["luck"] = int(m.get("luck", 0)) + ELITE_MULTS["luck_add"]
    
    # Loot extra
    loot = []
    for it in (m.get("loot_table") or []):
        it2 = dict(it)
        it2["drop_chance"] = min(100.0, float(it2.get("drop_chance", 0.0)) + ELITE_MULTS["loot_bonus_pct"])
        loot.append(it2)
    m["loot_table"] = loot
    return m

# --- NOVA FUNÇÃO: ESCALA HÍBRIDA (CORRIGIDA) ---
def _scale_monster_stats(mon: dict, player_level: int) -> dict:
    """Escala o monstro e garante que max_hp esteja setado."""
    
    # 1. Normalização Inicial de HP
    if "max_hp" not in mon and "hp" in mon:
        mon["max_hp"] = mon["hp"]
    elif "max_hp" not in mon:
        mon["max_hp"] = 10 

    # 2. Definição do Nível
    min_lvl = mon.get("min_level", 1)
    max_lvl = mon.get("max_level", player_level + 2)
    target_lvl = max(min_lvl, min(player_level + random.randint(-1, 1), max_lvl))
    mon["level"] = target_lvl

    # 3. Atualiza Nome 
    raw_name = mon.get("name", "Inimigo").replace("Lv.", "").strip()
    raw_name = re.sub(r"^\d+\s+", "", raw_name) 
    mon["name"] = f"Lv.{target_lvl} {raw_name}"

    if target_lvl <= 1:
        mon["hp"] = mon["max_hp"]
        return mon

    # ==========================================================
    # 📉 AJUSTE DE BALANCEAMENTO (NERF NA XP E OURO)
    # ==========================================================
    # Antes estava 15 HP / 12 XP. Agora vamos deixar mais suave:
    
    GROWTH_HP = 12       # HP continua subindo bem (era 15)
    GROWTH_ATK = 2.0     # Dano sobe devagar (era 2.5)
    GROWTH_DEF = 1.0     # Defesa sobe pouco (era 1.5)
    
    GROWTH_XP = 3        # <--- REDUZIDO DRASTICAMENTE (Era 12)
                         # Agora Lv.10 dá +30 XP extra, não +120
                         
    GROWTH_GOLD = 1.5    # <--- REDUZIDO (Era 5)
                         # Agora Lv.10 dá +15 Gold extra, não +50
    
    scaling_bonus = 1 + (target_lvl * 0.02) 

    # 5. Aplica Fórmula
    base_hp = int(mon.get("max_hp", 10))
    base_atk = int(mon.get("attack", 2))
    base_def = int(mon.get("defense", 0))
    base_xp = int(mon.get("xp_reward", 5))
    base_gold = int(mon.get("gold_drop", 1))

    mon["max_hp"] = int((base_hp * scaling_bonus) + (target_lvl * GROWTH_HP))
    mon["hp"] = mon["max_hp"]
    mon["attack"] = int((base_atk * scaling_bonus) + (target_lvl * GROWTH_ATK))
    mon["defense"] = int((base_def * scaling_bonus) + (target_lvl * GROWTH_DEF))
    
    # XP e Ouro ajustados
    mon["xp_reward"] = int((base_xp * scaling_bonus) + (target_lvl * GROWTH_XP))
    mon["gold_drop"] = int((base_gold * scaling_bonus) + (target_lvl * GROWTH_GOLD))
    
    return mon

def _build_combat_details_from_template(mon: dict, player_level: int = 1) -> dict:
    m = mon.copy()
    
    # Normaliza chaves legadas antes de escalar
    if "monster_max_hp" in m: m["max_hp"] = m.pop("monster_max_hp")
    if "monster_attack" in m: m["attack"] = m.pop("monster_attack")
    if "monster_defense" in m: m["defense"] = m.pop("monster_defense")
    if "monster_name" in m: m["name"] = m.pop("monster_name")

    # Aplica a Escala (que agora garante max_hp e nome)
    m = _scale_monster_stats(m, player_level)
    
    return {
        "id": m.get("id"),
        "name": m.get("name"),
        "level": m.get("level", 1),
        "hp": int(m.get("hp", 1)),
        "max_hp": int(m.get("max_hp", 1)), # Agora deve vir correto da escala
        "attack": int(m.get("attack", 1)),
        "defense": int(m.get("defense", 0)),
        "initiative": int(m.get("initiative", 0)),
        "luck": int(m.get("luck", 0)),
        "gold_drop": int(m.get("gold_drop", 0)),
        "xp_reward": int(m.get("xp_reward", 0)),
        "loot_table": m.get("loot_table", []),
        "is_elite": bool(m.get("_elite", False) or m.get("is_elite", False)),
        "is_boss": bool(m.get("is_boss", False)),
        "skills": m.get("skills", [])
    }

def _get_monster_media(mon_tpl: dict, region_key: str, is_elite: bool):
    cands = []
    # Tenta usar o ID ou nome limpo para achar a mídia
    raw_name = mon_tpl.get("name", "").replace("Lv.", "").strip().split(" ")[-1] # Pega ultima palavra se tiver Lv.
    raw_id = mon_tpl.get("id", "")
    
    for k in ("file_id_name", "file_id_key", "media_key"):
        if v := mon_tpl.get(k): cands.append(v)

    slug_id = _slugify(raw_id)
    if is_elite: cands.append(f"mob_{slug_id}_elite")
    cands.append(f"mob_{slug_id}")
    cands.append(f"hunt_{region_key}")
    
    for key in cands:
        fd = file_id_manager.get_file_data(key)
        if fd and fd.get("id"): return fd 
    return None

async def _hunt_energy_cost(player_data: dict, region_key: str) -> int:
    # 1. Define 1 como custo base padrão
    base = 1 
    
    # 2. Tenta ler a configuração global (se houver)
    base = int(getattr(game_data, "HUNT_ENERGY_COST", base))
    
    # 3. Verifica se a região específica tem um custo diferente
    reg_info = _get_region_info(region_key)
    base = int(reg_info.get("hunt_energy_cost", base))
    
    # 4. Aplica os bônus/reduções de Premium (Lenda/VIP podem ter custo reduzido)
    premium = PremiumManager(player_data)
    return int(premium.get_perk_value("hunt_energy_cost", base))

# =========================
# HANDLERS
# =========================
async def start_hunt(
    user_id: int, 
    chat_id: int, 
    context: ContextTypes.DEFAULT_TYPE, 
    is_auto_mode: bool, 
    region_key: str, 
    query: Optional[CallbackQuery] = None
):
    from handlers.combat.main_handler import combat_callback

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        if query: await query.answer("Erro: Dados não encontrados.", show_alert=True)
        return

    # Custo e Missão
    cost = await _hunt_energy_cost(pdata, region_key)
    if cost > 0:
        if not player_manager.spend_energy(pdata, cost):
            msg = "⚡️ Sem energia!"
            if is_auto_mode: await context.bot.send_message(chat_id, msg)
            elif query: await query.answer(msg, show_alert=True)
            return
        
        await player_manager.save_player_data(user_id, pdata)
        try:
            from modules import mission_manager 
            await mission_manager.update_mission_progress(user_id, "spend_energy", "any", cost)
        except: pass

    # --- SETUP DA BATALHA ---
    player_lvl = int(pdata.get("level", 1))
    
    # 1. Escolhe e Escala Monstro
    tpl = _pick_monster_template(region_key, player_lvl)
    
    # Elite Check
    total_stats = await player_manager.get_player_total_stats(pdata)
    is_elite = _roll_is_elite(int(total_stats.get("luck", 5)))
    if is_elite: tpl = _apply_elite_scaling(tpl)

    # Constrói stats finais
    monster_stats = _build_combat_details_from_template(tpl, player_level=player_lvl)
    monster_media = _get_monster_media(tpl, region_key, is_elite)
    player_media = _get_class_media(pdata, purpose="combate")

    # Sincronia HP/MP
    max_hp = total_stats.get('max_hp', 50)
    max_mp = total_stats.get('max_mana', 10)
    cur_hp = min(pdata.get('current_hp', max_hp), max_hp)
    cur_mp = min(pdata.get('current_mp', max_mp), max_mp)

    # 2. CACHE DA BATALHA (Aqui adicionamos o Nível do Player ao Nome)
    char_name = pdata.get('character_name', 'Herói')
    
    battle_cache = {
        'player_id': user_id,
        'chat_id': chat_id,
        # CORREÇÃO: Injeta o nível no nome para aparecer na interface
        'player_name': f"Lv.{player_lvl} {char_name}", 
        'player_stats': total_stats,
        'player_hp': cur_hp,
        'player_mp': cur_mp,
        'player_media_id': player_media.get('id') if player_media else None,
        'player_media_type': (player_media.get('type') or 'photo').lower() if player_media else 'photo',
        
        'monster_stats': monster_stats,
        'monster_media_id': monster_media.get('id') if monster_media else None,
        'monster_media_type': (monster_media.get('type') or 'photo').lower() if monster_media else 'photo',
        
        'region_key': region_key,
        'is_auto_mode': is_auto_mode,
        'battle_log': ["Aguardando sua ação..."],
        'turn': 'player', 
        'message_id': None, 
    }

    pdata["player_state"] = {"action": "in_combat"}
    pdata["current_hp"] = cur_hp
    pdata["current_mp"] = cur_mp
    await player_manager.save_player_data(user_id, pdata)

    caption = await format_combat_message_from_cache(battle_cache) 
    
    kb = []
    if is_auto_mode:
        kb = [[InlineKeyboardButton("🛑 PARAR AUTO-CAÇA", callback_data='autohunt_stop')]]
    else:
        kb = [
            [InlineKeyboardButton("⚔️ 𝐀𝐭𝐚𝐜𝐚𝐫", callback_data='combat_attack'), InlineKeyboardButton("✨ Skills", callback_data='combat_skill_menu')],
            [InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu'), InlineKeyboardButton("🏃 𝐅𝐮𝐠𝐢𝐫", callback_data='combat_flee')]
        ]

    if query:
        try: await query.delete_message()
        except: pass

    # Envio da Mídia
    sent_msg = None
    mid = battle_cache['monster_media_id']
    mtype = battle_cache['monster_media_type']
    
    if mid:
        try:
            if mtype == "video":
                sent_msg = await context.bot.send_video(chat_id, video=mid, caption=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
            else:
                sent_msg = await context.bot.send_photo(chat_id, photo=mid, caption=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        except Exception: pass
    
    if not sent_msg:
        sent_msg = await context.bot.send_message(chat_id, text=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    
    if sent_msg:
        battle_cache['message_id'] = sent_msg.message_id
        context.user_data['battle_cache'] = battle_cache

    if is_auto_mode:
        # Fake trigger para auto hunt
        fake_u = type("User", (), {"id": user_id})()
        fake_q = CallbackQuery(id=f"auto_{user_id}", from_user=fake_u, chat_instance="auto", data="combat_attack")
        fake_up = Update(update_id=0, callback_query=fake_q)
        await asyncio.sleep(2)
        await combat_callback(fake_up, context, action='combat_attack')

async def hunt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except: pass
    
    region_key = (query.data or "").replace("hunt_", "", 1)
    await start_hunt(query.from_user.id, query.message.chat.id, context, False, region_key, query)

async def start_auto_hunt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split('_')
        hunt_count = int(parts[2])
        region_key = "_".join(parts[3:]) 
        await auto_hunt_engine.start_auto_hunt(update, context, hunt_count, region_key)
    except Exception: pass

autohunt_start_handler = CallbackQueryHandler(start_auto_hunt_callback, pattern=r'^autohunt_start_')        
hunt_handler = CallbackQueryHandler(hunt_callback, pattern=r"^hunt_")