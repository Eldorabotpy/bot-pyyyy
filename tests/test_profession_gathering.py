import ast
import copy
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from flask import Flask

ROOT = Path(__file__).resolve().parents[1]
TOOLS = {'frasco_vidro': 'alquimista', 'faca_pedra': 'esfolador', 'picareta_pedra': 'minerador', 'machado_pedra': 'lenhador', 'foice_pedra': 'colhedor'}

def load_functions(path, names, ns):
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8'))
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
    for node in nodes:
        node.decorator_list = []
    exec(compile(ast.Module(body=nodes, type_ignores=[]), path, 'exec'), ns)

class GatheringTests(unittest.TestCase):
    def setUp(self):
        self.player = {'inventory': {'frasco_vidro': {'base_id': 'frasco_vidro', 'durability': [0,20]}, 'crafted-uuid': {'base_id': 'frasco_vidro', 'durability': [19,20]}}, 'equipment_tools': {'alquimista': 'crafted-uuid'}, 'learned_professions': {'alquimista': {'level':1, 'xp':0}}, 'profession': {'key':'alquimista','level':1,'xp':0}}
        self.writes = []
        engine = types.ModuleType('modules.profession_engine')
        engine._get_item_info = lambda base: {'tool_type': TOOLS[base], 'durability':[10,10]}
        load_functions('modules/profession_engine.py', {'_norm_tool_key','_get_equipped_tool','validate_and_prepare_gather','_repair_durability'}, engine.__dict__)
        modules = types.ModuleType('modules'); modules.profession_engine = engine
        core = types.ModuleType('modules.player.core')
        core.users_collection = types.SimpleNamespace(find_one=lambda q: copy.deepcopy(self.player), update_one=lambda q,u: self.writes.append(u))
        self.patcher = patch.dict(sys.modules, {'modules':modules,'modules.profession_engine':engine,'modules.player.core':core})
        self.patcher.start(); self.addCleanup(self.patcher.stop)
        ns = {}
        load_functions('rotas/character.py', {'coletar_recurso'}, ns)
        self.app = Flask(__name__)
        self.app.add_url_rule('/collect', view_func=ns['coletar_recurso'], methods=['POST'])
        self.client = self.app.test_client()

    def call(self, resource='sangue', action='coletar'):
        return self.client.post('/collect', json={'user_id':'0123456789abcdef01234567','recurso_tipo':resource,'acao':action})

    def test_uses_equipped_uuid_instead_of_broken_old_flask(self):
        response = self.call()
        self.assertEqual(response.status_code, 200, response.json)
        update = self.writes[0]['$set']
        self.assertEqual(update['inventory.crafted-uuid']['durability'], [18,20])
        self.assertNotIn('inventory.frasco_vidro', update)
        self.assertGreater(update['inventory.sangue']['quantity'], 0)
        self.assertEqual(update['learned_professions']['alquimista']['xp'], 10)

    def test_preview_does_not_wear_or_award(self):
        self.assertEqual(self.call(action='verificar').status_code,200)
        self.assertEqual(self.writes, [])

    def test_broken_equipped_tool_does_not_use_spare(self):
        self.player['inventory']['crafted-uuid']['durability'] = [0,20]
        self.player['inventory']['frasco_vidro']['durability'] = [20,20]
        response = self.call()
        self.assertEqual(response.status_code,400)
        self.assertIn('quebrada',response.json['error'])
        self.assertEqual(self.writes,[])

    def test_must_equip_and_learn_profession(self):
        for field in ('equipment_tools', 'learned_professions'):
            with self.subTest(field=field):
                original = self.player[field]
                self.player[field] = {}
                self.player['profession'] = {}
                self.assertEqual(self.call().status_code,400)
                self.player[field] = original
        self.assertEqual(self.writes,[])

    def test_all_gathering_professions_and_legacy_slot(self):
        for resource, base in [('madeira','machado_pedra'),('pedra','picareta_pedra'),('ferro','picareta_pedra'),('minerio_de_ferro','picareta_pedra'),('linho','foice_pedra'),('pena','faca_pedra'),('sangue','frasco_vidro')]:
            for legacy in (False,True):
                with self.subTest(resource=resource, legacy=legacy):
                    profession = TOOLS[base]
                    self.player = {'inventory':{'uuid':{'base_id':base,'durability':{'current':1,'max':20}}}, 'learned_professions':{profession:{'level':1,'xp':0}}, 'equipment':{'tool':'uuid'} if legacy else {}, 'equipment_tools':{} if legacy else {profession:'uuid'}}
                    self.writes.clear()
                    response = self.call(resource)
                    self.assertEqual(response.status_code,200,response.json)
                    self.assertEqual(self.writes[0]['$set']['inventory.uuid']['durability'],[0,20])

    def test_unknown_resource_rejected_without_writes(self):
        self.assertEqual(self.call('gold').status_code,400)
        self.assertEqual(self.writes,[])

if __name__ == '__main__': unittest.main()
