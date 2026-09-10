# modules/combat/party_engine.py
import random
from pymongo import MongoClient
from bson import ObjectId
from config import MONGO_CONNECTION_STRING

# 👇 CONEXÃO COM O MONGODB 👇
client = MongoClient(MONGO_CONNECTION_STRING)
db = client["eldora_bot"]
parties_collection = db["grupos_party"]

# ==========================================
# 🛡️ XP DE CLÃ DOS MEMBROS DA PARTY
# ==========================================

PERCENTUAL_XP_CLA_COMBATE = 0.10


def _adicionar_xp_cla_party_seguro(
    user_id,
    xp_recebido,
):
    """
    Entrega ao clã 10% do XP recebido
    por um membro da party.

    Uma falha no clã não interrompe
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
        from modules.clan.clan_manager import (
            adicionar_xp_cla,
        )

        sucesso = adicionar_xp_cla(
            user_id=user_id,
            quantidade=xp_cla,
        )

        if sucesso:
            print(
                f"🛡️ [XP CLÃ PARTY] "
                f"Jogador {user_id} contribuiu "
                f"com +{xp_cla} XP."
            )

            return xp_cla

    except Exception as erro:
        print(
            "⚠️ [XP CLÃ PARTY] "
            f"Falha para {user_id}: {erro}"
        )

    return 0

def obter_grupo_do_jogador(char_id):
    """Procura se o jogador já está em QUALQUER grupo"""
    try:
        grupo = parties_collection.find_one({"membros": str(char_id)})
        if grupo:
            grupo["_id"] = str(grupo["_id"])
        return grupo
    except:
        return None

def sair_ou_desfazer_grupo(char_id):
    """Remove o jogador ou destrói o grupo se for o líder"""
    grupo = obter_grupo_do_jogador(char_id)
    if not grupo: return False, "Não estás em nenhum grupo.", []
    
    party_id = ObjectId(grupo["_id"])
    
    if grupo["lider"] == str(char_id):
        parties_collection.delete_one({"_id": party_id})
        membros_afetados = [m for m in grupo.get("membros", []) if m != str(char_id)]
        return True, "O líder desfez o grupo.", membros_afetados
    
    parties_collection.update_one(
        {"_id": party_id},
        {"$pull": {"membros": str(char_id)}, "$unset": {f"nomes_membros.{char_id}": ""}}
    )
    membros_restantes = [m for m in grupo.get("membros", []) if m != str(char_id)]
    return True, "Saíste do grupo.", membros_restantes

def criar_novo_grupo(lider_id, lider_nome, mapa_atual):
    sair_ou_desfazer_grupo(lider_id)
    novo_grupo = {
        "lider": str(lider_id),
        "lider_nome": lider_nome,
        "membros": [str(lider_id)],
        "nomes_membros": {str(lider_id): lider_nome},
        "mapa": mapa_atual
    }
    resultado = parties_collection.insert_one(novo_grupo)
    return str(resultado.inserted_id)

def adicionar_membro(party_id, char_id, char_nome):
    try:
        if obter_grupo_do_jogador(char_id):
            return False, "Já estás noutro grupo! Sai primeiro."
            
        grupo = parties_collection.find_one({"_id": ObjectId(party_id)})
        if not grupo: return False, "Grupo não existe."
        if len(grupo.get('membros', [])) >= 5: return False, "Grupo cheio (máx 5)."
            
        parties_collection.update_one(
            {"_id": ObjectId(party_id)},
            {"$push": {"membros": str(char_id)}, "$set": {f"nomes_membros.{char_id}": char_nome}}
        )
        return True, "Entrou no grupo!"
    except Exception as e:
        return False, "Erro ao buscar o grupo no banco."

def obter_grupo(party_id):
    try:
        grupo = parties_collection.find_one({"_id": ObjectId(party_id)})
        if grupo: grupo["_id"] = str(grupo["_id"])
        return grupo
    except:
        return None

# ==========================================
# 👇 MANTENHA AS FUNÇÕES DE CURA DO BOSS 👇
# ==========================================
def calculate_heal_amount(caster_stats, target_max_hp, effect_data):
    amount = 0
    if "amount_percent_max_hp" in effect_data:
        pct = float(effect_data["amount_percent_max_hp"])
        amount = int(target_max_hp * pct)
    elif effect_data.get("heal_type") == "magic_attack":
        magic_atk = caster_stats.get("magic_attack", caster_stats.get("attack", 10))
        scale = float(effect_data.get("heal_scale", 1.0))
        amount = int(magic_atk * scale)
    elif "amount_flat" in effect_data:
        amount = int(effect_data["amount_flat"])
    return amount

def process_party_effects(caster_id, caster_name, skill_data, caster_stats, all_active_states):
    logs = []
    effects = skill_data.get("effects", {})
    affected_count = 0
    
    if "party_heal" in effects:
        heal_def = effects["party_heal"]
        for pid, state in all_active_states.items():
            if state['hp'] <= 0: continue 
            heal_val = calculate_heal_amount(caster_stats, state['max_hp'], heal_def)
            if heal_val > 0:
                old_hp = state['hp']
                state['hp'] = min(state['max_hp'], state['hp'] + heal_val)
                real_heal = state['hp'] - old_hp
                if real_heal > 0:
                    affected_count += 1
                    if pid != caster_id:
                        current_log = state.get('log', '')
                        state['log'] = current_log + f"\n💚 {caster_name} te curou (+{real_heal})"
        if affected_count > 0:
            logs.append(f"💚 𝐂𝐮𝐫𝐚 𝐞𝐦 𝐆𝐫𝐮𝐩𝐨: {affected_count} aliados recuperados.")

    if "party_mana" in effects:
        mana_def = effects["party_mana"]
        affected_count = 0
        for pid, state in all_active_states.items():
            if state['hp'] <= 0: continue
            val = 0
            if "amount_flat" in mana_def: val = int(mana_def["amount_flat"])
            if val > 0:
                state['mp'] = min(state['max_mp'], state['mp'] + val)
                affected_count += 1
                if pid != caster_id:
                    state['log'] = state.get('log', '') + f"\n💙 {caster_name} restaurou sua Mana (+{val})"
        if affected_count > 0:
            logs.append(f"💙 𝐌𝐚𝐧𝐚 𝐞𝐦 𝐆𝐫𝐮𝐩𝐨: {affected_count} aliados recuperados.")

    if "party_buff" in effects:
        logs.append("🛡️ Buff de grupo aplicado (Efeito visual).")

    return logs

# ==========================================
# 💰 DIVISÃO DE RECOMPENSAS DO GRUPO (SISTEMA ANTI-SANGUESSUGA)
# ==========================================
def dividir_recompensas_grupo(char_id, xp_total, gold_total):
    """
    Calcula e divide o XP e Ouro APENAS entre os membros do grupo que estão ONLINE.
    """
    from modules.player.core import users_collection
    from bson import ObjectId
    import sys

    grupo = obter_grupo_do_jogador(char_id)
    
    if not grupo or len(grupo.get("membros", [])) <= 1:
        return False, xp_total, gold_total, []
        
    todos_membros = grupo.get("membros", [])
    
    # 1. 🛡️ O RADAR ANTI-SANGUESSUGA (BLINDADO CONTRA LISTAS FANTASMAS)
    membros_online = []
    
    try:
        # Tenta ler a memória real do servidor em execução (onde os jogadores estão logados de verdade)
        modulo_principal = sys.modules.get('__main__') or sys.modules.get('main')
        jogadores_online_reais = getattr(modulo_principal, 'jogadores_online', {})
        
        # O PARAQUEDAS: Se a lista do servidor estiver inacessível, assumimos que estão todos online para não quebrar a Party!
        if not jogadores_online_reais:
            membros_online = todos_membros
        else:
            ids_online_no_servidor = [str(info.get('char_id')) for info in jogadores_online_reais.values()]
            for membro in todos_membros:
                # O matador (char_id) é SEMPRE considerado online, e verificamos o resto no radar
                if str(membro) in ids_online_no_servidor or str(membro) == str(char_id):
                    membros_online.append(membro)
    except Exception as e:
        print("Erro no Radar da Party:", e)
        membros_online = todos_membros # Fallback de emergência
        
    # 2. Se só sobrou você lutando (os outros caíram/saíram), devolve 100% do prémio para você!
    num_membros_ativos = len(membros_online)
    if num_membros_ativos <= 1:
        return False, xp_total, gold_total, []
        
    # 3. BÔNUS DE GRUPO: +20% de Recompensas baseadas no grupo
    xp_com_bonus = int(xp_total * 1.20)
    gold_com_bonus = int(gold_total * 1.20)
    
    # 4. 🍕 Divide a pizza APENAS entre os guerreiros ativos!
    xp_por_membro = (
        max(
            1,
            xp_com_bonus // num_membros_ativos,
        )
        if xp_com_bonus > 0
        else 0
    )

    gold_por_membro = (
        max(
            1,
            gold_com_bonus // num_membros_ativos,
        )
        if gold_com_bonus > 0
        else 0
    )
    
    membros_ids_str = [str(m) for m in membros_online]
    
    # 5. Entrega a recompensa aos aliados ativos.
    #
    # O matador não é atualizado aqui porque o stats.py
    # já atualiza o documento dele e entrega seu XP de clã.
    for membro_id in membros_online:
        if str(membro_id) == str(char_id):
            continue

        try:
            membro_oid = ObjectId(
                str(membro_id)
            )

            resultado_player = (
                users_collection.update_one(
                    {
                        "_id": membro_oid,
                    },
                    {
                        "$inc": {
                            "xp": xp_por_membro,
                            "gold": gold_por_membro,
                        }
                    },
                )
            )

            if resultado_player.matched_count != 1:
                print(
                    "⚠️ [PARTY RECOMPENSA] "
                    f"Aliado não encontrado: {membro_id}"
                )

                continue

            # Depois de confirmar a recompensa,
            # entrega a contribuição ao clã do aliado.
            xp_cla_ganho = (
                _adicionar_xp_cla_party_seguro(
                    user_id=membro_id,
                    xp_recebido=xp_por_membro,
                )
            )

            if xp_cla_ganho > 0:
                print(
                    "   🛡️ Clã do aliado "
                    f"recebeu +{xp_cla_ganho} XP."
                )

            # Limpa o cache para o aliado enxergar
            # o novo XP e ouro imediatamente.
            # A limpeza do cache será realizada
            # pelo fluxo assíncrono de recompensa.

        except Exception as erro:
            print(
                "❌ [PARTY RECOMPENSA] "
                f"Erro ao premiar aliado "
                f"{membro_id}: {erro}"
            )
        
    return True, xp_por_membro, gold_por_membro, membros_ids_str
