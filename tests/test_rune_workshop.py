import copy, unittest, ast, types, sys
from pathlib import Path
from unittest.mock import patch
from modules import rune_workshop as w

class RuneTests(unittest.TestCase):
 def setUp(self):
  self.items={'sword':{'type':'equipamento'},'runa_vampiro_menor':{'type':'runa','stackable':True}}
  self.player={'_id':'p','gold':10000,'inventory':{'sword-1':{'base_id':'sword','rarity':'lendario','durability':[20,20]},'runa_vampiro_menor':6,'po_runico':50,'fragmento_runa_ancestral':10},'equipment':{'arma':'sword-1'}}
 def op(self,action,**kw):return w.apply_operation(self.player,{'action':action,**kw},self.items)
 def test_rarity_and_legacy(self):
  for rarity,n in [('comum',0),('bom',0),('raro',1),('épico',2),('lendario',3)]:self.assertEqual(len(w.sockets({'rarity':rarity})),n)
  self.assertEqual(w.sockets({'rarity':'raro','sockets':['old','old2']}),['old','old2'])
 def test_socket_consumes_one_and_preserves_item(self):
  inv,gold=self.op('encaixar',item_id='sword-1',slot=0,rune_id='runa_vampiro_menor')
  self.assertEqual(inv['runa_vampiro_menor'],5);self.assertEqual(inv['sword-1']['sockets'],['runa_vampiro_menor',None,None]);self.assertEqual(gold,10000)
  self.assertNotIn('sockets',self.player['inventory']['sword-1'])
 def test_duplicate_family_rejected(self):
  self.player['inventory']['sword-1']['sockets']=['runa_vampiro_maior',None,None]
  with self.assertRaisesRegex(ValueError,'família'):self.op('encaixar',item_id='sword-1',slot=1,rune_id='runa_vampiro_menor')
 def test_extract_returns_rune_and_charges(self):
  self.player['inventory']['sword-1']['sockets']=['runa_vampiro_menor']
  inv,gold=self.op('extrair',item_id='sword-1',slot=0)
  self.assertEqual(inv['runa_vampiro_menor'],7);self.assertEqual(gold,9900);self.assertEqual(inv['sword-1']['sockets'],[None]*3)
 def test_extract_insufficient_gold_does_not_mutate(self):
  self.player['inventory']['sword-1']['sockets']=['runa_vampiro_menor'];self.player['gold']=0
  before=copy.deepcopy(self.player)
  with self.assertRaises(ValueError):self.op('extrair',item_id='sword-1',slot=0)
  self.assertEqual(self.player,before)
 def test_evolve_exact_materials(self):
  inv,gold=self.op('evoluir',rune_id='runa_vampiro_menor')
  self.assertEqual(inv['runa_vampiro_menor'],3);self.assertEqual(inv['runa_vampiro_maior'],1);self.assertEqual(inv['po_runico'],45);self.assertEqual(gold,9500)
 def test_installed_runes_are_not_evolution_material(self):
  self.player['inventory']['runa_vampiro_menor']=2;self.player['inventory']['sword-1']['sockets']=['runa_vampiro_menor']
  with self.assertRaises(ValueError):self.op('evoluir',rune_id='runa_vampiro_menor')
 def test_dissolve(self):
  inv,_=self.op('dissolver',rune_id='runa_vampiro_menor');self.assertEqual(inv['po_runico'],52)
 def test_forge_seven_fragments(self):
  with patch('secrets.choice',return_value='runa_vampiro_menor'):inv,_=self.op('forjar')
  self.assertEqual(inv['fragmento_runa_ancestral'],3);self.assertEqual(inv['runa_vampiro_menor'],7)
 def test_invalid_item_slot_and_busy(self):
  for data in ({'item_id':'other','slot':0},{'item_id':'sword-1','slot':-1},{'item_id':'sword-1','slot':True}):
   with self.assertRaises(ValueError):self.op('encaixar',rune_id='runa_vampiro_menor',**data)
  self.player['player_state']={'action':'in_combat'}
  with self.assertRaises(ValueError):self.op('evoluir',rune_id='runa_vampiro_menor')
 def test_catalog_has_three_levels_each(self):
  self.assertEqual(len(w.RUNES_DB),24)
  for rune in w.RUNES_DB.values():
   if rune['next_id']:self.assertIn(rune['next_id'],w.RUNES_DB)
 def test_compare_and_swap_and_revision(self):
  class Collection:
   def update_one(inner,query,update):
    self.assertEqual(query['inventory'],self.player['inventory']);self.assertIn('equipment',query)
    return type('Result',(),{'modified_count':0})()
  with self.assertRaisesRegex(ValueError,'durante'):w.save_operation(Collection(),self.player,{'action':'evoluir','rune_id':'runa_vampiro_menor','revision':0},self.items)
  with self.assertRaisesRegex(ValueError,'Atualize'):w.save_operation(Collection(),self.player,{'revision':1},self.items)
 def test_equipped_bonuses_and_rewards(self):
  source=(Path(__file__).resolve().parents[1]/'modules/combat/durability.py').read_text(encoding='utf-8')
  nodes=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name in ('_dur_tuple','is_item_broken')]
  module=types.ModuleType('modules.combat.durability')
  exec(compile(ast.Module(body=nodes,type_ignores=[]),'<durability>','exec'),module.__dict__)
  self.player['inventory']['sword-1']['sockets']=['runa_vampiro_menor','runa_midas_menor','runa_sabio_menor']
  with patch.dict(sys.modules,{'modules.combat.durability':module}):
   self.assertEqual(w.equipped_bonuses(self.player)['lifesteal'],1)
   self.assertEqual(w.reward_bonus(self.player,100,100),(103,105))
   self.player['equipment']['weapon']='sword-1'
   self.assertEqual(w.equipped_bonuses(self.player)['lifesteal'],1)
   self.player['inventory']['sword-1']['durability']=[0,20]
   self.assertEqual(w.equipped_bonuses(self.player),{})
   self.player['inventory']['sword-1']['durability']=[20,20];self.player['equipment']={}
   self.assertEqual(w.equipped_bonuses(self.player),{})
 def test_view_only_gives_slots_to_gear(self):
  view=w.state_view(self.player,self.items)
  self.assertEqual(len(view['equipamentos']),1)
  self.assertEqual(view['equipamentos'][0]['sockets'],[None]*3)

 def test_stack_variants(self):
  for field in ('qty','qtd','quantity'):
   inv={'a':{'base_id':'r','%s'%field:2},'r':1};w.consume(inv,'r',3);self.assertEqual(inv,{})

if __name__=='__main__':unittest.main(verbosity=2)
