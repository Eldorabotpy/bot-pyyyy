# pvp/tournament_system.py

import asyncio
import random
import logging
import html
from datetime import datetime

# Importações dos seus módulos existentes
from modules import player_manager
# CORREÇÃO: Importamos a collection para pegar o DB
from modules.player.core import players_collection 
from . import pvp_battle 

logger = logging.getLogger(__name__)

# =================================================================
# ⚙️ CONFIGURAÇÃO DE CANAL DE AVISOS
# =================================================================
TOURNAMENT_GROUP_ID = -1002881364171  # ID do Grupo
TOURNAMENT_TOPIC_ID = 805             # ID do Tópico (message_thread_id)

DOC_ID = "tournament_active"

CURRENT_MATCH_STATE = {
    "p1": None, 
    "p2": None,
    "ready": set(),
    "task": None,
    "active": False
}

# --- SETUP DO BANCO DE DADOS ---
if players_collection is not None:
    db = players_collection.database
else:
    db = None
    logger.error("❌ Erro Crítico no Torneio: players_collection é None.")

# --- FUNÇÃO AUXILIAR DE ENVIO ---
async def _enviar_msg_torneio(context, text):
    """Envia mensagem no Grupo e Tópico configurados."""
    try:
        await context.bot.send_message(
            chat_id=TOURNAMENT_GROUP_ID,
            message_thread_id=TOURNAMENT_TOPIC_ID,
            text=text,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"❌ Erro ao enviar mensagem no torneio: {e}")

# --- BANCO DE DADOS ---

def get_tournament_data():
    """Busca ou cria os dados do torneio no Mongo."""
    if db is None: return {}
    
    collection = db.system_data 
    data = collection.find_one({"_id": DOC_ID})
    
    if not data:
        data = {
            "_id": DOC_ID, 
            "status": "idle",
            "participants": [],
            "bracket": [],          
            "round_winners": [],    
            "round_number": 0,      
        }
        collection.insert_one(data)
    return data

def save_tournament_data(data):
    if db is None: return
    db.system_data.replace_one({"_id": DOC_ID}, data, upsert=True)

# --- FASE 1: INSCRIÇÃO ---

async def abrir_inscricoes(context, chat_id_admin):
    data = get_tournament_data()
    data["status"] = "registration"
    data["participants"] = [] 
    data["bracket"] = []
    data["round_winners"] = []
    data["round_number"] = 0
    save_tournament_data(data)
    
    msg = (
        "🎺 <b>TORNEIO DE ELDORA - INSCRIÇÕES ABERTAS!</b> 🎺\n\n"
        "O Rei convoca os guerreiros para a arena!\n\n"
        "1. Vá no privado do Bot.\n"
        "2. Entre no Menu <b>⚔️ PvP</b>.\n"
        "3. Clique em <b>✍️ Inscrever-se</b>.\n\n"
        "⏳ <i>As chaves e convocações serão postadas aqui neste tópico!</i>"
    )
    
    await _enviar_msg_torneio(context, msg)
    
    if chat_id_admin != TOURNAMENT_GROUP_ID:
        try: await context.bot.send_message(chat_id_admin, "✅ Inscrições abertas!")
        except: pass

async def registrar_jogador(user_id):
    data = get_tournament_data()
    if data["status"] != "registration":
        return False, "❌ As inscrições não estão abertas."
    
    if user_id in data["participants"]:
        return False, "✅ Você já está inscrito!"
        
    data["participants"].append(user_id)
    save_tournament_data(data)
    return True, "✍️ <b>Inscrição Confirmada!</b>"

# --- FASE 2: GERAÇÃO DA CHAVE ---

async def fechar_inscricoes_e_gerar_chave(context, chat_id_admin):
    data = get_tournament_data()
    players = data["participants"]
    
    if len(players) < 2:
        await context.bot.send_message(chat_id_admin, "❌ Jogadores insuficientes (Mínimo 2).")
        return
    
    random.shuffle(players)
    
    # Inicia a Rodada 1
    data["status"] = "active"
    data["round_number"] = 1
    data["round_winners"] = []
    
    # ⚠️ AQUI ESTAVA O ERRO: Agora usamos await
    bracket_text = await _gerar_pares_e_texto(data, players)
    save_tournament_data(data)
    
    await _enviar_msg_torneio(context, bracket_text)
    
    if chat_id_admin != TOURNAMENT_GROUP_ID:
        try: await context.bot.send_message(chat_id_admin, "✅ Chaves geradas e postadas!")
        except: pass

# --- NOVA VERSÃO ASYNC PARA PEGAR NOMES ---
async def _gerar_pares_e_texto(data, lista_jogadores):
    bracket = []
    
    # Bye (Ímpar) - O último passa direto
    if len(lista_jogadores) % 2 != 0:
        bye_player = lista_jogadores.pop()
        data["round_winners"].append(bye_player)

    while len(lista_jogadores) >= 2:
        p1 = lista_jogadores.pop(0)
        p2 = lista_jogadores.pop(0)
        bracket.append([p1, p2])
    
    data["bracket"] = bracket
    
    rodada = data["round_number"]
    texto = f"🔒 <b>INSCRIÇÕES ENCERRADAS!</b>\n🔥 <b>Iniciando Rodada {rodada}</b> 🔥\n\n📜 <b>Ordem de Combate:</b>\n"
    
    # Loop assíncrono para buscar nomes
    for i, pair in enumerate(bracket):
        try:
            # Busca dados do jogador 1
            p1_data = await player_manager.get_player_data(pair[0])
            n1 = p1_data.get("character_name", f"ID: {pair[0]}") if p1_data else f"ID: {pair[0]}"
            
            # Busca dados do jogador 2
            p2_data = await player_manager.get_player_data(pair[1])
            n2 = p2_data.get("character_name", f"ID: {pair[1]}") if p2_data else f"ID: {pair[1]}"
            
            # Escapa HTML para evitar erros se alguém tiver nome tipo "<B>"
            n1 = html.escape(n1)
            n2 = html.escape(n2)
            
            texto += f"⚔️ Luta {i+1}: <b>{n1}</b> 🆚 <b>{n2}</b>\n"
        except Exception as e:
            logger.error(f"Erro ao pegar nomes no torneio: {e}")
            texto += f"⚔️ Luta {i+1}: <code>{pair[0]}</code> 🆚 <code>{pair[1]}</code>\n"
            
    texto += "\n📢 <b>O Admin iniciará os combates em breve!</b>"
    return texto

# --- FASE 3: CONTROLE DE LUTAS ---

async def chamar_proxima_luta(context, chat_id_admin):
    data = get_tournament_data()
    bracket = data.get("bracket", [])
    
    if not bracket:
        await context.bot.send_message(chat_id_admin, "⚠️ Nenhuma luta na fila (Bracket vazio).")
        return

    next_match = bracket[0]
    p1_id, p2_id = next_match[0], next_match[1]
    
    # Configura Timer
    CURRENT_MATCH_STATE["p1"] = p1_id
    CURRENT_MATCH_STATE["p2"] = p2_id
    CURRENT_MATCH_STATE["ready"] = set()
    CURRENT_MATCH_STATE["active"] = True
    
    if CURRENT_MATCH_STATE["task"]: CURRENT_MATCH_STATE["task"].cancel()
    
    CURRENT_MATCH_STATE["task"] = asyncio.create_task(
        _timer_wo_task(context, p1_id, p2_id)
    )

    # Busca nomes para o anúncio
    p1_d = await player_manager.get_player_data(p1_id)
    p2_d = await player_manager.get_player_data(p2_id)
    n1 = p1_d.get("character_name", "Guerreiro") if p1_d else "Desconhecido"
    n2 = p2_d.get("character_name", "Guerreiro") if p2_d else "Desconhecido"
    
    msg = (
        f"⚔️ <b>CONVOCAÇÃO DE COMBATE!</b> ⚔️\n\n"
        f"🔴 <b>{html.escape(n1)}</b> 🆚 🔵 <b>{html.escape(n2)}</b>\n\n"
        f"⚠️ <b>Vocês têm 2 MINUTOS!</b>\n"
        f"Vão no menu PvP e cliquem em <b>'ESTOU PRONTO'</b>."
    )
    
    await _enviar_msg_torneio(context, msg)

async def confirmar_prontidao(user_id, context):
    if not CURRENT_MATCH_STATE["active"]: return "❌ Nenhuma luta ativa."
    if user_id not in [CURRENT_MATCH_STATE["p1"], CURRENT_MATCH_STATE["p2"]]: return "❌ Você não é convocado."
    if user_id in CURRENT_MATCH_STATE["ready"]: return "✅ Já confirmado."
        
    CURRENT_MATCH_STATE["ready"].add(user_id)
    
    if len(CURRENT_MATCH_STATE["ready"]) == 2:
        if CURRENT_MATCH_STATE["task"]: CURRENT_MATCH_STATE["task"].cancel()
        await _executar_luta(context)
        return "⚔️ <b>LUTA INICIADA!</b> Olhe o grupo!"
        
    return "✅ <b>Confirmado!</b> Aguardando oponente..."

async def _timer_wo_task(context, p1_id, p2_id):
    try:
        await asyncio.sleep(120) 
        prontos = CURRENT_MATCH_STATE["ready"]
        
        if p1_id in prontos: vencedor, motivo = p1_id, "W.O. (Oponente faltou)"
        elif p2_id in prontos: vencedor, motivo = p2_id, "W.O. (Oponente faltou)"
        else: vencedor, motivo = random.choice([p1_id, p2_id]), "W.O. Duplo (Sorteio)"

        await _finalizar_luta_logica(context, vencedor, None, motivo_wo=motivo)
    except asyncio.CancelledError: pass

async def _executar_luta(context):
    p1, p2 = CURRENT_MATCH_STATE["p1"], CURRENT_MATCH_STATE["p2"]
    
    # --- NIVELAMENTO ---
    NIVEL_DO_TORNEIO = 50 
    
    winner_id, log = await pvp_battle.simular_batalha_completa(
        p1, 
        p2, 
        nivel_padrao=NIVEL_DO_TORNEIO 
    )
    
    await _finalizar_luta_logica(context, winner_id, log)

# --- FASE 4: PROGRESSÃO ---

async def _finalizar_luta_logica(context, winner_id, log, motivo_wo=None):
    CURRENT_MATCH_STATE["active"] = False
    CURRENT_MATCH_STATE["ready"] = set()
    
    data = get_tournament_data()
    if data["bracket"]: data["bracket"].pop(0)
    
    if winner_id:
        data["round_winners"].append(winner_id)
    
    p_data = await player_manager.get_player_data(winner_id)
    nome = p_data.get("character_name", "Guerreiro") if p_data else "Guerreiro"
    
    if motivo_wo:
        msg = f"⏱️ <b>FIM POR TEMPO!</b>\n🏆 <b>Vencedor:</b> {html.escape(nome)}\nℹ️ {motivo_wo}"
    else:
        # Pega as últimas linhas do log para mostrar o resumo
        resumo = log[0] + "\n...\n" + "\n".join(log[-8:])
        msg = f"🏆 <b>VITÓRIA!</b> ({html.escape(nome)} avança)\n\n{resumo}"
    
    await _enviar_msg_torneio(context, msg)

    # Verifica fim da Rodada
    if not data["bracket"]:
        vencedores = data["round_winners"]
        
        if len(vencedores) == 1:
            campeao_id = vencedores[0]
            data["status"] = "finished"
            save_tournament_data(data)
            
            p_win = await player_manager.get_player_data(campeao_id)
            nome_win = p_win.get("character_name", "Lendário") if p_win else "Lendário"
            
            msg_final = (
                f"🎉🏆 <b>TEMOS UM CAMPEÃO!</b> 🏆🎉\n\n"
                f"👑 <b>{html.escape(nome_win)}</b> venceu o Torneio de Eldora!\n"
            )
            await _enviar_msg_torneio(context, msg_final)
            
        elif len(vencedores) > 1:
            data["round_number"] += 1
            next_players = list(vencedores)
            data["round_winners"] = [] 
            
            # ⚠️ TAMBÉM ATUALIZADO AQUI
            bracket_text = await _gerar_pares_e_texto(data, next_players)
            save_tournament_data(data)
            
            await _enviar_msg_torneio(context, f"🔄 <b>RODADA ENCERRADA!</b> Próxima fase...\n\n{bracket_text}")
    else:
        save_tournament_data(data)
        await _enviar_msg_torneio(context, "📢 <b>Próxima luta pronta! Aguardando chamada do Admin.</b>")