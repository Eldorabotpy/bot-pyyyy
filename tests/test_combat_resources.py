import ast
import unittest
from pathlib import Path

source = (Path(__file__).resolve().parents[1] / 'modules/player/stats.py').read_text(encoding='utf-8')
tree = ast.parse(source)
names = {'_recuperar_recursos_combate', '_apply_passive_skill_bonuses', '_apply_party_aura_bonuses', '_map_stat_name'}
nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names or isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SPECIAL_COMBAT_FLOAT_KEYS' for t in n.targets)]
ns = {'SKILL_DATA': {}}
exec(compile(ast.Module(body=nodes, type_ignores=[]), '<combat-resources>', 'exec'), ns)
recover = ns['_recuperar_recursos_combate']

class ResourceTests(unittest.TestCase):
    def test_lifesteal_rune_percent(self):
        self.assertEqual(recover({'max_hp':100, 'lifesteal':5}, 50, 0, 200), (60, 0))
    def test_caps(self):
        self.assertEqual(recover({'max_hp':100, 'max_mana':50, 'lifesteal':100, 'hp_regen_percent':.5, 'mp_regen_percent':.5}, 98, 49, 200, True), (100, 50))
    def test_dead_never_regenerates(self):
        self.assertEqual(recover({'max_hp':100, 'hp_regen_percent':1}, 0, 0, regenerar=True), (0, 0))
    def test_regeneration_fraction(self):
        self.assertEqual(recover({'max_hp':1000, 'max_mana':200, 'hp_regen_percent':.005, 'mp_regen_percent':.01}, 500, 0, regenerar=True), (505, 2))
    def test_no_damage_no_lifesteal(self):
        self.assertEqual(recover({'max_hp':100, 'lifesteal':5}, 50, 0), (50, 0))
    def test_passives_and_aura_keep_fraction(self):
        ns['SKILL_DATA'] = {'passive': {'type':'passive', 'rarity_effects': {'comum': {'effects': {'stat_add_mult': {'crit_chance_flat':.05, 'armor_penetration':.15}, 'crit_resistance_flat':.15, 'party_aura': {'hp_regen_percent':.005, 'resistance_mult': {'physical':.08}}}}}}}
        player = {'skills': {'passive': {'rarity':'comum'}}}
        stats = {'attack':100}
        ns['_apply_passive_skill_bonuses'](player, stats)
        ns['_apply_party_aura_bonuses'](player, stats)
        self.assertEqual(stats['crit_chance_flat'], 5)
        self.assertEqual(stats['armor_penetration'], .15)
        self.assertEqual(stats['crit_resistance_flat'], .15)
        self.assertEqual(stats['hp_regen_percent'], .005)
        self.assertEqual(stats['resistance']['physical'], .08)

if __name__ == '__main__':
    unittest.main(verbosity=2)
