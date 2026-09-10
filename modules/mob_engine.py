# modules/mob_engine.py
import threading
import random
import math
from modules.game_data.map_spawns import MAP_SPAWNS
from modules.game_data.monsters import MONSTERS_DATA

class GerenciadorCacada:
    def __init__(self, socketio):
        self.socketio = socketio
        self.mobs_vivos = {} 
        self.inicializar_mundo()

    def buscar_status_base(self, monster_id):
        """Procura o monstro dentro do seu monsters.py"""
        for categoria, lista_mobs in MONSTERS_DATA.items():
            for mob in lista_mobs:
                if mob.get("id") == monster_id:
                    return mob
        return None

    def gerar_mob_dinamico(self, config_spawn, regiao):
        """🎲 O MESTRE DE JOGO: Gera um monstro com nível e status sorteados"""
        base_stats = self.buscar_status_base(config_spawn["monster_id"])
        if not base_stats: return None

        mob_vivo = config_spawn.copy()
        mob_vivo["nome"] = base_stats.get("name", "Monstro Desconhecido")
        mob_vivo["regiao"] = regiao 
        
        # ==========================================
        # 🎲 SISTEMA DE RARIDADE (RESPEITANDO O MAX_LEVEL)
        # ==========================================
        nivel_base = base_stats.get("min_level", 1)
        nivel_maximo = base_stats.get("max_level", nivel_base)
        
        # Calcula quantos níveis existem entre o mínimo e o máximo
        gap_de_niveis = nivel_maximo - nivel_base
        
        # Sorteia o "Tier" do monstro
        # 0 = Nível Base, 1 = 25% do Gap, 2 = 50% do Gap, 3 = 75% do Gap, 4 = 100% (Level Máximo)
        tier_sorteado = random.choices([0, 1, 2, 3, 4], weights=[60, 25, 10, 4, 1], k=1)[0]
        
        if gap_de_niveis > 0:
            # Aplica a porcentagem do Tier no Gap de níveis
            niveis_extras = math.floor(gap_de_niveis * (tier_sorteado / 4.0))
        else:
            niveis_extras = 0
            
        nivel_final = nivel_base + niveis_extras
        mob_vivo["level"] = nivel_final
        
        # ==========================================
        # 2. MULTIPLICADORES ÉPICOS DE STATUS
        # ==========================================
        # Se ele pulou 10 níveis (Ex: 15 para 25), ele ganha (10 * 15%) = +150% de Status!
        mult_status = 1.0 + (niveis_extras * 0.15)
        mult_recompensa = 1.0 + (niveis_extras * 0.20)

        # 3. Aplica o multiplicador na Vida
        vida_calculada = math.floor(base_stats.get("hp", 100) * mult_status)
        mob_vivo["hp_max"] = vida_calculada
        mob_vivo["hp_atual"] = vida_calculada
        mob_vivo["max_hp"] = vida_calculada 
        mob_vivo["hp"] = vida_calculada
        
        # 4. Aplica o multiplicador no Combate
        mob_vivo["attack"] = math.floor(base_stats.get("attack", 5) * mult_status)
        mob_vivo["defense"] = math.floor(base_stats.get("defense", 0) * mult_status)
        
        # 5. Salva a recompensa gorda para quem derrotar o bicho!
        mob_vivo["xp_reward"] = math.floor(base_stats.get("xp_reward", 10) * mult_recompensa)
        mob_vivo["gold_drop"] = math.floor(base_stats.get("gold_drop", 0) * mult_recompensa)

        return mob_vivo

    def inicializar_mundo(self):
        """Monta o mapa sorteando os níveis da primeira geração de monstros"""
        for regiao, spawns in MAP_SPAWNS.items():
            self.mobs_vivos[regiao] = {}
            for config in spawns:
                mob_dinamico = self.gerar_mob_dinamico(config, regiao)
                if mob_dinamico:
                    self.mobs_vivos[regiao][config["spawn_id"]] = mob_dinamico
                else:
                    print(f"⚠️ CAÇADA: Monstro '{config['monster_id']}' não foi encontrado no monsters.py!")

    def obter_mobs_regiao(self, regiao):
        return self.mobs_vivos.get(regiao, {})

    def processar_morte(self, regiao, spawn_id):
        if regiao in self.mobs_vivos and spawn_id in self.mobs_vivos[regiao]:
            mob = self.mobs_vivos[regiao][spawn_id]
            tempo_respawn = mob.get("respawn_segundos", 15)

            # 🌌 FENDA DIMENSIONAL — contador de abates por mapa.
            # Conta só uma vez por morte real do mob vivo.
            if not mob.get("_abate_dimensional_contado"):
                mob["_abate_dimensional_contado"] = True

                try:
                    from modules.events import dimensional_boss_manager as dbm

                    resultado_dimensional = dbm.registrar_abate_mapa(
                        regiao=regiao,
                        spawn_id=spawn_id,
                        monster_id=mob.get("monster_id"),
                        socketio=self.socketio
                    )

                    if resultado_dimensional.get("evento_criado"):
                        print(
                            f"🌌 [DIMENSIONAL] Fenda criada automaticamente em {regiao} "
                            f"após abates. evento_id={resultado_dimensional.get('evento_id')}"
                        )

                except Exception as e:
                    print(f"⚠️ [DIMENSIONAL] Falha ao registrar abate para Fenda: {e}")
        
            self.socketio.emit('mobMapaMorreu', {"spawn_id": spawn_id})
            del self.mobs_vivos[regiao][spawn_id]
            
            # Guardamos a base de onde ele nasceu para rolar os dados novamente
            config_base = {
                "spawn_id": spawn_id, 
                "monster_id": mob["monster_id"], 
                "x": mob["x"], 
                "y": mob["y"], 
                "respawn_segundos": tempo_respawn
            }
            
            timer = threading.Timer(tempo_respawn, self.respawn_mob, args=[regiao, spawn_id, config_base])
            timer.daemon = True 
            timer.start()
                       
    def respawn_mob(self, regiao, spawn_id, config_base):
        """Faz o monstro voltar à vida rolando um NOVO nível aleatório!"""
        novo_mob = self.gerar_mob_dinamico(config_base, regiao)
        
        if novo_mob and regiao in self.mobs_vivos:
            self.mobs_vivos[regiao][spawn_id] = novo_mob
            
            self.socketio.emit('mobMapaNasceu', {
                "regiao": regiao,
                "spawn_id": spawn_id,
                "mob_data": novo_mob
            })