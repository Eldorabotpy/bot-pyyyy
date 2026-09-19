import ast
import asyncio
import unittest
from pathlib import Path
from types import SimpleNamespace

root = Path(__file__).resolve().parents[1]
ns = {}
tree = ast.parse((root/'modules/player/stats.py').read_text(encoding='utf-8'))
nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {'_recuperar_recursos_combate', '_aplicar_golpes_combate'}]
exec(compile(ast.Module(body=nodes, type_ignores=[]), '<hits>', 'exec'), ns)
apply_hits = ns['_aplicar_golpes_combate']

class PerHitTests(unittest.TestCase):
    def result(self, damages):
        return {'hits':[{'damage':d,'critical':False,'hit_number':i+1,'log_index':i} for i,d in enumerate(damages)], 'log_messages':['hit']*len(damages)}
    def test_separate_damage_and_healing(self):
        hp,mp,mob,logs=apply_hits(self.result([30,50]), {'max_hp':100,'lifesteal':10}, 50,0,100)
        self.assertEqual([x['dano'] for x in logs], [30,50])
        self.assertEqual([x['roubo_vida'] for x in logs], [3,5])
        self.assertEqual([x['player_hp_apos_golpe'] for x in logs], [53,58])
        self.assertEqual((hp,mob),(58,20))
    def test_no_second_hit_after_kill(self):
        hp,_,mob,logs=apply_hits(self.result([100,100]), {'max_hp':100,'lifesteal':10}, 50,0,20)
        self.assertEqual((hp,mob,len(logs)),(52,0,1))
        self.assertEqual(logs[0]['dano'],20)
    def test_dodge_does_not_heal(self):
        _,_,_,logs=apply_hits(self.result([0,50]), {'max_hp':100,'lifesteal':10},50,0,100)
        self.assertEqual([x['roubo_vida'] for x in logs],[0,5])
    def test_actual_healing_capped_per_hit(self):
        hp,_,_,logs=apply_hits(self.result([30,50]), {'max_hp':100,'lifesteal':10},99,0,100)
        self.assertEqual([x['roubo_vida'] for x in logs],[1,0])
        self.assertEqual(hp,100)
    def test_lifesteal_label_requires_equipped_rune_and_healing(self):
        for stats, expected in [
            ({'max_hp':100}, False),
            ({'max_hp':100,'lifesteal_flat':.1}, False),
            ({'max_hp':100,'lifesteal':10,'runa_roubo_vida_ativa':True}, True),
        ]:
            _,_,_,logs=apply_hits(self.result([30]),stats,50,0,100)
            self.assertEqual(logs[0]['mostrar_roubo_vida'],expected)
            self.assertEqual('Roubou' in logs[0]['texto'],expected)
        _,_,_,logs=apply_hits(self.result([30]),{'max_hp':100,'lifesteal':10,'runa_roubo_vida_ativa':True},100,0,100)
        self.assertFalse(logs[0]['mostrar_roubo_vida'])
        self.assertNotIn('Roubou',logs[0]['texto'])

    def test_engine_emits_each_hit_with_matching_log(self):
        tree=ast.parse((root/'modules/combat/combat_engine.py').read_text(encoding='utf-8'))
        node=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='processar_acao_combate')
        rolls=iter([(30,False,False),(50,True,False)])
        engine={'random':SimpleNamespace(random=lambda:0), 'criticals':SimpleNamespace(roll_damage=lambda *args:next(rolls)), 'durability':SimpleNamespace(is_weapon_broken=lambda _: (False,None,(10,10)))}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<engine>','exec'),engine)
        result=asyncio.run(engine['processar_acao_combate']({}, {'initiative':100}, {}, None))
        self.assertEqual([h['damage'] for h in result['hits']],[30,50])
        self.assertEqual(result['total_damage'],80)
        self.assertTrue(result['hits'][1]['critical'])
        self.assertEqual([h['log_index'] for h in result['hits']],[1,2])

if __name__=='__main__': unittest.main(verbosity=2)
