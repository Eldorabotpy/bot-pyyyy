"""Isolated regressions for HTTP character IDs and Socket.IO invitation authorization."""

import ast
import sys
from pathlib import Path
from types import ModuleType

from flask import Flask, jsonify, request

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
source = ast.parse((root / 'main.py').read_text(encoding='utf-8-sig'))
middleware_node = next(
    node for node in source.body
    if isinstance(node, ast.FunctionDef)
    and node.name == 'enforce_selected_character_for_player_apis'
)

identity_calls = []
middleware_node.decorator_list = []


class PlayerSessionError(ValueError):
    status_code = 401


def require_player_identity(player_id):
    identity_calls.append(str(player_id))


portal_auth_stub = ModuleType('modules.portal_auth')
portal_auth_stub.PlayerSessionError = PlayerSessionError
portal_auth_stub.require_player_identity = require_player_identity
previous_portal_auth = sys.modules.get('modules.portal_auth')
sys.modules['modules.portal_auth'] = portal_auth_stub

scope = {'request': request, 'jsonify': jsonify}
exec(compile(ast.Module(body=[middleware_node], type_ignores=[]), 'main.py', 'exec'), scope)
middleware = scope['enforce_selected_character_for_player_apis']
app = Flask(__name__)

try:
    for key in ('user_id', 'char_id', 'jogador_id', 'player_id', 'character_id', 'personagem_id', 'id_personagem', 'id_jogador'):
        identity_calls.clear()
        with app.test_request_context('/api/teste', method='POST', json={key: 'personagem-valido'}):
            assert middleware() is None
        assert identity_calls == ['personagem-valido'], key

    identity_calls.clear()
    with app.test_request_context('/api/personagem/personagem-valido'):
        request.view_args = {'personagem_id': 'personagem-valido'}
        assert middleware() is None
    assert identity_calls == ['personagem-valido']

    identity_calls.clear()
    with app.test_request_context('/api/teste', method='POST', json={'user_id': 'a', 'personagem_id': 'b'}):
        response, status = middleware()
        assert status == 403 and response.json['erro']
    assert not identity_calls

    identity_calls.clear()
    with app.test_request_context('/api/teste', method='POST'):
        assert middleware() is None
    assert not identity_calls
finally:
    if previous_portal_auth is None:
        sys.modules.pop('modules.portal_auth', None)
    else:
        sys.modules['modules.portal_auth'] = previous_portal_auth


from modules.socket_invites import SocketInviteRegistry

now = [100.0]
registry = SocketInviteRegistry(ttl_seconds=30, clock=lambda: now[0])
assert registry.issue('amizade', 'sid-alvo', 'sid-remetente', 'char-a', 'char-b')
assert registry.consume('amizade', 'sid-errado', 'char-b', sender_char_id='char-a') is None
assert registry.consume('amizade', 'sid-alvo', 'outro-char', sender_char_id='char-a') is None
assert registry.consume('amizade', 'sid-alvo', 'char-b', sender_char_id='char-invasor') is None
assert registry.consume('amizade', 'sid-alvo', 'char-b', sender_char_id='char-a')['sender_sid'] == 'sid-remetente'
assert registry.consume('amizade', 'sid-alvo', 'char-b', sender_char_id='char-a') is None

registry.issue('grupo', 'sid-alvo', 'sid-remetente', 'char-a', 'char-b', {'party_id': 'party-a'})
assert registry.consume('grupo', 'sid-alvo', 'char-b', context={'party_id': 'party-b'}) is None
assert registry.consume('grupo', 'sid-alvo', 'char-b', context={'party_id': 'party-a'})

registry.issue('duelo', 'sid-alvo', 'sid-remetente', 'char-a', 'char-b')
now[0] += 31
assert registry.consume('duelo', 'sid-alvo', 'char-b', sender_char_id='char-a') is None

registry.issue('duelo', 'sid-alvo', 'sid-remetente', 'char-a', 'char-b')
registry.discard_socket('sid-remetente')
assert registry.consume('duelo', 'sid-alvo', 'char-b', sender_char_id='char-a') is None

print('OK: aliases de identidade HTTP, IDs conflitantes, seleção de personagem e convites Socket.IO curtos, específicos e de uso único.')
