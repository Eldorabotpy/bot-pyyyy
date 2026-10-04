"""Testes isolados: nunca importa conexão Mongo nem usa contas reais."""
import copy
import hashlib
import hmac
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode
from bson import ObjectId
from flask import Flask

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('portal_test',root/'modules/portal_auth.py')
auth=importlib.util.module_from_spec(spec);spec.loader.exec_module(auth)

class Store:
    def __init__(self): self.docs=[]
    def matches(self,doc,query):
        for key,value in query.items():
            if key=='$or':
                if not any(self.matches(doc,q) for q in value): return False
            elif isinstance(value,dict) and '$exists' in value:
                if (key in doc)!=value['$exists']: return False
            elif doc.get(key)!=value: return False
        return True
    def find_one(self,q): return next((copy.deepcopy(d) for d in self.docs if self.matches(d,q)),None)
    def find(self,q): return [copy.deepcopy(d) for d in self.docs if self.matches(d,q)]
    def insert_one(self,d): self.docs.append(copy.deepcopy(d))
    def update_one(self,q,u):
        for d in self.docs:
            if self.matches(d,q):
                d.update(u['$set']);return SimpleNamespace(matched_count=1)
        return SimpleNamespace(matched_count=0)

accounts=Store();players=Store()
auth.accounts=lambda:accounts
auth.limit_attempts=lambda:None
sys.modules['modules.player.core']=SimpleNamespace(users_collection=players)
sys.modules['config']=SimpleNamespace(TELEGRAM_TOKEN='test-only-token')
app=Flask(__name__);app.secret_key='isolated-test-secret';app.register_blueprint(auth.portal_auth_bp)
client=app.test_client()

def signed(tid,date=1000):
    data={'auth_date':str(date),'user':json.dumps({'id':tid})}
    key=hmac.new(b'WebAppData',b'test-only-token',hashlib.sha256).digest()
    data['hash']=hmac.new(key,'\n'.join(f'{k}={v}' for k,v in sorted(data.items())).encode(),hashlib.sha256).hexdigest()
    return urlencode(data)
assert auth.verify_telegram(signed(42),'test-only-token',1001)==42
for raw,now in [(signed(42)+'&user=forged',1001),(signed(42).replace('1000','1001'),1001),(signed(42),1700)]:
    try: auth.verify_telegram(raw,'test-only-token',now)
    except ValueError: pass
    else: raise AssertionError('Telegram falsificado/expirado aceito')

assert client.post('/api/auth/google',json={'credential':'fake'}).status_code==400
csrf=client.get('/api/auth/status').json['csrf']
headers={'X-Eldora-CSRF':csrf}
auth.verify_google=lambda token: {'one':'google-1','two':'google-2'}[token]
assert client.post('/api/auth/google',headers=headers,json={'credential':'one'}).status_code==409
result=client.post('/api/auth/google',headers=headers,json={'credential':'one','mode':'create'})
assert result.status_code==200 and len(accounts.docs)==1
assert 'password_hash' not in accounts.docs[0]
account=accounts.docs[0];oid=ObjectId();players.docs=[{'_id':oid,'conta_mestre':account['username'],'character_name':'Existente'}]
csrf=result.json['csrf'];headers={'X-Eldora-CSRF':csrf}
assert client.post('/api/auth/select',headers=headers,json={'character_id':str(ObjectId())}).status_code==403
assert client.post('/api/auth/select',headers=headers,json={'character_id':str(oid)}).status_code==200
# Vincular mantém a mesma conta, personagem e inventário; não confia no ID legado.
auth.verify_telegram=lambda raw,token:42
result=client.post('/api/auth/telegram',headers=headers,json={'mode':'link','init_data':'verified-by-stub'})
assert result.status_code==200 and result.json['personagens'][0]['id']==str(oid)
assert len(accounts.docs)==1 and accounts.docs[0]['telegram_verified_id']==42
headers={'X-Eldora-CSRF':result.json['csrf']}
assert client.post('/api/auth/google',headers=headers,json={'mode':'link','credential':'two'}).status_code==400
assert client.post('/api/auth/logout',headers=headers,json={}).status_code==200
assert client.get('/api/auth/status').json['authenticated'] is False
csrf=client.get('/api/auth/status').json['csrf'];headers={'X-Eldora-CSRF':csrf}
assert client.post('/api/auth/google',headers=headers,json={'mode':'link','credential':'two'}).status_code==401
result=client.post('/api/auth/google',headers=headers,json={'mode':'create','credential':'two'})
assert result.status_code==200
headers={'X-Eldora-CSRF':result.json['csrf']}
assert client.post('/api/auth/telegram',headers=headers,json={'mode':'link','init_data':'verified-by-stub'}).status_code==400
assert len(accounts.docs)==2
# Exercita o login legado real sem importar o módulo conectado ao banco.
import ast
from flask import request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
sys.modules['modules.portal_auth']=auth
node=next(n for n in ast.parse((root/'modules/webapp_api.py').read_text(encoding='utf-8-sig')).body if isinstance(n,ast.FunctionDef) and n.name=='api_login_conta')
node.decorator_list=[]
scope={'request':request,'jsonify':jsonify,'contas_collection':accounts,'users_collection':players,'check_password_hash':check_password_hash}
exec(compile(ast.Module(body=[node],type_ignores=[]),'legacy-login','exec'),scope)
accounts.docs[0]['password_hash']=generate_password_hash('legacy-password')
with app.test_request_context('/api/portal/login',method='POST',json={'username':accounts.docs[0]['username'],'password':'legacy-password'},headers={'X-Eldora-CSRF':'test-csrf'}):
    from flask import session
    session['portal_csrf']='test-csrf'
    response,code=scope['api_login_conta']()
    assert code==403 and 'Google' in response.json['erro']
# Cadastro Telegram exige credenciais; entrada por senha funciona sem Telegram.
auth.verify_telegram=lambda raw,token:84
csrf=client.get('/api/auth/status').json['csrf'];headers={'X-Eldora-CSRF':csrf}
client.post('/api/auth/logout',headers=headers,json={})
csrf=client.get('/api/auth/status').json['csrf'];headers={'X-Eldora-CSRF':csrf}
assert client.post('/api/auth/telegram',headers=headers,json={'mode':'create','init_data':'verified'}).status_code==400
result=client.post('/api/auth/telegram',headers=headers,json={'mode':'create','init_data':'verified','username':'novo_telegram','password':'test-password-789'})
assert result.status_code==200 and result.json['has_password']
assert accounts.docs[-1]['login_alias']=='novo_telegram'
assert check_password_hash(accounts.docs[-1]['password_hash'],'test-password-789')
with app.test_request_context('/api/portal/login',method='POST',json={'username':'novo_telegram','password':'test-password-789'},headers={'X-Eldora-CSRF':'test-csrf'}):
    session['portal_csrf']='test-csrf'
    response=scope['api_login_conta']()
    assert response.json['sucesso'] is True
# Reparo de conta Telegram antiga não renomeia chave usada pelos personagens.
legacy={'_id':ObjectId(),'username':'eldora_legado','telegram_verified_id':99}
accounts.docs.append(legacy)
with client.session_transaction() as sess:
    sess['portal_account']=str(legacy['_id']);sess['portal_csrf']='repair'
auth.verify_telegram=lambda raw,token:99
result=client.post('/api/auth/telegram-credentials',headers={'X-Eldora-CSRF':'repair'},json={'username':'acesso_legado','password':'test-password-789','init_data':'verified'})
assert result.status_code==200 and accounts.docs[-1]['username']=='eldora_legado'
assert accounts.docs[-1]['login_alias']=='acesso_legado'
print('OK: assinatura Telegram, expiração, CSRF, cadastro, sessão, vínculo, identidade duplicada, propriedade do personagem e saída.')
