# handlers/combat_handler.py

import random
import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest
from modules import file_ids 
from modules import player_manager, game_data
from handlers.menu.region import send_region_menu
from handlers.utils import format_combat_message
from handlers.class_selection_handler import show_class_selection_menu
from modules import mission_manager
from modules import clan_manager

# 🔗 Integração com Dungeon (runtime novo)
try:
    from modules.dungeons.runtime import advance_after_victory as _dungeon_advance_after_victory
except Exception:
    _dungeon_advance_after_victory = None  # sem dungeon instalada


# -------------------------
# Helpers de segurança/UI
# -------------------------
async def _safe_answer(query):
    try:
        await query.answer()
    except BadRequest:
        pass


async def _edit_caption_only(query, caption_text: str, reply_markup=None):
    """Edita SEMPRE a CAPTION; se falhar, manda fallback como texto."""
    try:
        await query.edit_message_caption(
            caption=caption_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    except BadRequest:
        try:
            await query.get_bot().send_message(
                chat_id=query.message.chat_id,
                text=caption_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        except Exception:
            pass


def _mstat(details: dict, key: str, default: int = 1) -> int:
    """Lê stats do monstro aceitando tanto 'monster_attack' quanto 'attack' etc."""
    return int(details.get(f"monster_{key}", details.get(key, default)))


# -------------------------
# Durabilidade — helpers
# -------------------------
_WEAPON_SLOTS = ("weapon", "primary_weapon", "arma")
_ARMOR_SLOTS  = ("elmo", "armadura", "calca", "luvas", "botas", "anel", "colar", "brinco")


def _get_equipped_uid(player_data: dict, slot_names) -> str | None:
    equip = (player_data or {}).get("equipment", {}) or {}
    for s in slot_names:
        uid = equip.get(s)
        if isinstance(uid, str) and uid:
            return uid
    return None


def _get_unique_inst(player_data: dict, uid: str) -> dict | None:
    if not uid:
        return None
    inv = (player_data or {}).get("inventory", {}) or {}
    inst = inv.get(uid)
    return inst if isinstance(inst, dict) and inst.get("base_id") else None


def _dur_tuple(raw) -> tuple[int, int]:
    cur, mx = 20, 20
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        try:
            cur = int(raw[0]); mx = int(raw[1])
        except Exception:
            pass
    elif isinstance(raw, dict):
        try:
            cur = int(raw.get("current", 20)); mx = int(raw.get("max", 20))
        except Exception:
            pass
    cur = max(0, cur)
    mx = max(1, mx)
    if cur > mx:
        cur = mx
    return cur, mx


def _consume_durability(player_data: dict, uid: str, amount: int = 1) -> tuple[int, int, bool]:
    """
    Consome 'amount' de durabilidade do item único 'uid'.
    Retorna (cur, mx, quebrou_agora).
    """
    inv = player_data.get("inventory", {}) or {}
    inst = inv.get(uid)
    if not isinstance(inst, dict):
        return (0, 0, False)

    cur, mx = _dur_tuple(inst.get("durability"))
    if mx <= 0:
        mx = 20
    if cur <= 0:
        # já quebrado
        return (0, mx, False)

    cur = max(0, cur - int(amount))
    inst["durability"] = [cur, mx]
    inv[uid] = inst
    player_data["inventory"] = inv
    return (cur, mx, cur == 0)


def _weapon_broken(player_data: dict) -> tuple[bool, str | None, tuple[int, int]]:
    """Verifica se a arma equipada está quebrada (durabilidade 0)."""
    w_uid = _get_equipped_uid(player_data, _WEAPON_SLOTS)
    if not w_uid:
        return (False, None, (0, 0))
    inst = _get_unique_inst(player_data, w_uid)
    if not inst:
        return (False, None, (0, 0))
    cur, mx = _dur_tuple(inst.get("durability"))
    return (cur <= 0, w_uid, (cur, mx))


def _apply_end_of_battle_durability(player_data: dict, combat_details: dict, log: list[str]) -> None:
    """
    Consome durabilidade UMA ÚNICA VEZ no fim da batalha:
      - arma -1 se used_weapon=True
      - TODAS AS PEÇAS DE ARMADURA -1 se took_damage=True
    Adiciona logs se quebrar.
    """
    used_weapon = bool(combat_details.get("used_weapon"))
    took_damage = bool(combat_details.get("took_damage"))
    changed = False
    user_id = player_data.get("user_id", 0)

    # 1. Desgaste da Arma (lógica existente, sem alterações)
    if used_weapon:
        w_uid = _get_equipped_uid(player_data, _WEAPON_SLOTS)
        if w_uid:
            cur, mx, broke_now = _consume_durability(player_data, w_uid, 1)
            changed = True
            if broke_now:
                log.append(
                    f"⚠️ 𝑺𝒖𝒂 𝒂𝒓𝒎𝒂 𝒒𝒖𝒆𝒃𝒓𝒐𝒖 ({cur}/{mx}). "
                    f"𝑼𝒔𝒆 📜 𝑷𝒆𝒓𝒈𝒂𝒎𝒊𝒏𝒉𝒐 𝒅𝒆 𝑫𝒖𝒓𝒂𝒃𝒊𝒍𝒊𝒅𝒂𝒅𝒆 𝒑𝒂𝒓𝒂 𝒓𝒆𝒔𝒕𝒂𝒖𝒓𝒂𝒓."
                )

    # ###############################################################
    # ## INÍCIO DA LÓGICA ATUALIZADA (DESGASTE EM TODOS) ##
    # ###############################################################
    if took_damage:
        # Encontra todas as peças de armadura e acessórios equipados
        equipped_armor_uids = []
        for slot in _ARMOR_SLOTS:
            uid = _get_equipped_uid(player_data, [slot])
            if uid:
                equipped_armor_uids.append(uid)
        
        # Se houver pelo menos uma peça...
        if equipped_armor_uids:
            # NOVO: Loop que passa por CADA item encontrado
            for uid_to_damage in equipped_armor_uids:
                cur, mx, broke_now = _consume_durability(player_data, uid_to_damage, 1)
                changed = True
                
                if broke_now:
                    # Pega o nome do item para uma mensagem mais clara
                    item_inst = _get_unique_inst(player_data, uid_to_damage)
                    item_name = (item_inst or {}).get("display_name", "Sua armadura")
                    log.append(
                        f"⚠️ {item_name} 𝒒𝒖𝒆𝒃𝒓𝒐𝒖 ({cur}/{mx}). "
                        f"𝑼𝒔𝒆 📜 𝑷𝒆𝒓𝒈𝒂𝒎𝒊𝒏𝒉𝒐 𝒅𝒆 𝑫𝒖𝒓𝒂𝒃𝒊𝒍𝒊𝒅𝒂𝒅𝒆 𝒑𝒂𝒓𝒂 𝒓𝒆𝒔𝒕𝒂𝒖𝒓𝒂𝒓."
                    )
    # ###############################################################
    # ## FIM DA LÓGICA ATUALIZADA ##
    # ###############################################################

    # Salva os dados se alguma durabilidade foi alterada
    if changed:
        player_manager.save_player_data(user_id, player_data)

    # Limpa as flags para a próxima batalha
    combat_details.pop("used_weapon", None)
    combat_details.pop("took_damage", None)

# -------------------------
# Críticos — helpers
# -------------------------
def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _diminishing_crit_chance_from_luck(luck: int) -> float:
    """
    Retorno decrescente: 100 * (1 - 0.99**luck)
    Ex.: Luck 10 ≈ 9.6%, Luck 30 ≈ 25.9%, Luck 50 ≈ 39.5%
    """
    try:
        l = max(0, int(luck))
    except Exception:
        l = 0
    return 100.0 * (1.0 - (0.99 ** l))


def _get_player_class_key(pdata: dict) -> str | None:
    # Versão local do normalizador
    def _as_dict(obj):
        return obj if isinstance(obj, dict) else {}
    candidates = [
        _as_dict(pdata.get("class")).get("type"),
        _as_dict(pdata.get("classe")).get("type"),
        pdata.get("class_type"),
        pdata.get("classe_tipo"),
        pdata.get("class_key"),
        pdata.get("classe"),
        pdata.get("class"),
    ]
    for c in candidates:
        if isinstance(c, str) and c.strip():
            return c.strip().lower()
    return None


def _crit_params_for_player(player_data: dict) -> dict:
    luck = int(player_manager.get_player_total_stats(player_data).get("luck", 5))

    chance = _diminishing_crit_chance_from_luck(luck)
    chance = _clamp(chance, 1.0, 40.0)

    mega_chance = min(25.0, luck / 2.0)
    mult = 1.6
    mega_mult = 2.0

    ckey = _get_player_class_key(player_data) or ""
    if ckey == "assassino":
        chance = min(45.0, chance + 5.0)
        mult = 1.6
        mega_mult = 2.1
    elif ckey == "guerreiro":
        mult = 1.7
        mega_mult = 2.0
    elif ckey == "mago":
        mult = 1.6
        mega_mult = 2.2
        mega_chance = min(30.0, mega_chance + 3.0)

    return {
        "chance": chance,
        "mega_chance": mega_chance,
        "mult": mult,
        "mega_mult": mega_mult,
        "min_damage": 1,
    }


def _crit_params_for_monster(details: dict) -> dict:
    luck = _mstat(details, 'luck', 5)
    chance = _diminishing_crit_chance_from_luck(luck)
    chance = _clamp(chance, 1.0, 30.0)

    mega_chance = min(15.0, luck / 3.0)
    mult = 1.5
    mega_mult = 1.75

    return {
        "chance": chance,
        "mega_chance": mega_chance,
        "mult": mult,
        "mega_mult": mega_mult,
        "min_damage": 1,
    }


def _roll_crit_and_damage(raw_attack: int, target_defense: int, params: dict) -> tuple[int, bool, bool]:
    """
    Aplica crítico ANTES da defesa, arredondando para cima.
    Retorna (final_damage, crit, mega).
    """
    r = random.random() * 100.0
    is_crit = (r <= float(params.get("chance", 0.0)))

    mult = 1.0
    mega = False
    if is_crit:
        r2 = random.random() * 100.0
        if r2 <= float(params.get("mega_chance", 0.0)):
            mult = float(params.get("mega_mult", 2.0))
            mega = True
        else:
            mult = float(params.get("mult", 1.6))

    boosted = math.ceil(float(raw_attack) * mult)
    dmg = max(int(params.get("min_damage", 1)), boosted - int(target_defense))
    return dmg, is_crit, mega


# --- penalidade de XP na derrota ---
def _apply_defeat_xp_penalty(player_data: dict, combat_details: dict) -> int:
    """
    Penaliza XP ao perder a batalha, EXCETO na floresta_sombria.
    """
    region_da_batalha = (combat_details or {}).get("region_key")
    if region_da_batalha == "floresta_sombria":
        return 0 # Retorna 0 de XP perdido, efetivamente cancelando a penalidade

    # A lógica original continua para todas as outras regiões
    base_reward = int(combat_details.get('monster_xp_reward', 0))
    loss = max(0, base_reward * 2)
    cur = int(player_data.get('xp', 0))
    new_xp = max(0, cur - loss)
    player_data['xp'] = new_xp
    return loss


# -------------------------
# Voltar ao menu da região
# -------------------------
async def _return_to_region_menu(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int, msg: str | None = None):
    """Sai do combate, seta idle e mostra o menu da região atual."""
    player = player_manager.get_player_data(user_id) or {}
    player['player_state'] = {'action': 'idle'}
    player_manager.save_player_data(user_id, player)

    if msg:
        await context.bot.send_message(chat_id, msg)

    await send_region_menu(context=context, user_id=user_id, chat_id=chat_id)


def _is_dungeon_battle(details: dict) -> bool:
    """Detecta se este combate pertence a uma run de dungeon."""
    return bool(details.get("dungeon_ctx") or details.get("dungeon_run") or details.get("dungeon_next_on_victory"))


# -------------------------
# Handler principal
# -------------------------
# Em handlers/combat_handler.py

async def combat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manipula as ações de combate: atacar ou fugir (UI sempre como VÍDEO/FOTO -> edit caption)."""
    query = update.callback_query
    await _safe_answer(query)

    user_id = query.from_user.id
    chat_id = query.message.chat_id

    player_data = player_manager.get_player_data(user_id)
    if not player_data:
        try:
            await query.edit_message_caption(caption="Não encontrei seus dados. Use /start para começar.")
        except BadRequest:
            await context.bot.send_message(chat_id=chat_id, text="Não encontrei seus dados. Use /start para começar.")
        return

    player_data["user_id"] = user_id

    state = player_data.get('player_state', {})
    if state.get('action') != 'in_combat':
        try:
            await query.edit_message_caption(caption="Você não está em combate no momento.")
        except BadRequest:
            await context.bot.send_message(chat_id=chat_id, text="Você não está em combate no momento.")
        return

    combat_details = dict(state.get('details', {}) or {})

    if 'monster_max_hp' not in combat_details:
        try:
            combat_details['monster_max_hp'] = int(combat_details.get('monster_hp', 1))
            player_data['player_state']['details'] = combat_details
            player_manager.save_player_data(user_id, player_data)
        except Exception:
            pass

    player_total_stats = player_manager.get_player_total_stats(player_data)
    log = list(combat_details.get('battle_log', []))

    action = query.data
    in_dungeon = _is_dungeon_battle(combat_details)

    # =============================
    # FUGA
    # =============================
    if action == 'combat_flee':
        player_ini = int(player_total_stats.get('initiative', 10))
        monster_ini = _mstat(combat_details, 'initiative', 5)
        bias = float(combat_details.get("flee_bias", 0.0))
        flee_chance = max(0.05, min(0.95, 0.75 + ((player_ini - monster_ini) / 100.0) + bias))

        if random.random() <= flee_chance:
            _apply_end_of_battle_durability(player_data, combat_details, log)

            try:
                await query.delete_message()
            except Exception:
                pass

            if in_dungeon:
                player_data['player_state'] = {'action': 'idle'}
                player_manager.save_player_data(user_id, player_data)
                await _return_to_region_menu(context, user_id, chat_id, "🏃 Você fugiu do calabouço.")
                return

            await _return_to_region_menu(context, user_id, chat_id, "🏃 𝑽𝒐𝒄𝒆̂ 𝒄𝒐𝒏𝒔𝒆𝒈𝒖𝒊𝒖 𝒇𝒖𝒈𝒊𝒓 𝒅𝒂 𝒃𝒂𝒕𝒂𝒍𝒉𝒂.")
            return
        else:
            log.append("🏃 𝑺𝒖𝒂 𝒕𝒆𝒏𝒕𝒂𝒕𝒊𝒗𝒂 𝒅𝒆 𝒇𝒖𝒈𝒂 𝒇𝒂𝒍𝒉𝒐𝒖!")

            dodge_chance = player_manager.get_player_dodge_chance(player_data)
            if random.random() < dodge_chance:
                log.append(f"⚡️ Mas com um movimento ágil, você se **esquivou** do ataque do inimigo!")
            else:
                monster_attack = _mstat(combat_details, 'attack', 1)
                player_defense = int(player_total_stats.get('defense', 3))
                mparams = _crit_params_for_monster(combat_details)
                monster_damage, mcrit, mmega = _roll_crit_and_damage(monster_attack, player_defense, mparams)

                if mcrit and mmega: log.append("☠️ 𝐌𝐄𝐆𝐀 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎 𝐃𝐎 𝐈𝐍𝐈𝐌𝐈𝐆𝐎! ☠️")
                elif mcrit: log.append("💀 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎 𝐃𝐎 𝐈𝐍𝐈𝐌𝐈𝐆𝐎! 💀")

                combat_details["took_damage"] = True
                player_data['current_hp'] = int(player_data.get('current_hp', 0)) - monster_damage
                log.append(f"⬅️ {combat_details.get('monster_name','Inimigo')} 𝒂𝒕𝒂𝒄𝒂!")
                log.append(f"🩸 𝑽𝒐𝒄𝒆̂ 𝒓𝒆𝒄𝒆𝒃𝒆 {monster_damage} 𝒅𝒆 𝒅𝒂𝒏𝒐.")

            if player_data['current_hp'] <= 0:
                xp_lost = _apply_defeat_xp_penalty(player_data, combat_details)
                _apply_end_of_battle_durability(player_data, combat_details, log)
                player_data['current_hp'] = int(player_manager.get_player_total_stats(player_data).get('max_hp', 50))
                player_data['player_state'] = {'action': 'idle'}
                player_manager.save_player_data(user_id, player_data)

                try:
                    await query.delete_message()
                except Exception:
                    pass

                if in_dungeon:
                    await _return_to_region_menu(context, user_id, chat_id, "💀 Você foi derrotado no calabouço.")
                    return

                defeat_text = (
                    f"𝑽𝒐𝒄𝒆̂ 𝒇𝒐𝒊 𝒅𝒆𝒓𝒓𝒐𝒕𝒂𝒅𝒐 𝒑𝒆𝒍𝒐 {combat_details.get('monster_name','inimigo')}!"
                    + (f"\n\n❌ 𝑷𝒆𝒏𝒂𝒍𝒊𝒅𝒂𝒅𝒆: Você perdeu {xp_lost} XP." if xp_lost > 0 else "")
                )
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=defeat_text,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➡️ 𝐂𝐨𝐧𝐭𝐢𝐧𝐮𝐚r", callback_data='continue_after_action')]])
                )
                return

            combat_details['battle_log'] = log
            player_data['player_state']['details'] = combat_details
            player_manager.save_player_data(user_id, player_data)

            new_text = format_combat_message(player_data)
            kb = [[InlineKeyboardButton("⚔️ 𝐀𝐭𝐚𝐜𝐚𝐫", callback_data='combat_attack'),
                   InlineKeyboardButton("🏃 𝐅𝐮𝐠𝐢𝐫", callback_data='combat_flee')]]
            reply_markup = InlineKeyboardMarkup(kb)
            await _edit_caption_only(query, new_text, reply_markup)
            return

    # =============================
    # ATAQUE
    # =============================
    if action == 'combat_attack':
        broken, w_uid, (w_cur, w_mx) = _weapon_broken(player_data)
        if broken:
            log.append(f"⛔ Sua arma está quebrada ({w_cur}/{w_mx}). 𝑼𝒔𝒆 𝒖𝒎 📜 𝑷𝒆𝒓𝒈𝒂𝒎𝒊𝒏𝒉𝒐 𝒅𝒆 𝑫𝒖𝒓𝒂𝒃𝒊𝒍𝒊𝒅𝒂𝒅𝒆 𝒑𝒂𝒓𝒂 𝒓𝒆𝒔𝒕𝒂𝒖𝒓𝒂𝒓.")
            combat_details['battle_log'] = log
            player_data['player_state']['details'] = combat_details
            player_manager.save_player_data(user_id, player_data)

            new_text = format_combat_message(player_data)
            kb = [[InlineKeyboardButton("⚔️ 𝐀𝐭𝐚𝐜𝐚𝐫", callback_data='combat_attack'),
                   InlineKeyboardButton("🏃 𝐅𝐮𝐠𝐢𝐫", callback_data='combat_flee')]]
            await _edit_caption_only(query, new_text, InlineKeyboardMarkup(kb))
            return

        combat_details["used_weapon"] = True

        player_attack = int(player_total_stats.get('attack', 5))
        monster_defense = _mstat(combat_details, 'defense', 0)

        pparams = _crit_params_for_player(player_data)
        player_damage, pcrit, pmega = _roll_crit_and_damage(player_attack, monster_defense, pparams)

        if pcrit and pmega: log.append("💥 𝐌𝐄𝐆𝐀 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎! 💥")
        elif pcrit: log.append("✨ 𝐀𝐂𝐄𝐑𝐓𝐎 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎! ✨")

        current_hp_before = int(combat_details.get('monster_hp', 1))
        combat_details['monster_hp'] = current_hp_before - player_damage
        if 'monster_max_hp' not in combat_details:
            combat_details['monster_max_hp'] = current_hp_before

        log.append(f"➡️ {player_data.get('character_name','𝑽𝒐𝒄𝒆̂')} 𝒂𝒕𝒂𝒄𝒂!")
        log.append(f"💥 𝑽𝒐𝒄𝒆̂ 𝒄𝒂𝒖𝒔𝒂 {player_damage} 𝒅𝒆 𝒅𝒂𝒏𝒐.")
        
        if combat_details['monster_hp'] > 0:
            double_attack_chance = player_manager.get_player_double_attack_chance(player_data)
            if random.random() < double_attack_chance:
                log.append("⚔️ Com sua velocidade, você consegue um...")
                log.append("💥 𝐀𝐓𝐀𝐐𝐔𝐄 𝐃𝐔𝐏𝐋𝐎! 💥")
                
                player_damage_2, pcrit_2, pmega_2 = _roll_crit_and_damage(player_attack, monster_defense, pparams)
                
                if pcrit_2 and pmega_2: log.append("💥 𝐌𝐄𝐆𝐀 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎 no segundo golpe! 💥")
                elif pcrit_2: log.append("✨ 𝐀𝐂𝐄𝐑𝐓𝐎 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎 no segundo golpe! ✨")

                combat_details['monster_hp'] -= player_damage_2
                log.append(f"💥 𝑽𝒐𝒄𝒆̂ 𝒄𝒂𝒖𝒔𝒂 mais {player_damage_2} 𝒅𝒆 𝒅𝒂𝒏𝒐.")
        
        # 2) Vitória → fim de batalha + consumo
        if combat_details['monster_hp'] <= 0:
            _apply_end_of_battle_durability(player_data, combat_details, log)
            
            # Atualiza a missão pessoal
            mission_manager.update_mission_progress(
                player_data, 'HUNT',
                details={'monster_id': combat_details.get('id'), 'region': combat_details.get('region_key'), 'is_elite': combat_details.get('is_elite', False)}
            )
            # Atualiza a missão de guilda
            clan_id = player_data.get("clan_id")
            if clan_id:
                mission_details = {
                    'monster_id': combat_details.get('id'), 
                    'region': combat_details.get('region_key'), 
                    'is_elite': combat_details.get('is_elite', False), 
                    'count': 1
                }
                
                await clan_manager.update_guild_mission_progress(
                    clan_id=clan_id, 
                    mission_type='HUNT', 
                    details=mission_details, 
                    context=context)
            
            if combat_details.get('is_elite', False):
                mission_manager.update_mission_progress(
                    player_data, 'HUNT_ELITE',
                    details={'monster_id': combat_details.get('id'), 'region': combat_details.get('region_key')}
                )

            # Multiplicadores base (Premium, etc.)
            xp_mult = float(player_manager.get_player_perk_value(player_data, 'xp_multiplier', 1.0))
            gold_mult = float(player_manager.get_player_perk_value(player_data, 'gold_multiplier', 1.0))
            
            # ===============================================
            # ## INÍCIO DA CORREÇÃO: APLICAR BUFFS DO CLÃ ##
            # ===============================================
            if clan_id:
                clan_buffs = clan_manager.get_clan_buffs(clan_id)
                
                # Adiciona o bónus de XP do clã (em percentagem)
                xp_bonus_percent = clan_buffs.get("xp_bonus_percent", 0)
                if xp_bonus_percent > 0:
                    xp_mult += (xp_bonus_percent / 100.0)
                
                # Adiciona o bónus de Ouro do clã (em percentagem)
                gold_bonus_percent = clan_buffs.get("gold_bonus_percent", 0)
                if gold_bonus_percent > 0:
                    gold_mult += (gold_bonus_percent / 100.0)
            # ===============================================
            # ## FIM DA CORREÇÃO ##
            # ===============================================

            xp_reward = int(float(combat_details.get('monster_xp_reward', 0)) * xp_mult)
            gold_reward = int(float(combat_details.get('monster_gold_drop', 0)) * gold_mult)

            looted_items_list = []
            for item in combat_details.get('loot_table', []):
                if random.random() * 100 <= float(item.get('drop_chance', 0)):
                    item_id = item.get('item_id')
                    if item_id:
                        looted_items_list.append(item_id)
            
            if in_dungeon and _dungeon_advance_after_victory:
                rewards_package = { "xp": xp_reward, "gold": gold_reward, "items": looted_items_list }
                player_data['current_hp'] = int(player_manager.get_player_total_stats(player_data).get('max_hp', 50))
                player_manager.save_player_data(user_id, player_data)
                try: await query.delete_message()
                except Exception: pass
                await _dungeon_advance_after_victory(
                    update, context, user_id=user_id, chat_id=chat_id,
                    combat_details=combat_details, rewards_to_accumulate=rewards_package
                )
                return
            else:
                player_data['xp'] = int(player_data.get('xp', 0)) + xp_reward
                if gold_reward > 0:
                    player_manager.add_gold(player_data, gold_reward)

                looted_items_text = ""
                if looted_items_list:
                    looted_items_text = "\n\n<b>𝑰𝒕𝒆𝒏𝒔 𝑨𝒅𝒒𝒖𝒊𝒓𝒊𝒅𝒐𝒔:</b>\n"
                    from collections import Counter
                    item_names = [(game_data.ITEMS_DATA.get(item_id, {}) or {}).get('display_name', item_id) for item_id in looted_items_list]
                    for name, count in Counter(item_names).items():
                        looted_items_text += f"- {count}x {name}\n"
                        item_key_to_add = next((key for key, val in game_data.ITEMS_DATA.items() if val.get('display_name') == name), name)
                        for _ in range(count):
                            player_manager.add_item_to_inventory(player_data, item_key_to_add)

                levels_gained, points_gained, level_up_message = 0, 0, ""
                while True:
                    current_level = int(player_data.get('level', 1))
                    xp_needed = int(game_data.get_xp_for_next_combat_level(current_level))
                    current_xp = int(player_data.get('xp', 0))
                    if current_xp < xp_needed: break
                    player_data['xp'] -= xp_needed
                    old_allowed = player_manager.allowed_points_for_level(player_data)
                    player_data['level'] = current_level + 1
                    new_allowed = player_manager.allowed_points_for_level(player_data)
                    delta_points = max(0, new_allowed - old_allowed)
                    player_data['stat_points'] = int(player_data.get('stat_points', 0)) + delta_points
                    levels_gained += 1
                    points_gained += delta_points        
                if levels_gained > 0:
            # Este 'if' agora serve APENAS para criar a mensagem de level up
                    nivel_txt = "nível" if levels_gained == 1 else "níveis"
                    ponto_txt = "ponto" if points_gained == 1 else "pontos"
                    level_up_message = (f"\n\n✨ <b>Parabéns!</b> Você subiu {levels_gained} {nivel_txt} "
                                f"(agora Nv. {player_data['level']}) e ganhou {points_gained} {ponto_txt} de atributo.")
        
                
                player_data['current_hp'] = int(player_manager.get_player_total_stats(player_data).get('max_hp', 50))
                
                monster_name = combat_details.get('monster_name', 'inimigo')
                victory_summary = (f"✅ Você derrotou {monster_name}!\n"
                                   f"+{xp_reward} XP, +{gold_reward} ouro."
                                   f"{looted_items_text}{level_up_message}")
                if xp_mult > 1 or gold_mult > 1:
                    victory_summary += "\n\n✨ 𝑩𝒐̂𝒏𝒖𝒔 𝑷𝒓𝒆𝒎𝒊𝒖𝒎 𝒂𝒑𝒍𝒊𝒄𝒂𝒅𝒐!"

                player_data['player_state'] = {'action': 'idle'}
                player_manager.save_player_data(user_id, player_data)

                try: await query.delete_message()
                except Exception: pass
                
                # =========================================================
                # 👇 INÍCIO DA NOVA LÓGICA DE ENVIO DE MÍDIA 👇
                # =========================================================
                media_key_to_use = None
                if looted_items_list:
                    primeiro_item_id = looted_items_list[0]
                    item_info = (game_data.ITEMS_DATA or {}).get(primeiro_item_id, {})
                    media_key_to_use = item_info.get("media_key")
                if not media_key_to_use:
                    media_key_to_use = "vitoria_sem_item"

                media_data = file_ids.get_file_data(media_key_to_use)
                keyboard = [[InlineKeyboardButton("➡️ 𝐂𝐨𝐧𝐭𝐢𝐧𝐮𝐚𝐫", callback_data='continue_after_action')]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                if media_data and media_data.get("id"):
                    media_id = media_data["id"]
                    media_type = (media_data.get("type") or "photo").lower()
                    try:
                        if media_type == "video":
                            await context.bot.send_video(chat_id=chat_id, video=media_id, caption=victory_summary, reply_markup=reply_markup, parse_mode='HTML')
                        else:
                            await context.bot.send_photo(chat_id=chat_id, photo=media_id, caption=victory_summary, reply_markup=reply_markup, parse_mode='HTML')
                    except Exception:
                        await context.bot.send_message(chat_id=chat_id, text=victory_summary, reply_markup=reply_markup, parse_mode='HTML')
                else:
                    await context.bot.send_message(chat_id=chat_id, text=victory_summary, reply_markup=reply_markup, parse_mode='HTML')
                # =========================================================
                # 👆 FIM DA NOVA LÓGICA 👆
                # =========================================================

                if int(player_data.get('level', 1)) >= 10 and not player_data.get('class'):
                    await show_class_selection_menu(update, context)
                return

        # 3) Monstro ataca
        dodge_chance = player_manager.get_player_dodge_chance(player_data)
        if random.random() < dodge_chance:
            log.append(f"⚡️ O inimigo tenta contra-atacar, mas você se ...")
            log.append("⚡️🏃‍♂️‍➡️ 𝔼𝕊ℚ𝕌𝕀𝕍𝔸! 🌀")
        else:
            monster_attack = _mstat(combat_details, 'attack', 1)
            player_defense = int(player_total_stats.get('defense', 3))
            mparams = _crit_params_for_monster(combat_details)
            monster_damage, mcrit, mmega = _roll_crit_and_damage(monster_attack, player_defense, mparams)
            if mcrit and mmega: log.append("☠️ 𝐌𝐄𝐆𝐀 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎 𝐃𝐎 𝐈𝐍𝐈𝐌𝐈𝐆𝐎! ☠️")
            elif mcrit: log.append("💀 𝐂𝐑𝐈́𝐓𝐈𝐂𝐎 𝐃𝐎 𝐈𝐍𝐈𝐌𝐈𝐆𝐎! 💀")
            combat_details["took_damage"] = True
            player_data['current_hp'] = int(player_data.get('current_hp', 0)) - monster_damage
            log.append(f"⬅️ {combat_details.get('monster_name','Inimigo')} 𝒂𝒕𝒂𝒄𝒂!")
            log.append(f"🩸 𝑽𝒐𝒄𝒆̂ 𝒓𝒆𝒄𝒆𝒃𝒆 {monster_damage} 𝒅𝒆 𝒅𝒂𝒏𝒐.")

        # 4) Derrota do jogador
        if player_data['current_hp'] <= 0:
            xp_lost = _apply_defeat_xp_penalty(player_data, combat_details)
            _apply_end_of_battle_durability(player_data, combat_details, log)
            player_data['current_hp'] = int(player_manager.get_player_total_stats(player_data).get('max_hp', 50))
            player_data['player_state'] = {'action': 'idle'}
            player_manager.save_player_data(user_id, player_data)
            try: await query.delete_message()
            except Exception: pass
            if in_dungeon:
                await _return_to_region_menu(context, user_id, chat_id, "💀 Você foi derrotado no calabouço.")
                return
            defeat_text = (f"𝑽𝒐𝒄𝒆̂ 𝒇𝒐𝒊 𝒅𝒆𝒓𝒓𝒐𝒕𝒂𝒅𝒐 𝒑𝒆𝒍𝒐 {combat_details.get('monster_name','𝒊𝒏𝒊𝒎𝒊𝒈𝒐')}!"
                           + (f"\n\n❌ 𝑷𝒆𝒏𝒂𝒍𝒊𝒅𝒂𝒅𝒆: Você perdeu {xp_lost} XP." if xp_lost > 0 else ""))
            await context.bot.send_message(
                chat_id=chat_id, text=defeat_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➡️ 𝑪𝒐𝒏𝒕𝒊𝒏𝒖𝒂𝒓", callback_data='continue_after_action')]])
            )
            return

        # 5) Continuidade da luta
        combat_details['battle_log'] = log
        player_data['player_state']['details'] = combat_details
        player_manager.save_player_data(user_id, player_data)

        new_text = format_combat_message(player_data)
        kb = [[InlineKeyboardButton("⚔️ 𝐀𝐭𝐚𝐜𝐚𝐫", callback_data='combat_attack'),
               InlineKeyboardButton("🏃 𝐅𝐮𝐠𝐢𝐫", callback_data='combat_flee')]]
        reply_markup = InlineKeyboardMarkup(kb)
        await _edit_caption_only(query, new_text, reply_markup)

# -------------------------
# Continuar → volta ao menu
# -------------------------
async def continue_after_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await _safe_answer(query)
    user_id = query.from_user.id
    chat_id = query.message.chat_id

    try:
        await query.delete_message()
    except Exception:
        pass

    await _return_to_region_menu(context, user_id, chat_id)


# Handlers
combat_handler = CallbackQueryHandler(combat_callback, pattern=r'^combat_(attack|flee)$')
continue_after_action_handler = CallbackQueryHandler(continue_after_action, pattern=r'^continue_after_action$')
