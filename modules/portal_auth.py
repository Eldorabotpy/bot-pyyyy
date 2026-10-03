"""Identidades verificadas e sessão do portal. Não confia em IDs do navegador."""
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timezone
from urllib.parse import parse_qsl
from bson import ObjectId
from flask import Blueprint, current_app, jsonify, request, session
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

portal_auth_bp = Blueprint('portal_auth', __name__)

# Identificador público do aplicativo Web; não é um segredo nem uma senha.
DEFAULT_GOOGLE_CLIENT_ID = '16919820429-j7oc4nsbu759h83qkl9i9ngj1vengsvt.apps.googleusercontent.com'


def google_client_id():
    # Uma variável vazia permite desativar o provedor no ambiente.
    return os.getenv('GOOGLE_CLIENT_ID', DEFAULT_GOOGLE_CLIENT_ID).strip()



def accounts():
    from modules.player.core import db
    col = db['contas_mestre']
    col.create_index('google_sub', unique=True, partialFilterExpression={'google_sub': {'$type': 'string'}})
    col.create_index('telegram_verified_id', unique=True, partialFilterExpression={'telegram_verified_id': {'$type': 'number'}})
    return col


def current_account():
    value = session.get('portal_account')
    return accounts().find_one({'_id': ObjectId(value)}) if ObjectId.is_valid(str(value)) else None


def require_csrf():
    token = session.get('portal_csrf', '')
    if not token or not hmac.compare_digest(token, request.headers.get('X-Eldora-CSRF', '')):
        raise ValueError('Sessão expirada. Atualize a página e tente novamente.')


def limit_attempts():
    from modules.player.core import db
    bucket = int(time.time()) // 900
    digest = hmac.new(str(current_app.secret_key).encode(), (request.remote_addr or 'unknown').encode(), hashlib.sha256).hexdigest()
    col = db['portal_login_attempts']
    col.create_index('expires_at', expireAfterSeconds=0)
    key = f'{digest}:{bucket}'
    doc = col.find_one_and_update({'_id': key}, {'$inc': {'count': 1}, '$set': {'expires_at': datetime.fromtimestamp((bucket+2)*900, timezone.utc)}}, upsert=True, return_document=ReturnDocument.AFTER)
    if doc['count'] > 30:
        raise ValueError('Muitas tentativas. Aguarde alguns minutos para tentar novamente.')


def start_session(account):
    session.pop('portal_character', None)
    session['portal_account'] = str(account['_id'])
    session['portal_csrf'] = secrets.token_urlsafe(32)
    session['portal_login_at'] = time.time()
    session.permanent = True


def account_payload(account):
    from modules.player.core import users_collection
    characters = []
    for p in users_collection.find({'conta_mestre': account['username']}):
        characters.append({'id': str(p['_id']), 'nome': p.get('character_name','Herói'), 'genero': p.get('gender','masculino'), 'level': p.get('level',1), 'classe': str(p.get('class','aventureiro')).capitalize(), 'avatar_customizado': p.get('avatar_customizado','padrao')})
    return {'sucesso': True, 'username': account['username'], 'personagens': characters, 'csrf': session['portal_csrf'], 'google_linked': bool(account.get('google_sub')), 'telegram_linked': bool(account.get('telegram_verified_id'))}


def verify_telegram(raw, token, now=None):
    pairs = parse_qsl(raw, keep_blank_values=True)
    data = dict(pairs)
    if len(pairs) != len(data):
        raise ValueError('Dados Telegram inválidos.')
    signature = data.pop('hash', '')
    secret = hmac.new(b'WebAppData', token.encode(), hashlib.sha256).digest()
    check = '\n'.join(f'{key}={value}' for key,value in sorted(data.items()))
    expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not signature or not hmac.compare_digest(signature, expected):
        raise ValueError('Abra o jogo pelo bot para validar o Telegram.')
    age = (time.time() if now is None else now) - int(data.get('auth_date', 0))
    if age < -30 or age > 600:
        raise ValueError('Validação Telegram expirada. Reabra o jogo pelo bot.')
    user = json.loads(data.get('user', '{}'))
    if type(user.get('id')) is not int or user['id'] <= 0:
        raise ValueError('Identidade Telegram inválida.')
    return user['id']


def verify_google(credential):
    client = google_client_id()
    if not client:
        raise ValueError('Login Google ainda não configurado pelo administrador.')
    from google.oauth2 import id_token
    from google.auth.transport.requests import Request
    claims = id_token.verify_oauth2_token(credential, Request(), client)
    if claims.get('iss') not in ('accounts.google.com', 'https://accounts.google.com') or not claims.get('sub') or claims.get('email_verified') is not True:
        raise ValueError('Não foi possível validar esta conta Google.')
    return claims['sub']


@portal_auth_bp.get('/api/auth/status')
def auth_status():
    session.setdefault('portal_csrf', secrets.token_urlsafe(32))
    account = current_account()
    payload = account_payload(account) if account else {'sucesso': True, 'csrf': session['portal_csrf']}
    payload.update({'authenticated': bool(account), 'google_client_id': google_client_id()})
    response = jsonify(payload)
    response.headers['Cache-Control'] = 'no-store'
    return response


@portal_auth_bp.post('/api/auth/<provider>')
def provider_login(provider):
    if provider not in ('google','telegram'):
        return jsonify(erro='Provedor inválido.'), 404
    try:
        require_csrf()
        limit_attempts()
        data = request.get_json(silent=True) or {}
        mode = data.get('mode', 'login')
        if mode not in ('login','create','link'):
            raise ValueError('Ação inválida.')
        account = current_account() if mode == 'link' else None
        if mode == 'link' and (not account or time.time()-session.get('portal_login_at',0)>600):
            return jsonify(erro='Entre novamente na conta existente antes de vincular.'), 401
        if provider == 'google':
            identity = verify_google(str(data.get('credential','')))
            field = 'google_sub'
        else:
            from config import TELEGRAM_TOKEN
            identity = verify_telegram(str(data.get('init_data','')), TELEGRAM_TOKEN)
            field = 'telegram_verified_id'
        col = accounts()
        owner = col.find_one({field: identity})
        if mode == 'link':
            if owner and owner['_id'] != account['_id']:
                raise ValueError('Esta identidade já está vinculada a outra conta. Nenhum personagem foi alterado.')
            if account.get(field) not in (None, identity):
                raise ValueError('Esta conta já possui outra identidade vinculada.')
            result = col.update_one({'_id': account['_id'], '$or': [{field: {'$exists': False}}, {field: identity}]}, {'$set': {field: identity}})
            if result.matched_count != 1:
                raise ValueError('Vinculação alterada. Entre novamente.')
            account = col.find_one({'_id': account['_id']})
        elif owner:
            account = owner
        elif mode == 'create':
            oid = ObjectId()
            account = {'_id': oid, 'username': 'eldora_'+str(oid), field: identity, 'criado_em': datetime.now(timezone.utc)}
            col.insert_one(account)
        else:
            return jsonify(erro='Identidade ainda não vinculada. Entre na conta antiga e vincule, ou escolha Criar nova conta.'), 409
        start_session(account)
        return jsonify(account_payload(account))
    except ImportError:
        return jsonify(erro='Dependência de login não instalada no servidor.'), 503
    except DuplicateKeyError:
        return jsonify(erro='Identidade já vinculada. Entre novamente; não foi criada outra vinculação.'), 409
    except (ValueError, TypeError, KeyError):
        # Detalhes de tokens ou credenciais nunca são devolvidos ao navegador.
        return jsonify(erro='Não foi possível validar ou vincular. Entre novamente; confira se a identidade já pertence a outra conta.'), 400


@portal_auth_bp.post('/api/auth/select')
def select_character():
    try:
        require_csrf()
        account = current_account()
        if not account:
            return jsonify(erro='Entre na sua conta.'), 401
        from modules.player.core import users_collection
        value = (request.get_json(silent=True) or {}).get('character_id')
        if not ObjectId.is_valid(str(value)) or not users_collection.find_one({'_id':ObjectId(value),'conta_mestre':account['username']}):
            return jsonify(erro='Este personagem não pertence à sua conta.'), 403
        session['portal_character'] = str(value)
        return jsonify(sucesso=True)
    except ValueError as exc:
        return jsonify(erro=str(exc)), 403


@portal_auth_bp.post('/api/auth/logout')
def logout():
    try:
        require_csrf()
    except ValueError as exc:
        return jsonify(erro=str(exc)), 403
    for key in list(session):
        if key.startswith('portal_'):
            session.pop(key, None)
    return jsonify(sucesso=True)
