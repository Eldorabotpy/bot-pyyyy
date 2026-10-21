# modules/mob_engine.py
import threading
import random
import math
import time
from modules.game_data.map_spawns import MAP_SPAWNS
from modules.game_data.monsters import MONSTERS_DATA
from modules.game_data.elite_config import ELITE_CHANCE, ELITE_MULTIPLIERS
from modules.dungeon_persistence import DungeonPersistence, durable_dungeon

class GerenciadorCacada(DungeonPersistence):
    def __init__(self, socketio, dungeon_collection=None):
        self.socketio = socketio
        self.mobs_vivos = {}

        # ==========================================
        # 🏰 CONTROLE DAS INSTÂNCIAS DA DUNGEON
        # ==========================================
        #
        # Solo:
        # player:<user_id>
        #
        # Grupo:
        # group:<group_id>
        # ==========================================
        self.dungeon_execucoes = set()

        # Guarda quais jogadores pertencem à
        # execução quando ela é criada.
        self.dungeon_instancia_membros = {}

        # Guarda em qual instância cada jogador
        # que realmente entrou está participando.
        self.dungeon_jogador_instancia = {}

        # Guarda quem já consumiu uma chave
        # naquela execução específica.
        #
        # Ex:
        # dungeon_01:group:ABC -> {"id_pedro", "id_joao"}
        self.dungeon_instancia_pagadores = {}

        # ==========================================
        # 👑 DUNGEONS CONCLUÍDAS
        # ==========================================
        #
        # Guarda somente durante a execução atual.
        #
        # Ex:
        # dungeon_01:player:123
        # dungeon_01:group:ABC
        # ==========================================
        self.dungeon_instancias_concluidas = set()

        self._evento_corrupcao_ativo = None
        self._evento_corrupcao_refresh_at = 0.0
        self._evento_corrupcao_lock = threading.RLock()

        self.inicializar_mundo()
        self.iniciar_persistencia_dungeon(dungeon_collection)

    def buscar_status_base(self, monster_id):
        """Procura o monstro dentro do seu monsters.py"""
        for categoria, lista_mobs in MONSTERS_DATA.items():
            for mob in lista_mobs:
                if mob.get("id") == monster_id:
                    return mob
        return None

    @staticmethod
    def _nome_mob(mob):
        nome = str(mob.get("base_name") or mob.get("nome") or "Monstro")
        marcadores = []
        if mob.get("elite"):
            marcadores.append("Elite")
        if mob.get("corrupted"):
            marcadores.append("Corrompido")
        return f"{' '.join(marcadores)} {nome}" if marcadores else nome

    @staticmethod
    def _aplicar_modificadores_corrupcao(mob, evento_id, config):
        """Aplica bônus apenas à instância e guarda a base para removê-los depois."""
        modifiers = (config or {}).get("modifiers") or {}
        signature = tuple(
            (key, float(modifiers.get(key, 1.0)))
            for key in ("hp", "attack", "defense", "xp")
        )
        if (
            mob.get("corruption_modifiers_event_id") == evento_id
            and tuple(mob.get("corruption_modifiers_signature", ())) == signature
        ):
            return False
        base = mob.get("corruption_base_stats")
        hp_max_atual = max(1, int(mob.get("hp_max", mob.get("hp", 1)) or 1))
        hp_atual = max(0, int(mob.get("hp_atual", hp_max_atual) or 0))
        hp_ratio = min(1.0, hp_atual / hp_max_atual)
        if base:
            for key, value in base.items():
                mob[key] = value
        else:
            keys = ("hp_max", "max_hp", "hp", "hp_atual", "attack", "defense", "xp_reward")
            base = {key: mob[key] for key in keys if key in mob}
            mob["corruption_base_stats"] = base
        for key, stat in (("hp", "hp_max"), ("attack", "attack"), ("defense", "defense"), ("xp", "xp_reward")):
            if stat not in mob:
                continue
            multiplier = max(1.0, min(3.0, float(modifiers.get(key, 1.0))))
            mob[stat] = max(0 if stat == "defense" else 1, math.floor(int(mob[stat]) * multiplier))
        mob["max_hp"] = mob.get("hp_max", mob.get("max_hp", mob.get("hp", 1)))
        mob["hp"] = mob["hp_max"]
        if "hp_atual" in mob:
            mob["hp_atual"] = max(0, min(int(mob["hp_max"]), math.floor(int(mob["hp_max"]) * hp_ratio)))
        mob["corruption_modifiers_event_id"] = evento_id
        mob["corruption_modifiers_signature"] = signature
        return True

    @staticmethod
    def _mob_elegivel_para_corrupcao(mob):
        return str(mob.get("tipo", "")).lower() != "boss" and not any(mob.get(flag) for flag in (
            "boss", "is_boss", "dungeon_boss", "event_boss",
            "dungeon_mob", "event_owner_id",
        ))

    def _evento_corrupcao_atual(self, *, force=False):
        now = time.monotonic()
        with self._evento_corrupcao_lock:
            if not force and now - self._evento_corrupcao_refresh_at < 10:
                return self._evento_corrupcao_ativo
            self._evento_corrupcao_refresh_at = now
            try:
                from modules.events.dynamic_event_service import active_corruption_event
                self._evento_corrupcao_ativo = active_corruption_event()
            except Exception:
                # Falha no serviço de eventos não deve impedir o mapa de carregar
                # nem remover o estado válido recebido na última consulta.
                self._evento_corrupcao_refresh_at = 0.0
                return self._evento_corrupcao_ativo
        self.sincronizar_corrupcao_mobs(self._evento_corrupcao_ativo)
        return self._evento_corrupcao_ativo

    def sincronizar_corrupcao_mobs(self, evento=None):
        """Aplica/remove a corrupção nas instâncias globais e atualiza os mapas conectados."""
        evento_id = str((evento or {}).get("_id") or (evento or {}).get("id") or "")
        config = (evento or {}).get("corruption") or {}
        chance = max(0, min(100, int(config.get("chance", 15)))) if evento_id else 0
        alterados = []

        for regiao, mobs in list(self.mobs_vivos.items()):
            if regiao == "dungeon_01":
                continue
            for spawn_id, mob in list(mobs.items()):
                if evento_id:
                    if not self._mob_elegivel_para_corrupcao(mob):
                        continue
                    mudou = False
                    if (mob.get("corrupted") or mob.get("corruption_event_id")) and mob.get("corruption_event_id") != evento_id:
                        mob["corrupted"] = False
                        mob.pop("corruption_event_id", None)
                        mudou = True
                    if mob.get("corruption_checked_event_id") == evento_id:
                        if mob.get("corrupted"):
                            mudou = self._aplicar_modificadores_corrupcao(mob, evento_id, config) or mudou
                        if mudou:
                            mob["name"] = self._nome_mob(mob)
                            mob["nome"] = mob["name"]
                            alterados.append((regiao, spawn_id, mob))
                        continue
                    mob["corruption_checked_event_id"] = evento_id
                    if mob.get("elite") or random.random() * 100 < chance:
                        mob["corrupted"] = True
                        mob["corruption_event_id"] = evento_id
                        mudou = True
                    if mob.get("corrupted"):
                        mudou = self._aplicar_modificadores_corrupcao(mob, evento_id, config) or mudou
                    if mudou:
                        mob["name"] = self._nome_mob(mob)
                        mob["nome"] = mob["name"]
                        alterados.append((regiao, spawn_id, mob))
                elif mob.get("corrupted") or mob.get("corruption_event_id") or mob.get("corruption_checked_event_id"):
                    tinha_corrupcao_visual = bool(mob.get("corrupted") or mob.get("corruption_event_id"))
                    base = mob.pop("corruption_base_stats", {})
                    hp_max_atual = max(1, int(mob.get("hp_max", mob.get("hp", 1)) or 1))
                    hp_atual = max(0, int(mob.get("hp_atual", hp_max_atual) or 0))
                    hp_ratio = min(1.0, hp_atual / hp_max_atual)
                    for key, value in base.items():
                        mob[key] = value
                    if "hp_atual" in base:
                        mob["hp_atual"] = max(0, min(int(mob.get("hp_max", 1)), math.floor(int(mob.get("hp_max", 1)) * hp_ratio)))
                    mob.pop("corruption_modifiers_event_id", None)
                    mob.pop("corruption_modifiers_signature", None)
                    mob["corrupted"] = False
                    mob.pop("corruption_event_id", None)
                    mob.pop("corruption_checked_event_id", None)
                    if tinha_corrupcao_visual:
                        mob["name"] = self._nome_mob(mob)
                        mob["nome"] = mob["name"]
                        alterados.append((regiao, spawn_id, mob))

        for regiao, spawn_id, mob in alterados:
            self.socketio.emit("mobMapaAtualizado", {
                "regiao": regiao,
                "spawn_id": spawn_id,
                "mob_data": mob,
            })
        return len(alterados)

    def atualizar_evento_corrupcao(self, *, force=True):
        """Atualiza a seleção de corrupção após uma mudança de estado/configuração."""
        return self._evento_corrupcao_atual(force=force)

    def gerar_mob_dinamico(self, config_spawn, regiao):
        """🎲 O MESTRE DE JOGO: Gera um monstro com nível e status sorteados"""
        evento_corrupcao = self._evento_corrupcao_atual()
        base_stats = self.buscar_status_base(config_spawn["monster_id"])
        if not base_stats: return None

        mob_vivo = config_spawn.copy()
        mob_vivo["base_name"] = base_stats.get("name", "Monstro Desconhecido")
        mob_vivo["nome"] = mob_vivo["base_name"]
        mob_vivo["name"] = mob_vivo["base_name"]
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

        is_boss = any((
            mob_vivo.get("boss"), mob_vivo.get("is_boss"), mob_vivo.get("dungeon_boss"),
            mob_vivo.get("event_boss"), base_stats.get("boss"), base_stats.get("is_boss"),
            str(mob_vivo.get("tipo", base_stats.get("tipo", ""))).lower() == "boss",
        ))
        elite_definido = bool(config_spawn.get("elite") or base_stats.get("elite"))
        elite_sorteado = (
            not elite_definido
            and regiao != "dungeon_01"
            and not is_boss
            and random.random() < ELITE_CHANCE
        )
        mob_vivo["elite"] = elite_definido or elite_sorteado
        mob_vivo["is_elite"] = mob_vivo["elite"]
        mob_vivo["elite_generated"] = elite_sorteado

        if mob_vivo["elite"]:
            mob_vivo["hp_max"] = max(1, math.floor(mob_vivo["hp_max"] * ELITE_MULTIPLIERS["hp"]))
            mob_vivo["max_hp"] = mob_vivo["hp_max"]
            mob_vivo["hp_atual"] = mob_vivo["hp_max"]
            mob_vivo["hp"] = mob_vivo["hp_max"]
            mob_vivo["attack"] = max(1, math.floor(mob_vivo["attack"] * ELITE_MULTIPLIERS["attack"]))
            mob_vivo["defense"] = max(0, math.floor(mob_vivo["defense"] * ELITE_MULTIPLIERS["defense"]))
            if elite_sorteado:
                mob_vivo["initiative"] = int(base_stats.get("initiative", 0)) + ELITE_MULTIPLIERS["initiative_add"]
                mob_vivo["luck"] = int(base_stats.get("luck", 0)) + ELITE_MULTIPLIERS["luck_add"]
                mob_vivo["xp_reward"] = math.floor(mob_vivo["xp_reward"] * ELITE_MULTIPLIERS["xp"])
                mob_vivo["gold_drop"] = math.floor(mob_vivo["gold_drop"] * ELITE_MULTIPLIERS["gold"])
        mob_vivo["name"] = self._nome_mob(mob_vivo)
        mob_vivo["nome"] = mob_vivo["name"]

        if evento_corrupcao:
            self.sincronizar_corrupcao_mobs_for_instance(
                mob_vivo,
                evento_corrupcao,
            )

        return mob_vivo

    def sincronizar_corrupcao_mobs_for_instance(self, mob, evento):
        evento_id = str((evento or {}).get("_id") or (evento or {}).get("id") or "")
        if not evento_id or not self._mob_elegivel_para_corrupcao(mob):
            return mob
        if mob.get("corruption_checked_event_id") == evento_id:
            return mob
        mob["corruption_checked_event_id"] = evento_id
        chance = max(0, min(100, int((evento.get("corruption") or {}).get("chance", 15))))
        if mob.get("elite") or random.random() * 100 < chance:
            mob["corrupted"] = True
            mob["corruption_event_id"] = evento_id
            self._aplicar_modificadores_corrupcao(mob, evento_id, evento.get("corruption") or {})
        mob["name"] = self._nome_mob(mob)
        mob["nome"] = mob["name"]
        return mob

    def inicializar_mundo(self):
        """Monta o mapa sorteando os níveis da primeira geração de monstros"""
        for regiao, spawns in MAP_SPAWNS.items():
            self.mobs_vivos[regiao] = {}

            # ==========================================
            # 🏰 DUNGEON É INSTANCIADA POR JOGADOR
            # ==========================================
            #
            # Não criamos os mobs da dungeon globalmente
            # quando o servidor inicia.
            #
            # Eles serão criados quando cada jogador
            # entrar na própria execução.
            # ==========================================
            if regiao == "dungeon_01":
                continue

            for config in spawns:
                mob_dinamico = self.gerar_mob_dinamico(config, regiao)
                if mob_dinamico:
                    self.mobs_vivos[regiao][config["spawn_id"]] = mob_dinamico
                else:
                    print(f"⚠️ CAÇADA: Monstro '{config['monster_id']}' não foi encontrado no monsters.py!")

    # ==========================================
    # 🏰 CRIAR DUNGEON PRIVADA DO JOGADOR
    # ==========================================
    @durable_dungeon
    def preparar_dungeon_jogador(
        self,
        regiao,
        user_id,
        group_id=None,
        group_members=None
    ):
        regiao = str(
            regiao
            or ""
        )

        user_id = str(
            user_id
            or ""
        )

        group_id = str(
            group_id
            or ""
        ).strip()

        if (
            regiao != "dungeon_01"
            or not user_id
        ):
            return None

        # ==========================================
        # 🔒 JOGADOR JÁ ESTÁ EM UMA EXECUÇÃO
        # ==========================================
        #
        # Se entrou solo, continua solo.
        # Se entrou em grupo, continua naquela
        # mesma instância até a execução terminar.
        # ==========================================
        instancia_atual = (
            self.dungeon_jogador_instancia.get(
                user_id
            )
        )

        if instancia_atual:
            return instancia_atual

        # ==========================================
        # 👥 EXECUÇÃO EM GRUPO
        # ==========================================
        if group_id:

            instance_key = (
                f"group:{group_id}"
            )

            instance_id = (
                f"{regiao}:"
                f"{instance_key}"
            )

            membros = []

            for membro_id in (
                group_members
                or []
            ):
                membro_id = str(
                    membro_id
                    or ""
                )

                if (
                    membro_id
                    and membro_id not in membros
                ):
                    membros.append(
                        membro_id
                    )

            if user_id not in membros:
                membros.append(
                    user_id
                )

        # ==========================================
        # 👤 EXECUÇÃO SOLO
        # ==========================================
        else:

            # Mantemos user_id como chave interna
            # para continuar compatível com o
            # reset solo que já existe.
            instance_key = (
                user_id
            )

            instance_id = (
                f"{regiao}:"
                f"player:{user_id}"
            )

            membros = [
                user_id
            ]

        chave_execucao = (
            regiao,
            instance_key
        )

        # ==========================================
        # 🏰 INSTÂNCIA JÁ EXISTE
        # ==========================================
        if (
            chave_execucao
            in self.dungeon_execucoes
        ):

            membros_congelados = (
                self.dungeon_instancia_membros.get(
                    instance_id,
                    []
                )
            )

            # Jogador que entrou no grupo depois
            # que a dungeon começou não entra
            # automaticamente nesta execução.
            if (
                user_id
                not in membros_congelados
            ):
                return None

            self.dungeon_jogador_instancia[
                user_id
            ] = instance_id

            return instance_id

        # ==========================================
        # 🆕 CRIAR NOVA EXECUÇÃO
        # ==========================================
        self.mobs_vivos.setdefault(
            regiao,
            {}
        )

        # Congela quem fazia parte do grupo
        # quando a execução foi criada.
        self.dungeon_instancia_membros[
            instance_id
        ] = list(
            membros
        )

        # Somente quem realmente carregou a dungeon
        # é marcado aqui como participante ativo.
        self.dungeon_jogador_instancia[
            user_id
        ] = instance_id

        token_instancia = (
            instance_id
            .replace(
                ":",
                "_"
            )
        )

        # ==========================================
        # 👹 CRIAR OS MOBS DA INSTÂNCIA
        # ==========================================
        for config in MAP_SPAWNS.get(
            regiao,
            []
        ):
            config_privada = (
                config.copy()
            )

            spawn_base = str(
                config_privada[
                    "spawn_id"
                ]
            )

            spawn_privado = (
                f"{spawn_base}__"
                f"{token_instancia}"
            )

            config_privada[
                "spawn_id"
            ] = spawn_privado

            # Mantido temporariamente para continuar
            # compatível com o filtro atual.
            config_privada[
                "dungeon_owner_id"
            ] = user_id

            config_privada[
                "dungeon_instance_id"
            ] = instance_id

            config_privada[
                "dungeon_members"
            ] = list(
                membros
            )

            config_privada[
                "dungeon_mob"
            ] = True

            mob_dinamico = (
                self.gerar_mob_dinamico(
                    config_privada,
                    regiao
                )
            )

            if not mob_dinamico:
                print(
                    "⚠️ DUNGEON: "
                    f"Monstro '{config_privada['monster_id']}' "
                    "não encontrado."
                )
                continue

            mob_dinamico[
                "dungeon_owner_id"
            ] = user_id

            mob_dinamico[
                "dungeon_instance_id"
            ] = instance_id

            mob_dinamico[
                "dungeon_members"
            ] = list(
                membros
            )

            mob_dinamico[
                "dungeon_mob"
            ] = True

            self.mobs_vivos[
                regiao
            ][
                spawn_privado
            ] = mob_dinamico

        self.dungeon_execucoes.add(
            chave_execucao
        )

        print(
            "🏰 [DUNGEON] Execução criada: "
            f"{instance_id} | "
            f"membros={membros}"
        )

        return instance_id


    # ==========================================
    # ♻️ RESETAR EXECUÇÃO DE DUNGEON
    # ==========================================
    @durable_dungeon
    def resetar_dungeon_jogador(
        self,
        regiao,
        user_id,
        group_id=None
    ):
        regiao = str(
            regiao
            or ""
        )

        user_id = str(
            user_id
            or ""
        )

        group_id = str(
            group_id
            or ""
        ).strip()

        if (
            regiao != "dungeon_01"
            or not user_id
        ):
            return

        # ==========================================
        # 🏰 DESCOBRIR QUAL INSTÂNCIA RESETAR
        # ==========================================
        instancia_atual = (
            self.dungeon_jogador_instancia.get(
                user_id
            )
        )

        if group_id:

            instance_key = (
                f"group:{group_id}"
            )

            instance_id = (
                f"{regiao}:"
                f"{instance_key}"
            )

        elif instancia_atual:

            instance_id = str(
                instancia_atual
            )

            prefixo_grupo = (
                f"{regiao}:group:"
            )

            if instance_id.startswith(
                prefixo_grupo
            ):

                group_id_real = (
                    instance_id[
                        len(prefixo_grupo):
                    ]
                )

                instance_key = (
                    f"group:{group_id_real}"
                )

            else:

                instance_key = (
                    user_id
                )

        else:

            instance_key = (
                user_id
            )

            instance_id = (
                f"{regiao}:player:{user_id}"
            )

        mobs_regiao = (
            self.mobs_vivos.setdefault(
                regiao,
                {}
            )
        )

        membros_instancia = list(
            self.dungeon_instancia_membros.get(
                instance_id,
                []
            )
        )

        remover = []

        # ==========================================
        # 👹 REMOVER MOBS DA INSTÂNCIA
        # ==========================================
        for (
            spawn_id,
            mob
        ) in list(
            mobs_regiao.items()
        ):

            mob_instance_id = str(
                mob.get(
                    "dungeon_instance_id"
                )
                or ""
            )

            if (
                mob_instance_id
                == instance_id
            ):
                remover.append(
                    spawn_id
                )
                continue

            # ======================================
            # 👹 LIMPAR MÍMICOS ANTIGOS
            # ======================================
            event_owner_id = str(
                mob.get(
                    "event_owner_id"
                )
                or ""
            )

            if not event_owner_id:
                continue

            if group_id:

                if (
                    event_owner_id
                    in membros_instancia
                ):
                    remover.append(
                        spawn_id
                    )

            elif (
                event_owner_id
                == user_id
            ):
                remover.append(
                    spawn_id
                )

        for spawn_id in remover:

            mobs_regiao.pop(
                spawn_id,
                None
            )

        # ==========================================
        # 🔓 REMOVER JOGADORES DA INSTÂNCIA
        # ==========================================
        for (
            jogador_id,
            jogador_instance_id
        ) in list(
            self.dungeon_jogador_instancia.items()
        ):

            if (
                jogador_instance_id
                == instance_id
            ):
                self.dungeon_jogador_instancia.pop(
                    jogador_id,
                    None
                )

        self.dungeon_instancia_membros.pop(
            instance_id,
            None
        )

        # Uma execução encerrada não mantém
        # direito de entrada gratuita.
        self.dungeon_instancia_pagadores.pop(
            instance_id,
            None
        )

        # A conclusão vale somente para esta run.
        # Ao terminar/resetar a execução, uma futura
        # entrada começa uma dungeon nova.
        self.dungeon_instancias_concluidas.discard(
            instance_id
        )

        self.dungeon_execucoes.discard(
            (
                regiao,
                instance_key
            )
        )

        print(
            "♻️ [DUNGEON] Execução resetada: "
            f"{instance_id}"
        )

    # ==========================================
    # 🔐 PODE PARTICIPAR DESTA EXECUÇÃO?
    # ==========================================
    def pode_participar_dungeon(
        self,
        regiao,
        user_id,
        group_id=None
    ):
        regiao = str(
            regiao
            or ""
        )

        user_id = str(
            user_id
            or ""
        )

        group_id = str(
            group_id
            or ""
        ).strip()

        if (
            regiao != "dungeon_01"
            or not user_id
        ):
            return False

        # Solo sempre pode iniciar uma nova execução.
        if not group_id:
            return True

        instance_key = (
            f"group:{group_id}"
        )

        instance_id = (
            f"{regiao}:"
            f"{instance_key}"
        )

        chave_execucao = (
            regiao,
            instance_key
        )

        # Ainda não existe execução dessa party.
        # O grupo atual será congelado na criação.
        if (
            chave_execucao
            not in self.dungeon_execucoes
        ):
            return True

        membros_congelados = (
            self.dungeon_instancia_membros.get(
                instance_id,
                []
            )
        )

        # Quem entrou na party depois que a dungeon
        # começou não pode entrar nesta run.
        return (
            user_id
            in membros_congelados
        )


    # ==========================================
    # 🗝️ JÁ PAGOU ESTA EXECUÇÃO?
    # ==========================================
    def jogador_ja_pagou_dungeon(
        self,
        regiao,
        user_id,
        group_id=None
    ):
        regiao = str(
            regiao
            or ""
        )

        user_id = str(
            user_id
            or ""
        )

        group_id = str(
            group_id
            or ""
        ).strip()

        if (
            regiao != "dungeon_01"
            or not user_id
        ):
            return False

        if group_id:

            instance_key = (
                f"group:{group_id}"
            )

            instance_id = (
                f"{regiao}:"
                f"{instance_key}"
            )

        else:

            instance_key = (
                user_id
            )

            instance_id = (
                f"{regiao}:"
                f"player:{user_id}"
            )

        # ==========================================
        # 🗝️ PAGAMENTO PODE VIR ANTES DA INSTÂNCIA
        # ==========================================
        #
        # A chave é consumida na rota HTTP antes
        # de o mapa terminar de carregar.
        #
        # Portanto o jogador pode estar registrado
        # como pagador alguns instantes antes de
        # dungeon_execucoes ser criada.
        # ==========================================

        pagadores = (
            self.dungeon_instancia_pagadores.get(
                instance_id,
                set()
            )
        )

        return (
            user_id
            in pagadores
        )


    # ==========================================
    # 🗝️ REGISTRAR CHAVE PAGA
    # ==========================================
    @durable_dungeon
    def registrar_pagamento_dungeon(
        self,
        regiao,
        user_id,
        group_id=None
    ):
        regiao = str(
            regiao
            or ""
        )

        user_id = str(
            user_id
            or ""
        )

        group_id = str(
            group_id
            or ""
        ).strip()

        if (
            regiao != "dungeon_01"
            or not user_id
        ):
            return None

        if group_id:

            instance_id = (
                f"{regiao}:"
                f"group:{group_id}"
            )

        else:

            instance_id = (
                f"{regiao}:"
                f"player:{user_id}"
            )

        pagadores = (
            self.dungeon_instancia_pagadores.setdefault(
                instance_id,
                set()
            )
        )

        pagadores.add(
            user_id
        )

        print(
            "🗝️ [DUNGEON] Chave registrada: "
            f"{user_id} -> {instance_id}"
        )

        return instance_id
    
    # ==========================================
    # 🚪 JOGADOR SAIU DA DUNGEON
    # ==========================================
    @durable_dungeon
    def sair_dungeon_jogador(
        self,
        user_id
    ):
        user_id = str(
            user_id
            or ""
        )

        if not user_id:
            return None

        instance_id = (
            self.dungeon_jogador_instancia.pop(
                user_id,
                None
            )
        )

        if not instance_id:
            return None

        print(
            "🚪 [DUNGEON] Jogador saiu da instância: "
            f"{user_id} -> {instance_id}"
        )

        # ==========================================
        # 👥 AINDA TEM ALGUÉM NESSA EXECUÇÃO?
        # ==========================================
        ainda_tem_jogador = any(
            atual == instance_id
            for atual
            in self.dungeon_jogador_instancia.values()
        )

        if ainda_tem_jogador:
            return instance_id

        # ==========================================
        # 🏁 ÚLTIMO JOGADOR SAIU
        # ==========================================
        #
        # A execução acabou.
        # Na próxima entrada será uma nova run.
        # ==========================================

        prefixo_grupo = (
            "dungeon_01:group:"
        )

        if instance_id.startswith(
            prefixo_grupo
        ):

            group_id = (
                instance_id[
                    len(prefixo_grupo):
                ]
            )

            self.resetar_dungeon_jogador(
                regiao="dungeon_01",
                user_id=user_id,
                group_id=group_id
            )

        else:

            self.resetar_dungeon_jogador(
                regiao="dungeon_01",
                user_id=user_id
            )

        return instance_id


    # ==========================================
    # 👥 GRUPO AINDA POSSUI JOGADOR NA RUN?
    # ==========================================
    def dungeon_grupo_tem_participante_ativo(
        self,
        regiao,
        group_id
    ):
        regiao = str(
            regiao
            or ""
        )

        group_id = str(
            group_id
            or ""
        ).strip()

        if (
            regiao != "dungeon_01"
            or not group_id
        ):
            return False

        instance_id = (
            f"{regiao}:group:{group_id}"
        )

        return any(
            atual == instance_id
            for atual
            in self.dungeon_jogador_instancia.values()
        )

    # ==========================================
    # 🏆 INSTÂNCIA DA DUNGEON FOI CONCLUÍDA?
    # ==========================================
    def dungeon_instancia_concluida(
        self,
        instance_id
    ):
        instance_id = str(
            instance_id
            or ""
        )

        if not instance_id:
            return False

        return (
            instance_id
            in self.dungeon_instancias_concluidas
        )
    
    # ==========================================
    # 👁️ MOBS VISÍVEIS PARA O JOGADOR
    # ==========================================
    def obter_mobs_regiao(
        self,
        regiao,
        user_id=None,
        group_id=None,
        group_members=None
    ):
        self._evento_corrupcao_atual()
        regiao = str(
            regiao
            or ""
        )

        # ==========================================
        # 🌍 MAPAS NORMAIS
        # ==========================================
        if regiao != "dungeon_01":
            user_id = str(user_id or "")
            mobs = self.mobs_vivos.get(
                regiao,
                {}
            )
            return {
                spawn_id: mob
                for spawn_id, mob in mobs.items()
                if not mob.get("event_owner_id")
                or str(mob.get("event_owner_id")) == user_id
            }

        user_id = str(
            user_id
            or ""
        )

        if not user_id:
            return {}

        # ==========================================
        # 🗝️ CONFIRMAR ENTRADA AUTORIZADA
        # ==========================================
        #
        # Um jogador que já está mapeado para uma
        # instância pode apenas estar recarregando
        # o mapa.
        #
        # Quem ainda não está mapeado precisa ter
        # passado pela rota de entrada e consumido
        # sua chave nesta execução.
        # ==========================================
        instancia_atual = (
            self.dungeon_jogador_instancia.get(
                user_id
            )
        )

        if not instancia_atual:

            pagamento_confirmado = (
                self.jogador_ja_pagou_dungeon(
                    regiao=regiao,
                    user_id=user_id,
                    group_id=group_id
                )
            )

            if not pagamento_confirmado:

                print(
                    "🔒 [DUNGEON] Entrada sem pagamento bloqueada: "
                    f"user={user_id} | "
                    f"regiao={regiao} | "
                    f"group={group_id}"
                )

                return {}

        # ==========================================
        # 🏰 DESCOBRIR / CRIAR INSTÂNCIA
        # ==========================================
        instance_id = (
            self.preparar_dungeon_jogador(
                regiao=regiao,
                user_id=user_id,
                group_id=group_id,
                group_members=group_members
            )
        )

        if not instance_id:
            return {}

        resultado = {}

        for (
            spawn_id,
            mob
        ) in self.mobs_vivos.get(
            regiao,
            {}
        ).items():

            # ======================================
            # 👹 MÍMICO / EVENTO INDIVIDUAL
            # ======================================
            #
            # Mesmo estando em grupo, somente
            # o dono daquele evento enxerga
            # e enfrenta o Mímico.
            # ======================================
            event_owner_id = str(
                mob.get(
                    "event_owner_id"
                )
                or ""
            )

            if event_owner_id:

                if event_owner_id == user_id:
                    resultado[
                        spawn_id
                    ] = mob

                continue

            # ======================================
            # ⚔️ MOBS NORMAIS / BOSS
            # ======================================
            #
            # Todos os jogadores da mesma instância
            # enxergam os mesmos mobs.
            # ======================================
            mob_instance_id = str(
                mob.get(
                    "dungeon_instance_id"
                )
                or ""
            )

            if (
                mob_instance_id
                == instance_id
            ):
                resultado[
                    spawn_id
                ] = mob

        return resultado

    @durable_dungeon
    def processar_morte(self, regiao, spawn_id):
        if regiao in self.mobs_vivos and spawn_id in self.mobs_vivos[regiao]:
            mob = self.mobs_vivos[regiao][spawn_id]
            tempo_respawn = mob.get("respawn_segundos", 15)

            # 🌌 FENDA DIMENSIONAL — contador de abates por mapa.
            #
            # Mobs de dungeon NÃO alimentam a Fenda Dimensional.
            # Eles fazem parte de uma execução fechada da masmorra.
            if (
                regiao != "dungeon_01"
                and not mob.get("quest_event_id")
                and not mob.get("_abate_dimensional_contado")
            ):
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
        
            self.socketio.emit(
                'mobMapaMorreu',
                {
                    "spawn_id": spawn_id
                }
            )

            del self.mobs_vivos[regiao][spawn_id]

            # Encontros de missão são pessoais e não reaparecem após a vitória.
            if mob.get("quest_event_id"):
                return {
                    "removido": True,
                    "respawn": False,
                    "regiao": regiao,
                    "spawn_id": spawn_id,
                    "monster_id": mob.get("monster_id"),
                }

            # ==========================================
            # 🏰 DUNGEON 01 — SEM RESPAWN NORMAL
            # ==========================================
            if regiao == "dungeon_01":

                monster_id_morto = str(
                    mob.get(
                        "monster_id"
                    )
                    or ""
                )

                instance_id = str(
                    mob.get(
                        "dungeon_instance_id"
                    )
                    or ""
                )

                # ======================================
                # 👹 MÍMICO / EVENTO INDIVIDUAL
                # ======================================
                #
                # Mímicos não contam para liberar
                # o Rei Caído.
                # ======================================
                if mob.get(
                    "event_owner_id"
                ):

                    return {
                        "removido": True,
                        "respawn": False,
                        "regiao": regiao,
                        "spawn_id": spawn_id,
                        "monster_id": monster_id_morto,
                        "boss_spawnado": False,
                    }

                # ======================================
                # 👑 O PRÓPRIO REI CAÍDO MORREU
                # ======================================
                #
                # Nunca criar outro boss após a morte
                # do próprio Rei Caído.
                # ======================================
                if (
                    monster_id_morto
                    == "rei_caido_dungeon_01"
                    or mob.get(
                        "dungeon_boss"
                    )
                ):

                    # ==================================
                    # 🏆 DUNGEON CONCLUÍDA
                    # ==================================
                    if instance_id:

                        self.dungeon_instancias_concluidas.add(
                            instance_id
                        )

                    # ==================================
                    # 👥 QUEM AINDA ESTÁ NESTA RUN?
                    # ==================================
                    participantes_ativos = {
                        str(jogador_id)
                        for (
                            jogador_id,
                            jogador_instance_id
                        )
                        in self.dungeon_jogador_instancia.items()
                        if str(
                            jogador_instance_id
                        ) == instance_id
                    }

                    # ==================================
                    # 🏆 PACOTE DE CONCLUSÃO
                    # ==================================
                    pacote_conclusao = {
                        "dungeon_id":
                            "dungeon_01",

                        "dungeon_instance_id":
                            instance_id,

                        "nome":
                            "Catacumbas do Rei Caído",

                        "boss":
                            "Rei Caído",

                        "mensagem":
                            (
                                "O Rei Caído foi derrotado! "
                                "As Catacumbas foram concluídas."
                            ),

                        "membros":
                            sorted(
                                participantes_ativos
                            ),
                    }

                    # ==================================
                    # 📡 AVISAR SOMENTE PARTICIPANTES
                    # ==================================
                    app_ref = getattr(
                        self,
                        "app",
                        None
                    )

                    jogadores_online = {}

                    if app_ref:

                        jogadores_online = (
                            app_ref.config.get(
                                "JOGADORES_ONLINE",
                                {}
                            )
                            or {}
                        )

                    for (
                        sid,
                        info
                    ) in list(
                        jogadores_online.items()
                    ):

                        info = (
                            info
                            or {}
                        )

                        char_id = str(
                            info.get(
                                "char_id"
                            )
                            or ""
                        )

                        regiao_online = str(
                            info.get(
                                "regiao"
                            )
                            or ""
                        )

                        if (
                            char_id
                            in participantes_ativos
                            and regiao_online
                            == "dungeon_01"
                        ):

                            self.socketio.emit(
                                "dungeonConcluida",
                                pacote_conclusao,
                                to=sid
                            )

                    print(
                        "🏆 [DUNGEON] Catacumbas concluídas: "
                        f"{instance_id} | "
                        f"participantes={sorted(participantes_ativos)}"
                    )

                    return {
                        "removido": True,
                        "respawn": False,
                        "regiao": regiao,
                        "spawn_id": spawn_id,
                        "monster_id": monster_id_morto,
                        "boss_derrotado": True,
                        "dungeon_concluida": True,
                        "dungeon_instance_id": instance_id,
                        "membros": sorted(participantes_ativos),
                    }

                # ======================================
                # 🔎 CONTAR MOBS NORMAIS RESTANTES
                # ======================================
                mobs_restantes = 0

                if instance_id:

                    for mob_restante in (
                        self.mobs_vivos.get(
                            regiao,
                            {}
                        ).values()
                    ):

                        # Precisa pertencer exatamente
                        # à mesma execução.
                        if str(
                            mob_restante.get(
                                "dungeon_instance_id"
                            )
                            or ""
                        ) != instance_id:
                            continue

                        # Mímicos e outros encontros
                        # individuais não contam.
                        if mob_restante.get(
                            "event_owner_id"
                        ):
                            continue

                        # Boss não entra na contagem
                        # dos mobs necessários.
                        if (
                            mob_restante.get(
                                "dungeon_boss"
                            )
                            or str(
                                mob_restante.get(
                                    "monster_id"
                                )
                                or ""
                            )
                            == "rei_caido_dungeon_01"
                        ):
                            continue

                        if mob_restante.get(
                            "dungeon_mob"
                        ):
                            mobs_restantes += 1

                print(
                    "🏰 [DUNGEON] Mobs restantes: "
                    f"{mobs_restantes} | "
                    f"instancia={instance_id}"
                )

                # ======================================
                # 👑 AINDA EXISTEM MOBS NORMAIS
                # ======================================
                if (
                    not instance_id
                    or mobs_restantes > 0
                ):

                    return {
                        "removido": True,
                        "respawn": False,
                        "regiao": regiao,
                        "spawn_id": spawn_id,
                        "monster_id": monster_id_morto,
                        "mobs_restantes": mobs_restantes,
                        "boss_spawnado": False,
                    }

                # ======================================
                # 👑 VERIFICAR SE O BOSS JÁ EXISTE
                # ======================================
                boss_ja_existe = False

                for mob_existente in (
                    self.mobs_vivos.get(
                        regiao,
                        {}
                    ).values()
                ):

                    if (
                        str(
                            mob_existente.get(
                                "dungeon_instance_id"
                            )
                            or ""
                        )
                        == instance_id
                        and (
                            mob_existente.get(
                                "dungeon_boss"
                            )
                            or str(
                                mob_existente.get(
                                    "monster_id"
                                )
                                or ""
                            )
                            == "rei_caido_dungeon_01"
                        )
                    ):
                        boss_ja_existe = True
                        break

                if boss_ja_existe:

                    return {
                        "removido": True,
                        "respawn": False,
                        "regiao": regiao,
                        "spawn_id": spawn_id,
                        "monster_id": monster_id_morto,
                        "mobs_restantes": 0,
                        "boss_spawnado": False,
                    }

                # ======================================
                # 👑 CRIAR O REI CAÍDO
                # ======================================

                token_instancia = (
                    instance_id.replace(
                        ":",
                        "_"
                    )
                )

                boss_spawn_id = (
                    "dungeon01_rei_caido__"
                    f"{token_instancia}"
                )

                boss_config = {
                    "spawn_id":
                        boss_spawn_id,

                    "monster_id":
                        "rei_caido_dungeon_01",

                    # Tiled:
                    # X = 28
                    # Y = 25
                    "x":
                        28 * 32,

                    "y":
                        25 * 32,

                    "respawn_segundos":
                        0,

                    "dungeon_owner_id":
                        mob.get(
                            "dungeon_owner_id"
                        ),

                    "dungeon_instance_id":
                        instance_id,

                    "dungeon_members":
                        list(
                            mob.get(
                                "dungeon_members"
                            )
                            or []
                        ),

                    "dungeon_mob":
                        True,

                    "dungeon_boss":
                        True,

                    "boss":
                        True,
                }

                rei_caido = (
                    self.gerar_mob_dinamico(
                        boss_config,
                        regiao
                    )
                )

                if not rei_caido:

                    print(
                        "❌ [DUNGEON] Não foi possível "
                        "criar rei_caido_dungeon_01."
                    )

                    return {
                        "removido": True,
                        "respawn": False,
                        "regiao": regiao,
                        "spawn_id": spawn_id,
                        "monster_id": monster_id_morto,
                        "mobs_restantes": 0,
                        "boss_spawnado": False,
                    }

                # Reforça os dados da instância.
                rei_caido[
                    "dungeon_instance_id"
                ] = instance_id

                rei_caido[
                    "dungeon_members"
                ] = list(
                    mob.get(
                        "dungeon_members"
                    )
                    or []
                )

                rei_caido[
                    "dungeon_mob"
                ] = True

                rei_caido[
                    "dungeon_boss"
                ] = True

                rei_caido[
                    "boss"
                ] = True

                self.mobs_vivos[
                    regiao
                ][
                    boss_spawn_id
                ] = rei_caido

                print(
                    "👑 [DUNGEON] REI CAÍDO SURGIU! "
                    f"instancia={instance_id} | "
                    "tile=(28,25)"
                )

                # ======================================
                # 📡 MOSTRAR O BOSS NO MAPA
                # ======================================
                self.socketio.emit(
                    "mobMapaNasceu",
                    {
                        "regiao":
                            regiao,

                        "spawn_id":
                            boss_spawn_id,

                        "mob_data":
                            rei_caido,

                        "dungeon_instance_id":
                            instance_id,
                    }
                )

                return {
                    "removido": True,
                    "respawn": False,
                    "regiao": regiao,
                    "spawn_id": spawn_id,
                    "monster_id": monster_id_morto,
                    "mobs_restantes": 0,
                    "boss_spawnado": True,
                    "boss_spawn_id": boss_spawn_id,
                }
            
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
