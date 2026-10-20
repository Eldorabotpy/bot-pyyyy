from datetime import datetime, timedelta, timezone
from copy import deepcopy
import os
import sys
import unittest
from unittest.mock import patch


# The manager tries to ensure Mongo indexes during import. Keep this unit test
# isolated from real game databases and make its expected connection failure fast.
_mongo_env = os.environ.get("MONGO_CONNECTION_STRING")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ["MONGO_CONNECTION_STRING"] = (
    "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=10"
)
try:
    from modules import premium_store_manager
finally:
    if _mongo_env is None:
        os.environ.pop("MONGO_CONNECTION_STRING", None)
    else:
        os.environ["MONGO_CONNECTION_STRING"] = _mongo_env


def _premium_order():
    plano = premium_store_manager.obter_eldora_premium()
    return {
        "dias": plano["dias"],
        "chaves_masmorra": plano["chaves_masmorra"],
        "trocas_classe": plano["trocas_classe"],
        "trocas_profissao": plano["trocas_profissao"],
        "pocoes_xp_g": plano["pocoes_xp_g"],
    }


class PremiumEntitlementTests(unittest.TestCase):
    def test_plan_contains_requested_rewards(self):
        plano = premium_store_manager.obter_eldora_premium()

        self.assertEqual(plano["trocas_classe"], 1)
        self.assertEqual(plano["trocas_profissao"], 1)
        self.assertEqual(plano["pocoes_xp_g"], 5)

    def test_approval_grants_profession_credit_and_five_large_xp_potions(self):
        agora = datetime(2026, 10, 20, tzinfo=timezone.utc)
        resultado = premium_store_manager._preparar_credito_eldora_premium(
            jogador={"inventory": {}},
            pedido=_premium_order(),
            codigo_pedido="premium-test-1",
            agora=agora,
        )

        self.assertEqual(resultado["eldora_premium"]["class_change_credits"], 1)
        self.assertEqual(resultado["eldora_premium"]["profession_change_credits"], 1)
        self.assertEqual(resultado["inventory"]["pocao_xp_boost_g"], 5)

    def test_renewal_stacks_potions_and_preserves_unspent_credits(self):
        agora = datetime(2026, 10, 20, tzinfo=timezone.utc)
        expira_em = agora + timedelta(days=10)
        jogador = {
            "eldora_premium": {
                "activated_at": agora - timedelta(days=20),
                "expires_at": expira_em,
                "class_change_credits": 2,
                "profession_change_credits": 0,
            },
            "inventory": {
                "pocao_xp_boost_g": {
                    "base_id": "pocao_xp_boost_g",
                    "quantity": 2,
                },
                "chave_masmorra": {
                    "base_id": "chave_masmorra",
                    "quantity": 3,
                },
            },
        }

        resultado = premium_store_manager._preparar_credito_eldora_premium(
            jogador=jogador,
            pedido=_premium_order(),
            codigo_pedido="premium-test-2",
            agora=agora,
        )

        self.assertEqual(resultado["eldora_premium"]["class_change_credits"], 3)
        self.assertEqual(resultado["eldora_premium"]["profession_change_credits"], 1)
        self.assertEqual(resultado["inventory"]["pocao_xp_boost_g"]["quantity"], 7)
        self.assertEqual(resultado["inventory"]["chave_masmorra"]["quantity"], 13)
        self.assertEqual(
            resultado["eldora_premium"]["expires_at"],
            expira_em + timedelta(days=30),
        )

    def test_active_legacy_premium_gets_one_profession_credit_once(self):
        agora = datetime.now(timezone.utc)
        jogador_id = premium_store_manager.ObjectId(
            "507f1f77bcf86cd799439011"
        )
        jogador = {
            "_id": jogador_id,
            "eldora_premium": {
                "expires_at": agora + timedelta(days=10),
                "profession_change_credits": 0,
            },
        }

        class FakeUsersCollection:
            def find_one(self, _query):
                return deepcopy(jogador)

            def find_one_and_update(self, query, update, return_document=None):
                premium = jogador["eldora_premium"]
                if premium.get("profession_change_credit_migration_v1") is True:
                    return None
                if premium.get("profession_change_credits") != query.get(
                    "eldora_premium.profession_change_credits"
                ):
                    return None
                if premium["expires_at"] <= query[
                    "eldora_premium.expires_at"
                ]["$gt"]:
                    return None

                for path, value in update["$set"].items():
                    _, key = path.split(".", 1)
                    premium[key] = value
                return deepcopy(jogador)

        with patch.object(premium_store_manager, "users_col", FakeUsersCollection()):
            migrado = premium_store_manager._migrar_credito_profissao_premium_antigo(
                jogador_id,
                jogador,
                agora,
            )
            novamente = premium_store_manager._migrar_credito_profissao_premium_antigo(
                jogador_id,
                migrado,
                agora,
            )

        self.assertEqual(migrado["eldora_premium"]["profession_change_credits"], 1)
        self.assertTrue(
            novamente["eldora_premium"]["profession_change_credit_migration_v1"]
        )
        self.assertEqual(
            novamente["eldora_premium"]["profession_change_credits"], 1
        )

    def test_legacy_migration_does_not_restore_already_used_credit(self):
        agora = datetime.now(timezone.utc)
        jogador_id = premium_store_manager.ObjectId(
            "507f1f77bcf86cd799439011"
        )
        jogador = {
            "_id": jogador_id,
            "eldora_premium": {
                "expires_at": agora + timedelta(days=10),
                "profession_change_credits": 0,
            },
            "premium_service_history": [
                {"tipo": "profissao", "origem": "eldora_premium"}
            ],
        }

        class FakeUsersCollection:
            def find_one(self, _query):
                return deepcopy(jogador)

            def find_one_and_update(self, query, update, return_document=None):
                premium = jogador["eldora_premium"]
                if premium.get("profession_change_credit_migration_v1") is True:
                    return None
                if premium.get("profession_change_credits") != query.get(
                    "eldora_premium.profession_change_credits"
                ):
                    return None

                for path, value in update["$set"].items():
                    _, key = path.split(".", 1)
                    premium[key] = value
                return deepcopy(jogador)

        with patch.object(premium_store_manager, "users_col", FakeUsersCollection()):
            migrado = premium_store_manager._migrar_credito_profissao_premium_antigo(
                jogador_id,
                jogador,
                agora,
            )

        self.assertEqual(migrado["eldora_premium"]["profession_change_credits"], 0)
        self.assertTrue(
            migrado["eldora_premium"]["profession_change_credit_migration_v1"]
        )

    def test_profession_change_consumes_premium_credit_before_gems(self):
        agora = datetime.now(timezone.utc)
        jogador = {
            "_id": premium_store_manager.ObjectId("507f1f77bcf86cd799439011"),
            "gems": 0,
            "profession": {"key": "lenhador", "level": 1},
            "learned_professions": {"lenhador": {"level": 1}},
            "maestrias_resgatadas": [],
            "player_state": {"action": "idle"},
            "inventory": {},
            "equipment_tools": {},
            "premium_tool_recoveries": [],
            "premium_service_history": [],
            "eldora_premium": {
                "expires_at": agora + timedelta(days=20),
                "profession_change_credits": 1,
                "profession_change_credit_migration_v1": True,
            },
        }

        class FakeUsersCollection:
            def find_one(self, _query, _projection=None):
                return deepcopy(jogador)

            def find_one_and_update(self, query, update, return_document=None):
                self.query = query
                self.update = update
                self_outer.assertGreater(
                    jogador["eldora_premium"]["expires_at"],
                    query["eldora_premium.expires_at"]["$gt"],
                )
                self_outer.assertEqual(
                    query["eldora_premium.profession_change_credits"],
                    {"$gte": 1},
                )

                updated = deepcopy(jogador)
                for path, amount in update["$inc"].items():
                    target = updated
                    parts = path.split(".")
                    for part in parts[:-1]:
                        target = target.setdefault(part, {})
                    target[parts[-1]] = target.get(parts[-1], 0) + amount
                for path, value in update["$set"].items():
                    target = updated
                    parts = path.split(".")
                    for part in parts[:-1]:
                        target = target.setdefault(part, {})
                    target[parts[-1]] = value
                for path, value in update["$push"].items():
                    updated.setdefault(path, []).append(value)
                jogador.clear()
                jogador.update(updated)
                return deepcopy(jogador)

        self_outer = self
        fake_users = FakeUsersCollection()
        with patch.object(premium_store_manager, "users_col", fake_users):
            resultado = premium_store_manager.comprar_servico_gemas(
                user_id=str(jogador["_id"]),
                tipo="profissao",
                destino="minerador",
                concordou=True,
            )

        self.assertTrue(resultado["success"], resultado)
        self.assertTrue(resultado["credito_premium_usado"])
        self.assertEqual(resultado["custo_gemas"], 0)
        self.assertEqual(jogador["gems"], 0)
        self.assertEqual(jogador["eldora_premium"]["profession_change_credits"], 0)
        self.assertEqual(jogador["profession"]["key"], "minerador")
        self.assertEqual(jogador["premium_service_history"][-1]["origem"], "eldora_premium")


if __name__ == "__main__":
    unittest.main()
