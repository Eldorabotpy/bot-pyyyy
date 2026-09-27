import ast
import asyncio
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
# Carrega as funções puras sem importar a conexão com o banco de produção.
source = ast.parse((ROOT / 'modules/profession_engine.py').read_text(encoding='utf-8'))
names = {'_inv_qty', '_dur_tuple', '_set_dur', '_consume_repair_scroll', 'restore_durability', 'restore_all_equipped_durability'}
ns = {'Tuple': tuple, '_get_item_info': lambda base: {'durability': [90, 90]} if base == 'martelo' else {}}
exec(compile(ast.Module(body=[n for n in source.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names], type_ignores=[]), '<repair>', 'exec'), ns)

class RepairTests(unittest.TestCase):
    def player(self, scroll=2):
        return {'inventory': {'crafted': {'base_id': 'espada', 'durability': [0, 45], 'sockets': ['runa_vampiro_menor']}, 'tool': {'base_id': 'martelo', 'durability': [0, 90]}, 'pergaminho_de_reparo': scroll}, 'equipment': {'weapon': 'crafted'}, 'equipment_tools': {'ferreiro': 'tool'}}

    def test_individual_preserves_crafted_maximum_and_runes(self):
        p = self.player()
        result = asyncio.run(ns['restore_durability'](p, 'crafted'))
        self.assertNotIn('error', result)
        self.assertEqual(p['inventory']['crafted']['durability'], [45, 45])
        self.assertEqual(p['inventory']['crafted']['sockets'], ['runa_vampiro_menor'])
        self.assertEqual(p['inventory']['pergaminho_de_reparo'], 1)

    def test_mass_repairs_combat_and_profession_with_one_scroll(self):
        p = self.player()
        result = asyncio.run(ns['restore_all_equipped_durability'](p))
        self.assertEqual(result['count'], 2)
        self.assertEqual(p['inventory']['tool']['durability'], [90, 90])
        self.assertEqual(p['inventory']['crafted']['durability'], [45, 45])
        self.assertEqual(p['inventory']['pergaminho_de_reparo'], 1)

    def test_full_item_does_not_consume(self):
        p = self.player()
        p['inventory']['crafted']['durability'] = [45, 45]
        self.assertIn('error', asyncio.run(ns['restore_durability'](p, 'crafted')))
        self.assertEqual(p['inventory']['pergaminho_de_reparo'], 2)

    def test_uid_and_legacy_scroll_formats(self):
        for base in ('pergaminho_de_reparo', 'pergaminho_durabilidade'):
            for qty_key in ('quantity', 'qtd'):
                p = self.player()
                del p['inventory']['pergaminho_de_reparo']
                p['inventory']['scroll-uid'] = {'base_id': base, qty_key: 1}
                self.assertNotIn('error', asyncio.run(ns['restore_all_equipped_durability'](p)))
                self.assertNotIn('scroll-uid', p['inventory'])

    def test_no_scroll_no_repair(self):
        p = self.player(0)
        self.assertIn('error', asyncio.run(ns['restore_durability'](p, 'tool')))
        self.assertEqual(p['inventory']['tool']['durability'], [0, 90])

if __name__ == '__main__':
    unittest.main()
