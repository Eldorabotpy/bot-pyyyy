import ast
import copy
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def matches(document, query):
    for key, expected in query.items():
        actual = document.get(key)
        if isinstance(expected, dict):
            if "$in" in expected and actual not in expected["$in"]:
                return False
            if "$ne" in expected and actual == expected["$ne"]:
                return False
        elif actual != expected:
            return False
    return True


class Result:
    def __init__(self, modified_count):
        self.modified_count = modified_count


class FakeCollection:
    def __init__(self, document):
        self.document = copy.deepcopy(document)

    def find_one(self, query, projection=None):
        return copy.deepcopy(self.document) if matches(self.document, query) else None

    def update_one(self, query, update):
        if not matches(self.document, query):
            return Result(0)
        for key, value in update.get("$set", {}).items():
            self.document[key] = copy.deepcopy(value)
        for key, value in update.get("$inc", {}).items():
            self.document[key] = self.document.get(key, 0) + value
        for key, value in update.get("$addToSet", {}).items():
            values = self.document.setdefault(key, [])
            if value not in values:
                values.append(copy.deepcopy(value))
        return Result(1)

    def find_one_and_update(self, query, update, return_document=None):
        result = self.update_one(query, update)
        return copy.deepcopy(self.document) if result.modified_count else None


def load_functions():
    source = (ROOT / "modules/premium_store_manager.py").read_text(encoding="utf-8-sig")
    tree = ast.parse(source)
    wanted = {"aprovar_pedido_manual", "recusar_pedido_manual"}
    nodes = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in wanted
    ]
    namespace = {
        "STATUS_AGUARDANDO_PAGAMENTO": "aguardando_pagamento",
        "STATUS_EM_ANALISE": "em_analise",
        "STATUS_PROCESSANDO_APROVACAO": "processando_aprovacao",
        "STATUS_APROVADO": "aprovado",
        "STATUS_RECUSADO": "recusado",
        "_agora": lambda: datetime.now(timezone.utc),
        "_serializar_pedido_admin": lambda pedido: copy.deepcopy(pedido),
        "ReturnDocument": type("ReturnDocument", (), {"AFTER": object()}),
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<manual-orders>", "exec"), namespace)
    return namespace


class PremiumManualOrdersTest(unittest.TestCase):
    def setUp(self):
        self.ns = load_functions()
        self.order = FakeCollection({
            "_id": "order-1",
            "codigo": "ELD-00000020",
            "user_id": "player-1",
            "gemas": 3500,
            "status": "aguardando_pagamento",
        })
        self.users = FakeCollection({
            "_id": "player-1",
            "gems": 179,
            "premium_order_credits": [],
        })
        self.ns["premium_orders_col"] = self.order
        self.ns["users_col"] = self.users

    def test_awaiting_order_can_be_approved_only_once(self):
        first = self.ns["aprovar_pedido_manual"]("ELD-00000020")
        second = self.ns["aprovar_pedido_manual"]("ELD-00000020")

        self.assertTrue(first["success"])
        self.assertTrue(second["success"])
        self.assertTrue(second["ja_processado"])
        self.assertEqual(self.order.document["status"], "aprovado")
        self.assertEqual(self.users.document["gems"], 3679)

    def test_awaiting_order_can_be_rejected_without_receipt(self):
        result = self.ns["recusar_pedido_manual"](
            "ELD-00000020", motivo="Comprovante privado inválido"
        )

        self.assertTrue(result["success"])
        self.assertEqual(self.order.document["status"], "recusado")
        self.assertEqual(self.users.document["gems"], 179)


if __name__ == "__main__":
    unittest.main()
