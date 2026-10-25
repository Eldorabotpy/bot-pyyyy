import copy
import threading
import unittest
from unittest.mock import AsyncMock, patch

from bson import ObjectId
from flask import Flask

from modules.class_evolution_service import (
    apply_skill_upgrade_to_player_data,
    get_skill_upgrade_quote,
)
from modules.skill_progression import get_skill_level_multiplier
from rotas.character import character_bp


SKILL_ID = "guerreiro_corte_perfurante"


def player_fixture(level=2, rarity="comum"):
    skill = {"unlocked": True, "level": level, "rarity": rarity}
    inventory = {
        f"tomo_{SKILL_ID}": {"quantity": 2},
        "pedra_de_aprimoramento": {"quantity": 5},
        "cristal_mana_bruto": {"quantity": 5},
        "essencia_purificadora": {"quantity": 5},
    }
    return {
        "_id": ObjectId(),
        "class": "guerreiro",
        "gold": 10000,
        "inventory": inventory,
        "skills": {SKILL_ID: copy.deepcopy(skill)},
        "skills_desbloqueadas": {SKILL_ID: copy.deepcopy(skill)},
        "database_skills": {SKILL_ID: copy.deepcopy(skill)},
    }


class _UpdateResult:
    def __init__(self, modified_count):
        self.modified_count = modified_count


class _MemoryUsers:
    def __init__(self, player):
        self.player = copy.deepcopy(player)
        self.reject_update = False
        self.lock = threading.Lock()

    def update_one(self, query, update):
        with self.lock:
            if self.reject_update or query.get("_id") != self.player["_id"]:
                return _UpdateResult(0)
            for field, expected in query.items():
                if field == "_id":
                    continue
                present = field in self.player
                if isinstance(expected, dict) and "$exists" in expected:
                    if present != expected["$exists"]:
                        return _UpdateResult(0)
                elif not present or self.player[field] != expected:
                    return _UpdateResult(0)
            before = copy.deepcopy(self.player)
            self.player.update(copy.deepcopy(update.get("$set", {})))
            return _UpdateResult(int(self.player != before))


class SkillUpgradeServiceTests(unittest.TestCase):
    def test_quote_lists_exact_next_rank_costs_and_bonus(self):
        player = player_fixture(level=2)

        quote = get_skill_upgrade_quote(player, SKILL_ID)

        self.assertTrue(quote["eligible"])
        self.assertTrue(quote["can_upgrade"])
        self.assertEqual(quote["gold"]["required"], 300)
        self.assertEqual(quote["next_level"], 3)
        self.assertEqual(quote["current_power_pct"], 4)
        self.assertEqual(quote["next_power_pct"], 8)
        self.assertEqual(
            {item["id"]: item["required"] for item in quote["items"]},
            {
                f"tomo_{SKILL_ID}": 1,
                "pedra_de_aprimoramento": 1,
                "cristal_mana_bruto": 1,
                "essencia_purificadora": 1,
            },
        )

    def test_apply_consumes_cost_and_updates_all_skill_snapshots(self):
        player = player_fixture(level=2)

        success, message, updated = apply_skill_upgrade_to_player_data(player, SKILL_ID)

        self.assertTrue(success, message)
        self.assertEqual(updated["level"], 3)
        self.assertEqual(player["gold"], 9700)
        for field in ("skills", "skills_desbloqueadas", "database_skills"):
            self.assertEqual(player[field][SKILL_ID]["level"], 3)
        self.assertEqual(player["inventory"][f"tomo_{SKILL_ID}"]["quantity"], 1)
        self.assertEqual(get_skill_level_multiplier(updated["level"]), 1.08)

    def test_missing_materials_and_gold_do_not_mutate_player(self):
        player = player_fixture(level=2)
        player["gold"] = 0
        player["inventory"].pop("pedra_de_aprimoramento")
        original = copy.deepcopy(player)

        success, _, _ = apply_skill_upgrade_to_player_data(player, SKILL_ID)

        self.assertFalse(success)
        self.assertEqual(player, original)

    def test_max_level_is_capped_and_evolution_skills_use_their_own_flow(self):
        maxed = player_fixture(level=10)
        maxed["inventory"] = {}
        max_quote = get_skill_upgrade_quote(maxed, SKILL_ID)
        evolution = player_fixture()
        evolution["skills"]["evo_knight_aegis"] = {"unlocked": True, "level": 1}

        self.assertTrue(max_quote["eligible"])
        self.assertFalse(max_quote["can_upgrade"])
        self.assertIsNone(max_quote["next_level"])
        evolution_quote = get_skill_upgrade_quote(evolution, "evo_knight_aegis")
        self.assertFalse(evolution_quote["eligible"])
        self.assertIn("evolução de classe", evolution_quote["reason"])

    def test_skill_for_another_class_is_not_upgradeable(self):
        player = player_fixture()
        player["class"] = "mago"

        quote = get_skill_upgrade_quote(player, SKILL_ID)

        self.assertFalse(quote["eligible"])
        self.assertFalse(quote["can_upgrade"])
        self.assertIn("classe", quote["reason"])


class SkillUpgradeApiTests(unittest.TestCase):
    def setUp(self):
        self.player = player_fixture(level=1)
        self.users = _MemoryUsers(self.player)
        self.app = Flask(__name__)
        self.app.register_blueprint(character_bp)
        self.client = self.app.test_client()
        self.identity_patch = patch("modules.portal_auth.require_player_identity", side_effect=self._identity)
        self.csrf_patch = patch("modules.portal_auth.require_csrf", return_value=None)
        self.users_patch = patch("rotas.character.users_collection", self.users)
        self.cache_patch = patch("modules.player.core.clear_player_cache", new=AsyncMock())
        for patcher in (self.identity_patch, self.csrf_patch, self.users_patch, self.cache_patch):
            patcher.start()
            self.addCleanup(patcher.stop)

    def _identity(self, user_id):
        if str(user_id) != str(self.player["_id"]):
            raise AssertionError("API received a different character ID")
        return copy.deepcopy(self.users.player)

    def test_quote_endpoint_is_read_only_and_uncached(self):
        response = self.client.get(
            f"/api/personagem/{self.player['_id']}/habilidades/{SKILL_ID}/aprimoramento"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Cache-Control"), "no-store")
        self.assertTrue(response.json["formula"]["can_upgrade"])
        self.assertEqual(self.users.player["gold"], 10000)

    def test_confirm_endpoint_atomically_consumes_materials_and_updates_level(self):
        response = self.client.post(
            "/api/personagem/aprimorar_habilidade",
            json={"user_id": str(self.player["_id"]), "skill_id": SKILL_ID},
        )

        self.assertEqual(response.status_code, 200)
        saved = self.users.player
        self.assertEqual(saved["gold"], 9850)
        self.assertEqual(saved["skills"][SKILL_ID]["level"], 2)
        self.assertEqual(saved["database_skills"][SKILL_ID]["level"], 2)
        self.assertEqual(saved["inventory"][f"tomo_{SKILL_ID}"]["quantity"], 1)

    def test_confirm_endpoint_rejects_stale_compare_and_set(self):
        self.users.reject_update = True

        response = self.client.post(
            "/api/personagem/aprimorar_habilidade",
            json={"user_id": str(self.player["_id"]), "skill_id": SKILL_ID},
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.users.player["gold"], 10000)
        self.assertEqual(self.users.player["skills"][SKILL_ID]["level"], 1)


if __name__ == "__main__":
    unittest.main()
