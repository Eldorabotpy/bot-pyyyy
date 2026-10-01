# Compras da Flora usam a mesma coleção e inventário do personagem.
from flask_socketio import emit
from flask import request
from bson.objectid import ObjectId

CATALOGO_FLORA = {
    "pocao_xp_boost": {"nome": "Poção de XP P", "preco": 15},
    "pocao_xp_boost_g": {"nome": "Poção de XP G", "preco": 60},
}

def registrar_loja_reino(socketio, db, jogadores_online):
    @socketio.on('comprar_item_gema')
    def handle_comprar_item_gema(dados):
        from modules.player.core import users_collection
        jogador_online = jogadores_online.get(request.sid)
        if not jogador_online:
            emit('respostaCompraGema', {'sucesso': False, 'mensagem': 'Reconecte ao reino para comprar.'})
            return
        item = dados.get('item') if isinstance(dados, dict) else None
        produto = CATALOGO_FLORA.get(item) if isinstance(item, str) else None
        if not produto:
            emit('respostaCompraGema', {'sucesso': False, 'mensagem': 'Artigo indisponível.'})
            return
        char_id = str(jogador_online.get('char_id', ''))
        if not ObjectId.is_valid(char_id):
            return
        oid = ObjectId(char_id)
        # Comparação do inventário evita sobrescrever compras/consumos concorrentes.
        for _ in range(3):
            jogador = users_collection.find_one({'_id': oid})
            if not jogador or int(jogador.get('gemas', 0)) < produto['preco']:
                emit('respostaCompraGema', {'sucesso': False, 'mensagem': f"Gemas insuficientes! Custa {produto['preco']} 💎."})
                return
            anterior = jogador.get('inventory', {})
            if not isinstance(anterior, dict):
                break
            inventario = dict(anterior)
            atual = inventario.get(item, 0)
            if isinstance(atual, dict):
                inventario[item] = {**atual, 'quantity': int(atual.get('quantity', 0)) + 1}
            else:
                inventario[item] = int(atual) + 1
            resultado = users_collection.update_one(
                {'_id': oid, 'gemas': {'$gte': produto['preco']},
                 'inventory': anterior if 'inventory' in jogador else {'$exists': False}},
                {'$inc': {'gemas': -produto['preco']}, '$set': {'inventory': inventario}})
            if resultado.modified_count:
                emit('respostaCompraGema', {'sucesso': True, 'mensagem': f"{produto['nome']} entregue na mochila. Use para ativar o XP dobrado!"})
                return
        emit('respostaCompraGema', {'sucesso': False, 'mensagem': 'O inventário mudou. Tente novamente.'})
