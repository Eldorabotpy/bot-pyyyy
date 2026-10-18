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
from werkzeug.security import generate_password_hash, check_password_hash

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('portal_test',root/'modules/portal_auth.py')
auth=importlib.util.module_from_spec(spec);spec.loader.exec_module(auth)

class Store:
    def __init__(self): self.docs=[]
    def matches(self,doc,query):
        for key,value in query.items():
            if key=='$or':
                if not any(self.matches(doc,q) for q in value): return False
            elif key=='$and':
                if not all(self.matches(doc,q) for q in value): return False
            elif isinstance(value,dict) and '$exists' in value:
                if (key in doc)!=value['$exists']: return False
            elif isinstance(value,dict) and '$ne' in value:
                if doc.get(key)==value['$ne']: return False
            elif doc.get(key)!=value: return False
        return True
    def find_one(self,q): return next((copy.deepcopy(d) for d in self.docs if self.matches(d,q)),None)
    def find(self,q): return [copy.deepcopy(d) for d in self.docs if self.matches(d,q)]
    def insert_one(self,d): self.docs.append(copy.deepcopy(d))
    def update_one(self,q,u):
        for d in self.docs:
            if self.matches(d,q):
                d.update(u.get('$set',{}))
                for key in u.get('$unset',{}): d.pop(key,None)
                for key,amount in u.get('$inc',{}).items(): d[key]=d.get(key,0)+amount
                return SimpleNamespace(matched_count=1)
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
auth.verify_google=lambda token: {'one':'google-1','two':'google-2','three':'google-3'}[token]
result=client.post('/api/auth/google',headers=headers,json={'credential':'one'})
assert result.status_code==409 and 'Não crie outra conta para recuperar seus personagens.' in result.json['erro']
result=client.post('/api/auth/google',headers=headers,json={'credential':'one','mode':'create'})
assert result.status_code==200 and len(accounts.docs)==1
master_id=accounts.docs[0]['_id']
headers={'X-Eldora-CSRF':result.json['csrf']}
# The same Google subject can never create a second master account.
result=client.post('/api/auth/google',headers=headers,json={'credential':'one','mode':'create'})
assert result.status_code==409 and len(accounts.docs)==1
result=client.post('/api/auth/google',headers=headers,json={'credential':'one','mode':'login'})
assert result.status_code==200 and accounts.docs[0]['_id']==master_id and len(accounts.docs)==1
assert 'password_hash' not in accounts.docs[0]
account=accounts.docs[0];oid=ObjectId();players.docs=[{'_id':oid,'conta_mestre':account['username'],'character_name':'Existente'}]
csrf=result.json['csrf'];headers={'X-Eldora-CSRF':csrf}
assert client.post('/api/auth/select',headers=headers,json={'character_id':str(ObjectId())}).status_code==403
assert client.post('/api/auth/select',headers=headers,json={'character_id':str(oid)}).status_code==200
assert client.get('/api/auth/status').json['selected_character_id']==str(oid)
revoked_accounts=[]
app.config['REVOKE_ACCOUNT_SOCKETS']=lambda account_id: revoked_accounts.append(str(account_id))
second_oid=ObjectId()
players.docs.append({'_id':second_oid,'conta_mestre':account['username'],'character_name':'Segundo'})
assert client.post('/api/auth/select',headers=headers,json={'character_id':str(second_oid)}).status_code==200
assert revoked_accounts==[str(account['_id'])]
assert client.post('/api/auth/select',headers=headers,json={'character_id':str(oid)}).status_code==200
assert revoked_accounts==[str(account['_id']),str(account['_id'])]
with app.test_request_context('/api/auth/google'):
    from flask import session
    session['portal_account']=str(account['_id'])
    auth.start_session({'_id':ObjectId(),'session_version':0},auth_method='google')
assert revoked_accounts[-1]==str(account['_id'])
with app.test_request_context('/api/player-check'):
    from flask import session
    session['portal_account']=str(account['_id']);session['portal_session_version']=0;session['portal_character']=str(oid)
    assert auth.require_player_identity(str(oid))['_id']==oid
    assert players.docs[0]['conta_mestre_id']==account['_id']
    try: auth.require_player_identity(str(ObjectId()))
    except auth.PlayerSessionError: pass
    else: raise AssertionError('ID de outro personagem aceito')
# Conta Google pode ganhar senha alternativa sem criar outra conta.
result=client.post('/api/auth/credentials',headers=headers,json={'username':'conta_recuperavel','password':'backup-password-789'})
assert result.status_code==200 and result.json['has_password']
assert accounts.docs[0]['login_alias']=='conta_recuperavel'
assert check_password_hash(accounts.docs[0]['password_hash'],'backup-password-789')
headers={'X-Eldora-CSRF':result.json['csrf']}
# Vincular mantém a mesma conta, personagem e inventário; não confia no ID legado.
auth.verify_telegram=lambda raw,token:42
result=client.post('/api/auth/telegram',headers=headers,json={'mode':'link','init_data':'verified-by-stub'})
assert result.status_code==200 and result.json['personagens'][0]['id']==str(oid)
assert len(accounts.docs)==1 and accounts.docs[0]['telegram_verified_id']==42
headers={'X-Eldora-CSRF':result.json['csrf']}
assert client.post('/api/auth/google',headers=headers,json={'mode':'link','credential':'two'}).status_code==400
assert client.post('/api/auth/logout',headers=headers,json={}).status_code==200
assert revoked_accounts[-1]==str(account['_id'])
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
sys.modules['modules.portal_auth']=auth
node=next(n for n in ast.parse((root/'modules/webapp_api.py').read_text(encoding='utf-8-sig')).body if isinstance(n,ast.FunctionDef) and n.name=='api_login_conta')
node.decorator_list=[]
scope={'request':request,'jsonify':jsonify,'contas_collection':accounts,'users_collection':players,'check_password_hash':check_password_hash}
exec(compile(ast.Module(body=[node],type_ignores=[]),'legacy-login','exec'),scope)
accounts.docs[0]['password_hash']=generate_password_hash('legacy-password')
with app.test_request_context('/api/portal/login',method='POST',json={'username':accounts.docs[0]['username'],'password':'legacy-password'},headers={'X-Eldora-CSRF':'test-csrf'}):
    from flask import session
    session['portal_csrf']='test-csrf'
    response=scope['api_login_conta']()
    assert response.json['sucesso'] is True
    assert session['portal_auth_method']=='password'
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
# Senha pode ser alterada após reautenticação recente no provedor conectado.
with client.session_transaction() as sess:
    sess['portal_account']=str(accounts.docs[0]['_id']);sess['portal_session_version']=accounts.docs[0].get('session_version',0)
    sess['portal_csrf']='change-password';sess['portal_login_at']=__import__('time').time();sess['portal_auth_method']='google'
result=client.post('/api/auth/credentials',headers={'X-Eldora-CSRF':'change-password'},json={'username':'conta_recuperavel','password':'backup-password-new'})
assert result.status_code==200 and check_password_hash(accounts.docs[0]['password_hash'],'backup-password-new')
# A senha é alternativa válida mesmo quando o Google segue vinculado.
with app.test_request_context('/api/portal/login',method='POST',json={'username':'conta_recuperavel','password':'backup-password-new','remember':False},headers={'X-Eldora-CSRF':'test-csrf'}):
    session['portal_csrf']='test-csrf'
    response=scope['api_login_conta']()
    assert response.json['sucesso'] is True and session['portal_auth_method']=='password'
# Troca Google exige uma alternativa recente e não rouba identidade de outra conta.
with client.session_transaction() as sess:
    sess['portal_account']=str(accounts.docs[0]['_id']);sess['portal_session_version']=accounts.docs[0].get('session_version',0)
    sess['portal_csrf']='replace-google';sess['portal_login_at']=__import__('time').time();sess['portal_auth_method']='password'
result=client.post('/api/auth/google',headers={'X-Eldora-CSRF':'replace-google'},json={'mode':'replace','credential':'two'})
assert result.status_code==400 and accounts.docs[0]['google_sub']=='google-1'
result=client.post('/api/auth/google',headers={'X-Eldora-CSRF':result.json.get('csrf','replace-google')},json={'mode':'replace','credential':'three'})
assert result.status_code==200 and accounts.docs[0]['google_sub']=='google-3'
# Remover um provedor exige outro método ativo e invalida sessões antigas.
with client.session_transaction() as sess:
    sess['portal_account']=str(accounts.docs[0]['_id']);sess['portal_session_version']=accounts.docs[0].get('session_version',0)
    sess['portal_csrf']='unlink-google';sess['portal_login_at']=__import__('time').time();sess['portal_auth_method']='password'
result=client.post('/api/auth/unlink/google',headers={'X-Eldora-CSRF':'unlink-google'},json={})
assert result.status_code==200 and not result.json['google_linked']
stale_client=app.test_client()
with stale_client.session_transaction() as sess:
    sess['portal_account']=str(accounts.docs[0]['_id']);sess['portal_session_version']=0;sess['portal_csrf']='stale'
assert stale_client.get('/api/auth/status').json['authenticated'] is False
# O último método de entrada não pode ser removido.
with client.session_transaction() as sess:
    sess['portal_account']=str(accounts.docs[1]['_id']);sess['portal_session_version']=0
    sess['portal_csrf']='last-login';sess['portal_login_at']=__import__('time').time();sess['portal_auth_method']='google'
result=client.post('/api/auth/unlink/google',headers={'X-Eldora-CSRF':'last-login'},json={})
assert result.status_code==403 and accounts.docs[1].get('google_sub')=='google-2'
# Regressão: seis caracteres e Telegram de outra conta não bloqueiam login por senha.
old={'_id':ObjectId(),'username':'seis_digitos','password_hash':generate_password_hash('123456')}
accounts.docs.append(old)
for remember in (False,True):
    with app.test_request_context('/api/portal/login',method='POST',json={'username':'seis_digitos','password':'123456','remember':remember,'init_data':'irrelevante-para-senha'},headers={'X-Eldora-CSRF':'test-csrf'}):
        session['portal_csrf']='test-csrf'
        response=scope['api_login_conta']()
        assert response.json['sucesso'] is True and session.permanent==remember
assert 'telegram_verified_id' not in old
print('OK: assinatura Telegram, expiração, CSRF, cadastro, sessão, vínculo, identidade duplicada, propriedade do personagem e saída.')
