# handlers/hunt_handler.py

import random
import re
import unicodedata
import logging
import asyncio
from datetime import datetime, timezone
# --- IMPORTAÇÕES CORRIGIDAS ---
from typing import Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, CallbackQuery
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

from modules import player_manager, game_data
from modules import file_ids as file_id_manager
from handlers.utils import format_combat_message
from modules.player.premium import PremiumManager
from modules import auto_hunt_engine
from handlers.utils import format_combat_message_from_cache
from handlers.profile_handler import _get_class_media

logger = logging.getLogger(__name__)

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
    "xp": 3.0,
    "loot_bonus_pct": 10,
}

# =========================
# Utils
# =========================
def _slugify(text: str) -> str:
    if not text: return ""
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
        "id": f"generic_{region_key}", "name": "Criatura da Região",
        "hp": base_hp, "attack": base_atk, "defense": base_def,
        "initiative": base_ini, "luck": base_luk,
        "xp_reward": 8 + player_level * 2, "gold_drop": 4 + player_level * 2,
        "loot_table": [],
    }

def _roll_is_elite(luck_stat: int) -> bool:
    bonus = min(0.08, max(0.0, luck_stat / 2000.0)) 
    p = DEFAULT_ELITE_CHANCE + bonus
    return random.random() < p

def _apply_elite_scaling(mon: dict) -> dict:
    m = dict(mon)
    name = m.get("name") or m.get("monster_name") or "Inimigo"
    m["name"] = f"{name} (🅴🅻I🆃🅴) 👑"
    hp_max = int(m.get("hp") or m.get("max_hp") or m.get("monster_max_hp") or 1)
    atk = int(m.get("attack") or m.get("monster_attack") or 1)
    deff = int(m.get("defense") or m.get("monster_defense") or 0)
    ini = int(m.get("initiative") or m.get("monster_initiative") or 0)
    luk = int(m.get("luck") or m.get("monster_luck") or 0)
    gold = int(m.get("gold_drop") or m.get("monster_gold_drop") or 0)
    xp = int(m.get("xp_reward") or m.get("monster_xp_reward") or 0)
    hp_max = int(hp_max * ELITE_MULTS["hp"])
    atk = int(round(atk * ELITE_MULTS["attack"]))
    deff = int(round(deff * ELITE_MULTS["defense"]))
    ini = ini + ELITE_MULTS["initiative_add"]
    luk = luk + ELITE_MULTS["luck_add"]
    gold = int(round(gold * ELITE_MULTS["gold"]))
    xp = int(round(xp * ELITE_MULTS["xp"]))
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
        if not isinstance(it, dict): continue
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
    
    return {
        "id": mon.get("id"),
        "name": name,
        "hp": int(mon.get("monster_hp", mon.get("hp", max_hp))),
        "max_hp": max_hp,
        "attack": int(mon.get("monster_attack", mon.get("attack", 1))),
        "defense": int(mon.get("monster_defense", mon.get("defense", 0))),
        "initiative": int(mon.get("monster_initiative", mon.get("initiative", 0))),
        "luck": int(mon.get("monster_luck", mon.get("luck", 0))),
        "gold_drop": int(mon.get("monster_gold_drop", mon.get("gold_drop", 0))),
        "xp_reward": int(mon.get("monster_xp_reward", mon.get("xp_reward", 0))),
        "loot_table": mon.get("loot_table", []),
        "is_elite": bool(mon.get("_elite", False) or mon.get("is_elite", False)),
        "is_boss": bool(mon.get("is_boss", False)),
    }

# =========================
# Mídia do monstro
# =========================
def _get_monster_media(mon_tpl: dict, region_key: str, is_elite: bool):
    cands = []
    raw_name = mon_tpl.get("monster_name") or mon_tpl.get("name") or ""
    raw_id   = mon_tpl.get("id") or ""
    
    for k in ("file_id_name", "file_id_key", "media_key"):
        v = mon_tpl.get(k)
        if isinstance(v, str) and v.strip():
            cands.append(v.strip())

    base_slugs = []
    if slug_name := _slugify(raw_name): base_slugs.append(slug_name)
    if slug_id := _slugify(raw_id): 
        if slug_id not in base_slugs:
            base_slugs.append(slug_id)

    if is_elite:
        for s in base_slugs:
            cands.extend([f"mob_{s}_elite", f"{s}_elite_media", f"{s}_elite_video"])

    for s in base_slugs:
        cands.extend([f"mob_{s}", f"mob_video_{s}", f"{s}_media", f"video_{s}"])

    cands.extend([f"hunt_{region_key}", f"regiao_{region_key}"])
    
    for key in cands:
        if "abertura" in key.lower(): continue
        fd = file_id_manager.get_file_data(key)
        if fd and fd.get("id"):
            return fd 
            
    return None

# =========================
# FUNÇÃO NÚCLEO (CORRIGIDA)
# =========================
async def start_hunt(
    user_id: int, 
    chat_id: int, 
    context: ContextTypes.DEFAULT_TYPE, 
    is_auto_mode: bool, 
    region_key: str, 
    query: Optional[CallbackQuery] = None
):
    """Função núcleo que inicia uma caçada, criando o BATTLE CACHE."""
    
    from handlers.combat.main_handler import combat_callback

    pdata = await player_manager.get_player_data(user_id)
    if not pdata:
        if query: await query.answer("Erro: Não foi possível carregar seus dados.", show_alert=True)
        return

    cost = await _hunt_energy_cost(pdata, region_key)
    
    # -------------------------------------------------------------
    # [CORREÇÃO] Gasto de Energia + Atualização de Missão
    # -------------------------------------------------------------
    if cost > 0:
        if not player_manager.spend_energy(pdata, cost):
            if is_auto_mode:
                await context.bot.send_message(chat_id, "⚡️ Sua energia acabou! Caça automática finalizada.")
            elif query:
                await query.answer(f"Energia insuficiente para caçar (precisa de {cost}).", show_alert=True)
            return
        
        await player_manager.save_player_data(user_id, pdata)

        # >>> INÍCIO DA ATUALIZAÇÃO DA MISSÃO <<<
        try:
            from modules import mission_manager 
            # Atualiza a missão "spend_energy" com a quantidade gasta (cost)
            await mission_manager.update_mission_progress(user_id, "spend_energy", "any", cost)
        except Exception as e:
            logger.error(f"[HUNT] Erro ao atualizar missão de energia: {e}")
        # >>> FIM DA ATUALIZAÇÃO DA MISSÃO <<<

    # --- Preparação da Batalha ---
    tpl = _pick_monster_template(region_key, int(pdata.get("level", 1)))
    total_stats_jogador = await player_manager.get_player_total_stats(pdata)
    is_elite = _roll_is_elite(int(total_stats_jogador.get("luck", 5)))
    
    if is_elite:
        tpl = _apply_elite_scaling(tpl)

    monster_stats = _build_combat_details_from_template(tpl)
    monster_media = _get_monster_media(tpl, region_key, is_elite)

    player_media_data = _get_class_media(pdata, purpose="combate") # Pega skin/classe

    # --- Sincronização de HP/MP ---
    # 1. Pega o HP e MP MÁXIMOS dos stats totais
    max_hp = total_stats_jogador.get('max_hp', 50)
    max_mp = total_stats_jogador.get('max_mana', 10)
    
    # 2. Pega o HP e MP atuais da base de dados
    current_hp = pdata.get('current_hp', max_hp)
    current_mp = pdata.get('current_mp', max_mp)
    
    # 3. Garante que o HP e MP atuais não sejam maiores que o máximo
    current_hp = min(current_hp, max_hp)
    current_mp = min(current_mp, max_mp)

    # --- Normalização defensiva de XP/Ouro do monstro ---
    try:
        def _first_int(d, *keys, default=0):
            for k in keys:
                if isinstance(d, dict) and k in d:
                    try:
                        return int(float(d.get(k, 0)))
                    except Exception:
                        continue
            return int(default)

        monster_stats['xp_reward'] = _first_int(monster_stats, 'xp_reward', 'xp', 'monster_xp_reward', default=0)
        monster_stats['gold_drop'] = _first_int(monster_stats, 'gold_drop', 'gold', 'monster_gold_drop', default=0)

        # Propaga nomes alternativos para compatibilidade
        if 'monster_xp_reward' not in monster_stats:
            monster_stats['monster_xp_reward'] = monster_stats['xp_reward']
        if 'monster_gold_drop' not in monster_stats:
            monster_stats['monster_gold_drop'] = monster_stats['gold_drop']

    except Exception as e:
        logger.exception(f"[HUNT DEBUG] Falha ao normalizar monster_stats: {e}")

    # 5. CRIA O CACHE DE BATALHA
    battle_cache = {
        'player_id': user_id,
        'chat_id': chat_id,
        'player_name': pdata.get('character_name', 'Herói'),
        'player_stats': total_stats_jogador, # Stats totais
        
        # --- Usa os valores sincronizados ---
        'player_hp': current_hp,
        'player_mp': current_mp, 
        
        'player_media_id': player_media_data.get('id') if player_media_data else None,
        'player_media_type': (player_media_data.get('type') or 'photo').lower() if player_media_data else 'photo',
        
        'monster_stats': monster_stats, # Stats totais do monstro
        'monster_media_id': monster_media.get('id') if monster_media else None,
        'monster_media_type': (monster_media.get('type') or 'photo').lower() if monster_media else 'photo',
        
        'region_key': region_key,
        'is_auto_mode': is_auto_mode,
        'battle_log': ["Aguardando sua ação..."],
        'turn': 'player', 
        'message_id': None, 
        'skill_cooldowns': {}, 
    }

    # 6. Atualiza o Estado do Jogador
    pdata["player_state"] = {"action": "in_combat"}
    pdata["current_hp"] = current_hp
    pdata["current_mp"] = current_mp
    await player_manager.save_player_data(user_id, pdata)

    # 7. Formata a Mensagem Inicial
    caption = await format_combat_message_from_cache(battle_cache) 

    if is_auto_mode:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🛑 PARAR AUTO-CAÇA", callback_data='autohunt_stop')]])
    else:
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⚔️ 𝐀𝐭𝐚𝐜𝐚𝐫", callback_data='combat_attack'),
                InlineKeyboardButton("✨ Skills", callback_data='combat_skill_menu'),
            ],[
                InlineKeyboardButton("🧪 Poções", callback_data='combat_potion_menu'),
                InlineKeyboardButton("🏃 𝐅𝐮𝐠𝐢𝐫", callback_data='combat_flee')
            ]
        ])

    if query:
        try: await query.delete_message()
        except Exception: pass

    # 8. Envia a Mídia Inicial (Monstro)
    media_sent = False
    sent_message = None
    
    if battle_cache['monster_media_id']:
        try:
            media_type = battle_cache['monster_media_type']
            media_id = battle_cache['monster_media_id']
            
            if media_type == "video":
                sent_message = await context.bot.send_video(
                    chat_id=chat_id, video=media_id, caption=caption, 
                    reply_markup=kb, parse_mode="HTML"
                )
            else:
                sent_message = await context.bot.send_photo(
                    chat_id=chat_id, photo=media_id, caption=caption, 
                    reply_markup=kb, parse_mode="HTML"
                )
            media_sent = True
        except Exception as e:
            logger.warning(f"Falha ao enviar mídia do monstro ({media_id}): {e}. Usando fallback.")

    if not media_sent:
        sent_message = await context.bot.send_message(
            chat_id=chat_id, text=caption, 
            reply_markup=kb, parse_mode="HTML"
        )
    
    # 9. Salva o ID da Mensagem no Cache (CRUCIAL)
    if sent_message:
        battle_cache['message_id'] = sent_message.message_id
    
    # 10. Salva o cache na memória do bot
    context.user_data['battle_cache'] = battle_cache

    # 11. Inicia o combate automático (se necessário)
    if is_auto_mode:
        fake_user = type("User", (), {"id": user_id})()
        fake_query = CallbackQuery(id=f"auto_{user_id}", from_user=fake_user, chat_instance="auto", data="combat_attack")
        fake_update = Update(update_id=0, callback_query=fake_query)
        await asyncio.sleep(2)
        await combat_callback(fake_update, context, action='combat_attack')
                
async def _hunt_energy_cost(player_data: dict, region_key: str) -> int:
    """
    Custo de energia para caçar, agora com bónus premium a funcionar (assíncrono).
    """
    # Síncrono
    base = int(getattr(game_data, "HUNT_ENERGY_COST", 1))
    base = int(((getattr(game_data, "REGIONS_DATA", {}) or {}).get(region_key, {}) or {}).get("hunt_energy_cost", base))

    premium = PremiumManager(player_data) # Síncrono
    perk_val = int( premium.get_perk_value("hunt_energy_cost", base))

    return max(0, perk_val)

async def hunt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler que é chamado pelo botão 'Caçar' manual."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    region_key = (query.data or "").replace("hunt_", "", 1)
    
    await start_hunt(user_id, chat_id, context, is_auto_mode=False, region_key=region_key, query=query)

async def start_auto_hunt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback que lê os dados do botão (10, 25, 35) e chama o engine.
    """
    query = update.callback_query
    await query.answer()
    
    try:
        # Callback: "autohunt_start_COUNT_REGION"
        parts = query.data.split('_')
        hunt_count = int(parts[2])
        # A região pode ter underlines, então junta o resto
        region_key = "_".join(parts[3:]) 
        
        if not region_key:
            raise ValueError("Region key estava vazia.")

        await auto_hunt_engine.start_auto_hunt(update, context, hunt_count, region_key)
        
    except (IndexError, ValueError, TypeError) as e:
        logger.error(f"Callback de Auto-Hunt inválido: {query.data} | Erro: {e}")
        try:
            await query.edit_message_text("Erro ao processar o seu pedido de caçada rápida.")
        except:
            pass

autohunt_start_handler = CallbackQueryHandler(start_auto_hunt_callback, pattern=r'^autohunt_start_')        
hunt_handler = CallbackQueryHandler(hunt_callback, pattern=r"^hunt_")