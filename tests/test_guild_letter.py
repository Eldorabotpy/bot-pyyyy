import ast,asyncio,copy,sys,types,unittest
from pathlib import Path
from unittest.mock import patch

class LetterTests(unittest.TestCase):
 def setUp(self):
  self.doc={'_id':'hero','inventory':{'carta_recomendacao':1,'pocao':7},'gold':99,'guild_missions':{'pontos':24}}
  self.writes=0;self.cleared=[]
  owner=self
  class Collection:
   def find_one(self,*a):return copy.deepcopy(owner.doc)
   def update_one(self,q,u):
    if not all(owner.doc.get(k)==v for k,v in q.items()):return types.SimpleNamespace(matched_count=0)
    owner.writes+=1;owner.doc.update(u.get('$set',{}))
    for key in u.get('$unset',{}):owner.doc['inventory'].pop(key.split('.',1)[1],None)
    return types.SimpleNamespace(matched_count=1)
  async def clear(uid):self.cleared.append(uid)
  core=types.ModuleType('modules.player.core');core.clear_player_cache=clear
  self.patch=patch.dict(sys.modules,{'modules.player.core':core});self.patch.start();self.addCleanup(self.patch.stop)
  tree=ast.parse((Path(__file__).resolve().parents[1]/'modules/webapp_api.py').read_text(encoding='utf-8'))
  node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_recolher_carta_guilda')
  ns={'users_collection':Collection(),'_run_async':asyncio.run}
  exec(compile(ast.Module(body=[node],type_ignores=[]),'<letter>','exec'),ns);self.collect=ns['_recolher_carta_guilda']
 def test_first_registration_consumes_and_preserves_other_data(self):
  self.assertTrue(self.collect('hero',concluir=True));self.assertTrue(self.doc['guild_intro_seen'])
  self.assertEqual(self.doc['inventory'],{'pocao':7});self.assertEqual(self.doc['gold'],99);self.assertEqual(self.doc['guild_missions']['pontos'],24);self.assertEqual(self.cleared,['hero'])
 def test_old_registration_removes_legacy_dictionary_letter(self):
  self.doc['guild_intro_seen']=True;self.doc['inventory']={'uid':{'base_id':'carta_recomendacao','quantity':1},'pocao':7}
  self.assertTrue(self.collect('hero'));self.assertEqual(self.doc['inventory'],{'pocao':7})
 def test_not_registered_keeps_letter(self):
  self.assertFalse(self.collect('hero'));self.assertEqual(self.writes,0)
 def test_repeat_does_not_consume_other_items(self):
  self.collect('hero',True);before=copy.deepcopy(self.doc)
  self.assertFalse(self.collect('hero',True));self.assertEqual(self.doc,before)
 def test_legacy_registered_without_letter_no_write(self):
  self.doc['guild_intro_seen']=True;self.doc['inventory']={'pocao':7}
  self.assertFalse(self.collect('hero'));self.assertEqual(self.writes,0)
if __name__=='__main__':unittest.main(verbosity=2)
