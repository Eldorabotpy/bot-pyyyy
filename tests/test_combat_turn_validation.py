import ast,asyncio,copy,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
from bson import ObjectId
class TurnTests(unittest.TestCase):
 def setUp(self):
  self.uid=str(ObjectId());self.ticks=0;self.player={'_id':ObjectId(self.uid),'current_hp':100,'current_mp':0}
  self.room={'sala_id':'room','estado':'em_andamento','membros_ids':[self.uid],'spawn_id':'spawn'}
  self.turn='other';self.auras=None
  async def clear(*a):pass
  def tick(p):self.ticks+=1;return p,[]
  async def stats(p,allies):self.auras=allies;raise RuntimeError('STOP_AFTER_STATS')
  manager=types.ModuleType('modules.player_manager');manager.clear_player_cache=clear
  modules=types.ModuleType('modules');modules.player_manager=manager
  combat=types.ModuleType('modules.combat');combat.group_combat_manager=types.SimpleNamespace(obter_sala=lambda _:self.room,obter_sala_por_spawn=lambda *a:self.room,pegar_combatente_atual=lambda _:self.turn,pacote_estado_sala=lambda _:copy.deepcopy(self.room),ESTADO_EM_ANDAMENTO='em_andamento')
  consumables=types.ModuleType('modules.game_data.items_consumables');consumables.CONSUMABLES_DATA={}
  cooldowns=types.ModuleType('modules.cooldowns');cooldowns.iniciar_turno=tick
  self.stubs={'modules':modules,'modules.combat':combat,'modules.game_data.items_consumables':consumables,'modules.cooldowns':cooldowns}
  source=(Path(__file__).resolve().parents[1]/'modules/player/stats.py').read_text(encoding='utf-8')
  node=next(n for n in ast.parse(source).body if isinstance(n,ast.AsyncFunctionDef) and n.name=='processar_turno_combate')
  ns={'users_collection':types.SimpleNamespace(find_one=lambda _:self.player),'get_player_total_stats':stats}
  exec(compile(ast.Module(body=[node],type_ignores=[]),'<turn>','exec'),ns);self.run=ns['processar_turno_combate']
 def call(self):
  with patch.dict(sys.modules,self.stubs):return asyncio.run(self.run(self.uid,'atacar','spawn',None,types.SimpleNamespace(mobs_vivos={'forest':{'spawn':{'hp_atual':100}}}),{},None,sala_id='room'))
 def test_wrong_turn_does_not_spend_cooldown(self):self.assertIn('erro',self.call());self.assertEqual(self.ticks,0)
 def test_outsider_cannot_attack(self):self.room['membros_ids']=[];self.assertIn('erro',self.call());self.assertEqual(self.ticks,0)
 def test_dead_hero_cannot_attack(self):self.turn=self.uid;self.player['current_hp']=0;self.assertIn('erro',self.call());self.assertEqual(self.ticks,0)
 def test_group_passes_allies_to_stats(self):
  self.turn=self.uid
  with self.assertRaisesRegex(RuntimeError,'STOP_AFTER_STATS'):self.call()
  self.assertEqual(self.auras,[self.uid])
if __name__=='__main__':unittest.main(verbosity=2)
