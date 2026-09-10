# ==============================================================================
# ARQUIVO: eventos_invasao.py - GERENCIADOR DE ONDAS E DROPS (VERSÃO CORRIGIDA)
# ==============================================================================
import random
import threading
import time
import asyncio # Caso precises de rodar a função async
from modules.combat.rewards import processar_recompensa_abate
from bson.objectid import ObjectId
from modules.player.combat_stats import get_combat_stats_sync, aplicar_combat_stats_no_player
try:
    from modules.game_data.data import WAVE_DEFINITIONS 
except ImportError:
    # Se tiver guardado o data.py dentro da pasta de modulos
    from modules.game_data.data import WAVE_DEFINITIONS

MAX_JOGADORES_INVASAO = 20
MAX_GRUPOS_INVASAO = 4
MAX_MEMBROS_POR_FRENTE = 5

BALANCE_INVASAO = {
    "minions_min": 3,
    "minions_max": 6,

    "limite_minions_min": 4,
    "limite_minions_max": 8,

    "delay_spawn_onda": 4.0,
    "tempo_entre_ondas": 10.0,

    "boss_hp_base": 1.05,
    "boss_hp_por_jogador": 0.28,

    "minion_hp_base": 0.70,
    "minion_hp_por_jogador": 0.14,

    "atk_onda": 0.10,
    "atk_jogador": 0.015,

    "def_onda": 0.07,
}

FRENTES_INVASAO = [
    {
        "id": "norte",
        "nome": "Portão Norte",
        "x": 29 * 32,
        "y": 21 * 32,
    },
    {
        "id": "sul",
        "nome": "Portão Sul",
        "x": 30 * 32,
        "y": 40 * 32,
    },
    {
        "id": "leste",
        "nome": "Muralha Leste",
        "x": 13 * 32,
        "y": 11 * 32,
    },
    {
        "id": "oeste",
        "nome": "Muralha Oeste",
        "x": 44 * 32,
        "y": 9 * 32,
    },
]

class GerenciadorInvasao:
    def __init__(self, socket_instancia):
        self.socketio = socket_instancia
        self.evento_ativo = False
        self.preparacao_ativa = False
        self.tempo_final_evento = 0
        self.onda_atual = 1
        self.monstros_vivos = {}
        self.registro_dano = {}  
        self.eliminados = []     
        self.jogadores_ativos = 0 
        self.ids_jogadores_evento = []
        self.frentes_ativas = []
        self.frentes_em_raid = set()
        self.frentes_concluidas = set()
        self.frentes_perdidas = set()
        self.onda_em_transicao = False
        self.contador_invocacoes = 0
        self.recompensas_raid_entregues = set()

    def _jogadores_por_frente_estimado(self):
        total_jogadores = int(getattr(self, "jogadores_ativos", 1) or 1)
        total_jogadores = max(1, min(MAX_JOGADORES_INVASAO, total_jogadores))

        total_frentes = len(getattr(self, "frentes_ativas", []) or [])
        total_frentes = max(1, total_frentes)

        return max(
            1,
            min(
                MAX_MEMBROS_POR_FRENTE,
               (total_jogadores + total_frentes - 1) // total_frentes
            )
        )


    def _calcular_balanceamento_frente(self, numero_onda):
        onda = max(1, int(numero_onda or 1))
        jogadores = self._jogadores_por_frente_estimado()

        fator_onda_hp_boss = 1.0 + ((onda - 1) * 0.35)
        fator_onda_hp_minion = 1.0 + ((onda - 1) * 0.25)

        boss_hp_mult = (
            BALANCE_INVASAO["boss_hp_base"] +
            jogadores * BALANCE_INVASAO["boss_hp_por_jogador"]
        ) * fator_onda_hp_boss

        minion_hp_mult = (
            BALANCE_INVASAO["minion_hp_base"] +
            jogadores * BALANCE_INVASAO["minion_hp_por_jogador"]
        ) * fator_onda_hp_minion

        atk_mult = (
            1.0 +
            ((onda - 1) * BALANCE_INVASAO["atk_onda"]) +
            ((jogadores - 1) * BALANCE_INVASAO["atk_jogador"])
        )

        def_mult = 1.0 + ((onda - 1) * BALANCE_INVASAO["def_onda"])

        minions_iniciais = min(
            BALANCE_INVASAO["minions_max"],
            max(BALANCE_INVASAO["minions_min"], jogadores + 2)
        )

        limite_minions = min(
            BALANCE_INVASAO["limite_minions_max"],
            max(BALANCE_INVASAO["limite_minions_min"], jogadores + 4)
        )

        invocar_por_ciclo = 1
        if jogadores >= 3:
            invocar_por_ciclo = 2
        if jogadores >= 5 and onda >= 3:
            invocar_por_ciclo = 3

        intervalo_invocacao = max(10.0, 18.0 - (onda * 1.5))
        intervalo_aoe = max(12.0, 20.0 - (onda * 1.5))
        raio_aoe = min(170, 115 + (onda * 10))

        return {
            "jogadores": jogadores,
            "boss_hp_mult": boss_hp_mult,
            "minion_hp_mult": minion_hp_mult,
            "atk_mult": atk_mult,
            "def_mult": def_mult,
            "minions_iniciais": minions_iniciais,
            "limite_minions": limite_minions,
            "invocar_por_ciclo": invocar_por_ciclo,
            "intervalo_invocacao": intervalo_invocacao,
            "intervalo_aoe": intervalo_aoe,
            "raio_aoe": raio_aoe,
        }


    def _extrair_ids_online(self, jogadores_online):
        ids = []

        if isinstance(jogadores_online, dict):
            for _, info in jogadores_online.items():
                if isinstance(info, dict):
                    char_id = info.get("char_id") or info.get("player_id") or info.get("id")
                    if char_id:
                        ids.append(str(char_id))
                elif info:
                    ids.append(str(info))

        elif isinstance(jogadores_online, list):
            for info in jogadores_online:
                if isinstance(info, dict):
                    char_id = info.get("char_id") or info.get("player_id") or info.get("id")
                    if char_id:
                        ids.append(str(char_id))
                elif info:
                    ids.append(str(info))

        ids_unicos = []
        vistos = set()

        for pid in ids:
            if pid not in vistos:
                vistos.add(pid)
                ids_unicos.append(pid)

        return ids_unicos[:MAX_JOGADORES_INVASAO]


    def _preparar_escalonamento_invasao(self, jogadores_online):
        self.ids_jogadores_evento = self._extrair_ids_online(jogadores_online)

        qtd = len(self.ids_jogadores_evento)
        self.jogadores_ativos = max(1, min(MAX_JOGADORES_INVASAO, qtd))

        qtd_frentes = max(
            1,
            min(
                MAX_GRUPOS_INVASAO,
                (self.jogadores_ativos + MAX_MEMBROS_POR_FRENTE - 1) // MAX_MEMBROS_POR_FRENTE
            )
        )

        self.frentes_ativas = FRENTES_INVASAO[:qtd_frentes]
        self.frentes_em_raid = set()
        self.frentes_concluidas = set()
        self.frentes_perdidas = set()

        return self.frentes_ativas


    def _obter_dados_mob_db(self, mob_id):
        from modules.game_data.monsters import MONSTERS_DATA

        for mob in MONSTERS_DATA.get("defesa_reino", []):
            if mob.get("id") == mob_id:
                return mob

        return {}


    def _posicao_minion_frente(self, frente, indice):
        espalhamento = [
            (-90, -50), (-45, -75), (0, -90), (45, -75), (90, -50),
            (-100, 20), (-55, 45), (0, 60), (55, 45), (100, 20),
        ]

        dx, dy = espalhamento[indice % len(espalhamento)]

        return (
            int(frente["x"] + dx + random.randint(-12, 12)),
            int(frente["y"] + dy + random.randint(-12, 12)),
        )


    def _emitir_status_frentes(self):
        frentes_payload = []

        for frente in getattr(self, "frentes_ativas", []) or []:
            fid = frente.get("id")

            status = "aberta"
            if fid in getattr(self, "frentes_em_raid", set()):
                status = "em_combate"
            elif fid in getattr(self, "frentes_concluidas", set()):
                status = "defendida"
            elif fid in getattr(self, "frentes_perdidas", set()):
                status = "perdida"

            frentes_payload.append({
                "id": fid,
                "nome": frente.get("nome", fid),
                "status": status
            })

        self.socketio.emit("statusInvasaoFrentes", {
            "ativo": bool(self.evento_ativo),
            "onda": int(getattr(self, "onda_atual", 1) or 1),
            "total_frentes": len(frentes_payload),
            "defendidas": len(getattr(self, "frentes_concluidas", set())),
            "perdidas": len(getattr(self, "frentes_perdidas", set())),
            "em_raid": len(getattr(self, "frentes_em_raid", set())),
            "frentes": frentes_payload
        })

    def agendar_invasao(self, jogadores_online):
        if self.evento_ativo or self.preparacao_ativa: return
        
        self.preparacao_ativa = True
        duracao_prep = 600 # 10 minutos
        self.tempo_final_evento = time.time() + duracao_prep
        
        # Enviamos o tempo final para o JS se sincronizar
        self.socketio.emit('alertaInvasao', {
            "mensagem": "A INVASÃO COMEÇARÁ EM 10 MINUTOS!",
            "tempo_restante": duracao_prep 
        })
        
        threading.Timer(duracao_prep, self.iniciar_invasao, args=[jogadores_online]).start()
        
    def iniciar_invasao(self, jogadores_online):
        if self.evento_ativo:
            return

        self.evento_ativo = True
        self.preparacao_ativa = False
        self.onda_atual = 1
        self.registro_dano = {}
        self.eliminados = []
        self.recompensas_raid_entregues = set()
        self.participantes_invasao = set()
        self.monstros_vivos = {}
        self.contador_invocacoes = 0

        self._preparar_escalonamento_invasao(jogadores_online)

        duracao_segundos = 1800.0
        self.tempo_final_evento = time.time() + duracao_segundos

        self.socketio.emit('alertaInvasao', {
            "mensagem": (
                f"🚨 O CÉU ESCURECEU! A INVASÃO COMEÇOU! 🚨\n"
                f"⚔️ {self.jogadores_ativos}/20 heróis defenderão {len(self.frentes_ativas)} frente(s)!"
            ),
            "tempo_restante": int(duracao_segundos),
            "onda": self.onda_atual,
            "jogadores": self.jogadores_ativos,
            "frentes": len(self.frentes_ativas)
        })

        self._emitir_status_frentes()
        self.iniciar_onda(self.onda_atual)

        if hasattr(self, 'timer_evento') and self.timer_evento:
            self.timer_evento.cancel()

        self.timer_evento = threading.Timer(duracao_segundos, self.finalizar_invasao_derrota)
        self.timer_evento.start()

    def iniciar_onda(self, numero_onda):
        import threading
        import time

        self.onda_atual = numero_onda
        self.monstros_vivos.clear()
        self.onda_em_transicao = False
        self.frentes_em_raid = set()
        self.frentes_concluidas = set()
        self.frentes_perdidas = set()

        dados_onda = WAVE_DEFINITIONS.get(numero_onda)

        if not dados_onda:
            self.finalizar_invasao_vitoria()
            return

        agora = time.time()
        tempo_final = getattr(self, 'tempo_final_evento', agora + 1800)
        restante = int(max(0, tempo_final - agora))

        self.socketio.emit('alertaInvasao', {
            "mensagem": f"🌑 O CÉU ESCURECE...\n⚔️ ONDA {numero_onda} COMEÇOU!",
            "tempo_restante": restante,
            "onda": numero_onda
        })

        self._emitir_status_frentes()

        boss_id = dados_onda['boss_id']

        threading.Timer(
            BALANCE_INVASAO["delay_spawn_onda"],
            self._gerar_monstros_da_onda,
            args=[numero_onda, dados_onda, None, boss_id]
        ).start()
        
    def _gerar_monstros_da_onda(self, numero_onda, dados_onda, multiplicador_hp, boss_id):
        if not self.evento_ativo:
            return

        import threading

        db_boss = self._obter_dados_mob_db(boss_id)
        nome_boss = db_boss.get("name", boss_id).upper()

        if "min_level" in db_boss:
            nivel_boss = random.randint(
                int(db_boss.get("min_level", 50) or 50),
                int(db_boss.get("max_level", 50) or 50)
            )
        else:
            nivel_boss = 50

        balance = self._calcular_balanceamento_frente(numero_onda)
        pool_minions = dados_onda.get("mob_pool", []) or []

        novos_monstros = {}

        for frente in getattr(self, "frentes_ativas", []) or FRENTES_INVASAO[:1]:
            frente_id = frente["id"]
            frente_nome = frente["nome"]

            boss_unico_id = f"{boss_id}_{frente_id}"

            hp_boss_base = int(db_boss.get("hp", 1150) or 1150)
            atk_boss_base = int(db_boss.get("attack", 20) or 20)
            def_boss_base = int(db_boss.get("defense", 8) or 8)

            self._gerar_monstro(
                id_monstro=boss_unico_id,
                nome=nome_boss,
                nivel=nivel_boss,
                skin=boss_id,
                is_boss=True,
                hp_max=int(hp_boss_base * balance["boss_hp_mult"]),
                x=int(frente["x"]),
                y=int(frente["y"]),
                ataque=int(atk_boss_base * balance["atk_mult"]),
                defesa=int(def_boss_base * balance["def_mult"]),
                frente_id=frente_id,
                frente_nome=frente_nome,
                monster_id=boss_id,
                special_attack=dados_onda.get("special_attack") or db_boss.get("special_attack") or {}
            )

            novos_monstros[boss_unico_id] = self.monstros_vivos[boss_unico_id]

            for i in range(int(balance["minions_iniciais"])):
                if not pool_minions:
                    break

                minion_id = random.choice(pool_minions)
                db_minion = self._obter_dados_mob_db(minion_id)

                nome_minion = db_minion.get("name", minion_id).upper()
                nivel_minion = random.randint(
                    int(db_minion.get("min_level", 1) or 1),
                    int(db_minion.get("max_level", 5) or 5)
                )

                hp_minion = int(db_minion.get("hp", 50) or 50)
                atk_minion = int(db_minion.get("attack", 4) or 4)
                def_minion = int(db_minion.get("defense", 3) or 3)

                x_minion, y_minion = self._posicao_minion_frente(frente, i)

                mob_unico_id = f"{minion_id}_{frente_id}_{i}"

                self._gerar_monstro(
                    id_monstro=mob_unico_id,
                    nome=nome_minion,
                    nivel=nivel_minion,
                    skin=minion_id,
                    is_boss=False,
                    hp_max=int(hp_minion * balance["minion_hp_mult"]),
                    x=x_minion,
                    y=y_minion,
                    ataque=int(atk_minion * balance["atk_mult"]),
                    defesa=int(def_minion * balance["def_mult"]),
                    frente_id=frente_id,
                    frente_nome=frente_nome,
                    monster_id=minion_id,
                    boss_base_id=boss_id
                )

                novos_monstros[mob_unico_id] = self.monstros_vivos[mob_unico_id]

            threading.Timer(
                balance["intervalo_invocacao"],
                self._boss_invocar_minions,
                args=[boss_unico_id, numero_onda, dados_onda]
            ).start()

            threading.Timer(
                balance["intervalo_aoe"],
                self._boss_loop_ataque,
                args=[boss_unico_id, numero_onda, dados_onda]
            ).start()

        self.socketio.emit("spawnMonstrosInvasao", novos_monstros)
        self._emitir_status_frentes()

    def _gerar_monstro(
        self,
        id_monstro,
        nome,
        nivel,
        skin,
        is_boss,
        hp_max,
        x,
        y,
        ataque=5,
        defesa=3,
        frente_id=None,
        frente_nome=None,
        monster_id=None,
        boss_base_id=None,
        special_attack=None
    ):
        self.monstros_vivos[id_monstro] = {
            "id": id_monstro,
            "monster_id": monster_id or skin or id_monstro,
            "nome": nome,
            "name": nome,
            "nivel": nivel,
            "level": nivel,
            "skin": skin,
            "is_boss": is_boss,
            "hp": int(hp_max),
            "hp_atual": int(hp_max),
            "max_hp": int(hp_max),
            "hp_max": int(hp_max),
            "x": int(x),
            "y": int(y),
            "defesa": int(defesa),
            "defense": int(defesa),
            "ataque": int(ataque),
            "attack": int(ataque),
            "frente_id": frente_id,
            "frente_nome": frente_nome,
            "boss_base_id": boss_base_id,
            "special_attack": special_attack or {},
            "regiao": "capital_eldora"
        }
    
    def _boss_invocar_minions(self, boss_id, numero_onda, dados_onda):
        if not self.evento_ativo or boss_id not in self.monstros_vivos:
            return

        import threading

        boss = self.monstros_vivos[boss_id]
        frente_id = boss.get("frente_id")
        frente_nome = boss.get("frente_nome") or frente_id or "Frente"

        if frente_id in getattr(self, "frentes_em_raid", set()):
            return
        if frente_id in getattr(self, "frentes_concluidas", set()):
            return
        if frente_id in getattr(self, "frentes_perdidas", set()):
            return

        balance = self._calcular_balanceamento_frente(numero_onda)

        minions_vivos_frente = len([
            m for m in self.monstros_vivos.values()
            if not m.get("is_boss") and m.get("frente_id") == frente_id
        ])

        limite = int(balance["limite_minions"])

        if minions_vivos_frente < limite:
            vagas = limite - minions_vivos_frente
            qtd_invocar = min(int(balance["invocar_por_ciclo"]), vagas)

            pool_minions = dados_onda.get("mob_pool", []) or []
            novos_minions = {}

            for _ in range(qtd_invocar):
                if not pool_minions:
                    break

                self.contador_invocacoes = int(getattr(self, "contador_invocacoes", 0) or 0) + 1

                minion_base = random.choice(pool_minions)
                novo_id = f"{minion_base}_{frente_id}_summon_{self.contador_invocacoes}"

                db_minion = self._obter_dados_mob_db(minion_base)
                nome_formatado = db_minion.get("name", minion_base).upper()

                nivel_minion = random.randint(
                    int(db_minion.get("min_level", 1) or 1),
                    int(db_minion.get("max_level", 5) or 5)
                )

                hp_minion = int(db_minion.get("hp", 50) or 50)
                atk_minion = int(db_minion.get("attack", 4) or 4)
                def_minion = int(db_minion.get("defense", 3) or 3)

                nx = int(boss["x"] + random.randint(-125, 125))
                ny = int(boss["y"] + random.randint(-105, 105))

                self._gerar_monstro(
                    id_monstro=novo_id,
                    nome=nome_formatado,
                    nivel=nivel_minion,
                    skin=minion_base,
                    is_boss=False,
                    hp_max=int(hp_minion * balance["minion_hp_mult"]),
                    x=nx,
                    y=ny,
                    ataque=int(atk_minion * balance["atk_mult"]),
                    defesa=int(def_minion * balance["def_mult"]),
                    frente_id=frente_id,
                    frente_nome=frente_nome,
                    monster_id=minion_base,
                    boss_base_id=boss.get("monster_id")
                )

                novos_minions[novo_id] = self.monstros_vivos[novo_id]

            if novos_minions:
                self.socketio.emit("spawnMonstrosInvasao", novos_minions)

        threading.Timer(
            balance["intervalo_invocacao"],
            self._boss_invocar_minions,
            args=[boss_id, numero_onda, dados_onda]
        ).start()

    def _boss_loop_ataque(self, boss_id, numero_onda, dados_onda):
        if not self.evento_ativo or boss_id not in self.monstros_vivos:
            return

        import threading

        boss = self.monstros_vivos[boss_id]
        frente_id = boss.get("frente_id")

        if frente_id in getattr(self, "frentes_em_raid", set()):
            return
        if frente_id in getattr(self, "frentes_concluidas", set()):
            return
        if frente_id in getattr(self, "frentes_perdidas", set()):
            return

        balance = self._calcular_balanceamento_frente(numero_onda)

        atk_especial = (
            dados_onda.get("special_attack", {}) or
            boss.get("special_attack", {}) or
            {}
        )

        nome_ataque = atk_especial.get("name", "Ataque Pesado")
        log_txt = atk_especial.get("log_text", "O Boss prepara um golpe!")

        self.socketio.emit("bossPreparandoAtaque", {
            "monstro_id": boss_id,
            "x": boss["x"],
            "y": boss["y"],
            "raio": int(balance["raio_aoe"]),
            "tempo_cast": 3000,
            "nome_ataque": nome_ataque
        })

        self.socketio.emit("alertaInvasao", {
            "mensagem": f"⚠️ {boss.get('frente_nome', 'Frente')}: {log_txt}",
            "frente_id": frente_id,
            "onda": numero_onda
        })

        threading.Timer(
            balance["intervalo_aoe"],
            self._boss_loop_ataque,
            args=[boss_id, numero_onda, dados_onda]
        ).start()

    def jogador_levou_dano_boss(self, player_id, player_nome, db_collection):
        """Calcula o dano do AoE do Boss usando status oficiais."""
        if not self.evento_ativo or player_id in self.eliminados:
            return

        jogador = db_collection.find_one({"_id": ObjectId(player_id)})
        if not jogador:
            return

        stats_player = get_combat_stats_sync(jogador)

        onda = max(1, int(getattr(self, "onda_atual", 1) or 1))
        dados_onda = WAVE_DEFINITIONS.get(onda, {})
        atk_data = dados_onda.get("special_attack", {}) or {}

        multiplicador = float(atk_data.get("damage_multiplier", 2.0) or 2.0)
        multiplicador = max(1.2, min(3.5, multiplicador))

        max_hp = int(stats_player.get("max_hp", 100) or 100)
        defesa_jogador = int(stats_player.get("defense", 0) or 0)

        dano_base = random.randint(8, 14) * (1.0 + onda * 0.35)
        dano_bruto = int(dano_base * multiplicador)
        teto_dano = max(18, int(max_hp * 0.40))
        dano_final = max(6, min(teto_dano, dano_bruto - (defesa_jogador // 2)))

        hp_atual = min(int(jogador.get("current_hp", max_hp) or max_hp), max_hp)
        novo_hp = max(0, hp_atual - dano_final)

        db_collection.update_one({"_id": ObjectId(player_id)}, {"$set": {"current_hp": novo_hp}})

        self.socketio.emit('atualizarHUDVida', {
            'player_id': player_id,
            'dano': dano_final,
            'hp': novo_hp,
            'max_hp': max_hp
        })
        if novo_hp <= 0:
            self.jogador_morreu(player_id, player_nome, db_collection)

    def processar_ataque(self, monstro_id, player_id, player_nome, db_collection, dicionario_sids_online=None):
        from bson.objectid import ObjectId
        import random

        if not self.evento_ativo or monstro_id not in self.monstros_vivos:
            return

        if player_id in self.eliminados:
            return

        monstro = self.monstros_vivos[monstro_id]
        eh_o_boss = monstro.get('is_boss') is True

        if "rei" in monstro_id or "prole" in monstro_id or "campeao" in monstro_id:
            eh_o_boss = True

        if eh_o_boss:
            self.iniciar_instancia_raid(monstro_id, player_id, db_collection, dicionario_sids_online)
            return

        jogador = db_collection.find_one({"_id": ObjectId(player_id)})
        if not jogador:
            return

        stats_player = get_combat_stats_sync(jogador)
        ataque_total = int(stats_player.get("attack", 5) or 5)
        defesa_mob = int(monstro.get("defense", monstro.get("defesa", 0)) or 0)
        variacao = random.uniform(0.90, 1.10)

        dano_final = max(1, int((ataque_total * variacao) - (defesa_mob * 0.85)))

        monstro["hp"] = max(0, int(monstro.get("hp", 0) or 0) - dano_final)
        monstro["hp_atual"] = monstro["hp"]
        self.registro_dano[player_id] = self.registro_dano.get(player_id, 0) + dano_final

        self.socketio.emit('danoMonstroInvasao', {
            'id': monstro_id,
            'dano': dano_final,
            'hp': max(0, monstro["hp"]),
            'max_hp': monstro.get("max_hp", 100)
        })

        if monstro["hp"] <= 0:
            self._monstro_morreu(monstro_id, player_id, player_nome, db_collection)

    def iniciar_instancia_raid(self, boss_id, lider_id, db_collection, dicionario_sids_online):
        import time
        from bson.objectid import ObjectId
        from modules.combat.party_engine import obter_grupo_do_jogador
        from modules.combat.combat_raid_engine import criar_sala_raid

        lider_id = str(lider_id)

        if boss_id not in self.monstros_vivos:
            return

        boss_ref = self.monstros_vivos.get(boss_id, {})
        frente_id = boss_ref.get("frente_id") or "central"
        frente_nome = boss_ref.get("frente_nome") or "Frente Central"

        if frente_id in getattr(self, "frentes_em_raid", set()):
            return

        if frente_id in getattr(self, "frentes_concluidas", set()):
            return

        self.frentes_em_raid.add(frente_id)
        self._emitir_status_frentes()
        grupo_do_jogador = obter_grupo_do_jogador(lider_id)
        membros_ids = grupo_do_jogador.get('membros', []) if grupo_do_jogador else [lider_id]
        membros_ids = [str(m) for m in membros_ids if m]
        if lider_id not in membros_ids:
            membros_ids.insert(0, lider_id)
        membros_ids = membros_ids[:5]

        jogadores_na_raid = []

        for membro_id in membros_ids:
            sid_do_jogador = None
            info_online = None

            if dicionario_sids_online:
                for sid, info in dicionario_sids_online.items():
                    if str(info.get('char_id')) == str(membro_id):
                        sid_do_jogador = sid
                        info_online = info
                        break

            if not sid_do_jogador:
                continue

            if info_online and info_online.get("em_combate"):

                continue

            try:
                dados_db = db_collection.find_one({"_id": ObjectId(membro_id)})
            except Exception:
                dados_db = None

            if not dados_db:

                continue

            stats = get_combat_stats_sync(dados_db)
            dados_db = aplicar_combat_stats_no_player(dados_db, stats)

            # ✅ SKIN DO PARTICIPANTE DA RAID:
            # A raid precisa receber a skin real de cada membro,
            # não a skin local de quem está olhando a tela.
            skin_online = ""

            if isinstance(info_online, dict):
                skin_online = (
                    info_online.get("skin")
                    or info_online.get("skinEquipada")
                    or info_online.get("skin_equipada")
                    or info_online.get("classe_skin")
                    or info_online.get("sprite")
                    or ""
                )

            skin_db = (
                dados_db.get("skin")
                or dados_db.get("skinEquipada")
                or dados_db.get("skin_equipada")
                or dados_db.get("equipped_skin")
                or dados_db.get("classe_skin")
                or dados_db.get("sprite")
                or dados_db.get("avatar")
                or ""
            )

            skin_final = str(skin_online or skin_db or "aventureiro_m").strip()

            # Aceita tanto nome simples quanto URL salva por engano.
            if "/" in skin_final:
                skin_final = skin_final.split("/")[-1]

            skin_final = skin_final.split("?")[0]
            skin_final = skin_final.replace(".png", "")
            skin_final = skin_final.lower().replace(" ", "_")
            skin_final = skin_final.replace("_masculino", "_m").replace("_feminino", "_f")

            if skin_final in ("", "player", "padrao", "undefined", "null"):
                skin_final = "aventureiro_m"

            dados_db["skin"] = skin_final
            dados_db["skin_equipada"] = skin_final

            dados_db['sid'] = sid_do_jogador
            dados_db['id'] = str(dados_db['_id'])
            jogadores_na_raid.append(dados_db)

        if not jogadores_na_raid:

            return
        self.frentes_em_raid.discard(frente_id)
        self._emitir_status_frentes()
        
        if boss_ref.get("frente_id"):
            monstros_na_raid = [m for m in self.monstros_vivos.values() if m.get("frente_id") == frente_id]
        else:
            monstros_na_raid = [boss_ref] + [m for mid, m in self.monstros_vivos.items() if mid != boss_id and not m.get('is_boss')]

        if not monstros_na_raid:
            return
        self.frentes_em_raid.discard(frente_id)
        self._emitir_status_frentes()

        raid_id = f"raid_invasao_{frente_id}_{int(time.time())}"
        ids_para_remover = [m.get("id") for m in monstros_na_raid if m.get("id")]

        raid_state = criar_sala_raid(
            raid_id,
            jogadores_na_raid,
            monstros_na_raid,
            self.socketio,
            metadata={
                "tipo_evento": "invasao_reino",
                "frente_id": frente_id,
                "frente_nome": frente_nome,
                "onda": int(getattr(self, "onda_atual", 1) or 1),
                "boss_id": boss_id,
                "membros_ids": [str(j.get("id")) for j in jogadores_na_raid]
            }
        )

        if dicionario_sids_online:
            for jogador in jogadores_na_raid:
                sid_jogador = jogador.get('sid')
                if sid_jogador in dicionario_sids_online:
                    dicionario_sids_online[sid_jogador]['em_combate'] = True

        for mid in ids_para_remover:
            self.monstros_vivos.pop(mid, None)

        self.socketio.emit("removerMonstrosInvasao", ids_para_remover)
        for mid in ids_para_remover:
            self.socketio.emit("monstroInvasaoMorreu", mid)
    
        return raid_state

    def _monstro_morreu(self, monstro_id, player_id, assassino_nome, users_collection):
        import random
        import time
        from bson.objectid import ObjectId

        monstro = self.monstros_vivos.pop(monstro_id, None)
        if not monstro:
            return

        self.socketio.emit('monstroInvasaoMorreu', monstro_id)

        if monstro.get('is_boss'):
            self.socketio.emit('alertaInvasao', {"mensagem": "👑 O BOSS FOI ESMAGADO!"})
            self.distribuir_loot_boss(monstro.get('nome', 'Boss'), users_collection)
        else:
            onda_ref = int(getattr(self, 'onda_atual', 1) or 1)
            xp_ganho = 15 * onda_ref
            ouro_ganho = 5 * onda_ref
            xp_do_passe = 10

            itens_extra = {}
            msg_item = ""
            if random.randint(1, 100) <= 15:
                itens_extra["pocao_cura_leve"] = 1
                msg_item = "<br>❤️ +1 Poção de Cura Leve"

            ok, info_level = self._aplicar_recompensa_direta_invasao(
                player_id=player_id,
                users_collection=users_collection,
                xp_ganho=xp_ganho,
                ouro_ganho=ouro_ganho,
                xp_passe=xp_do_passe,
                fragmentos=0,
                itens_extra=itens_extra
            )

            if ok:
                msg_level = ""
                if info_level and info_level.get("level_up"):
                    msg_level = f"<br>✨ Subiu para o nível {info_level.get('novo_level')}!"

                self.socketio.emit('lootRecebido', {
                    "tipo": "invasao_lacaio",
                    "player_id": str(player_id),
                    "monstro": monstro.get("nome"),
                    "ouro": int(ouro_ganho),
                    "xp": int(xp_ganho),
                    "xp_passe": int(xp_do_passe),
                    "mensagem": (
                        f"✨ Mataste {monstro.get('nome')}<br>"
                        f"💰 +{ouro_ganho} Ouro<br>"
                        f"🌟 +{xp_ganho} XP<br>"
                        f"🎫 +{xp_do_passe} XP Passe"
                        f"{msg_item}{msg_level}"
                    )
                })

        if len(self.monstros_vivos) == 0:
            proxima = int(getattr(self, 'onda_atual', 1) or 1) + 1

            try:
                from data import WAVE_DEFINITIONS
            except ImportError:
                from modules.game_data.data import WAVE_DEFINITIONS

            if proxima in WAVE_DEFINITIONS:
                agora = time.time()
                restante = int(max(0, getattr(self, 'tempo_final_evento', agora + 1800) - agora))
                self.socketio.emit('alertaInvasao', {"mensagem": f"⚠️ ONDA {proxima} COMEÇA EM 10 SEGUNDOS!", "tempo_restante": restante, "onda": proxima})
                threading.Timer(10.0, self.iniciar_onda, args=[proxima]).start()
            else:
                self.finalizar_invasao_vitoria()

    def distribuir_loot_boss(self, nome_boss, users_collection):
        import random

        for player_id, dano in list(self.registro_dano.items()):
            if player_id in self.eliminados:
                continue

            ouro_ganho = max(1, int(dano * 0.1))
            xp_ganho = max(1, int(dano * 0.5))
            xp_do_passe = 50

            itens_extra = {}
            mensagem_drops = "<br>🏅 +10 Fragmentos de Bravura"

            if random.randint(1, 100) <= 40:
                itens_extra["pocao_cura_leve"] = 1
                mensagem_drops += "<br>❤️ +1 Poção de Cura Leve"

            ok, info_level = self._aplicar_recompensa_direta_invasao(
                player_id=player_id,
                users_collection=users_collection,
                xp_ganho=xp_ganho,
                ouro_ganho=ouro_ganho,
                xp_passe=xp_do_passe,
                fragmentos=10,
                itens_extra=itens_extra
            )

            if not ok:
                continue

            msg_level = ""
            if info_level and info_level.get("level_up"):
                msg_level = f"<br>✨ Subiu para o nível {info_level.get('novo_level')}!"

            self.socketio.emit('lootRecebido', {
                "tipo": "invasao_boss_mapa",
                "player_id": str(player_id),
                "monstro": nome_boss,
                "ouro": int(ouro_ganho),
                "xp": int(xp_ganho),
                "xp_passe": int(xp_do_passe),
                "fragmentos": 10,
                "mensagem": (
                    f"✨ <b>Recompensa do {nome_boss}</b>:<br>"
                    f"💰 +{ouro_ganho} Ouro<br>"
                    f"🌟 +{xp_ganho} XP<br>"
                    f"🎫 +{xp_do_passe} XP Passe"
                    f"{mensagem_drops}{msg_level}"
                )
            })

        self.registro_dano.clear()

    def jogador_levou_dano_minion(self, player_id, player_nome, db_collection):
        if not self.evento_ativo or player_id in self.eliminados:
            return

        jogador = db_collection.find_one({"_id": ObjectId(player_id)})
        if not jogador:
            return

        stats_player = get_combat_stats_sync(jogador)

        onda = max(1, int(getattr(self, "onda_atual", 1) or 1))
        max_hp = int(stats_player.get("max_hp", 100) or 100)
        defesa_jogador = int(stats_player.get("defense", 0) or 0)

        ataque_mob_estimado = int(6 + (onda * 5))
        dano_bruto = ataque_mob_estimado + random.randint(-2, 4)
        teto_dano = max(8, int(max_hp * 0.22))
        dano_real = max(2, min(teto_dano, dano_bruto - (defesa_jogador // 3)))

        hp_atual = min(int(jogador.get("current_hp", max_hp) or max_hp), max_hp)
        novo_hp = max(0, hp_atual - dano_real)

        db_collection.update_one({"_id": ObjectId(player_id)}, {"$set": {"current_hp": novo_hp}})

        self.socketio.emit('atualizarHUDVida', {
            'player_id': player_id,
            'dano': dano_real,
            'hp': novo_hp,
            'max_hp': max_hp
        })

        if novo_hp <= 0:
            self.jogador_morreu(player_id, player_nome, db_collection)

    def jogador_morreu(self, player_id, player_nome, users_collection):
        if not self.evento_ativo:
            return

        if player_id not in self.eliminados:
            self.eliminados.append(player_id)

            jogador = users_collection.find_one({"_id": ObjectId(player_id)})
            if jogador:
                stats = get_combat_stats_sync(jogador)
                max_hp = int(stats.get("max_hp", 100) or 100)
                max_mp = int(stats.get("max_mana", 50) or 50)
            else:
                max_hp = 100
                max_mp = 50

            users_collection.update_one(
                {"_id": ObjectId(player_id)},
                {"$set": {
                    "current_hp": max_hp,
                    "current_mp": max_mp,
                    "current_location": "capital_eldora"
                }}
            )

            self.socketio.emit('forcarTeletransporte', {
                'player_id': player_id,
                'nova_regiao': 'capital_eldora',
                'is_respawn': True
            })


    def _entregar_recompensa_raid_invasao(self, raid_state, pacote_resultado):
        from modules.player.core import users_collection
        
        resultado = str(pacote_resultado.get("resultado") or "").lower().strip()

        if resultado != "vitoria":
            return
        
        raid_id = str(raid_state.get("raid_id") or "")
        if not raid_id:
            return

        if not hasattr(self, "recompensas_raid_entregues"):
            self.recompensas_raid_entregues = set()

        if raid_id in self.recompensas_raid_entregues:
            return

        self.recompensas_raid_entregues.add(raid_id)

        metadata = raid_state.get("metadata", {}) or {}
        resultado = "vitoria"
        onda = int(metadata.get("onda") or getattr(self, "onda_atual", 1) or 1)
        frente_nome = metadata.get("frente_nome") or "Frente do Reino"

        jogadores = raid_state.get("jogadores", {}) or {}
        participacao = raid_state.get("participacao", {}) or {}

        for player_id, jogador_raid in jogadores.items():
            dados_part = participacao.get(str(player_id), {}) or {}
            dano = int(dados_part.get("dano", 0) or 0)
            turnos = int(dados_part.get("turnos", 0) or 0)
            participou = dano > 0 or turnos > 0

            xp_ganho = 80 * onda
            ouro_ganho = 35 * onda
            fragmentos = 4 * onda
            xp_passe = 35

            if not participou:
                xp_ganho = max(5, xp_ganho // 4)
                ouro_ganho = max(1, ouro_ganho // 4)
                fragmentos = 0
                xp_passe = 3

            ok, info_level = self._aplicar_recompensa_direta_invasao(
                player_id=player_id,
                users_collection=users_collection,
                xp_ganho=xp_ganho,
                ouro_ganho=ouro_ganho,
                xp_passe=xp_passe,
                fragmentos=fragmentos
            )

            if not ok:
                continue

            msg_level = ""
            if info_level and info_level.get("level_up"):
                msg_level = f"<br>✨ Subiu para o nível {info_level.get('novo_level')}!"

            payload_loot = {
                "tipo": "invasao_raid",
                "player_id": str(player_id),
                "resultado": resultado,
                "frente": frente_nome,
                "onda": onda,
                "ouro": int(ouro_ganho),
                "xp": int(xp_ganho),
                "xp_passe": int(xp_passe),
                "fragmentos": int(fragmentos),
                "mensagem": (
                    f"🛡️ Defesa da Invasão concluída!<br>"
                    f"📍 {frente_nome}<br>"
                    f"💰 +{ouro_ganho} Ouro<br>"
                    f"🌟 +{xp_ganho} XP<br>"
                    f"🎫 +{xp_passe} XP Passe<br>"
                    f"🏅 +{fragmentos} Fragmentos de Bravura"
                    f"{msg_level}"
                )
            }

            sid_destino = jogador_raid.get("sid")
            if sid_destino:
                self.socketio.emit("lootRecebido", payload_loot, to=sid_destino)
            else:
                self.socketio.emit("lootRecebido", payload_loot)

    def _aplicar_recompensa_direta_invasao(
        self,
        player_id,
        users_collection,
        xp_ganho=0,
        ouro_ganho=0,
        xp_passe=0,
        fragmentos=0,
        itens_extra=None
    ):
        from bson.objectid import ObjectId

        try:
            from modules.game_data.season_pass import adicionar_xp_passe
        except Exception:
            adicionar_xp_passe = None

        try:
            from modules.player.stats import check_and_apply_level_up
        except Exception:
            check_and_apply_level_up = None

        player_id = str(player_id)

        if not hasattr(self, "participantes_invasao"):
            self.participantes_invasao = set()

        self.participantes_invasao.add(player_id)

        itens_extra = itens_extra or {}

        try:
            filtro = {"_id": ObjectId(player_id)}
        except Exception:
            return False, None

        player = users_collection.find_one(filtro)

        if not player:
            return False, None

        xp_ganho = int(xp_ganho or 0)
        ouro_ganho = int(ouro_ganho or 0)
        xp_passe = int(xp_passe or 0)
        fragmentos = int(fragmentos or 0)

        player["xp"] = int(
            player.get("xp", 0) or 0
        ) + xp_ganho

        player["gold"] = int(
            player.get("gold", 0) or 0
        ) + ouro_ganho


        # ==========================================================
        # 🎫 BLINDAGEM DO PASSE DE BATALHA
        # ==========================================================

        passe = player.get(
            "passe_batalha"
        )

        if not isinstance(
            passe,
            dict
        ):
            passe = {}

        passe.setdefault(
            "level",
            1
        )

        passe.setdefault(
            "xp",
            0
        )

        passe.setdefault(
            "is_premium",
            False
        )

        passe.setdefault(
            "resgatados_free",
            []
        )

        passe.setdefault(
            "resgatados_premium",
            []
        )

        player[
            "passe_batalha"
        ] = passe


        if (
            adicionar_xp_passe
            and xp_passe > 0
        ):
            try:

                adicionar_xp_passe(
                    player,
                    xp_passe
                )

            except Exception as e:

                print(
                    "⚠️ [INVASÃO] "
                    "Erro ao somar XP Passe: "
                    f"{e}"
            )

        inventario = player.get("inventory", {}) or {}

        if not isinstance(inventario, dict):
            inventario = {}

        if fragmentos > 0:
            item = inventario.get("fragmento_bravura")

            if isinstance(item, dict):
                item["quantity"] = int(item.get("quantity", 0) or 0) + fragmentos
                item.setdefault("base_id", "fragmento_bravura")
                item.setdefault("name", "Fragmento de Bravura")
                item.setdefault("type", "material")
            else:
                inventario["fragmento_bravura"] = {
                    "base_id": "fragmento_bravura",
                    "name": "Fragmento de Bravura",
                    "type": "material",
                    "quantity": fragmentos
                }

        for item_id, qtd in itens_extra.items():
            qtd = int(qtd or 0)

            if qtd <= 0:
                continue

            item = inventario.get(item_id)

            if isinstance(item, dict):
                item["quantity"] = int(item.get("quantity", 0) or 0) + qtd
                item.setdefault("base_id", item_id)
            else:
                inventario[item_id] = {
                    "base_id": item_id,
                    "quantity": qtd
                }

        player["inventory"] = inventario

        info_level = None

        if check_and_apply_level_up:

            try:

                (
                    levels_gained,
                    points_gained,
                    msg_level
                ) = check_and_apply_level_up(
                    player
                )

                info_level = {
                    "level_up":
                        levels_gained > 0,

                    "levels_gained":
                        levels_gained,

                    "points_gained":
                        points_gained,

                    "msg_level":
                        msg_level,

                    "novo_level":
                        player.get(
                            "level",
                            1
                        )
                }


                # ==============================================
                # ❤️💧 LEVEL UP = HP E MP COMPLETOS
                # ==============================================

                if levels_gained > 0:

                    stats_novos = (
                        get_combat_stats_sync(
                            player
                        )
                    )

                    max_hp_novo = int(
                        stats_novos.get(
                            "max_hp",
                            100
                        )
                    )

                    max_mp_novo = int(
                        stats_novos.get(
                            "max_mana",
                            50
                        )
                    )


                    # Cura total no level-up.
                    stats_novos[
                        "current_hp"
                    ] = max_hp_novo

                    stats_novos[
                        "current_mp"
                    ] = max_mp_novo

                    player = (
                        aplicar_combat_stats_no_player(
                            player,
                            stats_novos
                        )
                    )

                    player[
                        "current_hp"
                    ] = max_hp_novo

                    player[
                        "current_mp"
                    ] = max_mp_novo

            except Exception as e:

                print(
                    "⚠️ [INVASÃO] "
                    f"Erro no level up: {e}"
                )

        users_collection.update_one(
            filtro,
            {
                "$set": {

                    "xp":
                        int(
                            player.get(
                                "xp",
                                0
                            ) or 0
                        ),

                    "gold":
                        int(
                            player.get(
                                "gold",
                                0
                            ) or 0
                        ),

                    "level":
                        int(
                            player.get(
                                "level",
                                1
                            ) or 1
                        ),

                    "stat_points":
                        int(
                            player.get(
                                "stat_points",
                                0
                            ) or 0
                        ),

                    "max_hp":
                        int(
                            player.get(
                                "max_hp",
                                100
                            ) or 100
                        ),

                    "max_mana":
                        int(
                            player.get(
                                "max_mana",
                                50
                            ) or 50
                        ),
                
                    "current_hp":
                        int(
                            player.get(
                                "current_hp",
                                1
                            ) or 1
                        ),

                    "current_mp":
                        int(
                            player.get(
                                "current_mp",
                                10
                            ) or 10
                        ),
                
                    "stats":
                        player.get(
                            "stats",
                            {}
                        ),
                
                    "base_stats":
                        player.get(
                            "base_stats",
                            {}
                        ),
                
                    "inventory":
                        player.get(
                            "inventory",
                            {}
                        ),
                
                    "passe_batalha":
                        player.get(
                            "passe_batalha",
                            {}
                        ),
                }
            }
        )

        return True, info_level

    def registrar_resultado_raid(self, raid_state, pacote_resultado):
        import threading
        import time

        if not self.evento_ativo:
            print("⚠️ [INVASÃO RAID] Resultado ignorado: evento não está ativo.")
            return

        metadata = raid_state.get("metadata", {}) or {}

        if metadata.get("tipo_evento") != "invasao_reino":
            print("⚠️ [INVASÃO RAID] Resultado ignorado: metadata não é invasao_reino.")
            return

        frente_id = metadata.get("frente_id") or "central"
        frente_nome = metadata.get("frente_nome") or frente_id or "Frente desconhecida"
        resultado = str(pacote_resultado.get("resultado") or "").lower().strip()

        if resultado not in {"vitoria", "derrota"}:
            logs_txt = " ".join(
                str(l.get("texto", ""))
                for l in pacote_resultado.get("log", [])
                if isinstance(l, dict)
            ).upper()

            if "PERDIDA" in logs_txt or "ANIQUILADO" in logs_txt or "DERROTA" in logs_txt:
                resultado = "derrota"
            elif "DEFENDIDA" in logs_txt or "VITÓRIA" in logs_txt or "VITORIA" in logs_txt:
                resultado = "vitoria"
            else:
                resultado = "derrota"

        if not hasattr(self, "frentes_em_raid"):
            self.frentes_em_raid = set()

        if not hasattr(self, "frentes_concluidas"):
            self.frentes_concluidas = set()

        if not hasattr(self, "frentes_perdidas"):
            self.frentes_perdidas = set()

        if not hasattr(self, "onda_em_transicao"):
            self.onda_em_transicao = False


        # 1. Entrega recompensa e emite lootRecebido
        if resultado == "vitoria":
            self._entregar_recompensa_raid_invasao(raid_state, pacote_resultado)

        # 2. Libera a frente que estava em raid
        self.frentes_em_raid.discard(frente_id)

        # 3. Marca resultado da frente
        if resultado == "vitoria":
            self.frentes_concluidas.add(frente_id)

            self.socketio.emit("alertaInvasao", {
                "mensagem": f"🛡️ {frente_nome} foi defendida pelos heróis!",
                "frente_id": frente_id,
                "onda": int(getattr(self, "onda_atual", 1) or 1)
            })

        else:
            self.frentes_perdidas.add(frente_id)

            # ✅ DERROTA NA RAID:
            # Todos os jogadores que participaram dessa frente ficam eliminados
            # da invasão atual. Eles não podem ir para outro portão/frente.
            jogadores_raid = raid_state.get("jogadores", {}) or {}

            if not hasattr(self, "eliminados"):
                self.eliminados = []

            for player_id, jogador_raid in jogadores_raid.items():
                player_id = str(player_id)

                if player_id not in self.eliminados:
                    self.eliminados.append(player_id)

                sid_jogador = jogador_raid.get("sid")
                if sid_jogador:
                    self.socketio.emit("alertaInvasao", {
                        "mensagem": "💀 Você caiu defendendo esta frente e está fora da invasão atual.",
                        "frente_id": frente_id,
                        "onda": int(getattr(self, "onda_atual", 1) or 1)
                    }, to=sid_jogador)

            self.socketio.emit("alertaInvasao", {
                "mensagem": f"💀 {frente_nome} caiu diante da horda!",
                "frente_id": frente_id,
                "onda": int(getattr(self, "onda_atual", 1) or 1)
            })

        # 4. Remove qualquer resto visual da frente/raid no mapa
        ids_para_remover = []

        for mid, mob in list(getattr(self, "monstros_vivos", {}).items()):
            if mob.get("frente_id") == frente_id or mid in raid_state.get("monstros", {}):
                ids_para_remover.append(mid)
                self.monstros_vivos.pop(mid, None)

        if ids_para_remover:
            self.socketio.emit("removerMonstrosInvasao", ids_para_remover)
            for mid in ids_para_remover:
                self.socketio.emit("monstroInvasaoMorreu", mid)

        # 5. Atualiza painel das frentes, se existir
        if hasattr(self, "_emitir_status_frentes"):
            self._emitir_status_frentes()

        # 6. Descobre quais frentes precisam estar resolvidas
        ids_frentes_ativas = set()

        for frente in getattr(self, "frentes_ativas", []) or []:
            fid = frente.get("id")
            if fid:
                ids_frentes_ativas.add(fid)

        # Fallback: se por algum motivo frentes_ativas não foi inicializada,
        # considera só a frente atual para não travar o teste.
        if not ids_frentes_ativas:
            ids_frentes_ativas = {frente_id}

        resolvidas = (
            set(getattr(self, "frentes_concluidas", set())) |
            set(getattr(self, "frentes_perdidas", set()))
        )

        # 7. Só passa a onda quando TODAS as frentes ativas forem resolvidas
        if not ids_frentes_ativas.issubset(resolvidas):
            return

        if self.onda_em_transicao:
            return

        self.onda_em_transicao = True

        proxima = int(getattr(self, "onda_atual", 1) or 1) + 1

        if proxima in WAVE_DEFINITIONS:
            agora = time.time()
            restante = int(max(0, getattr(self, "tempo_final_evento", agora + 1800) - agora))

            self.socketio.emit("alertaInvasao", {
                "mensagem": f"⚠️ TODAS AS FRENTES FORAM RESOLVIDAS!\n🌑 ONDA {proxima} COMEÇA EM 10 SEGUNDOS!",
                "tempo_restante": restante,
                "onda": proxima
            })

            threading.Timer(10.0, self.iniciar_onda, args=[proxima]).start()

        else:
            frentes_perdidas_final = set(getattr(self, "frentes_perdidas", set()) or [])

            if frentes_perdidas_final:

                self.evento_ativo = False
                self.monstros_vivos.clear()

                self.socketio.emit("alertaInvasao", {
                    "mensagem": "💀 A INVASÃO TERMINOU EM DERROTA! Uma ou mais frentes caíram...",
                    "resultado": "derrota",
                    "onda": int(getattr(self, "onda_atual", 1) or 1)
                })

                self.socketio.emit("eventoEncerrado", {
                    "resultado": "derrota"
                })

            else:
                self.finalizar_invasao_vitoria()

    def finalizar_invasao_vitoria(self):
        from modules.player.core import users_collection
        import traceback

        self.evento_ativo = False

        if not hasattr(self, "participantes_invasao"):
            self.participantes_invasao = set()

        participantes = list(self.participantes_invasao)

        # ==========================================
        # RECOMPENSA FINAL DA INVASÃO
        # ==========================================
        ouro_final = 250
        xp_final = 400
        xp_passe_final = 80
        fragmentos_finais = 25

        for player_id in participantes:
            try:
                self._aplicar_recompensa_direta_invasao(
                    player_id=player_id,
                    users_collection=users_collection,
                    xp_ganho=xp_final,
                    ouro_ganho=ouro_final,
                    xp_passe=xp_passe_final,
                    fragmentos=fragmentos_finais
                )
            except Exception:
                traceback.print_exc()

        # ==========================================
        # DADOS DE ENCERRAMENTO
        # IMPORTANTE: aqui você deve colocar o nome
        # EXATO do arquivo do boss/mob no GitHub,
        # sem ".png"
        # ==========================================
        dados_encerramento = {
            "resultado": "vitoria",
            "titulo": "VITÓRIA!\nO Reino foi Salvo",
            "fala_npc": (
            "Glória aos Heróis!\n"
            "As recompensas estão no baú!"
            ),
            "npc_vitoria": "comemoracao_rei"
        }

        self.socketio.emit('eventoEncerrado', dados_encerramento)

        self.socketio.emit(
            'alertaInvasao',
            {
                "mensagem": "🏆 A INVASÃO FOI REPELIDA COM SUCESSO! 🏆",
                "resultado": "vitoria"
            }
        )
    
    def finalizar_invasao_derrota(self):
        """Disparado automaticamente quando os 30 minutos acabam"""
        if self.evento_ativo:
            self.evento_ativo = False
            self.monstros_vivos.clear()
            # Avisa a todos que os monstros venceram
            self.socketio.emit('alertaInvasao', {"mensagem": "💀 O TEMPO ESGOTOU! A CAPITAL CAIU... 💀"})
            self.socketio.emit('eventoEncerrado', {})