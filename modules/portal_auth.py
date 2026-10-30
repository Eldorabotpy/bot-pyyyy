"""Identidades verificadas e sessão do portal. Não confia em IDs do navegador."""
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl
from bson import ObjectId
from flask import Blueprint, current_app, jsonify, request, session
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

portal_auth_bp = Blueprint('portal_auth', __name__)


class AccountInputError(ValueError):
    """Erro claro de validação que pode ser mostrado no formulário."""

# Identificador público do aplicativo Web; não é um segredo nem uma senha.
DEFAULT_GOOGLE_CLIENT_ID = '16919820429-j7oc4nsbu759h83qkl9i9ngj1vengsvt.apps.googleusercontent.com'


def google_client_id():
    # Uma variável vazia permite desativar o provedor no ambiente.
    return os.getenv('GOOGLE_CLIENT_ID', DEFAULT_GOOGLE_CLIENT_ID).strip()



def accounts():
    from modules.player.core import db
    col = db['contas_mestre']
    col.create_index('username', unique=True, partialFilterExpression={'username': {'$type': 'string'}})
    col.create_index('login_alias', unique=True, partialFilterExpression={'login_alias': {'$type': 'string'}})
    col.create_index('google_sub', unique=True, partialFilterExpression={'google_sub': {'$type': 'string'}})
    col.create_index('telegram_verified_id', unique=True, partialFilterExpression={'telegram_verified_id': {'$type': 'number'}})
    return col


def current_account():
    value = session.get('portal_account')
    if not ObjectId.is_valid(str(value)):
        return None
    account = accounts().find_one({'_id': ObjectId(value)})
    if not account:
        _clear_portal_session()
        return None
    try:
        expected_version = int(account.get('session_version', 0))
        session_version = int(session.get('portal_session_version', 0))
    except (TypeError, ValueError):
        _clear_portal_session()
        return None
    if session_version != expected_version:
        _clear_portal_session()
        return None
    return account


def _clear_portal_session():
    for key in list(session):
        if key.startswith('portal_'):
            session.pop(key, None)


def character_owner_query(account):
    """Accept new immutable ownership IDs and legacy username ownership."""
    account_id = account['_id']
    return {'$or': [
        {'conta_mestre_id': account_id},
        {'conta_mestre_id': str(account_id)},
        {'conta_mestre_id': {'$exists': False}, 'conta_mestre': account['username']},
    ]}


class PlayerSessionError(ValueError):
    def __init__(self, message, status_code=403):
        super().__init__(message)
        self.status_code = status_code


def require_player_identity(player_id):
    """Require a request's player ID to match this account's selected character."""
    account = current_account()
    if not account:
        raise PlayerSessionError('Entre na sua conta para continuar.', 401)
    selected_id = str(session.get('portal_character') or '')
    requested_id = str(player_id or '')
    if not ObjectId.is_valid(selected_id):
        raise PlayerSessionError('Selecione um personagem antes de jogar.', 401)
    if requested_id != selected_id:
        raise PlayerSessionError('O personagem solicitado não é o personagem ativo desta sessão.')
    from modules.player.core import users_collection
    query = {'_id': ObjectId(selected_id), **character_owner_query(account)}
    player = users_collection.find_one(query)
    if not player:
        _clear_portal_session()
        raise PlayerSessionError('Este personagem não pertence à conta conectada.', 403)
    if player.get('conta_mestre_id') != account['_id']:
        users_collection.update_one({'_id': player['_id']}, {'$set': {'conta_mestre_id': account['_id']}})
    return player


def require_csrf():
    token = session.get('portal_csrf', '')
    if not token or not hmac.compare_digest(token, request.headers.get('X-Eldora-CSRF', '')):
        raise ValueError('Sessão expirada. Atualize a página e tente novamente.')


def _jogador_selecionado():
    """Retorna o personagem ativo validando conta e propriedade no servidor."""
    character_id = str(session.get('portal_character') or '')
    if not ObjectId.is_valid(character_id):
        raise PlayerSessionError('Selecione um personagem antes de continuar.', 401)
    return require_player_identity(character_id)


@portal_auth_bp.get('/api/central-eldora/novidades')
def central_eldora_novidades():
    try:
        player = _jogador_selecionado()
        from modules.central_eldora_news import obter_novidades_nao_lidas
        from modules.player.core import users_collection
        leitura = users_collection.database['central_eldora_news_reads'].find_one(
            {'_id': player['_id']}, {'ids_lidos': 1}
        ) or {}
        response = jsonify(novidades=obter_novidades_nao_lidas(leitura.get('ids_lidos', [])))
        response.headers['Cache-Control'] = 'no-store'
        return response
    except PlayerSessionError as exc:
        return jsonify(erro=str(exc)), exc.status_code


@portal_auth_bp.post('/api/central-eldora/novidades/lida')
def marcar_novidade_central_eldora_lida():
    try:
        require_csrf()
        player = _jogador_selecionado()
        novidade_id = str((request.get_json(silent=True) or {}).get('id') or '')
        from modules.central_eldora_news import CENTRAL_ELDORA_NEWS
        if novidade_id not in {item['id'] for item in CENTRAL_ELDORA_NEWS}:
            return jsonify(erro='Novidade não encontrada.'), 404
        from modules.player.core import users_collection
        users_collection.database['central_eldora_news_reads'].update_one(
            {'_id': player['_id']},
            {'$addToSet': {'ids_lidos': novidade_id}},
            upsert=True,
        )
        return jsonify(sucesso=True)
    except PlayerSessionError as exc:
        return jsonify(erro=str(exc)), exc.status_code
    except ValueError as exc:
        return jsonify(erro=str(exc)), 403


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


def start_session(account, remember=True, auth_method='unknown'):
    previous_account_id = str(session.get('portal_account') or '')
    if ObjectId.is_valid(previous_account_id):
        revoke = current_app.config.get('REVOKE_ACCOUNT_SOCKETS')
        if revoke:
            revoke(previous_account_id)
    session.pop('portal_pending_identity', None)
    session.pop('portal_pending_google_handoff_hash', None)
    session.pop('portal_character', None)
    session['portal_account'] = str(account['_id'])
    session['portal_session_version'] = int(account.get('session_version', 0))
    session['portal_csrf'] = secrets.token_urlsafe(32)
    session['portal_login_at'] = time.time()
    session['portal_auth_method'] = auth_method
    session.permanent = remember


def account_payload(account):
    from modules.player.core import users_collection
    characters = []
    for p in users_collection.find(character_owner_query(account)):
        characters.append({'id': str(p['_id']), 'nome': p.get('character_name','Herói'), 'genero': p.get('gender','masculino'), 'level': p.get('level',1), 'classe': str(p.get('class','aventureiro')).capitalize(), 'avatar_customizado': p.get('avatar_customizado','padrao')})
    has_password = bool(account.get('password_hash'))
    google_linked = bool(account.get('google_sub'))
    telegram_linked = bool(account.get('telegram_verified_id'))
    return {'sucesso': True, 'username': account['username'], 'login_alias': account.get('login_alias'), 'personagens': characters, 'csrf': session['portal_csrf'], 'has_password': has_password, 'display_name': account.get('login_alias',account['username']), 'google_linked': google_linked, 'telegram_linked': telegram_linked, 'can_unlink_google': has_password or telegram_linked, 'can_unlink_telegram': has_password or google_linked, 'auth_method': session.get('portal_auth_method', 'unknown'), 'fresh_auth': time.time()-session.get('portal_login_at', 0) <= 600}


def create_telegram_google_handoff(account):
    """Issue a short-lived, one-use bridge from browser Google auth to the Mini App."""
    from modules.player.core import db
    bot_username = os.getenv('TELEGRAM_BOT_USERNAME', 'Eldora_rpg_bot').strip().lstrip('@')
    if not re.fullmatch(r'[A-Za-z0-9_]{5,32}', bot_username):
        raise ValueError('Bot Telegram não configurado para retornar ao jogo.')
    token = secrets.token_urlsafe(32)
    col = db['portal_telegram_google_handoffs']
    col.create_index('token_hash', unique=True)
    col.create_index('expires_at', expireAfterSeconds=0)
    col.insert_one({
        'token_hash': hashlib.sha256(token.encode()).hexdigest(),
        'account_id': account['_id'],
        'expires_at': datetime.now(timezone.utc) + timedelta(minutes=10),
    })
    return f'https://t.me/{bot_username}?start=eldora_{token}'


def claim_telegram_google_handoff(token, telegram_user_id):
    """Bind a handoff to the Telegram user who opened the bot deep link."""
    if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
        return False
    if type(telegram_user_id) is not int or telegram_user_id <= 0:
        return False
    from modules.player.core import db
    col = db['portal_telegram_google_handoffs']
    record = col.find_one_and_update({
        'token_hash': hashlib.sha256(token.encode()).hexdigest(),
        'expires_at': {'$gt': datetime.now(timezone.utc)},
        '$or': [{'telegram_id': {'$exists': False}}, {'telegram_id': telegram_user_id}],
    }, {'$set': {'telegram_id': telegram_user_id}}, return_document=ReturnDocument.AFTER)
    return bool(record)


def consume_telegram_google_handoff(token, telegram_user_id):
    """Atomically consume a browser-to-Mini-App bridge token."""
    if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
        return None
    return consume_telegram_google_handoff_hash(hashlib.sha256(token.encode()).hexdigest(), telegram_user_id)


def consume_telegram_google_handoff_hash(token_hash, telegram_user_id):
    """Consume the staged handoff using the signed Telegram user identity."""
    if not isinstance(token_hash, str) or not re.fullmatch(r'[a-f0-9]{64}', token_hash):
        return None
    if type(telegram_user_id) is not int or telegram_user_id <= 0:
        return None
    from modules.player.core import db
    col = db['portal_telegram_google_handoffs']
    record = col.find_one_and_delete({
        'token_hash': token_hash,
        'expires_at': {'$gt': datetime.now(timezone.utc)},
        'telegram_id': telegram_user_id,
    })
    if not record:
        return None
    return accounts().find_one({'_id': record['account_id'], 'google_sub': {'$type': 'string'}})


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
    account = current_account()
    session.setdefault('portal_csrf', secrets.token_urlsafe(32))
    payload = account_payload(account) if account else {'sucesso': True, 'csrf': session['portal_csrf']}
    payload.update({
        'authenticated': bool(account),
        'google_client_id': google_client_id(),
        'selected_character_id': str(session.get('portal_character') or '') or None if account else None,
    })
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
        if mode not in ('login','create','link','replace'):
            raise ValueError('Ação inválida.')
        return_to_telegram = data.get('return_to_telegram') is True
        if return_to_telegram and (provider != 'google' or mode != 'login'):
            raise ValueError('Retorno ao Telegram disponível apenas para entrar com Google.')
        account = current_account() if mode in ('link','replace') else None
        if mode in ('link','replace') and (not account or time.time()-session.get('portal_login_at',0)>600):
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
        elif mode == 'replace':
            alternate_method = session.get('portal_auth_method')
            alternate_available = (
                (alternate_method == 'password' and bool(account.get('password_hash')))
                or (alternate_method == 'google' and bool(account.get('google_sub')) and provider != 'google')
                or (alternate_method == 'telegram' and bool(account.get('telegram_verified_id')) and provider != 'telegram')
            )
            if not alternate_available or not account.get(field):
                return jsonify(erro='Entre por outro método já vinculado antes de trocar este provedor.'), 403
            if owner and owner['_id'] != account['_id']:
                raise ValueError('Esta identidade já está vinculada a outra conta. Nenhum personagem foi alterado.')
            result = col.update_one({'_id': account['_id'], field: account.get(field)}, {'$set': {field: identity}})
            if result.matched_count != 1:
                raise ValueError('Vinculação alterada. Entre novamente.')
            account = col.find_one({'_id': account['_id']})
        elif owner:
            if mode == 'create':
                return jsonify(erro='Esta identidade já possui conta. Escolha Entrar em conta vinculada.'), 409
            account = owner
        elif mode == 'create':
            oid = ObjectId()
            account = {'_id':oid, 'username':'eldora_'+str(oid), field:identity, 'criado_em':datetime.now(timezone.utc)}
            if provider == 'telegram':
                account.update(telegram_credentials(data, col))
            col.insert_one(account)
        else:
            if provider == 'google':
                return jsonify(erro='Este Google ainda não está vinculado a uma conta-mestre. Se você já tem personagens, entre na conta existente com usuário e senha ou Telegram e vincule o Google em Conta Eldora. Não crie outra conta para recuperar seus personagens.'), 409
            return jsonify(erro='Este Telegram ainda não está vinculado a uma conta-mestre. Se você já tem personagens, entre na conta existente e vincule o Telegram em Conta Eldora.'), 409
        start_session(account, auth_method=provider)
        payload = account_payload(account)
        if return_to_telegram:
            payload['telegram_deep_link'] = create_telegram_google_handoff(account)
        return jsonify(payload)
    except ImportError:
        return jsonify(erro='Dependência de login não instalada no servidor.'), 503
    except AccountInputError as exc:
        return jsonify(erro=str(exc)), 400
    except DuplicateKeyError:
        return jsonify(erro='Identidade já vinculada. Entre novamente; não foi criada outra vinculação.'), 409
    except (ValueError, TypeError, KeyError):
        # Detalhes de tokens ou credenciais nunca são devolvidos ao navegador.
        return jsonify(erro='Não foi possível validar ou vincular. Entre novamente; confira se a identidade já pertence a outra conta.'), 400


@portal_auth_bp.post('/api/auth/telegram-google-handoff')
def exchange_telegram_google_handoff():
    try:
        require_csrf()
        limit_attempts()
        data = request.get_json(silent=True) or {}
        from config import TELEGRAM_TOKEN
        telegram_user_id = verify_telegram(str(data.get('init_data', '')), TELEGRAM_TOKEN)
        if data.get('token'):
            account = consume_telegram_google_handoff(data.get('token'), telegram_user_id)
        else:
            token_hash = session.pop('portal_pending_google_handoff_hash', None)
            account = consume_telegram_google_handoff_hash(token_hash, telegram_user_id)
        if not account:
            return jsonify(erro='Este acesso expirou ou já foi usado. Volte ao bot e repita a entrada com Google.'), 410
        start_session(account, auth_method='google')
        response = jsonify(account_payload(account))
        response.headers['Cache-Control'] = 'no-store'
        return response
    except ValueError as exc:
        return jsonify(erro=str(exc)), 403


@portal_auth_bp.post('/api/auth/telegram-google-handoff/issue')
def issue_telegram_google_handoff():
    try:
        require_csrf()
        limit_attempts()
        account = current_account()
        if not account:
            return jsonify(erro='Entre novamente com Google para voltar ao Telegram.'), 401
        if not account.get('google_sub'):
            return jsonify(erro='Esta conta ainda não tem Google vinculado.'), 409
        response = jsonify(telegram_deep_link=create_telegram_google_handoff(account))
        response.headers['Cache-Control'] = 'no-store'
        return response
    except ValueError as exc:
        return jsonify(erro=str(exc)), 403


def telegram_credentials(data, col, exclude_account_id=None):
    from werkzeug.security import generate_password_hash
    alias = str(data.get('username','')).strip().lower()
    password = data.get('password','')
    if not re.fullmatch(r'[a-z0-9_]{3,24}',alias) or alias.startswith('eldora_'):
        raise AccountInputError('Use 3 a 24 letras, números ou sublinhado. O prefixo eldora_ é reservado.')
    if not isinstance(password,str) or not 6 <= len(password) <= 128:
        raise AccountInputError('A senha precisa ter de 6 a 128 caracteres.')
    conflict_query = {'$or':[{'username':alias},{'login_alias':alias}]}
    if exclude_account_id is not None:
        conflict = col.find_one(conflict_query)
        if conflict and conflict.get('_id') != exclude_account_id:
            raise AccountInputError('Este usuário já está em uso. Escolha outro nome.')
    elif col.find_one(conflict_query):
        raise AccountInputError('Este usuário já está em uso. Escolha outro nome.')
    return {'login_alias':alias, 'password_hash':generate_password_hash(password)}


@portal_auth_bp.post('/api/auth/credentials')
def set_account_credentials():
    """Add a password fallback to an authenticated provider account."""
    try:
        require_csrf()
        limit_attempts()
        account = current_account()
        if not account:
            return jsonify(erro='Entre na sua conta para configurar um acesso alternativo.'), 401
        if time.time()-session.get('portal_login_at', 0) > 600:
            return jsonify(erro='Por segurança, saia e entre novamente antes de configurar uma senha.'), 401
        data = request.get_json(silent=True) or {}
        method = session.get('portal_auth_method')
        if method == 'password':
            from werkzeug.security import check_password_hash
            current_password = data.get('current_password', '')
            if not account.get('password_hash') or not isinstance(current_password, str) or not check_password_hash(account['password_hash'], current_password):
                return jsonify(erro='Confirme a senha atual para alterá-la.'), 403
        elif not ((method == 'google' and account.get('google_sub')) or (method == 'telegram' and account.get('telegram_verified_id'))):
            return jsonify(erro='Entre novamente por Google, Telegram ou senha antes de alterar este acesso.'), 403
        col = accounts()
        credentials = telegram_credentials(data, col, exclude_account_id=account['_id'])
        query = {'_id': account['_id']}
        if account.get('password_hash'):
            query['password_hash'] = account['password_hash']
        else:
            query['password_hash'] = {'$exists': False}
        updated = col.update_one(query, {'$set': credentials})
        if updated.matched_count != 1:
            return jsonify(erro='As credenciais mudaram. Atualize a página e tente novamente.'), 409
        account.update(credentials)
        return jsonify(account_payload(account))
    except DuplicateKeyError:
        return jsonify(erro='Este usuário já está em uso.'), 409
    except ValueError as exc:
        return jsonify(erro=str(exc)), 400


@portal_auth_bp.post('/api/auth/unlink/<provider>')
def unlink_provider(provider):
    try:
        require_csrf()
        if provider not in ('google', 'telegram'):
            return jsonify(erro='Provedor inválido.'), 404
        account = current_account()
        if not account:
            return jsonify(erro='Entre na sua conta para gerenciar os acessos.'), 401
        if time.time()-session.get('portal_login_at', 0) > 600:
            return jsonify(erro='Por segurança, saia e entre novamente antes de remover um vínculo.'), 401
        field = 'google_sub' if provider == 'google' else 'telegram_verified_id'
        if not account.get(field):
            return jsonify(erro='Este provedor não está vinculado à conta.'), 409
        method = session.get('portal_auth_method')
        alternate_available = (
            (method == 'password' and bool(account.get('password_hash')))
            or (method == 'google' and provider != 'google' and bool(account.get('google_sub')))
            or (method == 'telegram' and provider != 'telegram' and bool(account.get('telegram_verified_id')))
        )
        if not alternate_available:
            return jsonify(erro='Entre novamente usando outro acesso da conta antes de remover este vínculo.'), 403
        remaining_login = bool(account.get('password_hash')) or bool(account.get('google_sub') if provider == 'telegram' else account.get('telegram_verified_id'))
        if not remaining_login:
            return jsonify(erro='Adicione uma senha ou outro provedor antes de remover o último acesso.'), 409
        col = accounts()
        result = col.update_one({'_id': account['_id'], field: account[field]}, {'$unset': {field: ''}, '$inc': {'session_version': 1}})
        if result.matched_count != 1:
            return jsonify(erro='O vínculo mudou. Atualize a página e tente novamente.'), 409
        account.pop(field, None)
        account['session_version'] = int(account.get('session_version', 0)) + 1
        session['portal_session_version'] = account['session_version']
        revoke = current_app.config.get('REVOKE_ACCOUNT_SOCKETS')
        if callable(revoke):
            revoke(str(account['_id']))
        return jsonify(account_payload(account))
    except ValueError as exc:
        return jsonify(erro=str(exc)), 403


@portal_auth_bp.post('/api/auth/logout-all')
def logout_all_sessions():
    try:
        require_csrf()
        account = current_account()
        if not account:
            return jsonify(erro='Entre na sua conta para continuar.'), 401
        accounts().update_one({'_id': account['_id']}, {'$inc': {'session_version': 1}})
        revoke = current_app.config.get('REVOKE_ACCOUNT_SOCKETS')
        if callable(revoke):
            revoke(str(account['_id']))
        _clear_portal_session()
        return jsonify(sucesso=True)
    except ValueError as exc:
        return jsonify(erro=str(exc)), 403


@portal_auth_bp.post('/api/auth/telegram-credentials')
def set_telegram_credentials():
    try:
        require_csrf()
        limit_attempts()
        account=current_account()
        if not account or account.get('password_hash'):
            return jsonify(erro='Entre na conta Telegram que ainda não possui senha.'), 403
        data=request.get_json(silent=True) or {}
        from config import TELEGRAM_TOKEN
        tid=verify_telegram(str(data.get('init_data','')),TELEGRAM_TOKEN)
        if tid!=account.get('telegram_verified_id'):
            return jsonify(erro='Este Telegram não corresponde à conta.'), 403
        col=accounts()
        credentials=telegram_credentials(data,col,exclude_account_id=account['_id'])
        updated=col.update_one({'_id':account['_id'],'password_hash':{'$exists':False}}, {'$set':credentials})
        if updated.matched_count!=1:
            return jsonify(erro='As credenciais já foram configuradas. Entre novamente.'), 409
        account.update(credentials)
        return jsonify(account_payload(account))
    except DuplicateKeyError:
        return jsonify(erro='Este usuário já está em uso.'), 409
    except ValueError as exc:
        return jsonify(erro=str(exc)), 400


@portal_auth_bp.post('/api/auth/select')
def select_character():
    try:
        require_csrf()
        account = current_account()
        if not account:
            return jsonify(erro='Entre na sua conta.'), 401
        from modules.player.core import users_collection
        value = (request.get_json(silent=True) or {}).get('character_id')
        if not ObjectId.is_valid(str(value)) or not users_collection.find_one({'_id':ObjectId(value), **character_owner_query(account)}):
            return jsonify(erro='Este personagem não pertence à sua conta.'), 403
        users_collection.update_one({'_id':ObjectId(value), **character_owner_query(account)}, {'$set': {'conta_mestre_id': account['_id']}})
        previous_character_id = str(session.get('portal_character') or '')
        session['portal_character'] = str(value)
        if previous_character_id and previous_character_id != str(value):
            revoke = current_app.config.get('REVOKE_ACCOUNT_SOCKETS')
            if revoke:
                revoke(str(account['_id']))
        return jsonify(sucesso=True)
    except ValueError as exc:
        return jsonify(erro=str(exc)), 403


@portal_auth_bp.post('/api/auth/logout')
def logout():
    try:
        require_csrf()
    except ValueError as exc:
        return jsonify(erro=str(exc)), 403
    account_id = str(session.get('portal_account') or '')
    _clear_portal_session()
    if ObjectId.is_valid(account_id):
        revoke = current_app.config.get('REVOKE_ACCOUNT_SOCKETS')
        if revoke:
            revoke(account_id)
    return jsonify(sucesso=True)
