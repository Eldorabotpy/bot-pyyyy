import time
import uuid

# Dicionário global para guardar todas as lutas rolando no servidor simultaneamente
batalhas_ativas = {}

def iniciar_combate_grupo(equipe_herois, emboscada_mobs, regiao_atual):
    """
    equipe_herois: Lista de dicionários com os stats dos jogadores puxados do banco.
    emboscada_mobs: Lista de dicionários com os monstros gerados para a luta.
    """
    sala_id = f"arena_{uuid.uuid4().hex[:8]}"
    
    combatentes = []
    
    # 1. Prepara os Heróis para a Fila
    for heroi in equipe_herois:
        combatentes.append({
            "id": heroi["char_id"],
            "tipo": "heroi",
            "nome": heroi["nome"],
            "initiative": heroi.get("initiative", 5),
            "ref_dados": heroi # Guarda os stats completos
        })
        
    # 2. Prepara os Monstros para a Fila
    for i, mob in enumerate(emboscada_mobs):
        mob_id = f"mob_{i+1}"
        mob["id"] = mob_id # Injeta um ID único temporário no monstro
        combatentes.append({
            "id": mob_id,
            "tipo": "monstro",
            "nome": mob.get("name", "Monstro"),
            "initiative": mob.get("initiative", 2),
            "ref_dados": mob
        })
        
    # 3. A MÁGICA DO TURNO: Ordena do maior pro menor atributo de Iniciativa!
    combatentes.sort(key=lambda c: c["initiative"], reverse=True)
    
    # 4. Cria a Sala Oficial
    batalhas_ativas[sala_id] = {
        "sala_id": sala_id,
        "regiao": regiao_atual,
        "herois": { h["char_id"]: h for h in equipe_herois },
        "mobs": { m["id"]: m for m in emboscada_mobs },
        "fila_iniciativa": [c["id"] for c in combatentes], # Ex: ["heroi_1", "mob_2", "heroi_2"...]
        "index_turno_atual": 0,
        "tempo_inicio_turno": time.time()
    }
    
    # Retorna o ID da sala para o Socket avisar os jogadores
    return batalhas_ativas[sala_id]

def pegar_combatente_atual(sala_id):
    """Descobre de quem é a vez de jogar nesta exata sala."""
    sala = batalhas_ativas.get(sala_id)
    if not sala: return None
    
    id_da_vez = sala["fila_iniciativa"][sala["index_turno_atual"]]
    return id_da_vez

def avancar_turno(sala_id):
    """Passa a vez para o próximo da fila. Se chegar no final, recomeça a rodada."""
    sala = batalhas_ativas.get(sala_id)
    if not sala: return
    
    sala["index_turno_atual"] += 1
    
    # Se todo mundo já jogou, recomeça a fila (Nova Rodada!)
    if sala["index_turno_atual"] >= len(sala["fila_iniciativa"]):
        sala["index_turno_atual"] = 0
        
    # Reseta o relógio para o sistema anti-AFK
    sala["tempo_inicio_turno"] = time.time()
    
    return pegar_combatente_atual(sala_id)