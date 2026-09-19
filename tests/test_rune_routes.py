import ast,copy,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
from flask import Flask,jsonify,request
from modules.rune_workshop import state_view

class RuneRouteTests(unittest.TestCase):
 def setUp(self):
  self.app=Flask(__name__);self.room=None;self.cleared=[]
  self.player={'_id':'p','gold':1000,'inventory':{'runa_vampiro_menor':3,'po_runico':5}}
  outer=self
  class Collection:
   def find_one(self,q):return copy.deepcopy(outer.player) if q['_id']=='p' else None
   def update_one(self,q,change):
    matches=all((key not in outer.player if isinstance(value,dict) and value=={'$exists':False} else outer.player.get(key)==value) for key,value in q.items())
    if matches:
     outer.player.update(copy.deepcopy(change.get('$set',{})))
     for key,value in change.get('$inc',{}).items():outer.player[key]=outer.player.get(key,0)+value
    return types.SimpleNamespace(modified_count=int(matches))
  async def clear(uid):self.cleared.append(uid)
  player_manager=types.ModuleType('modules.player_manager');player_manager.clear_player_cache=clear
  combat=types.ModuleType('modules.combat');combat.group_combat_manager=types.SimpleNamespace(obter_sala_do_jogador=lambda _:self.room)
  self.stubs={'modules.player_manager':player_manager,'modules.combat':combat}
  tree=ast.parse((Path(__file__).resolve().parents[1]/'modules/webapp_api.py').read_text(encoding='utf-8'))
  node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='api_runas_operar');node.decorator_list=[]
  import asyncio
  ns={'users_collection':Collection(),'_forja_parse_user_id':lambda uid:uid,'items_data':types.SimpleNamespace(ITEMS_DATA={}), '_run_async':asyncio.run,'jsonify':jsonify,'request':request}
  exec(compile(ast.Module(body=[node],type_ignores=[]),'<rune-route>','exec'),ns);self.route=ns['api_runas_operar']
 def call(self):
  with patch.dict(sys.modules,self.stubs),self.app.test_request_context(json={'user_id':'p','action':'evoluir','rune_id':'runa_vampiro_menor','revision':0}):
   result=self.route();return (result[0].get_json(),result[1]) if isinstance(result,tuple) else (result.get_json(),200)
 def test_success_then_duplicate_rejected(self):
  result,code=self.call();self.assertEqual(code,200);self.assertEqual(self.player['gold'],500);self.assertEqual(self.player['inventory']['runa_vampiro_maior'],1);self.assertEqual(self.cleared,['p'])
  self.assertEqual(self.call()[1],409);self.assertEqual(self.player['gold'],500)
 def test_group_combat_blocks(self):
  self.room={'estado':'em_andamento'};self.assertEqual(self.call()[1],409);self.assertEqual(self.player['gold'],1000)
 def test_live_solo_combat_blocks(self):
  self.player.update(rune_hunt_active={'regiao':'r','spawn_id':'m'},current_hp=100)
  self.app.config['SISTEMA_CACADA']=types.SimpleNamespace(mobs_vivos={'r':{'m':{'hp_atual':50}}})
  self.assertEqual(self.call()[1],409)
 def test_defeated_monster_releases(self):
  self.player.update(rune_hunt_active={'regiao':'r','spawn_id':'m'},current_hp=100)
  self.app.config['SISTEMA_CACADA']=types.SimpleNamespace(mobs_vivos={'r':{'m':{'hp_atual':0}}})
  self.assertEqual(self.call()[1],200)

if __name__=='__main__':unittest.main()
