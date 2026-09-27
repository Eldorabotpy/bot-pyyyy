import ast, asyncio, copy, sys, types, unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
class ForgeTests(unittest.TestCase):
 def setUp(self):
  tree=ast.parse((ROOT/'modules/webapp_api.py').read_text(encoding='utf-8'))
  nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'_forja_tempo_restante','_forja_salvar_trabalho'}]
  self.doc={'_id':'hero','inventory':{'stone':3},'player_state':{'action':'idle'},'equipment':{},'equipment_tools':{}}
  owner=self
  class Collection:
   def update_one(inner,q,u):
    if any(owner.doc.get(k)!=v for k,v in q.items()):return types.SimpleNamespace(modified_count=0)
    owner.doc.update(copy.deepcopy(u['$set']));return types.SimpleNamespace(modified_count=1)
  self.cleared=[]
  async def clear(uid):self.cleared.append(uid)
  core=types.ModuleType('modules.player.core');core.clear_player_cache=clear
  p=patch.dict(sys.modules,{'modules.player.core':core});p.start();self.addCleanup(p.stop)
  self.ns={'users_collection':Collection(),'_run_async':asyncio.run}
  exec(compile(ast.Module(body=nodes,type_ignores=[]),'<forge>','exec'),self.ns)
 def test_deadlines(self):
  remaining=self.ns['_forja_tempo_restante']
  self.assertGreater(remaining({'finish_time':(datetime.now(timezone.utc)+timedelta(seconds=60)).isoformat()}),0)
  self.assertEqual(remaining({'finish_time':(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()}),0)
  for value in (None,'invalid',''):
   with self.assertRaises(ValueError):remaining({'finish_time':value})
 def test_duplicate_start_or_finish_rejected(self):
  for state in ({'action':'equipment_upgrading'},{'action':'idle'}):
   original=copy.deepcopy(self.doc)
   self.assertTrue(self.ns['_forja_salvar_trabalho'](original,{'stone':1},state))
   self.assertFalse(self.ns['_forja_salvar_trabalho'](original,{'stone':0},state))
   self.doc['inventory']={'stone':3}
 def test_inventory_changed_not_overwritten(self):
  original=copy.deepcopy(self.doc);self.doc['inventory']['loot']=1
  self.assertFalse(self.ns['_forja_salvar_trabalho'](original,{},{}))
  self.assertEqual(self.doc['inventory']['loot'],1)
 def test_finish_route_rejects_early_request_without_writes(self):
  from flask import Flask, request, jsonify
  tree=ast.parse((ROOT/'modules/webapp_api.py').read_text(encoding='utf-8'))
  node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='api_finish_equipment_upgrade')
  node.decorator_list=[]
  doc={'_id':'hero','player_state':{'action':'equipment_upgrading','finish_time':(datetime.now(timezone.utc)+timedelta(seconds=60)).isoformat()}}
  ns=dict(self.ns,request=request,jsonify=jsonify,_forja_parse_user_id=lambda value:value,users_collection=types.SimpleNamespace(find_one=lambda q:doc))
  exec(compile(ast.Module(body=[node],type_ignores=[]),'<finish>','exec'),ns)
  app=Flask(__name__)
  with app.test_request_context(json={'user_id':'hero'}):
   response,status=ns['api_finish_equipment_upgrade']()
   self.assertEqual(status,409)
   self.assertGreater(response.json['remaining_seconds'],0)
 def test_crafting_does_not_replace_active_work(self):
  tree=ast.parse((ROOT/'modules/crafting_engine.py').read_text(encoding='utf-8'))
  node=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='start_craft')
  for action in ('equipment_upgrading','in_combat','dismantling'):
   async def get_player(uid):return {'player_state':{'action':action}}
   ns={'player_manager':types.SimpleNamespace(get_player_data=get_player),'get_recipe':lambda rid:{'inputs':{}},'_as_dict':lambda value:value or {}}
   exec(compile(ast.Module(body=[node],type_ignores=[]),'<start>','exec'),ns)
   self.assertIn('ocupado',asyncio.run(ns['start_craft']('hero','recipe')))
if __name__=='__main__':unittest.main()
