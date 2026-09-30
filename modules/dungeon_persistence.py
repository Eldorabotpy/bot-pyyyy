"""Checkpoints das execuções de dungeon no mesmo MongoDB dos jogadores.

Um documento por execução mantém monstros, chefe, participantes e pagamentos
juntos. Nenhum checkpoint recria mobs a partir do catálogo na restauração.
"""
from copy import deepcopy
from datetime import datetime, timezone
from functools import wraps
import threading


def durable_dungeon(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        # Caçadas do mundo não precisam de checkpoints da dungeon.
        if method.__name__ != "sair_dungeon_jogador":
            region = kwargs.get("regiao", args[0] if args else None)
            if region != "dungeon_01":
                return method(self, *args, **kwargs)
        with self._dungeon_lock:
            self._dungeon_write_depth += 1
            try:
                result = method(self, *args, **kwargs)
                if self._dungeon_write_depth == 1:
                    self.salvar_dungeons()
                return result
            finally:
                self._dungeon_write_depth -= 1
    return wrapped


class DungeonPersistence:
    def iniciar_persistencia_dungeon(self, collection=None):
        self._dungeon_lock = threading.RLock()
        self._dungeon_write_depth = 0
        if collection is None:
            from modules.player.core import users_collection
            if users_collection is None:
                raise RuntimeError("Banco indisponível para recuperar as dungeons.")
            collection = users_collection.database["dungeon_instances"]
        self._dungeon_collection = collection
        self._dungeon_saved = {}
        # Falha de leitura interrompe a inicialização: não iniciar um mundo vazio
        # e sobrescrever execuções válidas quando o banco estiver indisponível.
        for doc in collection.find({"region": "dungeon_01", "schema_version": 1}):
            self._restaurar_dungeon(doc)

    @staticmethod
    def _execution_key(instance_id):
        region, kind, owner = instance_id.split(":", 2)
        return region, f"group:{owner}" if kind == "group" else owner

    def _restaurar_dungeon(self, doc):
        instance_id = doc["_id"]
        key = self._execution_key(instance_id)
        if doc.get("started"):
            self.dungeon_execucoes.add(key)
        self.dungeon_instancia_membros[instance_id] = list(doc.get("members", []))
        self.dungeon_instancia_pagadores[instance_id] = set(doc.get("payers", []))
        for user_id in doc.get("active_members", []):
            self.dungeon_jogador_instancia[user_id] = instance_id
        if doc.get("completed"):
            self.dungeon_instancias_concluidas.add(instance_id)
        for mob in doc.get("mobs", []):
            self.mobs_vivos.setdefault("dungeon_01", {})[mob["spawn_id"]] = deepcopy(mob)
        self._dungeon_saved[instance_id] = self._snapshot_dungeon(instance_id)

    def _snapshot_dungeon(self, instance_id):
        return {
            "_id": instance_id, "schema_version": 1, "region": "dungeon_01",
            "started": self._execution_key(instance_id) in self.dungeon_execucoes,
            "members": list(self.dungeon_instancia_membros.get(instance_id, [])),
            "payers": sorted(self.dungeon_instancia_pagadores.get(instance_id, set())),
            "active_members": sorted(uid for uid, iid in self.dungeon_jogador_instancia.items()
                                     if iid == instance_id),
            "completed": instance_id in self.dungeon_instancias_concluidas,
            # Mímicos têm estado próprio nos eventos do jogador; não reaparecem
            # por um checkpoint antigo depois de o prêmio do baú ser resgatado.
            "mobs": [deepcopy(mob) for mob in list(self.mobs_vivos.get("dungeon_01", {}).values())
                     if mob.get("dungeon_instance_id") == instance_id
                     and not mob.get("event_owner_id")],
        }

    def salvar_dungeons(self):
        with self._dungeon_lock:
            ids = (set(self.dungeon_instancia_membros)
                   | set(self.dungeon_instancia_pagadores)
                   | set(self.dungeon_jogador_instancia.values()))
            for instance_id in ids:
                doc = self._snapshot_dungeon(instance_id)
                if doc == self._dungeon_saved.get(instance_id):
                    continue
                self._dungeon_collection.replace_one(
                    {"_id": instance_id},
                    {**doc, "updated_at": datetime.now(timezone.utc)}, upsert=True)
                self._dungeon_saved[instance_id] = doc
            for instance_id in set(self._dungeon_saved) - ids:
                self._dungeon_collection.delete_one({"_id": instance_id})
                del self._dungeon_saved[instance_id]

    def salvar_hp_dungeon(self, regiao, spawn_id):
        if regiao != "dungeon_01":
            return
        with self._dungeon_lock:
            mob = self.mobs_vivos.get(regiao, {}).get(spawn_id)
            if mob and not mob.get("event_owner_id") and mob.get("hp_atual", 0) > 0:
                self.salvar_dungeons()
