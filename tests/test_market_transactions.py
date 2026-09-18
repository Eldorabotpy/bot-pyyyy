import asyncio, copy, importlib.util, sys, types, unittest
from pathlib import Path
from unittest.mock import patch
from bson import ObjectId
ROOT=Path(__file__).resolve().parents[1]
class Store:
 def __init__(self): self.data={};self.client=self;self.n=0;self.fail=None;self.retry=False
 def __getitem__(self,k): return Collection(self,k)
 def start_session(self): return Session(self)
 def write(self):
  self.n+=1
  if self.n==self.fail: raise RuntimeError('Falha simulada na gravação')
class Session:
 def __init__(self,db):self.db=db
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def with_transaction(self,callback,**kwargs):
  before=copy.deepcopy(self.db.data)
  try:
   if self.db.retry:
    callback(self); self.db.data=copy.deepcopy(before);self.db.retry=False
   return callback(self)
  except Exception:
   self.db.data=before;raise
class Collection:
 def __init__(self,db,name):self.database=db;self.name=name
 @property
 def docs(self):return self.database.data.setdefault(self.name,[])
 def find_one(self,q,**kw):
  return next((copy.deepcopy(d) for d in self.docs if all(d.get(k)==v for k,v in q.items())),None)
 def insert_one(self,d,**kw):
  self.database.write();d.setdefault('_id',ObjectId());self.docs.append(copy.deepcopy(d))
 def update_one(self,q,u,**kw):
  self.database.write()
  for d in self.docs:
   if all(d.get(k)==v for k,v in q.items()):
    d.update(copy.deepcopy(u.get('$set',{})))
    for k,v in u.get('$inc',{}).items():d[k]=d.get(k,0)+v
    return types.SimpleNamespace(matched_count=1)
  return types.SimpleNamespace(matched_count=0)
 def find_one_and_update(self,q,u,**kw):
  if not self.find_one(q):self.docs.append(copy.deepcopy(q))
  self.update_one(q,u);return self.find_one(q)
class MarketTests(unittest.TestCase):
 def setUp(self):
  self.db=Store();self.seller=ObjectId();self.buyer=ObjectId()
  self.db['users'].docs.extend([{'_id':self.seller,'gold':10,'gems':0,'inventory':{'herb':20}}, {'_id':self.buyer,'gold':1000,'gems':1000,'inventory':{}}])
  core=types.ModuleType('modules.player.core');core.users_collection=self.db['users'];core._player_cache={};core._player_cache_time={}
  player=types.ModuleType('modules.player');player.core=core
  items=types.ModuleType('modules.game_data.items');items.ITEMS_DATA={'herb':{'stackable':True},'sword':{'type':'weapon','stackable':False},'xp':{'tradable':False},'evolution':{}}
  evo=types.ModuleType('modules.game_data.items_evolution');evo.EVOLUTION_ITEMS_DATA={'evolution':{}}
  stubs={'modules':types.ModuleType('modules'),'modules.player':player,'modules.player.core':core,'modules.game_data':types.ModuleType('modules.game_data'),'modules.game_data.items':items,'modules.game_data.items_evolution':evo}
  with patch.dict(sys.modules,stubs):
   spec=importlib.util.spec_from_file_location('tested_market',ROOT/'modules/market_manager.py');self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
 def sell(self,**kw):return self.m.create_listing(seller_id=str(self.seller),item_id=kw.pop('item_id','herb'),total_price=kw.pop('price',100),quantity=kw.pop('qty',3),**kw)
 def buy(self,l,**kw):return asyncio.run(self.m.purchase_listing(buyer_id=str(self.buyer),listing_id=l['_id'],**kw))
 def cancel(self,l,uid=None):return asyncio.run(self.m.cancel_listing(l['_id'],seller_id=str(uid or self.seller)))
 def test_potion_stack_with_default_equipment_fields(self):
  self.m.ITEMS_DATA['potion']={'type':'consumivel','stackable':True}
  for field in ['quantity','qty','qtd']:
   with self.subTest(field=field):
    self.db['users'].docs[0]['inventory']={'potion':{'base_id':'potion',field:10,'upgrade_level':0,'durability':None,'enchantments':{}}}
    l=self.sell(item_id='potion',qty=3,price=150)
    self.assertEqual(l['item']['type'],'stack')
    self.assertEqual(self.m._quantity(self.db['users'].docs[0]['inventory']['potion']),7)
    self.cancel(l)
    self.assertEqual(self.m._quantity(self.db['users'].docs[0]['inventory']['potion']),10)
 def test_potion_stack_purchase(self):
  self.m.ITEMS_DATA['potion']={'type':'consumivel','stackable':True}
  self.db['users'].docs[0]['inventory']={'potion':{'base_id':'potion','quantity':10,'upgrade_level':0,'enchantments':{}}}
  l=self.sell(item_id='potion',qty=3,price=150);self.buy(l)
  self.assertEqual(self.db['users'].docs[1]['inventory']['potion']['quantity'],3)
  self.assertEqual(self.db['users'].docs[1]['gold'],850)
  self.assertEqual(self.db['users'].docs[0]['gold'],145)
 def test_exact_total_and_tax(self):
  l=self.sell();self.assertEqual(self.m.listing_total(l),100);self.buy(l)
  self.assertEqual(self.db['users'].find_one({'_id':self.buyer})['gold'],900)
  self.assertEqual(self.db['users'].find_one({'_id':self.seller})['gold'],100)
 def test_small_total(self):
  l=self.sell(price=5,qty=10);self.buy(l);self.assertEqual(self.db['users'].docs[1]['gold'],995)
 def test_refund_both_inventory_formats(self):
  for value in [20,{'base_id':'herb','quantity':20},{'base_id':'herb','qty':20}]:
   self.db['users'].docs[0]['inventory']={'herb':copy.deepcopy(value)}
   l=self.sell(qty=5);self.cancel(l)
   self.assertEqual(self.m._quantity(self.db['users'].docs[0]['inventory']['herb']),20)
 def test_no_duplicate_cancel_or_purchase(self):
  l=self.sell();self.cancel(l);before=copy.deepcopy(self.db.data)
  for op in [self.cancel,self.buy]:
   with self.assertRaises(self.m.ListingInactive):op(l)
   self.assertEqual(self.db.data,before)
 def test_purchase_wins_cancel(self):
  l=self.sell();self.buy(l);before=copy.deepcopy(self.db.data)
  with self.assertRaises(self.m.ListingInactive):self.cancel(l)
  self.assertEqual(before,self.db.data)
 def test_failed_create_rolls_back(self):
  for step in [1,2,3]:
   before=copy.deepcopy(self.db.data);self.db.n=0;self.db.fail=step
   with self.assertRaises(RuntimeError):self.sell()
   self.assertEqual(before,self.db.data)
 def test_failed_purchase_rolls_back(self):
  l=self.sell()
  for step in [1,2,3]:
   before=copy.deepcopy(self.db.data);self.db.n=0;self.db.fail=step
   with self.assertRaises(RuntimeError):self.buy(l)
   self.assertEqual(before,self.db.data)
 def test_failed_cancel_rolls_back(self):
  l=self.sell()
  for step in [1,2]:
   before=copy.deepcopy(self.db.data);self.db.n=0;self.db.fail=step
   with self.assertRaises(RuntimeError):self.cancel(l)
   self.assertEqual(before,self.db.data)
 def test_validation_has_no_effect(self):
  for args in [{'price':0},{'price':'1.5'},{'qty':21},{'currency':'unknown'},{'price':True}]:
   before=copy.deepcopy(self.db.data)
   with self.assertRaises(self.m.MarketError):self.sell(**args)
   self.assertEqual(before,self.db.data)
 def test_blocked_catalog(self):
  for base in ['xp','evolution']:
   self.db['users'].docs[0]['inventory'][base]=1;before=copy.deepcopy(self.db.data)
   with self.assertRaises(self.m.InvalidListing):self.sell(item_id=base,qty=1)
   self.assertEqual(before,self.db.data)
 def test_unique_data_preserved(self):
  item={'base_id':'sword','upgrade_level':7,'rarity':'epico','durability':[20,50],'attributes':{'attack':90}}
  self.db['users'].docs[0]['inventory']['uuid']=copy.deepcopy(item)
  l=self.sell(item_id='uuid',qty=1);self.buy(l)
  self.assertIn(item,self.db['users'].docs[1]['inventory'].values())
 def test_insufficient_balance_and_permission(self):
  l=self.sell(price=1001);before=copy.deepcopy(self.db.data)
  with self.assertRaises(self.m.InvalidPurchase):self.buy(l)
  with self.assertRaises(self.m.PermissionDenied):self.cancel(l,self.buyer)
  self.assertEqual(before,self.db.data)
 def test_legacy_price_and_partial(self):
  l=self.sell();stored=self.db['market_listings'].docs[0];stored.pop('total_price');stored['unit_price']=10
  self.buy(l,quantity=1);self.assertEqual(self.m.listing_total(self.m.get_listing(l['_id'])),20)
  self.cancel(l);self.assertEqual(self.db['users'].docs[0]['inventory']['herb'],19)
 def test_transaction_callback_retry(self):
  l=self.sell();self.db.retry=True;self.buy(l)
  self.assertEqual(self.db['users'].docs[1]['gold'],900)
  self.assertEqual(self.db['users'].docs[1]['inventory']['herb']['quantity'],3)
 def test_gems_and_self_purchase(self):
  l=self.sell(currency='gemas',price=101)
  with self.assertRaises(self.m.InvalidPurchase):
   asyncio.run(self.m.purchase_listing(buyer_id=str(self.seller),listing_id=l['_id']))
  self.buy(l)
  self.assertEqual(self.db['users'].docs[1]['gems'],899)
  self.assertEqual(self.db['users'].docs[0]['gems'],91)
 def test_missing_seller_does_not_charge(self):
  l=self.sell();self.db['users'].docs.pop(0);before=copy.deepcopy(self.db.data)
  with self.assertRaises(self.m.MarketError):self.buy(l)
  self.assertEqual(before,self.db.data)
 def test_listing_api_details(self):
  import ast
  item={'base_id':'sword','upgrade_level':7,'rarity':'epico','durability':[20,50],'attributes':{'attack':90}}
  self.db['users'].docs[0]['inventory']['uuid']=copy.deepcopy(item)
  listing=self.sell(item_id='uuid',qty=1)
  fake_manager=types.SimpleNamespace(list_active=lambda **kw:[copy.deepcopy(listing)],listing_total=self.m.listing_total)
  tree=ast.parse((ROOT/'modules/webapp_api.py').read_text(encoding='utf-8-sig'))
  names={'api_listar_mercado','_formatar_stats_item_para_front','_json_seguro_mongo'}
  nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
  for n in nodes:n.decorator_list=[]
  ns={'copy':copy,'ObjectId':ObjectId,'market_manager':fake_manager,'items_data':types.SimpleNamespace(ITEMS_DATA={'sword':{'type':'weapon','display_name':'Espada','description':'Teste'}}),'jsonify':lambda x:x}
  exec(compile(ast.Module(body=nodes,type_ignores=[]),'<api-list>','exec'),ns)
  response=ns['api_listar_mercado']();card=response['ouro'][0]
  self.assertEqual(card['quantidade'],1);self.assertEqual(card['preco'],100)
  self.assertEqual(card['item_details']['raridade'],'epico')
  self.assertEqual(card['item_details']['refino'],7)
  self.assertEqual(card['item_details']['descricao'],'Teste')
  self.assertEqual(card['item_details']['durability'],[20,50])
if __name__=='__main__': unittest.main(verbosity=2)
