import ast
import copy
import sys
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId
from pymongo import ReturnDocument


ROOT = Path(__file__).resolve().parents[1]


def nested(document, path):
    value = document
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


class FakeUsers:
    def __init__(self, player):
        self.player = copy.deepcopy(player)

    def matches(self, query):
        for key, expected in query.items():
            if key == "$or":
                if not any(self.matches(part) for part in expected):
                    return False
                continue
            actual = nested(self.player, key)
            if isinstance(expected, dict):
                if "$gte" in expected and not actual >= expected["$gte"]:
                    return False
                if "$ne" in expected and actual == expected["$ne"]:
                    return False
                if "$exists" in expected:
                    exists = actual is not None
                    if exists != expected["$exists"]:
                        return False
            elif actual != expected:
                return False
        return True

    def find_one(self, query, projection=None):
        return copy.deepcopy(self.player) if self.matches(query) else None

    def find_one_and_update(self, query, update, return_document=None):
        if not self.matches(query):
            return None
        for key, value in update.get("$inc", {}).items():
            self.player[key] = self.player.get(key, 0) + value
        for key, value in update.get("$set", {}).items():
            self.player[key] = copy.deepcopy(value)
        for key, value in update.get("$push", {}).items():
            self.player.setdefault(key, []).append(copy.deepcopy(value))
        return copy.deepcopy(self.player)


def load_service_function():
    source = (ROOT / "modules/premium_store_manager.py").read_text(
        encoding="utf-8-sig"
    )
    tree = ast.parse(source)
    node = next(
        item for item in tree.body
        if isinstance(item, ast.FunctionDef)
        and item.name == "comprar_servico_gemas"
    )
    namespace = {
        "_object_id": lambda value: ObjectId(value) if ObjectId.is_valid(value) else None,
        "_agora": lambda: datetime.now(timezone.utc),
        "ReturnDocument": ReturnDocument,
        "CUSTO_TROCA_CLASSE": 550,
        "CUSTO_TROCA_PROFISSAO": 250,
        "SKILLS_INICIAIS_CLASSE": {"mago": "mago_bola_de_fogo"},
    }
    exec(compile(ast.Module(body=[node], type_ignores=[]), "<service>", "exec"), namespace)
    return namespace


class PremiumServicesTest(unittest.TestCase):
    def setUp(self):
        classes = types.ModuleType("modules.game_data.classes")
        classes.CLASSES_DATA = {
            "guerreiro": {"display_name": "Guerreiro", "tier": 1},
            "mago": {"display_name": "Mago", "tier": 1},
        }
        professions = types.ModuleType("modules.game_data.professions")
        professions.PROFESSIONS_DATA = {
            "ferreiro": {"display_name": "Ferreiro", "category": "crafting"},
            "minerador": {"display_name": "Minerador", "category": "gathering"},
        }
        self.old_modules = {
            key: sys.modules.get(key)
            for key in ("modules.game_data.classes", "modules.game_data.professions")
        }
        sys.modules["modules.game_data.classes"] = classes
        sys.modules["modules.game_data.professions"] = professions
        self.ns = load_service_function()
        self.player_id = ObjectId()
        self.users = FakeUsers({
            "_id": self.player_id,
            "gems": 1000,
            "class": "guerreiro",
            "equipment": {"weapon": "sword"},
            "skills": {"guerreiro_skill": {"level": 3}},
            "equipped_skills": {"slot_1": "guerreiro_skill"},
            "player_state": {"action": "idle"},
            "profession": {"key": "ferreiro", "level": 8, "xp": 40},
            "learned_professions": {
                "ferreiro": {"key": "ferreiro", "level": 8, "xp": 40},
                "minerador": {"key": "minerador", "level": 12, "xp": 90},
            },
        })
        self.ns["users_col"] = self.users

    def tearDown(self):
        for key, value in self.old_modules.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value

    def buy(self, **kwargs):
        return self.ns["comprar_servico_gemas"](
            str(self.player_id),
            kwargs.get("tipo"),
            kwargs.get("destino"),
            kwargs.get("concordou", True),
        )

    def test_class_change_is_atomic_and_archives_loadout(self):
        result = self.buy(tipo="classe", destino="mago")
        self.assertTrue(result["success"])
        self.assertEqual(self.users.player["gems"], 450)
        self.assertEqual(self.users.player["class"], "mago")
        self.assertEqual(self.users.player["equipment"], {})
        self.assertIn("guerreiro", self.users.player["class_skill_loadouts"])
        self.assertIn("mago_bola_de_fogo", self.users.player["skills"])

    def test_profession_change_preserves_progress(self):
        result = self.buy(tipo="profissao", destino="minerador")
        self.assertTrue(result["success"])
        self.assertEqual(self.users.player["gems"], 750)
        self.assertEqual(self.users.player["profession"]["level"], 12)
        self.assertEqual(self.users.player["profession"]["xp"], 90)

    def test_missing_agreement_or_balance_never_changes_player(self):
        before = copy.deepcopy(self.users.player)
        result = self.buy(tipo="classe", destino="mago", concordou=False)
        self.assertFalse(result["success"])
        self.assertEqual(self.users.player, before)

        self.users.player["gems"] = 100
        before = copy.deepcopy(self.users.player)
        result = self.buy(tipo="classe", destino="mago")
        self.assertFalse(result["success"])
        self.assertEqual(self.users.player, before)


if __name__ == "__main__":
    unittest.main()
