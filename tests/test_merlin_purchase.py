import ast
import copy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from flask import Flask, jsonify, request


class MerlinPurchaseTest(unittest.TestCase):
    def setUp(self):
        tree = ast.parse((Path(__file__).resolve().parents[1] / 'modules/webapp_api.py').read_text(encoding='utf-8-sig'))
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'api_loja_comprar')
        node.decorator_list = []
        ns = dict(request=request, jsonify=jsonify, copy=copy, MERLIN_ITENS=('pocao_cura_leve',))
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<merlin>', 'exec'), ns)
        self.app = Flask(__name__)
        self.app.add_url_rule('/buy', view_func=ns['api_loja_comprar'], methods=['POST'])
        self.player = {'_id': 1, 'gold': 1000, 'inventory': {}}
        self.race = False
        self.core = SimpleNamespace(users_collection=SimpleNamespace(find_one=lambda query: copy.deepcopy(self.player), update_one=self.update))

    def update(self, query, changes):
        if self.race or query['gold'] != self.player['gold'] or query['inventory'] != self.player['inventory']:
            return SimpleNamespace(modified_count=0)
        self.player.update(copy.deepcopy(changes['$set']))
        return SimpleNamespace(modified_count=1)

    def buy(self, qty):
        with patch.dict('sys.modules', {'modules.player.core': self.core}):
            return self.app.test_client().post('/buy', json={'user_id': '1', 'item_id': 'pocao_cura_leve', 'quantidade': qty, 'preco': 1})

    def test_quantity_and_official_price(self):
        result = self.buy(3)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.player['gold'], 700)
        self.assertEqual(self.player['inventory']['pocao_cura_leve']['quantity'], 3)

    def test_invalid_quantities_and_insufficient_funds_do_not_mutate(self):
        before = copy.deepcopy(self.player)
        for qty in (0, -1, 1.5, True, '3', 1000, 11):
            with self.subTest(qty=qty):
                self.assertEqual(self.buy(qty).status_code, 400)
                self.assertEqual(self.player, before)

    def test_existing_stack_and_concurrent_change(self):
        self.player['inventory'] = {'pocao_cura_leve': 2}
        self.assertEqual(self.buy(3).status_code, 200)
        self.assertEqual(self.player['inventory']['pocao_cura_leve'], 5)
        self.race = True
        before = copy.deepcopy(self.player)
        self.assertEqual(self.buy(1).status_code, 409)
        self.assertEqual(self.player, before)


if __name__ == '__main__':
    unittest.main()
