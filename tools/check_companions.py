"""Regressão isolada dos companheiros, sem importar módulos de conexão ao banco.
Execute: venv/Scripts/python.exe tools/check_companions.py
"""
import copy
import importlib.util
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from bson import ObjectId

spec = importlib.util.spec_from_file_location('companions_tested', Path(__file__).resolve().parents[1] / 'modules/companions.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


class MemoryCollection:
    def __init__(self):
        self.docs = {}
        self.lock = threading.Lock()
    def find_one(self, query):
        with self.lock:
            return copy.deepcopy(self.docs.get(query['_id']))
    def update_one(self, query, update, upsert=False):
        with self.lock:
            key = query['_id']
            if key not in self.docs and upsert:
                self.docs[key] = {'_id': key, **copy.deepcopy(update['$setOnInsert'])}
                return SimpleNamespace(modified_count=0)
            doc = self.docs.get(key)
            if not doc or any(doc.get(k) != v for k, v in query.items()):
                return SimpleNamespace(modified_count=0)
            if '$set' in update:
                doc.update(copy.deepcopy(update['$set']))
                return SimpleNamespace(modified_count=1)
            return SimpleNamespace(modified_count=0)


def rejected(fn):
    try:
        fn()
    except ValueError:
        return
    raise AssertionError('Ação inválida foi aceita')


def run():
    locked = c.normalize(c.initial())
    locked['pets']['slime']={'xp':15000,'bond':1500,'stage':0,'specialty':None}
    locked['essences']['slime']=999
    before_locked=copy.deepcopy(locked)
    rejected(lambda:c.action({},locked,'evolve','slime'))
    assert locked==before_locked
    rejected(lambda:c.action({'bestiario':{'morcego_das_minas':50}},locked,'claim','morcego'))
    assert c.view({},locked)['pets']['slime']['next_released'] is False
    # Ovo de família antiga permanece utilizável mesmo com família futura bloqueada.
    locked['eggs']=['morcego'];locked['incubators']=1
    c.action({},locked,'incubate','morcego')
    locked['incubation']['distance']=c.HATCH_DISTANCE
    c.action({},locked,'hatch','morcego')
    assert 'morcego' in locked['pets']
    c.RELEASED_PET_CHAPTER=4 # Simula liberação editorial para regressão das evoluções.
    store = MemoryCollection()
    c.collection = lambda: store
    c.premium_player = lambda uid: {}
    uid = str(ObjectId())
    player = {'bestiario': {'slime_verde': 50, 'lobo_magro': 50, 'morcego_das_minas': 50}}
    def act(action, family=None, specialty=None):
        return c.mutate(uid, lambda s: c.action(player, s, action, family, specialty))
    rejected(lambda: c.action({'bestiario':{}}, c.initial(), 'incubator'))
    act('incubator')
    rejected(lambda: act('incubator'))
    def claim(_):
        try:
            act('claim','slime')
            return 1
        except ValueError:
            return 0
    with ThreadPoolExecutor(8) as pool:
        assert sum(pool.map(claim, range(8))) == 1
    assert c.load(uid)['eggs'] == ['slime']
    act('claim','lobo')
    act('incubate','slime')
    rejected(lambda: act('incubate','lobo'))
    rejected(lambda: act('hatch','slime'))
    c.record_distance(uid, c.HATCH_DISTANCE/2)
    saved = copy.deepcopy(store.docs)
    store.docs = copy.deepcopy(saved) # Simula reconstrução do estado persistido.
    assert c.load(uid)['incubation']['distance'] == c.HATCH_DISTANCE/2
    c.record_distance(uid, c.HATCH_DISTANCE*2)
    assert c.load(uid)['incubation']['distance'] == c.HATCH_DISTANCE
    act('hatch','slime')
    assert c.load(uid)['active'] == 'slime'
    rejected(lambda: act('hatch','slime'))
    for _ in range(225):
        c.record_victory(uid,'slime_verde')
    pet=c.load(uid)['pets']['slime']
    assert c.level(pet)[0]==10 and pet['bond']==225
    act('evolve','slime')
    assert c.load(uid)['essences']['slime']==200
    assert c.bonus(c.load(uid))=={'defense':5}
    rejected(lambda: act('evolve','slime','vital'))
    for _ in range(1275):
        c.record_victory(uid,'slime_verde')
    rejected(lambda: act('evolve','slime','invalido'))
    act('evolve','slime','vital')
    assert c.bonus(c.load(uid))=={'max_hp':30}
    rejected(lambda: act('evolve','slime','guardiao'))
    act('unequip')
    before=c.load(uid)
    c.record_victory(uid,'slime_verde')
    assert c.load(uid)==before and c.bonus(before)=={}
    rejected(lambda: act('incubate','lobo'))
    c.deliver_supplies(uid, {'companion_incubator_grants':[{'id':'purchase-1','quantity':1}]})
    c.deliver_supplies(uid, {'companion_incubator_grants':[{'id':'purchase-1','quantity':1}]})
    assert c.load(uid)['incubators']==1
    act('incubate','lobo')
    assert c.load(uid)['incubators']==0
    c.record_distance(uid,c.HATCH_DISTANCE)
    act('hatch','lobo')
    assert c.load(uid)['active']=='lobo'
    c.record_victory(uid,'lobo_magro')
    assert c.load(uid)['pets']['slime']['bond']==1500
    assert c.load(uid)['pets']['lobo']['bond']==1
    sample,distance=c.movement_distance(None,'capital',0,0,1)
    assert distance==0
    sample,distance=c.movement_distance(sample,'capital',150,0,2)
    assert distance==150
    assert c.movement_distance(sample,'capital',150,0,3)[1]==0
    assert c.movement_distance(sample,'floresta',200,0,3)[1]==0
    assert c.movement_distance(sample,'capital',20000,0,3)[1]==0
    assert c.movement_distance(sample,'capital',float('nan'),0,3)[1]==0
    assert c.movement_distance(sample,'capital',160,0,20)[1]==0
    assert c.knowledge({'bestiario':{'ond1_slime_verde':999, 'slime_verde':50}})['slime']==50
    assert c.view(player,c.load(uid))['pets']['lobo']['level']==1
    # Conversão antiga não gera novas unidades a cada leitura e mantém o ovo.
    legacy = {'incubator':True, 'incubation':None}
    converted = c.normalize(legacy)
    assert converted['incubators']==1 and converted['incubator_claimed']
    assert c.normalize(converted)==converted
    legacy['incubation']={'family':'slime','distance':1234}
    converted=c.normalize(legacy)
    assert converted['incubators']==0 and converted['incubation']['distance']==1234
    from datetime import datetime, timedelta, timezone
    start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    premium_player = {'eldora_premium': {'activated_at': start, 'expires_at': start+timedelta(days=30)}}
    first = c.premium_cycle(premium_player, start)
    early = {'eldora_premium': {**premium_player['eldora_premium'], 'expires_at': start+timedelta(days=60)}}
    assert c.premium_cycle(early, start+timedelta(days=29))['id'] == first['id']
    second = c.premium_cycle(early, start+timedelta(days=30))
    assert second['id'] != first['id'] and second['kills'] == 0
    assert c.premium_cycle(premium_player, start+timedelta(days=30)) is None
    assert c.premium_cycle({'passe_batalha': {'is_premium': True, 'level': 80}}, start) is None
    premium=c.normalize(c.initial())
    premium['incubators']=4 # unidades legadas preservadas
    premium['premium_incubators']=['S1:20']
    for _ in range(1500):
        c.advance_premium(premium, first)
    c.advance_premium(premium, second)
    assert premium['premium_cycles'][second['id']]['kills']==1
    pending=c.premium_view({},premium,start+timedelta(days=61))
    assert not pending['active'] and len(pending['cycles'])==1
    for goal in (100,500,1500):
        receipt=f"{first['id']}:{goal}"
        c.action({},premium,'premium_incubator',receipt)
        rejected(lambda:c.action({},premium,'premium_incubator',receipt))
    assert premium['incubators']==7 and premium['premium_incubators']==['S1:20']
    rejected(lambda:c.action(player,premium,'premium_incubator','20'))
    rejected(lambda:c.action(player,premium,'premium_incubator',f"{second['id']}:100"))
    assert not c.premium_view({},premium)['cycles']
    # Ganho real sem pet equipado e resgate simultâneo na mesma revisão persistida.
    premium_uid=str(ObjectId())
    now=datetime.now(timezone.utc)
    c.premium_player=lambda uid: {'eldora_premium': {'activated_at':now-timedelta(days=1), 'expires_at':now+timedelta(days=29)}}
    for _ in range(100):
        c.record_victory(premium_uid,'goblin')
    saved=c.load(premium_uid)
    assert saved['active'] is None
    key=next(iter(saved['premium_cycles']))
    def claim_premium(_):
        try:
            c.mutate(premium_uid,lambda state:c.action({},state,'premium_incubator',f'{key}:100'))
            return 1
        except ValueError:
            return 0
    with ThreadPoolExecutor(8) as pool:
        assert sum(pool.map(claim_premium,range(8)))==1
    assert c.load(premium_uid)['incubators']==1
    c.premium_player=lambda uid: {}
    print('OK: ciclos Premium, renovação antecipada, expiração, metas, legado, abate sem pet e resgate concorrente.')

    # Exercita a rota Flask real via AST, sem importar o módulo conectado ao Mongo.
    import ast
    import sys
    from flask import Flask, request, jsonify
    root = Path(__file__).resolve().parents[1]
    tree = ast.parse((root/'modules/webapp_api.py').read_text(encoding='utf-8-sig'))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'api_companheiros')
    function.decorator_list = []
    original = sys.modules.get('modules')
    sys.modules['modules'] = SimpleNamespace(companions=c)
    api_scope = {'request': request, 'jsonify': jsonify, 'ObjectId': ObjectId,
                 'users_collection': SimpleNamespace(find_one=lambda q: player if str(q['_id']) == uid else None)}
    exec(compile(ast.Module(body=[function], type_ignores=[]), 'companions-route', 'exec'), api_scope)
    app = Flask(__name__)
    app.add_url_rule('/api/companheiros/<user_id>', view_func=api_scope['api_companheiros'], methods=['GET','POST'])
    client = app.test_client()
    assert client.get('/api/companheiros/'+uid).json['state']['active'] == 'lobo'
    assert client.post('/api/companheiros/'+uid, json={'action':'equip','family':'slime'}).json['state']['active'] == 'slime'
    assert client.post('/api/companheiros/'+uid, json={'action':'claim','family':'slime'}).status_code == 400
    assert client.get('/api/companheiros/invalid').status_code == 400
    assert client.get('/api/companheiros/'+str(ObjectId())).status_code == 404
    assert client.post('/api/companheiros/'+uid, json={'action':'incubate','family':{}}).status_code == 400
    if original is None:
        del sys.modules['modules']
    else:
        sys.modules['modules'] = original
    print('OK: conquista concorrente, ovo único, chocadeira, persistência, nascimento, XP, duas evoluções, custos, especialização, equipamento e limites de movimento.')

if __name__ == '__main__':
    run()
