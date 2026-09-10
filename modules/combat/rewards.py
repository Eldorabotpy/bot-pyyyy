# modules/combat/rewards.py
# (VERSÃO CORRIGIDA: MONGODB PARTY + DIVISÃO JUSTA DE OURO/XP)

import logging
import asyncio
import random
from collections import Counter
from modules import player_manager, game_data
from modules.player.premium import PremiumManager
from modules.game_data.season_pass import adicionar_xp_passe
from modules.player.core import get_player_data, save_player_data
from modules.game_data.xp import add_combat_xp
from modules.season_manager import dar_xp_passe

# 🔥 A CORREÇÃO: Puxar do MongoDB em vez da Memória!
from modules.combat.party_engine import parties_collection

logger = logging.getLogger(__name__)
# ============================================================
# 🛡️ XP DE CLÃ POR COMBATE
# ============================================================

PERCENTUAL_XP_CLA_COMBATE = 0.10


def _adicionar_xp_cla_seguro(
    user_id,
    xp_recebido,
):
    """
    Entrega ao clã 10% do XP realmente recebido
    pelo jogador.

    A falha do sistema de clã nunca deve impedir
    a recompensa normal do combate.
    """

    try:
        xp_recebido = int(
            xp_recebido or 0
        )
    except (TypeError, ValueError):
        xp_recebido = 0

    if xp_recebido <= 0:
        return 0

    xp_cla = max(
        1,
        int(
            xp_recebido *
            PERCENTUAL_XP_CLA_COMBATE
        ),
    )

    try:
        # Importação local para evitar
        # dependência circular entre módulos.
        from modules.clan.clan_manager import (
            adicionar_xp_cla,
        )

        adicionou = adicionar_xp_cla(
            user_id=user_id,
            quantidade=xp_cla,
        )

        if adicionou:
            logger.info(
                "🛡️ [XP CLÃ] Jogador %s "
                "contribuiu com %s XP.",
                user_id,
                xp_cla,
            )

            return xp_cla

        return 0

    except Exception as erro:
        logger.warning(
            "⚠️ [XP CLÃ] Não foi possível "
            "entregar XP ao clã do jogador %s: %s",
            user_id,
            erro,
        )

        return 0
    
def calculate_victory_rewards(player_data: dict, combat_details: dict) -> tuple[int, int, list]:
    """Calcula XP, Ouro e Itens iniciais (Antes da divisão)."""
    try:
        base_xp = int(float(combat_details.get('monster_xp_reward', combat_details.get('xp_reward', 0))))
        base_gold = int(float(combat_details.get('monster_gold_drop', combat_details.get('gold_drop', 0))))
    except:
        base_xp = 0
        base_gold = 0

    premium = PremiumManager(player_data)
    xp_mult = float(premium.get_perk_value('xp_multiplier', 1.0))
    gold_mult = float(premium.get_perk_value('gold_multiplier', 1.0))

    xp_reward = int(base_xp * xp_mult)
    gold_reward = int(base_gold * gold_mult)
    
    looted_items = []
    loot_table = combat_details.get('loot_table', [])
    
    if loot_table and isinstance(loot_table, list):
        for item in loot_table:
            if not isinstance(item, dict): continue
            
            chance = float(item.get('drop_chance', 0))
            luck = int(player_data.get('total_stats', {}).get('luck', 0))
            chance += (luck * 0.1) 
            
            if random.random() * 100 <= chance:
                item_id = item.get('item_id')
                if item_id:
                    looted_items.append(item_id)
    
    return xp_reward, gold_reward, looted_items

def apply_and_format_victory(player_data: dict, monster_stats: dict, context=None) -> str:
    # 1. Calcula o total do saque BRUTO
    xp_bruto, gold_bruto, items = calculate_victory_rewards(player_data, monster_stats)

    # 👇 O passe agora recebe 100% do XP da batalha!
    xp_do_passe = xp_bruto
    player_id_str = str(player_data['_id'])

    # 2. 🔥 O GATILHO DA PARTY (Totalmente Síncrono) 🔥
    xp_final, gold_final = processar_recompensa_abate(
        player_id_str, xp_bruto, xp_do_passe, gold_bruto, items, player_data
    )

    # 3. Formata o Log para o ecrã do matador
    monster_name = monster_stats.get('name') or monster_stats.get('monster_name', 'Inimigo')
    text = f"🏆 <b>VITÓRIA!</b>\n\nVocê derrotou {monster_name}!\n"
    text += f"✨ XP: +{xp_final}\n💰 Ouro: +{gold_final}\n"

    if items:
        text += "\n<b>📦 Saque Encontrado (Partilhado!):</b>\n"
        for item_id in items:
            # O matador recebe o item dele aqui, na memória temporária
            player_manager.add_item_to_inventory(player_data, item_id, 1)
            from modules import game_data
            item_def = game_data.ITEMS_DATA.get(item_id, {})
            name = item_def.get('display_name', item_id)
            text += f"• 1x {name}\n"

    return text

def process_defeat(player_data: dict, combat_details: dict) -> tuple[str, bool]:
    """Processa derrota."""
    xp_lost = 0
    base_reward = int(combat_details.get('monster_xp_reward', 0))
    xp_lost = max(0, int(base_reward * 0.5))
    player_data['xp'] = max(0, int(player_data.get('xp', 0)) - xp_lost)
    
    monster_name = combat_details.get('name', 'Inimigo')
    summary = f"☠️ <b>Derrota!</b>\n\nVocê caiu para {monster_name}."
    if xp_lost > 0:
        summary += f"\n❌ Penalidade: -{xp_lost} XP"
    
    return summary, xp_lost > 0

def _calculate_rewards_from_cache(player_data: dict, battle_cache: dict) -> tuple[int, int, list]:
    monster_stats = battle_cache.get("monster_stats", {})
    if 'monster_xp_reward' not in monster_stats:
        monster_stats['monster_xp_reward'] = monster_stats.get('xp_reward', 0)
    if 'monster_gold_drop' not in monster_stats:
        monster_stats['monster_gold_drop'] = monster_stats.get('gold_drop', 0)
    return calculate_victory_rewards(player_data, monster_stats)

def process_defeat_from_cache(player_data: dict, battle_cache: dict) -> tuple[str, bool]:
    return process_defeat(player_data, battle_cache.get("monster_stats", {}))

async def processar_recompensa_abate(matador_id, xp_base_combate, xp_base_passe, ouro_base, itens_looteados, player_data_memoria):
    from bson import ObjectId 
    from modules.game_data.xp import add_combat_xp_inplace, add_combat_xp
    
    print(f"\n{'='*40}\n🗡️ [DEBUG PARTY LOOT] INICIANDO DIVISÃO\n{'='*40}")
    print(f"Matador ID: {matador_id}")
    
    grupo = parties_collection.find_one({"membros": str(matador_id)})

    if not grupo:
        print(
            "🚨 [RESULTADO] Jogador NÃO está "
            "em grupo (Modo Solo)."
        )

        # XP normal do jogador.
        add_combat_xp_inplace(
            player_data_memoria,
            xp_base_combate,
        )

        # XP de contribuição para o clã.
        xp_cla_ganho = _adicionar_xp_cla_seguro(
            user_id=matador_id,
            xp_recebido=xp_base_combate,
        )

        if xp_cla_ganho > 0:
            print(
                f"   🛡️ Clã recebeu "
                f"+{xp_cla_ganho} XP."
            )

        if ouro_base > 0:
            player_manager.add_gold(
                player_data_memoria,
                ouro_base,
            )

        return xp_base_combate, ouro_base

    else:
        membros = grupo.get("membros", [])
        qtd_membros = len(membros)
        print(f"✅ [RESULTADO] Party encontrada! {qtd_membros} membros: {membros}")
        
        bonus_party_mult = 1.0 + (0.05 * (qtd_membros - 1))
        xp_combate_dividido = int((xp_base_combate / qtd_membros) * bonus_party_mult)
        ouro_dividido = int((ouro_base / qtd_membros) * bonus_party_mult)

        for membro_id_str in membros:
            print(f"\n👉 Processando membro: {membro_id_str}")
            
            if str(membro_id_str) == str(matador_id):
                print(
                    "   👑 É o Matador! Atualizando "
                    "a memória temporária (RAM)."
                )

                add_combat_xp_inplace(
                    player_data_memoria,
                    xp_combate_dividido,
                )

                xp_cla_ganho = _adicionar_xp_cla_seguro(
                    user_id=membro_id_str,
                    xp_recebido=xp_combate_dividido,
                )

                if xp_cla_ganho > 0:
                    print(
                        f"   🛡️ Clã do matador recebeu "
                        f"+{xp_cla_ganho} XP."
                    )

                if ouro_dividido > 0:
                    player_manager.add_gold(
                        player_data_memoria,
                        ouro_dividido,
                    )
                
            else:
                print("   🛡️ É um Aliado! Atualizando direto no Banco de Dados.")
                try:
                    membro_oid = ObjectId(membro_id_str)
                except:
                    membro_oid = membro_id_str

                try:
                    # O motor assíncrono também já está blindado e alimenta o Passe lá dentro!
                    await add_combat_xp(
                        membro_oid,
                        xp_combate_dividido,
                    )

                    xp_cla_ganho = _adicionar_xp_cla_seguro(
                        user_id=membro_id_str,
                        xp_recebido=xp_combate_dividido,
                    )

                    if xp_cla_ganho > 0:
                        print(
                            f"   🛡️ Clã do aliado recebeu "
                            f"+{xp_cla_ganho} XP."
                        )

                    pdata = await get_player_data(
                        membro_oid
                    )
                    
                    if not pdata:
                        pdata = await get_player_data(membro_id_str)
                        if pdata: membro_oid = membro_id_str

                    if pdata:
                        if ouro_dividido > 0:
                            player_manager.add_gold(pdata, ouro_dividido)

                        if itens_looteados:
                            for item_id in itens_looteados:
                                player_manager.add_item_to_inventory(pdata, item_id, 1)

                        await save_player_data(membro_oid, pdata)
                        
                        # 4. A NOTIFICAÇÃO DOURADA NO CHAT DO ALIADO
                        try:
                            from main import socketio, jogadores_online
                            for sid, info in jogadores_online.items():
                                if str(info.get('char_id')) == str(membro_id_str):
                                    socketio.emit('novaMensagemChat', {
                                        'remetente': '🎁 Saque', 
                                        'texto': f'A Party abateu um inimigo! Ganhaste +{xp_combate_dividido} XP e +{ouro_dividido} Ouro.', 
                                        'tipo': 'loot'
                                    }, room=sid)
                                    break
                        except Exception as erro_chat:
                            print(f"      ⚠️ Falha ao avisar aliado no chat: {erro_chat}")
                            
                except Exception as e:
                    print(f"      ❌ CRASH AO SALVAR ALIADO: {str(e)}")

        print(f"{'='*40}\n")
        return xp_combate_dividido, ouro_dividido