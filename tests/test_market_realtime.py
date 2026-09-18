import ast, asyncio, sys, types, unittest
from pathlib import Path
from unittest.mock import patch
from flask import Flask, request, jsonify

class MarketRealtimeTests(unittest.TestCase):
 def setUp(self):
  self.app=Flask(__name__);self.events=[];self.committed=False
  def emit(event,data):
   self.assertTrue(self.committed)
   self.events.append((event,data))
  self.app.extensions['socketio']=types.SimpleNamespace(emit=emit)
  async def purchase(**kw):
   self.committed=True
   return {'_id':'listing','seller_id':'seller'},150
  self.manager=types.SimpleNamespace(get_listing=lambda _: {'seller_id':'stale'},purchase_listing=purchase)
  tree=ast.parse((Path(__file__).resolve().parents[1]/'modules/webapp_api.py').read_text(encoding='utf-8-sig'))
  nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'_avisar_atualizacao_mercado','api_comprar_mercado'}]
  for n in nodes:n.decorator_list=[]
  self.ns={'request':request,'jsonify':jsonify,'_run_async':asyncio.run}
  exec(compile(ast.Module(body=nodes,type_ignores=[]),'<market-api>','exec'),self.ns)
 def buy(self):
  modules=types.ModuleType('modules');modules.market_manager=self.manager
  core=types.ModuleType('modules.player.core');core.users_collection=None
  with patch.dict(sys.modules,{'modules':modules,'modules.player.core':core}), self.app.test_request_context(json={'user_id':'123','id_venda':'listing'}):
   return self.ns['api_comprar_mercado']().get_json()
 def test_notify_committed_seller_and_buyer(self):
  self.assertTrue(self.buy()['sucesso'])
  self.assertEqual(self.events,[('mercadoAtualizado',{'id_venda':'listing','jogadores':['123','seller']})])
 def test_failed_purchase_never_notifies(self):
  async def fail(**kw):raise ValueError('Saldo insuficiente')
  self.manager.purchase_listing=fail
  self.assertFalse(self.buy()['sucesso']);self.assertEqual(self.events,[])
 def test_socket_failure_does_not_fail_committed_purchase(self):
  def fail(*a):raise RuntimeError('Socket indisponível')
  self.app.extensions['socketio'].emit=fail
  self.app.logger.disabled=True
  self.assertTrue(self.buy()['sucesso']);self.assertTrue(self.committed)
if __name__=='__main__':unittest.main(verbosity=2)
