import unittest

from modules.encyclopedia import build_catalog


class EncyclopediaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nodes = build_catalog()
        cls.index = {node['id']: node for node in cls.nodes}

    def test_all_pages_have_valid_paths_without_cycles(self):
        roots = {'mundo', 'classes', 'combate', 'profissoes', 'itens', 'runas',
                 'criaturas', 'dungeons', 'guilda', 'clas', 'economia',
                 'forja_alquimia', 'eventos'}
        self.assertEqual(len(self.nodes), len(self.index))
        for node in self.nodes:
            seen = set()
            current = node
            while current['parent'] not in roots:
                self.assertNotIn(current['id'], seen)
                seen.add(current['id'])
                self.assertIn(current['parent'], self.index)
                current = self.index[current['parent']]

    def test_capital_has_real_services_and_class_has_real_evolution(self):
        for npc in ('merlin', 'flora', 'varek', 'selene', 'thorek', 'paracelso', 'forja', 'refino', 'guilda', 'mercado'):
            self.assertEqual(self.index['capital:' + npc]['parent'], 'regiao:reino_eldora')
        children = [x for x in self.nodes if x['parent'] == 'classe:guerreiro']
        self.assertTrue(any(x['id'].startswith('skill:') for x in children))
        self.assertTrue(any(x['titulo'] == 'Cavaleiro' for x in children))

    def test_catalog_tracks_live_recipe_data(self):
        from modules.alchemy.bruxa_pocoes import RECEITAS_BRUXA
        recipe = RECEITAS_BRUXA['elixir_xp_dobrado_10m']
        before = recipe['gold_cost']
        try:
            recipe['gold_cost'] = 9876
            node = next(n for n in build_catalog() if n['id'] == 'receita:Caldeirão da Bruxa:elixir_xp_dobrado_10m')
            self.assertIn(['Custo em ouro', '9876'], node['secoes'])
        finally:
            recipe['gold_cost'] = before


if __name__ == '__main__':
    unittest.main()
